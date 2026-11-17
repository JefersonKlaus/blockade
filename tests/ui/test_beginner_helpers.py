"""Dica (hint) and Desfazer (undo): only against the phone on Fácil."""
from __future__ import annotations

from blockwar import theme
from blockwar.bot import Level
from blockwar.models import Mode

from ui_actions import click, start, tap_twice
from ui_queries import label, screen, view


def start_beginner(app):
    """Against the phone on Fácil: the only level with Dica and Desfazer."""
    return start(app, mode=Mode.BOT, level=Level.EASY)


def test_hint_marks_a_cell_and_undo_reverts(app):
    start_beginner(app)
    click(app, "Dica")
    hint = app.game.match.hint_pos
    assert view(app).cells[hint[0]][hint[1]].bgcolor == theme.HINT
    assert view(app).labels[hint[0]][hint[1]].value == "?"
    tap_twice(app, (1, 3))                        # you play, the phone answers
    assert app.game.match.game.turn == 2
    click(app, "Desfazer (3)")
    assert app.game.match.game.turn == 0 and view(app).message.value == "Jogada desfeita."
    assert view(app).cells[1][3].bgcolor == theme.EMPTY
    assert label(view(app).btn_undo) == "Desfazer (2)"
    app.game.on_undo(None)
    assert view(app).message.value == "Não dá para desfazer agora."


def test_undo_button_is_disabled_when_no_undos_are_left(app):
    start_beginner(app)
    for _ in range(3):
        tap_twice(app, app.game.match.game.board.empty_cells()[0])
        assert view(app).btn_undo.disabled is False       # still one (or more) left
        app.game.on_undo(None)
    tap_twice(app, app.game.match.game.board.empty_cells()[0])
    assert app.game.match.undos_left == 0 and view(app).btn_undo.disabled is True


def test_hint_and_undo_buttons_are_there_only_on_the_beginner_level(app):
    start_beginner(app)
    assert view(app).btn_hint.visible and view(app).btn_undo.visible
    for mode, level in ((Mode.BOT, Level.MEDIUM), (Mode.BOT, Level.HARD),
                        (Mode.TWO, Level.EASY)):
        start(app, mode=mode, level=level)
        assert view(app).btn_hint.visible is False and view(app).btn_undo.visible is False
        assert app.on_menu in [c.on_click for c in screen(app) if label(c) == "Menu"]
