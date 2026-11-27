from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import ClassVar, Dict, List

import numpy as np

from dsp import Buffer

class Encoder:
    # Encodes float stereo audio with FFmpeg; the format follows the file extension.
    codecs: ClassVar[Dict[str, List[str]]] = {
        ".flac": ["-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24", "-compression_level", "8"],
        ".mp3": ["-c:a", "libmp3lame", "-b:a", "256k"],
        ".opus": ["-c:a", "libopus", "-b:a", "192k"],
        ".wav": ["-c:a", "pcm_s24le"],
    }

    def __init__(self, executable: str = "ffmpeg") -> None:
        located = shutil.which(executable)
        if located is None:
            raise FileNotFoundError(f"{executable} is required to encode audio")
        self.executable: str = located

    def write(self, path: Path, samples: Buffer, rate: int, title: str = "") -> None:
        suffix = path.suffix.lower()
        if suffix not in Encoder.codecs:
            raise ValueError(f"Unsupported audio format: {suffix}")
        if samples.ndim != 2 or samples.shape[0] != 2:
            raise ValueError("Expected stereo samples shaped (2, n)")
        interleaved = np.ascontiguousarray(samples.T, dtype="<f4").tobytes()
        command = [
            self.executable, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "f32le", "-ar", str(rate), "-ac", "2", "-i", "pipe:0",
            "-map_metadata", "-1", "-metadata", f"title={title}",
            # Leave encoder version strings out, so the files depend only on the audio.
            "-fflags", "+bitexact", "-flags:a", "+bitexact",
            *Encoder.codecs[suffix], str(path),
        ]
        subprocess.run(command, input=interleaved, check=True)
