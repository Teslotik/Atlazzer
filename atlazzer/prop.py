import math

import bpy
from bpy.types import PropertyGroup, SpaceView3D, SpaceImageEditor, Scene, Image, MeshUVLoopLayer
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty, StringProperty, EnumProperty

from . draw import Painter


regions_painter = None
def set_regions(self, value:bool):
    global regions_painter
    if regions_painter is None and value:
        regions_painter = SpaceImageEditor.draw_handler_add(Painter.uvsquare([o for o in bpy.context.selected_objects if o.type == 'MESH'], thickness = 3), (), 'WINDOW', 'POST_VIEW')
    elif regions_painter is not None and not value:
        SpaceImageEditor.draw_handler_remove(regions_painter, 'WINDOW')
        regions_painter = None


class AtlasProperties(PropertyGroup):
    draw_regions:BoolProperty(
        name = 'Draw UV Regions',
        default = False,
        set = set_regions,
        get = lambda self: regions_painter is not None
    )
    atlas_w:IntProperty(
        name = 'Atlas Width',
        default = 1024,
        min = 1
    )
    atlas_h:IntProperty(
        name = 'Atlas Width',
        default = 1024,
        min = 1
    )
    units:EnumProperty(
        name = 'Units',
        items = [
            ('RELATIVE', 'Relative', '', 1),
            ('PIXELS', 'Pixels', '', 2)
        ]
    )
    filter:StringProperty(
        name = 'Filter',
        default = ''
    )
    pack_analysis_time:IntProperty(
        name = 'Pack Analysis Time',
        default = 5,
        min = 0
    )
    pack_scale:BoolProperty(
        name = 'Pack Scale',
        default = True
    )
    pack_algorithm:EnumProperty(
        name = 'Pack Algorithm',
        items = [
            ('SQUARE', 'Square', '', 1),
            ('OCCUPIED', 'Occupied', '', 2),
            ('2048', '2048', '', 3),
            ('SHELF', 'Shelf', '', 4)
        ],
        default = 'OCCUPIED'
    )
    export:StringProperty(
        name = 'Export',
        subtype = 'DIR_PATH',
        default = '//'
    )



class RegionProperties(PropertyGroup):
    # Relative units
    x:FloatProperty(set = lambda self, v: self.move_x(v), get = lambda self: self.px)
    y:FloatProperty(set = lambda self, v: self.move_y(v), get = lambda self: self.py)
    w:FloatProperty(set = lambda self, v: self.resize_w(v), get = lambda self: self.pw)
    h:FloatProperty(set = lambda self, v: self.resize_h(v), get = lambda self: self.ph)
    # Pixel units
    xx:IntProperty(name = 'x', set = lambda self, v: setattr(self, 'x', v / bpy.context.space_data.image.size[0]), get = lambda self: math.floor(self.x * bpy.context.space_data.image.size[0]))
    xy:IntProperty(name = 'y', set = lambda self, v: setattr(self, 'y', v / bpy.context.space_data.image.size[1]), get = lambda self: math.floor(self.y * bpy.context.space_data.image.size[1]))
    xw:IntProperty(name = 'w', set = lambda self, v: setattr(self, 'w', v / bpy.context.space_data.image.size[0]), get = lambda self: math.floor(self.w * bpy.context.space_data.image.size[0]))
    xh:IntProperty(name = 'h', set = lambda self, v: setattr(self, 'h', v / bpy.context.space_data.image.size[1]), get = lambda self: math.floor(self.h * bpy.context.space_data.image.size[1]))
    # Internal - use as previous pos/size
    px:FloatProperty(default = 0)
    py:FloatProperty(default = 0)
    pw:FloatProperty(default = 1)
    ph:FloatProperty(default = 1)

    def move_x(self, value:float):
        for co in self.id_data.uv_layers.active.uv:
            co.vector.x += value - self.px
        self.px = value
    
    def move_y(self, value:float):
        for co in self.id_data.uv_layers.active.uv:
            co.vector.y += value - self.py
        self.py = value
    
    def resize_w(self, value:float):
        # NOTE If we use 0 or negative valeus, uv will collapse into point and we couldn't restore it
        value = max(value, 0.001)
        for co in self.id_data.uv_layers.active.uv:
            co.vector.x = (co.vector.x - self.px) / self.pw * value + self.px if self.pw > 0 else 0
        self.pw = value
    
    def resize_h(self, value:float):
        value = max(value, 0.001)
        for co in self.id_data.uv_layers.active.uv:
            co.vector.y = (co.vector.y - self.py) / self.ph * value + self.py if self.ph > 0 else 0
        self.ph = value



