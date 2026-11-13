# Phase LF 計畫｜LLM 閃現：名稱與描述進遊戲、記進日誌、減少白白重問

> 開發 PM 派的規格＋實作 agent 起草（2026-11-13）。使用者核可（專案 PM 轉達）：「都按照建議」——指 `docs/phases/LLM閃現調查報告.md` A5 的第 1、2 段（名稱與說明接進遊戲、減少白白重試），本規格另把前端顯示拆成第 3 段。
> 實作者先讀 `docs/dev/上手-LLM.md`（LF-1 新開），閃現規則看 `docs/dev/上手-內容資料與模擬.md` 第四節第 35～41 點。
> 設計依據：`docs/design/06-技能.md` 6.34.3～6.34.5（閃現流程、小變化不改名、大變化與轉型改名）、**6.34.7「LLM 的角色」**（提議變化內容與名稱、預先生成、10 秒退回、只把最後給出的版本記進日誌、重播不呼叫 LLM、名稱照原技能的界域）；`CLAUDE.md` 守則 1、3、6、7。
> **不改 `docs/design/`**；和設計有出入、或要使用者決定的地方列在第 7、8 節，先照最保守的做法做。

## 0. 現況（實作前讀程式確認，2026-11-13 main `251eff3b`）

| 項目 | 現況 | 出處 |
|---|---|---|
| LLM 在閃現裡做什麼 | 只從引擎算好的目錄挑「類別＋模板＋參數」；寫的一句話 `note_zh` **只拿來檢查、然後丟掉** | `src/trpg/llm/flash_propose.py`（`judge_items`、`_Loop`） |
| 名稱 | 選項名稱一律「{前綴}・{原名}」（大變化、轉型）或原名（小變化）；LLM 命名步驟 `name_offer` 只有評估工具 `flash_eval.py` 用，**遊戲沒呼叫** | `skillgen/flash_derive.py::flashed_identity`、`llm/flash_propose.py::name_offer` |
| 名稱能不能留住 | 就算命名了也留不住：閃現後的技能每次由「原技能＋變化歷程」重推（下一次閃現、升階 `roguelite/retier.py`、傳承），名稱由 `flashed_identity` 從歷程算，歷程裡沒有名稱 | `flash_derive.derive_skill` |
| 預先生成、10 秒退回 | **已經有**（6L-2）：`api/world_pregen.py` 背景單一佇列、暫存只在記憶體、`WAIT_SECONDS = 10`、等待提示 `POST .../pregen/wait`；世界引擎經 `world/generated.py::supply` 拿紀錄，最後給出的版本記進 `WorldLogEntry.generated`，重播用 `recorded()` 不呼叫 LLM | `world/generated.py`、`world/growth.py::_flash_source` |
| roguelite | 沒有預先生成（同步呼叫）；提議紀錄存 `RunState.flash_llm_log`，選項連同套用後的技能存 `pending_flash`，讀檔不再呼叫 LLM | `roguelite/flashes.py::open_flash` |
| 白白重試 | 實測 94 項提議被擋 42 項（45%）：`flash.duplicate` 18（指定類別時目錄只剩 1～2 個模板卻要 3 個）、`note_zh.missing_added` 11（部分誤擋，例「風屬傷害」不在詞表）、`effect_mismatch` 3；被擋的理由**全是說明文字或重複**，而說明文字根本不顯示 | `LLM閃現調查報告.md` B.2 |
| 結構化輸出 | 已用 JSON schema（`response_format`），但 schema 是「全目錄的扁平列舉」，模板和它的參數選單沒有綁在一起 | `llm/prompts/flash.py::flash_schema` |

## 1. 範圍總覽

