"""
.msz (Music Bundle) save and load round trip (no MIDI hardware).

- the editors' blocks are saved in raw MIDI values, each with its DT1
- the MIDI file of the player goes in the bundle
- the DT1 saved for a block, received by a new editor, shows the same values
"""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock

from mido import Message, MetaMessage, MidiFile
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.midi.sysex.patch_values import SYSEX, VALUE_FORMAT, VALUE_FORMAT_MIDI
from jdxi_editor.ui.editors.midi_player.editor import MidiFilePlayer
from jdxi_editor.ui.v2.analog import AnalogToneEditor
from jdxi_editor.ui.v2.drums import DrumKitEditor
from jdxi_editor.ui.windows.patch.manager import PatchManager

_APP = QApplication.instance() or QApplication([])
HEADER_KEYS = {"JD_XI_HEADER", "ADDRESS", "TEMPORARY_AREA", "SYNTH_TONE", "TONE_NAME", SYSEX, VALUE_FORMAT}


def _editor_values(editor) -> dict:
    return {(block.key, spec.name): editor.values[spec].value() for block in editor.blocks for spec in block.params}


def _set_values(editor, count: int = 5) -> dict:
    """Set *count* parameters of every block to a value off their default."""
    changed = {}
    for block in editor.blocks:
        specs = [s for s in block.params if not s.name.startswith("TONE_NAME") and s.hi > s.lo][:count]
        values = {s.name: (s.lo + s.hi + 1) // 2 for s in specs}
        editor.apply_values(block, values)
        changed.update({(block.key, name): value for name, value in values.items()})
    return changed


class TestMSZRoundTrip(unittest.TestCase):
    def setUp(self):
        self.helper = MidiIOHelper()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.msz = self.temp_dir / "test_round_trip.msz"
        self.song = self.temp_dir / "test_song.mid"
        self._editors = []
        midi = MidiFile(ticks_per_beat=480)
        track = midi.add_track("Test Track")
        track.append(MetaMessage("set_tempo", tempo=500000, time=0))
        for note in (60, 64):
            track.append(Message("note_on", channel=0, note=note, velocity=100, time=0))
            track.append(Message("note_off", channel=0, note=note, velocity=0, time=480))
        midi.save(str(self.song))

    def tearDown(self):
        for editor in self._editors:
            editor.close()
            editor.deleteLater()
        QApplication.processEvents()

    def _editor(self, cls):
        editor = cls(self.helper, Mock())
        self._editors.append(editor)
        return editor

    def _save(self, editors, with_song: bool) -> zipfile.ZipFile:
        player = Mock(spec=MidiFilePlayer)
        player.midi_state = Mock()
        player.midi_state.file = MidiFile(str(self.song)) if with_song else None
        parent = QWidget()
        parent.get_existing_editor = lambda cls: player if cls == MidiFilePlayer else None
        manager = PatchManager(midi_helper=self.helper, parent=None, save_mode=True, editors=editors)
        manager.parent = parent
        manager.path_input.setText(str(self.msz))
        manager._handle_action()
        self.assertTrue(self.msz.exists(), ".msz file was not created")
        return zipfile.ZipFile(self.msz)

    @staticmethod
    def _sections(bundle: zipfile.ZipFile) -> dict:
        return {
            name: json.loads(bundle.read(name))
            for name in bundle.namelist()
            if name.endswith(".json")
        }

    def test_msz_round_trip_analog_synth(self):
        editor = self._editor(AnalogToneEditor)
        changed = _set_values(editor)
        with self._save([editor], with_song=False) as bundle:
            sections = self._sections(bundle)
        self.assertIn("jdxi_tone_data_19420000.json", sections)
        section = sections["jdxi_tone_data_19420000.json"]
        self.assertEqual(section[VALUE_FORMAT], VALUE_FORMAT_MIDI)
        for (_, name), value in changed.items():
            self.assertEqual(section[name], value, name)

        loaded = self._editor(AnalogToneEditor)
        loaded.receive_dt1(bytes.fromhex(section[SYSEX]))
        self.assertEqual(_editor_values(loaded), _editor_values(editor))

    def test_msz_round_trip_with_midi_file(self):
        analog, drums = self._editor(AnalogToneEditor), self._editor(DrumKitEditor)
        _set_values(analog)
        _set_values(drums, count=2)
        with self._save([analog, drums], with_song=True) as bundle:
            midi_files = [n for n in bundle.namelist() if n.endswith(".mid")]
            self.assertEqual(len(midi_files), 1)
            song = self.temp_dir / "loaded_song.mid"
            song.write_bytes(bundle.read(midi_files[0]))
            sections = self._sections(bundle)
        loaded_song = MidiFile(str(song))
        self.assertEqual(len(loaded_song.tracks), len(MidiFile(str(self.song)).tracks))
        self.assertEqual(loaded_song.ticks_per_beat, 480)

        loaded_analog, loaded_drums = self._editor(AnalogToneEditor), self._editor(DrumKitEditor)
        for section in sections.values():
            data = bytes.fromhex(section[SYSEX])
            loaded_analog.receive_dt1(data)
            loaded_drums.receive_dt1(data)
        self.assertEqual(_editor_values(loaded_analog), _editor_values(analog))
        self.assertEqual(_editor_values(loaded_drums), _editor_values(drums))

    def test_msz_midi_values_in_range(self):
        editor = self._editor(AnalogToneEditor)
        with self._save([editor], with_song=False) as bundle:
            sections = self._sections(bundle)
        self.assertTrue(sections)
        for name, section in sections.items():
            for key, value in section.items():
                if key in HEADER_KEYS:
                    continue
                self.assertIsInstance(value, int, f"{name}: {key}")
                self.assertGreaterEqual(value, 0, f"{name}: {key}")
                self.assertLessEqual(value, 127, f"{name}: {key}")


if __name__ == "__main__":
    unittest.main()
