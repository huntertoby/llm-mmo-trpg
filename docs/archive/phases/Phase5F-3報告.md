# Phase 5F-3 完成報告：賽季 Boss 規則（封印、只准傭兵、每日次數、首殺、評分榜、源晶柱）＋區域 Boss 掉落與重複挑戰

規格：`docs/phases/Phase5計畫.md` 第 37 節。先寫成第 36 節，合併 main 時 5F-4 也用了 36，所以本段順延成 37，「之後各段規格」順延成 38。依據：第 1 節 5F-3 列；09 9.7、9.6.8（#86、#87）、9.6.9（#98、#100）、9.6.10（#101）；19 19.6.2、19.7、19.9；20 20.2、20.6；`Phase5F-2報告.md` 待 PM 決定 6。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格 37 節（含決策影響盤點 37.2） | `docs/phases/Phase5計畫.md` |
| Boss 階段新觸發 `tag_down`（同陣營帶標籤的單位倒下 N 名）、`round_at`（第 N 輪起），都有 `condition_zh`；`check_phases` 只對 `hp_below` 檢查遞減；護陣 `taken_permille` 下限 100 → 0、`range` 上限 12 → 24；預設陣容不夠 `tag_down` 名額時載入失敗 | `src/trpg/content/battle.py`、`src/trpg/content/library.py` |
| 引擎：`_reached` 依觸發種類判斷；護陣 ×0 時傷害是 0（不套最低 1 點）；事件 `boss_phase_changed` 加 `trigger`、`condition_zh`，`permille` 改成選填 | `src/trpg/engine/boss_phases.py`、`effects/handlers.py`、`events.py`、`view.py`（`next_condition_zh`） |
| 戰鬥紀錄與單位卡依觸發種類寫條件 | `src/trpg/narrative/events.py`、`unit_traits.py` |
| `LOG_FORMAT` `/109` → `/110` | `runner.py`、`docs/phases/戰鬥紀錄格式變更.md`、測試字面值（cli 6 檔、engine 5 檔） |
| 碎晶之主、三根源晶柱、晶傀儡 | `content/units/rift_*.yaml` |
| 新技能 6 招（只給敵人）：霧晶／雷晶／火晶脈衝、碎界脈動、晶蝕、界碎 | `content/skills/skill_rift_*.yaml`、`skill_shard_erosion.yaml` |
| 新狀態：源晶共鳴（護陣 ×0）、晶能湧動、晶能狂湧、界崩 | `content/statuses.yaml` |
| Boss 地圖「裂界門」（13×13 圓形浮台、外圈虛空） | `content/maps/rift_gate.yaml` |
| 賽季資料：`seal_keys`、`season_boss`、世界事件 #3「封印共鳴」（目標種類 `seal_key`）；`WorldEventEffect.seal_keys` | `content/world/season.yaml`、`src/trpg/content/world_season.py` |
| 世界規則：封印鑰匙、解鎖時間與狀態、挑戰、通關結果 | `src/trpg/world/season_boss.py`（新） |
| 換日與動作後：集滿時間、鑰匙、`seal_key` 進度 | `src/trpg/world/season_board.py` |
| 狀態欄位：`EncounterResult.season_boss`；`WorldState.seal_keys／seal_full_at／boss_attempts／boss_clears`；`CharacterState.seal_key_sources／boss_drop_days` | `src/trpg/world/state.py` |
| 動作 `season_boss` 與事件 `seal_key_gained`、`season_boss_challenged／cleared／failed` | `src/trpg/world/season_events.py`、`actions.py`；`step.py`（併入 5F-4 的 `ACCOUNT_HANDLERS`，次數算帳號） |
| 開戰與回寫：陣容、地圖不換皮、敵人 10 級、不帶劇情夥伴與下一場修正；勝負都不給經驗、金錢、掉落，HP 等照開戰前 | `src/trpg/world/battle.py` |
| 區域 Boss 保底掉落：`loot.yaml` `bosses`（霧鎖真人 → 雲頂霧晶＋史詩） | `content/world/loot.yaml`、`src/trpg/content/world_loot.py`、`src/trpg/world/loot.py` |
| 伺服器：通關評分榜 `season_boss_board.json`（紀念類）、首殺戰鬥紀錄 `season_boss/<季>-first-kill.json`；`FirstKill.account_id／battle_log`；首殺公告模板；今日公告的賽季 Boss 一行；季末分類表 | `src/trpg/server/season_boss_board.py`（新）、`first_kills.py`、`announce.py`、`season_policy.py`、`notes.py`、`content/world/announcements.yaml` |
| API：公告板 `season_boss` 區塊、事件句子、首殺與評分榜記錄 | `src/trpg/api/season_boss_view.py`（新）、`season_schemas.py`、`season_view.py`、`routes/world.py`、`world.py`、`world_presenter.py`、`world_schemas.py` |
| 前端：公告板的「賽季 Boss」區塊（狀態、解鎖時間、鑰匙進度條、帳號今天剩幾次、首殺、評分榜、挑戰按鈕） | `client/src/world/BoardPanel.tsx`、`board.ts`、`boardBoss.test.ts`（新）、`screens/WorldScreen.tsx`、`api/types.ts` |
| 產生檔 | `client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/battle/fixtures/glossary.json`、`tests/skillgen/fixtures/refactor_3wr2.json`、`tests/cli/snapshots/cli_output_hashes.json` |
| 模擬腳本 | `scripts/season_boss_sim.py`（新） |
| 測試 | `tests/engine/test_boss_triggers_5f3.py`、`tests/world/test_season_boss.py`、`tests/world/test_boss_loot.py`、`tests/api/test_season_boss_api.py`（都是新檔）；`tests/content/test_world_season.py`、`tests/api/test_announce.py`、`test_world_board.py`、`tests/content/test_con_hp.py`、`test_coverage.py`、`test_skill_scaling.py`、`tests/skillgen/test_budget.py` |

