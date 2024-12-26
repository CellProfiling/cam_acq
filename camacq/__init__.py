"""Control microscope through client server program."""

from pathlib import Path

__version__ = (Path(__file__).parent / "VERSION").read_text(encoding="utf-8").strip()
