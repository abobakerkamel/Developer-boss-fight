
import cv2
from .core import GameFSMState


class HUDRenderer:
    def _center_text(self, frame, text, y, scale, thickness, color):
        h, w = frame.shape[:2]
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        cv2.putText(frame, text, (max(10,(w-tw)//2), y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    @staticmethod
    def _bar(frame, x, y, width, height, ratio, fill_color, label):
        cv2.rectangle(frame, (x,y), (x+width,y+height), (30,30,35), -1)
        fill = int(width * max(0.0, min(1.0, ratio)))
        if fill:
            cv2.rectangle(frame, (x,y), (x+fill,y+height), fill_color, -1)
        cv2.rectangle(frame, (x,y), (x+width,y+height), (240,240,240), 2)
        cv2.putText(frame, label, (x+8,y+height-7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255,255,255), 2, cv2.LINE_AA)

    def render(self, frame, game, stable_gesture, fps, now=0.0):
        h, w = frame.shape[:2]
        cv2.putText(frame, "DEVELOPER BOSS FIGHT V2.5", (24,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255,255,255), 2, cv2.LINE_AA)

        self._bar(frame, 24, 45, 290, 23, game.player.hp_ratio, (80,200,80),
                  f"PLAYER HP {game.player.hp}/{game.player.max_hp}")

        cv2.putText(frame, game.boss_title or "...", (24,101),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.84, (255,240,255), 2, cv2.LINE_AA)
        self._bar(frame, 24, 115, min(510,w-48), 24, game.health_ratio, (0,180,0),
                  f"BOSS HP {game.health}/{game.max_health}")

        # Progression HUD
        self._bar(
            frame, 24, 152, 290, 20,
            game.energy.ratio,
            (180,80,230),
            f"DEPLOY ENERGY {int(game.energy.value)}% | BLOCKS {game.energy.successful_blocks}/3"
        )
        cv2.putText(frame, f"COMBO x{game.combo.count}", (24,205),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                    (0,255,255) if game.combo.count >= 3 else (230,230,230), 2, cv2.LINE_AA)
        cv2.putText(frame, f"SCORE {game.score}", (24,233),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (230,230,230), 2, cv2.LINE_AA)

        cv2.putText(frame, f"WAVE {game.current_wave_number}/{game.total_waves}",
                    (w-190,58), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                    (200,220,255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Gesture: {stable_gesture.value}", (w-230,88),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230,230,230), 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {int(fps)}", (w-125,28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (100,255,100), 2, cv2.LINE_AA)

        if game.boss:
            if game.boss.rage:
                cv2.putText(frame, "RAGE MODE x3 ATTACK SPEED", (w-315,128),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.56, (40,40,255), 2, cv2.LINE_AA)

            if game.boss.definition.mechanic == "regen" and game.boss.current_hp < game.boss.definition.max_hp:
                countdown = game.mechanics.regen_countdown(game.boss, now)
                if countdown is not None and countdown > 0:
                    cv2.putText(frame, f"MEMORY LEAK REGEN IN {countdown:.1f}s", (w-335,158),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180,100,255), 2, cv2.LINE_AA)
                elif countdown is not None:
                    cv2.putText(frame, "MEMORY LEAK REGENERATING +5 HP", (w-355,158),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (80,255,120), 2, cv2.LINE_AA)

        if game.energy.ready:
            self._center_text(frame, "ULTIMATE READY - OPEN BOTH HANDS",
                              h-52, 0.58, 2, (255,150,255))

        if game.mechanics.message and now < game.mechanics.message_until:
            self._center_text(frame, game.mechanics.message, int(h*0.30),
                              0.70, 2, (80,220,255))

        if game.last_attack_label:
            cv2.putText(frame, f"Attack: {game.last_attack_label}", (24,263),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255,255,255), 2, cv2.LINE_AA)

        if not game.player.alive:
            self._center_text(frame, "BUILD FAILED", int(h*0.50), 1.8, 4, (50,50,255))
            self._center_text(frame, "PRESS R TO RETRY", int(h*0.58), 0.8, 2, (255,255,255))
        elif game.state == GameFSMState.SPAWNING:
            self._center_text(frame, "INCOMING...", int(h*0.50), 1.4, 3, (0,200,255))
        elif game.state == GameFSMState.BOSS_DEFEATED:
            self._center_text(frame, "BUG FIXED", int(h*0.50), 1.8, 4, (0,255,255))
        elif game.state == GameFSMState.VICTORY:
            self._center_text(frame, "WAVE CLEARED", int(h*0.50), 1.4, 3, (100,255,150))
        elif game.state == GameFSMState.RUN_COMPLETE:
            self._center_text(frame, "ALL BUGS FIXED", int(h*0.50), 1.5, 4, (0,255,255))

        cv2.putText(frame, "Q Quit | R Reset | D Landmarks | M Sound",
                    (24,h-18), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                    (210,210,210), 1, cv2.LINE_AA)
