import subprocess
import os, sys
from typing import List, Dict, Any
import math
from functools import reduce
from random import choice, randint, random
import time
from copy import deepcopy

import bpy
from bpy.types import Operator, Context, Event, Image, Mesh, Object
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty

from . import constant
from . import util
from . import prop

class InstallImageProcessingOperator(Operator):
    bl_idname = 'wm.install_image_processing'
    bl_label = 'Install Image Processing'
    
    def execute(self, context:Context):
        for label, (mod, version, _) in constant.image_processing.items():
            if util.install_module(mod, version, constant.modules_path):
                print(f'[Info] Installed module: {label}')
            else:
                print(f'[Error] Failed to isntall module: {label}')
        return {'FINISHED'}



class RegionScaleOperator(bpy.types.Operator):
    bl_idname = 'region.scale'
    bl_label = 'Scale Rigion'
    
    target:StringProperty(
        name = 'Object'
    )

    factor:FloatProperty(
        name = 'Factor',
        default = 0.5,
        min = 0.001
    )

    @classmethod
    def poll(cls, context:Context):
        return context.mode == 'OBJECT'

    def execute(self, context:Context):
        region = bpy.data.objects[self.target].data.region_props
        region.w *= self.factor
        region.h *= self.factor
        return {'FINISHED'}

    def invoke(self, context:Context, event:Event):
        context.scene.atlas_props.draw_regions = True
        if not self.target:
            self.target = context.active_object.name
        return self.execute(context)



class RegionMoveOperator(Operator):
    bl_idname = 'region.move'
    bl_label = 'Move Region'
    
    target:StringProperty(
        name = 'Object'
    )

    x:FloatProperty()
    y:FloatProperty()

    @classmethod
    def poll(cls, context:Context):
        return context.mode == 'OBJECT'

    def modal(self, context:Context, event:Event):
        if event.type == 'MOUSEMOVE':  # Apply
            area = context.space_data
            sx, sy = area.zoom
            region = bpy.data.objects[self.target].data.region_props
            region.x += (event.mouse_x - event.mouse_prev_x) / context.region.width / sx
            region.y += (event.mouse_y - event.mouse_prev_y) / context.region.height / sy
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':  # Confirm
            return {'FINISHED'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:  # Cancel
            region = bpy.data.objects[self.target].data.region_props
            region.x = self.x
            region.y = self.y
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

    def invoke(self, context:Context, event:Event):
        context.scene.atlas_props.draw_regions = True
        if not self.target:
            self.target = context.active_object.name
        region = bpy.data.objects[self.target].data.region_props
        self.x = region.x
        self.y = region.y
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}



class RegionAddResourceOperator(Operator):
    bl_idname = 'region.add_resource'
    bl_label = 'Add Image'
    
    target:StringProperty(
        name = 'Object'
    )

    def execute(self, context:Context):
        mesh = bpy.data.objects[self.target].data
        resource = mesh.region_resources.add()
        mesh.region_resource_index = len(mesh.region_resources) - 1
        resource.layer = mesh.region_resource_index
        return {'FINISHED'}
    
    def invoke(self, context:Context, event:Event):
        if not self.target:
            self.target = context.active_object.name
        return self.execute(context)



class RegionRemoveResourceOperator(Operator):
    bl_idname = 'region.remove_resource'
    bl_label = 'Remove Image'
    
    target:StringProperty(
        name = 'Object'
    )

    def execute(self, context:Context):
        mesh = bpy.data.objects[self.target].data
        if len(mesh.region_resources) > 0 and mesh.region_resource_index >= 0:
            mesh.region_resources.remove(mesh.region_resource_index)
            mesh.region_resource_index -= 1
        return {'FINISHED'}
    
    def invoke(self, context:Context, event:Event):
        if not self.target:
            self.target = context.active_object.name
        return self.execute(context)



class RegionMoveResourceOperator(Operator):
    bl_idname = 'region.move_resource'
    bl_label = 'Move Resource'
    
    target:StringProperty(
        name = 'Object'
    )
    up:BoolProperty(
        name = 'Up'
    )

    def execute(self, context:Context):
        mesh = bpy.data.objects[self.target].data
        if self.up and mesh.region_resource_index > 0:
            mesh.region_resources.move(mesh.region_resource_index, mesh.region_resource_index - 1)
            mesh.region_resource_index -= 1
        elif not self.up and mesh.region_resource_index < len(mesh.region_resources) - 1:
            mesh.region_resources.move(mesh.region_resource_index, mesh.region_resource_index + 1)
            mesh.region_resource_index += 1
        return {'FINISHED'}

    def invoke(self, context:Context, event:Event):
        if not self.target:
            self.target = context.active_object.name
        return self.execute(context)



