# Phase BS-2b 完成報告｜BS-2 美術驗收的必修 1＋可修 1、2

> 規格：派工 prompt；驗收紀錄 `docs/art/BS-2驗收.md`（必修 1、可修 1、可修 2）；`docs/phases/PhaseBS-2報告.md`。
> 基準：開工時 `git merge --ff-only main` 到 `efae4edb`。
> 只改前端戰鬥紀錄與預覽標籤；沒碰後端與 `content/`；沒重產雜湊或快照；沒跑 `scripts/check.py`。不做可修 4（「兩下都中」改條件名，等玩法 PM 定字）。

## 1. 做了什麼

| 項目 | 做法 | 完成 |
|---|---|---|
| 必修 1：紀錄面板的標籤行主字被擠成直排 | 採驗收建議的 (a)＋(b) 合併：`BattleLog.tsx` 的 `LogText` 在畫標籤的行加 `has-no-turn`；`battle-log.css` 新增 `.log-line.has-no-turn { flex-wrap: wrap }`、主字 `flex: 1 1 0; min-width: 6em`、標籤 `order: 1; margin-left: 16px`。結果：主字吃滿第一行（含「詳」鈕），標籤掉到第二行、左緣對齊主字。浮動提示（`.log-toast`，單行省略號）不受影響。 | 是 |
| 可修 1：隱蔽出手改實線 | 刪掉 `.no-turn-tag[data-no-turn="concealed"] { border-style: dashed }`；兩種都是紫色 1px 實線細框＋淡底，靠字區分（註解寫明 3.7 的虛線＝本場不成立）。 | 是 |
| 可修 2：預覽列的標籤不掛說明卡 | `ActionPanel.tsx` 的 `NoTurnLine` 拿掉 `<Hint>` 與 `tabIndex`，只留 `<span class="no-turn-tag">`；不再 import `NO_TURN_HINT_ZH`。紀錄標籤（掛說明卡）與浮動提示（不掛）照舊。 | 是 |
| 上手筆記 | `docs/dev/上手-前端戰鬥畫面與動畫.md` 第 135 點改「預覽不掛說明卡」；新增 139～141（窄欄 flex 不縮標籤會擠直排、虛線＝不成立、實拍紀錄面板的注入法與無頭 Chrome 真 1 倍）；第五節測試表補 BS-2b。 | 是 |

## 2. 實機量測（真 1 倍，DPR 1）

無頭 Chrome（`--headless=new --mute-audio`，除錯埠 9473）＋CDP，伺服器 `trpg serve --port 9472`（`TRPG_DEV_ROUTES=1`、存檔在暫存區），頁面 `/?dev=1&mute=1&anim=0.1`。量所有 `.log-line.has-no-turn`（31 行）：

| 視窗 | 行寬 | 主字最窄 | 主字最高 | 標籤都在主字下方 | 標籤都在行內 | 框線 |
|---|---|---|---|---|---|---|
| 800×600 | 166～189 | **120px**（修前 13px） | 52px（3 行字） | 是 | 是 | 全 solid |
| 1600×900 | 188～211 | **137px**（修前 26px） | 52px | 是 | 是 | 全 solid |

三種字都量到：「隱蔽出手（不會轉身）」122px、「背刺・無聲（不會轉身）」133px、「背刺・隱蔽出手（不會轉身）」。

**資料注入（註明）**：截圖的「不會轉身」是包 `window.fetch` 注入的：遞迴走 JSON 回應，把每個 `attack_rolled` 輪流設 `no_turn: "concealed"`／`"silent"`（silent 那筆另設 `backstab: 2`），`text` 尾巴補「［…（不會轉身）］」。所以截圖裡是敵人（盜賊弓手）帶著這兩種標籤；版面與真資料相同（前端只看 `no_turn`／`backstab`）。步驟：選「開闊平原」、匕首＋兩個關鍵字、開始戰鬥，反覆按「結束回合」＋「跳到結尾」，到玩家回合時打開紀錄、把「無聲」與「隱蔽出手」相鄰的兩行捲進畫面，`Emulation.setDeviceMetricsOverride` 設尺寸後 `Page.captureScreenshot`。

