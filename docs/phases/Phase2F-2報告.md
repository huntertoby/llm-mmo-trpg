# Phase 2F-2 報告：組合器與 AI

## 1. commit 列表

| commit | 說明 |
|---|---|
| `e9e539d` | 4.1：組合器的被動與反應技候選原語改讀骨架 YAML（`core.primitives`／`secondary.primitives`）；新增 `scripts/composer_rejects.py`；`REACTION_EVENTS` 單一來源（`SKILL_REACTION_EVENTS`）；environment 的同名常數改名 `ENV_REACTION_EVENTS` |
| `d88f3e5` | 4.4：`_passive_violations` 的「法術技、`weapon_req: any`」改讀 `passive.yaml` 的 `required_category`／`required_weapon_req`（骨架 schema 新增欄位，預設 `None`） |
| `d1fc67f` | 4.4：`sim/batch.py` 的 `_template_rows` 改用 `_Instance` dataclass |
| `5405022` | 4.2：AI 陷阱數值搬進 `content/ai_profiles.yaml` 的 `trap:`（`TrapAiRules`，原值不變；未知形狀用預設係數） |
| `e4f6940` | 4.3：`_gains` 拆成 `_damage_gains`／`_ally_gains`／`_kill_gains`／`_push_gains`／`_surface_gains`／`_defend_gains` 等 |
| `3051dfb` | 4.3：`compute_area` 拆成 `_unit_area`／`_tile_area`／`_direction_area`／`_self_area` |
| `aeefe30` | 4.3：`cli/main.py` 的 `main` 改用 argparse `set_defaults(func=...)` 分派 |

## 2. 驗收逐條結果（4.5）

1. **候選原語來自骨架 YAML** ✅
   `tests/skillgen/test_composer_skeleton_driven.py`：`test_passive_core_candidates_follow_the_skeleton`（把測試骨架核心改成只有 heal，被動只會產生 heal）、`test_reaction_candidates_follow_the_skeleton`（核心只有 push，反應技只會產生 push）、`test_passive_without_any_allowed_candidate_retries`、`test_intercept_needs_the_skeleton_to_allow_it`、`test_reaction_self_branch_only_uses_skeleton_primitives`。
2. **退回統計前後對照** ✅ 見第 3 節；反應技 `skeleton.core` 退回 108 → 0。
3. **`REACTION_EVENTS` 只有一個定義** ✅
   `grep -rn "REACTION_EVENTS" src --include=*.py`：只剩 `SKILL_REACTION_EVENTS`（`content/skills.py`，唯一來源）、composer 由它導出的 `NON_INTERCEPT_EVENTS`、environment 的 `ENV_REACTION_EVENTS`。測試 `test_reaction_events_have_a_single_source`。
4. **AI 陷阱數值在 `content/ai_profiles.yaml`；未知形狀不會 `KeyError`** ✅
   `tests/engine/test_traps.py`：`test_the_ai_trap_numbers_live_in_the_content_with_their_original_values`、`test_an_unknown_trap_shape_uses_the_default_factor_instead_of_raising`、`test_changing_the_content_trap_limit_changes_the_ai_candidates`。
5. **複雜度 noqa** ✅ `_gains`、`compute_area`、`main` 的 noqa 已移除；總數見第 5 節（19 → 14，減少 5 個，需求至少 4 個）。
6. **3 場對照戰鬥與 2F-1 結束時相同** ✅ 見第 4 節。
7. **`skill_fuzz.py --count 1000` 異常 0；`scripts/check.py` 全過** ✅
   `skill_fuzz`：組合成功 1000/1000、通過驗證 1000/1000、可施放 1000/1000、例外 0。
   `check.py`：ruff、ruff format、mypy、lint-imports、pytest（1395 passed）全部通過。

## 3. 組合器退回統計（`uv run python scripts/composer_rejects.py --count 300`）

每個骨架各組 300 個（明確指定骨架、稀有度隨機）。「退回總數」＝所有技能重抽次數的總和（`attempts - 1`）；原因欄：`attempt:*` 是嘗試階段的例外（`Retry`），`validate:*` 是驗證器回報的違規規則。

