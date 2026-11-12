# Q 版小圖示第 3、4 批（技能主圖、徽章與部件）：移植需求（給開發 PM）

美術 PM，2026-11-12。這是 Q 版小圖示的第二份移植需求（第一份是 `Q版小圖示-武器防具移植需求.md`，開發段 QI-1）。範圍＝第③批技能主圖＋第④批骨架徽章、部件小圓片、技能卡小圖、56／96px 組裝（含第④批已畫的 32 種狀態圖樣），**含後端段**（`icon_of()` 要多帶的資料與推導規則）。

- **定案依據**：使用者看過第 3、4 批，沒有意見（2026-11-12，專案 PM 轉達；第③批原話「都照建議」，第④批原話「第4批沒意見」）。第 3 批第 3 版過審（`Q版小圖示-第3批技能主圖-審查.md`「第 3 版複審」），第 4 批第 2 版過審（`Q版小圖示-第4批徽章與部件-審查.md`「第 2 版複審」，文件 `62a5e833`）；前三批真 1 倍補查第 2 版複審通過（`Q版小圖示-前三批真1倍補查.md`）。
- **樣張版本**：第 3 批的圖 `6b4e3cea`＋真 1 倍修正 `0caaa84f`；第 4 批的圖 `10b1040f`。**以 `10b1040f` 之後的 `docs/art/sample/` 為準**（`qIconsSkills.js`、`qIconsParts.js` 在這之後沒有再改）。
- **紀錄**：`docs/art/Q版小圖示-第3批技能主圖.md`（第 4 節推導規則表、第 11 節與 15.6 給開發的重點、4.5 後端要多帶的 7 項）、`docs/art/Q版小圖示-第4批徽章與部件.md`（第 5 節組裝、第 8 節給開發的重點、第 9 節美術 PM 的決定）。兩份給開發的重點已整理進本文第 4 節。
- **不在這一份**：狀態圖示的**框**（極性框形、框色）與**類別底色**、頭頂 11px、狀態卡 20px 是第⑤批，另給一份移植需求；第⑤批直接沿用本段搬過去的 32 種狀態圖樣（`qIconsStatus.js` 呼叫 `qIconsParts.js`）。
- **沒有實機截圖**：樣張「現行」欄，第 3 批是樣張端的 `AssembledIcon.draw`（`assembled.js`＋`skillIcons.js`＋`parts.js`）；第 4 批是遊戲端原始程式打包的 `sample/tools/qPartsLive.js`（`skillIcon.ts`、`skillParts.ts`、`skillGlyphs.ts`、`statusIcon.ts`），技能卡小圖的 SVG 原樣抄在 `q-icons-parts.html` 的 `CARD_SVG`。
- 本文引用的遊戲端檔案以 **main `3dd40196`** 查證（QI-1a 已合併：`client/src/render/qIcon/core.ts`、`weapons.ts`；IP-1 已合併）。

## 1. 目標與範圍

### 1.1 要換掉的畫法（只換框裡、圓片裡的圖）

| 遊戲端 | 現在 | 換成 |
|---|---|---|
| `client/src/render/skillIcon.ts` 的 `paintSkillIcon()`：主圖 `mainArt()`／`compositeArt()`／`segMotif()`、底 `paintBackground()`＋`elementTexture()`＋第二元素斜色帶 | 現行組裝式主圖（元素漸層與紋理底、形狀動態、核心效果圓片） | 第 3 批主圖＝道具＋出手＋效果記號，兩階色塊元素底（`qIconsSkills.js` 的 `paint()`／`def()`／`base()`） |
| 同上，`small`（≤40px）時右下的核心效果圓片（`drawChip(ctx, parts.core, 79, 79, 18, …)`） | 有 | **拿掉**（使用者 11-11 同意；第3批 11 節第 3 點） |
| 同上，>40px 的四角圓片、骨架徽章 `skeletonBadge()`、元素片 `elementChip()`、底部效果列 `effectRow()` | 現行版位與圖樣 | 第 4 批 `paintIcon()` 的 `"full"`；另加 `"mid"`（技能卡用）。版位三處改動見 4.3 |
| `client/src/render/skillParts.ts` 的 `EFFECT`、`COND`、`COST_ART`、`TRIG`、`LINK`、`modifierChangePart` 的圖樣；`effectPart()` 帶狀態、帶表面時的圖樣 | 現行圖樣 | `qIconsParts.js` 的 `EFFECT`、`COND`、`COST`、`TRIG`、`LINK`、`CHANGE`、`STATUS`（32）、表面（8 種外形） |
| `client/src/render/skillGlyphs.ts` 的 `skeletonGlyph()`；圖示左上元素片用的 `elementGlyph()`；組裝列的 `shapeTile()`（`skillIcon.ts`） | 現行 | `SKELETON`（16）、`ELEMENT`（第 3 批元素道具縮小）、`SHAPE`（13，九宮格示意） |
| `client/src/ui/SkillCardView.tsx` 第 169 行 `<SkillIconView … size={compact ? 48 : 56} small …>` | 強制 `small` | 改成 `"mid"`（主圖＋右下骨架徽章＋被動／反應左上觸發時機）（4.3 第 15 點；48 見第 5 節第 5 點） |
| `client/src/ui/SkillCardGlyphs.tsx` 的 `ChipGlyph`（16px）、`EffectGlyph`（18px）、`PinGlyph`（13px）共 22 個 SVG | React SVG，圖釘用 `currentColor` 變色 | 第 4 批 `CARD`（`cardCanvas()`）；圖釘收 `pinned` 參數（4.4 第 25 點） |

**範圍數量**（第4批 1 節盤點，以遊戲端為準）：主圖道具 56 個代碼（含「沒有道具」）、出手 9、效果記號 23、染色 13 色＋`stone`；骨架徽章 16、效果 51 個圖（53 個代碼）、表面 8、條件 17、代價 6、觸發 22（＋5 個暫代）、接續 6、形狀 13、修正內容 21 個鍵、元素 9、狀態 32、技能卡小圖 22（含圖釘兩態）。技能數 `content/skills/` 402 招（其中 `enemy_only` 22 招）。

### 1.2 不動的（規則 13：框不動，只換框裡的圖）

- **技能外框**：`skillGlyphs.ts` 的 `framePath()`（主動方、反應盾、被動圓、姿態六角、修正齒輪）與稀有度色 `RARITY_COLOR`、傳說／史詩的內框。樣張呼叫的就是現行外框（第3批 1 節最後一條）。
- **圓片的深色圓底與色環**：`drawChip()` 的圓底、色環粗細；**徽章的圓底與稀有度色環**（`skeletonBadge()`）；組裝列 `tileCanvas()` 的 100 單位座標與圓片半徑 42、工坊選項 46。
- **縮放屬性的文字圓章** `AttrGlyph`（第4批 1 節）。
- **不在這一段的**：狀態框與類別底色（`statusIcon.ts`、`skillIcon.ts` 的 `statusTile()`、`statusIconTile()`；單位頭頂與狀態卡）＝第⑤批；元素關鍵字小圖樣＝第⑤b 批；HUD 的源力圖示（之後對齊成晶石）＝第⑦批；`storyIconArt.ts` 的同名 `drawChip`（劇情圖示，和技能無關）。

### 1.3 用到這些畫法的地方（main `3dd40196` 的 `client/src/` 查到的呼叫處；驗收截圖照這張表拍）

