# Q 版小圖示第⑥批（物品）：移植需求（給開發 PM）

畫圖 agent（美術 PM 派），2026-11-12（Opus 5.5）。Q 版小圖示的第七份移植需求，對應「⑥ 物品」。格式照 `Q版小圖示-事件卡移植需求.md`。

- **定案依據**：
  - 使用者 2026-11-11 同意把墨線小圖示改 Q 版（原話「好」）。
  - 使用者 2026-11-12 對下面四點說「可以」（專案 PM 轉述）：
    1. 商店等清單列，在名稱前加 24 px 小圖示。
    2. 物品飛進背包的圖示，改成深底圓形加金邊。
    3. 框色：材料用稀有度框；消耗品等其他類用褐金框 `#8a6a3a`，不用「普通」的灰框。
    4. 遊戲端目前沒有物品圖示，這批是第一套。框的類別底色沿用 `itemIcons.js`。
  - 美術 PM 已定（紀錄第 10 節）：規則 2 例外放寬到切割寶石、結晶；規則 6 近黑例外延伸到黑色材料；小、中回復藥同剪影、染料六罐同形、三種晶叢靠顏色分，都接受。
- **樣張版本**：第 2 版 `ca6ac921`、`e9717cf7`，複審通過 `c8aec041`（`Q版小圖示-第6批物品-審查.md`「複審」）；焦鐵小修 `519fea34`（複審的可修，紀錄第 13 節）；活血骨框線改紫（美術 PM 決定照 content `rare`，紀錄第 13 節末）。**以這版之後的 `docs/art/sample/` 為準**。畫法 `qIconsItems.js`（`ICON` 表 37 個）、頁 `q-icons-items.html`。
- **紀錄**：`docs/art/Q版小圖示-第6批物品.md`。第 1 節盤點、第 2 節清單、第 3 節大小、第 9 節是給開發的重點。本文整理後**取代**第 9 節，和紀錄有出入時以本文為準。
- **沿用 QI-1 的決定**（`PhaseQI-1計畫.md` 0.0 節）：畫布＝顯示尺寸 × `ICON_RES`（2），圖樣貼整數裝置像素（`blit`），開發頁可切 1 倍給驗收用；材質色照 `material.ts`。
- **段名**：建議 **QI-7**（QI-6 是 ⑧ 事件卡），由開發 PM 定。**估 1 段**（見第 6 節）。

## 1. 範圍

### 1.1 要畫上圖示的地方（遊戲端 `main` 查過）

| # | 位置 | 元件（`client/src/`） | 現行 | 改成 | 顯示大小 |
|---|---|---|---|---|---|
| 1 | 背包 6×5 物品格 | `world/BagScreen.tsx` `BagCellView`（`row.gear !== true` 那一支） | `.world-bag-tile` 名字小牌（`bagGrid.ts` 的 `tileLines`） | 物品圖示（背包框），右下個數 `.world-bag-count` 照現行 | **42**（格子 `--bag-cell` 50，和 `GearIcon size={42}` 同大） |
| 2 | 腰包一排 | 同上（`pouchCells`） | 同上 | 同上 | 42 |
| 3 | 信件附件 | `world/MailPanel.tsx` 61～62 行（`.mail-thing` 非裝備）、373～374 行（`.mail-thing-chip`） | 10px 金色小方塊 `.mail-thing-mark` | 物品圖示（背包框），小牌高度照現行 32 | **32** |
| 4 | 拿到物品飛進背包 | `world/GainEffects.tsx` `GainFlyIcon`／`GainIcon`；`world/gainFx.ts` `gainIconOf` | 物品＝細線布袋 SVG、沒外觀的裝備＝細線劍 SVG（深底圓金邊） | 物品畫**自己的** Q 版圖示，框一律**深底圓金邊**（使用者決定 2）；表裡沒有的物品＝`gain_item`（Q 版布袋）；沒外觀的裝備＝`gain_gear`（Q 版劍）。有外觀的裝備照 6Q-1 現行（`GearIcon` 32 ＋ `.gain-gear`），不動 | **28**（`.item-fly` 28） |
| 5 | 清單列（使用者決定 1） | `world/EconomyPanel.tsx`：`ShopPanel` 買（`.world-shop-list` 第一張）、賣東西（第二張）、`PouchEditor`；`world/LootChoicePanel.tsx`（背包滿了選丟哪件）；`world/SmithyPanel.tsx` 特色材料的勾選標籤（`label.world-craft-material`） | 純文字列 | 買、賣、整理腰包、背包滿了：`.world-shop-name` 前面加物品圖示（背包框）。鐵匠：`label.world-craft-material` 裡沒有 `.world-shop-name`，圖示放在 **checkbox 和名字之間** | **24** |

