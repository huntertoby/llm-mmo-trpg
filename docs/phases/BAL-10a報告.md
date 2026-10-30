# BAL-10a 報告：第 1、2 次閃現小變化覆蓋掃描（只量不調）

## 做了什麼
- 新增 `scripts/flash_minor_coverage.py`（借用 BAL-2 `flash_category_audit.py` 的不合法原因判定）與測試 `tests/sim/test_flash_minor_coverage.py`（2 個技能、1 種子、確定性、CSV 表頭）。未改任何模板、規則、內容。
- 做法：對 301 個內建技能與 54 個白板配方（3 階 × active／passive／reaction × 6 個配方種子），在「技能階級～角色階級 3」（照角色階級重配）各看 2 個種子：第 1 次閃現（不指定類別）→ 依序選每個選項 → 各分支的第 2 次閃現。共 972 列（技能, 階級）；第 2 次取所有分支與種子的最小值。
- 產物：`docs/phases/BAL-10/minor_coverage.md`（彙總、不足清單、原因、結構缺口率）、`docs/phases/BAL-10/minor_coverage.csv`。重跑：`uv run python scripts/flash_minor_coverage.py --jobs 8 --csv ...`（約 10 分鐘）。
- 判定「不足」＝該列選項數 < 2；「階級不足（模板 min_tier）」不算缺口（本來就不出）。

## 結果摘要
- 972 列中有 292 列不足，涉及 124 招不同技能（占 355 招的 35%）。
- 依「技能在自己的最低階級」計（實際玩家第一次會遇到的情況）：

| 種類 | 第 1 次 <2 | 第 2 次 <2（任一分支） | 總招數 |
|---|---|---|---|
| 內建 active | 19 | 49 | 247 |
| 內建 modifier | 13 | 18 | 18 |
| 內建 stance | 10 | 10 | 12 |
| 內建 passive | 4 | 11 | 16 |
| 內建 reaction | 1 | 2 | 8 |
| 白板 passive | 3 | 6 | 15 |
| 白板 reaction | 1 | 3 | 18（配方數） |
| 白板 active | 0 | 2 | 33 |
| 白板 modifier | 0 | 3 | 3 |
| 白板 stance | 1 | 2 | 3 |

  合計第 1 次 < 2：內建 47 招＋白板 5 招＝52；第 2 次 < 2：內建 90 招＋白板 16 招＝106（內建 18 招 modifier 全部、passive 11/16 都在內）。
- 階級走勢：active 的第 1 次不足率 1 階 7%、2 階 9%、3 階 17%（階級越高越多，因為升階重配後預算窗更窄，「預算窗／強度下限」失敗變多）；passive 第 2 次不足率 1 階 73%。
- 彙總表（種類 × 階級）見 `minor_coverage.md` 第 1 節。

## 缺口成因（依影響招數排序）
1. **modifier（修正型被動）幾乎沒有小變化**：18 招中 13 招第 1 次 0～1 個。`mod_potency` 要有正的傷害／治療幅度、`mod_keyword`／`mod_relax` 要有條件且沒有 `any_of`、`mod_range` 規則已滿 2 條或重調失敗；許多 modifier 規則只是無條件加成或綁狀態。
2. **姿態**：10／12 招第 1 次 < 2。`stance_cost_*` 只適用單一效果、有階梯的元素姿態（24 次「非單一效果／變身姿態」），變身姿態（form_*）只出 `stance_potency` 1 個。
3. **被動／反應（含白板）第 2 次**：能用的只剩 `trigger_*`、`keyword_*`、`extend_duration`、`dual_scaling`，其中 `trigger_range`／`trigger_range_wide` 對形狀 self 的被動永遠不合法（45＋29 次），`trigger_potency`、`trigger_cap`、`keyword_*`、`extend_duration` 常因預算窗失敗；`dual_scaling` 多數「無候選變體」（117＋38）。白板 passive 1 階第 1 次 50% 不足。
4. **無傷害的主動技（輔助、控場、位移、召喚、常駐）**：不足列 active 的 41% 是「無傷害」，26% 第 1 次不足。`multi_hit`、`kill_refund`、`reshape_*`、`element_second`、`followup_hit` 都要傷害效果；`area_plus`／`range_plus` 對 self／無可增大參數的形狀不合法；`summon_toughen` 只限單隻召喚（139 次不合法）；`extend_duration` 要有狀態／表面／區域。形狀 self 的 active 66% 第 2 次不足；ground_tile 42%；召喚 46%；常駐（`is_activatable`）12/12 全部不足。
5. **複合技（含 followup）**：`area_plus`／`range_plus`／`reshape_*`（複合技不改形狀）、`multi_hit`、`followup_hit` 都擋掉，只剩費用／元素類。已測複合技（最低階級）：影旋斬 `skill_shadow_whirl` 第 1 次 1 個、第 2 次 0；`skill_gravity_burst`、`skill_leap_slam` 同為 1／0；`skill_armor_break_combo` 0／0；`skill_death_spiral`、`skill_retreating_slash` 第 2 次 1；`skill_charged_cleave` 2、`skill_parry_riposte` 3 尚可。
6. **AP1 的主動技**：`cost_light`（AP 已是 1，共 107 次）不合法；AP1 且無傷害的 active 第 2 次不足 30%。
7. **預算窗／強度下限（重調失敗）**：`keyword_exploit`／`keyword_imbue`（共約 300 次）、`cost_charge`、`extend_duration`、`trigger_*` 在許多技能上結構合法但重調不過；這類不是缺模板，是數值窗太窄（可調的是旋鈕或下限，屬原型數值）。

