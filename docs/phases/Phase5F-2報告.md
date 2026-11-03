# Phase 5F-2 完成報告：區域 Boss 的階段機制

規格：`docs/phases/Phase5計畫.md` 第 34 節（這一段先補的規格；合併 main 時 main 已加了第 33 節 5D-4，本段順延成 34，「之後各段規格」順延成 35）。依據：第 1 節 5F-2 列；09 9.6.8（#86）、18 18.2.3、20 20.6；19 19.2.3／19.7 只確認資料格式擋不住。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格 34 節（含決策影響盤點 34.2） | `docs/phases/Phase5計畫.md` |
| 階段資料格式 `UnitTemplate.phases`（`BossPhase`、`HpBelowTrigger`／`PhaseTrigger` 聯集、`PhaseTile`、`PhaseSpawn`、`check_phases`）；`WardSpec.range` 上限 5 → 12 | `src/trpg/content/battle.py` |
| 載入檢查：階段技能（存在、符合武器、欄位上限）、行為模式、狀態、天氣、召喚範本、地形；Boss 地圖預設陣容的 `tiles`／`spawns.at` 在地圖內 | `src/trpg/content/library.py` |
| 引擎：`check_boss_phases`（純函式、不取亂數）；結算收尾與換手後各檢查一次 | `src/trpg/engine/boss_phases.py`（新）、`src/trpg/engine/turns.py` |
| 狀態欄位 `UnitState.phases`／`phase_index`、`BattleState.phase_weathers`；`BattleSetup.phase_weathers`；`with_phase_assets`、`phase_spawn_ids` | `src/trpg/engine/state.py`、`lifecycle.py`、`setup.py`、`battle.py` |
| 事件 `boss_phase_changed`、`weather_changed`；戰鬥紀錄文字 | `src/trpg/engine/events.py`、`src/trpg/narrative/events.py` |
| `LOG_FORMAT` `/108` → `/109` | `src/trpg/engine/runner.py`、`docs/phases/戰鬥紀錄格式變更.md`、測試字面值（cli 6 檔、engine 5 檔） |
| 單位卡：`UnitView.boss_phase`（`BossPhaseView`）；特性欄「階段：劍陣 → HP 60%「鎖霧」 → 30%「歸一」」 | `src/trpg/engine/view.py`、`src/trpg/narrative/unit_traits.py` |
| 大世界：`grow_enemy` 一併升階改名階段技能；`prepare_battle` 把階段召喚（照敵人等級成長）與天氣放進設定 | `src/trpg/world/battle.py` |
| 霧鎖真人、雲頂觀陣眼石靈 | `content/units/sect_mist_lock_master.yaml`、`content/units/sect_summit_array_stone.yaml` |
| 新技能 霧遁、霧鎖千山（蓄力強招）；新狀態 鎖霧大陣、歸一 | `content/skills/skill_mist_shift.yaml`、`content/skills/skill_mist_lock_peaks.yaml`、`content/statuses.yaml` |
| Boss 地圖「雲頂觀」 | `content/maps/cloud_summit.yaml` |
| 雲頂觀地點接 Boss 地圖與 Boss 陣容 `mist_lock_court` | `content/world/maps/cloud_ridge.yaml`、`content/world/encounters/cloud_ridge.yaml`（只改雲頂觀兩處） |
| 前端：階段轉換提示（既有 `NoticeBanner`，15 秒）、單位卡「階段」列、兩個新狀態圖示 | `client/src/battle/bossPhase.ts`（新）、`client/src/screens/BattleScreen.tsx`、`client/src/ui/UnitInfo.tsx`、`client/src/render/statusIcon.ts` |
| 產生檔 | `client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/battle/fixtures/glossary.json`、`client/src/render/fixtures/skill_icons.json` |
| 小模擬腳本 | `scripts/boss_phase_sim.py`（新） |
| 測試 | `tests/engine/test_boss_phases.py`（新，26 項）、`tests/world/test_boss_battle.py`（新）、`client/src/battle/bossPhase.test.ts`（新）；受影響：`tests/content/test_con_hp.py`、`test_coverage.py`、`test_regions.py`、`test_skill_scaling.py`、`test_world_map.py`、`tests/world/test_enemy_smoke.py`、`client/src/render/statusIcon.test.ts` |

## 做法摘要