| 元件 | 檔案 | 尺寸（CSS px） | 這段之後畫什麼 |
|---|---|---|---|
| `SkillIconView` | `run/LoadoutEditor.tsx`（兩處）、`world/PartyPanel.tsx` | 24 | 主圖（`main`） |
| | `ui/SkillBar.tsx`（次要列）、`ui/SummonPanel.tsx`、`ui/VariantList.tsx`、`ui/workshop/CheckPanel.tsx` | 28 | 主圖 |
| | `ui/SkillBar.tsx`（技能按鈕）、`ui/SkillTile.tsx`、`world/RangeClassPick.tsx`、`ui/workshop/CheckPanel.tsx` | 40 | 主圖 |
| | `ui/SkillCardView.tsx` | 56（`compact` 時 48） | `mid` |
| | `ui/workshop/CheckPanel.tsx` | 96 | `full` |
| `AssemblyFormula`（`TileCanvas`） | `ui/SkillCardView.tsx`、`ui/workshop/CheckPanel.tsx` | 30（各段部件）、18（條件、代價） | 部件小圓片、徽章、形狀 |
| `OptionGlyph`（`optionTile()`） | `ui/workshop/FieldEditor.tsx` | 26（預設）、20、22 | 部件小圓片 |
| `ChipGlyph`／`EffectGlyph` | `ui/SkillCardView.tsx`；`ui/StatusCardParts.tsx`（`ap`、`mana`、`source`、`reaction`、效果 `stack`） | 16／18 | 技能卡小圖 |
| `PinGlyph` | `ui/SkillCardView.tsx`、`ui/BattleLogDock.tsx`、`ui/UnitInfo.tsx` | 13 | 圖釘兩態 |
| 開發頁 | 目前沒有技能圖示專用的開發頁（`client/dev/skill-gallery.html` 是技能動畫片段）；可擴充 `client/dev/weaponicon-gallery.html` 或另開，由開發決定。資料可用 `client/src/render/fixtures/skill_icons.json`（402 招的圖示資料） | | |

`statusTile()`（`render/unitSprite.ts` 單位頭頂 24）、`statusIconTile()`、`surfaceTile()`（`ui/StatusCardParts.tsx` 狀態卡 20）也走 `drawChip()`，但傳自己的 `draw`：**狀態那兩個這段不動**（第⑤批）；`surfaceTile()` 見第 5 節第 7 點。

## 2. 來源與移植方式

### 2.1 樣張畫法檔（`docs/art/sample/`）

| 檔案 | 內容 | 主要 API |
|---|---|---|
| `qIcons.js`（`window.QIcons`） | 共用：剪影外框、畫法小工具、`ART.status`／`ART.hud`（第 4 批包一層 `from48()` 呼叫） | `render(def, px, res, { ow })`、`outlinePx(px)`、`H`、`W`（含 `totemPole`）、`M`、`EL` |
| `qIconsWeapons.js`（`window.QIconsWeapons`） | 第 1 批武器副手；這兩批用它的 `def(look)`（武器道具）與 `blit()` | 遊戲端已有：`client/src/render/qIcon/weapons.ts`、`qIcon/core.ts` 的 `blit()`、`ICON_RES`（QI-1a） |
| `qIconsSkills.js`（`window.QIconsSkills`） | 第 3 批主圖：道具、出手、記號、元素底 | `def(look)` → `{ pre, d, post, meta }`；`paint(ctx, look, size, res, { frame })`；`base(ctx, look)`；`ELEMENT`、`SUMMON`、`FORM`、`MOTION`、`ACT`、`TINT`、`BASE`、`RARITY`、`PAD`、`framePath`；`look = { prop, motion, act, tint, el, el2, spark, kind, rarity }` |
| `qIconsParts.js`（`window.QIconsParts`） | 第 4 批：徽章、圓片、卡片小圖、組裝 | `def(cat, id, 圖樣px)`、`glyph()`、`paint(ctx, cat, id, x, y, size, unitPx, res)`、`chip()`、`chipCanvas(cat, id, px)`、`cardCanvas(id, px, zoom, { pinned })`、`cardPx(px)`、`partsOf(icon)`、`paintIcon(ctx, icon, look, size, res, { level })`；`TRIG_ALIAS`、`EFFECT_ALIAS`、`COST_RING`、`LINK_RING`、`UNLIT`、`BOX`、`hooks.status` |
| `tools/qskills_derive.py` | **推導規則的參考實作**（技能內容 → `look`），只讀 `content/skills/` | `derive(skill)` → `{ prop, motion, act, tint, el, el2, spark }`；`derive_prop`、`derive_motion`、`derive_action`；表 `WEAPON_LOOK`、`MELEE_WORDS`、`RANGED_WORDS`、`SUMMON_GROUP`、`SUMMON_TINT`、`MOD_TAG_PROP`、`MOD_TINT`、`DOT`、`BIND`、`CURSE`、`STATUS_TINT`、`COND_TINT`、`SURFACE_TINT`、`EFFECT_ACTION`、`LATE_ACTION`、`NEEDS_PROP` |

只在樣張端、不用搬的：`qSkillsData.js`（推導匯出）、`qPartsData.js`、`tools/qPartsLive.js`、`tools/qparts_export.py`、`q-icons-skills.html`、`q-icons-parts.html` 的自查與總表。

樣張頁：`q-icons-skills.html`（`?part=a｜b｜starters｜real｜scene｜audit｜review｜hash｜lab｜true1x`）、`q-icons-parts.html`（`?part=a｜b｜asm｜scene｜audit｜review（&only=類:代碼,…）｜hash｜asmzoom｜true1x`）。

### 2.2 建議的移植方式

1. **照樣張原樣搬成 TypeScript，不另畫簡化版**（品質底線第 5 條）。`qIconsSkills.js`、`qIconsParts.js` 的畫法逐行搬，放 `client/src/render/qIcon/` 下（和 QI-1a 同一處；檔名由開發決定）；武器道具直接呼叫 QI-1a 的 `qIcon/weapons.ts`，不要再搬一份 `qIconsWeapons.js`。
2. **推導放後端**（第 3 節）：前端只吃 `look` 代碼畫圖，不在前端另寫一份規則。
3. **出圖照樣張的流程、框照現行**：主圖＝`render(def(look), a, res, { ow: outlinePx(size) })` 用 `blit()` 貼在框內留白處；圓片＝現行圓底與色環＋`paint()`（圖樣本身＝直徑 78%）；組裝＝`paintIcon()` 的三級。
4. **搬完用樣張頁對照**：同一招（同一份 `SkillIcon`＋`look`）、同一個尺寸與 `res`，遊戲端的圖和樣張應逐像素相同；材質色照 QI-1 決定改用 `material.ts`（2.4 第 3 列）造成的武器道具色差除外。

### 2.3 和遊戲端清單對齊

- 圖示資料：`src/trpg/narrative/skill_icon.py` 的 `SkillIcon`（API 經技能卡片、變奏卡片、`/api/workshop/check` 的 `icon` 給前端；前端型別由 `pnpm gen:api` 產生）。
- 部件代碼：`skillParts.ts` 的 `KNOWN_PARTS`；名詞表（`/api/glossary`）的狀態、表面、觸發。第 4 批的清單由 `qparts_export.py` 用後端的 `build_glossary` 與 `skill_icon` 匯出，和遊戲端同一份。
- 道具：`content/skill_icon_props.yaml`（IP-1，57 個值）＝`docs/art/技能圖示道具清單.md` 第 1 節。
- 召喚物分組：`content/summon_looks.yaml` 的 `body`／`variant`（推導腳本的 `SUMMON_GROUP` 照它寫）。

### 2.4 樣張與遊戲端對不上的地方（逐條）

