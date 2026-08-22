"""
Headless tests for the Step 1 refactor (Game Core: BossDefinition/BossEntity,
WaveManager, GameFSM, GameController). No camera / MediaPipe required.

Run with:
    python -m tests.test_game_core
or with pytest, if installed:
    pytest tests/test_game_core.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.game_state import GameController
from src.core import GameFSMState
from src.gesture_classifier import Gesture
from src.gesture_stabilizer import GestureEvent


def make_event(gesture, now):
    return GestureEvent(gesture=gesture, timestamp=now, position=(100, 100))


def defeat_current_boss(game: GameController, t: float) -> float:
    """Hammer FORCE PUSH (30 dmg) until the current boss's hp hits 0.
    Returns the timestamp of the last damaging event."""
    assert game.state == GameFSMState.FIGHTING, f"expected FIGHTING, got {game.state}"
    hits = 0
    while game.boss.alive and hits < 50:
        t += 0.65  # clears the (former) cooldown window comfortably
        game.handle_event(make_event(Gesture.FIST, t), t)
        game.update(t)
        hits += 1
    assert not game.boss.alive, "boss should be dead after enough hits"
    return t


def advance_time(game: GameController, t: float, seconds: float, step: float = 0.05) -> float:
    end = t + seconds
    while t < end:
        t += step
        game.update(t)
    return t


def test_wave1_boss_matches_original_prototype():
    game = GameController()
    t = 0.0
    game.update(t)  # auto-starts -> SPAWNING
    assert game.state == GameFSMState.SPAWNING
    assert game.boss is not None
    assert game.boss.definition.id == "bug_99"
    assert game.max_health == 100  # same HP as the original hardcoded prototype

    t = advance_time(game, t, 1.0)  # let SPAWNING -> FIGHTING auto-advance
    assert game.state == GameFSMState.FIGHTING
    print("OK: wave 1 spawns BUG - LEVEL 99 with 100 HP, matches original prototype")


def test_attacks_ignored_outside_fighting():
    game = GameController()
    t = 0.0
    game.update(t)
    assert game.state == GameFSMState.SPAWNING

    hp_before = game.health
    game.handle_event(make_event(Gesture.FIST, t), t)
    assert game.health == hp_before, "damage must not apply before FIGHTING"
    print("OK: attacks are ignored while boss is still spawning")


def test_full_state_machine_transition_sequence():
    """
    IDLE -> SPAWNING -> FIGHTING -> BOSS_DEFEATED -> VICTORY ->
    WAVE_TRANSITION -> (NEXT_WAVE, instantaneous) -> SPAWNING (wave 2) -> FIGHTING

    Rather than asserting an exact state at a hand-picked timestamp (which is
    flaky near auto-advance boundaries with float time), this records every
    distinct state the FSM passes through and checks the *order* is exactly
    the one described in Phase 2 of the brief.
    """
    game = GameController()
    t = 0.0
    assert game.fsm.current_state == GameFSMState.IDLE

    observed = [GameFSMState.IDLE]
    game.update(t)
    if game.state != observed[-1]:
        observed.append(game.state)

    # Drive time forward in fine steps until we've fought and killed wave 1's
    # boss and reached wave 2's FIGHTING state, recording every distinct
    # state transition along the way.
    fought_wave1 = False
    for _ in range(2000):
        t += 0.02
        game.update(t)

        if game.state != observed[-1]:
            observed.append(game.state)

        if game.state == GameFSMState.FIGHTING and not fought_wave1 and game.boss.definition.id == "bug_99":
            t = defeat_current_boss(game, t)
            fought_wave1 = True
            if game.state != observed[-1]:
                observed.append(game.state)

        if game.state == GameFSMState.FIGHTING and game.boss is not None and game.boss.definition.id == "memory_leak_120":
            break

    expected = [
        GameFSMState.IDLE,
        GameFSMState.SPAWNING,
        GameFSMState.FIGHTING,
        GameFSMState.BOSS_DEFEATED,
        GameFSMState.VICTORY,
        GameFSMState.WAVE_TRANSITION,
        GameFSMState.SPAWNING,
        GameFSMState.FIGHTING,
    ]
    assert observed == expected, f"unexpected transition order: {[s.value for s in observed]}"
    assert game.current_wave_number == 2
    print("OK: full FSM sequence IDLE..WAVE_TRANSITION..SPAWNING..FIGHTING(wave2) in exact order")


def test_illegal_transition_is_rejected():
    game = GameController()
    t = 0.0
    game.update(t)  # SPAWNING
    try:
        game.fsm.transition_to(GameFSMState.RUN_COMPLETE, t)
        raise AssertionError("illegal transition should have raised")
    except ValueError:
        pass
    print("OK: illegal transitions raise ValueError instead of silently corrupting state")


def test_all_four_waves_clear_to_run_complete():
    game = GameController()
    t = 0.0
    game.update(t)

    expected_bosses = ["bug_99", "memory_leak_120", "dependency_hell_150", "production_bug_999"]

    for wave_index, expected_id in enumerate(expected_bosses, start=1):
        t = advance_time(game, t, 1.0)
        assert game.state == GameFSMState.FIGHTING
        assert game.boss.definition.id == expected_id, (
            f"wave {wave_index}: expected {expected_id}, got {game.boss.definition.id}"
        )

        t = defeat_current_boss(game, t)

        if wave_index < len(expected_bosses):
            # BOSS_DEFEATED(1.0) + VICTORY(1.2) + WAVE_TRANSITION(0.8) = 3.0s
            # elapsed before SPAWNING begins, which itself lasts 0.8s. Land
            # comfortably inside that [3.0, 3.8) window.
            t = advance_time(game, t, 3.3)
            assert game.state == GameFSMState.SPAWNING
        else:
            # RUN_COMPLETE is terminal, so any generous wait works here.
            t = advance_time(game, t, 4.0)
            assert game.state == GameFSMState.RUN_COMPLETE

    print("OK: all 4 waves clear in order and the run ends at RUN_COMPLETE")


def test_reset_returns_to_wave_one():
    game = GameController()
    t = 0.0
    game.update(t)
    t = advance_time(game, t, 1.0)
    t = defeat_current_boss(game, t)
    t = advance_time(game, t, 4.0)
    assert game.current_wave_number == 2

    t += 1.0
    game.reset(t)
    assert game.current_wave_number == 1
    assert game.boss.definition.id == "bug_99"
    assert game.health == game.max_health
    print("OK: reset() returns the run to wave 1 with a full-health boss")


def run_all():
    tests = [
        test_wave1_boss_matches_original_prototype,
        test_attacks_ignored_outside_fighting,
        test_full_state_machine_transition_sequence,
        test_illegal_transition_is_rejected,
        test_all_four_waves_clear_to_run_complete,
        test_reset_returns_to_wave_one,
    ]
    for test in tests:
        test()
    print(f"\n{len(tests)}/{len(tests)} Step-1 tests passed.")


if __name__ == "__main__":
    run_all()
