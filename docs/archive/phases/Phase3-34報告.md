# Phase 3-34 報告｜檢查提速

## 改動
1. `scripts/check.py`：pytest 改 `-n <N>`，N 預設 8，環境變數 `TRPG_PYTEST_WORKERS` 覆寫（數字或 `auto`，其他值直接報錯）。例：`TRPG_PYTEST_WORKERS=auto uv run python scripts/check.py`。
2. `--full`：pytest 加 `-m ""`（含 slow），並設 `TRPG_FULL=1`（前端完整組合、hypothesis 完整樣本）。不帶參數為快速版。
3. 30 個測試函式標 `@pytest.mark.slow`（見下）；3 個 hypothesis 檔的 `max_examples` 平常降為 3，`TRPG_FULL=1` 時回原值（15／12／12），未刪任何測試。
4. 前端 `dollGear.test.ts` 全組合：平常每 8 個組合取 1（確定性），`TRPG_FULL=1` 才跑完整（>5000 張）。

## 時間（機器上另有一個 agent 同時在跑，數字偏高）
| | pytest | check.py 整體 |
|---|---|---|
| 改動前（`-n 8`，含 40 名 durations 全量） | 527 秒 | － |
| 快速版（改動後） | 約 2.5 分（整體 2 分 46 秒，含 ruff、mypy、前端） | 2 分 46 秒 |
| `--full` | 565 秒（含 slow） | 9 分 51 秒 |

快速版 pytest 與前一次相比略有下降幅度因 CPU 競爭而不精確；主要節省來自 slow 標記（CLI 快照 164 秒、auto run 100 秒等）。

## 改動前最慢的前 40 名（秒）
163.9 cli/test_output_snapshots 快照；99.4 test_run_auto_ten_seeds；54.4 skill_determinism 屬性（every_listed_skill_action）；33.3 sim/test_skill_report；27.6 completion 跨 jobs；27.0 status_determinism 屬性；26.8 run_cli spends_skill_points[1]；23.1 run_cli draws_weapon[1]；18.7 commander_cli；17.5 run_cli branching_evolution[5]；14.9 candidates behavior_tilts；14.8 run_cli draws_weapon[3]；14.3 sim_cli stdout；13.1 polish_3c6a cluster_bolt；13.1 api autosave；12.5 skill_determinism never_raise；12.5 run_cli deterministic；11.9 attack_flow_report；11.1 completion fast；10.4 completion cli；10.3 determinism 屬性；10.0 evolution round_trips；10.0 sim/test_batch；10.0 skill_growth；9.6 composer_3c6b；9.2 evolution mid_battle；9.1 matrix cli；8.4 commanders ×2；8.3 run_cli [2]；8.2 run_cli [2]；7.9 branching_evolution[6]；7.5 matrix real；7.5 skillgen evolution；7.1／6.8 orders[參數]；6.9 skill_ai_scenarios；6.8 polish sim_maps；6.7 offers；6.5 skill_infusion。

## slow 清單與理由
- 理由皆為：單一測試 ≥ 5 秒，屬大量模擬／整條 CLI 自動跑局／跨 jobs 重跑比對。
- 標 slow（30 個函式，參數化者整組）：test_output_snapshots、test_run_cli（5 個函式）、test_commander_cli、test_sim_cli、test_run_autosave、test_skill_report、test_completion（3）、test_attack_flow_report、test_batch、test_matrix（2）、test_commanders（2）、test_candidates::behavior_tilts、test_composer_3c6b、skillgen/test_evolution、roguelite/test_evolution（2）、test_skill_growth、test_offers、engine/test_polish_3c6a（2）、test_orders、test_skill_ai_scenarios、test_skill_infusion。
- 縮樣本（不標 slow）：test_determinism、test_skill_determinism、test_status_determinism 的 hypothesis 屬性測試（共 4 個）。

## 待 PM 決定
1. `--full` 的 pytest 有 2 個失敗，與本階段改動無關，是原本被 slow 標記擋住（`pyproject` 預設 `not slow`）而未被發現的既有問題：`tests/skillgen/test_random_composer.py::test_one_thousand_seeds_are_all_valid_and_spread_out` 與 `tests/sim/test_skill_fuzz.py::test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible`，皆為種子 966「50 次重抽都做不出合格技能（階級 5、rare、control、weapon）」。需由技能生成相關階段處理；因此 `--full` 目前整體為失敗，快速版全過。
2. 驗收「`--full` 全過」因上項尚未達成，請決定是否另開修復段。
3. 標記範圍較保守地用規格的 5 秒門檻（機器有競爭時時間偏高，實際可能略少於 5 秒的幾個也被標了）；若覺得標太多可調回。
4. hypothesis 樣本平常降到 3（原 12–15），沒另建 slow 重複版本，改以 `TRPG_FULL=1` 切換。
5. `CLAUDE.md` 與 `docs/開發PM交接.md` 未改，需補 `--full` 與 `TRPG_PYTEST_WORKERS` 說明。
