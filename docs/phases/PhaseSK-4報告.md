# Phase SK-4 報告：吸血配方＋覆蓋表資料不進版控

> 2026-11-19，實作者。規格 `docs/phases/PhaseSK-4計畫.md`；來源是玩法交接 4.1.34 第 10 點、`docs/phases/PhaseWC-2b報告.md` 開發 PM 裁定。
> 分支 `worktree-agent-a0980c6aa9001228b`（worktree 原本落後 main，先 fast-forward 到 `e3e242222`，含本段計畫）。不 push。
> 沒有試數值、沒有跑平衡量測。沒有改 `docs/design/`、`config/`、`client/`。

## 結果（一兩句）

三件都做完。組合器的打擊、範圍骨架會以 100‰ 的機率在傷害上附吸血 300‰（初值）；「傷害＋治療」從做不到（每格 0）變成最好的一格 5.2%，覆蓋表做不到 **90 → 85**、極低維持 36。覆蓋表的 `buckets.json`（WC-1、WC-2 兩份）改成不進版控。戰鬥不變比對 different=0；parity、CLI 快照沒有任何鍵變。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 吸血配方（打擊、範圍） | 完成 | `4a2d27975` |
| 2 覆蓋表資料不進版控 | 完成 | `69c0a2e42` |
| 3 重跑覆蓋表、報告「傷害＋治療」 | 完成 | `646be71f8` |

## 1. 做法

### 1.1 吸血配方（第 1 件）

- **設定**（`skill_composer.yaml` 的 `structure`，都是初值，接數值工坊）：
  - `lifesteal_permille: 100`：附吸血的機率（和其他獨立串流的附帶差不多）。
  - `lifesteal_amount_permille: 300`：附上的吸血值（回復造成傷害的 30%；原語上限 500，手寫的生命汲取是 400）。
  - `lifesteal_skeletons: [strike, area]`：哪些骨架可以附。載入時檢查骨架存在（`_check_composer_objects`），寫錯會丟 `ContentError`。
- **組法**（`composer_parts._lifesteal_damage`，接在 `build_effects` 最後）：
  - 骨架在清單裡、有對敵的傷害效果（`affects` 省略或 `enemies`）、沒有聖光雙效、還沒有吸血時，用獨立串流 `composer.lifesteal` 擲機率。
  - 抽中就在**第一個**對敵傷害效果上加 `lifesteal_permille`。不新增效果，所以不佔附帶或效果數的名額。
  - 之後照原流程的旋鈕重調強度。預算照既有的吸血計價（`skill_budget.yaml` 的 `lifesteal_value_permille: 800`：點數 ×(1＋吸血‰×0.8)），所以吸血的招傷害骰會小一點。
- **驗證器、LLM schema、提示詞都不用放寬**：`lifesteal_permille` 本來就是傷害原語的參數，不限骨架（只有聖光雙效限光環、範圍），驗證器與提議 schema 都已接受。所以**沒有升版號**。
- 聖光雙效照舊只靠手寫，沒做。
- **沒抽中的種子不變**：用 HEAD（改前）的 `src`、`content` 和改後各組 800 個種子 ×（不指定、連擊、點燃）共 2400 招比對：
  - 有 22 招不同，其中 19 招是帶了吸血的。
  - 另外 3 招（種子 499、522、762，不指定關鍵字）是抽中吸血、但那一輪調不進預算窗而重抽，重抽後的亂數位置不同，所以結果換了一招（不帶吸血）。這和吹送、疾病擴散等既有獨立串流的行為相同。
  - 不指定骨架時，前 400 個種子有 5 招帶吸血（打擊、範圍合計約 99 招，約 5%）；指定骨架時，打擊、範圍前 200 個種子都有。
- **新測試** `tests/skillgen/test_composer_lifesteal_sk4.py`（9 條）：打擊、範圍會出吸血（值照設定、只附一個對敵傷害、驗證器通過、預算明細有「吸血」、許願命中「傷害」「治療」）；控場、位移、連段、光環、蓄力不會出；骨架寫錯載入失敗。

### 1.2 覆蓋表資料不進版控（第 2 件）

