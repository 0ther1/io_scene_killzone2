import bpy
import _bpy_types
import tempfile
import os
from mathutils import Vector, Quaternion, Matrix
from . import datatypes, decoders, dds
from .core import read_core

VERSION = 0

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

def apply_bindings_to_armature(context, obj, arm_obj, bindings: datatypes.SkinnedMeshBoneBindings):
    context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)
    bpy.ops.object.duplicate()
    copy_arm = context.view_layer.objects.active

    bpy.ops.object.mode_set(mode='EDIT')

    for i, name in enumerate(bindings.bone_names):
        copy_arm.data.edit_bones[name].matrix = Matrix(bindings.inverse_bind_matrices[i]).transposed().inverted()

    bpy.ops.object.mode_set(mode='OBJECT')

    for arm in (obj for obj in bpy.data.objects if obj.type == "ARMATURE" and len(obj.data.bones) == len(copy_arm.data.bones) and obj is not copy_arm):
        equals = True
        for b in arm.data.bones:
            other_bone = copy_arm.data.bones.get(b.name)
            if other_bone is None or b.matrix_local != other_bone.matrix_local:
                equals = False
                break

        if equals:
            bpy.data.objects.remove(copy_arm, do_unlink=True)
            copy_arm = arm
            break

    mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = copy_arm

def apply_render_effect(mat, fx: datatypes.RenderEffectResource):
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    links = mat.node_tree.links
        
    for rt in fx.render_techniques:
        for tb in rt.texture_bindings:
            if not isinstance(tb.texture, datatypes.Texture):
                continue

            if tb.sampler == "inSampler0":
                tex_image = nodes.new(type="ShaderNodeTexImage")
                tex_image.image = CREATED_OBJECTS[tb.texture]

                links.new(tex_image.outputs["Color"], bsdf.inputs["Base Color"])

def create_static_mesh_resource(context, sm: datatypes.StaticMeshResource, parent, name_override: str="", **kwargs):
    primitives = []

    for rp in sm.primitives:
        if not isinstance(rp, datatypes.RenderingPrimitiveResource) or not isinstance(rp.vertex_array, datatypes.VertexArrayResource) or not isinstance(rp.index_array, datatypes.IndexArrayResource):
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

        if not verts or not polygons:
            continue

        if isinstance(verts[0][0], tuple):
            verts = list(map(lambda e: e[0], verts))

        name = "RenderingPrimitiveResource"

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], polygons)
        mesh.update(calc_edges=True)

        mat = bpy.data.materials.new(name="Material")
        mesh.materials.append(mat)

        if isinstance(rp.render_effects, datatypes.RenderEffectResource):
            apply_render_effect(mat, rp.render_effects)

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
        if len(primitives) > 1:
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

