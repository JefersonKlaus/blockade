import random

import pytest

from blockwar.mathmode import LEVEL_NAMES, Question, is_correct, make_question


def evaluate(text: str) -> int:
    expression = text.replace(" = ?", "").replace("−", "-").replace("×", "*").replace("÷", "//")
    return eval(expression, {"__builtins__": {}})  # só contas geradas pelo próprio módulo


@pytest.mark.parametrize("level", [1, 2, 3])
def test_questions_are_correct_and_have_four_distinct_nonnegative_choices(level):
    rng = random.Random(level)
    for _ in range(300):
        q = make_question(level, rng)
        assert evaluate(q.text) == q.answer
        assert len(q.choices) == 4 and len(set(q.choices)) == 4
        assert q.answer in q.choices and all(c >= 0 for c in q.choices)


def test_level_one_is_small_and_has_only_add_and_subtract():
    rng = random.Random(3)
    for _ in range(200):
        q = make_question(1, rng)
        assert "×" not in q.text and "÷" not in q.text and q.answer <= 20


def test_division_is_always_exact_at_level_three():
    rng = random.Random(4)
    divisions = [q for q in (make_question(3, rng) for _ in range(300)) if "÷" in q.text]
    assert divisions  # o sorteio de 300 perguntas inclui divisões
    for q in divisions:
        a, b = (int(x) for x in q.text.replace(" = ?", "").split(" ÷ "))
        assert a % b == 0 and a // b == q.answer


def test_same_seed_same_question():
    assert make_question(2, random.Random(9)) == make_question(2, random.Random(9))


def test_invalid_level_and_correctness_check():
    with pytest.raises(ValueError):
        make_question(0, random.Random(1))
    q = Question("2 + 2 = ?", 4, (3, 4, 5, 6))
    assert is_correct(q, 4) and not is_correct(q, 5)
    assert LEVEL_NAMES[0] == "Desligado" and set(LEVEL_NAMES) == {0, 1, 2, 3}
