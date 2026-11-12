# Phase QI-2b 報告：Q 版技能圖示｜搬畫法（新檔＋開發頁，不接到遊戲畫面）

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-2計畫.md`（QI-2b 部分；第 0.0 節為開發 PM 定稿）。依據 origin/main `8d4b282a`。未 push。
> QI-2a（後端 `art`）還沒進 main：開發頁與測試的主圖代碼**暫時**用參考實作算出的資料（見第 1 節 B4、待決 1）。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| B1 主圖 | 新 `client/src/render/qIcon/skills.ts`：由 `docs/art/sample/qIconsSkills.js` 逐行搬（`ELEMENT`、`SUMMON`、`FORM`、`MOTION`、`ACT`、`TINT`、`BASE`、`BASE_ZH`、`RARITY`、`PAD`、`TR`/`BL`、`def(look)`（`pre`/`d`/`post`/`meta`、`boxOf`、`pos`、`corner`、`markK`、`markAt`、`drawMark`、`tipMark`、`side: "br"/"tr"`、`wedges`、瞬步殘影的離屏 `source-in`）、`base`、`paint(ctx, look, size, res, { frame })`、`canvas`、`list`）。武器道具＝`qWeaponDef(qResolve(resolveGear({ kind, form, material })))`，材質名照樣張 `propOf()`（劍、巨劍、火槍、手槍、雙手槍 `steel`），色照 `material.ts`；拳套沒寫形制用鐵拳、`GUN_SMALL` 照搬；外框用 `skillGlyphs.ts` 的 `framePath`；貼圖一律 `core.ts` 的 `blit`。不認得的代碼照樣張退（召喚→`spirit`、化身→`bear`、元素→`arcane`；`w:` 不認得的種類由 `resolveGear` 退直劍）。`clearQSkillDefs()` 清快取（測試換畫布用） | `dbdba09c` |
| B2 部件 | 新 `client/src/render/qIcon/parts.ts`：由 `qIconsParts.js` 逐行搬 `SKELETON` 16、`EFFECT` 51（`EFFECT_ALIAS` 2）、`SURFACE` 8（油 `oilPool`）、`STATUS` 32（獨立表，D6）、`COND` 17、`COST` 6（`COST_RING`）、`TRIG` 22＋`TRIG_ALIAS` 5（檔頭註明**暫代**）、`LINK` 6（`LINK_RING`）、`SHAPE` 13（`UNLIT`）、`CHANGE` 21（`signArrow`）、`ELEMENT` 9、`CARD` 22；`entry`、`def`、`glyph`、`paint`、`chip`、`chipCanvas`、`cardCanvas`、`cardPx`、`paintIcon`（三級）、`canvas`、`list`、`hooks.status`（32 種以外的狀態由呼叫端掛，2c 傳 `statusGlyph()`）。**樣張的 `partsOf` 不搬**：`paintIcon` 收純資料的 `QParts` | `dbdba09c` |
| B2 轉換 | 新 `client/src/render/qIcon/partsAdapter.ts`：`toQParts(icon, partsOf(icon))`（遊戲端 `skillIcon.ts::partsOf` → `QParts`；從原始資料補 `seg`、修正內容的 `value`／`on_hit_effects` 底圖）、`skillLook(icon, art)`（沒有 `art` 時 `NO_ART`＝`none`／`aura`／`buff`）。只**型別匯入** `skillIcon.ts`，2c 讓 `skillIcon.ts` 匯入 Q 版畫法時不會循環 | `dbdba09c` |
| B3 `qIcons.js` 片段 | 新 `client/src/render/qIcon/legacy48.ts`：`drop`（H.drop）、`totemPole`（W.totemPole＝`SKILL_V1.skill_plant_totem.d`）、`ART.status` 4 款（倒地、冰凍、加速、恐懼）、`ART.hud` 4 款（AP、法力、耐力、移動）——兩個樣張實際用到的全部 | `dbdba09c` |
| B4 開發頁 | 新 `client/dev/skillicon-gallery.html`＋`client/src/dev/skillIconGallery.ts`（參數說明在檔頭）：`?px=`（可多個）、`&res=1,2`、`&zoom=`、`&level=main|mid|full`、`&set=skills|props|motions|acts|starters|named|iconprop|real|parts|card|change|list`（逗號接多段）、`&cat=&id=`、`&ids=`、`&skills=`、`&from=&n=`、`&label=0`、`&old=1`；`window.__qiSkillDev`（`main`、`icon`、`chip`、`card`、`looks`、`partList`、`framePath`、`M`、`MATERIAL`）。**暫時資料** `client/src/dev/fixtures/qi2bTempArt.json`：用 `docs/art/sample/tools/qskills_derive.py` 對 402 招逐招 `derive()`，再照需求 3.3 第 2b 列套 `icon_prop`（化身、`wielding_weapon` 招不套；`motion` 用新道具重算；`none`＋`NEEDS_PROP`→`el:arcane`），附招名與 `enemy_only`；頁面上方標「暫用參考資料」。fixture 帶 `art` 時一律用 fixture | `a212f4e8`、`24774440` |
| B5 測試 | 新 `client/src/render/qIcon/qIconSkills.test.ts`（T-B1～T-B7，18 項） | `a212f4e8` |
| B6 對照與截圖 | 第 4 節；`docs/art/shots/qi2/` 10 張 | `24774440` |
| B7 | 本報告、上手筆記 | 本 commit |

**沒有改 `core.ts`、`weapons.ts`、`armor.ts`，也沒有加任何匯出**（用到的都已是匯出）。

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 8.1-1 | 第 7 節 T-B1～T-B7 | 過：`src/render/qIcon/qIconSkills.test.ts` 18 項。T-B1（402 招的 art 都在 TS 表；`w:` 取到第 1 批那一款、形制相同；`def()` 沒退回）；T-B2 兩項（數量 16／51／53／8／17／6／22／5／6／13／21／9／32／22；名詞表狀態 118、表面 8、觸發 27、條件 17、效果 53 與 `KNOWN_PARTS` 都有圖或明確退回；5 個暫代觸發沒有招用到）；T-B3 兩項（主圖 24／28／40 × 五種框 × res 1、2，組裝 48／56 mid、96 full；圓片 18／20／22／26／30、卡片 13／16／18——用追蹤變換的假畫布，每個 5 參數 `drawImage` 都不縮放、左上角在整數裝置像素）；T-B4 三項（主圖外框＝`outlinePx(整個圖示邊長)`；圖樣 ≤14px 不包外框；`small`／`tiny` 依圖樣 px，18px 組裝列圓片的圖樣 11.79px → tiny）；T-B5 三項（有箭頭的 9 個鍵；實際修正技 changes 逐筆；點名冷卻 −1、AP −1 朝下，傷害 +150、命中 +1、範圍 +1、推距 +1、沒有數值朝上）；T-B6 四項（main 沒有圓片；mid 只有 (83,83) r15 與被動／反應 (17,17) r15；full 觸發 (15,15) r12.5、元素片 (12,39) r8、接續青環 `#7fd8ff`、徽章 (86,86) r11；瞬步背刺、狂野之刃、燧石飛刃沒有元素片）；T-B7 三項（402 招 × 24／40 × res 1、2 與全部部件 × 18／30 畫兩次相同；不認得的代碼、缺欄位、402＋50＋工坊示範的 full 組裝都不丟例外） |
| 8.1-3 | 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（292 檔、3640 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告） |
| 8.1-3 | 快照 | `render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts` 在整包測試通過，`git status` 乾淨（快照沒變） |
| 8.1-4 | 遊戲畫面不變 | `git diff --stat 8d4b282a..HEAD -- client/src client/dev`：只有 8 個新檔（`render/qIcon/skills.ts`、`parts.ts`、`legacy48.ts`、`partsAdapter.ts`、`qIconSkills.test.ts`、`dev/skillIconGallery.ts`、`dev/fixtures/qi2bTempArt.json`、`client/dev/skillicon-gallery.html`），沒有改任何既有檔；`core.ts`、`weapons.ts` 未動 |
| 8.1-7 | 截圖 | 10 張，單張 ≤ 294 KB；×6 特寫 PNG、其餘 jpg 80；裝置像素比 1 拍（第 4 節） |
| 8.1-8 | (a) | 第 4 節 |
| — | 相關測試 | `vitest run src/render/qIcon/ src/test/importCycles.test.ts`：4 檔 67 項過（含 1a、1b 的測試） |

