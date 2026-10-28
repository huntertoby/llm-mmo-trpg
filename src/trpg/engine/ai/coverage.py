"""效用 AI 對每個效果原語的估值方式（Phase 3E-2b 的宣告表）。

效用 AI 不是逐原語分派：技能先以便宜的估計（:func:`trpg.engine.ai.utility.skill_estimate`）篩選，
再對每個候選跑 ``preview`` 依事件評分（傷害、治療、狀態、位置價值……），改寫規則型原語另外加分
（``_rewrite_gains``）。所以新增原語時要想清楚它在 AI 裡怎麼被看見——預覽事件就夠，或需要專用的
候選估計、加分、友方支援檢查——並把結論寫進這張表。載入內容時
:func:`trpg.primitive_coverage.check_primitive_coverage` 檢查 ``skill_primitives.yaml`` 的每個
原語都在這裡（缺了就報錯）。
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

__all__ = ["PRIMITIVE_VALUATION"]

_EVENTS = "預覽事件評分"

PRIMITIVE_VALUATION: Mapping[str, str] = MappingProxyType(
    {
        "damage": f"{_EVENTS}（期望傷害、擊倒、擊殺）",
        "heal": f"{_EVENTS}（實際補到的量）；友方支援 _supports",
        "shield": f"{_EVENTS}；友方支援 _supports",
        "cleanse": f"{_EVENTS}；友方支援 _supports（有負面狀態）",
        "push": f"{_EVENTS}（位移、撞擊、掩護與位置價值）",
        "pull": f"{_EVENTS}（位移、撞擊、掩護與位置價值）",
        "knock_prone": f"{_EVENTS}（擊倒對抗的成功率）",
        "shockwave": f"{_EVENTS}（倒地的狀態價值）",
        "teleport": "候選估計 _special_estimate（落點的位置價值）",
        "dash": f"{_EVENTS}（衝到目標旁的位置與傷害）",
        "charge_through": "候選估計 _charge_estimate（路徑上的敵人數＋終點位置價值）",
        "shadowstep": "候選估計 _shadowstep_estimate",
        "leap": "候選估計 _special_estimate（落點的位置價值）",
        "swap": f"{_EVENTS}（交換後的位置價值）",
        "teleport_target": "候選估計 displace_estimate（ai/displace.py）",
        "swap_any": "候選估計 displace_estimate（ai/displace.py）",
        "apply_status": f"{_EVENTS}（行為模式的 status_values）；友方增益 _supports",
        "create_surface": f"{_EVENTS}（表面與位置價值）；陷阱估計 _trap_estimate",
        "destroy_object": f"{_EVENTS}（掩護與位置價值）",
        "blow_surface": f"{_EVENTS}（表面移動後的位置價值）",
        "clear_surface": f"{_EVENTS}（表面移除後的位置價值）",
        "create_obstacle": f"{_EVENTS}（場地型技能：位置價值）",
        "raise_terrain": f"{_EVENTS}（高低差與位置價值）",
        "lower_terrain": f"{_EVENTS}（高低差與位置價值）",
        "intercept": "反應技（攔截由反應機制觸發，不是主動施放的評分對象）",
        "add_stack": f"{_EVENTS}；超載層數的風險 ai/gamble.py（overloads）",
        "consume_stack": f"{_EVENTS}（層數加成反映在傷害）",
        "consume_status": f"{_EVENTS}（消耗後的 then 效果）",
        "place_trap": "候選估計 _trap_estimate；放置收益 _trap_gains",
        "grant_ap": "_rewrite_gains（ai_profiles.yaml rewrite）；友方支援 _SUPPORT_CHECKS",
        "reset_cooldown": "_rewrite_gains；友方支援 _SUPPORT_CHECKS",
        "cheat_death": "_rewrite_gains；友方支援 _SUPPORT_CHECKS",
        "redirect_damage": "_rewrite_gains；友方支援 _SUPPORT_CHECKS",
        "copy_skill": "以被複製的技能預覽評分（effective_skill）",
        "extra_reaction": "_rewrite_gains；友方支援 _SUPPORT_CHECKS",
        "hurl_object": "候選估計 scene_estimate（ai/scene_objects.py）",
        "topple": "候選估計 scene_estimate（ai/scene_objects.py）",
        "restore_resource": "_rewrite_gains；友方支援 _SUPPORT_CHECKS",
        "steal_buff": "_rewrite_gains",
        "dispel": "_rewrite_gains",
        "reveal": "_rewrite_gains",
        "revive": "候選估計 _placement_estimate；_rewrite_gains（revive_points）",
        "delayed_damage": "_rewrite_gains（_bomb_points）",
        "summon": "候選估計 summon_estimate（ai/summon.py）",
        "zone": "候選估計 zone_estimate（ai/zone.py）",
        "rule_change": "常駐類啟動：_placement_estimate；_rewrite_gains（activation_round_points）",
        "gamble": "預覽的兩個分支（Preview.gamble）加權；失手反噬 ai/gamble.py",
        "grant_skill": "_rewrite_gains；友方支援 _grant_supports",
        "inscribe": "候選估計 rune_estimate（ai/rune.py）",
        "detonate_runes": "ai/rune.py（符文引爆）；預覽事件評分",
        "sacrifice_summon": "候選估計 sacrifice_estimate（ai/summon.py）",
    }
)
"""原語 ID → AI 估值的路徑（給人讀的說明；檢查的是鍵）。"""
