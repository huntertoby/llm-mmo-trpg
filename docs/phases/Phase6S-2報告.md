# Phase 6S-2 報告：降低技能升級候選退回率

- 範圍：`src/trpg/skillgen/`（補值與補強、出題）、提示詞（`src/trpg/llm/prompts/proposal.py` 題目區、`builder.py` 版本號）、`tests/skillgen/`。另外動了 `tests/llm/test_prompts.py` 一行（新版本號的快照，見「待 PM 決定」3）。
- 沒有呼叫真的 LLM；改善後的實測由 PM 用 27B 補量（指令在最後）。
- 驗證規則、預算數值與上下限、互斥規則都沒有改。

## 1. 原因分析（27B 與 Gemma，commit 6af12836，升級候選 50 題）

### 1.1 退回的實際路徑

`propose_skill` 每次嘗試：`evaluate_with_repair` → `evaluate_proposal`（提議模型 → `budget_filler` 補數值 → `validate_skill` → 題目要求 `_topic_errors`）。有可修代碼時用 `budget_filler(repairs=…)` 再驗一次。3 次都不合格就走退回（組合器 → 技能池 → 工坊）。

兩個重點：

- **`keyword.required` 被 `budget.weak` 蓋住**：題目要求（關鍵字、核心原語）只在 `validate_skill` 全部通過後才檢查。所以第一次是 `budget.weak`，修好或重試後才冒出 `keyword.required`，常常把 3 次嘗試用完。
- **`exclusion.no_cooldown_big_area` 不是退回原因**：LLM 沒有冷卻欄位，引擎依 `skill_exclusions.yaml` 補冷卻（`cooldown_repairs`），兩個模型的「引擎修補」裡大量出現的就是這條修好的紀錄。被退回的 25／27 題，最後一次的錯誤沒有一題是它。

### 1.2 被退回的題目，最後一次的錯誤（每題計一次）

| 錯誤 | 27B（退回 25） | Gemma（退回 27） |
|---|---:|---:|
| `budget.weak` | 13 | 8（另有變奏的 budget.weak 2） |
| `keyword.required` | 7 | 4 |
| `value_error`（選填欄位組合） | 2 | 7 |
| `reference`（普通稀有度帶變奏） | 2 | — |
| `shield.status` | — | 3 |
| 其他 | 3 | 5 |

- 27B 退回題中 **19／25 有題目關鍵字**（Gemma 21／27）。
- 27B 的 47 筆 `budget.weak`，36 筆比例在 40% 以下（10～30% 最多），只有 8 筆在 60～70%。也就是「差一點」的不多，大多是 **整個結構太小**。

### 1.3 前幾大原因與證據

1. **只有一個沒有數值的核心效果 → 過弱，補值器補不回來**（27B 題 9 pull、45 push、8 topple、12 knock_prone、26／48／49 cleanse、15／25 zone、19 shadowstep、20 teleport…）。這些核心沒有旋鈕或旋鈕很小；4-L10b 的過弱補強（巢狀效果、AP 降到 1）最多把可用預算砍半，例如 cleanse 3.00 ÷ 23.11 降 AP 後仍只有約 26%。系統指令裡「越簡單越容易通過」也把模型推向單一效果。
2. **題目關鍵字帶不到**，分兩種：
   - **選單裡根本帶不到**（出題問題，換模型也沒用）：27B 題 0（普通稀有度淨化光環＋召喚物：號令要稀有）、5、11、22（光環不能對敵，毒只能施加給敵方）、28、44、47。這些題每次都退回。
   - **帶得到但模型不知道怎麼帶**：`available.keywords` 只給一句關鍵字說明（例如召喚物：「你可以獻祭自己的召喚物…」），沒說在這份選單裡要用 `apply_status（status＝commanding）`；題 3（帶電＝`damage（element＝lightning）`）、4、18、21、36 都屬此類。
