# BAL-12e 報告：升階持續上限 6、改加強度

依 `docs/phases/PhaseBAL計畫.md` 第 7 節「BAL-12e」（玩法決定 #76；06 6.34.9、6.3）。

## 1. 做了什麼

**引擎（狀態與表面的強度）**
- 沿用既有的 `apply_status.magnitude_permille`／`StatusInstance.magnitude_permille`：施加時不再只限姿態，**數值型狀態**（`StatusDef.scales_with_magnitude`：有每回合傷害／治療、倍率欄位、屬性或攻擊加值，且非控制、非姿態）也存下強度。
  - 每回合傷害與治療：`DamageEffect`／`HealEffect` 的 `multiplier_permille` 帶強度（只在最後捨去一次）。
  - 倍率欄位：增益（含姿態）放大有利的一邊（姿態行為不變），減益放大不利的一邊（虛弱 750 ×1.5 → 625、中毒受治療 500 ×1.5 → 250）。
  - 屬性與攻擊加值：非姿態狀態乘強度、無條件捨去（激昂 +2 ×1.5 → +3）；姿態照舊不放大加值。
  - 修正舊漏洞：回合結束倒數時重建的狀態實例原本會丟掉 `magnitude_permille`，現在保留。
- **表面**：`create_surface` 新增原語參數 `magnitude_permille`；`CreateSurfaceEffect` 與 `Tile.surface_magnitude_permille`（預設 1000）記下強度。回合開始的傷害、治療，進入或回合開始時施加的狀態（火焰 → 燃燒）都帶強度。吹送、擴散照原表面帶著；互動換成別種表面、或清除時回到 1000。`Ruleset.surface_scales_with_magnitude` 判斷表面有沒有數值。
- `LOG_FORMAT` `/90` → `/91`（戰鬥狀態多了欄位、規則包的原語多了參數）；`runner.py` 文件字串與 `docs/phases/戰鬥紀錄格式變更.md` 都補了這一版，測試裡的字面值一起改。存檔版本不變（技能欄位原本就有，舊存檔照常可讀）。

**內容與驗證**
- `SkillDef`：`magnitude_permille` 可以填在 `apply_status`、`create_surface`、`enter_form`（形態幅度仍只限姿態技能）。驗證器新規則 `magnitude.unscalable`：沒有數值的狀態（標記、隱蔽、控制類）或表面（冰、水、油、煙霧、黑暗）不能填。
- 預算：狀態與表面的點數 × 強度（同完整姿態）。
- 卡片：狀態寫「強度 N%（每回合傷害 ×N%）：數值句」（數值句用與結算同一個算法放大）；表面寫「強度 N%（表面每回合的傷害、治療與施加的狀態 ×N%）」。工坊說明（`workshop_text.yaml`）改寫 apply_status 那筆、新增 create_surface 那筆（實作者初稿）。

**升階重配（`skill_tier.py`）**
- `retier_growth.stretch` 的持續上限 10 → **6**；原本就超過 6 的不縮短、不再加回合。
- 數值型狀態與表面的持續旋鈕換成複合旋鈕 `(持續, 強度)`：先把回合加到 6，到上限後才加強度（每格 25‰，上限 2000‰；`skill_budget.yaml` 的 `magnitude_step`／`magnitude_max`）。同一個旋鈕，所以順序固定。
- 表面：只有形狀已經放大到這個角色階級能用的最大時，才加強度（先加格數）。
- 沒有數值的表面放大格數後仍到不了預算窗時（冰：持續卡在 6），新增 `_weak_growth`：照樣換成較大的形狀、取最接近目標比例的（只容許「過弱」），排在原本形狀的候選與落石之後、`_best_effort` 之前。
- 控制類狀態不放大回合、也不加強度（照舊）。閃現的「延長」沒有動（不受 6 回合上限）。

**完整技能（`complete.py`）**：效果參數那一組多了數值型狀態與表面的強度旋鈕（`status_magnitude_steps`，1000～1300，乘在原本的強度上），比持續 +1 回合細。

## 2. 驗收量測

`uv run python scripts/bal12b_measure.py duration`（13 個點數固定的配方 × 種子 1～4，逐階升階）：

| 項目 | BAL-12b（上限 10） | BAL-12e |
|---|---|---|
| 3 階淬毒 實用比例 | 0.48 | **0.75～0.80**（持續 6、強度 1625‰） |
| 3 階毒刺迎擊 實用比例 | 0.49 | **0.77～0.83**（持續 6、強度 1625‰） |
| 毒沼 3 階 | 0.52（方陣、持續 9） | 0.75～0.84（方陣、持續 6、強度 1475～1575‰） |
| 持續 > 6 的列 | 46／152 | 0／152 |
| 52 個持續型白板完整技能到 +120‰ | 4／52 | **28／52**（+123～124‰） |

