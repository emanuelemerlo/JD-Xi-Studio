# JD-Xi Studio Features and Usage

This document covers patch loading/saving, undo and unsaved changes, and SoundFont usage.

---

## 1. Recent Changes

What changed in each version is in [CHANGELOG.md](../CHANGELOG.md). (This section used to describe
the internals of the first editors, replaced in 1.0 by the current ones.)

---

## 2. Patch Loading and Saving

### Supported Formats

| Format | Load | Save | Description |
|--------|------|------|-------------|
| **.jsz** | ✓ | ✓ | Patch bundle (ZIP of JSON files) |
| **.msz** | ✓ | ✓ | Music bundle (patch + MIDI file) |
| **.json** | ✓ | ✓ | Single JSON patch file |
| **.syx** | ✓ | ✓ | Raw Roland SysEx (DT1 messages concatenated) |

### Save Flow

1. **File → Save Patch...** — Open the file dialog
2. Choose format by extension: `.jsz`, `.msz`, `.syx`, or `.json`
3. **.jsz / .msz**: Saves each block of the JD-Xi's memory as JSON in a ZIP, in raw MIDI values with its
   DT1 (see [MSZ Bundle Format](msz-bundle-format.md)); `.msz` also includes the loaded MIDI file (if any)
4. **.syx**: Converts current UI values to SysEx DT1 messages and writes binary; compatible with SysEx librarians and other Roland editors

### Load Flow

1. **File → Load Patch...** — Select a file
2. **.jsz / .msz**: Extracts the JSON files and sends each block's DT1 to the instrument as saved
3. **.json**: Sends single patch to the instrument
4. **.syx**: Reads binary, splits on F0…F7 boundaries, sends each SysEx message to the instrument

### Editors Included in Save

| Editor | Included |
|--------|----------|
| Digital Synth 1 & 2 | Yes (Common + Modify sections) |
| Drum Kit | Yes (Common + Partials) |
| Analog Synth | Yes |
| Effects | Yes (Effect1, Effect2, Delay, Reverb) |
| Vocal FX | Yes |
| Arpeggiator | Yes |
| Pattern Sequencer | No |
| Program Editor | No |
| MIDI File Player | MIDI saved separately in .msz |

### Undo, Reload and unsaved changes

- **Undo / Redo**: Ctrl+Z and Ctrl+Y (or Ctrl+Shift+Z), or the buttons at the top of each editor.
  They act on the editor shown only. A slider drag, or a drag on a graph (envelope, filter, LFO…),
  is one step even when it moves two values; the value undone is sent to the JD-Xi at once. Up to
  30 steps; a step that cannot be applied changes nothing. A value the JD-Xi sends drops the steps
  on that value.
- **● Modified** next to the editor's name (and a dot on its tab) while its changes are not saved
  to a file (`.jsz`, `.msz`, `.syx`).
- **Asked first** before a preset, a program or a patch file replaces edited parts, and at closing:
  *Save to file…*, *Discard the changes* or *Cancel*. Off in Preferences › *Ask before losing
  unsaved changes*. Changes made on the JD-Xi itself are not seen beforehand.
- **Reload** (Digital, Drums, Analog): back to the values from before the editor's changes,
  however many (asked first; off when nothing differs).

The edits go to the JD-Xi's temporary area as they are made: to keep them, save to a file or
press WRITE on the JD-Xi.

### A/B compare (Digital 1, Digital 2, Analog)

The tone editors' top bar has, after Undo / Redo / Reload, **A B · camera · ⇄ · disk**: two photos
of the part's whole Tone, to switch between while playing.

- **A / B** choose a slot; a full one is also recalled. Empty slots have a dashed outline, the
  chosen one an outline in the part's colour, the active one (the JD-Xi plays it) is filled with
  that colour, with a dot once modified.
- **Camera** captures the Tone in the chosen slot. With the JD-Xi connected the Tone is read again
  first and the photo is taken only from a complete answer; without it the editor's values are
  taken, marked "local". Replacing a photo asks; one never saved to a file can be saved first.
- **⇄** (Ctrl+Shift+A) recalls the other photo. A recall sends the photo's blocks, reads the Tone
  back and makes it active only when the JD-Xi holds exactly the photo; otherwise nothing is
  active and the Tone is reported uncertain. Only this part's Tone is sent: the other parts, the
  effects and the program stay as they are.
