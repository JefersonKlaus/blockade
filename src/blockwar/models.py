"""Basic shared types: players, game modes, positions and errors."""
from __future__ import annotations

from enum import Enum
from typing import Tuple

# A position on the board: (row, column), starting at zero in the top-left corner.
Pos = Tuple[int, int]

DEFAULT_SIZE = 7             # size used while the screen has not reported its own yet
MIN_BOARD, MAX_BOARD = 4, 14  # limits accepted by the engine (the size comes from the screen)


class Player(Enum):
    """The two sides. Each has a colour and a symbol (helps players who can't tell the
    colours apart)."""

    BLUE = "blue"
    ORANGE = "orange"

    @property
    def other(self) -> "Player":
        return Player.ORANGE if self is Player.BLUE else Player.BLUE

    @property
    def symbol(self) -> str:
        return "●" if self is Player.BLUE else "▲"  # circle / triangle


class Mode(Enum):
    """Who plays. The value is also what is written to the save file, so it must not
    change (older saves use these words)."""

    BOT = "bot"      # you (Blue) against the phone (Orange)
    TWO = "dois"     # two people on the same device ("dois" = two)


HUMAN_PLAYER = Player.BLUE   # against the phone, you are always Blue...
BOT_PLAYER = Player.ORANGE   # ...and the phone is Orange


class IllegalMove(ValueError):
    """Impossible move: off the board, square taken, or the game is already over."""
