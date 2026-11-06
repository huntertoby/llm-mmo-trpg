# BAL-2b 完成報告（閃現 AI 三種玩家、觸發／修正類基本分、姿態模板適用範圍）

> 實作者報告。分支：`worktree-agent-a694ba18cc1554fbf`（從 `main` 快轉後開工，含 BAL-2 與玩法 PM 的 f5ae18fe）。

## 1. Commit 列表

| Commit | 內容 |
|---|---|
| `35d7b7a5` | A：均衡閃現 AI（`balanced`）＋測試 |
| `12cd3377` | B：觸發、修正類模板的基本用法分（資料驅動）＋測試 |
| `a164bad7` | C：沒有階梯的單一狀態姿態（狂怒、堅壁…）適用費用／修正類＋測試 |
| （下一個） | D：稽核腳本加 `--policies` |
| （本報告） | docs: BAL-2b report |

## 2. 做了什麼

### A. 閃現 AI 三種玩家
- 名稱照現有：`none`＝**集中**（閃過最多次的先閃）、`all`＝**全指定**（同樣集中，每次指定類別）、`mixed` 原義不變、新增 `balanced`＝**均衡**。
- 均衡：優先閃沒閃過的技能；候選之間挑「該種類已閃次數最少」的種類（同次數依 主動、被動、反應、姿態、修正型被動），再取技能列順序；全部閃過後改挑閃過最少次的。不指定類別。
- `--flash-policy`（`trpg run auto`）與 `trpg sim flash --policies`、稽核腳本 `--policies` 都收 `balanced`。`FLASH_POLICIES` 仍是 `("none","all","mixed")`（`sim flash` 預設與既有測試不動），新增 `ALL_FLASH_POLICIES`（含 balanced）。預設行為不變。

### B. 觸發、修正類的基本分
- `FlashTemplate.usage_base`（預設 0，加在 `_usage_score` 上），資料寫在 `content/flash_templates.yaml`：trigger_potency 2、trigger_range／range_wide／cap 1、mod_potency 2、mod_range 1、mod_relax 1、stance_potency 2；mod_keyword 維持 0（有訊號時原有 2 分）。其他類別不變。
- 測試：基本分只出現在觸發／修正類模板；被動／反應的 `category_ranking` 觸發類不再固定最後。

### C. 姿態模板適用範圍
- 姿態分三族：**元素姿態階梯**（不動）、**沒有階梯的單一狀態姿態**（狂怒、堅壁；新增支援）、**變身姿態**（見下，目前不出）。
- 單一狀態姿態：費用類（蓄力）＝維持費 +1、姿態幅度提高；輕巧＝維持費 −1、幅度降低（要有維持費才能減）；修正類＝維持費不變、幅度提高（嚴格變強）。幅度用既有的 `apply_status.magnitude_permille`（完整技能 3W-5b 已在引擎與卡片落地），級距寫在 `flash_templates.yaml` 的 `rules.stance_magnitudes`（1000～2000，比完整技能寬，因為這些是固定點數，角色 2、3 階時要靠幅度拉進預算窗）。
- 行為一致測試（`tests/skillgen/test_flash_stance_all_bal2b.py`）：1～3 階都合法、預算比例在窗內、分數不低於（修正類嚴格大於）變化前、卡片數字＝引擎倍率。
- 觸發範圍（self 形狀不出「觸發範圍 +1」）與沒有條件的修正型被動：照現狀擋，未動。
- 因行為改變，更新一個既有測試：`test_a_focused_category_with_no_option_is_refused_before_paying` 原本拿堅壁姿態當「沒有合格選項」的例子，改用變身姿態（熊）。

### D. 稽核重跑（腳本 `--seeds 3 --board-seeds 10 --sim-seeds 20 --jobs 8 --policies none,balanced,all`）

前（BAL-2）→ 後（BAL-2b）：

