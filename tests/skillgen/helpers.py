"""預算與驗證器測試用的小工具：以字典建立技能、取得違規代碼。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.skills import PrimitiveDef, PrimitiveTable, SkillDef
from trpg.skillgen.validate import Violation, validate_skill

__all__ = ["lib", "lib_with_rewrite_primitive", "rules_of", "skill", "skill_raw", "violations"]


def lib() -> ContentLibrary:
    return library()


def skill(**overrides: Any) -> SkillDef:
    """合格的基準技能（T1 打擊、AP 2、傷害 ×1.8、冷卻 2、法力 4；比例 80.4%），可覆寫任何欄位。

    覆寫值會經過 schema 驗證，所以 schema 層級的錯誤仍會在這裡被擋下；
    要測 schema 擋不到的上限（例如效果超過 4 個），請改用 :func:`skill_raw`。
    """
    return SkillDef.model_validate(_data(**overrides))


def skill_raw(**updates: Any) -> SkillDef:
    """基準技能再用 ``model_copy`` 直接改欄位（不重新驗證），測試驗證器自己的上限檢查。"""
    return skill().model_copy(update=updates)


def _data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "skill_test",
        "name_zh": "測試技",
        "tier": 1,
        "rarity": "rare",
        "kind": "active",
        "skeleton": "strike",
        "category": "weapon",
        "weapon_req": "melee",
        "ap_cost": 2,
        "scaling_attr": "str",
        "shape": {"type": "single", "range": "weapon"},
        "effects": [{"type": "damage", "multiplier_permille": 1800}],
        "condition": None,
        "cost": {"mana": 4, "cooldown": 2},
    }
    data.update(overrides)
    return data


def violations(s: SkillDef, library_: ContentLibrary | None = None) -> list[Violation]:
    return validate_skill(s, library_ or lib())


def rules_of(s: SkillDef, library_: ContentLibrary | None = None) -> set[str]:
    return {v.rule for v in violations(s, library_)}


def lib_with_rewrite_primitive() -> ContentLibrary:
    """加入一個假的改寫規則型原語 ``fake_rewrite``（最低稀有度傳說）的內容庫。"""
    base = lib()
    fake = PrimitiveDef(
        id="fake_rewrite",
        name_zh="額外行動",
        description_zh="測試用的改寫規則型原語",
        category="rule_rewrite",
        min_rarity="legendary",
        harmful=False,
        acts_on="caster",
        budget_basis="fixed",
        base_points=6,
    )
    fields = {name: getattr(base.ruleset, name) for name in Ruleset.model_fields}
    fields["primitives"] = PrimitiveTable(primitives=(*base.ruleset.primitives.primitives, fake))
    return replace(base, ruleset=Ruleset(**fields))
