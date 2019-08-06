"""
Generates a image of the top view of a chunk
Needs a textures folder with a block folder inside
"""
import sys
if len(sys.argv) == 1:
    print('You must give a region file')
    sys.exit()
else:
    region = sys.argv[1]
    chx = int(sys.argv[2])
    chz = int(sys.argv[3])
import os
from PIL import Image
sys.path.append('..')
from main import *
sys.path.pop(0)

chunk = Chunk.from_region(region, chx, chz)
img = Image.new('RGBA', (16*16,16*16))
grid = [[None for i in range(16)] for j in range(16)]
for y in reversed(range(256)):
    for z in range(16):
        for x in range(16):
            b = chunk.get_block(x, y, z).id
            if b == 'air' or grid[z][x] != None: continue
            grid[z][x] = b

texturesf = os.listdir('textures/block')
textures = {}
for z in range(16):
    for x in range(16):
        b = grid[z][x]
        if b == None: continue
        if b not in textures:
            if b+'.png' not in texturesf:
                print(f'Skipping {b}')
                textures[b] = None
                continue
            textures[b] = Image.open(f'textures/block/{b}.png')
        if textures[b] == None: continue
        img.paste(textures[b], box=(x*16, z*16))

img.show()