# Phase QF-4 報告：三個慢測試加速

基準：main `5188031d0`。分支 `worktree-agent-a052f52f8a8c81c74`，沒 push。規格：`docs/phases/PhaseQF-4計畫.md`。

**結論：3 個只達標 1 個。** `test_player_check_texts_have_no_english_identifiers` 改成去重後分 8 份，每份 26～42 秒，已拿掉 600 秒放寬。另外兩個 90% 以上的時間花在 `src` 同一個地方：組合器的「護主」反應配方，3 階起每次嘗試都做不出合格技能，但還是試滿次數。測試端找不到不減覆蓋又能降到 120 秒的做法，所以兩個都**保留** `timeout(600)`，修法列在「待 PM 決定」第 1 項。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 熱點分析 | 本報告第 2 節 | cProfile ＋ 分段計時（腳本只放 scratch，沒進 repo） |
| 2 加速 | `85d0324de` | `tests/skillgen/test_player_text.py`：草稿全域去重，參數化分 8 份 |
| 3 拿掉放寬 | `fc0281404` | 同檔拿掉 `@pytest.mark.timeout(600)`；另外兩個沒達標，照留 |
| 報告 | 本 commit | |

只改了 `tests/skillgen/test_player_text.py` 和本報告。

## 2. 熱點分析

用 cProfile 跑測試本體（三個行程同時跑，有 profile 的額外負擔，秒數只拿來看比例）。

### 2.1 `test_upgrade_topup.py::test_reaction_keywords_the_composer_cannot_carry[summon]`

| 段落 | 秒數（profile 下） |
|---|---|
| `_legal` | 0.15 |
| `_check(_without_recipes(library))`（工坊退路） | 10.7 |
| `_check(library)`（完整組合器，最後仍退到工坊） | **971.5** |

呼叫路徑：`fallback_skill` → `_from_composer`（`COMPOSER_TRIES = 8`）→ `compose_random_skill` → `_compose_with_keyword`（每次 300 個種子）→ `_compose_special` → `_compose_reaction_recipe`（4800 次）→ `_first_valid`（610 次，每次 `MAX_ATTEMPTS = 100`，共 61,000 次 build）→ `_guardian_drafts` ＋ `_tune_drafts` → `tune` **245 萬次**。

每次 `tune` 只算了一次 `ratio`，也就是最弱強度的草稿一算就不合格，馬上回 `False`。時間花在 `SkillDef.model_validate`（282 秒）和 `skill_budget`（426 秒；其中 `_summon_points` 210 秒、`Fraction` 運算約 175 秒）。3 階史詩的護主沒有任何一份草稿進得了預算窗（TF-1 已知），組合器還是試滿 8 × 100 次嘗試，每次約 40 份草稿。

### 2.2 `test_test_mode.py::test_run_with_equipment_plays_to_the_end_and_replays_the_same`

兩次 `auto_play`：第一次 333 秒，第二次 417 秒（profile 下，總共 750 秒）。

- `pick_slots`／`generate_pick_candidates` 718 秒，其中 4 次 `_complete_offer`（完整技能候選，`candidates._bridge` → `from_composer`）就占 711 秒。
- 往下是同一個熱點：`_compose_reaction_recipe` 695 秒、`tune` 166 萬次、`ratio` 601 秒。約 93% 的時間在護主配方。
- 戰鬥本身（AI 下棋、引擎）不到 5%。

### 2.3 `test_player_text.py::test_player_check_texts_have_no_english_identifiers`

- 60 個種子 × 突變共 **1049 份草稿**，每份跑 `draft_options` ＋ `check_draft`（profile 下 430 秒）。
- `draft_options` 被呼叫 2098 次、占 421 秒：每份算兩次，測試算一次，`check_draft` 內部又算一次（`src`）。
- 細項：`_effects_step` 211 秒、`playerize` 141 秒、`_effect_choices` 138 秒、`build_skill` 112 萬次 129 秒。
- 1049 份裡有 **138 份完全重複**（突變後和原稿或同種子的另一個突變一樣，例如原稿本來就是 `category: weapon`）。重複都在同一個種子內，跨種子沒有。

## 3. 做法

### 3.1 player_text（達標）

- `_unique_drafts()`（`functools.cache`）：照原本的順序產生 60 個種子的原稿與突變，用 `json.dumps(sort_keys=True)` 去重，保留第一次出現的那份（原本的鍵順序）。存成 JSON 字串，每份測試自己 `json.loads`，**不共用可變的 dict**。組合 60 個種子約 1 秒。
- `test_player_check_texts_have_no_english_identifiers` 參數化 `part ∈ 0..7`，檢查 `drafts[part::8]`（每份 113～114 份草稿）。8 份合起來就是全部。

### 3.2 試過、沒採用

- **在測試裡快取 `composer_tuning._Evaluator.ratio`**（monkeypatch，key＝內容庫 ＋ 草稿 JSON）：命中率只有 60%（每次嘗試的種子不同，草稿裡帶種子的欄位不同），3 階召喚那一段從約 260 秒降到 200 秒，不夠。而且這等於在測試裡改 `src` 的行為，所以不採用。
- **summon 那題拆成兩個測試**：工坊退路只要 10 秒，完整組合器那段單獨就要 260 秒，拆了也不會達標。
- **裝備那題和同檔 `test_test_mode_refills_to_the_gear_inclusive_maximum` 共用第一次 auto_play**：那個測試跑的是同一輪（種子 3、測試模式、GEAR）。共用可以讓整檔少跑一次，但這個測試單獨跑時還是要跑兩輪才能比對重播，單一測試的秒數不會變，所以沒做（也超出「只改這 3 個測試」）。
- **換內容庫或種子讓那一輪變短**：會改掉這一輪實際走過的節點和候選，等於少測，沒做。

