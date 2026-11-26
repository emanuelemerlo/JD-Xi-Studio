#!/usr/bin/env python3
"""
Capture the documentation and README screenshots from the running editor.

Starts the real Instrument window off screen (no JD-Xi needed), opens each
editor tab and saves it with QWidget.grab(), at 2x scale for sharp text.

Usage:
    # Review first: write everything to a folder
    python scripts/capture_screenshots.py --out-dir /tmp/shots

    # Then replace the images used by doc/*.rst and the READMEs
    python scripts/capture_screenshots.py --install

Images (doc/images/ for the Sphinx docs, resources/ for the READMEs, where
"_600"/"_200" copies are the thumbnails linked to the full-size image):
    jdxi-digital-synth1.png  digital_synth.png   (+ _600)
    jdxi-analog-synth.png    analog_synth.png    (+ _600)
    jdxi-drum-kit.png        drum_editor.png     (+ _600)
    (README only)            arpeggiator.png     (+ _600)
    jdxi-effects.png         effects.png         (+ _600)
    jdxi-vocal-effects.png   vocal_effects.png   (+ _600)
    jdxi-pattern-sequencer.png  pattern.png      (+ _600)
    jdxi-midi-editor.png     midi_player.png     (+ _600)
    jdxi-programs.png        programs_page.png   (+ _600)
    midi_config_200.png      midi_config.png     (+ _200)
    keyboard_window.png      keyboard_window.png (+ _900)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCALE = "2"
WINDOW_SIZE = (1400, 780)  # logical pixels of the editor window
MIDI_CONFIG_SIZE = (520, 0)  # width; height from the dialog's content

# editor type -> (doc/images name or None, resources name or None)
EDITOR_SHOTS = {
    "program": ("jdxi-programs.png", "programs_page.png"),
    "digital1": ("jdxi-digital-synth1.png", "digital_synth.png"),
    "analog": ("jdxi-analog-synth.png", "analog_synth.png"),
    "drums": ("jdxi-drum-kit.png", "drum_editor.png"),
    "arpeggio": (None, "arpeggiator.png"),
    "effects": ("jdxi-effects.png", "effects.png"),
    "vocal_fx": ("jdxi-vocal-effects.png", "vocal_effects.png"),
    "pattern": ("jdxi-pattern-sequencer.png", "pattern.png"),
    "midi_player": ("jdxi-midi-editor.png", "midi_player.png"),
}
# README versions that show a different page from the docs' image
README_TABS: dict[str, tuple[str, ...]] = {}
# README versions cropped to the editor's content (left, right fractions of
# the width), so it is larger in the 600 px thumbnail
README_CROP: dict[str, tuple[float, float]] = {}
MIDI_CONFIG_SHOT = ("midi_config_200.png", "midi_config.png")
KEYBOARD_SHOT = "keyboard_window.png"  # doc/images and resources
THUMBNAIL_WIDTHS = {"midi_config.png": 200, KEYBOARD_SHOT: 900}  # others: 600


def _settle(app, ms: int = 400) -> None:
    from PySide6.QtCore import QElapsedTimer

    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < ms:
        app.processEvents()


def select_tab(widget, text: str) -> bool:
    """Show the first tab, at any depth, whose label is text."""
    from PySide6.QtWidgets import QTabBar

    for bar in widget.findChildren(QTabBar):
        if not bar.isVisible():  # e.g. Partial 2's pages while Partial 1 shows
            continue
        for index in range(bar.count()):
            if bar.tabText(index).strip() == text:
                bar.setCurrentIndex(index)
                return True
    return False


def readme_name_for(doc_name: str) -> str:
    return f"readme-{doc_name}"


def demo_midi_file(path: Path) -> Path:
    """A short original song for the MIDI Player's screenshot: drums (ch 10), bass
    (ch 3, Analog), chords (ch 2) and a lead (ch 1), eight bars of 4/4 then four
    of 3/4, so the ruler shows a change of time signature."""
    import mido

    tpb = 480
    bars = [(4, 4)] * 8 + [(3, 4)] * 4
    roots = [45, 41, 48, 43] * 3  # A F C G
    events: dict[int, list] = {ch: [] for ch in (0, 1, 2, 9)}

    def note(ch, start, length, pitch, vel=96):
        events[ch].append((start, mido.Message("note_on", channel=ch, note=pitch, velocity=vel)))
        events[ch].append((start + length, mido.Message("note_off", channel=ch, note=pitch, velocity=0)))

    tick = 0
    melody = [0, 3, 7, 10, 7, 3, 12, 10]
    for bar, ((beats, _), root) in enumerate(zip(bars, roots)):
        for beat in range(beats):
            t = tick + beat * tpb
            note(9, t, tpb // 4, 36 if beat == 0 else (38 if beat % 2 else 36))  # kick / snare
            for half in (0, tpb // 2):
                note(9, t + half, tpb // 8, 42, 70)  # closed hi-hat
            note(2, t, tpb // 2, root - 12 + (7 if beat == 2 else 0))  # bass
            note(0, t + tpb // 2, tpb // 2, root + 24 + melody[(bar * 3 + beat) % len(melody)], 90)
        for interval in (0, 3, 7):
            note(1, tick, beats * tpb - 20, root + 12 + interval, 70)  # chords
        tick += beats * tpb

    song = mido.MidiFile(type=1, ticks_per_beat=tpb)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage("track_name", name="Demo", time=0))
    conductor.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(112), time=0))
    conductor.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    conductor.append(mido.MetaMessage("time_signature", numerator=3, denominator=4, time=8 * 4 * tpb))
    song.tracks.append(conductor)
    names = {0: "Lead", 1: "Chords", 2: "Bass", 9: "Drums"}
    for ch, evs in events.items():
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=names[ch], time=0))
        last = 0
        for t, msg in sorted(evs, key=lambda e: (e[0], e[1].type == "note_on")):
            track.append(msg.copy(time=t - last))
            last = t
        song.tracks.append(track)
    song.save(str(path))
    return path


def capture_name(names: tuple) -> str:
    """The capture's file name: the doc image's, else the README image's."""
    doc_name, readme_name = names
    return doc_name or readme_name


