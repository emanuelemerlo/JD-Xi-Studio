What's New in 1.0.0 rc 1
========================

The release candidate: the MIDI Player fits a General MIDI file to the JD-Xi — its tracks and its
sounds — and plays it on time, the Programs page is a mixer, the menus follow the app. Tried on the
JD-Xi: the fixes from those checks are in this version.

MIDI Player
-----------

* The «MIDI file» tab is the **MIDI Player**; **Close** empties it (asking first when the file has
  changes not saved).
* **Fit to the JD-Xi** says which of the file's tracks the JD-Xi plays. **Assign tracks to parts…**
  proposes a part for each (drums, then one track each for Digital 1, Digital 2, Analog), in the
  parts' colours; **None played** to choose only the tracks you want; opened again, it shows what
  was applied.
* **Sounds of the parts**: the JD-Xi presets closest to the file's General MIDI instruments (a
  Digital tone, an Analog bass or lead, a drum kit), written into the file and sent on Apply — a
  GM file sounds close to its original the first time it is played.
* Event filter › **GM** (on by default): a General MIDI file's program changes no longer change
  the parts' sounds (and lose the edits not saved); the JD-Xi's own still go.
* **Channels**: Mute and **Solo** per channel, as on a mixer.
* On time on Windows: notes leave on average 0.6 ms after when the file says (it was about 8 ms);
  two tracks on the same note no longer leave it hanging.
* Big files load in seconds, with their progress on the display; the Pattern imports the file when
  shown, its first 64 bars.
* Tracks: **Expand** for more room, a grip for their height; a track without a name shows the
  instrument it plays. The loop's A point shows as soon as it is set.
* USB recorder: **Record on every Play**, now in stereo, on the JD-Xi's input.

Programs
--------

* The mixer: above each fader the part's **Pan**, **Delay** and **Reverb**; the faders are the
  editors' levels. **Undo / Redo** of the whole program, in any tab.
* **Program settings** (was *Program parts*), right after Programs: what the program keeps besides
  its tones, part by part.
* Playlist: Add / Remove over the songs, Play, Stop, Pause and **Mix** in a compact row; the
  **Extra sound** column (a Digital preset on the Analog part) readable.

Windows and menus
-----------------

* The menus follow the app: **File** (Patch, MIDI Player, Preferences), **Editor** (the tabs, in
  their order, Ctrl+0–9), **JD-Xi**, **Tools**, **Window**, **Help**; what cannot be done is greyed
  out, its tooltip saying why. Ctrl+O / Ctrl+S are the patch's.
* **Editors** in the keyboard window and **Keyboard** in the editors window bring the other one up.
* Keyboard window: the LFO **Rate** slider moves the LFO rate (it moved the Amp depth); **Env**
  starts in the middle, where the program is as saved.
* The «JD-Xi connected» badge goes Off-line when the JD-Xi is switched off.

What the JD-Xi holds
--------------------

* A typed name is an edit (one Undo, «Modified»).
* Save on the JD-Xi asks before writing in a slot whose content is not known.
* A tone change on one part forgets only that part; a message the port refuses is not counted as
  held.

Also: picomidi 0.3 (a muted track no longer cuts a note another track holds).

Removed: the FluidSynth software synth and the SoundFont preset lists (they played General MIDI
sounds, not the JD-Xi's, and only for notes coming from a MIDI keyboard).

What's New in 1.0.0 beta 2
==========================

**Visual Sound Design, Editing & Librarian for the Roland JD-Xi.** This beta makes the work with
the instrument safer and easier to follow: the app always says whether the JD-Xi is there, what it
holds, and what is saved where.

.. note::

   These features were tried on a simulated JD-Xi; the checks on the real instrument are listed in
   ``doc/hardware-test-plan.md`` (the automatic part: ``pytest -m hardware tests/test_jdxi_checks.py``).

Connection and Off-line
-----------------------

* The JD-Xi counts as **connected only once it answers as a JD-Xi** (a port named "JD-Xi" is not
  enough). The state shows as a badge: under MIDI IN / OUT in the keyboard window, at the top right
  of the editors window, in the corner of the other windows: **Off-line**, **Verifying the
  JD-Xi…**, **connected**, **Unstable connection**.
* Off-line everything can be tried, nothing is sent or saved: the commands that need the JD-Xi are
  off, with the reason in their tooltip. A warning says so once, after the start screen.
* When the JD-Xi arrives after changes made without it, they are given up for what it holds;
  **Save as file…** in that notice keeps them first.

When the JD-Xi comes back
-------------------------

After a disconnection (cable out, switched off and on) everything is read again and compared with
what the JD-Xi confirmed before:

* the same: «Reconnected»;
* different, with changes not saved anywhere: the parts that differ, and **Restore on the JD-Xi**
  or **Keep what the JD-Xi has** (a restore is read back part by part);
* different, with nothing at risk: the JD-Xi's settings are shown.

Where you are
-------------

A line under each editor's header and on the Programs page:
*program › part › tone · origin · state*. The origin is where the part's sound came from (a
program, a preset, a recipe, a file, an A/B photo, Init); the state is *original*, *modified,
temporary* (sent, not kept), *modified, not sent* (Off-line), *saved to file*, *saved in E-12*.

Save on the JD-Xi
-----------------

The JD-Xi keeps a program only with its WRITE, in the user banks E–H. **Programs › Save on the
JD-Xi…** guides it: name the program, choose the slot (slots named «Init Program» are proposed as
probably free, a slot with a program asks first), press WRITE on the JD-Xi as shown, then **Done**:
the app selects the slot and reads it back. «Saved in E-12 ✓» appears only when the slot holds the
sound.

New sound and section help
--------------------------

* **New sound ▾** in the Digital and Analog editors: *From scratch (Init)* — this part's tone
  only, a plain sawtooth with the filter open; one Undo brings the sound back — *From a preset*,
  *From a recipe*.
* A **?** on OSC, FILTER, AMP, LFO, PITCH, the effects, delay and reverb: what the section changes,
  how the sound changes, an example, in the information panel.

Programs
--------

.. figure:: images/jdxi-programs.png
   :alt: The Programs page: library, parts and mixer
   :width: 100%

   The Programs page: the library on the left, the parts inside the mixer on the right.

* The library searches number, name, genre and the four tones, sorts by number, name or genre,
  marks the program loaded on the JD-Xi apart from the one selected, and shows the tones in their
  parts' colours; right click: Load, Rename, Genre, Add to playlist, Export.
* The parts are inside the mixer: above each fader the part's Pan and its Delay and Reverb sends,
  under it the part's name, its tone (click: choose another), its MIDI channel and Edit; parts in
  their tabs' colours, a light line between them, the Master neutral, a box to type a level. The
  sends are off where the part's output skips that effect.
* The faders are the parts' levels (and the Master the Program Level): moving one is an edit like
  any other, the part's tab follows. **Undo / Redo** on the Programs page take back the last change
  to the program, in any tab; the tooltip says which.
* **Program settings** (the button beside Rename, or Editor › Program settings), right after
  Programs: what the program keeps besides its tones, part by part — level, pan, effects, pitch,
  offsets, zones, scale and MIDI. The mixer's Pan and sends are the same values.
* Organize: the playlists (factory programs too) and the selected one's programs.

A/B compare and recipes
-----------------------

* A/B compare (Digital 1, Digital 2, Analog): two photos of a tone, recalled and checked by reading
  it back; a photo taken without the JD-Xi whose data is not all known cannot be recalled.
* A recipe step is one Undo, also when it sets several editors.
