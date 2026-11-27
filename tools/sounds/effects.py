from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from dsp import Buffer, Signal

@dataclass(frozen=True)
class Reverb:
    # Convolution reverb with a synthesised impulse response: exponentially decaying noise
    # whose decay time falls with frequency (air and wall absorption), a diffuse build-up and
    # a handful of early reflections. Built in the short-time Fourier domain so every band
    # gets its own decay without recursive filters.
    decay: float = 2.4
    damping: float = 0.45
    predelay: float = 0.02
    buildup: float = 0.03
    early: float = 0.35
    lowcut: float = 180.0
    highcut: float = 11000.0
    seed: int = 1

    def decay_at(self, frequencies: Buffer) -> Buffer:
        # Full decay up to 600 Hz, falling to decay * damping at 10 kHz (log-frequency interpolation).
        position = np.clip(np.log2(np.maximum(frequencies, 1.0) / 600.0) / math.log2(10000.0 / 600.0), 0.0, 1.0)
        return self.decay * (1.0 + (self.damping - 1.0) * position)

    def impulse(self, rate: int) -> Buffer:
        frame, hop = 1024, 256
        length = int((self.decay * 1.1 + self.predelay) * rate)
        frames = length // hop + 4
        frequencies = np.fft.rfftfreq(frame, 1.0 / rate)
        times = np.arange(frames) * hop / rate
        decays = self.decay_at(frequencies)
        magnitude = np.exp(-np.outer(times, Signal.DECAY60 / decays))
        magnitude *= Signal.highpass(frequencies, self.lowcut, 1) * Signal.lowpass(frequencies, self.highcut, 1)
        generator = np.random.default_rng(self.seed)
        window = np.hanning(frame)
        impulse = np.zeros((2, frames * hop + frame))
        for channel in range(2):
            phases = np.exp(2j * math.pi * generator.random((frames, frequencies.shape[-1])))
            blocks = np.fft.irfft(magnitude * phases, n=frame, axis=-1) * window
            for index in range(frames):
                impulse[channel, index * hop:index * hop + frame] += blocks[index]
        time = Signal.seconds(impulse.shape[-1], rate)
        impulse *= 1.0 - np.exp(-time / max(self.buildup, 1e-4))
        for delay, gain, side in ((0.007, 0.9, 0), (0.011, 0.8, 1), (0.017, 0.65, 0), (0.023, 0.6, 1), (0.031, 0.5, 0), (0.037, 0.45, 1)):
            index = int(delay * rate)
            impulse[side, index] += gain * self.early * float(np.abs(impulse).max())
        impulse /= np.sqrt(np.mean(np.sum(impulse ** 2, axis=-1)))
        return np.pad(impulse[:, :length], ((0, 0), (int(self.predelay * rate), 0)))

    def process(self, samples: Buffer, rate: int) -> Buffer:
        return Signal.convolve(samples, self.impulse(rate))

@dataclass(frozen=True)
class Delay:
    # Ping-pong echo: each repeat alternates sides and is quieter by the feedback ratio.
    # The input is band-limited once so the echoes stay behind the dry sound.
    time: float = 0.375
    feedback: float = 0.4
    repeats: int = 8
    lowcut: float = 300.0
    highcut: float = 5000.0
    pingpong: bool = True

    def process(self, samples: Buffer, rate: int) -> Buffer:
        filtered = Signal.filter(samples, rate, lambda f: Signal.highpass(f, self.lowcut, 1) * Signal.lowpass(f, self.highcut, 1))
        mono = filtered.mean(axis=0)
        step = int(round(self.time * rate))
        output = np.zeros((2, samples.shape[-1] + step * self.repeats), dtype=np.float32)
        for repeat in range(1, self.repeats + 1):
            gain = self.feedback ** (repeat - 1)
            offset = step * repeat
            if self.pingpong:
                output[(repeat + 1) % 2, offset:offset + mono.shape[-1]] += mono * gain * math.sqrt(2.0)
            else:
                output[:, offset:offset + filtered.shape[-1]] += filtered * gain
        return output

