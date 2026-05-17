from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AscensionTier:
    level: str
    mora: int
    materials: list[dict] = field(default_factory=list)


@dataclass
class TalentInfo:
    books_type: str
    domain: str
    schedule: list[str] = field(default_factory=list)


@dataclass
class TalentTier:
    level: str
    mora: int
    materials: list[dict] = field(default_factory=list)


@dataclass
class ConstellationInfo:
    name: str
    description: str


@dataclass
class SkillInfo:
    name: str
    description: str
    cd: int = 0
    energy: int = 0
    stamina: int = 0


@dataclass
class PassiveInfo:
    name: str
    description: str
    unlock: str = ""


@dataclass
class CharacterStats:
    hp_90: float = 0
    atk_90: float = 0
    def_90: float = 0
    crit_rate: float = 0
    crit_dmg: float = 0
    er: float = 0


@dataclass
class CharacterData:
    name: str
    rarity: int
    element: str
    weapon: str
    ascension_items: list[AscensionTier] = field(default_factory=list)
    ascension_total_1_90: dict = field(default_factory=dict)
    talent: TalentInfo | None = None
    talent_items: list[TalentTier] = field(default_factory=list)
    talent_triple_crown: dict = field(default_factory=dict)
    skills: list[SkillInfo] = field(default_factory=list)
    passives: list[PassiveInfo] = field(default_factory=list)
    constellations: list[ConstellationInfo] = field(default_factory=list)
    stats: CharacterStats | None = None


@dataclass
class BossData:
    name: str
    type: str
    location: str
    element: str
    resistances: dict[str, float] = field(default_factory=dict)
    drops: list[str] = field(default_factory=list)
    mechanics: str = ""
    tips: str = ""
