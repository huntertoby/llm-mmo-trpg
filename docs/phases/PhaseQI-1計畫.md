# Phase QI-1 計畫：Q 版小圖示移植第 1 段（武器＋副手＋防具飾品）

> 草稿（開發 PM 助手 2026-11-12，依據 main `47cea90f`）。開發 PM 確認開頭的「待開發 PM 確認」後再定稿、push、派工。
> 美術依據：`docs/art/Q版小圖示-武器防具移植需求.md`（以下簡稱「需求」，引用寫「需求 x.y」）；樣張以 `docs/art/sample/` 的 `qIcons.js`、`qIconsWeapons.js`、`qIconsArmor.js` 為準（`0caaa84f` 之後）。
> 對應 `docs/開發PM交接.md` 3.000 第 4 點的「①武器副手＋②防具飾品」。工作量超過一段上限，**切成 QI-1a、QI-1b 兩段，依序做**（第 4 節）。

## 0. 待開發 PM 確認

規格內暫採的做法寫在「暫採」欄；確認後改掉這張表的對應列。

| # | 問題 | 出處 | 暫採 |
|---|---|---|---|
| 1 | D3 寫「畫布尺寸＝CSS 顯示尺寸 × devicePixelRatio」，D4 寫「內部解析度固定 2 倍」。若照字面讀 `window.devicePixelRatio`，100% 縮放螢幕會變成 1 倍，和 D4 衝突 | PM 決定 D3、D4 | 「dpr」讀成固定的內部解析度 `ICON_RES = 2`：畫布寬高＝`round(CSS px × 2)`，不讀 `window.devicePixelRatio` |
| 2 | 身上裝備格 `.world-worn-box .gear-icon` 是 `min(48px, calc(100% - 4px))`，隨面板寬在 40～48 之間變、可能是小數；「照顯示尺寸出圖」要在執行期量 | `client/src/styles/world-economy.css` 54–58 行、`.world-worn` 49–58 行；需求 3.1 第 3 點、第 4 節第 4 點 | `GearIcon` 量外層格子的內容寬，取 `min(48, floor(內容寬 − 4))` 的整數 CSS px，顯式設寬高；CSS 的縮放規則拿掉 |
| 3 | **圖示的材質色和遊戲端 Q 版人物不同一份**：需求說圖示用「人物那一份」（鐵 `#8d969f`、鋼 `#c3ccd6`、銅 `#c27a48`），但遊戲端 Q 版人物實際走 `GAME_HOOKS` → `itemColors` → `material.ts`（鐵 `#7a828b`、鋼 `#a9b6c6`、銅 `#b06a3c`）；樣張那一份 `qSample.ts` 只給開發頁。結果：實機上鐵、鋼、銅的圖示會比手上那把亮一階；驗收第 13 項「和人物並排」會看得出來 | 需求 2.4 第 7 列、3.3 第 20 點；`client/src/render/qSpec.ts` 13 行、`itemColors.ts`、`material.ts`、`qSample.ts` 1–14 行 | 照需求：圖示另開一張表照樣張，不改 `material.ts`；並排截圖照實交，報告寫明差異。請美術 PM 確認是否接受，或改成圖示也用 `material.ts` |
| 4 | **截圖張數與格式**：需求第 5 節 13 項、最小尺寸兩種解析度、6 倍最近鄰放大，估計 QI-1a 約 14 張、QI-1b 約 16 張（每張 ≤ 1600×1600），超過 6.5.2 的 10 張；另外 jpg 80 會在 6 倍放大的硬邊上產生壓縮雜訊，正好壓在美術要看的「1px 外框是不是硬邊」上 | `docs/開發PM交接.md` 6.5.2；需求第 5 節 | 照 6.5.2 存 jpg 80、每段先以 ≤ 10 張為目標（合圖），不夠時照第 8.2 節的張數上限交並在報告列出；建議放寬為「真 1 倍與 DPR 2 的 6 倍特寫可用 png、每段上限 16 張」 |
| 5 | 切段後兩段都要改 `client/src/render/gearIcon.ts`（1a：武器副手分支與貼圖流程；1b：防具飾品分支、拿掉 `D` 表）。派工說「改的檔不重疊」 | 本規格第 4 節 | 1b 在 1a 合併後才開始（不平行），所以不衝突；其餘檔案不重疊 |
| 6 | D1 也會改到人物：`dollItem()` 用 `resolveGear()`，沒寫 `form` 的錘從釘頭錘（單手）變戰錘（`isTwoHandedPart` 變雙手）。目前內容資料沒有這種物品，只有 1a 之前產生、存在存檔裡的錘（`item_gen` 抄 `weapons.yaml` 的 `look.form`，現在是 `null`）會受影響 | `client/src/render/dollGear.ts` 67–77、109–112 行；`src/trpg/content/item_gen.py` 142–150 行 | 照 D1 一起改（人物、圖示都變方頭，和需求「三處都是方頭」一致；`hammer` 本來就是雙手武器） |
| 7 | 需求 1.3 與第 5 節第 10 項寫 `RangeClassPick` 是 48px，但實際顯示是 40px（`.ob-kit-row canvas.gear-icon`），D3 也說「套組 40」 | 需求 1.3、第 5 節第 10 項；`client/src/styles/range-ob.css` 184–187 行 | 照 D3 直接畫 40；第 10 項截圖拍 40 |
| 8 | 關鍵字小圖樣：需求 2.4 第 9 列說「樣張示意時縮 0.75」，3.4 第 22 點說「照現行 `motif()` 接、這一段不重畫」，沒寫移植時要不要縮 | 需求 2.4 第 9 列、3.4 第 22 點 | 照現行大小（不縮），位置改用 `meta.spots` 換算 |
| 9 | 舊的墨線小圖示路徑（`inkStyle.withIconMode`／`iconHead`、`inkGear` 的 `inIconMode` 分支、`shortWeaponIcon.test.ts`）換完後沒人用；需求 5 (b) 要報告舊程式是否拿掉 | `client/src/render/inkStyle.ts` 104–140 行、`inkGear.ts` 111–133 行 | 這一段不刪（會動到人物畫法檔與快照），報告列為死碼、另排整理 |
| 10 | 子 agent 模型：本次派工說一律 Opus 5.5；`docs/開發PM交接.md` 3.000 第 2 點寫 Fable 5.2 | 派工訊息；交接 3.000 | 照本次派工（Opus 5.5），請開發 PM 定案後改第 3 節 |

