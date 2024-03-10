from typing import Union, Tuple, Generator, Optional
from nbt import nbt
from .biome import Biome
from .block import Block, OldBlock
from .region import Region
from .errors import OutOfBoundsCoordinates, ChunkNotFound
from .versions import VERSION_21w43a, VERSION_20w17a, VERSION_19w36a, VERSION_17w47a, VERSION_PRE_15w32a


def bin_append(a, b, length=None):
    """
    Appends number a to the left of b
    bin_append(0b1, 0b10) = 0b110
    """
    length = length or b.bit_length()
    return (a << length) | b


def nibble(byte_array, index):
    value = byte_array[index // 2]
    if index % 2:
        return value >> 4
    else:
        return value & 0b1111


def _palette_from_section(section: nbt.TAG_Compound) -> nbt.TAG_List:
    if 'block_states' in section:
        return section["block_states"]["palette"]
    else:
        return section["Palette"]


def _states_from_section(section: nbt.TAG_Compound) -> list:
        # BlockStates is an array of 64 bit numbers
        # that holds the blocks index on the palette list
        if 'block_states' in section:
            states = section['block_states']['data']
        else:
            states = section['BlockStates']

        # makes sure the number is unsigned
        # by adding 2^64
        # could also use ctypes.c_ulonglong(n).value but that'd require an extra import

        return [state if state >= 0 else states + 2 ** 64 
            for state in states.value]


def _section_height_range(version: Optional[int]) -> range:
    if version > VERSION_17w47a:
        return range(-4, 20)
    else:
        return range(16)


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
    tile_entities: :class:`nbt.TAG_Compound`
        ``self.data['TileEntities']`` as an attribute for easier use
    """

    __slots__ = ("version", "data", "x", "z", "tile_entities")

    def __init__(self, nbt_data: nbt.NBTFile):
        try:
            self.version = nbt_data["DataVersion"].value
        except KeyError:
            # Version is pre-1.9 snapshot 15w32a, so world does not have a Data Version.
            # See https://minecraft.wiki/w/Data_version
            self.version = VERSION_PRE_15w32a

        if self.version >= VERSION_21w43a:
            self.data = nbt_data
            self.tile_entities = self.data["block_entities"]
        else:
            self.data = nbt_data["Level"]
            self.tile_entities = self.data["TileEntities"]
        self.x = self.data["xPos"].value
        self.z = self.data["zPos"].value

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
        anvil.OutOfBoundsCoordinates
            If Y is not in range of 0 to 15
        """
        section_range = _section_height_range(self.version)
        if y not in section_range:
            raise OutOfBoundsCoordinates(f"Y ({y!r}) must be in range of "
                f"{section_range.start} to {section_range.stop}")

        if 'sections' in self.data:
            sections = self.data["sections"]
        else:
            try:
                sections = self.data["Sections"]
            except KeyError:
                return None

        for section in sections:
            if section["Y"].value == y:
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
        palette = _palette_from_section(section)
        return tuple(Block.from_palette(i) for i in palette)

    def get_biome(self, x: int, y: int, z: int) -> Biome:
        """
        Returns the biome in the given coordinates

        Parameters
        ----------
        int x, y, z
            Biome's coordinates in the chunk

        Raises
        ------
        anvil.OutOfBoundCoordidnates
            If X, Y or Z are not in the proper range

        :rtype: :class:`anvil.Biome`
        """
        section_range = _section_height_range(self.version)
        if x not in range(16):
            raise OutOfBoundsCoordinates(f"X ({x!r}) must be in range of 0 to 15")
        if z not in range(16):
            raise OutOfBoundsCoordinates(f"Z ({z!r}) must be in range of 0 to 15")
        if y // 16 not in section_range:
            raise OutOfBoundsCoordinates(f"Y ({y!r}) must be in range of "
                f"{section_range.start * 16} to {section_range.stop * 16 - 1}")
        
        if 'Biomes' not in self.data:
            # Each biome index refers to a 4x4x4 volumes here so we do integer division by 4
            section = self.get_section(y // 16)
            biomes = section['biomes']
            biomes_palette = biomes['palette']
            if 'data' in biomes:
                biomes = biomes['data']
            else:
                # When there is only one biome in the section of the palette 'data'
                # is not present
                return Biome.from_name(biomes_palette[0].value)


            index = ((y % 16 // 4) * 4 * 4) + (z // 4) * 4 + (x // 4)
            bits = (len(biomes_palette) - 1).bit_length()
            state = index * bits // 64
            data = biomes[state]

            # shift the number to the right to remove the left over bits
            # and shift so the i'th biome is the first one
            shifted_data = data >> ((bits * index) % 64)

            # if there aren't enough bits it means the rest are in the next number
            if 64 - ((bits * index) % 64) < bits:
                data = biomes[state + 1]

                # get how many bits are from a palette index of the next biome
                leftover = (bits - ((state + 1) * 64 % bits)) % bits

                # Make sure to keep the length of the bits in the first state
                # Example: bits is 5, and leftover is 3
                # Next state                Current state (already shifted)
                # 0b101010110101101010010   0b01
                # will result in bin_append(0b010, 0b01, 2) = 0b01001
                shifted_data = bin_append(
                    data & 2**leftover - 1, shifted_data, bits - leftover
                )

            palette_id = shifted_data & 2**bits - 1
            return Biome.from_name(biomes_palette[palette_id].value)

        else:
            biomes = self.data["Biomes"]
            if self.version < VERSION_19w36a:
                # Each biome index refers to a column stored Z then X.
                index = z * 16 + x
            else:
                # https://minecraft.wiki/w/Java_Edition_19w36a
                # Get index on the biome list with the order YZX
                # Each biome index refers to a 4x4 areas here so we do integer division by 4
                index = (y // 4) * 4 * 4 + (z // 4) * 4 + (x // 4)
            biome_id = biomes[index]
            return Biome.from_numeric_id(biome_id)

    def get_block(
        self,
        x: int,
        y: int,
        z: int,
        section: Union[int, nbt.TAG_Compound] = None,
        force_new: bool = False,
    ) -> Union[Block, OldBlock]:
        """
        Returns the block in the given coordinates

        Parameters
        ----------
        int x, y, z
            Block's coordinates in the chunk
        section : int
            Either a section NBT tag or an index. If no section is given,
            assume Y is global and use it for getting the section.
        force_new
            Always returns an instance of Block if True, otherwise returns type OldBlock for pre-1.13 versions.
            Defaults to False

        Raises
        ------
        anvil.OutOfBoundCoordidnates
            If X, Y or Z are not in the proper range

        :rtype: :class:`anvil.Block`
        """
        if x not in range(16):
            raise OutOfBoundsCoordinates(f"X ({x!r}) must be in range of 0 to 15")
        if z not in range(16):
            raise OutOfBoundsCoordinates(f"Z ({z!r}) must be in range of 0 to 15")
        section_range = _section_height_range(self.version)
        if y // 16 not in section_range:
            raise OutOfBoundsCoordinates(f"Y ({y!r}) must be in range of "
                f"{section_range.start * 16} to {section_range.stop * 16 - 1}")

        if section is None:
            section = self.get_section(y // 16)
            # global Y to section Y
            y %= 16

        if self.version < VERSION_17w47a:
            # Explained in depth here https://minecraft.wiki/w/index.php?title=Chunk_format&oldid=1153403#Block_format

            if section is None or "Blocks" not in section:
                if force_new:
                    return Block.from_name("minecraft:air")
                else:
                    return OldBlock(0)

            index = y * 16 * 16 + z * 16 + x

            block_id = section["Blocks"][index]
            if "Add" in section:
                block_id += nibble(section["Add"], index) << 8

            block_data = nibble(section["Data"], index)

            block = OldBlock(block_id, block_data)
            if force_new:
                return block.convert()
            else:
                return block

        # If its an empty section its most likely an air block
        if section is None:
            return Block.from_name("minecraft:air")
        try:
            states = _states_from_section(section)
        except KeyError:
            return Block.from_name("minecraft:air")
            
        # Number of bits each block is on BlockStates
        # Cannot be lower than 4
        palette = _palette_from_section(section)

        bits = max((len(palette) - 1).bit_length(), 4)

        # Get index on the block list with the order YZX
        index = y * 16 * 16 + z * 16 + x
        # in 20w17a and newer blocks cannot occupy more than one element on the BlockStates array
        stretches = self.version < VERSION_20w17a

        # get location in the BlockStates array via the index
        if stretches:
            state = index * bits // 64
        else:
            state = index // (64 // bits)

        data = states[state]

        if stretches:
            # shift the number to the right to remove the left over bits
            # and shift so the i'th block is the first one
            shifted_data = data >> ((bits * index) % 64)
        else:
            shifted_data = data >> (index % (64 // bits) * bits)

        # if there aren't enough bits it means the rest are in the next number
        if stretches and 64 - ((bits * index) % 64) < bits:
            data = states[state + 1]

            # get how many bits are from a palette index of the next block
            leftover = (bits - ((state + 1) * 64 % bits)) % bits

            # Make sure to keep the length of the bits in the first state
            # Example: bits is 5, and leftover is 3
            # Next state                Current state (already shifted)
            # 0b101010110101101010010   0b01
            # will result in bin_append(0b010, 0b01, 2) = 0b01001
            shifted_data = bin_append(
                data & 2**leftover - 1, shifted_data, bits - leftover
            )

        # get `bits` least significant bits
        # which are the palette index
        palette_id = shifted_data & 2**bits - 1
        return Block.from_palette(palette[palette_id])

    def stream_blocks(
        self,
        index: int = 0,
        section: Union[int, nbt.TAG_Compound] = None,
        force_new: bool = False,
    ) -> Generator[Block, None, None]:
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
        force_new
            Always returns an instance of Block if True, otherwise returns type OldBlock for pre-1.13 versions.
            Defaults to False

        Raises
        ------
        anvil.OutOfBoundCoordidnates
            If `section` is not in the range of 0 to 15

        Yields
        ------
        :class:`anvil.Block`
        """

        if isinstance(section, int):
            section_range = _section_height_range(self.version)
            if section not in section_range:
                raise OutOfBoundsCoordinates(f"section ({section!r}) must be in range of "
                    f"{section_range.start} to {section_range.stop}")

        # For better understanding of this code, read get_block()'s source

        if section is None or isinstance(section, int):
            section = self.get_section(section or 0)

        if self.version < VERSION_17w47a:
            if section is None or "Blocks" not in section:
                air = Block.from_name("minecraft:air") if force_new else OldBlock(0)
                for _ in range(4096):
                    yield air
                return

            while index < 4096:
                block_id = section["Blocks"][index]
                if "Add" in section:
                    block_id += nibble(section["Add"], index) << 8

                block_data = nibble(section["Data"], index)

                block = OldBlock(block_id, block_data)
                if force_new:
                    yield block.convert()
                else:
                    yield block

                index += 1
            return

        air = Block.from_name("minecraft:air")
        if section is None:
            for _ in range(4096):
                yield air
            return
        try:
            states = _states_from_section(section)
        except KeyError:
            for _ in range(4096):
                yield air
            return

        palette = _palette_from_section(section)
        bits = max((len(palette) - 1).bit_length(), 4)

        stretches = self.version < VERSION_20w17a

        if stretches:
            state = index * bits // 64
        else:
            state = index // (64 // bits)

        data = states[state]

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

    def stream_chunk(
        self, index: int = 0, section: Union[int, nbt.TAG_Compound] = None
    ) -> Generator[Block, None, None]:
        """
        Returns a generator for all the blocks in the chunk

        This is a helper function that runs Chunk.stream_blocks from section 0 to 15

        Yields
        ------
        :class:`anvil.Block`
        """
        for section in _section_height_range(self.version):
            for block in self.stream_blocks(section=section):
                yield block

    def get_tile_entity(self, x: int, y: int, z: int) -> Optional[nbt.TAG_Compound]:
        """
        Returns the tile entity at given coordinates, or ``None`` if there isn't a tile entity

        To iterate through all tile entities in the chunk, use :class:`Chunk.tile_entities`
        """
        for tile_entity in self.tile_entities:
            t_x, t_y, t_z = [tile_entity[k].value for k in "xyz"]
            if x == t_x and y == t_y and z == t_z:
                return tile_entity

    @classmethod
    def from_region(cls, region: Union[str, Region], chunk_x: int, chunk_z: int):
        """
        Creates a new chunk from region and the chunk's X and Z

        Parameters
        ----------
        region
            Either a :class:`anvil.Region` or a region file name (like ``r.0.0.mca``)

        Raises
        ----------
        anvil.ChunkNotFound
            If a chunk is outside this region or hasn't been generated yet
        """
        if isinstance(region, str):
            region = Region.from_file(region)
        nbt_data = region.chunk_data(chunk_x, chunk_z)
        if nbt_data is None:
            raise ChunkNotFound(f"Could not find chunk ({chunk_x}, {chunk_z})")
        return cls(nbt_data)
