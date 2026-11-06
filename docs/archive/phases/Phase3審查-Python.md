# Phase 3 結束審查｜Python 端（2c42268..e789993，`src/trpg`、`content`）

> 審查者：opus 審查 agent（只讀），2026-10-23。PM 的排程決定見 `Phase3計畫.md` 第 38 節。

1. **【嚴重，已實測】變奏可偷帶禁用原語，執行時引擎崩潰**（3-25b #4 的漏洞）：`content/skills.py:2101`、`:2113`（`_all_effect_specs`）只走基礎效果，沒檢查 `variant.add_effect`／`replace_effect.effect`；`variant_form` 驗證時 `variants=()` 又跳過。實測 `skill_tidal_spear` 變奏 `add_effect: delayed_damage` 驗證通過，執行時 `bombs.py:42-45` 的 `bomb_spec` 只查基礎型態 → `StopIteration`。另 `copying.py:66`、`skill_triggers.py:314`、`ai/utility.py:1953` 拿基礎型態（語意漏洞，不崩潰）。`rule_change` 已由常駐類擋住；`grant_skill` 沒問題。修：檢查走過變奏效果；禁用清單改 `skill_primitives.yaml` 旗標（例 `lookup_by_skill_id: true`）；回歸測試。小，3E-2。
2. **原語分派沒有預設分支，未實作的原語靜默失效**：`interpreter.py:1302`（`build`）→ `:2362`（`tile_effect` 無 else）。新增原語要改 schema（`skills.py` 約 80 處 `type ==`）、解譯器、預算、AI、預覽、敘事、`keyword_derive`。修：if 鏈改登錄表；載入時檢查 `skill_primitives.yaml` 每個原語在解譯器、預算、AI、敘事都有對應，缺了就報錯。中，3E-2。
3. **效果樹走訪重複四份、涵蓋不一致**：`content/skills.py:2113`、`keyword_derive.py:60`、`engine/skill_infusion.py:93`、`skillgen/combo.py:24`（漏 zone 子效果；followup、陷阱、反噬、變奏不一致）。修：統一 `SkillDef.iter_effects(include_followup=, include_variants=)`。小，3E-2。
4. **技能 schema 過度耦合，不適合 LLM 生成**：`EffectSpec` 扁平約 40 個專用選填欄位；19 個 `model_validator`；`skills.py` 3564 行。修：由 `skill_primitives.yaml` 的 `params` 自動產生每原語一支的 discriminated union 作為 LLM 提議模型，驗證後轉回 `EffectSpec`；拆檔。LLM schema 設計 3E-2，拆檔 3E-3。
5. **pytest 卡 97～99%、偶發 ImportError**：`tests/**/__pycache__` 有 64 個 `*.pyc.<pid>`（多個 pytest 同時寫同一 checkout）；worktree 不會被收集。ImportError 可能來自多 agent 共用主 checkout 的 `__pycache__`／`.venv`、`uv run` 自動 sync 重裝、收集途中 `git merge`。卡住：`sim/batch.py:188`、`sim/attack_flow_report.py:197` 用 spawn `Pool`＋`initializer`，子行程失敗時 `Pool` 無限重開、`map` 不返回。修：改 `ProcessPoolExecutor`（`BrokenProcessPool`）、加 pytest-timeout、jobs>1 的測試 `xdist_group` 或 slow、agent 在自己 worktree 跑並 `UV_NO_SYNC=1`／`uv run --frozen`、清暫存檔。小，3E-2。
6. **`LOG_FORMAT` 版本策略**：本範圍改版 22 次、docstring 成變更紀錄、平行分支要合併定號；只改 YAML 數值卻不升版。建議：JSON 結構版本與可重播性分開；`BattleLog` 記 `ruleset_hash`；戰鬥中存檔改「重播後驗證」（存最終狀態 digest）；版本歷程移到 `docs/`；golden 紀錄重播測試。中，3E-3（Phase 4 大量新增原語則提前）。
7. **引擎循環依賴靠延遲 import**：`PLC0415` noqa 16 → 24（`delayed.py:134`、`rule_changes.py:42`、`traps.py:147`、`zones.py:376`、`skill_triggers.py:561/619`、`reactions.py:306`、`skill_infusion.py:407`、`lifecycle.py:133/138`）。修：登錄式 skill runner 或薄的 `skills/api.py`。中，3E-3（最好 Phase 4 前）。
8. **引擎寫死遊戲數值**：`gear_triggers.py:46` `DEFAULT_RUNE_ROUNDS=2`、`rules/statuses.py:45` `DEFAULT_DEFENSE_BREAK=100`、`summon_variants.py:24` `_MIN_CRIT=2`、`skillgen/evolution.py:400-402` 冷卻 2／2／5、`ai/charge.py:19` `_DEFAULT_BUFF_VALUE=3`。移到 YAML。小，3E-3。
9. **命名混淆、`engine/` 太扁平**（約 60 模組）：`infusion.py` vs `skill_infusion.py`、`summon_variants.py`（其實是分歧進化）vs `variants.py`、7 個 `gear_*.py`。拆 `engine/summons/`、`engine/gear/`。小到中，3E-3。
10. **新增 6 處 `PLR0917`**（`interpreter.py:276/348`、`ai/utility.py:2088`、`skills/mobility.py:282`、`skill_triggers.py:175`、`skillgen/option_followup.py:295`）：改 keyword-only 即可；`preview.py:526` `_outcome`（C901）改事件型別 → 處理函式表。小，3E-3。
11. **為測試吞 `KeyError`**：`summons.py:106-112`、`:143-148`、`delayed.py:111`；技能 ID 打錯會靜默 0 成長。測試改真實 ID、引擎直接報錯。小，3E-3。
12. **平行池重複、脆弱改名**：`sim/batch.py:170-195` 與 `sim/attack_flow_report.py:185-200` 幾乎相同；`random_composer.py:581` `_relabel` 用字串取代。抽 `sim/parallel.py`（第 5 點只改一處）；改結構化欄位。小，3E-3。

**整體評價**：確定性守則落實良好（無 `random`、時間、`hash()`、`uuid`、浮點結算；估值用 `Fraction`），依賴方向有測試。主要風險：新增原語要改很多處且漏做不報錯；變奏驗證漏洞（已實測崩潰）。建議 Phase 4 前完成 1、2、3、5，第 4 點至少定設計。
