
from collections import deque
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MotionSample:
    timestamp: float
    center: tuple[int, int]


@dataclass(frozen=True)
class MotionState:
    velocity: tuple[float, float]
    speed: float
    displacement: tuple[float, float]


class HandMotionAnalyzer:
    """Small temporal buffer for dynamic punch / throw-style interactions."""

    def __init__(self, window_seconds: float = 0.22, max_samples: int = 20):
        self.window_seconds = window_seconds
        self.samples = deque(maxlen=max_samples)

    def update(self, center: tuple[int, int] | None, now: float) -> MotionState:
        if center is None:
            self.samples.clear()
            return MotionState((0.0, 0.0), 0.0, (0.0, 0.0))

        self.samples.append(MotionSample(now, center))
        while len(self.samples) > 2 and now - self.samples[0].timestamp > self.window_seconds:
            self.samples.popleft()

        if len(self.samples) < 2:
            return MotionState((0.0, 0.0), 0.0, (0.0, 0.0))

        first = self.samples[0]
        last = self.samples[-1]
        dt = max(1e-6, last.timestamp - first.timestamp)
        dx = last.center[0] - first.center[0]
        dy = last.center[1] - first.center[1]
        vx, vy = dx / dt, dy / dt
        return MotionState((vx, vy), math.hypot(vx, vy), (dx, dy))

    def reset(self):
        self.samples.clear()
