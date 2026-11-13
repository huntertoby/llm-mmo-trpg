# Phase RG-5 完成報告（#163 玩家大盾的外觀＋追加批次）

依據：`docs/art/RG樣張.md` 第 10 節（10.8 決定與 P-1～P-4）、`RG樣張-審查.md` 末節；`docs/玩法PM交接.md` 4.1.5（形制名與掉落）、4.1.6（盾陣改名、高度、連擊點單位）；`docs/art/RG-4驗收.md` 末節「美術 PM 裁定」（K1、K3、待決 9、KW-3 待決 3、遇敵卡「開戰」）；`docs/phases/PhaseRG-4報告.md` 與開發 PM 裁定。

## 1. 做了什麼

### 1.1 兩種大盾開放給玩家（第 1 件）
- `content/equipment/appearance.yaml`：`sect_great` 拿掉 `enemy_only`，名稱改「雲紋碑盾」；新增 `molten_shell`「熔殼塔盾」。兩者都帶 `offhands: [tower_shield]`。
- P-3：`FormDef.offhands`（新欄位，沒寫不輸出）限定形制只配那些副手的物品。`item_appearance_problems` 擋不配的物品（例如圓盾物品寫 `sect_great`），載入時檢查 `offhands` 的 ID 都在 `offhands.yaml`。`gearAppearance.json` 重產；只有這兩款會輸出 `offhands`。
- `FormDef.enemy_only` 保留（目前沒有形制用它），玩家拿得到形制的地方照舊略過它。
- 物品產生器：副手的形制本來就照底材物品（塔盾＝`tower`），不從造型裡抽，所以一般掉落、打造的外觀不變。

### 1.2 熔殼立殼改成手持塔盾、Q 版圖示、材質換色（第 2、3 件，前端子 agent）
- 握法：`qCore.isTowerLike` 加 `molten_shell`。
- 碑盾（`qSectShield.ts`）：帶 `trim` 的物品（敵人）照原樣畫。沒有 `trim` 的物品（玩家）照材質補色。P-1：盾邊用材質本色（混關鍵字之前）的亮度判斷。圓章圈、銅釘例外照 10.4。
- 熔殼（新檔 `qMoltenShell.ts`）：正面、側面、背面三個方向。殼板是主色往玄武岩混 0.35，殼縫紅光固定。P-2：三道殼縫各用一張偏移表 `CRACKS`。分派加在 `qGear.ts` 的 shieldSide／shieldBack 與 `qWeapons.ts` 的 pdHeld2。
- 圖示：`qIcon/weapons.ts` 加兩款（`block`，badge 0.87），畫法在 `qIcon/greatShields.ts`。背包、裝備欄都走這張表。
- 樣張同步（`docs/art/sample/rgPlayerShield.js`）：P-1 改 `sectPal()`，P-2 改成 `CRACKS` 三張表，P-4 修註解（盾邊 2.4，佔 8%）。其他既有畫法檔沒動。
- 開發頁：`/dev/rg5-shield-gallery.html`（`?mode=fp|pal|shield|doll|icon|dolls|materials|icons`）和 `/dev/rg5-shield-scene.html`（`?mode=scene|bag|c|d|k3&w=1600|800`）。

### 1.3 打盾兵掉的塔盾是對應形制（玩法PM交接 4.1.5）
- `world/loot.yaml` 的 `signature_affixes` 拆成兩列，每列多 `form`：持盾弟子 → `sect_great`，熔殼甲兵 → `molten_shell`。
- `world.loot._with_signature`：補上必帶詞條之後，形制換成那一列的 `form`。不取亂數，材質照一般規則（不動）。
- 陣容裡兩種盾兵都有時，取上面那一列（持盾弟子）。
- 其他來源的塔盾照一般規則。roguelite 三選一不套用（同 RG-4）。

## 2. 指紋（前端，無頭 Chrome `--headless=new --disable-gpu --mute-audio --dump-dom`，網址加 `?mute=1`）

