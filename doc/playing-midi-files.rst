Playing MIDI Files
==================

JD-Xi Studio provides two main tools for working with MIDI files: the **Pattern Sequencer** for step-based editing and the **MIDI Player** for playback and track management.

Overview
=======

**MIDI Player**
   Load standard MIDI files (.mid, .midi), see which tracks the JD-Xi plays, fit them to its four parts (Digital 1, Digital 2, Analog, Drums) with **Assign tracks to parts…**, and play them on the synthesizer — recording its USB audio if you like.

**Pattern Sequencer**
   Load MIDI files into a 4×16 step grid, edit notes/velocity/duration per step, and save patterns back to MIDI files. Integrates with the MIDI Player via "Load into Pattern Editor."

Typical Workflow
================

1. **Load a MIDI file** in the MIDI Player (its Load button, File › Open a MIDI file in the MIDI Player…, or drag-and-drop)
2. **Fit to the JD-Xi** (for a general MIDI file): **Assign tracks to parts…**, check the
   proposal, Apply; or a track's channel in its header. **Starting sounds** gives the parts a sound
   to start from
3. **Play**: Start playback on the JD-Xi
4. **Edit in Pattern Editor** (optional): Load into Pattern Editor → edit steps → Save Pattern

Available Tools
===============

* :doc:`Pattern Sequencer <pattern_sequencer>` — 4×16 step grid, MIDI load/save, part muting
* :doc:`MIDI Player <midi_file_player>` — fit to the JD-Xi, tracks, playback, USB recording
