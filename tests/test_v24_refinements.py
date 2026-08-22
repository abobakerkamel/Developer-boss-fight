
import unittest

from src.gameplay.progression import EnergySystem
from src.gameplay.aiming import AimSmoother


class V24RefinementTests(unittest.TestCase):
    def test_three_blocks_charge_ultimate(self):
        e = EnergySystem()
        e.add_block()
        self.assertFalse(e.ready)
        e.add_block()
        self.assertFalse(e.ready)
        e.add_block()
        self.assertTrue(e.ready)
        self.assertEqual(e.value, 100.0)

    def test_energy_resets_after_ultimate(self):
        e = EnergySystem()
        for _ in range(3):
            e.add_block()
        self.assertTrue(e.consume_all())
        self.assertEqual(e.value, 0.0)
        self.assertEqual(e.successful_blocks, 0)

    def test_aim_smoothing(self):
        a = AimSmoother(history_size=3)
        pts = {
            "index_mcp": (0, 0),
            "index_pip": (10, 0),
            "index_dip": (20, 0),
            "index_tip": (30, 0),
        }
        state = a.update(pts)
        self.assertGreater(state.direction[0], 0.99)
        self.assertLess(abs(state.direction[1]), 0.01)


if __name__ == "__main__":
    unittest.main()
