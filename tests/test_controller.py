import pytest

from blockwar.board import Board
from blockwar.bot import Level
from blockwar.controller import (BOT_PLAYER, HUMAN_PLAYER, UNDOS_PER_GAME, Match, Mode, Phase,
                                 Setup, blocks_word, record_summary, setup_from_save,
                                 store_setup)
from blockwar.game import Game
from blockwar.mathmode import ADD, DIV, MUL, OPERATIONS, SUB, MathSettings
from blockwar.models import DEFAULT_SIZE, Player
from blockwar.storage import SaveData

B, O = Player.BLUE, Player.ORANGE


MATH_ON = MathSettings(frozenset({ADD, SUB}))
ALL_MATH = MathSettings(frozenset(OPERATIONS), frozenset(range(1, 11)))


def math_settings(math) -> MathSettings:
    """`math=True` turns on simple sums; a `MathSettings` is used as it is."""
    if isinstance(math, MathSettings):
        return math
    return MATH_ON if math else MathSettings()


def two(size=5, math=False, seed=1) -> Match:
    return Match(Setup(mode=Mode.TWO, size=size, math=math_settings(math), seed=seed))


def versus(size=5, math=False, level=Level.MEDIUM, seed=1) -> Match:
    return Match(Setup(mode=Mode.BOT, size=size, math=math_settings(math), bot_level=level,
                       seed=seed))


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


# ---------------------------------------------------------------- menu choices

def test_default_setup():
    setup = Setup()
    assert setup.mode is Mode.BOT and setup.size == DEFAULT_SIZE
    assert setup.bot_level is Level.MEDIUM and setup.math == MathSettings()
    assert not setup.math.enabled


def test_record_key_exists_only_against_the_phone():
    assert Setup(Mode.BOT, 7, Level.HARD, MATH_ON).record_key == "7:dificil:1"
    assert Setup(Mode.BOT, 5, Level.EASY).record_key == "5:facil:0"
    assert Setup(Mode.TWO).record_key is None


def test_different_choices_have_different_record_keys():
    keys = {Setup(Mode.BOT, size, level, math).record_key
            for size in (5, 7) for level in Level for math in (MathSettings(), MATH_ON)}
    assert len(keys) == 2 * 3 * 2


def test_records_only_care_whether_math_is_on_not_which_math():
    """Otherwise every tweak of the tables would start a new, empty record."""
    assert Setup(math=MATH_ON).record_key == Setup(math=ALL_MATH).record_key


def test_setup_is_saved_and_restored():
    data = SaveData()
    setup = Setup(Mode.TWO, 5, Level.HARD, ALL_MATH)
    store_setup(data, setup)
    again = setup_from_save(data)
    assert (again.mode, again.bot_level, again.math) == (Mode.TWO, Level.HARD, ALL_MATH)


def test_the_board_size_is_not_saved():
    """It comes from the screen of each device (phone ~7x7, tablet up to 14x14)."""
    data = SaveData()
    store_setup(data, Setup(size=12))
    assert not hasattr(data, "size")
    assert setup_from_save(data).size == DEFAULT_SIZE


def test_setup_from_a_default_save_is_the_default_setup():
    setup = setup_from_save(SaveData())
    assert (setup.mode, setup.size, setup.bot_level, setup.math) == (
        Mode.BOT, DEFAULT_SIZE, Level.MEDIUM, MathSettings())


def test_record_summary_text():
    data = SaveData(records={"7:medio:0": {"wins": 3, "losses": 1, "draws": 0}})
    assert record_summary(data, Setup()) == "Neste nível: 3 vitórias, 1 derrotas, 0 empates"
    assert record_summary(data, Setup(mode=Mode.TWO)) == ""


def test_record_summary_is_empty_before_the_first_game_at_that_level():
    """Nothing to brag about yet: no point cluttering a first-time player's menu."""
    assert record_summary(SaveData(), Setup()) == ""
    data = SaveData(records={"7:medio:0": {"wins": 0, "losses": 0, "draws": 1}})
    assert record_summary(data, Setup()) != ""  # but a single draw is still shown


@pytest.mark.parametrize("count, text", [(0, "0 blocos"), (1, "1 bloco"), (2, "2 blocos")])
def test_blocks_word(count, text):
    assert blocks_word(count) == text


# ---------------------------------------------------------------- starting

def test_a_new_match_waits_for_the_first_tap():
    match = two()
    assert match.phase is Phase.CHOOSING and match.game.turn == 0
    assert match.pending is None and match.question is None and match.hint_pos is None
    assert match.undos_left == UNDOS_PER_GAME and not match.is_over
    assert match.message == "Toque numa casa para ver o que vira."
    assert match.score_line() == "2 × 2" and match.preview_cells() == ()


def test_math_mode_explains_the_question_at_the_start():
    assert "responda a conta" in two(math=True).message


@pytest.mark.parametrize("size", [5, 7])
def test_the_match_uses_the_chosen_board_size(size):
    assert two(size=size).game.size == size


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
    assert match.tap((2, 2)) == "ignored"
    assert match.tap((9, 9)) == "ignored"
    assert match.tap((-1, 0)) == "ignored"
    assert match.pending is None


