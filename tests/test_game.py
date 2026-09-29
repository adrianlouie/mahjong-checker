import random
from collections import Counter

import pytest

from checker import is_winning_hand
from game import Game
from helpers import hand
from tiles import build_full_set

READY_13 = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")     # waits: 2c, 5c
JUNK_13 = hand("1b 4b 7b 1c 4c 7c 1k 4k 7k E S W N")             # nowhere near winning


def fresh(seed=1):
    return Game(random.Random(seed))


def everything(g):
    """Every tile in the game, wherever it is."""
    tiles = list(g.wall) + [t for t, _ in g.discards]
    for p in g.players:
        tiles += p.concealed + p.meld_tiles()
    return tiles


def rig_discard(g, tile, src, hand_for_you=None):
    """Pretend player `src` just threw `tile` and let the engine resolve it."""
    if hand_for_you is not None:
        g.players[0].concealed = list(hand_for_you)
    g.discards.append((tile, src))
    g.phase = Game.RUNNING
    g.next = ("resolve", tile, src, False)
    g._run()


# ---------- setup ----------

def test_new_game_deals_13_each_plus_your_draw():
    g = fresh()
    assert g.phase == Game.PLAYING
    assert len(g.me.concealed) == 14
    assert g.drawn_tile in g.me.concealed
    assert all(len(p.concealed) == 13 for p in g.players[1:])
    assert len(g.wall) == 136 - 14 - 39


def test_every_tile_is_somewhere_exactly_once():
    g = fresh(3)
    g.discard(g.me.concealed[0])
    assert Counter(everything(g)) == Counter(build_full_set())


# ---------- playing ----------

def test_discard_then_bots_play_and_you_draw_again():
    g = fresh()
    g.discard(g.me.concealed[0])
    assert g.phase in (Game.PLAYING, Game.CLAIM, Game.WON)
    if g.phase == Game.PLAYING and not g.me.melds:
        assert len(g.me.concealed) == 14
        assert g.round == 2


def test_cannot_discard_a_tile_you_do_not_hold():
    g = fresh()
    missing = next(t for t in build_full_set() if t not in g.me.concealed)
    with pytest.raises(ValueError):
        g.discard(missing)


def test_cannot_declare_win_with_a_losing_hand():
    with pytest.raises(ValueError):
        fresh().declare_win()


def test_self_draw_win():
    g = fresh()
    g.me.concealed = READY_13 + ["2-circles"]
    assert g.can_declare_win()
    g.declare_win()
    assert g.phase == Game.WON
    assert g.winner == 0 and g.win_kind == "self-draw"


def test_empty_wall_ends_the_game_as_a_draw():
    g = fresh()
    g.me.concealed = JUNK_13 + ["9-characters"]
    for bot in g.players[1:]:
        bot.concealed = list(JUNK_13)                    # nobody can win
    g.wall = []
    g.discard("9-characters")
    assert g.phase == Game.DRAWN
    with pytest.raises(ValueError):
        g.discard(g.me.concealed[0])


# ---------- winning on discards ----------

def test_you_are_offered_a_win_on_a_bot_discard_and_can_take_it():
    g = fresh()
    rig_discard(g, "2-circles", 1, READY_13)
    assert g.phase == Game.CLAIM
    assert g.offer["win"] and g.offer["tile"] == "2-circles" and g.offer["from"] == 1
    g.declare_win()
    assert g.phase == Game.WON
    assert g.winner == 0 and g.win_kind == "discard"
    assert is_winning_hand(g.me.concealed)
    assert ("2-circles", 1) not in g.discards


def test_passing_a_win_lets_the_game_continue():
    g = fresh()
    for bot in g.players[1:]:
        bot.concealed = list(JUNK_13)
    rig_discard(g, "2-circles", 1, READY_13)
    assert g.phase == Game.CLAIM
    g.pass_claim()
    assert g.phase in (Game.PLAYING, Game.CLAIM)         # bots 2, 3 played; you drew or got an offer
    assert ("2-circles", 1) in g.discards


def test_a_bot_wins_on_your_discard():
    g = fresh()
    g.me.concealed = JUNK_13 + ["2-circles"]
    g.players[1].concealed = list(READY_13)
    g.discard("2-circles")
    assert g.phase == Game.WON
    assert g.winner == 1 and g.win_kind == "discard"
    assert is_winning_hand(g.players[1].concealed)


