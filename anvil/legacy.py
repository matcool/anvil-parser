import json
import os

with open(os.path.join(__file__, '..', 'legacy_blocks.json'), 'r') as file:
    LEGACY_ID_MAP = json.load(file)
