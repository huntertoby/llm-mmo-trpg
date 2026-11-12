# Phase QI-7 報告：⑥ 物品 Q 版小圖示 37 個（第一套物品圖示）

> 實作者（Opus 5.5），2026-11-12～13。需求：`docs/art/Q版小圖示-物品移植需求.md`（使用者 11-12「可以」；第 5 節由開發 PM 定：1、8 選 (a)，2～7 照美術建議）。起點：本機 main `60de8628`（含 `134435d9`）。未 push。`content/` 沒動；`PanelTabs`、`PanelKit`、成長面板、公告板沒動。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| 後端 | `BagItemView`、`ShopItemView`、`LetterItemView` 加選用欄位 `color`（染料，讀 `items.yaml`）、`rare`（材料照 `items.yaml`，其他 `None`）；`world_economy_view.item_rare`；重產 `client/openapi.json`、`schema.d.ts`；新測試 `tests/api/test_item_icon_fields_qi7.py`（3 項） | `c79a3cda` |
| 搬畫法 | 新檔 `client/src/render/qIcon/items.ts`（由 `docs/art/sample/qIconsItems.js` 逐行搬，37 個）；`legacy48.ts` 加 `ART.item`（小回復藥、回魔藥、火瓶、精料）與 `GLASS`、`liquid`；快取 `render/itemIcon.ts`；元件 `ui/ItemIcon.tsx`（`ItemIcon`、`ItemIconPad`、`ItemListIcon`）；新測試 `render/qIcon/qIconItems.test.ts`（17 項） | `bf8e7aaf` |
| 接線 | 背包格／腰包格 42、信件附件 32、飛進背包 28、清單列 24（商店買、賣東西、整理腰包、背包滿了、鐵匠特色材料）；CSS；新測試 `world/qi7ItemIcons.test.ts`（10 項）＋`panelIcons.test.ts` 1 項；改既有 2 檔（第 3 節） | `5c1a1d27` |
| 開發頁、截圖 | `client/dev/item-gallery.html`＋`src/dev/itemGallery.tsx`；`src/dev/itemLegacy.tsx`（舊 GainIcon SVG、名字小牌，只給並排）；`docs/art/shots/qi7/` 9 張 | `7a0a99fe` |
| 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節表、第四節 94～101、第五節表） | 本 commit |

## 2. 逐條對需求