def capture(out_dir: Path) -> list[Path]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["QT_SCALE_FACTOR"] = SCALE
    sys.path.insert(0, str(ROOT))

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    from jdxi_editor.ui.widgets.digital.base import load_lcd_font

    load_lcd_font()

    from jdxi_editor.ui.windows.jdxi import instrument as instrument_module
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    # No JD-Xi: don't block on the MIDI dialog or check for updates
    JDXiInstrument._show_midi_config = lambda self: None
    instrument_module.should_auto_check = lambda *a, **k: False

    window = JDXiInstrument()
    editor_window = window.main_editor
    editor_window.resize(*WINDOW_SIZE)
    editor_window.show()
    _settle(app, 1500)

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for editor_type, names in EDITOR_SHOTS.items():
        doc_name = capture_name(names)
        window.show_editor(editor_type)
        _settle(app)
        if editor_type == "midi_player":
            # a file loaded: tracks, ruler (with its 3/4), the Fit to the JD-Xi parts
            import tempfile

            player = editor_window.editor_tab_widget.currentWidget()
            demo = demo_midi_file(Path(tempfile.mkdtemp()) / "Demo song.mid")
            player.midi_load_file_from_path(str(demo))
            _settle(app, 1200)
        path = out_dir / doc_name
        editor_window.grab().save(str(path))
        written.append(path)
        print(f"captured {editor_type:12} -> {path}")
        tabs = README_TABS.get(editor_type, ())
        crop = README_CROP.get(editor_type)
        if tabs or crop:
            editor = editor_window.editor_tab_widget.currentWidget()
            for tab in tabs:
                if not select_tab(editor, tab):
                    print(f"  tab {tab!r} not found in {editor_type}")
                _settle(app)
            image = editor_window.grab()
            if crop:
                left = round(image.width() * crop[0])
                right = round(image.width() * crop[1])
                image = image.copy(left, 0, right - left, image.height())
            path = out_dir / readme_name_for(doc_name)
            image.save(str(path))
            written.append(path)
            print(f"captured {editor_type + ' README':12} -> {path}")

    from jdxi_editor.ui.windows.midi.config_dialog import MIDIConfigDialog

    dialog = MIDIConfigDialog(window.midi_helper, parent=window)
    dialog.show()
    _settle(app)
    hint = dialog.sizeHint()
    dialog.resize(max(MIDI_CONFIG_SIZE[0], hint.width()), max(hint.height(), dialog.height()))
    _settle(app)
    path = out_dir / MIDI_CONFIG_SHOT[1]
    dialog.grab().save(str(path))
    written.append(path)
    print(f"captured {'midi config':12} -> {path}")
    dialog.close()

    # the keyboard window, with the Off-line badge under MIDI IN / OUT
    window.raise_()
    _settle(app)
    path = out_dir / KEYBOARD_SHOT
    window.grab().save(str(path))
    written.append(path)
    print(f"captured {'keyboard':12} -> {path}")

    window._wait_for_usb_recording_threads()
    return written


