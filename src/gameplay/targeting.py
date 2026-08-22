from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class WeakPoint:
    name: str
    center: tuple[int, int]
    radius: int
    multiplier: float = 2.5


@dataclass(frozen=True)
class TargetingResult:
    locked: bool
    hit_boss: bool
    weak_point: WeakPoint | None
    impact_point: tuple[int, int] | None
    damage_multiplier: float


class TargetingSystem:
    """2D ray-vs-boss targeting used by the Debug Blaster."""

    def __init__(self, max_distance: int = 1400, lock_tolerance_px: int = 30):
        self.max_distance = max_distance
        self.lock_tolerance_px = lock_tolerance_px

    @staticmethod
    def _normalize(vx: float, vy: float) -> tuple[float, float]:
        mag = math.hypot(vx, vy)
        if mag < 1e-6:
            return 1.0, 0.0
        return vx / mag, vy / mag

    @staticmethod
    def _point_to_ray_distance(
        point: tuple[int, int],
        origin: tuple[int, int],
        direction: tuple[float, float],
    ) -> tuple[float, float]:
        px = point[0] - origin[0]
        py = point[1] - origin[1]
        projection = px * direction[0] + py * direction[1]
        closest_x = origin[0] + projection * direction[0]
        closest_y = origin[1] + projection * direction[1]
        distance = math.hypot(point[0] - closest_x, point[1] - closest_y)
        return distance, projection

    @staticmethod
    def _ray_rect_intersection(origin, direction, rect):
        if rect is None:
            return None
        x, y, w, h = rect
        dx, dy = direction
        t_min, t_max = 0.0, float("inf")

        for p, d, lo, hi in (
            (origin[0], dx, x, x + w),
            (origin[1], dy, y, y + h),
        ):
            if abs(d) < 1e-8:
                if p < lo or p > hi:
                    return None
                continue
            t1 = (lo - p) / d
            t2 = (hi - p) / d
            t1, t2 = min(t1, t2), max(t1, t2)
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
            if t_min > t_max:
                return None

        if t_max < 0:
            return None
        t = t_min if t_min >= 0 else t_max
        return (int(origin[0] + dx * t), int(origin[1] + dy * t))

    def evaluate(self, origin, direction, boss_rect, weak_points):
        if origin is None or direction is None or boss_rect is None:
            return TargetingResult(False, False, None, None, 1.0)

        direction = self._normalize(*direction)

        best_wp = None
        best_proj = float("inf")
        for wp in weak_points:
            distance, projection = self._point_to_ray_distance(
                wp.center, origin, direction
            )
            tolerance = wp.radius + self.lock_tolerance_px
            if 0 <= projection <= self.max_distance and distance <= tolerance:
                if projection < best_proj:
                    best_wp = wp
                    best_proj = projection

        if best_wp is not None:
            return TargetingResult(
                True,
                True,
                best_wp,
                best_wp.center,
                best_wp.multiplier,
            )

        impact = self._ray_rect_intersection(origin, direction, boss_rect)
        if impact is not None:
            return TargetingResult(True, True, None, impact, 1.0)

        return TargetingResult(False, False, None, None, 1.0)
