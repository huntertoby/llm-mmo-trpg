# Phase E6-c2 報告｜傳說的打造與掉落（＋WM-1 旁白占位小修、E6-b2「。；」小修）

> 規格 `docs/phases/PhaseE6-c2計畫.md`；規則以 `docs/design/08-裝備.md` 8.27、8.30 第 6、8、10、11 點與 `docs/design/平衡待查.md` 第 41 條為準；小修照 `docs/art/WM-1驗收.md`、`docs/art/E6-b2驗收.md`。基準 `084157a1c`（開工後照開發 PM 指示合併 main 到 `5d5d32f1b`，只多 E6-b2 美術驗收與交接文件）。不改引擎，`LOG_FORMAT` 不升（`/139`）；沒動 `docs/design/`、`config/`、`CLAUDE.md`。
>
> 第 6 項是開發 PM 中途追加的（E6-b2 美術小修）。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 鐵匠打造傳說 | `3decb42e6` |
| 2 世界掉落傳說 | `d6d8e9e4d` |
| 3 傳說的賣價 | `6edcb6ae1` |
| 4 前端打造畫面多傳說＋截圖 | `cfe522aed` |
| 5 (ah) 旁白占位小修＋截圖 | `7057c5583` |
| 6 E6-b2「。；」小修＋截圖（追加） | `8fc2f50f5` |
| 合併 main | `5d5d32f1b`（開工時） |
| 報告 | 最後一個 commit |

## 2. 各項做法

### 2.1 鐵匠打造傳說（第 1 項）

- 資料：`content/world/crafting.yaml` 的 `craft.rarities` 多 `legendary: {gold_per_level: 40, quest_coins: 5, extra: {item_superior_material: 1}}`（平衡待查第 41 條初值）。`CraftRarityCost` 新欄位 `extra`（另外要的材料 → 個數，和配方的材料一起扣；跨檔檢查要是材料）。既有的稀有、史詩一字未改。
- `CraftRarity`、`CraftAction.rarity`、`CraftRecipe.rarity` 的字面值多 `legendary`。**`CraftRecipe` 沒有加欄位**：傳說指定的類型沿用 E6-a2 的 `signature`（空值不輸出），所以舊配方的 JSON、指紋、配方碼都不變（舊配方碼比對 different=0）。
- `world.crafting`：
  - `legendary_problem`：開關 `legendary_enabled` 關著 →「傳說打造還沒有開放」；部位不在 `legendary_slots` →「傳說只能打主手、副手、身體、腳、項鍊」。用欄位打造、用配方碼打造都檢查。
  - `unique_choices(slot, weapon_class)`：可以指定的獨特效果類型（8.27 的五種順序）；篩法同 `signature_choices`（不限定武器種類、不是獨特或暫緩詞條），候選用 `legendary_unique`（招牌、改寫規則、限傳說）。沒標種類的限傳說詞條不能指定（E6-c1 待決 1 那一組）。
  - 二選一照一般打造（抽成 `_chosen`）：給 `signature` → 傳說時檢查 `unique_choices`，其他照 E6-a2；給 `affix` → 照 `build_choices`。`CraftAction` 原本就擋兩個都給。
  - 隱藏配方照舊優先（稀有度由配方決定，傳說也一樣）。
  - 打出來的不是傳說（沒有獨特效果候選時產生器會降史詩）→「這份配方打不出來（這個部位沒有能用的獨特效果）」，不收費。
- 產生器 `generate_item(..., signature_kind=)`：傳說（開關打開）時是獨特效果的類型，`_unique_effect(kind=)` 只從那一種（依 id）抽、不看部位權重；那一種沒有候選時拋 `ItemGenError`（不降史詩）。E6-c1 的「傳說的獨特效果不能指定類型」拋錯拿掉，對應測試改成新行為。沒給 `kind` 時路徑完全不變（產生器種子比對 different=0）。`_unique_kind` 改名公開為 `unique_kind`。
- API 顯示資料在開關關著時不列傳說（第 4 項一起處理，這一項先把 `_rarity_views` 擋好，免得關著時畫面多出傳說）。
- `scripts/hardcoded/classes.yaml`：「要指定 1 條詞條」那條歸類的 `where` 加 `_chosen`（字從 `_recipe_from_fields` 搬過去）。

