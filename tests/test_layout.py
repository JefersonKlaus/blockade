"""Board and score-bar sizes for each screen (phone ~7x7, tablet up to 14x14)."""
from blockwar import layout


def test_the_score_bar_is_split_by_the_score_and_always_fills_the_bar():
    assert layout.bar_widths(0, 0, 300) == (0, 0)
    assert layout.bar_widths(2, 2, 300) == (150, 150)
    assert layout.bar_widths(5, 0, 200) == (200, 0)
    left, right = layout.bar_widths(7, 3, 301)
    assert left + right == 301 and left > right
    for blue in range(0, 50, 7):
        for orange in range(0, 50, 5):
            left, right = layout.bar_widths(blue, orange, 337)
            assert left >= 0 and right >= 0 and left + right in (0, 337)


def test_the_grid_is_the_biggest_that_fits_the_screen():
    for width, height, grid in [
        (360, 640, 6),      # small Android phone
        (390, 844, 7),      # iPhone 14
        (430, 900, 8),      # the desktop window opened by main()
        (600, 960, 11),     # 7" tablet
        (768, 1024, 14),    # iPad...
        (1024, 1366, 14),   # ...but never more than 14x14
    ]:
        assert layout.grid_size(layout.board_space(width, height, 12)) == grid, (width, height)


def test_squares_stay_big_enough_for_a_finger_and_fill_the_space():
    for space in range(100, 1400, 37):
        size = layout.grid_size(space)
        assert layout.MIN_GRID <= size <= layout.MAX_GRID == 14
        side = layout.cell_side(size, space)
        if size > layout.MIN_GRID:
            assert side >= layout.TOUCH_CELL           # never smaller than a finger
            assert layout.cell_side(size + 1, space) < layout.TOUCH_CELL or size == 14
        total = layout.board_width(size, side)
        assert total <= space and space - total < size  # the board fills the space


def test_the_board_fits_the_height_on_short_screens():
    """Landscape-shaped windows: the board must leave room for the rest of the game."""
    assert layout.board_space(1000, 600, 12) == 600 - 24 - layout.RESERVED_HEIGHT


def test_unknown_screen_size_uses_a_phone_default():
    assert layout.board_space(None, None, 12) == layout.DEFAULT_SPACE
    assert layout.grid_size(layout.DEFAULT_SPACE) == 8
