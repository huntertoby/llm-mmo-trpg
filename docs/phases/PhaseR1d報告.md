# Phase R1d 報告：`skillgen/proposal.py` 按職責拆成子模組、`preview._outcome` 改查表

依據：`docs/phases/整理提案-程式.md` 2.2 節 R1（`proposal.py`）與 `PhaseR4報告.md` 待 PM 決定第 1 項（`_outcome`）。分支 `dev/r1d`。做法照 R1a～R1c、R4。

## 結果一：`proposal.py` → `proposal/` 套件

`src/trpg/skillgen/proposal.py`（1,914 行）→ `src/trpg/skillgen/proposal/`（共 2,254 行，多出的是各檔的 docstring、import 與 `__init__` 的 re-export）：

| 檔案 | 行數 | 內容 |
|---|---|---|
| `__init__.py` | 170 | 原模組 docstring＋子模組說明、re-export、原樣的 `__all__` |
| `models.py` | 241 | 常數（`LLM_ID_PREFIX`、`PROPOSAL_KINDS`、`CLOSED_SKELETONS`、`NESTED_EFFECT_TYPES`、`CALLER_FIELDS`、`_MAX_*`、`_GENERAL_TAG`）、`Stage`、`_Proposal`、`ProposalError`／`ProposalContext`／`ProposalResult`／`ProposalModels`、`_compact`；型別組合小工具 `_literal`、`_list_of`、`_union`、`_strip_none`、`_id_choice`、`_get`、`_alias`、`_union_or_none` |
| `params.py` | 294 | `_Refs`、`grantable_skills`、參數型別（`_param_type`、`_is_numeric`、`_scaling_model`、`_field`、`_affects_type`、`_required`、`_has_nested`）、`TOP_ONLY_DAMAGE_PARAMS`／`ZONE_AFFECTS`／`EXACTLY_ONE_PARAMS`、`_split_effect`；`rarity_statuses`、`budget_statuses` |
| `builder.py` | 441 | `_Builder`（效果、巢狀、反噬、形狀、條件、觸發模型）、變奏（`_when_model`、`_variant_model`）、`reaction_events`、`_reaction_model` |
| `build.py` | 598 | 骨架／種類選擇、`_Shared`、版型效果 union、複合技能第二段、`WEAPON_REQ_*`／`CATEGORIES`／`ACTIVE_ONLY_FIELDS`／`LAYOUT_SPLITS`、`_Branch` 與頂層分支、`build_proposal_models` |
| `convert.py` | 203 | `_skill_id`、`_skill_data`、`combined_skill_name`、`to_skill_def`、`proposal_from_skill` |
| `evaluate.py` | 307 | 錯誤路徑與中文訊息、`_pydantic_errors`、`_rule_error`、`_layout_hints`、`evaluate_proposal`、`_topic_errors`、`_unheld_errors`、`feedback_payload` |

每檔 < 700 行。子模組依賴單向：`models` 為葉；`params` → `models`；`builder` → `models`、`params`；`build` → `models`、`params`、`builder`；`convert` → `models`；`evaluate` → `models`、`build`、`convert`。沒有循環匯入、沒有延遲匯入、沒有新增 `noqa`（原檔 13 個 `noqa: UP007` 照搬）。

### 做法

- 純搬移：腳本依原檔頂層敘述切段（含前置註解與屬性 docstring；三個 `# ----` 分節橫幅改由子模組本身取代），逐字搬到所屬子模組，各檔複製原 import 區塊、自動補上兄弟模組的 import，再以 `ruff --fix F401,I001` 清掉沒用到的。AST 比對：原檔 126 個頂層敘述（扣除模組 docstring、`__all__`、import；含屬性 docstring）全部原樣出現在新檔，無缺、無多。
- 唯一的順序變動：`_get`、`_alias`、`_union_or_none`、`_GENERAL_TAG` 移到 `models.py`、`rarity_statuses`／`budget_statuses` 移到 `params.py`（多個子模組共用，放上游避免循環；內容未改）。
- re-export：全專案（src／tests／scripts／bot，AST 掃描）從 `trpg.skillgen.proposal` 匯入的名稱 33 個（含私有 `_Refs`、`_proposal_path`、`_pydantic_errors`、`_rule_error`、`_skill_path`、`_topic_errors`、`_unheld_errors`）；另加其餘 6 個公開名稱（`CALLER_FIELDS`、`COUNT_CHOICES`、`EXACTLY_ONE_PARAMS`、`LAYOUT_SPLITS`、`PLACEHOLDER_NAME`、`Stage`）與 `NumberFiller`（原檔自 `proposal_numbers` 匯入並列在 `__all__`），共 **40 個**，一律以 `import X as X` 明確 re-export；`__all__`（17 個）不變。
- 沒有人以 `import trpg.skillgen.proposal` 或 `from trpg.skillgen import proposal` 當模組物件使用或 monkeypatch（已 AST 掃描）；呼叫端 import 一行都沒改；import-linter 契約沒動。
- `create_model` 產生的模型 `__module__` 改成子模組名；JSON Schema 的 `$defs` 名稱沒有因此改變（沒有同名衝突、未出現模組限定名稱，下方 schema 比對逐 byte 相同）。

