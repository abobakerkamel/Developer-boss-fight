from __future__ import annotations

from pathlib import Path
import cv2


class AnimationPlayer:
    """Loads PNG frame sequences from one boss folder."""

    def __init__(self, root: str | Path, fps: float = 10.0):
        self.root = Path(root)
        self.fps = float(fps)
        self.animations: dict[str, list] = {}
        self.current = "idle"
        self.frame_index = 0
        self.last_time = 0.0
        self.loop = True
        self.on_finish = "idle"
        self._load()

    def _load(self):
        for folder in self.root.iterdir() if self.root.exists() else []:
            if not folder.is_dir():
                continue
            frames = []
            for path in sorted(folder.glob("*.png")):
                image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                if image is not None:
                    frames.append(image)
            if frames:
                self.animations[folder.name] = frames

    def has(self, name: str) -> bool:
        return bool(self.animations.get(name))

    def play(self, name: str, now: float, loop: bool = True, on_finish: str = "idle"):
        if not self.has(name):
            name = "idle" if self.has("idle") else name
        if name != self.current:
            self.current = name
            self.frame_index = 0
            self.last_time = now
        self.loop = loop
        self.on_finish = on_finish

    def update(self, now: float):
        frames = self.animations.get(self.current, [])
        if not frames:
            return None

        frame_duration = 1.0 / max(1.0, self.fps)
        if self.last_time == 0.0:
            self.last_time = now

        if now - self.last_time >= frame_duration:
            steps = max(1, int((now - self.last_time) / frame_duration))
            self.last_time += steps * frame_duration
            self.frame_index += steps

            if self.frame_index >= len(frames):
                if self.loop:
                    self.frame_index %= len(frames)
                else:
                    fallback = self.on_finish
                    if fallback != self.current and self.has(fallback):
                        self.current = fallback
                        self.frame_index = 0
                        self.loop = True
                        frames = self.animations[self.current]
                    else:
                        self.frame_index = len(frames) - 1

        return frames[min(self.frame_index, len(frames) - 1)]
