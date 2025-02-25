import bpy
from bpy.types import PropertyGroup, SpaceView3D, SpaceImageEditor, Scene, Image
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
    pack_analysis_time:IntProperty(
        name = 'Pack Analysis Time',
        default = 5,
        min = 0
    )
    pack_scale:BoolProperty(
        name = 'Pack Scale',
        default = True
    )
    pack_metric:EnumProperty(
        name = 'Pack Metric',
        items = [
            ('SQUARE', 'Square', '', 1),
            ('OCCUPIED', 'Occupied', '', 2)
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
    xx:IntProperty(name = 'x', set = lambda self, v: setattr(self, 'x', v / bpy.context.space_data.image.size[0]), get = lambda self: round(self.x * bpy.context.space_data.image.size[0]))
    xy:IntProperty(name = 'y', set = lambda self, v: setattr(self, 'y', v / bpy.context.space_data.image.size[1]), get = lambda self: round(self.y * bpy.context.space_data.image.size[1]))
    xw:IntProperty(name = 'w', set = lambda self, v: setattr(self, 'w', v / bpy.context.space_data.image.size[0]), get = lambda self: round(self.w * bpy.context.space_data.image.size[0]))
    xh:IntProperty(name = 'h', set = lambda self, v: setattr(self, 'h', v / bpy.context.space_data.image.size[1]), get = lambda self: round(self.h * bpy.context.space_data.image.size[1]))
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