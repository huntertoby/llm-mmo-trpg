# Phase 4-L4 報告｜提議 schema 子集

> 規格：`docs/phases/Phase4計畫.md` 3A 節。實作者撰寫。

## 1. 做了什麼

| 項目 | 內容 |
|---|---|
| 題目與篩選 | 新模組 `src/trpg/skillgen/proposal_subset.py`：`ProposalRequest`、`select_subset`、`ProposalSubset`、`SubsetError`、`build_subset_models`、`available_payload`、`subset_tokens`、`json_tokens`。純函式、確定性，欄位一律排序後的 tuple。 |
| 模型篩選 | `build_proposal_models` 新增 keyword 參數 `shapes`、`conditions`、`triggers`、`skeletons`（`None`＝全部，既有呼叫不變，有測試比對）。篩掉的形狀／條件／觸發 → `union_tag_invalid`，骨架 → `literal_error`，`allowed` 只列子集。條件（觸發）全篩掉時提議沒有 `condition`（`trigger`）欄位；`kind` 也只留所選骨架適用的種類。 |
| prompt 組裝 | `src/trpg/llm/prompts/proposal.py`：`build_proposal_prompt(library, request, *, player_text, previous_proposal, errors, world) -> ProposalPrompt(messages, json_schema, models, subset)`，另有 `ProposalPrompt.tokens`、`estimate_messages_tokens`。 |
| token 估算 | `src/trpg/shared/tokens.py`：`estimate_tokens`（ASCII ÷ 3 ＋ 非 ASCII × 1，向上取整）與 `PROMPT_TOKEN_BUDGET = 30_000`；`trpg.llm.prompts` 重新匯出同一份（見待決 #1）。 |
| 世界觀登記 | `WorldStyle` 等模型移到 `src/trpg/content/world.py`（成為 `ContentModel`），`content/registry.py` 登記 `llm/world_shattered.yaml`（`trpg content check` 會驗）；`trpg/llm/prompts/world.py` 留作重新匯出，既有匯入不變。 |
| 依賴規則 | `pyproject.toml` import-linter 新增「skillgen 不得匯入 llm」，`tests/test_architecture.py` 同步（`lint-imports` 7 個契約全過）。 |
| 提示文字 | 骨架的 `description_zh` 經測試確認不含欄位名與階段編號，**不需要**補 `llm_hint`；`PROMPT_VERSION` 沒有升（系統指令、區塊格式、世界觀內容都沒改，只是資料區多了內容；快照測試通過）。 |

### 公開 API 摘要

- `ProposalRequest(tier, rarity, kind=None, skeleton=None, keywords=())`：`tier < 1`、種類不開放、關鍵字 > 2 或重複 → `ValueError`；未知骨架／關鍵字 ID 在 `select_subset` 丟 `ValueError`（中文訊息）。`kind` 省略時依骨架，兩者都省略為 `active`。
- `select_subset(library, request, *, token_budget=DEFAULT_SUBSET_TOKEN_BUDGET) -> ProposalSubset`。`DEFAULT_SUBSET_TOKEN_BUDGET = 30_000 − 6_000`；`build_proposal_prompt` 用「30k − 實際系統指令 − `USER_RESERVE_TOKENS`（5_000）」。
- `ProposalSubset`：`kind`、`skeletons`、`primitives`、`shapes`、`conditions`、`triggers`、`keywords`、`dropped`（ID、中文原因）、`tokens`（schema ＋ available 的估算）。
- `available_payload(library, subset)`：`{skeletons, primitives(含 params), shapes, conditions, triggers, keywords}`，依 ID 排序，`hint` 取 `llm_hint`（骨架、關鍵字用 `description_zh`），數值參數與範圍不列。

### 篩選細節

1. 骨架：指定者必須 `enabled`、非 `reaction`／`modifier`／`trap`、適用該種類，否則 `SubsetError`；未指定時取全部符合者。再逐一檢查是否可用（稀有度、有核心原語、有形狀、`requires_condition` 需有條件、被動需有觸發），不可用的記進 `dropped`。沒有任何可用骨架 → `SubsetError`。
2. 原語：核心 ∪（有附帶名額者的）附帶原語；附帶原語省略＝不限時取全部、`harmful_only` 只留有害；`require_any_primitives` 視為核心。稀有度不夠的去掉。核心原語的必填巢狀參數（`then`、`effects`）所需的原語（`damage`／`heal`／`shield`／`apply_status`）一併視為核心，否則 `consume_status` 等骨架無法表達。
3. 形狀 ⊆ 骨架 `shapes`（依稀有度）；條件依稀有度；觸發只給被動，依稀有度。
4. 關鍵字：只看專屬規則（`grade` 省略）的 `effect`／`condition`／`trigger`／`shape` 來源；通過骨架與稀有度的優先收，過不了的記進 `dropped`。
5. 補足：優先收的、再依 YAML 順序補其他合法原語（二分搜尋最大可放入數量），剩餘預算再補條件（等於先砍條件、再砍附帶原語）；大小用 schema ＋ available 的 JSON 估算。最後以模型建構結果為準（排除掉建構時被排除的原語並記進 `dropped`）。

## 2. 大小統計

固定抽樣矩陣：4 個稀有度 × （不指定骨架＋12 個可用骨架）× 0／1／2 個關鍵字（關鍵字依索引固定輪流取）＝ 168 組，**138 組可行、30 組不可行**（骨架在該稀有度不可用，`SubsetError`）。數字為 `ProposalPrompt.tokens`（system ＋ user ＋ schema，不含玩家文字與重試回饋）：

