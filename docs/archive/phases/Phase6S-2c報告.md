# Phase 6S-2c 報告：結構補強的附帶效果不再固定先試 damage

- 範圍：`src/trpg/skillgen/proposal_topup.py`、`proposal_budget.py`（傳種子與稀有度、建議文字）、`src/trpg/llm/prompts/proposal.py`（預算說明的例子）、`builder.py`（版本號）、`tests/skillgen/`、`tests/llm/test_prompts.py`（新版本快照一行）。
- 驗證規則、預算數值與上下限都沒有改；沒有呼叫真的 LLM。

## 1. 改了什麼

### 1.1 附帶效果的順序（`proposal_topup.filler_order`）

6S-2 固定照 `damage → heal → shield` 試，第一個合格的採用，所以只要傷害合格就一定是傷害。現在：

1. **骨架偏好的一組先試**（`FILLER_PREFERENCE`，原型值）：

   | 骨架 | 先試 |
   |---|---|
   | strike、area、combo、builder_finisher、rune、consume_status、trap（攻擊） | damage |
   | aura（支援） | heal、shield |
   | control（控制） | apply_status（有害狀態） |
   | displace（位移） | damage、apply_status |
   | 表外（passive、reaction、summon、stance…） | 核心效果對友方／自己 → heal、shield；否則 damage、apply_status |

2. 偏好組與其餘各自 **依「題目種子＋提議內容」的雜湊輪替起點**：`json.dumps(提議, sort_keys=True)` 前面接種子，用 `trpg.shared.rng.fnv1a64`（不用內建 `hash()`、不用亂數）。種子是 `evaluate_with_repair` 原本就有的 `seed`（`propose_skill` 傳題目種子），所以同一題的三次嘗試、重播都相同。
3. 其餘照舊：每個候選走完整驗證（提議模型、補值、`validate_skill`、題目要求），第一個合格的採用；最多 24 個、每組 10 個。

### 1.2 新增附帶效果 `apply_status`（有害狀態）

規格要求「控制骨架優先非 damage 的狀態類」，原本的三種附帶效果沒有狀態類，所以加了 `apply_status`：

- 只施加給敵方、只用 **非有益** 的狀態；狀態必須有預算點數、稀有度夠（與提議模型 `apply_status` 的狀態選單同一組條件：`budget_statuses`、`rarity_statuses`），依雜湊輪替起點取 3 種（`FILLER_STATUS_MAX`）。
- 只有題目選單開放 `apply_status` 時才加（同其他附帶效果）。
- 關鍵字補強（`_keyword_candidates`）沒改。

### 1.3 提示詞與回饋

- `BUDGET_NOTE_ZH`：例子原本是「pull＋damage 可、cleanse＋heal 可」，改成「依技能主題選，不一定是傷害（例：pull＋施加狀態、pull＋damage、cleanse＋heal、cleanse＋shield 都可；只有 pull 不可）」。
- `WEAK_ADVICE`（補強救不回時回給 LLM 的建議）：「例如對敵方的 damage、對友方的 heal」改成「依技能主題選，例如對友方的 heal 或 shield、對敵方的施加狀態或 damage」。
- 系統指令沒改（快照雜湊相同）；`PROMPT_VERSION` 改成 `skill-proposal/7`，`tests/llm/test_prompts.py` 加一行快照（同 6S-2 做法）。

## 2. Mock 的補強分布（改前 vs 改後）

改前＝6S-2 的固定順序（測試裡用 monkeypatch 還原 `filler_order`／`FILLER_EFFECTS` 對照）；改後＝本段。

### 2.1 50 題升級候選（`upgrade_items(seed=0)`）的單一核心提議

建構方式同 6S-2 報告 3.2：每題、每個骨架、前兩個形狀 × 對象，取「`topup=False` 時只剩 `budget.weak`／`keyword.required`」的單一核心提議。可建構的 52 份提議（13 題）。

**純附帶效果的補強**（題目沒有關鍵字、由 `topup.budget.weak` 修好）：

| 補上的附帶效果 | 改前 | 改後 |
|---|---:|---:|
| damage | 5 | 2 |
| heal | 4 | 0 |
| shield | 0 | 4 |
| apply_status | 0 | 3（blinded、prone、silenced 各 1） |
| 合計 | 9 | 9 |

有關鍵字的題（關鍵字補強先試，順序沒改）：改前 apply_status 19／damage 4／create_surface 4／補參數 9，改後 apply_status 20／damage 3／create_surface 4／補參數 9。

