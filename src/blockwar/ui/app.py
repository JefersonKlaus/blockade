"""The app: opens the window, picks the language, switches screens and remembers the
menu choices.

Screens (one at a time, to keep them clean):
  menu       -> menu.py:        icon + "Blockade", who plays, level, math, Play
                                (the menu's Play = a game WITHOUT math)
  math page  -> menu.py:        "Practice math": + − × ÷, times tables, Play
                                (Play here = a game WITH the chosen math)
  game       -> game_screen.py: the biggest board that fits the screen (up to 14×14); on
                the very first game, the "How to play" tutorial (tutorial.py) opens on top

Language: Portuguese when the device is in Portuguese, English otherwise (texts.py).
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any, Optional

import flet as ft

from .. import APP_NAME, layout, storage, theme
from ..bot import Level
from ..choices import Setup, setup_from_save, store_setup
from ..mathmode import MathSettings
from ..models import Mode
from ..records import record_summary
from ..texts import Texts, texts_for
from .game_screen import GameScreen
from .menu import math_screen, menu_screen
from .tutorial import Tutorial
from .widgets import show_screen

logger = logging.getLogger(__name__)

PAGE_PADDING = 12


class BlocksApp:
    def __init__(self, page: ft.Page, texts: Texts) -> None:
        self.page = page
        self.texts = texts
        self.save = storage.load_save()
        self.setup = setup_from_save(self.save)
        self.tutorial = Tutorial(page, texts)
        self.game: Optional[GameScreen] = None   # only exists on the game screen
        self.with_math = False                    # does the current game have math?

    def _show(self, root: ft.Control) -> None:
        """Replaces the whole screen; the tutorial window is never left open by mistake."""
        self.tutorial.close()
        show_screen(self.page, root)

    # ------------------------------------------------------------------ menu

    def show_menu(self) -> None:
        self.game = None
        record = record_summary(self.save, self._game_setup(with_math=False), self.texts)
        self._show(menu_screen(self.setup, record, self.texts, on_mode=self.on_mode,
                               on_level=self.on_level, on_open_math=self.on_open_math,
                               on_play=self.on_play))

    def on_mode(self, mode: Mode) -> None:
        self.setup.mode = mode
        self._remember()
        self.show_menu()

    def on_level(self, level: Level) -> None:
        self.setup.bot_level = level
        self._remember()
        self.show_menu()

    def _remember(self) -> None:
        store_setup(self.save, self.setup)
        storage.save_save(self.save)

    # ------------------------------------------------------------------ math page

    def show_math(self) -> None:
        self.game = None
        self._show(math_screen(self.setup.math, self.texts, on_change=self.on_math,
                               on_back=self.on_menu, on_play=self.on_play_math))

    def on_open_math(self, _event: Any) -> None:
        self.show_math()

    def on_math(self, math: MathSettings) -> None:
        self.setup.math = math
        self._remember()
        self.show_math()

    # ------------------------------------------------------------------ game

    def _space(self) -> float:
        """Side of the biggest square that fits the board on this screen."""
        def number(value: Any) -> Optional[float]:
            return value if isinstance(value, (int, float)) else None
        return layout.board_space(number(getattr(self.page, "width", None)),
                                  number(getattr(self.page, "height", None)),
                                  number(getattr(self.page, "padding", 0)) or 0)

    def _game_setup(self, with_math: bool) -> Setup:
        """The choices for one game. The math chosen on the math page only applies to games
        started there; the menu's game never has math."""
        return replace(self.setup, math=self.setup.math if with_math else MathSettings())

    def show_game(self, with_math: bool) -> None:
        # The biggest board that fits: ~7×7 on a phone, 10×10 or more on a tablet, up to 14×14.
        space = self._space()
        self.setup.size = layout.grid_size(space)
        self.with_math = with_math
        self.game = GameScreen(self.page, self._game_setup(with_math), self.save, self.texts,
                               self.tutorial, space, on_new=self.on_new, on_menu=self.on_menu)
        self._show(self.game.view.root)
        self.game.render()

    def on_play(self, _event: Any) -> None:
        """The menu's Play: a game without math."""
        self._start(with_math=False)

    def on_play_math(self, _event: Any) -> None:
        """Play on the math page: a game with the chosen math."""
        self._start(with_math=True)

    def _start(self, with_math: bool) -> None:
        """Opens the board. Only the very first time does the tutorial open by itself on
        top; after that, only with the game's "?" button."""
        self.show_game(with_math)
        if not self.save.tutorial_seen:
            self.save.tutorial_seen = True
            storage.save_save(self.save)
            self.tutorial.open(with_math and self.setup.math.enabled)

    def on_new(self, _event: Any) -> None:
        """ "Play again": a new game of the same kind (with or without math)."""
        self.show_game(self.with_math)

    def on_menu(self, _event: Any) -> None:
        self.show_menu()

    def on_resize(self, _event: Any) -> None:
        """The window changed size: the game's board follows."""
        if self.game is not None:
            self.game.resize(self._space())


async def lock_portrait(page: ft.Page) -> None:
    """The game is always upright (portrait) on phones/tablets. Nothing to lock on a computer."""
    platform = getattr(page, "platform", None)
    try:
        if platform is not None and platform.is_mobile():
            await page.set_allowed_device_orientations([ft.DeviceOrientation.PORTRAIT_UP])
    except Exception:  # e.g. opened in the phone's browser via `flet run --android`
        logger.debug("could not lock the orientation", exc_info=True)


async def device_language(page: ft.Page) -> Optional[str]:
    """The device's main language code (e.g. "pt"), or None when it cannot be read."""
    try:
        info = await page.get_device_info()
        return info.locales[0].language_code if info and info.locales else None
    except Exception:  # e.g. a platform without device info
        logger.debug("could not read the device language", exc_info=True)
        return None


async def main(page: ft.Page) -> None:
    """Entry point passed to `ft.run`."""
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=theme.SEED)
    page.bgcolor = theme.PAGE_BG
    page.padding = PAGE_PADDING
    try:
        page.window.width = 430   # on a computer, an upright window like a phone
        page.window.height = 900
    except Exception:  # window not configurable (web/phone): no problem
        logger.debug("window is not configurable", exc_info=True)
    await lock_portrait(page)
    app = BlocksApp(page, texts_for(await device_language(page)))
    page.on_resize = app.on_resize
    app.show_menu()
