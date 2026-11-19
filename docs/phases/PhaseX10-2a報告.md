# X10-2a 報告：程式認得 `quantity_scale`（值先設 1，結果不變）

依據：`docs/phases/PhaseX10-2a計畫.md`、`docs/phases/PhaseX10-1報告.md`（第 6 節係數表、第 8 節待決與開發 PM 裁定）、`docs/phases/X10-影響盤點.md`、`docs/design/05-戰鬥.md` 5.4.1。
基準：開工前 `git merge main`（`a74f97218`）。沒改 `docs/design/`、`config/`；`content/` 只在 `rules/core.yaml` 加了 `quantity_scale: 1`。沒 push、沒跑全量、沒用 `-m ""`、沒試數值。

## 1. 交付與 commit

| # | 項目 | commit | 主要檔案 |
|---|---|---|---|
| 1 | `quantity_scale` 欄位＋換算腳本改用它防重跑 | `20af9d2bb` | `content/rules/core.yaml`、`content/rules.py`、`scripts/x10/rescale.py`、`scripts/x10/fields.yaml`、`tests/test_x10_rescale.py`、`tests/test_x10_scale.py`（新） |
| 2 | 引擎：骰面 × scale（d20 不乘）、寫死的 1 點下限 × scale | `4bddd49d9` | `engine/context.py`（`Ctx.roll_quantity`）、`engine/effects/handlers.py`、`engine/effects/world.py`、`engine/skills/primitives/numeric.py`、`engine/practice.py`、`engine/preview.py` |
| 3 | 預算：固定值 ÷ scale | `edcf24fc6` | `skillgen/budget.py`、`content/summons.py`（`summon_dpr`）、`skillgen/flash_ops.py`、`skillgen/options.py`、`content/skill_rules.py`、`scripts/x10/fields.yaml` |
| 4 | 組合器、LLM：取值步距與最低花費 | `004ef5f5d` | `skillgen/composer_parts.py`、`whiteboard.py`、`random_composer.py`、`proposal_numbers.py`、`flash_ops.py` |
| 5 | AI 評分：量類 ÷ scale | `0baaa7b67` | `engine/ai/utility/gains.py`、`scoring.py`、`skill_estimate.py`、`engine/ai/summon.py`、`gamble.py`、`zone.py`、`infuse.py`、`race.py`、`priority.py`、`scripts/x10/fields.yaml` |
| 6 | Python 預設值 | `988990a7f` | `content/rules.py`、`content/library/ruleset.py`、`content/world_encounters.py` |

### 各項做法

1. **欄位與標記**
   - `CoreRules.quantity_scale: Literal[1, 10] = 1`（舊紀錄沒有此欄位＝1）。放在 `ap_per_turn` 後面而不是第一個：`tests/cli/test_battle_cli.py` 會改內嵌規則包的「第一個整數欄位」測雜湊，放第一個會變成 2 而驗證失敗。
   - `rescale.py`：拿掉每檔首行註解（`MARKER`、`marked_files`）。新增 `current_scale()`、`scale_change()`：`apply()` 先檢查 `quantity_scale`，已經是 10 或找不到就整批拒絕；換算時把它 1 → 10，和其他欄位一起過「改寫後重新 parse」的驗證。
   - `fields.yaml`：`quantity_scale` 列 keep（腳本自己改）。
2. **引擎**
   - 擲骰：`Ctx.roll_quantity(sides)`＝`rng.roll(sides) × scale`。傷害（含爆骰、暴擊加骰、聖光雙效共用骰）、治療、護盾、物件傷害都走它；爆骰判斷看骰面本身。d20 檢定與命中都不經過它。
   - 預覽的 `dice_distribution(..., scale)` 同步，否則預覽的期望傷害會和實際差 10 倍。
   - 1 點下限：免死、分傷、靈魂連結留下的 HP，以及免死事件的「擋下量」、反噬的 HP 下限，都改成 `_hp_floor(ctx)`＝`quantity_scale`。測試模式的 `hold_standing` 同。
