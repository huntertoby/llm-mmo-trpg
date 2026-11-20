# Phase HC-4a 報告：content schema 數字重新歸類，戰鬥核心先搬

依據：`docs/phases/PhaseHC-4a計畫.md`；`寫死數值-清單.md` HC-4 節、`PhaseHC-1報告.md` 開發 PM 裁定 2、`PhaseHC-2報告.md` 裁定 1、2。
基準：開工時 `git merge main`（`6c887ed7b`）。分支 `worktree-agent-aec9f544d2f27360e`，沒 push。
沒改 `client/`、`src/trpg/api/`、`classes.yaml` 的 ts 區、`docs/design/`、`config/`。沒跑全量、沒用 `-m ""`、沒試數值。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 新增 `guard` 類、重新歸類 content 的數字 | `d7ba43651` | `classify.py`、`classes.yaml`（py 區）、涵蓋測試、重產清單 |
| 2 戰鬥核心搬家 | `5efe8fc86` | 預設值改必填、頭目部位／階段的規則型上下限搬到 `core.yaml`、工坊欄位 |
| 報告 | 本 commit | |

每個 commit 前都跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試；第 2 項另跑 78 場比對與所有目錄的非 slow 測試。

## 2. 第 1 項：`guard` 類與重新歸類

### 2.1 工具
- `scripts/hardcoded/classify.py`：`CLASSES` 加 `guard`；和 const、layout 一樣不用搬，`status` 一定是 `done`（寫 `todo` 會報錯）。清單第 4 節改名「不搬的規則（const／layout／guard）」。
- `classes.yaml` 開頭說明加 `guard` 的定義與判斷原則。
- `tests/test_hardcoded_scan.py`：status 檢查認得 `guard`；壞規則多一例（`guard` 寫 `todo`）；抽查改成 `MAX_ATTRIBUTE`、`_MAX_DICE_COUNT` 是 guard，`max_elements_dual`、`ap_cost` 是 config。

### 2.2 怎麼判斷（照 HC-1 裁定 2）
- **預設值**（`Field(default)`、類別屬性、dict 預設、函式預設）：照舊 config（內容沒寫、靠預設值生效的）。
- **上下限**（`le`、`ge`、`min_length`、`max_length`）：
  - 規則型＝設計文件寫成規則、或技能／生成器／LLM 都要遵守的上下限 → **config**。
  - 只擋手寫、工坊、LLM 填出離譜值的（射程、半徑、回合、‰ 上限、清單長度、字數、地圖尺寸）→ **guard**。
  - 拿不準時歸 config（保守），留給 HC-4b～d 逐檔再看。
- **只拿來當護欄的模組常數**（`_MAX_DICE_COUNT`、`GIANT_FOOTPRINTS`、`MIN_COMBO_N`、`_MAX_ATTRS`、`_MAX_MELEE_RANGE`、`_ROLE_HP_RANGE`、`MAX_MAGNITUDE`、字數上限等，與 `WeatherDef._mods` 的 −1000 檢查）→ guard。
- `MAX_ATTRIBUTE`（999）照 HC-2 裁定 1 改判 guard（規則 id 改成 `py-guard-max-attribute`）。
- 命中表的數學（`compute_hit_thresholds` 的 ln 2、`_DECIMAL_PRECISION`）與 `weapon_attr_examples_zh` 的範例列數 → const（見待決 2）。
- `content/audio.py` 的上下限照 HC-1 留 const（音效合成參數）。

規則型、留 config 的上下限（第 1 項後 40 筆、含同欄位的預設值 4 筆；`py-content-rule-bounds*`）：
- 組合器的 AP 1～3（`CostStep.ap`、`WhiteboardRules` 四個 ap_cost）；
- 願望的關鍵字數、元素數（「最多 2 個元素」）、效果數（`WishTagRules`）；
- 預算表依回合查表的長度（`obstacle／inscribe／shield_duration_permille`、`wind_spread_permille`）；
- 技能：條件數（`ConditionSpec.any_of`）、修正幅度（`ModifierChange` 8 項）、階級與等階（`SkillDef.tier`、`rank`）、自身狀態代價的回合（`SelfStatusCost.duration`）、源力代價（`SkillCost.source`）、群召數（`SummonEvolution.count_number`）；
- 大世界：解法線索數（`SolutionDef.threads`）、方法的屬性數（`MethodDef.attributes`）；
- 頭目部位的破壞效果數（`BossPart.on_break`，第 2 項已搬）。

