"""內容覆蓋率（Phase 2G-1 3.3）：content/ 裡定義的機制都要有手寫技能示範，且手寫技能都要被裝備。

允許清單 ``_UNCOVERED`` 列出目前尚未被任何手寫技能使用的 ID；測試同時檢查清單沒有過時
（清單內的 ID 必須真的未被使用），所以補上技能後必須同步刪除清單項目。
"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import SKILL_REACTION_EVENTS, SkillDef

# 尚未被手寫技能使用的 ID。分類 -> {ID: 原因}
_UNCOVERED: dict[str, dict[str, str]] = {
    "skeleton": {},
    "trigger": {},
    "reaction_event": {},
    "condition": {},
    "primitive": {},
    "status": {
        "armor_broken": "只由斧的 armor_break 武器參數施加（3-24a1），沒有技能施加",
        "rallied": "只由戰意圖騰的光環施加（3-33e1），沒有技能施加",
    },
    "stack": {"fury": "只由裝備的充能詞條 affix_charge_fury 使用（3G-G3a），沒有手寫技能"},
}

# 只能由引擎原語間接產生的狀態：使用該原語就算「技能可施加」。
# prone 由 knock_prone 原語產生、shielded 由 shield 原語產生、undying 由 cheat_death 原語產生
# （3C-4a），不需要 apply_status。
_STATUS_VIA_PRIMITIVE = {
    "prone": "knock_prone",
    "shielded": "shield",
    "undying": "cheat_death",
    "soul_link": "redirect_damage",  # 3C-4b
    "revealed": "reveal",  # 3D-8a
    "time_bomb": "delayed_damage",  # 3D-8b
}


# 3-24b1 為關鍵字技能池補的技能：3-24b2 起由開局與候選產生器從池裡給出（不經過 build），
# 在那之前先以池為裝備來源（builds.yaml 是模擬回歸範本，不為補池而改動）。
_POOL_ONLY = frozenset(
    {
        "skill_kindling_strike",
        "skill_flash_freeze",
        "skill_shatter_ice",
        "skill_downpour",
        "skill_holy_water",
        # 3-24c：關鍵字池的真實利用者與不限武器的 1 階技能（由池給出）
        "skill_bone_pursuit",
        "skill_shock_follow",
        "skill_soul_burst",
        "skill_spirit_offering",
        "skill_scorching_slash",
        "skill_flare_shot",
        "skill_kindle_pop",
        "skill_icebreaker",
        "skill_frost_snap",
        "skill_thaw_blast",
        "skill_spark_chain",
        "skill_thunder_clap",
        "skill_splash_flask",
        "skill_frost_touch",
        "skill_mark_prey",
        # 3-27：倒地、潮濕、標記、高處與撞擊、隱蔽、召喚物的專屬主動利用者
        "skill_trample",
        "skill_ground_finish",
        "skill_gravity_crush",
        "skill_tide_cleave",
        "skill_ripple_shot",
        "skill_hunters_strike",
        "skill_pinpoint_shot",
        "skill_plunging_strike",
        "skill_downdraft",
        "skill_pinning_shot",
        "skill_veiled_shot",
        "skill_glacier_offering",
        # 3-31：普攻符文的修正型被動（不是起始技能；由升級候選與戰利品給出，尚無 build 裝備）
        "skill_rune_sight",
        "skill_rune_breaker",
        "skill_rune_etcher",
        # 3-33e1：召喚物（一）的召喚技能（由池給出；dev_summoner 系列起始包也可帶到）
        "skill_summon_fire_spirit",
        "skill_summon_ice_spirit",
        "skill_summon_thunder_spirit",
        "skill_summon_water_sprite",
        "skill_summon_shade",
        "skill_summon_hawk",
        # 3-33e2a：召喚物（二）a
        "skill_summon_bomb_puppet",
        "skill_summon_golem",
        "skill_summon_earth_wall",
        "skill_summon_war_wolf",
    }
)


def _skills() -> list[SkillDef]:
    return list(library().skills.values())


def _equipped() -> set[str]:
    lib = library()
    ids = {s for b in lib.builds.builds for s in b.hero.skills}
    ids |= {s for unit in lib.units.values() for s in unit.skills}
    ids |= _POOL_ONLY
    # 3G-G3b：裝備的授予動作詞條授予的常駐技能也算被裝備
    ids |= {a.skill for a in lib.affixes.values() if a.category == "action"}
    # 3D-8c：裝備的 grant_skill 技能暫時給出的技能（不佔欄位）也算被裝備
    ids |= {
        e.skill
        for sid in ids
        for e in lib.skills[sid].effects
        if e.type == "grant_skill" and e.skill is not None
    }
    return ids


def _conditions(skill: SkillDef) -> list[str]:
    found = [skill.condition.type] if skill.condition else []
    found += [e.condition.type for e in skill.effects if e.condition]
    return found


def _used() -> dict[str, set[str]]:
    skills = _skills()
    primitives = {e.type for s in skills for e in s.effects}
    statuses = {e.status for s in skills for e in s.effects if e.status}
    for s in skills:
        statuses |= {c.status for c in [s.condition] if c and c.status}
        statuses |= {e.condition.status for e in s.effects if e.condition and e.condition.status}
    statuses |= {st for st, prim in _STATUS_VIA_PRIMITIVE.items() if prim in primitives}
    if any(s.followup is not None and s.followup.when == "delayed" for s in skills):
        statuses.add("charging")  # 延遲段（3F-4b）等待期間的狀態，由 followup.when: delayed 產生
    return {
        "skeleton": {s.skeleton for s in skills},
        "trigger": {s.trigger.event for s in skills if s.trigger},
        "reaction_event": {s.reaction.event for s in skills if s.reaction},
        "condition": {c for s in skills for c in _conditions(s)},
        "primitive": primitives,
        "status": {s for s in statuses if s},
        "stack": {e.stack for s in skills for e in s.effects if e.stack},
    }


def _defined() -> dict[str, set[str]]:
    lib = library()
    rules = lib.ruleset
    return {
        "skeleton": {k for k, v in lib.skeletons.items() if v.enabled},
        "trigger": {t.id for t in rules.skill_triggers.triggers},
        "reaction_event": set(SKILL_REACTION_EVENTS),
        "condition": {c.id for c in rules.conditions.conditions},
        "primitive": {p.id for p in rules.primitives.primitives},
        "status": {s.id for s in rules.statuses.statuses},
        "stack": {s.id for s in rules.stacks.stacks},
    }


def test_every_handwritten_skill_is_equipped_by_a_build_or_unit() -> None:
    unequipped = sorted(set(library().skills) - _equipped())
    assert unequipped == [], f"沒有任何 build 英雄或單位裝備的手寫技能：{unequipped}"


def test_equipped_skills_exist() -> None:
    assert sorted(_equipped() - set(library().skills)) == []


def test_every_defined_mechanic_is_used_or_explicitly_allowed() -> None:
    used = _used()
    for category, defined in _defined().items():
        missing = defined - used[category] - set(_UNCOVERED[category])
        assert not missing, f"{category} 沒有任何手寫技能使用，也不在允許清單：{sorted(missing)}"


def test_uncovered_allowlist_is_not_stale() -> None:
    used, defined = _used(), _defined()
    for category, allowed in _UNCOVERED.items():
        stale = {i for i in allowed if i in used[category]}
        assert not stale, f"{category} 允許清單過時（已被使用，請刪除）：{sorted(stale)}"
        unknown = {i for i in allowed if i not in defined[category]}
        assert not unknown, f"{category} 允許清單含不存在的 ID：{sorted(unknown)}"


def test_self_status_cost_is_used_by_a_handwritten_skill() -> None:
    """Phase 2H-1：自身狀態代價至少被一個手寫技能使用；冰凍至少被一個手寫技能施加。"""
    skills = _skills()
    assert any(s.cost.self_status for s in skills)
    assert "frozen" in _used()["status"]


def test_dual_scaling_and_both_masteries_are_used_by_handwritten_skills() -> None:
    """Phase 2H-2：雙屬性縮放、mastery: range、mastery: duration 各至少一個手寫技能使用。"""
    skills = _skills()
    assert any(s.secondary_scaling_attr for s in skills)
    assert any(s.mastery == "range" for s in skills)
    assert any(s.mastery == "duration" for s in skills)
