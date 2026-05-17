import pytest

from app.plugin import PluginContext, PluginResult
from app.plugins.staticdata import DataPlugin
from app.providers.staticdata import StaticDataProvider
from tests.conftest import FakeSender, make_event

DATA_DIR = None


@pytest.fixture(scope="module")
def provider() -> StaticDataProvider:
    from pathlib import Path

    d = Path(__file__).resolve().parents[1] / "app" / "data"
    p = StaticDataProvider(d)
    p.load()
    return p


@pytest.fixture
def plugin(provider: StaticDataProvider) -> DataPlugin:
    return DataPlugin(provider)


class TestDataPluginMatch:
    def test_matches_char(self, plugin: DataPlugin) -> None:
        assert plugin.match(make_event("/char 胡桃")) is True

    def test_matches_boss(self, plugin: DataPlugin) -> None:
        assert plugin.match(make_event("/boss 雷电将军")) is True

    def test_does_not_match_plain_text(self, plugin: DataPlugin) -> None:
        assert plugin.match(make_event("你好")) is False

    def test_does_not_match_other_command(self, plugin: DataPlugin) -> None:
        assert plugin.match(make_event("/help")) is False

    def test_does_not_match_similar_prefix(self, plugin: DataPlugin) -> None:
        assert plugin.match(make_event("/chart")) is False
        assert plugin.match(make_event("/bosses")) is False


class TestDataPluginHandle:
    @pytest.mark.anyio
    async def test_char_returns_materials(self, plugin: DataPlugin) -> None:
        event = make_event("/char 胡桃")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert result.text is not None
        assert "胡桃" in result.text
        assert "火" in result.text
        assert "20→40" in result.text
        assert "繁荣" in result.text
        assert "三皇冠" in result.text
        assert "基础属性" in result.text
        assert "技能" in result.text
        assert "HP" in result.text
        assert "蝶引来生" in result.text
        assert "天赋" in result.text
        assert "蝶隐之时" in result.text
        assert "命座" in result.text
        assert "C1" in result.text
        assert "赤团开时斜飞去" in result.text

    @pytest.mark.anyio
    async def test_char_not_found(self, plugin: DataPlugin) -> None:
        event = make_event("/char 不存在的角色")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert "未找到" in (result.text or "")

    @pytest.mark.anyio
    async def test_char_no_query(self, plugin: DataPlugin) -> None:
        event = make_event("/char")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert "请指定" in (result.text or "")

    @pytest.mark.anyio
    async def test_boss_returns_info(self, plugin: DataPlugin) -> None:
        event = make_event("/boss 雷电将军")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert result.text is not None
        assert "雷电将军" in result.text
        assert "周本" in result.text
        assert "抗性" in result.text
        assert "70%" in result.text  # 雷抗

    @pytest.mark.anyio
    async def test_boss_not_found(self, plugin: DataPlugin) -> None:
        event = make_event("/boss 不存在的BOSS")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert "未找到" in (result.text or "")

    @pytest.mark.anyio
    async def test_boss_no_query(self, plugin: DataPlugin) -> None:
        event = make_event("/boss")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert "请指定" in (result.text or "")

    @pytest.mark.anyio
    async def test_char_uses_alias(self, plugin: DataPlugin) -> None:
        event = make_event("/char hutao")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert result.text is not None
        assert "胡桃" in result.text

    @pytest.mark.anyio
    async def test_boss_uses_alias(self, plugin: DataPlugin) -> None:
        event = make_event("/boss 雷神")
        ctx = PluginContext(event=event, sender=FakeSender())
        result = await plugin.handle(ctx)
        assert result.text is not None
        assert "雷电将军" in result.text

    @pytest.mark.anyio
    async def test_help(self, plugin: DataPlugin) -> None:
        help_data = plugin.help()
        assert help_data is not None
        assert "/char" in help_data.command
        assert "养成材料" in help_data.description
        assert help_data.category == "原神"