## 1. PM 決定

| # | 決定 | 出處 |
|---|---|---|
| D1 | `resolveGear()` 遇到沒寫 `form` 的 `hammer`：退成 `warhammer`（照美術建議，同樣張 `NO_FORM`）；其他種類照舊退第一款 | 需求第 4 節第 2 點；開發 PM 2026-11-12 |
| D2 | `GearLook` 先不加 `color`（不擋本段；需要時另排）。快取鍵不含 `color` | 需求第 4 節第 3 點 |
| D3 | 背包格 42、套組 40、身上裝備格 `min(48px…)`：照實際顯示尺寸出圖（畫布尺寸＝CSS 顯示尺寸 × 內部解析度），不靠 CSS 縮放；寫測試鎖住「畫布像素尺寸等於顯示尺寸 × 內部解析度」 | 需求第 4 節第 4 點（解讀見第 0 節第 1、2 列） |
| D4 | 內部解析度本段維持固定 2 倍，不改（列為後續）。開發頁另外可以切 1 倍（只給驗收截圖用） | 需求第 4 節第 5 點 |
| — | `content/weapons.yaml` 的 `hammer` 補 `look: {kind: hammer, material: iron, form: warhammer}` | 需求第 4 節第 1 點（已決定，排入本段） |

## 2. 目標與範圍外

**目標**：把武器小圖示（米色圓章）與裝備格裡的武器、副手、防具、飾品圖樣，換成美術第 1、2 批的 Q 版圖樣；框（圓章 CSS、`frame()`、`motif()`）不動。成對武器的圖示畫兩把；錘一律方頭；裝備格在 40、42 與身上裝備格也直接畫在顯示尺寸。

**範圍外**：技能主圖、徽章與部件（③④，含後端 `narrative/skill_icon.py`）、狀態圖示（⑤）、HUD 與事件卡（⑦⑧）、物品圖示（⑥）；人物（`qDoll` 系列）畫法；關鍵字小圖樣重畫；`material.ts` 的顏色；內部解析度改成跟螢幕走（D4）；`GearLook.color`（D2）；需求第 6 節的「可修」項目；樣張端 `gearArt.js`（需求第 7 節）；刪舊墨線小圖示程式（第 0 節第 9 列）。

## 3. 工作環境

