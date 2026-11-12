# Phase PB-1n 報告：數值工坊開放頭目部位欄位與 AI 部位評分

> 實作者：implementer agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhasePB-1計畫.md` 第 6 節，另加派工 prompt 的「PB-1b 的 AI 部位評分 8 個占位值（`content/ai_profiles.yaml` 的 `parts:`）」。
> 分支 `worktree-agent-addbdd2d692f29d8d`，從 origin/main 分出後 `git merge --ff-only main`（`56528be9` 是祖先）；未 push。只做 1n；引擎、AI 邏輯、內容數值都沒動。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 白名單：部位 | `content/tuning_fields.yaml` 的 `kind: unit` 加 16 個樣式：`parts[*].hp_permille`（permille，建議 50～400，說明含「加總不能超過 600‰」）、`parts[*].armor_bonus`（建議 0～15，「沒寫＝和本體相同」）、`parts[*].resist.<physical/elemental/nature/spirit>`、`parts[*].element_mods.<九元素>`、`parts[*].on_break[*].amount`（`existing_only`；說明依 `stat` 寫清楚格／點／‰，`damage_dealt` 是倍率‰、750＝−25%、要小於 1000） | `97de7951` |
| 白名單：AI 部位評分 | 新對象種類 `kind: ai`（`glob: ai_profiles.yaml`，`TARGET_MODELS["ai"]=AiProfileTable`）只開 `parts.*` 8 個值（`seal_skill`、`interrupt_charge`、`stat_down`、`control`、`stop_mechanic`、`priority_bonus`、`guard_back_bonus`、`near_break_permille`），每個都有中文說明與建議範圍 | `97de7951` |
| 展開與標籤 | `api/tuning/objects.py`：`_part_label`（「部位「拂塵」血量（‰）」；數量欄位依 `stat` 換成「部位「長劍」破掉後第 1 個效果：之後造成傷害的倍率（‰；750＝−25%）」）、`_part_skipped`（`on_break[*]` 只展開 `stat_down`，仿 `_phase_skipped`）、`_part_limits`（擋的範圍照 `content/parts.py`）、部位護甲／抗性沒寫時顯示「沒寫＝和本體相同」；AI 表的清單名「AI 估值表（全體共用）」與頂端三句提示（`AI_NOTES_ZH`）；`diff.py` 用同一個名字 | `97de7951`、`bf11b5eb` |
| 錯誤對到欄位 | `api/tuning/check.py` 加 `_BREAK_KINDS`：pydantic `loc` 在 `on_break[i]` 後多一段判別值，對欄位時拿掉（否則「要小於 1000」掉到頁首） | `97de7951` |
| schema 檢查 | `content/tuning_fields.py` 的「對得到 schema 整數欄位」走訪原本就穿得過 `BossPart`／`PartBreakEffect`（判別聯集逐一展開、`dict[ResistGroup, int]` 以列舉值當鍵），不必另寫；只加 `ai` 種類 | `97de7951` |
| 前端（最小） | `TuningCategory` 加 `ai`（`openapi.json`、`schema.d.ts` 重產）；`model.ts` 的 `objectKind`、`TuningScreen` 在「敵人與頭目」分頁多讀 `/objects?kind=ai` 併入清單、選到時用 `ai` 讀欄位；`FieldForm` 清單多一組「AI 估值（全體共用）」、表頭類別文字。表單本身照 `fields` 自動產生，沒改 | `66576cd7` |
| 測試 | 新檔 `tests/api/tuning/test_parts_pb1n.py`（21 項，數值一律讀 `content/` 現值，使用者寫回後不必收編）；`test_yaml_patch.py` 的 `_concrete_cases` 改用 `concrete_fields` 展開（加部位列）；`tuning.test.ts` 加 2 項 | `97de7951`、`66576cd7`、`9acd2117` |
| 截圖 | `docs/art/shots/pb1n/` 6 張（1600 寬 5 張、800 寬 1 張） | `f2203faa` |
| 筆記 | `docs/dev/上手-內容資料與模擬.md` 第七節加「頭目部位與 AI 部位評分（PB-1n）」 | 報告 commit |

## 2. 驗收

### 2.1 規格第 6 節第 3 點

| 項目 | 測試 |
|---|---|
| T-A1：每個新路徑對得到 schema | `test_part_and_ai_fields_are_whitelisted_with_hints_and_notes`（`load_tuning_fields` 的載入檢查＋每個樣式都有說明與建議範圍）、`test_mist_lock_expands_three_parts_and_only_the_stat_down_amount`（3 個部位全展開；`on_break` 只有長劍第 1 項）、`test_units_without_parts_get_no_part_fields` |
| T-A2：YAML 字面替換 | `test_patch_flow_part_value_changes_only_that_number`（流式部位）、`test_patch_flow_effect_amount_inside_block_part`（區塊式部位裡的流式效果）、`test_patch_inserts_missing_part_armor_and_resist_keeping_comments`（流式插 `, armor_bonus: 5`、區塊式插一行、整個 `resist` 沒寫插 `resist: {physical: 250}`、註解保留、刪掉回原樣）、`test_patch_ai_parts_value_keeps_the_rest_of_the_file`；`test_yaml_patch.py` 的 hypothesis 300 例含部位路徑 |
| 加總 601 擋下、中文原因 | `test_part_hp_total_over_600_is_refused_in_chinese`：三個改動都掛「parts 的 hp_permille 加總不能超過 600‰（收到 601‰）」 |
| 其他非法值 | `test_illegal_part_values_are_refused`（8 例：長劍 1000「要小於 1000」、0、血量 0、部位抗性 1200、封招的數量「不開放」、快破門檻 1001、AI 負值、`old` 不符） |
| 改 `whisk` → 只差那一個值 | `test_writeback_changes_only_that_literal[whisk]`、`[ai]`（暫存 repo；commit 主旨、只動那個檔那一行、LF 照舊） |
| 改後驗證＋小模擬 | `test_part_and_ai_changes_validate_and_run_a_smoke_battle`：長劍降傷、拂塵血量、氣海護甲、AI 封招價值一起改 → 驗證通過 → 草稿內容庫跑霧鎖真人 1 場（`probe_battle`） |

### 2.2 實機（自己的 worktree 內的 clone；伺服器埠 8163、無頭 Chrome `--mute-audio`）

照上手-內容 第七節坑 5：`git clone --local --no-hardlinks . .scratch_pb1n/repo`、clone 裡 `checkout -b main`，`TRPG_TUNING=1 TRPG_CONTENT_DIR=<clone>/content TRPG_SAVE_DIR=.scratch_pb1n/saves trpg serve --port 8163`。**寫回 commit 只落在 clone，主資料夾與 worktree 分支沒有 `tune:` commit；clone 已刪。**

1. 「敵人與頭目」分頁清單多一組「AI 估值（全體共用）（1）」；點開是 8 個值、建議／允許範圍與三句提示（`pb1n_01_ai_parts_1600.jpg`）。
2. 霧鎖真人表單的部位欄位（`pb1n_02_mist_parts_1600.jpg`）、長劍降傷欄位（`pb1n_03_sword_amount_1600.jpg`）。
3. 三個部位填 250／250／101 → 0.5 秒後驗證，三格都紅字「加總不能超過 600‰（收到 601‰）」（`pb1n_04_…_1600.jpg`、`pb1n_05_…_800.jpg`）。
4. 經 API 寫回 `whisk 200→150`＋`parts.seal_skill 8→12` → clone 得到 `tune(ai_profiles,sect_mist_lock_master): parts.seal_skill 8→12 等 2 項`，`git show` 只有兩個檔各一行、只差那個數字；重讀表單現值 150‰（`pb1n_06_after_writeback_1600.jpg`）。
5. 小模擬（頭目戰、霧鎖真人、build_fire＋build_tank 各 1 種子，草稿長劍 750→500）：4 場跑完 12.1 秒，改前改後都是 2 場 2 勝、18 回合（樣本太小，只證明流程通）。

### 2.3 結束碼

| 指令 | 結束碼 |
|---|---|
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `mypy`（1515 檔） | 0 |
| `lint-imports`（14 kept） | 0 |
| `pytest tests/api/tuning tests/content tests/api/test_openapi_snapshot.py -n 8` | 0（見第 4 節） |
| `trpg content check` | 0 |
| `corepack pnpm -C client typecheck`／`test`／`build` | 0／0／0 |

## 3. 給使用者的使用說明（頭目部位）

1. 進數值工坊 →「敵人與頭目」→ 霧鎖真人，往下捲就是「部位「拂塵／氣海／長劍」」的血量、護甲、抗性與「破掉後」的數字；隊友 AI 愛不愛打部位、頭目護不護背，在同一個清單最下面的「AI 估值表（全體共用）」（改了影響所有戰鬥）。
2. 部位血量是頭目開場最大 HP 的千分比，同一隻頭目三個部位加總不能超過 600‰，超過時三格都會紅字擋下。
3. 長劍破掉後「之後造成傷害的倍率 750‰」（＝打出 75%，−25%）和 AI 的 8 個值都是占位，請直接改成你要的數字、跑小模擬比較後再寫回。

## 4. 待 PM 決定

1. **AI 估值表開了一個新對象種類 `ai`**（規格第 6 節沒寫，派工 prompt 要求）：只開 `parts:` 8 個值，其餘照 NW 計畫留給 NW-3；前端放在「敵人與頭目」分頁（不新增分頁）。NW-3 開其他 AI 欄位時只改白名單。
2. 部位欄位的排列是「欄位為主」（三個部位的血量、三個部位的護甲……，同 `phases[*]` 的做法），霧鎖真人表單多 46 列；要改成「部位為主」分組要動 `concrete_fields` 的順序（會影響所有 `[*]` 欄位），沒做。
3. 加總超過 600‰ 的訊息沿用整包檢查的原文「單位 sect_mist_lock_master：parts 的 hp_permille 加總不能超過 600‰（收到 601‰）」，含英文識別字；要換成純中文要改 `content/parts.py` 的訊息（會動 PB-1a 的測試字串），沒做。
4. 使用者寫回部位或 AI 值後會變紅的既有測試（`tests/engine/test_mist_lock_parts_pb1.py` 寫死 200‰／24／750、`tests/engine/test_parts_ai_pb1.py::test_the_value_table_has_placeholder_values` 寫死 8 個值）列進上手筆記的收編說明；是否先改成讀內容，由 PM 決定（本段沒動引擎測試）。
5. 部位 `resist` 經工坊插入後再還原，會留下 `resist: {}`（語意同沒寫；yaml_patch 只刪那一項，不刪空的上層），沿用現行行為。
6. `pytest tests/api/tuning tests/content …` 全段 3159 項通過、結束碼 0，是在標籤微調（`bf11b5eb`）與測試改讀現值（`9acd2117`）之前跑的；之後只重跑了 `test_parts_pb1n.py`（21 項）與合併前的指定檢查（見 2.3 最後一次的結束碼）。
