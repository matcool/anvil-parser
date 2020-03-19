from typing import List, Tuple, Sequence, Iterable
from . import EmptySection, Block
from .errors import OutOfBoundsCoordinates
import array
from nbt import nbt

def bin_append(a, b, length=None):
    length = length or b.bit_length()
    return (a << length) | b

class RawSection:
    """
    Same as :class:`EmptySection` but you manually
    set the palette and the blocks array (which instead
    of :class:`Block`, it's indexes on the palette)
    
    Attributes
    ----------
    y: :class:`int`
        Section's Y index
    blocks: Iterable[:class:`int`]
        Array of palette indexes
    _palette: Sequence[:class:`Block`]
        Section's palette
    """
    __slots__ = ('y', '_palette', 'blocks')
    def __init__(self, y: int, blocks: Iterable[int], palette: Sequence[Block]):
        self.y = y
        self.blocks: Iterable[int] = blocks
        self._palette: Sequence[Block] = palette

    def palette(self) -> Sequence[Block]:
        """Returns ``self._palette``"""
        return self._palette

    def blockstates(self, palette: Sequence[Block]=None) -> array.array:
        """Refer to :class:`EmptySection.blockstates()`"""
        bits = max((len(self._palette) - 1).bit_length(), 4)
        states = array.array('Q')
        current = 0
        current_len = 0
        for index in self.blocks:
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
        """Refer to :class:`EmptySection.save()`"""
        return EmptySection.save(self)
