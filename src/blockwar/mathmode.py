"""Modo "Guerra com contas": para colocar o bloco, é preciso acertar uma conta."""
from __future__ import annotations

import random
from dataclasses import dataclass

LEVEL_NAMES = {0: "Desligado", 1: "Fácil", 2: "Médio", 3: "Difícil"}
_KINDS = {1: ("add", "sub"), 2: ("add", "sub", "mul"), 3: ("add", "sub", "mul", "div")}
_OFFSETS = (-10, -5, -3, -2, -1, 1, 2, 3, 5, 10)


@dataclass(frozen=True)
class Question:
    text: str
    answer: int
    choices: tuple[int, ...]


def _operands(kind: str, level: int, rng: random.Random) -> tuple[str, int]:
    """Devolve (texto, resposta) de uma conta do tipo e nível pedidos."""
    if kind == "add":
        low, high = {1: (1, 10), 2: (10, 60), 3: (50, 150)}[level]
        a, b = rng.randint(low, high), rng.randint(max(1, low // 2), high // 2 + 5)
        return f"{a} + {b}", a + b
    if kind == "sub":
        low, high = {1: (1, 12), 2: (10, 90), 3: (50, 200)}[level]
        a, b = sorted((rng.randint(low, high), rng.randint(1, high // 2)), reverse=True)
        return f"{a} − {b}", a - b
    if kind == "mul":
        a = rng.randint(2, 5) if level == 2 else rng.randint(3, 10)
        b = rng.randint(2, 9) if level == 2 else rng.randint(3, 10)
        return f"{a} × {b}", a * b
    divisor, result = rng.randint(2, 9), rng.randint(2, 10)
    return f"{divisor * result} ÷ {divisor}", result


def _choices(answer: int, rng: random.Random) -> tuple[int, ...]:
    """Quatro alternativas: a certa e três erradas próximas dela, em ordem sorteada."""
    pool = sorted({answer + d for d in _OFFSETS if answer + d >= 0 and answer + d != answer})
    options = rng.sample(pool, 3) + [answer]
    rng.shuffle(options)
    return tuple(options)


def make_question(level: int, rng: random.Random) -> Question:
    """Sorteia uma conta do nível 1 (fácil), 2 (médio) ou 3 (difícil)."""
    if level not in _KINDS:
        raise ValueError("nível de contas deve ser 1, 2 ou 3")
    text, answer = _operands(rng.choice(_KINDS[level]), level, rng)
    return Question(f"{text} = ?", answer, _choices(answer, rng))


def is_correct(question: Question, choice: int) -> bool:
    return choice == question.answer
