# Phase 4-L5c 報告（第二次小測試後的小修）

規格：`docs/phases/Phase4計畫.md` 3E 節第 1～5 點。實作者：sonnet。全部測試用 `MockLLMClient`，未呼叫真模型。

## 做了什麼

1. **只能填 true 的開關**：`PrimitiveParam` 加 `true_only: bool`（`content/skill_primitives.yaml` 的 `damage.explode`、`damage.split_heal` 標 `true_only: true`）。
   - 提議模型：`type: bool` 且 `true_only` 的參數為 `Literal[True]`（schema `const: true`，可省略）。
   - 驗證器：`SkillDef._check_true_only` 讀 `true_only_params()`（同一份 YAML，不寫死），填 `false` 擋下，代碼 `flag.true_only`。
   - 清理：`trpg.llm.response.drop_false_flags` 把這些開關的 `false` 視為省略（雙保險），`propose_skill` 在 `clean_response` 之後呼叫。
2. **列舉只放技能能用的 ID**：`budget_basis: status` 的原語（`apply_status`，含巢狀位置）其 `status` 參數只列有 `budget_points` 的狀態（規則與 `budget.unavailable` 相同）；與 4-L5b 的稀有度篩選取交集。新函式 `budget_statuses(library)`。
3. **token 估算不算 schema**：`subset_tokens` 只算 `available`；`ProposalPrompt.tokens` 只算訊息；`select_subset` 的補足以 `available` 為準。新增 `SCHEMA_CHAR_LIMIT`、`json_chars`、`ProposalPrompt.schema_chars`，`build_proposal_prompt` 超過上限丟 `SubsetError`。
4. **專屬錯誤代碼**：`SkillRuleError` 加 `code`；`_pydantic_errors` 對 `stage: skill` 優先用它。
5. **CLI 不出不可能的題目**：`propose_requests` 對輪替出的題目檢查 `_feasible`（`select_subset` 不丟 `SubsetError` 且 `fallback_skill` 至少一層做得出），不可行就依種子換下一組（`llm.propose.{i}.{attempt}` 分支，最多 12 組，第 0 組與舊輸出相同）。稀有度、骨架、關鍵字都由參數指定的題目照跑。

## 開關清單與推導方式

- 清單 ＝ YAML 參數 `true_only: true`：目前 `damage.explode`、`damage.split_heal`（測試確認等於 YAML 推導，且都是 `type: bool`）。新增這類開關只需在 YAML 標記。
- `modifier` 的 `change.*` 只能是 true 另有檢查，不在提議範圍，未動。

## 被排除的狀態（無 `budget_points`，不能由技能施加）

`armor_broken`、`charging`、`revealed`、`shielded`、`soul_link`、`time_bomb`、`undying`（清單由資料推導，不寫死）。

## schema 字元上限與現況

- `SCHEMA_CHAR_LIMIT = 125_000`（`trpg.skillgen.proposal_subset`；現況最大值 61,994 × 2，取整）。
- 大小矩陣（稀有度 × 骨架（含不指定）× 0/1/2 關鍵字，138 組可行）：schema 最大 61,994、平均 24,355 字元；訊息 token 估算最大 6,540、平均 2,640（上限 30,000）。
- 影響：schema 不再占 token 預算，`select_subset` 對多數題目不再裁掉附帶原語／條件（相同題目的 `available` 比 4-L5b 長）。

## 新錯誤代碼表（`stage: skill`）

| 代碼 | 來源 | path |
|---|---|---|
| `combo.position` | 原語要求第一個／最後一個效果 | `effects[i]` |
| `combo.sole_effect` | 原語必須是唯一效果 | `effects` |
| `combo.others_affect` | 其他效果必須 `affects: self` | `effects[i].affects` |
| `combo.max_per_skill` | 每技能數量上限（含「最多一個改變自身位置」群組規則） | `effects[i]`／`effects` |
| `combo.active_only` | 只能用在主動技能 | `kind` |
| `flag.true_only` | 只能填 true 的開關填了 false | `effects[i].<開關名>` |

其他驗證器維持 `value_error`。

## noqa

無新增。

## 測試

- 新增 `tests/skillgen/test_proposal_l5c.py`（開關、狀態列舉、各 `combo.*` 代碼，皆由 YAML 規則參數化）、`tests/llm/test_l5c.py`（`drop_false_flags`、迴圈接受 `false`、token／schema 上限）、`tests/cli/test_llm_propose_cli.py` 兩個輪替可行性測試。
- 更新：`test_proposal_subset.py`（預算數值改為 available 的量級）、`test_proposal_prompt.py`、`test_proposal.py`（狀態列舉）、CLI 快照 `llm_propose_mock.txt`（第 3 題錯誤由 `literal_error` 變 `value_error`：schema 更完整，提議過了格式層，卡在 `variants[1]` 空替換）。
- 跑過：`tests/content`、`skillgen`、`llm`、`cli`、`test_architecture`（2041 全過，修正狀態列舉測試後該檔 21 過）、`tests/engine` 2544 過、ruff、format、mypy、lint-imports 7 契約、`swamp` 種子 60 重播一致。
- `proposal_from_skill` 往返數沒有下降（既有往返下限測試全過）。
- `PROMPT_VERSION` 未升：系統指令與區塊格式沒改（快照雜湊不變）；只是同題目的 `available` 變長（因為 schema 不再占預算）。

## 待 PM 決定

1. `PROMPT_VERSION` 沒升（模板未變、只是 `available` 內容較完整）；若要把「available 內容變了」也算版本變動，需升號並加快照。
2. 預算現在只管 `available`＋固定 prompt，題目的附帶原語與條件多數會全收（訊息最大約 6.5k token）；若想保留輪替／縮小選單（3C 第 2 點），那是 4-L6。
3. `SCHEMA_CHAR_LIMIT` 超過時丟 `SubsetError`（CLI 當作該題退回）；上限取現況最大值 ×2，之後原語增加可調。
4. 輪替可行性檢查會多跑一次 `fallback_skill`（結果丟棄），`trpg llm propose` 出題階段每題多幾秒；若嫌慢可只檢查 `select_subset`。
5. 第 1 點的 `false` 清理對所有 `true_only` 開關一視同仁、依 `type` 判斷；不在 `effects` 以外的位置（例如變奏的 `add_effect`）也會被遞迴處理（行為一致，無副作用）。
6. `combo.max_per_skill` 同時用在「每技能最多 N 個」與「最多一個改變自身位置」的群組規則（後者仍在程式裡，未搬進 YAML）。
