# Phase QI-4b 報告：⑤b 關鍵字接線（`gearIcon.ts`、說明框列關鍵字）＋`statusTile` 縮進色環＋QI-2c 補拍

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-4計畫.md`（第 0.0 節定稿與美術答覆、第 0 節表第 1～6、10～12 點照建議、QI-4b 各節；4c 已拿掉）。起點：main `9882d7d2`（QI-4a 合併）。開發 PM 追加：import 環先拆、`keywordNames` 進 `gearAppearance.json`、實機截圖加 QI-2c 補拍與戰場 `statusTile`；中途追加美術 PM QI-4a 驗收可修 1（`statusTile` 掛鉤圖樣套第④批 `fit()`）。未 push。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| import 環（4a 待決 1） | `resolveGear`、`gearKinds`、`GearLook`、`Resolved`（與它們用到的 `KINDS`、`NO_FORM`、`SLOT_DEFAULT_KIND`、`KEYWORD_OF_ELEMENT`）原樣搬到新檔 `render/gearResolve.ts`（只 import `gearAppearance.json`、`artPalette`、`palette`）；`gearIcon.ts` re-export；`qIcon/skills.ts` 改從 `gearResolve` import。行為不變：既有測試不改一字通過（14 檔 211 項），`importCycles.test.ts` 過 | `76366860` |
| B2 `keywordNames` | `trpg.content.appearance`：新 `keyword_names(table, keywords)`；`appearance_export`／`appearance_json` 多收 `KeywordTable`，輸出多一個鍵 `keywordNames`（照 `keywords` 順序，名稱＝`skill_keywords.yaml` 的 `name_zh`；缺名稱丟 `ValueError`）。`scripts/export_appearance.py` 另載 `skill_keywords.yaml`，重產 `client/src/render/gearAppearance.json`（只多 14 行）。API、OpenAPI 不動 | `b7d48e7f` |
| B1 `gearIcon.ts` | `drawQ` 的舊 `motifs(…)` 換成 `KW.paint(ctx（換成 CSS px 座標）, r.keywords, px, res, { def: gearQDef(…) })`；`KEYWORD_CHIP_MIN_PX = 32` 取代 `SMALL_ICON_MAX_PX`；`drawGear` 第 3 參數 `small` → `chips`（預設 true）；`gearIconCanvas` 傳 `px >= 32`；快取鍵拿掉 `s`／`l` 欄；刪 `motif()`、`motifs()`、`TAU`；`gearQDef` 的回傳型別多寫 `meta.diag?`、`meta.r`（本來就有，給 `paint` 用）。檔頭、`drawGear` 註解改寫；`keywords.ts` 檔頭第 8 行改成「QI-4b 起接到遊戲畫面」 | `2fe2094a` |
| B4 開發頁 | `keyword-gallery.html`：`bare()` 改傳 `chips = false`（否則會畫兩次）；`&live=1` 走遊戲端 `gearIconCanvas`（複製貼上不縮放）；`&set=live` 頁內組合 vs 遊戲端逐像素比，結果在 `body.dataset.live` | `2fe2094a` |
| B3 說明框 | 新 `gear/gearKeywords.ts`：`keywordName`、`gearKeywordLine(look, slot)`（「關鍵字：點燃、潮濕」或 `null`）、`withKeywordLine(lines, look, slot)`。`itemTipLines(item, slot?)` 在詞條行（或「（沒有詞條）」）之後接這一行；呼叫處 `BagScreen.wornTipLines`、`RunHeroPanel`、`GearCardView` 比較列傳 `slot`；`HeroGearPanel`、`UnitInfo` 在呼叫端 `withKeywordLine(tipLines(e.affixes), e.appearance, e.slot)`（`tipLines` 簽名不變）；`GearCardView` 的 `gear-card-lines` 多一個 `li[data-testid=gear-card-keywords]`（「沒有詞條」那一列判斷不變） | `04e56f39` |
| B5 測試 | 新 `render/qi4bGearKeywords.test.ts`（T-B1～T-B3、T-B5、T-B7，13 項）；改寫 5 項既有測試（第 3 節）；pytest 加 2 條 | `2fe2094a`、`04e56f39`、`b7d48e7f` |
| 追加：`statusTile` 縮進色環 | `parts.ts` 的 `fit` 只加 `export`；`skillParts.ts` 的 `hooks.status`：`status.ts` 認得的圖樣，非 `stance_*` 套 `QP.fit(…, STATUS_TILE_FIT = 0.86)`，`stance_*`（六角臂章）照舊不縮（新匯出 `STATUS_TILE_FIT`、`statusTileFits`）。重錄 `qi3bStatusBaseline.json`：只有 38 筆變（第 3 節） | `13c8a608` |
| 追加：開發頁 | `status-gallery.html?set=tile`：`&nofit=1`（每格上方並排 QI-4a 沒縮的圖樣＝改前）、`&ids=`（只列這些狀態） | `6bb517bb` |
| B6 截圖、報告、上手筆記 | `docs/art/shots/qi4/4b-*` 7 張；本報告；上手筆記 | `30acc3ff`、本 commit |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| T-B1 | 接線 | 過：105 款 × 32／40／42／48／64 × res 1、2（1050 組，關鍵字 12 組輪流）：`chips = true` 的假畫布紀錄＝`chips = false` 的紀錄＋直接呼叫 `keywords.paint` 的紀錄（關鍵字層排在最後）；沒有關鍵字時不多畫；`gearIconCanvas` 原始碼是 `px >= KEYWORD_CHIP_MIN_PX`（20、31 不畫，32 起畫）；圓章只有一個（底色只出現 `keywords[0]`） |
| T-B2 | 快取鍵 | 過：10 欄、尾兩欄＝px、res；32≠36；屬性順序無關 |
| T-B3 | 舊畫法拿掉 | 過：`gearIcon.ts` 沒有 `motif`／`motifs` 的定義與呼叫、沒有 `SMALL_ICON_MAX_PX`；全專案沒有從 `gearIcon` import 它們 |
| T-B4 | `keywordNames` | 過：前端 12 個鍵＝`keywords` 順序，`high_ground` → 高處、`summon` → 召喚物；pytest `test_keyword_names_follow_skill_keywords_yaml`、`test_keyword_names_reject_unknown_keyword`、`test_client_json_is_up_to_date` |
| T-B5 | 說明框 | 過：`gearKeywordLine` 0／1／2 個、不認得、`element: "fire"`（元素關鍵字排第一、截 2 個）；`itemTipLines` 沒有關鍵字時和改前逐字相同；原始碼掃描確認 5 個呼叫處與 `gear-card-keywords` |
| T-B6 | 既有測試改寫 | 第 3 節 |
| T-B7 | 不動的確認 | 過：新測試鎖「chips 的紀錄以不畫關鍵字層的紀錄開頭」。另做一次性比對（暫存檔，跑完刪掉）：把 `76366860` 版 `gearIcon.ts` 放在旁邊，105 款 × 4 組關鍵字（含空、元素）× 3 稀有度 × 5 尺寸 × res 1、2＝12600 組，新 `chips=false`＝舊 `small=true` 逐筆相同、新 `chips=true` 的前段也相同 → 框、稀有度、主圖、寶石色、元素混色沒變 |
| B4 | `live=0`／`live=1` 逐像素 | 過：`keyword-gallery.html?set=live`（無頭 Chrome、`--disable-gpu`）105 款 × 32／42／48／64 × res 1、2 共 840 組，**840 組 0 像素不同** |
| 追加 | `statusTile` 縮進 | 過：`qi4aStatusTile.test.ts` 改寫那條鎖住「38 個＝`fit(0.86)` 包 `entry(id).d`、48 個 `stance_*`＝直接畫」；截圖 `4b-01` |
| 8.1-2 | 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（302 檔、3852 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告） |
| 8.1-2 | 快照 | `render/__snapshots__/` 沒有變動，`inkDollSnapshot`／`creaturePose` 在整包通過 |
| 8.1-3 | Python | `uv run ruff check .`、`ruff format --check .`、`mypy`（1456 檔）、`lint-imports`（14 kept）全過；pytest 見第 2 節末 |
| 8.1-5 | `__layoutSmoke` | 自己的 `trpg serve`（8152、存檔放暫存區）：`runCase` 1600×900、1040×624、800×600 **全 PASS**；打開背包後 `icons()` 三尺寸**全 PASS**（23 個圖示；顯示 32、42、48（800 寬 38）、64；身上裝備格 9 個左上角對齊裝置像素）。`runTown` 在打開背包**前**跑時，「實地・圖示」一列 FAIL＝「頁面上沒有圖示畫布」（背包還沒開，筆記第二節 4 寫明要先開背包），其他列全 PASS |
| 8.1-6 | 浮動卡實測 | 1600×900（頭）與 800×600（身體）：滑過身上裝備格圖示 → 卡片開、內容含「關鍵字：帶電、倒地」／「關鍵字：冰凍、隱蔽」→ 沿直線滑進卡片仍開著 → 卡內捲動：內容一次放得下（`scrollHeight − clientHeight = 0`，沒有可捲的）→ 點一下釘住（`.pinned`）→ 滑鼠移走仍在 → Esc 關閉。兩個尺寸都過 |
| 8.1-7 | 截圖 | 第 4 節，7 張，單張 ≤ 273 KB |
| 相關測試 | — | `vitest run src/render/gearIcon.test.ts src/render/qIcon/ src/gear/ src/run/ src/ui/gear/ src/world/bagScreen.test.ts src/ui/floatCardRule.test.ts src/dev/layoutSmoke.test.ts src/test/importCycles.test.ts src/test/sourceScan.test.ts src/render/qi4bGearKeywords.test.ts …` 全過 |

pytest：`UV_NO_SYNC=1 uv run pytest -q -n 8 tests/content/ tests/api/test_client_fixtures.py tests/api/test_openapi_snapshot.py` 結束碼見第 2.1 節。

### 2.1 slow 測試結束碼

`UV_NO_SYNC=1 uv run pytest -q -n 8 tests/content/ tests/api/test_client_fixtures.py tests/api/test_openapi_snapshot.py`：結束碼 **0**，2960 passed（6 分 37 秒）。

**內容 digest／規則包雜湊**：`content/` 沒有任何改動（`git diff --stat 9882d7d2..HEAD -- content/` 無輸出）；`appearance_export` 不進規則包，`tests/content/` 的 digest 相關測試照過。

## 3. 改寫的既有測試、基準與快照

**既有測試（舊 → 新）**

1. `render/gearIcon.test.ts` 輔助 `draw(look, small = false)` → `draw(look, chips = true)`（第 3 參數語意反過來，呼叫處跟著翻）；「造型 × 形制 × 稀有度 × 大小圖 × 染色」改「× 畫不畫關鍵字層」（同樣兩種都跑）；`drawGear(ctx, undefined, true, "head")` → `false`（同樣「不畫關鍵字層」）。
2. 同檔「小圖不畫關鍵字小圖樣，大圖會畫」→「chips = false 不畫關鍵字層，chips = true 會畫」；「小圖仍保留元素混色」→ 用 `chips = false`。
3. 同檔「快取鍵包含是否小圖；36px 以下為小圖」→「32px 以上畫圓章；快取鍵含 px、不再有『是否小圖』那一欄」（`KEYWORD_CHIP_MIN_PX === 32`、10 欄、尾兩欄 px／res、32≠36）。
4. 同檔「1 個關鍵字兩處都畫，2 個關鍵字各畫一處」→「只畫一個圓章：1 個沒有記號，2 個多一個點版記號」（兩個時紀錄比一個多）。
5. `render/qIcon/qIconArmor.test.ts` 207 行 `px <= 36` → `px >= 32`（同 `gearIconCanvas`）；222 行錘柄測試 `true`（舊 small）→ `false`（不畫關鍵字層，同義）；「小圖仍保留元素混色；>36px 畫關鍵字小圖樣」→「不畫關鍵字層時仍保留元素混色；≥32px 畫關鍵字圓章」，多一條「32 現在也畫」（舊：36 以下不畫）。
6. `render/qIcon/qIconWeapons.test.ts` 201 行 `false`（舊 small＝false）→ `true`（chips），同義。
7. `render/qIcon/qIconKeywords.test.ts` T-A9「gearIcon.ts、GearIcon.tsx 沒有用到 keywords.ts」（4a 鎖不接線）→「gearIcon.ts 用 keywords.ts、GearIcon.tsx 只經 gearIcon.ts」。
8. `render/qi4aStatusTile.test.ts`「86 種＝掛鉤直接畫 entry(id).d」→「`stance_*` 48 個直接畫、其他 38 個＝`fit(0.86)` 包 entry(id).d；38 個和直接畫不同；都不是舊圖樣」。
9. `tests/content/test_appearance.py::test_client_json_is_up_to_date` 改傳 `library().keywords`。

`gear/gearPreview.test.ts`：不用改（只比較同 px 的鍵是否相同）。

**`qi3bStatusBaseline.json`（`statusTile` 縮進色環，同一段 `record()` 逐鍵重錄、鍵順序與格式不變）**：236 筆中**只有 38 筆變**，全部是 `head|<id>`，名單＝4a 的 86 個裡不是 `stance_*` 的：

armor_broken、array_ward、charging、commanding、crystal_surge、crystal_surge_2、entangled、frost_ember_burst、hard_shell、heart_ember_burst、heart_link、league_truce、mist_return、molten_burst、molten_shell、oath_bonus_easy、oath_bonus_hard、oath_bonus_medium、oath_broken、overdrawn、race_adapt、race_stonewall、rallied、revealed、rift_channel、rift_collapse、rift_resonance、shard_burst、shielded、shielded_marking、shielded_mending、shielded_thorns、shielded_wet、soul_link、summit_array_ward、sword_formation、time_bomb、undying。

證明來自這項改動：重錄前工作樹相對 `04e56f39` 只改了 `parts.ts`（`fit` 加 `export`）與 `skillParts.ts` 的掛鉤；`04e56f39` 時舊基準在 `qi2cStatusUnchanged` 全過（同一輪相關測試）；重錄後 `git diff` 只有上面 38 行（38 增 38 刪），48 個 `head|stance_*`、32 個第④批 `head|`、118 個 `card|` 一筆沒動。`qi2dBaseline.json` 不經掛鉤（4a 已證、`qi4aStatusTile.test.ts` 仍鎖住），不動。

快照 `render/__snapshots__/` 沒有變動；沒有整批重產任何 fixture。`gearAppearance.json` 只多 `keywordNames`（第 1 節）。

## 4. 需求第 5 節末 (b)、(c)；截圖；實機未看

**(b) 舊 `motif()` 的去留**：刪了（`motif`、`motifs`、`SMALL_ICON_MAX_PX`）。開發頁 `keyword-gallery.html?set=legacy` 的頁內抄本（樣張 `legacy()`）留著對照。`qIcon/weapons.ts` 檔頭第 7 行提到「`motif()`」與兩個定義的 `meta.spots` 照規格不動（現在沒有人讀 `spots`）。

**(c) 說明框有沒有列出全部關鍵字**：列「圖示代表的那幾個」＝`resolveGear(look, slot).keywords`（認得的、最多 2 個、武器表元素換成的元素關鍵字在前），和圓章、點用同一份。加在：背包身上裝備格說明卡（`BagScreen.wornTipLines` → `itemTipLines`）、跑團主角面板（`RunHeroPanel`）、裝備卡本體（`GearCardView` 的 `gear-card-keywords`，背包「詳情」與戰後三選一）與其「目前的」比較列說明卡、戰鬥主角面板 `HeroGearPanel`、單位資訊 `UnitInfo`。不加：背包格 42 的 `<Hint>`（點下去就開 `GearCardView`）、郵件／獲得動畫 32、靶場起始武器 40。物品有第 3 個會產生關鍵字的詞條時，後端 `derive_keywords(limit=2)` 已截掉，前端看不到（詞條行仍列）。

**截圖**（`docs/art/shots/qi4/`）

| 檔 | 對到 | 內容 |
|---|---|---|
| `docs/art/shots/qi4/4b-01-statustile-fit-before-after-18-24-26-x4.png` | 追加（美術 QI-4a 可修 1） | `status-gallery?set=tile&nofit=1`：護盾、心連結、戰意、帶電護盾（第④批對照）、水幕護盾、定時炸彈、蓄力、劍陣 × 18／24／26 × 真 1 倍與 DPR 2，最近鄰 ×4；每格上＝改前（4a）、下＝改後 |
| `docs/art/shots/qi4/4b-02-battle-bomb-charge-statustile-dpr3.png` | 4a 待決 7、`statusTile` 實機 | 實機戰場（單場戰鬥）定時炸彈 2、蓄力 1 徽章，DPR 3 特寫（筆記第四節 18 的做法） |
| `docs/art/shots/qi4/4b-03-bag-1600-tooltip-keywords.jpg` | 第 7 項實機 1600 | 背包：身上裝備格 fit 48、背包格 42、詳情卡 64＋「目前」32、頭的說明卡含「關鍵字：帶電、倒地」；詳情卡含「關鍵字：冰凍、召喚物」 |
| `docs/art/shots/qi4/4b-04-bag-800-tooltip-keywords.jpg` | 第 7 項實機 800 | 同上 800×600（身上裝備格 38），身體的說明卡含「關鍵字：冰凍、隱蔽」 |
| `docs/art/shots/qi4/4b-05-qi2c-workshop-card56-1600-800.jpg` | QI-2c 補拍（驗收 1 節第 8 項） | 技能工坊「技能卡片預覽」56 mid，1600、800 |
| `docs/art/shots/qi4/4b-06-qi2c-workshop-800-96-40-28.jpg` | QI-2c 補拍（第 9 項） | 技能工坊 96 full／40／28 main，800（右 1600 對照） |
| `docs/art/shots/qi4/4b-07-qi2c-worn-slots-1600-true1x-x6.png` | QI-2c 補拍（第 12 項） | 1600×900 裝置像素比 1 的身上裝備格（主手、副手、頭、身體）最近鄰 ×6；畫布左上 (457,284)…(643,284) 都是整數 |

**實機的資料是造的**：開發角色只有入門單手劍、背包是空的，戰鬥單位也沒有定時炸彈／蓄力。截圖與浮動卡實測時在**自己的無頭 Chrome** 用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch`：大世界回應的穿戴中 9 格與背包 12 件換成示範裝備（造型、稀有度、1～2 個關鍵字、詞條文字都是假的），戰鬥回應給兩個敵人加 `time_bomb`（2）、`charging`（1）（同 QI-3b 的做法，筆記第四節 46）。程式與後端都沒動；圖示、說明卡、徽章都是遊戲端照這些資料畫的。

