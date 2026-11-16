from blockwar import theme
from blockwar.models import Player

B, O = Player.BLUE, Player.ORANGE


def test_empty_and_owned_cells():
    assert theme.cell_look(None, B) == theme.CellLook(theme.EMPTY, "", theme.MUTED)
    blue = theme.cell_look(B, O)
    assert blue.bg == theme.BLUE and blue.symbol == "●" and blue.fg == theme.WHITE
    assert theme.cell_look(O, B).symbol == "▲"


def test_last_move_is_darker():
    assert theme.cell_look(B, O, is_last=True).bg == theme.BLUE_LAST
    assert theme.cell_look(O, B, is_last=True).bg == theme.ORANGE_LAST


def test_pending_cell_shows_the_current_players_tint():
    look = theme.cell_look(None, O, is_pending=True)
    assert look.bg == theme.ORANGE_TINT and look.symbol == "▲"


def test_flip_preview_beats_owner_color_and_shows_the_new_owner():
    look = theme.cell_look(O, B, is_flip=True)
    assert look.bg == theme.FLIP_PREVIEW and look.symbol == "●"


def test_flash_hint_and_priorities():
    assert theme.cell_look(B, O, is_flash=True).bg == theme.FLASH
    assert theme.cell_look(None, B, is_hint=True) == theme.CellLook(theme.HINT, "?", theme.DARK)
    assert theme.cell_look(B, O, is_hint=True).bg == theme.BLUE  # dica só vale em casa vazia
    assert theme.cell_look(None, B, is_pending=True, is_hint=True).bg == theme.BLUE_TINT


def test_bar_widths_always_fill_the_bar():
    assert theme.bar_widths(0, 0, 300) == (0, 0)
    assert theme.bar_widths(2, 2, 300) == (150, 150)
    left, right = theme.bar_widths(7, 3, 301)
    assert left + right == 301 and left > right
    assert theme.bar_widths(5, 0, 200) == (200, 0)


def test_cell_side_is_bigger_on_small_boards():
    assert theme.cell_side(5) > theme.cell_side(7)
