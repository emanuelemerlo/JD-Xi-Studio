What's New in 1.1.0
===================

Deeper editing of the SuperNATURAL synth tones, and text that is easier to read.

Digital Synth
-------------

* **Link 1·2·3**: a change to the partial shown goes to the other partials that are on, in one
  Undo step. The oscillator (waveform, PCM wave, pitch, detune) stays each partial's own.
* **Partial ▾**: copy, paste and swap a partial or one section of it (Oscillator, Filter,
  Amplifier, LFO, Modulation LFO), also between Digital 1 and Digital 2.
* **Randomize** a section, a partial or the whole tone by a little, a medium amount or much; the
  tone stays playable and audible, and each press is one Undo step.
* **PCM waves by family**: Wave Number opens the 160 waves in eleven families, with a search,
  ★ favourites and *Try*, which plays a note with each wave so they can be compared by ear.
* The filter and amplifier envelopes show the **Envelope Loop** (FREE-RUN, TEMPO-SYNC).
* The partial switches (P1 ON, P1 SEL…) sit next to their own switch.

See :doc:`digital_synth` (*Working with the Three Partials*).

A/B compare
-----------

* **Take from a photo**: the sections where a photo differs from the current sound, to bring in
  one by one (Digital and Analog).

Reading
-------

* **File › Preferences › Text size**: Normal, Large (112%) or Larger (125%), from the next start.
  The text grows, the knobs and graphs keep their size. Text is never smaller than 12 px, and the
  grey secondary text is lighter.
* The LCD displays (tone, program, file) and the preset card follow the text size.
* Maximised, the main window shows the instrument as a body on a darker surface, with an edge.

What's New in 1.0.0
===================

The first official release. Since the release candidate: **Recipes** made to be written by an AI
and fine-tuned by ear, in one workspace; a MIDI Player that counts bars as the file does and shows
a part on the keyboard; the optional tabs always at hand; ready-made packages for **macOS** and
**Linux**; and the fixes from trying rc 1 on the JD-Xi.

Recipes
-------

* One workspace: the library on the left (Import recipe…, + New recipe, search, categories,
  Duplicate, Export, Delete, Close), the work in the middle, the explanation on the right.
* **With an AI**: describe the sound, copy the request — format, rules and the parameters it may
  set — into an AI's chat, paste its answer: every row is checked. See :doc:`recipes`.
* The editor works by **steps**: rename, add, duplicate, move, delete; rows copied and pasted
  (also from an AI's answer); Save as…, Undo changes, «not saved».
* In Italian, a recipe setting an LFO depth no longer stops the import; Mono/Poly, a negative
  Bend Range D and a Pan of «C» are understood.

MIDI Player
-----------

* The **ruler** follows the file's time signatures and tempo changes: its bars are the ones the
  position shows and «Snap to bars» uses, in 3/4, 6/8 or when the time signature changes; where a
  time signature starts it is written on the ruler (*5  3/4*).
* **Keyboard** (Playback): the keyboard of the main window shows the notes one part of the file
  plays — Digital 1, Digital 2, Analog or Drums — in the part's colour, at the part's octave; a
  triangle on the first or last key means notes beyond the 37 keys.
* A part doubled by two identical tracks plays each note once.

Editors window
--------------

* **Program settings**, **Recipes** and **Settings** are always in the tab bar (no more «+»
  menu). Each can be reduced to a small bar in its colour with **◂**; a click on the bar opens it
  again. Which are open is remembered.
* The pop-up menus highlight the item under the mouse.

Installing
----------

* Next to the Windows installer and portable app, the releases now have a **macOS disk image**
  (Apple silicon and Intel; drag the app to Applications) and a **Linux .deb** (Ubuntu 22.04,
  Debian 12 or later: ``sudo apt install ./jd-xi-studio_1.0.0_amd64.deb``). See
  :doc:`installation`; the first opening on macOS is explained in :doc:`troubleshooting`.

Fixes
-----

* The JD-Xi switched off and on again: every reconnection opens new MIDI ports (the badge stayed
  «Verifying the JD-Xi…»).
* macOS: while playing, the app asks the system not to slow its timers, so the notes stay on time.
* The Program editor no longer logs false failures for a Partial Switch sent back by the JD-Xi.
* The log calls the JD-Xi's Identity Reply value a *software revision*, not a firmware version.

The manual
----------

* **Troubleshooting** holds the solutions (installing, the connection, playing MIDI files, what to
  put in a report); old pages no one used are gone.

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
