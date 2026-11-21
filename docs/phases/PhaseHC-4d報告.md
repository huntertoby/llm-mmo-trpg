# Phase HC-4d 報告：大世界的預設值搬進 content（HC-4 收尾）

依據：`docs/phases/PhaseHC-4d計畫.md`；HC-4c 報告最後的開發 PM 裁定；做法照 HC-4a～HC-4c。
基準：main `e865b12bf`（worktree 開工時在 `0f4c1f95f`，先 fast-forward）。分支 `worktree-agent-a38f81d8d77f0d4ff`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`。`WORLD_RULES_VERSION` 沒升（2.6）。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 大世界搬家 | `9bf0fc099` | 大世界 schema 的預設值改必填；規則型上下限搬進內容檔、在載入層檢查；結構常數改判 guard／const |
| 2 時段表 | `946236c86` | `world/rules.yaml` 新增 `day_parts`；API `WorldClockView.day_parts`；`hud.ts` 改讀 |
| 3 其餘 content 尾巴 | `7b295f621` | 技能 schema 剩下的規則型上下限搬到 `core.yaml` 的 `skill_limits`；敵人招數下限搬到 `world/enemies.yaml`；`dual_max_gap` 必填 |
| 4 開進工坊 | `e6e9b14f0` | 新開四張全體共用的表（大世界規則、經濟、交易、賽季），21 格 |
| 5 收尾 | `f1f4c4fc3` | 刪掉這段搬完變成 0 筆的 31 條規則 |
| 修正 | `7b67188d9` | `tests/test_hardcoded_scan.py` 的抽查改看搬家後的 `max_self_status_duration` |
| 修正 | `5580626bf` | 工坊新欄位的說明拿掉決定編號與英文欄位名；`scripts/x10/fields.yaml` 列入四張新表的建議範圍 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、`trpg content check` 與相關測試。

## 2. 第 1 項：大世界搬家

### 2.1 預設值改必填（內容檔都有寫、值相同）
| 檔 | 改必填的欄位 |
|---|---|
| `world_rules.py`（`world/rules.yaml`） | `BattleRules` 3 格；`EnemyGrowthRules.skill_tier_by_level`；`XpRules` 3 格（`DEFAULT_SHARES` 刪掉，`XP_SOURCES` 改寫明來源名）；`HeroGrowthRules` 5 格；`OpportunityRules` 3 格；`WishRules` 6 格；`CalendarRules` 2 格；`FieldRules` 11 格；`WorldRules.week_days`（`DEFAULT_WEEK_DAYS` 刪掉）與 7 張子表 |
| `world_season.py` | `DailyGoalRules` 3 格；`WorldEventDef` 2 格；`LeagueRules` 5 格；`BossScore` 4 格；`SeasonBossDef` 的 `daily_attempts`、`score` |
| `world_trade.py` | `TradeCommon` 2 格、`MailRules` 5 格、`TradeAudit` 5 格；`trade`、`audit` 子表 |
| `world_economy.py` | `EconomyRules` 的 `bag_slots`、`pouch_slots`、`stack_max`（`_STACKS` 刪掉，缺項檢查改看 `ITEM_KINDS`）、`sell_permille`、`battle_gold`；`BattleGold` 3 格 |
| `world_crafting.py` | `CraftRules` 2 格；`EnhanceRules` 3 格與 `enhance` 子表；`ResonanceRules.pieces` |
| `world_mercenaries.py`、`world_oaths.py`、`world_newcomer.py`、`world_quests.py` | `max_hired`、`shadow_daily_coins`、`shadow_reports_kept`；`OathTable.penalty_rounds`；`RangeContent.max_rounds`（舊欄位，內容檔有寫）、`reflash_level`；`AffinityRules` 的 `min_value`、`max_value`、`rumors_per_week` |
| `world.py`（`llm/world_shattered.yaml`、`llm/style_eval.yaml`） | `WorldTermRules.name_prefix_len`；`NamingRules` 3 個字數上限與 `world_terms`；`WorldStyle.naming`；`StyleEvalRules.dot_share_max_permille` |
| `roguelite.py` | `StartRules` 2 格；`CandidateSettings` 3 格與 `candidates` 子表；`StartHero.speed` |

- **沒寫的先寫進 content**（值＝原本的程式預設）：`roguelite.yaml` 三個起始主角的 `speed: 5`；`world/season.yaml` 世界事件「封印共鳴」的 `min_target_permille: 250`。
- **「有某欄才用到」改選填**：`OathCheck.hp_permille` 只有 `forbid_skill_tag_until_hp` 用到，改 `int | None`（不填不輸出）；這個種類沒填算缺欄位（`OATH_CHECK_FIELDS`）。
- **主手武器大類 `MainHandMix`**：三格改必填，但內容檔**沒有** `main_hand`（`None`＝一律同大類），所以沒寫進 content（寫了等於打開這個功能）。原本的 500、750、3 從沒生效過，現在只在測試裡。

### 2.2 規則型上下限搬進內容檔，載入時檢查
| 原本 | 搬到 | 值 | 在哪裡檢查 |
|---|---|---|---|
| `races.py` 種族技次數、效果數、視線減免、元素減傷上限 | `races.yaml` 的 `limits` | 2、3、500、250 | `RaceTable` 載入時（訊息同原字句） |
| `world_map.py` `MIN_LOCATIONS`、`MAX_LOCATIONS` | `regions.yaml` 的 `locations_per_region` | [15, 25] | `world_map_problems`（地點圖本來就要有 `regions.yaml`） |
| `fields.py` `LAYOUT_SIZES`、`STONES_PER_REGION` | `world/rules.yaml` 的 `field_maps` | 同原表 | `field_map_report(rules=…)` |
| `world_situations.py` 模板屬性數、方法數；`world_events.py` 骨架情境解法的屬性數 | `situation_rules.yaml` 的 `template_limits` | 2、3、3 | `situation_problems`（模板與該區骨架） |
| `world_mercenaries.py` `MIN_PER_ROLE` | `mercenaries.yaml` 的 `min_per_role` | 2 | `MercenaryTable` |
| `world_newcomer.py` `DEMOS_PER_CLASS` | `newcomer.yaml` 的 `range.demos_per_class` | 2 | `RangeContent` |
| `world_situations.py` `MAX_CARE_CLAIMS` | 改成 `len(CARE_ITEMS)` | 4 | 不另寫數字 |

### 2.3 改判 guard／const（理由寫進 `classes.yaml`）
| 位置 | 數字 | 判斷 | 理由 |
|---|---|---|---|
| `world_encounters.py` `MAX_GROUP_SIZE`、`MAX_THIRD_SIZE` | 4、3 | guard | 戰場地圖敵方／第三方起始區的格數（模板 4 格、就地切戰場 `field.min_enemy_cells` 4） |
| `world_narration.py` `STORY_SENTENCES_MAX`、`STORY_REFS_MAX` | 3、4 | guard | LLM 旁白輸出的格式護欄 |
| `world_quests.py` `_MAX_LEVEL` | 10 | guard | 任務等級欄位的護欄（等級上限在 `hero_growth.level_cap`） |
| `world_situations.py` `DC_SHIFT_LIMIT`、`CARE_LIMIT` | 2、2 | guard | 9.6.4 使用者定的天花板；實際值在 `check.dc_shift_max`／`care_max`（同 `RACE_BONUS_LIMIT`） |
| `world_situations.py` `_DANGER_LEVELS` | 1～3 | guard | 危險度刻度（和 `DangerDef.level`、模板 `danger` 的 `le=3` 同一件事） |
| `SolutionDef.threads`、`MethodDef.attributes` 的 `max_length=2` | 2 | guard | 線頭 0～2 條的格式上限（實際上限 `budget.threads_max`）；方法的常見屬性是分類格式 |
| `world_quests.py` `OFFER_SIZE` | 3 | const | 三選一的張數 |
| `fields.py` `DECOR_FIXED_SIZE` 曬衣繩 | 3 | const | 裝飾圖的固定尺寸，和美術素材綁在一起 |

### 2.4 沒有世界規則時的備用值
- `CalendarRules()`、`DEFAULT_WEEK_DAYS`、`FieldRules()` 原本是「沒有 `world/rules.yaml`」時的備用值。改成寫在呼叫的地方：
  - `world/calendar.py` 的 `NO_RULES_CALENDAR`（480、6）；
  - `world/season.py` 的 `NO_RULES_WEEK_DAYS`（7）；
  - `api/world_field_view.py` 的 `NO_RULES_WALK_MAX_STEPS`（30）；
  - `world/affinity.py` 的 `DEFAULT_AFFINITY_RULES` 補寫 −100、100、3。
- 新測試對照這幾個值和內容檔相同。新規則 `py-world-no-rules-fallbacks`（config todo，留給 HC-7）。
- `FieldView.walk_max_steps` 改成沒有預設值。OpenAPI 只少了 `default: 30`、`required` 多一格；`schema.d.ts` 只少 `@default 30` 註解。
- `world/story_gen.py` 的 `NamingRules()` 改讀 `load_world_style().naming`（同值 12、80、80）。

### 2.5 測試
- 新增：
  - `tests/content/test_rule_defaults_hc4d.py`：少寫一格就驗證失敗、值照內容檔、上限讀內容檔、誓約 `hp_permille` 只在用到時必填；
  - `tests/world/test_rule_defaults_hc4d.py`：備用值對照內容檔；
  - `tests/content/field_rules.py`：實地地圖測試取 `field_maps` 的小工具。
- 改（只換建構方式，或把上限的案例移到跨檔案檢查，斷言意思不變）：
  - `test_field.py`、`test_growth.py`、`test_weapon_mix.py`、`test_world_loot_api.py`、`test_world_economy.py`、`test_consistency.py`；
  - 實地地圖的 5 個測試檔（補 `rules=`）；
  - `test_races.py`、`test_world_map.py`、`test_world_mercenaries.py`、`test_oath.py`、`test_replay.py`、`test_newcomer_content.py`；
  - `test_world_events.py`、`test_world_situations.py`：屬性數的 schema 案例拿掉，改由跨檔案檢查擋（新測試）；
  - `test_situation_coverage.py`；
  - `test_rules_content.py`：`field:` 改必填；拿掉規則檔時要一起拿掉實地地圖。
- `tests/world/frozen_replay/world_rules.json`（凍結複本）：原本靠程式預設的 `field.gap_*` 四格、`wish`、`field_maps`（第 2 項再加 `day_parts`）照當時的預設值寫明。只新增鍵，凍結重播的雜湊照舊通過。
- `scripts/x10/fields.yaml`：新欄位列為 keep；`regions.yaml` 新開一組。

### 2.6 `WORLD_RULES_VERSION` 不升
- `world/save.py` 的說明：只有「`trpg.world` 裡會讓同樣的日誌重播出不同結果的改動」才加一；只改內容資料不用加（內容 digest 會變）。
- 這段只換數字放的地方，世界推進逐位元組相同（第 6 節），所以不升。內容檔多了欄位，內容 digest 本來就會變。

## 3. 第 2 項：時段表
- `world/rules.yaml` 新增 `day_parts`：`morning 6、noon 11、evening 18、night 21`（`DayPartHours`，必須遞增）。值照前端原本用的 11、18、21，早的起點 6＝遊戲日開頭。
- API：`WorldClockView` 多了 `day_parts`（`DayPartHoursView`），由 `rules_of(library).day_parts` 帶入。大世界畫面本來就要有世界規則。
- `hud.ts` 的 `dayPart` 改讀 `clock.day_parts`：白天 `h < noon` 是早，其餘午；夜晚 `evening ≤ h < night` 是晚，其餘夜。判斷式和原本一樣，只換掉數字。
  - 剩下的 `% 24` 是一天 24 小時，`ts-day-phase-hours` 改判 const。
- **世界時鐘不能共用這張表**：`trpg.world.clock.day_phase` 只看 `now`，拿不到內容庫，白天／夜晚由半天週期決定。所以加了對照測試：
  - 遊戲日開頭是 `morning` 點、白天；過半天是 `evening` 點、夜晚；
  - 午在白天裡、夜在夜晚裡。
- OpenAPI、`schema.d.ts` 重產，只多了 `DayPartHoursView` 與 `day_parts`。
- vitest：每個鐘點 00～23 再加 `24:00`、讀不懂的時刻、空字串，白天、夜晚各一次，字和圖示都和原本寫死的版本相同。另外驗證改了 `day_parts` 字會跟著變。

## 4. 第 3 項：其餘 content 尾巴
### 4.1 搬到 `core.yaml` 的 `skill_limits`（`Ruleset` 層檢查；`ruleset_hash` 會變）
| 原本 | 新格 | 值 | 檢查 |
|---|---|---|---|
| `SkillDef.rank` 的 `le=5` | `max_rank` | 5 | `skill_limit_problems` |
| `SelfStatusCost.duration` 的 `ge=2, le=3` | `min_self_status_duration`、`max_self_status_duration` | 2、3 | 同上；組合器的 `self_status_duration` 範圍改在 `composer_rule_problems` 對照 |
| `SkillCost.source` 的 `le=2` | `max_source_cost` | 2 | 同上 |
| `SkillDef.stance_upkeep` 的 `le=2` | `max_stance_upkeep` | 2 | 同上 |
| `ConditionSpec.any_of` 的 `max_length=2` | `max_any_of` | 2 | 同上（技能、修正規則、每個效果的條件） |
| `TriggerSpec` 的 `n in (2, 3)`、`SkillTriggerDef` 的 `[2, 3]` | `every_n_hits` | [2, 3] | `skill_limit_problems`；`Ruleset` 檢查 `budget_by_n_permille` 的鍵剛好是這些 |
| `skill.py` `_MIN_BESIDE_POWER` | `min_beside_power_permille` | 100 | `skill_limit_problems`（上限 1000 是 ‰ 護欄） |
| `stacks.py` `_MAX_BACKLASH` | `max_overload_backlash` | 2 | `Ruleset._check_overloads` |

- schema 只留下限與護欄（`rank ≥ 1`、`duration ≥ 1`、`source ≥ 1`、`any_of` 至少 1 個、`n` 必填、反噬至少 1 個）。照 HC-4b 的前例，超出上限的技能改由驗證器的 `cap.limits` 擋。
- `skill_scaling.py` 的 `dual_max_gap` 改必填（內容檔寫 40）。
- `enemy_moves.py` 的 `MOB, ELITE, BOSS = 2, 3, 3` 搬到 `world/enemies.yaml` 的 `min_moves`（`mob`、`elite`、`boss_phase`），新函式 `min_moves(library)`。工坊的提示句改從這裡組字。
- 改判 guard：
  - `maps.py` `MAX_HEIGHT`：地圖高度格式 0～3，引擎夾住、AI 拿它當哨兵；
  - `rule_changes.py` `_MAX_DURATION`：回合類護欄，照 HC-4a 的判斷。
- **沒搬**：`skills/reactions.py` 的 `TrapSpec.rounds` 預設 2，見待決 1。
- 測試：
  - 新增 `test_rule_defaults_hc4d.py` 的第 3 項案例：訊息有數字、改小就擋、係數表的鍵要對、反噬上限在 `Ruleset`；
  - 改 `test_legendary_schema.py`、`test_required_when_and_trigger_params.py`、`test_variance_schema.py`、`test_condition_any_of.py`、`test_passive_validation.py`、`test_self_status.py`：上限的案例改看 `skill_limit_problems` 或 `cap.limits`，下限照舊是 schema；
  - 改 `test_world_enemies.py`、`test_enemy_skill_count_149.py`；
  - 改 `scripts/x10/fields.yaml`。

## 5. 第 4 項：開進工坊
既有的表都不是大世界的檔，所以新開四張全體共用的表。每張對一個檔，工坊一張表只能對一種 schema。
- 改的程式：`TuningTarget.kind`、`TARGET_MODELS`、`TABLE_KINDS`，表名與表單頂端提示，前端 `client.ts` 的種類、`TuningScreen` 載入。

| 表（kind） | 分組 | 欄位 | 名稱 | 建議範圍 |
|---|---|---|---|---|
| 大世界規則 `world_rules`（`world/rules.yaml`） | 戰鬥回寫 | `battle.fatigue_hp_permille` | 疲憊時的開場 HP（‰） | 300～1000 |
| | 戰鬥回寫 | `battle.respawn_seconds` | 已清空到重生的秒數 | 600～7200 |
| | 成長 | `xp.base` | 一份經驗 | 50～200 |
| | 成長 | `hero_growth.insight_per_level` | 每升 1 級給的靈感點 | 0～5 |
| | 許願池 | `wish.cost_quest_coins` | 許願花的任務幣 | 1～10 |
| | 許願池 | `wish.refund_permille` | 都不拿時退回（‰） | 0～1000 |
| | 實地地圖 | `field.sight_range` | 敵人視野（格） | 2～8 |
| | 實地地圖 | `field.perceive_range` | 隱藏入口的感知距離（格） | 1～6 |
| 大世界經濟 `world_economy`（`world/economy.yaml`） | 戰鬥收入 | `battle_gold.battle` | 一般戰鬥的金幣 | 5～40 |
| | 戰鬥收入 | `battle_gold.elite` | 精英戰鬥的金幣 | 15～120 |
| | 買賣與背包 | `sell_permille` | 賣給商店的價格（‰） | 200～800 |
| | 買賣與背包 | `bag_slots` | 背包格數 | 10～60 |
| 交易與郵寄 `world_trade`（`world/trade.yaml`） | 交易門檻 | `trade.min_level` | 幾級起能交易 | 1～10 |
| | 郵寄 | `mail.mailbox_max` | 信箱上限 | 5～50 |
| | 郵寄 | `mail.return_days` | 幾天沒領就退回 | 1～7 |
| | 稽核報表 | `audit.big_value` | 稽核：大額的估值 | 100～2000 |
| 賽季 `world_season`（`world/season.yaml`） | 今日目標 | `daily_goals.newbie_days` | 新手期天數 | 0～5 |
| | 今日目標 | `daily_goals.coins` | 完成一條給的任務幣 | 0～5 |
| | 賽季頭目 | `season_boss.daily_attempts` | 賽季頭目每天挑戰次數 | 1～5 |
| | 賽季頭目 | `season_boss.score.per_round` | 頭目評分：每輪扣幾分 | 0～50 |
| | 影子循環賽 | `league.seeds` | 循環賽每組種子數 | 1～4 |

- 每格都有中文名稱、分組，說明都寫了調高、調低的效果。現值都在建議範圍內（測試檢查）。草稿驗證通過；超過 1000‰ 被擋。新測試 `tests/api/tuning/test_workshop_open_hc4d.py`。
- 「每天幾條今日目標」（`daily_goals.count`）原本想開，但欄位名 `count` 在工坊的禁開清單（技能結構），改開「新手期天數」。
- **沒開的**（數量多或意思相近）：
  - `world/rules.yaml`：遇敵機率、趕路、補給、紮營、感知 DC、天氣、`enemy_growth`、`hero_growth` 其餘格與升級門檻、`xp` 的來源份數、機遇、`wish` 其餘 4 格、`field` 其餘 9 格、`calendar`、`day_parts`、`field_maps`；
  - `world/economy.yaml`：`pouch_slots`、`stack_max`、`start_gold`、`battle_gold.level_step_permille`、任務幣、商店；
  - `world/trade.yaml`：`item_level_margin`、稅率、`mail` 其餘 3 格、`audit` 其餘 4 格；
  - `world/season.yaml`：`daily_goals.count`（禁開名稱）、世界事件、`league` 其餘格、`season_boss.score` 其餘 3 格、日程與懸賞；
  - 其餘大世界檔（`crafting`、`loot`、`mercenaries`、`oaths`、`newcomer`、`affinity`、`situation_rules`、`races.yaml` 的 `limits`、`regions.yaml`）與第 3 項的 `skill_limits` 新格（結構型上限）。

## 6. 不變比對（基準 `git archive e865b12bf src content config`）
腳本放在 scratch（沒進 repo）。改前、改後各用自己的 `src/` 與 `content/`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`，並確認載入的 `trpg` 路徑）。

