import math
from typing import ClassVar, List, Tuple, Type

import numpy as np
import pytest

from dsp import Signal
from midi import Pitch
from songs.notifications import AlertNotification, CautionNotification, Pulsed

class TestWarningHarmonics:
    # IEC 60601-1-8 guidance for alarm signals, as applied to the caution and alert sounds
    # (see .docs/sounds.md): a pulse's fundamental lies between 150 Hz and about 1 kHz, and
    # its first four harmonics are within 15 dB of each other, so it is heard through small
    # speakers, in noise and with high-frequency hearing loss.
    RATE: ClassVar[int] = 48000
    SPREAD: ClassVar[float] = 15.0
    # The pulse layers, with the interval above the written pitch and a typical velocity.
    LAYERS: ClassVar[List[Tuple[str, int, int]]] = [("Signal", 0, 100), ("Tone", 0, 100), ("Halo Left", 12, 90), ("Body", -12, 90)]

    @staticmethod
    def harmonics(song: Type[Pulsed], pitch: int) -> List[float]:
        # Levels (dB) of harmonics 1-4 of one pulse, all layers summed in mono and dry, with
        # each strip's gain and drive, measured over the held part of the pulse.
        strips = song().strips()
        count = int(0.1 * TestWarningHarmonics.RATE)
        mix = np.zeros(count)
        for name, interval, velocity in TestWarningHarmonics.LAYERS:
            strip = strips[name]
            rendered = strip.instrument.render(pitch + interval, velocity / 127.0, 0.1, TestWarningHarmonics.RATE)
            rendered = Signal.saturate(rendered, strip.drive).mean(axis=0) * 10.0 ** (strip.gain / 20.0)
            mix += Signal.fit(rendered, count)
        held = mix[int(0.02 * TestWarningHarmonics.RATE):]
        size = 1 << 16
        spectrum = np.abs(np.fft.rfft(held * np.hanning(held.shape[-1]), n=size))
        frequencies = np.fft.rfftfreq(size, 1.0 / TestWarningHarmonics.RATE)
        fundamental = Pitch.frequency(pitch)
        levels = []
        for harmonic in range(1, 5):
            band = (frequencies > harmonic * fundamental * 0.97) & (frequencies < harmonic * fundamental * 1.03)
            levels.append(20.0 * math.log10(float(spectrum[band].max())))
        return levels

    @pytest.mark.parametrize("song", [CautionNotification, AlertNotification])
    def test_first_four_harmonics_within_15_db(self, song: Type[Pulsed]) -> None:
        midi = song().compose()
        pitches = sorted({note.pitch for note in midi.track("Signal").notes})
        assert pitches
        for pitch in pitches:
            # About 1 kHz at most: the highest pulse note is D6 (1175 Hz).
            assert 150.0 <= Pitch.frequency(pitch) <= 1200.0
            levels = TestWarningHarmonics.harmonics(song, pitch)
            assert max(levels) - min(levels) <= TestWarningHarmonics.SPREAD, (Pitch.name(pitch), levels)
