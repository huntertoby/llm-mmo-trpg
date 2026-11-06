# Phase 3U-1 報告｜浮動卡底色＋屬性列＋全站排版掃描

規格：`docs/phases/Phase3U計畫.md` 第 1 節。3U-2（人物比例）未做。

## 1. 改了什麼

| commit | 內容 |
|---|---|
| `ab2c4e08` | 新增 `.float-panel` 變體：`.float-card.float-panel > .float-card-body` 有面板底色 `#14141c`、邊框、內距、陰影；種族卡／出身卡（`RaceOriginPicker.tsx`）與戰鬥中的種族技卡（`SkillBar.tsx`）加上它 |
| `b1c01b28` | 屬性列：`★建議` 改成名稱下方一行小字（`display:block`、`font-size:.8em`），第一欄維持 `3em`，按鈕與數值欄位不動；「影響：…」仍跨整列 |
| `592c2991` | 靜態規則（`floatCardRule.test.ts`）：每個 `<FloatCard>` 要嘛內容有 `<SkillCardView>`（技能卡自帶底色），要嘛 className 含 `part-tip-box` 或 `float-panel`；另檢查 `.float-panel` 的 CSS 有不透明底色與邊框。已確認拿掉 `float-panel` 時此規則會擋下（`run/RaceOriginPicker.tsx:40`） |
| `ab813827` | `layoutSmoke.ts`：`evaluate` 新增「每張顯示中的浮動卡有底色」「沒有文字溢出／相鄰重疊」兩項；新增 `runScreens(title)` 全站掃描；`window.__layoutSmoke.scan()` 可單獨掃目前畫面；vitest 補案例 |

## 2. 浮動卡使用處列表（全面掃描）

`FloatCard` 的直接使用處只有 6 個（外加 `Hint`／`PartTip` 兩個共用元件，`useFloatCard`／`HoverFloat` 為底層）：

| 位置 | 元件／class | 內容 | 改前底色 | 改後 |
|---|---|---|---|---|
| `run/RaceOriginPicker.tsx` | `skill-card-float race-pick-card`（種族卡、出身卡） | 文字，非技能卡 | 無（透明，使用者回報的問題） | 加 `float-panel`：有底色 |
| `ui/SkillBar.tsx` `RaceSlot` | `skill-card-float race-card`（戰鬥中種族技卡） | 文字，非技能卡 | 無（同一個問題，使用者尚未回報） | 加 `float-panel`：有底色 |
| `ui/SkillBar.tsx` 技能鈕 | `skill-card-float` | `SkillCardView` | 有（`.skill-card`） | 不變 |
| `ui/SkillBar.tsx` 迷你欄位（被動／反應／姿態） | `skill-card-float` | `SkillCardView` | 有 | 不變 |
| `ui/Hint.tsx` | `part-tip-box hint-tip-box` | 一句話說明 | 有（`.part-tip-box .float-card-body`） | 不變 |
| `ui/PartTip.tsx` | `part-tip-box` | 部件說明 | 有 | 不變 |
| 格子資訊卡 `UnitInfo`（`.unit-float`，不走 `FloatCard`） | 自有樣式 | 地形／角色 | 有（提示列另有煙霧檢查） | 不變 |

實機補掃（headless Chrome，1280×720，逐一滑過工坊技能頁、工坊裝備頁、開新一輪頁的前 30 個可滑過元素）：共看到 63 張浮動卡，無底色者 0 張。

## 3. 全站排版掃描

`runScreens` 涵蓋：首頁、工坊（技能、裝備）、開始畫面（開局、滑過種族卡、滑過出身卡、選武器與關鍵字後滑過關鍵字、屬性分配）、一輪畫面、戰鬥畫面（滑過技能卡）；每階段量「顯示中的浮動卡有底色」與「文字溢出自己的框」「相鄰元素矩形互相重疊 > 2px」。戰鬥畫面另有既有的 `runCase`（現在也含這兩項，並滑過第一個技能鈕）。

用法（同 `docs/開發PM交接.md` 6.2 第 5 步）：`localStorage.clear()` → 重新載入 → `await window.__layoutSmoke.runScreens("全站掃描")`（需從首頁開始）。

結果（內建瀏覽器，固定種子與弓）：

| 視窗 | `runScreens` | `runCase`（戰鬥，含舊有 9 項） |
|---|---|---|
| 1600×900 | 全 PASS（10 階段 ×2 項） | 見註 |
| 1280×720 | 全 PASS | 全 PASS（11 項） |
| 800×600 | 全 PASS | 全 PASS |

註：1600×900 只跑了 `runScreens`；戰鬥版面的 `runCase` 在 1280×720 與 800×600 跑，未另跑 1600×900 與 `shortBottom`（與本次修改無關的舊項目；若 PM 要補請說一聲）。

偵測器本身的驗證：把舊 CSS（`★建議` 行內）注入後，`scan()` 回報 `溢出 span.run-alloc-name「智力 ★建議」 73>42`；修正後為空。

掃描發現與修正（逐條）：
1. 種族卡、出身卡浮動卡無底色（使用者圖 1）→ 已修。
2. 戰鬥中種族技卡同樣無底色（同根因，掃描新發現）→ 已修。
3. 屬性列 `★建議` 溢出壓到減號按鈕（使用者圖 2）→ 已修。
4. 初版的「相鄰重疊」檢查把行內（`display:inline`）元素折行時外框互相重疊也算進去，造成假警報（開局的「主角：HP…（拋射…」那行）→ 檢查改為只看非行內元素。
5. 其他：未發現新的溢出或重疊。

## 4. 截圖（`docs/phases/img/3U-1-*`，headless Chrome 1600×900）

「前」是在新版畫面上注入舊行為的 CSS（把 `.float-panel` 內容區底色／邊框／內距清掉、`★建議` 還原行內）截的，不是舊版建置；效果與舊版相同。

- `3U-1-race-card-before.png` / `3U-1-race-card-after.png`：滑過種族卡（人類）
- `3U-1-alloc-before.png` / `3U-1-alloc-after.png`：屬性分配（建議主屬性「意志」，★建議）

## 5. 驗收

- `tsc --noEmit`：通過
- vitest 全量：117 檔、1148 項全過
- `pnpm build`：通過（只有既有的 chunk 大小警告）
- 排版煙霧檢查：見第 3 節，全 PASS
- 未動 Python，未跑 pytest 與 `scripts/check.py`

## 6. 待 PM 決定

1. 屬性列的做法選「★建議換到名稱下一行」而非加寬第一欄：加寬會讓只有那一列的按鈕位置與其他列不對齊。
2. `float-panel` 底色用 `#14141c`（與 `.skill-card` 相同），若美術 PM 要別的色請告知。
3. 「一輪畫面」之後的升級選技、營火、撿裝備、結束畫面（需要打完一場戰鬥）這次沒有放進 `runScreens`；如要涵蓋，需要能跳過戰鬥的測試入口（目前沒有）。
4. 1600×900 的戰鬥 `runCase` 與 `shortBottom` 本段沒有重跑（見第 3 節註）。
5. 開發過程中 worktree 內的 `.venv` 是我為了啟動伺服器用 `uv sync --offline` 建立的（未下載任何東西，來自快取）；也有他人佔用 8014 埠，我改用 8024，已關閉自己的伺服器。
