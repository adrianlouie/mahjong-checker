"""Helpers shared by several test files."""

import random
from collections import Counter

from tiles import SUITS, all_tile_types


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
