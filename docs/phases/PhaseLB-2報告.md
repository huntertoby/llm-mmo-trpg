# Phase LB-2 報告｜本機 LLM 技能提議失敗診斷

> 2026-11-14。基底 main `791d01e25`（含 LB-1b `4317d97a8`）。原始資料：`docs/phases/LB-2資料/`。
> 題目同 LB-1：4-L5 那 20 題（seed 0），每題最多 3 次＋命名。沒改 `config/`、`docs/design/`、計畫檔。
> **第 6 步（改完後的重測）沒有跑完**：改完後 LM Studio 載入模型時沒有整個放進 GPU（Gemma 30 t/s、VRAM 9.4 GB；swift VRAM 17.9 GB、GPU 使用率 20%），依規矩停下回報。見第五節。

## 一、給使用者的白話結論

**問題主要出在我們這邊，不是 Gemma 不行。** 把每次失敗的原文都記下來之後（以前只記一個代碼 `value_error`），看得出 Gemma 被擋的原因大多是「我們沒告訴它的規則」：

1. **我們寫給模型看的欄位說明，模型根本看不到。** 技能提議的規則（例如「法術技的武器需求只能填 focus 或 any」「變奏只能換 1～2 項」）只寫在 JSON schema 的說明文字裡。但 LM Studio 只拿 schema 來限制輸出格式，**不會把說明放進 prompt**（實測：prompt token 數跟 schema 大小無關；schema 有 9 萬字元，prompt 只有 5～6 千 token）。prompt 本身完全沒提到 `category`、`weapon_req`、`element`、`variants` 這些頂層欄位是什麼。LB-1 裡 Gemma 的「格式錯誤 `value_error`」其實**一個都不是格式錯**，全是這類看不到的跨欄位規則。
2. **重試的回饋說不出要改哪裡。** 例：「地形限大地」的錯誤只說「技能元素要是 earth」，Gemma 把效果裡的元素改成 earth，但規則看的是 JSON 頂層的 `element`；同一份錯誤答案連交三次（第 8 題）。
3. **schema 本來就能擋的錯，我們沒擋。** 變奏數量的稀有度上限、變奏的替換項數、武器需求與類別的配對，都可以寫成 schema 的分支讓模型根本選不到錯的組合，原本沒做（類別分支以前因 schema 太大關掉，現在 schema 變小了放得下）。
4. **swift 那次「伺服器拒絕 response_format、退回 guided_json」**：同樣的 21 份 schema 現在對 Gemma、swift（思考開或關）都是 HTTP 200，重現不了。真正的問題是我們的 client：**只要任何一次 400 就永久改用 guided_json**，而 LM Studio 會整個忽略 guided_json（實測），於是整輪變成沒有約束，而且只記一則 warning。最可能的觸發是換模型那一刻的暫時錯誤。已修：不再永久退回，退回時每次記 error、量測結果標記次數。

改了什麼（**沒有放寬任何驗證或引擎規則**，只改說明、回饋與 schema 的表達）：

| 改動 | 針對的錯誤 |
|---|---|
| 每次失敗記下錯誤全文、pydantic 位置與輸入值、模型原始輸出、回饋文字（遊戲寫 `trpg.llm` 日誌、不記原始輸出；量測寫 JSON） | 看不出原因 |
| prompt 題目區加 `fields_note_zh`：類別與武器需求配對、頂層 `element`（含這題用得到的「限大地」規則）、附帶效果數量、變奏的寫法與上限、被動技能的 `affects` | 全部看不到的規則 |
| 重試回饋附修法：頂層 `element` 填什麼、`replace_effect.index` 改哪裡、刪多的附帶效果 | `terrain_needs_earth`、主傷害、`skeleton.secondary_count` |
| schema：頂層依類別分支（放得下時）、變奏數依稀有度設上限（common 不給變奏欄位）、變奏拆成「恰好 1～2 項」分支、拿掉模型看不到的說明文字 | `weapon_req` 配對、變奏數量與項數 |
| client：`guided_json` 不再默默變成永久退路 | swift 那輪整輪沒約束 |