### 2.2 世界掉落傳說（第 2 項）

- `content/world_loot.py`：`battle_weights` 的舊條文（「掉落不產生傳說（8.22.1 第 7 點）」）拿掉，改成「一般戰鬥不掉傳說（08 8.30 第 8 點）」——一般戰鬥的權重仍不能寫傳說。
- `GearDropRules.elite_legendary_permille`（預設 0），`loot.yaml` 寫 20（2%）。
- `world.loot._roll_gear`：精英那一件（含區域 Boss）先用 `_legendary_roll` 抽：只在 `legendary_enabled` 打開時抽，亂數用 `rng.fork("legendary")`，**不推進原本的串流**，所以關著時掉落逐位元不變，開關打開後沒抽到傳說的那件也和關著時相同（測試鎖住）。抽到時稀有度換成傳說；頭、手、戒指由產生器降成史詩（8.30 第 6 點）。
- 頭目的保底史詩（5F-3）抽到傳說時換成傳說（待決 2）。

### 2.3 賣價（第 3 項）

- `loot.yaml` 的 `sell_rarity_coef` 加 `legendary: 20`（初值）。沒有物品等級的照舊不收（`items.yaml` 的三件測試傳說、初始裝備）。分解照舊不收傳說（`crafting.yaml` 的 `salvage` 沒動）。
- 賣不掉的錯誤訊息從「初始裝備與傳說不收」改成「沒有物品等級的裝備不收」。`tests/world/test_gear.py` 原本用「有物品等級的傳說」驗不收，改成沒有物品等級的那種。

### 2.4 前端打造畫面（第 4 項）

- API：`CraftRarityView.slots`（這個稀有度能打的部位；傳說＝`legendary_slots`，其他空＝全部）、`cost_zh` 多「＋上料 ×1」；`CraftSlotView.uniques`（「獨特效果：〇〇」）；開關關著時不列傳說、`uniques` 是空的。配方表摘要：傳說寫「・指定獨特效果：〇〇」。`openapi.json`、`schema.d.ts` 重新產生；5 個前端夾具補 `uniques: []`、`slots: []`。
- 前端 `crafting.ts`：`kindOptions`（傳說用 `uniques`、其他用 `signatures`）、`slotsFor`、`withRarity`（換稀有度時部位不能打就換第一個能打的，類型選項跟著換，不能用的類型換成第一條詞條）。`SmithyPanel`：部位下拉照稀有度篩、稀有度改走 `withRarity`、選傳說時那組選項的標題是「或指定獨特效果類型（不能指定是哪一條）」。後端沒列傳說時完全不出現。
- 截圖用新開發頁 `client/dev/e6c2-smithy.html`（`src/dev/e6c2SmithyGallery.tsx`，正式 `SmithyPanel`＋假資料；開關預設關，實機到不了）。

### 2.5 (ah) 旁白占位小修（第 5 項）

- `StoryParts.StoryPendingDialog`：和補上後的 `StoryDialog` 同一個說書人框（`.world-dialog`、48px 頭像、「說書人」名字），文字區放灰色的占位句（字照舊「說書人正在構思這段故事……」，拿掉原本的斜體）。`EventCard` 改用它，`data-testid` 照舊 `world-event-story-pending`。
- `story.css`：事件卡裡的說書人框文字區先留好一段旁白的高度 `min-height: calc(3 * 1.55em + 4px)`——一段最多 48 字（`narration.ts` 的 `PAGE_MAX`），事件卡文字區一行約 18 字，所以留 3 行（規格寫「至少兩行」；只留兩行時實測補上後卡片長高 22px，見待決 4）。只套在 `.world-event` 裡，其他對話框不變。舊的 `.world-story-pending` 樣式拿掉。
- 量測（headless Chrome 800 寬，`storyGallery` 新增 `?mode=story-pending`／`story-filled`）：兩張卡片高 467／467、文字區 69／69、選項按鈕的上緣 `[271,271,343,343,386,432]` 兩張完全相同。