3. **修占比後變過弱**：位移／控制骨架加了傷害時，第一次調值把傷害調過占比上限（`skeleton.secondary_share`），修補把傷害降回最低值後又過弱，但這次修補只帶 `secondary_share`、沒有走過弱補強。27B 題 35、39、46、47 的 `skeleton.secondary_share|budget.weak` 就是這條路徑。
4. 其餘（`value_error` 反應技形狀、普通稀有度帶變奏、地形限大地等）是模型的格式問題，回饋訊息已有，這段沒有處理。

## 2. 改了什麼

### 2.1 引擎修補（確定性、純函式，不放寬規則）

| 修補 | 位置 | 內容 |
|---|---|---|
| A. 結構補強 | `skillgen/proposal_topup.py`（新）、`proposal_budget.evaluate_with_repair` | 數值修補後只剩 `budget.weak`／`keyword.required` 時，依序試：①補 LLM 沒填的參數（例：`damage` 沒填元素就補成關鍵字要的元素）、②加一個題目關鍵字的專屬效果、③加一個附帶效果（`damage` 打敵方、`heal`／`shield` 給友方；傷害沿用提議裡的元素，沒有就物理）、④關鍵字效果＋附帶效果。**只加題目選單（提議模型）開放的原語**，每個候選照樣走完整驗證，第一個合格的採用；最多 24 個候選。有益狀態只給友方、有害狀態與有害原語只打敵方。`repaired` 記 `topup.budget.weak`／`topup.keyword.required`，報表可以和數值修補分開看。 |
| B. 連鎖修補 | `proposal_budget._evaluate_repaired` | 修一個可修代碼時冒出另一個可修代碼（最常見：修 `secondary_share` 後變 `budget.weak`），兩者一起再修一次；仍不合格就照舊回報第一次修補的結果。 |
| C. 過弱補強第 3 步 | `proposal_budget.lift_weak` | 原本的兩步都不行、且有占比受限的附帶效果時，把它降回最低值、只調核心（含巢狀）再走一次 AP 階梯。放在最後，原本補得到的結果不變。 |
| D. 出題可達性 | `proposal_topic.make_topic`、`proposal_topup.keywords_reachable` | 題目有關鍵字時，檢查選單裡至少有一種寫法可能帶到（原語在選單且放得進某骨架、狀態稀有度夠、有害效果不在禁止對敵的骨架、或條件／觸發／形狀在選單）。指定的核心讓關鍵字帶不到時換別的核心（最多 4 次；第一次仍用原本的 `core` 串流），都不行就不指定核心；連不指定核心都帶不到就換下一個稀有度。**沒有關鍵字的題目完全不變。** |
| E. 回饋訊息 | `proposal_budget._topup_advice` | 補強也救不回時，`budget.weak` 附「請再加一個骨架允許的附帶效果…」，`keyword.required` 附這份選單裡的可用寫法。只改訊息文字。 |

### 2.2 提示詞

- `available.keywords[]` 多一個 `ways`：這份選單裡帶得到該關鍵字的寫法（例：`apply_status（status＝commanding）`、`damage（element＝lightning）`、`條件 target_has_status（status＝poison）`），最多 6 個。
- 題目區（`<request>`）多兩段說明：
  - `budget_note_zh`（每題都有）：效果總強度要到 70%～100%；只有一個沒有數值的核心一定過弱，骨架允許時加一個附帶效果（正例 pull＋damage、cleanse＋heal，反例只有 pull）；冷卻由遊戲依形狀自動補（大範圍會加冷卻）；選填欄位越少越好，但效果數量不在此限。
  - `keyword_note_zh`（有關鍵字的題才有）：必須照 `ways` 選一種寫法帶到每個關鍵字，附一個例子。
