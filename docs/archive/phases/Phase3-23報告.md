# Phase 3-23 報告｜刻印（`inscribe`，玩法 #26）

> 規格：`docs/phases/Phase3計畫.md` 第 23 節；設計：`docs/design/06-技能.md` 6.25、`docs/玩法決定紀錄.md` #26。在獨立 worktree（分支 `worktree-agent-a503c0e6db386db3a`，從 main 的 `bda13a8` 分出）實作，未 push、未合併。與 3-21b 平行：未動基本動作（`engine/actions.py`）、`ui/ActionPanel.tsx`、`ui/TurnControls.tsx`；`styles.css` 只在檔尾新增；API 型別只新增欄位。

## 1. 做了什麼

**引擎**（新模組 `engine/runes.py`〔寫入〕、`engine/rune_queries.py`〔唯讀查詢，避免循環匯入〕、`engine/ai/rune.py`）
- **狀態**：`BattleState.runes`（`RuneState`：編號、施放者、陣營、位置、元素或標籤、剩餘輪數；不可變，更新時替換）與 `next_rune_id`；`clone`、序列化、`test_state_clone` 同步。同一施放者同一格再刻一次＝取代（舊的以 `replaced` 消失）；同一施放者超過 `rune_limit_per_owner`（6）時最舊（編號最小）的以 `limit` 消失；每次環境回合 −1，歸零以 `expired` 消失（`run_environment` 在暫時障礙到期之後呼叫 `tick_runes`）；施放者倒下時符文保留到時效結束（保守）。全程不用亂數，排序依編號。
- **原語 `inscribe`**：在技能形狀的格子（可站立）留下施放者專屬符文；參數 `element`（元素）或 `tag`（標籤）恰好一個、可選 `duration`（1–5；省略取 `core.rune_default_rounds` ＝ 3）。本身無效果，敵我都看得到（`BattleView.runes`／`RuneView`）。效果 `InscribeEffect`、事件 `rune_inscribed`／`rune_removed`（原因 `expired`／`limit`／`detonated`／`replaced`）。
- **讀取**：
  1. 條件 `on_own_rune`（`ConditionSpec` 新欄位 `element`；可帶 `element` 或 `tag` 篩選）：對**格子**判斷、只算施放者自己的符文。技能條件、效果條件與修正型被動（`modifiers`）共用同一條 `condition_met`，所以「修正型被動以打到自己的符文格為條件」不需另造觸發（示範：符文共鳴）。
  2. 消耗型原語 `detonate_runes`：影響範圍內施放者自己的符文（依編號）每格移除並發 `rune_removed(detonated)`，對該格上符合 `affects`（預設 `enemies`，可 `all`；施放者自己不受傷）的單位**自動命中**一次傷害（骰值＋縮放屬性×法術倍率；元素取 `element`、省略取符文元素，標籤符文為物理）。可搭配形狀 cross／square3／ring／allies_in_radius。
- **骨架 `rune`**（新增 `content/skeletons/rune.yaml`，`SKELETON_IDS` 15 種）：核心 `inscribe`／`detonate_runes`，附帶 `damage`（≤40%）、`apply_status`；`min_rarity: rare`。
- **隨機組合器**：`rune` 骨架為「明確指定才用」的主動骨架，由獨立亂數串流以 `skill_composer.yaml` 的 `rune.skeleton_permille: 40`（4%）改組（同陷阱、蓄力終結的作法），**不改變其他種子的抽選**；組合器只產生 `inscribe`（元素＝主題元素、`duration` 為強度旋鈕），`detonate_runes` 只給手寫技能。400 個種子中出現 6 次（1.5%）。
- **示範技能**（6 招，`content/skills/`）與 build：
  - 刻印 3 招：`skill_thunder_sigil`（雷紋刻印：十字 5 格、2 輪）、`skill_ember_trail`（火痕：直線 3 格、3 輪）、`skill_hunt_sigil`（獵印：指定格、**標籤**符文 `hunt`、5 輪）。
  - 讀取 3 招：`skill_rune_thunderbolt`（咒雷：目標在自己的雷紋上追加 2d8，元素篩選）、`skill_rune_resonance`（符文共鳴：修正型被動，打到自己符文上的目標傷害 +15%）、`skill_rune_burst`（符文爆裂：**消耗**，半徑 3 內自己的符文每格引爆，3d6）。
  - 新 build `build_runeweaver`（刻印流；`content/sim/builds.yaml`，共 23 個）裝備以上 6 招＋連鎖閃電，讓覆蓋率測試（每個手寫技能都被裝備）成立。
