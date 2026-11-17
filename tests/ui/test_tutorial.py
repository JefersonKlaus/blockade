"""The "Como jogar" window: what it shows, its size, and the "?" button."""
from __future__ import annotations

from blockwar import theme
from blockwar.bot import Level
from blockwar.models import Mode
from blockwar.texts import PORTUGUESE

from fake_page import FakePage
from ui_actions import MATH_ON, click, run, start, tap_twice
from ui_queries import EMOJI, dialog, dialog_texts, label, on_screen, view, walk


def test_play_opens_the_board_with_the_tutorial_window_on_top(app):
    app.show_menu()
    click(app, "Jogar!")
    assert on_screen(app) == "game" and app.game.match is not None   # the board is underneath
    assert len(view(app).cells) == 5
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
    run(app.game.on_cell((1, 3)))
    app.game.on_hint(None)
    app.game.on_undo(None)
    assert app.game.match.pending is None and app.game.match.hint_pos is None
    click(app, "Entendi!")
    run(app.game.on_cell((1, 3)))
    assert app.game.match.pending == (1, 3)


def test_closing_the_tutorial_another_way_also_unlocks_the_board(app):
    app.on_play(None)
    dialog(app).on_dismiss(None)               # e.g. Android's back button
    run(app.game.on_cell((1, 3)))
    assert app.game.match.pending == (1, 3)


def test_the_tutorial_draws_a_capture_example_with_the_game_colors(app):
    app.on_play(None)
    colored = [c.bgcolor for c in walk(dialog(app)) if type(c).__name__ == "Container"
               and getattr(c, "bgcolor", None) in (theme.BLUE, theme.ORANGE, theme.BLUE_LAST,
                                                   theme.BLUE_TINT)]
    assert colored.count(theme.ORANGE) == 2              # ● ▲ ▲ [tap]
    assert theme.BLUE_TINT in colored                    # the tapped square
    assert colored.count(theme.BLUE) + colored.count(theme.BLUE_LAST) == 1 + 4  # -> ● ● ● ●


def test_the_tutorial_mentions_math_only_in_the_math_game(app, ui):
    app.setup.math = MATH_ON
    app.on_play_math(None)
    assert "Acerte a conta para colocar o bloco!" in dialog_texts(app)
    other = ui.BlocksApp(FakePage(), PORTUGUESE)                 # first game from the menu instead
    other.setup.math = MATH_ON
    other.on_play(None)
    assert "Acerte a conta para colocar o bloco!" not in dialog_texts(other)


def test_the_tutorial_window_is_only_as_big_as_it_needs(app, ui):
    """Fixed narrow width (not the whole screen width) and its height follows the content
    (`tight`, no scrolling area stretched to the screen)."""
    app.on_play(None)
    window = dialog(app)
    assert window.content.width == ui.tutorial.TUTORIAL_WIDTH <= 280
    column = window.content.content
    assert column.tight is True and getattr(column, "scroll", None) is None
    assert window.actions[-1].width == ui.tutorial.TUTORIAL_WIDTH   # button no wider than the text


def test_the_help_button_opens_the_tutorial_over_the_game(app):
    start(app)
    tap_twice(app, (1, 3))
    board = app.game.match.game.board
    view(app).btn_help.on_click(None)
    assert app.tutorial.is_open and dialog_texts(app)[0] == "Como jogar"
    run(app.game.on_cell((0, 0)))                                # board locked meanwhile
    assert app.game.match.pending is None
    click(app, "Entendi!")
    assert app.page.dialogs == [] and app.game.match.game.board == board   # game unchanged
    run(app.game.on_cell((0, 0)))
    assert app.game.match.pending == (0, 0)


def test_the_help_button_does_not_stack_windows(app):
    start(app)
    app.game.on_help(None)
    app.game.on_help(None)
    assert len(app.page.dialogs) == 1
