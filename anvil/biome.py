from .legacy import LEGACY_BIOMES_ID_MAP

class Biome:
    """
    Represents a minecraft biome.

    Attributes
    ----------
    namespace: :class:`str`
        Namespace of the biome, most of the time this is ``minecraft``
    id: :class:`str`
        ID of the biome, for example: forest, warm_ocean, etc...
    """
    __slots__ = ('namespace', 'id')

    def __init__(self, namespace: str, biome_id: str=None):
        """
        Parameters
        ----------
        namespace
            Namespace of the biome. If no biome_id is given, assume this is ``biome_id`` and set namespace to ``"minecraft"``
        biome_id
            ID of the biome
        """
        if biome_id is None:
            self.namespace = 'minecraft'
            self.id = namespace
        else:
            self.namespace = namespace
            self.id = biome_id

    def name(self) -> str:
        """
        Returns the biome in the ``minecraft:biome_id`` format
        """
        return self.namespace + ':' + self.id

    def __repr__(self):
        return f'Biome({self.name()})'

    def __eq__(self, other):
        if not isinstance(other, Biome):
            return False
        return self.namespace == other.namespace and self.id == other.id

    def __hash__(self):
        return hash(self.name())

    @classmethod
    def from_name(cls, name: str):
        """
        Creates a new Biome from the format: ``namespace:biome_id``

        Parameters
        ----------
        name
            Biome in said format
        """
        namespace, biome_id = name.split(':')
        return cls(namespace, biome_id)

    @classmethod
    def from_numeric_id(cls, biome_id: int):
        """
        Creates a new Biome from the numeric biome_id format

        Parameters
        ----------
        biome_id
            Numeric ID of the biome
        """
        if biome_id not in LEGACY_BIOMES_ID_MAP:
            raise KeyError(f'Biome {biome_id} not found')
        name = LEGACY_BIOMES_ID_MAP[biome_id]
        return cls('minecraft', name)