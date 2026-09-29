"""Monte Carlo win chances: "replay the rest of the game thousands of times".

The analytic numbers in probability.py answer "how likely am I to SEE a
helpful tile?". They can't say what bots winning first, or stealing tiles by
calling pong/chi, does to you. Simulation can:

    1. Take the current game. You know your hand, all discards and all melds.
    2. Randomly deal the tiles you can't see to the three bots and the wall
       (Game.determinize) - one possible "world".
    3. Make your choice in that world (discard X / pong / pass ...).
    4. Play the rest of the game with the bot AI in every seat, INCLUDING yours.
    5. Record who won. Repeat with a fresh random world.

The share of worlds you win is the estimate. Every option is tried in the SAME
worlds, so comparing options is fair (less noise than separate random runs).

Simplifications (also in the README): after this choice, the sim plays you like
a bot; bots' past discards are not used to guess their hands.
"""

import random
import time
from collections import Counter

from game import Game

DEFAULT_PLAYOUTS = 300
MAX_OPTIONS = 4


def candidate_actions(game, max_discards=MAX_OPTIONS):
    """The choices worth simulating right now, as dicts {action, tiles}.

    Discards are the analytic top few (lowest distance first); claims are every
    legal option. Returns [] when there is no real decision (you can just win).
    """
    if game.phase == Game.PLAYING:
        if game.can_declare_win():
            return []
        rows = game.analysis()["options"][:max_discards]
        return [{"action": "discard", "tiles": [row["discard"]]} for row in rows]
    if game.phase == Game.CLAIM and not game.offer["win"]:
        actions = [{"action": "pass", "tiles": []}]
        if game.offer["pong"]:
            actions.append({"action": "pong", "tiles": []})
        actions += [{"action": "chi", "tiles": list(pair)} for pair in game.offer["chi"]]
        return actions
    return []


def apply_action(world, action):
    """Make `action` in a (copied) world, then let the game play itself out."""
    kind, tiles = action["action"], action["tiles"]
    if kind == "discard":
        world.discard(tiles[0])
    elif kind == "pass":
        world.pass_claim()
    else:
        world.claim(kind, tiles)
    return world.winner        # a seat number, or None if the wall ran out


def simulate(game, actions, playouts=DEFAULT_PLAYOUTS, rng=None, seconds=None):
    """Estimate the outcome of each action. Returns (playouts_done, results).

    `results` is one dict per action: the action itself plus the share of
    simulated games where you won ("you"), a bot won ("bots") or nobody did
    ("draw"). Stops early after `seconds` if given.
    """
    rng = rng or random.Random()
    tallies = [Counter() for _ in actions]
    deadline = None if seconds is None else time.monotonic() + seconds
    done = 0
    while done < playouts and (deadline is None or done == 0 or time.monotonic() < deadline):
        base = game.determinize(rng)
        for tally, action in zip(tallies, actions):
            winner = apply_action(base.clone(), action)
            tally["draw" if winner is None else "you" if winner == 0 else "bots"] += 1
        done += 1
    results = [{**action,
                "you": tally["you"] / done, "bots": tally["bots"] / done,
                "draw": tally["draw"] / done}
               for action, tally in zip(actions, tallies)]
    return done, results
