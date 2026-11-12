# Phase QI-2 計畫：Q 版小圖示移植第 2 段（③技能主圖＋④骨架徽章、部件小圓片、技能卡小圖、56／96 組裝，含後端）

> 草稿（開發 PM 助手 2026-11-12，依據本機 main `6d331a38`）。開發 PM 確認第 0 節「待開發 PM 確認」後再定稿、push、派工。
> 美術依據：`docs/art/Q版小圖示-技能圖示移植需求.md`（以下簡稱「需求」，引用寫「需求 x.y」）；樣張以 `10b1040f` 之後的 `docs/art/sample/qIconsSkills.js`、`qIconsParts.js` 為準，推導的參考實作 `docs/art/sample/tools/qskills_derive.py`。
> 前一段：`docs/phases/PhaseQI-1計畫.md`（第 0.0 節的定案照樣適用：畫布＝顯示尺寸 × 固定 2、材質色用 `material.ts`、截圖規則）、`PhaseQI-1a報告.md`（共用核心 `client/src/render/qIcon/core.ts`、`weapons.ts`）、`PhaseIP-1報告.md`（`icon_prop`、允許清單）；設計 `docs/design/06-技能.md` 6.36。
> **切三段**：QI-2a 後端（`art` 推導、內容表、API）→ QI-2b 前端搬畫法（新檔、不接到遊戲畫面）→ QI-2c 前端接線（換掉現行畫法、實機截圖）。理由見第 4 節。

## 0.0 開發 PM 定稿（2026-11-12；取代第 0 節各點的預設，未列的照第 0 節預設）

- 卡片小圖換 canvas（搬 `cardCanvas`），`PinGlyph` 收 `pinned`、三處呼叫傳實際狀態；CSS `currentColor` 不再變色是預期。
- `surfaceTile` 一起換；`statusTile`、`statusIconTile` 不動（第⑤批再換）。
- `HoverFloat` 的 `PinIcon` 與 `float-card.css` 的金色圖釘：本段不換（待美術 PM 回覆，回了另排）。
- 先後：2a 現在可派；2b、2c 等 QI-1b 合併（已合併 `13ac4d53`）後依序派，不改 `qIcon/core.ts`、`weapons.ts`（需要時只加匯出、列報告）。
- 需求 3.2 與 3.3 矛盾：**照 3.3**（實跑結果 `none`／`aura`／`buff`），已請美術 PM 確認 3.2 是否筆誤。
- `icon_prop` 改變出手的 6 招（含 `skill_ember_bite` `swing` → `shot`）：照規則算，2c 截圖標出給美術看。
- 修正技「改造對象」圓片：暫留現行畫法，待美術補圖。
- 截圖：每段 ≤ 10 張；放大總覽交原大總表＋逐像素比對數字（QI-1a 做法）；真 1 倍／最近鄰特寫可用 PNG ≤ 300 KB。
- `MOD_TINT` 等表：值為 `None` 的鍵當作沒有；依表的順序比對，不看輸入鍵順序。
- 其餘 5 點（工坊 `status` 選項換 Q 版、舊畫法本段不刪、部件寫死鋼色照樣張、`icon_of` 無內容庫時的讀表方式、子 agent 一律 Opus 5.5）：照第 0 節預設。
- **QI-2c 追加（美術 PM QI-1b 驗收）**：身上裝備格圖示置中後左上角對齊裝置像素（`Math.round(x * dpr) / dpr`），`__layoutSmoke` 的 `icons()` 加位置檢查。
- **每段合併前跑與改動相關的 slow 測試**（例：2a 動 `icon_of`／內容 → `tests/skillgen/`、`tests/narrative/`、`tests/api/` 含 slow、`tests/cli/test_output_snapshots.py -m slow`）；雜湊／快照不得整批重產，每項要證明變動來自本段（拿掉本段改動回到舊值）。

## 0. 待開發 PM 確認（原表；已由 0.0 取代）

「暫採」是規格目前寫進去的做法；確認後改掉對應列。

| # | 問題 | 出處 | 暫採（建議） |
|---|---|---|---|
| 1 | 卡片小圖做法：SVG 換 canvas，或照 Q 版重畫 SVG | 需求第 5 節第 6 點、4.4 第 25 點、2.4 第 10 列 | **換 canvas**：搬 `cardCanvas()`，`ChipGlyph`／`EffectGlyph`／`PinGlyph` 保留元件名與用法、內部改畫 canvas（畫布 ＝ 顯示尺寸 × 2、CSS 原尺寸）。理由：美術要「和 `cardCanvas()` 同圖、≤14px 不包外框、真 1 倍硬邊」，重畫 SVG 做不到逐像素對照；canvas 可以直接和樣張比 |
| 2 | 狀態卡的表面圖 `surfaceTile()` 要不要一起換成 Q 版 8 種表面 | 需求第 5 節第 7 點、1.3 末段；`client/src/render/skillIcon.ts` 492 行、`ui/StatusCardParts.tsx` 102 行 | **一起換**（美術建議；同題材同形，和效果圓片的表面同一個圖樣）。只改 `surfaceTile` 的 `draw`；`statusTile`、`statusIconTile` 不動（第⑤批） |
| 3 | 格子資訊卡的圖釘 `HoverFloat.tsx` 的 `PinIcon`（另一份同形 SVG，已釘金色 `#ffd04a`、未釘淡色）與浮動卡 `.float-card.pinned::after` 的金色圖釘（`styles/float-card.css` 179 行，CSS data URI）要不要一起換 | 需求 2.4 第 11 列（待開發查證）；`docs/開發PM交接.md` 6.5.1（格子資訊卡圖釘的金色是美術 PM 定的） | **這段不換**。需求只點名 `PinGlyph` 三處（`BattleLogDock`、`UnitInfo`、`SkillCardView`）；那兩處的金色是另一個已定的配色，換成紅頭會改到已定的設計。轉美術 PM 決定要不要之後統一 |
| 4 | 和 QI-1b 的先後 | QI-1b 未合併（`docs/phases/` 沒有 1b 報告）；QI-1b 會改 `qIcon/core.ts` 周邊、`gearIcon.ts`、`dev/layoutSmoke.ts`（加 `iconScaleIssues`） | **QI-2a 可和 QI-1b 平行**（檔案不重疊）；**QI-2b、2c 在 QI-1b 合併後才派**。2b、2c 不改 `qIcon/core.ts`、`qIcon/weapons.ts`（要用的東西只 import 既有 export；缺的在新檔另寫） |
| 5 | 需求 3.2 說「草稿缺欄位時每張表都落到最後一列 `el:arcane`／`aura`／`buff`」，但照 3.3 的表與參考實作，`icon_of({})` 算出的是 `none`／`aura`／`buff`（`buff` 不在 `NEEDS_PROP`，所以 `none` 不換成 `el:arcane`；助手實跑 `qskills_derive.derive({})` 確認） | 需求 3.2、3.3「最後」列；`qskills_derive.py` 225、453 行 | **照 3.3 與參考實作**（`none`／`aura`／`buff`）：402 招逐招比對的基準是參考實作，兩處不同時以表為準。請轉美術 PM 確認 3.2 那句是筆誤 |
| 6 | `icon_prop` 會改出手的 6 招沒有美術看過的樣張（參考實作沒讀 `icon_prop`）：5 招 `w:sword→w:dagger` 從 `swing` 變 `thrust`（`skill_ambush_stab`、`skill_flurry_jab`、`skill_ground_finish`、`skill_marrow_thorn`、`skill_venom_blade`）；**`skill_ember_bite`（近戰、`icon_prop: summon:whelp`）從 `swing` 變 `shot`**（道具不是武器，走第 3 列；射程是 `weapon` 不是 1，走第 4 列） | 需求 3.3 出手第 2～4 列（「吃的是最後決定的 `prop`」）、驗收第 6 項；助手實跑 | **照規則算**（需求已寫「`motion` 照新 `prop` 重算」），在驗收第 6 項的截圖標出這 6 招，請美術 PM 看 `ember_bite` 的 `shot` 是否可接受 |
| 7 | 組裝算式裡修正技的「改造對象」圓片（`modifierTargetPart`）在 Q 版沒有對應圖樣（`qIconsParts.js` 的 `CATS` 沒有這一類） | `client/src/render/skillIcon.ts` 453 行、`skillParts.ts` `modifierTargetPart`；`qIconsParts.js` 379 行 | **暫留現行畫法**（只有工坊與技能卡的組裝算式出現，修正技 18 招），報告列出；請美術 PM 決定補圖或改用別的 Q 圖樣 |
| 8 | 截圖張數：驗收第 1 項（約 322 個長相 × 24、28 × 真 1 倍與 DPR 2，樣張那邊是 32 張 PNG）、第 7 項（約 200 個圓片）照 6 倍放大一定超過每段 10 張與單張 300 KB | `開發PM交接.md` 6.5.2；需求第 6 節；D7 | **第 1、7 項交「原大總表」（1 倍顯示，真 1 倍與 DPR 2 各一張）＋逐像素比對的數字**，6 倍放大只用在第 4 項點名款與第 7 項第 2 版改過的款；照 QI-1a 的做法（`PhaseQI-1a報告.md` 第 4 節）。美術 PM 要 6 倍全量的話請另給張數上限 |
| 9 | 修正技染色 `MOD_TINT` 的比對順序：參考實作照 `change` 字典的鍵順序找第一個（YAML 的寫法順序）；後端 `skill_icon(SkillDef)` 吃的是 `model_dump`（schema 欄位順序，**而且沒填的鍵也在、值是 `None`**） | `qskills_derive.py` 386 行；助手實跑：直接把 `model_dump` 餵參考實作，11 招修正技全部變成 `blood`（`damage_permille: None` 排第一個）；去掉 `None` 後 402 招 0 差異；目前沒有任何一招的 `modifiers[0].change` 有兩個以上 `MOD_TINT` 的鍵 | **值是 `None`／空的鍵當作沒有**（必做，否則 11 招錯色）；有兩個以上時照**內容表的列順序**取第一個（不看輸入鍵順序，結果和鍵順序無關）。目前結果和參考實作相同 |
| 10 | 工坊選項 `status` 欄位（`optionTile` → `statusTile`，現行白色狀態圖樣）要不要換 Q 版 | 需求 1.3 `OptionGlyph`「部件小圓片」、4.4 第 19 點；`skillIcon.ts` 582 行 | **換**：選項小圖改用 Q 版 `STATUS` 圓片（32 種以外照現行 `statusGlyph()`）；`statusTile` 本身（單位頭頂、`unitSprite.ts` 用）不動 |
| 11 | 舊畫法（`paintBackground`、`elementTexture`、`drawMotif` 系列、`elementGlyph`、`skeletonGlyph`、`SkillCardGlyphs.tsx` 的 SVG 路徑）換完後沒人用 | 需求第 6 節 (c)；QI-1 第 0.0 節第 9 點（舊墨線小圖示本段不刪） | **這段不刪**（`skillIcon.test.ts` 仍測 `drawMotif`、`gridLayout` 等），報告逐一列出死碼與還在用的地方，另排整理 |
| 12 | 部件的固定色：`qIconsParts.js` 寫死 `STEEL = "#c3ccd6"`（亮色劍、徽章用），而第 3 批主圖的武器道具經 `core.ts` 的 `M` 已改用 `material.ts`（鋼 `#a9b6c6`） | `qIconsParts.js` 10 行；QI-1 第 0.0 節第 3 點；`PhaseQI-1a報告.md` 待決 2 | **照樣張的字面色**（部件不是「材質」，不換），報告列出；美術 PM 要統一再改 |
| 13 | 推導表在 `content/`，但 `icon_of()` 是沒有內容庫的純函式 | D2、D3；`src/trpg/narrative/skill_icon.py` 334 行；呼叫處 `narrative/skills.py` 1624、1773 行與 `api/routes/workshop.py` 74 行都有 `library` | `icon_of(skill, art=None)`：正式呼叫處一律傳 `library` 上的表；`None` 時讀預設內容資料夾的表（`functools.cache`，只給測試與快照腳本用）。見 A3 |
| 14 | 子 agent 模型：本次派工說一律 Opus 5.5；`docs/開發PM交接.md` 3.000 第 2 點寫 Fable 5.2 | 派工訊息；交接 3.000 | 照本次派工（Opus 5.5），同 QI-1 第 0.0 節第 10 點 |

