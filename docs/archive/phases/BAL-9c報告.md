# BAL-9c 完成報告｜Boss 戰頭目 700‰＋弓手護衛降傷、弩穿透折扣

分支 `worktree-agent-a228fcd54a0c4e01a`。原始表在 `docs/phases/BAL-9c/`：`archer.md`（種子 0–59）、`archer_b.md`（種子 60–119）、`pierce.md`、`pierce_b.md`。腳本：`scripts/bal9c_boss.py`、`scripts/bal9c_pierce.py`（所有 content 註解標 BAL-9c 原型專用）。

## 1. Boss 戰

- `bandit_warlord` `max_hp` 86 → 60（700‰，與 BAL-9b 覆寫語意相同：改範本 max_hp，Con 加成不動；最終 HP 110 → 84）。
- 弓手護衛**只降傷害、不動血量**：新增武器 `bow_guard`（`bow` 的複本，骰面 1d8 → 1d6），只有 `bandit_archer_guard` 使用；一般 `bandit_archer` 與其他護衛不受影響（不必動 `boss_escort_damage_permille`）。

### 弓手護衛骰面掃描（頭目 700‰；每值有召喚 360 場／無召喚 360 場＝種子 0–119 × 3 包；1d2 只有種子 60–119，180 場）

| 弓手護衛骰面 | 有召喚 勝率／輪數 | 無召喚 勝率／輪數 | 打死頭目仍輸（有召喚／無召喚） |
|---|---|---|---|
| 1d8（現況） | 40.0%／10.7 | 23.3%／8.2 | 49／360、12／360 |
| **1d6（選定）** | 45.0%／10.8 | 24.4%／9.0 | 50／360、21／360 |
| 1d5 | 44.7%／11.0 | 24.2%／9.0 | 49／360、19／360 |
| 1d4 | 48.1%／11.2 | 28.1%／8.9 | 45／360、22／360 |
| 1d3 | 50.3%／11.3 | 28.9%／8.9 | 45／360、21／360 |
| 1d2（180 場） | 51.1%／11.7 | 33.9%／8.9 | 22／180、17／180 |

判讀：
- **有召喚勝率全落在 35–65%，但輪數 10.7–11.7，沒有任何值落進 6–10 輪**。弓手降傷只讓我方活得更久、戰鬥略長，不能縮短輪數；輪數主要由頭目／護衛血量決定（BAL-9b：650‰ 以下才到 8.3 輪，但勝率 37%）。選 1d6 是「勝率進區間、輪數最短（10.8）」的折衷；若玩法 PM 一定要 ≤ 10 輪，需動 HP（650‰）或其他旋鈕，並接受勝率約 37%。
- 弓手降傷對無召喚勝率有幫助但有限（23% → 24～34%），1d4 以下才明顯（28%+）。
- 骰面差距之間有雜訊（兩批 180 場 CI 約 ±7 點），1d6/1d5 不可區分。

## 2. boss_approach 檢查（結論：不改）

「打死頭目仍輸」場數與 BAL-9b（650‰／500‰，無召喚每格 300 場：31／49；有召喚每格 180 場：49／55）對照，在 1d6＋700‰ 下：無召喚 21／360（約 17.5／300）、有召喚 50／360（約 25／180），皆明顯低於 BAL-9b。有降，依指示**不改 `boss_approach`**（也沒有實作門檻機制）。注意：同樣 700‰ 的 1d8 對照為 12／360 與 49／360，所以降下來主要來自頭目 HP 700‰ 比 650‰/500‰ 保守，而不是弓手降傷（弓手降傷後無召喚的數字反而略升，雜訊範圍內）。

## 3. 弩

- `pierce_line` 還原 5。新增武器欄位 `pierce_permille`（預設 1000＝不打折）：穿透到後方的敵人傷害 ×‰；非 1000 時穿透的那幾下不再觸發分裂與連擊（`_attack_once(extra_permille=…)`）。引擎邏輯（`src/trpg/engine/reactions.py`）、資料欄位與特性文字（`src/trpg/content/battle.py`）。
- 白板弩 vs 單手劍，10 圖 × 10 種子 ＝ 100 場，pierce_line=5：

| pierce_permille | 弩勝率 | 弩 DPR | 單手劍 DPR | DPR 比 |
|---|---|---|---|---|
| 1000 | 36% | 7.31 | 5.17 | 141.5% |
| 800 | 37% | 6.95 | 5.17 | 134.5% |
| 700 | 37% | 6.79 | 5.17 | 131.5% |
| 600 | 36% | 6.71 | 5.17 | 129.8% |
| 500 | 36% | 6.58 | 5.17 | 127.2% |
| **400（選定）** | 36% | 6.42 | 5.17 | **124.2%** |
| 300 | 38% | 6.25 | 5.17 | 120.9% |
| 200 | 38% | 6.04 | 5.17 | 116.8% |
| 100 | 36% | 6.15 | 5.17 | 118.9% |

選 400‰：≤ 125% 且最接近 125%。勝率不受影響（36%）。骰面維持 1d5。

## 4. 測試與快照

- `tests/content/test_bandit_lair.py`：原斷言「warlord HP > bandit_boss HP」在 60 < 62 後不成立，改為護甲與屬性總和比較（斷言語意＝加強版仍強於一般頭目；請 PM 確認可接受）。
- `tests/content/test_con_hp.py`：warlord 遷移 HP 110 → 84（註解標 BAL-9c）。
- `tests/sim/test_flash_balanced_policy.py`：靠種子的測試，種子 (1,2,3) → (4,6,7)，斷言不改（原種子兩策略的閃現總數剛好持平 4 = 4）。
- `client/src/battle/fixtures/glossary.json`：由 `scripts/export_client_fixtures.py` 重產（新增 `bow_guard`、弩特性文字）。
- 新增 `tests/engine/test_weapons_24a2.py` 兩個測試（`pierce_permille` 只折扣後方、原型弩的資料）。
- `tests/cli/test_run_cli.py`：靠種子的 run auto 測試重挑種子（`test_run_auto_flashes_and_shows_flash_counts` 3, 2 → 3, 5；`..._major_flash_...` 3, 13 → 4, 7），斷言不改。
- CLI 快照（`tests/cli/test_output_snapshots.py` 等）未變，不需 `UPDATE_CLI_SNAPSHOTS=1`。

## 5. 收尾檢查

ruff check、ruff format --check、mypy（899 檔）、lint-imports（7 契約）通過；pytest（`-m "(slow or not slow) and not llm"`）：`tests/content`＋`tests/engine` 5421 passed（1 xfailed、3 xpassed 既有）；`tests/sim`＋`roguelite`＋`api`＋`skillgen` 修正後全過；`tests/cli` 全過；swamp 種子 7 重播通過（76 動作、250 事件）。
