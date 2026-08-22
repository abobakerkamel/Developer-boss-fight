
from __future__ import annotations

import math
import cv2
import numpy as np

from ..gesture_classifier import Gesture
from ..gameplay.targeting import TargetingSystem, TargetingResult


class ARWeaponSystem:
    """V2.2 AR weapon layer: Shield, Blaster, Gauntlet, Gravity Claw, Ultimate."""

    def __init__(self):
        self.targeting = TargetingSystem()
        self.last_targeting = TargetingResult(False, False, None, None, 1.0)

    @staticmethod
    def _norm(direction):
        if not direction:
            return (1.0, 0.0)
        dx, dy = direction
        mag = max(1e-6, math.hypot(dx, dy))
        return dx / mag, dy / mag

    @staticmethod
    def _local_glow(frame, center, radius, color, alpha=0.32):
        cx, cy = center
        pad = max(20, radius + 24)
        x1, y1 = max(0, cx-pad), max(0, cy-pad)
        x2, y2 = min(frame.shape[1], cx+pad), min(frame.shape[0], cy+pad)
        if x1 >= x2 or y1 >= y2:
            return
        roi = frame[y1:y2, x1:x2]
        overlay = np.zeros_like(roi)
        cv2.circle(overlay, (cx-x1, cy-y1), radius, color, max(5, radius//4), cv2.LINE_AA)
        overlay = cv2.GaussianBlur(overlay, (0, 0), 7)
        roi[:] = cv2.addWeighted(roi, 1.0, overlay, alpha, 0)

    @staticmethod
    def _glow_poly(frame, pts, color, alpha=0.25):
        xs, ys = zip(*pts)
        pad = 22
        x1, y1 = max(0, min(xs)-pad), max(0, min(ys)-pad)
        x2, y2 = min(frame.shape[1], max(xs)+pad), min(frame.shape[0], max(ys)+pad)
        if x1 >= x2 or y1 >= y2:
            return
        roi = frame[y1:y2, x1:x2]
        shifted = np.asarray([(x-x1, y-y1) for x, y in pts], dtype=np.int32)
        overlay = np.zeros_like(roi)
        cv2.polylines(overlay, [shifted], True, color, 10, cv2.LINE_AA)
        overlay = cv2.GaussianBlur(overlay, (0, 0), 7)
        roi[:] = cv2.addWeighted(roi, 1.0, overlay, alpha, 0)
        cv2.polylines(frame, [np.asarray(pts, dtype=np.int32)], True, color, 2, cv2.LINE_AA)

    def draw_firewall(self, frame, hand_info, now):
        if not hand_info:
            return
        cx, cy = hand_info["center"]
        palm_size = max(55, int(hand_info.get("hand_scale_px", 120) * 0.85))
        pts = []
        for i in range(6):
            a = math.radians(60 * i + 30)
            pts.append((int(cx + palm_size * math.cos(a)), int(cy + palm_size * math.sin(a))))
        self._glow_poly(frame, pts, (255, 220, 70), 0.34)
        for r in (0.45, 0.72):
            cv2.circle(frame, (cx, cy), int(palm_size*r), (120, 220, 255), 1, cv2.LINE_AA)
        rotation = now * 2.2
        for i in range(6):
            a = rotation + i * math.tau / 6
            p = (int(cx + palm_size*0.72*math.cos(a)), int(cy + palm_size*0.72*math.sin(a)))
            cv2.circle(frame, p, 4, (100, 255, 255), -1, cv2.LINE_AA)
        cv2.putText(frame, "FIREWALL", (cx-60, cy-palm_size-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,255,255), 2, cv2.LINE_AA)

    def draw_blaster(self, frame, hand_info, targeting, now):
        if not hand_info:
            return
        wrist = hand_info["wrist"]
        tip = hand_info.get("aim_origin", hand_info["index_tip"])
        dx, dy = self._norm(hand_info.get("aim_direction", hand_info["index_direction"]))
        px, py = -dy, dx
        length = max(70, int(hand_info.get("hand_scale_px", 110)*0.85))
        width = max(18, int(length*0.28))
        muzzle = (int(tip[0]+dx*18), int(tip[1]+dy*18))
        back = (int(wrist[0]+dx*25), int(wrist[1]+dy*25))
        pts = [
            (int(back[0]+px*width), int(back[1]+py*width)),
            (int(muzzle[0]+px*width*0.55), int(muzzle[1]+py*width*0.55)),
            (int(muzzle[0]-px*width*0.55), int(muzzle[1]-py*width*0.55)),
            (int(back[0]-px*width), int(back[1]-py*width)),
        ]
        self._glow_poly(frame, pts, (255, 150, 60), 0.28)
        cv2.fillConvexPoly(frame, np.asarray(pts, np.int32), (80, 80, 105))
        cv2.polylines(frame, [np.asarray(pts, np.int32)], True, (255,230,150), 2, cv2.LINE_AA)
        cv2.circle(frame, muzzle, 7, (255,255,255), -1, cv2.LINE_AA)
        cv2.putText(frame, "DEBUG BLASTER", (max(10, back[0]-70), max(25, back[1]-35)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200,245,255), 2, cv2.LINE_AA)
        # Strong visual aim guide: finger tip -> target direction.
        end = (int(tip[0]+dx*1600), int(tip[1]+dy*1600))

        aim_overlay = frame.copy()
        cv2.line(aim_overlay, tip, end, (255, 180, 70), 5, cv2.LINE_AA)
        aim_overlay = cv2.GaussianBlur(aim_overlay, (0, 0), 4)
        frame[:] = cv2.addWeighted(frame, 1.0, aim_overlay, 0.16, 0)

        cv2.line(frame, tip, end, (150, 220, 255), 2, cv2.LINE_AA)
        cv2.circle(frame, tip, 8, (255,255,255), -1, cv2.LINE_AA)
        cv2.circle(frame, tip, 15, (100,220,255), 2, cv2.LINE_AA)

        # Finger-direction arrows make the source unmistakable.
        for dist in (45, 75, 105):
            px = int(tip[0] + dx*dist)
            py = int(tip[1] + dy*dist)
            perp_x, perp_y = -dy, dx
            a = (int(px - dx*10 + perp_x*6), int(py - dy*10 + perp_y*6))
            b = (px, py)
            c = (int(px - dx*10 - perp_x*6), int(py - dy*10 - perp_y*6))
            cv2.line(frame, a, b, (180,235,255), 2, cv2.LINE_AA)
            cv2.line(frame, c, b, (180,235,255), 2, cv2.LINE_AA)
        if targeting.impact_point:
            self.draw_target_lock(frame, targeting)

    def draw_gauntlet(self, frame, hand_info, motion_speed, now):
        if not hand_info:
            return
        cx, cy = hand_info["center"]
        r = max(38, int(hand_info.get("hand_scale_px", 100)*0.42))
        critical = motion_speed >= 1000
        color = (80, 120, 255) if not critical else (80, 255, 255)
        self._local_glow(frame, (cx, cy), r, color, 0.38)
        cv2.circle(frame, (cx, cy), r, color, 3, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), int(r*0.72), (255,255,255), 1, cv2.LINE_AA)
        for i in range(5):
            a = now*3.0 + i*math.tau/5
            p = (int(cx+r*0.85*math.cos(a)), int(cy+r*0.85*math.sin(a)))
            cv2.circle(frame, p, 4, color, -1, cv2.LINE_AA)
        label = "CRITICAL PUNCH!" if critical else "FORCE GAUNTLET READY"
        cv2.putText(frame, label, (max(10,cx-90), max(25,cy-r-18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)

    def draw_gravity_claw(self, frame, hand_info, boss_rect, grabbed):
        if not hand_info:
            return
        center = hand_info["center"]
        color = (255, 100, 255)
        self._local_glow(frame, center, 28, color, 0.30)
        cv2.circle(frame, center, 22, color, 2, cv2.LINE_AA)
        if boss_rect:
            bx, by, bw, bh = boss_rect
            boss_center = (bx+bw//2, by+bh//2)
            cv2.line(frame, center, boss_center, color, 3 if grabbed else 1, cv2.LINE_AA)
            for t in (0.25, 0.5, 0.75):
                x = int(center[0]+(boss_center[0]-center[0])*t)
                y = int(center[1]+(boss_center[1]-center[1])*t)
                cv2.circle(frame, (x,y), 4, (255,200,255), -1, cv2.LINE_AA)
        cv2.putText(frame, "GRAVITY CLAW" + (" - GRABBED" if grabbed else ""),
                    (max(10,center[0]-80), max(25,center[1]-42)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, color, 2, cv2.LINE_AA)

    def draw_ultimate(self, frame, hands_info, now):
        if len(hands_info) < 2:
            return
        c1, c2 = hands_info[0]["center"], hands_info[1]["center"]
        mid = ((c1[0]+c2[0])//2, (c1[1]+c2[1])//2)
        dist = max(70, int(math.hypot(c2[0]-c1[0], c2[1]-c1[1])*0.42))
        overlay = frame.copy()
        cv2.rectangle(overlay, (0,0), (frame.shape[1], frame.shape[0]), (20,10,35), -1)
        frame[:] = cv2.addWeighted(frame, 0.72, overlay, 0.28, 0)
        self._local_glow(frame, mid, dist, (255,80,255), 0.5)
        cv2.circle(frame, mid, dist, (255,120,255), 4, cv2.LINE_AA)
        cv2.circle(frame, mid, int(dist*0.72), (100,220,255), 3, cv2.LINE_AA)
        for i in range(12):
            a = -now*2 + i*math.tau/12
            p1 = (int(mid[0]+dist*0.74*math.cos(a)), int(mid[1]+dist*0.74*math.sin(a)))
            p2 = (int(mid[0]+dist*1.02*math.cos(a)), int(mid[1]+dist*1.02*math.sin(a)))
            cv2.line(frame, p1, p2, (180,180,255), 2, cv2.LINE_AA)
        cv2.putText(frame, "DEPLOY TO PRODUCTION", (max(20,mid[0]-145), max(35,mid[1]-dist-25)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.72, (240,220,255), 3, cv2.LINE_AA)

    @staticmethod
    def draw_target_lock(frame, result):
        if not result.impact_point:
            return
        cx, cy = result.impact_point
        radius = 28 if result.weak_point else 36
        color = (80,255,255) if result.weak_point else (120,220,255)
        cv2.circle(frame, (cx,cy), radius, color, 2, cv2.LINE_AA)
        for a in (0,90,180,270):
            rad = math.radians(a)
            p1 = (int(cx+(radius+6)*math.cos(rad)), int(cy+(radius+6)*math.sin(rad)))
            p2 = (int(cx+(radius+16)*math.cos(rad)), int(cy+(radius+16)*math.sin(rad)))
            cv2.line(frame,p1,p2,color,2,cv2.LINE_AA)
        label = "WEAK POINT LOCKED" if result.weak_point else "TARGET LOCKED"
        cv2.putText(frame,label,(cx-85,cy-radius-15),cv2.FONT_HERSHEY_SIMPLEX,0.48,color,2,cv2.LINE_AA)

    @staticmethod
    def draw_weak_points(frame, weak_points):
        for wp in weak_points:
            cv2.circle(frame, wp.center, wp.radius, (0,170,255), 1, cv2.LINE_AA)
            cv2.circle(frame, wp.center, 3, (0,255,255), -1, cv2.LINE_AA)
            cv2.putText(frame, wp.name, (wp.center[0]+wp.radius+4, wp.center[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,220,255), 1, cv2.LINE_AA)

    def update_and_render(self, frame, gesture, hand_info, boss_rect, weak_points, now,
                          motion_speed=0.0, grabbed=False):
        self.last_targeting = TargetingResult(False, False, None, None, 1.0)
        if gesture == Gesture.OPEN_PALM:
            self.draw_firewall(frame, hand_info, now)
        elif gesture == Gesture.POINTING and hand_info:
            self.last_targeting = self.targeting.evaluate(
                hand_info.get("aim_origin", hand_info["index_tip"]),
                hand_info.get("aim_direction", hand_info["index_direction"]),
                boss_rect,
                weak_points
            )
            self.draw_blaster(frame, hand_info, self.last_targeting, now)
        elif gesture == Gesture.FIST:
            self.draw_gauntlet(frame, hand_info, motion_speed, now)
        elif gesture == Gesture.PINCH:
            self.draw_gravity_claw(frame, hand_info, boss_rect, grabbed)
        return self.last_targeting