### 0.1 需求裡「待開發查證」4 項的結論（助手 2026-11-12 只讀查證）

1. **`partsOf` 是否和樣張相同**（需求 2.4 第 8 列）：**實際技能資料上結果相同**，差在三處：① 樣張每個效果帶 `seg`（第幾段），遊戲端沒有——接續記號排進效果列要用到（2c 從 `parts.segs[i].effects` 回推，不必改 `partsOf` 的回傳型別）；② 遊戲端的草稿（`icon.partial`）元素是 `undefined`（中性），樣張沒有這個狀態——2c 照「沒有元素」畫 Q 版底並列進報告；③ 樣張沒有「改造對象」（第 0 節第 7 列）。效果的鍵（`status:<id>`、`surface:<id>`、原語）、核心效果（第一個不是 `damage`）、最多 4 個、修正技改列 `changes`、觸發只給被動與反應且 `null` 時沒有、條件 `target_has_status` 帶狀態，兩邊相同（`skillIcon.ts` 74–117 行、`skillParts.ts` 680、808、1003 行 對 `qIconsParts.js` 427–436 行）。2c 用測試鎖住（T-C2）。
2. **`HoverFloat` 是否另有一份圖釘**（需求 2.4 第 11 列）：**有**。`ui/HoverFloat.tsx` 22–28 行 `PinIcon`（和 `PinGlyph` 同一條 path，`currentColor`；`.tile-pin-icon` 未釘淡色、已釘 `#ffd04a`）；另外 `styles/float-card.css` 179 行 `.float-card.pinned::after` 是 CSS 背景圖的金色圖釘。建議這段不換（第 0 節第 3 列）。
3. **`paintBackground`、`drawMotif` 隨主圖換掉後還有沒有人用**（需求 2.4 第 13 列）：正式程式**只有 `render/skillIcon.ts` 用**（`mainArt`、`compositeArt`、`shapeTile`、`optionTile` 的形狀與元素）；`elementGlyph` 另有 `skillParts.ts` 522 行（`on_hit_effects` 小閃電）、1133 行（`add_element`）；`skeletonGlyph` 只在 `skillIcon.ts`（徽章、`skeletonTile`）。換完後只剩 `render/skillIcon.test.ts`（匯入 `drawMotif`、`ELEMENT_ICON`、`elementPalette`、`gridLayout`、`isRanged`、`normalizeArm`、`SKELETON_NAME`）。`storyIconArt.ts` 的 `drawChip` 是同名的另一個函式，無關。
4. **推導表放進 `content/` 對雜湊與世界日誌的影響**（需求 3.5 末點）：新內容檔會進 `library.files`，所以 **`roguelite/save.ruleset_hash`（一輪存檔）與 `world/save.content_digest`（世界日誌規則鍵）會變**——使用者重開伺服器後進行中的一輪從頭開始、舊世界日誌標成不能重播（一次；之後每改一次表再一次）；**`engine/ruleset_hash.hash_ruleset`（戰鬥紀錄）不變**，因為表不放進 `Ruleset`，舊戰鬥紀錄照樣重播。不用加版號（`docs/dev/上手-內容資料與模擬.md` 第二節 digest 表）。D4 的檢查不改任何內容檔；`art` 是 API 才算的欄位，不進存檔、不進 LLM prompt（`SkillCard` 只在 `trpg.api` 與 `trpg.narrative` 使用，助手 grep 確認）。

## 1. PM 決定

| # | 決定 | 出處 |
|---|---|---|
| D1 | 推導放**後端**：`icon_of()` 新增 `art`（`prop`、`motion`、`act`、`tint`、`spark`），API 帶出；前端只畫，不推導 | 開發 PM 2026-11-12；需求 3.2、第 5 節第 1 點 |
| D2 | 推導表放 `content/`（內容即資料，pydantic schema 驗證）。**誰維護：待玩法 PM 回覆**（開發 PM 已去問），不擋實作；YAML 檔頭先寫「維護者：待定（QI-2 D2）」 | 開發 PM 2026-11-12；需求第 5 節第 2 點；CLAUDE.md 守則 4 |
| D3 | `icon_prop` 清單外的值：維持 IP-1 現行「載入內容時報錯」；執行期遇到（理論上不會）退回推導、不報錯 | 開發 PM 2026-11-12；需求第 5 節第 3 點；IP-1 報告待決 5 |
| D4 | 化身招（效果有 `enter_form`）與 `wielding_weapon` 招（效果條件）填了 `icon_prop`：資料檢查擋下（`ContentError`） | 開發 PM 2026-11-12；IP-1 報告待決 6；需求第 5 節第 4 點 |
| D5 | 技能卡 `compact` 48px 用 `mid`（和 56 同一級） | 開發 PM 2026-11-12；需求第 5 節第 5 點 |
| D6 | 順序：③④ 先於第⑤批（狀態）；共用圖樣畫法建在 `client/src/render/qIcon/` 下，第⑤批沿用（32 種狀態圖樣做成獨立可呼叫的表） | 開發 PM 2026-11-12；需求 4.4 第 27 點 |
| D7 | 截圖：每段 ≤ 10 張；真 1 倍／最近鄰放大特寫可用 PNG（單張 ≤ 300 KB），其他 jpg 80 | 開發 PM 2026-11-12；`開發PM交接.md` 6.5.2（2026-11-12 例外） |