def test_a_tap_on_an_occupied_cell_keeps_the_current_selection():
    match = two()
    match.tap((1, 3))
    assert match.tap((2, 2)) == "ignored"
    assert match.pending == (1, 3)


def test_confirm_plays_the_selected_cell():
    match = two()
    match.tap((1, 3))
    assert match.confirm() == "played" and match.game.board.get((1, 3)) is B


def test_actions_out_of_phase_are_ignored():
    match = two()
    assert match.confirm() == "ignored"      # nothing selected
    assert match.answer(1) == "ignored"      # no question
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
    assert result is not None and result.player is BOT_PLAYER and not result.skipped
    assert match.game.board.get(result.pos) is BOT_PLAYER
    assert match.phase is Phase.CHOOSING and match.game.current is HUMAN_PLAYER
    assert match.game.turn == 2 and match.turn_label() == "Sua vez"
    assert match.message.startswith("Celular ")


def test_bot_move_only_plays_once_per_turn():
    match = versus()
    play_here(match, (1, 3))
    assert match.bot_move() is not None
    assert match.bot_move() is None and match.game.turn == 2


def test_names_depend_on_the_mode():
    assert versus().name(B) == "Você" and versus().name(O) == "Celular"
    assert two().name(B) == "Azul" and two().name(O) == "Laranja"
    assert two().turn_label() == "Vez do Azul ●" and versus().turn_label() == "Sua vez"


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


def test_answering_twice_is_ignored():
    match = two(math=True)
    play_here(match, (1, 3))
    answer_right(match)
    assert match.answer(0) == "ignored" and match.game.turn == 1


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


@pytest.mark.parametrize("op, symbol", [(ADD, "+"), (SUB, "−"), (MUL, "×"), (DIV, "÷")])
def test_questions_follow_the_chosen_operation(op, symbol):
    match = two(math=MathSettings(frozenset({op}), frozenset({7})))
    for _ in range(4):
        play_here(match, match.game.board.empty_cells()[0])
        assert f" {symbol} " in match.question.text and len(match.question.choices) == 4
        answer_right(match)


def test_wrong_answer_against_the_phone_hands_the_turn_to_the_bot():
    match = versus(math=True)
    play_here(match, (1, 3))
    assert answer_wrong(match) == "skipped"
    assert match.message.endswith("Você perdeu a vez.")
    assert match.phase is Phase.BOT_TURN
    assert match.bot_move() is not None and match.phase is Phase.CHOOSING


def test_the_bot_never_has_to_answer_questions():
    match = versus(math=ALL_MATH)
    play_here(match, (1, 3))
    answer_right(match)
    assert match.phase is Phase.BOT_TURN
    match.bot_move()
    assert match.question is None and match.phase is Phase.CHOOSING


# ---------------------------------------------------------------- beginner helpers

def easy(**kwargs) -> Match:
    """Against the phone on Fácil: the only level where Dica and Desfazer work."""
    return versus(level=Level.EASY, **kwargs)


def test_hint_and_undo_are_only_for_the_beginner_level():
    assert easy().helpers_allowed
    for match in (versus(level=Level.MEDIUM), versus(level=Level.HARD), two()):
        assert not match.helpers_allowed


@pytest.mark.parametrize("match", [
    pytest.param(lambda: versus(level=Level.MEDIUM), id="medium"),
    pytest.param(lambda: versus(level=Level.HARD), id="hard"),
    pytest.param(lambda: two(), id="two-players"),
])
def test_hint_and_undo_do_nothing_outside_the_beginner_level(match):
    match = match()
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
    assert match.undo() and match.game.board == start
    assert match.game.current is B and match.game.turn == 0
    assert match.undos_left == UNDOS_PER_GAME - 1 and match.message == "Jogada desfeita."


def test_undo_against_the_phone_after_a_wrong_answer():
    match = easy(math=True)
    start = match.game.board
    play_here(match, (1, 3))
    answer_wrong(match)
    match.bot_move()
    assert match.undo() and match.game.board == start and match.game.turn == 0
    assert match.phase is Phase.CHOOSING and match.game.current is HUMAN_PLAYER


def test_undo_is_not_allowed_while_the_phone_is_thinking():
    match = easy()
    play_here(match, (1, 3))
    assert match.phase is Phase.BOT_TURN and match.undo() is False


def test_undo_is_limited_per_game():
    match = easy()
    assert not match.undo()                   # nothing to undo yet
    for _ in range(UNDOS_PER_GAME + 1):
        play_here(match, match.game.board.empty_cells()[0])
        match.bot_move()
        undone = match.undo()
    assert undone is False and match.undos_left == 0
    assert match.game.turn == 2


def test_undo_clears_selection_hint_and_flash():
    match = easy()
    play_here(match, (1, 3))
    match.bot_move()
    match.hint()
    assert match.undo()
    assert match.pending is None and match.hint_pos is None and match.last_flipped == ()