- 強度落在 1075～1625‰（設計寫約 1170～1670‰；2 階的點燃、毒牙只有 1075‰，因為它們 1 階持續 5，2 階先補到 6 回合）。
- 到不了 +120‰ 的 24 個全部是沒有數值的狀態或表面：凝冰（冰）、烙印／追蹤印記／追蹤印痕／先機標記（標記）、隱身脫離（隱蔽）——設計 #76「到 6 回合後就不再加，接受」。
- 同一原因，這幾個在高階 **低於預算窗 0.70**：凝冰 2 階 0.65～0.69、3 階 0.51～0.54（表面仍放大到方陣）；隱身脫離 3 階 0.59；烙印 3 階 0.57～0.61（4 個種子中 3 個）。上限 10 時這些都在窗內（0.75～0.88）。見「待 PM 決定」1。

## 3. 快照變動

- 行為快照 `tests/skillgen/fixtures/refactor_3wr2.json` 重產：
  - 完整技能 24／301：skill_ashen_oath、cinder_mine、crippling_crit、ember_brand、fire_bolt、fleet_foot、fracture_mark、grief_rage、guard_breaker_fist、guard_swap、holy_ground、poison_mist、rending_strike、renewal、sanctuary、spellblade_surge、stand_firm、stoneskin_ward、tailwind、thorn_wall、vault_leap、venom_cloud、venom_pit、wild_roar（多了狀態或表面的強度旋鈕，例：火焰箭 +166‰ → +125‰，燃燒強度 1168‰）。完整技能超過 +150‰ 的由 23 招降到 19 招。
  - 升階重配 4／301：skill_gear_smoke_bomb、holy_ground、smoke_arrow、smoke_bomb（煙霧持續上限 6；聖地加強度）。
  - 閃現 0／129。
- CLI 輸出快照：沒有變。client fixture（glossary 等）：沒有變（`tests/api` 的檢查通過）。

## 4. 測試

- 新增 `tests/engine/test_strength_bal12e.py`（中毒每回合傷害與治療削減、倒數保留強度、虛弱與激昂、標記與緩速不吃強度、強度 1000 不變、毒表面、火焰表面傳給燃燒、水覆蓋回到 1000、再生）。
- 改了斷言的（設計改變，不是換種子）：
  - `test_retier_growth_3w9b.py`：`test_fixed_blanks_scale_the_effect_itself` 與 `test_retier_keeps_the_ratio`：沒有數值的狀態／表面持續已到 6 時，只容許「過弱」、不檢查窗與比例差（其餘照舊）。
  - `test_complete_3w5b.py::test_over_150_only_when_no_capped_path_reaches_120`、`test_flash_bal12c.py::test_complete_small_overshoot_is_still_accepted`：例子由火焰箭改成連珠雷（火焰箭現在用燃燒強度補到 +125‰，不再超過 +150‰）。
  - `test_workshop_text_48f.py`：說明條目 169 → 170。
  - `LOG_FORMAT` 字面值 `/90` → `/91`（cli 6、engine 5、roguelite 夾具 1）。

## 5. 檢查

ruff check、ruff format --check、mypy、lint-imports 通過；相關 pytest：skillgen＋content 4822 通過（14 個 slow 跳過，另跑行為快照 732 通過）、engine＋narrative＋api＋roguelite 4723 通過、cli＋llm＋sim＋shared＋架構 698 通過、CLI 輸出快照（slow）通過；重播 `trpg battle --map swamp --seed 7` → `battle replay` 一致（76 個動作、250 個事件）。

## 6. 待 PM 決定

1. **沒有數值的白板高階低於預算窗**：凝冰 2～3 階、隱身脫離 3 階、烙印 3 階（0.51～0.69）。設計寫「接受」，所以測試改成只容許「過弱」；但驗證器仍會對這些標「過弱」（`retier_report` 不在窗內）。要不要給它們別的補償（例如減費用、接受現狀並在驗證器豁免）？
2. **表面的持續上限也用 6**：規格第 1 點只寫「狀態」；照 BAL-12b 的做法 A（毒沼 6、×1.50）與設計「持續回合最多放大到 6」，表面也一起套 6。
3. **原本就超過 6 回合的**：不縮短、不加回合，但 **仍可加強度**（照「到 6 回合後剩下的預算改加強度」）。若要連強度也不加，改 `_stretch_knobs` 一行。
4. **重複施加時的強度**：照舊「剩餘回合較長的那個留下」，強度跟著留下的那個（沒有取兩者較大的強度）。
5. **姿態的屬性加值不放大**（沿用 3W-5b），非姿態狀態的屬性與攻擊加值放大；增益狀態的代價（例如石膚的移動 −1）不放大。
6. **完整技能也會加強度**（`status_magnitude_steps`，和持續回合在同一組）：讓完整技能的 +120‰ 加得上去，但 24 招內建技能的完整版本改變（第 3 節）。
7. 強度級距 25‰、上限 2000‰（同原語參數上限）是實作者初值；表面的「形狀放大到最大」以角色階級能用的最大形狀判斷，形狀放不大（被動、反應、陷阱）視為已到上限。
8. 工坊兩筆說明（apply_status／create_surface 的強度）是實作者初稿，待玩法 PM 改寫。
