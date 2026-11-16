"""Salva configurações e recordes em um arquivo JSON (tolerante a arquivo ruim)."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .mathmode import MathSettings, settings_from_dict, settings_from_legacy_level

logger = logging.getLogger(__name__)

SAVE_NAME = "guerra_dos_blocos.json"
OUTCOMES = ("wins", "losses", "draws")
_MODES = ("bot", "dois")
_LEVELS = ("facil", "medio", "dificil")


@dataclass
class SaveData:
    mode: str = "bot"
    bot_level: str = "medio"
    math: MathSettings = field(default_factory=MathSettings)
    games_played: int = 0
    records: dict[str, dict[str, int]] = field(default_factory=dict)


def default_path() -> Path:
    """GUERRA_SAVE (testes) > pasta de dados do app no Flet > pasta do usuário."""
    override = os.environ.get("GUERRA_SAVE")
    if override:
        return Path(override)
    app_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if app_data:
        return Path(app_data) / SAVE_NAME
    return Path.home() / ".guerra_dos_blocos" / SAVE_NAME


def _int(value: Any, default: int) -> int:
    ok = isinstance(value, int) and not isinstance(value, bool) and value >= 0
    return value if ok else default


def _clean_records(raw: Any) -> dict[str, dict[str, int]]:
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, dict[str, int]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            cleaned[key] = {name: _int(value.get(name), 0) for name in OUTCOMES}
    return cleaned


def load_save(path: Optional[Path] = None) -> SaveData:
    """Lê o arquivo; qualquer problema devolve valores padrão em vez de quebrar o app."""
    path = path or default_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SaveData()
    if not isinstance(raw, dict):
        return SaveData()
    mode, level = raw.get("mode"), raw.get("bot_level")
    # Saves antigos tinham só um "math_level" (0 a 3); os novos guardam as escolhas.
    math = (settings_from_dict(raw["math"]) if "math" in raw
            else settings_from_legacy_level(raw.get("math_level")))
    return SaveData(
        mode=mode if mode in _MODES else "bot",
        bot_level=level if level in _LEVELS else "medio",
        math=math,
        games_played=_int(raw.get("games_played"), 0),
        records=_clean_records(raw.get("records")),
    )


def save_save(data: SaveData, path: Optional[Path] = None) -> bool:
    """Grava com arquivo temporário + troca, para não deixar o save pela metade."""
    path = path or default_path()
    payload = {"mode": data.mode, "bot_level": data.bot_level,
               "math": data.math.to_dict(), "games_played": data.games_played,
               "records": data.records}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return True
    except OSError:
        logger.warning("não consegui salvar em %s", path, exc_info=True)
        return False


def record_outcome(data: SaveData, key: str, outcome: str) -> None:
    """Soma uma vitória ('wins'), derrota ('losses') ou empate ('draws') à chave da partida."""
    if outcome not in OUTCOMES:
        raise ValueError(f"resultado inválido: {outcome}")
    entry = data.records.setdefault(key, {name: 0 for name in OUTCOMES})
    entry[outcome] += 1
    data.games_played += 1


def record_for(data: SaveData, key: str) -> dict[str, int]:
    return dict(data.records.get(key, {name: 0 for name in OUTCOMES}))