### 2.3 重新歸類後的筆數（`classify.py --stats`；基準＝`6c887ed7b` 的 classes.yaml）

| | config | scale | const | text | layout | guard | 合計 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 後端 基準 | 1409 | 39 | 8827 | 197 | 0 | 0 | 10472 |
| 後端 第 1 項後 | 1035 | 38 | 8833 | 197 | 0 | 369 | 10472 |
| 後端 第 2 項後 | **966** | 38 | 8843 | 196 | 0 | **369** | 10412 |
| 前端（沒動） | 56 | 0 | 5439 | 99 | 54752 | 0 | 60346 |

- content 的 config：984 → 610（第 1 項：368 筆改 guard、6 筆改 const）→ **541**（第 2 項搬走 69 筆）。
- guard 369 筆＝content 的上下限 337＋護欄常數 31＋`MAX_ATTRIBUTE` 1。
- 第 2 項後後端合計少 60 筆：拿掉的預設值與常數不再出現在原始碼；const 多 10 筆是新 docstring（`py-docstring`）。
- `--unused`：content 有 6 條逐檔 config 規則在第 1 項後變成 0 筆（loader、skills/conditions、skills/effects、ui_wait、workshop、world_enemies：數字全是護欄）；第 2 項後戰鬥核心 6 檔的規則與 `py-content-rule-bounds-boss-parts` 也是 0 筆（已改 done）。都留著接之後新寫的數字，沒刪。

## 3. 第 2 項：戰鬥核心搬家

範圍：`rules.py`、`battle.py`、`forms.py`、`parts.py`、`equipment.py`、`item_budget.py`。第 1 項後這 6 檔還有 config 73 筆，搬完剩 **4 筆**（`CoreRules._check_tier_budget` 的 1～5，見待決 3）。

### 3.1 預設值改必填（內容檔都有寫，值不變）
- `CoreRules`（32）：party／elite_ap_per_turn、miss_refund_min_cost、max_displace_distance、collision_damage_dice、consume_status_max_scale、topple_length、topple_damage_dice、teleport 兩個抵抗加成、chain_falloff／floor、pierce_behind、explode_max、scale_cap_max、backstab_hit_bonus、ambush_hit_bonus、far_distance、revive_landing_radius、shield_guard／formation_hit_penalty、variant_max_by_rarity、max_trigger_depth、trap_trace_radius、source_max、summon_limit_per_owner、summon_hard_cap、summon_max_duration、boss_summon_damage_permille、zone／rune_limit_per_owner、rune_default／max_rounds、legendary_timed_rounds；`wind` 本身也改必填。
- `WindRules.collision_permille`。
- `EquipmentCaps` 6 個、`EquipmentRules.diminishing_permille`、`max_affixes_per_item`；`EquipmentRules.caps`、`Ruleset.equipment` 也改必填（原本是空物件預設）。
- `ItemGenRules` 的 max_attempts、offer_size、offer_attempts。
- `FormTable.cooldown`、`NaturalCharge.size`、`EntryHealAdjacent.attr_permille`。
- `BossPart.hp_permille`（6 個部位都有寫 200）。
- `FormationSpec.range`、`WardSpec.range`、`TotemSpec.duration`、`SummonSnare.duration`、`PhaseGrowSurface.max_rows`、`UnitTemplate.speed`（166 個單位範本都有寫）。

### 3.2 「有某欄才用到」的預設值：改成可省略、用到時必填
這 4 個欄位只在旁邊某欄有值時才有意義，有些內容沒寫（因為用不到）。照字面改必填就得在 18 處寫進用不到的值，所以改成 `int | None`、用到時必填（解讀，見待決 1）：

| 欄位 | 何時必填 | 補寫進內容的 |
|---|---|---|
| `FormEntry.shield_duration` | 有 `shield_max_hp_permille` | `forms.yaml` 熊、龍各補 `shield_duration: 2`（原本靠預設） |
| `SummonInfusion.duration` | 有 `status` | 不用補（3 個帶狀態的都有寫） |
| `SummonHitRule.duration` | 有 `status` | 不用補（鷹隼、冰靈有寫） |
| `SummonHitRule.chain_permille` | `chain_targets` > 0 | 不用補（雷靈有寫） |

- 用到的地方（`engine/forms.py`、`engine/weapon_traits.py`、`skillgen/budget.py`、`narrative/summon_info.py`）加 `assert … is not None`，說明是 schema 保證的。