**改完後各模型表現：還沒有數字。** 改完後的第一次 Gemma 重測遇到 LM Studio 只載入一部分到 GPU（30 t/s，基準時是 225 t/s），量測腳本依門檻自動停止；改跑 swift 也一樣（VRAM 只有 17.9 GB，LB-1 時 24.4 GB），我中止了。下表只有改前；改後兩欄等使用者處理好 LM Studio 後補跑（指令見第五節）。

| 項目 | LB-1 Gemma（沿用） | LB-1b Gemma（重測） | LB-2 基準 Gemma 0.7（只加記錄） | LB-2 基準 Gemma 0.3（只加記錄） | LB-2 改後 Gemma 0.7 ×2 | LB-2 改後 swift 0.7 ×2 |
|---|---|---|---|---|---|---|
| 一次通過 | 8/20 | 5/20 | 5/20 | 7/20 | 未跑（GPU 未載滿） | 未跑（GPU 未載滿） |
| LLM 最終通過（含重試） | 13/20 | 10/20 | 11/20 | 11/20 | — | — |
| 退回 | 7/20 | 10/20 | 9/20 | 9/20 | — | — |
| 平均嘗試 | 2.0 | 2.35 | 2.25 | 2.25 | — | — |
| 每題秒數中位數 | 3.81 | 4.28 | 4.12 | 4.25 | — | — |
| 命名成功 | 13/13 | 10/10 | 11/11 | 11/11 | — | — |
| 生成 t/s／VRAM | 未量 | 222／21.0 GB | 225／21.6 GB | 226／21.8 GB | 30／9.4 GB（停） | 未量到（暖機 35.6 秒，停） |

## 二、錯誤分類統計（改前）

基準條件：Gemma（`google/gemma-4-26b-a4b-qat`）、`reasoning_effort=none`、20 題、程式為第 1 個 commit（只加記錄）。schema 寫法兩輪都是 `response_format`，沒有退回。

- **提議格式（pydantic 層，schema 管得到的）錯誤：90 次嘗試中 0 次。** 約束解碼有效；所有錯誤都在「轉成技能」與「規則」兩層。
- 0.7 一輪 45 次嘗試 44 條錯誤；0.3 一輪 45 次嘗試 48 條錯誤。分輪的表在 `stats_gemma_base_t07.md`、`stats_gemma_base_t03.md`。

兩輪合計前 10 名（`stats_gemma_base_both.md`；`value_error`／`reference` 依訊息細分）：

| 名次 | 類別 | 次數 | 原文例子 | 對應改動 |
|---|---|---|---|---|
| 1 | `passive.affects` | 12 | Q12：effects[0]（raise_terrain）：trigger.target 為 self 時，效果的 affects 只能是 self，收到 tiles | prompt `fields_note_zh.trigger` |
| 2 | `skeleton.secondary_count` | 12 | Q3：骨架 strike：附帶效果最多 1 個，收到 2 個 | prompt `fields_note_zh.effects`＋回饋 `SECONDARY_ADVICE` |
| 3 | `value_error`｜變奏替換內容 1～2 項 | 11 | Q1：變奏 finisher 的替換內容必須填 1～2 項（shape、range_delta、element、add_effect、replace_effect），收到 3 項 | schema 變奏分支＋prompt `variants` |
| 4 | `exclusion.terrain_needs_earth` | 9 | Q8：…只有大地元素的技能能用（技能元素要是 earth）（效果 raise_terrain、damage）——Gemma 把 damage 的 element 改 earth、頂層不填，三次一樣 | prompt `element`＋回饋 `ELEMENT_ADVICE` |
| 5 | `value_error`｜變奏換掉主傷害 | 8 | Q13：變奏「帶電」：主傷害（第 0 個效果）不能被換掉 | prompt `variants`＋回饋 `MAIN_DAMAGE_ADVICE` |
| 6 | `budget.over` | 6 | Q12：超出預算：total 8.50 ÷ 可用預算 4.20 ＝ 202.4% | 不改（數值，非說明問題） |
| 7 | `value_error`｜法術技的 weapon_req | 5 | Q2：法術技（category: spell）的 weapon_req 只能是 focus、any，收到 melee | schema 類別分支＋prompt `category` |
| 8 | `budget.weak` | 4 | Q10：過弱：66.7%（下限 70%）＋既有建議 | 不改（已有 6S-2 建議） |
| 9 | `reference`｜稀有度變奏上限 | 3（rare 另 2） | Q13：稀有度 common 最多帶 0 個變奏，收到 1 個 | schema `maxItems`／common 拿掉欄位＋prompt `variants` |
| 10 | `skeleton.secondary_share` | 3 | Q20：骨架 rune：damage 占 55.6%，超過上限 40%…（已有建議） | 不改 |

