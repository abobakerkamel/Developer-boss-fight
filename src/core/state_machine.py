from __future__ import annotations

from typing import Callable, Optional

from .enums import GameFSMState

# Explicit, validated transition graph. Any transition not listed here is
# rejected by transition_to(). This replaces the old linear if/elif state
# handling in GameController.
_ALLOWED_TRANSITIONS: dict[GameFSMState, set[GameFSMState]] = {
    GameFSMState.IDLE: {GameFSMState.SPAWNING},
    GameFSMState.SPAWNING: {GameFSMState.FIGHTING},
    GameFSMState.FIGHTING: {GameFSMState.BOSS_DEFEATED},
    GameFSMState.BOSS_DEFEATED: {GameFSMState.VICTORY},
    GameFSMState.VICTORY: {GameFSMState.WAVE_TRANSITION},
    GameFSMState.WAVE_TRANSITION: {GameFSMState.NEXT_WAVE},
    GameFSMState.NEXT_WAVE: {GameFSMState.SPAWNING, GameFSMState.RUN_COMPLETE},
    GameFSMState.RUN_COMPLETE: set(),  # terminal; only GameFSM.reset() escapes it
}

# States that advance automatically once they've been active for this long.
# FIGHTING, IDLE, NEXT_WAVE (decision only) and RUN_COMPLETE are not in here:
# FIGHTING ends on an external hp<=0 signal, IDLE ends on an explicit start(),
# NEXT_WAVE resolves instantly inside update(), RUN_COMPLETE is terminal.
_AUTO_ADVANCE_SECONDS: dict[GameFSMState, float] = {
    GameFSMState.SPAWNING: 0.8,
    GameFSMState.BOSS_DEFEATED: 1.0,
    GameFSMState.VICTORY: 1.2,
    GameFSMState.WAVE_TRANSITION: 0.8,
}

OnEnterCallback = Callable[[GameFSMState, float], Optional[GameFSMState]]


class GameFSM:
    """
    Small explicit state machine for the run-level game flow.

    `on_enter` is called every time a new state is entered, with signature
    (state, now) -> Optional[next_state]. It may return a state to request
    an immediate follow-up transition (used for NEXT_WAVE, which has to
    decide between SPAWNING and RUN_COMPLETE), or None to just react
    (e.g. GameController spawning VFX/HUD messages) without redirecting.
    """

    def __init__(self, on_enter: OnEnterCallback | None = None):
        self._on_enter = on_enter
        self.current_state = GameFSMState.IDLE
        self.state_entered_at = 0.0

    def transition_to(self, new_state: GameFSMState, now: float):
        allowed = _ALLOWED_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Illegal transition: {self.current_state.value} -> {new_state.value}"
            )
        self._enter(new_state, now)

    def _enter(self, state: GameFSMState, now: float):
        self.current_state = state
        self.state_entered_at = now

        if self._on_enter is not None:
            redirect = self._on_enter(state, now)
            if redirect is not None:
                self.transition_to(redirect, now)

    def force_start(self, now: float):
        """Only legal way to leave IDLE from outside the normal graph is via
        the graph itself, but IDLE -> SPAWNING still needs an explicit kick
        at boot; this is that kick."""
        self.transition_to(GameFSMState.SPAWNING, now)

    def report_boss_defeated(self, now: float):
        """External signal: FIGHTING -> BOSS_DEFEATED (hp hit 0)."""
        self.transition_to(GameFSMState.BOSS_DEFEATED, now)

    def update(self, now: float):
        duration = _AUTO_ADVANCE_SECONDS.get(self.current_state)
        if duration is None:
            return

        if now - self.state_entered_at < duration:
            return

        allowed = _ALLOWED_TRANSITIONS.get(self.current_state, set())
        if len(allowed) == 1:
            (only_next,) = tuple(allowed)
            self.transition_to(only_next, now)
        elif self.current_state == GameFSMState.WAVE_TRANSITION:
            self.transition_to(GameFSMState.NEXT_WAVE, now)

    def reset(self, now: float = 0.0):
        self.current_state = GameFSMState.IDLE
        self.state_entered_at = now
