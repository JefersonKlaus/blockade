"""The on-screen texts in English and Portuguese, and how the language is chosen."""
import dataclasses
import string

from blockwar.bot import Level
from blockwar.models import Player
from blockwar.texts import ENGLISH, PORTUGUESE, Texts, texts_for


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_both_languages_have_every_text_with_the_same_blanks():
    """A translation must exist and keep every {placeholder}, or the game would crash
    (or show a raw "{name}") in one language only."""
    for field in dataclasses.fields(Texts):
        english, portuguese = getattr(ENGLISH, field.name), getattr(PORTUGUESE, field.name)
        assert english.strip() and portuguese.strip(), field.name
        assert placeholders(english) == placeholders(portuguese), field.name


def test_names_and_counts():
    assert [ENGLISH.player(p) for p in Player] == ["Blue", "Orange"]
    assert [PORTUGUESE.player(p) for p in Player] == ["Azul", "Laranja"]
    assert [ENGLISH.level(level) for level in Level] == ["Easy", "Medium", "Hard"]
    assert [PORTUGUESE.level(level) for level in Level] == ["Fácil", "Médio", "Difícil"]
    assert [ENGLISH.blocks(n) for n in (0, 1, 2)] == ["0 blocks", "1 block", "2 blocks"]
    assert [PORTUGUESE.blocks(n) for n in (0, 1, 2)] == ["0 blocos", "1 bloco", "2 blocos"]


def test_portuguese_only_for_a_device_in_portuguese():
    for code in ("pt", "pt-BR", "pt_PT", "PT"):
        assert texts_for(code) is PORTUGUESE, code
    for code in ("en", "en-US", "es", "fr", "", None, "und"):
        assert texts_for(code) is ENGLISH, code
