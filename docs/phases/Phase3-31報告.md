# Phase 3-31 報告｜普攻與符文

> 規格：`docs/phases/Phase3計畫.md` 第 34 節；設計：`docs/design/06-技能.md` 6.25「普攻與符文」、`docs/design/08-裝備.md` 8.24（`affix_attack_rune_*` 三列）。
> 所有數值都是初值，放在 `content/`，未經模擬。

## 1. 交付內容

### 1.1 引擎規則

| 項目 | 做法 | 位置 |
|---|---|---|
| 讀取符文（加傷） | 普攻傷害計算多一個來源：目標格有自己的符文時 +N‰（詞條擲 100～150，被動 150）。與其他傷害加成**合計後**再套全身 +50% 上限 | `engine/modifiers.py` `damage_permille`、`engine/gear_enhance.py` `gear_rune_read_permille` |
| 單格引爆 | `on_hit_effects` 允許清單加入 `detonate_runes`，並新增 `EffectSpec.scope: target_cell`（只引爆被命中目標所在的那 1 格；`on_hit_effects` 內必填，主動技能不可填）。既有的範圍引爆不受影響 | `content/skills.py`、`engine/skills/interpreter.py` `detonate_runes` |
| 留下符文 | `on_hit_effects` 允許清單加入 `inscribe`（目標格、元素可設定，被動預設雷紋 2 輪）。每人 6 格上限、超過時最舊的消失，沿用 3-23 的 `inscribe_rune` | 同上 |
| 每回合最多 1 次 | `ModifierSpec.per_turn_limit: 1`（只能用在 `damage_permille`〔且只套普攻〕與 `on_hit_effects`）。計數存在 `UnitState.gear_turn_counts`（既有欄位，自己回合開始時清除；鍵為 `rule:<技能 id>:<規則索引>` 或詞條 id），可序列化、可重播，不新增狀態欄位 | `engine/modifiers.py`、`engine/skill_triggers.py` |
| 詞條形式 | `AttackAffix` 新增 `rune: read／detonate／inscribe`、`dice`（引爆）、`rune_element`、`rune_rounds`（刻印）。引爆與刻印走 `gear:attack_rune`（`gear_triggered`，`trigger: attack_rune`）；讀取走傷害計算 | `content/equipment.py`、`engine/gear_triggers.py`、`engine/skill_triggers.py` |
| 驗證器 | 同一件裝備不能同時有 `inscribe` 與 `detonate`：`item_problems`（物品）與 `loadout_problems`（穿戴快照）；同一個被動不能同時有刻與引爆：`SkillDef` 驗證（跨規則也檢查）。中文錯誤訊息共用 `RUNE_BOTH_MESSAGE` | `content/equipment.py` `rune_pair_problems`、`content/skills.py` |
| AI | 不新增權重。普攻評估走預覽事件，讀取加傷與引爆傷害自然計入；只補 `has_rune_reader`，讓持有普攻符文被動或詞條的單位也會先刻再引 | `engine/ai/rune.py` |

### 1.2 內容

- `content/affixes.yaml` 三條（部位照 8.24）：

| id | 文字 | 部位 | 初值 |
|---|---|---|---|
| `affix_attack_rune_read` | 你的普攻打到站在你符文上的敵人時，傷害 +N（每回合 1 次） | 武、手、戒 | 100～150‰ |
| `affix_attack_rune_detonate` | 普攻命中時，引爆目標格上你的符文（每回合 1 次） | 武、手 | 1d6（元素取符文） |
| `affix_attack_rune_inscribe` | 普攻命中時，在目標格刻下雷紋（每回合 1 次，持續 2 輪） | 武、手 | 雷紋、2 輪 |

- 三招刻印類修正型被動（`kind: modifier`、套在普攻，**請玩法 PM 審名稱與稀有度**）：

| id | 名稱 | 稀有度 | 階級 | 內容 | 關鍵字 |
|---|---|---|---|---|---|
| `skill_rune_sight` | 識紋 | epic | 1 | 普攻打到站在你符文上的敵人：傷害 +15%（每回合 1 次） | 利用：標記（讀取符文） |
| `skill_rune_breaker` | 破紋 | epic | 1 | 普攻命中時引爆目標格上你的符文（只那 1 格），1d6 符文傷害（每回合 1 次） | 利用：標記 |
| `skill_rune_etcher` | 刃刻 | epic | 2 | 普攻命中時在目標格刻下雷紋，持續 2 輪（每回合 1 次） | 製造：帶電、標記 |

  修正型被動的骨架最低稀有度本來就是 epic（`content/skeletons/modifier.yaml`），所以三招都取最低值 epic。

- 預算（`content/skill_budget.yaml` 的 `modifier:` 新增兩個旋鈕，皆為初值）：
  - `per_turn_limit_uses: 8`：帶 `per_turn_limit` 的規則，每場使用次數不看 `uses` 表，固定估 8 次。
  - `on_hit_rune_permille: 270`：命中後效果裡的 `inscribe`、`detonate_runes` 點數 ×0.27（符文單獨沒有效果、要搭配讀取者）。
  - 結果：識紋 72%（階級 1）、破紋 75.6%（階級 1）、刃刻 96%（階級 2）。刃刻要到階級 2 才不超預算（刻印原語單次 4 點太貴）；出貨技能的階級目前只允許 1、2（`test_calibrate`）。
