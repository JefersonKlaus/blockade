"""Doing what a child does: pressing buttons, starting and finishing games."""
from __future__ import annotations

import asyncio

from blockwar.board import Board
from blockwar.bot import Level
from blockwar.game import Game
from blockwar.mathmode import ADD, SUB, MathSettings
from blockwar.models import Mode

from ui_queries import clickable, math_button, on_screen


def run(coro):
    return asyncio.run(coro)


def click(app, text: str) -> None:
    result = clickable(app, text).on_click(None)
    if asyncio.iscoroutine(result):
        run(result)


def tap_twice(app, pos) -> None:
    run(app.game.on_cell(pos))
    run(app.game.on_cell(pos))


MATH_ON = MathSettings(frozenset({ADD, SUB}))


def start(app, mode=Mode.TWO, math=False, level=Level.MEDIUM):
    """Start a game the way a child does: Jogar! in the menu, or, with math, Jogar! on
    the math page (and, the very first time, the tutorial window -> Entendi!)."""
    app.setup.mode, app.setup.bot_level = mode, level
    app.setup.math = math if isinstance(math, MathSettings) else (
        MATH_ON if math else MathSettings())
    if math:
        app.on_play_math(None)
    else:
        app.on_play(None)
    assert on_screen(app) == "game"
    if app.tutorial.is_open:
        click(app, app.texts.got_it)
    assert not app.tutorial.is_open and app.page.dialogs == []
    return app


def open_math_page(app):
    app.show_menu()
    math_button(app).on_click(None)
    assert on_screen(app) == "math"


def finish_game(app, mode=Mode.BOT):
    start(app, mode=mode)
    app.game.match.game = Game(board=Board.from_text(
        ["BBBBB", "BBBBB", "BBBBB", "BBBBB", "OOOO."]))
    tap_twice(app, (4, 4))
