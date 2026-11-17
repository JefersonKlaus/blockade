"""How the game screen is built: the board, its size on each screen, and the rows
lined up with it."""
from __future__ import annotations


from blockwar import layout, theme
from blockwar.texts import PORTUGUESE

from fake_page import FakePage
from ui_actions import run, start, tap_twice
from ui_queries import label, painted, root, view


def test_starting_a_game_builds_the_board_and_paints_the_four_blocks(app):
    start(app)
    assert (len(view(app).cells), len(view(app).cells[0])) == (5, 5)
    assert all(len(row) == 5 for row in view(app).labels)
    assert painted(app) == 4
    assert view(app).turn_text.value == "Vez do Azul ●"
    screen_view = view(app)
    assert screen_view.blue_text.value == "● Azul: 2"
    assert screen_view.orange_text.value == "▲ Laranja: 2"
    # 2 x 2: the score bar is split evenly
    assert screen_view.bar_blue.width + screen_view.bar_orange.width == screen_view.board_width
    assert abs(view(app).bar_blue.width - view(app).bar_orange.width) <= 1
    assert view(app).btn_undo.disabled is True and view(app).btn_hint.disabled is False
    assert label(view(app).btn_undo) == "Desfazer (3)"   # undos left live on the button


def game_rows(app) -> list:
    """Top row, scores, score bar and board: stacked, all as wide as the board (otherwise
    the board frame and the score bar stretch across a wide window while the squares stay
    on the left)."""
    screen_view = view(app)
    return [screen_view.top_bar, screen_view.scores, screen_view.bar, screen_view.board]


def test_the_board_is_the_biggest_that_fits_the_screen(ui):
    for width, height, grid in [(390, 844, 7), (768, 1024, 14),   # phone, tablet
                                (1000, 600, 6)]:                   # wide, short window
        app = ui.BlocksApp(FakePage(width, height), PORTUGUESE)
        start(app)
        assert app.game.match.game.size == grid and len(view(app).cells) == grid
        assert view(app).side >= layout.TOUCH_CELL
        space = layout.board_space(width, height, 12)
        assert space - grid < view(app).board_width <= space      # fills the space
        side = view(app).side
        assert all(cell.width == cell.height == side for row in view(app).cells for cell in row)
        assert {row.width for row in game_rows(app)} == {view(app).board_width}


def test_the_board_follows_the_screen_when_it_is_resized(app):
    start(app)
    tap_twice(app, (1, 3))
    small = view(app).board_width
    app.page.width = 400                            # e.g. a desktop window made wider
    app.on_resize(None)
    assert app.game.match.game.size == 5                 # the game in progress keeps its board
    assert view(app).board_width > small and 400 - 24 - 5 < view(app).board_width <= 400 - 24
    assert all(cell.width == view(app).side for row in view(app).cells for cell in row)
    assert view(app).labels[0][0].size == layout.symbol_size(view(app).side)
    assert {row.width for row in game_rows(app)} == {view(app).board_width}
    assert view(app).bar_blue.width + view(app).bar_orange.width == view(app).board_width
    assert view(app).cells[1][3].bgcolor == theme.BLUE_LAST  # the game itself is unchanged


def test_every_cell_is_tappable_and_plays_its_own_position(app):
    start(app)
    handlers = {view(app).cells[r][c].on_click for r in range(5) for c in range(5)}
    assert len(handlers) == 25
    run(view(app).cells[0][4].on_click(None))
    assert app.game.match.pending == (0, 4)


def test_first_tap_previews_second_tap_plays(app):
    start(app)
    run(app.game.on_cell((1, 3)))
    assert view(app).cells[1][3].bgcolor == theme.BLUE_TINT       # chosen cell
    assert view(app).cells[1][2].bgcolor == theme.FLIP_PREVIEW    # what will flip
    assert view(app).message.value == "Vira 1 bloco. Toque de novo para jogar."
    run(app.game.on_cell((1, 3)))
    assert app.game.match.game.turn == 1 and app.game.busy is False
    assert view(app).cells[1][2].bgcolor == theme.BLUE            # turned blue
    assert view(app).cells[1][3].bgcolor == theme.BLUE_LAST       # last move, darker
    assert view(app).labels[1][3].value == "●"
    assert view(app).turn_text.value == "Vez do Laranja ▲" and view(app).btn_undo.disabled is False
    assert view(app).blue_text.value == "● Azul: 4"
    assert view(app).orange_text.value == "▲ Laranja: 1"
    assert view(app).bar_blue.width > view(app).bar_orange.width


def test_the_game_has_a_help_button_at_the_top_right(app):
    start(app)
    top = root(app).controls[0]
    assert top is view(app).top_bar
    assert top.controls[-1] is view(app).btn_help                # right end of the top row
    assert label(view(app).btn_help.content) == "?" and view(app).btn_help.tooltip == "Como jogar"
    assert view(app).turn_text in top.controls                    # whose turn, in the same row
    assert top.width == view(app).board_width                     # lines up with the board edge
