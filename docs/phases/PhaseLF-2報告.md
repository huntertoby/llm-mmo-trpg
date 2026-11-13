# Phase LF-2 報告｜減少 LLM 閃現不合格要重問的浪費

> 實作 agent，2026-11-13。規格 `docs/phases/PhaseLF計畫.md` 第 4 節。依據 main `d882f34c`（LF-1 已合併）。
> 使用者核可：「都按照建議」（專案 PM 轉達；調查報告 A5 第 2 段）。設計依據 `docs/design/06-技能.md` 6.34.7；`docs/design/` 沒動。
> commit：`ead480ea`（實作＋測試）、`97afafb6`（實機後修正：說明與名稱必填、擋截斷的名稱）、本報告與上手筆記一筆。

## 1. 做了什麼

| 規格 4.1 | 做法 | 檔案 |
|---|---|---|
| 1. 數量不超過目錄 | `FlashCatalog.combinations`（不同的（模板, 參數）組合數）；`want = min(題目選項數, combinations)`。目錄是空的時紀錄照舊（`wanted` ＝ 題目選項數、不呼叫） | `skillgen/flash_catalog.py`、`llm/flash_propose.py` |
| 2. 說明不合格只丟說明 | `judge_items` 改成：說明的字元、長度、一致性、古風詞、世界觀詞不過 → 記 `flash.note_dropped.<原因>`，變化照收。只有結構問題（不在目錄、類別不存在、參數不在選單、多選項的參數沒填、套不上、格式、多餘欄位）才算被拒絕、才重試，而且只為還缺的數量重試；錯誤回饋只列這些 | `llm/flash_propose.py` |
| 3. 本地修正 | 新模組：`repair_fields`（類別填錯改正、單一選項的參數代填、不用填的參數拿掉、代號空白）、`normalize_note`（前後空白、半形標點與數字轉全形、尾巴重複句號、超過 40 字截到最後一個標點）、`normalize_name`；重複的項目直接丟掉。每種記 `flash.repaired.*` | `llm/flash_repair.py`（新） |
| 4. schema 綁參數 | 每個模板一個 `oneOf` 分支：`template`、`category` 是 `const`，參數只列該模板的選單（必填），沒有選單的分支沒有該欄位；`oneof_as_anyof`（預設開）由 `OpenAICompatClient` 改成 `anyOf`。超過 40 個模板退回扁平列舉 | `llm/prompts/flash.py` |
| 5. 限制寫進 prompt | `<request>` 多 `categories`、`choices`（每個模板的參數組合數）；`<catalog>` 每列多 `note_words`（引擎先算 `skill_facts` 差集，給「這個變化會加上的效果」可直接引用的詞）；system 說明 count 上限、同一模板不要重複、category 照目錄填。`FLASH_PROMPT_VERSION` `flash-variation/6` | `llm/prompts/flash.py`、`llm/consistency.py::added_word_choices`、`llm/flash_propose.py::note_words` |
| 6. 詞表 | 風元素補「風屬、風系、風勢、山風、陣風」 | `content/llm/effect_words.yaml` |
| 7. 命名併進提議 | 大變化題目每項帶 `name_zh`；`name_checker`（`naming.check_name`：字數、字元集、禁字、重名、世界觀詞、古風詞＋名稱提到的詞要對得上＋加上的效果要被名稱或同一項說明提到＋「・」最多一個且不在頭尾）過了就寫進 `texts`，`name_texts` 記 `FlashNameRecord(attempts=0)`、不另呼叫；不合格（`flash.name_dropped.*`）、補位的大變化、轉型保底照 LF-1 呼叫命名 | `llm/flash_propose.py`、`llm/naming.py` |
| 8. 評估 | `FlashProposalStats` 多 `naming_calls`、`names_merged`、`notes_dropped`、`repairs`、`mean_round_trips`；`summary_lines` 多「每題往返次數、丟掉的說明、本地修正」（`scripts/eval_flash_llm.py` 照印） | `llm/flash_propose.py` |

**沒改**：`client/`、`content/flash_templates.yaml`、`api/flash_changes.py`、`api/run_schemas.py`、`config/llm.toml`、`docs/design/`。日誌、存檔、戰鬥紀錄格式都沒變（`LOG_FORMAT` 仍是 `trpg-battle-log/119`，三個 `endswith` 測試不用動）。

## 2. 實機後的修正（`97afafb6`）

第一次用本機模型跑「之後」（第 3 節表格的「LF-2 初版」欄）發現兩個品質問題，改完再跑一次（「LF-2」欄）：

1. **名稱被截斷**：schema 的 `name_zh` 有 `maxLength: 12`，語法約束把模型想寫的長名稱從中間切掉，出現「焰息・延燒一瞬・雲嶺版・」「餘燼不熄・延燒一息・山霧」這種剛好 12 字、結尾是「・」的名稱，而且都過得了命名檢查。改成：schema 不設名稱長度上限（太長的由檢查丟掉、照 LF-1 另外命名）；提議時取的名稱另外要求「・」最多一個、不在頭尾（`name_zh.dots`）；prompt 照命名步驟的寫法要求兩到六字、句式多樣、不加地名或「版」。
2. **大變化題目常沒寫說明**：`note_zh` 原本是選填，模型在大變化題目多半只填名稱。改成 schema 必填（不合格照樣只丟說明）；大變化的 `name_zh` 也必填。

