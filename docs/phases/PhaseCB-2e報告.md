# Phase CB-2e 完成報告｜#149：頭目每階段 3 招的施放率補強

基準 commit `cf7cb00d`。依 `docs/phases/PhaseCB-2e計畫.md` 實作。**除了 PM 表內的三項，沒有調其他數值、門檻或 AI 權重；沒有改 `src/trpg/`；`WORLD_RULES_VERSION` 沒有加一。**

**結論**

- `concealed: 2` 的三組補量都在 3 個百分點內（最大 −0.9），**已採用**。
- 規格要處理的三筆裡兩筆達標：霧鎖真人第 2 階段 `mist_shift` 2% → 24%、碎晶之主第 1 階段第三招 9% → 25%；收霧斬 49%（原 `execute` 6%）。第三筆碎晶之主第 3、4 階段 `skill_blink` 0% 照規格不動。
- **新發現一筆 < 10%：灰燼之心第 1 階段 `lava_spout` 8%**（51/603；本段前後相同，調查時 40 場量到 12%）。不在本段範圍，沒有動，見待 PM 決定第 1 點。
- 碎晶之主分 build：沒有 < 40% 的；trapper 12/30 剛好 40%。
- 驗收全部通過。

## 交付

| 項目 | 內容 | commit |
|---|---|---|
| AI 增益表 `concealed: 2`、模擬腳本 | `content/ai_profiles.yaml`、`scripts/cb2e_sim.py` | `d9d830eb` |
| 收霧斬、震波 | 新增 `content/skills/skill_mist_rend.yaml`；`sect_mist_lock_master` 第 3 階段 `skill_execute` → `skill_mist_rend`；`rift_shard_lord` 第 1 階段 `skill_cluster_bolt` → `skill_thunder_clap`；登記處與測試 | `5fd6c2e5` |
| 腳本修正 | 報表的階段編號、頭目回合歸屬 | `673a5148` |
| 種子、固定名單、快照、報告 | 見「快照與改動的測試」 | 本 commit |

收霧斬的登記處：技能圖示 fixture（`client/src/render/fixtures/skill_icons.json`，只多這一筆）、`tests/skillgen/test_enemy_only.py` 名單、`tests/content/test_skill_scaling.py` 的內建招數 401 → 402、CLI 的 `skills_list`／`skills_show_all` 快照。`export_client_fixtures.py` 重跑後其餘 fixture 沒有差異。

技能預算（`trpg skills budget skill_mist_rend`）：total 6.90／可用 7.84＝**88.0%，合格**（和放血斬相同）。收霧斬除了 `enemy_only`、名稱、稀有度（`rare`，同其他敵人專用招）與敘事外，欄位和放血斬完全相同（資料測試逐欄比對）。

## 三項補量（只加 `concealed: 2` 的前後對照，同種子逐場配對）

腳本：`scripts/cb2e_sim.py conceal`／`compare`。主角是 build 底稿拉到地點等級、帶系統傭兵。

| 組 | 場數 | 前：勝率／輪數 | 後：勝率／輪數 | 變動 | 隱蔽招 前→後（次／帶招單位的回合） |
|---|---|---|---|---|---|
| 叛徒戰（青霧執事，霧隱；8 build × 8 種子） | 64 | 87.5%（56）／9.9 | 87.5%（56）／9.9 | **0.0**（勝負翻轉 10 場） | 34/577 → 184/581 |
| 夜間霧魅增援（雲嶺 6 個營地、夜晚、`wraiths_surge`；192 場中有加到霧魅的） | 152 | 99.3%（151）／4.5 | 99.3%（151）／4.4 | **0.0**（翻轉 0 場） | 77/447 → 84/435 |
| 帶 `skill_blink` 的我方 build（assassin、banisher、bomber、telekinesis、wallburn × 兩區 22 個一般地點 × 2 種子） | 220 | 79.1%（174）／5.3 | 78.2%（172）／5.3 | **−0.9**（翻轉 2 場） | 10/873 → 27/885 |

三組都沒超過 3 個百分點 → 採用。叛徒戰淨變動是 0，但有 10 場勝負互換（5 場變贏、5 場變輸），64 場的樣本下單次量測的波動不小。

### 調查量過的四組（前後；和調查的數字逐項相同）

