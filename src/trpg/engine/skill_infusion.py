"""灌注技能（Phase 3-33d，``docs/design/06-技能.md`` 6.29.3）。

施放者花 ``summon_infuse_ap_cost`` AP（:class:`~trpg.engine.actions.InfuseSkill`）把自己的一招主動
技能「借」給自己的一隻召喚物：

- **代價**：法力、HP 代價、每場次數與冷卻在灌注時由 **施放者** 付（冷卻當下開始算）；自身狀態
  代價（``cost.self_status``）也在灌注時加在施放者身上。
- **快照**（:class:`~trpg.engine.state.InfusedSkill`）：施放者當下的有效屬性與技能等級。召喚物施放
  時暫時以快照的屬性、施放者的武器與技能等級代替自己的（:func:`borrowed`；施放完還原），所以傷害、
  命中與「武器射程」都是施放者的數字；之後施放者的屬性變化不影響。召喚物自己的狀態照常生效。
- **施放**（:func:`release_infusion`）：召喚物在 **下一個自己的回合開始時**（回合開始的效果與被動
  觸發之後、行動之前）施放，佔用牠 ``summon_infused_cast_ap_cost`` AP（取代一次普攻）。原點是牠
  的位置，射程、視線、形狀都以牠為準；目標依模式選（:func:`pick_infused`）。選不到合法目標、或
  回合開始時被暈眩等狀態控制時放棄（``infusion_fizzled``），法力與冷卻都不退；施放前倒下或消失
  也不退（灌注隨牠一起離場）。
- **限制**（:func:`infuse_problem`）：每隻每輪最多被灌注 1 次、身上同時只有 1 招待施放；圖騰、
  暈眩中、以及會在施放者這個回合結束時到期（來不及施放）的召喚物不能灌注；技能本身的限制見
  :func:`skill_ban`。

目標的選擇（:func:`pick_infused`；不跑引擎、確定性）：

- **集火**：只選影響範圍內含集火目標的選取（技能有敵對效果時；沒有時同跟隨）；
- **守護我**：有選取能打到「威脅施放者」的敵人（敵人的武器射程 ＋ 速度 ≥ 與施放者的距離）時只從
  這些選取中挑；沒有時同跟隨；
- **跟隨／待命**：所有合法選取。

在剩下的選取中取分數最高者（同分取列舉順序在前的）：敵對技能 ＝ 範圍內敵人數 × 10 − 被
``affects: all`` 波及的友方數 × 15，再以敵人損失的 HP 比例（‰）合計做次序；至少要打到 1 個敵人。
非敵對技能（治療、增益）＝ 範圍內友方數，再以友方損失的 HP 比例合計做次序；至少要有 1 個友方。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from trpg.content.skills import SACRIFICE_SUMMON, SUMMON, SkillDef
from trpg.engine import modifiers
from trpg.engine.actions import InfuseSkill, UseSkill
from trpg.engine.context import Ctx
from trpg.engine.events import (
    InfusedSkillCast,
    InfusionFizzled,
    SkillCooldownChanged,
    SkillInfused,
)
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.statuses import (
    blocks_spells,
    effective_attribute,
    skip_turn_status,
)
from trpg.engine.self_costs import pay_self_costs
from trpg.engine.skill_levels import skill_level
from trpg.engine.skills.casting import run_infused
from trpg.engine.skills.mobility import self_move_problem
from trpg.engine.skills.targeting import (
    SkillArea,
    fires_gun,
    pay_skill_cost,
    resolve_effects,
    resource_problem,
    selections,
)
from trpg.engine.state import BattleState, InfusedSkill, UnitState
from trpg.engine.summon_control import summon_problem
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, UnitId

__all__ = [
    "InfuseChoice",
    "borrowed",
    "do_infuse_skill",
    "infuse_choices",
    "infuse_problem",
    "infused_pick",
    "pick_infused",
    "release_infusion",
    "skill_ban",
    "skill_infuse_problem",
    "snapshot",
    "summon_target_problem",
]

_RULE_CATEGORIES = ("rule_rewrite", "rule_change")
_SELF_MOVES = ("dash", "leap", "charge_through", "shadowstep")
_ENEMY_POINTS = 10
_ALLY_HIT_POINTS = 15
_PERMILLE = 1000


def skill_ban(state: BattleState, skill: SkillDef) -> str | None:
    """技能本身不能灌注的原因（不看施放者的資源）；可以時 ``None``。

    只能灌注一般的主動技能；不能灌注召喚（含獻祭召喚物）、傳說、改變規則類（改寫規則型原語、
    規則改變）、複合技能（``followup``）、陷阱技能與需要層數的技能。"""
    specs = list(skill.iter_effects())
    rules = state.ruleset
    checks = (
        (skill.kind != "active" or skill.is_activatable, "只有主動技能可以灌注"),
        (skill.rarity == "legendary", "傳說技能不能灌注"),
        (any(e.type in (SUMMON, SACRIFICE_SUMMON) for e in specs), "召喚技能不能灌注"),
        (
            # iter_effects 含巢狀效果（on_kill 的 refund_ap 等不是原語，查不到就略過）
            any(
                p is not None and p.category in _RULE_CATEGORIES
                for p in (rules.find_primitive(e.type) for e in specs)
            ),
            "改變規則類技能不能灌注",
        ),
        (skill.followup is not None, "複合技能（多段）不能灌注"),
        (skill.trap is not None, "陷阱技能不能灌注"),
        (skill.cost.stacks is not None, "需要層數的技能不能灌注"),
    )
    reason = next((text for banned, text in checks if banned), None)
    return None if reason is None else f"{reason}：{skill.name_zh}"


def skill_infuse_problem(state: BattleState, owner: UnitState, skill_id: str) -> str | None:
    """``owner`` 不能灌注 ``skill_id`` 的原因（技能本身與施放者的資源：法力、冷卻、武器、沉默……；
    不看召喚物與 AP）；可以時 ``None``。"""
    if skill_id not in owner.all_skills:
        return f"{owner.name_zh} 沒有裝備技能：{skill_id}"
    try:
        skill = state.ruleset.skill_def(skill_id)
    except KeyError:
        return f"找不到技能：{skill_id}"
    problem = skill_ban(state, skill)
    if problem is not None:
        return problem
    if fires_gun(owner, skill):
        return f"火器技能需要彈藥，不能灌注：{skill.name_zh}"
    return resource_problem(state, owner, skill)


def infuse_problem(state: BattleState, owner: UnitState, action: InfuseSkill) -> str | None:
    """灌注不合法的原因：召喚物不能操控、已有一招待施放、本輪已灌注過、被暈眩、AP 不足、技能
    不能灌注（:func:`skill_infuse_problem`）。"""
    problem = summon_target_problem(state, owner, action.summon_id)
    if problem is not None:
        return problem
    cost = state.ruleset.core.summon_infuse_ap_cost
    if owner.ap < cost:
        return f"AP 不足：灌注需要 {cost}，剩餘 {owner.ap}"
    return skill_infuse_problem(state, owner, action.skill_id)


def summon_target_problem(state: BattleState, owner: UnitState, summon_id: UnitId) -> str | None:
    """召喚物這邊不能接受灌注的原因（不看技能與 AP）。"""
    problem = summon_problem(state, owner, summon_id)
    if problem is not None:
        return problem
    summon = state.units[summon_id]
    if summon.infused_skill is not None:
        name = _skill_name(state, summon.infused_skill.skill_id)
        return f"{summon.name_zh}身上已經有待施放的「{name}」"
    if summon.infused_round == state.round:
        return f"{summon.name_zh}本輪已經被灌注過了"
    if skip_turn_status(state.ruleset, summon) is not None:
        return f"{summon.name_zh}無法行動（暈眩）"
    expires = summon.summon_expires_round
    if state.active_unit == owner.id and expires is not None and expires <= state.round:
        return f"{summon.name_zh}會在你的回合結束時消失，來不及施放"
    return None


def _skill_name(state: BattleState, skill_id: str) -> str:
    try:
        return state.ruleset.skill_def(skill_id).name_zh
    except KeyError:
        return skill_id


@dataclass(frozen=True, slots=True)
class InfuseChoice:
    """灌注選單的一招技能：``problem`` 為不能灌注的中文原因（可以時 ``None``）。"""

    skill_id: str
    name_zh: str
    problem: str | None


def infuse_choices(
    state: BattleState, owner: UnitState, summon_id: UnitId
) -> tuple[str | None, tuple[InfuseChoice, ...]]:
    """灌注選單：``(召喚物或 AP 的問題, 每招主動技能的選項)``（技能依裝備順序；只列主動技能）。"""
    problem = summon_target_problem(state, owner, summon_id)
    cost = state.ruleset.core.summon_infuse_ap_cost
    if problem is None and owner.ap < cost:
        problem = f"AP 不足：灌注需要 {cost}，剩餘 {owner.ap}"
    found: list[InfuseChoice] = []
    for skill_id in owner.all_skills:
        try:
            skill = state.ruleset.skill_def(skill_id)
        except KeyError:
            continue
        if skill.kind != "active":
            continue
        found.append(
            InfuseChoice(skill_id, skill.name_zh, skill_infuse_problem(state, owner, skill_id))
        )
    return problem, tuple(found)


# ---------------------------------------------------------------------------
# 灌注（施放者的動作）
# ---------------------------------------------------------------------------


def do_infuse_skill(ctx: Ctx, owner: UnitState, action: InfuseSkill) -> None:
    """灌注的結算：花 AP、付技能的代價（法力、HP、次數、冷卻）、記下快照、自身狀態代價加在施放者
    身上。"""
    problem = infuse_problem(ctx.state, owner, action)
    if problem is not None:
        raise IllegalActionError(problem)
    state = ctx.state
    skill = state.ruleset.skill_def(action.skill_id)
    summon = state.units[action.summon_id]
    ap = ctx.core.summon_infuse_ap_cost
    paid = pay_skill_cost(owner, skill, ap=ap)
    summon.infused_skill = snapshot(state, owner, skill.id)
    summon.infused_round = state.round
    ctx.emit(
        SkillInfused,
        unit_id=summon.id,
        owner_id=owner.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        ap=paid.ap,
        mana=skill.cost.mana,
        mana_after=owner.mana,
        stamina=skill.cost.stamina,
        stamina_after=owner.stamina,
        hp_spent=paid.hp,
        cooldown=paid.cooldown,
    )
    if paid.cooldown is not None:
        ctx.emit(SkillCooldownChanged, unit_id=owner.id, skill_id=skill.id, remaining=paid.cooldown)
    pay_self_costs(ctx, owner, skill)


# ---------------------------------------------------------------------------
# 借用施放者的數字
# ---------------------------------------------------------------------------


@contextmanager
def borrowed(state: BattleState, summon: UnitState, infused: InfusedSkill) -> Iterator[SkillDef]:
    """暫時讓召喚物用灌注快照 ``infused`` 的屬性、施放者的武器與技能等級（``with`` 結束時還原），
    產生要施放的技能（套用技能等級的 5 級小特性；不套變奏與施放者的修正規則）。"""
    owner = state.units[infused.owner_id]
    saved = (summon.attributes, summon.weapon, summon.skill_levels)
    summon.attributes = dict(infused.attributes)
    summon.weapon = owner.weapon
    summon.skill_levels = {infused.skill_id: infused.skill_level} if infused.skill_level > 1 else {}
    try:
        yield modifiers.shaped_skill(state, summon, state.ruleset.skill_def(infused.skill_id))
    finally:
        summon.attributes, summon.weapon, summon.skill_levels = saved


def _cast_problem(state: BattleState, summon: UnitState, skill: SkillDef) -> str | None:
    """召喚物自己施放不了（沉默時的法術技、定身或倒地時的自身位移）。"""
    if skill.category == "spell" and blocks_spells(state.ruleset, summon):
        return "沉默"
    if any(e.type in _SELF_MOVES for e in skill.effects):
        return self_move_problem(state, summon)
    return None


def _threatens(enemy: UnitState, owner: UnitState) -> bool:
    return manhattan(enemy.xy, owner.xy) <= enemy.weapon.range + enemy.speed


def _mode_filter(
    state: BattleState,
    summon: UnitState,
    hostile: bool,
    options: list[tuple[UseSkill, SkillArea]],
) -> list[tuple[UseSkill, SkillArea]]:
    if not hostile:
        return options
    mode = summon.summon_mode
    if mode == "focus":
        target = (
            None if summon.summon_target_id is None else state.units.get(summon.summon_target_id)
        )
        if target is not None and target.alive and target.team is not summon.team:
            return [o for o in options if target.id in o[1].units]
        return options
    if mode == "guard" and summon.owner_id is not None:
        owner = state.units.get(summon.owner_id)
        if owner is None or not owner.alive:
            return options
        threats = {
            e.id for e in state.living_units() if e.team is not summon.team and _threatens(e, owner)
        }
        guarded = [o for o in options if threats.intersection(o[1].units)]
        return guarded or options
    return options


def _missing_permille(unit: UnitState) -> int:
    return (unit.max_hp - unit.hp) * _PERMILLE // max(unit.max_hp, 1)


def _score(
    state: BattleState, summon: UnitState, skill: SkillDef, area: SkillArea
) -> tuple[int, int] | None:
    effects = resolve_effects(state, skill)
    units = [state.units[uid] for uid in area.units]
    enemies = [u for u in units if u.team is not summon.team]
    allies = [u for u in units if u.team is summon.team]
    if any(e.hostile for e in effects):
        if not enemies:
            return None
        harmed = 0
        if any(e.affects == "all" for e in effects):
            harmed = sum(1 for u in allies if u.id != summon.id)
        points = len(enemies) * _ENEMY_POINTS - harmed * _ALLY_HIT_POINTS
        return points, sum(_missing_permille(u) for u in enemies)
    if not allies:
        return None
    return len(allies), sum(_missing_permille(u) for u in allies)


def _pick(
    state: BattleState, summon: UnitState, skill: SkillDef
) -> tuple[UseSkill, SkillArea] | None:
    """在 :func:`borrowed` 之內：依模式選出的選取（見模組說明）；沒有時 ``None``。"""
    if _cast_problem(state, summon, skill) is not None:
        return None
    hostile = any(e.hostile for e in resolve_effects(state, skill))
    options = _mode_filter(state, summon, hostile, list(selections(state, summon, skill)))
    best: tuple[tuple[int, int], UseSkill, SkillArea] | None = None
    for pick, area in options:
        score = _score(state, summon, skill, area)
        if score is not None and (best is None or score > best[0]):
            best = (score, pick, area)
    return None if best is None else (best[1], best[2])


def snapshot(state: BattleState, owner: UnitState, skill_id: str) -> InfusedSkill:
    """``owner`` 現在灌注 ``skill_id`` 的快照（有效屬性、技能等級、輪數）。"""
    return InfusedSkill(
        skill_id=skill_id,
        owner_id=owner.id,
        attributes=tuple((a, effective_attribute(state.ruleset, owner, a)) for a in Attribute),
        skill_level=skill_level(owner, skill_id),
        round=state.round,
    )


def pick_infused(state: BattleState, summon_id: UnitId) -> tuple[UseSkill, SkillArea] | None:
    """召喚物 ``summon_id`` 以目前位置與模式施放身上灌注的技能時會選的選取與影響範圍（不修改
    ``state``；沒有灌注、已離場或選不到時 ``None``）。"""
    summon = state.units.get(summon_id)
    if summon is None or summon.infused_skill is None or not summon.alive:
        return None
    return _pick_with(state, summon_id, summon.infused_skill)


def infused_pick(
    state: BattleState, summon_id: UnitId, skill_id: str, owner_id: UnitId
) -> tuple[UseSkill, SkillArea] | None:
    """預覽用：假設 ``owner_id`` 現在把 ``skill_id`` 灌注給 ``summon_id``，召喚物以目前位置與模式
    會選的選取（不修改 ``state``）。"""
    summon = state.units.get(summon_id)
    owner = state.units.get(owner_id)
    if summon is None or owner is None or not summon.alive:
        return None
    return _pick_with(state, summon_id, snapshot(state, owner, skill_id))


def _pick_with(
    state: BattleState, summon_id: UnitId, infused: InfusedSkill
) -> tuple[UseSkill, SkillArea] | None:
    sim = state.clone()
    summon = sim.units[summon_id]
    with borrowed(sim, summon, infused) as skill:
        return _pick(sim, summon, skill)


# ---------------------------------------------------------------------------
# 召喚物的回合開始：施放
# ---------------------------------------------------------------------------


def release_infusion(ctx: Ctx, summon: UnitState) -> None:
    """召喚物回合開始（其他回合開始的處理之後）：施放灌注的技能，或放棄（``infusion_fizzled``）。"""
    infused = summon.infused_skill
    assert infused is not None
    summon.infused_skill = None
    name = _skill_name(ctx.state, infused.skill_id)
    if skip_turn_status(ctx.rules, summon) is not None:
        _fizzle(ctx, summon, infused, name, "controlled")
        return
    with borrowed(ctx.state, summon, infused) as skill:
        found = _pick(ctx.state, summon, skill)
        if found is None:
            _fizzle(ctx, summon, infused, name, "no_target")
            return
        pick, area = found
        summon.ap = max(0, summon.ap - ctx.core.summon_infused_cast_ap_cost)
        ctx.emit(
            InfusedSkillCast,
            unit_id=summon.id,
            owner_id=infused.owner_id,
            skill_id=skill.id,
            name_zh=skill.name_zh,
            origin=Pos(x=summon.xy[0], y=summon.xy[1]),
            target_id=pick.target_id,
            target_pos=pick.target_pos,
            direction=pick.direction,
            tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
        )
        run_infused(ctx, summon, skill, pick, area)


def _fizzle(ctx: Ctx, summon: UnitState, infused: InfusedSkill, name: str, reason: str) -> None:
    ctx.emit(
        InfusionFizzled,
        unit_id=summon.id,
        owner_id=infused.owner_id,
        skill_id=infused.skill_id,
        name_zh=name,
        reason=reason,
    )
