"""Interface Flet. Toda a regra do jogo vive em controller.py.

Telas (uma de cada vez, para ficarem limpas; botões no meio da tela, Jogar! por último):
  menu      -> ícone + "Blockade", quem joga, nível (verde/amarelo/vermelho),
               Praticar matemática, Jogar!
  contas    -> "Praticar matemática": + − × ÷ (só os símbolos), tabuadas, Jogar!
  partida   -> o maior tabuleiro que cabe na tela (até 14×14), em pé (retrato);
               ao começar, o tutorial "Como jogar" abre numa janela por cima

Esta tela é por turnos (nada de laço de 60 quadros), o que combina bem com o Flet.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

import flet as ft

from . import APP_NAME, theme
from .bot import Level
from .controller import Match, Mode, Phase, Setup, record_summary, setup_from_save, store_setup
from .mathmode import OPERATIONS, SYMBOLS, TABLES, MathSettings
from .models import Player, Pos
from .storage import SaveData, load_save, save_save

logger = logging.getLogger(__name__)

FLIP_DELAY = 0.35   # quanto tempo os blocos virados piscam
BOT_DELAY = 0.6     # "pensando" do celular, para o jogador acompanhar
TUTORIAL_CELL = 36  # casas do desenho de exemplo no tutorial
TUTORIAL_WIDTH = 260  # a janela do tutorial só ocupa o necessário, não a tela toda
PLAY_GAP = 28       # espaço mínimo entre as escolhas e o botão Jogar!
PLAY_BOTTOM = 36    # distância do Jogar! até a borda de baixo (perto dos dedos)
HELP_SIZE = 40      # botão "?" (tutorial) no canto de cima, à direita, na partida
ICON = "icon.png"   # src/assets/icon.png (também o ícone do app no celular)
MATH_TITLE = "Praticar matemática"
PAGE_PADDING = 12

MENU, MATH, GAME = "menu", "contas", "partida"


class BlocksApp:
    """Liga as telas ao `Match` (a partida) e ao arquivo de recordes."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.save: SaveData = load_save()
        self.setup: Setup = setup_from_save(self.save)
        self.screen = MENU
        self.tutorial: Optional[ft.AlertDialog] = None
        self.tutorial_open = False
        self.match: Optional[Match] = None
        self.busy = False
        self.flash: set[Pos] = set()
        self.side = 0
        self.board_width = 0
        self.cells: list[list[ft.Container]] = []
        self.labels: list[list[ft.Text]] = []

    # ------------------------------------------------------------------ peças comuns

    def _show(self, screen: str, controls: list[ft.Control], play: ft.Control,
              spacing: int = 14, top: Optional[list[ft.Control]] = None) -> None:
        """Troca a tela inteira (uma tela de cada vez), sempre com o mesmo desenho:

            top      -> no alto (ícone + nome, ou "Voltar")
            controls -> as escolhas, centralizadas no espaço do meio
            play     -> o Jogar!, embaixo, perto dos dedos, com um espaço acima dele

        Menu e "Praticar matemática" usam o mesmo desenho, então o Jogar! fica
        exatamente no mesmo lugar nas duas telas."""
        self._close_tutorial()
        self.screen = screen
        self.page.clean()
        self.page.add(ft.Column(controls=[
            *(top or []),
            ft.Column(controls=controls, spacing=spacing, expand=True,
                      alignment=ft.MainAxisAlignment.CENTER,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(content=play, padding=ft.Padding(left=0, top=PLAY_GAP, right=0,
                                                          bottom=PLAY_BOTTOM)),
        ], spacing=0, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    @staticmethod
    def _title(text: str, size: int = 28) -> ft.Control:
        return ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=theme.DARK,
                       text_align=ft.TextAlign.CENTER)

    def _header(self) -> ft.Control:
        """Ícone do app + nome, no alto do menu."""
        return ft.Row(controls=[
            ft.Image(src=ICON, width=56, height=56),
            self._title(APP_NAME, size=32),
        ], spacing=12, alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER)

    @staticmethod
    def _button(text: str, on_click: Callable[[Any], Any], bg: str = theme.BUTTON_BG,
                fg: str = theme.DARK, **extra: Any) -> ft.Button:
        """Botão pastel comum (fundo claro, texto escuro)."""
        return ft.Button(text, bgcolor=bg, color=fg, on_click=on_click, **extra)

    @classmethod
    def _play_button(cls, text: str, on_click: Callable[[Any], Any],
                     width: int = 240) -> ft.Control:
        """O botão Jogar!: o maior e mais chamativo, sempre o último."""
        return cls._button(
            text, on_click, bg=theme.PLAY_BG, width=width, height=58,
            style=ft.ButtonStyle(text_style=ft.TextStyle(size=22, weight=ft.FontWeight.BOLD)))

    @staticmethod
    def _border(color: Optional[str]) -> Optional[ft.Border]:
        if color is None:
            return None
        side = ft.BorderSide(3, color)
        return ft.Border(left=side, top=side, right=side, bottom=side)

    def _card(self, text: str, look: theme.CardLook, on_click: Callable[[Any], Any],
              width: int = 130, height: int = 64, size: int = 18) -> ft.Control:
        """Um cartão grande só com texto (sem figuras). O escolhido tem cor mais forte e
        borda."""
        return ft.Container(
            content=ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=look.fg,
                            text_align=ft.TextAlign.CENTER),
            width=width, height=height, bgcolor=look.bg, border=self._border(look.border),
            border_radius=16, ink=True, alignment=ft.Alignment(0, 0), on_click=on_click)

    def _card_section(self, title: str, cards: list[ft.Control]) -> ft.Control:
        """Uma pergunta com seus cartões."""
        return ft.Column(controls=[
            ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=theme.DARK,
                    text_align=ft.TextAlign.CENTER),
            ft.Row(controls=cards, spacing=10, run_spacing=10, wrap=True,
                   alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _remember(self) -> None:
        store_setup(self.save, self.setup)
        save_save(self.save)

    # ------------------------------------------------------------------ menu

    def _pick(self, field: str) -> Callable[[Any], None]:
        """Cria o tratador que grava a escolha em `setup` e redesenha o menu."""
        def handler(value: Any) -> None:
            setattr(self.setup, field, value)
            self._remember()
            self.show_menu()
        return handler

    def _math_button(self) -> ft.Control:
        """Abre a página de matemática; quando há contas escolhidas, mostra quais."""
        math = self.setup.math
        if math.enabled:
            return self._button(f"{MATH_TITLE}: {math.symbols()}", self.on_open_math,
                                bg=theme.CARD_SELECTED, fg=theme.BLUE_INK, width=280, height=50)
        return self._button(MATH_TITLE, self.on_open_math, width=280, height=50)

    def show_menu(self) -> None:
        setup = self.setup
        pick_mode, pick_level = self._pick("mode"), self._pick("bot_level")
        rows: list[ft.Control] = [self._card_section("Quem vai jogar com você?", [
            self._card(text, theme.card_look(mode == setup.mode),
                       lambda _e, m=mode: pick_mode(m))
            for text, mode in (("Um amigo", Mode.TWO), ("O celular", Mode.BOT))])]
        if setup.mode is Mode.BOT:
            rows.append(self._card_section("Quão esperto é o celular?", [
                self._card(level.label, theme.level_look(level, level is setup.bot_level),
                           lambda _e, lv=level: pick_level(lv), width=100)
                for level in Level]))
        summary = record_summary(self.save, setup)
        if summary:
            rows.append(ft.Text(summary, size=13, color=theme.MUTED))
        rows.append(self._math_button())
        self._show(MENU, rows, self._play_button("Jogar!", self.on_play), spacing=20,
                   top=[self._header()])

    def on_play(self, _event: Any) -> None:
        """Jogar!: abre o tabuleiro e, por cima dele, o tutorial."""
        self.show_game()
        self.show_tutorial()

    # ------------------------------------------------------------------ praticar matemática

    def on_open_math(self, _event: Any) -> None:
        self.show_math()

    def on_math_back(self, _event: Any) -> None:
        self.show_menu()

    def _set_math(self, settings: MathSettings) -> None:
        self.setup.math = settings
        self._remember()
        self.show_math()

    def show_math(self) -> None:
        """Página "Praticar matemática": só os 4 símbolos; com × ou ÷ aparecem as tabuadas
        logo abaixo. Nenhum símbolo escolhido = jogo sem contas. O último botão já é o
        Jogar!, sem precisar voltar ao menu."""
        math = self.setup.math
        rows: list[ft.Control] = [
            self._title(MATH_TITLE),
            ft.Row(controls=[
                self._card(SYMBOLS[op], theme.card_look(op in math.operations),
                           lambda _e, o=op: self._set_math(self.setup.math.toggled_operation(o)),
                           width=72, height=72, size=36)
                for op in OPERATIONS], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
        ]
        if math.uses_tables:
            rows.append(self._card_section("Tabuada", [
                self._card(str(t), theme.card_look(t in math.tables),
                           lambda _e, t=t: self._set_math(self.setup.math.toggled_table(t)),
                           width=54, height=48, size=20)
                for t in TABLES]))
        back = ft.Row(controls=[ft.TextButton("◀ Voltar", on_click=self.on_math_back)],
                      alignment=ft.MainAxisAlignment.START)
        self._show(MATH, rows, self._play_button("Jogar!", self.on_play), spacing=20,
                   top=[back])

    # ------------------------------------------------------------------ tutorial (janela)

    @staticmethod
    def _step(text: str) -> ft.Control:
        return ft.Text(text, size=15, weight=ft.FontWeight.W_500, color=theme.DARK,
                       text_align=ft.TextAlign.CENTER)

    @staticmethod
    def _example_row(looks: list[theme.CellLook]) -> ft.Control:
        return ft.Row(controls=[
            ft.Container(
                width=TUTORIAL_CELL, height=TUTORIAL_CELL, bgcolor=look.bg, border_radius=6,
                content=ft.Column(controls=[ft.Text(look.symbol, size=18,
                                                    weight=ft.FontWeight.BOLD, color=look.fg)],
                                  alignment=ft.MainAxisAlignment.CENTER,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            for look in looks], spacing=theme.GAP, alignment=ft.MainAxisAlignment.CENTER)

    def _example(self) -> ft.Control:
        """Desenho da captura, com as mesmas cores do jogo: ● ▲ ▲ [toque] vira ● ● ● ●."""
        blue, orange = Player.BLUE, Player.ORANGE
        before = [theme.cell_look(blue, blue), theme.cell_look(orange, blue),
                  theme.cell_look(orange, blue), theme.cell_look(None, blue, is_pending=True)]
        after = [theme.cell_look(blue, orange)] * 3 + [theme.cell_look(blue, orange,
                                                                       is_last=True)]
        return ft.Container(
            content=ft.Column(controls=[
                self._example_row(before),
                ft.Text("⬇", size=18, color=theme.DARK),
                self._example_row(after),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=8, bgcolor=theme.BOARD_BG, border_radius=10)

    def show_tutorial(self) -> None:
        """"Como jogar": uma janela (modal) por cima do tabuleiro, quando a partida começa
        ou no botão "?" da partida. Só do tamanho necessário (largura fixa, altura do
        conteúdo). Só fecha no "Entendi!"; enquanto está aberta, o tabuleiro não recebe
        toques."""
        steps: list[ft.Control] = [
            self._step("1. Toque numa casa vazia."),
            self._step("2. Toque de novo para colocar o seu bloco."),
            self._example(),
            self._step("Os blocos do outro presos entre dois blocos seus viram seus!"),
            self._step("Quem tiver mais blocos no fim ganha!"),
        ]
        if self.setup.math.enabled:
            steps.append(self._step("Acerte a conta para colocar o bloco!"))
        self.tutorial = ft.AlertDialog(
            modal=True, bgcolor=theme.PAGE_BG,
            title=self._title("Como jogar", size=22),
            content=ft.Container(
                width=TUTORIAL_WIDTH,
                content=ft.Column(controls=steps, spacing=10, tight=True,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
            actions=[self._play_button("Entendi!", self.on_start_game, width=TUTORIAL_WIDTH)],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            on_dismiss=self.on_tutorial_dismissed)
        self.tutorial_open = True
        self.page.show_dialog(self.tutorial)

    def _close_tutorial(self) -> None:
        if self.tutorial_open:
            self.tutorial_open = False
            self.page.pop_dialog()

    def on_start_game(self, _event: Any) -> None:
        """ "Entendi!": fecha a janela do tutorial; o tabuleiro já está embaixo."""
        self._close_tutorial()

    def on_tutorial_dismissed(self, _event: Any) -> None:
        self.tutorial_open = False

    def on_help(self, _event: Any) -> None:
        """Botão "?" da partida: abre o tutorial de novo, por cima do jogo."""
        if not self.tutorial_open:
            self.show_tutorial()

    # ------------------------------------------------------------------ partida

    def _space(self) -> float:
        """Lado do maior quadrado que cabe para o tabuleiro nesta tela."""
        padding = getattr(self.page, "padding", 0)
        padding = padding if isinstance(padding, (int, float)) else 0
        width, height = getattr(self.page, "width", None), getattr(self.page, "height", None)
        return theme.board_space(width if isinstance(width, (int, float)) else None,
                                 height if isinstance(height, (int, float)) else None, padding)

    def _measure_board(self) -> None:
        assert self.match is not None
        size = self.match.game.size
        self.side = theme.cell_side(size, self._space())
        self.board_width = theme.board_width(size, self.side)

    def _build_board(self, size: int) -> ft.Control:
        self.cells, self.labels = [], []
        for r in range(size):
            cell_row, label_row = [], []
            for c in range(size):
                label = ft.Text("", size=theme.symbol_size(self.side),
                                weight=ft.FontWeight.BOLD, color=theme.MUTED)
                cell = ft.Container(
                    width=self.side, height=self.side, border_radius=6, bgcolor=theme.EMPTY,
                    content=ft.Column(controls=[label], alignment=ft.MainAxisAlignment.CENTER,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    on_click=self._cell_handler((r, c)))
                cell_row.append(cell)
                label_row.append(label)
            self.cells.append(cell_row)
            self.labels.append(label_row)
        grid = ft.Column(controls=[ft.Row(controls=list(row), spacing=theme.GAP)
                                   for row in self.cells], spacing=theme.GAP)
        return ft.Container(content=grid, padding=theme.BOARD_PADDING, bgcolor=theme.BOARD_BG,
                            border_radius=10)

    def on_resize(self, _event: Any) -> None:
        """A janela mudou de tamanho: as mesmas casas, redimensionadas para o novo espaço."""
        if self.screen != GAME or self.match is None:
            return
        self._measure_board()
        for row, label_row in zip(self.cells, self.labels, strict=True):
            for cell, label in zip(row, label_row, strict=True):
                cell.width = cell.height = self.side
                label.size = theme.symbol_size(self.side)
        self.scores.width = self.top_bar.width = self.board_width
        self._render()

    def show_game(self) -> None:
        # O maior tabuleiro que cabe: ~7×7 no celular, 10×10 ou mais no tablet, até 14×14.
        self.setup.size = theme.grid_size(self._space())
        self.match = Match(self.setup)
        self.busy = False
        self.flash = set()
        size = self.setup.size
        self._measure_board()
        self.turn_text = ft.Text(size=22, weight=ft.FontWeight.BOLD, color=theme.DARK,
                                 text_align=ft.TextAlign.CENTER, expand=True)
        self.btn_help = ft.Container(
            content=ft.Text("?", size=22, weight=ft.FontWeight.BOLD, color=theme.BLUE_INK),
            width=HELP_SIZE, height=HELP_SIZE, border_radius=HELP_SIZE // 2,
            bgcolor=theme.BUTTON_BG, alignment=ft.Alignment(0, 0), ink=True,
            tooltip="Como jogar", on_click=self.on_help)
        # Vez de quem joga no meio, "?" no canto direito; o espaço vazio à esquerda tem a
        # largura do "?" para o texto ficar centralizado de verdade.
        self.top_bar = ft.Row(controls=[ft.Container(width=HELP_SIZE), self.turn_text,
                                        self.btn_help], width=self.board_width,
                              vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.blue_text = ft.Text(size=16, weight=ft.FontWeight.BOLD, color=theme.BLUE_INK)
        self.orange_text = ft.Text(size=16, weight=ft.FontWeight.BOLD, color=theme.ORANGE_INK)
        self.bar_blue = ft.Container(height=14, width=0, bgcolor=theme.BLUE)
        self.bar_orange = ft.Container(height=14, width=0, bgcolor=theme.ORANGE)
        self.message = ft.Text(size=15, weight=ft.FontWeight.W_500, color=theme.DARK,
                               text_align=ft.TextAlign.CENTER)
        self.question_box = ft.Column(controls=[], visible=False, spacing=8,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.end_title = ft.Text(size=24, weight=ft.FontWeight.BOLD, color=theme.DARK)
        self.end_record = ft.Text(size=13, color=theme.MUTED)
        self.end_box = ft.Column(controls=[
            self.end_title, self.end_record,
            ft.Row(controls=[self._button("Jogar de novo", self.on_new, bg=theme.PLAY_BG),
                             self._button("Menu", self.on_menu)],
                   alignment=ft.MainAxisAlignment.CENTER),
        ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.btn_hint = self._button("Dica", self.on_hint)
        self.btn_undo = self._button("Desfazer", self.on_undo)
        self.scores = ft.Row(controls=[self.blue_text, self.orange_text], width=self.board_width,
                             alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        bar = ft.Container(content=ft.Row(controls=[self.bar_blue, self.bar_orange], spacing=0),
                           bgcolor=theme.BAR_EMPTY, border_radius=7)
        # Dica e Desfazer só existem no nível Fácil contra o celular (ajudas de iniciante).
        self.btn_hint.visible = self.btn_undo.visible = self.match.helpers_allowed
        self._close_tutorial()
        self.screen = GAME
        self.page.clean()
        self.page.add(ft.Column(controls=[
            self.top_bar, self.scores, bar, self._build_board(size), self.message,
            self.question_box, self.end_box,
            ft.Row(controls=[self.btn_hint, self.btn_undo, self._button("Menu", self.on_menu)],
                   alignment=ft.MainAxisAlignment.CENTER),
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
        self.btn_undo.content = f"Desfazer ({match.undos_left})"
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
            ft.Text(question.text, size=28, weight=ft.FontWeight.BOLD, color=theme.DARK),
            ft.Row(controls=[self._button(
                str(value), self._answer_handler(value), height=52,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD)))
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

    def _blocked(self) -> bool:
        """Sem partida, celular pensando ou tutorial aberto: toques não valem."""
        return self.busy or self.match is None or self.tutorial_open

    async def on_cell(self, pos: Pos) -> None:
        if self._blocked():
            return
        if self.match.tap(pos) == "played":
            await self._continue()
        else:
            self._render()

    async def on_answer(self, value: int) -> None:
        if self._blocked():
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
                # No tablet (até 14×14) o nível difícil pode levar um tempinho para pensar:
                # pensa numa thread, junto com a pausa, para a tela nunca travar.
                await asyncio.gather(asyncio.sleep(BOT_DELAY), asyncio.to_thread(match.bot_move))
                await self._flash_flipped()
        finally:
            self.busy = False
        if match.is_over and match.record(self.save) is not None:
            save_save(self.save)
        self._render()

    # ------------------------------------------------------------------ botões

    def on_hint(self, _event: Any) -> None:
        if not self._blocked():
            self.match.hint()
            self._render()

    def on_undo(self, _event: Any) -> None:
        if self._blocked():
            return
        if not self.match.undo():
            self.match.message = "Não dá para desfazer agora."
        self._render()

    def on_new(self, _event: Any) -> None:
        """ "Jogar de novo": quem acabou de jogar já viu o tutorial, vai direto à partida."""
        self.show_game()

    def on_menu(self, _event: Any) -> None:
        self.show_menu()


async def lock_portrait(page: ft.Page) -> None:
    """Jogo sempre em pé (retrato) no celular/tablet. No computador não há o que travar."""
    platform = getattr(page, "platform", None)
    try:
        if platform is not None and platform.is_mobile():
            await page.set_allowed_device_orientations([ft.DeviceOrientation.PORTRAIT_UP])
    except Exception:  # ex.: aberto no navegador do celular via `flet run --android`
        logger.debug("não consegui travar a orientação", exc_info=True)


async def main(page: ft.Page) -> None:
    """Ponto de entrada passado para `ft.run`."""
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=theme.SEED)
    page.bgcolor = theme.PAGE_BG
    page.padding = PAGE_PADDING
    try:
        page.window.width = 430   # no computador, uma janela em pé como um celular
        page.window.height = 900
    except Exception:  # janela não configurável (web/celular): sem problema
        logger.debug("window não configurável", exc_info=True)
    await lock_portrait(page)
    app = BlocksApp(page)
    page.on_resize = app.on_resize
    app.show_menu()