## 做法摘要

- **源晶柱解謎是通用資料**：三根柱子各帶護陣「源晶共鳴」（×0，範圍 24 涵蓋整張浮台），任一根還在，本體就不受骰值傷害。本體第 2 階段用 `tag_down rift_pillar 3` 觸發。柱子自己也有階段：倒 1 根、倒 2 根時，留下的柱子換上「晶能湧動」（×1.25）、「晶能狂湧」（×1.5）。之後要寫同類解謎，只要寫 content。
- **本體加 `immovable`**：模擬發現本體會被推下虛空，或走出柱子的護陣範圍，解謎就被繞過了。所以本體加了 `immovable`，護陣範圍也放到整張地圖。
- **封印與解鎖**：解鎖時間用 `seal_full_at` 推算，算法照 37.6，不另存排程。沒集滿時第 10 天 06:00 強制解鎖，第 9 天 06:00 起公告，開放到第 14 天 06:00（第 13 天結束）。集滿時間點由日誌序號決定，重播結果一致。
- **每帳號每天 3 次**：次數存在世界狀態，用日誌的 `actor` 計算，所以可以重播。按下挑戰就扣 1 次，撤退不退次數。種子從角色的 `battle` 串流取，由賽季種子衍生，客戶端無法指定。
- **首殺**：世界狀態 `boss_clears` 的第一筆就是首殺（`season_boss_cleared.first`）。伺服器會用開戰前的角色加這場的步驟重算一次，存成 `BattleLog`。
- **評分榜**：每個角色每季只留最好的一次，排序依分數高、輪數少、序號小。「出發地點」照 5C-3f 的規則，看的人還沒發現時顯示提示語；目前從城鎮出發，所以實際不會遇到隱藏地點。
- **區域 Boss**：可以不限次數重複挑戰，Boss 地點不寫已清空（照現狀）。每個角色每個刷新日第一次打倒有保底：Boss 那份材料換成雲頂霧晶、那件裝備換成史詩，亂數照常消耗。第一次打倒霧鎖真人另外給 1 把封印鑰匙。

## 小模擬（`uv run python scripts/season_boss_sim.py --seeds 5`，8 個 build × 5 種子＝40 場）

走大世界的真實路徑：`prepare_battle` → 效用 AI 雙方 → `max_rounds` 30。主角是 build 底稿，用敵我同一套規則成長到 10 級。傭兵依主角類型配：輸出與控制主角帶鐵壁＋回春，守護主角帶赤焰＋回春，輔助主角帶赤焰＋穿雲。敵方 10 級。