## 2. 目標與範圍外

**目標**：技能圖示的主圖換成第 3 批「道具＋出手＋效果記號＋兩階色塊元素底」；部件小圓片、骨架徽章、形狀、元素片、技能卡小圖換成第 4 批；圖示分三級（`main` ≤40、`mid` 技能卡 56／48、`full` 工坊 96）；推導在後端算好成 `SkillIcon.art`。框（`framePath`、稀有度色、圓片的圓底與色環、徽章底）不動（需求 1.2）。**主圖、組裝、部件同一次出現在遊戲畫面上**（需求第 5 節第 8 點）：2b 只建新檔、不接畫面，2c 一次接上。

**範圍外**：狀態框與類別底色、單位頭頂狀態 `statusTile`（24）、狀態卡狀態 `statusIconTile`（20）＝第⑤批；元素關鍵字小圖樣（⑤b）；HUD 源力（⑦）；`storyIconArt.ts`；`AttrGlyph`；`HoverFloat` 的圖釘與 `.float-card.pinned::after`（第 0 節第 3 列）；需求第 7 節的「可修」各點與清單外待補圖的道具；刪舊畫法程式（第 0 節第 11 列）；內部解析度跟螢幕走；改 `content/skills/`（D4 的檢查只加規則，現有 36 招都通過）。

## 3. 工作環境

