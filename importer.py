import bpy
import tempfile
import os
from mathutils import Vector, Quaternion, Matrix
from . import datatypes, decoders, dds
from .core import read_core

def prepare_vertex_array(va: datatypes.VertexArrayResource):
    if hasattr(va, "_is_prepared"):
        return
    
    offset = 0
    for sf in va.stream_fields:
        sf.values = {ve: list() for ve in sf.vertex_elements}
        for _ in range(va.count):
            for ve in sf.vertex_elements:
                value = decoders.decode_vertex_element(va.data, offset, ve)
                offset += decoders.VERTEX_ELEMENT_SIZES[datatypes.EVertexElementStorageType(ve.type)] * ve.num_components
                sf.values[ve].append(value)

    va._is_prepared = True

def prepare_index_array(ia: datatypes.IndexArrayResource):
    if hasattr(ia, "indices"):
        return
    
    ia.indices = [decoders.decode_triangle(ia.data, 6*i) for i in range(ia.count//3)]
    ia.data = None

def create_static_mesh_resource(context, sm: datatypes.StaticMeshResource, parent, name_override: str=""):
    primitives = []

    for rp in sm.primitives:
        if not rp or not rp.vertex_array or not rp.index_array:
            continue

        prepare_vertex_array(rp.vertex_array)
        prepare_index_array(rp.index_array)

        polygons = rp.index_array.indices
        max_vtx = max(max(polygons, key=lambda p: max(p)))

        verts = []
        uvs = []

        for sf in rp.vertex_array.stream_fields:
            for ve in sf.vertex_elements:
                if datatypes.EVertexElement.VtxElemUV0 <= ve.vertex_element <= datatypes.EVertexElement.VtxElemUV6:
                    uvs.append(sf.values[ve][rp.index_offset:rp.index_offset+max_vtx+1])
                elif ve.vertex_element == datatypes.EVertexElement.VtxElemPos:
                    verts = sf.values[ve][rp.index_offset:rp.index_offset+max_vtx+1]

        if not verts:
            continue

        if isinstance(verts[0][0], tuple):
            verts = list(map(lambda e: e[0], verts))

        name = rp.name or "RenderingPrimitiveResource"

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], polygons)
        mesh.update(calc_edges=True)

        mat = bpy.data.materials.new(name="Material")
        mesh.materials.append(mat)

        for i, uv_verts in enumerate(uvs):
            uvl = mesh.uv_layers.new(name=f"UV Map {i}")
            for l in mesh.loops:
                uv = uv_verts[l.vertex_index]
                if len(uv) == 4:
                    uv = uv[2:]
                uvl.data[l.index].uv = uv

        obj = bpy.data.objects.new(name, mesh)
        parent.objects.link(obj)

        primitives.append(obj)

    if primitives:
        main_object = primitives[0]
        if len(primitives) > 0:
            context.view_layer.objects.active = main_object
            bpy.ops.object.select_all(action='DESELECT')
            for obj in primitives:
                obj.select_set(True)

            bpy.ops.object.join()
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = None

        main_object.name = name_override or sm.name or "StaticMeshResource"

        return main_object

    return None

