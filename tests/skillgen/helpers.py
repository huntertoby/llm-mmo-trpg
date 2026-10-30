"""預算與驗證器測試用的小工具：以字典建立技能、取得違規代碼。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.skills import PrimitiveDef, PrimitiveTable, SkillDef
from trpg.skillgen.validate import Violation, validate_skill

__all__ = [
    "general_effect_tags",
    "lib",
    "lib_with_rewrite_primitive",
    "rules_of",
    "skill",
    "skill_raw",
    "standard_form",
    "union_tags",
    "violations",
]


def lib() -> ContentLibrary:
    return library()


def skill(**overrides: Any) -> SkillDef:
    """合格的基準技能（T1 打擊、AP 2、傷害 ×1.8、冷卻 2、耐力 8；比例 80.4%），可覆寫任何欄位。

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
        "cost": {"stamina": 8, "cooldown": 2},
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


def standard_form(schema: dict[str, Any]) -> dict[str, Any]:
    """提議 schema 的一般型態（Phase 4-L5b：頂層是以 ``form`` 區分的型態；只有一個型態時
    就是根；4-L10a 起反應技另一支，這裡取一般種類組那一支）。"""
    if "properties" in schema:
        return schema
    found: dict[str, Any] = schema["$defs"]["SkillProposal"]
    return found


def effect_branches(schema: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """效果模型的各支（4-L10a：「恰好填一個」與 split_heal 的效果拆成以欄位區分的分支；沒有拆
    的就是模型本身）。"""
    model: dict[str, Any] = schema["$defs"][name]
    if "properties" in model:
        return [model]
    return [schema["$defs"][str(i["$ref"]).rsplit("/", 1)[-1]] for i in model["oneOf"]]


def general_effect_tags(schema: dict[str, Any]) -> set[str]:
    """一般型態效果 union 的原語 ID（``GeneralEffect`` 的 ``oneOf``）。"""
    return union_tags(schema["$defs"]["GeneralEffect"])


def union_tags(union: dict[str, Any], prefix: str = "Effect_") -> set[str]:
    """``oneOf`` 各支 ``$ref`` 的 ID（去掉 ``#/$defs/<prefix>``）。"""
    refs = [str(item["$ref"]).rsplit("/", 1)[-1] for item in union["oneOf"]]
    return {r.removeprefix(prefix) for r in refs}
