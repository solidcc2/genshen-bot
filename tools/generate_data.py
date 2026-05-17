#!/usr/bin/env python3
"""Generate app/data/characters.json from Dimbreath/AnimeGameData (GitLab).

Fetches raw game data, extracts character skills and stats, and outputs
curated JSON for the bot's StaticDataProvider to load at runtime.

Usage:  python tools/generate_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"
GITLAB_RAW = "https://gitlab.com/Dimbreath/AnimeGameData/-/raw/master"

# Map game icon-name suffixes to our Chinese character names.
# iconName format: "UI_AvatarIcon_{SUFFIX}"
ICON_TO_CHINESE: dict[str, str] = {
    "Hutao": "胡桃",
    "Qin": "琴",
    "Ayaka": "神里绫华",
    "Shougun": "雷电将军",
    "Kazuha": "枫原万叶",
    "Kokomi": "珊瑚宫心海",
    "Itto": "荒泷一斗",
    "Ayato": "神里绫人",
    "Yoimiya": "宵宫",
    "Yae": "八重神子",
    "Heizo": "鹿野院平藏",
    "Shinobu": "久岐忍",
    "Sara": "九条裟罗",
    "Gorou": "五郎",
    "Tohma": "托马",
    "Sayu": "早柚",
    "Mona": "莫娜",
    "Albedo": "阿贝多",
    "Eula": "优菈",
    "Klee": "可莉",
    "Diluc": "迪卢克",
    "Venti": "温迪",
    "Qiqi": "七七",
    "Ambor": "安柏",
    "Kaeya": "凯亚",
    "Lisa": "丽莎",
    "Razor": "雷泽",
    "Barbara": "芭芭拉",
    "Sucrose": "砂糖",
    "Bennett": "班尼特",
    "Xiangling": "香菱",
    "Fischl": "菲谢尔",
    "Noel": "诺艾尔",
    "Chongyun": "重云",
    "Diona": "迪奥娜",
    "Xinyan": "辛焱",
    "Rosaria": "罗莎莉亚",
    "Ganyu": "甘雨",
    "Xiao": "魈",
    "Zhongli": "钟离",
    "Keqing": "刻晴",
    "Shenhe": "申鹤",
    "Yelan": "夜兰",
    "Baizhuer": "白术",
    "Liuyun": "闲云",
    "Xingqiu": "行秋",
    "Beidou": "北斗",
    "Ningguang": "凝光",
    "Feiyan": "烟绯",
    "Yunjin": "云堇",
    "Yaoyao": "瑶瑶",
    "Gaming": "嘉明",
    "Nahida": "纳西妲",
    "Nilou": "妮露",
    "Cyno": "赛诺",
    "Alhatham": "艾尔海森",
    "Tighnari": "提纳里",
    "Dehya": "迪希雅",
    "Wanderer": "流浪者",
    "Collei": "柯莱",
    "Dori": "多莉",
    "Faruzan": "珐露珊",
    "Layla": "莱依拉",
    "Kaveh": "卡维",
    "Candace": "坎蒂丝",
    "Momoka": "绮良良",
    "Furina": "芙宁娜",
    "Neuvillette": "那维莱特",
    "Navia": "娜维娅",
    "Clorinde": "克洛琳德",
    "Sigewinne": "希格雯",
    "Arlecchino": "阿蕾奇诺",
    "Wriothesley": "莱欧斯利",
    "Liney": "林尼",
    "Emilie": "艾梅莉埃",
    "Linette": "琳妮特",
    "Freminet": "菲米尼",
    "Charlotte": "夏洛蒂",
    "Chevreuse": "夏沃蕾",
    "Mavuika": "玛薇卡",
    "Citlali": "茜特菈莉",
    "Xilonen": "希诺宁",
    "Kinich": "基尼奇",
    "Mualani": "玛拉妮",
    "Chasca": "恰斯卡",
    "Kachina": "卡齐娜",
    "Iansan": "伊安珊",
    "Lanyan": "蓝砚",
    "Olorun": "欧洛伦",
    "Chiori": "千织",
    "Mika": "米卡",
    "Sethos": "赛索斯",
}


def _fetch(url: str) -> list | dict:
    resp = httpx.get(url, follow_redirects=True, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _get_skill_data(
    skills_list: list[dict],
    textmap: dict[str, str],
    skill_ids: list[int],
) -> list[dict]:
    """Build skill info for given skill IDs."""
    skills_map = {s["id"]: s for s in skills_list}
    result: list[dict] = []
    for sid in skill_ids:
        s = skills_map.get(sid)
        if s is None:
            continue
        name = textmap.get(str(s.get("nameTextMapHash", 0)), "")
        desc = textmap.get(str(s.get("descTextMapHash", 0)), "")
        result.append({
            "id": sid,
            "name": name,
            "desc": _truncate_desc(desc),
            "cd": s.get("cdTime", 0),
            "cost": s.get("costElemVal", 0),
            "cost_type": s.get("costElemType"),
            "stamina": s.get("costStamina", 0),
            "max_charge": s.get("maxChargeNum", 1),
        })
    return result


def _truncate_desc(desc: str, max_len: int = 200) -> str:
    if len(desc) <= max_len:
        return desc
    for sep in "。！？\n":
        idx = desc.rfind(sep, 0, max_len)
        if idx > 0:
            return desc[: idx + 1]
    return desc[:max_len] + "…"


def _calc_stat(
    base_val: float,
    curve_type: str,
    target_level: int,
    curves: dict[tuple[str, int], float],
    promote_bonus: float,
) -> float:
    mult = curves.get((curve_type, target_level), 1.0)
    return round(base_val * mult + promote_bonus, 1)


def main() -> None:
    print("Fetching data from GitLab…")

    textmap_full: dict[str, str] = _fetch(
        f"{GITLAB_RAW}/TextMap/TextMap_MediumCHS.json"
    )
    # Fallback for entries not in Medium
    textmap_fb: dict[str, str] = _fetch(
        f"{GITLAB_RAW}/TextMap/TextMapCHS.json"
    )
    textmap: dict[str, str] = {**textmap_fb, **textmap_full}
    print(f"  TextMap_Medium entries: {len(textmap_full)}")
    print(f"  TextMap_CHS entries: {len(textmap_fb)}")
    print(f"  Merged total: {len(textmap)}")

    avatars: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/AvatarExcelConfigData.json"
    )
    print(f"  Avatars: {len(avatars)} entries")

    depots: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/AvatarSkillDepotExcelConfigData.json"
    )
    print(f"  SkillDepots: {len(depots)}")

    skills_list: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/AvatarSkillExcelConfigData.json"
    )
    print(f"  Skills: {len(skills_list)}")

    promotes: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/AvatarPromoteExcelConfigData.json"
    )
    print(f"  Promotes: {len(promotes)}")

    curves_data: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/AvatarCurveExcelConfigData.json"
    )
    curves: dict[tuple[str, int], float] = {}
    for entry in curves_data:
        lvl = entry["level"]
        for ci in entry["curveInfos"]:
            curves[(ci["type"], lvl)] = ci["value"]
    print(f"  Curves: {len(curves_data)} entries, {len(curves)} (type,level) pairs")

    talents_data: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/AvatarTalentExcelConfigData.json"
    )
    talents_map: dict[int, dict] = {t["talentId"]: t for t in talents_data}
    print(f"  Talents (constellations): {len(talents_data)} entries")

    proud_data: list[dict] = _fetch(
        f"{GITLAB_RAW}/ExcelBinOutput/ProudSkillExcelConfigData.json"
    )
    # Build proud group → {name, desc} lookup (level 1 = base)
    proud_map: dict[int, dict[str, str]] = {}
    for p in proud_data:
        gid = p.get("proudSkillGroupId")
        lv = p.get("level")
        if gid and lv == 1:
            name = textmap.get(str(p.get("nameTextMapHash", 0)), "")
            desc = textmap.get(str(p.get("descTextMapHash", 0)), "")
            proud_map[gid] = {"name": name, "desc": desc}
    print(f"  ProudSkill: {len(proud_data)} entries, {len(proud_map)} groups")

    # Build character name → avatar ID map via iconName
    playable_ids: set[int] = set()
    # Filter for actual playable characters (formal use type)
    for a in avatars:
        use_type = a.get("useType", "")
        if use_type in ("AVATAR_FORMAL",):
            playable_ids.add(a["id"])

    name_to_id: dict[str, int] = {}
    for a in sorted(avatars, key=lambda x: x["id"]):
        icon = a.get("iconName", "")
        suffix = icon.replace("UI_AvatarIcon_", "")
        ch_name = ICON_TO_CHINESE.get(suffix)
        if ch_name and a["id"] in playable_ids and ch_name not in name_to_id:
            name_to_id[ch_name] = a["id"]

    unmapped = set(ICON_TO_CHINESE.values()) - set(name_to_id.keys())
    if unmapped:
        print(f"\n  ⚠ Unmapped characters in icon table: {sorted(unmapped)}")
    else:
        print(f"\n  All {len(name_to_id)} characters mapped via icon names")

    # Build lookup maps
    avatar_by_id = {a["id"]: a for a in avatars}
    depot_by_id = {d["id"]: d for d in depots}

    # Promote lookup: (promoteId, promoteLevel) → {propType: value}
    promote_map: dict[tuple[int, int], dict[str, float]] = {}
    for p in promotes:
        pid = p.get("avatarPromoteId")
        plevel = p.get("promoteLevel")
        props = {}
        for prop in p.get("addProps", []):
            if isinstance(prop, dict) and prop.get("value", 0) > 0:
                props[prop["propType"]] = prop["value"]
        promote_map[(pid, plevel)] = props

    # Curve type selection (5-star vs 4-star)
    CURVE_SETS = {
        5: {
            "FIGHT_PROP_BASE_HP": "GROW_CURVE_HP_S5",
            "FIGHT_PROP_BASE_ATTACK": "GROW_CURVE_ATTACK_S5",
            "FIGHT_PROP_BASE_DEFENSE": "GROW_CURVE_HP_S5",
        },
        4: {
            "FIGHT_PROP_BASE_HP": "GROW_CURVE_HP_S4",
            "FIGHT_PROP_BASE_ATTACK": "GROW_CURVE_ATTACK_S4",
            "FIGHT_PROP_BASE_DEFENSE": "GROW_CURVE_HP_S4",
        },
    }

    # Generate per-character data
    output: dict[str, dict] = {}

    for ch_name, avatar_id in name_to_id.items():
        av = avatar_by_id.get(avatar_id)
        if av is None:
            continue

        rarity = 5 if av.get("qualityType") == "QUALITY_ORANGE" else 4
        curve_map = CURVE_SETS.get(rarity, CURVE_SETS[4])

        # Base stats at level 1
        hp_base = av.get("hpBase", 0)
        atk_base = av.get("attackBase", 0)
        def_base = av.get("defenseBase", 0)

        # Promote bonuses at max ascension (level 6)
        promote_id = av.get("avatarPromoteId", 0)
        promote_lv6 = promote_map.get((promote_id, 6), {})

        hp_promote = promote_lv6.get("FIGHT_PROP_BASE_HP", 0)
        atk_promote = promote_lv6.get("FIGHT_PROP_BASE_ATTACK", 0)
        def_promote = promote_lv6.get("FIGHT_PROP_BASE_DEFENSE", 0)

        # Determine actual growth curve types per stat (from per-character data)
        grow_curves = {}
        for gc in av.get("propGrowCurves", []):
            grow_curves[gc["type"]] = gc["growCurve"]

        hp_curve = grow_curves.get(
            "FIGHT_PROP_BASE_HP", curve_map["FIGHT_PROP_BASE_HP"]
        )
        atk_curve = grow_curves.get(
            "FIGHT_PROP_BASE_ATTACK", curve_map["FIGHT_PROP_BASE_ATTACK"]
        )
        def_curve = grow_curves.get(
            "FIGHT_PROP_BASE_DEFENSE", curve_map["FIGHT_PROP_BASE_DEFENSE"]
        )

        # Ascension stat bonus (type like CRIT/CRIT_DMG) – extract from promote 2+
        asc_bonus_type: str | None = None
        asc_bonus_value: float = 0.0
        for plevel in range(2, 7):
            pdata = promote_map.get((promote_id, plevel), {})
            for k, v in pdata.items():
                if k not in (
                    "FIGHT_PROP_BASE_HP",
                    "FIGHT_PROP_BASE_ATTACK",
                    "FIGHT_PROP_BASE_DEFENSE",
                ):
                    asc_bonus_type = k
                    asc_bonus_value = v
                    break
            if asc_bonus_type:
                break

        stats = {
            "hp_base": hp_base,
            "atk_base": atk_base,
            "def_base": def_base,
            "crit_rate": round(av.get("critical", 0) * 100, 1),
            "crit_dmg": round(av.get("criticalHurt", 0) * 100, 1),
            "er": round(av.get("chargeEfficiency", 1.0) * 100, 1),
            "hp_90": _calc_stat(hp_base, hp_curve, 90, curves, hp_promote),
            "atk_90": _calc_stat(atk_base, atk_curve, 90, curves, atk_promote),
            "def_90": _calc_stat(def_base, def_curve, 90, curves, def_promote),
        }

        # Skills via skill depot
        depot_id = av.get("skillDepotId", 0)
        depot = depot_by_id.get(depot_id)

        skills: list[dict] = []
        if depot:
            skill_ids = [s for s in depot.get("skills", []) if s and s > 0]
            energy_skill = depot.get("energySkill", 0)
            if energy_skill and energy_skill not in skill_ids:
                skill_ids.append(energy_skill)
            skills = _get_skill_data(skills_list, textmap, skill_ids)

        # Passive talents
        passives: list[dict] = []
        if depot:
            for entry in depot.get("inherentProudSkillOpens", []):
                group_id = entry.get("proudSkillGroupId", 0)
                if group_id == 0:
                    continue
                promote_lvl = entry.get("needAvatarPromoteLevel", 0)
                unlock_map = {0: "初始", 1: "突破1", 4: "突破4"}
                info = proud_map.get(group_id, {})
                passives.append({
                    "name": info.get("name", ""),
                    "desc": info.get("desc", ""),
                    "unlock": unlock_map.get(promote_lvl, f"突破{promote_lvl}"),
                })

        # Constellations via depot talent IDs
        constellations: list[dict] = []
        if depot:
            talent_ids = [t for t in depot.get("talents", []) if t]
            for tid in talent_ids:
                tal = talents_map.get(tid)
                if tal is None:
                    continue
                c_name = textmap.get(str(tal.get("nameTextMapHash", 0)), "")
                c_desc = textmap.get(str(tal.get("descTextMapHash", 0)), "")
                constellations.append({
                    "name": c_name,
                    "desc": c_desc,
                })

        output[ch_name] = {
            "stats": stats,
            "skills": skills,
            "passives": passives,
            "constellations": constellations,
            "asc_bonus": {
                "type": asc_bonus_type or "",
                "value": asc_bonus_value,
            },
        }

    # ── Write output ──
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "characters.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nWritten {len(output)} characters to {out_path}")

    with_skills = sum(
        1 for v in output.values() if isinstance(v, dict) and v.get("skills")
    )
    with_stats = sum(
        1 for v in output.values() if isinstance(v, dict) and v.get("stats")
    )
    n_empty = sum(
        1
        for v in output.values()
        if isinstance(v, dict) and not v.get("skills") and not v.get("stats")
    )
    n_skills_with_names = sum(
        1
        for v in output.values()
        if isinstance(v, dict)
        and any(s.get("name") for s in v.get("skills", []))
    )
    print(f"  Characters with skills: {with_skills}")
    print(f"  Characters with stats: {with_stats}")
    print(f"  Skills with non-empty names: {n_skills_with_names}")
    with_const = sum(
        1 for v in output.values() if isinstance(v, dict) and v.get("constellations")
    )
    total_const = sum(
        len(v.get("constellations", []))
        for v in output.values()
        if isinstance(v, dict)
    )
    print(f"  Characters with constellations: {with_const} (total {total_const})")
    print(f"  Empty/errored: {n_empty}")


if __name__ == "__main__":
    main()
