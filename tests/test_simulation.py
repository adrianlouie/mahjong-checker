import random
from collections import Counter

import pytest

from game import Game
from helpers import hand
from simulation import apply_action, candidate_actions, simulate
from tiles import build_full_set

READY_13 = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")
JUNK_13 = hand("1b 4b 7b 1c 4c 7c 1k 4k 7k E S W N")


def game_with_my_hand(tiles, seed=1):
    """A consistent fresh game in which you hold exactly `tiles` (14 of them)."""
    g = Game(random.Random(seed))
    g.me.concealed = list(tiles)
    g.drawn_tile = None
    return g.determinize(random.Random(seed), auto=False)


def all_tiles(g):
    tiles = list(g.wall) + [t for t, _ in g.discards]
    for p in g.players:
        tiles += p.concealed + p.meld_tiles()
    return tiles


# ---------- worlds ----------

def test_determinize_keeps_what_you_know_and_deals_the_rest():
    g = Game(random.Random(2))
    g.discard(g.me.concealed[0])
    world = g.determinize(random.Random(9))
    assert Counter(all_tiles(world)) == Counter(build_full_set())
    assert world.me.concealed == g.me.concealed
    assert world.discards == g.discards
    assert [len(p.concealed) for p in world.players] == [len(p.concealed) for p in g.players]
    assert len(world.wall) == len(g.wall)


def test_determinize_actually_reshuffles_hidden_tiles():
    g = Game(random.Random(2))
    world = g.determinize(random.Random(9))
    assert world.players[1].concealed != g.players[1].concealed


def test_simulating_never_changes_the_real_game():
    g = Game(random.Random(4))
    before = (list(g.wall), [list(p.concealed) for p in g.players], list(g.discards),
              g.phase, list(g.me.concealed))
    simulate(g, candidate_actions(g), playouts=10, rng=random.Random(1))
    after = (list(g.wall), [list(p.concealed) for p in g.players], list(g.discards),
             g.phase, list(g.me.concealed))
    assert before == after


def test_world_is_played_to_the_end():
    g = Game(random.Random(4))
    world = g.determinize(random.Random(1))
    apply_action(world, candidate_actions(g)[0])
    assert world.phase in (Game.WON, Game.DRAWN)


# ---------- estimates ----------

def test_outcomes_add_up_to_one():
    g = Game(random.Random(4))
    done, results = simulate(g, candidate_actions(g), playouts=25, rng=random.Random(1))
    assert done == 25
    for row in results:
        assert row["you"] + row["bots"] + row["draw"] == pytest.approx(1)


def test_simulation_is_repeatable_with_a_seed():
    g = Game(random.Random(4))
    first = simulate(g, candidate_actions(g), playouts=20, rng=random.Random(5))
    second = simulate(g, candidate_actions(g), playouts=20, rng=random.Random(5))
    assert first == second


def test_a_ready_hand_wins_more_often_than_a_scattered_one():
    ready = game_with_my_hand(READY_13 + ["9-characters"])
    scattered = game_with_my_hand(JUNK_13 + ["9-characters"])
    _, ready_rows = simulate(ready, [{"action": "discard", "tiles": ["9-characters"]}],
                             playouts=120, rng=random.Random(3))
    _, scattered_rows = simulate(scattered, [{"action": "discard", "tiles": ["9-characters"]}],
                                 playouts=120, rng=random.Random(3))
    assert ready_rows[0]["you"] > scattered_rows[0]["you"] + 0.15


def test_time_limit_stops_early_but_always_does_at_least_one_playout():
    g = Game(random.Random(4))
    done, _ = simulate(g, candidate_actions(g), playouts=10 ** 6, rng=random.Random(1), seconds=0.05)
    assert 1 <= done < 10 ** 6


# ---------- which choices get simulated ----------

def test_discard_candidates_come_from_the_best_options():
    g = Game(random.Random(4))
    actions = candidate_actions(g)
    assert 1 <= len(actions) <= 4
    assert all(a["action"] == "discard" and a["tiles"][0] in g.me.concealed for a in actions)
    assert actions[0]["tiles"][0] == g.analysis()["options"][0]["discard"]


def test_no_decision_when_you_can_simply_win():
    g = Game(random.Random(4))
    g.me.concealed = READY_13 + ["2-circles"]
    assert candidate_actions(g) == []


def natural_claim_game():
    """Play seeded games (discarding the bot-AI's choice for you) until a pong/chi offer appears."""
    from bots import choose_discard
    for seed in range(300):
        g = Game(random.Random(seed))
        for _ in range(20):
            if g.phase == Game.CLAIM and not g.offer["win"]:
                return g
            if g.phase != Game.PLAYING or g.can_declare_win():
                break
            g.discard(choose_discard(g.me.concealed, len(g.me.melds)))
    raise AssertionError("no claim situation found")


def test_claim_candidates_are_pass_plus_each_legal_claim():
    g = natural_claim_game()
    actions = candidate_actions(g)
    assert actions[0]["action"] == "pass"
    assert len(actions) == 1 + g.offer["pong"] + len(g.offer["chi"])


def test_simulating_a_claim_choice_runs():
    g = natural_claim_game()
    actions = candidate_actions(g)
    done, rows = simulate(g, actions, playouts=20, rng=random.Random(2))
    assert done == 20 and [r["action"] for r in rows] == [a["action"] for a in actions]


def test_every_claim_choice_is_played_to_a_finish():
    """Regression: claiming in a simulated world must carry on to the end of the game."""
    g = natural_claim_game()
    for action in candidate_actions(g):
        world = g.determinize(random.Random(3))
        apply_action(world, action)
        assert world.phase in (Game.WON, Game.DRAWN), action
    done, rows = simulate(g, candidate_actions(g), playouts=30, rng=random.Random(2))
    assert all(r["you"] + r["bots"] + r["draw"] == pytest.approx(1) for r in rows)
    assert all(r["draw"] < 1 for r in rows)              # somebody usually wins
