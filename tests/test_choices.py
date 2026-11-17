"""The menu choices (`Setup`) and how they are kept in the save file."""
from blockwar.bot import Level
from blockwar.choices import Setup, setup_from_save, store_setup
from blockwar.mathmode import OPERATIONS, MathSettings
from blockwar.models import DEFAULT_SIZE, Mode
from blockwar.storage import SaveData

ALL_MATH = MathSettings(frozenset(OPERATIONS), frozenset(range(1, 11)))


def test_default_setup():
    setup = Setup()
    assert setup.mode is Mode.BOT and setup.size == DEFAULT_SIZE
    assert setup.bot_level is Level.MEDIUM and setup.math == MathSettings()
    assert not setup.math.enabled


def test_setup_is_saved_and_restored():
    data = SaveData()
    setup = Setup(Mode.TWO, 5, Level.HARD, ALL_MATH)
    store_setup(data, setup)
    again = setup_from_save(data)
    assert (again.mode, again.bot_level, again.math) == (Mode.TWO, Level.HARD, ALL_MATH)


def test_the_board_size_is_not_saved():
    """It comes from the screen of each device (phone ~7x7, tablet up to 14x14)."""
    data = SaveData()
    store_setup(data, Setup(size=12))
    assert not hasattr(data, "size")
    assert setup_from_save(data).size == DEFAULT_SIZE
