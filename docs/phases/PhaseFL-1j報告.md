# Phase FL-1j 報告｜閃現、重閃、成長面板的斷行

依據：`docs/art/FL-1b驗收.md` 末節「FL-1i 複驗」可修 1、2（FL-1i 待決 3）、`docs/phases/PhaseFL-1i報告.md` 待決 3、`docs/phases/PhaseFL-1h報告.md`。worktree 開工時就在 main `c149b1793`（不用 fast-forward）。

## 1. Commit

| commit | 內容 |
|---|---|
| `9b0deac52` | `FLASH_NO_BREAK_WORDS` 加「傷害」「轉型」；數字＋單位通用黏合 `numberUnitRuns`（`noBreakRuns` 第二步）；`NoBreakText` 匯出，成長面板／營火的藍字經過它；新測試 `run/fl1jFlashWrap.test.ts`，改 `fl1hFlashWords.test.ts`、`flash.test.ts` 的期望 |
| `cde998932` | 重閃鈕裡的藍字「可以重閃第 3 格轉型」整段不換行（`.fc-nobr`），全形空白移到 span 外 |
| `0a77f4a6c` | 截圖 `docs/art/shots/FL-1j/`（10 張） |
| （本報告與上手筆記） | `docs/phases/PhaseFL-1j報告.md`、`docs/dev/上手-前端戰鬥畫面與動畫.md` 第 165 點與測試表 |

## 2. 做法

- **不可拆詞**：`FLASH_NO_BREAK_WORDS = ["雙手槍", "強度", "傷害", "轉型"]`。
- **數字＋單位（通用規則，不逐字列舉）**：`flashChoice.numberUnitRuns(text)`——數字（含小數「1.15」、骰子「1d4」、正負號、％／‰）＋最多一個空白＋後面的單位（`unitAfterNumber`：英文字母整串如「AP」，否則前 2 個中文字）包成不斷行；**數字前面緊貼的一個中文字（可隔一個空白）也一起黏**（「少 1 回合」「第 3 格」「等 5 回合」），避免數字落到行首或「第／3」。英文或數字中間的數字不拆。`noBreakRuns` 先切不可拆詞，剩下的純文字再跑這一步，所以條件括號（`.fc-when`）與下固定區一句話（`.fc-say-line`）都自動套到。
  - 試過 `Intl.Segmenter` 找單位：Node 的 ICU 把「回合，」切成「回／合」，各瀏覽器詞典也不同，所以改成固定取 2 個中文字（多黏一字如「5 格外」「2d6 變成」只少一個斷點，無害）。
  - CSS 只用既有的 `.fc-nobr { white-space: nowrap }`，Chrome、Edge、Firefox、Safari 都支援，不需要降級。
- **成長面板／營火藍字**：`CampfireSkillCare` 重閃鈕裡的「可以重閃第 3 格轉型」包成 `.skill-flash-transform.small.fc-nobr`（字固定、約 108px，一輪 376 的鈕寬 242 也放得下），放不下就整段換到下一行；全形空白移到 span 外，換行時不會變成行首縮排。技能卡的閃現資訊（`ui/SkillFlashInfo.tsx`，含 `Hint`）的同一句改經 `NoBreakText`（「第 3 格」「轉型」不拆；那裡是 flex 項目，沒加整段 nowrap，量到各寬度都是一行）。

## 3. 逐條驗收

| # | 項目 | 證據 |
|---|---|---|
| 1 | 「傷害」「轉型」加進不可拆詞 | vitest `fl1jFlashWrap.test.ts` (1)；量行見第 4 節：1600 第 3 張卡從「火焰傷／害」變「火焰／傷害」；截圖 02、03、06 |
| 2 | 數字和單位不拆開（通用規則） | vitest (2)：`unitAfterNumber`、`numberUnitRuns` 單元；**夾具 7 組全部選項的一句話**都檢查「不斷行段以外，數字後面不直接接中文或英文單位」；`reflash_major` 兩張非轉型卡的 HTML 有 `<span class="fc-nobr">少 1 回合</span>`。量行：1600 第 1 張卡從「燃燒少 1 ／回合」變「燃燒／少 1 回合」；截圖 01、04、05 |
| 3 | 成長面板藍字不斷成「轉／型」 | vitest (3)；量行：成長面板 1600／800、營火 408／376 都是「…加深　／可以重閃第 3 格轉型」（整段換行），營火 1600／800 一行放得下；截圖 07、08、09 |
| 4 | 1600 重閃大變化非轉型卡不再出現「火焰傷／害」「燃燒少 1 ／回合」 | 第 4 節 1600 列：兩張卡都沒有 |
| 5 | 窄欄也量一次 | 第 4 節（大世界 1600／800、一輪 800／408／376） |

