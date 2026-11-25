from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, ClassVar

@dataclass
class SMBIOSStructure:
    """One structure of an SMBIOS table (DMTF DSP0134, 6.1.2): the formatted area and its string set."""

    type: int
    handle: int
    data: bytes  # formatted area, including the 4-byte header
    strings: List[str]

    def byte(self, offset: int) -> Optional[int]:
        return self.data[offset] if offset + 1 <= len(self.data) else None

    def word(self, offset: int) -> Optional[int]:
        return int.from_bytes(self.data[offset:offset + 2], "little") if offset + 2 <= len(self.data) else None

    def dword(self, offset: int) -> Optional[int]:
        return int.from_bytes(self.data[offset:offset + 4], "little") if offset + 4 <= len(self.data) else None

    def string(self, offset: int) -> Optional[str]:
        index = self.byte(offset)
        if index is None or not 1 <= index <= len(self.strings):
            return None
        return self.strings[index - 1].strip() or None

class SMBIOS:
    """Reader for the raw SMBIOS structure table, as exposed by Linux at /sys/firmware/dmi/tables/DMI (root only)."""

    TABLE: Path = Path("/sys/firmware/dmi/tables/DMI")
    END_OF_TABLE: int = 127

    @staticmethod
    def parse(table: bytes) -> List[SMBIOSStructure]:
        structures: List[SMBIOSStructure] = []
        position = 0

        while position + 4 <= len(table):
            type, length = table[position], table[position + 1]
            formatted_end = position + length
            if length < 4 or formatted_end > len(table):
                break

            # The string set follows the formatted area and ends with two NUL bytes.
            strings_end = table.find(b"\0\0", formatted_end)
            if strings_end == -1:
                break
            area = table[formatted_end:strings_end]
            strings = [raw.decode("utf-8", errors="replace") for raw in area.split(b"\0")] if area else []

            structures.append(SMBIOSStructure(
                type=type,
                handle=int.from_bytes(table[position + 2:position + 4], "little"),
                data=table[position:formatted_end],
                strings=strings,
            ))

            if type == SMBIOS.END_OF_TABLE:
                break
            position = strings_end + 2

        return structures

    @staticmethod
    def read(path: Path = TABLE) -> Optional[List[SMBIOSStructure]]:
        try:
            return SMBIOS.parse(path.read_bytes())
        except OSError:
            return None

@dataclass
class SMBIOSMemoryDevice:
    """SMBIOS Memory Device (Type 17, DMTF DSP0134 7.18)."""

    TYPE: ClassVar[int] = 17

    # Memory Device — Type (7.18.2), indexed from 0x01
    MEMORY_TYPES: ClassVar[Tuple[str, ...]] = (
        "Other", "Unknown", "DRAM", "EDRAM", "VRAM", "SRAM", "RAM", "ROM", "Flash", "EEPROM", "FEPROM", "EPROM", "CDRAM", "3DRAM", "SDRAM", "SGRAM",
        "RDRAM", "DDR", "DDR2", "DDR2 FB-DIMM", "Reserved", "Reserved", "Reserved", "DDR3", "FBD2", "DDR4", "LPDDR", "LPDDR2", "LPDDR3", "LPDDR4", "Logical non-volatile device", "HBM",
        "HBM2", "DDR5", "LPDDR5", "HBM3",
    )

    locator: Optional[str]
    bank_locator: Optional[str]
    manufacturer: Optional[str]
    type: Optional[str]
    installed: bool
    size: Optional[int]               # bytes; None if unknown, 0 if no module is installed
    speed: Optional[int]              # MT/s, maximum rated
    configured_speed: Optional[int]   # MT/s, currently configured

    @classmethod
    def from_structure(cls, structure: SMBIOSStructure) -> "SMBIOSMemoryDevice":
        if structure.type != cls.TYPE:
            raise ValueError(f"Not a Memory Device structure: type {structure.type}")

        size_code = structure.word(0x0C)
        installed = size_code != 0
        size: Optional[int] = None
        if size_code == 0:
            size = 0
        elif size_code == 0x7FFF:
            extended = structure.dword(0x1C)
            size = (extended & 0x7FFFFFFF) * 1024 * 1024 if extended is not None else None
        elif size_code is not None and size_code != 0xFFFF:
            size = (size_code & 0x7FFF) * (1024 if size_code & 0x8000 else 1024 * 1024)

        type_code = structure.byte(0x12)
        type: Optional[str] = None
        if type_code is not None and 1 <= type_code <= len(cls.MEMORY_TYPES):
            type = cls.MEMORY_TYPES[type_code - 1]
        if type in ("Unknown", "Reserved"):
            type = None

        return cls(
            locator=structure.string(0x10),
            bank_locator=structure.string(0x11),
            manufacturer=structure.string(0x17),
            type=type,
            installed=installed,
            size=size,
            speed=cls.read_speed(structure, 0x15, 0x54),
            configured_speed=cls.read_speed(structure, 0x20, 0x58),
        )

    @staticmethod
    def read_speed(structure: SMBIOSStructure, offset: int, extended_offset: int) -> Optional[int]:
        speed = structure.word(offset)
        if speed == 0xFFFF:
            extended = structure.dword(extended_offset)
            speed = extended & 0x7FFFFFFF if extended is not None else None
        return speed or None