| 段 | 內容 | 依賴 | 撞檔注意 |
|---|---|---|---|
| **LF-1** 後端核心 | 名稱與描述的資料流：變化帶文字、提議紀錄帶文字、選項與推出的技能用 LLM 名稱、升階與下一次閃現留得住；大變化與轉型呼叫命名步驟；世界日誌記下、重播只讀日誌；世界日誌格式升版 | 無 | 不動 `client/`、`content/flash_templates.yaml`、`api/flash_changes.py`、`api/run_schemas.py`（FL-1b 進行中） |
| **LF-2** 減少不合格重問 | 題目數量不超過目錄、說明文字不合格改成「丟掉說明、留下變化」、本地修正可修的錯、schema 依模板綁參數、限制寫進 prompt、命名併進提議呼叫（少一次往返）；評估工具輸出前後對照 | LF-1 | 只動 `src/trpg/llm/`、`skillgen/flash_catalog.py`、相關測試 |
| **LF-3** API 與前端顯示 | `FlashOptionOut` 加 `note_zh`、`name_source`（只加新欄位）；閃現選項卡片顯示 LLM 名稱來源與一句話說明；等待提示文字；PM 重產 OpenAPI；本機 LLM 實機截圖 | LF-1、FL-1b 合併後 | `client/`、`api/run_schemas.py`、`api/run_presenter.py` |

許願池（07 7.6、#88）**不在本規格**；第 2 節只說明這套流程怎麼留給它共用。

## 2. 共用的「LLM 出招流程」（給閃現、劇情技能、機遇、之後的許願池）

現有的三個入口已經各自長成同一個形狀，本計畫把它寫明、閃現照它補齊，許願池之後照抄：

```
請求（純資料，含完整輸入 → 鍵 input_key）
  → [API 層] 預先生成佇列（world_pregen：單一佇列、只放記憶體、預測錯了只是沒命中）
       └ 生成函式：提示（限制寫進 prompt）→ LLMClient.complete(json_schema) → clean_response
                   → JSON／pydantic → 本地修正 → 引擎驗證（守則 3）→ 不合格帶錯誤回饋重試（≤ max_retries）
                   → 紀錄（來源 llm／partial／template、嘗試次數、錯誤碼、結構、文字）
  → [世界引擎] supply(request, 種類, 退路, accept)：等最多 10 秒；種類或鍵不對、accept 不收 → 退路
       └ 最後給出的版本收進動作的 generated 清單 → 日誌 WorldLogEntry.generated
  → [重播] recorded(日誌紀錄) 當供應者，不呼叫 LLM；舊日誌沒有紀錄 ＝ 退路
```

約定（LF-1 落實到閃現；許願池照用）：

1. **紀錄分兩層**：結構（引擎會套用、決定強度的東西，例：閃現的 `Variation`）與 **文字**（名稱、一句話描述；只影響顯示）。文字用獨立的型別（閃現是 `skillgen.flash_text.VariationText`，以結構的穩定鍵對應），讓「文字不合格」只丟文字、不丟結構。
2. **引擎照樣驗證文字**：文字從日誌或暫存讀進來時，引擎用純函式（字數、字元集、禁字）再檢查一次，不合格的欄位當作沒有（退回組合式名稱或模板說明）；LLM 不能經由文字改到任何數值或結構（守則 3）。
3. **文字跟著結構存**：會被重推的東西（閃現的變化歷程）要把文字存在歷程裡，否則升階、下一次閃現就掉回組合式名稱。
4. **沒有值時不輸出**：新欄位一律 `exclude_if` 空值，沒有 LLM 文字的存檔、日誌、規則包雜湊逐字不變。
5. **許願池怎麼接**（之後另排，不在本規格）：新增一種 `GenRequest`／紀錄種類（例 `wish`）；玩家願望放進 `<player_input>`（守則 7），只進 prompt、不進鍵以外的任何引擎輸入；提議走完整技能管線（`candidate_source`／`propose.py`），文字走同一套文字型別與檢查；預先生成可以不用（玩家當場許願，照 10 秒退回選單版）。`world_pregen.Generators` 多一個欄位即可，佇列、等待、日誌、重播都不用改。

## 3. LF-1 後端核心（本次實作）

### 3.1 要做的

1. **變化帶文字**（`skillgen/flash_state.py::Variation`）：加選填 `name_zh`、`note_zh`（`exclude_if` 為 `None`）；`key()` **不含**文字（子亂數、去重、合併照舊）。所以閃現狀態、變化歷程、一輪存檔、角色存檔在沒有文字時逐字不變。
2. **文字型別與檢查**（新檔 `skillgen/flash_text.py`）：`VariationText{key, name_zh?, note_zh?}`；`clean_text(variation, text)` 回傳套上合格文字的變化：
   - 名稱：只給大變化、轉型（設計 6.34.3「小變化不改名」）；全形中文與「・（）」、長度 ≤ `naming.name_max_chars`（12）、不含禁字。
   - 描述：全形中文與全形標點、≤ 40 字（同 `prompts/flash.py::NOTE_MAX_CHARS`，測試鎖兩者相等）、不含英文與禁字。
   - 不合格的欄位丟掉（不丟變化）。