| 項目 | 前 | 後 |
|---|---|---|
| 姿態「費用」類可指定 | 2.6% | **18.4%** |
| 姿態「修正」類可指定 | 5.3% | **21.1%**（stance_potency 合法 2 → 8 / 38） |
| 全指定策略下，被動／反應的 trigger 平均名次 | 2.2／2.2（最後） | 無統計 1.0／2.2、多目標 1.0／2.2、單體 2.1／2.2 |
| 排名第一是 trigger（被動 65、反應 54 題） | 無統計 4／0、多目標 4／0 | 無統計 **61／43**、多目標 **61／43** |
| 姿態 `category_ranking` 的 modifier 名次 | 1.5 | 1.0 |
| trigger／modifier 排第一變化的用法分 | 恆 0（單體常用 modifier 0:38, 2:57） | trigger 恆 2、modifier 恆 2 |
| 單體常用的被動／反應 | trigger 4／0 排第一 | 單體常用時 element／extend 較高（3 分）仍領先，trigger 排第 2 |

一輪模擬（20 種子，每場約 2～3 次閃現，樣本小）：

| 策略 | 出題數 | 閃的技能：主動／被動／反應／姿態／修正 | trigger 出現在選項（題數比） | trigger 被選 |
|---|---|---|---|---|
| none（集中） | 66 | 65／1／0／0／0 | 2（1.5%） | 0 |
| all（全指定） | 44 | 44／0／0／0／0 | 0 | 0 |
| balanced（均衡） | 66 | 61／4／1／0／0 | 8（7.6%） | **4（6.1%）** |

## 3. 驗收

- `uv run ruff check`、`ruff format --check`、`mypy`（852 檔）、`lint-imports`（7 條契約）：通過。
- `pytest`：`tests/skillgen`＋`tests/roguelite`＋`tests/sim`（-n 8）4073 passed、14 skipped；`tests/cli`（-n 8、`--timeout=3000`）156 passed。
- 新增測試：`tests/sim/test_flash_balanced_policy.py`、`tests/skillgen/test_flash_usage_base.py`、`tests/skillgen/test_flash_stance_all_bal2b.py`。

## 4. 待 PM 決定

1. **變身姿態（10 個）無法套用，這是規則包的結構限制**：`enter_form` 必須是技能唯一的效果（沒有可加的效果）、技能的 `stance_upkeep` 不能填（形態維持費在 `forms.yaml`）、`magnitude_permille` 只有 `apply_status` 能填，所以變身姿態沒有任何每招的強度旋鈕，費用／修正類做不出「效果提高／降低」，且它們在 2、3 階本來就低於預算窗。要讓 6.34.4「適用所有姿態」包含變身，需要引擎與卡片的改動，選項：（a）讓 `FormState` 加幅度或維持費欄位，並改引擎與 `narrative`（會動戰鬥狀態結構與規則包雜湊以外的契約，超出本批範圍）；（b）放寬 `enter_form` 的唯一效果限制，讓變身姿態附帶「進入時護盾」等效果當旋鈕（較小的改動，但要玩法 PM 決定變身姿態可不可以多帶效果）；（c）維持現狀，變身姿態只出大變化（加深、橋接）。我沒有自行擴大範圍，依守則採最保守做法（不出）。
2. 白板與轉型出來的姿態本來就在階梯上（guard／flame／frost 階梯）；稽核「stance」38 個受測對象中，實際受益的是狂怒、堅壁（共 6 個（技能,階級））加原本就合法的 2 個，其餘 30 個是變身姿態。
3. 均衡策略仍很少閃到姿態、修正型被動（0 次）：2～3 點靈感／場，且姿態、修正型被動大多是變身姿態或需要先上場用過；這是資源限制，不是 AI 偏好。若想量到這些種類的實戰表現，需要加大靈感點或指定開局持有（BAL-1 的靈感經濟掃描可補）。
4. 單體常用統計下，全指定策略的被動／反應仍多選 element／extend（3 分高於觸發類的 2 分）；基本分設 2 是保守值，要不要調高由玩法 PM 決定。`usage_base` 在資料裡可直接改。
5. 單一狀態姿態的幅度級距上限 2000‰ 是初值（堅壁 750‰ 受傷倍率在 2000‰ 時約 500‰），未經平衡模擬。
