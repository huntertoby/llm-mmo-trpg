# Q 版小圖示第 1、2 批（武器、副手、防具、飾品）：移植需求（給開發 PM）

美術 PM，2026-11-12。這是 Q 版小圖示的第一份移植需求，對應開發的移植段「①＋②」（`docs/美術PM交接.md` 0.01 節的分段）。

- **定案依據**：使用者看過第 1、2 批，沒有意見（2026-11-12，專案 PM 轉達，原話：「都照建議」）。第 1 批第 3 版過審（`Q版小圖示-第1批武器-審查.md`「第 3 版複審」），第 2 批第 3 版過審（`Q版小圖示-第2批防具飾品-審查.md`「第 3 版複審」）；前三批真 1 倍補查第 2 版複審通過（`Q版小圖示-前三批真1倍補查.md`，文件 commit `5a509e6c`）。
- **樣張版本**：第 1 批的圖 `6ff3d19a`、第 2 批的圖 `8584c43e`，加上真 1 倍修正 `0caaa84f`（`QIconsWeapons.blit()`）。**以 `0caaa84f` 之後的 `docs/art/sample/` 為準**。
- **紀錄（逐款描述、撞圖、和人物不一致的地方）**：`docs/art/Q版小圖示-第1批武器.md`、`docs/art/Q版小圖示-第2批防具飾品.md`。兩份的第 9 節「給開發移植的重點」已整理進本文第 3 節。
- 畫法規則 14 條：`docs/art/Q版小圖示樣張.md` 第 2 節（精簡版在 `docs/art/上手-畫法.md` 2.3）。
- **沒有實機截圖**：樣張的「現行」欄，武器小圖示用的是遊戲端打包的 `docs/art/sample/tools/obLiveIcons.js`，裝備圖示用的是樣張端的 `gearArt.js`（不是遊戲端的 `gearIcon.ts`）。

## 1. 目標與範圍

### 1.1 要換掉的畫法（只換框裡的圖）

| 遊戲端 | 現在 | 換成 |
|---|---|---|
| `client/src/render/weaponIcon.ts` 的 `weaponItemIconCanvas()`／`weaponIconCanvas()`（武器小圖示，米色圓章） | 墨線畫法 `inkWeapons.drawInkWeaponAlone`，先 `measure()` 量外框再縮放，成對武器用 `pairedPart()` 畫成單把 | Q 版圖樣的**圓章構圖**（第 1 批），成對武器畫兩把 |
| `client/src/render/gearIcon.ts` 的 `drawGear()`，`slotType` 是 `weapon`、`offhand` 的造型 | `D` 表裡的現行畫法 | Q 版圖樣的**裝備格構圖**（第 1 批） |
| 同上，`slotType` 是 `head`、`body`、`hands`、`feet`、`ring`、`neck` 的造型 | 同上 | Q 版圖樣（第 2 批） |

兩批都換完後 `gearIcon.ts` 的 `D` 表可以整張拿掉（第 2 批紀錄第 9 節第 2 點）。

**範圍數量**（和 `client/src/render/gearAppearance.json` 的 `kinds[].forms` 逐項對過，一致）：

- 武器 17 種 53 款：`sword`(4)、`greatsword`(3)、`dagger`(3)、`dual_dagger`(3)、`axe`(3)、`hammer`(3)、`spear`(3)、`scythe`(3)、`fist`(3)、`whip`(3)、`bow`(3)、`crossbow`(3)、`longgun`(3)、`shotgun`(3)、`pistol`(3)、`dual_pistol`(3)、`staff`(4)。
- 副手 4 種 8 款：`round_shield`、`kite_shield`、`tome`、`orb` 各 2 款。
- 防具 18 種 37 款：頭 `hood`、`hat`、`circlet`、`cap`、`helmet`(3)；身 `robe`、`leather`、`mail`、`plate`、`coat`；手 `cloth_gloves`、`leather_gloves`、`gauntlets`、`bracers`；腳 `shoes`、`boots`、`iron_boots`、`greaves`（未註明的都是 2 款）。
- 飾品 3 種 7 款：`ring`(3)、`pendant`(2)、`charm`(2)。
- 變體：材質（10 種）、染色（布、皮；8 色）、元素關鍵字 4 個（`ignite`、`wet`、`charged`、`frozen`）、稀有度 5 級，分法照現行，沒有新增規則。

### 1.2 不動的（規則 13：框不動，只換框裡的圖）

- **米色圓章**：CSS `.weapon-icon`（`client/src/styles/theme.css` 約 329 行：漸層 `#f6eed8`→`#d6c7a2`、`box-shadow` 金框）。Q 版圖樣只畫圖、不含圓章底。
- **裝備格**：`gearIcon.ts` 的 `frame()`（深底 `#23262d`、稀有度框色、非普通的右上角色塊、史詩以上底光、傳說內框）原樣保留。
- **關鍵字小圖樣**：`motif()`、`SMALL_ICON_MAX_PX`（36）照舊，只有位置改用 Q 版的 `meta.spots`（第 3 節第 12 點）。
- 人物（`qDoll` 系列）、技能圖示、狀態圖示、物品圖示等其他小圖示都不在這一段。