- **技能圖示**：`narrative.skill_icon.icon_of` 本來就吃任意原語／條件代碼，新原語自動推導（`test_icon_of_derives_rune_parts`）；前端 `skillParts.ts` 補 `inscribe`、`detonate_runes`、`on_own_rune` 部件與名稱，`skillGlyphs.ts` 補骨架 `rune` 的名稱與圖示；`client/src/render/fixtures/skill_icons.json` 重產。
- **敘事**：事件文字（「X 在 (4, 2) 刻下雷紋（剩 2 輪；只有 X 讀得到）」「X 的雷紋（(2, 3)）被引爆了」…）、技能說明文字（`narrative/skills.py`）、條件文字（`condition_text`「目標站在自己的雷紋上」）。符文名稱在 `shared/types.rune_name`（元素 → 力／火／冰／雷／毒／風／土／聖／影＋「紋」；標籤符文為「<標籤>紋」）。

**AI**（`engine/ai/rune.py`；`content/ai_profiles.yaml` 的 `rune:`，標平衡階段初值）：先刻再引。
- 只在行動者有**讀取技能**（有 `on_own_rune` 條件的技能或效果，或 `detonate_runes`）時才刻；沒有讀取技能時刻印技能不納入候選。
- 選位置（便宜估計）：影響範圍內每格依離最近敵人的距離計分（腳下 3、相鄰 2、距離 2 為 1，更遠 0；已有自己的符文不算）。
- 評分：預覽事件中新刻的符文 ＝ `inscribe_points`（6）× `damage` 權重 × 距離比例（腳下 1000‰／相鄰 `adjacent_permille` 600／距離 2 `near_permille` 300）。
- 讀取加分：讀取技能打到站在自己符文上的敵人，每個目標 `read_points`（6）× `damage` 權重（傷害本身已由預覽計算，這是額外鼓勵）；引爆看被引爆的符文格上站著的敵人。

**網頁**（`client/src/battle/runes.ts`、`render/BattleRenderer.ts`）：符文畫在格子上（菱形外框＝施放者陣營色、菱形內紋與四端刻痕＝元素色〔標籤符文米色〕，同一格多個符文各占一個象限，剩 1 輪畫淡），走 `rows.place`／`tileLift`，跟著格子抬高；格子資訊卡新增「符文：刻印流英雄的雷紋，剩 2 輪」（`TileSection` 新 kind `rune`）；事件與紀錄文字來自後端敘事。`openapi.json`、`schema.d.ts` 重產（只新增 `RuneView` 與 `BattleView.runes`）。

## 2. 驗收