- **資料化**：Boss 範本寫 `phases`；第 1 項是開場階段（只有名字），之後每項 `trigger: {kind: hp_below, permille}`（嚴格遞減），可選：`skills`（整組換）、`ai_profile`、`remove_statuses`、`add_statuses`（同開場狀態格式、不擲抵抗）、`weather`、`tiles`（同 `terrain_change` 的格子）、`spawns`（`template`、`count`、`at` 省略＝Boss 附近）、`text_zh`。新內容不改引擎。
- **觸發**：每次結算收尾（被動觸發與誓約之後、勝負判定之前）與換手之後檢查；HP ≤ 門檻就進入，一次跌破多個依序進入；`phase_index` 只增不減，每個階段整場一次；倒下那一擊不觸發；預覽不檢查。
- **重用**：召喚走 `SpawnUnitEffect`（最近安全格、排在先攻最後）、改格子走 `ChangeTileEffect`、加狀態走 `ApplyStatusEffect`；蓄力強招與預告沿用 6.23 #5 延遲段（`telegraph.charges`、前端「蓄」標記），換技能組時正在蓄力的照常釋放；第 1 階段的 −50% 用既有護陣 `ward`。天氣第一次能在戰鬥中改：天氣定義隨設定內嵌（`phase_weathers`），重播不讀資料檔；設定沒放（沒經過 `with_phase_assets`）時天氣不改、召喚落空（同既有的未知範本），不會讓戰鬥出錯。
- **霧鎖真人**（HP 90，1 級基準；體質後 102）：① 劍陣：`archer`、聚雷＋霧遁，陣眼石靈（12 格內真人受到的傷害 ×500‰，石靈倒下即解除），劍陣弟子 ×2 守高台入口；② 鎖霧（≤ 60%）：濃霧（既有 `fog`）、霧遁＋霧鎖千山＋聚雷、`cunning`、隱蔽 2 回合、召喚霧行者 ×2；③ 歸一（≤ 30%）：晴朗、移除隱蔽、蓄力斬＋先發制人、`brute`、「歸一」每回合開始回 1d6。
- **格式擋不住的後續**：灰燼之心的殼（開場狀態＋`remove_statuses`）、吸氣吐氣與熔心爆（技能組）、餘燼蜥（`spawns`）都能直接寫；火地擴散、冷卻破甲、碎晶之主三柱（新 `trigger` 種類）要新欄位，`trigger` 已是依 `kind` 區分的聯集，加新種類不動舊資料。
- **青霧執事九轉回天預告**：5A-M1 已完成，本段只補測試（預告 3×3 範圍）。

## 小模擬（`uv run python scripts/boss_phase_sim.py --seeds 40`）

雲頂觀 Boss 地圖、地圖預設的原型三人（戰士、弓手、法師），雙方效用 AI，`max_rounds` 30；「沒有階段」＝同範本拿掉 `phases`（整場停在第 1 階段）。6 級＝雲頂觀建議等級（敵我照大世界成長，召喚的霧行者同級）。

| 條件 | 場數 | 勝率 | 平均輪數 | 敗場真人剩餘 HP | 到第 2 階段 | 到第 3 階段 |
|---|---|---|---|---|---|---|
| 1 級・沒有階段 | 40 | 90% | 6.9 | 68% | 0% | 0% |
| 1 級・有階段 | 40 | 42% | 6.8 | 42% | 92% | 67% |
| 6 級・沒有階段 | 40 | 97% | 5.1 | 16% | 0% | 0% |
| 6 級・有階段 | 40 | 77% | 5.5 | 30% | 100% | 90% |

- 階段讓勝率明顯下降（6 級 97% → 77%）、輪數略增；6 級九成能打到第 3 階段，三個階段都看得到。
- 1 級勝率 42% 偏難，但雲頂觀建議等級是 6，1 級只是原型三人的參考。
- 輪數只有 5～7 輪，比 9.6.8 想像的「打很久、看階段」短；要拉長可以加真人 HP 或石靈 HP（建議值見待 PM 決定 5）。數值沒有反覆手調。

## 檢查結果

合併 main（`4485ec9e`，5D-4 等）之後：

