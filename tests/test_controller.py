
from blockwar.board import Board
from blockwar.bot import Level
from blockwar.choices import Setup
from blockwar.controller import UNDOS_PER_GAME, Match, Phase
from blockwar.game import Game
from blockwar.mathmode import ADD, OPERATIONS, SUB, MathSettings
from blockwar.models import BOT_PLAYER, HUMAN_PLAYER, Mode, Player
from blockwar.records import record_game
from blockwar.storage import SaveData
from blockwar.texts import ENGLISH, PORTUGUESE

B, O = Player.BLUE, Player.ORANGE


MATH_ON = MathSettings(frozenset({ADD, SUB}))
ALL_MATH = MathSettings(frozenset(OPERATIONS), frozenset(range(1, 11)))


def math_settings(math) -> MathSettings:
    """`math=True` turns on simple sums; a `MathSettings` is used as it is."""
    if isinstance(math, MathSettings):
        return math
    return MATH_ON if math else MathSettings()


def two(size=5, math=False, seed=1) -> Match:
    return Match(Setup(mode=Mode.TWO, size=size, math=math_settings(math), seed=seed),
                 PORTUGUESE)


def versus(size=5, math=False, level=Level.MEDIUM, seed=1) -> Match:
    return Match(Setup(mode=Mode.BOT, size=size, math=math_settings(math), bot_level=level,
                       seed=seed), PORTUGUESE)


def with_board(match: Match, lines) -> Match:
    match.game = Game(board=Board.from_text(lines))
    return match


def play_here(match: Match, pos) -> str:
    """Tap a cell twice (select + confirm) and return the result of the second tap."""
    match.tap(pos)
    return match.tap(pos)


def answer_right(match: Match) -> str:
    return match.answer(match.question.answer)


def answer_wrong(match: Match) -> str:
    return match.answer(next(c for c in match.question.choices if c != match.question.answer))


def play_until_over(match: Match, *, wrong_every: int = 0, max_turns: int = 200) -> int:
    """Drive a match to the end like a player would. Returns how many turns it took."""
    for turn in range(max_turns):
        if match.is_over:
            return turn
        if match.phase is Phase.BOT_TURN:
            assert match.bot_move() is not None
            continue
        assert match.phase is Phase.CHOOSING
        result = play_here(match, match.game.board.empty_cells()[0])
        if result == "question":
            if wrong_every and turn % wrong_every == 0:
                assert answer_wrong(match) == "skipped"
            else:
                assert answer_right(match) == "played"
        else:
            assert result == "played"
    raise AssertionError("the match did not finish")


# ---------------------------------------------------------------- texts

def test_a_match_in_english():
    match = Match(Setup(mode=Mode.TWO, size=5, seed=1), ENGLISH)
    assert match.message == "Tap a square to see what turns."
    assert match.turn_label() == "Blue's turn ●"
    play_here(match, (1, 3))
    assert match.message == "Blue turned 1 block." and match.turn_label() == "Orange's turn ▲"


# ---------------------------------------------------------------- starting

def test_a_new_match_waits_for_the_first_tap():
    match = two()
    assert match.phase is Phase.CHOOSING and match.game.turn == 0
    assert match.pending is None and match.question is None and match.hint_pos is None
    assert match.undos_left == UNDOS_PER_GAME and not match.is_over
    assert match.message == "Toque numa casa para ver o que vira."
    assert match.score_line() == "2 × 2" and match.preview_cells() == ()


# ---------------------------------------------------------------- taps

def test_first_tap_previews_and_second_tap_plays():
    match = two()
    assert match.tap((1, 3)) == "selected"
    assert match.pending == (1, 3) and match.preview_cells() == ((1, 2),)
    assert match.message == "Vira 1 bloco. Toque de novo para jogar."
    assert match.game.turn == 0                 # selecting does not play yet
    assert match.tap((1, 3)) == "played"
    assert match.game.current is O and match.pending is None
    assert match.last_flipped == ((1, 2),) and match.message == "Azul virou 1 bloco."
    assert match.phase is Phase.CHOOSING and match.score_line() == "4 × 1"


def test_a_move_that_flips_nothing_says_so():
    match = two()
    assert match.tap((0, 0)) == "selected"
    assert match.message == "Não vira nada. Toque de novo para jogar mesmo assim."
    assert match.tap((0, 0)) == "played"
    assert match.message == "Azul colocou um bloco." and match.last_flipped == ()


def test_tapping_another_cell_moves_the_selection():
    match = two()
    match.tap((1, 3))
    assert match.tap((0, 0)) == "selected"
    assert match.pending == (0, 0) and "Não vira nada" in match.message
    assert match.game.turn == 0


