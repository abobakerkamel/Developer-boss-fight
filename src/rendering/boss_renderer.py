from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np

from ..core import GameFSMState
from .animation_player import AnimationPlayer
from ..gameplay.targeting import WeakPoint


class BossRenderer:
    """Renders the active data-driven boss as a 2D animated AR sprite."""

    def __init__(self, assets_root: str | Path):
        self.assets_root = Path(assets_root)
        self.player: AnimationPlayer | None = None
        self.boss_id: str | None = None
        self.rect: tuple[int, int, int, int] | None = None
        self.last_hp: int | None = None
        self.last_state = None
        self.hit_until = 0.0
        self.reaction_until = 0.0
        self.reaction_strength = 0
        self.reaction_kind = "hit"
        self.scale = 0.62

    def _ensure_boss(self, game, now):
        if game.boss is None:
            self.player = None
            self.boss_id = None
            self.rect = None
            return

        boss_id = game.boss.definition.id
        if boss_id != self.boss_id:
            self.boss_id = boss_id
            self.player = AnimationPlayer(self.assets_root / boss_id, fps=10)
            self.last_hp = game.health
            self.last_state = None
            if self.player.has("spawn"):
                self.player.play("spawn", now, loop=False, on_finish="idle")
            else:
                self.player.play("idle", now)

    def notify_hit(self, now: float, kind: str = "hit"):
        self.hit_until = now + 0.28
        self.reaction_until = now + (0.34 if kind in {"force", "critical"} else 0.22)
        self.reaction_strength = 34 if kind == "force" else (24 if kind == "critical" else 10)
        self.reaction_kind = kind
        if self.player is not None:
            self.player.play("hit", now, loop=False, on_finish="idle")

    @property
    def _rage(self):
        return False

    @staticmethod
    def _alpha_overlay(frame, sprite, x, y):
        h, w = sprite.shape[:2]
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(fw, x + w), min(fh, y + h)
        if x1 >= x2 or y1 >= y2:
            return None

        sx1, sy1 = x1 - x, y1 - y
        sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
        crop = sprite[sy1:sy2, sx1:sx2]

        if crop.ndim == 3 and crop.shape[2] == 4:
            alpha = crop[:, :, 3:4].astype(np.float32) / 255.0
            rgb = crop[:, :, :3].astype(np.float32)
            bg = frame[y1:y2, x1:x2].astype(np.float32)
            frame[y1:y2, x1:x2] = (rgb * alpha + bg * (1.0 - alpha)).astype(np.uint8)
        else:
            frame[y1:y2, x1:x2] = crop[:, :, :3]
        return (x1, y1, x2 - x1, y2 - y1)

    def render(self, frame, game, now):
        self._ensure_boss(game, now)
        if self.player is None or game.boss is None:
            return None

        # Animation state mapping.
        if game.state == GameFSMState.BOSS_DEFEATED:
            self.player.play("death", now, loop=False, on_finish="death")
        elif game.boss.rage and now >= self.hit_until:
            self.player.play("rage", now, loop=True)
        elif game.state == GameFSMState.SPAWNING and self.player.has("spawn"):
            pass
        elif now >= self.hit_until and self.player.current not in {"spawn", "death"}:
            self.player.play("idle", now, loop=True)

        sprite = self.player.update(now)
        if sprite is None:
            return None

        fh, fw = frame.shape[:2]
        target_h = int(fh * self.scale)
        scale = target_h / max(1, sprite.shape[0])
        sprite = cv2.resize(sprite, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        # Default floating placement. Gravity Claw may override the runtime position.
        bob = int(8 * np.sin(now * 2.5))
        if game.boss.grabbed and game.boss.position is not None:
            cx, cy = game.boss.position
        else:
            cx = int(fw * 0.72)
            cy = int(fh * 0.54) + bob
        if now < self.reaction_until:
            progress = max(0.0, (self.reaction_until - now) / 0.34)
            cx += int(self.reaction_strength * progress)

        x = cx - sprite.shape[1] // 2
        y = cy - sprite.shape[0] // 2

        if now < self.hit_until:
            # hit flash without changing sprite assets
            if sprite.ndim == 3 and sprite.shape[2] >= 3:
                rgb = sprite[:, :, :3].astype(np.int16)
                rgb = np.clip(rgb + 70, 0, 255).astype(np.uint8)
                sprite = sprite.copy()
                sprite[:, :, :3] = rgb

        self.rect = self._alpha_overlay(frame, sprite, x, y)
        game.boss.position = (cx, cy)
        return self.rect

    def get_weak_points(self, game) -> list[WeakPoint]:
        if self.rect is None or game.boss is None:
            return []
        x, y, w, h = self.rect
        # Core + eye-like top point. Scales with current sprite rectangle.
        return [
            WeakPoint("CORE", (x + int(w * 0.50), y + int(h * 0.55)), max(12, int(w * 0.09)), 2.5),
            WeakPoint("EYE", (x + int(w * 0.50), y + int(h * 0.28)), max(10, int(w * 0.07)), 2.0),
        ]
