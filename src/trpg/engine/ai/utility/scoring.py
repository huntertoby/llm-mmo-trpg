"""效用 AI 的動作評分：:func:`score_action`、改寫類技能的事件分數、戰術指令加成、技能成本與
防禦／撤離／翻越的直接分數。

自 :mod:`trpg.engine.ai.utility` 拆出（Phase R1c），內容未改。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import (
    AiProfile,
    AiWeights,
    BasicActionAiRules,
    RewriteAiRules,
    RunAiRules,
)
from trpg.content.skills import (
    CHEAT_DEATH,
    CHEAT_DEATH_STATUS,
    DELAYED_DAMAGE,
    DISPEL,
    EXTRA_REACTION,
    GRANT_AP,
    GRANT_SKILL,
    REDIRECT_DAMAGE,
    REDIRECT_STATUS,
    RESET_COOLDOWN,
    RESTORE_RESOURCE,
    REVEAL,
    REVIVE,
    STEAL_BUFF,
    TIME_BOMB,
    SkillDef,
)
from trpg.engine.actions import (
    Action,
    Attack,
    EndTurn,
    UseSkill,
)
from trpg.engine.ai.gamble import cautious, on_miss_cost
from trpg.engine.ai.leader import far_target_extra
from trpg.engine.ai.parts import guard_face_extra
from trpg.engine.ai.priority import (
    delayed_heal_points,
)
from trpg.engine.ai.self_costs import self_cost_gate
from trpg.engine.ai.utility.gains import _DEFEND_RADIUS, _gains
from trpg.engine.ai.utility.position import (
    ActionScore,
    OrderContext,
    _enemies,
    _order_weights,
    _Scene,
    _scene,
    _Walk,
    position_value,
)
from trpg.engine.ai.variant import cast_form
from trpg.engine.bombs import blast_tiles
from trpg.engine.events import (
    ApGranted,
    ApRefunded,
    DamageDealt,
    EventBase,
    FollowupCharged,
    ReactionsGranted,
    ResourceRestored,
    SkillActivated,
    SkillCooldownChanged,
    SkillGranted,
    StatusApplied,
    StatusRemoved,
    TrapRevealed,
    UnitRevived,
)
from trpg.engine.ids import OVERDRAWN
from trpg.engine.preview import Preview, preview
from trpg.engine.rules.combat import (
    attack_reach,
)
from trpg.engine.rules.footprint import dist_to, is_giant, unit_dist
from trpg.engine.rules.geometry import (
    XY,
)
from trpg.engine.rules.movement import (
    available_move_budget,
    path_map,
)
from trpg.engine.skills.targeting import (
    hp_cost,
    skill_mana_cost,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId


def score_action(
    state: BattleState,
    action: Action,
    profile: AiProfile,
    *,
    before: Fraction | None = None,
    orders: OrderContext | None = None,
    walk: _Walk | None = None,
) -> ActionScore:
    """單一動作的分數（``EndTurn`` 固定為 0），以完整 ``preview`` 計算。

    ``before`` 為行動者在 ``state`` 的位置價值（省略時重新計算）；``orders`` 為行動者適用的
    戰術指令（:func:`resolve_orders`；``None`` 時與沒有指令的分數完全相同）。
    """
    if isinstance(action, EndTurn):
        return ActionScore(action, Fraction(0), None)
    w = _order_weights(profile.weights, orders)
    if w is not profile.weights:
        profile = profile.model_copy(update={"weights": w})
    actor = state.units[action.unit_id]
    p = preview(state, action)
    if walk is None:
        walk = _scene(state, actor, orders).walk
    if before is None:
        before = position_value(state, actor.id, w, orders, walk=walk)
    if p.gamble is None:
        score = _preview_score(state, action, p, profile, before=before, orders=orders, walk=walk)
    else:  # 賭注（Phase 3D-7a）：每個分支各自評分，依機率加權
        score = sum(
            (
                b.chance
                * _preview_score(
                    state, action, b.preview, profile, before=before, orders=orders, walk=walk
                )
                for b in p.gamble.branches
            ),
            Fraction(0),
        )
    if isinstance(action, UseSkill):
        skill = state.ruleset.skill_def(action.skill_id)
        score -= on_miss_cost(actor, skill, p, profile)  # 失手反噬（Phase 3D-7a）
        score = cautious(state, actor, skill, score, profile)
        score = self_cost_gate(state, actor, skill, p, profile, score=score)  # 自己付的代價（3-50）
    return ActionScore(action, score, p)


def _preview_score(
    state: BattleState,
    action: Action,
    p: Preview,
    profile: AiProfile,
    *,
    before: Fraction,
    orders: OrderContext | None,
    walk: _Walk | None,
) -> Fraction:
    """一個預覽的分數：預覽收益 ＋ 命中率 × 位置價值的變化，扣技能的機會成本（賭注的每個分支各算
    一次，結果再依機率加權）。"""
    w = profile.weights
    actor = state.units[action.unit_id]
    after = position_value(p.min_state, actor.id, w, orders, walk=walk)
    # 位置變化只在動作成功時發生（攻擊、技巧動作乘上命中率／成功率）
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    score = _lock_gains(state, actor, p, profile) + hit * (after - before)
    if orders is not None:
        score += _order_bonus(state, actor, p, profile, orders)
    if isinstance(action, UseSkill):
        score -= skill_cost(
            state, actor, action, w, {**profile.status_values, **profile.self_status_values}
        )
        score += _rewrite_gains(state, actor, action, p, profile)
        score += w.multi_target * extra_targets(state, actor, p)
    elif isinstance(action, Attack):  # 蓄力吐息（3J-2）：開始蓄力的收益是預計範圍內的敵人
        score += profile.weights.damage * _delayed_points(state, actor, p, profile.rewrite)
    if w.prefer_far_from_leader or (w.guard_face_bonus and is_giant(actor)):
        score += hit * _target_bias(state, actor, p, w)  # GB-3：打誰（T17、T18）
    return score


def _target_bias(state: BattleState, actor: UnitState, p: Preview, w: AiWeights) -> int:
    """挑目標的偏好（GB-3）：殼縫餘燼蜥打離頭目遠的人（T17，:func:`far_target_extra`）、巨型頭目
    打貼著快破部位的人（T18，:func:`guard_face_extra`）。打到的人＝預覽最多後果裡受到傷害的單位
    （以動作前的位置算）。"""
    hit_ids = sorted({e.target_id for e in p.max_events if isinstance(e, DamageDealt)})
    victims = tuple(
        u for uid in hit_ids if (u := state.units.get(uid)) is not None and u.id != actor.id
    )
    return far_target_extra(state, actor, w, victims) + guard_face_extra(state, actor, w, victims)


def _lock_gains(state: BattleState, actor: UnitState, p: Preview, profile: AiProfile) -> Fraction:
    """預覽收益；瞄準預告（RG-1）改用「現在就射出」的預覽（``p.lock_fire``）× ``lock_on_permille``
    （下回合才射、對手可以應對）。"""
    if p.lock_fire is None:
        return _gains(state, actor, p, profile)
    gains = _gains(state, actor, p.lock_fire, profile)
    return gains * profile.rewrite.lock_on_permille / 1000


def extra_targets(state: BattleState, actor: UnitState, p: Preview) -> Fraction:
    """範圍技（BAL-5 B1）預期打到的敵人數超過 1 的部分：要命中判定的敵人各算命中率，不用判定、
    在最少結果裡就受傷的敵人算 1；扣掉其中最大的一個（第一個目標本來就由傷害收益計分）。"""
    chances: dict[UnitId, Fraction] = {
        t.unit_id: t.hit_chance for t in p.targets if not t.ally and t.damage is not None
    }
    for e in p.min_events:
        if (
            isinstance(e, DamageDealt)
            and e.target_id not in chances
            and e.target_id in state.units
            and state.units[e.target_id].team is not actor.team
        ):
            chances[e.target_id] = Fraction(1)
    if len(chances) < 2:  # noqa: PLR2004
        return Fraction(0)
    return sum(chances.values(), Fraction(0)) - max(chances.values())


_REWRITE_SCORED = frozenset(
    {
        GRANT_AP,
        RESET_COOLDOWN,
        CHEAT_DEATH,
        REDIRECT_DAMAGE,
        EXTRA_REACTION,
        RESTORE_RESOURCE,
        STEAL_BUFF,
        DISPEL,
        REVEAL,
        REVIVE,
        DELAYED_DAMAGE,
        GRANT_SKILL,
    }
)
"""預覽事件之外還要另外加分的改寫規則型原語（:func:`_rewrite_gains`）。"""


def _rewrite_gains(
    state: BattleState, actor: UnitState, action: UseSkill, p: Preview, profile: AiProfile
) -> Fraction:
    """改寫規則型原語的收益減去源力成本（Phase 3C-4a；``ai_profiles.yaml`` 的 ``rewrite``，
    × ``damage`` 權重）。最簡單的近似：

    - ``grant_ap``：獲得的 AP × ``ap_points``（≈ 多一次動作的價值；與其他動作一樣不扣這次動作
      本身花的 AP）；給友方的 AP 再 × ``ally_ap_permille``（所以優先給自己）；
    - ``reset_cooldown``：被重置的冷卻回合數 × ``cooldown_points``；
    - ``cheat_death``：``undying_points`` × 目標已損失 HP 的比例（HP 越低越值得；已帶有則 0）；
    - ``redirect_damage``：``redirect_points`` × 目標已損失 HP 的比例（施放者 HP 不到一半為 0）；
    - ``extra_reaction``：每個額外次數 ``reaction_points``（目標有反應規則時）；
    - 常駐類傳說的啟動（Phase 3D-6）：``activation_round_points`` × 生效輪數（限時為持續輪數、
      整場為 ``activation_battle_rounds``）；
    - 源力：每點扣 ``source_points``。

    ``copy_skill`` 沒有額外收益：預覽已包含複製的技能自己的效果（:func:`effective_skill`）。
    """
    skill = cast_form(state, action)
    types = {e.type for e in skill.effects}
    rules = profile.rewrite
    source = skill.cost.source or 0
    on_kill = any(e.on_kill for e in skill.effects)  # 擊殺時效果（3D-8b）
    watch = _watch_statuses(state, skill)  # 進入監視（3D-8c）
    delayed = skill.followup is not None and skill.followup.when == "delayed"  # 延遲段（3F-4b）
    if not types & _REWRITE_SCORED and not (source or on_kill or watch or delayed):
        return Fraction(0)
    points = Fraction(-rules.source_points * source)
    points += _overwatch_points(state, actor, watch, rules)
    for e in p.min_events:
        points += _rewrite_event_points(state, actor, e, types, rules)
    points += _bomb_points(state, actor, skill, p, rules)
    points += _delayed_points(state, actor, p, rules)
    revived = sum(1 for e in p.min_events if isinstance(e, UnitRevived) and e.source_id == actor.id)
    points += rules.revive_points * revived  # 復活（3D-8b）
    points += _kill_points(actor, skill, p, rules)
    return profile.weights.damage * points


def _watch_statuses(state: BattleState, skill: SkillDef) -> set[str]:
    """技能替施放者施加的「監視」類狀態（內建反應的 ``requires_status``；3D-8c）。"""
    needed = {d.requires_status for d in state.ruleset.reactions.reactions if d.requires_status}
    return {
        e.status
        for e in skill.effects
        if e.type == "apply_status" and e.status in needed and (e.affects or "self") == "self"
    }


def _overwatch_points(
    state: BattleState, actor: UnitState, watch: set[str], rules: RewriteAiRules
) -> Fraction:
    """進入監視的收益（3D-8c）：下一次敵人行動時，走得進武器射程（武器射程 ＋ 速度）的敵人數（最多
    ``overwatch_max_enemies`` 個，已經在射程內的不算——直接攻擊比較划算）× ``overwatch_points``；
    已經有監視狀態時為 0。"""
    if not watch or any(actor.has_status(s) for s in watch):
        return Fraction(0)
    reach = actor.weapon.range
    near = sum(1 for e in _enemies(state, actor) if reach < unit_dist(actor, e) <= reach + e.speed)
    return Fraction(rules.overwatch_points * min(near, rules.overwatch_max_enemies))


def _kill_points(actor: UnitState, skill: SkillDef, p: Preview, rules: RewriteAiRules) -> Fraction:
    """擊殺時效果（``on_kill``，3D-8b）的收益：返還的 AP × ``refund_ap_points``、本技能冷卻歸零 ×
    ``cooldown_points`` × 技能的冷卻回合；只出現在「最多後果」的預覽（能擊殺的情形），所以再 ×
    命中率近似。"""
    total = Fraction(0)
    for e in p.max_events:
        if isinstance(e, ApRefunded) and e.unit_id == actor.id:
            total += rules.refund_ap_points * e.amount
        elif (
            isinstance(e, SkillCooldownChanged)
            and e.unit_id == actor.id
            and e.skill_id == skill.id
            and e.remaining == 0
        ):
            total += rules.cooldown_points * (skill.cost.cooldown or 0)
    return total * (p.hit_chance if p.hit_chance is not None else Fraction(1))


def _bomb_points(
    state: BattleState, actor: UnitState, skill: SkillDef, p: Preview, rules: RewriteAiRules
) -> Fraction:
    """定時炸彈（3D-8b）的收益：骰子平均 ×（炸彈半徑內的敵人數 − 友方數，含施放者）×
    ``bomb_points_permille``——炸彈附在敵人身上時，以目前的位置估計波及的人（它會移動，所以只是
    近似）。預覽沒有施加炸彈（失手）時為 0。"""
    spec = next((e for e in skill.effects if e.type == DELAYED_DAMAGE), None)
    if spec is None or spec.dice is None:
        return Fraction(0)
    average = Fraction(spec.dice.count * (spec.dice.sides + 1), 2)
    total = Fraction(0)
    for e in p.min_events:
        if not (isinstance(e, StatusApplied) and e.status_id == TIME_BOMB):
            continue
        carrier = state.units[e.target_id]
        tiles = set(blast_tiles(state, carrier.pos, spec.radius or 0))
        near = [u for u in state.living_units() if u.xy in tiles]
        enemies = sum(1 for u in near if u.team is not actor.team)
        friends = len(near) - enemies
        total += average * (enemies - friends) * rules.bomb_points_permille / 1000
    return total


def _delayed_points(
    state: BattleState, actor: UnitState, p: Preview, rules: RewriteAiRules
) -> Fraction:
    """延遲段（3F-4b）的收益：預覽中開始蓄力（``followup_charged``）時，預計範圍內的（敵人數 −
    友方數）× ``delayed_enemy_points``（第二段是治療時改看受傷的友方，5A-M1）；被攻擊才釋放的
    再 × ``delayed_attacked_permille``。範圍以
    目前的位置推算（敵人會移動，所以只是近似）。"""
    for e in p.min_events:
        if not (isinstance(e, FollowupCharged) and e.unit_id == actor.id):
            continue
        healing = delayed_heal_points(state, actor, e, rules)  # 治療型強招（Phase 5A-M1）
        if healing is not None:
            return healing
        tiles = {(t.x, t.y) for t in e.tiles}
        near = [u for u in state.living_units() if u.xy in tiles and u.id != actor.id]
        enemies = sum(1 for u in near if u.team is not actor.team)
        points = Fraction((2 * enemies - len(near)) * rules.delayed_enemy_points)
        if e.release == "attacked":
            points = points * rules.delayed_attacked_permille / 1000
        return points
    return Fraction(0)


def _rewrite_event_points(
    state: BattleState, actor: UnitState, e: EventBase, types: set[str], rules: RewriteAiRules
) -> Fraction:
    """預覽事件在 :func:`_rewrite_gains` 的加分（數值見 ``ai_profiles.yaml`` 的 ``rewrite``）。"""
    points = Fraction(0)
    if isinstance(e, ApGranted):
        ally = Fraction(rules.ally_ap_permille, 1000)
        points = rules.ap_points * e.amount * (Fraction(1) if e.unit_id == actor.id else ally)
    elif isinstance(e, SkillCooldownChanged) and RESET_COOLDOWN in types and e.remaining == 0:
        points = Fraction(
            rules.cooldown_points * state.units[e.unit_id].cooldowns.get(e.skill_id, 0)
        )
    elif isinstance(e, StatusApplied) and e.status_id in (CHEAT_DEATH_STATUS, REDIRECT_STATUS):
        target = state.units[e.target_id]
        lost = Fraction(target.max_hp - target.hp, target.max_hp)
        if target.team is not actor.team:
            pass
        elif e.status_id == CHEAT_DEATH_STATUS:
            points = (
                Fraction(0)
                if target.has_status(CHEAT_DEATH_STATUS)
                else rules.undying_points * lost
            )
        elif actor.hp * 2 >= actor.max_hp:
            points = rules.redirect_points * lost
    elif isinstance(e, ReactionsGranted) and state.units[e.unit_id].reactions:
        points = Fraction(rules.reaction_points * e.amount)
    elif isinstance(e, ResourceRestored) and state.units[e.unit_id].team is actor.team:
        per_point = rules.mana_points if e.resource == "mana" else rules.cooldown_points
        points = Fraction(per_point * e.amount * (1 if e.resource == "mana" else len(e.skill_ids)))
    elif isinstance(e, StatusRemoved) and e.reason == "stolen":
        points = Fraction(rules.steal_points)
    elif isinstance(e, StatusRemoved) and e.reason == "dispelled":  # 驅散敵方增益（3D-8a）
        points = Fraction(rules.dispel_points)
    elif isinstance(e, TrapRevealed) or (isinstance(e, StatusRemoved) and e.reason == "revealed"):
        points = Fraction(rules.reveal_points)  # 揭露（3D-8a）：敵方陷阱或敵人失去隱蔽
    elif isinstance(e, (SkillGranted, SkillActivated)):  # 暫時獲得技能（3D-8c）、常駐類傳說（3D-6）
        points = _skill_event_points(state, actor, e, rules)
    return points


def _skill_event_points(
    state: BattleState, actor: UnitState, e: SkillGranted | SkillActivated, rules: RewriteAiRules
) -> Fraction:
    """``skill_granted``（暫時獲得技能，3D-8c）與 ``skill_activated``（常駐類傳說，3D-6）的加分。
    給友方或自己的暫時技能 ＝ ``grant_skill_points`` × 每輪預期使用次數 × 持續輪數（只刷新輪數
    不加分）；傳說只算施放者自己的啟動。"""
    if isinstance(e, SkillGranted):
        if e.refreshed or state.units[e.unit_id].team is not actor.team:
            return Fraction(0)
        return Fraction(
            rules.grant_skill_points * rules.grant_skill_uses_permille * e.duration, 1000
        )
    if e.unit_id != actor.id:
        return Fraction(0)
    rounds = (
        rules.activation_battle_rounds if e.expires_round is None else e.expires_round - state.round
    )
    return Fraction(rules.activation_round_points * rounds)


def _order_bonus(
    state: BattleState, actor: UnitState, p: Preview, profile: AiProfile, orders: OrderContext
) -> Fraction:
    """集火與利用環境的收益加成：（倍率 − 1）× 對應的預覽收益。"""
    bonus = Fraction(0)
    if orders.focus is not None:
        extra = Fraction(orders.bonuses.focus_permille - 1000, 1000)
        bonus += extra * _gains(state, actor, p, profile, only=orders.focus)
    w = profile.weights
    if orders.env and (w.env_damage or w.env_kill or w.push or w.surface or w.expose):
        # 這些權重全是 0 的行為模式沒有環境收益可以加成（結果必為 0，省下一次 _gains）
        extra = Fraction(orders.bonuses.environment_permille - 1000, 1000)
        zeroed = {
            key: 0
            for key in (
                "damage",
                "kill",
                "status",
                "friendly_fire",
                "heal",
                "defend",
                "cover_damage",
            )
        }
        env_only = profile.model_copy(
            update={"weights": profile.weights.model_copy(update=zeroed), "status_values": {}}
        )
        bonus += extra * _gains(state, actor, p, env_only)
    return bonus


def skill_cost(
    state: BattleState,
    actor: UnitState,
    action: UseSkill,
    w: AiWeights,
    status_values: dict[str, int] | None = None,
) -> Fraction:
    """技能的機會成本：法力（不回復）、耐力（3H-2）、冷卻（這幾回合不能再用）、HP 代價（算作對
    自己的傷害）與自身狀態代價（Phase 2H-1：``damage`` 權重 × 狀態價值 × 有效回合
    ``duration − 1``，價值取 ``status_values``，沒列出的狀態用 ``status`` 權重，與對敵人施加
    同一狀態的收益對稱）。"""
    skill = state.ruleset.skill_def(action.skill_id)
    cost = Fraction(
        w.mana * skill_mana_cost(state.ruleset.core, actor, skill)
        + Fraction(w.stamina_permille * skill.cost.stamina, 1000)
        + w.cooldown * (skill.cost.cooldown or 0)
        + w.friendly_fire * hp_cost(actor, skill)
    )
    self_status = skill.cost.self_status
    if self_status is not None:
        points = (status_values or {}).get(self_status.status)
        value = w.status if points is None else w.damage * points
        cost += value * (self_status.duration - 1)
    if skill.cost.overdraft is not None:  # 透支（3-50）：下回合少 overdraft AP，約等於少一次出手
        points = (status_values or {}).get(OVERDRAWN)  # 少 1 AP 約等於少半個回合的行動
        cost += (w.status if points is None else w.damage * points) * skill.cost.overdraft
    return cost


def defend_score(state: BattleState, unit: UnitState, w: AiWeights) -> Fraction:
    """防禦的分數：``defend`` × 6 格內的敵人數（防禦只替自己加上狀態，位置不變；與完整
    ``preview`` 的分數相同）。"""
    near = sum(1 for e in _enemies(state, unit) if unit_dist(unit, e) <= _DEFEND_RADIUS)
    return Fraction(w.defend * near)


def _run_tiles(state: BattleState, unit: UnitState, budget: int) -> list[XY]:
    """``budget`` 點移動點數本回合能停留的格子（含目前位置）。"""
    pm = path_map(state, unit, budget)
    return [unit.xy, *sorted(xy for xy in pm.cost if pm.can_end_at(xy))]


def run_score(state: BattleState, unit: UnitState, rules: RunAiRules) -> Fraction:
    """跑步的分數（Phase 3-20）：只有追擊（目前走不到攻擊距離、跑步後走得到）與撤離（低血量、
    敵人逼近、跑步後能離敵人更遠）兩種情況給分，其餘 0 分。跑步不移動，所以不跑完整 ``preview``。

    只在移動點數用完時才考慮（先走、走完才跑：跑步的 +3 格不會因為先跑而更有效，先走也不會讓
    走位評分被跑步搶走）；速度 0 ＝ 固定不動（木樁、圖騰），不跑。
    """
    budget = available_move_budget(state, unit)
    enemies = _enemies(state, unit)
    if unit.speed == 0 or budget != 0 or not enemies:
        return Fraction(0)
    now = [unit.xy]
    after = _run_tiles(state, unit, state.ruleset.core.run_move_bonus)
    if unit.hp * 1000 < rules.retreat_hp_permille * unit.max_hp:  # 低血量：只考慮撤離，不追擊
        if min(unit_dist(unit, e) for e in enemies) > rules.retreat_enemy_radius:
            return Fraction(0)

        def gap(tiles: list[XY]) -> int:
            return max(min(dist_to(e, t) for e in enemies) for t in tiles)

        return Fraction(rules.retreat_points if gap(after) > gap(now) else 0)
    reach = attack_reach(state, unit)

    def can_hit(tiles: list[XY]) -> bool:
        return any(dist_to(e, t) <= reach for t in tiles for e in enemies)

    return Fraction(rules.pursue_points if not can_hit(now) and can_hit(after) else 0)


def vault_score(unit: UnitState, dest: XY, scene: _Scene, rules: BasicActionAiRules) -> Fraction:
    """攀跳的分數（Phase 3-21b）：落點走到最近敵人的步數（走路規則，不含攀跳）比現在少至少
    ``vault_min_saving`` 步才給 ``vault_points``；現在走不到、落點走得到也算；其餘 0 分。"""
    walk = scene.walk
    if walk is None or not scene.enemies:
        return Fraction(0)
    before = [d for e in scene.enemies if (d := walk.to(e, unit.xy)) is not None]
    after = [d for e in scene.enemies if (d := walk.to(e, dest)) is not None]
    if not after:
        return Fraction(0)
    if before and min(before) - min(after) < rules.vault_min_saving:
        return Fraction(0)
    return Fraction(rules.vault_points)
