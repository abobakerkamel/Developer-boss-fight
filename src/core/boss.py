from __future__ import annotations

from dataclasses import dataclass, field

from .enums import BossPhaseName


@dataclass(frozen=True)
class BossDefinition:
    """
    Static, data-driven description of a boss. Loaded from config/bosses.json.
    Nothing in here changes at runtime -- runtime state lives on BossEntity.
    """

    id: str
    name: str
    level: int
    max_hp: int
    allowed_gestures: tuple[str, ...]
    phases: tuple[str, ...]
    rage_threshold: float | None
    mechanic: str
    mechanic_params: dict
    rewards: dict

    @classmethod
    def from_dict(cls, data: dict) -> "BossDefinition":
        return cls(
            id=data["id"],
            name=data["name"],
            level=int(data["level"]),
            max_hp=int(data["max_hp"]),
            allowed_gestures=tuple(data.get("allowed_gestures", [])),
            phases=tuple(data.get("phases", [BossPhaseName.NORMAL.value])),
            rage_threshold=data.get("rage_threshold"),
            mechanic=data.get("mechanic", "none"),
            mechanic_params=data.get("mechanic_params", {}),
            rewards=data.get("rewards", {}),
        )

    @property
    def display_title(self) -> str:
        return f"{self.name} - LEVEL {self.level}"


@dataclass
class BossEntity:
    """
    Runtime instance of a boss fight. Holds everything that changes while
    the boss is alive: hp, phase, rage/shield flags, position on screen.

    This is the thing Step 2+ mechanics (regen, sequence, rage) will hang
    their logic off of. For Step 1 it is deliberately a plain data container
    with only the generic damage/heal operations -- no per-boss mechanic
    branching lives here yet.
    """

    definition: BossDefinition
    current_hp: int = field(init=False)
    current_phase: str = field(init=False)
    alive: bool = field(init=False, default=True)
    rage: bool = field(init=False, default=False)
    shield: bool = field(init=False, default=False)
    position: tuple[int, int] | None = field(init=False, default=None)
    grabbed: bool = field(init=False, default=False)

    def __post_init__(self):
        self.current_hp = self.definition.max_hp
        self.current_phase = self.definition.phases[0] if self.definition.phases else BossPhaseName.NORMAL.value

    @property
    def hp_ratio(self) -> float:
        if self.definition.max_hp <= 0:
            return 0.0
        return max(0.0, self.current_hp / self.definition.max_hp)

    def take_damage(self, amount: int) -> int:
        """Apply damage, return the actual amount applied (clamped)."""
        if not self.alive or amount <= 0:
            return 0

        applied = min(self.current_hp, amount)
        self.current_hp -= applied

        if (
            self.definition.rage_threshold is not None
            and not self.rage
            and self.hp_ratio <= self.definition.rage_threshold
        ):
            self.rage = True
            self.current_phase = BossPhaseName.RAGE.value

        if self.current_hp <= 0:
            self.current_hp = 0
            self.alive = False

        return applied

    def heal(self, amount: int) -> int:
        if not self.alive or amount <= 0:
            return 0
        before = self.current_hp
        self.current_hp = min(self.definition.max_hp, self.current_hp + amount)
        return self.current_hp - before
