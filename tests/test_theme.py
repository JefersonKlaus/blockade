import colorsys
import re

import pytest

from blockwar import theme
from blockwar.models import Player

B, O = Player.BLUE, Player.ORANGE

COLOR_NAMES = [n for n in dir(theme) if n.isupper() and isinstance(getattr(theme, n), str)]
# Colours used as backgrounds (everything except the dark "ink" colours used for text).
BACKGROUNDS = [n for n in COLOR_NAMES if not n.endswith("_INK") and n not in ("DARK", "MUTED")]


def rgb(color: str) -> tuple[float, float, float]:
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def luminance(color: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    """WCAG contrast ratio (1 = invisible, 21 = black on white)."""
    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def all_cell_looks():
    flags = ("is_last", "is_pending", "is_flip", "is_hint", "is_flash")
    for owner in (None, B, O):
        for current in (B, O):
            for flag in (None, *flags):
                kwargs = {flag: True} if flag else {}
                yield theme.cell_look(owner, current, **kwargs)


# ---------------------------------------------------------------- pastel palette

def test_all_colors_are_valid_hex_codes():
    assert len(COLOR_NAMES) >= 20
    for name in COLOR_NAMES:
        assert re.fullmatch(r"#[0-9A-F]{6}", getattr(theme, name)), name


@pytest.mark.parametrize("name", BACKGROUNDS)
def test_backgrounds_are_pastel(name):
    """Pastel = bright and soft: high brightness, only moderate saturation (HSV)."""
    _, saturation, value = colorsys.rgb_to_hsv(*rgb(getattr(theme, name)))
    assert value >= 0.75, f"{name} is too dark for a pastel palette"
    assert saturation <= 0.55, f"{name} is too vivid for a pastel palette"


def test_every_square_is_readable():
    """Pastel backgrounds need dark symbols: every symbol must stand out (WCAG >= 3 for
    large text, and the ● / ▲ are large)."""
    for look in all_cell_looks():
        if look.symbol:
            assert contrast(look.fg, look.bg) >= 3, look


@pytest.mark.parametrize("fg, bg", [
    (theme.DARK, theme.PAGE_BG), (theme.DARK, theme.BUTTON_BG), (theme.DARK, theme.PLAY_BG),
    (theme.BLUE_INK, theme.CARD_SELECTED), (theme.MUTED, theme.CARD_BG),
    (theme.BLUE_INK, theme.PAGE_BG), (theme.ORANGE_INK, theme.PAGE_BG),
])
def test_text_on_screens_and_buttons_is_readable(fg, bg):
    assert contrast(fg, bg) >= 3


def test_players_have_distinct_colors_and_symbols():
    """Colour-blind players rely on the symbol, everyone else on the colour."""
    assert theme.player_color(B) != theme.player_color(O)
    assert theme.player_tint(B) != theme.player_tint(O)
    assert theme.player_ink(B) != theme.player_ink(O)
    assert theme.cell_look(B, B).symbol != theme.cell_look(O, O).symbol
    assert theme.player_color(B, last=True) != theme.player_color(B)


def test_the_board_stands_out_from_the_page_and_empty_squares_from_the_board():
    assert contrast(theme.BOARD_BG, theme.PAGE_BG) > 1.15
    assert contrast(theme.EMPTY, theme.BOARD_BG) > 1.15


# ---------------------------------------------------------------- squares

def test_empty_and_owned_cells():
    assert theme.cell_look(None, B) == theme.CellLook(theme.EMPTY, "", theme.MUTED)
    blue = theme.cell_look(B, O)
    assert blue.bg == theme.BLUE and blue.symbol == "●" and blue.fg == theme.BLUE_INK
    orange = theme.cell_look(O, B)
    assert orange.bg == theme.ORANGE and orange.symbol == "▲" and orange.fg == theme.ORANGE_INK


def test_last_move_is_darker():
    assert theme.cell_look(B, O, is_last=True).bg == theme.BLUE_LAST
    assert theme.cell_look(O, B, is_last=True).bg == theme.ORANGE_LAST
    assert luminance(theme.BLUE_LAST) < luminance(theme.BLUE)
    assert luminance(theme.ORANGE_LAST) < luminance(theme.ORANGE)


def test_pending_cell_shows_the_current_players_tint():
    look = theme.cell_look(None, O, is_pending=True)
    assert look.bg == theme.ORANGE_TINT and look.symbol == "▲" and look.fg == theme.ORANGE_INK


def test_flip_preview_beats_owner_color_and_shows_the_new_owner():
    look = theme.cell_look(O, B, is_flip=True)
    assert look.bg == theme.FLIP_PREVIEW and look.symbol == "●"


def test_flash_hint_and_priorities():
    assert theme.cell_look(B, O, is_flash=True).bg == theme.FLASH
    assert theme.cell_look(None, B, is_hint=True) == theme.CellLook(theme.HINT, "?", theme.DARK)
    assert theme.cell_look(B, O, is_hint=True).bg == theme.BLUE  # hints only on empty cells
    assert theme.cell_look(None, B, is_pending=True, is_hint=True).bg == theme.BLUE_TINT


def test_flash_only_applies_to_owned_cells():
    assert theme.cell_look(None, B, is_flash=True) == theme.cell_look(None, B)


def test_priority_order_pending_then_flip_then_flash():
    assert theme.cell_look(None, B, is_pending=True, is_flip=True).bg == theme.BLUE_TINT
    assert theme.cell_look(O, B, is_flip=True, is_flash=True).bg == theme.FLIP_PREVIEW
    assert theme.cell_look(B, O, is_flash=True, is_last=True).bg == theme.FLASH


def test_owned_cells_always_show_their_symbol_in_their_ink():
    for owner in (B, O):
        for current in (B, O):
            for is_last in (False, True):
                look = theme.cell_look(owner, current, is_last=is_last)
                assert look.symbol == owner.symbol and look.fg == theme.player_ink(owner)


def test_card_colors_distinguish_the_chosen_option():
    selected_bg, selected_fg = theme.card_colors(True)
    plain_bg, plain_fg = theme.card_colors(False)
    assert selected_bg == theme.CARD_SELECTED and plain_bg == theme.CARD_BG
    assert selected_bg != plain_bg and selected_fg != plain_fg


# ---------------------------------------------------------------- score bar

def test_bar_widths_always_fill_the_bar():
    assert theme.bar_widths(0, 0, 300) == (0, 0)
    assert theme.bar_widths(2, 2, 300) == (150, 150)
    left, right = theme.bar_widths(7, 3, 301)
    assert left + right == 301 and left > right
    assert theme.bar_widths(5, 0, 200) == (200, 0)


def test_bar_widths_never_exceed_the_total():
    for blue in range(0, 50, 7):
        for orange in range(0, 50, 5):
            left, right = theme.bar_widths(blue, orange, 337)
            assert left >= 0 and right >= 0
            assert left + right in (0, 337)


# ---------------------------------------------------------------- board size

@pytest.mark.parametrize("width, height, grid", [
    (360, 640, 6),      # small Android phone
    (375, 667, 7),      # iPhone SE
    (390, 844, 7),      # iPhone 14
    (430, 900, 8),      # the desktop window opened by main()
    (600, 960, 11),     # 7" tablet
    (768, 1024, 14),    # iPad: 10x10 or bigger...
    (1024, 1366, 14),   # ...but never more than 14x14
])
def test_the_grid_is_the_biggest_that_fits_the_screen(width, height, grid):
    space = theme.board_space(width, height, 12)
    assert theme.grid_size(space) == grid


def test_tablets_get_at_least_10x10():
    for width in (600, 700, 744, 768, 800, 834, 1024):
        assert theme.grid_size(theme.board_space(width, 1200, 12)) >= 10


@pytest.mark.parametrize("space", range(100, 1400, 37))
def test_squares_stay_big_enough_for_a_finger(space):
    size = theme.grid_size(space)
    assert theme.MIN_GRID <= size <= theme.MAX_GRID == 14
    side = theme.cell_side(size, space)
    if size > theme.MIN_GRID:
        assert side >= theme.TOUCH_CELL           # never smaller than a finger
        assert theme.cell_side(size + 1, space) < theme.TOUCH_CELL or size == theme.MAX_GRID


def test_the_board_fits_the_height_on_short_screens():
    """Landscape-shaped windows: the board must leave room for the rest of the game."""
    space = theme.board_space(1000, 600, 12)
    assert space == 600 - 24 - theme.RESERVED_HEIGHT


def test_unknown_screen_size_uses_a_phone_default():
    assert theme.board_space(None, None, 12) == theme.DEFAULT_SPACE
    assert theme.grid_size(theme.DEFAULT_SPACE) == 8


@pytest.mark.parametrize("size", [5, 7, 10, 14])
@pytest.mark.parametrize("space", [336, 366, 576, 744])
def test_the_board_fills_the_available_space(size, space):
    side = theme.cell_side(size, space)
    total = theme.board_width(size, side)
    assert total <= space and space - total < size


def test_symbols_grow_with_the_cell():
    assert theme.symbol_size(60) > theme.symbol_size(40) > 0
