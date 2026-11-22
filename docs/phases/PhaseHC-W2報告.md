# Phase HC-W2 報告：工坊開放 2（形狀查表、形態、裝備規則、物品生成）

依據：`docs/phases/PhaseHC-W2計畫.md`；參考做法 `PhaseHC-B計畫.md`、`PhaseHC-B報告.md`（第 3 項建議與開發 PM 裁定 3）。
基準：main `161b97693`。分支 `worktree-agent-a7da31e1b4440f12b`，沒 push。
數字一律照現值搬或照現值開，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 形狀的查表倍率 | `93cccab7c` | 錐形、十字、環形、連鎖的查表搬到 `skill_budget.yaml` 的 `shape_budget.<id>.by_value.<值>`（連鎖另有 `non_power_by_value.<值>`）；載入檢查搬家；工坊「形狀」組多 17 格 |
| 2 形態、裝備規則、物品生成開進工坊 | `1200d2cf1` | 三個新的表種類 `forms`、`equipment`、`item_gen`；中文名、說明、分組；前端載入；截圖 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試目錄、逐招預算比對與 78 場戰鬥比對。

## 2. 搬家與開放的欄位表

### 2.1 形狀查表（第 1 項）

「現在在哪」都是 `content/skill_budget.yaml`（＝工坊「技能預算表」的「形狀」組）。

| 數值 | 原本在哪 | 現在在哪 | 工坊 |
|---|---|---|---|
| 錐形依長度 size 的倍率 2／3／4（1300／1600／2000‰） | `skill_shapes.yaml` 的 `cone.budget.by_value_permille` | `shape_budget.cone.by_value.2～4` | 開（「錐形長度 N」） |
| 十字依臂長 arm 的倍率 1／2（1800／2000‰） | `cross.budget.by_value_permille` | `shape_budget.cross.by_value.1～2` | 開（「十字臂長 N」） |
| 環形依半徑 radius 的倍率 1／2（1800／2200‰） | `ring.budget.by_value_permille` | `shape_budget.ring.by_value.1～2` | 開（「環形半徑 N」） |
| 連鎖依跳數 jumps 的倍率 1／2／3（1188／1313／1375‰，威力效果） | `chain.budget.by_value_permille` | `shape_budget.chain.by_value.1～3` | 開（「連鎖跳 N 次（傷害、治療、護盾）」） |
| 連鎖的非威力倍率 1／2／3（1250／1500／1750‰） | `chain.budget.non_power_by_value_permille` | `shape_budget.chain.non_power_by_value.1～3` | 開（「連鎖跳 N 次（狀態等非威力）」） |
| 這四種形狀的基礎值 `base_permille`（1000／1800／1000／1000） | HC-B 已在 `shape_budget` | 不動 | 開；說明寫清楚只在沒填參數時用：十字的是陷阱的十字範圍（陷阱不填臂長）在用；錐形、環形、連鎖目前沒有招會用到，說明直接寫「改這格通常沒有效果」 |
| `param`（看哪個參數）、連鎖的 `power_primitives` | `skill_shapes.yaml` | 不動（結構） | 不開 |

程式面：
- `ShapePrice`（`skill_rules.py`）多 `by_value`、`non_power_by_value`；`ShapeBudget`（`skills/shapes.py`）只剩 `param`、`power_primitives`，`permille_for` 改由呼叫端傳表。不留兩份。
- 原本在 `ShapeBudget`／`ShapeDef` 的檢查（表要涵蓋參數整個範圍、要有 `param`、表不可為空、非威力表要有 `power_primitives`）搬到 `shape_budget_problems`（載入時）；`ShapeDef.budget_param_values()` 給要涵蓋的參數值。
- `scripts/x10/fields.yaml` 補 `shape_budget.*.*.*`（keep）。

### 2.2 形態（`forms.yaml`，新表「形態」，59 格）

| 分組 | 開的欄位 | 說明 |
|---|---|---|
| 共通 | `upkeep_stamina`、`upkeep_mana`、`stance_upkeep_stamina`、`stance_upkeep_mana`、`cooldown` | 維持費與冷卻 |
| 每個形態一組（「形態「熊」」…10 組） | 天生武器：`dice`、`range`、`damage_permille`、`traits.strikes／knockback／reach／bleed／backstab_crit`、`charge.size`；形態中：`effects.max_hp_permille／defense_permille／move／heal_permille／flat_height`、`effects.damage_taken[*].permille`（標籤帶元素，例「受到神聖傷害的倍率」）；進入時：`entry.shield_max_hp_permille／shield_duration／heal_max_hp_permille／next_attack_hit／next_attack_crit／move／conceal／collision_permille`、`entry.burst.radius／dice`、`entry.heal_adjacent.dice／attr_permille` | 除了天生武器骰與受傷倍率，其他都 `existing_only`（只展開已寫的；沒寫＝那個形態沒有那個機制，加上去屬結構） |
| 不開 | `id`、`name_zh`、`category`、`look`、`attrs`、`element`、`element_choices`、天生武器名、`magnitude_permille`（檔裡沒寫，由技能幅度推） | 結構、文字、外觀 |

