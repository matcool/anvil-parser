from typing import List, Tuple
from . import Block
from .errors import OutOfBoundsCoordinates
from nbt import nbt
from struct import Struct

# dirty mixin to change q to Q
def _update_fmt(self, length):
    self.fmt = Struct(f'>{str(length)}Q')
nbt.TAG_Long_Array.update_fmt = _update_fmt

class EmptySection:
    """
    Class used for making own sections
    This is where the blocks are actually stored, in a 16*16*16 sized array
    To save up some space, None is used instead of the air block object
    and will be replaced with `self.air` when needed
    """
    def __init__(self, y: int):
        self.y = y
        # None is the same as an air block
        self.blocks: List[Block] = [None] * 4096
        # Block that will be used when None
        self.air = Block('minecraft', 'air')

    @staticmethod
    def inside(x: int, y: int, z: int) -> bool:
        """Basic method to check if X Y and Z are in range of 0-15"""
        return x >= 0 and x <= 15 and y >= 0 and y <= 15 and z >= 0 and z <= 15

    def set_block(self, block: Block, x: int, y: int, z: int):
        """Sets the block at given coordinates"""
        if not self.inside(x, y, z):
            raise OutOfBoundsCoordinates('X Y and Z must be in range of 0-15')
        index = y * 256 + z * 16 + x
        self.blocks[index] = block

    def get_block(self, x: int, y: int, z: int) -> Block:
        """
        Gets the block at given coordinates
        Will return the air block if its None internally
        """
        if not self.inside(x, y, z):
            raise OutOfBoundsCoordinates('X Y and Z must be in range of 0-15')
        index = y * 256 + z * 16 + x
        return self.blocks[index] or self.air

    def palette(self) -> Tuple[Block]:
        """
        Generates and returns a tuple of all the different blocks in the section
        The order can change a lot as it uses sets, but should be fine as when saving
        it calls this once
        """
        palette = set(self.blocks)
        if None in palette:
            palette.remove(None)
            palette.add(self.air)
        return tuple(palette)

    def blockstates(self, palette: Tuple[Block]=None) -> List[int]:
        """
        Returns a list of numbers, which are the blocks data
        This is used in the BlockStates tag of the section 
        The list should always be the length of bits * 4096 / 64,
        with bits being the bit length of the number of blocks in the palette,
        and that being atleast 4
        """
        palette = palette or self.palette()
        bits = max((len(palette) - 1).bit_length(), 4)
        states = []
        current = ''
        def to_bin(n: int, length: int=None):
            if length is None: length = n.bit_length()
            return '0'*(length-max(n.bit_length(), 1)) + bin(n)[2:]
        for block in self.blocks:
            if block is None:
                index = palette.index(self.air)
            else:
                index = palette.index(block)
            b = to_bin(index, length=bits)
            # If it more than 64 bits then add to list and start over
            # with the remaining bits from last one
            if len(current) + bits > 64:
                leftover = len(current) + len(b) - 64
                states.append(int(b[bits-leftover:] + current, base=2))
                current = b[:leftover]
            else:
                current = b + current
        states.append(int(current, base=2))
        return states

    def save(self) -> nbt.TAG_Compound:
        """
        Saves the section to an TAG_Compound and is used inside the chunk tag
        This is missing the SkyLight tag, but minecraft still accepts it anyway,
        and generates the values
        """
        root = nbt.TAG_Compound()
        root.tags.append(nbt.TAG_Byte(name='Y', value=self.y))

        palette = self.palette()
        nbt_pal = nbt.TAG_List(name='Palette', type=nbt.TAG_Compound)
        for block in palette:
            tag = nbt.TAG_Compound()
            tag.tags.append(nbt.TAG_String(name='Name', value=block.name()))
            if block.properties:
                properties = nbt.TAG_Compound()
                properties.name = 'Properties'
                for key, value in block.properties.items():
                    if type(value) == str:
                        properties.tags.append(nbt.TAG_String(name=key, value=value))
                    elif type(value) == bool:
                        # booleans are a string saved as either 'true' or 'false'
                        properties.tags.append(nbt.TAG_String(name=key, value=str(value).lower()))
                    elif type(value) == int:
                        # ints also seem to be saved as a string
                        properties.tags.append(nbt.TAG_String(name=key, value=str(value)))
                    else:
                        # assume its a nbt tag and just append it
                        properties.tags.append(value)
                tag.tags.append(properties)
            nbt_pal.tags.append(tag)
        root.tags.append(nbt_pal)

        states = self.blockstates(palette=palette)
        bstates = nbt.TAG_Long_Array(name='BlockStates')
        bstates.value = states
        root.tags.append(bstates)

        return root