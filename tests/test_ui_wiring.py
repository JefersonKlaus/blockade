"""Tests the wiring of the Flet screens (menu, taps, questions, bot turn, records).

Every test runs twice:

* ``fake`` - with a tiny stand-in for Flet that accepts anything. It runs even when
  Flet is not installed and checks only the logic of the screen.
* ``real`` - with the real Flet control classes. Real controls reject unknown
  arguments and enum values, so this catches API mistakes (e.g. after a Flet upgrade
  or a typo in ui.py). It is skipped when Flet is not installed.

Neither variant opens a window or checks how the screen *looks*. Use ``flet run`` for
that (see the README).

Tests find controls by their text instead of by their position in the tree, so they
keep working when the layout changes (e.g. wrapping a column in a container).
"""
from __future__ import annotations

import asyncio
import importlib
import re
import sys
import types
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from blockwar import theme
from blockwar.board import Board
from blockwar.bot import Level
from blockwar.controller import Mode, Phase
from blockwar.game import Game
from blockwar.mathmode import ADD, MUL, SUB, MathSettings
from blockwar.storage import SaveData

# ---------------------------------------------------------------- fake Flet

ENUM_NAMES = {"FontWeight", "CrossAxisAlignment", "MainAxisAlignment", "ScrollMode",
              "ThemeMode", "TextAlign", "Icons", "DeviceOrientation"}


class _Enum:
    def __getattr__(self, name):
        return name


class Control:
    """Stores whatever it receives. Like real Flet, the first positional argument is
    the text: `value` for Text and `content` for buttons (here: both)."""

    def __init__(self, *args, **kwargs):
        self.content = args[0] if args and isinstance(args[0], str) else None
        self.controls = []
        self.visible = True
        self.disabled = False
        if "value" in kwargs:
            self.value = kwargs.pop("value")
        self.__dict__.update(kwargs)

    # One field behind both names, so changing a button's `content` (real Flet) or a
    # text's `value` never leaves a stale copy in the other one.
    @property
    def value(self):
        return self.content

    @value.setter
    def value(self, text):
        self.content = text


