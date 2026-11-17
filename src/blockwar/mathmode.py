"""Math practice: to place a block, the player must answer a question correctly.

On the math page ("Practice math") the child, or an adult, chooses:
- which operations are asked: +, −, ×, ÷ (none chosen = no math);
- with × or ÷: which times tables (1 to 10).
Results never go above 100 (e.g. 99 + 1, 10 × 10).

This module only knows what is chosen and how to draw the questions; how the choices
are written to the save file is storage.py's job.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace

ADD, SUB, MUL, DIV = "add", "sub", "mul", "div"
OPERATIONS = (ADD, SUB, MUL, DIV)                 # fixed order: also the order on screen
SYMBOLS = {ADD: "+", SUB: "−", MUL: "×", DIV: "÷"}
MAX_RESULT = 100                                  # 99 + 1, 10 × 10
TABLES = tuple(range(1, 11))                      # times tables 1 to 10
FACTORS = tuple(range(1, 11))                     # table of 3: 3 × 1 ... 3 × 10
DEFAULT_TABLES = frozenset({2, 3, 4, 5})
_OFFSETS = (-10, -5, -3, -2, -1, 1, 2, 3, 5, 10)


@dataclass(frozen=True)
class Question:
    text: str
    answer: int
    choices: tuple[int, ...]


@dataclass(frozen=True)
class MathSettings:
    """The chosen math. With no operation, math is off. There is always at least one
    times table, so turning on × or ÷ never leaves the game without questions."""

    operations: frozenset[str] = frozenset()
    tables: frozenset[int] = DEFAULT_TABLES

    # ------------------------------------------------------------- queries

    @property
    def enabled(self) -> bool:
        return bool(self.operations)

    @property
    def uses_tables(self) -> bool:
        """Has × or ÷ (the operations that use the times tables)."""
        return bool(self.operations & {MUL, DIV})

    def ordered_operations(self) -> tuple[str, ...]:
        return tuple(op for op in OPERATIONS if op in self.operations)

    def ordered_tables(self) -> tuple[int, ...]:
        return tuple(sorted(self.tables))

    # ------------------------------------------------------------- changes

    def toggled_operation(self, op: str) -> "MathSettings":
        """Turns one operation on/off. Turning all of them off turns math off."""
        if op not in OPERATIONS:
            raise ValueError(f"unknown operation: {op}")
        return replace(self, operations=frozenset(self.operations ^ {op}))

    def toggled_table(self, table: int) -> "MathSettings":
        """Turns one times table on/off. The last table that is on cannot be turned off."""
        if table not in TABLES:
            raise ValueError(f"invalid times table: {table}")
        tables = self.tables ^ {table}
        return replace(self, tables=frozenset(tables)) if tables else self


# ------------------------------------------------------------- questions

def _operands(op: str, settings: MathSettings, rng: random.Random) -> tuple[str, int]:
    """Returns (text, answer) of a question with the given operation."""
    if op == ADD:  # the answer is never above 100
        a = rng.randint(1, MAX_RESULT - 1)
        b = rng.randint(1, MAX_RESULT - a)
        return f"{a} + {b}", a + b
    if op == SUB:  # never negative
        a = rng.randint(1, MAX_RESULT)
        b = rng.randint(1, a)
        return f"{a} − {b}", a - b
    # Always draw from tuples in a fixed order: a frozenset's iteration order changes from
    # one run to the next, which would break replaying a game with the same seed.
    table, factor = rng.choice(settings.ordered_tables()), rng.choice(FACTORS)
    if op == MUL:
        return f"{table} × {factor}", table * factor
    return f"{table * factor} ÷ {table}", factor


def _choices(answer: int, rng: random.Random) -> tuple[int, ...]:
    """Four options: the right one and three wrong ones close to it, in random order."""
    pool = sorted({answer + d for d in _OFFSETS if answer + d >= 0})
    options = rng.sample(pool, 3) + [answer]
    rng.shuffle(options)
    return tuple(options)


def make_question(settings: MathSettings, rng: random.Random) -> Question:
    """Draws a question that follows the choices."""
    if not settings.enabled:
        raise ValueError("no operation chosen")
    op = rng.choice(settings.ordered_operations())
    text, answer = _operands(op, settings, rng)
    return Question(f"{text} = ?", answer, _choices(answer, rng))