## 3. 改寫的既有測試、快照

沒有改任何既有測試；快照沒有變動。

## 4. 需求第 6 節 (a)、截圖、實機未看

**(a) 和樣張逐像素對照**（QI-1a 做法）：自己的 vite（5270）開 `skillicon-gallery.html?set=none`，同一頁從自己的靜態伺服器（8131，帶 CORS）抓 `qIcons.js`、`qIconsWeapons.js`、`qIconsSkills.js`、`qIconsParts.js` 原始碼，**載入前**把 `qIcons.js` 的 `M`（鋼、鐵、木、皮）與 `qIconsWeapons.js` 的 `MAT`（鐵、鋼、銅）換成 `material.ts` 的色（`PW` 在載入時就算好，所以要改原始碼、不能載入後改物件）；`window.AssembledIcon = { framePath: 遊戲端 framePath }`（外框照遊戲端，需求 2.4 第 4 列）。兩邊畫同一份 `look`／`SkillIcon`、同尺寸與 `res`，交錯著畫、`getImageData` 逐像素比（每類一頁剛載入的頁面）。

| 比對 | 組數 | 0 像素不同 | 不同的 | 最大像素數／色階差 |
|---|---|---|---|---|
| 主圖 402 招 × 24、28、40 × res 1、2（樣張 `QIconsSkills.canvas`） | 2412 | 2394 | 18 | 142 px／54 |
| 組裝 402 招 × mid 56、mid 48、full 96 × res 1、2（樣張 `QIconsParts.canvas`，用它自己的 `partsOf`；我方 `toQParts(partsOf)`） | 2412 | 2394 | 18 | 391 px／54 |
| 部件 201 個（12 類扣卡片）× 18 res 1、18 res 2、30 res 2（`chipCanvas`） | 603 | 603 | 0 | — |
| 卡片小圖 22＋圖釘未釘 × 16、18、13 × res 1、2（`cardCanvas`） | 138 | 138 | 0 | — |