| 稀有度 | 可行組數 | 最大 | 平均 |
|---|---|---|---|
| common | 15 | 5,227 | 4,222 |
| rare | 39 | 24,999 | 18,010 |
| epic | 42 | 24,868 | 18,035 |
| legendary | 42 | 24,769 | 18,078 |
| **全部** | **138** | **24,999**（rare／aura／2 個關鍵字） | **16,540**（最小 3,283） |

測試矩陣（`tests/llm/test_proposal_prompt.py::test_prompt_size_matrix`）另外塞滿玩家文字（500 字）、較大的上一次提議與錯誤回饋，每組估算仍 ≤ 30,000。未篩選的完整 schema 約 5 萬 token（144,786 字元，其中 2,712 個非 ASCII），所以必須篩選。

## 3. `dropped` 常見原因（上述矩陣，共 1,085 筆）

| 次數 | 原因 |
|---|---|
| 648 | 超過大小上限，未收入（補足階段砍掉的原語與條件；主要是 `rare` 以上的條件與少用的附帶原語） |
| 331 | 骨架範圍外或稀有度不足，不收（關鍵字專屬原語不在所選骨架範圍內） |
| 58 | 此題目不收觸發或稀有度不足（關鍵字的觸發規則，但技能不是被動） |
| 27 | 稀有度不足，不收（關鍵字的條件） |
| 12 / 6 / 3 | 骨架被排除：稀有度不足／沒有足夠稀有度的核心原語／需要條件但此稀有度沒有條件 |
| 3 | 關鍵字的形狀不在骨架範圍或稀有度不足 |

`SubsetError` 的原因：骨架稀有度不足（21）、核心原語稀有度不足（6，`common` 的 `displace`、`summon`）、需要條件但普通沒有條件（3，`combo`）。

## 4. 測試與檢查

`tests/llm`、`tests/skillgen/test_proposal.py`、`tests/skillgen/test_proposal_subset.py`、`tests/test_architecture.py`、`tests/content`、`tests/cli` 全過（1,021＋114）；`ruff check`、`ruff format --check`、`mypy`（598 檔）、`lint-imports` 全過。未跑完整 `scripts/check.py`，也沒有改引擎，未另跑重播。新增測試：

- `tests/skillgen/test_proposal_subset.py`（36）：模型篩選與錯誤碼／`allowed`、題目驗證、稀有度、骨架範圍、關鍵字（10 個關鍵字逐一的表格測試）、確定性（位元組相同）、往返（10 個手寫技能經子集模型仍通過提議與轉換階段）、`available` 格式、所有 hint 不含欄位名與階段編號。
- `tests/llm/test_proposal_prompt.py`：估算與常數、prompt 結構、重試不改子集、玩家文字隔離、大小矩陣（4 個稀有度共 ≥ 114 組可行）、世界觀登記。

## 5. `# noqa` 清單

無。

## 6. 待 PM 決定

1. **`estimate_tokens` 與 `PROMPT_TOKEN_BUDGET` 放在 `trpg.shared.tokens`**（規格寫「`trpg.llm.prompts` 加」與「skillgen 自己定義同值常數」）：改放 `shared`，兩邊匯入同一份，不可能不一致；`trpg.llm.prompts` 照規格匯出同名。若要照字面各自定義請告知。
2. **關鍵字優先收的原語不是「永不砍」**：規格寫必收永不砍，但關鍵字（如 `ignite`）的專屬原語可多達 10 個，加上核心會超過上限，因此改為「核心永不砍、關鍵字的排在補足清單最前面、最後才砍」；核心本身放不下才丟 `SubsetError`。
3. **補足階段會填滿預算**（約 24k）：`rare` 以上多數題目的 prompt 在 1.8 萬～2.5 萬 token。是否太長影響小模型品質，待 4-L9 真實模型評估後再決定是否改成較小的目標值（`token_budget` 是參數，容易調）。
4. **大小估算的 schema 用 `ensure_ascii=False` 的緊湊 JSON**（規格寫 `json.dumps(schema)`，預設會把中文轉成 `\uXXXX`，估算會大很多）；估算本身是保守的啟發式，真實 tokenizer 的數字要等 4-L9 對照。
5. **附帶原語「省略 `primitives`＝不限」的骨架**（`combo`、`consume_status`、`passive`、`stance`、`summon`、`sacrifice`）在 rare 以上會把幾乎所有原語列為候選，實際收多少由預算決定；這些骨架的 `secondary.max_count` 多為 0～1，大部分候選其實用不上。若要縮小可在骨架 YAML 補 `secondary.primitives` 清單（內容調整，不是這段範圍）。
6. **`consume_status`／`zone` 等核心需要巢狀原語的骨架**，子集會帶進 `damage`／`heal`／`shield`／`apply_status` 作為頂層效果選項，即使該骨架不允許那些附帶效果（會在驗證階段被 `skeleton.secondary` 擋下）。要完全避免需要提議模型把巢狀與頂層可用原語分開，留給 4-L5 以後。
7. **`kind` 欄位隨所選骨架收斂**（規格只列骨架、形狀、條件、觸發四個 union）：為了避免未指定被動骨架時模型仍開放 `trigger` 之外的種類，我讓 `kind` 的 `Literal` 只含所選骨架適用的種類；未指定骨架時行為與之前相同。
8. **`ProposalRequest` 的 `kind` 與骨架矛盾、骨架不開放（`reaction`／`modifier`／`trap`）時丟 `SubsetError` 而非 `ValueError`**：這些是「這題沒有可用結構」，4-L5 可統一退回組合器；只有未知 ID 丟 `ValueError`。
9. **形狀與稀有度**：沿用 YAML 的 `min_rarity`；部分形狀（如 `unit_then_tile`、`object_then_tile`）註解標明「只給手寫技能」但沒有資料欄位區分，目前會出現在子集裡。若要排除需在形狀 YAML 加旗標。
