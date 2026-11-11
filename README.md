# JDXi-Editor

![Roland JD-Xi Cartoon](resources/JDXI-Editor_logo_640.png)

**JDXi-Editor**: The missing MIDI editor for the **Roland JD-Xi synthesizer**

> **This is an independent fork** of [JDXI-Editor](https://github.com/markxbrooks/JDXI-Editor) by Mark Brooks (MIT licence).
> It goes its own way: the presets and SysEx addresses are checked against Roland's manuals, the editor runs
> without a JD-Xi (offline mode), Windows builds come from CI, and the interface is translated (English, Italiano).
> A new interface for desktop screens is being built, one editor at a time (version 1.0, starting with
> the Analog editor): every parameter of the manual on screen, graphic controls, and an explanation of
> the parameter under the pointer. The last version with the original interface is 0.10.0 beta
> (tag `v0.10.0-beta.1`). Releases, issues and the update check of the app use this repository.


## Unleash the hidden power of your Roland JD-Xi. 
- Stop fighting menus and start creating. 
- JDXi-Editor puts every sound, control, and performance tool right at your fingertips—fast, visual, and effortless. 
- Shape your tones, browse and save presets, build playlists, and take full command of your synth without breaking your creative flow. 
- Wherever you create—from your home studio to late-night sessions—this is the editor your JD-Xi has always deserved.
- Designed to implement as many features as possible from Roland’s MIDI implementation—without the need to dive through hardware menus. 🎛️

---

## 🎛️ Features of JDXI-Editor for Roland JD-Xi Synthesizer
- **On-Screen Keyboard**: Easily play and test sounds from your JD-Xi.
- **Preset Selection with Search**: Quickly find and load presets.
- **Octave Shifting**: Adjust octave ranges for precise sound control.
- **Digital & Analog Synth Editors**: Edit JD-Xi's digital and analog synths directly.
- **Drum Part Editor**: Customize drum sounds and patterns 🥁.
- **Effects Editor**: Edit reverb, delay, compressor, phaser, and arpeggiator settings.
- **Vocal Effects Editor**: Vocoder and Auto-Pitch with polymorphic UI.
- **Pattern Editor**: 4×16 step sequencer with MIDI load/save, part muting, and USB recording.
- **MIDI File Player**: Load MIDI files, classify tracks, assign channels, play with JD-Xi or FluidSynth.
- **SoundFont Support**: Use .sf2/.sf3 for playback without hardware.
- **MIDI Debugger**: Monitor and debug MIDI messages efficiently.
- **New Analog editor** (1.0): all 46 parameters on one screen, filter curve and envelopes to drag,
  drawn waveforms, and an information panel that explains the parameter under the pointer.
- **Recipes** (1.0): import a recipe (template .xlsx/.csv, Markdown, text, PDF or a pasted table),
  check it row by row, then follow it step by step with the JD-Xi's values next to the recipe's.
- **New Vocal Effect and Arpeggio editors** (1.0): AutoPitch and Vocoder with every parameter; the
  arpeggio with its timing drawn and the parts it plays.
- **New Drum Kit editor** (1.0): the 37 drum partials as pads, each with its four waves, pitch,
  filter and amplifier envelopes drawn and draggable.
- **New Digital Synth editor** (1.0), for Digital 1 and 2: every SuperNATURAL synth parameter, the
  three partials with drawn waveforms, filter curves, envelopes and LFOs.
- **Keyboard and editors together** (1.0): the editor windows minimise, come back and move with
  the keyboard window; Window → Line up places them right above it.
- **Pattern and MIDI file player in the new look** (1.0): same functions and engine, with the
  new editors' dark cards and flat buttons with icon and name.
- **New Program editor** (1.0): program name, level, tempo and the four parts side by side (main,
  pitch, offsets, velocity range, scale tune, MIDI receive) with every Program Part parameter.
- **New Effects editor** (1.0): Effect 1, Effect 2, Delay and Reverb with every parameter of the
  manual (side-chain compressor included), the signal chain, the delay echoes and compressor curve.
- **Languages**: English and Italian, chosen in Preferences (see [Languages](#-languages)).
- **Offline mode**: opens and edits without a JD-Xi or a MIDI system; it connects when one is available.

---

Designed for musicians, sound designers, and MIDI enthusiasts looking to unlock the full potential of the Roland JD-Xi synthesizer!

### 🖥️ 'Keyboard Window' Screenshot

<a href="resources/main_window_0.6.gif" rel="Current view of the Roland JD-Xi Editor App">
  <img src="resources/main_window_0.6.gif" alt="Roland JD-Xi Main Editor Window" />
</a>

---
## 🎥 Watch JDXI-Editor in Action

Check out some great performances and demos of the Roland JD-Xi:

- 🎹 [Pink Floyd – *Sheep* 🐑 on the Roland JD-Xi](https://www.youtube.com/watch?v=vh-i8eb2SYQ)  
- 🎹 [Avicii – *Wake Me Up* on the Roland JD-Xi](https://www.youtube.com/watch?v=VyQxaOc6G2Y)  
- 🎹 [Vangelis – *Blade Runner End Titles* | Synth Cover on the Roland JD-Xi](https://www.youtube.com/watch?v=mGgGibBKm9E)  
- 🎹 [Underworld – *Born Slippy* on the Roland JD-Xi](https://www.youtube.com/watch?v=xHLttYaMxCw&list=PLVZK_NOytILiQuNulDn-tOdAUQWdNAS-y&index=18)  
- 🎹 [*Knight Rider Theme* on the Roland JD-Xi](https://www.youtube.com/watch?v=4XpuQm7_Ohs&list=PLVZK_NOytILiQuNulDn-tOdAUQWdNAS-y&index=20)  
- 🎹 [Twin Peaks – *Laura Palmer's Theme* on the Roland JD-Xi](https://www.youtube.com/watch?v=zSkKNoy8O9Y&list=PLVZK_NOytILiQuNulDn-tOdAUQWdNAS-y&index=29)  
- 🎹 [The Cure – *A Forest* on the Roland JD-Xi](https://www.youtube.com/watch?v=wejcaIawCMs&list=PLVZK_NOytILiQuNulDn-tOdAUQWdNAS-y&index=25)  
- 🎹 [Michael Jackson – *Thriller* on the Roland JD-Xi](https://www.youtube.com/watch?v=flFQlFggTug&list=PLVZK_NOytILiQuNulDn-tOdAUQWdNAS-y&index=19)  

---

### 🎬 Featured Demo  

Phil Collins – *In The Air Tonight* performed on the Roland JD-Xi  

[![Watch the demo](https://img.youtube.com/vi/oquaCQE1EFs/0.jpg)](https://www.youtube.com/watch?v=oquaCQE1EFs)

## 🚀 Getting Started

Builds of this fork are on its [releases page](https://github.com/emanuelemerlo/JDXI-Editor/releases).
Beta versions are marked as pre-releases. The app checks this page for updates (Help › Check for Updates):
a beta is told about the next beta, a final release only about final releases.

### Windows 📦
Each release offers two separate downloads; take the one you want:
- the **installer** `jdxi_editor-<version>_setup_win_x86-64.exe` (installs for the current user,
  no administrator rights, adds Start menu entries and an uninstaller);
- the **portable** `JDXI-Editor-<version>-win64-portable.zip` (nothing to install: unzip anywhere,
  even a USB stick, and run `jdxi_editor\jdxi_editor.exe`).
Windows 10 or 11, 64-bit. The files are not signed: if SmartScreen warns, choose
"More info" → "Run anyway". Test builds of every push are in the
[Windows build](https://github.com/emanuelemerlo/JDXI-Editor/actions/workflows/windows-build.yml) workflow
(Artifacts at the bottom of a run: `…-win64-setup` holds the installer, `…-win64-portable` the
app folder, ready to run once unzipped).

### macOS and Linux
This fork does not publish macOS or Linux packages yet: run it with Python (below), or build a package
with `python -m building.buildsys` (see [Building](#building)). The packages on the original project's
releases page are of the original app.

### Python 🐍
Python 3.10 to 3.13. The `JDXI-Editor` package on PyPI is the original project; install this fork from GitHub,
in a virtual environment, and start it with `jdxi-editor`:

```bash
$ python -m venv jdxi-env
$ source jdxi-env/bin/activate        # Windows: jdxi-env\Scripts\activate
$ python -m pip install "git+https://github.com/emanuelemerlo/JDXI-Editor.git"
$ jdxi-editor
```

PyAudio needs the PortAudio library: on macOS `brew install portaudio`, on Debian/Ubuntu `sudo apt install portaudio19-dev`, before the `pip install`. The FluidSynth player needs FluidSynth itself (`brew install fluid-synth`, `sudo apt install fluidsynth`).

To run from a checkout instead (for development):

```bash
$ git clone https://github.com/emanuelemerlo/JDXI-Editor.git
$ cd JDXI-Editor
$ python -m venv venv
$ source venv/bin/activate
$ python -m pip install -e ".[dev]"
$ python -m jdxi_editor.main
```

## 🌍 Languages

The interface is in **English** and **Italiano**. Choose it in **Help › Preferences › Interface language**
("Same as the system" follows the operating system; the change applies at the next start). Qt's own
buttons and file dialogs follow the same language.

Parameter names (Cutoff, Resonance, Porta Time…) stay as on the JD-Xi display and in Roland's manuals,
in every language, so what you read on screen matches the instrument.

To add a language or new strings, see [jdxi_editor/i18n/README.md](jdxi_editor/i18n/README.md).

# 📖 Documentation

## Features and Usage

See **[Features and Usage](doc/features-and-usage.md)** for:

- **Recent changes** — Arpeggiator SysEx sync, Effects Editor, Vocal Effects
- **Patch loading and saving** — .jsz, .msz, .json, .syx formats; save/load flow
- **SoundFont usage** — FluidSynth for playback, preset list from .sf2/.sf3

---

## ℹ Available Documentation:
### 📃 HTML Documentation:

The original project's documentation, which still describes most of this fork:
https://markxbrooks.github.io/JDXI-Editor/ — what changed here is in [CHANGELOG.md](CHANGELOG.md).

### 🎹 UI Previews


**Program Editor**  
<a href="resources/program_editor.gif">
  <img src="resources/program_editor_600.gif" alt="Program Editor" />
</a>

&nbsp;

**Analog & Digital Synths**  
<a href="resources/analog_synth.png">
  <img src="resources/analog_synth_600.png" alt="Analog Synth" />
</a>

&nbsp;

<a href="resources/digital_synth.png">
  <img src="resources/digital_synth_600.png" alt="Digital Synth" />
</a>

&nbsp;

**Drum Editor**  
<a href="resources/drum_editor.png">
  <img src="resources/drum_editor_600.png" alt="Drum Editor" />
</a>

&nbsp;

**MIDI File Player**  
<a href="resources/midi_player.png">
  <img src="resources/midi_player_600.png" alt="MIDI File Player" />
</a>

&nbsp;

**Pattern Sequencer**  
<a href="resources/pattern.png">
  <img src="resources/pattern_600.png" alt="Pattern Sequencer" />
</a>

&nbsp;

**Effects**  
<a href="resources/effects.png">
  <img src="resources/effects_600.png" alt="Effects" />
</a>

&nbsp;

**Vocal Effects**  
<a href="resources/vocal_effects.png">
  <img src="resources/vocal_effects_600.png" alt="Vocal Effects" />
</a>

&nbsp;

**Arpeggiator**  
<a href="resources/arpeggiator.png">
  <img src="resources/arpeggiator_600.png" alt="Arpeggiator" />
</a>

---

## 🎛️ Features

- On-screen Keyboard
- Preset selection with search
- Octave shifting
- JD-Xi-style LCD Display
- ADSR displays
- Pitch ENV displays
- Digital Synth Parts 1 & 2 (including 3 partials per part)
- Analog Synth Editor
- Drum Part Editor 🥁
- Effects: Reverb, Delay, Compressor, Phaser, Vocoder
- Vocal Effects Editor (Vocoder, Auto-Pitch)
- Arpeggiator Editor
- Pattern Editor (4×16 step sequencer, MIDI load/save)
- MIDI File Player (track classification, channel assignment)
- SoundFont (.sf2/.sf3) playback without hardware

---

## ❓ Frequently Asked Questions
### What is JDXI-Editor?
JDXI-Editor is a Python-based MIDI editor for the Roland JD-Xi synthesizer, built with the Qt Framework and RtMidi.
### Does JDXI-Editor work on MacOS, Linux and Windows?
Yes, JDXI-Editor supports MacOS, Linux, and Windows!
### What features does JDXI-Editor offer?
JDXI-Editor provides preset selection, synth editing, drum part customization, effects editing, and more.

---

- Learn more about the [Roland JD-Xi Synthesizer](https://www.roland.com/global/products/jd-xi/).
- Explore the [Qt Framework](https://www.qt.io/) for building cross-platform apps.
- Discover [RtMidi](https://www.music.mcgill.ca/~gary/rtmidi/), a real-time MIDI library.

---

### 💡 Contribute and Share Feedback
JDXI-Editor is a growing project! 
- ⭐ Star this repository to support its development.
- 🛠️ Contribute features or report issues via [GitHub Issues](https://github.com/emanuelemerlo/JDXI-Editor/issues).

---

## Building

```bash
python -m building.buildsys 2>&1 | head -50

Building on: linux
Project root: /home/brooks/PycharmProjects/JDXI-Editor
╭─────────── linux builder ────────────╮
│  linux builder Application Starting  │
╰──────────────────────────────────────╯
[02/10/26 23:12:10] INFO                        ℹ️ linux builder starting up with log file /home/brooks/.linux builder/logs/linux builder-10Feb2026-23-12-10.log...                                                         
                    INFO                        ℹ️ 🎹 JD-Xi Editor v0.9.6 - Linux Build System                                                                                                                              
                    INFO                        ℹ️ ==================================================                                                                                                                       
                    INFO                        ℹ️                                                                                                                                                                          
                             🧹 Cleaning previous builds...                                                                                                                                                                
                    INFO                        ℹ️                                                                                                                                                                          
                             📦 Building with PyInstaller...                                                                                                                                                               
                    INFO                        ℹ️   This may take a few minutes... 
```

Mac .dmg package
```commandline
python3 -m building.buildsys --dmg
```

Mac .app
```commandline
python3 -m building.buildsys --app
```

Mac .pkg
```commandline
python3 -m building.buildsys --pkg
```

Linux .deb or .Appimage
```commandline
python3 -m building.buildsys # builds both with no flag
```

Windows: the app (PyInstaller, one folder) and the installer (Inno Setup 6)
```commandline
python -m pip install ".[soundfont,build-windows]"   # not -e: the spec bundles the installed resources
cd %TEMP%
pyinstaller --noconfirm --clean --distpath <repo>\dist <repo>\building\windows\jdxi_editor.spec
cd <repo>
iscc /DMyAppVersion=<version> jdxi_editor.iss                # -> dist\installer\
```
Translations: after changing interface strings run `python -m building.i18n update`, translate the
`.ts` files, then `python -m building.i18n compile` (the tests fail while a string is untranslated).

The `Windows build` workflow (`.github/workflows/windows-build.yml`) does the same on every push
to a `fix/**` or `release/**` branch, starts the app as a smoke test, and uploads the portable app and the
installer as two separate artifacts; on a `v*` tag it attaches them to a release (a pre-release when the tag has a `-`, e.g. `v0.10.0-beta.1`); the tag must match `__version__`.
The older builder is still available:
```commandline
python -m building.buildsys
```
or
```
.\building\scripts\build.ps1
```

converting wav files to midi

```commandline
cd ~/Downloads/separated/htdemucs/OxygeneV
mkdir -p midi
basic-pitch midi bass.flac --minimum-frequency 30 --maximum-frequency 400
```

```python
import audioread; audioread.available_backends = lambda flush_cache=False: []
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
_, midi, notes = predict('bass.flac', ICASSP_2022_MODEL_PATH, minimum_frequency=30, maximum_frequency=400)
midi.write('midi/bass.mid'); print(len(notes), 'notes')
"

```


## Arpeggio trial

`arpeggio-trial` damages a clean MIDI file and asks the filler to repair it from a rendering of that file. The clean file is the ground truth and is not modified.

```bash
python scripts/classify_midi_parts.py arpeggio-trial clean.mid --wav clean.wav --track BassSynth \
  --drop 0.2 --wrong 0.05 --octave 0.05 --extra 0.05 --model full --seed 1
```

`--drop` deletes notes. `--wrong` moves a note onto another frequent pitch or a neighbour, `--octave` shifts it by an octave, and `--extra` adds a neighbour beside it. The shares are disjoint. `--model` is `current` (the existing filler), `audio`, `repeat` (audio plus the repetition prior), or `full` (those two plus the MIDI noise term). `--decoder` is `rules`, `hmm`, or `best` (default): the repeat HMM's hidden state is the figure's transposition, or stopped, and `best` keeps whichever segmentation matches the clean file on more pitches. `trial.txt` reports both scores, plus precision, recall and false repairs separately for confirmed and probable notes. Probable notes are counted and not written. `candidates.csv` carries each candidate's audio, repetition, sequence and score. The score is a weighted sum of logs.

Outside any figure, an empty step takes its pitch prior from a chain learned on the track's confident notes, `P(pitch | previous) × P(next | pitch)`. The audio bar is unchanged.

On a rendered G3–B♭3–C4 loop (64 repeats, 20% deletion, seed 1) the current filler, audio, repeat and full each restored 35 of 38 notes, precision 1.000, no false repairs. The audio term already clears the write bar on that rendering, so the extra terms do not change the count. With 10 missing B♭3s and 4 steps written as D4, audio, repeat and full each corrected all 4 and restored 8 of the holes: 12 of 14, recall 0.857, precision 1.000. Where the audio term prefers D4 and the repeats plus a learned B♭3→D4 confusion prefer B♭3, the full score corrects the D4 and audio alone keeps it.

The earlier BassSynth drop trial, from the current filler, was recall 0.45 and 0.37 at precision 1.00 (seeds 1 and 2). That recording is not in this repo, so those two numbers were not remeasured here.

## 🙏 Credits

- The original [JDXI-Editor](https://github.com/markxbrooks/JDXI-Editor) by Mark Brooks, on which this fork is built
- [Qt](https://www.qt.io/)
- [RtMidi](https://www.music.mcgill.ca/~gary/rtmidi/)
- [Cursor.ai](https://cursor.so)
- [qtawesome](https://github.com/spyder-ide/qtawesome)
- Inspiration from many great JD-Xi editor projects that paved the way
- **Roland**, for creating such a powerful little synth!

---

> Original project made with 🎹 and ☕ by Mark Brooks · this fork maintained by emanuelemerlo

