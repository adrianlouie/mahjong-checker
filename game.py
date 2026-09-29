"""Day 4: the solitaire game engine (no web code in here).

You play against 3 simple bots. Each round:
    1. you draw a tile        (you now hold 14)
    2. you discard one tile   (back to 13)
    3. each bot draws a tile and discards one at random
You win if your 14 tiles form 4 sets + a pair:
    - on your own draw, or
    - on ANY bot's discard (in Hong Kong mahjong you can win off a discard).

The bots are deliberately dumb: they never try to win and never claim tiles.
They just make discards appear, so you have tiles to win on.

The game only knows about tiles and turns. game.py never touches Flask;
app.py is the thin layer that turns a Game into JSON for the web page.
"""

import random

from checker import is_winning_hand
from probability import analyse_hand, discard_options, unseen_counts
from tiles import build_full_set, sorted_hand

BOT_NAMES = ["Bot 1", "Bot 2", "Bot 3"]
LOOKS_PER_ROUND = 4   # my own draw + the 3 bot discards


class Game:
    # phase values
    PLAYING = "playing"   # your turn: you hold 14 tiles and must discard (or win)
    CLAIM = "claim"       # a bot discarded a tile that completes your hand
    WON = "won"
    DRAWN = "drawn"       # the wall ran out with nobody winning

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.wall = build_full_set()
        self.rng.shuffle(self.wall)
        self.hand = [self.wall.pop() for _ in range(13)]
        self.bots = [[self.wall.pop() for _ in range(13)] for _ in BOT_NAMES]
        self.discards = []          # list of (tile, who) in the order they were thrown
        self.log = []               # short messages shown on the page
        self.offered = None         # (tile, who) waiting for you to win or pass
        self.next_bot = 0           # which bot acts next (used when resuming after a pass)
        self.drawn_tile = None
        self.history = []           # one entry per turn, so the UI can chart your chances
        self.round = 0
        self.phase = self.PLAYING
        self._my_draw()

    # ------------------------------------------------------------------
    # your actions
    # ------------------------------------------------------------------

    def discard(self, tile):
        """Throw away one tile from your 14, then let the bots play."""
        self._require_phase(self.PLAYING)
        if tile not in self.hand:
            raise ValueError(f"you don't have {tile}")
        self.hand.remove(tile)
        self.drawn_tile = None
        self.discards.append((tile, "You"))
        self.log.append(f"You discarded {tile}")
        self.next_bot = 0
        self._run_bots()

    def declare_win(self):
        """Win on your own draw (14 tiles) or on the bot discard on offer."""
        if self.phase == self.PLAYING:
            if not is_winning_hand(self.hand):
                raise ValueError("that hand is not a winning hand")
            self.log.append("You win by self-draw!")
        elif self.phase == self.CLAIM:
            tile, who = self.offered
            self.hand.append(tile)
            self.log.append(f"You win on {who}'s {tile}!")
        else:
            raise ValueError("the game is over")
        self.phase = self.WON

    def pass_claim(self):
        """Decline to win on the offered discard; the bots carry on."""
        self._require_phase(self.CLAIM)
        tile, who = self.offered
        self.log.append(f"You passed on {who}'s {tile}")
        self.discards.append((tile, who))
        self.offered = None
        self.phase = self.PLAYING   # (temporary: _run_bots sets the real phase)
        self._run_bots()

    # ------------------------------------------------------------------
    # turn flow
    # ------------------------------------------------------------------

    def _my_draw(self):
        if not self.wall:
            self._end_drawn()
            return
        self.drawn_tile = self.wall.pop()
        self.hand.append(self.drawn_tile)
        self.round += 1
        self.phase = self.PLAYING
        self._record_history()

    def _run_bots(self):
        """Let bots next_bot..2 draw and discard; stop early if you can win."""
        while self.next_bot < len(self.bots):
            index = self.next_bot
            self.next_bot += 1
            if not self.wall:
                self._end_drawn()
                return
            bot = self.bots[index]
            bot.append(self.wall.pop())
            thrown = bot.pop(self.rng.randrange(len(bot)))
            who = BOT_NAMES[index]
            self.log.append(f"{who} discarded {thrown}")
            if is_winning_hand(self.hand + [thrown]):
                self.offered = (thrown, who)
                self.phase = self.CLAIM
                self._record_history()
                return
            self.discards.append((thrown, who))
        self._my_draw()

    def _end_drawn(self):
        self.phase = self.DRAWN
        self.log.append("The wall is empty - nobody wins.")

    def _require_phase(self, phase):
        if self.phase != phase:
            raise ValueError(f"not allowed right now (phase is {self.phase})")

    # ------------------------------------------------------------------
    # what the page needs to know
    # ------------------------------------------------------------------

    def _discarded_tiles(self):
        return [tile for tile, _ in self.discards]

    def _looks(self):
        return min(LOOKS_PER_ROUND, len(self.wall)), len(self.wall)

    def analysis(self):
        """Shanten, waits and probabilities for the current situation."""
        next_round, rest = self._looks()
        if self.phase == self.PLAYING:
            unseen = unseen_counts(self.hand, self._discarded_tiles())
            return {"options": discard_options(self.hand, unseen, next_round, rest)}
        if self.phase == self.CLAIM:
            unseen = unseen_counts(self.hand, self._discarded_tiles() + [self.offered[0]])
            return {"current": analyse_hand(self.hand, unseen, next_round, rest)}
        return {}

    def _record_history(self):
        """Save the best chance available this turn (used for the chart)."""
        if self.phase == self.PLAYING:
            best = self.analysis()["options"][0]
        else:
            best = analyse_hand(self.hand, unseen_counts(
                self.hand, self._discarded_tiles() + [self.offered[0]]), *self._looks())
        self.history.append({
            "round": self.round,
            "shanten": best["shanten"],
            "chance_next_round": best["chance_next_round"],
        })

    def can_declare_win(self):
        return self.phase == self.PLAYING and is_winning_hand(self.hand)

    def to_dict(self):
        return {
            "phase": self.phase,
            "hand": sorted_hand(self.hand),
            "drawn_tile": self.drawn_tile,
            "offered": None if self.offered is None else
                       {"tile": self.offered[0], "who": self.offered[1]},
            "can_declare_win": self.can_declare_win(),
            "discards": [{"tile": t, "who": w} for t, w in self.discards],
            "wall_count": len(self.wall),
            "round": self.round,
            "log": self.log[-12:],
            "analysis": self.analysis(),
            "history": self.history,
        }