- Windows、Git Bash。Python 一律 `uv run python`（不要直接打 `python`）；前端 `corepack pnpm -C client …`。
- 新 worktree 第一次：`uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`；之後 Python 指令加 `UV_NO_SYNC=1`。
- 預覽埠（不用 8000、8001、5195）：QI-2b vite 5270～5274、靜態伺服器 8131～8132；QI-2c vite 5275～5279、`trpg serve` 8133～8135。QI-2a 不開伺服器。vite 的 `/api` 寫死轉 8000，要接自己的 `trpg serve` 另寫暫存設定檔、用完刪掉，不改 `vite.config.ts`（上手-前端第四節第 13 點）。
- 瀏覽器網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`，截圖用 `--force-device-scale-factor=1`。
- 結束前用自己記下的 PID 關掉 vite、`trpg serve`、靜態伺服器與無頭 Chrome，確認沒有殘留；不用 `taskkill /IM`、`pkill`。
- 等背景程序用完成通知，不寫 `until`／`while` 輪詢迴圈。
- agent 與子 agent 一律指定 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣。
- 只跑相關測試（第 9 節）；不跑 `scripts/check.py`、不跑模擬。不要 push。每完成一個交付項目就 commit（第一行英文，例 `feat(qi2a): derive Q skill icon art in icon_of`），結尾帶 Co-Authored-By。
- 要讀的：`CLAUDE.md`；需求全文；QI-2a 讀 `docs/dev/上手-內容資料與模擬.md`（全文）、`docs/art/sample/tools/qskills_derive.py`、`docs/phases/PhaseIP-1報告.md`；QI-2b、2c 讀 `docs/dev/上手-前端戰鬥畫面與動畫.md`（全文）、`docs/phases/PhaseQI-1a報告.md`、`docs/art/上手-畫法.md` 2.1、2.7～2.9；2b 另讀 `docs/art/Q版小圖示-第3批技能主圖.md` 第 11 節與 15.6、`Q版小圖示-第4批徽章與部件.md` 第 8、9 節；2c 另讀第 4 批第 5 節。

## 4. 切段

| 段 | 內容 | 改的檔（主要） | 前置 |
|---|---|---|---|
| **QI-2a** 後端 | 推導表進 `content/`、`art` 推導、D3、D4、API、重產型別與快照 | 新 `content/skill_icon_art.yaml`、新 `src/trpg/content/skill_icon_art.py`、`src/trpg/content/registry.py`、`library/load.py`、`library/container.py`、`library/skill_checks.py`、新 `src/trpg/narrative/skill_icon_art.py`、`narrative/skill_icon.py`、`narrative/skills.py`、`api/routes/workshop.py`、`tests/narrative/icon_fixture.py`、`client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/render/fixtures/skill_icons.json`、`client/src/ui/fixtures/skillCards.json`、`tests/`（新檔＋`test_icon_prop_api_ip1.py` 一處） | 無；可和 QI-1b 平行；**不和其他改 API 的段平行**（交接 3.00 第 5 點） |
| **QI-2b** 前端搬畫法 | `qIconsSkills.js`、`qIconsParts.js`（與它們用到的 `qIcons.js` 片段）逐行搬成 TS；技能圖示開發頁；和樣張逐像素對照；驗收第 1～8、11 項截圖 | 新 `client/src/render/qIcon/skills.ts`、`qIcon/parts.ts`、`qIcon/legacy48.ts`（`ART.status`／`ART.hud` 用到的款、`W.totemPole`、`H.drop` 等；檔名可調）、新 `client/src/dev/skillIconGallery.ts`＋`client/dev/skillicon-gallery.html`、新測試檔 | QI-2a、QI-1b 合併後 |
| **QI-2c** 前端接線 | 三級組裝、部件換圖、組裝列與工坊選項、技能卡小圖與圖釘、`surfaceTile`、排版檢查、實機截圖 | `render/skillIcon.ts`、`render/skillParts.ts`、`render/skillGlyphs.ts`（只改 `skeletonGlyph` 的呼叫端，不刪舊函式）、`ui/SkillIconView.tsx`、`ui/SkillCardView.tsx`、`ui/SkillCardGlyphs.tsx`、`ui/BattleLogDock.tsx`、`ui/UnitInfo.tsx`、`ui/VariantList.tsx`、`dev/layoutSmoke.ts`、`dev/skillIconGallery.ts`（加 `mid`／`full`）、既有測試改寫 | QI-2b 合併後 |

理由：① 後端與前端改的檔完全不重疊，2a 只多一個前端看不到的欄位（需求第 5 節第 8 點「後端段可以先做」）。② 兩個樣張檔共約 145 KB（`qIconsSkills.js` 63 KB、`qIconsParts.js` 82 KB，加上 `qIcons.js` 的 `STATUS`／`HUD` 片段），逐行搬加對照與 9 項截圖已接近一段上限；接線要改 6 個既有元件、`skillIcon.ts` 600 行與 `skillParts.ts` 1331 行的圖樣、改寫既有測試、實機截圖與浮動卡實測，放同一段會超過 25 萬 token。③ 「搬畫法／接線」這樣切，2b 合併後遊戲畫面完全不變，滿足「主圖、組裝、部件同一次上線」，不需要旗標。若 2b 超量，可在 `skills.ts` 做完時交件，`parts.ts` 另派 2b-2（檔案不重疊）。

## 5. 受影響的既有功能

| 區塊 | 受影響的 | 改／不改 | 理由 |
|---|---|---|---|
| 引擎 | 無：`art` 只在 `trpg.narrative` 算；推導表不放進 `Ruleset`；`trpg.engine` 不匯入 `trpg.narrative`（import-linter） | 不改 | 06 6.36「只影響圖示」；T-A9 鎖住 |
| 內容資料 | 新 `content/skill_icon_art.yaml`（推導表，A1）；`trpg content check` 659 → 660 個檔 | 新增（2a） | D2 |
| 內容檢查 | `skill_checks.icon_prop_problems` 加 D4（化身、`wielding_weapon` 招不能填）；現有 36 招沒有這兩類（化身 10 招、`wielding_weapon` 24 招，交集 0，助手實跑） | 改（2a） | D4 |
| 內容 digest／存檔 | `ruleset_hash`、`content_digest` 因新檔改變（一次）；`hash_ruleset` 不變；舊戰鬥紀錄照樣重播 | 不改（不加版號） | 第 0.1 節第 4 點；報告附重開提醒 |
| 存檔 | `SkillIcon` 不進一輪存檔、世界存檔、戰鬥紀錄 | 不改 | 2a 以 `grep` 確認並寫進報告 |
| API／型別 | `SkillIcon.art`（`IconArt \| None`，預設 `None`、`exclude_if` None；`icon_of` 一律填）經技能卡、變奏卡、`/api/workshop/check` 帶出；`client/openapi.json`、`schema.d.ts` 重產 | 改（2a） | D1。選填是為了 TS 型別是 `art?:`：既有前端測試手寫的 `SkillIconData`（`render/skillIcon.test.ts`）不用在 2a 動；2c 對沒有 `art` 的舊資料畫 `none`／`aura`／`buff` |
| 衍生快照 | `client/src/render/fixtures/skill_icons.json`（402 招、隨機 50、工坊示範每一步都多 `art`）、`client/src/ui/fixtures/skillCards.json` | 重產（2a） | `tests/narrative/test_skill_icon.py::test_client_fixture_is_current`、`tests/api/test_client_fixtures.py` 會擋 |
| CLI 快照 | `skills_list`、`skills_show_all` 不含圖示，預期不變 | 不改 | 2a 跑一次確認（第 9 節） |
| IP-1 的測試 | `tests/api/test_icon_prop_api_ip1.py::test_icon_without_prop_is_unchanged` 斷言「加了 `icon_prop` 只差這一欄」——現在 `art.prop`（與可能的 `art.motion`）也會跟著變 | 改寫（2a），不放寬 | 新斷言：只差 `icon_prop` 與 `art`，且 `art.prop == "w:axe"`、其餘欄位逐一相同 |
| 工坊 | `/api/workshop/check` 的 `icon` 多 `art`（草稿的 `icon_prop` 已在入口丟掉）；`OptionGlyph`（26／20／22）換 Q 版圓片 | 改（2a 資料、2c 畫法） | 需求 1.3 |
| 隨機組合器、白板、LLM 提議 | 不產生新欄位；它們的技能同樣算得出 `art`（`icon_prop` 已在入口丟掉） | 不改 | IP-1 交付 3 |
| 技能圖示 `SkillIconView` | 24（配招、隊伍）、28（次要列、召喚、變奏、工坊）、40（技能列、技能磚、靶場選職業、工坊）→ `main`；`SkillCardView` 56／48 → `mid`（D5）；工坊 96 → `full`。`small?: boolean` 改成 `level?: "main" \| "mid" \| "full"`（不填依邊長：≤40 `main`、其餘 `full`）；`SkillCardView`、`VariantList` 兩個傳 `small` 的地方改傳級別 | 改（2c） | 需求 1.3、2.4 第 7 列、4.3 第 15 點 |
| 組裝算式 `AssemblyFormula`、`TileCanvas` | 30（各段部件）、18（條件、代價）：部件、徽章、形狀換 Q 版；「改造對象」暫留（第 0 節第 7 列） | 改（2c） | 需求 4.4 |
| 技能卡小圖 | `ChipGlyph`（16）、`EffectGlyph`（18）、`PinGlyph`（13）：SVG → canvas；`PinGlyph` 收 `pinned`（預設 `true`），`BattleLogDock`、`UnitInfo`、`SkillCardView` 傳實際狀態（原本靠 CSS `currentColor` 變色，換 canvas 後 CSS 顏色不再生效） | 改（2c） | 需求 4.4 第 25 點；第 0 節第 1 列 |
| 狀態卡 `StatusCardParts` | `ChipGlyph`／`EffectGlyph` 跟著換；表面圖 `surfaceTile`（20）換 Q 版（第 0 節第 2 列）；狀態圖 `statusIconTile` 不動 | 改 `surfaceTile` 的畫法（2c），元件不改 | 第⑤批另做狀態 |
| 單位頭頂狀態 | `render/unitSprite.ts` 的 `statusTile`＋`tileCanvas`（24）：`tileCanvas` 會改（圓片貼圖對齊），但狀態那兩個的畫面必須和改之前相同 | 不改畫面 | 需求驗收第 13 項；T-C6 鎖住 |
| 格子資訊卡圖釘、浮動卡金色圖釘 | `HoverFloat.tsx` `PinIcon`、`float-card.css` `::after` | 不改 | 第 0 節第 3 列 |
| 舊畫法 | `skillGlyphs.ts` 的 `paintBackground`、`elementTexture`、`drawMotif` 系列、`elementGlyph`、`skeletonGlyph`；`SkillCardGlyphs.tsx` 的 SVG | 不刪（留死碼） | 第 0 節第 11 列 |
| 依賴原版位的地方 | 元素片在左上、接續在斜切線中央、物理有元素片 | 2c 查證（`grep` 座標與測試），結果寫進報告 | 需求 4.3 第 16 點、第 6 節 (d) |
| 排版煙霧檢查 | QI-1b 的 `iconScaleIssues` 加上 `canvas.skill-icon` 與組裝列、卡片小圖的 canvas | 改（2c） | 需求 4.1 第 2 點 |
| 字型重畫 | `render/fontLoad.ts` 呼叫 `clearSkillIconCache`；新快取也要一起清 | 改（2c） | 新圖示快取不靠字型，但清快取的入口要保留 |
| 開發頁 | 新 `skillicon-gallery.html`（現在沒有技能圖示專用頁；`skill-gallery.html` 是動畫片段） | 新增（2b）、擴充（2c） | 需求 1.3 末列 |

## 6. 交付項目

### QI-2a 後端

- **A1 推導表**：`content/skill_icon_art.yaml`＋schema `src/trpg/content/skill_icon_art.py`（`ContentModel`，`extra="forbid"`、`frozen`），登記進 `KNOWN_CONTENT_FILES`，`load_library` 載入並存進 `ContentLibrary`（同時把 IP-1 已載入的 `IconPropTable` 也存進 `ContentLibrary`，D3 要用）。內容＝`qskills_derive.py` 的同名表**逐筆照抄、順序不變**：`WEAPON_LOOK`、`MELEE_WORDS`、`RANGED_WORDS`、`THRUST_PROPS`、`RANGED_KINDS`、`SUMMON_GROUP`、`SUMMON_TINT`、`MOD_TAG_PROP`、`MOD_TINT`、`DOT`、`BIND`、`CURSE`、`STATUS_TINT`、`COND_TINT`、`SURFACE_TINT`、`EFFECT_ACTION`、`LATE_ACTION`、`SHAPE_MOTION`、`NEEDS_PROP`（`AREA_SHAPES` 參考實作沒用到，不搬）。有優先順序的表一律是「列表」不是對應表；`terrain` 那一列照參考實作在載入後換成 `surface`＋`stone`（需求 3.3 第 15～20 列）。schema 檢查：代碼集合封閉（出手 9、記號 23＋`terrain`、染色 13＋`stone`、道具前綴 `w`／`el`／`summon`／`form`／`none`），ID 不重複。**跨檔參照**（狀態、原語、表面、召喚物、武器 ID）只寫成測試列出、不在載入時擋——參考表若有現在不存在的 ID（助手沒逐一查），擋了就得改美術的表；查到的清單寫進報告。檔頭寫來源與「維護者：待定（QI-2 D2）」。
- **A2 D4**：`library/skill_checks.py::icon_prop_problems` 加：效果（含 `followup.effects`）有 `enter_form`，或任一效果的 `condition.type == "wielding_weapon"` 的技能填了 `icon_prop` → 問題字串（中文，說明「化身／持武器條件的招圖示固定畫化身／那把武器，`icon_prop` 不生效」）。
- **A3 推導**：新 `src/trpg/narrative/skill_icon_art.py`：`IconArt`（`prop`、`motion`、`act`：`str`；`tint`、`spark`：`str | None`）與 `derive_art(skill: Mapping, tables) -> IconArt`，規則照需求 3.3（`icon_prop` 插在第 2、3 列之間，且**值在允許清單內**才用——D3 執行期退回；化身與 `wielding_weapon` 仍優先；「最後」列對 `icon_prop: none` 一樣生效；`motion` 吃最後決定的 `prop`）。輸入用容錯取值（沿用 `skill_icon.py` 的 `_map`／`_seq`／`_text`），**值是 `None` 的鍵當作沒有**（第 0 節第 9 列）；表一律依序比對、不依賴 `set` 或輸入鍵順序；永遠不丟例外（參考實作遇到型別錯的輸入會丟 `TypeError`，移植不能）。`icon_of(skill, art=None)` 填 `SkillIcon.art`；`skill_icon(skill, art=None)` 同。`art` 參數是「推導表＋允許清單」的包裝（名稱由實作者定），`None` 時讀預設內容資料夾（`functools.cache`）。函式照 ruff `C901` ≤ 15 拆。
- **A4 呼叫處**：`narrative/skills.py`（技能卡、變奏卡）、`api/routes/workshop.py::_check`、`tests/narrative/icon_fixture.py` 都傳 `library` 上的表。
- **A5 型別與快照**：`UV_NO_SYNC=1 uv run python scripts/export_openapi.py` → `corepack pnpm -C client gen:api`；`UV_NO_SYNC=1 uv run python -m tests.narrative.icon_fixture`；`UV_NO_SYNC=1 uv run python scripts/export_client_fixtures.py`。`git diff --stat` 確認只有 `openapi.json`、`schema.d.ts`、`skill_icons.json`、`skillCards.json` 變，且 JSON 的變動只有多出 `art`（寫腳本比對，結果寫進報告）。
- **A6 測試**：第 7 節 T-A1～T-A10；改寫 `test_icon_prop_api_ip1.py` 一處（第 5 節）。
- **A7 報告與上手筆記**（第 10 節）。

### QI-2b 前端搬畫法（不接到遊戲畫面）

- **B1 主圖**：`client/src/render/qIcon/skills.ts`，由 `qIconsSkills.js` 逐行搬：`ELEMENT`、`SUMMON`、`FORM`、`MOTION`、`ACT`（23＋`terrain` 別名）、`TINT`、`BASE`、`RARITY`、`PAD`、`def(look)`（`pre`／`d`／`post`／`meta`、`boxOf`、`pos`、`corner`、`markK`、`markAt`、`drawMark`、`tipMark`、`side: "br"`／`"tr"`、`wedges`、殘影的離屏染色）、`base(ctx, look)`、`paint(ctx, look, size, res, { frame })`。武器道具呼叫 QI-1a 的 `qWeaponDef(qResolve(…))`（材質名照 `propOf()`：劍、巨劍、火槍、手槍、雙手槍 `steel`，其餘預設；色照 `material.ts`，需求 2.4 第 3 列），拳套沒寫形制用鐵拳、`GUN_SMALL` 照搬；框用遊戲端 `skillGlyphs.ts` 的 `framePath`（需求 2.4 第 4 列）；貼圖一律 `core.ts` 的 `blit`（需求 4.1 第 1 點）。不認得的代碼不丟例外：照樣張退（召喚→`spirit`、化身→`bear`、元素→`arcane`），`w:` 不認得的種類退 `sword`，報告列出。
- **B2 部件**：`client/src/render/qIcon/parts.ts`，由 `qIconsParts.js` 逐行搬：`SKELETON`（16）、`EFFECT`（51 圖、53 碼，`EFFECT_ALIAS`）、`SURFACE`（8，油用 `oilPool`）、`STATUS`（32，**獨立可呼叫的表 `STATUS[id].d`**，D6）、`COND`（17）、`COST`（6，`COST_RING`）、`TRIG`（22＋`TRIG_ALIAS` 5 個，程式裡註明「暫代」）、`LINK`（6，`LINK_RING`）、`SHAPE`（13，命中格固定 `#ffb23a`、`UNLIT`）、`CHANGE`（21，`signArrow` 照數值正負）、`ELEMENT`（9）、`CARD`（22＋圖釘兩態）；`entry`、`def`、`glyph`、`paint`、`chip`、`chipCanvas`、`cardCanvas`、`cardPx`、`paintIcon`（三級，**收一個純資料的部件結構**，不在這裡另寫 `partsOf`——拆解只留 `skillIcon.ts::partsOf` 一份，需求 2.4 第 8 列；2b 的開發頁與測試用 `partsOf` 的結果轉成這個結構，轉換函式放在不會造成循環匯入的地方，由實作者定）。`hooks.status`（32 種以外的狀態）改成參數，由 2c 傳現行 `statusGlyph()`（需求 2.4 第 9 列）。
- **B3 `qIcons.js` 片段**：`client/src/render/qIcon/legacy48.ts`（檔名可調）：`qIconsParts.js`／`qIconsSkills.js` 用到但 QI-1a 沒搬的 `ART.status` 各款、`ART.hud`（`ap`、`mana`、`stamina`、`move`…實際用到的）、`W.totemPole`、`H.drop` 等，逐行搬。**不改 `core.ts`、`weapons.ts`**（第 0 節第 4 列）。
- **B4 開發頁**：`client/src/dev/skillIconGallery.ts`＋`client/dev/skillicon-gallery.html`：資料讀 `render/fixtures/skill_icons.json`（2a 之後帶 `art`）；參數 `?px=`、`&res=1|2`（1＝真 1 倍）、`&zoom=<k>`（最近鄰放大）、`&level=main|mid|full`、`&set=skills|props|motions|acts|starters|named|iconprop|real|parts|card|change`（對到第 8.2 節）、`&cat=&id=`（單一部件）、`&from=&n=`（分張）、`&label=0`、`&old=1`（並排現行畫法，第 5 項用）；掛 `window.__qiSkillDev` 供像素比對。檔頭寫參數說明。
- **B5 測試**：第 7 節 T-B1～T-B7。
- **B6 和樣張逐像素對照**（第 7 節末段）與截圖（第 8.2 節）。
- **B7 報告與上手筆記**（第 10 節）。

