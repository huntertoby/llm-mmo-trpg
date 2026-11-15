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