def create_regular_skinned_mesh_resource(context, rsm: datatypes.RegularSkinnedMeshResource, parent, name_override: str="", *, apply_bindings: bool=False, **kwargs):
    arm = None
    bindings = None
    binding_required = False

    if rsm.skeleton:
        bindings = (isinstance(rsm.skinned_mesh_bone_bindings, datatypes.SkinnedMeshBoneBindings) and rsm.skinned_mesh_bone_bindings) or None
        binding_required = apply_bindings and bindings != None
        if isinstance(rsm.skeleton, datatypes.Skeleton):
            arm = create_resource(context, rsm.skeleton, context.scene.collection)
        elif isinstance(rsm.skeleton, str):
            for o in bpy.data.objects:
                if o.type == "ARMATURE" and o.get("kz_id") == rsm.skeleton:
                    arm = o
                    break

    all_verts = []
    all_weight_maps = []

    if isinstance(rsm.skin_info, datatypes.RegularSkinnedMeshResourceSkinInfo):
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
        if not isinstance(rp, datatypes.RenderingPrimitiveResource):
            continue

        verts = all_verts[i]

        if not verts:
            continue

        polygons = []
        uvs = []
        max_vtx = -2

        if isinstance(rp.index_array, datatypes.IndexArrayResource):
            prepare_index_array(rp.index_array)
            polygons = rp.index_array.indices
            max_vtx = max(max(polygons, key=lambda p: max(p)))

        if isinstance(rp.vertex_array, datatypes.VertexArrayResource):
            prepare_vertex_array(rp.vertex_array)
            for sf in rp.vertex_array.stream_fields:
                for ve in sf.vertex_elements:
                    if datatypes.EVertexElement.VtxElemUV0 <= ve.vertex_element <= datatypes.EVertexElement.VtxElemUV6:
                        uvs.append(sf.values[ve][rp.index_offset:rp.index_offset+max_vtx+1])

        name = "RenderingPrimitiveResource"

        if not polygons:
            continue

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], polygons)
        mesh.update(calc_edges=True)

        mat = bpy.data.materials.new(name="Material")
        mesh.materials.append(mat)

        if isinstance(rp.render_effects, datatypes.RenderEffectResource):
            apply_render_effect(mat, rp.render_effects)

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

        bone_names = (isinstance(rsm.skinned_mesh_bone_bindings, datatypes.SkinnedMeshBoneBindings) and rsm.skinned_mesh_bone_bindings.bone_names) or (arm and [b.name for b in arm.data.bones])

        if bone_names:
            for bone_index, weights in weight_maps.items():
                bone_name = bone_names[bone_index]
                vg = obj.vertex_groups.new(name=bone_name)
                for vtx, weight in weights:
                    vg.add([vtx], weight, "ADD")

        primitives.append(obj)

    if primitives:
        main_object = primitives[0]
        if len(primitives) > 1:
            context.view_layer.objects.active = main_object
            bpy.ops.object.select_all(action='DESELECT')
            for obj in primitives:
                obj.select_set(True)

            bpy.ops.object.join()
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = None

        main_object.name = name_override or rsm.name or "RegularSkinnedMeshResource"

        if arm:
            if binding_required:
                apply_bindings_to_armature(context, main_object, arm, bindings)
            else:
                mod = main_object.modifiers.new(name="Armature", type="ARMATURE")
                mod.object = arm

        for i, fx in enumerate(rsm.render_effects):
            if not isinstance(fx, datatypes.RenderEffectResource):
                continue

            mat = main_object.data.materials[i]
            apply_render_effect(mat, fx)

        return main_object
    
    return None

def create_lod_mesh_resource(context, lmr: datatypes.LodMeshResource, parent, name_override: str="", **kwargs):
    valid_parts = [p for p in lmr.meshes if isinstance(p.mesh, datatypes.MeshResourceBase) and p.mesh not in CREATED_OBJECTS]

    if not valid_parts:
        return None
    elif len(valid_parts) == 1:
        return create_resource(context, valid_parts[0].mesh, parent, name_override or lmr.name or "LodMeshResource", **kwargs)

    col = bpy.data.collections.new(name_override or lmr.name or "LodMeshResource")
    parent.children.link(col)

    for i, part in enumerate(valid_parts):
        create_resource(context, part.mesh, col, f"LOD {i}", **kwargs)

    return col

def create_multi_mesh_resource(context, mmr: datatypes.MultiMeshResource, parent, name_override: str="", **kwargs):
    valid_parts = [p for p in mmr.parts if isinstance(p.mesh, datatypes.MeshResourceBase) and p.mesh not in CREATED_OBJECTS]

    if not valid_parts:
        return None
    elif len(valid_parts) == 1:
        return create_resource(context, valid_parts[0].mesh, parent, name_override or mmr.name or "MultiMeshResource", **kwargs)

    col = bpy.data.collections.new(name_override or mmr.name or "MultiMeshResource")
    parent.children.link(col)

    for i, part in enumerate(valid_parts):
        create_resource(context, part.mesh, col, f"Part {i}", **kwargs)

    return col

def create_switch_mesh_resource(context, smr: datatypes.SwitchMeshResource, parent, name_override: str="", **kwargs):
    valid_parts = [p for p in smr.parts if isinstance(p.mesh, datatypes.MeshResourceBase) and p.mesh not in CREATED_OBJECTS]

    if not valid_parts:
        return None
    elif smr.parts_use_the_same_mesh or len(valid_parts) == 1:
        return create_resource(context, valid_parts[0].mesh, parent, name_override or smr.name or p.key, **kwargs)
    
    col = bpy.data.collections.new(name_override or smr.name or "SwitchMeshResource")
    parent.children.link(col)

    for p in valid_parts:
        create_resource(context, p.mesh, col, p.key, **kwargs)

    return col