**實機未看**：主角面板 `HeroGearPanel`、單位資訊 `UnitInfo` 的 32 與它們的說明卡「關鍵字」行（只有原始碼掃描＋純函式測試；32 的圓章在 `4b-03` 的「目前」那一格看得到）；跑團主角面板 `RunHeroPanel`；戰後三選一（`GearCardView` 同元件，背包詳情已拍）；組裝列 18／工坊狀態選項 26 的 `statusTile`（只有開發頁 `4b-01`）。

## 5. 待 PM 決定

1. **`statusTile` 縮進的範圍與係數**：k 用 0.86（同第④批「帶電護盾」，讓「護盾」和它一樣大）；六角臂章 `stance_*`（48 個）**不縮**——第④批的姿態臂章 `stance_guard`／`stance_fury`／`stance_holy_1`… 也沒套 `fit()`，縮了反而兩套不一樣大（美術驗收也寫六角「色環仍露得出來」）。所以實際改的是 38 個，不是「86 種都縮」。若美術要 86 個全縮，或要第④批預設的 0.84，改 `skillParts.ts` 的 `statusTileFits`／`STATUS_TILE_FIT` 一行並重錄基準。（出處：開發 PM 追加原話「讓 86 種都縮進環內」；`docs/art/QI-4a驗收.md`（`a115e135`）第 2 節）
2. **`runTown` 的「實地・圖示」一列在背包打開前會 FAIL**（頁面上沒有圖示畫布）：照筆記「背包要先打開才量得到」，打開後 `icons()` 全 PASS。是否要讓 `runTown` 沒有圖示時改成「略過」而不是 FAIL，另排。（`dev/layoutSmoke.ts` `runTownWith`）
3. **身上裝備格 800 寬是 38，不是筆記寫的 39**（`fitIconPx`；這次量到 `world-worn-box` 內容寬 42.x）。≥ 32 照樣畫圓章，不影響；筆記已改成「約 38～39」。
4. **`appearance_export` 簽名多一個必填參數 `keywords: KeywordTable`**：目前只有匯出腳本與測試呼叫；選必填是為了不讓匯出漏掉名稱（缺名稱丟例外）。
5. **說明框「關鍵字」行的位置**：放在詞條行之後（入門武器的 `opening_note_zh` 照舊在最前）；`GearCardView` 是 `gear-card-lines` 最後一個 `li`（「沒有詞條」之後）。樣式沿用 `li`，沒有另設顏色。
6. **一次性的 T-B7 比對沒有留成測試**（要留舊版 `gearIcon.ts` 當參考檔才跑得了）；留在報告為證，常駐測試只鎖「前段相同」。

