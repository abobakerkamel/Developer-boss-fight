
import json
import unittest
from pathlib import Path

from src.core.boss import BossDefinition, BossEntity
from src.gameplay.boss_mechanics import BossMechanicsSystem


class V25GameplayFixTests(unittest.TestCase):
    def test_dependency_hell_has_no_sequence_mechanic(self):
        root = Path(__file__).resolve().parents[1]
        bosses = json.loads((root / "config" / "bosses.json").read_text(encoding="utf-8"))
        dep = next(b for b in bosses if b["id"] == "dependency_hell_150")
        self.assertEqual(dep["mechanic"], "none")

    def test_memory_leak_regenerates_after_delay(self):
        d = BossDefinition(
            id="memory_leak_120",
            name="MEMORY LEAK",
            level=120,
            max_hp=150,
            allowed_gestures=(),
            phases=("NORMAL",),
            rage_threshold=None,
            mechanic="regen",
            mechanic_params={
                "regen_delay_seconds": 2.0,
                "regen_tick_seconds": 0.5,
                "regen_amount_per_tick": 5,
            },
            rewards={},
        )
        b = BossEntity(d)
        b.take_damage(50)
        m = BossMechanicsSystem()
        m.reset_for_boss(b, 0.0)
        m.notify_damage(0.0)

        m.update(b, 1.9)
        self.assertEqual(b.current_hp, 100)

        m.update(b, 2.1)
        self.assertEqual(b.current_hp, 105)

        m.update(b, 2.7)
        self.assertEqual(b.current_hp, 110)


if __name__ == "__main__":
    unittest.main()