## 4. 秒數

都是單獨跑（`-p no:randomly --durations=0`，不平行）。同時有 HC-5a 在跑測試；負載用 `tasklist` 數 `python.exe` 行程數記錄（每個 uv 或 xdist 都會多幾個行程，只能當相對指標）。

| 測試 | 改前 | 改後 | 備註 |
|---|---|---|---|
| summon | 271.7 秒（python 行程 38） | 沒改 | 驗收跑 `-n 8` 時是 422.6 秒，**超過 300**，600 的放寬有必要 |
| 裝備重播 | 210.0 秒（38） | 沒改 | 驗收 `-n 8` 時 316.9 秒 |
| player_text | 211.5 秒（38） | 8 份 26.1～41.4 秒，合計約 276 秒（行程 88） | 見下一列的同負載對照 |
| player_text 同負載 A/B（scratch 腳本、同一行程背靠背） | 舊本體 340.8 秒 | 8 份 25.0～42.1 秒，合計 239.6 秒 | 行程數前後都是 72 |

改前的 211.5 秒是在負載較輕時量的（38），改後的 pytest 計時在較重時量（88），所以另外做了同負載 A/B：同一個行程、同一時段先跑舊本體、再跑 8 份。去重讓總量少約 30%；平行時每份都在 120 秒內。

## 5. 覆蓋對照（player_text）

計數只在 scratch 量（`text_cover.py`、`text_after.py`），沒進 repo。

| 對象 | 改前 | 改後 | 一致 |
|---|---|---|---|
| 檢查的草稿份數 | 1049（含重複） | 911（8 份：114／114／114／114／114／114／114／113） | — |
| 不同的草稿（sort_keys JSON） | 911 | 911 | **集合相同** |
| 種子 | 0～59 | 0～59 | 是 |
| 突變種類（原稿 ＋ 15 種欄位突變 ＋ 刪第 1～3 個效果） | 每個種子全做 | 每個種子全做，只略過和既有草稿一字不差的 | 是 |
| 送進 `_leaks` 的不同文字 | 1977 | 1977 | **集合相同** |
| assert 的對象 | 所有文字的英文識別字（`found == {}`） | 同，每份各自 assert | 是 |

突變的覆蓋：刪除效果的突變，每個種子依原稿的效果數量做（第 1 個 60 份、第 2 個 26 份、第 3 個 8 份），改後照舊。被略過的 138 份都和留下的某一份完全相同，所以檢查到的文字不變。

另外兩個測試沒改，覆蓋不變。

## 6. collected 數

| 檔 | 改前（非 slow／全部） | 改後（非 slow／全部） |
|---|---|---|
| `tests/skillgen/test_upgrade_topup.py` | 35／55 | 35／55 |
| `tests/roguelite/test_test_mode.py` | 16／16 | 16／16 |
| `tests/skillgen/test_player_text.py` | 3／3 | 10／10 |
| 合計 | 54／74 | **61／81**（+7） |

## 7. 檢查與結束碼

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check tests` | 0 |
| `uv run ruff format --check tests` | 0（982 files already formatted） |
| `uv run mypy` | 0（1772 source files） |
| `uv run python scripts/run_pytest.py -q --durations=15 <三個檔> -n 8` | 0（61 passed，615.9 秒；python 行程 70～88） |

沒跑全量（規格不要求）。沒有改 `src/`、`content/`、`pyproject.toml`、`.claude/`、`docs/design/`，也沒有標 slow。

## 8. 待 PM 決定

1. **護主配方的 `src` 修正**（summon 與裝備重播兩個測試沒達標的原因，也拖慢正式遊戲：profile 下一次完整技能候選約 60～180 秒）。熱點在 `src/trpg/skillgen/random_composer.py` `_compose_reaction_recipe` → `_first_valid`，以及 `src/trpg/skillgen/composer_recipes.py` `_guardian_drafts`。3 階起每份草稿最弱強度就不合格，還是試滿 100 次嘗試 × 約 40 份草稿，外層再重試 8 次。可能的修法（請開發 PM 選）：
   - (a) `reaction_recipes(lib, tier)` 或 `pick_recipe` 在做不出護主的階級不給這個配方（要確認亂數串流不變，或接受候選改變）；
   - (b) `_first_valid` 或 `_guardian_drafts` 裡，同一個（召喚物、縮放屬性、強度、代價）已經不合格就不再算預算（預算和種子無關的部分）；
   - (c) 第一次嘗試全部草稿的 `base_ratio` 都不合格時，直接回 `None`。

   修完預估 summon 會降到工坊那段的量級（約 10～20 秒），裝備重播也會大幅降低，但**沒量**。修完再拿掉兩個 600 秒放寬。
2. **兩個測試保留 `timeout(600)`**：`test_upgrade_topup.py` 第 732 行、`test_test_mode.py` 第 114 行，註解沒改。驗收時 summon 在 `-n 8` 下跑了 422.6 秒，600 秒的餘裕不大。負載再重時可能還是會被收掉。
3. **player_text 是把時間攤開，總量只少約 30%**：單一測試不會再逼近上限，總 CPU 時間仍有 2～4 分鐘。要再省，可以讓 `check_draft` 接受已經算好的 `draft_options`（每份草稿現在算兩次，約占一半時間）；這要改 `src`，沒做。
4. **範圍外的發現**：`test_test_mode.py::test_test_mode_refills_to_the_gear_inclusive_maximum` 在驗收的 `-n 8` 下跑了 159 秒，熱點應該是同一個護主配方（同一輪），修第 1 項後會一起變快。
