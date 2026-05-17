import pytest

from app.llm.tracker import TokenUsageTracker
from app.storage import StorageProvider
from app.storage.memory import MemoryStorage


@pytest.mark.anyio
class TestTokenUsageTracker:
    @pytest.fixture
    def storage(self) -> MemoryStorage:
        return MemoryStorage()

    async def test_no_limits_always_has_capacity(self, storage: MemoryStorage) -> None:
        tracker = TokenUsageTracker(storage)
        assert await tracker.has_capacity() is True
        assert tracker.has_limits() is False

    async def test_daily_limit_blocks(self, storage: MemoryStorage) -> None:
        tracker = TokenUsageTracker(storage, max_per_day=100)
        assert tracker.has_limits() is True
        assert await tracker.has_capacity() is True

        await tracker.record(80)
        assert await tracker.has_capacity() is True

        await tracker.record(30)  # total 110 > 100
        assert await tracker.has_capacity() is False

    async def test_total_limit_blocks(self, storage: MemoryStorage) -> None:
        tracker = TokenUsageTracker(storage, max_total=200)
        assert await tracker.has_capacity() is True

        await tracker.record(150)
        assert await tracker.has_capacity() is True

        await tracker.record(60)  # total 210 > 200
        assert await tracker.has_capacity() is False

    async def test_daily_and_total_both_enforced(self, storage: MemoryStorage) -> None:
        tracker = TokenUsageTracker(storage, max_per_day=100, max_total=500)
        await tracker.record(90)
        assert await tracker.has_capacity() is True

        await tracker.record(20)  # daily 110 > 100, total 110 < 500
        assert await tracker.has_capacity() is False

    async def test_record_updates_counts(self, storage: MemoryStorage) -> None:
        tracker = TokenUsageTracker(storage)
        assert await tracker.daily_usage() == 0
        assert await tracker.total_usage() == 0

        await tracker.record(50)
        assert await tracker.daily_usage() == 50
        assert await tracker.total_usage() == 50

        await tracker.record(30)
        assert await tracker.daily_usage() == 80
        assert await tracker.total_usage() == 80

    async def test_has_limits(self, storage: MemoryStorage) -> None:
        assert TokenUsageTracker(storage).has_limits() is False
        assert TokenUsageTracker(storage, max_per_day=100).has_limits() is True
        assert TokenUsageTracker(storage, max_total=500).has_limits() is True
        assert TokenUsageTracker(storage, max_per_day=100, max_total=500).has_limits() is True