| 比對 | 時機 | 結果 |
|---|---|---|
| 逐招預算 434 招（`BudgetReport` repr＋`validate_skill` 違規；`budget434.py`） | 第 1 項後、第 3 項後、最後 | `skills=434 same=434 different=0` |
| 78 場戰鬥（`compare78.py`，去掉 `ruleset_hash` 與內嵌規則包） | 第 1 項後、第 3 項後、最後 | `battles=78 events=26446 different=0` |
| 閃現出題（`flash_dump.py`：規則、計價、406 招完整技能、174 組出題 1322 筆） | 第 3 項後、最後 | 全部 `different=0`；閃現表 `model_dump` 沒有差異 |
| 世界推進（`world_dump.py`，見下） | 第 1 項後、第 3 項後、最後 | 566 筆，**檔案逐位元組相同** |
| roguelite 開局（`rogue_cmp.py`，見下） | 第 1 項後、第 3 項後、最後 | `runs=10 different=0` |

- **世界推進** `world_dump.py <root> <scripts> <out.json>`：
  - 用 `scripts/ob6_newbie_sim.py` 的走路器，6 個固定種子角色走真實流程：主城建角、選大類、接新手任務，走路打新手第 1、2 場固定戰（含巡邏遭遇），回鎮 `opening_confirm`，挑三選一；
  - 接著在雲嶺商店買賣、兩個角色互寄一封信（交易、稅），再休息 5 天，換日時跑賽季帳、今日目標、世界事件、主手大類比例；
  - 每個動作後記下角色存檔（`dumps_char`）、世界狀態 JSON 與事件，前後兩邊的輸出檔逐位元組比對。
  - 地圖、地區、場地的生成就是載入內容；這段的地點圖、實地地圖、規則載入後世界推進結果相同。
