"""The screen background shows whose turn it is."""
from __future__ import annotations

import asyncio

from blockwar import theme
from blockwar.models import Mode

from ui_actions import finish_game, start, tap_twice
from ui_queries import view


def test_the_background_shows_whose_turn_it_is_with_two_players(app):
    start(app)
    assert app.page.bgcolor == theme.BLUE_TINT              # Azul starts
    tap_twice(app, (1, 3))
    assert app.page.bgcolor == theme.ORANGE_TINT            # now Laranja
    tap_twice(app, (0, 0))
    assert app.page.bgcolor == theme.BLUE_TINT


def test_the_background_turns_orange_while_the_phone_plays(app, monkeypatch):
    start(app, mode=Mode.BOT)
    assert app.page.bgcolor == theme.BLUE_TINT              # your turn
    seen = []

    async def spy_sleep(_seconds):
        seen.append((view(app).message.value, app.page.bgcolor))

    monkeypatch.setattr(asyncio, "sleep", spy_sleep)
    tap_twice(app, (1, 3))
    assert ("O celular está pensando...", theme.ORANGE_TINT) in seen
    assert app.page.bgcolor == theme.BLUE_TINT              # your turn again


def test_the_background_stays_with_the_player_answering_a_question(app):
    start(app, math=True)
    tap_twice(app, (1, 3))
    assert app.game.match.question is not None and app.page.bgcolor == theme.BLUE_TINT


def test_the_background_is_neutral_when_the_game_is_over_and_in_the_menu(app):
    finish_game(app)
    assert app.game.match.is_over and app.page.bgcolor == theme.PAGE_BG
    start(app)
    app.on_menu(None)
    assert app.page.bgcolor == theme.PAGE_BG
    app.show_math()
    assert app.page.bgcolor == theme.PAGE_BG
