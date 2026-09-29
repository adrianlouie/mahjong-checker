import random
from collections import Counter

from checker import can_form_sets, is_winning_hand
from helpers import build_random_winning_hand, hand


# ---------- hands that ARE winning ----------

def test_all_runs():
    assert is_winning_hand(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k 5k"))


def test_all_triplets():
    assert is_winning_hand(hand("1b 1b 1b 9c 9c 9c E E E R R R 5k 5k"))


def test_mixed_runs_and_triplets():
    assert is_winning_hand(hand("2b 3b 4b 7c 7c 7c 1k 2k 3k S S S N N"))


def test_honor_pair():
    assert is_winning_hand(hand("1b 2b 3b 4c 5c 6c 7k 8k 9k 3b 3b 3b R R"))


def test_two_identical_runs():
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


def test_hands_built_to_win_are_recognised():
    rng = random.Random(42)
    checked = 0
    while checked < 500:
        tiles = build_random_winning_hand(rng)
        if tiles is None:
            continue
        assert is_winning_hand(tiles), tiles
        checked += 1


def test_first_pair_choice_can_be_wrong():
    # The checker tries pairs in this order: 6k, 7k, then white dragon.
    # Only the white-dragon pair works, so the first two attempts must be
    # undone (backtracked) before the third succeeds.
    tiles = hand("4b 5b 6b 1c 2c 3c 5k 6k 6k 7k 7k 8k P P")
    assert is_winning_hand(tiles)
    without_6k_pair = Counter(tiles)
    without_6k_pair["6-characters"] -= 2
    assert not can_form_sets(without_6k_pair)
    without_7k_pair = Counter(tiles)
    without_7k_pair["7-characters"] -= 2
    assert not can_form_sets(without_7k_pair)
    without_dragon_pair = Counter(tiles)
    without_dragon_pair["white-dragon"] -= 2
    assert can_form_sets(without_dragon_pair)
