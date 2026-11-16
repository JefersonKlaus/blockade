"""Tabuleiro imutável e a regra de captura (o coração do jogo).

Regra: ao colocar um bloco, em cada uma das 8 direções, se houver uma fila de blocos
inimigos seguida de um bloco seu, toda a fila vira sua. Capturas não encadeiam.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .models import MAX_BOARD, MIN_BOARD, IllegalMove, Player, Pos

DIRECTIONS: tuple[Pos, ...] = tuple(
    (dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))

Cell = Optional[Player]


@dataclass(frozen=True)
class Board:
    """Grade quadrada de casas vazias (None) ou ocupadas por um jogador."""

    size: int
    cells: tuple[tuple[Cell, ...], ...]

    # ------------------------------------------------------------- criação

    @classmethod
    def initial(cls, size: int) -> "Board":
        """Tabuleiro inicial: 4 blocos no centro, em xadrez (2 de cada lado)."""
        if not MIN_BOARD <= size <= MAX_BOARD:
            raise ValueError(f"tamanho deve estar entre {MIN_BOARD} e {MAX_BOARD}")
        mid = size // 2
        rows: list[list[Cell]] = [[None] * size for _ in range(size)]
        rows[mid - 1][mid - 1] = Player.BLUE
        rows[mid][mid] = Player.BLUE
        rows[mid - 1][mid] = Player.ORANGE
        rows[mid][mid - 1] = Player.ORANGE
        return cls(size, tuple(tuple(row) for row in rows))

    @classmethod
    def from_text(cls, lines: Sequence[str]) -> "Board":
        """Monta um tabuleiro a partir de texto: 'B' azul, 'O' laranja, '.' vazio."""
        size = len(lines)
        if any(len(line) != size for line in lines):
            raise ValueError("o tabuleiro de texto precisa ser quadrado")
        table = {"B": Player.BLUE, "O": Player.ORANGE, ".": None}
        try:
            rows = tuple(tuple(table[ch] for ch in line) for line in lines)
        except KeyError as error:
            raise ValueError(f"caractere inválido: {error}") from None
        return cls(size, rows)

    def to_text(self) -> list[str]:
        return ["".join(c.letter if c else "." for c in row) for row in self.cells]

    # ------------------------------------------------------------- consulta

    def in_bounds(self, pos: Pos) -> bool:
        return 0 <= pos[0] < self.size and 0 <= pos[1] < self.size

    def get(self, pos: Pos) -> Cell:
        return self.cells[pos[0]][pos[1]]

    def positions(self) -> Iterable[Pos]:
        for r in range(self.size):
            for c in range(self.size):
                yield (r, c)

    def empty_cells(self) -> list[Pos]:
        return [pos for pos in self.positions() if self.get(pos) is None]

    def count(self, player: Player) -> int:
        return sum(1 for row in self.cells for cell in row if cell is player)

    def counts(self) -> dict[Player, int]:
        return {Player.BLUE: self.count(Player.BLUE), Player.ORANGE: self.count(Player.ORANGE)}

    @property
    def is_full(self) -> bool:
        return all(cell is not None for row in self.cells for cell in row)

    @property
    def corners(self) -> tuple[Pos, ...]:
        last = self.size - 1
        return ((0, 0), (0, last), (last, 0), (last, last))

    # ------------------------------------------------------------- mudança

    def with_changes(self, changes: dict[Pos, Cell]) -> "Board":
        """Devolve um tabuleiro novo com as casas indicadas alteradas."""
        rows = [list(row) for row in self.cells]
        for (r, c), value in changes.items():
            rows[r][c] = value
        return Board(self.size, tuple(tuple(row) for row in rows))


def flips_for(board: Board, pos: Pos, player: Player) -> tuple[Pos, ...]:
    """Blocos que viram se `player` colocar um bloco em `pos` (vazio se nada vira)."""
    if not board.in_bounds(pos) or board.get(pos) is not None:
        return ()
    flipped: list[Pos] = []
    for dr, dc in DIRECTIONS:
        line: list[Pos] = []
        r, c = pos[0] + dr, pos[1] + dc
        while board.in_bounds((r, c)) and board.get((r, c)) is player.other:
            line.append((r, c))
            r, c = r + dr, c + dc
        if line and board.in_bounds((r, c)) and board.get((r, c)) is player:
            flipped.extend(line)
    return tuple(flipped)


def apply_move(board: Board, pos: Pos, player: Player) -> tuple[Board, tuple[Pos, ...]]:
    """Coloca o bloco e vira o que for capturado. Levanta IllegalMove se não der."""
    if not board.in_bounds(pos):
        raise IllegalMove(f"{pos} está fora do tabuleiro")
    if board.get(pos) is not None:
        raise IllegalMove(f"{pos} já está ocupada")
    flipped = flips_for(board, pos, player)
    changes: dict[Pos, Cell] = {pos: player}
    changes.update({p: player for p in flipped})
    return board.with_changes(changes), flipped
