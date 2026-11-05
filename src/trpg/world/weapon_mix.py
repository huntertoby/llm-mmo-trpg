"""主手掉落的武器大類（Phase 6T-1a；08 8.13 #135）。

- **每天 6 點**（換日，:func:`trpg.world.season_board.roll_season`）用前一天有動作的角色
  （:attr:`~trpg.world.state.DailyActivity.characters`）算一次全服的武器大類人數，存進世界狀態
  （:attr:`~trpg.world.state.WorldState.weapon_mix`）；重播時同樣的日誌算出同樣的比例。
- **掉主手時**（:func:`main_hand_class`）：野外一般戰鬥 500‰ 和主角同大類、精英 750‰；其餘依比例分給
  另外兩大類，兩類合計不到 ``min_sample`` 人（資料不足）時平均分。區域 Boss、懸賞一律同大類。

亂數由呼叫者給（掉落亂數的 ``fork``，不推進原本的串流，其他掉落和 6T-1a 以前一樣）；不讀時間。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final, Literal

from trpg.content.item_gen import WeaponClass
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_loot import MainHandMix
from trpg.shared.rng import Rng
from trpg.world.state import CharacterState, WeaponMix, WorldState

__all__ = [
    "WEAPON_CLASSES",
    "WEAPON_CLASS_ZH",
    "DropKind",
    "class_blocked",
    "hero_skills",
    "main_hand_class",
    "other_class_odds",
    "usable_skills",
    "weapon_class_of",
    "with_weapon_mix",
]

WEAPON_CLASSES: Final[tuple[WeaponClass, ...]] = ("focus", "melee", "ranged")
"""三大類（排序）。"""
WEAPON_CLASS_ZH: Final[Mapping[str, str]] = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}

type DropKind = Literal["field", "elite", "fixed"]
"""主手掉落的來源：野外一般戰鬥、有精英、固定同大類（區域 Boss、懸賞）。"""


def weapon_class_of(library: ContentLibrary, char: CharacterState) -> WeaponClass:
    """角色主手武器（目前裝備的）的大類；掉落判斷「同大類」也看這個（6T-1b）。"""
    return library.weapons[char.hero.weapon].weapon_class


def class_blocked(skill: SkillDef | None, weapon_class: str) -> bool:
    """技能的 ``weapon_req`` 是別大類（主手換成別大類後暫時不能用，6T-1b）；找不到定義時 ``False``
    （交給引擎照舊報錯）。"""
    return skill is not None and skill.weapon_req not in ("any", weapon_class)


def usable_skills(
    skill_ids: Iterable[str], defs: Mapping[str, SkillDef], weapon_class: str
) -> tuple[str, ...]:
    """開戰時放進技能列的技能（08 8.13 #135、6T-1b）：拿掉 ``weapon_req`` 是別大類的武器技（主手換成
    別大類時），順序不變；換回同大類就全部回來（技能本身一直留在角色身上）。``defs``：技能 ID →
    定義（含生成技能），查不到的原樣保留。"""
    return tuple(s for s in skill_ids if not class_blocked(defs.get(s), weapon_class))


def with_weapon_mix(world: WorldState, today: int) -> WorldState:
    """換日到 ``today`` 時算今天的比例（用 ``today - 1`` 的上線紀錄；已經算過就不變）。"""
    if world.weapon_mix is not None and world.weapon_mix.day == today:
        return world
    row = next((a for a in world.activity if a.day == today - 1), None)
    counts: dict[str, int] = {}
    for weapon_class in () if row is None else row.characters.values():
        counts[weapon_class] = counts.get(weapon_class, 0) + 1
    return world.model_copy(update={"weapon_mix": WeaponMix(day=today, counts=counts)})


def other_class_odds(
    rules: MainHandMix, mix: WeaponMix | None, hero_class: str
) -> dict[WeaponClass, int]:
    """另外兩大類各分到的權重（合計 > 0）：照比例；資料不足時各 1（平均）。"""
    others = [c for c in WEAPON_CLASSES if c != hero_class]
    counts = {} if mix is None else mix.counts
    weights = {c: counts.get(c, 0) for c in others}
    if sum(weights.values()) < rules.min_sample:
        return dict.fromkeys(others, 1)
    return weights


def main_hand_class(
    rules: MainHandMix | None,
    mix: WeaponMix | None,
    hero_class: WeaponClass,
    *,
    kind: DropKind,
    rng: Rng,
) -> WeaponClass:
    """這件主手的武器大類（見模組說明）。``rules`` 是 ``None``（沒有設定）時一律同大類。"""
    if rules is None or kind == "fixed":
        return hero_class
    same = rules.elite_same_permille if kind == "elite" else rules.same_permille
    if rng.randint(0, 999) < same:
        return hero_class
    weights = [(c, w) for c, w in other_class_odds(rules, mix, hero_class).items() if w > 0]
    roll = rng.randint(0, sum(w for _, w in weights) - 1)
    for weapon_class, weight in weights:
        if roll < weight:
            return weapon_class
        roll -= weight
    raise AssertionError("unreachable")


def hero_skills(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """主角開戰時的技能列（:func:`usable_skills`，含生成技能）。"""
    generated = {s.id: s for s in char.generated_skills}
    defs = {s: generated.get(s) or library.skills.get(s) for s in char.hero.skills}
    found = {k: v for k, v in defs.items() if v is not None}
    return usable_skills(char.hero.skills, found, weapon_class_of(library, char))
