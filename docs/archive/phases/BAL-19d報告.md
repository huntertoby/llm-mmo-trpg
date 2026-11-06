# BAL-19d 報告：遠程武器技（玩法決定 #110，缺口 4）

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19d；設計 `docs/design/06-技能.md` 6.27.4（技能供給補齊）、6.10（武器技看武器屬性）。新增 `content/skills/skill_rng_*.yaml` 14 檔；沒有改 `src/`、既有技能與其他資料檔（測試計數與 fixture 的配合修改見「快照與 fixture」）。

## 做法

- 目標格（BAL-18 缺口 4）：武器技 × 敏捷的倒地、高處、帶電、中毒各補到 ≥ 3；風、聖元素武器技各 3 招。
- 遠程 12 招（`weapon_req: ranged`、`scaling_attr: dex`）；風、聖各留 1 招近戰（力量），照 6.27.4「近戰、遠程都有」。
- 關鍵字都靠專屬機制推導：倒地＝`knock_prone`；高處＝條件 `height_advantage`（遠程傷害的「高處」只是通用歸類，交叉表不算）；帶電＝雷傷；中毒＝`apply_status: poison`／毒池（毒元素傷害本身不算中毒）。
- 骨架照工坊結構檢查選（displace 的傷害占比 ≤ 50%，strike 的傷害 ≥ 60%）。稀有度照武器技現有曲線（普通 10／稀有 95／史詩 5）：普通 1、稀有 12、史詩 1。

## 新增技能（14 招）

| ID | 名稱 | 武器 | 關鍵字（專屬） | 元素 | 稀有度 | 階級 | AP | 骨架 | 預算比例 |
|---|---|---|---|---|---|---|---|---|---|
| skill_rng_thunder_arrow | 雷鳴箭 | 遠程 | charged | 雷 | 普通 | 1 | 1 | strike | 78.8% |
| skill_rng_static_bolt | 導雷弩矢 | 遠程 | charged、wet（利用） | 雷 | 稀有 | 1 | 2 | strike | 82.2% |
| skill_rng_storm_volley | 雷霆箭雨 | 遠程 | charged | 雷 | 史詩 | 2 | 2 | area（3×3） | 75.8% |
| skill_rng_venom_arrow | 淬毒箭 | 遠程 | poisoned | 毒 | 稀有 | 1 | 1 | strike | 96.7% |
| skill_rng_toxic_volley | 毒霧箭 | 遠程 | poisoned | 毒（＋毒池） | 稀有 | 1 | 2 | area（十字） | 71.2% |
| skill_rng_hamstring_shot | 斷腱射擊 | 遠程 | prone | — | 稀有 | 1 | 1 | displace | 74.3% |
| skill_rng_downdraft_shot | 下擊風箭 | 遠程 | prone | 風 | 稀有 | 1 | 1 | strike | 96.9% |
| skill_rng_gale_arrow | 疾風箭 | 遠程 | collision | 風 | 稀有 | 1 | 1 | displace | 93.5% |
| skill_rng_plunging_volley | 俯射箭雨 | 遠程 | high_ground | — | 稀有 | 1 | 2 | area（十字） | 82.4% |
| skill_rng_hawkeye_mark | 鷹眼標記 | 遠程 | high_ground、marked | — | 稀有 | 1 | 2 | strike | 79.5% |
| skill_rng_consecrated_arrow | 聖別之箭 | 遠程 | marked（利用） | 聖 | 稀有 | 1 | 2 | strike | 78.4% |
| skill_rng_radiant_volley | 聖光箭雨 | 遠程 | — | 聖 | 稀有 | 1 | 2 | area（十字） | 72.4% |
| skill_rng_judgment_cleave | 審判斬 | 近戰 | prone | 聖 | 稀有 | 1 | 2 | strike | 81.6% |
| skill_rng_gale_cleave | 裂風斬 | 近戰 | collision | 風 | 稀有 | 1 | 2 | strike | 78.4% |

- 稀有度：普通 1、稀有 12、史詩 1（武器技全體 普通 10→11、稀有 95→107、史詩 5→6）；階級：1 階 13、2 階 1。
- 每招 `uv run trpg skills budget <id>` 合格且「驗證：通過」（71.2%～96.9%）；`uv run trpg content check`：349 個技能（合併 BAL-19c 後 358）通過預算與結構驗證。

## 交叉表前後（`uv run python scripts/skill_balance_audit.py --sections 2`）

格子：合計（手寫＋模板配方），`*`＝少於 3。前＝本段開始時（main 807ea049），後＝本段。

武器技 × 關鍵字：

