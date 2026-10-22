"""自動對戰與重播（CLI 與之後的模擬器共用的驅動迴圈）。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import cast

from pydantic import BaseModel, ConfigDict

from trpg.engine.actions import Action, Decision, EndTurn, Step
from trpg.engine.ai import Policy
from trpg.engine.ai.commanded import OrderLogging
from trpg.engine.ai.composite import choose_followup
from trpg.engine.ai.orders import OrderRecord
from trpg.engine.ai.simple import choose_action
from trpg.engine.battle import begin_battle, has_only_end_turn, resolve, resume
from trpg.engine.copying import copy_selections
from trpg.engine.events import Event, EventBase
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team, UnitId

__all__ = [
    "DEFAULT_MAX_ACTIONS",
    "LOG_FORMAT",
    "BattleLog",
    "BattleRun",
    "DecisionPolicy",
    "StepLimitExceeded",
    "StopCondition",
    "accept_all",
    "advance",
    "apply_step",
    "auto_step",
    "replay",
    "run_battle",
]

LOG_FORMAT = "trpg-battle-log/42"
"""``/42``（Phase 3-24c）：新條件 ``target_collided``（單位的 ``collided_round``）、新原語
``sacrifice_summon``（召喚物消失原因 ``sacrificed``）、火器的武器技也算開火（消耗彈匣、槍聲、站定、
距離修正）；``/41`` 的紀錄無法重播。
``/41``（Phase 3G-G2）：規則包 ``Ruleset.keywords``（關鍵字推導表，技能強化詞條依關鍵字選技能）；
武器特性強化、普攻附加、技能強化都由裝備快照在開戰時算出，戰鬥事件沒有新增。``/40`` 的紀錄無法重播。
``/40``（Phase 3G-G1，接在 3-24a2 的 ``/39`` 之後）：裝備——戰鬥設定 ``UnitSpawn.equipment``／
``SpawnTemplate.equipment``（裝備快照：物品與詞條定義內嵌）、單位範本 ``equipment``、單位狀態
``gear``（遞減後的詞條與數值）、規則包 ``equipment``（遞減權重與硬上限）、新事件 ``gear_hp_lost``；
裝備改變戰鬥的初始狀態，``/39`` 的紀錄無法由新版程式重播（已接受）。
``/39``（Phase 3-24a2）：基本動作之外的武器動作裝填（動作 ``reload``、事件 ``weapon_reloaded``、
單位的 ``ammo``）、武器資料新增遠程特性欄位（``pierce_line``／``ignore_height``／``magazine``／
``reload_ap``／``gunshot``／``steady``／``ignore_cover``／``armor_pierce_permille``／``range_mod``）；
帶彈匣的武器空膛時不能普攻，同種子的 AI 對戰結果可能與 ``/38`` 不同。
``/38``（Phase 3-23，接在 3-21b 的 ``/37`` 之後）：刻印——原語 ``inscribe``／
``detonate_runes``（符文用 ``EffectSpec`` 的 ``element``／``tag``）、
條件 ``on_own_rune``（``ConditionSpec`` 新欄位 ``element``）、骨架 ``rune``、
戰鬥狀態的 ``runes``／``next_rune_id``、新事件 ``rune_inscribed``／
``rune_removed``、新效果
``inscribe``／``detonate_rune``、核心規則 ``rune_limit_per_owner``／``rune_default_rounds``／
``rune_max_rounds``、預算規則 ``inscribe_duration_permille``／``detonate_runes_permille``；
``/37`` 的規則包沒有這些欄位，舊紀錄不能由新版程式重播。
``/37``（Phase 3-21b）：基本動作攀跳（動作 ``vault``、事件 ``unit_vaulted``）、核心規則
``vault_ap_cost``／``vault_move_cost``／``vault_climb_height``／``vault_jump_width``、AI 規則
``basic`` 的 ``vault_*``；AI 會選擇攀跳，同種子的 AI 對戰結果與 ``/36`` 可能不同，且 ``format`` 不符
的紀錄由 ``trpg battle replay`` 拒絕。
``/36``（Phase 3-21a）：基本動作守護（``defend`` 加 ``target_id``、事件 ``guard_set``、
``attack_intercepted.guard``、單位的 ``guarding_id``／``guard_transfers``）、換位（``swap``）、瞄準
（``aim``、事件 ``unit_aimed``、單位的 ``aimed``）、核心規則 ``swap_ap_cost``／``aim_ap_cost``／
``aim_hit_bonus``／``guard_transfers_per_round``，AI 規則 ``guard``／``swap``／``aim``；
速度 0 的單位不能跑步。舊紀錄的步驟仍可逐步重播，但 AI 會選擇新動作，同種子的 AI 對戰結果
與 ``/35`` 不同，且 ``format`` 不符的紀錄由 ``trpg battle replay`` 拒絕。
``/35``（Phase 3-20）：基本動作跑步——動作 ``run``、事件 ``unit_ran``、單位的 ``ran_this_turn``、
核心規則 ``run_ap_cost``／``run_move_bonus``、AI 規則 ``run``；``resolve`` 對舊紀錄中的動作行為不變
（舊紀錄的步驟仍可逐步重播），但 AI 會選擇跑步，同種子的 AI 對戰結果與 ``/34`` 不同，且
``format`` 不符的紀錄由 ``trpg battle replay`` 拒絕。
``/34``（Phase 3C-6b）：守護者替隊友擋下近戰攻擊時，轉身面向攻擊者的是守護者（不是原本被瞄準
的人），AI 的走位與背刺因此改變；舊紀錄不能由新版程式重播。
``/33``（Phase 3C-6a）：被近戰攻擊後轉身——近戰攻擊（普攻與近戰武器技，不論命中與否）結算完，
目標轉向攻擊者（遠程不轉、強制位移不轉；背刺仍以擲骰當下的朝向為準），AI 的走位與背刺次數因此
改變；``damage_dealt.pierce_permille``（穿透折扣與格擋分開記錄）、``move_blocked.forced``（推擊
被擋下，紀錄以接著的 ``collided`` 為主）、``shot_pierced.behind`` 只列命中的後方單位；
``steal_buff`` 的事件順序改為先 ``status_removed`` 再 ``status_applied``。舊紀錄的 AI 選擇與事件
順序不同，不能由新版程式重播。
``/32``（Phase 3D-8d）：朝向與背刺——單位的 ``facing``（開場面向敵方起始位置；主動移動、攻擊與
對單位施放技能後更新）、核心規則 ``backstab_hit_bonus``／``backstab_crit_range_bonus``／
``ambush_hit_bonus``、``attack_rolled`` 的 ``backstab``／``ambush``、``status_removed`` 的新原因
``ambushed``；條件 ``from_behind``、``self_concealed``；原語 ``shadowstep``
（``EffectSpec.landing``、移動方式 ``shadowstep``）；AI 權重 ``backstab``、``back_exposed``。
``/31`` 的狀態沒有朝向，舊紀錄不能由新版程式重播（背刺與 AI 的選擇都依朝向）。
``/31``（Phase 3D-8c）：監視射擊——狀態 ``overwatch``、內建反應 ``overwatch_shot``（反應事件
``enemy_moves_in_range``、反應定義的 ``requires_status``）、``status_removed`` 的新原因 ``fired``，
有監視技能的單位自動多一條反應規則；夾擊——條件 ``flanked``；暫時獲得技能——原語 ``grant_skill``
（``EffectSpec.skill``）、單位的 ``granted_skills``、新事件 ``skill_granted``／
``skill_grant_expired``、預算規則 ``grant_skill_expected_uses_per_round_permille``；AI 規則
``flank``、``overwatch_*``、``grant_skill_*``；``/30`` 的規則包沒有這些欄位與狀態，舊紀錄不能由新版
程式重播。
``/30``（Phase 3D-8b）：復活——原語 ``revive``（``EffectSpec.hp_permille``）、單位的 ``revived``、
核心規則 ``revive_landing_radius``、新事件 ``unit_revived``；技能內的擊殺時效果——傷害效果的
``on_kill``（專用效果 ``refund_ap``／``refund_cooldown``）、新事件 ``ap_refunded``；定時炸彈——
原語 ``delayed_damage``（``EffectSpec.rounds``／``radius``）、狀態 ``time_bomb`` 與
``StatusInstance.skill_id``、效果 ``bomb_blast``、新事件 ``bomb_ticked``／``bomb_exploded``、
環境回合的炸彈倒數、預算規則 ``revive_*``／``delayed_damage_*``／``on_kill_*``／
``refund_ap_points``；``/29`` 的規則包沒有這些欄位與狀態，舊紀錄不能由新版程式重播。
``/29``（Phase 3D-8a）：吸血與聖光雙效——傷害效果的 ``lifesteal_permille``／``split_heal``、
``healed.cause``（``lifesteal``）；驅散與揭露——原語 ``dispel``（``count: 1 | all``）／``reveal``、
``status_removed`` 的新原因 ``dispelled``／``revealed``、狀態 ``revealed``
（``prevents_concealment``）、陷阱的 ``revealed_to``、新事件 ``trap_revealed``、預算規則
``dispel_*``／``reveal_*``／``lifesteal_value_permille``；``/28`` 的規則包沒有這些欄位與狀態，
舊紀錄不能由新版程式重播。
``/28``（Phase 3D-7b）：高變異——傷害效果的 ``explode``（``DamageEffect.explode_max``、
``damage_dealt.exploded``）、技能的 ``crit_range``／``damage_permille``；超載——層數的 ``overload``
（``stacks.yaml``）、新事件 ``overload_triggered``、``stacks_changed`` 的新原因 ``overload``；依情況
縮放——傷害效果的 ``scaling``；核心規則 ``explode_max``／``scale_cap_max_permille``、預算規則
``variance_*``／``scale_expected_steps_milli``／``overload_expected_permille``；``/27`` 的規則包沒有
這些欄位，舊紀錄不能由新版程式重播。
``/27``（Phase 3D-7a）：賭博型技能——原語 ``gamble``（``EffectSpec`` 新欄位
``chance_permille``／``win``／``lose``，分支內的 ``damage_multiplier``／``self_damage_of_hit``）、
失手反噬 ``cost.on_miss``、``damage_dealt.cause`` 的新值 ``backlash``（不會讓受到的單位 HP 低於
1）、新事件 ``gamble_rolled``／``backlash_triggered``、預算規則 ``gamble_*``；``/26`` 的規則包
沒有這些欄位，舊紀錄不能由新版程式重播。
``/25``（Phase 3D-5）：持續區域——原語 ``zone``（``EffectSpec`` 新欄位 ``anchor``／``when``／
``speed``／``effects``）、核心規則 ``zone_limit_per_owner``、預算規則 ``zone_*``、戰鬥狀態的
``zones``／``next_zone_id``、新事件 ``zone_created``／``zone_moved``／``zone_triggered``／
``zone_expired``；示範技能「戰歌」改寫成跟隨型區域。``/24`` 的規則包沒有這些欄位，舊紀錄不能由
新版程式重播。
``/24``（Phase 3D-4b）：圖騰——單位範本的 ``totem``（``radius``／``status``／``duration``）、
新事件 ``totem_pulsed``、圖騰的回合沒有 AP、預算規則 ``totem_expected_allies_permille``；
``/23`` 的規則包沒有 ``totem`` 欄位，舊紀錄不能由新版程式重播。
``/23``（Phase 3D-4a）：召喚——原語 ``summon``（形狀 ``ground_tile``；
``EffectSpec`` 新欄位 ``unit``、``count``）、規則包的 ``summons``（召喚物範本與武器）、
核心規則 ``summon_limit_per_owner``、單位範本的 ``summon``、單位狀態的 ``owner_id``／
``summon_expires_round``／``dismissed``、新事件 ``unit_summoned``／``summon_expired``、
``effect_fizzled`` 的新原因（``summon_blocked``／``unknown_summon``）；
``/22`` 的規則包沒有這些欄位，舊紀錄不能由新版程式重播。
``/22``（Phase 3D-3）：修正規則的技能變形（``area_delta``、``shape_to``、``allow_self_target``；
``skill_shapes.yaml`` 的 ``conversions``、``SkillDef.include_caster``）、四個新反應事件
（``hit_by_spell``、``ally_downed``、``enemy_enters_adjacent``、``ally_targeted``，單位反應規則的
``when.event``）、投擲的油桶摔破漏油而不是爆炸（``HurlObjectEffect.ignite``；舊紀錄中投擲的油桶
重播會得到不同結果）、倒塌物可破壞；
舊紀錄的規則包與投擲結算不能由新版程式重播。
``/21``（Phase 3D-2c）：直線衝撞原語 ``charge_through``（形狀 ``ground_tile``，``UseSkill`` 帶
``target_pos`` ＝終點格；``dice``、新欄位 ``on_hit``）、事件 ``unit_charged``、戰鬥紀錄中新的
``effect_fizzled`` 原因 ``charge_no_path``；``/20`` 的規則集沒有這個原語，舊紀錄的規則包不能由新版
程式重播。