### 2.6 E6-b2「。；」小修（第 6 項，追加）

- 新的 `client/src/gear/clauses.ts` `joinClauses`：先拿掉每段結尾的「。」（連續的也拿），再用「；」接起來；沒有「。」結尾時和原本的 `join("；")` 逐字相同。
- 用在：`GearCardView` 比較區「目前」那行（標灰卡、背包詳情、三選一共用），另外同樣是把裝備文字用「；」接起來的 `itemLines` 的副手特性、`gearDraft.itemSummary`、`SlotGrid` 說明、`ItemList` 副手特性也一起換（待決 5）。

## 3. 驗收

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（`budget.py`；基準 `084157a1c` 用 `git archive` 解開） | `cmp` 0，442 招 different=0 |
| 78 場戰鬥（`compare78.py`） | 0；`battles=78 events=26741 different=0`；規則包差異 0；格式 `/139 → /139` |
| census 小樣本（`census_run.py`：`--seeds 4 --tiers 1,3 --rarities common,epic`；`census_cmp.py` 不看 `timing`） | `cells=204 different=0` |
| 產生器種子比對（`gen_seed.py`，6752 行，含傳說稀有度） | 基準與新版 `cmp` 0，different=0 |
| 舊配方碼（`recipes.py` 6 份配方的指紋、配方碼、帶序列的配方碼；`test_recipe_code_compat_e6a2.py`） | `cmp` 0，different=0；測試通過（含在 `check.py --all`） |
| 世界掉落同一批種子（新寫的 `loot_seed.py`：兩區 × 物品等級 1／4／7／10 × 一般／精英／頭目保底 × 主手同大類與否 × 種子 0～149，共 7200 筆、5116 筆有掉落） | 基準與新版 `cmp` 0，different=0 |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 0、0、0、0（每項 commit 前跑過；也含在 `check.py --all`） |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| tsc（`pnpm -C client typecheck`）、vitest | 0、0（含在 `check.py --all`） |
| `uv run python scripts/check.py --all`（全部程式 commit 之後） | CHECK_RESULT |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | SLOW_RESULT |
| `pnpm -C client build`（`corepack pnpm`） | BUILD_RESULT |

比對腳本與輸出在 scratchpad 的 `e6c2/`（`budget.py`、`compare78.py`、`census_*.py`、`gen_seed.py` 沿用 E6-c1／E6-a2；`loot_seed.py` 是這段新寫的）。

**截圖**

- `docs/art/shots/e6-c2/smithy-legendary-1600.png`（1600 寬）：左＝選了傳說（部位只剩五個、費用寫上料）；中＝部位與詞條下拉展開、選了「獨特效果：改寫規則」；右＝開關關著，稀有度只有稀有、史詩。
- `docs/art/shots/wm-1b/story-1-pending.png`、`story-2-filled.png`（800 寬）：占位與補上，按鈕位置相同（見 2.5 的量測）。
- `docs/art/shots/e6-b2b/grey-card-800.jpg`（800 寬）：`e6b2-gallery.html?part=cards`，最後一排兩張標灰卡的「目前」那行是「你走過的格子結 1 回合冰；你自己踩不會滑倒；基礎加成：防禦值 +1%」「……和其他反應共用每輪 1 次；敏捷 +3；閃避 +3%」，沒有「。；」。

截圖都用 headless Chrome（`--mute-audio`、網址帶 `mute=1`），自己開的 vite（5199 埠）與 Chrome 交件前都用 PID 關掉。

**新測試**

