# Changelog

All notable changes to JD-Xi Studio (and, before 1.0, to this fork of JDXI-Editor) are documented in this file.

# [Unreleased]

### Changes
- The main window's menus follow the app: **File** (Patch › Open / Save, MIDI Player › Open / Save
  / Save as / Recent), **Editor** (the editors window's tabs, by section: Programs, Parts, Effects,
  Playback, Recipes, Settings; Ctrl+0–9 in tab order), **JD-Xi** (Save the program, Send all — now
  asking first, naming the editors —, Read the user programs, MIDI Configuration, Self-test),
  Preferences, Quit), **Tools** (monitor, debugger, log), **Window**, **Help**. «…» only on what
  opens a dialog; every File and JD-Xi item's tooltip says what it loads or sends, and where. What
  cannot be done is off, its tooltip saying why: MIDI Player › Save / Save as without a file in the
  player, Save the program, Send all, Read the user programs and Self-test with the JD-Xi offline.
- Ctrl+O / Ctrl+S open and save the **patch** (they were the MIDI Player's file's, wherever you
  were); the MIDI Player's file: Ctrl+Alt+O / Ctrl+Alt+S. Menu items that are off are greyed out.
- **Editors** (keyboard window, menu bar) and **Keyboard** (editors window, tabs bar) bring the
  other window to the front, on any screen, without Alt+Tab.
- Removed Window › *Line up the editors with the keyboard*: the editors window opens where it was
  left, and the buttons above bring it in front.
- The «MIDI file» tab is the **MIDI Player**.
- A track without a name shows, in grey, the instrument it plays (the file's instrument name or
  its General MIDI program; channel 10: drums).
- MIDI Player › Tracks: **Expand** hides the cards not needed while listening (Player and Playback
  stay); a grip under the card sets its height (remembered; double click: back to normal).
- USB recorder: «Save» is **Record on every Play**, with a tooltip saying what it records.
- MIDI Player › **Fit to the JD-Xi** (was Classification): a line says what of the file the JD-Xi
  plays («28 of 44 tracks are on channels no JD-Xi part plays»); **Assign tracks to parts…**
  proposes a part for each track (drums to Drums, the best bass, keys and strings track to Digital 1,
  Digital 2, Analog, the rest not played), to check and apply; **Starting sounds** (was Apply
  presets). The channel buttons of the four parts stand out and say which part plays them.
- Setting the loop's A point shows it on the ruler at once (it showed only with B).
- Opening a big MIDI file is much faster (a 45-track, 20-minute song: from 20–40 s to a few
  seconds) and says so meanwhile on the player's display («Loading: track 12 of 45»), then tracks and
  time in the status bar; no more tiny windows flashing while the tracks are built.
  The Pattern imports the file when it is shown, and only its first 64 bars (a pattern, not a whole
  song); the file's length is read once instead of once per track and per playhead step.
- Programs › Organize: the «Cheat Preset» column is «Extra sound», one readable combo (its MIDI
  bytes in the tooltip, what it does in the header's); the file and Play cells in the app's look.
- Programs › Organize: Add to / Remove from playlist over the songs' table (they act on the songs);
  Play, Stop, Pause and **Mix** (was Shuffle Play) in a compact row of their own, with the
  now-playing line beside them.
- picomidi 0.3: a muted track no longer cuts a note another track holds; a program chased from
  mid-song comes with its bank select; a track's velocity scale at 0 silences it.

### Fixed
- Programs › Library: a user bank (E–H) shows all its 64 slots; those JD-Xi Studio has not read
  yet appear as «(not read yet)» (G and H looked empty: only programs read once are known).
- Message boxes: buttons wide enough for their text («Scarta le modifiche» was cut).
- Pattern: Play, Stop, Pause, Shuffle at one width (they stretched with the window).
- Spin boxes (BPM, Vel, Steps…): wider up / down buttons with visible arrows.
- MIDI Player › Automation: the label stays next to its controls.
- On 1080p screens the envelopes, filter curves and LFO views were squashed (an envelope ~68 px
  high): about 90 px now, room to drag their points.
- MIDI Player: Play, Stop, Pause, Panic, Load and Save at one width (the first four stretched with
  the window, Load and Save stayed small).
- A typed name (program, tones, drum kit) is an edit: one Undo step, «Modified» (it was taken for
  a value from the JD-Xi: no Undo, and it became the original).
- Save on the JD-Xi: a slot whose content is not known asks before writing and is no longer
  proposed as probably free (only slots known to hold the init program are).
- A tone change on one part forgets only that part's data; the others stay known and confirmed
  (A/B photos of the other parts can still be recalled). Program changes on channels the JD-Xi does
  not play change nothing.
- A message the MIDI port refuses no longer counts as held by the JD-Xi; the window says so.
- The context line says «not sent» when no connection is known (it said «temporary»).
- USB recording: stereo (it saved only one channel of the JD-Xi); only the devices that can record
  are listed, and the JD-Xi's input is chosen (it could pick its output, which cannot record); the
  format is 16 bit (the 32 bit the interface asked for was never used).
- Changing a track's channel now moves its pitch bend and aftertouch too; the drum detection sees
  pitch bend; the pattern's tempo and time signature are written again (message types compared
  as strings).
- USB recording: a stop arriving before the recording thread starts is no longer lost (it ran its
  whole 10 s tail).
- The context line shows the last save: «saved in E14» no longer stays after a later save to file.

### Removed
- «Open current MIDI as PDF» (sheet music through LilyPond, not installed with the app) and the
  music21 dependency; «Digital Synth 3» (Ctrl+3), which opened nothing (the JD-Xi has two Digital
  parts).
- The FluidSynth software synth (MIDI configuration) and the SoundFont preset lists: they played
  General MIDI sounds, not the JD-Xi's, and only for notes from a MIDI keyboard. pyfluidsynth, the
  `soundfont` extra (sf2utils, sounddevice) and the bundled FluidSynth DLLs are gone with them.

# [1.0.0-beta.2] - 2026-11-19

Sound design and the Programs tab. Tried on the simulated JD-Xi (the automatic checks run on it in
every build); on the real instrument the checks of `doc/hardware-test-plan.md` are still to run
(section 1a: `pytest -m hardware tests/test_jdxi_checks.py`, then the ★ steps).

### Changes
- Checks against a JD-Xi (`tests/test_jdxi_checks.py`): identity, a whole reading, pending until
  read back, reconnection, restore, Init and Undo, Save on the JD-Xi; on the simulated JD-Xi in
  every run, on the real one with `pytest -m hardware` for each release
- A «?» on the panels of the tone and effects editors (OSC, FILTER, AMP, LFO, PITCH, effects,
  delay, reverb): what the section changes, how the sound changes, an example, in the information
  panel
- «New sound ▾» in the Digital and Analog editors: from scratch (Init: this part's tone only, a
  plain sawtooth with the filter open; one Undo brings the sound back), from a preset, from a recipe
- «Save on the JD-Xi…» (Programs): name the program, choose the slot (E–H, «Init Program» slots
  proposed as probably free, a used slot asks first), press WRITE on the JD-Xi as shown, and the app
  selects the slot and checks that it holds the sound: «Saved in E02 ✓» only then
- A context line under each editor's header and on the Programs page: program › part › tone ·
  origin (program, preset, recipe, file, A/B) · state (original, modified and temporary, modified
  and not sent, saved to file, saved in a program slot)
- The «JD-Xi connected» indicators (editors window, Settings) follow the shared connection: green
  only once the JD-Xi answered; the main window shows the badge under MIDI IN / OUT; no badge
  over dialogs' buttons
- What the JD-Xi confirmed (read back) is kept apart from what was only sent. When the JD-Xi comes
  back after a disconnection everything is read and compared: same → says so; different with
  unsaved changes → the parts that differ and «Restore on the JD-Xi / Keep what the JD-Xi has»
  (the restore is checked part by part); different with nothing at risk → the JD-Xi's is shown
- Programs: one JD-Xi-style display only, the program's (it said "No file loaded"; now the number
  and name of the program loaded). The playlist shows what plays as a line of text over its bars
- One connection state for the whole app: the JD-Xi counts as connected only once it answers as a
  JD-Xi (a port named JD-Xi is not enough). Without it: a warning at start (once), an «Off-line»
  badge in every window, and the commands that need it are off with the reason in the tooltip.
  When it arrives after changes made without it, they are given up for what it holds, with
  «Save as file» to keep them; requests that go unanswered show «Unstable connection»
- Send all says whether it was complete, partial or failed
- JD-Xi Studio presents itself as "Visual Sound Design, Editing & Librarian" (README, About, start screen)
- Programs tab, simpler: the library searches number, name, genre and the four tones, sorts by
  number, name or genre, shows "N of M programs", marks the program loaded on the JD-Xi (▶, bold)
  apart from the one selected, and shows the tones in their parts' colours. Its menu (right
  click): Load, Rename and Export (the loaded program), Genre (user programs), Add to playlist
- Parts and mixer in one card: under each part's fader its tone (click: choose another, the
  part's presets), MIDI channel and Edit; the separate list of parts is gone
- Below, Organize: the playlists and, beside them, the selected playlist's programs. Presets are
  chosen from each part, user programs are the library's E–H banks

### Fixes
- Dialog titles no longer cut in the title bar (every dialog is at least as wide as its title)
- Playlists: «Add to playlist» offers every program, factory ones (A–D) included; it said «All
  programs are already in this playlist» when no user program had been read yet
