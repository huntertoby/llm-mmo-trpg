"""基本動作與勝利條件的規則說明（Phase 3-41b，清單 8、12）：由 ``rules/core.yaml`` 的數值組出
中文說明，和規則同一個來源——改資料時文字自動跟著變，前端不再寫死「+3 格」「+25%」這類數字。

純函式、確定性。前端從 ``/api/glossary`` 的 ``actions``／``objectives`` 取用：動作按鈕與「更多動作」
選單的浮動卡、勝利條件的一行說明與目標格資訊卡。勝利條件的文字裡 ``{rounds}`` 是佔位，
由前端填入該場的限時輪數。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.rules import CoreRules

__all__ = [
    "ROUNDS_PLACEHOLDER",
    "InfoText",
    "action_texts",
    "objective_texts",
]

ROUNDS_PLACEHOLDER = "{rounds}"


@dataclass(frozen=True)
class InfoText:
    """一則說明：``id``、顯示名、一句話摘要（``summary_zh``）與完整規則列（``lines_zh``）。"""

    id: str
    name_zh: str
    summary_zh: str
    lines_zh: tuple[str, ...]


def _pct(permille: int) -> str:
    return f"{permille / 10:g}%"


def _contest(core: CoreRules, attr: str) -> str:
    return (
        f"{attr}對抗：d20 ＋ 雙方{attr}差的攻防修正 ＋ 熟練 {core.proficiency}，"
        f"合計 ≥ {core.hit_target} 才成功"
    )


def _ap(core_cost: int) -> str:
    return f"花 {core_cost} AP"


def _basic_actions(core: CoreRules, refill: Sequence[str] = ()) -> list[InfoText]:
    dice = core.collision_damage_dice
    return [
        InfoText(
            "move",
            "移動",
            "點亮起的格子移動，不花 AP，只花移動點數",
            (
                "不花 AP，只花移動點數（點亮起的格子）",
                f"往上爬一層多花 {core.move_climb_extra_cost} 點移動點數；"
                f"一步最多往上 {core.max_climb_height} 層",
            ),
        ),
        InfoText(
            "attack",
            "普攻",
            f"{_ap(core.basic_attack_ap_cost)}，用武器攻擊紅框的目標",
            (
                f"{_ap(core.basic_attack_ap_cost)}，用武器攻擊射程內的目標",
                "傷害 ＝ 武器的骰子 ＋ 固定值 ＋ 縮放屬性 × "
                f"{core.basic_attack_attr_multiplier_permille / 1000:g}",
                f"命中判定：d20 ＋ 攻防修正 ＋ 熟練 {core.proficiency}，"
                f"合計 ≥ {core.hit_target} 才命中",
            ),
        ),
        InfoText(
            "run",
            "跑步",
            f"{_ap(core.run_ap_cost)}，本回合移動點數 +{core.run_move_bonus} 格（每回合 1 次）",
            (
                f"{_ap(core.run_ap_cost)}，本回合移動點數 +{core.run_move_bonus} 格"
                "（固定格數，不受加速或緩速影響）",
                "每回合限 1 次；跑步本身不會移動，之後再點亮起的格子",
                "被定身時不能跑步",
            ),
        ),
        InfoText(
            "defend",
            "守護",
            f"{_ap(core.defend_ap_cost)}，防禦 +{_pct(core.defend_defense_bonus_permille)}"
            "到下回合開始；相鄰有隊友時可點他，改由你替他承受單體攻擊",
            (
                f"{_ap(core.defend_ap_cost)}，防禦值 +{_pct(core.defend_defense_bonus_permille)}，"
                "持續到自己的下一個回合開始",
                "守護隊友：點相鄰的隊友，敵人以單體攻擊他、且你仍與他相鄰時，改由你承受"
                f"（每輪最多 {core.guard_transfers_per_round} 次；範圍技能不轉移）",
            ),
        ),
        InfoText(
            "shove",
            "推擊",
            f"{_ap(core.maneuver_ap_cost)}，力量對抗，成功推開相鄰敵人 {core.shove_distance} 格",
            (
                f"{_ap(core.maneuver_ap_cost)}，對相鄰的敵人使出",
                _contest(core, "力量"),
                f"成功時沿「你 → 目標」方向推 {core.shove_distance} 格"
                f"（距離上限 {core.max_displace_distance} 格）；"
                f"撞到障礙或單位，每少走 1 格受 {dice} 物理撞擊傷害",
                "推進致命地形的單位死亡（精英與 Boss 改受 "
                f"{_pct(core.deadly_terrain_elite_permille)} 最大 HP 傷害）",
                f"標示為「穩如泰山」的單位，推擊距離只有 {_pct(core.steadfast_push_permille)}",
            ),
        ),
        InfoText(
            "trip",
            "絆倒",
            f"{_ap(core.maneuver_ap_cost)}，敏捷對抗，成功讓相鄰敵人倒地",
            (
                f"{_ap(core.maneuver_ap_cost)}，對相鄰的敵人使出",
                _contest(core, "敏捷"),
                "成功時目標倒地；站起要花掉"
                f"一半（{_pct(core.prone_stand_up_move_permille)}，無條件進位）的移動點數",
            ),
        ),
        InfoText(
            "interact",
            "推動物件",
            f"{_ap(core.interact_ap_cost)}，把相鄰的可推動物件往遠離你的方向推 1 格",
            (
                f"{_ap(core.interact_ap_cost)}，把相鄰的「可推動」物件沿「你 → 物件」方向推 1 格"
                "（不能推單位；你自己不動）",
                f"你和物件所在格的高度差不能超過 {core.interact_height_limit} 層",
            ),
        ),
        InfoText(
            "shove_aside",
            "撥開物件",
            f"{_ap(core.interact_ap_cost)}，把相鄰的可推動物件往左或右側推 1 格",
            (
                f"{_ap(core.interact_ap_cost)}，把相鄰的「可推動」物件"
                "往垂直於「你 → 物件」的左或右推 1 格（你自己不動）",
                f"你和物件所在格的高度差不能超過 {core.interact_height_limit} 層",
            ),
        ),
        InfoText(
            "swap",
            "換位",
            f"{_ap(core.swap_ap_cost)}，和相鄰的我方單位互換位置",
            (
                f"{_ap(core.swap_ap_cost)}，與相鄰的我方單位（含召喚物）互換位置",
                "朝向不變，不會觸發藉機攻擊",
            ),
        ),
        InfoText(
            "aim",
            "瞄準",
            f"{_ap(core.aim_ap_cost)}，本回合下一次攻擊命中 +{core.aim_hit_bonus}",
            (
                f"{_ap(core.aim_ap_cost)}，本回合下一次需要擲命中的攻擊（普攻或技能）"
                f"命中 +{core.aim_hit_bonus}",
                "不疊加；回合結束或用掉就失效",
            ),
        ),
        InfoText(
            "vault",
            "攀跳",
            f"{_ap(core.vault_ap_cost)} 與 {core.vault_move_cost} 點移動點數，攀上高處或跳過缺口",
            (
                f"{_ap(core.vault_ap_cost)}，另外消耗 {core.vault_move_cost} 點移動點數",
                f"攀爬：爬上相鄰、高 {core.vault_climb_height} 層的格子（超過一般移動一步可爬的 "
                f"{core.max_climb_height} 層）",
                f"跳躍：越過正前方連續 {core.vault_jump_width} 格不能站的格子"
                "（深淵、岩漿、斷橋缺口），落在對面的下一格",
            ),
        ),
        InfoText(
            "reload",
            "裝填",
            "把有彈匣的武器裝滿（空膛時才能裝填）",
            (
                "花的 AP 依武器而定（看武器特性的「彈匣」一行）",
                "只有空膛時才能裝填；裝滿彈匣",
            ),
        ),
        InfoText(
            "end_stance",
            "結束姿態",
            "解除目前的姿態，免費",
            (f"免費，只能在自己的回合；進入姿態要花 {core.stance_ap_cost} AP",),
        ),
        InfoText(
            "stand",
            "起身",
            f"倒地的單位站起來，花 {_pct(core.prone_stand_up_move_permille)} 的移動點數",
            (
                "倒地的單位原地站起，消耗 "
                f"{_pct(core.prone_stand_up_move_permille)} 的移動點數（無條件進位）",
            ),
        ),
        InfoText(
            "stamina",
            "耐力",
            "武器技與反應（例如格擋）要消耗的資源",
            (
                "武器技花耐力、法術技花法力；格擋等反應也花耐力，共用同一個池。耐力不足就不能"
                "施放武器技或反應",
                f"每輪最多反應 {core.reactions_per_round} 次",
                _stamina_recovery(core, refill),
            ),
        ),
        InfoText(
            "end_turn",
            "結束回合",
            f"結束這個回合；最多保留 {core.ap_carry_max} AP 到下回合",
            (
                f"結束這個回合；每回合 {core.ap_per_turn} AP，"
                f"未用完的 AP 最多保留 {core.ap_carry_max} 點到下回合",
            ),
        ),
    ]


def _stamina_recovery(core: CoreRules, refill: Sequence[str]) -> str:
    """耐力怎麼回復（3H-5）：每回合開始回復的點數取自 ``core.resources``，戰後回滿與否取自
    ``roguelite.yaml`` 的 ``refill_after_battle``（資料，不寫死）。"""
    regen = core.resources.stamina_regen
    head = f"主角每回合開始回復 {regen} 點（不超過上限）；" if regen else "戰鬥中不會自動回復；"
    after = "每場打贏後回滿" if "stamina" in refill else "戰鬥之間不回復"
    mana = "法力每場打贏後回滿" if "mana" in refill else "法力只在營火回滿"
    return f"{head}{after}；{mana}，HP 只在營火回滿"


def action_texts(core: CoreRules, refill_after_battle: Sequence[str] = ()) -> tuple[InfoText, ...]:
    """基本動作（含常駐按鈕與「更多動作」選單）的規則說明，數字取自 ``core``。"""
    return tuple(_basic_actions(core, refill_after_battle))


# ---------------------------------------------------------------------------
# 勝利條件（``trpg.engine.objectives``）
# ---------------------------------------------------------------------------


def objective_texts() -> tuple[InfoText, ...]:
    """三種勝利條件、兩種目標格與四種結算原因的說明（對照 ``engine/objectives.py`` 的判定）。

    ``{rounds}`` 是限時輪數的佔位。判定規則本身沒有可調數值，所以文字固定；測試用引擎的判定
    逐項驗證（倒下的隊友不用撤、召喚物不計、只在每輪結束判定）。
    """
    r = ROUNDS_PLACEHOLDER
    return (
        InfoText(
            "eliminate",
            "全滅",
            "擊倒所有敵人",
            (
                "擊倒所有敵人即勝；我方全部倒下即敗",
                "召喚物不計入（不用打倒敵方召喚物，我方召喚物倒下也不算全滅）",
            ),
        ),
        InfoText(
            "escape",
            "撤離",
            f"{r} 輪內，所有還活著的我方單位抵達出口",
            (
                f"{r} 輪內，所有還活著的我方單位都抵達出口格即勝；站上出口格的單位離開戰場",
                "倒下的隊友不用撤；召喚物不計",
                f"第 {r} 輪結束時還有我方單位留在戰場上即敗；敵方全部被擊倒也算勝",
            ),
        ),
        InfoText(
            "defend",
            "守點",
            f"守住守點 {r} 輪，別讓敵人站在上面",
            (
                f"守住守點 {r} 輪即勝",
                "每輪結束時（環境回合之後）判定：有敵方單位站在守點格上即敗；敵方召喚物不算",
                "我方全部倒下即敗；敵方全部被擊倒也算勝",
            ),
        ),
        InfoText(
            "exit",
            "出口格",
            "我方單位站上來就撤離戰場",
            (
                "我方單位站上出口格就撤離戰場",
                f"{r} 輪內所有還活著的我方單位都撤離才算勝利；"
                "時限到仍有人留在場上即敗（倒下的隊友不用撤）",
            ),
        ),
        InfoText(
            "point",
            "守點格",
            "每輪結束時，敵人站在上面就失守",
            (
                "每輪結束時（環境回合之後），若有敵方單位站在守點格上，守點失守（戰敗）；敵方召喚物不算",
                "守到時限最後一輪結束即勝；我方單位站在上面可以擋住敵人",
            ),
        ),
        InfoText("result_escaped", "撤離成功", "撤離成功：所有還活著的隊友都抵達了出口。", ()),
        InfoText("result_escape_failed", "撤離超時", "撤離超時：時限到了，仍有人留在戰場上。", ()),
        InfoText("result_defended", "守住了", "守住了：守點撐到最後一輪結束。", ()),
        InfoText("result_point_lost", "守點失守", "守點失守：敵人占領了守點。", ()),
    )