- `ruff check .`、`ruff format --check .`（1744 檔）、`mypy`（strict，1160 檔）、`lint-imports`（11 kept）：通過。
- `pytest -n 8 tests/engine tests/content tests/world tests/api tests/narrative`：7479 通過（第一次跑出 1 個失敗 `test_source.py` 的精英名單少了霧鎖真人，已補，該檔 21 通過）。
- vitest：1269 通過（136 檔）；`pnpm build`：通過。
- swamp 種子 7 重播：通過（88 動作、313 事件）；另跑雲頂觀種子 1：三個階段都出現，重播通過（123 動作、507 事件）。
- CLI 快照：`skills_list`、`skills_show_all/06～15` 共 11 個因新增 2 招技能（霧遁、霧鎖千山）改變，已用 `UPDATE_CLI_SNAPSHOTS=1` 重產（25 通過）；其他 CLI 輸出不變。
- 產生檔已重產：OpenAPI／`schema.d.ts`、`glossary.json`、`skill_icons.json`。
- 沒跑全量 matrix／completion；沒有新增 `# noqa`（`load_library` 的複雜度用拆出 `_check_unit_phases` 解決）。

## 代決（開發 PM 規格 34.9；照最保守預設實作）

| # | 事項 | 實作 |
|---|---|---|
| 5F2-1 | 檢查時機 | 結算收尾＋換手之後；預覽不檢查 |
| 5F2-2 | 一次跌破多個門檻 | 依序觸發每一個（召喚照樣出現，天氣以最後一個為準） |
| 5F2-3 | 「降到」 | HP ≤ 門檻；倒下那一擊不觸發 |
| 5F2-4 | 換技能組時的蓄力 | 照常釋放；冷卻只留新技能組裡的 |
| 5F2-5 | 第 1 階段 −50% | 護陣 `ward`（12 格），石靈打碎才解除，進第 2 階段不自動解除 |
| 5F2-6 | 每回合隱蔽換位 | 技能「霧遁」（傳送 3 格＋隱蔽 2 回合，冷卻 1、法力 3）交給 AI |
| 5F2-7 | 每回合結束回血 | 用回合開始回血 1d6（引擎只有回合開始） |
| 5F2-8 | 近戰化 | 全程單手劍；第 3 階段換近戰技能組與 `brute`，護盾來自蓄力斬 |
| 5F2-9 | 霧鎖千山 | 十字（中心＋四方向 1 格），2d8＋定身 1 回合，冷卻 3、法力 10 |
| 5F2-10 | 香爐 | 先用油桶 |
| 5F2-11 | 召喚物 | 和 Boss 同陣營；大世界照敵人等級成長；不加 `boss_escort` |
| 5F2-12 | 數值 | 真人 HP 90、石靈 HP 30、歸一 1d6 |
| 5F2-13 | 雲頂觀遭遇 | 只有 Boss 陣容；`summit_patrol` 保留不用 |
| 5F2-14 | 版號 | `/109` |

## 待 PM 決定

1. **回合結束回血**（5F2-7）：18.2.3 寫「每回合結束治療自己少量」，現在是回合開始。要真的回合結束需要狀態新欄位（`on_turn_end_heal`）。
2. **霧鎖千山的範圍**：現在是既有「十字」（5 格，以真人為中心）。「千山」聽起來更大；要大十字（每方向 2～3 格）需要新的形狀參數。
3. **一次跌破兩個門檻**（5F2-2）：現在第 2 階段的霧行者照樣召喚、天氣直接變晴。若希望「跳過」中間階段（只套最後一個），改 `boss_phases._enter` 的迴圈即可。
4. **香爐**（5F2-10）與 **換武器**（5F2-8）：都需要新物件／武器狀態與美術。
5. **數值**：6 級勝率 77%、平均 5.5 輪。若要 Boss 戰更長、更像「三個階段各打一陣」，建議試真人 HP 90 → 120、石靈 HP 30 → 40（只改 content，再跑同一個腳本比較）；本段未調。
6. **雲頂觀的一般遇敵**：現在 Boss 地點的戰鬥一律是 Boss 戰（`summit_patrol` 留著沒用）。Boss 的入場限制、重複挑戰、Boss 掉落（20 號「區域 Boss 必掉 1 件史詩」）都不在本段，應在 5F-3 或之後排。
7. 陣眼石靈的單位卡：特性欄把護陣的同門標籤原樣顯示成「mist_lock_core」（既有特性欄格式），要中文標籤名需另加標籤名表。
