
from dataclasses import dataclass
import math
import random

import cv2
import numpy as np


@dataclass
class BossProjectile:
    start: tuple[int, int]
    target: tuple[int, int]
    launched_at: float
    charge_duration: float = 0.55
    travel_duration: float = 0.85
    damage: int = 20
    resolved: bool = False

    @property
    def impact_time(self) -> float:
        return self.launched_at + self.charge_duration + self.travel_duration

    def phase(self, now: float) -> str:
        age = now - self.launched_at
        if age < self.charge_duration:
            return "CHARGE"
        if age < self.charge_duration + self.travel_duration:
            return "TRAVEL"
        return "IMPACT"

    def charge_progress(self, now: float) -> float:
        return max(0.0, min(1.0, (now - self.launched_at) / max(1e-6, self.charge_duration)))

    def travel_progress(self, now: float) -> float:
        start = self.launched_at + self.charge_duration
        return max(0.0, min(1.0, (now - start) / max(1e-6, self.travel_duration)))

    def position(self, now: float) -> tuple[int, int]:
        if self.phase(now) == "CHARGE":
            return self.start

        t = self.travel_progress(now)

        # ease-in: projectile accelerates toward the player
        e = t * t
        x = self.start[0] + (self.target[0] - self.start[0]) * e
        y = self.start[1] + (self.target[1] - self.start[1]) * e
        return int(x), int(y)


@dataclass
class ImpactEffect:
    position: tuple[int, int]
    started_at: float
    blocked: bool
    duration: float = 0.48

    def alive(self, now: float) -> bool:
        return now - self.started_at <= self.duration

    def progress(self, now: float) -> float:
        return max(0.0, min(1.0, (now - self.started_at) / self.duration))