| # | 項目 | 樣張 | 遊戲端 | 移植怎麼做 |
|---|---|---|---|---|
| 1 | 推導在哪 | Python 腳本算好匯出 `qSkillsData.js`，頁面只讀 | 沒有推導；`SkillIcon` 缺 7 項原始欄位 | 後端算 `art`（第 3 節） |
| 2 | `icon_prop` | 參考實作 `qskills_derive.py` **沒有讀** `icon_prop`（寫在 IP-1 之前） | IP-1 已入檔 36 招、`SkillIcon.icon_prop` 已帶出 | 後端推導照 3.3 插入；行為一致測試對有填的招另算（3.5） |
| 3 | 武器道具的材質色 | `propOf()` 給劍、巨劍、火槍、手槍、雙手槍 `steel`，其餘用第 1 批預設；色票是 `qIcons.js` 的 `M`（人物那一份） | QI-1 開發 PM 決定（`PhaseQI-1計畫.md` 0.0 第 3 點，美術同意）：圖示用 `material.ts` | 照 QI-1：呼叫 `qIcon/weapons.ts`，材質名照 `propOf()`、色照 `material.ts`。逐像素對照時武器道具的金屬色會差一階，不算不一致 |
| 4 | 技能外框 | 有載入 `assembled.js` 時用 `AssembledIcon.framePath`（樣張版） | `skillGlyphs.ts` 的 `framePath()` | 用遊戲端的 |
| 5 | 貼圖 | `QIconsWeapons.blit()` | `qIcon/core.ts` 的 `blit()`、`blitOrigin()`（QI-1a 已有） | 共用 QI-1a 那一份，不另寫 |
| 6 | 內部解析度 | `canvas()` 預設 zoom 1 時 ×2；`{ res: 1 }` 是真 1 倍 | `skillIcon.ts`、`tileCanvas()` 固定 `DPR = 2`；`SkillIconView`／`TileCanvas` 畫布 `size × 2`、CSS 原尺寸 | 照 QI-1 0.0 第 1 點：畫布＝顯示尺寸 × 2、CSS 顯示原尺寸、畫到整數像素；開發頁另能切 1（驗收用） |
| 7 | 大小圖分級 | `paintIcon(…, { level })`：`main`（≤40 預設）、`mid`、`full` | `small: boolean`（`SMALL_ICON_MAX = 40`）；快取鍵含 `s`／`l` | 改成三級；快取鍵帶級別（4.1 第 5 點） |
| 8 | 部件清單 `partsOf` | `qIconsParts.js` 自己的 `partsOf()`（照現行規則：核心＝第一個不是單純傷害的效果、最多 4 個；被動／反應才有觸發） | `skillIcon.ts` 的 `partsOf()` | 用遊戲端的，只加 4.3 的三處改動。兩者其餘地方是否完全相同：待開發查證 |
| 9 | 非技能施加的狀態 | `hooks.status`（樣張頁掛現行白色狀態圖樣）；沒掛時畫增益箭頭 | `statusGlyph()` | 32 種以外照現行 `statusGlyph()`（第4批 8 節） |
| 10 | 卡片小圖 | canvas（`cardCanvas()`） | React SVG（`SkillCardGlyphs.tsx`） | 換 canvas；或開發另選做法，但結果要和樣張同圖（第 5 節第 6 點） |
| 11 | 圖釘 | `cardCanvas("pin", 13, 1, { pinned })` 兩態 | `PinGlyph` 一種，`currentColor`；註解說和 `HoverFloat` 的圖示相同 | 收 `pinned`；`HoverFloat` 是否另有一份圖釘、要不要一起換：待開發查證 |
| 12 | 組裝列骨架 | `chipCanvas("skeleton")`：深色圓底、沒有色環、圖樣 62 單位 | `skeletonTile()`：`skeletonGlyph` 放大 3 倍 | 照樣張 |
| 13 | `elementGlyph` 的其他用處 | — | `skillParts.ts` 522、1133 行（修正內容 `add_element`）、`skillIcon.ts` 594 行（工坊選項）、`skillGlyphs.ts` 的 `paintBackground`／`drawMotif` 系列 | 修正內容與工坊選項改用 `ELEMENT`（第4批 `CHANGE.add_element`、`element`）；`paintBackground`、`drawMotif` 隨主圖換掉後是否還有人用：待開發查證 |

## 3. 後端段：`icon_of()` 要多帶的資料與推導規則

檔案：`src/trpg/narrative/skill_icon.py`（main 查證：`icon_of(skill: Mapping)` 純函式、永遠不丟例外；`skill_icon(SkillDef)` 是包裝）。

### 3.1 已在 IP-1 做完的（不用再做）

- `SkillDef.icon_prop`、允許清單 `content/skill_icon_props.yaml`（57 個值，帶 `group`、`weapon_class`）、載入時檢查（清單外、大類不符拋 `ContentError`）；36 招已填（`PhaseIP-1報告.md` 交付 1、2）。
- `SkillIcon.icon_prop`（沒填不輸出）；技能卡片、變奏卡片的 `icon` 跟著帶；`client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/render/fixtures/skill_icons.json`、`client/src/ui/fixtures/skillCards.json` 已重產（交付 4）。
- LLM 提議、白板、工坊草稿入口一律丟掉 `icon_prop`（交付 3）。
- **前端沒有畫 `icon_prop`**：這一段才畫。

### 3.2 要做：新增推導、API 多帶 `art`

美術建議（第3批 4.5、11 節第 1、2 點）：**在後端算好一個欄位**，例如 `SkillIcon.art = { prop, motion, act, tint, spark }`（都是字串代碼；草稿缺欄位時照 3.3 的表落到 `none`／`aura`／`buff`，不丟例外），前端只管畫；元素底 `el`、`el2` 直接用現有的 `SkillIcon.elements[0]`、`[1]`（規則相同，沒改）。現有欄位不動（第 4 批的徽章、圓片、組裝列還要用）。純函式、只看輸入；表一律 tuple 依序比對，不依賴 `set` 順序（CLAUDE.md 守則 2）。

若不在後端算，就要把下表 3.4 的 7 項原始欄位全部帶給前端、在前端寫推導（不建議：規則會有兩份）。

### 3.3 推導規則表（第3批第 4 節的最終版；參考實作 `docs/art/sample/tools/qskills_derive.py`）

每張表「由上往下，第一個符合的就用」。效果清單＝`effects` 接 `followup.effects`。各表的細項（召喚物分組、狀態分類、條件色…）**照腳本裡同名的表抄，不要另寫**。

**道具 `prop`**（`derive_prop`；`icon_prop` 插在第 2、3 列之間）

| 順序 | 條件 | 結果 |
|---|---|---|
| 1 | 效果裡有 `enter_form` | `form:<effects[].form>` |
| 2 | 任何效果的 `condition.type == wielding_weapon` | `w:<condition.weapon>`，經 `WEAPON_LOOK` 換成種類／形制（`arcane_blade`→`sword/arcane`、`tower_shield`→`kite_shield/tower`、`round_shield`→`round_shield/wood`、`tome`→`tome/book`、`orb`→`orb/ball`、`scepter`→`staff/scepter`、`totem_staff`→`staff/totem`…，其餘武器 id 就是種類） |
| **2b** | **技能有 `icon_prop`，而且值在允許清單內** | **`icon_prop` 的值**（IP-1 已入檔；06 6.36；`技能圖示道具清單.md` 第 0 節：化身與 `wielding_weapon` 仍優先，這兩類招填了不生效） |
| 3 | 修正技（`kind == modifier`，或沒有效果而有 `modifiers`） | 看 `modifiers[0].applies_to`：`skill_tags` 有 `heal`→`el:holy`、`summon`→`summon:spirit`、`ranged`→`w:bow`；`all_attacks` 或 `actions` 含 `attack`→`w:sword`（`weapon_req` 遠程是 `w:bow`）；其他有 `actions`／`skill_tags` 且近戰→`w:fist`；其餘→`w:tome/book` |
| 4a | `weapon_req == ranged` | 名稱關鍵字（下表）→ 沒中是 `w:bow` |
| 4b | `weapon_req == melee` | `tags` 有 `stealth`→`w:dagger`；有 `martial`→`w:fist`；名稱關鍵字；形狀 `cone`／`ring`→`w:greatsword`；其餘→`w:sword` |
| 5 | 效果裡有 `summon` | `summon:<組>`（`effects[].unit` 去掉 `summon_` 後查 `SUMMON_GROUP`；不認得→`spirit`） |
| 6 | 元素（`elements[0]`）不是物理也不是空的 | `el:<元素>` |
| 7 | `tags` 有 `water` 或效果有 `surface: water` | `el:water` |
| 8 | `tags` 有 `arcane` | `el:arcane` |
| 9 | 其餘 | `none` |
| 最後 | `prop == none`，而且記號（下面的 `act`）是 `hit`、`combo`、`finisher`、`step`、`dash`、`transform`、`summon`（`NEEDS_PROP`） | 改成 `el:arcane`（**`icon_prop: none` 也一樣**，`技能圖示道具清單.md` 1.7） |

