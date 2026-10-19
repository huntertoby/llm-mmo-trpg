# Phase 3D-4a 報告：召喚（引擎）

## 1. commit

| commit | 內容 |
|---|---|
| bdc20d1 | `summon` 原語與骨架啟用、召喚物範本（`content/units/summons/`，嵌入規則包）、`summon_limit_per_owner`；引擎：召喚、插入行動順序、到期、召喚者離場、上限、勝負條件／撤離／源力排除；視圖與事件文字、模擬指標、預算、組合器排除；網頁 OpenAPI／型別重產與「已消失的召喚物不畫」；示範技能「喚起骷髏」；引擎、資料、文字測試 |
| d6745c9 | 召喚者 AI（評分與選位）、召喚物由效用 AI 行動；`build_trapper` 裝上示範技能；API 拒絕對召喚物下個別戰術指令；AI、整場、重播與 API 測試 |
| bcd2a96 | `LOG_FORMAT` 升為 `/23`、CLI 快照重錄 |
| （本報告） | 報告 |

開發期間我沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 資料

- `content/skeletons/summon.yaml`：`enabled: true`。
- `content/skill_primitives.yaml` 新原語 `summon`：`{type: summon, unit: <範本 ID>, duration: N, count: 1}`；形狀只能 `ground_tile`、`acts_on: caster`、稀有度至少 rare；參數 `unit`（新參數型別 `summon`，載入時檢查範本存在）、`duration`（1–4，必填）、`count`（只能 1，省略為 1）。`EffectSpec` 新欄位 `unit`、`count`。
- `SkillDef` 的檢查（`_check_summon`）：只能用在主動技能、最多一個召喚效果、`count` 只能 1、其餘效果必須明寫 `affects: self`（選的格子是召喚位置，必須是空格）。
- 召喚物範本 `content/units/summons/`（沿用單位範本 schema，新欄位 `summon: true`）：
  - 元素之靈 `summon_elemental_spirit`：HP 14、速度 5、火焰法杖（射程 5，1d6 火）、`archer` 模式、元素抗性 250‰。
  - 骷髏戰士 `summon_skeleton_warrior`：HP 20、速度 4、單手劍（1d8）、`brute` 模式。
  - 兩者 `reactions: []`（不格擋、不藉機攻擊，見待決 #3）。
- 載入：`units/summons/` 的範本連同武器放進 `SummonTable`，**嵌入規則包** `Ruleset.summons`（重播不依賴資料檔；`Ruleset.summon_def()` 查表）。`units/` 底下寫 `summon: true`、或 `summons/` 底下沒寫，都報錯；召喚物不在 `library.units`，不能直接參戰。
- `content/rules/core.yaml`：`summon_limit_per_owner: 2`。
- 預算（`skill_budget.yaml` 新 `summon_round_value_permille: 800`）：點數 ＝ 召喚物每輪預估傷害（武器骰平均 ＋ 固定傷害，`content.summons.summon_dpr`）× `duration` × 800‰。
- 隨機組合器不產生召喚（骨架加入 `_HAND_WRITTEN_ONLY`、原語加入 `_HAND_WRITTEN_PRIMITIVES`），既有種子的組合結果不變。
- 示範技能 **喚起骷髏** `skill_raise_skeleton`（稀有 T1、AP 1、法力 6、冷卻 3、指定格射程 3、召喚骷髏戰士 2 輪；預算 87.2% 合格），裝在 `build_trapper`（原本 4 個主動，有空位；3D-4b 再整理到召喚師 build）。

### 2.2 引擎（`trpg.engine.summons`、`lifecycle`、`turns`）