3. **出題時套文字**（`skillgen/flash_offer.py`）：來源可選擇提供 `texts(library, request) -> Mapping[鍵, VariationText]`（沒有這個方法＝沒有文字）；`make_offer` 先拿提議、再拿文字，`_Builder.option` 套用前用 `clean_text` 把文字掛到變化上，所以 **提議的、補位的、轉型保底** 只要鍵對得上都能有文字。`has_options`、`category_counts` 不看文字。
4. **名稱留得住**（`flash_derive.flashed_identity`）：最後一個大變化或轉型的那一筆若有 `name_zh`，名稱用它；沒有照舊「{前綴}・{原名}」。ID 的雜湊本來就涵蓋整筆歷程（有文字時 ID 跟著不同；沒有文字時不變）。
5. **LLM 端**（`llm/flash_propose.py`）：
   - `judge_items` 把合格項目的 `note_zh` 收進文字表（目前檢查完就丟）。
   - `LlmFlashSource` 加 `naming` 參數（client 或依（技能, 種子）建 client 的函式；`None`＝不命名）：提議完用同一份請求、只用提議的結構（純函式 `make_offer`）出一次題，對大變化與轉型選項呼叫既有命名步驟 `name_skill`（照原技能的區域與武器，#126），名稱寫進文字表；沒有描述的那一項，命名的 `concept` 合格（≤ 40 字等）時當描述。
   - `FlashProposalRecord.texts`（新欄位）；`LlmFlashSource.texts()`、`RecordedSource.texts()` 依標籤讀。
   - `LocalLlmProvider.flash_source`、CLI `trpg run --llm` 開命名（同一個 client）；Mock 預設不命名（不動既有快照），`mock_flash_source(..., naming=True)` 用 `mock_naming_client`。
6. **一輪與大世界的紀錄**：`roguelite.state.FlashLlmRecord` 加 `texts`（`exclude_if` 空）；`world/growth.py::_flash_source` 的紀錄來源連文字一起給 `make_offer`。世界引擎照樣驗證（`clean_text`）。
7. **格式版號**：世界日誌 `WLOG_FORMAT` 升 `trpg-wlog/10`（`/9` 照讀，寫回時標頭改 `/10`；照 6L-2、6T-1a 前例：紀錄多了選填欄位就升）。戰鬥紀錄 `LOG_FORMAT` **不升**：戰鬥紀錄只內嵌技能定義，`SkillDef` 的結構沒變（名稱本來就是字串欄位）。角色 `trpg-char/13`、一輪 `trpg-run/13` **不升**：新欄位沒有值時不輸出，舊檔逐字照讀（列待 PM 決定 1）。`WORLD_RULES_VERSION` 不升：舊日誌沒有文字，重播結果逐字相同。

### 3.2 要改的檔

`src/trpg/skillgen/flash_state.py`、`flash_text.py`（新）、`flash_offer.py`、`flash_derive.py`；`src/trpg/llm/flash_propose.py`；`src/trpg/roguelite/state.py`；`src/trpg/world/growth.py`、`world/save.py`；`src/trpg/api/llm_source.py`；`src/trpg/cli/run_llm.py`；測試 `tests/skillgen/test_flash_text_lf1.py`（新）、`tests/llm/test_flash_texts_lf1.py`（新）、`tests/world/test_flash_texts_world_lf1.py`（新）與用到 `trpg-wlog/9` 字面的既有測試。

### 3.3 驗收

