# Phase PERF-4b 完成報告｜vitest 省時與前端執行期環

基準 commit：`4d4948c8`。環境：Windows、Git Bash、16 核心；量測期間有其他 agent 同時工作。vitest 5.0.5、vite 8.3.4、pixi.js 8.22.0。

## 交付

| commit | 內容 |
|---|---|
| `7f5fb28c` | V1：`client/vite.config.ts` 加 `test.deps.optimizer.ssr`（`enabled: true`、`include: ["pixi.js"]`） |
| `81f89e42` | S3：`itemColors`（連同私有的 `darker`）原樣搬到新檔 `client/src/render/itemColors.ts`；`qSpec` 改從新檔匯入；`paperdoll` 匯入後轉出口，其餘 importer 不動 |
| `1394bb16` | 環檢查：`client/src/test/importCycles.ts`、`importCycles.test.ts`（14 項） |

只動了上述 `client/` 檔案與本報告。沒動 `packageManager`、`pnpm-lock.yaml`，沒下載任何外部檔案（`install --frozen-lockfile --offline` 結束碼 0）。

## 逐條驗收

| 條件 | 結果 | 證據 |
|---|---|---|
| `typecheck` 過 | 通過 | `corepack pnpm typecheck` 結束碼 0（HEAD） |
| vitest 全過，項數 ≥ 3301（環檢查另計） | 通過 | 改後 3315 passed（3301＋環檢查 14），failed 0、pending 0、todo 0，275 檔 |
| `vite build` 結束碼 0 | 通過 | `npx vite build` 結束碼 0 |
| 正式建置不受 V1 影響 | 通過 | V1 後 118 個產物的 sha1 與基準逐檔相同 |
| 建置與基準比對（含 S3） | 通過 | 118 個檔案，去掉 hash 的檔名相同；總大小 7,164,284 → 7,164,280 bytes。內容有變的只有 `index` 少 4 bytes，另外 5 個 chunk 大小相同、只有 hash 變 |
| 雜湊快照原樣通過，不得重產 | 通過 | `render/creaturePose.test.ts` 5 passed、`render/inkDollSnapshot.test.ts` 5 passed；兩檔沒有修改。vitest 快照統計 matched 6、updated 0、added 0、unmatched 0 |
| 附對照：交替各 3 次的 wall 與項數 | 完成 | 見下節 |
| 非測試模組執行期環為 0 | 通過 | `src/test/importCycles.test.ts`「靜態 import 沒有環」「算上動態 import() 也沒有環」；修改前同一檢查抓到 `[render/paperdoll.ts, render/qSpec.ts]`（紅燈），且只有這一個環 |
| 不得減少比對內容 | 通過 | 逐項比對改前改後的測試名單：少 0 項、狀態改變 0 項；沒有任何 `vi.mock("pixi.js")`；`pixi.js` 沒有子路徑匯入，不會有雙實例 |

預先打包確實生效：`client/node_modules/.vite/vitest/<hash>/deps_ssr` 產生 5.6 MB 的打包結果。

## 對照時間

同一棵樹（HEAD）、同一批交替；改前用基準 commit 的 `vite.config.ts`，改後用新設定，**兩邊唯一的差別是預先打包**。各先暖機一次不計（改前 66.4 秒、改後 57.5 秒）。

| 次 | 改前 wall | 項數 | 改後 wall | 項數 |
|---|---|---|---|---|
| 1 | 65.1 s | 3315 | 56.1 s | 3315 |
| 2 | 65.6 s | 3315 | 47.3 s | 3315 |
| 3 | 55.8 s | 3315 | 48.5 s | 3315 |
| 平均 | **62.2 s** | | **50.6 s** | |

全量 wall 快約 19%（−11.6 秒）。

| 指標（3 次平均） | 改前 | 改後 |
|---|---|---|
| 除 `badgeCapsule` 外全部測試檔跑完的時間點 | 40.1 s | 22.3 s |
| `badgeCapsule.test.ts` 測試本體 | 48.1 s | 38.5 s |
| import 佔累計時間 | 約 75% | 約 48% |
| import 累計（由百分比與測試本體總和推算，約略值） | 約 394 s | 約 114 s |

**盤點的 27～32 秒沒有重現。** 全量 wall 的下限是 `badgeCapsule.test.ts`：每一輪都是它最後結束，本體 36～51 秒，開跑點約 9～13 秒。其他檔案的完成點從 40 秒降到 22 秒，量級接近盤點，但被這一檔擋住，反映不到全量 wall。拆這檔是本階段範圍外。

