from __future__ import annotations

from typing import ClassVar, Dict, Sequence, Tuple

from effects import Limiter
from midi import MIDIFile
from mixer import Master, Strip
from score import Part, Score
from songs.interface import Interface

# The notifications rise in urgency in the order information, default and message, warning,
# caution, alert. Urgency is carried by what research on auditory warnings found people
# reliably hear as more urgent (Edworthy, Loxley & Dennis 1991; Hellier et al. 1993): more
# pulses, faster pulses (rate is the strongest cue), more repetitions, a harder timbre and a
# higher level. The levels are set so that both the integrated loudness and the loudest
# 400 ms (maximum momentary loudness, which decides how loud a short sound seems) rise in
# that order. The warnings use the signal voice in groups of three, two groups of three,
# and a repeating pattern.

class InformationNotification(Interface):
    # Information that needs no action: the quietest sound, and the opposite gesture to the
    # default notification all the way through, not only at the start. Default rises (C to F),
    # settles on a bright F major and echoes; information falls a fifth (A to D), like
    # Windows 11's "one note, then a lower one", and rests, nearly dry, on a soft D minor
    # (D F A) with a quiet shimmer on the D. Both stay within Zerc's F6/9 notes.
    name: ClassVar[str] = "notification-information"
    title: ClassVar[str] = "Information"

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        tone = score.part("Tone", channel=0, program=80)
        tone.note(0.0, "A5", 0.4, 70)
        tone.note(0.25, "D5", 0.6, 66)
        score.part("Shimmer", channel=1, program=81).note(0.25, "D6", 0.4, 56)
        score.part("Bloom", channel=2, program=89).chord(0.0, ("D4", "F4", "A4"), 0.9, 66)
        score.part("Sub", channel=3, program=38).note(0.0, "D3", 0.6, 76)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Tone": Strip(Interface.tone(), gain=-2.0, reverb=0.25),
            "Shimmer": Strip(Interface.shimmer(), gain=-8.0, pan=0.25, reverb=0.4),
            "Bloom": Strip(Interface.bloom(), gain=-8.0, reverb=0.45, highpass=150.0),
            "Sub": Strip(Interface.sub(), gain=-4.0, reverb=0.05),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.room(), loudness=-21.5, limiter=Limiter(ceiling=-1.0), tail=2.6, fade=0.8)

class DefaultNotification(Interface):
    # The everyday notification: two drop-like round notes, a fourth rising to the tonic (C to
    # F), a small "arrived" that echoes, doubled an octave up by a soft pluck (which also carries it on
    # phone speakers, which hardly reproduce the round notes' fundamentals). The bloom and the sub come in with the
    # F, so the arrival opens into a full chord, and a shimmer echoes it.
    name: ClassVar[str] = "notification-default"
    title: ClassVar[str] = "Notification"

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        tone = score.part("Tone", channel=0, program=80)
        tone.note(0.0, "A4", 0.6, 56)
        tone.note(0.0, "C5", 0.6, 88)
        tone.note(0.25, "F5", 0.6, 96)
        pluck = score.part("Pluck", channel=1, program=84)
        pluck.note(0.0, "C6", 0.3, 76)
        pluck.note(0.25, "F6", 0.3, 84)
        score.part("Shimmer", channel=2, program=81).note(0.25, "F6", 0.4, 60)
        score.part("Bloom", channel=3, program=89).chord(0.25, ("F4", "A4", "C5"), 1.0, 72)
        score.part("Sub", channel=4, program=38).note(0.25, "F3", 0.6, 80)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Tone": Strip(Interface.tone(), gain=-3.0, reverb=0.25, delay=0.2),
            "Pluck": Strip(Interface.pluck(), gain=-6.0, pan=-0.15, reverb=0.3),
            "Shimmer": Strip(Interface.shimmer(), gain=-6.0, pan=0.25, reverb=0.4, delay=0.25),
            "Bloom": Strip(Interface.bloom(), gain=-10.0, reverb=0.45, highpass=150.0),
            "Sub": Strip(Interface.sub(), gain=-5.0, reverb=0.05),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.room(), delay=Interface.echo(), loudness=-18.7, limiter=Limiter(ceiling=-1.0), tail=2.6, fade=0.8)

