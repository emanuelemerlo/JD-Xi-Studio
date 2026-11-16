"""Editor modules for JD-Xi parameters.

The tabs use the editors of jdxi_editor.ui.v2; what is here is the machinery
they are built on (SynthEditor, the Programs, Pattern and MIDI file editors,
the preset panel) and the Preset window.
"""

from jdxi_editor.ui.editors.program.editor import ProgramEditor

__all__ = ["ProgramEditor"]
