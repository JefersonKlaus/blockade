import random

import pytest

from blockwar.board import Board
from blockwar.game import Game
from blockwar.models import IllegalMove, Player

B, O = Player.BLUE, Player.ORANGE


# ---------------------------------------------------------------- starting a game

def test_new_game_starts_with_blue_and_no_history():
    game = Game(7)
    assert game.current is B and game.turn == 0 and not game.over
    assert not game.can_undo and game.last_move is None and game.winner is None


# ---------------------------------------------------------------- moves

def test_play_flips_blocks_and_passes_the_turn():
    game = Game(board=Board.initial(4))
    assert game.preview((1, 3)) == ((1, 2),)
    result = game.play((1, 3))
    assert result.player is B and result.pos == (1, 3)
    assert result.flipped == ((1, 2),) and not result.game_over
    assert game.counts() == {B: 4, O: 1}
    assert game.current is O and game.turn == 1 and game.last_move == (1, 3)


def test_play_rejects_occupied_and_out_of_range_cells():
    game = Game(7)
    with pytest.raises(IllegalMove):
        game.play((2, 2))
    with pytest.raises(IllegalMove):
        game.play((-1, 0))
    assert game.turn == 0 and game.current is B  # an illegal move changes nothing
    assert not game.can_undo                      # ...and does not create history


def test_skip_loses_the_turn_without_touching_the_board():
    game = Game(7)
    game.play((0, 0))
    before = game.board
    result = game.skip()
    assert result.pos is None and result.player is O      # a lost turn
    assert result.flipped == () and not result.game_over
    assert game.board == before and game.current is B and game.turn == 2
    assert game.last_move is None


# ---------------------------------------------------------------- undo

def test_undoing_a_whole_random_game_returns_to_the_start():
    rng = random.Random(3)
    game = Game(5)
    states = []
    while not game.over:
        states.append((game.board, game.current, game.turn, game.last_move))
        if rng.random() < 0.1:
            game.skip()
        else:
            game.play(rng.choice(game.board.empty_cells()))
    for expected in reversed(states):
        assert game.undo()
        assert (game.board, game.current, game.turn, game.last_move) == expected
    assert not game.can_undo and not game.undo()      # nothing left to undo


# ---------------------------------------------------------------- end of the game

def test_full_board_ends_the_game_and_most_blocks_win():
    assert Game(board=Board.from_text(["OOOB"] * 4)).winner is O
    game = Game(board=Board.from_text(["BBBO"] * 4))
    assert game.over and game.winner is B
    with pytest.raises(IllegalMove):
        game.skip()
    with pytest.raises(IllegalMove):
        game.play((0, 0))


def test_equal_counts_on_a_full_board_is_a_draw():
    game = Game(board=Board.from_text(["BBOO"] * 4))
    assert game.over and game.winner is None  # a draw


def test_wiping_out_a_side_ends_the_game_early():
    game = Game(board=Board.from_text(["BB..", "BB..", "....", "...."]))
    assert game.over and game.winner is B
    assert not game.board.is_full


def test_a_game_in_progress_has_no_winner_even_if_someone_leads():
    game = Game(board=Board.from_text(["BBB.", "BBB.", "...O", "...."]))
    assert not game.over and game.winner is None


def test_random_games_always_end_and_keep_the_block_count_consistent():
    for size, seed in ((5, 0), (5, 1), (7, 2), (7, 3)):
        rng = random.Random(seed)
        game = Game(size)
        while not game.over:
            total_before = sum(game.counts().values())
            game.play(rng.choice(game.board.empty_cells()))
            assert sum(game.counts().values()) == total_before + 1
        assert game.board.is_full or min(game.counts().values()) == 0
        assert game.turn <= size * size - 4
        if game.board.is_full:  # odd boards have an odd number of cells: never a draw
            assert game.winner is not None