名稱關鍵字（`name_zh` 含有就算，先列的先比；第 3 版只留指名武器的字）：近戰 盾→`kite_shield`、鞭→`whip`、拳→`fist`、匕→`dagger`、矛／槍→`spear`、斧→`axe`、鐮→`scythe`、錘／鎚→`hammer`；遠程 弩→`crossbow`、飛刃／飛刀→`kunai`、槍→`longgun`。（第3批 4.1、15.6）

**出手 `motion`**（`derive_motion`；**吃的是最後決定的 `prop`**，所以 `icon_prop` 會影響出手，例：填 `w:spear` 的單體近戰是 `thrust`）

1. `shape.type`：`chain`→`chain`；`line`→`thrust`；`cone`→`sweep`；`ring`→`spin`；`square3`、`cross`、`allies_in_radius`→`area`；`ground_tile`→`place`；`self` 或沒有→`aura`。
2. 其餘，道具是武器（`w:`）而且 `weapon_req == melee`：`single` 而且道具是矛或匕首→`thrust`；否則 `swing`。
3. `single` 而且 `shape.range` 是 1 或沒有、道具不是遠程武器（弓、弩、火槍、霰彈槍、手槍、雙手槍、飛刃）→`swing`。
4. 其餘→`shot`。

**效果記號與染色 `act`、`tint`**（`derive_action`）

| 順序 | 條件 | 記號 | 染色 |
|---|---|---|---|
| 1 | 修正技 | `modify` | `change.add_element` 的元素；否則照改動的鍵查 `MOD_TINT` |
| 2 | `followup.when == delayed` 而且第一段只有 `shield` | `builder` | 第二段第一個非物理元素 |
| 3～13 | `EFFECT_ACTION` 依序：`enter_form`→`transform`；`summon`→`summon`；`sacrifice_summon`／`consume_status`／`detonate_runes`→`detonate`；`place_trap`／`delayed_damage`／`inscribe`→`trap`；`shadowstep`／`teleport`／`teleport_target`／`swap`／`swap_any`→`step`；`dash`／`leap`／`charge_through`→`dash`；`pull`→`pull`；`push`／`blow_surface`／`shockwave`／`hurl_object`→`push`；`knock_prone`／`topple`→`knockdown`；`heal`／`revive`→`heal`；`shield`／`cheat_death`／`redirect_damage`／`intercept`→`shield` | 同左 | `summon`：`SUMMON_TINT`；`detonate`：被引爆狀態的 `DOT`／`BIND` |
| 14 | 第一個 `apply_status` 的 `status` | 燃燒、中毒、流血→`dot`；冰凍、定身、暈眩、沉默→`bind`；緩速→`slow`；標記→`mark`；虛弱、易傷、恐懼、致盲、挑釁→`curse`；其餘→`buff` | `DOT`、`BIND`、`CURSE`、`STATUS_TINT`（虛弱是 `steel`，減益不用毒綠） |
| 15～20 | `LATE_ACTION` 依序：`create_surface`／`zone`／`clear_surface`→`surface`；`create_obstacle`／`raise_terrain`／`lower_terrain`／`destroy_object`→**`surface`＋染色 `stone`**；`add_stack`→`builder`；`consume_stack`→`finisher`；`dispel`／`steal_buff`→`curse`；`cleanse`、`restore_resource`、`reset_cooldown`、`grant_ap`、`grant_skill`、`extra_reaction`、`rule_change`、`copy_skill`、`leave_form`、`reveal`→`buff` | 同左 | `surface`：`SURFACE_TINT` |
| 21 | `tags` 有 `finisher` | `finisher` | — |
| 22 | 兩個以上 `damage`，或有帶 `condition` 的 `damage` | `combo` | 條件的色（`COND_TINT`，鍵是條件的 `status`，沒有就用 `type`）；沒有條件色時用第二元素 |
| 23 | 有 `damage` | `hit` | — |
| 24 | 其餘 | `buff` | — |

**`spark`**：`variants[]` 裡第一個有 `element` 的那個元素（燧石飛刃的油上火星：閃光染橘）。

代碼 `terrain` 不再輸出（畫法收到舊的 `terrain` 當 `surface`＋`stone`）；`slow` 是第 2 版新代碼（第3批 11 節第 1 點）。`enemy_only` 的招照樣算得出圖。

### 3.4 `SkillIcon` 現在沒有、推導要用的 7 項（第3批 4.5；main 查證）

| # | 欄位 | main 現況 | 用在 |
|---|---|---|---|
| 1 | 效果條件的 `weapon`（`wielding_weapon` 的武器 id） | `IconEffect.condition` 只有條件種類字串 | `prop` 第 2 列 |
| 2 | `effects[].unit`（召喚物 id）、`effects[].form`（化身 id） | `IconEffect` 沒有 | `prop` 第 1、5 列；`tint`（`SUMMON_TINT`） |
| 3 | 效果條件的 `status` | 只有技能層級 `IconCondition.status` | `combo` 的條件色 |
| 4 | `tags`（至少 `stealth`、`martial`、`finisher`、`arcane`、`water`） | 只用來推 `elements`，沒帶出 | `prop` 第 4b、7、8 列；`act` 第 21 列 |
| 5 | `name_zh` | 沒有 | 名稱關鍵字（若改由 `icon_prop` 全面取代關鍵字表就不用；目前仍要） |
| 6 | `variants[].element` | 沒有 | `spark` |
| 7 | `followup.when == delayed` 而且第一段只有護盾 | `link` 與兩段 `effects` 已有，可在後端算 | `act` 第 2 列 |

已有、直接用的：`kind`、`rarity`、`weapon_req`、`elements`、`segments[].shape_id`／`range`、`segments[].effects[].type`／`status`／`surface`、`link`、`modifier.applies_to`、`modifier.changes`（`add_element` 的值）、`icon_prop`。

**若 `art` 在後端算，上面 7 項不必出現在 API**（`icon_of()` 內部讀原始 `skill` 即可）。API 只多帶 `art`；改完重跑 `export_openapi.py` → `pnpm gen:api`，重產 `skill_icons.json`（`python -m tests.narrative.icon_fixture`，IP-1 報告交付 6）與 `skillCards.json`。

### 3.5 建議的測試

