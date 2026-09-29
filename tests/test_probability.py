import random

import pytest

from checker import is_winning_hand
from helpers import hand, near_winning_hands
from probability import (_candidate_tiles, TILE_TYPES, analyse_hand,
                         chance_to_see, discard_options, estimate_ready_rate,
                         estimate_win_rate, shanten, shanten_distribution,
                         unseen_counts, useful_tiles, winning_tiles)


# ---------- winning_tiles (ready hands) ----------

def test_single_wait():
    tiles = hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k")
    assert winning_tiles(tiles) == ["5-characters"]


def test_two_way_wait():
    # 3c 4c waiting for 2c or 5c
    tiles = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")
    assert winning_tiles(tiles) == ["2-circles", "5-circles"]


def test_not_ready_hand_has_no_waits():
    tiles = hand("1b 4b 7b 1c 4c 7c 1k 4k 7k E S W N")
    assert winning_tiles(tiles) == []


def test_cannot_wait_on_a_fifth_copy():
    # Holding all four 5k: the only "completing" tile would be a 5th 5k.
    tiles = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 5k 5k")
    assert winning_tiles(tiles) == []


# ---------- shanten ----------

def test_shanten_of_winning_hand_is_minus_one():
    assert shanten(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k 5k")) == -1


def test_shanten_of_ready_hand_is_zero():
    assert shanten(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 1c 2c 3c 5k")) == 0


def test_shanten_one_step_from_ready():
    # 3 sets + a pair + two isolated tiles: one tile to become ready.
    assert shanten(hand("1b 2b 3b 4b 5b 6b 7b 8b 9b 5k 5k 1c 9c")) == 1


def test_shanten_of_scattered_hand_is_large():
    assert shanten(hand("1b 4b 7b 1c 4c 7c 1k 4k 7k E S W N")) >= 5


def test_shanten_agrees_with_checker_and_waits_on_near_winning_hands():
    rng = random.Random(11)
    for tiles in near_winning_hands(rng, 300, size=14):
        assert (shanten(tiles) == -1) == is_winning_hand(tiles), tiles
    for tiles in near_winning_hands(rng, 300, size=13):
        assert (shanten(tiles) == 0) == bool(winning_tiles(tiles)), tiles


def test_shanten_never_below_minus_one_or_above_eight():
    rng = random.Random(2)
    for tiles in near_winning_hands(rng, 200, size=13, max_swaps=13):
        assert 0 <= shanten(tiles) <= 8


# ---------- useful tiles ----------

def test_useful_tiles_of_ready_hand_are_its_waits():
    tiles = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")
    unseen = unseen_counts(tiles, [])
    assert [t for t, _ in useful_tiles(tiles, unseen)] == winning_tiles(tiles)


def test_candidate_shortcut_matches_trying_every_tile():
    rng = random.Random(5)
    for tiles in near_winning_hands(rng, 60, size=13, max_swaps=8):
        current = shanten(tiles)
        everything = {t for t in TILE_TYPES if shanten(tiles + [t]) < current}
        shortcut = {t for t in _candidate_tiles(tiles) if shanten(tiles + [t]) < current}
        assert shortcut == everything, tiles


def test_useful_copies_shrink_when_tiles_are_discarded():
    tiles = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")
    fresh = analyse_hand(tiles, unseen_counts(tiles, []), 4, 60)
    later = analyse_hand(tiles, unseen_counts(tiles, ["2-circles", "5-circles", "5-circles"]), 4, 60)
    assert fresh["useful_copies"] == 8          # 4 x 2c + 4 x 5c, none held
    assert later["useful_copies"] == 5
    assert later["chance_next_round"] < fresh["chance_next_round"]


# ---------- probability maths ----------

def test_chance_to_see_by_hand():
    assert chance_to_see(1, 4, 1) == pytest.approx(0.25)
    assert chance_to_see(2, 4, 2) == pytest.approx(1 - 1 / 6)   # 1 - C(2,2)/C(4,2)
    assert chance_to_see(0, 10, 4) == 0
    assert chance_to_see(1, 3, 5) == 1                          # I see everything


def test_chance_grows_with_more_looks_and_more_copies():
    assert chance_to_see(3, 100, 8) > chance_to_see(3, 100, 4)
    assert chance_to_see(6, 100, 4) > chance_to_see(3, 100, 4)


def test_unseen_counts():
    mine = hand("1b 1b 2b")
    unseen = unseen_counts(mine, ["1-bamboo", "9-circles"])
    assert sum(unseen.values()) == 136 - 3 - 2
    assert unseen["1-bamboo"] == 4 - 2 - 1
    assert unseen["9-circles"] == 3


# ---------- discard options ----------

def test_discard_options_prefers_ready_discard():
    # 14 tiles: winning tiles complete after discarding the loose 9k.
    tiles = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c 9k")
    rows = discard_options(tiles, unseen_counts(tiles, []), 4, 60)
    assert rows[0]["discard"] == "9-characters"
    assert rows[0]["shanten"] == 0
    assert {r["discard"] for r in rows} == set(tiles)


# ---------- Monte Carlo ----------

def test_random_hands_almost_never_win():
    rate = estimate_win_rate(3000, random.Random(1))
    assert 0 <= rate < 0.01


def test_ready_rate_is_small():
    rate = estimate_ready_rate(300, random.Random(1))
    assert 0 <= rate < 0.1


def test_shanten_distribution_sums_to_one_and_is_far_from_winning():
    dist = shanten_distribution(300, size=13, rng=random.Random(1))
    assert sum(dist.values()) == pytest.approx(1)
    average = sum(k * v for k, v in dist.items())
    assert average > 3
