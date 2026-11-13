# graphify 試用報告（2026-11-13）

> 使用者核可一次小試用（原話「適用」，專案 PM 轉達）。只做研究，沒改程式；試用完已 `uv tool uninstall graphifyy`。
> 工具：github.com/Graphify-Labs/graphify（PyPI `graphifyy`），試用版本 v0.9.108。

## 結論（先講）

**現在不值得正式用。** 對我們最常見的「找程式位置」題目，graphify 沒有比 Grep／Read 省 token，準確度反而較差：

- 我們的關鍵路徑大多是**資料驅動或執行期才接上的**（YAML → `ContentLibrary`、世界引擎 `supply` → 背景佇列 → 生成函式、Python API → TS 前端），AST 圖接不起來，`path` 只會繞經 `ContentLibrary` 這類大樞紐給出沒意義的路。
- 自然語言查詢靠關鍵字比對節點名，中文概念詞（閃現、許願池、重閃）完全對不上，第一題甚至跑到帳號系統。
- 圖很大、很慢：建圖 5 分鐘、圖檔 92 MB，每次查詢光讀圖就 20 秒，沒改檔的增量更新也要 4 分鐘。
- 上手筆記（`docs/dev/上手-*.md`）已經把各塊的入口與檔案列好，agent 讀筆記＋Grep 就到得了；graphify 補不到筆記沒寫的東西。

如果之後要再評估，比較可能有用的是 `affected`（反向找呼叫者，像「改了 `power_floor` 會影響誰」），但 `rg "power_floor\("` 也能做到。

## 一、試用方式

- 安裝：`uv tool install graphifyy`（15 秒）。
- 建圖：`GRAPHIFY_BACKEND=none GRAPHIFY_QUERY_LOG_DISABLE=1 graphify extract . --code-only`，輸出在 worktree 的 `graphify-out/`（沒 commit）。
- 沒有執行 `graphify install`、`graphify hook install`、`claude install`、`cluster-only`／`label`（這兩個會呼叫 LLM 命名分群）；沒有寫任何 skill、CLAUDE.md、設定檔或 `~/.claude`。
- **確認不外送的依據**（讀原始碼 `graphify/cli.py`、`llm.py`、`querylog.py`）：
  - `--code-only` 會丟掉文件、圖片（本次 1217 份文件、2968 張圖），只做本機 tree-sitter AST。
  - `GRAPHIFY_BACKEND=none` 讓每個 LLM 步驟（語意抽取、LLM 去重、分群命名）都停用。**沒設時它會自動偵測後端，連 `claude` CLI 在 PATH 上都會被當成 `claude-cli` 後端**，所以兩個都要設。
  - `extract` 的分群命名用 `label_communities_by_hub`（本機、依樞紐節點名）；查詢日誌預設關閉，`GRAPHIFY_QUERY_LOG_DISABLE=1` 再保險一次。
  - 套件內沒有遙測；會連網的只有 `add <url>`、`clone`、`--google-workspace`、`--postgres`、Neo4j／FalkorDB 匯出與各 LLM 後端，本次都沒用。

## 二、建圖成本

| 項目 | 數值 |
|---|---|
| 掃到的檔 | 3384 個程式檔（含 `tests/`、`scripts/`、`client/`；`content/` 的 YAML 沒有符號） |
| 圖 | 78,567 個節點、231,489 條邊、1,580 個分群 |
| 建圖時間（全新） | 5 分 05 秒（16 個 worker） |
| 增量更新（沒改任何檔）`graphify update .` | 4 分 02 秒（重分群、重寫 `graph.html` 與報告） |
| 每次查詢 | 約 20 秒（每次重讀 92 MB 的 `graph.json`） |
| `graphify-out/` 大小 | `graph.json` 92 MB、`.graphify_analysis.json` 4.5 MB、`manifest.json` 0.8 MB，加 `cache/` 共約 197 MB |

## 三、三題對照

**估算方法**：Grep／Read 那一欄是我實際讀進來的工具輸出字元數（Grep 結果與 Read 的行數加總）；graphify 那一欄是查詢輸出檔 `wc -c`。換算 token 用約 3 字元 ≈ 1 token（中英混雜的程式碼與註解）。兩邊都沒算我自己下指令的字數。順序是先做 Grep 再做 graphify，所以 graphify 的關鍵字查詢有借用 Grep 學到的符號名（對 graphify 有利）。

