# Phase E6-c1 報告｜傳說產生器（開關預設關）

> 規格 `docs/phases/PhaseE6-c1計畫.md`；規則以 `docs/design/08-裝備.md` 8.27、8.21.2.11 的 #180 註、8.30 第 6、7、10、11 點為準；做法照 E6 草案 c 段與 D12、D14。基準 main `2cf79cf35`（交件前合併 main 到 `1cb9054a1`，只多文件與美術截圖）。不改引擎，`LOG_FORMAT` 不升；沒動 `client/`、`config/`、`docs/design/`。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 稀有度表加傳說、傳說的預算檢查、部位 | `9c05e2967` |
| 2 獨特效果（招牌那一步、池子） | `10684c138` |
| 6 開關 `legendary_enabled`（預設關）＋產生器接上傳說 | `ef6fba839` |
| 3 程式命名 | `a8a8c3349` |
| 4 產生器不再挑 `items.yaml` 的測試傳說 | `4489968e0` |
| 5 獨特效果不能重抽 | `96735c179` |
| 合併 main | `1cb9054a1` |
| 報告 | 最後一個 commit |

第 6 項排在第 3 個 commit：產生器要先有開關，才能在「關著逐位元不變」的前提下接上傳說。

## 2. 各項做法

### 2.1 稀有度表與預算檢查（第 1 項）

- `item_gen.yaml`：`rarities.legendary: {min 2, max 2, categories 同史詩, required: true}`（草案 D14）；新欄位 `legendary_slots: [weapon, offhand, body, feet, neck]`（8.30 第 6 點）。`ItemGenRules` 的 `rarities` 允許傳說，加 `legendary_slot()`。
- `item_budget.legendary_unique(affix)`：能當獨特效果的詞條＝標了招牌、改寫規則（`category: rule`）、`legendary_only`（8.30 第 7 點）。傳說另外 2 條的類別同史詩，不會是這些詞條，所以傳說上符合的那一條就是獨特效果，不另存欄位。
- `affix_points(..., legendary=True)`：給了詞條預算時，傳說上的獨特效果照 `signature_points`（60%，分數不捨去）；不是傳說或不知道預算時照舊。`item_points`、`item_budget_problems` 依物品帶入。
- `item_budget_problems`：
  - 沒有物品等級的傳說（三件測試傳說）照舊不檢查，點數照舊（40）。
  - 有物品等級的傳說：部位要在 `legendary_slots`；恰好 1 個獨特效果；獨特效果不佔 2 條、不算類別；上限是整件預算，**不檢查下限**（比照招牌，E6-a2「放得下就放」）。
- 工坊：`tuning_fields.yaml` 開 `rarities.legendary.min_affixes／max_affixes`（`test_workshop_open_hcw2` 要求每個整數都開）；x10 的 `rarities.*.*` 原本就列 keep。`legendary_slots`、`legendary_enabled` 不是整數，不開。

### 2.2 獨特效果（第 2 項）

- `item_gen._unique_effect`：池子＝`_unique_fits`（能掛在底材，以傳說物品檢查所以限傳說的也能掛；不含獨特、暫緩詞條）。
- 種類：標了招牌的照招牌種類；沒標的改寫規則算「改寫規則」；依部位權重 `signature_weights` 抽種類（沒候選的種類當 0），再從那一種（依 id）抽 1 條。數值取最強的，點數 60%。
- 沒標種類、也不是改寫規則的限傳說詞條（現在沒有）另成一組、權重 1（待決 1）。
- 沒有任何候選時回傳 `None`、不取亂數。
- 傳說不看 `signature_enabled`，也不另帶招牌（8.27「傳說不再另帶招牌效果」）。

### 2.3 開關與產生器（第 6 項）

- `ItemGenRules.legendary_enabled: bool = False`，`item_gen.yaml` 寫 `legendary_enabled: false`。
- 關著：抽到傳說照舊走 `_legendary`（從 `items.yaml` 挑同部位，沒有就降史詩），其他稀有度不受影響。程式只把 `rules = _rules(...)` 提前、`ctx` 移到抽底材之後，兩者都不用亂數。
- 打開：
  - 頭、手、戒指 → 降成史詩（在抽底材之前）；
  - 抽底材 → 抽獨特效果；沒有候選 → 降成史詩，照一般史詩流程（含招牌那一步）；
  - 剩下的預算（整件 − 60%）照 `rarities.legendary`（2 條，第 1 條 build 詞條）分，`allow_empty=True`（放得下就放）；
  - 獨特效果放最後；物品 `rarity: legendary`、`legendary: true`（`_affix_slot_problems` 要 `legendary` 旗標才准掛限傳說詞條）。
- 傳說給了 `signature_kind` 時拋 `ItemGenError`「傳說的獨特效果不能指定類型」（打造傳說是 E6-c2，待決 3）。

### 2.4 命名（第 3 項）

- `_item_name(rarity, base)`：程式取名「稀有度＋底材名」，傳說就是「傳說長劍」這類。不用亂數、不看獨特效果。LLM 取名另開一段（8.30 第 10 點）。

### 2.5 測試傳說（第 4 項）

- 開關打開時不再走 `_legendary`；三件測試傳說留在 `items.yaml`。`items.yaml` 在三件前面加了註解，`_legendary` 補了說明。

### 2.6 不能重抽（第 5 項）

