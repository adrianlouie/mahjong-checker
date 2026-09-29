import pytest

from app import create_app
from helpers import hand

READY_13 = hand("1b 2b 3b 4b 5b 6b 7c 8c 9c 5k 5k 3c 4c")


@pytest.fixture
def client():
    app = create_app(seed=7)
    app.testing = True
    return app.test_client()


def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Mahjong" in response.data


def test_new_game_returns_a_14_tile_hand(client):
    state = client.post("/api/new").get_json()
    assert state["phase"] == "playing"
    assert len(state["hand"]) == 14
    assert len(state["symbols"]) == 34
    assert state["analysis"]["options"]


def test_state_matches_new_game(client):
    created = client.post("/api/new").get_json()
    assert client.get("/api/state").get_json()["hand"] == created["hand"]


def test_discard_advances_the_game(client):
    state = client.post("/api/new").get_json()
    tile = state["hand"][0]
    after = client.post("/api/discard", json={"tile": tile}).get_json()
    assert after["round"] == 2
    assert len(after["hand"]) == 14
    assert len(after["history"]) >= 2


def test_discarding_a_tile_you_do_not_have_is_a_400(client):
    client.post("/api/new")
    response = client.post("/api/discard", json={"tile": "not-a-tile"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_discard_without_body_is_a_400(client):
    client.post("/api/new")
    assert client.post("/api/discard").status_code == 400


def test_win_with_a_losing_hand_is_a_400(client):
    client.post("/api/new")
    assert client.post("/api/win").status_code == 400


def test_pass_when_nothing_is_on_offer_is_a_400(client):
    client.post("/api/new")
    assert client.post("/api/pass").status_code == 400


def test_win_flow_through_the_api():
    app = create_app(seed=7)
    app.testing = True
    client = app.test_client()
    client.post("/api/new")
    app.config["game"].players[0].concealed = READY_13 + ["2-circles"]   # rig a winning hand
    state = client.get("/api/state").get_json()
    assert state["can_declare_win"] is True
    won = client.post("/api/win").get_json()
    assert won["phase"] == "won" and won["winner"] == 0


def test_stats_endpoint(client):
    data = client.get("/api/stats?trials=500").get_json()
    assert data["trials"] == 500
    assert 0 <= data["win_rate_14_tiles"] < 0.01
    assert sum(data["shanten_distribution_13_tiles"].values()) == pytest.approx(1)


def test_stats_trials_are_capped(client, monkeypatch):
    monkeypatch.setattr("app.MAX_STATS_TRIALS", 200)
    assert client.get("/api/stats?trials=99999999").get_json()["trials"] == 200


def offer_setup(app, client, me, tile, src):
    """Rig the running game so that player `src` has just thrown `tile`."""
    client.post("/api/new")
    game = app.config["game"]
    junk = hand("1b 4b 7b 1c 4c 7c 1k 4k 7k E S W N")
    game.players[0].concealed = list(me)
    for bot in game.players[1:]:
        bot.concealed = list(junk)
    game.discards.append((tile, src))
    game.phase, game.next = game.RUNNING, ("resolve", tile, src, False)
    game._run()


def test_claim_pong_through_the_api():
    app = create_app(seed=7)
    app.testing = True
    client = app.test_client()
    offer_setup(app, client, READY_13, "5-characters", 2)
    state = client.get("/api/state").get_json()
    assert state["phase"] == "claim" and state["offer"]["pong"] is True
    assert {c["action"] for c in state["analysis"]["claims"]} == {"pass", "pong"}
    after = client.post("/api/claim", json={"kind": "pong"}).get_json()
    assert after["phase"] == "playing"
    assert after["melds"][0]["type"] == "pong"
    assert len(after["hand"]) == 11


def test_claim_chi_through_the_api():
    app = create_app(seed=7)
    app.testing = True
    client = app.test_client()
    offer_setup(app, client, hand("2b 3b 5b 6b R G P E S W N 9c 9k"), "4-bamboo", 3)
    after = client.post("/api/claim", json={"kind": "chi",
                                            "tiles": ["3-bamboo", "5-bamboo"]}).get_json()
    assert after["melds"][0]["tiles"] == ["3-bamboo", "4-bamboo", "5-bamboo"]


def test_bad_claim_is_a_400(client):
    client.post("/api/new")
    assert client.post("/api/claim", json={"kind": "pong"}).status_code == 400


def test_pass_through_the_api():
    app = create_app(seed=7)
    app.testing = True
    client = app.test_client()
    offer_setup(app, client, READY_13, "5-characters", 2)
    after = client.post("/api/pass").get_json()
    assert after["phase"] in ("playing", "claim", "won", "drawn")
    assert after["melds"] == []


# ---------- simulated odds ----------

def test_odds_for_a_discard_decision(client):
    client.post("/api/new")
    data = client.get("/api/odds?n=15&seconds=5").get_json()
    assert data["kind"] == "discard"
    assert data["playouts"] == 15
    assert 1 <= len(data["options"]) <= 4
    for row in data["options"]:
        assert row["you"] + row["bots"] + row["draw"] == pytest.approx(1)
        assert row["action"] == "discard"


def test_odds_do_not_change_the_game(client):
    before = client.post("/api/new").get_json()
    client.get("/api/odds?n=10&seconds=5")
    after = client.get("/api/state").get_json()
    assert before["hand"] == after["hand"] and before["wall_count"] == after["wall_count"]


def test_odds_for_a_claim_decision():
    app = create_app(seed=7)
    app.testing = True
    client = app.test_client()
    offer_setup(app, client, READY_13, "5-characters", 2)
    data = client.get("/api/odds?n=10&seconds=5").get_json()
    assert data["kind"] == "claim"
    assert [r["action"] for r in data["options"]] == ["pass", "pong"]


def test_no_odds_when_the_game_is_over():
    app = create_app(seed=7)
    app.testing = True
    client = app.test_client()
    client.post("/api/new")
    app.config["game"].players[0].concealed = READY_13 + ["2-circles"]
    client.post("/api/win")
    assert client.get("/api/odds?n=5").get_json()["kind"] == "none"


def test_odds_request_size_is_capped(client, monkeypatch):
    monkeypatch.setattr("app.MAX_PLAYOUTS", 7)
    client.post("/api/new")
    assert client.get("/api/odds?n=100000&seconds=5").get_json()["playouts"] == 7