| 需求 | 結果 |
|---|---|
| 1.1 第 1、2 列 背包／腰包 42 | `BagCellView`：`row.gear !== true` 且 `hasItemIcon(row.item, row.color)` 時 `<ItemIcon size={42} frame="bag">`，取代名字小牌；個數 `.world-bag-count` 照現行；表裡沒有的 id 退回名字小牌（截圖 6） |
| 1.1 第 3 列 信件附件 32 | 信上的附件小牌（`.mail-thing-chip`）與寄東西的格子（`Thing`）畫 32；小牌高度實量 32（有圖、沒圖都是 32）：圖示用 `margin: -1px 0 -1px -1px` 蓋住小牌左上下的 1px 框線（截圖 5） |
| 1.1 第 4 列 飛進背包 28 | `GainIconChoice` 加 `{ kind: "item" }`；`gainedItems` 帶 `color`、`rare`；`GainFlyIcon` 畫 `<ItemIcon size={28} frame="fly">`（飛行圓含在畫布裡，不包 `.gain-gear`）；`GainIcon` 的兩個 SVG 換成 `gain_gear`、`gain_item`；有外觀的裝備照 6Q-1 不動（截圖 4、6） |
| 1.1 第 5 列 清單列 24 | 買、賣、整理腰包、背包滿了：`.world-shop-name` 前加 `ItemListIcon`，圖示與名字包在 `.world-shop-thing` 裡（同一個 `Hint`：滑過圖示也出說明）；鐵匠：`label.world-craft-material` 裡 checkbox 和名字之間；通用料的 `<select>` 照舊文字（截圖 7～9） |
| 1.2 不動的 | 背包格、腰包格、信件小牌、清單列樣式、`.item-fly` 的位置與動畫、個數 CSS、技能列「道具」欄、`ItemDetail`、`InventorySummary` 都沒改 |
| 2 清單 37 個 | `QI.list()` 37 個（藥與草 4、投擲瓶 5、補給 1、材料 5＋8＋6、染料 6、通用 2）；`items.yaml` 35 個都有（表裡沒有的＝0，T1） |
| 3.1 沿用 | 補給＝`hud.ts` 的 `ration`；通用裝備＝`parts.entry("skeleton","strike")`；`ART.item` 四款搬進 `legacy48.ts`；稀有度色直接引用 `artPalette.GEAR_RARITY` |
| 3.2 新畫 | 都在 `qIcon/items.ts`；類別底色 `ITEM_CAT_BG`（漸層到 `#1a1612`） |
| 3.3 接法 | `itemIconCanvas(id, px, res, { frame, color, rare })`（快取）、`hasItemIcon`、`ItemIcon` 的 `frame` 呼叫端明寫（飛行 "fly"，其他 "bag"） |
| 4 第 1 點 背包框 | 圓角 16%、類別底色漸層、線寬 max(1.5, 3.5%)、框線 `rimOf`（材料＝common／rare／epic，其他 `#8a6a3a`）；稀有材料一律 epic（T2） |
| 4 第 2 點 飛行圓 | 深底 `#2a2018` r 13/28、金邊 `#e8bb48` 線寬 1.6/28、裁在 12.2/28；霧晶 0.77、熔心晶 0.82（T1、T4） |
| 4 第 3、4 點 外框、尺寸 | 外框照顯示大小（24→1.2、28→1.4、32／42→1.6），24、28 是 `small`；畫布＝顯示 × 2（T4） |
| 4 第 5 點 整數像素 | 圖樣 `blit` 到整數裝置像素；元件掛載後量位置、`position: relative` 挪 `pixelSnapNudge`（只對 "bag"；飛行中不挪）。實量見 4 (c) |
| 4 第 6 點 列高 | 見 4 (c)：31 → 31，沒撐高 |
| 4 第 7 點 染料色 | 從後端 `color` 來（第 5 節第 1 點 (a)）；表裡的六色另有測試和 `items.yaml` 比對（T1） |
| 4 第 8～10 點 | 回魔藥 `fitIn(0.92)`、火瓶 `fitIn(0.9)`、通用劍 `b10(…, 1.2)`；黑曜片、熔心晶、精華照樣張；焦鐵是 `519fea34` 之後的 `IRON_CHAR` 版（指紋全同） |

## 3. 改到的既有測試（舊 → 新）

雜湊／快照：**沒有重產任何雜湊或快照**（`render/__snapshots__/`、各 baseline json 都沒動）。`client/openapi.json`、`schema.d.ts` 依規定重產（加欄位），`tests/api/test_openapi_snapshot.py` 過。

1. `world/panelIcons.test.ts`「名字小牌：個數放在小牌外面（不壓框）」→ 標題改「名字小牌（圖示表裡沒有的物品）：…」，斷言不變（測試用的 id `"p"` 不在圖示表，照舊畫名字小牌）。理由：名字小牌只剩表裡沒有的物品在用。另**新增**一項「QI-7：圖示表裡有的物品畫 42 的 Q 版圖示（背包框、畫布 84），不畫名字小牌；個數照現行」。
2. `world/gainFx.test.ts`「畫法：裝備畫 GearIcon 的 canvas，其他畫通用 SVG」→ 標題改「…其他畫通用圖示（QI-7 起是 Q 版畫布，不是 SVG）」，斷言不變（`GainIcon` 換成畫布後 `not.toContain("<svg")`、`herb` 等於 `GainIcon gear=false` 照樣成立）。其他項程式不變照樣通過。

## 4. (a) 指紋；(c) 清單列的整數像素與列高；結束碼；浮動卡

**(a) 指紋（37 行）**：開發頁 `item-gallery.html?set=<指紋>`（自己的 vite 5317）與樣張 `qicons_shots.py --hash items`（`q-icons-items.html?part=hash`），同一個 FNV、同一個行格式（每個用到的大小 `2 倍／1 倍`，含框；物品 24、28、32、42，通用 28）：
- 和**原樣張**比：**37 行全部相同**。
- 和**材質色換成 `material.ts` 的樣張**（樣張整個複製到暫存區，`qIcons.js` 的 `M` 與 `qIconsWeapons.js` 的 `MAT` 的鋼、鐵、銅換遊戲端色，QI-6 4 (a) 的做法）比：**37 行全部相同**。這批的圖都是字面色（通用劍是部件的亮鋼字面色、補給麵包、`ART.item` 四款也是），換不換都一樣。