3. **預算**（點數單位不變）
   - `flat_bonus`、召喚物脈動 `heal_flat`、自爆 `flat`：÷ scale。
   - `summon_dpr` 加 `scale`：召喚物武器固定傷害與成長固定傷害 ÷ scale（預算與 AI 共用）。X10-1 表格沒列，但同樣是吃固定值的點數。
   - 法力、耐力代價：`mana × mana_per_point ÷ scale`、`stamina × mana_per_point ÷ (stamina_per_mana × scale)`。
   - 回復法力：`amount × restore_mana_point_permille ÷ (1000 × scale)`。
   - `mana_per_point`、`restore_mana_point_permille` 改成「每 `quantity_scale` 點」計價，數值不變、欄位格式不用改；清單從 `unit_change` 改列 keep。
   - `flash_ops` 以血支付：法力、耐力留 1 × scale，省下的折抵 ÷ scale。
   - `options.py` 的說明文字：倍率 1 時一字不改，10 時寫「法力每 10 點」。
4. **組合器、LLM**
   - `quantity_randint(rng, low, high, scale)`＝`rng.randint(⌈low/scale⌉, ⌊high/scale⌋) × scale`。倍率 1 時和原本的 `randint` 完全一樣，耗用的亂數也一樣；20～40 時只取 20、30、40，機率和換算前相同。
   - 用在主動技、被動、反應、白板的法力範圍，以及姿態法力。姿態每階 `+ (tier−1)` 改成 `× scale`。
   - 武器技「不花資源」那一檔的最低 1 耐力、LLM 提議補的最低花費：改成 1 × scale。
   - 回復法力的旋鈕階梯（`param_range`，只限 `restore_resource` 的 mana）：起點取到第一個 scale 的倍數，步距 × scale，換算後是 10、20…100。
   - 閃現「效果 +」的 `flat_bonus` 階梯：`range(scale, top+1, scale)`。
5. **AI 評分**（`ai_profiles.yaml` 不動）
   - 命中期望傷害（有用部分）、事件傷害、對友傷害、打掉的護盾、加的護盾、治療量、打掩護物的傷害、分傷折扣：÷ scale。
   - 技能成本：法力、耐力、HP 代價 ÷ scale；回復法力的加分 ÷ scale。
   - 召喚物：每輪傷害（`summon_dpr` ÷）、脈動護盾固定值、自爆固定值。
   - 失手反噬：武器固定值 ÷ scale。
   - 區域護盾的 `amount` ÷ scale。
   - 灌注存活率：`infuse_threat_damage` × scale 再和 HP 相加，結果等於「HP ÷ scale」。
   - 種族「回復」：缺口 ÷ scale。
   - `_restore_supports`：門檻改在換算前的單位比。
   - 骰子平均本來就是換算前的單位，不除。
   - `fields.yaml`：AI 那組 pending 全改列 keep，`infuse_threat_damage` 從 scale 改回 keep；工坊 AI 的 `hint_*` 也改 keep。統計：scale 1,838 個值（少了 `infuse_threat_damage`），pending 0、unit_change 0。
6. **Python 預設值**：選「從 content 讀」。
   - `quantity_scale` 不是 1 時，下列欄位若沒寫在內容檔（用了換算前單位的 Python 預設值），載入就報錯，倍率 1 時照舊：
     - `CoreRules`：`resources.class_base／base／stamina_regen`、`attribute_perks.base／step`、`summon_growth` 四個量類；
     - `Ruleset`：`forms` 的四個維持費。
   - 現有內容都有寫。
   - `ArmorMods.min_total／max_total` 直接拿掉預設值：唯一的使用處（灰燼之心）和測試都有寫。
   - `infuse_threat_damage`：依裁定 2 是 AI 的單位，不 ×10，由第 5 項在引擎裡乘回。

## 2. 不變比對（`quantity_scale: 1`）

- 範圍共 78 場：
  - 15 張正式地圖 × 種子 1、7；
  - `open_plain` 種子 3 × 8 個 build（fire、storm、tank、healer、summoner、gambler、bomber、warlock）；
  - 4 張頭目圖（`archetype: boss` 的 `bandit_lair`、`cloud_summit`、`molten_heart_pit`、`rift_gate`）× 種子 3～12。
- 比對方式：基準是開工時的 `a74f97218`，比對 `--log-json` 整份（設定、動作、事件、最終狀態、指令）與文字輸出。
  - 排除 `ruleset_hash`，因為規則包多了一個欄位。
  - 排除內嵌規則包的 `quantity_scale` 鍵。
  - 文字輸出排除「已寫入戰鬥紀錄」那一行。