| 組 | 場數 | 前 | 後 | 變動 |
|---|---|---|---|---|
| 懸賞霧中劍客 | 80 | 85.0%／4.7 | 85.0%／4.6 | 0.0（翻轉 8 場） |
| 營地霧隱精英 | 88 | 94.3%／4.7 | 92.0%／5.0 | −2.3 |
| 裂痕霧魅 | 80 | 100%／4.4 | 100%／4.4 | 0.0 |
| 角魔祭壇熔晶魅 | 80 | 98.8%／4.3 | 98.8%／4.7 | 0.0 |

三項內容都完成後重跑一次，七組數字與只加 `concealed: 2` 時完全相同（收霧斬、震波只影響頭目）。

## 三個頭目的每回合施放率（最終內容；80 場＝8 build × 10 種子）

施放率＝施放次數 ÷ 頭目在該階段的行動回合數；一回合放兩次算兩次（所以會超過 100%）。階段只認頭目本體的轉階段事件；頭目回合中途轉階段、且該回合還沒放招時，回合歸到新階段。「前」是基準 `cf7cb00d` 同種子。**粗體＝< 10%**，「可」＝10～20%。

### 霧鎖真人（前 91%／10.1 輪 → 後 95%／10.1 輪）

| 階段（進入場數／平均進入輪；頭目回合數） | 招 | 前 | 後 |
|---|---|---|---|
| 第 1 階段（80；499） | `cluster_bolt` | 38% | 40% |
| | `mist_shift` | 18%（可） | 53% |
| | `guardian_aegis` | 88% | 89% |
| 第 2 階段（78／6.2；161） | `mist_shift` | **2%** | 24% |
| | `mist_lock_peaks` | 36% | 38% |
| | `cluster_bolt` | 41% | 37% |
| 第 3 階段（76／8.3；106） | `charged_cleave` | 75% | 58% |
| | `first_strike` | 28% | 40% |
| | `execute` → `mist_rend` | **6%** | 49% |

分 build 勝場（後）：striker 9、fire 10、storm 10、ranged 10、tank 10、guardian 10、healer 10、trapper 7（各 10 場）。前：ranged 7、fire 9、trapper 7，其餘 10。

### 灰燼之心（74%／10.8 輪；本段前後逐項相同）

| 階段 | 招 | 施放率 |
|---|---|---|
| 第 1 階段（80；603） | `lava_spout` | **8%（51 次）** |
| | `fire_bolt` | 132% |
| | `ashen_oath` | 10%（可；63 次） |
| 第 2 階段（77／8.4；111） | `heart_inhale` | 15%（可） |
| | `heart_exhale` | 31% |
| | `fire_bolt` | 66% |
| 第 3 階段（62／8.5；103） | `heart_meltdown` | 17%（可） |
| | `heart_exhale` | 17%（可） |
| | `fire_bolt` | 33% |

分 build 勝場：striker 7、fire 6、storm 7、ranged 8、tank 7、guardian 10、healer 9、trapper 5。

### 碎晶之主（前 71%／12.6 輪 → 後 74%／12.6 輪）

| 階段 | 招 | 前 | 後（80 場） | 後（240 場） |
|---|---|---|---|---|
| 第 1 階段（80；472） | `cluster_bolt` → `thunder_clap` | **9%** | 25% | 25% |
| | `shard_erosion` | 86% | 72% | 70% |
| | `spark_chain` | 92% | 89% | 88% |
| 第 2 階段（77／5.8；286） | `rift_tremor` | 26% | 23% | 23% |
| | `shard_erosion` | 58% | 58% | 61% |
| | `cluster_bolt` | 16%（可） | 19%（可） | 15%（可） |
| 第 3 階段（69／8.8；188） | `rift_shatter` | 24% | 21% | 23% |
| | `skill_blink` | **0%** | **0%** | **0%**（503 回合 0 次） |
| | `rift_tremor` | 67% | 68% | 66% |
| 第 4 階段（15／15.2；34，樣本小） | `rift_shatter` | 14%（可） | 26% | 20% |
| | `skill_blink` | **0%** | **0%** | **0%** |
| | `rift_tremor` | 51% | 53% | 51% |

本體進第 2 階段：80 場中 77 場，平均在第 5.8 輪（`cb2a_sim.py` 的「100%／2.3 輪」把源晶柱的 `surge` 算了進去，`cb2e_sim.py` 只認本體）。