### 2.3 裝備規則（`rules/equipment.yaml`，新表「裝備規則」，12 格）

| 分組 | 開的欄位 |
|---|---|
| 同名詞條的遞減 | `diminishing_permille[0～2]`（「同名詞條第 N 條的效果」；schema 照擋「第 1 條要 1000、不遞增」） |
| 硬上限 | `max_affixes_per_item`、`caps.damage_bonus_permille／element_resist_permille／ap_gain_per_round／cooldown_min／crit_range_min／move_bonus／cost_affixes／rule_affixes` |
| 不開 | `caps.damage_reduction_permille`：載入時要等於 `1000 − core.yaml 的 element_mod_floor_permille`，而那一格沒開，單獨改一定驗證失敗（待決 2） |

### 2.4 物品生成（`item_gen.yaml`，新表「物品生成」，83 格）

| 分組 | 開的欄位 |
|---|---|
| 稀有度 | `rarity_weights.*`（5）、`rarities.<普通～史詩>.min_affixes／max_affixes`（8） |
| 預算 | `total_budget[*].total`（標籤「全身預算「等級 N」：總點數」）、`min_fill_permille`、`min_affix_points`、`base_strength.fallback_level` |
| 部位比例 | `slot_permille.*`（8） |
| 詞條佔比 | `affix_permille.*`（8） |
| 數值詞條的單價 | `stat_prices.<屬性、最大 HP、元素抗性、防禦、移動>.points／per`（10） |
| 條件詞條 | `conditional_prices.<命中、防禦、傷害>.points／per`（6）、`condition_rates_permille.*`（3） |
| 其他類別的點數 | `category_points.*`（8）、`weapon_element_points`、`trigger_limit_permille`、`weapon_attribute_preference_permille` |
| 代價型詞條 | `cost_prices.*.points／per`（14）、`cost_min_points` |
| 基礎加成 | `base_bonus.points／permille` |
| 戰後掉落 | `offer_size` |
| 不開 | `total_budget[*].level`（表的鍵）、`conditional_rates`（成立率分類，文字）、`rarities.*.categories`／`required`、`required_picks`、`unique_affixes`、`held_back_affixes`（清單）、`max_attempts`、`offer_attempts`（程式的重試次數，待決 3） |

程式面：
- `TARGET_MODELS`／`TABLE_KINDS`／`TuningTarget.kind` 多三種；`TABLE_NAMES_ZH`、`TABLE_NOTES_ZH`（表單頂端的提示）各一筆。
- 三個檔都是 `load_library` 從內容資料夾讀，草稿看得到，**不必**像 HC-B 搬家。
- 白名單檢查兩處修正：對照表的鍵是 `type` 別名（`SlotType`、`Rarity` 等）時照樣認得；路徑段如果是對照表的**鍵**（`slot_permille.weapon` 的部位 `weapon`）不算禁止的欄位名（禁止的 `weapon` 欄位照擋）。
- 標籤：清單項目前綴多「形態「熊」：」「全身預算「等級 5」：」；`{element}` 換成元素中文。分組：形態表依形態分組（同頭目部位的做法）。
- 前端：`client.ts` 的種類、`TuningScreen.tsx` 載入三張表（放在「規則與預算」那一欄）。
- `scripts/x10/fields.yaml`：三張表的建議範圍歸類（維持費、屬性與 HP 的「一個單位」跟著量類 ×10，其他不變）。
- API 形狀沒變：`export_openapi.py`、`gen:api` 重跑後 `client/openapi.json`、`schema.d.ts` 沒有差異。
- 白名單合計 14 類對象、828 個欄位。

### 2.5 寫死數值清單

`classify.py --check` 是 0。這段搬的都是 YAML → YAML（沒有 Python 寫死數字被搬走），所以清單上沒有規則要從 todo 改成 done（待決 4）。`_part_group` 改寫時順手拿掉一個 `# noqa: PLR2004`。

## 3. 兩種比對

