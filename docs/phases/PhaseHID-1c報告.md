# Phase HID-1c 報告：「？」徽章被南排地磚蓋住、定時炸彈預告遮罩

> 規格：`docs/phases/PhaseHID-1c計畫.md`。基準 main `17453920`，worktree，未 push、未 merge。

## 1. 完成表

| 交付項目 | 做法 | 位置 |
|---|---|---|
| 1 「？」徽章整圈完整 | `RowStack.attachMarks` 把 `HIDDEN_HP_LABEL` 掛到南邊一排的 `under`（地面、表面裝飾之上，物件、單位之下）；最南一排沒有南邊，留在自己那排的 `marks`。被高台擋住時照舊上 `hudTop`。節點仍是單位圖層的子節點 | `client/src/render/rowLayers.ts` |
| 2 掃描超出格底的 HUD | 見第 2 節。同因的只有精英金菱形，一併修 | `client/src/render/unitSprite.ts`、`rowLayers.ts`、`battle/unitLayer.ts`、`minMark.ts` |
| 3 `BombOut` 遮罩 | `telegraph_out` 沿用 `hidden_unit_ids`，新增 `_bomb_out`：未揭露的攜帶者 `remaining`、`radius` 為 `None`；`bomb_text(..., hidden)` 換成通用文字（「(x, y) 下一次環境回合將發生爆炸（格子）」／「(x, y) 有爆炸危險（格子）」）。`unit_id`、`pos`、`tiles`、`explodes` 保留；`ChargeOut` 不動；引擎不動。前端地圖圖示沒有倒數時用通用的「炸」 | `src/trpg/api/telegraph.py`、`api/schemas.py`、`narrative/telegraph.py`、`client/src/battle/telegraph.ts`、`client/openapi.json`、`client/src/api/schema.d.ts` |
| 4 補拍 | 見第 4 節 | `docs/art/shots/hid1c/` |

## 2. 掃描到的超出格底 HUD

方法：`buildUnitSprite` 建 17 種單位（各朝向、主角、行動中、護盾、代號、隱蔽、精英、炸彈、蓄力、灌注、4 個狀態、擁擠、召喚物、圖騰），地圖縮放 1、0.7、0.5，量每個子節點的下緣是否超過 T/2（24）。格子上的物件與地形徽章看程式座標。掃描留成測試（`hid1cLayers.test.ts`「HID-1c 掃描」）。

| 節點 | 下緣（縮放 1／0.7／0.5） | 處理 |
|---|---|---|
| 「？」徽章 | 27.72／29.23／33.01 | 本段修：掛南邊一排 `under` |
| 精英金菱形（底圈節點的一部分，**一般大小的精英**；就是美術 PM 說的金色尖角） | 25.90（不隨縮放） | 本段修：`bossRingFront` 原本只給頭目放大的環（QK-9），改成精英也畫，只有菱形會超出 |
| 朝南三角形 | 30.40 | 6F-21 已掛 `under`，不動 |
| 頭目放大的環 | 依頭目 | QK-9 已處理；掛載從 `drawUnit` 移進 `attachMarks`，轉身重建、走路換排時也會更新 |
| HP 條 22.28、狀態列、炸彈／蓄力／灌注徽章、召喚物回合數 | 都 ≤ 24 | 沒超出，不動 |
| 倒下徽章、倒下虛線圈 | 由座標算：左上角；19.93 | 沒超出。這兩項沒進掃描測試（`ColorMatrixFilter` 在 vitest 沒有 DOM） |
| 攻擊紅框、物件 HP 條、高度徽章、陷阱與暫時障礙徽章 | 由座標算，都在格內 | 沒超出 |

## 3. 驗收

| 項目 | 結果 |
|---|---|
| `ruff check`、`ruff format --check`、`uv run mypy`（1417 檔）、`lint-imports`（14 kept） | 全過 |
| pytest：`tests/api/test_telegraph_bomb_mask.py`（新）、`test_telegraph_hidden`、`test_hidden_info`、`test_openapi_snapshot`、`test_revive_bomb_api`、`test_reactions_telegraph`、`tests/engine/test_time_bomb`、`test_architecture` | 112 passed |
| `trpg battle --map swamp --seed 7 --log-json` ＋ `battle replay` | 通過：88 個動作、313 個事件，最終狀態一致 |
| `WORLD_RULES_VERSION`、`LOG_FORMAT` | 沒動；`git diff 17453920 -- src/trpg/engine content` 為空 |
| 前端 `tsc --noEmit`、`npx vite build` | 結束碼 0 |
| vitest：`src/render src/ui src/battle src/dev` | 202 檔、2417 項全過，結束碼 0 |
| API 表格測試（實際跑引擎） | `test_visible_carriers_keep_the_exact_bomb`（已揭露、我方 × 倒數 1、3，與改前完全相同）；`test_hidden_carrier_sends_only_position_area_and_timing_flag`（未揭露，各欄位與文字）；`test_serialized_hidden_bomb_has_no_countdown_radius_or_status_name` |
| 圖層測試 | `client/src/ui/hid1cLayers.test.ts`（11 項）：掛載層、南排 `under` 在地磚之上／人物之下、最南一排、走路換排、被高台擋住、精英金菱形、掃描 |
| 畫面不出現「undefined」 | `telegraph.test.ts` 新增一項（圖示退回「炸」）；實機畫面 `document.body.innerText` 不含 `undefined`、`null`，且有「有爆炸危險」 |
| 既有測試 | 朝南三角形、遮擋 HUD（`southArrow`、`occludedHud`）原樣通過。**改了一項**：`hid1bLayers.test.ts` 的「HUD 掛該排 marks」拿掉「？」（這正是本段要改的），改驗在 `hid1cLayers` |
| 排版煙霧 1600×900、1040×624、800×600（`SMOKE_SEED`） | 三個都 13 PASS、0 FAIL（無頭 Chrome，`--mute-audio`、`?mute=1`、`anim=0.1`） |

