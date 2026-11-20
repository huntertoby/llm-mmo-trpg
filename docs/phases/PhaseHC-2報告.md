# Phase HC-2 報告：量類寫死值跟著 quantity_scale

基準：開工時 `git merge main`（`b8803ebb7`）。分支 `worktree-agent-a33505cbc7924293b`，沒 push。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 專查「量類預設 1」 | `87a228a02` | `classes.yaml` 記下找到的 6 筆與判斷 |
| 2 content 的量類預設值與上下限 | `36efbdd24` | 預設值拿掉改必填、上限改 `quantity_cap()`、互動 `min_damage` 跟倍率 |
| 3 生成器與零星位置 | `942875d2e` | 生成器確認、`restore_resource` 後備、屬性上限合併、覆蓋表、前端 `?? 10`、倍率測試 |
| 4 `run_campfire.json` 新單位 | `e0ff182ff` | 主角數值用伺服器函式重算 |
| 報告 | 本 commit | |

每個 commit 前都跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試；第 2、3 項各跑一次 78 場比對。

## 2. 專查「量類預設 1」（第 1 項）

- 做法：把掃描器略過的集合拿掉 1，篩出欄位名、所在位置、原文帶 hp、mana、stamina、damage、heal、shield、armor、attr、flat、upkeep、bonus 等字的數字 1（93 筆），再依原文補篩一輪（`or 1` 這類後備），逐筆判斷。
- **是量類的 6 筆**（都在這段改掉）：
  1. `content/forms.py` `FormTable.stance_upkeep_mana` 預設 1
  2. `content/rules.py` `SummonGrowth.hp_per_attr_mod` 預設 1
  3. `content/roguelite.py` `_default_heroes` 法器主角 `armor_bonus=1`
  4. `content/environment.py` `InteractionOutcome.min_damage` 預設 1
  5. `engine/skills/primitives/rule_rewrites.py` `restore_resource` 法力 `spec.amount or 1`
  6. `skillgen/budget.py` `_restore_resource_points` 法力 `effect.amount or 1`
- **不是量類**（不列）：
  - `ge=1` 的正數護欄（HP、法力、屬性的下限）。
  - `max(1, …)` 的「活著／最大 HP 至少 1」（X10-2b 已裁定不改）。
  - `SkillDef.stance_upkeep`、`_STANCE_UPKEEPS`：維持費的「點數」，每點的數量在 `forms.yaml`。
  - 熟練、層數、格數、`等級 − 1`、除以 0 的保護。
- 掃描器照舊不列 1，所以 `classes.yaml` 裡這兩條規則（`py-scale-one-defaults-content`、`-misc`）在清單是 0 筆，只作紀錄。

## 3. 每處改了什麼

### 3.1 content（第 2 項）

- **新檔 `content/quantity.py`**：`QuantityScale = Literal[1, 10]`、`MAX_QUANTITY_SCALE`（10）、`quantity_cap(old)`＝換算前的上限 × 最大倍率。
- **上限**：X10-1 放寬過的 18 個上限改寫成 `le=quantity_cap(換算前)`，數字不變（例：`attack_bonus` 100＝`quantity_cap(10)`）。
  - `battle.py`：`StatusDef` 的 attack_bonus、shield_reflect、shield_end_heal、shield_break_lightning；`SummonDetonate.flat`；`SummonPulse` 的 heal_flat、shield_flat。
  - `environment.py` `ReactionDef.shield_flat`；`flash_templates.py` `FlashRules.trigger_flat_bonus`。
  - `forms.py` 四個維持費；`rules.py` `SummonGrowth` 四個量類成長、`SummonTrait.armor_bonus`。
