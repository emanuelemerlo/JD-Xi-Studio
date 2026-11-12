# Developer tools

Tools used while developing JD-Xi Studio's MIDI analysis (track classification,
transcription repair). They are not needed to use the editor.

## Converting audio files to MIDI

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

