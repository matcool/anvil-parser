from typing import List, Tuple, Sequence, Iterable
from . import EmptySection, Block
from .errors import OutOfBoundsCoordinates
import array

def bin_append(a, b, length=None):
    length = length or b.bit_length()
    return (a << length) | b

class RawSection:
    """EmptySection but you manually set the palette and the blocks (index on the palette) array"""

    __slots__ = ('y', '_palette', 'blocks')
    def __init__(self, y: int, blocks: Iterable[int], palette: Sequence[Block]):
        self.y = y
        self.blocks: Iterable[int] = blocks
        self._palette: Sequence[Block] = palette

    def palette(self) -> Sequence[Block]:
        return self._palette

    def blockstates(self, palette: Sequence[Block]=None) -> array.array:
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

    def save(self):
        return EmptySection.save(self)