- **roguelite 開局** `rogue_cmp.py <base> <new> <out>`：
  - `trpg run new` 跑 10 組（6 個種子；指定武器、關鍵字、種族、回歸 build 各幾組）；
  - 比對存檔與輸出，`run_id` 是亂數，比對前換成 `<id>`。
- **預測會變的地方（逐鍵核對）**：
  - 78 場的內嵌規則包只多了 `core.skill_limits` 的 9 格與 `races.limits`，所以 `ruleset_hash` 會變（計畫允許）；
  - 閃現表的 `model_dump` 沒有差異；
  - OpenAPI 只有 2.4 與第 3 節說的變化（第 4 項沒有改到 API 的型別）；
  - parity 夾具、CLI 快照沒重產，slow 測試照原樣通過（第 7 節）。

## 7. 檢查（最後一個程式 commit `5580626bf`）
| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1772 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| `run_pytest.py -q tests -n 8`（全部非 slow，`7b67188d9` 上） | 1（17875 passed、8 skipped、6 failed，見下） |
| 上面 3 個內容錯誤修正後（`5580626bf`）重跑相關檔 | 0（42 passed） |
| 上面 3 個逾時的測試，`-o timeout=1800` 單獨重跑 | 0（5 passed） |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979 passed） |
| 前端 `pnpm -C client typecheck` | 0 |
| 前端 `pnpm -C client test`（vitest） | 0（393 檔、4822 個） |
| 前端 `pnpm -C client build` | 0 |