- 清單列裡的**裝備列**（背包滿了選丟哪件：`LootChoicePanel` 的 `item.gear === true`；賣東西：後端 `world_economy_view.py` 的 `_gear_item` 把有價格的裝備設成 `sellable`，會出現在賣東西清單）：見第 5 節第 3 點。
- 鐵匠的「通用料」是 `<select>`（`SmithyPanel.tsx` 約 76 行），`<option>` 放不了圖，照現行文字。
- `EconomyPanel.tsx` 的 `InventoryPanel`／`BagRow`：`main` 上沒有元件在畫它（只剩測試與註解），這段不加；若開發查到還有地方用，照第 5 列加。

### 1.2 不動的
- **框**（規則 13）：背包格（白 3% 底、`rgb(200,168,104,.22)` 框、選取金框）、腰包格、信件小牌（`.mail-thing-chip`）、清單列樣式、`.item-fly` 的位置、陰影、動畫，都照現行。物品圖示自己的框（背包框、飛行圓）是**這批新做的**（第 3 節第 1、2 點）。
- 個數：背包格右下 `.world-bag-count` 照現行 CSS（樣張的 `countText()` 只是示意，不搬）。
- 戰鬥技能列的「道具」欄（`SkillBar.tsx` `item-group`，技能圖示）：**不在這批**（美術 PM 決定 4，之後另開一項）。
- 樣張端有、遊戲端沒有的物品（信件、鑰匙、地圖殘頁、護符、源晶碎片）：沒畫（美術 PM 決定 5）。
- 錢包（金幣、任務幣）：第⑦批 HUD 已有，不動。
- 選取物品的詳情（`BagScreen.tsx` `ItemDetail`）、`InventorySummary` 的文字：不加圖。
- 後端、`content/`：**不用動**（染料顏色、稀有標記怎麼帶到前端見第 5 節第 1、2 點）。

### 1.3 行為改變（要講明）
1. 背包、腰包的物品格從深褐「名字小牌」換成圖示，和裝備圖示同大（42）；名字改看滑過說明（`cellHint` 照現行）。
2. 物品框的底色分類：消耗品綠、投擲瓶藍、補給褐、材料灰、染料紫。框線色：材料＝稀有度色（灰／藍／紫，和裝備同一套），其他一律褐金 `#8a6a3a`。
3. 物品飛進背包畫該物品的圖示，深底圓金邊；以前所有物品都是同一個布袋。**圓的大小和有外觀的裝備飛行（6Q-1）不同**：物品照 `GainIcon` 是 28 格裡直徑 26 的圓、金邊壓在圓上；裝備是直徑 32 的圓、金邊畫在圓外，外徑差約 6px（現行通用圖已經是這樣）。維持哪一種見第 5 節第 8 點。
4. 商店、賣東西、整理腰包、背包滿了選丟哪件、鐵匠特色材料的清單，名稱前多一個 24 的圖示。
5. 信件附件的金色小方塊換成 32 的物品圖示。

## 2. 清單：37 個圖示 ↔ 物品 id

物品 id 照 `content/world/items.yaml`（35 個，`main` 與本分支相同；`ItemKind`＝consumable｜material｜dye｜supply）＋通用 2 個。**框的類別（cat）與品質（tier）不是從 content 推出來的，是 `qIconsItems.js` `ICON` 表的欄位**，照搬（見第 4 節第 2 點）。

