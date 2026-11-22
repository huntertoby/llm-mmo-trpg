# Phase CR-1 報告｜暴擊倍率可變＋種族可以給數值

> 規格 `docs/phases/PhaseCR-1計畫.md`；規則以 `docs/design/05-戰鬥.md` 5.4.2（#178）、`docs/design/07-角色成長.md` 7.7（#179）為準。基準 main `36b7dbdf8`（含 E3、E4）。交件前合併 main `1eaac15a1`（只有 E4b 的前端與文件，沒有衝突）。

## 1. Commit

| 項目 | commit |
|---|---|
| 加派：工坊 `觸發.on_displace`、`觸發.on_block` 的 player 文字換成玩法 PM 定的版本（source 不動；沒有測試鎖這兩段文字） | `fee41c443` |
| B1 拿掉種族的禁用欄位檢查（出身保留）、刪兩個測試 | `24885e4bd` |
| A1 算法（`_damage_rolls` 讀倍率）＋ `core.crit_damage`（基礎、全身上下限）＋ 200% 鎖定測試 | `e1a63a430` |
| A2 武器、天生武器、單位檔的倍率欄位＋工坊（新增「武器」表） | `5184991d4` |
| A3＋A4 加倍率的來源（裝備詞條、修正技、技能自帶）與疊加、全身上下限 | `96c405296` |
| B2＋B3 種族環境被動的「數值」類（`stats.crit_damage_permille`） | `ee6b45d51` |
| A5 技能預算 | `19b9132ca` |
| A6 顯示（預覽、技能卡）與「暴擊只放大骰子」 | `2b4d8747d` |
| B4 `races.yaml` 開頭註解（`races.py` 模組說明在 B1 一起改了） | `feef4634a` |
| 截圖、重產 `寫死數值-清單.md` | `354aaf88b` |
| 合併 main（`1eaac15a1`，只有 E4b 的前端與文件） | 合併 commit |
| 全量第 1 次的修正：`scripts/x10/fields.yaml` 列入新的 ‰ 欄位 | `4fe6c88b0` |
| 報告 | 最後一個 commit |

A3 與 A4 同一個 commit：疊加就是 `crit_damage_permille` 把各來源加起來的同一個函式，分開會變成半成品。B2、B3 也同一個（B3 的「清單擴充」就是 B2 加的 `stats`）。

## 2. 做法

### 2.1 算法（A1）

- `engine/rules/combat.py`：`crit_extra_total(extra, permille)`＝多擲那組 ×（倍率 − 1000）÷ 1000，無條件捨去；`None` 或 2000 直接回原值。`CRIT_PERMILLE_DOUBLE = 2000`。
- `effects/handlers._damage_rolls`：先擲原本的 `count` 顆，暴擊時再擲同樣 `count` 顆（爆骰照常），回傳（骰值、爆骰數、計入傷害的總和）。擲骰順序和次數跟改版前「一次擲 2×count 顆」一樣。`DamageDealt.rolls` 照擲出的原值記（含多擲那組）。聖光雙效的 `preset_rolls` 路徑：暴擊另擲的那幾顆乘倍率。
- `DamageEffect.crit_permille: int | None`（`None`＝200%，不輸出）。攻擊方在建立效果時算好：普攻（`reactions._attack_once`）、技能（`Cast.crit_permille(unit)`）。
- 預覽 `preview.crit_distribution`：200% 時直接用 `dice_distribution(count × 2)`（和改版前同一份）；其他倍率用卷積。
- `core.crit_damage`（`CritDamageRules`）：`base_permille` 2000、`min_permille` 1500、`max_permille` 3000；寫進 `rules/core.yaml`，工坊「核心戰鬥規則」的「暴擊傷害」組。schema 預設值同 yaml，只給舊紀錄用。

### 2.2 每種武器的倍率（A2）

