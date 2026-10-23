# Phase 4-L5 報告｜重試迴圈＋退回＋數值補齊

> 規格：`docs/phases/Phase4計畫.md` 3B 節。實作者撰寫。全部測試用 `MockLLMClient`／`httpx.MockTransport`，沒有呼叫真模型。

## 1. 做了什麼

| 項目 | 內容 |
|---|---|
| client（3B-1） | `LLMConfig.enable_thinking: bool = False`（`config/llm.toml` 寫明，`TRPG_LLM_ENABLE_THINKING` 覆寫）；請求一律帶 `chat_template_kwargs: {"enable_thinking": …}`。`finish_reason == "length"` 且內容為空 → `LLMBadResponse`（中文訊息提示思考用光輸出、檢查 `enable_thinking`）。新模組 `trpg/llm/response.py` 的 `clean_response`：去掉 `<think>…</think>`（含只剩結尾標籤、思考被截斷）與包住整段的 ```` ``` ```` 程式碼框。 |
| 旋鈕共用（3B-2） | `composer_parts.effect_knobs(library, effect, *, category, weight)`：由效果字典推出強度旋鈕（骰子、武器倍率、狀態／表面持續、推拉距離、層數、賭注成功率、符文持續……）。隨機組合器改用它（`Ctx.add_knobbed`），**輸出逐位元不變**（400 個種子＋60 個種子 × 2 個關鍵字的 SHA-256 與改動前相同；組合器、候選測試全過）。另為組合器不會產生的 `charge_through`、`hurl_object`、`detonate_runes` 加骰子旋鈕（不影響組合器）。 |
| 預算補數值（3B-2） | 新模組 `skillgen/proposal_budget.py`：`budget_filler(library, *, seed, repairs=())` ＝ `minimal_filler` → 頂層效果的旋鈕（核心／附帶權重由 `validate.is_core_effect` 判斷）→ `composer_tuning.tune`。形狀參數不調；同提議＋同 seed → 同數值。 |
| 引擎修數值錯誤（3B-3） | `REPAIRABLE_CODES`（模組常數，見第 3 節）；`evaluate_with_repair(raw, models, library, ctx, *, seed)`：先以 `budget_filler` 驗證，錯誤全是規則層且全部可修時，以 `budget_filler(..., repairs=代碼)` 修一次再驗；修不好回傳修補前的錯誤。 |
| 退回（3B-5） | 新模組 `skillgen/proposal_fallback.py`：`fallback_skill(library, request, ctx, *, seed) -> (SkillDef, "composer"｜"pool"｜"workshop")`。① 組合器帶第一個題目關鍵字（換種子最多 8 次，結果需帶全部題目關鍵字〔專屬規則〕、骨架與種類相符）② 技能池（同階級、同稀有度、種類／骨架／關鍵字相符的手寫技能，依種子挑）③ 工坊推導（`draft_options` 依骨架逐步取第一組合法值：基本設定 → 形狀 × 核心效果〔各最多 4 × 6〕→ 必要條件；數值由 `budget_filler` 補，可修錯誤修一次）。都失敗丟 `FallbackError`。 |
| 迴圈（3B-4） | 新模組 `llm/propose.py`：`propose_skill(client, library, request, ctx, *, seed, max_attempts=3, player_text=None, clock=time.perf_counter) -> ProposalOutcome`。每次 `build_proposal_prompt`（重試帶上一份清理後的提議與 `feedback_payload`）→ `complete(json_schema=…)` → `clean_response` → `evaluate_with_repair`。`LLMUnavailable` 立即退回；`LLMTimeout`／`LLMBadResponse` 算一次嘗試；`SubsetError` 不呼叫 LLM 直接退回。 |
| 統計（3B-6） | `ProposalStats`：一次通過率、平均嘗試次數、退回率、各 `code` 次數、各來源次數、引擎修補次數、平均耗時；退回率 > `alert_permille` 時 `alert`（等於不提醒）。`summary_lines()` 給 CLI 與報告。 |
| CLI（3B-7） | `trpg llm propose [--tier N] [--rarity R] [--skeleton S] [--keyword K]... [--seed N] [-n 次數] [--mock] [--config path]`：每題一行（題目｜來源｜嘗試次數｜每次的錯誤 code｜耗時｜技能名）＋摘要表。`--mock` 每題用 `MockLLMClient`，回傳同階級／稀有度／種類／骨架的手寫技能經 `proposal_from_skill` 的提議（找不到就回 `{}`，走退回）。 |

## 2. 公開 API

- `trpg.llm.config.LLMConfig.enable_thinking`（新欄位，預設 `False`）。
- `trpg.llm.response.clean_response(text) -> str`。
- `trpg.llm.propose`：`propose_skill`、`ProposalOutcome(skill, source, records, reason)`（屬性 `attempts`＝實際呼叫 LLM 次數、`codes`＝每次的錯誤代碼、`seconds`）、`AttemptRecord(codes, seconds, repaired)`、`ProposalStats`（`of`、`add`、`first_pass_permille`、`fallback_permille`、`mean_attempts`、`mean_seconds`、`alert`、`summary_lines`）、`ProposalSource`、`LLM_ERROR_CODES`（`llm.unavailable`／`llm.timeout`／`llm.bad_response`）、`DEFAULT_MAX_ATTEMPTS = 3`。題目沒有可用結構時 `reason` 以 `subset.unavailable` 開頭。
- `trpg.skillgen.proposal_budget`：`budget_filler`、`evaluate_with_repair`、`RepairedEvaluation(result, repaired)`、`REPAIRABLE_CODES`、`is_repairable`、`repairable_errors`（另有 `REPAIR_COOLDOWN = 1`、`REPAIR_TUNES = 4`）。
- `trpg.skillgen.proposal_fallback`：`fallback_skill`、`FallbackError`、`FallbackSource`、`wanted_kind`、`COMPOSER_TRIES = 8`。
- `trpg.skillgen.composer_parts`：`effect_knobs`、`KnobSpec`、`Ctx.add_knobbed`。
- `trpg.skillgen.validate.is_core_effect`（`_is_core` 的公開包裝）。
- `trpg.cli.llm`：`cmd_llm_propose`、`ProposeArgs`、`propose_requests`、`PROPOSE_RARITIES`。

## 3. 可由引擎修的錯誤代碼（`proposal_budget.REPAIRABLE_CODES`）

| 代碼（fnmatch） | 修法 |
|---|---|
| `budget.over` | 換一條亂數串流重調旋鈕（核心優先、全部旋鈕交替，最多 4 次）。結構在最小旋鈕就超標時修不了（沒有 AP／冷卻旋鈕，見待決 #2）。 |
| `budget.weak` | 同上。 |
| `skeleton.core_share` | 重調時只動核心效果的旋鈕（附帶效果停在最小值），與全部旋鈕交替。 |
| `exclusion.no_cooldown_*` | 補最小合法冷卻 `cost.cooldown = 1`（預算折抵照 `skill_budget.yaml`），再重調。 |

不在清單：`budget.unavailable`（預算無法計算＝結構問題）、`variant.*.budget.*`、`skeleton.secondary_share`、`exclusion.stun_single_long_cooldown`（需要 single 形狀，不是純數值）、`cap.*`。

**手寫技能結構的實測**（161 個可表達的手寫技能，`proposal_from_skill` 後用完整模型驗證，seed 7）：`minimal_filler` 37 個合格 → `budget_filler`＋修補 **110 個合格**，其中 7 個靠修補（`exclusion.no_cooldown_big_area`）。剩下 51 個：`budget.weak` 44（召喚 18、`consume_status` 4、位移類的 `topple`／`hurl_object`／`swap`、`grant_skill`、`create_obstacle`、`restore_resource` 等沒有旋鈕或附帶占比上限卡住）、`exclusion.stun_single_long_cooldown` 4、`no_cooldown_big_area`（修補後仍過弱）4、`cap.rule_rewrite_cost` 2、變奏過弱 1、`budget.over` 1。

## 4. `trpg llm propose --mock -n 10`（seed 0）

```
  1. common／strike／prone｜llm｜嘗試 1｜通過｜0.00 秒｜火焰箭
  2. rare／不限骨架／collision｜llm｜嘗試 1｜通過｜0.00 秒｜汲命術
  3. epic／不限骨架／marked｜composer｜嘗試 3｜literal_error、extra_forbidden；（同左 ×2）｜暗影・光環 #1430544302
  4. common／不限骨架／high_ground｜llm｜嘗試 1｜通過｜0.00 秒｜火焰箭
  5. rare／area／無關鍵字｜llm｜嘗試 1｜通過｜0.00 秒｜聖水
  6. epic／不限骨架／無關鍵字｜composer｜嘗試 3｜cap.rule_rewrite_cost、budget.weak（×3）｜暗影・控場 #3988197716
  7. common／strike／無關鍵字｜llm｜嘗試 1｜通過｜0.00 秒｜聚雷
  8. rare／不限骨架／collision｜composer｜嘗試 3｜union_tag_invalid（×3）｜風・打擊 #128837899
  9. epic／area／無關鍵字｜composer｜嘗試 3｜missing×8（×3，沒有對應手寫技能，Mock 回 {}）｜物理・範圍 #1880156148
 10. common／area／無關鍵字｜llm｜嘗試 1｜通過｜0.00 秒｜旋風斬