- 不同的 18＋18 組全是**同 3 招**：碎甲重擊 `skill_armor_breaker`、碎冰擊 `skill_icebreaker`、碎岩擊 `skill_rock_smash`，道具都是 `w:hammer`。原因是 QI-1b 美術定的錘柄亮一階（`weapons.ts` 的 `HAMMER_SHAFT #a06a36`，樣張 `#6a4420`；色階差 R 0xa0−0x6a＝54 正好是最大差），屬「武器道具的材質色」類，不是搬錯。
- 組裝 2394 組相同＝遊戲端 `partsOf` 經 `toQParts` 和樣張 `partsOf` 在 402 招上畫出同一張 mid／full（接續排位、觸發、元素片、代價、條件、效果列縮放都一致），可當 2c T-C2 的佐證。
- 這次沒有看到 ±1 色階雜訊（上手第四節第 23 點）。

**截圖**（`docs/art/shots/qi2/`；無頭 Chrome `--force-device-scale-factor=1`、`--mute-audio`，網址帶 `?mute=1`；×6＝CSS zoom＋`image-rendering: pixelated` 最近鄰）

| 檔 | 格式 | 對到 8.2 | 內容 |
|---|---|---|---|
| `docs/art/shots/qi2/2b-01-skills-24-28-true1x.jpg` | jpg（PNG 687 KB 超過） | 第 1 項 | 402 招的 340 個不同長相（鍵含框形與稀有度），24、28 真 1 倍原大 |
| `docs/art/shots/qi2/2b-02a-skills-24-28-dpr2.jpg`、`2b-02b-…` | jpg | 第 1 項 | 同上 DPR 2（一張 324 KB 超過，拆兩張：第 1～170、171～340） |
| `docs/art/shots/qi2/2b-03-categories-40-24-dpr2.jpg` | jpg | 第 2 項 | 道具 56（每個道具第一招；沒有招用到的標「合成」）、出手 9、記號 23：40＋24 DPR 2；出手 24 ×6 一列 |
| `docs/art/shots/qi2/2b-04-starters-named-40-28-24.jpg` | jpg | 第 3、4 項 | 六招入門招；化身、產下幼蜥、召喚守護靈、雙牙；弓槍配大記號 16 招＋散彈驅離；地面效果六種外形；拳套配記號；直線突刺——每招 40／28／24 真 1 倍＋DPR 2 |
| `docs/art/shots/qi2/2b-05-starters-forms-24-x6.png` | **PNG** | 第 3、4 項 | 六招入門招、化身 10、產下幼蜥、召喚守護靈、雙牙：24 真 1 倍｜DPR 2 ×6 |
| `docs/art/shots/qi2/2b-06-real-q-vs-old.jpg` | jpg | 第 5 項 | 實例 75 招（每 5 招取 1、扣 `enemy_only`）：Q 版 40、24｜現行 40、24（虛線框），DPR 2 |
| `docs/art/shots/qi2/2b-07-parts18-iconprop.jpg` | jpg | 第 7、6 項 | 部件小圓片全部 18 真 1 倍｜DPR 2；`icon_prop` 36 招 40 DPR 2（標道具值與出手；紅字＝改變出手的 6 招，含 `skill_ember_bite` `shot`） |
| `docs/art/shots/qi2/2b-08-parts30-change30-dpr2.jpg` | jpg | 第 7、11 項 | 部件小圓片全部 30 DPR 2；修正內容 21 鍵（實際數值）與 +1／−1 各一，30 DPR 2 |
| `docs/art/shots/qi2/2b-09-v2-card-change-x6.png` | **PNG** | 第 7、8、11 項 | 第 2 版改過的 24 個部件 18 真 1 倍｜DPR 2 ×6；技能卡小圖 22＋圖釘未釘 16／18／13 真 1 倍＋DPR 2 ×6；修正內容 18 真 1 倍 ×6 |