class MessageNotification(Interface):
    # A message from someone: three quick plucks rising through the chord (D F A over F and
    # C), quick like speech, ending on the open third as if waiting for a reply. Round tones
    # double the plucks; a bloom and a sub hold the chord under them.
    name: ClassVar[str] = "notification-message"
    title: ClassVar[str] = "Message"

    NOTES: ClassVar[Tuple[Tuple[float, str, int], ...]] = ((0.0, "D5", 82), (0.1875, "F5", 86), (0.375, "A5", 96))

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        pluck = score.part("Pluck", channel=0, program=84)
        tone = score.part("Tone", channel=1, program=80)
        for beat, pitch, velocity in MessageNotification.NOTES:
            pluck.note(beat, pitch, 0.3, velocity)
            tone.note(beat, pitch, 0.4, velocity - 10)
        score.part("Shimmer", channel=2, program=81).note(0.375, "A6", 0.4, 56)
        score.part("Bloom", channel=3, program=89).chord(0.0, ("F4", "A4", "C5"), 0.9, 64)
        score.part("Sub", channel=4, program=38).note(0.0, "F3", 0.5, 72)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Pluck": Strip(Interface.pluck(), gain=-3.0, reverb=0.22),
            "Tone": Strip(Interface.tone(), gain=-6.0, reverb=0.25, delay=0.12),
            "Shimmer": Strip(Interface.shimmer(), gain=-8.0, pan=0.25, reverb=0.4, delay=0.25),
            "Bloom": Strip(Interface.bloom(), gain=-9.0, reverb=0.45, highpass=150.0),
            "Sub": Strip(Interface.sub(), gain=-3.0, reverb=0.05),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.room(), delay=Interface.echo(), loudness=-18.6, limiter=Limiter(ceiling=-1.0), tail=2.4, fade=0.8)

class Pulsed(Interface):
    # Base of the warnings. They are built like the pleasant sounds (the same round tone,
    # bloom, sub, shimmer, echo and space), so the family stays one, and become more urgent
    # through the warning melodies and a signal voice. A pulse is a set of notes struck
    # together, in four layers: the signal voice and the round tone in the centre, a halo an
    # octave above that alternates between the sides, and a short low body an octave below.
    # All notes come from G, D and A, so overlapping pulses (and other phones playing the
    # same sound a little earlier or later) always form the same consonant chord.
    LENGTH: ClassVar[float] = 0.2

    def __init__(self) -> None:
        # Pulses written so far (pulse() must be called in time order).
        self.count: int = 0

    def pulse(self, parts: Tuple[Part, Part, Part, Part, Part], beat: float, pitches: Sequence[str], velocity: int) -> None:
        signal, tone, left, right, body = parts
        # The halo alternates between the sides from pulse to pulse, which gives width while
        # the core stays in the centre.
        halo = left if self.count % 2 == 0 else right
        # A small, fixed variation from pulse to pulse, as a player's hand would give, so
        # repeated pulses are not identical copies.
        velocity += self.count * 5 % 7 - 3
        self.count += 1
        for pitch in pitches:
            signal.note(beat, pitch, Pulsed.LENGTH, velocity)
            tone.note(beat, pitch, Pulsed.LENGTH, velocity)
            halo.note(beat, Part.pitch(pitch) + 12, Pulsed.LENGTH, velocity - 10)
            body.note(beat, Part.pitch(pitch) - 12, Pulsed.LENGTH, velocity - 10)

    def parts(self, score: Score) -> Tuple[Part, Part, Part, Part, Part]:
        self.count = 0
        return (
            score.part("Signal", channel=0, program=81),
            score.part("Tone", channel=1, program=80),
            score.part("Halo Left", channel=2, program=88),
            score.part("Halo Right", channel=3, program=88),
            score.part("Body", channel=4, program=38),
        )

