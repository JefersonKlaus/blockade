"""Interface Flet: menu e partida. Toda a regra do jogo vive em controller.py.

Esta tela é por turnos (nada de laço de 60 quadros), o que combina bem com o Flet.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

import flet as ft

from . import theme
from .bot import Level
from .controller import Match, Mode, Phase, Setup, record_summary, setup_from_save, store_setup
from .mathmode import LEVEL_NAMES
from .models import VALID_SIZES, Player, Pos
from .storage import SaveData, load_save, save_save

logger = logging.getLogger(__name__)

FLIP_DELAY = 0.35   # quanto tempo os blocos virados piscam
BOT_DELAY = 0.6     # "pensando" do celular, para o jogador acompanhar
GAP = 3             # espaço entre as casas


class BlocksApp:
    """Liga as telas ao `Match` (a partida) e ao arquivo de recordes."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.save: SaveData = load_save()
        self.setup: Setup = setup_from_save(self.save)
        self.match: Optional[Match] = None
        self.busy = False
        self.flash: set[Pos] = set()
        self.board_width = 0
        self.cells: list[list[ft.Container]] = []
        self.labels: list[list[ft.Text]] = []

    # ------------------------------------------------------------------ menu

    def _choice_row(self, title: str, options: list[tuple[str, Any]], current: Any,
                    on_pick: Callable[[Any], None]) -> ft.Control:
        """Uma pergunta com botões de escolha; o escolhido aparece preenchido."""
        buttons = []
        for label, value in options:
            kind = ft.Button if value == current else ft.OutlinedButton
            buttons.append(kind(label, on_click=lambda _e, v=value: on_pick(v)))
        return ft.Column(controls=[
            ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=theme.MUTED),
            ft.Row(controls=buttons, spacing=8, wrap=True, alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _pick(self, field: str) -> Callable[[Any], None]:
        """Cria o tratador que grava a escolha em `setup` e redesenha o menu."""
        def handler(value: Any) -> None:
            setattr(self.setup, field, value)
            store_setup(self.save, self.setup)
            save_save(self.save)
            self.show_menu()
        return handler

    def show_menu(self) -> None:
        setup = self.setup
        rows: list[ft.Control] = [
            ft.Text("Guerra dos Blocos", size=30, weight=ft.FontWeight.BOLD),
            ft.Text("Espreme os blocos do adversário e vire todos para o seu lado.",
                    size=14, color=theme.MUTED),
            self._choice_row("Modo", [("Contra o celular", Mode.BOT), ("Pai e filho", Mode.TWO)],
                             setup.mode, self._pick("mode")),
            self._choice_row("Tamanho", [(f"{n}×{n}", n) for n in VALID_SIZES],
                             setup.size, self._pick("size")),
        ]
        if setup.mode is Mode.BOT:
            rows.append(self._choice_row("Nível do celular", [(lv.label, lv) for lv in Level],
                                         setup.bot_level, self._pick("bot_level")))
        rows.append(self._choice_row("Contas para jogar", [(n, k) for k, n in LEVEL_NAMES.items()],
                                     setup.math_level, self._pick("math_level")))
        rows.append(ft.Button("Jogar", on_click=self.on_play))
        summary = record_summary(self.save, setup)
        if summary:
            rows.append(ft.Text(summary, size=13, color=theme.MUTED))
        rows.append(ft.Text(
            "Como jogar: toque numa casa vazia para ver o que vira e toque de novo para "
            "confirmar. Se os blocos do adversário ficarem espremidos em linha reta entre o "
            "seu novo bloco e outro seu, eles viram seus. Ganha quem tiver mais blocos quando "
            "o tabuleiro encher. Cantos não podem ser espremidos!", size=12, color=theme.MUTED))
        self.page.clean()
        self.page.add(ft.Column(controls=rows, spacing=14, scroll=ft.ScrollMode.AUTO,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    def on_play(self, _event: Any) -> None:
        self.show_game()

    # ------------------------------------------------------------------ partida

    def _build_board(self, size: int) -> ft.Control:
        side = theme.cell_side(size)
        self.cells, self.labels = [], []
        for r in range(size):
            cell_row, label_row = [], []
            for c in range(size):
                label = ft.Text("", size=int(side * 0.45), weight=ft.FontWeight.BOLD,
                                color=theme.MUTED)
                cell = ft.Container(
                    width=side, height=side, border_radius=6, bgcolor=theme.EMPTY,
                    content=ft.Column(controls=[label], alignment=ft.MainAxisAlignment.CENTER,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    on_click=self._cell_handler((r, c)))
                cell_row.append(cell)
                label_row.append(label)
            self.cells.append(cell_row)
            self.labels.append(label_row)
        grid = ft.Column(controls=[ft.Row(controls=list(row), spacing=GAP) for row in self.cells],
                         spacing=GAP)
        return ft.Container(content=grid, padding=8, bgcolor=theme.BOARD_BG, border_radius=10)

    def show_game(self) -> None:
        self.match = Match(self.setup)
        self.busy = False
        self.flash = set()
        size = self.setup.size
        self.board_width = size * theme.cell_side(size) + (size - 1) * GAP + 16
        self.turn_text = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        self.blue_text = ft.Text(size=16, weight=ft.FontWeight.BOLD, color=theme.BLUE)
        self.orange_text = ft.Text(size=16, weight=ft.FontWeight.BOLD, color=theme.ORANGE)
        self.bar_blue = ft.Container(height=14, width=0, bgcolor=theme.BLUE)
        self.bar_orange = ft.Container(height=14, width=0, bgcolor=theme.ORANGE)
        self.message = ft.Text(size=15, weight=ft.FontWeight.W_500)
        self.undo_info = ft.Text(size=12, color=theme.MUTED)
        self.question_box = ft.Column(controls=[], visible=False, spacing=8,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.end_title = ft.Text(size=24, weight=ft.FontWeight.BOLD)
        self.end_record = ft.Text(size=13, color=theme.MUTED)
        self.end_box = ft.Column(controls=[
            self.end_title, self.end_record,
            ft.Row(controls=[ft.Button("Jogar de novo", on_click=self.on_new),
                             ft.OutlinedButton("Menu", on_click=self.on_menu)],
                   alignment=ft.MainAxisAlignment.CENTER),
        ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.btn_hint = ft.OutlinedButton("Dica", on_click=self.on_hint)
        self.btn_undo = ft.OutlinedButton("Desfazer", on_click=self.on_undo)
        scores = ft.Row(controls=[self.blue_text, self.orange_text], width=self.board_width,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        bar = ft.Container(content=ft.Row(controls=[self.bar_blue, self.bar_orange], spacing=0),
                           bgcolor=theme.BAR_EMPTY, border_radius=7)
        self.page.clean()
        self.page.add(ft.Column(controls=[
            ft.Text("Guerra dos Blocos", size=22, weight=ft.FontWeight.BOLD),
            self.turn_text, scores, bar, self._build_board(size), self.message,
            self.question_box, self.end_box,
            ft.Row(controls=[self.btn_hint, self.btn_undo,
                             ft.OutlinedButton("Menu", on_click=self.on_menu)],
                   alignment=ft.MainAxisAlignment.CENTER),
            self.undo_info,
        ], spacing=10, scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        self._render()

    # ------------------------------------------------------------------ desenho

    def _render(self) -> None:
        match = self.match
        assert match is not None
        game = match.game
        preview = set(match.preview_cells())
        for r in range(game.size):
            for c in range(game.size):
                pos = (r, c)
                look = theme.cell_look(
                    game.board.get(pos), game.current, is_last=pos == game.last_move,
                    is_pending=pos == match.pending, is_flip=pos in preview,
                    is_hint=pos == match.hint_pos, is_flash=pos in self.flash)
                self.cells[r][c].bgcolor = look.bg
                self.labels[r][c].value = look.symbol
                self.labels[r][c].color = look.fg
        counts = game.counts()
        blue, orange = counts[Player.BLUE], counts[Player.ORANGE]
        self.blue_text.value = f"{Player.BLUE.symbol} {match.name(Player.BLUE)}: {blue}"
        self.orange_text.value = (f"{Player.ORANGE.symbol} "
                                  f"{match.name(Player.ORANGE)}: {orange}")
        self.bar_blue.width, self.bar_orange.width = theme.bar_widths(blue, orange,
                                                                       self.board_width)
        self.turn_text.value = match.turn_label()
        self.message.value = match.message
        self.undo_info.value = f"Desfazer restantes: {match.undos_left}"
        can_act = match.phase is Phase.CHOOSING and not self.busy
        self.btn_hint.disabled = not can_act
        self.btn_undo.disabled = not can_act or not game.can_undo or match.undos_left <= 0
        self._render_question()
        self._render_end()
        self.page.update()

    def _render_question(self) -> None:
        match = self.match
        assert match is not None
        question = match.question
        self.question_box.visible = match.phase is Phase.QUESTION and question is not None
        if not self.question_box.visible or question is None:
            self.question_box.controls = []
            return
        self.question_box.controls = [
            ft.Text(question.text, size=28, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[ft.Button(str(value), on_click=self._answer_handler(value))
                             for value in question.choices],
                   alignment=ft.MainAxisAlignment.CENTER, wrap=True),
        ]

    def _render_end(self) -> None:
        match = self.match
        assert match is not None
        self.end_box.visible = match.is_over
        if match.is_over:
            self.end_title.value = f"{match.result_text()} {match.score_line()}"
            self.end_record.value = match.record_text(self.save)

    # ------------------------------------------------------------------ fluxo

    def _cell_handler(self, pos: Pos) -> Callable[[Any], Any]:
        async def handler(_event: Any) -> None:
            await self.on_cell(pos)
        return handler

    def _answer_handler(self, value: int) -> Callable[[Any], Any]:
        async def handler(_event: Any) -> None:
            await self.on_answer(value)
        return handler

    async def on_cell(self, pos: Pos) -> None:
        if self.busy or self.match is None:
            return
        if self.match.tap(pos) == "played":
            await self._continue()
        else:
            self._render()

    async def on_answer(self, value: int) -> None:
        if self.busy or self.match is None:
            return
        if self.match.answer(value) in ("played", "skipped"):
            await self._continue()
        else:
            self._render()

    async def _flash_flipped(self) -> None:
        """Faz os blocos recém-virados piscarem antes de assentar na cor nova."""
        assert self.match is not None
        self.flash = set(self.match.last_flipped)
        self._render()
        if self.flash:
            await asyncio.sleep(FLIP_DELAY)
            self.flash = set()
            self._render()

    async def _continue(self) -> None:
        """Depois de uma vez: anima, deixa o celular jogar se for a vez dele e fecha a partida."""
        match = self.match
        assert match is not None
        self.busy = True
        try:
            await self._flash_flipped()
            if match.phase is Phase.BOT_TURN:
                match.message = "O celular está pensando..."
                self._render()
                await asyncio.sleep(BOT_DELAY)
                match.bot_move()
                await self._flash_flipped()
        finally:
            self.busy = False
        if match.is_over and match.record(self.save) is not None:
            save_save(self.save)
        self._render()

    # ------------------------------------------------------------------ botões

    def on_hint(self, _event: Any) -> None:
        if self.match is not None and not self.busy:
            self.match.hint()
            self._render()

    def on_undo(self, _event: Any) -> None:
        if self.match is not None and not self.busy and not self.match.undo():
            self.match.message = "Não dá para desfazer agora."
        self._render()

    def on_new(self, _event: Any) -> None:
        self.show_game()

    def on_menu(self, _event: Any) -> None:
        self.show_menu()


async def main(page: ft.Page) -> None:
    """Ponto de entrada passado para `ft.run`."""
    page.title = "Guerra dos Blocos"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 12
    try:
        page.window.width = 430
        page.window.height = 900
    except Exception:  # janela não configurável (web/celular): sem problema
        logger.debug("window não configurável", exc_info=True)
    BlocksApp(page).show_menu()