**實機未看**：本段不接遊戲畫面，全部用開發頁畫（規格 8.2：第 9～13 項是 2c）。主圖代碼是暫時的參考資料（QI-2a 未合併）；2a 合併後 fixture 帶 `art`，開發頁自動改用，屆時 36 招以外應和本次相同（2a T-A2 鎖住）。

## 5. 長函式

前端逐行搬的函式不拆。超過 80 行的函式：**沒有**（最長是 `skills.ts` 的 `def()` 63 行，和樣張同）。沒有改 Python。

## 6. 和樣張不同的地方（全部列在 `skills.ts`、`parts.ts` 檔頭）

- 依賴改 import；`QS.`／`Q.`／`QW.` 的寫法保留（`import * as QS`、`const Q = { ART, render, outlinePx }`、`const QW = { blit }`），方便逐行對照。
- 型別：表用 `table()`（`skills.ts`）／`PartTable` 包；用字串查表處加 `!` 或 `as`（樣張同處直接取值）；`for … of [[…]]` 字面表加 `as const`、點列加 `: Pt[]`；沒用到的參數加 `_` 前綴（noUnusedParameters）。值都沒改。
- 樣張 `ACT.hit.d(k, o, ["#ffffff"])` 補成兩個色（hit 只用第一個）；`paw(q, { tiny: true })`、`crate(c, { small: true })` 照樣張傳不完整的 `o`（加 `as QOpts` 與註解）；終結記號 `QS.ACT.finisher.d(p, …)` 樣張不傳染色，照傳 `undefined`。
- 沒有畫布（vitest 沒注入假畫布）時：`boxOf` 不量、回預設外接框且不記；`paint`／`glyph` 不貼。
- `list()`：樣張用 `QW.list()`，這裡由 `Q_WEAPON_KINDS` 列（同樣每種一款：`SKILL_FORM`、錘 `warhammer`、其餘第一款），只給開發頁用。

