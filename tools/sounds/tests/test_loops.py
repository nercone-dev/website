import math
from typing import ClassVar, Dict, Optional

import numpy as np
import pytest

from build import Builder
from dsp import Additive, Partial, Signal
from effects import Delay, Limiter, Reverb
from midi import MIDIFile, Tempo, Track
from mixer import Master, Mixer, Strip

class TestLoops:
    # A seamless loop is one period of a periodic signal: repeating the file must sound the
    # same as the steady state of the music played over and over.
    RATE: ClassVar[int] = 48000

    def test_fold_of_a_periodic_signal(self) -> None:
        period = 1000
        one = np.random.default_rng(1).standard_normal((2, period))
        repeated = np.tile(one, 3)
        assert np.allclose(Signal.fold(repeated, period), 3 * one)

    def test_fold_adds_a_partial_tail(self) -> None:
        signal = np.arange(10, dtype=np.float64)
        assert np.allclose(Signal.fold(signal, 4), [0 + 4 + 8, 1 + 5 + 9, 2 + 6, 3 + 7])

    def test_fold_rejects_an_empty_period(self) -> None:
        with pytest.raises(ValueError):
            Signal.fold(np.zeros(8), 0)

    def test_circular_filter_has_no_edges(self) -> None:
        # A sine with a whole number of cycles in the buffer is periodic; a circular filter
        # must scale it by the response at its frequency everywhere, ends included.
        count = 4800
        frequency = 100.0 * TestLoops.RATE / count
        time = np.arange(count) / TestLoops.RATE
        tone = np.sin(2 * math.pi * frequency * time)
        filtered = Signal.filter(tone, TestLoops.RATE, lambda f: Signal.lowpass(f, frequency, 2), circular=True)
        assert np.allclose(filtered, tone * float(Signal.lowpass(np.array([frequency]), frequency, 2)[0]), atol=1e-9)

    def test_circular_limiter_matches_the_steady_state(self) -> None:
        period = TestLoops.RATE // 2
        time = np.arange(period) / TestLoops.RATE
        one = np.stack([np.sin(2 * math.pi * 220.0 * time) * (0.6 + 0.8 * (time > 0.47))] * 2)
        limiter = Limiter(ceiling=-1.0)
        looped, _ = limiter.process(one, TestLoops.RATE, circular=True)
        long, _ = limiter.process(np.tile(one, 6), TestLoops.RATE)
        assert np.abs(looped).max() <= 10.0 ** (-1.0 / 20.0) + 1e-9
        assert np.allclose(looped, long[:, 3 * period:4 * period], atol=1e-6)

    @staticmethod
    def tone() -> Additive:
        return Additive((Partial(1.0, 1.0, 3.0), Partial(2.0, 0.3, 1.0)), attack=0.005, release=0.5)

    @staticmethod
    def score(passes: int) -> MIDIFile:
        # A 2 s pattern played `passes` times: a short note, and a note held across the end of
        # the pattern, so its release and the reverb must carry over into the next pass.
        midi = MIDIFile(tempos=[Tempo(0, 120.0)])
        track = Track("Tone")
        for index in range(passes):
            start = index * 4 * midi.resolution
            track.add(start, midi.resolution // 2, 72, 90)
            track.add(start + midi.resolution * 3, midi.resolution * 2, 69, 100)
        midi.tracks.append(track)
        return midi

    def strips(self) -> Dict[str, Strip]:
        return {"Tone": Strip(TestLoops.tone(), reverb=0.3, delay=0.2)}

    @staticmethod
    def master(loop: Optional[float], tail: float) -> Master:
        return Master(reverb=Reverb(decay=0.8), delay=Delay(time=0.375, feedback=0.4, repeats=4), loudness=-20.0, tail=tail, loop=loop)

    def test_loop_equals_the_steady_state_of_repeating_it(self) -> None:
        period = 2 * TestLoops.RATE
        looped = Mixer(TestLoops.RATE).mix(TestLoops.score(1), self.strips(), TestLoops.master(2.0, 3.0))
        repeated = Mixer(TestLoops.RATE).mix(TestLoops.score(6), self.strips(), TestLoops.master(None, 3.0))
        assert looped.shape == (2, period)
        steady = repeated[:, 4 * period:5 * period]
        assert np.allclose(looped, steady, atol=1e-5 * np.abs(steady).max())

    def test_rendered_loop_is_one_period_without_fade(self) -> None:
        audio = Mixer(TestLoops.RATE).render(TestLoops.score(1), self.strips(), TestLoops.master(2.0, 3.0))
        assert audio.shape == (2, 2 * TestLoops.RATE)
        # The held note's tail must reach the start, and the end must not be faded out.
        assert np.abs(audio[:, :int(0.1 * TestLoops.RATE)]).max() > 0.05 * np.abs(audio).max()
        assert np.abs(audio[:, -int(0.05 * TestLoops.RATE):]).max() > 0.05 * np.abs(audio).max()

    def test_loop_rejects_notes_after_its_end(self) -> None:
        with pytest.raises(ValueError):
            Mixer(TestLoops.RATE).render(TestLoops.score(1), self.strips(), TestLoops.master(1.0, 3.0))

class TestBuilder:
    def test_select_by_path_and_by_directory(self) -> None:
        assert Builder.select("zerc") == ["zerc"]
        assert Builder.select("user-interface/ringtone") == ["user-interface/ringtone"]
        expected = sorted(path for path, song in Builder.songs.items() if song.directory == "user-interface")
        assert expected
        assert Builder.select("user-interface") == expected
        assert Builder.select("user-interface/") == expected
        # A prefix of a directory name is not a directory.
        assert Builder.select("user") == []
