import subprocess
import os, sys
from typing import List

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