- Windows、Git Bash。Python 一律 `uv run python`（不要直接打 `python`）；前端 `corepack pnpm -C client …`。
- 新 worktree 第一次：`uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`；之後 Python 指令加 `UV_NO_SYNC=1`。
- 預覽埠：QI-1a 用 vite 5260～5264、`trpg serve`／靜態伺服器 8126～8128；QI-1b 用 5265～5269、8129～8130。**不用 8000、8001、5195。** vite 的 `/api` 寫死轉 8000，要接自己的 `trpg serve` 就另寫暫存設定檔（上手-前端第四節第 13 點），不改 `vite.config.ts`。
- 瀏覽器網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`、截圖用 `--force-device-scale-factor=1`（裝置像素比 1，需求第 5 節）。
- 結束前用自己記下的 PID 關掉 vite、`trpg serve`、靜態伺服器與無頭 Chrome，確認沒有殘留；不用 `taskkill /IM`、`pkill`。
- 等背景程序用完成通知，不寫 `until`／`while` 輪詢迴圈。
- 子 agent 一律指定 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣（第 0 節第 10 列）。
- 只跑相關測試（第 9 節）；不跑 `scripts/check.py`、不跑模擬。不要 push。
- 要讀的：`CLAUDE.md`；`docs/dev/上手-前端戰鬥畫面與動畫.md`（全文）；QI-1a 另讀 `docs/dev/上手-內容資料與模擬.md` 第二節「內容 digest」、第四節第 13 點、第六節；需求全文；`docs/art/上手-畫法.md` 2.1、2.4、2.5；`docs/art/Q版小圖示-第1批武器.md` 第 9 節（1a）、`Q版小圖示-第2批防具飾品.md` 第 9 節（1b）。

## 4. 切段

估計：三個樣張檔共約 210 KB（`qIcons.js` 66 KB 其中本段只用到第 1～202 行與 `render`／`badgeScale` 一帶、`qIconsWeapons.js` 72 KB、`qIconsArmor.js` 72 KB），逐行搬成 TS 加測試與截圖，一個 agent 會超過 25 萬 token。

| 段 | 內容 | 改的檔（主要） |
|---|---|---|
| **QI-1a** 共用核心＋武器副手 | `qIcons.js` 共用部分、`qIconsWeapons.js` 全部；`weaponIcon.ts`、`drawGear()` 的 `weapon`／`offhand`；`resolveGear` D1；`weapons.yaml`＋快照；武器開發頁 | 新 `client/src/render/qIcon/`（`core.ts`、`weapons.ts`，檔名可調）、`render/weaponIcon.ts`、`render/gearIcon.ts`、`content/weapons.yaml`、`client/src/battle/fixtures/glossary.json`（重產）、`dev/weaponIconGallery.ts`、`client/dev/weaponicon-gallery.html`、相關測試 |
| **QI-1b** 防具飾品＋顯示尺寸 | `qIconsArmor.js` 全部；`drawGear()` 的防具飾品、拿掉 `D` 表；D3（40、42、身上裝備格）；裝備開發頁；排版檢查加一項；實機截圖 | 新 `client/src/render/qIcon/armor.ts`、`render/gearIcon.ts`（1a 合併後）、`ui/GearIcon.tsx`、`ui/WeaponIcon.tsx`、`world/BagScreen.tsx`、`world/RangeClassPick.tsx`、`styles/world-economy.css`、`styles/range-ob.css`、`dev/gearGallery.ts`、`client/dev/gear-gallery.html`、`dev/layoutSmoke.ts`、相關測試 |

QI-1b 在 QI-1a 合併後才派。共用的只有 `gearIcon.ts`（第 0 節第 5 列）。

## 5. 受影響的既有功能

| 區塊 | 受影響的 | 改／不改 | 理由 |
|---|---|---|---|
| 引擎 | 無（`look` 只影響外觀；規則包 `Ruleset` 不含武器表） | 不改 | — |
| 內容資料 | `content/weapons.yaml` 的 `hammer.look` | 改（1a） | 需求第 4 節第 1 點 |
| 內容資料 | `item_gen._weapon_base` 抄 `weapon.look.form`：之後產生的錘帶 `form: warhammer` | 不改程式 | 資料改了自然跟上；`tests/content/test_item_gen.py` 要跑 |
| 內容 digest／存檔 | `roguelite/save.ruleset_hash`、`world/save.content_digest` 會變：使用者重開伺服器後進行中的一輪從頭開始、舊世界日誌標成不能重播 | 不改（不加版號） | 上手-內容第二節：只改 `content/` 不加版號；回報 PM 時附重開提醒 |
| 存檔中的舊物品 | 1a 之前產生的錘 `form` 為 `null` → D1 後畫成戰錘（人物也是，第 0 節第 6 列） | 不改資料 | D1 |
| 前端快照 | `battle/fixtures/glossary.json`：`weapon_looks` 的 `hammer.look.form` 由 `null` 變 `"warhammer"`。`unitDolls.json`、`raceLooks.json`、`skillCards.json` 不含錘（查過 0 筆），預期不變 | 重產（1a） | `tests/api/test_client_fixtures.py` 會擋沒重產的 |
| API／型別 | 無（欄位不變） | 不改 | `openapi.json`、`schema.d.ts` 不動 |
| 工坊 | `ui/gear/CustomItemForm.tsx`（64）、`SlotGrid.tsx`（64）、`ItemList.tsx`（48）的預覽圖示換成 Q 版 | 不改元件 | 只換畫法；裝備資料（`/api/gear` 的 `look`）不變 |
| 隨機組合器、LLM 提議 | 無（不產生外觀欄位） | 不改 | — |
| 人物（紙娃娃、Q 版小人） | `dollGear.dollItem` 經 `resolveGear` 受 D1 影響（第 0 節第 6 列）；`pairedPart` 照舊（人物仍一手一把） | 只受 D1 影響 | 需求 2.4 第 11 列 |
| 武器圓章 `WeaponIcon` | `RunHeroPanel`（24）、`StartPicker`、`RangeParts`（20）：換 Q 版、成對畫兩把、不再呼叫 `measure()`／`iconAngle()`／`drawInkWeaponAlone()` | 改畫法（1a） | 需求 3.2 第 9、10 點 |
| 裝備格 `GearIcon` | 32：`RunHeroPanel`、`HeroGearPanel`、`UnitInfo`、`GearCardView`（目前裝備）、`GainEffects`、`MailPanel`；48：`ItemList`；64：`GearCardView`、`SlotGrid`、`CustomItemForm` | 改畫法（武器副手 1a、防具飾品 1b） | 需求 1.3 |
| CSS 縮放的三處 | 背包 `BagScreen` 48→畫 42；身上裝備格 48→畫量到的尺寸；套組 `RangeClassPick` 48→畫 40 | 改（1b） | D3 |
| `RangeClassPick` 入門武器 | `weaponIconItem()` 不再 `pairedPart()`：雙匕首、雙手槍的入門武器圖示從單把變兩把 | 改（1a，預期） | 需求 3.2 第 10 點 |
| 樣式 | `.weapon-icon`（`theme.css` 329 行、`gear.css` 21 行）、`frame()`、`motif()`、`SMALL_ICON_MAX_PX` | 不改 | 需求 1.2 |
| 開發頁 | `weaponicon-gallery.html`、`gear-gallery.html` 要列全部款式並能切 1 倍與放大 | 改（1a、1b） | 驗收截圖用（第 8 節） |
| 排版煙霧檢查 | 加「圖示畫布沒被縮放」一項 | 改（1b） | D3 要求測試鎖住 |
| 既有測試 | `render/weaponIcon.test.ts`（`iconAngle`／`isDiagonal`）、`arcaneBlade.test.ts` 84–87 行、`weaponLooks.test.ts` 65、137、173 行一帶（小圖示斜放、成對畫單把）、`gearIcon.test.ts`（「成對武器畫兩把」「不認得的形制退回第一個」等） | 改寫成 Q 版的對應斷言（不放寬） | 舊斷言描述的是被換掉的畫法；每個改動在報告逐條說明 |
| 舊墨線小圖示 | `inkStyle.withIconMode`／`iconHead`、`inkGear` 圖示分支、`shortWeaponIcon.test.ts` | 不改（留死碼） | 第 0 節第 9 列 |

## 6. 交付項目

### QI-1a

- **A1 共用核心**：`client/src/render/qIcon/core.ts`（檔名可調），由 `docs/art/sample/qIcons.js` 逐行搬：外框色 `OUT`、`M`（樣張材質色，第 0 節第 3 列）、`EL`、畫法小工具 `H`、剪影外框（`dilate`、`halo`）、`render(def, px, res, opt)`、`outlinePx`、`badgeScale`／`badgeOf`、`GEAR_PAD`、`blit()`（需求 3.1 第 1 點的程式），以及第 1 批用到的八把樣本畫法 `W`（含 `W.diag`、`W.towerShield`、`W.arcaneArt`）。技能、物品、狀態、HUD 那幾區不搬。建立畫布集中在一個可注入的函式，讓 vitest 能用假畫布。
- **A2 武器副手畫法**：`client/src/render/qIcon/weapons.ts`，由 `qIconsWeapons.js` 逐行搬全部 17 種 53 款＋副手 4 種 8 款的 `def`／`pre`／`post`／`meta`、`palette`（含稀有度護手換色，需求 3.2 第 14 點）、`crossed()`、鞭兩種構圖等（需求 3.2 第 11～13 點）。**不搬樣張的 `resolve()`、`NO_FORM`、`shock`／`freeze` 別名**：一律吃 `resolveGear()` 的結果（需求 2.2 第 2 點、2.4 第 1 列）。關鍵字只認 `charged`／`frozen` 等新名。
- **A3 `resolveGear` D1**：`render/gearIcon.ts`，`hammer` 沒寫（或不認得）`form` 時退 `warhammer`；其他種類照舊。
- **A4 圓章**：`render/weaponIcon.ts` 的 `weaponItemIconCanvas(item, px, res = ICON_RES)`：`resolveGear` → Q 版 `def` → `render(def, px × meta.badge, res, { ow: outlinePx(px), badge: true })` → `blit()` 置中貼在 `round(px × res)` 的畫布上；拿掉 `measure()`、`iconAngle()`、`isDiagonal()`、墨線呼叫。`weaponIconItem()` 拿掉 `pairedPart()` 那一行（成對保留 `dual_*`）。快取鍵：`kind、form、material、keywords、element、rarity、px、frame、res`（需求 3.1 第 8 點，不含 `color`）。`ICON_RES = 2` 匯出成常數（D4）。
- **A5 裝備格（武器副手）**：`render/gearIcon.ts` 的 `gearIconCanvas(look, px, slot, res = ICON_RES)`：`frame()` 照舊畫在 64 格座標；`slotType` 是 `weapon`／`offhand` 時改畫 Q 版圖樣：`render(def, px × (1 − 2 × GEAR_PAD), res)`，以 `p = px × GEAR_PAD` 用 `blit()` 對齊整數裝置像素貼上（需求 3.1 第 1、2 點）；`> SMALL_ICON_MAX_PX` 時照現行 `motif()` 畫，位置用 `meta.spots` 換算到框內（`p + spot × (px − 2p) / 48`，再換回 64 格座標），大小照現行（第 0 節第 8 列）；寶石色照現行 `palette().accent`。防具飾品暫走 `D` 表（1b 換）。武器副手不再用 `D` 表與 `SCALE`。快取鍵加 `res`。
- **A6 內容**：`content/weapons.yaml` 的 `hammer` 補 `form: warhammer`；`UV_NO_SYNC=1 uv run python scripts/export_client_fixtures.py` 重產，`git diff --stat` 確認只有 `client/src/battle/fixtures/glossary.json` 變、且只有 `hammer` 那一筆的 `form`（不是就停下寫進報告）。
- **A7 武器開發頁**：`client/src/dev/weaponIconGallery.ts`（＋`client/dev/weaponicon-gallery.html`）：清單改成由 `gearAppearance.json` 的 `weapon`／`offhand` 種類 × 款式產生（61 款，不手寫）；參數 `?px=<CSS px>`、`&res=<1|2>`（預設 2；**1 ＝真 1 倍，畫布寬高＝CSS px**）、`&zoom=<k>`（canvas 以 `px × k` CSS 顯示、`image-rendering: pixelated`）、`&frame=badge|gear`（圓章底用 `.weapon-icon` 同樣的 CSS）、`&rarity=`、`&set=<all|rarity|material|element|closeup>`（對應第 8 節的截圖項）、`&label=0`。在檔頭註解寫參數說明。
- **A8 測試**：第 7 節 T1～T5、T7、T9；第 5 節列出的既有測試改寫。
- **A9 報告**與上手筆記（第 10 節）。

### QI-1b

- **B1 防具飾品畫法**：`client/src/render/qIcon/armor.ts`，由 `qIconsArmor.js` 逐行搬 18 種 37 款＋飾品 3 種 7 款、`palette(r)` 各欄位與固定色、`tone()`（照顏色判斷的四級換色、黑染例外、兜帽另亮一階、迴圈最多 4 次，需求 3.3 第 17～20 點）、`destination-out` 挖洞與 `halo()`（第 21 點）。共用 1a 的 `core.ts`，不另寫一份 `badgeScale`／`GEAR_PAD`。材質色用 `core.ts` 的樣張那一份（第 0 節第 3 列）。
- **B2 裝備格（防具飾品）**：`drawGear`／`gearIconCanvas` 的 `head`、`body`、`hands`、`feet`、`ring`、`neck` 改呼叫 Q 版（流程同 A5）；**拿掉 `D` 表、`SCALE`、只給 `D` 用的小工具**（`motif()`、`frame()`、`palette()` 的 `accent` 仍要留）；不認得的種類照遊戲端退 `sword`、沒有 `kind` 照 `SLOT_DEFAULT_KIND`（需求 2.4 第 4 列）。
- **B3 顯示尺寸（D3）**：
  - `ui/GearIcon.tsx`：`size` 改收任何整數 CSS px（至少 32、40、42、48、64）；新增 `fit`（身上裝備格用）：量外層格子內容寬，取 `min(48, floor(內容寬 − 4))`，顯式設 `style.width/height`，尺寸變了就重畫（`ResizeObserver`，第 0 節第 2 列）。畫布寬高一律 `iconCanvasPx(size) = round(size × ICON_RES)`。
  - `ui/WeaponIcon.tsx` 同樣改用 `iconCanvasPx`（行為不變，20／24／28）。
  - `world/BagScreen.tsx`：背包格 `size={42}`；身上裝備格 `fit`。`world/RangeClassPick.tsx`：`size={40}`。
  - 刪掉 `styles/world-economy.css` 的 `.world-bag-cell .gear-icon`、`.world-worn-box .gear-icon` 的寬高覆寫與 `styles/range-ob.css` 的 `.ob-kit-row canvas.gear-icon`（空格的灰階 `filter` 保留）。
- **B4 裝備開發頁**：`client/src/dev/gearGallery.ts`（＋`client/dev/gear-gallery.html`）：加 `?px=`、`&res=`、`&zoom=`、`&set=<armor|acc|dye|material|element|closeup|sizes|all>`，清單由 `gearAppearance.json` 產生；`set=dye` 照需求第 5 節第 5 項（黑、紅、藍、褐 × 長袍、斗篷帽、露指手套、長靴；布、皮各一款 8 色）；`set=doll` 盡量做「人物拿著同一件與圖示並排」（第 13 項；做不到就在報告寫明）。
- **B5 排版煙霧檢查**：`client/src/dev/layoutSmoke.ts` 加 `iconScaleIssues(doc, win)`：頁面上每個 `canvas.gear-icon`、`canvas.weapon-icon`，`getBoundingClientRect()` 的寬高是整數 CSS px，且 `canvas.width === round(寬 × ICON_RES)`、高同；判定抽成純函式加 vitest；掛到 `window.__layoutSmoke.icons()`，並併進 `runScreens`／`runTown` 的結果表（擇實際能看到背包的那一個）。
- **B6 測試**：第 7 節 T2（防具飾品）、T6、T8、T9；`gearIcon.test.ts` 裡描述 `D` 表的斷言改寫成 Q 版的對應斷言。
- **B7 報告**與上手筆記（第 10 節）。

## 7. 行為一致測試（vitest，用實際內容資料，不手寫清單）

資料來源：`client/src/battle/fixtures/glossary.json`（由 `content/` 匯出，含全部武器的 `weapon_class` 與有外觀的 `weapon_looks`）、`client/src/render/gearAppearance.json`（由 `content/equipment/appearance.yaml` 匯出）。

| # | 段 | 測什麼 |
|---|---|---|
| T1 | 1a | glossary 的**每一把武器**（含沒有 `look` 的 10 把）：`weaponIconItem(id, weapon_class)` → `resolveGear` 的 `kind`／`form`／`material` 等於 `weapon_looks` 的 `look`（沒有 `look` 的照 `WEAPON_CLASS_KIND`；`form` 缺的照 `resolveGear` 規則），**成對武器保留 `dual_*`**；同一件丟給 Q 版 `def()` 取到的是該 `kind`／`form` 自己的圖樣（不是退回別款）。 |
| T2 | 1a／1b | `gearAppearance.json` 每個 `slotType` 為 `weapon`／`offhand`（1a）與 `head`／`body`／`hands`／`feet`／`ring`／`neck`（1b）的 `kind × form` 都有 Q 版圖樣、名稱 `zh` 與 JSON 的 `zh` 一致；總數從 JSON 算出後再和需求 1.1 的 61、44 比（數字寫在斷言旁並註明出處）。 |
| T3 | 1a | 錘：glossary 的 `hammer` 外觀 `form === "warhammer"`；`resolveGear({kind:"hammer"})` 與 `{kind:"hammer", form:"???"}` 都是 `warhammer`；其他每個種類沒寫 `form` 時仍退 JSON 的第一款（逐種類跑）；`dollItem({kind:"hammer"}, "main_hand")` 也是 `warhammer`（第 0 節第 6 列）。 |
| T4 | 1a | 成對：JSON 裡 `paired: true` 的每個種類，圖示路徑收到的是成對種類（不換單把），`dollGear` 仍把主手、副手各畫一把（`pairedPart` 不變）。 |
| T5 | 1a | 快取鍵：圓章與裝備格的鍵含 `res`；同一件 `res` 1 與 2 不同鍵；與輸入屬性順序無關；不含 `color`（D2）。 |
| T6 | 1b | 畫布尺寸：`iconCanvasPx(css)` 對 20、24、28、32、40、42、48、64 都等於 `css × ICON_RES`；身上裝備格的尺寸函式對內容寬 42～52（含小數）回傳整數且 ≤ 48；原始碼掃描（`test/sourceScan.ts` 的 `readSources`）：`client/src/styles/` 沒有任何規則再設定 `.gear-icon`／`.weapon-icon` 的 `width`／`height`；`iconScaleIssues` 的純函式判定（整數、相等通過；縮放、小數不通過）。 |
| T7 | 1a | 貼圖對齊：`blit` 的左上角乘 `res` 是整數，覆蓋需求列的例子（圓章 20px、`meta.badge` 0.966 → `a` 19.32；裝備格 32／42／48／64 的 `p`、`a`）與 `res` 1、2。 |
| T8 | 1b | 換色 `tone()`：用 `gearAppearance.json` 的 `dyes` 與遊戲端染色表跑，黑、紅、藍、紫、褐、綠、白、金的結果等於需求 3.3 第 17 點列出的值（紅 `#db4545`、藍 `#4571db`、紫 `#8551c0`、黑主色 `#474a51`；L ≥ 105 的不換）；黑染 `meta.tone === "black"`。 |
| T9 | 1a／1b | 確定性與不丟例外：每款 × 材質（含不認得）× 關鍵字（無、1、2、不認得）× 稀有度 × 尺寸（≤24、>36）用假畫布畫兩次，呼叫紀錄相同、不丟例外（沿用 `gearIcon.test.ts` 的假畫布寫法）。 |

