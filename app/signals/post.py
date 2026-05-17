from __future__ import annotations

import random
from typing import Any

from app.event_model import NormalizedEvent
from app.signals import Signal, SignalVerdict


class RandomPass(Signal):
    """Randomly force-pass with a configured probability."""

    name = "random"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._chance = config.get("chance", 0.03)

    def evaluate(self, event: NormalizedEvent) -> SignalVerdict:
        if random.random() < self._chance:
            return SignalVerdict(bypass=True, reason="random_pass")
        return SignalVerdict(score=0, reason="no_random")
