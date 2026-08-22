
from collections import deque
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AimState:
    direction: tuple[float, float]
    origin: tuple[int, int]
    stability: float


class AimSmoother:
    """
    Smooths the pointing ray across recent frames.

    Direction is built from multiple index-finger segments rather than
    only PIP -> TIP:
        MCP -> PIP
        PIP -> DIP
        DIP -> TIP

    The distal segments receive higher weights so the ray visually follows
    the fingertip while staying stable.
    """

    def __init__(self, history_size: int = 7):
        self.directions = deque(maxlen=history_size)
        self.origins = deque(maxlen=history_size)

    @staticmethod
    def _normalize(x, y):
        mag = math.hypot(x, y)
        if mag < 1e-6:
            return 1.0, 0.0
        return x / mag, y / mag

    def update(self, points: dict | None) -> AimState | None:
        if not points:
            self.reset()
            return None

        mcp = points["index_mcp"]
        pip = points["index_pip"]
        dip = points["index_dip"]
        tip = points["index_tip"]

        segments = [
            (pip[0]-mcp[0], pip[1]-mcp[1], 0.15),
            (dip[0]-pip[0], dip[1]-pip[1], 0.30),
            (tip[0]-dip[0], tip[1]-dip[1], 0.55),
        ]

        dx = 0.0
        dy = 0.0
        for sx, sy, weight in segments:
            ux, uy = self._normalize(sx, sy)
            dx += ux * weight
            dy += uy * weight

        dx, dy = self._normalize(dx, dy)

        self.directions.append((dx, dy))
        self.origins.append(tip)

        avg_dx = sum(d[0] for d in self.directions) / len(self.directions)
        avg_dy = sum(d[1] for d in self.directions) / len(self.directions)
        avg_dx, avg_dy = self._normalize(avg_dx, avg_dy)

        ox = int(sum(p[0] for p in self.origins) / len(self.origins))
        oy = int(sum(p[1] for p in self.origins) / len(self.origins))

        # Stability: 1.0 means recent directions agree strongly.
        agreement = 0.0
        for ddx, ddy in self.directions:
            agreement += max(-1.0, min(1.0, ddx*avg_dx + ddy*avg_dy))
        stability = max(0.0, agreement / len(self.directions))

        return AimState((avg_dx, avg_dy), (ox, oy), stability)

    def reset(self):
        self.directions.clear()
        self.origins.clear()
