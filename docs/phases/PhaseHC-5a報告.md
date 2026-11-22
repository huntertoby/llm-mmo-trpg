# Phase HC-5a 報告：閃現生成常數搬進 content

依據：`docs/phases/PhaseHC-5a計畫.md`；HC-4d 報告的開發 PM 裁定 1（`TrapSpec.rounds`）；做法照 HC-4b3、HC-4c。
基準：main `5188031d0`（worktree 開工時在 `6adbedef3`，先 fast-forward）。分支 `worktree-agent-a4d0300bf0c6a9f70`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`，也沒碰 QF-4 的三個測試檔。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 閃現常數搬家 | `d29001ef3` | `skillgen/flash_*.py` 的 71 筆 config 搬進 `flash_templates.yaml`（`rules` 新格、`rules.search`、轉型模板的草稿欄位）；鏡像 `core.yaml` 的改讀 `skill_limits` |
| 2 `TrapSpec.rounds` | `f65e77be1` | 改必填；skillgen 兩處試組與工坊草稿表單改由 `probe_trap()` 明確帶值（2） |
| 3 開進工坊 | `e528f15aa` | `flash` 表新開 16 格（3 個新分組） |
| 4 收尾 | `ba2ea7c09` | 刪掉變成 0 筆的 8 條規則；`寫死數值-清單.md` 用 `--md` 重產 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、`trpg content check` 與相關測試。

## 2. 第 1 項：閃現常數搬家

### 2.1 放在哪裡（都在 `content/flash_templates.yaml`，由 `ContentLibrary.flash` 帶進 skillgen）

**`rules`（既有區塊，`FlashRules` 新格，全部必填）**

| 原本 | 新格 | 值 |
|---|---|---|
| `flash_ops.CHARGE_COOLDOWN_STEP`、`MAX_CHARGE_COOLDOWN` | `charge_cooldown_step`、`max_charge_cooldown` | 2、5 |
| `flash_cost.CHARGE_DURATION_CAP` | `charge_duration_cap` | 2 |
| `flash_ops.MAX_TRIGGERS_PER_ROUND` | `max_triggers_per_round` | 3 |
| `flash_ops.RELAX_PERMILLE`、`MAX_RELAX_PERMILLE` | `hp_relax_step_permille`、`hp_relax_max_permille` | 150、900 |
| `flash_reclaim.TIGHTEN_PERMILLE`、`MIN_TIGHTEN_PERMILLE` | `hp_tighten_step_permille`、`hp_tighten_min_permille` | 150、100 |
| `flash_ops._RELAX_ALTERNATIVES`、`flash_reclaim._TARGET_CONDITION`／`_SELF_CONDITION` 的 500 | `added_hp_condition_permille` | 500（條件種類留在程式） |
| `flash_ops.MAX_EMPTY_SLOTS_CAP` | `max_empty_slots_cap` | 6 |
| `flash_ops._BLOOD_BONUS_PERMILLE` | `blood_bonus_permille` | 50 |
| `flash_ops.SUMMON_HP_STEPS`（強壯、合體共用） | `summon_hp_steps` | [100…1000] 7 格 |
| `flash_ops._new_damage` 的 300 | `new_damage_multiplier_permille` | 300 |
| `flash_ops._FOLLOWUP_POTENCY_STEPS`、`_FOLLOWUP_EASE_STEPS`、`_FINE_MULTIPLIER_TOP` | `followup_potency_tries`、`followup_ease_steps`、`followup_fine_top_permille` | 10、4、3000 |
| `flash_offer._usage_score` 的 13 個權重 | `usage_scores`（op → 分數；13 個 op 都要寫、多寫會擋） | 2、2、2、2、1、1、3、2、1、1、3、1、2 |
| `flash_offer._MULTI_TARGETS_PERMILLE`、`_FREQUENT_USES` | `usage_multi_targets_permille`、`usage_frequent_uses` | 1500、6 |
| `flash_offer._KEYWORD_CAP` | `second_keyword_cap` | 6 |
| `flash_major._MAX_CARRIED` | `transform_carry_max` | 2 |
| `flash_major._POWER_STEP` | `beside_power_step_permille` | 100 |

**`rules.search`（新開的子區塊 `FlashSearch`）**：`tune_attempts` 3（原 `flash_derive.TUNE_ATTEMPTS`、`flash_trade._TUNE_ATTEMPTS`，兩個本來就寫「同」）、`strict_margin_millipoints` 10（原 `flash_derive.STRICT_MARGIN`、`flash_major._STRICT_MARGIN` 的 `Fraction(1, 100)`，換成千分之一點避開新的除數）、`cap_shrink_steps` 6、`cap_shrink_permille` 30、`max_cost_cuts` 12（原 `flash_trade`）。
- 新開區塊的理由：這幾格是生成器的搜尋參數（重調要試幾次、嚴格要多出多少、壓回上限時怎麼退），不是玩法數值，但改了會改變做得出來的招，所以要進資料；和玩法數值分開放，工坊不開。

**`transforms[]`（既有的轉型模板，`TransformTemplate` 新欄位，用到時必填、用不到時不能填）**

| 原本（`flash_major.py`） | 新欄位 | 哪些轉型 |
|---|---|---|
| `_to_passive`／`_to_reaction`／`_to_trap`／`_to_blessing`／`_to_aid` 的代價清單、`_SUMMON_COSTS`、`_GUARDIAN_COSTS`、伴生的 `({}, mana 2, mana 4)` | `draft_costs` | 被動、反應、召喚、陷阱與 TF-1 四種（姿態、修正不填） |
| 反應 2、召喚 4、陷阱 4、護主 2、援手 1 的射程 | `draft_range` | 轉成反應、召喚、陷阱 |
| 召喚 1、陷阱 2 的 AP | `draft_ap_cost` | 轉成召喚、陷阱 |
| `_MAX_TRAP_EFFECTS` | `max_trap_effects` | 轉成陷阱 |
| `_STANCE_UPKEEPS` | `stance_upkeeps` | 轉成姿態 |

- 代價裡的法力是換算前的單位，程式照舊經 `CoreRules.scaled_cost` 乘 `quantity_scale`（`fields.yaml` 登記為 keep 並註明）。
- `draft_costs` 的鍵只能是 `mana`、`stamina`、`cooldown`（型別寫 `dict[str, int]` 加檢查，因為 `scaled_cost` 收 `Mapping[str, Any]`）。

**`extra_major[]`**：預支（`only: borrow`）的 `amount`、`uses` 改成用到時必填（內容檔本來就寫 2、1），拿掉程式的 `or 2`、`or 1`。

### 2.2 不另開格、改讀既有規則（同值）
| 原本 | 改讀 | 值 |
|---|---|---|
| `flash_ops.MAX_STANCE_UPKEEP` | `core.skill_limits.max_stance_upkeep`（HC-4d） | 2 |
| `_op_mod_range` 的 `< 2`（修正規則最多 2 條） | `core.skill_limits.max_modifiers` | 2 |
| `_op_mod_range` 把射程 +1 升成 `2` | `core.skill_limits.modifier_bounds.range_delta_max` | 2 |
| `flash_major._MIN_POWER` | `core.skill_limits.min_beside_power_permille`（HC-4d） | 100 |
| `flash_cost._SHIELD_DEFAULT_DURATION` | 護盾狀態（`status`，省略＝`shielded`）的預設回合，同引擎結算 | 2（`shielded*` 6 個都是 2） |
| `_op_distance_bonus` 貼身的 `2` | `skillgen/validate.py` 的 `POINT_BLANK_MIN_REACH`（docstring 本來就寫「和閃現距離加碼同一個門檻」） | 2 |

### 2.3 判成結構常數（`classes.yaml` 新規則 `py-skillgen-flash-ops-structure-hc5a`，const）
- `_op_mod_cost` 的 `len(skill.modifiers) < 2`：代價減輕「至少留一條規則」，要 2 條以上才能減其中一條；2 是「留下的 1 條＋要減的 1 條」，不是規則上限。
- `_op_light` 的 `(skill.ap_cost or 2) - 1`：`or 2` 是死碼（AP 是 `None` 或 1 時前一行已經改走減資源），改成 `assert` 後直接減 1，不是換寫法躲掃描。

### 2.4 為了帶入 `library` 改的簽名（skillgen 內部）
- `flash_cost`：`strength_table`、`strength_moves`、`light_ok`、`charge_ok`、`accept_for` 多一個 `library`（護盾預設回合要讀狀態表）。
- `flash_major`：`_hostile_core`、`_modifier_changes`、`_power_tries`；`flash_ops`：`_new_damage`、`_conditional_bonus`；`flash_reclaim`：`_tightened`、`_rule_conditions`。幾個 `_lib` 參數改名 `library`（現在用到了）。
- 公開常數拿掉：`flash_cost.CHARGE_DURATION_CAP`、`flash_derive.TUNE_ATTEMPTS`／`STRICT_MARGIN`、`flash_ops.SUMMON_HP_STEPS`（`__all__` 一起改）。repo 裡只有 `test_flash_cost_fl1a.py` 用到，改讀 `LIB.flash.rules.charge_duration_cap`。

### 2.5 測試
- 新增 `tests/content/test_rule_defaults_hc5a.py`：少寫一格就驗證失敗（28 格）；13 個用法分數都要寫、多寫擋；`summon_hp_steps` 要遞增；嚴格差距換回 0.01 點；轉型草稿欄位用到時必填（17 例）、用不到時不能填（6 例）、代價鍵檢查；預支的 `amount`、`uses`。
- 改：`test_flash_cost_fl1a/c/d/e.py`（呼叫多帶 `LIB`）；`tests/test_hardcoded_scan.py` 的抽查從 `flash_ops.RELAX_PERMILLE`（config）改成 `flash_templates.py` 的 `charge_cooldown_step`（guard）。
- `scripts/x10/fields.yaml`：新格全部 keep（回合、次數、‰、分數、格數；代價是換算前單位）。

## 3. 第 2 項：`TrapSpec.rounds`
- `content/skills/reactions.py`：`rounds: int = Field(ge=1, le=6)`，沒有預設值。`enter`、`delay` 兩種都用到，所以直接必填（不是用到時必填）。內容檔的陷阱技、組合器配方、`to_trap` 轉型都有寫。
- 新函式 `skillgen/option_effect_rules.py::probe_trap(library)`：`{"trigger": "enter", "rounds": library.composer.trap.enter_rounds.min}`，現值 2，同原本的程式預設。
  - `options.py::_probe_builds`（選項探測）與 `option_effect_rules.py` 的效果規則探測改用它；`_effect_choices` 往下傳。
  - 工坊草稿表單 `_trap_field` 的 `rounds` 預設改成 `probe_trap(library)["rounds"]`（表單的 `required` 照舊，沒改）。
- `src/trpg/content/` 的 config todo：1 → **0**。順帶 `options.py` 表單的 `default=2`（HC-5b 範圍的 config）也少 1 筆。
- 新增 `tests/skillgen/test_trap_rounds_hc5a.py`：沒寫輪數驗證失敗、內容檔都有寫、試組陷阱的值、表單預設讀內容。
- OpenAPI 重產沒有差異（技能定義不在 API 的 schema 裡）。

## 4. 第 3 項：開進工坊（`flash` 表新開 16 格）

| 分組 | 欄位 | 名稱 | 建議範圍 |
|---|---|---|---|
| 小變化的步階 | `rules.charge_cooldown_step` | 蓄力每次加幾回合冷卻 | 1～3 |
| | `rules.max_charge_cooldown` | 蓄力後冷卻最多幾回合 | 3～6 |
| | `rules.charge_duration_cap` | 蓄力最多比原招多幾回合 | 0～4 |
| | `rules.max_triggers_per_round` | 觸發次數上限最多加到幾次 | 1～3 |
| | `rules.hp_relax_step_permille` | 條件放寬：血量門檻一次放寬幾‰ | 50～300 |
| | `rules.hp_relax_max_permille` | 條件放寬：血量門檻最多到幾‰ | 500～1000 |
| | `rules.hp_tighten_step_permille` | 專注：血量門檻一次收緊幾‰ | 50～300 |
| | `rules.added_hp_condition_permille` | 新加條件的血量門檻（‰） | 200～800 |
| | `rules.blood_bonus_permille` | 以血支付的威力加成（‰） | 0～200 |
| 出題的用法分數 | `rules.usage_scores.area` | 用法分數：常打多個目標時「範圍」 | 0～5 |
| | `rules.usage_scores.kill_refund` | 用法分數：有擊殺時「擊殺返還」 | 0～5 |
| | `rules.usage_scores.keyword_exploit` | 用法分數：關鍵字有訊號時「利用關鍵字」 | 0～5 |
| | `rules.usage_multi_targets_permille` | 「常打到多個目標」的門檻（‰） | 1000～3000 |
| | `rules.usage_frequent_uses` | 「常用」的放出次數 | 2～12 |
| 轉型 | `rules.transform_carry_max` | 轉型帶得走幾個效果 | 1～3 |
| | `rules.beside_power_step_permille` | 伴生、護主找強度的間距（‰） | 50～250 |

- 每格都有中文名稱、分組，說明寫了調高、調低的效果；有上限的寫了「只能 a～b」或「不能超過 X」。現值都在建議範圍內（測試檢查）。說明沒有決定編號、英文欄位名。
- 草稿驗證通過；超過 1000‰ 被擋。新測試 `tests/api/tuning/test_workshop_open_hc5a.py`（表的欄位剛好是 HC-4b3 的 18 格＋這 16 格、值與說明、同組相鄰、驗證）。`test_workshop_open_hc4b3.py` 的「剛好這些欄位」改成「至少有這些」。
- **沒開的**（意思相近或屬結構、搜尋參數）：
  - `usage_scores` 其餘 10 個（`range`、`reshape`、`multi_hit`、`followup`、`followup_potency`、`extend`、`charge`、`light`、`keyword_imbue`、`mod_keyword`）；
  - `hp_tighten_min_permille`、`max_empty_slots_cap`、`second_keyword_cap`、`new_damage_multiplier_permille`；
  - `summon_hp_steps`（階梯，同 HC-4b3 不開階梯）、接續段三格（`followup_*`，搜尋草稿數與細階梯範圍）；
  - `rules.search` 五格（不是玩法數值）；
  - 轉型模板的 `draft_costs`、`draft_range`、`draft_ap_cost`、`max_trap_effects`、`stance_upkeeps`（清單項目，同 HC-4b3 待決 3 的 `summon_duration`：轉型沒有 `name_zh`）。
- 前端沒改（表與表單元件沿用 HC-4b3），所以沒跑 tsc、vitest、build；沒截圖。

## 5. 第 4 項：收尾
- 刪掉 8 條變成 0 筆的規則：`py-skillgen-flash-{cost,derive,major,offer,ops,reclaim,trade}-config-number`、`py-content-skills-reactions-config-number`。
- `classify.py --check` 沒歸類 0；`寫死數值-清單.md` 用 `--md` 重產。
- 基準就已經 0 筆的 11 條照舊不動（`py-scale-names`、`py-scale-dict-keys`、`py-scale-resource-base`、`py-content-loader-config-number`、`py-content-skills-conditions-config-number`、`py-content-skills-effects-config-number`、`py-content-ui-wait-config-number`、`py-content-workshop-config-number`、`py-content-world-enemies-config-number`、`py-content-rules-text-text`、`py-content-skill-rules-text-text`）。

## 6. config todo 與歸類（`classify.py --stats`）
| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `5188031d0` | 372 | 38 | 8931 | 193 | 432 |
| 後端 交件 | **299** | 22 | 8949 | 193 | 451 |
| 前端（沒改） | 22 | 0 | 5441 | 98 | 0 |

- config 少 73：閃現 71、`TrapSpec.rounds` 1、`options.py` 表單的 `default=2` 1。`src/trpg/content/` 剩 0，`skillgen/flash_*.py` 剩 0。
- scale 少 16：轉型代價裡的法力（`py-scale-generator-costs`，原本 `flash_major.py` 的 16 筆）搬進內容檔；`composer_recipes.py` 的 4 筆照舊。
- guard 多 19：新 schema 欄位的 `Field(le/ge)` 護欄。const 多 18：新欄位的 `ge=0`／`le=1000` 等 ‰ 護欄、`_op_mod_cost` 的結構數（2.3）、docstring 裡的數字。

## 7. 不變比對（基準 `git archive 5188031d0 src content config`）
腳本放在 scratch（沒進 repo），沿用 HC-4d 的 `budget434.py`、`compare78.py`、`flash_dump.py`。改前用基準的 `src/`、`content/`，改後用交件 commit 的 `git archive`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`，並確認載入的 `trpg` 路徑）。

