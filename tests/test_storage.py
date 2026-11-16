import json

import pytest

from blockwar import storage
from blockwar.storage import SaveData


def test_roundtrip(tmp_path):
    path = tmp_path / "pasta" / "save.json"
    data = SaveData(size=5, mode="dois", bot_level="dificil", math_level=2, games_played=3,
                    records={"5:dificil:2": {"wins": 1, "losses": 2, "draws": 0}})
    assert storage.save_save(data, path) is True
    assert storage.load_save(path) == data


def test_missing_corrupt_and_wrong_types_fall_back_to_defaults(tmp_path):
    assert storage.load_save(tmp_path / "nao-existe.json") == SaveData()
    path = tmp_path / "s.json"
    path.write_text("{lixo")
    assert storage.load_save(path) == SaveData()
    path.write_text("[1, 2]")
    assert storage.load_save(path) == SaveData()
    path.write_text(json.dumps({"size": 99, "mode": "x", "bot_level": 3, "math_level": 7,
                                "games_played": True, "records": [1]}))
    assert storage.load_save(path) == SaveData()


def test_records_are_cleaned_field_by_field(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"records": {
        "ok": {"wins": 2, "losses": "x", "draws": -1}, "ruim": 5, 3: {"wins": 1}}}))
    # "ruim" não é um dicionário e some; a chave 3 vira "3" no JSON e é aceita
    assert storage.load_save(path).records == {
        "ok": {"wins": 2, "losses": 0, "draws": 0},
        "3": {"wins": 1, "losses": 0, "draws": 0}}


def test_save_returns_false_when_it_cannot_write(tmp_path):
    assert storage.save_save(SaveData(), tmp_path) is False  # o destino é uma pasta


def test_record_outcome_counts_each_result():
    data = SaveData()
    storage.record_outcome(data, "k", "wins")
    storage.record_outcome(data, "k", "wins")
    storage.record_outcome(data, "k", "draws")
    assert storage.record_for(data, "k") == {"wins": 2, "losses": 0, "draws": 1}
    assert storage.record_for(data, "outra") == {"wins": 0, "losses": 0, "draws": 0}
    assert data.games_played == 3
    with pytest.raises(ValueError):
        storage.record_outcome(data, "k", "ganhou")


def test_default_path_prefers_override_then_flet_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("GUERRA_SAVE", str(tmp_path / "a.json"))
    assert storage.default_path() == tmp_path / "a.json"
    monkeypatch.delenv("GUERRA_SAVE")
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    assert storage.default_path() == tmp_path / storage.SAVE_NAME
    monkeypatch.delenv("FLET_APP_STORAGE_DATA")
    assert storage.default_path().name == storage.SAVE_NAME
