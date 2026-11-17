import random

import pytest

from blockwar.mathmode import (ADD, DIV, MAX_RESULT, MUL, OPERATIONS, SUB, TABLES,
                               MathSettings, Question, make_question)

SYMBOLS = {"+": ADD, "−": SUB, "×": MUL, "÷": DIV}


def settings(ops=OPERATIONS, tables=(2, 3, 4, 5)) -> MathSettings:
    return MathSettings(frozenset(ops), frozenset(tables))


def evaluate(text: str) -> int:
    expression = text.replace(" = ?", "").replace("−", "-").replace("×", "*").replace("÷", "//")
    return eval(expression, {"__builtins__": {}})  # only questions built by the module itself


def parts(question: Question) -> tuple[int, str, int]:
    """ "12 ÷ 3 = ?" -> (12, DIV, 3)"""
    left, symbol, right = question.text.replace(" = ?", "").split(" ")
    return int(left), SYMBOLS[symbol], int(right)


def sample(math: MathSettings, count: int = 400, seed: int = 0) -> list[Question]:
    rng = random.Random(seed)
    return [make_question(math, rng) for _ in range(count)]


# ---------------------------------------------------------------- every question

def test_questions_are_correct_and_have_four_distinct_nonnegative_choices():
    for q in sample(settings(OPERATIONS, TABLES), 1200):
        assert q.text.endswith(" = ?")
        assert evaluate(q.text) == q.answer
        assert len(q.choices) == 4 and len(set(q.choices)) == 4
        assert q.answer in q.choices and all(c >= 0 for c in q.choices)
        assert all(abs(c - q.answer) <= 10 for c in q.choices)  # plausible distractors


def test_only_the_chosen_operations_are_asked():
    for ops in [(ADD,), (SUB,), (MUL, DIV), (ADD, SUB, MUL), OPERATIONS]:
        assert {parts(q)[1] for q in sample(settings(ops))} == set(ops)


def test_the_right_answer_is_not_always_in_the_same_place():
    positions = {q.choices.index(q.answer) for q in sample(settings(), 100)}
    assert positions == {0, 1, 2, 3}


# ---------------------------------------------------------------- results up to 100

def test_results_go_from_0_up_to_100_and_never_beyond():
    """The max result is 100: e.g. 99 + 1 or 10 × 10; subtraction never goes negative."""
    for op in OPERATIONS:
        answers = set()
        for q in sample(settings([op], TABLES), 2000):
            first, _, second = parts(q)
            assert 0 <= q.answer <= MAX_RESULT == 100
            assert first <= 100 and second <= 100
            answers.add(q.answer)
        if op in (ADD, MUL):
            assert max(answers) == 100                      # 99 + 1, 10 × 10 do come up


# ---------------------------------------------------------------- times tables

def test_times_and_division_use_only_the_chosen_tables_and_divide_exactly():
    for tables in [(7,), (3, 9), TABLES]:
        seen = set()
        for q in sample(settings([MUL], tables=tables)):
            table, _, factor = parts(q)
            assert table in tables and 1 <= factor <= 10
            seen.add(table)
        assert seen == set(tables)
        for q in sample(settings([DIV], tables=tables)):
            dividend, _, divisor = parts(q)
            assert divisor in tables and dividend // divisor == q.answer
            assert dividend % divisor == 0 and 1 <= q.answer <= 10


# ---------------------------------------------------------------- settings

def test_toggling_tables_keeps_at_least_one():
    math = settings([MUL], tables=(3,))
    assert math.toggled_table(7).tables == {3, 7}
    assert math.toggled_table(3) == math
    for bad in (0, 11):
        with pytest.raises(ValueError):
            math.toggled_table(bad)
