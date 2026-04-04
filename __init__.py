bl_info = {
    "name": "Killzone 2, 3 models",
    "author": "other1",
    "version": (2, 0),
    "blender": (5, 0, 0),
    "location": "File > Import",
    "description": "Import Killzone 2, 3 models",
    "category": "Import-Export",
}

import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator
from .importer import load_core


class ImportKillzone2Core(Operator, ImportHelper):
    """Import Killzone 2, 3 PS3 *.core files"""
    bl_idname = "import_scene.killzone2_core"
    bl_label = "Import Killzone 2, 3 PS3 *.core"

    filename_ext = ".core"

    filter_glob: StringProperty(
        default="*.core",
        options={'HIDDEN'},
        maxlen=255,
    )

    save_textures: BoolProperty(
        name="Save textures",
        description="Save textures as images",
        default=False,
    )

    apply_bindings: BoolProperty(
        name="Apply skeleton bindings",
        description="Apply bone bindings to fix misaligned rest pose",
        default=True,
    )

    def execute(self, context):
        return load_core(context, self.filepath, self.save_textures, self.apply_bindings)


def menu_func_import(self, context):
    self.layout.operator(ImportKillzone2Core.bl_idname, text="Killzone 2, 3 *.core")


def register():
    bpy.utils.register_class(ImportKillzone2Core)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportKillzone2Core)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
