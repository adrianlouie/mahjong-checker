# Mahjong Odds

A Hong Kong–style mahjong game that shows your **winning chances as you play**. You play against three bots that try to win too. You can **pong** and **chi**, and after every move the page tells you how far your hand is from winning, which tiles would help, and your **simulated chance of winning** (with the bots racing you).

Built as a first-year CS project. The interesting parts are the algorithm that decides whether a hand is a winning hand (a **recursive backtracking search**), and a **Monte Carlo simulation** that replays the rest of the game thousands of times to estimate your chances.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python app.py            # then open http://localhost:5000
pytest                   # run the tests
python stats.py          # Monte Carlo statistics (see below)
```

## How the game works

- 136 tiles: 3 suits (bamboo, circles, characters) × 1–9 × 4 copies, 4 winds × 4, 3 dragons × 4. (Real Hong Kong sets also have 8 flower tiles; flowers are bonus tiles that never sit in your hand, so they're left out.)
- Four players sit in a circle: **you, Bot 1, Bot 2, Bot 3**. You start with 13 tiles. On a turn a player **draws** a tile, then **discards** one.
- You win when your hand is **4 sets + 1 pair**, either on your own draw or on **any player's discard** (in Hong Kong mahjong you can win off a discard).
- A **set** is a triplet (three identical tiles) or a run (three consecutive numbers in the *same* suit, e.g. 3-4-5 bamboo). Winds and dragons can't form runs, and runs don't wrap around (8-9-1 is not a run).

### Claiming a discard (pong and chi)

After any discard, players can claim it. Priority:

1. **Win**: any player can win on any discard. If several can, the one closest after the thrower gets it.
2. **Pong** (碰): any player who holds two matching tiles can take the discard to make a triplet.
3. **Chi** (上): the **next player in turn order only** (the real rule) can take the discard to make a run. For you, that means only **Bot 3's** discards can be chied.

A claim creates a **meld**: a face-up set that stays on the table. The claimer then discards (skipping the players in between). If nobody claims, the next player draws. If you pass on a chance to win, you can't claim that same tile.

Because melds are already-finished sets, a hand with melds needs fewer concealed tiles: 14 with no melds, 11 with one, 8 with two, and so on. That's why `is_winning_hand` accepts any tile count that is 3k + 2.

### The bots (`bots.py`)

Simple, and built from pieces you already know:

- They **win** whenever they can (with the same checker you use).
- They **discard** the tile that leaves their hand closest to winning (lowest "distance", see below). If tied, they keep tiles that have pairs or neighbours.
- They **claim** a pong or chi only if it brings them strictly closer to winning.

They don't read your discards, defend, or plan. They still play much better than random discards.

## The core algorithm: is this a winning hand? (`checker.py`)

We can't just look at a hand and know how to split it up, so we **try**.

1. **Choose the pair.** Try every tile that appears at least twice as "the pair". Remove those two tiles.
2. **Split the remaining 12 tiles into 4 sets** using recursion:
   - If no tiles are left → success.
   - Otherwise take the **smallest** tile still in the hand. Any set containing it must be either a triplet of it, or a run *starting* at it (nothing smaller is left). So there are at most two options.
   - Try an option: remove those tiles and **recurse** on the smaller hand.
   - If the recursion fails, **put the tiles back (backtrack)** and try the other option.
   - If both options fail → this hand can't be split, return failure to the caller.
3. If no choice of pair leads to success, it's not a winning hand.

The hand is stored as a `Counter` (`{tile: count}`), so "remove a run" is three `-= 1`s and "undo" is three `+= 1`s. With melds on the table you pass only the concealed tiles: the count is 3k + 2, and the same algorithm applies (one pair plus k sets).

### Worked example

Hand (14 tiles, no melds): `4-5-6 bamboo, 1-2-3 circles, 5 6 6 7 7 8 characters, white-dragon ×2`

| Pair tried | Left to split into 4 sets | Result |
|---|---|---|
| 6-characters | 456b, 123c, 5k 7k 7k 8k, 白 白 | 5k can't start a run (no 6k left) → **fail, undo** |
| 7-characters | 456b, 123c, 5k 6k 6k 8k, 白 白 | 5k-6k-7k needs a 7k → **fail, undo** |
| white-dragon | 456b, 123c, 5k 6k 6k 7k 7k 8k | 5-6-7k then 6-7-8k → **success** |

The first two attempts are exactly the "try, fail, undo" part of backtracking. (This hand is a test: `test_first_pair_choice_can_be_wrong`.)

### Two honest notes

- **Where the guessing really happens.** Inside the set-splitting step, taking a triplet whenever there are 3+ copies of the smallest tile is always safe (three runs starting at the same tile can always be rearranged into a triplet plus other runs). I checked this by brute force on small hands and found no counterexample. So most of the real trial-and-error is in *choosing the pair*. The code still has both branches because they're the clear way to explain the search.
- **Speed.** The recursion is tiny: at most about 7 candidate pairs, then a chain of at most 4 set removals with 2 options each. That's why we can test hundreds of thousands of random hands in seconds.

## Winning chances (`probability.py`)

**Ready hand ("ting pai", or *tenpai* in Japanese):** 13 tiles that one more tile would complete. `winning_tiles` finds the completing tiles by brute force: try all 34 tile types as the 14th tile and ask the checker. It skips a type if you already hold all 4 copies (a 5th can't exist).

**Distance from winning ("shanten"):** a fresh hand is usually 3–4 tiles from ready, and if we only reported "0% until ready" the game would feel dead. So we compute how far each hand is: −1 = winning, 0 = ready, 1 = one step from ready, and so on. It's another recursive search: split the hand into sets (2 points each), partial sets like a pair or `4-5` (1 point), and the pair (1 point), and keep the best split. `distance = 8 − 2·sets − partials − pair`. Melds on the table count as finished sets. Tests confirm distance 0 exactly matches "has a winning tile" and distance −1 exactly matches the checker on hundreds of near-winning hands.

**Speed.** The bots and the simulation call this thousands of times per second, so each suit is solved separately and the answer is remembered (cached), then the four groups are combined. I kept the original, simpler version in the tests (`slow_shanten`) and check that the fast one always gives the same answer.

**Helpful tiles:** the unseen tiles that would lower your distance. "Unseen" means the full set minus your hand, every discard and every meld on the table (the wall and the bots' hidden hands are both unknown to you).

**The percentage:** if `K` helpful tiles are among `N` unseen ones and you will see `L` of them, then

```
P(see at least one helpful tile) = 1 − C(N−K, L) / C(N, L)
```

Read it as "1 − (ways to see only unhelpful tiles) / (all ways to see L tiles)". It's used with L = 4 for "next round" (your draw plus the three bot discards) and L = tiles left in the wall for "before the wall runs out".

This formula has a big blind spot: it only asks "will I see a helpful tile?". It ignores that a bot might **win first** or **steal a tile with pong/chi**. That's what the simulation below fixes. For a hand that's not ready, this number is naturally high early and doesn't mean you'll win.

## Simulated win chance (`simulation.py`)

To include the bots in the odds, we **replay the rest of the game** many times ("Monte Carlo"):

1. Take the current game. You know your hand, every discard and every meld.
2. Randomly deal the tiles you *can't* see to the three bots and the wall. That's one possible "world" (`Game.determinize`).
3. Make your choice in that world (discard X, pong, pass, ...).
4. Play the rest of the game with the bot AI in every seat, including yours.
5. Record who won. Repeat with a new random world about 200–300 times (as many as fit in about 2.5 seconds).

The share of worlds where you win is the estimate. Every option is tried in the **same** worlds, which makes comparing options fairer. The page shows the estimate with a rough margin of error (about ±6% at 250 games), so a 2-point difference between two options is noise, not a real preference.

For a pong/chi offer, the buttons show your distance from winning after the claim and the simulated win chance for claiming versus passing.

Simplifications, on purpose:

- From your choice on, the simulation plays **you like a bot**, so it isn't measuring how well *you* will play.
- It doesn't use what the bots' past discards suggest about their hands, so it can't spot a bot that's obviously close to winning.
- The result changes a little every time, because the worlds are random.
- Simulated games are quick to play: in one run of 60 fully automatic games, the seat that draws first won 42% of them and the rest were split among the bots. So "you" start with roughly 20–40% in this game, not 25%. It's a race, and going first helps.

## Monte Carlo statistics (`stats.py`)

"Just try it many times." Deal lots of random hands and count. Example (`python stats.py --trials 100000 --seed 1`):

```
Random 14-tile hands dealt: 100,000
  Winning hands: 0  (so fewer than 1 in 100,000)