class RegionCalcSizeOperator(Operator):
    bl_idname = 'region.calc_size'
    bl_label = 'Calc Size'
    
    target:StringProperty(
        name = 'Object'
    )

    @classmethod
    def poll(cls, context:Context):
        if not hasattr(context.space_data, 'image'): return False
        if context.space_data.image is None: return False
        if context.mode != 'OBJECT': return False
        return True

    def execute(self, context:Context):
        mesh = bpy.data.objects[self.target].data
        if mesh.region_resources:
            mesh.region_props.xw = max(r.image.size[0] for r in mesh.region_resources)
            mesh.region_props.xh = max(r.image.size[1] for r in mesh.region_resources)
        else:
            mesh.region_props.w = 1
            mesh.region_props.h = 1
        return {'FINISHED'}

    def invoke(self, context:Context, event:Event):
        if not self.target:
            self.target = context.active_object.name
        return self.execute(context)



class RegionFindResourcesOperator(Operator):
    bl_idname = 'region.find_resources'
    bl_label = 'Find Resources'

    def execute(self, context:Context):
        for obj in context.selected_objects:
            if obj.type != 'MESH': continue
            mesh = obj.data

            loaded = [r.image for r in mesh.region_resources]
            extra = []

            # Find in materials
            for material in obj.data.materials:
                if material is None: continue
                extra.extend(n.image for n in material.node_tree.nodes if hasattr(n, 'image') and n.image not in loaded)

            # Find in names
            extra.extend(i for i in bpy.data.images if i.name.startswith(obj.name) or i.name.endswith(obj.name))
            
            for image in extra:
                resource = mesh.region_resources.add()
                resource.image = image
                mesh.region_resource_index = len(mesh.region_resources) - 1
                resource.layer = mesh.region_resource_index
        return {'FINISHED'}



class AtlasCreateOperator(Operator):
    bl_idname = 'atlas.create'
    bl_label = 'Create Atlas'
    
    def execute(self, context:Context):
        context.scene.atlas_props.draw_regions = True
        w = context.scene.atlas_props.atlas_w
        h = context.scene.atlas_props.atlas_h
        atlas = bpy.data.images.new('Template', width = w, height = h, alpha = True)
        atlas.generated_type = 'COLOR_GRID'
        
        context.space_data.image = atlas

        return {'FINISHED'}



