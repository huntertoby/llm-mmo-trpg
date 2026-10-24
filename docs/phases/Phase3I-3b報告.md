# Phase 3I-3b 報告：雙屬性技能的對抗判定也用平均

規格：`docs/phases/Phase3I計畫.md` 4.5 節最後一點、`docs/phases/Phase3I-3報告.md`；設計 06 6.10（#46）。

## 盤點結果（重點）

盤點 `contest(`、`contest_chance(`、`status_save_chance(` 所有呼叫點後發現：**引擎與預覽的攻方值早就走 `skill_scaling_value`**。技能的擊倒（`Cast.knock_down`）、位移抵抗（`_displace_check`）、狀態抵抗（`status_effects`）、預覽的位移機率（`displace_checks`）與狀態機率（`_status_chances`）都以 `attack_value=skill_scaling_value(...)` 傳入；`contest` 只用 `attr` 去讀**守方**的屬性。3I-3 報告寫的「對抗屬性仍是武器主屬性」指的是守方比較的屬性與卡片文字，並非攻方的值。所以引擎不需改，`LOG_FORMAT` 不遞增（紀錄格式沒變；目前實際值為 `/68`）。

## 做了什麼

| 項目 | 做法 |
|---|---|
| 卡片 | `contest_label`：雙屬性技能寫「力量／智力（取平均）」（武器技與法術技皆是），單屬性技能維持原樣（武器技仍寫武器主屬性）；和算法句一致 |
| 文件註解 | `SkillDef.contest_attr` 說明：只決定守方被比的屬性，攻方的值是 `scaling_value` |
| 行為一致測試 | `tests/engine/test_arcane_blade_3i3.py`：擊倒對抗的實際 `modifier` ＝ 以 `skill_scaling_value` 算出的值（武器 × 第二屬性表格，含單屬性對照）；狀態抵抗 `attack_value` ＝ 縮放值、預覽機率不低於單屬性；`contest_label` 表格 |
| 普攻與非雙屬性技能 | 程式未動，既有測試（推擊、絆倒、`test_weapon_skill_scaling` 等）全過；表格內單屬性對照確認攻方值＝武器縮放值 |

## 檢查

ruff check／format、mypy、lint-imports（7 kept）通過；pytest engine、content、skillgen、narrative、api、roguelite 6589 passed 1 skipped；`-m "slow or not slow" tests/cli` 148 passed（快照與 run auto 種子無變動）；重播 `trpg battle --map open_plain --ally-build build_blank_arcane_blade --seed 3`（含魔劍斬）一致（130 動作）。

## 待 PM 決定

1. 守方仍比攻方的單一主屬性（武器技為武器主屬性；法術技為第一縮放屬性）。若要守方也取平均需另開規格（影響平衡）。
2. 推擊、絆倒、武器特性絆倒是普攻動作，沒有技能與第二屬性，維持單一屬性。
3. 玩法 PM 若原意是「引擎行為要改」：盤點顯示引擎已符合；請確認只需卡片文字與測試。
