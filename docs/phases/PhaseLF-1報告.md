# Phase LF-1 報告｜LLM 閃現的名稱與描述進遊戲、記進日誌、重播

> 實作 agent，2026-11-13。規格 `docs/phases/PhaseLF計畫.md` 第 3 節。依據 main `251eff3b`。
> commit：`4f38b770`（規格）、`30f090e7`（實作）、`d9d74e9e`（測試＋Mock 命名種子分流）、本報告與上手筆記一筆。

## 1. 做了什麼

| 項目 | 做法 | 檔案 |
|---|---|---|
| 變化帶文字 | `Variation` 加選填 `name_zh`、`note_zh`（`exclude_if` 為 `None`、不進 `key()`） | `skillgen/flash_state.py` |
| 引擎端文字檢查 | 新模組：`VariationText{key, name_zh?, note_zh?}`、`clean_text`（小變化不掛名稱；名稱全形中文與「・（）」≤ 12 字；描述全形中文與標點 ≤ 40 字；不合格的欄位丟掉、變化照常）、`clean_name`、`clean_note`、`text_map` | `skillgen/flash_text.py` |
| 出題掛文字 | 來源可選擇提供 `texts(library, request)`（`TextSource`）；`make_offer` 先 `proposed`、再 `texts`、再轉型保底與補位；`_Builder.option` 一律先 `clean_text`（沒有文字時也會清掉變化上原本帶的文字） | `skillgen/flash_offer.py` |
| 名稱留得住 | `flashed_identity`：最後一個大變化／轉型的 `name_zh`（`clean_name` 過了）取代「{前綴}・{原名}」。重推、升階重配、下一次閃現都沿用 | `skillgen/flash_derive.py` |
| LLM 端 | `judge_items(notes=)` 收下合格項目的 `note_zh`；`FlashProposalRecord.texts`；`LlmFlashSource(naming=)` 提議後呼叫新的 `name_texts`（用紀錄出一次題，對大變化與轉型 `name_skill`，照原技能區域與武器；沒有描述時用 `concept`，`clean_note` 過了才用；模型 `llm.unavailable` 時不命名）；`LlmFlashSource.texts()`、`RecordedSource.texts()`；`select_flash_source` 同一個 client 命名；`mock_flash_source(naming=False)` | `llm/flash_propose.py` |
| 開命名 | `LocalLlmProvider.flash_source`、`trpg run --llm` 用同一個 client 命名；`MockLlmProvider(flash_naming=False)` 預設不命名 | `api/llm_source.py`、`cli/run_llm.py` |
| 一輪與大世界的紀錄 | `FlashLlmRecord.texts`（`exclude_if` 空）；`growth._RecordedFlash(accepted, texts)` | `roguelite/state.py`、`world/growth.py` |
| 日誌格式 | `WLOG_FORMAT` `trpg-wlog/10`，`/7`～`/9` 照讀；模組說明補 LF-1 一段 | `world/save.py` |

**沒改**：`client/`、`content/flash_templates.yaml`、`api/flash_changes.py`、`api/run_schemas.py`（沒有加 `FlashOptionOut` 欄位，OpenAPI 不變；名稱已經在技能卡的 `name_zh` 裡，描述的 API 欄位排在 LF-3）。`docs/design/` 沒動。

## 2. 版號與相容

- `trpg-wlog/10`：閃現提議紀錄多 `texts`。沒有文字的那一行和 `/9` 逐字相同；`/9` 以前照讀（`READABLE_WLOG_FORMATS`）。測試字面改了 3 處（`tests/world/test_save.py` 兩處＋「不認得的格式」改用 `/11`、`test_field.py`、`test_field_lineup_seed.py`）。
- `LOG_FORMAT`（`trpg-battle-log/119`）**沒升**：戰鬥紀錄沒有新欄位（只內嵌 `SkillDef`，結構沒變），所以派工提的 3 個 `endswith` 測試不用動。
- `CHAR_FORMAT`（`trpg-char/13`）、`SAVE_FORMAT`（`trpg-run/13`）**沒升**：新欄位沒值時不輸出，舊檔逐字照讀（待 PM 決定 1）。
- `WORLD_RULES_VERSION` 沒升：舊日誌沒有文字，重播結果逐字相同（`tests/world/test_flash_texts_world_lf1.py::test_old_log_without_texts_replays_with_template_names`）。
- 技能 ID：歷程雜湊本來就包含整筆變化，有文字時 ID 不同；沒有文字時不變（slow 的 `test_refactor_parity.py` 全過，沒有重產夾具）。

## 3. 本機 LLM 冒煙（手動 2 題，唯讀）

`localhost:8001` 沒有回應；改用調查報告的 LM Studio（`100.87.188.89:1234`、`swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp`、`reasoning_effort = "none"`；設定在 worktree 的 `config/llm.local.toml`，gitignored、沒有 commit）。火焰箭、2 階、雲嶺、長劍，同一條遊戲路徑（`LlmFlashSource(client, naming=client)` → `make_offer`）：

- 第 1 次（小變化），5.0 秒，`partial`（三次嘗試都有一項 `flash.note_zh.missing_added`）：
  - 多打一下：火焰箭｜「如竹葉連擊，造成多段火焰傷害與燃燒。」
  - 延長：火焰箭｜「火光在石壁上延燒，持續時間增加一回合。」
  - 輕巧：火焰箭｜「動作輕巧如鶴舞，消耗減少，威力略降。」
  - 蓄力（模板補位）：火焰箭｜沒有描述
