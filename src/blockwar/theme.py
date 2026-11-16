"""Cores, tamanhos e aparência de cada casa, em funções puras (fáceis de testar, sem Flet).

Paleta pastel: fundos suaves, e o texto/símbolo sempre num tom escuro da mesma cor
("tinta"), para continuar fácil de ler (branco sobre pastel some).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bot import Level
from .models import MAX_BOARD, Player

# ------------------------------------------------------------------ paleta pastel

PAGE_BG = "#FFF8F0"       # creme: fundo de todas as telas
BOARD_BG = "#D8D2EC"      # lavanda: moldura do tabuleiro
EMPTY = "#F8F6FD"         # casa vazia

BLUE = "#A9CCF5"          # azul pastel (●)
BLUE_LAST = "#80B1EA"     # última jogada do azul, um pouco mais forte
BLUE_TINT = "#DCEBFB"     # casa escolhida pelo azul, antes de confirmar
BLUE_INK = "#1F4E85"      # símbolo/texto sobre azul

ORANGE = "#FFC5A6"        # pêssego pastel (▲)
ORANGE_LAST = "#F7A47C"
ORANGE_TINT = "#FFE6D8"
ORANGE_INK = "#8A3A12"

FLIP_PREVIEW = "#FBEA93"  # amarelo pastel: blocos que vão virar
FLASH = "#FFF3B8"         # piscada de quem acabou de virar
HINT = "#BDEBCB"          # menta: casa da dica

CARD_BG = "#EEE9F8"       # cartão/opção não escolhida
CARD_SELECTED = BLUE      # cartão/opção escolhida
BUTTON_BG = "#E6DEF6"     # botões comuns (lilás)
PLAY_BG = "#A8E6C1"       # botão Jogar! (verde menta, o mais chamativo)
BAR_EMPTY = "#ECE8F5"

# Níveis do celular: verde (fácil), amarelo (médio), vermelho (difícil), em pastel.
GREEN, GREEN_TINT, GREEN_INK = "#BDE5A8", "#E5F5DC", "#2B5A1E"
YELLOW, YELLOW_TINT, YELLOW_INK = "#FBE08A", "#FEF5D0", "#6A4E0B"
RED, RED_TINT, RED_INK = "#F5A8A8", "#FDE1E1", "#8A1F1F"

WHITE = "#FFFFFF"
DARK = "#3D3A5C"          # texto principal (ameixa escuro, mais suave que preto)
MUTED = "#7D7A99"         # texto secundário
SEED = BLUE               # cor-base do tema do Flet (botões, seleção de texto...)


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
    """Cor escura para símbolos e textos do jogador (legível sobre o pastel)."""
    return BLUE_INK if player is Player.BLUE else ORANGE_INK


@dataclass(frozen=True)
class CardLook:
    """Aparência de um cartão/opção. O escolhido ganha cor mais forte e uma borda."""

    bg: str
    fg: str
    border: Optional[str]    # cor da borda; None = sem borda (não escolhido)


def card_colors(selected: bool) -> tuple[str, str]:
    """Fundo e texto de um cartão ou opção: neutro quando não escolhido, azul pastel
    quando escolhido."""
    return (CARD_SELECTED, BLUE_INK) if selected else (CARD_BG, MUTED)


def card_look(selected: bool) -> CardLook:
    bg, fg = card_colors(selected)
    return CardLook(bg, fg, BLUE_INK if selected else None)


_LEVEL_COLORS = {
    Level.EASY: (GREEN, GREEN_TINT, GREEN_INK),
    Level.MEDIUM: (YELLOW, YELLOW_TINT, YELLOW_INK),
    Level.HARD: (RED, RED_TINT, RED_INK),
}


def level_look(level: Level, selected: bool) -> CardLook:
    """Cartão de nível: sempre na cor do nível (verde, amarelo, vermelho). O escolhido
    fica com a cor cheia e borda; os outros, com a mesma cor clarinha."""
    strong, tint, ink = _LEVEL_COLORS[level]
    return CardLook(strong, ink, ink) if selected else CardLook(tint, ink, None)


def cell_look(owner: Optional[Player], current: Player, *, is_last: bool = False,
              is_pending: bool = False, is_flip: bool = False, is_hint: bool = False,
              is_flash: bool = False) -> CellLook:
    """Decide cor e símbolo de uma casa. Os estados mais importantes vêm primeiro."""
    if is_pending:  # a casa escolhida: cor clara do jogador da vez com o símbolo dele
        return CellLook(player_tint(current), current.symbol, player_ink(current))
    if is_flip:  # blocos que vão virar: amarelo, já com o símbolo de quem vai ficar com eles
        return CellLook(FLIP_PREVIEW, current.symbol, DARK)
    if is_flash and owner is not None:  # acabou de virar: pisca antes de assentar
        return CellLook(FLASH, owner.symbol, DARK)
    if is_hint and owner is None:
        return CellLook(HINT, "?", DARK)
    if owner is None:
        return CellLook(EMPTY, "", MUTED)
    return CellLook(player_color(owner, is_last), owner.symbol, player_ink(owner))


def bar_widths(blue: int, orange: int, total_width: int) -> tuple[int, int]:
    """Larguras da barra de força (azul à esquerda, laranja à direita)."""
    total = blue + orange
    if total <= 0:
        return 0, 0
    left = round(total_width * blue / total)
    return left, total_width - left


# ------------------------------------------------------------------ tamanho do tabuleiro

GAP = 3                  # espaço entre as casas
BOARD_PADDING = 8        # borda do tabuleiro em volta das casas
TOUCH_CELL = 44          # menor casa confortável para o dedo de uma criança
MIN_GRID = 5             # celular pequeno: pelo menos 5×5
MAX_GRID = MAX_BOARD     # tablet grande: no máximo 14×14
RESERVED_HEIGHT = 250    # vez, placar, barra, mensagem e botões em volta do tabuleiro
DEFAULT_SPACE = 406      # espaço quando a tela ainda não informou o tamanho dela


def board_space(width: Optional[float], height: Optional[float], padding: float) -> float:
    """Lado do maior quadrado que cabe para o tabuleiro: a largura toda da tela, a não
    ser que a altura (menos o resto da tela de jogo) seja menor."""
    if not width or width <= 0:
        return DEFAULT_SPACE
    space = width - 2 * padding
    if height and height > 0:
        space = min(space, height - 2 * padding - RESERVED_HEIGHT)
    return max(space, 0)


def grid_size(space: float) -> int:
    """Quantas casas por lado: o maior tabuleiro em que cada casa ainda tem pelo menos
    `TOUCH_CELL` pixels. Celular ~7×7, tablet 10×10 ou mais, nunca mais que 14×14."""
    fits = int((space - 2 * BOARD_PADDING + GAP) // (TOUCH_CELL + GAP))
    return max(MIN_GRID, min(MAX_GRID, fits))


def cell_side(size: int, space: float) -> int:
    """Lado de cada casa para o tabuleiro ocupar todo o espaço."""
    inner = space - 2 * BOARD_PADDING - (size - 1) * GAP
    return max(1, int(inner // size))


def board_width(size: int, side: int) -> int:
    """Largura total do tabuleiro (casas + espaços + borda)."""
    return size * side + (size - 1) * GAP + 2 * BOARD_PADDING


def symbol_size(side: int) -> int:
    """Tamanho do ● / ▲ dentro de uma casa."""
    return int(side * 0.5)