### 1.3 用到這兩個畫法的地方（`client/src/` 查到的呼叫處；驗收截圖照這張表拍）

| 元件 | 檔案 | 尺寸（CSS px） |
|---|---|---|
| `WeaponIcon`（圓章） | `run/RunHeroPanel.tsx` | 24 |
| | `run/StartPicker.tsx`、`world/RangeParts.tsx` | 20 |
| | 元件預設值 | 28 |
| `GearIcon`（裝備格） | `run/RunHeroPanel.tsx`、`ui/gear/HeroGearPanel.tsx`、`ui/UnitInfo.tsx`、`ui/gear/GearCardView.tsx`（目前裝備）、`world/GainEffects.tsx`、`world/MailPanel.tsx` | 32 |
| | `ui/gear/ItemList.tsx`、`world/BagScreen.tsx`、`world/RangeClassPick.tsx` | 48 |
| | `ui/gear/GearCardView.tsx`、`ui/gear/SlotGrid.tsx`、`ui/gear/CustomItemForm.tsx` | 64 |
| CSS 把 canvas 縮放的 | `.world-bag-cell .gear-icon`（42，`styles/world-economy.css`）、`.ob-kit-row canvas.gear-icon`（40，`styles/range-ob.css`）、`.world-worn-box .gear-icon`（`min(48px, calc(100% - 4px))`） | 見第 3 節第 3 點 |
| 開發頁 | `client/dev/weaponicon-gallery.html`（`src/dev/weaponIconGallery.ts`，`?px=`）、`client/dev/gear-gallery.html`（`src/dev/gearGallery.ts`） | |

## 2. 來源與移植方式

### 2.1 樣張畫法檔（`docs/art/sample/`）

| 檔案 | 內容 | 主要 API |
|---|---|---|
| `qIcons.js`（`window.QIcons`） | 共用：剪影外框、畫法小工具、八把武器樣本、圓章自動縮放、裝備格留白 | `render(def, px, res, { ow, badge })` → 邊長 `round(px × res)` 的 canvas（只有圖樣）；`outlinePx(px)`；`badgeScale(d, 上限)`；`GEAR_PAD`（0.06）；`H`（`mix、f、rr、ci、el、poly、ln、halo…`）；`W`（八把樣本的畫法，含 `W.diag`、`W.towerShield`、`W.arcaneArt`）；`M`（材質色）、`EL`（元素色） |
| `qIconsWeapons.js`（`window.QIconsWeapons`） | 第 1 批：武器 17 種 53 款＋副手 4 種 8 款 | `def(look)` → `{ zh, d, pre, post, meta: { badge, diag, spots, r } }`；`paint(ctx, look, size, res, { frame: "badge"｜"gear"｜"none", motif })`；`blit(ctx, cv, x, y, a, res)`；`resolve`、`palette`、`gearFrame`、`KINDS`、`MAT`、`MAT_ZH`、`KW`、`RARITY`、`NO_FORM`、`GEAR_PAD`、`canvas`、`list` |
| `qIconsArmor.js`（`window.QIconsArmor`） | 第 2 批：防具 18 種 37 款＋飾品 3 種 7 款（只有裝備格）；依賴上面兩個檔 | `def(look, slot?)` → `{ zh, d, meta: { spots, r, lifted, tone } }`（沒有 `pre`／`post`／`badge`）；`paint(ctx, look, size, res, { frame: "gear"｜"none", motif, slot })`；`resolve`、`palette`、`KINDS`、`DYE`、`SLOT_DEFAULT_KIND`、`canvas`、`list` |

樣張頁：`q-icons-weapons.html`、`q-icons-armor.html`（`?part=a｜b｜c｜var｜scene｜close&kind=…｜audit｜review｜hash｜true1x`；武器頁另有 `cmp`）、`q-icons.html`（風格樣張）。

### 2.2 建議的移植方式

1. **照樣張原樣搬成 TypeScript，不另畫簡化版**（品質底線第 5 條「已有素材一定要用」）。三個檔的畫法（`d`／`pre`／`post`、各款的 `…Art` 函式、`palette`、`tone`）逐行搬；武器相關可以併成一個模組（第 1 批紀錄第 9 節第 5 點）。新檔放 `client/src/render/` 下，檔名由開發決定。
2. **`resolve` 用遊戲端的 `resolveGear()` 當唯一來源**，Q 版畫法吃它的結果。樣張的 `resolve()` 和 `resolveGear()` 有幾處不同（2.4 節），不要照搬樣張那一份。
3. **出圖照樣張的 `paint()` 流程**，但只畫圖樣、框照現行：圓章＝`render(def, size × meta.badge, res, { ow: outlinePx(size), badge: true })` 用 `blit()` 貼在中心；裝備格＝`frame()` 之後 `render(def, size × 0.88, res)` 用 `blit()` 貼在四邊留 6% 的位置。
4. 搬完用樣張頁對照：同一組 `look`、同一個尺寸與 `res`，遊戲端的圖和樣張的圖應該逐像素相同或只差不到半個裝置像素的位移（裝備格多了對齊，見第 3 節第 2 點）。

### 2.3 和遊戲端清單對齊

