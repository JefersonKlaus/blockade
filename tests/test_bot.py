import random


from blockwar.board import Board, apply_move, flips_for
from blockwar.bot import Level, choose_move, level_from_value, positional_value
from blockwar.models import Player

B, O = Player.BLUE, Player.ORANGE
SEEDS = range(20)


# ---------------------------------------------------------------- every level

def test_every_level_picks_an_empty_cell_or_none_on_a_full_board():
    start = Board.initial(7)
    one_left = Board.from_text(["BBOO", "BBOO", "BBOO", "BBO."])
    full = Board.from_text(["BBOO"] * 4)
    for level in Level:
        for player in (B, O):
            assert choose_move(start, player, level, random.Random(1)) in start.empty_cells()
        assert choose_move(one_left, O, level, random.Random(0)) == (3, 3)
        assert choose_move(full, B, level, random.Random(1)) is None


# ---------------------------------------------------------------- easy

def test_easy_plays_randomly_over_many_seeds():
    board = Board.initial(7)
    picks = {choose_move(board, B, Level.EASY, random.Random(s)) for s in range(60)}
    assert len(picks) > 10  # not stuck on one cell, not following a strategy


# ---------------------------------------------------------------- medium

def test_medium_always_picks_a_move_with_the_most_flips_and_breaks_ties_randomly():
    board = Board.initial(7)
    best = max(len(flips_for(board, p, B)) for p in board.empty_cells())
    picks = {choose_move(board, B, Level.MEDIUM, random.Random(s)) for s in SEEDS}
    assert all(len(flips_for(board, p, B)) == best for p in picks)
    assert len(picks) > 1  # the opening has several equally good captures


# ---------------------------------------------------------------- hard

def test_positional_values():
    board = Board.initial(7)
    for corner in ((0, 0), (0, 6), (6, 0), (6, 6)):
        assert positional_value(board, corner) == 8.0  # corners
    assert positional_value(board, (6, 5)) == -3.0    # next to another empty corner
    assert positional_value(board, (0, 1)) == -3.0    # next to an empty corner
    assert positional_value(board, (1, 1)) == -3.0
    assert positional_value(board, (0, 3)) == 2.0     # edge
    assert positional_value(board, (3, 1)) == 0.0     # middle
    taken, _ = apply_move(board, (0, 0), B)
    assert positional_value(taken, (0, 1)) == 2.0     # corner taken: no longer a risk
    assert positional_value(taken, (1, 1)) == 0.0


def test_hard_prefers_a_corner_over_a_slightly_bigger_capture():
    board = Board.from_text([
        ".OB..",
        ".....",
        ".....",
        "BOO..",
        ".....",
    ])
    # corner (0,0) flips 1 block; (3,3) would flip 2, but hard values the corner
    assert choose_move(board, B, Level.MEDIUM, random.Random(0)) == (3, 3)
    assert choose_move(board, B, Level.HARD, random.Random(0)) == (0, 0)


def test_hard_looks_ahead_and_avoids_giving_the_opponent_a_big_reply():
    board = Board.from_text([
        "OOOOO",
        ".OOOO",
        "OOB.O",
        ".BBBB",
        "B..OB",
    ])
    # (1,0) and (4,2) each flip 1 block and are both edge cells. After (1,0) orange can
    # answer with a big capture; after (4,2) it cannot. Medium does not care which one
    # it plays, hard always picks the safe one.
    medium = {choose_move(board, B, Level.MEDIUM, random.Random(s)) for s in SEEDS}
    assert medium == {(1, 0), (4, 2)}
    assert {choose_move(board, B, Level.HARD, random.Random(s)) for s in SEEDS} == {(4, 2)}


# ---------------------------------------------------------------- levels

def test_level_from_value():
    """The values are what goes into the save file, so they must map back."""
    assert [level_from_value(level.value) for level in Level] == list(Level)
    assert level_from_value("lixo") is Level.MEDIUM
