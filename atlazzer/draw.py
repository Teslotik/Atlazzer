from typing import Callable, List

import bpy
from bpy.types import Object
import gpu
from gpu.types import GPUVertFormat, GPUVertBuf, GPUIndexBuf, GPUShader
from gpu_extras.batch import batch_for_shader
from mathutils import Color, Vector

class Painter:
    @staticmethod
    def uvsquare(objects, thickness = 1):
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        def draw():
            for obj in objects:
                props = obj.data.region_props
                x = props.x
                y = props.y
                w = props.w
                h = props.h
                coords = [
                    (x,     y,     0), (x + w, y,     0),
                    (x + w, y,     0), (x + w, y + h, 0),
                    (x + w, y + h, 0), (x,     y + h, 0),
                    (x,     y + h, 0), (x,     y,     0),
                ]
                batch = batch_for_shader(shader, 'LINES', {'pos': coords})
                
                h = hash(obj.name)
                shader.uniform_float('color', Vector((
                    (h & 0xFF) / 255,
                    ((h >> 8) & 0xFF) / 255,
                    ((h >> 16) & 0xFF) / 255,
                    1
                )).normalized())
                
                gpu.state.line_width_set(thickness)
                batch.draw(shader)
        return draw