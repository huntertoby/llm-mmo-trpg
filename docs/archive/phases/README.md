# docs/archive/phases/

已結案的階段報告（Phase 0～5、Phase 6 已結案系列、BAL 報告、閃現／複合技轉型、Phase 3 審查等）由 `docs/phases/` 搬到這裡，**檔名不變**（`git mv`，歷史與 grep 都保得住）。計畫檔（`docs/phases/*計畫.md`）留原地，只在檔頭加結案標記。報告裡的 `img/` 相對連結已改成根路徑 `docs/phases/img/`（圖片留原地）。

`docs/phases/BAL-*/` 子目錄的 `.md`（量測摘要表，2026-11-06 DOC-A 刪 114 檔）已刪，可由 `scripts/` 重產；同目錄的 `.csv`／`.json`／`.json.gz`／`.log` 是腳本輸入或不可重產的底稿，**不刪**。對應腳本（用法見各腳本 docstring 的 `--out docs/phases/BAL-N/...`）：

| BAL 目錄 | 重產腳本 |
|---|---|
| `BAL-3/` | `scripts/balance_baseline.py` |
| `BAL-4/` | `scripts/difficulty_sweep.py` |
| `BAL-6/` | `scripts/attrition_sweep.py` |
| `BAL-7/` | `scripts/boss_support_sweep.py` |
| `BAL-8/` | `scripts/bal8_measure.py` |
| `BAL-8b/` | `scripts/bal8b_measure.py`、`scripts/bal8b_melee_boss.py` |
| `BAL-9/` | `scripts/bal9_sweep.py` |
| `BAL-9b/` | `scripts/bal9b_analyze.py`、`bal9b_boss.py`、`bal9b_pierce.py`、`bal9b_targets.py` |
| `BAL-9c/` | `scripts/bal9c_boss.py`、`scripts/bal9c_pierce.py` |
| `BAL-10/` | `scripts/flash_converge_measure.py`、`scripts/flash_reclaim_measure.py`、`scripts/flash_minor_coverage.py`（minor_coverage） |
| `BAL-11/` | `scripts/bal12b_measure.py`、`scripts/flash_minor_coverage.py`（minor_coverage） |
| `BAL-12/` | `scripts/bal13c_matrix.py`、`bal13d_matrix.py`、`matrix_ranks.py`、`skill_diagnosis.py`、`synergy_audit.py`、`flash_minor_coverage.py`（minor_coverage）；`12a_matrix.json`／`12d_matrix.json` 是 13c／13d 的輸入 |
| `BAL-13/` | `scripts/synergy_audit.py`、`scripts/weak_build_audit.py`；`13b_collect.json.gz` 是 13d 的輸入 |
| `BAL-14/` | `scripts/bal14a_summons.py` |
| `BAL-15/` | `scripts/bal15a_resources.py`、`bal15a_pool.py`、`bal15a_table.py` |
| `BAL-16/` | `scripts/bal16_block_riposte.py`、`bal16a_boss.py`、`bal16b_heal.py` |
| `BAL-18/` | `scripts/skill_balance_audit.py` |
| `BAL-19g/` | `scripts/skill_balance_audit.py` |

更早的 `LOG_FORMAT` 版本流水在 `戰鬥紀錄格式變更-舊版.md`（最近 10 版仍在 `docs/phases/戰鬥紀錄格式變更.md`）。

> 2026-11-06（R2）：階段代號命名的測試檔已按主題改名或合併，這裡的已結案報告提到的 `tests/...` 舊檔名多半已失效；對照表在 `docs/archive/phases/PhaseR2報告.md`。

> 2026-11-12（整理，使用者「都照建議」）：再由 `docs/phases/` 搬入 54 份已結案報告，檔名不變（`git mv`）：QK-1～9（含 QK-6a）、RT-1／2／3／3b／4／6、6F-21／22、6R-1／2／F／P、6T-1a～1d、UI-E1／E1b／E3／E3b、R1a～R1e、R2～R4、CODE-1～3、DOC-A／DOC-B、MAC-1／2、LLM-1、`PERF-1`／`PERF-2`、HID-1、TR-1、AU-1～3、I8。文件裡 `docs/phases/<這些報告>` 的路徑已改成本目錄；只寫檔名的引用沒改。**沒搬**：`Phase5計畫.md`（程式、內容、測試註解大量引用）、`Phase6F-19報告.md`／`Phase6F-20報告.md`（`client/src/ui/badgeCapsule.test.ts` 引用）、`PERF-3報告.md`（`src/trpg/skillgen/candidates.py` 引用），以及仍在進行或被引用中的 QI、CB-4、BAL-20／21、NW、OB-6、PR-2、IP-1 等。
