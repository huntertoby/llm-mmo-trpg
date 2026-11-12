# Phase QI-2c 報告：Q 版技能圖示｜前端接線

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-2計畫.md`（第 0.0 節開發 PM 定稿、第 6 節 C1～C10、第 7 節 T-C1～T-C8、第 8 節）＋開發 PM 第七任派工追加（裝備格對齊、刪暫時資料、`hooks.status`、改變出手的 6 招截圖）＋開發 PM 中途追加兩點（技能主圖的錘照樣張暗柄、開發頁實例名單照 `realPicks()`）。
> 起點 main `a5825a77`（含 QI-2b `10423205`、QI-2a）。未 push。平行的 QI-3a 檔案（`statusIcon.ts`、`qIcon/parts.ts`、`qIcon/core.ts`、`status-gallery`）**都沒動**；`qIcon/weapons.ts` 只照開發 PM 追加 1 的許可加了一個開關參數（第 1 節）；`skills.ts` 只改一行傳入該參數（同許可）。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| T-C6 基準 | **先在改動前**錄單位頭頂 `statusTile`（24）、狀態卡 `statusIconTile`（20）對名詞表 118 種狀態的假畫布呼叫紀錄雜湊（`render/fixtures/qi2cStatusBaseline.json`，236 組、雜湊兩兩不同） | `ef1f178a` |
| 追加 1 錘暗柄 | `qIcon/weapons.ts`：`qWeaponDef(r, icon = true)`（樣張 `def(look, icon)`）；`Builder` 多 `icon`；`HAMMER`／`maceArt` 在 `icon` 為 false 時用 `M.shaft`（`#6a4420`），快取鍵加 `|art`。`qIcon/skills.ts` 的 `weaponDef` 傳 `false`。預設行為（裝備圖示）不變 | `24be810b` |
| C1 三級 | `render/skillIcon.ts`：`SkillIconLevel`、`defaultIconLevel`（≤40 main）、`SKILL_CARD_ICON_LEVEL = "mid"`、`paintSkillIcon(ctx, icon, level, size, res)`（main＝`QS.paint`；mid／full＝`QP.paintIcon(toQParts(icon, partsOf(icon)))`）、`skillIconCanvas(icon, size, level, res)`（`blank()`、寬高 `iconCanvasPx`）、`iconCacheKey(icon, size, level, res)`。舊的 `paintSkillIcon` 改名 `paintLegacySkillIcon` 留著（開發頁 `&old=1` 用）。`ui/SkillIconView.tsx`：`level` 取代 `small`、畫布 `iconCanvasPx(size)`、`data-level` | `0e62505f` |
| C2 `partsOf` | 拆解仍只有 `partsOf`；段號由 `toQParts` 從 `segments[i].effects` 回推（2b 已做）；三處改動由 `QP.paintIcon` 畫（T-C2、T-C3 鎖住） | `0e62505f` |
| C3 部件 | `render/skillParts.ts`：`Part.q`（Q 版類別＋代碼＋修正內容的 `value`／`base`），`effectPart`、`conditionPart`、`costPart`、`triggerPart`、`linkPart`、`modifierChangePart` 都帶；`drawChip` 收 `unitPx`／`res` 時畫 Q 版（`QP.chip`：圓底與色環同現行、圖樣＝直徑 78%、整數裝置像素貼上），否則照舊 `draw`；`KNOWN_PARTS` 換成 Q 版的表（效果含 `EFFECT_ALIAS`、觸發含 `TRIG_ALIAS`；狀態仍是現行全表）。**`hooks.status`**：這個檔載入時掛上（`statusColor` 色＋`statusGlyph()`，照樣張頁 `q-icons-parts.html` 第 83 行） | `0e62505f` |
| C4 組裝列與工坊選項 | `tileCanvas(tile, px, res)`：`blank(iconCanvasPx)`、`tile.draw(ctx, px/100, res)`；`AssemblyTile.draw(ctx, unitPx?, res?)`；`skeletonTile`＝深色圓底 r40＋圖樣 62；`shapeTile`＝Q 版 `SHAPE` 圓片（id 保留臂長）；`optionTile` 的 shape／element／status（規格第 0 節第 10 列）／effects／condition／event 都是 Q 版圓片（半徑照現行 46）。**`statusTile`、`statusIconTile` 不動**（T-C6） | `0e62505f` |
| C5 表面 | `surfaceTile` → Q 版 8 種（油 `oilPool`） | `0e62505f` |
| C6 技能卡 | `SkillCardView` 56／compact 48 → `level={SKILL_CARD_ICON_LEVEL}`（mid）；`VariantList` 28 → `level="main"` | `0e62505f` |
| C7 卡片小圖 | `ui/SkillCardGlyphs.tsx`：`ChipGlyph` 16、`EffectGlyph` 18、`PinGlyph({ pinned = true })` 13 改 canvas（`render/skillIcon.ts` 的 `cardGlyphCanvas`＝`QP.cardCanvas` 加快取；傷害的元素色 `effectGlyphTint` 照現行 SVG 的色）。`BattleLogDock`（`pinned`）、`UnitInfo`（`pinned`）、`SkillCardView`（`pin.pinned`）傳實際狀態。保留 `aria-hidden`。舊 SVG 改名 `LEGACY_CHIP_PATHS`、`legacyEffectPath` 留著 | `0e62505f` |
| 字型重畫 | `clearSkillIconCache()` 一起清技能圖示、組裝列方塊、卡片小圖三個快取 | `0e62505f` |
| 追加 裝備格對齊 | `render/gearIcon.ts`：`pixelSnapNudge(x, dpr)`＝`Math.round(x × dpr) / dpr − x`、`onDevicePixel`；`ui/GearIcon.tsx`：`fit` 的畫布加 `gear-fit` class，量位置後 `position: relative` 挪過去（`ResizeObserver`＋視窗 resize 重量）| `facb6b7a` |
| C8 排版檢查 | `dev/layoutSmoke.ts`：`ICON_CANVAS_SELECTOR`（加 `skill-icon`、`part-tile`、`skill-chip-glyph`、`skill-effect-glyph`、`pin-glyph`）；`IconBox.snap`（`gear-fit` 的左上角對齊裝置像素）；`iconScaleProblem` 加位置判定 | `facb6b7a` |
| 追加 刪暫時資料 | 刪 `client/src/dev/fixtures/qi2bTempArt.json`（**誤併進 `facb6b7a`**，內容是刪除本身，不影響）；`qIconSkills.test.ts` 改只讀 fixture（第 3 節） | `facb6b7a`、`a2b600bf` |
| C9 開發頁 | `dev/skillIconGallery.ts`：有技能資料的格子一律走遊戲端 `paintSkillIcon`；`set=real` 照樣張 `realPicks()`；新 `set=motionchg`；`&marks=1`；`&old=1` 改畫 `paintLegacySkillIcon` | `a2b600bf`、`7f01323d` |
| C10 測試 | 新 `render/qi2cWiring.test.ts`（18 項）、`render/qi2cStatusUnchanged.test.ts`（1 項）；`dev/layoutSmoke.test.ts` 加 3 項；改寫既有測試（第 3 節） | `a2b600bf`、`facb6b7a`、`0e62505f`、`0da89141` |
| 截圖 | `docs/art/shots/qi2/2c-*` 9 張（第 4 節） | `7f01323d` |
| 上手筆記、本報告 | 第 9 節 | `0da89141`、本 commit |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| T-C1 | 級別 | 過：`qi2cWiring.test.ts` 「T-C1 級別」3 項（預設依邊長、技能卡 mid（掃 `SkillCardView`／`VariantList` 原始碼）、沒有地方再傳 `small`、快取鍵含級別／res／art 五欄）；`skillIcon.test.ts`「級別與內部解析度是不同的快取鍵」 |
| T-C2 | `partsOf` 和樣張相同 | 過：測試檔內照 `qIconsParts.js` 427–436 行寫樣張版，對 402 招＋隨機 50＋工坊示範 21 步比核心、效果列（鍵、順序、段號）、條件、代價、觸發、接續、骨架、類型、元素，全部相同 |
| T-C3 | 三處改動 | 過：被動、反應各挑一招：觸發 (15,15) r12.5、元素片 (12,39) r8、(15,15) r11 沒有；火元素主動技元素片 (15,15) r11；物理、沒有元素都沒有元素片；複合技接續色環 `#7fd8ff`、在效果列 y＝87、斜切線中央 (50,50) 沒有圓；骨架徽章 full (86,86) r11、mid (83,83) r15 |
| T-C4 | 畫布尺寸 | 過：`skillIconCanvas` 24～96、`tileCanvas` 18～30、`cardGlyphCanvas` 16／18／13 的寬＝顯示 × 2；元件原始碼用 `iconCanvasPx`；`layoutSmoke.test.ts`「圖示畫布（QI-1b／QI-2c）」3 項（整數＋相等過；小數、縮放、左上角沒對齊不過） |
| T-C5 | 圖釘 | 過：`PinGlyph({ pinned = true })` 與三處呼叫（掃原始碼）；未釘 `globalAlpha 0.55`＋灰鋼、已釘紅頭；傷害染色照現行 SVG 色 |
| T-C6 | 不動的確認 | 過：`qi2cStatusUnchanged.test.ts`：118 種 × 2 尺寸的呼叫紀錄雜湊和開工前基準完全相同；另在瀏覽器把 `a5825a77` 版 `skillIcon.ts` 與現行並排逐像素比：**236 組全 0 差異**（截圖 2c-09） |
| T-C7 | 表面與工坊選項 | 過：8 種表面的呼叫紀錄＝`QP.chip("surface", id)`；`optionTile` 的 status（含 32 種以外的 `armor_broken`）／element／shape／effects／condition／event＝`QP.chip(對應類別)`、skeleton＝深色圓底＋`QP.paint` 62、surface＝`surfaceTile`；不認得的值 `null` 或「?」（`unknown`） |
| T-C8 | 既有測試改寫 | 第 3 節 |
| 追加 錘 | 錘 3 招和樣張逐像素比 | 過：碎甲重擊、碎冰擊、碎岩擊 × main 24／28／40、mid 56／48、full 96 × res 1、2 ＝ **36 組全 0 像素差**（2b 時這 3 招各 6 組不同、最大色階差 54）。順帶跑全部 402 招同樣 12 種組合 ＝ **4824 組全 0 差異**（每張至少 408 個不透明像素，不是空圖）。**裝備圖示不變**：武器＋副手全部款式 × 5 材質 × 5 尺寸（1524 組）的 `gearIconCanvas`＋`weaponItemIconCanvas` 假畫布呼叫紀錄雜湊，改前（`git show HEAD:weapons.ts`）／改後逐行相同（`cmp` IDENTICAL）；`qi2cWiring.test.ts` 鎖住：`qWeaponDef(r)` 戰錘／釘頭錘含 `#a06a36`，`qWeaponDef(r, false)` 是 `#6a4420` |
| 追加 裝備格對齊 | `icons()` 位置檢查＋vitest | 過：純函式測試（`qi2cWiring.test.ts` 最後一項、`layoutSmoke.test.ts`）。實機（自己的 `trpg serve` 8141，建角進主城開背包）：1600×900@1、800×600@1.25、1040×624@1.5 三種 `icons()` 全 PASS（各 9 個 `gear-fit`，「左上角對齊裝置像素」）；1600@1 實際挪了 `top: 0.5px`（原本在 283.5） |
| 8.1-3 | 三個結束碼 | 見第 2.1 節 |
| 8.1-3 | 快照 | `render/__snapshots__/` 沒有變動（`git status` 乾淨）；`inkDollSnapshot`、`creaturePose` 在整包測試通過 |
| 8.1-5 | `__layoutSmoke.runCase` | 1600×900、1040×624、800×600 各 `localStorage.clear()` → `/?dev=1&anim=0.1&mute=1` → `runCase` **全 PASS**（12 項 × 3）；`icons()` 戰鬥 3 尺寸全 PASS；技能卡展開、戰鬥紀錄、單位資訊（1600、800）、工坊與工坊第 3～5 步（1600、800）的 `icons()` 全 PASS（例：工坊效果步 97 個畫布，顯示 16～96 px）；`runTown` 3 種尺寸全 PASS |
| 8.1-6 | 浮動卡實測 | 第 6 節 |
| 8.1-7 | 截圖 | 9 張 ≤ 242 KB（第 4 節） |
| 8.1-8 | (c)(d) | 第 4 節 |