| 類（cat → 底色） | id | 名稱 | 框線 | 畫法（`qIconsItems.js`） |
|---|---|---|---|---|
| 消耗品 consumable（綠 `#2a3a30`） | `item_hp_potion_small` | 小回復藥 | `#8a6a3a` | 沿用風格樣張 `ART.item.item_hp_potion_small` |
| | `item_hp_potion_medium` | 中回復藥 | 同上 | `hpMediumArt` |
| | `item_mana_potion` | 回魔藥 | 同上 | 沿用 `ART.item.item_mana_potion`，`fitIn(0.92)` |
| | `item_antidote_herb` | 解毒草 | 同上 | `herbArt` |
| 投擲瓶 throwable（藍 `#2a3040`） | `item_water_flask` | 水瓶 | 同上 | `waterArt` |
| | `item_oil_flask` | 油瓶 | 同上 | `oilArt` |
| | `item_mist_flask` | 霧瓶 | 同上 | `mistArt` |
| | `item_frost_flask` | 冰瓶 | 同上 | `frostArt` |
| | `item_fire_flask` | 火瓶 | 同上 | 沿用 `ART.item.item_fire_flask`（`pre`＋`d`），`fitIn(0.9)` |
| 補給 supply（褐 `#3a3020`） | `item_supplies` | 補給 | 同上 | 沿用第⑦批 `hud.ts` 的 `ration`（只在商店出現：不進背包） |
| 材料 material（灰 `#2e2a26`） | `item_coarse_material` | 粗料 | 品質 1 common `#8a8f99` | `coarseArt` |
| | `item_fine_material` | 精料 | 品質 2 rare `#4f9dff` | 沿用 `ART.item.item_fine_material` |
| | `item_superior_material` | 上料 | 品質 3 epic `#b06cff` | `superiorArt`（`pre` 光暈） |
| | `item_essence` | 精華 | 3 | `essenceArt`（`pre`）；規則 2 例外 |
| | `item_scorched_iron` | 焦鐵 | 1 | `ironArt`（`lamella`、`IRON_CHAR`） |
| | `item_mist_crystal` | 霧晶 | 2 | `mistCrystalArt`（`pre`；飛行 `fly: 0.77`） |
| | `item_summit_mist_crystal` | 雲頂霧晶 | 3 | `summitArt`（`pre`） |
| | `item_talisman_ash` | 符紙灰 | 1 | `ashArt` |
| | `item_cinnabar` | 丹砂 | 2 | `cinnabarArt` |
| | `item_wolf_fang` | 狼牙 | 1 | `fangArt` |
| | `item_thunder_feather` | 雷羽 | 2 | `thunderArt` |
| | `item_living_bone` | 活血骨 | 3（稀有） | `boneArt`（`pre`） |
| | `item_green_bamboo` | 青竹節 | 1 | `bambooArt` |
| | `item_lava_core` | 熔岩核 | 2 | `lavaArt`（`pre`） |
| | `item_frost_ember` | 寒燼 | 3 | `frostEmberArt`（`pre`） |
| | `item_molten_heart` | 熔心晶 | 3 | `moltenArt`（`pre`；飛行 `fly: 0.82`）；規則 2 例外 |
| | `item_ember_feather` | 餘燼羽 | 2 | `emberArt`（`pre`） |
| | `item_sulfur_crystal` | 硫磺結晶 | 1 | `sulfurArt` |
| | `item_obsidian_shard` | 黑曜片 | 2 | `obsidianArt`；規則 6 例外 |
| 染料 dye（紫 `#30283a`） | `item_dye_indigo`、`item_dye_cinnabar`、`item_dye_ink`、`item_dye_jade`、`item_dye_ochre`、`item_dye_snow` | 靛青、朱砂、墨色、翠綠、赭黃、雪白染料 | `#8a6a3a` | 同一個 `dyeArt(color)`，只換顏色（`#2E4A7D`、`#B23A2E`、`#2B2B2B`、`#3E8E6A`、`#C08A3E`、`#E8E8E8`＝items.yaml 的 `color`） |
| 通用（飛行圓） | `gain_gear` | 通用：裝備 | 金邊 | 沿用第④批徽章「打擊」：`parts.ts` `entry("skeleton","strike")`，`b10(…, 1.2)` |
| | `gain_item` | 通用：物品 | 金邊 | `sackArt`（新畫的布袋） |

合計 37：新畫 31、沿用 6（小回復藥、回魔藥、火瓶、精料、補給、通用劍）。

## 3. 來源與依賴

**移植方式**：照前幾段，逐行搬樣張，只做型別調整，檔頭寫「和樣張不同」。同一個題材只有一份畫法，**能呼叫已移植的 `client/src/render/qIcon/` 就呼叫，不要另畫一份**。建議新檔 `qIcon/items.ts`（由開發定）。