### 3.1 逐招預算
- 腳本：基準（`161b97693`）把內建 434 招的 `skill_budget` 完整結果（總點數、raw、可用預算、比例、每個效果的點數／形狀倍率／說明、複合段、變奏）存成 JSON，之後重算逐招比。
- 結果：第 1 項後、第 2 項後各一次，都是 **`skills=434 same=434 different=0`**。

### 3.2 戰鬥不變比對（78 場）
- 基準：`git archive 161b97693 src content`，`PYTHONPATH`、`TRPG_CONTENT_DIR` 指向基準（腳本印出載入的 `trpg` 在基準資料夾）。
- 範圍：15 張正式地圖 × 種子 1、7；`open_plain` 種子 3 × 8 個 build（`build_push`～`build_healer`）；4 張頭目圖（`bandit_lair`、`cloud_summit`、`molten_heart_pit`、`rift_gate`）× 種子 3～12。
- 比對 `--log-json` 整份（排除 `ruleset_hash`、內嵌規則包）＋文字輸出。
- 結果：第 1 項後、最後一個程式 commit 後各一次，都是 **`battles=78 different=0`**（我的腳本把巢狀的 events 也數進去，總數 30240，和 HC-B 報告的 26446 算法不同，兩邊用同一支腳本）。
- `ruleset_hash` 有變：內嵌規則包的形狀拿掉了 `by_value_permille`、`non_power_by_value_permille`。

## 4. 工坊測試

`tests/api/tuning/test_workshop_open_hcw2.py`（13 項）：
- 形狀組：四種形狀的每一格查表都開、值對、在「形狀」組、標籤帶參數值。
- 改錐形查表一格（內建錐形招最多的長度，×2）：同長度的錐形招預算比例變高、可用預算不變；其他長度的錐形招與非錐形招不變。
- 三張新表：列在清單上、每格值對、標籤沒有未換掉的 `{…}`、說明有「越…」、都有分組；每個檔的整數不是開了就是在「不開」清單；標籤帶形態名、元素、等級。
- 草稿：形態 `upkeep_mana`、裝備 `caps.move_bonus`、物品生成 `rarity_weights.common` 各改一格 → 能存（`put_draft`）、能驗證（`check` 為 ok）、草稿內容庫讀到新值；錯的草稿（遞減第 1 條改成 999）驗證不過。

改了的既有測試：`test_rules_budget_bs1`（`TABLE_KINDS` 多三個）、`test_budget_table_hcb`（「不開」清單拿掉四種形狀）、`test_skill_rules_content`（查表的檢查改成新的 `shape_budget_problems` 測試）。

## 5. 截圖（`docs/art/shots/hc-w2/`）

- `forms-table.jpg`：形態表（展開「共通」與「形態「熊」」，其他 9 組收合）。
- `equipment-table.jpg`：裝備規則（兩組，預設展開）。
- `item-gen-table.jpg`：物品生成（10 組，展開「預算」）。
- `budget-shape-group-open.jpg`：技能預算表展開「形狀」組（30 格，可見錐形、十字的查表）。
- 伺服器 `trpg serve --port 9173`（`TRPG_TUNING=1`，存檔、帳號在暫存區），內建瀏覽器、網址帶 `?mute=1&dev=1`。拍完已停掉伺服器（自己開的 PID），埠沒在聽；分頁已關。

## 6. 檢查（最後一個程式 commit `1200d2cf1`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy src tests` | 0 |
| `lint-imports` | 0（14 kept） |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| 逐招預算比對 | 0（different=0） |
| 78 場戰鬥比對 | 0（different=0） |
| `pnpm -C client typecheck` | 0 |
| `pnpm -C client test --run` | 0（393 檔、4820 項） |
| `pnpm -C client build` | 0 |

測試目錄（一次一組、各自 `-n 8`，`tests/llm` 與 `tests/skillgen` 沒同時跑）：

| 檢查 | 結束碼 |
|---|---|
| `pytest tests/api -n 8`（第一次） | 卡死，開發 PM 停掉（見下） |
| `pytest tests/api -n 8 -p no:cacheprovider -o console_output_style=classic -v`（重跑） | 0（1368 passed, 1 skipped，4 分 15 秒） |
| `pytest tests/bot -n 8` | 0（67） |
| `pytest tests/cli -n 8` | 0（148） |
| `pytest tests/content -n 8` | 0（3168） |
| `pytest tests/engine -n 8` | 0（5120） |
| `pytest tests/llm -n 8` | 0（495） |
| `pytest tests/narrative -n 8` | 0（479） |
| `pytest tests/roguelite -n 8` | 0（279） |
| `pytest tests/server -n 8` | 0（77） |
| `pytest tests/shared -n 8` | 0（76） |
| `pytest tests/sim -n 8` | 0（180） |
| `pytest tests/skillgen -n 8` | 0（4637 passed, 7 skipped） |
| `pytest tests/world -n 8` | 0（1328） |
| `pytest tests/test_*.py -n 8` | 0（256） |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979） |

