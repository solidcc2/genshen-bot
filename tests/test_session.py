from __future__ import annotations

import pytest

from app.session import Session, SessionManager
from app.storage.memory import MemoryStorage


@pytest.fixture
def manager():
    storage = MemoryStorage()
    return SessionManager(storage)


class TestSession:
    def test_default_values(self) -> None:
        s = Session(chat_id="chat_001")
        assert s.chat_id == "chat_001"
        assert s.state == {}
        assert s.created_at is not None
        assert s.updated_at is not None


class TestSessionManager:
    @pytest.mark.anyio
    async def test_get_or_create_new(self, manager) -> None:
        session = await manager.get_or_create("new_chat")
        assert session.chat_id == "new_chat"
        assert session.state == {}

    @pytest.mark.anyio
    async def test_set_and_get_state(self, manager) -> None:
        await manager.set_state("chat_001", "scene", "combat")
        val = await manager.get_state("chat_001", "scene")
        assert val == "combat"

    @pytest.mark.anyio
    async def test_get_state_missing_key(self, manager) -> None:
        val = await manager.get_state("chat_001", "nonexistent")
        assert val is None

    @pytest.mark.anyio
    async def test_state_isolated_per_chat(self, manager) -> None:
        await manager.set_state("chat_001", "step", 1)
        await manager.set_state("chat_002", "step", 99)

        assert await manager.get_state("chat_001", "step") == 1
        assert await manager.get_state("chat_002", "step") == 99

    @pytest.mark.anyio
    async def test_state_updates_updated_at(self, manager) -> None:
        session1 = await manager.get_or_create("chat_001")
        old_updated = session1.updated_at

        await manager.set_state("chat_001", "key", "val")
        session2 = await manager.get_or_create("chat_001")
        assert session2.updated_at >= old_updated

    @pytest.mark.anyio
    async def test_save_roundtrip(self, manager) -> None:
        session = await manager.get_or_create("chat_001")
        session.state["cursor"] = "msg_123"
        await manager.save(session)

        loaded = await manager.get_or_create("chat_001")
        assert loaded.state["cursor"] == "msg_123"

    @pytest.mark.anyio
    async def test_multiple_state_keys(self, manager) -> None:
        await manager.set_state("chat_001", "a", 1)
        await manager.set_state("chat_001", "b", 2)
        assert await manager.get_state("chat_001", "a") == 1
        assert await manager.get_state("chat_001", "b") == 2

    @pytest.mark.anyio
    async def test_get_or_create_existing(self, manager) -> None:
        session = await manager.get_or_create("chat_001")
        session.state["key"] = "value"
        await manager.save(session)

        loaded = await manager.get_or_create("chat_001")
        assert loaded.state["key"] == "value"
