"""Guards the configuration that `flet run` and `flet build` depend on.

If one of these fails, `flet run` (from the project folder) or the Android/iOS build
will probably break too, even though all the game tests still pass.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

import blockwar

tomllib = pytest.importorskip("tomllib", reason="tomllib needs Python 3.11+")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def flet_entry_script(pyproject: dict) -> Path:
    """Where `flet run` (with no arguments, from the project folder) looks for the app:
    <project>/<tool.flet.app.path>/<tool.flet.app.module>.py"""
    app = pyproject["tool"]["flet"]["app"]
    return ROOT / app.get("path", ".") / f"{app.get('module', 'main')}.py"


def test_flet_run_finds_the_entry_script(pyproject):
    script = flet_entry_script(pyproject)
    assert script == ROOT / "src" / "main.py"
    assert script.is_file()


def test_the_game_package_sits_next_to_the_entry_script(pyproject):
    """`flet build` packages only the app folder, so the game code must live there."""
    app_dir = flet_entry_script(pyproject).parent
    assert (app_dir / "blockwar" / "__init__.py").is_file()
    assert (app_dir / "blockwar" / "ui" / "__init__.py").is_file()


def test_flet_build_metadata_is_present(pyproject):
    flet = pyproject["tool"]["flet"]
    assert flet["org"] and "." in flet["org"]      # reverse domain, part of the bundle id
    assert flet["product"] == blockwar.APP_NAME == "Blockade"  # name shown on the phone
    assert pyproject["project"]["name"]


def test_runtime_dependencies_are_only_what_the_phone_needs(pyproject):
    """`flet build` installs `project.dependencies` into the Android/iOS app. Dev tools
    (pytest, the Flet CLI/desktop extras...) must stay in the `dev` extra."""
    deps = pyproject["project"]["dependencies"]
    assert any(dep.replace(" ", "").startswith("flet>=") for dep in deps)
    assert not any("pytest" in dep or "[" in dep for dep in deps)
    dev = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("flet[all]") for dep in dev)
    assert any(dep.startswith("pytest") for dep in dev)


def test_version_matches_the_package(pyproject):
    assert pyproject["project"]["version"] == blockwar.__version__


def test_the_game_logic_does_not_import_flet():
    """Only the ui package may import Flet; everything else must be testable without it."""
    package = ROOT / "src" / "blockwar"
    for module in package.rglob("*.py"):
        if module.parent == package / "ui":
            continue
        source = module.read_text(encoding="utf-8")
        assert "import flet" not in source and "from flet" not in source, module.name


def test_main_script_starts_the_flet_app_with_the_ui_entry_point(monkeypatch):
    """Runs src/main.py exactly like `flet run` does, but with `ft.run` replaced."""
    flet = pytest.importorskip("flet", reason="real Flet is not installed")
    calls = []
    monkeypatch.setattr(flet, "run", lambda target, *a, **kw: calls.append(target))
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    for name in [m for m in sys.modules if m.startswith("blockwar.ui")]:
        monkeypatch.delitem(sys.modules, name)
    runpy.run_path(str(ROOT / "src" / "main.py"), run_name="__main__")
    assert len(calls) == 1
    target = calls[0]
    assert target.__module__ == "blockwar.ui.app" and target.__name__ == "main"


def test_ipads_are_allowed_to_stay_in_portrait(pyproject):
    """iPad ignores the runtime portrait lock unless the app requires full screen."""
    assert pyproject["tool"]["flet"]["ios"]["info"]["UIRequiresFullScreen"] is True


# ---------------------------------------------------------------- app icon

ICON = ROOT / "src" / "assets" / "icon.png"


def test_the_app_icon_is_where_flet_build_and_the_app_look_for_it(pyproject):
    """`flet build` takes <app path>/assets/icon.png as the launcher icon; the menu
    shows the same file (ui/menu.py ICON) above the app name."""
    assert ICON.parent == ROOT / pyproject["tool"]["flet"]["app"]["path"] / "assets"
    assert ICON.is_file()
    source = (ROOT / "src" / "blockwar" / "ui" / "menu.py").read_text(encoding="utf-8")
    assert 'ICON = "icon.png"' in source


def test_the_app_icon_is_a_big_square_png_with_a_transparent_background():
    """Flet expects a transparent icon.png and adds each platform's margins/background.
    1024 px is what the App Store asks for."""
    with ICON.open("rb") as file:
        header = file.read(33)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
    color_type = header[25]
    assert (width, height) == (1024, 1024)
    assert color_type == 6                      # RGBA: has an alpha channel


def test_the_icon_corners_are_transparent_and_the_middle_is_not():
    image_module = pytest.importorskip("PIL.Image", reason="Pillow is not installed")
    with image_module.open(ICON) as image:
        assert image.mode == "RGBA"
        for corner in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            assert image.getpixel(corner)[3] == 0
        assert image.getpixel((512, 512))[3] == 255


def test_icon_and_launch_backgrounds_are_the_app_page_color(pyproject):
    from blockwar import theme
    for key in [
        "icon_background", "android.adaptive_icon_background",
        # launch screen (splash), in light and dark mode: never white or near-black
        "splash.color", "splash.dark_color", "splash.icon_background",
        "splash.icon_dark_background",
        # boot screen, shown after the splash while Python starts
        "boot_screen.flet.bgcolor_light", "boot_screen.flet.bgcolor_dark",
    ]:
        value = pyproject["tool"]["flet"]
        for part in key.split("."):
            value = value[part]
        assert value == theme.PAGE_BG, key


def test_the_icon_script_recreates_the_same_icon(tmp_path, monkeypatch):
    """tools/make_icon.py is the source of the icon: running it must give this file."""
    pytest.importorskip("PIL", reason="Pillow is not installed")
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_icon", ROOT / "tools" / "make_icon.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from PIL import ImageChops
    with module.draw() as fresh, __import__("PIL.Image").Image.open(ICON) as saved:
        assert ImageChops.difference(fresh, saved.convert("RGBA")).getbbox() is None
