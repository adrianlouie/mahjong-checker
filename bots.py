"""The bots' brains. Deliberately simple, and built from pieces you already know.

A bot is "greedy about distance from winning" (shanten, see probability.py):
    - it wins whenever it can (checked by the game engine with is_winning_hand)
    - when discarding, it throws the tile that leaves its hand CLOSEST to winning
    - it claims a pong/chi only if that brings it closer to winning

It does NOT read other players' discards, defend, or plan. That keeps it easy
to explain, and it still plays far better than random discards.
"""

from collections import Counter

from probability import shanten
from tiles import TILE_ORDER, parse_tile


def _keep_value(tile, counts):
    """Tie-breaker: how much a tile is worth keeping (higher = keep).

    Pairs and neighbours in the same suit are worth more than loners.
    """
    suit, rank = parse_tile(tile)
    value = 3 * (counts[tile] - 1)
    if rank is not None:
        for offset, weight in ((-2, 1), (-1, 2), (1, 2), (2, 1)):
            if 1 <= rank + offset <= 9 and counts.get(f"{rank + offset}-{suit}"):
                value += weight
    return value


def choose_discard(concealed, melds=0):
    """Pick the tile to throw: lowest resulting distance, then least useful."""
    counts = Counter(concealed)
    best_tile, best_key = None, None
    for tile in counts:
        rest = list(concealed)
        rest.remove(tile)
        key = (shanten(rest, melds), _keep_value(tile, counts), TILE_ORDER[tile])
        if best_key is None or key < best_key:
            best_tile, best_key = tile, key
    return best_tile


def best_distance_after_discarding(concealed, melds):
    """The distance you could reach by discarding the best tile from `concealed`."""
    return min(shanten([t for i, t in enumerate(concealed) if i != skip], melds)
               for skip in range(len(concealed)))


def distance_after_claim(concealed, melds, used_tiles):
    """Distance after claiming a set with `used_tiles` from your hand, then discarding well.

    `used_tiles` are the tiles taken out of the concealed hand (2 of them for a
    pong or chi). The claimed discard itself never enters the concealed hand.
    """
    rest = list(concealed)
    for tile in used_tiles:
        rest.remove(tile)
    return best_distance_after_discarding(rest, melds + 1)


def wants_pong(concealed, melds, tile):
    """Claim the pong only if it makes the hand strictly closer to winning."""
    before = shanten(concealed, melds)
    return distance_after_claim(concealed, melds, [tile, tile]) < before


def best_chi(concealed, melds, options):
    """Of the possible chi options, the one that helps most, or None if none help."""
    before = shanten(concealed, melds)
    best, best_distance = None, before
    for pair in options:
        distance = distance_after_claim(concealed, melds, pair)
        if distance < best_distance:
            best, best_distance = pair, distance
    return best