- **召喚**（`summon_unit`）：召喚物屬於召喚者陣營、`owner_id` 記錄召喚者、`summon_expires_round` ＝ 施放輪 ＋ `duration`、源力 0、`ai_profile` 取範本；名稱為範本名 ＋ 編號（骷髏戰士1）。單位 ID 照建立順序分配（`unit_NNNN`）。事件 `unit_summoned`（召喚者、技能、到期輪、插入位置）。位置在結算時又被占用或範本不存在時 `effect_fizzled`（`summon_blocked`／`unknown_summon`）。
- **行動順序**：插入先攻順序中召喚者之後、同一召喚者已有的召喚物之後（不擲先攻；`initiative` 只抄召喚者的值供顯示）。插入點在目前位置之前時 `turn_pos` 跟著移動。召喚者在自己的回合施放時，召喚物這一輪就緊接著行動。
- **到期**：召喚者的回合結束（`end_turn`，在 `turn_ended` 之前；被暈眩跳過的回合也算）時，`summon_expires_round` ≤ 目前輪數的召喚物消失，所以召喚物恰好行動 `duration` 次。
- **消失**（`lifecycle.dismiss_summon`）：新旗標 `UnitState.dismissed`（`alive` 為假），移出先攻順序、移除姿態／以它為來源的嘲諷與恐懼／它的陷阱，事件 `summon_expired`（原因 `expired`、`owner_gone`、`limit`）。**不是倒下**：沒有 `unit_downed`、不觸發倒下相關的反應與被動。消失的單位保留在 `units` 中（事件與紀錄仍查得到名字）。
- **召喚者倒下或撤離**：`down_unit`、`escape_unit` 一併讓它的召喚物消失（`owner_gone`）。
- **上限**：召喚前，同一召喚者仍在場的召喚物數 ≥ `summon_limit_per_owner` 時，依召喚順序讓最舊的先消失（`limit`），再放新的。
- **勝負與其他規則**（`UnitState.is_summon`）：全滅判定不看召喚物（`objectives.check_battle_end`）；守點只看非召喚物的敵人；召喚物走到出口不撤離；召喚物不取用源泉、它擊倒的精英沒有人得到源力；`battle_result` 的我方清單不含召喚物（不帶出戰鬥、不給經驗）。
- 目標選取：`targeting.summon_site_problem`（地圖內、可站立、不是致命地形、沒有單位），`legal_actions` 只列出可召喚的格子。

### 2.3 AI

- 召喚物由效用 AI 控制（範本的 `ai_profile`）；CLI、模擬、網頁都一樣（網頁只有主角由玩家操控，召喚物自動行動）。網頁 API 拒絕對召喚物下個別戰術指令（全隊指令照常適用）。
- 召喚者（`engine/ai/summon.py`）：
  - 選位置（便宜估計，`skill_estimate`）：召喚位置越靠近最近的敵人越好，沒有敵人不納入。
  - 評分（預覽收益）：新召喚物的 `summon_dpr` × 剩餘輪數 × `damage` 權重 × 命中折合 1/2，再扣召喚位置與最近敵人的距離 × 1/10（完整評分也偏好靠近敵人）；因超過上限而消失的舊召喚物，扣掉它剩餘輪數的同樣價值。

### 2.4 視圖、事件、紀錄、網頁

- `UnitView` 新欄位 `owner_id`、`summon_expires_round`、`dismissed`；`turn_order` 自然含召喚物。`project_for`、`filter_events` 不需要新規則（召喚與消失雙方都看得到），測試確認。
- CLI 紀錄：「X 召喚了 骷髏戰士1，出現在 (2, 3)（緊接在 X 之後行動，第 6 輪 X 的回合結束時消失）」「時間到了／召喚者離場／超過同時存在的上限，最舊的召喚物：骷髏戰士1 消失了」；單位表的召喚物不顯示源力，消失者顯示「已消失」；`trpg skills show` 有召喚效果的說明。
- 網頁（最小，不加樣式）：重產 `openapi.json`／`schema.d.ts`；`onField`／`isAlive` 與各處「還在場上」的判斷加上 `!dismissed`（畫面、行動順序列、點選、指令目標都不再出現已消失的召喚物）。召喚物照一般單位畫出。
- 模擬指標：`unit_summoned` 算出場、`summon_expired` 算離場（同援軍與撤離）。

## 3. 驗收條件逐條（3D-4a）

### 驗收 1：召喚、行動順序、到期、召喚者倒下、上限、勝負判定

