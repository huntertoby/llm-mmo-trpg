# Phase QF-1 計畫：兩件小修

> 來源：`docs/phases/PhaseAP-2b報告.md` 待決 3、4 與開發 PM 裁定。
> 小段。同時有 X10-1 在改 `content/` 的 schema 與 `skill_primitives.yaml`、`scripts/x10/`；這段不要動那些檔，真的要動就停下來回報。

## 範圍
1. **數值工坊批次改 `ap_cost`**：`src/trpg/api/tuning/skills.py` 的範圍 (1, 3)，遇到帶 `borrow_ap` 的技能要放行 0（只放行 0，不放行 0 以外的新值）。不帶預支的照舊 1～3。
2. **形態 build 開場報錯**：`build_form_mastery`、`build_form_tester_2` 用 `--ally-build` 開場就報錯（`skill_form_breath_dragon`），改前就有。
   - 先查原因：是資料錯、是 build 設定錯，還是程式錯。
   - 修好後在報告寫明原因。
   - 如果要改技能資料、改規則才修得好，先停下來回報。

## 驗收
- ruff、format、mypy、lint-imports、`trpg content check` 結束碼 0；相關測試分目錄跑，不要用 `-m ""`，不跑全量。
- 兩項都要有回歸測試。
- 戰鬥不變比對：既有戰鬥 different=0。第 2 項會讓原本報錯的那兩場能跑，這兩場要另外說明。
- 每項一個 commit。報告寫在 `docs/phases/PhaseQF-1報告.md`。