- **行為一致**：對 402 招，沒填 `icon_prop` 的招，後端 `art` 和 `qskills_derive.derive()` 逐招相同（`prop`、`motion`、`act`、`tint`、`spark`）；有填的 36 招，`prop` ＝ `icon_prop`（扣掉化身與 `wielding_weapon` 招；目前 36 招裡沒有這兩類，IP-1 報告待決 6），`motion` 照新 `prop` 重算。參考實作在 `docs/art/`（不是套件），測試怎麼引用由開發決定（也可以先用它匯出一份對照 JSON）。
- **不丟例外**：缺欄位、型別錯的草稿（`icon_of({})` 等）照 3.3 的表回傳 `none`／`aura`／`buff`。
- `icon_prop` 不在清單時（第 5 節第 3 點）的行為。
- 內容 digest：這段不改內容檔，規則包雜湊預期不變；若把推導用的表搬進 `content/`（第 5 節第 2 點）會新增內容檔，雜湊與世界日誌的影響：待開發查證。

### 3.6 新道具 ID 前綴

這兩批用到的道具代碼前綴只有 `w`、`el`、`summon`、`form`、`none`，**沒有新前綴**，IP-1 的格式檢查（`ICON_PROP_PATTERN`）不用改。推導會輸出允許清單以外的形制寫法（`w:tome/book`、`w:round_shield/wood`、`w:orb/ball`、`w:staff/scepter`、`w:staff/totem`），那是推導結果、不是 `icon_prop` 的值，不受格式檢查。清單外待補圖的道具（瓶、煙霧彈、吼聲、腳／靴、肩撞、獠牙與黏液；`技能圖示道具清單.md` 第 3 節）之後補圖時若用新前綴，屆時另給增量並註明。

## 4. 一定要做對的重點

每條後面括號是出處（`第3批`＝`Q版小圖示-第3批技能主圖.md`，`第4批`＝`Q版小圖示-第4批徽章與部件.md`，`第4批審查`＝`-審查.md`，`補查`＝`Q版小圖示-前三批真1倍補查.md`，`上手`＝`上手-畫法.md`）。

### 4.1 出圖與貼圖（兩批共用）

1. **貼圖不要縮放、要對齊整數裝置像素（最重要）**：主圖 `render(def, a, res)` 的 canvas 邊長是 `round(a × res)`，而 `a = size × (1 − 2 × pad)` 幾乎都不是整數（六角框 24px：`a`＝17.04、貼在 3.48）；圓片圖樣 canvas 是 16 個裝置像素卻被縮到 15.7、貼在 1.3。用 `drawImage(cv, x, y, a, a)` 縮放貼上會重新取樣、1px 外框被抹掉（化身 24px 整塊糊掉、九宮格與陷阱像被平滑縮小）。一律用 QI-1a 的 `blit()`（照 canvas 原尺寸、左上角四捨五入到整數裝置像素、以原格子為中心）。主圖、`drawChip` 內的圖樣、`skeletonBadge`、組裝列 `chipTile`／`tileCanvas`、卡片小圖都照這樣做；**ctx 的原點要在整數像素上**（`paint()` 的 `unitPx × res` 是每單位幾個裝置像素）。（第3批 11 節第 3 點、16.1；第4批 8 節第 1 條；補查第 2 版複審）
2. **畫布＝顯示尺寸 × 2、CSS 顯示原尺寸、不靠 CSS 縮放**：照 QI-1 的決定（`PhaseQI-1計畫.md` 0.0 第 1 點）。組裝列 30／18、工坊選項 26／20／22、卡片小圖 16／18／13 都直接畫在顯示尺寸。（上手 4.1）
3. **外框粗細**：主圖用**整個圖示邊長**算 `outlinePx(size)`（不是主圖格的邊長）；圓片、徽章、卡片小圖的圖樣 ≤14px 不包外框（`ow: 0`），其餘 `outlinePx(圖樣px)`。外框色 `#16121a`。（`qIconsSkills.js` `paint()`；`qIconsParts.js` `glyph()`；上手 2.1）
4. **簡化程度照圖樣本身的大小**：圓片裡的圖樣＝直徑的 78%（`r × 1.56`），圖樣格再大 1/3（`BOX = 48/36`）。18px 圓片的圖樣只有約 12px、56 角落約 10px，都走 `o.tiny`（只留一個主體、不包外框）。`def(cat, id, 圖樣px)` 吃的是圖樣 px，不是圓片 px。卡片小圖圖樣 `min(14, px × 0.84)`。（第4批 1 節尺寸、8 節；上手 2.8）
5. **快取鍵**：主圖 `prop|motion|act|tint|el|el2|spark|kind|rarity|px`，再加級別（`main`／`mid`／`full`）與內部解析度；組裝圖示另含 `SkillIcon` 的部件。`def()` 與 `boxOf()` 各有快取，`boxOf()` 第一次會畫兩張 192px 離屏畫布。（第3批 11 節第 3 點）

### 4.2 主圖（第 3 批）

6. **一張圖三層**：`pre`（出手線、殘影、弧箭頭、光暈，不包外框）、`d`（道具＋記號，包外框）、`post`。道具擺位一律走 `boxOf()`：量外接框（大、小兩種簡化取聯集）→ 長邊縮到指定單位、中心放到指定點（`def()` 的 `pos()`）；記號位置用 `corner(side, k)`。主圖格留白 `PAD`：方 9%、盾 13% 並上移 2.5%、圓與六角 14.5%、齒輪 15.5%。（第3批 11 節第 3 點；上手 2.7）
7. **≤40px 不畫核心效果圓片**；主圖 96、56、48、40、28、24 是同一張圖，≤24px 只省小零件。（第3批 1 節、11 節第 3 點）
8. **元素底**：`base()`＝深色整片＋圓心 (50,51)、半徑 36 的亮一階圓（`mix(深, 亮, 0.72)`），不用漸層、不畫紋理；有第二元素時圓換成第二元素的色（`mix(B2深, B2亮, 0.8)`），使用者 11-12 同意算在「兩階色塊」內。色值在 `BASE`。（第3批 1 節、4.4；`美術PM交接.md` 0.00 使用者答覆第 5 點）
9. **武器道具**：呼叫第 1 批 `def(look).d`（**裝備格構圖**、`badge: false`），不另畫；拳套沒寫形制時用鐵拳（`SKILL_FORM = { fist: "knuckle" }`）；火槍、霰彈槍 ≤24px 多疊加粗的槍托折角與黃銅箍（`GUN_SMALL`）。材質見 2.4 第 3 列。（第3批 11 節第 2、3 點）
10. **記號的排法**（第 2、3 版）：
    - `tipMark`：傷害、追擊配 `TIP_KINDS`（斧、錘、矛、鐮、弩、杖、弓、火槍、霰彈槍）時，道具縮到約 32 單位往左下退、白閃光 0.45 倍放作用端外側（`TIP_B`）；持續傷害配武器只留一顆 0.56 倍的滴或小火。
    - `side: "br"`：對目標的大記號配 `HEAD_KINDS`（斧、錘、矛、鐮、杖、弩、**弓、火槍、霰彈槍、拳套**）與召喚記號配任何武器 → 記號放右下 (34,32.4)，武器往左上讓開（預設 20.6,21／長邊 31；`BR_POS`：弓 19.8,20.2／32.5，火槍、霰彈槍 19.8,19.8／33.5，拳套 18.2,18.8／29；召喚記號一律用預設）。**單純傷害 `hit` 不走 `br`**。
    - 記號和元素道具同色時提亮一階（主色混一半白）。
    - 數字都在 `pos()`、`markK()`、`markAt()`、`drawMark()`。
    （第3批 4.4b、11 節第 2 點、15.6）
