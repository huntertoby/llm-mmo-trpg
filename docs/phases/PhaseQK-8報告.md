# Phase QK-8 報告：人形敵人與 NPC 部件、qDoll 新形制、NPC 外觀資料（#145）

> 實作者：worktree `dev/qk8`（從 main `ddd6d8a9` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md` 第 0 節＋8.5 節；真相來源 `docs/art/sample/qNpc.js`、`q-npcs.html`、`qDoll.js` 11-07 新形制（`ba9f8f81`、`4bef4a2a`）；`docs/design/18-雲嶺內容.md` 18.5.1（#145）。樣張照點列改寫進 client，**沒有 import 樣張程式**。content 改動前和玩法 PM 對過清單（全部確認，另補 3 點，見第 3 節）。

## 0. 樣張 → client 檔案對照

| 樣張 | client | 說明 |
|---|---|---|
| `qDoll.js` 的 `body.kind: bare`、`EDGEK` | `qGear.ts`（`bareBody`）、`qDoll.ts`（`EDGEK`） | 赤膊：膚色軀幹、腰上收窄、腋下陰影、胸線、背面脊線；手臂內線／拳頭圈／側面描邊用膚色加深 0.23、線寬 0.9 |
| `neck.kind: fur_collar／feathers`（`neckWide`） | `qGear.ts` `neckItem` | 畫在身體上、手臂與胸前武器下面 |
| QW `whisk／talisman／puppet_strings`、`heldFingers` | `qNpcHeld.ts`（新）＋`qWeapons.ts` 的 QW 展開、`puppet_cross` 別名 | 照持武器規則、四指橫過握柄 |
| `HELD_OFF`、`offHeld`（副手法球、拂塵…） | `qDoll.ts`（`sidePlan`、`drawBackPost`、`drawFrontOff`） | 副手法球不再畫成書；法球沒指定顏色時照元素色（保留原本副手法球的元素色） |
| `qNpc.js` 的 `prep`、`PART`（B／C／D 層） | `qNpc.ts`（新） | 長進 qDoll 的圖層：B 層在 `drawBody` 開頭、C 層在最後（同一張離屏，qStamp 一起描外框，新部件不多一圈內框）；D 層（白紗、傀儡線）畫到 qStamp 新開的「外框之上」離屏，朝西遠側手的傀儡線到「外框之下」離屏；劍穗、傀儡線借 `POSE.probe` 記下武器變換 |
| `q-npcs.html` 版面 | `client/qk8-gallery.html`＋`src/dev/qk8Gallery.ts`（新） | 外觀全部照 content（單位 doll＋weapon、區域外觀、NPC 頭像經 `npcLook` 換算），同樣張比例 |
| 盜賊三套 `BANDITS.cliff／ash` | `content/ui/region_dolls.yaml`（新）＋`src/trpg/content/region_dolls.py`＋`client/src/render/qNpcRegion.ts`＋`battle/drawModel.ts` | 戰場在該區時換外觀；武器、詞綴、特徵、大小照範本 |

**圍裙統一一種寫法**：資料一律 `waist: {kind: apron, color, trim(=亮一階的邊), material}`（皮圍裙 `material: leather` 不畫口袋）；範本舊寫法 `body.apron`（煉丹師、青霧執事）在 `npcPrep` 換成同一個部件。畫法照 `qNpc.js`；QK-3 的圍裙畫法（`qGearForms` 的 free／top 層）拿掉，兩種畫法沒有並存。

## 1. 完成表

| # | 項目 | commit |
|---|---|---|
| 1 | qDoll 新形制：赤膊、毛領、白羽披肩、拂塵／符紙／傀儡線、副手法球 | `e4637adf` |
| 2 | 人形敵人新部件四面分畫：圍裙、背葫蘆、木偶箱、郵袋、黃符、白紗面罩、斗笠 douli、頭帶、護目鏡（戴在眼睛上）、額上護目鏡、劍穗、傀儡線 | `e4637adf` |
| 3 | QK-3 待決 6：頸飾（墜飾／吊牌、護符／符牌、骨符）接上紙娃娃（`dollGear` 的 `neck`、`resolveDoll` 裝備格加 `neck`、`KNOWN_KINDS.neck`） | `f39518a8` |
| 4 | schema、content、盜賊三套、NPC 換算 | `f68c064f`、`5cf46a56` |
| 5 | 霧鎖真人統一頭目版（NPC 全身、頭像、頭目戰資料同一個樣子） | `f68c064f` |
| 6 | QK-3 第 1 條（見第 5 節） | `d08ffd22` |
| 7 | 畫廊、62 組並排、實機截圖 | `c29703e6`、`d1be0938` |

### NPC 地圖紙娃娃換算（`client/src/world/npcLook.ts`）
- 頭像配件照順序換算（同樣張 `prep`）：`wide_hat` → `douli`、`headband` → 頭帶（不再借頭巾）、`goggles`／`goggles_up` 沒戴帽時是頭部部件、戴帽時改成帽子的 `form`（老鐵帽＋護目鏡、架在帽沿上的額上護目鏡）、`fur_collar` → 頸飾、`cap` 深色 `#3a2a1a`（同樣張）。
- 頭像 `gear.main_hand` → 主手造型覆寫（`main_kind／material／color`，元素用 `main_element`）；`mist` 配件 → 全身特徵 `traits: [mist]`（霧鎖真人地圖上照頭目一樣繞霧）。頭像本身照舊不畫主手（`portrait.ts` 沒動）。

