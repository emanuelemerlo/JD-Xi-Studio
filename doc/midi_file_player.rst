MIDI Player
===========

The **MIDI Player** plays MIDI files on the Roland JD-Xi: it says which of a file's tracks the
JD-Xi plays, helps put them on its four parts, and records the JD-Xi's USB audio while it plays.

What the JD-Xi plays
====================

The JD-Xi plays four parts, each on its own channel: **Digital 1** (1), **Digital 2** (2),
**Analog** (3) and **Drums** (10). Notes on any other channel are not heard. A file made for the
JD-Xi plays as it is; a general MIDI file (an orchestra on 16 channels) has to be fitted first.

Fit to the JD-Xi
================

* A line says what of the file the JD-Xi plays: *Ready for the JD-Xi*, or for example
  *28 of 44 tracks are on channels no JD-Xi part plays: they are not heard*.
* **Assign tracks to parts…** proposes a part for each track that plays notes, in a table you
  can change before **Apply**: the drum tracks to Drums; for each melodic part the one track
  recognised best for it — the bass to Digital 1, keys or guitars to Digital 2, strings to Analog
  (the Analog part plays one note at a time); the other tracks are not played. The Part column
  shows each part in its colour, grey when not played. **None played** sets every track «Not
  played», to choose only the ones you want; **Proposal** and **As now** switch between the
  proposal and the parts the tracks are on (opened again after Apply, it shows what was applied).
  A track's channel can also be set by hand in its header.
* **Sounds of the parts**, under the table: for each part the JD-Xi preset closest to the General
  MIDI instrument of its main track (the one with the most notes) — a Digital tone for Digital 1
  and 2, an Analog tone for the Analog part (basses and leads: a lead played low is a bass line),
  a drum kit for the Drums. On Apply it takes the place of the file's program changes on that part
  and is sent to the JD-Xi, so a General MIDI file sounds close to its original the first time.
  Each can be changed, or left **Unchanged**.
* **Starting sounds** gives the parts a sound to start from, also written into the file:
  Digital 1 Picked Bass, Digital 2 Piano, Analog JP8 Strings.
* **Channels**: per channel its number, **M** (mute, red) and **S** (solo, green). With one or
  more channels soloed only those play; the mutes are kept, back as they were when the solos go
  off; the channels a solo silences are dimmed. Channels 1, 2, 3 and 10 stand out; the tooltips
  say which part plays them.

The file on disk changes only when you save it. **Close** (in the Player card, or File › MIDI
Player › Close) empties the player as at start; when the file has changes not saved yet it asks
first: *Save…*, *Close without saving* or *Cancel*.

Tracks
======

* One row per track: name (when the file has none, the instrument it plays, in grey), channel,
  part, mute, solo, velocity scale, and its notes on the time line.
* **Expand** hides the cards under the tracks not needed while listening (Automation, USB
  recorder, Event filter) so the tracks take the room; Player, Fit to the JD-Xi and Playback stay.
  **Restore** brings them back.
* The grip under the Tracks card sets its height (remembered; double click: the usual height).
* Loading a big file shows its progress on the player's display (*Loading: track 12 of 45*).
* The ruler above the tracks numbers the bars as the player counts them, following the file's
  time signatures and tempo changes; where a time signature starts it shows it (*5  3/4*), unless
  the whole file is in 4/4.

Playback
========

* Play, Pause, Stop, Panic; speed in percent of the file's tempo.
* **Keyboard**: the keyboard of the main window shows the notes a part of the file plays
  (Digital 1, Digital 2, Analog or Drums), in the part's colour, on the keys that play them at
  the part's octave; a triangle on the first or last key means notes beyond the 37 keys.
* **Loop** repeats the A–B range, or the whole song when none is set. **A** and **B** take the
  playback position (snapped to bars if chosen); A shows on the ruler at once, the range when B
  is set. **Trim** keeps only a part of the file.
* **Event filter**: what of the file is not sent to the JD-Xi. **GM** (on by default): the program
  changes that do not choose a JD-Xi sound — a General MIDI file's, which would change the parts'
  sounds and lose the edits not saved; those after a JD-Xi bank select (a file made for the
  JD-Xi, the Automation's) still go. **PC**: all program changes. **CC**: the controllers.
* Two tracks playing the same note on one part retrigger it instead of doubling it (no note left
  hanging until Panic).

USB recorder
============

The JD-Xi is also a USB audio interface. With **Record on every Play**, every Play records its
audio into a WAV (stereo, 16 bit) until 10 seconds after the song ends; in a playlist, one WAV per
song. The port list shows only the inputs that can record, and the JD-Xi's is chosen by itself.

Pattern Sequencer
=================

The Pattern imports the file opened here when it is shown, its first 64 bars (a pattern, not a
whole song).

Formats: Standard MIDI Files (.mid, .midi), types 0 and 1.

.. figure:: images/jdxi-midi-editor.png
   :alt: MIDI Player
   :width: 60%

   The MIDI Player
