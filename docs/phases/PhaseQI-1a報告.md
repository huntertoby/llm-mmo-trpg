# Phase QI-1a 報告：Q 版小圖示｜共用核心＋武器副手

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-1計畫.md`（QI-1a 部分；第 0.0 節取代第 0 節）。依據 main `80064515`。未 push。
> 規格第 10 節寫「各段寫 `PhaseQI-1報告.md`」；本次派工指定檔名 `PhaseQI-1a報告.md`，照派工。

## 1. 做了什麼（交付項目）

| 項目 | 內容 | commit |
|---|---|---|
| A6 內容 | `content/weapons.yaml` 的 `hammer.look` 補 `form: warhammer`；重產 `client/src/battle/fixtures/glossary.json`。`git diff --stat` 只有這個檔，且只有 `hammer` 那筆 `"form": null → "warhammer"`（其他快照檔重寫後內容不變） | `1eb7c4bc` |
| A1 共用核心 | 新 `client/src/render/qIcon/core.ts`：由 `qIcons.js` 逐行搬 `OUT`、`M`、`EL`、`HI/HI2/SH`、`f/rr/ci/el/poly/ln/starPts/glow/flame/sparkle`、`dilate`、`halo`、`outlinePx`、`render`、`farOf`／`badgeScale`、`BADGE_R`、`GEAR_PAD`、`blit`（另抽出 `blitOrigin` 給測試）、八把樣本畫法（`diag`、`PW`、`swordArt`、`greatswordArt`、`arcaneArt`、弓三件 `bowGeo/bowArt/bowString`、`staffArt`、`hammerArt`、`fistArt`、`towerShield`）、`ICON_RES = 2`。建畫布集中在 `blank()`，`setQCanvasFactory` 可注入假畫布；沒有 DOM 時 `render` 回 `null`。材質色（`M` 的鋼、鐵、木、皮）取自 `material.ts`（第 0.0 節第 3 點）；混色用共用 `color.ts` 的 `mix` | `e1b2e9e7` |
| A2 武器副手 | 新 `client/src/render/qIcon/weapons.ts`：由 `qIconsWeapons.js` 逐行搬 17 種 53 款＋副手 4 種 8 款的畫法、`palette`（稀有度護手換色）、`crossed()`、鞭兩種構圖、弓／槍／拳刃等全部細節。**沒搬** `resolve()`、`NO_FORM`、`shock/freeze` 別名、`gearFrame`／`motif`／`paint`／`canvas`；改由 `qResolve(resolveGear(…), element)` 轉欄位。`MAT` 用 `material.ts`；寶石色 `accent` 照現行 `gearIcon.palette().accent`（第一個關鍵字的色，12 個都認） | `e1b2e9e7` |
| A3 D1 | `resolveGear`：`hammer` 沒寫或不認得 `form` 退 `warhammer`（`NO_FORM`）；其他種類照舊 | `e1b2e9e7` |
| A4 圓章 | `weaponIcon.ts` 全換：`weaponIconItem` 拿掉 `pairedPart`（成對保留 `dual_*`）；`weaponItemIconCanvas(item, px, res = ICON_RES)` → `render(def, px × meta.badge, res, { ow: outlinePx(px), badge: true })` → `blit` 置中到 `round(px × res)` 畫布；拿掉 `measure`、`iconAngle`、`isDiagonal`、墨線呼叫。快取鍵 `weaponIconKey`＝kind、form、material、keywords、element、rarity、px、`badge`、res（不含 color） | `e1b2e9e7` |
| A5 裝備格 | `gearIcon.ts`：`drawGear(ctx, look, small, slot, px = 64, res = ICON_RES)`；`slotType` 為 weapon／offhand 時 `frame()` 後畫 Q 版（`render(def, px × 0.88, res)`、`blit` 對齊）、>36px 照 `motif()` 疊在 `meta.spots` 換算的位置（大小照現行）；防具飾品仍走 `D` 表。`gearIconCanvas(look, px, slot, res)` 畫布 `round(px × res)`；`gearIconKey` 加 `element` 與 `res` | `e1b2e9e7` |
| A7 開發頁 | `client/src/dev/weaponIconGallery.ts`＋`client/dev/weaponicon-gallery.html`：清單由 `gearAppearance.json` 產生（61 款）；`?px` `&res` `&zoom` `&frame` `&rarity` `&set=all|sizes|rarity|material|element|closeup|audit` `&from&n` `&label=0`，檔頭有說明；`window.__qiDev` 供像素比對 | `14702469`、`3246ab35` |
| A8 測試 | 新 `client/src/render/qIcon/qIconWeapons.test.ts`（T1～T5、T7、T9）、`client/src/test/fakeCanvas.ts`；改寫既有測試（第 3 節） | `e1b2e9e7` |
| 截圖 | `docs/art/shots/qi1/` 10 張（第 4 節） | `ff95fb57`、`f2d7138a` |
| A9 | 本報告、上手筆記 | 本 commit |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 8.1-1 | 第 7 節本段測試全過 | 過：`src/render/qIcon/qIconWeapons.test.ts` 19 項（T1「glossary 的每一把武器…」、T2「kind × form 都有圖樣…總數 61」、T3「錘一律方頭」、T4「成對武器」、T5 三項、T7 十一項、T9「每款 × 材質…畫兩次呼叫紀錄相同」）。改寫的舊斷言見第 3 節 |
| 8.1-2 | typecheck／test／build 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（287 檔、3533 項全過）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告） |
| 8.1-2 | 後端 | `UV_NO_SYNC=1 uv run trpg content check` 通過（658 檔、402 技能）；`uv run pytest -q -n 8 tests/api/test_client_fixtures.py tests/api/test_glossary_names.py tests/api/test_gear_api.py tests/content/test_item_gen.py tests/content/test_equipment_content.py` **230 passed**；`ruff check` All checks passed；`ruff format --check` 2336 files already formatted；`mypy` no issues（1440 檔）；`lint-imports` 14 kept, 0 broken |
| 8.1-3 | 快照 | `render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts`、`render/dollGear.test.ts` 通過、快照**沒有變**（含 D1：預設快照裡沒有沒寫 form 的錘） |
| 8.1-4 | `__layoutSmoke.runCase` | 自己的 build＋`trpg serve --port 8127`（存檔放暫存區），每個尺寸 `localStorage.clear()` 後開 `/?dev=1&anim=0.1&mute=1`：1600×900、1040×624、800×600 **全 PASS**（第 5 節） |
| 8.1-5 | 浮動卡實測 | 過（第 5 節）；英雄面板裝備列沒實測（該 run 沒有裝備），列「實機未看」 |
| 8.1-6 | 截圖 | 10 張，jpg 80 或 PNG（真 1 倍／最近鄰特寫，照開發 PM 11-12 更新），單張都 ≤ 300 KB，DPR 1 拍（第 4 節） |
| 8.1-7 | (a)(b) | 第 4 節 |

## 3. 改寫的既有測試、快照變動

| 檔 | 舊斷言 | 新斷言（理由：舊的描述被換掉的墨線畫法） |
|---|---|---|
| `render/weaponIcon.test.ts` | `iconAngle()`／`isDiagonal()` 的角度（長條 ±45°、手槍與拳套 0） | Q 版 `meta.diag`：長條（劍斧錘杖弓鐮鞭矛匕首巨劍）與長槍、霰彈槍、弩斜放；手槍、鐵拳、爪、盾、書、珠不斜放、拳刃斜放；小圖樣位置組（diag／gun／block） |
| `render/arcaneBlade.test.ts` 84–87 行 | `isDiagonal("sword")` | `weaponIconDef(魔導劍).meta` 是 `{ diag: true, r: { kind: "sword", form: "arcane" } }` |
| `render/weaponLooks.test.ts` 141–143 行 | `isDiagonal("scythe"/"whip") === true`、`isDiagonal("fist") === false` | 同樣三個斷言改看實際武器 ID 的 Q 版 `meta.diag` |
| `render/weaponLooks.test.ts` 174–177 行 | 成對武器的小圖示「換成單把」：`kind: "dagger"`／`"pistol"`、雙匕首斜放 | 成對**保留** `dual_dagger`／`dual_pistol`（需求 3.2 第 10 點），Q 版 `def` 取到成對那一款 |
| `render/gearIcon.test.ts`「成對武器畫兩把」 | 數 `save` 呼叫（D 表 `pair()`） | 用假畫布數刃的多邊形（`lineWidth=0.800`）：成對 ≥ 單把 × 2 |
| `render/gearIcon.test.ts`「快取鍵包含是否小圖」 | 是否小圖在 `at(-2)` | 鍵尾多了 `res`，改 `at(-3)`（值不變） |
| `render/gearIcon.test.ts`「確定性」 | `draw(l)` 等於 `draw(l)` | 先畫一次暖快取（第一次多一段量圓章縮放的呼叫），再比後兩次 |
| `render/gearIcon.test.ts` 兩個 describe | — | 加 `useFakeQCanvas()`：武器、副手的圖樣畫在另建畫布上，`draw()` 回傳外層＋圖樣畫布的呼叫（「小圖仍保留元素混色」等才量得到） |

快照：無變動（D1 也沒有造成快照變動）。`glossary.json` 是內容快照，變動只有 `hammer.look.form`（D1／A6 造成）。

## 4. 需求第 5 節 (a)(b)、截圖、實機未看

**(a) 和樣張逐像素對照**（需求 2.2 第 4 點）：武器開發頁（vite 5260）裡用 `<script>` 載入靜態伺服器（8126）上的 `docs/art/sample/qIcons.js`、`qIconsWeapons.js`，同一頁兩邊畫同一組 `look`，`getImageData` 比對。樣張的 `M`、`MAT` 先換成 `material.ts` 的鐵、鋼、銅（第 0.0 節第 3 點；不換的話鐵、鋼、銅本來就會差一階）。樣張那邊的圓章用它自己的 `blit`；裝備格用 `gearFrame`＋`blit`（樣張的 `paint()` 是縮放貼法，見下）。
- 61 款預設材質 × 圓章 20（res 1、2）、24、28 × 裝備格 32（res 1、2）、48、64：**488 組全部 0 像素不同**。
- 61 款 × 每款全部可用材質 × 裝備格 32（無／ignite＋傳說／frozen＋wet＋史詩）× 圓章 20 真 1 倍（無元素／fire／ice）：**2058 組**，0 差異的 2057 組；1 組（蛇骨鞭・皮・fire、圓章 20 真 1 倍）7 個像素差 1 個色階——共用 `color.ts` 的 `mix` 和樣張的 `mix` 四捨五入算式不同（`x(1−t)+yt` 對 `x+(y−x)t`），可重現。
- 和樣張原本的 `paint()`（裝備格縮放貼法）比，244 組都不同（最多 6142 像素）：就是需求 3.1 第 2 點說的「只差 blit 對齊的位移、邊緣更硬」。
- 雜訊：同一頁做了大量讀回後，Chrome 換軟體繪製，之後新畫的圖和先前快取的圖會差 1 色階（曾見 1～4 像素差 1）。重新載入頁面、兩邊交錯畫就是 0。

**(b) 舊程式**：`D` 表仍在 `gearIcon.ts`（防具飾品還用，武器副手那幾筆與 `pair()`、`SCALE` 已沒人用，QI-1b 整張拿掉）。墨線小圖示：`inkStyle.withIconMode` 在正式程式已沒有呼叫者（只剩測試）；`iconHead`、`inIconMode` 分支（`inkGear.ts`、`inkWeapons.ts`、`inkWeaponFrame.ts`）還在、但不在圖示模式就是 no-op；`shortWeaponIcon.test.ts` 仍測它們。照第 0.0 節第 9 點本段不刪。

**規則 6 亮度（深底裝備格 32px，圖樣平均亮度 ≥100、亮度 ≥150 的亮面 ≥5%；開發頁 `?set=audit`）——不達標的款，照指示沒有自己提亮：**

| 款 | 材質 | 平均亮度 | 亮面 |
|---|---|---|---|
| 錘・戰錘 | 鐵（預設） | 98.6 | 6.3% |
| 錘・釘頭錘 | 鐵（預設） | 99.97（顯示 100.0） | 7.2% |
| 錘・戰錘 | 銅 | 95.6 | 6.1% |
| 錘・釘頭錘 | 銅 | 96.9 | 7.2% |
| 斧・手斧 | 銅 | 99.9 | 10.0% |
| 火槍・獵槍 | 銅 | 99.97 | 7.8% |
| 拳套・拳刃 | 皮 | 89.5 | 7.7% |
| 拳套・鐵拳 | 皮 | 95.1 | 6.1% |

預設材質 61 款中 2 款不過（兩把錘，都是因為鐵改用 `material.ts` 較暗的 `#7a828b`）；全部材質 8 組不過。完整表在開發頁 `?set=audit`。

