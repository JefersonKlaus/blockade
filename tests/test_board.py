import random

import pytest

from blockwar.board import Board, apply_move, flips_for
from blockwar.models import MAX_BOARD, MIN_BOARD, IllegalMove, Player

B, O = Player.BLUE, Player.ORANGE


def reference_flips(board: Board, pos, player) -> set:
    """Independent, deliberately naive version of the capture rule, used to check
    `flips_for` on thousands of random positions. Keep it simple, not fast."""
    if board.get(pos) is not None:
        return set()
    captured = set()
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == dc == 0:
                continue
            run = []
            for step in range(1, board.size):
                r, c = pos[0] + dr * step, pos[1] + dc * step
                if not (0 <= r < board.size and 0 <= c < board.size):
                    run = []
                    break
                cell = board.cells[r][c]
                if cell is None:
                    run = []
                    break
                if cell is player:
                    break
                run.append((r, c))
            else:
                run = []
            captured.update(run)
    return captured


# ---------------------------------------------------------------- creating boards

def test_initial_board_is_centered_and_balanced_for_every_supported_size():
    for size in range(MIN_BOARD, MAX_BOARD + 1):
        board = Board.initial(size)
        assert board.size == size and len(board.cells) == size
        assert all(len(row) == size for row in board.cells)
        assert board.counts() == {B: 2, O: 2}
        assert len(board.empty_cells()) == size * size - 4
        mid = size // 2
        assert {board.get((mid - 1, mid - 1)), board.get((mid, mid))} == {B}
        assert {board.get((mid - 1, mid)), board.get((mid, mid - 1))} == {O}


def test_initial_rejects_bad_sizes():
    for size in (MIN_BOARD - 1, MAX_BOARD + 1, 0, -5):
        with pytest.raises(ValueError):
            Board.initial(size)


def test_text_boards_and_validation():
    board = Board.from_text(["B.O", "...", "O.B"])
    assert board.size == 3 and board.get((0, 0)) is B and board.get((0, 2)) is O
    assert board.get((1, 1)) is None and board.get((2, 2)) is B
    with pytest.raises(ValueError):
        Board.from_text(["B.", "..", ".."])      # not square
    with pytest.raises(ValueError):
        Board.from_text(["X..", "...", "..."])   # unknown character


def test_board_is_immutable_and_with_changes_returns_a_copy():
    board = Board.initial(5)
    with pytest.raises(AttributeError):
        board.size = 7  # type: ignore[misc]
    changed = board.with_changes({(0, 0): B})
    assert changed.get((0, 0)) is B and board.get((0, 0)) is None
    assert changed != board


# ---------------------------------------------------------------- capture rule

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
    assert flips_for(board, (2, 2), O) == ()   # occupied cell
    assert flips_for(board, (-1, 0), O) == ()  # outside the board
    assert flips_for(board, (7, 7), O) == ()


def test_flips_for_matches_the_reference_rule_on_random_boards(make_random_board):
    """Property test: on any position, for any move and player, `flips_for` must flip
    exactly what the rule describes. Guards refactors of the capture code."""
    rng = random.Random(2024)
    for _ in range(300):
        board = make_random_board(rng, rng.choice([4, 5, 7, 9]), fill=rng.random())
        for pos in board.positions():
            for player in (B, O):
                got = flips_for(board, pos, player)
                assert len(got) == len(set(got)), "a block must never be listed twice"
                assert set(got) == reference_flips(board, pos, player), (board, pos)


# ---------------------------------------------------------------- applying moves

def test_apply_move_rejects_bad_cells():
    board = Board.initial(7)
    with pytest.raises(IllegalMove):
        apply_move(board, (2, 2), B)
    with pytest.raises(IllegalMove):
        apply_move(board, (9, 9), B)
    with pytest.raises(IllegalMove):
        apply_move(board, (-1, 3), B)


def test_apply_move_conserves_blocks_on_random_boards(make_random_board):
    """The mover gains 1 + flipped blocks, the opponent loses exactly the flipped ones,
    and no other cell changes."""
    rng = random.Random(11)
    for _ in range(200):
        board = make_random_board(rng, 7, fill=rng.random())
        empties = board.empty_cells()
        if not empties:
            continue
        pos, player = rng.choice(empties), rng.choice([B, O])
        before = board.counts()
        new, flipped = apply_move(board, pos, player)
        after = new.counts()
        assert after[player] == before[player] + 1 + len(flipped)
        assert after[player.other] == before[player.other] - len(flipped)
        changed = {p for p in board.positions() if board.get(p) != new.get(p)}
        assert changed == {pos, *flipped}