- `tests/world/test_crafting_legendary_e6c2.py`（第 1、4 項）：
  - 獨特效果類型跟著開關與部位；
  - 指定類型打出傳說、獨特效果是那一種、放最後、配方記類型、配方碼照打相同；
  - 指定技能強化：第 1 條是那條、獨特效果隨機；
  - 二選一；
  - 頭、手、戒指不能打；
  - 部位沒有那一種時報錯；
  - 開關關著不能打；
  - 費用（金幣 40 × 等級、任務幣 5、另 1 個上料，通用料是精料時上料另扣、上料不夠打不了）；
  - 傳說配方沒有多欄位；
  - 顯示資料：開關打開才列傳說（費用字、部位）、`uniques`、配方摘要。
- `tests/world/test_loot_legendary_e6c2.py`（第 2 項）：初值 20‰、開關預設關；關著時和機率 0 逐位元相同；機率 100% 時精英一定傳說（頭、手、戒指降史詩）、一般戰鬥不出；初值 2% 時 400 種子有出、沒抽到的和關著相同、一般戰鬥不出；頭目保底變傳說；`battle_weights` 寫傳說被擋。
- `tests/world/test_sell_legendary_e6c2.py`（第 3 項）：係數 20、`gear_price`、實際賣出、仍不能分解。
- `tests/content/test_legendary_gen_e6c1.py`：`signature_kind` 對傳說改成指定獨特效果類型（原本是拋錯）。
- `client/src/world/crafting.test.ts`：傳說只列能打的部位、換稀有度時部位與類型跟著換、送 `rarity: legendary`＋`signature`、開關關著不出現。
- `client/src/world/eventStory.test.ts`：占位是同一個說書人框（外框 class、頭像、名字相同）、灰色占位句、框以外的卡片內容逐字相同。
- `client/src/gear/clauses.test.ts`：`joinClauses`；「目前」那行沒有「。；」；物品摘要也一樣。

沒有新增 `# noqa`。

## 4. 待 PM 決定

1. **打造傳說沒有獨特效果候選時**：產生器原本會降成史詩；打造改成報「這份配方打不出來」、不收費（玩家付的是傳說的錢）。指定類型時那一種沒有候選，產生器直接拋錯（不降史詩）。現有內容五個部位都有 3 條改寫規則可抽，所以實際碰不到。
2. **頭目的保底史詩也會抽傳說**：8.30 第 8 點寫「精英、頭目」，我讓區域 Boss 的那一件也抽 2%，抽到時保底史詩換成傳說（傳說高於保底）。另一種做法是保底那件不抽。
3. **傳說的費用欄位**：「另要 1 個上料」做成 `CraftRarityCost.extra`（材料 → 個數），和通用料一起扣；通用料剛好也是上料時合計扣（例：項鍊 1＋1＝2 個）。費用字寫「＋上料 ×1」。
4. **旁白框的高度留 3 行**：規格寫「至少兩行」。事件卡的文字區一行約 18 字、一段旁白最多 48 字，只留兩行時補上後卡片長高 22px、按鈕往下跳，所以留 3 行（量測相同）。還有一種會長高的情況沒處理：旁白只有一段、又有「多講一點」時，那顆按鈕補上後才出現。
5. **「。；」改的範圍**：除了驗收點名的「目前」那行（標灰卡、背包詳情），同樣用「；」接裝備文字的 `itemLines` 副手特性、`itemSummary`、`SlotGrid` 說明、`ItemList` 副手特性也一起改。後端 `world_crafting_view` 的鐵匠裝備說明（`description_zh`）也是「；」接詞條，沒改（不在前端、這次沒看到問題）。
6. **前端的呈現**：傳說的類型選項放在同一個「詞條」下拉的那組選項裡（照 E6-a2），標題換成「或指定獨特效果類型（不能指定是哪一條）」；換成傳說時部位下拉只剩五個部位。交美術看截圖。
7. **開發頁**：`client/dev/e6c2-smithy.html` 與 `storyGallery` 的兩個新模式留在 repo（同 E 系列做法）。

## 5. 平衡疑慮（請 PM 轉玩法）

- 沒試數值。傳說打造金幣每級 40、任務幣 5、1 個上料，賣價係數 20，精英與頭目 2% 傳說，全是平衡待查第 41 條與 8.30 的初值；開關預設關，打開時一起看（平衡待查第 41、43 條）。
