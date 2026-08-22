
from pathlib import Path
import os
import threading


class SoundManager:
    """Zero-dependency sound manager. Uses winsound on Windows; no-op elsewhere."""

    def __init__(self, assets_dir):
        self.assets_dir = Path(assets_dir)
        self.enabled = True
        try:
            import winsound
            self._winsound = winsound
        except Exception:
            self._winsound = None

    def play(self, name: str):
        if not self.enabled or self._winsound is None:
            return
        path = self.assets_dir / f"{name}.wav"
        if not path.exists():
            return
        try:
            self._winsound.PlaySound(
                str(path),
                self._winsound.SND_FILENAME
                | self._winsound.SND_ASYNC
                | self._winsound.SND_NODEFAULT,
            )
        except Exception:
            pass

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled
