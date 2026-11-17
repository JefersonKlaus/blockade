"""Math questions during a game started from the math page."""
from __future__ import annotations

from blockwar.models import Mode, Player

from ui_actions import click, start, tap_twice
from ui_queries import clickable, texts, view


def test_a_right_answer_places_the_block_and_the_phone_replies(app):
    start(app, mode=Mode.BOT, math=True)
    tap_twice(app, (1, 3))
    assert view(app).question_box.visible is True
    assert app.game.match.question.text in texts(app)
    for choice in app.game.match.question.choices:
        assert clickable(app, str(choice))
    assert view(app).btn_hint.disabled and view(app).btn_undo.disabled
    click(app, str(app.game.match.question.answer))
    assert app.game.match.game.board.get((1, 3)) is Player.BLUE
    assert view(app).question_box.visible is False and view(app).question_box.controls == []
    assert app.game.match.game.turn == 2 and view(app).turn_text.value == "Sua vez"


def test_a_wrong_answer_loses_the_turn_and_the_phone_plays(app):
    start(app, mode=Mode.BOT, math=True)
    tap_twice(app, (1, 3))
    wrong = next(c for c in app.game.match.question.choices if c != app.game.match.question.answer)
    click(app, str(wrong))
    assert app.game.match.game.board.get((1, 3)) is None
    assert app.game.match.game.turn == 2 and view(app).turn_text.value == "Sua vez"
    assert view(app).message.value.startswith("Celular")   # the phone played after you
