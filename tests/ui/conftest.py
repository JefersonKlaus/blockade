"""Fixtures for the screen tests.

The tests build the screens with the real Flet controls on a fake page (fake_page.py):
real controls reject unknown arguments and enum values, so wrong control names or
arguments are caught here. No window is opened, and nothing checks how the screen
*looks*; use ``flet run`` for that (see the README).
"""
from __future__ import annotations

import pytest

import blockwar.ui as ui_package
from blockwar import storage
from blockwar.storage import SaveData
from blockwar.texts import PORTUGUESE

from fake_page import FakePage


@pytest.fixture
def ui(monkeypatch):
    """The `blockwar.ui` package. The save file is never touched: `ui.saves` lists
    `games_played` at every save."""
    saves = []
    monkeypatch.setattr(storage, "load_save", lambda: SaveData())
    monkeypatch.setattr(storage, "save_save",
                        lambda data: saves.append(data.games_played) or True)
    monkeypatch.setattr(ui_package.game_screen, "FLIP_DELAY", 0)
    monkeypatch.setattr(ui_package.game_screen, "BOT_DELAY", 0)
    monkeypatch.setattr(ui_package, "saves", saves, raising=False)
    return ui_package


@pytest.fixture
def app(ui):
    # A screen that fits a 5x5 board. In Portuguese, so the tests read the exact texts a
    # Brazilian child sees (English has its own tests in test_language.py).
    instance = ui.BlocksApp(FakePage(), PORTUGUESE)
    instance.setup.seed = 1
    return instance
