"""Modo "Praticar matemática": para colocar o bloco, é preciso acertar uma conta.

Na página "Praticar matemática" a criança (ou um adulto) escolhe:
- quais contas entram: +, −, ×, ÷ (nenhuma escolhida = sem contas);
- com × ou ÷: quais tabuadas (1 a 10).
O resultado nunca passa de 100 (ex.: 99 + 1, 10 × 10).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Any, Iterable

ADD, SUB, MUL, DIV = "add", "sub", "mul", "div"
OPERATIONS = (ADD, SUB, MUL, DIV)                 # ordem fixa: também a ordem na tela
SYMBOLS = {ADD: "+", SUB: "−", MUL: "×", DIV: "÷"}
MAX_RESULT = 100                                  # 99 + 1, 10 × 10
TABLES = tuple(range(1, 11))                      # tabuadas do 1 ao 10
FACTORS = tuple(range(1, 11))                     # tabuada do 3: 3 × 1 ... 3 × 10
DEFAULT_TABLES = frozenset({2, 3, 4, 5})
_OFFSETS = (-10, -5, -3, -2, -1, 1, 2, 3, 5, 10)


@dataclass(frozen=True)
class Question:
    text: str
    answer: int
    choices: tuple[int, ...]


@dataclass(frozen=True)
class MathSettings:
    """As contas escolhidas. Sem nenhuma operação, as contas ficam desligadas. Sempre há
    pelo menos uma tabuada, para que ligar × ou ÷ nunca deixe o jogo sem perguntas."""

    operations: frozenset[str] = frozenset()
    tables: frozenset[int] = DEFAULT_TABLES

    # ------------------------------------------------------------- consulta

    @property
    def enabled(self) -> bool:
        return bool(self.operations)

    @property
    def uses_tables(self) -> bool:
        """Tem conta de × ou ÷ (as que usam as tabuadas)."""
        return bool(self.operations & {MUL, DIV})

    def ordered_operations(self) -> tuple[str, ...]:
        return tuple(op for op in OPERATIONS if op in self.operations)

    def ordered_tables(self) -> tuple[int, ...]:
        return tuple(sorted(self.tables))

    def symbols(self) -> str:
        """ "+ ×" para o botão do menu (vazio quando desligado)."""
        return " ".join(SYMBOLS[op] for op in self.ordered_operations())

    def summary(self) -> str:
        """Resumo, ex.: "+ × · tabuadas 2 a 5"."""
        if not self.enabled:
            return "Desligado"
        if not self.uses_tables:
            return self.symbols()
        word = "tabuadas" if len(self.tables) > 1 else "tabuada"
        return f"{self.symbols()} · {word} {tables_text(self.ordered_tables())}"

    # ------------------------------------------------------------- mudanças

    def toggled_operation(self, op: str) -> "MathSettings":
        """Liga/desliga uma operação. Desligar todas desliga as contas."""
        if op not in OPERATIONS:
            raise ValueError(f"operação desconhecida: {op}")
        return replace(self, operations=frozenset(self.operations ^ {op}))

    def toggled_table(self, table: int) -> "MathSettings":
        """Liga/desliga uma tabuada. A última tabuada ligada não pode ser desligada."""
        if table not in TABLES:
            raise ValueError(f"tabuada inválida: {table}")
        tables = self.tables ^ {table}
        return replace(self, tables=frozenset(tables)) if tables else self

    # ------------------------------------------------------------- arquivo

    def to_dict(self) -> dict[str, Any]:
        return {"operations": list(self.ordered_operations()),
                "tables": list(self.ordered_tables())}


def tables_text(tables: Iterable[int]) -> str:
    """ "2 a 5" para uma sequência, "2, 5, 7" para tabuadas soltas, "todas" para 1 a 10."""
    ordered = sorted(tables)
    if tuple(ordered) == TABLES:
        return "todas"
    if len(ordered) > 2 and ordered == list(range(ordered[0], ordered[-1] + 1)):
        return f"{ordered[0]} a {ordered[-1]}"
    return ", ".join(str(t) for t in ordered)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def settings_from_dict(raw: Any) -> MathSettings:
    """Lê as escolhas salvas; cada campo ruim volta ao padrão sem estragar os outros.
    Aceita também o formato anterior, que tinha um "enabled" separado."""
    if not isinstance(raw, dict):
        return MathSettings()
    raw_ops, raw_tables = raw.get("operations"), raw.get("tables")
    operations = frozenset(op for op in raw_ops if op in OPERATIONS) if isinstance(
        raw_ops, list) else frozenset()
    if raw.get("enabled") is False:
        operations = frozenset()
    tables = frozenset(t for t in raw_tables if _is_int(t) and t in TABLES) if isinstance(
        raw_tables, list) else frozenset()
    return MathSettings(operations=operations, tables=tables or DEFAULT_TABLES)


def settings_from_legacy_level(level: Any) -> MathSettings:
    """Converte o antigo "nível de contas" (0 a 3) dos saves mais antigos."""
    if not _is_int(level):
        return MathSettings()
    if level == 1:
        return MathSettings(frozenset({ADD, SUB}))
    if level == 2:
        return MathSettings(frozenset({ADD, SUB, MUL}), frozenset({2, 3, 4, 5}))
    if level == 3:
        return MathSettings(frozenset(OPERATIONS), frozenset(range(2, 11)))
    return MathSettings()


# ------------------------------------------------------------- perguntas

def _operands(op: str, settings: MathSettings, rng: random.Random) -> tuple[str, int]:
    """Devolve (texto, resposta) de uma conta da operação pedida."""
    if op == ADD:  # a resposta nunca passa de 100
        a = rng.randint(1, MAX_RESULT - 1)
        b = rng.randint(1, MAX_RESULT - a)
        return f"{a} + {b}", a + b
    if op == SUB:  # nunca dá negativo
        a = rng.randint(1, MAX_RESULT)
        b = rng.randint(1, a)
        return f"{a} − {b}", a - b
    # Sorteios sempre sobre tuplas em ordem fixa: iterar um frozenset muda de ordem de
    # uma execução para outra e quebraria a repetição com a mesma semente.
    table, factor = rng.choice(settings.ordered_tables()), rng.choice(FACTORS)
    if op == MUL:
        return f"{table} × {factor}", table * factor
    return f"{table * factor} ÷ {table}", factor


def _choices(answer: int, rng: random.Random) -> tuple[int, ...]:
    """Quatro alternativas: a certa e três erradas próximas dela, em ordem sorteada."""
    pool = sorted({answer + d for d in _OFFSETS if answer + d >= 0})
    options = rng.sample(pool, 3) + [answer]
    rng.shuffle(options)
    return tuple(options)


def make_question(settings: MathSettings, rng: random.Random) -> Question:
    """Sorteia uma conta de acordo com as escolhas."""
    if not settings.enabled:
        raise ValueError("nenhuma conta escolhida")
    op = rng.choice(settings.ordered_operations())
    text, answer = _operands(op, settings, rng)
    return Question(f"{text} = ?", answer, _choices(answer, rng))


def is_correct(question: Question, choice: int) -> bool:
    return choice == question.answer
