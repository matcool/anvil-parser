from typing import Union, Tuple, Generator
from nbt import nbt
from .block import Block
from .region import Region
from .errors import OutOfBoundsCoordinates
import math


# This version removes block state value stretching from the storage
# so a block value isn't in multiple elements of the array
_VERSION_20w17a = 2529

def bin_append(a, b, length=None):
    """
    Appends number a to the left of b
    bin_append(0b1, 0b10) = 0b110
    """
    length = length or b.bit_length()
    return (a << length) | b

class Chunk:
    """
    Represents a chunk from a ``.mca`` file.

    Note that this is read only.

    Attributes
    ----------
    x: :class:`int`
        Chunk's X position
    z: :class:`int`
        Chunk's Z position
    version: :class:`int`
        Version of the chunk NBT structure
    data: :class:`nbt.TAG_Compound`
        Raw NBT data of the chunk
    """
    __slots__ = ('version', 'data', 'x', 'z')

    def __init__(self, nbt_data: nbt.NBTFile):
        self.version = nbt_data['DataVersion'].value
        self.data = nbt_data['Level']
        self.x = self.data['xPos'].value
        self.z = self.data['zPos'].value
        
    def get_section(self, y: int) -> nbt.TAG_Compound:
        """
        Returns the section at given y index
        can also return nothing if section is missing, aka it's empty

        Parameters
        ----------
        y
            Section Y index

        Raises
        ------
        ValueError
            If Y is not in range of 0 and 15
        """
        if y < 0 or y > 15:
            raise ValueError('Y index must be in the range of 0 to 15')

        try:
            sections = self.data["Sections"]
        except KeyError:
            return None

        for section in sections:
            if section['Y'].value == y:
                return section

    def get_palette(self, section: Union[int, nbt.TAG_Compound]) -> Tuple[Block]:
        """
        Returns the block palette for given section

        Parameters
        ----------
        section
            Either a section NBT tag or an index


        :rtype: Tuple[:class:`anvil.Block`]
        """
        if isinstance(section, int):
            section = self.get_section(section)
        if section is None:
            return
        return tuple(Block.from_palette(i) for i in section['Palette'])

    def get_block(self, x: int, y: int, z: int, section: Union[int, nbt.TAG_Compound]=None) -> Block:
        """
        Returns the block in the given coordinates

        Parameters
        ----------
        int x, y, z
            Block's coordinates in the chunk
        section : int
            Either a section NBT tag or an index. If no section is given,
            assume Y is global and use it for getting the section.

        Raises
        ------
        ValueError
            If X or Z aren't in the range of 0 to 15,
            or if Y isn't in the range of 0 to 255

        
        :rtype: :class:`anvil.Block`
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

        # in 20w17a and newer blocks cannot occupy more than one element on the BlockStates array
        stretches = self.version < _VERSION_20w17a
        # stretches = True

        # get location in the BlockStates array via the index
        if stretches:
            state = index * bits // 64
        else:
            state = index // (64 // bits)

        # makes sure the number is unsigned
        # by adding 2^64
        # could also use ctypes.c_ulonglong(n).value but that'd require an extra import
        data = states[state]
        if data < 0:
            data += 2**64

        if stretches:
            # shift the number to the right to remove the left over bits
            # and shift so the i'th block is the first one
            shifted_data = data >> ((bits * index) % 64)
        else:
            shifted_data = data >> (index % (64 // bits) * bits)

        # if there aren't enough bits it means the rest are in the next number
        if stretches and 64 - ((bits * index) % 64) < bits:
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
        """
        Returns a generator for all the blocks in given section

        Parameters
        ----------
        index
            At what block to start from.

            To get an index from (x, y, z), simply do:

            ``y * 256 + z * 16 + x``
        section
            Either a Y index or a section NBT tag.

        Yields
        ------
        :class:`anvil.Block`
        """
        if isinstance(section, int) and (section < 0 or section > 16):
            raise OutOfBoundsCoordinates()

        # For better understanding of this code, read get_block()'s source

        if section is None or isinstance(section, int):
            section = self.get_section(section or 0)

        if section is None or section.get('BlockStates') is None:
            air = Block.from_name('minecraft:air')
            for i in range(4096):
                yield air

        states = section['BlockStates'].value
        palette = section['Palette']

        bits = max((len(palette) - 1).bit_length(), 4)

        stretches = self.version < _VERSION_20w17a

        if stretches:
            state = index * bits // 64
        else:
            state = index // (64 // bits)

        data = states[state]
        if data < 0:
            data += 2**64

        bits_mask = 2**bits - 1

        if stretches:
            offset = (bits * index) % 64
        else:
            offset = index % (64 // bits) * bits

        data_len = 64 - offset
        data >>= offset

        while index < 4096:
            if data_len < bits:
                state += 1
                new_data = states[state]
                if new_data < 0:
                    new_data += 2**64

                if stretches:
                    leftover = data_len
                    data_len += 64

                    data = bin_append(new_data, data, leftover)
                else:
                    data = new_data
                    data_len = 64

            palette_id = data & bits_mask
            yield Block.from_palette(palette[palette_id])

            index += 1
            data >>= bits
            data_len -= bits
        
    @classmethod
    def from_region(cls, region: Union[str, Region], chunkX: int, chunkZ: int):
        """
        Creates a new chunk from region and the chunk's X and Z

        Parameters
        ----------
        region
            Either a :class:`anvil.Region` or a region file name (like ``r.0.0.mca``)
        """
        if isinstance(region, str):
            region = Region.from_file(region)
        nbt_data = region.chunk_data(chunkX, chunkZ)
        if nbt_data is None:
            raise Exception('Unexistent chunk')
        return cls(nbt_data)
