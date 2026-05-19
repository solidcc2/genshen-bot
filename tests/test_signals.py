from __future__ import annotations

from unittest.mock import patch

import pytest

from app.event_model import Mention, NormalizedEvent, Scene
from app.signals import SignalEvaluator, SignalVerdict, create_evaluator
from app.signals.hard import AtMention, ReplyToBot
from app.signals.post import RandomPass
from app.signals.soft import KeywordMatch, NoiseFilter, QuestionDetect
from tests.conftest import make_event


# ── Helpers ──

def _event(text: str, **overrides) -> NormalizedEvent:
    return make_event(text, **overrides)


def _group_event(text: str, **overrides) -> NormalizedEvent:
    return make_event(text, scene=Scene.GROUP, **overrides)


# ── SignalVerdict ──

class TestSignalVerdict:
    def test_defaults(self) -> None:
        v = SignalVerdict()
        assert v.bypass is False
        assert v.score == 0
        assert v.reason == ""


# ── AtMention ──

class TestAtMention:
    def test_bypass_when_mentioned(self) -> None:
        sig = AtMention({"enabled": True}, bot_user_id="123")
        event = _group_event("hello", mentions=(Mention(user_id="123"),))
        v = sig.evaluate(event)
        assert v.bypass is True
        assert "at_mention" in v.reason

    def test_no_bypass_when_not_mentioned(self) -> None:
        sig = AtMention({"enabled": True}, bot_user_id="123")
        event = _group_event("hello", mentions=(Mention(user_id="456"),))
        v = sig.evaluate(event)
        assert v.bypass is False

    def test_bypass_when_text_mentioned(self) -> None:
        sig = AtMention({"enabled": True}, bot_user_id="123", bot_name="genshin")
        event = _group_event("genshin help")
        v = sig.evaluate(event)
        assert v.bypass is True
        assert "text_mention" in v.reason

    def test_no_mentions_tuple(self) -> None:
        sig = AtMention({"enabled": True}, bot_user_id="123")
        event = _group_event("hello")
        v = sig.evaluate(event)
        assert v.bypass is False

    def test_disabled(self) -> None:
        sig = AtMention({"enabled": False}, bot_user_id="123")
        event = _group_event("hello", mentions=(Mention(user_id="123"),))
        # enabled=False still evaluates but SignalEvaluator skips it
        v = sig.evaluate(event)
        assert v.bypass is True  # signal logic still works


# ── ReplyToBot ──

class TestReplyToBot:
    def test_bypass_when_reply_to_bot(self) -> None:
        sig = ReplyToBot({"enabled": True}, bot_user_id="123")
        event = _group_event("ok", reply_to="123")
        v = sig.evaluate(event)
        assert v.bypass is True
        assert "reply_to_bot" in v.reason

    def test_no_bypass_when_reply_to_other(self) -> None:
        sig = ReplyToBot({"enabled": True}, bot_user_id="123")
        event = _group_event("ok", reply_to="456")
        v = sig.evaluate(event)
        assert v.bypass is False

    def test_no_bypass_when_no_reply(self) -> None:
        sig = ReplyToBot({"enabled": True}, bot_user_id="123")
        event = _group_event("ok")
        v = sig.evaluate(event)
        assert v.bypass is False


# ── QuestionDetect ──

class TestQuestionDetect:
    def test_scores_on_question_mark(self) -> None:
        sig = QuestionDetect({"enabled": True, "weight": 30, "patterns": ["?"]})
        event = _group_event("你好吗?")
        v = sig.evaluate(event)
        assert v.score == 30

    def test_scores_on_ma(self) -> None:
        sig = QuestionDetect({"enabled": True, "weight": 30, "patterns": ["吗"]})
        event = _group_event("你吃饭了吗")
        v = sig.evaluate(event)
        assert v.score == 30

    def test_scores_on_shenme(self) -> None:
        sig = QuestionDetect({"enabled": True, "weight": 30, "patterns": ["什么"]})
        event = _group_event("什么是原神")
        v = sig.evaluate(event)
        assert v.score == 30

    def test_no_score_on_statement(self) -> None:
        sig = QuestionDetect({"enabled": True, "weight": 30, "patterns": ["?", "吗", "什么"]})
        event = _group_event("今天天气不错")
        v = sig.evaluate(event)
        assert v.score == 0

    def test_zero_score_on_empty(self) -> None:
        sig = QuestionDetect({"enabled": True, "weight": 30})
        event = _group_event("")
        v = sig.evaluate(event)
        assert v.score == 0

    def test_uses_default_patterns(self) -> None:
        sig = QuestionDetect({"enabled": True, "weight": 30})
        event = _group_event("这个怎么用")
        v = sig.evaluate(event)
        assert v.score == 30


# ── KeywordMatch ──

