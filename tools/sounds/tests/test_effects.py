import math
from typing import ClassVar

import numpy as np
import pytest

from effects import Limiter, Loudness
from midi import MIDIFile, Tempo, Track
from mixer import Mixer

class TestEffects:
    RATE: ClassVar[int] = 48000

    @staticmethod
    def sine(level_db: float, seconds: float, frequency: float = 1000.0) -> np.ndarray:
        time = np.arange(int(seconds * TestEffects.RATE)) / TestEffects.RATE
        tone = 10.0 ** (level_db / 20.0) * np.sin(2 * math.pi * frequency * time)
        return np.stack((tone, tone))

    # EBU Tech 3341, minimum requirements test cases 1 and 2: stereo 1 kHz sine.
    @pytest.mark.parametrize("level", [-23.0, -33.0])
    def test_integrated_loudness_of_sine(self, level: float) -> None:
        assert Loudness.integrated(TestEffects.sine(level, 20.0), TestEffects.RATE) == pytest.approx(level, abs=0.1)

    def test_relative_gate(self) -> None:
        # EBU Tech 3341 case 3: -36, -23, -36 dBFS for 10, 60, 10 s gives -23 LUFS.
        signal = np.concatenate((TestEffects.sine(-36.0, 10.0), TestEffects.sine(-23.0, 60.0), TestEffects.sine(-36.0, 10.0)), axis=-1)
        assert Loudness.integrated(signal, TestEffects.RATE) == pytest.approx(-23.0, abs=0.1)

    def test_absolute_gate(self) -> None:
        # EBU Tech 3341 case 5: blocks below -70 LKFS are ignored.
        signal = np.concatenate((TestEffects.sine(-26.0, 20.0), TestEffects.sine(-20.0, 20.1), TestEffects.sine(-26.0, 20.0)), axis=-1)
        assert Loudness.integrated(signal, TestEffects.RATE) == pytest.approx(-23.0, abs=0.1)
        silence = np.concatenate((np.zeros((2, 10 * TestEffects.RATE)), TestEffects.sine(-23.0, 20.0), np.zeros((2, 10 * TestEffects.RATE))), axis=-1)
        assert Loudness.integrated(silence, TestEffects.RATE) == pytest.approx(-23.0, abs=0.1)

    def test_limiter_keeps_peaks_under_ceiling(self) -> None:
        signal = TestEffects.sine(6.0, 2.0, 100.0)
        limited, reduction = Limiter(ceiling=-1.0).process(signal, TestEffects.RATE)
        assert np.abs(limited).max() <= 10.0 ** (-1.0 / 20.0) + 1e-9
        assert reduction < -6.0

    def test_limiter_leaves_quiet_audio_untouched(self) -> None:
        signal = TestEffects.sine(-12.0, 1.0)
        limited, reduction = Limiter(ceiling=-1.0).process(signal, TestEffects.RATE)
        assert np.allclose(limited, signal)
        assert reduction == 0.0

    def test_limiter_look_ahead_matches_setting(self) -> None:
        # Gain reduction must begin no earlier than the look-ahead (plus one block) before a peak.
        signal = np.full((2, TestEffects.RATE), 0.5)
        signal[:, TestEffects.RATE // 2] = 2.0
        limiter = Limiter(ceiling=-1.0, lookahead=0.005, block=32)
        limited, _ = limiter.process(signal, TestEffects.RATE)
        first = int(np.argmax(np.abs(limited[0] - signal[0]) > 1e-9))
        assert TestEffects.RATE // 2 - first <= int(0.005 * TestEffects.RATE) + 2 * limiter.block

    def test_controller_defaults_and_holds(self) -> None:
        # General MIDI: expression starts at 127 and a controller holds its value until changed.
        midi = MIDIFile(tempos=[Tempo(0, 120.0)])
        track = Track("Pad")
        track.control(1920, 11, 0)
        track.control(3840, 11, 127)
        midi.tracks.append(track)
        mixer = Mixer(TestEffects.RATE)
        curve = mixer.expression(midi, track, TestEffects.RATE * 3)
        assert curve is not None
        assert curve[0] == pytest.approx(1.0)
        assert curve[int(0.9 * TestEffects.RATE)] == pytest.approx(1.0)
        assert curve[int(1.5 * TestEffects.RATE)] == pytest.approx(0.0)
        assert curve[int(2.5 * TestEffects.RATE)] == pytest.approx(1.0)
