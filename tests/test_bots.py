from bots import choose_discard
from helpers import hand
from melds import can_pong, chi_options
from probability import shanten

READY_13 = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")


def test_bot_discards_the_loose_tile_and_stays_ready():
    tiles = READY_13 + hand("R")
    assert choose_discard(tiles) == "red-dragon"


def test_bot_never_breaks_a_ready_hand_when_it_can_avoid_it():
    for extra in ("9k", "E", "1c", "N"):
        tiles = READY_13 + hand(extra)
        rest = list(tiles)
        rest.remove(choose_discard(tiles))
        assert shanten(rest) == 0


def test_bot_discards_lone_honor_before_a_pair():
    tiles = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k E W 7k")
    assert choose_discard(tiles) in ("east-wind", "west-wind", "7-characters")
    assert choose_discard(tiles) != "5-characters"


def test_bot_with_a_meld_counts_it():
    # 1 meld on the table + 10 concealed tiles that are ready; 1 extra tile to throw
    tiles = hand("1b 2b 3b 4c 5c 6c 7k 8k 9k 5k R")
    assert choose_discard(tiles, melds=1) == "red-dragon"


def test_can_pong():
    assert can_pong(hand("3b 3b 5c"), "3-bamboo")
    assert not can_pong(hand("3b 5c"), "3-bamboo")


def test_chi_options_in_the_middle_of_the_range():
    options = chi_options(hand("2b 3b 5b 6b 9c"), "4-bamboo")
    assert set(options) == {("2-bamboo", "3-bamboo"), ("3-bamboo", "5-bamboo"),
                            ("5-bamboo", "6-bamboo")}


def test_chi_options_at_the_edges_and_across_suits():
    assert chi_options(hand("2b 3b"), "1-bamboo") == [("2-bamboo", "3-bamboo")]
    assert chi_options(hand("7b 8b"), "9-bamboo") == [("7-bamboo", "8-bamboo")]
    assert chi_options(hand("2c 3c"), "1-bamboo") == []          # wrong suit
    assert chi_options(hand("E E S S"), "west-wind") == []       # honors have no runs
    assert chi_options(hand("8b 9b"), "1-bamboo") == []          # no wrap-around