### 3.1 沿用已移植的（直接呼叫）

| 圖示 | 呼叫 |
|---|---|
| 補給 `item_supplies` | `hud.ts` 的 `ration`（QI-5 已搬；樣張 `QH.def("ration").d`） |
| 通用裝備 `gain_gear` | `parts.ts` 的 `entry("skeleton", "strike")`（樣張 `QP.entry`；亮鋼是部件字面色 `#c3ccd6`，不換 material.ts，同 `parts.ts` 檔頭） |
| 小回復藥、回魔藥、火瓶、精料 | 風格樣張 `qIcons.js` 的 `ART.item`（284～305 行）：遊戲端還沒有（`legacy48.ts` 只有 `status`、`hud`、`event`），**這段搬進 `legacy48.ts` 的 `ART.item`**（和 QI-6 的 `ART.event` 同處）；`liquid`、`GLASS` 一起搬 |
| 畫法小工具 | `core.ts`：`mix`、`f`、`rr`、`ci`、`el`、`poly`、`ln`、`starPts`、`glow`、`flame`、`sparkle`、`halo`、`blank`、`render`、`outlinePx`、`blit`、`OUT`、`HI2`；`legacy48.ts` 的 `drop`（水瓶、油瓶的水滴） |
| 稀有度色 | `render/artPalette.ts` 的 `GEAR_RARITY`（common／rare／epic）：**直接引用，不另抄色**（樣張 `QW.RARITY` 是同一份） |

每個圖示的 `pre`（光暈）、`fly`（飛行圓裡的圖樣比例）、`cat`、`tier`、`color` 寫在 `qIconsItems.js` 的 `ICON` 表，照搬。`zh`、`grp`、`kind`、`src`、`topic` 只給樣張頁，可以不搬。

### 3.2 這批新畫的（從 `qIconsItems.js` 搬）
- 小工具：`at`、`st`、`clip`、`b10`、`fitIn`、`leafPath`／`leaf`、`prism`、`cloud`、`bipyr`、`liquid`。
- 畫法：`hpMediumArt`、`herbArt`、`waterArt`、`oilArt`、`mistArt`、`frostArt`、`coarseArt`、`superiorArt`、`essenceArt`、`ironArt`（`IRON_CHAR`、`IRON_*`、`lamella`）、`mistCrystalArt`、`summitArt`、`ashArt`、`cinnabarArt`、`fangArt`、`thunderArt`、`boneArt`、`bambooArt`、`lavaArt`、`frostEmberArt`、`moltenArt`、`emberArt`、`sulfurArt`、`obsidianArt`、`dyeArt(color)`、`sackArt`。
- 出圖：`ICON`、`frameOf`、`glyphPx`、`glyph`、`rimOf`（`NEUTRAL_RIM`＝`#8a6a3a`、`TIER_RARITY`）、`bagFrame`、`flyFrame`、`paint`、`canvas`。
- **類別底色**：樣張 `bagFrame()` 讀的是 `itemIcons.js` 的 `ItemIcons.CAT[cat][0]`（`itemIcons.js` 本身不搬）。遊戲端在 `items.ts` 寫一張 `ITEM_CAT_BG`：consumable `#2a3a30`、throwable `#2a3040`、supply `#3a3020`、material `#2e2a26`、dye `#30283a`（使用者決定 4：沿用 `itemIcons.js`）。漸層往下到 `#1a1612`。