- 結果：第 2～6 項每個 commit 各跑一次，都是 **`battles=78 events=27376 different=0`**。
- 第 1 項只加欄位與改腳本，沒有另外跑戰鬥；它的 tests/cli 和 slow parity 都過了，第 2 項那次比對也包含它。
- 快照、夾具沒有變動：`tests/cli` 的輸出快照、`test_refactor_parity`（slow）、OpenAPI 快照都通過，也沒有重產。

## 3. ×10 試跑（沒有 commit，已還原）

- 做法：
  - 在 worktree 跑 `uv run python scripts/x10/rescale.py`：換算 1,838 筆、515 個檔，`quantity_scale` 變成 10。
  - 再跑一次 rescale，被拒絕（結束碼 1，「已經換算過」）。
  - `trpg content check` 結束碼 0，434 個技能的預算驗證全過。
  - 跑同一組 78 場，跑完 `git restore content`，`git status` 是乾淨的。
- 結果：

| 指標 | ×1 | ×10 |
|---|---|---|
| 我方勝 / 敵方勝 | 44 / 34 | 47 / 31 |
| 勝方相同 | — | 63 / 78 |
| 勝方與輪數都相同 | — | 44 / 78 |
| 平均輪數 | 4.49 | 4.29 |
| 輪數差（×10 − ×1） | — | −3：1 場、−2：3、−1：15、0：50、+1：9 |
| 動作序列完全相同 | — | 5 / 78 |
| 每個單位 HP 比例完全相同 | — | 4 / 78 |

- **差異的原因都是捨去**，沒有發現 AI 或引擎沒換到的地方。
- 檢查方法：逐場找「第一個不是剛好 ×10 的數字」和「事件流第一次分岔（事件種類、單位、目標、位置不同）」的位置。
- 78 場的分岔都發生在第一個捨去差異**之後**；沒有一場是在狀態還是精確 ×10 時就做了不同決定。
- 第一個捨去差異出在兩處：
  - **法力上限 ×1400‰**（61 場）：例如基礎 24 × 1.4 ＝ 33.6，×1 時四捨五入成 34，×10 時是 336。換算後法力上限比換算前略低（33.6 對 34），有幾場因此差一點放不出法術、改用普攻或別的技能，從第 1 輪就分岔。
  - **傷害倍率的 ‰ 捨去**（17 場，含 2 場打物件）：例如 ×1 打出 2、×10 打出 23（＝2.3）。新單位的尾數比較細，傷害普遍比「舊值 ×10」略高。
- 這兩項就是 X10-1 報告第 9 節預告的「捨去誤差」。我方勝率略升（44 → 47）、輪數略短，和傷害偏高的方向一致。
- **沒有修任何數值。**

## 4. 檢查（最後一個程式 commit `988990a7f`，報告 commit 只加這份文件）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（全專案） | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（982 passed） |
| `pytest -n 8 tests/cli tests/test_x10_*.py tests/world/test_ashen_waste.py tests/content/test_x10_caps.py tests/engine/test_ruleset_hash.py` | 0（245 passed） |
| `pytest -n 8 tests/content tests/world -k "rules or form or encounter or resource or summon or ruleset or tuning"` | 0（521 passed） |
| `pytest tests/api/test_openapi_snapshot.py` | 0 |
| `rescale.py --check` | 0 |
| 78 場不變比對 | different=0 |

各項 commit 時另外跑過的相關測試：

| 項目 | 測試 | 結果 |
|---|---|---|
| 2 | `tests/engine` 的 preview、combat、免死／分傷／測試模式 | 全過 |
| 3 | `tests/skillgen -k "budget or flash or blood or option or summon"` | 1230 passed |
| 4 | `tests/skillgen tests/llm -k "compos or whiteboard or random or proposal or flash or knob or level_up"` | 2530 passed |
| 5 | `tests/engine -k "ai or gamble or summon or zone or infuse or race or skill_estimate"` | 1439 passed |

每一項的 commit 都跑過 slow parity 和 cli，結束碼 0。

新增的單元測試（`tests/test_x10_scale.py`，25 個）：
- 骰面 ×scale：傷害、治療、護盾。
- d20 不乘：命中的自然骰相同，傷害骰是 10 的倍數。
- 免死留下的 HP ＝ 1 × scale。
- 預覽分布 ×scale。
- **預算換算前後點數相同**：內容裡 343 招非召喚技能，法力、耐力、`flat_bonus`、回復法力都 ×10，在 scale 10 的規則下，總點數與代價折抵逐招相同。
- `summon_dpr`。
- 法力範圍步距：200 個種子，×10 的結果剛好是 ×1 的 10 倍。
- 回復法力的階梯、閃現 `flat_bonus` 的階梯、最低花費。
- `_useful_damage`、灌注存活率。
- scale 10 時缺量類欄位會報錯；`ArmorMods` 沒有預設值。

