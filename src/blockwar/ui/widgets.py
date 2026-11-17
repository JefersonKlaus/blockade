"""Shared visual pieces, without state: titles, pastel buttons and cards, switching screens."""
from __future__ import annotations

from typing import Any, Callable, Optional

import flet as ft

from .. import theme

Handler = Callable[[Any], Any]


def show_screen(page: ft.Page, root: ft.Control) -> None:
    """Shows `root` as the whole screen, inside a SafeArea: on a phone, nothing is hidden
    behind the status bar (clock, signal, battery), the notch or the navigation bar at
    the bottom.

    The SafeArea is only as wide as its content; the Container around it takes the whole
    screen and puts the screen in the middle (centred horizontally, from the top).

    Every new screen starts with the cream background (a game then paints the background
    with the colour of whoever plays)."""
    page.bgcolor = theme.PAGE_BG
    page.clean()
    page.add(ft.SafeArea(expand=True, content=ft.Container(
        content=root, alignment=ft.Alignment(x=0, y=-1))))


def title(text: str, size: int = 28) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=theme.DARK,
                   text_align=ft.TextAlign.CENTER)


def button(text: str, on_click: Handler, bg: str = theme.BUTTON_BG, **extra: Any) -> ft.Button:
    """Ordinary pastel button (light background, dark text)."""
    return ft.Button(text, bgcolor=bg, color=theme.DARK, on_click=on_click, **extra)


def play_button(text: str, on_click: Handler, width: int = 240) -> ft.Button:
    """The Play button: the biggest and most eye-catching, always the last one."""
    return button(text, on_click, bg=theme.PLAY_BG, width=width, height=58,
                  style=ft.ButtonStyle(text_style=ft.TextStyle(size=22,
                                                               weight=ft.FontWeight.BOLD)))


def _border(color: Optional[str]) -> Optional[ft.Border]:
    if color is None:
        return None
    side = ft.BorderSide(3, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


def card(text: str, look: theme.CardLook, on_click: Handler, width: int = 130,
         height: int = 64, size: int = 18) -> ft.Container:
    """A big card with text only (no pictures). The chosen one has a stronger colour and
    a border."""
    return ft.Container(
        content=ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=look.fg,
                        text_align=ft.TextAlign.CENTER),
        width=width, height=height, bgcolor=look.bg, border=_border(look.border),
        border_radius=16, ink=True, alignment=ft.Alignment(0, 0), on_click=on_click)


def card_section(heading: str, cards: list[ft.Control]) -> ft.Column:
    """A question with its cards."""
    return ft.Column(controls=[
        ft.Text(heading, size=18, weight=ft.FontWeight.BOLD, color=theme.DARK,
                text_align=ft.TextAlign.CENTER),
        ft.Row(controls=cards, spacing=10, run_spacing=10, wrap=True,
               alignment=ft.MainAxisAlignment.CENTER),
    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
