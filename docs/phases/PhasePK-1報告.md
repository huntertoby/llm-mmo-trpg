# Phase PK-1 報告：挑選模式第 1 段（挑選核心）＋比較

> 2026-11-15，實作者（PK-1）。規格：`docs/phases/技能生成-挑選模式提案.md` 第 7 節（第 7.1～7.6 節）；使用者決定（專案 PM 轉）：第 6 節 5 題全選 A，「做出來後 來你來去做裁判 看紙面數據 哪個看起來比較好 比較有趣跟全面」。
> 給裁判的並排樣本與指標：`docs/phases/PhasePK-1比較.md`；原始資料：`docs/phases/PK-1資料/`。

## 1. 改了什麼

| 檔案 | 內容 |
|---|---|
| `content/skill_pick.yaml`、`src/trpg/content/skill_pick.py` | 新表 `SkillPickRules`：候選池（`pool.seeds` 60、`pool.designs` 16、`pool.top_k` 5、`pool.min_for_llm` 2）與打分權重（協同每條 300、上限 3 條；打法每次 20、上限 400；屬性路線主 200／雙 100；手寫加分 0；多樣性扣分：同骨架 150、同形狀 100、同效果種類 250、同元素 60）。全部是原型預設值，等使用者在數值工坊調 |
| `src/trpg/content/registry.py`、`library/load.py`、`library/container.py` | 登記新表、`ContentLibrary.skill_pick`（不進規則包；同 `skill_icon_art.yaml` 的掛法） |
| `content/tuning_fields.yaml`、`src/trpg/content/tuning_fields.py`、`src/trpg/api/tuning/objects.py` | 數值工坊新對象種類 `pick`（全體共用的表，分類 `rules`，和核心規則、預算表放同一個分頁）；15 個欄位全開，中文標籤與說明 |
| `client/src/api/client.ts`、`client/src/screens/TuningScreen.tsx` | 工坊畫面多抓 `tuningObjects("pick")`（讀不到就略過，同其他表） |
| `src/trpg/skillgen/skill_pick.py`（新） | 候選池 `candidate_pool`、設計鍵 `design_key`／`design_label`（定義同 `scripts/recipe_census.py`）、打分 `score_candidate`、排序 `rank_candidates`、`pick_slate`。純函式、確定性 |
| `src/trpg/skillgen/pick_player.py`（新） | `PickPlayer`：打分用的玩家狀態摘要（手上技能、行為紀錄、屬性、武器屬性） |
| `src/trpg/skillgen/proposal_fallback.py` | `_fits` 改成公開的 `fits_request`（候選池共用）；`fallback_skill(skip_composer=)`（預設 `False`＝原行為） |
| `src/trpg/llm/prompts/pick.py`（新） | `PICK_PROMPT_VERSION = "skill-pick/1"`、`build_pick_messages`、`pick_schema`（`pick` 是 `enum [0..K-1]`，名稱與兩段文字的長度同命名 schema） |
| `src/trpg/llm/pick.py`（新） | `pick_skill`（一次呼叫挑選＋命名、重試、退回）、`make_pick_proposer`（`LlmProposer` 介面）、`mock_pick_client`（Mock 挑選器）、`candidate_card` |
| `src/trpg/skillgen/proposal_topic.py`（`LlmAttempt`）、`skillgen/candidates.py`（`LlmTrace`、`from_llm`）、`roguelite/state.py`（`LlmRecord`）、`roguelite/offers.py`（`_tag`） | 紀錄加四欄：`pick_seeds`（前 K 個候選的組合器種子）、`pick_designs`（前 K 的設計鍵）、`pick_index`（LLM 選的 index）、`pick_reason`（退回原因）。`LlmRecord` 的四欄空值 `exclude_if` 不寫出 |
| `scripts/pick_compare.py`（新） | 比較腳本：`run`（真模型或 `--mock`）、`report`（從 JSON 重產 markdown，保留手寫摘要） |
| 測試 | `tests/skillgen/test_skill_pick_pk1.py`（10 項）、`tests/llm/test_pick_pk1.py`（15 項）；`tests/test_architecture.py` 允許清單加 `pick_skill`（避免撞名要比對全部內建技能名，同 `name_skill`）；`tests/api/tuning/test_rules_budget_bs1.py` 的 `TABLE_KINDS` 多 `pick` |

## 2. 開關

**這段沒有接上任何出題流程，所以沒有開關**；現行三選一、閃現、機遇、許願池、`trpg run`、大世界全部照舊（自由設計與組合器的程式一行沒刪）。

