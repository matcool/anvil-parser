# This version removes the chunk's "Level" NBT tag and moves all contained tags to the top level
# https://minecraft.wiki/w/Java_Edition_21w43a
VERSION_21w43a = 2844

# This version removes block state value stretching from the storage
# so a block value isn't in multiple elements of the array
VERSION_20w17a = 2529

# This version changes how biomes are stored to allow for biomes at different heights
# https://minecraft.wiki/w/Java_Edition_19w36a
VERSION_19w36a = 2203

# This is the version where "The Flattening" (https://minecraft.wiki/w/Java_Edition_1.13/Flattening) happened
# where blocks went from numeric ids to namespaced ids (namespace:block_id)
VERSION_17w47a = 1451

# This represents Versions before 1.9 snapshot 15w32a, 
# these snapshots do not have a Data Version so we use -1 since -1 is less than any valid data version.
# https://minecraft.wiki/w/Data_version
VERSION_PRE_15w32a = -1