- 種類、款式、可用材質、預設材質：`client/src/render/gearAppearance.json`（由 `content/equipment/appearance.yaml` 匯出）。樣張的 `KINDS` 照它寫，數量一致（1.1 節）。
- 武器外觀：`content/weapons.yaml` 的 `look`（經 `/api/glossary` 的 `weapon_looks` 給前端，`appearance.ts` 的 `weaponLook()`）。有 `look` 的 23 把都在 61 款裡；沒有 `look` 的 10 把（`spark_staff`、`water_jet`、`shade_blades`、`talons`、`bomb_casing`、`vine_lash`、`guardian_rod`、`totem_stone`、`stone_fist`、`fangs`）照 `weapon_class` 退回 `sword`／`bow`／`staff`（`WEAPON_CLASS_KIND`），也會畫成 Q 版的對應款。
- 副手：`content/offhands.yaml` 沒有外觀欄位；副手物品的外觀在 `content/items.yaml`（`kind`、`form`、`material`；例：`item_offhand_tower_shield` 是 `kite_shield`／`tower`／`iron`）。

### 2.4 樣張與遊戲端對不上的地方（逐條）

| # | 項目 | 樣張 | 遊戲端 | 移植怎麼做 |
|---|---|---|---|---|
| 1 | 元素關鍵字名 | `gearArt.js`（樣張的「現行」欄）用舊名 `shock`／`freeze`；`qIconsWeapons.js` 的 `KW`、`EL_OF_KW` 兩種名字都收（`shock`、`freeze` 是別名）；`qIconsArmor.js` 只用新名 | `charged`／`frozen`（`gearAppearance.json` 的 `elementKeywords`） | 只用 `charged`／`frozen`，別名不用搬 |
| 2 | 魔導劍形制 | `gearArt.js` 沒有 `arcane`；Q 版有（`W.arcaneArt`） | `sword` 有 `arcane`（`arcane_blade` 的 `look`） | 照 Q 版 |
| 3 | 沒寫 `form` 的錘 | `qIconsWeapons.js` 的 `NO_FORM = { hammer: "warhammer" }`：退成戰錘（方頭） | `resolveGear()` 退成清單第一款 `mace`（釘頭錘）；`weapons.yaml` 的 `hammer` 沒寫 `form`（`items.yaml` 的兩把錘有寫 `warhammer`） | 補 `form: warhammer`（第 4 節第 1 點）；`resolveGear()` 要不要也加同樣的退回見第 4 節第 2 點 |
| 4 | 不認得的 `kind` | 防具樣張退成 `helmet`；武器樣張退成 `sword` | 一律退成 `sword`（`FALLBACK_KIND`），沒有 `kind` 時照欄位 `SLOT_DEFAULT_KIND` | 照遊戲端 |
| 5 | 關鍵字過濾 | 只檢查是字串、取前 2 個 | 只留 `KEYWORD_COLOR` 認得的、取前 `maxKeywords`（2） | 照遊戲端 |
| 6 | `color`（人物外觀覆寫色） | `look.color` 會蓋掉材質色，換色照 `tone()`；進快取鍵 | `GearLook` 沒有 `color`（`appearance.ts` 的 `DollGearLook` 有） | 待開發查證：圖示的呼叫處有沒有機會拿到 `color`；沒有就不用接（第 4 節第 3 點） |
| 7 | 材質色 | 鐵 `#8d969f`／`#5a6169`、鋼 `#c3ccd6`／`#7d8794`、銅 `#c27a48`／`#7e4a28`（人物那一份；其餘同遊戲端） | `material.ts`：鐵 `#7a828b`／`#474c52`、鋼 `#a9b6c6`／`#6d7a8a`、銅 `#b06a3c`／`#6e3e20` | 圖示另開一張表照樣張，**不要改 `material.ts`**（紙娃娃、墨線畫法都從它導出）。遊戲端的 Q 版人物實際用哪一份材質色：待開發查證（`qSample.ts` 是樣張那一份，只給開發頁用） |
| 8 | 外框色 | `#16121a`（`qCore.ts` 的 `Q_OUT` 同色） | 現行裝備圖示描邊 `GEAR_INK` `#16181d` | 圖樣外框用 `#16121a`；框（`frame()`）不動 |
| 9 | 關鍵字小圖樣的位置 | `meta.spots` 是 48 格座標；樣張示意時只疊第一個元素關鍵字、縮 0.75 | `motif()` 畫在 64 格座標（`SCALE` 放大後），每個關鍵字各一處、只有一個時兩處 | 第 3 節第 12 點 |
| 10 | 小圖示方向 | 長條 45°、長槍霰彈槍 −45°、手槍 −0.42 弧度、拳刃 45°、鐵拳爪直立 | `iconAngle()`：手槍、拳套 0，其餘 ±45° | 照 Q 版（畫法裡已轉好，不再呼叫 `iconAngle()`） |
| 11 | 成對武器 | 圓章與裝備格都畫兩把 | 小圖示用 `pairedPart()` 換成單把；`RangeClassPick.tsx` 拿 `weaponIconItem()` 的結果給 `GearIcon` | 圖示不再換單把（第 3 節第 7 點）；人物仍用 `pairedPart()` |
| 12 | 顯示尺寸 | 圓章 20、24、28；裝備格 32、42、48、64，都直接畫在該尺寸 | `GearIcon` 的 `size` 只收 32／48／64；42、40 與 `min(48px, …)` 是 CSS 把 canvas 縮放 | 第 3 節第 3 點 |

