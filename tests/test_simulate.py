import pytest

from blockwar import simulate
from blockwar.bot import Level
from blockwar.models import Player


def test_play_game_is_reproducible_and_always_finishes():
    first = simulate.play_game(7, Level.MEDIUM, Level.EASY, seed=3)
    assert first in (Player.BLUE, Player.ORANGE, None)
    assert first == simulate.play_game(7, Level.MEDIUM, Level.EASY, seed=3)


def test_tournament_counts_every_game():
    tally = simulate.tournament(6, 5, Level.MEDIUM, Level.EASY, seed=1)
    assert sum(tally.values()) == 6
    with pytest.raises(ValueError):
        simulate.tournament(0, 5, Level.MEDIUM, Level.EASY)


def test_balance_guard_hard_beats_easy_and_medium_most_of_the_time():
    """Se uma mudança nas regras quebrar isto, os níveis precisam ser revistos."""
    vs_easy = simulate.tournament(16, 7, Level.HARD, Level.EASY, seed=10)
    assert vs_easy["first"] >= 13
    vs_medium = simulate.tournament(16, 7, Level.HARD, Level.MEDIUM, seed=20)
    assert vs_medium["first"] >= 11


def test_cli_prints_a_summary(capsys):
    assert simulate.main(["--games", "4", "--size", "5", "--blue", "medio",
                          "--orange", "facil"]) == 0
    out = capsys.readouterr().out
    assert "medio x facil em 5x5, 4 partidas" in out
