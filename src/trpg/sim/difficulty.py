"""難度與法力旋鈕（平衡階段 BAL-4／BAL-4b，``docs/phases/PhaseBAL計畫.md``）：模擬用的覆寫工具。

BAL-4b 起，採用的數值（敵人 HP ×1.2、敵人與護衛傷害 ×1.2、我方技能法力費用 ×0.8、法力上限 ×1.4）
已寫進 ``content/``（單位範本 ``max_hp``、``rules/core.yaml``）。這裡的旋鈕都是
**在 content 值上再乘**的整數千分比
（‰，1000 ＝ 不再調整 ＝ content 現況），套用在記憶體內的 library 副本上，不寫檔：

- 敵人 HP／Boss HP／護衛 HP：單位範本的 ``max_hp`` 再乘
  （四捨五入、至少 1；體質帶來的 HP 加成不縮放）。
  「Boss」＝ 有 ``boss`` 標籤的敵方範本；「護衛」＝ 有 ``boss_escort`` 標籤的（Boss 戰護衛與援軍，
  ``*_guard``）；其餘敵方範本（一輪與地圖的陣容與援軍，不含召喚物）為「敵人」。
- 敵人傷害／Boss 傷害／護衛傷害：``CoreRules.enemy_damage_permille`` 等欄位 ＝ content 值 × 旋鈕。
- 技能法力費用：已縮放過的技能費用再乘旋鈕（兩次四捨五入、有費用者至少 1），
  ``CoreRules.ally_mana_cost_permille`` ＝ content 值 × 旋鈕
  （之後 ``Ruleset.with_skills`` 加入的技能  依這個**絕對**倍率從原始費用縮放）。
- 法力上限：``ResourceRules.mana_cap_permille`` ＝ content 值 × 旋鈕。

要回到 BAL-4 的「純 1000」基準，把旋鈕設成 content 值的倒數（例如費用 1250、上限 714）；一般用法是
直接比較 content 現況（``NEUTRAL``）與調整後的差異。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, apply_ally_mana_cost, enemy_template_ids
from trpg.engine.ids import BOSS_ESCORT_TAG, BOSS_TAG

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
    escort_hp: int = _PERMILLE
    escort_damage: int = _PERMILLE

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
            ("護衛HP", self.escort_hp),
            ("護衛傷", self.escort_damage),
        )
        parts = [f"{n}={v}" for n, v in names if v != _PERMILLE]
        return " ".join(parts) if parts else "baseline"


NEUTRAL = Difficulty()


def scale_int(value: int, permille: int) -> int:
    """``value × permille‰``，四捨五入（半數進位），整數運算。"""
    return (value * permille + _PERMILLE // 2) // _PERMILLE


def enemy_roster(library: ContentLibrary) -> tuple[str, ...]:
    """敵方範本 ID（排序）：一輪的遭遇與 Boss 陣容、地圖預設陣容與援軍事件；不含召喚物。"""
    return enemy_template_ids(library.units, library.maps, library.roguelite)


def _hp_permille(template: UnitTemplate, d: Difficulty) -> int:
    if BOSS_TAG in template.tags:
        return d.boss_hp
    return d.escort_hp if BOSS_ESCORT_TAG in template.tags else d.enemy_hp


def _scale_units(library: ContentLibrary, d: Difficulty, roster: Iterable[str]) -> dict:  # type: ignore[type-arg]
    units = dict(library.units)
    for template_id in roster:
        template = units[template_id]
        permille = _hp_permille(template, d)
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
    old = ruleset.core
    core = old.model_copy(
        update={
            "enemy_damage_permille": scale_int(old.enemy_damage_permille, d.enemy_damage),
            "boss_damage_permille": scale_int(old.boss_damage_permille, d.boss_damage),
            "boss_escort_damage_permille": scale_int(
                old.boss_escort_damage_permille, d.escort_damage
            ),
            "ally_mana_cost_permille": scale_int(old.ally_mana_cost_permille, d.mana_cost),
            "resources": old.resources.model_copy(
                update={"mana_cap_permille": scale_int(old.resources.mana_cap_permille, d.mana_cap)}
            ),
        }
    )
    new_ruleset = ruleset.model_copy(update={"core": core})
    new_ruleset = apply_ally_mana_cost(new_ruleset, units, roster, d.mana_cost)
    new_ruleset.model_post_init(None)
    return dataclasses.replace(library, units=units, ruleset=new_ruleset)
