# BAL-14b 完成報告｜召喚批套用

規格：`docs/phases/PhaseBAL計畫.md` 最末段「BAL-14b」（玩法 PM 2026-11-02）。分支以 main `295663f6` 為底。

## 1. 改了什麼

| # | 項目 | 改動 | commit |
|---|---|---|---|
| 1 | 精英召喚 | `content/skills/skill_summon_elite.yaml`：`summon_damage_permille` 500 → 250、`summon_duration_delta` 2 → 1（HP +50%、上限 −1 不動） | `285eb507` |
| 2 | 鷹隼 | `content/rules/core.yaml` `summon_role_hp_permille.scout` 2400 → 3000 | `793a7e74` |
| 3 | 刪 `boss_blocker_points` | `SummonAiRules` 的 `boss_blocker_points`／`boss_blocker_slack`、`engine/ai/summon.py` 的 `blocker_gains`／`blocking_summons`、`utility.py` 的呼叫、`ai_profiles.yaml` 的欄位與註解；`tests/engine/test_summon_growth.py` 刪掉 3 個擋路加分測試（`test_boss_ai_actually_attacks_the_blocking_summon` 保留：只有普攻時頭目照樣打擋路召喚物） | `2ba009f5` |
| 4 | 長戰情境 | `scripts/bal14a_summons.py flow --long`：`std_enemy_t5` 複本、範本 HP ×20、上限 10 輪；分「會反擊」與「不反擊」（`idle`、速度 0，防禦不變）兩種。另加 `matrix --builds`、覆寫 `mod.<技能>.<欄位>=<值>` | `26fd2c9c`、本報告 commit |
| 5 | 重量 | 見第 3 節 | 本報告 commit |

**精英召喚的預算**：改完後預算比 93% → **10.7%**（同時上限 −1 抵 3500 點，比 HP＋傷害＋持續還多），`trpg content check` 會報 `budget.weak`。規格說不改召喚預算，所以採最保守做法：把 `skill_summon_elite` 列進 `content/skill_budget.yaml` 的 `known_budget_exceptions`（不改計價），交玩法 PM 決定（見第 5 節）。`trpg skills budget --all` 的例外說明原本寫死「射程係數，見 Phase3-49報告」，改成通用的「見 skill_budget.yaml 的 known_budget_exceptions」（`src/trpg/cli/budget.py`）。

## 2. 測試、快照與重產

- 寫死數值的測試改讀 content：`tests/engine/test_summon_mastery.py`（精英的 HP／傷害／持續改讀技能的修正值，測試名 `..._two_extra_rounds` → `..._extra_rounds`）、`tests/cli/test_budget_cli.py`（通過數與已知例外數改讀 `known_budget_exceptions`）。
- 行為快照 `tests/skillgen/fixtures/refactor_3wr2.json`：只有 `skill_summon_elite` 兩筆變（`8acfcfb9`）。
- CLI 輸出快照 `tests/cli/snapshots/cli_output_hashes.json`：只有 `skills_list`、`skills_show_all` 兩筆（精英說明文字），戰鬥輸出不變（`UPDATE_CLI_SNAPSHOTS=1`）。
- client fixture：`client/src/render/fixtures/skill_icons.json` 1 行（`uv run python -m tests.narrative.icon_fixture`）。`scripts/export_client_fixtures.py` 重跑後 glossary／unitDolls／raceLooks 沒有變。
- 沒有靠種子的測試需要重挑。**戰鬥紀錄格式沒變，`LOG_FORMAT` 維持 /94。**

## 3. 重量結果（`docs/phases/BAL-14/14b_*`；約 9 分鐘，`--jobs 6`）

**長戰單體 DPR**（`14b_long.md`，每格 40 場；我方 DPR ＝ 我方總傷害 ÷ 輪數；舊精英 ＝ 記憶體內覆寫回 500／2，`14b_long_old_elite.md`）：

| build | 會反擊：輪數／DPR | 不反擊：DPR | 對普攻流（不反擊） |
|---|---|---|---|
| 普攻流弓手 | 5.8／17.6 | 19.9 | 100% |
| 技能流弓手 | 8.0／14.1 | 17.7 | 89% |
| 召喚師 | 7.5／16.4 | 17.5 | 88% |
| 精英召喚（新） | 9.8／**27.3** | 20.5 | 103% |
| 精英召喚（舊） | 9.9／30.4 | 28.2 | 142% |
| 群召 | 10.0／**26.1** | 21.3 | 107% |

- 不反擊時（純輸出）精英從 142% 降到 103%，群召 107%：都只略高於普攻流。
- 會反擊時普攻流與技能流英雄分別在 5.8、8.0 輪倒下，精英／群召的召喚物替英雄擋傷害、撐滿 10 輪，DPR 是普攻流的 155%／148%。也就是說，長戰時召喚流多出來的輸出來自存活，不是單位時間的傷害。

**三情境**（`14b_flow.md`、`14b_flow_old_elite.md`）：精英單體 DPR 25.2 → 23.1、範圍 44.7 → 40.4、Boss 勝率 95% → 92%。

**矩陣**（10 圖 × 30 種子，`14b_matrix.md`、`14b_matrix_old_elite.md`）：build_summon_elite 89.7% → **86.0%**；build_summon_swarm 88.3%；build_summoner 74.3%（不變，依規格接受偏高）。

**召喚包**（`14b_packs.md`，18 包 × 5 張正式圖＋Boss × 10 種子）：鷹隼一般戰被打倒 **70% → 44%**（進 10～50%），勝率 66 → 68%；Boss 戰 78% → 74%（每包 10 場）。其餘 17 包逐格與 BAL-14a 相同。

**Boss**（`14b_boss.md`，每包 60 種子）：有召喚 49.4%／10.3 輪、無召喚 23.9%／9.2 輪，**與 BAL-14a 逐格相同**（刪掉擋路加分不影響結果，和 BAL-14a 設 0 時一致）。

## 4. 檢查

ruff check、ruff format --check（src／tests／scripts）、mypy（927 檔）、lint-imports（7 契約）通過。pytest（`-n 6`）：`tests/engine`＋`tests/skillgen`（含 slow）7958 通過後重產快照再過 732；`tests/content` 等相關檔 1641；`tests/sim`＋`roguelite`＋`narrative`＋`api`＋架構 997（重產 icon fixture 後再過 16）；`tests/cli`（含 slow）156；CLI 輸出快照通過。重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 一致（100 個動作、303 個事件）。

## 5. 待 PM 決定

1. **（規則）** 精英召喚預算比只剩 10.7%，暫時列為已知例外。要嘛重訂召喚專精的計價（例如 `summon_limit` 3500 點對 −1 的抵扣改小；但群召 +1 也用同一個值，改了群召會跟著變），要嘛接受它在預算外。
2. **（原型數值）** 精英召喚降了以後矩陣仍有 86%、群召 88%（召喚師 74% 已接受）。長戰會反擊時兩者 DPR 是普攻流的約 1.5 倍（來自存活）。要不要再調，或一起接受。
3. **（原型數值）** 鷹隼 Boss 戰被打倒仍有 74%（每包只有 10 場）。規格決定 Boss 對召喚物 ×2 不改，所以這項只記錄。
4. **（規則）** `docs/design/06-技能.md` 823 行還寫「Boss 的 AI 會優先清掉擋路的召喚物」，程式已經刪了這個加分。設計文件要由玩法 PM 改。