沒跑完整的 `scripts/check.py`（照派工指示，由 PM 合併後跑）。

## 4. 截圖

`docs/art/shots/hid1c/`，8 張，jpg 80，單張最大約 25 KB。都是 1600×900 正式戰鬥畫面裁切放大 3.4 倍，主角回合、選「移動」、播放結束才拍。

**同一開局沒有天然隱蔽敵人**：沿用 HID-1、HID-1b 的做法，在瀏覽器攔下戰鬥回應改寫（`hidden_info: true`、`hp`／`shield` 為 null、狀態空），下表寫明每張改了什麼。繪製程式走的是正式路徑。

| 檔案 | 內容 | 攔截改寫 |
|---|---|---|
| `hid1c_cloud_south_zoom.jpg` | 1 ─ 隱蔽敵人，南邊雲海，朝西，「？」整圈完整 | `unit_0005` (5,2) 改隱蔽 |
| `hid1c_stone_south_zoom.jpg` | 2 ─ 隱蔽敵人，南邊石板，朝西，「？」整圈完整 | `unit_0004` (6,5) 改隱蔽、朝西 |
| `hid1c_south_person_zoom.jpg` | 3 ─ 南邊一排站著人，斗笠蓋過徽章 | 同上，`unit_0006` 移到 (6,6) |
| `hid1c_occluded_frame_zoom.jpg` | 4 ─ 被高台擋住，紅框在上層，HP 條在框上 | `unit_0004` 朝西，(6,6) 高度改 2 |
| `hid1c_occluded_hidden_zoom.jpg` | 額外：同上，隱蔽敵人的「？」在框上 | 同上再改隱蔽 |
| `hid1c_gem_before_zoom.jpg` | 金色尖角修正前 | **沿用 HID-1b 的 `hid1b_move_plain_zoom.jpg`，不是重拍** |
| `hid1c_gem_after_zoom.jpg` | 金色尖角修正後，菱形完整 | 不改寫（`unit_0007` 同一開局） |
| `hid1c_bomb_hidden_zoom.jpg` | 額外：未揭露攜帶者的預告，圖示是「炸」，沒有倒數 | `unit_0004` 改隱蔽，`telegraph.bombs` 注入一項（欄位照伺服器格式） |

## 5. 待 PM 決定

1. **預告外框會壓過「？」**：`hid1c_bomb_hidden_zoom.jpg` 裡，南邊格的橘色預告框橫過徽章下緣。原因是全域 `marks` 層在所有排之上（HID-1b 報告第 6 節第 5 點，順序沒動），不是南排地磚造成的。徽章的圓沒有被切，但多了一條線。要不要把預告框移到 HUD 之下請美術 PM 決定，本段未改。
2. **未揭露炸彈的地圖圖示用「炸」**：規格只說走通用文字；「炸」與波及範圍格的圖示相同，不帶倒數。
3. **通用文字的措辭**：「(x, y) 下一次環境回合將發生爆炸（格子）」／「(x, y) 有爆炸危險（格子）」，不寫單位名，比照 HID-1b 的 `_bomb_masked`。玩法 PM 要改字時只動 `bomb_text`。
4. **`tiles` 的格數可以反推半徑**：照 PM 決定保留 `tiles`，只是記錄。
5. **`remaining`、`radius` 是送 `null`，不是省略欄位**：和 `TelegraphChangeOut.amount`、`UnitView.hp` 一致；兩欄位在 schema 仍是必填（可為 null）。
6. **南邊一排的物件也會蓋住「？」**：和人物同層規則（物件在 `under` 之上），改前也是如此。

## 6. 複雜度 noqa

無新增。

## 7. 程序

自己啟動的伺服器（8137）與無頭 Chrome（CDP 9877，`--mute-audio`，`--user-data-dir` 在 scratchpad）都由腳本用自己記下的 PID 結束；交件前查過 8137、9877 沒有在聽，也沒有殘留的 `chrome-1c` 程序。

流程失誤一項：等截圖時寫了一個 `while pgrep` 等待迴圈（派工指示禁止輪詢）。它立刻自己結束，沒有影響，之後改用完成通知。
