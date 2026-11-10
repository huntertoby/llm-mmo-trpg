# Phase HID-1b 報告：隱蔽單位的圖層與預告洩漏

> 規格：`docs/phases/PhaseHID-1b計畫.md`。基準 main `439b03e7`，worktree，未 push、未 merge。

## 1. 完成表

| 交付項目 | 做法 | 位置 |
|---|---|---|
| 1 圖層 | `RowLayer.marks` 移到上層霧之後，HP 條、「？」、狀態列、召喚物回合數、倒下徽章、炸彈／蓄力／灌注徽章都掛進 `marks`（人物留在 `units`，霧之下）。攻擊紅框改畫在每排新的 `frames`（物件、高度徽章之上，單位之下），不縮框；被南邊高台、屋頂擋住的格子改畫 `attackTop`（`marks` 之上、`hudTop` 之下，框才看得到）。`draw()` 重建排後重畫紅框 | `client/src/render/rowLayers.ts`、`battle/highlightLayer.ts`、`battle/rendererBase.ts`、`BattleRenderer.ts` |
| 2 預告不洩漏 | `telegraph_out` 用 HID-1 的 `hidden_unit_ids`（同一份判定），新增 `mask_telegraph_changes`：未揭露單位的 `unit_downed` 不列出，其他項目 `before`、`after`、`amount` 清成 `None`；`change_text(..., hidden)` 換成不含數值與狀態名的文字。引擎 `telegraph` 不動 | `src/trpg/api/hidden_info.py`、`api/telegraph.py`、`narrative/telegraph.py` |
| 3 四角飾件舊 FAIL | 查出是 `ResizeObserver` 的時機問題（見第 3 節），改成框一出現就先標記一次 | `client/src/ui/smallFrames.ts` |
| 4 補拍 | 5 張＋1 張總覽，`docs/art/shots/hid1b/` | 見第 5 節 |

`runCase` 新增 `seed` 選項（`client/src/dev/layoutSmoke.ts`），用來跑多種子。

## 2. 洩漏查證結果

`TelegraphChange` 的來源只有 `_changes()`（`src/trpg/engine/environment.py`）。逐類查：

| 種類 | 帶單位 ID | `before` | `after` | `amount` | `text`（改前） | 查證結果 |
|---|---|---|---|---|---|---|
| `unit_damaged` | 目標 | 無 | 無 | `e.amount - e.absorbed`（扣護盾後）| 「X (x, y) 將受到 N 點傷害」 | **洩漏**：`amount` 與 `text` 的 N 已扣護盾、含易傷等狀態倍率，可反推護盾與狀態。改成 `None`，文字「將受到傷害」 |
| `unit_downed` | 目標 | 無 | 無 | 無 | 「X 將倒下」 | **洩漏** HP（剩餘 HP ≤ 這次傷害）。整項不列（同 HID-1 `mask_outcomes` 的做法）；傷害那一項仍在 |
| `bomb_exploded` | 攜帶者 | 無 | 無 | 半徑 | 「X 身上的定時炸彈將在 … 爆炸（半徑 N 格，…）」 | **洩漏**狀態名與狀態內容（半徑）。`amount` 改 `None`，文字「(x, y) 將發生爆炸（格子）」；`pos`、`tiles` 留著（危險預警） |
| 狀態到期 | — | — | — | — | — | **沒有洩漏**：規格懷疑的 `status_removed` 不在 `_changes()`，環境回合也不產生狀態到期（狀態在單位回合結算）；`test_status_expiry_is_not_part_of_the_changes` 以實際引擎鎖住 |
| `surface`、`terrain`、`object_*`、`zone_*`、`unit_spawned` | 無或新單位 | 表面、地形值 | 表面、地形、模板、區域技能 | 區域編號 | 公開資訊 | 不涉及單位身上的資料，不改 |

規格的「`before`、`after`、`amount`、`text`」以外的項目，見第 6 節第 1 點（`bombs`、`charges` 未遮）。