現值（本體 HP 380、柱子 60）：

| 條件 | 場數 | 勝率 | 平均輪數 | 勝場輪數 | 敗場本體剩餘 HP | 柱子全倒 | 到核心過載 |
|---|---|---|---|---|---|---|---|
| build_striker | 5 | 20% | 18.0 | 12.0 | 87% | 80% | 20% |
| build_fire | 5 | 60% | 15.2 | 14.0 | 14% | 100% | 100% |
| build_storm | 5 | 100% | 14.2 | 14.2 | — | 100% | 100% |
| build_ranged | 5 | 100% | 13.8 | 13.8 | — | 100% | 100% |
| build_tank | 5 | 80% | 13.2 | 11.0 | 100% | 80% | 80% |
| build_guardian | 5 | 100% | 10.0 | 10.0 | — | 100% | 100% |
| build_healer | 5 | 80% | 7.4 | 7.5 | 27% | 100% | 100% |
| build_trapper | 5 | 40% | 18.2 | 17.0 | 90% | 60% | 40% |
| **全部** | 40 | **72%** | **13.8** | 12.1 | 70% | 90% | 80% |

候選值掃描（`--sweep`，全部 40 場）：

| 本體／柱子 HP（1 級基準） | 勝率 | 平均輪數 |
|---|---|---|
| 140／45 | 92% | 8.7 |
| 260／50 | 82% | 11.8 |
| 380／50 | 75% | 13.4 |
| 380／60（現值） | 72% | 13.8 |
| 450／50 | 77% | 14.3 |
| 450／60 | 67% | 14.5 |

- 只帶鐵壁＋回春時，守護和輔助主角輸出太低，3 根柱子打不完，勝率 0%。表格是改帶輸出傭兵後的結果。
- 各 build 差距還很大：striker 20%、trapper 40%，其他 build 80～100%。每個 build 只跑 5 場，誤差大。19.7 要求「差太多調 Boss，不調 build」，請 PM 定目標範圍。
- 調整前發現兩個漏洞，已修：最低傷害 1 點會穿過 ×0 護陣，本體被慢慢磨掉；本體會走出護陣範圍。

## 檢查結果

合併 main（`2fbfff32`，含 5F-1b 與 5F-4）後跑的檢查如下。衝突在 `step.py`（賽季 Boss 改用 5F-4 的 `ACCOUNT_HANDLERS`，次數算帳號）、season.yaml、規格節號與產生檔；都已解決，產生檔重產。

- `ruff check .`、`ruff format --check .`、`mypy`（strict，1199 檔）、`lint-imports`（13 kept）：全部通過。
- `pytest -n 8 tests/engine tests/content tests/world tests/api tests/server tests/bot tests/test_architecture.py`：7391 通過、1 失敗。失敗的是 `test_source.py` 的精英名單少了碎晶之主，已補，該檔 21 通過。
- slow 測試：`tests/skillgen/test_budget.py`、`test_refactor_3wr2.py`、`tests/sim/test_push_check.py`（正式地圖 13 → 14）、CLI 快照：全部通過（971 項）。夾具在合併後又重產一次，因為 main 的霧影分身招式還沒在夾具裡。
- vitest 1282 通過（140 檔），`pnpm build` 通過。新狀態補了圖示（`statusIcon.ts`，狀態 111 個）。按鈕不用原生 `title`（照 6.5.1）。
- 重播：swamp 種子 7 通過（88 動作、313 事件）。首殺重播通過：`trpg battle replay <世界>/season_boss/s1-first-kill.json`，218 動作、1058 事件、rift_gate。
- OpenAPI、`schema.d.ts`、`glossary.json` 已重產。
- CLI 快照：`skills_list`、`skills_show_all/07～15` 共 10 個重產，原因是多了 6 招技能（合併後還加上 main 的霧影分身）。`refactor_3wr2` 夾具重產，新增 6 招的項目；既有 20 招的閃現出題也變了，原因見待 PM 決定 2。
- 瀏覽器（8190 埠，用自己的存檔資料夾）：公告板的賽季 Boss 區塊顯示正確（已解鎖、開放到、鑰匙、今天剩 3／3 次、首殺、評分榜第 1 名）。按「挑戰」之後出現遭遇，事件列顯示「踏進裂界門挑戰「碎晶之主」（今天第 1 次，還剩 2 次）」。同時發現首殺被寫成城鎮的地點足跡，已修正。
- 沒跑全量、matrix、completion。新增的 `# noqa` 只有 `step.py` 的 `_season_boss`（`PLR0917`）。它要和 `_AccountHandler` 同簽名，和 5F-4 的 `_league` 一樣。

