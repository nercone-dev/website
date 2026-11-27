from typing import List, Tuple

import pytest

from midi import KeySignature, MIDIFile, Pitch, Tempo, TimeSignature, Track, VLQ

class TestMIDI:
    # Examples from the Standard MIDI File 1.0 specification, "Variable-Length Quantities".
    SPEC_VLQ: List[Tuple[int, str]] = [
        (0x00000000, "00"), (0x00000040, "40"), (0x0000007F, "7F"), (0x00000080, "81 00"),
        (0x00002000, "C0 00"), (0x00003FFF, "FF 7F"), (0x00004000, "81 80 00"), (0x00100000, "C0 80 00"),
        (0x001FFFFF, "FF FF 7F"), (0x00200000, "81 80 80 00"), (0x08000000, "C0 80 80 00"), (0x0FFFFFFF, "FF FF FF 7F"),
    ]

    @pytest.mark.parametrize("value,encoded", SPEC_VLQ)
    def test_vlq_matches_specification(self, value: int, encoded: str) -> None:
        data = bytes.fromhex(encoded)
        assert VLQ.encode(value) == data
        assert VLQ.decode(data, 0) == (value, len(data))

    def test_vlq_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            VLQ.encode(0x10000000)
        with pytest.raises(ValueError):
            VLQ.encode(-1)
        with pytest.raises(ValueError):
            VLQ.decode(bytes.fromhex("FF FF FF FF 7F"), 0)

    @staticmethod
    def chunks(data: bytes) -> List[Tuple[bytes, bytes]]:
        result = []
        offset = 0
        while offset < len(data):
            kind = data[offset:offset + 4]
            size = int.from_bytes(data[offset + 4:offset + 8], "big")
            result.append((kind, data[offset + 8:offset + 8 + size]))
            offset += 8 + size
        return result

    @staticmethod
    def sample() -> MIDIFile:
        midi = MIDIFile(title="Test", resolution=480, tempos=[Tempo(0, 120.0)], time_signature=TimeSignature(3, 8), key_signature=KeySignature(-1, False))
        track = Track("Piano", channel=2, program=4)
        track.add(0, 480, 60, 100)
        track.add(480, 240, 64, 90)
        track.control(0, 11, 100)
        midi.tracks.append(track)
        return midi

    def test_header_chunk(self) -> None:
        parts = TestMIDI.chunks(TestMIDI.sample().encode())
        kind, header = parts[0]
        assert kind == b"MThd"
        assert len(header) == 6
        # format 1, two tracks (conductor + piano), 480 ticks per quarter note
        assert header == bytes.fromhex("0001 0002 01E0")
        assert [kind for kind, _ in parts[1:]] == [b"MTrk", b"MTrk"]

    def test_every_track_ends_with_end_of_track(self) -> None:
        for _, body in TestMIDI.chunks(TestMIDI.sample().encode())[1:]:
            assert body.endswith(bytes.fromhex("FF 2F 00"))

    def test_conductor_meta_events(self) -> None:
        conductor = TestMIDI.chunks(TestMIDI.sample().encode())[1][1]
        # Set Tempo: FF 51 03 tttttt, 500000 microseconds per quarter note at 120 BPM.
        assert bytes.fromhex("FF 51 03 07 A1 20") in conductor
        # Time Signature: FF 58 04 nn dd cc bb, denominator as a power of two (8 = 2^3).
        assert bytes.fromhex("FF 58 04 03 03") in conductor
        # Key Signature: FF 59 02 sf mi, one flat major.
        assert bytes.fromhex("FF 59 02 FF 00") in conductor
        # Sequence/Track Name: FF 03 len text
        assert bytes.fromhex("FF 03 04") + b"Test" in conductor

    def test_channel_events_use_track_channel(self) -> None:
        body = TestMIDI.chunks(TestMIDI.sample().encode())[2][1]
        assert bytes.fromhex("C2 04") in body
        assert bytes.fromhex("B2 0B 64") in body
        assert bytes.fromhex("92 3C 64") in body
        assert bytes.fromhex("82 3C") in body

    def test_round_trip(self) -> None:
        original = TestMIDI.sample()
        decoded = MIDIFile.decode(original.encode())
        assert decoded.title == "Test"
        assert decoded.resolution == 480
        assert decoded.time_signature == TimeSignature(3, 8)
        assert decoded.key_signature == KeySignature(-1, False)
        assert [tempo.bpm for tempo in decoded.tempos] == [120.0]
        track = decoded.track("Piano")
        assert track.channel == 2 and track.program == 4
        assert track.notes == sorted(original.tracks[0].notes, key=lambda note: (note.start, note.pitch))
        assert track.controls == original.tracks[0].controls

    def test_repeated_pitch_is_not_cut_short(self) -> None:
        # A note ending where the next note of the same pitch starts must stay two full notes.
        midi = MIDIFile(tracks=[Track("Lead")])
        midi.tracks[0].add(0, 480, 60, 100)
        midi.tracks[0].add(480, 480, 60, 100)
        decoded = MIDIFile.decode(midi.encode())
        assert [(note.start, note.length) for note in decoded.track("Lead").notes] == [(0, 480), (480, 480)]

    @staticmethod
    def handmade(track: bytes) -> bytes:
        header = b"MThd" + bytes.fromhex("00000006 0000 0001 0060")
        return header + b"MTrk" + len(track).to_bytes(4, "big") + track

    def test_running_status_and_note_on_velocity_zero(self) -> None:
        # Format 0: note on, then running-status data bytes; a note on with velocity 0 is a note off.
        track = bytes.fromhex("00 90 3C 40 00 40 40 60 3C 00 00 40 00 00 FF 2F 00")
        decoded = MIDIFile.decode(TestMIDI.handmade(track))
        notes = decoded.tracks[0].notes
        assert [(note.start, note.length, note.pitch, note.velocity) for note in notes] == [(0, 96, 60, 64), (0, 96, 64, 64)]

    def test_track_without_end_of_track_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            MIDIFile.decode(TestMIDI.handmade(bytes.fromhex("00 90 3C 40 60 80 3C 40")))

    def test_rejects_smpte_division(self) -> None:
        data = b"MThd" + bytes.fromhex("00000006 0000 0001 E728") + b"MTrk" + bytes.fromhex("00000004 00 FF 2F 00")
        with pytest.raises(ValueError):
            MIDIFile.decode(data)

    def test_seconds_follow_tempo_changes(self) -> None:
        midi = MIDIFile(resolution=960, tempos=[Tempo(0, 120.0), Tempo(960 * 4, 60.0)])
        assert midi.seconds(960) == pytest.approx(0.5)
        assert midi.seconds(960 * 4) == pytest.approx(2.0)
        assert midi.seconds(960 * 5) == pytest.approx(3.0)

    @pytest.mark.parametrize("name,number", [("C4", 60), ("A4", 69), ("C-1", 0), ("G9", 127), ("F#3", 54), ("Bb2", 46)])
    def test_scientific_pitch_names(self, name: str, number: int) -> None:
        assert Pitch.parse(name) == number
        assert Pitch.parse(Pitch.name(number)) == number

    def test_concert_pitch(self) -> None:
        assert Pitch.frequency(69) == pytest.approx(440.0)
        assert Pitch.frequency(81) == pytest.approx(880.0)

    def test_unknown_chunks_are_skipped(self) -> None:
        # SMF 1.0: readers must ignore chunk types they do not recognise.
        midi = TestMIDI.sample().encode()
        alien = b"XFIH" + (4).to_bytes(4, "big") + b"data"
        data = midi[:14] + alien + midi[14:]
        assert MIDIFile.decode(data).track("Piano").notes == MIDIFile.decode(midi).track("Piano").notes

    def test_overlapping_notes_of_one_pitch_are_refused(self) -> None:
        midi = MIDIFile(tracks=[Track("Lead")])
        midi.tracks[0].add(0, 960, 60, 100)
        midi.tracks[0].add(480, 240, 60, 100)
        with pytest.raises(ValueError):
            midi.encode()

    def test_truncated_file_raises_value_error(self) -> None:
        data = TestMIDI.sample().encode()
        for cut in (10, 20, len(data) - 3):
            with pytest.raises(ValueError):
                MIDIFile.decode(data[:cut])

    @pytest.mark.parametrize("bpm", [0.0, 3.0, 61_000_000.0])
    def test_tempo_outside_24_bit_range_is_refused(self, bpm: float) -> None:
        with pytest.raises(ValueError):
            Tempo(0, bpm)

    def test_zero_tempo_event_is_refused(self) -> None:
        track = bytes.fromhex("00 FF 51 03 00 00 00 00 FF 2F 00")
        with pytest.raises(ValueError):
            MIDIFile.decode(TestMIDI.handmade(track))

    @pytest.mark.parametrize("sharps", [-8, 8])
    def test_key_signature_range(self, sharps: int) -> None:
        with pytest.raises(ValueError):
            KeySignature(sharps)