- **Disk** saves the active photo as a part `.syx` (read by the editors' Import) with the name
  given, written as Tone Name.
- Recall and ⇄ are disabled while the JD-Xi is not connected. Notices float under the buttons.
- The photos are kept per part in `~/.jdxi_studio/ab_compare` and come back at start; nothing is
  sent until a slot is pressed. After a program change (or a restart) a recall asks first.
- Undo / Redo / Reload are unchanged: a recall arrives as values from the JD-Xi.

### Save Source

The editor **saves from the current UI control values**. The keyboard window reads the JD-Xi at
start and reads the part shown every two seconds, so the values follow the instrument; an editor
also reads its own area when it is shown, and «Read from JD-Xi» reads it on request.

For more detail, see [Patch Saving Gap Analysis](patch-saving-gap-analysis.md).

---

### Screen sizes

The editors are designed for about 2560x1440 (4K at 150%). On a screen with less than 1150 px of
usable height (1080p at 125%: 1536x864; 2496x1664 at 175%: 1426x951) they use a compact layout:
smaller knobs, graphs and spacing with the text the same size; Digital puts each partial's
sections on two tabs and Programs puts the library among the lower tabs. Narrower than 1800 px,
the side panel is narrower; narrower than 1500 px, some rows of cards become columns.

### Following the JD-Xi

- At start the window reads the program, the four tones and the SYSTEM settings (the channel the
  JD-Xi takes program changes on: programs are sent there).
- Every two seconds it reads the part shown — not while a MIDI file or pattern plays, nor for
  three seconds after a click, key or value from the app — so a tone, an octave or a value
  changed on the JD-Xi reaches the display, the OCTAVE buttons, the panel sliders and the editors.
- The notes played on the JD-Xi light the window's keys; after three notes on a part's channel
  the window selects that part (the JD-Xi plays the part selected on it).

### Self-test with the JD-Xi

Help › **Self-test with the JD-Xi…** runs fifteen steps through the app's own functions: the
connection and the SYSTEM settings, loading a program and tones, a dozen edits to the Analog and
the Digital 1 tone with Undo, the octave, a note (you listen), then what you do on the JD-Xi (a
tone, OCTAVE, a few notes). Each result is checked by reading the JD-Xi back; the edits stay in
its temporary memory and the starting program is loaded again at the end. The report (Markdown)
is saved in `~/.jdxi_studio/reports`.

## 3. SoundFont Usage

### Overview

JDXI-Editor can use SoundFont (.sf2/.sf3) files for:

1. **FluidSynth playback** — Local software synth for MIDI playback without hardware
2. **Preset list source** — Use SoundFont preset names instead of built-in JD-Xi names (especially for Drums)

### Configuration

Open **MIDI Configuration** (gear icon or via menu) to access:

| Option | Description |
|--------|-------------|
| **Enable FluidSynth for local playback** | Uses FluidSynth for MIDI playback when no hardware is connected |
| **Use SoundFont List** | When enabled, preset names (especially Drums row) come from the configured SoundFont instead of built-in JD-Xi options |
| **Hardware Interface** | Audio output device for FluidSynth (requires `sounddevice`) |
| **SoundFont (SF2/SF3)** | Path to your .sf2 or .sf3 file (e.g. FluidR3_GM.sf2) |

### Use SoundFont List

- **Drums row**: When enabled, the Pattern editor Drums row shows GM percussion names (e.g. "Bass Drum 1", "Acoustic Snare") from the SoundFont instead of JD-Xi built-in names
- **Digital / Analog**: When enabled and a valid SF2 path is set, preset lists can be populated from the SoundFont (bank 0 melodic, bank 128 for drum kits)
- **Fallback**: If the path is invalid or the file cannot be read, built-in JD-Xi presets are used

### Default Path

The default SoundFont path is `~/SoundFonts/FluidR3_GM.sf2` if that file exists. You can browse to select a different .sf2 or .sf3 file.

### Requirements

- **FluidSynth**: `pip install pyfluidsynth` (or `fluidsynth`)
- **SoundFont parsing** (for preset list): `pip install sf2utils`
- **Hardware interface selection**: `pip install sounddevice`

---

## Related Documentation

- [Patch Saving Gap Analysis](patch-saving-gap-analysis.md) — Detailed comparison with Perl editor, format notes
- [MSZ Bundle Format](msz-bundle-format.md) — Music bundle structure
- [CHANGELOG](../CHANGELOG.md) — Full changelog
