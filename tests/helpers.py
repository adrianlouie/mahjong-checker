"""Helpers shared by several test files."""

import random
from collections import Counter
from functools import lru_cache

from tiles import SUITS, TILE_ORDER, all_tile_types

TILE_TYPES = all_tile_types()
NUMBERED_COUNT = 27


def hand(text):
    """Turn "1b 2b 3b R" style shorthand into tile names (tests only).

    b = bamboo, c = circles, k = characters (e.g. "5k" is 5-characters);
    E S W N = winds, R G P = red / green / white dragon.
    """
    suits = {"b": "bamboo", "c": "circles", "k": "characters"}
    honors = {"E": "east-wind", "S": "south-wind", "W": "west-wind",
              "N": "north-wind", "R": "red-dragon", "G": "green-dragon",
              "P": "white-dragon"}
    out = []
    for word in text.split():
        if word in honors:
            out.append(honors[word])
        else:
            out.append(f"{word[0]}-{suits[word[1]]}")
    return out


def build_random_winning_hand(rng):
    """A hand that is winning BY CONSTRUCTION: 4 random sets + a pair.

    Returns None if the random choices would need a 5th copy of a tile.
    """
    tiles = []
    for _ in range(4):
        if rng.random() < 0.5:
            suit, start = rng.choice(SUITS), rng.randint(1, 7)
            tiles += [f"{start + i}-{suit}" for i in range(3)]       # a run
        else:
            tiles += [rng.choice(all_tile_types())] * 3              # a triplet
    tiles += [rng.choice(all_tile_types())] * 2                      # the pair
    if max(Counter(tiles).values()) > 4:
        return None
    rng.shuffle(tiles)
    return tiles


def near_winning_hands(rng, count, size, max_swaps=4):
    """Winning hands with a few tiles swapped for random ones, then trimmed to `size`.

    Gives a spread of hands that are close to (but often not) winning - much
    more useful for testing than purely random hands, which are never close.
    """
    out = []
    while len(out) < count:
        tiles = build_random_winning_hand(rng)
        if tiles is None:
            continue
        for _ in range(rng.randint(0, max_swaps)):
            tiles[rng.randrange(len(tiles))] = rng.choice(all_tile_types())
        if max(Counter(tiles).values()) > 4:
            continue
        rng.shuffle(tiles)
        out.append(tiles[:size])
    return out


def slow_shanten(tiles, melds=0):
    """The ORIGINAL, slower distance calculation, kept as a reference.

    tests check that the fast version in probability.py always agrees with it.

    We try to split the tiles into building blocks:
        set     = triplet or run           (worth 2 points)
        partial = pair or 2-of-a-run       (worth 1 point: one tile from a set)
        head    = the single pair we need  (worth 1 point)
    and the shanten number is 8 - 2*sets - partials - head, using the best
    split. Only 4 sets+partials can count in total (that's all a hand has room
    for), so partials are capped at 4 - sets.

    Same backtracking spirit as checker.py: at each tile, try each way of using
    it, recurse, and keep the best result.
    """
    counts = [0] * len(TILE_TYPES)
    for tile in tiles:
        counts[TILE_ORDER[tile]] += 1

    def count_at(i):
        return counts[i] if i < len(counts) else 0

    @lru_cache(maxsize=None)
    def best(i, c0, c1, c2, sets, partials, head):
        # i = tile position; c0, c1, c2 = tiles still unused at i, i+1, i+2.
        if sets > 4:
            return 99
        if i >= len(counts):
            return 8 - 2 * sets - min(partials, 4 - sets) - head
        if c0 == 0:                          # nothing left here: next position
            return best(i + 1, c1, c2, count_at(i + 3), sets, partials, head)

        numbered = i < NUMBERED_COUNT
        rank = i % 9 + 1                     # only meaningful if numbered
        result = best(i, c0 - 1, c1, c2, sets, partials, head)      # leave it alone
        if c0 >= 3:                                                  # triplet
            result = min(result, best(i, c0 - 3, c1, c2, sets + 1, partials, head))
        if c0 >= 2 and not head:                                     # the pair
            result = min(result, best(i, c0 - 2, c1, c2, sets, partials, 1))
        if c0 >= 2:                                                  # pair as partial
            result = min(result, best(i, c0 - 2, c1, c2, sets, partials + 1, head))
        if numbered and rank <= 7 and c1 >= 1 and c2 >= 1:           # run
            result = min(result, best(i, c0 - 1, c1 - 1, c2 - 1, sets + 1, partials, head))
        if numbered and rank <= 8 and c1 >= 1:                       # e.g. 4-5
            result = min(result, best(i, c0 - 1, c1 - 1, c2, sets, partials + 1, head))
        if numbered and rank <= 7 and c2 >= 1:                       # e.g. 4-6
            result = min(result, best(i, c0 - 1, c1, c2 - 1, sets, partials + 1, head))
        return result

    return best(0, counts[0], counts[1], counts[2], melds, 0, 0)
