# Killzone 2 and 3 *.core import plugin for Blender

Blender plugin to import Killzone 2 and 3 *.core files  
Tested on Blender 5.0

## Supported assets
- Meshes - imports to Blender mesh objects
- Skeletons - imports to Blender armature objects
- Textures - imports to Blender images (optionally saved on disk)

Animations are not supported since they are in Sony's proprietary EDGE format.

## Notes
- Mesh objects can have multiple UV maps.
- Sometimes assets references other assets outside of their *.core file - these references are not resolved (e.g. some common assets placed in separate files, like characters' skeleton).