class AtlasPackOperator(Operator):
    class Rect:
        def __init__(self, proto, x, y, w, h):
            self.proto = proto
            self.x = x
            self.y = y
            self.w = w
            self.h = h

    bl_idname = 'atlas.pack'
    bl_label = 'Pack Atlas'
    
    scale:BoolProperty(
        name = 'Scale',
        default = True
    )

    time:IntProperty(
        name = 'Analysis Time',
        default = 5,
        min = 0
    )

    def size(self, regions):
        w = max(r.x + r.w for r in regions) - min(r.x for r in regions)
        h = max(r.y + r.h for r in regions) - min(r.y for r in regions)
        return w, h

    def intersects(self, a, b):
        return a is not b and a.x < b.x + b.w and a.x + a.w > b.x and a.y < b.y + b.h and a.y + a.h > b.y
    
    def collides(self, regions):
        return any(self.intersects(a, b) for a in regions for b in regions)

    def grid(self, v:float, step:float):
        return math.floor(v / step) * step

    def estimate(self, regions):
        '''Fits in square metric'''
        w, h = self.size(regions)
        weight = 2
        return pow(w * h, weight)

    def resolve(self, regions, step):
        '''Bubble collisions'''
        while self.collides(regions):
            for region in regions:
                intersections = [r for r in regions if self.intersects(region, r)]
                if not intersections: continue
                neighbor = choice(intersections)
                direction = choice(('l', 'r', 't', 'b'))
                if direction == 'l':
                    region.x = self.grid(neighbor.x + neighbor.w + step, step)
                elif direction == 'r':
                    region.x = self.grid(neighbor.x - region.w - step, step)
                elif direction == 't':
                    region.y = self.grid(neighbor.y + neighbor.h + step, step)
                elif direction == 'b':
                    region.y = self.grid(neighbor.y - region.h - step, step)

    # TODO Performance of the outer loop can be improved by random function
    def stick(self, regions, step):
        '''Move regions towards origin of coordinates'''
        for _ in range(len(regions)):
            for region in regions:
                horizontal = round(region.x / step)
                for i in range(0, horizontal):
                    region.x = (horizontal - i - 1) * step
                    if any(self.intersects(region, r) for r in regions):
                        region.x = (horizontal - i) * step
                        break

                vertical = round(region.y / step)
                for i in range(0, vertical):
                    region.y = (vertical - i - 1) * step
                    if any(self.intersects(region, r) for r in regions):
                        region.y = (vertical - i) * step
                        break

    @classmethod
    def poll(cls, context:Context):
        return context.mode == 'OBJECT' and len(context.selected_objects) > 0

    def execute(self, context:Context):
        context.scene.atlas_props.draw_regions = True

        regions = [o.data.region_props for o in context.selected_objects if o.type == 'MESH']
        
        # Define grid step
        scale = 1000
        step = reduce(math.gcd, [round(r.w * scale) for r in regions] + [round(r.h * scale) for r in regions]) / scale
        step = max(step, 1 / scale)
        step = min(step, 20 / scale)

        # Pack
        prev = time.time()
        elapsed = 0
        best = None
        weight = 0
        border = max(max(self.size(regions)), 1) * 2
        while elapsed <= self.time:
            generated = [self.Rect(r,
                randint(0, round((border - r.w) * scale)) / scale,
                randint(0, round((border - r.w) * scale)) / scale,
                r.w, r.h
            ) for r in regions]

            self.resolve(generated, step)
            self.stick(generated, step)
            w = self.estimate(generated)
            if best is None or w < weight:
                best = generated
                weight = w

            t = time.time()
            elapsed += t - prev
            prev = t
            # break

        assert(best is not None)

        # Apply result
        w, h = self.size(best)
        scale = max(w, h)
        if self.scale:
            for region in best:
                region.proto.x = region.x / scale
                region.proto.y = region.y / scale
                region.proto.w = region.w / scale
                region.proto.h = region.h / scale
        dx = min(r.proto.x for r in best)
        dy = min(r.proto.y for r in best)
        for region in best:
            region.proto.x -= dx
            region.proto.y -= dy

        return {'FINISHED'}



class AtlasBakeOperator(Operator):
    bl_idname = 'atlas.bake'
    bl_label = 'Bake Atlas'
    
    @classmethod
    def poll(cls, context:Context):
        path = os.path.normpath(bpy.path.abspath(context.scene.atlas_props.export))
        return context.mode == 'OBJECT' and os.path.isdir(path)

    def execute(self, context:Context):
        context.scene.atlas_props.draw_regions = True
        print('Bake atlases')
        import PIL.Image

        meshes:List[Mesh] = [o.data for o in context.selected_objects if o.type == 'MESH']

        # Sort images into layers lists
        data:Dict[Any, List[prop.RegionResource]] = {}
        for mesh in meshes:
            for resource in mesh.region_resources:
                items = data.get(resource.layer) or []
                items.append((mesh.uv_layers.active, resource, mesh.region_props))
                data[resource.layer] = items
        
        w = context.scene.atlas_props.atlas_w
        h = context.scene.atlas_props.atlas_h
        i = 0
        path = os.path.normpath(bpy.path.abspath(context.scene.atlas_props.export))
        for layer in data.values():
            images = [util.blender_to_pillow(r.image) for (_, r, _) in layer]
            atlas = PIL.Image.new('RGBA', (w, h))
            # Bake atlas
            for ((tex, resource, region), image) in zip(layer, images):
                image = image.resize((int(region.w * w), int(region.h * h)))
                atlas.paste(image, (int(region.x * w), int(region.y * h)), image)
            print(f'Atlas backed: {i + 1} / {len(data)}')
            atlas = atlas.transpose(PIL.Image.Transpose.FLIP_TOP_BOTTOM)
            atlas.show()
            atlas.save(os.path.join(path, f'{layer[0][1].layer}.png'))
            i += 1
        self.report({'INFO'}, f'Saved {i} to {path}')

        return {'FINISHED'}