| 骨架 | 改動前 退回總數 | 改動前 原因 | 改動後 退回總數 | 改動後 原因 |
|---|---|---|---|---|
| area | 7 | Retry 7 | 7 | Retry 7 |
| aura | 111 | Retry 111 | 111 | Retry 111 |
| builder_finisher | 6 | Retry 6 | 6 | Retry 6 |
| combo | 0 | — | 0 | — |
| control | 632 | Retry 632 | 632 | Retry 632 |
| displace | 257 | Retry 257 | 257 | Retry 257 |
| passive | 100 | Retry 100 | 100 | Retry 100 |
| **reaction** | **335** | Retry 227、**validate:skeleton.core 108** | **254** | Retry 254、skeleton.core **0** |
| stance | 59 | Retry 59 | 59 | Retry 59 |
| strike | 0 | — | 0 | — |
| trap | 25 | Retry 25 | 25 | Retry 25 |

組出 300/300、失敗 0，前後皆同。反應技的 `skeleton.core` 退回（自身增益分支抽到 heal／shield，但反應技骨架核心沒有這兩個原語）從 108 降到 0。反應技的 `Retry` 227 → 254 是因為原本會落在 heal／shield 的抽選，現在在「沒有骨架允許的自身增益原語」時改走對觸發者的分支，或在抽到擋攻擊時重抽，整體退回總數仍減少 81。

## 4. 對照戰鬥比對結果

開工前（HEAD＝`21f7301`）與完成後各跑一次，存到暫存目錄後用 `cmp` 比對位元組：

```bash
uv run trpg battle --map ruined_fort --seed 1 --ally-build build_trapper,build_guardian --log-json <tmp>/{before,after}1.json
uv run trpg battle --map open_plain  --seed 2                                            --log-json <tmp>/{before,after}2.json
uv run trpg battle --map dark_forest --seed 3 --ally-build build_warlock,build_healer    --log-json <tmp>/{before,after}3.json
```

結論：3 場**完全相同**（`cmp` 無差異）。另外在 `_gains`、`compute_area`、CLI 重構各完成後都重跑過一次，皆相同。`trpg battle replay` 與 `rng`、`skills budget` 的 CLI 行為也手動確認過。

## 5. 修改過期望值的測試與原因

無。既有測試的期望值沒有任何改動；也沒有任何依賴特定隨機技能輸出的測試需要更新（組合器抽樣分布改變後全部仍通過）。

## 6. 複雜度類 noqa 數量

計數方式與 2F-1 報告相同（`grep -rn noqa src/` 中含 `C901`、`PLR0911`、`PLR0912`、`PLR0915` 的行，不含 `PLR0917`）。

| | 數量 |
|---|---|
| Phase 2F 開始前 | 19 |
| 2F-1 結束時 | 17 |
| 目前（2F-2 結束） | 14 |

移除 3 個：`_gains`（C901／PLR0912／PLR0915）、`compute_area`（C901／PLR0912／PLR0915）、`main`（C901／PLR0911／PLR0912）。**沒有新增任何複雜度類 noqa。**`_battle` 原有的 `PLR0911` 保留（只是簽名改為 `_battle(args)`）。

## 7. 待 PM 決定

1. **反應技骨架是否要加入 heal／shield**：骨架 YAML 沒有改。結果是反應技的「自身增益」分支現在只剩 `apply_status`（有益狀態）；抽到自身分支但沒有可用原語時改走對觸發者的分支。若想恢復自身治療／護盾型反應技，需把 heal、shield 加進 `reaction.yaml` 的 `core.primitives`。
2. **`content/battle.py` 的 `ReactionWhen.event` 是 Literal**：它是「反應規則」（含 `targeted_by_*` 與反應技事件）的聯集，不是單獨的 `REACTION_EVENTS` 常數，意義與 `SKILL_REACTION_EVENTS` 不同，所以我沒有動它。若想連它也由 `SKILL_REACTION_EVENTS` 導出，需要改成執行期驗證而非 Literal。
3. **AI 陷阱數值的位置**：`trap:` 放在 `ai_profiles.yaml` 表格層級，載入時複製進每個行為模式（與 `trap_likelihood_permille` 同一個機制），各行為模式可以自己覆寫。形狀係數以‰ 整數存放（`cross` ＝ 1500），執行期轉成 `Fraction`，與原值完全相同。未對形狀 ID 做存在性檢查（未知形狀在載入時不報錯，使用預設係數）；是否要在載入時驗證請 PM 決定。
4. **`passive.yaml` 新欄位**：骨架 schema 新增 `required_category`、`required_weapon_req`（預設 `None` ＝ 不限）。驗證違規代碼仍是 `passive.category`，訊息文字略改成引用骨架資料。
5. **`skill_estimate`／`_trap_estimate` 新增 keyword-only 參數**（`trap`／`rules`）以取得 AI 陷阱數值，避免增加位置參數而觸發 `PLR0917`。
