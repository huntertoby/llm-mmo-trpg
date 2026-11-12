# Phase QI-1b 報告：Q 版小圖示｜防具飾品、拿掉 `D` 表、顯示尺寸（D3）與實機截圖

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-1計畫.md`（QI-1b 部分；第 0.0 節已定）。依據本機 main `41a88bbd`（worktree 先 `git merge --ff-only main`）。未 push。
> 另含：美術 PM 對 1a 的追加（寶石色）與開發 PM 轉來的 `docs/art/QI-1檢查.md`（美術分支 `72698890`）三點。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| B1 防具飾品畫法 | 新 `client/src/render/qIcon/armor.ts`：由 `docs/art/sample/qIconsArmor.js` 逐行搬 18 種 37 款＋飾品 3 種 7 款的畫法、`palette`（`qArmorPalette`：`a/d/l/t/dd/accent/tone/lifted`）、`tone()`（ok／black／vivid／dull 四級、黑染例外、兜帽另亮一階、迴圈最多 4 次）、`destination-out` 挖洞（素戒、臂環、鎖鏈護手指縫）與 `halo()`（護膝甲片、披風外套、吊牌）。共用 1a 的 `core.ts`（`render`、`halo`、`GEAR_PAD`…）。不搬樣張的 `resolve()`（一律吃 `resolveGear`）、`motif`／`paint`／`canvas`／`list`。材質色用 `material.ts`、混色用 `color.ts`、染色表用 `artPalette.GEAR_DYE` | `e31345f5` |
| 寶石色（美術 PM 追加） | `core.gemAccent(keywords, material)`：照 `KEYWORD_COLOR` 的宣告順序（元素四個在前）挑——有元素關鍵字用元素色、沒有才用其他關鍵字的色、都沒有晶石 `#b8a8ff`／其他 `#e04060`；**不受關鍵字順序影響**。武器副手 `qPalette` 與防具飾品 `qArmorPalette` 共用 | `e31345f5` |
| B2 裝備格 | `gearIcon.ts`：`drawGear` 一律 `frame()` → Q 版圖樣（`gearQDef`：武器副手 → 防具飾品 → 退直劍）→ `blit` 對齊 → >36px 疊 `motif()`（位置用 `meta.spots` 換算）。**`D` 表、`SCALE`、`palette()`、`shape/line/diag/grip/guard/shine/gem/torso/glove/boot/gunFrame/flintHammer/pair` 等只給 `D` 用的小工具全部拿掉**（823 行 → 約 190 行）；`motif()`、`frame()` 留著 | `e31345f5`、`af86ff9a` |
| B3 顯示尺寸（D3） | `ui/GearIcon.tsx`：`size` 收任何整數 CSS px；新增 `fit`（量外層格子內容寬 → `fitIconPx` ＝ `min(48, floor(內容寬 − 4))`，`ResizeObserver` 尺寸變了就重畫）；畫布寬高一律 `iconCanvasPx(px)`。`ui/WeaponIcon.tsx` 改用 `iconCanvasPx`（行為不變）。`world/BagScreen.tsx`：背包格 `size={42}`、身上裝備格兩處 `fit`。`world/RangeClassPick.tsx`：`size={40}`。刪掉 `styles/world-economy.css` 的 `.world-bag-cell .gear-icon`、`.world-worn-box .gear-icon` 寬高覆寫與 `styles/range-ob.css` 的 `.ob-kit-row canvas.gear-icon`（空格的灰階 `filter` 保留） | `de71b40b` |
| B5 排版煙霧檢查 | `dev/layoutSmoke.ts`：純函式 `iconScaleProblem(box)`、`iconScaleRows`，量測 `collectIconBoxes(doc)`，`iconScaleIssues(doc, win)`；掛 `window.__layoutSmoke.icons(stage?)`，併進 `runTown` 的結果表（`dev/townSmoke.ts` 的 `runTownWith` 多一個 `extra` 參數） | `de71b40b` |
| B6 測試 | 新 `client/src/render/qIcon/qIconArmor.test.ts`（T2 防具飾品、T6、T8、T9、寶石色表格與順序無關、錘柄色） | `de71b40b`、`ffae80c0` |
| 規則 6（美術定，`QI-1檢查.md`） | 戰錘、釘頭錘的錘柄木色**只在圖示**改亮一階 `#6a4420` → `#a06a36`（`weapons.ts` 的 `HAMMER_SHAFT`；`core.hammerArt`、`haft` 多一個柄色參數，預設不變）；人物、連枷、斧不動 | `ffae80c0` |
| B4 裝備開發頁 | `client/src/dev/gearGallery.ts`＋`client/dev/gear-gallery.html` 重寫：清單由 `gearAppearance.json` 產生；`?px` `&res` `&zoom` `&rarity` `&set=armor|acc|all|dye|material|element|closeup|sizes|audit|doll`（可用逗號接多段）`&from&n` `&label=0`，檔頭有說明；`window.__qiDev`（`gear`、`art`、`list`） | `0d67a3c9`、`ffae80c0` |
| 截圖 | `docs/art/shots/qi1/` 10 張（第 4 節） | `28681db4` |
| B7 | 本報告、上手筆記 | 本 commit |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 8.1-1 | 第 7 節本段測試 | 過。`src/render/qIcon/qIconArmor.test.ts` 17 項：T2「kind × form 都有圖樣…總數 44」「沒有 kind 時照欄位預設造型」；T6 五項（`iconCanvasPx` 對 20～64、`fitIconPx` 內容寬 42～52 每 0.25、`styles/` 掃描沒有 `.gear-icon`／`.weapon-icon` 的 width／height、元件原始碼 42／40／`fit`、`iconScaleProblem` 通過與不通過）；T8 四項；寶石色兩項（表格、12 個關鍵字每一對兩種順序相同，武器副手與防具飾品都比）；T9 兩項＋錘柄一項。1a 的 `qIconWeapons.test.ts` 照舊全過 |
| 8.1-2 | 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（288 檔、3563 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告）。沒有動 Python／內容，未跑後端檢查 |
| 8.1-3 | 快照 | `inkDollSnapshot`、`creaturePose`、`dollGear` 在整包測試裡通過，`git status` 乾淨（快照沒變） |
| 8.1-4 | `__layoutSmoke` | 自己的 build＋`trpg serve --port 8129`（存檔在暫存區）：`runCase` 1600×900、1040×624、800×600 **全 PASS**；`icons()` 三個尺寸都打開背包與身上裝備格 **全 PASS**（第 5 節） |
| 8.1-5 | 浮動卡實測 | 過（第 5 節）：背包格 `<Hint>`、身上裝備格 `PartTip`、英雄面板裝備列 `PartTip`，1600×900 與 800×600 |
| 8.1-6 | 截圖 | 10 張、單張 ≤ 228 KB；真 1 倍／最近鄰特寫用 PNG，其餘 jpg 80；DPR 1 拍（第 4 節） |
| 8.1-7 | (a)(b) | 第 4 節 |

