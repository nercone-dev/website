import fcntl
from typing import Union
from pathlib import Path

class Counter:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("0", encoding="utf-8")

    def get(self) -> int:
        return int(self.path.read_text(encoding="utf-8").strip())

    def increase(self) -> None:
        with self.path.open("r+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                value = int(f.read().strip())
            except ValueError:
                value = 0
            f.seek(0)
            f.write(str(value + 1))
            f.truncate()