另外（瀏覽器，寫進報告）：需求 2.2 第 4 點的對照——同一組 `look`、同一尺寸與 `res`，遊戲端開發頁的圓章圖樣與樣張 `docs/art/sample/q-icons-weapons.html` 逐像素比對（用靜態伺服器開樣張頁，兩邊各取 canvas 的 `getImageData` 算不同的像素數與最大差值）；裝備格允許「只差 `blit` 對齊的位移」。每段至少比 10 款（含成對、鞭、弓、拳刃各一；1b 含黑染、兜帽、素戒挖洞各一）。

## 8. 驗收條件

### 8.1 共通（兩段都要）

1. 第 7 節本段的測試全過；改寫的既有測試在報告逐條說明「舊斷言 → 新斷言」。
2. `corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、`corepack pnpm -C client build` 三個結束碼都是 0（分開記）。1a 另跑 `UV_NO_SYNC=1 uv run trpg content check`、`uv run pytest -q tests/api/test_client_fixtures.py tests/api/test_glossary_names.py tests/api/test_gear_api.py tests/content/test_item_gen.py tests/content/test_equipment_content.py`、`ruff check`、`ruff format --check`（只動到 YAML 時也跑）。
3. `render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts`、`render/dollGear.test.ts` 通過且快照沒有變；有變要逐項說明原因（D1 以外的變動都要停下回報）。
4. `window.__layoutSmoke`：`corepack pnpm -C client build` 後啟動自己的 `trpg serve`，在 1600×900、1040×624、800×600 三個情況各 `localStorage.clear()` → 開 `/?dev=1&anim=0.1&mute=1` → `await window.__layoutSmoke.runCase("標題")`，全 PASS；1b 另跑 `icons()`（三個尺寸都要打開背包與身上裝備格）全 PASS。
5. 浮動卡實測（6.5.1）：1600×900 與 800×600，從裝備圖示（背包格的 `<Hint>`、身上裝備格的 `PartTip`、英雄面板裝備列）滑進卡片 → 卡內捲到底 → 釘住 → 關閉，結果寫進報告。
6. 截圖存 `docs/art/shots/qi1/`，檔名前綴 `1a-`、`1b-`；jpg 品質 80、單張 ≤ 300 KB；用裝置像素比 1 拍；6 倍放大用最近鄰（`image-rendering: pixelated`）。實機到不了的用開發頁畫並在報告「實機未看」逐項列出。報告寫完整路徑。
7. 需求第 5 節最後兩點寫進報告：(a) 第 7 節末段的對照方式與結果；(b) `D` 表（1b）與墨線小圖示舊程式（第 0 節第 9 列）是否已拿掉、哪裡還在用。

### 8.2 截圖分配（對到需求第 5 節 13 項）

「真 1 倍」＝開發頁 `res=1`；「DPR 2」＝`res=2`；最小尺寸兩種都 6 倍放大。多項合一張以壓張數；目標每段 ≤ 10 張，最多 16 張（第 0 節第 4 列）。

| 需求項 | 段 | 內容 | 張數估計 |
|---|---|---|---|
| 1 圓章 61 款 | 1a | 20 真 1 倍×6；20 DPR 2×6；24、28 DPR 2 原大 | 3～4 |
| 2 裝備格 61 款 | 1a | 32 真 1 倍×6；32 DPR 2×6；48、64 DPR 2 原大 | 3～6 |
| 3 稀有度 | 1a | 直劍、鳶盾 × 5 級：32 真 1 倍×6、64 DPR 2 | 1 |
| 8 特寫（武器部分） | 1a | 鞭三款、雙左輪、雙彎匕、弓三款、拳刃圓章 20；拳刃、蛇骨鞭裝備格 32；真 1 倍＋DPR 2 | 1～2 |
| 9 錘 | 1a | 實機：英雄面板圓章、裝備格、地圖上的人物（三處方頭）合一張 | 1 |
| 10 成對 | 1a | 雙匕首、雙手槍圓章與裝備格；`RangeClassPick` 的 40（第 0 節第 7 列） | 1 |
| 4 防具飾品 44 款 | 1b | 32 真 1 倍×6；32 DPR 2×6；42、48、64 DPR 2 原大 | 3～5 |
| 5 染色 | 1b | 黑紅藍褐 × 4 款；布、皮各一款 8 色；32 真 1 倍＋DPR 2 | 1～2 |
| 6 材質 | 1b | 每種武器、防具至少一款的全部可用材質（含鏈鞭銀、骨暗節），32 DPR 2 | 1～2 |
| 7 元素 | 1b | 4 元素混色（金屬、晶石、杖頭、法器珠）＋ >36px 小圖樣位置＋一個非元素關鍵字；32、48、64 DPR 2 | 1 |
| 8 特寫（防具部分） | 1b | 黑長袍／黑布兜帽／黑素手套 32、護膝脛甲、印戒、披風外套 32 | 1 |
| 11 實機 12 處 | 1b | 英雄面板 24＋32、開局選武器 20、靶場武器架 20、背包 42（含空格灰色預設）、裝備卡 64／32、裝備欄格 64、物品列表 48、單位資訊 32、獲得物品 32、信件 32、靶場套組 40、身上裝備格（1600 與 800 寬各一） | 3～4（裁切合圖） |
| 12 CSS 縮放三處 | 1b | 42、40、身上裝備格在 100% 縮放的 6 倍放大，外框硬邊、不比 32 真 1 倍糊 | 1 |
| 13 和人物並排 | 1b | 開發頁做得到才交（第 0 節第 3 列的色差照實） | 0～1 |

## 9. 開發中跑的測試

- 前端：`corepack pnpm -C client exec vitest run src/render/gearIcon.test.ts src/render/weaponIcon.test.ts src/render/weaponLooks.test.ts src/render/arcaneBlade.test.ts src/render/dollGear.test.ts src/render/appearanceFallback.test.ts src/gear/gearPreview.test.ts src/ui/entryScreen.test.ts <新測試檔>`；1b 加 `src/dev/layoutSmoke.test.ts`、`src/ui/floatCardRule.test.ts`。
- 每次 commit 前 `corepack pnpm -C client typecheck`；交件前跑第 8.1 節第 2、3 點。
- 每完成一個交付項目就 commit；commit 第一行英文（例 `feat(qi1a): port Q weapon icon core`），結尾帶 Co-Authored-By。

## 10. 報告格式

各段寫 `docs/phases/PhaseQI-1報告.md`（1a 建立，1b 在同檔加「QI-1b」一節）：

1. 做了什麼（交付項目逐條，附 commit）。
2. 驗收逐條（測試名稱或指令輸出為證；三個結束碼分開記）。
3. 改寫的既有測試（舊斷言 → 新斷言）與快照變動說明。
4. 需求第 5 節 (a)(b) 兩點；截圖清單（完整路徑、對到第 8.2 節哪一項、真 1 倍或 DPR 2）；「實機未看」清單。
5. 浮動卡實測、`__layoutSmoke` 結果表。
6. 新增的複雜度 noqa（C901、PLR0911／0912／0915；只有改到 Python 時）逐一列理由；前端沒有 lint，逐行搬的長函式不拆（和樣張對照用），在報告列出超過 80 行的函式。
7. 請使用者重開伺服器檢查的重點（1a：內容檔有改，進行中的一輪會從頭開始；看英雄面板的錘、雙匕首圓章）。
8. **待 PM 決定**：最多 10 點，每點附出處；原型數值與解讀類照最保守做完再列。
9. 順手更新上手筆記：`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節加 `render/qIcon/`、`weaponIcon.ts`、`gearIcon.ts`、`ui/GearIcon.tsx` 的職責；開發入口表加兩個開發頁的參數；第四節加「CSS 不要縮放圖示畫布」「材質色兩份」兩個坑）；1a 另更新 `docs/dev/上手-內容資料與模擬.md`（改武器 `look` 要重產 `glossary.json`）。
