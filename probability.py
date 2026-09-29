"""Day 3: waits, "how close am I?", and win probabilities.

Three ideas live here:

1. READY HAND ("ting pai" / tenpai): a 13-tile hand that ONE more tile would
   turn into a winning hand. `winning_tiles` finds which tiles those are by
   brute force: try every possible 14th tile and ask the checker.

2. SHANTEN ("how many tiles away am I?"): 0 = ready, 1 = one step from ready,
   2 = two steps, ... and -1 = already a winning hand. Without this, a fresh
   hand would sit at "0% chance" for many turns and the game would feel dead.
   It's another recursive search, like the checker.

3. PROBABILITY: given the tiles I can't see yet (the "unseen pool"), what is
   the chance that I see at least one tile that helps me?
"""

import random
from collections import Counter
from functools import lru_cache
from math import comb

from checker import is_winning_hand
from tiles import (COPIES, SUITS, TILE_ORDER, all_tile_types, build_full_set,
                   is_numbered, parse_tile, random_hand)

TILE_TYPES = all_tile_types()
NUMBERED_COUNT = 27   # the first 27 tile types are the numbered suits (3 x 9)


# ---------------------------------------------------------------------------
# 1. Ready hands / waits
# ---------------------------------------------------------------------------

def winning_tiles(hand13):
    """Which tiles would complete this 13-tile hand? (empty list = not ready)

    Brute force: for each of the 34 tile types, add it and run the checker.
    We skip a tile type if we already hold all 4 copies - a 5th can't exist.
    """
    held = Counter(hand13)
    waits = []
    for tile in TILE_TYPES:
        if held[tile] >= COPIES:
            continue
        if is_winning_hand(list(hand13) + [tile]):
            waits.append(tile)
    return waits


# ---------------------------------------------------------------------------
# 2. Shanten
# ---------------------------------------------------------------------------

def shanten(tiles):
    """Distance from a winning hand: -1 win, 0 ready, 1, 2, ...

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

    return best(0, counts[0], counts[1], counts[2], 0, 0, 0)


def useful_tiles(hand, unseen):
    """Tiles that would lower this hand's shanten, with copies left unseen.

    Returns a list of (tile, copies_left). For a ready hand (shanten 0) these
    are exactly the winning tiles.
    """
    current = shanten(hand)
    useful = []
    for tile in _candidate_tiles(hand):
        copies = unseen.get(tile, 0)
        if copies > 0 and shanten(list(hand) + [tile]) < current:
            useful.append((tile, copies))
    return useful


def _candidate_tiles(hand):
    """Tile types that could possibly help: ones we hold, or within 2 ranks of one.

    A tile far away from everything in the hand can only ever be a lone
    "leftover", so it can't lower the shanten. Skipping them makes this ~3x
    faster. (tests/test_probability.py checks this shortcut gives the same
    answer as trying all 34.)
    """
    wanted = set()
    for tile in set(hand):
        suit, rank = parse_tile(tile)
        wanted.add(tile)
        if rank is not None:
            for r in (rank - 2, rank - 1, rank + 1, rank + 2):
                if 1 <= r <= 9:
                    wanted.add(f"{r}-{suit}")
    return [t for t in TILE_TYPES if t in wanted]


# ---------------------------------------------------------------------------
# 3. Probability
# ---------------------------------------------------------------------------

def unseen_counts(my_hand, discards):
    """Tiles I can't see: the full set minus my hand minus everything discarded.

    (Opponents' hidden hands and the wall are both "unseen" to me.)
    """
    unseen = Counter(build_full_set())
    unseen.subtract(my_hand)
    unseen.subtract(discards)
    return +unseen      # unary + drops zero/negative counts


def chance_to_see(helpful_copies, unseen_total, looks):
    """P(at least one of the next `looks` tiles I see is a helpful one).

    Picture a bag with `unseen_total` tiles, `helpful_copies` of them helpful.
    I pull `looks` tiles out without putting any back. The chance I get NO
    helpful tile is C(N-K, looks) / C(N, looks) - "ways to pick only unhelpful
    tiles" over "all ways to pick". Subtract from 1 for "at least one".
    """
    if helpful_copies <= 0 or looks <= 0 or unseen_total <= 0:
        return 0.0
    looks = min(looks, unseen_total)
    misses = comb(unseen_total - helpful_copies, looks) if unseen_total - helpful_copies >= looks else 0
    return 1 - misses / comb(unseen_total, looks)


def analyse_hand(hand13, unseen, looks_next_round, looks_rest_of_game):
    """Everything the UI shows about a 13-tile hand."""
    useful = useful_tiles(hand13, unseen)
    copies = sum(n for _, n in useful)
    total = sum(unseen.values())
    return {
        "shanten": shanten(hand13),
        "useful": useful,
        "useful_copies": copies,
        "chance_next_round": chance_to_see(copies, total, looks_next_round),
        "chance_rest_of_game": chance_to_see(copies, total, looks_rest_of_game),
    }


def discard_options(hand14, unseen, looks_next_round, looks_rest_of_game):
    """For a 14-tile hand: what happens to my chances if I discard each tile?

    Returns one row per DIFFERENT tile in the hand, best discard first
    (lowest shanten, then most useful tiles left).
    """
    rows = []
    for tile in sorted(set(hand14), key=TILE_ORDER.__getitem__):
        remaining = list(hand14)
        remaining.remove(tile)
        info = analyse_hand(remaining, unseen, looks_next_round, looks_rest_of_game)
        info["discard"] = tile
        rows.append(info)
    rows.sort(key=lambda r: (r["shanten"], -r["useful_copies"]))
    return rows


# ---------------------------------------------------------------------------
# Monte Carlo: "just try it thousands of times"
# ---------------------------------------------------------------------------

def estimate_win_rate(trials=100_000, rng=random):
    """Deal `trials` random 14-tile hands; return the fraction that win."""
    wins = sum(is_winning_hand(random_hand(14, rng)) for _ in range(trials))
    return wins / trials


def estimate_ready_rate(trials=20_000, rng=random):
    """Deal `trials` random 13-tile hands; return the fraction that are ready."""
    ready = sum(bool(winning_tiles(random_hand(13, rng))) for _ in range(trials))
    return ready / trials


def shanten_distribution(trials=5_000, size=13, rng=random):
    """Deal random hands and count how far from winning each one is.

    Returns {shanten_value: fraction_of_hands}. This is the interesting Monte
    Carlo result: almost no random hand wins, but you can see how far a typical
    deal is from winning.
    """
    tally = Counter(shanten(random_hand(size, rng)) for _ in range(trials))
    return {value: tally[value] / trials for value in sorted(tally)}