- 系統指令沒改（快照雜湊相同），`PROMPT_VERSION` 改成 `skill-proposal/6`，讓 run 紀錄分得出新舊提示。
- token：50 題升級候選第一次 prompt 的估算平均 2363 → 2634、最大 4321 → 4290（兩邊題目集因修補 D 略有不同；真實 token 約為估算的 0.76，平均約 +200）。仍遠低於 8192。

## 3. 離線證據

### 3.1 表格測試（`tests/skillgen/test_topup_6s2.py`，18 個）

- **真實失敗重建**：6 個提議在 `topup=False` 時得到與 27B `skills_errors.csv` **一字不差** 的訊息（題 9、45、8、26、48、49，例如「過弱：total 3.60 ÷ 可用預算 14.07 ＝ 25.6%（下限 70.0%，階級 1）」），正式流程下全部合格；斷言：`validate_skill` 無違規、預算比例在窗內、核心與形狀保留、只多一個語意合理的附帶效果。
- 連鎖修補：push＋damage（階級 1）修補前後都合格，`repaired` 含 `skeleton.secondary_share` 與 `budget.weak`。
- 關鍵字補強：topple＋「標記」補 `apply_status marked` 給敵方；knock_prone＋「召喚物」補 `apply_status commanding` 給友方；技能依專屬規則帶到關鍵字、預算在窗內。
- 確定性與純函式：同輸入兩次結果相同、輸入不被修改、候選順序固定。
- 救不回的（控制骨架的 clear_surface，傷害最多 40%）照舊回 `budget.weak`，訊息附建議。
- 出題：27B 題 0 的題目判為帶不到、改成稀有就帶得到；`make_topic` 對 6 個關鍵字 × 8 個種子只出帶得到的題（slow）；沒有關鍵字的題目不受影響。
- 提示：`ways` 與兩段說明有出現，沒有關鍵字的題不帶關鍵字說明，prompt 估算 < 3500。
- `propose_skill` ＋ `MockLLMClient` 回題 26 的單一淨化：第一次就合格（來源 `llm`，1 次嘗試）。

### 3.2 50 題的單一核心掃描（離線腳本，不進版控）

對每題用「只有核心效果」的提議（最常見的失敗型態）比較補強前後：可建構的 22 題中，補強前 `budget.weak` 12、`keyword.required` 6；補強後 `budget.weak → 合格` 6、`keyword.required → 合格` 3（其餘是選單帶不到關鍵字的題，現在出題時已排除；或控制骨架占比限制下結構上補不到的 steal_buff、clear_surface）。補強耗時平均 0.02 秒、最大 0.07 秒。

### 3.3 回歸對照（舊 commit 4b508cb6 的 `proposal_budget`／`proposal_topic` vs 新）

把每個手寫玩家技能轉成提議（`proposal_from_skill`），在階級 1～3 下各驗一次，另加「只留第一個效果」的版本，舊版與新版的 `evaluate_with_repair` 對照（全選單提議模型、種子 11）：

| 結果 | 次數 |
|---|---:|
| 舊版合格 | 1113 |
| 　其中新版合格、技能完全相同 | **1113**（沒有任何一個改變） |
| 舊版不合格 | 444 |
| 　新版轉為合格 | 87 |
| 　新版仍不合格 | 357（剩下的多是 `tier.*`、`skeleton.condition`、`skeleton.required_primitive` 這類補強不處理的結構錯誤） |

出題（`make_topic`，階級 1～3 × 種子 0～39 × 6 種關鍵字設定）：沒有關鍵字的 120 題 **全部相同**；有關鍵字的 600 題中 215 題改變（換了核心或稀有度，避開帶不到關鍵字的組合）。

### 3.4 Mock 評估（`scripts/eval_llm_skills.py --suites upgrade`，Mock）

只用來確認流程與耗時，不代表模型表現（Mock 從手寫技能挑提議，多數不在題目選單內而以 `union_tag_invalid` 失敗）：50 題、牆鐘 84 秒（平行 4），每題含補強平均 0.1 秒、最大 0.3 秒。有 1 題（反應技 heal＋高地，階級 2 稀有）三種退回都做不出技能而丟 `FallbackError`；退回路徑（組合器、技能池、工坊）這段沒有改，27B 實測時這題是 LLM 一次通過，應是既有的退回缺口，列入待決 6。