### QI-2c 前端接線

- **C1 三級**：`render/skillIcon.ts`：`paintSkillIcon(ctx, icon, level)`、`skillIconCanvas(icon, size, level, res = ICON_RES)`、`iconCacheKey` 帶 `level` 與 `res`（需求 4.1 第 5 點）；主圖用 B1、組裝用 B2 的 `paintIcon`；`SMALL_ICON_MAX` 保留為「預設級別的門檻」。`ui/SkillIconView.tsx`：`level` 參數取代 `small`；畫布 `iconCanvasPx(size)`；沒有 `art` 時畫 `none`／`aura`／`buff`。
- **C2 `partsOf` 與三處改動**：`partsOf` 仍是唯一拆解函式；組裝時從 `segs[i].effects` 回推每個效果列項目在第幾段（接續記號放在第二段第一個效果前面，沒有就放最後）；觸發左上 (15,15) 半徑 12.5、有觸發時元素片讓到 (12,39) 半徑 8；物理與沒有元素不畫元素片（需求 4.3 第 16 點）。查證「別處依賴原版位」並寫進報告。
- **C3 部件換圖**：`render/skillParts.ts` 的 `EFFECT`、`COND`、`COST_ART`、`TRIG`、`LINK`、`modifierChangePart` 圖樣換成 B2；`drawChip` 的圓底與色環不動，裡面改呼叫 `paint()`（圖樣＝直徑 78%，`blit` 對齊）；`Part.color` 只剩色環用；效果帶狀態查 `STATUS`，32 種以外傳 `statusGlyph()`；`KNOWN_PARTS` 的測試照新表。元素片與 `add_element` 改用 `ELEMENT`。
- **C4 組裝列與工坊選項**：`tileCanvas` 改成整數像素貼圖（`skeletonTile` 照 `chipCanvas("skeleton")`：深色圓底 (50,50) 半徑 40、無色環、圖樣 62 單位；`shapeTile` 用 `SHAPE`）；`optionTile` 的形狀、元素、狀態（第 0 節第 10 列）、效果、條件、觸發換 Q 版。**`statusTile`、`statusIconTile` 的畫面不變**（T-C6）。
- **C5 `surfaceTile`**：換 Q 版 8 種表面（第 0 節第 2 列）。
- **C6 技能卡**：`ui/SkillCardView.tsx` 169 行改 `level="mid"`（56 與 compact 48，D5）；`ui/VariantList.tsx` 改傳 `level="main"`（或不傳）。
- **C7 卡片小圖**：`ui/SkillCardGlyphs.tsx` 的 `ChipGlyph`、`EffectGlyph`、`PinGlyph` 內部改 canvas（第 0 節第 1 列；`damage` 的元素色照現行 `elementColor` 傳入）；`PinGlyph({ pinned = true })`，`BattleLogDock.tsx`（`pinned`）、`UnitInfo.tsx`（`pinned`）、`SkillCardView.tsx`（`pin.pinned`）傳實際狀態。保留 `aria-hidden`。
- **C8 排版檢查**：`dev/layoutSmoke.ts` 的 `iconScaleIssues`（QI-1b）加上 `canvas.skill-icon`、組裝列與卡片小圖的 canvas；純函式判定加 vitest。
- **C9 開發頁擴充**：`skillicon-gallery.html` 加 `mid`／`full` 實際組裝（用遊戲端 `partsOf`），供驗收第 9、10 項與實機到不了的情況。
- **C10 測試、截圖、報告與上手筆記**：第 7 節 T-C1～T-C8；既有測試改寫（逐條說明舊斷言 → 新斷言，不放寬）；第 8.2 節截圖；第 10 節。

