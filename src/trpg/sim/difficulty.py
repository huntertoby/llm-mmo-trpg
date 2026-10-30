"""難度與法力旋鈕（平衡階段 BAL-4，``docs/phases/PhaseBAL計畫.md``）：只量不調。

六個旋鈕都以整數千分比（‰，1000 ＝ 現行）套用在記憶體內的 library 副本上，**不改 ``content/``、
預設行為不變**：

- 敵人 HP／Boss HP：單位範本的 ``max_hp``（四捨五入、至少 1；體質帶來的 HP 加成不縮放）。
  「Boss」＝ 有 ``boss`` 標籤的敵方範本（盜賊首領、盜賊頭目），其餘敵方（一輪與地圖的陣容與援軍，
  不含召喚物）為「敵人」。
- 敵人傷害／Boss 傷害：``CoreRules.enemy_damage_permille``／``boss_damage_permille``，由引擎的
  傷害結算乘上（只算敵方單位對我方的傷害，含技能與持續效果）。
- 技能法力費用：``CoreRules.ally_mana_cost_permille``；規則包內的技能（敵方陣容裝備的技能除外）
  的 ``cost.mana`` 依倍率縮放，之後 ``Ruleset.with_skills`` 加入的技能（一輪的生成技能）也套用。
- 法力上限：``ResourceRules.mana_cap_permille``，套用在依屬性算上限的角色（主角與 build 英雄；
  隊友與敵人用固定值，不縮放）。

這些欄位都是 ``exclude`` 的模擬旋鈕：不進序列化、也不進規則包雜湊，所以預設的紀錄與雜湊不變。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass

from trpg.content.library import ContentLibrary, scale_mana_cost
from trpg.content.maps import SpawnUnitsEvent
from trpg.engine.ids import BOSS_TAG

__all__ = ["NEUTRAL", "Difficulty", "enemy_roster", "with_difficulty"]

_PERMILLE = 1000


@dataclass(frozen=True, slots=True)
class Difficulty:
    """一組旋鈕（‰；1000 ＝ 現行行為）。"""

    enemy_hp: int = _PERMILLE
    enemy_damage: int = _PERMILLE
    boss_hp: int = _PERMILLE
    boss_damage: int = _PERMILLE
    mana_cost: int = _PERMILLE
    mana_cap: int = _PERMILLE

    @property
    def label(self) -> str:
        """只列出偏離 1000 的旋鈕；全預設為 ``baseline``。"""
        names = (
            ("敵HP", self.enemy_hp),
            ("敵傷", self.enemy_damage),
            ("BossHP", self.boss_hp),
            ("Boss傷", self.boss_damage),
            ("費用", self.mana_cost),
            ("法力上限", self.mana_cap),
        )
        parts = [f"{n}={v}" for n, v in names if v != _PERMILLE]
        return " ".join(parts) if parts else "baseline"


NEUTRAL = Difficulty()


def scale_int(value: int, permille: int) -> int:
    """``value × permille‰``，四捨五入（半數進位），整數運算。"""
    return (value * permille + _PERMILLE // 2) // _PERMILLE


def enemy_roster(library: ContentLibrary) -> tuple[str, ...]:
    """敵方範本 ID（排序）：一輪的遭遇與 Boss 陣容、地圖預設陣容與援軍事件；不含召喚物。"""
    ids: set[str] = set()
    rules = library.roguelite
    for step in rules.encounters:
        for option in step.options:
            ids.update(option)
    ids.update(rules.boss.enemies)
    for map_def in library.maps.values():
        if map_def.encounter is not None:
            ids.update(map_def.encounter.enemies)
        for event in map_def.events:
            if isinstance(event, SpawnUnitsEvent):
                ids.update(p.template for p in event.units)
    return tuple(sorted(i for i in ids if i in library.units and not library.units[i].summon))


def _scale_units(library: ContentLibrary, d: Difficulty, roster: Iterable[str]) -> dict:  # type: ignore[type-arg]
    units = dict(library.units)
    for template_id in roster:
        template = units[template_id]
        permille = d.boss_hp if BOSS_TAG in template.tags else d.enemy_hp
        if permille != _PERMILLE:
            units[template_id] = template.model_copy(
                update={"max_hp": max(1, scale_int(template.max_hp, permille))}
            )
    return units


def with_difficulty(library: ContentLibrary, d: Difficulty) -> ContentLibrary:
    """套用旋鈕的 library 副本（不動原物件，也不寫檔）；``d`` ＝ :data:`NEUTRAL` 時與原物件等價。"""
    if d == NEUTRAL:
        return library
    roster = enemy_roster(library)
    units = _scale_units(library, d, roster)
    ruleset = library.ruleset
    core = ruleset.core.model_copy(
        update={
            "enemy_damage_permille": d.enemy_damage,
            "boss_damage_permille": d.boss_damage,
            "ally_mana_cost_permille": d.mana_cost,
            "resources": ruleset.core.resources.model_copy(
                update={"mana_cap_permille": d.mana_cap}
            ),
        }
    )
    update: dict[str, object] = {"core": core}
    skills = library.skills
    if d.mana_cost != _PERMILLE:
        enemy_skills = {s for i in roster for s in units[i].skills}
        skills = {
            k: v if k in enemy_skills else scale_mana_cost(v, d.mana_cost)
            for k, v in library.skills.items()
        }
        table = ruleset.skills.model_copy(
            update={
                "skills": tuple(
                    s if s.id in enemy_skills else scale_mana_cost(s, d.mana_cost)
                    for s in ruleset.skills.skills
                )
            }
        )
        update["skills"] = table
    new_ruleset = ruleset.model_copy(update=update)
    new_ruleset.model_post_init(None)
    return dataclasses.replace(library, units=units, skills=skills, ruleset=new_ruleset)