| 項目 | 結果 |
|---|---|
| `/dev/rg4-shield-gallery.html?mode=fp`（既有盾 448 格） | 改前 `9bc00424`，改後 `9bc00424`，逐字相同 |
| rg5 `?mode=fp`（既有圖示＋持盾弟子整隻 4 方向 × 8 姿勢 × DPR 1～3，436 行） | 改前 `bf9d4970`，改後 `bf9d4970`，`cmp` 相同 |
| rg4 `?mode=doll`、`?mode=shield`（敵人配色） | 差異 0 |
| 新碑盾、熔殼部件 vs 樣張（12 種配色 × front/side/back × 縮放 1、2、4 × DPR 1、2 × 錨點整數／小數，864 格） | 差異 0 |
| 整隻 hero_fighter 拿新盾 vs 樣張（2 形制 × 7 材質 × 4 方向 × 8 姿勢 × DPR 1～3，1344 格） | 差異 0 |
| 圖示 vs 樣張（2 形制 × 12 配色 × 64/48/42/32、圓章 28/24/20 × res 1、2，336 格） | 差異 0 |
| vitest 既有快照（`qIconWeapons`、`creaturePose`、`inkDollSnapshot`、`qSectShield`） | 沒有更新任何快照 |

「新圖和第 10 節逐字相同」的對象，是改完 P-1、P-2 之後的樣張。P-2 改了殼縫，樣張和遊戲端一起改。

## 3. 預測與實際

| 項目 | 預測 | 實際 |
|---|---|---|
| `gearAppearance.json` | 只有 `kite_shield.forms` 末尾多 `sect_great`、`molten_shell` 兩款（帶 `offhands`），其他鍵逐字不變 | 同預測（+30 行，其他沒變） |
| 不變比對（改前＝RG-5 開工時的 HEAD；8 張地圖 × 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12；效用 AI、`max_rounds=30`；比整份紀錄，去掉 `format`、`ruleset_hash`、內嵌規則包） | 預設陣容沒有盾兵（`content/maps` 沒有任何 `shield_guard` 單位），高度改動不影響；盾陣沒人帶；連擊點單位只改文字 → `different=0`。規則包內嵌的層數表多 `unit_zh`、詞條改名 → `ruleset_hash` 46 場全變 | `battles=46 events=20499 different=0 ruleset_hash_changed=46` |
| 一場重播（open_plain 種子 7） | 通過 | 「重播驗證通過：91 個動作、383 個事件，最終狀態一致」 |
| CLI 快照 | 0 鍵變（沒有盾兵、盾陣、連擊點條件） | `tests/cli` 全過，未重產 |
| 物品生成（`tests/content/test_item_gen.py`） | 不變（副手形制照底材，不抽） | 全過 |
| 掉落（`tests/world`）、roguelite 快照（`tests/roguelite`） | 只有盾兵掉的塔盾換形制；其他掉落逐位元不變（同種子換成盜賊時，非塔盾那件 `item == base`）；roguelite 不變 | `tests/world`＋`tests/roguelite`＋`item_gen`＋`world_loot` 共 1666 passed，沒有快照要改 |
| `glossary.json` 測試替身 | 只有 `combo_point` 的說明「每層」→「每點」 | 同預測 |
| `openapi.json`、`schema.d.ts`、`skillCards.json`、`raceLooks.json` | 不變 | 重產後不變 |
| 計數類測試 | 前端外觀款數多 2 | `qIconWeapons.test.ts` 61→63；`qIconKeywords.test.ts`、`qi4bGearKeywords.test.ts` 105→107 |

## 4. 追加批次（玩法PM交接 4.1.6、RG-4 驗收裁定）

