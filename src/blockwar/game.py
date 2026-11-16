"""A partida: de quem é a vez, histórico para desfazer e fim de jogo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .board import Board, apply_move, flips_for
from .models import DEFAULT_SIZE, IllegalMove, Player, Pos


@dataclass(frozen=True)
class MoveResult:
    """O que aconteceu em uma vez: uma jogada normal ou uma vez perdida."""

    player: Player
    pos: Optional[Pos]          # None quando a vez foi perdida
    flipped: tuple[Pos, ...]
    skipped: bool
    game_over: bool


@dataclass(frozen=True)
class _Snapshot:
    board: Board
    current: Player
    last_move: Optional[Pos]
    turn: int


class Game:
    """Estado de uma partida entre Azul (começa) e Laranja.

    Qualquer casa vazia é uma jogada válida; capturar é uma consequência, não uma
    obrigação. A partida acaba quando o tabuleiro enche ou um lado fica sem blocos.
    """

    def __init__(self, size: int = DEFAULT_SIZE, board: Optional[Board] = None,
                 first: Player = Player.BLUE) -> None:
        self.board = board if board is not None else Board.initial(size)
        self.size = self.board.size
        self.current = first
        self.turn = 0                       # vezes já jogadas (inclui vezes perdidas)
        self.last_move: Optional[Pos] = None
        self._history: list[_Snapshot] = []

    # ------------------------------------------------------------- consulta

    @property
    def over(self) -> bool:
        counts = self.board.counts()
        return self.board.is_full or min(counts.values()) == 0

    @property
    def winner(self) -> Optional[Player]:
        """Quem tem mais blocos quando a partida terminou (None se empate ou em andamento)."""
        if not self.over:
            return None
        counts = self.board.counts()
        if counts[Player.BLUE] == counts[Player.ORANGE]:
            return None
        return Player.BLUE if counts[Player.BLUE] > counts[Player.ORANGE] else Player.ORANGE

    @property
    def is_draw(self) -> bool:
        return self.over and self.winner is None

    def counts(self) -> dict[Player, int]:
        return self.board.counts()

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def preview(self, pos: Pos) -> tuple[Pos, ...]:
        """O que viraria se o jogador da vez jogasse em `pos` (não altera nada)."""
        return flips_for(self.board, pos, self.current)

    # ------------------------------------------------------------- jogadas

    def _save(self) -> None:
        self._history.append(_Snapshot(self.board, self.current, self.last_move, self.turn))

    def play(self, pos: Pos) -> MoveResult:
        """O jogador da vez coloca um bloco em `pos`."""
        if self.over:
            raise IllegalMove("a partida já terminou")
        new_board, flipped = apply_move(self.board, pos, self.current)  # valida a casa
        self._save()
        player = self.current
        self.board = new_board
        self.last_move = pos
        self.current = player.other
        self.turn += 1
        return MoveResult(player, pos, flipped, False, self.over)

    def skip(self) -> MoveResult:
        """O jogador da vez perde a vez (usado no modo contas quando ele erra)."""
        if self.over:
            raise IllegalMove("a partida já terminou")
        self._save()
        player = self.current
        self.current = player.other
        self.last_move = None
        self.turn += 1
        return MoveResult(player, None, (), True, self.over)

    def undo(self) -> bool:
        """Volta uma vez. Devolve False se não há nada para desfazer."""
        if not self._history:
            return False
        snap = self._history.pop()
        self.board, self.current = snap.board, snap.current
        self.last_move, self.turn = snap.last_move, snap.turn
        return True