## 3. 改寫的既有測試、快照

- 既有測試沒有改斷言：1a 已把 `gearIcon.test.ts` 裡描述武器 `D` 表的斷言改成 Q 版；剩下的（全組合不丟例外、`resolveGear` 預設、快取鍵、稀有度框、關鍵字小圖樣一處／兩處、確定性）描述的是框、`resolveGear` 與 `motif()`，換掉 `D` 表後照樣成立，沒有放寬。防具飾品的 Q 版畫法另在 `qIconArmor.test.ts` 用假畫布測（`gearIcon.test.ts` 的「全組合」那兩個 describe 沒掛假畫布，防具飾品在那裡只畫框，和 1a 時的武器一樣）。
- 快照：無變動。

## 4. 需求第 5 節 (a)(b)、截圖、實機未看

**(a) 和樣張逐像素對照**：裝備開發頁（vite 5265）用 `<script>` 載入靜態伺服器（8129）上的 `qIcons.js`、`qIconsWeapons.js`、`qIconsArmor.js`，同一頁兩邊畫同一組 `look` 的圖樣（不含框：我方 `__qiDev.art`＝`render(gearQDef(...), a, res)`，樣張 `QIcons.render(QIconsArmor.def(look), a, res, {})`），`getImageData` 比。樣張的 `MAT` 與 `QIcons.M` 的鐵、鋼、銅先換成 `material.ts` 的色。
- 範圍：44 款 × 每款全部可用材質、布皮款 × 8 色染料、44 款 × 3 組關鍵字（`ignite`／`frozen+marked`／`marked`，史詩）× 5 種尺寸（32 res 1、32／42／48／64 res 2）＝ **2345 組，2315 組 0 像素不同**。
- 不同的 30 組都可解釋：(1) 20 組＝關鍵字只有 `marked`（非元素）的寶石戒、項鍊墜、頭冠、臂環——寶石換成 `marked` 的色（需求 3.4 第 22 點「其餘 8 個請照現行補」＋美術 PM 追加；樣張只認 4 個元素關鍵字，退預設紅）；(2) 10 組＝紅染、藍染的寬簷帽，最多差 1 色階——帽冠色 `mix(a, d, 0.5)` 剛好落在 .5，共用 `color.ts` 的 `mix` 和樣張的四捨五入算式不同（1a 待決 3 同一件事）。
- 黑染自查值 73.9～173.2（樣張自查 74～173），一致。裝備格貼法和 1a 一樣用 `blit`（和樣張的縮放貼法只差對齊位移），這次只比圖樣本身。

