# Phase HC-1 報告：寫死數值掃描工具與歸類檔

依據：`docs/phases/PhaseHC-1計畫.md`；參考 `寫死數值-盤點初稿.md`、`內容擴充評估.md`、`scripts/x10/fields.yaml` 與 `tests/test_x10_fields.py`。
基準：開工時 `git merge main`（`9a7897f11`）。分支 `worktree-agent-a7004356b5f26dd68`，沒 push。
**沒改 `src/`、`client/` 的任何行為**（只新增 `scripts/hardcoded/`、測試和文件）。沒改 `docs/design/`、`config/`。沒跑全量、沒用 `-m ""`、沒試數值。

## 1. 交付與 commit

| # | 項目 | commit |
|---|---|---|
| 1 | 後端掃描 `scripts/hardcoded/scan_py.py` | `0d472b49c` |
| 2 | 前端掃描 `scripts/hardcoded/scan_ts.py` | `58726ff7a` |
| 3 | 歸類檔 `scripts/hardcoded/classes.yaml`＋歸類程式 `classify.py` | `9564d6b56` |
| 4 | 涵蓋測試 `tests/test_hardcoded_scan.py`（同時小改兩個掃描器：加 `scan_source`、參數預設值算在函式裡） | `ba8f3b91f` |
| 5 | 清單 `docs/phases/寫死數值-清單.md`（由 `classify.py --md` 產生）＋搬家分段 | `a6f653ff5` |

## 2. 工具怎麼用

```bash
uv run python scripts/hardcoded/classify.py --check      # 沒歸類的列出來，結束碼 1
uv run python scripts/hardcoded/classify.py --stats      # 各類筆數（後端、前端分開）
uv run python scripts/hardcoded/classify.py --dump config            # 某一類的 tsv
uv run python scripts/hardcoded/classify.py --unclassified           # 沒歸類的 tsv
uv run python scripts/hardcoded/classify.py --unused                 # 一筆都沒用到的規則
uv run python scripts/hardcoded/classify.py --md docs/phases/寫死數值-清單.md   # 重產清單
uv run python scripts/hardcoded/scan_py.py | scan_ts.py  [--count]   # 只看掃描結果
```

### 掃描範圍
- **後端**（AST）：`src/trpg/**/*.py`。
  - 數字：不列 0、1、-1（含 0.0、1.0）、`range()` 參數、True／False；負數照負數記（`-2`）。
  - 含數字的中文字串：中日韓文字＋數字（0-9、全形０-９）。f-string 只看固定部分，`{...}` 照原樣保留。
  - docstring 與「欄位下一行的說明字串」記成 `docstring`，其他是 `text`。
  - 每筆附：檔、行、`scope`（`Class.method`／`<module>`）、`slot`（`Field(le)`、`=NAME`、`{key}`、`def:param`、`cmp:x`……）、`owner`（所在敘述的指派目標＝欄位或常數名）、`ann`（型別註記）、那一行原文。
- **前端**（不靠 Node 的小型 tokenizer）：`client/src/**/*.ts(x)`，不含 `*.test.*`、`*.spec.*`、`*.d.ts`（`api/schema.d.ts` 是產生的）、`fixtures/`、`client/src/test/`。
  - 數字：同樣不列 0、1、-1。字串裡的 `"12px"`、`"#fff"` 不算字面值，所以不會列。
  - 文字：一般字串、樣板字串、JSX 文字。
  - `slot`：`{key}`、`=name`、`attr=name`（JSX 屬性）、`name()`（呼叫參數）、`[]`、`cmp`、`op:*`、`return`、`?:`。

### 歸類檔的寫法（`classes.yaml` 開頭有完整說明）
- 規則由上往下，**第一條符合的勝出**。
- 條件：`lang`、`files`、`scope`、`where`、`kind`、`slot`、`owner`、`ann`、`value`（都是 fnmatch 樣式），`text`、`context`（正規表示式），`bare_digits`，`not`（排除）。
  - `where`：函式或類別裡的就是 `scope`；模組層的是 `<module>.常數名`。
  - `bare_digits`：字串去掉占位和引用（`#169`、`5.4.1`、`Phase 3D-6`、`BAL-12e`、日期、識別字裡的數字）後還有沒有數字。
- **完全不用行號**。
- 驗證：`class` 只能是五類；`const`／`layout` 一定是 `done`；未知欄位、重複 id、壞的正規表示式都報錯。

### 穩定性（另一個 agent 同時在改 client 與 narrative）
規則的粒度：
- **後端**：`檔＋函式／類別` 或 `檔＋模組常數名`。
  - 既有函式或類別裡改數字、改字串、行號移動：照舊涵蓋，歸類不變。
  - 新的函式、類別、模組常數：測試失敗，要人歸類。這就是「防止再犯」。
- **前端**：大多是檔層級（UI 檔的數字＝layout，玩法副本另列）。
  - 前端文字是列出檔名的 `ts-ui-text`：這些檔裡新增的含數字字串會自動進 text（todo），新檔會失敗。