## 7. 待 PM 決定

1. **暫時的 `art` 資料**：`client/src/dev/fixtures/qi2bTempArt.json`（參考實作＋`icon_prop` 規則，402 招）。開發頁與 T-B1 在 fixture 沒有 `art` 時用它。建議 2c（或 2a 合併後）刪掉、測試改只讀 fixture。（派工第 4 點）
2. **錘的 3 招和樣張不同**（第 4 節）：QI-1b 錘柄亮一階的延伸，技能圖示的錘也是亮柄。若美術要技能主圖用樣張的暗柄，要另加參數（`weapons.ts` 不能改，本段不做）。（`QI-1檢查.md`、`PhaseQI-1b報告.md`）
3. **`form_upkeep_permille` 沒有正負箭頭**：需求 4.4 第 20 點說箭頭照正負並「補上 `form_upkeep_permille`、`form_entry_permille`」，但樣張 `CHANGE.form_upkeep_permille` 畫的是「掌印＋小沙漏」，只有 `form_entry_permille` 用 `up()`。照樣張；有箭頭的鍵 9 個（T-B5 鎖住）。`summon_limit_delta` 的 −1（`skill_summon_elite`）也是固定加號、不翻。請美術確認。
4. **實例「78 招」**：需求沒有給名單，開發頁取每 5 招 1 招、扣 `enemy_only` 共 75 招（`set=real`）。要對到樣張 `skills-real.png` 的 78 招請給名單。（需求第 6 節第 5 項）
5. **截圖改 jpg 與拆張**：第 1 項真 1 倍原大總表 PNG 687 KB，改 jpg（294 KB）；DPR 2 一張 324 KB 拆兩張（02a／02b）。第 4 項的 ×6 只做 24（40／28 ×6 會超量）。（D7、6.5.2）
6. **截圖放 `docs/art/shots/qi2/`**：派工說不要改 `docs/art/`，規格 8.1 第 7 點要放這裡；只新增 10 張、沒改既有檔。
7. **元素片物理白閃光、觸發暫代**：照樣張（`TRIG_ALIAS` 5 個在 `parts.ts` 註明暫代；目前沒有招用到，T-B2 鎖住「沒有招用到」——第一招用到時測試會失敗，提醒通知美術補圖）。
8. **`hooks.status`（32 種以外的狀態）**：本段沒掛，開發頁畫樣張的退回（增益箭頭）；名詞表 118 種狀態扣掉 32 種，其餘都走這條。2c 掛 `statusGlyph()`。
9. **草稿 `icon.partial` 的元素**：`toQParts` 把 `undefined`（中性）當「沒有元素」（`null`，不畫元素片、元素底用預設紫），照規格第 0.1 節第 1 點；2c 報告再列。

## 8. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：第一節表加 `render/qIcon/skills.ts`、`parts.ts`、`legacy48.ts`、`partsAdapter.ts` 一列；第二節「開發入口」表加 `skillicon-gallery.html` 的參數；第四節加第 33～36 點（`halo` 另建畫布要記全域假畫布、樣張傳不完整的 `o`、和樣張比對要改原始碼再載入並注入 `framePath`、組裝列 18px 圓片的圖樣是 11.79px）；第五節測試表加「技能圖示 Q 版畫法」一列。

## 9. 請使用者重開伺服器檢查的重點

本段**遊戲畫面完全不變**、沒有改內容與 API，不用重開。要看圖：自己的 vite 開 `/dev/skillicon-gallery.html?mute=1`（`&set=named&px=40,28,24&res=1,2` 等，參數見檔頭）。
