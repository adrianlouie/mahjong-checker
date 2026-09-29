import random
from collections import Counter

from checker import can_form_sets, is_winning_hand
from tiles import SUITS, WINDS, DRAGONS, all_tile_types


def hand(text):
    """Turn "1b 2b 3b" style shorthand into tile names (test helper only)."""
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


# ---------- hands that ARE winning ----------

def test_all_runs():
    assert is_winning_hand(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k 5k"))


def test_all_triplets():
    assert is_winning_hand(hand("1b 1b 1b 9c 9c 9c E E E R R R 5k 5k"))


def test_mixed_runs_and_triplets():
    assert is_winning_hand(hand("2b 3b 4b 7c 7c 7c 1k 2k 3k S S S N N"))


def test_honor_pair():
    assert is_winning_hand(hand("1b 2b 3b 4c 5c 6c 7k 8k 9k 3b 3b 3b R R"))


def test_needs_backtracking():
    # 1b 1b 2b 2b 3b 3b can only be split as two runs (1-2-3 twice).
    # There are only two 1b, so the "triplet" choice is impossible.
    assert is_winning_hand(hand("1b 1b 2b 2b 3b 3b 4c 5c 6c 7k 8k 9k R R"))


def test_pair_must_be_chosen_carefully():
    # Three 2b: could be a triplet OR pair + part of a run. Only one works.
    assert is_winning_hand(hand("2b 2b 2b 3b 4b 5c 6c 7c 1k 2k 3k 9c 9c 9c"))


# ---------- hands that are NOT winning ----------

def test_wrong_length():
    assert not is_winning_hand(hand("1b 2b 3b"))
    assert not is_winning_hand(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k"))


def test_run_cannot_cross_suits():
    assert not is_winning_hand(hand("1b 2c 3k 4b 5b 6b 7c 8c 9c 1c 1c 1c 5k 5k"))


def test_winds_cannot_form_a_run():
    assert not is_winning_hand(hand("E S W 1b 2b 3b 4c 5c 6c 7k 8k 9k R R"))


def test_run_cannot_wrap_around():
    assert not is_winning_hand(hand("8b 9b 1b 2c 3c 4c 5k 6k 7k 1c 1c 1c 9k 9k"))


def test_two_pairs_and_junk():
    assert not is_winning_hand(hand("1b 1b 3b 3b 5b 5b 7b 7b 9b 9b 1c 1c 3c 3c"))


def test_no_pair_at_all():
    assert not is_winning_hand(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 4c 5c"))


# ---------- the recursion itself, on 12-tile inputs ----------

def test_can_form_sets_empty_hand_is_true():
    assert can_form_sets(Counter())


def test_can_form_sets_true_and_false():
    assert can_form_sets(Counter(hand("1b 2b 3b 4b 5b 6b 7c 7c 7c 9k 9k 9k")))
    assert not can_form_sets(Counter(hand("1b 2b 4b 5b 6b 7b 7c 7c 7c 9k 9k 9k")))


def test_checker_does_not_mutate_its_input():
    tiles = hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k 5k")
    before = list(tiles)
    is_winning_hand(tiles)
    assert tiles == before


def _build_random_winning_hand(rng):
    """Build a hand that is winning BY CONSTRUCTION: 4 random sets + a pair.

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


def test_hands_built_to_win_are_recognised():
    rng = random.Random(42)
    checked = 0
    while checked < 500:
        tiles = _build_random_winning_hand(rng)
        if tiles is None:
            continue
        assert is_winning_hand(tiles), tiles
        checked += 1