## 7. 行為一致測試

資料一律用實際內容（`content/skills/` 402 招；前端用 2a 重產的 `skill_icons.json`、`skillCards.json`），不手寫清單。參考實作在 `docs/art/`（不是套件）：pytest 用 `importlib.util.spec_from_file_location` 載入 `docs/art/sample/tools/qskills_derive.py`（只讀，不改它）。

### QI-2a（pytest）

| # | 測什麼 |
|---|---|
| T-A1 | **推導表每一列實際跑 `icon_of()`**（`skill_icon(library.skills[id], art=…)`）：下表每一列至少一招，斷言 `art` 的對應欄位；同時斷言這招**確實走到這一列**（可呼叫拆出的各列函式，或用「前面各列都不成立」的條件）。「實例」欄是助手用參考實作挑出來的第一招（只看沒填 `icon_prop` 的），實作者要用腳本重新確認。**沒有實例的列**用一招實際技能複製後改最少的欄位（例：改 `name_zh`、`weapon_req`），在測試裡標「合成」並在報告列出 |
| T-A2 | **402 招逐招比對參考實作**：參考實作吃 YAML 原文、`icon_of` 走正式路徑 `skill_icon(SkillDef)`。沒填 `icon_prop` 的 366 招：`prop`、`motion`、`act`、`tint`、`spark` 與 `derive()` 完全相同，`elements[0]`／`[1]` 等於 `derive()` 的 `el`／`el2`；有填的 36 招：`prop == icon_prop`、`motion == derive_motion(原文, icon_prop)`、`act`／`tint`／`spark` 與 `derive()` 相同。不同的招數必須是 0（不是就停下回報） |
| T-A3 | **推導表和參考實作的表相同**：YAML 載入後逐表、逐筆、照順序等於 `qskills_derive` 的同名常數（`terrain` 換算除外）。檔頭註明：之後玩法 PM 改表時，這個測試要和表一起改（不是放寬） |
| T-A4 | **`icon_prop` 插在第 2、3 列之間**（實際技能＋填值，用 `model_copy(update=…)`）：化身招（例 `skill_form_bear`）填 `w:axe` → 仍是 `form:bear`；`wielding_weapon` 招（例 `skill_akimbo_burst`）填 `w:sword` → 仍是 `w:dual_pistol`；修正技（例 `skill_attack_mastery`，第 3 列）填 `w:hammer` → `w:hammer`；有名稱關鍵字的遠程招（例 `skill_rng_static_bolt`，第 4a 列）填 `w:longgun` → `w:longgun`；元素招（例 `skill_air_burst`，第 6 列）填 `w:fist` → `w:fist` |
| T-A5 | **出手依最後道具重算**：第 0 節第 6 列的 6 招，`motion` 等於「用 `icon_prop` 重算」且不等於「沒填時」；另外 `icon_prop: none` 配 `NEEDS_PROP` 的記號（實際技能填 `none`）→ `el:arcane`，`motion` 用 `el:arcane` 算 |
| T-A6 | **D3 執行期退回**：允許清單外的值（`"w:banana"`、`"W:SWORD"`、數字、空字串）丟給 `icon_of` → `art` 與沒填時相同、不丟例外；`SkillIcon.icon_prop` 照 IP-1 現行（字串原樣、非字串為 `None`） |
| T-A7 | **D4**：化身招、`wielding_weapon` 招（含條件只在 `followup.effects` 的）填 `icon_prop` → `icon_prop_problems` 回問題、`load_library` 拋 `ContentError`；目前內容 0 招被擋 |
| T-A8 | **不丟例外**：`icon_of({})` 的 `art` 是 `none`／`aura`／`buff`、`tint`／`spark` 為 `None`（第 0 節第 5 列）；型別錯的草稿（`effects: "x"`、`shape: 3`、`tags: 5`、`modifiers: [1]`、`followup: []`、`variants: "x"`）與工坊示範每一步都回傳 `IconArt` |
| T-A9 | **拿掉 `art` 不影響戰鬥**：`hash_ruleset(library.ruleset)` 在「推導表換成空表」的內容庫下不變；同一張地圖、同一組種子（沿用 `test_icon_prop_battle_ip1.py` 的單位配法，至少 2 個種子），原內容庫與換空表的內容庫對戰，步驟、事件、最終狀態逐筆相同；另確認 `ruleset_hash`／`content_digest` 會因表改變（寫明是預期） |
| T-A10 | **API**：技能卡、變奏卡、`/api/workshop/check` 的 `icon.art` 都有值且等於 `derive_art` 的結果；`test_icon_prop_api_ip1.py` 改寫那一項（第 5 節） |

T-A1 的列與實例（參考實作實跑，括號是該列的招數）：

| 表 | 列 | 實例 |
|---|---|---|
| 道具 | 1 化身（10） | `skill_form_bear` → `form:bear` |
| | 2 `wielding_weapon`（24） | `skill_akimbo_burst` → `w:dual_pistol` |
| | 2b `icon_prop`（36） | `skill_ambush_stab` → `w:dagger` |
| | 3 修正技：`heal`／`summon`／`ranged` 標籤（2／2／1）、攻擊近戰（8）、攻擊遠程（**無**）、近戰其他（2）、其餘（1） | `skill_beam_of_mercy` → `el:holy`、`skill_summon_elite` → `summon:spirit`、`skill_timber_piercer` → `w:bow`、`skill_attack_mastery` → `w:sword`、**合成** → `w:bow`、`skill_burning_shove` → `w:fist`、`skill_lingering_roar` → `w:tome/book` |
| | 4a 遠程：弩（1）、飛刃（1）、槍（**無**）、預設（38） | `skill_rng_static_bolt` → `w:crossbow`、`skill_oil_spark_throw` → `w:kunai`、**合成** → `w:longgun`、`skill_armor_piercing_arrow` → `w:bow` |
| | 4b 近戰：`stealth`（2）、`martial`（1）、關鍵字 盾（2）、鞭（1）、拳／匕／矛槍／斧／鐮／錘鎚（**皆無**，已被 `icon_prop` 取代）、`cone`／`ring`（4）、預設（45） | `skill_shadow_ambush` → `w:dagger`、`skill_palm_strike` → `w:fist`、`skill_shield_bash` → `w:kite_shield`、`skill_whip_crack` → `w:whip`、**合成**各一、`skill_cleave` → `w:greatsword`、`skill_all_in` → `w:sword` |
| | 5 召喚（22） | `skill_fsum_cinder_pact` → `summon:spirit` |
| | 6 元素（152）／7 水（4）／8 奧術（16）／9 沒有（27） | `skill_air_burst` → `el:wind`、`skill_downpour` → `el:water`、`skill_afterimage_vow` → `el:arcane`、`skill_bear_trap` → `none` |
| | 最後 `none`＋`NEEDS_PROP`（**無**） | **合成**（或 T-A5 的 `icon_prop: none`） |
| 出手 | 1 形狀：`chain`／`line`／`cone`／`ring`／`square3`／`cross`／`allies_in_radius`／`ground_tile`／`self` | `skill_chain_lightning`、`skill_ember_trail`、`skill_ashen_oath`、`skill_air_burst`、`skill_all_in_chant`、`skill_cinder_dive`、`skill_rune_burst`、`skill_bear_trap`、`skill_afterimage_vow`；沒有形狀 → **合成** |
| | 2 近戰武器：`thrust`（1）／`swing`（52） | `skill_shadow_backstab`、`skill_all_in` |
| | 3 `swing`（2）／4 `shot`（128） | `skill_rx_dread_glare`、`skill_akimbo_burst` |
| 記號 | 1 `modify`：`add_element`（2）／`MOD_TINT`（16） | `skill_burning_shove` → `fire`、`skill_attack_mastery` → `blood` |
| | 2 `builder`（11） | `skill_charged_cleave` |
| | 3～13 各組 | `skill_form_bear`（transform）、`skill_fsum_cinder_pact`（summon，`fire`）、`skill_detonate_burning`（detonate，`fire`）、`skill_bear_trap`（trap）、`skill_banish`（step）、`skill_death_spiral`（dash）、`skill_gear_grapple`（pull）、`skill_air_burst`（push）、`skill_bone_crusher`（knockdown）、`skill_bloodlust`（heal）、`skill_ember_ward`（shield） |
| | 14 狀態：`dot`／`bind`／`slow`／`mark`／`curse`／`buff` | `skill_blade_dance`、`skill_deep_freeze`、`skill_annotated_frost`、`skill_hex_bolt`、`skill_blinding_dark`、`skill_fire_enchant` |
| | 15～20 | `skill_ashen_oath`（surface，`fire`）、`skill_earth_collapse`（surface＋`stone`）、`skill_overcurrent`（builder）、`skill_combo_finisher`（finisher）、`skill_blessing_thief`（curse）、`skill_afterimage_vow`（buff） |
| | 21／22／23／24 | `skill_ash_harvest`、`skill_akimbo_burst`、`skill_all_in`、**合成**（沒有傷害、沒有其他效果） |
| `spark` | 有（3） | `skill_frost_ledge_cleave` → `ice`、`skill_oil_spark_throw` → `fire` |

