from __future__ import annotations

from typing import ClassVar, Dict, List, Tuple

from dsp import Analog, Clap, DrumKit, Envelope, Kick, Metal, Snare, Sweep, Tom
from effects import Delay, Limiter, Reverb
from midi import KeySignature, MIDIFile, Tempo
from mixer import Strip, Ducking, Master
from score import Part, Score, Song
from songs.zerc import Zerc

class Mirai(Song):
    # "Mirai" (future). The GarageBand version was assembled from Apple Loops; this one keeps
    # its tempo (128 BPM), key (A minor), four-bar harmony (Fmaj7 Fmaj7 Am7 Cmaj7) and section
    # layout, and replaces every loop with parts written here.
    name: ClassVar[str] = "mirai"
    title: ClassVar[str] = "Mirai"

    BARS: ClassVar[int] = 80
    # (bass root, pad voicing, arpeggio tones low to high)
    CHORDS: ClassVar[Tuple[Tuple[str, Tuple[str, ...], Tuple[str, ...]], ...]] = (
        ("F1", ("F3", "A3", "C4", "E4", "G4"), ("F4", "A4", "C5", "E5", "G5")),
        ("F1", ("F3", "A3", "C4", "E4", "G4"), ("F4", "A4", "C5", "E5", "G5")),
        ("A1", ("G3", "A3", "C4", "E4", "B4"), ("E4", "A4", "C5", "E5", "G5")),
        ("C2", ("G3", "B3", "C4", "E4", "G4"), ("E4", "G4", "B4", "C5", "E5")),
    )
    # Indices into the arpeggio tones, one per sixteenth note of a bar.
    ARPEGGIO: ClassVar[Tuple[int, ...]] = (0, 2, 1, 3, 2, 4, 3, 2, 0, 2, 1, 3, 4, 3, 2, 1)
    # Sixteen bars of melody over four passes of the harmony (beats from bar 49).
    MELODY: ClassVar[Tuple[Tuple[float, str, float], ...]] = (
        (0, "E5", 1.5), (1.5, "D5", 0.5), (2, "C5", 1), (3, "A4", 1),
        (4, "C5", 2), (6, "G4", 1), (7, "A4", 1),
        (8, "E5", 3), (11, "D5", 0.5), (11.5, "C5", 0.5),
        (12, "B4", 1.5), (13.5, "C5", 0.5), (14, "G4", 2),
        (16, "A4", 0.5), (16.5, "C5", 0.5), (17, "E5", 1), (18, "F5", 1.5), (19.5, "E5", 0.5),
        (20, "D5", 1), (21, "C5", 1), (22, "A4", 2),
        (24, "C5", 1), (25, "B4", 0.5), (25.5, "A4", 0.5), (26, "E5", 2),
        (28, "D5", 1), (29, "C5", 1), (30, "E5", 2),
        (32, "A5", 1.5), (33.5, "G5", 0.5), (34, "E5", 1), (35, "C5", 1),
        (36, "E5", 2), (38, "D5", 1), (39, "C5", 1),
        (40, "E5", 1), (41, "G5", 1), (42, "A5", 2),
        (44, "G5", 1.5), (45.5, "E5", 0.5), (46, "D5", 1), (47, "E5", 1),
        (48, "F5", 1.5), (49.5, "E5", 0.5), (50, "C5", 1), (51, "A4", 1),
        (52, "C5", 1.5), (53.5, "D5", 0.5), (54, "E5", 2),
        (56, "A4", 1), (57, "C5", 1), (58, "B4", 1), (59, "G4", 1),
        (60, "A4", 4),
    )
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
    def chord(bar: int) -> Tuple[str, Tuple[str, ...], Tuple[str, ...]]:
        return Mirai.CHORDS[(bar - 1) % 4]

    @staticmethod
    def within(bar: int, *ranges: Tuple[int, int]) -> bool:
        return any(first <= bar <= last for first, last in ranges)

    def compose(self) -> MIDIFile:
        midi = MIDIFile(title=self.title, tempos=[Tempo(0, 128.0)], key_signature=KeySignature(0, True))
        score = Score(midi)
        pad = score.part("Chords", channel=0, program=90)
        bass = score.part("Bass", channel=1, program=38)
        arpeggio = score.part("Arpeggio", channel=2, program=80)
        lead = score.part("Lead", channel=3, program=81)
        bells = score.part("Bells", channel=4, program=8)
        drums = score.part("Drums", channel=9)
        effects = score.part("Effects", channel=5, program=122)

        for bar in range(1, Mirai.BARS + 1):
            root, voicing, tones = Mirai.chord(bar)
            start = Mirai.beat(bar)
            # Chords: a held voicing; velocity (and with it the filter) rises through the intro
            # and falls through the outro.
            if bar <= 8:
                velocity = 56 + bar * 5
            elif bar >= 73:
                velocity = 96 - (bar - 72) * 5
            else:
                velocity = 92 if Mirai.within(bar, (17, 40), (57, 64)) else 84
            pad.chord(start, voicing, 4.0, velocity, strum=0.01)

            # Bass: sustained in the quiet parts, an eighth-note pulse with the drums.
            if Mirai.within(bar, (17, 40), (57, 72)):
                for eighth in range(8):
                    octave = 12 if eighth in (3, 7) else 0
                    bass.note(start + eighth * 0.5, Part.pitch(root) + 12 + octave, 0.42, 100 if eighth % 2 == 0 else 82)
            elif Mirai.within(bar, (5, 16), (41, 56), (73, 78)):
                bass.note(start, Part.pitch(root) + 12, 3.9, 88)

            # Arpeggio in sixteenths.
            if Mirai.within(bar, (17, 32), (65, 72)):
                for sixteenth, index in enumerate(Mirai.ARPEGGIO):
                    accent = 92 if sixteenth % 4 == 0 else (72 if sixteenth % 2 == 0 else 60)
                    arpeggio.note(start + sixteenth * 0.25, tones[index], 0.22, accent)

            # Bells: a slow dotted pattern over the upper chord tones in the middle sections.
            if Mirai.within(bar, (33, 48)):
                for offset, index, velocity in ((0.0, 4, 78), (1.5, 3, 66), (3.0, 2, 70)):
                    bells.note(start + offset, Part.pitch(tones[index]) + 12, 1.5, velocity)

        for offset, pitch, length in Mirai.MELODY:
            beat = Mirai.beat(49) + offset
            accent = 8 if offset % 4 == 0 else (-6 if offset % 1 else 0)
            lead.note(beat, pitch, length, 96 + accent)

        self.drums(drums)

        for bar in (15, 47, 55):
            effects.note(Mirai.beat(bar), Mirai.SWEEP, 8.0, 100)

        # Ending: resolve to A minor (add 9) and let it ring.
        end = Mirai.beat(Mirai.BARS + 1)
        pad.chord(end, ("A3", "C4", "E4", "B4"), 6.0, 70)
        bass.note(end, "A2", 6.0, 80)
        for offset, pitch, velocity in ((0.0, "A5", 70), (0.5, "B5", 62), (1.0, "C6", 66), (1.5, "E6", 72)):
            bells.note(end + offset, pitch, 4.0, velocity)
        return midi

    def drums(self, part: Part) -> None:
        starts = (9, 17, 33, 57)
        ends = (16, 32, 40, 64)
        for bar in range(1, Mirai.BARS + 1):
            light = Mirai.within(bar, (9, 16), (65, 72))
            full = Mirai.within(bar, (17, 40), (57, 64))
            if not light and not full:
                continue
            start = Mirai.beat(bar)
            hits: List[Tuple[float, int, int]] = []
            if bar in starts:
                hits.append((0.0, Mirai.CRASH, 100))
            if full:
                hits += [(0.0, Mirai.KICK, 110), (1.5, Mirai.KICK, 92), (2.5, Mirai.KICK, 100), (1.0, Mirai.SNARE, 108), (3.0, Mirai.SNARE, 112), (1.0, Mirai.CLAP, 70), (3.0, Mirai.CLAP, 74)]
                for sixteenth in range(16):
                    if sixteenth == 14 and bar % 2 == 0:
                        hits.append((3.5, Mirai.OPEN_HAT, 72))
                    elif sixteenth % 2 == 0:
                        hits.append((sixteenth * 0.25, Mirai.HAT, 80 if sixteenth % 4 == 2 else 62))
                    elif sixteenth in (5, 13):
                        hits.append((sixteenth * 0.25, Mirai.HAT, 42))
            elif bar <= 16:
                hits += [(0.0, Mirai.KICK, 96), (2.5, Mirai.KICK, 84), (1.0, Mirai.CLAP, 66), (3.0, Mirai.CLAP, 70)]
                hits += [(eighth * 0.5, Mirai.HAT, 68 if eighth % 2 else 54) for eighth in range(8)]
            else:
                # Bars 65-72: the beat thins out to hats and claps on the way to the outro.
                hits += [(1.0, Mirai.CLAP, 60), (3.0, Mirai.CLAP, 64)]
                hits += [(eighth * 0.5, Mirai.HAT, 60 if eighth % 2 else 46) for eighth in range(8)]
            if bar in ends:
                hits = [hit for hit in hits if hit[0] < 2.0]
                hits += [
                    (2.0, Mirai.SNARE, 72), (2.25, Mirai.SNARE, 78), (2.5, Mirai.HIGH_TOM, 88), (2.75, Mirai.HIGH_TOM, 86),
                    (3.0, Mirai.LOW_TOM, 94), (3.25, Mirai.LOW_TOM, 92), (3.5, Mirai.SNARE, 104), (3.75, Mirai.SNARE, 114),
                ]
            for offset, pitch, velocity in hits:
                part.note(start + offset, pitch, 0.25, velocity)

    def strips(self) -> Dict[str, Strip]:
        pad = Analog(
            "saw", voices=7, detune=20.0, width=1.0,
            amplitude=Envelope(0.08, 1.5, 0.85, 0.6, curve=1.2),
            cutoff=700.0, keytrack=0.3, contour=Envelope(0.25, 1.8, 0.55, 0.6), amount=1.8, velocity_amount=0.9,
            poles=2, drift=3.0, seed=31,
        )
        bass = Analog(
            "saw", voices=1,
            amplitude=Envelope(0.003, 0.5, 0.6, 0.06),
            cutoff=260.0, keytrack=0.5, contour=Envelope(0.002, 0.18, 0.0, 0.08), amount=1.5,
            poles=4, sub=0.7, seed=32,
        )
        arpeggio = Analog(
            "square", voices=2, detune=7.0, width=0.6,
            amplitude=Envelope(0.002, 0.3, 0.0, 0.08),
            cutoff=1900.0, keytrack=0.5, contour=Envelope(0.001, 0.16, 0.0, 0.08), amount=2.2, velocity_amount=0.7,
            poles=2, resonance=0.3, seed=33,
        )
        lead = Analog(
            "saw", voices=3, detune=8.0, width=0.5,
            amplitude=Envelope(0.012, 0.8, 0.8, 0.3),
            cutoff=2200.0, keytrack=0.4, contour=Envelope(0.005, 0.5, 0.35, 0.3), amount=1.2, velocity_amount=0.5,
            poles=2, vibrato_rate=5.5, vibrato_depth=14.0, vibrato_delay=0.25, drift=1.5, seed=34,
        )
        drums = DrumKit({
            Mirai.KICK: Kick(start=170.0, end=50.0, sweep=0.03, decay=0.38, click=0.35, drive=1.8),
            Mirai.SNARE: Snare(tone=200.0, tone_decay=0.11, noise_decay=0.22, snap=0.85),
            Mirai.CLAP: Clap(),
            Mirai.HAT: Metal(decay=0.05, highpass=8000.0, noise=0.6),
            Mirai.OPEN_HAT: Metal(decay=0.3, highpass=7500.0, noise=0.6),
            Mirai.CRASH: Metal(decay=2.4, highpass=4500.0, noise=0.9, tone=1.3),
            Mirai.LOW_TOM: Tom(frequency=100.0, decay=0.45),
            Mirai.HIGH_TOM: Tom(frequency=145.0, decay=0.38),
        })
        return {
            "Chords": Strip(pad, gain=-9.0, reverb=0.3, duck=0.45, highpass=110.0),
            "Bass": Strip(bass, gain=-6.0, reverb=0.02, duck=0.35, drive=1.4),
            "Arpeggio": Strip(arpeggio, gain=-5.0, pan=0.15, reverb=0.25, delay=0.3, duck=0.2),
            "Lead": Strip(lead, gain=-3.0, reverb=0.25, delay=0.2),
            "Bells": Strip(Zerc.bells(), gain=-12.0, pan=-0.2, reverb=0.45, delay=0.2),
            "Drums": Strip(drums, gain=-4.0, reverb=0.07),
            "Effects": Strip(Sweep(low=250.0, high=10000.0), gain=-12.0, reverb=0.5),
        }

    def master(self) -> Master:
        return Master(
            reverb=Reverb(decay=2.2, damping=0.4, predelay=0.02, buildup=0.03, early=0.3, seed=13),
            delay=Delay(time=60.0 / 128.0 * 0.75, feedback=0.4, repeats=6, lowcut=400.0, highcut=6000.0),
            ducking=Ducking("Drums", (Mirai.KICK,), attack=0.005, release=0.22),
            loudness=-15.0,
            limiter=Limiter(ceiling=-1.0),
            tail=3.5,
            fade=1.5,
        )
