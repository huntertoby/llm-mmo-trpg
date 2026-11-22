"""BS-1：數值工坊開放背刺／潛行偷襲的加成（``rules/core.yaml``）與無聲的預算成本
（``skill_budget.yaml``），06 6.21.1「數值工坊開放的欄位」。

數值一律讀 ``content/`` 的現值（使用者寫回後不必收編）；只寫死欄位路徑與對象種類。
"""

from __future__ import annotations

from typing import Any

from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.objects import TABLE_NAMES_ZH, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TABLE_KINDS, parse_path

CONTENT = bundled_content_dir()
CORE = "rules/core.yaml"
BUDGET = "skill_budget.yaml"
CORE_PATHS = (
    "backstab_hit_bonus",
    "backstab_crit_range_bonus",
    "ambush_hit_bonus",
    "far_distance",  # SK-1（#166）條件「遠距」的門檻
    "trap_trace_radius",  # RG-2（#162）陷阱痕跡
    "shield_guard_hit_penalty",  # RG-1（#162）盾兵掩護
    "contagion_radius",  # SK-2b：疾病擴散的距離
    "reroll_ally_range",  # SK-3b：重擲幫隊友的範圍
    "shield_formation_hit_penalty",  # RG-4（#163）塔盾詞條「護陣」
    "party_ap_per_turn",  # AP-1（#168）
    "ap_per_turn",
    "elite_ap_per_turn",
    "ap_carry_max",
    "miss_refund_ap",
    "miss_refund_min_cost",
    "boss_parts.hp_total_max_permille",  # HC-4a：部位血量加總上限（從 parts.py 搬來）
    "tier_budget.1",  # HC-B：階級預算（數字鍵）、武器基準傷害、召喚物小特性的點數
    "tier_budget.2",
    "tier_budget.3",
    "tier_budget.4",
    "tier_budget.5",
    "budget_reference_weapon_damage",
    "summon_traits.sturdy.budget_points",
    "summon_traits.swift.budget_points",
    "summon_traits.keen.budget_points",
    "element_mod_floor_permille",  # HC-4b：和裝備規則的總減傷上限一起開
    "skill_limits.min_form_entry_cooldown",  # GS-3：帶進入時效果的化身技最短冷卻
    "skill_limits.max_cooldown",  # HC-4b：技能結構的規則數值（從 skills/constants.py 搬來）
    "skill_limits.min_crit_range",
    "skill_limits.max_grant_duration",
    "skill_limits.max_refund_ap",
    "skill_limits.max_cooldown_restore",
    "skill_limits.modifier_bounds.damage_permille_min",  # HC-4b2：修正規則的幅度
    "skill_limits.modifier_bounds.heal_permille_min",
    "skill_limits.modifier_bounds.hit_bonus_max",
    "skill_limits.modifier_bounds.cooldown_delta_max",
    "skill_limits.modifier_bounds.push_distance_delta_max",
    "skill_limits.modifier_bounds.range_delta_max",
    "skill_limits.modifier_bounds.summon_duration_delta_max",
    "skill_limits.modifier_bounds.on_hit_max_displace",
)
BUDGET_PATHS = (
    "modifier.points_milli.silent_strike",
    "silent_strike_round_milli",
    "condition_permille.mild",  # SK-1（#166）寬鬆條件（本回合移動過）的倍率
    "hook_min_cooldown",  # SK-2b：鉤的冷卻下限
    "hook_points",  # SK-3b：SK-2 三個新原語的預算點數（從原語表搬來）
    "contagion_points",
    "reroll_budget_permille",  # SK-3b：重擲的預算
    "absorb_surface_points",
    "borrow_ap_points",  # AP-2：預支的預算點數
    "flash_cost.damage_rungs",  # FL-1a：閃現蓄力、輕巧的調整幅度
    "flash_cost.magnitude_step",
    "flash_transform.companion_power_permille",  # TF-1：伴生、護主的縮小幅度與輪數
    "flash_transform.companion_duration",
    "flash_transform.guardian_power_permille",
    "flash_transform.guardian_duration",
)


def _now(file: str, path: str) -> Any:
    found = lookup(read_data(CONTENT / file), parse_path(path))
    return None if found is MISSING else found


def test_the_rules_and_budget_tables_are_listed(read_service: TuningService) -> None:
    # NW-3 物件表、PK-1 挑選、SK-5 觸發時機與組合器
    assert TABLE_KINDS == (
        "ai",
        "rules",
        "budget",
        "object",
        "pick",
        "skill_triggers",
        "skill_composer",
        "skill_conditions",  # HC-B：條件的預算倍率覆寫、協同係數
        "skill_synergies",
        "forms",  # HC-W2：形態、裝備規則、物品生成
        "equipment",
        "item_gen",
        "skill_evolution",  # HC-4b2：召喚技分歧進化的幅度
        "flash",  # HC-4b3：閃現的計價與規則數值
        "world_rules",  # HC-4d：大世界規則、經濟、交易、賽季
        "world_economy",
        "world_trade",
        "world_season",
    )
    found = {o.kind: o for o in read_service.objects() if o.kind in ("rules", "budget")}
    assert (found["rules"].id, found["rules"].file, found["rules"].category) == (
        "core",
        CORE,
        "rules",
    )
    assert (found["budget"].id, found["budget"].file, found["budget"].category) == (
        "skill_budget",
        BUDGET,
        "rules",
    )
    assert found["rules"].name_zh == TABLE_NAMES_ZH["rules"]


def test_the_detail_shows_the_current_values(read_service: TuningService) -> None:
    core = object_detail(CONTENT, read_service.table, "rules", "core")
    assert [f.path for f in core.fields] == list(CORE_PATHS)
    assert [f.value for f in core.fields] == [_now(CORE, p) for p in CORE_PATHS]
    assert any("全體共用" in n for n in core.notes_zh)
    budget = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    paths = [f.path for f in budget.fields]
    # HC-B 起預算表全部開放並分組（原語點數、形狀、係數……），這裡只確認 BS-1 起逐段開的欄位都還在
    assert set(BUDGET_PATHS) <= set(paths)
    assert [f.value for f in budget.fields] == [_now(BUDGET, p) for p in paths]


def test_changes_validate_and_bad_values_are_refused(read_service: TuningService) -> None:
    hit, silent = _now(CORE, "backstab_hit_bonus"), _now(BUDGET, BUDGET_PATHS[0])
    changes = (
        Change(file=CORE, path="backstab_hit_bonus", old=hit, new=hit + 1),
        # 2026-11-21 使用者改值：無聲 420 已貼著無聲步的預算上限，加價會超支，改成降價
        Change(file=BUDGET, path=BUDGET_PATHS[0], old=silent, new=silent - 40),
    )
    read_service.drafts.put(Draft(name="bs1", changes=changes))
    result = read_service.check("bs1")
    assert result.ok, (result.field_errors, result.page_errors)
    bad = TuningChangeIn(file=CORE, path="backstab_hit_bonus", old=hit, new=-1)
    refused = read_service.check("current", [bad])
    assert not refused.ok
    assert [(e.file, e.path) for e in refused.field_errors] == [(CORE, "backstab_hit_bonus")]
