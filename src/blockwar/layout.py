"""Board size for each screen, as pure functions (easy to test, no Flet).

The board is the biggest square that fits: ~7×7 on a phone, up to 14×14 on a tablet.
"""
from __future__ import annotations

from typing import Optional

from .models import MAX_BOARD

GAP = 3                  # space between squares
BOARD_PADDING = 8        # the board's frame around the squares
TOUCH_CELL = 44          # smallest square that is comfortable for a child's finger
MIN_GRID = 5             # small phone: at least 5×5
MAX_GRID = MAX_BOARD     # big tablet: at most 14×14
RESERVED_HEIGHT = 250    # turn, score, bar, message and buttons around the board
DEFAULT_SPACE = 406      # space used while the screen has not reported its size


def board_space(width: Optional[float], height: Optional[float], padding: float) -> float:
    """Side of the biggest square that fits the board: the whole screen width, unless the
    height (minus the rest of the game screen) is smaller."""
    if not width or width <= 0:
        return DEFAULT_SPACE
    space = width - 2 * padding
    if height and height > 0:
        space = min(space, height - 2 * padding - RESERVED_HEIGHT)
    return max(space, 0)


def grid_size(space: float) -> int:
    """Squares per side: the biggest board where each square still has at least
    `TOUCH_CELL` pixels. Phone ~7×7, tablet 10×10 or more, never more than 14×14."""
    fits = int((space - 2 * BOARD_PADDING + GAP) // (TOUCH_CELL + GAP))
    return max(MIN_GRID, min(MAX_GRID, fits))


def cell_side(size: int, space: float) -> int:
    """Side of each square so the board fills all the space."""
    inner = space - 2 * BOARD_PADDING - (size - 1) * GAP
    return max(1, int(inner // size))


def board_width(size: int, side: int) -> int:
    """Total width of the board (squares + gaps + frame)."""
    return size * side + (size - 1) * GAP + 2 * BOARD_PADDING


def symbol_size(side: int) -> int:
    """Size of the ● / ▲ inside a square."""
    return int(side * 0.5)


def bar_widths(blue: int, orange: int, total_width: int) -> tuple[int, int]:
    """Widths of the score bar (blue on the left, orange on the right)."""
    total = blue + orange
    if total <= 0:
        return 0, 0
    left = round(total_width * blue / total)
    return left, total_width - left
