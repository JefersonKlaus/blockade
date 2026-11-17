"""The save file (JSON): where it lives, how it is read and how it is written.

This is the only module that knows the file format. A bad file never breaks the app:
each invalid field falls back to its default without spoiling the others.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .bot import Level, level_from_value
from .mathmode import ADD, DEFAULT_TABLES, MUL, OPERATIONS, SUB, TABLES, MathSettings
from .models import Mode

logger = logging.getLogger(__name__)

# The file keeps the app's former name ("Guerra dos Blocos"), so existing saves and
# records are still found after the rename to Blockade.
SAVE_NAME = "guerra_dos_blocos.json"
OUTCOMES = ("wins", "losses", "draws")


@dataclass
class SaveData:
    """Everything that is saved: the menu choices and the records."""

    mode: Mode = Mode.BOT
    bot_level: Level = Level.MEDIUM
    math: MathSettings = field(default_factory=MathSettings)
    games_played: int = 0
    records: dict[str, dict[str, int]] = field(default_factory=dict)
    tutorial_seen: bool = False   # the "How to play" tutorial has opened by itself once


def default_path() -> Path:
    """BLOCKADE_SAVE (tests) > the app's data folder in Flet > the user's home folder."""
    override = os.environ.get("BLOCKADE_SAVE")
    if override:
        return Path(override)
    app_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if app_data:
        return Path(app_data) / SAVE_NAME
    return Path.home() / ".guerra_dos_blocos" / SAVE_NAME


# ------------------------------------------------------------------ writing

def math_to_dict(math: MathSettings) -> dict[str, Any]:
    return {"operations": list(math.ordered_operations()),
            "tables": list(math.ordered_tables())}


def save_save(data: SaveData, path: Optional[Path] = None) -> bool:
    """Writes a temporary file and swaps it in, so a save is never left half-written."""
    path = path or default_path()
    payload = {"mode": data.mode.value, "bot_level": data.bot_level.value,
               "math": math_to_dict(data.math), "games_played": data.games_played,
               "records": data.records, "tutorial_seen": data.tutorial_seen}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return True
    except OSError:
        logger.warning("could not save to %s", path, exc_info=True)
        return False


# ------------------------------------------------------------------ reading

def load_save(path: Optional[Path] = None) -> SaveData:
    """Reads the file; any problem gives the defaults instead of breaking the app."""
    path = path or default_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SaveData()
    if not isinstance(raw, dict):
        return SaveData()
    # Old saves only had a "math_level" (0 to 3); newer ones keep the actual choices.
    math = (math_from_dict(raw["math"]) if "math" in raw
            else math_from_legacy_level(raw.get("math_level")))
    return SaveData(
        mode=Mode.TWO if raw.get("mode") == Mode.TWO.value else Mode.BOT,
        bot_level=level_from_value(raw.get("bot_level")),
        math=math,
        games_played=_count(raw.get("games_played")),
        records=_records(raw.get("records")),
        tutorial_seen=raw.get("tutorial_seen") is True,
    )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _count(value: Any) -> int:
    """A counter: an integer, never negative (otherwise zero)."""
    return value if _is_int(value) and value >= 0 else 0


def _records(raw: Any) -> dict[str, dict[str, int]]:
    if not isinstance(raw, dict):
        return {}
    return {key: {name: _count(value.get(name)) for name in OUTCOMES}
            for key, value in raw.items() if isinstance(key, str) and isinstance(value, dict)}


def math_from_dict(raw: Any) -> MathSettings:
    """Reads the math choices; each bad field falls back to its default without spoiling
    the others. Also reads the previous format, which had a separate "enabled"."""
    if not isinstance(raw, dict):
        return MathSettings()
    raw_ops, raw_tables = raw.get("operations"), raw.get("tables")
    operations: frozenset[str] = frozenset()
    if isinstance(raw_ops, list) and raw.get("enabled") is not False:
        operations = frozenset(op for op in raw_ops if op in OPERATIONS)
    tables: frozenset[int] = frozenset()
    if isinstance(raw_tables, list):
        tables = frozenset(t for t in raw_tables if _is_int(t) and t in TABLES)
    return MathSettings(operations=operations, tables=tables or DEFAULT_TABLES)


def math_from_legacy_level(level: Any) -> MathSettings:
    """Converts the old "math level" (0 to 3) of the oldest saves."""
    if not _is_int(level):
        return MathSettings()
    return {
        1: MathSettings(frozenset({ADD, SUB})),
        2: MathSettings(frozenset({ADD, SUB, MUL}), frozenset({2, 3, 4, 5})),
        3: MathSettings(frozenset(OPERATIONS), frozenset(range(2, 11))),
    }.get(level, MathSettings())