**截圖**（`docs/art/shots/qi1/`；全部用無頭 Chrome、`--force-device-scale-factor=1`、`--mute-audio` 拍；PNG＝真 1 倍／最近鄰特寫，照 11-12 開發 PM 更新）

| 檔 | 格式 | 對到 8.2 | 內容 |
|---|---|---|---|
| `docs/art/shots/qi1/1a-1-badge20-true1x-x6.png` | **PNG** | 第 1 項 | 圓章 20 真 1 倍 ×6，61 款 |
| `docs/art/shots/qi1/1a-2-badge20-dpr2-x6.jpg` | jpg（PNG 360 KB 超過） | 第 1 項 | 圓章 20 DPR 2 ×6 |
| `docs/art/shots/qi1/1a-3a-gear32-true1x-x6.png`、`1a-3b-…png` | **PNG** | 第 2 項 | 裝備格 32 真 1 倍 ×6（第 1～35、36～61 款） |
| `docs/art/shots/qi1/1a-4a-gear32-dpr2-x6.png`、`1a-4b-…png` | **PNG** | 第 2 項 | 裝備格 32 DPR 2 ×6 |
| `docs/art/shots/qi1/1a-5-sizes-badge24-28-gear48-64-dpr2.jpg` | jpg | 第 1、2 項 | 圓章 24、28 與裝備格 48、64，DPR 2 原大 |
| `docs/art/shots/qi1/1a-6-rarity-and-closeup-x6.png` | **PNG** | 第 3、8 項 | 直劍、鳶盾 × 5 稀有度（32 真 1 倍 ×6、64 DPR 2）＋特寫（鞭三款、雙左輪、雙彎匕、弓三款、拳刃圓章 20；拳刃、蛇骨鞭裝備格 32；真 1 倍與 DPR 2 各一列 ×6） |
| `docs/art/shots/qi1/1a-7-hammer-live.jpg` | jpg | 第 9 項 | 實機：英雄面板 24 圓章、裝備測試的主手格 64、地圖上的人物、物品列表 48、開局選武器 20（＋×3）——錘都是方頭 |
| `docs/art/shots/qi1/1a-8-paired-live.jpg` | jpg | 第 10 項 | 實機：開局選武器 20 的雙匕首、雙手槍（＋×3）、物品列表 48 的試煉雙七首、雙七首、雙手槍 |

