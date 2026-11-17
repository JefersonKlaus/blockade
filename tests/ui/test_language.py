"""The app speaks English by default and Portuguese on a device set to Portuguese."""
import dataclasses
from types import SimpleNamespace


from blockwar.bot import Level
from blockwar.models import Mode
from blockwar.texts import ENGLISH, PORTUGUESE

from fake_page import FakePage
from ui_actions import click, finish_game, open_math_page, run, start, tap_twice
from ui_queries import dialog_texts, symbol, texts


class DevicePage(FakePage):
    """A page whose device reports its languages (or fails to), like Flet's
    `page.get_device_info()`."""

    def __init__(self, *languages, fails=False, info=True):
        super().__init__()
        self.languages, self.fails, self.info = languages, fails, info

    async def get_device_info(self):
        if self.fails:
            raise RuntimeError("no device info here")
        if not self.info:
            return None
        return SimpleNamespace(locales=[SimpleNamespace(language_code=code, country_code=None)
                                        for code in self.languages])


def app_after_main(ui, page):
    run(ui.main(page))
    return page.on_resize.__self__           # the BlocksApp that main() created


# ---------------------------------------------------------------- choosing the language

def test_the_app_is_in_portuguese_only_on_a_device_in_portuguese(ui):
    for page in (DevicePage("pt"), DevicePage("pt", "en")):
        app = app_after_main(ui, page)
        assert app.texts is PORTUGUESE and "Quem vai jogar com você?" in texts(app)
    for page in (DevicePage("en"), DevicePage("es"),
                 DevicePage("en", "pt"),          # Portuguese only as a second language
                 DevicePage(),                    # no languages
                 DevicePage(info=False),          # no device info
                 DevicePage(fails=True),          # reading the device info fails
                 FakePage()):                     # a page without device info at all
        app = app_after_main(ui, page)
        assert app.texts is ENGLISH and "Who will play with you?" in texts(app)


# ---------------------------------------------------------------- English everywhere

def visit_every_screen(app) -> list[str]:
    """Every text of every screen: menu, math page, tutorial, a game with a math question,
    the beginner helpers and the end of a game."""
    seen = []
    app.setup.mode, app.setup.bot_level = Mode.BOT, Level.EASY
    app.show_menu()
    seen += texts(app)
    open_math_page(app)
    symbol(app, "×").on_click(None)             # math on: × and the times tables
    seen += texts(app)
    click(app, app.texts.play)                    # first game ever: the tutorial is open
    seen += dialog_texts(app)
    click(app, app.texts.got_it)
    tap_twice(app, (1, 3))                        # a math question
    seen += texts(app)
    finish_game(app)
    seen += texts(app)
    return seen


def only_in(language, other) -> set[str]:
    """Plain texts (no {blanks}) that exist only in `language`."""
    return {getattr(language, f.name) for f in dataclasses.fields(language)
            if "{" not in getattr(language, f.name)
            and getattr(language, f.name) != getattr(other, f.name)}


def test_the_english_app_shows_no_portuguese(ui):
    app = ui.BlocksApp(FakePage(), ENGLISH)
    app.setup.seed = 1
    seen = visit_every_screen(app)
    assert not set(seen) & only_in(PORTUGUESE, ENGLISH)
    for text in ("Who will play with you?", "How smart is the phone?", "Practice math",
                 "Times tables", "◀ Back", "How to play", "Got it!", "Hint", "Undo (3)",
                 "Play again", "You won! 21 × 4"):
        assert text in seen, text


def test_the_portuguese_app_shows_no_english(ui):
    app = ui.BlocksApp(FakePage(), PORTUGUESE)
    app.setup.seed = 1
    seen = visit_every_screen(app)
    assert not set(seen) & only_in(ENGLISH, PORTUGUESE)
    assert "Você venceu! 21 × 4" in seen and "Jogar de novo" in seen


def test_an_english_game_against_the_phone(ui):
    app = ui.BlocksApp(FakePage(), ENGLISH)
    app.setup.seed = 1
    start(app, mode=Mode.BOT)
    assert app.game.view.turn_text.value == "Your turn"
    assert app.game.view.blue_text.value == "● You: 2"
    assert app.game.view.orange_text.value == "▲ Phone: 2"
    app.game.match.tap((1, 3))
    app.game.render()
    assert app.game.view.message.value == "Turns 1 block. Tap again to play."