### 4.1 「護陣」改名「盾陣」（K1）
- 玩家看得到的字都改了：`affixes.yaml` 的 `name_zh`、`tuning_fields.yaml` 的工坊標籤與說明、戰鬥紀錄（「盾陣 −2［命中 −2：被X的盾陣擋住］」）、預覽文字（「盾陣 −2：被 X 的盾陣擋住 (x, y)」）。相關的 docstring、`core.yaml` 註解也一起改。
- 程式識別字（`affix_trait_tower_formation`、`shield_formation_hit_penalty`、`SHIELD_FORMATION`）沒改。
- 陣眼石靈的狀態 `ward`「護陣」沒動（`statuses.yaml`、`status_info`、`unit_traits`、狀態圖示）。

### 4.2 第一季只有打盾兵拿得到盾陣
- 照 4.1.6 確認，維持 RG-4 的做法，沒有改程式。低等級盾兵照帶（loot.yaml 註解已更新）。

### 4.3 掩護高度統一成「高 1 層」
- `combat.guard_blocks`：攻擊者站得比目標高 1 層以上就無視。盾兵和盾陣同一條，和塔盾本體一致。
- RG-4 以前的寫法是：持盾者視為 1 層高，攻擊者要比持盾者高 2 層才無視。
- 「目標比持盾者高 2 層以上時擋不到」照舊。
- 半掩護物件的高度條件沒動。4.1.6 寫「同塔盾、半掩護」，但現行半掩護物件仍是「掩護物視為 1 層高」，這次不改，見待決。
- 效用 AI 的盾兵站位估值（`ai/utility/position.py`）也呼叫 `guard_blocks`，所以跟著變。
- 測試：RG-4 原本標成「待確認」的那條改成「高 1 層無視」。RG-1 加「高 1 層無視」和「大家同高照樣擋」兩條。

### 4.4 連擊點的單位（KW-3）
- `StackDef.unit_zh`：預設「層」，預設值不輸出。`combo_point` 設成「點」。
- 用到它的地方：條件說明行（「自身「連擊點」達 5 點」，其他三種照舊「達 N 層」）、層數不足的拒絕原因、技能卡 `add_stack`／`consume_stack` 的單位、紀錄裡的層數變化行、裝備充能行。另外 `stacks.yaml` 連擊點說明的「每層」改成「每點」。
- 兩個名稱都保留：關鍵字叫「連擊」，層數叫「連擊點」。
- 條件說明行保留「」引號，只改單位。

### 4.5 前端（RG-4 驗收裁定）
- 待決 9：盾陣預覽沿用盾兵的小盾加點線。`battle/rgMarks.ts` 的 `GUARD_COVERS` 也認 `shield_formation`，沒有另畫圖示。
- KW-3 待決 3：`UnitInfo.tsx` 的連擊點、怒氣、專注、氣改畫和 HUD 同尺寸的 `StackPips`，其他層數照舊 `StackBadge`。0 層照現行規則不列。
- 開發 PM 決定：遇敵卡有單挑提議（`duel == "offered"` 而且不在戰鬥中）時，「開戰」拿掉 `primary`，其他情況照舊。
- K3（持盾弟子身邊一圈粉紅小點）：**不是畫錯，沒有修**。那是 6F-22 的舊剪影（`heightArt.silhouette()`：身體一個橢圓加頭一個圓，虛線 3／2，敵方外框色 `#ffb3a8`）。條件是南鄰格比自己高（`elevation.occluded()`）或屋頂蓋住，而且新外框沒畫。RG-4 那張截圖裡，持盾弟子的南鄰是高台，旁邊其他敵人的南鄰是平地，所以只有他有。拿劍的一般敵人在同樣位置也會畫，對照見 `7-k3-*`。

### 4.6 版號說明
- **`LOG_FORMAT` `/123` → `/124`**：盾兵與盾陣的高度條件改了。同樣的規則包與步驟，攻擊者比目標高 1 層時結算會不同。事件、狀態的欄位沒有增減。紀錄與預覽文字的「護陣」改成「盾陣」，連擊點的單位改成「點」（純文字，不影響重播）。`/123` 的紀錄無法重播。
  - 同步了 9 處寫死字串：`tests/cli` 6 檔 7 處、`test_gear_g2.py`、`test_gear_g3a.py`。
  - 同步了 3 個 `endswith`：`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`。
  - `docs/phases/戰鬥紀錄格式變更.md` 加了 `/124` 一條。
