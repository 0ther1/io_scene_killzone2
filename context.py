from typing import TYPE_CHECKING, BinaryIO
from . import datatypes

if TYPE_CHECKING:
    from .reader import Reader
else:
    class Reader:
        pass

class Context:
    type_names: list[str]
    objects: list[datatypes.BaseObject]
    object_dict: dict[str, datatypes.BaseObject]
    string_banks: dict[str, list[str]]
    stream_file: BinaryIO|None

    def __init__(self):
        self.type_names = []
        self.objects = []
        self.object_dict = dict()
        self.string_banks = dict()
        self.version = 0
        self.stream_file = None

    def read_type_names(self, r: Reader):
        count = r.read_var_int()
        self.type_names = [r.read_string() for _ in range(count)]

    def read_type_index(self, r: Reader) -> str:
        return self.type_names[r.read_var_index(len(self.type_names))]
    
    def read_string_banks(self, r: Reader):
        self.string_banks = dict()

        count = r.read_var_int()
        for _ in range(count):
            type_name = self.read_type_index(r)
            string_count = r.read_var_int()
            self.string_banks[type_name] = [r.read_typed_string(type_name) for _ in range(string_count)]

    def read_string_index(self, r: Reader, type_name: str="String") -> str:
        bank = self.string_banks[type_name]
        idx = r.read_var_index(len(bank))
        return bank[idx]
    
    def skip_string_index(self, r: Reader, type_name: str="String", count: int=1):
        bank = self.string_banks[type_name]

        size = 1
        if len(bank) > 0x10000:
            size = 4
        elif len(bank) > 0x100:
            size = 2

        r.skip(size*count)

    def read_object_types(self, r: Reader):
        count = r.read_var_int()
        self.objects = [getattr(datatypes, self.read_type_index(r), datatypes.BaseObject)() for _ in range(count)]
        self.object_dict = dict()

        if self.version == 173:
            r.read_var_int()

        for obj in self.objects:
            raw_id = r.read(16)
            arr = bytearray()

            for i in range(0, 16, 4):
                arr.extend(raw_id[i:i+4][::-1])

            obj.id = arr.hex()
            obj.read_size = r.unpack(">I")[0]

            if self.version < 173:
                r.skip(12)

            self.object_dict[obj.id] = obj

    def read_object_ref(self, r: Reader, parse: bool=False) -> datatypes.BaseObject|str|None:
        ref_type = r.read(1)[0]
        obj = None
        match ref_type:
            case 0:
                idx = r.read_var_index(len(self.objects) + 1)
                if idx:
                    obj = self.objects[idx-1]
            case 2:
                id = r.read_string()
                obj = self.object_dict.get(id, id)
            case _:
                raise RuntimeError(f"Unexpected reference type {ref_type}")
            
        if isinstance(obj, datatypes.BaseObject) and parse:
            obj.parse(self)

        return obj
    
    def skip_object_ref(self, r: Reader, count: int=1):
        size = 1
        if len(self.objects) + 1 > 0x10000:
            size = 4
        elif len(self.objects) + 1 > 0x100:
            size = 2

        for _ in range(count):
            ref_type = r.read(1)[0]
            match ref_type:
                case 0:
                    r.skip(size)
                case 2:
                    r.skip_string()
                case _:
                    raise RuntimeError(f"Unexpected reference type {ref_type}")
    
    def read_objects_data(self, r: Reader):
        for obj in self.objects:
            r.skip_alloc_info_list()
            r.skip_alloc_info_list()
            obj.read(r, self)
