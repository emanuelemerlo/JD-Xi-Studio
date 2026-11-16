"""
Saving the Analog editor (no MIDI hardware).

The composer writes the Analog block in raw MIDI values with its name: the
values of an old bundle (display values, tests/fixtures) shown in the editor
come out of the composer as the same MIDI values.
"""

import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.io.helper import MidiIOHelper, patch_json_tone_name
from jdxi_editor.midi.sysex.json_composer import JDXiJSONComposer
from jdxi_editor.midi.sysex.patch_values import VALUE_FORMAT, VALUE_FORMAT_MIDI, upgrade_legacy_section
from jdxi_editor.ui.v2.analog import AnalogToneEditor

_APP = QApplication.instance() or QApplication([])
FIXTURE = Path(__file__).parent / "fixtures" / "jdxi_tone_data_19420000.json"
NAME = "Toxic Bass 1"


class TestJDXiJSONComposer(unittest.TestCase):
    def setUp(self):
        self.editor = AnalogToneEditor(MidiIOHelper())

    def tearDown(self):
        self.editor.close()
        self.editor.deleteLater()
        QApplication.processEvents()

    def test_compose_analog_synth_json_file(self):
        values = upgrade_legacy_section(json.loads(FIXTURE.read_text(encoding="utf-8")))
        values.update({f"TONE_NAME_{i}": ord(c) for i, c in enumerate(NAME, 1)})
        block = self.editor.blocks[0]
        self.assertGreater(self.editor.apply_values(block, values), 40)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = JDXiJSONComposer().process_editor(self.editor, Path(temp_dir))
            self.assertEqual(output.name, FIXTURE.name)
            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(saved["ADDRESS"], "19420000")
        self.assertEqual(saved[VALUE_FORMAT], VALUE_FORMAT_MIDI)
        self.assertEqual(patch_json_tone_name(saved), NAME)
        for spec in block.params:  # the old bundle has no LFO_SHAPE: shown as 0
            self.assertEqual(saved[spec.name], values.get(spec.name, 0), spec.name)


if __name__ == "__main__":
    unittest.main()
