import random

from blockwar.board import Board, apply_move
from blockwar.bot import Level, choose_move, level_from_value, positional_value
from blockwar.models import Player

B, O = Player.BLUE, Player.ORANGE


def test_every_level_picks_an_empty_cell_and_none_when_full():
    board = Board.initial(7)
    for level in Level:
        pos = choose_move(board, B, level, random.Random(1))
        assert pos in board.empty_cells()
    full = Board.from_text(["BBOO"] * 4)
    assert choose_move(full, B, Level.HARD, random.Random(1)) is None


def test_same_seed_gives_same_choice():
    board = Board.initial(7)
    for level in Level:
        a = choose_move(board, B, level, random.Random(5))
        b = choose_move(board, B, level, random.Random(5))
        assert a == b


def test_medium_takes_the_biggest_capture():
    board = Board.from_text(["....", "BOO.", "....", "...."])
    assert choose_move(board, B, Level.MEDIUM, random.Random(0)) == (1, 3)


def test_positional_values():
    board = Board.initial(7)
    assert positional_value(board, (0, 0)) == 8.0     # canto
    assert positional_value(board, (0, 1)) == -3.0    # colada num canto vazio
    assert positional_value(board, (1, 1)) == -3.0
    assert positional_value(board, (0, 3)) == 2.0     # borda
    assert positional_value(board, (3, 1)) == 0.0     # miolo
    taken, _ = apply_move(board, (0, 0), B)
    assert positional_value(taken, (0, 1)) == 2.0     # canto ocupado: deixa de ser perigo


def test_hard_prefers_a_corner_over_a_slightly_bigger_capture():
    board = Board.from_text([
        ".OB..",
        ".....",
        ".....",
        "BOO..",
        ".....",
    ])
    # canto (0,0) vira 1 bloco; (3,3) viraria 2, mas o difícil dá valor ao canto
    assert choose_move(board, B, Level.MEDIUM, random.Random(0)) == (3, 3)
    assert choose_move(board, B, Level.HARD, random.Random(0)) == (0, 0)


def test_level_from_value_and_labels():
    assert level_from_value("dificil") is Level.HARD
    assert level_from_value("lixo") is Level.MEDIUM
    assert level_from_value("lixo", Level.EASY) is Level.EASY
    assert [lv.label for lv in Level] == ["Fácil", "Médio", "Difícil"]