### QI-2b（vitest，假畫布用 `test/fakeCanvas.ts`）

| # | 測什麼 |
|---|---|
| T-B1 | **後端代碼前端都畫得出來**：`skill_icons.json` 的每一筆（402＋隨機 50＋工坊示範）的 `art` 丟給 `def(look)`：`prop`／`motion`／`act`／`tint`／`spark` 都在 TS 表裡（不是走「不認得」的退回）；`w:` 道具都取得到 QI-1a 的武器圖樣（不是退回別款） |
| T-B2 | **部件代碼齊全**：名詞表快照（`battle/fixtures/glossary.json`）的每個狀態、表面、觸發、條件、效果原語，與 `KNOWN_PARTS`，都有 Q 版圖樣或明確退回（狀態 32 種以外 → 參數傳入的現行圖樣；觸發 5 個 → `TRIG_ALIAS`）；數量和需求 1.1 的 16／51(53)／8／17／6／22(+5)／6／13／21／9／32／22 比（數字寫在斷言旁並註明出處） |
| T-B3 | **貼圖對齊整數裝置像素**：主圖 24、28、40、48、56、96 × 五種框形 × `res` 1、2；圓片 18、20、22、26、30 與 56 角落、96 角落；卡片小圖 13、16、18——`blit` 的左上角乘 `res` 都是整數，沒有 `drawImage` 的縮放貼法（假畫布記錄 `drawImage` 的參數個數） |
| T-B4 | **外框規則**：主圖 `ow = outlinePx(整個圖示邊長)`；圓片、徽章、卡片小圖的圖樣 ≤14px 時 `ow = 0`；`def(cat, id, 圖樣px)` 的 `small`／`tiny` 依圖樣 px（18px 圓片 → `tiny`） |
| T-B5 | **`signArrow`**：冷卻 −1、AP −1 朝下青色；傷害 +150‰、命中 +1、範圍 +1、推距 +1、沒有數值 朝上橘黃（用 `skill_icons.json` 裡實際修正技的 `changes`） |
| T-B6 | **`paintIcon` 三級**（用 `partsOf` 轉出的部件結構）：`main` 只有主圖與框；`mid` 只多右下徽章 (83,83) r15、被動／反應左上觸發 (17,17) r15；`full` 的元素片、觸發、接續、代價、條件、徽章、效果列位置照需求 4.3 第 16、17 點；瞬步背刺、狂野之刃、燧石飛刃（物理）沒有元素片 |
| T-B7 | **確定性與不丟例外**：全部款 × 尺寸 × `res` 畫兩次（先暖快取）呼叫紀錄相同；不認得的代碼不丟例外 |

另外（瀏覽器，寫進報告）：照 QI-1a 的做法（`PhaseQI-1a報告.md` 第 4 節 (a)），開發頁同一頁載入靜態伺服器上的樣張（`qIcons.js`、`qIconsWeapons.js`、`qIconsSkills.js`、`qIconsParts.js`），樣張的 `M`、`MAT` 先換成 `material.ts` 的色，同一份 `look`／部件、同尺寸與 `res`，`getImageData` 比對：主圖 402 招 × 24、40（res 1、2）、全部部件 × 18（res 1、2）、30，卡片小圖 22 × 16／18／13；寫出不同的組數、最大像素數與原因（只允許武器道具的材質色與 `color.ts` 的 `mix` 四捨五入，需求 2.2 第 4 點）。

### QI-2c（vitest）

| # | 測什麼 |
|---|---|
| T-C1 | **級別**：`SkillIconView` 的預設級別依邊長（≤40 `main`、其餘 `full`）；`SkillCardView` 56 與 compact 48 都是 `mid`（D5，掃原始碼或元件邏輯抽成純函式）；快取鍵含 `level`、`res` 與 `art` 各欄位，不同級別不同鍵 |
| T-C2 | **`partsOf` 和樣張相同**（第 0.1 節第 1 點）：測試裡照 `qIconsParts.js` 427–436 行寫一份樣張版（只在測試檔），對 `skill_icons.json` 全部資料比：核心、效果列（鍵與順序）、條件、代價、觸發、接續、骨架、每個效果列項目的段號都相同 |
| T-C3 | **三處改動接上了**：用實際技能（被動、反應、複合、物理、沒有元素各至少一招，從 `skill_icons.json` 挑）畫 `full`，假畫布記錄觸發 (15,15)、元素片 (12,39)、接續在效果列且色環 `#7fd8ff`、物理與沒有元素沒有元素片 |
| T-C4 | **畫布尺寸**：`SkillIconView`、`TileCanvas`、卡片小圖的畫布寬高 ＝ 顯示尺寸 × `ICON_RES`；排版檢查的純函式判定（整數、相等通過；縮放、小數不通過） |
| T-C5 | **圖釘**：`PinGlyph` 收 `pinned`，三處呼叫傳的是實際狀態（`BattleLogDock`、`UnitInfo`、`SkillCardView`；元件邏輯抽純函式或掃原始碼） |
| T-C6 | **不動的確認**：`statusTile(id)`、`statusIconTile(id)` 對名詞表全部狀態，經 `tileCanvas` 的假畫布呼叫紀錄，和 2c 開工前（先在 2b 合併後的 main 錄一份基準，存在測試檔）完全相同 |
| T-C7 | **`surfaceTile` 與工坊選項**：8 種表面走 Q 版（油是 `oilPool`）；`optionTile` 的 `status`／`surface`／`element`／`shape`／`skeleton`／`effects`／`condition`／`event` 都畫 Q 版；不認得的值照現行回 `null` 或「?」 |
| T-C8 | **既有測試改寫**：`render/skillIcon.test.ts`、`render/glossaryNames.test.ts`、`ui/skillCard.test.ts`、`world/panelIcons.test.ts`、`world/range.test.ts` 裡描述舊畫法的斷言改成 Q 版的對應斷言（逐條寫進報告，不放寬） |

## 8. 驗收條件

### 8.1 共通

