import context as _
from anvil import Chunk, EmptyChunk, EmptyRegion, Block, Region
import random

def test_mixed_chunk_types():
    colors = ['red', 'orange', 'yellow', 'green']

    region = EmptyRegion(0, 0)

    chunk = EmptyChunk(0, 0)
    empty_chunk = EmptyChunk(1, 0)
    for i, color in enumerate(colors):
        chunk.set_block(Block(color), i, 0, 0)
        empty_chunk.set_block(Block(color), i, 0, 0)

    chunk = Chunk(chunk.save())

    region.add_chunk(chunk)
    region.add_chunk(empty_chunk)

    region = Region(region.save())

    for i in range(2):
        chunk = region.get_chunk(i, 0)
        for i, color in enumerate(colors):
            assert chunk.get_block(i, 0, 0).id == color
