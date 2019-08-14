# anvil-parser
Simple parser for the [Minecraft anvil file format](https://minecraft.gamepedia.com/Anvil_file_format)
# Usage
```python
import anvil

region = anvil.Region.from_file('r.0.0.mca')

# You can also provide the region file name instead of the object
chunk = anvil.Chunk.from_region(region, 0, 0)

# If `section` is not provided, will get it from the y coords
# and assume it's global
block = chunk.get_block(0, 0, 0)

print(block) # <Block(minecraft:air)>
print(block.id) # air
print(block.properties) # {}
```
# Note
Still contains some bugs, testing done with saves from 1.14.4, and in DataVersion 1976