- `WeaponDef.crit_permille`、`NaturalWeapon.crit_permille`（`weapon_def` 帶過去）、`UnitTemplate.crit_permille`，都是 `int | None`、1000～5000、沒填不輸出。
- 單位檔的倍率在 `ContentLibrary.weapon_of` 寫進單位的武器（蓋過武器自己的）。
- 決定基礎的武器（`crit_damage.crit_weapon`）：普攻看 `unit.weapon`（形態中是天生武器），武器技看手上的武器（`held_weapon`，同暴擊範圍的規則），法術技不看武器、照基礎。
- 工坊：新表 `weapons`（`weapons.yaml`，`weapons[*].crit_permille`）；單位的 `crit_permille`；形態表的 `forms[*].natural_weapon.crit_permille`（`existing_only`，見待決 2）。前端 `client.ts` 的 kind、`TuningScreen` 多抓一張表。
- 現有武器、單位、天生武器都沒寫值（＝照基礎 200%），序列化與存檔不變。

### 2.3 加倍率的來源與疊加（A3、A4、B2）

`engine/crit_damage.crit_damage_permille(state, unit, *, use, subject, skill)`：

1. 武器基礎（或 `core.crit_damage.base_permille`）；
2. ＋裝備詞條：新數值詞條 `affix_crit_damage`（`stat: crit_damage`，「暴擊傷害 +{n}」，`value` 100～100‰），`item_gen.yaml` 的 `stat_prices.crit_damage {points: 3, per: 100}`＝+10% 算 3 點。`build_gear` 照 8.21.5.3 遞減（同 id 100%／50%／25%），放進 `GearBonus("crit_damage_permille")`，`gear_crit_damage_permille` 查詢；裝備檢視的標籤「暴擊傷害」。
3. ＋修正技：新改變 `crit_damage_permille`（±1000、不可 0；`modifier_changes.yaml`、`CHANGE_HANDLERS`、卡片「暴擊傷害 +25%（暴擊只放大骰子）」、預算 `points_milli.crit_damage_per_100` 25）。同一招的複本照 E1 遞減。只算「受修正的施放」（`use` 不是 `None`），條件看這次的目標。
4. ＋技能自帶：`SkillDef.crit_permille`（只限有傷害的主動技），比基礎多出的部分（自帶 − base）加進這招。範圍 `skill_limits.min_crit_permille`～`max_crit_permille`（1500～3000，工坊）。
5. ＋種族：`RacePassive.stats.crit_damage_permille`（`RaceStats`，±1000、不可 0）。
6. 全部相加後套全身上下限（150%～300%）。

### 2.4 技能預算（A5）

`skillgen/budget._crit_factor`（從 `_variance_factor` 拆出）：

- 擴大暴擊範圍：1 ＋ 額外暴擊率 ×（倍率 − 100%）× 骰子占比。倍率＝技能自帶的，沒帶照 `core.crit_damage.base_permille`。200% 時算式和改版前逐位相同，說明文字也一樣（「暴擊 17–20 ×1.105」）。
- 技能自帶倍率另乘：1 ＋ 5% ×（自帶 − 基礎）× 骰子占比；說明「暴擊傷害 250% ×1.0175」，範圍那行也標出「・250%」。
- `skill_budget.yaml` 的說明註解同步。

### 2.5 顯示（A6）

- `combat.crit_text_zh(range, permille)`：「暴擊 19–20・250%」，自然 20 時「暴擊 20・250%」。
- 預覽 `notes`：倍率不是 200% 時加一行（普攻看武器範圍、技能看 `skill_profile`；不含背刺，背刺另有一行）。200% 時不顯示。
- 技能卡：技能自帶倍率時，「暴擊範圍 17–20」換成「暴擊 19–20・250%」；沒帶時照舊。
- 「暴擊不加倍」→「暴擊只放大骰子（這部分不放大）」：`skill_primitives.yaml` 的 `flat_bonus` 說明、`workshop_text.yaml` 的 source 與 player、`EffectSpec.flat_bonus` 的說明。
- 對外資料（CLAUDE.md 第 14 條）：預覽是行動者自己的動作、技能卡是自己的技能，都是本人看得到的資料；沒有新增 API 欄位。

