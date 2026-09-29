"""Rules for claiming a discarded tile to make a meld (a set on the table).

Hong Kong rules used here:
    pong  (碰)  three identical tiles. Anyone may pong ANY player's discard.
    chi   (上)  a run of three in one suit. You may chi ONLY the discard of the
                player just before you in turn order (the "upper" player).
    win        beats pong and chi, and can be claimed off anyone's discard.
"""

from tiles import parse_tile


def can_pong(concealed, tile):
    """True if you hold at least 2 copies of `tile` to pair with the discard."""
    return concealed.count(tile) >= 2


def chi_options(concealed, tile):
    """Every way to complete a run using the discarded `tile`.

    Returns a list of (tile_a, tile_b): the two tiles from YOUR hand that go
    with the discard. For a discarded 4-bamboo you might get
        [("2-bamboo","3-bamboo"), ("3-bamboo","5-bamboo"), ("5-bamboo","6-bamboo")]
    Runs only exist in the three numbered suits.
    """
    suit, rank = parse_tile(tile)
    if rank is None:
        return []
    options = []
    # the discard can be the lowest, middle or highest tile of the run
    for low, high in ((rank - 2, rank - 1), (rank - 1, rank + 1), (rank + 1, rank + 2)):
        if low < 1 or high > 9:
            continue
        a, b = f"{low}-{suit}", f"{high}-{suit}"
        if a in concealed and b in concealed:
            options.append((a, b))
    return options