11. **記號表 23 個**（含 `slow`、不含 `terrain`）；染色多 `stone`。地面效果 `ACT.surface.d` **依染色分六種外形**：`stone` 兩塊石頭、`holy` 光圈加光點、`steel`／`shadow` 兩團雲、`ice` 薄冰加冰刺、`fire` 暗紅餘燼上三撮火（餘燼用固定的暗紅，不跟著同色提亮）、其餘是液體（一灘加一滴）。（第3批 11 節第 2 點、15.6）
12. **出手線**：`shot` 配弓弩槍**不畫任何東西**；元素道具拖彗尾；飛刃與 `thrust` 共用 `wedges()`；`thrust` 配武器時楔形用 `dim`（元素底亮色混 22%）、亮芯 0.4，其餘用 `soft`、0.6。瞬步的殘影是把道具畫到離屏畫布再 `source-in` 染色（一招多兩次離屏繪製）。（第3批 4.2、11 節第 2、3 點、15.6）
13. **真 1 倍修正的畫法變動**：雙匕首配右上記號（`side: "tr"`）擺位 `{ x: 19.4, y: 28.6, size: 33 }`；巨人在 `o.small` 時手臂用 `halo()` 包外框；餘燼幼蜥在 `o.small` 時身體 `#ffb44e`、亮斑 `#fff3a8`；守護靈在 `o.small` 時光環 `#ffd23f`、線寬 3.2、`ellipse(24, 7.7, 9.6, 3.4)`。（第3批 11 節第 3 點、16.2）
14. **不要畫兩次同一件事**：道具已是召喚物或化身不畫召喚／化身記號；元素道具配同元素的持續傷害只畫大一號的道具；連鎖的單純傷害、元素道具的單純傷害不另畫記號；沒有道具的招記號放大放正中。這些在 `def()` 裡，照搬即可，不要「補」記號。（第3批 1 節、上手 2.7）

### 4.3 56／96 組裝（第 4 批）

15. **三級**：`main`（≤40，只有主圖）、`mid`（技能卡：主圖照第 3 批的留白＋右下骨架徽章 (83,83) 半徑 15、稀有度色環＋被動／反應左上觸發時機 (17,17) 半徑 15、白環）、`full`（96 工坊：主圖盒方框 62／其他框形 56 單位、中心 y 41／43）。**`SkillCardView` 的 56px 從強制 `small` 改成 `mid`**——使用者看得到的變化：卡片圖示右下從核心效果圓片變成骨架徽章，被動／反應左上多觸發時機。（第4批 5 節、8 節；第4批審查兩版「美術 PM 的決定」）
16. **組裝三處改動**（`full`，和現行版位不同）：
    - **觸發時機**（原本是主圖）放左上 (15,15) 半徑 12.5、白環；有觸發時元素片讓到 (12,39) 半徑 8。
    - **接續記號**（原本在斜切線中央）排進底部效果列、放在第二段第一個效果前面（沒有就放最後），半徑 9、色環青色 `LINK_RING #7fd8ff`，和效果圓片的淡白環分開。
    - **沒有元素、以及物理的技能都不畫元素片**（物理那一顆是白四芒閃光，和效果列的傷害圓片同圖）。物理技（瞬步背刺、狂野之刃、燧石飛刃）左上角是空的，是預期。
    - 移植時**請確認沒有別處依賴原本的版位**（元素片在左上、接續在斜切線中央、物理有元素片）。
    （第4批 5 節、8 節；第4批審查「美術 PM 的決定」第 2 條）
17. 其餘版位照現行：右上代價 (85,15) 半徑 11、第二個 (85,36) 半徑 8，環色 `COST_RING`；左下條件 (14,86) 半徑 11、環 `#ffe9a8`；右下骨架 (86,86) 半徑 11；底部效果列算法照現行 `effectRow`（核心 11.5、其餘 8.5，放不下就縮，最小 4.5）。（`qIconsParts.js` `paintIcon()`）

### 4.4 部件小圓片、徽章、形狀、卡片小圖（第 4 批）

18. **`render/skillParts.ts`**：`EFFECT`、`COND`、`COST_ART`、`TRIG`、`LINK` 與 `modifierChangePart` 的圖樣換成 `EFFECT`、`COND`、`COST`、`TRIG`、`LINK`、`CHANGE`（座標以 0,0 為中心、半徑約 10）。Q 版每個圖樣自帶顏色，`Part.color` 只剩色環用（代價的環色在 `COST_RING`）。`drawChip` 的圓底與色環不動，裡面改呼叫 `paint()`。`KNOWN_PARTS` 的測試照新表。（第4批 8 節）
19. **效果帶狀態**時查 `STATUS`（32 個，技能會施加的全部，含 `shield` 效果帶的 `shielded_charged`）；32 個以外照現行 `statusGlyph()`。**效果帶表面**時油用 `oilPool`（琥珀黃一灘加一滴、白反光），其他呼叫第 3 批 `ACT.surface`（依表面換外形，8 種）。`effectPart` 的 `teleport_target`、`swap_any` 和 `swap` 同圖（`EFFECT_ALIAS`）。（第4批 1 節、8 節）
20. **修正內容右上的小箭頭照數值正負**（`signArrow`）：正＝朝上橘黃、負＝朝下青色，沒有數值當正（例：冷卻 −1、AP −1 朝下；傷害 +150‰、命中 +1、範圍 +1 朝上）。補上 `form_upkeep_permille`、`form_entry_permille`。（第4批 2 節修正內容、8 節；審查第 1 版可修「修正內容箭頭寫死」）
21. **觸發的 5 個暫代（`TRIG_ALIAS`）**：名詞表有、現行畫「?」、**目前沒有招用到**的 `targeted_by_melee`→`hit_by_melee`、`targeted_by_attack`→`hit_by_attack`、`enemy_moves_in_range`→`enemy_enters_adjacent`、`ally_hit_in_range`／`kin_hit_in_range`→`ally_hit_adjacent`。**這是暫代**（「被瞄準」指到「被擊中」語意不同）；第一招用到時請通知美術補畫。程式裡請留註解標明暫代。（第4批 8 節；第 9 節第 7 點）
22. **`render/skillGlyphs.ts`**：`skeletonGlyph` 換成 `SKELETON` 16 個（`modifier`、`passive`、`combo`、`sacrifice` 現行同一個空心圓，現在各有圖；打擊是亮色劍、範圍是衝擊環、位移是雙 V）。圖示左上的元素片改用 `ELEMENT`（物理那顆只在清單裡，組裝不畫）。（第4批 1 節、8 節）
23. **形狀 `SHAPE`（組裝列 `shapeTile`）**：命中格**固定橘色 `#ffb23a`、不再染元素色**、放大；沒打到的格縮小、用 `UNLIT #3a3f4e`；自己＝米白圓、隊友＝綠圓（單位畫成圓、格子畫成方）；物件＝褐色方塊；兩個單位之間一個白色雙頭箭頭。臂長 ≥2 的大十字**沒有畫**，沿用 3×3 十字。（第4批 2 節形狀、8 節）
24. **組裝列的骨架**：深色圓底 (50,50) 半徑 40、沒有色環、圖樣 62 單位（現行 `skeletonTile` 是放大 3 倍）。（`qIconsParts.js` `chipCanvas()`）
25. **技能卡小圖 22 個**（`ui/SkillCardGlyphs.tsx`）：換成 `CARD`（`cardCanvas(id, px, zoom, { pinned })`），圖樣 `min(14, px × 0.84)`、不包外框；`damage` 的元素色照現行 `elementColor` 傳進去。**7 個換題材**（源力晶石、觸發鈴、延遲沙漏、次數票券、移動靴子、狀態旗、傷害閃光），美術 PM 已定採用。**圖釘收 `pinned`**（預設 `true`）：已釘＝紅頭；未釘＝同外形灰鋼色、整顆 55% 不透明（現行是 `currentColor` 變色，改成傳參數；`BattleLogDock`、`UnitInfo`、`SkillCardView` 三處都要接）。（第4批 2 節卡片、8 節、9 節第 4、5 點）
26. **刻意同圖、不要「修」**：打擊徽章＝條件 `wielding_weapon`；位移徽章＝效果 `dash`；`consume_stack`＝代價 `stacks`；骷髏＝`on_kill`（觸發與接續）；沙漏＝代價延遲、接續延遲、卡片延遲；靴子＝移動過、移動後、卡片移動；旗＝施加狀態、卡片狀態；吊牌＝條件與觸發；`grant_pierce`＝`charge_through`；骰子＝效果與代價；驅散＝增益箭頭被劃掉。六個姿態狀態同一個六角臂章、靠底色與紋章分。（第4批 3 節）
27. **32 種狀態圖樣要能給第⑤批直接用**：第⑤批的狀態框與頭頂直接呼叫這 32 個（`qIconsStatus.js` 依賴 `qIconsParts.js`），搬的時候請做成獨立可呼叫的表（`STATUS[id].d`），不要寫死在圓片裡。（`美術PM交接.md` 0.00；上手 2.9）
28. 依賴：`qIconsParts.js` 呼叫 `qIcons.js` 的 `ART.status`、`ART.hud`（包 `from48()`）、第 3 批的 `ACT`、`ELEMENT`、`TINT`，與 `blit`；**不再呼叫 `W.swordArt`**（亮色劍在 `bladeSword`）。（第4批 8 節）

