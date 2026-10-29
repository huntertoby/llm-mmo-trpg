# Phase 4-L7 報告（名稱與敘事）

規格：`docs/phases/Phase4計畫.md` 3G 節。實作者：sonnet。全部測試用 `MockLLMClient`，未呼叫真模型（8001 埠未碰）。

## 做了什麼

1. **命名與敘事 prompt**（`llm/prompts/naming.py`，`NAMING_PROMPT_VERSION = "skill-naming/1"`，有快照測試）：沿用碎界語氣與名詞表（`content/llm/world_shattered.yaml`），任務段改為命名。輸入 `<skill>` 區塊只放中文名稱（骨架、效果、形狀、關鍵字、元素、主題、已用名稱），沒有數值或代號；重試時帶 `<previous_naming>`／`<errors>`；玩家文字（若有）一律包 `<player_input>` 並跳脫。JSON schema 只有 `name_zh`、`concept`、`cast_flavor`，長度上限來自世界觀資料。
2. **規則資料**：`WorldStyle.naming`（`NamingRules`：`name_max_chars` 12、`concept_max_chars` 80、`flavor_max_chars` 80、`forbidden_terms`）寫在 `world_shattered.yaml`，換世界觀只換資料。系統指令（提議 prompt）沒變，`PROMPT_VERSION` 不升。
3. **`llm/naming.py`**：`name_skill`（最多 3 次重試，`LLMUnavailable` 立即退回）、`check_naming`、`fallback_naming`、`apply_naming`（只 `model_copy` 換 `name_zh` 與 `narrative`，結構與數值不動）。檢查碼：`*.empty`、`*.too_long`、`*.charset`（名稱只能全形中文、`・`、全形括號；敘事只能全形中文與全形標點，所以英文代號、數字、半形符號、標籤、程式碼片段都被擋）、`*.forbidden`（禁字表）、`name_zh.duplicate`（和內容庫技能名稱及本提議器已發出的名稱重複）。仍失敗用組合式名稱「元素・骨架」（無元素則只有骨架，撞名加「（二）」）與模板敘事，和隨機組合器同一做法。
4. **接點**：`make_proposer(..., naming=<client>)`；結構合格的 `llm` 來源技能才命名（組合器、技能池、失敗提議都不呼叫）。`naming=None`（預設）＝沿用提議裡的名稱與敘事，行為與 4-L6 完全相同。CLI `--llm` 傳入同一個本機 client、`--llm-mock` 用 `mock_naming_client`（確定性、依種子挑詞）；開關同 4-L6 的 `generate`。`name_attempt` 為公開輔助函式（測試也用）。
5. **run 紀錄與存檔 `trpg-run/9`**（`/5～/8` 可讀）：`LlmRecord`／`LlmTrace`／`LlmAttempt` 新增 `name_source`（`llm`／`fallback`／無）、`name_attempts`、`name_codes`。生成的名稱與敘事本來就隨候選的 `SkillDef` 存檔，重播與讀檔不呼叫 LLM（測試：存讀檔前後命名呼叫次數不變）。`trpg run` 摘要多一行「LLM 命名：N 個，生成 x，組合式名稱 y，呼叫 z 次」。
6. 卡片與戰鬥紀錄本來就讀 `SkillDef.name_zh`／`narrative`，不需改；roguelite 同輪撞名仍由 `unique_skill_name` 加「（二）」。API 未改。

## 驗收

- pytest：`tests/llm tests/skillgen tests/roguelite tests/narrative tests/api tests/content tests/test_architecture.py` 4499 過（含新增）；`-m "slow or not slow" tests/cli --timeout=3000` 154 過。CLI 快照未變（預設關閉）。
- `ruff check`、`ruff format --check`、`mypy`（781 檔）、`lint-imports`（7 契約）全過。
- `trpg run auto --seed 1 --llm-mock` 跑完，顯示「LLM 命名：1 個，生成 1」；`--seed 3` 兩次輸出逐字相同。
- 新測試：`tests/llm/test_naming.py`（36：過長／空字串／指令字樣／英文代號／標籤／重名各自退回組合式名稱、回饋重試後恢復、連不上、`<think>` 與程式碼框清理、套用只改文字、prompt 快照與 `<player_input>` 跳脫、提議器整合）；`tests/roguelite/test_llm_run.py` 新增 3 個（命名紀錄與讀檔不重呼叫、整輪確定性、`/8` 舊存檔可讀）。既有測試只改 `trpg-run/8` → `/9` 字串。

## noqa

無新增。

## 待 PM 決定

1. **命名去重範圍**：只比對內容庫技能名稱與「同一個提議器已發出的名稱」；這一輪已持有的技能名稱提議器看不到，撞名仍由 roguelite 加「（二）」（行為與組合器相同）。要在 prompt 的 `taken_names` 帶入本輪持有技能，需把名單傳進題目（改 `LlmProposer` 簽名）。
2. **提議時已有的 `name_zh`／`concept`／`cast_flavor`**：命名步驟開啟後會被覆蓋（提議 schema 仍要求 `name_zh`，12 字上限）。未移出提議 schema，以免動到 `PROMPT_VERSION` 與 4-L5 的驗證；要省 token 可在 4-L8 移除。
3. **多一次呼叫**：每個成功的 LLM 候選多 1～3 次命名呼叫（本機模型約數秒）；失敗的提議不命名。
4. **字元集較嚴**：名稱只允許中文、`・`、全形括號；敘事不允許阿拉伯數字（模型寫「3 格」會被退回）。若實測退回率高，可放寬敘事的全形／半形數字。
5. **禁字表較保守**（「系統」「提示」「輸出」「指令」等也禁，可能誤擋少數正常用詞），可在 `world_shattered.yaml` 調整；英文與標籤由字元集擋。
6. **`--llm-mock` 整輪成功率仍低**（4-L6 待決 1），所以整輪 CLI 實測命名次數少；命名邏輯由單元與提議器整合測試覆蓋。
7. **組合式名稱的敘事是固定模板**（「以X為本的技能。」「力量依你的意志成形。」），沒有組合器的「（暫定）」字樣；若要全部技能風格一致需 PM 指定。
8. 命名 prompt 版本號只在測試快照與 `naming_prompt_record`，尚未寫進 run 紀錄（提議 prompt 版本也尚未寫進，沿用 4-L2 的待辦）。