- **通用樣式規則**不綁檔：‰ 的 1000、HTTP 碼、d20、時間單位、切片與雜湊、量類欄位名。

## 3. 筆數

| | config | scale | const | text | layout | 合計 |
|---|---:|---:|---:|---:|---:|---:|
| 後端 `src/trpg/` | 1416 | 67 | 8818 | 197 | 0 | 10498 |
| 前端 `client/src/` | 56 | 1 | 5410 | 99 | 54752 | 60318 |
| **合計** | **1472** | **68** | **14228** | **296** | **54752** | **70816** |

- **config／scale／text 共 1836 筆**（後端 1680、前端 156），全部 `todo`。
- 沒歸類：0。規則 397 條，都有用到（`--unused` 空的）。
- 大宗的 const／layout：
  - 後端 docstring 6927（const）、‰ 的 1000 共 458、`sim/` 264、`cli/` 152。
  - 前端 `render/` 53370（layout）、`dev/` 4968（const）。
- 各區塊明細和每一筆見 `docs/phases/寫死數值-清單.md`。
  - 第 1 節：筆數。
  - 第 3、4 節：規則表。
  - 第 5 節：config／scale／text 依區塊、檔案列出，每列有行、所在、值、原文、規則、狀態。

### 和盤點初稿的對照
- 初稿 B（量類約 20）→ scale 68。
  - 多出來的是：`content/rules.py` 的資源池與職業基礎、`roguelite.py` 起始英雄、`skillgen/flash_major.py` 與 `composer_recipes.py` 寫死的法力代價。
  - `composer_special.py:263` 已經乘 `scale`（X10-3c），歸 config。
- 初稿 A：`engine/ai`、`flash_ops`、`proposal_costs`、`world_*` 都在 config 裡。
  - 初稿點名的 `skill_tier.py:64` 與 `flash_ops.py:656` 兩份召喚 HP 階梯都在 config，可以在 HC-5 一起合併。
- 前端 A／B／D：初稿列的都有對到。
  - `flash.ts:20`、`flow.ts:50`、`impact.ts`／`vfx.ts`、`affixStatus.ts`、工坊預設、`AttributeAllocator ?? 10`、`growthPanel「每級 +2」` 等。
- **初稿列了但掃描不會列的**：`content/environment.py:372` `min_damage` 預設 1。規格規定不列 0、1、-1，見待決 2。

## 4. 建議的搬家分段（也寫在清單第 2 節）

| 段 | 內容 | 筆數 |
|---|---|---:|
| HC-2 | **量類**：a. content 的量類預設與上下限（rules、forms、battle、roguelite）；b. 生成器寫死的法力代價（flash_major、composer_recipes）；c. 零星（`_MAX_ATTR`、`DEFAULT_DEFENSE_BREAK`、situation_coverage、前端 `?? 10`） | 68 |
| HC-3 | **前端副本改由 API 帶**：a. 閃現與技能欄（FALLBACK、SLOT_LIMITS、SOURCE_MAX、affix、開局關鍵字）；b. 大世界與工坊（背包、walk、鐘點、工坊預設） | 56 |
| HC-4 | **content schema 預設值與上下限**（先定通則，見待決 1）：a. 戰鬥核心；b. 技能規則；c. AI 與環境（含 `engine/ai`）；d. 大世界 | 約 990＋engine/ai 50 |
| HC-5 | **技能生成常數**：a. 閃現 `flash_*`；b. 組合器、候選、提案、升階、進化 | 約 210 |
| HC-6 | **說明文字**：a. 後端敘事與卡片；b. content 驗證訊息；c. 前端說明＋api 說明 | 296 |
| HC-7 | **其餘 config**：a. engine（非 AI）＋world；b. api＋llm＋server | 約 160 |

建議順序：HC-2 先做（量類是 X10 的延續，風險最高）→ HC-3（前端副本會悄悄和後端分岔）→ HC-4 定通則 → HC-5 → HC-6 → HC-7。
每段做完把對應規則的 `status` 改 `done`，或刪掉已經不存在的數字。

## 5. 檢查（最後一個 commit `a6f653ff5`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1741 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `pytest tests/test_hardcoded_scan.py tests/test_architecture.py tests/test_x10_fields.py` | 0（52 passed） |
| `classify.py --check` | 0（沒歸類 0） |

- 沒改 src／client 的行為，所以沒跑重播與其他測試。
- 涵蓋測試本身大約 7 秒，其中掃描約 6 秒。

### 檢查本身
- 測試會擋：
  - 有一筆沒歸類就失敗。失敗訊息附「怎麼歸類」的說明、規則範本和前 40 筆。
  - 歸類檔寫錯就失敗。
- 抽查：
  - 量類：`forms.py upkeep_mana`、`_MAX_ATTR`、前端 `?? 10`。
  - config：`party_ap_per_turn`、`RELAX_PERMILLE`、`SLOT_LIMITS`、`FALLBACK`。
  - const：`_PERMILLE`。
- 兩個掃描器的單元測試：
  - 不列 0／1／-1、`range`、bool；
  - 負數；
  - f-string；
  - docstring；
  - JSX 文字、樣板字串；
  - `</div>` 不當正規表示式。