- **`WORLD_RULES_VERSION` 32 → 33**：掉落程式改了（盾兵掉的塔盾換成對應形制），世界裡的戰鬥結算也跟著上一條改了。
  - 同步了 `test_pr2a_range_practice.py`、`test_opening_stages.py`。
  - `world/save.py` 的版本說明加了 RG-5 一段。
- 日誌、角色、世界的格式都沒變。

## 5. 截圖（`docs/art/shots/RG-5/`，DPR 1，網址加 `?mute=1`，無頭 Chrome 加 `--disable-gpu --mute-audio`）

**全部是開發頁，實機未看。** 要拍實機，得另外開後端（不用 8000、8001），再寫 CDP 腳本建角、帶兩種盾、注入層數和單挑提議。這一輪沒做。開發頁走的是正式元件（BagContents、WornSlot、BattleRenderer、UnitInfo、WorldPanel）與正式 JSON。

| 檔 | 內容 |
|---|---|
| `1-dolls-devpage.png` | 玩家 hero_fighter 拿碑盾（鐵）、熔殼（鐵）；四方向 × 待機 0／700，真 1 倍、最近鄰 ×4、向量 ×4 |
| `2-bag-worn-1600-devpage.png`、`2-bag-worn-800-devpage.png` | 背包 42 格（兩種新盾混在塔盾、鳶盾、木圓盾、長劍之間）與裝備欄 48 格 × 7 材質，附最近鄰放大 |
| `3-materials-devpage.png` | 兩種形制 × 7 材質的換色；紙娃娃正面、側面、背面，真 1 倍＋向量 ×3 |
| `4-icons-true1x-devpage.png` | 裝備格 64/48/42/32、圓章 28/24/20；7 材質的 32、42、20，真 1 倍 ×4 |
| `5-scene-1600-devpage.png`、`5-scene-800-devpage.png` | 戰場（格子 63／25 px）：玩家碑盾、熔殼各朝 4 方向，含換色，與持盾弟子並排；真 1 倍＋ ×4 裁切 |
| `6-sample-vs-game-devpage.png` | 樣張和遊戲端並排，每格標 diff=0 |
| `7-k3-silhouette-1600-devpage.png`、`7-k3-silhouette-800-devpage.png` | K3 對照。左：持盾弟子南鄰高 2，有點。中：同一隻站平地，沒有點。右：一般劍兵南鄰高 2，也有點 |
| `8-c-formation-preview-1600-devpage.png`、`8-c-formation-preview-800-devpage.png` | 盾陣預覽的小盾加點線（上方預覽字的 `name_zh` 是假資料） |
| `9-d-unitcard-stacks-1600-devpage.png`、`9-d-unitcard-stacks-800-devpage.png` | 單位資訊卡：連擊 3、怒氣滿、專注 1、氣 2 畫成計量，靜電照舊 |
| `10-e-encounter-fight-1600-devpage.png`、`10-e-encounter-fight-800-devpage.png` | 遇敵卡。左：有單挑提議，「開戰」是一般樣式。右：沒有單挑，照舊藍色主鈕 |

## 6. 檢查結束碼

- `ruff check .` 0、`ruff format --check .` 0、`mypy` 0、`lint-imports` 0（14 kept）、`trpg content check` 0。
- `pnpm -C client typecheck` 0、`pnpm -C client build` 0（只有原本就有的 chunk 大小警告）。
- 相關 vitest 0（18 檔 243 項；子 agent 另跑 render/ui/world/battle/gear 313 檔、dev/screens/run/api/test 25 檔，全部通過）。
- 相關 pytest 全過。沒有跑全量 `check.py`。
- 子 agent 開的 vite（PID 34268、64356）都已用 PID 關掉；Chrome 是單次子程序，已經結束。

## 7. Commit