1. 本段第 7 節的測試全過；改寫的既有測試在報告逐條說明「舊斷言 → 新斷言」。
2. **QI-2a**：`UV_NO_SYNC=1 uv run trpg content check`（660 個檔、402 個技能）；`ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 結束碼 0；第 9 節的 pytest 全過；`trpg battle --map open_plain --seed 7 --log-json <暫存>/b.json` ＋ `trpg battle replay` 通過；`corepack pnpm -C client typecheck` 0（重產的型別不能弄壞前端）；CLI 快照 `skills_list`、`skills_show_all` 不變。
3. **QI-2b、2c**：`corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、`corepack pnpm -C client build` 三個結束碼都是 0（分開記）。`render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts` 通過且快照沒有變。
4. **QI-2b**：`git diff --stat <起點>..HEAD -- client/src` 只有新檔與 `dev/`（遊戲畫面不變）；不改 `qIcon/core.ts`、`qIcon/weapons.ts`。
5. **QI-2c `window.__layoutSmoke`**：`corepack pnpm -C client build` 後啟動自己的 `trpg serve`（存檔放暫存區），1600×900、1040×624、800×600 各 `localStorage.clear()` → 開 `/?dev=1&anim=0.1&mute=1` → `await window.__layoutSmoke.runCase("標題")` 全 PASS；另跑 `icons()`（QI-1b 的入口，含技能列、技能卡、工坊）全 PASS。
6. **QI-2c 浮動卡實測**（6.5.1）：1600×900 與 800×600 各做一次「從觸發元素滑進卡片 → 卡內捲到底 → 釘住 → 關閉」：技能列按鈕的技能卡（含卡上的組裝算式部件 `PartTip`）、工坊的選項小圖 `OptionGlyph`、戰鬥紀錄圖釘（已釘／未釘兩態）。結果寫進報告。
7. 截圖存 `docs/art/shots/qi2/`，檔名前綴 `2b-`、`2c-`；每段 ≤ 10 張（D7）；真 1 倍／最近鄰放大特寫用 PNG、其他 jpg 80，單張 ≤ 300 KB；`--force-device-scale-factor=1` 拍；6 倍放大用最近鄰。實機到不了的用開發頁畫並在報告「實機未看」逐項列出。報告寫完整路徑。
8. 需求第 6 節末尾 (a)～(d) 寫進報告：(a) 逐像素對照方式與結果（2b）；(b) 後端推導和 `qskills_derive.derive()` 的逐招比對結果（2a，T-A2）；(c) 舊畫法程式是否已拿掉、哪裡還在用（2c，第 0 節第 11 列）；(d) 「別處依賴原版位」的查證結果（2c）。

### 8.2 截圖分配（對到需求第 6 節 13 項）

「真 1 倍」＝開發頁 `res=1`；「DPR 2」＝`res=2`；最小尺寸兩種都最近鄰放大（張數不夠時照第 0 節第 8 列）。

| 需求項 | 段 | 內容 | 張數估計 |
|---|---|---|---|
| 1 主圖全部長相（約 322） | 2b | 24、28 原大總表：真 1 倍一張、DPR 2 一張（＋逐像素比對數字） | 2 |
| 2 分類總表（道具 56、出手 9、記號 23） | 2b | 40 DPR 2；24 的 ×6 一列 | 1 |
| 3 六招入門招 | 2b | 40、28、24 DPR 2（＋×6） | 併進第 4 項那張 |
| 4 點名款特寫 | 2b | 化身 10、產下幼蜥、召喚守護靈、雙牙（24 真 1 倍）；弓槍配大記號 12＋散彈驅離；地面效果六種、拳套配記號、直線突刺；40／28／24 真 1 倍＋DPR 2，×6 | 2（PNG） |
| 5 實例 78 招：現行｜Q 版 | 2b | 40、24 DPR 2（`&old=1` 並排） | 1 |
| 6 `icon_prop` 36 招 | 2b | 40 DPR 2，每招標道具值；標出第 0 節第 6 列的 6 招 | 1 |
| 7 部件小圓片全部 | 2b | 18 真 1 倍＋DPR 2 原大總表；第 2 版改過的款 ×6；30 DPR 2 | 2（PNG） |
| 8 技能卡小圖 22＋圖釘兩態 | 2b | 16、18、13 真 1 倍＋DPR 2，×6 | 併進第 7 項 |
| 11 修正內容箭頭正負 | 2b | 30 DPR 2；18 真 1 倍 ×6 | 併進第 7 項 |
| 9 技能卡 56 `mid` 24 招＋compact 48 | 2c | 56 真 1 倍＋DPR 2（×6 一列）；48 DPR 2 | 1～2 |
| 10 96 `full` 24 招 | 2c | 96 DPR 2，標出三處改動 | 1 |
| 12 實機每處一張（需求 1.3 全部呼叫處） | 2c | 技能列 40／次要列 28、技能磚 40、配招 24、隊伍 24、召喚面板 28、變奏列 28、靶場選職業 40、技能卡 56（常駐行、效果行、組裝算式 30／18、圖釘兩態）、精簡卡 48、戰鬥紀錄與單位資訊的圖釘、狀態卡的 `ChipGlyph`／`EffectGlyph`／表面圖、工坊 96／40／28＋組裝算式＋選項 26／20／22；裁切合圖，1600 與 800 寬各至少一張 | 4～5 |
| 13 不動的確認 | 2c | 單位頭頂狀態 24、狀態卡狀態 20：改前（2b 合併後的 main）｜改後並排 | 1 |

## 9. 開發中跑的測試

- **QI-2a**：`UV_NO_SYNC=1 uv run pytest -q -n 8 tests/narrative/ tests/content/test_icon_prop_ip1.py tests/content/test_icon_prop_battle_ip1.py tests/content/test_loader.py tests/content/test_coverage.py tests/content/test_skills_content.py tests/api/test_icon_prop_api_ip1.py tests/api/test_client_fixtures.py tests/api/test_openapi_snapshot.py tests/api/test_workshop_api.py tests/api/test_skill_card_stats.py tests/skillgen/test_icon_prop_drop_ip1.py tests/skillgen/test_workshop_check.py tests/test_architecture.py <新測試檔>`；`UV_NO_SYNC=1 uv run pytest -q tests/cli/test_output_snapshots.py -m slow -k "skills_list or skills_show_all"`（交件前一次）；前端 `corepack pnpm -C client exec vitest run src/render/skillIcon.test.ts src/ui/skillCard.test.ts src/world/panelIcons.test.ts src/world/range.test.ts`（讀這兩個快照的檔）。
- **QI-2b**：`corepack pnpm -C client exec vitest run src/render/qIcon/ src/test/importCycles.test.ts <新測試檔>`。
- **QI-2c**：`corepack pnpm -C client exec vitest run src/render/skillIcon.test.ts src/render/glossaryNames.test.ts src/render/qIcon/ src/ui/skillCard.test.ts src/ui/floatCardRule.test.ts src/ui/battleHud.test.ts src/world/panelIcons.test.ts src/world/range.test.ts src/dev/layoutSmoke.test.ts src/test/importCycles.test.ts src/render/unitLook.test.ts <新測試檔>`。
- 每次 commit 前 `corepack pnpm -C client typecheck`（2a 動到 Python 時另跑 `ruff check`、`ruff format --check`、`mypy`、`lint-imports`）；交件前跑第 8.1 節第 2、3 點。

## 10. 報告格式

各段寫 `docs/phases/PhaseQI-2a報告.md`、`PhaseQI-2b報告.md`、`PhaseQI-2c報告.md`：

1. 做了什麼（交付項目逐條，附 commit）。
2. 驗收逐條（測試名稱或指令輸出為證；結束碼分開記）。
3. 改寫的既有測試（舊斷言 → 新斷言）與快照變動說明（2a：JSON 只多 `art` 的比對結果；2c：`render/__snapshots__/` 若有變要逐項說明，沒預期的變動先停下回報）。
4. 需求第 6 節 (a)～(d) 中本段負責的；截圖清單（完整路徑、對到第 8.2 節哪一項、真 1 倍或 DPR 2）；「實機未看」清單。
5. 2a：推導表跨檔參照查到不存在的 ID 清單；T-A1 的「合成」列清單；內容 digest 改前／改後（三個雜湊，同 IP-1 報告第 4 節的寫法）；請使用者重開伺服器檢查的重點（內容檔有新增：進行中的一輪會從頭開始；畫面這段不變）。
6. 2c：浮動卡實測、`__layoutSmoke` 結果表；請使用者重開伺服器檢查的重點（技能列、技能卡右下變骨架徽章、被動／反應左上觸發、工坊 96、圖釘兩態）。
7. 新增的複雜度 noqa（C901、PLR0911／0912／0915；只有改到 Python 時）逐一列理由；前端逐行搬的長函式不拆（和樣張對照用），列出超過 80 行的函式。
8. **待 PM 決定**：最多 10 點，每點附出處；原型數值與解讀類照最保守做完再列。
9. 順手更新上手筆記：2a 更新 `docs/dev/上手-內容資料與模擬.md`（第一節表加 `skill_icon_art.yaml`；第二節「加一個技能」第 8 點補 D4 與 `art`；digest 表下補「推導表改了也會讓一輪重開」；第五節測試表加新測試檔）；2b、2c 更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節加 `qIcon/skills.ts`、`parts.ts`、`legacy48.ts` 與 `skillIcon.ts` 三級的職責；開發入口表加 `skillicon-gallery.html` 的參數；第四節加踩到的坑；第五節測試表加一列）。
