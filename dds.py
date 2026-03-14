from . import datatypes
from struct import pack
import numpy as np

BITS_PER_PIXELS = {
    datatypes.EPixelFormat.INDEX_4: 4,
    datatypes.EPixelFormat.INDEX_8: 8,
    datatypes.EPixelFormat.ALPHA_4: 4,
    datatypes.EPixelFormat.ALPHA_8: 8,
    datatypes.EPixelFormat.GLOW_8: 8,
    datatypes.EPixelFormat.RGBA_8888: 32,
    datatypes.EPixelFormat.RGBA_8888_REV: 32,
    datatypes.EPixelFormat.RGBA_5551: 16,
    datatypes.EPixelFormat.RGBA_5551_REV: 16,
    datatypes.EPixelFormat.RGBA_4444: 16,
    datatypes.EPixelFormat.RGBA_4444_REV: 16,
    datatypes.EPixelFormat.RGB_888_32: 32,
    datatypes.EPixelFormat.RGB_888_32_REV: 32,
    datatypes.EPixelFormat.RGB_888: 24,
    datatypes.EPixelFormat.RGB_888_REV: 24,
    datatypes.EPixelFormat.RGB_565: 16,
    datatypes.EPixelFormat.RGB_565_REV: 16,
    datatypes.EPixelFormat.RGB_555: 16,
    datatypes.EPixelFormat.RGB_555_REV: 16,
    datatypes.EPixelFormat.S3TC1: 4,
    datatypes.EPixelFormat.S3TC3: 8,
    datatypes.EPixelFormat.S3TC5: 8,
    datatypes.EPixelFormat.RGBE_REV: 32,
    datatypes.EPixelFormat.INDEX_2X2: 4,
    datatypes.EPixelFormat.INDEX_2: 2,
    datatypes.EPixelFormat.FLOAT_32: 32,
    datatypes.EPixelFormat.RGB_FLOAT_32: 96,
    datatypes.EPixelFormat.RGBA_FLOAT_32: 128,
    datatypes.EPixelFormat.FLOAT_16: 16,
    datatypes.EPixelFormat.RG_FLOAT_16: 32,
    datatypes.EPixelFormat.RGB_FLOAT_16: 48,
    datatypes.EPixelFormat.RGBA_FLOAT_16: 64,
    datatypes.EPixelFormat.DEPTH_24_STENCIL_8: 32,
    datatypes.EPixelFormat.DEPTH_16_STENCIL_0: 16,
}

RGBA_MASKS = {
    datatypes.EPixelFormat.ALPHA_4: (0, 0, 0, 0xf),
    datatypes.EPixelFormat.ALPHA_8: (0, 0, 0, 0xff),
    datatypes.EPixelFormat.RGBA_8888: (0xff000000, 0xff0000, 0xff00, 0xff),
    datatypes.EPixelFormat.RGBA_8888_REV: (0xff00, 0xff0000, 0xff000000, 0xff),
    datatypes.EPixelFormat.RGBA_5551: (0b1111100000000000, 0b11111000000, 0b111110, 0b1),
    datatypes.EPixelFormat.RGBA_5551_REV: (0b111110, 0b11111000000, 0b1111100000000000, 0b1),
    datatypes.EPixelFormat.RGBA_4444: (0xf000, 0xf00, 0xf0, 0xf),
    datatypes.EPixelFormat.RGBA_4444_REV: (0xf0, 0xf00, 0xf000, 0xf),
    datatypes.EPixelFormat.RGB_888_32: (0xff000000, 0xff0000, 0xff00, 0),
    datatypes.EPixelFormat.RGB_888_32_REV: (0xff00, 0xff0000, 0xff000000, 0),
    datatypes.EPixelFormat.RGB_888: (0xff0000, 0xff00, 0xff, 0),
    datatypes.EPixelFormat.RGB_888_REV: (0xff, 0xff00, 0xff0000, 0),
    datatypes.EPixelFormat.RGB_565: (0xf800, 0x7e0, 0x1f, 0),
    datatypes.EPixelFormat.RGB_565_REV: (0x1f, 0x7e0, 0xf800, 0),
    datatypes.EPixelFormat.RGB_555: (0x7c00, 0xe30, 0x1f, 0),
    datatypes.EPixelFormat.RGB_555_REV: (0x1f, 0xe30, 0x7c00, 0),
    datatypes.EPixelFormat.RGBE_REV: (0xff000000, 0xff0000, 0xff00, 0),
    datatypes.EPixelFormat.DEPTH_24_STENCIL_8: (0xffffff, 0, 0, 0xff000000),
    datatypes.EPixelFormat.DEPTH_16_STENCIL_0: (0xffff, 0, 0, 0),
}

