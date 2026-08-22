
import random
import cv2
import numpy as np


class ScreenFX:
    def __init__(self):
        self.shake_until = 0.0
        self.shake_strength = 0
        self.flash_until = 0.0
        self.flash_color = (255, 255, 255)
        self.flash_alpha = 0.0
        self.glitch_until = 0.0
        self.damage_until = 0.0

    def hit(self, now: float, critical=False):
        self.shake_until = max(self.shake_until, now + (0.28 if critical else 0.16))
        self.shake_strength = max(self.shake_strength, 12 if critical else 6)
        self.flash_until = max(self.flash_until, now + 0.13)
        self.flash_color = (80, 255, 255) if critical else (255, 255, 255)
        self.flash_alpha = 0.28 if critical else 0.16

    def player_hit(self, now: float):
        self.shake_until = max(self.shake_until, now + 0.22)
        self.shake_strength = max(self.shake_strength, 9)
        self.damage_until = max(self.damage_until, now + 0.35)

    def rage(self, now: float):
        self.glitch_until = max(self.glitch_until, now + 0.7)

    def ultimate(self, now: float):
        self.shake_until = max(self.shake_until, now + 0.45)
        self.shake_strength = max(self.shake_strength, 14)
        self.flash_until = max(self.flash_until, now + 0.22)
        self.flash_color = (255, 120, 255)
        self.flash_alpha = 0.30

    def apply(self, frame, now: float):
        h, w = frame.shape[:2]

        if now < self.glitch_until:
            # lightweight horizontal slice displacement
            out = frame.copy()
            for _ in range(5):
                y = random.randint(0, max(0, h - 12))
                sh = random.randint(4, 14)
                dx = random.randint(-25, 25)
                out[y:y+sh] = np.roll(out[y:y+sh], dx, axis=1)
            frame[:] = out

        if now < self.damage_until:
            overlay = np.zeros_like(frame)
            overlay[:, :] = (0, 0, 180)
            frame[:] = cv2.addWeighted(frame, 0.78, overlay, 0.22, 0)

        if now < self.flash_until:
            overlay = np.zeros_like(frame)
            overlay[:, :] = self.flash_color
            frame[:] = cv2.addWeighted(frame, 1.0-self.flash_alpha, overlay, self.flash_alpha, 0)

        if now < self.shake_until and self.shake_strength:
            dx = random.randint(-self.shake_strength, self.shake_strength)
            dy = random.randint(-self.shake_strength, self.shake_strength)
            matrix = np.float32([[1, 0, dx], [0, 1, dy]])
            frame[:] = cv2.warpAffine(frame, matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
