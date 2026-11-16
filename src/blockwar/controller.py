"""O fluxo de uma partida, sem nenhuma tela: toques, perguntas, vez do robô, desfazer.

A interface (ui.py) só repassa os toques para o `Match` e desenha o que ele informa.
Assim, quase todo o comportamento do jogo pode ser testado sem abrir o Flet.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .bot import Level, choose_move, level_from_value
from .game import Game, MoveResult
from .mathmode import Question, is_correct, make_question
from .models import DEFAULT_SIZE, Player, Pos
from .storage import SaveData, record_for, record_outcome

BOT_PLAYER = Player.ORANGE
HUMAN_PLAYER = Player.BLUE
UNDOS_PER_GAME = 3


class Mode(Enum):
    BOT = "bot"      # você (Azul) contra o celular (Laranja)
    TWO = "dois"     # pai e filho no mesmo aparelho


class Phase(Enum):
    CHOOSING = "escolhendo"   # um humano escolhe onde jogar
    QUESTION = "pergunta"     # um humano precisa responder a conta
    BOT_TURN = "robo"         # o celular vai jogar
    OVER = "fim"


@dataclass
class Setup:
    """Escolhas do menu."""

    mode: Mode = Mode.BOT
    size: int = DEFAULT_SIZE
    bot_level: Level = Level.MEDIUM
    math_level: int = 0          # 0 = sem contas
    seed: Optional[int] = None

    @property
    def record_key(self) -> Optional[str]:
        """Chave do recorde (só existe contra o celular)."""
        if self.mode is not Mode.BOT:
            return None
        return f"{self.size}:{self.bot_level.value}:{self.math_level}"


def setup_from_save(data: SaveData) -> Setup:
    return Setup(mode=Mode.TWO if data.mode == "dois" else Mode.BOT, size=data.size,
                 bot_level=level_from_value(data.bot_level), math_level=data.math_level)


def store_setup(data: SaveData, setup: Setup) -> None:
    data.size, data.mode = setup.size, setup.mode.value
    data.bot_level, data.math_level = setup.bot_level.value, setup.math_level


def blocks_word(count: int) -> str:
    return "1 bloco" if count == 1 else f"{count} blocos"


def record_summary(data: SaveData, setup: Setup) -> str:
    """Texto do recorde para as escolhas do menu (vazio no modo pai e filho)."""
    key = setup.record_key
    if key is None:
        return ""
    entry = record_for(data, key)
    return (f"Neste nível: {entry['wins']} vitórias, {entry['losses']} derrotas, "
            f"{entry['draws']} empates")


class Match:
    """Uma partida completa com as regras de interação."""

    def __init__(self, setup: Setup) -> None:
        self.setup = setup
        self.rng = random.Random(setup.seed)
        self.game = Game(setup.size)
        self.pending: Optional[Pos] = None
        self.question: Optional[Question] = None
        self.hint_pos: Optional[Pos] = None
        self.undos_left = UNDOS_PER_GAME
        self.phase = Phase.CHOOSING
        self.message = ""
        self.last_flipped: tuple[Pos, ...] = ()
        self.recorded = False
        self._set_turn_message()

    # ------------------------------------------------------------- textos

    def name(self, player: Player) -> str:
        if self.setup.mode is Mode.BOT:
            return "Você" if player is HUMAN_PLAYER else "Celular"
        return player.label

    def score_line(self) -> str:
        counts = self.game.counts()
        return f"{counts[Player.BLUE]} × {counts[Player.ORANGE]}"

    def turn_label(self) -> str:
        if self.phase is Phase.OVER:
            return "Fim de jogo"
        player = self.game.current
        if self.setup.mode is Mode.BOT:
            return "Sua vez" if player is HUMAN_PLAYER else "Vez do celular"
        return f"Vez do {player.label} {player.symbol}"

    def _set_turn_message(self) -> None:
        if self.setup.math_level:
            self.message = "Toque numa casa. Depois de confirmar, responda a conta."
        else:
            self.message = "Toque numa casa para ver o que vira."

    def result_text(self) -> str:
        winner = self.game.winner
        if winner is None:
            return "Empate!"
        if self.setup.mode is Mode.BOT:
            return "Você venceu!" if winner is HUMAN_PLAYER else "O celular venceu desta vez."
        return f"{winner.label} venceu!"

    # ------------------------------------------------------------- consulta

    @property
    def is_over(self) -> bool:
        return self.phase is Phase.OVER

    def preview_cells(self) -> tuple[Pos, ...]:
        """Blocos que virariam na casa selecionada."""
        if self.pending is None:
            return ()
        return self.game.preview(self.pending)

    # ------------------------------------------------------------- toques

    def tap(self, pos: Pos) -> str:
        """Trata um toque numa casa. Devolve 'ignored', 'selected', 'question' ou 'played'."""
        if self.phase is not Phase.CHOOSING:
            return "ignored"
        if not self.game.board.in_bounds(pos) or self.game.board.get(pos) is not None:
            return "ignored"
        self.hint_pos = None
        if self.pending == pos:
            return self.confirm()
        self.pending = pos
        count = len(self.game.preview(pos))
        if count:
            self.message = f"Vira {blocks_word(count)}. Toque de novo para jogar."
        else:
            self.message = "Não vira nada. Toque de novo para jogar mesmo assim."
        return "selected"

    def confirm(self) -> str:
        """Confirma a casa selecionada (pergunta uma conta antes, se o modo estiver ligado)."""
        if self.phase is not Phase.CHOOSING or self.pending is None:
            return "ignored"
        if self.setup.math_level:
            self.question = make_question(self.setup.math_level, self.rng)
            self.phase = Phase.QUESTION
            self.message = "Responda certo para colocar o bloco!"
            return "question"
        self._play(self.pending)
        return "played"

    def answer(self, choice: int) -> str:
        """Responde a conta. Devolve 'played' (acertou), 'skipped' (errou) ou 'ignored'."""
        if self.phase is not Phase.QUESTION or self.question is None or self.pending is None:
            return "ignored"
        if is_correct(self.question, choice):
            self._play(self.pending)
            return "played"
        right = self.question.answer
        self.pending = None
        self.question = None
        result = self.game.skip()
        self.last_flipped = ()
        self.message = f"Errou! A resposta era {right}. {self.name(result.player)} perdeu a vez."
        self._after_turn(result)
        return "skipped"

    def _play(self, pos: Pos) -> None:
        player = self.game.current
        result = self.game.play(pos)
        self.last_flipped = result.flipped
        self.pending = None
        self.question = None
        who = self.name(player)
        self.message = (f"{who} virou {blocks_word(len(result.flipped))}."
                        if result.flipped else f"{who} colocou um bloco.")
        self._after_turn(result)

    def _after_turn(self, result: MoveResult) -> None:
        if result.game_over:
            self.phase = Phase.OVER
            self.message = f"{self.result_text()} {self.score_line()}"
        elif self.setup.mode is Mode.BOT and self.game.current is BOT_PLAYER:
            self.phase = Phase.BOT_TURN
        else:
            self.phase = Phase.CHOOSING

    # ------------------------------------------------------------- celular

    def bot_move(self) -> Optional[MoveResult]:
        """Faz a jogada do celular (só vale quando é a vez dele)."""
        if self.phase is not Phase.BOT_TURN:
            return None
        pos = choose_move(self.game.board, BOT_PLAYER, self.setup.bot_level, self.rng)
        if pos is None:
            return None
        self._play(pos)
        return MoveResult(BOT_PLAYER, pos, self.last_flipped, False, self.game.over)

    # ------------------------------------------------------------- extras

    def undo(self) -> bool:
        """Desfaz a última vez (contra o celular, desfaz também a resposta dele)."""
        if self.phase is not Phase.CHOOSING or self.undos_left <= 0 or not self.game.can_undo:
            return False
        self.game.undo()
        if self.setup.mode is Mode.BOT:
            while self.game.current is BOT_PLAYER and self.game.can_undo:
                self.game.undo()
        self.undos_left -= 1
        self.pending = self.hint_pos = None
        self.last_flipped = ()
        self.message = "Jogada desfeita."
        return True

    def hint(self) -> Optional[Pos]:
        """Sugere uma casa (a escolha de um robô médio, sempre a mesma para a mesma posição)."""
        if self.phase is not Phase.CHOOSING:
            return None
        rng = random.Random(self.game.turn)
        self.hint_pos = choose_move(self.game.board, self.game.current, Level.MEDIUM, rng)
        self.pending = None
        self.message = "Dica: a casa verde vira bastante coisa."
        return self.hint_pos

    def record(self, data: SaveData) -> Optional[str]:
        """Registra o resultado (uma vez só) e devolve 'wins', 'losses', 'draws' ou None."""
        key = self.setup.record_key
        if not self.is_over or self.recorded or key is None:
            return None
        self.recorded = True
        winner = self.game.winner
        outcome = "draws" if winner is None else ("wins" if winner is HUMAN_PLAYER else "losses")
        record_outcome(data, key, outcome)
        return outcome

    def record_text(self, data: SaveData) -> str:
        return record_summary(data, self.setup)