def make_dds(tex: datatypes.Texture, filepath: str):
    with open(filepath, "wb") as file:
        file.write(b"DDS ")

        is_compressed = tex.format.pixel_format in {datatypes.EPixelFormat.S3TC1, datatypes.EPixelFormat.S3TC3, datatypes.EPixelFormat.S3TC5}
        is_dx10 = tex.format.pixel_format > 24
        data = tex.data

        caps = 0x1000
        caps2 = 0

        if tex.type == datatypes.ETextureType.CubeMap:
            caps |= 0x8
            caps2 = 0xfe00

        flags = 0x1 | 0x2 | 0x4 |0x1000
        if is_compressed:
            flags |= 0x80000
        else:
            flags |= 0x8

        if tex.num_surfaces > 1:
            flags |= 0x20000
            caps |= 0x8 | 0x400000

        pitch_or_linear_size = len(tex.data)
        if not is_compressed:
            pitch_or_linear_size = (tex.format.width * BITS_PER_PIXELS[tex.format.pixel_format] + 7) // 8

        file.write(pack("7I", 124, flags, tex.format.height, tex.format.width, pitch_or_linear_size, 0, tex.num_surfaces if tex.num_surfaces > 1 else 0))

        file.write(b"\x00\x00\x00\x00"*11)

        flags = 0
        four_cc = 0
        bit_count = 0
        r_mask = 0
        g_mask = 0
        b_mask = 0
        a_mask = 0

        if is_compressed:
            flags = 0x4
            match tex.format.pixel_format:
                case datatypes.EPixelFormat.S3TC1:
                    four_cc = 827611204
                case datatypes.EPixelFormat.S3TC3:
                    four_cc = 861165636
                case datatypes.EPixelFormat.S3TC5:
                    four_cc = 894720068
        elif is_dx10:
            flags = 0x4
            four_cc = 808540228
        else:
            flags = 0x40
            if datatypes.EPixelFormat.RGBA_8888 <= tex.format.pixel_format <= datatypes.EPixelFormat.RGBA_4444_REV:
                flags |= 0x1

            bit_count = BITS_PER_PIXELS[tex.format.pixel_format]
            r_mask, g_mask, b_mask, a_mask = RGBA_MASKS[tex.format.pixel_format]

            data = deswizzle_morton_optimized(data, tex.format.width, tex.format.height, bit_count//8)

        file.write(pack("8I", 32, flags, four_cc, bit_count, r_mask, g_mask, b_mask, a_mask))

        file.write(pack("5I", caps, caps2, 0, 0, 0))

        if is_dx10:
            match tex.format.pixel_format:
                case datatypes.EPixelFormat.FLOAT_32:
                    fmt = 41
                case datatypes.EPixelFormat.RGB_FLOAT_32:
                    fmt = 6
                case datatypes.EPixelFormat.RGBA_FLOAT_32:
                    fmt = 2
                case datatypes.EPixelFormat.FLOAT_16:
                    fmt = 54
                case datatypes.EPixelFormat.RG_FLOAT_16:
                    fmt = 34
                case datatypes.EPixelFormat.RGB_FLOAT_16:
                    fmt = 10 # ?
                case datatypes.EPixelFormat.RGBA_FLOAT_16:
                    fmt = 10

            file.write(pack("5I", fmt, 3, 0, 1, 0x01))

        file.write(data)

def deswizzle_morton_optimized(data: bytes, width: int, height: int, bpp: int) -> bytes:
    # Calculate total pixels
    total_pixels = width * height
    
    # Create coordinate arrays
    y_coords, x_coords = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
    x_coords = x_coords.flatten()
    y_coords = y_coords.flatten()
    
    # Generate Morton indices
    max_coord = max(width, height)
    bits_needed = max_coord.bit_length()
    
    morton_indices = np.zeros(total_pixels, dtype=np.uint32)
    for i in range(bits_needed):
        morton_indices |= ((x_coords >> i) & 1).astype(np.uint32) << (2*i)
        morton_indices |= ((y_coords >> i) & 1).astype(np.uint32) << (2*i + 1)
    
    # Filter valid indices
    valid_mask = morton_indices < total_pixels
    morton_indices = morton_indices[valid_mask]
    linear_indices = np.arange(total_pixels, dtype=np.uint32)[valid_mask]
    
    # Convert to byte offsets
    src_offsets = morton_indices * bpp
    dst_offsets = linear_indices * bpp
    
    # Create output buffer
    deswizzled = bytearray(total_pixels * bpp)
    
    # Copy data (using numpy for efficient copying)
    data_array = np.frombuffer(data, dtype=np.uint8)
    for src_offset, dst_offset in zip(src_offsets, dst_offsets):
        deswizzled[dst_offset:dst_offset + bpp] = data_array[src_offset:src_offset + bpp].tobytes()
    
    return bytes(deswizzled)