class WarningNotification(Pulsed):
    # Something needs attention (注意). It is close to information in urgency, so it is
    # information's sound (round tones, bloom, sub, shimmer, echo) with a warning melody:
    # three notes high-low-high (A5 D5 A5) at 180 ms, over a suspended D G A bloom instead of
    # a settled chord, ending high and open, asking for a look. The signal voice is a light
    # edge here (about 15 % of the energy): enough to set it apart from information, not
    # enough to make it a signal. The harmonic rule of the signal voice (see interface.py)
    # is applied to caution and alert, not to this low-urgency sound.
    name: ClassVar[str] = "notification-warning"
    title: ClassVar[str] = "Warning"

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        parts = self.parts(score)
        for beat, pitch, velocity in ((0.0, "A5", 92), (0.36, "D5", 86), (0.72, "A5", 96)):
            self.pulse(parts, beat, (pitch,), velocity)
        score.part("Bloom", channel=5, program=89).chord(0.0, ("D4", "G4", "A4"), 1.1, 70)
        score.part("Sub", channel=6, program=38).note(0.0, "D3", 0.7, 76)
        score.part("Shimmer", channel=7, program=81).note(0.72, "A6", 0.4, 60)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Signal": Strip(Interface.signal(), gain=-9.0, reverb=0.15, delay=0.05),
            "Tone": Strip(Interface.tone(release=0.2), gain=-2.0, reverb=0.25, delay=0.1),
            "Halo Left": Strip(Interface.halo(), gain=-6.0, pan=-0.3, reverb=0.3),
            "Halo Right": Strip(Interface.halo(), gain=-6.0, pan=0.3, reverb=0.3),
            "Body": Strip(Interface.body(), gain=-10.0, reverb=0.05),
            "Bloom": Strip(Interface.bloom(), gain=-10.0, reverb=0.45, highpass=150.0),
            "Sub": Strip(Interface.sub(), gain=-7.0, reverb=0.05),
            "Shimmer": Strip(Interface.shimmer(), gain=-5.0, pan=0.25, reverb=0.4, delay=0.2),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.room(), delay=Interface.echo(), loudness=-16.0, limiter=Limiter(ceiling=-1.0), tail=2.6, fade=0.8)

class CautionNotification(Pulsed):
    # An important notification (重要): the warning played as fourths (A5/D6 and D5/A5),
    # faster (150 ms) and twice, with more of the signal voice and a body under each pulse,
    # over a deeper suspended bloom (G D A). The same family as the warning, but firmer.
    name: ClassVar[str] = "notification-caution"
    title: ClassVar[str] = "Caution"

    HIGH: ClassVar[Tuple[str, ...]] = ("A5", "D6")
    LOW: ClassVar[Tuple[str, ...]] = ("D5", "A5")

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        parts = self.parts(score)
        bloom = score.part("Bloom", channel=5, program=89)
        sub = score.part("Sub", channel=6, program=38)
        shimmer = score.part("Shimmer", channel=7, program=81)
        for group in (0.0, 1.6):
            for offset, pitches, velocity in ((0.0, CautionNotification.HIGH, 100), (0.3, CautionNotification.LOW, 94), (0.6, CautionNotification.HIGH, 104)):
                self.pulse(parts, group + offset, pitches, velocity)
            bloom.chord(group, ("G3", "D4", "A4"), 1.2, 74)
            sub.note(group, "G2", 0.7, 80)
            shimmer.note(group + 0.6, "D7", 0.3, 56)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {
            "Signal": Strip(Interface.signal(), gain=-5.0, reverb=0.1, delay=0.03),
            "Tone": Strip(Interface.tone(release=0.12), gain=-12.0, reverb=0.15, delay=0.05),
            "Halo Left": Strip(Interface.halo(), gain=-2.0, pan=-0.3, reverb=0.25),
            "Halo Right": Strip(Interface.halo(), gain=-2.0, pan=0.3, reverb=0.25),
            "Body": Strip(Interface.body(), gain=-5.0, reverb=0.05, drive=0.8),
            "Bloom": Strip(Interface.bloom(), gain=-5.0, reverb=0.4, highpass=150.0),
            "Sub": Strip(Interface.sub(), gain=-5.0, reverb=0.05),
            "Shimmer": Strip(Interface.shimmer(), gain=-2.0, pan=0.25, reverb=0.35, delay=0.15),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.room(), delay=Interface.echo(), loudness=-15.0, limiter=Limiter(ceiling=-1.0), tail=2.4, fade=0.8)