## 碎晶之主分 build（每個 build 30 場；整體 66%／12.8 輪）

| build | 勝場 | 勝率 | 平均輪數 | CB-2d |
|---|---|---|---|---|
| striker | 15/30 | 50% | 14.6 | 17 |
| fire | 15/30 | 50% | 14.9 | 15 |
| storm | 22/30 | 73% | 12.6 | 22 |
| ranged | 22/30 | 73% | 13.2 | 24 |
| tank | 20/30 | 67% | 12.1 | 22 |
| guardian | 27/30 | 90% | 10.2 | 25 |
| healer | 26/30 | 87% | 7.3 | 24 |
| trapper | 12/30 | 40% | 17.4 | 11 |

**< 40% 的：無。** trapper 12/30 剛好在門檻上（30 場的波動約 ±9 個百分點）。striker、ranged、tank 各少 2 場，guardian、healer 各多 2 場。

## 逐條驗收

| 條件 | 結果 | 證據 |
|---|---|---|
| `ruff check` | 通過 | `All checks passed!` |
| `ruff format --check` | 通過 | `2297 files already formatted` |
| `uv run mypy` | 通過 | `no issues found in 1438 source files` |
| `lint-imports` | 通過 | `Contracts: 14 kept, 0 broken.` |
| `tests/content`、`engine`、`sim`、`world`、`test_architecture.py`（`TRPG_FULL=1 -m "not llm"`、`-n 8`） | 通過 | 修正後整批重跑：`8603 passed, 4 xfailed` |
| `tests/api`、`tests/cli`（同上） | 通過 | 修正後整批重跑：`1092 passed, 1 skipped`；`test_dev_boss_rehearses_to_the_boss_charge` 這次沒有失敗 |
| `tests/skillgen`、`narrative`、`roguelite`（同上，扣掉下一列那一項） | 通過 | `5491 passed, 14 skipped`（在種子與快照修正之前跑的；之後只改了 `tests/engine` 三個檔與 CLI 快照，沒有再重跑這三個目錄） |
| `test_player_check_texts_have_no_english_identifiers`（單獨跑） | 通過 | `1 passed in 96s` |
| 前端 `typecheck` | 通過 | `tsc --noEmit` 結束碼 0 |
| vitest `src/render/skillIcon.test.ts`、`src/render/inkDollSnapshot.test.ts` | 通過 | `2 passed (2)`、`39 passed (39)` |
| 3 張地圖以上 `--log-json` ＋ `replay` | 通過 | open_plain 7（91 動作、383 事件）、oil_depot 13（102、454）、bridge_chasm 3（59、253）、swamp 21（54、240），都是「重播驗證通過」，數字與 CB-2d 相同 |

依指示沒有跑 `scripts/check.py`、`trpg sim completion／matrix`。

### 行為一致測試

| 規格 | 測試 |
|---|---|
| 霧鎖真人第 3 階段 3 招都能施放（跑引擎） | `tests/engine/test_enemy_skills_149.py::test_the_mist_lock_master_last_phase_can_cast_three_moves` |
| 收霧斬對滿血目標也能放、命中流血 2 回合 | 同檔 `test_mist_rend_hits_and_bleeds_without_a_health_gate` |
| AI 會選到收霧斬、第 2 階段會選到 `mist_shift` | `tests/world/test_enemy_ai_moves_149.py::test_the_ai_picks_each_boss_phase_move`（新增兩筆，取代 `execute` 那筆） |
| 碎晶之主第 1 階段 AI 會選到 `skill_thunder_clap` | `tests/world/test_shard_lord_first_phase.py`（正式裂界門，只算本體第 1 階段；改成參數化，`spark_chain` 與 `thunder_clap` 各一筆） |
| 三柱階段 3 招都能施放 | `test_first_boss_phase_can_cast_three_moves`（名單改成震波） |
| 第一季招數仍達 18.2、頭目每階段 3 招 | `tests/content/test_enemy_skill_count_149.py`（既有的 `test_every_first_season_enemy_has_enough_moves`；另加三項資料測試：收霧斬逐欄等於放血斬、三柱用震波且第 2 階段聚雷與第 3 階段 `skill_blink` 不動、`concealed` 是 2） |