| 條件 | 證據 |
|---|---|
| 1. 放置 | `tests/engine/test_runes.py`：`test_inscribe_places_a_rune_with_default_duration_and_both_teams_see_it`、`test_inscribe_covers_every_tile_of_the_shape_and_takes_explicit_duration`、`test_inscribe_does_nothing_on_unstandable_tiles` |
| 1. 持續與移除 | `test_runes_count_down_each_environment_round_and_expire`、`test_runes_outlive_a_fallen_caster_until_they_expire`、`test_same_cell_is_refreshed_and_other_owners_runes_coexist` |
| 1. 上限擠掉最舊 | `test_per_owner_limit_evicts_the_oldest_rune` |
| 1. 條件讀取（元素篩選、別人的符文不算）、修正型被動 | `test_on_own_rune_condition_checks_the_targets_tile`、`test_on_own_rune_element_and_tag_filters`、`test_someone_elses_rune_does_not_count`、`test_conditional_effect_in_a_skill_only_fires_on_own_rune`、`test_modifier_passive_boosts_damage_on_own_rune` |
| 1. 消耗引爆 | `test_detonate_removes_own_runes_in_range_and_hits_enemies_standing_on_them`、`test_detonate_with_no_runes_is_harmless`、`test_detonate_element_override_and_all_affects_spare_the_caster` |
| 1. 預算、示範技能過預算 | `test_inscribe_budget_scales_with_duration`、`test_detonate_budget_uses_dice_average_and_shape_multiplier`、`test_demo_skills_pass_budget_and_validation`；`uv run trpg skills budget --all`：158 個通過、違規 0 |
| 1. 組合器種子 0–49 仍合法 | `tests/skillgen/test_rune_composer.py`：`test_seeds_0_to_49_stay_valid`、`test_composer_produces_inscribe_with_low_weight`、`test_explicit_rune_skeleton_composes_valid_skills`；既有 `test_workshop_options`（120 個種子與全部手寫技能符合工坊選項）通過 |
| 1. `icon_of` 推導 | `test_icon_of_derives_rune_parts`；`tests/narrative/test_skill_icon.py::test_client_fixture_is_current`（fixture 已重產） |
| 1. AI 先刻再引的情境 | `tests/engine/test_rune_ai.py`：`test_only_units_with_a_reader_skill_want_to_inscribe`、`test_the_ai_inscribes_before_it_reads`、`test_rune_gains_are_larger_closer_to_the_enemy`、`test_reading_skill_scores_higher_when_the_target_stands_on_an_own_rune`、`test_detonation_is_attractive_when_enemies_stand_on_runes`、`test_ai_decisions_with_runes_are_deterministic` |
| 1. 同種子重播一致 | `test_same_inputs_replay_identically_and_state_roundtrips`、`test_telegraph_does_not_mutate_the_state` |
| 2. `--log-json` ＋ `replay` 一致，紀錄有刻印與讀取 | `tests/cli/test_rune_cli.py::test_runeweaver_battle_has_inscribe_and_read_events_and_replays`（training_range 種子 0、`--ally-build build_runeweaver`：`rune_inscribed`、`rune_removed`，並有引爆或咒雷，重播驗證通過、同種子紀錄相同）。手動：`uv run trpg battle --map open_plain --seed 7 --ally-build build_runeweaver --log-json <檔>` → `trpg battle replay <檔>` 輸出「重播驗證通過：143 個動作、419 個事件，最終狀態一致」；另掃 5 張地圖 × 種子 0–7，40 場中有 34 場有讀取 |
| 3. vitest | `client/src/battle/runes.test.ts`（繪製資料：舊回應無 `runes`、陣營色／元素色／標籤色、同格象限、剩 1 輪淡化、跟著 `tileLift`；資訊卡文字）；vitest 534 項通過 |
| 3. 截圖 | `docs/phases/img/3-23-runes-on-map.png`（地圖上的雷紋）、`3-23-tile-card.png`（資訊卡「符文：刻印流英雄的雷紋，剩 2 輪」）、`3-23-detonate.png`（符文爆裂：紀錄「的雷紋（(2, 3)）被引爆了」、盜賊倒下） |
| 4. `check.py` 全過、`pnpm build` 成功 | 見第 7 節 |

## 3. `LOG_FORMAT`
`trpg-battle-log/36` → `/37`（`runner.py` 註解列出：原語 `inscribe`／`detonate_runes`、條件 `on_own_rune`（`ConditionSpec.element`）、骨架 `rune`、戰鬥狀態 `runes`／`next_rune_id`、新事件 `rune_inscribed`／`rune_removed`、新效果 `inscribe`／`detonate_rune`、核心規則 `rune_*`、預算規則 `inscribe_duration_permille`／`detonate_runes_permille`）。舊 `/36` 紀錄與戰鬥中存檔不能由新版讀取（慣例同前）。**3-21b 若同時遞增，合併衝突請 PM 處理**（兩邊各加一段 `/37`、`/38` 說明並更新 4 個 CLI 測試的格式字串與 `docs/開發PM交接.md`）。

## 4. 新原語／條件的預算點數（初值，未經模擬）
- **`inscribe`**：`budget_basis: inscribe`，`base_points: 5` × `inscribe_duration_permille[n]`（`[600, 800, 1000, 1200, 1400]`，n ＝ `duration` 1–5，省略取預設 3 輪 ＝ 1000‰）。形狀倍率照一般「影響格」效果計（十字 1.8、直線 3 格 1.4、指定格 1.0）。
  - 理由：規格說「比照標記類原語」，但本專案的預算驗證有**過弱下限 0.7**，只有 1–3 點的刻印技能永遠過不了（AP 1 的階級 1 技能可用預算約 7–8）；所以取 5 點，讓單獨一個刻印效果（AP 1、冷卻 2、法力 4）落在 89%–92%。刻印本身沒有傷害，這個點數等於「先付訂金、之後由讀取技能領回」。
