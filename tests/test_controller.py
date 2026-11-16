from blockwar.board import Board
from blockwar.bot import Level
from blockwar.controller import (BOT_PLAYER, UNDOS_PER_GAME, Match, Mode, Phase, Setup,
                                 record_summary, setup_from_save, store_setup)
from blockwar.game import Game
from blockwar.models import Player
from blockwar.storage import SaveData

B, O = Player.BLUE, Player.ORANGE


def two(size=5, math=0, seed=1) -> Match:
    return Match(Setup(mode=Mode.TWO, size=size, math_level=math, seed=seed))


def versus(size=5, math=0, level=Level.MEDIUM, seed=1) -> Match:
    return Match(Setup(mode=Mode.BOT, size=size, math_level=math, bot_level=level, seed=seed))


def with_board(match: Match, lines) -> Match:
    match.game = Game(board=Board.from_text(lines))
    return match


# ---------------------------------------------------------------- escolhas do menu

def test_record_key_exists_only_against_the_phone():
    assert Setup(Mode.BOT, 7, Level.HARD, 2).record_key == "7:dificil:2"
    assert Setup(Mode.TWO).record_key is None


def test_setup_is_saved_and_restored():
    data = SaveData()
    setup = Setup(Mode.TWO, 5, Level.HARD, 3)
    store_setup(data, setup)
    again = setup_from_save(data)
    assert (again.mode, again.size, again.bot_level, again.math_level) == (Mode.TWO, 5,
                                                                          Level.HARD, 3)


def test_record_summary_text():
    data = SaveData(records={"7:medio:0": {"wins": 3, "losses": 1, "draws": 0}})
    assert record_summary(data, Setup()) == "Neste nível: 3 vitórias, 1 derrotas, 0 empates"
    assert record_summary(data, Setup(mode=Mode.TWO)) == ""


# ---------------------------------------------------------------- toques

def test_first_tap_previews_and_second_tap_plays():
    match = two()
    assert match.tap((1, 3)) == "selected"
    assert match.pending == (1, 3) and match.preview_cells() == ((1, 2),)
    assert match.message == "Vira 1 bloco. Toque de novo para jogar."
    assert match.tap((1, 3)) == "played"
    assert match.game.current is O and match.pending is None
    assert match.last_flipped == ((1, 2),) and match.message == "Azul virou 1 bloco."
    assert match.phase is Phase.CHOOSING


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
    assert match.pending is None


def test_actions_out_of_phase_are_ignored():
    match = two()
    assert match.confirm() == "ignored"      # nada selecionado
    assert match.answer(1) == "ignored"      # sem pergunta
    assert match.bot_move() is None          # não é a vez do celular


# ---------------------------------------------------------------- celular

def test_against_the_phone_the_bot_answers_after_your_move():
    match = versus()
    match.tap((1, 3))
    assert match.tap((1, 3)) == "played"
    assert match.phase is Phase.BOT_TURN and match.turn_label() == "Vez do celular"
    assert match.tap((0, 0)) == "ignored"    # você não joga na vez do celular
    result = match.bot_move()
    assert result is not None and result.player is BOT_PLAYER
    assert match.phase is Phase.CHOOSING and match.game.current is B
    assert match.game.turn == 2 and match.turn_label() == "Sua vez"


def test_names_depend_on_the_mode():
    assert versus().name(B) == "Você" and versus().name(O) == "Celular"
    assert two().name(B) == "Azul" and two().turn_label() == "Vez do Azul ●"


# ---------------------------------------------------------------- contas

def test_math_mode_asks_a_question_before_placing():
    match = two(math=1)
    match.tap((1, 3))
    assert match.tap((1, 3)) == "question"
    assert match.phase is Phase.QUESTION and match.question is not None
    assert match.game.turn == 0               # o bloco só entra depois de acertar
    assert match.tap((0, 0)) == "ignored"
    assert match.answer(match.question.answer) == "played"
    assert match.game.turn == 1 and match.game.board.get((1, 3)) is B
    assert match.question is None and match.phase is Phase.CHOOSING