def test_taps_on_occupied_or_outside_cells_are_ignored():
    match = two()
    match.tap((1, 3))
    for pos in ((2, 2), (9, 9), (-1, 0)):
        assert match.tap(pos) == "ignored"
    assert match.pending == (1, 3)             # the current selection is kept


def test_actions_out_of_phase_are_ignored():
    match = two()
    assert match.confirm() == "ignored"      # nothing selected
    assert match.answer(1) == "ignored"      # no question
    match.tap((1, 3))
    assert match.answer(1) == "ignored"      # a square chosen, but still no question
    assert match.bot_move() is None          # not the phone's turn


def test_two_players_take_turns():
    match = two()
    play_here(match, (1, 3))
    assert match.turn_label() == "Vez do Laranja ▲"
    play_here(match, (0, 0))
    assert match.game.board.get((0, 0)) is O and match.turn_label() == "Vez do Azul ●"


# ---------------------------------------------------------------- phone

def test_against_the_phone_the_bot_answers_after_your_move():
    match = versus()
    assert play_here(match, (1, 3)) == "played"
    assert match.phase is Phase.BOT_TURN and match.turn_label() == "Vez do celular"
    assert match.tap((0, 0)) == "ignored"    # you cannot play on the phone's turn
    result = match.bot_move()
    assert result is not None and result.player is BOT_PLAYER and result.pos is not None
    assert match.game.board.get(result.pos) is BOT_PLAYER
    assert match.phase is Phase.CHOOSING and match.game.current is HUMAN_PLAYER
    assert match.game.turn == 2 and match.turn_label() == "Sua vez"
    assert match.message.startswith("Celular ")


def test_the_same_seed_replays_the_same_match():
    def moves(seed):
        match = versus(size=7, level=Level.EASY, seed=seed)
        for _ in range(5):
            play_here(match, match.game.board.empty_cells()[0])
            match.bot_move()
        return match.game.board

    assert moves(4) == moves(4)


# ---------------------------------------------------------------- math questions

def test_math_mode_asks_a_question_before_placing():
    match = two(math=True)
    match.tap((1, 3))
    assert match.tap((1, 3)) == "question"
    assert match.phase is Phase.QUESTION and match.question is not None
    assert match.message == "Responda certo para colocar o bloco!"
    assert match.game.turn == 0               # the block goes in only after a right answer
    assert match.tap((0, 0)) == "ignored"
    assert match.confirm() == "ignored"
    assert answer_right(match) == "played"
    assert match.game.turn == 1 and match.game.board.get((1, 3)) is B
    assert match.question is None and match.phase is Phase.CHOOSING


def test_wrong_answer_loses_the_turn_and_places_nothing():
    match = two(math=True)
    board = match.game.board
    play_here(match, (1, 3))
    right = match.question.answer
    assert answer_wrong(match) == "skipped"
    assert match.game.board == board and match.game.current is O and match.game.turn == 1
    assert match.message == f"Errou! A resposta era {right}. Azul perdeu a vez."
    assert match.pending is None and match.question is None
    assert match.phase is Phase.CHOOSING and match.last_flipped == ()


def test_undo_and_hint_are_blocked_while_a_question_is_open():
    match = versus(level=Level.EASY, math=True)   # the level where the helpers exist
    play_here(match, (0, 0))
    answer_right(match)
    match.bot_move()
    assert match.game.can_undo and match.hint() is not None   # allowed right now...
    play_here(match, match.game.board.empty_cells()[0])
    assert match.phase is Phase.QUESTION                        # ...but not mid-question
    assert match.undo() is False and match.hint() is None
    assert match.undos_left == UNDOS_PER_GAME


def test_wrong_answer_against_the_phone_hands_the_turn_to_the_bot():
    match = versus(math=True)
    play_here(match, (1, 3))
    assert answer_wrong(match) == "skipped"
    assert match.message.endswith("Você perdeu a vez.")
    assert match.phase is Phase.BOT_TURN
    assert match.bot_move() is not None and match.phase is Phase.CHOOSING


# ---------------------------------------------------------------- beginner helpers

def easy(**kwargs) -> Match:
    """Against the phone on Fácil: the only level where Dica and Desfazer work."""
    return versus(level=Level.EASY, **kwargs)


def test_hint_and_undo_do_nothing_outside_the_beginner_level():
    assert easy().helpers_allowed
    for match in (versus(level=Level.MEDIUM), versus(level=Level.HARD), two()):
        assert not match.helpers_allowed
        assert match.hint() is None and match.hint_pos is None
        play_here(match, (1, 3))
        if match.phase is Phase.BOT_TURN:
            match.bot_move()
        turn = match.game.turn
        assert match.undo() is False
        assert match.game.turn == turn and match.undos_left == UNDOS_PER_GAME


