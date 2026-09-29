"""Day 2: the winning-hand checker (the algorithmic core).

A Hong Kong winning hand is 14 tiles that split into:
    4 sets  +  1 pair
where a set is either
    - a triplet ("pung"): three identical tiles, or
    - a run ("chow"): three consecutive ranks in the SAME numbered suit
      (e.g. 3-4-5 bamboo). Winds/dragons can never form a run, and runs
      don't wrap around (8-9-1 is not a run).

THE IDEA (backtracking)
-----------------------
We don't know how to split the hand, so we TRY. Pick a way to pull tiles out
of the hand, then ask the same question about the smaller hand that is left
(recursion). If that smaller hand turns out to be impossible, we UNDO our
choice (backtrack) and try a different one. If every choice fails, the answer
is "not a winning hand".

We store the hand as a Counter: {tile: how many copies}. Removing a set is
then just subtracting from counts, and undoing it is just adding back.
"""

from collections import Counter

from tiles import TILE_ORDER, is_numbered, parse_tile

def is_winning_hand(tiles):
    """True if `tiles` form some sets plus exactly one pair.

    With no melds on the table that means 14 tiles = 4 sets + 1 pair. Each
    meld you have already claimed (pong/chi) is a finished set that lives on
    the table, so you pass only your CONCEALED tiles: 11 tiles for 1 meld,
    8 for 2, 5 for 3, 2 for 4. In every case the count is 3k + 2.
    """
    if len(tiles) < 2 or len(tiles) % 3 != 2:
        return False

    counts = Counter(tiles)

    # Step 1: try every tile that appears at least twice as "the pair".
    for tile in list(counts):
        if counts[tile] >= 2:
            counts[tile] -= 2                # take the pair out
            if can_form_sets(counts):        # can the other 12 tiles be 4 sets?
                return True
            counts[tile] += 2                # it didn't work: put the pair back
    return False


def can_form_sets(counts):
    """True if EVERY tile in `counts` can be used up by triplets and runs.

    This is the recursive (backtracking) part.
    """
    # Find the smallest tile still in the hand (in TILE_ORDER order).
    first = _smallest_tile(counts)

    # Base case: nothing left, so everything was used up. Success!
    if first is None:
        return True

    # Why only look at the smallest tile? Whatever set contains it can only be
    #   (a) a triplet of it, or
    #   (b) a run STARTING at it (nothing smaller is left to start earlier).
    # So there are at most 2 choices, and we never try the same split twice.
    #
    # (Honest note: if we hold 3+ copies of the smallest tile, taking the
    # triplet is always safe - three runs starting at the same tile can always
    # be swapped for a triplet plus other runs. So the "undo" below rarely
    # fires here. The real trial-and-error is choosing the PAIR in
    # is_winning_hand: see test_first_pair_choice_can_be_wrong.)

    # Choice A: use a triplet of `first`.
    if counts[first] >= 3:
        counts[first] -= 3                   # make the choice
        if can_form_sets(counts):            # recurse on the smaller hand
            return True
        counts[first] += 3                   # BACKTRACK: undo the choice

    # Choice B: use a run first, first+1, first+2 (same suit, numbered only).
    run = _run_starting_at(first)
    if run is not None and all(counts[t] >= 1 for t in run):
        for t in run:
            counts[t] -= 1                   # make the choice
        if can_form_sets(counts):
            return True
        for t in run:
            counts[t] += 1                   # BACKTRACK: undo the choice

    # Neither choice worked, so this hand can't be split into sets.
    return False


def _smallest_tile(counts):
    """The first tile (by TILE_ORDER) with a count above zero, or None."""
    remaining = [t for t, n in counts.items() if n > 0]
    if not remaining:
        return None
    return min(remaining, key=TILE_ORDER.__getitem__)


def _run_starting_at(tile):
    """The 3 tiles of a run starting at `tile`, or None if none is possible.

    "3-bamboo" -> ("3-bamboo", "4-bamboo", "5-bamboo")
    "8-bamboo" -> None  (would need a 10)
    "east-wind" -> None (honors have no runs)
    """
    if not is_numbered(tile):
        return None
    suit, rank = parse_tile(tile)
    if rank > 7:
        return None
    return (tile, f"{rank + 1}-{suit}", f"{rank + 2}-{suit}")
