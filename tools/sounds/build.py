# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.5"]
# ///
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Type

from audio import Encoder
from midi import MIDIFile
from mixer import Mixer
from score import Song
from songs.alarms import DefaultAlarm, WakeUpAlarm
from songs.mirai import Mirai
from songs.notifications import AlertNotification, CautionNotification, DefaultNotification, InformationNotification, MessageNotification, WarningNotification
from songs.ringtone import Ringtone
from songs.zerc import Zerc
from songs.zercone import Zercone

class Builder:
    songs: ClassVar[Dict[str, Type[Song]]] = {
        song.path(): song for song in (
            Zerc, Zercone, Mirai,
            Ringtone, DefaultAlarm, WakeUpAlarm,
            DefaultNotification, InformationNotification, WarningNotification, CautionNotification, MessageNotification, AlertNotification,
        )
    }
    default_output: ClassVar[Path] = Path(__file__).resolve().parents[2].joinpath("public", "static", "assets", "sounds")
    default_formats: ClassVar[List[str]] = [".flac", ".mp3"]

    def __init__(self, output: Path, formats: List[str]) -> None:
        self.output: Path = output
        self.formats: List[str] = formats
        self.encoder: Encoder = Encoder()

    def build(self, song: Song) -> None:
        started = time.monotonic()
        path = self.output.joinpath(f"{song.path()}.mid")
        path.parent.mkdir(parents=True, exist_ok=True)
        song.compose().write(path)
        # Render from the file just written, so the MIDI file is the single source of the audio.
        midi = MIDIFile.read(path)
        mixer = Mixer(song.rate)
        audio = mixer.render(midi, song.strips(), song.master())
        for suffix in self.formats:
            self.encoder.write(path.with_suffix(suffix), audio, song.rate, song.title)
        report = ", ".join(f"{key}={value:.2f}" for key, value in mixer.report.items())
        print(f"{song.path()}: {audio.shape[-1] / song.rate:.2f} s, {report} ({time.monotonic() - started:.1f} s)")

    @classmethod
    def main(cls, arguments: Optional[List[str]] = None) -> None:
        parser = argparse.ArgumentParser(description="Compose and render the NecOS / nercone.dev sounds.")
        parser.add_argument("songs", nargs="*", metavar="song", help=f"songs to build, or directories of them: {', '.join(sorted(cls.songs))} (default: all)")
        parser.add_argument("--output", type=Path, default=cls.default_output, help="output directory")
        parser.add_argument("--format", action="append", dest="formats", choices=sorted({".flac", ".mp3", ".opus", ".wav"}), help="audio formats (default: .flac and .mp3)")
        options = parser.parse_args(arguments)
        selected: List[str] = []
        for argument in options.songs or sorted(cls.songs):
            matches = cls.select(argument)
            if not matches:
                parser.error(f"unknown song: {argument}")
            selected += [name for name in matches if name not in selected]
        builder = cls(options.output, options.formats or cls.default_formats)
        for name in selected:
            builder.build(cls.songs[name]())

    @classmethod
    def select(cls, argument: str) -> List[str]:
        # A song by its path ("user-interface/ringtone"), or every song in a directory ("user-interface").
        name = argument.strip("/")
        if name in cls.songs:
            return [name]
        return sorted(path for path in cls.songs if path.startswith(f"{name}/"))

if __name__ == "__main__":
    Builder.main()