class TestKeywordMatch:
    def test_scores_on_keyword(self) -> None:
        sig = KeywordMatch({"enabled": True, "weight": 25, "triggers": ["原神", "胡桃"]})
        event = _group_event("我喜欢原神")
        v = sig.evaluate(event)
        assert v.score == 25
        assert "keyword_match" in v.reason

    def test_scores_on_different_keyword(self) -> None:
        sig = KeywordMatch({"enabled": True, "weight": 25, "triggers": ["原神", "胡桃"]})
        event = _group_event("胡桃怎么配队")
        v = sig.evaluate(event)
        assert v.score == 25

    def test_no_score_without_keyword(self) -> None:
        sig = KeywordMatch({"enabled": True, "weight": 25, "triggers": ["原神", "胡桃"]})
        event = _group_event("今天天气不错")
        v = sig.evaluate(event)
        assert v.score == 0

    def test_no_score_on_empty(self) -> None:
        sig = KeywordMatch({"enabled": True, "weight": 25, "triggers": ["原神"]})
        event = _group_event("")
        v = sig.evaluate(event)
        assert v.score == 0

    def test_case_insensitive(self) -> None:
        sig = KeywordMatch({"enabled": True, "weight": 25, "triggers": ["genshin"]})
        event = _group_event("Genshin Impact")
        v = sig.evaluate(event)
        assert v.score == 25


# ── NoiseFilter ──

class TestNoiseFilter:
    def test_negative_score_on_short_message(self) -> None:
        sig = NoiseFilter({"enabled": True, "weight": -50, "min_length": 2})
        event = _group_event("a")
        v = sig.evaluate(event)
        assert v.score == -50

    def test_negative_score_on_empty(self) -> None:
        sig = NoiseFilter({"enabled": True, "weight": -50, "min_length": 2})
        event = _group_event("")
        v = sig.evaluate(event)
        assert v.score == -50

    def test_zero_score_on_normal_message(self) -> None:
        sig = NoiseFilter({"enabled": True, "weight": -50, "min_length": 2})
        event = _group_event("正常消息长度")
        v = sig.evaluate(event)
        assert v.score == 0

    def test_configurable_min_length(self) -> None:
        sig = NoiseFilter({"enabled": True, "weight": -30, "min_length": 5})
        event = _group_event("1234")
        v = sig.evaluate(event)
        assert v.score == -30

        event2 = _group_event("12345")
        v2 = sig.evaluate(event2)
        assert v2.score == 0


# ── RandomPass ──

class TestRandomPass:
    def test_bypass_on_random_hit(self) -> None:
        with patch("random.random", return_value=0.01):
            sig = RandomPass({"enabled": True, "chance": 0.03, "weight": 60})
            event = _group_event("hello")
            v = sig.evaluate(event)
            assert v.bypass is True
            assert "random_pass" in v.reason

    def test_no_bypass_on_random_miss(self) -> None:
        with patch("random.random", return_value=0.99):
            sig = RandomPass({"enabled": True, "chance": 0.03, "weight": 60})
            event = _group_event("hello")
            v = sig.evaluate(event)
            assert v.bypass is False


# ── SignalEvaluator (unit) ──

