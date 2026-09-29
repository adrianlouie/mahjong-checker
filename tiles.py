"""Day 1: how we represent mahjong tiles.

A tile is just a string:
    "3-bamboo", "9-circles", "1-characters"   (numbered suits, ranks 1-9)
    "east-wind", "north-wind"                  (winds)
    "red-dragon", "green-dragon", "white-dragon"  (dragons)

Hong Kong mahjong uses 136 tiles (ignoring the 8 flower tiles, because
flowers are bonus tiles that are never part of the 14-tile hand):
    3 suits x 9 ranks x 4 copies = 108
    4 winds x 4 copies           =  16
    3 dragons x 4 copies         =  12
"""

import random

SUITS = ["bamboo", "circles", "characters"]
WINDS = ["east-wind", "south-wind", "west-wind", "north-wind"]
DRAGONS = ["red-dragon", "green-dragon", "white-dragon"]
COPIES = 4  # there are 4 copies of every tile


def all_tile_types():
    """The 34 different kinds of tile, in a fixed order.

    The order matters: the winning-hand checker always looks at the
    "smallest" tile first, and this list defines what "smallest" means.
    """
    types = []
    for suit in SUITS:
        for rank in range(1, 10):
            types.append(f"{rank}-{suit}")
    types.extend(WINDS)
    types.extend(DRAGONS)
    return types


TILE_ORDER = {tile: position for position, tile in enumerate(all_tile_types())}


def build_full_set():
    """All 136 physical tiles (4 copies of each of the 34 types)."""
    return [tile for tile in all_tile_types() for _ in range(COPIES)]


def parse_tile(tile):
    """Split a tile into (suit, rank).

    "3-bamboo"   -> ("bamboo", 3)
    "east-wind"  -> ("east-wind", None)   honors have no rank
    """
    if tile not in TILE_ORDER:
        raise ValueError(f"unknown tile: {tile!r}")
    first, _, rest = tile.partition("-")
    if first.isdigit():
        return rest, int(first)
    return tile, None


def is_numbered(tile):
    """True for bamboo/circles/characters tiles (the only ones that can form runs)."""
    return parse_tile(tile)[1] is not None


def sort_key(tile):
    """Use with sorted(hand, key=sort_key) to show a hand in a readable order."""
    return TILE_ORDER[tile]


def sorted_hand(hand):
    return sorted(hand, key=sort_key)


def random_hand(size=14, rng=random):
    """Deal `size` tiles from a freshly shuffled full set.

    random.sample picks WITHOUT replacement, so a hand can never contain
    more than 4 copies of any tile - exactly like a real wall.
    """
    return rng.sample(build_full_set(), size)


# Unicode mahjong tile characters, used by the web page to draw tiles.
_UNICODE_START = {"characters": 0x1F007, "bamboo": 0x1F010, "circles": 0x1F019}
_UNICODE_HONORS = {
    "east-wind": 0x1F000, "south-wind": 0x1F001,
    "west-wind": 0x1F002, "north-wind": 0x1F003,
    "red-dragon": 0x1F004, "green-dragon": 0x1F005, "white-dragon": 0x1F006,
}


def tile_symbol(tile):
    """The unicode character for a tile, e.g. tile_symbol("east-wind")."""
    suit, rank = parse_tile(tile)
    if rank is None:
        return chr(_UNICODE_HONORS[tile])
    return chr(_UNICODE_START[suit] + rank - 1)
