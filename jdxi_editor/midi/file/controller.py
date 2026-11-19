"""
MIDI File Controller Module

Manages MIDI file operations including saving, loading, and pattern conversion.
Handles tempo management, bar detection, and note-to-button mapping.
"""

from typing import Callable, Optional

from decologr import Decologr as log
from mido import MetaMessage, MidiFile, MidiTrack, tempo2bpm

from jdxi_editor.midi.channel.channel import MidiChannel
from jdxi_editor.midi.conversion.note import MidiNoteConverter
from picomidi import MidiTempo
from picomidi.message.type import MidoMessageType


class MidiFileControllerConfig:
    """Configuration for MIDI file controller."""

    def __init__(
        self,
        ticks_per_beat: int = 480,
        beats_per_measure: int = 4,
        default_bpm: int = 120,
        default_velocity: int = 100,
    ):
        """
        Initialize controller configuration.

        :param ticks_per_beat: MIDI ticks per beat (standard is 480)
        :param beats_per_measure: Number of beats per measure (typically 4)
        :param default_bpm: Default tempo in BPM
        :param default_velocity: Default note velocity
        """
        self.ticks_per_beat = ticks_per_beat
        self.beats_per_measure = beats_per_measure
        self.default_bpm = default_bpm
        self.default_velocity = default_velocity

    @property
    def ticks_per_measure(self) -> int:
        """Calculate ticks per bar."""
        return self.ticks_per_beat * self.beats_per_measure


class MidiFileController:
    """
    The Pattern editor's MIDI file in memory and its tempo.

    Saving and loading patterns is the Pattern editor's own (save_pattern,
    load_pattern, and midi/pattern/importer.py for imported files).
    """

    # MIDI channel mapping
    CHANNEL_TO_ROW = {
        MidiChannel.DIGITAL_SYNTH_1: 0,  # Channel 0
        MidiChannel.DIGITAL_SYNTH_2: 1,  # Channel 1
        MidiChannel.ANALOG_SYNTH: 2,  # Channel 2
        MidiChannel.DRUM_KIT: 3,  # Channel 9
    }

    ROW_TO_CHANNEL = {v: k for k, v in CHANNEL_TO_ROW.items()}

    def __init__(
        self,
        config: Optional[MidiFileControllerConfig] = None,
        midi_converter: Optional[MidiNoteConverter] = None,
        scope: str = "MidiFileController",
    ):
        """
        Initialize MIDI file controller.

        :param config: Controller configuration
        :param midi_converter: MIDI note converter for validation
        :param scope: Logging scope name
        """
        self.config = config or MidiFileControllerConfig()
        self.midi_converter = midi_converter
        self.scope = scope

        # Current MIDI file in memory
        self.midi_file: Optional[MidiFile] = None
        self.current_bpm = self.config.default_bpm

        # Callback for tempo changes
        self.on_tempo_changed: Optional[Callable[[int], None]] = None

    def create_new_file(self) -> MidiFile:
        """
        Create a new MIDI file with default settings.

        :return: New MidiFile object
        """
        midi_file = MidiFile(
            type=1,
            ticks_per_beat=self.config.ticks_per_beat,
        )

        # Add default track with tempo
        track = MidiTrack()
        midi_file.tracks.append(track)
        self._add_tempo_to_track(track, self.config.default_bpm)

        self.midi_file = midi_file
        self.current_bpm = self.config.default_bpm

        log.message(
            message="Created new MIDI file",
            scope=self.scope,
        )

        return midi_file

    def set_tempo(self, bpm: int) -> None:
        """
        Set the MIDI file tempo.

        Updates the current file's tempo and triggers callback.

        :param bpm: Tempo in beats per minute (20-300)
        """
        bpm = max(20, min(300, bpm))  # Constrain to valid range
        self.current_bpm = bpm

        if self.midi_file and self.midi_file.tracks:
            # Remove existing tempo messages
            track = self.midi_file.tracks[0]
            track[:] = [
                msg for msg in track if msg.type != MidoMessageType.SET_TEMPO.value
            ]

            # Add new tempo message
            self._add_tempo_to_track(track, bpm)

        log.message(
            message=f"Tempo set to {bpm} BPM",
            scope=self.scope,
        )

        if self.on_tempo_changed:
            self.on_tempo_changed(bpm)

    def get_tempo(self) -> int:
        """
        Get the current MIDI file tempo.

        :return: Tempo in BPM
        """
        if not self.midi_file or not self.midi_file.tracks:
            return self.current_bpm

        # Search for SET_TEMPO message in first track
        track = self.midi_file.tracks[0]
        for msg in track:
            if msg.type == MidoMessageType.SET_TEMPO.value:
                return int(tempo2bpm(msg.tempo))

        return self.current_bpm

    def _add_tempo_to_track(self, track: MidiTrack, bpm: int) -> None:
        """
        Add tempo message to a track.

        :param track: MidiTrack to add tempo to
        :param bpm: Tempo in BPM
        """
        microseconds_per_beat = int(MidiTempo.MICROSECONDS_PER_MINUTE / bpm)
        tempo_msg = MetaMessage(
            MidoMessageType.SET_TEMPO.value,
            tempo=microseconds_per_beat,
            time=0,
        )
        track.insert(0, tempo_msg)

    def set_config(self, config: MidiFileControllerConfig) -> None:
        """
        Update controller configuration.

        :param config: New configuration
        """
        self.config = config

    def set_midi_converter(self, converter: MidiNoteConverter) -> None:
        """
        Set or update the MIDI converter.

        :param converter: MidiNoteConverter instance
        """
        self.midi_converter = converter

    def get_current_file(self) -> Optional[MidiFile]:
        """
        Get the currently loaded MIDI file.

        :return: MidiFile instance or None
        """
        return self.midi_file