```

| 項目 | 值 |
|---|---|
| 題目數 | 10 |
| 一次通過率 | 60.0%（6） |
| 平均嘗試次數 | 1.80 |
| 退回率 | 40.0%（4）（提醒：超過 20%） |
| 平均耗時 | 0.00 秒（Mock 模式計時固定為 0） |
| 來源 | llm 6、composer 4 |
| 錯誤代碼 | missing 24、budget.weak 3、cap.rule_rewrite_cost 3、extra_forbidden 3、literal_error 3、union_tag_invalid 3 |
| 引擎修補 | 無 |

Mock 每次回同一份提議，所以失敗的題目三次都同樣失敗；這張表只示範流程，不代表真模型的通過率（真模型由 PM 用不加 `--mock` 的同一指令測）。

## 5. 測試與檢查

`tests/skillgen`、`tests/llm`、`tests/cli/test_llm_propose_cli.py`、`tests/test_architecture.py` 910 過；`tests/cli/test_cli.py`、`test_output_snapshots.py` 過；`ruff check`、`ruff format --check`、`mypy`、`lint-imports`（7 契約）全過；`swamp` 種子 60 `--log-json` ＋ `replay` 一致。未跑 `scripts/check.py`，也沒有執行 `-m llm`。新增測試：

- `tests/llm/test_propose.py`（13 ＋ 1 個 `@pytest.mark.llm`）：壞 → 壞 → 好得 `llm`、`attempts=3`，第 2、3 次 user 訊息含上一份提議與錯誤；壞 ×3 → `composer`；`LLMUnavailable` 只呼叫 1 次就退回；`LLMTimeout`／`LLMBadResponse` 算嘗試；`SubsetError` 不呼叫；只剩 `budget.weak` 的提議 1 次呼叫就通過且比例在 `[low, high]`；`no_cooldown_big_area` 由引擎補冷卻 1；數值等於 `budget_filler` 同 seed 的結果；```` ``` ```` 與 `<think>` 包裝仍解析；`max_attempts`；`ProposalStats` 與 alert（等於 20% 不提醒、超過才提醒）。真模型測試：1 個題目跑完，來源不限，只驗不丟例外。
- `tests/llm/test_client.py`：`enable_thinking` 寫進請求（`httpx.MockTransport`）與環境變數覆寫；`finish_reason=length`＋空內容 → `LLMBadResponse`。`tests/llm/test_response.py`：清理的 10 種情況。
- `tests/skillgen/test_proposal_budget.py`：4 個手寫技能結構（最小補值只剩 `budget.weak`）補完合格、確定性、比例在區間、形狀參數不變；不同 seed 都在區間；冷卻修補、核心占比修補、不可修的錯誤原樣回傳；可修代碼表。
- `tests/skillgen/test_proposal_fallback.py`：三層各自觸發（以 monkeypatch 讓前面的來源失敗）、種類／骨架相符、確定性、全失敗丟 `FallbackError`。
- `tests/cli/test_llm_propose_cli.py`：`--mock -n 3` 輸出逐字快照（`tests/cli/snapshots/llm_propose_mock.txt`，`UPDATE_CLI_SNAPSHOTS=1` 重產）、題目輪替確定性、注入 client、未知關鍵字與設定檔錯誤。