Random 13-tile hands dealt: 50,000
  Ready hands (one tile from winning): 0.012%
    2:   7.82%   3:  31.23%   4:  38.01%   5:  18.69%   ...
```

A random hand almost never wins (fewer than 1 in 100,000 here), and roughly 1 in 10,000 random 13-tile hands is ready. A typical random hand is 3–4 tiles from ready. That's why you have to *play* to win.

## Project layout

| File | What it does |
|---|---|
| `tiles.py` | Tile names, the 136-tile set, dealing, sort order, tile symbols |
| `checker.py` | The winning-hand backtracking algorithm |
| `probability.py` | Waits, distance from winning (fast, meld-aware), probability maths, Monte Carlo helpers |
| `melds.py` | The pong and chi rules: which claims are possible |
| `bots.py` | The bot AI: what to discard, whether to claim |
| `game.py` | The game: wall, four players, turn order, claims, copies for simulation. No web code. |
| `simulation.py` | Replays the rest of the game many times to estimate your win chance |
| `app.py` | A thin Flask app that turns the game into JSON (`/api/state` is fast, `/api/odds` runs the simulation) |
| `templates/`, `static/` | The web page (plain HTML/CSS/JavaScript that only draws what the server says) |
| `stats.py` | Command-line Monte Carlo statistics |
| `tests/` | pytest tests for every module |

## Limits (on purpose)

- **Shape only.** Real Hong Kong play also requires a minimum number of *faan* (scoring points) to win. This project only checks the sets-plus-pair shape, and does no scoring. Bots will "win" with hands a real table wouldn't accept.
- No Thirteen Orphans or Seven Pairs, no kongs (four-of-a-kind), and no concealed-hand bonuses.
- The bots are greedy and simple. They don't defend or read discards.
- If you pass on a winning tile, you can't claim that same tile as a pong/chi (a simplification).
- One game is kept in server memory, so it's a single-player local app.

## Ideas for later

Thirteen Orphans, kongs, faan scoring, smarter bots (defence, reading discards), using discards to guess bots' hands in the simulation.