- Loading a patch says whether it reached the JD-Xi whole, in part or not at all
- Start-up: the dialogs (MIDI configuration, Off-line notice) wait for the start screen to go;
  its progress steps reach the end and the last one is seen
- Message boxes in the app's look (dark, light text): their text was red on light grey; the
  Off-line notices carry a warning sign
- MIDI configuration: the status dot level with its message
- Program icon: the display reads «JD-Xi»
- A message that cannot go out (JD-Xi not connected) is no longer taken as what the JD-Xi holds
- A/B: a photo taken without the JD-Xi whose data is not all known can no longer be recalled or
  saved (bytes never read were sent as zeros); taking it again with the JD-Xi connected fixes it
- A/B: when a photo cannot be written to disk it says so, instead of "captured"
- Recipes: setting a row or a whole step is one Undo, also when it sets several editors
- Program mixer: each part in the colour of its tab, the Master in a neutral light with an output
  icon; the faders light from the bottom up to the level (at 0 they looked full), centred over
  their icon and mute, without tick marks, with a box above showing the level, where it can also
  be typed
- MIDI Debugger, CC / PC tab: the fields were squeezed flat; the tab now scrolls
- MIDI Monitor: says why it stays empty while the JD-Xi is not connected (nothing is sent)
- Program icon: at 32 px and below (title bar, taskbar) it shows the name, "JD" over "Xi", instead
  of the drawing, which was unreadable at that size
- The middle C
  mark on the keyboard is smaller and quieter
- Tooltips were black (unreadable) on the settings page and in the new editors on Windows: a
  tooltip is a window of its own, so the colours are now set for the whole app

### A/B compare of a Tone (Digital 1, Digital 2, Analog)
- In the tone editors' bar: **A B** to choose (and recall) a photo of the whole Tone, **camera** to
  capture the Tone in the chosen slot, **⇄** (Ctrl+Shift+A) to switch while playing, **disk** to
  save the active photo as a named part `.syx`; the photos are kept per part across restarts
- The active photo (the one the JD-Xi plays) is filled with the part's colour, with a dot once
  modified; what needs the JD-Xi is disabled while it is not connected; notices float under the
  buttons without moving the bar
- Capture reads the Tone from the JD-Xi first (a "local" photo without it); a recall sends only
  that part's Tone and counts as done only once the JD-Xi is read back holding exactly the photo;
  replacing a photo never saved to a file offers to save it first
- A program change makes the next recall ask first; Undo / Redo / Reload unchanged
- Fixed: a read started right after another one could lose a request (the queue took it for a
  duplicate of the one just answered) and wait for its timeout

### The window follows the JD-Xi's controllers
- The pitch and mod wheels in the window move with the JD-Xi's (nothing is sent back)
- The panel sliders follow the JD-Xi's knobs as they turn (Cutoff, Resonance, Level, LFO Rate,
  Envelope, LFO depths, Reverb, Delay), no longer a couple of seconds later
- Fixed: letting go of the window's pitch wheel did not send it back to the centre (the JD-Xi
  stayed bent); the mod wheel sprang back to zero like a pitch wheel

### Look
- The window's keyboard marks middle C (a red dot and «C4») on the key that sounds it at the
  current octave: the lower C with Octave +1, the top one with -1; none beyond the 37 keys
- Logo, program icon and installer picture: the JD-Xi's big dial drawn as on the instrument, an
  endless knob without a pointer, its category shown by the lit LED on the circle around it

# [1.0.0b1] — tag `v1.0.0-beta.1` (first beta: one framework for the editors, install on Linux and macOS)

### Installing on Linux and macOS
- `install.sh`: one command installs the newest release (or a given one) in its own Python
  environment, with a launcher in the applications menu (Linux) or `~/Applications` (macOS) and a
  `jdxi-studio` command; it checks the libraries needed and shows how to install the missing ones;
  run again to update, `--uninstall` to remove (settings and patches stay). Tried on Linux; the macOS
  part is untested

### Consolidation of the editors
- The Analog editor is built on the same framework as the Digital, Drums and Effects editors:
  one way to send, receive, save and undo for every tone editor; its tone name is saved in the
  patch with its values
- The old editors no longer used (Digital, Drums, Effects, Vocal FX, Arpeggio, Analog) are
  removed, with the widgets and data modules only they used (78 modules); Programs, Pattern and
  MIDI File keep their current editors

### Fixes (code review)
- A .msz bundle can no longer write its MIDI file outside the temporary folder: it is always
  extracted as `bundle.mid` there, whatever name the archive gives it
- After an incomplete read, saving takes from the copy of the JD-Xi's memory only the sections
  that read confirmed; a program chosen on the JD-Xi empties that copy
- A connection whose output did not open is no longer reported as made (the input is closed)
- A malformed MIDI message is logged without a second error in the handler

### Fixes
- A crash that could happen at any moment (seen on macOS): Python's garbage collector could run in
  the MIDI request thread and destroy Qt objects there; it now runs on the main thread only
- With an octave shift on the JD-Xi the keys played light in the window where they are pressed
  (the JD-Xi sends them an octave or more away: the shifted octave did not light, or lit the
  wrong key); a key held while the octave changes still goes off

# [1.0.0a5] — tag `v1.0.0-alpha.5` (the window follows the JD-Xi; self-test with the instrument)

### The window follows the JD-Xi (hardware tests, round 1)
- At start, once the ports are open, the window reads the program and the tones: the display
  no longer starts on «Init Tone»
- The part shown is read again every two seconds (not while a MIDI file or pattern plays, not
  just after a click, key or value from the app): a tone chosen on the JD-Xi appears on the
  display, the OCTAVE − / + light as on the instrument and the panel sliders (Cutoff, Resonance,
  Level, LFO) move to the tone's values without sending them back
- A program change from the JD-Xi on a part's channel reads that part; only the program channel
  changes the program number (a tone change used to change it)
- The notes played on the JD-Xi light the window's keys
- Playing the JD-Xi's keyboard selects in the window the part selected on the JD-Xi (its notes
  come on that part's channel): the window's tone buttons, octave and sliders act on the part
  being played
- The window's Octave − / + write the part shown (they always wrote Digital 1)
- The preset panel's ‹ › load the tone, as the JD-Xi's buttons do (they only moved the list)
- Requests and received SysEx are logged at DEBUG (the reading every two seconds would fill the log)
- Programs go to the channel the JD-Xi takes them on (SYSTEM › Program Ctrl Ch, read at start);
  the status bar says what to change on the JD-Xi when it takes no program changes
- The keyboard window's tone arrows loaded the preset before the one shown
- Programs: «Load A02» under the library
- Closing after «Discard the changes» with the keyboard always on top (the dialog was cancelled)
- A DT1 for one parameter (sent by the JD-Xi) no longer sets every other parameter of the
  editor to 0
- **Help › Self-test with the JD-Xi…**: the app loads a program and tones, edits a value and
  undoes it, changes the octave and plays a note, and checks each result on the JD-Xi; then
  asks you to choose a tone, press OCTAVE and play on the JD-Xi and checks that the window
  follows. A report is saved in `~/.jdxi_studio/reports`
  It also makes a dozen edits to the Analog and the Digital 1 tone — oscillator, filter, amp,
  envelopes, LFO — checks every value on the JD-Xi, undoes the edits and checks again (in the
  JD-Xi's temporary memory: nothing is written, and the starting program is loaded again)
- Effects: a type chosen in the app whose parameters are all 0 (via MIDI the JD-Xi loads no
  settings for a new type) gets audible starting values — it was silent (Balance D100:0W,
  Depth 0, Level 0)
- A reading of the JD-Xi on its way while a value is edited no longer puts the old value back
  (and no longer loses the edit's Undo step): the reply's bytes written after the request are
  the editor's
- A value put back by hand (Arpeggio ON, then OFF) no longer leaves the editor marked modified
- Arpeggio ON (in its tab or with the panel button) with no part set to arpeggiate: the part
  selected arpeggiates (ON did nothing to hear). The panel button works through the Arpeggio
  editor and lights as the arpeggio is; it wrote offset 3 of the Program Part areas instead of
  the zones
- Recipes: in an empty editor «Take the values from the JD-Xi» asks for a part and makes a row
  for every parameter of it, with the JD-Xi's values
- Self-test: a KO names the parameters, says when the tone was changed during the test and
  how many Undo steps the edits made
- An orange pencil on the tab of an editor with changes not saved (it was a dot before the
  name), and «✎ Modified» in the editor
- A reply logged with the fields of a request parsed at the same time (the input and output
  handlers shared one parser)
- The messages sent were never heard by their listeners (a signal of the MIDI helper's second
  base class): the MIDI OUT light blinks again, the MIDI monitor shows them

### Recipes
- The side panel of the other tabs: what the page is for, and for the row chosen its part,
  parameter, the recipe's value against the JD-Xi's and the recipe's note
- Tidier tables (columns as wide as their text, taller rows, the actions on the left of their
  column); an empty library says what goes there

### Italian
- The Italian translation uses the words of the JD-Xi's Italian manual: *tono* (not *timbro*),
  *arpeggio*, *sequencer di pattern*, *file MIDI*, *drum kit*, *Velocity*, *reverb*, *Vocal FX*,
  *log*; the panel's names stay as printed (Part Select, Program, Tone, Mute);
  `doc/italian-glossary.md` lists them

### Tabs
- **Core tabs** always there (Programs, Digital 1 and 2, Analog, Drums, Arpeggio, Effects,
  Vocal FX, Pattern, MIDI File); **Program parts, Recipes and Settings** open and close: a **+**
  at the top right of the editors window (or a right click on the tabs) opens them, a small ×
  closes them; the editor keeps its values when closed, and the open ones come back at the next
  start

# [1.0.0a4] — tag `v1.0.0-alpha.4` (screens from 1080p to 4K; safer Undo and Reload)

### Screens from 1080p to 4K
- **Compact layout** on low screens (available height under 1150 px: 1080p at 125%, 2496x1664
  at 175%): smaller knobs, graphs and spacing, the text the same size; in Digital the partial's
  sections on two tabs (OSC · FILTER · AMP / LFO · MOD LFO · MISC), kept in step across partials;
  in Programs the library is the first of the lower tabs, beside parts and mixer; in Pattern the
  card notes go into tooltips
- **Narrow screens** (under 1800 px wide): a narrower side panel; under 1500 px some rows of
  cards become columns (Pattern, Vocal FX) and the steps are narrower: no sideways scrolling
- The side panel is as wide as its content plus the system's scroll bar (macOS: no 2 px
  sideways scroll)
- **Effects**: each effect card is as tall as the type shown (Thru no longer leaves a large
  empty area); the chain diagram keeps its height

### Undo, Redo and Reload
- **A drag on a graph** (envelope, filter, LFO, effects…) is one step of Undo, even when it moves
  two values (e.g. Decay and Sustain); Undo puts them back in reverse order, Redo in order
- **Reload** (Digital, Drums, Analog) brings back the values from before the editor's changes,
  without reloading the preset from the JD-Xi (it works offline too); asked first, and off while
  nothing differs
- **Up to 30 steps** of Undo: more are hard to follow among controls and tabs; Reload still goes
  back to the start, however many changes
- **All or nothing**: a step that cannot be applied changes nothing and stays where it was
- **Values from the JD-Xi**: one the instrument sends drops the steps on that value, so Undo and
  Redo never bring back something it no longer has
- **Ctrl+Z / Ctrl+Y** act on the editor shown only, never on one out of sight
- A program change resets the replaced parts' history only once it is sent (port closed: the
  changes and their Undo stay)

