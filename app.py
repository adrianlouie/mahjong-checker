"""The web layer: a thin Flask app around game.Game.

The browser never decides anything. It asks the server for the game state
(JSON), draws it, and sends back what you clicked (discard / win / pass).
All of the mahjong logic stays in game.py, checker.py and probability.py.

NOTE: one Game is kept in memory, so this is a single-player local app.

Run it with:   python app.py     then open http://localhost:5000
"""

import random

from flask import Flask, jsonify, render_template, request

from game import Game
from probability import estimate_ready_rate, estimate_win_rate, shanten_distribution
from tiles import all_tile_types, tile_symbol

MAX_STATS_TRIALS = 50_000


def create_app(seed=None):
    """Build the Flask app. `seed` makes the dealing repeatable (used by tests)."""
    app = Flask(__name__)
    app.config["rng"] = random.Random(seed)
    app.config["game"] = None
    symbols = {tile: tile_symbol(tile) for tile in all_tile_types()}

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
    def new_game():
        app.config["game"] = Game(app.config["rng"])
        return state_response()

    @app.get("/api/state")
    def state():
        return state_response()

    @app.post("/api/discard")
    def discard():
        tile = (request.get_json(silent=True) or {}).get("tile")
        current_game().discard(tile)
        return state_response()

    @app.post("/api/win")
    def win():
        current_game().declare_win()
        return state_response()

    @app.post("/api/pass")
    def pass_claim():
        current_game().pass_claim()
        return state_response()

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
