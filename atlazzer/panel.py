import bpy
from bpy.types import Panel, UIList, UILayout, Context
from bpy.props import BoolProperty, EnumProperty

from . import constant

class AtlazzerPanel(Panel):
    bl_idname = 'ATLAZZER_PT_main'
    bl_label = 'Atlazzer'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Atlazzer'

    def draw(self, context:Context):
        layout:UILayout = self.layout

        if not constant.DEBUG and not constant.is_image_processing_installed():
            col = layout.column()
            col.label(text = 'First, you MUST install image processing library')
            col.operator('wm.install_image_processing')
            return

        region_props = context.scene.atlas_props
        layout.prop(region_props, 'draw_regions')

        layout.label(text = 'Atlas Size')
        row = layout.row()
        group = row.row(align = True)
        group.prop(context.scene.atlas_props, 'atlas_w', text = '')
        group.prop(context.scene.atlas_props, 'atlas_h', text = '')
        group = row.row(align = True)
        op = group.operator('atlas.scale', text = '0.5')
        op.factor = 0.5
        op = group.operator('atlas.scale', text = '2.0')
        op.factor = 2.0

        col = layout.column(align = True)
        col.operator('atlas.create', text = '1. Create Atlas')
        col.operator('region.find_resources', text = '2. Find Images')
        col.operator('region.calc_all_sizes', text = '3. Calc All Sizes')
        pack = col.column(align = True)
        pack.prop(context.scene.atlas_props, 'pack_algorithm')
        if context.scene.atlas_props.pack_algorithm in ('SQUARE', 'OCCUPIED'):
            heuristic = pack.operator('atlas.pack_heuristic', text = '4. Pack Atlas Heuristic')
            pack.prop(context.scene.atlas_props, 'pack_analysis_time')
            pack.prop(context.scene.atlas_props, 'pack_scale')
            heuristic.time = context.scene.atlas_props.pack_analysis_time
            heuristic.scale = context.scene.atlas_props.pack_scale
            heuristic.metric = context.scene.atlas_props.pack_algorithm
        elif context.scene.atlas_props.pack_algorithm == '2048':
            pack.operator('atlas.pack_2048', text = '4. Pack Atlas 2048')
        elif context.scene.atlas_props.pack_algorithm == 'SHELF':
            pack.operator('atlas.pack_shelf', text = '4. Pack Atlas Shelf')
        col.operator('atlas.bake', text = '5. Bake Atlas')
        col.operator('atlas.replace_resources', text = '6. Replace Images By Atlas')

        layout.prop(context.scene.atlas_props, 'export')



class RegionsPanel(Panel):
    bl_idname = 'ATLAZZER_PT_regions'
    bl_parent_id = 'ATLAZZER_PT_main'
    bl_label = 'Regions'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Atlazzer'

    def draw(self, context:Context):
        layout:UILayout = self.layout

        if not constant.DEBUG and not constant.is_image_processing_installed():
            return

        if bpy.context.space_data.image is not None:
            layout.prop(context.scene.atlas_props, 'units')

        for obj in bpy.context.selected_objects:
            if obj.type != 'MESH': continue

            box = layout.box()
            box.label(text = obj.name)
            
            # Position and size
            if context.mode == 'OBJECT':
                row = box.row()
                if context.scene.atlas_props.units == 'RELATIVE' or bpy.context.space_data.image is None:
                    # x, y
                    pos = row.row(align = True)
                    pos.prop(obj.data.region_props, 'x')
                    pos.prop(obj.data.region_props, 'y')
                    # w, h
                    size = row.row(align = True)
                    size.prop(obj.data.region_props, 'w')
                    size.prop(obj.data.region_props, 'h')
                else:
                    # x, y
                    pos = row.row(align = True)
                    pos.prop(obj.data.region_props, 'xx')
                    pos.prop(obj.data.region_props, 'xy')
                    # w, h
                    size = row.row(align = True)
                    size.prop(obj.data.region_props, 'xw')
                    size.prop(obj.data.region_props, 'xh')

                move = row.operator('region.move', text = '', icon = 'VIEW_PAN')
                move.target = obj.name
            
            # Scale uv
            row = box.row(align = True)
            op = row.operator('region.scale', text = f'0.25')
            op.target = obj.name
            op.factor = 0.25
            op = row.operator('region.scale', text = f'0.5')
            op.target = obj.name
            op.factor = 0.5
            op = row.operator('region.scale', text = f'0.75')
            op.target = obj.name
            op.factor = 0.75
            op = row.operator('region.scale', text = f'{1 / 0.75}')
            op.target = obj.name
            op.factor = 1 / 0.75
            op = row.operator('region.scale', text = f'{1 / 0.5}')
            op.target = obj.name
            op.factor = 1 / 0.5
            op = row.operator('region.scale', text = f'{1 / 0.25}')
            op.target = obj.name
            op.factor = 1 / 0.25

            op = box.operator('region.calc_size')
            op.target = obj.name

            # Textures list
            row = box.row()
            col = row.column()
            col.template_list('ATLAZZER_UL_region_resources', 'compact', obj.data, 'region_resources', obj.data, 'region_resource_index')
            controls = row.column()
            col = controls.column(align = True)
            add = col.operator('region.add_resource', icon = 'ADD', text = '')
            add.target = obj.name
            remove = col.operator('region.remove_resource', icon = 'REMOVE', text = '')
            remove.target = obj.name
            col = controls.column(align = True)
            up = col.operator('region.move_resource', icon = 'TRIA_UP', text = '')
            up.target = obj.name
            up.up = True
            down = col.operator('region.move_resource', icon = 'TRIA_DOWN', text = '')
            down.target = obj.name
            down.up = False