## 3. 本機 LLM 前後對照（唯讀、小樣本）

- 模型：LM Studio `100.87.188.89:1234`、`swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp`、`reasoning_effort = "none"`（`localhost:8001` 沒回應）。設定放 worktree 的 `config/llm.local.toml`（gitignored，沒有 commit）。
- 題目：和調查報告 B.2 同一組——7 招（火焰箭、餘燼烙印、迎頭痛擊、暗影突襲、回春、普攻精通、堅壁姿態）× 3 種題目（第 1 次不指定、指定最後一個可用類別、第 3 次大變化），角色 2 階、雲嶺、長劍。21 題中 3 題目錄是空的（修正型與姿態的大變化），不呼叫模型。
- 路徑：遊戲同一條 `make_offer(LlmFlashSource(client, naming=client))`；「LF-1（之前）」用 `git archive` 匯出的 main `d882f34c` 原始碼跑，同一支腳本。
- 只量正確性與效率，沒有做任何平衡數值量測。

| 指標（18 題有呼叫模型） | LF-1（之前） | LF-2 初版 | **LF-2** |
|---|---|---|---|
| 模型提議的項目 | 89 | 55 | 55 |
| 被拒絕（要重問）的項目 | 35（39%） | 0 | **0** |
| 　錯誤碼：重複 `flash.duplicate`（每次嘗試同碼算一次） | 17 | — | — |
| 　錯誤碼：說明不合格（同上） | 10（`missing_added` 8、`effect_mismatch` 2） | — | — |
| 說明不合格只丟說明 | — | 1 | 5（`effect_mismatch` 3、`missing_added` 1、`world_terms` 1） |
| 本地修正 | — | 0 | 0 |
| 來源：模型湊滿／部分／全模板 | 11／7／0 | 18／0／0 | **18／0／0** |
| 提議呼叫 | 38 | 18 | **18** |
| 命名呼叫 | 17 | 3 | **6** |
| 往返合計（每題） | 55（3.06） | 21（1.17） | **24（1.33）** |
| 提議時取好、直接用的名稱 | — | 12 | 12 |
| 每題耗時 平均／中位／最長 | 5.2／4.3／11.9 秒 | 2.4／2.6／5.1 秒 | **2.5／2.4／6.5 秒** |
| 大變化題目 平均／最長 | 10.2／11.9 秒 | 4.1／5.1 秒 | **4.6／6.5 秒** |
| 21 題總耗時 | 94.1 秒 | 43.9 秒 | **45.7 秒** |
| 63 個選項中帶描述的 | 55 | 44 | 51 |

對照調查報告 B.2（同一組題目、當時 4-L11 的程式）：94 項被擋 42 項（45%）、40 次提議呼叫、每題平均 5.6 秒；這次的「之前」是 89 項被擋 35 項（39%）、38 次。

說明：

- 被拒絕歸零主要來自第 1 點（指定類別時只要目錄有的數量：火焰箭費用類要 2 個、餘燼烙印／暗影突襲／回春的指定類別只要 1 個）和第 2 點（說明不再擋變化）；schema 綁參數後模型沒有犯任何可修的錯，所以實機的本地修正是 0（Mock 測試涵蓋每一種修正）。
- 命名呼叫剩下的 6 次：3 次是轉型保底（模型沒有提議，照 LF-1 命名），3 次是提議時的名稱沒過檢查或沒給的大變化。
- 大變化名稱（LF-2）：火焰箭「燃嶺／驚雷／燎原／竹火」、迎頭痛擊「餘燼不滅／雲光一擊／霧鎖寒鋒／潮湧重擊」、回春「凝霜迴光／霧沼靈光／靜岳守形／長明迴響」。LF-1 的名稱例：「雲間灼影／竹梢驚雷火／霧鎖焚心／鶴唳燎原」。
- 腳本與原始輸出在 agent 的 scratchpad `lf2/`（`bench.py`、`before.json`、`after.json`、`after2.json`、`summ.py`），沒有放進 repo。沒有開 `trpg serve`，沒有占用任何埠。

## 4. 測試與檢查（結束碼）