- **拿掉預設值、改必填**（內容檔都有寫）：
  - `forms.py`：四個維持費；`Ruleset.forms` 也改必填（原本 `FormTable()`）。
  - `rules.py`：`ResourceRules` 的 class_base、base、mana、stamina、stamina_regen（刪掉 `_default_class_base`）；`AttributePerks` 的 base、step；`SummonGrowth` 的 hp_per_level、hp_per_attr_mod、flat_per_level_permille、flat_per_attr_mod_permille；`CoreRules` 的 resources、attribute_perks、summon_growth。
  - `roguelite.py`：`StartRules.heroes`（刪掉 `_default_heroes`）、`RunRules.start`。
  - `world_rules.py`：`EnemyGrowthRules.attribute_points_per_level`、`WorldRules.enemy_growth`。
- **刪掉的驗證**：
  - X10-2a 的「scale 不是 1 時量類要寫明」。
  - `CoreRules._check_quantity_defaults`、`Ruleset._check_form_quantities`、`explicit_missing`。
  - 改必填後由 pydantic 直接擋（倍率 1 也擋）。
- **互動 `min_damage`**：
  - 改成 `int | None`，`None`＝1 × `quantity_scale`，同引擎效果的 `min_damage_for`。
  - `engine/interactions.py` 的導電改用 `min_damage_for(scale)`。
  - 導電的兩條內容都寫了 10，結果不變。
- **測試**：
  - `tests/test_x10_scale.py`：兩個「scale 10 要寫明」改成「倍率 1、10 都必填」。
  - `test_attribute_perks.py`：重複檢查的假資料補 base、step。
  - `test_environment.py`：導電期望值改用 `min_damage_for`。
- **歸類**：
  - `SkillDef.stance_upkeep`（上限 2）從 scale 改判 config todo：它是點數，不是量類。
  - `SummonGrowth` 的兩個 flat_…_permille 和 `AttributePerks` base／step：HC-1 歸 config，但它們在 X10-2a 的量類清單裡，這段一起改必填；上限現在歸 `py-scale-caps`（done）。

### 3.2 生成器與零星位置（第 3 項）

- **生成器**：
  - `skillgen/flash_major.py`（8 個呼叫點）、`composer_recipes.py`（伴生、護主）在 X10-2b 已改成 `core.scaled_cost(cost)`，這段確認過，沒改程式。
  - 歸類改成 `py-scale-generator-costs`（done，20 筆）。
- **`restore_resource` 法力後備**：
  - `rule_rewrites.py` 改成 `spec.amount or ctx.core.quantity_scale`。
  - `budget.py` 改成冷卻 `or 1`、法力 `or scale`。
  - `amount` 是必填參數（min 1），這是走不到的後備，結果不變。
- **`_MAX_ATTR`**：
  - `content/battle.py` 和 `engine/gear/core.py` 各有一個 999，合併成 `content.battle.MAX_ATTRIBUTE`，gear 改用它。
  - **數值沒改**，留 todo，見待決 1。
- **`DEFAULT_DEFENSE_BREAK`**：是千分比（破甲降防禦 100‰），不是量類。沒改程式，從 scale 改判 config todo，見待決 2。
- **`world/situation_coverage.py`**：
  - `CoverageInputs` 的 base_attribute、points_per_level、ability_mod_base、ability_mod_divisor 拿掉預設、改必填。
  - 欄位移到 `race_names` 前面。
  - `inputs_from_library` 本來就全從內容取。
  - 測試的假資料明寫換算前的值（10、2、10、2），斷言不變。
- **前端 `AttributeAllocator`**：
  - `{base[a.id] ?? 10}` 改成 `?? "—"`。
  - 五個呼叫端都帶齊六項屬性，平常看不到差別。
  - `tests/test_hardcoded_scan.py` 的抽查改成看 `MAX_ATTRIBUTE`，拿掉 `?? 10` 那筆。