- 理由：原型的升級三選一是白板產生器（`whiteboard_candidates`），**本來就不呼叫 LLM**（`offers._compute_offer`：「白板三選一……LLM 來源關閉」）；LLM 只在「完整技能三選一」那條（`generate_candidates` 的 `from_llm`）。把挑選接進白板要另開 LLM 來源，接進完整技能則屬提案第 3 段，都超出這段「最小可比版本」，所以照最保守的做法不接。
- 之後要接時：`trpg.llm.pick.make_pick_proposer` 和現行 `make_proposer` 是同一個介面（`LlmProposer`），回傳的 `LlmAttempt` 已帶四個挑選欄位，`from_llm` → `LlmTrace` → `LlmRecord` 的資料路徑已接好；只要在 `api/llm_source.py`、`cli/run_llm.py` 依設定（建議 `LLMConfig.skill_mode`，環境變數 `TRPG_LLM_SKILL_MODE`，預設 `free`）換提議器即可。打分要的玩家資料（手上技能、行為紀錄）目前 `LlmProposer` 拿不到，見第 6 節待決 2。

## 3. 實量結果（Gemma，摘要；全文見 `PhasePK-1比較.md`）

- 量測前檢查：`/api/v0/models` 的 `state=loaded` 只有 `google/gemma-4-26b-a4b-qat`；生成速度 220 t/s（門檻 60）。沒有換模型、沒有改 `config/llm.toml`，跑完照舊是 Gemma 載入。
- 24 題（LB 20 題＋4 題），兩條路各一次，總共約 2 分鐘。
- 第一次實跑後發現候選卡片沒有列被動、反應技的觸發時機，補上卡片的 `timing` 後整組重跑。只動卡片資料，系統指令不變，所以版本號維持 `skill-pick/1`。比較文件用的是重跑的那次。

| | 自由設計 | 挑選模式 |
|---|---|---|
| 退回 | 4/24（第一次實跑 7/24） | 0/24 |
| 每題秒數 中位／最慢 | 2.9／5.5 | 1.1／5.1（組合器 CPU 中位 0.3、最慢 4.4；LLM 中位 0.7、最慢 1.6） |
| LLM 呼叫 | 提議 1～3 次＋命名 1 次 | 1 次（21 題）／2 次（3 題） |
| prompt token 中位 | 1,356（每次提議） | 2,063（K=5） |
| 輸出 token 中位 | — | 81 |
| 不同設計／效果原語／骨架 | 21／10／9 | 23／10／9 |
| 題目關鍵字帶齊 | 14/14 | 14/14 |

挑選模式另有幾個觀察：

- LLM 挑的 index：0 號 12 次、1 號 6 次、2 號 3 次、3 號 1 次、4 號 2 次。
- 挑到手寫技能 6/24：手寫技能在候選裡只占 18/120 張，挑中的保留原本的名稱與敘事。
- 元素偏少：沒有元素的有 14/24，自由設計是 7/24。

## 4. 快照與相容性（逐鍵）

- 先預測：這段沒有接任何出題流程，Mock、一輪、大世界、CLI 的輸出都不會變；新的內容檔只會改 `ruleset_hash(library)`、`content_digest`，規則包雜湊不變。
- CLI 快照（`tests/cli` `-m slow`）：44 passed，**沒有任何鍵變動、沒有重產**。
- 存檔：`LlmRecord` 新的四欄空值不寫出（`tests/llm/test_pick_pk1.py::test_records_without_pick_mode_serialize_as_before`），沒有挑選模式的存檔逐字不變。
- 戰鬥不變比對：照 LB-2 報告第八節，改前用 `git archive main src content` 的副本，8 張圖 × 種子 1、2，加 3 張頭目圖 × 種子 3～12，比對去掉規則包的整份紀錄。結果 **`battles=46 events=20458 different=0`**。腳本在暫存區，不進 repo。
- 改到的既有測試只有兩處：
  - `tests/api/tuning/test_rules_budget_bs1.py`：`TABLE_KINDS` 多 `pick`。
  - `tests/test_architecture.py`：允許清單多 `pick_skill`（避免撞名，同 `name_skill`）。
- 內容檔數多 1 個（`skill_pick.yaml`）；`tests/content` 全過。
- 前端：數值工坊畫面多抓一張表，沒有新元件；`openapi.json` 沒有變（`kind` 參數是字串）。

## 5. 測試

- 新增 `tests/skillgen/test_skill_pick_pk1.py`（12 項）：
  - 預設值、設計鍵定義。
  - 候選池每個都過 `validate_skill`、符合題目，設計鍵兩兩不同；湊滿設計數就停。
  - 同種子同結果（固定 3 個種子）。
  - 協同、打法、屬性路線各自加分，打分不看強弱。
  - 多樣性扣分與同分順序；改工坊權重後排序跟著變；預設權重的排序快照。
- 新增 `tests/llm/test_pick_pk1.py`（15 項）：
  - Mock 挑 0 號、2 號時，結構與數值不變。
  - 壞 JSON、index 超範圍、名稱過長、多餘欄位都退回第一名＋組合式名稱，最多 3 次呼叫。
  - 重試會帶 `<errors>`。
  - 連不上模型立刻退回；逾時算一次嘗試。
  - 候選太少不呼叫 LLM；候選池空的退回技能池或工坊。
  - schema 形狀與大小。
  - `skill-pick/1` 的 prompt 快照（照現行做法：只加鍵）。
  - 資料區有跳脫。
  - 提議器會填好四個紀錄欄位；`LlmRecord` 序列化來回一致。