全部非 slow 那一輪（22 分鐘）的 6 個失敗：
- **3 個是這段的錯**，修正在 `5580626bf`，修完重跑相關檔都通過：
  - `test_no_design_numbers_txt1.py`：工坊新欄位的說明寫了決定編號（#98 等）；
  - `test_x10_fields.py`、`test_x10_rescale.py`：四張新表的建議範圍沒列進 `scripts/x10/fields.yaml`。
- **3 個是逾時**（300 秒，worker 被 pytest-timeout 結束，log 有 `node down`）：
  - `test_upgrade_topup.py::…cannot_carry[summon]`、`roguelite/test_test_mode.py::test_run_with_equipment_plays_to_the_end_and_replays_the_same`、`skillgen/test_player_text.py::test_player_check_texts_have_no_english_identifiers`。
  - 同樣 3 個、同樣負載（`-n 3`、`-o timeout=1800`）前後各跑一次：

    | 測試 | 基準 `e865b12bf` | 交件 |
    |---|---:|---:|
    | topup `[summon]` | 290.5 秒 | 298.8 秒 |
    | player_text 英文識別字 | 223.5 秒 | 230.1 秒 |
    | test_mode 帶裝備打完 | 220.3 秒 | 228.4 秒 |

  - 基準本來就貼著 300 秒；交件慢約 3%，在機器負載的誤差內（那段時間同一批測試比平常慢 3 倍）。
  - 開發中第 3 項那一輪，技能檢查曾經整棵走訪技能模型，比較慢。之後改成只看條件與觸發時機所在的欄位，434 招驗證 3 輪 0.29 秒（基準 0.26 秒）。
