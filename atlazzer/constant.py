import os, sys

DEBUG = False

modules_path = os.path.join(os.path.dirname(__file__), 'modules')

# label: (module, version, folder)
image_processing = {
    'Pillow': ('Pillow', '11.1.0', 'PIL')
}

sys.path.append(modules_path)

# Checks whether folders exists
def is_image_processing_installed():
    return all(os.path.isdir(os.path.join(modules_path, i[2])) for i in image_processing.values())