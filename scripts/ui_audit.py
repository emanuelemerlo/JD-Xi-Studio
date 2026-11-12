"""
UI audit: finds interface problems without clicking every control by hand.

    python scripts/ui_audit.py                 # this screen's scale and fonts
    QT_SCALE_FACTOR=1.5 QT_FONT_DPI=120 python scripts/ui_audit.py

It opens JD-Xi Studio (without a JD-Xi: MIDI is faked) and checks
  - navigation: every panel button and every menu entry that opens an editor
    opens the right tab, brings the editors window up and lights the right
    button on the panel (and only that one); how long showing each takes;
  - the keyboard panel: labels and buttons whose text does not fit, controls
    that overlap or stick out of the panel.
Prints one line per problem and exits with 1 when there is any (0 when clean).
tests/test_ui_audit.py runs it at two scales.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("JDXI_LANGUAGE", "en")

import conftest  # noqa: E402  (the fake MIDI ports)
import rtmidi  # noqa: E402

rtmidi.MidiIn = conftest.FakeMidiIn
rtmidi.MidiOut = conftest.FakeMidiOut

from PySide6.QtCore import QRect, QTimer  # noqa: E402
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QSlider, QWidget  # noqa: E402

PANEL_KEYS = {"digital1": "digital1", "digital2": "digital2", "analog": "analog", "drums": "drums", "arp": "arpeggio"}
SLOW_MS = 400  # showing an editor that is already open
SLOW_FIRST_MS = 2500  # building an editor the first time (Program parts, Settings, Recipes...)


def spin(app, n=10):
    for _ in range(n):
        app.processEvents()


def text_of(widget) -> str:
    if isinstance(widget, (QLabel, QAbstractButton)):
        return widget.text().replace("&", "")
    return ""


def audit_navigation(app, window, problems: list[str], timings: dict[str, float]) -> None:
    tabs = window.main_editor.editor_tab_widget

    def check(source: str, key: str) -> None:
        config = window.editor_registry[key]
        widget = tabs.currentWidget()
        if widget is None or type(widget) is not config.editor_class:
            problems.append(f"navigation: {source} opened {type(widget).__name__}, not {config.editor_class.__name__}")
        if not window.main_editor.isVisible():
            problems.append(f"navigation: {source} left the editors window hidden")
        if key in window.PANEL_EDITORS:
            lit = [k for k, b in window.part_buttons.items() if b.isChecked()]
            want = [k for k, v in PANEL_KEYS.items() if v == key]
            if lit != want:
                problems.append(f"panel: after {source} the lit buttons are {lit}, expected {want}")

    built: dict[str, float] = {}

    def timed(source: str, key: str, action) -> None:
        config = window.editor_registry[key]
        exists = any(type(tabs.widget(i)) is config.editor_class for i in range(tabs.count()))
        start = time.perf_counter()
        action()
        spin(app)
        ms = (time.perf_counter() - start) * 1000
        if exists:
            timings[key] = max(timings.get(key, 0.0), ms)
        else:
            built[key] = ms
            if ms > SLOW_FIRST_MS:
                problems.append(f"slow: building the {key} editor took {ms:.0f} ms")
        check(source, key)

    for name, key in PANEL_KEYS.items():
        timed(f"panel button {name}", key, window.part_buttons[name].click)
    timed("panel button Vocoder", "vocal_fx", window.vocal_effects_button.click)
    timed("panel button Effects", "effects", window.effects_button.click)
    # menu entries: those whose text names an editor's tab
    titles = {window.editor_registry[k].title.lower(): k for k in window.editor_registry}
    for top in window.menuBar().actions():
        menu = top.menu()
        if menu is None:
            continue
        for action in menu.actions():
            label = action.text().replace("&", "").replace("…", "").replace("...", "").strip().lower()
            key = titles.get(label)
            if key and action.isEnabled():
                timed(f"menu {top.text().replace('&', '')} > {action.text().replace('&', '')}", key, action.trigger)
    for key, ms in built.items():
        print(f"  building {key}: {ms:.0f} ms (first time)")
    for key, ms in timings.items():
        if ms > SLOW_MS:
            problems.append(f"slow: showing the {key} editor took {ms:.0f} ms")


def audit_panel(window, problems: list[str]) -> None:
    panel = window.panel_container
    area = panel.rect()
    leaves = []
    for widget in panel.findChildren(QWidget):
        if not widget.isVisibleTo(panel) or widget.width() <= 1:
            continue
        if isinstance(widget, (QLabel, QAbstractButton, QSlider)):
            rect = QRect(widget.mapTo(panel, widget.rect().topLeft()), widget.size())
            leaves.append((widget, rect))
            name = text_of(widget) or type(widget).__name__
            if not area.contains(rect, False) and rect.intersected(area) != rect:
                problems.append(f"panel: '{name}' sticks out of the panel ({rect.getRect()})")
            text = text_of(widget)
            if text and "\n" not in text and not (isinstance(widget, QLabel) and widget.wordWrap()):
                need = widget.fontMetrics().horizontalAdvance(text)
                room = widget.contentsRect().width()
                if isinstance(widget, QAbstractButton):
                    room -= 6
                if need > room + 1:
                    problems.append(f"panel: '{text}' does not fit ({need} px of text in {room} px)")
    for i, (a, ra) in enumerate(leaves):
        for b, rb in leaves[i + 1:]:
            if a.isAncestorOf(b) or b.isAncestorOf(a):
                continue
            inter = ra.intersected(rb)
            if inter.width() > 3 and inter.height() > 3 and text_of(a) and text_of(b):
                problems.append(
                    f"panel: '{text_of(a) or type(a).__name__}' overlaps '{text_of(b) or type(b).__name__}'"
                )


def main() -> int:
    app = QApplication.instance() or QApplication([])
    from jdxi_editor.main import load_translations
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    load_translations(app)
    window = JDXiInstrument()
    window.show()
    problems: list[str] = []
    timings: dict[str, float] = {}

    def run():
        try:
            spin(app, 20)
            audit_panel(window, problems)
            audit_navigation(app, window, problems, timings)
        except Exception as ex:  # an error is a problem too
            problems.append(f"error: {type(ex).__name__}: {ex}")
        app.quit()

    QTimer.singleShot(1500, run)
    app.exec()
    scale = os.environ.get("QT_SCALE_FACTOR", "1")
    print(f"UI audit (scale {scale}, font DPI {os.environ.get('QT_FONT_DPI', 'system')}):")
    for key, ms in sorted(timings.items(), key=lambda kv: -kv[1]):
        print(f"  showing {key}: {ms:.0f} ms (slowest)")
    for problem in dict.fromkeys(problems):
        print(f"  PROBLEM {problem}")
    print(f"  {len(set(problems))} problem(s)")
    window.close()
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
