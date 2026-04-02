from .reader import Reader
from .context import Context
import os

def read_core(filepath: str) -> Context:
    ctx = Context()

    stream_path = filepath + "stream"
    if os.path.exists(stream_path):
        ctx.stream_file = open(stream_path, "rb")

    try:
        with open(filepath, "rb") as file:
            reader = Reader(file)

            magic = reader.read(16)
            if not magic.startswith(b"RTTIBin") or magic[-1] != 1:
                raise RuntimeError("Invalid Killzone .core file")

            ctx.version = int(float(magic[8:12])*100)
            
            reader.skip(16)

            ctx.read_type_names(reader)
            ctx.read_object_types(reader)
            
            reader.skip_alloc_info_list()

            ctx.read_string_banks(reader)

            reader.read_var_int()

            reader.skip_alloc_info_list()

            try:
                ctx.read_objects_data(reader)
            except NotImplementedError:
                pass
            except:
                raise
    except:
        if ctx.stream_file:
            ctx.stream_file.close()
        raise

    return ctx
