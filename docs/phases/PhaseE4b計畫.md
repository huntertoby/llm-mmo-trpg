# Phase E4b 計畫：觸發圖示移植（格擋時、你讓別人位移時）＋倒地說明框懸掛縮排

> 來源：
> - 美術移植需求：`docs/art/E4-觸發圖示-美術.md` 第 6 節（要做的 1～7）、第 7 節（裁定）。樣張 `docs/art/sample/e4-triggers.html`（網址加 `?mute=1`），畫法在 `docs/art/sample/e4Triggers.js` 的 `blockArt`、`displaceArt`。
> - 美術 E4 驗收：`docs/art/E4驗收.md` 小修 1（倒地說明框的分點換行懸掛縮排）。
>
> 只改前端。和 CR-1 平行：**不改** CR-1 會碰的暴擊、傷害預覽、技能卡暴擊那一行，也不改 `src/`、`content/`、`config/`。

## 範圍

1. **兩個觸發圖示**：照美術第 6.1 節第 1～3 項：
   - `parts.ts` 的 `TRIG` 在最後加 `on_block`、`on_displace`，前面的順序不動。
   - 拿掉 `TRIG_ALIAS` 的兩筆暫借，改註解。
   - 畫法逐行搬，不加新色。
2. **測試**：照第 6.1 節第 4～6 項改 3 個測試檔，包括 `qIconSkills.test.ts`、`qIconQi2d.test.ts`、`arAp2Borrow.test.ts`。`arAp2Borrow.test.ts` 第 53 行「TRIG 最後一個」要改寫。
3. **倒地說明框懸掛縮排**：分點換行後，第二行對齊上一行「・」後面的字，做法和 E2 驗收定的加註換行一樣。6 行字不改。
4. **截圖**（存到 `docs/art/shots/e4b/`，交美術 PM）：
   - E4 的兩張技能卡，1600 寬，看組裝列的時機圖換成新的。
   - 組裝列 30／26／18，800 寬真 1 倍 PNG 一張，再加最近鄰放大一張。
   - 倒地說明框 800 寬一張。

## 驗收

- **結果不變**：只改前端，後端不動。其他部件的基準雜湊不重錄。
- **靜態檢查**：tsc、vitest、build，結束碼都要是 0。
- **全量檢查**：全部 commit 之後，用 SendMessage 問開發 PM「準備跑 check.py」，收到回覆才跑 `uv run python scripts/check.py --all`。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseE4b報告.md`。
