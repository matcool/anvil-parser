from typing import Union, Tuple, Generator
from nbt import nbt
from .block import Block
from .region import Region
from .errors import OutOfBoundsCoordinates
import math

def bin_append(a, b, length=None):
    """
    Appends number a to the left of b
    bin_append(0b1, 0b10) = 0b110
    """
    length = length or b.bit_length()
    return (a << length) | b

class Chunk:
    __slots__ = ('version', 'data', 'x', 'z')

    def __init__(self, nbt_data: nbt.NBTFile):
        self.version = nbt_data['DataVersion']
        self.data = nbt_data['Level']
        self.x = self.data['xPos']
        self.z = self.data['zPos']
        
    def get_section(self, y: int) -> nbt.TAG_Compound:
        """
        Returns the section at given y index
        can also return nothing if section is missing, aka its empty

        Errors if y is not in range of 0 and 15
        """
        if y < 0 or y > 15:
            raise ValueError('Y index must be in the range of 0 to 15')
        for section in self.data['Sections']:
            if section['Y'].value == y:
                return section

    def get_palette(self, section: Union[int, nbt.TAG_Compound]) -> Tuple[Block]:
        """
        Returns the block palette for given section, which can either be nbt tags or the y index
        Output is a tuple of Blocks
        """
        if isinstance(section, int):
            section = self.get_section(section)
        if section is None:
            return
        return tuple(Block.from_palette(i) for i in section['Palette'])

    def get_block(self, x: int, y: int, z: int, section: Union[int, nbt.TAG_Compound]=None) -> Block:
        """
        Returns Block in the given coordinates, with them being relative to the chunk
        If section was not given, assumes Y is on global coords and gets section from it,
        else uses the section and assumes Y is relative to the section
        """
        if x < 0 or x > 15 or z < 0 or z > 15:
            raise ValueError('X and Z must be in the range of 0 to 15')
        if y < 0 or y > 255:
            raise ValueError('Y must be in the range of 0 to 255')
        
        if section is None:
            section = self.get_section(y // 16)
            # global Y to section Y
            y %= 16

        # If its an empty section its most likely an air block 
        if section is None or section.get('BlockStates') is None:
            return Block.from_name('minecraft:air')

        # Number of bits each block is on BlockStates
        # Cannot be lower than 4
        bits = max((len(section['Palette']) - 1).bit_length(), 4)

        # Get index on the block list with the order YZX
        index = y * 16*16 + z * 16 + x

        # BlockStates is an array of 64 bit numbers
        # that holds the blocks index on the palette list
        states = section['BlockStates'].value
        
        # get location in the BlockStates array via the index
        state = index * bits // 64

        # makes sure the number is unsigned
        # by adding 2^64
        # could also use ctypes.c_ulonglong(n).value but that'd require an extra import
        data = states[state]
        if data < 0:
            data += 2**64

        # shift the number to the right to remove the left over bits
        # and shift so the i'th block is the first one
        shifted_data = data >> ((bits * index) % 64)

        # if there arent enough bits it means the rest are in the next number
        if 64 - ((bits * index) % 64) < bits:
            data = states[state + 1]
            if data < 0:
                data += 2**64
            # get how many bits are from a palette index of the next block
            leftover = (bits - ((state + 1) * 64 % bits)) % bits

            # Make sure to keep the length of the bits in the first state
            # Example: bits is 5, and leftover is 3
            # Next state                Current state (already shifted)
            # 0b101010110101101010010   0b01
            # will result in bin_append(0b010, 0b01, 2) = 0b01001
            shifted_data = bin_append(data & 2**leftover - 1, shifted_data, bits-leftover)
        
        # get `bits` least significant bits
        # which are the palette index
        palette_id = shifted_data & 2**bits - 1

        block = section['Palette'][palette_id]
        return Block.from_palette(block)

    def stream_blocks(self, index: int=0, section: Union[int, nbt.TAG_Compound]=None) -> Generator[Block, None, None]:
        if isinstance(section, int) and (section < 0 or section > 16):
            raise OutOfBoundsCoordinates()

        # For better understanding of this code, read get_block()'s source

        if section is None or isinstance(section, int):
            section = self.get_section(section or 0)

        if section is None or section.get('BlockStates') is None:
            return Block.from_name('minecraft:air')

        states = section['BlockStates'].value
        palette = section['Palette']

        bits = max((len(palette) - 1).bit_length(), 4)

        state = index * bits // 64

        data = states[state]
        if data < 0:
            data += 2**64

        bits_mask = 2**bits - 1

        offset = (bits * index) % 64

        data_len = 64 - offset
        data >>= offset

        while index < 4096:
            if data_len < bits:
                state += 1
                new_data = states[state]
                if new_data < 0:
                    new_data += 2**64

                leftover = data_len
                data_len += 64

                data = bin_append(new_data, data, leftover)

            palette_id = data & bits_mask
            yield Block.from_palette(palette[palette_id])

            index += 1
            data >>= bits
            data_len -= bits
        
    @classmethod
    def from_region(cls, region: Union[str, Region], chunkX: int, chunkZ: int):
        """
        Creates a new chunk from region and the chunk's X and Z
        region can either be the name of the region file, or a Region object
        """
        if isinstance(region, str):
            region = Region.from_file(region)
        nbt_data = region.chunk_data(chunkX, chunkZ)
        if nbt_data is None:
            raise Exception('Unexistent chunk')
        return cls(nbt_data)
