# Phase 5A-ART 完成報告：敵人外觀移植（ART1～ART4）

規格：`docs/phases/Phase5計畫.md` 第 42 節（合併 main 後由第 41 節順延；main 的 5F-5c 佔了 41）。需求：`docs/art/敵人外觀.md`（含第 3 節「第 4 段補充」）、`docs/art/sample/enemyArt.js`／`enemies.html`／`storyDoll.js`、`docs/art/shots/misc/enemies.png`。美術 PM 的代決還沒經使用者確認，這次照代決先做；之後改名或改配色只要動資料。**引擎一行都沒改。**

## 交付

| 段 | 內容 | 主要檔案 |
|---|---|---|
| 規格 | 42 節（含決策影響盤點） | `docs/phases/Phase5計畫.md` |
| ART1 異形畫法 | 移植 14 種身形（`flyer` 有 bird／bat、`crawler` 有 beetle／spider）、6 種材質（裂縫、切面、刻符、木紋、背上小物）、全部特徵（含 `crust`）、5 種大小（新增 `tiny` 0.62）。<br>畫布 96×96，腳底在下方 12px。朝西鏡像；南北朝向沿用側面，敵方朝西、我方朝東。頭目（huge）在戰場上再 ×0.9。<br>`status_traits`：單位有該狀態時，特徵才會解進貼圖鍵。灰燼之心有熔殼時畫殼，熔殼移除後殼就不見。<br>召喚物的 `doll_look.creature` 優先於 `summon_look`。熔核點：lizard 在腹部 (2,-7.4)，wisp 在 (0,-20) | `client/src/render/inkCreature.ts`、`artTextures.ts`、`unitSprite.ts` |
| ART2 精英與頭目記號 | `elite` 標籤或頭目 `rarity`：陣營環外加墨線＋金環 `#ffbf3a`，環前方一顆金菱形。<br>精英 ×1.15，頭目不放大。頭目有外光，做法同 `renderFigureCanvas`。<br>詞綴特效：異形畫在貼圖裡；人形另疊兩張貼圖，霧氣繞身在身體後面，其餘在身上。`mirror` 畫錯開的分身；`mist_hidden` 本體 75% 不透明。<br>`linked`：`BattleRenderer` 在相鄰（曼哈頓距離 1）的同陣營單位之間畫青色虛線。<br>前端同時認得內容的詞綴 ID 和美術 id | `inkCreature.ts`、`linkLines.ts`、`unitSprite.ts`、`BattleRenderer.ts`、`drawModel.ts`（`elite`） |
| ART3 修士部件 | 髮髻、赤膊（手臂也是膚色）、念珠、圍裙、藥葫蘆／木偶箱、腰掛黃符、白紗面罩（遮頭頂與頭髮）、白羽披肩、劍穗、拂塵／符紙／傀儡線。<br>副手格加認 `sword`／`dagger`，只有範本外觀會用到。不認得的 kind 不畫 | `client/src/render/inkSect.ts`、`inkDoll.ts`、`inkGear.ts`、`inkRace.ts`、`appearance.ts` |
| 資料格式 | `DollLook` 新增 `creature`（`CreatureLook`）、`affixes`、`traits`、`main_kind`、`main_tassel`、`bun_band`、`beard`、`build`；`hair` 加 `bun`；`gear` 加 `neck`／`back`／`waist` 三格；`DollGear` 加 `form`／`trim`／`apron`；`skin` 改成選填。<br>`EliteAffixDef.look`、`EnemyVariantDef.doll`、`summon_looks.yaml` 的 `creature` 都是新的（召喚物載入時寫進範本的 `doll.creature`）。<br>`CreatureLook` 只檢查格式，不檢查值認不認得 | `src/trpg/content/battle.py`、`world_enemies.py`、`summons.py`、`library.py`；OpenAPI／`schema.d.ts` 已重產 |
| ART4 內容資料 | 照第 3 節的單位 ID 對照表與第 2 節寫入：荒原 13 隻（含殼縫餘燼蜥，和餘燼蜥同款）、碎晶之主（傳說外光）、三根源晶柱、晶傀儡、熔晶魅、雲嶺野獸 4 種、霧魅、碎晶傀儡、兩個陣眼石靈、修士 12 種（霧鎖真人有傳說外光）。<br>另外：5 個變體的 `doll`、6 個詞綴的 `look`、餘燼幼蜥的 `creature` | `content/units/*.yaml`、`content/world/enemies.yaml`、`content/summon_looks.yaml` |
| 測試 | Python：對照表逐隻、schema、詞綴外觀、變體覆寫、召喚物 creature。<br>vitest：每種身形 × 材質 × 大小、全組合自測 1000 組以上都不丟錯、熔殼出現與消失、精英／頭目、詞綴、連線、南北朝向、召喚物優先、修士 13 個部件與資料對照 | `tests/content/test_enemy_looks.py`、`client/src/render/inkCreature.test.ts`、`inkSect.test.ts` |

## 檢查

