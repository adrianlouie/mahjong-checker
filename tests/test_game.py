import random
from collections import Counter

import pytest

from checker import is_winning_hand
from game import Game
from helpers import hand
from tiles import build_full_set

READY_13 = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")     # waits: 2c, 5c


def fresh(seed=1):
    return Game(random.Random(seed))


def test_new_game_deals_13_plus_a_draw():
    g = fresh()
    assert g.phase == Game.PLAYING
    assert len(g.hand) == 14
    assert g.drawn_tile in g.hand
    assert all(len(b) == 13 for b in g.bots)
    assert len(g.wall) == 136 - 14 - 39


def test_every_tile_is_somewhere_exactly_once():
    g = fresh(3)
    g.discard(g.hand[0])
    everything = g.hand + g.wall + [t for b in g.bots for t in b] + [t for t, _ in g.discards]
    assert Counter(everything) == Counter(build_full_set())


def test_discard_then_bots_play_and_you_draw_again():
    g = fresh()
    tile = g.hand[0]
    g.discard(tile)
    assert g.phase == Game.PLAYING
    assert len(g.hand) == 14                 # 13 after discard + a new draw
    assert len(g.discards) == 4              # you + 3 bots
    assert g.round == 2
    assert len(g.wall) == 136 - 14 - 39 - 3 - 1


def test_cannot_discard_a_tile_you_do_not_hold():
    g = fresh()
    missing = next(t for t in build_full_set() if t not in g.hand)
    with pytest.raises(ValueError):
        g.discard(missing)


def test_cannot_declare_win_with_a_losing_hand():
    with pytest.raises(ValueError):
        fresh().declare_win()


def test_self_draw_win():
    g = fresh()
    g.hand = READY_13 + ["2-circles"]
    assert g.can_declare_win()
    g.declare_win()
    assert g.phase == Game.WON


def test_bot_discard_can_offer_a_win_and_you_can_take_it():
    g = fresh()
    g.hand = READY_13 + ["9-characters"]
    g.bots[0] = ["5-circles"] * 13           # bot 1 will throw a 5c (its draw is a random tile too)
    g.wall = ["5-circles"] * 5               # make sure it also draws a 5c
    g.discard("9-characters")
    assert g.phase == Game.CLAIM
    assert g.offered == ("5-circles", "Bot 1")
    g.declare_win()
    assert g.phase == Game.WON
    assert is_winning_hand(g.hand)


def test_passing_a_claim_lets_the_bots_continue():
    g = fresh()
    g.hand = READY_13 + ["9-characters"]
    g.bots[0] = ["5-circles"] * 13
    g.wall = ["5-circles"] + ["1-bamboo"] * 10
    g.discard("9-characters")
    assert g.phase == Game.CLAIM
    g.pass_claim()
    assert g.phase == Game.PLAYING           # bots 2 and 3 played, you drew
    assert ("5-circles", "Bot 1") in g.discards
    assert len(g.hand) == 14


def test_empty_wall_ends_the_game_as_a_draw():
    g = fresh()
    g.wall = []
    g.discard(g.hand[0])
    assert g.phase == Game.DRAWN
    with pytest.raises(ValueError):
        g.discard(g.hand[0])


def test_analysis_and_history_update_each_turn():
    g = fresh()
    first = g.to_dict()
    assert len(first["analysis"]["options"]) >= 1
    assert len(first["history"]) == 1
    g.discard(g.hand[0])
    assert len(g.to_dict()["history"]) == 2


def test_state_dict_has_what_the_page_needs():
    state = fresh().to_dict()
    for key in ["phase", "hand", "drawn_tile", "discards", "wall_count",
                "round", "log", "analysis", "history", "can_declare_win"]:
        assert key in state