- 看門狗留證：`.claude/pm-logs/pytest/20261121-151156-32240/`（三個逾時的 `.stacks` 都是 `Timeout (0:04:55)`）。

## 8. config todo 與歸類（`classify.py --stats`）
| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `e865b12bf` | 554 | 38 | 8893 | 194 | 398 |
| 後端 交件 | **372** | 38 | 8931 | 193 | 432 |
| 前端 基準 | 26 | 0 | 5440 | 98 | 0 |
| 前端 交件 | **22** | 0 | 5441 | 98 | 0 |

- **`src/trpg/content/` 剩 1 筆**（基準 190）：`TrapSpec.rounds` 的預設 2，見待決 1。
- **後端少 182**：
  - content −189：搬進內容檔，或改判 guard／const（2.3、4.1 的表）；
  - 增加 +7：沒有世界規則時的備用值，`world/*` +6、`api/*` +1（2.4，`py-world-no-rules-fallbacks` 4 筆，`DEFAULT_AFFINITY_RULES` 補寫的 3 筆）。
- **前端少 4**：`hud.ts` 的 11、18、21 改讀 API；24 改判 const。
- **guard 多 34、const 多 38**：
  - 改判的結構常數；
  - 新 schema 的護欄（`RaceLimits`、`SkillLimits` 新格、`FieldMapRules`、`DayPartHours` 的 `le`／`ge`）；
  - docstring 與提示裡的數字。