| 項目 | 證據 |
|---|---|
| 召喚 | `tests/engine/test_summons.py::test_summon_places_an_allied_unit_owned_by_the_caster`（陣營、`owner_id`、位置、名稱、HP、源力 0、AI 模式、到期輪） |
| 位置限制 | `test_summon_site_must_be_empty_standable_and_not_deadly`（有單位、深淵不合法；`legal_actions` 不列出） |
| 緊接召喚者行動 | `test_the_summon_acts_right_after_its_owner_without_rolling_initiative`（先攻順序在召喚者後一位；召喚者結束回合後下一個 `turn_started` 是召喚物）、`test_summons_of_the_same_owner_queue_in_summon_order`；整場：`tests/engine/test_summon_ai.py::test_the_ai_casts_the_summon_and_the_summon_acts`（召喚者與召喚物的回合之間沒有別人） |
| 到期 | `test_the_summon_acts_duration_times_and_expires_at_the_owner_turn_end`（duration 2 → 恰好 2 個回合；第 3 輪召喚者 `turn_ended` 之前 `summon_expired: expired`；移出順序、格子空出） |
| 召喚者倒下 | `test_the_summon_disappears_when_its_owner_goes_down`（`owner_gone`，不是倒下） |
| 上限與最舊者消失 | `test_the_oldest_summon_disappears_over_the_limit`（第 3 隻讓第 1 隻 `limit` 消失；順序與 `turn_pos` 正確）、`test_the_limit_comes_from_the_core_rules`（覆寫為 1） |
| 勝負不看召喚物 | `test_victory_ignores_summons`（敵方只剩召喚物 → 我方勝）、`test_an_ally_side_of_only_summons_loses`、`test_an_enemy_summon_on_the_defend_point_does_not_take_it`、`test_a_summon_cannot_escape` |
| 源力、結果 | `test_summons_have_no_source`、`test_summons_do_not_take_source_wells`、`test_battle_result_excludes_summons` |

**既有勝負條件確認**：`eliminate`／`escaped` 改為只看非召喚物（召喚物不能撤離，所以 `escaped` 的判斷不受影響）；`escape_failed`、`round_limit` 不看單位；`defended`／`point_lost` 只看非召喚物的敵人；`check_round_end` 先呼叫 `check_battle_end`，所以每輪判定同樣不看召喚物。

### 驗收 2：視圖、事件過濾、序列化、重播

| 項目 | 證據 |
|---|---|
| 序列化 | `test_summons_survive_serialization_and_replay_resolution`（含召喚物與已消失召喚物的狀態 JSON 往返一致，往返後繼續結算到消失） |
| 視圖與事件過濾 | `test_views_show_summons_and_dismissal_to_both_teams`（雙方視角都有召喚物、`owner_id`、`summon_expires_round`、`turn_order`；消失後 `dismissed` 且不在順序中；`filter_events` 雙方都看得到 `unit_summoned`、`summon_expired`） |
| 重播 | `test_summon_ai.py::test_a_summoning_battle_replays_exactly`（swamp 種子 1、`build_trapper`：重播的狀態 JSON 與事件逐字相同） |
| API | `tests/api/test_summon_api.py::test_the_hero_summons_and_the_summon_acts_on_its_own`（預覽、施放、事件帶 `text`、`view` 的召喚物欄位、主角結束回合後召喚物自動行動）、`test_summons_take_no_individual_orders` |
| 網頁 | `client/src/battle/drawModel.test.ts`「draws summons like other units and removes dismissed summons」；client typecheck |
| 文字 | `tests/narrative/test_summon_text.py::test_summon_and_expiry_have_log_lines` |
| 資料 | `tests/content/test_summon_content.py`（14 個：範本載入與位置、原語參數錯誤、schema 規則、預算公式） |

### 驗收 3：AI、`sim completion`、`check.py`