| 比對 | 時機 | 結果 |
|---|---|---|
| 逐招預算 434 招（`BudgetReport` repr＋`validate_skill` 違規） | 第 1 項後、交件 | `skills=434 same=434 different=0` |
| 78 場戰鬥（去掉 `ruleset_hash` 與內嵌規則包） | 第 3 項後、交件 | `battles=78 events=26446 different=0`；內嵌規則包 0 差異 |
| 閃現出題（規則、計價、406 招完整技能、出題） | 第 1 項後、交件 | 規則、計價、加成、退回都相同；完整技能 `same=406 different=0`；出題 `items=522 rows=3966 same=522 different=0` |

- **閃現出題加了用法統計**：HC-4b3 的 174 組都用空的用法統計，`_usage_score` 大多是 0 分，比不到搬家的權重。這段另外各跑一次「常打多個目標、有擊殺、目標帶關鍵字」與「常打單體、平均距離近」的用法統計，共 522 組、3966 筆（空用法那 174 組照舊）。
- **預測會變的地方（逐鍵核對）**：
  - 閃現表的 `model_dump` 只多了新格（`rules` 的 22 格與 `search`，轉型模板每個多 5 個草稿欄位），值都是原本的常數；沒有其他差異。這份 dump 不進雜湊、存檔或 API。
  - 78 場的內嵌規則包沒有差異（閃現表不嵌入；`TrapSpec` 的預設拿掉後，內容檔本來就寫了輪數），`ruleset_hash` 也沒變。
  - OpenAPI、前端夾具（`export_client_fixtures.py`）重產都沒有差異。
  - parity 夾具、CLI 快照沒重產，slow 測試照原樣跑（第 8 節）。