- **刪掉的規則**（第 5 項，31 條，這段搬完變成 0 筆）：
  - 29 條 `py-content-*-config-number`（`world_rules`、`fields`、`world_*` 十六條、`races`、`roguelite`、`enemy_moves`、`maps`、`rule_changes`、`skill_scaling`、`skill_triggers`、`skills-skill`、`skills-specs`、`stacks`）；
  - `py-content-rule-bounds-skills`、`py-skill-stance-upkeep-points`；
  - 兩條 text 規則 `py-content-skill-triggers-text-text`、`py-content-world-events-text-text`（訊息改了）。
  - 基準就已經 0 筆的 11 條照舊不動（`py-scale-names` 等）。
- 新規則：
  - `py-content-guard-constants-hc4d`、`py-content-skill-limits-guard-hc4d`（guard）；
  - `py-content-structure-constants-hc4d`（const）；
  - `py-world-no-rules-fallbacks`（config todo）、`py-content-hc4d-text`（text todo）；
  - `py-content-rule-bounds-world` 改判 guard done。
- `寫死數值-清單.md` 用 `--md` 重產。

## 9. 待 PM 決定（都照最保守的做了）
1. **`TrapSpec.rounds` 的預設 2 沒搬**（content 剩的唯一 1 筆）。
   - 內容檔的陷阱技都有寫 `rounds`；但 `skillgen` 有兩個地方組陷阱時只給 `{"trigger": "enter"}`，靠這個預設補：`options.py` 的選項探測、`option_effect_rules.py` 的效果規則探測。
   - 工坊技能草稿的表單也以 2 當預設。
   - 改必填的話，要先讓這幾處從內容檔取值。那是 `skillgen` 的範圍，屬 HC-5，而且探測結果可能變。所以這段沒動，規則 `py-content-skills-reactions-config-number` 留 todo。建議 HC-5 一起做。