## 5. 內容、後端與要決定的事

| # | 項目 | 誰決定 | 說明 |
|---|---|---|---|
| 1 | 推導在後端算（`SkillIcon.art`），或把 7 項原始欄位帶給前端 | **開發 PM** | 美術建議後端算（第 3.2 節）；只有一份規則、前端只畫 |
| 2 | 名稱關鍵字表、召喚物分組表、狀態分類表要不要放 `content/`（內容即資料） | **開發 PM**；若放，維護者由**玩法 PM** 定 | 第3批 11 節第 1 點建議放 `content/` 由玩法 PM 維護；不放也不擋移植（照腳本寫成 tuple 常數） |
| 3 | `icon_prop` 不在允許清單時 | **開發 PM**（IP-1 報告待決 5） | 美術建議執行期靜默退回推導、不報錯（`技能圖示道具清單.md` 第 0 節）。`icon_of()` 沒有內容庫，要嘛把清單當常數讀進來、要嘛前端遇到不認得的代碼退回；手寫內容載入時已擋、三個入口已清掉，實際上不會出現 |
| 4 | 化身招與 `wielding_weapon` 招填了 `icon_prop`，資料檢查要不要擋 | **開發 PM**（IP-1 報告待決 6） | 推導上不生效（3.3 第 2b 列）；現在 36 招沒有這兩類，不擋移植 |
| 5 | 技能卡 `compact` 時 48px 用哪一級 | **開發 PM** | 樣張只定義了 56 的 `mid`。美術建議 48 也用 `mid`（同一張卡兩種大小一致）；若改用 `main`，報告寫明 |
| 6 | 卡片小圖的做法（SVG 換 canvas，或照 Q 版重畫 SVG） | **開發 PM** | 美術要求的是結果：和 `cardCanvas()` 同圖、≤14px 不包外框、真 1 倍硬邊 |
| 7 | 狀態卡上的表面圖 `surfaceTile()`（`ui/StatusCardParts.tsx`）要不要一起換成 Q 版的 8 種表面 | **開發 PM** | 表面圖樣是第 4 批的；美術建議一起換（同題材同形），狀態框那兩個（`statusTile`、`statusIconTile`）留到第⑤批 |
| 8 | 切段與上線順序 | **開發 PM** | 主圖換成 Q 版後，若四角圓片、徽章仍是現行畫法，會兩種畫風並排（第3批 11 節第 3 點）：**主圖、組裝、部件請同一次上線**。後端段可以先做（只多一個欄位，前端不畫就沒有變化） |
| 9 | 內部解析度 | 不用決定 | 照 QI-1（固定 2；開發頁可切 1） |

**需要玩法 PM 決定的：只有第 2 點（若表放進 `content/`，由誰維護）。** 推導規則本身是美術的畫法規則，使用者已同意（第3批「都照建議」）。後端除了第 3 節以外不用動；不改 `content/skills/`。

## 6. 驗收（美術 PM 會看的截圖）

每項都要有截圖；實機到不了的用開發頁畫出來，並在報告寫「實機未看」。瀏覽器測試靜音（網址加 `?mute=1`）；截圖用裝置像素比 1 拍（`--force-device-scale-factor=1`）。

**最小尺寸一律交兩種**：(a) **DPR 2**（遊戲現在的內部解析度）；(b) **真 1 倍**（canvas 寬高＝CSS px）。兩種都用最近鄰放大 6 倍（`image-rendering: pixelated`；放大 6 倍的一個像素在截圖裡是 6×6 的純色方塊）。

**截圖格式（使用者 11-12 選 A，原話「A」；`開發PM交接.md` 6.5.2）**：只有**真 1 倍／最近鄰放大的特寫**可以用 PNG（單張 ≤300 KB）；情境圖、版面一律 jpg 品質 80（單張 ≤300 KB）。**每段 ≤10 張**（PNG 也算），放 `docs/art/shots/<段>/`；項目多時拼成對照圖（同一張裡左邊遊戲端、右邊樣張截圖）。下面 13 項若一段放不下，照切段分配，報告列出每項在哪一張。

