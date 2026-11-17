"""One game: whose turn it is, the history for undo, and the end of the game."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .board import Board, apply_move, flips_for
from .models import DEFAULT_SIZE, IllegalMove, Player, Pos


@dataclass(frozen=True)
class MoveResult:
    """What happened in one turn: a normal move or a lost turn."""

    player: Player
    pos: Optional[Pos]          # None when the turn was lost
    flipped: tuple[Pos, ...]
    game_over: bool


@dataclass(frozen=True)
class _Snapshot:
    board: Board
    current: Player
    last_move: Optional[Pos]
    turn: int


class Game:
    """State of a game between Blue (starts) and Orange.

    Any empty square is a valid move; capturing is a consequence, not a requirement.
    The game ends when the board is full or one side has no blocks left.
    """

    def __init__(self, size: int = DEFAULT_SIZE, board: Optional[Board] = None) -> None:
        self.board = board if board is not None else Board.initial(size)
        self.size = self.board.size
        self.current = Player.BLUE
        self.turn = 0                       # turns played so far (lost turns included)
        self.last_move: Optional[Pos] = None
        self._history: list[_Snapshot] = []

    # ------------------------------------------------------------- queries

    @property
    def over(self) -> bool:
        counts = self.board.counts()
        return self.board.is_full or min(counts.values()) == 0

    @property
    def winner(self) -> Optional[Player]:
        """Who has more blocks once the game is over (None for a draw or a game in progress)."""
        if not self.over:
            return None
        blue, orange = self.board.count(Player.BLUE), self.board.count(Player.ORANGE)
        if blue == orange:
            return None
        return Player.BLUE if blue > orange else Player.ORANGE

    def counts(self) -> dict[Player, int]:
        return self.board.counts()

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def preview(self, pos: Pos) -> tuple[Pos, ...]:
        """What would turn if the current player played at `pos` (changes nothing)."""
        return flips_for(self.board, pos, self.current)

    # ------------------------------------------------------------- moves

    def play(self, pos: Pos) -> MoveResult:
        """The current player places a block at `pos`."""
        self._check_not_over()
        new_board, flipped = apply_move(self.board, pos, self.current)  # checks the square
        return self._next_turn(new_board, pos, flipped)

    def skip(self) -> MoveResult:
        """The current player loses the turn (used in math games after a wrong answer)."""
        self._check_not_over()
        return self._next_turn(self.board, None, ())

    def _check_not_over(self) -> None:
        if self.over:
            raise IllegalMove("the game is already over")

    def _next_turn(self, board: Board, pos: Optional[Pos],
                   flipped: tuple[Pos, ...]) -> MoveResult:
        """Saves the current state (for undo) and passes the turn to the other player."""
        self._history.append(_Snapshot(self.board, self.current, self.last_move, self.turn))
        player = self.current
        self.board, self.last_move = board, pos
        self.current = player.other
        self.turn += 1
        return MoveResult(player, pos, flipped, self.over)

    def undo(self) -> bool:
        """Goes back one turn. Returns False when there is nothing to undo."""
        if not self._history:
            return False
        snap = self._history.pop()
        self.board, self.current = snap.board, snap.current
        self.last_move, self.turn = snap.last_move, snap.turn
        return True