2. **沒有世界規則時的備用值**（2.4）：搬到 `world/*`、`api/*`，數字寫明、測試對照內容檔，留給 HC-7。HC-7 也可以改成沒有世界規則就報錯，只有測試的精簡內容庫會碰到。
3. **有實地地圖就要有 `world/rules.yaml`**：大小建議與傳送石數搬進規則檔，所以只有實地地圖、沒有規則檔的內容會載入失敗。原本可以載入；正式內容兩個都有。`test_rules_content.py` 拿掉規則檔時改成一起拿掉實地地圖。
4. **上限移到 `Ruleset` 層後，錯誤出現的地方不同**（同 HC-4b 待決 2）：
   - 技能的 `rank`、自身狀態回合、源力、維持費、`any_of`、`every_n_hits` 的 `n` 超出上限時，`SkillDef.model_validate` 不再擋，改由載入內容庫、`validate_skill` 的 `cap.limits`、工坊草稿檢查擋；
   - 層數超載的反噬數、`every_n_hits` 係數表的鍵在 `Ruleset` 驗證時擋；
   - 現有內容與 434 招、閃現出題結果都不變。
5. **改判 guard／const 的結構常數**（2.3 與 4.1 最後一段，共 15 個）：要改成 config 的話告訴我。其中 `DC_SHIFT_LIMIT`、`CARE_LIMIT` 是使用者定的天花板，實際值本來就在內容檔。
6. **誓約判定的 `hp_permille` 改選填**：只有「HP 低於某值前不能用」用到。其他種類的戰鬥設定不再輸出 `hp_permille: 500` 這一鍵。
   - 舊紀錄照讀，重播結果相同；
   - 戰鬥紀錄版號沒升；
   - 78 場戰鬥都沒有誓約，所以沒比到這一鍵。
