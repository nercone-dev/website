from __future__ import annotations

from typing import ClassVar, Dict, Tuple

from dsp import FM, Additive, Analog, Envelope, Partial
from effects import Delay, Limiter, Reverb
from midi import KeySignature, MIDIFile, Tempo
from mixer import Strip, Master
from score import Score, Song

class Zerc(Song):
    # NecOS startup sound.
    #
    # The motif is the one from the original GarageBand project: C3 D3 F3+A3 C4 D4 (in
    # scientific pitch, C4 = middle C), entering at 0, 1/2, 3/4, 3/4, 1 and 3/2 beats at
    # 120 BPM. The gaps (1/4, 1/8, 0, 1/8, 1/4 s) are a palindrome, so the motif is point
    # symmetric in time like the NecOS mark.
    #
    # The NecOS mark is two strokes, a white one and a grey one, crossing in the middle.
    # The sound has the same two strokes: a bright struck "white" layer (keys and bells
    # playing the motif) and a soft "grey" layer (pad, bass and air) that blooms under it.
    # An F root under the motif turns it into F6/9: open and major like a classic startup
    # chord, and the same harmony that opens Zercone.
    name: ClassVar[str] = "zerc"
    title: ClassVar[str] = "Zerc"

    MOTIF: ClassVar[Tuple[Tuple[float, str, int], ...]] = (
        (0.0, "C3", 84),
        (0.5, "D3", 80),
        (0.75, "F3", 78),
        (0.75, "A3", 76),
        (1.0, "C4", 86),
        (1.5, "D4", 96),
    )
    END: ClassVar[float] = 4.0

    def compose(self) -> MIDIFile:
        midi = MIDIFile(title=self.title, tempos=[Tempo(0, 120.0)], key_signature=KeySignature(-1, False))
        score = Score(midi)

        keys = score.part("Keys", channel=0, program=4)
        bells = score.part("Bells", channel=1, program=8)
        for beat, pitch, velocity in Zerc.MOTIF:
            keys.note(beat, pitch, Zerc.END - beat, velocity)
            bells.note(beat, keys.pitch(pitch) + 12, Zerc.END - beat, velocity - 12)

        pad = score.part("Pad", channel=2, program=89)
        pad.chord(0.0, ("F2", "C3", "F3", "A3"), 5.0, 72)

        bass = score.part("Bass", channel=3, program=38)
        bass.note(0.0, "F1", 4.5, 100)
        bass.note(0.0, "F2", 4.5, 64)

        air = score.part("Air", channel=4, program=88)
        air.chord(1.5, ("A5", "D6"), 3.0, 60)
        return midi

    @staticmethod
    def keys() -> FM:
        return FM(
            ratio=1.0, index=2.6, index_decay=1.2, index_floor=0.45,
            amplitude=Envelope(0.003, 5.0, 0.0, 1.4),
            tine_ratio=14.0, tine_index=1.5, tine_decay=0.07, tine_level=0.2,
            detune=3.0, tracking=0.4,
        )

    @staticmethod
    def bells() -> Additive:
        return Additive(
            (
                Partial(1.0, 1.0, 5.0),
                Partial(2.0, 0.45, 3.2),
                Partial(3.0, 0.22, 2.0),
                Partial(4.16, 0.12, 1.2),
                Partial(5.43, 0.07, 0.8),
                Partial(6.79, 0.04, 0.5),
            ),
            attack=0.0015, release=1.6, tracking=0.5, brightness=0.8, detune=4.0, width=0.8,
        )

    @staticmethod
    def pad() -> Analog:
        return Analog(
            "saw", voices=7, detune=16.0, width=0.9,
            amplitude=Envelope(0.9, 2.5, 0.8, 1.8, curve=1.5),
            cutoff=1100.0, keytrack=0.3,
            contour=Envelope(1.6, 3.0, 0.5, 1.8), amount=1.4, velocity_amount=0.3,
            poles=2, drift=2.0, seed=2,
        )

    @staticmethod
    def bass() -> Analog:
        return Analog(
            "triangle", voices=1,
            amplitude=Envelope(0.025, 3.5, 0.55, 1.4),
            cutoff=320.0, keytrack=0.0, poles=2,
        )

    def strips(self) -> Dict[str, Strip]:
        keys, bells, pad, bass = Zerc.keys(), Zerc.bells(), Zerc.pad(), Zerc.bass()
        air = Analog(
            "triangle", voices=3, detune=6.0, width=1.0,
            amplitude=Envelope(1.0, 2.0, 0.8, 2.0, curve=1.5),
            cutoff=7000.0, keytrack=0.0, vibrato_rate=4.5, vibrato_depth=5.0, vibrato_delay=0.5, seed=5,
        )
        return {
            "Keys": Strip(keys, gain=-3.0, reverb=0.22, delay=0.05),
            "Bells": Strip(bells, gain=-6.0, pan=0.1, reverb=0.45, delay=0.18),
            "Pad": Strip(pad, gain=-12.0, reverb=0.4, highpass=90.0),
            "Bass": Strip(bass, gain=-10.0, reverb=0.04, drive=1.2),
            "Air": Strip(air, gain=-11.0, pan=-0.1, reverb=0.7),
        }

    def master(self) -> Master:
        return Master(
            reverb=Reverb(decay=2.8, damping=0.4, predelay=0.025, buildup=0.04, early=0.3, seed=11),
            delay=Delay(time=0.375, feedback=0.35, repeats=5, lowcut=400.0, highcut=6000.0),
            loudness=-16.0,
            limiter=Limiter(ceiling=-1.0),
            tail=3.0,
            fade=1.2,
        )
