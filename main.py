
import math
import time
from pathlib import Path

import cv2

from src.camera import Camera
from src.game_state import GameController
from src.gesture_classifier import Gesture, GestureClassifier
from src.gesture_stabilizer import GestureEvent, GestureStabilizer
from src.hand_tracker import HandTracker
from src.hud import HUDRenderer
from src.model_downloader import ensure_hand_landmarker_model
from src.rendering import ARWeaponSystem, BossRenderer, ScreenFX
from src.vfx import VFXEngine
from src.gameplay import HandMotionAnalyzer, BossCombatSystem
from src.gameplay.aiming import AimSmoother
from src.audio import SoundManager


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "hand_landmarker.task"
BOSS_ASSETS = PROJECT_ROOT / "assets" / "bosses"
SOUND_ASSETS = PROJECT_ROOT / "assets" / "sounds"


def build_hand_info(landmarks, frame_shape):
    if landmarks is None or len(landmarks) != 21:
        return None

    h, w = frame_shape[:2]

    def px(index):
        return (
            int(max(0.0, min(1.0, landmarks[index].x)) * w),
            int(max(0.0, min(1.0, landmarks[index].y)) * h),
        )

    wrist = px(0)
    index_mcp = px(5)
    index_pip = px(6)
    index_dip = px(7)
    index_tip = px(8)
    middle_mcp = px(9)
    pinky_mcp = px(17)

    center = (
        int((wrist[0] + middle_mcp[0]) / 2),
        int((wrist[1] + middle_mcp[1]) / 2),
    )
    direction = (index_tip[0]-index_pip[0], index_tip[1]-index_pip[1])
    hand_scale_px = int(math.hypot(
        middle_mcp[0]-wrist[0], middle_mcp[1]-wrist[1]
    ) * 2.2)

    return {
        "center": center,
        "wrist": wrist,
        "index_mcp": index_mcp,
        "index_pip": index_pip,
        "index_dip": index_dip,
        "index_tip": index_tip,
        "index_direction": direction,
        "pinky_mcp": pinky_mcp,
        "hand_scale_px": max(60, hand_scale_px),
    }


def point_in_rect(point, rect, padding=45):
    if point is None or rect is None:
        return False
    x, y = point
    rx, ry, rw, rh = rect
    return rx-padding <= x <= rx+rw+padding and ry-padding <= y <= ry+rh+padding


