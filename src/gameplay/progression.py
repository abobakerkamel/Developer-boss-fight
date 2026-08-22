
from dataclasses import dataclass


@dataclass
class ComboSystem:
    count: int = 0
    best: int = 0
    last_hit_at: float = -999.0
    timeout: float = 2.2

    def register_hit(self, now: float) -> int:
        if now - self.last_hit_at <= self.timeout:
            self.count += 1
        else:
            self.count = 1
        self.last_hit_at = now
        self.best = max(self.best, self.count)
        return self.count

    def update(self, now: float):
        if self.count and now - self.last_hit_at > self.timeout:
            self.count = 0

    @property
    def multiplier(self) -> float:
        if self.count <= 1:
            return 1.0
        return min(1.75, 1.0 + (self.count - 1) * 0.10)

    def reset(self):
        self.count = 0
        self.best = 0
        self.last_hit_at = -999.0


@dataclass
class EnergySystem:
    """
    V2.4 Deploy Energy rule:
    ONLY successful Firewall blocks charge Ultimate.

    1 block -> ~33%
    2 blocks -> ~66%
    3 blocks -> 100%
    """
    value: float = 0.0
    maximum: float = 100.0
    successful_blocks: int = 0

    @property
    def ratio(self) -> float:
        return max(0.0, min(1.0, self.value / self.maximum))

    @property
    def ready(self) -> bool:
        return self.successful_blocks >= 3 or self.value >= self.maximum

    def add_block(self):
        self.successful_blocks = min(3, self.successful_blocks + 1)

        if self.successful_blocks >= 3:
            self.value = 100.0
        else:
            self.value = self.successful_blocks * (100.0 / 3.0)

    def consume_all(self) -> bool:
        if not self.ready:
            return False
        self.value = 0.0
        self.successful_blocks = 0
        return True

    def reset(self):
        self.value = 0.0
        self.successful_blocks = 0
