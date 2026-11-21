# JD-Xi Studio Features and Usage

This document covers patch loading/saving, undo and unsaved changes, the connection to the JD-Xi,
saving on it and new sounds.

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

1. **File › Patch › Save…** — Open the file dialog
2. Choose format by extension: `.jsz`, `.msz`, `.syx`, or `.json`
3. **.jsz / .msz**: Saves each block of the JD-Xi's memory as JSON in a ZIP, in raw MIDI values with its
   DT1 (see [MSZ Bundle Format](msz-bundle-format.md)); `.msz` also includes the loaded MIDI file (if any)
4. **.syx**: Converts current UI values to SysEx DT1 messages and writes binary; compatible with SysEx librarians and other Roland editors

### Load Flow

1. **File › Patch › Open…** — Select a file
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
| MIDI Player | MIDI saved separately in .msz |

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

JD-Xi › **Self-test…** runs fifteen steps through the app's own functions: the
connection and the SYSTEM settings, loading a program and tones, a dozen edits to the Analog and
the Digital 1 tone with Undo, the octave, a note (you listen), then what you do on the JD-Xi (a
tone, OCTAVE, a few notes). Each result is checked by reading the JD-Xi back; the edits stay in
its temporary memory and the starting program is loaded again at the end. The report (Markdown)
is saved in `~/.jdxi_studio/reports`.

### Connection and Off-line

The app keeps one connection state for every window: **Off-line** (no ports), **Verifying the
JD-Xi…** (ports open, no answer yet) and **connected** only once the instrument answers the
Identity Request as a Roland JD-Xi (a port named "JD-Xi" is not enough). The state is shown as a
badge under MIDI IN / OUT in the keyboard window, at the top right of the editors window and in the
corner of the other windows.

Off-line everything can be tried, but nothing is sent or saved: the commands that need the JD-Xi
(Save on the JD-Xi, Save patch, Send all, loading programs and tones, A/B recall) are off, with the
reason in their tooltip. When the JD-Xi arrives, the changes made without it are given up for what
it holds; **Save as file…** in that notice keeps them first.

### When the JD-Xi comes back (safety net)

After a disconnection (cable, power) everything is read and compared with what the JD-Xi confirmed
before: the same → «Reconnected»; different with unsaved changes → the parts that differ and
**Restore on the JD-Xi / Keep what the JD-Xi has** (a restore is read back part by part); different
with nothing at risk → the JD-Xi's settings are shown. Requests that go unanswered show «Unstable
connection» until a whole reading succeeds.

### Where you are: the context line

Under each editor's header (and on the Programs page): program › part › tone · origin (program,
preset, recipe, file, A/B, Init) · state: *original*, *modified, temporary* (sent, not kept),
*modified, not sent* (Off-line), *saved to file «…»*, *saved in E-12*.

### Save on the JD-Xi

The JD-Xi keeps a program only with its WRITE, in E–H. **Programs › Save on the JD-Xi…**: name it,
choose the slot (slots named «Init Program»/«Init Tone» are proposed as probably free; a slot with a
program asks first), press WRITE on the JD-Xi as shown, then **Done**: the app selects the slot and
reads it back. «Saved in E-12 ✓» only when it holds the sound; otherwise it says what differs.

### New sound and section help

**New sound ▾** (Digital and Analog editors): *From scratch (Init)* — this part's tone only, a plain
sawtooth with the filter open; one Undo brings the sound back — *From a preset*, *From a recipe*.
A **«?»** on OSC, FILTER, AMP, LFO, PITCH, effects, delay and reverb explains the section in the
information panel: what it changes, how the sound changes, an example.

---

## Related Documentation

- [Patch Saving Gap Analysis](patch-saving-gap-analysis.md) — Detailed comparison with Perl editor, format notes
- [MSZ Bundle Format](msz-bundle-format.md) — Music bundle structure
- [CHANGELOG](../CHANGELOG.md) — Full changelog