def test_closest_seat_after_the_thrower_wins_first():
    g = fresh()
    g.me.concealed = JUNK_13 + ["2-circles"]
    g.players[2].concealed = list(READY_13)
    g.players[3].concealed = list(READY_13)
    g.discard("2-circles")
    assert g.winner == 2


def test_a_bot_wins_on_its_own_draw():
    g = fresh()
    g.me.concealed = JUNK_13 + ["9-characters"]
    g.players[1].concealed = list(READY_13)
    g.wall = ["2-circles"]
    g.discard("9-characters")
    assert g.winner == 1 and g.win_kind == "self-draw"


# ---------- whole games ----------

def test_auto_games_finish_and_keep_every_tile():
    for seed in range(15):
        g = Game(random.Random(seed), auto=True)
        assert g.phase in (Game.WON, Game.DRAWN)
        assert Counter(everything(g)) == Counter(build_full_set())
        if g.phase == Game.WON:
            winner = g.players[g.winner]
            assert is_winning_hand(winner.concealed)
            assert len(winner.concealed) + 3 * len(winner.melds) == 14


def test_bots_win_a_fair_share_of_games():
    # smarter than random discards: at least some of 40 games are won
    wins = sum(Game(random.Random(s), auto=True).phase == Game.WON for s in range(40))
    assert wins >= 5


# ---------- what the page needs ----------

def test_state_dict_has_what_the_page_needs():
    state = fresh().to_dict()
    for key in ["phase", "winner", "hand", "melds", "drawn_tile", "offer", "others",
                "discards", "wall_count", "round", "log", "analysis", "history",
                "can_declare_win"]:
        assert key in state
    assert len(state["others"]) == 3
    assert state["others"][0]["hand"] is None            # bots' hands stay hidden


def test_bot_hands_are_revealed_when_the_game_ends():
    g = fresh()
    g.me.concealed = READY_13 + ["2-circles"]
    g.declare_win()
    assert all(o["hand"] is not None for o in g.to_dict()["others"])


def test_analysis_and_history_update_each_turn():
    g = fresh()
    assert g.to_dict()["analysis"]["options"]
    assert len(g.history) == 1
    g.discard(g.me.concealed[0])
    if g.phase == Game.PLAYING:
        assert len(g.history) == 2


# ---------- claiming: pong and chi ----------

def rigged(me, bots=(JUNK_13, JUNK_13, JUNK_13)):
    g = fresh()
    g.players[0].concealed = list(me)
    for player, tiles in zip(g.players[1:], bots):
        player.concealed = list(tiles)
    return g


def resolve(g, tile, src):
    g.discards.append((tile, src))
    return g._resolve(tile, src, False)


def test_you_are_offered_a_pong():
    g = rigged(READY_13)                                   # holds 5-characters twice
    assert resolve(g, "5-characters", 2) is True
    assert g.phase == Game.CLAIM
    assert g.offer["pong"] and not g.offer["win"] and g.offer["chi"] == []


def test_pong_makes_a_meld_and_you_discard_next():
    g = rigged(READY_13)
    rig_discard(g, "5-characters", 2)
    assert g.phase == Game.CLAIM
    g.claim("pong")
    assert g.phase == Game.PLAYING
    assert g.me.melds == [{"type": "pong", "claimed": "5-characters", "from": 2,
                           "tiles": ["5-characters"] * 3}]
    assert len(g.me.concealed) == 11
    assert ("5-characters", 2) not in g.discards
    g.discard(g.me.concealed[0])                             # you can carry on playing
    assert g.phase in (Game.PLAYING, Game.CLAIM, Game.WON)


def test_chi_is_only_offered_for_the_player_before_you():
    me = hand("2b 3b 5b 6b R G P E S W N 9c 9k")
    g = rigged(me)
    assert resolve(g, "4-bamboo", 3) is True                # bot 3 sits right before you
    assert {tuple(o) for o in g.offer["chi"]} == {
        ("2-bamboo", "3-bamboo"), ("3-bamboo", "5-bamboo"), ("5-bamboo", "6-bamboo")}

    g = rigged(me)
    assert resolve(g, "4-bamboo", 2) is False               # bot 2 is NOT before you
    assert g.offer is None
    assert g.next == ("draw", 3)


