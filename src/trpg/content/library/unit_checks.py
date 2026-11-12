"""單位範本、測試 build、Boss 階段與地圖引用的跨檔案檢查。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from trpg.content.battle import BossPhase, OffhandDef, TagDownTrigger, UnitTemplate, WeaponDef
from trpg.content.environment import AiProfileTable, WeatherDef, check_rule
from trpg.content.library.gear_checks import _GearCatalog
from trpg.content.library.ruleset import Ruleset
from trpg.content.maps import MapDef, SpawnUnitsEvent
from trpg.content.parts import ControlBreak, StopMechanicBreak
from trpg.content.rules import CoreRules
from trpg.content.sim_builds import BuildTable
from trpg.content.skills import SkillDef, held_gear, skill_slot_problems, weapon_problem
from trpg.shared.errors import ContentError


def _check_units(
    root: Path,
    units: dict[str, UnitTemplate],
    *,
    weapons: dict[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    source: Path | None = None,
    gear: _GearCatalog | None = None,
) -> None:
    """單位範本引用的武器、行為模式、反應與技能都存在且合法（``source``：錯誤訊息指向的檔案）。
    ``gear``：有給時檢查範本的裝備（物品存在、穿戴合法；Phase 3G-G1）；召喚物不能有裝備。"""
    reaction_index = ruleset.reactions.by_id()
    for template_id, template in units.items():
        path = source or root / "units" / f"{template_id}.yaml"
        if template.weapon not in weapons:
            raise ContentError(path, f"未知的武器：{template.weapon}")
        if template.equipment:
            problems = (
                ["召喚物不能有裝備"]
                if gear is None
                else gear.problems(template, weapons[template.weapon])
            )
            if problems:
                raise ContentError(path, "；".join(problems))
        if template.ai_profile is not None and template.ai_profile not in ai_profiles.by_id():
            raise ContentError(path, f"未知的行為模式：{template.ai_profile}")
        if template.totem is not None:
            status = next(
                (d for d in ruleset.statuses.statuses if d.id == template.totem.status), None
            )
            if status is None or not status.beneficial:
                raise ContentError(path, f"圖騰的狀態必須是有益的既有狀態：{template.totem.status}")
        _check_summon_traits(path, template, ruleset)
        for rule in template.reactions or ():
            try:
                check_rule(rule, reaction_index, skills)
            except ValueError as exc:
                raise ContentError(path, str(exc)) from exc
            if rule.reaction in skills and rule.reaction not in template.skills:
                raise ContentError(path, f"反應規則引用了沒有裝備的反應技：{rule.reaction}")
        offhand = None if gear is None else gear.offhand_of(template)
        problems = unit_skill_problems(
            template, weapons[template.weapon], skills, ruleset.core, offhand
        )
        if problems:
            raise ContentError(path, "；".join(problems))


def _check_summon_traits(path: Path, template: UnitTemplate, ruleset: Ruleset) -> None:
    """召喚物的固有灌注關鍵字在對照表中、命中特性的狀態存在（Phase 3-33e1）。"""
    if template.innate is not None and template.innate not in ruleset.core.summon_infusions:
        raise ContentError(path, f"固有灌注關鍵字不在 summon_infusions 對照表中：{template.innate}")
    status_ids = {d.id for d in ruleset.statuses.statuses}
    for rule in template.hit_rules:
        if rule.status is not None and rule.status not in status_ids:
            raise ContentError(path, f"命中特性引用了未知的狀態：{rule.status}")
    for opening in template.opening_statuses:  # Phase 5A-M1
        if opening.status not in status_ids:
            raise ContentError(path, f"開場狀態引用了未知的狀態：{opening.status}")


def _check_builds(
    root: Path,
    builds: BuildTable,
    units: dict[str, UnitTemplate],
    *,
    weapons: dict[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    gear: _GearCatalog,
) -> None:
    """build 的英雄範本合法（武器、技能、行為模式、裝備），隊友存在，build ID 不與單位範本衝突。"""
    path = root / "sim" / "builds.yaml"
    unknown = sorted(c for c in builds.companions if c not in units)
    if unknown:
        raise ContentError(path, f"companions 引用了未知的單位範本：{', '.join(unknown)}")
    clash = sorted(b.id for b in builds.builds if b.id in units)
    if clash:
        raise ContentError(path, f"build ID 與單位範本重複：{', '.join(clash)}")
    heroes = {b.id: b.hero for b in builds.builds}
    player_side = {**heroes, **{c: units[c] for c in sorted(builds.companions)}}
    problems = [
        p
        for uid, template in sorted(player_side.items())
        for p in player_template_enemy_only_problems(uid, template, skills, ruleset)
    ]
    if problems:
        raise ContentError(path, "；".join(problems))
    _check_units(
        root,
        heroes,
        weapons=weapons,
        skills=skills,
        ruleset=ruleset,
        ai_profiles=ai_profiles,
        source=path,
        gear=gear,
    )


def player_template_enemy_only_problems(
    unit_id: str, template: UnitTemplate, skills: Mapping[str, SkillDef], ruleset: Ruleset
) -> list[str]:
    """玩家這一邊的範本（Phase 5F-R1；build 英雄＝主角、影子、傭兵、劇情夥伴的底稿，
    與 build 的隊友）
    不能裝 ``enemy_only`` 技能（技能欄與反應）、不能開場帶 ``enemy_only`` 狀態。"""
    problems: list[str] = []
    reactions = tuple(r.reaction for r in template.reactions or ())
    for sid in (*template.skills, *reactions):
        skill = skills.get(sid)
        if skill is not None and skill.enemy_only:
            problems.append(f"{unit_id}：技能 {sid} 只給敵人（enemy_only），玩家這一邊不能用")
    enemy_statuses = ruleset.enemy_only_statuses()
    for opening in template.opening_statuses:
        if opening.status in enemy_statuses:
            problems.append(
                f"{unit_id}：開場狀態 {opening.status} 只給敵人（enemy_only），玩家這一邊不能帶"
            )
    return problems


def unit_skill_problems(
    template: UnitTemplate,
    weapon: WeaponDef,
    skills: dict[str, SkillDef],
    core: CoreRules,
    offhand: OffhandDef | None = None,
) -> list[str]:
    """單位範本裝備的技能是否存在、與武器（含限定武器，3I-5）相容、沒有超過欄位上限（繁體中文，
    空串列為通過）。``offhand``：範本裝備的副手。"""
    held = held_gear(weapon, offhand)
    problems: list[str] = []
    equipped: list[SkillDef] = []
    for skill_id in template.skills:
        skill = skills.get(skill_id)
        if skill is None:
            problems.append(f"skills：未知的技能 {skill_id!r}")
            continue
        equipped.append(skill)
        problem = weapon_problem(skill, weapon.weapon_class, held)
        if problem is not None:
            problems.append(f"skills：{problem}")
    problems += [f"skills：{p}" for p in skill_slot_problems(equipped, core.skill_slots)]
    return problems


def unit_phase_problems(
    template: UnitTemplate,
    *,
    units: Mapping[str, UnitTemplate],
    weapons: Mapping[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    weather: Mapping[str, WeatherDef],
    offhand: OffhandDef | None = None,
) -> list[str]:
    """範本 ``phases``（Phase 5F-2）引用的技能（存在、符合武器、欄位上限）、行為模式、狀態、天氣、
    召喚範本與地形都存在（繁體中文，空串列為通過）。"""
    problems: list[str] = []
    status_ids = set(ruleset.statuses.by_id())
    profiles = ai_profiles.by_id()
    terrain_ids = set(ruleset.terrain.by_id())
    weapon = weapons.get(template.weapon)
    for phase in template.phases:
        where = f"階段 {phase.id}"
        if phase.skills is not None and weapon is not None:
            staged = template.model_copy(update={"skills": phase.skills})
            problems += [
                f"{where}：{p}"
                for p in unit_skill_problems(staged, weapon, skills, ruleset.core, offhand)
            ]
        if phase.ai_profile is not None and phase.ai_profile not in profiles:
            problems.append(f"{where}：未知的行為模式 {phase.ai_profile}")
        wanted = [*phase.remove_statuses, *(o.status for o in phase.add_statuses)]
        problems += [f"{where}：未知的狀態 {s}" for s in wanted if s not in status_ids]
        if phase.weather is not None and phase.weather not in weather:
            problems.append(f"{where}：未知的天氣 {phase.weather}")
        for spawn in phase.spawns:
            found = units.get(spawn.template)
            if found is None or found.summon:
                problems.append(f"{where}：召喚的單位範本不存在或是召喚物 {spawn.template}")
            elif found.phases:
                problems.append(f"{where}：召喚的單位範本不能也有 phases（{spawn.template}）")
        problems += [
            f"{where}：未知的地形 {t.terrain}"
            for t in phase.tiles
            if t.terrain is not None and t.terrain not in terrain_ids
        ]
    return problems + unit_part_problems(template, ruleset)


def unit_part_problems(template: UnitTemplate, ruleset: Ruleset) -> list[str]:
    """範本 ``parts``（PB-1a）引用的狀態：``control`` 的狀態要存在、而且是控制（有
    ``control_group`` 或 ``skip_turn``）；``stop_mechanic`` 的狀態要存在（繁體中文，空串列為通過）。
    結構與封招、階段 ID 的檢查在 ``UnitTemplate`` 本身（:func:`template_part_problems`）。"""
    problems: list[str] = []
    statuses = ruleset.statuses.by_id()
    for part in template.parts:
        where = f"部位 {part.id}"
        for effect in part.on_break:
            if isinstance(effect, ControlBreak):
                found = statuses.get(effect.status)
                if found is None:
                    problems.append(f"{where}：未知的狀態 {effect.status}")
                elif found.control_group is None and not found.skip_turn:
                    problems.append(f"{where}：control 的狀態 {effect.status} 不是控制狀態")
            elif isinstance(effect, StopMechanicBreak) and effect.status not in statuses:
                problems.append(f"{where}：未知的狀態 {effect.status}")
    return problems


def _check_unit_phases(
    root: Path,
    units: dict[str, UnitTemplate],
    *,
    weapons: dict[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    weather: dict[str, WeatherDef],
    gear: _GearCatalog,
) -> None:
    """每個範本的 ``phases`` 都通過 :func:`unit_phase_problems`。"""
    for template_id, template in units.items():
        problems = unit_phase_problems(
            template,
            units=units,
            weapons=weapons,
            skills=skills,
            ruleset=ruleset,
            ai_profiles=ai_profiles,
            weather=weather,
            offhand=gear.offhand_of(template),
        )
        if problems:
            raise ContentError(root / "units" / f"{template_id}.yaml", "；".join(problems))


def _map_phase_tile_problems(map_def: MapDef, units: Mapping[str, UnitTemplate]) -> list[str]:
    """地圖預設陣容裡 Boss 階段的 ``tiles``／``spawns.at`` 在地圖內（Phase 5F-2）。"""
    if map_def.encounter is None:
        return []
    problems: list[str] = []
    for template_id in sorted(set(map_def.encounter.enemies)):
        template = units.get(template_id)
        for phase in () if template is None else template.phases:
            cells = [t.at for t in phase.tiles] + [s.at for s in phase.spawns if s.at is not None]
            problems += [
                f"{template_id} 階段 {phase.id} 的 {list(xy)} 在地圖外"
                for xy in cells
                if not (0 <= xy[0] < map_def.width and 0 <= xy[1] < map_def.height)
            ]
            problems += _tag_down_problems(template_id, phase, map_def.encounter.enemies, units)
    return problems


def _tag_down_problems(
    template_id: str, phase: BossPhase, enemies: Sequence[str], units: Mapping[str, UnitTemplate]
) -> list[str]:
    """``tag_down`` 觸發（Phase 5F-3）：預設陣容裡帶該標籤的單位要夠 ``count`` 名（否則永遠不會
    觸發）。"""
    trigger = phase.trigger
    if not isinstance(trigger, TagDownTrigger):
        return []
    have = sum(1 for e in enemies if (u := units.get(e)) is not None and trigger.tag in u.tags)
    if have >= trigger.count:
        return []
    return [
        f"{template_id} 階段 {phase.id} 要「{trigger.tag}」倒下 {trigger.count} 名，"
        f"地圖的預設陣容只有 {have} 名"
    ]


def _map_reference_problems(
    map_def: MapDef, units: dict[str, UnitTemplate], weather: dict[str, WeatherDef]
) -> list[str]:
    """地圖引用的天氣、遭遇與地圖事件中的單位範本是否存在。"""
    problems: list[str] = []
    if map_def.weather not in weather:
        problems.append(f"未知的天氣：{map_def.weather}")
    templates: list[str] = []
    if map_def.encounter is not None:
        templates += [*map_def.encounter.allies, *map_def.encounter.enemies]
    for event in map_def.events:
        if isinstance(event, SpawnUnitsEvent):
            templates += [u.template for u in event.units]
    unknown = sorted({t for t in templates if t not in units})
    if unknown:
        problems.append(f"未知的單位範本：{', '.join(unknown)}")
    return problems