- `.gitignore` 加 `docs/phases/WC-1資料/buckets.json`（0.8 MB）、`docs/phases/WC-2資料/buckets.json`（8.3 MB），兩檔都 `git rm --cached`（本機檔案留著）。
- 資料夾裡沒有其他小檔；覆蓋表 md（`許願覆蓋表.md`、`許願覆蓋表-WC2.md`）照舊進版控。
- `scripts/wish_coverage.py`：
  - 開頭說明加一段「資料不進版控」：先 `run` 重產（同內容同參數，計時以外逐字相同；8 個行程約 15 分鐘），再 `report`。
  - `report` 找不到資料檔時不寫表，印出要跑的 `run` 指令，結束碼 2。
  - 產生的表頭改成「資料檔不進版控，重產照 `scripts/wish_coverage.py` 開頭的說明」（原本指向 WC-2 報告）。
- 新測試（`tests/test_wish_coverage.py` 兩條）：沒資料時 `report` 回 2 並提示；`.gitignore` 有這兩行。

### 1.3 覆蓋表（第 3 件）

`scripts/wish_coverage.py run --seeds 40 --workers 8`（768 桶，982 秒）＋ `report`，更新 `docs/phases/許願覆蓋表-WC2.md`（資料檔重產在本機，不進版控）。改前的對照用 WC-2b 的表與資料（跑之前先複製到 scratchpad）。

**「傷害＋治療」各格（%）**

| | 1普 | 1稀 | 1史 | 2普 | 2稀 | 2史 | 3普 | 3稀 | 3史 | 4普 | 4稀 | 4史 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WC-2b | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| SK-4 | 5.2 | 5.2 | 0 | 5.2 | 1.7 | 1.7 | 5.2 | 1.7 | 1.7 | 5.2 | 1.7 | 0 |

- 從做不到清單（a）移除，最好的一格 5.2%（≥ 2%，算做得到）。史詩 1、4 階仍是 0：40 個種子裡剛好沒抽中（每格期望只有一兩招）。
- 單一標籤「治療」平均 8% → 11%（最好的一格 13% → 15%）。

**摘要**

| | WC-2b | SK-4 |
|---|---|---|
| 做不到 | 90（a 57、b 19、需人工 14） | 85（a 56、b 19、需人工 10） |
| 極低 | 36（a 22、需人工 14） | 36（a 22、需人工 14） |

**清單的變化（逐項）**

| 組合 | WC-2b | SK-4 |
|---|---|---|
| 傷害＋治療 | 做不到（a） | 做得到 |
| 中毒（關鍵字）＋治療 | 做不到（需人工） | 做得到 |
| 倒地（關鍵字）＋治療 | 做不到（需人工） | 極低 2% |
| 治療＋直線 | 做不到（需人工） | 極低 2% |
| 治療＋錐形 | 做不到（需人工） | 極低 2% |
| 冰凍（關鍵字）＋治療 | 極低 | 做得到 |
| 帶電（關鍵字）＋治療 | 極低 | 做得到 |
| 控制＋治療 | 極低 | 做得到 |
| 標記（關鍵字）＋治療 | 極低 | 做得到 |
| 冰霜（元素）＋大地（元素） | 做得到 | 極低 2%（需人工） |

- 除了最後一列，都是吸血帶出來的「治療」組合。
- **冰霜＋大地**變差是抽樣：少數種子抽中吸血後重抽、換了一招（見 1.1），這一組本來就貼在 2% 邊上，和吸血無關。之後重跑可能又回去。
- 新出現的做不到：0 組。表最後和 WC-1 舊表的對照照舊重產（做不到 → 做得到 84 組、→ 極低 12 組、還是做不到 85 組）。
- 其他單格的小幅變動（例：點燃、潮濕的 1～2 個百分點）同樣是抽中吸血的種子換招造成的抽樣差。

## 2. 戰鬥不變比對

- WC-2 的比對腳本沒有 commit，這次另寫一份（放 scratchpad，沒 commit），同樣 60 場：10 張一般圖 × 種子 1、2，加 4 張頭目圖（`cloud_summit`、`molten_heart_pit`、`rift_gate`、`ruined_fort`）× 種子 3～12。
- 做法：`trpg battle --map … --seed …`（地圖預設陣容），整份輸出比 SHA-256。改前＝`git archive e3e242222` 的 `src content config`，`PYTHONPATH`、`TRPG_CONTENT_DIR` 指向舊的（印出載入路徑確認）。
- 第 1 件做完：`battles=60 different=0`（結束碼全 0）。第 2、3 件只動腳本與資料，碰不到戰鬥。
- 預期就是 0：吸血只在組合器新組的技能上，地圖預設陣容都是手寫技能。

## 3. 版號

沒有升任何版號。`lifesteal_permille` 本來就在傷害原語、驗證器和提議 schema 裡，`skill-proposal`、`wish-tags`、`LOG_FORMAT` 都沒動；覆蓋表格式維持 `wish-coverage/2`（資料欄位沒變）。

