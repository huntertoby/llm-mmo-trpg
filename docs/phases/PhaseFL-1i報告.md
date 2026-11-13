# Phase FL-1i 報告｜營火「轉型除外」、「強度」不可拆、單位資訊卡層數計量

依據：`docs/玩法PM交接.md` 4.1.8 第 2 點（FL-1h 待決 7）、`docs/art/RR-2驗收.md` F-1（1600 下固定區斷成「重算強／度」）、`docs/art/RG-4驗收.md` 末節「KW-3 待決 3」。worktree 開工前 fast-forward 到 main `ff5b10d69`。

## 1. Commit

| commit | 內容 |
|---|---|
| `23dc44648` | 營火（與成長面板「整備」）重閃說明行加「（轉型除外）」，`pnl4Followups.test.ts` 跟著改 |
| `582104544` | `FLASH_NO_BREAK_WORDS` 加「強度」，下固定區那句話（`.fc-say-line`）開 `nobr`；`fl1hFlashWords.test.ts` 加 2 條 |
| `9e851bdac` | 截圖 `docs/art/shots/FL-1i/`（10 張） |
| （本報告與上手筆記） | `docs/phases/PhaseFL-1i報告.md`、`docs/dev/上手-前端戰鬥畫面與動畫.md` 第 164 點與測試表 |

## 2. 開工前 grep（有沒有人做過）

- 第 1 項：`新選項整招不會比現在弱` 只在 `client/src/run/CampfireSkillCare.tsx:63`（`reflashNoteText`）與 `world/pnl4Followups.test.ts:103`，都還沒有「轉型除外」。後端、`content/`、CLI 沒有這句。**沒做過**。
- 第 2 項：`FLASH_NO_BREAK_WORDS = ["雙手槍"]`，`nobr` 只在 `.fc-when` 開。**沒做過**。
- 第 3 項：**RG-5 已經做了**（commit `d8c5a2b89`，`ui/UnitInfo.tsx` 第 252～258 行 `hasGauge(k) ? <StackPips …/> : <StackBadge …/>`，`owned` 照現行；測試 `ui/unitInfoStacks.test.ts`；`RG-5報告` 4.4）。`RG-5驗收.md` 沒有驗到這一項，所以這次**只核對**、補截圖與浮動卡實測，程式沒改。

## 3. 逐條驗收

| # | 項目 | 做法 | 證據 |
|---|---|---|---|
| 1 | 營火說明行「轉型除外」 | `reflashNoteText` 改成「…新選項整招不會比現在弱（轉型除外）；標 ▼ 的是換掉後變小的地方。」同一個函式也用在大世界「成長與技能 → 整備 → 重閃」，兩處一起變 | `pnl4Followups.test.ts`「重閃說明字不變」改字後通過；截圖 01（成長面板 1600）、02（800）、03（一輪營火 1600）。CDP 讀到的字三張都逐字相同 |
| 2 | 「強度」不可拆 | `FLASH_NO_BREAK_WORDS = ["雙手槍", "強度"]`；`RunFlashPending` 下固定區 `<TermText text={sayText(picked)} terms={terms} nobr />`（所有卡都開；不可拆詞只有這兩個，對一般卡無害）。條件括號 `.fc-when` 照舊開 | vitest 2 條（`noBreakRuns(FLASH_TRANSFORM_FOOT_ZH)` 切出「強度」、`TermText nobr` 包成 `.fc-nobr`）。逐字量行（`Range.getClientRects`）：**1600** `reflash_major` 轉型卡＝「…轉型後照新種類重算／強度，不跟原本比。」（原本 FL-1h/04 是「重算強／度」）；**800**＝「…敵人踩上去時／才發動。轉型後照新種類重算強度，不跟原本比。」；**一輪 800** `transform` 組＝「…轉型後／照新種類重算強度，不跟原本比。」三種都不在詞中斷。截圖 04、05、06 |
| 3 | 單位資訊卡層數計量 | 只核對（見第 2 節） | `unitInfoStacks.test.ts`、`qIconKW3.test.ts` 通過；開發頁 `rg5-shield-scene.html?mode=d`（正式 `UnitInfo` 元件）量到計量 `連擊 60×22`、`怒氣 53×22`、`專注 46×22`、`氣 46×22`，和 HUD 同一個 `StackPips`／`gaugeBox`（不是縮小版）；靜電照舊 `StackBadge`；0 層不列；`.hud-icons` 已是 `align-items: center`。截圖 07（1600）、08（800） |

### 浮動卡實測（第 3 項的計量說明，`StackTip`；1600×900 與 800×600）

