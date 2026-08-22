import math
import random
import time

import cv2
import numpy as np

from .gesture_classifier import Gesture


def alpha_blend(base, overlay, alpha):
    return cv2.addWeighted(base, 1.0, overlay, alpha, 0)


def glow_line(frame, start, end, core_width=3, glow_width=19, color=(255, 255, 255)):
    overlay = frame.copy()
    cv2.line(overlay, start, end, color, glow_width, cv2.LINE_AA)
    overlay = cv2.GaussianBlur(overlay, (0, 0), 8)
    frame[:] = cv2.addWeighted(frame, 1.0, overlay, 0.42, 0)
    cv2.line(frame, start, end, (255, 255, 255), core_width, cv2.LINE_AA)


def draw_glowing_circle(frame, center, radius, color=(255, 220, 80), thickness=3, glow=18):
    overlay = frame.copy()
    cv2.circle(overlay, center, radius, color, glow, cv2.LINE_AA)
    overlay = cv2.GaussianBlur(overlay, (0, 0), 10)
    frame[:] = cv2.addWeighted(frame, 1.0, overlay, 0.35, 0)
    cv2.circle(frame, center, radius, color, thickness, cv2.LINE_AA)


class Effect:
    def __init__(self, start_time, duration=0.5):
        self.start_time = start_time
        self.duration = duration

    def age(self, now):
        return now - self.start_time

    def alive(self, now):
        return self.age(now) <= self.duration

    def render(self, frame, now):
        raise NotImplementedError


class FirewallEffect(Effect):
    def __init__(self, center, start_time):
        super().__init__(start_time, 0.65)
        self.center = center

    def render(self, frame, now):
        t = max(0.0, min(1.0, self.age(now) / self.duration))
        alpha = 1.0 - t

        base_radius = int(65 + 15 * math.sin(now * 9))
        draw_glowing_circle(
            frame,
            self.center,
            base_radius,
            (255, 210, 70),
            thickness=3,
            glow=16,
        )

        for i in range(6):
            angle = (now * 1.8) + i * math.tau / 6.0
            x = int(self.center[0] + base_radius * math.cos(angle))
            y = int(self.center[1] + base_radius * math.sin(angle))
            cv2.circle(frame, (x, y), 5, (80, 240, 255), -1, cv2.LINE_AA)

        overlay = frame.copy()
        cv2.circle(overlay, self.center, int(base_radius * 1.1), (60, 190, 255), -1, cv2.LINE_AA)
        frame[:] = cv2.addWeighted(frame, 1.0, overlay, 0.07 * alpha, 0)


class LaserEffect(Effect):
    def __init__(self, start, direction, start_time, length=900):
        super().__init__(start_time, 0.45)
        self.start = start
        dx, dy = direction
        norm = max(1e-6, math.hypot(dx, dy))
        self.direction = (dx / norm, dy / norm)
        self.length = length

    def render(self, frame, now):
        t = max(0.0, min(1.0, self.age(now) / self.duration))
        length = int(self.length * (0.65 + 0.35 * min(1.0, t * 2)))

        end = (
            int(self.start[0] + self.direction[0] * length),
            int(self.start[1] + self.direction[1] * length),
        )
        glow_line(frame, self.start, end)

        # Laser tip.
        cv2.circle(frame, end, 8, (255, 255, 255), -1, cv2.LINE_AA)
        for _ in range(5):
            r = random.randint(8, 22)
            a = random.random() * math.tau
            px = int(end[0] + r * math.cos(a))
            py = int(end[1] + r * math.sin(a))
            cv2.circle(frame, (px, py), 2, (180, 230, 255), -1, cv2.LINE_AA)


class ShockwaveEffect(Effect):
    def __init__(self, center, start_time):
        super().__init__(start_time, 0.7)
        self.center = center

    def render(self, frame, now):
        t = max(0.0, min(1.0, self.age(now) / self.duration))

        for offset in (0.0, 0.17, 0.34):
            local = t - offset
            if 0.0 <= local <= 1.0:
                radius = int(20 + 300 * local)
                thickness = max(1, int(7 - 4 * local))
                draw_glowing_circle(
                    frame,
                    self.center,
                    radius,
                    (255, 255, 255),
                    thickness=thickness,
                    glow=15,
                )


