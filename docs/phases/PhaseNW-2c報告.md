# Phase NW-2c 報告：數值工坊內看 1 階比值（＋三件小修）

> 實作者：implementer agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhaseNW-2計畫.md`（NW-2c 列、5.7、T11、T12、D4、第 8 節 NW-2c、第 9 節；R1／R2 使用者「照建議」）、`docs/phases/PhaseNW-2b報告.md` 末節開發 PM 裁定（待決 5）、`docs/phases/PhaseDD-2報告.md` 開發 PM 裁定（待決 3）、`docs/phases/PhasePB-1n報告.md` 待決 2、3（開發 PM 交接 3.0000 第 4 點 (c)）。
> 分支 `worktree-agent-a1e70d238f2a185a7`（起點 `404c56bd`，含 `34e50d21`）；未 push。沒有改任何數值、沒有動 `content/` 的資料。

## 1. 做了什麼（交付與 commit）

| commit | 交付 |
|---|---|
| `63367382` | **C1** 比值核心搬進 `src/trpg/sim/skill_ratio.py`（情境建構、條件成立的做法、`condition_met`／`variant_holds` 檢查、`measure`、彙總 `skill_summary`／`odd_conditions`／`low_tag`、參考線 `reference_checks`）；`scripts/t1_skill_ratio.py` 改薄包裝（CLI＋印表）；`tests/sim/test_skill_ratio.py` |
| `d4c73061` | **DD-2 待決 3**：預覽回應的期望傷害夾在「最多」以內（`src/trpg/api/schemas.py::_damage`）；`tests/api/test_preview_expected_cap_dd2.py` |
| `58625162` | **PB-1n 待決 3**：部位血量加總上限的訊息改中文（`content/parts.py`）＋工坊對到欄位、拿掉「單位 <ID>：」前綴（`api/tuning/check.py`）；**PB-1n 待決 2** 的後端一半（`objects.py::_part_group`）；`test_parts_pb1n.py` 一條改斷言＋一條新測試 |
| `a047b156` | **C2** 比值工作與快取、基準匯入（`api/tuning/ratios.py`、`sim_jobs.py::start_ratio`、`service.py`、`routes.py`、`schemas.py`）；**NW-2b 待決 5**：分組預覽跑 `validate_skill`（`skills.py`）；`TuningFieldView.group_zh`；`summary_cells` 移進核心（腳本改用，輸出再驗一次逐字相同）；OpenAPI 與 `schema.d.ts` 重產；`tests/api/tuning/test_ratio_nw2c.py` |
| `54ec98c5` | **C3** 前端：技能表單比值區、模擬面板「比值」情境（規模估時、改前改後並排、匯入基準）、分組預覽加比值欄與結構違規、頭目部位欄位按部位分組；`client/src/tuning/ratio.test.ts` |
| `3d0703c5` | 實機發現的兩個小問題（比值規模跑完會閃「正在算規模」、`.tn-ratio` 類名撞到技能清單）＋`TuningRatioPlan.requested`；截圖 `docs/art/shots/nw2c/` |
| （本 commit） | 報告、上手筆記兩份 |

注意：`58625162` 的 `objects.py` 用到 `TuningFieldView.group_zh`，欄位在下一個 commit `a047b156` 才加（中間那個 commit 單獨 checkout 會在讀單位表單時出錯）；合併整段沒有影響。

新檔：`src/trpg/sim/skill_ratio.py`、`src/trpg/api/tuning/ratios.py`、`tests/sim/test_skill_ratio.py`、`tests/api/tuning/test_ratio_nw2c.py`、`tests/api/test_preview_expected_cap_dd2.py`、`client/src/tuning/{ratioModel.ts, RatioView.tsx, ratio.test.ts}`。

### 1.1 比值（NW-2c）

- **工作**：`POST /api/tuning/sims` 的 `scenario: "ratio"`（`skills`、`seeds`）。一個工作單位＝一組「武器 × 招」（核心 `ratio_task(root, RatioJob)`，程序池同其他模擬）。只量 1 階主動武器技、非敵人專用（同腳本）；其他招列在結果的 `skipped`。
- **規模（T11）**：`POST /skills/ratio-plan` 回組數（Σ 招 × 可用武器 × 情境數）、`work`＝組數 × 種子、預估秒數（÷ 上一次實測的每秒場數，預設 450）；上限 40,000 組×種子（422「一次最多 40,000 組×種子…」）。預設 50 種子；`seeds` 上限改成 250（見待決 3）。
- **快取與存放（T12）**：`<save_dir>/tuning/ratios/run-<序號>-<鍵>.json`，鍵＝樹雜湊＋招＋種子；改前同鍵命中就不跑。改後（草稿內容）也存，鍵用草稿資料夾的樹雜湊；草稿沒改內容時只跑一次（改前＝改後）。最多留 40 份。
- **基準匯入**：`POST /skills/ratio-baseline` 收 `t1_skill_ratio.py run` 的 JSON（格式不對 422），記下匯入時的內容樹雜湊；之後內容改了，表單標「內容已變，僅供參考」。畫面在模擬面板「比值」分頁的檔案選擇（不是彈出層）。
- **技能表單比值區**（`GET /skills/{id}/ratio`）：摘要表六格（直接、含持續、成立 直接、成立 含持續、雙匕首、綁定武器，同 BAL-21e 摘要表）、類別、參考線（D4）與達標／低於、來源（工坊量測／匯入的基準、種子數、內容已變）、「上次」＝最近一份不同內容的量測。註明「只當參考，不擋寫回；和預算比例是兩把尺」。
- **參考線（D4）**：無條件單體（直接）≥ 0.9；條件成立（直接，含各變奏）≥ 1.1；條件不成立（直接）≥ 0.6「建議，未定案」；1 AP 箭類（1 階遠程、AP 1、單體傷害）≥ 0.6「建議，未定案」（無條件的 1 AP 箭類用這條取代 0.9）。比的是範圍最高值（BAL-21e 待決 1 的判法）。召喚、非傷害、非單體不套。
- **分組預覽**：每列加「比值（直接，目前）」。
- 腳本**沒有** `--category spell`，所以照規格不新增（法器法術補量是另一段）。

### 1.2 小修

- **NW-2b 待決 5**：分組預覽對改後的每招跑 `validate_skill`，列 `violations`（不含 `budget.over`／`budget.weak`）；畫面在改動格下紅字「結構違規：…（規則）」、判定欄加「＋結構違規」。仍可放進草稿（整包驗證會擋寫回）。
- **DD-2 待決 3**：`_damage` 在命中時的期望 > 最多時把它夾成最多，已乘命中率的期望照同比例縮（＝最多 × 命中率）。**只改 API 的顯示**：引擎 `DamageRange` 與 AI（`gains._useful_damage` 本來就用目標 HP 夾）不動，所以 AI 固定種子不受影響（見待決 2）。
- **PB-1n 待決 3**：訊息改成「所有部位的血量加總不能超過 600‰（收到 601‰）」；工坊顯示時拿掉 `UnitTemplate` 加的「單位 sect_mist_lock_master：」前綴（`_UNIT_PREFIX`），因為訊息裡不再有欄位名，另以「部位的血量」→ `hp_permille` 對到三個部位欄位（`_MESSAGE_FIELDS`）。
- **PB-1n 待決 2**：後端每個部位欄位帶 `group_zh`（「部位 1「拂塵」」）；前端 `fieldBlocks` 把部位欄位集中成組、組內照原順序、放在第一個部位欄位的位置，各組有標題。`concrete_fields` 的順序沒動（避免影響 `phases[*]` 等其他 `[*]` 欄位與既有測試）。

## 2. 驗收逐條

### 2.1 規格第 8 節（NW-2c）

| # | 條件 | 證據 |
|---|---|---|
| T-C1 | 搬家前後腳本 JSON 與 stdout SHA-256 相同 | 第 3 節（兩組指令、四個檔，全部相同；`summary_cells` 移進核心後又跑一次，仍相同） |
| T-C2 | 同參數兩次相同 | `test_ratio_nw2c.py::test_ratio_job_before_after_cache_and_determinism`（第二次 `again.skills == result.skills`） |
| T-C2 | 改前快取命中 | 同上（第二次 `total == 6`、`before_cached`）；實機第二次 0.5～1.4 秒 |
| T-C2 | 上限 40,000 組×種子 | `test_plan_limits_and_unknown_skills`（100 招 × 250 種子 → `problem_zh` 與 `start_sim` 422） |
| T-C2 | 參考線判定（0.89 → 低於 0.9、1.12 → 達標） | `tests/sim/test_skill_ratio.py::test_unconditional_line_uses_the_best_weapon`、`test_conditional_lines_on_and_off`；另有變奏、1 AP 箭類、不套線三條 |
| — | 草稿沒改內容只跑一次、表單比值來源 | `test_without_a_draft_the_ratio_runs_once` |
| — | 基準匯入、內容已變、格式不對 | `test_baseline_import_and_staleness`；「上次」＝不同內容：`test_previous_is_the_last_measurement_of_other_content` |
| — | 端點 | `test_ratio_routes` |
| — | NW-2b 待決 5 | `test_group_preview_lists_structure_violations_and_ratio`（斷腱射擊 `skeleton.secondary_share`，沒有 `budget.*`） |
| — | DD-2 待決 3 | `tests/api/test_preview_expected_cap_dd2.py`（截圖那一下：最多 18、命中 85% → 期望 15.3、命中時 18.0；沒超過的不變） |
| — | PB-1n 待決 2、3 | `test_parts_pb1n.py::test_part_hp_total_over_600_is_refused_in_chinese`、`test_part_fields_carry_a_group_per_part`；`ratio.test.ts`「PB-1n 待決 2」兩項 |
| — | 前端 C3 | `client/src/tuning/ratio.test.ts` 11 項（比值區三種狀態、參考線文字、估時、結果表變動格與參考線改前改後、模擬面板「比值」分頁與進度單位「組」、分組預覽結構違規與比值欄、部位分組） |

### 2.2 規格第 9 節

| # | 條件 | 結果 |
|---|---|---|
| 1 | 第 8 節測試全過；改到的既有測試列舊→新 | 全過；改到的見第 4 節 |
| 2 | 每次 commit：ruff、format、mypy、lint-imports、相關測試；前端 typecheck、test、build 分開記 | 交件前結束碼見 2.3 |
| 3 | 實機走一遍（2b 的項目） | NW-2c 的實機見 2.4（2b 的寫回流程本段沒改，沒重走） |
| 4 | `trpg content check`；一場紀錄＋重播 | 2.3 |
| 5 | 實測數字（比值重算 1 招／一組） | 第 5 節 |

### 2.3 交件前結束碼

（見下表；完整 log 在暫存區，不進 repo）

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | 2517 個檔 |
| `uv run mypy` | 0 | 1521 個原始檔 |
| `uv run lint-imports` | 0 | 14 kept, 0 broken |
| `uv run trpg content check` | 0 | 662 個檔、404 個技能（輸出和改前相同） |
| `pytest -q tests/api/tuning tests/sim/test_skill_ratio.py tests/api/test_openapi_snapshot.py tests/api/test_client_fixtures.py tests/test_architecture.py tests/content/test_tuning_fields.py tests/content/test_tuning_fields_nw2a.py tests/content/test_boss_parts_content.py tests/api/test_preview_expected_cap_dd2.py tests/engine/test_dual_dagger_skills_dd1.py tests/content/test_loader.py -n 8` | 0 | 287 passed |
| `pytest -q tests/api/test_routes.py -n 4`（單獨） | 0 | 46 passed |
| `pytest -q tests/cli/test_output_snapshots.py -m slow -n 8` | 0 | 24 passed（快照沒動） |
| `trpg battle --map open_plain --seed 7 --log-json …`／`trpg battle replay …` | 0／0 | 91 個動作、383 個事件，重播一致 |
| `corepack pnpm -C client typecheck` | 0 | |
| `corepack pnpm -C client test` | 0 | 318 個檔、4107 項 |
| `corepack pnpm -C client build` | 0 | |

注意：第一次把 `tests/api/test_routes.py` 和 `tests/api/tuning` 放在同一個 `pytest -n 8` 裡跑時，`test_routes.py` 45 項在 setup 報「fixture 'client' not found」（`tests/api/conftest.py` 的 fixture 沒套到；同名的 `tests/api/tuning/test_routes.py` 也在同一批）。單獨跑 `tests/api/test_routes.py` 46 項全過；看起來是同名測試檔同批收集的問題，和本段的改動無關（PM 全量照常收集）。

### 2.4 實機（自己的 `trpg serve --port 8157`、`TRPG_TUNING=1`、`TRPG_SAVE_DIR=<暫存>`；無頭 Chrome `--headless=new --mute-audio`、網址 `?dev=1&mute=1`、CDP）

沒有寫回（worktree 分支本來就寫不回；本段的功能不需要寫回）。結束時刪掉草稿、關掉伺服器與 Chrome（`netstat` 8157／9337／9338 沒有在聽、沒有殘留的 `chrome-profile` 行程）。

1. 霧鎖真人表單：部位分三組「部位 1「拂塵」／部位 2「氣海」／部位 3「長劍」」（`docs/art/shots/nw2c/nw2c_05_parts_grouped_1600.jpg`）。
2. 火焰箭矢：量前比值區「還沒有比值…」→ 武器倍率 800→900（預算 88.7%）→ 模擬「比值」、每組 10 種子：估時「6 組 × 10 種子（1 招、6 組武器×招）…」→ 開始 → 改前 0.73～0.79、改後 0.85～0.93（變動格標黃），1 AP 箭類參考線兩邊都達標（`nw2c_01_ratio_result_1600.jpg`）；冷啟動 9.8 秒（含程序池啟動與輪詢）。再跑一次：改前快取命中，1.4 秒。
3. 比值區：來源「工坊量測（10 種子）」、類別無條件、六格與參考線（`nw2c_02_ratio_box_1600.jpg`）。
4. 匯入基準（搬家證據那份 3 招 20 種子 JSON）→ 點射：來源「匯入的基準（20 種子）」、類別條件類、直接 0.50、成立 直接 1.31～1.58；「條件成立 ≥ 1.10：1.58 達標」、「條件不成立 ≥ 0.60：0.50 低於〔建議，未定案〕」（`nw2c_03_baseline_pinpoint_1600.jpg`）。
5. 分組：「1 階遠程武器技」基礎傷害 ＋1 級 → 預覽 0.48 秒；斷腱射擊一列紅字「結構違規：骨架 displace：damage 占 53.8%，超過上限 50.0%（skeleton.secondary_share）」、判定「合格＋結構違規」；比值欄有值的是量過或基準裡的三招（`nw2c_04_group_violation_1600.jpg`）。
6. 800×600：比值區、比值結果表，頁面沒有左右捲軸（`nw2c_06_ratio_box_800.jpg`、`nw2c_07_ratio_result_800.jpg`）。
7. **浮動卡（6.5.1）**：本段沒有新的彈出層（比值區、匯入基準都是頁內區塊；新元件不用 `title=`，`floatCardRule.test.ts` 照過）。實測技能表單欄位名的 `<Hint>`：1600×900 與 800×600 都是「滑過出現（上方，214×36）→ 沿直線滑進仍在 → 捲到底仍在（內容短）→ 點擊釘住（`pinned`）→ 移走仍在 → Esc 關閉」。
8. **`__layoutSmoke.runTuning`** 1600×900、1040×624、800×600 全 PASS；另在每個尺寸對「點射＋比值分頁」「分組預覽」跑 `scan()`：1600、1040 都 0 項；800 寬點射表單有 2 項「溢出 div.tn-field-now「現值 1000‰（1」 109>103」（現值欄寫不下「1000‰（100%）」，是 NW-2b 的欄寬，和本段無關，見待決 8）；頁面都沒有左右捲軸。

截圖 7 張（jpg 80、皆 ≤ 177 KB），都在 `docs/art/shots/nw2c/`。

## 3. 搬家證據（T-C1）

指令（搬家前在 `404c56bd` 跑一次存檔，搬家後在同一個 worktree 再跑；`summary_cells` 移進核心後又跑一次）：

```
uv run python scripts/t1_skill_ratio.py run --skills skill_fire_arrow,skill_pinpoint_shot,skill_rng_venom_arrow --seeds 20 --jobs 4 --out <暫存>/before.json > before.stdout
uv run python scripts/t1_skill_ratio.py report <暫存>/before.json --detail > before_report.txt
uv run python scripts/t1_skill_ratio.py run --skills skill_shadow_backstab,skill_fire_arrow --seeds 5 --jobs 4 --detail --out <暫存>/before2.json > before2.stdout
```

| 檔 | 搬家前 SHA-256 | 搬家後 |
|---|---|---|
| `run` JSON（3 招 20 種子） | `291d99abd412896a3f27e6f0eed514af59c47b5b9f3497bca675f6c274b7728b` | 相同 |
| `run` stdout | `57f8622add435362ca630c58746461342097b76aa31f090e0c06bda98abd72e6` | 相同 |
| `report --detail` | `2e0d7946c5f29a15dea2593be53f64a92b457f39231a72637e87ef3c1e664af5` | 相同 |
| `run --detail` JSON（背刺＋火焰箭矢 5 種子） | `a4c2bf70529d984e21027ccebe7f95222316e5f32273141519bd89295d6bccf5` | 相同 |
| `run --detail` stdout | `ab155c3345c3de527f99b7888729f340e7711889d28718563cf70bbad591a548` | 相同 |

stderr 只有兩行（招數組數與「寫入 <路徑>」），除了輸出路徑外相同。第二組含瞬步背刺（背後格擋住的「不成立」與 `_target_back`）與 `--detail` 明細。

## 4. 改到的既有測試、相容改動

| 測試 | 舊 → 新 | 為什麼 |
|---|---|---|
| `tests/api/tuning/test_parts_pb1n.py::test_part_hp_total_over_600_is_refused_in_chinese` | `"加總不能超過 600‰（收到 601‰）" in m` → `m == "所有部位的血量加總不能超過 600‰（收到 601‰）"` | 訊息改中文、拿掉單位 ID 前綴；改成整句相等，順便鎖住「沒有英文識別字」 |
| `client/src/tuning/tuning.test.ts`（規模與估時）、`skills.test.ts`（`OPTIONS`） | 手寫的 `TuningSimOptions` 多 `ratio_default_seeds: 50`、`ratio_max_work: 40000`、`ratio_battles_per_second: 450` | openapi-typescript 把回應中有預設值的欄位標成必填；斷言沒動 |

- `tests/content/test_boss_parts_content.py` 的部位測試只比對 `"600"`，照過、沒改。
- 相容改動：`SimJobs._launch` 多選填 `same`、`estimate_s`；`_Plan` 多三個有預設值的欄位；`_record_timing` 拆出 `_write_timing`（舊行為不變）；`SkillForm` 多選填 `ratio`／`ratioLoading`（不給就不顯示比值區）；`simEstimate` 多選填 `ratioPlan`；`TuningSimRequest.seeds` 上限 160 → 250（頭目戰、地圖戰另有 160 場上限，照擋）。
- OpenAPI：只有新增（`TuningRatio*`、`TuningSkillRatio`、`TuningViolation` 用在分組列、`TuningFieldView.group_zh`、`TuningGroupRow.violations`／`ratio`、`TuningSimOptions.ratio_*`、`TuningSimJob.ratio_result`、`TuningSimRequest.skills`、`scenario` 多 `ratio`、四個端點），加上 `seeds` 的 `maximum`。
- 沒有重產任何 CLI 快照、前端夾具或 parity 夾具；`content/` 沒動；引擎沒動。

## 5. 實測數字（Windows 11、16 邏輯核心、程序池 4）

| 項目 | 數字 |
|---|---|
| 比值：1 招（火焰箭矢）6 組 × 10 種子，改前改後各一次、程序池冷啟動（實機） | 9.8 秒（含 spawn 4 個行程與每秒輪詢；第一次實機 6.5 秒） |
| 同上第二次（改前快取命中，只跑改後） | 0.5～1.4 秒 |
| 腳本：3 招 18 組 × 20 種子（程序池 4，含 spawn） | 約 7.8 秒 |
| 測試內（執行緒池）1 招 6 組 × 2 種子、改前改後 | 6.6 秒（含兩份內容庫載入與工作區複製） |
| 分組預覽 45 招（含 `validate_skill`，實機含畫面） | 0.48 秒（NW-2b 不跑 `validate_skill` 時 0.33 秒） |

`ratio_battles_per_second` 會被小工作的啟動時間拉低（10 種子一次後估時變成「3～5 秒」），大工作時估時偏高；見待決 4。

## 6. 安全措施對照

| 措施 | 怎麼驗 |
|---|---|
| 比值只讀、不寫 `content/` | 只寫 `<save_dir>/tuning/ratios/` 與 `sims/timing.json`；測試用暫存存檔資料夾、`git = None` |
| 一次一個模擬、可取消 | 沿用 `SimJobs._launch`（`start_ratio` 走同一個鎖與 409） |
| 規模上限 | 40,000 組×種子，`ratio-plan` 與 `start_sim` 同一個判定（測試） |
| 參考線不擋寫回 | 比值不參與 `check`／`apply`（沒有接進驗證流程） |
| 匯入的 JSON 是資料 | 只檢查欄位型別後存檔，不執行；格式不對 422（測試） |

**沒驗證的**：DD-2 的期望值夾住沒有實機（雙匕首戰鬥要攔 `POST /api/battles`，只靠單元測試）；比值 250 種子的實際耗時；寫回後「改後量測變成目前值」的實機（測試只驗存檔鍵）；1040 寬的比值結果表截圖；部位分組只拍了 1600。

## 7. 待 PM 決定

1. **參考線比「範圍最高值」，1 AP 箭類取代 0.9**：無條件 1 AP 箭類只看 ≥ 0.6（建議線），不再同時標 0.9；條件類兩條（成立 ≥ 1.1、不成立 ≥ 0.6）；變奏算「成立」；綁定武器與雙匕首不進參考線。是 BAL-21e 判法的延伸，最保守的解讀。（規格 D4、BAL-21e 待決 1）
2. **DD-2 的夾住只在 API 顯示層**：引擎的期望值給 AI 用（AI 另以目標 HP 夾），改引擎會換 AI 固定種子，所以沒動。要不要連引擎一起改，另排段並跑 AI 固定種子。（DD-2 待決 3）
3. **`TuningSimRequest.seeds` 上限 160 → 250**：比值和頭目戰、地圖戰共用 `seeds`；頭目戰、地圖戰仍受 160 場上限擋。比值每組上限 250（BAL-21e 的規模），規格只寫了組×種子 40,000。（T11）
4. **估時的每秒場數用上一次實測**（規格 5.7）：小工作被行程啟動時間拉低（實測 10 種子後約 18 場／秒），之後的大工作估時會偏高。要不要只在 ≥ 某規模時才更新。（T11）
5. **基準匯入記的是匯入時的樹雜湊**：腳本 JSON 沒有內容雜湊（輸出要逐字相同，不能加），所以「內容已變」是指匯入之後有改內容；匯入一份舊內容跑出來的 JSON 不會被標出來。畫面與回應都寫了「請匯入用目前內容跑出來的結果」。（T12）
6. **改後量測也存**：鍵用草稿資料夾的樹雜湊，寫回後內容剛好相同（沒有預算例外的附帶改動）時表單直接顯示為目前值；有附帶改動時要再跑一次。（T12）
7. **分組預覽的結構違規只標示、不擋「放進草稿」**：整包驗證照擋寫回；要不要在預覽就把這些招排除。（NW-2b 待決 5）
8. **800 寬點射表單的「現值」欄寫不下「1000‰（100%）」**（`scan()` 2 項溢出，NW-2b 的欄寬，本段沒動）；要修請排前端小修。
9. **部位分組只在前端集中**（後端 `concrete_fields` 順序仍是欄位為主，差異頁、草稿順序也是）；PB-1n 提到的「動 `concrete_fields` 會影響所有 `[*]` 欄位」照保守做法沒動。（PB-1n 待決 2）
10. **部位其他兩句訊息仍含 `parts`**（「parts 要有 2～4 個部位」「parts 的 id 不能重複」）：工坊改不到部位數與 ID，碰不到；本段只照裁定改 600‰ 那句。（PB-1n 待決 3）

**新增的複雜度 noqa**：`src/trpg/api/tuning/objects.py::_part_group` 一個 `# noqa: PLR2004`（`len(parts) < 2`，同檔 `_part_label`／`_part_skipped` 的寫法）。沒有新增 `C901`／`PLR0911`／`PLR0912`／`PLR0915`。腳本原本的 `# noqa: PLW0603`（全域內容庫）隨搬家拿掉。