## 4. 快照、夾具逐鍵核對

| 東西 | 預測 | 結果 |
|---|---|---|
| `refactor_3wr2.json`（parity） | 不變：內建技能的完整強度、升階、閃現出題都不經過組合器 `build_effects` | 每個 commit 跑 `-m slow` parity，全過，沒改任何鍵 |
| CLI 快照（`cli_output_hashes.json`）與 `run auto` 測試 | 不變：快照是手寫技能清單與固定戰鬥；`run auto` 的三選一雖然會組技能，但種子 4、6 的流程不受影響（預測不確定，以測試為準） | 每個 commit 跑 `-m slow tests/cli`，全過 |
| 組合器輸出 | 只有抽中吸血的打擊、範圍種子會變（另有抽中後重抽的少數種子） | 2400 招中 22 招變（見 1.1）；`tests/skillgen` 沒有鎖輸出的測試失敗 |
| 夾具、OpenAPI | 不會變 | 沒有重產 |

## 5. 檢查

| 指令 | 時間點 | 結束碼 |
|---|---|---|
| `ruff check`、`ruff format --check`（src tests；第 2 件起加 scripts） | 每個 commit | 0 |
| `mypy src`（第 2 件加腳本與測試檔，676 檔） | 每個 commit | 0 |
| `lint-imports`（14 kept） | 每個 commit | 0 |
| `trpg content check` | 第 1 件 | 0 |
| `pytest tests/skillgen tests/test_wish_coverage.py -n 8`（4596 passed、14 skipped） | 第 1 件 | 0 |
| `pytest tests/content tests/roguelite tests/world tests/api -n 8`（6071 passed、1 skipped） | 第 1 件 | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8`（980） | 第 1 件 | 0 |
| 戰鬥不變比對 60 場 | 第 1 件 | different=0 |
| `pytest tests/test_wish_coverage.py`（8） | 第 2 件 | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8`（980） | 第 2 件 | 0 |
| `wish_coverage.py run --seeds 40 --workers 8`、`report` | 第 3 件 | 0、0 |
| ruff、format、`mypy src`、lint-imports | 第 3 件 | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8`（980） | 第 3 件 | 0 |
| `pytest tests/llm tests/test_wish_coverage.py -n 8`（504；和 skillgen 分開跑） | 第 3 件之後 | 0 |

- `tests/llm` 和 `tests/skillgen` 沒有同時跑。沒跑全量 `scripts/check.py`、`tests/sim`，沒用 `-m ""`。
- 沒有新增 `# noqa`。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| # | 事項 | 我的做法 | 其他選項 |
|---|---|---|---|
| 1 | 吸血附在哪個傷害 | 只附第一個對敵（`affects` 省略或 `enemies`）的傷害；`affects: all`（會打到友方）的傷害不附 | 也附在 `affects: all` 上（引擎只算對敵的實際傷害） |
| 2 | 吸血的值 | 固定 300‰（原語是 `knob: none`，旋鈕不調它），預算差由傷害骰補 | 做成旋鈕階梯（例 200／300／400） |
| 3 | 許願池要不要定向補抽 | 沒有：只靠一般組合器 100‰ 的機率，許願池不像召喚、第二元素那樣針對「治療」補抽吸血版本 | 願望有「傷害＋治療」時，對候選補一個吸血版本（同 `_dual_draws`） |
| 4 | 工坊 | 新的三個值在 `skill_composer.yaml`，這個檔還不在工坊白名單（下一段才開新對象種類），所以沒加 | 下一段一起開 |
| 5 | 抽中後重抽 | 抽中吸血但調不進預算窗時，那一輪照原流程重抽，所以少數種子（2400 招中 3 招）換成另一招不帶吸血的技能，和吹送、疾病擴散一樣 | 調不進時退回不帶吸血的同一招 |

## 開發 PM 裁定（2026-11-19）

合併：main（--no-ff）。不變比對 different=0；沒有升版號；parity 和 CLI 快照不變。覆蓋表做不到 90 → 85。

- 接受（保守做法、初值）：1（只附在對敵的傷害上）、2（吸血值固定 300‰）、3（許願池不針對「治療」補抽吸血）、5（調不進預算就重抽，和吹送、疾病擴散一樣）。
- 4（三個值開進工坊）：併進下一段工坊新對象種類。
- 第 1、3 點告知玩法 PM；要改再排段。
