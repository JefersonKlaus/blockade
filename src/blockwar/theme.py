"""Cores e aparência de cada casa, em funções puras (fáceis de testar, sem Flet)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import Player

EMPTY = "#E2E8F0"
BOARD_BG = "#94A3B8"
BLUE = "#2563EB"
BLUE_LAST = "#1E3A8A"
ORANGE = "#F97316"
ORANGE_LAST = "#9A3412"
BLUE_TINT = "#BFDBFE"
ORANGE_TINT = "#FED7AA"
FLIP_PREVIEW = "#FACC15"
FLASH = "#FDE68A"
HINT = "#86EFAC"
WHITE = "#FFFFFF"
DARK = "#1E293B"
MUTED = "#475569"
BAR_EMPTY = "#CBD5E1"


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


def cell_look(owner: Optional[Player], current: Player, *, is_last: bool = False,
              is_pending: bool = False, is_flip: bool = False, is_hint: bool = False,
              is_flash: bool = False) -> CellLook:
    """Decide cor e símbolo de uma casa. Os estados mais importantes vêm primeiro."""
    if is_pending:  # a casa escolhida: cor clara do jogador da vez com o símbolo dele
        return CellLook(player_tint(current), current.symbol, player_color(current))
    if is_flip:  # blocos que vão virar: amarelo, já com o símbolo de quem vai ficar com eles
        return CellLook(FLIP_PREVIEW, current.symbol, DARK)
    if is_flash and owner is not None:  # acabou de virar: pisca antes de assentar
        return CellLook(FLASH, owner.symbol, DARK)
    if is_hint and owner is None:
        return CellLook(HINT, "?", DARK)
    if owner is None:
        return CellLook(EMPTY, "", MUTED)
    return CellLook(player_color(owner, is_last), owner.symbol, WHITE)


def bar_widths(blue: int, orange: int, total_width: int) -> tuple[int, int]:
    """Larguras da barra de força (azul à esquerda, laranja à direita)."""
    total = blue + orange
    if total <= 0:
        return 0, 0
    left = round(total_width * blue / total)
    return left, total_width - left


def cell_side(size: int) -> int:
    """Tamanho de cada casa em pixels: casas maiores nos tabuleiros menores."""
    return 58 if size <= 5 else 46
