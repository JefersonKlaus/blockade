"""The Flet screens: the only package that imports Flet. All game rules live outside it.

  app.py          opens the window and switches screens (menu, math page, game)
  menu.py         the choice screens: the menu and the math page ("Practice math")
  game_screen.py  one game on screen: taps, animation, the phone's turn, the record
  game_view.py    the game's controls (builds and paints them)
  tutorial.py     the "How to play" window
  widgets.py      shared pieces: pastel buttons and cards, switching screens

The words on screen come from texts.py: English by default, Portuguese when the device is
in Portuguese.
"""
from .app import BlocksApp, main

__all__ = ["BlocksApp", "main"]