## 3. 一定要做對的重點

每條後面括號是出處（`第1批` ＝ `Q版小圖示-第1批武器.md`，`第2批` ＝ `Q版小圖示-第2批防具飾品.md`，`上手` ＝ `上手-畫法.md`）。

### 3.1 出圖與貼圖

1. **圖樣貼進框裡不要縮放，要對齊整數裝置像素。** `render(def, a, res)` 畫出來的 canvas 邊長是 `round(a × res)`；如果用 `drawImage(cv, x, y, a, a)` 縮放貼到小數位置（`a × res` 或 `x × res` 不是整數），瀏覽器會重新取樣，1px 外框被抹成半透明、整塊糊掉（真 1 倍補查的鞭三款、雙左輪就是這樣；2 倍也會，只是較不明顯）。用 `blit()`：照 canvas 原尺寸 `cv.width / res` 貼、以原本的格子為中心、左上角四捨五入到整數裝置像素：
   ```js
   function blit(ctx, cv, x, y, a, res) {
     const w = cv.width / res, snap = (v) => Math.round(v * res) / res;
     ctx.drawImage(cv, snap(x + (a - w) / 2), snap(y + (a - w) / 2), w, w);
   }
   ```
   例：圓章自動縮放（`meta.badge < 1`，61 款裡 38 款）20px 時 `a`＝19.32、`p`＝0.34。`weaponItemIconCanvas()` 與 `drawGear()` 都要照這樣做。（第1批 9.0 (k)、13.1；上手 2.5 最後幾條；`Q版小圖示-前三批真1倍補查.md` 結論與第 2 版複審）
2. **裝備格四邊留白 6% 也一起對齊。** 留白算出來同樣是小數：32px 時 `p`＝1.92、`a`＝28.16（2 倍是 3.84、56.32）；42px 時 2.52、36.96；48px 時 2.88、42.24；64px 時 3.84、56.32。樣張這一條路徑沒改（第 1 批裝備格、第 2 批仍是縮放貼法，為了不動過審的指紋；真 1 倍 32px 仍認得出），**移植時建議一起用 `blit()`**。因此遊戲端的裝備格和樣張截圖會差不到半個裝置像素的位移、邊緣更硬，不算不一致。（第1批 9.0 (k)；上手 2.5 最後一條；第2批 9.2）
3. **不要讓 CSS 再縮放 canvas。** 現在 `.world-bag-cell .gear-icon`（42）、`.ob-kit-row canvas.gear-icon`（40）、`.world-worn-box .gear-icon`（`min(48px, …)`）把 48 或 32 的 canvas 用 CSS 縮放，瀏覽器重新取樣，會把第 1、2 點的對齊抵銷（外框發糊）。建議 `GearIcon` 直接在顯示尺寸畫（樣張 42px 就是直接畫的）；怎麼改由開發決定（第 4 節第 4 點）。`.gear-icon` 的 `image-rendering: auto` 在不縮放時沒有影響。（本文查證：`client/src/styles/`）
4. **剪影外框的做法**：先畫色塊，再把剪影往外長一圈墊在底下（`render()` 裡的 `dilate()`：剪影往一圈方向位移 `r` 與 `r/2` 疊起來再染外框色，不用逐步膨脹）；`pre`（光暈）畫在外框底下、`post`（弓弦、箭桿這類細線）畫在最上面。外框色 `#16121a`。（第1批 9.3；上手 2.1）
5. **外框粗細**＝5%、最細 1、最粗 1.6 CSS px：**圓章用圓章直徑**（`outlinePx(size)`：20px→1、24px→1.2、28px→1.4），**裝備格用圖樣邊長**（`render()` 預設 `outlinePx(圖樣邊長)`；32px 格的圖樣 28.16 → 1.41）。（第1批 2 節、9.3；第2批 9.3）
6. **畫法收到的 `o`**：`small`＝圖樣邊長 ≤24px、`tiny`＝≤14px、`owPx`（外框幾個裝置像素）、`badge`（畫在圓章裡）、`u`（1 CSS px 是幾個 48 格單位，畫 1px 細線用）、`flat`（量剪影那一遍）；成對武器另有 `pair`、`rear`（後面那把）。**圓章一定要傳 `badge: true`**，`meta.badge` 也要用圓章的構圖量（`badgeScale()`）。（第1批 9.0 (a)(d)；上手 2.5）
7. **圓章自動縮放與留白只定義一次**：`badgeScale()`（圖樣最遠點離中心 ≤21.2 單位，`floor` 到千分位，以 `meta` 給的上限封頂）與 `GEAR_PAD`（0.06）在 `qIcons.js`，第 1、2 批與風格樣張共用，不要各寫一份。圓章：邊長 `size × meta.badge`、置中；不再需要 `measure()`。（第1批 2 節、9.2；上手 2.5）
8. **快取鍵**：武器含 `kind、form、material、keywords、element、rarity、color、px、frame`；防具飾品含 `kind、form、material、dye、keywords、rarity、color、px`（現行 `gearIconKey` 多一個 `color`）。兩者都要再加內部解析度 `res`（若之後不固定 2）。`def()` 第一次會量一次圖樣範圍（兩張 96px 畫布），之後走快取。（第1批 9.4；第2批 9.7）

