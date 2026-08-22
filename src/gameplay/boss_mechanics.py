
from dataclasses import dataclass
from ..gesture_classifier import Gesture


@dataclass
class BossMechanicsSystem:
    last_damage_at: float = -999.0
    last_regen_tick: float = -999.0
    sequence_index: int = 0
    sequence_unlocked_until: float = -999.0
    message: str = ""
    message_until: float = -999.0

    def reset_for_boss(self, boss, now: float):
        self.last_damage_at = now
        self.last_regen_tick = now
        self.sequence_index = 0
        self.sequence_unlocked_until = -999.0
        self.message = ""
        self.message_until = -999.0

        if boss and boss.definition.mechanic == "sequence":
            boss.shield = True

    def notify_damage(self, now: float):
        self.last_damage_at = now
        self.last_regen_tick = now

    def allow_damage(self, boss, gesture: Gesture, now: float) -> bool:
        if boss is None:
            return False

        if boss.definition.mechanic != "sequence":
            return True

        if now < self.sequence_unlocked_until:
            boss.shield = False
            return True

        boss.shield = True
        required = boss.definition.mechanic_params.get(
            "required_sequence", ["PINCH", "FIST", "OPEN_PALM"]
        )

        if not required:
            return True

        expected = required[self.sequence_index]

        if gesture.value == expected:
            self.sequence_index += 1
            self.message = f"DEPENDENCY {self.sequence_index}/{len(required)}"
            self.message_until = now + 0.8

            if self.sequence_index >= len(required):
                self.sequence_index = 0
                self.sequence_unlocked_until = now + 5.0
                boss.shield = False
                self.message = "DEPENDENCIES RESOLVED - SHIELD DOWN"
                self.message_until = now + 1.4
            return False

        self.sequence_index = 0
        self.message = "BUILD ERROR - SEQUENCE RESET"
        self.message_until = now + 0.9
        return False


    def regen_countdown(self, boss, now: float):
        if boss is None or boss.definition.mechanic != "regen":
            return None
        if boss.current_hp >= boss.definition.max_hp:
            return None
        delay = float(boss.definition.mechanic_params.get("regen_delay_seconds", 2.0))
        return max(0.0, delay - (now - self.last_damage_at))

    def update(self, boss, now: float):
        if boss is None or not boss.alive:
            return

        mechanic = boss.definition.mechanic

        if mechanic == "regen":
            params = boss.definition.mechanic_params

            # V2.4 defaults are deliberately obvious on video.
            delay = float(params.get("regen_delay_seconds", 2.0))
            tick_seconds = float(params.get("regen_tick_seconds", 0.5))
            regen_amount = int(params.get("regen_amount_per_tick", 5))

            if (
                boss.current_hp < boss.definition.max_hp
                and now - self.last_damage_at >= delay
                and now - self.last_regen_tick >= tick_seconds
            ):
                actual = boss.heal(regen_amount)
                self.last_regen_tick = now

                if actual:
                    self.message = f"MEMORY LEAK +{actual} HP"
                    self.message_until = now + 0.75

        elif mechanic == "sequence":
            if now >= self.sequence_unlocked_until:
                boss.shield = True

        elif mechanic == "rage" and boss.rage:
            self.message = "PRODUCTION RAGE MODE - ATTACK SPEED x2"
            self.message_until = max(self.message_until, now + 0.15)
