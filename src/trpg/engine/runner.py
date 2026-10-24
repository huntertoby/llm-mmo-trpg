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

LOG_FORMAT = "trpg-battle-log/70"
"""``/70``（3-50b 後小修，06 6.5）：自己付的沉默也改為「回合結束才生效」
（``dormant``），本回合仍可施法。
同一份輸入的結算可能不同，因此 ``/69`` 的紀錄無法重播。
``/69``（Phase 3-50b）：代價換強度修正——護盾原語多了 ``duration``（``ShieldEffect.duration``）；
自己付的暈眩改為「本回合照常、回合結束才生效」（狀態 ``dormant``，不再歸零本回合 AP 與移動點數）。
同一份輸入的結算可能不同，因此 ``/68`` 的紀錄無法重播。
``/68``（Phase 3-50）：代價換強度——自己付的代價（``cost.self_status``、新的 ``cost.overdraft``）
改為不觸發控制遞減、不受 Boss 硬控轉換；自身狀態多了暈眩（施放後本回合剩下的 AP 與移動點數歸零）、
沉默、流血；新狀態透支（``ap_penalty``：下一個回合開始時少 1 AP）。同一份輸入的結算可能不同，
因此 ``/67`` 的紀錄無法重播。
``/67``（Phase 3I-6）：臨時附魔與攻擊元素的優先順序——狀態多了 ``attack_element``（新狀態火焰
附魔、神聖附魔）；普攻元素依「附魔 ＞ 普攻附加 ＞ 武器元素詞條 ＞ 武器本身」決定（原本武器本身的元素
優先於普攻附加），沒有自己元素的武器技也吃附魔。同一份輸入的結算可能不同，因此 ``/66`` 的紀錄無法
重播。
``/66``（Phase 3I-4）：第二批其他武器——武器多了 ``paired``、``strikes``（雙匕首普攻打兩下）；
新武器雙匕首、霰彈槍、手槍、雙手槍；成對武器占雙手。
同一份輸入的結算可能不同，因此 ``/65`` 的紀錄無法重播。
``/65``（Phase 3-48e）：刻印 ``inscribe`` 只刻在影響的格子（``affects: tiles``）；其他對象
不再刻在單位腳下，改發 ``effect_fizzled``（``inscribe_needs_tiles``）；規則包的原語 ``inscribe``
多了 ``forbid_affects``。``/64`` 的紀錄無法重播。
``/64``（Phase 3I-2）：副手——物品多了 ``offhand``/``offhand_def``（圓盾強化格擋；
塔盾：遠程攻擊打持有者時命中同半掩護、持有者移動 −1；法書：法術技傷害 +10%；法器珠：法術技施放距離
+1），裝備快照內容不同。同一份輸入的結算可能不同，因此 ``/63`` 的紀錄無法重播。
``/63``（Phase 3I-1）：錘的雙屬性改取較高（同類取較高、一物理一心智取平均，#46）；新武器拳套
（內建反應「反擊」``counter_attack``，事件 ``hit_by_melee``；手上武器有 ``counter`` 的單位用預設規則
時格擋規則預設 ``off``）、鐮刀（收割：目標當下 HP ≤ 30% 時普攻與武器技傷害 +25%）、鞭（射程 2；
纏繞：狀態 ``entangled``，下回合移動點數減少）。同一份輸入的結算可能不同，
因此 ``/62`` 的紀錄無法重播。
``/62``（Phase 3H-6）：武器技的命中、傷害、對抗與專精看施放者手上武器的縮放屬性（雙屬性武器
取較高／取平均），技能自己的 ``scaling_attr`` 對武器技不生效。同一份輸入的結算可能不同，因此
``/61`` 的紀錄無法重播。
``/61``（Phase 3H-5）：主角的耐力每回合開始回復（``core.yaml`` 的 ``resources.stamina_regen``，
不超過上限），``turn_started`` 多了 ``stamina``／``max_stamina``／``stamina_gained``；單位狀態多了
``stamina_regen``。同一份輸入的結算可能不同，因此 ``/60`` 的紀錄無法重播。
``/60``（Phase 3H-2）：武器技花耐力（``cost.stamina``）、主角的法力與耐力上限依屬性
（``core.yaml`` 的 ``resources``）；``skill_used``／``skill_triggered``／``skill_infused`` 多了
``stamina``／``stamina_after``。同一份輸入的結算可能不同，因此 ``/59`` 的紀錄無法重播。
``/59``（Phase 3H-1）：屬性的常駐數值（力量：撞擊傷害 ±、智力：表面與持續區域 +回合、
感知：反應攻擊命中 +、看見隱蔽單位的距離 +、自動看見附近敵方陷阱（可能多出 ``trap_revealed``）、
意志：控制的抵抗 +）、雙屬性武器的取法（``attr_mode``：輕武器取較高、重武器取平均）、
易傷的抵抗屬性改智力；同一份輸入的結算可能不同，因此 ``/58`` 的紀錄無法重播。
``/58``（Phase 3-41b）：``damage_dealt`` 事件多了 ``flat``／``scaled_permille``／
``scale_attr``／``block_permille``（戰鬥紀錄把傷害組成分項顯示用），事件內容不同，
因此 ``/57`` 的紀錄無法重播。
``/57``（Phase 3E-2a，接在 3-33f2 的 ``/56`` 之後）：帶變奏的技能不能被 ``copy_skill`` 複製、
命中後修正規則改用實際施放的型態比對；帶變奏技能的邊角情況結果可能不同，
因此 ``/56`` 的紀錄無法重播。
``/56``（Phase 3-33f2，接在 3-33f1 的 ``/55`` 之後）：召喚技能分歧進化與
召喚詞條——``summon`` 效果多了 ``power_permille``／``max_hp_permille``／``trait``／``infusion``
且 ``count`` 可為 2，單位狀態多了 ``bonus_infusion``／``summon_power_permille``，
新觸發時機 ``on_summon_downed``（召喚物倒下時）、新詞條（召喚冷卻／持續／獻祭加成、
召喚物倒下時爆炸或治療、召喚物繼承普攻附加），
召喚物的傷害倍率與持續輪數可能不同，因此 ``/55`` 的紀錄無法重播。
``/55``（Phase 3-33f1，合併時定號）：召喚物依定位的 HP 係數、召喚專精（群召、精英召喚）改變
上限／持續／傷害，單位範本多了 ``role``。``/54``（Phase 3-33e2a，接在 3-33e2b 的 ``/53`` 之後；
合併時定號）：召喚物（二）a——範本多了
``detonate``（自爆）、``inert``（不行動）與標籤 ``immovable``／``topplable``／``blocks_sight``，
新事件 ``summon_detonated``／``wall_toppled``、``push_resisted`` 多了 ``reason``、``move_blocked``
多了 ``immovable``、召喚物消失原因多了 ``detonated``／``toppled``，石像不會被推動、土牆擋視線
也能被推倒，召喚技能的預算與 AI 估值計入召喚物特性（持續輪數調整），因此 ``/53`` 的紀錄無法重播。
``/53``（Phase 3-33e2b，接在 3-33e1 的 ``/52`` 之後；PM 合併時定號）：召喚物（二）b——範本多了
``snare``／``platform``／``inert``、``pulse`` 多了護盾與拉扯，單位狀態多了 ``snare_round``／
``platform_pos``，新事件 ``snare_triggered``／``summon_pulled``，灌注失效多了原因
``downed``／``gone``；
會飛的單位（``flying``）移動不看高度差與障礙、不受地面表面影響，因此 ``/52`` 的紀錄無法重播。
``/52``（Phase 3-33e1，接在 3-33d 的 ``/51`` 之後）：灌注關鍵字補齊到 10 個
（``summon_infusions``）、召喚物範本的固有灌注／命中特性／脈動（``innate``、``hit_rules``、``pulse``）、
單位狀態多了 ``trip_round``、新狀態「戰意」（``attack_bonus``，戰意圖騰改版），召喚物的 HP、命中
後效果與回合開始都可能不同，因此 ``/51`` 的紀錄無法重播。
``/51``（Phase 3-33d，接在 3-33c 的 ``/50`` 之後；PM 合併時定號）：灌注技能——單位狀態多了
``infused_skill``／``infused_round``，新動作 ``infuse_skill``（1 AP），新事件 ``skill_infused``／
``infused_skill_cast``／``infusion_fizzled``；召喚物在自己回合開始時施放灌注的技能，效用 AI 的施放者
會灌注，因此 ``/50`` 的紀錄無法重播。
``/50``（Phase 3-33c，接在 3-32a 的 ``/49`` 之後；PM 合併時定號）：召喚物操控——單位狀態多了
``summon_mode``／``summon_target_id``／``commanded_round``，新動作 ``set_summon_mode``（0 AP）與
``command_summon``（1 AP），新事件 ``summon_mode_set``／``summon_commanded``；召喚物的 AI 依模式行動
（跟隨預設會待在召喚者附近、圖騰預設待命）、召喚技能的 AI 估值納入成長與灌注、我方 AI 施放者會自動
切換模式，因此 ``/49`` 的紀錄無法重播。
``/49``（Phase 3-32a，接在 3-33b 的 ``/48`` 之後）：普攻流——單位狀態多了 ``attack_hits_landed``
（普攻連擊的普攻命中計數）、武器參數多了 ``high_range``／``backstab_dice``，普攻會因連擊
（多攻擊一次，``gear_triggered.trigger == "attack_combo"``）、分裂（``"attack_cleave"``）、
主動技能欄的空格（普攻精通）與武器特性強化而結果不同；``/48`` 的紀錄無法重播。
``/48``（Phase 3-33b，接在 3-25a 的 ``/47`` 之後）：召喚物基本規則——召喚物的 HP 與傷害依施放者
等級與屬性成長（``UnitTemplate.level``、``summon_growth``）、``UseSkill.infusion`` 灌注關鍵字、
持續輪數上限、硬上限、Boss 對召喚物傷害 ×2；召喚物數值與傷害在 ``/47`` 的規則下不同，``/47`` 的
紀錄無法重播。
``/47``（Phase 3-25a，接在 3-29 的 ``/46`` 之後）：戰場變奏——技能可帶 ``variants``，條件成立時
施放變奏型態（形狀、射程、元素、附帶效果不同），施放事件 ``skill_used`` 多了 ``variant``；
同一份動作在 ``/46`` 的規則下合法性與結果可能不同，``/46`` 的紀錄無法重播。
``/46``（Phase 3-29，接在 3-26a 的 ``/45`` 之後）：直線衝撞 ``charge_through`` 的目標格
可以是射程內直線上的任何格（站著敵人、牆前、地圖邊），停在最後一個空格；目標格的敵人背後
走不過去時命中後另受一次撞擊（``collided``）。同一份動作在 ``/45`` 的規則下結果不同，
``/45`` 的紀錄無法重播。
``/45``（Phase 3-26a，接在 3G-G3b 的 ``/44`` 之後）：單位狀態多了技能等級 ``skill_levels``、
技能等級的效果倍率（傷害、治療、護盾）與 5 級小特性（範圍 +1／冷卻 −1）；``/44`` 的紀錄無法重播。
``/44``（Phase 3G-G3b，接在 3-24c 的 ``/43`` 之後）：裝備的授予動作、授予反應與改變規則——
授予的技能併進單位的 ``skills``（開戰時由裝備快照決定）、單位的反應規則多了裝備授予或擴充的
規則（反應事件
``ally_hit_in_range``、內建反應 ``redirect_damage``、反應定義 ``effect: redirect_damage``）、
單位狀態 ``gear_round_counts`` 多了 ``extra:<反應>``（額外觸發次數）、裝備規則
``caps.rule_affixes``、新技能 ``skill_gear_*``；裝備的規則改變查詢走 ``active_rule_change``。
``/43`` 的紀錄無法重播。
``/43``（Phase 3-24c，接在 3G-G3a 的 ``/42`` 之後）：新條件 ``target_collided``
（單位的 ``collided_round``）、新原語
``sacrifice_summon``（召喚物消失原因 ``sacrificed``）、火器的武器技也算開火（消耗彈匣、槍聲、站定、
距離修正）；``/42`` 的紀錄無法重播。
``/42``（Phase 3G-G3a）：裝備的觸發與充能——新動作 ``activate_charge``、新事件
``gear_triggered``／``charge_activated``、單位狀態 ``gear_turn_counts``／``gear_round_counts``／
``ap_gain_turn``、詞條欄位（觸發的 ``tag``／``status``／``surface``、充能的
``effect_target``）、層數 ``fury``。
``/41`` 的紀錄無法重播。
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