## 4. 各寬度斷點（`flash-choice.html?set=reflash_major&pick=N`，下固定區 `.fc-say-line`，逐字 `Range.getClientRects` 量行，「／」是換行）

`pick` 照畫面順序：0＝敵人被標記時（非轉型）、1＝專精點燃（和現在一樣）、2＝放過雷電技能（非轉型）、3＝轉型陷阱。

| 寬 | pick | 改前（`c149b1793`） | 改後 |
|---|---|---|---|
| 大世界 1600 | 0 | …燃燒少 1 **／回合**，多了… | …1d12，燃燒**／少 1 回合**，多了…（一行半） |
| 大世界 1600 | 2 | …1d4 火焰傷**／害**（本回合… | …1d4 火焰**／傷害**（本回合… |
| 大世界 1600 | 3 | …重算／強度，不跟原本比。 | 同左 |
| 大世界 800 | 0 | …（原本 4），／傷害…1d4 火焰傷害／（目標… | 同左 |
| 大世界 800 | 2 | …燃燒少 1 回**／合**，…帶「雷電」標籤的技**／能**時才有 | …燃燒**／少 1 回合**，…帶「雷電」標**／籤**的技能時才有 |
| 大世界 800 | 3 | …敵人踩上去時／才發動。… | 同左 |
| 一輪 800 | 0／1／3 | （一行或在句讀換行） | 同左 |
| 一輪 800 | 2 | …傷害（本／回合已施放過… | 同左（見待決 2） |
| 一輪 408 | 0 | 用過之後要等 5 **／回合**…變成 ／1d12…1d4 火**／焰傷害**… | 用過之後要**／等 5 回合**…變成**／ 1d12**…多了額外傷害：**／1d4 火焰傷害**… |
| 一輪 408 | 2 | 傷害從 ／2d6…多了額外傷**／害**：…「雷電」／標籤 | 傷害**／從 2d6 變成 1d12**…多了額外**／傷害**：…「雷**／電**」標籤（見待決 2） |
| 一輪 408 | 3 | …轉型後照／新種類重算強度… | 同左 |
| 一輪 376 | 0 | …傷害從 ／2d6…多了額**／外傷害**… | …傷害**／從 2d6 變成 1d12**…多了**／額外傷害**… |
| 一輪 376 | 2 | 傷**／害**從 2d6…多**／了**額外傷害…已施**／放過**… | 一行到「少 1 回合，」**／多了額外傷害…（本回合已／施放過**… |
| 一輪 376 | 3 | …不跟原**／本比**。 | 同左（見待決 2） |

一輪 408／376 的下固定區一句話只顯示 2 行（`line-clamp: 2`，轉型卡 4 行），量的是整句排版的斷點。pick=1 各寬度改前改後相同（「多持續 1 回合」本來就沒斷；376 的「點／燃」見待決 2）。

成長面板／營火的重閃鈕（`.reflash-slots button` 第 3 次那顆）：

| 頁 | 改前（美術 FL-1i/01） | 改後 |
|---|---|---|
| 成長面板 1600 | …加深　可以重閃第 3 格轉**／型** | …加深　**／可以重閃第 3 格轉型** |
| 成長面板 800 | （藍字整段換行） | …加深　／可以重閃第 3 格轉型 |
| 營火 1600／800 | 一行 | 一行 |
| 營火 408／376 | — | …加深　／可以重閃第 3 格轉型 |

技能卡閃現資訊（`SkillFlashInfo`）的同一句在各寬度都是一行（寬 108）。

## 5. 快照預測與檢查

