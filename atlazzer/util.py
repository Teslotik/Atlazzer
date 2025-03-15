import subprocess
import os, sys
from typing import List
import re

import bpy
from bpy.types import Image

from . import constant
from . import struct

gamma_table = [int((i / 255) ** (1.0 / 2.2) * 255) for i in range(256)]
gamma_table_inv = [int((i / 255) ** 2.2 * 255) for i in range(256)]

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

def pillow_to_blender(name:str|None, image, override = False, colorspace = 'sRGB') -> Image:
    import PIL.Image
    image:PIL.Image = image

    w, h = image.size
    pixels = list(image.getdata())

    img = bpy.data.images.get(name) if override else None
    if image.mode == 'L':
        img = img or bpy.data.images.new(name, width = w, height = h, alpha = False)
        img.colorspace_settings.name = colorspace
        pixels_float = [(min(max(r / 255, 0), 1), ) for r in pixels]
        img.pixels = [channel for pixel in pixels_float for channel in pixel]
    elif image.mode == 'RGB':
        img = img or bpy.data.images.new(name, width = w, height = h, alpha = False)
        img.colorspace_settings.name = colorspace
        pixels_float = [(min(max(r / 255, 0), 1), min(max(g / 255, 0), 1), min(max(b / 255, 0), 1)) for r, g, b in pixels]
        img.pixels = [channel for pixel in pixels_float for channel in pixel]
    elif image.mode == 'RGBA':
        img = img or bpy.data.images.new(name, width = w, height = h, alpha = True)
        img.colorspace_settings.name = colorspace
        pixels_float = [(min(max(r / 255, 0), 1), min(max(g / 255, 0), 1), min(max(b / 255, 0), 1), min(max(a / 255, 0), 1)) for r, g, b, a in pixels]
        img.pixels = [channel for pixel in pixels_float for channel in pixel]
    else:
        raise 'Failed to convert mode'
    
    assert len(img.pixels) == img.size[0] * img.size[1] * img.channels

    img.update()
    return img

def apply_gamma_correction(image):
    assert(image.mode == 'L')
    return image.point(gamma_table)

def revert_gamma_correction(image):
    assert(image.mode == 'L')
    return image.point(gamma_table_inv)

def pack_shelf_decreasing_high(rects, w:float):
    if not rects: return

    # Sort
    rects.sort(key = lambda r: r.h, reverse = True)

    # Pack
    dx = 0
    dy = 0
    size = rects[0].h
    inrow = 0
    for i, rect in enumerate(rects):
        if inrow and dx + rect.w > w:
            dx = 0
            dy += size
            size = rect.h
            inrow = 0
        else:
            inrow += 1
        rect.x = dx
        rect.y = dy
        dx += rect.w
    
    return rects

# {name}, a
# a{index}, a012
# {name}*, abc
# *{name}, bca
def apply_fitler(string:str, pattern:str, **kwargs):
    if not pattern: return string
    for item in re.findall(r'\{(.*?)\}', pattern):
        if item == 'index': continue
        pattern = pattern.replace('{' + item + '}', kwargs.get(item, ''))
    pattern = pattern.replace('{index}', r'\d{,}')
    pattern = pattern.replace('*', r'.{,}?')
    return bool(re.fullmatch(pattern, string))
