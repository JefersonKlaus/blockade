import random

import pytest

from blockwar.board import Board, apply_move, flips_for
from blockwar.bot import Level, choose_move, level_from_value, positional_value
from blockwar.models import Player

B, O = Player.BLUE, Player.ORANGE
SEEDS = range(20)


# ---------------------------------------------------------------- every level

@pytest.mark.parametrize("level", list(Level))
@pytest.mark.parametrize("player", [B, O])
def test_every_level_picks_an_empty_cell(level, player):
    board = Board.initial(7)
    for seed in range(5):
        assert choose_move(board, player, level, random.Random(seed)) in board.empty_cells()


@pytest.mark.parametrize("level", list(Level))
def test_no_move_when_the_board_is_full(level):
    full = Board.from_text(["BBOO"] * 4)
    assert choose_move(full, B, level, random.Random(1)) is None


@pytest.mark.parametrize("level", list(Level))
def test_a_single_empty_cell_is_always_chosen(level):
    board = Board.from_text(["BBOO", "BBOO", "BBOO", "BBO."])
    assert choose_move(board, O, level, random.Random(0)) == (3, 3)


@pytest.mark.parametrize("level", list(Level))
def test_same_seed_gives_same_choice(level):
    board = Board.initial(7)
    a = choose_move(board, B, level, random.Random(5))
    b = choose_move(board, B, level, random.Random(5))
    assert a == b


@pytest.mark.parametrize("level", list(Level))
def test_choosing_does_not_change_the_board(level):
    board = Board.from_text(["....", "BOO.", ".O..", "...."])
    snapshot = board.to_text()
    choose_move(board, B, level, random.Random(0))
    assert board.to_text() == snapshot


# ---------------------------------------------------------------- easy

def test_easy_plays_randomly_over_many_seeds():
    board = Board.initial(7)
    picks = {choose_move(board, B, Level.EASY, random.Random(s)) for s in range(60)}
    assert len(picks) > 10  # not stuck on one cell, not following a strategy


# ---------------------------------------------------------------- medium

def test_medium_takes_the_biggest_capture():
    board = Board.from_text(["....", "BOO.", "....", "...."])
    assert choose_move(board, B, Level.MEDIUM, random.Random(0)) == (1, 3)


def test_medium_always_picks_a_move_with_the_most_flips_and_breaks_ties_randomly():
    board = Board.initial(7)
    best = max(len(flips_for(board, p, B)) for p in board.empty_cells())
    picks = {choose_move(board, B, Level.MEDIUM, random.Random(s)) for s in SEEDS}
    assert all(len(flips_for(board, p, B)) == best for p in picks)
    assert len(picks) > 1  # the opening has several equally good captures


# ---------------------------------------------------------------- hard

def test_positional_values():
    board = Board.initial(7)
    assert positional_value(board, (0, 0)) == 8.0     # corner
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

def test_level_from_value_and_labels():
    assert level_from_value("dificil") is Level.HARD
    assert level_from_value("lixo") is Level.MEDIUM
    assert level_from_value("lixo", Level.EASY) is Level.EASY
    assert [lv.label for lv in Level] == ["Fácil", "Médio", "Difícil"]


@pytest.mark.parametrize("level", list(Level))
def test_level_values_roundtrip(level):
    """The stored value is what goes into the save file, so it must map back."""
    assert level_from_value(level.value) is level