``/20``（Phase 3D-2b）：位移他人原語 ``teleport_target``（形狀 ``unit_then_tile``，``UseSkill``
帶 ``target_id`` 與 ``target_pos``）、``swap_any``（形狀 ``unit_pair``，帶 ``target_id`` 與新欄位
``second_target_id``）、``unit_moved`` 的新 ``mode``（``teleported``）、``maneuver_rolled`` 的新
``maneuver``（``teleport``／``swap``）與新欄位 ``resist_bonus``、核心規則
``teleport_enemy_resist_bonus``／``teleport_lethal_resist_bonus``；``swap`` 對敵人改用位移檢定
（不再擲命中）。``/19`` 的紀錄重播 ``swap`` 時結果不同，不能由新版程式重播。

``/19``（Phase 3D-2）：自身位移原語 ``dash``（衝鋒）、``leap``（跳躍）、``swap``（交換位置）、
事件 ``unit_dashed``、``unit_moved`` 的新 ``mode``（``dash``／``leap``／``swap``）、戰鬥紀錄中
新的 ``effect_fizzled`` 原因（``dash_blocked``／``dash_no_path``／``swap_blocked``）；``/18`` 的
規則集沒有這些原語，舊紀錄的事件與規則包不能由新版程式重播。

``/18``（Phase 3D-1）：連段條件（單位的 ``moved_this_turn``、``turn_cast_tags``；條件
``moved_this_turn``／``adjacent_ally``／``target_isolated``／``first_round``／``cast_tag_this_turn``）、
資源互動原語 ``restore_resource``（事件 ``resource_restored``）與 ``steal_buff``
（``status_removed`` 的新原因 ``stolen``）、狀態分類 ``polarity``；``/17`` 的紀錄沒有這些欄位與
規則（狀態表多了必填的 ``polarity``），無法由新版程式重播。

