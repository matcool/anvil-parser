import context as _
from anvil import EmptyRegion, Block, RawSection
import math
import time
import logging
import array

LOGGER = logging.getLogger(__name__)

def test_benchmark():
    region = EmptyRegion(0, 0)

    block = Block('iron_block')

    def func(x: int, z: int) -> int:
        return math.sin(x * x + z * z) * 0.5 + 0.5

    w = 256
    scale = 0.05
    y_scale = 15

    start = time.time()
    for x in range(w):
        for z in range(w):
            u = x - w / 2
            v = z - w / 2
            y = int(func(u * scale, v * scale) * y_scale)
            region.set_block(block, x, y, z)
    end = time.time()

    LOGGER.info(f'Generating took: {end - start:.3f}s')

    times = []
    n = 3
    for _ in range(n):
        start = time.time()
        region.save()
        end = time.time()
        times.append(end - start)

    LOGGER.info(f'Saving (average of {n}) took: {sum(times) / len(times):.3f}s')

def test_raw_section():
    region = EmptyRegion(0, 0)

    block = Block('iron_block')
    air = Block('air')
    palette = (air, block)

    def func(x: int, z: int) -> int:
        return math.sin(x * x + z * z) * 0.5 + 0.5

    w = 256
    chunk_w = w // 16
    scale = 0.05
    y_scale = 15

    start = time.time()

    # from 0 to y_scale
    heights = array.array('B')
    for z in range(w):
        for x in range(w):
            u = z - w / 2
            v = x - w / 2
            height = int(func(u * scale, v * scale) * y_scale)
            heights.append(height)
            
    for chunk_x in range(chunk_w):
        for chunk_z in range(chunk_w):
            blocks = array.array('B')
            for y in range(16):
                for z in range(16):
                    for x in range(16):
                        rx = x + chunk_x * 16
                        rz = z + chunk_z * 16
                        i = rz * w + rx
                        height = heights[i]
                        if y == height:
                            blocks.append(1)
                        else:
                            blocks.append(0)
            region.add_section(RawSection(0, blocks, palette), chunk_x, chunk_z)

    end = time.time()

    LOGGER.info(f'Generating took: {end - start:.3f}s')

    times = []
    n = 3
    for _ in range(n):
        start = time.time()
        region.save()
        end = time.time()
        times.append(end - start)

    LOGGER.info(f'Saving (average of {n}) took: {sum(times) / len(times):.3f}s')

def test_raw_section_simple():
    region = EmptyRegion(0, 0)

    air = Block('air')
    palette = (air, Block('white_concrete'), Block('light_gray_concrete'), Block('gray_concrete'))

    blocks = array.array('B')
    for z in range(16):
        for x in range(16):
            d = x * x + z * z
            if d < 25:
                blocks.append(1)
            elif d < 100:
                blocks.append(2)
            elif d < 225:
                blocks.append(3)
            else:
                blocks.append(0)

    blocks.extend(0 for _ in range(16 * 16 * 16 - len(blocks)))

    assert len(blocks) == 16 * 16 * 16
    
    section = RawSection(0, blocks, palette)
    region.add_section(section, 0, 0)

    region.save()
