from pathlib import Path

from app.providers.staticdata import StaticDataProvider

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"


class TestStaticDataProvider:
    """Character data comes from in-code mapping — no JSON file needed.

    Boss data is still loaded from app/data/bosses.json.
    """

    def setup_method(self) -> None:
        self.provider = StaticDataProvider(DATA_DIR)
        # load() only loads bosses.json; characters are in-code
        self.provider.load()

    # ── character tests (mapping-based) ─────────────────────────

    def test_list_characters(self) -> None:
        chars = self.provider.list_characters()
        assert "胡桃" in chars
        assert "芙宁娜" in chars
        assert "神里绫华" in chars
        assert len(chars) > 80

    def test_search_character_exact(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert data.name == "胡桃"
        assert data.element == "火"
        assert data.weapon == "长柄武器"
        assert data.rarity == 5

    def test_search_character_alias(self) -> None:
        data = self.provider.search_character("hutao")
        assert data is not None
        assert data.name == "胡桃"

    def test_search_character_not_found(self) -> None:
        data = self.provider.search_character("不存在的角色")
        assert data is None

    def test_character_ascension_items(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert len(data.ascension_items) == 6
        assert data.ascension_items[0].level == "20→40"
        assert data.ascension_items[0].mora == 20000

    def test_character_ascension_includes_boss_mat(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        tier = data.ascension_items[1]  # 40→50
        assert tier.mora == 40000
        materials = tier.materials
        names = [m["name"] for m in materials]
        assert "常燃火种" in names  # boss mat inserted at index 1

    # ── skills & stats tests ────────────────────────────────────

    def test_character_has_skills(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert len(data.skills) >= 3
        names = [s.name for s in data.skills]
        assert "蝶引来生" in names
        assert "安神秘法" in names

    def test_character_skill_energy_and_cd(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        burst = next((s for s in data.skills if s.energy > 0), None)
        assert burst is not None
        assert burst.energy == 60
        assert burst.cd == 15

    def test_character_skill_description(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        e_skill = next((s for s in data.skills if s.name == "蝶引来生"), None)
        assert e_skill is not None
        assert len(e_skill.description) > 20

    def test_character_has_stats(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        s = data.stats
        assert s is not None
        assert s.hp_90 > 14000
        assert s.crit_rate == 5.0
        assert s.crit_dmg == 50.0
        assert s.er >= 100

    def test_character_stats_5star_vs_4star(self) -> None:
        hu_tao = self.provider.search_character("胡桃")
        bennett = self.provider.search_character("班尼特")
        assert hu_tao is not None and hu_tao.stats is not None
        assert bennett is not None and bennett.stats is not None
        # 5-star base HP should be higher than 4-star
        assert hu_tao.stats.hp_90 > bennett.stats.hp_90

    def test_character_stats_diff_element_same_rarity(self) -> None:
        diluc = self.provider.search_character("迪卢克")
        mona = self.provider.search_character("莫娜")
        assert diluc is not None and diluc.stats is not None
        assert mona is not None and mona.stats is not None
        # Both 5-star, dilution: reasonable sanity check
        assert diluc.stats.hp_90 > 10000
        assert mona.stats.hp_90 > 10000

    def test_character_has_passives(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert len(data.passives) >= 2
        names = [p.name for p in data.passives]
        assert "蝶隐之时" in names

    def test_skills_work_with_empty_data_dir(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            provider = StaticDataProvider(tmp)
            provider.load()
            data = provider.search_character("胡桃")
            assert data is not None
            assert len(data.skills) == 0  # no characters.json
            assert data.stats is None
            assert len(data.constellations) == 0

    def test_character_has_constellations(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert len(data.constellations) == 6
        assert data.constellations[0].name == "赤团开时斜飞去"
        assert len(data.constellations[0].description) > 10

    def test_character_talent_info(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert data.talent is not None
        assert data.talent.books_type == "繁荣"
        assert data.talent.domain == "太山府"
        assert "周日" in data.talent.schedule

    def test_character_talent_items(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        assert len(data.talent_items) == 8
        assert data.talent_items[0].mora == 12500

    def test_character_triple_crown(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        tc = data.talent_triple_crown
        assert tc.get("crown") == 3
        assert tc.get("mora") == sum(
            [12500, 17500, 25000, 30000, 37500, 45000, 55000, 65000]
        )

    def test_character_total_1_90(self) -> None:
        data = self.provider.search_character("胡桃")
        assert data is not None
        total = data.ascension_total_1_90
        assert total.get("mora") == sum(
            [20000, 40000, 60000, 80000, 100000, 120000]
        )

    def test_partial_match(self) -> None:
        data = self.provider.search_character("桃")
        assert data is not None
        assert data.name == "胡桃"

    # ── boss tests (JSON-based) ─────────────────────────────────

    def test_load_bosses(self) -> None:
        bosses = self.provider.list_bosses()
        assert "雷电将军" in bosses
        assert "无相之岩" in bosses
        assert len(bosses) >= 25

    def test_search_boss_exact(self) -> None:
        data = self.provider.search_boss("雷电将军")
        assert data is not None
        assert data["name"] == "雷电将军"
        assert data["type"] == "周本"

    def test_search_boss_alias(self) -> None:
        data = self.provider.search_boss("雷神")
        assert data is not None
        assert data["name"] == "雷电将军"

    def test_search_boss_not_found(self) -> None:
        data = self.provider.search_boss("不存在的BOSS")
        assert data is None

    def test_boss_resistances(self) -> None:
        data = self.provider.search_boss("雷电将军")
        assert data is not None
        res = data.get("resistances", {})
        assert res.get("雷") == 0.7
        assert res.get("物理") == 0.1

    def test_boss_drops(self) -> None:
        data = self.provider.search_boss("雷电将军")
        assert data is not None
        assert "凶将之手眼" in data.get("drops", [])

    # ── edge cases ──────────────────────────────────────────────

    def test_empty_data_dir_bosses(self) -> None:
        """Boss search should return None when bosses.json is missing."""
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            provider = StaticDataProvider(tmp)
            provider.load()
            assert provider.list_bosses() == []
            assert provider.search_boss("雷电将军") is None

    def test_character_still_works_with_empty_data_dir(self) -> None:
        """Characters are from in-code mapping, so they work without any data dir."""
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            provider = StaticDataProvider(tmp)
            # no load() needed for characters
            data = provider.search_character("胡桃")
            assert data is not None
            assert data.name == "胡桃"
