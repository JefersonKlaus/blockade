"""Shared pytest setup for the whole suite.

Everything here is deliberately small: helpers that several test files need and
safety nets that keep the tests from touching anything outside the test run.
"""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from blockwar.board import Board
from blockwar.models import Player

B, O = Player.BLUE, Player.ORANGE


@pytest.fixture(autouse=True)
def isolated_save_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test gets its own save file, so no test ever reads or overwrites the
    real scores in ~/.guerra_dos_blocos or in Flet's app storage folder."""
    path = tmp_path / "save" / "guerra_dos_blocos.json"
    monkeypatch.setenv("GUERRA_SAVE", str(path))
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    return path


def random_board(rng: random.Random, size: int, fill: float = 0.6) -> Board:
    """A board with random blocks (not necessarily reachable in a real game).

    Useful for property tests: the capture rule must hold on *any* position.
    """
    choices = [B, O, None]
    weights = [fill / 2, fill / 2, 1 - fill]
    rows = tuple(tuple(rng.choices(choices, weights)[0] for _ in range(size))
                 for _ in range(size))
    return Board(size, rows)


@pytest.fixture
def make_random_board():
    return random_board
