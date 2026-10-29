# Phase 4-L6 報告（LLM 接進候選產生器＋原語多樣性）

規格：`docs/phases/Phase4計畫.md` 3F 節、3C 節第 0～3 點。實作者：sonnet。全部測試用 `MockLLMClient`／假提議器，未呼叫真模型（8001 埠未碰）。已在 `3T-3`（`content/skills/` 套件）之後 merge main，無衝突；我沒有改 `content/skills`。

## 做了什麼

1. **`llm` 來源**（`skillgen/candidates.py`）：`generate_candidates(..., llm=None)`。有提議器時，每個候選種類（加深／橋接／新方向）以 `llm_share_permille` 的機率請 LLM 提議，**每種最多一次**；失敗（3 次重試後退回、技能不適用武器）就照原順序走組合器→技能池，候選仍湊滿 3 個。擲骰與出題用獨立 `fork("llm/<種類>")`，不消耗其他亂數；沒傳提議器或比例 0 ＝ 逐字相同（表格測試）。通用池的「新方向」不請 LLM。
2. **提議器掛接**：`skillgen` 與 `roguelite` 都不得匯入 `llm`，所以 `skillgen/proposal_topic.py` 定義 `LlmProposer`／`LlmAttempt`；真正呼叫模型的是 `llm/candidate_source.py`（`make_proposer`、`mock_proposer`、`mock_client_for`）；`roguelite/llm_hook.py` 用 `ContextVar` 裝上（`use_proposer`），`make_offer` 在 `run.llm` 為真且有提議器時才使用。
3. **關鍵字**：`ProposalContext.keywords` → 驗證器 `keyword.required`（走 `evaluate_proposal`，錯誤回饋給 LLM 重試）；`propose_skill` 自動把題目的關鍵字帶進 ctx。形態等 `composable: false` 關鍵字不出 LLM 題目（`make_topic` 回傳 None）；核心原語抽籤排除 `enter_form`／`leave_form`（`skill_composer.yaml` 的 `llm_topic.core_exclude`）。
4. **3C 0～3 全部完成**
   - 0 「自然」主題：`content/llm/world_shattered.yaml` 新增 `themes`（`nature`，毒素／大地／風／治療／藤蔓召喚物／荊棘牆），`WorldStyle.themes`；題目以 `llm_theme_permille`（100‰）帶 `theme`，只進 prompt 題目區塊（`system prompt` 未改，`PROMPT_VERSION` 不升）。不改元素表。
   - 1 `ProposalRequest.core_primitive`：`legal_core_primitives` 取合法骨架×稀有度的核心原語，`pick_core_primitive` 依權重抽；`select_subset` 只開放它當核心（骨架限於核心可用它的）；驗證器 `core.required`。抽不到合法組合就省略。
   - 2 輪替選單：`ProposalRequest.menu_seed`；附帶原語最多 6、條件最多 4（題目關鍵字要的必收），`available` 順序由種子打亂（`menu_order`）。
   - 3 run 內配額：`RunState.llm_uses`；權重 ＝ 基礎×100÷(100＋n×100)，表在 `content/skill_composer.yaml` 的 `llm_topic`（`base_weight`、`quota_percent_per_use`、`core_weights`）。計數＝每組候選各技能的效果原語（每技能每種算 1），在 `offers.offer_updates`。
5. **額外**：`ProposalContext/Request.weapon_class` → `weapon.incompatible`，並把 `weapon_class` 放進題目區塊。原先實測約一半 LLM 候選因武器不相容被丟掉（見待決 3 之外的驗證）；加了之後模型可在重試中修正。
6. **存檔 `trpg-run/8`**（舊 `/5～/7` 可讀）：`RunState.llm`、`llm_uses`、`llm_log`（`LlmRecord`：題目關鍵字、稀有度、核心原語、選單種子、主題、嘗試次數、代碼、成敗、原因）；`OfferTag.source` 多 `llm`，`OfferTag.llm` 存這個候選的紀錄。生成的 `SkillDef` 本來就隨候選節點與 `generated_skills` 存檔，重播與讀檔不呼叫 LLM（測試：重播前後呼叫次數不變）。
7. **退回率**：`trpg run` 的摘要與結果印「LLM 提議：N 題，成功／退回（x%），呼叫 M 次」，退回率 > `fallback_alert_permille` 加提醒（`run_llm.llm_lines`）。
8. **CLI／設定**：`trpg run new|auto --llm`（本機模型）／`--llm-mock`（Mock，CI 用）；`config/llm.toml` 新增 `generate`（預設 false；環境變數 `TRPG_LLM_GENERATE`）。`run new --llm` 把開關寫進存檔，`run auto --from` 沿用。
9. API：僅 `OfferTagOut.source` 加 `"llm"`，已重新匯出 `client/openapi.json` 與 `schema.d.ts`；前端未改。

