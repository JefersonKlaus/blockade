import random

import pytest

from blockwar.mathmode import (ADD, DIV, MAX_RESULT, MUL, OPERATIONS, SUB, TABLES,
                               MathSettings, Question, is_correct, make_question,
                               settings_from_dict, settings_from_legacy_level, tables_text)

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

@pytest.mark.parametrize("ops", [(ADD,), (SUB,), (MUL,), (DIV,), (ADD, SUB), OPERATIONS])
@pytest.mark.parametrize("seed", [1, 2])
def test_questions_are_correct_and_have_four_distinct_nonnegative_choices(ops, seed):
    for q in sample(settings(ops, TABLES), 300, seed=seed):
        assert q.text.endswith(" = ?")
        assert evaluate(q.text) == q.answer
        assert len(q.choices) == 4 and len(set(q.choices)) == 4
        assert q.answer in q.choices and all(c >= 0 for c in q.choices)
        assert all(abs(c - q.answer) <= 10 for c in q.choices)  # plausible distractors


@pytest.mark.parametrize("ops", [(ADD,), (MUL, DIV), (ADD, SUB, MUL), OPERATIONS])
def test_only_the_chosen_operations_are_asked(ops):
    assert {parts(q)[1] for q in sample(settings(ops))} == set(ops)


def test_the_right_answer_is_not_always_in_the_same_place():
    positions = {q.choices.index(q.answer) for q in sample(settings(), 100)}
    assert positions == {0, 1, 2, 3}


def test_same_seed_same_question():
    math = settings()
    assert sample(math, 20, seed=9) == sample(math, 20, seed=9)


def test_questions_need_at_least_one_operation():
    with pytest.raises(ValueError):
        make_question(MathSettings(), random.Random(1))


def test_correctness_check():
    q = Question("2 + 2 = ?", 4, (3, 4, 5, 6))
    assert is_correct(q, 4) and not is_correct(q, 5)


# ---------------------------------------------------------------- results up to 100

@pytest.mark.parametrize("ops", [(ADD,), (SUB,), (MUL,), (DIV,), OPERATIONS])
def test_no_number_in_a_question_goes_above_100(ops):
    """The max result is 100: e.g. 99 + 1 or 10 × 10."""
    for q in sample(settings(ops, TABLES), 600):
        first, _, second = parts(q)
        assert 0 <= q.answer <= MAX_RESULT == 100
        assert first <= 100 and second <= 100


def test_addition_uses_the_whole_range_up_to_100():
    answers = [q.answer for q in sample(settings([ADD]), 600)]
    assert max(answers) == 100 and min(answers) < 20


def test_subtraction_never_goes_negative():
    for q in sample(settings([SUB]), 600):
        first, _, second = parts(q)
        assert 1 <= second <= first <= 100 and q.answer >= 0


def test_10_times_10_is_the_biggest_multiplication():
    answers = {q.answer for q in sample(settings([MUL], TABLES), 2000)}
    assert max(answers) == 100


# ---------------------------------------------------------------- tabuadas

@pytest.mark.parametrize("tables", [(2,), (7,), (3, 9), (1, 10), TABLES])
def test_multiplication_uses_only_the_chosen_tables(tables):
    seen = set()
    for q in sample(settings([MUL], tables=tables)):
        table, _, factor = parts(q)
        assert table in tables and 1 <= factor <= 10
        seen.add(table)
    assert seen == set(tables)


@pytest.mark.parametrize("tables", [(2,), (5, 6), TABLES])
def test_division_is_exact_and_uses_only_the_chosen_tables(tables):
    for q in sample(settings([DIV], tables=tables)):
        dividend, _, divisor = parts(q)
        assert divisor in tables
        assert dividend % divisor == 0 and dividend // divisor == q.answer
        assert 1 <= q.answer <= 10


def test_tables_only_affect_multiplication_and_division():
    mixed = sample(settings([ADD, MUL], tables=(9,)))
    assert all(parts(q)[0] == 9 for q in mixed if parts(q)[1] == MUL)
    assert len({parts(q)[0] for q in mixed if parts(q)[1] == ADD}) > 10


# ---------------------------------------------------------------- settings