| 關鍵字 | 敏捷（前） | 敏捷（後） | 力量（前） | 力量（後） |
|---|---|---|---|---|
| prone | 2* (0+2) | 4 (2+2) | 10 (8+2) | 11 (9+2) |
| high_ground | 2* (2+0) | 4 (4+0) | 4 | 不變 |
| charged | 3 (0+3) | 6 (3+3) | 5 | 不變 |
| poisoned | 2* (0+2) | 4 (2+2) | 4 | 不變 |
| wet | 3 (1+2) | 4 (2+2) | 3 | 不變 |
| collision | 5 (3+2) | 6 (4+2) | 9 (7+2) | 10 (8+2) |
| marked | 4 (3+1) | 6 (5+1) | 2* (1+1) | 不變 |
| generic | 14 (11+3) | 15 (12+3) | 47 | 不變 |
| ignite、frozen、concealed | 6、3、5 | 不變 | | |

武器技 × 元素：

| 元素 | 敏捷（前） | 敏捷（後） | 力量（前） | 力量（後） | 合計（後） |
|---|---|---|---|---|---|
| wind | **0** | 2* (2+0) | **0** | 1* (1+0) | 3 |
| holy | **0** | 2* (2+0) | **0** | 1* (1+0) | 3 |
| lightning | 3 (0+3) | 6 (3+3) | 5 | 不變 | |
| poison | 2* (0+2) | 4 (2+2) | 4 | 不變 | |

- 敏捷列的倒地、高處、帶電、中毒都 ≥ 3；第 2h 節「少於 3」清單少了 prone／high_ground／poisoned × 敏捷、poison × 敏捷。
- 風、聖元素武器技各 3 招（遠程 2＋近戰 1），但分到單一屬性格仍是 2／1，所以 2h 仍列 wind、holy × 力量／敏捷（見待決 1）。
- 法術技各表不變。

## 快照與 fixture

- `tests/skillgen/fixtures/refactor_3wr2.json`：重產。complete、retier 各新增 14 條，既有 335 條雜湊全部不變；flash（ID 排序後等距抽約 40 招）因技能數變動換了抽樣（54 條移除、60 條新增），共同條目雜湊不變。
- `client/src/render/fixtures/skill_icons.json`：重產（`uv run python -m tests.narrative.icon_fixture`），只新增 14 招。
- `tests/cli/snapshots/cli_output_hashes.json`：`skills_list`、`skills_show_all/00`～`15` 雜湊改變（技能清單多 14 招，含 BAL-19c 合併後的 9 招），其他不變。合併 main（BAL-19c）後重產，沒有手改。
- 測試修改（不是 `src/`）：`tests/content/test_coverage.py` 的 `_BAL19_PREFIXES` 加 `"skill_rng_"`；`tests/content/test_skill_scaling.py` 內建技能數 335 → 349（合併 BAL-19c 後 358）。

## 檢查

- 合併 main（BAL-19c，`b6b0c868`）後：`_BAL19_PREFIXES` 合併成 `("skill_wis_", "skill_wil_", "skill_sum_", "skill_rng_")`、內建技能數 344＋14＝358，兩個 fixture 重產（complete／retier 既有 344 條雜湊不變、只新增 14 條）；`uv run pytest -n 8 --timeout=1800 tests/content tests/skillgen tests/narrative tests/api/test_client_fixtures.py`：5376 passed、14 skipped。交叉表在合併後重跑，武器技各表與上表相同（19c 的技能歸「召喚」欄）。
- 合併前：`uv run pytest -n 8 --timeout=1800 tests/content tests/skillgen tests/narrative`：2 failed（上面兩個 fixture）、5320 passed、14 skipped；重產後重跑那兩個檔＋`test_coverage`、`test_skill_scaling`、`tests/api/test_client_fixtures.py`：393 passed。
- CLI 輸出快照：`UPDATE_CLI_SNAPSHOTS=1 ... -m "slow or not slow"`（不加 -n）：25 passed（645 秒）。
- `ruff check`、`ruff format --check`（排除暫存）、`mypy`（941 檔沒有問題，合併後）、`lint-imports`（7 契約）通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay`：88 個動作、313 個事件，一致。

## 待 PM 決定

1. **風、聖「各 3 招」照合計算**：遠程 2＋近戰 1，所以 2h 的單一屬性格（wind／holy × 力量 1*、× 敏捷 2*）仍少於 3。若要每個屬性格都 ≥ 3，需再補力量 2＋敏捷 1（各元素）。
2. **數值是初值，未經模擬**；沒有跑 sim matrix。毒霧箭（71.2%）、聖光箭雨（72.4%）、斷腱射擊（74.3%）偏靠下限；淬毒箭 96.7%、下擊風箭 96.9% 靠上限。
3. **帶電原本已 3（全是模板 0+3）**：仍補了 3 招手寫（含 1 招史詩 2 階的雷霆箭雨），讓手寫池也有遠程帶電；敏捷帶電變成 6。
4. 審判斬、裂風斬是力量近戰（風、聖近戰各 1），用 `skill_rng_` 前綴只是本段命名；ID 名稱不代表遠程。
5. 這批技能沒有放進 build、單位或開局包，只靠關鍵字池進候選；`test_coverage` 用 ID 前綴豁免（同 BAL-19a）。
6. 沒有重跑第 5 節（偏離率），留給 BAL-19 最後的驗收。