class GrabEffect(Effect):
    """PINCH -> GRAB / DEBUG. A closing claw/bracket that snaps shut on the
    target, with an imploding (inward-collapsing) ring instead of the usual
    outward burst -- visually distinct from FIST's shockwave."""

    def __init__(self, center, start_time):
        super().__init__(start_time, 0.5)
        self.center = center

    def render(self, frame, now):
        t = max(0.0, min(1.0, self.age(now) / self.duration))
        cx, cy = self.center

        # Imploding ring: starts wide, collapses toward the pinch point.
        start_radius, end_radius = 70, 14
        radius = int(start_radius + (end_radius - start_radius) * min(1.0, t * 1.4))
        draw_glowing_circle(
            frame,
            self.center,
            max(4, radius),
            (90, 255, 170),
            thickness=2,
            glow=14,
        )

        # Two closing pincer brackets ("[" "]") that snap shut on the target.
        gap = int(40 * max(0.0, 1.0 - t * 1.3)) + 6
        arm = 26
        color = (120, 255, 190)

        cv2.line(frame, (cx - gap, cy - arm), (cx - gap, cy + arm), color, 3, cv2.LINE_AA)
        cv2.line(frame, (cx - gap, cy - arm), (cx - gap + 10, cy - arm), color, 3, cv2.LINE_AA)
        cv2.line(frame, (cx - gap, cy + arm), (cx - gap + 10, cy + arm), color, 3, cv2.LINE_AA)

        cv2.line(frame, (cx + gap, cy - arm), (cx + gap, cy + arm), color, 3, cv2.LINE_AA)
        cv2.line(frame, (cx + gap, cy - arm), (cx + gap - 10, cy - arm), color, 3, cv2.LINE_AA)
        cv2.line(frame, (cx + gap, cy + arm), (cx + gap - 10, cy + arm), color, 3, cv2.LINE_AA)

        if t < 0.55:
            cv2.putText(
                frame,
                "</>",
                (cx - 22, cy - arm - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (150, 255, 210),
                2,
                cv2.LINE_AA,
            )


class Particle:
    def __init__(self, origin, velocity, lifetime, radius):
        self.x, self.y = float(origin[0]), float(origin[1])
        self.vx, self.vy = velocity
        self.birth = time.perf_counter()
        self.lifetime = lifetime
        self.radius = radius

    def render(self, frame, now):
        age = now - self.birth
        if age > self.lifetime:
            return False

        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08

        alpha = 1.0 - age / self.lifetime
        r = max(1, int(self.radius * alpha))

        cv2.circle(
            frame,
            (int(self.x), int(self.y)),
            r,
            (120, 220, 255),
            -1,
            cv2.LINE_AA,
        )
        return True


class VFXEngine:
    def __init__(self):
        self.effects = []
        self.particles = []

    def trigger(self, gesture, hand_info, now):
        if hand_info is None:
            return

        center = hand_info["center"]

        if gesture == Gesture.OPEN_PALM:
            self.effects.append(
                FirewallEffect(center, now)
            )
            self._spawn_particles(center, 18)

        elif gesture == Gesture.POINTING:
            direction = hand_info["index_direction"]
            self.effects.append(
                LaserEffect(
                    hand_info["index_tip"],
                    direction,
                    now,
                )
            )
            self._spawn_particles(hand_info["index_tip"], 14)

        elif gesture == Gesture.FIST:
            self.effects.append(
                ShockwaveEffect(center, now)
            )
            self._spawn_particles(center, 30)

        elif gesture == Gesture.PINCH:
            self.effects.append(
                GrabEffect(center, now)
            )
            self._spawn_particles(center, 16)

    def _spawn_particles(self, origin, count):
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(0.8, 4.5)
            velocity = (
                math.cos(angle) * speed,
                math.sin(angle) * speed,
            )
            self.particles.append(
                Particle(
                    origin=origin,
                    velocity=velocity,
                    lifetime=random.uniform(0.25, 0.7),
                    radius=random.uniform(2, 5),
                )
            )

    def update_and_render(self, frame, now):
        alive_effects = []
        for effect in self.effects:
            if effect.alive(now):
                effect.render(frame, now)
                alive_effects.append(effect)
        self.effects = alive_effects

        alive_particles = []
        for particle in self.particles:
            if particle.render(frame, now):
                alive_particles.append(particle)
        self.particles = alive_particles

    def reset(self):
        self.effects.clear()
        self.particles.clear()