def main():
    print("=" * 68)
    print("DEVELOPER BOSS FIGHT V2.5 - GAMEPLAY FIX")
    print("13 Boss Reaction | 14 Combo | 15 Energy")
    print("16 Boss Mechanics | 17 Advanced VFX | 18 Sound")
    print("=" * 68)

    try:
        ensure_hand_landmarker_model(MODEL_PATH)
        camera = Camera(0, 1280, 720, 30)
        tracker = HandTracker(
            model_path=str(MODEL_PATH),
            num_hands=2,
            detection_confidence=0.5,
            presence_confidence=0.5,
            tracking_confidence=0.5,
        )
    except Exception as error:
        print(f"ERROR: {error}")
        return

    classifier = GestureClassifier()
    stabilizer = GestureStabilizer(history_size=7, min_votes=5, cooldown_seconds=0.60)
    game = GameController()
    vfx = VFXEngine()
    screen_fx = ScreenFX()
    hud = HUDRenderer()
    boss_renderer = BossRenderer(BOSS_ASSETS)
    weapons = ARWeaponSystem()
    motion = HandMotionAnalyzer()
    aim_smoother = AimSmoother(history_size=7)
    boss_combat = BossCombatSystem(attack_interval=3.2)
    sound = SoundManager(SOUND_ASSETS)

    previous_time = time.perf_counter()
    debug_landmarks = False
    last_punch_at = -999.0
    last_ultimate_at = -999.0
    pinch_was_active = False
    last_player_hp = game.player.hp
    last_boss_id = None
    rage_seen = False
    last_combat_result = ""

    print("OPEN PALM -> Firewall")
    print("POINTING -> Debug Blaster / Weak Points")
    print("FAST FIST -> Force Gauntlet Punch")
    print("PINCH -> Gravity Claw")
    print("BOTH HANDS OPEN + 100% Energy -> Deploy Ultimate")
    print("Q quit | R reset | D landmarks | M sound")

    try:
        while True:
            frame = camera.read()
            if frame is None:
                break
            now = time.perf_counter()

            detection = tracker.process(frame)
            if debug_landmarks:
                tracker.draw(frame, detection)

            hands = detection.get("hands", [])
            infos = [build_hand_info(h, frame.shape) for h in hands]
            raw_gestures = [classifier.classify(h) for h in hands]

            first_info = infos[0] if infos else None
            raw_gesture = raw_gestures[0] if raw_gestures else Gesture.NONE

            # Smoothed fingertip aiming uses multiple index-finger joints.
            if raw_gesture == Gesture.POINTING and first_info is not None:
                aim_state = aim_smoother.update(first_info)
                if aim_state is not None:
                    first_info["aim_origin"] = aim_state.origin
                    first_info["aim_direction"] = aim_state.direction
                    first_info["aim_stability"] = aim_state.stability
            else:
                aim_smoother.reset()

            motion_state = motion.update(first_info["center"] if first_info else None, now)

            event, stable_gesture = stabilizer.update(
                raw_gesture, now,
                position=first_info["center"] if first_info else None,
            )

            previous_boss_id = game.boss.definition.id if game.boss else None
            game.update(now)
            current_boss_id = game.boss.definition.id if game.boss else None
            if current_boss_id and current_boss_id != last_boss_id:
                sound.play("wave")
                last_boss_id = current_boss_id
                rage_seen = False

            boss_rect = boss_renderer.render(frame, game, now)
            weak_points = boss_renderer.get_weak_points(game)

            # Gravity Claw
            pinch_active = raw_gesture == Gesture.PINCH and first_info is not None
            if game.boss is not None:
                if pinch_active and (
                    game.boss.grabbed
                    or point_in_rect(first_info["center"], boss_rect, padding=80)
                ):
                    if not game.boss.grabbed:
                        sound.play("grab")
                    game.boss.grabbed = True
                    game.boss.position = first_info["center"]
                elif not pinch_active and pinch_was_active:
                    game.boss.grabbed = False
            pinch_was_active = pinch_active

            if game.boss is not None and game.boss.grabbed:
                boss_rect = boss_renderer.render(frame, game, now)
                weak_points = boss_renderer.get_weak_points(game)

            display_gesture = raw_gesture if raw_gesture != Gesture.NONE else stable_gesture
            targeting = weapons.update_and_render(
                frame, display_gesture, first_info, boss_rect, weak_points, now,
                motion_speed=motion_state.speed,
                grabbed=bool(game.boss and game.boss.grabbed),
            )
            if display_gesture == Gesture.POINTING:
                weapons.draw_weak_points(frame, weak_points)

            # Static events
            if event is not None and event.gesture not in {Gesture.FIST, Gesture.PINCH}:
                context = None
                if event.gesture == Gesture.POINTING:
                    context = {
                        "hit_boss": targeting.hit_boss,
                        "damage_multiplier": targeting.damage_multiplier,
                        "weak_point_name": targeting.weak_point.name if targeting.weak_point else None,
                    }

                # OPEN PALM still feeds Dependency Hell sequence but has no normal damage.
                damage = game.handle_event(event, now, attack_context=context)

                if event.gesture == Gesture.OPEN_PALM:
                    vfx.trigger(event.gesture, first_info, now)

                if event.gesture == Gesture.POINTING and damage > 0:
                    vfx.trigger(event.gesture, first_info, now)

                if damage > 0:
                    critical = game.last_hit_kind == "CRITICAL"
                    boss_renderer.notify_hit(now, "critical" if critical else "hit")
                    screen_fx.hit(now, critical=critical)
                    sound.play("critical" if critical else "hit")

            # Dynamic Force Punch
            if (
                raw_gesture == Gesture.FIST
                and motion_state.speed >= 620.0
                and now - last_punch_at >= 0.75
                and game.player.alive
            ):
                punch_event = GestureEvent(Gesture.FIST, now, first_info["center"] if first_info else None)
                damage = game.handle_event(
                    punch_event, now,
                    attack_context={"punch_valid": True, "punch_speed": motion_state.speed},
                )
                if damage > 0:
                    vfx.trigger(Gesture.FIST, first_info, now)
                    kind = "critical" if game.last_hit_kind == "CRITICAL" else "force"
                    boss_renderer.notify_hit(now, kind)
                    screen_fx.hit(now, critical=game.last_hit_kind == "CRITICAL")
                    sound.play("critical" if game.last_hit_kind == "CRITICAL" else "hit")
                last_punch_at = now

            # Ultimate now requires 100% Energy
            both_open = (
                len(raw_gestures) >= 2
                and raw_gestures[0] == Gesture.OPEN_PALM
                and raw_gestures[1] == Gesture.OPEN_PALM
            )
            if both_open:
                weapons.draw_ultimate(frame, infos[:2], now)
                if game.energy.ready and now - last_ultimate_at >= 4.0 and game.player.alive:
                    ultimate_event = GestureEvent(Gesture.ULTIMATE, now, None)
                    damage = game.handle_event(ultimate_event, now)
                    if damage > 0:
                        boss_renderer.notify_hit(now, "critical")
                        screen_fx.ultimate(now)
                        sound.play("ultimate")
                    last_ultimate_at = now

            # Boss attacks / Player HP
            firewall_active = Gesture.OPEN_PALM in raw_gestures
            boss_combat.update(game, frame.shape, firewall_active, now)
            boss_combat.render(frame, now)

            if boss_combat.last_result != last_combat_result:
                if "BLOCKED" in boss_combat.last_result:
                    sound.play("block")
                elif "PLAYER HIT" in boss_combat.last_result:
                    sound.play("player_hit")
                last_combat_result = boss_combat.last_result

            if game.player.hp < last_player_hp:
                screen_fx.player_hit(now)
            last_player_hp = game.player.hp

            if game.boss and game.boss.rage and not rage_seen:
                rage_seen = True
                screen_fx.rage(now)
                sound.play("rage")

            vfx.update_and_render(frame, now)

            # Global post effect after scene/VFX, before HUD.
            screen_fx.apply(frame, now)

            if now - game.last_hit_time < 0.55 and game.last_attack_label:
                if game.last_damage:
                    text = (
                        f"CRITICAL -{game.last_damage}"
                        if game.last_hit_kind == "CRITICAL"
                        else f"HIT -{game.last_damage}"
                    )
                else:
                    text = game.last_attack_label
                cv2.putText(
                    frame, text,
                    (int(frame.shape[1]*0.55), int(frame.shape[0]*0.18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.82,
                    (0,255,255) if game.last_damage else (200,200,255),
                    3, cv2.LINE_AA,
                )

            delta = now - previous_time
            fps = 1.0 / delta if delta > 0 else 0.0
            previous_time = now
            hud.render(frame, game, stable_gesture, fps, now)

            cv2.imshow("Developer Boss Fight V2.5", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                game.reset(now)
                stabilizer.reset()
                motion.reset()
                aim_smoother.reset()
                vfx.reset()
                boss_combat.reset()
                last_punch_at = -999.0
                last_ultimate_at = -999.0
                last_player_hp = game.player.hp
                last_boss_id = None
                rage_seen = False
                last_combat_result = ""
            if key == ord("d"):
                debug_landmarks = not debug_landmarks
            if key == ord("m"):
                print("Sound:", "ON" if sound.toggle() else "OFF")

    finally:
        tracker.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