## 3. 四角飾件舊 FAIL 的原因

**不是種子造成的，是 `ResizeObserver` 回呼沒有來**：戰鬥主角卡（`data-rt-compact`）要靠 `installSmallFrames` 標成小框（飾件 70%、左右內距 16px），內距才讓得開飾件；標記只在 `ResizeObserver` 回呼裡做。回呼沒來時卡片留在大飾件＋內距 10px，第一個小圖示就在左下飾件裡。

- **重現（已驗證）**：只把 `.rt-frame` 的 `ResizeObserver` 擋掉跑 `runCase`（無頭 Chrome），得到**一字不差的 FAIL**：`hero-card … 左下 × svg.skill-chip-glyph`（第一個圖示 x=11，正常是 17）；沒擋掉時跑過的 28 場（多種子、3 種尺寸，含報告裡常 FAIL 的 `SMOKE_SEED`）飾件都 PASS，修前修後都一樣，FAIL 一次都沒出現。
- **為什麼時有時無（推論，沒有直接重現）**：`ResizeObserver` 綁在算繪幀上，內建瀏覽器窗在背景、隱藏時不跑算繪幀，回呼就不來。歷來報告裡相同的 main 也在 PASS／FAIL 之間跳，和這個一致，和種子無關。
- 修法：`watch` 把框納入觀察時先呼叫一次 `updateSmallFrame`，不等第一次回呼；測試 `client/src/ui/smallFramesInstall.test.ts`（回呼永遠不來時仍標好）。

## 4. 驗收

| 項目 | 結果 |
|---|---|
| `ruff check`、`ruff format --check`、`uv run mypy`（1416 檔）、`lint-imports`（14 kept） | 全過 |
| pytest：`tests/api/test_telegraph_hidden.py`（新，36 項）、`test_hidden_info`、`test_reactions_telegraph`、`test_revive_bomb_api`、`test_zone_api`、`test_delayed_api`、`tests/narrative/test_zone_text`、`tests/engine` 預告相關 8 檔（`test_time_bomb`、`test_environment_turn`、`test_boss_phases`、`test_delayed_followup`、`test_directed_charge`、`test_phase1c_decisions`、`test_polish_3c6a`、`test_runes`、`test_temporary_obstacles`、`test_zones`）、`test_architecture` | 303 passed；`test_openapi_snapshot` 2 passed（schema 沒變） |
| `trpg battle --map swamp --seed 7 --log-json` ＋ `battle replay` | 通過：88 個動作、313 個事件，最終狀態一致 |
| `WORLD_RULES_VERSION`、`LOG_FORMAT` | 沒動；`git diff 439b03e7 -- src/trpg/engine content` 為空 |
| 前端 `tsc --noEmit`、`npx vite build` | 結束碼 0 |
| vitest：`src/render src/ui src/battle src/dev`（200 檔、2402 項）＋ `smallFramesInstall`（3 項） | 全過 |
| 行為一致表格測試 | `test_telegraph_hidden.py`：4 種對照 × 5 種變化（爆炸傷害、護盾、倒下、狀態到期、炸彈）；隱蔽未揭露的 × 5；`test_visible_units_keep_the_exact_telegraph` 比對改前完整內容；`test_serialized_hidden_telegraph_has_no_hp_shield_or_status_ids` 掃序列化後的回應 |
| 既有 `HID-1` 測試 | `test_hidden_info.py` 原樣通過 |
| 排版煙霧 1600×900、1040×624、800×600（`SMOKE_SEED`） | 三個都 13 PASS、0 FAIL（無頭 Chrome，`--mute-audio`、主音量 0） |
| 四角飾件固定 5 個種子（20261024、1、3、4、6）× 1600×900、1040×624、800×600 | 15 場全部 13 PASS、0 FAIL。**這 15 場是把 `.rt-frame` 的 `ResizeObserver` 擋掉跑的**（修前會 FAIL 的條件）；飾件那一列 PASS |