- **新測試 `tests/test_hc2_scale.py`（23 個）**：
  - 把 `core.quantity_scale` 換成 1（內容不動）。
  - flash_major 的 8 種轉型（`_BUILDERS` 的被動、反應、召喚、陷阱＋`_SOURCE_BUILDERS` 的伴生、護主、`_to_blessing`、`_to_aid`）的草稿代價：法力剛好是倍率 10 時的 1/10，冷卻相同。
  - composer_recipes 的伴生、護主：同上。
  - 互動 `min_damage` 後備是 1 × scale，內容兩條導電仍是 10。
  - `restore_resource` 法力後備：預算點數在兩種倍率下相同（量 ÷ scale）。
  - 10 個代表性 schema 上限＝換算前 × `MAX_QUANTITY_SCALE`。

### 3.3 `run_campfire.json`（第 4 項）

- **做法**：
  - 用 `new_dev_run(dev_blaze)` 開一輪，照夾具弄成 3 級、配點全在智力（開局 40 ＋ 2 級 × 20）。
  - 用 `hero_out`、`resource_rule_text` 算出來，只替換主角數值欄位。
  - 腳本是一次性的，放在 scratchpad，沒進 repo。
- **換掉的欄位**：
  - attributes、effective_attributes：10 → 100，智力 18 → 180。
  - attribute_spent：8 → 80。
  - hp、max_hp：44 → 440；hp_con_base：10 → 100。
  - mana、max_mana：56 → 784。
  - stamina、max_stamina：20 → 200。
  - attribute_perks：撞擊 ±10、門檻 140／220。
  - weapon_traits_zh：「10–60＋智力 × 0.3（目前 +54）」＋「擲 1d6，每點 ×10」。
  - 頂層 resource_rule_zh：回復 5 → 50。
- **法力是 784，不是 560**：夾具是 BAL-4b（法力上限 ×1.4）以前抓的；這裡照現在伺服器的算法。
- **沒動**：技能卡、閃現、裝備、背包。見待決 3。
- **截圖**：`docs/art/HC-2/campfire_respec_80.jpg`（開發頁 `panel-gallery.html#campfire`，「免費重配屬性點（退回 80 點）」）。
  - 同畫面的背包詞條「最大 HP +12」仍是舊單位（待決 3）。
- 用到這份夾具的 5 個 vitest，加上配點的 2 個，都通過。

## 4. 不變比對

- **基準**：`git archive b8803ebb7 src content`，用 `PYTHONPATH`、`TRPG_CONTENT_DIR` 指向基準。每個 worker 都斷言載入的 `trpg` 來自基準那份。
- **範圍**：同 X10-2a～3c 的 78 場。
  - 15 張正式地圖 × 種子 1、7；
  - `open_plain` 種子 3 × 8 個 build；
  - 4 張頭目圖 × 種子 3～12。
- **比對**：
  - `--log-json` 整份，排除 `ruleset_hash`；內嵌規則包另外比。
  - 文字輸出，排除寫入路徑那一行。
- **第 2、3 項做完各跑一次，結果都是 `battles=78 events=26446 different=0`**。事件總數和 X10-3c 相同。
- **內嵌規則包的差異只有一種**：`interactions.rules[].then[].min_damage`，非導電的 20 條從 1 變成 `null`（第 2 項的預設值改成 None）。
  - 導電兩條仍是 10。
  - 其他欄位逐字相同，所以 `ruleset_hash` 會變。
- **快照、夾具**：`tests/cli` 輸出快照、`test_refactor_parity`（slow）、OpenAPI 快照都通過，沒有重產。

## 5. 檢查（最後一個程式 commit `e0ff182ff`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1744 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 不變比對 78 場 | different=0 |
| `pnpm -C client typecheck` | 0 |
| vitest（配點 2 檔＋營火夾具 5 檔） | 0（7 檔 73 個） |
| 分目錄 `pytest -n 8`（預設標記） | 見下表 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 見下表 |

| 目錄 | 結束碼 | 結果 |
|---|---|---|
| api | 0 | 1340 passed、1 skipped |
| bot | 0 | 67 |
| cli | 0 | 148 |
| content | 0 | 3166 |
| engine | **1** | 5119 passed、1 failed（見下） |
| llm | 0 | 495 |
| narrative | 0 | 479 |
| roguelite | 0 | 279 |
| server | 0 | 77 |
| shared | 0 | 76 |
| sim | 0 | 180 |
| skillgen | 0 | 4637 passed、7 skipped |
| world | 0 | 1328 |
| 頂層 `tests/*.py` | 0 | 248 |
| slow：parity ＋ cli | 0 | 979 |

