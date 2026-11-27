from __future__ import annotations

from typing import ClassVar, Dict, Tuple

from effects import Limiter
from midi import MIDIFile
from mixer import Ducking, Master, Strip
from score import Part
from songs.interface import Interface

class DefaultAlarm(Interface):
    # Alarms and timers: the cadence of an alarm clock (four quick notes, a rest, repeat),
    # which everyone recognises at once, played as chord arpeggios on a synth pluck, round
    # tones and the chime instead of a buzzer beep, over a pad and bass that hold each chord
    # through the rest.
    # A seamless 4 s loop; play it repeated until stopped.
    name: ClassVar[str] = "alarm-default"
    title: ClassVar[str] = "Alarm"

    # (beat, four pitches, pad voicing, bass): F twice, then G-D-A (the suspended colour of
    # the warnings) and F an octave higher, so the second bar rises and leans back to the start.
    GROUPS: ClassVar[Tuple[Tuple[float, Tuple[str, str, str, str], Tuple[str, ...], str], ...]] = (
        (0.0, ("F6", "C6", "A5", "C6"), ("F3", "A3", "C4", "G4"), "F2"),
        (2.0, ("F6", "C6", "A5", "C6"), ("F3", "A3", "C4", "G4"), "F2"),
        (4.0, ("G6", "D6", "A5", "D6"), ("G3", "A3", "D4", "G4"), "G2"),
        (6.0, ("A6", "F6", "C6", "F6"), ("F3", "A3", "C4", "G4"), "F2"),
    )
    # Velocities of the four notes of a group: an accent, then a slight lilt.
    ACCENTS: ClassVar[Tuple[int, int, int, int]] = (104, 90, 95, 88)
    LOOP: ClassVar[float] = 8.0

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        pluck = score.part("Pluck", channel=0, program=84)
        tone = score.part("Tone", channel=5, program=80)
        chime = score.part("Chime", channel=1, program=11)
        shimmer = score.part("Shimmer", channel=2, program=81)
        pad = score.part("Pad", channel=3, program=89)
        bass = score.part("Bass", channel=4, program=33)
        for group, (beat, pitches, voicing, root) in enumerate(DefaultAlarm.GROUPS):
            for index, pitch in enumerate(pitches):
                velocity = DefaultAlarm.ACCENTS[index] - (group % 2) * 3
                pluck.note(beat + index * 0.25, pitch, 0.2, velocity)
                tone.note(beat + index * 0.25, pitch, 0.2, velocity - 8)
                chime.note(beat + index * 0.25, Part.pitch(pitch) - 12, 0.16, velocity - 20)
            shimmer.note(beat, pitches[0], 0.5, 70)
            # The last chord is cut short, so little of it rings on into the start of the loop.
            pad.chord(beat, voicing, 1.5 if group == len(DefaultAlarm.GROUPS) - 1 else 2.0, 74)
            bass.note(beat, root, 1.0, 92)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Pluck": Strip(Interface.pluck(), gain=-3.0, pan=-0.1, reverb=0.18),
            "Tone": Strip(Interface.tone(), gain=-6.0, reverb=0.18),
            "Chime": Strip(Interface.chime(), gain=-10.0, reverb=0.12),
            "Shimmer": Strip(Interface.shimmer(), gain=-6.0, pan=0.25, reverb=0.3, delay=0.2),
            "Pad": Strip(Interface.pad(), gain=-15.0, reverb=0.35, highpass=150.0),
            "Bass": Strip(Interface.bass(), gain=-15.0, reverb=0.03),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.room(), delay=Interface.echo(), loudness=-16.0, limiter=Limiter(ceiling=-1.0), tail=3.0, loop=Interface.seconds(DefaultAlarm.LOOP))

