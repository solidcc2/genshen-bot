from __future__ import annotations

from app.event_model import NormalizedEvent
from app.plugin import BotPlugin, PluginContext, PluginHelp, PluginResult
from app.providers.staticdata import StaticDataProvider
from app.providers.staticdata.models import CharacterData


class DataPlugin(BotPlugin):
    command = ""

    def __init__(self, provider: StaticDataProvider) -> None:
        self._provider = provider

    @staticmethod
    def _match_prefix(text: str, cmd: str) -> bool:
        return text == cmd or text.startswith(cmd + " ")

    def match(self, event: NormalizedEvent) -> bool:
        text = event.text.strip()
        return self._match_prefix(text, "/char") or self._match_prefix(text, "/boss")

    async def handle(self, ctx: PluginContext) -> PluginResult:
        text = ctx.event.text.strip()

        if self._match_prefix(text, "/char"):
            query = text[5:].strip()
            return await self._handle_char(query)
        elif self._match_prefix(text, "/boss"):
            query = text[5:].strip()
            return await self._handle_boss(query)

        return PluginResult(text="用法：/char <角色名> 或 /boss <BOSS名>")

    async def _handle_char(self, query: str) -> PluginResult:
        if not query:
            return PluginResult(text="请指定角色名，例如：/char 胡桃")

        data = self._provider.search_character(query)
        if data is None:
            return PluginResult(text=f"未找到角色「{query}」，试试 /char 胡桃")

        lines = [
            f"✦ {data.name} ({data.element} · {data.weapon} · {'⭐' * data.rarity})",
            "",
        ]

        # ── stats ──
        if data.stats:
            s = data.stats
            lines.append("──基础属性(Lv.90)──")
            lines.append(
                f"  HP {s.hp_90:.0f}  ATK {s.atk_90:.0f}  DEF {s.def_90:.0f}"
            )
            lines.append(
                f"  暴击 {s.crit_rate}%  暴伤 {s.crit_dmg}%  充能 {s.er}%"
            )
            lines.append("")

        # ── skills ──
        if data.skills:
            lines.append("──技能──")
            for sk in data.skills:
                parts = [f"  {sk.name}"]
                extras = []
                if sk.energy:
                    extras.append(f"能量{sk.energy}")
                if sk.cd:
                    extras.append(f"CD{sk.cd}s")
                if extras:
                    parts[-1] += f" ({', '.join(extras)})"
                if sk.description:
                    parts.append(f"    {sk.description}")
                lines.extend(parts)
            lines.append("")

        # ── passives ──
        if data.passives:
            lines.append("──天赋──")
            for p in data.passives:
                parts = [f"  {p.name}"]
                if p.unlock:
                    parts[-1] += f" ({p.unlock})"
                if p.description:
                    parts.append(f"    {p.description}")
                lines.extend(parts)
            lines.append("")

        # ── constellations ──
        if data.constellations:
            lines.append("──命座──")
            for i, c in enumerate(data.constellations, 1):
                clines = [f"  C{i} {c.name}"]
                if c.description:
                    clines.append(f"    {c.description}")
                lines.extend(clines)
            lines.append("")

        # ── ascension materials (one line per tier) ──
        if data.ascension_items:
            lines.append("──突破材料──")
            for tier in data.ascension_items:
                mats = "  ".join(f"{m['name']}×{m['count']}" for m in tier.materials)
                lines.append(f"  {tier.level}  {tier.mora:,}  {mats}")
            if data.ascension_total_1_90:
                t = data.ascension_total_1_90
                total_mats = "  ".join(f"{m['name']}×{m['count']}" for m in t.get("materials", []))
                lines.append(f"  1-90  {t.get('mora', 0):,}  {total_mats}")

        # ── talent materials (one line per tier) ──
        if data.talent:
            t = data.talent
            sched = f"  {'/'.join(t.schedule)}" if t.schedule else ""
            lines.append(f"\n──天赋材料({t.books_type})──{sched}")
            for tier in data.talent_items:
                mats = "  ".join(f"{m['name']}×{m['count']}" for m in tier.materials)
                lines.append(f"  {tier.level}  {tier.mora:,}  {mats}")
            if data.talent_triple_crown:
                tc = data.talent_triple_crown
                book_parts = [f"{k}×{v}" for k, v in tc.get("books", {}).items()]
                weekly_parts = [f"{k}×{v}" for k, v in tc.get("weekly", {}).items()]
                crown = tc.get("crown", 0)
                extra = "  ".join(book_parts + weekly_parts)
                if crown:
                    extra += f"  智识之冕×{crown}"
                lines.append(f"  三皇冠  {tc.get('mora', 0):,}  {extra}")

        return PluginResult(text="\n".join(lines))

    async def _handle_boss(self, query: str) -> PluginResult:
        if not query:
            return PluginResult(text="请指定 BOSS 名称，例如：/boss 雷电将军")

        data = self._provider.search_boss(query)
        if data is None:
            return PluginResult(text=f"未找到 BOSS「{query}」")

        lines = [
            f"✦ {data['name']} ({data.get('type', '')})",
            f"  位置: {data.get('location', '')}",
            f"  元素: {data.get('element', '')}",
        ]

        res = data.get("resistances", {})
        if res:
            lines.append("  抗性:")
            res_list = sorted(res.items(), key=lambda x: -x[1])
            for elem, val in res_list:
                icon = "⬛" if val >= 0.7 else "🟦" if val >= 0.3 else "⬜"
                lines.append(f"    {icon} {elem} {val * 100:.0f}%")

        drops = data.get("drops", [])
        if drops:
            lines.append(f"  掉落: {'/'.join(drops)}")

        if data.get("mechanics"):
            lines.append(f"\n  机制: {data['mechanics']}")
        if data.get("tips"):
            lines.append(f"  技巧: {data['tips']}")

        return PluginResult(text="\n".join(lines))

    def help(self) -> PluginHelp:
        return PluginHelp(
            command="/char <角色名> 或 /boss <BOSS名>",
            description="查询角色养成材料 / BOSS 属性、抗性与掉落",
            usage="/char 胡桃 — 突破+天赋材料总汇\n/boss 雷电将军 — 抗性+掉落+打法",
            category="原神",
        )
