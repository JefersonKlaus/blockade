"""Praticar matemática: the four signs, the times tables and its own Jogar!."""
from __future__ import annotations


from blockwar.mathmode import ADD, DIV, MUL, SUB, MathSettings

from ui_actions import click, open_math_page
from ui_queries import (
    EMOJI,
    MATH_BUTTON,
    buttons_in_order,
    centered_group,
    is_highlighted,
    math_button,
    on_screen,
    option,
    play_slot,
    root,
    symbol,
    texts,
)


def test_math_page_shows_only_the_four_symbols(app):
    open_math_page(app)
    shown = texts(app)
    assert MATH_BUTTON in shown
    for sign in ("+", "−", "×", "÷"):
        assert not is_highlighted(symbol(app, sign))
    for word in ("Mais", "Menos", "Vezes", "Dividir", "Números até", "Ligar as contas?"):
        assert word not in shown
    assert "Tabuada" not in shown                   # no × or ÷ yet
    assert not [t for t in shown if EMOJI.search(t)]


def test_math_page_has_play_at_the_bottom_in_the_same_place_as_the_menu(app):
    app.show_menu()
    menu_root, menu_slot = root(app), play_slot(app)
    app.setup.math = MathSettings(frozenset({MUL}))
    open_math_page(app)
    math_root, math_slot = root(app), play_slot(app)
    centered_group(app)                               # the signs/tables are centered
    assert math_root.controls[-1] is math_slot
    # same slot, same spacing, same button size: Play does not move between screens
    assert (math_slot.padding.top, math_slot.padding.bottom) == (
        menu_slot.padding.top, menu_slot.padding.bottom)
    assert (math_slot.content.width, math_slot.content.height) == (
        menu_slot.content.width, menu_slot.content.height)
    assert menu_root.expand is math_root.expand is True   # both fill the screen height
    assert buttons_in_order(app)[0] == "◀ Voltar"   # the back link stays at the top


def test_choosing_operations_is_multiple_choice_and_saved(app, ui):
    open_math_page(app)
    symbol(app, "+").on_click(None)
    symbol(app, "−").on_click(None)
    assert app.setup.math.operations == {ADD, SUB} and app.save.math.operations == {ADD, SUB}
    assert is_highlighted(symbol(app, "+")) and is_highlighted(symbol(app, "−"))
    symbol(app, "+").on_click(None)
    assert app.setup.math.operations == {SUB} and not is_highlighted(symbol(app, "+"))
    assert len(ui.saves) == 3


def test_times_tables_appear_below_with_multiplication_or_division(app):
    open_math_page(app)
    symbol(app, "+").on_click(None)
    assert "Tabuada" not in texts(app)
    for sign in ("×", "÷"):
        symbol(app, sign).on_click(None)
        shown = texts(app)
        assert "Tabuada" in shown
        assert shown.index("Tabuada") > shown.index("÷")  # below the four symbols
        for table in range(1, 11):
            option(app, "Tabuada", str(table))            # every table 1-10 is offered
        symbol(app, sign).on_click(None)
        assert "Tabuada" not in texts(app)


def test_choosing_several_times_tables(app):
    app.setup.math = MathSettings(frozenset({MUL}), frozenset({2}))
    open_math_page(app)
    option(app, "Tabuada", "7").on_click(None)
    option(app, "Tabuada", "9").on_click(None)
    assert app.setup.math.tables == {2, 7, 9} and app.save.math.tables == {2, 7, 9}
    option(app, "Tabuada", "2").on_click(None)
    assert app.setup.math.tables == {7, 9}
    assert is_highlighted(option(app, "Tabuada", "7"))
    assert not is_highlighted(option(app, "Tabuada", "2"))


def test_back_returns_to_the_menu_keeping_the_choices(app):
    open_math_page(app)
    symbol(app, "÷").on_click(None)
    click(app, "◀ Voltar")
    assert on_screen(app) == "menu" and app.setup.math.operations == {DIV}
    math_button(app).on_click(None)
    assert is_highlighted(symbol(app, "÷"))          # still chosen on the math page
