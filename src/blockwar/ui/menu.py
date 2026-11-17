"""The two choice screens: the menu and the math page ("Practice math").

They only build the controls; what each tap does comes from outside (app.py), and the
words come from the `Texts` they are given. Both use the same layout, so the Play button
sits in exactly the same place on both screens.
"""
from __future__ import annotations

from typing import Any, Callable

import flet as ft

from .. import APP_NAME, theme
from ..bot import Level
from ..choices import Setup
from ..mathmode import OPERATIONS, SYMBOLS, TABLES, MathSettings
from ..models import Mode
from ..texts import Texts
from .widgets import Handler, button, card, card_section, play_button, title

ICON = "icon.png"   # src/assets/icon.png (also the app icon on the phone)
ICON_SIZE = 96      # icon at the top of the menu, with the name right below it
PLAY_GAP = 28       # minimum space between the choices and the Play button
PLAY_BOTTOM = 36    # distance from Play to the bottom edge (near the thumbs)


def choice_screen(top: ft.Control, choices: list[ft.Control], play: str,
                  on_play: Handler) -> ft.Control:
    """The shared layout of the choice screens:

        top     -> at the top (icon + name, or "Back")
        choices -> the choices, centred in the middle space
        play    -> the Play button, at the bottom, near the thumbs, with a space above it"""
    return ft.Column(controls=[
        top,
        ft.Column(controls=choices, spacing=20, expand=True,
                  alignment=ft.MainAxisAlignment.CENTER,
                  horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Container(content=play_button(play, on_play),
                     padding=ft.Padding(left=0, top=PLAY_GAP, right=0, bottom=PLAY_BOTTOM)),
    ], spacing=0, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)


# ------------------------------------------------------------------ menu

def header() -> ft.Control:
    """The app icon (big) with the name right below it, at the top of the menu."""
    return ft.Column(controls=[
        ft.Image(src=ICON, width=ICON_SIZE, height=ICON_SIZE),
        title(APP_NAME, size=32),
    ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)


def menu_screen(setup: Setup, record: str, texts: Texts, on_mode: Callable[[Mode], Any],
                on_level: Callable[[Level], Any], on_open_math: Handler,
                on_play: Handler) -> ft.Control:
    """Who plays, the phone's level (only against it), the record, the way to the game
    with math (the math page) and Play (a game without math)."""
    choices: list[ft.Control] = [card_section(texts.who_plays, [
        card(text, theme.card_look(mode is setup.mode), lambda _e, m=mode: on_mode(m))
        for text, mode in ((texts.a_friend, Mode.TWO), (texts.the_phone, Mode.BOT))])]
    if setup.mode is Mode.BOT:
        choices.append(card_section(texts.how_smart, [
            card(texts.level(level), theme.level_look(level, level is setup.bot_level),
                 lambda _e, lv=level: on_level(lv), width=100)
            for level in Level]))
    if record:
        choices.append(ft.Text(record, size=13, color=theme.MUTED))
    choices.append(button(texts.math_title, on_open_math, width=280, height=50))
    return choice_screen(header(), choices, texts.play, on_play)


# ------------------------------------------------------------------ math page

def math_screen(math: MathSettings, texts: Texts, on_change: Callable[[MathSettings], Any],
                on_back: Handler, on_play: Handler) -> ft.Control:
    """Only the 4 signs; with × or ÷ the times tables appear right below. No sign chosen =
    a game without questions. The last button is Play, with no need to go back to the
    menu."""
    choices: list[ft.Control] = [
        title(texts.math_title),
        ft.Row(controls=[
            card(SYMBOLS[op], theme.card_look(op in math.operations),
                 lambda _e, o=op: on_change(math.toggled_operation(o)),
                 width=72, height=72, size=36)
            for op in OPERATIONS], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
    ]
    if math.uses_tables:
        choices.append(card_section(texts.times_tables, [
            card(str(t), theme.card_look(t in math.tables),
                 lambda _e, t=t: on_change(math.toggled_table(t)), width=54, height=48, size=20)
            for t in TABLES]))
    back = ft.Row(controls=[ft.TextButton(texts.back, on_click=on_back)],
                  alignment=ft.MainAxisAlignment.START)
    return choice_screen(back, choices, texts.play, on_play)