### 2.6 種族（B）

- B1：`RaceSkill`、`RacePassive`、`RaceDef` 不再繼承 `_GuardedModel`；`_FORBIDDEN_EFFECT_TYPES` 刪掉；`forbidden_key_problems` 只剩出身用，訊息改成「出身不影響戰鬥，不得給…」。種族技效果與被動規則仍是封閉清單（原則 2 的結構）、原則 3 的檢查（1 AP、次數、效果數、不佔欄、推拉不吃撞擊、投擲不造成傷害）都保留。
- 刪掉的測試：`test_races.py` 的 `test_pure_numbers_are_rejected`、`test_no_bundled_race_data_contains_forbidden_keys`（改成檢查出身）；`test_race_skills.py` 的 `test_pushed_damage_spec_is_never_used_by_race_skills`。`test_damage_in_effect_params_is_rejected`、效果類型的測試改成「封閉清單照樣擋」。
- B3 清單擴充（逐一列出）：只有一項——**環境被動加 `stats`（數值類），目前只有 `crit_damage_permille`**。種族技的效果類型（`RACE_EFFECT_SPECS`）、環境被動的規則（`UNIT_RULE_SPECS`）都沒擴充。
- 現有 10 族內容不變（`stats` 都沒寫）。

## 3. 驗收

### 3.1 結果不變（different=0）

基準 `36b7dbdf8`（`git archive` 的 `src`、`content`、`scripts`、`config`）；新版用最後的程式 commit `feef4634a` 的 `git archive`（截圖 commit 只多文件與圖）。腳本在暫存區（`compare78.py`、`budget.py`、`census_cmp.py`，同 E4）。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`） | `cmp` 0，逐位相同（A5 commit 後、最後 commit 各一次） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0 whole_equal=True` |
| 78 場（`compare78.py`，a 段那組；`format` 也比） | A1 後：`battles=78 events=26741 different=0`；最後：`battles=78 events=26741 different=0`。內嵌規則包只差 `core.crit_damage`、`skill_limits.min/max_crit_permille`（missing → 預設值）與 `flat_bonus` 說明的用字 |
| CLI 快照、parity（slow） | 見 3.3 |

`LOG_FORMAT` 不升版（`/138`）：沒有新事件欄位，新增的狀態欄位（`WeaponDef.crit_permille` 等）沒值時不輸出，78 場的 `setup`、`final_state` 逐位相同。

### 3.2 新機制的測試

| 驗收條件 | 測試 |
|---|---|
| 250%、150% 的算法與捨去 | `tests/engine/test_crit_damage_cr1.py::test_the_design_example`（5.4.2 的例子 ×10：140／110／170）、`test_the_extra_set_is_floored`、`test_exploding_dice_in_the_extra_set_are_amplified_too`、`test_the_preview_distribution_at_two_hundred_fifty_percent` |
| 屬性和固定值不放大 | `test_crit_damage_cr1.py::test_attribute_and_flat_are_not_amplified`（150／200／250／300%） |
| 200% 結果、亂數取用次數 | `test_crit_damage_cr1.py::test_two_hundred_percent_matches_the_old_doubled_dice`（36 組：骰值、傷害、擲完的亂數狀態和「一次擲兩倍顆數」相同）、`test_the_preview_distribution_matches_at_two_hundred_percent`；另 78 場 different=0 |
| 詞條遞減、全身上下限 | `tests/engine/test_crit_sources_cr1.py::test_the_same_affix_diminishes`（100＋50＋25）、`test_everything_adds_up_and_then_the_cap_applies`；`tests/engine/test_crit_weapon_cr1.py::test_the_attack_weapon_sets_the_base_and_the_body_caps_apply`（3600→3000、1100→1500）、`test_the_caps_come_from_the_core_rules` |
| 種族的暴擊傷害有加進去 | `tests/engine/test_crit_race_cr1.py::test_the_race_adds_to_the_crit_damage`（+150、−300、+1000→上限） |
| 技能預算 200% 與 250% | `tests/skillgen/test_crit_budget_cr1.py::test_at_two_hundred_percent_nothing_changes`、`test_two_hundred_fifty_percent_on_the_skill`、`test_a_spell_counts_its_whole_damage_as_dice` |
| 重播確定性 | `test_crit_weapon_cr1.py::test_the_replay_is_deterministic_with_a_custom_multiplier`（250%，6 個種子，事件與亂數狀態） |
| 其他 | 武器、單位、天生武器欄位（`test_crit_weapon_cr1.py`）、修正技與技能自帶（`test_crit_sources_cr1.py`）、顯示（`tests/engine/test_crit_display_cr1.py`） |

