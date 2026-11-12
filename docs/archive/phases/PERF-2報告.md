# PERF-2 報告：完整技能三選一加速（結果不變）

分支 `worktree-agent-ab500a8091cd2560e`（已 `git merge main`，含 5C-2）。另有選用分支 `perf2-content-pathfix`（本分支＋1 個 `trpg.content` commit，見第 4 節，**需 PM 決定要不要收**）。

## 1. 量測方法

- 腳本 `scripts/perf_complete_offer.py`：6 組代表角色（火、雷、坦、刺客、治療、術士；1～10 級、不同種子），每組量一次 `make_offer(..., "complete")`，印出時間與三張候選 JSON 的 sha256（結果指紋）。
  - `--cold`：每組前清空組合器快取（最壞情況，等於伺服器剛啟動後的第一次）。
  - `--rounds 2`：第 2 輪換種子（同一行程，快取已熱）。
  - `--profile N`：cProfile。
- 機器上同時有其他 agent 在跑測試，單次時間波動很大（同一組可差 30%）。下表是**交錯量 3 次**（舊版／新版／新版＋選用修正輪流跑）取第 2 次；3 次的平均值見表下。舊版用 `git archive 9d435a86` 解到暫存資料夾、以 `PYTHONPATH` 載入。

## 2. 熱點（cProfile，舊版）

完整技能三選一的時間幾乎全在**候選產生器的「橋接」候選**（`candidates._bridge` 佔 95%）：橋接要找同時帶兩個關鍵字的技能，一對對關鍵字去試；每試一個種子就呼叫隨機組合器 `compose_random_skill(keyword=...)`，組合器再對最多 300 個種子變體逐一組完整技能、組完才看有沒有該關鍵字（一次三選一約 1,000～1,500 個變體、92% 因沒有關鍵字被丟掉）。`complete_strength` 本身只佔 <1%。

逐層成本（雷系，舊版 profile 約 93 秒/6 組）：

| 熱點 | 佔比 | 說明 |
|---|---|---|
| 傳說技能的候選列舉 `composer_special._pick` | ~42% | 變體抽到傳說（約 10%）時，每輪列 16～52 個候選、每個都做 schema 驗證＋預算，最多 48 輪 |
| 強度調整 `composer_tuning.tune` | ~32% | 每調一格旋鈕就驗證整招技能＋算預算 |
| `EffectSpec` 驗證器每次新建 `Path` 查範圍表 | ~17% | `default_content_dir() / "skill_primitives.yaml"` 每次建新 `Path`，在 Windows 上雜湊（大小寫正規化）很慢；**在 `trpg.content`** |
| 內容表 `by_id()` 每次重建字典 | ~4% | 預算、機制標籤、驗證器每個效果都查 |
| 關鍵字檢查 `derive_keywords` | ~6% | 每個變體推導全部 12 個關鍵字，只為了看其中 1 個 |

沒有找到「library 深拷貝」「重複預算表」或 `retier` 的熱點（`retier` 已有快取）。

## 3. 改法（只動 `trpg.skillgen`，不改結果）

1. **傳說候選的合格判斷快取**（`skillgen/memo.py` 新增，`composer_special._pick`）：「通過 schema＋預算比例合格」與「通過驗證器」以草稿內容為鍵快取在內容庫上。鍵＝草稿去掉 `id` 與 `narrative`（只有這兩欄帶種子；ID 只出現在違規訊息、敘事文字沒有限制）後的排序 JSON 的 BLAKE2b 摘要（不用內建 `hash()`）。洗牌只看合格張數，所以改成洗草稿清單、挑中的技能再照原流程重建——回傳的技能與原本逐字相同。同一次三選一內命中率約 35～55%，行程熱了以後更高。表以物件身分＋弱參照掛在內容庫上，內容庫被回收就丟；每表上限 200,000 筆，滿了清空。
2. **內容表 ID 對照快取**（`memo.by_id`／`memo.derived`）：`budget`、`mechanics`、`composer_parts`、`validate` 裡 `rules.statuses.by_id()` 等 49 處改用快取版（凍結 model，同一張表只建一次）。
3. **單一關鍵字檢查**（`keywords.has_keyword`）：組合器的「這個變體有沒有關鍵字 k」改成只跑 k 自己的推導規則（基礎型態＋戰場變奏，與 `derive_keywords` 範圍相同）。測試逐一比對全部內建技能 × 全部關鍵字與 `derive_keywords` 結果一致。
4. **強度調整少算一次**（`composer_tuning._raise`）：一次跳多格失敗、退回一格時原本會重算一次跟剛才完全相同的草稿，改成直接還原剛才的違規數。
5. **機制標籤快取**（`random_composer._tags`）：同一次組合對同樣的草稿常算 2～3 次，改以草稿鍵快取。
6. 試過但撤掉：強度調整每一步的比例快取——不同種子之間命中率只有 3～5%，JSON 鍵的成本抵掉收益。

確定性：快取只記「結果」（布林、標籤），不依賴 set 順序或 `hash()`；`id()` 只當快取的對照鍵且都以 `is`／弱參照確認是同一個物件（物件被持有或回收時同步移除，不會誤用重用的 id）。

