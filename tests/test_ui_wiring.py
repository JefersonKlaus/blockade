"""Testa a ligação da interface usando um 'Flet de mentira'.

Isto NÃO valida a aparência nem a API real do Flet: só confere que a lógica da tela
(menu, toques, perguntas, vez do celular, recordes) está ligada ao jogo.
"""
import asyncio
import importlib
import sys
import types
from types import SimpleNamespace

import pytest

from blockwar import theme
from blockwar.board import Board
from blockwar.bot import Level
from blockwar.controller import Mode, Phase
from blockwar.game import Game
from blockwar.storage import SaveData

ENUM_NAMES = {"FontWeight", "CrossAxisAlignment", "MainAxisAlignment", "ScrollMode", "ThemeMode"}


class _Enum:
    def __getattr__(self, name):
        return name


class Control:
    def __init__(self, *args, **kwargs):
        self.value = args[0] if args and isinstance(args[0], str) else None
        self.controls = []
        self.visible = True
        self.disabled = False
        self.__dict__.update(kwargs)


class FakeFlet(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Enum() if name in ENUM_NAMES else Control


class FakePage:
    def __init__(self):
        self.added, self.updates = [], 0
        self.window = SimpleNamespace()

    def add(self, *controls):
        self.added.extend(controls)

    def clean(self):
        self.added.clear()

    def update(self):
        self.updates += 1


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def ui(monkeypatch):
    monkeypatch.setitem(sys.modules, "flet", FakeFlet("flet"))
    monkeypatch.delitem(sys.modules, "blockwar.ui", raising=False)
    module = importlib.import_module("blockwar.ui")
    saves = []
    monkeypatch.setattr(module, "load_save", lambda: SaveData())
    monkeypatch.setattr(module, "save_save", lambda data: saves.append(data.games_played) or True)
    monkeypatch.setattr(module, "FLIP_DELAY", 0)
    monkeypatch.setattr(module, "BOT_DELAY", 0)
    module.saves = saves
    yield module
    sys.modules.pop("blockwar.ui", None)


@pytest.fixture
def app(ui):
    instance = ui.BlocksApp(FakePage())
    instance.setup.size = 5
    instance.setup.seed = 1
    return instance


def start(app, mode=Mode.TWO, math=0, level=Level.MEDIUM):
    app.setup.mode, app.setup.math_level, app.setup.bot_level = mode, math, level
    app.on_play(None)
    return app


def painted(app):
    return sum(1 for row in app.cells for cell in row if cell.bgcolor != theme.EMPTY)


def tap_twice(app, pos):
    run(app.on_cell(pos))
    run(app.on_cell(pos))


# ---------------------------------------------------------------- menu

def test_menu_shows_title_choices_and_play_button(app):
    app.show_menu()
    root = app.page.added[0]
    texts = [c.value for c in root.controls if getattr(c, "value", None)]
    assert "Guerra dos Blocos" in texts
    buttons = [c for c in root.controls if c.value == "Jogar"]
    assert len(buttons) == 1 and buttons[0].on_click == app.on_play
    assert any("Como jogar" in t for t in texts)


def test_menu_hides_the_bot_level_in_two_player_mode(app):
    app.setup.mode = Mode.TWO
    app.show_menu()
    titles = [c.controls[0].value for c in app.page.added[0].controls
              if c.controls and c.controls[0].value]
    assert "Nível do celular" not in titles
    app.setup.mode = Mode.BOT
    app.show_menu()
    titles = [c.controls[0].value for c in app.page.added[0].controls
              if c.controls and c.controls[0].value]
    assert "Nível do celular" in titles


def test_picking_an_option_updates_setup_saves_and_redraws(app, ui):
    app._pick("size")(7)
    assert app.setup.size == 7 and app.save.size == 7
    app._pick("math_level")(2)
    assert app.save.math_level == 2 and len(ui.saves) == 2
    app._pick("bot_level")(Level.HARD)
    assert app.save.bot_level == "dificil"


# ---------------------------------------------------------------- partida

def test_starting_a_game_builds_the_board_and_paints_the_four_blocks(app):
    start(app)
    assert (len(app.cells), len(app.cells[0])) == (5, 5)
    assert painted(app) == 4
    assert app.turn_text.value == "Vez do Azul ●"
    assert app.blue_text.value == "● Azul: 2" and app.orange_text.value == "▲ Laranja: 2"
    assert app.bar_blue.width == app.bar_orange.width == app.board_width // 2
    assert app.btn_undo.disabled is True and app.btn_hint.disabled is False


def test_first_tap_previews_second_tap_plays(app):
    start(app)
    run(app.on_cell((1, 3)))
    assert app.cells[1][3].bgcolor == theme.BLUE_TINT       # casa escolhida
    assert app.cells[1][2].bgcolor == theme.FLIP_PREVIEW    # o que vai virar
    assert app.message.value == "Vira 1 bloco. Toque de novo para jogar."
    run(app.on_cell((1, 3)))
    assert app.match.game.turn == 1 and app.busy is False
    assert app.cells[1][2].bgcolor == theme.BLUE            # virou azul
    assert app.cells[1][3].bgcolor == theme.BLUE_LAST       # última jogada, mais escura
    assert app.turn_text.value == "Vez do Laranja ▲" and app.btn_undo.disabled is False


def test_busy_app_ignores_taps(app):
    start(app)
    app.busy = True
    run(app.on_cell((1, 3)))
    assert app.match.pending is None


def test_against_the_phone_the_bot_replies_automatically(app):
    start(app, mode=Mode.BOT)
    tap_twice(app, (1, 3))
    assert app.match.game.turn == 2 and app.match.phase is Phase.CHOOSING
    assert app.turn_text.value == "Sua vez"
    assert app.busy is False and app.flash == set()


def test_math_mode_shows_the_question_and_a_correct_answer_places_the_block(app):
    start(app, math=1)
    tap_twice(app, (1, 3))
    assert app.question_box.visible is True
    text, answers = app.question_box.controls
    assert text.value == app.match.question.text and len(answers.controls) == 4
    right = next(b for b in answers.controls if b.value == str(app.match.question.answer))
    run(right.on_click(None))
    assert app.match.game.board.get((1, 3)).letter == "B"
    assert app.question_box.visible is False


def test_math_mode_wrong_answer_skips_the_turn(app):
    start(app, math=1)
    tap_twice(app, (1, 3))
    answers = app.question_box.controls[1].controls
    wrong = next(b for b in answers if b.value != str(app.match.question.answer))
    run(wrong.on_click(None))
    assert app.match.game.turn == 1 and app.match.game.board.get((1, 3)) is None
    assert app.message.value.startswith("Errou!")


def test_hint_marks_a_cell_and_undo_reverts(app):
    start(app)
    app.on_hint(None)
    hint = app.match.hint_pos
    assert app.cells[hint[0]][hint[1]].bgcolor == theme.HINT
    tap_twice(app, (1, 3))
    app.on_undo(None)
    assert app.match.game.turn == 0 and app.message.value == "Jogada desfeita."
    assert app.cells[1][3].bgcolor == theme.EMPTY
    app.on_undo(None)
    assert app.message.value == "Não dá para desfazer agora."


# ---------------------------------------------------------------- fim e recordes

def finish_game(app, mode=Mode.BOT):
    start(app, mode=mode)
    app.match.game = Game(board=Board.from_text(
        ["BBBBB", "BBBBB", "BBBBB", "BBBBB", "OOOO."]))
    tap_twice(app, (4, 4))


def test_game_over_shows_the_result_and_records_a_win(app, ui):
    finish_game(app)
    assert app.match.is_over
    assert app.end_box.visible is True
    assert app.end_title.value == "Você venceu! 21 × 4"
    assert app.end_record.value.startswith("Neste nível: 1 vitórias")
    assert app.save.records["5:medio:0"]["wins"] == 1
    assert ui.saves[-1] == 1                      # o recorde foi gravado em disco
    assert app.btn_hint.disabled and app.btn_undo.disabled


def test_two_player_game_over_is_not_recorded(app, ui):
    finish_game(app, mode=Mode.TWO)
    assert app.end_title.value == "Azul venceu! 21 × 4" and app.end_record.value == ""
    assert app.save.records == {} and ui.saves == []


def test_play_again_and_menu_buttons(app):
    finish_game(app)
    app.on_new(None)
    assert app.match.game.turn == 0 and app.end_box.visible is False
    app.on_menu(None)
    assert app.page.added[0].controls[0].value == "Guerra dos Blocos"


def test_main_builds_the_menu_and_sets_the_window(ui):
    page = FakePage()
    run(ui.main(page))
    assert page.title == "Guerra dos Blocos" and page.window.width == 430
    assert len(page.added) == 1
