from typing import Union, List, BinaryIO
from .empty_chunk import EmptyChunk
from .block import Block
from .errors import OutOfBoundsCoordinates
from io import BytesIO
from nbt import nbt
import zlib
import math

class EmptyRegion:
    """
    Class used for making own regions
    Cannot yet be interchanged with the regular `Region` class,
    as it is currently only used when reading mca files
    """
    def __init__(self, x: int, z: int):
        # Create a 1d list for the 32x32 chunks
        self.chunks: List[EmptyChunk] = [None] * 1024
        self.x = x
        self.z = z

    def inside(self, x: int, y: int, z: int, chunk: bool=False) -> bool:
        """Returns if the given coordinates (global or chunk) are inside this region"""
        factor = 32 if chunk else 512
        rx = x // factor
        rz = z // factor
        return not (rx != self.x or rz != self.z or y < 0 or y > 255)

    def get_chunk(self, x: int, z: int) -> EmptyChunk:
        """Returns the chunk at given chunk coordinates"""
        if not self.inside(x, 0, z, chunk=True):
            raise OutOfBoundsCoordinates('Given chunk coordinates do not belong in this region')
        return self.chunks[z % 32 * 32 + x % 32]

    def add_chunk(self, chunk: EmptyChunk):
        """
        Adds given chunk to this region
        Will overwrite if a chunk already exists in this location
        """
        if not self.inside(chunk.x, 0, chunk.z, chunk=True):
            raise ValueError('Chunk does not belong in this region')
        self.chunks[chunk.z % 32 * 32 + chunk.x % 32] = chunk

    def set_block(self, block: Block, x: int, y: int, z: int):
        """
        Sets block at given coordinates, them being global
        will make a new chunk if chunk at coords does not exist
        """
        if not self.inside(x, y, z):
            raise OutOfBoundsCoordinates('Given coordinates do not belong in this region')
        cx = x // 16
        cz = z // 16
        chunk = self.get_chunk(cx, cz)
        if chunk is None:
            chunk = EmptyChunk(cx, cz)
            self.add_chunk(chunk)
        chunk.set_block(block, x % 16, y, z % 16)

    def set_if_inside(self, block: Block, x: int, y: int, z: int):
        """Helper function that only sets the block if self.inside(x, y, z) is True"""
        if self.inside(x, y, z):
            self.set_block(block, x, y, z)

    def fill(self, block: Block, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, ignore_outside: bool=False):
        """Fills in blocks from (x1,y1,z1) to (x2,y2,z2)"""
        if not ignore_outside:
            if not self.inside(x1, y1, z1):
                raise OutOfBoundsCoordinates('First coordinates do not belong in this region')
            if not self.inside(x2, y2, z2):
                raise OutOfBoundsCoordinates('Second coordinates do not belong in this region')
        def from_inclusive(a, b):
            """Returns a range from a to b, including both endpoints"""
            c = int(b > a)*2-1
            return range(a, b+c, c)
        for y in from_inclusive(y1, y2):
            for z in from_inclusive(z1, z2):
                for x in from_inclusive(x1, x2):
                    if ignore_outside:
                        self.set_if_inside(block, x, y, z)
                    else:
                        self.set_block(block, x, y, z)

    def save(self, file: Union[str, BinaryIO]=None) -> bytes:
        """
        Returns the region as bytes with the anvil file format structure
        If a file path or object is given, will save there
        """
        # Store all the chunks data as zlib compressed nbt data
        chunks_data = []
        for chunk in self.chunks:
            if chunk is None:
                chunks_data.append(None)
                continue
            chunk_data = BytesIO()
            chunk.save().write_file(buffer=chunk_data)
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