## 4. 前後時間（秒，`--cold`：每組都從空快取開始）

| 組 | 舊版 9d435a86 | 本分支 | 本分支＋選用 content 修正 |
|---|---|---|---|
| 火 lv1 | 2.71 | 2.16 | 1.47 |
| 雷 lv4 | 9.01 | 6.48 | 4.62 |
| 坦 lv7 | 3.76 | 2.94 | 1.97 |
| 刺客 lv4 | 13.03 | 9.37 | 6.88 |
| 治療 lv10 | 4.69 | 3.63 | 2.57 |
| 術士 lv7 | 4.47 | 3.37 | 2.29 |
| **平均／中位數** | **6.28／4.58** | **4.66／3.50** | **3.30／2.43** |

3 次交錯量測的平均：舊版 6.25／4.51、本分支 4.38／3.25（−30%）、加選用修正 3.12／2.29（−50%）。行程熱了以後（`--rounds 2` 第 2 輪、換種子）傳說部分大多命中，但時間仍主要由種子決定（同一個角色換種子可從 0.3 秒到 15 秒；舊版同樣如此）。

**目標「典型 ≤ 2 秒」沒有達到**：本分支中位數約 3.3 秒，加上選用的 content 修正約 2.3 秒；最慢的組（刺客、雷）仍 5～9 秒。

### 選用：`perf2-content-pathfix`（動到 `trpg.content`，超出這次的範圍）

`trpg.content.skills.effects` 的三個範圍表查詢（`_yaml_ranged_params`、`composition_rules`、`true_only_params`）每次 `EffectSpec`／`SkillDef` 驗證都建新的 `Path` 再拿去查 `@cache`；改成同一個內容資料夾重用同一個 `Path` 物件（`TRPG_CONTENT_DIR` 的值當鍵，換資料夾仍照原本行為）。約 15 行。這是剩下**單一最大的熱點**（驗證時間將近一半），單獨就能再省約 30%。因為任務只准動 `trpg.skillgen`，放在另一個分支，`tests/content`、`tests/cli/test_cli.py`、`test_budget_cli.py`（有 `TRPG_CONTENT_DIR` 覆寫）全過。

## 5. 確定性證明

- 行為快照 `tests/skillgen/test_refactor_3wr2.py -m "slow or not slow"`：877 passed（未重產快照）。
- 6 組角色 × 2 輪的結果指紋（候選 JSON sha256）新舊版逐字相同（例：`f9ec3d757788`、`8facc14e97f5`、`df4107e4c92b`…；第 2 輪 `060cc448d7fa`、`17f37f2c7d7f`…），合併 main 後與選用分支也相同。
- 新測試 `tests/skillgen/test_memo_perf2.py`（11 項）：`has_keyword` 對全部內建技能 × 關鍵字與 `derive_keywords` 一致；傳說與指定關鍵字組合在空快取／熱快取下逐字相同；`draft_key` 只忽略 `id`、`narrative`；快取依內容庫分開。
- 合併 main 前：`tests/skillgen tests/roguelite tests/world` 4327 passed、14 skipped；受影響的 API 測試 9 檔 101 passed。合併 main 後的結果見第 7 節。

## 6. 瓶頸與下一步（待 PM 決定）

1. **選用分支 `perf2-content-pathfix` 要不要收**（動 `trpg.content.skills.effects`，約 15 行，結果不變，再快約 30%）。
2. 剩下的時間是**結構性的**：橋接候選靠「組完整技能再丟掉沒關鍵字的」來搜尋，一次三選一要組上千個變體；每個變體都要做 pydantic 驗證＋預算。在「結果逐字不變」的限制下，能快取的都快取了。要再快一個量級只剩改變結果的做法，需要使用者／玩法 PM 決定：
   - (a) 給橋接搜尋設上限（例如每對關鍵字只試 2～4 個種子、或總變體數上限），找不到就照現有規則退回單一關鍵字；會改變候選，要重產快照。
   - (b) 傳說稀有度不進「指定關鍵字」的組合（傳說佔變體 10%、時間 40%，而且多半做不出指定關鍵字）。
   - (c) 不改結果的做法：大世界在機遇／劇情步驟**出現時**就在背景先算好三選一（玩家按下時直接拿），或伺服器啟動時先跑幾組暖快取；這是 API／世界層的改動，不在這次範圍。
3. 同一個角色換種子時間差很大（0.3～15 秒），最壞情況比平均更影響體感；(a) 能直接壓住最壞情況。

## 7. 檢查（合併 main 5f627a46 之後）

- `tests/skillgen tests/roguelite tests/world` ＋受影響的 API 9 檔：4466 passed、14 skipped（-n 8）。
- `tests/cli -m "slow or not slow"`：180 passed（-n 8、--timeout=3000）。
- `ruff check .`、`ruff format --check .`、`mypy`（1073 檔）、`lint-imports`（9 kept）全過。
- 選用分支另跑 `tests/content`、`tests/cli/test_cli.py`、`tests/cli/test_budget_cli.py`、`tests/skillgen/test_memo_perf2.py`：1992 passed。
