"""Monte Carlo statistics: "just try it thousands of times".

    python stats.py                 # 100,000 random hands
    python stats.py --trials 500000
    python stats.py --seed 1        # repeatable results

Deal lots of random hands and count what happens. Real winning hands are so
rare that you'll often see "0 wins" - that IS the answer: fewer than 1 in
`trials`. So we also report how far a typical random hand is from winning.
"""

import argparse
import random

from checker import is_winning_hand
from probability import shanten_distribution
from tiles import random_hand


def run(trials, seed=None):
    """Return a dict of results (also used by the tests)."""
    rng = random.Random(seed)
    wins = sum(is_winning_hand(random_hand(14, rng)) for _ in range(trials))
    # One shared sample of 13-tile hands: "ready" simply means distance 0, so the
    # ready rate and the distance table always agree. (tests/test_probability.py
    # checks that distance 0 and "has a winning tile" are the same thing.)
    ready_trials = max(trials // 2, 1)
    distribution = shanten_distribution(ready_trials, 13, rng)
    return {
        "trials": trials,
        "wins": wins,
        "ready_trials": ready_trials,
        "ready_rate": distribution.get(0, 0.0),
        "distribution": distribution,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--trials", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    result = run(args.trials, args.seed)
    wins = result["wins"]
    print(f"Random 14-tile hands dealt: {result['trials']:,}")
    if wins:
        print(f"  Winning hands: {wins}  ({wins / result['trials']:.6%}, about 1 in {result['trials'] // wins:,})")
    else:
        print(f"  Winning hands: 0  (so fewer than 1 in {result['trials']:,})")
    print(f"Random 13-tile hands dealt: {result['ready_trials']:,}")
    print(f"  Ready hands (one tile from winning): {result['ready_rate']:.3%}")
    print("  Distance from winning (0 = ready), share of hands:")
    for distance, share in result["distribution"].items():
        print(f"    {distance}: {share:7.2%}  {'#' * round(share * 60)}")


if __name__ == "__main__":
    main()
