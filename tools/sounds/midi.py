from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Set, Tuple

class VLQ:
    maximum: ClassVar[int] = 0x0FFFFFFF

    @staticmethod
    def encode(value: int) -> bytes:
        if value < 0 or value > VLQ.maximum:
            raise ValueError(f"Variable-length quantity out of range: {value}")
        groups = [value & 0x7F]
        value >>= 7
        while value:
            groups.append((value & 0x7F) | 0x80)
            value >>= 7
        return bytes(reversed(groups))

    @staticmethod
    def decode(data: bytes, offset: int) -> Tuple[int, int]:
        value = 0
        for index in range(4):
            if offset + index >= len(data):
                raise ValueError("Truncated variable-length quantity")
            byte = data[offset + index]
            value = (value << 7) | (byte & 0x7F)
            if not byte & 0x80:
                return value, offset + index + 1
        raise ValueError("Variable-length quantity longer than 4 bytes")

class Pitch:
    names: ClassVar[Tuple[str, ...]] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    offsets: ClassVar[Dict[str, int]] = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

    @staticmethod
    def parse(name: str) -> int:
        # Scientific pitch notation: C4 = 60 (GarageBand and Logic call this note C3).
        letter = name[0].upper()
        if letter not in Pitch.offsets:
            raise ValueError(f"Unknown pitch name: {name!r}")
        index = 1
        semitone = Pitch.offsets[letter]
        while index < len(name) and name[index] in "#b":
            semitone += 1 if name[index] == "#" else -1
            index += 1
        pitch = (int(name[index:]) + 1) * 12 + semitone
        if not 0 <= pitch <= 127:
            raise ValueError(f"Pitch out of MIDI range: {name!r}")
        return pitch

    @staticmethod
    def name(pitch: int) -> str:
        return f"{Pitch.names[pitch % 12]}{pitch // 12 - 1}"

    @staticmethod
    def frequency(pitch: float, reference: float = 440.0) -> float:
        return reference * 2.0 ** ((pitch - 69.0) / 12.0)

@dataclass(frozen=True)
class Note:
    start: int
    length: int
    pitch: int
    velocity: int

    @property
    def end(self) -> int:
        return self.start + self.length

@dataclass(frozen=True)
class Control:
    time: int
    number: int
    value: int

@dataclass(frozen=True)
class Tempo:
    time: int
    bpm: float

    def __post_init__(self) -> None:
        # The Set Tempo meta event stores microseconds per quarter note in 24 bits.
        if not 60_000_000 / 0xFFFFFF <= self.bpm <= 60_000_000:
            raise ValueError(f"Tempo out of the range a MIDI file can store: {self.bpm} BPM")

    @property
    def microseconds(self) -> int:
        return round(60_000_000 / self.bpm)

@dataclass(frozen=True)
class TimeSignature:
    numerator: int = 4
    denominator: int = 4

    def __post_init__(self) -> None:
        if not 1 <= self.numerator <= 255 or self.denominator <= 0 or self.denominator & (self.denominator - 1):
            raise ValueError(f"Time signature out of MIDI range: {self.numerator}/{self.denominator}")

@dataclass(frozen=True)
class KeySignature:
    sharps: int = 0
    minor: bool = False

    def __post_init__(self) -> None:
        if not -7 <= self.sharps <= 7:
            raise ValueError(f"Key signature must have -7 to 7 sharps: {self.sharps}")

@dataclass
class Track:
    name: str
    channel: int = 0
    program: Optional[int] = None
    notes: List[Note] = field(default_factory=list)
    controls: List[Control] = field(default_factory=list)

    def add(self, start: int, length: int, pitch: int, velocity: int) -> None:
        if start < 0 or length <= 0:
            raise ValueError(f"Note must start at or after 0 and have a positive length: start={start}, length={length}")
        if not 0 <= pitch <= 127 or not 1 <= velocity <= 127:
            raise ValueError(f"Note out of MIDI range: pitch={pitch}, velocity={velocity}")
        self.notes.append(Note(start, length, pitch, velocity))

    def control(self, time: int, number: int, value: int) -> None:
        if time < 0:
            raise ValueError(f"Control change before the start of the track: {time}")
        if not 0 <= number <= 127 or not 0 <= value <= 127:
            raise ValueError(f"Control change out of MIDI range: number={number}, value={value}")
        self.controls.append(Control(time, number, value))