**`tests/api` 第一次卡死**：交件前的整套（18:40 開始，各目錄依序跑）第一組 `tests/api -n 8` 跑到約 99%（最後一行點只差最後幾項、前面沒有失敗）後不再前進，掛了 2 小時 42 分，8 個 worker 只剩 2 個；開發 PM 把那棵程序樹停掉，輸出最後是 `[gw5] node down: Not properly terminated`。那次是點號輸出，看不出卡在哪個測試。其他目錄照樣跑完（上表）。之後照開發 PM 指示單獨重跑 `tests/api -n 8 -p no:cacheprovider -o console_output_style=classic -v`，4 分 15 秒跑完、全過，沒有重現卡死。同一段工作裡 `tests/api` 另外整組跑過兩次（第 1 項前 127 秒、第 2 項前 157 秒），都正常結束。卡死的原因沒有查到（待決 8）。

## 7. 待 PM 決定

1. **四種查表形狀的基礎值也開了**：規格說「以及它們的基礎值」。十字的基礎值給陷阱的十字範圍用（灰燼地雷、毒池陷阱），是有效的；錐形、環形、連鎖的基礎值目前沒有招用到（內建、生成的招都會填參數），說明直接寫「改這格通常沒有效果」。要不要乾脆不開這三格。
2. **裝備的總減傷上限沒開**：`caps.damage_reduction_permille` 要等於 `1000 − core.yaml 的 element_mod_floor_permille`（載入時檢查），核心規則那一格沒開，單獨開只會驗證失敗。要開的話兩格一起開（同一張草稿改兩個檔），或把其中一個改成由另一個推。
3. **物品生成沒開的數字**：`max_attempts`、`offer_attempts`（產生器亂數重試次數，程式參數）與 `total_budget` 的等級（表的鍵）。照最保守沒開；戰後幾選一（`offer_size`）有開。
4. **寫死數值清單沒有項目改 done**：規格寫「搬過的項目在清單上改成 done」，但這段搬的都是 YAML 之間（查表從形狀表搬到預算表；三個檔本來就在 `content/`），`classes.yaml` 裡沒有對應的 todo 規則。
5. **形態欄位都是「只展開已寫的」**：天生武器骰與受傷倍率以外，沒寫的機制（例：熊沒有隱蔽）不能從工坊加。若要能加，屬結構改動，另排。
6. **新開欄位的建議範圍**：照 HC-B 裁定 8，大致是現值的一半到兩倍（0 或很小的值另給合理範圍），只提示不擋；schema 的上下限照擋，說明裡寫「只能 X～Y」。
7. **新表的欄位畫面沒有顯示「允許範圍」**（`limit_min／limit_max`）：只有說明文字寫 schema 範圍；超出時驗證會擋並列出錯誤。要在畫面顯示，`field_limits` 要多認這三張表。
8. **`tests/api -n 8` 偶發卡死**（第 6 節）：重跑（加 `-v`）沒有重現，所以不知道是哪個測試。這次改動的測試在重跑裡都過了。要不要另開一段查（例如每次都用 `-v` 跑，下次卡住就看得到名稱），請 PM 決定。

## 開發 PM 裁定（2026-11-21）

通過，已用 --no-ff 合併。逐招預算比對（434 招）和 78 場戰鬥比對都是 different=0。

待決八件：
1. **錐形、環形、連鎖的基礎值**：留著。使用者要的是能調的都看得到。說明文字要寫「目前沒有招用到，改了暫時沒效果」，併進 HC-6（文字）。
2. **總減傷上限**：併進 HC-4b，和核心規則的元素修正下限一起開，驗證時兩格一起看。
3. **重試次數和等級鍵不開**：同意。重試次數是程式行為，等級鍵是結構。
4. **清單沒有項目可改成 done**：知道了。
5. **形態只展開已經寫的機制**：同意。
6. **建議範圍取現值的一半到兩倍，只提示不擋**：同意，和 HC-B 一樣。
7. **允許範圍只寫在說明文字裡**：先這樣。之後若要把範圍顯示在畫面上，交給美術 PM 一起看。
8. **`tests/api -n 8` 偶發卡死**：使用者已決定做 QF-3a（看門狗加查 worker 死因），下一段就做。
