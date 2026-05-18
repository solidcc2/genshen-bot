from __future__ import annotations

from typing import TYPE_CHECKING

from app.event_model import NormalizedEvent
from app.llm.models import LLMMessage
from app.plugin import PluginRegistry
from app.session import Session

if TYPE_CHECKING:
    from app.chat_log import ChatLogStore


class ContextBuilder:
    def __init__(
        self,
        persona: str,
        plugin_registry: PluginRegistry,
        chat_log: ChatLogStore | None = None,
        context_limit: int = 20,
    ) -> None:
        self._persona = persona
        self._registry = plugin_registry
        self._chat_log = chat_log
        self._context_limit = context_limit

    async def build(self, session: Session, event: NormalizedEvent) -> list[LLMMessage]:
        messages: list[LLMMessage] = []

        # Layer 0: 人设
        messages.append(LLMMessage(role="system", content=self._persona))

        # Layer 1: 技能声明（自动从 PluginRegistry 聚合）
        skills = self._registry.get_help_entries()
        if skills:
            skill_lines = ["可用命令："]
            for s in skills:
                skill_lines.append(f"{s.command} — {s.description}")
            messages.append(LLMMessage(role="system", content="\n".join(skill_lines)))

        # Layer 2: 近期群聊环境消息（按游标过滤 + limit 控制）
        if self._chat_log:
            cursor_msg_id = session.state.get("llm_context_since_msg")
            recent = await self._chat_log.get_recent(
                event.chat_id, limit=self._context_limit, cursor_msg_id=cursor_msg_id
            )
            if recent:
                log_lines = ["近期群聊记录："]
                for entry in reversed(recent):
                    log_lines.append(f"[{entry.user_id}]: {entry.text}")
                messages.append(LLMMessage(role="system", content="\n".join(log_lines)))

        # Layer 3: 会话历史
        for msg in session.messages:
            messages.append(LLMMessage(role=msg.role, content=msg.text))  # type: ignore[arg-type]

        # Layer 4: 当前输入
        messages.append(LLMMessage(role="user", content=event.text))

        return messages