# [1.0.0a3] — tag `v1.0.0-alpha.3` (a name of its own everywhere; fixes from testing alpha 2)

### JD-Xi Studio, not JDXI-Editor
- **Installer**: "JD-Xi Studio" by Emanuele Merlo, with its own AppId and folder
  (`%LOCALAPPDATA%\Programs\JD-Xi Studio`): it no longer replaces, or is replaced by, the original
  JDXI-Editor, and the two can be installed side by side. The program is `JD-Xi-Studio.exe`, the files
  `JD-Xi-Studio-<version>-setup-win64.exe` and `JD-Xi-Studio-<version>-win64-portable.zip`.
  An alpha 1 or 2 installed as "JDXI Editor" is offered for removal (settings and files are kept)
- **An update removes the old version's files** first: pictures of an earlier version no longer stay
  next to the new ones (the Jupiter-8 photo in the Digital editors came from there)
- **Own settings and user folder**: `~/.jdxi_studio` (programs, recipes, recent files, logs) and its
  own settings key; at the first start the settings and files used up to alpha 2 (the original
  program's) are copied over, the originals are left for JDXI-Editor

### Changes: undo, reload, no loss by mistake
- **Undo / Redo** (Ctrl+Z, Ctrl+Y or Ctrl+Shift+Z, and two buttons at the top of every editor):
  the editor shown, or the last one edited; a slider drag is one change; the value undone is sent to
  the JD-Xi at once
- **Modified**: an editor with changes not saved to a file shows "● Modified" next to its name and
  a dot on its tab
- **Asked first**: before a preset, a program or a patch file replaces edited sounds, and at
  closing: *Save to file…* (then repeat), *Discard the changes* or *Cancel*. Only the parts that
  change count (a Digital 1 preset does not ask about Analog). Preferences › *Ask before losing
  unsaved changes* turns it off. What is done on the JD-Xi itself cannot be stopped
- **Reload** (Digital, Drums, Analog): the preset again, the sound as stored

### Logs
- **Log viewer**: fixed-width text with the columns lined up (the emoji before each message are left
  out, the level column says it); a **Warnings and errors** tab with their count, showing only the
  lines from WARNING up and what follows them (e.g. a traceback); no more broken or repeated lines
  (the file was read by characters but positioned by bytes, and *Clear* read it all again)
- **Kept two weeks**: log files older than 14 days are deleted at start
- **The level in Preferences works**: every level can be chosen and is kept (the row number was
  saved in its place, so it always came back as DEBUG) and applied at start; the "Enable Logging?"
  box, which switched nothing, is gone
- Selecting Vocal FX no longer logs a warning about an "unknown synth"

### Fixes
- **Preset card** (Digital, Drums): every row as wide as the card, nothing cut or sticking out with
  large Windows text; Previous / Next as arrows; the display fits the card
- **The preset's category as a card** (icon and name: Bass, Strings/Pad, Lead, Brass, Keyboard,
  Seq, FX, drum kits) in place of the picture of the synth a preset imitates, which said little and
  suggested a compatibility the JD-Xi does not have
- **The category card follows the list**: choosing a category (which selects one of its presets)
  updates it; Analog has it too
- **Analog's preset panel** looks and lines up as Digital's and Drums' (no blue frame of its own, both
  tabs readable, rows as wide as the card)
- **Splash**: the mark with the name, origin and version beside it, the startup steps and display
  the card's width, the trademark notice small at the bottom
- **Preferences** in two cards (Interface, Logs): each option with its box and, in grey, what it does
- **USB recorder**: icons and names next to their controls (the name column took the spare width)
- **Settings is always among the tabs** (it appeared only when opened from the menu)
- **Log viewer** shows this session's log (the logs are one file per session, with date and time)
- **Programs**: the area of Presets / User Programs / Playlist / Playlist Editor keeps one height
- **Recipes in English too**: `JD-Xi recipe - template.xlsx` (with its menus and Check column, the
  instructions and the example translated), `JD-Xi recipe - blank.csv`, `JD-Xi recipe - example.csv`,
  `JD-Xi recipe parameters.csv`, made from the Italian files by `building/recipes/make_english.py`.
  The Recipes page offers the files in the interface's language; the editor reads both (English
  headers, "value / range / by ear", EFFECTS / VOCAL)
- **Obsolete files removed** (115): the instrument pictures the editors no longer show (digital_synths,
  analog_synths, drum_kits, effects, vocal_fx, programs, presets, arpeggiator), unused icons and fonts,
  a duplicate LCD font, the original project's Perl/Arduino leftovers and old CSVs, and the development
  notes of finished work (critiques, gap analyses, migration and refactoring plans); `make_art.py` now
  draws only the logo, the icons and the installer image
- **Exporting a recipe to .xlsx** writes Step, From and To as numbers: the template's Check column
  no longer marks every range row as wrong

# [1.0.0a2] — tag `v1.0.0-alpha.2` — 2026-11-12 (Windows 11 fixes, JD-Xi Studio's look)

The fixes from testing alpha 1 on Windows 11, JD-Xi Studio's own logo, icon and pictures,
the About window with both authors, the documentation aligned, and the Release workflow.

### About, documentation and releases
- **The repository is now `emanuelemerlo/JD-Xi-Studio`** (it was `JDXI-Editor`): the update
  check, the links in the app, the README, the documentation and pyproject use the new name
  (GitHub redirects the old one, so earlier versions still find the updates)
- **Panel names always fit**: where the system's font is wider than the one designed for (Segoe UI
  missing on Linux, Windows' scaling), a name is drawn a little smaller instead of being cut; this
  made the UI audit fail on the GitHub runners
- **Every editor has its title badge** at the top left (Analog and Recipes were missing it); the UI
  audit checks it
- **About** in the new look: the logo, the version as the release names it (1.0.0-alpha.1), the
  authors (Emanuele Merlo for JD-Xi Studio, Mark Brooks for the original JDXI-Editor), libraries,
  licence and the trademark notice
- **Documentation aligned**: README (JD-Xi Studio, features, new screenshots of every editor and of
  the keyboard window, download, release steps, credits), README.rst, the Sphinx project name,
  authors and version (read from `project.py`), pyproject authors, LICENSE (both copyrights);
  developer notes moved to `doc/dev-tools.md`
- **Release workflow** (`.github/workflows/release.yml`, Actions › Release › Run workflow): tests,
  Windows installer and portable app, Python wheel and source package, then the tag and the release
  with every file attached, in one run; no tag to push by hand
- **Removed**: the Sphinx build output committed in `doc/latex` (20 MB), an old PDF of the 0.8
  documentation, IDE files, unused root files (old PyInstaller specs, `volume_cc.py`,
  `programs.json`), the GIFs of the old interface

### Windows 11 fixes

- **The keyboard window starts at its own size**, not maximised from a saved state, and the
  maximise button brings it back to that size (it could only be minimised)
- **The editors window comes in front** when a part, Vocoder, Effects or a menu opens an editor
  (it opened the tab behind the keyboard window)
- **The panel shows the editor that is open**: Arpeggiator lights while its editor is open (the
  part lit before stayed lit), a part lights when its editor opens from a menu or its tab; Vocoder
  and Effects do not stay lit; a preset change is sent once (every part click connected it again)
- **Switching editors is immediate**: colouring the selected tab restyled every editor (about
  0.9 s per click); now only the tab bar
- **UI audit** (`scripts/ui_audit.py`, run by the tests at 100% and 150%): every panel button and
  menu entry opens the right tab and lights the right button, no panel text cut or overlapping,
  showing an editor stays fast, each name centred over its slider or button
