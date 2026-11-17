import re
import subprocess
import sys
from pathlib import Path

import pytest

from blockwar import simulate
from blockwar.bot import Level
from blockwar.models import Player

SRC = Path(__file__).resolve().parents[1] / "src"


def test_tournament_counts_every_game_including_draws():
    # 4x4 has an even number of cells, so a full board can end 8 x 8
    tally = simulate.tournament(4, 4, Level.EASY, Level.EASY, seed=0)
    assert sum(tally.values()) == 4 and tally["draw"] >= 1
    assert tally["first"] + tally["second"] >= 1                  # games really are played
    assert set(tally) <= {"first", "second", "draw"}
    assert tally == simulate.tournament(4, 4, Level.EASY, Level.EASY, seed=0)  # repeatable
    with pytest.raises(ValueError):
        simulate.tournament(0, 5, Level.MEDIUM, Level.EASY)


def test_tournament_swaps_colours_and_credits_the_right_level(monkeypatch):
    """Every second game the levels swap colours, and each win goes to the level that won,
    whatever colour it played."""
    calls = []

    def fake_play_game(size, blue, orange, seed):      # the hard level always wins
        calls.append((blue, orange, seed))
        return Player.BLUE if blue is Level.HARD else Player.ORANGE

    monkeypatch.setattr(simulate, "play_game", fake_play_game)
    tally = simulate.tournament(4, 5, Level.HARD, Level.EASY, seed=10)
    assert calls == [(Level.HARD, Level.EASY, 10), (Level.EASY, Level.HARD, 11),
                     (Level.HARD, Level.EASY, 12), (Level.EASY, Level.HARD, 13)]
    assert tally["first"] == 4 and tally["second"] == 0 and tally["draw"] == 0


@pytest.mark.slow
def test_balance_guard_hard_beats_easy_and_medium_most_of_the_time():
    """If a rule change breaks this, the bot levels need to be reviewed."""
    vs_easy = simulate.tournament(16, 7, Level.HARD, Level.EASY, seed=10)
    assert vs_easy["first"] >= 13
    vs_medium = simulate.tournament(16, 7, Level.HARD, Level.MEDIUM, seed=20)
    assert vs_medium["first"] >= 11


def test_cli_runs_as_a_module():
    """`python -m blockwar.simulate` is the command documented in the README."""
    result = subprocess.run(
        [sys.executable, "-m", "blockwar.simulate", "--games", "2", "--size", "5"],
        capture_output=True, text=True, timeout=60, cwd=SRC, check=False)
    assert result.returncode == 0, result.stderr
    summary = re.search(r"dificil x facil on 5x5, 2 games: dificil (\d), facil (\d), draws (\d)",
                        result.stdout)
    assert summary and sum(int(n) for n in summary.groups()) == 2