``/17``（Phase 3C-5b）：穿透——技能欄位 ``pierce``、修正規則 ``grant_pierce``、核心規則
``pierce_behind_permille``、事件 ``shot_pierced``；穿透技能無視半掩護，傷害與命中因此和 ``/16``
的規則不同（``/16`` 的紀錄沒有穿透技能，內容與事件逐字不變，但規則包與事件種類多了新欄位）。

``/16``（Phase 3C-5a）：場景物件原語——投擲物件 ``hurl_object``（形狀 ``object_then_tile``，
``UseSkill`` 同時帶 ``target_object_id`` 與 ``target_pos``、效果 ``hurl_object``、事件
``object_hurled``）與推倒（物件標籤 ``topplable``／``penetrable``、原語 ``topple``、事件
``object_toppled``、傷害原因 ``topple``、物件摧毀原因 ``hurled``／``toppled``、核心規則
``topple_length``／``topple_damage_dice``／``topple_rubble_object``／``hurl_scatter_radius``）；
推石柱、枯樹改為推倒，所以 ``/15`` 的紀錄無法重播。

``/15``（Phase 3C-4b）：三個改寫規則型原語 ``redirect_damage``（狀態 ``soul_link``，
``StatusInstance.amount`` 存轉移千分比）、``copy_skill``（戰鬥狀態 ``casts``、
``UseSkill.copy_cast``、``Decision.copy_cast``、暫停種類 ``copy_skill``）、
``extra_reaction``（單位 ``extra_reactions``）；
新事件 ``damage_redirected``／``skill_copied``／``reactions_granted``、``damage_dealt.redirected``；
``/14`` 的紀錄沒有這些欄位與規則，無法由新版程式重播。