### 3.2 武器與副手（第 1 批）

9. **接法**：
   - `weaponItemIconCanvas(item, px)`：畫圓章構圖的圖樣，不含圓章底（圓章是 CSS）。不再呼叫 `measure()`、`iconAngle()`、`drawInkWeaponAlone()`。
   - `drawGear()`：`slotType` 是 `weapon`、`offhand` 的改呼叫 Q 版，留白 6%；`frame()`、`motif()`、`SMALL_ICON_MAX_PX` 照舊。
   - `def(look)` 的 `look = { kind, form?, material?, element?, keywords?, rarity?, color? }`，欄位同 `GearLook`／`GearItem`。（第1批 9.1、9.2）
10. **成對武器**：圖示直接給 `dual_dagger`／`dual_pistol`，不要再用 `pairedPart()` 換成單把（`weaponIconItem()` 拿掉那一行；人物的 `dollGear` 照舊）。畫法走 `crossed()`：後面那把先畫、前面那把包外框；短刀、三稜刺、燧發、短銃、左輪交叉成 X，**彎匕兩把並排斜放不交叉**。`RangeClassPick.tsx` 的 48px 圖示會因此從單把變兩把（預期）。（第1批 9.0 (d)(i)、9.2；美術 PM 決定見審查第 1、3 版）
11. **同一個題材、兩種框的構圖差異要保留**：
    - 鞭：圓章裡是「左下握柄＋實心螺旋圓捲＋往右上勾出去的鞭梢」（`whipCoil`、`COIL`、`COIL_TAIL`、`COIL_GRIP`），裝備格是 S 形；圓章 ≤24px 時圓捲上的螺旋暗線換成一道淺色外弧＋一小段深色內弧，鞭身 3.2→4、梢端米白加粗。
    - 蛇骨鞭裝備格：刃片只留甩出去的後半段（`whipPts(5.6)` 走到 42% 之後的點）、四片放大（半寬 4.6）。
    - 弓：圓章裡弦是 `post` 的 1px 深褐線（`#5a3a22`，不是外框色）、箭桿 `#3a2616` 1.25px，自己不包外框、線寬用 `o.u`；裝備格弦白、箭桿淺木色、箭尾紅羽。圓章不分尺寸都留箭（規則 8 的例外）。
    - 雙手槍・左輪：圓章 ≤24px 前面那把（`o.small && o.pair && o.badge && !o.rear`）轉輪放大、加一道暗槽；後面那把省轉輪與扳機護弓。
    - 雙匕首・彎匕：圓章 ≤24px 兩把間距 4.6→5.8 單位（`meta.badge` 0.969）。
    - 雙短銃：成對且 ≤24px 槍管 17→21 單位。
    （第1批 9.0 (b)(c)(g)(l)(m)(n)(o)、11.2）
12. **形制細節照樣張**：拳刃 45° 斜放（`katarArt` 畫在直立座標、`W.diag` 轉），`meta.diag` 為 `true`、圓章不套 0.86 上限、關鍵字小圖樣位置用斜放那一組（畫法回傳的 `diag`、`spots` 蓋掉種類預設）；鐵拳、爪直立。斬馬刀前段放寬。`W.towerShield` 的 `deco`（武器／裝備圖示傳 `true`，32px 以上畫四角鉚釘、頂邊微拱）。圓盾在圓章裡上限 0.8。（第1批 9.0 (e)(h)(j)、11.2）
13. **方向**：長條武器握把左下、作用端右上（45°）；長槍、霰彈槍槍口朝右上（−45°）；手槍只斜 −0.42 弧度；拳套（拳刃除外）、盾、書、法器珠直立；斧刃、鐮刃在柄的右下那側。（第1批 2 節；上手 2.4）
14. **稀有度**：史詩以上護手換色（單手劍、匕首的暗銅→金 `#e8bb48`；雙手劍的金→亮金 `#f6d878`），其餘照現行框。（第1批 1 節變體表、`qIconsWeapons.js` 的 `palette()`）
15. **沒寫 `form` 的錘畫方頭戰錘**：請補 `weapons.yaml`（第 4 節第 1 點）。補之前樣張的 `resolve()` 會把它當戰錘、遊戲端的 `resolveGear()` 會當釘頭錘，兩邊不一致。（第1批 9.0 (f)、9.6；審查第 1 版「美術 PM 的決定」）

### 3.3 防具與飾品（第 2 批）

