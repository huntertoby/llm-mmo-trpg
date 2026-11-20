# Phase HC-B 計畫：技能預算的計價全部開進工坊

> 來源：專案 PM 轉使用者（2026-11-21）。使用者看著工坊的「技能預算表」問：
> 「為啥技能預算表 能改的數值哪麼少 比如說我想調低升起地形需要的預算 沒看到」
> 接在 HC-4a 之後：HC-4a 改了 `content/tuning_fields.yaml` 和 `src/trpg/skillgen/budget.py`。
> **數字一律照現值搬，不試數值，不跑平衡量測。**

## 現況

- 44 個原語的 `base_points`（例：`raise_terrain`）在 `content/skill_primitives.yaml`。這個檔在 `tuning_fields.yaml` 的 `forbidden_files` 裡，因為 schema 匯入時從固定資料夾讀，草稿看不到。
- SK-3b 已經用同一招，把鉤、疾病擴散、吸收表面的點數搬到 `content/skill_budget.yaml`（見 `src/trpg/content/skill_rules.py` 約 480 行），工坊因此改得到。
- `skill_shapes.yaml` 的形狀倍率（`budget.base_permille` 等）、`modifier_changes.yaml` 也在 `forbidden_files` 裡。

## 範圍

1. **原語點數搬家**：照 SK-3b 的做法，把所有原語的 `base_points` 搬到 `skill_budget.yaml`，例如 `primitive_points.<原語 id>`，值不變。
   - `skill_primitives.yaml` 的 `base_points` 拿掉，讀的地方都改讀 `skill_budget.yaml`。不要留兩份。
   - SK-3b 搬過的鉤、擴散、吸收要不要併進同一張表：可以併，值不變就好，報告寫明。
   - 開進工坊白名單。每個原語都要有中文名稱（取原語既有的中文名），說明寫清楚調高、調低的效果，例如「越大，這種效果在同預算的技能裡越弱」。
2. **其他看不到的計價**：逐項盤點「影響技能預算、但工坊看不到」的數值，能搬的搬，搬不了的寫原因。至少看：
   - `statuses.yaml`、`surfaces.yaml` 的 `budget_points`：如果工坊已經有這兩個檔的 target，只要補白名單欄位就好。
   - `skill_shapes.yaml` 的形狀倍率：照第 1 項的做法搬到 `skill_budget.yaml`（例如 `shape_budget.<形狀 id>`），值不變。`by_value_permille` 這種查表結構如果搬起來很彆扭，就先不搬，寫原因。
   - `skill_budget.yaml` 裡已經有、但白名單沒開的欄位（`ap_coefficient_permille`、各種 `*_permille`、`collision_die_points` 等）：全部開。
   - `modifier_changes.yaml`、`skill_triggers.yaml`、`skill_conditions.yaml`、`skill_synergies.yaml` 裡跟預算有關的係數：能開就開，不能開就寫原因。
   - 報告附一張表：數值、原本在哪、現在在哪（或為什麼沒搬）。
3. **工坊預算表分組**：欄位變多以後要分組，讓使用者找得到。至少分「原語點數」「狀態」「表面」「形狀」「係數」「召喚」，其他照內容自訂。分組放在白名單（例如 `group_zh`），前端照分組畫成可收合的區塊。要截圖：改之前、改之後各一張，存在 `docs/art/shots/hc-b/`。

## 不做

- 不改任何數值。不改預算公式。
- 不動 `docs/design/`、`config/`、`llm.toml`。

## 驗收

- **值不變的證明**：
  - 內建全部技能的預算總點數搬家前後逐招相同（寫腳本比，報告附結果；不同＝0）。
  - `tests/skillgen/test_refactor_parity.py`（`-m slow`）照舊通過。
  - 戰鬥不變比對：除了 `ruleset_hash` 以外 different=0。
- 工坊：改 `primitive_points.raise_terrain` 的草稿，預算表上的升起地形技能預算比例跟著變（加一個測試）。
- 寫死數值掃描：`scripts/hardcoded/classify.py --check` 是 0；新增的 yaml 欄位有被清單涵蓋。
- 交件前跑完所有非 slow 的測試目錄（分目錄、一次一組、最多 `-n 8`；`tests/llm` 和 `tests/skillgen` 不同時跑），加上 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`；ruff、format、mypy、lint-imports、前端 tsc、vitest、build 都要 0。
- 快照、夾具先預測再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- 報告寫在 `docs/phases/PhaseHC-B報告.md`。