| 題目 | Grep／Read | graphify |
|---|---|---|
| (a) 閃現模板：讀檔 → 前端顯示 | 5 次呼叫、約 10k 字元（≈3.3k token）。**完整**：`content/library/tables.py:132-153` 讀 `flash_templates.yaml` 成 `FlashTable` → `ContentLibrary.flash`（`library/container.py:97`）→ `skillgen/flash_offer.py` 出題 → `api/run_presenter.py:256 _pending` 用 `flash_changes`、`flash_text.option_headline`／`option_say`／`flash_terms` 組 `PendingFlashOut`（`run_schemas.py:482`）→ `client/src/screens/RunFlashPending.tsx` 讀 `run.pending_flash`。 | 3 次查詢、約 9.3k 字元（≈3.1k token）。自然語言查詢（2.3k 字元）**完全錯**：跑到 `server/accounts.py`。帶 Grep 學來的符號名（7k 字元）找到 `FlashTable`、`load.py`、`PendingFlashOut`、`option_headline`，但被截斷在 2000 token、沒有邊；`path FlashTable → RunFlashPending()` **找不到路**（Python 與 TS 之間沒有邊）。前端那一段還是要 Grep。 |
| (b) 許願池：API → LLM 提議 | 5 次呼叫、約 11k 字元（≈3.8k token）。**完整**：`api/routes/world.py`（動作；等待用 `wish_wait_request` 在 :416）→ `world/step.py:525` 分派 `apply_wish` → `world/wish.py:203 supply(WishGenRequest…)` → `api/world_pregen.py` 佇列（`URGENT_KINDS` 插隊）→ `wish_generator`（:213）→ `llm/wish.match_wish` 對關鍵字 → `LocalLlmProvider.wish_source`（`api/llm_source.py:143`，`make_proposer(…, player_text=wish)`）→ `make_offer`。 | 2 次、約 7k 字元（≈2.3k token）。自然語言查詢**找到核心的一半**：`wish_generator`、`match_wish`、`WishSource`、三個 `wish_source`、`WishGen`／`WishGenRequest`；約 7 成輸出是無關的 `client/src/api/types.ts` 型別。**漏掉** routes、`step.py` 分派、`apply_wish`、`supply`（執行期經回呼接上，AST 看不到）。`path apply_wish → match_wish` 給「都引用 `ContentLibrary`」這種沒意義的 2 跳。 |
| (c) 重閃的強度下限在哪判斷 | 3 次呼叫、約 14k 字元（≈4.7k token；一次 Grep「下限｜floor」輸出大）。**完整**：值的來源 `skillgen/flash_offer.py:520 _replaced_floor`（被換掉那一筆的預算分數 ‰ 進位，歷程重推不了改 :539 `_fallback_floor`）→ 存進選項／`FlashRecord.floor_permille`（`flash_state.py:93`）→ `flash_derive.py:222 power_floor` 取 max（`STRICT_OPS` 再加 `STRICT_MARGIN`；轉型不設下限）→ 檢查在 `flash_major.fixed_strength`（:605）、預算重調 `floor=`、`flash_trade`；重推時 `derive_chain`（:510）讀回 `floor_permille`。 | 3 次、約 11.6k 字元（≈3.9k token）。自然語言查詢**挑錯**：`power_floor()` 對到 `scripts/budget_knob_audit.py`，其餘是前端重閃 UI 與裝備詞條。`explain` 因同名有兩個而報歧義；換成完整路徑的 `affected` 給出正確的呼叫者（`apply_variation`、`derive_chain`、`derive_on_current`、`_apply_transform`、`_substitute`），但 8 成是測試；**漏掉** `flash_offer._replaced_floor`／`_fallback_floor`（下限值真正算出來的地方，不是 `power_floor` 的呼叫者）。而且要先知道符號名才問得對。 |

**小結**：token 量兩邊差不多（graphify 沒有明顯省），但 graphify 三題都需要 Grep 補洞，而且自然語言查詢三題有兩題起點挑錯。Grep 的優勢是能搜中文註解（「下限」、「許願」），我們的程式註解剛好寫得很密。

## 四、如果要用，怎麼裝才不干擾平行合併

我們常有 3～4 個 agent 在各自的 worktree 平行做、PM 在主資料夾合併。若真要用：

1. **不要裝 git hook（`graphify hook install`）**。原因：
   - hook 寫在共用的 `.git/hooks`（所有 worktree 共用），會在 post-commit、post-checkout、post-merge、post-rewrite 觸發。它內建「linked worktree 就跳過」，所以實際只在**主資料夾**重建——也就是 PM 每次合併、每次 checkout 都在背景跑一次 4～5 分鐘的 16 worker 重建，和 PM 的全量測試搶 CPU（守則 11 規定全量期間不跑其他重工作）。
   - 它的 merge driver 會改 `git config`（`merge.graphify.*`）與 `.gitattributes`，等於改共用設定。
2. **`graphify-out/` 不進版控**，放進 `.gitignore`（現在沒有忽略，試用時是 `??`）。92 MB 的 JSON 進版控會讓每次合併都衝突，而且 worktree 的圖只反映該分支。
3. **要用就由 PM 在主資料夾手動建一份**（`--code-only`＋`GRAPHIFY_BACKEND=none`，例如每段合併後），agent 用 `--graph <主資料夾>/graphify-out/graph.json` 唯讀查詢。不在 worktree 各建一份（每份 5 分鐘、200 MB）。
4. 不執行 `graphify install`／`claude install`（會寫 skill、CLAUDE.md 段落與 PreToolUse hook，等於改 agent 行為與設定）。

## 五、風險

- **資料外送**：預設會自動偵測 LLM 後端（環境變數裡的 API 金鑰，或 PATH 上的 `claude` CLI），沒加 `--code-only`／`GRAPHIFY_BACKEND=none` 就會把文件送出去做語意抽取；`cluster-only`、`label` 也會呼叫 LLM。要用必須把兩個開關寫死在包裝腳本裡，不能靠每個 agent 記得。
- **圖過期**：增量更新也要 4 分鐘，平行開發時主資料夾的圖幾乎一定落後各 worktree 的分支；agent 拿到舊行號或已改名的符號，比 Grep 現場搜更容易誤導。
- **額外維護**：多一個工具版本要追（這個專案更新很頻繁，CLI 參數多）、200 MB 輸出要清、每次合併後要記得重建；還要教 agent 何時用、用哪些參數（`--budget`、`path::symbol` 消歧義）。
- **磁碟與 CPU**：16 個 worker 跑 5 分鐘，會拖慢同時在跑的測試或模擬。

## 六、清理

- 試用結束執行 `uv tool uninstall graphifyy`，解除了 `graphify`、`graphify-mcp` 兩個執行檔；`uv tool list` 已沒有 graphifyy、`which graphify` 找不到。
- `graphify-out/` 留在試用 worktree 沒有 commit（只 commit 這份報告）；worktree 清掉時一起刪。