``/14``（Phase 3C-4a）：源力（單位的 ``source``、``ap_pending``、``ap_granted_round``，
戰鬥狀態的 ``source_wells``，戰鬥設定 ``UnitSpawn.source``）、新事件 ``source_changed``／
``ap_granted``／``death_cheated``、``skill_used.source``、``status_removed`` 的新原因 ``spent``、
三個改寫規則型原語與狀態 ``undying``；擊倒精英會多出 ``source_changed`` 事件，所以 ``/13`` 的
紀錄用新版程式重跑事件會不同。

``/13``（Phase 3C-3b）：表面歸屬（格子的 ``surface_creator``）、新觸發時機 ``on_enter_surface``、
``consume_status`` 原語（``status_removed`` 的新原因 ``consumed``）、基本推擊貼牆也合法並產生撞擊；
``/12`` 的紀錄含有舊的推擊合法性與觸發表，無法由新版程式重播。

``/12``（Phase 3C-3a）：撞擊——推擊遇到障礙或超過距離上限時新增 ``collided`` 事件與
``DamageDealt.cause == "collision"``，規則包加入 ``collision_damage_dice`` 與三個新觸發時機；
``/11`` 的紀錄重播會因撞擊傷害而不同，無法由新版程式重播。

``/11``（Phase 2H-1）：``status_removed`` 的新原因 ``thawed``、規則包的狀態加入
``removed_by_element``、互動規則加入 ``apply_status`` 結果與單位所在格表面條件；``/10`` 的紀錄
無法由新版程式重播。

