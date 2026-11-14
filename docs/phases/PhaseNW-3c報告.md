# Phase NW-3c 完成報告｜造牆提示擴大＋組合器排除冷卻井

起點：本機 `main` `3c5c894f3`（worktree 原在 `a2642212d`，已 fast-forward）。
依據：`docs/玩法PM交接.md` 4.1.15；`docs/phases/PhaseNW-3b報告.md`（含開發 PM 裁定）；`docs/phases/PhaseCW-1報告.md`。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| 組合器排除冷卻井（4.1.15 第 4 點） | `skill_composer.yaml` 的 `structure` 加 `obstacle_exclude: [cooling_well]`（`StructureRules.obstacle_exclude`，預設空）。新函式 `composer_parts.obstacle_candidates(library)`＝`blocks_move`、非 `explosive`、不在排除清單的物件（排序），組合器 `_fixed_effect` 改用它抽物件。載入時檢查清單裡的 ID 是 `objects.yaml` 的物件（`library/load.py::_check_composer_objects`，錯誤指向 `skill_composer.yaml`）。程式沒有寫死任何物件 ID | `7243cd43c` |
| 造牆 HP 提示擴大（第 1、3 點） | `api/tuning/objects.obstacle_objects`＝手寫技能檔的 `create_obstacle` 物件 ∪ `obstacle_candidates(library)`，和組合器用**同一個函式**。提示字不變。現在掛提示的是 9 個物件：木箱、枯樹、土牆、倒木、冰牆、矮牆、倒塌物、石柱、荊棘叢；冷卻井、油桶（爆炸）沒有 | `55cf5e9ec` |
| 閃現延伸（第 2 點） | **沒改**。延伸效果（`flash_templates.yaml` 的 `extend_effects`）只把原技能既有的 `create_obstacle` 延長，物件來自原技能，已在上面的範圍裡 | — |
| 報告、上手筆記 | 本報告；`docs/dev/上手-內容資料與模擬.md` 第七節「造牆物件的 HP 提示」改寫，另加「組合器的造牆排除清單」一點 | 本報告 commit |

**為什麼放在組合器資料、不用物件 tag**：4.1.15 舉了兩種做法。物件 `tags` 要進 `OBJECT_TAGS`（「引擎認得的標籤」），而且 `narrative/tile_info.py` 要求每個標籤都有一句玩家看得到的說明（`test_tile_info.py` 鎖），另外會改規則包（`ruleset_hash`）、名詞表夾具與前端。這個排除只跟組合器有關，所以寫在組合器自己的調參檔 `skill_composer.yaml`（同檔已有 `fallback_secondary`、`target_conditions` 這類清單），不碰規則包、引擎、前端。ID 寫在資料、不寫在程式；新增「不該被組合器造出來」的物件只要加進這份清單。

## 2. 逐條驗收

| 驗收 | 結果 |
|---|---|
| 新規則有測試 | **過**。`tests/skillgen/test_obstacle_candidates_nw3c.py`（5 項）：候選＝標籤篩選減排除清單（對全部物件列舉）；冷卻井在排除清單、不在候選，木箱／石柱／三種牆在候選，候選沒有會爆炸的；控場骨架前 60 個種子確實造得出牆（避免性質測試空轉）；**性質測試**（hypothesis 40 個任意種子，控場骨架是唯一會抽 `create_obstacle` 的骨架）放出的物件都在候選內、沒有冷卻井；排除清單寫不存在的物件時載入失敗。`tests/api/tuning/test_nw3c_walls.py`（2 項）：提示清單包含全部組合器候選、含木箱等 6 個只有組合器會抽的牆、沒有冷卻井與油桶；物件表單上冷卻井的最大 HP 沒提示、木箱和土牆有（字逐字） |
| 戰鬥不變比對 46 場 | **過**：`battles=46 events=19276 different=0`（第 3 節） |
| OpenAPI | 沒改 API 型別（`notice_zh` 欄位 NW-3b 已有，只改哪些物件帶值），**不用重產**；`tests/api/test_openapi_snapshot.py` 過 |
| CLI 快照 | 預測 **0 鍵**，實際 0 鍵（第 4 節），沒重產 |
| `uv run trpg content check` | 結束碼 **0** |
| commit 前檢查 | `ruff check`、`ruff format --check`（2744 檔）、`mypy`（1618 檔）、`lint-imports`（14 kept）全過；pytest 見第 4 節。沒改前端，tsc／vitest 不需要 |

## 3. 不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive 3c5c894f3 src content` 解到暫存區，用 `PYTHONPATH=<暫存區>/src` 跑（腳本印出 `trpg.__file__` 確認用的是暫存區的程式）；改後＝本段工作樹。地圖預設陣容、效用 AI、`max_rounds=30`；每場比完整事件、步驟、勝方、最終狀態（拿掉 `setup`、`ruleset_hash`、`final_state.ruleset`）的 SHA-256。