## 代決（規格 37.10；都照最保守的做法實作）

| # | 事項 | 實作 |
|---|---|---|
| 5F3-1 | 在哪裡打 | 獨立地圖「裂界門」，從任何城鎮挑戰 |
| 5F3-2 | 次數什麼時候扣 | 按下挑戰就扣；撤退不退 |
| 5F3-3 | 種子 | 角色的 `battle` 串流（賽季種子衍生） |
| 5F3-4 | 失敗 | 只扣次數；HP、法力、耐力照開戰前；下一場修正不套用也不消耗 |
| 5F3-5 | 打贏 | 不給經驗、金錢、掉落；稱號只記在評分榜 |
| 5F3-6 | 劇情夥伴 | 不擋挑戰，但不出場；有影子就擋 |
| 5F3-7 | 封印共鳴 | 全服累積（開始時帶入之前的鑰匙），門檻 12，照上線人數調整 |
| 5F3-8 | 鑰匙來源 | 霧鎖真人第一次打倒、每張懸賞第一次搶下 |
| 5F3-9 | 集滿後何時解鎖 | 最早第 8 天，且至少 24 小時後；第 10 天強制 |
| 5F3-10 | 開放到 | 第 13 天結束 |
| 5F3-11 | 分數 | max(0, 1000 − 20 × 輪數) ＋ 100 × 存活人數 ＋ 200（沒人倒下） |
| 5F3-12 | 評分榜 | 每角色每季最好的一次 |
| 5F3-13 | 原文做不到的地方 | 晶蝕改成既有的「流血」（新狀態會進技能生成器的狀態池）、不能疊層；晶傀儡只召喚一次；「回合結束全場傷害」改成本體周圍環形的技能；「每回合換邊」改成瞬步；雷柱的直線與界碎的 2 排直線都改成十字臂長 2 |
| 5F3-14 | 界崩 | 第 3 階段之後才會觸發 |
| 5F3-15 | 區域 Boss | 不限次數；保底掉落每角色每刷新日一次 |
| 5F3-16 | 版號 | `/110` |
| — | 規格外補的 | 本體 `immovable`；護陣範圍上限 24；×0 時不套最低傷害；賽季 Boss 首殺不寫進城鎮的地點足跡 |

## 待 PM 決定

1. **數值**：本體 380、柱子 60 時，40 場勝率 72%、平均 13.8 輪；各 build 從 20% 到 100% 不等。目標勝率與輪數請 PM 定。另一個候選是 450／60（67%、14.5 輪）。
2. **敵人專用技能進了玩家技能池**：6 招新技能照既有做法，和九轉回天、霧鎖千山一樣是內建技能，所以也進了關鍵字池與通用池。`refactor_3wr2` 夾具中，有 20 招既有技能的閃現出題變了。如果要「只給敵人」，需要另做排除機制，這也會影響 5F-2 的霧鎖千山（5F-2b 決定大十字只給敵人用）。
3. **原文近似**（5F3-13）：晶蝕疊層、擊殺晶傀儡移除晶蝕、每 3 回合召喚、回合結束全場傷害、真的直線形狀的蓄力，都需要新的引擎欄位。
4. **解鎖時間是否綁 6 點**：現在是「集滿後 24 小時」，可能落在任何時刻；要不要改成對齊下一次 6 點刷新。
5. **封印共鳴的門檻**：12 把是初值，照 5F-1b 的規則依上線人數調整，最少保留 1/4（3 把）。現有的鑰匙來源只有霧鎖真人與 3 張懸賞，每個角色最多 4 把。
6. **稱號**：目前只寫在評分榜；要不要另做帳號稱號（紀念類）。
7. **首殺之後的對打賽**（9.7「有人首殺 → 娛樂賽」）留給 5F-5。
8. **CLI 快照**：`skills_list`、`skills_show_all/07～15` 共 10 個重產，原因是新增 6 招技能。