### 3.3 檢查指令

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy`、`uv run lint-imports`（每個 commit 前） | 0 |
| `uv run trpg content check` | 0（705 個檔、442 招通過預算） |
| `uv run python scripts/hardcoded/classify.py --check` | 0（沒歸類 0；新增 3 條規則＋`_crit_factor` 併進既有規則，`寫死數值-清單.md` 重產） |
| `corepack pnpm -C client typecheck`（tsc） | 0 |
| `uv run python scripts/check.py --all`（合併 main 後） | 第 1 次 1：`tests/test_x10_rescale.py`、`tests/test_x10_fields.py` 兩個失敗（新數字欄位沒列進 `scripts/x10/fields.yaml`）→ 補成 keep（`4fe6c88b0`）。第 2 次 **0**：pytest 18677 passed、8 skipped；vitest 410 檔 4916 passed；寫下通過戳記 |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed）；CLI 快照、parity 沒變，不用重產 |
| `corepack pnpm -C client build` | 0 |

合併 main 之後 `src`、`content`、`config` 和比對用的 `feef4634a` 完全相同（`git diff --stat` 空），3.1 的比對結果適用於交件版本。

測試輸出（暫存區）：`check_all.log`、`check_all2.log`、`slow.log`、`build2.log`、`c78_a1.log`、`c78_final.log`、`census_new.log`、`budget_final.txt`。

### 3.4 截圖（交給美術 PM）

內容複本（暫存區）：匕首 `crit_permille: 2500`、瞬步背刺加 `crit_range: 19`、`crit_permille: 2500`、一個起始包（匕首＋瞬步背刺、踢翻）；靶場、`?dev=1&mute=1`，無頭 Chrome 加 `--mute-audio`。

- `docs/art/shots/cr-1/cr1_attack_preview_1600x900.jpg`：普攻預覽「暴擊 19–20・250%」
- `docs/art/shots/cr-1/cr1_attack_preview_800x600.jpg`：同上，800×600。⚠ 這個寬度下目標的浮動卡蓋住左邊預覽面板的右半（「暴擊 19–20・2…」），是既有的版面重疊，這段沒改前端
- `docs/art/shots/cr-1/cr1_skill_card_1600x900.jpg`：技能卡展開「詳細」，兩條傷害都寫「暴擊 19–20・250%」
- `docs/art/shots/cr-1/cr1_skill_card_800x600.jpg`：同上，800×600

截圖後伺服器（8791 埠）與 Chrome 都用自己的 PID 關掉，確認沒有殘留。

## 4. 複雜度

沒有新增 `noqa`。超標的地方都拆了：`build_gear` 拆出 `_stat_total`（第 1 類數值放查詢還是併進範本）、卡片的 ‰ 改變句子改成表 `_PERMILLE_CHANGE_TEXT`、預算拆出 `_crit_factor`。

## 5. 數值疑慮（請玩法 PM 記進平衡待查）

1. 修正技「暴擊傷害 +10%」每次 25 milli（5% × 10% × 0.7 × 7）：all_attacks 10 次只值 0.25 點，+100% 也才 2.5 點，很便宜；但全身上限 300% 擋住。
2. 裝備詞條 +10% ＝ 3 點，和「暴擊範圍 +1 ＝ 15 點」相比：+10% 的期望值大約是範圍 +1 的 1/10（範圍 +1 是暴擊率 +5%，等於整組多擲骰的 5%），3 點相對偏貴（照設計「刻意抓貴」）。
3. 技能自帶倍率和武器倍率相加：匕首 250% ＋ 自帶 250% ＝ 300%（上限）。高倍率武器配自帶倍率的招很快頂到上限，自帶倍率的預算仍照「比基礎多出的部分」計，頂到上限時付的點數會比實際拿到的多。
4. 預算的「倍率」用技能自帶或基礎，不看武器；武器技拿高倍率武器時，擴大暴擊範圍的實際價值比預算算的高。

## 6. 待 PM 決定

1. **武器初值沒有逐把寫 2000**：沒寫＝照 `core.crit_damage.base_permille`（200%）。逐把寫會改到單位狀態的武器序列化（78 場的 setup 會不同）。工坊「武器」表每把都能填。
2. **天生武器的工坊欄位是 `existing_only`**（形態表的慣例：只展開已寫的數值，HC-W2 的測試也這樣鎖）。現在沒有天生武器寫值，所以工坊看不到這一格，要先在 `forms.yaml` 手寫一次。
3. **法術技不看武器倍率**，照基礎（同暴擊範圍：法術只有自然 20）。單位檔的倍率寫進單位的武器，所以敵人的法術也不吃單位檔的倍率；頭目要「重擊 300%」的法術，用技能自帶倍率。
4. **技能自帶倍率是「加上比基礎多出的部分」**，不是取代武器倍率（「全部相加」）。範圍初值 1500～3000。
5. **暴擊傷害詞條先不掉落**（`held_back_affixes`）：規格只說「初值 +10%，算 3 點」，沒說進產生器；進了會改掉落與 census。數值固定 +10%（`value` 100～100）。
6. **「被動技」加暴傷用修正技（修正型被動）做**：`kind: passive` 是觸發型，沒有常駐數值的結構。
7. **被動觸發、陷阱等不受修正的施放**不吃修正技的暴傷（同修正技的傷害加成）；裝備、種族、武器、技能自帶照算。
8. **召喚物**：召喚時不經 `weapon_of`，單位檔的 `crit_permille` 不套用到召喚物範本（目前也沒有召喚物填）。
9. **預覽那一行的範圍不含背刺**（背刺另有一行「暴擊範圍 +1」）；修正技的條件看主要目標。角色面板的「暴擊傷害 250%」（5.4.2 第 8 點）這段沒做，規格只要求預覽與技能卡。
10. 種族 `stats` 目前只開 `crit_damage_permille`；傷害、血量等其他數值要用時再加欄位。工坊還沒開種族表（規格沒要求）。

## 開發 PM 裁定（2026-11-23）

**驗收通過**，合併為 `d7b642c4a`。`check.py --all` 第 2 次 0（18677 passed、vitest 4916）、slow parity／cli 0、build 0；442 招逐位相同、census 204 格 different=0、78 場 26741 事件 different=0（含 format）。沒有新增 noqa，`config/` 沒動。

- 第 1、2、5、10 點：保守做法，接受。
- 第 3、4、6、7 點：屬規則解讀，接受現做法，轉玩法 PM 確認並補 5.4.2（法術技不看武器倍率、技能自帶倍率是加上多出的部分、被動加暴傷用修正技、召喚物不套單位檔倍率）。
- 第 8 點：角色面板顯示「暴擊傷害 N%」記佇列 (v)，用字請玩法 PM 定。
- 第 9 點：轉玩法 PM 記平衡待查。
- 800×600 預覽被目標浮動卡蓋住右半：既有版面問題，轉美術 PM 看。
- 守則 14：新增的暴擊倍率顯示在自己的預覽與技能卡上；敵方武器倍率目前不另外顯示。
