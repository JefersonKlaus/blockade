"""Records against the phone: wins, losses and draws, kept per level.

Two-player games (e.g. parent and child) do not count.
"""
from __future__ import annotations

from typing import Optional

from .choices import Setup
from .models import HUMAN_PLAYER, Mode, Player
from .storage import OUTCOMES, SaveData
from .texts import Texts


def record_key(setup: Setup) -> Optional[str]:
    """Record key (only against the phone): board size, the phone's level and whether
    math is on (1) or off (0). Records with and without math are kept apart."""
    if setup.mode is not Mode.BOT:
        return None
    return f"{setup.size}:{setup.bot_level.value}:{1 if setup.math.enabled else 0}"


def outcome_for(winner: Optional[Player]) -> str:
    """The result from your side: 'wins', 'losses' or 'draws' (winner None = a draw)."""
    if winner is None:
        return "draws"
    return "wins" if winner is HUMAN_PLAYER else "losses"


def record_outcome(data: SaveData, key: str, outcome: str) -> None:
    """Adds a win ('wins'), loss ('losses') or draw ('draws') to the game's key."""
    if outcome not in OUTCOMES:
        raise ValueError(f"invalid outcome: {outcome}")
    entry = data.records.setdefault(key, {name: 0 for name in OUTCOMES})
    entry[outcome] += 1
    data.games_played += 1


def record_game(data: SaveData, setup: Setup, winner: Optional[Player]) -> Optional[str]:
    """Records a finished game. Returns the outcome, or None when the game does not count
    (two players)."""
    key = record_key(setup)
    if key is None:
        return None
    outcome = outcome_for(winner)
    record_outcome(data, key, outcome)
    return outcome


def record_for(data: SaveData, key: str) -> dict[str, int]:
    return dict(data.records.get(key, {name: 0 for name in OUTCOMES}))


def record_summary(data: SaveData, setup: Setup, texts: Texts) -> str:
    """The record text shown for these choices. Empty for two players, and before the
    first game at that level (nothing to show yet)."""
    key = record_key(setup)
    if key is None:
        return ""
    entry = record_for(data, key)
    if not any(entry.values()):
        return ""
    return texts.record.format(wins=entry["wins"], losses=entry["losses"],
                               draws=entry["draws"])
