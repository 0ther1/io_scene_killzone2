from .reader import Reader
from .context import Context

def read_core(filepath: str) -> Context:
    ctx = Context()
    with open(filepath, "rb") as file:
        reader = Reader(file)

        if reader.read(16) != b"RTTIBin<1.58>  \x01":
            raise RuntimeError("Invalid Killzone 2 .core file")
        
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
