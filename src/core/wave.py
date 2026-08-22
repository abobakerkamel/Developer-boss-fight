from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .boss import BossDefinition, BossEntity


@dataclass(frozen=True)
class WaveDefinition:
    wave_number: int
    boss_id: str


class WaveManager:
    """
    Owns the ordered list of waves and knows which boss definition belongs
    to which wave. It does NOT know about the FSM -- GameController asks it
    "give me the next boss" / "am I out of waves" and reacts accordingly.

    Everything is loaded from JSON so adding a 5th boss/wave later is a data
    change, not a code change (see Phase 18 in the brief).
    """

    def __init__(self, config_dir: Path):
        config_dir = Path(config_dir)
        bosses_raw = json.loads((config_dir / "bosses.json").read_text(encoding="utf-8"))
        waves_raw = json.loads((config_dir / "waves.json").read_text(encoding="utf-8"))

        self._boss_definitions: dict[str, BossDefinition] = {
            data["id"]: BossDefinition.from_dict(data) for data in bosses_raw
        }

        self._waves: list[WaveDefinition] = sorted(
            (WaveDefinition(wave_number=w["wave_number"], boss_id=w["boss_id"]) for w in waves_raw),
            key=lambda w: w.wave_number,
        )

        for wave in self._waves:
            if wave.boss_id not in self._boss_definitions:
                raise ValueError(
                    f"waves.json references unknown boss_id '{wave.boss_id}' "
                    f"(not present in bosses.json)"
                )

        self._index = 0  # index into self._waves for the CURRENT wave

    @property
    def total_waves(self) -> int:
        return len(self._waves)

    @property
    def current_wave_number(self) -> int:
        if self._index >= len(self._waves):
            return self.total_waves
        return self._waves[self._index].wave_number

    @property
    def is_last_wave(self) -> bool:
        return self._index >= len(self._waves) - 1

    @property
    def is_exhausted(self) -> bool:
        """True once every wave has been spawned and cleared."""
        return self._index >= len(self._waves)

    def current_boss_definition(self) -> BossDefinition:
        if self.is_exhausted:
            raise RuntimeError("WaveManager has no more waves; check is_exhausted first")
        wave = self._waves[self._index]
        return self._boss_definitions[wave.boss_id]

    def spawn_current(self) -> BossEntity:
        """Create a fresh BossEntity for the current wave."""
        return BossEntity(self.current_boss_definition())

    def advance(self) -> bool:
        """
        Move to the next wave. Returns True if there is another wave to
        fight, False if the run is complete.
        """
        self._index += 1
        return not self.is_exhausted

    def reset(self):
        self._index = 0