### 3.3 遊戲端的接法（建議，由開發定）
- `render/itemIcon.ts`（或併進 `qIcon/items.ts`）：`itemIconCanvas(id, px, res = ICON_RES, opt?)` 回傳含框的畫布、有快取；`hasItemIcon(id)`；**帶明確的 `frame` 參數**（`"bag"｜"fly"`；樣張 `canvas()` 本來就收 `opt.frame`）。沒給時才照樣張 `frameOf` 推（28＝飛行圓，其他＝背包框；`gain_*` 永遠飛行圓），以後別處用到 28 的背包框才不會被畫成圓。
- `ui/ItemIcon.tsx`：照 `GearIcon` 的寫法（畫布寬高＝`iconCanvasPx(size)`，CSS 不縮放畫布；`label` 給 `aria-label`）；props 帶 `frame`，呼叫端明寫（飛行處寫 `frame="fly"`，其他寫 `frame="bag"`）。
- `BagCellView`：`row.gear !== true` 時 `<ItemIcon id={row.item} size={42} />` 取代 `.world-bag-tile`；`world-economy.css` 的 `.world-bag-cell > button:has(.world-bag-tile)` 那條規則跟著改。表裡沒有的 id：退回現行名字小牌（不畫布袋，背包裡布袋看不出是什麼）。
- `gainFx.ts`：`GainIconChoice` 加一種 `{ kind: "item"; item: string }`（非裝備且 `hasItemIcon`）；`GainFlyIcon` 畫 `<ItemIcon id size={28} />`（飛行圓已含在畫布裡，不另包 `.gain-gear`）；`GainIcon` 的兩個 SVG 換成 `gain_gear`、`gain_item` 的 28 圖。
- 清單列：`.world-shop-name` 前一個 `<ItemIcon size={24} frame="bag" />`；放在同一個 `Hint` 裡（滑過圖示也出說明）。鐵匠特色材料：放在 `label.world-craft-material` 裡的 checkbox 和名字之間。

## 4. 一定要做對的重點

1. **背包框**（42、32、24）：圓角 `size × 0.16`、類別底色漸層（上 `ITEM_CAT_BG[cat]` → 下 `#1a1612`）、線寬 `max(1.5, size × 0.035)`、框線色 `rimOf(id)`：材料＝`GEAR_RARITY[{1:common, 2:rare, 3:epic}[tier]]`，其他＝`#8a6a3a`（**不是** common 的 `#8a8f99`：使用者決定 3）。現有 19 個材料都有 tier（`rare: true` 的四個是 3）；**材料沒有 tier 時的框線待美術 PM 定**：樣張 `rimOf` 現在回傳褐金 `#8a6a3a`，和使用者決定 3「材料用稀有度框」不合，已回報，定案前這段不會遇到（表裡沒有的 id 照第 5 節第 4 點退回現行）。圖樣格＝`size × 0.86` 置中，`blit` 貼到整數裝置像素。
2. **飛行圓**（28）：照 `GainIcon` SVG 原樣——深底 `#2a2018` 圓 r＝13/28 × size、金邊 `#e8bb48` 線寬 1.6/28 × size；圖樣格＝`size × (ICON[id].fly ?? 0.8)`（霧晶 0.77、熔心晶 0.82），**裁在內圓 r＝12.2/28 × size**（主形不出內圓，外框貼到金邊被裁一點可以）。**這個圓和有外觀的裝備飛行（6Q-1 `.item-fly .gain-gear`：直徑 32、`box-shadow` 1.6 金邊畫在圓外）不是同一個大小**：物品圓直徑 26、金邊壓在圓上，外徑差約 6px。照第 5 節第 8 點的決定做；選 (a) 就維持這裡的數字。
3. **外框與簡化**：外框 `outlinePx(size)`（24→1.2、28→1.4、32 以上 1.6；照**顯示大小**，不是圖樣大小）。`small`（圖樣 ≤24px）照圖樣本身：24 的圖樣 20.6、28 的 22.4（飛行圓）都是 `small`，32 的 27.5、42 的 36.1 不是。這批沒有 ≤14px 的圖樣（都包外框）。
4. **尺寸與 DPR**：

| 用在 | 顯示（CSS px） | 畫布（`ICON_RES` 2） | 框 | 圖樣本身 | `small` | 外框 |
|---|---|---|---|---|---|---|
| 背包格、腰包格 | 42 | 84×84 | 背包框 | 36.1 | 否 | 1.6 |
| 信件附件 | 32 | 64×64 | 背包框 | 27.5 | 否 | 1.6 |
| 飛進背包 | 28 | 56×56 | 飛行圓 | 22.4（霧晶 21.6、熔心晶 23.0） | 是 | 1.4 |
| 清單列 | 24 | 48×48 | 背包框 | 20.6 | 是 | 1.2 |

   遊戲端固定 DPR 2（同 QI-1）；開發頁要能切 `res=1` 給驗收看真 1 倍（最壞情況）。

