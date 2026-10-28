# Phase 3J-4b 報告｜形態開局與 +30% 精確

規格：`docs/phases/Phase3J計畫.md` 4.13；設計：`docs/design/06-技能.md` 6.30「形態池名單」、6.27.3。

## 做了什麼

1. **起始技能規則只為 `enter_form` 開放姿態**：`is_starter_skill`（`skillgen/keywords.py`）對 1 階、普通／稀有的姿態，只有帶 `enter_form` 的（新函式 `is_form_maker`）算起始技能；其他姿態照舊不行，2 階化身也不行（階級）。
2. **開局選「形態」一定拿到 1 階化身**：`starter_pools()`（`roguelite/start.py`）把「形態」池收斂成熊、貓、巨鵰、狼人 4 招；`starting_skill` 沿用 `Rng(seed).fork("start/skill/form")` 隨機抽 1 招（確定性）。三招利用者仍在關鍵字池（三選一、工坊），只是不當起始技能。
3. **「在形態中 +30%」精確化**：新增 `EffectSpec.form_bonus_permille`（`damage`／`heal`，只能用在技能自己的效果）。施放者在形態中時，該效果的倍率再乘 `1000 + n`‰（整體乘，骰值、屬性加成一起，屬性加成只算一次）。
   - 引擎：`targeting.form_bonus_permille()`；傷害走 `damage_parameters`（施放、預覽、`then` 共用），治療走 `Cast.heal_multiplier(spec=...)`。
   - 內容：化形撲擊、野性怒吼、化形回春改成單一效果＋`form_bonus_permille: 300`（拿掉原本的追加骰與 `in_form` 條件效果）。
   - 卡片（`narrative/skills.py`）：「若你在形態中，整體 +30%」；預算（`skillgen/budget.py`）：基礎點數 × (1 + n‰ × 「在形態中」條件倍率 0.6)；原語表（`skill_primitives.yaml`）、工坊文字（4 筆）、選項標籤、玩家文字。
   - 關鍵字：帶 `form_bonus_permille` 的效果等同「在形態中」條件，仍屬「形態」利用者。
4. `LOG_FORMAT` 遞增為 `/82`（`runner.py` 文件字串與測試字面值一起改）；`skill_icons.json` 重產；CLI 快照更新。

## 驗收對照（4.1 第 9 點與 4.13）

| 條件 | 證據 |
|---|---|
| 起始技能規則只為 `enter_form` 開放姿態 | `tests/roguelite/test_form_start_3j4b.py::test_starter_rule_opens_stances_only_for_enter_form` |
| 形態池起始只有 4 招 1 階化身 | `test_the_form_start_pool_holds_only_the_tier_one_forms`；`tests/skillgen/test_keywords.py`（池內容）；`tests/engine/test_forms_3j4.py::test_the_exploiters_belong_to_the_form_pool` |
| 多個種子、多把武器都拿到 1 階化身，且確定性、非固定一招 | `test_the_form_keyword_always_gives_a_tier_one_form_for_many_seeds`（4 把武器 × 40 種子）；`test_a_form_run_starts_with_a_form_and_another_keyword_skill`（`new_keyword_run`，含順序對調） |
| 精確 +30%：在形態中／不在形態中傷害＝卡片、屬性加成只算一次 | `tests/engine/test_forms_3j4.py::test_the_pounce_dashes_and_the_form_adds_exactly_thirty_percent`、`..._roar_...`（斷言 `multiplier_permille` 1000／1300，`amount == (骰值×1000+屬性加成)×倍率//10^6`，`scaled_permille` 兩種情況相同） |
| 治療精確 +30% | `test_the_form_renewal_heals_exactly_thirty_percent_more_inside_a_form` |
| 驗證／關鍵字／預算 70～100% | `test_form_bonus_is_valid_on_top_level_damage_and_heal_only`、`test_form_bonus_makes_a_skill_a_form_exploiter`、`test_the_three_exploiters_stay_within_seventy_to_one_hundred_percent_of_the_budget` |
| ruff／format／mypy／lint-imports | 全過 |
| 相關測試 | `tests/engine tests/skillgen tests/content tests/roguelite tests/narrative`（除下列已修的 4 項外全過）；`tests/api tests/sim tests/llm tests/shared` 等 582 passed；`-m "slow or not slow" tests/cli` 全過（種子與快照更新後） |
| 重播 | `trpg battle --map open_plain --seed 9 --ally-build build_form_user` → `battle replay` 通過（100 動作、292 事件） |

## 為了讓既有測試通過做的調整

- `tests/engine/test_forms_3j4.py`：三招利用者的測試改成精確倍率；形態池起始改成「4 化身＋3 利用者」。
- `tests/skillgen/test_keywords.py`：形態池起始集合。
- `tests/skillgen/test_workshop_text_48f.py`：改寫對照表 159 → 163 筆（新增 `form_bonus_permille` 的原語與工坊各 2 筆玩家文字）。
- `tests/content/test_coverage.py`：`in_form` 條件目前沒有手寫技能使用，列入允許清單（3J-4c 的解形爆發會用，到時刪除）。
- `tests/cli/test_run_cli.py::test_run_auto_reaches_a_branching_evolution`：開局池改變使種子 4 不再進化，改用種子 3（慣例，註解已更新）；CLI 快照 `skills_show_all` 等雜湊重產。

## 複雜度 noqa

沒有新增。

## 待 PM 決定

1. **欄位設計**：「同等機制」我選了 `form_bonus_permille`（專用於 `damage`／`heal`），而不是讓條件效果支援 `multiplier_permille`——條件效果的語意是「額外一筆」，無法表達「同一筆乘 1.3」。其他「在 X 時 +n%」若要比照，需要另開欄位或泛化。
2. **預算**：在形態中的加成部分乘 `in_form` 的 harsh 倍率 0.6（等於 +18% 計入預算）。三招利用者落在 70～100%，數值初值未經模擬。
3. **利用者不當起始技能**：形態池的起始只剩 4 招化身（照 6.30 文字）；因此開局永遠拿不到化形撲擊等；若玩法 PM 想讓「第二個關鍵字也選形態」之類的情況拿到利用者，需另案。
4. **固定起始技能**（`--skills`／API 指定）同樣受池限制：形態只能指定 4 招化身。
5. **`LOG_FORMAT` `/82`**：與 3R-2 可能撞號，合併時由 PM 決定最終編號與文字。
6. `test_coverage.py` 的 `in_form` 允許清單在 3J-4c 實作後須刪除（否則「清單過時」測試會失敗）。
7. 武器類別（weapon）技能也能填 `form_bonus_permille`（倍率對武器技同樣有效），目前沒有內容使用；未額外限制。
8. 2 階化身仍不能當起始技能（階級規則）；沒有改動。
