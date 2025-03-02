import subprocess
import os, sys
from typing import List, Dict, Any
import math
from functools import reduce
from random import choice, randint, random
import time
from copy import deepcopy
import math

import bpy
from bpy.types import Operator, Context, Event, Image, Mesh, Object, UILayout
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty, EnumProperty
from mathutils import Vector, Matrix

from . import constant
from . import util
from . import prop
from . import struct

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
        resource.layer = f'color{mesh.region_resource_index}'
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
        if context.mode != 'OBJECT': return False
        return True

    def execute(self, context:Context):
        mesh = bpy.data.objects[self.target].data
        if mesh.region_resources and hasattr(context.space_data, 'image') and context.space_data.image:
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
                resource.layer = f'color{mesh.region_resource_index}'
        return {'FINISHED'}



class AtlasScaleOperator(bpy.types.Operator):
    bl_idname = 'atlas.scale'
    bl_label = 'Scale Atlas'

    factor:FloatProperty(
        name = 'Factor',
        default = 2.0,
        min = 0.001
    )

    def execute(self, context:Context):
        context.scene.atlas_props.atlas_w = round(context.scene.atlas_props.atlas_w * self.factor)
        context.scene.atlas_props.atlas_h = round(context.scene.atlas_props.atlas_h * self.factor)
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



class AtlasPackHeuristicOperator(Operator):
    class Rect:
        def __init__(self, proto, x, y, w, h):
            self.proto = proto
            self.x = x
            self.y = y
            self.w = w
            self.h = h

    bl_idname = 'atlas.pack_heuristic'
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

    metric:EnumProperty(
        name = 'Metric',
        items = [
            ('SQUARE', 'Square', '', 1),
            ('OCCUPIED', 'Occupied', '', 2)
        ],
        default = 'OCCUPIED'
    )

    bias = 1e-7

    def size(self, regions):
        w = max(r.x + r.w for r in regions) - min(r.x for r in regions)
        h = max(r.y + r.h for r in regions) - min(r.y for r in regions)
        return w, h

    def intersects(self, a, b):
        return a is not b and a.x + self.bias < b.x + b.w and a.x + a.w - self.bias > b.x and a.y + self.bias < b.y + b.h and a.y + a.h - self.bias > b.y
    
    def collides(self, regions):
        return any(self.intersects(a, b) for a in regions for b in regions)

    def grid(self, v:float, step:float):
        return math.floor(v / step) * step

    def estimate_square(self, regions):
        '''Fits in square metric'''
        w, h = self.size(regions)
        return abs(w - h) * (w * h)
    
    def estimate_occupied(self, regions):
        '''Less free space metric'''
        occupied = sum(r.w * r.h for r in regions)
        w, h = self.size(regions)
        total = w * h
        # In theory negative values are impossible
        return total - occupied

    # TODO Performance of the outer loop can be improved by random function
    def stick(self, regions, step):
        '''Move regions towards origin of coordinates'''
        def left(region):
            horizontal = round(region.x / step)
            for i in range(0, horizontal):
                region.x = (horizontal - i - 1) * step
                if any(self.intersects(region, r) for r in regions):
                    region.x = (horizontal - i) * step
                    break

        def bottom(region):
            vertical = round(region.y / step)
            for i in range(0, vertical):
                region.y = (vertical - i - 1) * step
                if any(self.intersects(region, r) for r in regions):
                    region.y = (vertical - i) * step
                    break

        for _ in range(len(regions)):
            for region in regions:
                left(region)
                bottom(region)

    def resolve(self, regions, step):
        '''Bubble collisions'''
        while self.collides(regions):
            for region in regions:
                intersections = [r for r in regions if self.intersects(region, r)]
                if not intersections: continue
                neighbor = choice(intersections)
                direction = choice(('l', 't'))
                if direction == 'l':
                    region.x = neighbor.x + neighbor.w + self.bias * 2
                elif direction == 't':
                    region.y = neighbor.y + neighbor.h + self.bias * 2

    @classmethod
    def poll(cls, context:Context):
        return context.mode == 'OBJECT' and len(context.selected_objects) > 0

    def execute(self, context:Context):
        context.scene.atlas_props.draw_regions = True

        regions = [o.data.region_props for o in context.selected_objects if o.type == 'MESH']
        
        w, h = max(r.w for r in regions), max(r.h for r in regions)
        source_scale = 1 / max(w, h)
        for region in regions:
            region.w = region.w * source_scale
            region.h = region.h * source_scale

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
        while elapsed <= self.time:
            generated = [self.Rect(r, 0, 0, r.w, r.h) for r in regions]

            self.resolve(generated, step)
            self.stick(generated, step)
            if self.metric == 'SQUARE':
                w = self.estimate_square(generated)
            elif self.metric == 'OCCUPIED':
                w = self.estimate_occupied(generated)
            if best is None or w < weight:
                best = generated
                weight = w

            t = time.time()
            elapsed += t - prev
            prev = t
            # break

        assert(best is not None)

        # Apply result
        if self.scale:
            w, h = self.size(best)
            source_scale = max(w, h)
        for region in best:
            region.proto.x = region.x / source_scale
            region.proto.y = region.y / source_scale
            region.proto.w = region.w / source_scale
            region.proto.h = region.h / source_scale
        dx = min(r.proto.x for r in best)
        dy = min(r.proto.y for r in best)
        for region in best:
            region.proto.x -= dx
            region.proto.y -= dy

        return {'FINISHED'}