**合格數不變**：52 份裡兩邊都是 45 份合格、7 份補不回。

### 2.2 同一份提議換種子（12 個種子）

| 提議 | 改前 | 改後 |
|---|---|---|
| aura：cleanse（階級 3 普通） | heal 12 | heal 6、shield 6 |
| displace：pull（階級 1 稀有） | damage 12 | damage 6、apply_status 6（prone 2、bleed、poison、vulnerable、weaken 各 1） |

每個補強結果都通過 `validate_skill`、預算比例在驗證器的窗內。

## 3. 測試

`tests/skillgen/test_topup_6s2c.py`（新，13 個，約 30 秒，不標 slow）：

- `filler_order`：7 種骨架／核心的偏好組在前、每種原語都會試到、40 個種子內偏好組的起點都輪替到、確定性。
- 同種子、不同提議內容（射程）也會輪替。
- 候選確定性、只用選單內原語、有害狀態只打敵方且非有益；普通稀有度只試普通狀態。
- 2.2 的兩份手寫提議：12 個種子都合格、驗證全過、預算在窗內，補上的附帶效果種類＝{heal, shield}／{damage, apply_status}。
- 2.1 的 50 題表格：重跑結果相同；合格數不少於舊順序；舊順序傷害過半，新順序傷害少於舊順序、不過半、至少三種附帶效果。

既有測試的調整（行為改變的直接結果，不是放寬）：

- `test_topup_6s2.py::test_real_weak_failures_are_topped_up`：補的效果也可能是 `apply_status`，斷言改成「傷害與有害狀態打敵方、治療／護盾給友方」。
- `test_topup_6s2.py::test_unfixable_weak_gets_actionable_feedback`：控制骨架的 clear_surface 現在補有害狀態就合格（`apply_status` 是控制骨架的核心原語）；先斷言它被補好，再用不開放 `apply_status` 的選單維持「救不回、附建議」的情境。
- `test_topup_6s2.py::test_request_payload_has_budget_and_keyword_notes`：檢查的字串從「pull＋damage」改成新說明的「不一定是傷害」「cleanse＋shield」。
- `test_proposal_l10b.py::test_lone_knobless_core_still_reports_weak`：3 階單獨傳送現在由結構補強加有害狀態修好；這個測試驗的是 4-L10b 的數值補強，改成 `topup=False` 驗原本的斷言，另斷言開啟補強時合格。

`test_refactor_3wr2` 等 fixture 沒有變（結構補強只在 LLM 提議路徑），不需重產。

## 4. 檢查

- `ruff check`、`ruff format --check`、`mypy src`（511 檔）、`lint-imports`（13 條契約）通過。
- `pytest tests/skillgen tests/llm -n 8`：4145 通過、14 略過（既有的條件略過），約 4 分 49 秒。
- 重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 通過（88 個動作、313 個事件）。

## 5. 待 PM 決定

1. **新增 `apply_status` 附帶效果**：規格的「控制骨架優先狀態類」需要它，但這讓補強多了一種效果，也讓一些原本救不回的提議變合格（控制骨架的淨地、揭露、奪取增益，3 階單獨傳送）。保守的替代是把 `FILLER_EFFECTS` 改回三種、只保留輪替與偏好。我的判斷：只用選單內、非有益、稀有度夠的狀態，驗證全過才採用，預設開。
2. 骨架偏好表 `FILLER_PREFERENCE`、`FILLER_STATUS_MAX = 3` 是原型值，寫在程式裡（同 6S-2 的 `FILLER_EFFECTS`）；位移骨架放成「傷害與有害狀態輪替」而不是只偏好狀態，因為位移骨架加傷害是很自然的組合，全推給狀態會變成另一種集中。
3. Mock 掃描可建構的樣本不多（純附帶效果 9 份），分布是方向性的證據；真實模型的前後比較（不同組合數、最常見組合占比）請 PM 照 6S-2 報告第 4 節的指令補量。
4. 控制骨架的附帶效果只允許 damage，`apply_status` 優先只在它能當核心（第二個核心效果）時有效；這是骨架規則本身，沒改。

## 6. commit

- `e49c700a` feat(skillgen): 6S-2c rotate top-up filler order by skeleton preference and hash
- `e0156d4e` feat(llm): 6S-2c neutral filler examples in budget note and weak advice
- 本報告的 commit（docs）