| commit | 內容 |
|---|---|
| `9ce22cfd1` | 樣張 P-1、P-2、P-4 |
| `830f3b700` | 前端：碑盾換色、熔殼紙娃娃與圖示 |
| `2a1818900` | 開發頁（指紋比對、場景、背包） |
| `91633b58a` | 第一批截圖 |
| `336fe9481` | 內容：兩種形制開放給玩家、`FormDef.offhands`、`gearAppearance.json` |
| `f4e282c18` | 盾陣預覽沿用盾兵小盾 |
| `309951816` | 盾兵掉對應形制、`WORLD_RULES_VERSION` 33 |
| `d8c5a2b89` | 單位資訊卡層數計量 |
| `72c884e4d` | 遇敵卡「開戰」在單挑提議時改一般樣式 |
| `438b9ffa0`、`8aa0c98e7` | 場景頁拿掉暫補、K3 對照、C／D／E 截圖、款數測試 |
| `8dd76b544` | 盾陣改名、高度統一、連擊點單位、`LOG_FORMAT` `/124` |
| （本報告的 commit） | 報告、上手筆記（前端 160、引擎 45）、一行格式修正 |

## 8. 待 PM 決定

1. **紙娃娃元素混色和圖示不同**（美術）：紙娃娃照遊戲現行的 `colors(it)[0]`（混 45%，元素色用 elementTint），圖示和樣張是關鍵字色混 40%。有元素關鍵字時，紙娃娃的盾面、殼板比樣張差一階（例：鐵＋點燃 `#b67758` 對 `#af785e`）。盾邊不受影響。現在照遊戲現行規則。
2. **P-1 的暗邊色**（美術）：「關鍵字只染盾面」解讀成暗邊也用本色的暗色。10.4 表的「鋼＋冰凍」盾邊 `#758e9e` 是 P-1 之前的值，遊戲端現在是 `#626e7c`。10.4 表要不要改。
3. **玩家／敵人怎麼分**：碑盾看有沒有 `trim`。敵人範本都有 `trim`，玩家物品不會帶。
4. **墨線畫風**（`inkOffhand.ts`）不認這兩個形制，會畫成鳶盾。遊戲固定 Q 版，規格沒提，所以沒做。
5. **P-2 的效果**：32 以上看得出上面那道只裂半邊、下面那道有分岔。圓章 20 仍然大致是三道橘線（10.7 第 3 條已接受）。
6. **K3 舊剪影**（美術）：6F-22 的剪影是固定的橢圓加圓，拿大盾的單位，小點會落在盾外。要不要改成貼實際外形，或有新外框時一律不畫。
7. **半掩護物件的高度條件**（玩法）：4.1.6 寫「統一成高 1 層（同塔盾、半掩護）」，但現行半掩護物件是「掩護物視為 1 層高、攻擊者要比掩護物高 2 層才無視」。這次只改盾兵與盾陣（專案 PM 轉達的範圍），半掩護物件沒動。要不要一起統一。
8. **掉落物品的名稱**：形制換了，物品名仍是「塔盾」。「雲紋碑盾」「熔殼塔盾」只出現在外觀的形制名（圖示說明等），物品名沒改。
9. **連擊點單位的範圍**：條件行、拒絕原因、技能卡、紀錄行、裝備充能、連擊點說明都改了；手寫技能各自的說明文字（例如「每層傷害 +20%」）沒有逐條改。
10. **形制與副手的對應只擋 `items.yaml` 與自訂物品**：世界掉落的形制來自 `signature_affixes.form`。這個 form 屬於塔盾的造型、而且限定配塔盾，由測試 `test_signature_forms_are_tower_shield_forms` 保證，載入時沒有另外交叉檢查。
11. **實機截圖**：這輪全是開發頁（見第 5 節）。

## 9. 平衡疑慮

- 盾兵與盾陣在「攻擊者高 1 層」時不再擋，高台弓手對盾兵陣型更有利。現有地圖的預設陣容沒有盾兵，影響要看世界遭遇。
