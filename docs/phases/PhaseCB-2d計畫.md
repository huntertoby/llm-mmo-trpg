# Phase CB-2d｜#149 收尾：換招、雨中梯田、碎晶之主分 build

> 來源：玩法 PM 審 CB-2a（commit 1f7c13e2，`docs/design/18-雲嶺內容.md` 18.2、`docs/玩法決定紀錄.md` #149）。前置報告：`docs/phases/PhaseCB-2a報告.md`。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 雨中梯田倒下 ≤ 40% | 不放寬。先敵方 HP −10%，不夠再減 1 人 |
| `shock_follow`（碎晶之主） | 換一招 AI 會選、傷害不高於 `shard_erosion` 的招 |
| `whirlwind`（霧鎖真人） | 換 `execute` |
| `aim_hit_permille` | 700（`content/ai_profiles.yaml`） |
| `magma_slug` 智力 | 4 → 8；黏液不開縮放例外 |
| `frost_feather` | 名字與數值已通過 |
| 硬殼 | 維持 `parry_riposte`，遠程不套；招重複時不套，改抽其他詞綴（程式確認是否已是這樣） |
| 控制與推擠門檻 | 不拆 |
| 個性差異 | 不調 |
| `ruined_fort` 25%、霧鎖真人 95%、「瞄準」價值下降 | 記平衡待辦，**本段不調** |

## 範圍外

- 不調其他數值，不做 #150、#147、1 階技能平衡。
- #150 改第 3 步配備後，雨中梯田要再量一次（屬於 #150 的驗收）。

## 交付項目

1. 上表的內容修改。
2. **雨中梯田**：用 `scripts/archive/f4d_terrace_sweep.py` 的做法（可複製到 scratch 改寫，不要動 `scripts/archive/`）量敵方 HP −10%；未達 ≤ 40% 才減 1 人。選最小的改動。
3. **模擬**（內容都完成後跑一次，輸出摘要表）：沿用 `scripts/cb2a_sim.py`：新手戰各武器的倒下率、三個頭目的勝率與輪數，**碎晶之主分 build 統計（每個 build ≥ 40%，列出未達的）**，`shock_follow` 替代招與 `execute` 的施放次數，AI 瞄準使用率。

## 受影響的既有功能

| 項目 | 影響 | 處理 |
|---|---|---|
| CLI 快照、固定種子測試 | 數字會變 | 重產前逐類說明原因；確定性與重播比對不可放寬 |
| `tests/skillgen`（`test_enemy_only` 等固定名單）、`tests/narrative`（圖示 fixture）、`tests/roguelite`（固定種子） | CB-2a 曾在合併後才抓到 | **這三個目錄要跑** |
| 世界日誌 | 內容 digest 會變 | `WORLD_RULES_VERSION` 不加一 |

## 行為一致測試

- 表格測試，**實際跑引擎**：碎晶之主三柱階段的 3 招都能施放，AI 會選到替代招；`magma_slug` 的命中率反映智力 8。
- 資料測試：第一季敵人招數仍達 18.2 表格。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/content`、`tests/engine`、`tests/sim`、`tests/world`、`tests/api`、`tests/cli`、`tests/skillgen`、`tests/narrative`、`tests/roguelite`、`tests/test_architecture.py` 通過（CLI 快照帶 `TRPG_FULL=1 -m "not llm"`）。
- 至少 3 張地圖 `--log-json` ＋ `replay` 通過。

## 報告

`docs/phases/PhaseCB-2d報告.md`：逐條驗收、雨中梯田採用的調整與前後倒下率、替代招、模擬摘要、待 PM 決定。