- **`detonate_runes`**：`budget_basis: detonate_runes`，骰子平均 × `detonate_runes_permille`（700‰；需要先刻印、敵人要站在符文上的折扣），形狀倍率另外照一般效果計（`allies_in_radius` 半徑 3 ＝ 2.2）。符文爆裂 3d6 ＝ 16.17 點（75.5%）。
- **條件 `on_own_rune`**：`harshness: harsh`（×0.6）、`min_rarity: rare`。理由：需要先用另一招刻印才成立。咒雷 14.40（91.0%）、符文共鳴 3.78（90.0%）。
- 示範技能預算（`trpg skills budget --all`）：雷紋刻印 7.20／91.8%、火痕 7.00／89.3%、獵印 7.00／89.3%、符文爆裂 16.17／75.5%、咒雷 14.40／91.0%、符文共鳴 3.78／90.0%。

## 5. 換種子／快照
- 既有釘種子的測試軌跡**沒有改變**（AI 與組合器的改動只在行動者有刻印技能／種子抽中 `rune` 骨架時才生效），無需換種子。
- `tests/cli/snapshots/cli_output_hashes.json`：以 `UPDATE_CLI_SNAPSHOTS=1` 重產，只有 `skills_list`、`skills_show_all` 兩筆（技能數 152 → 158）改變。
- 計數測試：`test_budget_cli`（158 個技能）、`test_sim_builds`（23 個 build）、`test_con_hp`（`build:build_runeweaver` 40）、`test_skill_rules_content`（15 種骨架）、`test_validate`（`rune` 範例）、4 個 CLI 測試的格式字串 `/37`。

## 6. 新增的複雜度 noqa
無。（`condition_text` 的 `PLR0911`、`_placement_estimate` 的 `PLR0911`、`_Cast.build` 的 `PLR0912` 都以拆出函式或併入 `_SIMPLE` 表解決。）

## 7. `check.py`／`pnpm build`
- `uv run python scripts/check.py`（只在最後跑一次）：ruff check、ruff format --check、mypy（440 檔）、lint-imports、pytest（全量，平行）、client install／typecheck／test（vitest 534 項）**全部通過**。
- `corepack pnpm -C client build`：成功（僅既有的 chunk 大小警告）。
- 大型模擬（`sim completion`／`matrix`）依規定未跑。

## 8. 待 PM 決定
1. **取 `inscribe` 5 點**（第 4 節）：若 PM 想要「便宜的標記」，需同時放寬預算驗證的過弱下限或給 `rune` 骨架專屬下限。
2. **`duration` 的語意**：沿用暫時障礙的「環境回合」倒數——施放當輪結束就 −1，所以持續 2 輪的符文實際上只活到下一輪的環境回合前（施放者只有下一輪的一個回合能讀）。預設 3 輪（規格初值）；示範技能的雷紋刻印用 2 輪（十字 5 格，預算限制）。
3. **標籤符文**：`tag` 已支援（獵印），但技能工坊的選項只能挑 `element`（`element` 在原語參數中標必填，填了 `tag` 時改為不必填）；工坊 UI 暫時做不出標籤符文，手寫技能可以。
4. **刻在有單位的格子**：允許（符文不阻擋、不要求空格）；不可站立的格子（牆、石柱、原木）沒有效果（`effect_fizzled: not_standable`），十字形狀因此可能少刻幾格。
5. **`detonate_runes` 的傷害**：自動命中、不暴擊、不吃格擋與修正型被動的傷害‰，`cause: effect`；施放者站在自己的符文上時符文被引爆但他不受傷。若 PM 希望引爆傷害吃格擋／暴擊，需要改成走一般攻擊傷害路徑。
6. **別人的符文**：敵我都看得到，但只有刻下它的人讀得到；敵方 AI 沒有任何讀取技能時不會刻，也不會閃避符文格。
7. **同格同施放者再刻＝取代**（而不是刷新剩餘輪數）：元素或標籤可能改變，所以用 `rune_removed(replaced)` ＋ `rune_inscribed`；占用上限時只算 1 格。
8. **AI 數值**（`rune:`）未經模擬。實測：刻印流 AI 會在敵人附近刻符文，也會在敵人踩上時用咒雷與符文爆裂（5 張地圖 × 種子 0–7 的 40 場中有 34 場有讀取），但符文只活 2–3 輪、敵人多半不會停在原地，勝率尚未驗證；`matrix` 全量模擬依規定未跑，請平衡階段決定。
9. **符文外觀**：目前是統一的菱形紋＋元素色（非元素專屬圖案）；同一格多個符文縮成四象限。若美術 PM 要元素專屬紋樣，可在 `drawRunes` 內依 `element` 換繪法（資料已在 `RuneDraw`）。
10. **前端沒有為「符文被引爆」另做特效**：引爆沿用技能的施放特效，符文消失靠狀態更新；紀錄文字有「被引爆了」。
