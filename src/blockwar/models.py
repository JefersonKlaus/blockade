"""Tipos básicos compartilhados: jogadores, posições e erros."""
from __future__ import annotations

from enum import Enum
from typing import Tuple

# Uma posição no tabuleiro: (linha, coluna), começando em zero no canto superior esquerdo.
Pos = Tuple[int, int]

VALID_SIZES = (5, 7)  # tamanhos do menu (ambos ímpares: sem empate com tabuleiro cheio)
DEFAULT_SIZE = 7
MIN_BOARD, MAX_BOARD = 4, 9  # limites aceitos pelo motor


class Player(Enum):
    """Os dois lados da guerra. Cada um tem cor e símbolo (ajuda quem não distingue cores)."""

    BLUE = "azul"
    ORANGE = "laranja"

    @property
    def other(self) -> "Player":
        return Player.ORANGE if self is Player.BLUE else Player.BLUE

    @property
    def label(self) -> str:
        return self.value.capitalize()

    @property
    def symbol(self) -> str:
        return "●" if self is Player.BLUE else "▲"  # círculo / triângulo

    @property
    def letter(self) -> str:
        """Letra usada nos tabuleiros de texto dos testes: B ou O."""
        return "B" if self is Player.BLUE else "O"


class IllegalMove(ValueError):
    """Jogada impossível: fora do tabuleiro, casa ocupada ou partida já terminada."""