- AI 會施放召喚、召喚物會行動：`test_the_ai_casts_the_summon_and_the_summon_acts`；評分與選位：`test_summon_gains_are_dpr_times_rounds_minus_distance`、`test_replacing_the_oldest_summon_costs_its_remaining_value`、`test_the_estimate_prefers_tiles_next_to_the_enemy`、`test_the_ai_summons_next_to_the_enemy_when_it_cannot_attack`。
- 另以小腳本（不是正式模擬）跑 `build_trapper` × 10 張地圖 × 種子 0–2（30 場）：召喚 13 次、召喚物回合 19 次、攻擊 17 次、30 場全部分出勝負。
- `uv run trpg sim completion --seeds 3`（只跑一次）：270 場，**異常合計：exception 0、max_actions 0、draw 0 —— 通過**。
- `uv run python scripts/check.py`（只跑一次）：ruff、format、mypy、lint-imports、pytest（**2345 passed**）、client install、typecheck、vitest（**111 passed**）——**全部檢查通過**。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/skillgen/test_validate.py::test_each_enabled_skeleton_has_a_valid_example` | 啟用的骨架多了 `summon`，加入示範技能當例子 |
| `tests/skillgen/test_validate.py::test_disabled_skeletons_are_rejected` | 原本以 `summon`（唯一停用的骨架）驗證拒絕規則；改為用停用的複本驗證，並確認啟用後不再被拒絕 |
| `tests/content/test_skill_rules_content.py` | `ENABLED` 加入 `summon` |
| `tests/cli/test_budget_cli.py` | 技能總數 104 → 105 |
| `tests/cli/test_striker_trapper_battle.py::test_the_new_builds_have_the_specified_skills` | `build_trapper` 多裝了示範技能（5 → 6 個技能） |
| `tests/cli/test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/22` → `/23` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 重錄（新增 1 個技能）；所有戰鬥類快照沒有變 |
| `client/src/battle/testFixtures.ts` | `UnitView` 多了三個欄位 |

## 5. 新增的複雜度 noqa

沒有 C901、PLR0911、PLR0912、PLR0915。開發中 `content.skills._value_problem` 超過 PLR0911（拆出 `_reference_problem`，以表格查引用類參數）、`targeting._tile_area` 超過 PLR0912（拆出 `_site_problem`，陷阱與召喚的放置格檢查）。新增的非複雜度 noqa：`summons.summon_unit`、`content.skills._reference_problem` 的 `PLR0917`（位置參數個數，沿用專案中同類函式的做法），測試內延後匯入的 `PLC0415`。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/23`**（本段只升一次）：規則包多了 `summons` 與 `summon_limit_per_owner`、單位範本多了 `summon`、單位狀態多了 `owner_id`／`summon_expires_round`／`dismissed`、`EffectSpec` 多了 `unit`／`count`、新事件 `unit_summoned`／`summon_expired`、新的 `effect_fizzled` 原因；`/22` 的規則包缺這些欄位，不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **持續輪數的算法**：`duration: N` ＝ 召喚物恰好行動 N 次——在「施放輪 ＋ N」輪召喚者的回合結束時消失（施放當回合的結束不算）。若要「施放回合結束就算 1 輪」需改一行。
2. **召喚出現時不觸發落點效果**：同地圖援軍（`UnitSpawned`），不結算表面進入效果與陷阱；之後的回合開始照常結算表面。可以召喚在自己陣營的陷阱上（實際發生在 cliff_outpost 種子 1），敵方隱藏陷阱的格子也不擋（不洩漏）。
3. **召喚物沒有反應**：兩個範本都寫 `reactions: []`（不格擋、不藉機攻擊），保守。別人的反應照常把召喚物當一般單位（例如它倒下時，隊友的 `ally_downed` 反應技會觸發；它可以被嘲諷、治療、傳送）。要不要排除召喚物請 PM 決定。
4. **消失不是倒下**：到期、召喚者離場、超過上限都只發 `summon_expired`，不發 `unit_downed`，不觸發倒下相關的反應、被動與精英源力。被打倒的召喚物則是一般的倒下（留在原地、顯示倒下），之後召喚者倒下時不再發消失事件。
5. **源力與勝負的細節**：召喚物擊倒精英時，**召喚者也拿不到**源力（「召喚物沒有源力」的保守解讀）；守點只看非召喚物的敵人；召喚物不能撤離；`battle_result` 不列召喚物（不帶出戰鬥、不給經驗）。
6. **戰術指令**：召喚物照全隊指令行動，但網頁 API 拒絕對召喚物下個別指令（「玩家不能直接操控」的保守解讀）；「保護」指令可以選召喚物當保護對象。
7. **其餘效果只能對自己**：召喚技能的其他效果必須 `affects: self`，`count` 目前只能 1、`duration` 上限 4。若要「召喚＋範圍傷害」之類的組合需另訂。
8. **預算與 AI 係數都是初值**：預算 `summon_round_value_permille` 800‰（示範技能 87.2%）；AI 的命中折合 1/2 與距離扣分 1/10 寫在 `engine/ai/summon.py`（沒有放 `ai_profiles.yaml`）。召喚物 DPR 只算武器骰平均 ＋ 固定傷害，不看屬性與命中。
9. **召喚物在實戰中很快被打倒**：`build_trapper` 30 場中召喚 13 次，其中 9 隻在到期前倒下、沒有一隻活到到期（敵人會優先打靠近的骷髏戰士，20 HP 撐不住；元素之靈還沒有技能使用）。召喚物的強度、召喚師 build 與圖騰請 3D-4b／平衡階段處理。
10. **網頁只做了最小支援**：召喚物照一般單位畫、已消失的不畫、行動順序列跳過；沒有區別標示、剩餘輪數與召喚位置預覽（3D-4b）。`trpg skills show` 的召喚效果後面會帶「（自己）」（`acts_on: caster` 的原語都這樣顯示，同傳送），3C-6 整理文字時可一併處理。

