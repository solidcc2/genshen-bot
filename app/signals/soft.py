from __future__ import annotations

import re
from typing import Any

from app.event_model import NormalizedEvent
from app.signals import Signal, SignalVerdict


class QuestionDetect(Signal):
    """Score positively if the message looks like a question."""

    name = "question"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        raw = config.get("patterns", ["?", "吗", "什么", "怎么", "哪", "谁", "为什么", "如何"])
        self._patterns = [re.compile(re.escape(p), re.IGNORECASE) if len(p) == 1
                          else re.compile(p, re.IGNORECASE)
                          for p in raw]

    def evaluate(self, event: NormalizedEvent) -> SignalVerdict:
        text = event.text.strip()
        if not text:
            return SignalVerdict(score=0, reason="empty")

        for pat in self._patterns:
            if pat.search(text):
                return SignalVerdict(score=self.weight, reason=f"question_match")

        return SignalVerdict(score=0, reason="no_question")


class KeywordMatch(Signal):
    """Score positively if the message contains any trigger keyword."""

    name = "keyword"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        triggers = config.get("triggers", [])
        self._patterns = [re.compile(re.escape(t), re.IGNORECASE) for t in triggers]

    def evaluate(self, event: NormalizedEvent) -> SignalVerdict:
        text = event.text.strip()
        if not text:
            return SignalVerdict(score=0, reason="empty")

        for pat in self._patterns:
            if pat.search(text):
                return SignalVerdict(score=self.weight, reason="keyword_match")

        return SignalVerdict(score=0, reason="no_keyword")


class NoiseFilter(Signal):
    """Negative score for very short or low-information messages."""

    name = "noise_filter"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._min_length = config.get("min_length", 2)

    def evaluate(self, event: NormalizedEvent) -> SignalVerdict:
        text = event.text.strip()
        if not text:
            return SignalVerdict(score=self.weight, reason="empty_message")

        if len(text) < self._min_length:
            return SignalVerdict(score=self.weight, reason="too_short")

        return SignalVerdict(score=0, reason="ok")
