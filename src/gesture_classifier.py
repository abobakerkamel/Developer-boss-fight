
from enum import Enum
import math
import numpy as np


class Gesture(str, Enum):
    NONE = "NONE"
    OPEN_PALM = "OPEN_PALM"
    POINTING = "POINTING"
    FIST = "FIST"
    PINCH = "PINCH"
    ULTIMATE = "ULTIMATE"


def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def angle(a, b, c):
    ba = np.array([a.x - b.x, a.y - b.y], dtype=np.float32)
    bc = np.array([c.x - b.x, c.y - b.y], dtype=np.float32)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-8:
        return 0.0
    cosine = float(np.dot(ba, bc) / denom)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


class GestureClassifier:
    FINGER_TRIPLES = {
        "index": (5, 6, 8),
        "middle": (9, 10, 12),
        "ring": (13, 14, 16),
        "pinky": (17, 18, 20),
    }

    def __init__(self):
        self.min_extended_angle = 150.0
        self.min_folded_angle = 122.0

        # V2.5: easier pinch. Normalized by palm scale.
        self.pinch_max_ratio = 0.48
        self.fist_thumb_to_palm_max_ratio = 0.86

    def _hand_scale(self, lm):
        return max(1e-6, distance(lm[0], lm[9]))

    def _finger_bend(self, lm, name):
        mcp, pip, tip = self.FINGER_TRIPLES[name]
        return angle(lm[mcp], lm[pip], lm[tip])

    def _finger_extended(self, lm, name):
        mcp, pip, tip = self.FINGER_TRIPLES[name]
        bend = self._finger_bend(lm, name)
        scale = self._hand_scale(lm)
        reach = distance(lm[tip], lm[mcp])
        return bend >= self.min_extended_angle and (reach / scale) > 0.65

    def _finger_folded(self, lm, name):
        mcp, pip, tip = self.FINGER_TRIPLES[name]
        bend = self._finger_bend(lm, name)
        scale = self._hand_scale(lm)
        tip_to_palm = distance(lm[tip], lm[0])
        return bend <= self.min_folded_angle or (tip_to_palm / scale) < 1.35

    def _deep_folded(self, lm, name):
        """Used only to distinguish a true closed fist from a pinch."""
        _, _, tip = self.FINGER_TRIPLES[name]
        bend = self._finger_bend(lm, name)
        scale = self._hand_scale(lm)
        tip_to_palm = distance(lm[tip], lm[0]) / scale
        return bend <= 95.0 and tip_to_palm < 1.18

    def _thumb_extended(self, lm):
        thumb_angle = angle(lm[2], lm[3], lm[4])
        scale = self._hand_scale(lm)
        reach = distance(lm[4], lm[5])
        return thumb_angle >= 145.0 and (reach / scale) > 0.55

    def _pinch_ratio(self, lm):
        return distance(lm[4], lm[8]) / self._hand_scale(lm)

    def _is_pinch(self, lm):
        """
        Easier PINCH:
        - thumb/index tips may be touching OR just clearly close.
        - index finger may be curved (natural pinch).
        - reject only when the hand is clearly a fully compact fist.
        """
        ratio = self._pinch_ratio(lm)
        if ratio > self.pinch_max_ratio:
            return False

        index_bend = self._finger_bend(lm, "index")
        compact_fist = (
            self._deep_folded(lm, "index")
            and self._deep_folded(lm, "middle")
            and self._deep_folded(lm, "ring")
            and self._deep_folded(lm, "pinky")
        )

        # A natural pinch normally has a curved but not fully crushed index.
        return (index_bend >= 78.0) and not compact_fist

    def _is_fist(self, lm):
        folds = [
            self._finger_folded(lm, "index"),
            self._finger_folded(lm, "middle"),
            self._finger_folded(lm, "ring"),
            self._finger_folded(lm, "pinky"),
        ]
        if not all(folds):
            return False

        scale = self._hand_scale(lm)
        thumb_to_palm = min(
            distance(lm[4], lm[5]),
            distance(lm[4], lm[9]),
        ) / scale

        return thumb_to_palm <= self.fist_thumb_to_palm_max_ratio

    def classify(self, lm):
        if lm is None or len(lm) != 21:
            return Gesture.NONE

        index_ext = self._finger_extended(lm, "index")
        middle_ext = self._finger_extended(lm, "middle")
        ring_ext = self._finger_extended(lm, "ring")
        pinky_ext = self._finger_extended(lm, "pinky")
        thumb_ext = self._thumb_extended(lm)

        middle_fold = self._finger_folded(lm, "middle")
        ring_fold = self._finger_folded(lm, "ring")
        pinky_fold = self._finger_folded(lm, "pinky")

        # PINCH must be tested first.
        if self._is_pinch(lm):
            return Gesture.PINCH

        if thumb_ext and index_ext and middle_ext and ring_ext and pinky_ext:
            return Gesture.OPEN_PALM

        if index_ext and middle_fold and ring_fold and pinky_fold:
            return Gesture.POINTING

        if self._is_fist(lm):
            return Gesture.FIST

        return Gesture.NONE

    @staticmethod
    def label(gesture):
        return {
            Gesture.NONE: "NONE",
            Gesture.OPEN_PALM: "OPEN PALM",
            Gesture.POINTING: "POINTING",
            Gesture.FIST: "FIST",
            Gesture.PINCH: "PINCH",
            Gesture.ULTIMATE: "ULTIMATE",
        }.get(gesture, "NONE")