## 8. 檢查（最後一個程式 commit `ba2ea7c09`；前端沒改，沒跑 tsc、vitest、build）
| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1774 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 逐招預算比對 434 招 | different=0 |
| 78 場戰鬥比對 | different=0 |
| 閃現出題比對 | different=0 |
| `run_pytest.py -q tests -n 8`（全部非 slow） | 0（17960 passed、8 skipped，35 分 35 秒；沒有 node down、沒有 stuck） |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979 passed） |

## 9. 待 PM 決定（都照最保守的做了）
1. **`rules.search` 新開子區塊**：重調次數、嚴格差距、壓回上限的步數與減費用格數不是玩法數值，但改了會改變做出來的招，所以照「拿不準歸 config」搬進資料，另開子區塊、不開進工坊。要改判 const 留在程式的話告訴我。
2. **轉型草稿的代價、射程、AP 放在各轉型模板**（`transforms[]`），不是 `rules`：每種轉型各自不同，放模板旁邊最好找。`composer_recipes.py` 還有一份同值的護主、伴生代價與 `_power_tries`（HC-5b 範圍，沒動），兩邊之後可以改成讀同一份。
3. **`hp_relax_step_permille` 與 `hp_tighten_step_permille` 分成兩格**：程式說明寫收緊「同條件放寬的一級」，現值都是 150。分開放不會讓一格改了另一格跟著變；要合成一格的話告訴我。
4. **改讀既有規則的 6 處**（2.2）：同值，但語意綁到別的格。例如工坊改了 `max_modifiers`，閃現「範圍 +1」能不能多加一條規則也跟著變；改了 `shielded` 狀態的預設回合，閃現比較護盾回合的基準也跟著變（和引擎一致）。貼身門檻直接沿用 `validate.POINT_BLANK_MIN_REACH`（它本身仍是 config todo，留給 HC-5b）。
5. **`TrapSpec.rounds` 的試組值取組合器 `trap.enter_rounds.min`**：內容裡沒有「陷阱預設輪數」這一格，最接近的是組合器 enter 陷阱的最短輪數（2）。試組只看 schema 與規則合不合法，工坊表單是預填值。另開專用格的話告訴我。工坊表單的 `rounds` 沒改成 `required`（前端的必填提示會變），送出沒填輪數的草稿現在會被 schema 擋，不再補 2。LLM 提議的陷阱沒寫輪數時也會被擋（原本補 2）；提示詞沒提到輪數，現有測試沒有這種案例。
6. **用法分數改成 `op → 分數` 的表**：13 個 op 都要寫，條件留在程式。1 分的 5 個（`followup`、`followup_potency`、`charge`、`light`、`keyword_imbue`）原本寫成 `int(...)`、掃描沒列成 config，現在也一起進表，方便一起調。
7. **工坊只開 16 格**（第 4 節），沒開的列在同一節。
8. **範圍外的小改動**：`_op_light` 的死碼改 `assert`（2.3）；`flash_major._to_trap` 加一行 `assert`（型別收窄）；幾個 `_lib` 參數改名 `library`；`options.py` 的探測多傳一個 `trap` 參數。輸出不變。