## 6. `# noqa` 清單

無。

## 7. 待 PM 決定

1. **LLM 來源的技能不強制帶題目關鍵字**：關鍵字只用來篩 schema 子集（4-L4），驗證器只要求「至少一個關鍵字」；退回的組合器與技能池則要求帶全部題目關鍵字。4-L6 接候選產生器（加深／橋接需要特定關鍵字）前要決定是否把「缺題目關鍵字」當成要回 LLM 的錯誤。
2. **`budget.over` 實際上幾乎修不了**：重調只能從最小旋鈕往上，結構本身超標時需要冷卻折抵或調 AP，這段依規格不做 AP／冷卻旋鈕（4-L3 待決 #2）。建議 4-L8 一併考慮「超標時引擎補冷卻」。
3. **沒有旋鈕的結構必定過弱**：召喚（`count`／`duration`／`max_hp_permille`／`power_permille`）、`consume_status` 的巢狀 `then`、`topple`、`grant_skill`、`create_obstacle` 等沒有旋鈕（`tune` 只調頂層效果），這類提議會一路 `budget.weak` 到用盡再退回。手寫結構 161 個中 44 個屬此類。是否擴充旋鈕（巢狀效果、召喚參數階梯）或改以 AP 旋鈕補，請於 4-L8／4-L9 決定。
4. **`skeleton.secondary_share` 沒列入可修清單**（規格沒列）：理論上「降附帶旋鈕」可修，4 個手寫結構因此失敗（seed 3）。要列入只需加進 `REPAIRABLE_CODES` 並讓修補走「只調核心」。
5. **修補失敗時回給 LLM 的是修補前的錯誤**（反映 LLM 自己提議的問題，而不是引擎改過的版本）。
6. **工坊推導是保底**：只守骨架與種類、不保證題目關鍵字；名稱「〈骨架名〉（保底）」、`provenance.created_by = "workshop"`；姿態與傳說推導不出（多半由組合器先接住）。題目本身不可能（例：普通稀有度的被動或 combo）時三層都失敗並丟 `FallbackError`，CLI 印「失敗」行、不中止、結束碼仍為 0。
7. **退回的階級與稀有度取 `ctx`**（呼叫端決定，與 LLM 提議相同），骨架、種類、關鍵字取題目。
8. **CLI 輪替**：未指定稀有度時只輪 common／rare／epic（傳說需要源力代價等提議模型沒有的欄位，只在 `--rarity legendary` 時用）；骨架一半不指定、另一半從該稀有度可用的開放骨架抽；關鍵字 0 或 1 個；`--tier` 預設 1。`--mock` 的耗時固定記 0（快照需要）；Mock 依種子挑手寫技能，不看關鍵字。
9. **`chat_template_kwargs` 一律送出**（`enable_thinking` 為 false 也送）：vLLM 會用它；若之後換成不認得這個欄位而回 400 的伺服器，需要改成只在非預設值時送。
10. **`ProposalOutcome.attempts` 是實際呼叫 LLM 的次數**：`SubsetError` 直接退回時為 0。統計的「各 code 次數」已包含 `skeleton.secondary`（4-L4 待決 #6 的觀察指標）。
11. 本 worktree 原本沒有 `.venv`，我執行了 `uv sync --frozen` 建立本 worktree 自己的環境（沒有動主資料夾的環境）。