開發頁 `?mode=d`，滑到「怒氣」計量：80 ms 還沒開 → 680 ms 時已開一張、在視窗內、portal 到 `body`（位置在計量下方：上方空間不夠，翻轉）→ 經橋接區滑進卡仍在 → 卡內捲到底（173／173，不用捲）→ 點一下釘住（`pinned`），滑走仍在 → Esc 關掉（0 張）。兩種寬都一樣。截圖 09、10（釘住狀態）。

第 1、2 項沒有動到浮動卡。

## 4. 快照預測

- CLI 快照：**預測 0 鍵**（改的字只在前端 `client/src/`；後端、`content/`、CLI 都沒有這句）。沒跑 slow 測試。
- 引擎、後端、API 型別都沒改；`ruff`／`mypy`／`lint-imports` 沒有 Python 改動可查，沒跑。

## 5. 檢查

- `corepack pnpm -C client typecheck`：0
- `corepack pnpm -C client exec vitest run src/run/fl1hFlashWords.test.ts src/world/pnl4Followups.test.ts src/run/rr2ReflashWeaker.test.ts src/run/fl1bFlashChoice.test.ts src/run/fl1gFlashFix.test.ts src/run/lf3FlashLlmText.test.ts src/ui/unitInfoStacks.test.ts src/render/qIcon/qIconKW3.test.ts`：8 檔 74 項全過
- 沒跑整包 vitest、build、`scripts/check.py`（照派工）。

## 6. 截圖（`docs/art/shots/FL-1i/`，10 張、jpg 80、最大 97 KB、DPR 1；**全部是開發頁**）

無頭 Chrome（`--headless=new --disable-gpu --mute-audio`，除錯埠 9392 只綁 127.0.0.1）、CDP `setDeviceMetricsOverride` `deviceScaleFactor 1`（量到 `devicePixelRatio = 1`），自己的 vite 9391，網址帶 `?mute=1`。收尾用 PID 關掉 vite 與 Chrome，兩個埠都沒在聽。

| 檔 | 內容 |
|---|---|
| `01-campfire-note-1600.jpg` | `panel-gallery.html?case=lv4&tab=care&fold=reflash#growth`：成長面板整備的重閃說明行帶「（轉型除外）」 |
| `02-campfire-note-800.jpg` | 同上 800×600 |
| `03-run-campfire-note-1600.jpg` | `panel-gallery.html#campfire`：一輪營火畫面同一行 |
| `04-transform-foot-1600.jpg` | `flash-choice.html?set=reflash_major&pick=3`：轉型卡下固定區「…重算／強度，不跟原本比。」（對照 `FL-1h/04` 的「重算強／度」） |
| `05-transform-foot-800.jpg` | 同上 800×600 |
| `06-transform-foot-run-800.jpg` | `flash-choice.html?set=transform&pick=3&mode=run`：一輪版 800 |
| `07-unitcard-stacks-1600.jpg` | `rg5-shield-scene.html?mode=d&w=1600`：資訊卡連擊 3、專注 1、怒氣滿、氣 2 是 HUD 計量，靜電照舊 |
| `08-unitcard-stacks-800.jpg` | 同上 800 |
| `09-unitcard-gauge-tip-1600.jpg` | 資訊卡「怒氣」計量的說明卡釘住（1600） |
| `10-unitcard-gauge-tip-800.jpg` | 同上 800 |

**實機未看**：三項都只在開發頁看（營火要跑一輪、轉型重閃要走到大變化格、資訊卡要敵人身上有計量層數）；開發頁走的是正式元件（`WorldGrowth`、`RunCampfire`、`FlashPendingPanel`、`UnitInfo`）與伺服器產生的夾具。

## 7. 待 PM 決定

1. **第 3 項 RG-5 已做**：這次只核對＋補截圖。若美術 PM 要複驗，看 `FL-1i/07～10`。
2. **下固定區對所有卡都開了 `nobr`**（不只轉型卡）。目前不可拆詞只有「雙手槍」「強度」，對一般卡只會讓這兩個詞不拆。若只想轉型卡開，改成 `nobr={picked.transform}` 一行。
3. 順手看到（不在範圍、沒改）：1600 `reflash_major` 第 3 張卡（非轉型）的下固定區斷成「1d4 火焰傷／害（本回合…）」，第 1 張卡斷在「燃燒少 1 ／回合」。若要處理，可把「傷害」加進不可拆詞，或數字＋單位黏起來（類似 `KeepNum`）；需要美術 PM 先說要不要。