- CLI 快照：**預測 0 鍵**（只改 `client/src/` 的前端字處理；後端、`content/`、技能說明、CLI 都沒動）。沒跑 slow 測試。引擎、後端、API 型別都沒改。
- `corepack pnpm -C client typecheck`：0
- `corepack pnpm -C client exec vitest run src/run/ src/world/pnl4Followups.test.ts src/world/pnl2Growth.test.ts src/test/importCycles.test.ts src/test/sourceScan.test.ts src/ui/floatCardRule.test.ts`：25 檔 246 項全過（第 2 個 commit 後再跑 `fl1jFlashWrap`、`flash`、`pnl4Followups`、`pnl2Growth` 4 檔 65 項全過）
- 沒跑整包 vitest、build、`scripts/check.py`（照派工）。
- 浮動卡：沒有新增或改動彈出層。`SkillFlashInfo` 的 `Hint` 子元素仍是同一個 `<span>`（裡面多了不斷行的小段），觸發方式不變。

## 6. 截圖（`docs/art/shots/FL-1j/`，10 張、jpg 80、最大 81 KB、DPR 1；**全部是開發頁**）

無頭 Chrome（`--headless=new --disable-gpu --mute-audio`，除錯埠 9472 只綁 127.0.0.1）＋CDP `setDeviceMetricsOverride` `deviceScaleFactor 1`（量到 `devicePixelRatio = 1`），自己的 vite 9471，網址帶 `?mute=1`。收尾用 PID 關掉 vite 與 Chrome（含子程序），兩個埠都沒在聽。

| 檔 | 內容 |
|---|---|
| `01-reflash-burn-1600.jpg` | `flash-choice.html?set=reflash_major&mode=world&pick=0` 1600：下固定區「燃燒／少 1 回合」 |
| `02-reflash-fire-dmg-1600.jpg` | 同組 `pick=2` 1600：「1d4 火焰／傷害」 |
| `03-reflash-fire-dmg-800.jpg` | 同上 800×600：「燃燒／少 1 回合」「標／籤」 |
| `04-reflash-burn-run-800.jpg` | `mode=run&pick=0` 800 |
| `05-reflash-burn-run-408.jpg` | `mode=run&pick=0` 408（一輪窄欄）：「用過之後要／等 5 回合」 |
| `06-reflash-fire-dmg-run-376.jpg` | `mode=run&pick=2` 376 |
| `07-growth-transform-hint-1600.jpg` | `panel-gallery.html?case=lv4&tab=care&fold=reflash#growth` 1600：第 3 次重閃鈕的藍字整段在第二行（對照 FL-1i/01 的「轉／型」） |
| `08-growth-transform-hint-800.jpg` | 同上 800×600 |
| `09-campfire-transform-hint-376.jpg` | `panel-gallery.html#campfire` 376（捲到重閃區）：鈕裡藍字整段換行、卡上一行 |
| `10-transform-foot-run-376.jpg` | `reflash_major&mode=run&pick=3` 376：轉型卡 |

**實機未看**：三項都只在開發頁看（重閃大變化格要跑一輪到第 3 格、成長面板要升階）；開發頁走的是正式元件（`FlashPendingPanel`、`WorldGrowth`、`RunCampfire`）與伺服器產生的夾具。

## 7. 待 PM 決定

1. **數字前面多黏一個中文字**（「少 1 回合」「第 3 格」「等 5 回合」「本 2」）：美術只要求數字和單位不拆；多黏前一字是為了不出現「第／3 格」、數字落到行首。若不要，`numberUnitRuns` 的 `lead` 拿掉一行（測試跟著改）。
2. **其他一般詞仍會在字中間斷**（不在這次範圍、沒改）：一輪 800「（本／回合已施放過」、408「「雷／電」標籤」、376「點／燃」「不跟原／本比」「才發／動」。若要處理，比較通用的做法是改用切詞（`Intl.Segmenter`）決定斷點，或再往不可拆詞清單加詞；需要美術 PM 先說要不要、做到哪裡。
3. 單位固定取 2 個中文字（不切詞），偶爾多黏一個字（「5 格外」「2d6 變成」）；只少一個斷點，沒看到超出卡外。
4. 技能卡閃現資訊（`SkillFlashInfo`）的藍字只經 `NoBreakText`（「第 3 格」「轉型」不拆），沒有整段 nowrap（flex 項目，避免窄卡超出）；目前各寬度都是一行。