另外同樣的特寫 PNG（含 jpg 的那張 `1a-2` 的 PNG 版）也留在共用筆記 `qi1-png\`。

**實機未看**：`RangeClassPick` 的成對圖示（目前靶場三大類的起始武器是單手劍、弓、火焰法杖，沒有成對武器；40px 尺寸是 1b）——用開發頁的裝備格截圖代替；英雄面板的 32px 裝備列（測試的 run 沒有裝備）；裝備格 32 的實機（用開發頁）。

## 5. 浮動卡實測、`__layoutSmoke`

**浮動卡**（自己的 `trpg serve`，大世界測試角色的背包）：

| 觸發元素 | 1600×900 | 800×600 |
|---|---|---|
| 背包格 `<Hint>`（稀有板甲） | 滑過後開在上方（400ms 內量到）→ 滑進卡片仍開 → 卡內滾輪（內容高 28＝可視 28，已在底、卡不關）→ 點一下 `pinned` → Esc 關 | 同左 |
| 身上裝備格主手 `PartTip` | 同上（內容高 60＝可視 60）；Esc 關 | 同左 |

兩張卡內容都不夠高，「捲到底」只驗到滾輪不會關卡。工坊的主手格（`part-tip-box no-bridge`）與物品列表沒有可滑進的卡（既有行為，沒動）。

**`window.__layoutSmoke.runCase`**：

| 尺寸 | 結果 |
|---|---|
| 1600×900 | 全 PASS（12 項） |
| 1040×624 | 全 PASS |
| 800×600 | 全 PASS |

## 6. 複雜度 noqa、長函式

沒有改 Python 程式（只改 YAML），沒有新增 noqa。前端逐行搬的函式沒有超過 80 行的（最長是 `whipCoil` 約 25 行、`SPEAR` 約 25 行）。

## 7. 請使用者重開伺服器檢查的重點

- 內容檔有改（`weapons.yaml`）：重開後進行中的一輪會從頭開始、舊世界日誌標成不能重播。
- 看：英雄面板的錘（方頭）、開局選武器的雙匕首／雙手槍（兩把）、裝備測試的物品列表與主手格。舊存檔裡沒寫 `form` 的錘，人物與圖示都會變成戰錘（D1；人物因此是雙手）。

## 8. 待 PM 決定

1. **規則 6 不達標**：預設鐵的戰錘 98.6、釘頭錘 99.97（第 4 節表；全部材質 8 組）。原因是改用 `material.ts` 較暗的鐵。由美術 PM 決定是否調畫法（第 0.0 節第 3 點）。
2. **固定零件的金屬色也跟著 `material.ts`**：第 0.0 節第 3 點說「圖示改用 material.ts 的色」，我讀成材質表 `MAT` 之外，樣張 `M` 裡的 `steel/steelD/iron/ironD`（箭頭、弩頭、錘柄底箍、包鐵圓盾的箍等固定零件）也一起換；`brass`、`gold`、`grip`、`shaft` 等照樣張。要只換材質表的話改 `core.ts` 的 `M` 四行（出處：`qIcon/core.ts` 檔頭）。
3. **混色用共用 `color.ts`**：和樣張 `mix` 的四捨五入算式不同，2058 組裡 1 組差 7 個像素 1 色階（第 4 節）。照專案「調色只用 color.ts」做；要逐像素一致就改用樣張那份。
4. **寶石色**：照需求 3.4 第 22 點用現行 `palette().accent`（第一個關鍵字的色，12 個都認）；樣張只認 4 個元素關鍵字、取第一個元素關鍵字。關鍵字是 `[prone, ignite]` 時兩邊寶石色不同（樣張本來就沒定義這種情況）。
5. **`gearIconKey` 多了 `element`**：Q 版杖頭、法器珠的光球色看外觀的 `element`（例如 `holy` 這類不混色的元素），`resolveGear` 不保留 element，鍵不含它會撞快取。內容資料目前只有 fire／lightning／ice，實際上不會撞。
6. **元素不是四元素時**：`qResolve` 照樣張留 `look.element`（`holy` 等會畫該元素的光球色），現行 `gearIcon` 是忽略。照樣張做。
7. **圓章的 `rarity`、`keywords`**：`weaponIconItem`／`GearItem` 沒有這兩個欄位，武器小圖示一律普通、無關鍵字（和現行一樣）；開發頁的 `&rarity=` 只影響裝備格。
8. **報告檔名**：規格第 10 節是 `PhaseQI-1報告.md`（1b 在同檔加節），派工指定 `PhaseQI-1a報告.md`，照派工。1b 要不要併檔請定。
9. **`1a-2`（圓章 20 DPR 2 ×6）用 jpg**：PNG 360 KB 超過 300 KB 上限；要 PNG 就得拆成兩張（會超過 10 張）。

## 9. 上手筆記更新

- `docs/dev/上手-前端戰鬥畫面與動畫.md`：第一節表加 `render/qIcon/`、`weaponIcon.ts`、`gearIcon.ts`、`ui/GearIcon.tsx`／`WeaponIcon.tsx` 的職責；第二節「開發入口」表加 `weaponicon-gallery.html` 的參數；第四節加第 18～21 點（CSS 不要縮放圖示畫布、材質色兩份、vitest 要假畫布、瀏覽器像素比對的 ±1 雜訊）；第五節測試表加「武器、裝備小圖示」一列。
- `docs/dev/上手-內容資料與模擬.md`：第四節加第 14 點（改武器 `look` 要重產 `glossary.json`；原第 14 點改為第 15 點）。
