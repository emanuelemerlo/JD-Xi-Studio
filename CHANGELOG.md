# Changelog

All notable changes to JDXI-Editor are documented in this file.

# [1.0.0a1] — tag `v1.0.0-alpha.1` (new interface, in progress)

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
- **Window → Show the editors** (Ctrl+Shift+W); the panel keeps its size and stays centred when
  the keyboard window is maximised

### Each editor in its own colour

- **The editor's name as a badge in its colour** at the top of each new editor
- **Digital Synth 1 red, Digital Synth 2 orange**, Drums purple, as on the JD-Xi panel; Effects teal,
  Vocal Effect pink (they shared colours with the parts before); the preset panel of Digital 2 says
  DIGITAL SYNTH 2

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
