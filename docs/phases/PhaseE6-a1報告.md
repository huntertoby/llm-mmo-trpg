# Phase E6-a1 報告｜招牌標記、60% 定價、產生器（開關預設關）

> 規格 `docs/phases/PhaseE6-a1計畫.md`；規則以 `docs/design/08-裝備.md` 8.27、8.30 第 1、2、11 點（#180）與 8.21.6、8.22.1 第 6 點的 #180 加註為準。基準 main `3900361f2`。不改引擎，`LOG_FORMAT` 不升。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 招牌欄位（五種、空值不輸出、載入檢查） | `0eb5bfdb2` |
| 2 60% 定價、70% 下限只看招牌以外 | `b1680ebf8` |
| 3 條數（招牌算進條數） | `5f0bc64c9` |
| 4 產生器（部位權重、開關預設關） | `4f6a04043` |
| 5 改寫規則拿掉「限傳說」 | `fee4b6165` |
| 報告 | 最後一個 commit |

## 2. 各項做法

### 2.1 招牌欄位（第 1 項）

- `_AffixBase.signature: Literal["action", "reaction", "terrain", "behavior", "rule"] | None`，空值不輸出（`exclude_if`），既有詞條、物品、內嵌在 `BattleSetup` 的 `Loadout` 序列化都不變。
- 載入時檢查種類和類別相符（`equipment.SIGNATURE_CATEGORIES`）：
  - 新動作、行為改寫：第 9 類（授予技能）；
  - 新反應：第 10 類，或授予反應技的第 9 類；
  - 地形規則：第 12 類；改寫規則：第 11 類。
- 第 9 類再對照授予的技能種類（`gear_checks.SIGNATURE_SKILL_KINDS`）：新動作＝主動、行為改寫＝修正、新反應＝反應。授予被動技的不能標招牌。
- 現有內容**沒有**標招牌（草案 D1 說要補 9 條，但規格要求既有資料序列化不變、D13 也說內容由第 10 步一併清，見待決 2）。

### 2.2 60% 定價（第 2 項）

- `item_gen.yaml` 加 `signature_permille: 600`（`ItemGenRules` 必填欄位）。
- `item_budget.signature_points(rules, budget)` ＝ `Fraction(budget × 600, 1000)`，不捨去。
- `affix_points` 加關鍵字參數 `budget`（該件的詞條預算）。招牌詞條有 `budget` 時用 60%；沒給 `budget`（不知道是哪件、沒有物品等級）照舊用類別固定點數。
- `item_points`、`item_budget_problems`、產生器的 `_best_value`、`affix_choices`、`downscale_item`（`_drop_fixed`、`_lower_value`、`_fixed_points`）、`with_affix` 都帶入該件的詞條預算。
- 70% 下限（新函式 `_fill_problems`）：
  - 沒有招牌：和原本一字不差（訊息也一樣）。
  - 有招牌：上限仍是整件 100%；下限只看招牌以外——招牌以外的點數要 ≥（預算 − 招牌）× 70%；招牌以外什麼都沒放時不檢查下限。
- 例：5 級主手預算 24、招牌 14.4、剩 9.6、下限 6.72；1 級主手預算 12、招牌 7.2（不捨去）。

### 2.3 條數（第 3 項）

- `item_gen.yaml` 加 `signature_rarities: [rare, epic]`、`signature_slots: [weapon, offhand, body, feet, neck]`；`ItemGenRules.carries_signature(rarity, slot_type)`。
- `RarityRule.besides_signature()`：上下限各少 1（稀有 2～3 → 1～2、史詩 3 → 2），build 詞條（8.21.6）照舊。
- 預算檢查 `_rarity_problems`：帶招牌的稀有度、部位上，**第 1 條**招牌不算類別（不會被當成「不能有 action 類詞條」），但算進條數上限（稀有、史詩最多 3 條）。其他稀有度、部位（頭、手、戒指、普通、優良）或第 2 條招牌照舊報類別錯誤。

### 2.4 產生器（第 4 項）

