"""The end of a game: the result, the record (saved once) and the end buttons."""
from __future__ import annotations

from blockwar.models import Mode

from ui_actions import click, finish_game, run, start, tap_twice
from ui_queries import texts, view, visible_buttons


def test_game_over_shows_the_result_and_records_a_win(app, ui):
    finish_game(app)
    assert app.game.match.is_over
    assert view(app).end_box.visible is True
    assert view(app).end_title.value == "Você venceu! 21 × 4"
    assert view(app).end_record.value.startswith("Neste nível: 1 vitórias")
    assert app.save.records["5:medio:0"]["wins"] == 1
    assert ui.saves[-1] == 1                      # the record was written to disk
    assert view(app).btn_hint.disabled and view(app).btn_undo.disabled
    assert view(app).turn_text.value == "Fim de jogo"


def test_the_result_is_saved_only_once(app, ui):
    finish_game(app)
    app.game.render()
    run(app.game._after_move())
    assert ui.saves == [0, 1]        # 0: the tutorial was seen; 1: the win, saved once


def test_a_game_in_progress_is_not_recorded(app, ui):
    start(app, mode=Mode.BOT)
    tap_twice(app, (1, 3))                        # you and the phone both played
    assert app.save.records == {} and ui.saves == [0]   # only "the tutorial was seen"


def test_there_is_one_menu_button_during_and_after_a_game(app):
    start(app)
    assert len(visible_buttons(app, "Menu")) == 1          # the bottom bar
    finish_game(app)
    assert len(visible_buttons(app, "Menu")) == 1          # only the one next to...
    assert len(visible_buttons(app, "Jogar de novo")) == 1  # ..."Jogar de novo"
    assert not visible_buttons(app, "Dica") and not visible_buttons(app, "Desfazer (3)")
    click(app, "Jogar de novo")
    assert len(visible_buttons(app, "Menu")) == 1          # the bottom bar is back


def test_play_again_and_menu_buttons(app):
    finish_game(app)
    click(app, "Jogar de novo")
    assert app.game.match.game.turn == 0 and view(app).end_box.visible is False
    app.on_menu(None)
    assert "Jogar!" in texts(app) and "Quem vai jogar com você?" in texts(app)