開發頁的 37 行（＝樣張）：

```
item_hp_potion_small | 24:0042e6b1/ef2185fc 28:6b724610/7cc93971 32:8e5a4ab2/5a05b19b 42:69a1fade/5e9c6cbe
item_hp_potion_medium | 24:51151c9a/16e27a13 28:83d17e20/8d032912 32:68fca36e/a38d7f63 42:958ee511/2a8c851a
item_mana_potion | 24:16898373/905f06fb 28:c762dfdc/1fce4170 32:37991b64/a738f8a5 42:f19fc339/64b56383
item_antidote_herb | 24:e7126a9a/1022ba93 28:aeac61f9/ba21feb5 32:24263b70/2fd7d159 42:d55bd0dc/ad974d83
item_water_flask | 24:15267544/aea340f1 28:2965842e/10367ed8 32:5a7ea80f/2615d868 42:ae49002c/3d0f348a
item_oil_flask | 24:70cb43e0/f6756d34 28:f9f03c9b/f028208b 32:3978d7cc/6a794ebc 42:fb9f8a3d/5f935229
item_mist_flask | 24:bfa67d65/39ac0626 28:d6b4ddba/0c218cf2 32:286b5795/19f5ef55 42:7ff5a2da/1f6457bd
item_frost_flask | 24:fa66064b/b2d69742 28:f9d59e6f/74d9fb1a 32:39c774ee/1f0aca6d 42:a5db214d/63471102
item_fire_flask | 24:a9d7f30d/33a65fb4 28:27cfd58d/a04fa04d 32:92794f12/3efad839 42:2353a450/4ccd5cee
item_supplies | 24:fce09362/204e957c 28:15fcf030/52497a2f 32:c935d5a4/1836524f 42:a0fd59a7/09bd55f5
item_coarse_material | 24:ac9812d6/c850a027 28:c3ed3a93/8e31809d 32:4df3213b/9a4cab1a 42:7ee1ff47/1339651a
item_fine_material | 24:9e793589/a016225a 28:ae8e1742/4d0cac3c 32:3f94436d/e07b0746 42:849ace75/5ff5d09b
item_superior_material | 24:7e378c97/a4a5f09a 28:edcf60b8/34ec36f0 32:68e4f343/f0e4cfd0 42:905e37bf/b6a36c98
item_essence | 24:876909a9/94007733 28:b920725c/15c4ebd1 32:c0680075/b15f5f71 42:c7165e79/7ab65273
item_scorched_iron | 24:6f6a2a4b/450ebfa6 28:aad4a5ac/66352dd7 32:ec135b2e/0e79ab78 42:c4bf916f/7a97ab8a
item_mist_crystal | 24:aa7ba42f/0684d756 28:4f0736d5/2b70af45 32:5d8686b0/bdf69a1d 42:a341d18c/2d50815c
item_summit_mist_crystal | 24:1c4a165d/bf4f5f0c 28:cda09964/6a633c80 32:de19fc18/1cd092f0 42:25730a49/570c3e2a
item_talisman_ash | 24:e717a0a1/05614975 28:7f81e8ba/0eac6a25 32:4b7d009a/02992d20 42:59c450ed/63955813
item_cinnabar | 24:b9a76164/737d5f5b 28:b250b76f/f91cc25e 32:dc3719cd/7ef98742 42:245b7d1a/fe9b766e
item_wolf_fang | 24:5e1f3b8e/20244065 28:f7eeea70/024752cc 32:c0c743a4/ec4da9ca 42:816c7ac5/5ed41066
item_thunder_feather | 24:d9001d15/9cd070d2 28:6ecd31c9/a7c933d9 32:02e5f008/a9c091ac 42:6c18953f/a6ebab07
item_living_bone | 24:9628d2e1/3ee9cecd 28:e675e83b/800fa5ef 32:7827660d/ba8182da 42:806d7dea/3d1a3d8a
item_green_bamboo | 24:1d0e2cfd/282785f5 28:08251bc3/99e90977 32:ad813cb9/e0ec7f0e 42:2ec4e18d/5556c413
item_lava_core | 24:de5ee3df/667b9c7f 28:80a7a040/e228e67b 32:e4c17817/23683749 42:7c92d91e/f9ae2e5c
item_frost_ember | 24:ac329f4b/87c899c1 28:06f05455/21d5ae9c 32:63a99678/425dfd6e 42:9d9aa6f1/34757c28
item_molten_heart | 24:bba212fe/6a9a3df7 28:9b8717e2/7bfa75c7 32:270e4ab3/c2ce6602 42:da9c6467/8820d108
item_ember_feather | 24:fe1d7a81/6d2b7e95 28:1e0bc711/9c30272d 32:2a588d1f/322853b7 42:3bdeb7d1/4b34fea4
item_sulfur_crystal | 24:d720920d/49a551f8 28:cf6fa92b/5c6875c2 32:b064bc49/916d715e 42:cef7bfef/d12eeaba
item_obsidian_shard | 24:c6bcf2e2/41b63a5e 28:951ac8f9/4755e508 32:9abd47de/0f92c39e 42:4b0c5b1d/134ef705
item_dye_indigo | 24:87bb3c9d/0a00fdd2 28:b30aadf6/7e57165f 32:ae27cdb1/df92dadb 42:58686936/d20ee370
item_dye_cinnabar | 24:43a55c3e/888aa70f 28:1957147d/69bb85a8 32:4734ca6f/00598cd6 42:fba125e4/e156d84f
item_dye_ink | 24:ee586a2f/3399f1ab 28:cffbb506/7cab68ca 32:870ee39a/3803d2c4 42:fff3daf2/9d269ff7
item_dye_jade | 24:e25c1f6e/53b7cc04 28:3c2a6785/a74edfef 32:621dc104/a3f78397 42:b36aa128/92e8545f
item_dye_ochre | 24:0518ec83/3f963b3e 28:2e89936a/a13de0b9 32:afeec168/4856d26f 42:f4c75ccc/fb09793c
item_dye_snow | 24:0efeaa25/342e87bd 28:60086475/9d9ccd9b 32:8061daef/f17014d1 42:68758438/b60f6103
gain_gear | 28:ae130329/6830a7ce
gain_item | 28:d9a222a0/19e0223c
```

