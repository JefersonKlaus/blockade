import json

from blockwar import storage
from blockwar.bot import Level
from blockwar.mathmode import ADD, MUL, OPERATIONS, SUB, TABLES, MathSettings
from blockwar.models import Mode
from blockwar.storage import SaveData, math_from_dict, math_from_legacy_level, math_to_dict


def write(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def settings(ops=OPERATIONS, tables=(2, 3, 4, 5)) -> MathSettings:
    return MathSettings(frozenset(ops), frozenset(tables))


# ---------------------------------------------------------------- save and load

def test_roundtrip_in_a_readable_format(tmp_path):
    path = tmp_path / "folder" / "save.json"
    data = SaveData(mode=Mode.TWO, bot_level=Level.HARD, math=settings(OPERATIONS, (5, 2)),
                    games_played=3, records={"5:dificil:1": {"wins": 1, "losses": 2, "draws": 0}},
                    tutorial_seen=True)
    assert storage.save_save(data, path) is True
    assert storage.load_save(path) == data
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert (raw["mode"], raw["bot_level"]) == ("dois", "dificil")   # older saves' words
    assert raw["math"] == {"operations": ["add", "sub", "mul", "div"], "tables": [2, 5]}


def test_saving_replaces_the_old_file_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{broken", encoding="utf-8")
    assert storage.save_save(SaveData(mode=Mode.TWO), path)
    assert storage.save_save(SaveData(mode=Mode.BOT), path)
    assert storage.load_save(path).mode is Mode.BOT
    assert sorted(p.name for p in tmp_path.iterdir()) == ["save.json"]


def test_save_returns_false_when_it_cannot_write(tmp_path, caplog):
    assert storage.save_save(SaveData(), tmp_path) is False  # the target is a folder
    assert "could not save" in caplog.text


def test_default_path_prefers_override_then_flet_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("BLOCKADE_SAVE", str(tmp_path / "a.json"))
    assert storage.default_path() == tmp_path / "a.json"
    monkeypatch.delenv("BLOCKADE_SAVE")
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))  # set by flet run / on device
    assert storage.default_path() == tmp_path / storage.SAVE_NAME
    monkeypatch.delenv("FLET_APP_STORAGE_DATA")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    # the old file name: renaming it would lose every existing save
    assert storage.default_path() == tmp_path / ".guerra_dos_blocos" / "guerra_dos_blocos.json"


# ---------------------------------------------------------------- bad files

def test_missing_corrupt_and_wrong_types_fall_back_to_defaults(tmp_path):
    assert storage.load_save(tmp_path / "does-not-exist.json") == SaveData()
    path = tmp_path / "s.json"
    for text in ("{garbage", "[1, 2]", ""):
        path.write_text(text)
        assert storage.load_save(path) == SaveData()
    path.write_bytes(b"\xff\xfe\x00garbage")                      # not UTF-8
    assert storage.load_save(path) == SaveData()
    write(path, {"mode": "x", "bot_level": 3, "math": [7], "games_played": True, "records": [1]})
    assert storage.load_save(path) == SaveData()


def test_good_fields_survive_next_to_bad_ones(tmp_path):
    path = tmp_path / "s.json"
    write(path, {"mode": "nonsense", "bot_level": "facil",
                 "math": {"operations": ["mul", "pow"], "tables": [0]}, "games_played": 12})
    data = storage.load_save(path)
    assert (data.mode, data.bot_level, data.games_played) == (Mode.BOT, Level.EASY, 12)
    assert data.math == MathSettings(frozenset({MUL}))  # only the bad parts were reset


def test_invalid_values_are_replaced_by_defaults(tmp_path):
    path = tmp_path / "s.json"
    for field, bad_value in [
        ("math", "on"), ("math", None),
        ("games_played", -3), ("games_played", 1.5),
        ("tutorial_seen", 1), ("tutorial_seen", "true"),   # only a real JSON true counts
    ]:
        write(path, {field: bad_value})
        assert getattr(storage.load_save(path), field) == getattr(SaveData(), field), field


def test_records_are_cleaned_field_by_field(tmp_path):
    path = tmp_path / "s.json"
    write(path, {"records": {
        "ok": {"wins": 2, "losses": "x", "draws": -1, "extra": 9}, "bad": 5, 3: {"wins": 1}}})
    # "bad" is not a dict and is dropped; the key 3 becomes "3" in JSON and is kept
    assert storage.load_save(path).records == {
        "ok": {"wins": 2, "losses": 0, "draws": 0},
        "3": {"wins": 1, "losses": 0, "draws": 0}}


# ---------------------------------------------------------------- math settings in the file

def test_math_settings_roundtrip_through_a_dict():
    for math in (MathSettings(), settings(), settings([MUL], (7,)), settings(OPERATIONS, TABLES)):
        assert math_from_dict(math_to_dict(math)) == math


def test_bad_saved_math_settings_are_fixed_field_by_field():
    for raw in (None, [], "x", 3, {}):
        assert math_from_dict(raw) == MathSettings()
    math = math_from_dict({"operations": ["add", "pow", 3], "tables": [2, 11, True, "5", 7]})
    assert math == MathSettings(frozenset({ADD}), frozenset({2, 7}))
    assert math_from_dict({"operations": ["mul"], "tables": []}).tables == {2, 3, 4, 5}


def test_the_previous_format_with_an_enabled_flag_is_read():
    old_off = {"enabled": False, "max_number": 20, "operations": ["add"], "tables": [3]}
    assert math_from_dict(old_off) == MathSettings(tables=frozenset({3}))
    old_on = {"enabled": True, "max_number": 20, "operations": ["add", "mul"], "tables": [3]}
    assert math_from_dict(old_on) == settings([ADD, MUL], (3,))


def test_old_saves_with_a_math_level_are_converted(tmp_path):
    """Saves written before the math page had only a `math_level` (0-3)."""
    assert [math_from_legacy_level(level) for level in (0, 1, 2, 3)] == [
        MathSettings(),
        settings([ADD, SUB]),
        settings([ADD, SUB, MUL], (2, 3, 4, 5)),
        settings(OPERATIONS, range(2, 11)),
    ]
    for bad in (None, True, 7, 2.0, "2"):       # bool is an int in Python, but not a level
        assert math_from_legacy_level(bad) == MathSettings()
    path = tmp_path / "s.json"
    write(path, {"math_level": 1})
    assert storage.load_save(path).math == settings([ADD, SUB])
    write(path, {"math_level": 3, "math": {"operations": []}})   # the new format wins
    assert storage.load_save(path).math == MathSettings()