**engine 的 1 個失敗是既有問題，不是這段造成的**：
- 失敗的是 `test_environment_turn.py::test_property_telegraph_matches_every_environment_turn_on_demo_maps`（hypothesis），抽到 `seed=13502, map_index=1`（油庫）。
- 用同一組參數在基準 `b8803ebb7`（`git archive`，`PYTHONPATH`、`TRPG_CONTENT_DIR` 指過去）跑，也失敗：`environment_turns == 0`、`round == 2`。
- hypothesis 的資料庫記住了這個例子，所以重跑仍會失敗。見待決 5。

## 6. 筆數（`classify.py --stats`）

- 後端 scale：67 → **39**。
  - done 38：`py-scale-caps` 18、`py-scale-generator-costs` 20。
  - **todo 1**：`py-scale-max-attribute`。
- 前端 scale：1 → **0**（`ts-attr-base` 改 done，0 筆）。
- **scale todo 剩 1 筆**（`MAX_ATTRIBUTE` 999，待決 1）。
- 改判 config todo 的 2 筆（不再算 scale）：`SkillDef.stance_upkeep`、`DEFAULT_DEFENSE_BREAK`。
- 寬規則 `py-scale-names`、`py-scale-dict-keys`、`py-scale-resource-base` 現在 0 筆，留著接之後新增的量類。

## 7. 待 PM 決定（5 件；解讀類都照最保守做了）

1. **屬性上限 `MAX_ATTRIBUTE` 999**：
   - 999 不是 10 的倍數，沒辦法寫成「換算前 × scale」。
   - 改成 100 × `quantity_scale` 的話，倍率 10 時是 1000（範本驗證與裝備加成上限各 +1）。
   - 實際屬性約 100～300，碰不到，但這是規則數字，所以沒改：只合併成一個常數，留 todo。
   - 要改成 100 × scale，還是改判護欄（HC-4 的 `guard` 類）？
2. **`DEFAULT_DEFENSE_BREAK`（100‰）不是量類**：照 HC-1 裁定 2「執行時會用到的預設值」改判 config todo，留給 HC-4／HC-7。也沒改歸類為 scale done。
3. **營火夾具只換了主角數值**：
   - 技能卡（「法力 6」「1d12＋智力加成」）、裝備與背包詞條（「最大 HP +12」）仍是舊單位。
   - 要用伺服器重產，需要那幾招閃過的 `SkillDef`，夾具裡沒有。
   - 另外，`client/src/dev/fixtures/flashChoice.json` 的 `hero` 是 X10-3d 從這份抄的，沒重產（要跑 `scripts/export_flash_choice_fixture.py`，會連帶重排 LLM 組）。
   - 要不要另開一段，用新的 run 重抓整份夾具？
4. **schema 上限用「最大倍率」，不是內容的倍率**：
   - pydantic 欄位載入時拿不到 `core.yaml` 的 `quantity_scale`，上限寫成換算前 × 10。數字和 X10-1 相同。
   - LLM 生成的技能在解析時照樣受這個上限保護。
   - 倍率 1 時上限偏寬（只會發生在測試）。
   - 要嚴格跟內容倍率走的話，要把檢查搬到 `Ruleset` 層，但生成的技能就少了解析時的擋。

5. **既有的 hypothesis 失敗**：
   - 油庫種子 13502 打到第 2 輪結束都沒有可比較的環境回合，`assert environment_turns >= 1 or state.round == 1` 不成立。
   - 基準也失敗，和 HC-2 無關。
   - 要放寬斷言，還是另開修正？這段沒動。

## 8. 平衡疑慮

- 沒有。只換寫法，78 場戰鬥結果逐字相同。
