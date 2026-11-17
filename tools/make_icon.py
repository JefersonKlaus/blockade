"""Draws the Blockade app icon: src/assets/icon.png (1024×1024, transparent background).

The same file is used
  - by `flet build` as the launcher icon on Android, iOS, web and desktop (Flet adds the
    platform margins and, where transparency is not allowed, the `icon_background` colour
    from pyproject.toml), and
  - by the app itself, above the name at the top of the menu.

Run it again after changing the colours in theme.py:

    python tools/make_icon.py            (needs Pillow: pip install -e ".[dev]")
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from blockwar import theme  # noqa: E402  (needs the path above)

SIZE = 1024
SCALE = 4                      # draw 4× bigger, then shrink: smooth edges
OUT = ROOT / "src" / "assets" / "icon.png"

# Three rows of blocks: blue ● and orange ▲ in an X, like a board mid-game.
PATTERN = ("BOB",
           "OBO",
           "BOB")


def hex_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def draw() -> Image.Image:
    s = SIZE * SCALE
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)

    # Just the 3×3 blocks, filling the canvas (no board frame around them). The gaps
    # stay transparent: Flet puts the icon background colour behind them where needed.
    margin, gap = 0, s * 0.045
    cell = (s - 2 * margin - 2 * gap) / 3
    for r, row in enumerate(PATTERN):
        for c, owner in enumerate(row):
            x0, y0 = margin + c * (cell + gap), margin + r * (cell + gap)
            x1, y1 = x0 + cell, y0 + cell
            blue = owner == "B"
            pen.rounded_rectangle((x0, y0, x1, y1), radius=int(cell * 0.18),
                                  fill=hex_rgb(theme.BLUE if blue else theme.ORANGE))
            cx, cy, r_sym = (x0 + x1) / 2, (y0 + y1) / 2, cell * 0.28
            ink = hex_rgb(theme.BLUE_INK if blue else theme.ORANGE_INK)
            if blue:     # ●
                pen.ellipse((cx - r_sym, cy - r_sym, cx + r_sym, cy + r_sym), fill=ink)
            else:        # ▲
                pen.polygon([(cx, cy - r_sym * 1.1), (cx + r_sym * 1.1, cy + r_sym * 0.8),
                             (cx - r_sym * 1.1, cy + r_sym * 0.8)], fill=ink)
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw().save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