### 作廢的第一輪量測

第一輪我把改前版本解開到 `.perf-before/` 另一個目錄，改前 77.1 秒、改後 65.5 秒。這組**不公平，不要引用**：同一批原始碼掃描測試在 `.perf-before/` 約 345 ms，在同一棵樹上切換設定則兩邊都約 40 ms，代表差異來自目錄位置，不是 V1（位置為何變慢沒有深查）。上表是修正後重量的結果。

建置比對與測試名單比對的基準仍取自這個目錄，它們比對的是內容，不受執行速度影響。改前的 3301 項也來自那裡。

## V1 變快的原因

1. **import 變快（主因）**：測試環境下 `pixi.js` 預設走 Node 原生 ESM，每個測試檔都要各自載入 pixi 的數百個小模組。預先打包後只讀打包好的檔案，import 累計約少七成。
2. **測試本體變快（盤點的疑點）**：同一棵樹上測試本體總和 115.0 → 109.7 秒，少 5.3 秒。
   - 減少幾乎全來自 `badgeCapsule.test.ts`（−9.6 秒）；其餘檔案加總反而多約 4 秒，屬雜訊範圍。
   - 檔案第一項測試沒有變快（12.9 → 14.1 秒），所以不是 import 成本被算進測試本體。
   - **推論**：`badgeCapsule` 是吃 CPU 的長測試，其他 worker 提早結束後，它與別的工作爭搶的時間變短。把它單獨跑時改前 48.8／32.2 秒、改後 42.7／54.7 秒，沒看到變快，與此推論相符；但樣本少、雜訊大，尚未嚴格證實。
3. **不是因為少測或 mock 改變**：見驗收表的名單比對與 mock 檢查。

盤點時另一組「測試本體變快」的現象，可能也受目錄位置或同時負載影響，這點無法回溯確認。

## S3 的行為一致

函式本體逐字搬移，雜湊快照原樣通過。S3 對時間的影響沒有單獨量（對照表兩邊都含 S3）。

## 環檢查的規則

- 算入：一般 `import`、`export … from`、副作用 import，以及 `import { type A } from "x"`（專案開 `verbatimModuleSyntax`，這種寫法編譯後會留下 `import {} from "x"`）。
- 不算：`import type`、`export type`、型別位置的 `import("x")`、註解與字串內容。
- 範圍：`client/src` 的 .ts／.tsx，不含 `*.test.*`、`.d.ts`、`src/test/`。
- 有防空跑測試（模組數 > 200、已知真實相依必須出現）與工具本身的單元測試。

## 過程紀錄

- 這個 worktree 建立時實際在 `9bc45ad3`，不是指定的 `4d4948c8`，規格檔也不存在。確認 `9bc45ad3` 是 `4d4948c8` 的祖先、差 4 個 commit 都沒動 `client/`、工作區乾淨且無自己的 commit 後，用 `git reset --keep 4d4948c8` 把本 worktree 的分支移到指定基準。沒有動 main 或其他分支。
- 全量 vitest 跑的次數多於規格的各 3 次：改前改後各有冷啟動 1 次、作廢輪 4 次、公平輪 4 次（含暖機）。多跑是為了排除量測偏差。
- 暫存的 `.perf-before/` 已刪除。

## 待 PM 決定

1. `badgeCapsule.test.ts` 是全量 wall 的下限（本體 36～51 秒）。要再明顯縮短全量時間得拆這檔或減少組合，本階段範圍外，是否另排一段？
2. 盤點的 27～32 秒沒有重現（實測 62.2 → 50.6 秒，其他檔案的完成點 40.1 → 22.3 秒）。驗收條件只要求附對照，所以依規格算過；若預期達到盤點數字，需要先處理第 1 點。
3. `paperdoll` 保留 `itemColors` 的轉出口，既有約 10 個 importer（多數是測試檔）不用動（最保守的搬移）。是否之後統一改成從 `itemColors` 匯入？
4. 規格的「不依賴外部套件」解讀為不新增相依：環檢查用專案既有的 `typescript`（`sourceScan` 已在用），沒有引入 madge 之類工具。
5. 環檢查比規格嚴格：`import { type A }` 與動態 `import()` 也算。目前兩種算法都是 0 個環，若日後嫌太嚴可以放寬。
6. 環檢查累計約 5 秒測試本體（用 TS 剖析全部原始碼建圖兩次以上）。不影響全量 wall，因為全量被 `badgeCapsule` 擋住。
