import pytest

from blockwar.board import DIRECTIONS, Board, apply_move, flips_for
from blockwar.models import IllegalMove, Player

B, O = Player.BLUE, Player.ORANGE


def test_initial_board_has_four_blocks_in_a_checker_pattern():
    board = Board.initial(7)
    assert board.counts() == {B: 2, O: 2}
    assert board.get((2, 2)) is B and board.get((3, 3)) is B
    assert board.get((2, 3)) is O and board.get((3, 2)) is O
    assert len(board.empty_cells()) == 45


@pytest.mark.parametrize("size", [3, 10, 0])
def test_initial_rejects_bad_sizes(size):
    with pytest.raises(ValueError):
        Board.initial(size)


def test_text_roundtrip_and_validation():
    lines = ["B.O", "...", "O.B"]
    assert Board.from_text(lines).to_text() == lines
    with pytest.raises(ValueError):
        Board.from_text(["B.", "..", ".."])
    with pytest.raises(ValueError):
        Board.from_text(["X..", "...", "..."])


def test_eight_directions_and_corners():
    assert len(DIRECTIONS) == 8 and (0, 0) not in DIRECTIONS
    assert Board.initial(5).corners == ((0, 0), (0, 4), (4, 0), (4, 4))


def test_flip_in_a_row_lists_the_blocks_in_walking_order():
    board = Board.from_text(["....", "BOO.", "....", "...."])
    assert flips_for(board, (1, 3), B) == ((1, 2), (1, 1))


def test_flip_needs_a_closing_block_of_your_own():
    board = Board.from_text(["....", ".OO.", "....", "...."])
    assert flips_for(board, (1, 3), B) == ()  # nenhum azul do outro lado
    board = Board.from_text(["....", "BOO.", "....", "...."])
    assert flips_for(board, (1, 3), O) == ()  # a fila é do próprio jogador, não do inimigo


def test_flip_does_not_jump_over_an_empty_cell():
    board = Board.from_text(["....", "B.O.", "....", "...."])
    assert flips_for(board, (1, 3), B) == ()


def test_only_the_closed_side_flips():
    board = Board.from_text(["....", "BO.O", "....", "...."])
    # à esquerda de (1, 2) o O está fechado por um B; à direita a fila de O termina na borda
    assert flips_for(board, (1, 2), B) == ((1, 1),)


def test_flips_in_all_eight_directions_at_once():
    board = Board.from_text([
        "B.B.B",
        ".OOO.",
        "BO.OB",
        ".OOO.",
        "B.B.B",
    ])
    assert set(flips_for(board, (2, 2), B)) == {
        (1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2), (3, 3)}


def test_flips_only_work_on_empty_in_bounds_cells():
    board = Board.initial(7)
    assert flips_for(board, (2, 2), O) == ()   # casa ocupada
    assert flips_for(board, (-1, 0), O) == ()  # fora do tabuleiro
    assert flips_for(board, (7, 7), O) == ()


def test_apply_move_flips_and_leaves_the_original_untouched():
    board = Board.from_text(["....", "BOO.", "....", "...."])
    new, flipped = apply_move(board, (1, 3), B)
    assert new.to_text() == ["....", "BBBB", "....", "...."]
    assert set(flipped) == {(1, 1), (1, 2)}
    assert board.to_text() == ["....", "BOO.", "....", "...."]


def test_captures_do_not_chain():
    board = Board.from_text([".....", "BOO.O", ".....", ".....", "....."])
    new, flipped = apply_move(board, (1, 3), B)
    assert set(flipped) == {(1, 1), (1, 2)}
    assert new.get((1, 4)) is O  # a fila da direita termina na borda: nada muda ali


def test_apply_move_rejects_bad_cells():
    board = Board.initial(7)
    with pytest.raises(IllegalMove):
        apply_move(board, (2, 2), B)
    with pytest.raises(IllegalMove):
        apply_move(board, (9, 9), B)


def test_is_full_and_counts():
    assert not Board.initial(4).is_full
    full = Board.from_text(["BBOO"] * 4)
    assert full.is_full and full.counts() == {B: 8, O: 8}