class AtlasPack2048Operator(Operator):
    bl_idname = 'atlas.pack_2048'
    bl_label = 'Pack Atlas'

    @classmethod
    def poll(cls, context:Context):
        if context.mode != 'OBJECT': return False
        if len(context.selected_objects) == 0: return False
        if not hasattr(context.space_data, 'image'): return False
        if context.space_data.image is None: return False
        return True

    # https://blog.magnum.graphics/backstage/pot-array-packing/
    def pack(self, atlas_size, regions):
        output = [[0, 0] for _ in range(len(regions))]
        
        free = 1
        previous_size = atlas_size
        
        for i, size in enumerate(regions):
            size = list(size)
            
            if free == 0:
                free = 1
                previous_size = atlas_size
            
            free *= (previous_size[0] // size[0]) * (previous_size[1] // size[1])

            side_slot_count = atlas_size[0] // size[0]
            layer_depth = math.floor(math.log2(side_slot_count))
            slot_index = side_slot_count * side_slot_count - free
            
            coordinates = [0, 0]
            
            for j in range(layer_depth):
                if slot_index & (1 << (2 * (layer_depth - j - 1))):
                    coordinates[0] += atlas_size[0] >> (j + 1)
                if slot_index & (1 << (2 * (layer_depth - j - 1) + 1)):
                    coordinates[1] += atlas_size[1] >> (j + 1)
            
            output[i] = [coordinates[0], coordinates[1]]
            previous_size = size
            free -= 1
        
        return output

    def execute(self, context:Context):
        regions = sorted([o.data.region_props for o in context.selected_objects if o.type == 'MESH'], key = lambda r: max(r.w, r.h), reverse = True)
        sorted_sizes = [(r.xw, r.xh) for r in regions]
        result = self.pack((context.scene.atlas_props.atlas_w, context.scene.atlas_props.atlas_h), sorted_sizes)
        for (region, (x, y)) in zip(regions, result):
            region.xx = x
            region.xy = y
        if any(r.xw != r.xh or (math.log2(r.xw) % 1 != 0) or (math.log2(r.xh) % 1 != 0) for r in regions):
            self.report({'WARNING'}, 'Algorithm works correctly only with squares')
        return {'FINISHED'}



class AtlasPackShelfOperator(Operator):
    bl_idname = 'atlas.pack_shelf'
    bl_label = 'Pack Atlas'
    bl_options = {'REGISTER', 'UNDO'}

    scale:BoolProperty(
        name = 'Scale',
        default = True
    )
    margin:FloatProperty(
        name = 'Margin',
        default = 0.0,
        min = 0.0
    )

    @classmethod
    def poll(cls, context:Context):
        if context.mode != 'OBJECT': return False
        if len(context.selected_objects) == 0: return False
        return True

    def execute(self, context:Context):
        rects = [struct.UVRect(o.data.region_props,
            o.data.region_props.x,
            o.data.region_props.y,
            o.data.region_props.w,
            o.data.region_props.h,
            margin = self.margin
        ) for o in context.selected_objects if o.type == 'MESH']

        w = (len(rects) ** 0.5) * (sum(r.w for r in rects) / len(rects)) if self.scale else 1
        util.pack_shelf_decreasing_high(rects, w)

        min_x = min(r.x for r in rects)
        min_y = min(r.y for r in rects)
        w = max(r.x + r.w for r in rects) - min_x
        h = max(r.y + r.h for r in rects) - min_y
        if hasattr(context.space_data, 'image') and context.space_data.image:
            margin_x = self.margin / context.space_data.image.size[0]
            margin_y = self.margin / context.space_data.image.size[1]
        else:
            margin_x = margin_y = self.margin
        scale = max(w, h) if self.scale else 1.0
        for rect in rects:
            rect.data.x = (rect.x + margin_x - min_x) / scale
            rect.data.y = (rect.y + margin_y - min_y) / scale
            rect.data.w = (rect.data.w - margin_x) / scale
            rect.data.h = (rect.data.h - margin_y) / scale

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
            bpy.ops.screen.area_dupli('INVOKE_DEFAULT')
            context.area.type = 'IMAGE_EDITOR'
            name = f'{layer[0][1].layer}'
            img = util.pillow_to_blender(name, atlas)
            context.space_data.image = img
            context.area.tag_redraw()
            img.save(filepath = os.path.join(path, f'{name}.png'))
            print(f'Atlas backed: {i + 1} / {len(data)}')
            i += 1
        self.report({'INFO'}, f'Saved {i} to {path}')

        return {'FINISHED'}



class AtlasReplaceResourcesOperator(Operator):
    bl_idname = 'atlas.replace_resources'
    bl_label = 'Replace Atlas Images'

    def execute(self, context:Context):
        for obj in context.selected_objects:
            if obj.type != 'MESH': continue
            mesh = obj.data

            for resource in mesh.region_resources:
                for material in mesh.materials:
                    if material is None: continue
                    for node in material.node_tree.nodes:
                        if not hasattr(node, 'image'): continue
                        if not node.image == resource.image: continue
                        image = bpy.data.images.get(f'{resource.layer}')
                        if not image: continue
                        node.image = image

        return {'FINISHED'}



class UVUnwrapPolygonsOperator(Operator):
    bl_idname = 'uv.unwrap_polygons'
    bl_label = 'Unwrap polygons'
    bl_options = {'REGISTER', 'UNDO'}

    scale:BoolProperty(
        name = 'Scale',
        default = True
    )
    factor:FloatProperty(
        name = 'Factor',
        min = 0,
        default = 1
    )

    def draw(self, context:Context):
        layout:UILayout = self.layout
        layout.prop(self, 'scale')
        if self.scale:
            layout.prop(self, 'factor')

    @classmethod
    def poll(cls, context:Context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context:Context):
        mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        mesh:Mesh = context.active_object.data

        if not mesh.uv_layers.active:
            mesh.uv_layers.new()
        uv = mesh.uv_layers.active

        for polygon in mesh.polygons:
            vertices = [mesh.vertices[v].co for v in polygon.vertices]

            # Center vertices
            center = Vector((sum(v.x for v in vertices), sum(v.y for v in vertices), sum(v.z for v in vertices))) / len(vertices)
            for i, v in enumerate(vertices): vertices[i] = v - center

            # Make polygon face up
            a, b, c, *_ = vertices
            v1 = b - a
            v2 = c - a
            normal = v1.cross(v2).normalized()
            target_normal = Vector((0, 0, 1))
            axis = normal.cross(target_normal)
            angle = math.acos(normal.dot(target_normal))
            matrix = Matrix.Rotation(angle, 4, axis)

            for i, v in enumerate(vertices): vertices[i] = matrix @ v

            # Reset polygon z rotation - make it align
            a, b, c, *_ = vertices
            vec = (b - a).normalized()
            angle = math.atan2(vec.y, vec.x)
            matrix = Matrix.Rotation(-angle, 4, Vector((0, 0, 1)))

            for i, v in enumerate(vertices): vertices[i] = matrix @ v

            for index, vertex in zip(polygon.loop_indices, vertices):
                uv.data[index].uv = vertex.xy
        
        if self.scale:
            material = context.active_object.active_material
            if material and material.node_tree.nodes.active and hasattr(material.node_tree.nodes.active, 'image') and material.node_tree.nodes.active.image:
                # Set scale to image
                w, h = material.node_tree.nodes.active.image.size
                for item in uv.data:
                    item.uv.x = item.uv.x / w * self.factor
                    item.uv.y = item.uv.y / h * self.factor
            else:
                # Normalize scale
                w = (max(i.uv.x for i in uv.data) - min(i.uv.x for i in uv.data))
                h = (max(i.uv.y for i in uv.data) - min(i.uv.y for i in uv.data))
                scale = max(w, h)
                for item in uv.data:
                    item.uv = item.uv / scale * self.factor
        
        # Center uv to uv editor
        dx = min(i.uv.x for i in uv.data)
        dy = min(i.uv.y for i in uv.data)
        for item in uv.data:
            item.uv -= Vector((dx, dy))

        bpy.ops.object.mode_set(mode = mode)
        return {'FINISHED'}



class UVPackRectOperator(Operator):
    bl_idname = 'uv.pack_rect'
    bl_label = 'Pack rect'
    bl_options = {'REGISTER', 'UNDO'}

    margin:FloatProperty(
        name = 'Margin',
        default = 0.0,
        min = 0.0
    )

    def draw(self, context:Context):
        layout:UILayout = self.layout
        layout.prop(self, 'margin')

    @classmethod
    def poll(cls, context:Context):
        if not context.active_object: return False
        if context.active_object.type != 'MESH': return False
        if not context.active_object.data.uv_layers.active: return False
        if not context.active_object.data.polygons: return False
        return True

    def execute(self, context:Context):
        mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        mesh:Mesh = context.active_object.data
        uv = mesh.uv_layers.active

        rects = []
        margin = self.margin / max(context.space_data.image.size) if hasattr(context.space_data, 'image') and context.space_data.image else self.margin
        for polygon in mesh.polygons:
            min_x = min(uv.data[i].uv.x for i in polygon.loop_indices)
            min_y = min(uv.data[i].uv.y for i in polygon.loop_indices)
            max_x = max(uv.data[i].uv.x for i in polygon.loop_indices)
            max_y = max(uv.data[i].uv.y for i in polygon.loop_indices)
            rects.append(struct.UVRect(polygon, min_x, min_y,
                (max_x - min_x) + margin * 2,
                (max_y - min_y) + margin * 2,
                margin = margin
            ))

        util.pack_shelf_decreasing_high(rects, (len(rects) ** 0.5) * (sum(r.w for r in rects) / len(rects)))

        for rect in rects:
            min_x = min(uv.data[i].uv.x for i in rect.data.loop_indices)
            min_y = min(uv.data[i].uv.y for i in rect.data.loop_indices)
            for index in rect.data.loop_indices:
                uv.data[index].uv.x = rect.x + (uv.data[index].uv.x - min_x) + rect.margin
                uv.data[index].uv.y = rect.y + (uv.data[index].uv.y - min_y) + rect.margin

        bpy.ops.object.mode_set(mode = mode)
        return {'FINISHED'}
    