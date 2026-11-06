# Phase 3-50c 報告：代價狀態無法淨化或驅散（玩法決定 #62）

規格：`docs/phases/Phase3計畫.md` 第 60c 節；設計：`docs/design/06-技能.md` 6.3、6.5 共通規則第 8 條。

## 做了什麼（對照規格 1～5 點）

1. **標記**：`StatusInstance.cost_status`（預設 `False`）；`apply_status` 以 `ApplyStatusEffect.self_paid` 寫入（自暈、自我沉默、自我流血、易傷、緩速、定身、透支都經 `pay_self_costs`，一律標記）。
   - `cleanse` 只移除 `polarity: debuff` **且非 `cost_status`** 的狀態；`dispel`／`steal_buff`（`resources._buffs_in_order`）也排除代價狀態。
   - 敵人施加的同種狀態沒有標記，照常可淨化。
   - 重複施加：新狀態較長或相等 → 以新的取代（旗標跟新的）；舊的嚴格較長 → 保留舊實例連同其旗標（自付的 3 回合緩速被敵人 1 回合緩速覆蓋時仍是代價狀態；敵人 5 回合的則取代並可淨化）。回合結束倒數也保留旗標。
   - 透支本來就不是可移除的狀態——實際上 `overdrawn` 是 `polarity: debuff`，先前**可以被淨化**；現在因為自付而標記，淨化不掉。
2. **顯示**：`StatusView.cost_status` 進 OpenAPI；HUD 與單位資訊的狀態文字（含浮動提示）尾端加「（代價狀態，無法淨化）」（`COST_STATUS_NOTE`）；技能卡代價行改為「（換 32% 預算；代價狀態，無法淨化）」（自身狀態與透支兩行），設計文件範例同步。
3. **AI**：`_supports` 的淨化判斷排除代價狀態，只帶代價狀態的目標不會被當成淨化對象。
4. **測試**：`tests/engine/test_cost_status.py`（19 個）：各代價狀態 × 自付不被淨化／敵人施加照常移除（參數化）、混合只移除非代價、淨化技能實際施放、重複施加兩個方向、驅散與奪取排除、回合結束保留旗標與 view、AI 支援判斷。vitest `client/src/ui/costStatus.test.ts`。

## 紀錄格式與影響盤點

- `LOG_FORMAT`：`/74` → **`/75`**（`/74` 紀錄中自付減益可被淨化，無法重播）。測試內寫死 `/74` 的處所改為 `/75`。另一個 agent（3-54a）若也遞增，合併時取較大者並合併 `runner.py` 說明。
- 重產 `client/openapi.json`、`client/src/api/schema.d.ts`；修 vitest／dev 夾具（`cost_status: false`）。
- 卡片文字改變：CLI 快照與相關 fixture 已視需要更新（見下）。

## 驗收

pytest：engine、content、skillgen、narrative、api 全過（6932 passed）；`-m "slow or not slow" tests/cli` 全過（卡片文字改變後更新 `cli_output_hashes.json` 的 `skills_list`、`skills_show_all`）；vitest 992 通過、build、ruff、format、mypy、lint-imports 通過；含四招示範技能（自暈、沉默、流血、透支）的整場戰鬥重播一致（`test_a_battle_with_the_four_demo_skills_replays_identically`）。
