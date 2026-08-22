
from dataclasses import dataclass


@dataclass
class PlayerState:
    max_hp: int = 100
    hp: int = 100
    last_damage_time: float = -999.0
    last_damage: int = 0
    blocks: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def hp_ratio(self) -> float:
        return max(0.0, self.hp / max(1, self.max_hp))

    def take_damage(self, amount: int, now: float) -> int:
        if amount <= 0 or not self.alive:
            return 0
        applied = min(self.hp, int(amount))
        self.hp -= applied
        self.last_damage = applied
        self.last_damage_time = now
        return applied

    def register_block(self):
        self.blocks += 1

    def reset(self):
        self.hp = self.max_hp
        self.last_damage_time = -999.0
        self.last_damage = 0
        self.blocks = 0