def test_undo_is_not_allowed_after_the_game_is_over():
    match = with_board(easy(), ["BBBB", "BBBB", "BBBB", "OOO."])
    play_here(match, (3, 3))
    assert match.is_over and match.undo() is False


# ---------------------------------------------------------------- hint

def test_hint_points_to_an_empty_cell_and_clears_on_tap():
    match = easy()
    pos = match.hint()
    assert pos in match.game.board.empty_cells() and match.hint_pos == pos
    assert match.message == "Dica: a casa verde vira bastante coisa."
    assert match.hint() == pos                # same position, same hint
    match.tap(pos)
    assert match.hint_pos is None


def test_hint_suggests_a_capture_and_clears_the_selection():
    match = easy()
    match.tap((0, 0))
    pos = match.hint()
    assert match.pending is None
    assert len(match.game.preview(pos)) == max(
        len(match.game.preview(p)) for p in match.game.board.empty_cells())


def test_hint_does_not_change_what_the_phone_will_play():
    """The hint uses its own random generator, so asking for one must not change the
    rest of the match (otherwise the same seed would give a different game)."""
    plain, hinted = easy(seed=3), easy(seed=3)
    hinted.hint()
    for match in (plain, hinted):
        play_here(match, (1, 3))
        match.bot_move()
    assert plain.game.board == hinted.game.board


def test_hint_is_ignored_outside_your_turn():
    match = easy()
    play_here(match, (1, 3))
    assert match.hint() is None


# ---------------------------------------------------------------- end and records

def test_winning_ends_the_game_and_records_a_win_once():
    match = with_board(versus(), ["BBBB", "BBBB", "BBBB", "OOO."])
    assert play_here(match, (3, 3)) == "played"
    assert match.is_over and match.phase is Phase.OVER
    assert match.message == "Você venceu! 13 × 3"
    data = SaveData()
    assert match.record(data) == "wins" and match.record(data) is None
    assert data.records["5:medio:0"]["wins"] == 1 and data.games_played == 1
    assert match.record_text(data).startswith("Neste nível: 1 vitórias")
    assert match.turn_label() == "Fim de jogo" and match.tap((0, 0)) == "ignored"
    assert match.hint() is None and match.bot_move() is None


def test_losing_is_recorded():
    match = with_board(versus(), ["OOOO", "OOOO", "OOOO", "BBB."])
    play_here(match, (3, 3))
    assert match.is_over and match.result_text() == "O celular venceu desta vez."
    assert match.message == "O celular venceu desta vez. 4 × 12"
    data = SaveData()
    assert match.record(data) == "losses"
    assert data.records["5:medio:0"] == {"wins": 0, "losses": 1, "draws": 0}


def test_a_tie_is_recorded_as_a_draw():
    match = with_board(versus(), ["BBBB", "BBB.", "OOOO", "OOOO"])
    play_here(match, (1, 3))
    assert match.is_over and match.result_text() == "Empate!"
    assert match.record(SaveData()) == "draws"


def test_the_phone_can_end_the_game():
    match = with_board(versus(), ["BBBB", "BBBB", "OOOO", "O.O."])
    play_here(match, (3, 1))                  # you fill one of the two last cells...
    assert match.phase is Phase.BOT_TURN and not match.is_over
    result = match.bot_move()                 # ...and the phone fills the last one
    assert result.pos == (3, 3) and result.game_over
    assert match.is_over and match.message == f"{match.result_text()} {match.score_line()}"
    assert match.record(SaveData()) in ("wins", "losses", "draws")


def test_a_game_in_progress_is_not_recorded():
    match = versus()
    data = SaveData()
    assert match.record(data) is None and data.games_played == 0


def test_records_use_the_setup_key():
    match = with_board(versus(level=Level.HARD, math=True), ["BBBB", "BBBB", "BBBB", "OOO."])
    play_here(match, (3, 3))
    answer_right(match)
    data = SaveData()
    match.record(data)
    assert list(data.records) == ["5:dificil:1"]  # size:bot level:math on


def test_two_player_games_are_not_recorded_and_name_the_winner():
    match = with_board(two(), ["BBBB", "BBBB", "BBBB", "OOO."])
    play_here(match, (3, 3))
    assert match.result_text() == "Azul venceu!"
    assert match.record(SaveData()) is None and match.record_text(SaveData()) == ""


# ---------------------------------------------------------------- whole matches

@pytest.mark.parametrize("level", list(Level))
@pytest.mark.parametrize("math", [False, ALL_MATH])
def test_complete_matches_against_the_phone_always_finish(level, math):
    match = versus(size=5, math=math, level=level, seed=7)
    play_until_over(match, wrong_every=3 if math else 0)
    assert match.phase is Phase.OVER and match.game.over
    data = SaveData()
    assert match.record(data) in ("wins", "losses", "draws")
    assert data.games_played == 1


@pytest.mark.parametrize("size", [5, 7])
def test_complete_two_player_matches_always_finish(size):
    match = two(size=size, math=True, seed=2)
    turns = play_until_over(match, wrong_every=4)
    assert match.is_over and turns > 0
    assert match.result_text().endswith("venceu!")  # odd boards: no draw when full
