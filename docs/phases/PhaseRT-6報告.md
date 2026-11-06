# Phase RT-6 報告：主城 HUD 小修

實作 agent，2026-11-07。分支 `dev/rt6`（基底 main `e9b3043e`）。
依據：`docs/art/6F-20檢查.md` 第 3 節、`docs/phases/Phase6F-20報告.md` 待決第 3 項、`docs/archive/art/RT-5d檢查.md` 第 3 節、`docs/archive/art/RT-5b檢查.md` 必修 4。

## 1. 各項結果

| # | 項目 | 結果 | commit |
|---|---|---|---|
| 1 | 主城 800 寬：收合的任務鈕壓到房子 | **做到**。窄視窗（< 900）收合時，任務鈕改貼在右欄錢包正下方（設計座標 top 208＝錢包下緣＋6），右緣和錢包對齊。寬視窗手動收合、展開的任務欄都照舊 | `00f768fb` |
| 2 | 主城 800 寬：技能說明卡蓋到「WASD 走一格」 | **做到**。功能列任何一顆鈕的說明卡開著時，說明列讓位（隱藏、不接滑鼠）；說明卡關了就回來。三種寬度行為一樣（說明卡本來就貼在功能列正上方，三種寬度都會蓋到說明列） | `00f768fb` |
| 3 | `rt5d_3_caption_1600`：說明列壓在碑前木橋上緣 | **做到**。浮橋每一格（`look: sky_bridge`）算進說明列要避開的裝飾物；重現 rt5d_3 的畫面，說明列往右挪 173（`data-shift=173`），木橋整個露出來 | `00f768fb` |
| 4 | 1600 寬夾邊「！」的上邊界 | **現況合格，沒改程式**，只補截圖（見第 3 節） | — |
| 5 | 補拍 | 7 張（見第 4 節） | 報告 commit |

### 做法

- **第 1 項**（`client/src/world/hud.ts`）：`hudLayout` 在 `collapsed && narrow` 時，任務鈕的 top 用新常數 `TRACKER_TUCK_TOP`（208），其他情況照原本的 `trackerTop` 算式。鏡頭的安全區（`hudInsets`）只看右欄最左緣，任務鈕寬 36 在右欄裡面，所以鏡頭不變。
- **第 2 項**（`client/src/styles/world-hud.css`）：`body:has(.float-card .hud-bar-card) .world-field.hud .world-field-bar { opacity: 0; pointer-events: none; }`。
  - 說明卡是 portal 到 body 的共用浮動卡，WorldField 不知道它開沒開，用 CSS `:has` 最小改動。
  - 沒有加淡出轉場：內建瀏覽器的分頁在背景時轉場不會跑完，量到的不透明度會落後；直接隱藏比較可靠。
  - 浮動卡本身（位置、貼齊、翻轉）沒改，仍照 6.5.1 貼在按鈕上方。
- **第 3 項**（`client/src/world/hudAvoid.ts`、`WorldField.tsx`）：新函式 `bridgeCellRect`（整格），加進 RT-5d 的裝飾物清單（燈柱、花壇之後）。照 `captionShiftDecor` 的規則：先試同時避開碑身、主線的人和裝飾物，讓不開才退回只避開碑身。

## 2. 測試與檢查

- **vitest**：新增 `client/src/world/rt6.test.ts`（15 個）。
  - 第 1 項：三種窄舞台下，任務鈕在錢包下方 6、右緣對齊、不碰其他 HUD 塊、在舞台上半部；寬視窗收合、展開時位置和舊算式一樣。
  - 第 2 項：CSS 規則存在（隱藏＋不接滑鼠），說明列沒有 opacity 轉場。
  - 第 3 項：用 rt5d_3 的實測幾何，說明列挪開後不壓木橋、不壓 HUD，挪的量＝173（和實機一致）；沒壓到就不挪。
  - `evaluateTown` 的純函式：好的版面全 PASS，三種壞法各自 FAIL。