class RegionResource(PropertyGroup):
    image:PointerProperty(type = Image)
    layer:StringProperty(default = 'color')  # NOTE Idk should it be int or str for better user experience



class UVProperties(PropertyGroup):
    src_uv:StringProperty(
        name = 'Source UV'
    )
    dst_uv:StringProperty(
        name = 'Destination UV'
    )
    src_image:PointerProperty(
        name = 'Source Image',
        type = Image
    )
    dst_image:PointerProperty(
        name = 'Destination Image',
        type = Image
    )



class MaterialProperties(PropertyGroup):
    width:IntProperty(
        name = 'Width',
        default = 1024,
        min = 1
    )
    height:IntProperty(
        name = 'Height',
        default = 1024,
        min = 1
    )

    bake_albedo:BoolProperty(
        name = 'Bake Albedo',
        default = True
    )
    albedo_suffix:StringProperty(
        name = 'Albedo Suffix',
        default = '_c'
    )
    bake_roughness:BoolProperty(
        name = 'Bake Roughness',
        default = True
    )
    roughness_suffix:StringProperty(
        name = 'Roughness Suffix',
        default = '_ro'
    )
    bake_smooth:BoolProperty(
        name = 'Bake Smooth',
        default = True
    )
    smooth_suffix:StringProperty(
        name = 'Smooth Suffix',
        default = '_s'
    )
    bake_metal:BoolProperty(
        name = 'Bake Metal',
        default = True
    )
    metal_suffix:StringProperty(
        name = 'Metal Suffix',
        default = '_m'
    )
    bake_metal_roughness:BoolProperty(
        name = 'Bake Metal-Roughness',
        default = True
    )
    metal_roughness_suffix:StringProperty(
        name = 'Metal-Roughness Suffix',
        default = '_mr'
    )
    bake_metal_smooth:BoolProperty(
        name = 'Bake Metal-Smooth',
        default = True
    )
    metal_smooth_suffix:StringProperty(
        name = 'Metal-Smooth Suffix',
        default = '_ms'
    )
    bake_normal:BoolProperty(
        name = 'Bake Normal',
        default = True
    )
    normal_suffix:StringProperty(
        name = 'Normal Suffix',
        default = '_n'
    )
    bake_emission:BoolProperty(
        name = 'Bake Emission',
        default = True
    )
    emission_suffix:StringProperty(
        name = 'Emission Suffix',
        default = '_e'
    )

    preset:EnumProperty(
        name = 'Combine Preset',
        items = [
            ('ALL', 'All PBR', '', 1),
            ('UNITY', 'Unity', '', 2),
            ('CUSTOM', 'Custom', '', 3),
        ],
        get = lambda self: self.get_preset(),
        set = lambda self, v: self.set_preset(v)
    )

    def is_all(self):
        if not self.bake_albedo: return False
        if not self.bake_roughness: return False
        if not self.bake_smooth: return False
        if not self.bake_metal: return False
        if not self.bake_metal_roughness: return False
        if not self.bake_metal_smooth: return False
        if not self.bake_normal: return False
        if not self.bake_emission: return False
        return True
    
    def is_unity(self):
        if self.bake_roughness: return False
        if self.bake_smooth: return False
        if self.bake_metal: return False
        if self.bake_metal_roughness: return False
        if not self.bake_metal_smooth: return False
        return True

    def get_preset(self):
        if self.is_all(): return 1
        if self.is_unity(): return 2
        return 3
    
    def set_preset(self, v):
        if v == 1:
            self.bake_albedo = True
            self.bake_roughness = True
            self.bake_smooth = True
            self.bake_metal = True
            self.bake_metal_roughness = True
            self.bake_metal_smooth = True
            self.bake_normal = True
            self.bake_emission = True
        elif v == 2:
            self.bake_roughness = False
            self.bake_smooth = False
            self.bake_metal = False
            self.bake_metal_roughness = False
            self.bake_metal_smooth = True