class AlertNotification(Pulsed):
    # An emergency such as an earthquake (非常事態). It has to be noticed at once, be
    # understood as an emergency, and leave people able to act calmly; it may also sound from
    # many phones in one place at slightly different times. So:
    #
    # - It is the fastest, widest and loudest of the family, and has its own shape: groups of
    #   four pulses at 125 ms leaping low-high-low-high between G4/D5 and A5/D6 (more than an
    #   octave, where the caution moves within one), two groups every 2 s. A faster rate, a
    #   wider pitch range, a rising end and more repetitions all raise perceived urgency.
    # - It is not harsh: consonant fifths and fourths instead of a dissonant interval, rounded
    #   onsets, and fundamentals of 390-1170 Hz whose harmonics fill the 1-4 kHz band, instead
    #   of a piercing high tone.
    # - The pause of about 0.8 s in every 2 s leaves room to hear an announcement or the
    #   people nearby, and keeps the rhythm recognisable when several phones are out of step.
    # - Every note is G, D or A, so out-of-step copies blend into one chord instead of clashing.
    # - It is deliberately unlike the official signals (the Japanese Earthquake Early Warning
    #   chime, the J-Alert sirens, and the 853 + 960 Hz EAS/WEA attention signal, whose
    #   simulation FCC rules forbid outside real emergencies and tests), so it can never be
    #   mistaken for a real public warning or make a real one harder to recognise.
    #
    # The file is a seamless 8 s loop; play it repeated until dismissed.
    name: ClassVar[str] = "notification-alert"
    title: ClassVar[str] = "Alert"

    LOW: ClassVar[Tuple[str, ...]] = ("G4", "D5")
    HIGH: ClassVar[Tuple[str, ...]] = ("A5", "D6")
    CYCLES: ClassVar[int] = 4
    CYCLE: ClassVar[float] = 4.0

    def compose(self) -> MIDIFile:
        midi, score = self.score()
        parts = self.parts(score)
        bloom = score.part("Bloom", channel=5, program=89)
        sub = score.part("Sub", channel=6, program=38)
        for cycle in range(AlertNotification.CYCLES):
            for group in (0.0, 1.5):
                start = cycle * AlertNotification.CYCLE + group
                for index in range(4):
                    pitches = AlertNotification.LOW if index % 2 == 0 else AlertNotification.HIGH
                    self.pulse(parts, start + index * 0.25, pitches, 96 + index * 4)
                # A short suspended bed under each group (gone before the pause), for depth.
                bloom.chord(start, ("G3", "D4", "A4"), 0.8, 76)
                sub.note(start, "G2", 0.8, 84)
        return midi

    def strips(self) -> Dict[str, Strip]:
        # The signal voice leads, for clarity and reach; the room is the drier booth and there
        # is no echo, so each pulse stays separate and the pause stays clear.
        return {
            "Signal": Strip(Interface.signal(), gain=-4.5, reverb=0.08),
            "Tone": Strip(Interface.tone(release=0.12), gain=-14.0, reverb=0.1),
            "Halo Left": Strip(Interface.halo(), gain=-3.0, pan=-0.35, reverb=0.06),
            "Halo Right": Strip(Interface.halo(), gain=-3.0, pan=0.35, reverb=0.06),
            "Body": Strip(Interface.body(), gain=-6.0, reverb=0.03, drive=0.8),
            "Bloom": Strip(Interface.bloom(release=0.25), gain=-5.0, reverb=0.12, highpass=150.0),
            "Sub": Strip(Interface.sub(release=0.2), gain=-5.0, reverb=0.03),
        }

    def master(self) -> Master:
        return Master(reverb=Interface.booth(), loudness=-12.0, limiter=Limiter(ceiling=-1.0), tail=2.0, loop=Interface.seconds(AlertNotification.CYCLES * AlertNotification.CYCLE))