16. **接法**：`drawGear()` 裡 `slotType` 是 `head`、`body`、`hands`、`feet`、`ring`、`neck` 的改呼叫 Q 版圖樣，`render(def, px × 0.88, res)` 貼在四邊各留 6% 的位置（用 `blit()`，第 2 點）。只有裝備格，沒有圓章。最小 32px，`o.small` 不會成立（畫法裡有 `o.small` 分支，但沒驗過）。鞋靴一律單隻、鞋尖朝右。（第2批 2 節、9.2、9.3）
17. **換色照顏色判斷、不照染色名稱**（美術 PM 定案，第 2 批審查「第 3 版複審」）。染料 `dye` 和外觀覆寫色 `color` 走同一套（`qIconsArmor.js` 的 `tone()`），之後新增的染料、自訂色不用另外寫。對原色算：
    - 亮度 L＝0.299R＋0.587G＋0.114B；彩度 C＝三個色版的最大減最小（0～255）。
    - ① **L ≥ 105**：不換（綠、白、金）。
    - ② **近黑：L < 70 且 C < 40**（黑 `#33363d`：L 54、C 10）：保留深色，主色＝原色混 10% 白（`#474a50`；兜帽混 17%），滾邊翻口色 `t` 用未染布的米灰（布色混 42% `#ffe6b8`）。規則 6 的例外（第 18 點）。
    - ③ **其餘深色、C ≥ 90**（紅 C 126、藍 C 126、紫 C 102）：三個色版同乘 1.09（四捨五入、上限 255），重複到 L ≥ 105；只提高明度、不混白（紅 `#b83a3a`→`#db4545`、藍 `#3a5fb8`→`#4571db`、紫 `#7a4ab0`→`#8551c0`）。
    - ④ **其餘深色、C < 90**（褐 `#7a5232`：L 90、C 72）：每次混 15% 白，重複到 L ≥ 105（美術 PM 決定保留這一級）。
    - ③④ 樣張的迴圈最多跑 4 次（`n++ < 4`），照搬。
    - 暗色 `d`＝換亮之後的主色混黑 35%（現行是染料原色混黑 35%）。
    （第2批 9.4 (a)、1 節變體表；審查「第 2 版複審」「第 3 版複審」的美術 PM 決定）
18. **黑染是規則 6 的例外**：不比照「平均亮度 ≥100」，**不加任何描邊或像素後處理**（第 2 版的 `rimLight()`／`getImageData` 已拿掉）；亮度只靠各款原有的米灰滾邊、翻口、金扣與左上亮面。移植後的測試如果有亮度檢查，`meta.tone === "black"` 的要另列、不套平均亮度門檻（樣張自查的實際值 74～173）。（第2批 9.10 (d)(e)、7 節；審查「第 2 版複審」必修 1 與決定）
19. **兜帽另外亮一階**：主色亮度 < 118 時整件再亮一階（③ 的顏色再乘一次 1.09；其餘混 15% 白）；近黑不換主色，改成洞口那圈裡布混白 45%（其他色 30%）、左上亮面放大。兜帽全部尺寸不畫束繩。（第2批 9.4 (b)、9.10 (a)、12.1）
20. **`palette(r)` 的欄位與固定色**：`a` 主色、`d` 暗色、`l` 金屬亮面（主色混 45% 白）、`t` 皮布淺色滾邊（主色混 42% `#ffe6b8`）、`dd` 洞裡最深（暗色混 55% 外框色）、`accent` 寶石、`tone`。元素關鍵字混色：防具 25%／15%、飾品 40%／25%、晶石直接換色。固定色：腰帶 `#3a2a1c`、金扣 `#d8b04a`、骨白 `#e9e3cf`、角 `#e8d8b8`、紅繩 `#c8483e`、米白 `#e8e0c8`、膚色 `#f1c9a5`。材質色用人物那一份（2.4 節第 7 列）。（第2批 9.4、1 節變體表）
21. **canvas 功能**：素戒、臂環用 `destination-out` 真的挖洞（看得到格底）；鎖鏈護手的指縫也是 `destination-out` 挖空、靠整體外框填成深色線；護膝甲片、披風外套的外套身／披風前襟／立領用 `halo()` 各自再包一圈外框；`roundRect`。全部是一般的路徑填色，沒有像素後處理。（第2批 9.8、9.10 (b)(c)(d)）

### 3.4 關鍵字小圖樣（兩批共用）

22. **小圖樣照現行 `motif()` 接**，>36px（`SMALL_ICON_MAX_PX`）才畫；位置改用 Q 版的 `meta.spots`（48 格座標，換算到框內：`p + spot × (size − 2p) / 48`；樣張示意時縮 0.75）。12 個關鍵字都照現行畫（現行是每個關鍵字一處、只有一個關鍵字時兩處都畫）；寶石換成關鍵字色照現行 `palette().accent`（Q 版的 `accent` 目前只認 4 個元素關鍵字，其餘 8 個請照現行補）。小圖樣本身這一段不重畫：使用者 11-12 已同意把它納入 Q 版全量重畫，排在之後的批次，屆時另給移植需求。（第1批 1 節變體表、9.2；第2批 9.5；`美術PM交接.md` 0.00 節使用者答覆第 2 點）

## 4. 內容欄位、後端與要決定的事

