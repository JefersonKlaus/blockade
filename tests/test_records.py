"""Records against the phone: wins, losses and draws per level."""

from blockwar.bot import Level
from blockwar.choices import Setup
from blockwar.mathmode import ADD, OPERATIONS, SUB, MathSettings
from blockwar.models import BOT_PLAYER, HUMAN_PLAYER, Mode
from blockwar.records import (record_for, record_game, record_key,
                              record_outcome, record_summary)
from blockwar.storage import SaveData
from blockwar.texts import ENGLISH, PORTUGUESE

MATH_ON = MathSettings(frozenset({ADD, SUB}))
ALL_MATH = MathSettings(frozenset(OPERATIONS), frozenset(range(1, 11)))


# ---------------------------------------------------------------- one record per level

def test_record_key_exists_only_against_the_phone():
    assert record_key(Setup(Mode.BOT, 7, Level.HARD, MATH_ON)) == "7:dificil:1"
    assert record_key(Setup(Mode.BOT, 5, Level.EASY)) == "5:facil:0"
    assert record_key(Setup(Mode.TWO)) is None


def test_different_choices_have_different_record_keys():
    """Size, level and math on/off each get their own record. Which math (signs, tables)
    does not, or every tweak of the tables would start a new, empty record."""
    assert record_key(Setup(math=MATH_ON)) == record_key(Setup(math=ALL_MATH))
    keys = {record_key(Setup(Mode.BOT, size, level, math))
            for size in (5, 7) for level in Level for math in (MathSettings(), MATH_ON)}
    assert len(keys) == 2 * 3 * 2


# ---------------------------------------------------------------- counting

def test_record_outcome_counts_each_result():
    data = SaveData()
    record_outcome(data, "k", "wins")
    record_outcome(data, "k", "wins")
    record_outcome(data, "k", "draws")
    record_outcome(data, "other", "losses")
    assert record_for(data, "k") == {"wins": 2, "losses": 0, "draws": 1}
    assert record_for(data, "other") == {"wins": 0, "losses": 1, "draws": 0}
    assert record_for(data, "missing") == {"wins": 0, "losses": 0, "draws": 0}
    assert data.games_played == 4


# ---------------------------------------------------------------- a finished game

def test_a_game_against_the_phone_is_recorded_under_its_level():
    data = SaveData()
    setup = Setup(Mode.BOT, 5, Level.HARD, MATH_ON)
    assert record_game(data, setup, HUMAN_PLAYER) == "wins"
    assert record_game(data, setup, BOT_PLAYER) == "losses"
    assert record_game(data, setup, None) == "draws"
    assert data.records == {"5:dificil:1": {"wins": 1, "losses": 1, "draws": 1}}
    assert data.games_played == 3


def test_two_player_games_are_not_recorded():
    data = SaveData()
    assert record_game(data, Setup(mode=Mode.TWO), HUMAN_PLAYER) is None
    assert data.records == {} and data.games_played == 0


# ---------------------------------------------------------------- menu text

def test_record_summary_text():
    data = SaveData(records={"7:medio:0": {"wins": 3, "losses": 1, "draws": 0}})
    assert record_summary(data, Setup(), PORTUGUESE) == (
        "Neste nível: 3 vitórias, 1 derrotas, 0 empates")
    assert record_summary(data, Setup(), ENGLISH) == "At this level: 3 won, 1 lost, 0 tied"
    assert record_summary(data, Setup(mode=Mode.TWO), ENGLISH) == ""


def test_record_summary_is_empty_before_the_first_game_at_that_level():
    """Nothing to brag about yet: no point cluttering a first-time player's menu."""
    assert record_summary(SaveData(), Setup(), ENGLISH) == ""
    data = SaveData(records={"7:medio:0": {"wins": 0, "losses": 0, "draws": 1}})
    assert record_summary(data, Setup(), ENGLISH) != ""  # but a single draw is still shown