- **全量 vitest**：249 檔、3133 個全過。`pnpm -C client typecheck`、`pnpm -C client build` 通過。
- **排版煙霧檢查**：
  - `layoutSmoke` 原本沒有主城的量測，新增 `window.__layoutSmoke.runTown(title)`（`client/src/dev/townSmoke.ts`）。在大世界實地畫面上量：HUD 各塊（`evaluateHudLayout` 五項）、窄視窗收合的任務鈕貼在錢包下方、說明列不壓 HUD、滑過功能列左／中／右三顆鈕時說明列讓位、說明卡關掉後說明列回來。用法：先進大世界（開發模式建角色後「站起來」），再執行 `await window.__layoutSmoke.runTown("標題")`。
  - `runTown`：1600×900、1040×624、800×600 **全 PASS**。
  - `runCase`（戰鬥）：三種尺寸都只有 1 項 FAIL：「戰鬥：四角飾件沒有壓到內容」（主角卡左下飾件 × 技能圖示 `svg.skill-chip-glyph`）。**這是 main 原本就有的**：把 `client/src` 暫時切回 `e9b3043e` 重建，800×600 同一項照樣 FAIL；這段沒有改到戰鬥畫面。見待決第 1 項。其他各項全 PASS。
- **6.5.1 浮動卡實測**（主城功能列「技能」的說明卡，無頭 Chrome 真的滑鼠事件）：

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現，說明列隱藏 | ✓ | ✓ |
| 分 6 步滑進卡片後不關 | ✓ | ✓ |
| 捲動（滾輪）後不關（卡片內容不需捲動，scrollHeight＝clientHeight） | ✓ | ✓ |
| 點一下釘住 → 滑出去不關，說明列仍隱藏 | ✓ | ✓ |
| Esc 關閉 → 說明列回來 | ✓ | ✓ |

## 3. 第 4 項：1600 寬夾邊「！」的上邊界

- 拍法：開發頁 `?dev=1&devcam=0,300`，主角站在西邊（雲嶺碑旁），守印人被推出畫面上緣。
- 量到：「！」夾在 y 286～310（畫面座標），泡泡約 [480,280,690,346]（看圖估的；`devcam=0,240` 那次實測泡泡 [528,280,738,346]、「！」頂端同樣 286）。全部在畫面內，沒有超出上緣。
- 旁邊的 B 頭在約 y 222～240，「！」在 B 腳下的徽章與朝向三角形下方，不重疊、不在頭頂（RT-5b 必修 4 的規則）。
- 上邊界 y≈286 的來源（RT-5d 檢查第 3 節問的）：夾邊用的是安全區 `safe`，上緣＝`hudInsets.top`＝左欄主角卡與隊友卡的下緣（舞台 y≈226）。這是 RT-5 的設計（夾進去的位置不壓主角卡、小地圖），是故意的；但這條上緣橫跨整個畫面寬，所以畫面中間的「！」也停在隊友卡下緣的高度。見待決第 2 項。

## 4. 截圖（`docs/art/shots/rt6/`，7 張，jpg 品質 80，最大 228 KB）

拍法：800 寬那 3 張用內建瀏覽器（開發頁，800×600）；1600 寬那 4 張用自己啟動的無頭 Chrome（`--mute-audio`、CDP `setDeviceMetricsOverride` 1600×900、device scale 1），網址加 `?mute=1`。`_zoom` 從同一張裁出來、最近鄰放大。

- `docs/art/shots/rt6/rt6_1_tracker_card_800.jpg`：主城 800 寬開場，「技能」說明卡釘住。右上任務鈕貼在錢包下方（約 752～778, 214～240），房子屋頂從約 y 250 開始，不再被蓋；說明列隱藏，說明卡下方沒有「WASD」字。（對照舊圖 `docs/art/shots/6f19/6f19_float_800_pinned.jpg`）
- `docs/art/shots/rt6/rt6_1_tracker_800_zoom.jpg`（3 倍）：任務鈕和房子。
- `docs/art/shots/rt6/rt6_2_card_caption_800_zoom.jpg`（2 倍）：說明卡與功能列之間沒有說明列。
- `docs/art/shots/rt6/rt6_3_caption_1600.jpg`：重現 rt5d_3（主角在西邊、雲嶺碑旁）。說明列在 [838,784,1108,805]，荒原碑前的木橋（約 736～832）整個露出來。
- `docs/art/shots/rt6/rt6_3_caption_1600_zoom.jpg`（2 倍）。
- `docs/art/shots/rt6/rt6_4_bubble_1600.jpg`：開發頁 `devcam=0,300`，守印人夾在上邊。下方露出地圖外的深色區是開發鏡頭位移造成的（同 RT-5d）。
- `docs/art/shots/rt6/rt6_4_bubble_1600_zoom.jpg`（3 倍）：「！」在 B 的腳下方，不在頭上。

## 5. 待 PM 決定