| # | 項目 | 誰決定 | 說明 |
|---|---|---|---|
| 1 | `content/weapons.yaml` 的 `hammer` 補 `look: {kind: hammer, material: iron, form: warhammer}` | 已決定（美術 PM，第 1 批審查第 1 版；使用者看過沒意見），開發 PM 排入 | 只影響外觀。補了之後裝備圖示、小圖示與人物才一致。前端的 `client/src/battle/fixtures/glossary.json` 目前是 `"form": null`，要不要重跑 `scripts/export_client_fixtures.py`（`tests/api/test_client_fixtures.py` 有對照測試）：待開發查證 |
| 2 | `resolveGear()` 遇到沒寫 `form` 的 `hammer` 要不要也退成 `warhammer`（同樣張的 `NO_FORM`） | **開發 PM 決定** | 第 1 點補完後 `weapons.yaml` 沒有缺 `form` 的錘；這條只影響之後新增卻漏寫 `form` 的錘。美術建議加（和人物的方頭一致），不加也不擋移植 |
| 3 | 外觀覆寫色 `color` 要不要進 `GearLook` | **開發 PM 決定**（若要加到 API 才需要後端） | 樣張的 `look.color` 走和染料同一套換色；遊戲端圖示的呼叫處目前沒有 `color`。沒有用到就不接，換色規則仍照第 17 點寫成照顏色判斷 |
| 4 | CSS 縮放的 40、42、`min(48px, …)` 改成直接畫在顯示尺寸 | **開發 PM 決定**做法 | 美術要求的是結果：驗收時這幾處的外框是硬邊、不比 32／48 糊（第 3 節第 3 點） |
| 5 | 內部解析度 | **開發 PM 決定**（不擋移植） | 遊戲端現在固定 DPR 2（`weaponIcon.ts` 的 `DPR`、`gearIconCanvas()` 的 `px * 2`），100% 縮放螢幕上是 2 倍圖被瀏覽器縮小。這一段不要求改；驗收看真 1 倍是最壞情況（第 5 節） |
| 6 | `gearAppearance.json` | 不用改 | 清單、各形制材質、染色、稀有度都已經有（第2批 9.6） |

**需要玩法 PM 決定的：沒有。** 後端除了第 1 點的內容檔（與第 3 點若要加欄位）以外不用動。

## 5. 驗收（美術 PM 會看的截圖）

每項都要有截圖；實機到不了的用開發頁（`client/dev/weaponicon-gallery.html`、`client/dev/gear-gallery.html`，可擴充）畫出來，並在報告寫「實機未看」。瀏覽器測試靜音（網址加 `?mute=1`）。

**最小尺寸一律交兩種**：(a) **DPR 2**（遊戲現在的內部解析度）；(b) **真 1 倍**（canvas 寬高＝CSS px，內部解析度 1）。兩種都用最近鄰放大 6 倍（`image-rendering: pixelated`）的圖交；截圖要用裝置像素比 1 拍（放大 6 倍的一個像素在截圖裡是 6×6 的純色方塊）。開發頁怎麼切到內部解析度 1：待開發查證（樣張頁的做法是 `canvas(…, { res: 1 })`）。

| # | 要看的 | 尺寸 | 對照的樣張截圖（`docs/art/` 下） |
|---|---|---|---|
| 1 | 武器＋副手 61 款，圓章 | 20 真 1 倍＋DPR 2；24、28 DPR 2 | `shots/qicons/true1x/weapons-badge20-01.png`～`-03.png`；`shots/qicons/weapons-a-melee1.png`、`weapons-a-melee2.png`、`weapons-a-ranged.png`、`weapons-a-off.png`；剪影撞圖 `shots/qicons/weapons-b.png` |
| 2 | 武器＋副手 61 款，裝備格 | 32 真 1 倍＋DPR 2；48、64 DPR 2 | `shots/qicons/true1x/weapons-gear32-01.png`～`-08.png`；總表 A 同上 |
| 3 | 稀有度框：直劍、鳶盾 × 5 級（史詩、傳說的底光與護手金色） | 32 真 1 倍；64 DPR 2 | `shots/qicons/true1x/weapons-rarity32-01.png`；`shots/qicons/weapons-var.png` |
| 4 | 防具＋飾品 44 款，裝備格 | 32 真 1 倍＋DPR 2；42、48、64 DPR 2 | `shots/qicons/true1x/armor-gear32-01.png`～`-06.png`；`shots/qicons/armor-a-head.png`、`armor-a-body.png`、`armor-a-hands.png`、`armor-a-feet.png`、`armor-a-acc.png`；`shots/qicons/armor-b.png` |
| 5 | 染色：黑、紅、藍、褐各 4 款（長袍、斗篷帽、露指手套、長靴）；另外布、皮各一款的 8 色全排 | 32 真 1 倍＋DPR 2 | `shots/qicons/true1x/armor-dark32-01.png`、`-02.png`；`shots/qicons/armor-var.png` |
| 6 | 材質變體：每種武器、防具至少一款的全部可用材質（含鏈鞭的銀、骨暗節） | 32 DPR 2 | `shots/qicons/weapons-var.png`、`armor-var.png` |
| 7 | 元素：4 個元素關鍵字的混色（金屬、晶石、杖頭、法器珠各一）＋ >36px 的小圖樣位置；一個非元素關鍵字（寶石換色） | 32、48、64 DPR 2 | `shots/qicons/weapons-var.png`、`armor-var.png`、`weapons-scene@2x.png` |
| 8 | 點名款的特寫（最近鄰放大）：鞭三款圓章 20、雙左輪圓章 20、雙彎匕圓章 20、弓三款圓章 20（弦與弓臂之間看得到米色空隙）、拳刃圓章 20 與裝備格 32、蛇骨鞭裝備格 32、黑長袍／黑布兜帽／黑素手套 32、護膝脛甲、印戒、披風外套 32 | 真 1 倍＋DPR 2 | `closeup/qicons/weapons/t1x-fix.png`、`whip.png`、`dual_pistol.png`、`dual_dagger.png`、`bow.png`、`fist.png`；`closeup/qicons/armor/robe.png`、`hood.png`、`cloth_gloves.png`、`greaves.png`、`ring.png`、`coat.png`；`shots/qicons/weapons-cmp-whip.png` |
| 9 | 錘：補 `form: warhammer` 後的英雄面板圓章、裝備格、地圖上的人物各一張，三處都是方頭 | 實機 | `closeup/qicons/weapons/hammer.png`；人物對照 `shots/qicons/weapons-c.png` |
| 10 | 成對武器：雙匕首、雙手槍在圓章與裝備格都是兩把；`RangeClassPick` 的 48px | 實機 | `closeup/qicons/weapons/dual_dagger.png`、`dual_pistol.png` |
| 11 | 實機畫面，每處一張（1.3 節的表）：英雄面板 24 圓章＋32 裝備列、開局選武器 20、靶場武器架 20、背包 42（含空格的灰色預設造型）、裝備卡 64／32、裝備欄格 64、物品列表 48、單位資訊 32、獲得物品 32、信件 32、靶場套組 40、身上裝備格 | 實機 | `shots/qicons/weapons-scene.png`、`weapons-scene@2x.png`、`armor-scene.png`、`armor-scene@2x.png`、`q-icons-scene.png`、`q-icons-scene@2x.png` |
| 12 | CSS 縮放的三處（42、40、`min(48px, …)`）在 100% 縮放螢幕上的放大圖：外框是硬邊 | 實機 | 同第 2、4 項的 32 真 1 倍（不能比它糊） |
| 13 | 和人物並排（開發頁做得到才交）：人物拿著同一件與圖示並排 | DPR 2 | `shots/qicons/weapons-c.png`、`armor-c-head.png`、`armor-c-body.png`、`armor-c-hands.png`、`armor-c-feet.png`、`armor-c-acc.png` |

