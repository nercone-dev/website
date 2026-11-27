from __future__ import annotations

from typing import ClassVar, Tuple

from dsp import FM, Analog, Clap, Envelope, Kick, Metal
from effects import Delay, Reverb
from midi import KeySignature, MIDIFile, Tempo
from score import Score, Song

class Interface(Song):
    # Base of the NecOS user-interface sounds (public/static/assets/sounds/user-interface).
    #
    # They are one family with Zerc, the startup sound: the same tempo (120 BPM, so a beat is
    # 0.5 s), the same key (F major), Zerc's motif in the ringtone and Zerc's kind of pad.
    # Pleasant sounds use the notes of Zerc's F6/9 chord (F G A C D). Warnings use only G, D
    # and A: still from that chord, but stacked in fourths, a suspended sound that is neither
    # happy nor sad.
    #
    # The timbres follow current system sounds rather than acoustic instruments. Windows 11's
    # sounds are "digitally sculpted" and deliberately evoke no instrument, with a rounder
    # waveform than Windows 10's sharp one, lower in pitch and without a long sustained last
    # note; iOS 17's default alert (Rebound) is two soft drop-like notes with an echo, and
    # iOS 26 added electronic remixes of its ringtone and a tone with an electronic bassline
    # under a whistled melody. So the voices here are synthetic: a round tone that slides
    # into its pitch like a drop, a filtered synth pluck, a whistle-like lead, a sine
    # shimmer, and the pad, bloom and sub under them. A first version used electric piano,
    # bells and marimba, and sounded dated (like Windows 7).
    #
    # Every sound is built in layers, never as one bare tone: a core that carries the notes,
    # something brighter on top, a bloom or pad under it and a sub. Each layer is audible
    # (none takes much more than half of the energy). The cores sit in the centre with no
    # detune; the width comes from ensembles, panning, echoes and the room.
    directory: ClassVar[str] = "user-interface"
    TEMPO: ClassVar[float] = 120.0

    @staticmethod
    def seconds(beats: float) -> float:
        return beats * 60.0 / Interface.TEMPO

    def score(self) -> Tuple[MIDIFile, Score]:
        midi = MIDIFile(title=self.title, tempos=[Tempo(0, Interface.TEMPO)], key_signature=KeySignature(-1, False))
        return midi, Score(midi)

    @staticmethod
    def tone(release: float = 0.4) -> Analog:
        # The round core: a triangle (nearly a sine, with soft odd harmonics) that slides up a
        # semitone into its pitch within the first few hundredths of a second, like a drop,
        # with a brief brighter edge from the filter, then a clean decay of about a second.
        # Warnings use a short release, so their pulses stay separate.
        return Analog(
            "triangle", voices=1,
            amplitude=Envelope(0.003, 1.2, 0.0, release),
            cutoff=1800.0, keytrack=0.7, contour=Envelope(0.001, 0.12, 0.0, 0.1), amount=1.6, velocity_amount=0.5,
            poles=2, bend=-1.0, bend_time=0.012, seed=71,
        )

    @staticmethod
    def pluck() -> Analog:
        # A synth pluck: three slightly detuned saws through a filter that snaps shut, so each
        # note starts bright and falls into a soft tone (the plucks of current electronic pop).
        return Analog(
            "saw", voices=3, detune=7.0, width=0.6,
            amplitude=Envelope(0.002, 0.7, 0.0, 0.15),
            cutoff=420.0, keytrack=0.8, contour=Envelope(0.001, 0.2, 0.0, 0.1), amount=2.0, velocity_amount=0.5,
            poles=2, drift=1.0, seed=72,
        )

    @staticmethod
    def whistle() -> Analog:
        # A whistle-like lead: a nearly pure tone that scoops up into each note and gains a
        # gentle vibrato as it is held.
        return Analog(
            "triangle", voices=1,
            amplitude=Envelope(0.03, 3.0, 0.7, 0.15, curve=1.3),
            cutoff=700.0, keytrack=1.0, poles=2,
            vibrato_rate=5.2, vibrato_depth=8.0, vibrato_delay=0.3,
            bend=-0.6, bend_time=0.04, seed=73,
        )

    @staticmethod
    def shimmer() -> Analog:
        # A pure sine with a quick, soft decay, an octave above the core: light on top
        # without the metallic partials of a bell.
        return Analog("sine", voices=1, amplitude=Envelope(0.003, 0.9, 0.0, 0.3), cutoff=20000.0, keytrack=0.0, seed=74)

    @staticmethod
    def halo() -> Analog:
        # The upper layer of warnings: a short round tone an octave above the signal.
        return Analog(
            "triangle", voices=1,
            amplitude=Envelope(0.006, 0.6, 0.0, 0.08),
            cutoff=2600.0, keytrack=0.4, poles=2, seed=75,
        )

    @staticmethod
    def signal() -> Analog:
        # The signal voice of warnings: a saw through a four-pole filter that follows the
        # pitch (at about four times the fundamental) with a resonance there, so harmonics 2-4
        # stand up next to the fundamental (IEC 60601-1-8 asks for the first four within 15 dB,
        # which makes a warning audible on small speakers, in noise and with hearing loss, and
        # easy to locate) while everything above them is rolled off and nothing is piercing.
        # A short, brighter edge and a small slide into the pitch, as in tone(). One voice:
        # with detuned unison voices the harmonics beat against each other and their balance
        # would change from moment to moment; the width comes from the halo instead.
        return Analog(
            "saw", voices=1,
            amplitude=Envelope(0.008, 0.8, 0.35, 0.1),
            cutoff=1050.0, keytrack=1.0, contour=Envelope(0.001, 0.08, 0.0, 0.05), amount=0.6, velocity_amount=0.3,
            poles=4, resonance=1.0, bend=-0.5, bend_time=0.01, seed=76,
        )

    @staticmethod
    def bloom(release: float = 0.9) -> Analog:
        # A soft chord that swells in under the strike and dies away within about a second:
        # five detuned saw voices with drift, a gently opening filter. It gives a short sound
        # body, width and movement (the partials change as the filter opens). The alert uses
        # a short release, so the bloom is gone before its pause.
        return Analog(
            "saw", voices=5, detune=12.0, width=0.9,
            amplitude=Envelope(0.05, 1.4, 0.0, release, curve=1.5),
            cutoff=1000.0, keytrack=0.2, contour=Envelope(0.08, 0.8, 0.2, 0.6), amount=0.8,
            velocity_amount=0.3, poles=2, drift=3.0, seed=61,
        )

    @staticmethod
    def sub(release: float = 0.6) -> Analog:
        # A round low note in the centre, an octave or two under the chord.
        return Analog("triangle", voices=1, amplitude=Envelope(0.02, 1.0, 0.0, release), cutoff=600.0, keytrack=0.0, seed=62)

    @staticmethod
    def body() -> Analog:
        # The low layer of warnings: a short triangle an octave under each pulse, ending well
        # before the next one, so the pulses get weight without blurring.
        return Analog("triangle", voices=1, amplitude=Envelope(0.006, 0.25, 0.0, 0.04), cutoff=900.0, keytrack=0.0, seed=64)

    @staticmethod
    def chime() -> FM:
        # A two-operator FM tone (modulator at the carrier frequency, index 3.2-3.8, the same
        # at every velocity): harmonics 1-4 within 10 dB, the fundamental strongest. It gives
        # the alarm its insistent edge an octave under the pluck. Harmonic k has the amplitude
        # J(k-1) + (-1)^k J(k+1) of the index; the fundamental, J0 - J2, vanishes near an
        # index of 1.84, so the index stays well above that.
        return FM(
            ratio=1.0, index=3.8, index_decay=0.5, index_floor=3.2,
            amplitude=Envelope(0.012, 1.0, 0.4, 0.12),
            detune=0.0, tracking=0.3, velocity_index=0.0,
        )

    @staticmethod
    def pad() -> Analog:
        # Like Zerc's pad, but with a shorter swell so chords can change every bar.
        return Analog(
            "saw", voices=5, detune=14.0, width=0.9,
            amplitude=Envelope(0.25, 2.0, 0.75, 0.9, curve=1.5),
            cutoff=900.0, keytrack=0.3,
            contour=Envelope(0.6, 2.5, 0.5, 0.9), amount=1.0, velocity_amount=0.4,
            poles=2, drift=2.0, seed=43,
        )

    @staticmethod
    def bass() -> Analog:
        return Analog(
            "triangle", voices=1,
            amplitude=Envelope(0.01, 2.0, 0.6, 0.2),
            cutoff=420.0, keytrack=0.0, poles=2, sub=0.3, seed=44,
        )

    @staticmethod
    def shaker() -> Metal:
        return Metal(decay=0.045, highpass=6500.0, noise=0.9, tone=1.1)

    @staticmethod
    def kick() -> Kick:
        # A soft, round kick. Its sweep starts at 180 Hz and it has some click, so it still
        # registers on phone speakers, which drop its low end.
        return Kick(start=180.0, end=50.0, sweep=0.03, decay=0.32, click=0.3, drive=1.4)

    @staticmethod
    def clap() -> Clap:
        return Clap()

    @staticmethod
    def room() -> Reverb:
        # One shared space for the family: not an audible room (few early reflections) but a
        # soft, dark tail behind the echo, as in current system sounds. The 30 ms pre-delay
        # keeps the onsets crisp; the low cut at 150 Hz leaves some warmth.
        return Reverb(decay=1.6, damping=0.25, predelay=0.03, buildup=0.03, early=0.08, lowcut=150.0, seed=11)

    @staticmethod
    def booth() -> Reverb:
        # A drier, shorter room for warnings: each pulse must stay separate from the next.
        return Reverb(decay=1.1, damping=0.35, predelay=0.025, buildup=0.02, early=0.35, lowcut=180.0, seed=12)

    @staticmethod
    def echo() -> Delay:
        # Zerc's dotted-eighth echo (0.375 s at 120 BPM), shorter.
        return Delay(time=0.375, feedback=0.3, repeats=4, lowcut=500.0, highcut=6000.0)
