from typing import Union, List, BinaryIO
from .empty_chunk import EmptyChunk
from .chunk import Chunk
from .empty_section import EmptySection
from .block import Block
from .errors import OutOfBoundsCoordinates
from io import BytesIO
from nbt import nbt
import zlib
import math

def from_inclusive(a, b):
    """Returns a range from a to b, including both endpoints"""
    c = int(b > a)*2-1
    return range(a, b+c, c)

class EmptyRegion:
    """
    Used for making own regions
    
    Attributes
    ----------
    chunks: List[:class:`anvil.EmptyChunk`]
        List of chunks in this region
    x: :class:`int`
    z: :class:`int`
    """
    __slots__ = ('chunks', 'x', 'z')
    def __init__(self, x: int, z: int):
        # Create a 1d list for the 32x32 chunks
        self.chunks: List[EmptyChunk] = [None] * 1024
        self.x = x
        self.z = z

    def inside(self, x: int, y: int, z: int, chunk: bool=False) -> bool:
        """
        Returns if the given coordinates are inside this region
        
        Parameters
        ----------
        int x, y, z
            Coordinates
        chunk
            Whether coordinates are global or chunk coordinates
        """
        factor = 32 if chunk else 512
        rx = x // factor
        rz = z // factor
        return not (rx != self.x or rz != self.z or y < 0 or y > 255)

    def get_chunk(self, x: int, z: int) -> EmptyChunk:
        """
        Returns the chunk at given chunk coordinates
        
        Parameters
        ----------
        int x, z
            Chunk's coordinates

        Raises
        ------
        anvil.OutOfBoundCoordidnates
            If the chunk (x, z) is not inside this region

        :rtype: :class:`anvil.EmptyChunk`
        """
        if not self.inside(x, 0, z, chunk=True):
            raise OutOfBoundsCoordinates(f'Chunk ({x}, {z}) is not inside this region')
        return self.chunks[z % 32 * 32 + x % 32]

    def add_chunk(self, chunk: EmptyChunk):
        """
        Adds given chunk to this region.
        Will overwrite if a chunk already exists in this location

        Parameters
        ----------
        chunk: :class:`EmptyChunk`
        
        Raises
        ------
        anvil.OutOfBoundCoordidnates
            If the chunk (x, z) is not inside this region
        """
        if not self.inside(chunk.x, 0, chunk.z, chunk=True):
            raise OutOfBoundsCoordinates(f'Chunk ({chunk.x}, {chunk.z}) is not inside this region')
        self.chunks[chunk.z % 32 * 32 + chunk.x % 32] = chunk

    def add_section(self, section: EmptySection, x: int, z: int, replace: bool=True):
        """
        Adds section to chunk at (x, z).
        Same as ``EmptyChunk.add_section(section)``

        Parameters
        ----------
        section: :class:`EmptySection`
            Section to add
        int x, z
            Chunk's coordinate
        replace
            Whether to replace section if it already exists in the chunk
        
        Raises
        ------
        anvil.OutOfBoundsCoordinates
            If the chunk (x, z) is not inside this region
        """
        if not self.inside(x, 0, z, chunk=True):
            raise OutOfBoundsCoordinates(f'Chunk ({x}, {z}) is not inside this region')
        chunk = self.chunks[z % 32 * 32 + x % 32]
        if chunk is None:
            chunk = EmptyChunk(x, z)
            self.add_chunk(chunk)
        chunk.add_section(section, replace)

    def set_block(self, block: Block, x: int, y: int, z: int):
        """
        Sets block at given coordinates.
        New chunk is made if it doesn't exist.

        Parameters
        ----------
        block: :class:`Block`
            Block to place
        int x, y, z
            Coordinates

        Raises
        ------
        anvil.OutOfBoundsCoordinates
            If the block (x, y, z) is not inside this region
        """
        if not self.inside(x, y, z):
            raise OutOfBoundsCoordinates(f'Block ({x}, {y}, {z}) is not inside this region')
        cx = x // 16
        cz = z // 16
        chunk = self.get_chunk(cx, cz)
        if chunk is None:
            chunk = EmptyChunk(cx, cz)
            self.add_chunk(chunk)
        chunk.set_block(block, x % 16, y, z % 16)

    def set_if_inside(self, block: Block, x: int, y: int, z: int):
        """
        Helper function that only sets
        the block if ``self.inside(x, y, z)`` is true
        
        Parameters
        ----------
        block: :class:`Block`
            Block to place
        int x, y, z
            Coordinates
        """
        if self.inside(x, y, z):
            self.set_block(block, x, y, z)

    def fill(self, block: Block, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, ignore_outside: bool=False):
        """
        Fills in blocks from
        ``(x1, y1, z1)`` to ``(x2, y2, z2)``
        in a rectangle.

        Parameters
        ----------
        block: :class:`Block`
        int x1, y1, z1
            Coordinates
        int x2, y2, z2
            Coordinates
        ignore_outside
            Whether to ignore if coordinates are outside the region

        Raises
        ------
        anvil.OutOfBoundsCoordinates
            If any of the coordinates are outside the region
        """
        if not ignore_outside:
            if not self.inside(x1, y1, z1):
                raise OutOfBoundsCoordinates(f'First coords ({x1}, {y1}, {z1}) is not inside this region')
            if not self.inside(x2, y2, z2):
                raise OutOfBoundsCoordinates(f'Second coords ({x}, {y}, {z}) is not inside this region')

        for y in from_inclusive(y1, y2):
            for z in from_inclusive(z1, z2):
                for x in from_inclusive(x1, x2):
                    if ignore_outside:
                        self.set_if_inside(block, x, y, z)
                    else:
                        self.set_block(block, x, y, z)

    def save(self, file: Union[str, BinaryIO]=None) -> bytes:
        """
        Returns the region as bytes with
        the anvil file format structure,
        aka the final ``.mca`` file.

        Parameters
        ----------
        file
            Either a path or a file object, if given region
            will be saved there.
        """
        # Store all the chunks data as zlib compressed nbt data
        chunks_data = []
        for chunk in self.chunks:
            if chunk is None:
                chunks_data.append(None)
                continue
            chunk_data = BytesIO()
            if isinstance(chunk, Chunk):
                nbt_data = nbt.NBTFile()
                nbt_data.tags.append(nbt.TAG_Int(name='DataVersion', value=chunk.version))
                nbt_data.tags.append(chunk.data)
            else:
                nbt_data = chunk.save()
            nbt_data.write_file(buffer=chunk_data)
            chunk_data.seek(0)
            chunk_data = zlib.compress(chunk_data.read())
            chunks_data.append(chunk_data)

        # This is what is added after the location and timestamp header
        chunks_bytes = bytes()
        offsets = []
        for chunk in chunks_data:
            if chunk is None:
                offsets.append(None)
                continue
            # 4 bytes are for length, b'\x02' is the compression type which is 2 since its using zlib
            to_add = (len(chunk)+1).to_bytes(4, 'big') + b'\x02' + chunk

            # offset in 4KiB sectors
            sector_offset = len(chunks_bytes) // 4096
            sector_count = math.ceil(len(to_add) / 4096)
            offsets.append((sector_offset, sector_count))

            # Padding to be a multiple of 4KiB long
            to_add += bytes(4096 - (len(to_add) % 4096))
            chunks_bytes += to_add

        locations_header = bytes()
        for offset in offsets:
            # None means the chunk is not an actual chunk in the region
            # and will be 4 null bytes, which represents non-generated chunks to minecraft
            if offset is None:
                locations_header += bytes(4)
            else:
                # offset is (sector offset, sector count)
                locations_header += (offset[0] + 2).to_bytes(3, 'big') + offset[1].to_bytes(1, 'big')

        # Set them all as 0
        timestamps_header = bytes(4096)

        final = locations_header + timestamps_header + chunks_bytes

        # Pad file to be a multiple of 4KiB in size
        # as Minecraft only accepts region files that are like that
        final += bytes(4096 - (len(final) % 4096))
        assert len(final) % 4096 == 0 # just in case

        # Save to a file if it was given
        if file:
            if isinstance(file, str):
                with open(file, 'wb') as f:
                    f.write(final)
            else:
                file.write(final)
        return final
