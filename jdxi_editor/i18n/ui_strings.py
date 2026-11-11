"""
Texts that reach tr() at run time (button specs, labels built from data).

The catalogue tools collect only literal tr("...") calls, so the texts the
widget helpers translate at run time are listed here once, to be in the .ts.
Parameter names are not listed: they stay as on the JD-Xi display.
"""

from jdxi_editor.i18n import tr

UI_STRINGS = (
    # transport, pattern, MIDI file player
    tr("Play"), tr("Stop"), tr("Pause"), tr("Resume"), tr("Shuffle Play"), tr("Load"), tr("Save"),
    tr("Refresh"), tr("Clear…"), tr("Add Measure"), tr("Copy Section"), tr("Paste Section"), tr("Tap"),
    tr("Vel:"), tr("BPM:"), tr("Port"), tr("Loop"), tr("Set A"), tr("Set B"), tr("Clear A–B"), tr("Trim"),
    tr("Panic"), tr("Automation:"), tr("Insert Program Change Here"), tr("Detect Drums"),
    tr("Classify Tracks"), tr("Apply Presets"), tr("Track Classification"), tr("Mute Channels"),
    tr("MIDI Event Suppression"), tr("Keys/Guitars"), tr("Strings"), tr("Bass"), tr("Misc"), tr("Modes"),
    tr("Transport"), tr("File"),
    # programs, presets, playlists
    tr("Edit Program Name"), tr("Load Program"), tr("Load Preset"), tr("Load a program"),
    tr("Add to Playlist"), tr("Delete from Playlist"), tr("New Playlist"), tr("Delete Playlist"),
    tr("Refresh Playlist"), tr("Save Changes"), tr("Mixer Level Settings"), tr("Program"), tr("Preset"),
    tr("Genre:"), tr("Bank:"), tr("Search programs..."), tr("Search presets..."), tr("Search playlists..."),
    tr("-- Select a Playlist --"), tr("Program Name"), tr("MIDI File Name"), tr("Cheat Preset"), tr("Number"),
    tr("Description"), tr("Programs"), tr("Bank"), tr("Name"), tr("Genre"), tr("Play"),
)
