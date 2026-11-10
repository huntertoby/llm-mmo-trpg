# Phase PERF-4b｜vitest 省時與前端執行期環

> 來源：2026-11-10 效能與結構盤點，使用者同意（「go」）。**不得減少任何比對內容**，3301 項 vitest 全部保留。
> 盤點數字：PixiJS 載入佔 import 時間 78%（122 個測試檔各載一次）；同批對照 61～71 秒 → 27～32 秒。

## 範圍外

- 不拆 `badgeCapsule.test.ts`，不改 `sourceScan`。
- 不重構 `WorldScreen`、`WorldField`、`unitSprite`。
- 不下載任何外部套件，不改 `packageManager`，不動 `pnpm-lock.yaml`。

## 交付項目

1. **V1 預先打包 `pixi.js`**：在 vitest 設定加 `test.deps.optimizer.ssr`（或該版本對應的設定），只影響測試，不影響 `vite build` 產物。盤點時連測試本體也變快、原因沒查明，要查清楚是什麼造成的，並確認不是因為有測試被跳過或 mock 行為改變。
2. **S3 解開 `paperdoll.ts` ↔ `qSpec.ts` 執行期環**：把共用的部分抽到不互相依賴的模組。純搬移，不改任何數值或繪製行為。

## 受影響的既有功能

| 項目 | 影響 | 處理 |
|---|---|---|
| 正式建置 | V1 不應影響 | 比對 `vite build` 前後產物大小與檔案清單 |
| 雜湊快照（`creaturePose.test.ts`、`inkDollSnapshot.test.ts`） | V1 換 Pixi 打包形式、S3 搬移，都可能影響 | 快照不得重產，必須原樣通過 |
| 找環工具 | 目前沒有常駐檢查 | 加一個 vitest 檢查 `client/src` 非測試模組沒有執行期環（排除 `import type`），不依賴外部套件 |

## 行為一致測試

- 既有雜湊快照原樣通過，就是 S3 繪製行為不變的證據。報告附上這兩個檔案的通過紀錄。

## 驗收條件

- `pnpm -C client typecheck`、vitest 全過且項數不少於 3301（新增的環檢查另計）、`vite build` 結束碼 0。Windows 用 `npx vite build`（在 `client` 內）。
- 附對照：改前改後同一批交替跑各 3 次的 wall 時間與項數。
- `client/src` 非測試模組執行期環為 0。

## 報告

`docs/phases/PhasePERF-4b報告.md`：逐條驗收、對照時間、V1 變快的原因、待 PM 決定。