### 3.5 檢查

- `ruff check`、`ruff format --check`、`mypy src`（494 檔）、`lint-imports`（13 條契約）通過。
- `pytest tests/skillgen -n 8`：3783 通過、14 slow 略過（含 `test_refactor_3wr2` fixture、budget 測試，都沒有變）；新測試的 slow 項另跑通過。另跑 `tests/llm`（328 通過），因為改了提示詞與版本號。
- 重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 驗證通過（88 個動作、313 個事件）。

## 4. 待 PM 實測的指令（27B，同一套題目）

```bash
TRPG_LLM_BASE_URL=http://127.0.0.1:1234/v1 \
TRPG_LLM_MODEL=swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp \
TRPG_LLM_REASONING_EFFORT=none \
UV_NO_SYNC=1 uv run python scripts/eval_llm_skills.py --real --suites upgrade,forced,free \
  --workers 1 --seed 0 --out-dir <輸出資料夾>
```

或照舊用 `run_llm_eval.sh <輸出資料夾> http://127.0.0.1:1234/v1 swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp none` 的技能部分。看 `skills.md`：升級候選的退回率、「引擎修補」裡的 `topup.*` 次數、錯誤代碼表。

注意：升級候選題目裡有關鍵字的題，現在不會再出「選單帶不到關鍵字」的組合，所以種子 0 的 50 題和 6af12836 不完全相同（沒有關鍵字的題相同）。這是修補 D 的直接效果；如果要嚴格比較同一批題目，可以另外比較沒有關鍵字的題。

## 5. 待 PM 決定

1. **結構補強（修補 A）是否保留**：引擎會替 LLM 的提議多加一個效果（只加選單內的、驗證全過才採用），這比數值修補多走一步。保守的替代做法是只保留 B～E 與提示詞。關閉只需 `evaluate_with_repair(..., topup=False)`（目前預設開）。我的判斷：補上的效果都在 LLM 本來能選的範圍內、語意有限制（傷害打敵、治療給友），而且比整招退回到組合器更貼近 LLM 的設計，所以預設開。
2. **出題可達性（修補 D）是必要條件、不保證一定過**：例如「標記＋獻祭召喚物」靠條件 `target_has_status` 才帶得到，仍可能失敗。若實測後還有大量 `keyword.required`，可以考慮讓補強也試條件（這段沒做，條件會改預算倍率）。
3. **`tests/llm/test_prompts.py` 加了一行新版本快照**（雜湊和 `/5` 相同，因為系統指令沒改）：改版本號時這個測試要求新增快照，不在 `tests/skillgen/` 範圍內，只加了這一行。
4. **系統指令的「越簡單越容易通過」沒有改**（要改就得重算快照、動 `tests/llm`）；題目區的說明已補「效果數量不在此限」。若實測仍見大量單一效果的提議，建議下一段把這句改掉。
5. 原型數值（未經模擬）：候選上限 `TOPUP_MAX = 24`、每組 `TOPUP_GROUP_MAX = 10`、附帶效果順序 `damage → heal → shield`、出題換核心最多 `CORE_RETRIES = 4` 次。
6. Mock 評估看到「反應技 heal＋高地（階級 2 稀有）」三種退回都做不出技能（`FallbackError`）。不是這段造成的（退回路徑沒改），但真模型失敗時會變成例外，建議另排小段補退回。

## 6. commit

- `93ef03e9` feat(skillgen): 6S-2 structural top-up, reachable keyword topics, budget/keyword prompt notes
- `b680d66b` test(skillgen): 6S-2 table tests from real 27B failures; dedupe repaired codes
- 本報告的 commit（docs）