- 技能工坊的選項文字：`skillgen/option_params.py` 加入 `scope` 的顯示名稱與選項（只動這兩處，未動組合器或進化模板）。

## 2. 驗收證據

| 驗收項目 | 證據（`tests/engine/test_attack_runes.py` 除非另註） |
|---|---|
| 三種效果各自觸發（詞條與被動都有） | `test_read_adds_damage_on_own_rune_once_per_turn_and_resets[affix／passive]`、`test_detonate_removes_only_the_target_cell_rune_once_per_turn[…]`、`test_inscribe_leaves_a_two_round_rune_on_the_target_cell[…]` |
| 每回合只觸發 1 次、下一回合重置 | 上列三個測試都包含「同回合第二次不再觸發」與「下一回合重置」（讀取、引爆；刻印驗證同回合第二次不再刻） |
| 單格引爆只移除目標格符文 | `test_detonate_removes_only_the_target_cell_rune_once_per_turn`：另一格符文保留；`test_detonate_without_a_rune_on_the_target_does_nothing` |
| 刻印 2 輪後消失、6 格上限 | `test_inscribe_leaves_a_two_round_rune_on_the_target_cell`（`remaining == 2`、過 2 輪 `expired`）、`test_inscribe_respects_the_six_rune_limit_per_owner`（最舊的以 `limit` 消失） |
| 加傷計入 +50% 上限 | `test_read_counts_toward_the_damage_bonus_cap`（讀取 ＋ 被動 ＋ 代價型合計超過 +50%，截斷為 1500‰） |
| 同件裝備／同被動「刻＋引爆」被擋 | `test_one_item_cannot_inscribe_and_detonate`、`test_one_passive_cannot_inscribe_and_detonate`（含同規則與跨規則）；`test_two_items_may_split_inscribe_and_detonate` 確認分開兩件可以 |
| 詞條擲出與部位 | `test_rune_affixes_only_appear_on_the_listed_slots`、`test_read_affix_rolls_ten_to_fifteen_percent`；`tests/content/test_equipment_content.py`（白名單 34 條、往返 schema） |
| 被動過預算、有關鍵字與圖示 | `test_rune_passives_pass_budget_have_keywords_and_icons`、`test_rune_passive_keywords_read_or_make_runes`；圖示 fixture 已重產 |
| schema 新欄位 | `test_modifier_schema_for_the_new_fields`（`scope` 必填、`per_turn_limit` 限制、`element/tag` 恰好一個） |
| 同種子確定、重播一致 | `test_same_seed_gives_the_same_events`、`test_full_battle_with_attack_runes_replays_identically`（整場自動戰鬥：重播事件與最終狀態逐位元相同） |
| 其餘 | `ruff check`、`ruff format --check`、`mypy` 全過；`scripts/check.py` 結果見第 4 節 |

## 3. 待 PM 決定

1. **`LOG_FORMAT` 未遞增（仍 `/47`）**：沒有新增或改欄位的事件（`gear_triggered.trigger` 多一個字串值 `attack_rune`），狀態也沒有新欄位；舊紀錄重播結果不變。若 PM 認為新規則需要新號，合併時再定。
2. **三招被動的名稱與稀有度**（識紋、破紋、刃刻；皆 epic）請玩法 PM 審；刃刻階級 2 是為了符合預算；若要回到階級 1，需要再降低刻印的預算係數。
3. **預算旋鈕**（`per_turn_limit_uses: 8`、`on_hit_rune_permille: 270`）是為了讓三招落在 70%～100% 的折衷，不是平衡結論；建議平衡階段一併檢視。
4. **詞條引爆傷害 1d6**（規格只寫「依符文」）：用法術公式 ＝ 骰值 ＋ 縮放屬性 × 0.5，縮放屬性取持有者最高屬性（同其他裝備觸發詞條）。
5. **`damage_permille` 的「每回合 1 次」僅限普攻**：修正規則帶 `per_turn_limit` 的傷害加成只能 `applies_to.actions`（不接受 `all_attacks`／技能標籤），因為只在普攻結算處記帳；既有的 `skill_rune_resonance`（所有攻擊 +15%，無次數限制）不變。
6. **讀取加傷同一個詞條 id 多件只生效 1 條**（普攻附加類屬非數值類別，原本就同 id 只生效 1 條）；詞條版與被動版可以並存，各自限 1 次、合計仍受 +50% 上限。
7. **命中後符文效果要求目標仍存活**（沿用既有 `on_hit_effects` 規則）：普攻直接擊殺目標時，不刻印也不引爆。
8. **未新增權重的 AI**：普攻符文只在 `has_rune_reader` 層面讓單位肯刻印；若要讓 AI 更積極把普攻目標選在自己的符文上，需要新增權重，留待後續。

## 4. 完整檢查

（見提交時的結果）
