# Phase 3-54e 報告｜石膚術、大地崩陷補上

規格：`docs/phases/Phase3計畫.md` 第 68 節；設計：`docs/design/06-技能.md` 6.33（#64、#65）。

## 做了什麼

| 規格 | 實作 |
|---|---|
| 1 隆起、下陷點數 | `content/skill_primitives.yaml`：`raise_terrain`、`lower_terrain` 的 `base_points` 2 → **7**。7 點下大地崩陷（3×3 純下陷、2 AP）落在預算內（見下「數字」），**不需要改 8**。 |
| 2 既有地形技能 | 全部技能逐一跑驗證器，超預算的只有 3 招（見下表）；石牆術、築起土牆、移山之力不受影響。 |
| 3 石膚術 | 新增 `skill_stoneskin_ward`（石膚術）：aura、單體友方（含自己）、石膚 2 回合＋護盾 1d6，1 AP、4 法力、冷卻 2，普通稀有，元素欄大地，縮放感知（效果推導的輔助主題）。 |
| 4 大地崩陷 | 新增 `skill_earth_collapse`（大地崩陷）：control、`square3` 射程 4、`lower_terrain` 1 層、純地形，史詩，2 AP、8 法力、冷卻 2，元素欄大地，縮放智力。 |
| 5 行為一致測試 | `tests/engine/test_earth_54e.py`（10 項，見驗收）。 |

### 數字（預算比例）

- 石膚術：石膚 3 點 × 單體友方 ＋ 護盾 1d6；比例約 78.8%（1d6）。1d8 為 90.9%，1d10 > 100%，所以採規格建議的 1d6 起並取最低可行骰（留在 70～100%）。
- 大地崩陷：7 點 × 形狀倍率 2.0 ＝ 14 點；1 AP 的可用預算只有約 7.8，**3×3 只能用 2 AP**（AP 係數 1）；2 AP、8 法力、冷卻 2 時比例約 83%。
- 原語 2 → 7 的真實影響比規格預想更大：形狀倍率（3×3＝2.0、十字＝1.8）乘在 7 上。3-54d 報告寫「下陷 base 4 點」與資料不符（資料原本是 2）。

### 既有技能下修（逐招）

| 技能 | 修改前 | 修改後 | 比例 |
|---|---|---|---|
| 築高台（`skill_raise_perch`） | 1 AP；隆起＋緩速 1 回合；8 耐力、冷卻 2 | **2 AP**、**拿掉緩速**，費用不變；形狀（十字 4）、名稱不變 | 超預算 234% → 合格 |
| 陷地術（`skill_sinkhole`） | 1 AP；下陷＋緩速 1 回合；4 法力、冷卻 2 | **2 AP**、**拿掉緩速**，費用不變；形狀、名稱不變 | 234% → 合格 |
| 立起高台圖騰（`skill_summon_plateau_totem`，用到隆起點數的高台特性） | 持續 4 輪；8 法力、冷卻 4 | 持續 **1 輪**；**6 法力、冷卻 2** | 258% → 合格（持續 1 輪時冷卻 4 會 < 70%，所以冷卻跟著降） |

單格以上 1 AP 要過預算已不可能（十字形 12.6 點 > 1 AP 上限），所以 AP 提高是必要的下修；見待 PM 決定 1、2。

### 其他連動

- `tests/content/test_coverage.py`：`stoneskin` 移出原語允許清單（已有技能使用）；新技能加進「由池給出」清單。
- `tests/skillgen/test_budget.py`：結構原語點數 2 → 7。
- `tests/content/test_skill_scaling.py`：內建技能數 284 → 286。
- 組合器既有種子改變（接受）：抽到隆起、下陷的機率與結果不同；`skill_icons.json` 已重產（`glossary.json`、`unitDolls.json` 無變動）。
- `LOG_FORMAT` 未遞增（沒有新事件、沒有結算規則改動）。

## 驗收（逐條）

