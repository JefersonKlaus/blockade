"""The menu: icon and name, who plays, the phone's level, the record and Play."""
from __future__ import annotations

from blockwar import theme
from blockwar.bot import Level
from blockwar.mathmode import ADD, MUL, MathSettings
from blockwar.models import Mode

from ui_queries import (EMOJI, MATH_BUTTON, buttons_in_order, centered_group, is_highlighted,
                        label, math_button, option, play_slot, root, screen, texts, walk)

WHO = "Quem vai jogar com você?"
HOW_SMART = "Quão esperto é o celular?"


def level_card(app, name: str):
    return option(app, HOW_SMART, name)


def test_the_menu_starts_with_the_app_name_below_a_big_app_icon(app, ui):
    app.show_menu()
    assert texts(app)[0] == "Blockade"
    header = root(app).controls[0]
    assert type(header).__name__ == "Column"             # stacked, not side by side
    icon, name = header.controls
    assert type(icon).__name__ == "Image" and icon.src == "icon.png"
    assert label(name) == "Blockade"
    assert icon.width == icon.height == ui.menu.ICON_SIZE >= 96
    assert str(header.horizontal_alignment).endswith("CENTER")


def test_the_menu_stays_simple_for_a_young_child(app):
    """Only two questions, nothing between the title and the first one (no subtitle, no
    tutorial text), and text-only buttons: no icons or emoji to decode."""
    app.show_menu()
    shown = texts(app)
    assert shown[1] == WHO
    assert [t for t in shown if t.endswith("?")] == [WHO, HOW_SMART]
    assert not [t for t in shown if EMOJI.search(t)]
    assert not [c for c in screen(app) if getattr(c, "icon", None)]


def test_the_choices_are_in_the_middle_and_play_is_at_the_bottom(app, ui):
    for mode in (Mode.BOT, Mode.TWO):
        app.setup.mode = mode
        app.show_menu()
        screen_root, group, slot = root(app), centered_group(app), play_slot(app)
        assert screen_root.controls[-1] is slot                    # nothing below Play
        assert (label(group.controls[-1]) or "").startswith(MATH_BUTTON)  # math right above
        choices = [c for c in walk(group) if getattr(c, "on_click", None)]
        assert len(choices) == len(buttons_in_order(app)) - 1      # every button but Play
        assert buttons_in_order(app)[-1] == "Jogar!"
        assert slot.padding.top == ui.menu.PLAY_GAP >= 24          # space above Play
        assert slot.padding.bottom == ui.menu.PLAY_BOTTOM >= 24    # close to, not on, the edge


def test_choosing_who_plays_and_the_level_updates_saves_and_redraws(app, ui):
    app.show_menu()
    assert is_highlighted(option(app, WHO, "O celular"))          # the default
    assert not is_highlighted(option(app, WHO, "Um amigo"))
    option(app, WHO, "Um amigo").on_click(None)
    assert app.setup.mode is Mode.TWO and app.save.mode is Mode.TWO
    assert HOW_SMART not in texts(app)                            # no level for two people
    option(app, WHO, "O celular").on_click(None)
    level_card(app, "Difícil").on_click(None)
    assert app.setup.bot_level is Level.HARD and app.save.bot_level is Level.HARD
    assert len(ui.saves) == 3
    assert is_highlighted(level_card(app, "Difícil"))


def test_levels_are_green_yellow_and_red(app):
    """Each level card keeps its colour; the chosen one is stronger and has a border."""
    for name, strong, tint in [("Fácil", theme.GREEN, theme.GREEN_TINT),
                               ("Médio", theme.YELLOW, theme.YELLOW_TINT),
                               ("Difícil", theme.RED, theme.RED_TINT)]:
        app.setup.bot_level = Level.EASY if name != "Fácil" else Level.HARD
        app.show_menu()
        assert level_card(app, name).bgcolor == tint and not is_highlighted(level_card(app, name))
        level_card(app, name).on_click(None)
        assert level_card(app, name).bgcolor == strong and is_highlighted(level_card(app, name))


def test_menu_shows_the_record_only_against_the_phone_and_after_playing(app):
    app.setup.mode = Mode.BOT
    app.show_menu()
    assert not any(t.startswith("Neste nível") for t in texts(app))  # nothing played yet
    app.save.records["5:medio:0"] = {"wins": 2, "losses": 1, "draws": 0}
    app.setup.size = 5
    app.show_menu()
    assert "Neste nível: 2 vitórias, 1 derrotas, 0 empates" in texts(app)
    app.setup.mode = Mode.TWO
    app.show_menu()
    assert not any(t.startswith("Neste nível") for t in texts(app))


def test_the_math_button_never_looks_switched_on(app):
    """The menu's Play never has math, so the math button is just the way to the math
    game, never a highlighted "math is on" switch."""
    for math in (MathSettings(), MathSettings(frozenset({ADD, MUL}))):
        app.setup.math = math
        app.show_menu()
        assert label(math_button(app)) == MATH_BUTTON and not is_highlighted(math_button(app))