5. **整數像素**：圖樣貼進框用 `blit`（左上角四捨五入到整數裝置像素，不縮放）。清單列的 24 是 flex 置中，列高、字高可能讓圖示的左上角落在小數 CSS px → 瀏覽器重新取樣、1px 外框發糊：用 `GearIcon` 的 `pixelSnapNudge` 做法挪到整數裝置像素，或確定列的 `align-items` 下圖示的 y 是整數。驗收看真 1 倍要是硬邊。`.item-fly` 是 Web Animations 移動的，飛行中不要求整數像素（現行裝備飛行也一樣），**停下來那一格（`.still`）**要清楚。
6. **清單列高**：照現行；若 24 的圖示把列撐高，報告寫實量的前後列高。
7. **染料顏色不要只寫死在圖示表**（紀錄第 9 節）：見第 5 節第 1 點。
8. **沿用的圖照樣張的縮放呼叫**：回魔藥 `fitIn(0.92)`、火瓶 `fitIn(0.9)`（原樣貼邊，24 外框會被切）、通用劍 `b10(…, 1.2)`；原畫法本身不改。
9. **規則例外（照樣張，不要「修正」）**：
   - **黑曜片＝規則 6 的黑色材料近黑例外**：本體保留深灰黑帶紫 `#3a3446`（暗面 `#26222e`），平均亮度只有 86、不套 ≥100；亮度靠左上寬的灰紫反光 `#a49cb8` 與兩道白邊亮線（24 加粗），亮面 24%。**不要為了過亮度把本體提亮**（第 1 版提亮成淡紫，像紫水晶，被審查退）。
   - **熔心晶＝規則 2 切割寶石例外**：8 片切面只用 4 階（亮 `#ffc060`、本色 `#e86a1e`、暗一 `#c8501a`、暗二 `#a8400e`，相鄰不同階），**桌面 `#ffe27a` 不計入 4 階**（只限填發光元素色：這顆是裡面透出的火光，上面再畫主色火＋白芯）。精華的菱形 4 面（`#fff6d0`／`#fbe8a0`／`#e8c460`／`#d8b04a`）也是這條例外。
10. **焦鐵用小修後的版本**（`519fea34`）：三片焦黑高度錯開、上緣是不規則斜邊（`IRON_CHAR`）；≥32 右片的裂紋跟著右片焦角的點走（`right[3]`→`right[4]`）。指紋要對這一版。

## 5. 要開發 PM 決定的事

| # | 項目 | 美術建議 |
|---|---|---|
| 1 | **染料顏色從哪來**：API 的 `BagItemView`／`ShopItemView` 沒有 `color`；樣張的 6 色是照抄 items.yaml | (a) 後端在物品的 view 加選用欄位 `color`（只有染料有，讀 items.yaml），圖示用 `dyeArt(color)`；之後加新染料不用改前端。(b) 不動後端：`ICON` 表照抄 6 色，另加一個測試比對 `content/world/items.yaml` 的 `color`，不一致就失敗。美術偏 (a)；不論哪個，表裡沒有的染料 id 都用 `dyeArt(該色)`，沒有顏色就用 `gain_item` |
| 2 | **材料品質（tier）放哪**：content 沒有品質欄（只有 `grade` 與 `rare`），樣張的 tier 是 `itemIcons.js` 抄來的 | **稀有材料一律依 content `rare` 推品質 3**（epic 紫框；美術 PM 2026-11-12 決定，活血骨因此從 2 改 3，樣張已照改）；rare 以外的品質仍照樣張 `ICON` 表搬（前端資料）；新材料沒有 tier 時的框線待美術 PM 定（第 4 節第 1 點）。`rare` 要從後端帶到前端（例如物品 view 加選用欄位），或前端表照抄＋測試比對 items.yaml，和第 1 點同一個做法 |
| 3 | **清單列裡的裝備列**：兩處——背包滿了選丟哪件（`LootChoicePanel`，裝備和物品混排）、賣東西（`ShopPanel` 第二張清單；後端 `_gear_item` 讓有價格的裝備 `sellable`） | 兩處同一個做法：裝備列放一個 24 寬的空位對齊名字，不畫 24 的裝備圖（裝備圖示最小 32，24 沒有審過）。要畫的話另提給美術 |
| 4 | 表裡沒有的物品 id | 背包格、清單列：退回現行（名字小牌／不加圖，清單列留 24 空位對齊）；飛行：`gain_item`。開發頁列出「內容裡有、表裡沒有」的 id（現在應為 0） |
| 5 | 檔放哪、怎麼切 | 新畫的放 `qIcon/items.ts`；風格樣張 `ART.item` 四個放 `legacy48.ts`；`ItemIcon` 元件放 `ui/` |
| 6 | 換完後的死碼：`GainIcon` 兩個 SVG、`.world-bag-tile*` CSS、`tileLines`／`TILE_LINE_CHARS`（若只剩表裡沒有的 id 在用則保留）、`.mail-thing-mark` | 沒有呼叫處就刪；測試 `panelIcons.test.ts` 的名字小牌斷言跟著改 |
| 7 | 開發頁 | 照 QI-6 的 `event-gallery`：`client/dev/item-gallery.html`，`?set=a｜fly｜list｜scene｜hash`、`&res=1｜2`、`&zoom=`、`&grp=` |
| 8 | **物品飛行圓的大小**：物品照 `GainIcon` 是 28 格裡直徑 26 的圓（金邊 1.6 壓在圓上）；有外觀的裝備（6Q-1）是直徑 32 的圓、金邊畫在圓外。兩種一起飛時（最多 3 個）外徑差約 6px | **(a) 物品維持 28（美術建議）**：照本文第 4 節第 2 點，明寫「外徑和裝備不同，維持現況」（現行通用圖和 6Q-1 本來就差這麼多）。(b) 物品改成 32、用和 `.gain-gear` 同一個圓：圖樣格照 0.8 × 32 重算，`fly` 比例、樣張自查表的飛行一表、`items-fly-t1` 都要重做，先回美術 |