@dataclass(frozen=True)
class Limiter:
    # Look-ahead peak limiter: per-block peak gain reduction, spread backwards over the
    # look-ahead so the gain is already down when the peak arrives, then released smoothly.
    ceiling: float = -1.0
    lookahead: float = 0.005
    release: float = 0.12
    block: int = 32

    def process(self, samples: Buffer, rate: int, circular: bool = False) -> Tuple[Buffer, float]:
        # circular=True limits one period of a loop: the middle of three copies, so the gain
        # at the start already knows the peaks at the end (and the other way round).
        if circular:
            count = samples.shape[-1]
            limited, reduction = self.process(np.concatenate((samples, samples, samples), axis=-1), rate)
            return limited[..., count:2 * count], reduction
        ceiling = 10.0 ** (self.ceiling / 20.0)
        count = samples.shape[-1]
        blocks = -(-count // self.block)
        padded = Signal.fit(np.abs(samples).max(axis=0), blocks * self.block).reshape(blocks, self.block).max(axis=1)
        target = np.minimum(1.0, ceiling / np.maximum(padded, 1e-12))
        ahead = max(int(self.lookahead * rate / self.block), 1)
        # Each block takes the lowest gain needed within the next `ahead` blocks (a sliding
        # minimum over the original targets, not over already-shifted ones).
        peaks = target.copy()
        for shift in range(1, ahead + 1):
            target[:-shift] = np.minimum(target[:-shift], peaks[shift:])
        # Instant attack, one-pole release; one Python step per block (about 1500 per second).
        coefficient = math.exp(-self.block / (self.release * rate))
        gain = np.empty_like(target)
        current = 1.0
        for index, value in enumerate(target):
            current = value if value < current else value + (current - value) * coefficient
            gain[index] = current
        smooth = np.interp(np.arange(count), np.arange(blocks) * self.block + self.block / 2, gain)
        limited = samples * smooth
        limited = np.clip(limited, -ceiling, ceiling)
        return limited, float(20.0 * math.log10(max(float(gain.min()), 1e-12)))

@dataclass(frozen=True)
class Biquad:
    # Second-order IIR section, b over a with a[0] = 1, as in the usual direct form.
    b: Tuple[float, float, float]
    a: Tuple[float, float, float]

    def response(self, frequencies: Buffer, rate: int) -> Buffer:
        delay = np.exp(-2j * math.pi * frequencies / rate)
        numerator = self.b[0] + delay * (self.b[1] + delay * self.b[2])
        denominator = self.a[0] + delay * (self.a[1] + delay * self.a[2])
        return np.abs(numerator / denominator)

class Loudness:
    # Integrated loudness after ITU-R BS.1770-4: K-weighting, 400 ms blocks with 75 % overlap,
    # absolute gate at -70 LKFS and relative gate at -10 LU. Left and right weigh 1.0 each.
    @staticmethod
    def filters(rate: int) -> Tuple[Biquad, Biquad]:
        # The pre-filter shelf and the RLB high-pass, designed for any rate from the analogue
        # parameters behind the 48 kHz coefficients printed in BS.1770 (as libebur128 does).
        gain, quality, centre = 3.999843853973347, 0.7071752369554196, 1681.974450955533
        k = math.tan(math.pi * centre / rate)
        vh = 10.0 ** (gain / 20.0)
        vb = vh ** 0.4996667741545416
        a0 = 1.0 + k / quality + k * k
        shelf = Biquad(
            ((vh + vb * k / quality + k * k) / a0, 2.0 * (k * k - vh) / a0, (vh - vb * k / quality + k * k) / a0),
            (1.0, 2.0 * (k * k - 1.0) / a0, (1.0 - k / quality + k * k) / a0),
        )
        quality, centre = 0.5003270373238773, 38.13547087602444
        k = math.tan(math.pi * centre / rate)
        a0 = 1.0 + k / quality + k * k
        highpass = Biquad((1.0, -2.0, 1.0), (1.0, 2.0 * (k * k - 1.0) / a0, (1.0 - k / quality + k * k) / a0))
        return shelf, highpass

    @staticmethod
    def blocks(samples: Buffer, rate: int) -> Buffer:
        # Mean-square power of each 400 ms block (100 ms hop), summed over channels.
        # Filtering uses the magnitude response only; phase does not change block energy
        # beyond transients (checked against FFmpeg's ebur128 to 0.1 LU).
        shelf, highpass = Loudness.filters(rate)
        hop = int(round(0.1 * rate))
        powers = None
        for channel in np.atleast_2d(samples):
            weighted = Signal.filter(channel.astype(np.float64), rate, lambda f: shelf.response(f, rate) * highpass.response(f, rate))
            hops = weighted.shape[-1] // hop
            energy = np.square(weighted[:hops * hop]).reshape(hops, hop).sum(axis=1)
            if hops < 4:
                block = np.array([energy.sum() / (4 * hop)])
            else:
                block = (energy[:-3] + energy[1:-2] + energy[2:-1] + energy[3:]) / (4 * hop)
            powers = block if powers is None else powers + block
        assert powers is not None
        return powers

    @staticmethod
    def gate(powers: Buffer) -> float:
        loudness = -0.691 + 10.0 * np.log10(np.maximum(powers, 1e-20))
        gated = powers[loudness > -70.0]
        if gated.size == 0:
            return -math.inf
        relative = -0.691 + 10.0 * math.log10(float(gated.mean())) - 10.0
        final = powers[(loudness > -70.0) & (loudness > relative)]
        return -0.691 + 10.0 * math.log10(float(final.mean()))

    @staticmethod
    def integrated(samples: Buffer, rate: int) -> float:
        return Loudness.gate(Loudness.blocks(samples, rate))
