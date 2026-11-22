# Phase E1 報告｜裝備授予技能一般化

> 規格 `docs/phases/PhaseE1計畫.md`；規則以 `docs/design/08-裝備.md` 8.28（#174）為準。基準 main `871ca53df`。

## 1. 盤點現況（改動前）

**裝備怎麼授予技能**

| 途徑 | 在哪 | 怎麼運作 |
|---|---|---|
| 第 9 類「授予動作」`ActionAffix` | `content/equipment.py`、`engine/gear/core.py::gear_skill_ids`／`granted_skills`／`geared_template` | 生效的詞條（`gear.active_affixes("action")`）給的技能 ID 依欄位固定順序**接在範本 `skills` 後面、已有的不重複**；`make_unit` 用加過的範本，所以戰鬥中它就在 `UnitState.skills` 裡，和自己學的分不出來 |
| 第 10 類「授予反應」`ReactionAffix` | `engine/gear/reactions.py`、`lifecycle.make_unit` 的 `gear_reaction_rules` | 不是技能：`extend_trigger`（既有反應多一個事件）、`grant`（只有 `redirect_damage`）、`extra_uses`（多幾次）。這段沒動 |
| 暫時授予 `grant_skill` | `engine/grants.py`、`UnitState.granted_skills` | 技能 ID＋剩餘輪數，不佔欄；已有的技能不重複給（只刷新輪數）；經 `UnitState.all_skills` 生效 |
| 裝備的規則改變、觸發詞條 | `engine/activations.py`、`engine/gear/triggers.py` | 臨時組一個 `skill_gear_<詞條>` 的 `SkillDef`，不進技能列 |

**`gear_checks` 擋了哪幾類**：`_action_problems` 只允許 `kind: active`（被動、反應、修正、姿態都擋），另擋會給「無聲」的技能（BS-1）。所以改前只有主動技能由裝備授予。

**`modifiers.py` 的疑點**：`empty_active_slots` 的 docstring 寫「裝備授予的常駐技能、暫時獲得的技能不算」，但它數的是 `unit.skills`，而裝備授予的主動技已經被併進 `unit.skills`（上表第 1 列），所以**裝備給的主動技會佔掉普攻精通的空格**，和 docstring 不符。暫時獲得的技能確實不算（它在 `granted_skills`）。

**欄位上限**：`battle._check_loadouts` 用的是加裝備之前的 `spawn.template.skills`，roguelite、世界、工坊的欄位檢查也都看玩家自己的招式組，所以裝備給的主動技本來就不算進欄位上限；不符的只有上面的普攻精通空格。

**引擎列舉「可以用的技能」是否都經過 `UnitState.all_skills`**：大多是（`battle.legal_actions`、`skills/interpreter`、`modifiers.unit_rules`、AI 的 `gains`／`rune`／`terrain`／`variant`／`scene_objects`、`skill_infusion`）。直接讀 `unit.skills`、因此**看不到暫時獲得的技能**的地方：

- 反應：`reactions._candidate`、`_kin_ward_def`（反應技要在 `unit.skills`）、AI `ai/priority.py`；
- `modifiers.shaped_skill` 的快速路徑（`has_modifier(unit.skills)`）；
- `prep.py`（戰前佈置）、`infusion.py`（灌注）、`ai/self_costs.py`、`ai/utility/skill_estimate.py`、`ai/parts.py`、`grants.grant_skill` 的「已有就不給」；
- `boss_phases.py` 換技能組時整個換掉 `unit.skills`（裝備給的技能也會被換掉；目前沒有帶裝備的頭目）。

裝備授予的技能因為放在 `unit.skills`，上面這些地方都看得到；這段維持這個做法（見第 3 節第 2 項），沒有改這些繞過 `all_skills` 的地方。
