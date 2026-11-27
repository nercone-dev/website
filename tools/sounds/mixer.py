from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Optional, Tuple

import numpy as np

from dsp import Buffer, Instrument, Signal
from effects import Delay, Limiter, Loudness, Reverb
from midi import MIDIFile, Track

@dataclass
class Strip:
    # One mixer channel strip: the instrument that plays a track, its level, pan, sends and tone.
    instrument: Instrument
    gain: float = 0.0
    pan: float = 0.0
    reverb: float = 0.0
    delay: float = 0.0
    duck: float = 0.0
    highpass: Optional[float] = None
    lowpass: Optional[float] = None
    drive: float = 0.0

@dataclass
class Ducking:
    # Side-chain style ducking driven by note onsets of one track (typically the kick).
    track: str
    pitches: Tuple[int, ...] = (36,)
    attack: float = 0.006
    release: float = 0.22

@dataclass
class Master:
    reverb: Reverb = field(default_factory=Reverb)
    delay: Optional[Delay] = None
    ducking: Optional[Ducking] = None
    loudness: float = -14.0
    limiter: Limiter = field(default_factory=Limiter)
    tail: float = 3.0
    fade: float = 1.5
    highpass: float = 25.0

class Mixer:
    # MIDI control numbers from the General MIDI specification.
    VOLUME: ClassVar[int] = 7
    EXPRESSION: ClassVar[int] = 11
    # Controller changes glide over this time, as on most synthesizers, instead of stepping.
    SLEW: ClassVar[float] = 0.01

    def __init__(self, rate: int = 48000) -> None:
        self.rate: int = rate
        self.cache: Dict[Tuple[str, int, int, int], Buffer] = {}
        self.report: Dict[str, float] = {}

    def voice(self, name: str, strip: Strip, pitch: int, velocity: int, length: int) -> Buffer:
        # Rendered notes are reused within one render() call, keyed by track name.
        key = (name, pitch, velocity, length)
        if key not in self.cache:
            rendered = strip.instrument.render(pitch, velocity / 127.0, length / self.rate, self.rate)
            if strip.highpass is not None or strip.lowpass is not None:
                rendered = Signal.filter(rendered, self.rate, lambda f: (Signal.highpass(f, strip.highpass, 2) if strip.highpass else 1.0) * (Signal.lowpass(f, strip.lowpass, 2) if strip.lowpass else 1.0))
            self.cache[key] = Signal.saturate(rendered, strip.drive).astype(np.float32)
        return self.cache[key]

    def expression(self, midi: MIDIFile, track: Track, count: int) -> Optional[Buffer]:
        # CC7 and CC11 hold their value until the next event (127 before the first one), with
        # a short glide; GM maps both to 40*log10(v/127) dB, i.e. an amplitude of (v/127)^2.
        result: Optional[Buffer] = None
        slew = max(int(Mixer.SLEW * self.rate), 1)
        for number in (Mixer.VOLUME, Mixer.EXPRESSION):
            events = sorted((control for control in track.controls if control.number == number), key=lambda control: control.time)
            if not events:
                continue
            starts = np.array([int(round(midi.seconds(control.time) * self.rate)) for control in events])
            values = np.array([1.0] + [(control.value / 127.0) ** 2 for control in events], dtype=np.float32)
            stepped = values[np.searchsorted(starts, np.arange(count), side="right")]
            sums = np.cumsum(np.concatenate((np.full(slew, stepped[0]), stepped)), dtype=np.float64)
            curve = ((sums[slew:] - sums[:-slew]) / slew).astype(np.float32)
            result = curve if result is None else result * curve
        return result

    def ducking(self, midi: MIDIFile, ducking: Ducking, count: int) -> Buffer:
        track = midi.track(ducking.track)
        onsets = np.array(sorted({midi.seconds(note.start) for note in track.notes if note.pitch in ducking.pitches}))
        time = Signal.seconds(count, self.rate)
        if onsets.size == 0:
            return np.ones(count, dtype=np.float32)
        index = np.searchsorted(onsets, time, side="right") - 1
        since = np.where(index >= 0, time - onsets[np.maximum(index, 0)], np.inf)
        # Fast dip to zero, then a smooth (raised-cosine) recovery over the release time.
        upcoming = np.searchsorted(onsets, time, side="left")
        until = np.where(upcoming < onsets.size, onsets[np.minimum(upcoming, onsets.size - 1)] - time, np.inf)
        recovery = np.where(since < ducking.release, 0.5 - 0.5 * np.cos(math.pi * np.clip(since / ducking.release, 0, 1)), 1.0)
        approach = np.clip(until / ducking.attack, 0.0, 1.0)
        return np.minimum(recovery, approach).astype(np.float32)

    def render(self, midi: MIDIFile, strips: Dict[str, Strip], master: Master) -> Buffer:
        self.cache.clear()
        count = int((midi.seconds(midi.length()) + master.tail) * self.rate)
        bus = np.zeros((2, count), dtype=np.float32)
        reverb = np.zeros((2, count), dtype=np.float32)
        delay = np.zeros((2, count), dtype=np.float32)
        duck = self.ducking(midi, master.ducking, count) if master.ducking else None
        for track in midi.tracks:
            if track.name not in strips:
                raise KeyError(f"No mixer strip for track {track.name!r}")
            strip = strips[track.name]
            buffer = np.zeros((2, count), dtype=np.float32)
            for note in track.notes:
                start = int(round(midi.seconds(note.start) * self.rate))
                length = int(round(midi.seconds(note.end) * self.rate)) - start
                rendered = self.voice(track.name, strip, note.pitch, note.velocity, length)
                end = min(start + rendered.shape[-1], count)
                buffer[:, start:end] += rendered[:, :end - start]
            curve = self.expression(midi, track, count)
            if curve is not None:
                buffer *= curve
            if duck is not None and strip.duck > 0:
                buffer *= 1.0 - strip.duck * (1.0 - duck)
            gain = 10.0 ** (strip.gain / 20.0)
            left, right = Signal.balance(strip.pan)
            buffer[0] *= gain * left
            buffer[1] *= gain * right
            bus += buffer
            if strip.reverb > 0:
                reverb += buffer * strip.reverb
            if strip.delay > 0:
                delay += buffer * strip.delay
        if master.delay is not None and np.any(delay):
            echoes = master.delay.process(delay, self.rate)
            bus += echoes[:, :count]
            reverb += echoes[:, :count] * 0.5
        if np.any(reverb):
            bus += master.reverb.process(reverb, self.rate)[:, :count]
        return self.finish(bus, master)

    def finish(self, bus: Buffer, master: Master) -> Buffer:
        audio = Signal.filter(bus.astype(np.float64), self.rate, lambda f: Signal.highpass(f, master.highpass, 2))
        fade = int(master.fade * self.rate)
        if fade > 0:
            audio[:, -fade:] *= np.cos(np.linspace(0, math.pi / 2, fade)) ** 2
        # K-weighting is linear, so scaling the audio by g scales every block power by g^2:
        # measure once and solve on the block powers. Two passes, because scaling moves quiet
        # blocks across the absolute -70 LKFS gate and shifts the measurement slightly.
        powers = Loudness.blocks(audio, self.rate)
        loudness = Loudness.gate(powers)
        if not math.isfinite(loudness):
            raise ValueError("The mix is silent; there is nothing to normalise")
        gain = 1.0
        for _ in range(2):
            gain *= 10.0 ** ((master.loudness - Loudness.gate(powers * gain ** 2)) / 20.0)
        audio *= gain
        audio, reduction = master.limiter.process(audio, self.rate)
        peak = float(np.abs(audio).max())
        self.report = {
            "loudness_before": loudness,
            "limiter_reduction_db": reduction,
            "loudness_after": Loudness.integrated(audio, self.rate),
            "peak_db": 20.0 * math.log10(peak) if peak > 0 else -math.inf,
        }
        return audio