**第 10 項：內容裡有、表裡沒有的 id**：開發頁 `?set=missing` ＝ **0 個**（內容 35、表 37 含通用 2）；`qIconItems.test.ts` T1 也鎖住。

**(c) 清單列的 24 與整數像素**：
- 圖示的畫布＝48×48、CSS 24（不縮放）；圖樣在畫布裡 `blit` 到整數裝置像素。
- 版面上的位置：`ItemIcon`（`frame="bag"`）掛載後量 `getBoundingClientRect`，用 `position: relative` 挪 `pixelSnapNudge`（`GearIcon` 的做法），視窗改大小時重量。
- 實機商店（買 8 列＋賣 11 列）量 17 張物品圖示畫布的左上角 × DPR：1600×900（DPR 1）、1600×900（DPR 2）、800×600 三種都是 **0 張落在小數裝置像素**。
- **列高前後**：同一頁把圖示與空位 `display: none` 前後各量一次，19 列都是 **31 px → 31 px**（列高由「買」「賣」鈕決定，24 的圖示沒撐高）。

**結束碼**（交件前各跑一次）：`corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test --run` **0**（323 檔、4199 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告）。後端：`uv run ruff check .` 0、`uv run ruff format --check .` 0、`uv run mypy` 0（1523 檔）、`uv run lint-imports` 0（14 kept）；`pytest -n 6 tests/api/test_world_economy_api.py tests/api/test_world_mail_api.py tests/api/test_client_fixtures.py tests/api/test_item_icon_fields_qi7.py tests/api/test_openapi_snapshot.py` 21 passed。開發中相關 vitest：`src/world src/ui/floatCardRule.test.ts src/render/qIcon src/test` 等。沒跑 `scripts/check.py`。

**浮動卡（6.5.1）**：自己的 `trpg serve`（8157，存檔在暫存區）、無頭 Chrome（CDP 9617，`--mute-audio`，網址 `?mute=1`），實機商店「解毒草」那列的 **24 圖示**當觸發元素（順便確認滑過圖示也出說明），1600×900 與 800×600 各一次：100 ms 時 0 張、550 ms 開 1 張 → 沿直線 8 步滑進卡片仍開著 → 卡內滾輪捲動：內容一次放得下（可捲量 0）→ 點一下釘住（`.float-card.pinned` 1 張）→ 滑鼠移開仍在 → Esc 關閉（0 張）。兩尺寸都過。

