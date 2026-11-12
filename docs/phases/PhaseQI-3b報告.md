# Phase QI-3b 報告：Q 版狀態圖示｜接線（paintStatusIcon、控制類框底色、角落級數、statusTile 部件圓片、實機截圖）

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-3計畫.md`（第 0.0 節定稿；第 0 節 1～10 點照「建議」欄；0.0 第 7 點 `statusTile` 併入本段；第 6 節 B1～B6、第 7 節 T-B1～T-B8、第 8 節）。
> 起點 main（`git merge --ff-only main`，含 `ecbf8964` QI-2c 合併、`e03b8d76` QI-3a 合併）。未 push。
> 檔案邊界：**沒有改** `qIcon/parts.ts`、`qIcon/skills.ts`、`qIcon/weapons.ts`、`qIcon/core.ts`、`render/skillParts.ts`（開發 PM 中途追加）、`content/`、`src/trpg/`（`git diff main..HEAD --stat` 為證：只動 `render/statusIcon.ts`、`render/skillIcon.ts`、`ui/statusCard.ts`、`dev/statusGallery.ts`、`client/dev/status-gallery.html`、測試與 fixture、文件、截圖）。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| B1 `paintStatusIcon` | `render/statusIcon.ts`：`paintStatusIcon(ctx, id, cx, cy, size, unitPx = 1, res = ICON_RES)` 改呼叫 `qIcon/status.ts` 的 `paint`（框 → 深底 → 類別底色 → 框線 → `blit` 圖樣；不認得的畫名稱第一個字、米白）。舊呼叫照樣成立。檔頭註解改寫；`glyphColor`／`CTRL_COLOR`／`OWN_COLOR`／`POL_COLOR`／`GLYPH`／`drawGlyph` 保留、值不改（註解寫明留給誰）。拿掉沒用的 `DPR` | `089c6382` |
| B2 頭頂 | `statusIconCanvas(id, size, res = ICON_RES)`：`qCanvasAvailable()` 才畫（沒有畫布回 null，同以前沒 DOM 的行為）、`blank(round(size × res))`、`scale(res)`、框 `size − 2`、`unitPx` 1。`statusIconKey(id, size, res = ICON_RES)` 加 `res`；`lookKey` 的「第一個字」改看 Q 版 `entry(id) === null`。`unitSprite.rowIconTexture` 沒改（鍵跟著 `statusIconKey` 走） | `089c6382` |
| B3 狀態卡 | `render/skillIcon.ts`：`statusIconTile(id).draw(ctx, u = 0.2, res = ICON_RES)` → `paintStatusIcon(ctx, id, 50, 50, 84, u, res)`；`tileKey(t, px, res = ICON_RES)` ＝ `px|res|id`、`tileCanvas` 一律用它。新常數 `STATUS_CARD_PX = 20`（沒傳參數時的退回值）。**`AssemblyTile.draw` 的介面**：QI-2c 已經是 `draw(ctx, unitPx?, res?)`，`tileCanvas` 已傳 `px / 100` 與 `res`，所以沒有另加規格寫的 `info?: { px, res }`（同一件事，見待決 1） | `089c6382` |
| 0.0 第 7 點 `statusTile` | `statusTile(id).draw` 改成 Q 版部件圓片 `QP.chip("status", id, 50, 50, 42, { ring: 淡色環, unitPx, res })`（同組裝列的 `chipCanvas` 半徑 42）。第④批 `STATUS` 32 種畫 Q 版；**其他 86 種經 `QP.hooks.status`**（`skillParts.ts` 載入時掛的現行 `statusGlyph()`＋`statusColor`，沒改掛法）。`unitSprite.statusTexture()`（定時炸彈、蓄力徽章，`tileCanvas(statusTile(id), 24)`）程式沒改，畫面跟著換 | `089c6382` |
| B4 角落級數 | `ui/statusCard.ts`：`ELEMENT_STANCE_RE`（`^stance_(physical\|fire\|ice\|lightning\|poison\|wind\|earth\|holy\|shadow)_([1-5])$`）、`CRYSTAL_SURGE_TIER = { crystal_surge: 1, crystal_surge_2: 2 }`、`statusTier(id)`；`statusCorner` 先看級數，再照舊（剩餘回合 → 數值 → 空）。`StatusCardParts.tsx` 沒改 | `089c6382` |
| B5 開發頁 | `dev/statusGallery.ts`：上半預設走遊戲端（狀態卡 `tileCanvas(statusIconTile(id), px, res)`、頭頂 `statusIconCanvas(id, px, res)`，快取畫布複製一張再放）；`&live=0`（或 `&tint=0`）切回 3a 的 `status.ts` 直畫；`&old=1` 改並排 QI-3b 以前的單色線條畫法（開發頁裡的 `legacyPaint`，原樣抄）；新 `&set=corner`（元素架勢 9 × 5 級、晶能兩個、一般回合數／數值／空／控制類，畫成 `StatusBadge` 同款 24px 方塊＋`.stat-corner`，引入 `styles/status-card.css`；`&zoom` 只放大方塊列）；新 `&set=tile`（部件圓片 `statusTile` 24px，標「Q 版／現行」）；下半戰場標題改「遊戲端畫法」 | `07f679d1`、`eeedf8e4` |
| B6 測試 | 新 `render/qi3bWiring.test.ts`（13 項）、`ui/qi3bStatusCorner.test.ts`（3 項）；改寫 `render/statusIcon.test.ts`、`render/qi2cStatusUnchanged.test.ts`（第 3 節）；新基準 `render/fixtures/qi3bStatusBaseline.json` | `7d7c557c` |
| 截圖 | `docs/art/shots/qi3/3b-*` 6 張（第 4 節） | `eeedf8e4` |
| 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md` | 本 commit |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| T-B1 | `paintStatusIcon` 換成 Q 版 | 過：`qi3bWiring.test.ts`「T-B1」3 項——名詞表 118 × {狀態卡 84／0.2 × res 2、1；頭頂 9／1 × res 2、1；52／1} 的假畫布呼叫紀錄（含圖樣畫布）＝直接呼叫 `QT.paint`；預設參數＝`(1, ICON_RES)`；外層 ctx 的 `fillStyle`／`strokeStyle` 不含 `glyphColor(id)`、沒有 `fillText` |
| T-B2 | 頭頂 | 過：`statusIconCanvas(id, 11)` 22×22、`res 1` 11×11，紀錄＝`QT.headCanvas(id, 11, 1, { res })`（118 × 2 res＋預設）；`statusIconKey` 含 res、不同 res 不同快取；沒有畫布回 null；頭頂線寬 1.500、染底 7 個查 `inset 0.5` 那筆 |
| T-B3 | 狀態卡 | 過：`tileCanvas(statusIconTile(id), 20)` 40×40、紀錄＝`QT.cardCanvas(id, 20, 1, { res: 2 })`、含 `lineWidth=7.560`；res 1 同理；spy 確認 `draw` 收到 `(0.2, 2)`、`(0.24, 1)`；直接呼叫 `draw` 退回 `(0.2, ICON_RES)`；`tileKey` 含 res；`TileCanvas` 畫布＝`iconCanvasPx(px)`（掃原始碼） |
| T-B4 | T-C6 改寫 | 過：第 3 節（`statusTile` 那一半也換了——0.0 第 7 點把它併進本段，所以兩半都換新基準） |
| T-B5 | 角落 | 過：`qi3bStatusCorner.test.ts`：名詞表 45 個 `stance_<元素>_<級>` → 級數（`remaining`／`amount` 有值也優先），9 × 5 個 ID 都在快照；`crystal_surge` → 1、`crystal_surge_2` → 2，兩個都在快照；其他 71 個照現行；像但不合樣式的 6 個 ID 不算；`ui/statusCard.test.ts` 原有 3 條沒改、通過 |
| T-B6 | 排序與排版不動 | 過：`statusIcon.test.ts` 的 `sortStatuses`／`statusRowLayout`／`bodyEffects` 斷言沒改一字；`ui/statusBadges.test.ts`、`badgeCapsule.test.ts`、`narrowMapLayout.test.ts`、`summonBadges.test.ts` 沒改、通過 |
| T-B7 | 部件圓片色與召喚物 | 過：`statusColor(id) === glyphColor(id)`（118＋不認得）；`qSummonSpirit.test.ts` 沒改、通過 |
| T-B8 | 既有測試改寫 | 第 3 節 |
| 0.0-7 | `statusTile` | 過：`qi3bWiring.test.ts`「statusTile」：32 種畫 Q 版、其餘 86 種（118 − 32）確實經 `QP.hooks.status`（包一層計數）；`unitSprite.ts` 仍是 `Texture.from(tileCanvas(statusTile(statusId), 24))`；T-C6 改寫第 3 項：每個 `statusTile(id)` 的紀錄＝`QP.chip("status", id, 50, 50, 42, …)`（同 `tileCanvas` 的裁切與縮放） |
| 8.1-2 | 三個結束碼 | 第 2.1 節 |
| 8.1-2 | 快照 | `render/__snapshots__/` 沒變（整包跑完 `git status` 乾淨） |
| 8.1-3 | slow 測試 | `UV_NO_SYNC=1 uv run pytest -q tests/api/test_client_fixtures.py`：4 passed；沒動 Python、`content/` |
| 8.1-5 | `__layoutSmoke` | 自己的 `trpg serve` 8138（正式 build、存檔在暫存區）：1600×900、1040×624、800×600 各 `localStorage.clear()` → `/?dev=1&anim=0.1&mute=1` → `runCase` **全 PASS**（12 項 × 3）；`icons()` 三尺寸全 PASS。另外在注入狀態資料的戰鬥裡（第 4 節「實機」說明）：1600、800 的 `runCase` 全 PASS；`icons()` 1600 **13 個**（含主角狀態列 8 個 `part-tile` 20px）、800 釘住單位資訊後 **22 個**（再加單位資訊 6 個 `part-tile` 與圖釘）全 PASS「全部整數、畫布＝顯示×2」 |
| 8.1-6 | 浮動卡實測 | 第 6 節：4 組全過 |
| 8.1-7 | 截圖 | 6 張（≤ 10），最大 295 KB（第 4 節） |
| 8.1-8 | (b) | 第 4 節 |
| — | 相關測試 | 規格第 9 節 QI-3b 清單＋`qi2cWiring.test.ts`＋新兩檔：19 檔 379 項過 |

