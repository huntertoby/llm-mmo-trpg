# Phase AR-AP2 計畫：預支美術移植

> 來源：美術 PM `docs/art/AP-2-移植需求.md`（88005845a），畫法在 `docs/art/AP-2-美術.md` 第 5 節（逐行照做）和第 9 節裁定。
> 只改前端（`client/`）和部件暫代清單。

## 範圍
照移植需求第 1 節的 7 項做，每項附第 1 節指定的截圖：
1. 狀態「預支」`borrowed_ap` 的圖示。
2. 原語「預支」`borrow_ap` 的圖示（和狀態同一個圖），從 `*_ALIAS` 拿掉暫借。
3. 觸發 `on_ap_spent_all` 的圖示。
4. 施放演出 `borrow_pull`（320 ms，胸口用 `chest()`），照 `rerollFx.ts` 的先例拆檔。
5. AP 列的菱形和紅斜線在 215 ms 開始淡入。
6. `statusIcon.ts` 的「待補畫」註解。
7. 部件暫代清單拿掉這三樣。

移植需求第 2 節列的是可接受的現象，不要修。

## 驗收
- 前端 tsc、相關 vitest、build 結束碼 0。
- 截圖存在 `docs/art/shots/ar-ap2/`，格式照移植需求第 4 節：真 1 倍和最近鄰用 PNG，其他用 jpg 80。測試要靜音：無頭 Chrome 加 `--mute-audio`，網址帶 `mute=1`。
- 不要改 Python 規則和內容資料；需要改就停下來回報。
- 報告寫在 `docs/phases/PhaseAR-AP2報告.md`。