class TestSignalEvaluator:
    def test_mode_all_always_responds(self) -> None:
        evaluator = create_evaluator(mode="all")
        event = _group_event("hello")
        assert evaluator.should_respond(event) is True

    def test_mode_none_never_responds(self) -> None:
        evaluator = create_evaluator(mode="none")
        event = _group_event("hello")
        assert evaluator.should_respond(event) is False

    def test_mode_mention_bypass_on_at(self) -> None:
        evaluator = create_evaluator(mode="mention", bot_user_id="123")
        event = _group_event("hello", mentions=(Mention(user_id="123"),))
        assert evaluator.should_respond(event) is True

    def test_mode_mention_no_match(self) -> None:
        evaluator = create_evaluator(mode="mention", bot_user_id="123")
        event = _group_event("hello")
        assert evaluator.should_respond(event) is False

    def test_hard_signal_bypasses(self) -> None:
        evaluator = SignalEvaluator(
            mode="auto", threshold=50,
            hard_signals=[AtMention({"enabled": True}, bot_user_id="123")],
            soft_signals=[], post_signals=[],
        )
        event = _group_event("hello", mentions=(Mention(user_id="123"),))
        assert evaluator.should_respond(event) is True

    def test_soft_scores_above_threshold(self) -> None:
        evaluator = SignalEvaluator(
            mode="auto", threshold=50,
            hard_signals=[],
            soft_signals=[QuestionDetect({"enabled": True, "weight": 60, "patterns": ["?"]})],
            post_signals=[],
        )
        event = _group_event("你好吗?")
        assert evaluator.should_respond(event) is True

    def test_soft_scores_below_threshold(self) -> None:
        evaluator = SignalEvaluator(
            mode="auto", threshold=50,
            hard_signals=[],
            soft_signals=[QuestionDetect({"enabled": True, "weight": 30, "patterns": ["?"]})],
            post_signals=[],
        )
        event = _group_event("你好吗？")
        assert evaluator.should_respond(event) is False

    def test_combined_soft_signals(self) -> None:
        # keyword (25) + question (30) = 55 >= 50
        evaluator = SignalEvaluator(
            mode="auto", threshold=50,
            hard_signals=[],
            soft_signals=[
                KeywordMatch({"enabled": True, "weight": 25, "triggers": ["原神"]}),
                QuestionDetect({"enabled": True, "weight": 30, "patterns": ["?"]}),
            ],
            post_signals=[],
        )
        event = _group_event("原神是什么?")
        assert evaluator.should_respond(event) is True

    def test_noise_pulls_below_threshold(self) -> None:
        # keyword (25) + noise (-50) = -25 < 50
        evaluator = SignalEvaluator(
            mode="auto", threshold=50,
            hard_signals=[],
            soft_signals=[
                KeywordMatch({"enabled": True, "weight": 25, "triggers": ["原神"]}),
                NoiseFilter({"enabled": True, "weight": -50, "min_length": 2}),
            ],
            post_signals=[],
        )
        event = _group_event("a")
        assert evaluator.should_respond(event) is False

    def test_private_scene_bypasses_in_chat_plugin(self) -> None:
        """SignalEvaluator is only called from ChatPlugin.handle(), which
        skips the gate for PRIVATE scenes. We verify the evaluator itself
        doesn't do scene filtering — that's the plugin's responsibility."""
        evaluator = create_evaluator(mode="auto", bot_user_id="123")
        event = make_event("hello", scene=Scene.PRIVATE)
        # evaluator itself doesn't know about scene; it would see no signals match
        assert evaluator.should_respond(event) is False


# ── create_evaluator factory ──

class TestCreateEvaluator:
    def test_auto_mode_with_bot_user_id(self) -> None:
        evaluator = create_evaluator(mode="auto", bot_user_id="123")
        assert evaluator._mode == "auto"
        assert len(evaluator._hard) == 2  # AtMention + ReplyToBot
        assert len(evaluator._soft) == 3  # KeywordMatch + QuestionDetect + NoiseFilter
        assert len(evaluator._post) == 1  # RandomPass

    def test_auto_mode_without_bot_user_id(self) -> None:
        evaluator = create_evaluator(mode="auto", bot_user_id="")
        assert evaluator._mode == "auto"
        assert len(evaluator._hard) == 0  # no hard signals without bot_user_id
        assert len(evaluator._soft) == 3
        assert len(evaluator._post) == 1

    def test_mention_mode_degrades_without_user_id(self) -> None:
        evaluator = create_evaluator(mode="mention", bot_user_id="")
        assert evaluator._mode == "all"  # degraded

    def test_unknown_mode_falls_back_to_auto(self) -> None:
        evaluator = create_evaluator(mode="unknown", bot_user_id="123")
        assert evaluator._mode == "auto"

    def test_negative_threshold_clamped(self) -> None:
        evaluator = SignalEvaluator(mode="auto", threshold=-10, hard_signals=[], soft_signals=[], post_signals=[])
        assert evaluator._threshold == 0

    def test_empty_triggers_disables_keyword(self) -> None:
        evaluator = create_evaluator(mode="auto", bot_user_id="123", signals={
            "keyword": {"triggers": []},
        })
        soft_sigs = [s for s in evaluator._soft if s.name == "keyword"]
        assert len(soft_sigs) == 0

    def test_custom_threshold(self) -> None:
        evaluator = create_evaluator(mode="auto", threshold=80, bot_user_id="123")
        assert evaluator._threshold == 80

    def test_custom_signal_config(self) -> None:
        evaluator = create_evaluator(mode="auto", bot_user_id="123", signals={
            "question": {"weight": 50, "patterns": ["?"]},
            "random": {"chance": 0.1},
        })
        # Verify custom configs are applied by checking behavior
        event = _group_event("你好?")
        assert evaluator.should_respond(event) is True  # 50 >= 50

    def test_random_force_pass(self) -> None:
        with patch("random.random", return_value=0.01):
            evaluator = create_evaluator(mode="auto", threshold=999, bot_user_id="123")
            event = _group_event("完全无关内容")
            assert evaluator.should_respond(event) is True  # random bypass

    def test_noise_filter_can_block(self) -> None:
        evaluator = create_evaluator(mode="auto", threshold=50, bot_user_id="123", signals={
            "keyword": {"triggers": ["原神"]},
        })
        event = _group_event("原")  # single char, noise filter hits
        assert evaluator.should_respond(event) is False
