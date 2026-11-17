"""The "How to play" window, which opens on top of the board.

It opens by itself on the very first game (see app.py) and, after that, with the game's
"?" button. It is only as big as it needs to be (fixed width, height of its content) and
only closes with "Got it!", or Android's back button; while it is open, the board ignores
taps.
"""
from __future__ import annotations

from typing import Any

import flet as ft

from .. import layout, theme
from ..models import Player
from ..texts import Texts
from .widgets import Handler, play_button, title

TUTORIAL_CELL = 36    # squares of the example drawing
TUTORIAL_WIDTH = 260  # the window only takes what it needs, not the whole screen


class Tutorial:
    """Opens and closes the window, and knows whether it is open."""

    def __init__(self, page: ft.Page, texts: Texts) -> None:
        self.page = page
        self.texts = texts
        self.is_open = False

    def open(self, with_math: bool) -> None:
        """Opens the window (never two, one on top of the other)."""
        if self.is_open:
            return
        self.is_open = True
        self.page.show_dialog(_dialog(self.texts, with_math, on_close=self.close,
                                      on_dismiss=self._dismissed))

    def close(self, _event: Any = None) -> None:
        if self.is_open:
            self.is_open = False
            self.page.pop_dialog()

    def _dismissed(self, _event: Any) -> None:
        """Closed another way (e.g. Android's back button)."""
        self.is_open = False


def _dialog(texts: Texts, with_math: bool, on_close: Handler,
            on_dismiss: Handler) -> ft.AlertDialog:
    steps: list[ft.Control] = [
        _step(texts.step_tap),
        _step(texts.step_tap_again),
        _example(),
        _step(texts.step_capture),
        _step(texts.step_most_wins),
    ]
    if with_math:
        steps.append(_step(texts.step_math))
    return ft.AlertDialog(
        modal=True, bgcolor=theme.PAGE_BG,
        title=title(texts.how_to_play, size=22),
        content=ft.Container(
            width=TUTORIAL_WIDTH,
            content=ft.Column(controls=steps, spacing=10, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
        actions=[play_button(texts.got_it, on_close, width=TUTORIAL_WIDTH)],
        actions_alignment=ft.MainAxisAlignment.CENTER,
        on_dismiss=on_dismiss)


def _step(text: str) -> ft.Control:
    return ft.Text(text, size=15, weight=ft.FontWeight.W_500, color=theme.DARK,
                   text_align=ft.TextAlign.CENTER)


def _example_row(looks: list[theme.CellLook]) -> ft.Control:
    return ft.Row(controls=[
        ft.Container(
            width=TUTORIAL_CELL, height=TUTORIAL_CELL, bgcolor=look.bg, border_radius=6,
            content=ft.Column(controls=[ft.Text(look.symbol, size=18,
                                                weight=ft.FontWeight.BOLD, color=look.fg)],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        for look in looks], spacing=layout.GAP, alignment=ft.MainAxisAlignment.CENTER)


def _example() -> ft.Control:
    """Drawing of a capture, in the game's colours: ● ▲ ▲ [tap] turns into ● ● ● ●."""
    blue, orange = Player.BLUE, Player.ORANGE
    before = [theme.cell_look(blue, blue), theme.cell_look(orange, blue),
              theme.cell_look(orange, blue), theme.cell_look(None, blue, is_pending=True)]
    after = [theme.cell_look(blue, orange)] * 3 + [theme.cell_look(blue, orange, is_last=True)]
    return ft.Container(
        content=ft.Column(controls=[
            _example_row(before),
            ft.Text("⬇", size=18, color=theme.DARK),
            _example_row(after),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=8, bgcolor=theme.BOARD_BG, border_radius=10)