## 補模板建議
標記：【數值】＝原型數值，玩法 PM 可定；【規則】＝要回使用者（改 6.34.3 出題規則或設計文件）；「放寬」＝改既有模板條件；「新增」＝新模板。

1. **複合技的接續段強化（新增，【數值】）**：新模板 `followup_potency`（接續段威力＋）、`followup_range`／`followup_shape`（接續段射程或形狀 +1）與 `followup_element`（接續段加第二元素）。目前複合技因形狀鎖定、`multi_hit`／`followup_hit` 禁用而只剩費用／元素類（影旋斬、重力爆發、飛躍猛擊、破甲連擊）；這四招＋死亡螺旋等 7 招最低階級第 2 次 ≤ 1。**【數值】**（屬「複合技轉型」延伸，不動規則）。
2. **modifier 專用模板（新增，【數值】）**：`mod_potency` 放寬到「無條件加成」（目前要正的傷害／治療幅度）；新增 `mod_cooldown`（規則附帶的冷卻／觸發窗放寬）、`mod_duration`（持續回合 +1）、`mod_stack`（疊層上限 +1）、`mod_cost`（對應技能費用 −1）。修正型被動 13/18 第 1 次 0 個，這是最大的整體缺口，需要 3～4 個新模板才補得起來。
3. **姿態／變身（放寬＋新增，【數值】）**：`stance_cost_*` 放寬到變身姿態與多效果姿態（對形態幅度、維持費同樣 ±1 級）；新增姿態的「進入代價（AP／冷卻）−1」（`stance_enter_light`）與「切換免費回合」類。變身姿態目前只有 `stance_potency` 一個。若要新增「姿態期間附帶效果」（例如姿態中第一擊加成），屬新機制，回【規則】。
4. **被動／反應的 self 形狀替代（放寬＋新增，【數值】）**：`trigger_range*` 對 self 被動永遠不合法，建議放寬為「觸發距離從無上限改為可設為 3 格」或新增 `trigger_cooldown`（觸發冷卻 −1）、`trigger_chance`（觸發機率 +）、`trigger_on_kill`（附加條件）。同時放寬 `dual_scaling` 的候選（被動多數「無候選變體」）。
5. **無傷害工具技的費用／範圍類（放寬，【數值】）**：`cost_light` 在 AP1 時改為「冷卻 −1 或消耗 −1」（現在 AP 已 1 就不合法）；`cost_charge` 對無傷害技改為「持續回合＋」；`extend_duration` 放寬到「自身狀態、召喚物存活回合、場地存在回合」；`area_plus`／`range_plus` 對 self 形狀改為「效果改作用於周圍 1 格」類的目標範圍（需新增 `radius_around_self`，**【規則】**，因為改了形狀分類）；`summon_toughen` 放寬到多隻召喚與場地型召喚（`summon_count_plus`、`summon_duration`）；`kill_refund` 對無傷害技改為其他回饋（回 AP／靈感）。
6. **陷阱、ground_tile、常駐技專用（新增，【數值】）**：陷阱 `trap_trigger_plus`（觸發次數）、`trap_duration`；ground_tile `tile_duration`、`tile_radius`；常駐（is_activatable）技 `upkeep_light`。常駐 12/12 全不足、ground_tile 第 2 次 42% 不足。
7. **規則面（回使用者）**：若某類技能在最低階級仍然補不到 2 個合法小變化（例如純被動資源類 modifier），選項是 (a) 第 1、2 次允許出「通用保底」（只提高預算的 `generic` 變化，不改結構）；(b) 容許少於 2 個選項（現行 6.34.3 的少出行為）並在 UI 標示。這兩者都要改出題規則或設計文件，**【規則】**，由使用者決定。

## 待 PM 決定
- 玩法 PM：以上【數值】條中哪些要做、做幾個模板（建議先做 1、2、3，約涵蓋 modifier、姿態、複合技共 50 招）。
- 使用者：第 7 條是否採用保底（回【規則】）。
- 預算窗失敗（約 300 次 `keyword_*`）的處理：是旋鈕太少還是強度下限太高，需另做一次查修。

## 驗證
- ruff check／format、mypy：新增腳本與測試通過；新增測試 1 個通過。