``/10``（Phase 2E-3）：層數（單位狀態加入 ``stacks``／``stack_expiry``、``stacks_changed``、
規則包的 ``stacks``）、陷阱（戰鬥狀態加入 ``traps``、``trap_placed``／``trap_triggered``／
``trap_expired``）、傷害加成（``damage_dealt`` 的倍率含層數加成）；``/9`` 的紀錄無法重播。

``/9``（Phase 2E-2）：反應技（``reaction_triggered`` 的 ``reaction`` 可以是技能 ID）、替隊友
擋攻擊（``attack_intercepted``）、姿態（``end_stance`` 動作、``status_removed`` 的新原因、規則包的
``stance_ap_cost``）；``/8`` 的紀錄無法重播。

``/8``（Phase 2E-1）：被動技能的觸發（``skill_triggered``、``trigger_limit_reached``；
單位狀態加入 ``trigger_counts``、``hits_landed``；規則包加入 ``skill_triggers``）；
``/7`` 的紀錄無法重播。

``/7``（Phase 2D-1）：護盾（``StatusInstance.amount``、``shield_gained``／``shield_absorbed``、
``damage_dealt.absorbed``）、有效屬性（狀態的屬性加值）與嘲諷；``/6`` 的紀錄無法重播。

``/5``（Phase 2B-1）：新狀態、抵抗判定（``status_save_rolled``）、控制遞減（單位狀態加入
``control_dr``）、Boss 轉換與 ``turn_skipped``；傷害與治療帶狀態倍率，``/4`` 的紀錄無法重播。

``/4``（Phase 2A）：加入 ``use_skill`` 動作與技能事件（``skill_used``、
``skill_cooldown_changed``），``turn_started`` 帶法力，``attack_rolled``／``maneuver_rolled``
帶 ``skill_id``；``/3`` 的紀錄無法重播。

``/3``（Phase 1C）：加入掩護（``attack_rolled.cover``）、``damage_dealt.base_amount``、牆壁地形，
且結算規則改變（表面在腳下立即生效、漏油、推不動的推擊不合法），``/2`` 的紀錄無法重播。