def create_skeleton(context, s: datatypes.Skeleton, parent, name_override: str = "", **kwargs):
    name = name_override or s.name or "Skeleton"

    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    obj["kz_id"] = s.id
    parent.objects.link(obj)

    context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    arm.display_type = "STICK"

    for j in s.joints:
        bone = arm.edit_bones.new(j.name)
        bone.head = (0, 0, 0)
        bone.tail = (0, 0.001, 0)

        parent = (j.parent_index > -1 and arm.edit_bones[j.parent_index]) or (j.parent_name and arm.edit_bones[j.parent_name]) or None

        pos = Vector(j.translation)
        rot = Quaternion((j.rotation[3], j.rotation[0], j.rotation[1], j.rotation[2]))
        mat = rot.to_matrix().to_4x4()
        mat.translation = pos

        if parent:
            mat = parent.matrix @ mat

        bone.matrix = mat
        bone.parent = parent

    bpy.ops.object.mode_set(mode="OBJECT")
    context.view_layer.objects.active = None

    for a in (o for o in bpy.data.objects if o.type == "ARMATURE" and len(o.data.bones) == len(obj.data.bones) and o is not obj):
        equals = True
        for b in a.data.bones:
            other_bone = obj.data.bones.get(b.name)
                
            if other_bone is None or b.matrix_local != other_bone.matrix_local:
                equals = False
                break

        if equals:
            bpy.data.objects.remove(obj, do_unlink=True)
            obj = a
            break

    return obj

def create_texture(context, tex: datatypes.Texture, *, textures_dir: str="", **kwargs):
    if tex.format.height == 1:
        return None
    
    if textures_dir:
        path = os.path.join(textures_dir, tex.id + ".dds")
    else:
        path = os.path.join(tempfile.gettempdir(), tex.id + ".dds")

    dds.make_dds(tex, path, VERSION)

    img = bpy.data.images.load(filepath=path)

    if not textures_dir:
        img.pack()
        os.remove(path)

    return img

CREATED_OBJECTS = dict()
def create_resource(context, obj, parent, name_override: str = "", **kwargs):
    result = CREATED_OBJECTS.get(obj)

    if result:
        if parent is not context.scene.collection:
            if isinstance(result, _bpy_types.Collection):
                if result.name not in parent.children:
                    parent.children.link(result)
            elif isinstance(result, _bpy_types.Object):
                if result.name not in parent.objects:
                    parent.objects.link(result)

        return result
    
    match type(obj):
        case datatypes.SwitchMeshResource:
            result = create_switch_mesh_resource(context, obj, parent, name_override, **kwargs)
        case datatypes.MultiMeshResource:
            result = create_multi_mesh_resource(context, obj, parent, name_override, **kwargs)
        case datatypes.LodMeshResource:
            result = create_lod_mesh_resource(context, obj, parent, name_override, **kwargs)
        case datatypes.StaticMeshResource:
            result = create_static_mesh_resource(context, obj, parent, name_override, **kwargs)
        case datatypes.RegularSkinnedMeshResource:
            result = create_regular_skinned_mesh_resource(context, obj, parent, name_override, **kwargs)
        case datatypes.Skeleton:
            result = create_skeleton(context, obj, parent, name_override, **kwargs)
        case datatypes.Texture:
            result = create_texture(context, obj, **kwargs)
        case _:
            return
        
    CREATED_OBJECTS[obj] = result

    return result

PRIORITIES = {
    datatypes.Texture: 0,
    datatypes.MultiMeshResource: 1,
    datatypes.SwitchMeshResource: 2,
    datatypes.LodMeshResource: 3,
    datatypes.RegularSkinnedMeshResource: 4,
    datatypes.StaticMeshResource: 5,
    datatypes.Skeleton: 6,
}

def load_core(context, filepath: str, save_textures: bool, apply_bindings: bool):
    CREATED_OBJECTS.clear()

    textures_dir = ""
    if save_textures:
        basename = os.path.splitext(os.path.basename(filepath))[0]
        textures_dir = os.path.join(os.path.dirname(filepath), f"{basename}_textures")
        os.makedirs(textures_dir)

    ctx = read_core(filepath)

    global VERSION
    VERSION = ctx.version

    objects = sorted([obj for obj in ctx.objects if obj.__class__ in PRIORITIES], key=lambda e: PRIORITIES[e.__class__])

    try:
        for obj in objects:
            obj.parse(ctx)

            create_resource(context, obj, context.scene.collection, textures_dir=textures_dir, apply_bindings=apply_bindings)
    finally:
        if ctx.stream_file:
            ctx.stream_file.close()

    return {"FINISHED"}