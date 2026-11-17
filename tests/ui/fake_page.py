"""A stand-in for the Flet page, so the screens can be tested without opening a window.

The controls on it are the real Flet controls; only the page (the window) is fake.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class FakePage:
    """Just enough of `ft.Page` for the ui package: a list of controls, update counting and a
    screen size. The default 290 px wide screen fits exactly a 5x5 board, which keeps
    the positions in the tests easy to follow."""

    def __init__(self, width=290, height=None, padding=12):
        self.controls: list[Any] = []
        self.dialogs: list[Any] = []      # open dialogs (the tutorial), like Flet's stack
        self.updates = 0
        self.window = SimpleNamespace()
        self.width, self.height, self.padding = width, height, padding

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None

    def add(self, *controls):
        self.controls.extend(controls)

    def clean(self):
        self.controls.clear()

    def update(self):
        self.updates += 1