## 6. 給使用者的檢查重點（重開伺服器後）

- 背包（42）、身上裝備格（fit）、主角面板與單位資訊（32）、裝備卡（64）：裝備圖示角落多一個 Q 版關鍵字小圓章，有第二個關鍵字時旁邊一個小點；32～36px 從「不畫」改成「畫一個圓章」；器物上的細線小圖樣沒了。
- 滑過身上裝備格、主角面板、單位資訊的裝備：說明卡最後一行「關鍵字：…」；背包詳情與戰後裝備卡也多這一行。
- 戰場定時炸彈／蓄力徽章、組裝列與工坊的狀態圓片：護盾、心連結、戰意等大輪廓縮進色環（和「帶電護盾」一樣大）；六角臂章不變。
- 需求第 6 節「交使用者時要講明」6 點（原樣轉列）：見 `docs/art/Q版小圖示-關鍵字移植需求.md` 第 6 節（42 點偏弱、點色只分大類、橘綠色盲、關鍵字色與圖樣不一致、同題材不同形等），本段沒改。

## 7. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：檔頭 QI-4 那句；第一節表 `gearIcon.ts` 列（新 `gearResolve.ts`、門檻 32、`chips`、`motif()` 拿掉）、`qIcon/keywords.ts` 列（已接線）、`skillParts.ts` 列（`statusTile` 掛鉤縮進色環）、新 `gear/gearKeywords.ts` 列；開發入口表 `keyword-gallery`（`&live=1`、`set=live`）、`status-gallery`（`&nofit=1`、`&ids=`）；第四節第 28、47、51 點改寫，新增第 54～56 點；第五節測試表加一列。