### 3.3 規則型上下限搬到 `rules/core.yaml`
05 5.12.2 與 09 9.6.8 寫成規則的 6 個數字：

```yaml
boss_parts:                   # 05 5.12.2
  count_min: 2                # 每隻頭目 2～4 個部位（第 1 點）
  count_max: 4
  hp_total_max_permille: 600  # 部位血量加總上限（第 3 點，數值工坊可調）
  break_effects_max: 2        # 每個部位最多幾種破壞效果（第 7 點）
boss_phases:                  # 開場階段＋1～3 次轉換
  count_min: 2
  count_max: 4
```

- schema：`parts.py` 新增 `BossPartRules`、`battle.py` 新增 `BossPhaseRules`，`CoreRules.boss_parts`／`boss_phases` 必填。刪掉 `PARTS_MIN`、`PARTS_MAX`、`PART_HP_TOTAL_MAX`、`PHASES_MIN`、`PHASES_MAX`；`BossPart.on_break` 只留 `min_length=1`。
- 驗證搬到 `Ruleset` 層（範本讀不到 core.yaml）：
  - `parts.part_rule_problems(parts, rules)`：部位數、血量加總、破壞效果數；由 `unit_checks.unit_part_problems` 呼叫。
  - `battle.phase_count_problems(phases, rules)`：階段數；由 `unit_checks.unit_phase_problems` 呼叫。
  - `check_parts` 只留 ID 不重複；`check_phases` 拿掉項數檢查。
- 訊息文字改用規則的值組字，內容不變（例「所有部位的血量加總不能超過 600‰（收到 601‰）」）。工坊的錯誤一樣掛在改到的 3 個部位欄位上（`test_parts_pb1n` 照舊通過）。

### 3.4 新增的工坊欄位（`tuning_fields.yaml`，`rules/core.yaml` 那一組）
- `boss_parts.hp_total_max_permille`（部位血量加總上限，‰，建議 400～800）：設計寫「數值工坊可調」。
- 沒開的（結構，列給 PM）：`boss_parts.count_min／count_max`、`break_effects_max`、`boss_phases.count_min／count_max`。
- 3.1 那些預設值本來就在內容檔，只是拿掉程式的預設，這段沒加進工坊（待決 4）。
- 順手改了單位 `speed` 的說明：「沒寫時是 5」→「單位檔必填」。

### 3.5 測試
- 只改測試資料（補上變成必填的欄位：單位的 speed、部位的 hp_permille 200、陣法 range、相鄰治療 attr_permille）與移層的檢查：
  - `test_boss_parts_content`：部位數、血量加總、破壞效果數 4 例從「範本驗證會擋」改成新測試「載入內容庫時擋」（`unit_phase_problems`，訊息逐字比）。
  - `test_boss_phases`：「2～4 項」那例改成 `phase_count_problems` 的新測試。
  - `test_equipment_content`：遞減權重的兩例改成用內容庫的值替換一欄，並比對訊息（原本缺欄位也會丟 ValidationError，會白過）。
  - `test_rules_budget_bs1`：工坊 core 欄位清單多一個。
  - `test_battle_content::test_unit_defaults` 拿掉 `speed == 5`。
- `scripts/x10/fields.yaml`：新寫進內容的欄位（`forms[].entry.shield_duration`、`boss_parts.*`、`boss_phases.*`）列進 keep（回合、個數、‰，不是量類）；`test_x10_fields`、`test_x10_rescale` 要求每個數字欄位都有歸類。

## 4. 不變比對

- 基準：`git archive 6c887ed7b src content`，`PYTHONPATH`、`TRPG_CONTENT_DIR` 指向基準；每個 worker 斷言載入的 `trpg` 來自基準那份。
- 範圍：同 X10-2a～HC-2 的 78 場（15 張正式地圖 × 種子 1、7；`open_plain` 種子 3 × 8 個 build；4 張頭目圖 × 種子 3～12）。
- 比對：`--log-json` 整份（排除 `ruleset_hash` 與 `setup`／`final_state` 裡的規則包），加上文字輸出（排除寫入路徑那一行）。
- 結果：**`battles=78 events=26446 different=0`**（事件總數和 HC-2 相同）。
- 內嵌規則包的差異（所以 `ruleset_hash` 會變）：
  - 新增 `core.boss_parts`、`core.boss_phases`；
  - 「用不到時改 None」：沒有狀態的 7 個灌注的 `duration`、沒有護盾的 8 個形態的 `shield_duration`、雷靈的 `duration`、鷹隼與冰靈的 `chain_permille`，從 2／500 變 `null`。
  - 其他欄位逐字相同。
