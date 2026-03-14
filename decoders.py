from struct import unpack_from
from . import datatypes

def decode_triangle(buffer: bytes, offset: int) -> tuple[int]:
    return unpack_from(">3H", buffer, offset)

VERTEX_ELEMENT_UNPACK_FORMATS = {
    datatypes.EVertexElementStorageType.SignedShortNormalized: "h",
    datatypes.EVertexElementStorageType.Float: "f",
    datatypes.EVertexElementStorageType.HalfFloat: "e",
    datatypes.EVertexElementStorageType.UnsignedByteNormalized: "B",
    datatypes.EVertexElementStorageType.SignedShort: "h",
    datatypes.EVertexElementStorageType.X11Y11Z10Normalized: "I",
    datatypes.EVertexElementStorageType.UnsignedByte: "B",
}

VERTEX_ELEMENT_SIZES = {
    datatypes.EVertexElementStorageType.SignedShortNormalized: 2,
    datatypes.EVertexElementStorageType.Float: 4,
    datatypes.EVertexElementStorageType.HalfFloat: 2,
    datatypes.EVertexElementStorageType.UnsignedByteNormalized: 1,
    datatypes.EVertexElementStorageType.SignedShort: 2,
    datatypes.EVertexElementStorageType.X11Y11Z10Normalized: 4,
    datatypes.EVertexElementStorageType.UnsignedByte: 1,
}

def sign_extend(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return (value ^ sign_bit) - sign_bit

def decode_11_11_10(value: tuple[int]) -> tuple[tuple[float]]:
    decoded = []

    for v in value:
        x = v & 0x7FF
        y = (v >> 11) & 0x7FF
        z = (v >> 22) & 0x3FF

        x = sign_extend(x, 11)
        y = sign_extend(y, 11)
        z = sign_extend(z, 10)

        if x < 0:
            x += 1
        if y < 0:
            y += 1
        if z < 0:
            z += 1

        decoded.append((x / 1023.0, y / 1023.0, z / 511.0))

    return tuple(decoded)

def decode_normalized(value: tuple[int], max_value: int) -> tuple[float]:
    return tuple(e / max_value for e in value)

def decode_vertex_element(buffer: bytes, offset: int, ve: datatypes.VertexStreamFormat) -> tuple[int|float]:
    typ = datatypes.EVertexElementStorageType(ve.type)
    fmt = VERTEX_ELEMENT_UNPACK_FORMATS[typ]
    value = unpack_from(f">{ve.num_components}{fmt}", buffer, offset)

    match typ:
        case datatypes.EVertexElementStorageType.SignedShortNormalized:
            value = decode_normalized(value, 32767)
        case datatypes.EVertexElementStorageType.UnsignedByteNormalized:
            value = decode_normalized(value, 255)
        case datatypes.EVertexElementStorageType.X11Y11Z10Normalized:
            value = decode_11_11_10(value)
        

    return value