class FakeFlet(types.ModuleType):
    """`ft.<Anything>` is a Control subclass named after it (so `ft.Button` and
    `ft.OutlinedButton` can be told apart); enums return their member names."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name in ENUM_NAMES:
            return _Enum()
        cls = type(name, (Control,), {})
        setattr(self, name, cls)
        return cls


class FakePage:
    """Just enough of `ft.Page` for ui.py: a list of controls, update counting and a
    screen size. The default 290 px wide screen fits exactly a 5x5 board, which keeps
    the positions in the tests easy to follow."""

    def __init__(self, width=290, height=None, padding=12):
        self.controls: list[Any] = []
        self.dialogs: list[Any] = []      # open dialogs (the tutorial), like Flet's stack
        self.updates = 0
        self.window = SimpleNamespace()
        self.width, self.height, self.padding = width, height, padding

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None

    def add(self, *controls):
        self.controls.extend(controls)

    def clean(self):
        self.controls.clear()

    def update(self):
        self.updates += 1


# ---------------------------------------------------------------- helpers

def run(coro):
    return asyncio.run(coro)


def label(control) -> str | None:
    """The visible text of a Text (`value`) or a button (`content`)."""
    for attr in ("value", "content"):
        value = getattr(control, attr, None)
        if isinstance(value, str):
            return value
    return None


def walk(control) -> Iterator[Any]:
    """Every control in the tree below (and including) `control`, in screen order (a
    dialog's title, then its content, then its action buttons)."""
    yield control
    for attr in ("title", "content"):
        child = getattr(control, attr, None)
        if child is not None and not isinstance(child, (str, int, float)):
            yield from walk(child)
    for attr in ("controls", "actions"):
        for child in getattr(control, attr, None) or []:
            yield from walk(child)


def screen(app) -> list[Any]:
    """Everything on the page, plus any open dialog (drawn on top of the page)."""
    return [c for root in [*app.page.controls, *app.page.dialogs] for c in walk(root)]


def dialog(app):
    assert len(app.page.dialogs) == 1, "expected exactly one open dialog"
    return app.page.dialogs[0]


def dialog_texts(app) -> list[str]:
    return [text for c in walk(dialog(app)) if (text := label(c))]


def texts(app) -> list[str]:
    return [text for c in screen(app) if (text := label(c))]


def shows(control, text: str) -> bool:
    """Whether `text` labels `control` itself (a button) or one of its children (a menu
    card, where the icon and the word are two separate `Text` controls inside it)."""
    return any(label(c) == text for c in walk(control))


def clickable(app, text: str):
    """The single clickable control showing `text`, directly or in a child control."""
    found = [c for c in screen(app) if getattr(c, "on_click", None) and shows(c, text)]
    assert len(found) == 1, f"expected one {text!r} button, found {len(found)}"
    return found[0]


def click(app, text: str) -> None:
    result = clickable(app, text).on_click(None)
    if asyncio.iscoroutine(result):
        run(result)


def option(app, section: str, text: str):
    """The button `text` inside the menu section titled `section` (some labels, like
    "Difícil", exist in more than one section)."""
    for container in screen(app):
        children = getattr(container, "controls", None) or []
        if any(label(child) == section for child in children):
            found = [c for c in walk(container)
                     if getattr(c, "on_click", None) and shows(c, text)]
            assert len(found) == 1, f"expected one {text!r} in {section!r}"
            return found[0]
    raise AssertionError(f"menu section {section!r} not found")


def is_highlighted(control) -> bool:
    """Whether a card or button is shown as chosen: chosen cards get a border (see
    `theme.card_look` / `theme.level_look`); the math button turns blue when on."""
    return (getattr(control, "border", None) is not None
            or getattr(control, "bgcolor", None) == theme.CARD_SELECTED)


def painted(app) -> int:
    return sum(1 for row in app.cells for cell in row if cell.bgcolor != theme.EMPTY)


def tap_twice(app, pos) -> None:
    run(app.on_cell(pos))
    run(app.on_cell(pos))


# ---------------------------------------------------------------- fixtures

@pytest.fixture(params=["fake", "real"])
def ui(request, monkeypatch):
    """The `blockwar.ui` module, imported against the fake or the real Flet."""
    if request.param == "fake":
        monkeypatch.setitem(sys.modules, "flet", FakeFlet("flet"))
    else:
        pytest.importorskip("flet", reason="real Flet is not installed")
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
    instance = ui.BlocksApp(FakePage())   # a screen that fits a 5x5 board
    instance.setup.seed = 1
    return instance


MATH_ON = MathSettings(frozenset({ADD, SUB}))
MATH_BUTTON = "Praticar matemática"
# Anything that is a picture rather than a letter, digit, sign or game symbol (● ▲ ⬇).
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def start(app, mode=Mode.TWO, math=False, level=Level.MEDIUM):
    """Start a game the way a child does: Jogar! -> tutorial window -> Entendi!"""
    app.setup.mode, app.setup.bot_level = mode, level
    app.setup.math = math if isinstance(math, MathSettings) else (
        MATH_ON if math else MathSettings())
    app.on_play(None)
    assert app.screen == "partida" and app.tutorial_open
    app.on_start_game(None)
    assert not app.tutorial_open and app.page.dialogs == []
    return app


def math_button(app):
    found = [c for c in screen(app) if (label(c) or "").startswith(MATH_BUTTON)
             and getattr(c, "on_click", None)]
    assert len(found) == 1
    return found[0]


def open_math_page(app):
    app.show_menu()
    math_button(app).on_click(None)
    assert app.screen == "contas"


def symbol(app, sign: str):
    """The big card of one operation on the math page (+ − × ÷)."""
    return clickable(app, sign)


def buttons_in_order(app) -> list[str]:
    return [label(c) or next((label(d) for d in walk(c) if label(d)), "")
            for c in screen(app) if getattr(c, "on_click", None)]


def centered_group(app):
    """The choices of a menu screen: centered in the space between the top and Play."""
    root = app.page.controls[0]
    group = root.controls[-2]
    assert group.expand is True
    assert str(group.alignment).endswith("CENTER")
    return group


def play_slot(app):
    """The bottom part of a menu screen: only the Play button, near the fingers."""
    slot = app.page.controls[0].controls[-1]
    assert label(slot.content) == "Jogar!"
    return slot


def level_card(app, name: str):
    return option(app, "Quão esperto é o celular?", name)


# ---------------------------------------------------------------- menu

def test_menu_starts_with_the_app_icon_and_name(app):
    app.show_menu()
    header = app.page.controls[0].controls[0]
    parts = list(walk(header))
    images = [c for c in parts if type(c).__name__ == "Image"]
    assert len(images) == 1 and images[0].src == "icon.png"
    assert "Blockade" in [label(c) for c in parts]
    assert texts(app)[0] == "Blockade"


def test_menu_shows_the_choices_and_play_button(app):
    app.show_menu()
    shown = texts(app)
    assert "Quem vai jogar com você?" in shown
    assert "Jogar!" in shown and clickable(app, "Jogar!").on_click == app.on_play


def test_nothing_between_the_title_and_the_first_question(app):
    """No subtitle ("espreme os blocos...") and no tutorial text: the screen stays clear."""
    app.show_menu()
    shown = texts(app)
    assert shown[1] == "Quem vai jogar com você?"
    assert not any("espreme" in t or "Como jogar" in t or "Toque" in t for t in shown)


@pytest.mark.parametrize("mode", [Mode.BOT, Mode.TWO])
def test_the_choices_are_in_the_middle_and_play_is_at_the_bottom(app, ui, mode):
    app.setup.mode = mode
    app.show_menu()
    root, group, slot = app.page.controls[0], centered_group(app), play_slot(app)
    assert root.controls[-1] is slot                        # nothing below Play
    assert (label(group.controls[-1]) or "").startswith(MATH_BUTTON)   # math right above
    choices = [c for c in walk(group) if getattr(c, "on_click", None)]
    assert len(choices) == len(buttons_in_order(app)) - 1   # every button but Play
    assert buttons_in_order(app)[-1] == "Jogar!"
    assert slot.padding.top == ui.PLAY_GAP >= 24            # space between choices and Play
    assert slot.padding.bottom == ui.PLAY_BOTTOM >= 24      # close to, not on, the edge


def test_menu_has_no_icons_or_emoji(app):
    for mode in (Mode.BOT, Mode.TWO):
        app.setup.mode = mode
        app.show_menu()
        assert not [t for t in texts(app) if EMOJI.search(t)]
        assert not [c for c in screen(app) if getattr(c, "icon", None)]
        assert {"Um amigo", "O celular"} <= set(texts(app))


def test_there_is_no_board_size_option(app):
    app.show_menu()
    shown = texts(app)
    assert not any("×" in t and t[0].isdigit() for t in shown)
    assert "Tamanho" not in shown and not any("Mais opções" in t for t in shown)


def test_menu_only_shows_two_big_questions_for_a_young_child(app):
    app.show_menu()
    headings = [t for t in texts(app) if t.endswith("?")]
    assert headings == ["Quem vai jogar com você?", "Quão esperto é o celular?"]


def test_who_plays_with_you_offers_a_friend_and_the_phone(app):
    app.show_menu()
    assert is_highlighted(option(app, "Quem vai jogar com você?", "O celular"))
    assert not is_highlighted(option(app, "Quem vai jogar com você?", "Um amigo"))


@pytest.mark.parametrize("name, strong, tint", [
    ("Fácil", theme.GREEN, theme.GREEN_TINT),
    ("Médio", theme.YELLOW, theme.YELLOW_TINT),
    ("Difícil", theme.RED, theme.RED_TINT),
])
def test_levels_are_green_yellow_and_red(app, name, strong, tint):
    app.setup.bot_level = Level.EASY if name != "Fácil" else Level.HARD
    app.show_menu()
    assert level_card(app, name).bgcolor == tint and not is_highlighted(level_card(app, name))
    level_card(app, name).on_click(None)
    assert level_card(app, name).bgcolor == strong and is_highlighted(level_card(app, name))


def test_only_the_chosen_level_is_highlighted(app):
    app.setup.bot_level = Level.MEDIUM
    app.show_menu()
    assert [is_highlighted(level_card(app, n)) for n in ("Fácil", "Médio", "Difícil")] == [
        False, True, False]


def test_menu_hides_the_bot_level_in_two_player_mode(app):
    app.setup.mode = Mode.TWO
    app.show_menu()
    assert "Quão esperto é o celular?" not in texts(app)
    app.setup.mode = Mode.BOT
    app.show_menu()
    assert "Quão esperto é o celular?" in texts(app)


def test_menu_redraw_replaces_the_old_menu(app):
    app.show_menu()
    app.show_menu()
    assert len(app.page.controls) == 1
    assert texts(app).count("Blockade") == 1


def test_clicking_menu_options_updates_setup_saves_and_redraws(app, ui):
    app.show_menu()
    option(app, "Quem vai jogar com você?", "Um amigo").on_click(None)
    assert app.setup.mode is Mode.TWO and app.save.mode == "dois"
    assert "Quão esperto é o celular?" not in texts(app)
    option(app, "Quem vai jogar com você?", "O celular").on_click(None)
    level_card(app, "Difícil").on_click(None)
    assert app.setup.bot_level is Level.HARD and app.save.bot_level == "dificil"
    assert len(ui.saves) == 3
    assert is_highlighted(level_card(app, "Difícil"))


def test_picking_an_option_updates_setup_saves_and_redraws(app, ui):
    app._pick("bot_level")(Level.HARD)
    assert app.save.bot_level == "dificil" and len(ui.saves) == 1


def test_menu_shows_the_record_only_against_the_phone_and_after_playing(app):
    app.setup.mode = Mode.BOT
    app.show_menu()
    assert not any(t.startswith("Neste nível") for t in texts(app))  # nothing played yet
    app.save.records["5:medio:0"] = {"wins": 2, "losses": 1, "draws": 0}
    app.setup.size = 5
    app.show_menu()
    assert "Neste nível: 2 vitórias, 1 derrotas, 0 empates" in texts(app)
    app.setup.mode = Mode.TWO
    app.show_menu()
    assert not any(t.startswith("Neste nível") for t in texts(app))


def test_the_math_button_shows_which_operations_are_on(app):
    app.show_menu()
    assert label(math_button(app)) == MATH_BUTTON and not is_highlighted(math_button(app))
    app.setup.math = MathSettings(frozenset({ADD, MUL}))
    app.show_menu()
    assert label(math_button(app)) == MATH_BUTTON + ": + ×"
    assert is_highlighted(math_button(app))


# ---------------------------------------------------------------- math page

def test_math_page_shows_only_the_four_symbols(app):
    open_math_page(app)
    shown = texts(app)
    assert MATH_BUTTON in shown
    for sign in ("+", "−", "×", "÷"):
        assert not is_highlighted(symbol(app, sign))
    for word in ("Mais", "Menos", "Vezes", "Dividir", "Números até", "Ligar as contas?"):
        assert word not in shown
    assert "Tabuada" not in shown                   # no × or ÷ yet
    assert not [t for t in shown if EMOJI.search(t)]


def test_math_page_has_play_at_the_bottom_in_the_same_place_as_the_menu(app):
    app.show_menu()
    menu_root, menu_slot = app.page.controls[0], play_slot(app)
    app.setup.math = MathSettings(frozenset({MUL}))
    open_math_page(app)
    math_root, math_slot = app.page.controls[0], play_slot(app)
    centered_group(app)                               # the signs/tables are centered
    assert math_root.controls[-1] is math_slot
    # same slot, same spacing, same button size: Play does not move between screens
    assert (math_slot.padding.top, math_slot.padding.bottom) == (
        menu_slot.padding.top, menu_slot.padding.bottom)
    assert (math_slot.content.width, math_slot.content.height) == (
        menu_slot.content.width, menu_slot.content.height)
    assert menu_root.expand is math_root.expand is True   # both fill the screen height
    assert buttons_in_order(app)[0] == "◀ Voltar"   # the back link stays at the top


def test_choosing_operations_is_multiple_choice_and_saved(app, ui):
    open_math_page(app)
    symbol(app, "+").on_click(None)
    symbol(app, "−").on_click(None)
    assert app.setup.math.operations == {ADD, SUB} and app.save.math.operations == {ADD, SUB}
    assert is_highlighted(symbol(app, "+")) and is_highlighted(symbol(app, "−"))
    symbol(app, "+").on_click(None)
    assert app.setup.math.operations == {SUB} and not is_highlighted(symbol(app, "+"))
    assert len(ui.saves) == 3


def test_no_symbol_chosen_means_no_math(app):
    app.setup.math = MathSettings(frozenset({ADD}))
    open_math_page(app)
    symbol(app, "+").on_click(None)
    assert not app.setup.math.enabled


@pytest.mark.parametrize("sign", ["×", "÷"])
def test_times_tables_appear_below_with_multiplication_or_division(app, sign):
    open_math_page(app)
    symbol(app, "+").on_click(None)
    assert "Tabuada" not in texts(app)
    symbol(app, sign).on_click(None)
    shown = texts(app)
    assert "Tabuada" in shown
    assert shown.index("Tabuada") > shown.index("÷")  # below the four symbols
    for table in range(1, 11):
        option(app, "Tabuada", str(table))            # every table 1-10 is offered
    symbol(app, sign).on_click(None)
    assert "Tabuada" not in texts(app)


def test_choosing_several_times_tables(app):
    app.setup.math = MathSettings(frozenset({MUL}), frozenset({2}))
    open_math_page(app)
    option(app, "Tabuada", "7").on_click(None)
    option(app, "Tabuada", "9").on_click(None)
    assert app.setup.math.tables == {2, 7, 9} and app.save.math.tables == {2, 7, 9}
    option(app, "Tabuada", "2").on_click(None)
    assert app.setup.math.tables == {7, 9}
    assert is_highlighted(option(app, "Tabuada", "7"))
    assert not is_highlighted(option(app, "Tabuada", "2"))


def test_the_last_times_table_cannot_be_turned_off(app):
    app.setup.math = MathSettings(frozenset({MUL}), frozenset({3}))
    open_math_page(app)
    option(app, "Tabuada", "3").on_click(None)
    assert app.setup.math.tables == {3}


def test_play_on_the_math_page_starts_the_game(app):
    app.setup.math = MathSettings(frozenset({MUL}))
    open_math_page(app)
    click(app, "Jogar!")                                 # no need to go back to the menu
    assert app.screen == "partida" and app.tutorial_open
    click(app, "Entendi!")
    assert app.match.setup.math.operations == {MUL}


def test_back_returns_to_the_menu_keeping_the_choices(app):
    open_math_page(app)
    symbol(app, "÷").on_click(None)
    click(app, "◀ Voltar")
    assert app.screen == "menu" and label(math_button(app)) == MATH_BUTTON + ": ÷"


def test_math_choices_are_used_in_the_game(app):
    start(app, math=MathSettings(frozenset({MUL}), frozenset({7})))
    tap_twice(app, (1, 3))
    assert app.match.question.text.startswith("7 × ")


# ---------------------------------------------------------------- tutorial (window)

def test_play_opens_the_board_with_the_tutorial_window_on_top(app):
    app.show_menu()
    click(app, "Jogar!")
    assert app.screen == "partida" and app.match is not None   # the board is underneath
    assert len(app.cells) == 5
    window = dialog(app)
    assert type(window).__name__ == "AlertDialog" and window.modal is True
    shown = dialog_texts(app)
    assert shown[0] == "Como jogar"
    assert "1. Toque numa casa vazia." in shown
    assert any("viram seus" in t for t in shown)
    assert any("mais blocos" in t for t in shown)
    assert not any("conta" in t for t in shown)     # math off: no math step
    assert not [t for t in shown if EMOJI.search(t)]
    assert label(window.actions[-1]) == "Entendi!"


def test_the_board_ignores_taps_while_the_tutorial_is_open(app):
    app.setup.mode, app.setup.bot_level = Mode.BOT, Level.EASY
    app.on_play(None)
    run(app.on_cell((1, 3)))
    app.on_hint(None)
    app.on_undo(None)
    assert app.match.pending is None and app.match.hint_pos is None
    click(app, "Entendi!")
    run(app.on_cell((1, 3)))
    assert app.match.pending == (1, 3)


def test_closing_the_tutorial_another_way_also_unlocks_the_board(app):
    app.on_play(None)
    app.on_tutorial_dismissed(None)            # e.g. Android's back button
    run(app.on_cell((1, 3)))
    assert app.match.pending == (1, 3)


def test_the_tutorial_draws_a_capture_example_with_the_game_colors(app):
    app.on_play(None)
    colored = [c.bgcolor for c in walk(dialog(app)) if type(c).__name__ == "Container"
               and getattr(c, "bgcolor", None) in (theme.BLUE, theme.ORANGE, theme.BLUE_LAST,
                                                   theme.BLUE_TINT)]
    assert colored.count(theme.ORANGE) == 2              # ● ▲ ▲ [tap]
    assert theme.BLUE_TINT in colored                    # the tapped square
    assert colored.count(theme.BLUE) + colored.count(theme.BLUE_LAST) == 1 + 4  # -> ● ● ● ●


def test_the_tutorial_mentions_math_only_when_it_is_on(app):
    app.setup.math = MATH_ON
    app.on_play(None)
    assert "Acerte a conta para colocar o bloco!" in dialog_texts(app)


def test_a_new_game_never_leaves_an_old_tutorial_window_open(app):
    app.on_play(None)
    app.on_play(None)                          # started again while the window was open
    assert len(app.page.dialogs) == 1 and app.tutorial_open
    app.on_menu(None)
    assert app.page.dialogs == [] and not app.tutorial_open


def test_play_again_does_not_show_the_tutorial_again(app):
    start(app)
    app.on_new(None)
    assert app.page.dialogs == [] and not app.tutorial_open


# ---------------------------------------------------------------- game

def test_starting_a_game_builds_the_board_and_paints_the_four_blocks(app):
    start(app)
    assert (len(app.cells), len(app.cells[0])) == (5, 5)
    assert all(len(row) == 5 for row in app.labels)
    assert painted(app) == 4
    assert app.turn_text.value == "Vez do Azul ●"
    assert app.blue_text.value == "● Azul: 2" and app.orange_text.value == "▲ Laranja: 2"
    assert app.bar_blue.width + app.bar_orange.width == app.board_width  # 2 x 2: even split
    assert abs(app.bar_blue.width - app.bar_orange.width) <= 1
    assert app.btn_undo.disabled is True and app.btn_hint.disabled is False
    assert label(app.btn_undo) == "Desfazer (3)"   # undos left live on the button


def test_the_game_screen_is_clear(app):
    """Only what you need to play: no repeated title, no extra info lines."""
    start(app)
    shown = texts(app)
    assert "Guerra dos Blocos" not in shown
    assert not any("restantes" in t for t in shown)


@pytest.mark.parametrize("width, height, grid", [
    (390, 844, 7),        # phone
    (600, 960, 11),       # small tablet
    (768, 1024, 14),      # tablet: the biggest board
    (1024, 1366, 14),     # never more than 14x14
])
def test_the_board_is_the_biggest_that_fits_the_screen(ui, width, height, grid):
    app = ui.BlocksApp(FakePage(width, height))
    start(app)
    assert app.match.game.size == grid and len(app.cells) == grid
    assert app.side >= theme.TOUCH_CELL
    space = theme.board_space(width, height, 12)
    assert space - grid < app.board_width <= space      # fills the space
    assert app.scores.width == app.board_width
    assert all(cell.width == cell.height == app.side for row in app.cells for cell in row)


def test_bigger_boards_start_in_the_center(ui):
    app = ui.BlocksApp(FakePage(768, 1024))
    start(app)
    assert painted(app) == 4
    assert app.match.game.board.get((6, 6)) is not None and app.match.game.board.get((7, 7))


def test_the_hard_phone_plays_on_the_biggest_board(ui):
    app = ui.BlocksApp(FakePage(768, 1024))
    start(app, mode=Mode.BOT, level=Level.HARD)
    tap_twice(app, (5, 7))
    assert app.match.game.turn == 2 and app.busy is False


def test_play_again_uses_the_same_board_size(ui):
    app = ui.BlocksApp(FakePage(600, 960))
    start(app)
    app.on_new(None)
    assert app.match.game.size == 11


def test_the_board_follows_the_screen_when_it_is_resized(app, ui):
    page = FakePage()
    run(ui.main(page))
    assert page.on_resize is not None
    start(app)
    tap_twice(app, (1, 3))
    small = app.board_width
    app.page.width = 400                            # e.g. a desktop window made wider
    app.on_resize(None)
    assert app.match.game.size == 5                 # the game in progress keeps its board
    assert app.board_width > small and 400 - 24 - 5 < app.board_width <= 400 - 24
    assert all(cell.width == app.side for row in app.cells for cell in row)
    assert app.labels[0][0].size == theme.symbol_size(app.side)
    assert app.scores.width == app.board_width
    assert app.bar_blue.width + app.bar_orange.width == app.board_width
    assert app.cells[1][3].bgcolor == theme.BLUE_LAST  # the game itself is unchanged


def test_resizing_outside_the_game_does_nothing(app):
    app.show_menu()
    app.page.width = 700
    app.on_resize(None)
    assert app.screen == "menu" and app.cells == []


def test_main_connects_the_resize_event(ui):
    page = FakePage()
    run(ui.main(page))
    assert callable(page.on_resize)


def test_every_cell_is_tappable_and_plays_its_own_position(app):
    start(app)
    handlers = {app.cells[r][c].on_click for r in range(5) for c in range(5)}
    assert len(handlers) == 25
    run(app.cells[0][4].on_click(None))
    assert app.match.pending == (0, 4)


def test_first_tap_previews_second_tap_plays(app):
    start(app)
    run(app.on_cell((1, 3)))
    assert app.cells[1][3].bgcolor == theme.BLUE_TINT       # chosen cell
    assert app.cells[1][2].bgcolor == theme.FLIP_PREVIEW    # what will flip
    assert app.message.value == "Vira 1 bloco. Toque de novo para jogar."
    run(app.on_cell((1, 3)))
    assert app.match.game.turn == 1 and app.busy is False
    assert app.cells[1][2].bgcolor == theme.BLUE            # turned blue
    assert app.cells[1][3].bgcolor == theme.BLUE_LAST       # last move, darker
    assert app.labels[1][3].value == "●"
    assert app.turn_text.value == "Vez do Laranja ▲" and app.btn_undo.disabled is False
    assert app.blue_text.value == "● Azul: 4" and app.orange_text.value == "▲ Laranja: 1"
    assert app.bar_blue.width > app.bar_orange.width


def test_flipped_blocks_flash_before_settling(app, ui, monkeypatch):
    start(app)
    seen = []

    async def spy_sleep(_seconds):
        seen.append({(r, c) for r in range(5) for c in range(5)
                     if app.cells[r][c].bgcolor == theme.FLASH})

    monkeypatch.setattr(ui.asyncio, "sleep", spy_sleep)
    tap_twice(app, (1, 3))
    assert seen == [{(1, 2)}]                   # flashing while the animation waits
    assert app.cells[1][2].bgcolor == theme.BLUE and app.flash == set()


def test_every_action_redraws_the_page(app):
    start(app)
    before = app.page.updates
    run(app.on_cell((1, 3)))
    assert app.page.updates > before


def test_busy_app_ignores_taps_answers_and_buttons(app):
    start(app)
    app.busy = True
    run(app.on_cell((1, 3)))
    run(app.on_answer(1))
    app.on_hint(None)
    assert app.match.pending is None and app.match.hint_pos is None


def test_taps_before_a_game_exists_are_ignored(app):
    run(app.on_cell((1, 3)))
    run(app.on_answer(3))
    app.on_hint(None)
    assert app.match is None


def test_tapping_an_occupied_cell_changes_nothing(app):
    start(app)
    run(app.on_cell((2, 2)))
    assert app.match.pending is None and app.match.game.turn == 0


def test_against_the_phone_the_bot_replies_automatically(app):
    start(app, mode=Mode.BOT)
    tap_twice(app, (1, 3))
    assert app.match.game.turn == 2 and app.match.phase is Phase.CHOOSING
    assert app.turn_text.value == "Sua vez"
    assert app.blue_text.value.startswith("● Você:")
    assert app.orange_text.value.startswith("▲ Celular:")
    assert app.busy is False and app.flash == set()


def test_buttons_are_disabled_while_the_phone_is_thinking(app, ui, monkeypatch):
    start(app, mode=Mode.BOT)
    states = []

    async def spy_sleep(_seconds):
        states.append((app.busy, app.btn_hint.disabled, app.btn_undo.disabled,
                       app.message.value))

    monkeypatch.setattr(ui.asyncio, "sleep", spy_sleep)
    tap_twice(app, (1, 3))
    thinking = [s for s in states if s[3] == "O celular está pensando..."]
    assert thinking and all(busy and hint and undo for busy, hint, undo, _ in thinking)
    assert app.btn_hint.disabled is False


# ---------------------------------------------------------------- math questions

def test_math_mode_shows_the_question_and_a_correct_answer_places_the_block(app):
    start(app, math=True)
    tap_twice(app, (1, 3))
    assert app.question_box.visible is True
    assert app.match.question.text in texts(app)
    choices = [str(c) for c in app.match.question.choices]
    for choice in choices:
        assert clickable(app, choice)
    assert app.btn_hint.disabled and app.btn_undo.disabled
    click(app, str(app.match.question.answer))
    assert app.match.game.board.get((1, 3)).letter == "B"
    assert app.question_box.visible is False and app.question_box.controls == []


def test_math_mode_wrong_answer_skips_the_turn(app):
    start(app, math=True)
    tap_twice(app, (1, 3))
    wrong = next(c for c in app.match.question.choices if c != app.match.question.answer)
    click(app, str(wrong))
    assert app.match.game.turn == 1 and app.match.game.board.get((1, 3)) is None
    assert app.message.value.startswith("Errou!")
    assert app.turn_text.value == "Vez do Laranja ▲"


def test_answers_outside_a_question_are_ignored(app):
    start(app, math=True)
    run(app.on_answer(5))
    assert app.match.game.turn == 0 and app.match.phase is Phase.CHOOSING


# ---------------------------------------------------------------- hint and undo

def start_beginner(app):
    """Against the phone on Fácil: the only level with Dica and Desfazer."""
    return start(app, mode=Mode.BOT, level=Level.EASY)


def test_hint_marks_a_cell_and_undo_reverts(app):
    start_beginner(app)
    click(app, "Dica")
    hint = app.match.hint_pos
    assert app.cells[hint[0]][hint[1]].bgcolor == theme.HINT
    assert app.labels[hint[0]][hint[1]].value == "?"
    tap_twice(app, (1, 3))                        # you play, the phone answers
    assert app.match.game.turn == 2
    click(app, "Desfazer (3)")
    assert app.match.game.turn == 0 and app.message.value == "Jogada desfeita."
    assert app.cells[1][3].bgcolor == theme.EMPTY
    assert label(app.btn_undo) == "Desfazer (2)"
    app.on_undo(None)
    assert app.message.value == "Não dá para desfazer agora."


def test_undo_button_is_disabled_when_no_undos_are_left(app):
    start_beginner(app)
    for _ in range(3):
        tap_twice(app, app.match.game.board.empty_cells()[0])
        app.on_undo(None)
    tap_twice(app, app.match.game.board.empty_cells()[0])
    assert app.match.undos_left == 0 and app.btn_undo.disabled is True


def test_hint_and_undo_buttons_are_there_only_on_the_beginner_level(app):
    start_beginner(app)
    assert app.btn_hint.visible and app.btn_undo.visible
    for mode, level in ((Mode.BOT, Level.MEDIUM), (Mode.BOT, Level.HARD),
                        (Mode.TWO, Level.EASY)):
        start(app, mode=mode, level=level)
        assert app.btn_hint.visible is False and app.btn_undo.visible is False
        assert app.on_menu in [c.on_click for c in screen(app) if label(c) == "Menu"]


def test_hint_and_undo_do_nothing_outside_the_beginner_level(app):
    start(app, mode=Mode.BOT, level=Level.HARD)
    app.on_hint(None)
    assert app.match.hint_pos is None
    tap_twice(app, (1, 3))
    app.on_undo(None)
    assert app.match.game.turn == 2


# ---------------------------------------------------------------- end and records

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
    assert ui.saves[-1] == 1                      # the record was written to disk
    assert app.btn_hint.disabled and app.btn_undo.disabled
    assert app.turn_text.value == "Fim de jogo"


def test_the_end_box_is_hidden_during_a_game(app):
    start(app)
    assert app.end_box.visible is False and app.question_box.visible is False


def test_the_result_is_saved_only_once(app, ui):
    finish_game(app)
    app._render()
    run(app._continue())
    assert ui.saves == [1]


def test_two_player_game_over_is_not_recorded(app, ui):
    finish_game(app, mode=Mode.TWO)
    assert app.end_title.value == "Azul venceu! 21 × 4" and app.end_record.value == ""
    assert app.save.records == {} and ui.saves == []


def test_play_again_and_menu_buttons(app):
    finish_game(app)
    click(app, "Jogar de novo")
    assert app.match.game.turn == 0 and app.end_box.visible is False
    app.on_menu(None)
    assert "Jogar!" in texts(app) and "Quem vai jogar com você?" in texts(app)


def test_menu_button_during_a_game_goes_back_to_the_menu(app):
    start(app)
    menu_buttons = [c for c in screen(app) if label(c) == "Menu"]
    assert len(menu_buttons) == 2  # one in the toolbar, one in the (hidden) end box
    menu_buttons[-1].on_click(None)
    assert "Quem vai jogar com você?" in texts(app)


def test_main_builds_the_menu_and_sets_the_window(ui):
    page = FakePage()
    run(ui.main(page))
    assert page.title == "Blockade" and page.window.width == 430
    assert page.window.height == 900 and page.padding == 12
    assert len(page.controls) == 1


def test_main_survives_pages_without_a_resizable_window(ui):
    """On the web and on phones the window cannot be resized; main() must not crash."""
    class LockedWindow:
        def __setattr__(self, name, value):
            raise RuntimeError("window is not configurable here")

    page = FakePage()
    page.window = LockedWindow()
    run(ui.main(page))
    assert len(page.controls) == 1


def test_main_uses_the_pastel_background(ui):
    page = FakePage()
    run(ui.main(page))
    assert page.bgcolor == theme.PAGE_BG and page.theme is not None


class MobilePage(FakePage):
    """A page on a phone/tablet that records orientation requests."""

    def __init__(self, mobile=True, fails=False):
        super().__init__()
        self.platform = SimpleNamespace(is_mobile=lambda: mobile)
        self.orientations, self.fails = [], fails

    async def set_allowed_device_orientations(self, orientations):
        if self.fails:
            raise RuntimeError("not supported here")
        self.orientations.append(list(orientations))


def test_main_locks_phones_and_tablets_in_portrait(ui):
    page = MobilePage()
    run(ui.main(page))
    assert len(page.orientations) == 1
    assert [str(o) for o in page.orientations[0]] == [str(ui.ft.DeviceOrientation.PORTRAIT_UP)]


def test_main_does_not_lock_the_orientation_on_a_computer(ui):
    page = MobilePage(mobile=False)
    run(ui.main(page))
    assert page.orientations == [] and len(page.controls) == 1


def test_main_keeps_going_if_the_orientation_cannot_be_locked(ui):
    page = MobilePage(fails=True)          # e.g. opened in the phone's browser
    run(ui.main(page))
    assert len(page.controls) == 1


def test_every_button_uses_the_pastel_palette(app):
    """No default (vivid) Material buttons anywhere: every screen, every button."""
    screens = [app.show_menu, app.show_math, lambda: app.on_play(None),
               lambda: start(app, math=True)]
    pastel = {theme.BUTTON_BG, theme.PLAY_BG, theme.CARD_SELECTED, theme.CARD_BG}
    for show in screens:
        show()
        if app.screen == "partida":
            tap_twice(app, (1, 3))          # open a math question: its answer buttons too
        for control in screen(app):
            if type(control).__name__ in ("Button", "OutlinedButton"):
                assert control.bgcolor in pastel, (app.screen, label(control))


# ---------------------------------------------------------------- tutorial size and "?" button

def test_the_tutorial_window_is_only_as_big_as_it_needs(app, ui):
    """Fixed narrow width (not the whole screen width) and its height follows the content
    (`tight`, no scrolling area stretched to the screen)."""
    app.on_play(None)
    window = dialog(app)
    assert window.content.width == ui.TUTORIAL_WIDTH <= 280
    column = window.content.content
    assert column.tight is True and getattr(column, "scroll", None) is None
    assert window.actions[-1].width == ui.TUTORIAL_WIDTH   # button no wider than the text


def test_the_game_has_a_help_button_at_the_top_right(app):
    start(app)
    top = app.page.controls[0].controls[0]
    assert top is app.top_bar
    assert top.controls[-1] is app.btn_help                # right end of the top row
    assert label(app.btn_help.content) == "?" and app.btn_help.tooltip == "Como jogar"
    assert app.turn_text in top.controls                    # whose turn, in the same row
    assert top.width == app.board_width                     # lines up with the board edge


def test_the_help_button_opens_the_tutorial_over_the_game(app):
    start(app)
    tap_twice(app, (1, 3))
    board = app.match.game.board
    app.btn_help.on_click(None)
    assert app.tutorial_open and dialog_texts(app)[0] == "Como jogar"
    run(app.on_cell((0, 0)))                                # board locked meanwhile
    assert app.match.pending is None
    click(app, "Entendi!")
    assert app.page.dialogs == [] and app.match.game.board == board   # game unchanged
    run(app.on_cell((0, 0)))
    assert app.match.pending == (0, 0)


def test_the_help_button_does_not_stack_windows(app):
    start(app)
    app.on_help(None)
    app.on_help(None)
    assert len(app.page.dialogs) == 1


def test_the_help_button_is_there_on_every_level(app):
    for mode, level in ((Mode.TWO, Level.EASY), (Mode.BOT, Level.HARD)):
        start(app, mode=mode, level=level)
        assert app.btn_help.on_click == app.on_help


def test_resizing_keeps_the_top_row_lined_up_with_the_board(app):
    start(app)
    app.page.width = 400
    app.on_resize(None)
    assert app.top_bar.width == app.board_width == app.scores.width
