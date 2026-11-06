# Phase 3W-2 完成報告：小變化模板（6.34.4）

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3W計畫.md` 3W-2 列、第 3 節（#70）、第 2 節行為一致；設計 `docs/design/06-技能.md` 6.34.3、6.34.4、6.34.9（#72）；PM 補充：強度下限、完整技能調整欄、姿態與修正類別、#72 最低角色階級。
> 分支：`worktree-agent-aae78ab052111d12d`（已 fast-forward 到 main `f7bd846e` 之後的提交），未 push。範圍：只做小變化；第 3 次大變化與轉型（3W-3）、白板產生（3W-4）、一輪流程（3W-5）都沒碰。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `716eb3d4` | `skillgen/flash_ops.py`（19 個改法）、`content/flash_templates.yaml` 小變化模板與類別、`UsageSource`（依用法統計排序）、強度下限（`budget_power`、`min_ratio`）、角色階級參數、重閃下限 `floor_permille` |
| （第二個） | `tests/skillgen/test_flash_templates.py`（79 個測試）、`test_flash.py` 配合新資料調整 |
| （本報告） | `docs/phases/Phase3W-2報告.md` |

## 2. 驗收

| 項目 | 結果 | 證據 |
|---|---|---|
| 6.34.4 小變化十三類全部實作並登錄；資料有、程式沒登錄會失敗 | 通過 | `test_the_thirteen_families_are_all_in_the_data_and_registered`、既有 `test_every_minor_op_in_the_data_is_implemented`；每個模板至少有一招技能套得上（`test_every_template_has_representative_skills`，33 個模板） |
| 每類模板套到代表技能：驗證器零違規（含 6.6 硬上限）、預算比例在新上限內、+40‰ | 通過 | `test_template_result_is_valid_in_budget_and_never_weaker`（每個模板最多 3 招）：`validate_skill == []`、`skill_budget.ok`、`bonus_permille == 40`、進規則包、技能卡可建 |
| 強度下限（玩法 PM）：預算分數不低於閃現前；重閃不低於被換掉那筆；「效果＋」類嚴格更強 | 通過 | 同上（`budget_power(after) >= before`）；`test_effect_plus_templates_are_strictly_stronger`；`test_power_never_drops_along_five_flashes`（火焰箭、聖光撫慰、餘燼烙印、反射護幕）；`test_reflash_keeps_the_replaced_power_as_floor`（選項帶 `floor_permille`，寫進紀錄，重算一致） |
| 完整技能調整欄：價格同 6.34.3、+120‰ 不變、不低於重閃前、再重閃換掉不累積、溶掉算花費 | 通過 | `test_complete_skill_adjustment_is_not_weaker_and_replaces`（`spent == 2`、`records == ()`、`adjustment.reflashes == 1`） |
| 「修正」類（修正型被動）、姿態可出修正／費用類 | 部分（見待決 #1） | 修正型被動 4 個模板可用；姿態列入類別，但沒有可用模板 |
| #72 最低角色階級：模板有 `min_tier`；出題只出階級能用的；同種子同階級同選項 | 通過 | `test_template_min_tiers_follow_decision_72`、`test_offers_only_use_templates_the_role_tier_allows`（1／2／3 階）、`test_same_seed_same_tier_same_offer` |
| 選項來源 #70：不指定 4 個至少 2 類；指定類別 3 個依用法統計排序；用法少出通用變化 | 通過 | 沿用 3W-1 的混合測試；`test_usage_statistics_reorder_a_category`（遠距離→距離 +1、多目標→範圍 +1、擊殺→收割）、`test_keyword_variations_follow_the_usage_signal`、`test_sparse_usage_offers_generic_variations_first`；指定的類別沒有合格變化時在扣點前拒絕（`test_a_focused_category_with_no_option_is_refused_before_paying`） |
| 行為一致（卡片＝實戰） | 通過 | `test_active_templates_play_in_the_engine`（各主動類模板的結果放進戰鬥，合法動作可結算、傷害預覽範圍包住實際傷害，≥ 12 招）、`test_preview_range_contains_resolved_damage_for_a_flashed_bolt`（多打一下：同一目標兩段命中，預覽範圍包住總傷害） |
| 不影響既有 | 通過 | `tests/skillgen`、`tests/content`、`test_architecture`、`roguelite/test_evolution`、`engine/test_skill_determinism`：3850 通過；`tests/cli/test_budget_cli.py`＋`test_output_snapshots.py`：8 通過（`--timeout=3000`）；`ruff check`、`ruff format --check`、`mypy`（805 檔）、`lint-imports`（7 kept） |

沒有跑完整 `scripts/check.py`。

## 3. 做了什麼

### 3.1 模板（`content/flash_templates.yaml`，33 個小變化；改法在 `skillgen/flash_ops.py`）

| 類別 | 模板（最低階） | 改法 |
|---|---|---|
| 範圍 | 範圍 +1、距離 +1、換成直線 3／錐形 2／十字（1）；換成 3×3（2）；整排直線長 6、連鎖跳躍（3） | 形狀參數；換形狀的目標形狀放在 `Variation.shape` |
| 連段 | 多打一下（1）；接續段（2） | 多打＝第一個傷害效果後複製一個（旋鈕分別調）；接續段＝6.23 的 `on_hit` 複合技，第二段傷害另有旋鈕 |
| 元素與關鍵字 | 第二個關鍵字：製造／利用（1）；第二元素（2）；雙屬性縮放（3） | 沿用橋接的 `graft_makes`／`graft_uses`；第二元素＝多一個別種元素傷害效果；雙屬性＝加 `secondary_scaling_attr`（範圍同工坊選單 `secondary_range`） |
| 費用 | 蓄力：冷卻 +2（≤5）；輕巧：AP −1（≥1）、冷卻壓到 ≤1（1） | 改 `cost`／`ap_cost`，預算器換算 |
| 延長與收割 | 延長 1 回合；擊殺返還 1 AP（1） | 延長沿用「恆久」的草稿；收割＝`on_kill: refund_ap` |
| 輔助 | 效果＋、範圍 +1（1）；範圍 +2（2）；附帶第二個關鍵字（限「潮濕」「暗影」，不傷友方）（1） | 效果＋＝結構不變、上限提高後重調 |
| 觸發 | 觸發範圍 +1（1）、+2（2）；效果＋；每回合觸發次數 +1（≤3） | `trigger.max_distance`／形狀大小 |
| 修正 | 修正幅度＋、作用範圍 +1（射程 +1，或多一條範圍 +1 規則）、第二個關鍵字、條件放寬一級 | 修正規則的 `change` 幅度有專用旋鈕（見 3.3） |

### 3.2 選項來源 `UsageSource`（取代 `DataOrderSource` 當預設）

- 每個模板展開成帶參數的變化（目標形狀、第二元素、第二個關鍵字、第二屬性），類別內依「用法分數」排序，同分依資料順序：多目標→範圍 +1；單體→換形狀、多打一下；平均距離遠→距離 +1；擊殺過→收割；目標身上常有某關鍵字→延長、「利用」該關鍵字（沒有訊號的關鍵字出「製造」）；常用（≥6 次）→輕巧。
- 放出次數 < `rules.usage_min_uses`（3，放在 content）→ 先出 `generic: true` 的通用變化（範圍 +1、距離 +1、延長、各類「效果＋」）。
- 第二個關鍵字候選：沿用橋接的排序（`evolution.bridge_keywords`：前後搭配、目標身上、持有、推導表），再補嫁接表其餘；套用後必須真的帶那個關鍵字。
- 大變化仍用 `DataOrderSource`（3W-3 補用法統計）。

### 3.3 強度下限與重調

- `evolution.budget_power(skill) = total ÷ AP（被動為觸發）係數`；不改費用的變化，等於直接比預算總點數；蓄力、輕巧、每回合觸發 +1 這類改係數的變化，比換算回同一係數後的分數（否則輕巧 AP −1 永遠過不了）。
- `composer_tuning.tune(min_ratio=…)`：有下限時目標比例抬到下限、上限放到驗證器的 1.00；`evolution._tuned/retune/finish_draft(floor=…)` 先把旋鈕調到最弱、換算下限成比例，最後再檢查分數。大變化走同一條路（`floor` 也生效）。
- 每一步：下限＝前一步的分數；結構不變、只靠重調變強的模板（`STRICT_OPS`：效果＋、修正幅度＋）再多 0.01 點，確保「閃了真的變強」。轉型不設下限（3W-3 決定）。
- 重閃：被換掉那一筆的分數（進位到千分點）存在 `FlashRecord.floor_permille`，選項帶 `floor_permille`（`choose` 寫入紀錄），所以只靠狀態就能重算出同樣的技能（`derive_skill` 驗證存檔仍成立）。
- 額外旋鈕（`tuning_extras`）：修正規則的 `change` 幅度（傷害、治療，階梯 50～1000‰）；接續段第二段的傷害。
- 同一份草稿最多試 3 次不同的調整亂數（第 1 次與 3W-1 相同）。

### 3.4 角色階級（#72）

- `FlashTemplate.min_tier`（1～3）；`FlashRequest.tier`（`None` ＝ 沿用技能自己的階級）；出題只列 `min_tier ≤ 階級` 的模板，套用時也再檢查。
- 預算：`at_tier(skill, tier)` 把技能的 `tier` 換成傳進來的角色階級後再算（3W-9 才改成「技能不再有固定階級」）。`derive_skill`／`derive_chain` 多一個 `tier` 參數；存下來的選項技能是用出題時的階級算的。

## 4. 新增的複雜度類 noqa

無（`C901`、`PLR0911／0912／0915` 都沒有新增）。有 4 個 `PLR2004`（魔術數字：`MAX_EFFECTS = 4`、修正規則最多 2 條），行內已寫理由。

## 5. 待 PM 決定

1. **姿態的「修正」「費用」類沒有可用模板**：姿態的維持費是形態表（`forms.yaml`）的全域數值，技能上沒有欄位；姿態的效果（進入形態、一個狀態）也沒有可調的數字。要做「維持費 ±1／效果升降」需要引擎新增「每招維持費」欄位（動 `engine/forms.py`、`turns.py`）。目前姿態列在這兩類（資料照 PM 定案），出題時這兩類沒有合格選項：指定時在扣點前拒絕，混合時略過。
2. **#72 的「4～6 格地形變化」「7 格以上地形變化」模板沒做**：現有地形原語的草稿要另外設計（#58 稀有門檻）；階級表的其餘項目都做了（含雙屬性縮放）。建議補一段（或併 3W-3）。
3. **修正類的「加第二個關鍵字」「條件放寬」是近似實作**：schema 沒有條件「或」。第二個關鍵字＝多一條條件換成另一個關鍵字的同樣規則（兩條都成立時幅度相加，不是單純的「或」）；條件放寬＝血量門檻 +150‰，其他條件拿掉（預算器會把幅度調小）。要真正的「或」需要 `ConditionSpec` 支援。「作用範圍 +1（光環類）」＝射程 +1 或多一條 `area_delta: 1` 的規則。
4. **「預算分數」定義成 `total ÷ AP（觸發）係數`**（見 3.3）。輕巧不會因 AP 係數變小而過不了；PM 若要「單純比 `total`」，輕巧與每回合觸發 +1 要另外處理。
5. **強度下限讓部分組合沒有選項**：技能已經接近預算上限、又要新增固定成本的效果（例如多打一下之後再接橋接）時，該候選不出現。被動、反應模板較少，常在第 4 次前就沒有合格選項（測試只要求閃 3 次）；出題不足 4 個時 `options` 可能少於 4 個。是否要補更多被動／反應模板，或允許出題不足時補通用變化，請 PM 決定。
6. **觸發範圍 +1／+2 適用面很窄**：被動、反應大多是 `shape: self` 且沒有 `max_distance`，只有帶距離上限或非自身形狀的才有。
7. **第二元素、接續段的新傷害效果起始很小**（法術 1d4／武器倍率 300‰，再由預算器調）；接續段用 `on_hit`、形狀 `single`，骨架依序試原骨架、`strike`、`combo`、`area`。
8. **雙屬性縮放**不改預算（縮放不影響預算），所以「分數不低於」自動成立；效果是命中與傷害取兩屬性平均，稀有度由重調補到史詩以上。
9. **#72 的「技能預算用角色階級」**：本段只在出題與套用時用傳進來的階級重算（`at_tier`），存下來的技能 `tier` 就是當時的階級；3W-9 要統一改。
10. **規則包雜湊**沒有再變（`SkillDef` 這段沒加欄位）。`FlashRecord`、`FlashOption` 多了 `floor_permille`（預設 0，舊紀錄可讀）。
