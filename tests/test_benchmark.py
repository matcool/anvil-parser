import context as _
from anvil import EmptyRegion, Block
import math
import time
import logging

LOGGER = logging.getLogger(__name__)

def test_benchmark():
    region = EmptyRegion(0, 0)

    block = Block('minecraft', 'iron_block')

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
