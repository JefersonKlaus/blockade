"""The game screen's controls: built once, then only painted with the `Match` state.

It decides nothing about the game: every tap is passed on to whoever implements
`GameActions` (game_screen.py).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol

import flet as ft

from .. import layout, theme
from ..controller import Match, Phase
from ..models import Player, Pos
from ..texts import Texts
from .widgets import button

HELP_SIZE = 40      # the "?" (tutorial) button in the top-right corner


class GameActions(Protocol):
    """What the game screen does with each tap."""

    async def on_cell(self, pos: Pos) -> None: ...
    async def on_answer(self, value: int) -> None: ...
    def on_hint(self, event: Any) -> None: ...
    def on_undo(self, event: Any) -> None: ...
    def on_help(self, event: Any) -> None: ...
    def on_new(self, event: Any) -> None: ...
    def on_menu(self, event: Any) -> None: ...


class GameView:
    """Whose turn it is (with the "?"), score, score bar, board, message, math question,
    end of game and the bottom buttons."""

    def __init__(self, actions: GameActions, size: int, space: float, texts: Texts) -> None:
        self.actions = actions
        self.texts = texts
        self.size = size
        self._measure(space)
        self.turn_text = ft.Text(size=22, weight=ft.FontWeight.BOLD, color=theme.DARK,
                                 text_align=ft.TextAlign.CENTER, expand=True)
        self.btn_help = ft.Container(
            content=ft.Text("?", size=22, weight=ft.FontWeight.BOLD, color=theme.BLUE_INK),
            width=HELP_SIZE, height=HELP_SIZE, border_radius=HELP_SIZE // 2,
            bgcolor=theme.BUTTON_BG, alignment=ft.Alignment(0, 0), ink=True,
            tooltip=texts.how_to_play, on_click=actions.on_help)
        # Whose turn in the middle, "?" in the right corner; the empty space on the left is
        # as wide as the "?" so the text is truly centred.
        self.top_bar = ft.Row(controls=[ft.Container(width=HELP_SIZE), self.turn_text,
                                        self.btn_help],
                              vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.blue_text = ft.Text(size=16, weight=ft.FontWeight.BOLD, color=theme.BLUE_INK)
        self.orange_text = ft.Text(size=16, weight=ft.FontWeight.BOLD, color=theme.ORANGE_INK)
        self.scores = ft.Row(controls=[self.blue_text, self.orange_text],
                             alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self.bar_blue = ft.Container(height=14, width=0, bgcolor=theme.BLUE)
        self.bar_orange = ft.Container(height=14, width=0, bgcolor=theme.ORANGE)
        self.bar = ft.Container(content=ft.Row(controls=[self.bar_blue, self.bar_orange],
                                               spacing=0),
                                bgcolor=theme.BAR_EMPTY, border_radius=7)
        self.message = ft.Text(size=15, weight=ft.FontWeight.W_500, color=theme.DARK,
                               text_align=ft.TextAlign.CENTER)
        self.question_box = ft.Column(controls=[], visible=False, spacing=8,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.end_title = ft.Text(size=24, weight=ft.FontWeight.BOLD, color=theme.DARK)
        self.end_record = ft.Text(size=13, color=theme.MUTED)
        self.end_box = ft.Column(controls=[
            self.end_title, self.end_record,
            ft.Row(controls=[button(texts.play_again, actions.on_new, bg=theme.PLAY_BG),
                             button(texts.menu, actions.on_menu)],
                   alignment=ft.MainAxisAlignment.CENTER),
        ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.btn_hint = button(texts.hint, actions.on_hint)
        self.btn_undo = button("", actions.on_undo)   # label (with undos left): paint()
        # Bottom bar during the game; at the end, the end_box (with its own "Menu") takes
        # its place.
        self.toolbar = ft.Row(controls=[self.btn_hint, self.btn_undo,
                                        button(texts.menu, actions.on_menu)],
                              alignment=ft.MainAxisAlignment.CENTER)
        self.board = self._board()
        self.root = ft.Column(controls=[
            self.top_bar, self.scores, self.bar, self.board, self.message,
            self.question_box, self.end_box, self.toolbar,
        ], spacing=10, scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self._fit_rows()

    # ------------------------------------------------------------------ size

    def _measure(self, space: float) -> None:
        self.side = layout.cell_side(self.size, space)
        self.board_width = layout.board_width(self.size, self.side)

    def _board(self) -> ft.Container:
        self.cells: list[list[ft.Container]] = []
        self.labels: list[list[ft.Text]] = []
        for r in range(self.size):
            cell_row, label_row = [], []
            for c in range(self.size):
                label = ft.Text("", size=layout.symbol_size(self.side),
                                weight=ft.FontWeight.BOLD, color=theme.MUTED)
                cell_row.append(ft.Container(
                    width=self.side, height=self.side, border_radius=6, bgcolor=theme.EMPTY,
                    content=ft.Column(controls=[label], alignment=ft.MainAxisAlignment.CENTER,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    on_click=self._tap((r, c))))
                label_row.append(label)
            self.cells.append(cell_row)
            self.labels.append(label_row)
        grid = ft.Column(controls=[ft.Row(controls=list(row), spacing=layout.GAP)
                                   for row in self.cells], spacing=layout.GAP)
        return ft.Container(content=grid, padding=layout.BOARD_PADDING, bgcolor=theme.BOARD_BG,
                            border_radius=10)

    def resize(self, space: float) -> None:
        """The screen changed size: the same squares, resized to the new space."""
        self._measure(space)
        for row, label_row in zip(self.cells, self.labels, strict=True):
            for cell, label in zip(row, label_row, strict=True):
                cell.width = cell.height = self.side
                label.size = layout.symbol_size(self.side)
        self._fit_rows()

    def _fit_rows(self) -> None:
        """Everything as wide as the board: so it all lines up in the middle of the screen,
        even in a wide (landscape) window."""
        for row in (self.top_bar, self.scores, self.bar, self.board):
            row.width = self.board_width

    # ------------------------------------------------------------------ taps

    def _tap(self, pos: Pos) -> Callable[[Any], Awaitable[None]]:
        async def handler(_event: Any) -> None:
            await self.actions.on_cell(pos)
        return handler

    def _answer(self, value: int) -> Callable[[Any], Awaitable[None]]:
        async def handler(_event: Any) -> None:
            await self.actions.on_answer(value)
        return handler

    # ------------------------------------------------------------------ painting

    def paint(self, match: Match, flash: set[Pos], busy: bool, record: str) -> None:
        """Updates every control with the game state (without `page.update()`)."""
        self._paint_board(match, flash)
        self._paint_scores(match)
        self.turn_text.value = match.turn_label()
        self.message.value = match.message
        # Hint and Undo only exist on the Easy level against the phone (beginner helpers).
        self.btn_hint.visible = self.btn_undo.visible = match.helpers_allowed
        self.btn_undo.content = self.texts.undo.format(count=match.undos_left)
        can_act = match.phase is Phase.CHOOSING and not busy
        self.btn_hint.disabled = not can_act
        self.btn_undo.disabled = (not can_act or not match.game.can_undo
                                  or match.undos_left <= 0)
        self._paint_question(match)
        self.end_box.visible = match.is_over
        self.toolbar.visible = not match.is_over   # only one "Menu" on screen
        if match.is_over:
            self.end_title.value = f"{match.result_text()} {match.score_line()}"
            self.end_record.value = record

    def _paint_board(self, match: Match, flash: set[Pos]) -> None:
        game = match.game
        preview = set(match.preview_cells())
        for r in range(game.size):
            for c in range(game.size):
                pos = (r, c)
                look = theme.cell_look(
                    game.board.get(pos), game.current, is_last=pos == game.last_move,
                    is_pending=pos == match.pending, is_flip=pos in preview,
                    is_hint=pos == match.hint_pos, is_flash=pos in flash)
                self.cells[r][c].bgcolor = look.bg
                self.labels[r][c].value = look.symbol
                self.labels[r][c].color = look.fg

    def _paint_scores(self, match: Match) -> None:
        counts = match.game.counts()
        blue, orange = counts[Player.BLUE], counts[Player.ORANGE]
        self.blue_text.value = f"{Player.BLUE.symbol} {match.name(Player.BLUE)}: {blue}"
        self.orange_text.value = f"{Player.ORANGE.symbol} {match.name(Player.ORANGE)}: {orange}"
        self.bar_blue.width, self.bar_orange.width = layout.bar_widths(blue, orange,
                                                                        self.board_width)

    def _paint_question(self, match: Match) -> None:
        question = match.question
        self.question_box.visible = match.phase is Phase.QUESTION and question is not None
        if not self.question_box.visible or question is None:
            self.question_box.controls = []
            return
        self.question_box.controls = [
            ft.Text(question.text, size=28, weight=ft.FontWeight.BOLD, color=theme.DARK),
            ft.Row(controls=[button(
                str(value), self._answer(value), height=52,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD)))
                for value in question.choices],
                   alignment=ft.MainAxisAlignment.CENTER, wrap=True),
        ]
