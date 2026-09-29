"""Day 3: waits, "how close am I?", and win probabilities.

Three ideas live here:

1. READY HAND ("ting pai" / tenpai): a 13-tile hand that ONE more tile would
   turn into a winning hand. `winning_tiles` finds which tiles those are by
   brute force: try every possible 14th tile and ask the checker.

2. SHANTEN ("how many tiles away am I?"): 0 = ready, 1 = one step from ready,
   2 = two steps, ... and -1 = already a winning hand. Without this, a fresh
   hand would sit at "0% chance" for many turns and the game would feel dead.
   It's another recursive search, like the checker. Melds you've already
   claimed count as finished sets.

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

def winning_tiles(hand, exposed=()):
    """Which tiles would complete this hand? (empty list = not ready)

    `hand` is your concealed tiles (13 with no melds). `exposed` are the tiles
    in your melds, which still count towards the 4 copies of each tile.

    Brute force: for each of the 34 tile types, add it and run the checker.
    We skip a tile type if all 4 copies are already in our hands - a 5th
    can't exist.
    """
    held = Counter(hand)
    held.update(exposed)
    waits = []
    for tile in TILE_TYPES:
        if held[tile] >= COPIES:
            continue
        if is_winning_hand(list(hand) + [tile]):
            waits.append(tile)
    return waits


# ---------------------------------------------------------------------------
# 2. Shanten
# ---------------------------------------------------------------------------

# The distance calculation runs thousands of times (every bot decision, every
# simulated game), so it is built to be cheap: each suit is solved on its own
# and remembered (cached), then the four groups are combined.

def _plus(options, sets, partials, head):
    """Add a building block to every option; drop options with two pairs."""
    return {(s + sets, p + partials, h + head) for s, p, h in options if h + head <= 1}


def _prune(options):
    """Drop options that are beaten on every count by another option."""
    return {a for a in options
            if not any(b != a and b[0] >= a[0] and b[1] >= a[1] and b[2] >= a[2]
                       for b in options)}


@lru_cache(maxsize=None)
def _group_options(counts, numbered):
    """All (sets, partials, head) splits of ONE suit (or the honors).

    `counts` is a tuple of how many copies we hold of each rank (or of each
    honor). Same trial-and-error idea as the checker: look at the first tile
    left, try each thing it could be part of, and recurse on what remains.
    """
    n = len(counts)

    @lru_cache(maxsize=None)
    def go(i, c0, c1, c2):
        # i = position; c0, c1, c2 = tiles still unused at i, i+1, i+2
        if i >= n:
            return {(0, 0, 0)}
        if c0 == 0:
            return go(i + 1, c1, c2, counts[i + 3] if i + 3 < n else 0)

        found = set(go(i, c0 - 1, c1, c2))                        # leave one unused
        if c0 >= 3:                                                # triplet
            found |= _plus(go(i, c0 - 3, c1, c2), 1, 0, 0)
        if c0 >= 2:
            rest = go(i, c0 - 2, c1, c2)
            found |= _plus(rest, 0, 1, 0)                          # pair as a partial set
            found |= _plus(rest, 0, 0, 1)                          # pair as THE pair
        if numbered:
            if i + 2 < n and c1 and c2:                            # run, e.g. 4-5-6
                found |= _plus(go(i, c0 - 1, c1 - 1, c2 - 1), 1, 0, 0)
            if i + 1 < n and c1:                                   # partial, e.g. 4-5
                found |= _plus(go(i, c0 - 1, c1 - 1, c2), 0, 1, 0)
            if i + 2 < n and c2:                                   # partial, e.g. 4-6
                found |= _plus(go(i, c0 - 1, c1, c2 - 1), 0, 1, 0)
        return frozenset(_prune(found))

    return go(0, counts[0], counts[1], counts[2])


@lru_cache(maxsize=None)
def _shanten_from_counts(counts, melds):
    states = {(melds, 0, 0)}
    for start, stop, numbered in ((0, 9, True), (9, 18, True), (18, 27, True), (27, 34, False)):
        options = _group_options(counts[start:stop], numbered)
        states = _prune({(s1 + s2, p1 + p2, h1 + h2)
                         for s1, p1, h1 in states for s2, p2, h2 in options
                         if h1 + h2 <= 1 and s1 + s2 <= 4})
    return min(8 - (2 * s + min(p, 4 - s) + h) for s, p, h in states)


def shanten(tiles, melds=0):
    """Distance from a winning hand: -1 win, 0 ready, 1, 2, ...

    `tiles` are your CONCEALED tiles; `melds` is how many sets (pong/chi) you
    already have on the table. We split the concealed tiles into building
    blocks:
        set     = triplet or run           (worth 2 points)
        partial = pair or 2-of-a-run       (worth 1 point: one tile from a set)
        head    = the single pair we need  (worth 1 point)
    and the distance is 8 - 2*sets - partials - head for the best split. A hand
    only has room for 4 sets, so partials are capped at 4 - sets. Melds count
    as sets we already have.
    """
    counts = [0] * len(TILE_TYPES)
    for tile in tiles:
        counts[TILE_ORDER[tile]] += 1
    return _shanten_from_counts(tuple(counts), melds)


def useful_tiles(hand, unseen, melds=0):
    """Tiles that would lower this hand's distance, with copies left unseen.

    Returns a list of (tile, copies_left). For a ready hand (distance 0) these
    are exactly the winning tiles.
    """
    current = shanten(hand, melds)
    useful = []
    for tile in _candidate_tiles(hand):
        copies = unseen.get(tile, 0)
        if copies > 0 and shanten(list(hand) + [tile], melds) < current:
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

def unseen_counts(my_hand, discards, melds_tiles=()):
    """Tiles I can't see: the full set minus my hand, all discards, all melds.

    `melds_tiles` are the tiles of every meld on the table (mine and the bots'),
    because claimed sets are face-up. Opponents' hidden hands and the wall are
    both "unseen" to me.
    """
    unseen = Counter(build_full_set())
    unseen.subtract(my_hand)
    unseen.subtract(discards)
    unseen.subtract(melds_tiles)
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


def analyse_hand(hand13, unseen, looks_next_round, looks_rest_of_game, melds=0):
    """Everything the UI shows about a hand that is one tile from a discard."""
    useful = useful_tiles(hand13, unseen, melds)
    copies = sum(n for _, n in useful)
    total = sum(unseen.values())
    return {
        "shanten": shanten(hand13, melds),
        "useful": useful,
        "useful_copies": copies,
        "chance_next_round": chance_to_see(copies, total, looks_next_round),
        "chance_rest_of_game": chance_to_see(copies, total, looks_rest_of_game),
    }


def discard_options(hand14, unseen, looks_next_round, looks_rest_of_game, melds=0):
    """For a hand about to discard: what happens if I discard each tile?

    Returns one row per DIFFERENT tile in the hand, best discard first
    (lowest shanten, then most useful tiles left).
    """
    rows = []
    for tile in sorted(set(hand14), key=TILE_ORDER.__getitem__):
        remaining = list(hand14)
        remaining.remove(tile)
        info = analyse_hand(remaining, unseen, looks_next_round, looks_rest_of_game, melds)
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