## 8. 代表性輸出

`uv run trpg battle --map swamp --seed 1 --ally-build build_trapper`（連續一段，輸出第 290–318 行）：陷阱流英雄先埋灰燼地雷、再施放「喚起骷髏」召喚骷髏戰士1；英雄結束回合後，骷髏戰士1 緊接著行動（不擲先攻），由 AI 控制攻擊盜賊盾衛；之後盜賊盾衛反過來打骷髏。

```
    盜賊頭目 受到 7 點物理傷害［骰 4］（元素修正 ×0.85），HP 2 → 0
  ＊ 盜賊頭目 倒下了！
  ✦ 標準隊友（戰士） 擊倒了 盜賊頭目，獲得源力：源力 1 → 2
  標準隊友（戰士） 結束回合
— 陷阱流英雄 的回合（AP 3，移動 7，法力 14/40）
  陷阱流英雄 施放「灰燼地雷」（AP 2，法力 8，冷卻 3 回合）→ 影響 1 格
    陷阱流英雄 在 (2, 2) 設下陷阱「灰燼地雷」（2 輪後引爆）
  陷阱流英雄 施放「喚起骷髏」（AP 1，法力 6，冷卻 3 回合）→ 影響 1 格
  陷阱流英雄 召喚了 骷髏戰士1，出現在 (2, 3)（緊接在 陷阱流英雄 之後行動，第 6 輪 陷阱流英雄 的回合結束時消失）
  陷阱流英雄 從 (0, 4) 移動到 (3, 0)（消耗 7 移動）
  陷阱流英雄 的「加速」結束了
  陷阱流英雄 結束回合
— 骷髏戰士1 的回合（AP 3，移動 4）
  骷髏戰士1 攻擊 盜賊盾衛：d20=19 修正 -3 熟練 +2 = 18（目標 11）→ 命中
  ⟳ 盜賊盾衛 反應：格擋（耐力 −10）
    盜賊盾衛 受到 3 點物理傷害［骰 5］（元素修正 ×0.9）（格擋/加成 ×0.5），HP 32 → 29
  骷髏戰士1 攻擊 盜賊盾衛：d20=8 修正 -3 熟練 +2 = 7（目標 11）→ 失手
  骷髏戰士1 攻擊 盜賊盾衛：d20=18 修正 -3 熟練 +2 = 17（目標 11）→ 命中
    盜賊盾衛 受到 6 點物理傷害［骰 4］（元素修正 ×0.9），HP 29 → 23
  骷髏戰士1 結束回合
— 盜賊盾衛 的回合（AP 3，移動 4，法力 4/8）
  盜賊盾衛 的「防禦」結束了
  盜賊盾衛 獲得狀態「防禦」
  盜賊盾衛 攻擊 標準隊友（戰士）：d20=13 修正 -1 熟練 +2 = 14（目標 11）→ 命中
    標準隊友（戰士） 受到 8 點物理傷害［骰 6］（元素修正 ×0.9），HP 14 → 6
  盜賊盾衛 攻擊 骷髏戰士1：d20=14 修正 +0 熟練 +2 = 16（目標 11）→ 命中
    骷髏戰士1 受到 10 點物理傷害［骰 7］，HP 20 → 10
  盜賊盾衛 結束回合
～ 環境回合 ～
```