| 指令 | 結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `pytest -n 8` 相關檔（`tests/llm` 全部、閃現相關的 roguelite／world／api／skillgen、`tests/cli/test_run_cli.py`、`test_llm_propose_cli.py`、`test_architecture.py`） | 0（532 passed） |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/roguelite/test_flash_llm_run.py tests/llm/test_flash_propose.py` | 0（897 passed） |
| `trpg battle --map open_plain --seed 7 --log-json …`＋`trpg battle replay` | 0／0（91 個動作、383 個事件，一致） |

新測試 `tests/llm/test_flash_lf2.py`（10）：重複＋類別填錯＋單一參數漏填＋多填參數＋代號空白＋說明超長一次修好、不重試（4.3 第 1 點）；說明的半形、句號、截斷、名稱間隔號；英文與半形空白的說明只丟說明、結構錯誤才為還缺的數量重試（第 2 點）；合格說明留下；指定費用類只有 2 個組合時 `wanted == 2`、`source == "llm"`、prompt 的 `count`／`categories`／`choices`（第 3 點）；prompt 帶 `note_words`；大變化提議時的名稱直接用、不合格的名稱照 LF-1 另外命名、統計記 `names_merged`；小變化題目忽略名稱；統計的往返、丟掉的說明、修正；「・」規則。
既有測試改寫：`test_flash_propose.py`（schema 改成分支＋新的分支快照與 `oneof_as_anyof` 兩種設定、扁平退路、版本 `/6`、被擋的項目表拿掉現在會本地修正或只丟說明的四種、重複改記修正碼）、`test_consistency.py`（說明不一致只丟說明；風的同義詞）、`test_flash_note_archaic.py`（古風詞只丟說明）、`test_prompt_prefix.py`（讀分支的模板）、`test_architecture.py`（`name_checker` 比對全部內建技能名，同 `name_skill` 加進白名單）。

快照與夾具：預測不會變——Mock 回應的項目本來就合格、不帶說明與名稱，也不看 prompt 與 schema；`wanted` 只在指定類別且目錄組合數少於 3 時變小，Mock 本來就挑不超過目錄的數量。實際沒有任何快照、parity 夾具或 CLI 輸出測試失敗，沒有重產。

## 5. 待 PM 決定（都照最保守的做法先做了）

1. **大變化題目仍要 4 個**：其中一格之後讓給轉型保底，第 4 個提議用不到（每題多寫一項，不多一次往返）。要省可以改成「有轉型保底時要 3 個」，但轉型保底是否存在要在提議前先算一次。
2. **目錄是空的時紀錄的 `wanted` 照舊**（＝題目選項數），沒有改成 0，以免動到既有紀錄。
3. **`note_zh` 與大變化的 `name_zh` 改成 schema 必填**（規格沒寫）：實機初版大變化題目多半沒寫說明（第 2 節）。不合格照樣只丟文字，不會因此重試。
4. **`name_zh` 的 schema 不設長度上限**，改由檢查擋超過 12 字的；另外提議時取的名稱要求「・」最多一個、不在頭尾（命名步驟本身沒有這條，所以不合格時照 LF-1 另外命名，名稱品質不會比 LF-1 差）。
5. **說明的半形數字轉全形**（「多燒1回合」→「多燒１回合」）：規格的「全形／半形」修正照字面做；prompt 仍要求不寫數字。要改成「有數字就丟說明」的話改一行。
6. **風的同義詞多加了「風系」「陣風」**（規格例子是「風屬、風勢、山風」）：只是同義詞、不改規則；玩法 PM 要收緊可以刪。
7. **類別修正不看模型填的類別存不存在**：只要模板在這次的目錄裡，類別一律改成目錄的那一類（例：`range_plus` 配「race_orc」也會改成 `area`）；模板不在目錄裡的照舊被擋。
8. **修正碼和丟文字的代碼放在 `FlashProposalRecord.codes`**（和被拒絕的錯誤碼同一個 tuple，被拒絕的在前），沒有新增紀錄欄位，所以紀錄格式不變；`rejected` 只列結構錯誤的模板。
9. **`flash-variation/6` 在本段內改了兩次**（第 2 節的修正），沒有升 `/7`：本段尚未合併、沒有任何紀錄用到初版。

## 6. 需要使用者決定

無。

## 7. 平衡疑慮

無（只改 LLM 怎麼提議與文字怎麼檢查；變化的結構、預算與數值不動，沒有做任何數值量測）。

## 8. 沒驗證

- 大世界實機（`trpg serve`＋預先生成＋10 秒等待）沒有用真模型跑；大變化題目從約 10 秒降到約 5 秒，預期更少退回模板，但沒有實測。
- 只量了一個模型（Qwen 3.8 27B）；Gemma 等其他模型對 `oneOf`／`anyOf` 分支的遵守程度沒有量。
- 前端顯示描述是 LF-3。

## 開發 PM 裁定

- 接受，已合併。前後對照：被拒絕要重問的項目 39% → 0，每題往返 3.06 → 1.33，21 題總耗時 94 → 46 秒。只量正確性與效率，沒有做數值量測。
- 待 PM 決定 1～9 全部照 agent 的做法維持。其中 note_zh、大變化 name_zh 改成 schema 必填，是依實機結果加的，接受。
- 第 10 點是檢查放寬：`tests/test_architecture.py` 的白名單加了 `name_checker`，理由和既有的 `name_skill` 相同，都要比對全部內建技能名來避免撞名。接受；專案 PM 指示 push 後回報範圍與理由。
