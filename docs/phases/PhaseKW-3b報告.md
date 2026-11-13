# Phase KW-3b 完成報告｜層數關鍵字換成第 2 版圖

> 實作 agent，2026-11-13。依據：`docs/art/KW樣張.md` 第 11 節（換圖清單）、第 10 節（K1～K7）、第 7 節（第 2 版指紋）；背景 `docs/phases/PhaseKW-3報告.md`。
> 開工時 worktree 快轉到 main `1a19e7be3`。

## 結論：不用換，main 已經是第 2 版

第 11 節寫「KW-3（main `2fcc2ac25`）照第 1 版 `e3dfb4258` 做」，但查下來 KW-3 用的就是第 2 版：

- 時間順序：美術第 2 版 `c9e3fd34c`（18:17）與複審 `2c01cd347`（18:18）在 KW-3 開工的 main `12d410797` 之前；KW-3 的程式 commit `dcad6ab78`、`25012c74f`（18:31）都在它之後（`git merge-base --is-ancestor c9e3fd34c dcad6ab78` 為真）。KW-3 報告第 4 節比的也是第 2 版第 7 節的 9 行。
- 第 11 節逐條對照遊戲端程式（main `1a19e7be3`）：

| # | 第 2 版要的 | 遊戲端現況 |
|---|---|---|
| K1 | 連擊圓章三道直斬線、≤14px 兩道 | `render/qIcon/keywords.ts` 的 `comboSlashes`（說明「三道直的斬線…；≤14px 兩道」） |
| K1／K3 | 創角連擊直斬線、透明度 1／0.85／0.7 | `ui/CreateIcons.tsx` 的 `combo_point`：三條直邊 path（樣張 `comboCreate` 算出），`fillOpacity` 0.7／0.85／1 |
| K2 | 氣 ≤14px 拿掉勾玉眼、深半邊 `#0e7f6a` | `keywords.ts` 的 `kiTaiji`：`if (o.tiny) { half("#0e7f6a"); return; }` |
| K4 | 創角專注 `#476deb`、怒氣 `#ff4a62` | `CreateIcons.tsx` 的 `KEYWORD_ICON_COLOR`：`focus: "#476deb"`、`fury: "#ff4a62"`（沒有 `#7d96ff`） |
| K5 | 格寬 6、步距 7、右內距 5；含膠囊 60／53／46／46 | `render/qIcon/stackGauge.ts` 的 `PIP = { w: 6, h: 10, step: 7, padR: 5 }`、`gaugeOuter`（KW-3 實機 DOM 量到 60×22、53×22、46×22、46×22） |
| K6 | 怒氣亮格 `#ff4a62`，框與外暈 `#df2046` | `stackGauge.ts` 的 `HUD_FILL.fury = "#ff4a62"`，框與外暈用 `KEYWORD_COLOR` |
| K7 | 只補紀錄 | — |

所以這段**沒有改任何程式與測試**，也沒有拍 `docs/art/shots/KW-3b/`（沒有換掉的圖，改前＝改後；第 2 版的實機與真 1 倍 ×4 截圖就是 `docs/art/shots/KW-3/`）。

## 指紋（重新量，main `1a19e7be3`）

自己的 vite（127.0.0.1:5310）開 `/dev/keyword-gallery.html?set=hash&mute=1`，無頭 Chrome `--headless=new --disable-gpu --mute-audio --force-device-scale-factor=1 --remote-debugging-address=127.0.0.1 --dump-dom`（自己的設定檔），
腳本抓 `#hash` 和 `docs/art/KW樣張.md` 第 7 節逐行比：**9／9 逐字相同**，沒有多出或少的行。
第 1 版的 `chip combo_point a`（`6d6b4797…`）、`chip ki a`（`83753649…`）、`hud combo_point a`（`97742787…`）都不在輸出裡。
既有 12 個圓章與裝備外觀：沒有改檔，KW-3 量過的 840＋96 組 0 差維持（這次沒有重跑 `set=compare`）。

## 檢查與結束碼

| 檢查 | 結束碼 |
|---|---|
| vitest `render/qIcon/qIconKW3.test.ts`、`ui/entryScreen.test.ts`、`ui/statusCard.test.ts`（92 個） | 0 |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |

vite 用自己記下的 PID（64344）關掉，5310 已沒有在聽；`--dump-dom` 的 Chrome 自己結束。沒有碰 RG-4 的檔。

## 待 PM 決定

1. `docs/art/KW樣張.md` 第 11 節開頭「KW-3 照第 1 版做」與事實不符，建議美術 PM 改成「KW-3 已是第 2 版，不用換」（這段沒改美術文件）。
2. 第 11 節「仍待定」的三件（創角 15px、HUD 0 層、名稱並存）KW-3 裁定已處理或已轉交，這段沒動。