**需要玩法 PM 決定的：沒有。** `content/` 不用動。

### 指紋比對
- 樣張 `uv run python docs/art/sample/tools/qicons_shots.py --hash items`（頁 `q-icons-items.html?part=hash`）：**37 行**，每行一個 id，每個用到的大小各一組 `2 倍／1 倍`（含框；物品 24、28、32、42，通用只有 28）。開發頁 `?set=hash` 出同一個 FNV 與行格式。
- **材質色照 QI-6 的做法**：和「`qIcons.js` 的 `M`、`qIconsWeapons.js` 的 `MAT` 的鋼、鐵、銅換成 `material.ts` 的樣張」比（`PhaseQI-6報告.md` 4 (a)）。這批的圖幾乎都是字面色（通用劍是部件的亮鋼字面色，不經過 `M`），預期換不換都 37 行全同；有不同的行，報告列出 id 與原因。
- 不同時先查：框的類別底色、`rimOf` 的稀有度色、`fly` 比例、`fitIn` 縮放、焦鐵是不是 `519fea34` 之後的版本。

## 6. 段數估計

**1 段（QI-7）**。理由：畫法 37 個都是單檔逐行搬（樣張 `qIconsItems.js` 約 380 行，和 QI-6 的 `qIconsEvent.js` 同量級），沿用的只多 `ART.item` 四個；接法 5 處都是「把一個元素換成 `<ItemIcon>`」，不改版面。
若要拆（例如同時進行的 agent 不能改同一批檔）：QI-7a＝畫法＋開發頁＋背包格、腰包、信件、飛行；QI-7b＝5 張清單列（`EconomyPanel.tsx`、`LootChoicePanel.tsx`、`SmithyPanel.tsx`），7b 在 7a 之後。

## 7. 驗收（美術 PM 會看的截圖）

每項都要有截圖；實機到不了的，用開發頁畫出來並寫「實機未看」。網址一律加 `?mute=1`，無頭 Chrome 加 `--mute-audio`；預覽伺服器不用 8000／8001。開發頁照 QI-1 加 `?px=`、`&res=1|2`、`&zoom=`。**最小尺寸交兩種：真 1 倍＋DPR 2**，都用最近鄰放大，裝置像素比 1 拍。只有真 1 倍與最近鄰特寫可以用 PNG（單張 ≤300 KB），其他用 jpg 80；**每段 ≤10 張**。存 `docs/art/shots/<段名>/`。

**張數怎麼放進 10 張**：第 1～4 項各合成**一張**對照表（PNG），排法照樣張 `items-t1`：每格「現行｜真 1 倍｜DPR 2」，同一張裡放該項用到的每個大小。第 5～9 項各一張 jpg，要看的最近鄰裁切（格子、一列清單、飛行停格）**併進同一張 jpg 的角落**，不另存。第 10 項貼在報告裡，不算張數。合計 9 張。

