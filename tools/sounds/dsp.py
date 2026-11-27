from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, ClassVar, Dict, Tuple

import numpy as np
from numpy.typing import NDArray

from midi import Pitch

# Audio samples, shaped (n,) for mono or (2, n) for stereo; float64 while synthesising,
# float32 once stored in mix buffers.
Buffer = NDArray[np.floating]

class Signal:
    # -60 dB expressed as a natural-log decay constant: exp(-DECAY60) == 0.001.
    DECAY60: ClassVar[float] = math.log(1000.0)
    # Pitch at which decay times and filter cutoffs are specified; other notes scale from here.
    MIDDLE_C: ClassVar[float] = Pitch.frequency(60)

    @staticmethod
    def seconds(count: int, rate: int) -> Buffer:
        return np.arange(count, dtype=np.float64) / rate

    @staticmethod
    def balance(position: float) -> Tuple[float, float]:
        # Constant-power pan law, position in [-1, 1], normalised so the centre is unity per side.
        angle = (min(max(position, -1.0), 1.0) + 1.0) * math.pi / 4.0
        return math.cos(angle) * math.sqrt(2.0), math.sin(angle) * math.sqrt(2.0)

    @staticmethod
    def pan(mono: Buffer, position: float) -> Buffer:
        left, right = Signal.balance(position)
        return np.stack((mono * left, mono * right))

    @staticmethod
    def fit(samples: Buffer, count: int) -> Buffer:
        if samples.shape[-1] >= count:
            return samples[..., :count]
        padding = [(0, 0)] * (samples.ndim - 1) + [(0, count - samples.shape[-1])]
        return np.pad(samples, padding)

    @staticmethod
    def lowpass(frequencies: Buffer, cutoff: float, poles: int = 2) -> Buffer:
        return 1.0 / np.sqrt(1.0 + (frequencies / cutoff) ** (2 * poles))

    @staticmethod
    def highpass(frequencies: Buffer, cutoff: float, poles: int = 2) -> Buffer:
        with np.errstate(divide="ignore"):
            ratio = np.where(frequencies > 0, cutoff / np.maximum(frequencies, 1e-9), np.inf)
        return 1.0 / np.sqrt(1.0 + ratio ** (2 * poles))

    @staticmethod
    def shelf(frequencies: Buffer, corner: float, gain_db: float, high: bool = True) -> Buffer:
        # Smooth first-order shelving magnitude, used for gentle tone shaping.
        ratio = (frequencies / corner) ** 2
        weight = ratio / (1.0 + ratio) if high else 1.0 / (1.0 + ratio)
        return 10.0 ** (gain_db * weight / 20.0)

    @staticmethod
    def filter(samples: Buffer, rate: int, response: Callable[[Buffer], Buffer], padding: int = 4096, taps: int = 1 << 16, circular: bool = False) -> Buffer:
        # Zero-phase filtering with the given magnitude response. Short signals are filtered
        # in one FFT (padding keeps the circular convolution from wrapping the tail onto the
        # head). Long ones would need a song-length FFT, so they are convolved block by block
        # with a windowed, centred FIR sampled from the same response (bounded memory).
        # circular=True treats the samples as one period of a repeating signal (a seamless
        # loop): one FFT of exactly that length, so the filter wraps the end onto the start.
        count = samples.shape[-1]
        if circular:
            spectrum = np.fft.rfft(samples, axis=-1)
            spectrum *= response(np.fft.rfftfreq(count, 1.0 / rate))
            return np.fft.irfft(spectrum, n=count, axis=-1)
        if count <= taps * 16:
            size = 1 << (count + padding - 1).bit_length()
            spectrum = np.fft.rfft(samples, n=size, axis=-1)
            spectrum *= response(np.fft.rfftfreq(size, 1.0 / rate))
            return np.fft.irfft(spectrum, n=size, axis=-1)[..., :count]
        kernel = np.fft.irfft(response(np.fft.rfftfreq(taps, 1.0 / rate)), n=taps)
        kernel = np.roll(kernel, taps // 2) * np.hanning(taps)
        shaped = np.atleast_2d(samples)
        filtered = Signal.convolve(shaped, np.broadcast_to(kernel, (shaped.shape[0], taps)))
        filtered = filtered[:, taps // 2:taps // 2 + count]
        return filtered.reshape(samples.shape)

    @staticmethod
    def convolve(samples: Buffer, impulse: Buffer, block: int = 1 << 16) -> Buffer:
        # Overlap-add convolution of (channels, n) with (channels, m), block by block so the
        # memory use stays bounded for long songs.
        channels, count = samples.shape
        length = impulse.shape[-1]
        size = 1 << (block + length - 1).bit_length()
        block = size - length + 1
        kernel = np.fft.rfft(impulse, n=size, axis=-1)
        output = np.zeros((channels, count + length - 1), dtype=np.float32)
        for start in range(0, count, block):
            chunk = samples[:, start:start + block]
            if not np.any(chunk):
                continue
            result = np.fft.irfft(np.fft.rfft(chunk, n=size, axis=-1) * kernel, n=size, axis=-1)
            end = min(start + size, output.shape[-1])
            output[:, start:end] += result[:, :end - start]
        return output

    @staticmethod
    def fold(samples: Buffer, period: int) -> Buffer:
        # One period of a loop as it sounds once it has repeated for a while: everything that
        # rings past the end (reverb, echoes, held notes) is added back onto the start.
        if period <= 0:
            raise ValueError(f"The period must be positive: {period}")
        folded = np.array(samples[..., :period], copy=True)
        for start in range(period, samples.shape[-1], period):
            segment = samples[..., start:start + period]
            folded[..., :segment.shape[-1]] += segment
        return folded

    @staticmethod
    def saturate(samples: Buffer, drive: float) -> Buffer:
        if drive <= 0:
            return samples
        return np.tanh(samples * drive) / math.tanh(drive)

    @staticmethod
    def noise(count: int, seed: int, channels: int = 1) -> Buffer:
        generator = np.random.default_rng(seed)
        samples = generator.standard_normal((channels, count))
        return samples[0] if channels == 1 else samples

    @staticmethod
    def seed(*values: float) -> int:
        # Deterministic seed from note parameters, so every build is bit-identical.
        return int(sum((index + 1) * 1_000_003 * round(value * 1000) for index, value in enumerate(values)) % (2 ** 32))

@dataclass(frozen=True)
class Envelope:
    attack: float = 0.005
    decay: float = 0.5
    sustain: float = 1.0
    release: float = 0.3
    # Attack shape: 1.0 is a linear ramp, larger values start slower (exponent of a raised cosine).
    curve: float = 1.0

    def render(self, held: float, rate: int) -> Buffer:
        held_count = max(int(round(held * rate)), 1)
        release_count = max(int(round(self.release * rate)), 1)
        time = Signal.seconds(held_count, rate)
        attack = np.ones(held_count)
        if self.attack > 0:
            phase = np.clip(time / self.attack, 0.0, 1.0)
            attack = (0.5 - 0.5 * np.cos(math.pi * phase)) ** self.curve
        after = np.maximum(time - self.attack, 0.0)
        body = self.sustain + (1.0 - self.sustain) * np.exp(-after * Signal.DECAY60 / max(self.decay, 1e-6))
        level = attack * body
        tail = level[-1] * np.exp(-Signal.seconds(release_count, rate) * Signal.DECAY60 / max(self.release, 1e-6))
        return np.concatenate((level, tail))

class Instrument:
    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        raise NotImplementedError()

@dataclass(frozen=True)
class Partial:
    ratio: float
    level: float
    # Seconds to fall by 60 dB at middle C; scaled by pitch tracking for other notes.
    decay: float

@dataclass(frozen=True)
class Additive(Instrument):
    # Sum of independently decaying sine partials: bells, mallets, harps and piano-like tones.
    partials: Tuple[Partial, ...]
    attack: float = 0.002
    release: float = 0.4
    tracking: float = 0.5
    brightness: float = 1.0
    detune: float = 0.0
    width: float = 0.0
    hammer: float = 0.0
    seed: int = 0

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        frequency = Pitch.frequency(pitch)
        scale = (Signal.MIDDLE_C / frequency) ** self.tracking
        longest = max(partial.decay for partial in self.partials) * scale
        count = int(round(min(longest, duration + self.release) * rate)) + 1
        time = Signal.seconds(count, rate)
        held = int(round(duration * rate))
        gate = np.ones(count)
        if held < count:
            gate[held:] = np.exp(-(time[held:] - time[held]) * Signal.DECAY60 / self.release)
        onset = np.clip(time / max(self.attack, 1e-6), 0.0, 1.0) if self.attack > 0 else np.ones(count)
        channels = []
        # One start phase per partial, shared by both sides (the detune already separates them),
        # so the timbre does not change with the stereo width or from note to note.
        generator = np.random.default_rng(Signal.seed(pitch, self.seed))
        phases = [0.0] + [generator.uniform(0, 2 * math.pi) for _ in self.partials[1:]]
        for side in (-1.0, 1.0):
            mono = np.zeros(count)
            cents = side * self.detune
            for index, partial in enumerate(self.partials):
                partial_frequency = frequency * partial.ratio * 2.0 ** (cents / 1200.0)
                if partial_frequency >= rate * 0.45:
                    continue
                # Velocity opens the upper partials, as a harder strike would.
                level = partial.level * velocity ** (1.0 + self.brightness * index * 0.35)
                decay = partial.decay * scale
                phase = phases[index]
                mono += level * np.exp(-time * Signal.DECAY60 / decay) * np.sin(2 * math.pi * partial_frequency * time + phase)
            channels.append(mono)
        stereo = np.stack(channels)
        if self.width < 1.0:
            middle = stereo.mean(axis=0)
            stereo = middle + (stereo - middle) * self.width
        stereo *= onset * gate
        if self.hammer > 0:
            click = Signal.noise(int(0.012 * rate), Signal.seed(pitch, self.seed, 7)) * np.exp(-Signal.seconds(int(0.012 * rate), rate) / 0.002)
            click = Signal.filter(click, rate, lambda f: Signal.lowpass(f, min(frequency * 12, 9000.0), 2) * Signal.highpass(f, frequency * 2, 1))
            length = min(click.shape[-1], count)
            stereo[:, :length] += click[:length] * self.hammer * velocity ** 2
        return stereo

@dataclass(frozen=True)
class FM(Instrument):
    # Two-operator FM with a decaying modulation index (electric pianos, glassy keys),
    # plus an optional high-ratio "tine" pair for the metallic attack.
    ratio: float = 1.0
    index: float = 2.0
    index_decay: float = 1.0
    index_floor: float = 0.2
    amplitude: Envelope = Envelope(0.002, 3.0, 0.0, 0.3)
    tine_ratio: float = 14.0
    tine_index: float = 0.0
    tine_decay: float = 0.05
    tine_level: float = 0.0
    detune: float = 0.0
    tracking: float = 0.4
    # How much the velocity scales the modulation index: 1.0 in full proportion (a softer
    # strike is duller), 0.0 not at all (the timbre stays the same at every velocity).
    velocity_index: float = 1.0

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        frequency = Pitch.frequency(pitch)
        scale = (Signal.MIDDLE_C / frequency) ** self.tracking
        envelope = Envelope(self.amplitude.attack, self.amplitude.decay * scale, self.amplitude.sustain, self.amplitude.release, self.amplitude.curve)
        level = envelope.render(duration, rate)
        count = level.shape[-1]
        time = Signal.seconds(count, rate)
        index = (self.index_floor + (self.index - self.index_floor) * np.exp(-time * Signal.DECAY60 / (self.index_decay * scale))) * (1.0 - self.velocity_index + self.velocity_index * velocity)
        channels = []
        for side in (-1.0, 1.0):
            carrier = frequency * 2.0 ** (side * self.detune / 1200.0)
            signal = np.sin(2 * math.pi * carrier * time + index * np.sin(2 * math.pi * carrier * self.ratio * time))
            # Keep the tine's significant sidebands (about index + 2 of them) below Nyquist.
            if self.tine_level > 0 and carrier * (1.0 + self.tine_ratio * (self.tine_index + 2.0)) < rate * 0.45:
                tine_index = self.tine_index * np.exp(-time * Signal.DECAY60 / self.tine_decay)
                tine = np.sin(2 * math.pi * carrier * time + tine_index * np.sin(2 * math.pi * carrier * self.tine_ratio * time))
                signal += self.tine_level * velocity * tine * np.exp(-time * Signal.DECAY60 / (self.tine_decay * 4))
            channels.append(signal * level)
        return np.stack(channels)

@dataclass(frozen=True)
class Analog(Instrument):
    # Virtual-analogue voice: band-limited saw/square/triangle built from harmonics, through a
    # time-varying low-pass filter, with unison detune, vibrato, a pitch bend at the start of
    # the note and a sub oscillator.
    waveform: str = "saw"
    voices: int = 1
    detune: float = 0.0
    width: float = 0.0
    amplitude: Envelope = Envelope(0.01, 0.5, 0.8, 0.3)
    cutoff: float = 2000.0
    keytrack: float = 0.5
    contour: Envelope = Envelope(0.01, 0.5, 0.0, 0.3)
    amount: float = 0.0
    velocity_amount: float = 1.0
    poles: int = 2
    resonance: float = 0.0
    vibrato_rate: float = 5.0
    vibrato_depth: float = 0.0
    vibrato_delay: float = 0.3
    sub: float = 0.0
    drift: float = 0.0
    seed: int = 0
    # Pitch bend into the note: it starts `bend` semitones away from its pitch (negative:
    # below) and settles exponentially with the time constant `bend_time` (seconds).
    bend: float = 0.0
    bend_time: float = 0.02

    def weights(self, count: int) -> Buffer:
        harmonics = np.arange(1, count + 1, dtype=np.float64)
        if self.waveform == "saw":
            return 1.0 / harmonics
        if self.waveform == "square":
            return np.where(harmonics % 2 == 1, 1.0 / harmonics, 0.0)
        if self.waveform == "triangle":
            signs = np.where((harmonics - 1) // 2 % 2 == 0, 1.0, -1.0)
            return np.where(harmonics % 2 == 1, signs / harmonics ** 2, 0.0)
        if self.waveform == "sine":
            return np.where(harmonics == 1, 1.0, 0.0)
        raise ValueError(f"Unknown waveform: {self.waveform!r}")

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        frequency = Pitch.frequency(pitch)
        level = self.amplitude.render(duration, rate) * velocity
        count = level.shape[-1]
        time = Signal.seconds(count, rate)

        # Filter cutoff at control rate (every 32 samples), interpolated per harmonic below.
        step = 32
        control_time = time[::step]
        contour = self.contour.render(duration, rate)[::step]
        contour = Signal.fit(contour, control_time.shape[-1])
        tracked = self.cutoff * (frequency / Signal.MIDDLE_C) ** self.keytrack
        opening = self.amount * (1.0 - self.velocity_amount + self.velocity_amount * velocity)
        cutoff = np.minimum(tracked * 2.0 ** (opening * contour), rate * 0.45)
        # Harmonics are counted from the highest pitch the note reaches, so a bend from above
        # cannot push any of them past the Nyquist frequency.
        highest = frequency * 2.0 ** (max(self.bend, 0.0) / 12.0)
        harmonic_limit = int(min(rate * 0.45, float(cutoff.max()) * 6.0) // highest)
        harmonic_limit = max(harmonic_limit, 1)
        weights = self.weights(harmonic_limit)

        generator = np.random.default_rng(Signal.seed(pitch, self.seed, 3))
        vibrato_ramp = np.clip((time - self.vibrato_delay) / 0.4, 0.0, 1.0) if self.vibrato_depth > 0 else None
        positions = [0.0 if self.voices == 1 else voice / (self.voices - 1) * 2.0 - 1.0 for voice in range(self.voices)]
        phases = np.empty((self.voices, count))
        for voice, position in enumerate(positions):
            cents = position * self.detune + generator.uniform(-1, 1) * self.drift
            instantaneous = np.full(count, frequency * 2.0 ** (cents / 1200.0))
            if vibrato_ramp is not None:
                vibrato_phase = generator.uniform(0, 2 * math.pi)
                instantaneous *= 2.0 ** (self.vibrato_depth / 1200.0 * vibrato_ramp * np.sin(2 * math.pi * self.vibrato_rate * time + vibrato_phase))
            if self.bend != 0.0:
                instantaneous *= 2.0 ** (self.bend * np.exp(-time / max(self.bend_time, 1e-6)) / 12.0)
            phases[voice] = 2 * math.pi * np.cumsum(instantaneous) / rate + generator.uniform(0, 2 * math.pi)

        # Harmonics in the outer loop: the filter gain of a harmonic is the same for every
        # voice, so it is interpolated once and applied to all voices together.
        cosine2 = 2.0 * np.cos(phases)
        previous = np.zeros((self.voices, count))
        current = np.sin(phases)
        voices = np.zeros((self.voices, count))
        for harmonic in range(1, harmonic_limit + 1):
            weight = weights[harmonic - 1]
            if weight != 0.0:
                ratio = harmonic * frequency / cutoff
                gain = 1.0 / np.sqrt(1.0 + ratio ** (2 * self.poles))
                if self.resonance > 0:
                    gain = gain * (1.0 + self.resonance * np.exp(-(np.log2(ratio) ** 2) / 0.02))
                voices += (weight * np.interp(time, control_time, gain)) * current
            # Chebyshev recurrence: sin((k+1)x) = 2cos(x)sin(kx) - sin((k-1)x).
            previous, current = current, cosine2 * current - previous
        if self.sub > 0:
            voices += self.sub * np.sin(phases / 2.0)
        output = np.zeros((2, count))
        for voice, position in enumerate(positions):
            output += Signal.pan(voices[voice], position * self.width) / math.sqrt(self.voices)
        return output * level

@dataclass(frozen=True)
class Kick(Instrument):
    start: float = 160.0
    end: float = 48.0
    sweep: float = 0.035
    decay: float = 0.45
    click: float = 0.35
    drive: float = 1.5

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        count = int(self.decay * 1.2 * rate)
        time = Signal.seconds(count, rate)
        frequency = self.end + (self.start - self.end) * np.exp(-time / self.sweep)
        body = np.sin(2 * math.pi * np.cumsum(frequency) / rate)
        body *= np.exp(-time * Signal.DECAY60 / self.decay) * np.clip(time / 0.0015, 0, 1)
        click = Signal.noise(count, Signal.seed(pitch, 11)) * np.exp(-time / 0.0025)
        click = Signal.filter(click, rate, lambda f: Signal.highpass(f, 1500.0, 1) * Signal.lowpass(f, 7000.0, 2))
        mono = Signal.saturate(body + self.click * click, self.drive) * velocity
        return Signal.pan(mono, 0.0) / math.sqrt(2.0)

@dataclass(frozen=True)
class Snare(Instrument):
    tone: float = 185.0
    tone_decay: float = 0.12
    noise_decay: float = 0.22
    snap: float = 0.8

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        count = int(max(self.tone_decay, self.noise_decay) * 1.2 * rate)
        time = Signal.seconds(count, rate)
        bend = 1.0 + 0.25 * np.exp(-time / 0.01)
        body = (np.sin(2 * math.pi * np.cumsum(self.tone * bend) / rate) + 0.5 * np.sin(2 * math.pi * np.cumsum(self.tone * 1.78 * bend) / rate))
        body *= np.exp(-time * Signal.DECAY60 / self.tone_decay)
        noise = Signal.noise(count, Signal.seed(pitch, 13), channels=2)
        noise = Signal.filter(noise, rate, lambda f: Signal.highpass(f, 1200.0, 2) * Signal.lowpass(f, 10000.0, 1))
        noise *= np.exp(-time * Signal.DECAY60 / self.noise_decay)
        stereo = Signal.pan(body * 0.6, 0.0) / math.sqrt(2.0) + self.snap * noise * (0.7 + 0.3 * velocity)
        return stereo * velocity * np.clip(time / 0.0008, 0, 1)

class Clap(Instrument):
    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        # Long enough for the last burst's 70 ms tail to fall below -60 dB.
        count = int(0.6 * rate)
        time = Signal.seconds(count, rate)
        envelope = np.zeros(count)
        for burst in (0.0, 0.009, 0.019, 0.031):
            shifted = np.maximum(time - burst, 0.0)
            envelope = np.maximum(envelope, np.where(time >= burst, np.exp(-shifted / (0.008 if burst < 0.03 else 0.07)), 0.0))
        noise = Signal.noise(count, Signal.seed(pitch, 17), channels=2)
        noise = Signal.filter(noise, rate, lambda f: Signal.highpass(f, 900.0, 2) * Signal.lowpass(f, 5500.0, 2))
        return noise * envelope * velocity

@dataclass(frozen=True)
class Metal(Instrument):
    # Hi-hats and cymbals: a cluster of inharmonic square waves (as in classic analogue drum
    # machines) mixed with noise, high-passed, with a decay chosen per instance.
    FREQUENCIES: ClassVar[Tuple[float, ...]] = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)

    decay: float = 0.06
    highpass: float = 7000.0
    noise: float = 0.6
    tone: float = 1.0

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        count = int(self.decay * 1.1 * rate)
        time = Signal.seconds(count, rate)
        metal = np.zeros(count)
        for frequency in Metal.FREQUENCIES:
            # Band-limited square wave: odd harmonics below 0.45 x the sample rate only.
            base = frequency * self.tone
            for harmonic in range(1, int(rate * 0.45 / base) + 1, 2):
                metal += 4.0 / (math.pi * harmonic) * np.sin(harmonic * (2 * math.pi * base * time + frequency))
        stereo = np.stack((metal, np.roll(metal, 7))) * 0.15 + self.noise * Signal.noise(count, Signal.seed(pitch, 19, self.decay), channels=2)
        stereo = Signal.filter(stereo, rate, lambda f: Signal.highpass(f, self.highpass, 3) * Signal.lowpass(f, 16000.0, 1))
        envelope = np.exp(-time * Signal.DECAY60 / self.decay) * np.clip(time / 0.0005, 0, 1)
        return stereo * envelope * velocity

@dataclass(frozen=True)
class Tom(Instrument):
    frequency: float = 110.0
    decay: float = 0.4

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        count = int(self.decay * 1.1 * rate)
        time = Signal.seconds(count, rate)
        frequency = self.frequency * (1.0 + 0.5 * np.exp(-time / 0.02))
        body = np.sin(2 * math.pi * np.cumsum(frequency) / rate) * np.exp(-time * Signal.DECAY60 / self.decay)
        return Signal.pan(body * velocity, 0.0) / math.sqrt(2.0)

@dataclass(frozen=True)
class Sweep(Instrument):
    # Filtered-noise riser/fall for transitions: a band-pass that glides between two
    # frequencies over the note's duration, with the level following the glide.
    low: float = 300.0
    high: float = 9000.0
    rising: bool = True
    width: float = 1.2

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        count = int(duration * rate)
        noise = Signal.noise(count + 2048, Signal.seed(pitch, 23, duration), channels=2)
        frame, hop = 2048, 512
        window = np.hanning(frame)
        output = np.zeros((2, count + frame))
        frequencies = np.fft.rfftfreq(frame, 1.0 / rate)
        for start in range(0, count, hop):
            progress = start / max(count - 1, 1)
            position = progress if self.rising else 1.0 - progress
            centre = self.low * (self.high / self.low) ** position
            response = np.exp(-(np.log2(np.maximum(frequencies, 1.0) / centre) ** 2) / (2 * self.width ** 2))
            block = np.fft.irfft(np.fft.rfft(noise[:, start:start + frame] * window, axis=-1) * response, n=frame, axis=-1)
            output[:, start:start + frame] += block * window
        output = output[:, :count]
        progress = np.linspace(0.0, 1.0, count)
        level = progress ** 2 if self.rising else (1.0 - progress) ** 1.5
        # A riser stops at its loudest point; a 10 ms fade keeps that stop from clicking.
        fade = min(int(0.01 * rate), count)
        level[count - fade:] *= np.linspace(1.0, 0.0, fade)
        return output * level * velocity * 0.5

@dataclass(frozen=True)
class DrumKit(Instrument):
    # Maps General MIDI percussion keys to drum voices.
    pieces: Dict[int, Instrument]

    def render(self, pitch: int, velocity: float, duration: float, rate: int) -> Buffer:
        if pitch not in self.pieces:
            raise KeyError(f"No drum voice on key {pitch}")
        return self.pieces[pitch].render(pitch, velocity, duration, rate)
