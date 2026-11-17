"""Colours and the look of squares and cards, as pure functions (easy to test, no Flet).

Sizes (of the board and the squares) live in layout.py.

Pastel palette: soft backgrounds, with text and symbols always in a dark shade of the
same colour ("ink"), so everything stays easy to read (white on pastel disappears).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bot import Level
from .models import Player

# ------------------------------------------------------------------ pastel palette

PAGE_BG = "#FFF8F0"       # cream: background of every screen
BOARD_BG = "#D8D2EC"      # lavender: the board's frame
EMPTY = "#F8F6FD"         # empty square

BLUE = "#A9CCF5"          # pastel blue (●)
BLUE_LAST = "#80B1EA"     # blue's last move, a little stronger
BLUE_TINT = "#DCEBFB"     # square chosen by blue, before confirming
BLUE_INK = "#1F4E85"      # symbol/text on blue

ORANGE = "#FFC5A6"        # pastel peach (▲)
ORANGE_LAST = "#F7A47C"
ORANGE_TINT = "#FFE6D8"
ORANGE_INK = "#8A3A12"

FLIP_PREVIEW = "#FBEA93"  # pastel yellow: blocks that will turn
FLASH = "#FFF3B8"         # flash of blocks that have just turned
HINT = "#BDEBCB"          # mint: the hinted square

CARD_BG = "#EEE9F8"       # card/option not chosen
CARD_SELECTED = BLUE      # card/option chosen
BUTTON_BG = "#E6DEF6"     # ordinary buttons (lilac)
PLAY_BG = "#A8E6C1"       # the Play button (mint green, the most eye-catching)
BAR_EMPTY = "#ECE8F5"

# The phone's levels: green (easy), yellow (medium), red (hard), in pastel.
GREEN, GREEN_TINT, GREEN_INK = "#BDE5A8", "#E5F5DC", "#2B5A1E"
YELLOW, YELLOW_TINT, YELLOW_INK = "#FBE08A", "#FEF5D0", "#6A4E0B"
RED, RED_TINT, RED_INK = "#F5A8A8", "#FDE1E1", "#8A1F1F"

DARK = "#3D3A5C"          # main text (dark plum, softer than black)
MUTED = "#7D7A99"         # secondary text
SEED = BLUE               # base colour of the Flet theme (buttons, text selection...)


@dataclass(frozen=True)
class CellLook:
    bg: str
    symbol: str
    fg: str


def player_color(player: Player, last: bool = False) -> str:
    if player is Player.BLUE:
        return BLUE_LAST if last else BLUE
    return ORANGE_LAST if last else ORANGE


def player_tint(player: Player) -> str:
    return BLUE_TINT if player is Player.BLUE else ORANGE_TINT


def player_ink(player: Player) -> str:
    """Dark colour for the player's symbols and texts (readable on the pastel)."""
    return BLUE_INK if player is Player.BLUE else ORANGE_INK


def page_color(turn: Optional[Player]) -> str:
    """Screen background: during a game, the light colour of whoever plays now, so
    everyone can see whose turn it is. With nobody's turn (menu, game over), the usual
    cream."""
    return PAGE_BG if turn is None else player_tint(turn)


@dataclass(frozen=True)
class CardLook:
    """Look of a card/option. The chosen one gets a stronger colour and a border."""

    bg: str
    fg: str
    border: Optional[str]    # border colour; None = no border (not chosen)


def card_look(selected: bool) -> CardLook:
    """Ordinary card or option: neutral when not chosen, pastel blue with a border when
    chosen."""
    if selected:
        return CardLook(CARD_SELECTED, BLUE_INK, BLUE_INK)
    return CardLook(CARD_BG, MUTED, None)


_LEVEL_COLORS = {
    Level.EASY: (GREEN, GREEN_TINT, GREEN_INK),
    Level.MEDIUM: (YELLOW, YELLOW_TINT, YELLOW_INK),
    Level.HARD: (RED, RED_TINT, RED_INK),
}


def level_look(level: Level, selected: bool) -> CardLook:
    """Level card: always in the level's colour (green, yellow, red). The chosen one gets
    the full colour and a border; the others, a light shade of the same colour."""
    strong, tint, ink = _LEVEL_COLORS[level]
    return CardLook(strong, ink, ink) if selected else CardLook(tint, ink, None)


def cell_look(owner: Optional[Player], current: Player, *, is_last: bool = False,
              is_pending: bool = False, is_flip: bool = False, is_hint: bool = False,
              is_flash: bool = False) -> CellLook:
    """Decides a square's colour and symbol. The most important states come first."""
    if is_pending:  # the chosen square: light colour of the current player, with their symbol
        return CellLook(player_tint(current), current.symbol, player_ink(current))
    if is_flip:  # blocks that will turn: yellow, already with the symbol of their new owner
        return CellLook(FLIP_PREVIEW, current.symbol, DARK)
    if is_flash and owner is not None:  # just turned: flashes before settling
        return CellLook(FLASH, owner.symbol, DARK)
    if is_hint and owner is None:
        return CellLook(HINT, "?", DARK)
    if owner is None:
        return CellLook(EMPTY, "", MUTED)
    return CellLook(player_color(owner, is_last), owner.symbol, player_ink(owner))