def test_wrong_answer_loses_the_turn_and_places_nothing():
    match = two(math=1)
    board = match.game.board
    match.tap((1, 3))
    match.tap((1, 3))
    right = match.question.answer
    wrong = next(c for c in match.question.choices if c != right)
    assert match.answer(wrong) == "skipped"
    assert match.game.board == board and match.game.current is O and match.game.turn == 1
    assert match.message.startswith(f"Errou! A resposta era {right}.")
    assert match.pending is None and match.question is None


def test_wrong_answer_against_the_phone_hands_the_turn_to_the_bot():
    match = versus(math=1)
    match.tap((1, 3))
    match.tap((1, 3))
    wrong = next(c for c in match.question.choices if c != match.question.answer)
    match.answer(wrong)
    assert match.phase is Phase.BOT_TURN
    assert match.bot_move() is not None


# ---------------------------------------------------------------- desfazer e dica

def test_undo_against_the_phone_goes_back_to_your_turn():
    match = versus()
    start = match.game.board
    match.tap((1, 3))
    match.tap((1, 3))
    match.bot_move()
    assert match.undo() and match.game.board == start
    assert match.game.current is B and match.game.turn == 0
    assert match.undos_left == UNDOS_PER_GAME - 1 and match.message == "Jogada desfeita."


def test_undo_two_players_goes_back_one_turn_and_is_limited():
    match = two()
    assert not match.undo()                   # nada para desfazer ainda
    for _ in range(UNDOS_PER_GAME + 1):
        empty = match.game.board.empty_cells()[0]
        match.tap(empty)
        match.tap(empty)
        undone = match.undo()
    assert undone is False and match.undos_left == 0
    assert match.game.turn == 1


def test_hint_points_to_an_empty_cell_and_clears_on_tap():
    match = two()
    pos = match.hint()
    assert pos in match.game.board.empty_cells() and match.hint_pos == pos
    assert match.hint() == pos                # mesma posição, mesma dica
    match.tap(pos)
    assert match.hint_pos is None


def test_hint_is_ignored_outside_your_turn():
    match = versus()
    match.tap((1, 3))
    match.tap((1, 3))
    assert match.hint() is None


# ---------------------------------------------------------------- fim e recordes

def test_winning_ends_the_game_and_records_a_win_once():
    match = with_board(versus(), ["BBBB", "BBBB", "BBBB", "OOO."])
    match.tap((3, 3))
    assert match.tap((3, 3)) == "played"
    assert match.is_over and match.phase is Phase.OVER
    assert match.message == "Você venceu! 13 × 3"
    data = SaveData()
    assert match.record(data) == "wins" and match.record(data) is None
    assert data.records["5:medio:0"]["wins"] == 1 and data.games_played == 1
    assert match.record_text(data).startswith("Neste nível: 1 vitórias")
    assert match.turn_label() == "Fim de jogo" and match.tap((0, 0)) == "ignored"


def test_losing_is_recorded():
    match = with_board(versus(), ["OOOO", "OOOO", "OOOO", "BBB."])
    match.tap((3, 3))
    match.tap((3, 3))
    assert match.is_over and match.result_text() == "O celular venceu desta vez."
    assert match.message == "O celular venceu desta vez. 4 × 12"
    data = SaveData()
    assert match.record(data) == "losses"
    assert data.records["5:medio:0"] == {"wins": 0, "losses": 1, "draws": 0}


def test_a_tie_is_recorded_as_a_draw():
    match = with_board(versus(), ["BBBB", "BBB.", "OOOO", "OOOO"])
    match.tap((1, 3))
    match.tap((1, 3))
    assert match.is_over and match.result_text() == "Empate!"
    assert match.record(SaveData()) == "draws"


def test_two_player_games_are_not_recorded_and_name_the_winner():
    match = with_board(two(), ["BBBB", "BBBB", "BBBB", "OOO."])
    match.tap((3, 3))
    match.tap((3, 3))
    assert match.result_text() == "Azul venceu!"
    assert match.record(SaveData()) is None and match.record_text(SaveData()) == ""
