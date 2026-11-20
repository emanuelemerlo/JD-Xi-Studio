Editor Windows
==============

The Editor Windows are the sophisticated command centers of JD-Xi Studio—comprehensive, specialized interfaces that provide deep, granular control over every aspect of your Roland JD-Xi synthesizer.

Available Editors
=================

* :doc:`JDXi Instrument Window <instrument>` - The main instrument interface and control center
* :doc:`Editor Windows Overview <editor>` - Comprehensive guide to all specialized editors
* :doc:`Digital Synth Editors (Parts 1 & 2) <digital_synth>` - Multi-partial digital synthesis control
* :doc:`Analog Synth Editor <analog_synth>` - Classic analog synthesis with warm, organic sound
* :doc:`Drum Kit Editor <drum_kit>` - Professional drum sound design with 36 individual voices

The menus
=========

The keyboard window's menus; each item's tooltip says what it loads or sends, and where. An item
ending in «…» opens a dialog.

* **File** — **Patch** › Open… (Ctrl+O) / Save… (Ctrl+S) (a program and its tones in a ``.jsz`` /
  ``.msz`` file; Open sends them to the JD-Xi); **MIDI Player** › Open… (Ctrl+Alt+O) / Save
  (Ctrl+Alt+S) / Save as… / Close (Ctrl+Alt+W) / Recent (the MIDI Player's file; Save, Save as
  and Close only with a file in the player); Preferences… (Ctrl+,); Quit.
* **Editor** — the tabs of the editors window: Programs (Ctrl+0); *Parts*: Digital 1, Digital 2,
  Analog, Drums (Ctrl+1–4), Program: common and parts; *Effects*: Effects, Vocal FX (Ctrl+6, 7);
  *Playback*: Arpeggio (Ctrl+5), Pattern (Ctrl+8), MIDI Player (Ctrl+9); Recipes; Settings.
* **JD-Xi** — done on the instrument: **Save the program…** (the guided WRITE into a user slot),
  **Send all…** (every value of the open editors into its current program; asks first, writes
  nothing in its memory), **Read the user programs (E–H)…** (loads the 256 user slots one by one
  and keeps their names in the library), **MIDI Configuration…**, **Self-test…**.
* **Tools** — MIDI Monitor, SysEx Debugger, Log Viewer.
* **Window** — show the editors (Ctrl+Shift+W) or the keyboard (Ctrl+Shift+K), keyboard always on
  top.
* **Help** — Documentation (F1), Check for Updates, About.

An item that needs the JD-Xi (Patch › Save…, everything in the JD-Xi menu but MIDI
Configuration…) is off while it is not connected: greyed out, its tooltip saying why.

Switching windows
=================

**Editors** at the right of the keyboard window's menu bar and **Keyboard** at the right of the
editors window's tabs bring the other window to the front, also on another screen, without
Alt+Tab. With the keyboard *always on top* the editors come in front of every other window but,
where the two overlap, stay under the keyboard (the Editors button's tooltip says so).