1. 提議的變化帶描述、大變化與轉型帶名稱時：選項的技能名稱是 LLM 名稱、變化帶描述；選了之後 **再閃一次、升階重配（`retier`）** 名稱仍在（Mock 測試）。
2. 文字不合格（英文、超長、禁字、小變化帶名稱）→ 只丟那個欄位，變化照常；結構不合格照舊退回模板。
3. 大世界：同一角色走一次閃現（Mock 命名開）→ 日誌那一筆的 `generated` 帶文字；用 `loads_log` 讀回、`replay` 裝會報錯的供應者，`pending_flash` 逐字相同（重播不呼叫 LLM）。
4. 沒有文字的紀錄、舊日誌（`/9`、`/8`、`/7`）照讀，結果和 LF-1 以前逐字相同；沒有文字時閃現狀態與 `FlashLlmRecord` 的 JSON 逐字不變（`exclude_if`）。
5. 引擎匯入方向不變（`lint-imports`、`tests/test_architecture.py`）；所有測試用 Mock、不需要網路。
6. 交件前：`ruff check`、`ruff format --check`、`mypy`、`lint-imports`、直接相關測試、一場 `trpg battle` 紀錄＋重播。

### 3.4 不做

- 前端與 API 欄位（LF-3）。
- 小變化改名（設計 6.34.3 定為不改名；第 8 節問使用者）。
- 命名的 `cast_flavor` 與 `concept` 寫進技能敘事（只取名稱與一句描述；第 7 節待決 3）。
- 重問的改善（LF-2）。

## 4. LF-2 減少不合格重問

### 4.1 要做的

1. **題目數量不超過目錄**：`want = min(題目選項數, 目錄裡不同的（模板, 參數）組合數)`；指定類別時常只有 1～2 個，不再逼模型重複（調查報告 `flash.duplicate` 18 次）。
2. **說明不合格只丟說明**：`note_zh` 的一致性、字數、古風、世界觀詞檢查不過時，留下變化、丟掉說明（記錯誤碼 `flash.note_dropped.*` 供統計），**不再為說明重試**；只有結構問題（不在目錄、參數不在選單、套不上、重複）才重試，而且只為「還缺的數量」重試。
3. **本地修正可修的錯**（不送回模型）：
   - 模板唯一對應類別時，類別填錯直接改正；
   - 參數選單只有一個值而沒填時補上；不用填卻填了時拿掉；
   - 全形／半形、前後空白、說明尾巴的句號重複、超過 40 字截到最後一個標點（截完仍要過檢查）；
   - 重複的項目直接丟掉（不算錯）。
   每一種修正記一個代碼（`flash.repaired.*`），評估工具統計。
4. **結構化輸出綁參數**：schema 改成「每個模板一個 `oneOf` 分支」，分支裡 `template` 是 `const`、`category` 是 `const`、`keyword`／`element`／`shape` 只列該模板的選單（沒有選單的分支沒有該欄位）；`json_schema_mode` 不支援 `oneOf` 時照 `oneof_as_anyof` 設定退成 `anyOf`。模板太多時（> 40 個分支）退回現在的扁平列舉。
5. **限制寫進 prompt**：`<request>` 寫明這次要幾個、哪些類別可用、每個模板有幾個參數選擇；說明的效果詞改給「這個變化會加上的效果」清單（由引擎先算 `skill_facts` 差集，寫成可直接引用的詞），減少 `missing_added`；`FLASH_PROMPT_VERSION` 升版。
6. **詞表誤擋**：`content/llm/effect_words.yaml` 的風元素補「風屬、風勢、山風」這類詞（只加同義詞，不改規則；`tests/llm/test_consistency.py` 加案例）。
7. **命名併進提議呼叫**（減少往返）：大變化題目的 schema 在每項多一個選填 `name_zh`；模型給了而且通過 `check_naming`（字數、字元集、禁字、重名、古風）就直接用，不另呼叫 `name_skill`；轉型保底（模型沒有提議）照 LF-1 另外命名。
8. **評估**：`trpg llm flash-eval`（或現有評估指令）多印「每題往返次數、被丟掉的說明數、本地修正數、命名呼叫數」；用本機 LLM 跑**一次小樣本**（7 招 × 3 種題目，同調查報告 B.2）前後對照寫進報告，不做大量呼叫。

### 4.2 要改的檔

