"""The immutable board and the capture rule (the heart of the game).

Rule: when a block is placed, in each of the 8 directions, a line of the opponent's
blocks followed by one of your own blocks turns entirely to your side. Captures do not
chain.
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
    """Square grid of empty squares (None) or squares taken by a player."""

    size: int
    cells: tuple[tuple[Cell, ...], ...]

    # ------------------------------------------------------------- creating

    @classmethod
    def initial(cls, size: int) -> "Board":
        """Starting board: 4 blocks in the centre, chequered (2 for each side)."""
        if not MIN_BOARD <= size <= MAX_BOARD:
            raise ValueError(f"size must be between {MIN_BOARD} and {MAX_BOARD}")
        mid = size // 2
        rows: list[list[Cell]] = [[None] * size for _ in range(size)]
        rows[mid - 1][mid - 1] = Player.BLUE
        rows[mid][mid] = Player.BLUE
        rows[mid - 1][mid] = Player.ORANGE
        rows[mid][mid - 1] = Player.ORANGE
        return cls(size, tuple(tuple(row) for row in rows))

    @classmethod
    def from_text(cls, lines: Sequence[str]) -> "Board":
        """Builds a board from text: 'B' blue, 'O' orange, '.' empty (handy in tests)."""
        size = len(lines)
        if any(len(line) != size for line in lines):
            raise ValueError("the text board must be square")
        table = {"B": Player.BLUE, "O": Player.ORANGE, ".": None}
        try:
            rows = tuple(tuple(table[ch] for ch in line) for line in lines)
        except KeyError as error:
            raise ValueError(f"invalid character: {error}") from None
        return cls(size, rows)

    # ------------------------------------------------------------- queries

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

    # ------------------------------------------------------------- changing

    def with_changes(self, changes: dict[Pos, Cell]) -> "Board":
        """Returns a new board with the given squares changed."""
        rows = [list(row) for row in self.cells]
        for (r, c), value in changes.items():
            rows[r][c] = value
        return Board(self.size, tuple(tuple(row) for row in rows))


def flips_for(board: Board, pos: Pos, player: Player) -> tuple[Pos, ...]:
    """Blocks that turn if `player` places a block at `pos` (empty if nothing turns)."""
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
    """Places the block and turns whatever is captured. Raises IllegalMove if it can't."""
    if not board.in_bounds(pos):
        raise IllegalMove(f"{pos} is off the board")
    if board.get(pos) is not None:
        raise IllegalMove(f"{pos} is already taken")
    flipped = flips_for(board, pos, player)
    changes: dict[Pos, Cell] = {pos: player}
    changes.update({p: player for p in flipped})
    return board.with_changes(changes), flipped