## 2. 改了哪些 content（只動外觀欄位，不動數值、技能、規則）

- **schema**：`NpcPortraitGear` 加 `element`（選填）；NPC 頭像 gear 的格子加 `main_hand`（`NpcPortraitSlot`）。新 `RegionDollTable`（`content/ui/region_dolls.yaml`，登記在 `KNOWN_CONTENT_FILES`；禁止寫 `main_kind`、`creature`）。`client/openapi.json`、`schema.d.ts` 重產。
- `content/world/npcs/cloud_ridge.yaml`：青崖道長拂塵、阿岳弓、霧鎖真人右手長劍＋左手拂塵（原副手長劍）、疤面刀、石師傅皮圍裙＋鎚。
- `content/world/npcs/ashen_waste.yaml`：灰鬚杖、爐叔皮圍裙＋鎚（赤膊照舊）、赫琳火杖、鍛疤鎚。
- 主城 figure：工坊師傅、樞島鐵匠皮圍裙；酒館老闆白圍裙（`#f4efe2`／邊 `#a89c80`）。舊註解「紙娃娃沒有圍裙部件」改掉。**沒有新增 figure**（玩法 PM 補充 2）。
- `content/world/trade.yaml`：三位郵差 `extras` 加 `post_badge`、`gear.back: {kind: mailbag}`。
- `content/units/sect_mist_lock_master.yaml`：`doll` 拿掉 `main_kind: whisk`、`off_hand` 改拂塵（主手照 weapon＝一手劍＝長劍）。
- `content/units/bandit_captain.yaml`：原版隊長加紅披風（樣張）。
- `content/ui/region_dolls.yaml`（新）：雲嶺斷崖幫（草編斗笠、麻布外套、布鞋；隊長頭目深色斗笠＋朱紅披風）、灰燼荒原荒原盜賊（鏽鐵、破布兜帽／頭巾；隊長橘頭巾、頭目鏽鐵全身甲＋橘披風）。範本：bandit／rookie／guard、archer／guard／rookie（荒原另加 `ashen_gunner`）、shieldbearer／guard、captain、boss；精英詞綴的範本 ID（`<範本>_<詞綴>`）照原範本那一列。
- #145 已改好的（小蓮、疤面 douli、柳掌櫃與鐵娘錢袋、老鐵背包）沒動；錢袋 `pouch`、背包 `backpack` 原本被 `KNOWN_KINDS` 擋掉、地圖上畫不出來，這段放行。
- 夾具：`client/src/render/fixtures/unitDolls.json` 重產（`scripts/export_client_fixtures.py`）；`client/src/dev/fixtures/encounterBoss.json` 霧鎖真人同步。

