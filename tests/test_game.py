import pytest

from blockwar.board import Board
from blockwar.game import Game
from blockwar.models import IllegalMove, Player

B, O = Player.BLUE, Player.ORANGE


def test_new_game_starts_with_blue_and_no_history():
    game = Game(7)
    assert game.current is B and game.turn == 0 and not game.over
    assert not game.can_undo and game.last_move is None and game.winner is None


def test_play_flips_blocks_and_passes_the_turn():
    game = Game(board=Board.initial(4))
    assert game.preview((1, 3)) == ((1, 2),)
    result = game.play((1, 3))
    assert result.player is B and result.flipped == ((1, 2),) and not result.skipped
    assert game.counts() == {B: 4, O: 1}
    assert game.current is O and game.turn == 1 and game.last_move == (1, 3)


def test_play_rejects_occupied_and_out_of_range_cells():
    game = Game(7)
    with pytest.raises(IllegalMove):
        game.play((2, 2))
    with pytest.raises(IllegalMove):
        game.play((-1, 0))
    assert game.turn == 0 and game.current is B  # jogada inválida não muda nada


def test_a_move_that_flips_nothing_is_still_legal():
    game = Game(7)
    result = game.play((0, 0))
    assert result.flipped == () and game.board.get((0, 0)) is B


def test_skip_loses_the_turn_without_touching_the_board():
    game = Game(7)
    before = game.board
    result = game.skip()
    assert result.skipped and result.pos is None and result.player is B
    assert game.board == before and game.current is O and game.turn == 1
    assert game.last_move is None


def test_undo_restores_board_player_and_turn():
    game = Game(board=Board.initial(4))
    start = game.board
    game.play((1, 3))
    game.skip()
    assert game.undo() and game.current is O and game.turn == 1
    assert game.undo() and game.board == start and game.current is B and game.turn == 0
    assert game.last_move is None
    assert not game.undo()


def test_full_board_ends_the_game_and_most_blocks_win():
    game = Game(board=Board.from_text(["BBBO"] * 4))
    assert game.over and game.winner is B and not game.is_draw
    with pytest.raises(IllegalMove):
        game.skip()
    with pytest.raises(IllegalMove):
        game.play((0, 0))


def test_equal_counts_on_a_full_board_is_a_draw():
    game = Game(board=Board.from_text(["BBOO"] * 4))
    assert game.over and game.winner is None and game.is_draw


def test_wiping_out_a_side_ends_the_game_early():
    game = Game(board=Board.from_text(["BB..", "BB..", "....", "...."]))
    assert game.over and game.winner is B


def test_last_move_ends_the_game_and_reports_it():
    board = Board.from_text(["BBBB", "BBBB", "BBBB", "OOO."])
    game = Game(board=board)
    result = game.play((3, 3))
    assert result.game_over and game.over and game.winner is B


def test_a_full_random_game_always_ends_with_a_board_full_of_blocks():
    import random
    rng = random.Random(7)
    game = Game(7)
    while not game.over:
        game.play(rng.choice(game.board.empty_cells()))
    assert game.board.is_full or min(game.counts().values()) == 0
    assert game.turn <= 45