**(b) 舊程式**：`gearIcon.ts` 的 `D` 表、`SCALE`、`palette()` 與只給它們用的小工具**已全部拿掉**，全專案沒有其他引用（`typecheck`、整包測試通過）。墨線小圖示（`inkStyle.withIconMode`／`iconHead`、`inkGear` 等的 `inIconMode` 分支、`shortWeaponIcon.test.ts`）照第 0.0 節第 9 點沒刪，現況同 1a 報告。`artPalette.GEAR_INK`、`GEAR_MATERIAL` 仍被其他檔使用，沒動。

**規則 6 亮度**（深底裝備格 32px，圖樣平均亮度 ≥100、亮度 ≥150 的亮面 ≥5%；開發頁 `?set=audit`）：

- 防具飾品：預設材質 44 款、全部可用材質、布皮 × 8 色染料**全部達標**；黑染（`tone=black`）照需求 3.3 第 18 點另列不套門檻（73.9～173.2）。**沒有不達標的款。**
- 武器（錘柄改亮一階前後，`weaponicon-gallery.html?set=audit`）：

| 款・材質 | 改前（1a 報告） | 改後 | 結論 |
|---|---|---|---|
| 戰錘・鐵 | 98.6／6.3% | **107.6**／6.1% | 過 |
| 釘頭錘・鐵 | 99.97／7.2% | **106.6**／7.9% | 過 |
| 戰錘・銅 | 95.6／6.1% | **104.6**／5.6% | 過（不用列例外） |
| 釘頭錘・銅 | 96.9／7.2% | **103.5**／7.9% | 過（不用列例外） |
| 手斧・銅 | 99.9／10.0% | 99.6／9.9% | 規則 6 例外（美術定，不改） |
| 獵槍・銅 | 99.97／7.8% | 100.0（顯示）／8.4% | 例外（美術定，不改；未四捨五入時 < 100） |
| 拳刃・皮 | 89.5／7.7% | 89.4／8.0% | 例外（美術定，不改） |
| 鐵拳・皮 | 95.1／6.1% | 95.1／6.1% | 例外（美術定，不改） |

  連枷沒改（鐵 103.5、銅 100.9，本來就過）。改後預設材質 61 款 0 款不過，全部材質剩上表 4 組例外。手斧、獵槍、拳刃的小數差異是量測雜訊（上手筆記第四節第 22 點）。

**截圖**（`docs/art/shots/qi1/`；無頭 Chrome、`--force-device-scale-factor=1`、`--mute-audio`、網址 `?mute=1`）