def test_chi_makes_a_sorted_meld():
    g = rigged(hand("2b 3b 5b 6b R G P E S W N 9c 9k"))
    rig_discard(g, "4-bamboo", 3)
    g.claim("chi", ["3-bamboo", "5-bamboo"])
    assert g.me.melds[0]["tiles"] == ["3-bamboo", "4-bamboo", "5-bamboo"]
    assert g.me.melds[0]["type"] == "chi"
    assert g.phase == Game.PLAYING
    assert sorted(g.me.concealed) == sorted(hand("2b 6b R G P E S W N 9c 9k"))


def test_invalid_claims_are_rejected():
    g = rigged(hand("2b 3b 5b 6b R G P E S W N 9c 9k"))
    rig_discard(g, "4-bamboo", 3)
    with pytest.raises(ValueError):
        g.claim("pong")                                     # you hold no pair
    with pytest.raises(ValueError):
        g.claim("chi", ["7-bamboo", "8-bamboo"])            # you don't hold those
    with pytest.raises(ValueError):
        g.claim("kong")
    with pytest.raises(ValueError):
        fresh().claim("pong")                               # nothing on offer


def test_win_beats_pong():
    g = rigged(READY_13, bots=(JUNK_13, READY_13 + [], JUNK_13))
    g.players[2].concealed = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")   # ready on 2c / 5c
    g.players[0].concealed = hand("2c 2c 1k 4k 7k E S W N R G P 9c")          # you could pong 2c
    g.discards.append(("2-circles", 1))
    g.phase, g.next = Game.RUNNING, ("resolve", "2-circles", 1, False)
    g._run()
    assert g.winner == 2


def test_a_bot_pongs_when_it_gets_closer_to_winning():
    bot2 = hand("1b 2b 3b 4b 5b 6b 1k 2k 3k 7c 7c 8k 9c")
    g = rigged(JUNK_13, bots=(JUNK_13, bot2, JUNK_13))
    assert resolve(g, "7-circles", 1) is False
    assert g.next == ("discard", 2)
    assert g.players[2].melds[0]["type"] == "pong"
    assert ("7-circles", 1) not in g.discards


def test_a_bot_does_not_pong_when_it_would_not_help():
    bot2 = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")   # ready: pong would break the pair
    g = rigged(JUNK_13, bots=(JUNK_13, bot2, JUNK_13))
    assert resolve(g, "5-characters", 1) is False
    assert g.players[2].melds == []


def test_the_next_bot_chis_your_discard():
    bot1 = hand("1b 2b 4b 5b 6b 1k 2k 3k 7c 8c 9c R G")
    g = rigged(JUNK_13 + ["3-bamboo"], bots=(bot1, JUNK_13, JUNK_13))
    g.discard("3-bamboo")
    assert g.players[1].melds[0]["type"] == "chi"
    assert g.players[1].melds[0]["tiles"] == ["1-bamboo", "2-bamboo", "3-bamboo"]
    assert ("3-bamboo", 0) not in g.discards


def test_a_bot_two_seats_away_cannot_chi():
    chi_able = hand("1b 2b 4b 5b 6b 1k 2k 3k 7c 8c 9c R G")
    g = rigged(JUNK_13, bots=(JUNK_13, chi_able, JUNK_13))
    assert resolve(g, "3-bamboo", 0) is False                # bot 2 is not next after you
    assert g.players[2].melds == []


def test_claim_choices_show_distance_after_each_option():
    g = rigged(hand("2b 3b 5b 6b 7b 8b 9b R G P E S W"))
    rig_discard(g, "4-bamboo", 3)
    choices = g.analysis()["claims"]
    assert choices[0]["action"] == "pass"
    assert {c["action"] for c in choices} == {"pass", "chi"}
    assert all("shanten" in c for c in choices)


def test_bots_actually_claim_in_full_games():
    melds = sum(len(p.melds) for seed in range(30)
                for p in Game(random.Random(seed), auto=True).players)
    assert melds > 0
