from nbt import nbt
from frozendict import frozendict

class Block:
    """
    Represents a minecraft block.

    Attributes
    ----------
    namespace: :class:`str`
        Namespace of the block, most of the time this is ``minecraft``
    id: :class:`str`
        ID of the block, for example: stone, diamond_block, etc...
    properties: :class:`dict`
        Block properties as a dict
    """
    __slots__ = ('namespace', 'id', 'properties')

    def __init__(self, namespace: str, block_id: str=None, properties: dict=None):
        """
        Parameters
        ----------
        namespace
            Namespace of the block. If no block_id is given, assume this is ``block_id`` and set namespace to ``"minecraft"``
        block_id
            ID of the block
        properties
            Block properties
        """
        if block_id is None:
            self.namespace = 'minecraft'
            self.id = namespace
        else:
            self.namespace = namespace
            self.id = block_id
        self.properties = properties or {}

    def name(self) -> str:
        """
        Returns the block in the ``minecraft:block_id`` format
        """
        return self.namespace + ':' + self.id

    def __repr__(self):
        return f'<Block({self.name()})>'

    def __eq__(self, other):
        if not isinstance(other, Block):
            return False
        return self.namespace == other.namespace and self.id == other.id and self.properties == other.properties

    def __hash__(self):
        return hash(self.name()) ^ hash(frozendict(self.properties))

    @classmethod
    def from_name(cls, name: str, *args, **kwargs):
        """
        Creates a new Block from the format: ``namespace:block_id``

        Parameters
        ----------
        name
            Block in said format
        , args, kwargs
            Will be passed on to the main constructor
        """
        namespace, block_id = name.split(':')
        return cls(namespace, block_id, *args, **kwargs)

    @classmethod
    def from_palette(cls, tag: nbt.TAG_Compound):
        """
        Creates a new Block from the tag format on Section.Palette

        Parameters
        ----------
        tag
            Raw tag from a section's palette
        """
        name = tag['Name'].value
        properties = tag.get('Properties')
        if properties:
            properties = dict(properties)
        return cls.from_name(name, properties=properties)