def create_regular_skinned_mesh_resource(context, rsm: datatypes.RegularSkinnedMeshResource, parent, name_override: str=""):
    all_verts = []
    all_weight_maps = []

    if rsm.skin_info:
        for p in rsm.skin_info.parts:
            verts = []
            weight_maps = dict()
            all_verts.append(verts)
            all_weight_maps.append(weight_maps)
            for i, vs in enumerate(p.vertices_skin + p.vertices_skin_nbt):
                verts.append((vs.x * rsm.position_bounds_scale[0] + rsm.position_bounds_offset[0],
                              vs.y * rsm.position_bounds_scale[1] + rsm.position_bounds_offset[1],
                              vs.z * rsm.position_bounds_scale[2] + rsm.position_bounds_offset[2]))
                if vs.bone0:
                    bone_weights = weight_maps.get(vs.bone0)
                    if not bone_weights:
                        bone_weights = []
                        weight_maps[vs.bone0] = bone_weights

                    bone_weights.append((i, vs.weight0 / 255))
                if vs.bone1:
                    bone_weights = weight_maps.get(vs.bone1)
                    if not bone_weights:
                        bone_weights = []
                        weight_maps[vs.bone1] = bone_weights

                    bone_weights.append((i, vs.weight1 / 255))
                if vs.bone2:
                    bone_weights = weight_maps.get(vs.bone2)
                    if not bone_weights:
                        bone_weights = []
                        weight_maps[vs.bone2] = bone_weights

                    bone_weights.append((i, (255 - vs.weight0 - vs.weight1) / 255))

    primitives = []

    for i, rp in enumerate(rsm.primitives):
        if not rp:
            continue

        verts = all_verts[i]
        polygons = []
        uvs = []
        max_vtx = -2

        if rp.index_array:
            prepare_index_array(rp.index_array)
            polygons = rp.index_array.indices
            max_vtx = max(max(polygons, key=lambda p: max(p)))

        if rp.vertex_array:
            prepare_vertex_array(rp.vertex_array)
            for sf in rp.vertex_array.stream_fields:
                for ve in sf.vertex_elements:
                    if datatypes.EVertexElement.VtxElemUV0 <= ve.vertex_element <= datatypes.EVertexElement.VtxElemUV6:
                        uvs.append(sf.values[ve][rp.index_offset:rp.index_offset+max_vtx+1])

        name = rp.name or "RenderingPrimitiveResource"

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], polygons)
        mesh.update(calc_edges=True)

        mat = bpy.data.materials.new(name="Material")
        mesh.materials.append(mat)

        for j, uv_verts in enumerate(uvs):
            uvl = mesh.uv_layers.new(name=f"UV Map {j}")
            for l in mesh.loops:
                uv = uv_verts[l.vertex_index]
                if len(uv) == 4:
                    uv = uv[2:]
                uvl.data[l.index].uv = uv

        obj = bpy.data.objects.new(name, mesh)
        parent.objects.link(obj)

        weight_maps = all_weight_maps[i]

        bone_names = (rsm.skinned_mesh_bone_bindings and rsm.skinned_mesh_bone_bindings.bone_names) or (rsm.skeleton and rsm.skeleton.bone_names)

        if bone_names:
            for bone_index, weights in weight_maps.items():
                bone_name = bone_names[bone_index]
                vg = obj.vertex_groups.new(name=bone_name)
                for vtx, weight in weights:
                    vg.add([vtx], weight, "ADD")

        primitives.append(obj)

    arm = None
    if rsm.skeleton:
        arm = create_resource(context, rsm.skeleton, context.scene.collection)

    if primitives:
        main_object = primitives[0]
        if len(primitives) > 0:
            context.view_layer.objects.active = main_object
            bpy.ops.object.select_all(action='DESELECT')
            for obj in primitives:
                obj.select_set(True)

            bpy.ops.object.join()
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = None

        main_object.name = name_override or rsm.name or "RegularSkinnedMeshResource"

        if arm:
            mod = main_object.modifiers.new(name="Armature", type="ARMATURE")
            mod.object = arm

        return main_object
    
    return None

def create_lod_mesh_resource(context, lmr: datatypes.LodMeshResource, parent, name_override: str=""):
    col = bpy.data.collections.new(name_override or lmr.name or "LodMeshResource")
    parent.children.link(col)

    for i, part in enumerate(lmr.meshes):
        if not part.mesh:
            continue

        create_resource(context, part.mesh, col, f"LOD {i}")

    return col

def create_multi_mesh_resource(context, mmr: datatypes.MultiMeshResource, parent, name_override: str=""):
    col = bpy.data.collections.new(name_override or mmr.name or "MultiMeshResource")
    parent.children.link(col)

    for i, part in enumerate(mmr.parts):
        if not part.mesh:
            continue

        create_resource(context, part.mesh, col, f"Part {i}")

    return col