## 5. 待 PM 決定

1. **「外加 4 張頭目圖」的解讀**：4 張頭目圖本來就在 15 張正式地圖裡，所以解讀成「這 4 張（`archetype: boss`）再加種子 3～12」，共 40 場，同 BAL-21a 的做法。另外 `open_plain` 的 8 個 build 是我挑的（X10-1 報告沒寫是哪 8 個）。要換範圍告訴我。
2. **×10 後法力上限的捨去**：`mana_cap_permille` 1400 讓法力上限從「四捨五入到整數」變成「多一位小數」，換算後普遍少 0.4 點（換算前單位）。61 場的第一個差異都來自這裡。這是數值、不是程式問題，記在這裡給 X10-2b 回歸參考，沒有動。
3. **其他寫死的 1 沒改**：規格只點名 `effects/handlers.py` 和 `practice.py`。
   - `CoreRules.mana_cost` 的「打折後至少 1 法力」；
   - `max_hp_for` 的「HP 至少 1」；
   - `minimal_filler` 給 `restore_resource.amount` 補的最小值 1（來自 `skill_primitives.yaml` 的 min，清單列 keep）。
   - 這三處照原樣。要不要也 × scale？
4. **反噬下限加了 `max(0, …)`**：×10 時 HP 可能低於 10，`hp − 10 ＋ 護盾` 會變負數，負的反噬會變成補血。倍率 1 時只有 HP ≤ 0 且沒有護盾才會碰到，不變比對 different=0。
5. **AI 的「量類」也包含法力、耐力**：裁定 2 寫的是「傷害、HP、護盾等」，但 5.4.1 規定法力、耐力也 ×10，所以技能成本裡的法力、耐力，以及回復法力的加分也一起除，否則換算後 AI 會覺得法術貴了 10 倍。
6. **超出 X10-1 第 6 節清單的預算點**：召喚物武器的固定傷害（`summon_dpr`）也 ÷ scale；閃現「以血支付」留下的資源改成 1 × scale。
7. **組合器之外也換了步距**：
   - 閃現「效果 +」的 `flat_bonus` 階梯（`trigger_flat_bonus` 換算後是 10）；
   - 回復法力的旋鈕階梯（`skill_primitives.yaml` 的 amount min 1、max 換算後 100）。
   - 都改成步距 × scale，起點取 10，讓生成分布和換算前一樣。若 X10-2b 想要 1～100 的細刻度，再改回步距 1。
8. **Python 預設值選了「從 content 讀」**：scale 10 時缺量類欄位直接報錯，沒有在 Python 裡 × scale（pydantic 的預設值拿不到 core 的倍率）。`ArmorMods` 的上下限直接改成必填。若希望預設值自動 × scale，要另外在規則包層做一次補值。
9. **`skill_budget.yaml` 的註解還寫「法力每點」**：只有 `core.yaml` 這個內容檔有改。註解在換算後的意思是「每 quantity_scale 點」，X10-2b 換算時可以順手改。

## 6. 平衡疑慮

- 見第 3 節：換算後傷害略高、法力上限略低，我方勝率在這 78 場從 44 升到 47。樣本小，X10-2b 回歸要用正式模擬確認。

## 開發 PM 裁定（2026-11-20）

合併：`Merge X10-2a`（--no-ff）。合併後 ruff、mypy、`trpg content check` 都是 0。

待決 9 件：
1. 接受，範圍照這樣，X10-2b 沿用同一組 78 場。
2. 接受，不動。捨去造成的差異（我方勝 44→47、勝方相同 63/78）是 5.4.1「尾數更細」的結果，不是漏換。已轉玩法 PM 記進平衡待查，由使用者在工坊調。
3. `mana_cost` 打折後的下限、`minimal_filler` 的回復法力下限改成 × scale；`max_hp_for` 的 HP 至少 1 照舊（那是「活著」的下限，不是量）。X10-2b 一起做。
4. 接受。
5. 接受。法力、耐力也是量類，照 5.4.1 一起除，裁定 2 的「等」包含它們。
6. 接受。
7. 接受。步距 × scale，生成的分布不變。
8. 接受。
9. X10-2b 一起改。