class RegionResourcesList(UIList):
    bl_idname = 'ATLAZZER_UL_region_resources'

    def draw_item(self, context:Context, layout:UILayout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            grid = layout.grid_flow(columns = 2, even_columns = True)
            grid.prop(item, 'layer', text = '', icon = 'RENDERLAYERS')
            grid.prop(item, 'image', text = '', icon = 'IMAGE_DATA')



def menu_VIEW3D_MT_uv_map(self, context):
	layout = self.layout
	layout.separator()
	layout.operator("uv.unwrap_polygons")



class AtlazzerUVPanel(Panel):
    bl_idname = 'ATLAZZER_PT_uv'
    bl_label = 'Atlazzer UV'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Atlazzer UV'

    def draw(self, context:Context):
        layout:UILayout = self.layout

        layout.operator('uv.pack_rect')

        if not constant.DEBUG and not constant.is_image_processing_installed():
            col = layout.column()
            col.label(text = 'First, you MUST install image processing library')
            col.operator('wm.install_image_processing')
            return
        
        if context.active_object and context.active_object.type == 'MESH':
            col = layout.column(align = True)
            col.operator('uv.transfer_image')
            row = col.row(align = True)
            row.prop(context.active_object.data.uv_props, 'src_uv')
            row.prop(context.active_object.data.uv_props, 'src_image')
            row = col.row(align = True)
            row.prop(context.active_object.data.uv_props, 'dst_uv')
            row.prop(context.active_object.data.uv_props, 'dst_image')
            col.label(text = 'WARNING! Only works for separate uv islands without connections!')



class AtlazzerMaterialPanel(Panel):
    bl_idname = 'ATLAZZER_PT_material'
    bl_label = 'Atlazzer Material'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Atlazzer Material'

    def draw(self, context:Context):
        layout:UILayout = self.layout

        if not constant.DEBUG and not constant.is_image_processing_installed():
            col = layout.column()
            col.label(text = 'First, you MUST install image processing library')
            col.operator('wm.install_image_processing')
            return

        layout.operator('material.bake')
        row = layout.row(align = True)
        row.prop(context.scene.material_props, 'width')
        row.prop(context.scene.material_props, 'height')
        layout.prop(context.scene.material_props, 'preset')
        layout.prop(context.scene.material_props, 'bake_albedo')
        layout.prop(context.scene.material_props, 'bake_roughness')
        layout.prop(context.scene.material_props, 'bake_smooth')
        layout.prop(context.scene.material_props, 'bake_metal')
        layout.prop(context.scene.material_props, 'bake_metal_roughness')
        layout.prop(context.scene.material_props, 'bake_metal_smooth')
        layout.prop(context.scene.material_props, 'bake_normal')
        layout.prop(context.scene.material_props, 'bake_emission')