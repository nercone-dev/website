import sys
from pathlib import Path

# The sound tools are plain scripts next to this directory, not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