### 2.1 交件前三個結束碼

在 `eeedf8e4`（＋本報告）上依序跑（記錄在暫存區）：
- `corepack pnpm -C client typecheck` → **0**
- `corepack pnpm -C client test` → **0**（297 檔、3697 項全過；含 `inkDollSnapshot`、`creaturePose`）
- `corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）
- 跑完 `git status --short` 乾淨。沒跑 `scripts/check.py`。

自己啟動的程序：vite 5285、無頭 Chrome（CDP 5286，`--user-data-dir` 在暫存區、`--mute-audio`）、`trpg serve` 8138。交件前用工作 ID 停掉；vite 的 node 子程序（PID 39900，命令列確認是本 worktree 的 `vite.js --port 5285`）另用 PID 關掉；三個埠都沒在聽、沒有殘留的 Chrome（以 `--user-data-dir` 認）。

## 3. 改寫的既有測試（舊斷言 → 新斷言，不放寬）；快照

**`render/qi2cStatusUnchanged.test.ts`（QI-2c T-C6 → QI-3b T-B4）**
1. 舊：名詞表全部的 `statusTile(24)`、`statusIconTile(20)` 呼叫紀錄雜湊 ＝ 2c 舊基準 `qi2cStatusBaseline.json`（236 組）。
   新：＝ QI-3b 基準 `qi3bStatusBaseline.json`（同一段 `record()`，3b 改完錄一次），**而且 236 組全部 ≠ 舊基準**（舊基準檔留著做這個比對），名詞表數量從 `> 100` 收緊成 `=== 118`。
2. 新增：基準裡相同的雜湊只有「元素架勢同元素 5 級的狀態卡」（9 組各 5 個，需求 2.4 第 3 列「各級同圖」），部件圓片 118 個兩兩不同（舊基準 236 個兩兩不同；新的狀態卡 9 × 4 個本來就該同圖）。
3. 新增：換成什麼——`statusTile` 紀錄＝Q 版部件圓片、`statusIconTile` 紀錄＝`QT.cardCanvas`（3a 已和樣張逐像素 0 差異）。
- **差異只來自本段的證明**：把 `skillIcon.ts`、`statusIcon.ts` 換回 `main` 版（其他不動）、跑 `main` 版的 T-C6 → **通過**（舊基準 236 組全同）；同一狀態下新 T-C6 的第 1、3 項失敗。換回本段的檔後新 T-C6 全過。

**`render/statusIcon.test.ts`（T-B8）**
1. 「每個狀態都有 status_look、圖樣，且畫得出來」：舊＝`GLYPH[id]` 有、`paintStatusIcon` 不丟例外、呼叫 > 5。新＝以上全部保留（`GLYPH` 留給部件圓片），另加 `QT.entry(id)` 不是 null、掛上 Q 版假畫布後外層恰好一次 `drawImage(canvas…)`（圖樣貼進框）、沒有 `fillText`。
2. 「外框依 polarity」：沒改。
3. 「四組原本重複的圖樣已分開」：舊＝6 對的 `GLYPH` 呼叫紀錄不同。新＝保留，另加 6 對的 Q 版 `def` 呼叫紀錄（含 `halo` 另建畫布）不同。**6 對都不同**（護盾家族 `guarded`／`shielded`／`defending` 沒有完全相同的），沒有觸發停止條件。
4. 「圖樣顏色：硬控黃…」：舊斷言全部保留（改名「部件圓片用，狀態框不再用」）；**新增**「框的底色」：118 個 × `paintStatusIcon(…, 84, 0.2, 2)` 的外層 `fillStyle` 順序＝控制類 7 個 `[深底, #d4ac20｜#2f78c8｜#8a4ccc]`、其他 111 個（含纏繞）只有 `[深底]`；`strokeStyle` 只有框色一個；外層不出現 `glyphColor(id)`。
5. 「不認得的 ID…不丟例外」：保留，`glyphColor("new_buff")` 保留；新增：不認得的增益外層只有 `[深底, #f2e6c8]`（不染類別、字米白）。
6. 「不認得的狀態在中間畫名稱第一個字」：保留 `fillText`；新增：寫的是「全」（名稱第一個字），`fillText` 前最後一個 `fillStyle` 是 `#f2e6c8`。
- 其餘（排序、排版、身上特效、框色表）沒改一字。

快照：`render/__snapshots__/` 沒有變動；沒有重產任何既有 fixture（只新增 `qi3bStatusBaseline.json`）。

## 4. 需求第 5 節末 (b)、截圖、實機未看

**(b) 舊畫法還在哪裡**（第 0 節第 6 列：全部保留、值不改）
- `glyphColor`、`CTRL_COLOR`、`OWN_COLOR`、`POL_COLOR`：**狀態框不再用**；`glyphColor` 由 `skillParts.ts` 的 `statusColor()` 呼叫 → 部件圓片 32 種以外的 `hooks.status`（`statusTile`、工坊狀態選項）與 `skillParts` 的舊 `Part.draw`。`CTRL_COLOR`／`OWN_COLOR`／`POL_COLOR` 只經 `glyphColor` 用。
- `GLYPH`、`drawGlyph`：狀態框不再用；`skillParts.ts` 的 `statusGlyph`（→ `hooks.status`）、`KNOWN_PARTS.statuses`、`qSummon.ts`（召喚物頭頂元素小圖）、`qSummonSpirit.test.ts` 還在用。開發頁 `&old=1` 的 `legacyPaint` 也用。

**頭頂圖示的實際螢幕尺寸**（第 0 節第 3 列：接受重新取樣）

| 視窗 | 地圖縮放（`自動 …%`） | `minMark` 倍率 | 頭頂圖示螢幕尺寸 |
|---|---|---|---|
| 1600×900 | 121%（畫布 597 CSS px ÷ 世界寬 10 × 48 ＋ 12 ＝ 492 → 1.213） | 1（9 × 1.213 ＝ 10.9 ≥ 10） | **11 × 1.213 ≈ 13.3 px** |
| 800×600 | 63%（312 ÷ 492 → 0.634） | 10 ÷ (9 × 0.634) ≈ 1.75 | **≈ 12.2 px**（框裡圖案剛好 10 px） |

兩種都不是 11 的整數倍，22×22 的畫布被 Pixi 縮成 13.3／12.2 px，1 裝置像素的底色圈與圖樣會被重新取樣。放大圖 `3b-04`：1600 的黃底（暈眩）、藍底（緩速）、紫底（恐懼）都看得到底色、圖樣在中間；800 的圖案更糊但底色仍分得出。

**截圖**（`docs/art/shots/qi3/`；無頭 Chrome `--mute-audio --force-device-scale-factor=1 --disable-gpu`、網址 `?mute=1`；開發頁＝自己的 vite 5285，實機＝自己的 `trpg serve` 8138 正式 build）

| 檔 | 格式 | 對到 8.2 | 內容 |
|---|---|---|---|
| `docs/art/shots/qi3/3b-01-corner-stance-crystal-card20-dpr2-x6.png` | PNG 288 KB | 第 5 項 | 開發頁 `set=corner&zoom=6`（DPR 2，走遊戲端 `statusIconTile`＋`tileCanvas`＋`statusCorner`）：元素架勢 9 種 × 5 級（每列同圖、角落 1～5；伍級另帶回合 3，角落仍寫 5）、晶能湧動 1／狂湧 2、一般（燃燒回合 3、蓄力數值 4、隱蔽空、暈眩回合 2 黃底） |
| `docs/art/shots/qi3/3b-02-battle-1600.jpg` | jpg 127 KB | 第 6 項 | **實機 1600×900**（地圖 121%）：控制類（暈眩黃、緩速藍、恐懼紫、嘲諷）、持續傷害（燃燒、中毒）、增益（加速、再生）、中性（堅守、架勢）、2 個加「+N」、定時炸彈／蓄力徽章（`statusTile`）、主角 HUD 狀態列 |
| `docs/art/shots/qi3/3b-03-battle-800.jpg` | jpg 75 KB | 第 6 項 | **實機 800×600**（地圖 63%），同一場 |
| `docs/art/shots/qi3/3b-04-head-row-1600-800-x6.png` | PNG 154 KB | 第 6 項 | 頭頂一格 ×6 最近鄰（裝置像素比 1）：左 1600、右 800，同一隻並排；含蓄力／定時炸彈徽章（部件圓片） |
| `docs/art/shots/qi3/3b-05-status-cards-hud-unitinfo.jpg` | jpg 126 KB | 第 7 項 | **實機**主角 HUD 狀態列與單位資訊（Shift＋點釘住）× 1600、800（×2 最近鄰）：角落回合數、數值（護盾 15／8）、空、架勢級數（烈焰參 3、大地伍 5 蓋過回合 3）、晶能 1／2；控制類染底 |
| `docs/art/shots/qi3/3b-06-statustile-part-chip-24-x2.png` | PNG 295 KB | （0.0 第 7 點） | 開發頁 `set=tile&zoom=2`：部件圓片 `statusTile` 24px，名詞表 118 個；標「Q 版」32 個、「現行」86 個（`hooks.status`） |

**實機怎麼拍的（要說明）**：實機沒有「給單位加狀態」的開發入口，開一場戰鬥時單位多半沒有狀態。所以在**自己的無頭 Chrome** 用 `Page.addScriptToEvaluateOnNewDocument` 包一層 `window.fetch`，把戰鬥回應裡每個單位的 `statuses` 換成測試組合（`StatusView` 原欄位；主角 8 個、敵人各 1～6 個），**前端程式、後端、存檔都沒動**——畫面是正式 build 照常畫出來的。注入腳本在暫存區，沒進 repo。

**實機未看**：元素架勢 9 × 5 級全部在狀態卡的樣子（實機只拍到烈焰參、大地伍，其餘用開發頁 `3b-01`）；工坊的狀態選項 26px（QI-2c 已是 Q 版、本段沒動）；技能組裝列裡的狀態部件（目前沒有技能把狀態放進組裝列，開發頁 `3b-06` 代替）；1040×624 只跑了 `__layoutSmoke`，沒有截圖。

## 5.（3a 專用，略）

## 6. `__layoutSmoke` 與浮動卡實測

**`__layoutSmoke`**：見第 2 節 8.1-5。

**浮動卡**（6.5.1；自己的無頭 Chrome＋CDP 滑鼠事件；觸發元素＝`StatusBadge`（`PartTip`））

| 視窗 | 觸發 | 開 | 滑進卡片 | 卡內捲到底 | 釘住（點觸發元素、滑走） | 關閉（Esc） |
|---|---|---|---|---|---|---|
| 1600×900 | 主角 HUD：暈眩 | 1 張（240×181） | 卡還在 | 內容放得下（`scrollHeight 173 = clientHeight 173`），不需要捲 | `.pinned`、滑到 (8, 880) 後卡還在 | 卡關閉 |
| 1600×900 | 單位資訊（盜賊 1，Shift＋點釘住格子卡）：暈眩 | 1 張 | 卡還在 | 同上，不需要捲 | `.pinned`、滑走還在 | 卡關閉，單位資訊仍在 |
| 800×600 | 主角 HUD：暈眩 | 1 張 | 卡還在 | 不需要捲 | `.pinned`、滑走還在 | 卡關閉 |
| 800×600 | 單位資訊：緩速 | 1 張 | 卡還在 | 不需要捲 | `.pinned`、滑走還在 | 卡關閉 |

單位資訊在格子資訊卡（`HoverFloat`）裡：沒釘住時 `pointer-events: none`（例外規則），所以先用 Shift＋點釘住格子卡（`auto`）再測裡面的狀態徽章。

**請使用者重開伺服器檢查的重點**（前端有變，要重新 build；內容與 API 沒動）
1. 戰場頭頂狀態列：Q 版圖樣；暈眩、冰凍黃底，緩速、定身藍底，嘲諷、恐懼、沉默紫底（纏繞不染）；排序、最多 2 格＋「+N」照舊。
2. 主角狀態列、單位資訊的狀態圖示：Q 版圖樣，控制類同上的底色、圖樣有一圈細外框。
3. 狀態卡角落：元素架勢寫級數 1～5（即使有回合數）、晶能湧動 1／狂湧 2，其他照舊。
4. 戰場上的定時炸彈、蓄力徽章（部件圓片）：32 種是 Q 版，其他（例：定時炸彈、蓄力）仍是舊線條圖樣放在 Q 版圓片底上。
5. 字型載入後「第一個字」照舊會重畫（`clearStatusIconCache` 沒改）。

## 7. 複雜度 noqa、長函式

沒改 Python、沒新增 noqa。前端沒有超過 80 行的新函式（開發頁新增 `cornerSection` 約 25 行、`tileSection` 約 12 行、`legacyPaint` 約 18 行）。

## 8. 待 PM 決定

1. **`AssemblyTile.draw` 沒另加 `info?: { px, res }`**（規格第 0 節第 2 列、B3）：QI-2c 已改成 `draw(ctx, unitPx?, res?)`、`tileCanvas` 傳 `px / 100` 與 `res`，意義相同；`statusIconTile` 直接用它（沒傳時退回 0.2／`ICON_RES`）。要改成物件參數請告知。
2. **`statusTile` 的 86 種仍是舊線條圖樣**（0.0 第 7 點：「沒有的保留現行畫法並列進報告」）：`qIcon/status.ts` 其實已有全部 118 種的 Q 版圖樣，`hooks.status` 改指向它就能全換——但 `hooks.status` 掛在 `skillParts.ts`（本段禁改、QI-2d 在改），也要美術定「狀態框的圖」放進圓片的大小與外框。名單＝`3b-06` 標「現行」的 86 個（`QP.STATUS` 以外）。建議和 QI-2d 或⑤b 一起排。
3. **`tileKey` 的格式改成 `px|res|id`**（原 `px|id`，res≠2 時另加後綴）：鍵只在記憶體快取用，沒有持久化；`skillIcon.test.ts` 用 `tileKey(t, 30)` 比相等，照過。
4. **頭頂圖示被 Pixi 重新取樣**（第 0 節第 3 列接受）：1600 寬 13.3 px、800 寬 12.2 px（第 4 節）。若美術看 `3b-04` 覺得底色圈不夠，要另排「照螢幕實際尺寸出圖」。
5. **800 寬時，帶 3 個狀態的敵人頭頂只剩「+3」**（`3b-04` 第一列右）：這是既有的 6F-17「擁擠時狀態列只留 +N」（附近有徽章／相鄰單位），本段沒動排版；美術若覺得暈眩那隻應該看得到黃底，要另看 `chooseRowMode`。
6. **實機截圖用注入的狀態資料**（第 4 節）：沒有加開發入口；之後若常要拍狀態，可考慮加一個開發路由（後端，超出本段）。
7. **架勢與晶能的 `remaining`／`amount` 實測值**（附錄疑點 6）：本段沒跑能施加架勢的實戰，角落規則級數優先，不影響顯示；未實跑確認。
8. **開發頁 `&old=1` 的「舊畫法」是開發頁裡原樣抄的 `legacyPaint`**（遊戲端的舊 `paintStatusIcon` 本體已換成呼叫 Q 版），只對照用。
9. **截圖 6 張**（規格估 5～6）：多一張 `statusTile` 部件圓片（0.0 第 7 點併進來的範圍）。1040×624 沒截圖。
10. **第 0 節第 7 列（`statusTile` 空檔）**：0.0 已併進本段，已做（32 種 Q 版＋86 種 `hooks.status`）；剩下的是第 2 點。

## 9. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：檔頭 QI-3 改成「3b 已接線」；第一節 `skillIcon.ts`／`skillParts.ts` 列（`statusTile`／`statusIconTile` 已換、`tileKey` 含 res）、狀態圖示列（`paintStatusIcon` 新流程、`statusIconCanvas` 的 res、`statusCorner` 級數）；開發入口表 `status-gallery.html`（`live`、`corner`、`tile`、`old` 改義）；第四節第 40 點改寫、新增第 45～47 點；第五節測試表加一列。