# ---------------------------------------------------------------- undo

def test_undo_against_the_phone_goes_back_to_your_turn():
    match = easy()
    start = match.game.board
    play_here(match, (1, 3))
    match.bot_move()
    after_one_round = match.game.board
    play_here(match, match.game.board.empty_cells()[0])
    match.bot_move()
    match.hint()
    assert match.undo() and match.game.board == after_one_round   # one turn back, not all
    assert match.game.current is B and match.game.turn == 2
    assert match.undo() and match.game.board == start and match.game.turn == 0
    assert match.undos_left == UNDOS_PER_GAME - 2 and match.message == "Jogada desfeita."
    assert match.pending is None and match.hint_pos is None and match.last_flipped == ()


def test_undo_is_limited_per_game():
    match = easy()
    assert not match.undo()                   # nothing to undo yet
    assert match.message == "Não dá para desfazer agora."
    for _ in range(UNDOS_PER_GAME + 1):
        play_here(match, match.game.board.empty_cells()[0])
        match.bot_move()
        undone = match.undo()
    assert undone is False and match.undos_left == 0
    assert match.game.turn == 2


# ---------------------------------------------------------------- hint

def test_hint_points_to_an_empty_cell_and_clears_on_tap():
    match = easy()
    match.tap((0, 0))
    pos = match.hint()
    assert match.pending is None               # asking for a hint drops the selection
    assert pos in match.game.board.empty_cells() and match.hint_pos == pos
    assert match.message == "Dica: a casa verde vira bastante coisa."
    assert match.hint() == pos                # same position, same hint
    match.tap(pos)
    assert match.hint_pos is None


def test_hint_does_not_change_what_the_phone_will_play():
    """The hint uses its own random generator, so asking for one must not change the
    rest of the match (otherwise the same seed would give a different game)."""
    plain, hinted = easy(seed=3), easy(seed=3)
    hinted.hint()
    for match in (plain, hinted):
        play_here(match, (1, 3))
        match.bot_move()
    assert plain.game.board == hinted.game.board


# ---------------------------------------------------------------- end of the game

def test_winning_ends_the_game():
    match = with_board(versus(), ["BBBB", "BBBB", "BBBB", "OOO."])
    assert play_here(match, (3, 3)) == "played"
    assert match.is_over and match.phase is Phase.OVER
    assert match.game.winner is HUMAN_PLAYER and match.message == "Você venceu! 13 × 3"
    assert match.turn_label() == "Fim de jogo" and match.tap((0, 0)) == "ignored"
    assert match.hint() is None and match.bot_move() is None


def test_losing_to_the_phone():
    match = with_board(versus(), ["OOOO", "OOOO", "OOOO", "BBB."])
    play_here(match, (3, 3))
    assert match.is_over and match.result_text() == "O celular venceu desta vez."
    assert match.message == "O celular venceu desta vez. 4 × 12"


def test_a_tie():
    match = with_board(versus(), ["BBBB", "BBB.", "OOOO", "OOOO"])
    play_here(match, (1, 3))
    assert match.is_over and match.game.winner is None and match.result_text() == "Empate!"


def test_the_phone_can_end_the_game():
    match = with_board(versus(), ["BBBB", "BBBB", "OOOO", "O.O."])
    play_here(match, (3, 1))                  # you fill one of the two last cells...
    assert match.phase is Phase.BOT_TURN and not match.is_over
    result = match.bot_move()                 # ...and the phone fills the last one
    assert result.pos == (3, 3) and result.game_over
    assert match.is_over and match.message == f"{match.result_text()} {match.score_line()}"


def test_two_player_games_name_the_winner():
    match = with_board(two(), ["BBBB", "BBBB", "BBBB", "OOO."])
    play_here(match, (3, 3))
    assert match.result_text() == "Azul venceu!"


# ---------------------------------------------------------------- whole matches

def test_complete_matches_against_the_phone_always_finish():
    for level in Level:
        for math in (False, ALL_MATH):
            match = versus(size=5, math=math, level=level, seed=7)
            play_until_over(match, wrong_every=3 if math else 0)
            assert match.phase is Phase.OVER and match.game.over
            data = SaveData()
            assert record_game(data, match.setup, match.game.winner) in (
                "wins", "losses", "draws")


def test_complete_two_player_matches_always_finish():
    for size in (5, 7):
        match = two(size=size, math=True, seed=2)
        assert play_until_over(match, wrong_every=4) > 0
        assert match.result_text().endswith("venceu!")  # odd boards: no draw when full
