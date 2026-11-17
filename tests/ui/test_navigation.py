"""Going from screen to screen: every screen safe and centered, which Jogar! starts
which game, and the tutorial opening by itself only the very first time."""
from __future__ import annotations


from blockwar import storage, theme
from blockwar.mathmode import ADD
from blockwar.models import Mode
from blockwar.storage import SaveData
from blockwar.texts import PORTUGUESE

from fake_page import FakePage
from ui_actions import MATH_ON, click, open_math_page, start, tap_twice
from ui_queries import dialog_texts, label, on_screen, screen, symbol, texts


def test_every_screen_is_clear_of_the_status_bar_and_centered(app):
    """The status bar (clock, signal, battery) must not cover the top of any screen. The
    SafeArea is only as wide as what is inside it, so a full-size Container puts each
    screen in the middle (horizontally), starting at the top."""
    for show in (app.show_menu, app.show_math, lambda: start(app)):
        show()
        assert len(app.page.controls) == 1                 # one screen at a time
        safe = app.page.controls[0]
        assert type(safe).__name__ == "SafeArea" and safe.expand is True
        assert safe.avoid_intrusions_top is True
        frame = safe.content
        assert type(frame).__name__ == "Container" and frame.width is None
        assert (frame.alignment.x, frame.alignment.y) == (0, -1)


def test_every_button_uses_the_pastel_palette(app):
    """No default (vivid) Material buttons anywhere: every screen, every button."""
    screens = [app.show_menu, app.show_math, lambda: app.on_play(None),
               lambda: start(app, math=True)]
    pastel = {theme.BUTTON_BG, theme.PLAY_BG, theme.CARD_SELECTED, theme.CARD_BG}
    for show in screens:
        show()
        if on_screen(app) == "game":
            tap_twice(app, (1, 3))          # open a math question: its answer buttons too
        for control in screen(app):
            if type(control).__name__ in ("Button", "OutlinedButton"):
                assert control.bgcolor in pastel, (on_screen(app), label(control))


def test_there_is_no_game_outside_the_game_screen(app):
    """The menu and the math page have no board to tap; leaving a game drops it."""
    app.show_menu()
    assert app.game is None
    start(app)
    assert app.game is not None
    app.on_menu(None)
    assert app.game is None
    app.show_math()
    assert app.game is None
    app.page.width = 700
    app.on_resize(None)                        # resizing outside a game changes nothing
    assert on_screen(app) == "math" and app.game is None


def test_menu_button_during_a_game_goes_back_to_the_menu(app):
    start(app)
    menu_buttons = [c for c in screen(app) if label(c) == "Menu"]
    assert len(menu_buttons) == 2  # one in the toolbar, one in the (hidden) end box
    menu_buttons[-1].on_click(None)
    assert "Quem vai jogar com você?" in texts(app)


def first_tap_twice(app) -> str:
    """Tap a square twice and return what happened: "played" or "question"."""
    app.game.match.tap((1, 3))
    return app.game.match.tap((1, 3))


def test_play_in_the_menu_is_always_a_game_without_math(app):
    open_math_page(app)
    symbol(app, "+").on_click(None)                 # math chosen on the math page...
    click(app, "◀ Voltar")
    click(app, "Jogar!")                            # ...but Jogar! in the menu
    if app.tutorial.is_open:
        click(app, "Entendi!")
    assert not app.game.match.setup.math.enabled and first_tap_twice(app) == "played"
    assert app.setup.math.operations == {ADD}       # the math choices are kept


def test_play_on_the_math_page_is_a_game_with_the_chosen_math(app):
    open_math_page(app)
    symbol(app, "×").on_click(None)
    click(app, "Jogar!")
    if app.tutorial.is_open:
        click(app, "Entendi!")
    assert first_tap_twice(app) == "question" and " × " in app.game.match.question.text


def test_play_again_keeps_the_same_kind_of_game(app):
    app.setup.math = MATH_ON                        # math chosen on the math page
    for play, with_math in ((app.on_play, False), (app.on_play_math, True)):
        play(None)
        app.tutorial.close()
        app.on_new(None)                            # "Jogar de novo"
        assert app.game.match.setup.math.enabled is with_math


def test_games_with_and_without_math_keep_separate_records(app):
    start(app, mode=Mode.BOT, math=True)
    assert app.game.match.setup.math.enabled
    start(app, mode=Mode.BOT)
    assert not app.game.match.setup.math.enabled
    app.save.records["5:medio:0"] = {"wins": 2, "losses": 0, "draws": 0}   # without math
    app.save.records["5:medio:1"] = {"wins": 9, "losses": 0, "draws": 0}   # with math
    app.setup.math = MATH_ON                        # math chosen on the math page...
    app.show_menu()                                 # ...but the menu shows its own game's record
    assert "Neste nível: 2 vitórias, 0 derrotas, 0 empates" in texts(app)


def test_the_tutorial_opens_by_itself_only_the_very_first_time(app, ui):
    app.on_play(None)
    assert app.tutorial.is_open and app.save.tutorial_seen is True
    assert ui.saves == [0]                     # remembered in the save file right away
    click(app, "Entendi!")
    for again in (app.on_menu, app.on_play, app.on_new, app.on_play):
        again(None)
        assert app.page.dialogs == [] and not app.tutorial.is_open
    app.game.on_help(None)                     # but the "?" button always opens it
    assert app.tutorial.is_open and dialog_texts(app)[0] == "Como jogar"


def test_the_tutorial_stays_closed_after_the_app_is_opened_again(ui, monkeypatch):
    monkeypatch.setattr(storage, "load_save", lambda: SaveData(tutorial_seen=True))
    app = ui.BlocksApp(FakePage(), PORTUGUESE)
    app.on_play(None)
    assert on_screen(app) == "game" and app.page.dialogs == [] and ui.saves == []


def test_a_new_game_never_leaves_an_old_tutorial_window_open(app):
    start(app)
    app.game.on_help(None)
    app.on_play(None)                          # started again while the window was open
    assert app.page.dialogs == [] and not app.tutorial.is_open
    app.game.on_help(None)
    app.on_menu(None)
    assert app.page.dialogs == [] and not app.tutorial.is_open