| 項目 | 結果 |
|---|---|
| ruff check、ruff format --check、mypy（1219 檔）、lint-imports（13 契約） | 全過 |
| pytest `tests/content tests/api tests/narrative`（-n 8） | 2990 通過、1 失敗：`test_skill_icon.py::test_client_fixture_is_current`。合併 main（5F-5c 的 `enemy_only` 讓隨機技能變了）後 `skill_icons.json` 過期，已重產；該檔 16 項重跑全過 |
| vitest | 143 檔、1333 項全過 |
| `pnpm build` | 通過 |
| swamp 種子 7 重播 | 通過（88 動作、313 事件） |

## 瀏覽器驗證

- 用 8260 埠。伺服器是我自己啟動的；用的是 scratchpad 裡的內容副本，只把幾張單場地圖的敵人換成要看的陣容，repo 沒動。
- 開自己的分頁 tab-19，驗完已關分頁、停伺服器，視窗大小也還原了。
- 每次開局前都先 `localStorage.clear()`。

| 場景 | 看到的 |
|---|---|
| 雲嶺一般遭遇（煉丹師、護法武僧、傀儡師、霧行者） | 竹青袍、髮髻、拂塵、背葫蘆；赤膊、銅膚、光頭、矮壯；墨灰袍加木偶箱與傀儡線；半透明白紗兜帽加面罩 |
| 雲嶺野獸（霧狼、山豹、石背熊、雷羽鷹） | 都畫得出來，雷羽鷹浮空、腳下有影子 |
| 荒原遭遇（熔爐母獸、熔岩甲蟲、熔核蛞蝓、硫煙獸） | 熔岩裂縫亮橘，在焦土上看得到；母獸背上有卵囊；召喚出的餘燼幼蜥是 tiny 的熔岩蜥蜴，和母獸同一系 |
| 灰燼之心 | 第 1 階段：甲蟲殼片圍住晶核，有金色外光、金環、金菱形。<br>打一下進第 2 階段（副本把門檻改成 99%）後，殼消失、露出晶核，同時爬出殼縫餘燼蜥 |
| 碎晶之主 | 紫色源晶傀儡，有傳說金光加金環，朝西；源晶柱的元素色分得出來 |
| 霧鎖真人 | 白髮白鬚、月白袍、拂塵、青披風、金光加金環。<br>青霧執事（精英）：金環、×1.15、四個綠十字、金葫蘆 |
| `__layoutSmoke.scan()` | 800×600 與 1600×900，每個場景都回 `[]` |

**和樣張 `enemies.png` 的差異**：

1. 腳邊狀態列的圖示（例如「熔核爆裂」）、代號圓與 HP 條會蓋住矮的異形。蜥蜴、蛞蝓、餘燼幼蜥最明顯：母獸腹部的熔核被狀態圖示蓋住，幼蜥大半被代號和徽章擋住。樣張沒有這些 UI。
2. 護法武僧手上有拳套（武器 `fist` 的外觀），樣張是空手。
3. 精英／頭目的環維持一格大，沒有照樣張依大小放大。
4. 頭目在戰場上再縮 0.9。
5. 1600×900 時內建瀏覽器會把畫面縮小，細節以 800×600 放大檢查為準。

## 待 PM 決定

1. **異形資料放在 `doll.creature`**：`敵人外觀.md` 寫的是範本頂層的 `creature`。為了不改引擎，改放在既有的 `doll` 底下，經 `UnitView.doll_look` 帶到前端。`doll.skin` 因此改成選填。
2. **`LOG_FORMAT` 沒有升**：`DollLook` 在戰鬥狀態裡，但新欄位都是有預設值的純顯示資料。照 `戰鬥紀錄格式變更.md` 1.2，舊紀錄會因規則包雜湊不符被拒絕（現行策略），新錄的紀錄照常重播。
3. **矮小異形被腳邊 UI 蓋住**（差異 1）：要不要讓矮的身形把狀態列移到別處，或把異形往上抬，需要美術 PM 決定。
4. **環不隨大小放大**（差異 3），**頭目在戰場上 ×0.9**（差異 4）：都是保守做法。
5. **南北朝向的異形**：敵方畫成朝西、我方朝東（我代決）。
6. **沒有寫的**：
   - 盜賊三套區域配色：同一批範本在三個地方共用，要做得先有區域範本或依區域換色的機制。
   - 傀儡師的木傀儡：它召喚的是玩家也會用的 `bomb_puppet`，我沒改。
   - 道童的杖頭綠光、小一號（0.9）。
   - 角魔狂信者：沿用武僧的赤膊外觀。
7. **對照表以外的代決**：
   - 灰燼犬 `ash_hound`：對照表寫「目前沒有單位」，但實際已有，照第 2 節寫成 `hound`＋`magma`。
   - 霧中劍客：月白袍加青邊。
   - 焦石背熊：石背熊換成火元素。
   - 青霧執事：照樣張畫「再生的」，它本身帶同款技能。
8. **`skill_icons.json`**：main 合併後過期，我已重產並 commit（1 行）。
9. **Phase5計畫節號**：合併 main 後 5A-ART 改成第 42 節，「之後各段規格」改成 43 節。
