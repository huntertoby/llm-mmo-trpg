# Phase 3W-7 完成報告：LLM 閃現變化提議

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3W計畫.md`「3W-7 細化」、第 3、5 節（#70、#72）；設計 `docs/design/06-技能.md` 6.34.3、6.34.7。
> 分支：`worktree-agent-a8215e5e6a417b6cc`（已 fast-forward 到含 `65ba6956` 的 main），未 push。
> 範圍：LLM 變化提議的選項來源、開關、紀錄、Mock 測試與 4-L9 評估入口。**沒有**接一輪流程（3W-5）、沒有改前端、沒有碰 3W-4b 的範圍（`whiteboard.py`、`skill_composer.yaml`）。測試全用 `MockLLMClient`，沒有呼叫任何真模型。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `240663de` | `make_offer` 的「提議型來源」掛鉤（`ProposingSource`）、`try_variation`、`skill_before`；變化目錄 `flash_catalog.py`；提議與補位的合併 `flash_merge.py`；`flash_templates.yaml` schema 加 `llm_hint` 欄位 |
| `f28d1e88` | `trpg.llm.flash_propose`（提議、驗證、重試、紀錄、來源、重播、命名、Mock、統計）、`trpg.llm.prompts.flash`（prompt 與 schema）、`trpg.llm.flash_eval` 與 `scripts/eval_flash_llm.py`、測試 `tests/llm/test_flash_propose.py`（35 個） |
| （本報告） | `docs/phases/Phase3W-7報告.md` |

## 2. 驗收

| 規格項目 | 結果 | 證據 |
|---|---|---|
| 1. 輸出只有「變化」、沒有數值；schema 由 `flash_templates.yaml` 產生；經 pydantic 與引擎驗證 | 通過 | schema 的欄位只有 `category/template/keyword/element/shape/note_zh`，列舉全來自目錄（`FlashCatalog`，由 `UsageSource` 展開，來源是 yaml）：`test_schema_has_no_numeric_fields_and_enums_come_from_the_catalog`。每項先過 pydantic（`extra=forbid`）、再查目錄、最後 `try_variation` 引擎真的套一次 |
| 2. 不指定 4 個（至少 2 類）、指定類別 3 個；一次呼叫、不合格用模板補；重試與退回照 4-L5 | 通過 | `test_good_proposal_fills_four_options_across_categories`、`test_focused_proposal_gives_three_in_the_category_and_costs_two`、`test_proposals_crowded_into_one_category_still_cover_two_categories`（4 個全在同一類，仍換成 ≥ 2 類）、`test_retry_accumulates_valid_items_and_gives_feedback`（合格的累積、第二次只再要 3 個）、`test_all_failures_fall_back_to_the_template_offer`（3 次失敗 → 題目與純模板來源完全相同）、`test_unavailable_model_stops_at_once_and_falls_back`；大變化轉型保底仍在：`test_major_flash_keeps_the_transform_guarantee` |
| 3. 名稱交給 4-L7；命名關閉時「{前綴}・{原名}」 | 通過 | `name_offer`：大變化／轉型的選項請 `name_skill` 命名（只換名稱與敘事），小變化不動；命名失敗或關閉保留 `derive_skill` 的「{前綴}・{原名}」：`test_major_options_are_named_and_minor_options_keep_the_prefix_name`、`test_naming_failure_keeps_the_prefix_name` |
| 4. 開關、確定性、種子標籤 `flash/...`、prompt 版本號、重播不呼叫 | 通過 | `select_flash_source(config)`：`generate` 關 ＝ `UsageSource`、開 ＝ `LlmFlashSource`（`test_source_switch_follows_the_generate_flag`）。`FlashProposalRecord`（pydantic、可存檔）含 `tag`（`flash/<技能>/<第幾次>/<重閃次數>[/<類別>]`）、`prompt_version`（`flash-variation/1`）、`accepted` 等；`RecordedSource` 直接取用紀錄，不需要 client：`test_replay_uses_the_record_and_never_calls_the_llm`（JSON 往返後題目與 `choose` 結果完全相同） |
| 5. 測試：合格／不合格／形態或種族原語／數值欄位／英文代號 → 驗證與退回；選項數與類別數；重播不呼叫 | 通過 | `test_each_kind_of_bad_item_is_rejected_with_its_code`（11 種錯誤各一，含 `beast_form`、種族類別、`damage` 數值欄位、英文代號、參數缺漏／越界／多餘）、`test_bad_responses_are_rejected_as_a_whole`、`test_think_tags_and_code_fences_are_cleaned`、`test_duplicates_are_dropped`、`test_not_applicable_variation_is_rejected_by_the_engine` |
| 6. 4-L9 評估加項的指標與腳本入口 | 通過 | `FlashProposalStats`（通過率、一次通過率、補位率、退回率與警示、平均嘗試次數、錯誤代碼、類別與模板命中、名稱抽樣）、`trpg.llm.flash_eval.evaluate_flash`、`scripts/eval_flash_llm.py`（預設 Mock；`--real` 才用真模型，等使用者開模型；`--csv` 輸出明細）。Mock 跑 12 招：題目 31、通過率 70.9%、補位 22.5%、退回 6.4%（Mock 不會依回饋修正，只是重複同一份回應，所以出現 `flash.duplicate`）：`test_evaluation_entry_runs_on_the_mock_and_reports` |
| 7. ruff、format、mypy、lint-imports、pytest | 通過 | `ruff check .`、`ruff format --check .`、`mypy`（817 檔）、`lint-imports`（7 kept）；pytest（`-m "(slow or not slow) and not llm"`，`-n 8`）：`tests/llm`、`tests/skillgen/test_flash*.py`、`tests/content`、`tests/test_architecture.py`、`tests/roguelite` 共 2074 通過；`tests/cli` 的快照與預算測試另見第 6 節 |

沒有新增複雜度類 `noqa`。

## 3. 設計摘要

- **來源掛鉤**：`flash.ProposingSource`（Protocol）= `FlashOptionSource` ＋ `proposed(library, request, skill)`。`make_offer` 若來源有 `proposed`，先把提議中類別可用、不重複、**引擎真的套得上**的變化建成選項放前面，其餘由資料順序補（`flash_merge.merge_options`）；不指定時至少涵蓋 `open.min_categories` 類（提議全擠一類時，從後面換成補位的別類）。**沒有 `proposed` 的來源（預設 `UsageSource`）行為完全不變**（`test_default_source_is_unchanged_without_proposals`）。
- **目錄**（`skillgen/flash_catalog.py`）：以 `UsageSource.ranked` 展開所有類別的候選變化，分組成「模板 → 可帶的關鍵字／元素／形狀選單」。LLM 只能在目錄內挑；`resolve` 把（模板、參數）對回資料產生的 `Variation`（形狀以 `type` 對回完整 `ShapeSpec`）。所以提議的變化一定是「資料本來就可能出的變化」，模型決定挑哪幾個，不能自創模板或參數。
- **提議器**（`llm/flash_propose.py`）：`propose_variations` 重試迴圈沿用 4-L5 的做法（`LLMUnavailable` 立即退回、`LLMTimeout`／`LLMBadResponse` 算一次嘗試；合格的累積、下一次只再要缺的數量並附 `<already>`、`<previous_proposal>`、`<errors>`）。錯誤代碼：`flash.not_json／schema／extra_field／unknown_category／category_not_available／unknown_template／template_not_available／category_mismatch／param_missing／param_not_offered／param_unused／english_text／note_text／duplicate／not_applicable`。`FlashProposalRecord.source`：`llm`（湊滿）、`partial`（部分，其餘模板補）、`template`（全退回）。
- **轉型保底不交給模型**：目錄不含轉型；模型提議轉型 ID 會被拒絕（`template_not_available`／`unknown_category`），保底仍由資料決定。
- **prompt**（`llm/prompts/flash.py`）：固定指令區＋資料區（`<request>`、`<skill>`、`<usage>`、`<held_keywords>`、`<catalog>`、`<already>`、`<previous_proposal>`、`<errors>`），資料區全部跳脫；沒有玩家文字、也沒有技能名稱（只給 `skill_summary` 的中文結構描述）。`llm_hint` 欄位已加進 4 種模板 schema，空的時候用 `summary_zh`（或進化模板的說明）。

## 4. 給 3W-5 的接點

- 一輪流程建 `FlashRequest` 後呼叫 `make_offer(library, request, source)`；`source = select_flash_source(llm_config, sink=...)`（或網頁 `llm` 開關對應的 `generate`）。`sink` 收到的 `FlashProposalRecord` 請隨 `FlashOffer` 一起存進 run；讀檔／重播時用 `RecordedSource(已存的紀錄)` 重新 `make_offer`（或直接用存下來的 `FlashOffer`，`choose` 不重算）。
- 命名：`name_offer(offer, client, library, seed=, taken=)` 回傳（改名後的題目, 命名紀錄），命名紀錄可存進 `FlashProposalRecord.names`（`model_copy(update=...)`）；命名關閉就不要呼叫。
- 4-L9：`uv run python scripts/eval_flash_llm.py --real`（使用者先開模型）。

## 5. 待 PM 決定

1. **`llm_hint` 沒填資料**：schema 已加欄位，但沒動 `content/flash_templates.yaml`（避免和 3W-2b 的改動衝突），目前 prompt 用 `summary_zh`。真模型評估後，若選擇偏斜，再補 hint。
2. **LLM 不能提議轉型**：保底由資料決定（守則 3、#70 的保底語意）。若要讓模型也能挑轉型種類，需改目錄加入轉型並處理「保底仍成立」。
3. **LLM 只能在目錄內挑參數**：關鍵字選單受 `UsageSource` 的候選上限限制（例如每個「第二關鍵字」模板最多 6 個）。這比「任意合法關鍵字」保守，但與一般出題同一套候選；要放寬需改 `_keyword_candidates`。
4. **提議排在補位之前**：選項順序是「模型提議的在前、模板補位的在後」，轉型位置仍由種子決定。這代表模型的偏好會影響選項順序；若 UI 要求隨機打散，由 3W-5／3W-6 決定。
5. **指定類別時只列該類的目錄**：模型被限制在該類；轉型仍另列第 4 個（3W-1 規則）。
6. **Mock 的重複回應**：`mock_flash_client` 每次嘗試回同一份回應，所以評估報表在「部分合格」時會出現 `flash.duplicate`，不代表真模型行為；真模型的通過率要等使用者開模型再量。
7. **命名只在大變化／轉型做**：小變化維持「{前綴}・{原名}」或原名（3W-1 規則），沒有請 LLM 命名；若小變化也要，需另定。命名失敗時保留「{前綴}・{原名}」而不是組合式名稱（避免大變化技能名稱和別招混淆）。
8. **紀錄的 `seconds`**：只供報表，放在 `FlashProposalRecord` 內；若 3W-5 要求 run 紀錄逐位元相同（含重播比對），請排除這個欄位。

## 6. 補充驗證

`tests/cli`（`--timeout=3000`）的 `test_output_snapshots.py`、`test_budget_cli.py` 8 個全數通過（426 秒；本段沒有改任何 CLI 輸出，`FlashTemplate` 新欄位不進規則包雜湊）。
