"""Finding things on the screen: texts, buttons, dialogs, the game controls.

Tests find controls by their text instead of by their position in the tree, so they
keep working when the layout changes (e.g. wrapping a column in a container).
"""
from __future__ import annotations

import re
from typing import Any, Iterator

from blockwar import theme


def label(control) -> str | None:
    """The visible text of a Text (`value`) or a button (`content`)."""
    for attr in ("value", "content"):
        value = getattr(control, attr, None)
        if isinstance(value, str):
            return value
    return None


def walk(control) -> Iterator[Any]:
    """Every control in the tree below (and including) `control`, in screen order (a
    dialog's title, then its content, then its action buttons)."""
    yield control
    for attr in ("title", "content"):
        child = getattr(control, attr, None)
        if child is not None and not isinstance(child, (str, int, float)):
            yield from walk(child)
    for attr in ("controls", "actions"):
        for child in getattr(control, attr, None) or []:
            yield from walk(child)


def visible(control) -> Iterator[Any]:
    """Like `walk`, but skips hidden controls and everything inside them."""
    if getattr(control, "visible", True) is False:
        return
    yield control
    for attr in ("title", "content"):
        child = getattr(control, attr, None)
        if child is not None and not isinstance(child, (str, int, float)):
            yield from visible(child)
    for attr in ("controls", "actions"):
        for child in getattr(control, attr, None) or []:
            yield from visible(child)


def screen(app) -> list[Any]:
    """Everything on the page, plus any open dialog (drawn on top of the page)."""
    return [c for root in [*app.page.controls, *app.page.dialogs] for c in walk(root)]


def dialog(app):
    assert len(app.page.dialogs) == 1, "expected exactly one open dialog"
    return app.page.dialogs[0]


def dialog_texts(app) -> list[str]:
    return [text for c in walk(dialog(app)) if (text := label(c))]


def texts(app) -> list[str]:
    return [text for c in screen(app) if (text := label(c))]


def shows(control, text: str) -> bool:
    """Whether `text` labels `control` itself (a button) or one of its children (a menu
    card, where the icon and the word are two separate `Text` controls inside it)."""
    return any(label(c) == text for c in walk(control))


def clickable(app, text: str):
    """The single clickable control showing `text`, directly or in a child control."""
    found = [c for c in screen(app) if getattr(c, "on_click", None) and shows(c, text)]
    assert len(found) == 1, f"expected one {text!r} button, found {len(found)}"
    return found[0]


def option(app, section: str, text: str):
    """The button `text` inside the menu section titled `section` (some labels, like
    "Difícil", exist in more than one section)."""
    for container in screen(app):
        children = getattr(container, "controls", None) or []
        if any(label(child) == section for child in children):
            found = [c for c in walk(container)
                     if getattr(c, "on_click", None) and shows(c, text)]
            assert len(found) == 1, f"expected one {text!r} in {section!r}"
            return found[0]
    raise AssertionError(f"menu section {section!r} not found")


def is_highlighted(control) -> bool:
    """Whether a card or button is shown as chosen: chosen cards get a border (see
    `theme.card_look` / `theme.level_look`); the math button turns blue when on."""
    return (getattr(control, "border", None) is not None
            or getattr(control, "bgcolor", None) == theme.CARD_SELECTED)


def buttons_in_order(app) -> list[str]:
    return [label(c) or next((label(d) for d in walk(c) if label(d)), "")
            for c in screen(app) if getattr(c, "on_click", None)]


def visible_buttons(app, text: str) -> list:
    return [c for root in app.page.controls for c in visible(root)
            if label(c) == text and getattr(c, "on_click", None)]


def root(app):
    """The layout of the current screen: inside the SafeArea that keeps it clear of the
    phone's status bar, and inside the Container that centers it."""
    assert len(app.page.controls) == 1
    return app.page.controls[0].content.content


def centered_group(app):
    """The choices of a menu screen: centered in the space between the top and Play."""
    group = root(app).controls[-2]
    assert group.expand is True
    assert str(group.alignment).endswith("CENTER")
    return group


def play_slot(app):
    """The bottom part of a menu screen: only the Play button, near the fingers."""
    slot = root(app).controls[-1]
    assert label(slot.content) == "Jogar!"
    return slot


def view(app):
    """The controls of the game on screen (board, scores, buttons...)."""
    return app.game.view


def painted(app) -> int:
    return sum(1 for row in view(app).cells for cell in row if cell.bgcolor != theme.EMPTY)


def on_screen(app) -> str:
    """Which screen is showing: "game", "math" (the math page) or "menu"."""
    if app.game is not None:
        return "game"
    return "math" if app.texts.back in texts(app) else "menu"


MATH_BUTTON = "Praticar matemática"


def math_button(app):
    """The menu's button to the math page, in the app's language."""
    found = [c for c in screen(app) if label(c) == app.texts.math_title
             and getattr(c, "on_click", None)]
    assert len(found) == 1
    return found[0]


def symbol(app, sign: str):
    """The big card of one operation on the math page (+ − × ÷)."""
    return clickable(app, sign)


# Anything that is a picture rather than a letter, digit, sign or game symbol (● ▲ ⬇).
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")
