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

# Killzone 3 + common

class GroupedLights(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        # GroupedObjects
        ctx.skip_string_index(r, count=r.read_var_int()*2)
        ctx.skip_object_ref(r, r.read_var_int())
        ctx.skip_string_index(r)
        r.skip(1)
        # GroupedLights
        ctx.skip_string_index(r, count=r.read_var_int())

class DestructibilityPartState(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        r.skip(9)      
        ctx.skip_object_ref(r)

class AITerrainManager(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_object_ref(r, 6)
        if ctx.version < 173:
            ctx.skip_object_ref(r)

class AIWaypointGrid(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        # AIStaticWaypointGrid
        r.skip_array(16)
        # AIDynamicWaypointGrid
        if ctx.version == 173:
            r.skip(1)

            r.align()
            count = r.unpack(">i")[0]
            r.skip(count*12)

            count = r.unpack(">i")[0]
            r.skip(count*26)

class AIWaypointNeighbors(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip_array(32)
        r.skip_array(16)
        r.skip_array(60)
        ctx.skip_object_ref(r, r.read_var_int())
        ctx.skip_string_index(r)
        r.skip(1)

class AIWaypointAreaRadiusTable(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip_array(2)
        r.skip_array(2)

class AINearestWaypoint(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)    

class AIAreaGraph(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_object_ref(r, r.read_var_int())
        r.skip_array(1)

class AIArea(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        r.skip_array(4)
        r.skip(4)
        r.skip_array(2)
        ctx.skip_string_index(r)

class PhysicsInstance:
    def read(self, r: Reader, ctx: Context):
        ctx.skip_object_ref(r)
        r.skip(8)

class PhysicsWaterPool(BaseObject, PhysicsInstance):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        PhysicsInstance.read(self, r, ctx)

class AnimationPoseMatchingConfigData(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        r.skip_array(4)
        r.skip_array(4)
        r.skip_array(4)
        r.skip(5)

class DrawableObjectInstance:
    def read(self, r: Reader, ctx: Context):
        if ctx.version >= 158:
            r.skip(12)

class WorldNode:
    def read(self, r: Reader, ctx: Context):
        if ctx.version < 158:
            r.skip(6)
        if ctx.version < 173:
            ctx.skip_object_ref(r)
        r.skip(64)

class GeometryObject(WorldNode, DrawableObjectInstance):
    def read(self, r: Reader, ctx: Context):
        WorldNode.read(self, r, ctx)
        DrawableObjectInstance.read(self, r, ctx)

class Light(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        if ctx.version == 173:
            r.skip(29)
            ctx.skip_object_ref(r, 2)
            r.skip(17)
        else:
            r.skip(13)
            ctx.skip_object_ref(r)
            r.skip(11)
        ctx.skip_object_ref(r)

class SunLight(BaseObject, Light):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        Light.read(self, r, ctx)
        if ctx.version == 173:
            r.skip(181)
        else:
            r.skip(141)

class CoronaInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        GeometryObject.read(self, r, ctx)
        ctx.skip_object_ref(r)

class LightAttachedCorona(CoronaInstance):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            r.skip(12)
            ctx.skip_object_ref(r)

class Camera(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        WorldNode.read(self, r, ctx)
        if ctx.version >= 158:
            ctx.skip_string_index(r)
            r.skip(1)
            ctx.skip_object_ref(r)
        r.skip(25)

class PhysicsCollisionInstance(BaseObject, PhysicsInstance):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        PhysicsInstance.read(self, r, ctx)
        if ctx.version == 173:
            r.skip(89)
        else:
            r.skip(97)

class CollisionInstance(WorldNode):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)
        ctx.skip_string_index(r)
        r.skip(2)
        ctx.skip_object_ref(r)            

class CollisionTrigger(PhysicsCollisionInstance, CollisionInstance):
    def read(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            PhysicsCollisionInstance.read(self, r, ctx)
            ctx.skip_string_index(r)
            r.skip(5)
        else:
            CollisionInstance.read(self, r, ctx)
            r.skip(4)

class StreamingHintTrigger(CollisionTrigger):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(4)
        if ctx.version == 173:
            ctx.skip_string_index(r, count=2)

class EncounterDifficultyModifier(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        ctx.skip_string_index(r)
        r.skip(18)

class ParticleSystemInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        GeometryObject.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(2)
        ctx.skip_object_ref(r)

class ProjectedMeshInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        if ctx.version < 173:
            return
        GeometryObject.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        ctx.skip_object_ref(r)
        r.skip(29)

class CoreScript(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        raise NotImplementedError("Core script not implemented")

class GameScript(CoreScript):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        raise NotImplementedError("Game script not implemented")

class AIAtmosphereBox(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        WorldNode.read(self, r, ctx)
        r.skip(4)

class Portal(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        r.skip_array(12)
        ctx.skip_object_ref(r, 2)
        r.skip(4)

class GlobalDamageModifier(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)

        if ctx.version < 158:
            r.skip(6)

        for _ in range(r.read_var_int()):
            if ctx.version == 173:
                ctx.skip_string_index(r)
                r.skip(1)
                ctx.skip_string_index(r)
                r.skip(5)
                ctx.skip_string_index(r, count=2)
                r.skip(4)
                ctx.skip_object_ref(r)
            else:
                ctx.skip_string_index(r)
                r.skip(2)
                ctx.skip_string_index(r)
                r.skip(4)

                if ctx.version == 158:
                    ctx.skip_string_index(r)
                    r.skip(4)

class AIMarker(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        WorldNode.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(6)

class WindBox(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        WorldNode.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(45)
        ctx.skip_object_ref(r)

class LightShadowed(Light):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            r.skip(56)        
        else:
            r.skip(32)

class SpotLight(BaseObject, LightShadowed):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        LightShadowed.read(self, r, ctx)
        r.skip(20)
        ctx.skip_object_ref(r)

class AIDarkBox(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        if ctx.version < 173:
            return
        WorldNode.read(self, r, ctx)
        r.skip(4)

class LumpOptimizationSettingsGame(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        # LumpOptimizationSettings
        r.skip(4)
        # LumpOptimizationSettingsGame
        r.skip(2)

class MeshHierachyShaderOverrides(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        for _ in range(r.read_var_int()):
            ctx.skip_object_ref(r)
            r.skip_array(4)
            for _ in range(r.read_var_int()):
                ctx.skip_object_ref(r)
                for _ in range(r.read_var_int()):
                    ctx.skip_string_index(r)
                    ctx.skip_object_ref(r)
                    r.skip(4)

                for _ in range(r.read_var_int()):
                    ctx.skip_string_index(r)
                    r.skip(20)
                    ctx.skip_object_ref(r)
            if ctx.version == 173:
                r.skip(1)

class StaticMeshInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        GeometryObject.read(self, r, ctx)
        if ctx.version >= 158:
            ctx.skip_string_index(r)
            r.skip(1)
        else:
            r.skip(4)
        ctx.skip_object_ref(r)
        MeshHierachyShaderOverrides().read(r, ctx)
        r.skip(8)

        if ctx.version == 173:
            r.skip_array(2)
            r.skip(4)

class ParTimeLevelInfo(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        ctx.skip_string_index(r)
        for _ in range(r.read_var_int()):
            r.skip(8)
            r.skip_array(4)

class WaterInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        if ctx.version < 173:
            return
        GeometryObject.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        ctx.skip_object_ref(r)
        r.skip(44)
        ctx.skip_object_ref(r)

class AILinkTypeInfoSpecialObject(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r, count=2)

class WeakResourceReference(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r, count=2)

class SimpleAnimatingSkinnedMeshInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        GeometryObject.read(self, r, ctx)
        # SkinnedMeshInstance
        ctx.skip_string_index(r)
        r.skip(1)
        ctx.skip_object_ref(r)
        # SimpleAnimatingSkinnedMeshInstance
        if ctx.version < 173:
            r.skip(4)
        ctx.skip_object_ref(r)

class CollisionMeshInstance(StaticMeshInstance, CollisionInstance, DrawableObjectInstance):
    def read(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            StaticMeshInstance.read(self, r, ctx)
        else:
            CollisionInstance.read(self, r, ctx)
            DrawableObjectInstance.read(self, r, ctx)
            ctx.skip_object_ref(r)
            MeshHierachyShaderOverrides().read(r, ctx)
            r.skip(4)

class AnimationPoseMatchingDataBase(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        for _ in range(r.read_var_int()):
            r.skip_array(24)
            r.skip(60)
        r.skip_array(4)

class LeanAndPeekAction(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(80)
        ctx.skip_object_ref(r, r.read_var_int()+1)

class LeanAndPeekPosition(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(8)
        ctx.skip_object_ref(r, r.read_var_int())

class EntityPlaceHolder(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(65)
        ctx.skip_string_index(r, count=2)
        for _ in range(r.read_var_int()):
            if ctx.version == 173:
                ctx.skip_string_index(r, count=2)
                r.skip(4)
            ctx.skip_string_index(r)
        ctx.skip_object_ref(r, r.read_var_int())
        r.skip(4)

class MultiBlendedMeshInstance(BaseObject, GeometryObject):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        if ctx.version < 173:
            return
        GeometryObject.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        ctx.skip_object_ref(r)

class PhonemeBoneChannel(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        r.skip(4)
        for _ in range(r.read_var_int()):
            r.skip(16)
        for _ in range(r.read_var_int()):
            r.skip(4)

class SkeletonTargetTree(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version < 173:
            return
        for _ in range(r.read_var_int()):
            ctx.skip_string_index(r)
            ctx.skip_object_ref(r)
            ctx.skip_string_index(r, count=2)
        ctx.skip_string_index(r)
        r.skip(1)

class SoundZoneInstance(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        if ctx.version < 173:
            return
        WorldNode.read(self, r, ctx)
        ctx.skip_object_ref(r)

class LevelAssetInfo(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        for _ in range(r.read_var_int()):
            ctx.skip_string_index(r)
            ctx.skip_string_index(r, count=r.read_var_int())
            if ctx.version == 173:
                ctx.skip_string_index(r, count=r.read_var_int())

class PostProcessEffectorInstance(BaseObject, WorldNode):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        if ctx.version < 173:
            return
        WorldNode.read(self, r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        ctx.skip_object_ref(r)

class OmniLight(BaseObject, LightShadowed):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        LightShadowed.read(self, r, ctx)
        r.skip(16)

class Shape2D(GeometryObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(2)
        r.skip_array(8)

class Shape2DExtrusion(Shape2D):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        r.skip(4)

class RenderZone(BaseObject, Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        BaseObject.read(self, r, ctx)
        Shape2DExtrusion.read(self, r, ctx)
        if ctx.version == 173:
            r.skip(16)
        else:
            r.skip(12)
        ctx.skip_object_ref(r)
        r.skip(45)
        ctx.skip_object_ref(r)
        r.skip(4)

class Zone(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(89)
        ctx.skip_object_ref(r, r.read_var_int())

class LightingSetupSet(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_object_ref(r, r.read_var_int())
        ctx.skip_string_index(r)
        r.skip(1)

class LightingSetup(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(1)
        ctx.skip_object_ref(r, r.read_var_int())

# Killzone 2

class PhonemeChannel(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            return
        
        r.skip(8)
        r.skip_array(8)

class BlendExpression(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            return
        
        ctx.skip_string_index(r)
        if ctx.version == 158:
            r.skip_array(4)

class RenderEffectInstanceImp1(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            return

        if ctx.version < 158:
            ctx.skip_object_ref(r, 3)
        ctx.skip_object_ref(r)

class AnimationMotionDirectional(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)        
        if ctx.version == 173:
            return

        r.skip(4)
        r.skip_array(4)
        ctx.skip_object_ref(r, r.read_var_int())

class AnimationMotionCurve(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)       
        if ctx.version == 173:
            return
        
        r.skip(4)
        r.skip_array(12) 
        r.skip_array(4)     

class SoundMixResource(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            BaseObject.read(self, r, ctx)
            return
        super().read(r, ctx)
        r.skip_array(4)
        r.skip(4)

class AmbientSoundZone(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            BaseObject.read(self, r, ctx)
            return
        super().read(r, ctx)
        r.skip(12)

class AIWaypointBufferManager(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            return
        r.skip(4)

class ReverbZone(Shape2DExtrusion):
    def read(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            BaseObject.read(self, r, ctx)
            return
        super().read(r, ctx)
        ctx.skip_string_index(r)
        r.skip(8)        

class AmbientSoundPortal(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)
        if ctx.version == 173:
            return
        ctx.skip_string_index(r)
        r.skip(1)
        r.skip_array(12)
        ctx.skip_object_ref(r, 2)
        r.skip(8)

class Occluder(BaseObject):
    def read(self, r: Reader, ctx: Context):
        super().read(r, ctx)        
        if ctx.version == 173:
            return
        ctx.skip_string_index(r)
        r.skip(1)
        r.skip_array(12)


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

    def __init__(self, r: Reader, ctx: Context):
        if ctx.version < 158:
            self.vertex_element, _, self.num_components, self.type, self.offset = r.unpack("<I4B")
        else:
            self.vertex_element, self.offset, self.type, self.num_components, _ = r.unpack(">I4B")

class VertexStreamField:
    flags: int
    stride: int
    vertex_elements: list[VertexStreamFormat]

    def __init__(self, r: Reader, ctx: Context):
        endian = ">" if ctx.version >= 158 else "<"

        self.flags, self.stride, count = r.unpack(endian + "3i")
        self.vertex_elements = [VertexStreamFormat(r, ctx) for _ in range(count)]

class Resource(BaseObject):
    name: str

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.name = ctx.read_string_index(r)
        r.skip(1)
        if ctx.version < 158:
            r.skip(6)

class VertexArrayResource(Resource):
    count: int
    stream_fields: list[VertexStreamField]
    data: bytes

    def _parse(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            BaseObject._parse(self, r, ctx)
        else:
            Resource._parse(self, r, ctx)
            r.align(self.data_offset)

        endian = ">" if ctx.version >= 158 else "<"

        if ctx.version == 173:
            self.count, count = r.unpack(endian + "2i")
        else:
            self.count, _, count = r.unpack(endian + "3i")
        self.stream_fields = [VertexStreamField(r, ctx) for _ in range(count)]

        data = bytearray()
        for f in self.stream_fields:
            if ctx.version < 173:
                r.align(self.data_offset)
            data += r.read(f.stride*self.count)

        self.data = bytes(data)

class IndexArrayResource(Resource):
    count: int
    data: bytes

    def _parse(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            BaseObject._parse(self, r, ctx)
        else:
            Resource._parse(self, r, ctx)

        r.align(self.data_offset)

        endian = ">" if ctx.version >= 158 else "<"

        self.count = r.unpack(endian + "i")[0]
        r.skip(8)
        self.data = r.read(self.count*2)

class MeshResourceBase(Resource):
    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        r.skip(29)

class TextureBinding:
    sampler: str

    def __init__(self, r: Reader, ctx: Context):
        self.sampler = ctx.read_string_index(r)
        self.texture = ctx.read_object_ref(r)
        r.skip(4)

class RenderTechnique:
    texture_bindings: list[TextureBinding]

    def __init__(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            r.skip(30)
        else:
            r.skip(27)
        ctx.skip_object_ref(r)
        self.texture_bindings = [TextureBinding(r, ctx) for _ in range(r.read_var_int())]

        for _ in range(r.read_var_int()):
            ctx.skip_string_index(r)
            r.skip(20)
            ctx.skip_object_ref(r)
            ctx.skip_string_index(r)

        r.skip(4)

        if ctx.version == 173:
            r.skip(4)

class RenderEffectResource(Resource):
    render_techniques: list[RenderTechnique]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        if ctx.version >= 158:
            ctx.skip_object_ref(r)
        self.render_techniques = [RenderTechnique(r, ctx) for _ in range(r.read_var_int())]

class PrimitiveResource(Resource):
    vertex_array: VertexArrayResource|str|None
    index_array: IndexArrayResource|str|None
    index_offset: int

    def _parse(self, r: Reader, ctx: Context):
        if ctx.version == 173:
            BaseObject._parse(self, r, ctx)
        else:
            Resource._parse(self, r, ctx)

        r.skip(4)
        self.vertex_array = ctx.read_object_ref(r, True)
        self.index_array = ctx.read_object_ref(r, True)
        self.index_offset = r.unpack(">i")[0]

        if ctx.version == 173:
            r.skip(24)
            ctx.skip_object_ref(r)
            r.skip(8)
        elif ctx.version == 158:
            ctx.skip_object_ref(r)

class RenderingPrimitiveResource(PrimitiveResource):
    render_effects: RenderEffectResource|str|None

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        if ctx.version < 173:
            r.skip(16)
        self.render_effects = ctx.read_object_ref(r, True)

class StaticMeshResource(MeshResourceBase):
    primitives: list[RenderingPrimitiveResource|str|None]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.primitives = [ctx.read_object_ref(r, True) for _ in range(r.read_var_int())]

class TwoBoneIkControl:
    name: str
    channel_names: list[str]
    start_joint_index: int
    mid_joint_index: int
    end_joint_index: int
    hinge_axis: tuple[float]
    hinge_max_limit: tuple[float]
    hinge_min_limit: tuple[float]

    def __init__(self, r: Reader, ctx: Context):
        joint_fmt = ">3h" if ctx.version == 173 else "3B"

        self.name = ctx.read_string_index(r)
        self.channel_names = [ctx.read_string_index(r) for _ in range(r.read_var_int())]
        self.start_joint_index, self.mid_joint_index, self.end_joint_index = r.unpack(joint_fmt)
        self.hinge_axis = r.unpack(">3f")
        self.hinge_max_limit, self.hinge_min_limit = r.unpack(">2f")

class Joint:
    name: str
    parent_name: str
    parent_index: int
    rotation: tuple[int]
    translation: tuple[int]

    def __init__(self, r: Reader=None, ctx: Context=None):
        if r and ctx:
            self.read(r, ctx)

    def read(self, r: Reader, ctx: Context):
        self.name = ctx.read_string_index(r)
        self.parent_name = ctx.read_string_index(r)
        self.parent_index = r.unpack(">h")[0]
        self.rotation = r.unpack(">4f")
        self.translation = r.unpack(">3f")

class Skeleton(Resource):
    bone_sets: str
    joints: list[Joint]
    ik_controls: list[TwoBoneIkControl]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.bone_sets = [ctx.read_string_index(r) for _ in range(r.read_var_int())]
        if ctx.version == 173:
            self.joints = [Joint(r, ctx) for _ in range(r.read_var_int())]
            for _ in range(r.read_var_int()): # Helpers
                ctx.skip_string_index(r)
                r.skip(68)
            ctx.skip_string_index(r, count=r.read_var_int()) # AnimationChannels
            self.ik_controls = [TwoBoneIkControl(r, ctx) for _ in range(r.read_var_int())]
            r.skip_array(4) # BoneSetFlags
            r.skip_array(4) # AnimChannelsBoneSetFlags
            r.skip_array(1) # EdgeAnimSkeleton
            r.skip(4) # SkeletonAnimatorABIHash 
        else:
            ctx.skip_object_ref(r, r.read_var_int())
            r.skip_array(24)
            self.ik_controls = [TwoBoneIkControl(r, ctx) for _ in range(r.read_var_int())]
            ctx.skip_string_index(r, count=r.read_var_int()) # AnimationChannels
            r.skip_array(1) # EdgeAnimSkeleton
            r.align(self.data_offset)

            start = -r.tell()

            endian = ">" if ctx.version >= 158 else "<"

            r.skip(4+6+2)
            some_count1, joint_count, some_count2 = r.unpack(">3B")
            r.skip(3)
            strings_chunk_length = r.unpack(endian + "H")[0]
            r.skip(44)

            r.align(start, 64)
            r.skip(24*joint_count)
            
            if some_count1:
                r.align(start, 16)
                r.skip(80*some_count1)
                
            r.align(start, 16)
            bone_infos = []
            for _ in range(joint_count):
                bone_infos.append((r.unpack(endian + "4f"), r.unpack(endian + "3f"), r.unpack(endian + "2I")))
                r.skip(12)

            r.align(start, 4)
            r.skip(joint_count*4)

            r.align(start, 4)
            r.skip((joint_count+some_count2)*4 + joint_count*4)

            strings = r.read(strings_chunk_length)

            def get_string(offset):
                arr = bytearray()
                for i in range(offset, len(strings)):
                    if not strings[i]:
                        break
                    arr.append(strings[i])

                return arr.decode()
            
            self.joints = []
            for i in range(joint_count):
                j = Joint()
                self.joints.append(j)

                rot, pos, name_offsets = bone_infos[i]
                j.name = get_string(name_offsets[0])
                j.parent_name = get_string(name_offsets[1])
                j.parent_index = -1
                j.rotation = rot
                j.translation = pos

class EPrimitiveSkinInfoType(IntEnum):
    Basic = 0
    NBT = 1

class VertexSkin:
    x: int
    y: int
    z: int
    weight0: int
    weight1: int
    n: tuple[int]
    bone0: int
    bone1: int
    bone2: int

    def __init__(self, r: Reader):
        self.x, self.y, self.z, self.weight0, self.weight1 = r.unpack(">3h2B")
        self.n = r.unpack(">3b")
        self.bone0, self.bone1, self.bone2 = r.unpack(">3B")

class VertexSkinNBT(VertexSkin):
    b: tuple[int]
    t: tuple[int]

    def __init__(self, r: Reader):
        super().__init__(r)
        self.b = r.unpack(">3b")
        self.t = r.unpack(">3b")

class PrimitiveSkinInfo:
    type: int
    vertices_skin: list[VertexSkin]
    vertices_skin_nbt: list[VertexSkinNBT]

    def __init__(self, r: Reader):
        self.type = r.unpack(">i")[0]
        r.skip(16)
        self.vertices_skin = [VertexSkin(r) for _ in range(r.read_var_int())]
        self.vertices_skin_nbt = [VertexSkinNBT(r) for _ in range(r.read_var_int())]

class VertexDeltaDeformation:
    delta_pos: tuple[float]
    delta_nrm_x: int
    delta_nrm_y: int
    delta_nrm_z: int
    vertex_index: int

    def __init__(self, r: Reader):
        self.delta_pos = r.unpack(">3f")
        self.delta_nrm_x, self.delta_nrm_y, self.delta_nrm_z, self.vertex_index = r.unpack(">4B")

class PrimitiveDeltaDeformation:
    deformations: list[VertexDeltaDeformation]

    def __init__(self, r: Reader):
        self.deformations = [VertexDeltaDeformation(r) for _ in range(r.read_var_int())]        

class BlendTargetDeformation:
    name: str
    deformations: list[PrimitiveDeltaDeformation]

    def __init__(self, r: Reader, ctx: Context):
        self.name = ctx.read_string_index(r)
        self.deformations = [PrimitiveDeltaDeformation(r) for _ in range(r.read_var_int())]        

class SkinnedMeshResource(MeshResourceBase):
    skeleton: Skeleton|str|None

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)   
        self.skeleton = ctx.read_object_ref(r, True)      

class RegularSkinnedMeshResourceSkinInfo(BaseObject):
    parts: list[PrimitiveSkinInfo]
    blend_target_deforms: list[BlendTargetDeformation]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.parts = [PrimitiveSkinInfo(r) for _ in range(r.read_var_int())]
        self.blend_target_deforms = [BlendTargetDeformation(r, ctx) for _ in range(r.read_var_int())]

class SkinnedMeshBoneBindings(BaseObject):
    bone_names: list[str]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        count = r.read_var_int()
        self.bone_names = [ctx.read_string_index(r) for _ in range(count)]
        self.inverse_bind_matrices = [[r.unpack(">4f") for _ in range(4)] for _ in range(count)]

class RegularSkinnedMeshResource(SkinnedMeshResource):
    skinned_mesh_bone_bindings: SkinnedMeshBoneBindings|str|None
    skin_info: RegularSkinnedMeshResourceSkinInfo|str|None
    primitives: list[RenderingPrimitiveResource|str|None]
    position_bounds_scale: tuple[float]
    position_bounds_offset: tuple[float]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)     
        if ctx.version == 173:
            r.skip(14)
        else:
            r.skip(19)

        self.skinned_mesh_bone_bindings = ctx.read_object_ref(r, True)
        if ctx.version == 173:
            ctx.skip_object_ref(r)

        if ctx.version < 158:
            self.skin_info = RegularSkinnedMeshResourceSkinInfo()
            self.skin_info._parse(r, ctx)
        else:
            self.skin_info = ctx.read_object_ref(r, True)

        self.primitives = [ctx.read_object_ref(r, True) for _ in range(r.read_var_int())]
        self.render_effects = [ctx.read_object_ref(r, True) for _ in range(r.read_var_int())]
        self.position_bounds_scale = r.unpack(">3f")
        self.position_bounds_offset = r.unpack(">3f")

class SwitchMeshResourcePart:
    mesh: MeshResourceBase|str|None
    key: str

    def __init__(self, r: Reader, ctx: Context):
        self.mesh = ctx.read_object_ref(r, True)
        self.key = ctx.read_string_index(r)

class SwitchMeshResource(MeshResourceBase):
    name: str
    parts_use_the_same_mesh: bool
    parts: list[SwitchMeshResourcePart]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.name = ctx.read_string_index(r)
        if ctx.version < 173:
            ctx.skip_string_index(r)
        self.parts_use_the_same_mesh = r.unpack(">?")[0]
        self.parts = [SwitchMeshResourcePart(r, ctx) for _ in range(r.read_var_int())]

class LodMeshResourcePart:
    mesh: MeshResourceBase|str|None

    def __init__(self, r: Reader, ctx: Context):
        self.mesh = ctx.read_object_ref(r, True)
        r.skip(4)

class LodMeshResource(MeshResourceBase):
    meshes: list[LodMeshResourcePart]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.meshes = [LodMeshResourcePart(r, ctx) for _ in range(r.read_var_int())]

class MultiMeshResourcePart:
    mesh: MeshResourceBase|str|None
    transform: tuple[tuple[float]]

    def __init__(self, r: Reader, ctx: Context):
        self.mesh = ctx.read_object_ref(r, True)
        self.transform = [r.unpack(">4f") for _ in range(4)]

class MultiMeshResource(MeshResourceBase):
    parts: list[MultiMeshResourcePart]

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)
        self.parts = [MultiMeshResourcePart(r, ctx) for _ in range(r.read_var_int())]        

class ETextureType(IntEnum):
    _2D = 0
    CubeMap = 2

class EPixelFormat_KZ2(IntEnum):
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

class EPixelFormat_KZ3(IntEnum):
    INVALID = 35
    INDEX_4 = 0
    INDEX_8 = 1
    ALPHA_4 = 2
    ALPHA_8 = 3
    INTENSITY_8 = 5
    GLOW_8 = 4
    RGBA_8888 = 6
    RGBA_8888_REV = 7
    RGBA_5551 = 8
    RGBA_5551_REV = 9
    RGBA_4444 = 10
    RGBA_4444_REV = 11
    RGB_888_32 = 12
    RGB_888_32_REV = 13
    RGB_888 = 14
    RGB_888_REV = 15
    RGB_565 = 16
    RGB_565_REV = 17
    RGB_555 = 18
    RGB_555_REV = 19
    S3TC1 = 20
    S3TC3 = 21
    S3TC5 = 22
    RGBE_REV = 23
    INDEX_2X2 = 24
    INDEX_2 = 25
    FLOAT_32 = 26
    RGB_FLOAT_32 = 27
    RGBA_FLOAT_32 = 28
    FLOAT_16 = 29
    RG_FLOAT_16 = 30
    RGB_FLOAT_16 = 31
    RGBA_FLOAT_16 = 32
    DEPTH_24_STENCIL_8 = 33
    DEPTH_16_STENCIL_0 = 34

class ETexColorSpace(IntEnum):
    Linear = 0
    sRGB = 1

class ETexCoordType(IntEnum):
    Normalized = 0
    Rectangle = 1

BITS_PER_PIXELS_KZ3 = {
    EPixelFormat_KZ3.INDEX_4: 4,
    EPixelFormat_KZ3.INDEX_8: 8,
    EPixelFormat_KZ3.ALPHA_4: 4,
    EPixelFormat_KZ3.ALPHA_8: 8,
    EPixelFormat_KZ3.INTENSITY_8: 8,
    EPixelFormat_KZ3.GLOW_8: 8,
    EPixelFormat_KZ3.RGBA_8888: 32,
    EPixelFormat_KZ3.RGBA_8888_REV: 32,
    EPixelFormat_KZ3.RGBA_5551: 16,
    EPixelFormat_KZ3.RGBA_5551_REV: 16,
    EPixelFormat_KZ3.RGBA_4444: 16,
    EPixelFormat_KZ3.RGBA_4444_REV: 16,
    EPixelFormat_KZ3.RGB_888_32: 32,
    EPixelFormat_KZ3.RGB_888_32_REV: 32,
    EPixelFormat_KZ3.RGB_888: 24,
    EPixelFormat_KZ3.RGB_888_REV: 24,
    EPixelFormat_KZ3.RGB_565: 16,
    EPixelFormat_KZ3.RGB_565_REV: 16,
    EPixelFormat_KZ3.RGB_555: 16,
    EPixelFormat_KZ3.RGB_555_REV: 16,
    EPixelFormat_KZ3.S3TC1: 4,
    EPixelFormat_KZ3.S3TC3: 8,
    EPixelFormat_KZ3.S3TC5: 8,
    EPixelFormat_KZ3.RGBE_REV: 32,
    EPixelFormat_KZ3.INDEX_2X2: 4,
    EPixelFormat_KZ3.INDEX_2: 2,
    EPixelFormat_KZ3.FLOAT_32: 32,
    EPixelFormat_KZ3.RGB_FLOAT_32: 96,
    EPixelFormat_KZ3.RGBA_FLOAT_32: 128,
    EPixelFormat_KZ3.FLOAT_16: 16,
    EPixelFormat_KZ3.RG_FLOAT_16: 32,
    EPixelFormat_KZ3.RGB_FLOAT_16: 48,
    EPixelFormat_KZ3.RGBA_FLOAT_16: 64,
    EPixelFormat_KZ3.DEPTH_24_STENCIL_8: 32,
    EPixelFormat_KZ3.DEPTH_16_STENCIL_0: 16,
}    

BITS_PER_PIXELS_KZ2 = {
    EPixelFormat_KZ2.INDEX_4: 4,
    EPixelFormat_KZ2.INDEX_8: 8,
    EPixelFormat_KZ2.ALPHA_4: 4,
    EPixelFormat_KZ2.ALPHA_8: 8,
    EPixelFormat_KZ2.GLOW_8: 8,
    EPixelFormat_KZ2.RGBA_8888: 32,
    EPixelFormat_KZ2.RGBA_8888_REV: 32,
    EPixelFormat_KZ2.RGBA_5551: 16,
    EPixelFormat_KZ2.RGBA_5551_REV: 16,
    EPixelFormat_KZ2.RGBA_4444: 16,
    EPixelFormat_KZ2.RGBA_4444_REV: 16,
    EPixelFormat_KZ2.RGB_888_32: 32,
    EPixelFormat_KZ2.RGB_888_32_REV: 32,
    EPixelFormat_KZ2.RGB_888: 24,
    EPixelFormat_KZ2.RGB_888_REV: 24,
    EPixelFormat_KZ2.RGB_565: 16,
    EPixelFormat_KZ2.RGB_565_REV: 16,
    EPixelFormat_KZ2.RGB_555: 16,
    EPixelFormat_KZ2.RGB_555_REV: 16,
    EPixelFormat_KZ2.S3TC1: 4,
    EPixelFormat_KZ2.S3TC3: 8,
    EPixelFormat_KZ2.S3TC5: 8,
    EPixelFormat_KZ2.RGBE_REV: 32,
    EPixelFormat_KZ2.INDEX_2X2: 4,
    EPixelFormat_KZ2.INDEX_2: 2,
    EPixelFormat_KZ2.FLOAT_32: 32,
    EPixelFormat_KZ2.RGB_FLOAT_32: 96,
    EPixelFormat_KZ2.RGBA_FLOAT_32: 128,
    EPixelFormat_KZ2.FLOAT_16: 16,
    EPixelFormat_KZ2.RG_FLOAT_16: 32,
    EPixelFormat_KZ2.RGB_FLOAT_16: 48,
    EPixelFormat_KZ2.RGBA_FLOAT_16: 64,
    EPixelFormat_KZ2.DEPTH_24_STENCIL_8: 32,
    EPixelFormat_KZ2.DEPTH_16_STENCIL_0: 16,
}   

class SurfaceFormat:
    width: int
    height: int
    pixel_format: int

    def __init__(self, width: int, height: int, pixel_format: int):
        self.width = width
        self.height = height
        self.pixel_format = pixel_format

class Texture(Resource):
    type: int
    format: SurfaceFormat
    num_surfaces: int
    tex_coord_type: int
    color_space: int

    def calc_data_size(self, numSurfaces: int=0):
        if numSurfaces < 1:
            numSurfaces = self.num_surfaces

        is_dxt = self.format.pixel_format in (EPixelFormat_KZ3.S3TC1, EPixelFormat_KZ3.S3TC3, EPixelFormat_KZ3.S3TC5)

        size = 0
        for i in range(numSurfaces):
            w = self.format.width >> i
            h = self.format.height >> i

            if is_dxt:
                h = (h + 3) & 0xFFFFFFFC
                line_size = (w + 3) // 4 * BITS_PER_PIXELS_KZ3[self.format.pixel_format] // 2
            else:
                line_size = w * BITS_PER_PIXELS_KZ3[self.format.pixel_format] // 8

            size += h * line_size
        
        return size

    def _parse(self, r: Reader, ctx: Context):
        super()._parse(r, ctx)

        if ctx.version == 173:
            values = r.unpack(">9B")
            self.type = values[3] # 0 or 3 or 6
            self.format = SurfaceFormat(1 << values[1], 1 << values[2], values[5])
            self.num_surfaces = values[4]
            self.tex_coord_type = values[7]
            self.color_space = values[8]

            main_mip_size = self.calc_data_size(1)

            data_size = r.unpack(">i")[0]
            r.skip(4)

            data = bytearray()

            if self.color_space == 1 and self.num_surfaces > 1 and main_mip_size >= 0x10000:
                offset = r.unpack(">i")[0]
                ctx.stream_file.seek(offset)
                data = ctx.stream_file.read(main_mip_size)

            data += r.read(data_size)

            self.data = bytes(data)
        else:
            self.type = r.unpack(">i")[0]
            self.format = SurfaceFormat(*r.unpack(">3i4x"))
            self.num_surfaces, self.color_space, self.tex_coord_type = r.unpack(">3i")
            if ctx.version < 158:
                r.skip(8)
            else:
                r.skip(12)
            data_size = r.unpack(">i")[0]
            r.skip(120)
            self.data = r.read(data_size)