class WakeUpAlarm(Interface):
    # Waking up in the morning. In small studies by McFarlane et al., people who woke to
    # sounds they rated as melodic reported less grogginess (PLOS ONE, 2020), and a melodic
    # alarm gave better vigilance after waking than a control sound while a merely rhythmic
    # one did not (Clocks & Sleep, 2020). So this is a short tune with a clear melody all the
    # way through: a whistle-like lead over a steady pulse of soft synth plucks in eighth
    # notes; round timbres with soft onsets and little energy around 3 kHz, where the ear
    # canal makes sounds piercing; and most of its energy between 300 Hz and 2 kHz, where
    # phone speakers still work well.
    #
    # Eight bars in two halves with a melody in each; the second plays it out more strongly
    # and adds a shaker and a soft kick, but is only about 1 dB louder, so the loop never
    # drops back to a weaker sound.
    # It stays on Csus4 at the end instead of resolving through E, so the tail of the loop
    # folded onto its start (and the first bar after it) never has E against F. A seamless
    # 16 s loop; players should also raise the volume gradually, as phone alarms do.
    name: ClassVar[str] = "alarm-wakeup"
    title: ClassVar[str] = "Wake Up"

    # (bass, pad voicing, pluck tones low to high) for each bar.
    BARS: ClassVar[Tuple[Tuple[str, Tuple[str, ...], Tuple[str, ...]], ...]] = (
        ("F2", ("F3", "A3", "C4", "G4"), ("A4", "C5", "F5", "G5", "A5")),
        ("A2", ("G3", "A3", "C4", "E4"), ("A4", "C5", "E5", "G5", "A5")),
        ("Bb1", ("F3", "A3", "C4", "D4"), ("A4", "D5", "F5", "A5", "C6")),
        ("C2", ("F3", "G3", "C4", "D4"), ("G4", "C5", "F5", "G5", "C6")),
    )
    # Indices into the pluck tones, one per eighth note.
    PATTERN: ClassVar[Tuple[int, ...]] = (0, 2, 4, 2, 1, 3, 4, 3)
    # Melody, in beats from the start: a lower phrase in bars 1-4, its answer in bars 5-8.
    MELODY: ClassVar[Tuple[Tuple[float, str, float], ...]] = (
        (0.0, "A5", 1.5), (1.5, "G5", 0.5), (2.0, "A5", 1.0), (3.0, "C6", 1.0),
        (4.0, "C6", 2.0), (6.0, "A5", 1.0), (7.0, "G5", 1.0),
        (8.0, "F5", 1.5), (9.5, "G5", 0.5), (10.0, "A5", 1.0), (11.0, "C6", 1.0),
        (12.0, "D6", 2.0), (14.0, "G5", 2.0),
        (16.0, "C6", 1.5), (17.5, "A5", 0.5), (18.0, "C6", 1.0), (19.0, "F6", 1.0),
        (20.0, "E6", 2.0), (22.0, "D6", 1.0), (23.0, "C6", 1.0),
        (24.0, "D6", 1.5), (25.5, "C6", 0.5), (26.0, "D6", 1.0), (27.0, "F6", 1.0),
        (28.0, "G6", 2.0), (30.0, "F6", 1.0), (31.0, "D6", 0.5),
    )
    LOOP: ClassVar[float] = 32.0

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        pluck = score.part("Pluck", channel=0, program=84)
        pad = score.part("Pad", channel=1, program=89)
        bass = score.part("Bass", channel=2, program=33)
        whistle = score.part("Whistle", channel=3, program=78)
        tone = score.part("Tone", channel=4, program=80)
        shaker = score.part("Shaker", channel=9)
        kick = score.part("Kick", channel=10)
        for bar in range(8):
            start = bar * 4.0
            root, voicing, tones = WakeUpAlarm.BARS[bar % 4]
            second = bar >= 4
            for eighth, index in enumerate(WakeUpAlarm.PATTERN):
                accent = 100 if eighth % 4 == 0 else (88 if eighth % 2 == 0 else 78)
                pluck.note(start + eighth * 0.5, tones[index], 0.45, accent + (4 if second else 0))
            # The last bar thins out early, so little of it rings on into the start (the
            # folded tail is also what the first pass of the loop starts with).
            pad.chord(start, voicing, 3.0 if bar == 7 else 4.0, 72 if not second else 78)
            bass.note(start, root, 2.5, 96)
            bass.note(start + 2.5, root, 1.4, 84)
            if second:
                for eighth in range(8):
                    shaker.note(start + eighth * 0.5, 70, 0.25, 56 if eighth % 2 == 0 else 72)
                for beat in (0.0, 2.0):
                    kick.note(start + beat, 36, 0.25, 84)
        for beat, pitch, length in WakeUpAlarm.MELODY:
            second = beat >= 16.0
            whistle.note(beat, pitch, length, (92 if beat % 2 == 0 else 84) - (0 if second else 3))
            tone.note(beat, Part.pitch(pitch) - 12, min(length, 1.0), 70 if second else 56)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Pluck": Strip(Interface.pluck(), gain=-4.0, reverb=0.2),
            "Pad": Strip(Interface.pad(), gain=-14.0, reverb=0.35, highpass=180.0, duck=0.2),
            "Bass": Strip(Interface.bass(), gain=-15.0, reverb=0.03),
            "Whistle": Strip(Interface.whistle(), gain=-9.0, pan=0.1, reverb=0.35, delay=0.15),
            "Tone": Strip(Interface.tone(), gain=-6.0, pan=-0.12, reverb=0.25),
            "Shaker": Strip(Interface.shaker(), gain=-22.0, pan=0.25, reverb=0.1, lowpass=10000.0),
            "Kick": Strip(Interface.kick(), gain=-6.0, reverb=0.02),
        }

    def master(self) -> Master:
        return Master(
            reverb=Interface.room(), delay=Interface.echo(), ducking=Ducking("Kick"),
            loudness=-14.0, limiter=Limiter(ceiling=-1.0), tail=4.0, loop=Interface.seconds(WakeUpAlarm.LOOP),
        )