1. **戰鬥煙霧檢查的舊 FAIL**：「四角飾件沒有壓到內容」主角卡左下飾件 × 技能圖示，三種尺寸都有，main `e9b3043e` 就有（不是這段造成的）。建議排進戰鬥 HUD 下一段，或確認是不是量測誤報。
2. **夾邊「！」的上緣是左欄下緣，整個畫面都一樣高**（第 3 節）。現況合格（在畫面內、不在別人頭上），沒改。如果要讓畫面中間的「！」貼近地圖上緣，可以改成只在左欄、右欄的水平範圍內避開，屬於規則變更，請美術 PM 決定。
3. **夾邊「！」可能貼在別人腳下**：`rt6_4_bubble_1600_zoom` 的「！」離 B 的朝向三角形約 8px。不在頭頂、符合 RT-5b 的規則；但會不會讓人以為是 B 的「！」，請美術 PM 看圖。
4. **說明列讓位的範圍**（照最保守做法）：只要功能列任何一顆鈕的說明卡開著（含釘住），說明列就隱藏，不量是否真的重疊。站在傳送石上時，說明列裡的「傳送：…」按鈕在說明卡開著時也會暫時看不到、按不到，關掉說明卡就回來。
5. **任務鈕的新位置只用在窄視窗**（照「其他寬度不變」）。寬視窗手動收合時，任務鈕仍在原本的地圖中段位置；要不要一起改成貼錢包，請美術 PM 決定。

## 6. 程序

- API 伺服器：`TRPG_SAVE_DIR=<scratchpad>/rt6/saves TRPG_DEV_ROUTES=1 uv run trpg serve --port 8134`（存檔在 scratchpad，沒碰 `saves/`）。
- 無頭 Chrome：CDP 埠 9134、`--mute-audio`、`--user-data-dir` 在 scratchpad。
- 兩個都只用自己的 PID 結束（`kill <pid>`），結束後確認 8134、9134 都沒有在監聽。沒碰 8000、8001。
- worktree 第一次 `uv run` 建了 `.venv`（`uv sync --frozen`）；截圖裁切用 `uv run --with pillow`（臨時，不改專案相依）。暫存檔都在 scratchpad，沒有 commit。
- 內建瀏覽器結束時已 `resize_window` preset `desktop`。

## RT-6b（RT-6 驗收退回的修正）：暫停（WIP）

2026-11-07，使用者指示非 Q 版工作先停，這段停在 WIP。分支 `dev/rt6b`。

- **做到**：第 4 項的程式（`client/src/world/hud.ts`：收合的任務鈕寬窄視窗都貼錢包下方，`tuck = opts.collapsed`）。**還沒改測試**：`rt6.test.ts`「寬視窗手動收合：位置照舊」那一條現在會 FAIL，`dev/townSmoke.ts` 的 `tracker-tuck` 也還只檢查窄視窗；都沒跑過。
- **還剩**：
  1. 夾邊「！」上緣分欄（`opening.ts` 的 `guideAnchor`）：只在左右欄水平範圍內用欄的下緣，中間用地圖可見範圍上緣＋`GUIDE_TOP`。打算在 `HudCamera` 加 `columns`（新函式 `hudColumnRects`：hero、mates、shadow、place、minimap、clock、wallet、tracker），在 `WorldField` 轉成畫布座標傳給 `FieldHeads`→`guideAnchor`；沿邊挪的時候每個候選位置重算上緣。
  2. 「！」旁的箭頭：`FieldHeads` 把 `EdgeArrow` 改成只要夾邊就畫在「！」旁（不只收起來時），泡泡名字旁的箭頭拿掉（待美術 PM 確認）；避讓改用每個別人的 `unitRect` 往外擴半格（24×scale），太近就沿邊挪。
  3. 說明列只在和說明卡真的重疊時隱藏：拿掉 `world-hud.css` 的 `body:has(...)` 規則，改成 `WorldField` 用 MutationObserver 量 `.float-card` 與說明列的矩形，重疊才加 class；`townSmoke` 加「沒重疊卻隱藏＝FAIL」。
  4. 補 `rt6.test.ts` 幾何斷言、`townSmoke` 改寬視窗也檢查任務鈕；全量 vitest、typecheck、build、`runTown`／`runCase` 三尺寸；補拍 `docs/art/shots/rt6/*_v2`。
- **下一步**：恢復時從上面第 4 項的測試修正開始，再做 1→2→3。
- 這段沒有啟動伺服器或瀏覽器。
