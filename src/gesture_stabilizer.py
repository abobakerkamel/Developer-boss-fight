from collections import deque
from dataclasses import dataclass
from .gesture_classifier import Gesture


@dataclass(frozen=True)
class GestureEvent:
    gesture: Gesture
    timestamp: float
    position: tuple[int, int] | None = None


class GestureStabilizer:
    def __init__(
        self,
        history_size: int = 7,
        min_votes: int = 5,
        cooldown_seconds: float = 0.60,
    ):
        if min_votes > history_size:
            raise ValueError("min_votes cannot exceed history_size")

        self.history = deque(maxlen=history_size)
        self.min_votes = min_votes
        self.cooldown_seconds = cooldown_seconds
        self.stable_gesture = Gesture.NONE
        self.last_event_time = -float("inf")

    def update(self, gesture, now, position=None):
        self.history.append(gesture)

        counts = {}
        for item in self.history:
            counts[item] = counts.get(item, 0) + 1

        candidate = max(counts, key=counts.get)
        votes = counts[candidate]

        if votes < self.min_votes:
            return None, self.stable_gesture

        if candidate != self.stable_gesture:
            self.stable_gesture = candidate

            if candidate != Gesture.NONE:
                if now - self.last_event_time >= self.cooldown_seconds:
                    self.last_event_time = now
                    return GestureEvent(candidate, now, position), candidate

        return None, self.stable_gesture

    def reset(self):
        self.history.clear()
        self.stable_gesture = Gesture.NONE
        self.last_event_time = -float("inf")
