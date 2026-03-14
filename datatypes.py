from typing import TYPE_CHECKING
from io import BytesIO
from enum import IntEnum
from .reader import Reader

if TYPE_CHECKING:
    from .context import Context
else:
    class Context:
        pass

class BaseObject:
    id: str
    read_size: int
    data_offset: int
    raw_data: bytes
    parsed: bool

    def __init__(self):
        self.id = ""
        self.read_size = 0
        self.data_offset = 0
        self.raw_data = bytes()
        self.parsed = False

    def read(self, r: Reader, ctx: Context):
        self.data_offset = r.tell()
        if self.read_size:
            self.raw_data = r.read(self.read_size)

    def parse(self, ctx: Context):
        if self.parsed:
            return
        
        self._parse(Reader(BytesIO(self.raw_data)), ctx)
        
        self.parsed = True

    def _parse(self, r: Reader, ctx: Context):
        pass

class PhonemeChannel(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(8)
        r.skip(8*r.read_var_int())

class BlendExpression(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(4*r.read_var_int())

class EntityPlaceHolder(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(65)
        ctx.read_string_index(r)
        ctx.read_string_index(r)
        [ctx.read_string_index(r) for _ in range(r.read_var_int())]
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        r.skip(4)

class RenderEffectInstanceImp1(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)     
        ctx.read_object_ref(r)

class Portal(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        r.skip(12*r.read_var_int())
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        r.skip(4)

class Zone(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)    
        ctx.read_string_index(r)
        r.skip(89)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]

class WorldNode(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_object_ref(r)
        r.skip(64)

class AIMarker(WorldNode):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(6)

class GlobalDamageModifier(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        for _ in range(r.read_var_int()):
            ctx.read_string_index(r)
            r.skip(2)
            ctx.read_string_index(r)
            r.skip(4)
            ctx.read_string_index(r)
            r.skip(4)

class DrawableObjectInstance:
    def read(self, r: Reader, ctx: Context):
        r.skip(12)

class GeometryObject(WorldNode, DrawableObjectInstance):
    def read(self, r: Reader, ctx: Context):
        WorldNode.read(self, r, ctx)
        DrawableObjectInstance.read(self, r, ctx)

class MeshHierachyShaderOverrides(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        for _ in range(r.read_var_int()):
            ctx.read_object_ref(r)
            r.skip(r.read_var_int()*4)
            for _ in range(r.read_var_int()):
                ctx.read_object_ref(r)
                for _ in range(r.read_var_int()):
                    ctx.read_string_index(r)
                    ctx.read_object_ref(r)
                    r.skip(4)

                for _ in range(r.read_var_int()):
                    ctx.read_string_index(r)
                    r.skip(20)
                    ctx.read_object_ref(r)

class StaticMeshInstance(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        ctx.read_object_ref(r)
        MeshHierachyShaderOverrides().read(r, ctx)
        r.skip(8)

class Light(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(13)
        ctx.read_object_ref(r)
        r.skip(11)
        ctx.read_object_ref(r)

class LightShadowed(Light):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(32)

class SpotLight(LightShadowed):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(20)
        ctx.read_object_ref(r)

class Camera(WorldNode):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        ctx.read_object_ref(r)
        r.skip(25)

class LumpOptimizationSettings(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)

class LumpOptimizationSettingsGame(LumpOptimizationSettings):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(2)

class LevelAssetInfo(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        for _ in range(r.read_var_int()):
            ctx.read_string_index(r)
            [ctx.read_string_index(r) for _ in range(r.read_var_int())]

class AnimationMotionDirectional(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)        
        r.skip(4)
        r.skip(r.read_var_int()*4)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]

class AnimationMotionCurve(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)       
        r.skip(4)
        r.skip(r.read_var_int()*12) 
        r.skip(r.read_var_int()*4)

class LeanAndPeekPosition(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)        
        r.skip(8)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]

class LeanAndPeekAction(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(80)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        ctx.read_object_ref(r)

class LightingSetupSet(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)    
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        ctx.read_string_index(r)
        r.skip(1)

class LightingSetup(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)             
        ctx.read_string_index(r)
        r.skip(1)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
    
class Shape2D(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        self.name = ctx.read_string_index(r)
        self.name_is_identifier, self.closed = r.unpack(">2?")
        self.points = [r.unpack(">2f") for _ in range(r.read_var_int())]

class Shape2DExtrusion(Shape2D):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        self.height = r.unpack(">f")[0]

class RenderZone(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(12)
        ctx.read_object_ref(r)
        r.skip(45)
        ctx.read_object_ref(r)
        r.skip(4)

class SunCascadeSettings:
    def __init__(self, r: Reader):
        self.filter_tap_count, self.msaa_quality, self.shadow_map_size = r.unpack(">b2i")

class SunLight(Light):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)         
        r.skip(141)

class SoundMixResource(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(r.read_var_int()*4+4)

class AIWaypointNeighbors(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(r.read_var_int()*32)
        r.skip(r.read_var_int()*16)
        r.skip(r.read_var_int()*60)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        ctx.read_string_index(r)
        r.skip(1)

class SkinnedMeshInstance(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        ctx.read_object_ref(r)

class SimpleAnimatingSkinnedMeshInstance(SkinnedMeshInstance):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)       
        ctx.read_object_ref(r) 

class PhysicsInstance(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_object_ref(r)
        r.skip(8)

class PhysicsCollisionInstance(PhysicsInstance):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(97)

class AITerrainManager(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)

class AINearestWaypoint(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)

class CoreScript(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        raise NotImplementedError("Lua script")

class GameScript(CoreScript):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)

class AmbientSoundZone(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(12)

class CollisionInstance(WorldNode):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)
        ctx.read_string_index(r)
        r.skip(2)
        ctx.read_object_ref(r)

class CollisionTrigger(CollisionInstance):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)

class AIAreaGraph(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        r.skip(r.read_var_int())

class AIWaypointGrid(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(r.read_var_int()*16)

class AIWaypointAreaRadiusTable(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(r.read_var_int()*2)
        r.skip(r.read_var_int()*2)

class AIArea(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        r.skip(r.read_var_int()*4+4)
        r.skip(r.read_var_int()*2)
        ctx.read_string_index(r)

class CollisionMeshInstance(CollisionInstance, DrawableObjectInstance):
    def read(self, r: Reader, ctx: Context):
        CollisionInstance.read(self, r, ctx)
        DrawableObjectInstance.read(self, r, ctx)
        ctx.read_object_ref(r)
        MeshHierachyShaderOverrides().read(r, ctx)
        r.skip(4)

class AIWaypointBufferManager(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)

class ReverbZone(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(8)

class WindBox(WorldNode):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(45)
        ctx.read_object_ref(r)

class ParticleSystemInstance(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(2)
        ctx.read_object_ref(r)

class AmbientSoundPortal(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(1)
        r.skip(r.read_var_int()*12)
        ctx.read_object_ref(r)
        ctx.read_object_ref(r)
        r.skip(8)

class OmniLight(LightShadowed):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(16)

class CoronaInstance(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_object_ref(r)

class AILinkTypeInfoSpecialObject(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        ctx.read_string_index(r)

class Occluder(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)        
        ctx.read_string_index(r)
        r.skip(1)
        r.skip(r.read_var_int()*12)

class PhysicsWaterPool(PhysicsInstance):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)      

class WeakResourceReference(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        ctx.read_string_index(r)

class StreamingHintTrigger(CollisionTrigger):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.read_string_index(r)
        r.skip(4)

class LightAttachedCorona(CoronaInstance):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)

class AIAtmosphereBox(WorldNode):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)

class Resource(BaseObject):
    name: str

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.name = ctx.read_string_index(r)
        r.skip(1)

class MeshResourceBase(Resource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        r.skip(29)

class PrimitiveResource(Resource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        r.skip(4)
        self.vertex_array = ctx.read_object_ref(r, True)
        self.index_array = ctx.read_object_ref(r, True)
        self.index_offset = r.unpack(">i")[0]
        ctx.read_object_ref(r)

class RenderingPrimitiveResource(PrimitiveResource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        r.skip(16)
        ctx.read_object_ref(r, True)

class StaticMeshResource(MeshResourceBase):
    primitives: list[RenderingPrimitiveResource|None]
    local_translate_scale: tuple[float]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.primitives = [ctx.read_object_ref(r, True) for _ in range(r.read_var_int())]
        self.local_translate_scale = r.unpack(">4f")
        r.skip(21)

class ETextureType(IntEnum):
    _2D = 0
    CubeMap = 2

class EPixelFormat(IntEnum):
    INVALID = 34
    INDEX_4 = 0
    INDEX_8 = 1
    ALPHA_4 = 2
    ALPHA_8 = 3
    GLOW_8 = 4
    RGBA_8888 = 5
    RGBA_8888_REV = 6
    RGBA_5551 = 7
    RGBA_5551_REV = 8
    RGBA_4444 = 9
    RGBA_4444_REV = 10
    RGB_888_32 = 11
    RGB_888_32_REV = 12
    RGB_888 = 13
    RGB_888_REV = 14
    RGB_565 = 15
    RGB_565_REV = 16
    RGB_555 = 17
    RGB_555_REV = 18
    S3TC1 = 19
    S3TC3 = 20
    S3TC5 = 21
    RGBE_REV = 22
    INDEX_2X2 = 23
    INDEX_2 = 24
    FLOAT_32 = 25
    RGB_FLOAT_32 = 26
    RGBA_FLOAT_32 = 27
    FLOAT_16 = 28
    RG_FLOAT_16 = 29
    RGB_FLOAT_16 = 30
    RGBA_FLOAT_16 = 31
    DEPTH_24_STENCIL_8 = 32
    DEPTH_16_STENCIL_0 = 33

class ETexColorSpace(IntEnum):
    Linear = 0
    sRGB = 1

class ETexCoordType(IntEnum):
    Normalized = 0
    Rectangle = 1

class SurfaceFormat:
    def __init__(self, r: Reader):
        self.width, self.height, self.pixel_format = r.unpack(">3i")
        r.skip(4)

class Texture(Resource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx) 
        self.type = r.unpack(">i")[0]
        self.format = SurfaceFormat(r)
        self.num_surfaces, self.color_space, self.tex_coord_type = r.unpack(">3i")
        r.skip(12)
        data_size = r.unpack(">i")[0]
        r.skip(120)
        self.data = r.read(data_size)

class EVertexElementStorageType(IntEnum):
    Undefined = 0
    SignedShortNormalized = 1
    Float = 2
    HalfFloat = 3
    UnsignedByteNormalized = 4
    SignedShort = 5
    X11Y11Z10Normalized = 6
    UnsignedByte = 7

class EVertexElement(IntEnum):
    VtxElemPos = 0
    VtxElemPos4 = 1
    VtxElemWeights = 2
    VtxElemTanQuat = 3
    VtxElemTangent = 4
    VtxElemBinormal = 5
    VtxElemNormal = 6
    VtxElemColor = 7
    VtxElemUV0 = 8
    VtxElemUV1 = 9
    VtxElemUV2 = 10
    VtxElemUV3 = 11
    VtxElemUV4 = 12
    VtxElemUV5 = 13
    VtxElemUV6 = 14
    VtxElemMotionVec = 15
    VtxElemVec4Byte0 = 16

class VertexStreamFormat:
    vertex_element: int
    offset: int
    type: int
    num_components: int

    def __init__(self, r: Reader):
        self.vertex_element, self.offset, self.type, self.num_components, _reserved = r.unpack(">I4B")

class VertexStreamField:
    flags: int
    stride: int
    vertex_elements: list[VertexStreamFormat]

    def __init__(self, r: Reader):
        self.flags, self.stride, count = r.unpack(">3i")
        self.vertex_elements = [VertexStreamFormat(r) for _ in range(count)]

class VertexArrayResource(Resource):
    count: int
    stream_fields: list[VertexStreamField]
    data: bytes

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        r.align(self.data_offset)
        self.count, _, count = r.unpack(">3i")
        self.stream_fields = [VertexStreamField(r) for _ in range(count)]

        stride = 0
        for f in self.stream_fields:
            stride += f.stride

        self.data = r.read(stride*self.count)

class IndexArrayResource(Resource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)         
        r.align(self.data_offset)
        self.count = r.unpack(">i")[0]
        r.skip(8)
        self.data = r.read(self.count*2)

class SkinnedMeshResource(MeshResourceBase):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)   
        self.skeleton = ctx.read_object_ref(r, True)      

class RegularSkinnedMeshResourceSkinInfo(BaseObject):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.parts = [PrimitiveSkinInfo(r) for _ in range(r.read_var_int())]
        self.blend_target_deforms = [BlendTargetDeformation(r, ctx) for _ in range(r.read_var_int())]

class SkinnedMeshBoneBindings(BaseObject):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        count = r.read_var_int()
        self.bone_names = [ctx.read_string_index(r) for _ in range(count)]
        r.skip(64*count)

class RegularSkinnedMeshResource(SkinnedMeshResource):
    skinned_mesh_bone_bindings: SkinnedMeshBoneBindings|None
    skin_info: RegularSkinnedMeshResourceSkinInfo|None
    primitives: list[RenderingPrimitiveResource|None]
    position_bounds_scale: tuple[float]
    position_bounds_offset: tuple[float]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)     
        r.skip(19)
        self.skinned_mesh_bone_bindings = ctx.read_object_ref(r, True)
        self.skin_info = ctx.read_object_ref(r, True)
        self.primitives = [ctx.read_object_ref(r, True) for _ in range(r.read_var_int())]
        [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        self.position_bounds_scale = r.unpack(">3f")
        self.position_bounds_offset = r.unpack(">3f")

class TwoBoneIkControl:
    def __init__(self, r: Reader, ctx: Context):
        self.name = ctx.read_string_index(r)
        self.channel_names = [ctx.read_string_index(r) for _ in range(r.read_var_int())]
        self.start_bone_index, self.mid_bone_index, self.end_bone_index = r.unpack(">3B")
        self.hinge_axis = r.unpack(">3f")
        self.hinge_max_limit, self.hinge_min_limit = r.unpack(">2f")

class Bone:
    name: str
    parent_name: str
    rotation: tuple[float]
    position: tuple[float]

class Skeleton(Resource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.bone_sets = [ctx.read_string_index(r) for _ in range(r.read_var_int())]
        self.hulls = [ctx.read_object_ref(r) for _ in range(r.read_var_int())]
        self.nulls_local_bounds = [r.unpack(">6f") for _ in range(r.read_var_int())]
        self.ik_controls = [TwoBoneIkControl(r, ctx) for _ in range(r.read_var_int())]
        self.animation_channels = [ctx.read_string_index(r) for _ in range(r.read_var_int())]
        self.edge_anim_skeleton = r.read(r.read_var_int())
        r.align(self.data_offset)

        start = -r.tell()

        r.skip(4+6+2)
        some_count1, bone_count, some_count2 = r.unpack(">3B")
        r.skip(3)
        strings_chunk_length = r.unpack(">H")[0]
        r.skip(44)

        r.align(start, 64)
        r.skip(24*bone_count)
        
        if some_count1:
            r.align(start, 16)
            r.skip(80*some_count1)
            
        r.align(start, 16)
        bone_infos = []
        for _ in range(bone_count):
            bone_infos.append((r.unpack(">4f"), r.unpack(">3f"), r.unpack(">2I")))
            r.skip(12)

        r.align(start, 4)
        r.skip(bone_count*4)

        r.align(start, 4)
        r.skip((bone_count+some_count2)*4 + bone_count*4)

        strings = r.read(strings_chunk_length)

        def get_string(offset):
            arr = bytearray()
            for i in range(offset, len(strings)):
                if not strings[i]:
                    break
                arr.append(strings[i])

            return arr.decode()
        
        self.bones = []
        for i in range(bone_count):
            b = Bone()
            self.bones.append(b)

            rot, pos, name_offsets = bone_infos[i]
            b.name = get_string(name_offsets[0])
            b.parent_name = get_string(name_offsets[1])
            b.rotation = rot
            b.position = pos

class PrimitiveBlendShapeMask:
    def __init__(self, r: Reader):
        self.mask0, self.mask1, self.mask2, self.mask3 = r.unpack(">4I")

class EPrimitiveSkinInfoType(IntEnum):
    Basic = 0
    NBT = 1

class VertexSkin:
    def __init__(self, r: Reader):
        self.x, self.y, self.z, self.weight0, self.weight1 = r.unpack(">3h2B")
        self.n = r.unpack(">3b")
        self.bone0, self.bone1, self.bone2 = r.unpack(">3B")

class VertexSkinNBT(VertexSkin):
    def __init__(self, r: Reader):
        super().__init__(r)
        self.b = r.unpack(">3b")
        self.t = r.unpack(">3b")

class PrimitiveSkinInfo:
    def __init__(self, r: Reader):
        self.type = r.unpack(">i")[0]
        self.blend_shape_mask = PrimitiveBlendShapeMask(r)
        self.vertices_skin = [VertexSkin(r) for _ in range(r.read_var_int())]
        self.vertices_skin_nbt = [VertexSkinNBT(r) for _ in range(r.read_var_int())]

class VertexDeltaDeformation:
    def __init__(self, r: Reader):
        self.delta_pos = r.unpack(">3f")
        self.delta_nrm_x, self.delta_nrm_y, self.delta_nrm_z, self.vertex_index = r.unpack(">4B")

class PrimitiveDeltaDeformation:
    def __init__(self, r: Reader):
        self.deformations = [VertexDeltaDeformation(r) for _ in range(r.read_var_int())]        

class BlendTargetDeformation:
    def __init__(self, r: Reader, ctx: Context):
        self.name = ctx.read_string_index(r)
        self.deformations = [PrimitiveDeltaDeformation(r) for _ in range(r.read_var_int())]

class SwitchMeshResourcePart:
    mesh: MeshResourceBase|None
    key: str

    def __init__(self, r: Reader, ctx: Context):
        self.mesh = ctx.read_object_ref(r, True)
        self.key = ctx.read_string_index(r)

class SwitchMeshResource(MeshResourceBase):
    name: str
    default_switch: str
    parts_use_the_same_mesh: bool
    parts: list[SwitchMeshResourcePart]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.name = ctx.read_string_index(r)
        self.default_switch = ctx.read_string_index(r)
        self.parts_use_the_same_mesh = r.unpack(">?")[0]
        self.parts = [SwitchMeshResourcePart(r, ctx) for _ in range(r.read_var_int())]

class LodMeshResourcePart:
    mesh: MeshResourceBase|None
    distance: float

    def __init__(self, r: Reader, ctx: Context):
        self.mesh = ctx.read_object_ref(r, True)
        self.distance = r.unpack(">f")[0]

class LodMeshResource(MeshResourceBase):
    meshes: list[LodMeshResourcePart]
    max_distance: float

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.meshes = [LodMeshResourcePart(r, ctx) for _ in range(r.read_var_int())]
        self.max_distance = r.unpack(">f")[0]

class MultiMeshResourcePart:
    def __init__(self, r: Reader, ctx: Context):
        self.mesh = ctx.read_object_ref(r, True)
        self.transform = [r.unpack(">4f") for _ in range(4)]

class MultiMeshResource(MeshResourceBase):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.parts = [MultiMeshResourcePart(r, ctx) for _ in range(r.read_var_int())]
