"""The flow of one game, without any screen: taps, questions, the phone's turn, undo.

The UI (ui/) only passes taps on to the `Match` and draws what it reports, so almost all
of the game's behaviour can be tested without opening Flet. Saving records and choices
is not done here: see records.py and storage.py.

The messages for the player (`message`, `turn_label()`...) come from the `Texts` the
match is given (see texts.py).
"""
from __future__ import annotations

import random
from enum import Enum
from typing import Optional

from .bot import Level, choose_move
from .choices import Setup
from .game import Game, MoveResult
from .mathmode import Question, make_question
from .models import BOT_PLAYER, HUMAN_PLAYER, Mode, Player, Pos
from .texts import Texts

UNDOS_PER_GAME = 3


class Phase(Enum):
    CHOOSING = "choosing"     # a person is choosing where to play
    QUESTION = "question"     # a person must answer the math question
    BOT_TURN = "bot_turn"     # the phone is about to play
    OVER = "over"


class Match:
    """A complete game with its interaction rules."""

    def __init__(self, setup: Setup, texts: Texts) -> None:
        self.setup = setup
        self.texts = texts
        self.rng = random.Random(setup.seed)
        self.game = Game(setup.size)
        self.pending: Optional[Pos] = None
        self.question: Optional[Question] = None
        self.hint_pos: Optional[Pos] = None
        self.undos_left = UNDOS_PER_GAME
        self.phase = Phase.CHOOSING
        self.last_flipped: tuple[Pos, ...] = ()
        self.message = texts.start_math if setup.math.enabled else texts.start

    # ------------------------------------------------------------- texts

    def name(self, player: Player) -> str:
        if self.setup.mode is Mode.BOT:
            return self.texts.you if player is HUMAN_PLAYER else self.texts.phone
        return self.texts.player(player)

    def score_line(self) -> str:
        counts = self.game.counts()
        return f"{counts[Player.BLUE]} × {counts[Player.ORANGE]}"

    def turn_label(self) -> str:
        if self.phase is Phase.OVER:
            return self.texts.game_over
        player = self.game.current
        if self.setup.mode is Mode.BOT:
            return self.texts.your_turn if player is HUMAN_PLAYER else self.texts.phone_turn
        return self.texts.player_turn.format(name=self.texts.player(player), symbol=player.symbol)

    def result_text(self) -> str:
        winner = self.game.winner
        if winner is None:
            return self.texts.draw
        if self.setup.mode is Mode.BOT:
            return self.texts.you_won if winner is HUMAN_PLAYER else self.texts.phone_won
        return self.texts.player_won.format(name=self.texts.player(winner))

    # ------------------------------------------------------------- queries

    @property
    def helpers_allowed(self) -> bool:
        """Hint and Undo are beginner helpers: only against the phone on the Easy level."""
        return self.setup.mode is Mode.BOT and self.setup.bot_level is Level.EASY

    @property
    def is_over(self) -> bool:
        return self.phase is Phase.OVER

    def preview_cells(self) -> tuple[Pos, ...]:
        """Blocks that would turn on the selected square."""
        if self.pending is None:
            return ()
        return self.game.preview(self.pending)

    # ------------------------------------------------------------- taps

    def tap(self, pos: Pos) -> str:
        """Handles a tap on a square. Returns 'ignored', 'selected', 'question' or 'played'."""
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
            self.message = self.texts.preview.format(blocks=self.texts.blocks(count))
        else:
            self.message = self.texts.preview_nothing
        return "selected"

    def confirm(self) -> str:
        """Confirms the selected square (asking a math question first, in math games)."""
        if self.phase is not Phase.CHOOSING or self.pending is None:
            return "ignored"
        if self.setup.math.enabled:
            self.question = make_question(self.setup.math, self.rng)
            self.phase = Phase.QUESTION
            self.message = self.texts.answer_prompt
            return "question"
        self._play(self.pending)
        return "played"

    def answer(self, choice: int) -> str:
        """Answers the question. Returns 'played' (right), 'skipped' (wrong) or 'ignored'."""
        if self.phase is not Phase.QUESTION or self.question is None or self.pending is None:
            return "ignored"
        if choice == self.question.answer:
            self._play(self.pending)
            return "played"
        right = self.question.answer
        result = self.game.skip()
        self._end_turn(result, self.texts.wrong_answer.format(
            answer=right, name=self.name(result.player)))
        return "skipped"

    def bot_move(self) -> Optional[MoveResult]:
        """Plays the phone's move (only when it is the phone's turn)."""
        if self.phase is not Phase.BOT_TURN:
            return None
        pos = choose_move(self.game.board, BOT_PLAYER, self.setup.bot_level, self.rng)
        return None if pos is None else self._play(pos)

    def _play(self, pos: Pos) -> MoveResult:
        result = self.game.play(pos)
        who, flipped = self.name(result.player), len(result.flipped)
        if flipped:
            message = self.texts.turned.format(name=who, blocks=self.texts.blocks(flipped))
        else:
            message = self.texts.placed.format(name=who)
        self._end_turn(result, message)
        return result

    def _end_turn(self, result: MoveResult, message: str) -> None:
        """After a turn (played or lost): clears the selection and decides who goes next."""
        self.pending = self.question = None
        self.last_flipped = result.flipped
        self.message = message
        if result.game_over:
            self.phase = Phase.OVER
            self.message = f"{self.result_text()} {self.score_line()}"
        elif self.setup.mode is Mode.BOT and self.game.current is BOT_PLAYER:
            self.phase = Phase.BOT_TURN
        else:
            self.phase = Phase.CHOOSING

    # ------------------------------------------------------------- beginner helpers

    def undo(self) -> bool:
        """Undoes the last turn (against the phone, also undoes the phone's reply)."""
        if not self.helpers_allowed:
            return False
        if self.phase is not Phase.CHOOSING or self.undos_left <= 0 or not self.game.can_undo:
            self.message = self.texts.cant_undo
            return False
        self.game.undo()
        if self.setup.mode is Mode.BOT:
            while self.game.current is BOT_PLAYER and self.game.can_undo:
                self.game.undo()
        self.undos_left -= 1
        self.pending = self.hint_pos = None
        self.last_flipped = ()
        self.message = self.texts.undone
        return True

    def hint(self) -> Optional[Pos]:
        """Suggests a square (a medium computer's choice; always the same for a position)."""
        if not self.helpers_allowed or self.phase is not Phase.CHOOSING:
            return None
        rng = random.Random(self.game.turn)
        self.hint_pos = choose_move(self.game.board, self.game.current, Level.MEDIUM, rng)
        self.pending = None
        self.message = self.texts.hint_message
        return self.hint_pos