- `affix_choices`：傳說的獨特效果回傳空（附魔台顯示「不能換」，指定也一樣，因為指定也看 `affix_choices`）。另外 2 條照一般規則；算剩餘預算的 `_others` 把獨特效果照 60% 計。
- 配套（規格沒寫，照招牌的做法）：
  - `downscale_item`（影子借用壓等級）：獨特效果照 60% 計價，最後才拿（`_kept_last`）。和招牌一樣，只剩範圍詞條還放不下時才會拿掉它。
  - `with_affix`（必帶詞條）：獨特效果不佔稀有度條數，也不會被拿掉。
  - 待決 2。

## 3. 驗收

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（E6-b1 的 `budget.py`；基準 `2cf79cf35` 用 `git archive` 解開） | `cmp` 0，skills=442 different=0 |
| 78 場戰鬥（`compare78.py`） | `battles=78 events=26741 different=0`；規則包差異 0；格式 `/139 → /139` |
| census 小樣本（`census_run.py`：`--seeds 4 --tiers 1,3 --rarities common,epic`；`census_cmp.py` 不看計時） | `cells=204 different=0`，除計時外整份相同 |
| 產生器種子比對（E6-a1 的 `gen_seed.py`，6752 行，含傳說稀有度與 `items.yaml` 每件的點數、預算檢查） | 基準與新版 `cmp` 0，different=0 |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 0、0、0、0（含在 `check.py --all`，開發中各項 commit 前也跑過） |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0；`classes.yaml` 的 `py-content-item-budget-const-text` 多 `_legendary_problems`） |
| `uv run python scripts/check.py --all`（合併 main 之後） | 0，已寫通過戳記 |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed） |

**新測試**

- `tests/content/test_legendary_budget_e6c1.py`（第 1 項）：
  - 稀有度表同史詩、2 條、`legendary_slots`；
  - 獨特效果候選的判斷；
  - 60% 計價，非傳說或沒預算時照類別點數；
  - 2 條不含獨特效果，第 3 條報錯；
  - 恰好 1 個獨特效果；
  - 超過預算報錯、沒有下限；
  - 頭、手、戒指報錯；
  - 測試傳說照舊不檢查。
- `tests/content/test_legendary_unique_e6c1.py`（第 2 項）：
  - 現有內容只有 3 條改寫規則可抽；
  - 池子含招牌、改寫規則、限傳說詞條；
  - 副手種類權重 3：1：1；
  - 權重 0 的種類不抽；
  - 暫緩詞條排除；
  - 沒候選回傳 `None` 且不取亂數；
  - 數值取最強。
- `tests/content/test_legendary_gen_e6c1.py`（第 6、3、4 項，開關打開）：
  - 開關預設關；關著照舊挑測試傳說；
  - 五個部位 × 等級 1～10：傳說、獨特效果放最後、其他 ≤ 2 條、60%、通過物品與預算檢查；
  - 10 級主手＝技能強化＋1 條＋獨特效果；
  - 頭、手、戒指降史詩，而且和同種子的史詩相同；
  - 沒候選降史詩；
  - 招牌開關也開時傳說只有 1 個獨特效果；
  - 開關打開不影響其他稀有度；
  - 傳說不能指定招牌類型；確定性；
  - 程式命名「傳說〇〇」；
  - 不挑 `items.yaml` 的測試傳說（含 `generate_item_retrying`）。
- `tests/content/test_legendary_reroll_e6c1.py`（第 5 項）：
  - 獨特效果沒有候選；另外 2 條可以重骰，換完照樣通過檢查、獨特效果不變；
  - 縮等級時獨特效果最後才拿；
  - 必帶詞條不拿掉獨特效果。

沒有新增 `# noqa`。

## 4. 待 PM 決定

1. **沒標種類的限傳說詞條怎麼抽**：現在沒有這種詞條。我讓它們另成一組、權重 1，和五種一起抽。另一種做法是要求限傳說詞條一定要標招牌種類（內容檢查擋下）。第 10 步寫內容時玩法 PM 定即可。
2. **縮等級、必帶詞條的配套**：規格只寫「不能重抽」，我把「獨特效果最後才拿、照 60% 計價」也套到 `downscale_item`、`with_affix`，做法同 E6-a1 的招牌。和招牌一樣，縮到很低等級、剩下的都是範圍詞條時，獨特效果還是可能被拿掉（低等級的腳、身體會出現）。
3. **傳說＋`signature_kind`**：打造傳說屬於 E6-c2，這段先拋錯「傳說的獨特效果不能指定類型」。E6-c2 要接「指定獨特效果的類型」時，在 `_unique_effect` 加種類篩選即可。
4. **獨特效果的辨認不另存欄位**：靠「傳說上符合 `legendary_unique` 的那一條」。傳說另外 2 條的類別同史詩，所以不會混淆。手寫物品若在傳說上放 2 條候選，檢查會報「有 2 個」。
5. **傳說沒有下限**：比照招牌（E6-a2「放得下就放」），預算檢查只看不超過整件預算。
6. **開關打開時預算分數變了**：`item_strength` 會把獨特效果照 60% 計（不是改寫規則原本的 40 點），所以戰後三選一的「預算分數」比較也跟著變。開關關著時沒有影響（測試傳說沒有物品等級，照舊 40）。

## 5. 平衡疑慮（請 PM 轉玩法）

- 沒試數值。只記：開關打開後，現有內容的獨特效果只有 3 條改寫規則可抽（還沒標招牌）。低等級的腳、身體在獨特效果 60% 之後剩下的預算很小，常常只有獨特效果加 0～1 條。