- 規則語法的測試：第一條勝出、`not` 排除、壞規則報錯。

## 6. 待 PM 決定

### 6.1 拿不準、照保守歸 config 的
規則的 note 開頭寫「保守」的 14 條（後端自動產生的規則只有每組第一條寫全文，其餘寫「同上一條」）：

| 規則 | 筆數 | 內容 |
|---|---:|---|
| `py-content-*-config-*`（全部 content） | 992 | content schema 的**預設值**與 **`le`／`ge` 上下限**。上下限比較像驗證，也可以算 const；但是量類 ×10 那次就是上限沒跟著改，所以先歸 config |
| `py-engine-ai-*-config-*`＋`environment.py` 的 AI 權重 | 55＋103 | AI 評分權重、半徑、門檻 |
| `py-llm-*-config-*` | 37 | LLM 呼叫設定（重試次數、等待秒數、退回率警示、名稱字數）。不是戰鬥數值，可能歸 `config/` 或 const |
| `py-world-*actions-config-number`（world 動作請求上限） | 19 | `max_length`、`le`（傳承 2、許願關鍵字 4、雇用 8、郵寄 10、金幣上限） |
| `py-server-*`（notes、league） | 4 | 留言板、腳印、循環賽最少人數 |
| `ts-vfx-damage-tiers` | 4 | 受擊頓格、重擊特效的失血門檻。是呈現用的，可以改判 layout |
| `ts-bag-size`、`ts-day-phase-hours`、`ts-crystal-tier` | 7 | 背包 6×5 後備、早午晚夜的鐘點、狀態 id → 層級 |

反過來，有一條是保守地歸 const 的：

| 規則 | 筆數 | 內容 |
|---|---:|---|
| `py-sim` | 264 | `sim/` 模擬與報表工具（場數、報表門檻、目標區間）。不影響遊戲，歸 const；如果平衡目標值也要集中管理，可以改 config |

### 6.2 規則類（先照最保守的預設做了）
1. **content schema 的上下限怎麼處理**（HC-4 開工前要定）。
   - 選項一：上下限也搬進資料，例如 `rules/limits.yaml`。
   - 選項二：上下限留在程式，但量類的上下限一律乘 `quantity_scale`。
   - 選項三：只驗證型別，上下限交給 `trpg content check`。
   - 目前全部歸 config（todo）。
2. **0、1、-1 不列**（照規格）。
   - 寫死的 `1` 會漏，例如 `content/environment.py:372 min_damage` 預設 1、`max(1, …)` 這類量類下限。
   - 量類的「最少 1」在 X10-3c 已經改成 `cost_floor`，但其他地方可能還有。
   - 要不要另做一個「量類欄位的 1」專查（只看 `owner`／`slot` 是量類名的 1），請 PM 決定。這段沒做。
3. **docstring 歸 const**（6927 筆）。
   - docstring 和欄位說明玩家看不到，數值本身另外列在 number，所以歸 const。
   - 但數值搬家後這些說明會過時。要不要列進 text 追蹤（數量會從 296 變成約 3000），請 PM 決定。
4. **中文數字（一、兩、三）不掃**。
   - 只掃 0-9 和全形０-９，例如「兩段」「三招」不會列。
   - 要列的話會多很多誤報，建議不列。

### 6.3 解讀與工具限制
5. **前端 `render/`、`audio/` 整個資料夾歸 layout，`dev/` 歸 const**。
   - `render/` 有 53370 筆，是繪圖座標與圖樣說明。
   - 抽看沒有玩法數字。如果日後在 `render/` 裡寫門檻（例如血條顏色的 HP 比例），不會被擋。
6. **前端與後端重複的輸入上限歸 const**。
   - 例如帳號 20、密碼 128、筆記 50、對話 500、名稱 12、物品名 20。
   - 前端 `auth.ts`、`notes.ts`、`story.ts` 和後端 `server/accounts.py`、`server/notes.py`、`llm/prompts/escape.py` 各寫一份。
   - 不是玩法數字，但會分岔。建議 HC-3 順手改成從 API 帶。
7. **前端 tokenizer 是近似的**：
   - JSX 文字裡有英文單引號（`don't`）會被當成字串開頭，吃到行尾。
   - `/` 是除號還是正規表示式靠前一個 token 判斷。
   - 抽查各檔的 scope 深度都正常；遇到誤判時只會影響那一行的 slot、scope，不會讓整檔亂掉。
8. **過時規則只列不擋**。
   - 測試不因「規則一筆都沒用到」失敗，免得別人刪掉數字就讓測試紅。
   - 用 `classify.py --unused` 看，建議每段搬家後清一次。
9. **後端規則是用腳本按「檔＋函式／常數」批次產生再人工分類的**（第 4 項 commit 之後重產過一次），所以 `classes.yaml` 有 3600 行，大部分是 `where:` 清單。
   - 每條規則上方有區塊註解說明那一組的歸類理由。
   - 「同上一條」的 note 指的是同一區塊的第一條。

## 7. 平衡疑慮
無。這段沒有改任何數值或行為。