## 3. 和玩法 PM 對清單

清單 SendMessage 給玩法 PM，回覆（經專案 PM 轉達）：全部確認；補充 ① 霧鎖真人右劍左拂塵、unit doll 改法可以、weapon 不動；② 錢袋、背包已在 `5730190a`，不要新增 figure；③ region_dolls 照做，只換頭身腳披風手，武器照範本 weapon，樣張武器差異寫進待決。

## 4. 截圖（`docs/art/shots/qk8/`）

- 並排 62 組（左樣張、右遊戲，正・東・西・背，2 倍）：`docs/art/shots/qk8/compare/01_monk_sect_acolyte.jpg` … `11_monk_sect_mist_lock_master.jpg`（修士 11）、`12_bandit_base_*` … `26_bandit_ash_*`（盜賊三套 15）、`27_npc_merc_qingfeng.jpg` … `62_npc_overseer_scar.jpg`（NPC 36）。共 3.7 MB。
- 實機（`?mute=1`）：`docs/art/shots/qk8/qk8_town_1600.jpg`、`docs/art/shots/qk8/qk8_town_800.jpg`（主城：守印人、守池人、郵差白鷺帶郵袋）；`docs/art/shots/qk8/qk8_battle_cliff_bandits_1600.jpg`＋`_zoom.jpg`（雲嶺斷崖幫寨：斗笠盜賊、深色斗笠精英隊長「疤面」）；`docs/art/shots/qk8/qk8_battle_sect_1600.jpg`＋`_zoom.jpg`（劍冢：劍陣弟子劍穗、霧行者白紗）。戰鬥用開發頭目戰入口（`TRPG_DEV_ROUTES=1`、region＝cloud_ridge）。
- QK-3 第 1 條補拍：`docs/art/shots/qk3/compare_v2/hero_gloves_long.jpg`、`hero_bracer_ring.jpg`（＋`_x3` 3 倍）。

## 5. QK-3 第 1 條（美術 PM 驗收，優先）

`hero_gloves_long`、`hero_bracer_ring` 朝西拿盾那隻手：手部件本來就在 `arm()` 裡、袖子之後畫，但側面持盾手是彎肘（前臂橫向伸到盾心），前臂大半被盾擋住，長手套護套與臂環落在盾邊和肘之間很窄的一段，袖口緊貼上臂下緣，看起來像被鱗甲袖子蓋住。改法：**側面持盾、彎肘的那隻手**（`sideArm` 的 `shield`），長手套往肘那頭多包 2.2、外翻袖口與兩圈臂環一起往肘移 2.2，袖口壓在上臂袖子上面露出來；武器、盾、披風照舊在最上層；其他姿勢一像素不變（快照沒變）。

## 6. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 254 檔、3178 項全過（`qSelfTest`、`inkWeaponFrame` 照跑沒改） |
| 快照重產 | `client/src/render/__snapshots__/inkDollSnapshot.test.ts.snap`：只有新部件相關的鍵變（範本 `bandit_captain`〔紅披風〕、修士 9 種；各欄位 `back:gourd／puppet_box`、`body:bare`、`head:veil`、`waist:talismans`、`main:whisk／talisman／puppet_cross`、`off:orb・ball・ice／floating`；新增 `back:backpack／mailbag`、`head:douli／goggles／goggles_up／headband`、`neck:charm／feathers／fur_collar／pendant`、`waist:apron／pouch`） |
| 改寫的測試 | `dollGear.test.ts`（頸飾改成畫）、`inkSect.test.ts`（霧鎖真人主手劍、副手拂塵）、`storyDialog.test.ts`（配件換算的新對照）、`capitalFigures.test.ts`（圍裙算現有部件）、`tests/content/test_enemy_looks.py`（霧鎖真人副手拂塵） |
| 新測試 | `client/src/render/qNpc.test.ts`（prep 換算、四方向畫得出來、赤膊膚色、斗笠、副手不是書、頸飾、區域外觀含精英後綴）、`tests/content/test_region_dolls.py`（schema、範本存在、身分道具） |
| `tsc --noEmit`、`vite build` | 過 |
| 排版煙霧 1600×900、1040×624、800×600 | 三個都 13 PASS、0 FAIL |
| Python | `ruff check`、`ruff format --check`（src、tests、scripts）、`mypy`、`lint-imports`（14 kept）、`pytest -q tests/content tests/world tests/api -n 4`：全過；`trpg content check` 過 |
| openapi | 重產 `client/openapi.json`、`schema.d.ts`（`NpcPortraitGear.element`、gear 格加 `main_hand`） |
| CLI 快照 | 沒有變 |