另外請在報告寫明：(a) 第 2.2 節第 4 點的對照方式與結果（和樣張逐像素相同，或只差裝備格對齊的位移）；(b) `D` 表與墨線小圖示的舊程式是否已拿掉、有沒有其他地方還在用。

## 6. 待決／已知未修（都不擋移植）

各批審查最後一版列的「可修」都留到之後順手，移植照現在的樣張即可；之後改了樣張再另給增量。

**第 1 批（第 3 版複審的可修）**
- 鞭三款圓章 20px 的剪影幾乎一樣，靠花紋與顏色分；要改是把蛇骨鞭甩出去那段加長加粗。
- 拳刃 20px 的拳頭只是一塊淺灰（美術 PM 決定維持鐵色，使用者覺得不像手再改）。

**第 2 批（第 3 版複審的可修）**
- 黑長袍 32px 前襟線看不到：使用者嫌暗再補一條米灰前襟線（黑素手套、黑布兜帽可接受）。
- 綠染兜帽仍是混白、略淡：之後照彩度判斷（兜帽那一階）。

**真 1 倍補查**：第 1、2 批沒有剩下的可修（第 1 次的兩項可修——雙彎匕間距、蛇骨鞭裝備格骨刺——已在 `0caaa84f` 修好）；第 2 版複審剩的三項可修（巨人、雙牙、幼蜥）屬第 3 批技能主圖，不在這一段。

**已知、交使用者時已講明的（不是缺陷）**
- 稀有度右上角色塊會被圖樣蓋住一部分，外框色完整（美術 PM 決定維持）。
- 鏈鞭、蛇骨鞭預設材質是皮所以是褐色；塔盾預設鐵灰（資料檔如此）。
- 元素關鍵字小圖樣沒重畫，疊在 Q 版上偏細（之後的批次重畫，第 3 節第 22 點）。
- 鞭在圓章與裝備格是兩種構圖；雙匕首三款裡彎匕並排、另兩款是 X；弓小尺寸留箭；鞋靴畫單隻。
- 同類之間要看細節才分得出的：短刀與三稜刺、三款弩、雙管與泵動、三把元素長杖、短靴與鐵靴、三款手套、長袍與旅行外套、短袍／獵裝／鎖子甲、印戒與寶石戒、皮臂甲與長皮手套。
- 黑染 32px 偏暗的三款（長袍、素手套、布兜帽）；全罩盔多紅纓與金 T；披風外套多立領與金鍊；皮臂甲畫了拳頭；護膝是盾形小甲片。
- 樣張只在樣張頁看過，沒有實機圖；遊戲端固定 DPR 2，真 1 倍是最壞情況。

## 7. 順手記（不屬這次範圍，排不排由開發 PM 決定）

- 樣張端的 `gearArt.js`（舊名 `shock`／`freeze`、沒有魔導劍）只是樣張頁「現行」欄用的，不需要跟著改；移植完成後樣張頁的「現行」欄會和遊戲端不同，不影響驗收。
