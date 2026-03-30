from .reader import Reader
from .context import Context

def read_core(filepath: str) -> Context:
    ctx = Context()
    with open(filepath, "rb") as file:
        reader = Reader(file)

        magic = reader.read(16)
        if not magic.startswith(b"RTTIBin") or magic[-1] != 1:
            raise RuntimeError("Invalid Killzone 2 .core file")

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

    return ctx