改到的既有測試（預期的版面變化）：`client/src/ui/occludedHud.test.ts`、`southArrow.test.ts`（`addChild` 字串）、`statusBadges.test.ts`（`marks` 在霧之後）。新測試 `client/src/ui/hid1bLayers.test.ts`（9 項）。

## 5. 截圖

`docs/art/shots/hid1b/`（jpg 80）。**同一開局沒有天然隱蔽敵人**：沿用 HID-1 的做法，在瀏覽器攔下戰鬥回應，把 `unit_0004`、`unit_0005` 改成 `hidden_info: true`、`hp`／`shield` 為 null、狀態空，`unit_0004` 站的格子改成 `surface: darkness`；用無頭 Chrome（`--mute-audio`、主音量 0）拍。一般敵人是 `unit_0007`。

| 檔案 | 內容 |
|---|---|
| `hid1b_move_plain_zoom.jpg` | 1 ─ 1600 選「移動」，一般敵人，HP 條在紅框之上（放大） |
| `hid1b_move_hidden_zoom.jpg` | 2 ─ 1600 選「移動」，隱蔽敵人，「？」在紅框之上（放大） |
| `hid1b_dark_hidden_zoom.jpg` | 3 ─ 黑暗格的隱蔽敵人，「？」在霧之上、人物在霧之下（放大） |
| `hid1b_corner_800.jpg` | 4 ─ 四角飾件 800 寬 |
| `hid1b_corner_1600.jpg` | 5 ─ 四角飾件 1600 寬 |
| `hid1b_move_overview_1600.jpg` | 額外：1600 選「移動」整張（確認紅框在單位之下、HUD 在紅框之上） |

## 6. 待 PM 決定

1. **`bombs`、`charges`（`BombOut`、`ChargeOut`）沒有遮**：規格只寫 `TelegraphChangeOut`，玩法 PM 也確認「環境與強招預告照畫」。但 `BombOut.text`、`remaining` 仍寫「X 身上的定時炸彈還要 N 次環境回合爆炸」、`ChargeOut` 的文字寫施放的技能名與倒數；**這兩個實際上是狀態資訊**。要不要連這兩項的文字一起遮請玩法 PM 決定。（狀態 ID `time_bomb` 本身沒有出現在回應裡，掃描測試涵蓋。）
2. **預告項目「存在」本身**：隱蔽單位站在油桶旁等情況，仍會列「將受到傷害」（危險預警，規格要留位置）。但有免疫等狀態時不產生事件，理論上「有沒有這一項」透露一點點；不處理。
3. **`unit_downed` 整項不列**，文字「將倒下」沒有留佔位（同 `mask_outcomes`）。
4. **朝向三角形不算霧上的 HUD**：規格列「HP 條、狀態列、徽章」；朝向三角形有一種畫在身體之下，移到霧上會蓋住身體。留在原層（被高台擋住時照舊上 `hudTop`）。
5. **天氣等全域環境層（`ambient.root`）與頂層 `marks` 高亮（預覽、移動格、環境預告圖示）的順序沒動**，HUD 仍在 `ambient.root` 與 `marks` 之下；規格只動霧與攻擊紅框。若天氣或高亮蓋到 HUD 要另排。
6. **紅框被高台、屋頂擋住的格子改畫上層**：規格沒寫到；若畫在單位之下，框就看不到了，採此做法（HUD 還是在框之上）。
7. **排版煙霧的種子**：種子 2、5 的「格子資訊卡」一項在部分尺寸是 FAIL（「沒有出現格子資訊卡」），該項是滑過格子找卡的步驟沒碰到有卡的格子，和飾件、本段改的繪製無關（本段沒動格子資訊卡），沒查 main 上是否相同；驗收用的固定 5 個種子不含這兩個。
8. **開發／除錯檢視**：`trpg.cli.battle` 的 `render_telegraph` 直接用引擎預告（全知視角 CLI），列出不改；前端開發頁沒有讀未過濾預告的地方。

## 7. 複雜度 noqa

無新增。