## 7. 待 PM 決定

1. **NPC 頭像接線（QK-6 合併後補）**：`qPortrait.ts` 沒動。頭像裡的斗笠（疤面 `gear.head douli`）、郵袋（`gear.back mailbag`）、圍裙會經 `drawQ` 自動畫出來；`qPortraitPrep` 仍只認 extras 的 `mailbag`，若之後也在 extras 寫 `mailbag` 會畫兩次（這段 content 只寫在 gear，沒寫 extras）。頭像的 `fur_collar` 仍走頭像自己的 C 層（QK-2 待決 5），可改走 `neck: fur_collar`。
2. **霧鎖真人頭目戰**：只改了資料（unit doll 副手拂塵、主手照 weapon 長劍），人形頭目照舊走 qDoll，不需要動 QK-4 的頭目繪製檔；頭目外光、霧氣照舊。
3. **樣張武器 ≠ 規則武器（玩法 PM：寫進待決）**：盜賊三套的武器照範本 weapon（盜賊匕首、弓手弓、盾衛單手劍＋鳶盾、隊長單手劍、頭目雙手劍）；樣張是盾衛斧＋圓盾、頭目斧、斷崖幫隊長刀／頭目雙手劍、荒原盜賊火斧、槍手手槍、盾衛錘、隊長霰彈槍。原版盾衛的頭盔＋鎖甲照範本（樣張是紅頭巾＋皮甲）。護法武僧 weapon 是 `fist`，Q 版畫成拳套（樣張空手）。
4. **八字鬍**：柳掌櫃、酒館老闆的 `mustache` 是頭像配件；地圖紙娃娃的 `Look` 還沒有鬍子樣式欄位（`beardStyle`，QK-6 外觀選項），這段沒畫。
5. **樣張與遊戲顏色差**：道童杖頭光照 content `main_glow`（綠），樣張是自然元素色；裝備色走遊戲的材質色表（`itemColors`），和樣張色略有差（同 QK-2）。
6. **`qWeapons.ts`、`qStamp.ts`、`qSpec.ts`、`appearance.ts`、`npcLook.ts`、`drawModel.ts` 不在原本的檔案清單**，但為了接線必須改（QW 展開手持物、外框之外的兩張離屏、赤膊不再換成上衣、`KNOWN_KINDS`／頸飾格／`main_element`、NPC 換算、區域外觀）。改動都很小；`appearance.ts` 只動 `KNOWN_KINDS`、`fromDollLook` 一行、裝備格清單，QK-6 若改 `withLookChoice` 不會衝突。
7. **霧行者 `head: veil`**：Q 版一律畫成白兜帽＋白紗面罩（樣張霧行者）；遊戲裡沒有其他人戴 `veil`。
8. **副手法球**：照樣張改走武器表的法球（不是書），沒指定顏色時用元素色（樣張忽略元素，這裡保留原本副手法球的元素色）。
9. **劍穗朝西**：在身體後面（用 `destination-over` 畫在本體之後，仍描外框，同樣張 B 層）。
