from nbt import nbt

class Block:
    def __init__(self, namespace: str, id: str, properties: dict=None):
        self.namespace = namespace
        self.id = id
        self.properties = properties or {}

    def name(self):
        return self.namespace + ':' + self.id

    def __repr__(self):
        return f'<Block({self.name()})>'

    @classmethod
    def from_name(cls, name: str, *args, **kwargs):
        """Creates a new Block from the block's name (namespace:id)"""
        namespace, id = name.split(':')
        return cls(namespace, id, *args, **kwargs)

    @classmethod
    def from_palette(cls, tag: nbt.TAG_Compound):
        """Creates a new Block from the tag format on Section.Palette"""
        name = tag['Name'].value
        properties = tag.get('Properties')
        if properties: properties = dict(properties)
        return cls.from_name(name, properties=properties)