import random
from collections import Counter

import pytest

from tiles import (all_tile_types, build_full_set, is_numbered, parse_tile,
                   random_hand, sorted_hand, tile_symbol)


def test_there_are_34_tile_types():
    assert len(all_tile_types()) == 34


def test_full_set_has_136_tiles_with_4_of_each():
    full = build_full_set()
    assert len(full) == 136
    assert set(Counter(full).values()) == {4}


def test_parse_numbered_tile():
    assert parse_tile("3-bamboo") == ("bamboo", 3)
    assert parse_tile("9-characters") == ("characters", 9)


def test_parse_honor_tile_has_no_rank():
    assert parse_tile("east-wind") == ("east-wind", None)
    assert parse_tile("red-dragon") == ("red-dragon", None)


def test_parse_unknown_tile_raises():
    with pytest.raises(ValueError):
        parse_tile("10-bamboo")
    with pytest.raises(ValueError):
        parse_tile("banana")


def test_is_numbered():
    assert is_numbered("5-circles")
    assert not is_numbered("west-wind")


def test_random_hand_has_right_size_and_legal_counts():
    rng = random.Random(1)
    for _ in range(200):
        hand = random_hand(14, rng)
        assert len(hand) == 14
        assert max(Counter(hand).values()) <= 4


def test_sorted_hand_groups_suits_then_honors():
    hand = ["red-dragon", "9-bamboo", "1-circles", "1-bamboo", "east-wind"]
    assert sorted_hand(hand) == ["1-bamboo", "9-bamboo", "1-circles",
                                 "east-wind", "red-dragon"]


def test_every_tile_has_a_distinct_symbol():
    symbols = {tile_symbol(t) for t in all_tile_types()}
    assert len(symbols) == 34