- 第 3 次（大變化），8.9 秒（含 4 次命名），`llm`：
  - 加深：**竹影焚心**｜「山霧鎖住熱氣，點燃的狀態多持續一回合。」
  - 換形：**雲嶺燎原**｜「火焰化作竹枝狀散射，一次命中更多目標。」
  - 轉型（姿態）：**赤焰立姿**｜「以長劍為引，將火焰頻率凝於自身，進入持續燃燒的架勢。」（命名的 `concept` 當描述）
  - 橋接：**鶴唳驚雷**｜「雲氣匯聚，命中時賦予目標帶電狀態。」

沒有開 `trpg serve`，沒有占用任何埠。

## 4. 測試與檢查（結束碼）

| 指令 | 結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1557 個檔） |
| `uv run lint-imports` | 0（14 kept） |
| `pytest -n 8` 相關 25 檔（`tests/llm` 全部、閃現相關的 roguelite／world／api／skillgen、`test_architecture.py`、`test_no_design_numbers_txt1.py`） | 0（678 passed） |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/roguelite/test_flash_llm_run.py tests/llm/test_flash_propose.py` | 0（897 passed） |
| `pytest -n 8 tests/cli/test_run_cli.py tests/cli/test_llm_propose_cli.py` | 0（20 passed） |
| `trpg battle --map open_plain --seed 7 --log-json …`＋`trpg battle replay` | 0／0（91 個動作、383 個事件，一致） |

新測試：`tests/skillgen/test_flash_text_lf1.py`（14：文字檢查、上限和 LLM 端一致、沒有文字時逐字不變、名稱留過重推／升階／下一次閃現、手改存檔的壞名稱被忽略）、`tests/llm/test_flash_texts_lf1.py`（4：描述收進紀錄、大變化與轉型命名＋紀錄往返後重播相同、沒有文字時 JSON 不變、模型連不上不命名）、`tests/world/test_flash_texts_world_lf1.py`（2：大變化命名與描述記進 `/10` 日誌、`replay` 裝會報錯的供應者仍逐字相同；`/9` 舊日誌照讀）、`tests/roguelite/test_flash_texts_run_lf1.py`（1：描述進選項、`flash_llm_log`、存檔往返、選了之後存進歷程）。

快照與夾具：預測不會變（Mock 預設不命名、Mock 提議沒有描述、文字欄位空值不輸出）；實際沒有任何快照或夾具失敗，沒有重產。

## 5. 待 PM 決定

1. **角色與一輪存檔的版號**：照「只多選填欄位、沒值不輸出」不升（`trpg-char/13`、`trpg-run/13`）。新檔帶文字時舊程式讀不了；要比照 6L-2 升版的話 LF-2 順手改（世界日誌已升 `/10`）。
2. **`LOG_FORMAT` 沒升**：戰鬥紀錄格式沒變。
3. **命名的敘事**（`concept`、`cast_flavor`）沒有寫進技能的 `narrative`：只取名稱；描述用提議的 `note_zh`，沒有時才用 `concept`（≤ 40 字）。要寫進敘事得把兩段文字也存進歷程。
4. **名稱只擋「和內容庫、同一題」重名**，不擋和玩家自己其他技能重名（請求沒帶玩家的技能名稱）。
5. **命名延遲**：大變化題目多 3～4 次命名呼叫（本機實測整題 8.9 秒），大世界預先生成來不及時整題退回模板。LF-2 第 7 點把命名併進提議呼叫後應改善。
6. **Mock 命名的種子改成依選項分流**（`name_texts` 新寫的；舊的 `name_offer` 只給評估工具用，沒改）。
7. `make_offer` 的內部順序改成「先提議、再文字、再轉型保底」：結果不變（parity 全過），但之後改這段的人要知道。

## 6. 需要使用者決定

1. **小變化要不要也改名**（設計 6.34.3「小變化不改名稱」）。LF-1 照設計只給小變化一句描述。

## 7. 平衡疑慮

無（只換文字，結構與數值不動；名稱與描述不進預算）。

## 8. 沒驗證

- 前端顯示（LF-3）：名稱會經技能卡的 `name_zh` 出現，描述目前 API 沒有欄位、玩家看不到。
- 大世界實機（`trpg serve`＋預先生成＋10 秒等待）沒有用真模型跑；只用 Mock 驗證日誌與重播，真模型只跑了 `make_offer` 那一層。

## 開發 PM 裁定

- 接受，已合併。規格 `PhaseLF計畫.md` 的三段切法照用：LF-2 減少不合格重問、LF-3 API 與前端（等 FL-1b 合併後）。
- 待 PM 決定 1～6：全部照保守做法維持。
  - 存檔不升版。新欄位沒值時不輸出，存檔可刪，不寫遷移。
  - LOG_FORMAT 不升。
  - 名稱只擋和內容庫撞名、同一題內撞名。
  - 大變化多出來的命名呼叫，由 LF-2 併進提議呼叫解決。
- 「小變化要不要改名」：設計 6.34.3 已定「小變化不改名稱」，照設計，不另外問使用者。
- 工作量提醒：這個 agent 已用約 34 萬 token，已過「同一塊的後續交回原 agent」的上限，LF-2 改派新 agent。