其餘：武器技的 weapon_req 3、`reference`｜層數 ki 的 consume_stack 只能 affects self 2、`variant.detonate.*` 5、`exclusion.stun_single_long_cooldown` 1、`keyword.required` 1、`skeleton.core_share` 1。

**92 條裡約 65 條（7 成）屬於「規則沒告訴模型／schema 沒擋」**，其餘是預算與骨架占比這類需要模型理解數值的錯誤。

改後的錯誤分類：**未量**（第五節）。

## 三、schema 相容性調查

工具：`scripts/llm_schema_probe.py`（20 題＋暖機題的 schema 各送一次 `max_tokens` 8 的請求）、`LB-2資料/enforce_probe.py`（小 schema 看有沒有真的約束輸出）。

1. **400 重現不了**：Gemma 對 21 份 schema（`anyOf` 改寫後、原樣 `oneOf` 抽 4 份）全部 HTTP 200；swift 不思考 21 份、思考開 3 份全部 200（`probe_*.json`）。LB-1 那次 400 的回應本文沒有記，原因無法確定；最可能是換模型（qwen → swift）時第一個請求遇到載入中的暫時錯誤。
2. **真正的缺陷在 client**：`auto` 模式把任何一次 400／422 都當成「伺服器不支援 response_format」，**永久**改用 `guided_json`。實測 LM Studio 對 `guided_json` 完全不約束（給只能是 `zzz_only` 的 enum，模型照樣輸出 `red`；swift 還包了 ```` ```json ````）。所以 swift 那輪 60 次呼叫全部沒有約束，而且只有一則 warning。
3. **修法**（`llm/client.py`）：
   - 每次先試 `response_format`；接受過一次就只用它。
   - 接受過之後又被回 400／422 ＝ 那一次的錯誤，丟 `LLMBadResponse`（算一次嘗試、附伺服器本文），不退回。
   - 還沒接受過就被拒時，**只有這一次**退到 `guided_json`，每次記 **error**（附伺服器回應本文）、`unconstrained_calls` 加一；量測 JSON 寫 `schema_mode`、`unconstrained_calls`、`llm_log`，終端印「錯誤：N 次呼叫沒有 schema 約束」。
4. **oneOf → anyOf 有沒有讓模型選到互斥組合**：實測 LM Studio（llama.cpp 引擎）對 `oneOf`、`anyOf` 都有約束（分支內 const＋enum 不會混搭）；基準 90 次嘗試沒有任何提議格式層錯誤。互斥欄位的錯誤都來自「schema 沒有分支」的地方，不是 anyOf 造成的。已拆的分支：
   - **類別 × 武器需求**：用既有的 `split_category`（4-L10a 做好但預設關），頂層每個版型分 `_weapon`／`_spell` 兩支。分支後超過 `SCHEMA_CHAR_LIMIT`（125,000 字元）的寬題目（例：3 階 epic 帶兩個關鍵字，136k）自動改用不分支的版本，配對規則仍在 prompt。20 題最大 97k。
   - **變奏替換內容 1～2 項**：`maxProperties` 被 LM Studio 忽略（實測），所以把 `Variant` 拆成 10 個「恰好這幾項」的 `anyOf` 分支（4 項取 1 或 2）。
   - **變奏數量**：`variants.maxItems` ＝ 稀有度上限；common 直接拿掉欄位。
   - 另外拿掉 schema 的 `description` 與用不到的 `$defs`（模型看不到，只讓 schema 變大）。
   - 這些都只讓 schema 變窄；pydantic 模型與驗證器不變（`schema_shape.py`），測試確認手寫技能的變奏都落在分支內。
   - **拆不了的**：「主傷害不能被換掉」（index 是相對位置）、骨架附帶效果數量、預算 → 只能靠 prompt 與回饋。

## 四、溫度對照（改前）

同 20 題、同程式（只加記錄）、Gemma、`reasoning_effort=none`：

| 溫度 | 一次通過 | LLM 最終 | 退回 | 平均嘗試 | 中位秒數 | 錯誤條數 |
|---|---|---|---|---|---|---|
| 0.7 | 5/20 | 11/20 | 9/20 | 2.25 | 4.12 | 44 |
| 0.3 | 7/20 | 11/20 | 9/20 | 2.25 | 4.25 | 48 |

0.3 一次通過多 2 題，但最終通過與退回一樣，錯誤條數還多 4 條；以 20 題的樣本看**不算明顯較好**，所以改後重測只排 0.7（依派工）。兩輪通過的題目不同（0.7：2、3、5、6、7、9、11、14、15、16、20；0.3：3、5、6、7、8、10、11、13、14、15、20），題目間的隨機波動比溫度的影響大。預設溫度要不要改由使用者決定（待決第 3 點）。

## 五、改完後的重測（未完成）

- **Gemma 0.7 第 1、2 輪**：暖機後串流量速 **30.0～30.1 t/s、VRAM 9.4 GB**（基準時 225 t/s、21.6 GB），腳本依 60 t/s 門檻自動停止（`run_gemma_after_t07_r1.log`、`_r2.log`）。我在這之前用探測腳本換過 swift（換模型會讓 LM Studio 重載），Gemma 重新載入後只有一部分在 GPU。
- **swift 0.7**：載入後 VRAM 17.9 GB（LB-1 是 24.4 GB）、GPU 使用率 20%，暖機 35.6 秒（LB-1 不思考 5.8 秒），量速請求久久不回，我中止了（`run_swift_after_t07_r1.log` 只有暖機一行）。qwen3.6 沒試。
- 我沒有啟動、關閉 LM Studio，也沒改它的設定；換模型只用 `TRPG_LLM_MODEL`。
- **補跑方法**（使用者把 LM Studio 的 GPU offload 調回全部放 GPU 後，依序跑，每行一個）：

  ```
  uv run python scripts/llm_model_compare.py --model google/gemma-4-26b-a4b-qat --reasoning-effort none --temperature 0.7 --label gemma_after_t07_r1
  uv run python scripts/llm_model_compare.py --model google/gemma-4-26b-a4b-qat --reasoning-effort none --temperature 0.7 --label gemma_after_t07_r2
  uv run python scripts/llm_model_compare.py --model swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp --reasoning-effort none --temperature 0.7 --label swift_after_t07_r1
  uv run python scripts/llm_model_compare.py --model swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp --reasoning-effort none --temperature 0.7 --label swift_after_t07_r2
  uv run python scripts/llm_model_compare.py --model qwen3.6-35b-a3b --reasoning-effort none --temperature 0.7 --label qwen_after_t07_r1
  uv run python scripts/llm_failure_stats.py docs/phases/LB-2資料/gemma_after_t07_r1.json docs/phases/LB-2資料/gemma_after_t07_r2.json
  ```

## 六、每項 prompt／回饋／schema 改動對應的錯誤

| 改動（位置） | 內容 | 對應錯誤（改前次數，兩輪合計） |
|---|---|---|
| `prompts/proposal.py` `CATEGORY_NOTE_ZH` | weapon／spell 的意思＋配對規則（原本只在 schema 說明，模型讀不到） | `value_error` weapon_req 8 |
| `ELEMENT_NOTE_ZH`＋`_element_rules` | 頂層 element 是技能元素、效果裡的不算；這題用得到的 `require.elements_any` 規則從 `skill_exclusions.yaml` 產生 | `exclusion.terrain_needs_earth` 9 |
| `EFFECTS_NOTE_ZH` | 核心以外都算附帶效果、數量看骨架 `secondary.note` | `skeleton.secondary_count` 12 |
| `VARIANTS_NOTE_ZH`／`VARIANTS_NONE_ZH` | 稀有度上限、1～2 項、index 從 0 起算、不能換主傷害、common 不填 | 變奏項數 11、主傷害 8、變奏數 5 |
| `PASSIVE_NOTE_ZH`（只有被動題） | trigger.target 為 self 時 affects 只能 self | `passive.affects` 12 |
| `evaluate.py` `advise`：`ELEMENT_ADVICE` | 「請在技能 JSON 的頂層填 element: "earth"（效果裡各自的 element 不算）」，規則清單來自內容資料 | `terrain_needs_earth`（Gemma 連三次同答） |
| `MAIN_DAMAGE_ADVICE` | 改 index 或改用 add_effect | 主傷害 8 |
| `SECONDARY_ADVICE` | 刪多的附帶效果或換骨架 | `skeleton.secondary_count` 12 |
| `schema_shape.py`＋`split_category` | 見第三節第 4 點 | weapon_req 8、變奏項數 11、變奏數 5 |

「Gemma 看不懂的寫法」：prompt 原本依賴模型從欄位名猜意思（Qwen 系猜得比較準），這次改成每個頂層欄位都有一句中文說明；沒有改 system 指令（system 與命名等其他 prompt 共用，改它影響面大）。

## 七、快照與測試逐鍵說明

- **`tests/llm/test_prompts.py` 的 `SNAPSHOTS`**：只新增 `"skill-proposal/15"` 一鍵，雜湊與 `/14` 相同。快照只雜湊 `build_skill_proposal_messages` 的固定輸入，這次的改動在它外面（`build_proposal_prompt` 的題目內容、schema、回饋），所以預測與結果都是「雜湊不變、只多版本號」。`PROMPT_VERSION` 依規矩升 `skill-proposal/14 → /15`。
- **`tests/llm/test_proposal_prompt.py::test_prompt_structure`**：原本斷言 `prompt.json_schema == models.json_schema()`；改成等於 `shape_schema(models.json_schema(), variant_limit=…)`，並檢查有 `SkillProposal_weapon`／`_spell` 兩支。
- **`tests/llm/test_propose.py::test_charge_through_form_in_prompt_and_schema`**：版型定義名多了類別後綴，改成兩支都檢查形狀只有 `ground_tile`。
- **`tests/llm/test_client.py`、`test_schema_rewrite.py`**：退回 guided_json 的行為改了（不記住、記 error），對應的三個測試改寫並改名；新增「接受過後的 400 不退回」。
- 沒有重產任何 Mock 快照或 parity 夾具；Mock 提議器用的是驗證結果，判定沒變。Mock 相依的 api／cli／roguelite／world 測試 83 個照過。
- 新測試：`tests/llm/test_propose_diagnostics_lb2.py`（記錄欄位、日誌不含原始輸出）、`tests/llm/test_schema_shape_lb2.py`（變奏分支、稀有度上限、類別分支、太大時退回不分支、欄位說明、修法）。全部離線。

## 八、驗收

- `ruff check`、`ruff format --check`、`mypy`（652 檔）、`lint-imports`（14 kept）通過。
- `tests/llm` 全部＋`tests/skillgen` 提議相關 16 檔＋`tests/test_architecture.py`：857 passed（`-n 8`）；Mock 相依的 api／cli／roguelite／world 9 檔 83 passed。
- 戰鬥不變比對（改前＝main `791d01e25` 用 `git archive` 解開、`PYTHONPATH` 指過去；8 張地圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，地圖預設陣容、效用 AI、`max_rounds=30`；比整份事件、步驟、去掉規則包的最終狀態）：`battles=46 events=20458 different=0`。這段沒動引擎。

## 九、待 PM 決定

1. **LM Studio 的 GPU 載入**：改後重測卡在模型沒整個放進 GPU（第五節）。要請使用者處理後補跑；補跑後由誰把改後欄位填回這份報告？
2. **`reasoning_effort` 預設**：LB-1 已證實不設 `none` 時 qwen／swift 全部退回。`config/llm.toml` 要不要預設 `reasoning_effort = "none"`（vLLM 不一定接受）由使用者決定；這段沒改。
3. **溫度**：0.3 與 0.7 在 20 題上沒有明顯差別（第四節），建議維持 0.7，由使用者決定。
4. **`SCHEMA_CHAR_LIMIT`**：類別分支讓寬題目（2～3 階、多關鍵字）超過 125k，這些題目現在退回不分支的 schema。要不要提高上限讓它們也分支（會拖慢約束解碼的編譯，沒量）？
5. **Q12（epic 被動、high_ground）**：LB-1、LB-2 所有模型都退回；Gemma 每次都用 raise_terrain 當被動效果（affects 只能 self 的規則下做不出來）。可能是題目本身的子集沒有合適的被動結構，建議玩法 PM 看這題的設計。
6. **`range_delta`**：驗證器訊息列出它是變奏可替換的項目，但提議模型沒開放給 LLM（`skill_tidal_spear` 這類只有 range_delta 的變奏 LLM 寫不出來）。要不要開放？
7. **LB-1 那次 400 的原因**：現在的 client 會把伺服器回應本文寫進 log 與量測 JSON，下次發生就看得到；目前無法確定。

## 十、commit

1. `37433e67c` feat(lb-2): record full diagnostics for failed skill proposals
2. `6b91ebaf1` fix(lb-2): never silently drop the JSON schema constraint（client、探測與統計腳本、基準資料）
3. `faa807a3e` feat(lb-2): explain hidden field rules in the prompt and tighten the schema
4. docs(lb-2): report（本報告、錯誤統計表、中止的重測紀錄）

## 開發 PM 裁定（2026-11-14）

- **驗收通過，合併。** 改了 5 個測試，都是跟著 client 行為改（退到 guided_json 不再記住、每次記 error）或 schema 分支後的定義名改的，**沒有放寬任何驗證**。快照只新增 `skill-proposal/15` 一鍵，雜湊與 /14 相同，跟預測一致。戰鬥不變比對 different=0。
- **第 6 步改後重測沒跑完，不算這段的缺失**：LM Studio 重載後模型沒整個放進 GPU（Gemma 30 t/s、9.4 GB），agent 照規矩停下。等使用者把 GPU offload 調回後，由開發 PM 派 **LB-2b**，照第五節的指令補跑，填回「改後」欄位，並和 LB-1 並排。
- 待決 1：同上，LB-2b。
- 待決 2、3（`reasoning_effort` 預設、溫度）：使用者決定。這段沒改 `config/llm.toml`。
- 待決 4（`SCHEMA_CHAR_LIMIT` 125k）：先維持。LB-2b 如果看到寬題目（2～3 階）退回特別多，再一起提。
- 待決 5（Q12 epic 被動、high_ground 所有模型都退回）：轉給玩法 PM 看題目設計。
- 待決 6（變奏的 `range_delta` 要不要開放給 LLM）：屬於規則決定，轉給玩法 PM 和使用者。
- 待決 7：現在 client 會記錄伺服器的回應本文，下次再出現 400 時再查。
