from __future__ import annotations

from typing import ClassVar, Dict, Tuple

from effects import Limiter
from midi import MIDIFile
from dsp import DrumKit
from mixer import Ducking, Master, Strip
from score import Part
from songs.interface import Interface
from songs.zerc import Zerc

class Ringtone(Interface):
    # An incoming call. It must be recognisable as "my phone" across a room, so it is built
    # on the Zerc motif itself (C D F+A C D, with the same rhythm), two octaves up in the range
    # small speakers reproduce well, on round tones doubled by a synth pluck with a sine
    # shimmer above. The motif stays the same every bar while the harmony moves under it
    # (F6/9, Dm7, B-flat maj9, Csus4: the motif fits all four), and a whistle-like lead
    # answers each time with a descending line (A G, F D, C A, D G) that turns up at the end
    # to lead back to the start. A light beat (soft kick, clap and hats, with the pad ducking
    # under the kick) gives it the pulse of current electronic ringtones. Everything above the bass uses only the pentatonic notes of
    # the motif (F G A C D), and the last bar stays suspended instead of resolving through E,
    # so no two notes a semitone apart sound together, even in the echoes and the tail that
    # the loop folds onto its start. A seamless 8 s loop; play it repeated while the call rings.
    name: ClassVar[str] = "ringtone"
    title: ClassVar[str] = "Ringtone"

    # (bass, pad voicing, the answer) for each bar.
    BARS: ClassVar[Tuple[Tuple[str, Tuple[str, ...], Tuple[str, str]], ...]] = (
        ("F2", ("F3", "A3", "C4", "G4"), ("A5", "G5")),
        ("D2", ("D3", "F3", "A3", "C4"), ("F5", "D5")),
        ("Bb1", ("F3", "A3", "C4", "D4"), ("C5", "A4")),
        ("C2", ("F3", "G3", "C4", "D4"), ("D5", "G5")),
    )
    # The motif rings until this beat of each bar, and in the last one until END, so that
    # little of it rings on into the start (the folded tail is also what the first pass of
    # the loop starts with).
    HOLD: ClassVar[float] = 3.5
    END: ClassVar[float] = 3.0
    LOOP: ClassVar[float] = 16.0
    # (beat, General MIDI key, velocity) of the beat in every bar.
    KICK: ClassVar[int] = 36
    CLAP: ClassVar[int] = 39
    HAT: ClassVar[int] = 42
    BEAT: ClassVar[Tuple[Tuple[float, int, int], ...]] = (
        (0.0, KICK, 92), (2.0, KICK, 84), (1.0, CLAP, 64), (3.0, CLAP, 68),
        (0.5, HAT, 44), (1.5, HAT, 48), (2.5, HAT, 44), (3.5, HAT, 50),
    )

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        tone = score.part("Tone", channel=0, program=80)
        pluck = score.part("Pluck", channel=5, program=84)
        shimmer = score.part("Shimmer", channel=1, program=81)
        whistle = score.part("Whistle", channel=2, program=78)
        pad = score.part("Pad", channel=3, program=89)
        bass = score.part("Bass", channel=4, program=33)
        drums = score.part("Drums", channel=9)
        for bar, (root, voicing, answer) in enumerate(Ringtone.BARS):
            start = bar * 4.0
            last = bar == len(Ringtone.BARS) - 1
            hold = Ringtone.END if last else Ringtone.HOLD
            for offset, pitch, velocity in Zerc.MOTIF:
                note = Part.pitch(pitch) + 24
                tone.note(start + offset, note, hold - offset, velocity + 4)
                pluck.note(start + offset, note, 0.3, velocity - 4)
                shimmer.note(start + offset, note + 12, 0.4, velocity - 16)
            whistle.note(start + 2.0, answer[0], 0.9, 92)
            whistle.note(start + 3.0, answer[1], 0.5 if last else 0.9, 86)
            for beat, key, velocity in Ringtone.BEAT:
                drums.note(start + beat, key, 0.25, velocity)
            pad.chord(start, voicing, 3.0 if last else 4.0, 72)
            bass.note(start, root, 2.5, 96)
            bass.note(start + 2.5, root, 1.4, 84)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Tone": Strip(Interface.tone(), gain=-3.0, reverb=0.22, delay=0.06),
            "Pluck": Strip(Interface.pluck(), gain=-5.0, pan=-0.15, reverb=0.25),
            "Shimmer": Strip(Interface.shimmer(), gain=-10.0, pan=0.25, reverb=0.4, delay=0.2),
            "Whistle": Strip(Interface.whistle(), gain=-4.0, pan=0.12, reverb=0.3, delay=0.12),
            "Pad": Strip(Interface.pad(), gain=-13.0, reverb=0.35, highpass=150.0, duck=0.25),
            "Bass": Strip(Interface.bass(), gain=-13.0, reverb=0.03, duck=0.15),
            "Drums": Strip(DrumKit({
                Ringtone.KICK: Interface.kick(),
                Ringtone.CLAP: Interface.clap(),
                Ringtone.HAT: Interface.shaker(),
            }), gain=-4.0, reverb=0.08, lowpass=9500.0),
        }

    def master(self) -> Master:
        return Master(
            reverb=Interface.room(), delay=Interface.echo(), ducking=Ducking("Drums", pitches=(Ringtone.KICK,)),
            loudness=-14.0, limiter=Limiter(ceiling=-1.0), tail=4.0, loop=Interface.seconds(Ringtone.LOOP),
        )