- `item_gen.yaml` 加 `signature_enabled: false` 與 `signature_weights`（主手、副手：新動作 3、行為改寫 3、其他 1；身體：新反應 3、其他 1；腳：地形規則 3、其他 1；項鍊全部 1）。`ItemGenRules` 檢查權重的部位要在 `signature_slots`、權重不可為負。
- `item_gen._signature`：開關打開、而且是帶招牌的稀有度與部位時，依 `SIGNATURE_KINDS` 的固定順序排權重；某種類在這件底材上沒有候選（`_fits`：能掛、不限傳說、不是獨特或暫緩詞條）時權重當 0；五種都沒有就不帶招牌，照一般的稀有、史詩產生。抽到種類後從候選（依 id）抽 1 條，數值取最強的。
- 招牌以外：剩下的預算（分數）、`besides_signature()` 的條數，照原本的流程分；`_roll_affixes` 加 `allow_empty`，放不下任何一條時回傳空的（只有招牌），不拋錯。
- 招牌放在詞條**最後**，第 1 條仍是 build 詞條（`affix_choices`、打造指定、`with_affix` 都依賴「第 1 條是 build」）。
- 材料傾向（`leanings`）、區域關鍵字不影響招牌：招牌在分其他詞條之前抽完。
- 開關關著時 `_signature` 直接回傳、不取亂數，產生器結果逐位元不變（見第 3 節）。
- 招牌「一定在」的配套（目前沒有內容會走到）：`affix_choices` 對招牌那一條回傳空（重骰是 E6-a2）；`downscale_item` 的 `_drop_fixed` 最後才拿招牌；`with_affix` 從最後一條「不是招牌」的開始拿。
- 工坊：`tests/api/tuning/test_workshop_open_hcw2.py` 要求 `item_gen.yaml` 的每個整數都開進工坊或列為結構，所以 `signature_permille` 與 25 個權重都開了（「其他類別的點數」與新的「招牌效果」組，寫了調高、調低的影響）。`signature_enabled` 是布林，不開。

### 2.5 改寫規則拿掉「限傳說」（第 5 項）

- `RuleAffix` 拿掉「必須 `legendary_only: true`」的檢查。`legendary_only` 照舊由資料決定：`_affix_slot_problems` 仍擋「限傳說詞條掛在非傳說物品上」，產生器 `_fits`、打造 `build_choices` 仍不抽限傳說詞條。
- 現有 3 條改寫規則都還是 `legendary_only: true`，所以已經在用的路徑結果不變。標灰、由玩家選是 E6-b1，這段沒做。

### 2.6 新數字的歸類

- `scripts/x10/fields.yaml`：`signature_permille`、`signature_weights.*.*` 列為 keep（點數比例與權重，不跟 ×10）。
- `scripts/hardcoded/classes.yaml`：`py-content-item-budget-const-text` 的範圍多一個 `_fill_problems`（預算區間的訊息從 `item_budget_problems` 搬過去）。
- 沒有新增 `# noqa`。

## 3. 驗收

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill` 違規；基準 `3900361f2` 用 `git archive` 解開） | `skills=442 same=442 different=0` |
| 78 場戰鬥（E5 的 `compare78.py`；去掉 `ruleset_hash`、內嵌規則包，`format` 也比） | `battles=78 events=26741 different=0`；內嵌規則包 0 差異 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0 whole_equal=True` |
| 產生器種子比對（新腳本：8 欄位 × 5 稀有度 × 等級 1～8 × 種子 0～11，加關鍵字、材料傾向、打造指定、武器大類、`roll_rarity`、`generate_item_retrying`、`downscale_item`、`with_affix`、`affix_choices`、`pick_affix`，以及 `items.yaml` 每件的點數與預算檢查；共 6752 行） | 基準與新版逐位元相同（`cmp` 結束碼 0，different=0） |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 0、0、0、0 |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| `uv run python scripts/check.py --all` | 0（第 3.1 節） |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（第 3.1 節） |

**新測試**

- `tests/content/test_signature_e6a1.py`：五種、空值不輸出（全部現有詞條 dump 不含 `signature`）、往返、種類和類別不符被擋、授予技能的種類要對。
- `tests/content/test_signature_pricing_e6a1.py`：60% 不捨去（等級 1～10）、沒給預算時照類別點數、`item_points`、70% 下限只看招牌以外、只有招牌時通過、沒標招牌時點數不變；稀有度與部位、`besides_signature`、招牌算進條數上限但不算類別、其他稀有度與部位仍報類別錯誤。
- `tests/content/test_signature_gen_e6a1.py`（測試內容庫：把幾條現有詞條標成招牌，另加腳的地形規則、主手的行為改寫，開關打開）：
  - 招牌一定在、放最後、點數是 60%，而且通過物品與預算檢查（5 部位 × 稀有、史詩 × 等級 1～10）；
  - 頭、手、戒指與普通、優良不帶；
  - 1 級稀有靴子只有招牌；
  - 條數：10 級史詩主手＝招牌＋2 條、第 1 條是技能強化；稀有是 2～3 條，放不下時 1 條；
  - 招牌以外的部分 ≥ 剩下預算的 70%；
  - 部位權重（副手新動作：新反應 ≈ 3：1；主手新動作：行為改寫 ≈ 1：1；身體、腳、項鍊只出有候選的那種；改權重會跟著變）；
  - 沒有候選的種類不會被抽到（改寫規則只有限傳說的；五種都沒候選時和開關關著的結果相同）；
  - 材料傾向不改招牌；
  - 開關關著：標了招牌的內容庫和原本的內容庫產出逐位元相同；
  - 縮等級保留招牌；沒標限傳說的改寫規則可以當招牌、現有改寫規則仍限傳說。
