bl_info = {
    "name": "Killzone 2 models",
    "author": "other1",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "File > Import",
    "description": "Import Killzone 2 models",
    "category": "Import-Export",
}

import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator
from .importer import load_core


class ImportKillzone2Core(Operator, ImportHelper):
    """Import Killzone 2 PS3 *.core files"""
    bl_idname = "import_scene.killzone2_core"
    bl_label = "Import Killzone 2 PS3 *.core"

    filename_ext = ".core"

    filter_glob: StringProperty(
        default="*.core",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        return load_core(context, self.filepath)


def menu_func_import(self, context):
    self.layout.operator(ImportKillzone2Core.bl_idname, text="Killzone 2 *.core")


def register():
    bpy.utils.register_class(ImportKillzone2Core)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportKillzone2Core)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
