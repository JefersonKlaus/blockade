import random

import pytest

from blockwar.board import DIRECTIONS, Board, apply_move, flips_for
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

def test_initial_board_has_four_blocks_in_a_checker_pattern():
    board = Board.initial(7)
    assert board.counts() == {B: 2, O: 2}
    assert board.get((2, 2)) is B and board.get((3, 3)) is B
    assert board.get((2, 3)) is O and board.get((3, 2)) is O
    assert len(board.empty_cells()) == 45


@pytest.mark.parametrize("size", range(MIN_BOARD, MAX_BOARD + 1))
def test_initial_board_is_centered_and_balanced_for_every_supported_size(size):
    board = Board.initial(size)
    assert board.size == size and len(board.cells) == size
    assert all(len(row) == size for row in board.cells)
    assert board.counts() == {B: 2, O: 2}
    assert len(board.empty_cells()) == size * size - 4
    mid = size // 2
    assert {board.get((mid - 1, mid - 1)), board.get((mid, mid))} == {B}
    assert {board.get((mid - 1, mid)), board.get((mid, mid - 1))} == {O}


@pytest.mark.parametrize("size", [MIN_BOARD - 1, MAX_BOARD + 1, 0, -5])
def test_initial_rejects_bad_sizes(size):
    with pytest.raises(ValueError):
        Board.initial(size)


def test_text_roundtrip_and_validation():
    lines = ["B.O", "...", "O.B"]
    assert Board.from_text(lines).to_text() == lines
    with pytest.raises(ValueError):
        Board.from_text(["B.", "..", ".."])      # not square
    with pytest.raises(ValueError):
        Board.from_text(["X..", "...", "..."])   # unknown character


def test_text_roundtrip_on_random_boards(make_random_board):
    rng = random.Random(0)
    for _ in range(50):
        board = make_random_board(rng, rng.randint(MIN_BOARD, MAX_BOARD))
        assert Board.from_text(board.to_text()) == board


def test_board_is_immutable_and_with_changes_returns_a_copy():
    board = Board.initial(5)
    with pytest.raises(AttributeError):
        board.size = 7  # type: ignore[misc]
    changed = board.with_changes({(0, 0): B})
    assert changed.get((0, 0)) is B and board.get((0, 0)) is None
    assert changed != board


def test_eight_directions_and_corners():
    assert len(DIRECTIONS) == 8 and len(set(DIRECTIONS)) == 8
    assert (0, 0) not in DIRECTIONS
    assert all(dr in (-1, 0, 1) and dc in (-1, 0, 1) for dr, dc in DIRECTIONS)
    assert Board.initial(5).corners == ((0, 0), (0, 4), (4, 0), (4, 4))
    assert Board.initial(7).corners == ((0, 0), (0, 6), (6, 0), (6, 6))


def test_positions_visits_every_cell_once_row_by_row():
    board = Board.initial(4)
    positions = list(board.positions())
    assert len(positions) == 16 and len(set(positions)) == 16
    assert positions[:5] == [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0)]


def test_in_bounds():
    board = Board.initial(5)
    assert board.in_bounds((0, 0)) and board.in_bounds((4, 4))
    for pos in [(-1, 0), (0, -1), (5, 0), (0, 5)]:
        assert not board.in_bounds(pos)


# ---------------------------------------------------------------- capture rule

def test_flip_in_a_row_lists_the_blocks_in_walking_order():
    board = Board.from_text(["....", "BOO.", "....", "...."])
    assert flips_for(board, (1, 3), B) == ((1, 2), (1, 1))


def test_flip_needs_a_closing_block_of_your_own():
    board = Board.from_text(["....", ".OO.", "....", "...."])
    assert flips_for(board, (1, 3), B) == ()  # no blue block on the other side
    board = Board.from_text(["....", "BOO.", "....", "...."])
    assert flips_for(board, (1, 3), O) == ()  # the row belongs to the mover, not the enemy


def test_flip_does_not_jump_over_an_empty_cell():
    board = Board.from_text(["....", "B.O.", "....", "...."])
    assert flips_for(board, (1, 3), B) == ()


def test_only_the_closed_side_flips():
    board = Board.from_text(["....", "BO.O", "....", "...."])
    # left of (1, 2) the O is closed by a B; to the right the O row runs into the edge
    assert flips_for(board, (1, 2), B) == ((1, 1),)


@pytest.mark.parametrize("lines, move, expected", [
    (["B...", "O...", "....", "...."], (2, 0), {(1, 0)}),          # vertical, downwards
    (["....", "O...", "B...", "...."], (0, 0), {(1, 0)}),          # vertical, upwards
    (["B...", ".O..", "....", "...."], (2, 2), {(1, 1)}),          # main diagonal
    (["...B", "..O.", "....", "...."], (2, 1), {(1, 2)}),          # anti-diagonal
    (["B....", "O....", "O....", "O....", "....."], (4, 0), {(1, 0), (2, 0), (3, 0)}),
])
def test_single_direction_captures(lines, move, expected):
    assert set(flips_for(Board.from_text(lines), move, B)) == expected


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
                assert set(got) == reference_flips(board, pos, player), (board.to_text(), pos)


def test_corner_blocks_can_never_be_captured(make_random_board):
    """README rule: 'Corner blocks can never be squeezed'."""
    rng = random.Random(7)
    for _ in range(300):
        board = make_random_board(rng, rng.choice([5, 7]), fill=0.8)
        for pos in board.empty_cells():
            for player in (B, O):
                assert not set(flips_for(board, pos, player)) & set(board.corners)


# ---------------------------------------------------------------- applying moves

def test_apply_move_flips_and_leaves_the_original_untouched():
    board = Board.from_text(["....", "BOO.", "....", "...."])
    new, flipped = apply_move(board, (1, 3), B)
    assert new.to_text() == ["....", "BBBB", "....", "...."]
    assert set(flipped) == {(1, 1), (1, 2)}
    assert board.to_text() == ["....", "BOO.", "....", "...."]


def test_a_row_running_into_the_edge_does_not_flip():
    board = Board.from_text([".....", "BOO.O", ".....", ".....", "....."])
    new, flipped = apply_move(board, (1, 3), B)
    assert set(flipped) == {(1, 1), (1, 2)}
    assert new.get((1, 4)) is O  # the row on the right runs into the edge: nothing changes


def test_captures_do_not_chain():
    board = Board.from_text([
        "..B..",
        "..O..",
        "BOO..",
        ".....",
        ".....",
    ])
    # Playing (2,3) flips (2,1) and (2,2). The freshly flipped (2,2) now "closes" the
    # orange (1,2) against the blue (0,2), but turned blocks never capture again during
    # the same move, so (1,2) must stay orange.
    new, flipped = apply_move(board, (2, 3), B)
    assert set(flipped) == {(2, 1), (2, 2)}
    assert new.get((1, 2)) is O


def test_apply_move_rejects_bad_cells():
    board = Board.initial(7)
    with pytest.raises(IllegalMove):
        apply_move(board, (2, 2), B)
    with pytest.raises(IllegalMove):
        apply_move(board, (9, 9), B)
    with pytest.raises(IllegalMove):
        apply_move(board, (-1, 3), B)


def test_illegal_move_is_a_value_error():
    assert issubclass(IllegalMove, ValueError)


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


def test_is_full_and_counts():
    assert not Board.initial(4).is_full
    full = Board.from_text(["BBOO"] * 4)
    assert full.is_full and full.counts() == {B: 8, O: 8}
    assert full.empty_cells() == []
    assert full.count(B) == 8 and full.count(O) == 8