@dataclass
class MIDIFile:
    title: str = ""
    resolution: int = 960
    tempos: List[Tempo] = field(default_factory=lambda: [Tempo(0, 120.0)])
    time_signature: TimeSignature = field(default_factory=TimeSignature)
    key_signature: KeySignature = field(default_factory=KeySignature)
    tracks: List[Track] = field(default_factory=list)

    # Status bytes and meta event types from the Standard MIDI File 1.0 specification.
    NOTE_OFF: ClassVar[int] = 0x80
    NOTE_ON: ClassVar[int] = 0x90
    CONTROL_CHANGE: ClassVar[int] = 0xB0
    PROGRAM_CHANGE: ClassVar[int] = 0xC0
    META: ClassVar[int] = 0xFF
    META_TRACK_NAME: ClassVar[int] = 0x03
    META_END_OF_TRACK: ClassVar[int] = 0x2F
    META_TEMPO: ClassVar[int] = 0x51
    META_TIME_SIGNATURE: ClassVar[int] = 0x58
    META_KEY_SIGNATURE: ClassVar[int] = 0x59
    DATA_LENGTHS: ClassVar[Dict[int, int]] = {0x80: 2, 0x90: 2, 0xA0: 2, 0xB0: 2, 0xC0: 1, 0xD0: 1, 0xE0: 2}

    def track(self, name: str) -> Track:
        for track in self.tracks:
            if track.name == name:
                return track
        raise KeyError(f"No such track: {name!r}")

    def seconds(self, tick: int) -> float:
        tempos = sorted(self.tempos, key=lambda tempo: tempo.time)
        elapsed = 0.0
        for index, tempo in enumerate(tempos):
            following = tempos[index + 1].time if index + 1 < len(tempos) else None
            if following is not None and tick > following:
                elapsed += (following - tempo.time) * 60.0 / (tempo.bpm * self.resolution)
                continue
            return elapsed + (tick - tempo.time) * 60.0 / (tempo.bpm * self.resolution)
        return elapsed

    def length(self) -> int:
        return max((note.end for track in self.tracks for note in track.notes), default=0)

    # Encoding

    def encode(self) -> bytes:
        chunks = [self.encode_conductor()] + [self.encode_track(track) for track in self.tracks]
        header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), self.resolution)
        return header + b"".join(b"MTrk" + struct.pack(">I", len(chunk)) + chunk for chunk in chunks)

    def encode_conductor(self) -> bytes:
        numerator, denominator = self.time_signature.numerator, self.time_signature.denominator
        if denominator & (denominator - 1) or denominator <= 0:
            raise ValueError(f"Time signature denominator must be a power of two: {denominator}")
        events: List[Tuple[int, int, bytes]] = [
            (0, 0, MIDIFile.meta(MIDIFile.META_TRACK_NAME, self.title.encode("utf-8"))),
            (0, 0, MIDIFile.meta(MIDIFile.META_TIME_SIGNATURE, bytes([numerator, denominator.bit_length() - 1, 24, 8]))),
            (0, 0, MIDIFile.meta(MIDIFile.META_KEY_SIGNATURE, struct.pack(">bB", self.key_signature.sharps, int(self.key_signature.minor)))),
        ]
        for tempo in self.tempos:
            events.append((tempo.time, 1, MIDIFile.meta(MIDIFile.META_TEMPO, tempo.microseconds.to_bytes(3, "big"))))
        return MIDIFile.serialize(events)

    def encode_track(self, track: Track) -> bytes:
        if not 0 <= track.channel <= 15:
            raise ValueError(f"MIDI channel out of range: {track.channel}")
        # MIDI cannot tell which note-off ends which of two sounding notes of the same pitch,
        # so overlapping notes of one pitch would not survive a round trip. Refuse them.
        ordered = sorted(track.notes, key=lambda note: (note.pitch, note.start))
        for previous, current in zip(ordered, ordered[1:]):
            if previous.pitch == current.pitch and current.start < previous.end:
                raise ValueError(f"Track {track.name!r}: overlapping notes of pitch {current.pitch} at tick {current.start}")
        # Sort key: time, then priority (name/program, controls, note-offs, note-ons) so that
        # a note ending exactly where the next note of the same pitch starts is never cut short.
        events: List[Tuple[int, int, bytes]] = [(0, 0, MIDIFile.meta(MIDIFile.META_TRACK_NAME, track.name.encode("utf-8")))]
        if track.program is not None:
            events.append((0, 1, bytes([MIDIFile.PROGRAM_CHANGE | track.channel, track.program])))
        for control in track.controls:
            events.append((control.time, 2, bytes([MIDIFile.CONTROL_CHANGE | track.channel, control.number, control.value])))
        for note in track.notes:
            events.append((note.end, 3, bytes([MIDIFile.NOTE_OFF | track.channel, note.pitch, 64])))
            events.append((note.start, 4, bytes([MIDIFile.NOTE_ON | track.channel, note.pitch, note.velocity])))
        return MIDIFile.serialize(events)

    @staticmethod
    def meta(kind: int, payload: bytes) -> bytes:
        return bytes([MIDIFile.META, kind]) + VLQ.encode(len(payload)) + payload

    @staticmethod
    def serialize(events: List[Tuple[int, int, bytes]]) -> bytes:
        output = bytearray()
        now = 0
        for time, _, data in sorted(events, key=lambda event: (event[0], event[1])):
            if time < 0:
                raise ValueError(f"Event before the start of the track: {time}")
            output += VLQ.encode(time - now) + data
            now = time
        output += VLQ.encode(0) + MIDIFile.meta(MIDIFile.META_END_OF_TRACK, b"")
        return bytes(output)

    def write(self, path: Path) -> None:
        path.write_bytes(self.encode())

    # Decoding

    @classmethod
    def decode(cls, data: bytes) -> "MIDIFile":
        try:
            return cls.parse(data)
        except (IndexError, struct.error) as error:
            raise ValueError(f"Truncated or malformed MIDI file: {error}") from error

    @classmethod
    def parse(cls, data: bytes) -> "MIDIFile":
        if data[:4] != b"MThd":
            raise ValueError("Not a Standard MIDI File")
        length, form, count, division = struct.unpack(">IHHH", data[4:14])
        if length < 6:
            raise ValueError("Header chunk too short")
        if form not in (0, 1):
            raise ValueError(f"Unsupported MIDI file format: {form}")
        if division & 0x8000:
            raise ValueError("SMPTE time division is not supported")
        result = cls(resolution=division, tempos=[], tracks=[])
        offset = 8 + length
        found = 0
        # Readers must skip chunk types they do not know ("alien" chunks).
        while found < count:
            if offset + 8 > len(data):
                raise ValueError(f"Expected {count} track chunks, found {found}")
            kind = data[offset:offset + 4]
            size = struct.unpack(">I", data[offset + 4:offset + 8])[0]
            if offset + 8 + size > len(data):
                raise ValueError("Truncated chunk")
            if kind == b"MTrk":
                result.decode_track(data[offset + 8:offset + 8 + size], first=found == 0)
                found += 1
            offset += 8 + size
        if not result.tempos or result.tempos[0].time != 0:
            result.tempos.insert(0, Tempo(0, 120.0))
        return result

    def decode_track(self, data: bytes, first: bool) -> None:
        name: Optional[str] = None
        channels: Set[int] = set()
        program: Optional[int] = None
        notes: List[Note] = []
        controls: List[Control] = []
        sounding: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        offset = 0
        now = 0
        status: Optional[int] = None
        ended = False
        while offset < len(data):
            delta, offset = VLQ.decode(data, offset)
            now += delta
            byte = data[offset]
            if byte == MIDIFile.META:
                kind = data[offset + 1]
                size, offset = VLQ.decode(data, offset + 2)
                payload = data[offset:offset + size]
                offset += size
                status = None
                if kind == MIDIFile.META_TRACK_NAME:
                    name = payload.decode("utf-8", errors="replace")
                elif kind == MIDIFile.META_TEMPO:
                    microseconds = int.from_bytes(payload[:3], "big")
                    if len(payload) != 3 or microseconds == 0:
                        raise ValueError("Invalid Set Tempo meta event")
                    self.tempos.append(Tempo(now, 60_000_000 / microseconds))
                elif kind == MIDIFile.META_TIME_SIGNATURE:
                    self.time_signature = TimeSignature(payload[0], 2 ** payload[1])
                elif kind == MIDIFile.META_KEY_SIGNATURE:
                    self.key_signature = KeySignature(struct.unpack(">b", payload[:1])[0], bool(payload[1]))
                elif kind == MIDIFile.META_END_OF_TRACK:
                    ended = True
                    break
                continue
            if byte in (0xF0, 0xF7):
                size, offset = VLQ.decode(data, offset + 1)
                offset += size
                status = None
                continue
            if byte & 0x80:
                status = byte
                offset += 1
            elif status is None:
                raise ValueError("Running status without a previous status byte")
            kind = status & 0xF0
            channel = status & 0x0F
            if kind not in MIDIFile.DATA_LENGTHS:
                raise ValueError(f"Unsupported status byte: {status:#x}")
            values = data[offset:offset + MIDIFile.DATA_LENGTHS[kind]]
            offset += MIDIFile.DATA_LENGTHS[kind]
            channels.add(channel)
            if kind == MIDIFile.NOTE_ON and values[1] > 0:
                sounding.setdefault((channel, values[0]), []).append((now, values[1]))
            elif kind in (MIDIFile.NOTE_ON, MIDIFile.NOTE_OFF):
                started = sounding.get((channel, values[0]))
                if started:
                    start, velocity = started.pop(0)
                    if now > start:
                        notes.append(Note(start, now - start, values[0], velocity))
            elif kind == MIDIFile.CONTROL_CHANGE:
                controls.append(Control(now, values[0], values[1]))
            elif kind == MIDIFile.PROGRAM_CHANGE:
                program = values[0]
        if not ended:
            raise ValueError("Track chunk without End of Track")
        if len(channels) > 1:
            raise ValueError(f"Track {name!r} uses more than one channel: {sorted(channels)}")
        if first and not notes and not controls:
            self.title = name or ""
            return
        notes.sort(key=lambda note: (note.start, note.pitch))
        self.tracks.append(Track(name or f"Track {len(self.tracks) + 1}", channels.pop() if channels else 0, program, notes, controls))

    @classmethod
    def read(cls, path: Path) -> "MIDIFile":
        return cls.decode(path.read_bytes())
