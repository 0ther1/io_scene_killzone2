from typing import BinaryIO, Any
from io import SEEK_CUR
from struct import unpack, calcsize

class Reader:
    def __init__(self, f: BinaryIO):
        self.f = f

    def read(self, size: int = -1) -> bytes:
        return self.f.read(size)
    
    def tell(self) -> int:
        return self.f.tell()
    
    def skip(self, count: int):
        self.f.seek(count, SEEK_CUR)

    def skip_array(self, item_size: int):
        count = self.read_var_int()
        self.skip(count*item_size)

    def align(self, offset: int = 0, alignment: int = 4):
        padding = (alignment - ((self.f.tell() + offset) % alignment)) % alignment
        self.skip(padding)
    
    def unpack(self, format: str) -> Any:
        return unpack(format, self.read(calcsize(format)))
    
    def skip_alloc_info_list(self):
        count = self.read_var_int()
        for _ in range(count*5):
            self.read_var_int()
    
    def read_var_int(self) -> int:
        value = self.read(1)[0]
        match value:
            case 129:
                return self.unpack(">H")[0]
            case 128:
                return self.unpack(">I")[0]
        return value
            
    def read_string(self, char_size: int=1, encoding: str="utf-8") -> str:
        length = self.read_var_int()
        return self.read(length*char_size).decode(encoding)
    
    def skip_string(self, char_size: int=1):
        length = self.read_var_int()
        self.skip(length*char_size)
    
    def read_typed_string(self, type_name: str) -> str:
        self.read_var_int()

        char_size = 1
        encoding = "utf-8"
        if type_name == "WString":
            char_size = 2
            encoding = "utf-16_be"

        length = self.read(1)[0]
        match length:
            case 254:
                length = self.unpack(">H")[0]
            case 255:
                length = self.unpack(">I")[0]

        return self.read(length*char_size).decode(encoding)
    
    def read_var_index(self, count: int) -> int:
        match count:
            case int() if count > 0x10000:
                return self.unpack(">I")[0]
            case int() if count > 0x100:
                return self.unpack(">H")[0]
        return self.unpack(">B")[0]
            