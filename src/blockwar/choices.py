"""The menu choices (`Setup`) and how they come from / go to the save file."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .bot import Level
from .mathmode import MathSettings
from .models import DEFAULT_SIZE, Mode
from .storage import SaveData


@dataclass
class Setup:
    """How the next game will be played."""

    mode: Mode = Mode.BOT
    size: int = DEFAULT_SIZE     # the UI replaces it with the biggest that fits the screen
    bot_level: Level = Level.MEDIUM
    math: MathSettings = field(default_factory=MathSettings)  # off by default
    seed: Optional[int] = None   # only so tests can replay the same game


def setup_from_save(data: SaveData) -> Setup:
    """The board size is not saved: it comes from the screen of each device."""
    return Setup(mode=data.mode, bot_level=data.bot_level, math=data.math)


def store_setup(data: SaveData, setup: Setup) -> None:
    data.mode, data.bot_level, data.math = setup.mode, setup.bot_level, setup.math