### 2.1 交件前三個結束碼

在 `0da89141` 上依序跑（記錄檔在暫存區）：
- `corepack pnpm -C client typecheck` → **0**
- `corepack pnpm -C client test` → **0**（294 檔、3663 項全過；含 `inkDollSnapshot`、`creaturePose`）
- `corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）
- 跑完 `git status --short` 乾淨（快照、fixture 沒有被改）。

開發中跑的相關測試（規格第 9 節 QI-2c 清單＋本段新檔）：13 檔 242 項過；`qi2cWiring.test.ts` 18 項、`layoutSmoke.test.ts`＋`qIconArmor.test.ts` 32 項、`pr2bPractice.test.ts` 27 項過。沒有跑 `scripts/check.py`、pytest（沒改 Python）。

自己啟動的程序（vite 5290、`trpg serve` 8141、靜態伺服器 8142、無頭 Chrome 8143）交件前都已用自己的工作 ID／PID 關掉，四個埠都沒在聽、沒有殘留的 Chrome（以 `--user-data-dir` 認）。

## 3. 改寫的既有測試（舊斷言 → 新斷言，不放寬）

- `render/skillIcon.test.ts`
  1. 「內容庫的每個技能（大圖與小圖）」：`paintSkillIcon(ctx, icon, small∈{false,true})` 呼叫數 > 10 → `paintSkillIcon(ctx, icon, level, size)` 對 main 40／mid 56／full 96 都 > 10（掛假 Q 畫布，主圖與圓片裡的圖都真的畫）。
  2. 「隨機 50、工坊每一步」：`paintSkillIcon(…, false)` → `(…, "full", 96)`。
  3. 「不認得的元素、形狀…」：大小圖兩種 → full／mid／main 三種。
  4. 「小圖比大圖筆畫少」→「main < mid < full」（多一層比較）。
  5. 「工坊半成品：還沒有形狀＝虛線圈」→ Q 版主圖不畫虛線圈（`setLineDash` 不出現）；保留 `partsOf` 的 `el` undefined、`shape_id` null；新增：沒有 `art` 的草稿 `skillLook` ＝ none／aura／buff、沒有元素；fixture 工坊第一步的 `art` 也是 none／aura／buff。
  6. 「算式小圖：形狀隨元素與骨架變」→「形狀是 Q 版九宮格（命中格固定橘），不隨元素變、隨形狀變」（Q 版設計如此，見待決 4）。
  7. 「大小圖是不同的快取鍵」→「級別與內部解析度是不同的快取鍵」（main≠full、mid≠full、40 預設＝main、96 預設＝full、res 1≠2）。
  - 「部件庫對照 content/ 沒有漏」斷言沒改，`KNOWN_PARTS` 換成 Q 版的表後照樣全有（表面、條件、觸發、效果、狀態）。
- `render/qIcon/qIconSkills.test.ts`：拿掉暫時資料 `TEMP`（`artOf` 只讀 fixture）；新增一項「402 招、隨機 50、工坊示範每一步都帶 art」；`ARTS` 的隨機與工坊不再「有 art 才列」，全部列（比 2b 嚴）。
- `battle/pr2bPractice.test.ts`「資訊卡：木樁沒有頭像圖」：`FIGURE` 原本禁止任何 `<canvas`（註解：小圖示是 SVG，不算）→ 禁止 `<canvas`，**除了** class 是 `skill-chip-glyph`／`skill-effect-glyph`／`pin-glyph`／`part-tile` 的卡片小圖與部件圓片（它們從 SVG 換成 canvas）。頭像、`hero-face`、`portrait`、`<img` 照樣擋。
- `render/glossaryNames.test.ts`、`ui/skillCard.test.ts`、`world/panelIcons.test.ts`、`world/range.test.ts`：沒有描述舊畫法的斷言，不用改（照跑通過）。

快照：`render/__snapshots__/` 沒有變；沒有重產任何 fixture。

## 4. 需求第 6 節 (c)(d)、截圖、實機未看

**(c) 舊畫法還在哪裡**（第 0 節第 11 列：不刪）
- `skillIcon.ts`：`paintLegacySkillIcon` 與它用的 `bigGlyph`、`segMotif`、`compositeArt`、`mainArt`、`elementChip`、`skeletonBadge`、`effectRow`、`frame` → 只有開發頁 `&old=1` 呼叫。
- `skillGlyphs.ts`：`paintBackground`、`drawMotif`、`elementGlyph`、`skeletonGlyph` → 只剩上面那條與 `skillParts.ts` 的舊 `draw`；`framePath`、`rarityColor`、`elementPalette`、`isRanged`、`normalizeArm`、`SKELETON_NAME` 照常使用（`framePath` 是 Q 版外框）。
- `skillParts.ts` 的 `Part.draw`：**遊戲畫面仍在用的兩處**——修正技「改造對象」（`modifierTargetPart` 沒有 `q`，第 0.0 節「暫留現行畫法」）、32 種以外狀態的 `statusGlyph`（經 `hooks.status`）、以及 `statusTile`（單位頭頂，不動）。其餘部件的 `draw` 只在沒給 `unitPx` 時用（遊戲畫面都有給）。
- `SkillCardGlyphs.tsx`：`LEGACY_CHIP_PATHS`、`legacyEffectPath`、`legacyEffectColor` 沒人呼叫。

**(d)「別處依賴原版位」查證**：`grep` 全 `client/src` 的 `15, 15`、`85, 15`、`14, 86`、`86, 86`、`elementChip`、斜切／切線：除了 `skillIcon.ts`、`qIcon/` 本身與本段測試，**沒有任何程式或 CSS 依賴元素片在左上、接續在斜切線中央、物理有元素片**（命中的只有 `ambientAnim`／`creaturePose` 的「斜切」變形與 `skillParts.ts` 一個 15×15 方框，無關）。舊測試也沒有斷言這些座標。

**截圖**（`docs/art/shots/qi2/`；無頭 Chrome `--mute-audio --force-device-scale-factor=1`、網址帶 `?mute=1`；開發頁＝自己的 vite 5290，實機＝自己的 `trpg serve` 8141 正式 build）

| 檔 | 格式 | 對到 8.2 | 內容 |
|---|---|---|---|
| `docs/art/shots/qi2/2c-01-card56-48-mid.jpg` | jpg | 第 9 項 | 24 招（入門 6、被動 3、反應 3、複合 4、物理 2、沒有元素 1、跳斬、修正 2、姿態 2）mid：每格 56 真 1 倍、48 真 1 倍、56 DPR 2、48 DPR 2 |
| `docs/art/shots/qi2/2c-02-card56-mid-true1x-x6.png` | PNG 29 KB | 第 9 項 | 56 mid 真 1 倍 ×6 最近鄰（火焰彈、被動、反應、複合各一） |
| `docs/art/shots/qi2/2c-03-full96-dpr2.jpg` | jpg | 第 10 項 | 同 24 招 96 full DPR 2；標籤 ①觸發左上（元素片讓下）②接續進效果列 ③物理／沒有元素不畫元素片 |
| `docs/art/shots/qi2/2c-04-iconprop-motion-changed.jpg` | jpg | 派工追加 | `icon_prop` 改變出手的 6 招，逐招標「招名｜舊道具・舊出手 → 新」：迎頭痛擊、連環快刺、倒地補刀、蝕骨刺、毒刃 `w:sword・swing → w:dagger・thrust`；餘燼啃咬 `w:sword・swing → summon:whelp・shot`；40／24 DPR 2＋現行（虛線）、96 full |
| `docs/art/shots/qi2/2c-05-real75.jpg` | jpg | 第 5 項（追加 2） | 開發頁 `set=real`（樣張 `realPicks()` 規則）75 招：Q 版 40、24｜現行 40、24 |
| `docs/art/shots/qi2/2c-06-game-1600-battle.jpg` | jpg | 第 12 項 | **實機 1600×900**：技能列 40、技能卡 compact 48 mid＋常駐行 16／效果行 18＋組裝算式 30（未釘）、釘住後的卡頭（圖釘已釘）、戰鬥紀錄圖釘未釘／已釘、單位資訊（常駐行小圖、狀態卡狀態 20、圖釘未釘／已釘） |
| `docs/art/shots/qi2/2c-07-game-1600-workshop.jpg` | jpg | 第 12 項 | **實機 1600×900 工坊**（隨機一個、骨架＝被動）：96 full（觸發左上、元素片讓下）／40／28、組裝算式、技能卡片預覽 56 mid、骨架選項 26、形狀選項 26、條件步 |
| `docs/art/shots/qi2/2c-08-game-800.jpg` | jpg | 第 12 項 | **實機 800×600**：戰鬥（技能列、技能卡、圖釘兩態、戰鬥紀錄圖釘、單位資訊）＋工坊（骨架＝反應技：96／40／28、算式、卡片預覽 56、骨架選項） |
| `docs/art/shots/qi2/2c-09-status-unchanged-before-after.png` | PNG 119 KB | 第 13 項 | 單位頭頂狀態 24｜狀態卡狀態 20：每格「改前（`a5825a77` 版 `skillIcon.ts`，虛線）｜改後」，118 種全部；頁首寫逐像素比 236 組 0 差異 |

**實機未看**（用開發頁畫的或靠測試）：配招 24（`LoadoutEditor`）、隊伍 24（`PartyPanel`）、召喚面板 28、變奏列 28、靶場選職業 40、技能磚 40（`SkillTile`）、次要列 28、非 compact 的 56 技能卡（只在工坊「技能卡片預覽」實機看到）、狀態卡的表面圖（`SurfaceBadge`）與層數 `EffectGlyph`、組裝算式的條件／代價 18（工坊截圖裡有代價 18，戰鬥裡沒拍到）、工坊選項 20（狀態）／22（效果列表）實機截圖沒單獨拍（`icons()` 有量到 20、22 全 PASS）。這些尺寸的主圖畫法和 2b 的 24／28／40 截圖同一條路（開發頁現在也走 `paintSkillIcon`），且全 402 招逐像素和樣張一致。

## 5. （2a 專用，略）

## 6. 浮動卡實測、`__layoutSmoke` 結果

**浮動卡**（6.5.1；1600×900 與 800×600 各一次，自己的無頭 Chrome＋CDP 滑鼠事件）

| 觸發 | 滑進卡片 | 卡內捲到底 | 釘住 | 關閉 |
|---|---|---|---|---|
| 技能列按鈕 → 技能卡（含組裝算式 `PartTip`） | 兩尺寸：卡還在 | 展開「詳細」後兩尺寸都**不需要捲**（內容放得下，`scrollHeight ≤ clientHeight`） | 卡上圖釘 `aria-pressed=true`，滑走卡還在；組裝算式部件的 `PartTip` 說明卡出現（共 2 張浮動卡）且技能卡沒關 | 再按圖釘取消、滑走 → 卡關閉 |
| 工坊選項小圖 `OptionGlyph` | **滑不進**：滑出小圖說明卡就關（逐步移動 12 步也一樣） | — | 沒有圖釘 | 滑走即關 |
| 戰鬥紀錄圖釘 | — | — | 展開紀錄後按圖釘：未釘（灰 55%）→ 已釘（紅頭）`aria-pressed=true`；再按回 `false` | — |
| 單位資訊圖釘（追加） | — | — | 未釘 → 已釘 `aria-pressed=true`（標籤「釘選」→「取消釘選」） | — |

`OptionGlyph` 的說明卡是 `PartTip pin={false}` → `pinOn: "touch"`、`no-bridge`，本來就設計成不可滑入（既有行為，本段沒改 `PartTip`）；列為待決 6 給 PM 確認是否要改。

**`__layoutSmoke`**：第 2 節 8.1-5 列。`runCase` 三尺寸各 12 項全 PASS；`icons()` 在戰鬥、技能卡、戰鬥紀錄、單位資訊、工坊（含第 3～5 步）、背包（身上裝備格）全 PASS。

**請使用者重開伺服器檢查的重點**（前端畫面有變，要重新 build；內容與 API 沒動，一輪不會重開）
1. 戰鬥技能列 40／28：Q 版主圖（道具＋出手＋記號＋元素底）。
2. 技能卡（滑過技能鈕）：48／56 是 mid——右下骨架徽章；被動、反應左上多觸發圓片；常駐行、效果行的小圖是 Q 版；右上圖釘未釘是灰色半透明、釘住變紅頭。
3. 展開「詳細」的組裝算式：部件圓片換 Q 版；修正技第一塊「改造對象」照舊（待美術補圖）。
4. 技能工坊 96：觸發在左上、元素片讓到它下面；複合技的接續記號（青色環）在底部效果列；物理與沒有元素的技能不畫元素片。選項小圖（骨架、形狀、效果、條件、狀態、元素）是 Q 版。
5. 戰鬥紀錄展開後的圖釘、單位資訊卡的「釘選」圖釘兩態。
6. 單位頭頂的狀態小圖、狀態卡的狀態圖**應該和以前一樣**。
7. 背包身上裝備格的圖示（QI-1b 驗收）：外框更銳利（左上角對齊裝置像素）。

## 7. 複雜度 noqa、長函式

沒有改 Python，沒有新增 noqa。前端沒有超過 80 行的新函式（最長是 `skillIconGallery.ts` 的 `sets()` 約 75 行，2b 既有、本段加兩個 case）。

## 8. 待 PM 決定

1. **實例名單是 75 招，不是 78**：照樣張頁 `realPicks()` 規則算出 75 招，和樣張 `docs/art/shots/qicons/skills-real.png` 標題「實例 75 招」一致（需求文件寫的 78 應是舊數字）。但開發頁用的是遊戲的 `art`（含 `icon_prop`），和樣張資料 `qSkillsData.js`（沒套 `icon_prop`）相比有 5 招不同：開發頁多 `bastion_strike`、`blazing_round`、`bulwark_stance`、`ember_bite`、`form_mastery`，少 `burning_shove`、`form_werewolf`、`rampart_jeer`、`shield_bash`、`summon_ember_whelp`。照最保守做法用遊戲實際畫的 art；要逐招對上 png 請說，可改成用樣張資料。（開發 PM 追加 2）
2. **錘暗柄的開關加在 `qIcon/weapons.ts`**（QI-3a 的禁改清單內，但有開發 PM 追加 1 的許可）：只加參數與兩處三元式、預設不變；請 QI-3a 合併時留意這個檔有本段改動。
3. **`qi2bTempArt.json` 的刪除誤併進 `facb6b7a`**（「裝備格對齊」那個 commit），沒有另開 commit。內容無誤，只是 commit 歸屬不乾淨；要拆請說。
4. **組裝列的形狀圓片不再隨元素變色**（舊測試 6 改寫）：Q 版 `SHAPE` 命中格固定橘、照樣張；臂長 2 的十字仍是 3×3 圖（說明寫臂長）。請美術確認不需要大十字款。
5. **工坊選項圓片半徑照現行 46**（`chipCanvas` 是 42）：規格沒寫，保留現行版面；Q 版圖樣因此比組裝列大一點（26px 選項：圖樣 18.7px → `small`）。
6. **工坊選項小圖說明卡滑不進**（第 6 節）：既有設計（`pin={false}` 不搭橋），本段沒改；浮動卡規則 6.5.1 若要求所有說明卡可滑入，需另排。
7. **`pr2bPractice.test.ts` 的「沒有頭像圖」放行了卡片小圖 canvas**（第 3 節）：用 class 白名單，頭像、`portrait` 等照擋。請確認這個解讀。
8. **`hooks.status` 掛在 `skillParts.ts` 載入時**（模組副作用）：任何畫 Q 版部件的路徑都會先載入它；QI-3（第⑤批）換狀態時可能要改掛法。
9. **草稿的中性元素**（2b 待決 9 延續）：`toQParts` 把 `undefined` 當沒有元素（不畫元素片、預設底），T-C2 和樣張一致；舊畫法的「中性灰」在 Q 版沒有對應。
10. **修正內容箭頭**：`form_upkeep_permille`、`summon_limit_delta` 照現狀畫（開發 PM 指示），沒有自己加。

## 9. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：檔頭加 QI-2c 已接線；第一節：qIcon 技能列改寫（`hooks.status` 已掛）、新增 `skillIcon.ts`／`skillParts.ts`（三級、`Part.q`、`drawChip` 的 `unitPx`、`tileCanvas`、卡片小圖）與 `SkillIconView`／`SkillCardGlyphs` 兩列、`qWeaponDef` 的 `icon` 旗標、`GearIcon fit` 的對齊；第二節：`skillicon-gallery.html` 參數（`motionchg`、`marks`、`real`、`old` 改走 `paintLegacySkillIcon`、拿掉暫時資料）、`icons()` 的新範圍；第四節第 37～42 點（`drawChip` 要給 `unitPx`、`statusTile` 兩種用途與 T-C6 基準、canvas 不吃 CSS 顏色、錘柄兩種、選項說明卡 no-bridge、進大世界的無頭腳本）；第五節測試表加一列。
