"""The computer opponent (the phone), at three levels."""
from __future__ import annotations

import random
from enum import Enum
from typing import Optional

from .board import Board, apply_move, flips_for
from .models import Player, Pos


class Level(Enum):
    """How smart the phone is. The values are written to the save file (and are part of
    the record keys), so they keep their original Portuguese words. The names shown on
    screen are in texts.py."""

    EASY = "facil"
    MEDIUM = "medio"
    HARD = "dificil"


def level_from_value(value: object) -> Level:
    """The level with this value ("facil", "medio", "dificil"); anything else gives
    MEDIUM."""
    for level in Level:
        if level.value == value:
            return level
    return Level.MEDIUM


def positional_value(board: Board, pos: Pos) -> float:
    """Strategic value of a square: corners are great, squares next to an empty corner
    are dangerous (they open the corner to the opponent) and edges are good."""
    last = board.size - 1
    r, c = pos
    if pos in board.corners:
        return 8.0
    for corner in board.corners:
        if board.get(corner) is None and max(abs(r - corner[0]), abs(c - corner[1])) == 1:
            return -3.0
    if r in (0, last) or c in (0, last):
        return 2.0
    return 0.0


def _best_reply_gain(board: Board, player: Player) -> float:
    """The best `player` could get with a reply (blocks turned + value of the square)."""
    best = 0.0
    for pos in board.empty_cells():
        gain = len(flips_for(board, pos, player)) + positional_value(board, pos)
        best = max(best, gain)
    return best


def _score(board: Board, pos: Pos, player: Player, level: Level) -> float:
    flips = flips_for(board, pos, player)
    if level is Level.MEDIUM:
        return float(len(flips))
    gain = len(flips) + positional_value(board, pos)
    after, _ = apply_move(board, pos, player)
    return gain - 0.6 * _best_reply_gain(after, player.other)


def choose_move(board: Board, player: Player, level: Level,
                rng: random.Random) -> Optional[Pos]:
    """Chooses the computer's square. Returns None when no square is free."""
    empties = board.empty_cells()
    if not empties:
        return None
    if level is Level.EASY:
        return rng.choice(empties)
    scored = [(_score(board, pos, player, level), pos) for pos in empties]
    top = max(score for score, _ in scored)
    best = [pos for score, pos in scored if score >= top - 1e-9]
    return rng.choice(best)