初值：`roguelite.yaml candidates.llm_share_permille: 800`、`llm_theme_permille: 100`。

## 驗收

pytest（skillgen、roguelite、api、content、llm、architecture：4190 過；`-m "slow or not slow" tests/cli --timeout=3000`：154 過）、`ruff check`、`ruff format --check`、`mypy`（778 檔）、`lint-imports`（7 契約）全過。`trpg run auto --seed 3 --llm-mock` 跑完，兩次輸出一致（有 CLI 測試）。新增測試：`tests/skillgen/test_llm_source.py`（15）、`tests/roguelite/test_llm_run.py`（7）、`tests/cli/test_run_cli.py` 一個。

3C 測試：同種子同題目；1000 個種子下每個合法核心原語都被抽到、分布不超過平均 3 倍；配額讓已出現的原語機率下降；打亂不改變成員與 `evaluate_proposal` 結果；合格提議器 ＋ 1000‰ 時 LLM 來源占 ≥ 70%；壞 JSON／缺關鍵字／缺核心原語 → 重試後退回、候選仍 3 個；形態關鍵字不出題。

## 既有測試的調整

- `tests/cli/snapshots/llm_propose_mock.txt` 更新：Mock 現在依題目的關鍵字與核心原語挑手寫技能、並先檢查在該題下合格（原本不看關鍵字），因此挑出的技能不同；`trpg llm propose` 的輸出格式不變。
- `test_injected_client_and_fallback_lines` 改成用技能自己的關鍵字當題目（驗證器現在強制關鍵字）。
- 其餘 `trpg-run/7` → `/8` 的字串。

## noqa

無新增。

## 待 PM 決定

1. **`--llm-mock` 成功率受手寫內容限制**：Mock 只能回手寫技能的提議，題目（階級×稀有度×關鍵字）常沒有對應手寫技能，整輪實測多數退回（退回率常 > 20% 會提醒）。這是 Mock 的限制、不代表真模型；要更好看的 CI 數字需另寫 Mock，或接受。
2. **schema 的列舉順序沒有打亂**（3C 第 2 點寫「available 與 schema」）：schema 內順序固定為 YAML 順序（版型／union 建構處），只打亂了 `available`（模型實際讀的）。要連 schema 一起打亂需改 `proposal.py` 的建構器，且 schema 只拿來約束解碼；若 4-L9 自由測試顯示偏好排前，再做。
3. **每種候選最多請一次 LLM**（失敗就退回組合器／技能池，不換關鍵字再試），避免一組候選呼叫次數爆增；模型 8 秒／次時一組候選最多約 3 次呼叫（約 3×最多 3 次重試）。
4. **LLM 來源在武器不相容時算失敗**（現在驗證器會先擋下重試，所以少見）。「新方向」要求不同屬性，LLM 技能不另外強制（`hero_attributes` 為 None，由引擎取範圍內屬性）。
5. **提議器用 ContextVar 掛接**（不逐層傳參數）；API 尚未提供開關（`run.llm` 只能由 CLI 或存檔設定），要在網頁上開需另開 API 欄位。
6. **配額計數**：計所有候選（含組合器／技能池）頂層效果原語，不含巢狀；權重公式為 `base×100÷(100+n×100)`，係數可調。
7. **退回原語限制**：`propose_skill` 的退回技能（fallback_skill）在候選流程中被丟棄（改由候選產生器自己的組合器→技能池退回），所以一次 LLM 失敗仍多花一次 `fallback_skill` 的計算（無 LLM 呼叫）；可加參數省略。
8. **主題 `nature` 只進 prompt 的題目區塊**，沒有強制檢查（例如不得用火冰雷）；4-L9 觀察後再決定是否加驗證。
9. 名稱與敘事（4-L7）、change 欄位（4-L8）、真模型評估（4-L9）照規格未做。
