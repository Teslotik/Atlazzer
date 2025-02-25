bl_info = {
    'name': 'Atlazzer',
    'author': 'Sergei S. aka Teslotik',
    'version': (0, 1),
    'blender': (4, 3, 0),
    'location': 'UV Editor -> Atlazzer',
    'description': 'Tools to work with atlas',
    'warning': '',
    'doc_url': '',
    'tracker_url': 'https://discord.gg/duDwM6PjGk',
    'category': 'UV',
}

import os, sys

import bpy
from bpy.types import Object, Mesh, Operator, Menu

from typing import List

from . import constant
from . import prop
from . import operator
from . import panel

classes = [
    prop.AtlasProperties,
    prop.RegionProperties,
    prop.RegionResource,
    
    operator.InstallImageProcessingOperator,
    operator.RegionScaleOperator,
    operator.RegionMoveOperator,
    operator.RegionAddResourceOperator,
    operator.RegionRemoveResourceOperator,
    operator.RegionMoveResourceOperator,
    operator.RegionCalcSizeOperator,
    operator.RegionFindResourcesOperator,
    operator.AtlasScaleOperator,
    operator.AtlasCreateOperator,
    operator.AtlasPackOperator,
    operator.AtlasBakeOperator,
    
    panel.AtlazzerPanel,
    panel.RegionsPanel,
    panel.RegionResourcesList
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.atlas_props = bpy.props.PointerProperty(type = prop.AtlasProperties)
    bpy.types.Mesh.region_props = bpy.props.PointerProperty(type = prop.RegionProperties)
    bpy.types.Mesh.region_resources = bpy.props.CollectionProperty(type = prop.RegionResource)
    bpy.types.Mesh.region_resource_index = bpy.props.IntProperty(default = -1)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Mesh.region_resource_index
    del bpy.types.Mesh.region_resources
    del bpy.types.Mesh.region_props
    del bpy.types.Scene.atlas_props

if __name__ == '__main__':
    register()