## 10. 平衡疑慮（無）
沒有。只換數字放的地方；434 招預算、78 場戰鬥、閃現出題（含有用法統計的 348 組）、完整技能、計價逐項相同。

## 開發 PM 裁定（2026-11-21）

已用 `--no-ff` 合併進 main，和 QF-4 一起推。合併後在 main 重跑 ruff、format、mypy、lint-imports、`classify.py --check`、`trpg content check`，結束碼都是 0。全量檢查由 push hook 跑。

待 PM 決定的 8 件：
1. **`rules.search`**：照做。留在 config，不開進工坊。
2. **`composer_recipes.py` 的護主、伴生代價**：交給 HC-5b，和轉型模板的值加對照驗證，或改成共用一處。
3. **兩格血量門檻步距**：保留兩格，以後可以分開調。
4. **改讀既有規則的 6 處**：照做。`POINT_BLANK_MIN_REACH` 交給 HC-5b。
5. **陷阱輪數必填**：**要修，交給 HC-5b**。原本輸入沒寫輪數時會自動補 2，現在會被 schema 擋下。LLM 提議和工坊草稿走這條路，結果會不一樣，不符合「結果不變」。
   - 修法：內容檔裡的 `TrapSpec.rounds` 照舊必填。LLM 提議和草稿的輸入層在驗證前，沒寫輪數就補組合器的 `trap.enter_rounds.min`（2）。
   - 加測試：沒寫輪數的提議和草稿，結果要和 HC-5a 之前相同。
6. **用法分數表**：照做。
7. **工坊只開 16 格**：照做。
8. **範圍外的小改動**：接受。
