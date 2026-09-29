"""The game engine (no web code in here).

Four players sit in a circle: you (seat 0) and three bots (seats 1-3). Turn
order is 0 -> 1 -> 2 -> 3 -> 0. On a turn a player draws a tile and discards
one. After every discard, the other players get a chance to WIN on it.

The engine is a small state machine (`self.next`) driven by `_run()`:
    ("draw", seat)                    that seat draws a tile
    ("discard", seat)                 that bot chooses a tile to throw
    ("resolve", tile, src, passed)    the tile `src` just threw: does anyone claim it?
`_run()` keeps stepping until it needs YOU to decide something (or the game
ends), then returns. Your actions (discard / win / pass) set up the next step
and call `_run()` again.

game.py never touches Flask; app.py is the thin layer that turns a Game into
JSON for the web page.
"""

import random

from bots import choose_discard
from checker import is_winning_hand
from probability import analyse_hand, discard_options, unseen_counts
from tiles import build_full_set, sorted_hand

NAMES = ["You", "Bot 1", "Bot 2", "Bot 3"]
LOOKS_PER_ROUND = 4   # my own draw + the 3 bot discards


class Player:
    def __init__(self, name, concealed):
        self.name = name
        self.concealed = concealed   # tiles in hand, hidden from the others
        self.melds = []              # claimed sets on the table (added with pong/chi)

    def meld_tiles(self):
        return [tile for meld in self.melds for tile in meld["tiles"]]


