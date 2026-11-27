from __future__ import annotations

from typing import ClassVar, Dict, Iterable, Optional, Sequence, Tuple, Union

from midi import MIDIFile, Pitch, Track
from mixer import Strip, Master

PitchLike = Union[int, str]

class Part:
    # Writes notes and controller automation into a MIDI track using beats (quarter notes)
    # instead of ticks, and pitch names (C4 = 60) or numbers.
    def __init__(self, track: Track, resolution: int) -> None:
        self.track: Track = track
        self.resolution: int = resolution

    def ticks(self, beat: float) -> int:
        return int(round(beat * self.resolution))

    @staticmethod
    def pitch(value: PitchLike) -> int:
        return Pitch.parse(value) if isinstance(value, str) else value

    def note(self, beat: float, pitch: PitchLike, length: float, velocity: int = 96) -> None:
        start = self.ticks(beat)
        self.track.add(start, self.ticks(beat + length) - start, Part.pitch(pitch), velocity)

    def chord(self, beat: float, pitches: Sequence[PitchLike], length: float, velocity: int = 96, strum: float = 0.0) -> None:
        for index, pitch in enumerate(pitches):
            offset = index * strum
            self.note(beat + offset, pitch, length - offset, velocity)

    def phrase(self, beat: float, notes: Iterable[Tuple[float, PitchLike, float, int]], transpose: int = 0) -> None:
        # notes: (beat offset, pitch, length, velocity) relative to the phrase start.
        for offset, pitch, length, velocity in notes:
            self.note(beat + offset, Part.pitch(pitch) + transpose, length, velocity)

    def ramp(self, number: int, start: float, end: float, first: int, last: int, step: float = 0.125) -> None:
        # Controller automation as a dense staircase, so any MIDI player follows the same curve.
        count = max(int(round((end - start) / step)), 1)
        for index in range(count + 1):
            progress = index / count
            self.track.control(self.ticks(start + (end - start) * progress), number, int(round(first + (last - first) * progress)))

    def set(self, beat: float, number: int, value: int) -> None:
        self.track.control(self.ticks(beat), number, value)

class Score:
    def __init__(self, midi: MIDIFile) -> None:
        self.midi: MIDIFile = midi

    def part(self, name: str, channel: int = 0, program: Optional[int] = None) -> Part:
        track = Track(name, channel, program)
        self.midi.tracks.append(track)
        return Part(track, self.midi.resolution)

class Song:
    # A piece of music: the score as MIDI, plus how each track is voiced and mixed.
    name: ClassVar[str] = ""
    title: ClassVar[str] = ""
    # Subdirectory of the output directory, as a relative POSIX path ("" for the top level).
    directory: ClassVar[str] = ""
    rate: ClassVar[int] = 48000

    @classmethod
    def path(cls) -> str:
        # Where the song goes, relative to the output directory and without a suffix; also
        # the name it is selected by on the command line.
        return f"{cls.directory}/{cls.name}" if cls.directory else cls.name

    def compose(self) -> MIDIFile:
        raise NotImplementedError()

    def strips(self) -> Dict[str, Strip]:
        raise NotImplementedError()

    def master(self) -> Master:
        raise NotImplementedError()