## 結果二：`engine/preview.py _outcome` 改查表

| | 前 | 後 |
|---|---|---|
| `_outcome` 本體 | 44 行、21 段 `isinstance` 鏈，`# noqa: C901, PLR0911, PLR0912` | 3 行：`_OUTCOME_HANDLERS.get(type(e))` 查表，無 `noqa` |
| 事件處理 | 內嵌在鏈中 | 每種事件一個小函式（`_damaged`、`_moved`…；4 種物件事件共用 `_object_at(kind)`），表 `_OUTCOME_HANDLERS: dict[type[EventBase], Callable[[Any], Outcome \| None]]` |

- 等價性：以腳本匯入全部 `trpg` 模組、走訪 `EventBase` 的 129 個子類別，確認表上 21 種事件型別彼此沒有繼承關係、也沒有任何子類別，所以 `type(e)` 查表與原本的 `isinstance` 鏈逐一等價（同 R4 `metrics_from_events` 的做法）。`UnitMoved` 的 `walk`／`dash` 原本落空後回傳 `None`，現在在 `_moved` 內直接回傳 `None`，結果相同。
- 表名用 `_OUTCOME_HANDLERS`：檔案後段已有說明字串常數 `_OUTCOMES`（`PRIMITIVE_PREVIEW` 用），避免撞名。
- `preview.py` 1,639 → 1,704 行（小函式的空行與簽名）。

### 複雜度 `noqa`

`src/` 中 `C901`／`PLR0911`／`PLR0912`／`PLR0915` 的 `noqa`：**8 → 7**（去掉 `engine/preview.py _outcome`）。剩下 7 個即 R4 報告保留表扣掉 `_outcome` 的其餘 7 處。

## 逐字比對

| 項目 | 結果 |
|---|---|
| `build_proposal_models` 的 JSON Schema 與中繼資料（稀有度 None／common／rare／epic／legendary × `split_category` 開關，10 組，約 1.7 MB） | 拆前拆後逐 byte 相同 |
| `trpg llm propose -n 3 --seed 1 --mock`（另加 `--naming`） | 拆前拆後輸出相同 |
| `trpg battle --map swamp --seed 7 --log-json` | 與 main `15ab0903` 的 src（`git archive`）逐 byte 相同；終端輸出只差「已寫入戰鬥紀錄：」路徑；`battle replay` 通過（88 個動作、313 個事件） |
| `client/openapi.json`（`scripts/export_openapi.py` 重產） | byte 相同（`git diff` 為空） |

## 驗收

- `ruff check`、`ruff format --check`、`mypy`、`lint-imports`（14 條契約 KEPT）：全過。
- `uv run pytest -q tests/skillgen tests/llm tests/engine tests/cli/test_output_snapshots.py -m "" -x -n 4`（含 slow 快照，未重產）：9510 passed、14 skipped、4 xpassed；8 個失敗全是 `@pytest.mark.llm` 的真模型測試（`test_real_model_ping`、`test_neutral_address_real_model.py` 6 個、`test_real_model_one_upgrade_item`），`-m ""` 會把它們一起選進來，這台 Mac 沒有本機模型（`LLMUnavailable`），與本段無關。CLI 快照 25 個全過。
- LLM 提議的 prompt 快照（`tests/llm/test_prompts.py` 等）在上面的 `tests/llm` 內，未重產通過。
- 匯入圖：R3 的 Tarjan SCC 檢查（頂端匯入、不含 `TYPE_CHECKING`、不含函式內匯入）：`trpg.engine` 165 個模組無環；`trpg.skillgen.proposal` 子模組無環。

## 待 PM 決定

- 交件指令的 `-m ""` 會選進 `llm` 標記的真模型測試，在沒有本機模型的 Mac 上必失敗；之後的交件指令建議改成 `-m "not llm"`。
- `ruff check .`／`ruff format --check .`（`check.py` 的範圍）在 main 上就因 `docs/art/sample/tools/qk_compare.py`（QK-1，`c71df733`）的 E501／PLR2004 與格式失敗；`src tests scripts` 全過。不在本段範圍，未動。

- `ProposalModels` 等類別與動態模型的 `__module__` 由 `trpg.skillgen.proposal` 變成子模組名（同 R1c 的 `UtilityAI`）。沒有找到依模組名的 pickle 或持久化；schema 輸出不受影響。
- `build.py`（598 行）的 `build_proposal_models` 仍是 R4 報告列的 80～100 行函式之一（92 行），本段純搬移未拆。
