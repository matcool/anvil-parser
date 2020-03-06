from __future__ import annotations
from typing import Tuple, Union, BinaryIO
from nbt import nbt
import zlib
from io import BytesIO
import anvil

class Region:
    def __init__(self, data: bytes):
        """Makes a Region object from data, which is the region file content"""
        self.data = data

    @staticmethod
    def header_offset(chunkX: int, chunkZ: int) -> int:
        """Returns the byte offset for given chunk in the header"""
        return 4 * (chunkX % 32 + chunkZ % 32 * 32)

    def chunk_location(self, chunkX: int, chunkZ: int) -> Tuple[int, int]:
        """
        Returns the chunk offset in the 4KiB sectors from the start of the file,
        and the length of the chunk in sectors of 4KiB

        Returns (0, 0) if chunk hasnt been generated yet
        """
        b_off = self.header_offset(chunkX, chunkZ)
        off = int.from_bytes(self.data[b_off : b_off + 3], byteorder='big')
        sectors = self.data[b_off + 3]
        return (off, sectors)

    def chunk_data(self, chunkX: int, chunkZ: int) -> nbt.NBTFile:
        """Returns the NBT chunk data"""
        off = self.chunk_location(chunkX, chunkZ)
        # (0, 0) means it hasn't generated yet, aka it doesn't exist yet
        if off == (0, 0):
            return
        off = off[0] * 4096
        length = int.from_bytes(self.data[off:off + 4], byteorder='big')
        compression = self.data[off + 4] # 2 most of the time
        if compression == 1:
            raise Exception('GZip is not supported')
        compressed_data = self.data[off + 5 : off + 5 + length - 1]
        return nbt.NBTFile(buffer=BytesIO(zlib.decompress(compressed_data)))

    def get_chunk(self, chunkX: int, chunkZ: int) -> 'Chunk':
        """
        Returns the chunk at given coordinates,
        same as doing Chunk.from_region(`this`, chunkX, chunkZ)
        """
        return anvil.Chunk.from_region(self, chunkX, chunkZ)

    @classmethod
    def from_file(cls, file: Union[str, BinaryIO]):
        """Creates a new region with the data from reading the given file"""
        if type(file == str):
            with open(file, 'rb') as f:
                return cls(data=f.read())
        else:
            return cls(data=file.read())
