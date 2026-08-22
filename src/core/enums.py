from enum import Enum


class GameFSMState(str, Enum):
    """
    Top-level run state machine.

    IDLE            -> nothing spawned yet (fresh boot / after full reset)
    SPAWNING        -> boss spawn animation / intro window
    FIGHTING        -> active combat, gestures deal damage
    BOSS_DEFEATED   -> hp hit 0, defeat animation window
    VICTORY         -> victory banner window
    WAVE_TRANSITION -> brief "clearing" window between waves
    NEXT_WAVE       -> decides whether to spawn the next boss or end the run
    RUN_COMPLETE    -> all waves cleared, terminal until reset()
    """

    IDLE = "IDLE"
    SPAWNING = "SPAWNING"
    FIGHTING = "FIGHTING"
    BOSS_DEFEATED = "BOSS_DEFEATED"
    VICTORY = "VICTORY"
    WAVE_TRANSITION = "WAVE_TRANSITION"
    NEXT_WAVE = "NEXT_WAVE"
    RUN_COMPLETE = "RUN_COMPLETE"


class BossPhaseName(str, Enum):
    NORMAL = "NORMAL"
    RAGE = "RAGE"