| 檔 | 格式 | 對到 8.2 | 內容 |
|---|---|---|---|
| `docs/art/shots/qi1/1b-1-armor44-gear32-true1x-x6.png` | PNG | 第 4 項 | 防具＋飾品 44 款，裝備格 32 真 1 倍 ×6 |
| `docs/art/shots/qi1/1b-2-armor44-gear32-dpr2-x6.png` | PNG | 第 4 項 | 同上 DPR 2 ×6 |
| `docs/art/shots/qi1/1b-3-sizes-gear42-48-64-dpr2.jpg` | jpg | 第 4 項 | 44 款的 42、48、64，DPR 2 原大 |
| `docs/art/shots/qi1/1b-4-dye-true1x-dpr2-x4.png` | PNG | 第 5 項 | 黑紅藍褐 × 長袍、斗篷帽、露指手套、長靴；長袍（布）、皮背心（皮）未染＋8 色；32 真 1 倍與 DPR 2，**×4**（×6 超過 300 KB） |
| `docs/art/shots/qi1/1b-5-material-gear32-dpr2.jpg` | jpg | 第 6 項（防具部分） | 每種防具飾品第一款 × 全部可用材質＋頭冠、臂環，32 DPR 2（武器部分在 1a 的開發頁 `?set=material`，見待決 4） |
| `docs/art/shots/qi1/1b-6-closeup-true1x-dpr2-x6.png` | PNG | 第 8 項（防具部分） | 黑長袍、黑布兜帽、黑素手套、護膝脛甲、印戒、披風外套 32，真 1 倍與 DPR 2 ×6 |
| `docs/art/shots/qi1/1b-7-doll-side-by-side.jpg` | jpg | 第 13 項 | 遊戲端 Q 版人物（`drawQLookPreview`、`GAME_HOOKS`）穿同一件 × 48px 圖示，44 款（戒指人物不畫） |
| `docs/art/shots/qi1/1b-8-element-gear32-48-64-dpr2.jpg` | jpg | 第 7 項 | 4 元素 × 板甲、鐵盔、晶石戒、長袍、直劍、晶石匕首、長杖、水晶球；非元素關鍵字（寶石戒 marked、項鍊墜 summon、頭冠 `prone+ignite` 與 `ignite+prone`＝同寶石色、典籍、鎖甲兩個關鍵字）；32、48、64 DPR 2 |
| `docs/art/shots/qi1/1b-9-live-places.jpg` | jpg | 第 11 項 | 實機合圖：背包 42（含空格）＋身上裝備格 48（1600 寬）＋詳情 64／32、身上裝備格 39＋背包 42（800 寬）、英雄面板 24＋32 裝備列、戰後裝備卡 64／目前 32、靶場套組 40、靶場武器架 20、裝備測試物品列表 48、手動組裝 64、起始武器 20 |
| `docs/art/shots/qi1/1b-10-css-spots-x6.png` | PNG | 第 12 項＋1a 缺圖 | 實機 DPR 1 截圖 ×6 最近鄰：背包格 42、身上裝備格 48（1600）與 39（800）、靶場套組 40；開發頁：成對 40（雙匕首、雙手槍）、對照 32 真 1 倍 |

**1a 缺圖（`QI-1檢查.md` 第 3 點）**：英雄面板 32 裝備列與裝備格 32 實機在 `1b-9`（英雄面板、戰後「目前裝備」32）；`RangeClassPick` 成對 40 在 `1b-10`（開發頁，靶場起始武器沒有成對的）。

**實機未看**：`RangeClassPick` 的成對 40（開發頁代替）；單位資訊 `UnitInfo` 32、獲得物品 `GainEffects` 32、信件 `MailPanel` 32（沒有走到；同一個 `GearIcon` 32，`1b-1`、`1b-2` 的 32 開發頁代替）；工坊裝備欄格 `SlotGrid` 64 有裝備的樣子（點「穿上」沒成功，畫面只有空格；同 `GearIcon` 64，`1b-3`、手動組裝 64 代替）；開局畫面的 `StartPicker`（用裝備測試頁的起始武器那一列，同一個元件 20px；開局畫面 `icons()` 另量過 22 個 20px 全 PASS）。

## 5. 浮動卡實測、`__layoutSmoke`

**浮動卡**（自己的 build＋`trpg serve`，暫存區的測試角色；背包裡的防具飾品是改暫存存檔塞進去的，不是使用者存檔）：

| 觸發元素 | 1600×900 | 800×600 |
|---|---|---|
| 背包格 `<Hint>`（黑長袍） | 滑過開 → 一步步滑進卡片仍開 → 卡內滾輪（內容高 28＝可視 28）仍開 → 點一下 `pinned` → 滑走仍開 → Esc 關 | 同左 |
| 身上裝備格（頭）`PartTip` | 同上（內容高 60＝可視 60） | 同左 |
| 英雄面板裝備列（戒指）`PartTip` | 同上（內容高 60＝可視 60） | 同左 |

三張卡內容都不夠高，「捲到底」只驗到滾輪不會關卡（同 1a）。

**`window.__layoutSmoke`**

| 檢查 | 1600×900 | 1040×624 | 800×600 |
|---|---|---|---|
| `runCase` | 全 PASS（12 項） | 全 PASS | 全 PASS |
| `icons()`：背包＋身上裝備格＋詳情 | PASS（15 個；32、42、48、64） | PASS（15 個；32、42、48、64） | PASS（15 個；32、**39**、42、64） |