| 條件 | 證據 |
|---|---|
| 隆起、下陷 7 點 | `test_raise_and_lower_terrain_cost_seven_points`；`test_structural_primitive_points`（test_budget.py） |
| 既有地形技能回到預算內、形狀與名稱不變 | `test_the_reworked_terrain_skills_are_back_inside_the_budget` |
| 石膚術 70～100%、石膚＋護盾同一目標、物理 −30%、移動 −1、2 回合（實際跑引擎） | `test_stoneskin_ward_is_a_valid_common_earth_skill_in_the_window`、`test_stoneskin_ward_on_an_ally_gives_skin_and_shield_to_the_same_target`、`test_stoneskin_ward_can_target_the_caster_too` |
| 大地崩陷 ≥ 70%、史詩、3×3 純下陷、不傷人 | `test_earth_collapse_is_an_epic_pure_terrain_earth_skill_in_the_window`、`test_earth_collapse_digs_a_pit_and_the_unit_sinks_with_the_ground` |
| 單位墜落 | **部分**：單次只降 1 層，落差 1 < 墜落門檻 2，單位只會跟著地面下沉、不墜落（`test_the_pit_makes_a_two_level_edge_...` 確認不墜落）；見待 PM 決定 3 |
| 工坊「元素大地＋只有下陷」能過預算 | `test_a_workshop_earth_skill_with_only_lowering_can_pass_the_budget`（單格 1 AP、3×3 2 AP 都過） |
| 重播（含大地崩陷） | `test_a_battle_with_earth_collapse_replays_identically`（腳本政策先施放大地崩陷，其後效用 AI；重播狀態相同） |
| ruff、format、mypy（729 檔）、lint-imports（7 kept） | 全過 |
| vitest | 997 項全過 |
| pytest（content、skillgen、engine、narrative、roguelite、api、llm） | 7736 項通過、1 項既有 skip（-n 8） |
| `tests/cli`（`-m "slow or not slow" --timeout=3000`，`UPDATE_CLI_SNAPSHOTS=1`） | 148 項全過；快照重錄（`cli_output_hashes.json`、`llm_propose_mock.txt`），`test_budget_cli.py` 技能數 284 → 286 |

## 複雜度 noqa

沒有新增 C901／PLR 類 noqa（測試檔內只有 `PLC0415` 函式內匯入，沿用 3-54d 慣例）。

## 待 PM 決定

1. **規格前提與資料不符**：隆起、下陷原本是 2 點（不是 3-54d 報告寫的 4）。形狀倍率 3×3＝2.0、十字＝1.8 乘在 7 點上，1 AP 的可用預算上限只有約 7.8～10，任何範圍型（十字、3×3）地形技能都必須 2 AP。若要保留 1 AP，需把點數降到 3～4 或放寬單體預算。
2. 築高台、陷地術因此**改 2 AP 並拿掉緩速**（規格範例只提拿掉緩速、調整費用；AP 屬於費用）。若要保持 1 AP，只能縮形狀（規格禁止）。
3. **「單位墜落」做不到**：隆起、下陷 `amount` 上限為 1，墜落門檻是落差 2，單一次下陷不會讓單位墜落（現況與 06 6.33 的「可以挖坑讓單位墜落」文字有落差）。要成立需下列任一：墜落門檻降為 1、允許 `amount: 2`、或「從高處被推進坑」才算。目前未改。
4. 立起高台圖騰持續 4 → 1 輪、冷卻 4 → 2（它靠隆起點數計高台價值，同一個原因超預算）；玩法上高台只撐一輪，是否可接受請 PM 判斷。另一種做法是調低 `summon_trait_platform_permille`（`skill_budget.yaml`）。
5. 效用 AI 對純地形技能沒有評分，單位 AI 不會主動施放大地崩陷（重播測試用腳本政策）；若要讓敵人／隊友 AI 使用需另開 AI 評分規格。
6. 石膚術護盾實際數值＝骰值＋感知縮放（測試觀察到 1d6 擲 4 得 10 點），預算以骰平均估算，與其他護盾技一致。
7. 兩招都是手寫內建、由池給出；大地崩陷史詩，隨機組合器是否抽到取決於稀有度池，未特別調整。