``/2``（Phase 1B）：``actions`` 改為步驟列表（動作或 ``decision``）；狀態加入物件、表面等欄位。
（``/1`` 的紀錄無法以 Phase 1B 的引擎重播。）"""
DEFAULT_MAX_ACTIONS = 20_000

type StepCallback = Callable[[Step | None, ResolveResult], None]
type DecisionPolicy = Callable[[BattleState, Pending], Decision]
"""``prompt`` 反應的決策函式。"""
type StopCondition = Callable[[BattleState, Pending | None], bool]
""":func:`advance` 的停止條件（例如「輪到玩家操控的單位」）。"""


class StepLimitExceeded(TrpgError):
    """自動推進超過步數上限仍未結束（或未輪到玩家）。"""


def accept_all(state: BattleState, pending: Pending) -> Decision:
    """預設：一律使用反應；``copy_skill`` 的選目標取第一個合法的選取（Phase 3C-4b）；複合技能的
    第二段（Phase 3F-4a）由 AI 的簡單估計選（:func:`~trpg.engine.ai.composite.choose_followup`，
    Phase 3F-4b；沒有值得的選取時放棄第二段）。"""
    if pending.kind == "followup":
        return choose_followup(state, pending)
    if pending.kind == "copy_skill":
        caster = state.units[pending.unit_id]
        pick = next(copy_selections(state, caster), None)
        return Decision(
            unit_id=pending.unit_id, accept=pick is not None, copy_cast=pick and pick[0]
        )
    return Decision(unit_id=pending.unit_id, accept=True)


class BattleRun:
    """一場自動對戰的結果：最終狀態、步驟列表、全部事件（含開場事件）。"""

    __slots__ = ("actions", "events", "orders", "seed", "setup", "state")

    def __init__(
        self,
        setup: BattleSetup,
        seed: int,
        state: BattleState,
        actions: list[Step],
        events: list[EventBase],
        *,
        orders: list[OrderRecord] | None = None,
    ) -> None:
        self.orders: list[OrderRecord] = [] if orders is None else orders
        """指揮官下達的指令紀錄（Phase 2C-2；沒有指揮官時為空）。"""
        self.setup = setup
        self.seed = seed
        self.state = state
        self.actions = actions
        self.events = events

    def to_log(self) -> BattleLog:
        return BattleLog(
            format=LOG_FORMAT,
            seed=self.seed,
            setup=self.setup,
            actions=self.actions,
            events=cast("list[Event]", self.events),
            final_state=self.state,
            orders=self.orders,
        )


class BattleLog(BaseModel):
    """``trpg battle --log-json`` 的輸出格式。``actions`` 是步驟（動作或決定）。"""

    model_config = ConfigDict(extra="forbid")

    format: str
    seed: int
    setup: BattleSetup
    actions: list[Step]
    events: list[Event]
    final_state: BattleState
    orders: list[OrderRecord] = []
    """戰術指令紀錄（Phase 2C-2）。重播只重播動作，不重新呼叫指揮官；舊紀錄沒有這個欄位。"""


def run_battle(
    setup: BattleSetup,
    seed: int,
    policy: Policy = choose_action,
    *,
    decide: DecisionPolicy = accept_all,
    on_step: StepCallback | None = None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    controllers: Mapping[UnitId | Team, Policy] | None = None,
) -> BattleRun:
    """跑到戰鬥結束。行動者的 policy 依序查：``controllers`` 的單位 ID → 陣營 → ``policy``。

    ``legal_actions`` 只剩 ``EndTurn`` 時（:func:`has_only_end_turn`）自動結束回合，不詢問
    policy。結算暫停（``prompt`` 反應）時以 ``decide`` 回答並 ``resume``。``on_step`` 在開場與
    每一步結算後呼叫（開場時 step 為 ``None``）。超過 ``max_actions`` 步仍未結束時拋出
    :class:`StepLimitExceeded`（設定 ``max_rounds`` 可保證結束）。
    推進迴圈本身是 :func:`advance`（網頁 API 的自動推進共用同一個函式）。
    """
    result = begin_battle(setup, seed)
    if on_step is not None:
        on_step(None, result)
    events: list[EventBase] = list(result.events)

    def record(step: Step | None, step_result: ResolveResult) -> None:
        if on_step is not None:
            on_step(step, step_result)
        events.extend(step_result.events)

    state, _pending, steps = advance(
        result.state,
        None,
        policy,
        decide=decide,
        on_step=record,
        max_actions=max_actions,
        controllers=controllers,
    )
    orders = _collect_orders(policy, controllers)
    return BattleRun(setup, seed, state, steps, events, orders=orders)


def auto_step(
    state: BattleState,
    pending: Pending | None,
    policy: Policy,
    *,
    decide: DecisionPolicy = accept_all,
    controllers: Mapping[UnitId | Team, Policy] | None = None,
) -> Step:
    """自動驅動的下一步：暫停中以 ``decide`` 回答；只剩 ``EndTurn`` 時結束回合；否則問 policy。"""
    if pending is not None:
        return decide(state, pending)
    if has_only_end_turn(state):
        assert state.active_unit is not None
        return EndTurn(unit_id=state.active_unit)
    return _controller_for(state, policy, controllers)(state)


def apply_step(state: BattleState, step: Step) -> ResolveResult:
    """結算一個步驟：決定以 ``resume``、動作以 ``resolve``（與 :func:`replay` 相同）。"""
    if isinstance(step, Decision):
        return resume(state, step)
    action: Action = step
    return resolve(state, action)


def advance(
    state: BattleState,
    pending: Pending | None,
    policy: Policy,
    *,
    decide: DecisionPolicy = accept_all,
    on_step: StepCallback | None = None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    controllers: Mapping[UnitId | Team, Policy] | None = None,
    stop: StopCondition | None = None,
) -> tuple[BattleState, Pending | None, list[Step]]:
    """以 :func:`auto_step` 持續結算，直到戰鬥結束或 ``stop(state, pending)`` 為真。

    回傳 ``(最後狀態, 最後的 pending, 這次結算的步驟)``。``on_step`` 在每一步結算後呼叫
    （呼叫者可以藉此逐步保存進度：超過 ``max_actions`` 步時拋出 :class:`StepLimitExceeded`，
    已結算的步驟都已經通知過）。
    """
    steps: list[Step] = []
    while not state.ended:
        if stop is not None and stop(state, pending):
            break
        if len(steps) >= max_actions:
            raise StepLimitExceeded(f"超過 {max_actions} 個動作仍未結束戰鬥")
        step = auto_step(state, pending, policy, decide=decide, controllers=controllers)
        result = apply_step(state, step)
        if on_step is not None:
            on_step(step, result)
        state = result.state
        pending = result.pending
        steps.append(step)
    return state, pending, steps


def _controller_for(
    state: BattleState, policy: Policy, controllers: Mapping[UnitId | Team, Policy] | None
) -> Policy:
    if not controllers:
        return policy
    unit = state.active
    assert unit is not None
    by_unit = controllers.get(unit.id)
    if by_unit is not None:
        return by_unit
    return controllers.get(unit.team, policy)


def _collect_orders(
    policy: Policy, controllers: Mapping[UnitId | Team, Policy] | None
) -> list[OrderRecord]:
    """會記錄指令的 policy（同一個物件只算一次）的指令紀錄，依輪數與陣營排序（穩定）。"""
    seen: set[int] = set()
    records: list[OrderRecord] = []
    for candidate in (policy, *(controllers or {}).values()):
        if isinstance(candidate, OrderLogging) and id(candidate) not in seen:
            seen.add(id(candidate))
            records.extend(candidate.order_log)
    records.sort(key=lambda r: (r.round, r.team.value))
    return records


def replay(setup: BattleSetup, seed: int, steps: Sequence[Step]) -> BattleRun:
    """以 ``初始狀態 ＋ 步驟列表`` 重播（動作以 ``resolve``、決定以 ``resume``）。"""
    result = begin_battle(setup, seed)
    state = result.state
    events: list[EventBase] = list(result.events)
    for step in steps:
        result = apply_step(state, step)
        state = result.state
        events.extend(result.events)
    return BattleRun(setup, seed, state, list(steps), events)