| # | 要看的 | 尺寸 | 對照的樣張截圖（`docs/art/` 下） |
|---|---|---|---|
| 1 | 主圖：402 招的全部不同長相（約 322 個） | 24、28 真 1 倍＋DPR 2 | `shots/qicons/true1x/skills-24-01.png`～`-16.png`、`skills-28-01.png`～`-16.png`；總排 `shots/qicons/skills-b.png` |
| 2 | 主圖分類總表：道具 56（武器、副手、元素、召喚、化身各至少一招）、出手 9、記號 23 | 40 DPR 2（含 24 的最近鄰放大） | `closeup/qicons/skills/a-weapon.png`、`a-off.png`、`a-el.png`、`a-summon.png`、`a-form.png`、`a-motion.png`、`a-act1.png`、`a-act2.png` |
| 3 | 六招入門招（瞬步背刺、狂野之刃、淬毒箭、燧石飛刃、火焰箭、火花連鎖） | 40、28、24 DPR 2 | `closeup/qicons/skills/starters.png` |
| 4 | 點名款特寫：化身 10 款、產下幼蜥、召喚守護靈、雙牙（24 真 1 倍）；弓槍配大記號 12 招＋散彈驅離；地面效果六種外形、拳套配記號、直線突刺 | 40、28、24 真 1 倍＋DPR 2 | `closeup/qicons/skills/t1x-fix.png`、`v3-bow-gun.png`、`v3-surface-fist-thrust.png` |
| 5 | 實例 78 招：現行｜Q 版 | 40、24 DPR 2 | `shots/qicons/skills-real.png` |
| 6 | `icon_prop` 36 招：每招的道具＝填的值（錘 3、拳套 13、匕首 6、塔盾 2…；`技能圖示道具清單.md` 第 2 節） | 40 DPR 2 | 樣張沒有這一張（參考實作沒讀 `icon_prop`）；道具造型對照 `closeup/qicons/skills/a-weapon.png`、`a-off.png`、`a-el.png`、`a-summon.png`、`a-form.png` |
| 7 | 部件小圓片全部：徽章 16、效果 51、表面 8、狀態 32、條件 17、代價 6、觸發 22（含 5 個暫代各一）、接續 6、形狀 13、修正內容 21、元素 9 | 組裝列 18 真 1 倍＋DPR 2；30 DPR 2 | `shots/qicons/true1x/parts-chip18-01.png`～`-11.png`；`closeup/qicons/parts/a-skeleton.png`、`a-effect1.png`～`a-effect3.png`、`a-surface.png`、`a-status1.png`、`a-status2.png`、`a-condition.png`、`a-cost.png`、`a-trigger1.png`、`a-trigger2.png`、`a-link.png`、`a-shape.png`、`a-change.png`、`a-element.png`；第 2 版改過的款 `v2-redraw-1.png`、`v2-redraw-2.png`、`v2-shape.png`、`v2-change.png`、`v2-status-new.png` |
| 8 | 技能卡小圖 22 個＋圖釘兩態 | 16、18、13 真 1 倍＋DPR 2 | `shots/qicons/true1x/parts-chip18-10.png`、`-11.png`；`closeup/qicons/parts/a-card1.png`、`a-card2.png` |
| 9 | 技能卡 56 `mid`：24 招（含被動、反應各幾招）；另 48 `compact` 幾招 | 56 真 1 倍＋DPR 2；48 DPR 2 | `shots/qicons/true1x/parts-icon56-01.png`～`-03.png`、`parts-corner56-01.png`、`-02.png` |
| 10 | 96 `full`（工坊）：24 招。要看得出三處改動——觸發左上、接續青環在效果列、物理與無元素沒有元素片（瞬步背刺、狂野之刃、燧石飛刃左上空） | 96 DPR 2 | `shots/qicons/parts-asm-1.png`、`parts-asm-2.png` |
| 11 | 修正內容箭頭正負：冷卻 −1、AP −1 朝下青色；傷害 +150‰、範圍 +1 朝上橘黃 | 30 DPR 2；18 真 1 倍 | `closeup/qicons/parts/a-change.png`、`v2-change.png` |
| 12 | 實機畫面，每處一張（1.3 節的表）：技能列 40 與次要列 28、技能磚 40、配招 24、隊伍 24、召喚面板 28、變奏列 28、靶場選職業 40、技能卡 56（含常駐行、效果行、組裝算式 30／18、圖釘已釘與未釘）、精簡卡 48、戰鬥紀錄與單位資訊的圖釘、狀態卡上的 `ChipGlyph`／`EffectGlyph`、工坊 96／40／28＋組裝算式＋選項 26／20／22 | 實機 | `shots/qicons/skills-scene.png`、`skills-scene@2x.png`、`parts-scene.png`、`parts-scene@2x.png` |
| 13 | 不動的確認：單位頭頂狀態（`statusTile` 24）與狀態卡狀態（`statusIconTile` 20）和改之前相同 | 實機或開發頁 | 改之前的截圖 |

另外請在報告寫明：(a) 第 2.2 節第 4 點的對照方式與結果（和樣張逐像素相同，或只差武器道具的材質色）；(b) 後端推導和 `qskills_derive.derive()` 的逐招比對結果（不同的招數與原因）；(c) 現行的 `paintBackground`、`elementTexture`、`drawMotif` 系列、`SkillCardGlyphs.tsx` 的 SVG 是否已拿掉、有沒有別處還在用；(d) 第 4.3 節第 16 點「別處依賴原版位」的查證結果。

## 7. 待決／已知未修（都不擋移植）

各批審查最後一版的「可修」都留到之後順手，移植照現在的樣張即可；之後改了樣張再另給增量（改的時候用 `--hash skills`／`--hash parts` 確認只有那幾款變）。

**第 3 批（第 3 版複審的可修）**
- 紀錄檔第 6、9 節楔形那句照圖改（只動文件，不影響移植）。
- 煙霧彈畫成弓加雲：屬 `icon_prop` 範圍，等清單外道具「投擲彈」補圖。

**真 1 倍補查（第 2 版複審的可修，都是 24px）**
- 化身為巨人偏方塊：頭再大一點或肩線收圓。
- 雙牙刃偏暗、記號佔半張：刃換亮鋼一階，或記號縮到約六成。
- 產下幼蜥有點像小人：改側面（頭朝右、尾巴拖長）或把底色壓暗一階。

**第 4 批（第 2 版複審的可修 7 條）**
1. 範圍徽章對嘲諷：18px 都是「四塊橘色圍一圈」，四段環改成連得起來的弧或亮芯放大。
2. `on_natural_20` 18px 沒有「20」、比現行難認：改畫粗體「20」為主。
3. 仍頂到色環的：`flanked` 紅三角、`extra_reaction`／`grant_skill` 加號、`delayed_damage` 火花、接續 `after_gather` 兩個大三角，縮到 0.85～0.9。
4. 96 完整版的塔盾猛擊：條件 `wielding_weapon` 與打擊徽章是同一把劍，一張圖兩把（只在工坊出現）。
5. 姿態紋章：堅壁的磚牆、鐵壁的鐵條在 18px 真 1 倍糊成格紋與條紋。
6. 石膚 18px 像「預設頭像」：裂紋加粗或肩上加石片缺角。
7. 紀錄檔與 `closeup/qicons/parts/v2-shape-change.png` 舊檔（文件整理，不影響移植）。

**第⑤批複審帶出來的（算第 4 批的可修）**
- 效果「分擔傷害」（`redirect_damage`，Y 形分岔箭頭）和狀態「靈魂連結」（第⑤批畫成雙環）同題材不同形；之後把效果圓片統一成雙環（`Q版小圖示-第5批狀態-審查.md` 可修 7 與「靈魂連結與『分擔傷害』要不要統一」）。

**清單外道具待補圖**（`技能圖示道具清單.md` 第 3 節）：瓶（優先，燈油瓶現在畫成岩石）、煙霧彈、吼聲、腳／靴、肩撞、獠牙與黏液。補了圖會更新清單、通知玩法 PM，另給增量（新前綴的話一併註明，見 3.6）。

**已知、交使用者時已講明的（不是缺陷）**
- 沒寫武器的近戰一律畫劍、遠程一律弓；`icon_prop` 已讓 36 招畫出正確道具，其餘照推導。
- ≤40px 看不到被動與反應的觸發時機（只剩框形）；56 卡片與 96 工坊才有。複合技、蓄力技的第二段與形狀細分不顯示在圖示上（看組裝算式）。
- 併成同一記號、只靠顏色分的：冰凍／定身／暈眩／沉默同一把鎖；恐懼、致盲、驅散、偷取同一個朝下箭頭；中毒與流血同形；圖騰三種、靈五種只差顏色；沒有道具的約 30 招只有一個大符號（四招治療同圖）。圓片（96 效果列、組裝算式）各自分開。
- 弓、弩、槍的單體技不畫「射出」線；武器的直線技在 28／24px 幾乎看不出直線。
- 仍像別的東西：陷阱像釘板、懷錶 24px 像獎牌、灰燼誓約與火牆 24px 像插蠟燭的蛋糕、聖光印地像光環、燈油瓶略像一坨醬；石碑像墓碑、下陷像下載、聚集像蝴蝶結、恐懼是鬼、落單像鐘罩。
- 元素底的漸層與紋理沒了；第二元素是中間圓的顏色。
- 技能卡 56 右下從核心效果圓片變成骨架徽章；範圍徽章換成衝擊環（九宮格只留給形狀）；位移、衝鋒是拉開的雙 V；形狀命中格固定橘色；卡片小圖 7 個換題材，HUD 源力之後對齊；圖釘未釘在卡片深底上很淡。
- 5 個觸發是暫代圖。
- 樣張只在樣張頁看過，沒有實機圖；遊戲端固定 DPR 2，真 1 倍是最壞情況。
