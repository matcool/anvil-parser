import context as _
from anvil import EmptyRegion, Region, Block

def coord_to_index(x, y, z):
    return y * 16 * 16 + z * 16 + x

def test_4bits():
    region = EmptyRegion(0, 0)

    region.set_block(Block('minecraft', 'stone'), 0, 0, 0)
    region.set_block(Block('minecraft', 'dirt'), 1, 0, 0)
    region.set_block(Block('minecraft', 'oak_planks'), 2, 0, 0)
    region.set_block(Block('minecraft', 'sand'), 10, 7, 5)
    region.set_block(Block('minecraft', 'white_wool'), 8, 6, 0)
    region.set_block(Block('minecraft', 'bedrock'), 15, 15, 15)

    region = Region(region.save())

    for i, block in enumerate(region.get_chunk(0, 0).stream_blocks()):
        if i == 0:
            assert block.id == 'stone'
        elif i == 1:
            assert block.id == 'dirt'
        elif i == 2:
            assert block.id == 'oak_planks'
        elif i == coord_to_index(10, 7, 5):
            assert block.id == 'sand'
        elif i == coord_to_index(15, 15, 15):
            assert block.id == 'bedrock'
        elif i == coord_to_index(8, 6, 0):
            assert block.id == 'white_wool'
        else:
            assert block.id == 'air'

def test_5bits():
    from random import randint
    region = EmptyRegion(0, 0)

    blocks = 'stone,dirt,oak_planks,sand,bedrock,white_wool,red_wool,green_wool,sponge,awesome,these,dont,need,to,exist,foo,bar'.split(',')
    positions = [(randint(0, 15), randint(0, 15), randint(0, 15)) for _ in range(len(blocks))]
    for block, pos in zip(blocks, positions):
        region.set_block(Block('minecraft', block), *pos)

    region = Region(region.save())

    for i, block in enumerate(region.get_chunk(0, 0).stream_blocks()):
        if block.id in blocks:
            assert coord_to_index(*positions[blocks.index(block.id)]) == i
        else:
            assert block.id == 'air'

def test_index():
    region = EmptyRegion(0, 0)

    region.set_block(Block('minecraft', 'dirt'), 2, 0, 0)
    region.set_block(Block('minecraft', 'stone'), 3, 0, 0)
    blocks = 'stone,dirt,oak_planks,sand,bedrock'.split(',')
    for i, block in enumerate(blocks):
        region.set_block(Block('minecraft', block), i % 16, 0, i // 16)

    region = Region(region.save())

    for i, block in enumerate(region.get_chunk(0, 0).stream_blocks(index=2)):
        i += 2
        if i < len(blocks):
            assert block.id == blocks[i]
        else:
            assert block.id == 'air'

def test_index_5bits():
    region = EmptyRegion(0, 0)

    region.set_block(Block('minecraft', 'dirt'), 2, 0, 0)
    region.set_block(Block('minecraft', 'stone'), 3, 0, 0)
    blocks = 'stone,dirt,oak_planks,sand,bedrock,white_wool,red_wool,green_wool,sponge,awesome,these,dont,need,to,exist,foo,bar'.split(',')
    for i, block in enumerate(blocks):
        region.set_block(Block('minecraft', block), i % 16, 0, i // 16)

    region = Region(region.save())
    
    for i, block in enumerate(region.get_chunk(0, 0).stream_blocks(index=17)):
        i += 17
        if i < len(blocks):
            assert block.id == blocks[i]
        else:
            assert block.id == 'air'