**實機資料**：開發建角 `POST /api/world/characters`（`weapon`、`keywords: ["ignite","wet"]`），首頁「繼續」→「站起來」。背包、商店、鐵匠、背包滿了用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch`，把 `/api/world/characters/<id>`（與 `/actions`）回應的 `inventory`、`shop`、`crafting`、`pending_loot` 換成假資料（含後端新欄位 `color`、`rare`；程式與後端不動，QI-6／PNL-1a 的做法）。商店與鐵匠從右上地點名（`[data-hud=place]`）的「商店」「鐵匠」開。飛進背包：模擬 `prefers-reduced-motion: reduce`，在 `window.__qiExtra` 補三件新東西後按一次方向鍵讓下一次畫面多出它們，`.item-fly.still` 停在背包鈕上 600 ms；三個疊在同一點，截圖前把第 i 個往左挪 i×44px 並排（只動測試頁的位置）。

## 5. 截圖（`docs/art/shots/qi7/`，9 張；PNG 只有真 1 倍／最近鄰對照表，其他 jpg 80；單張 ≤ 291 KB）

| 檔 | 對到需求第 7 節 | 內容 |
|---|---|---|
| `docs/art/shots/qi7/1-dev-potion-throw-supply-24-42-true1x-dpr2.png` | 1 | 開發頁（DPR 1 拍）：藥與草 4、投擲瓶 5、補給 1；每格「現行（名字小牌）｜24 真 1 倍｜24 DPR 2（×3）｜現行｜42 真 1 倍（×2）」 |
| `docs/art/shots/qi7/2-dev-materials-24-42-true1x-dpr2.png` | 2 | 材料 19（框線灰／藍／紫；稀有四個紫框）同上排法 |
| `docs/art/shots/qi7/3-dev-dye-24-true1x-dpr2.png` | 3 | 染料 6：現行｜24 真 1 倍｜24 DPR 2（×4） |
| `docs/art/shots/qi7/4-dev-fly28-37-true1x-dpr2.png` | 4 | 飛行圓 37 個：現行（GainIcon 布袋／劍）｜28 真 1 倍｜28 DPR 2（×3） |
| `docs/art/shots/qi7/5-dev-mail-32-true1x.jpg` | 5 | **開發頁**（正式 `MailPanel`＋假信）：信件附件 32、表裡沒有的物品照舊金色小方塊；下方 32 小牌真 1 倍最近鄰 ×3 |
| `docs/art/shots/qi7/6-world-1600-bag-fly.jpg` | 6、7 | 實機 1600×900：背包 6×5＋腰包（物品 42 與裝備 42 混排、個數照現行）；左下格子裁切 ×2；右下飛進背包停格裁切 ×3（有外觀的裝備 32｜沒外觀的裝備 28｜物品 28，物品比裝備小一圈＝第 8 點 (a) 的預期） |
| `docs/art/shots/qi7/7-world-1600-shop.jpg` | 8 | 實機 1600×900：商店買（8 列）、賣東西（含一列裝備：24 空位對齊）；左邊兩塊真 1 倍裁切 ×3 |
| `docs/art/shots/qi7/8-world-800-shop.jpg` | 8 | 實機 800×600：商店捲到「賣東西」，買的後半＋賣的裝備列與物品列 |
| `docs/art/shots/qi7/9-world-1600-loot-pouch-smithy.jpg` | 9 | 實機 1600×900：背包滿了選丟哪件（物品與裝備混排、裝備列空位對齊）；左：整理腰包裁切 ×2；右下：鐵匠特色材料（圖示在 checkbox 和名字之間）裁切 ×2 |

**實機未看**：信件附件（第 5 張用開發頁畫正式元件；樞島沒有郵差，假信要另包 `/mail` 的回應，這段沒做）；實機 DPR 2 的截圖（DPR 2 只量了位置與列高，見 4 (c)；開發頁的 DPR 2 欄代替）；飛行中（沒停下來）的樣子。

## 6. 第 5 節的處理、死碼、和樣張不同的地方

- **第 1 點 (a)**：物品 view 加 `color`（染料，`items.yaml` 原樣）；`ItemIcon` 收 `color`，有給就 `dyeArt(color)`；表裡沒有的 id 只要有 `color` 也當染料畫；沒顏色的未知 id → 背包格名字小牌、清單列空位、飛行 `gain_item`。
- **第 2 點**：物品 view 加 `rare`（材料 `True`／`False`，其他 `None`）；`tierOf`：後端 `rare === true` 一律 3（epic）；否則照表的 tier；表裡沒有 tier 的材料：rare（後端沒給用表的）→ 3、其他 → 1。表的稀有四個和 `items.yaml` 一致（前端 T1、後端測試各鎖一次）。
- **第 3 點**：裝備列（背包滿了、賣東西）放 `ItemIconPad`（24×24 空位），不畫裝備圖。
- **第 4 點**：表外 id 退回現行（同第 1 點）；開發頁 `?set=missing` 列出（0）。
- **第 5 點**：`qIcon/items.ts`、`legacy48.ts` 的 `ART.item`、`ui/ItemIcon.tsx`。
- **第 6 點 死碼**：**刪了** `GainEffects.tsx` 的兩個 GainIcon SVG（換成 `gain_gear`／`gain_item` 畫布；舊 SVG 另存 `src/dev/itemLegacy.tsx` 只給開發頁並排）。**留下**（仍有呼叫處）：`.world-bag-tile*` CSS、`tileLines`／`TILE_LINE_CHARS`（表裡沒有的 id 還在用）、`.mail-thing-mark`（表裡沒有的物品、沒有裝備卡的裝備附件還在用）。
- **第 7 點**：開發頁 `client/dev/item-gallery.html`：`?set=a｜fly｜list｜scene｜missing｜<指紋>`、`&res=`、`&zoom=`、`&grp=`、`&px=`，另加 `&bigres=`、`&bigzoom=`（32 以上的大小另給解析度與倍數，截圖第 1、2 張用）、`&label=0`。
- **第 8 點 (a)**：飛行圓維持 GainIcon 的 28（直徑 26、金邊壓在圓上）；`GainEffects.tsx`、`qIcon/items.ts` 檔頭、`ui/ItemIcon.tsx`、`uiMotion.css` 都寫明和裝備的 32 不同。
- **和樣張不同**（都不改畫法）：依賴改 import；類別底色寫成 `ITEM_CAT_BG`（樣張讀 `itemIcons.js`）；`QW.RARITY` → `GEAR_RARITY`；`canvas(id, px, res, opt)`（樣張 `(id, px, zoom, opt)`）；`opt` 多 `color`、`rare`；沒搬 `kind`、`topic`、`CAT_ZH`、`countText`、`glyph` 的 `noPre`；表的 `zh`、`grp`、`src` 留給開發頁與測試。`liquid` 只留 `legacy48.ts` 一份（樣張 `qIconsItems.js` 另有一份同畫法的）。

## 7. 待 PM 決定

1. **信件附件只在開發頁看過**（實機未看）：要實機截圖得在郵差所在城鎮、包 `/mail` 回應放假信；美術驗收若要求再補。
2. **信件小牌的圖示蓋住小牌左上下 1px 框線**（`margin: -1px 0 -1px -1px`），用來維持小牌高 32；另一個做法是小牌撐到 34。照最保守（高度不變）先做，請美術看截圖 5。
3. **鐵匠特色材料的 `label` 改成 `inline-flex`**（圖示和 checkbox、名字垂直置中、間距 4px）：原本是行內文字，換行位置可能和以前略有不同；只在鐵匠打造分頁。
4. **鐵匠的材料 view（`CraftMaterialView`）沒加 `rare`**：需求只點名物品 view；特色材料的框線照前端表（現有 19 個材料都有 tier，和 content 一致）。新材料若不在表裡，清單列只留空位。
5. **`dev/itemLegacy.tsx`（舊 GainIcon SVG、名字小牌）**：只為開發頁「現行｜Q」並排，美術驗收後可刪。
6. **截圖第 6 張的飛行停格是把三個 `.still` 往左挪開並排**（減少動態時三個會疊在背包鈕上同一點）：只動測試頁的位置，程式不變。
7. **`ItemIcon` 的整數像素挪移只在掛載與視窗改大小時量**：面板內捲動不會改變小數位置（捲動量是整數），但若之後有 CSS transform 縮放的容器放清單列，要再量。

## 開發 PM 裁定

（待填）
