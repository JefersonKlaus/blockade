"""One game on screen: connects taps to the `Match`, animates, lets the phone play and
saves the record when the game ends. The drawing lives in game_view.py."""
from __future__ import annotations

import asyncio
from typing import Any

import flet as ft

from .. import storage, theme
from ..choices import Setup
from ..controller import Match, Phase
from ..models import Pos
from ..records import record_game, record_summary
from ..storage import SaveData
from ..texts import Texts
from .game_view import GameView
from .tutorial import Tutorial
from .widgets import Handler

FLIP_DELAY = 0.35   # how long the turned blocks flash
BOT_DELAY = 0.6     # the phone "thinking", so the player can follow


class GameScreen:
    def __init__(self, page: ft.Page, setup: Setup, save: SaveData, texts: Texts,
                 tutorial: Tutorial, space: float, on_new: Handler, on_menu: Handler) -> None:
        self.page = page
        self.save = save
        self.texts = texts
        self.tutorial = tutorial
        self.on_new, self.on_menu = on_new, on_menu   # "Play again" and "Menu": app.py
        self.match = Match(setup, texts)
        self.busy = False             # animating or the phone thinking: taps are ignored
        self.flash: set[Pos] = set()  # blocks that have just turned (flashing)
        self.result_saved = False
        self.view = GameView(self, setup.size, space, texts)

    def render(self) -> None:
        self.view.paint(self.match, self.flash, self.busy,
                        record_summary(self.save, self.match.setup, self.texts))
        # The whole screen background shows whose turn it is (blue or orange).
        turn = None if self.match.is_over else self.match.game.current
        self.page.bgcolor = theme.page_color(turn)
        self.page.update()

    def resize(self, space: float) -> None:
        self.view.resize(space)
        self.render()

    # ------------------------------------------------------------------ taps

    def _blocked(self) -> bool:
        """Phone thinking or tutorial open: taps are ignored."""
        return self.busy or self.tutorial.is_open

    async def on_cell(self, pos: Pos) -> None:
        if self._blocked():
            return
        if self.match.tap(pos) == "played":
            await self._after_move()
        else:
            self.render()

    async def on_answer(self, value: int) -> None:
        if self._blocked():
            return
        if self.match.answer(value) in ("played", "skipped"):
            await self._after_move()
        else:
            self.render()

    def on_hint(self, _event: Any) -> None:
        if not self._blocked():
            self.match.hint()
            self.render()

    def on_undo(self, _event: Any) -> None:
        if not self._blocked():
            self.match.undo()
            self.render()

    def on_help(self, _event: Any) -> None:
        """The "?" button: opens the tutorial again, on top of the game."""
        self.tutorial.open(self.match.setup.math.enabled)

    # ------------------------------------------------------------------ after a turn

    async def _after_move(self) -> None:
        """Animates, lets the phone play when it is its turn, and saves the result at the end."""
        self.busy = True
        try:
            await self._flash_flipped()
            if self.match.phase is Phase.BOT_TURN:
                self.match.message = self.texts.thinking
                self.render()
                # On a tablet (up to 14×14) the hard level can take a moment to think: it
                # thinks in a thread, alongside the pause, so the screen never freezes.
                await asyncio.gather(asyncio.sleep(BOT_DELAY),
                                     asyncio.to_thread(self.match.bot_move))
                await self._flash_flipped()
        finally:
            self.busy = False
        self._save_result()
        self.render()

    async def _flash_flipped(self) -> None:
        """Makes the just-turned blocks flash before they settle in their new colour."""
        self.flash = set(self.match.last_flipped)
        self.render()
        if self.flash:
            await asyncio.sleep(FLIP_DELAY)
            self.flash = set()
            self.render()

    def _save_result(self) -> None:
        """Counts the record only once, when the game ends (two-player games don't count)."""
        if not self.match.is_over or self.result_saved:
            return
        self.result_saved = True
        if record_game(self.save, self.match.setup, self.match.game.winner) is not None:
            storage.save_save(self.save)
