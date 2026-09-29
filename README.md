# Mahjong Odds

A Hong Kong–style mahjong solitaire game that shows your **winning chances as you play**. You draw and discard against three simple bots, and after every move the page tells you how far your hand is from winning, which tiles would help, and how likely you are to see one.

Built as a first-year CS project. The interesting part is the algorithm that decides whether 14 tiles are a winning hand (a **recursive backtracking search**), plus a little probability on top.

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
- You start with 13 tiles. Each round you **draw** a tile, then **discard** one.
- Then each of the three bots draws a tile and throws away a random one.
- You win when your 14 tiles form **4 sets + 1 pair**, either on your own draw or on **any bot's discard** (in Hong Kong mahjong you can win off a discard).
- A **set** is a triplet (three identical tiles) or a run (three consecutive numbers in the *same* suit, e.g. 3-4-5 bamboo). Winds and dragons can't form runs, and runs don't wrap around (8-9-1 is not a run).

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

The hand is stored as a `Counter` (`{tile: count}`), so "remove a run" is three `-= 1`s and "undo" is three `+= 1`s.

### Worked example

Hand: `4-5-6 bamboo, 1-2-3 circles, 5 6 6 7 7 8 characters, white-dragon ×2`

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

**Distance from winning ("shanten"):** a fresh hand is usually 3–4 tiles from ready, and if we only reported "0% until ready" the game would feel dead. So we compute how far each hand is: −1 = winning, 0 = ready, 1 = one step from ready, and so on. It's another recursive search: split the hand into sets (2 points each), partial sets like a pair or `4-5` (1 point), and the pair (1 point), and keep the best split. `distance = 8 − 2·sets − partials − pair`. Tests confirm distance 0 exactly matches "has a winning tile" and distance −1 exactly matches the checker on hundreds of near-winning hands.

**Helpful tiles:** the unseen tiles that would lower your distance. "Unseen" means the full set minus your hand minus every discard (the wall and the bots' hidden hands are both unknown to you).

**The percentage:** if `K` helpful tiles are among `N` unseen ones and you will see `L` of them, then

```
P(see at least one helpful tile) = 1 − C(N−K, L) / C(N, L)
```

Read it as "1 − (ways to see only unhelpful tiles) / (all ways to see L tiles)". It's used with L = 4 for "next round" (your draw plus the three bot discards) and L = tiles left in the wall for "before the wall runs out".

Simplifications to be aware of: the bots' discards are treated as random draws from the unseen tiles, and the calculation doesn't consider you improving your hand *within* the round. For a ready hand this is your win chance. For a hand that's not ready it means "chance of a helpful tile", which is naturally high early and doesn't mean you'll win.

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
| `probability.py` | Waits, distance from winning, probability maths, Monte Carlo helpers |
| `game.py` | The game itself: wall, hands, bots, turns, claiming a win. No web code. |
| `app.py` | A thin Flask app that turns the game into JSON |
| `templates/`, `static/` | The web page (plain HTML/CSS/JavaScript that only draws what the server says) |
| `stats.py` | Command-line Monte Carlo statistics |
| `tests/` | pytest tests for every module |

## Limits (on purpose)

- **Shape only.** Real Hong Kong play also requires a minimum number of *faan* (scoring points) to win. This project only checks the 4-sets-plus-pair shape, and does no scoring.
- No Thirteen Orphans or Seven Pairs, no melds/kongs, and no claiming discards for chows or pungs.
- The bots discard at random and never try to win. They just make discards appear.
- One game is kept in server memory, so it's a single-player local app.

## Ideas for later

Thirteen Orphans, claiming discards for chows/pungs, smarter bots, faan scoring, a discard-history heatmap.
