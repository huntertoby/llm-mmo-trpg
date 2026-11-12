# Phase 6T-1d 報告

實作者，2026-11-05（程式）；收尾 2026-11-06（Mac：截圖、交件檢查）。依據：`docs/archive/art/6T-1c檢查.md`。只改 `client/`；沒碰遇敵卡、背包、雇用面板，也沒碰紙娃娃部件。

## 已完成

1. **soot 位置**（`b90dd4a5`）：`render/portrait.ts` 的 soot 從嘴邊 (4.4, −38.4) 3.6×1.9 移到右頰 (5.8, −40) 2.4×1.5、斜 −0.35，
   畫之前用臉形橢圓 (0, −42) 8.4×7.9 裁切（`ctx.clip`），不會溢出下顎。參數匯出成 `SOOT_*` 常數；只調參數加裁切，沒動部件。
   位置在鬍子上緣（x≈5.8 時約 −38.4）之上，帶鬍子的 NPC（鉚釘、兩位鐵匠、爐叔）也不會畫在鬍子上。
   測試：`portrait.test.ts`「6T-1d … soot 在臉頰、裁在臉內」兩項。
2. **小修 3「寄出」固定在面板底部**（`5118c191`）：`.mail-actions` 移到兩欄格線外（新的 `.mail-send-wrap`），
   `position: sticky; bottom: 0`、不透明底、上緣細金線＋12px 漸隱，z-index 6 蓋過捲動區下緣漸隱。
3. **小修 4 捲動區上緣**：只對郵寄面板（`.world-hud-panel[data-panel="mail"]`），上緣色塊改成實色 22px＋細金線（原本共用 56px 漸隱的下半段半透明）。
4. **小修 5 浮動卡避開標題**：共用 `floatPlacement` 加選填參數 `prefer`（預設 `above`，行為不變），`FloatCard`／`Hint` 加 `prefer` prop；
   附件格的 −、＋、×、裝備格的說明卡改 `prefer="below"`，下方放不下才翻到上方。
5. **小修 6 青石郵筒的苔**：苔斑 `#2a5e18`→`#1a4210`、大 1.2 倍、墨線 0.6→0.9，亮點 `#8ac850`→`#9ad858`（`POSTBOX_MOSS*`）。
6. **小修 7 全遊戲主要按鈕**（`8756bb0d`）：`base.css` 加 `button.primary:hover:not(:disabled)`（亮一階 `#4d6cb3`）與
   `button.primary:disabled`（深灰 `#36364a`，再加原本的 0.45 半透明）；拿掉郵寄面板自己的那條滑過規則；
   `entry.css` 加 `.entry-skin button.primary:disabled`（灰漸層），建角／首頁停用時也是灰。
   測試：`client/src/world/mail6t1d.test.ts`（按鈕規則、寄出黏底、上緣實色、prefer below、苔的亮度）。

已跑：相關 vitest 5 檔 72 項通過；`corepack pnpm -C client build` 結束碼 0（中途一次，非交件前最後一次）。

7. **開發頁 soot 頭像列**（`9a40ad1a`，收尾）：`dev/storyGallery.tsx` 加 `#soot`，五位帶 soot 的頭像（灰鴿、鉚釘、工坊師傅、主城鐵匠、爐叔）192／96／48，外觀直接讀 content（主城鐵匠在遊戲裡沒有頭像）。
8. **截圖**（`682362c6`，收尾）：見第 2 節。

## 1. 收尾時的環境與方法

- 2026-11-06 起在 Mac。merge main（`0f5018ec`）後先跑相關 vitest（543 項）與 `typecheck`，都過，不用修。
- 伺服器 `TRPG_SAVE_DIR=<scratchpad>/saves uv run trpg serve --port 8126`（Mock LLM）；開發頁用 `vite --port 5187`；無頭 Chrome（`--headless=new --mute-audio`，CDP 9483），
  `Emulation.setDeviceMetricsOverride` 設成檔名上的尺寸（device scale 1），jpg 品質 80。`_zoom` 從同一幀裁出、最近鄰放大。
- 存檔：scratchpad 的 `t1d/seed.py` 用正式 API 建 4 個角色（霜月：餘燼集灰鴿南邊、4 件裝備＋16 種材料；小白、阿霧：收件人；青石：霧渡鎮郵筒南邊），
  小白寄一封信給霜月。沒有攔 API、沒有假資料。拍之前先關掉升級對話框。

## 2. 截圖（`docs/art/shots/6t1d/`，18 張，單張 ≤ 171 KB）