`src/trpg/llm/flash_propose.py`、`llm/prompts/flash.py`、`llm/consistency.py`（只在需要時）、`skillgen/flash_catalog.py`（目錄組合數）、`content/llm/effect_words.yaml`；測試 `tests/llm/test_flash_propose.py`、`tests/llm/test_prompts.py`（prompt 版本快照）、`tests/llm/test_consistency.py`。

### 4.3 驗收

1. Mock：故意重複、類別填錯、參數漏填單一選項、說明超長的回應 → 不重試就湊滿；`codes` 有對應的修正碼。
2. Mock：說明不合格的項目留下、說明為空；結構不合格的才重試。
3. 指定類別、目錄只有 2 個組合時 `wanted == 2`，`source == "llm"`。
4. schema 快照：每個分支的參數只列該模板的選單；`oneof_as_anyof` 兩種設定各一個快照。
5. 本機 LLM 小樣本：被擋項目比例、平均往返次數與調查報告 B.2 對照（只是紀錄，不設門檻；數字寫進報告）。

## 5. LF-3 API 與前端顯示（FL-1b 合併後）

1. `api/run_schemas.py::FlashOptionOut` **只加新欄位**：`note_zh: str | None`（這一項的一句話描述；沒有＝前端照舊只顯示 `summary_zh`）、`name_source: Literal["llm", "template"]`（名稱來自 LLM 還是組合式）。`api/run_presenter.py`、大世界的閃現面板共用。PM 重產 OpenAPI 與 `client/src/api/schema.d.ts`。
2. 前端閃現選項卡（FL-1b 的選變體畫面）：名稱下方一行 `note_zh`（樣式照美術 PM 定稿；沒有就不佔位）；`summary_zh`（模板的機制說明）照舊。等待提示文字沿用 6L-2。
3. 技能卡、技能庫顯示 LLM 名稱（名稱已經在技能定義裡，確認沒有地方寫死組合式名稱）。
4. 驗收：Mock 的 API 測試（`tests/api/test_flash_api.py` 類）看到兩個新欄位；前端 vitest；**本機 LLM 實機**一次大世界閃現（含大變化）截圖，名稱與描述都出現（美術驗收每項有截圖）。

## 6. 不做（三段都不做）

- 許願池本身（另排）；閃現開放 LLM 做更多事（加條件、加修正、大變化改走完整技能提議）——調查報告待決 3，交玩法 PM。
- 預先生成的上限、佇列與 10 秒門檻不調（設計已定）。
- 平衡、模擬、量測。

## 7. 待 PM 決定（照最保守的做法先做）

1. **角色、一輪存檔的版號**：`Variation` 多兩個選填欄位、`FlashLlmRecord` 多 `texts`，沒值時不輸出，舊檔逐字照讀；但新檔帶文字時舊程式讀不了。先照「只多選填欄位不升」做（`trpg-char/13`、`trpg-run/13` 不動）；世界日誌照 6L-2 前例升 `/10`。要比照升版的話 LF-2 順手改。
2. **`LOG_FORMAT` 不升**：戰鬥紀錄沒有新欄位（派工說「格式有變就升」，判斷為沒變）。
3. **命名的敘事（`concept`、`cast_flavor`）要不要寫進技能**：LF-1 只取名稱；描述用提議的 `note_zh`，沒有時用命名的 `concept`（≤ 40 字才用）。寫進技能敘事要把兩段文字也存進變化歷程，留給 LF-2 或之後。
4. **名稱重複**：命名步驟擋「和內容庫或同一題其他選項同名」；不擋和玩家自己其他技能同名（請求沒有帶玩家的技能名稱）。LF-2 可把持有者技能名稱加進請求。
5. **命名的延遲**：大變化題目（第 3 次）多 3～4 次命名呼叫（調查報告實測每題約 8 秒、最慢 24 秒），大世界預先生成可能更常超過 10 秒而整題退回模板。LF-2 第 7 點把命名併進提議呼叫後應改善；LF-1 先接受。
6. **roguelite 的 Mock 命名**：`--llm-mock` 預設不命名（不動 CLI 快照）；要不要打開另排。

## 8. 需要使用者決定

1. **小變化要不要也改名**（設計 6.34.3：「小變化不改名稱」；調查報告待決 2）。LF-1 照設計不改名，只給小變化一句描述。
