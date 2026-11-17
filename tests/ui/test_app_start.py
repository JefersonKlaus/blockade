"""main(): the window, the pastel background and the portrait lock on phones."""
from __future__ import annotations

from types import SimpleNamespace

from blockwar import theme

from fake_page import FakePage
from ui_actions import run


class MobilePage(FakePage):
    """A page on a phone/tablet (or a computer) that records orientation requests."""

    def __init__(self, mobile=True, fails=False):
        super().__init__()
        self.platform = SimpleNamespace(is_mobile=lambda: mobile)
        self.orientations, self.fails = [], fails

    async def set_allowed_device_orientations(self, orientations):
        if self.fails:
            raise RuntimeError("not supported here")
        self.orientations.append(list(orientations))


def test_main_sets_the_window_and_shows_the_menu(ui):
    page = FakePage()
    run(ui.main(page))
    assert page.title == "Blockade" and (page.window.width, page.window.height) == (430, 900)
    assert page.padding == 12 and page.bgcolor == theme.PAGE_BG and page.theme is not None
    assert len(page.controls) == 1 and callable(page.on_resize)


def test_main_survives_pages_without_a_resizable_window(ui):
    """On the web and on phones the window cannot be resized; main() must not crash."""
    class LockedWindow:
        def __setattr__(self, name, value):
            raise RuntimeError("window is not configurable here")

    page = FakePage()
    page.window = LockedWindow()
    run(ui.main(page))
    assert len(page.controls) == 1


def test_phones_and_tablets_are_locked_in_portrait_but_not_computers(ui):
    phone, computer, browser = MobilePage(), MobilePage(mobile=False), MobilePage(fails=True)
    for page in (phone, computer, browser):     # browser: e.g. opened in the phone's browser
        run(ui.main(page))
        assert len(page.controls) == 1          # the menu shows up in every case
    assert phone.orientations == [[ui.app.ft.DeviceOrientation.PORTRAIT_UP]]
    assert computer.orientations == []
