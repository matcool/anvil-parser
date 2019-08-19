from typing import List
from .block import Block
from .empty_section import EmptySection
from .errors import OutOfBoundsCoordinates
from nbt import nbt

class EmptyChunk:
    """
    Class used for making own chunks
    Cannot yet be interchanged with the regular `Chunk` class,
    as it is currently only used when reading mca files
    """
    def __init__(self, x: int, z: int):
        self.x = x
        self.z = z
        self.sections: List[EmptySection] = []
        self.version = 1976

    def get_section(self, y: int) -> EmptySection:
        """Returns the section at given y index, None if not found"""
        for s in self.sections:
            if s.y == y: return s

    def get_block(self, x: int, y: int, z: int) -> Block:
        """
        Gets the block at given coordinates, x and z being 0-15 and y 0-255
        None means the section is empty, and the block is most likely an air block
        """
        if x < 0 or x > 15 or z < 0 or z > 15:
            raise OutOfBoundsCoordinates('X and Z must be in the range of 0-15')
        if y < 0 or y > 255:
            raise OutOfBoundsCoordinates('Y must be in range 0-255')
        section = self.get_section(y // 16)
        if section is None: return
        return section.get_block(x, y % 16, z)

    def set_block(self, block: Block, x: int, y: int, z: int):
        """Sets block at given coordinates, x and z being 0-15 and y 0-255"""
        if x < 0 or x > 15 or z < 0 or z > 15:
            raise OutOfBoundsCoordinates('X and Z must be in the range of 0-15')
        if y < 0 or y > 255:
            raise OutOfBoundsCoordinates('Y must be in range 0-255')
        section = self.get_section(y // 16)
        if section is None:
            section = EmptySection(y // 16)
            self.sections.append(section)
        section.set_block(block, x, y % 16, z)

    def save(self) -> nbt.NBTFile:
        """
        Saves the chunk data to an NBTFile
        Does not contain most data a regular chunk would have,
        but minecraft stills accept it
        """
        root = nbt.NBTFile()
        root.tags.append(nbt.TAG_Int(name='DataVersion',value=self.version))
        level = nbt.TAG_Compound()
        # Needs to be in a separate line because it just gets
        # ignored if you pass it as a kwarg in the constructor
        level.name = 'Level'
        level.tags.extend([
            nbt.TAG_List(name='Entities', type=nbt.TAG_Compound),
            nbt.TAG_List(name='TileEntities', type=nbt.TAG_Compound),
            nbt.TAG_List(name='LiquidTicks', type=nbt.TAG_Compound),
            nbt.TAG_Int(name='xPos', value=self.x),
            nbt.TAG_Int(name='zPos', value=self.z),
            nbt.TAG_Long(name='LastUpdate', value=0),
            nbt.TAG_Long(name='InhabitedTime', value=0),
            nbt.TAG_Byte(name='isLightOn', value=1),
            nbt.TAG_String(name='Status', value='full')
        ])
        sections = nbt.TAG_List(name='Sections', type=nbt.TAG_Compound)
        for s in self.sections:
            p = s.palette()
            # Minecraft does not save sections that are just air
            # So we can just skip them
            if len(p) == 1 and p[0].name() == 'minecraft:air': continue
            sections.tags.append(s.save())
        level.tags.append(sections)
        root.tags.append(level)
        return root