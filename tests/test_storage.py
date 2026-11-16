import json

import pytest

from blockwar import storage
from blockwar.mathmode import ADD, DIV, MUL, SUB, MathSettings
from blockwar.storage import SaveData


def write(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------- save and load

def test_roundtrip(tmp_path):
    path = tmp_path / "folder" / "save.json"
    math = MathSettings(frozenset({ADD, MUL}), frozenset({3, 7}))
    data = SaveData(mode="dois", bot_level="dificil", math=math, games_played=3,
                    records={"5:dificil:1": {"wins": 1, "losses": 2, "draws": 0}})
    assert storage.save_save(data, path) is True
    assert storage.load_save(path) == data


def test_defaults():
    data = SaveData()
    assert (data.mode, data.bot_level, data.math, data.games_played) == (
        "bot", "medio", MathSettings(), 0)
    assert data.records == {}
    assert SaveData().records is not SaveData().records  # no shared mutable default


def test_saved_file_is_readable_json_and_keeps_accents(tmp_path):
    path = tmp_path / "save.json"
    storage.save_save(SaveData(records={"placar-ção": {"wins": 1, "losses": 0, "draws": 0}}),
                      path)
    text = path.read_text(encoding="utf-8")
    assert "placar-ção" in text  # written as UTF-8, not as \\u escapes
    assert json.loads(text)["records"]["placar-ção"]["wins"] == 1


def test_saving_replaces_the_old_file_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{broken", encoding="utf-8")
    assert storage.save_save(SaveData(mode="dois"), path)
    assert storage.save_save(SaveData(mode="bot"), path)
    assert storage.load_save(path).mode == "bot"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["save.json"]


def test_save_returns_false_when_it_cannot_write(tmp_path, caplog):
    assert storage.save_save(SaveData(), tmp_path) is False  # the target is a folder
    assert "não consegui salvar" in caplog.text


def test_save_returns_false_when_the_parent_is_a_file(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert storage.save_save(SaveData(), blocker / "save.json") is False


def test_save_and_load_use_the_default_path(isolated_save_file):
    assert not isolated_save_file.exists()
    assert storage.save_save(SaveData(mode="dois"))
    assert isolated_save_file.exists() and storage.load_save().mode == "dois"


# ---------------------------------------------------------------- bad files

def test_missing_corrupt_and_wrong_types_fall_back_to_defaults(tmp_path):
    assert storage.load_save(tmp_path / "does-not-exist.json") == SaveData()
    path = tmp_path / "s.json"
    path.write_text("{garbage")
    assert storage.load_save(path) == SaveData()
    path.write_text("[1, 2]")
    assert storage.load_save(path) == SaveData()
    path.write_text("")
    assert storage.load_save(path) == SaveData()
    write(path, {"size": 99, "mode": "x", "bot_level": 3, "math": [7],
                 "games_played": True, "records": [1]})
    assert storage.load_save(path) == SaveData()


def test_a_file_that_is_not_utf8_falls_back_to_defaults(tmp_path):
    path = tmp_path / "s.json"
    path.write_bytes(b"\xff\xfe\x00garbage")
    assert storage.load_save(path) == SaveData()


def test_good_fields_survive_next_to_bad_ones(tmp_path):
    path = tmp_path / "s.json"
    write(path, {"mode": "nonsense", "bot_level": "facil",
                 "math": {"operations": ["mul", "pow"], "tables": [0]}, "games_played": 12})
    data = storage.load_save(path)
    assert (data.mode, data.bot_level, data.games_played) == ("bot", "facil", 12)
    assert data.math == MathSettings(frozenset({MUL}))  # only the bad parts were reset


def test_the_board_size_of_old_saves_is_ignored(tmp_path):
    """The size now comes from the screen. Old saves had one (and a float like 5.0 used
    to crash the game); it is simply not read anymore, nor written back."""
    path = tmp_path / "s.json"
    write(path, {"size": 5.0, "mode": "dois"})
    data = storage.load_save(path)
    assert data.mode == "dois" and not hasattr(data, "size")
    storage.save_save(data, path)
    assert "size" not in json.loads(path.read_text(encoding="utf-8"))


def test_the_math_settings_are_saved_as_readable_json(tmp_path):
    path = tmp_path / "s.json"
    math = MathSettings(frozenset({SUB, ADD}), frozenset({5, 2}))
    storage.save_save(SaveData(math=math), path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["math"] == {"operations": ["add", "sub"], "tables": [2, 5]}
    assert "math_level" not in raw


@pytest.mark.parametrize("level, enabled", [(0, False), (1, True), (2, True), (3, True)])
def test_old_saves_with_a_math_level_are_converted(tmp_path, level, enabled):
    """Saves written before the math page had only `math_level` (0-3)."""
    path = tmp_path / "s.json"
    write(path, {"math_level": level})
    data = storage.load_save(path)
    assert data.math.enabled is enabled
    if level == 3:
        assert data.math.operations == {ADD, SUB, MUL, DIV} and data.math.uses_tables


def test_new_math_settings_win_over_an_old_math_level(tmp_path):
    path = tmp_path / "s.json"
    write(path, {"math_level": 3, "math": {"operations": []}})
    assert storage.load_save(path).math == MathSettings()


@pytest.mark.parametrize("field, bad_value", [
    ("math_level", True),      # old saves: bool is an int in Python, but not a level
    ("math_level", 2.0),
    ("math_level", "2"),
    ("math", "on"),
    ("math", None),
    ("games_played", -3),
    ("games_played", 1.5),
])
def test_invalid_values_are_replaced_by_defaults(tmp_path, field, bad_value):
    path = tmp_path / "s.json"
    write(path, {field: bad_value})
    name = "math" if field == "math_level" else field
    assert getattr(storage.load_save(path), name) == getattr(SaveData(), name)


def test_records_are_cleaned_field_by_field(tmp_path):
    path = tmp_path / "s.json"
    write(path, {"records": {
        "ok": {"wins": 2, "losses": "x", "draws": -1}, "bad": 5, 3: {"wins": 1}}})
    # "bad" is not a dict and is dropped; the key 3 becomes "3" in JSON and is kept
    assert storage.load_save(path).records == {
        "ok": {"wins": 2, "losses": 0, "draws": 0},
        "3": {"wins": 1, "losses": 0, "draws": 0}}


def test_unknown_record_fields_are_dropped(tmp_path):
    path = tmp_path / "s.json"
    write(path, {"records": {"k": {"wins": 1, "extra": 9}}})
    assert storage.load_save(path).records == {"k": {"wins": 1, "losses": 0, "draws": 0}}


# ---------------------------------------------------------------- records

def test_record_outcome_counts_each_result():
    data = SaveData()
    storage.record_outcome(data, "k", "wins")
    storage.record_outcome(data, "k", "wins")
    storage.record_outcome(data, "k", "draws")
    storage.record_outcome(data, "other", "losses")
    assert storage.record_for(data, "k") == {"wins": 2, "losses": 0, "draws": 1}
    assert storage.record_for(data, "other") == {"wins": 0, "losses": 1, "draws": 0}
    assert storage.record_for(data, "missing") == {"wins": 0, "losses": 0, "draws": 0}
    assert data.games_played == 4


def test_invalid_outcome_changes_nothing():
    data = SaveData()
    with pytest.raises(ValueError):
        storage.record_outcome(data, "k", "won")
    assert data.records == {} and data.games_played == 0


def test_record_for_returns_a_copy():
    data = SaveData()
    storage.record_outcome(data, "k", "wins")
    storage.record_for(data, "k")["wins"] = 100
    assert data.records["k"]["wins"] == 1


# ---------------------------------------------------------------- where the file lives

def test_default_path_prefers_override_then_flet_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("GUERRA_SAVE", str(tmp_path / "a.json"))
    assert storage.default_path() == tmp_path / "a.json"
    monkeypatch.delenv("GUERRA_SAVE")
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))  # set by flet run / on device
    assert storage.default_path() == tmp_path / storage.SAVE_NAME
    monkeypatch.delenv("FLET_APP_STORAGE_DATA")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    assert storage.default_path() == tmp_path / ".guerra_dos_blocos" / storage.SAVE_NAME
