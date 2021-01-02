from typing import List, Tuple
from . import Block
from .errors import OutOfBoundsCoordinates
from nbt import nbt
from struct import Struct
import array

# dirty mixin to change q to Q
def _update_fmt(self, length):
    self.fmt = Struct(f'>{length}Q')
nbt.TAG_Long_Array.update_fmt = _update_fmt

def bin_append(a, b, length=None):
    length = length or b.bit_length()
    return (a << length) | b

class EmptySection:
    """
    Used for making own sections.

    This is where the blocks are actually stored, in a 16³ sized array.
    To save up some space, ``None`` is used instead of the air block object,
    and will be replaced with ``self.air`` when needed

    Attributes
    ----------
    y: :class:`int`
        Section's Y index
    blocks: List[:class:`Block`]
        1D list of blocks
    air: :class:`Block`
        An air block
    """
    __slots__ = ('y', 'blocks', 'air')
    def __init__(self, y: int):
        self.y = y
        # None is the same as an air block
        self.blocks: List[Block] = [None] * 4096
        # Block that will be used when None
        self.air = Block('minecraft', 'air')

    @staticmethod
    def inside(x: int, y: int, z: int) -> bool:
        """
        Check if X Y and Z are in range of 0-15
        
        Parameters
        ----------
        int x, y, z
            Coordinates
        """
        return x >= 0 and x <= 15 and y >= 0 and y <= 15 and z >= 0 and z <= 15

    def set_block(self, block: Block, x: int, y: int, z: int):
        """
        Sets the block at given coordinates
        
        Parameters
        ----------
        block
            Block to set
        int x, y, z
            Coordinates

        Raises
        ------
        anvil.OutOfBoundsCoordinates
            If coordinates are not in range of 0-15
        """
        if not self.inside(x, y, z):
            raise OutOfBoundsCoordinates('X Y and Z must be in range of 0-15')
        index = y * 256 + z * 16 + x
        self.blocks[index] = block

    def get_block(self, x: int, y: int, z: int) -> Block:
        """
        Gets the block at given coordinates.
        
        Parameters
        ----------
        int x, y, z
            Coordinates

        Raises
        ------
        anvil.OutOfBoundsCoordinates
            If coordinates are not in range of 0-15
        """
        if not self.inside(x, y, z):
            raise OutOfBoundsCoordinates('X Y and Z must be in range of 0-15')
        index = y * 256 + z * 16 + x
        return self.blocks[index] or self.air

    def palette(self) -> Tuple[Block]:
        """
        Generates and returns a tuple of all the different blocks in the section
        The order can change as it uses sets, but should be fine when saving since
        it's only called once.
        """
        palette = set(self.blocks)
        if None in palette:
            palette.remove(None)
            palette.add(self.air)
        return tuple(palette)

    def blockstates(self, palette: Tuple[Block]=None) -> array.array:
        """
        Returns a list of each block's index in the palette.
        
        This is used in the BlockStates tag of the section.

        Parameters
        ----------
        palette
            Section's palette. If not given will generate one.
        """
        palette = palette or self.palette()
        bits = max((len(palette) - 1).bit_length(), 4)
        states = array.array('Q')
        current = 0
        current_len = 0
        for block in self.blocks:
            if block is None:
                index = palette.index(self.air)
            else:
                index = palette.index(block)
            # If it's more than 64 bits then add to list and start over
            # with the remaining bits from last one
            if current_len + bits > 64:
                leftover = 64 - current_len
                states.append(bin_append(index & ((1 << leftover) - 1), current, length=current_len))
                current = index >> leftover
                current_len = bits - leftover
            else:
                current = bin_append(index, current, length=current_len)
                current_len += bits
        states.append(current)
        return states

    def save(self) -> nbt.TAG_Compound:
        """
        Saves the section to a TAG_Compound and is used inside the chunk tag
        This is missing the SkyLight tag, but minecraft still accepts it anyway
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
                    if isinstance(value, str):
                        properties.tags.append(nbt.TAG_String(name=key, value=value))
                    elif isinstance(value, bool):
                        # booleans are a string saved as either 'true' or 'false'
                        properties.tags.append(nbt.TAG_String(name=key, value=str(value).lower()))
                    elif isinstance(value, int):
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
