Playing MIDI Files
==================

JD-Xi Studio provides two main tools for working with MIDI files: the **Pattern Sequencer** for step-based editing and the **MIDI Player** for playback and track management.

Overview
=======

**MIDI Player**
   Load standard MIDI files (.mid, .midi), classify tracks (Detect Drums, Classify Tracks), assign channels to the JD-Xi's four parts (Digital 1, Digital 2, Analog, Drums), and play them on the synthesizer.

**Pattern Sequencer**
   Load MIDI files into a 4×16 step grid, edit notes/velocity/duration per step, and save patterns back to MIDI files. Integrates with the MIDI Player via "Load into Pattern Editor."

Typical Workflow
================

1. **Load a MIDI file** in the MIDI Player (File → Open… or drag-and-drop)
2. **Assign channels** (optional): Detect Drums and Classify Tracks, or a track's channel in its
   header (changes apply immediately); Apply Presets inserts JD-Xi presets per channel
3. **Play**: Start playback on the JD-Xi
4. **Edit in Pattern Editor** (optional): Load into Pattern Editor → edit steps → Save Pattern

Available Tools
===============

* :doc:`Pattern Sequencer <pattern_sequencer>` — 4×16 step grid, MIDI load/save, part muting
* :doc:`MIDI Player <midi_file_player>` — Track classification, channel assignment, playback
