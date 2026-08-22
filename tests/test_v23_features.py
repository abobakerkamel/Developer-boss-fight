
import unittest

from src.gameplay.progression import ComboSystem, EnergySystem
from src.gameplay.boss_mechanics import BossMechanicsSystem
from src.core.boss import BossDefinition, BossEntity
from src.gesture_classifier import Gesture


class V23Tests(unittest.TestCase):
    def test_combo(self):
        c = ComboSystem()
        self.assertEqual(c.register_hit(1.0), 1)
        self.assertEqual(c.register_hit(1.5), 2)
        self.assertGreater(c.multiplier, 1.0)
        c.update(5.0)
        self.assertEqual(c.count, 0)

    def test_energy(self):
        e = EnergySystem()
        e.add_block()
        e.add_block()
        e.add_block()
        self.assertTrue(e.ready)
        self.assertEqual(e.value, 100.0)
        self.assertTrue(e.consume_all())
        self.assertEqual(e.value, 0)
        self.assertEqual(e.successful_blocks, 0)

    def test_memory_leak_regen(self):
        d = BossDefinition(
            id="mem", name="MEM", level=1, max_hp=100,
            allowed_gestures=(), phases=("NORMAL",), rage_threshold=None,
            mechanic="regen",
            mechanic_params={"regen_delay_seconds": 1.0, "regen_per_second": 10},
            rewards={}
        )
        b = BossEntity(d)
        b.take_damage(40)
        m = BossMechanicsSystem()
        m.reset_for_boss(b, 0.0)
        m.last_damage_at = 0.0
        m.last_regen_tick = 0.0
        m.update(b, 1.1)
        self.assertGreater(b.current_hp, 60)

    def test_sequence_unlock(self):
        d = BossDefinition(
            id="dep", name="DEP", level=1, max_hp=100,
            allowed_gestures=(), phases=("NORMAL",), rage_threshold=None,
            mechanic="sequence",
            mechanic_params={"required_sequence":["PINCH","FIST","OPEN_PALM"]},
            rewards={}
        )
        b = BossEntity(d)
        m = BossMechanicsSystem()
        m.reset_for_boss(b, 0.0)
        self.assertFalse(m.allow_damage(b, Gesture.PINCH, 1.0))
        self.assertFalse(m.allow_damage(b, Gesture.FIST, 1.2))
        self.assertFalse(m.allow_damage(b, Gesture.OPEN_PALM, 1.4))
        self.assertFalse(b.shield)
        self.assertTrue(m.allow_damage(b, Gesture.POINTING, 1.5))


if __name__ == "__main__":
    unittest.main()