- **Pattern uses the whole window**, with the side panel as the other editors: pointing at a
  control (Play, BPM, Tap, the steps, the mute buttons...) explains it there; the steps grow
  with the window
- **Part Select follows the tab shown**: only the button of the editor shown is lit; Programs
  (a click on the display), Effects, Pattern... or the editors window closed: none lit
- **Keep on top is a pin** next to minimise / maximise / close (also in the Window menu): it
  is not saved and is off at every start, so a dialog can never be stuck behind the keyboard
  at launch
- **New pictures and icon**: one family of illustrations in the JD-Xi's look (black body, red
  display, the part colours), drawn by `building/art/make_art.py`: one per sound family (piano,
  pad, bass, strings, drum kits...) shown small at the bottom of the preset card, plus Programs,
  Presets, Effects, Vocal FX, Arpeggio; the installer's side image
- **New program icon**: a JD-Xi in miniature (red display, knobs with their red ring, step LEDs,
  mini keys), black and red only; simpler at 16-32 px so it stays readable in the taskbar
- **New logo**: JD-Xi Studio's own, in the JD-Xi's colours (black panel, white labels, red
  light only), laid out as the instrument (controls on the back two thirds, 37 mini keys at the
  front, microphone), in a gentle perspective; the name with "Xi" in red, replacing the original JDXI-Editor logo in the READMEs
- **Obsolete files removed**: about 150 unused pictures, icon sets, GIMP sources and old splash
  screens; the photos of other synths replaced by the new pictures
- **Keyboard always on top**: dialogs (MIDI ports, messages, names to save) come up above the
  keyboard; before, a dialog could open behind it and block it, so the keyboard seemed frozen
- **Panel sliders**: each name is centred over its slider (the names were left-aligned and the
  sliders sat at the left of their column); the names a little smaller, so "Reverb" is no
  longer cut
- **Panel layout**: the title in pixels (in points it grew with Windows' DPI and covered the
  display), the display lower, Program and Tone to the right of the part buttons (they
  overlapped), each label right above its - and + buttons, aligned alike; Vocoder and Effects
  centred over their buttons; room for "Reverb" over its slider; Analog Synth in the same colour
  as the other parts
- **Displays on solid black**, without the red gradient and the glow, on the keyboard and in
  every editor
- **Pattern, MIDI file player and Programs** with the same badge and cards (title inside, in the
  editor's colour) as the other new editors
- **Starts from VS Code and from the file**: profiling is off unless `JDXI_PROFILE=1` and never
  crashes when a debugger or another profiler is active ("Another profiling tool is already
  active"); `python jdxi_editor/main.py` uses its own folder's code even if another copy is installed
- **Visual Studio 2026 and VS Code**: `JD-Xi-Studio.sln`, `.vscode/` (run, debug, tests, tasks on Windows, macOS and Linux),
  `building/windows/local_build.ps1` (exe and installer on your PC), guide in `doc/dev-windows.md`

# [1.0.0a1] — tag `v1.0.0-alpha.1` — 2026-11-11 (first JD-Xi Studio alpha: the new interface)

The interface is being rebuilt for a desktop screen, one editor at a time. The
last version with the original interface is **0.10.0b1** (tag `v0.10.0-beta.1`).
Principles for every new screen: every parameter of the manual has a control (a
test checks it); controls show what they do (graphs, drawn waveforms); the
parameter under the pointer is explained on screen; names, groups and order as
on the JD-Xi display.

### Analog Synth editor (new)

- **All 46 Analog parameters on one screen**, in six panels named and ordered as on the display:
  OSC, PITCH, FILTER, AMP, LFO, COMMON (plus Pitch Env Velocity Sens, which is in the MIDI
  Implementation but not on the display)
- **Graphic controls**: waveforms drawn on their buttons (PW-SQR follows Pulse Width), the low-pass
  response curve (drag sideways for Cutoff, up and down for Resonance), pitch, filter and amp
  envelopes with points to drag, the LFO over time with its fade-in
- **Knobs** with their value field: drag (Shift for fine steps), wheel, arrow keys or type the value
  as on the display (+12 st, -2 st, +50…); double-click returns a bipolar value to 0
- **Information panel**: name on the display, long name, value, range and unit, an explanation from
  the Parameter Guide (with its page) and what the parameter depends on
- **Settings without effect are greyed out**: Pulse Width and PWM Depth except with PW-SQR, the
  filter with BYPASS, Rate with Tempo Sync ON (and Sync Note with it OFF), Porta Time with Porta Sw OFF
- **Sending while dragging** at most every 25 ms, the last value always; values read from the JD-Xi
  are shown without being sent back
- Three columns on wide screens, two from 1280×720; the tone panel (presets, read from the JD-Xi,
  .syx, random tone) stays on the right
- The original Analog editor (`AnalogSynthEditor`) is still in the code; the app opens the new one

### Keyboard and editor windows, together

- **Minimise works on Windows**: the keyboard window (frameless) now has the minimise hints Windows
  needs, so its minimise button and the taskbar work
- **The editor windows follow the keyboard**: minimising the keyboard or an editor window minimises
  them all; restoring the keyboard (from the taskbar too) brings back the editors that were open
- **Each window moves on its own** (two screens work as expected); the editors window opens where
  it was left
- **The keyboard can come in front of the editors**: the editors window is no longer owned by the
  keyboard window (Windows keeps owned windows above their owner), so clicking either brings it in
  front; **Window → Show the keyboard** (Ctrl+Shift+K, from the editors too) and **Window → Keyboard
  always on top**; closing the keyboard closes the editors
- **Window → Line up the editors with the keyboard**: the editors window right above the keyboard
  (below it when there is no room)
- **Window → Show the editors** (Ctrl+Shift+W)
- **A maximised keyboard window keeps the instrument as it is**: panel and keys are one block of
  fixed size, centred, and the body grows around it (the Parts Select buttons, the wheels and the
  keyboard no longer come apart from the panel); the status bar shows only while it has a message

### Each editor in its own colour

- **The editor's name as a badge in its colour** at the top of each new editor
- **Digital Synth 1 red, Digital Synth 2 orange**, Drums purple, as on the JD-Xi panel; Effects teal,
  Vocal Effect pink (they shared colours with the parts before); the preset panel of Digital 2 says
  DIGITAL SYNTH 2

### Preset panel, Programs tabs and tool windows in the new look

- **The preset panel** beside the tone editors: a card in the editor's colour, flat buttons with
  icon and full name (Previous, Load, Next, Read from JD-Xi, Import/Export .syx)
- **The tabs under Programs** (Presets, User Programs, Playlist, Playlist Editor): flat buttons,
  dark tables, without the decorative icon rows; the preset form no wider than it needs
- **Log viewer, MIDI monitor, SysEx debugger and patch manager** in the same dark look

### JD-Xi Studio: a name of its own

- **The interface is called JD-Xi Studio**, an independent edition of JDXI-Editor by Mark Brooks,
  so the two are not confused: splash screen, window titles, the keyboard panel, the editors
  window, About, Preferences and the update messages; the origin is always shown ("based on
  JDXI-Editor by Mark Brooks" on the splash and in About, with the MIT licence)
- **Its own mark**, drawn in code: the four part colours as a step row over three keys (splash,
  About, window icon); the original logo stays with the original project
- The installer, the exe, the settings folder and the saved settings keep the original names, so
  nothing is lost when updating

### One language in the windows

- Buttons, labels, lists, table headers, placeholders and tooltips built by the shared widget
  helpers now go through the translation (Pattern, MIDI file player, Programs, playlists, presets,
  MIDI debugger, keyboard tooltips); in Italian there are no more half-English windows
- Parameter names (Cutoff, Porta Time, Rx Bank Sel...), the JD-Xi's own values (OFF/ON, LIGHT,
  MEDIUM, HEAVY), tone categories and the labels printed on the instrument stay as on the JD-Xi

### Editors window header and Settings (new)

- **The editors as a row of buttons** with short, translated names (Programs, Digital 1, Digital 2,
  Analog, Drums, Arpeggio, Effects, Vocal FX, Pattern, MIDI file, Settings…); the selected one in
  the editor's colour; on the right the program and tone last received and the connection state
- **Settings** (Edit → Settings…, Ctrl+Shift+E): the JD-Xi's System Common (Master Tune, Key Shift,
  Master Level, Program Control Channel 1–16/OFF, Rx Program Change, Rx Bank Select) and System
  Controller (Tx Program Change, Tx Bank Select, Keyboard Velocity, Velocity Curve and Offset),
  checked against the MIDI Implementation, read from the JD-Xi with one button; the MIDI connection
  and ports; files (load/save patch, send all, update user programs); preferences, updates, MIDI
  monitor, SysEx debugger and log
- The System Settings tab under Programs moved to Settings; the Program Control Channel follows the
  MIDI Implementation (0–15 = channels 1–16, 16 = OFF)
- Each new editor's badge shows its translated short name, as on its button

### Programs on one page (new layout)

- **Library**: every program (A–D preset, E–H user) in one table with number, name, genre and the
  four tones; search by name or number, genre, bank buttons A–H; a double click (or Load program)
  loads it, and the MIDI line shows its bank select and program change
- **Parts of the program**: the tone of Digital 1, Digital 2, Drums and Analog with their channels,
  updated when a program loads or a tone changes; a double click opens the part's editor
- **Mixer**: the original level strips and mutes on the same page
- **Rename…** and **Parts and advanced settings…** (opens Program: common and parts: level, pan,
  offsets, scale, receive switches, zones) next to the display
- **Below, in tabs**: Presets, User Programs, Playlist, Playlist Editor (the same widgets as before)

### Pattern and MIDI file player (new layout)

- **Same editors, same engine**: the sequencer, learning, measures, copy/paste, USB recorder,
  track classification, automation, A/B loop, trim, event suppression and transport work as before
- **Pattern laid out as in the mockup**: TRANSPORT (display, Play/Stop/Pause/Shuffle, BPM and Tap,
  steps), NEW STEPS (velocity, duration), MEASURES (add, copy previous, copy/paste a range), the STEP
  SEQUENCER across the window, FILE and the USB RECORDER always on show
- **MIDI file player laid out as in the mockup**: PLAYER (display, transport, load/save),
  CLASSIFICATION (with mute channels), TRACKS (position, timeline, lanes, zoom), PLAYBACK, AUTOMATION,
  USB RECORDER, EVENT FILTER
- **The new editors' look**: dark cards with the title in the accent colour (yellow for Pattern,
  blue for the player), flat buttons with icon and name; a pressed button (Play, Stop, Loop…) takes
  the accent colour
