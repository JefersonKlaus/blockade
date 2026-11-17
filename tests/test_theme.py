import colorsys
import re


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


def test_backgrounds_are_pastel():
    """Pastel = bright and soft: high brightness, only moderate saturation (HSV)."""
    for name in BACKGROUNDS:
        _, saturation, value = colorsys.rgb_to_hsv(*rgb(getattr(theme, name)))
        assert value >= 0.75, f"{name} is too dark for a pastel palette"
        assert saturation <= 0.55, f"{name} is too vivid for a pastel palette"


def test_every_square_is_readable():
    """Pastel backgrounds need dark symbols: every symbol must stand out (WCAG >= 3 for
    large text, and the ● / ▲ are large)."""
    for look in all_cell_looks():
        if look.symbol:
            assert contrast(look.fg, look.bg) >= 3, look


def test_text_on_screens_and_buttons_is_readable():
    for fg, bg in [
        (theme.DARK, theme.PAGE_BG), (theme.DARK, theme.BUTTON_BG), (theme.DARK, theme.PLAY_BG),
        (theme.BLUE_INK, theme.CARD_SELECTED), (theme.MUTED, theme.CARD_BG),
        (theme.BLUE_INK, theme.PAGE_BG), (theme.ORANGE_INK, theme.PAGE_BG),
    ]:
        assert contrast(fg, bg) >= 3, (fg, bg)


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


# ---------------------------------------------------------------- whose turn: the background

def test_the_background_is_the_color_of_whose_turn_it_is():
    assert theme.page_color(B) == theme.player_tint(B) == theme.BLUE_TINT
    assert theme.page_color(O) == theme.player_tint(O) == theme.ORANGE_TINT
    assert theme.page_color(None) == theme.PAGE_BG        # menu and game over


def test_the_game_stays_readable_on_both_turn_backgrounds():
    for player in (B, O):
        background = theme.page_color(player)
        assert contrast(theme.BOARD_BG, background) > 1.15   # the board still stands out
        for text in (theme.DARK, theme.MUTED, theme.BLUE_INK, theme.ORANGE_INK):
            assert contrast(text, background) >= 3            # turn, scores, messages


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


def test_square_states_and_which_one_wins():
    """Chosen square > blocks that will turn > flash > hint > owner's colour."""
    pending = theme.cell_look(None, O, is_pending=True)            # the current player's tint
    assert (pending.bg, pending.symbol, pending.fg) == (theme.ORANGE_TINT, "▲", theme.ORANGE_INK)
    flip = theme.cell_look(O, B, is_flip=True)                      # already the new owner
    assert (flip.bg, flip.symbol) == (theme.FLIP_PREVIEW, "●")
    assert theme.cell_look(B, O, is_flash=True).bg == theme.FLASH
    assert theme.cell_look(None, B, is_hint=True) == theme.CellLook(theme.HINT, "?", theme.DARK)
    assert theme.cell_look(None, B, is_pending=True, is_flip=True).bg == theme.BLUE_TINT
    assert theme.cell_look(O, B, is_flip=True, is_flash=True).bg == theme.FLIP_PREVIEW
    assert theme.cell_look(B, O, is_flash=True, is_last=True).bg == theme.FLASH
    assert theme.cell_look(None, B, is_pending=True, is_hint=True).bg == theme.BLUE_TINT
    assert theme.cell_look(B, O, is_hint=True).bg == theme.BLUE     # hints only on empty cells
    assert theme.cell_look(None, B, is_flash=True) == theme.cell_look(None, B)  # owned only


def test_cards_distinguish_the_chosen_option():
    selected, plain = theme.card_look(True), theme.card_look(False)
    assert selected.bg == theme.CARD_SELECTED and plain.bg == theme.CARD_BG
    assert selected.fg != plain.fg
    assert selected.border is not None and plain.border is None
