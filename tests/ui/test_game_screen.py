"""Playing a turn on screen: taps, the flash of turned blocks and the phone's move."""
from __future__ import annotations

import asyncio

from blockwar import theme
from blockwar.bot import Level
from blockwar.controller import Phase
from blockwar.models import Mode
from blockwar.texts import PORTUGUESE

from fake_page import FakePage
from ui_actions import run, start, tap_twice
from ui_queries import view


def test_flipped_blocks_flash_before_settling(app, ui, monkeypatch):
    start(app)
    seen = []

    async def spy_sleep(_seconds):
        seen.append({(r, c) for r in range(5) for c in range(5)
                     if view(app).cells[r][c].bgcolor == theme.FLASH})

    monkeypatch.setattr(asyncio, "sleep", spy_sleep)
    tap_twice(app, (1, 3))
    assert seen == [{(1, 2)}]                   # flashing while the animation waits
    assert view(app).cells[1][2].bgcolor == theme.BLUE and app.game.flash == set()


def test_every_action_redraws_the_page(app):
    start(app)
    before = app.page.updates
    run(app.game.on_cell((1, 3)))
    assert app.page.updates > before


def test_busy_app_ignores_taps_answers_and_buttons(app):
    start(app)
    app.game.busy = True
    run(app.game.on_cell((1, 3)))
    run(app.game.on_answer(1))
    app.game.on_hint(None)
    assert app.game.match.pending is None and app.game.match.hint_pos is None


def test_against_the_phone_the_bot_replies_automatically(app):
    start(app, mode=Mode.BOT)
    tap_twice(app, (1, 3))
    assert app.game.match.game.turn == 2 and app.game.match.phase is Phase.CHOOSING
    assert view(app).turn_text.value == "Sua vez"
    assert view(app).blue_text.value.startswith("● Você:")
    assert view(app).orange_text.value.startswith("▲ Celular:")
    assert app.game.busy is False and app.game.flash == set()


def test_buttons_are_disabled_while_the_phone_is_thinking(app, ui, monkeypatch):
    start(app, mode=Mode.BOT)
    states = []

    async def spy_sleep(_seconds):
        states.append((app.game.busy, view(app).btn_hint.disabled, view(app).btn_undo.disabled,
                       view(app).message.value))

    monkeypatch.setattr(asyncio, "sleep", spy_sleep)
    tap_twice(app, (1, 3))
    thinking = [s for s in states if s[3] == "O celular está pensando..."]
    assert thinking and all(busy and hint and undo for busy, hint, undo, _ in thinking)
    assert view(app).btn_hint.disabled is False


def test_the_hard_phone_plays_on_the_biggest_board(ui):
    app = ui.BlocksApp(FakePage(768, 1024), PORTUGUESE)
    start(app, mode=Mode.BOT, level=Level.HARD)
    tap_twice(app, (5, 7))
    assert app.game.match.game.turn == 2 and app.game.busy is False
