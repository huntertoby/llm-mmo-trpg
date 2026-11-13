# Phase TF-1 計畫：召喚與輔助技的 1 階轉型（伴生、護主、庇佑、援手）

依據：`docs/design/06-技能.md` 6.34.5「召喚與輔助的 1 階轉型」（玩法 PM d71642970）、`docs/玩法決定紀錄.md` #159。
使用者核可：「都按照建議」（專案 PM 轉達）。大標字（`headline_zh`）由玩法 PM 定、專案 PM 轉達。

## 1. 範圍

1 階召喚技、輔助技（沒有傷害的治療、護盾、增益）在第 3 次閃現時多出四種轉型；共通規則（第 3 次、有合法就一定出現、
多種合法時用種子挑一種、照新種類預算重算、欄位滿了先卸下）沿用既有轉型流程，不改。

| 轉型 | 對象 | 新種類 | 行為 |
|---|---|---|---|
| 伴生 `to_passive_companion` | 召喚技 | 被動，時機「戰鬥開始時」 | 開場在身邊召出縮小版召喚物（每場一次；召喚物已達上限時不出現） |
| 護主 `to_reaction_guardian` | 召喚技 | 反應，被近戰擊中時 | 在身邊召出存在 1 回合的縮小版召喚物，立刻替你反咬攻擊者一次 |
| 庇佑 `to_passive_blessing` | 輔助技 | 被動，回合開始時 | 身邊 1 格內生命比例最低的友方（不含自己）受到縮小版的這招 |
| 援手 `to_reaction_aid` | 輔助技 | 反應 | 護盾、增益：身邊友方被敵人瞄準時（命中判定之前）對他施放；治療：身邊友方被敵人攻擊命中後對他施放 |

對敵人施放、不造成傷害的招照原本的「餘波／反擊」兩種轉型（既有 `_hostile_core` 已涵蓋，不改）。

## 2. 引擎與內容要補的能力（守則 4「內容即資料」）

1. **被動時機 `on_battle_start`**（`content/skill_triggers.yaml`）：`begin_battle` 放好單位、算完獨狼後收集一次並結算。
2. **被動對象 `trigger.target: weakest_ally`**（`TriggerSpec`）：`max_distance` 格內、同陣營、存活、不是自己，
   生命比例（hp ÷ max_hp）最低者；同比例取單位 ID 小的。沒有時不觸發、不付代價。必填 `max_distance`。
3. **反應 `reaction.aid: true`**（`ReactionSpec`）：反應的對象改成「被瞄準／受擊的那名友方」。只能搭配
   `ally_targeted` 與新事件 `ally_hit_near`。
4. **反應事件 `ally_hit_near`**：相鄰友方被敵人的攻擊（普攻或技能）命中、傷害結算之後仍存活；另一方是那名友方
   （必須 `aid: true`）。
5. **原語 `summon_beside`（召喚到身邊）**：只用在被動、反應（不在主動），形狀 `self` 或 `single`，唯一效果。
   在持有者相鄰的第一個合法空格（上、右、下、左的固定順序）召出 `unit`，持續 `duration` 輪，
   `power_permille`（100～1000）縮小 HP 與傷害。同一召喚者的召喚物已達上限時不召喚（`effect_fizzled`，
   原因 `summon_limit`），不像主動召喚那樣擠掉最舊的。`strike_other: true`：召出後立刻對形狀 `single`
   的對象（反應的觸發者）普攻一次（打得到才打）。預算沿用 `summon` 的算法，反咬另加一次每輪傷害。
   隨機組合器與 LLM 提議不使用（手寫／轉型專用）。
6. 轉型的縮小幅度、持續回合放在 `content/skill_budget.yaml` 的 `flash_transform`，開進數值工坊（`kind: budget`）。

## 3. 要改的檔案

- 內容：`content/flash_templates.yaml`（只新增四個轉型條目）、`skill_triggers.yaml`、`reactions.yaml`、
  `skill_primitives.yaml`、`skeletons/passive.yaml`、`skeletons/reaction.yaml`、`skill_budget.yaml`、
  `skill_composer.yaml`（`llm_topic.core_exclude`）、`tuning_fields.yaml`。
- 程式：`content/skills/`（`TriggerSpec`、`ReactionSpec`、常數、`SkillDef` 檢查）、`content/battle.py`、
  `content/flash_templates.py`、`engine/skill_triggers.py`、`engine/reactions.py`、`engine/battle.py`（開場）、
  `engine/skills/primitives/summoning.py`、`skillgen/budget.py`、`skillgen/flash_major.py`、
  `skillgen/composer_parts.py`、文字（`narrative/skills.py`、`engine/view.py`、`skillgen/options.py`）。
- 前端只補名詞對照（`render/qIcon/parts.ts` 的別名）；**不碰** LF-3 的五個檔案。

## 4. 驗收條件

1. 1 階召喚技在第 3 次閃現（`make_offer`）有轉型選項，種子決定是伴生或護主；1 階輔助技有庇佑或援手。
2. 既有能轉型的招（有傷害或對敵狀態）的轉型結果不變（新模板排在既有模板之後）；parity 夾具只有預測到的條目變。
3. 引擎測試：開場召出伴生（上限時不出現、每場一次、`lone_wolf` 不受影響）；護主召出 1 回合並反咬；
   庇佑選 1 格內生命比例最低的友方、沒有友方不觸發；援手護盾在命中前、治療在受擊後作用在友方。
4. `ruff check`、`ruff format --check`、`mypy`、`lint-imports`、`trpg content check`、相關測試、一場重播通過。

## 5. 不做

- 平衡量測、模擬報表；不改 `docs/design/`。
- 既有模板的 `headline_zh`、`say_zh`；LF-3 的 API 與前端檔案。
