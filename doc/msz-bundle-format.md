# MSZ Music Bundle Format

## Overview

The `.msz` (Music Bundle) format is a bundled file format that combines:
- **All synthesizer parameters** (JSON files: program, tones, effects, vocal effects, arpeggio)
- **MIDI files** (song data ready to play)

This allows you to save a complete "song" with all its patches and MIDI data in a single file, ready to load and play.

## File Structure

An `.msz` file is a ZIP archive containing:

```
song.msz
├── jdxi_tone_data_*.json    (one JSON file per memory block)
└── song.mid                  (MIDI file, if available)
```

### JSON Files
- One JSON file per block of the JD-Xi's memory (program common, each tone's common and partials,
  effects, vocal effects, arpeggio...), named after its 4-byte address
  (e.g. `jdxi_tone_data_19420000.json` for the Analog tone)
- Values are **raw MIDI values**, as the JD-Xi sends them (`"VALUE_FORMAT": "midi"`), with the
  tone or program name (`TONE_NAME_1`...`TONE_NAME_12`) and `SYSEX`: the whole block as one DT1
- Bundles from before 1.0 hold display values (milliseconds, fractions): they are converted to MIDI
  values when loaded

### MIDI File
- Standard MIDI file format (`.mid`)
- Contains the song/sequence data
- Automatically loaded into the «MIDI File» player when the bundle is opened

## Usage

### Saving a Music Bundle

1. **Set up your patches**: Configure all your synth parameters (Analog, Digital, Drum)
2. **Load/Edit your MIDI file**: Open the «MIDI File» player and load or create your MIDI sequence
3. **Save as .msz**:
   - Go to **File › Patch › Save…**
   - In the file dialog, select **"Music Bundle (*.msz)"** from the file type dropdown
   - Choose a filename (e.g., `my_song.msz`)
   - Click **Save**

The bundle will include:
- All current synth parameter settings
- The MIDI file (if one is loaded in the «MIDI File» player)

### Loading a Music Bundle

1. **Load the bundle**:
   - Go to **File › Patch › Open…**
   - Select your `.msz` file
   - Click **Load**

2. **What happens**:
   - All synth parameters are loaded and applied
   - The MIDI file (if present) is automatically loaded into the «MIDI File» player
   - You're ready to play!

## Compatibility

- **Backward Compatible**: The existing `.jsz` format still works (patch files without MIDI)
- **Forward Compatible**: `.msz` files can be opened by the same loader (MIDI file is optional)

## Technical Details

### Save Process
1. Each block is taken from the copy of the JD-Xi's memory the app keeps (what the instrument
   sent and what the editors wrote) when it is complete there, otherwise from the editors
   (`export_dt1s`). After an incomplete *Read from JD-Xi*, only the blocks that read confirmed
   come from that copy
2. If a MIDI file is loaded in the «MIDI File» player, it is saved as `song.mid` in the bundle
3. All files are zipped into a single `.msz` archive

### Load Process
1. The ZIP archive is opened and its JSON sections are extracted
2. Each section's `SYSEX` is sent to the JD-Xi unchanged (`MidiIOHelper.load_patch()`); the
   editors show the values as the JD-Xi receives them
3. The first `.mid` file in the archive is extracted as `bundle.mid` in a temporary folder,
   whatever its name in the archive (a name like `../../x.mid` cannot write elsewhere); files over
   32 MB are refused
4. The MIDI file is loaded into the «MIDI File» player

## File Extensions

- **`.msz`**: Music Bundle (includes patches + MIDI file)
- **`.jsz`**: Patch Bundle (includes patches only, no MIDI)
- **`.json`**: Single section (one block)
- **`.syx`**: SysEx file (the DT1 messages, for other tools too)

## Benefits

1. **Complete Song Preservation**: Save everything needed to recreate a song
2. **Easy Sharing**: One file contains all patches and MIDI data
3. **Ready to Play**: Load the bundle and immediately start playing
4. **Organized**: All related data is bundled together

## Notes

- If no MIDI file is loaded when saving, the bundle will only contain JSON files (works like `.jsz`)
- If a MIDI file exists in the bundle but the «MIDI File» player is not available, a warning is logged but the patch still loads
- The MIDI file is optional - bundles without MIDI files work exactly like `.jsz` files