- The open editors are still found by class name, so the playlist, the patch manager and the
  Pattern ↔ player link keep working

### Recipes (new)

- **Parts → Recipes…** (Ctrl+Shift+R): step-by-step instructions to make a sound, as in the mockups
- **New recipe** three ways: the template (.xlsx with menus, or .csv; saved from the app), **import a
  file** (.xlsx, .csv, .md, .txt, .pdf) or a **table pasted** from a document or web page, or the
  **recipe editor** (menus offer only valid parts, groups and parameters; checked while you write)
- **Check** before use, row by row: recognized, to confirm (a similar name, a row with several
  parameters split, a default wave), to fix (out of range, unknown parameter, missing part or Su;
  with the closest name or value to use), by ear; text that is not a row is kept as notes; rows
  without a part take the starting tone's part
- **Guide**: one step at a time, the recipe's value next to the JD-Xi's with its state (done, in
  range, to set, by ear); set one row or all the missing values of a step (sent exactly as when the
  control is moved), go to the control, read the JD-Xi again; how to keep the sound with [Menu/Write]
- Values as on the display: numbers with sign or unit, option names, ranges (55–65), pan L20/20R,
  D50:50W, note values, tempo 120.5, PCM/drum waves and arpeggio styles by number, HF Damp in Hz
  (the nearest of the JD-Xi's values); "Su" chooses the partial (1-3, all when empty), the drum
  instrument and wave (SD1/W2) or the part (D1, AN...)
- **Library** of saved recipes (~/.jdxi_editor/recipes); **export** to the template .xlsx, .csv or
  Markdown; take the values of a recipe's rows from the JD-Xi
- Every name of the template is matched to a parameter of the new editors: checked by tests
- New dependencies: openpyxl (the .xlsx template) and pypdf (recipes in PDF files)

### Vocal Effect editor (new)

- **AutoPitch and Vocoder** with every parameter of Program Vocal Effect (MIDI Implementation) and the
  vocal effect settings of Program Common (effect, number, part, Auto Note), explained from the
  Parameter Guide (p. 9, 28); the output shared by both (level, pan, Output Assign, sends) apart
- Only the selected effect is active; the AutoPitch key on two rows, major and minor; the key only
  with Scale Maj(Min)
- Address 00 0F, listed in the MIDI Implementation without a name, is shown as such

### Arpeggio editor (new)

- **Every Program Controller parameter**: on/off, style (the 128 names), grid, duration, motif with
  the manual's explanation of the selected one, octave range, accent, velocity (REAL or fixed); the
  program tempo; and which parts the arpeggio plays (Program Zone)
- A timing view draws two beats of the grid: notes per beat, shuffle, how long and how loud each note is

### Drum Kit editor (new)

- **Every Drum Kit parameter** of the MIDI Implementation: kit name and level, and for each of the
  37 drum partials (keys 36-72) its name, common settings, the four waves (WMT), pitch, TVF and TVA,
  with the Parameter Guide explanations (p. 20-24); only WMT Wave Group Type (always 0) is left out
- The kit as a grid of 37 pads in keyboard order; the selected pad is edited in sections as on the
  display: **COMMON**, **WAVE** (the four waves side by side, wave lists by name, velocity range and
  fade drawn and draggable), **PITCH**, **TVF**, **TVA** (each envelope drawn: drag the points for
  time and level); a pad's page is built the first time it is opened
- Settings without effect greyed out: a wave's settings when it is off, velocity ranges when WMT Vel
  Ctrl is not ON, pitch and FXM with Wave Tempo Sync, FXM color/depth with FXM off, resonance with
  LPF2/LPF3, the filter with OFF, Rx Hold-1 with NO-SUS; velocity lower/upper follow each other (p. 21)
- Parameters past the 128th byte of a partial (pitch envelope onward, at 01 xx) are addressed in the
  next LMB, as the MIDI Implementation numbers them: checked by tests

### Patches and .syx with the new editors

- The new editors give each block as one DT1, as the JD-Xi sends it: patch saving, the part .syx
  export and "send all settings" use those messages (reserved bytes from the copy of the JD-Xi's
  memory when known)

### Digital Synth editor (new), for Digital 1 and Digital 2

- **Every parameter of the SuperNATURAL synth tone**: Common, Modify and the three Partials of the
  MIDI Implementation, with the explanations of the Parameter Guide (p. 15-19)
- Tone common settings on top (name, level, category, octave, bend range, mono/poly, legato,
  portamento, unison, ring modulator, wave shape, analog feel); the three partials switched on and
  off and selected for the panel knobs in a strip, as with the [01]-[07] buttons, and edited one at
  a time: **OSC** (waveforms drawn, PCM wave list and gain, pitch envelope), **FILTER** (response
  curve for LPF1-4/HPF/BPF/PKG and -12/-24 dB, drag cutoff and resonance; envelope), **AMP**
  (envelope, level, pan, key follow, aftertouch), **LFO** and **MODULATION LFO** (drawn), **MISC**
  (interval sensitivities, envelope loop, chromatic portamento)
- Settings without effect greyed out: pulse width only with PW-SQR (and not on partials 1-2 with the
  ring modulator on), Super Saw detune only with SP-SAW, wave number and gain only with PCM,
  variation not with SP-SAW/PCM, wave shape not with PW-SQR/SP-SAW on partial 1, legato only with
  MONO, unison size only with unison on, rate or sync note by tempo sync, filter settings with BYPASS
- The tone preset panel (presets, read from JD-Xi, .syx import/export) is the existing one, on the side
- Key Follow -100..+100 in steps of 10, Ring Switch sent as 0/2, wave number as 4 nibbles: checked by tests

### Program editor (new): common settings and the four parts

- **Parts → Program: common and parts** (Ctrl+Shift+P): program name, level and tempo (5.00-300.00),
  vocal effect selection, and **every Program Part and Zone parameter** of the MIDI Implementation for
  Digital 1, Digital 2, Analog and Drums: the 52 part parameters the app could not edit before
- The four parts side by side, like a mixer, one section at a time as on the display: **MAIN** (level,
  mute, pan L64-63R, Part Output, sends, mono/poly, legato), **PITCH** (octave, coarse/fine tune, bend
  range, portamento with TONE), **OFFSET** (cutoff, resonance, envelope and vibrato offsets),
  **KEYBOARD** (velocity range and fades with a draggable graph, velocity sensitivity, zone octave,
  arpeggio on/off), **SCALE** (scale tune type, key and the twelve notes, drag the bars), **MIDI**
  (part on/off, receive channel, tone bank/number, the ten receive switches)
- Sends greyed out when Part Output makes them useless (REV, DIR, KIT); velocity lower/upper kept in order
- The program name is sent as one message (12 characters)
- **Values from the JD-Xi are read straight from its DT1 messages** (whole blocks and single
  parameters turned on the panel), for this and the Effects editor; 2-nibble parameters (Part
  Portamento Time) are now sent and read correctly

### Effects editor (new)

- **Effect 1, Effect 2, Delay and Reverb on one screen**, with every parameter of the Parameter Guide
  (p. 26-27) and the Version 1.50 side-chain compressor (Side Switch, Level, Note, Time, Release, Sync)
- **Signal chain** at the top: the selected types and how Effect 1 is connected (Output Assign DIR or
  EFX2, in series); click a block to go to its settings
- **Only the parameters of the selected type** are shown, as on the display; when the type changes
  the editor reads the block back, since the JD-Xi loads that type's own settings
- **Graphs**: the delay echoes over time (time or note, feedback, PAN with Tap Time on the left
  channel, level) and the compressor curve (drag the threshold)
- **Right addresses and encoding** from the MIDI Implementation, checked by tests: 4-nibble effect
  parameters (32768 = 0) at 00 11 + 4(n-1), Effect 2 types sent as 0, 5-8, delay time in ms; the
  delay and reverb levels the panel knobs set are Delay/Reverb Parameter 8/4, the block levels at 00 01
  (MIDI only) are shown apart
- Settings without effect greyed out (Rate or Note, Time or Note, Tap Time only with PAN, side chain
  with Side Switch OFF); parameter numbers that come from the JD-Xi Manager and not from a Roland
  document are marked on screen (Phaser Manual/Level, Ring Mod, Slicer, Side Time units)
- A common base (`jdxi_editor/ui/v2/framework.py`) describes parameters as data (address, encoding,
  range, explanation): the next editors are built on it
- The original effects editor (`EffectsCommonEditor`) is still in the code; the app opens the new one

### Start-up and CI

- **The USB recorder starts PortAudio only when it is used**, not when the MIDI file player and the
  pattern editor are created: starting it lists every audio driver (seconds on some Windows machines)
  and failed on machines without an audio system, which broke 59 tests on the GitHub runners. Its device
  list is filled when the recorder is first shown; without an audio system it is simply empty

### Instrument window

- **Minimise, maximise and close** buttons at the right of the menu bar, in the panel's colours; the
  empty part of the menu bar moves the window and maximises it on double-click

### Languages

- The tone panel (preset list, Previous/Load/Next, Read from JD-Xi, .syx, Random) is translated too

# [0.10.0b1] — tag `v0.10.0-beta.1` (beta, not released yet)

First version of this repository as an **independent fork** of
[markxbrooks/JDXI-Editor](https://github.com/markxbrooks/JDXI-Editor) (last
release there: 0.9.9). Versions continue from 0.9.9: 0.10.x betas with the
current interface, 1.0 with the new one.

### Fork

- **Update check** (Help › Check for Updates) asks this repository's releases, not the original's.
  A beta copy is told about newer betas; a final release only about final releases. Versions such as
  `v0.10.0-beta.2`, `0.10.0b2` and `v0.10.0-rc.1` now compare in release order (before, `0.10.0b1`
  counted as `0.10.0`)
- **pip installs** are upgraded from GitHub (`pip install -U git+https://github.com/emanuelemerlo/JDXI-Editor.git`):
  the `JDXI-Editor` package on PyPI is the original project. The PyPI publishing workflow only runs by hand
- **About** and **Help › Documentation** link to this repository and credit the original project;
  `pyproject.toml` URLs and maintainer updated
- **Windows build**: the installer and the portable app are two separate downloads, both as CI
  artifacts (`…-win64-setup`, `…-win64-portable`, the latter the app folder itself, not a zip in a zip)
  and as release assets
- **README, README.rst and doc/installation.rst** describe the fork, its Windows builds and how to install
  it from GitHub

### MIDI connection dialog

- **Redesigned and no longer freezes.** It opened FluidSynth and loaded its SoundFont (FluidR3_GM is
  140 MB) as it appeared, and listed the audio devices through PortAudio, all on the interface thread:
  the window showed "Not responding" for seconds. Now it opens at once; ports, audio devices and
  SoundFonts are listed in the background, FluidSynth starts only on "Start", in the background
- **Status at the top**: "Connected: the JD-Xi replies", "No reply…", "No JD-Xi among the MIDI ports".
  **Test connection** sends an Identity Request and waits for the reply with a timer (1.5 s), recognising
  the JD-Xi from its reply; another instrument (or Microsoft GS Wavetable Synth) is reported as such
- **Find the JD-Xi** picks its ports; JD-Xi ports are listed first and marked ★. The FluidSynth section
  ("Listen without the JD-Xi") stays closed unless in use. Standard OK/Cancel buttons; changed ports are
  reopened after the dialog closes. All texts translated

### Languages

- **Interface in English and Italian**, chosen in Help › Preferences › Interface language
  ("Same as the system", English, Italiano); it applies at the next start. `JDXI_LANGUAGE=it` overrides it
- Menus, dialogs, messages, tooltips and editor titles go through `jdxi_editor.i18n.tr()` (372 strings);
  Qt's own buttons and file dialogs use Qt's catalogue for the same language. Parameter names stay as on
  the JD-Xi display, as in Roland's manuals
- `python -m building.i18n update | compile | check` keeps the Qt Linguist catalogues
  (`jdxi_editor/i18n/*.ts` and `.qm`) in step with the code; `tests/test_i18n.py` fails on an
  untranslated string, a lost placeholder or a stale `.qm`

## Checked against the manuals

Checked against Roland's JD-Xi Parameter Guide (preset lists, pp. 44–47) and
MIDI Implementation (parameter address map).

### Fixed

- **Digital presets 070–074** loaded the sounds of 084–088 (wrong name and PC in `PROGRAM_CHANGE` and `LIST`); `LIST` lacked 075–088 and `ENUMERATED` lacked 256 "Init Tone"
- **Analog presets**: 16 presets (003–006, 010, 013–017, 019–021, 025–027) and 064 "Init Tone" were missing; 002 "Sub Bass 1" and 012 "Dist TB Bs 1" sent PC 6 and 17
- **Drum kits** 13–25 and 30 were missing from `PROGRAM_CHANGE`
- **Program Common addresses**: Program Tempo at `00 11` (was the reserved `00 17`), Vocal Effect at `00 16` (was `00 1C`), Vocal Effect Number at `00 1C` (was the reserved `00 1B`). The earlier values came from `doc/midi_parameters.txt`, whose Program Common rows were shifted; that file now matches the manual
- **Auto Note Switch**: ON was turned into 2 and rejected by the range check
- **MidiIOHelper**: a failed start (no MIDI backend) no longer leaves a half-initialized singleton that raises "can't initialize QObject twice" on the next attempt
- **JDXiPresetData.get_preset_details**: bank select and PC come from the preset tables (was MSB `0x10`, LSB `n // 16`)
- **Last preset name**: a stored preset number of 0 showed the last preset instead of "INIT PATCH"
- **Drum partials**: removed "C#5"; the JD-Xi has 37 partials, keys 36–72
- Removed `midi/data/parameter/program/controller.py`, which raised `TypeError` on import (`ArpeggioParam` covers Program Controller)
- **No MIDI backend**: without a MIDI API (Linux with no ALSA sequencer, containers, WSL) the editor crashed at startup; it now runs offline on null ports and says so in a message and in the status bar
- **MIDI configuration dialog**: opened without blocking (`open()` instead of `exec()`), after the main window is shown; the port indicators update when it closes, and asking again brings the open dialog forward
- **Sliders sent every change twice**: `Slider.valueChanged` was connected twice, so each move sent its SysEx twice. It is sent once, and while the handle is dragged at most every 25 ms (first move and release at once), so the JD-Xi keeps up with a fast drag
- **Analog waveform sent twice**: the waveform buttons and the editor callback both sent OSC_WAVEFORM; `ModeButtonGroup` also re-entered itself when re-checking its buttons
- **Round buttons**: a click on the icon and label next to a round button now clicks it (it used to react only on the 30 px circle); action buttons built from a ButtonSpec are no longer checkable by default, so they do not stay lit
- **Program page**: the program picker was recreated on load and inserted at the wrong place, so two pickers were drawn on top of each other; it is now refilled in place (`SearchableFilterableComboBox.set_banks`, `always_show_filters`)
- `create_centered_layout_with_widgets` added the layout to itself (12 "QLayout: Cannot add layout to itself" warnings), so nothing was centred
- Tab titles showed "Effects 1_2", "Delay_Reverb", "Programs _Presets": a single "&" is a Qt shortcut marker
- Effects labels follow the Parameter Guide ("Level", "Delay Send Level", "Balance (D:W)" … instead of "Efx1 Level", "EFX1 Delay Send Level (0-127)")
- Removed the decorative pictures (Jupiter-8, TR-909, effects artwork) beside the preset panels and in the simple editors
- EFX1 Delay Send Level label; missing `SysExSection` import in two test scripts; `imp` (removed in Python 3.12) in the py2app includes

### Added

- `tests/fixtures/jdxi_manual_presets.json`: the preset lists from the Parameter Guide, with tests that keep every preset table in step with it and check the Program Common addresses
- **Windows build**: `building/windows/jdxi_editor.spec` (PyInstaller, one folder) and the `Windows build` workflow, which builds the app and the Inno Setup installer, checks that the app starts, and attaches both to a pre-release on `v*` tags. `jdxi_editor.iss` takes the version from the build and installs per user, in English or Italian

### Changed

- `doc/midi_parameters.txt`: Program Common rows corrected against the MIDI Implementation (the rest of the file already matched); the vocal-effects address map, gap analyses and migration plan updated to match
- Installation docs and READMEs: Windows installer and portable zip, SmartScreen note, Python 3.10+ (3.13 added to the classifiers)
- `pyproject.toml`: `audio` extra (soundfile, librosa) and both in `dev`, since the audio-evidence tests import them; `build-windows` extra (PyInstaller)
- `tests/test_ui_responsiveness.py`: one MIDI message per control change, slider drag throttling, clickable labels, centred layout
- Tests run on in-memory MIDI ports (`tests/conftest.py`) that show a "JD-Xi" port, so they no longer need a MIDI driver or hardware; `pytest -m hardware` or `JDXI_TEST_REAL_MIDI=1` uses the real ports. `test_channel_edit_applies_after_delay` waits for the result instead of a fixed 500 ms, which was too short after other Qt-heavy tests
- Tests that need `tests/sheep.mid` (not in the repository) are marked `slow`, like the others that use it, so the default run no longer fails on them
- `python -m building.buildsys` on Windows passes the version to Inno Setup; removed the outdated copy `building/windows/jdxi_editor.iss` (0.9.2)

# [0.9.9] — 2026-11
Bumping version for PyPi

# [0.9.8] — 2026-11

### Refreshed UI (UI_CRITIQUE)

- **AppEditorStyle**: Shared restrained editor chrome (grey idle borders, soft sliders; accent only for focus/active) used app-wide via `Theme.apply_editor_style`
- **MidiPlayerStyle / PatternEditorStyle**: Subclass the shared chrome; muted timeline colours, two-line track headers, bar/beat ruler
- **Identity tokens**: Metallic red `#A71920`, illuminated accent `#E04435`, LCD orange `#FF6A00` in `AppEditorStyle` and `JDXiUIStyle`
- **Signature LCD**: `DigitalDisplay` / `DigitalTitle` JD-Xi-style panel; optional `BANK msb/lsb · PC n` line wired from tone selection
- **Tabs**: Underline selection (metallic red / Analog cyan) instead of full red box borders; main editor and section `TAB_TITLE` aligned
- **Preset workspace**: Top-aligned Digital/Analog/Drum preset + instrument image row; frameless instrument overview (no heavy inset card)
- **Selection / MIDI wire**: Slim `MidiWireInfo` (channel, bank, program); `MidiSelectionInfoBar` syncs LCD detail on preset change
- **Drum partial SysEx**: Pass `address` + `send_midi_parameter` into Pitch Env, Partial, Output, TVF, and TVA sections (fixes failed sends such as `PITCH_ENV_TIME_4_VELOCITY_SENS`); harden QWidget parent address lookup

# [0.9.7] — 2026-06

Interim release between Effects/Vocal/Pattern work (0.9.6) and the UI refresh (0.9.8).

# [0.9.6] — 2026-03

### Arpeggiator SysEx Sync

- **PARAMETER_ADDRESS_NAME_MAP**: Added `(TEMPORARY_PROGRAM, CONTROLLER)` → `ArpeggioParam` for correct Program Controller parsing
- **Phase 4**: Fixed ComboBox vs Slider value handling in `_dispatch_sysex_to_area` (ComboBox uses raw MIDI value; Slider uses display value)
- **helper.py**: Added CONTROLLER handling for `send_json_patch_to_instrument` (Arpeggio patch apply)
- **ArpeggioParam.get_by_name**: Added for param resolution in SysEx dispatcher
- **MidiRequests.PROGRAM_CONTROLLER**: RQ1 request for address 18 00 40 00, size 0x0C (12 bytes)
- **ArpeggioEditor**: `midi_requests`, `showEvent` → `data_request`, `midi_sysex_json` → `_dispatch_sysex_to_area`
- **Bidirectional SysEx**: Arpeggio Editor now receives and displays incoming Program Controller SysEx; requests data on show

### Effects Editor (Phases 1–6)

- **Data layer**: Added Delay/Reverb parameters (On/Off, Type, HF Damp, Time/Note mode), Compressor Side Chain/Side Sync, coarse_tune for Side Note
- **Delay & Reverb UI**: Full parameter set with Time/Note mode, Note dropdown, HF Damp
- **Compressor**: Side Chain, Side Sync switches; Side Note as coarse_tune combo
- **Polymorphic sections**: Effect 1 and Effect 2 use QStackedWidget—one page per effect type; no more show/hide
- **Layout**: 2-column grid (EFX1|EFX2, Delay|Reverb) via SimpleEditorHelper layout_mode="grid"
- **Phaser**: Renamed "Center Freq" to "Resonance" (0x21)
- **Polish**: Tooltips for key controls; "Balance [dry->wet]" labeling
- **Cleanup**: Removed efx1_param_labels, efx2_param_labels; fixed Phaser docstrings

### Vocal Effects (Phase 1)

- **Program Common addresses**: VOCAL_EFFECT 0x16→0x1C (per JD-Xi guide); VOCAL_EFFECT_NUMBER→0x1B (placeholder, undocumented)
- **SysEx routing**: apply_lmb_offset routes ProgramCommonParam to LMB=COMMON
- **VocalFXParam**: Fixed convert_to_midi/convert_from_midi for Pan, Gender, Octave; convert_from_display delegates to convert_to_midi
- **VocalEffectsData**: Tooltips for all vocal effect controls; "Balance [dry→wet]" label

### Vocal Effects (Phase 2)

- **data_request on show**: showEvent requests PROGRAM_COMMON and PROGRAM_VOCAL_EFFECT; MidiRequests.PROGRAM_VOCAL_EFFECT added
- **SysEx receive**: _dispatch_sysex_to_area updates controls from COMMON and VOCAL_EFFECT; JDXiMapSynthTone 0x01→VOCAL_EFFECT
- **VocalFXParam.get_by_name**: Added for param resolution in dispatcher

### Vocal Effects (Phase 3)

- **Polymorphic UI**: QStackedWidget for OFF/VOCODER/AUTO-PITCH; Vocal Effect combo switches stack page
- **Tab structure**: 3 tabs — Common, Vocoder & Auto Pitch, Mixer (replaces 4-tab layout)
- **Effect Part**: VOCAL_EFFECT_PART (Part 1/Part 2) in Common; removed VOCODER_SWITCH from Common

### Pattern Editor — MIDI Load/Save (Phases 1–4)

- **Phase 1 — Button selectability**: `_update_button_states_for_beats_per_measure` after load; `ensure_measure_count` for measures; `_wire_button_clicks` on all measures
- **Phase 2 — Data consistency**: `sync_measure_to_ui` after load and on edit; `PatternMeasure.steps` kept in sync with button state for copy/paste
- **Phase 3 — MIDI state alignment**: PPQ synced from loaded file; `_calculate_note_on_time` and save use correct `ticks_per_beat`; `save_pattern` preserves loaded file PPQ
- **Phase 4 — Save UX**: Save dialog pre-fills with loaded file path when loading from MidiFileEditor or Load; `_pattern_file_path` set from `midi_file.filename` when available
- **Tooltips on load**: Active notes show note names (e.g. C4, CLAP) in tooltips after MIDI file load
- **Drum name conversion**: `MidiNoteConverter.note_name_to_midi` handles drum names (CLAP, BD1, etc.) with JD-Xi fallback when `drum_options` empty
- **SequencerButton**: Fixed `note_duration`/`duration_ms` when `duration_ms` is None; added `duration_ms` property for pattern/manager compatibility

---

🎹 **SoundFonts & Pattern Editor Refinement Release**

This release introduces major improvements to the **SoundFont playback system**, continued development of the **Pattern Editor**, and extensive internal UI and codebase refinements.

## Added

### SoundFont Integration
- Added **SoundFont (.sf2 / .sf3) support**
- Ability to **load and browse SoundFont instruments**
- Use SoundFonts as a **virtual instrument backend**
- Enables MIDI playback and sequencing **without requiring a physical JD-Xi**
- Integration with **FluidSynth for audio playback**
- SoundFont preset list extraction and instrument selection

### Pattern Editor
- Expanded **Pattern Sequencer / Pattern Editor**
- **MIDI load/save**: Load from MidiFileEditor or file; edit steps; save back to same file with correct PPQ
- Improved step editing workflow and pattern playback timing
- **Part muting** for the four parts; **USB File Recording** widget
- Tooltips show note names (C4, CLAP, etc.) on loaded and edited steps
- Continued development of **grid-based sequencing tools**
- Foundations for future advanced sequencing features

### UI Enhancements
- Added **parameter plot widgets** for visual feedback
- Improved splash screen
- New instrument image handling for presets and parts
- Automatic instrument image loading
- Visual distinction between synth parts and drum kits

---

## Changed

### UI Improvements
- Improved spacing, margins, and layout consistency
- Updated section grouping and visual organization
- Switched application font to **Segoe UI**
- More consistent control panel styling

### Editor Components
- Refined slider and switch widget behavior
- Improvements to Program Editor sliders
- Improvements to Drum Editor layout and controls
- Updated UI margins and spacing across several windows

### MIDI Player
- Improved **MIDI channel detection**
- Automatic drum channel assignment to **Channel 10**
- Detection of:
  - bass instruments
  - guitars
  - keyboards
  - strings
- Automatic assignment to synth parts (channels 1–3)

---

## Refactored

### Core Architecture
Major internal refactoring was performed to improve maintainability.

- Expanded **ControlsRegistry** system for tracking UI controls
- Cleaner separation between:
  - UI layout
  - widget construction
  - MIDI / SysEx logic
- Adoption of **table-driven and data-model based patterns**
- Reduced duplication across synth editor components

### Codebase Improvements
- Improved handling of:
  - sliders
  - switches
  - parameter widgets
- Additional type hints and docstrings
- Continued restructuring of UI code in `picoui`
- Improved internal module organization

---

## Fixed

- Various UI inconsistencies across editor panels
- Improved preset loading reliability
- Reduced errors when switching programs rapidly
- Improved UI synchronization with JD-Xi state
- Fixes related to Program Editor slider behavior
- General stability improvements

---

# [0.9.5] — 2026-02
🎛️ **Editor and MIDI System Improvements**

## Added
- Improved **Arpeggiator SysEx synchronization**
- Effects editor enhancements
- Vocal effects editing improvements
- Improved patch loading and saving

## Supported Patch Formats
- `.jsz`
- `.msz`
- `.json`
- `.syx`

## Improvements
- MIDI debugging tools
- Parameter visualization
- Editor UI improvements

---

# [0.9.4] — 2026-02
🎹 **Major Code & UI Refinement Release**

## Major Code Improvements
- Substantial internal refactoring for improved maintainability and extensibility
- Cleaner separation between UI layout, widget construction, and MIDI logic
- Table-driven and data-model-based approaches adopted in several core areas
- Reduced duplication and more consistent editor patterns across synth sections

## UI & Layout Enhancements
- Improved spacing, alignment, and visual balance across the application
- Improved splash screen
- New Plot widgets for clearer visual feedback and parameter visualization
- More consistent use of reusable section and control widgets
- Overall UI feels more polished, legible, and "instrument-like"

## New Application Font
- Switched to **Segoe UI** for improved readability and a more modern, native look across platforms

## Instrument Images & Visual Identity
- Added instrument images for presets and parts
- Automatic image loading based on detected instrument type
- Graceful fallback when a specific image is unavailable
- Clear visual distinction between synth parts and drum kits

## Pattern Editor
- Improved workflow and usability
- Better visual structure and control grouping
- Continued groundwork for future sequencing enhancements

## MIDI File Player
- Drum detection and assignment to MIDI Channel 10
- Bass, Guitar/Keys & strings channel detection, assignment to Channels 1–3

## Preset & Program Handling
- Improved preset loading reliability
- More robust program loading and switching
- Fewer edge-case failures when changing parts or programs
- Better synchronization between UI state and JD-Xi internal state

## Fixed
- Numerous bug fixes across editors and supporting code
- Improved error handling and logging
- Reduced UI inconsistencies during rapid parameter changes

---

# [0.9.3] — 2026-01
🎹 **Major Code & UI Refinement Release**

## Major Code Improvements
- Substantial internal refactoring for improved maintainability and extensibility
- Cleaner separation between UI layout, widget construction, and MIDI logic
- Table-driven and data-model-based approaches adopted in several core areas
- Reduced duplication and more consistent editor patterns across synth sections

## UI & Layout Enhancements
- Improved spacing, alignment, and visual balance across the application
- Improved splash screen
- New Plot widgets for clearer visual feedback and parameter visualization
- More consistent use of reusable section and control widgets

## New Application Font
- Switched to **Segoe UI** for improved readability and a more modern, native look across platforms

## Instrument Images & Visual Identity
- Added instrument images for presets and parts
- Automatic image loading based on detected instrument type
- Graceful fallback when a specific image is unavailable
- Clear visual distinction between synth parts and drum kits

## Pattern Editor
- Improved workflow and usability
- Better visual structure and control grouping
- Continued groundwork for future sequencing enhancements

## MIDI File Player
- Drum detection and assignment to MIDI Channel 10
- Bass, Guitar/Keys & strings channel detection, assignment to Channels 1–3

## Preset & Program Handling
- Improved preset loading reliability
- More robust program loading and switching
- Fewer edge-case failures when changing parts or programs
- Better synchronization between UI state and JD-Xi internal state

## Fixed
- Numerous bug fixes across editors and supporting code
- Improved error handling and logging
- Reduced UI inconsistencies during rapid parameter changes

---

# [0.9.2] — 2026-01
🎹 **Major Feature Update + Expanded MIDI Support**

## New Builds
- macOS build available — packaged installer, no manual Python setup required
- Linux build available — .deb packaged installer and AppImage, built on Ubuntu 24.04
- Windows installer available (built via PyInstaller + Inno Setup)

## Better Playlist Editing
- Debugged the editing of existing Playlist Items
- Improved database backend code

## MIDI File Player Improvements
- Added "Detect Drum tracks" button to detect drums and save them as MIDI Channel 10
- Added "Classify Tracks" button to classify tracks as Bass, Piano/Guitars or Strings, and save as MIDI Channels 1, 2 or 3
- Drag and drop of MIDI tracks to sort and group tracks

## Improved Styling
- Icons for every tab
- Reusable widgets added for each page, giving a more harmonised appearance

## Improved Pattern Sequencer
- Can add bars and copy from previous bars
- More work planned for the sequencer

## MIDI File Support
- Load and play MIDI files directly in the editor
- Built-in Playlist Editor & Database
- Manage Playlists and Tracks per Playlist
- Select, play, and record tracks from the list
- Edit MIDI channel assignments
- Delete or reorder tracks
- Save modified MIDI files with automatic naming

## Digital Synth Editing
- Full editing support for all four digital parts, including partials

## Drum Editing — Vastly Improved
- Redesigned Drum Editor with clearer layout and control flow
- Improved parameter organization across drum partials
- More consistent mapping between kit parameters and MIDI behavior
- Better usability when editing multiple drum sounds

## Envelope Enhancements
- Added ADSR-style envelopes for Pitch, WMT, TVA, TVF
- Includes visual envelope displays for intuitive editing

## General Improvements
- New Splash screen
- User Programs Librarian & Database
- Select programs from a searchable list
- Integrated cheat-code workflow
- Enhanced playback slider and MIDI handling
- Cleaner, more reliable build system

---

# [0.9.1] — 2026-01
🎹 **Major Feature Update + Expanded MIDI Support**

## New Builds
- macOS build available — packaged installer, no manual Python setup required
- Linux build available — .deb packaged installer and AppImage, built on Ubuntu 24.04
- Windows installer available (built via PyInstaller + Inno Setup)

## MIDI File Support
- Load and play MIDI files directly in the editor
- Built-in Playlist Editor & Database
- Manage Playlists and Tracks per Playlist
- Select, play, and record tracks from the list
- Edit MIDI channel assignments
- Delete or reorder tracks
- Save modified MIDI files with automatic naming

## Digital Synth Editing
- Full editing support for all four digital parts, including partials

## Drum Editing — Vastly Improved
- Redesigned Drum Editor with clearer layout and control flow
- Improved parameter organization across drum partials
- More consistent mapping between kit parameters and MIDI behavior
- Better usability when editing multiple drum sounds

## Envelope Enhancements
- Added ADSR-style envelopes for Pitch, WMT, TVA, TVF
- Includes visual envelope displays for intuitive editing

## General Improvements
- New Splash screen
- User Programs Librarian & Database
- Select programs from a searchable list
- Integrated cheat-code workflow
- Enhanced playback slider and MIDI handling
- Cleaner, more reliable build system

---

# [0.9] — 2025-12
🎹 **Major Feature Update + Expanded MIDI Support**

## New Builds
- macOS build available — packaged installer, no manual Python setup required
- Linux build available — .deb packaged installer and AppImage, built on Ubuntu 24.04
- Windows installer available (built via PyInstaller + Inno Setup)

## MIDI File Support
- Load and play MIDI files directly in the editor
- Built-in Playlist Editor & Database
- Manage Playlists and Tracks per Playlist
- Select, play, and record tracks from the list
- Edit MIDI channel assignments
- Delete or reorder tracks
- Save modified MIDI files with automatic naming

## Digital Synth Editing
- Full editing support for all four digital parts, including partials

## Drum Editing — Vastly Improved
- Redesigned Drum Editor with clearer layout and control flow
- Improved parameter organization across drum partials
- More consistent mapping between kit parameters and MIDI behavior
- Better usability when editing multiple drum sounds

## Envelope Enhancements
- Added ADSR-style envelopes for Pitch, WMT, TVA, TVF
- Includes visual envelope displays for intuitive editing

## General Improvements
- User Programs Librarian & Database
- Select programs from a searchable list
- Integrated cheat-code workflow
- Enhanced playback slider and MIDI handling
- Cleaner, more reliable build system

---

# [0.8] — 2025-09
🎹 **New Windows Build + Major Feature Updates**

## New Builds
- **Windows build available** — packaged installer, no need to set up Python manually
- macOS and Linux builds also available

## MIDI File Support
- Load and play MIDI files directly in the editor
- Edit channel numbers
- Save modified MIDI files for playback

## Digital Synth Editing
- All 4 digital parts now fully editable, including partials

## General Improvements
- More stable UI across platforms
- Improved playback slider and MIDI handling
- Cleaner build system with PyInstaller + Inno Setup for Windows

## Notes
- Some features like the full Pattern Sequencer and PW display were still in progress

---

# [0.6.0] — 2025-05 (Beta)
🎹 **First Public Beta for macOS Sequoia**

## What's New
- Universal binary for macOS Sequoia (Intel & M1/M2/M3)
- Fully redesigned editor UI with improved layout
- Real-time MIDI feedback and enhanced control mapping
- Modular synth editors for Digital, Analog, and Drum sections

## Known Limitation
- Patch saving not yet implemented for drums

---

# [0.4.0] — 2025-05 (Beta)
🎹 **First Public Beta for macOS Sequoia**

## What's New
- Universal binary for macOS Sequoia (Intel & M1/M2/M3)
- Fully redesigned editor UI with improved layout
- Real-time MIDI feedback and enhanced control mapping
- Modular synth editors for Digital, Analog, and Drum sections

## Known Limitation
- Patch saving not yet implemented

---

# Core Features

JDXI-Editor provides a software editing environment for the **Roland JD-Xi synthesizer**, allowing deeper control than the hardware interface alone.

### Synth Editing
- Digital Synth Parts 1 & 2
- Three partials per digital synth
- Analog Synth Editor
- Drum Part Editor

### Effects
- Reverb
- Delay
- Vocoder
- Arpeggiator

### MIDI Tools
- MIDI debugger
- MIDI file player
- MIDI playlist support
- Pattern sequencing tools

### Interface
- JD-Xi style LCD display
- On-screen keyboard
- Preset browser with search
- Envelope visualizations (ADSR, pitch)

---

# Changelog

All notable changes to **JDXI-Editor** will be documented in this file.

The format loosely follows **Keep a Changelog**, and the project adheres to **semantic-ish versioning** while still in the 0.x development phase.

---

# Project

**JDXI-Editor** is a cross-platform MIDI editor built using:

- **Python**
- **Qt / PySide**
- **RtMidi**
- **Mido**

It aims to implement as much of the **Roland JD-Xi MIDI implementation** as possible, providing a modern graphical interface for sound editing, sequencing, and MIDI experimentation.

---

# Links

Repository  
https://github.com/markxbrooks/JDXI-Editor

Documentation  
https://markxbrooks.github.io/JDXI-Editor/