| # | 張 | 要看的 | 尺寸 | 對照（`docs/art/` 下） |
|---|---|---|---|---|
| 1 | 1（PNG 合成） | 藥與草 4、投擲瓶 5、補給 1（背包框，類別底色、褐金框線） | 24 真 1 倍＋DPR 2；42 真 1 倍 | `closeup/qicons/items/a-potion.png`、`a-throw.png`、`a-supply.png`；`shots/qicons/true1x/items-t1-01～03.png` |
| 2 | 1（PNG 合成） | 材料 19（框線＝灰／藍／紫，和裝備同色；稀有四個紫框）；焦鐵、熔心晶、黑曜片要看得清楚 | 24 真 1 倍＋DPR 2；42 真 1 倍 | `closeup/qicons/items/a-mat.png`、`a-cloud-1.png`、`a-cloud-2.png`、`a-ashen.png`；`true1x/items-t1-03～07.png` |
| 3 | 1（PNG 合成） | 染料 6（同一個罐子、六色分得開） | 24 真 1 倍＋DPR 2 | `closeup/qicons/items/a-dye.png`；`true1x/items-t1-07～08.png` |
| 4 | 1（PNG 合成） | 飛行圓 37 個（35 物品＋通用 2；主形沒有被圓裁掉） | 28 真 1 倍＋DPR 2 | `closeup/qicons/items/a-gain.png`；`true1x/items-fly-t1-01～03.png`、`items-t1-08.png` |
| 5 | 1（jpg，角落併 32 真 1 倍裁切） | 信件附件 32（小牌高度不變） | 實機 jpg＋32 真 1 倍 | `true1x/items-t1-*` 的 32 格；`shots/qicons/items-scene.jpg` 右欄「信件附件」 |
| 6、7 | 1（jpg，角落併格子裁切與飛行停格裁切） | 實機背包：背包 6×5＋腰包，和裝備圖示混排、個數照現行；拿到物品飛進背包停住那一格（`.still`）：物品、沒外觀的裝備、有外觀的裝備並排（圓的外徑照第 5 節第 8 點的決定，選 (a) 時物品比裝備小一圈是預期） | 1600×900 jpg；裁切最近鄰 | `shots/qicons/items-scene.jpg` 左上與中段右、`items-scene-bag@2x.jpg` |
| 8 | 2（jpg：1600×900、800×600 各一；1600 那張角落併一列真 1 倍裁切） | 實機商店買、賣兩張清單（24 圖示、列高、價格與鈕位置不變）；**賣東西清單要含一列裝備**（24 空位對齊） | 1600×900 與 800×600 | `shots/qicons/items-scene.jpg` 右欄商店 |
| 9 | 1（jpg，角落併裁切） | 背包滿了選丟哪件（物品與裝備混排，裝備列的空位對齊）、整理腰包、鐵匠特色材料（圖示在 checkbox 和名字之間） | 1600×900 jpg（實機到不了的用開發頁） | `shots/qicons/items-scene.jpg` 中段「背包滿了」 |
| 10 | 0（報告貼表） | 開發頁的「內容裡有、表裡沒有」清單（應為 0）與指紋結果 | — | — |

報告另外寫明：(a) 和樣張指紋比對的結果（37 行，相同幾行，不同的列原因；材質色換不換的兩種都寫）；(b) 第 5 節第 1～4、8 點怎麼處理；(c) 清單列的 24 怎麼對齊整數像素、列高前後；(d) 每項在哪一張。

## 8. 交使用者時要講明（記錄）
1. 背包裡的物品從「名字小牌」換成圖示（和裝備一樣大），每類一個底色；框線顏色只表示材料品質（和裝備稀有度同一套），其他物品一律褐金框。
2. 拿到物品飛進背包時，畫該物品自己的圖示，在深底圓金邊裡（若第 5 節第 8 點選 (a)：圓比裝備飛行的小一點，維持現況）。
3. 商店、賣東西、整理腰包、背包滿了、鐵匠特色材料的清單，名字前多一個小圖示。
4. 信件附件的金色小方塊換成物品圖示。
5. 染料六罐同一個罐子，只換顏色。
6. 戰鬥技能列的「道具」欄還是技能圖示，改用物品圖示是之後另開的一項。