`skill_thunder_clap` 在空地圖的 AI 測試（兩名英雄、40 個種子）量不到：錐形招要等人走進身前才放。所以沒有放進 `test_enemy_ai_moves_149.py`，也沒有加進 `RARELY_CHOSEN`，改用正式地圖的測試驗（12 個種子內有放）。

## 快照與改動的測試

第一次整批有 14 項失敗，分三類；斷言、確定性與重播比對都沒有放寬。

| 類別 | 測試 | 原因 | 處理 |
|---|---|---|---|
| 新增技能造成的清單變動 | CLI 快照 `skills_list`、`skills_show_all/06`～`15`（11 個鍵） | 多了收霧斬一招，清單往後推 | 只重產這 11 個鍵（`-k "skills_list or skills_show_all"`）。**其餘 CLI 快照（含全部戰鬥快照）沒有變** |
| 固定表格 | `tests/engine/test_support_ai.py`（`ally_status_values` 全表比對） | 表多了 `concealed: 2` | 期望值加上這一筆 |
| 固定種子（我方 build 帶 `skill_blink`，AI 軌跡變了） | `test_displace_ai.py::test_an_ai_battle_with_a_void_swap_replays`（build_banisher）、`test_hurl_object.py::test_an_ai_battle_hurls_objects_and_replays`（build_telekinesis） | 原種子那一場不再放虛空互換／丟油桶 | 種子 90 → 11、38 → 27（掃 0～119：互換有 11、32、113、119；丟物件有 27、68、105）。斷言與重播比對原樣 |

另外改的固定名單：`test_enemy_only.py`（加收霧斬）、`test_skill_scaling.py`（401 → 402）、`skill_icons.json`（重產，多一筆）。沒有新增 `# noqa`（`cb2e_sim.py` 的 `PLW0603` 是沿用 `cb2a_sim.py` 的程序池初始化寫法）。

## 模擬腳本

`scripts/cb2e_sim.py`（新檔，不依賴 `cb2a_sim.py`）：`bosses`（施放率）、`report`（把 JSON 重印成表）、`conceal`／`compare`（會隱蔽的單位同種子前後配對）。修掉的 `cb2a_sim.py` 問題：階段只認頭目本體，不把源晶柱 `surge` 算進去。`cb2a_sim.py` 本身沒動。

和調查筆記對過：基準的霧鎖真人第 1、2 階段回合數（527、151）與各招次數、四組隱蔽敵人的前後勝率都逐項相同。第 3 階段回合數基準是 87（筆記 85），差在轉階段那一回合的歸屬細節。

「營地霧隱精英」用的是調查時掃出來的 11 個（地點, 種子），寫死在腳本裡；陣容抽法變了要重掃。

## 沒驗證

- 沒有開瀏覽器看收霧斬、震波的動畫（調查判斷有現成片段，本段沒實機確認）。
- 只用底稿 build 與系統傭兵，沒測真人玩家配置。
- `test_dev_boss_rehearses_to_the_boss_charge` 只跑到一次（通過），沒有重複跑看不穩定的機率有沒有變。

## 待 PM 決定

1. **灰燼之心第 1 階段 `lava_spout` 8%（51/603），低於 10% 的處理線**。本段前後相同；調查時 40 場量到 12% 所以列為可接受，80 場掉到線下。`ashen_oath` 10%（63/603）也貼著線。要不要照同樣流程提候選。
2. **碎晶之主第 3、4 階段 `skill_blink` 仍是 0%**（240 場 593 回合 0 次）：已知缺口，照規格不動。
3. **霧鎖真人勝率 91% → 95%**（目標 70%），trapper 以外 7 個 build 幾乎全勝；照裁定留在平衡待辦。
4. 碎晶之主 80 場整體 74%（19.4 的目標 60～70%）；240 場是 66%。trapper 12/30 剛好 40%，沒有餘裕。
5. 霧鎖真人第 2 階段 `mist_shift` 24%，餘裕小（和調查相同）。
6. 叛徒戰前後淨變動 0，但 64 場裡 10 場勝負互換；若要更有把握可以加大樣本。
7. `docs/design/18-雲嶺內容.md` 等設計文件裡頭目的招式清單若有寫到 `execute`／聚雷，本段沒有改（設計文件由玩法 PM 寫）。
