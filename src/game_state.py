
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .core import GameFSM, GameFSMState, WaveManager
from .gesture_classifier import Gesture
from .gesture_stabilizer import GestureEvent
from .gameplay.player import PlayerState
from .gameplay.progression import ComboSystem, EnergySystem
from .gameplay.boss_mechanics import BossMechanicsSystem

GameState = GameFSMState

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = _PROJECT_ROOT / "config"


@dataclass(frozen=True)
class AttackConfig:
    damage: int
    label: str


class GameController:
    ATTACKS = {
        Gesture.OPEN_PALM: AttackConfig(0, "FIREWALL"),
        Gesture.POINTING: AttackConfig(20, "DEBUG LASER"),
        Gesture.FIST: AttackConfig(30, "FORCE GAUNTLET"),
        Gesture.PINCH: AttackConfig(0, "GRAVITY CLAW"),
        Gesture.ULTIMATE: AttackConfig(100, "DEPLOY ULTIMATE"),
    }

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.wave_manager = WaveManager(self.config_dir)
        self.fsm = GameFSM(on_enter=self._on_state_enter)
        self.boss = None
        self.player = PlayerState()
        self.combo = ComboSystem()
        self.energy = EnergySystem()
        self.mechanics = BossMechanicsSystem()

        self.last_attack_label = ""
        self.last_attack_time = 0.0
        self.attack_count = 0
        self.last_damage = 0
        self.last_hit_kind = ""
        self.last_hit_time = 0.0
        self.score = 0
        self._run_started = False
        self._last_boss_id = None

    def start(self, now: float = 0.0):
        if self._run_started:
            return
        self._run_started = True
        self.fsm.force_start(now)

    def update(self, now: float):
        if not self._run_started:
            self.start(now)
        self.fsm.update(now)
        self.combo.update(now)
        if self.boss is not None:
            self.mechanics.update(self.boss, now)

    def reset(self, now: float = 0.0):
        self.wave_manager.reset()
        self.boss = None
        self.player.reset()
        self.combo.reset()
        self.energy.reset()
        self.last_attack_label = ""
        self.last_attack_time = 0.0
        self.attack_count = 0
        self.last_damage = 0
        self.last_hit_kind = ""
        self.last_hit_time = 0.0
        self.score = 0
        self._run_started = False
        self._last_boss_id = None
        self.fsm.reset(now)
        self.start(now)

    def _on_state_enter(self, state: GameFSMState, now: float):
        if state == GameFSMState.SPAWNING:
            self.boss = self.wave_manager.spawn_current()
            if self.boss:
                self.mechanics.reset_for_boss(self.boss, now)
                self._last_boss_id = self.boss.definition.id
            return None

        if state == GameFSMState.NEXT_WAVE:
            if self.wave_manager.advance():
                return GameFSMState.SPAWNING
            return GameFSMState.RUN_COMPLETE
        return None

    def damage_player(self, amount: int, now: float) -> int:
        self.combo.count = 0
        return self.player.take_damage(amount, now)

    def register_block(self):
        self.player.register_block()
        self.energy.add_block()

    def handle_event(self, event: GestureEvent, now: float, attack_context: dict | None = None):
        if event is None or self.boss is None or not self.player.alive:
            return 0
        if self.fsm.current_state != GameFSMState.FIGHTING:
            return 0

        config = self.ATTACKS.get(event.gesture)
        if config is None:
            return 0

        attack_context = attack_context or {}
        damage = config.damage
        label = config.label

        # Dependency Hell shield/sequence intercepts attacks.
        if self.boss.definition.mechanic == "sequence":
            allowed = self.mechanics.allow_damage(self.boss, event.gesture, now)
            if not allowed:
                self.last_attack_label = self.mechanics.message or "DEPENDENCY SHIELD"
                self.last_attack_time = now
                self.last_damage = 0
                self.last_hit_kind = "BLOCKED"
                self.last_hit_time = now
                return 0

        if event.gesture == Gesture.POINTING:
            if not attack_context.get("hit_boss", False):
                damage = 0
                label = "DEBUG BLASTER - MISS"
            else:
                multiplier = float(attack_context.get("damage_multiplier", 1.0))
                damage = int(round(damage * multiplier))
                if attack_context.get("weak_point_name"):
                    label = f"CRITICAL DEBUG - {attack_context['weak_point_name']}"

        if event.gesture == Gesture.FIST:
            if not attack_context.get("punch_valid", False):
                damage = 0
                label = "FORCE GAUNTLET READY"
            else:
                speed = float(attack_context.get("punch_speed", 0.0))
                if speed >= 1000.0:
                    damage = 60
                    label = "CRITICAL FORCE PUNCH"
                else:
                    damage = 30
                    label = "FORCE PUNCH"

        if event.gesture == Gesture.PINCH:
            damage = 0
            label = "GRAVITY CLAW"

        if event.gesture == Gesture.ULTIMATE:
            if not self.energy.ready:
                damage = 0
                label = f"ULTIMATE NOT READY {int(self.energy.value)}%"
            else:
                self.energy.consume_all()
                damage = config.damage
                label = "DEPLOY TO PRODUCTION"

        self.last_attack_label = label
        self.last_attack_time = now
        self.attack_count += 1
        self.last_damage = 0
        self.last_hit_kind = "MISS" if damage <= 0 else "HIT"
        self.last_hit_time = now

        if damage:
            # Combo multiplier applies to normal attacks; ultimate remains fixed.
            if event.gesture != Gesture.ULTIMATE:
                damage = int(round(damage * self.combo.multiplier))

            base_before = self.boss.current_hp
            self.last_damage = self.boss.take_damage(damage)
            if self.last_damage:
                count = self.combo.register_hit(now)
                self.mechanics.notify_damage(now)
                self.score += int(self.last_damage * (1.0 + 0.08 * max(0, count - 1)))
                self.last_hit_kind = (
                    "CRITICAL"
                    if "CRITICAL" in label or self.last_damage >= 50
                    else "HIT"
                )

        if not self.boss.alive:
            reward = int(self.boss.definition.rewards.get("score", 0))
            self.score += reward
            self.fsm.report_boss_defeated(now)

        return self.last_damage

    @property
    def state(self): return self.fsm.current_state
    @property
    def health(self): return self.boss.current_hp if self.boss else 0
    @property
    def max_health(self): return self.boss.definition.max_hp if self.boss else 0
    @property
    def health_ratio(self): return self.boss.hp_ratio if self.boss else 0.0
    @property
    def boss_title(self): return self.boss.definition.display_title if self.boss else ""
    @property
    def current_wave_number(self): return self.wave_manager.current_wave_number
    @property
    def total_waves(self): return self.wave_manager.total_waves
