"""效用 AI 的預覽收益：把 ``preview`` 的事件換算成分數項（傷害、擊倒、狀態、表面、推擊、掩護……）。

自 :mod:`trpg.engine.ai.utility` 拆出（Phase R1c），內容未改。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import (
    AiProfile,
    AiWeights,
)
from trpg.content.skills import (
    HURL_OBJECT,
    SkillDef,
)
from trpg.engine.actions import (
    Attack,
    Defend,
    UseSkill,
)
from trpg.engine.ai.displace import exposure, is_hurt
from trpg.engine.ai.priority import (
    formation_break,
    priority_points,
    share_discount,
)
from trpg.engine.ai.rune import read_gains, rune_gains
from trpg.engine.ai.scene_objects import has_fire_follow_up
from trpg.engine.ai.summon import (
    summon_gains,
)
from trpg.engine.ai.terrain import terrain_gains
from trpg.engine.ai.utility.position import (
    _cover_objects_near_enemies,
    _enemies,
    _harmful,
    _in_cover,
)
from trpg.engine.ai.variant import cast_form
from trpg.engine.ai.zone import zone_gains
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    FormEntered,
    ObjectDamaged,
    ShieldGained,
    StacksChanged,
    StatusApplied,
    StatusRemoved,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.ids import PRONE
from trpg.engine.preview import DamageRange, Preview
from trpg.engine.rules.footprint import unit_dist
from trpg.engine.rules.geometry import (
    XY,
)
from trpg.engine.rules.movement import (
    is_deadly,
)
from trpg.engine.rules.statuses import shield_amount
from trpg.engine.skills.targeting import (
    skill_mana_cost,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface, UnitId

_DEFEND_RADIUS = 6
_POSSIBLE_KILL_DIVISOR = 4
_ATTACK_CAUSES = ("attack",)
_SURFACE_HARM = 8
"""讓友方站上有害的新表面的扣分：相當於這麼多點傷害（乘上 ``friendly_fire``）。"""


def _last_cause(events: tuple[EventBase, ...]) -> dict[UnitId, str]:
    cause: dict[UnitId, str] = {}
    for e in events:
        if isinstance(e, DamageDealt):
            cause[e.target_id] = e.cause
    return cause


def _useful_damage(damage: DamageRange, hit: Fraction, hp: int) -> Fraction:
    """命中時有用的傷害：超過目標剩餘 HP 的部分是浪費（擊倒另由 ``kill`` 計分）。"""
    return min(damage.expected_if_hit, Fraction(hp)) * hit


def _has_usable_spell(state: BattleState, unit: UnitState) -> bool:
    """單位有法力足夠的法術技（不看冷卻與 AP；沉默只對這樣的單位有價值）。"""
    rules = state.ruleset
    for sid in sorted(unit.all_skills):
        skill = rules.skill_def(sid)
        mana = skill_mana_cost(rules.core, unit, skill)
        if skill.is_active and skill.category == "spell" and unit.mana >= mana:
            return True
    return False


def _wasted_on(state: BattleState, status_id: str, target: UnitState) -> bool:
    """狀態對這個目標沒有價值：沉默（``blocks_spells``）施加在沒有可用法術技的單位上。"""
    return state.ruleset.status_def(status_id).blocks_spells and not _has_usable_spell(
        state, target
    )


def _status_gains(
    state: BattleState,
    actor: UnitState,
    p: Preview,
    profile: AiProfile,
    hit: Fraction,
    *,
    only: UnitId | None = None,
) -> Fraction:
    """對敵人施加狀態的收益。

    - 不需要抵抗判定的狀態（出現在 ``min`` 的 ``StatusApplied``）：``hit`` × 價值；
    - 需要抵抗判定的狀態（``TargetPreview.status_chances``）：該目標的命中率 × 施加成功率 × 價值，
      目標已帶有該狀態時不算（重複施加只是刷新）；
    - 價值：``status_values`` 有列出的狀態＝``damage`` 權重 × 等值傷害點數，其他用 ``status`` 權重；
      沉默施加在沒有可用法術技的目標上價值為 0（Phase 2D-2）。
    """
    w, values = profile.weights, profile.status_values

    def value(status_id: str, target: UnitState) -> Fraction:
        points = values.get(status_id)
        if points is not None and _wasted_on(state, status_id, target):
            return Fraction(0)
        return Fraction(w.status) if points is None else Fraction(w.damage * points)

    gains = Fraction(0)
    applied = {
        (e.target_id, e.status_id)
        for e in p.min_events
        if isinstance(e, StatusApplied)
        and e.target_id in state.units
        and state.units[e.target_id].team is not actor.team
        and (only is None or e.target_id == only)
    }
    for target_id, status_id in sorted(applied):
        gains += hit * value(status_id, state.units[target_id])
    for t in p.targets:
        if t.ally or (only is not None and t.unit_id != only):
            continue
        target = state.units[t.unit_id]
        for chance in t.status_chances:
            if not target.has_status(chance.status_id):
                gains += t.hit_chance * chance.apply_chance * value(chance.status_id, target)
    return gains


def _support_gains(state: BattleState, p: Preview, profile: AiProfile) -> Fraction:
    """友方支援的收益（Phase 2D-1）：護盾、增益與淨化。

    - 護盾：``shield`` × 實際增加的吸收量（新吸收量 − 原吸收量，下限 0；取最少與最多後果的平均）；
    - 增益（``ally_status_values``）：``support`` × 價值 × 新增的持續比例
      （新持續 − 剩餘 ÷ 新持續，下限 0；沒有預設持續的狀態＝尚未帶有時 1，已帶有 0）；
      目標在動作後倒下時為 0；
    - 淨化：``support`` × 被移除的每個狀態在 ``status_values`` 的價值（沒列出的用 3）。
    """
    w = profile.weights
    actor = state.units[p.action.unit_id]
    gains = Fraction(0)
    if w.shield:
        gained = Fraction(0)
        for events in (p.min_events, p.max_events):
            for e in events:
                if isinstance(e, ShieldGained) and state.units[e.unit_id].team is actor.team:
                    gained += max(0, e.total - shield_amount(state.ruleset, state.units[e.unit_id]))
        gains += w.shield * gained / 2
    if w.support:
        gains += _buff_gains(state, actor, p, profile)
    return gains


def _buff_gains(state: BattleState, actor: UnitState, p: Preview, profile: AiProfile) -> Fraction:
    """友方增益與淨化的收益（:func:`_support_gains` 的後半）。"""
    w = profile.weights
    gains = Fraction(0)
    after = p.min_state
    for e in p.min_events:
        if isinstance(e, StatusApplied):
            target = state.units.get(e.target_id)
            points = profile.ally_status_values.get(e.status_id)
            if target is None or target.team is not actor.team or points is None:
                continue
            if not after.units[e.target_id].alive:
                continue
            current = target.get_status(e.status_id)
            if e.duration is None:
                share = Fraction(0 if current is not None else 1)
            else:
                remaining = 0 if current is None or current.remaining is None else current.remaining
                share = Fraction(max(0, e.duration - remaining), e.duration)
            gains += w.support * points * share
        elif isinstance(e, StatusRemoved) and e.reason == "cleansed":
            target = state.units.get(e.target_id)
            if target is not None and target.team is actor.team:
                gains += w.support * profile.status_values.get(e.status_id, 3)
        elif isinstance(e, FormEntered) and e.unit_id == actor.id:  # 進入形態（3J-1a）
            rotating = state.units[actor.id].form is not None  # 形態輪替（3J-1b）
            gains += w.support * (
                profile.form.rotate_value if rotating else profile.form.enter_value
            )
    return gains


@dataclass(frozen=True)
class _GainFrame:
    """一次預覽收益計算共用的資料。``only`` 給定時只計入對該單位（敵人）的收益。"""

    state: BattleState
    actor: UnitState
    p: Preview
    profile: AiProfile
    only: UnitId | None
    hit: Fraction
    primary: UnitId | None
    """攻擊的主要目標（有精確期望傷害時）。"""
    skill_primary: dict[UnitId, bool]
    """技能中有精確期望傷害的敵方目標。"""

    @property
    def w(self) -> AiWeights:
        return self.profile.weights

    def is_enemy(self, uid: UnitId) -> bool:
        units = self.state.units
        return units[uid].team is not self.actor.team if uid in units else False

    def counts(self, uid: UnitId) -> bool:
        """這個單位的收益是否計入（集火時只計目標）。"""
        return self.only is None or uid == self.only


def _gain_frame(
    state: BattleState, actor: UnitState, p: Preview, profile: AiProfile, only: UnitId | None
) -> _GainFrame:
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    if p.displace_chance is not None:
        hit *= p.displace_chance  # 位移他人：收益只在位移成功時發生（Phase 3D-2b）
    skill_primary: dict[UnitId, bool] = {}
    if isinstance(p.action, UseSkill):
        foes = [t for t in p.targets if not t.ally]
        if foes:
            hit = sum((t.hit_chance for t in foes), Fraction(0)) / len(foes)
        skill_primary = {t.unit_id: True for t in foes if t.damage is not None}
    primary = None
    if isinstance(p.action, Attack) and p.action.target_id is not None and p.damage is not None:
        primary = p.action.target_id
    return _GainFrame(state, actor, p, profile, only, hit, primary, skill_primary)


def _event_damage(f: _GainFrame) -> tuple[Fraction, Fraction, Fraction]:
    """預覽事件中、不屬於精確期望傷害的傷害（取 min／max 兩種結果的總和）：
    對敵人的、其中的環境傷害、對友方的。被護盾吸收的不算。"""
    other_enemy = Fraction(0)
    env_enemy = Fraction(0)
    friendly = Fraction(0)
    for events in (f.p.min_events, f.p.max_events):
        seen: set[UnitId] = set()
        for e in events:
            if not isinstance(e, DamageDealt) or e.cause == "deadly_terrain":
                continue  # 致命地形的「傷害」是擊倒本身，由 kill／env_kill 計分
            first = e.target_id not in seen
            if e.cause == "attack" and (
                (e.target_id == f.primary and first) or e.target_id in f.skill_primary
            ):
                seen.add(e.target_id)
                continue
            if f.is_enemy(e.target_id):
                if f.counts(e.target_id):
                    other_enemy += e.amount - e.absorbed
                    if e.cause not in _ATTACK_CAUSES:
                        env_enemy += e.amount - e.absorbed
            elif e.target_id in f.state.units and f.only is None:
                friendly += e.amount - e.absorbed
    return other_enemy, env_enemy, friendly


def _shield_broken(f: _GainFrame) -> Fraction:
    """打掉敵人護盾的量（預覽事件裡對敵人的 ``absorbed``，含主要目標；取 min／max 兩種結果的總和）。

    6F-3（12B 對照 #7）：傷害收益只算扣到 HP 的部分，敵人有補師一直上盾時，盜賊的匕首全被護盾吸收、
    攻擊收益變 0，每回合都選「守護」，戰鬥拖到 11 輪。打掉護盾和替自己人加盾等價（同一個
    ``shield`` 權重），所以照護盾收益的算法給分。"""
    broken = Fraction(0)
    for events in (f.p.min_events, f.p.max_events):
        for e in events:
            if (
                isinstance(e, DamageDealt)
                and e.absorbed > 0
                and f.is_enemy(e.target_id)
                and f.counts(e.target_id)
            ):
                broken += e.absorbed
    return broken


def _damage_gains(f: _GainFrame) -> Fraction:
    """傷害：主要傷害用精確期望；其他取 min／max 平均 × 命中率；對友方的傷害扣分；打掉敵人的護盾
    照 ``shield`` 權重給分（:func:`_shield_broken`，6F-3）。"""
    w, state = f.w, f.state
    gains = Fraction(0)
    if f.p.damage is not None and f.primary is not None and f.counts(f.primary):
        gains += w.damage * _useful_damage(f.p.damage, f.hit, state.units[f.primary].hp)
    for t in f.p.targets:  # 技能：每個目標各自的命中率與期望傷害
        if t.damage is not None and not t.ally and f.counts(t.unit_id):
            gains += w.damage * _useful_damage(t.damage, t.hit_chance, state.units[t.unit_id].hp)
    other_enemy, env_enemy, friendly = _event_damage(f)
    gains += w.damage * f.hit * other_enemy / 2
    gains += w.env_damage * f.hit * env_enemy / 2
    gains -= w.friendly_fire * friendly / 2
    gains += w.shield * f.hit * _shield_broken(f) / 2
    return gains


def _ally_gains(f: _GainFrame) -> Fraction:
    """治療、友方增益、層數與陷阱（集火時不計）。"""
    if f.only is not None:
        return Fraction(0)
    p, state = f.p, f.state
    healed = sum(Fraction(lo + hi, 2) for uid, lo, hi in p.healed if uid in state.units)
    gains = Fraction(f.w.heal) * healed
    if isinstance(p.action, UseSkill):  # 防禦動作的 defending 由 ``defend`` 權重計分，不重複算
        gains += _support_gains(state, p, f.profile)
        gains += _stack_gains(state, f.actor, p, f.profile, f.hit)
        gains += _trap_gains(state, p, f.profile)
        gains += summon_gains(state, f.actor, p.min_events, f.profile)  # 召喚（Phase 3D-4a）
        gains += zone_gains(state, f.actor, p.min_events, f.profile)  # 持續區域（Phase 3D-5）
        gains += rune_gains(state, f.actor, p.min_events, f.profile)  # 先刻（Phase 3-23）
        gains += _rune_read_gains(state, f.actor, p, f.profile)  # 再引（Phase 3-23）
    return gains


def _kill_gains(f: _GainFrame) -> Fraction:
    """擊倒：確定的 ×命中率，只是可能的 ×命中率 ÷4；倒下的是友方則扣分。"""
    p, w = f.p, f.w
    gains = Fraction(0)
    certain_down = {e.unit_id for e in p.min_events if isinstance(e, UnitDowned)}
    possible_down = {e.unit_id for e in p.max_events if isinstance(e, UnitDowned)} - certain_down
    causes = _last_cause(p.max_events) | _last_cause(p.min_events)
    for uid, factor in [(u, f.hit) for u in sorted(certain_down)] + [
        (u, f.hit / _POSSIBLE_KILL_DIVISOR) for u in sorted(possible_down)
    ]:
        if f.only is not None and uid != f.only:
            continue
        if f.is_enemy(uid):
            gains += w.kill * factor
            if causes.get(uid, "attack") not in _ATTACK_CAUSES:
                gains += w.env_kill * factor
        elif uid in f.state.units:
            gains -= w.kill * factor
    return gains


def _push_gains(f: _GainFrame) -> Fraction:
    """被強制位移的敵人、施加的狀態，以及技能附帶的擊倒（倒地）。"""
    p, w = f.p, f.w
    pushed = {
        e.unit_id
        for e in p.min_events
        if isinstance(e, UnitMoved)
        and e.mode == "forced"
        and f.is_enemy(e.unit_id)
        and f.counts(e.unit_id)
    }
    gains = w.push * f.hit * len(pushed)
    gains += _status_gains(f.state, f.actor, p, f.profile, f.hit, only=f.only)
    for t in p.targets:  # 技能附帶的擊倒：命中率 × 對抗成功率（預覽的 min 只視為失敗）
        if (
            t.knock_chance is not None
            and not t.ally
            and f.counts(t.unit_id)
            and not f.state.units[t.unit_id].has_status(PRONE)
        ):
            gains += w.status * t.hit_chance * t.knock_chance
    return gains


def _surface_gains(f: _GainFrame) -> Fraction:
    """站在有害表面上的敵人數變化；技能讓友方站上有害的新表面則扣分。"""
    state, actor, team = f.state, f.actor, f.actor.team
    after = f.p.min_state
    before_harm = sum(1 for u in _enemies(state, actor) if f.counts(u.id) and _harmful(state, u.xy))
    after_harm = sum(
        1
        for u in after.living_units()
        if u.team is not team and f.counts(u.id) and _harmful(after, u.xy)
    )
    gains = f.w.surface * f.hit * (after_harm - before_harm)
    gains += _oil_setup_gains(f)
    if isinstance(f.p.action, UseSkill) and f.only is None:  # 讓友方站上有害的新表面（火、毒……）
        gains -= (
            f.w.friendly_fire
            * _SURFACE_HARM
            * (_harmed_allies(after, actor) - _harmed_allies(state, actor))
        )
    return gains


def _oil_setup_gains(f: _GainFrame) -> Fraction:
    """鋪油再點火的兩步連招（Phase 3D-3，最簡單的近似）：投擲的油桶摔破漏油、不爆炸，行動者有火焰
    技能時，站在油上的敵人增加的數目 × ``surface`` 的一半（油本身沒有傷害，不算有害表面）。"""
    action = f.p.action
    if not isinstance(action, UseSkill) or f.only is not None:
        return Fraction(0)
    if not any(e.type == HURL_OBJECT for e in effective_skill(f.state, action).effects):
        return Fraction(0)
    if not has_fire_follow_up(f.state, f.actor):
        return Fraction(0)
    after = f.p.min_state

    def on_oil(state: BattleState, units: Iterable[UnitState]) -> int:
        return sum(1 for u in units if state.tile(*u.xy).surface is Surface.OIL)

    before_n = on_oil(f.state, (u for u in _enemies(f.state, f.actor) if f.counts(u.id)))
    after_n = on_oil(
        after,
        (u for u in after.living_units() if u.team is not f.actor.team and f.counts(u.id)),
    )
    return f.w.surface * f.hit * (after_n - before_n) / 2


def _tile_value(f: _GainFrame, state: BattleState, uid: UnitId, xy: XY) -> Fraction:
    """單位 ``uid`` 站在 ``xy`` 對敵方的價值（位移他人的收益用）：敵人在致命地形上是擊倒
    （``kill`` ＋ ``env_kill``）、友方在致命地形上是損失（``kill``），其中 1/4 已由
    ``_kill_gains`` 計入，所以這裡取 3/4；有害表面取 ``surface``。"""
    w = f.w
    if is_deadly(state, xy):
        weight = w.kill + w.env_kill if f.is_enemy(uid) else w.kill
        return Fraction(weight * (_POSSIBLE_KILL_DIVISOR - 1), _POSSIBLE_KILL_DIVISOR)
    return Fraction(w.surface) if _harmful(state, xy) else Fraction(0)


def _displace_gains(f: _GainFrame) -> Fraction:
    """被傳送或互換的單位（預覽最多後果的模擬）走到更危險或更安全的格子：敵人走向危險、友方
    離開危險是收益，反過來是損失（Phase 3D-2b；乘上位移成功率，已含在 ``f.hit``）。"""
    if f.only is not None or not isinstance(f.p.action, UseSkill):
        return Fraction(0)
    after, state = f.p.max_state, f.state
    moved: set[UnitId] = set()
    for m in f.p.moves:
        if m.kind in ("teleport", "swap"):
            moved.update(uid for uid in (m.unit_id, m.other_id) if uid is not None)
    gains = Fraction(0)
    for uid in sorted(moved):
        if uid not in state.units or uid not in after.units:
            continue
        delta = _tile_value(f, after, uid, after.units[uid].xy) - _tile_value(
            f, state, uid, state.units[uid].xy
        )
        gains += delta if f.is_enemy(uid) else -delta
        mover, landed = state.units[uid], after.units[uid]
        if not f.is_enemy(uid) and is_hurt(mover):  # 快倒下的隊友離開敵人（兩格內的敵人數變少）
            gains += f.w.kill * (
                exposure(state, mover, mover.xy) - exposure(after, landed, landed.xy)
            )
    return f.hit * gains


def _defend_gains(f: _GainFrame) -> Fraction:
    """防禦動作：每名 6 格內的敵人。"""
    if not isinstance(f.p.action, Defend) or f.only is not None:
        return Fraction(0)
    near = sum(1 for e in _enemies(f.state, f.actor) if unit_dist(f.actor, e) <= _DEFEND_RADIUS)
    return Fraction(f.w.defend * near)


def _gains(
    state: BattleState,
    actor: UnitState,
    p: Preview,
    profile: AiProfile,
    only: UnitId | None = None,
) -> Fraction:
    """預覽收益。``only`` 給定時只計入對該單位（敵人）的收益——集火指令的加成用。"""
    f = _gain_frame(state, actor, p, profile, only)
    gains = _damage_gains(f) + _ally_gains(f) + _kill_gains(f) + _push_gains(f)
    gains += _surface_gains(f) + _displace_gains(f)
    gains += f.w.damage * priority_points(  # 先打補師、打斷強招（Phase 5A-M1）
        state, actor, p.min_events, p.max_events, f.hit, profile.rewrite, only
    )
    if only is None:  # 打散陣型（Phase 5A-M2）
        gains += f.w.damage * f.hit * formation_break(state, p.min_state, actor, profile.rewrite)
    gains -= f.w.damage * share_discount(  # 連心：分給同門的傷害打折（Phase 5A-M2）
        state, actor, p.min_events, p.max_events, f.hit, profile.rewrite, only
    )
    if f.w.expose or f.w.cover_damage:
        gains += _cover_gains(state, actor, p, f.w, f.hit, only)
    if only is None and isinstance(p.action, UseSkill):  # 純地形技能（3T-5）
        gains += terrain_gains(state, p.min_state, actor, p.min_events, profile)
    return gains + _defend_gains(f)


def _stack_gains(
    state: BattleState, actor: UnitState, p: Preview, profile: AiProfile, hit: Fraction
) -> Fraction:
    """累積層數的收益（Phase 2E-3）：每一層 ＝ ``damage`` 權重 × 該層數的 ``ai_value`` × 命中率。
    自己身上與敵人身上的層數都算；消耗層數不扣分——消耗的價值已經包含在終結技預覽的傷害加成裡
    （預覽跑的是真的引擎），所以有層數時終結技的分數自然比較高。"""
    gains = Fraction(0)
    w = profile.weights
    for e in p.max_events:
        if not isinstance(e, StacksChanged) or e.reason != "gained" or e.unit_id not in state.units:
            continue
        mine = e.unit_id == actor.id
        if not mine and state.units[e.unit_id].team is actor.team:
            continue
        gains += (
            w.damage * hit * state.ruleset.stack_def(e.stack_id).ai_value * (e.after - e.before)
        )
    return gains


def _trap_gains(state: BattleState, p: Preview, profile: AiProfile) -> Fraction:
    """放置陷阱的收益（Phase 2E-3，粗估）：陷阱觸發時的效果（傷害骰平均值或武器倍率、狀態的價值）
    × 範圍波及的預期敵人數 × ``trap_likelihood_permille``（陷阱真的會被踩中／波及的機率）。
    放置本身在預覽裡沒有任何效果，所以收益完全來自這個估計。"""
    assert isinstance(p.action, UseSkill)
    skill = state.ruleset.skill_def(p.action.skill_id)
    if skill.trap is None:
        return Fraction(0)
    w, values = profile.weights, profile.status_values
    value = Fraction(0)
    for spec in skill.effects:
        if spec.type == "damage":
            if spec.dice is not None:
                value += w.damage * Fraction(spec.dice.count * (spec.dice.sides + 1), 2)
            else:
                reference = state.ruleset.core.budget_reference_weapon_damage
                value += w.damage * Fraction((spec.multiplier_permille or 1000) * reference, 1000)
        elif spec.type == "apply_status" and spec.status is not None:
            points = values.get(spec.status)
            value += Fraction(w.status) if points is None else Fraction(w.damage * points)
        elif spec.type == "create_surface":
            value += w.surface
    return (
        value
        * profile.trap.shape_factor(skill.trap.shape)
        * profile.trap_likelihood_permille
        / 1000
    )


def _harmed_allies(state: BattleState, actor: UnitState) -> int:
    """站在有害表面上的友方數（不含行動者；行動者自己的位置由 ``hazard`` 計分）。"""
    return sum(
        1
        for u in state.living_units()
        if u.team is actor.team and u.id != actor.id and _harmful(state, u.xy)
    )


def _cover_gains(  # noqa: PLR0917
    state: BattleState,
    actor: UnitState,
    p: Preview,
    w: AiWeights,
    hit: Fraction,
    only: UnitId | None = None,
) -> Fraction:
    """推離掩護（``expose``）與破壞敵人的掩護物（``cover_damage``）的收益。"""
    team = actor.team
    before = sum(
        1 for e in _enemies(state, actor) if (only is None or e.id == only) and _in_cover(state, e)
    )
    exposed = Fraction(0)
    for after in (p.min_state, p.max_state):
        now = sum(
            1
            for e in after.living_units()
            if e.team is not team and (only is None or e.id == only) and _in_cover(after, e)
        )
        exposed += before - now
    gains = w.expose * hit * exposed / 2
    if w.cover_damage and only is None:
        shields = _cover_objects_near_enemies(state, actor)
        if shields:
            dealt = sum(
                e.amount
                for events in (p.min_events, p.max_events)
                for e in events
                if isinstance(e, ObjectDamaged) and e.object_id in shields
            )
            gains += w.cover_damage * hit * Fraction(dealt, 2)
    return gains


def effective_skill(state: BattleState, action: UseSkill) -> SkillDef:
    """動作實際結算效果的技能：``copy_skill`` 帶著 ``copy_cast`` 時是被複製的技能（Phase 3C-4b），
    其他是動作自己的技能。"""
    pick = action.copy_cast
    if pick is not None:
        return state.ruleset.skill_def(pick.skill_id)
    return cast_form(state, action)  # 戰場變奏（3-25a）：目標點選出的型態


def _rune_read_gains(
    state: BattleState, actor: UnitState, p: Preview, profile: AiProfile
) -> Fraction:
    """讀取技能打到站在自己符文上的敵人的額外加分（Phase 3-23）。"""
    action = p.action
    if not isinstance(action, UseSkill):
        return Fraction(0)
    return read_gains(state, actor, effective_skill(state, action), p, profile)
