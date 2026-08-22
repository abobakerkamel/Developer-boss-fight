
import unittest

from src.gameplay.player import PlayerState
from src.gameplay.motion import HandMotionAnalyzer


class V22FeatureTests(unittest.TestCase):
    def test_player_damage_clamps(self):
        p = PlayerState(max_hp=100, hp=100)
        self.assertEqual(p.take_damage(30, 1.0), 30)
        self.assertEqual(p.hp, 70)
        self.assertEqual(p.take_damage(100, 2.0), 70)
        self.assertEqual(p.hp, 0)
        self.assertFalse(p.alive)

    def test_motion_speed(self):
        m = HandMotionAnalyzer(window_seconds=1.0)
        m.update((0, 0), 0.0)
        state = m.update((100, 0), 0.1)
        self.assertGreaterEqual(state.speed, 900)


if __name__ == "__main__":
    unittest.main()
