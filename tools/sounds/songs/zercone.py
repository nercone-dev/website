from __future__ import annotations

from typing import ClassVar, Dict, List, Sequence, Tuple

from dsp import Additive, Analog, Clap, DrumKit, Envelope, Kick, Metal, Partial, Snare, Sweep, Tom
from effects import Delay, Limiter, Reverb
from midi import KeySignature, MIDIFile, Tempo
from mixer import Strip, Ducking, Master
from score import Part, Score, Song
from songs.zerc import Zerc

Melody = Tuple[Tuple[float, str, float], ...]

class Zercone(Song):
    # The Zerc motif grown into a piece. The three melody loops and the counter-line are the
    # ones from the original GarageBand project, note for note (C4 = middle C); harmony,
    # bass, drums, the arrangement and the ending were added here.
    name: ClassVar[str] = "zercone"
    title: ClassVar[str] = "Zercone"

    # Eight bars each. INTRO answers the motif with long notes every two bars, VERSE with
    # longer ones still, and MAIN repeats the motif every bar.
    INTRO: ClassVar[Melody] = (
        (0, "C3", 0.5), (0.5, "D3", 0.5), (0.75, "F3", 0.5), (0.75, "A3", 0.5), (1, "C4", 0.5), (1.5, "D4", 0.5), (2, "F4", 0.5), (2.5, "E4", 0.5), (3, "C4", 0.5), (3.5, "A3", 2), (5.5, "C4", 2.5),
        (8, "C3", 0.5), (8.5, "D3", 0.5), (8.75, "F3", 0.5), (8.75, "A3", 0.5), (9, "C4", 0.5), (9.5, "D4", 0.5), (10, "E4", 0.5), (10.5, "F4", 0.5), (11, "G4", 0.5), (11.5, "D4", 2), (13.5, "C4", 2.5),
        (16, "C3", 0.5), (16.5, "D3", 0.5), (16.75, "F3", 0.5), (16.75, "A3", 0.5), (17, "C4", 0.5), (17.5, "D4", 0.5), (18, "F4", 0.5), (18.5, "E4", 0.5), (19, "C4", 0.5), (19.5, "G4", 2.5), (22, "F4", 1), (23, "E4", 1),
        (24, "C3", 0.5), (24.5, "D3", 0.5), (24.75, "F3", 0.5), (24.75, "A3", 0.5), (25, "C4", 0.5), (25.5, "D4", 0.5), (26, "F4", 0.5), (26.5, "E4", 0.5), (27, "C4", 0.5), (27.5, "A3", 0.5), (28, "C4", 1.5), (29.5, "D4", 2.5),
    )
    VERSE: ClassVar[Melody] = (
        (0, "C3", 0.5), (0.5, "D3", 0.5), (0.75, "F3", 0.5), (0.75, "A3", 0.5), (1, "C4", 0.5), (1.5, "D4", 0.5), (2, "F4", 0.5), (2.5, "E4", 0.5), (3, "C4", 0.5), (3.5, "A3", 4.5),
        (8, "C3", 0.5), (8.5, "D3", 0.5), (8.75, "F3", 0.5), (8.75, "A3", 0.5), (9, "C4", 0.5), (9.5, "D4", 0.5), (10, "E4", 0.5), (10.5, "F4", 0.5), (11, "G4", 0.5), (11.5, "D4", 4.5),
        (16, "C3", 0.5), (16.5, "D3", 0.5), (16.75, "F3", 0.5), (16.75, "A3", 0.5), (17, "C4", 0.5), (17.5, "D4", 0.5), (18, "F4", 0.5), (18.5, "E4", 0.5), (19, "C4", 0.5), (19.5, "G4", 4.5),
        (24, "C3", 0.5), (24.5, "D3", 0.5), (24.75, "F3", 0.5), (24.75, "A3", 0.5), (25, "C4", 0.5), (25.5, "D4", 0.5), (26, "F4", 0.5), (26.5, "E4", 0.5), (27, "C4", 0.5), (27.5, "A3", 0.5), (28, "C4", 4),
    )
    MAIN: ClassVar[Melody] = (
        (0, "C3", 0.5), (0.5, "D3", 0.5), (0.75, "F3", 0.5), (0.75, "A3", 0.5), (1, "C4", 0.5), (1.5, "D4", 0.5), (2, "F4", 0.5), (2.5, "E4", 0.5), (3, "C4", 0.5), (3.5, "A3", 0.5),
        (4, "C3", 0.5), (4.5, "D3", 0.5), (4.75, "F3", 0.5), (4.75, "A3", 0.5), (5, "C4", 0.5), (5.5, "D4", 0.5), (6, "E4", 0.5), (6.5, "F4", 0.5), (7, "G4", 0.5), (7.5, "D4", 0.5),
        (8, "C3", 0.5), (8.5, "D3", 0.5), (8.75, "F3", 0.5), (8.75, "A3", 0.5), (9, "C4", 0.5), (9.5, "D4", 0.5), (10, "F4", 0.5), (10.5, "E4", 0.5), (11, "C4", 0.5), (11.5, "G4", 0.5),
        (12, "F4", 0.5), (12.5, "E4", 0.5), (13, "D4", 0.5), (13.5, "C4", 0.5), (14, "A3", 0.5), (14.5, "C4", 0.5), (15, "G3", 1),
        (16, "C3", 0.5), (16.5, "D3", 0.5), (16.75, "F3", 0.5), (16.75, "A3", 0.5), (17, "C4", 0.5), (17.5, "D4", 0.5), (18, "F4", 0.5), (18.5, "E4", 0.5), (19, "C4", 0.5), (19.5, "A3", 0.5),
        (20, "C3", 0.5), (20.5, "D3", 0.5), (20.75, "F3", 0.5), (20.75, "A3", 0.5), (21, "C4", 0.5), (21.5, "D4", 0.5), (22, "E4", 0.5), (22.5, "F4", 0.5), (23, "G4", 0.5), (23.5, "D4", 0.5),
        (24, "C3", 0.5), (24.5, "D3", 0.5), (24.75, "F3", 0.5), (24.75, "A3", 0.5), (25, "C4", 0.5), (25.5, "D4", 0.5), (26, "F4", 0.5), (26.5, "E4", 0.5), (27, "C4", 0.5), (27.5, "G4", 0.5),
        (28, "F4", 0.5), (28.5, "E4", 0.5), (29, "D4", 0.5), (29.5, "C4", 0.5), (30, "A3", 0.5), (30.5, "C4", 0.5), (31, "D4", 1),
    )
    # The "Emerald Haze" counter-line, one note per chord.
    HAZE: ClassVar[Melody] = ((0, "A3", 4), (4, "D4", 3.5), (7.5, "C4", 4), (11.5, "G3", 4.5), (16, "A3", 4), (20, "D4", 3.5), (23.5, "C4", 4), (27.5, "D4", 4.5))

    # One chord per bar under MAIN: IV ii I V / IV ii vi V in C major, the V as G7sus4 so the
    # loop floats back to F instead of closing. Each chord: bass root and upper voicing.
    CHORDS: ClassVar[Tuple[Tuple[str, Tuple[str, ...]], ...]] = (
        ("F2", ("F3", "A3", "C4", "E4")),
        ("D2", ("F3", "A3", "C4", "D4")),
        ("C2", ("E3", "G3", "C4", "D4")),
        ("G1", ("F3", "G3", "C4", "D4")),
        ("F2", ("F3", "A3", "C4", "E4")),
        ("D2", ("F3", "A3", "C4", "D4")),
        ("A1", ("E3", "G3", "A3", "C4")),
        ("G1", ("F3", "G3", "C4", "D4")),
    )

    # Arrangement, in 8-bar sections starting at these bars.
    BARS: ClassVar[int] = 88
    # General MIDI percussion keys, and the key the riser is played on.
    KICK: ClassVar[int] = 36
    SNARE: ClassVar[int] = 38
    CLAP: ClassVar[int] = 39
    HAT: ClassVar[int] = 42
    OPEN_HAT: ClassVar[int] = 46
    CRASH: ClassVar[int] = 49
    LOW_TOM: ClassVar[int] = 45
    HIGH_TOM: ClassVar[int] = 48
    SWEEP: ClassVar[int] = 60

    @staticmethod
    def beat(bar: int) -> float:
        return (bar - 1) * 4.0

    @staticmethod
    def melody(part: Part, bar: int, melody: Melody, velocity: int, transpose: int = 0) -> None:
        # The original notes all have velocity 98; shape them a little: the first note of each
        # bar leans in, off-beat eighths fall back, long notes sing.
        start = Zercone.beat(bar)
        for offset, pitch, length in melody:
            accent = 6 if offset % 4 == 0 else (-8 if offset % 1 else 0)
            accent += 4 if length >= 2 else 0
            part.note(start + offset, Part.pitch(pitch) + transpose, length, max(1, min(127, velocity + accent)))

    @staticmethod
    def progression(bar: int, slow: bool) -> Tuple[str, Tuple[str, ...]]:
        # The intro runs the same progression at half speed (two bars per chord), F Dm C Gsus.
        if slow:
            return Zercone.CHORDS[((bar - 1) % 8) // 2]
        return Zercone.CHORDS[(bar - 1) % 8]

    def compose(self) -> MIDIFile:
        midi = MIDIFile(title=self.title, tempos=[Tempo(0, 120.0)], key_signature=KeySignature(0, False))
        score = Score(midi)
        lead = score.part("Lead", channel=0, program=80)
        keys = score.part("Electric Piano", channel=1, program=4)
        harp = score.part("Harp", channel=2, program=46)
        haze = score.part("Haze", channel=3, program=91)
        pad = score.part("Pad", channel=4, program=89)
        bass = score.part("Bass", channel=5, program=38)
        drums = score.part("Drums", channel=9)
        effects = score.part("Effects", channel=6, program=122)
        ending_keys = score.part("Ending Keys", channel=7, program=4)
        ending_bells = score.part("Ending Bells", channel=8, program=8)

        # Lead: intro, verse, then the main loop; the verse returns as the outro.
        Zercone.melody(lead, 1, Zercone.INTRO, 86)
        Zercone.melody(lead, 9, Zercone.VERSE, 90)
        for bar in range(17, 81, 8):
            Zercone.melody(lead, bar, Zercone.MAIN, 94 if bar < 73 else 100)
        Zercone.melody(lead, 81, Zercone.VERSE, 84)

        # Electric piano: doubles the main loop against the verse (as in the original), then
        # turns into syncopated chord comping in the second half.
        for bar in (9, 17):
            Zercone.melody(keys, bar, Zercone.MAIN, 74)
        for bar in list(range(41, 65)) + list(range(73, 81)):
            _, voicing = Zercone.progression(bar, False)
            start = Zercone.beat(bar)
            for offset, length, velocity in ((0.0, 1.4, 80), (1.5, 0.9, 66), (3.0, 0.45, 70), (3.5, 0.45, 62)):
                keys.chord(start + offset, voicing, length, velocity, strum=0.012)

        # Harp: the main loop an octave up, a bell-like halo over the lead.
        for bar in (49, 57, 73):
            Zercone.melody(harp, bar, Zercone.MAIN, 70, transpose=12)

        # Haze counter-line from bar 57 to the end.
        for bar in range(57, 89, 8):
            Zercone.melody(haze, bar, Zercone.HAZE, 78)

        # Pad and bass.
        for bar in range(1, Zercone.BARS + 1):
            slow = bar <= 8
            if slow and bar % 2 == 0:
                continue
            root, voicing = Zercone.progression(bar, slow)
            start = Zercone.beat(bar)
            length = 8.0 if slow else 4.0
            pad.chord(start, voicing, length, 70 if bar < 73 else 76)
            drummed = 17 <= bar <= 24 or 33 <= bar <= 80
            if bar < 9:
                continue
            if drummed:
                for offset, size, velocity, octave in ((0.0, 1.5, 104, 0), (1.5, 0.5, 84, 0), (2.0, 1.0, 96, 0), (3.0, 0.5, 80, 12), (3.5, 0.5, 86, 0)):
                    bass.note(start + offset, Part.pitch(root) + octave, size - 0.05, velocity)
            else:
                bass.note(start, root, 3.95, 92 if bar < 81 else 80)
        pad.ramp(11, 0.0, 16.0, 40, 110, step=0.25)
        pad.ramp(11, Zercone.beat(81), Zercone.beat(89), 110, 70, step=0.25)

        self.drums(drums)

        # Risers into the full sections.
        for bar in (31, 71):
            effects.note(Zercone.beat(bar), Zercone.SWEEP, 8.0, 100)

        # Ending: the Zerc startup chord, as the last thing the song says.
        end = Zercone.beat(Zercone.BARS + 1)
        for beat, pitch, velocity in Zerc.MOTIF:
            ending_keys.note(end + beat, pitch, Zerc.END - beat, velocity)
            ending_bells.note(end + beat, Part.pitch(pitch) + 12, Zerc.END - beat, velocity - 12)
        pad.chord(end, ("F2", "C3", "F3", "A3"), 5.0, 72)
        bass.note(end, "F1", 4.5, 96)
        return midi

    def drums(self, part: Part) -> None:
        light = set(range(17, 25)) | set(range(65, 73))
        full = set(range(33, 65)) | set(range(73, 81))
        for bar in range(1, Zercone.BARS + 1):
            if bar not in light and bar not in full:
                continue
            start = Zercone.beat(bar)
            hits: List[Tuple[float, int, int]] = []
            section_start = bar in (17, 33, 41, 49, 57, 65, 73)
            section_end = (bar + 1) in (25, 33, 41, 49, 57, 65, 73, 81)
            if section_start:
                hits.append((0.0, Zercone.CRASH, 96))
            if bar in light:
                hits += [(0.0, Zercone.KICK, 100), (2.5, Zercone.KICK, 80), (1.0, Zercone.CLAP, 70), (3.0, Zercone.CLAP, 74)]
                hits += [(eighth * 0.5, Zercone.HAT, 52 if eighth % 2 else 66) for eighth in range(8)]
            else:
                hits += [(0.0, Zercone.KICK, 108), (1.5, Zercone.KICK, 86), (2.0, Zercone.KICK, 100), (1.0, Zercone.SNARE, 104), (3.0, Zercone.SNARE, 108), (1.0, Zercone.CLAP, 64), (3.0, Zercone.CLAP, 68)]
                for sixteenth in range(16):
                    if sixteenth == 14 and bar % 2 == 0:
                        hits.append((3.5, Zercone.OPEN_HAT, 70))
                    elif sixteenth % 2 == 0 or sixteenth in (7, 15):
                        hits.append((sixteenth * 0.25, Zercone.HAT, 76 if sixteenth % 4 == 0 else (60 if sixteenth % 2 == 0 else 44)))
            if section_end:
                hits = [hit for hit in hits if hit[0] < 2.0]
                fill: Sequence[Tuple[float, int, int]] = [
                    (2.0, Zercone.SNARE, 70), (2.25, Zercone.SNARE, 76), (2.5, Zercone.HIGH_TOM, 86), (2.75, Zercone.HIGH_TOM, 84),
                    (3.0, Zercone.LOW_TOM, 92), (3.25, Zercone.LOW_TOM, 90), (3.5, Zercone.SNARE, 100), (3.75, Zercone.SNARE, 110),
                ] if bar in full else [(2.0, Zercone.KICK, 84), (3.0, Zercone.CLAP, 80), (3.5, Zercone.CLAP, 88), (3.75, Zercone.CLAP, 96)]
                hits += list(fill)
            for offset, pitch, velocity in hits:
                part.note(start + offset, pitch, 0.25, velocity)

    def strips(self) -> Dict[str, Strip]:
        lead = Analog(
            "square", voices=2, detune=6.0, width=0.5,
            amplitude=Envelope(0.003, 0.9, 0.45, 0.28),
            cutoff=1500.0, keytrack=0.7,
            contour=Envelope(0.002, 0.45, 0.2, 0.25), amount=2.0, velocity_amount=0.6,
            poles=2, resonance=0.25, sub=0.15, drift=1.5, seed=21,
        )
        harp = Additive(
            tuple(Partial(float(k), 0.8 / k ** 1.3, 2.6 / k ** 0.6) for k in range(1, 9)),
            attack=0.002, release=0.5, tracking=0.6, brightness=1.0, detune=3.0, width=0.7, hammer=0.25, seed=22,
        )
        haze = Analog(
            "saw", voices=5, detune=10.0, width=0.8,
            amplitude=Envelope(0.35, 1.5, 0.85, 0.9, curve=1.3),
            cutoff=1400.0, keytrack=0.5, contour=Envelope(0.6, 2.0, 0.6, 0.9), amount=0.8, velocity_amount=0.4,
            poles=2, vibrato_rate=5.2, vibrato_depth=9.0, vibrato_delay=0.6, drift=2.0, seed=23,
        )
        bass = Analog(
            "saw", voices=1,
            amplitude=Envelope(0.004, 0.7, 0.55, 0.08),
            cutoff=220.0, keytrack=0.6, contour=Envelope(0.002, 0.25, 0.0, 0.1), amount=1.6,
            poles=4, sub=0.6, seed=24,
        )
        drums = DrumKit({
            Zercone.KICK: Kick(start=150.0, end=47.0, sweep=0.032, decay=0.42, click=0.3, drive=1.6),
            Zercone.SNARE: Snare(tone=190.0, tone_decay=0.12, noise_decay=0.2, snap=0.75),
            Zercone.CLAP: Clap(),
            Zercone.HAT: Metal(decay=0.055, highpass=7500.0, noise=0.6),
            Zercone.OPEN_HAT: Metal(decay=0.32, highpass=7000.0, noise=0.6),
            Zercone.CRASH: Metal(decay=2.2, highpass=4500.0, noise=0.9, tone=1.3),
            Zercone.LOW_TOM: Tom(frequency=105.0, decay=0.45),
            Zercone.HIGH_TOM: Tom(frequency=150.0, decay=0.38),
        })
        return {
            "Lead": Strip(lead, gain=-1.0, pan=0.0, reverb=0.18, delay=0.16),
            "Electric Piano": Strip(Zerc.keys(), gain=-9.0, pan=-0.25, reverb=0.2, duck=0.15),
            "Harp": Strip(harp, gain=-12.0, pan=0.3, reverb=0.35, delay=0.2),
            "Haze": Strip(haze, gain=-11.0, pan=-0.15, reverb=0.4, duck=0.2),
            "Pad": Strip(Zerc.pad(), gain=-15.0, reverb=0.35, duck=0.35, highpass=120.0),
            "Bass": Strip(bass, gain=-8.0, reverb=0.02, duck=0.25, drive=1.3),
            "Drums": Strip(drums, gain=-5.0, reverb=0.08),
            "Effects": Strip(Sweep(low=250.0, high=9000.0), gain=-12.0, reverb=0.5),
            "Ending Keys": Strip(Zerc.keys(), gain=-3.0, reverb=0.25, delay=0.05),
            "Ending Bells": Strip(Zerc.bells(), gain=-6.0, pan=0.1, reverb=0.45, delay=0.18),
        }

    def master(self) -> Master:
        return Master(
            reverb=Reverb(decay=2.4, damping=0.42, predelay=0.022, buildup=0.03, early=0.3, seed=12),
            delay=Delay(time=0.375, feedback=0.38, repeats=6, lowcut=400.0, highcut=5500.0),
            ducking=Ducking("Drums", (Zercone.KICK,), attack=0.005, release=0.25),
            loudness=-16.0,
            limiter=Limiter(ceiling=-1.0),
            tail=3.5,
            fade=1.5,
        )