- parity（slow）、CLI 快照：見第 5 節，都沒重產。

## 5. 檢查（最後一個程式 commit `5efe8fc86`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1744 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 不變比對 78 場 | different=0 |
| 分目錄 `pytest -n 8`（預設標記） | 見下表 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（979 passed；parity、CLI 快照沒重產） |

| 目錄 | 結束碼 | 結果 |
|---|---|---|
| api | 0 | 1339 passed、1 skipped（第一輪 1 failed：工坊 core 欄位清單少新欄位，補上後該檔與部位工坊測試 30 passed） |
| bot | 0 | 67 |
| cli | 0 | 148 |
| content | 0 | 3166 |
| engine | 0 | 5120 |
| llm | 0 | 495 |
| narrative | 0 | 479 |
| roguelite | 0 | 279 |
| server | 0 | 77 |
| shared | 0 | 76 |
| sim | 0 | 180 |
| skillgen | 0 | 4637 passed、7 skipped |
| world | 0 | 1328 |
| 頂層 `tests/*.py` | 0 | 251 |

- world、頂層第一輪各有失敗（測試的單位缺 speed；x10 欄位清單沒列新欄位），修好後整個目錄重跑都是 0（上表是重跑結果）。api 修的是單一檔，沒有整目錄重跑。
- 前端沒動，沒跑 vitest。OpenAPI 沒變（沒動 api schema）。

## 6. 待 PM 決定（5 件；都是解讀類，照最保守的做了）

1. **「有某欄才用到」的 4 個預設值改成可省略、用到時必填**（3.2）。照字面改必填，要在 18 處寫進用不到的值（例：沒有狀態的灌注寫 `duration: 2`），所以改成 `None`＝用不到。戰鬥結果不變，但內嵌規則包裡這些值從 2／500 變 `null`，`ruleset_hash` 會變（HC-2 也有同類變化）。要照字面全寫進內容的話告訴我。
2. **歸 const 的 6 筆**：`compute_hit_thresholds` 的 `Decimal(2)` 3 筆、`_DECIMAL_PRECISION` 60、`weapon_attr_examples_zh` 的範例列數（每組 2、最多 5 組）。是數學與說明排版，不是玩法數值；規格只說 config／guard 的分法，這幾筆照實改判 const。
3. **`CoreRules._check_tier_budget` 的 1～5 沒搬**（戰鬥核心剩的 4 筆 config todo）：這是「技能有 5 個階級」的規則，和 `SkillDef.tier ≤ 5`（HC-4b 範圍）是同一件事，建議 HC-4b 一起搬。
4. **工坊只開了 1 個欄位**（`boss_parts.hp_total_max_permille`，設計寫「數值工坊可調」）。其他：
   - 部位數、破壞效果數、階段數是結構，沒開。
   - 3.1 改必填的預設值本來就在內容檔，這段沒加進工坊。要開的話，`rules/core.yaml` 可以直接加；`forms.yaml`、`rules/equipment.yaml`、`item_gen.yaml` 還不是工坊對象，要加新的對象種類（會動 `api/tuning`，這段不能碰）。
5. **舊戰鬥紀錄相容**：`CoreRules` 有幾欄的說明寫「舊紀錄沒有此欄位」（例：`max_displace_distance`、`explode_max`、`source_max`），原本靠預設值載入舊紀錄的內嵌規則包。改必填後，比這些欄位還舊的紀錄載不進來（`tests/` 沒有這種夾具，全部測試通過）。HC-2 改必填的欄位也是同樣情況。要保留相容的話，可以在讀紀錄的地方補值，而不是放回 schema 預設值。

另外兩點供參考（不用決定）：
- 部位數、血量加總、破壞效果數、階段數改在載入內容庫時檢查，所以直接 `UnitTemplate.model_validate` 不再擋這幾項（測試照這個改了）；內容、工坊草稿都會經過內容庫檢查。
- `classes.yaml` 戰鬥核心 6 檔的逐檔 config 規則照規格改 done（現在 0 筆）。之後這些類別若再寫新的預設值，會被歸成 config done、不會被擋；要擋的話可以改成刪掉這幾條規則。

## 7. 平衡疑慮（無）

沒有。只換數字放的地方，78 場戰鬥逐字相同。