def test_default_settings_have_no_math():
    math = MathSettings()
    assert not math.enabled and math.operations == set() and math.tables == {2, 3, 4, 5}


def test_math_is_on_when_any_operation_is_chosen():
    for op in OPERATIONS:
        assert MathSettings().toggled_operation(op).enabled


def test_uses_tables_only_with_multiplication_or_division():
    assert not settings([ADD, SUB]).uses_tables
    assert settings([MUL]).uses_tables and settings([DIV]).uses_tables


def test_turning_off_every_operation_turns_math_off():
    math = settings([ADD]).toggled_operation(ADD)
    assert not math.enabled and math.summary() == "Desligado"
    with pytest.raises(ValueError):
        math.toggled_operation("pow")


def test_toggling_tables_keeps_at_least_one():
    math = settings([MUL], tables=(3,))
    assert math.toggled_table(7).tables == {3, 7}
    assert math.toggled_table(3) == math
    for bad in (0, 11):
        with pytest.raises(ValueError):
            math.toggled_table(bad)


@pytest.mark.parametrize("math, symbols, text", [
    (MathSettings(), "", "Desligado"),
    (settings([ADD, SUB]), "+ −", "+ −"),
    (settings([MUL], (7,)), "×", "× · tabuada 7"),
    (settings([DIV, MUL], (2, 3, 4, 5)), "× ÷", "× ÷ · tabuadas 2 a 5"),
    (settings(OPERATIONS, TABLES), "+ − × ÷", "+ − × ÷ · tabuadas todas"),
    (settings([ADD, DIV], (2, 5, 9)), "+ ÷", "+ ÷ · tabuadas 2, 5, 9"),
])
def test_symbols_and_summary(math, symbols, text):
    assert math.symbols() == symbols and math.summary() == text


@pytest.mark.parametrize("tables, text", [
    ((4,), "4"), ((2, 3), "2, 3"), ((2, 3, 4), "2 a 4"), ((1, 3, 5), "1, 3, 5"),
    (TABLES, "todas")])
def test_tables_text(tables, text):
    assert tables_text(tables) == text


# ---------------------------------------------------------------- saving

@pytest.mark.parametrize("math", [
    MathSettings(), settings(), settings([MUL], (7,)), settings(OPERATIONS, TABLES)])
def test_settings_roundtrip_through_a_dict(math):
    assert settings_from_dict(math.to_dict()) == math


def test_settings_dict_is_stable_json():
    assert settings([DIV, ADD], (5, 2)).to_dict() == {
        "operations": ["add", "div"], "tables": [2, 5]}


@pytest.mark.parametrize("raw", [None, [], "x", 3, {}])
def test_bad_saved_settings_fall_back_to_defaults(raw):
    assert settings_from_dict(raw) == MathSettings()


def test_bad_saved_fields_are_fixed_one_by_one():
    math = settings_from_dict({"operations": ["add", "pow", 3],
                               "tables": [2, 11, True, "5", 7]})
    assert math == MathSettings(frozenset({ADD}), frozenset({2, 7}))
    assert settings_from_dict({"operations": ["mul"], "tables": []}).tables == {2, 3, 4, 5}


def test_the_previous_format_with_an_enabled_flag_is_read():
    old_off = {"enabled": False, "max_number": 20, "operations": ["add"], "tables": [3]}
    assert settings_from_dict(old_off) == MathSettings(tables=frozenset({3}))
    old_on = {"enabled": True, "max_number": 20, "operations": ["add", "mul"], "tables": [3]}
    assert settings_from_dict(old_on) == settings([ADD, MUL], (3,))


@pytest.mark.parametrize("level, expected", [
    (0, MathSettings()),
    (1, MathSettings(frozenset({ADD, SUB}))),
    (2, MathSettings(frozenset({ADD, SUB, MUL}), frozenset({2, 3, 4, 5}))),
    (3, MathSettings(frozenset(OPERATIONS), frozenset(range(2, 11)))),
    (None, MathSettings()), (True, MathSettings()), (7, MathSettings()),
])
def test_old_saved_math_levels_are_converted(level, expected):
    assert settings_from_legacy_level(level) == expected
