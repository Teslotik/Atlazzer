import subprocess
import os, sys
from typing import List

import bpy
from bpy.types import Image

from . import constant


def install_module(mod:str, version:str|None, path:str):
    result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--upgrade', f'{mod}=={version}' if version else mod, '--target', f'{path}'
        ],
        stdout = sys.stdout, stderr = sys.stderr,
    )
    return result.returncode == 0

def blender_to_pillow(image:Image):
    import PIL.Image
        
    w, h = image.size
    # Convert into list of pixels to improve performance
    pixels = list(image.pixels)

    if image.channels == 1:
        img = PIL.Image.new('L', (w, h))
        img.putdata([(int(pixels[i] * 255), ) for i in range(0, len(pixels), 1)])
    elif image.channels == 3:
        img = PIL.Image.new('RGB', (w, h))
        img.putdata([(int(pixels[i] * 255), int(pixels[i + 1] * 255), int(pixels[i + 2] * 255)) for i in range(0, len(pixels), 3)])
    elif image.channels == 4:
        img = PIL.Image.new('RGBA', (w, h))
        img.putdata([(int(pixels[i] * 255), int(pixels[i + 1] * 255), int(pixels[i + 2] * 255), int(pixels[i + 3] * 255)) for i in range(0, len(pixels), 4)])
    else:
        raise 'Failed to convert mode'

    # img.show()

    return img

def pillow_to_blender(name:str, image) -> Image:
    import PIL.Image
    image:PIL.Image = image

    w, h = image.size
    pixels = list(image.getdata())

    if image.mode == 'L':
        img = bpy.data.images.new(name, width = w, height = h, alpha = False)
        pixels_float = [(r / 255, ) for r in pixels]
        img.pixels = [channel for pixel in pixels_float for channel in pixel]
    elif image.mode == 'RGB':
        img = bpy.data.images.new(name, width = w, height = h, alpha = False)
        pixels_float = [(r / 255, g / 255, b / 255) for r, g, b in pixels]
        img.pixels = [channel for pixel in pixels_float for channel in pixel]
    elif image.mode == 'RGBA':
        img = bpy.data.images.new(name, width = w, height = h, alpha = True)
        pixels_float = [(r / 255, g / 255, b / 255, a / 255) for r, g, b, a in pixels]
        img.pixels = [channel for pixel in pixels_float for channel in pixel]
    else:
        raise 'Failed to convert mode'
    
    img.update()
    return img