7. **工坊新開四張表、21 格**（第 5 節；第 4 項的 commit 訊息誤寫 22），沒開的列在同一節。
   - 每張表對一個檔，畫面上是四個新的全體共用對象。
   - 沒截圖：只多了清單項目，表單沿用既有元件，靠 API 測試與 vitest 驗證。
8. **主手武器大類 `MainHandMix` 沒寫進內容檔**（2.1）：寫了等於打開功能。原本的預設值從沒生效。
9. **範圍外的小改動**：
   - `engine/oath_tracking.py` 加一行 `assert`（型別）；
   - `world/story_gen.py` 改讀世界觀檔的字數上限；
   - `api/tuning/service.py` 的提示句改從內容檔組字；
   - `composer_rules.py` 的自身狀態回合範圍改對照 `skill_limits`；
   - 前面列的測試因為程式預設值拿掉而改寫。
10. **三個慢測試貼著 300 秒的逾時**（第 7 節）：
    - 全部非 slow 那一輪逾時，基準在同樣負載下也要 220～290 秒；
    - 建議把這三個標 slow，或放寬它們的逾時。這段沒改測試設定。

## 10. 平衡疑慮（無）
沒有。只換數字放的地方；434 招預算、78 場戰鬥、閃現出題、世界推進、roguelite 開局逐項相同。

## 開發 PM 裁定（2026-11-21）

已用 `--no-ff` 合併進 main。合併後在 main 重跑 ruff、format、mypy、lint-imports、`classify.py --check`、`trpg content check`，結束碼都是 0。全量檢查由 push hook 跑。

待 PM 決定的 10 件：
1. **`TrapSpec.rounds`**：併進 HC-5，和 `skillgen` 組陷阱的地方一起改。
2. **沒有世界規則時的備用值**：留給 HC-7（`world/*`、`api/*`）。
3. **有實地地圖就一定要有 `world/rules.yaml`**：照做。現有內容都有這個檔。
4. **技能上限改在 Ruleset 層擋**：照做，和 HC-4b2 的 `modifier_bounds` 做法一致。
5. **15 個結構常數改判 guard／const**：照做。
6. **誓約 `hp_permille` 只在用到的種類必填**：照做。舊紀錄照讀，重播結果相同。
7. **工坊只開 21 格**：照做。沒開的欄位列在報告第 5 節，使用者要調再開。
8. **`MainHandMix` 不寫進內容檔**：照做。寫進去等於打開這個功能，這是規則類，要問了才開。
9. **範圍外的小改動**：接受，輸出不變。
10. **貼著 300 秒的三個慢測試**：照 QF-3 的規則，不准先改標 slow。先看 push hook 的全量（12 worker、沒有別的 agent）會不會逾時；會的話轉專案 PM 決定要標 slow 還是放寬逾時。