- 8 張地圖 × 種子 1、2 ＋ `cloud_summit`、`rift_gate`、`molten_heart_pit` × 種子 3～12：**`battles=46 events=19276 different=0`**（兩份輸出檔逐位元組相同；事件總數和 NW-3／NW-3b 相同）。
- 理由也成立：沒改引擎、沒改規則包（`objects.yaml` 沒動）；戰鬥用內建技能，不經過組合器。

## 4. 快照與固定種子：預測與實際

**組合器是確定性的**：`compose_random_skill(seed, …)` 只用由種子建的 `Rng`；造牆物件是 `rng.choice(sorted(候選))`，`choice` 走 `randint(0, n-1)`（拒絕取樣）。候選從 10 個變 9 個，所以**只有抽到 `create_obstacle` 的那一抽**結果會變（之後的亂數也可能跟著變）；沒抽到的種子逐字不變。另外：候選清單現在和 CW-1（`e0c5fe8b3`）加冷卻井之前**完全相同**，抽到造牆的種子回到 CW-1 之前的結果。

**預測方法**：改之前在 baseline 跑一次會用到組合器的測試（`tests/skillgen`、`roguelite`、`api`、`sim`、`llm`、`world`、`narrative`、`cli` 含 slow，加上 engine／content 裡引用組合器、候選、工坊、開局的 33 個檔），用 scratchpad 的 pytest 外掛包住 `composer_parts._fixed_effect`，記下哪些測試**實際走到造牆那一抽**。結果：10342 passed，8 failed（全是要連真模型的 `test_real_model_*`／`test_neutral_address_real_model.py`，本機沒開 LLM，和本段無關）。

| 對象 | 預測 | 實際 |
|---|---|---|
| CLI 快照（`skills_list`、`skills_show_all/*`、7 個戰鬥鍵） | **0 鍵**：沒有一個快照測試走到造牆那一抽（都是內建技能與 build） | 0 鍵：`test_output_snapshots.py` 含 slow 全過，沒重產 |
| `tests/skillgen/fixtures/refactor_3wr2.json`（完整強度、升階、閃現 126 條） | **不變**：沒走到組合器造牆 | 不變，`test_refactor_parity.py` 全過 |
| 走到造牆那一抽的 214 個測試節點（59 個檔；`test_candidates.py` 15、`test_random_composer.py` 15、`test_flash_run.py` 9、`test_run_cli.py` 9、`test_wish.py` 9…） | 「可能變」：都是性質或寬鬆斷言，抽到的物件換了也該照樣過；沒有一個鎖住造牆物件或含造牆種子的雜湊 | 59 個檔＋快照、parity、OpenAPI、架構、工坊欄位共 **2194 passed、0 failed**，沒改任何既有斷言 |
| `tests/api/tuning/test_nw3b_small.py::test_obstacle_objects_come_from_the_skill_files` | **會紅**（舊斷言「提示清單＝只有手寫技能檔」，是這段要改的規則） | 改成「手寫技能檔 ∪ 組合器候選」；同檔其他測試沒改照樣過 |

## 5. 範圍外沒動

LLM 提議的物件列舉（`skillgen/proposal/params.py` 的 `objects`：全部物件）、技能工坊的物件選單（`option_params.py`：全部物件）、白板；規則包、引擎、前端（另一個 agent 在改 `client/src/render/`，沒碰）、設計文件與計畫檔。

## 6. 待 PM 決定

1. **LLM 提議與技能工坊仍可選冷卻井（還有油桶）當造牆物件**：4.1.15 只說組合器的造牆候選。LLM schema 的 `objects` 與工坊選單列的是全部物件；要不要也套用 `obstacle_exclude`（或改用 `obstacle_candidates`）請玩法 PM 定。照保守做法這段沒動（改 LLM schema 會動到提議的快照與 prompt）。
2. **排除寫在 `skill_composer.yaml`、不是物件 tag**：理由見第 1 節。若之後想讓「不當造牆候選」成為物件本身的屬性（例：工坊物件表單看得到），要另加不進規則包的欄位，再排一段。
3. **9 個物件都掛提示**：照 4.1.15 第 1 點「接受」，木箱、石柱、矮牆、倒塌物這些地圖物件的最大 HP 欄位下面現在也有「造牆技能會放出這個物件…」這行。

## 開發 PM 裁定（2026-11-14）

- 接受。46／0、CLI 快照 0 鍵；組合器確定性與受影響測試的預測方法（追蹤 baseline 214 節點）做得好。
- 待決 2：同意排除清單放 `skill_composer.yaml`，不用物件 tag。
- 待決 3：照 4.1.15。
- 待決 1（LLM 提議的物件列舉與技能工坊物件選單仍可選冷卻井、油桶）轉玩法 PM 定要不要也排除。