class BossCombatSystem:
    """
    Boss attack flow:
        CHARGE -> ENERGY ORB -> TRAIL -> IMPACT

    Firewall:
        impact -> shield explosion/ripple -> BLOCKED

    No Firewall:
        impact -> player hit flash/shake handled by ScreenFX -> HP loss
    """

    def __init__(self, attack_interval: float = 3.2):
        self.attack_interval = attack_interval
        self.last_attack_at = -999.0
        self.projectile: BossProjectile | None = None
        self.impact_effects: list[ImpactEffect] = []
        self.last_result = ""
        self.last_result_at = -999.0

    def reset(self):
        self.last_attack_at = -999.0
        self.projectile = None
        self.impact_effects.clear()
        self.last_result = ""
        self.last_result_at = -999.0

    def update(self, game, frame_shape, firewall_active: bool, now: float):
        if game.boss is None or not game.player.alive or game.state.value != "FIGHTING":
            self.projectile = None
            return

        h, w = frame_shape[:2]
        current_interval = 1.15 if game.boss.rage else 3.60

        if self.projectile is None and now - self.last_attack_at >= current_interval:
            start = game.boss.position or (int(w * 0.72), int(h * 0.50))
            target = (int(w * 0.50), int(h * 0.62))

            rage_bonus = 5 if game.boss.rage else 0
            travel_duration = 0.38 if game.boss.rage else 0.90
            charge_duration = 0.20 if game.boss.rage else 0.60

            self.projectile = BossProjectile(
                start=start,
                target=target,
                launched_at=now,
                charge_duration=charge_duration,
                travel_duration=travel_duration,
                damage=20 + rage_bonus,
            )
            self.last_attack_at = now

        if self.projectile is not None and self.projectile.phase(now) == "IMPACT":
            impact_pos = self.projectile.target

            if firewall_active:
                game.register_block()
                self.last_result = "FIREWALL BLOCKED"
                blocked = True
            else:
                game.damage_player(self.projectile.damage, now)
                self.last_result = f"PLAYER HIT -{self.projectile.damage}"
                blocked = False

            self.impact_effects.append(
                ImpactEffect(
                    position=impact_pos,
                    started_at=now,
                    blocked=blocked,
                )
            )

            self.last_result_at = now
            self.projectile = None

        self.impact_effects = [
            fx for fx in self.impact_effects if fx.alive(now)
        ]

    @staticmethod
    def _local_glow(frame, center, radius, color, alpha=0.35, sigma=8):
        cx, cy = center
        pad = radius + 30
        x1 = max(0, cx - pad)
        y1 = max(0, cy - pad)
        x2 = min(frame.shape[1], cx + pad)
        y2 = min(frame.shape[0], cy + pad)

        if x1 >= x2 or y1 >= y2:
            return

        roi = frame[y1:y2, x1:x2]
        overlay = np.zeros_like(roi)
        local = (cx - x1, cy - y1)

        cv2.circle(
            overlay,
            local,
            radius,
            color,
            max(8, radius // 2),
            cv2.LINE_AA,
        )

        overlay = cv2.GaussianBlur(
            overlay,
            (0, 0),
            sigma,
        )

        roi[:] = cv2.addWeighted(
            roi,
            1.0,
            overlay,
            alpha,
            0,
        )

    def _render_charge(self, frame, projectile, now):
        cx, cy = projectile.start
        t = projectile.charge_progress(now)

        # Energy core grows before launch.
        core_radius = int(6 + 18 * t)
        glow_radius = int(18 + 34 * t)

        self._local_glow(
            frame,
            (cx, cy),
            glow_radius,
            (0, 70, 255),
            alpha=0.42,
            sigma=9,
        )

        # Pulsating orange/red rings.
        pulse = 1.0 + 0.12 * math.sin(now * 18.0)
        cv2.circle(
            frame,
            (cx, cy),
            int(glow_radius * pulse),
            (0, 120, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (cx, cy),
            core_radius,
            (50, 150, 255),
            -1,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (cx, cy),
            max(3, core_radius // 3),
            (255, 255, 255),
            -1,
            cv2.LINE_AA,
        )

        # Rotating sparks around the charging orb.
        for i in range(10):
            a = now * 5.0 + i * math.tau / 10.0
            r = glow_radius + 7 + (i % 3) * 4
            px = int(cx + math.cos(a) * r)
            py = int(cy + math.sin(a) * r)
            cv2.circle(
                frame,
                (px, py),
                2 + (i % 2),
                (80, 190, 255),
                -1,
                cv2.LINE_AA,
            )

        cv2.putText(
            frame,
            "RAGE CHARGING!" if projectile.charge_duration <= 0.30 else "BOSS CHARGING...",
            (max(20, cx - 85), max(30, cy - glow_radius - 26)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (80, 180, 255),
            2,
            cv2.LINE_AA,
        )

    def _render_projectile(self, frame, projectile, now):
        x, y = projectile.position(now)
        t = projectile.travel_progress(now)

        # Projectile gets slightly larger as it approaches the player.
        core_radius = int(10 + 12 * t)
        glow_radius = int(core_radius + 20)

        # Direction vector.
        sx, sy = projectile.start
        tx, ty = projectile.target
        dx, dy = tx - sx, ty - sy
        mag = max(1.0, math.hypot(dx, dy))
        ux, uy = dx / mag, dy / mag

        # Long energy trail behind the orb.
        for i in range(7, 0, -1):
            trail_len = 18 * i
            px = int(x - ux * trail_len)
            py = int(y - uy * trail_len)

            r = max(2, int(core_radius * (i / 9)))
            cv2.circle(
                frame,
                (px, py),
                r,
                (0, 80 + 12 * i, 255),
                -1,
                cv2.LINE_AA,
            )

        # Outer glow and core.
        self._local_glow(
            frame,
            (x, y),
            glow_radius,
            (0, 70, 255),
            alpha=0.40,
            sigma=8,
        )

        cv2.circle(
            frame,
            (x, y),
            core_radius,
            (40, 140, 255),
            -1,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (x, y),
            max(4, core_radius // 3),
            (255, 255, 255),
            -1,
            cv2.LINE_AA,
        )

        # Flying sparks.
        for _ in range(5):
            px = x + random.randint(-glow_radius, glow_radius)
            py = y + random.randint(-glow_radius, glow_radius)
            cv2.circle(
                frame,
                (px, py),
                2,
                (70, 190, 255),
                -1,
                cv2.LINE_AA,
            )

        cv2.putText(
            frame,
            "RAGE ATTACK!" if projectile.travel_duration <= 0.50 else "INCOMING ATTACK",
            (max(20, x - 95), max(30, y - glow_radius - 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (70, 160, 255),
            2,
            cv2.LINE_AA,
        )

    def _render_impact(self, frame, effect, now):
        cx, cy = effect.position
        t = effect.progress(now)

        # Expanding rings.
        radius = int(18 + 125 * t)
        fade = max(0.0, 1.0 - t)

        if effect.blocked:
            color = (100, 240, 255)

            # Shield ripple.
            for scale in (0.55, 0.78, 1.0):
                rr = int(radius * scale)
                cv2.circle(
                    frame,
                    (cx, cy),
                    rr,
                    color,
                    max(1, int(4 * fade)),
                    cv2.LINE_AA,
                )

            # Hex-like impact polygon.
            pts = []
            for i in range(6):
                a = math.radians(60 * i + 30)
                rr = int(45 + 55 * t)
                pts.append((
                    int(cx + rr * math.cos(a)),
                    int(cy + rr * math.sin(a)),
                ))

            cv2.polylines(
                frame,
                [np.asarray(pts, dtype=np.int32)],
                True,
                color,
                2,
                cv2.LINE_AA,
            )

            label = "BLOCKED"
        else:
            color = (40, 80, 255)

            # Explosion rings.
            for scale in (0.45, 0.72, 1.0):
                rr = int(radius * scale)
                cv2.circle(
                    frame,
                    (cx, cy),
                    rr,
                    color,
                    max(1, int(5 * fade)),
                    cv2.LINE_AA,
                )

            label = "PLAYER HIT"

        self._local_glow(
            frame,
            (cx, cy),
            min(130, radius),
            color,
            alpha=0.33 * fade,
            sigma=10,
        )

        # Radial sparks.
        for i in range(18):
            a = i * math.tau / 18.0 + now * 2.0
            length = 25 + int(95 * t)
            p1 = (
                int(cx + math.cos(a) * 18),
                int(cy + math.sin(a) * 18),
            )
            p2 = (
                int(cx + math.cos(a) * length),
                int(cy + math.sin(a) * length),
            )
            cv2.line(
                frame,
                p1,
                p2,
                color,
                2,
                cv2.LINE_AA,
            )

        cv2.putText(
            frame,
            label,
            (max(20, cx - 65), max(35, cy - 145)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            color,
            3,
            cv2.LINE_AA,
        )

    def render(self, frame, now: float):
        if self.projectile is not None:
            phase = self.projectile.phase(now)

            if phase == "CHARGE":
                self._render_charge(
                    frame,
                    self.projectile,
                    now,
                )

            elif phase == "TRAVEL":
                self._render_projectile(
                    frame,
                    self.projectile,
                    now,
                )

        for effect in self.impact_effects:
            self._render_impact(
                frame,
                effect,
                now,
            )

        if now - self.last_result_at < 0.75 and self.last_result:
            cv2.putText(
                frame,
                self.last_result,
                (30, int(frame.shape[0] * 0.72)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (80, 255, 150)
                if "BLOCKED" in self.last_result
                else (80, 80, 255),
                3,
                cv2.LINE_AA,
            )