| 檔案 | 內容 |
|---|---|
| `docs/art/shots/6t1d/6t1d_soot_faces_1600.jpg` | 開發頁 `#soot`：五位 soot 頭像 192／96／48 |
| `docs/art/shots/6t1d/6t1d_soot_faces_1600_zoom.jpg` | 同上 192 那一列 2 倍（看 soot 落點；見待決 1） |
| `docs/art/shots/6t1d/6t1d_panel_huige_1600.jpg` | 餘燼集郵寄面板（收件匣），灰鴿頭像 |
| `docs/art/shots/6t1d/6t1d_panel_huige_800.jpg` | 同上 800×600 |
| `docs/art/shots/6t1d/6t1d_panel_huige_1600_zoom.jpg` | 灰鴿 56px 頭像 6 倍（soot 幾乎看不出來，見待決 1） |
| `docs/art/shots/6t1d/6t1d_btn_disabled_1600.jpg` | 寄東西分頁、還沒選收件人：「寄出」停用灰（`#36364a`＋0.45），黏在面板底部 |
| `docs/art/shots/6t1d/6t1d_btn_disabled_800.jpg` | 同上 800×600 |
| `docs/art/shots/6t1d/6t1d_btn_hover_1600.jpg` | 填好草稿、捲到中段、滑過「寄出」：亮一階 `#4d6cb3`、沒有說明卡；寄出列黏底、上緣實色 |
| `docs/art/shots/6t1d/6t1d_btn_hover_800.jpg` | 同上 800×600 |
| `docs/art/shots/6t1d/6t1d_send_sticky_800.jpg` | 800×600 捲到中段（捲動區 1036／370）：寄出列黏底、上緣實色色塊、附件格 −／＋／× |
| `docs/art/shots/6t1d/6t1d_float_pinned_1600.jpg` | 附件「＋」的說明卡在下方（`side-below`）、已釘住 |
| `docs/art/shots/6t1d/6t1d_float_pinned_1600_zoom.jpg` | 同上 3 倍 |
| `docs/art/shots/6t1d/6t1d_float_pinned_800.jpg` | 同上 800×600 |
| `docs/art/shots/6t1d/6t1d_float_pinned_800_zoom.jpg` | 同上 3 倍（卡片沒蓋到「2 要寄的東西」標題） |
| `docs/art/shots/6t1d/6t1d_postbox_mist_1600.jpg` | 霧渡鎮青石郵筒（主角移開兩格） |
| `docs/art/shots/6t1d/6t1d_postbox_mist_1600_zoom.jpg` | 郵筒 6 倍：苔斑加深、加大 |
| `docs/art/shots/6t1d/6t1d_entry_disabled_1600.jpg` | 建角頁「建立並在主城醒來」停用時是灰漸層 |
| `docs/art/shots/6t1d/6t1d_entry_disabled_800.jpg` | 同上 800×600 |

（原本拍的 `6t1d_send_sticky_1600` 和 `6t1d_btn_hover_1600` 幾乎同一幀，刪掉前者。）

## 3. 驗收

- **6.5.1 浮動卡實測**（附件格「＋」的說明卡；1600×900 與 800×600 結果相同）：滑過約 150ms 後出現在**下方**、貼齊沒有空隙（觸發元素底 = 卡片頂）；
  分 6 步滑進卡片、停 500ms 仍開著；卡片內容短（scrollHeight 28 = clientHeight 28），沒有可捲的內容，捲到底與滾輪都不關閉；點一下 → `pinned`；
  滑鼠移開 600ms 仍開著；Esc 關卡片、郵寄面板留著。另測背包裝備格（`prefer` 預設 above）在 800 寬照舊出現在上方、可釘住、Esc 關閉。郵寄面板沒有長到要捲的浮動卡。
- **主要按鈕實機停用**：郵寄「寄出」（停用 `rgb(54,54,74)`＋0.45；滑過亮一階 `rgb(77,108,179)`，1600／800 都量過）；建角「建立並在主城醒來」（灰漸層＋0.45）；
  roguelite 結束畫面（`?dev=1&screen=ended`）與升級畫面（`level_up`）在 `.entry-skin` 內，停用時是灰漸層（`ended` 用開發工具把按鈕設成 disabled 量到；`level_up` 本來就停用）。
  確認框（`OathWarningDialog`、背包換武器確認）沒有自己的 `.primary` 規則，吃 `base.css` 的共用規則（CSS 只有 `entry.css` 一處覆寫）；沒在實機開到。
- `pnpm -C client exec vitest run`：267 檔 3055 項全過；`typecheck` 0；`pnpm -C client build` 結束碼 0。
- 排版煙霧檢查（`?dev=1&anim=0.1`，清 localStorage）：1600×900、1040×624、800×600 各 13 項全 PASS。
- 沒改 Python。

## 待 PM 決定

1. **soot 位置只調 `SOOT_*` 做不到，留到 QK**（照檢查：再不行寫進待決）。原因：紙娃娃依體型整個縮放（`inkDoll.ts` 的 `buildScale`：stout ×(1.12, 0.88)、tall ×(0.96, 1.1)），
   頭像配件卻用固定座標（假設頭中心 (0, −42)）。實測眼睛高度：tall（灰鴿）約 −45.7、stout（鉚釘、工坊師傅、主城鐵匠、爐叔）約 −36.9，差 9 單位；
   五位裡四位 stout、一位 tall，任何一組常數都只能顧一邊：現在 −40 對灰鴿落在嘴角右側（56px 面板頭像幾乎看不出來），對四位 stout 落在**眼睛上方的髮際／額頭**（見 `6t1d_soot_faces_1600_zoom`）。
   裁切橢圓也是固定在 −42，對 tall 會往下顎外多出約 4 單位。建議（要改程式，超出本段「只調常數」）：畫 soot 前 `ctx.scale(...buildScale(look))`，讓落點與裁切跟著體型走；
   同一問題也影響 `goggles`（stout 的護目鏡在眼睛上方）等其他頭像配件，是否一起改請美術 PM 決定。本段 `SOOT_*` 維持原值沒動。
2. 上緣實色色塊只套在郵寄面板；其他面板仍是共用的 56px 漸隱。要全面改的話改 `theme.css`。
3. 用 `primary` 當「選中」狀態的切換鈕（分頁、武器、關鍵字等）在 busy 停用時也會變灰。
4. 確認框的停用樣式只用 CSS 推定（沒有覆寫），沒有實機開到；要不要補實機截圖。

## 啟動過的程序

- 收尾（Mac）：`uv run trpg serve --port 8126`、`vite --port 5187`、無頭 Chrome（CDP 9483），交件前都用自己記下的 PID 結束，三個埠確認沒在聽。沒用 8000／8001。
- Windows 時期：預覽伺服器沒開始聽就停掉；無頭 Chrome PID 65248 已結束。
