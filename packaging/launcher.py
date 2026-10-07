"""PyInstaller entry point for the packaged desktop app."""
import os
import sys

# Windowed builds have no console: give print/logging somewhere harmless to write.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from app.desktop import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