## 3. 截圖（`docs/art/shots/bs2b/`，jpg 80，都 ≤ 300 KB）

| 檔 | 內容 |
|---|---|
| `bs2b_log_800.jpg` | 800×600 全畫面，紀錄打開，「背刺・無聲」「隱蔽出手」各一行 |
| `bs2b_log_800_x3.jpg` | 同上紀錄面板，最近鄰放大 3 倍（看實線框與第二行對齊） |
| `bs2b_log_1600.jpg` | 1600×900 全畫面，紀錄打開，兩種標籤各一行 |
| `bs2b_log_1600_x3.jpg` | 同上紀錄面板，最近鄰放大 3 倍 |

## 4. 測試

新增（`client/src/battle/bs2SilentStrike.test.ts` 的 `describe("BS-2b：美術驗收必修 1、可修 1")`）：
- 結構：`BattleLog` 靜態渲染帶 `no_turn` 的行有 `has-no-turn`，DOM 裡主字在標籤前；沒有 `no_turn` 的行沒有這個 class。
- CSS：`.log-line.has-no-turn` 有 `flex-wrap: wrap`；`.log-text` 有 `flex: 1 1 0` 與 `min-width: 6em`；標籤 `order: 1`。
- 實線：`.no-turn-tag` 是 `border: 1px solid`，任何 `.no-turn-tag…` 規則都沒有 `dashed`。

既有測試改動（舊 → 新）：
1. 檔頭註解第 1 條：「（兩種各自的字＋說明卡）」→「（兩種各自的字；說明卡只在紀錄，BS-2b 起預覽不掛）」。
2. `it("預覽列：標籤樣式＋說明卡（種類寫在 data-no-turn）")` → `it("預覽列：只畫標籤樣式（種類寫在 data-no-turn）；BS-2b 拿掉滑鼠打不開的說明卡")`；斷言從 `toContain('class="preview-no-turn" data-no-turn="silent"')`＋`toContain('class="no-turn-tag"')` → 整段 `toBe('<ul><li class="preview-no-turn" data-no-turn="silent"><span class="no-turn-tag">背刺・無聲（不會轉身）：A 盜賊</span></li></ul>')`，另加 `ActionPanel.tsx` 不含 `NO_TURN_HINT_ZH`。
3. `「紀錄標籤…」`：`toContain("<NoTurnTag kind={line.noTurn.kind}")` → `toContain("<NoTurnTag kind={tag.kind}")`（`LogText` 先算 `tag` 變數）。

## 5. 檢查結束碼

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `vitest run src/battle/bs2SilentStrike.test.ts src/ui`（46 檔、676 項） | 0 |
| `corepack pnpm -C client test --run`（333 檔、4311 項全過） | 0 |
| `corepack pnpm -C client build` | 0 |

收尾：伺服器（9472）、無頭 Chrome（9473）、內建預覽分頁都已關，兩個埠都沒在聽。

## 6. 待 PM 決定

1. **800×600 時紀錄面板上緣被左上主角卡蓋住約 100px**（`bs2b_log_800.jpg` 可見「戰鬥紀錄」標題列在主角卡下面）：既有版面，不是這段造成的，也不在範圍內，沒改。修完必修 1 後帶標籤的行變成 3 行高（原本是更高的直排），面板可見的行數不受影響。要不要另排一段處理由 PM 定。
2. 帶標籤的行在寬欄（≥ 約 250px）時，標籤會留在第一行「詳」鈕後面而不是換行；目前所有視窗的紀錄面板都 ≤ 211px，實際一律在第二行。保守做法沒有強制換行。

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（無衝突）。全量於合併後跑。待決 1（800×600 紀錄面板上緣被主角卡蓋住約 100px，既有版面）交美術 PM 判斷是否另排；2（面板 ≥ 250px 時標籤留第一行）接受。
