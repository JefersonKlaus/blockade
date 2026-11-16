# Block War

Turn-based board game built with Python + Flet. Two sides (Blue ● and Orange ▲) place
blocks on a 5×5 or 7×7 board. Whoever squeezes the opponent's blocks in a straight line,
between the new block and another block of their own, turns all of them to their side. The
player with the most blocks when the board is full wins.

## Running the game

```bash
cd guerra_dos_blocos
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
flet run                           # starts the game (uses [tool.flet.app] path = "src")
```

If Flet does not find the app automatically, use `flet run src/main.py`.

Tests and simulation (Flet is not required):

```bash
pytest
python -m blockwar.simulate --games 40 --size 7 --blue dificil --orange facil
```

## Building for Android

Install the project dependencies, then run the build command from the project root:

```bash
flet build apk
```

The generated APK is placed in the `build/apk` directory. To generate an Android App
Bundle for Google Play instead, run:

```bash
flet build aab
```

The Android build may require the Android SDK and Java to be installed and configured in
your environment. Flet can download missing build tools when needed.

## Building for iOS

iOS builds must be performed on macOS with Xcode installed:

```bash
flet build ipa
```

The generated IPA is placed in the `build/ipa` directory. Before distributing the app
through TestFlight or the App Store, configure an Apple Developer team and the required
signing certificates and provisioning profiles in Xcode.

## Rules

- Any empty square is a valid move; capturing is a consequence, not a requirement.
- In each of the 8 directions, a sequence of opponent blocks enclosed by one of your
  blocks is turned to your side.
- Captures do not chain: blocks turned during a move do not capture again during that move.
- Corner blocks can never be squeezed.
- The game ends when the board is full (or one side has no blocks left). The boards have an
  odd number of squares, so a full board cannot result in a tie.

## Playing on screen

1. Tap an empty square: the blocks that would be turned are highlighted in yellow.
2. Tap the same square again to confirm (or tap another square to change the selection).
3. **Hint** highlights a suggested square in green. **Undo** goes back one move (3 per game).

Modes: play against the computer (Easy, Medium, Hard) or play with another person on the
same device.
**Math questions** (Easy, Medium, Hard): after confirming a square, you must answer a
multiple-choice question with 4 options. A wrong answer makes you lose your turn.

## Project structure

| File | Purpose |
|---|---|
| `src/main.py` | Entry point for `flet run` |
| `src/blockwar/models.py` | Players, positions, and errors |
| `src/blockwar/board.py` | Immutable board and capture rules |
| `src/blockwar/game.py` | Game state: turns, undo, and game over |
| `src/blockwar/bot.py` | Three-level computer opponent |
| `src/blockwar/mathmode.py` | Math-mode questions |
| `src/blockwar/controller.py` | Game flow (taps, questions, and device), without Flet |
| `src/blockwar/theme.py` | Square colors and appearance, without Flet |
| `src/blockwar/ui.py` | Flet screens (menu and game) |
| `src/blockwar/storage.py` | Scores and settings stored as JSON |
| `src/blockwar/simulate.py` | Computer-vs-computer simulation for checking balance |

All game rules are kept outside Flet, so they can be tested without opening a window. The
`tests/` directory contains the test suite; `tests/test_ui_wiring.py` uses a fake Flet and
**does not validate the visual appearance**.