- 執行結果：
  - `ruff check`、`ruff format --check`、`uv run mypy`（1641 檔）、`lint-imports`（14 kept）都通過。
  - `tests/content`＋`tests/api/tuning`＋`tests/test_architecture.py`：3328 passed。
  - `tests/llm` 單獨 `-n 8`：460 passed（3 分 47 秒）。
  - `tests/skillgen` 單獨 `-n 8`：4405 passed、14 skipped（6 分 58 秒）。
  - 相關檔逐檔單獨跑（`test_llm_source` 79 秒、`test_upgrade_topup` 243 秒，其餘都在 10 秒內）都過。
  - `tests/cli -m slow` 44 passed；`tests/sim -m slow` 見第 7 節。
- 開發中出事的一次：`tests/llm`＋`tests/skillgen` 合併成一批 `-n 8` 跑了 2 小時沒結束（xdist worker 重啟 3 次），開發 PM 通知後才停掉。之後逐檔跑、兩個資料夾各自 `-n 8` 跑，都在 7 分鐘內正常結束，沒有重現。當時新檔用 hypothesis 每例跑兩次候選池，已改成固定 3 個種子。合併批次為什麼讓 worker 重啟，沒有查到確切原因（記憶體或單一長測試都有可能）。

## 6. 待 PM 決定

1. **手寫技能進不進候選池**：提案 7.6 說「可以一起進」，這段讓它們進來，挑中時保留原本的名稱與敘事，因為改名會和內容庫同 ID 的技能衝突。實量 6/24 挑到手寫技能，等於「拿到既有的招」。可選：A 照現狀；B 只在組合器候選少於 `min_for_llm` 時才放手寫技能；C 工坊加權重 `pool_bonus` 調負（現在 schema 下限是 0，要改 schema）。
2. **接進遊戲時玩家資料怎麼傳**：打分要的手上技能、行為紀錄，現在的 `LlmProposer`（題目, 上下文, 種子）拿不到。接上一輪時要在 `CandidateRequest` 帶手上技能，並把它排除在 `_request_key` 之外，以免影響快取鍵。這段沒做。
3. **元素偏少**：組合器的候選多半沒有元素，挑選模式產出的技能物理居多（14/24）。要不要在打分加一項「元素多樣性／玩家常用元素」，或讓組合器多抽元素版本？這屬於數值與規則類，先記下。
4. **同骨架題目的候選只差元素和數字**（例：蓄力與終結、刻印）：多樣性扣分管不到骨架被題目固定的情況，這是組合器配方範圍的問題（提案第 5 節缺點 2）。
5. **白板三選一接不接挑選**：原型升級的白板本來就不呼叫 LLM。照提案要接的話，要新增 LLM 來源與開關，算新的一段。
6. **權重全是實作者的保守初值**（`content/skill_pick.yaml`），等使用者在數值工坊調。

## 7. 交件前檢查

- `tests/sim -m slow`：19 passed（2 分 45 秒）。`tests/cli -m slow`：44 passed。
- 前端兩處小改（型別多 `"pick"`、多抓一張表）**沒有跑 `tsc`／vitest**：這個 worktree 沒有 `client/node_modules`，沒有另外安裝。請 PM 合併後在主資料夾順手跑一次。
- 自己啟動的背景程序都已結束；沒有跑 `scripts/check.py`、沒有平衡量測與戰鬥模擬（不變比對以外）。

## 開發 PM 裁定（2026-11-15）

- **驗收通過，合併。** 沒有接上任何出題流程，現行遊戲完全不變，所以不需要開關。自由設計的程式沒刪。驗證和規則都沒放寬。改了兩個既有測試：數值工坊的表多一種 `pick`；架構允許清單加一條（挑選要比對內建技能名，避免撞名，和命名步驟同理）。CLI 快照不變，戰鬥 46 場 different=0。OpenAPI 重產後沒有差異。
- 卡住的原因（tests/llm 和 tests/skillgen 合併成一批 `-n 8` 時 worker 會重啟）沒有查到確切原因；分開跑都正常。之後 agent 照「分目錄跑」的做法。
- 比較文件 `PhasePK-1比較.md` 交給專案 PM 當裁判。待決 1（手寫技能要不要進候選池）、3（元素偏少）、4（骨架固定時候選只差元素和數字）屬於裁判和玩法的判斷，跟裁判結果一起回來再排。
- 待決 2（接進一輪時，玩家手上的技能和行為紀錄怎麼傳進提議器）：技術問題，裁判決定要接時，併進接入的那一段。
- 待決 5（白板三選一要不要另開一段接挑選）：等裁判結果。
- 待決 6：權重是保守初值，由使用者在數值工坊調。
- 補記（全量）：pytest 17798 passed、vitest 4676、build 0。mypy 擋下 `tests/llm/test_pick_pk1.py` 一處回傳 Any；開發 PM 改成 `bool(...)` 後，mypy、ruff、format 和整個 tests/llm（460 passed）都重跑過，結束碼都是 0。