def install(shots: Path) -> None:
    """Copy the captures over the images the docs and READMEs use."""
    from PIL import Image

    doc_images = ROOT / "doc" / "images"
    resources = ROOT / "resources"
    for editor_type, (doc_name, readme_name) in EDITOR_SHOTS.items():
        source = shots / capture_name((doc_name, readme_name))
        if doc_name:
            shutil.copyfile(source, doc_images / doc_name)
            print(f"updated doc/images/{doc_name}")
        if readme_name:
            readme_source = shots / readme_name_for(source.name)
            customised = editor_type in README_TABS or editor_type in README_CROP
            if not customised or not readme_source.exists():
                readme_source = source
            _install_readme_image(readme_source, resources, readme_name, Image)
    config_source = shots / MIDI_CONFIG_SHOT[1]
    _install_readme_image(config_source, resources, MIDI_CONFIG_SHOT[1], Image)
    shutil.copyfile(
        resources / MIDI_CONFIG_SHOT[0], doc_images / MIDI_CONFIG_SHOT[0]
    )
    print(f"updated doc/images/{MIDI_CONFIG_SHOT[0]}")
    keyboard = shots / KEYBOARD_SHOT
    if keyboard.exists():
        _install_readme_image(keyboard, resources, KEYBOARD_SHOT, Image)
        # the docs show it at 60 %: the 900 px copy is enough
        shutil.copyfile(resources / "keyboard_window_900.png", doc_images / KEYBOARD_SHOT)
        print(f"updated doc/images/{KEYBOARD_SHOT}")


def _install_readme_image(source: Path, resources: Path, name: str, Image) -> None:
    shutil.copyfile(source, resources / name)
    width = THUMBNAIL_WIDTHS.get(name, 600)
    stem = Path(name).stem
    image = Image.open(source)
    height = round(image.height * width / image.width)
    thumb = image.resize((width, height), Image.LANCZOS)
    thumb.save(resources / f"{stem}_{width}.png", optimize=True)
    print(f"updated resources/{name} and resources/{stem}_{width}.png")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out-dir", type=Path, help="write the captures here")
    parser.add_argument(
        "--install",
        action="store_true",
        help="replace the images in doc/images and resources",
    )
    parser.add_argument(
        "--from-dir",
        type=Path,
        help="with --install: use captures already in this folder",
    )
    args = parser.parse_args(argv)
    if not (args.out_dir or args.install):
        parser.error("give --out-dir and/or --install")

    if args.install and args.from_dir:
        install(args.from_dir)
        return 0
    out_dir = args.out_dir or ROOT / "build" / "screenshots"
    capture(out_dir)
    if args.install:
        install(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
