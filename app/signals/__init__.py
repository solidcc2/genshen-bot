from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.event_model import NormalizedEvent

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignalVerdict:
    bypass: bool = False
    score: int = 0
    reason: str = ""


class Signal(ABC):
    name: str = ""

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = config.get("enabled", True)
        self.weight = config.get("weight", 0)

    @abstractmethod
    def evaluate(self, event: NormalizedEvent) -> SignalVerdict: ...


_SIGNAL_DEFAULTS: dict[str, dict[str, Any]] = {
    "at_mention": {"enabled": True},
    "reply_to_bot": {"enabled": True},
    "keyword": {
        "enabled": True,
        "weight": 25,
        "triggers": ["原神", "胡桃"],
    },
    "question": {
        "enabled": True,
        "weight": 30,
        "patterns": ["?", "吗", "什么", "怎么", "哪", "谁", "为什么", "如何"],
    },
    "noise_filter": {
        "enabled": True,
        "weight": -50,
        "min_length": 2,
    },
    "random": {"enabled": True, "chance": 0.03, "weight": 60},
}


def _merge_signal_config(name: str, user_cfg: dict[str, Any]) -> dict[str, Any]:
    merged = dict(_SIGNAL_DEFAULTS.get(name, {}))
    merged.update(user_cfg)
    return merged


class SignalEvaluator:
    def __init__(
        self,
        mode: str,
        threshold: int,
        hard_signals: list[Signal],
        soft_signals: list[Signal],
        post_signals: list[Signal],
    ) -> None:
        self._mode = mode
        self._threshold = max(threshold, 0)
        self._hard = hard_signals
        self._soft = soft_signals
        self._post = post_signals

    def should_respond(self, event: NormalizedEvent) -> bool:
        if self._mode == "all":
            return True
        if self._mode == "none":
            return False

        # Hard signals: any bypass=True -> immediate PASS
        for sig in self._hard:
            if sig.enabled:
                v = sig.evaluate(event)
                if v.bypass:
                    return True

        # No soft signals -> only hard signals can trigger a response
        has_soft = any(s.enabled for s in self._soft)
        has_post = any(s.enabled for s in self._post)
        if not has_soft and not has_post:
            return False

        # Soft signals: accumulate score
        total = 0
        for sig in self._soft:
            if sig.enabled:
                v = sig.evaluate(event)
                total += v.score

        # Post-scorers: can force-pass
        for sig in self._post:
            if sig.enabled:
                v = sig.evaluate(event)
                if v.bypass:
                    return True

        return total >= self._threshold


def create_evaluator(
    mode: str,
    bot_user_id: str = "",
    bot_name: str = "",
    threshold: int = 50,
    signals: dict[str, Any] | None = None,
) -> SignalEvaluator:
    user_signals = signals or {}

    if mode == "mention":
        if not bot_user_id:
            _logger.warning(
                "response_mode=mention but bot_user_id is empty, degrading to 'all'"
            )
            mode = "all"
    elif mode == "auto":
        if not bot_user_id:
            _logger.warning(
                "response_mode=auto but bot_user_id is empty, "
                "at_mention and reply_to_bot signals disabled"
            )

    if mode == "mention":
        # mention mode: only at_mention and reply_to_bot signals
        from app.signals.hard import AtMention, ReplyToBot

        return SignalEvaluator(
            mode=mode,
            threshold=0,
            hard_signals=[
                AtMention(_merge_signal_config("at_mention", user_signals.get("at_mention", {})),
                          bot_user_id, bot_name),
                ReplyToBot(_merge_signal_config("reply_to_bot", user_signals.get("reply_to_bot", {})),
                           bot_user_id),
            ],
            soft_signals=[],
            post_signals=[],
        )

    if mode == "none":
        return SignalEvaluator(mode=mode, threshold=0, hard_signals=[], soft_signals=[], post_signals=[])

    if mode == "all":
        return SignalEvaluator(mode=mode, threshold=0, hard_signals=[], soft_signals=[], post_signals=[])

    # auto mode
    if mode != "auto":
        _logger.error("unknown response_mode=%s, falling back to 'auto'", mode)

    mode = "auto"

    from app.signals.hard import AtMention, ReplyToBot
    from app.signals.post import RandomPass
    from app.signals.soft import KeywordMatch, NoiseFilter, QuestionDetect

    hard_list: list[Signal] = []
    if bot_user_id:
        hard_list.append(
            AtMention(_merge_signal_config("at_mention", user_signals.get("at_mention", {})),
                      bot_user_id, bot_name)
        )
        hard_list.append(
            ReplyToBot(_merge_signal_config("reply_to_bot", user_signals.get("reply_to_bot", {})),
                       bot_user_id)
        )

    soft_list: list[Signal] = []
    kw_cfg = _merge_signal_config("keyword", user_signals.get("keyword", {}))
    if kw_cfg.get("triggers"):
        soft_list.append(KeywordMatch(kw_cfg))
    elif kw_cfg.get("enabled", True):
        _logger.warning("keyword signal enabled but triggers list is empty, disabling")

    soft_list.append(QuestionDetect(
        _merge_signal_config("question", user_signals.get("question", {}))
    ))
    soft_list.append(NoiseFilter(
        _merge_signal_config("noise_filter", user_signals.get("noise_filter", {}))
    ))

    post_list: list[Signal] = [RandomPass(
        _merge_signal_config("random", user_signals.get("random", {}))
    )]

    all_soft_disabled = all(not s.enabled for s in soft_list)
    if all_soft_disabled:
        _logger.warning(
            "all soft signals disabled in auto mode, "
            "behavior will approximate mention mode"
        )

    return SignalEvaluator(
        mode=mode,
        threshold=threshold,
        hard_signals=hard_list,
        soft_signals=soft_list,
        post_signals=post_list,
    )


__all__ = [
    "Signal",
    "SignalEvaluator",
    "SignalVerdict",
    "create_evaluator",
]