def create_switch_mesh_resource(context, smr: datatypes.SwitchMeshResource, parent, name_override: str=""):
    col = bpy.data.collections.new(name_override or smr.name or "SwitchMeshResource")
    parent.children.link(col)

    for p in smr.parts:
        if not p.mesh:
            continue

        create_resource(context, p.mesh, col, p.key)

    return col

def create_skeleton(context, s: datatypes.Skeleton, parent, name_override: str = "", *, bindings: datatypes.SkinnedMeshBoneBindings=None):
    name = name_override or s.name or "Skeleton"

    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    parent.objects.link(obj)

    context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    arm.display_type = "STICK"

    bind_matrices = None
    if bindings:
        bind_matrices = {name: bindings.inverse_bind_matrices[i] for i, name in enumerate(bindings.bone_names)}

    for b in s.bones:
        bone = arm.edit_bones.new(b.name)
        bone.head = (0, 0, 0)
        bone.tail = (0, 0.001, 0)

        if bind_matrices:
            mat = Matrix(bind_matrices[b.name]).inverted()
            mat[0][3], mat[3][0] = mat[3][0], mat[0][3]
            mat[1][3], mat[3][1] = mat[3][1], mat[1][3]
            mat[2][3], mat[3][2] = mat[3][2], mat[2][3]
        else:
            pos = Vector(b.position)
            rot = Quaternion((b.rotation[3], b.rotation[0], b.rotation[1], b.rotation[2]))
            mat = rot.to_matrix().to_4x4()
            mat.translation = pos

            if b.parent_name:
                mat = arm.edit_bones[b.parent_name].matrix @ mat

        bone.matrix = mat

        if b.parent_name:
            bone.parent = arm.edit_bones[b.parent_name]

    bpy.ops.object.mode_set(mode="OBJECT")
    context.view_layer.objects.active = None

    return obj

def create_texture(context, tex: datatypes.Texture):
    path = os.path.join(tempfile.gettempdir(), tex.id + ".dds")
    dds.make_dds(tex, path)

    img = bpy.data.images.load(filepath=path)
    img.pack()

    os.remove(path)

    return img

CREATED_OBJECTS = dict()
def create_resource(context, obj, parent, name_override: str = ""):
    result = CREATED_OBJECTS.get(obj)
    if result:
        return result
    
    match type(obj):
        case datatypes.SwitchMeshResource:
            result = create_switch_mesh_resource(context, obj, parent, name_override)
        case datatypes.MultiMeshResource:
            result = create_multi_mesh_resource(context, obj, parent, name_override)
        case datatypes.LodMeshResource:
            result = create_lod_mesh_resource(context, obj, parent, name_override)
        case datatypes.StaticMeshResource:
            result = create_static_mesh_resource(context, obj, parent, name_override)
        case datatypes.RegularSkinnedMeshResource:
            result = create_regular_skinned_mesh_resource(context, obj, parent, name_override)
        case datatypes.Skeleton:
            result = create_skeleton(context, obj, parent, name_override)
        case datatypes.Texture:
            result = create_texture(context, obj)
        case _:
            return
        
    CREATED_OBJECTS[obj] = result

    return result

PRIORITIES = {
    datatypes.SwitchMeshResource: 0,
    datatypes.MultiMeshResource: 1,
    datatypes.LodMeshResource: 2,
    datatypes.RegularSkinnedMeshResource: 3,
    datatypes.StaticMeshResource: 3,
    datatypes.Skeleton: 4,
    datatypes.Texture: 10,
}

def load_core(context, filepath: str):
    CREATED_OBJECTS.clear()

    ctx = read_core(filepath)

    for obj in sorted(ctx.objects, key=lambda e: PRIORITIES.get(e.__class__, 10)):
        if obj.__class__ not in PRIORITIES:
            continue

        obj.parse(ctx)

        create_resource(context, obj, context.scene.collection)

    return {"FINISHED"}