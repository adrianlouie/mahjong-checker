"""The web layer: a thin Flask app around game.Game.

The browser never decides anything. It asks the server for the game state
(JSON), draws it, and sends back what you clicked (discard / win / pass).
All of the mahjong logic stays in game.py, checker.py and probability.py.

NOTE: one Game is kept in memory, so this is a single-player local app.

Run it with:   python app.py     then open http://localhost:5000
"""

import functools
import random
import threading

from flask import Flask, jsonify, render_template, request

from game import Game
from probability import estimate_ready_rate, estimate_win_rate, shanten_distribution
from simulation import DEFAULT_PLAYOUTS, candidate_actions, simulate
from tiles import all_tile_types, tile_symbol

MAX_STATS_TRIALS = 50_000
MAX_PLAYOUTS = 1000
MAX_ODDS_SECONDS = 8.0


def create_app(seed=None):
    """Build the Flask app. `seed` makes the dealing repeatable (used by tests)."""
    app = Flask(__name__)
    app.config["rng"] = random.Random(seed)
    app.config["game"] = None
    symbols = {tile: tile_symbol(tile) for tile in all_tile_types()}
    lock = threading.Lock()   # the server handles requests on several threads

    def locked(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            with lock:
                return view(*args, **kwargs)
        return wrapper

    def current_game():
        if app.config["game"] is None:
            app.config["game"] = Game(app.config["rng"])
        return app.config["game"]

    def state_response():
        state = current_game().to_dict()
        state["symbols"] = symbols
        return jsonify(state)

    @app.errorhandler(ValueError)
    def bad_request(error):
        return jsonify({"error": str(error)}), 400

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/new")
    @locked
    def new_game():
        app.config["game"] = Game(app.config["rng"])
        return state_response()

    @app.get("/api/state")
    @locked
    def state():
        return state_response()

    @app.post("/api/discard")
    @locked
    def discard():
        tile = (request.get_json(silent=True) or {}).get("tile")
        current_game().discard(tile)
        return state_response()

    @app.post("/api/win")
    @locked
    def win():
        current_game().declare_win()
        return state_response()

    @app.post("/api/claim")
    @locked
    def claim():
        body = request.get_json(silent=True) or {}
        current_game().claim(body.get("kind"), body.get("tiles"))
        return state_response()

    @app.post("/api/pass")
    @locked
    def pass_claim():
        current_game().pass_claim()
        return state_response()

    @app.get("/api/odds")
    def odds():
        """Simulated win chances for the choice you are facing right now.

        Slow (about 2 seconds), so the page asks for it separately from /api/state.
        """
        playouts = max(1, min(request.args.get("n", DEFAULT_PLAYOUTS, type=int), MAX_PLAYOUTS))
        seconds = max(0.0, min(request.args.get("seconds", 2.5, type=float), MAX_ODDS_SECONDS))
        with lock:                                   # copy the game, then let go of the lock
            game = current_game()
            snapshot = game.clone()
            snapshot.history = []
        actions = candidate_actions(snapshot)
        if not actions:
            return jsonify({"kind": "none", "playouts": 0, "options": []})
        done, results = simulate(snapshot, actions, playouts, random.Random(), seconds)
        kind = "claim" if snapshot.phase == Game.CLAIM else "discard"
        return jsonify({"kind": kind, "playouts": done, "options": results})

    @app.get("/api/stats")
    def stats():
        trials = min(request.args.get("trials", 5000, type=int), MAX_STATS_TRIALS)
        trials = max(trials, 1)
        rng = random.Random()
        return jsonify({
            "trials": trials,
            "win_rate_14_tiles": estimate_win_rate(trials, rng),
            "ready_rate_13_tiles": estimate_ready_rate(max(trials // 5, 1), rng),
            "shanten_distribution_13_tiles": shanten_distribution(trials // 5 or 1, 13, rng),
        })

    return app


if __name__ == "__main__":
    create_app().run(debug=False)
