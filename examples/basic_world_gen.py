"""
Basic terrain generation made to test out EmptyRegion and related
Needs the `opensimplex` package to work

Generated terrain is 128x128 blocks and in the North-West corner
"""
import _path
import anvil
from opensimplex import OpenSimplex
import random
import math

noise = OpenSimplex()

region = anvil.EmptyRegion(0, 0)
grass = anvil.Block('minecraft', 'grass_block')
dirt = anvil.Block('minecraft', 'dirt')
glass = anvil.Block('minecraft', 'glass')
oak_log_up = anvil.Block('minecraft', 'oak_log', properties={'axis': 'y'})
oak_leaves = anvil.Block('minecraft', 'oak_leaves', properties={'persistent': True})

grass_plant = anvil.Block('minecraft', 'grass')
poppy = anvil.Block('minecraft', 'poppy')
dandelion = anvil.Block('minecraft', 'dandelion')
tall_grass_l = anvil.Block('minecraft', 'tall_grass', properties={'half': 'lower'})
tall_grass_u = anvil.Block('minecraft', 'tall_grass', properties={'half': 'upper'})

scale = 0.01
plant_scale = 1
xoff = region.x * 512
zoff = region.z * 512
random.seed(0)
for z in range(128):
    for x in range(128):
        x += xoff
        z += zoff
        v = noise.noise2d(x*scale, z*scale)
        v = (v + 1) / 2 # now its from 0 to 1
        v = math.floor(v * 100)
        region.set_block(grass, x, v, z)
        if v > 0:
            region.set_block(dirt, x, v-1, z)
        n = noise.noise2d(x*plant_scale+100, z*plant_scale)
        if n > 0.4:
            # flower
            if random.random() > 0.95:
                region.set_block(random.choice((poppy, dandelion)), x, v+1, z)
            else:
                if random.random() > 0.9:
                    region.set_block(tall_grass_l, x, v+1, z)
                    region.set_block(tall_grass_u, x, v+2, z)
                else:
                    region.set_block(grass_plant, x, v+1, z)
        # Tree
        if random.random() > 0.99:
            region.fill(oak_leaves, x-2, v+4, z-2, x+2, v+5, z+2, ignore_outside=True)
            for y in range(6):
                region.set_if_inside(oak_log_up, x, v+y+1, z)
            region.set_if_inside(oak_leaves, x, v+7, z)
            for y in range(2):
                region.set_if_inside(oak_leaves, x+1, v+6+y, z)
                region.set_if_inside(oak_leaves, x  , v+6+y, z+1)
                region.set_if_inside(oak_leaves, x-1, v+6+y, z)
                region.set_if_inside(oak_leaves, x  , v+6+y, z-1)

save = region.save('r.0.0.mca')