- `tests/content/test_equipment_content.py`：`test_rule_affix_must_be_legendary_only` 改成 `test_rule_affix_no_longer_requires_legendary_only`。

### 3.1 全量檢查

全部 5 項 commit 之後（`fee4b6165`）跑：

| 指令 | 結束碼 |
|---|---|
| `uv run python scripts/check.py --all` | 0（ruff、format、mypy、lint-imports、pytest、client install／typecheck／test、situation coverage 全部通過；已寫通過戳記） |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed；CLI 快照沒變） |

報告 commit 只改這份 `.md`。

## 4. 待 PM 決定

1. **70% 下限的解讀**：我照「招牌以外的點數 ≥（預算 − 招牌）× 70%；招牌以外什麼都沒放時不檢查」做。放得下、但只能放固定點數小詞條而到不了 70% 時，產生器會只出招牌（例：剩下的預算只夠一條固定點數、低於 70% 的詞條）。另一種解讀是「放得下就放，不看 70%」。要改的話只動 `item_budget._fill_problems` 與產生器的 `_enough`。
2. **現有詞條沒標招牌**：草案 D1 說現有 9 條第 9～11 類要補欄位，但規格要求既有資料序列化不變、D13 說內容第 10 步再清。所以這段一條都沒標；開關打開前要先由玩法 PM 標內容。
3. **招牌放在詞條最後**：為了保留「第 1 條是 build 詞條」的慣例。裝備卡「第一行放招牌」是 E6-b2 的顯示，那時依 `signature` 欄位排即可。
4. **招牌暫時不能重骰**：`affix_choices` 對招牌那一條回傳空，E6-a2 再接「同一種換另一條」。
5. **定價不看開關**：只要詞條標了招牌、物品有等級，就照 60% 計價（8.30 是規則，開關只管產生器）。類別豁免只給「帶招牌的稀有度、部位上的第 1 條招牌」。
6. **打造指定＋招牌**：開關打開後，打造指定的 build 詞條要放進剩下的 40%；放不下會照現有規則報「詞條預算放不下指定的詞條」。這屬於 E6-a2 的打造，這段沒改。
7. **工坊的提示範圍**：`signature_permille` 提示 300～900、權重 0～6，是我訂的初值。

## 5. 平衡疑慮（請 PM 轉玩法）

- 招牌 60% 之後剩下的預算很小（測試內容庫抽樣看到的，不是量測）：
  - 1 級稀有靴子剩 1.6 點，只有招牌；
  - 主手要剩 8 點才放得下技能強化（8 點），也就是物品等級 4 起；1～3 級的稀有、史詩主手放不下，退回一般詞條，「稀有起含 1 條技能強化」（8.21.6）在低等級做不到；
  - 6 級史詩主手剩 10.8 點，招牌以外是「技能強化 8 ＋ 條件命中 2.8」，其他詞條都很小。
- 這段沒試數值，只記下來。

## 開發 PM 驗收（2026-11-23）

**通過**，已合併進 main。`check.py --all` 0；slow parity／cli 0；442 招、78 場、census、產生器種子比對（6752 行）都 different=0；開關預設關、關著不取亂數。

- 待決裁定：
  1. 70% 下限解讀：先照實作（招牌以外的點數 ≥（預算 − 招牌）× 70%，什麼都沒放不檢查；放得下但不到 70% 只出招牌），轉玩法 PM 確認是否改「放得下就放」；開關關著，現在不影響結果。
  2. 現有詞條不標招牌：接受；開關打開前由玩法 PM 標內容（草案 D1、D13），記佇列。
  3. 招牌放詞條最後、卡片排序留 E6-b2：接受。
  4. 招牌暫不能重骰：接受，E6-a2 接。
  5. 定價不看開關：接受。
  6. 打造指定放進剩下的 40%：併 E6-a2。
  7. 工坊提示範圍初值：接受。
- 平衡疑慮（低等級剩餘預算小、主手 4 級前放不下技能強化）轉玩法 PM 記平衡待查。