class Game:
    # phase values
    PLAYING = "playing"   # your turn: you must discard (or declare a win)
    CLAIM = "claim"       # someone discarded a tile you may claim
    RUNNING = "running"   # the engine is working (never visible from outside)
    WON = "won"
    DRAWN = "drawn"       # the wall ran out with nobody winning

    def __init__(self, rng=None, auto=False):
        """`auto=True` makes seat 0 play like a bot too (used by simulations)."""
        self.rng = rng or random.Random()
        self.auto = auto
        self.wall = build_full_set()
        self.rng.shuffle(self.wall)
        self.players = [Player(name, [self.wall.pop() for _ in range(13)]) for name in NAMES]
        self.discards = []          # (tile, seat) in the order they were thrown
        self.log = []
        self.offer = None           # what you may claim right now (phase CLAIM)
        self.drawn_tile = None
        self.history = []           # one entry per turn, so the UI can chart your progress
        self.round = 0
        self.winner = None          # seat of the winner
        self.win_kind = None        # "self-draw" or "discard"
        self.phase = self.RUNNING
        self.next = ("draw", 0)
        self._run()

    # ------------------------------------------------------------------
    # your actions
    # ------------------------------------------------------------------

    @property
    def me(self):
        return self.players[0]

    def discard(self, tile):
        """Throw away one tile, then let the game carry on."""
        self._require_phase(self.PLAYING)
        if tile not in self.me.concealed:
            raise ValueError(f"you don't have {tile}")
        self.drawn_tile = None
        self._throw(0, tile)
        self.phase = self.RUNNING
        self.next = ("resolve", tile, 0, False)
        self._run()

    def declare_win(self):
        """Win on your own draw, or on the discard on offer."""
        if self.phase == self.PLAYING:
            if not is_winning_hand(self.me.concealed):
                raise ValueError("that hand is not a winning hand")
            self._win(0, "self-draw")
        elif self.phase == self.CLAIM and self.offer["win"]:
            self._win(0, "discard", self.offer["tile"], self.offer["from"])
        else:
            raise ValueError("you can't win right now")

    def pass_claim(self):
        """Decline the offered tile; the game carries on without you claiming it."""
        self._require_phase(self.CLAIM)
        tile, src = self.offer["tile"], self.offer["from"]
        self._log(f"You passed on {NAMES[src]}'s {tile}")
        self.offer = None
        self.phase = self.RUNNING
        self.next = ("resolve", tile, src, True)
        self._run()

    # ------------------------------------------------------------------
    # the state machine
    # ------------------------------------------------------------------

    def _run(self):
        """Step the game until it needs a decision from you, or it ends."""
        while True:
            step = self.next
            kind = step[0]
            if kind == "draw":
                if self._draw(step[1]):
                    return
            elif kind == "discard":
                seat = step[1]
                player = self.players[seat]
                self._throw(seat, choose_discard(player.concealed, len(player.melds)))
                self.next = ("resolve", self.discards[-1][0], seat, False)
            elif kind == "resolve":
                if self._resolve(*step[1:]):
                    return

    def _draw(self, seat):
        """Give `seat` a tile. Returns True if the engine must stop."""
        if not self.wall:
            self._end_drawn()
            return True
        player = self.players[seat]
        tile = self.wall.pop()
        player.concealed.append(tile)
        if seat == 0 and not self.auto:
            self.drawn_tile = tile
            self.round += 1
            self.phase = self.PLAYING
            self._record_history()
            return True
        if is_winning_hand(player.concealed):
            self._win(seat, "self-draw")
            return True
        self.next = ("discard", seat)
        return False

    def _resolve(self, tile, src, passed):
        """Decide what happens to the tile `src` just threw. True = engine must stop."""
        order = [(src + step) % 4 for step in (1, 2, 3)]

        # 1. Winning beats everything. The first player after the thrower who can win gets it.
        for seat in order:
            if not is_winning_hand(self.players[seat].concealed + [tile]):
                continue
            if seat == 0 and not self.auto:
                if passed:
                    continue
                self._make_offer(tile, src, win=True)
                return True
            self._win(seat, "discard", tile, src)
            return True

        # 2. Nobody wants it: the next player in turn order draws.
        self.next = ("draw", (src + 1) % 4)
        return False

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _throw(self, seat, tile):
        self.players[seat].concealed.remove(tile)
        self.discards.append((tile, seat))
        self._log(f"{NAMES[seat]} discarded {tile}")

    def _make_offer(self, tile, src, win=False, pong=False, chi=()):
        self.offer = {"tile": tile, "from": src, "win": win, "pong": pong, "chi": list(chi)}
        self.phase = self.CLAIM
        self._record_history()

    def _win(self, seat, kind, tile=None, src=None):
        if tile is not None:
            self.discards.pop()                    # the winning tile leaves the discard pile
            self.players[seat].concealed.append(tile)
        self.winner, self.win_kind = seat, kind
        self.phase = self.WON
        self.offer = None
        source = f" on {NAMES[src]}'s {tile}" if tile else " by self-draw"
        self._log(f"{NAMES[seat]} win{'s' if seat else ''}{source}!")

    def _end_drawn(self):
        self.phase = self.DRAWN
        self._log("The wall is empty - nobody wins.")

    def _require_phase(self, phase):
        if self.phase != phase:
            raise ValueError(f"not allowed right now (phase is {self.phase})")

    def _log(self, message):
        if not self.auto:
            self.log.append(message)

    # ------------------------------------------------------------------
    # what the page needs to know
    # ------------------------------------------------------------------

    def _all_meld_tiles(self):
        return [tile for player in self.players for tile in player.meld_tiles()]

    def _unseen(self):
        return unseen_counts(self.me.concealed, [t for t, _ in self.discards],
                             self._all_meld_tiles())

    def _looks(self):
        return min(LOOKS_PER_ROUND, len(self.wall)), len(self.wall)

    def analysis(self):
        """Distance, helpful tiles and probabilities for the current situation."""
        next_round, rest = self._looks()
        melds = len(self.me.melds)
        if self.phase == self.PLAYING:
            return {"options": discard_options(self.me.concealed, self._unseen(),
                                               next_round, rest, melds)}
        if self.phase == self.CLAIM:
            return {"current": analyse_hand(self.me.concealed, self._unseen(),
                                            next_round, rest, melds)}
        return {}

    def _record_history(self):
        """Save this turn's best distance (used for the chart)."""
        if self.auto:
            return
        analysis = self.analysis()
        best = analysis["options"][0] if "options" in analysis else analysis["current"]
        self.history.append({
            "round": self.round,
            "shanten": best["shanten"],
            "chance_next_round": best["chance_next_round"],
        })

    def can_declare_win(self):
        return (self.phase == self.PLAYING and is_winning_hand(self.me.concealed)) or \
               (self.phase == self.CLAIM and self.offer["win"])

    def to_dict(self):
        reveal = self.phase in (self.WON, self.DRAWN)
        return {
            "phase": self.phase,
            "winner": self.winner,
            "winner_name": None if self.winner is None else NAMES[self.winner],
            "win_kind": self.win_kind,
            "hand": sorted_hand(self.me.concealed),
            "melds": self.me.melds,
            "drawn_tile": self.drawn_tile,
            "offer": None if self.offer is None else
                     {**self.offer, "from_name": NAMES[self.offer["from"]]},
            "can_declare_win": self.can_declare_win(),
            "others": [{
                "name": p.name,
                "concealed_count": len(p.concealed),
                "melds": p.melds,
                "hand": sorted_hand(p.concealed) if reveal else None,
            } for p in self.players[1:]],
            "discards": [{"tile": t, "who": NAMES[s]} for t, s in self.discards],
            "wall_count": len(self.wall),
            "round": self.round,
            "log": self.log[-12:],
            "analysis": self.analysis(),
            "history": self.history,
        }