另外量過（1600×900）：戰後裝備三選一 PASS（24、32、64）、一輪英雄面板 PASS（24、32；800×600 也 PASS）、靶場套組 PASS（40）、靶場武器架 PASS（20、40）、裝備測試 PASS（20、48／20、64）、開局 PASS（20）。

## 6. 複雜度 noqa、長函式

沒有改 Python。前端逐行搬的函式沒有超過 80 行的（`armor.ts` 最長是 `capeCoatArt` 約 25 行）；`dev/gearGallery.ts` 的 `show()` 約 60 行。

## 7. 請使用者重開伺服器檢查的重點

- 沒有改內容資料，存檔與進行中的一輪不受影響；前端要重新 build（或重開開發伺服器）。
- 看：大世界背包（42 格）與身上裝備格（窄視窗時 39～48 跟著格子變）、靶場套組的入門武器（40）——外框應該是硬邊、不比 32 糊；英雄面板的錘圖示錘柄變亮一階。

## 8. 待 PM 決定

1. **需求與規格的黑染主色末位**：需求 3.3 第 17 點、規格 T8 寫 `#474a51`；`#33363d` 混 10% 白的藍版是 61 ＋ 194 × 0.1 ＝ 80.4 → `0x50`，樣張的 `mix` 與 `color.ts` 都得 **`#474a50`**。測試照實際值鎖、註明出處；請美術 PM 確認是筆誤（出處：`qIconArmor.test.ts` T8）。
2. **寶石色「第一個關鍵字」的解讀**：要「不受關鍵字順序影響」，我把「第一個」讀成照 `KEYWORD_COLOR` 的固定順序（元素四個在前，其餘照宣告順序）。兩個元素關鍵字同時存在（例 `frozen＋wet`）時取固定順序的第一個（`wet`），**元素混色**仍照 1a／樣張用關鍵字順序的第一個元素（`frozen`），兩者可能不同色。內容資料目前沒有兩個元素關鍵字的裝備（出處：`core.gemAccent`）。
3. **錘柄改亮的範圍**：美術 PM 寫「戰錘・鐵、釘頭錘・鐵的錘柄」，我讀成戰錘、釘頭錘兩款**所有材質**都換（改完量銅也過，就不用列例外）；連枷沒換（出處：`weapons.ts` `HAMMER_SHAFT`）。只要鐵換的話要再改一行並重量銅。
4. **截圖分配**：第 6 項材質只交防具飾品部分；1a 的截圖清單裡沒有武器材質那張，武器材質目前只在開發頁 `weaponicon-gallery.html?set=material`。第 5 項染色用 ×4（×6 超過 300 KB）。10 張的上限下沒辦法再補，要的話請放寬或改下一段補。
5. **身上裝備格的小數位置**：`fit` 後圖示尺寸是整數（39／48），但格子置中後左上角落在小數位置（例 266.44, 269.47）。`icons()` 照規格只檢查寬高，`1b-10` 放大看沒有糊；要不要再要求位置也對齊整數請定。
6. **`icons()` 併進哪個表**：照規格併進 `runTown`；但 `runTown` 量的是實地 HUD，背包要另外打開才量得到，所以驗收實際是「打開背包後 `icons()`」。
7. **`gearIcon.test.ts` 的全組合 describe 沒掛假畫布**：防具飾品的 Q 版圖樣在那兩個 describe 沒真的畫（沒有 DOM 時 `render` 回 `null`）；Q 版的全組合改在 `qIconArmor.test.ts` T9 用假畫布跑。要不要把那兩個 describe 也掛上假畫布（會變慢）請定。
8. **報告檔名**：照派工寫 `PhaseQI-1b報告.md`（規格第 10 節是同一個 `PhaseQI-1報告.md` 加節；1a 已分檔）。

## 9. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：第一節表（`render/qIcon/` 加 `armor.ts`、`gemAccent`；`gearIcon.ts` 改寫「`D` 表已拿掉」；`ui/GearIcon.tsx` 的 `size`／`fit`）；第二節開發入口表加 `gear-gallery.html` 的參數、`__layoutSmoke` 段加 `icons()`；第四節第 19 點補「QI-1b 已處理」、加第 23～25 點（`fit` 的小數位置、黑染末位、錘柄色只在圖示）；第五節測試表加 `qIcon/qIconArmor.test.ts`。
