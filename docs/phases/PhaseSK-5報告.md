# Phase SK-5 報告：工坊新對象種類＋許願池補抽吸血

> 2026-11-19，實作者。規格 `docs/phases/PhaseSK-5計畫.md`；來源是 SK-3b 待決 4、WC-2 待決 11、SK-4 待決 4、玩法交接 4.1.34 第 10 點。
> 分支 `worktree-agent-a221f2cfefa7ad073`（開工前 `git merge main`，fast-forward 到 `1ed3c79f8`）。不 push。
> 沒有試數值、沒有跑平衡量測（戰鬥不變比對與覆蓋表重跑除外）。沒有改 `docs/design/`、`config/`、任何 `content/` 的數值；沒有碰 AP-1 的範圍（引擎、戰鬥狀態 API、AP 列與戰鬥畫面、敵人單位）。

## 結果（一兩句）

兩項都做完。數值工坊多兩類全體共用的表：「被動觸發時機」（15 個預算係數）與「技能組合器的附帶配方」（規格列的 11 個值），能看、能改、改完過內容驗證。許願同時有「傷害＋治療」時許願池另做吸血版本，覆蓋表「傷害＋治療」最好的一格 **5.2% → 28.0%**（做不到 85、極低 36 不變）。戰鬥不變比對兩次都是 different=0；parity、CLI 快照沒有鍵變。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 工坊新增 `skill_triggers`、`skill_composer` | 完成 | `08b790c8b` |
| 2 許願池補抽吸血＋重跑覆蓋表 | 完成 | `9ffc319da` |

## 1. 工坊新對象種類（第 1 項）

### 1.1 白名單（`content/tuning_fields.yaml`）

- `kind: skill_triggers`（`skill_triggers.yaml`）：`triggers[*].budget_coefficient_permille`，`existing_only`。展開成 15 欄，標籤「觸發時機「你造的關鍵字被利用時」的預算係數（‰）」這類。`every_n_hits` 依 n 查表（`budget_by_n_permille` 的鍵是數字，路徑寫不出來），不展開。
- `kind: skill_composer`（`skill_composer.yaml`）：只開規格列的 11 個值：
  - SK-2b：`structure.hook_core_permille`、`absorb_core_permille`、`absorb_secondary_permille`、`contagion_permille`
  - SK-3b：`structure.exploit_passive_permille`、`reroll_reaction_permille`
  - WC-2：`passive.around_permille`、`structure.stack_rider_permille`、`summon_rider_permille`
  - SK-4：`structure.lifesteal_permille`、`lifesteal_amount_permille`
  - `lifesteal_skeletons` 等結構清單不開（測試確認改它會被擋）。
- 建議範圍（`hint_*`）只是提示；擋的範圍照 schema：係數 ≥1、機率 0～1000、吸血比例 1～500。

### 1.2 程式

- `src/trpg/content/tuning_fields.py`：`TARGET_MODELS` 加 `SkillTriggerTable`、`ComposerRules`；`TABLE_KINDS` 與 `TuningTarget.kind` 加兩類。
- `src/trpg/api/tuning/objects.py`：
  - 清單名稱 `TABLE_NAMES_ZH`、表單頂端提示 `TABLE_NOTES_ZH` 各加兩筆；
  - 觸發時機欄位的標籤前綴（`_ENTRY_WORDS` 加 `triggers`）；
  - 擋的範圍 `_sk5_limits`（從 `_schema_limits` 拆出，避免 PLR0911）。
- `src/trpg/api/tuning/yaml_patch.py`：**原本整個檔有錨點／別名就擋**，`skill_composer.yaml` 的白板配方用了 `&summon_cooldowns`、`&modifier_ladder`，所以一個值都改不了。改成只擋「路徑經過共用節點」的改動（`_shared_nodes`：`yaml.compose` 把別名接到同一個節點物件，出現兩次以上＝共用）。改完照舊重新 parse、比對整份資料只差那一個值。原本的錨點測試案例照樣擋。
- 前端只改工坊：`client/src/api/client.ts` 的 kind 聯集、`TuningScreen.tsx` 另抓兩類。兩類的 `category` 是 `rules`，放進「規則與預算（全體共用）」一組。
- API 型別沒變（`kind` 參數本來就是字串、`TuningCategory` 沒加），OpenAPI 快照測試過，沒重產。
- `docs/dev/上手-內容資料與模擬.md` 第七節 yaml_patch 那一列改寫錨點的說明。

### 1.3 測試

- 新 `tests/api/tuning/test_triggers_composer_sk5.py`（6 條）：兩類列在清單上、觸發係數只少 `every_n_hits`、組合器只開 11 個、擋的範圍、草稿改三個組合器值加一個觸發係數驗證通過、1001／600／0 被擋在對的欄位、別處有錨點不影響改值、共用節點照擋、結構清單改不了。
- `test_rules_budget_bs1.py` 的 `TABLE_KINDS` 斷言加兩類。
- 前端 `tuning.test.ts` 加一條（兩類依 kind 讀欄位、清單分組、畫面抓兩類）。

### 1.4 截圖（`docs/art/shots/SK-5/`，實機）

`client` 建置後 `TRPG_TUNING=1 trpg serve --port 8012`，內建瀏覽器開 `/?dev=1&mute=1`（工坊本身沒有聲音）。

| 檔案 | 內容 |
|---|---|
| `01-composer-form.jpg` | 組合器表單，11 欄的現值、建議與允許範圍 |
| `02-composer-edit-ok.jpg` | 吸血機率改 150，標「改過」；頁面驗證「驗證通過（1.96 秒）」 |
| `03-composer-edit-refused.jpg` | 改 1001，欄位下方「不能大於 1000」 |
| `04-triggers-form.jpg` | 被動觸發時機表單與頂端提示 |

截完把改動還原；伺服器與瀏覽器分頁都關了（8012 已釋放）。

## 2. 許願池補抽吸血（第 2 項）

### 2.1 做法

- 新模組 `src/trpg/skillgen/composer_lifesteal.py`：
  - `lifesteal_ready`：主動技、骨架在 `structure.lifesteal_skeletons`、不是陷阱或複合技、有對敵的傷害（沒有聖光雙效、還沒吸血）。
  - `add_lifesteal`：照 SK-4 配方在第一個對敵傷害上加 `lifesteal_amount_permille`，用組合器同一套旋鈕重調（`composer_tuning.tune`），最後過驗證器；寫法同 `composer_dual.add_second_element`。
- `wish_pick._lifesteal_draws`（接在雙元素之後、放寬之前）：效果標籤同時有 `damage`、`heal`，而且種類標籤是空的或主動時：
  1. 候選裡做得到吸血的組合器技能，依「命中其他標籤數」由多到少做吸血版本（串流 `pick.wish.lifesteal/have/<序號>`）；
  2. 一個都沒做出來時，用 `pick.wish.lifesteal/draw` 專門補抽，骨架輪流指定打擊、範圍，出題條件（關鍵字、武器、手上已有）照舊，最多 `候選量 ÷ 2` 個種子；
  3. 兩步合計最多加 `WISH_TAG_EXTRA`（3）個設計。
- 只許「治療」、只許「傷害」、種類是被動或反應時都不做（測試用 spy 確認 `add_lifesteal` 沒被呼叫）。
- 不改一般組合器；`pick.wish` 主串流不變，所以沒有「傷害＋治療」的願望，候選逐字不變。

### 2.2 測試

- 新 `tests/skillgen/test_wish_lifesteal_sk5.py`（6 條）：吸血版本合法、結構不變、只多一個吸血值、命中傷害＋治療；結構不合的回 `None`；近戰、法器各 3 個種子的「傷害＋治療」都有全命中的吸血候選；同種子結果相同；三種不該做的情況不呼叫。
- `tests/test_wish_coverage.py` 加一條（`#L` 只在傷害＋治療時算；/2 的字串照舊讀得懂）。

### 2.3 覆蓋表（`scripts/wish_coverage.py`，格式 `/2 → /3`）

- 每個合法技能另記吸血版本（`#L…`，`lifesteal_ready` 才做），願望效果同時有傷害、治療時算數。許願池第 2 步的專門補抽沒有另跑桶（同召喚桶以外的配方，量的是「候選做得到」）。
- `run --seeds 40 --workers 8`（768 桶，888 秒）＋ `report`，更新 `docs/phases/許願覆蓋表-WC2.md`（資料檔照舊不進版控）。

**「傷害＋治療」各格（%）**

| | 1普 | 1稀 | 1史 | 2普 | 2稀 | 2史 | 3普 | 3稀 | 3史 | 4普 | 4稀 | 4史 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SK-4 | 5.2 | 5.2 | 0 | 5.2 | 1.7 | 1.7 | 5.2 | 1.7 | 1.7 | 5.2 | 1.7 | 0 |
| SK-5 | 26.2 | 22.8 | 21.0 | 28.0 | 17.5 | 19.2 | 28.0 | 19.2 | 17.5 | 28.0 | 19.2 | 17.5 |

- 加「主動」種類標籤時是 25～40%（沒種類標籤時被動 20、反應 10 的權重拉低）。
- 只許「治療」那一列逐格不變（12／9／10／14／7／14／12／5／15／12／5／13）。
- 表上只有配對矩陣的「傷害×治療」兩格（5 → 28）與表頭說明變；做不到 85、極低 36 不變（「傷害＋治療」SK-4 已經離開做不到清單）。

## 3. 戰鬥不變比對

- 腳本放 scratchpad，沒有 commit。改前＝`git archive 1ed3c79f8` 的 `src content config`，`PYTHONPATH`、`TRPG_CONTENT_DIR` 指向舊的（確認載入路徑）。
- 和 SK-4 同一組 60 場：10 張一般圖 × 種子 1、2，加 4 張頭目圖 × 種子 3～12；`--log-json` 的整份資料（去掉 `ruleset`、`ruleset_hash`、`format`）與畫面輸出（去掉寫檔路徑那一行）各比 SHA-256。
- 第 1 項後：`battles=60 different=0`；第 2 項後：`battles=60 different=0`。
- 預期就是 0：第 1 項只改白名單（不進內容 digest）和工坊程式，第 2 項只改許願池。

## 4. 版號、快照、夾具

- 預測：兩項都不碰組合器一般路徑、內容資料與 API 型別，所以 parity 夾具、CLI 快照、OpenAPI、client 夾具都不該變。結果：`-m slow tests/skillgen/test_refactor_parity.py tests/cli` 兩次都全過，OpenAPI 快照測試過，沒有重產任何夾具。
- 升版：只有覆蓋表格式 `wish-coverage/2 → /3`（資料字串多 `#L` 段）。`skill-proposal`、`wish-tags`、`LOG_FORMAT` 都沒動。

## 5. 檢查結束碼

| 檢查 | 時間點 | 結束碼 |
|---|---|---|
| `ruff check .`、`ruff format --check .` | 第 1、2 項 | 0、0 |
| `mypy`（1716 檔） | 第 1、2 項 | 0 |
| `lint-imports`（14 kept） | 第 1、2 項 | 0 |
| `trpg content check`（695 檔、433 招） | 第 1、2 項 | 0 |
| `pytest -n 8 tests/api/tuning tests/content/test_tuning_fields*.py`（219） | 第 1 項 | 0 |
| `pytest tests/api/test_openapi_snapshot.py`（2） | 第 1 項 | 0 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli`（980） | 第 1 項、第 2 項 | 0、0 |
| 前端 `tsc --noEmit` | 第 1 項 | 0 |
| 前端 `vitest run src/tuning src/battle/bs2SilentStrike.test.ts`（4 檔、68） | 第 1 項 | 0 |
| `client build`（截圖用） | 第 1 項 | 0 |
| `pytest -n 8 tests/skillgen`（4596 passed、14 skipped） | 第 2 項 | 0 |
| `pytest -n 8 tests/llm tests/test_wish_coverage.py tests/test_architecture.py`（518；和 skillgen 分開跑） | 第 2 項 | 0 |
| `wish_coverage.py run --seeds 40 --workers 8`、`report` | 第 2 項 | 0、0 |
| 戰鬥不變比對 60 場 | 第 1、2 項 | different=0、different=0 |

沒跑全量 `scripts/check.py`（守則 11，由 PM 跑）；`tests/roguelite`、`tests/api` 其他檔沒跑（許願池只在「傷害＋治療」的願望變，grep 這兩個目錄沒有這種願望的測試）。

## 6. 複雜度例外

沒有新增 `# noqa: C901／PLR0911／0912／0915`。`_lifesteal_draws` 照 `_tag_draws` 加 `# noqa: PLR0917`（一次補抽的參數）。

## 待 PM 決定

| # | 事項 | 我的做法（最保守） | 其他選項 |
|---|---|---|---|
| 1 | 觸發係數開多少 | 規格寫「開放新觸發的係數，例如被利用時 300」；白名單只能用 `triggers[*]` 一次開，所以 15 個有係數的時機全開（不另加「只開某些 ID」的機制） | 加 ID 篩選，只開 SK-3 的 `on_keyword_exploited` |
| 2 | `every_n_hits` 的 n 表沒開 | 鍵是數字（`{2: 500, 3: 600}`），路徑格式寫不出來 | 改 schema 成具名欄位或擴充路徑格式後再開 |
| 3 | `yaml_patch` 放寬錨點 | 只擋路徑經過共用節點的改動，改完仍整份比對；不改 `skill_composer.yaml` 本身（展開錨點會動內容 digest） | 維持整檔擋，改成把組合器的錨點展開 |
| 4 | 吸血版本的範圍 | 只做打擊、範圍骨架的主動技（照 SK-4 的 `lifesteal_skeletons`）；種類標籤是被動、反應時不做；先改造候選、做不出才專門補抽，合計最多 3 個 | 每次都另外補抽；被動、反應也做 |
| 5 | 覆蓋表的模型 | 量「每個合法技能的吸血版本」，第 2 步專門補抽（指定骨架）沒另跑桶 | 加打擊、範圍的指定骨架桶，量得更接近許願池 |

## 開發 PM 裁定（2026-11-19）

合併：main（--no-ff）。不變比對兩次 different=0；parity、CLI 快照不變；`wish-coverage/3` 接受。「傷害＋治療」最好一格 5.2% → 28.0%。

1. 15 個觸發係數全開：接受。數值由使用者自己調，開多不開少。
2. `every_n_hits` 係數表沒開：排進佇列，等白名單支援數字鍵時再開。
3. 錨點規則放寬到只擋「改到共用錨點內容」的改動：接受。仍然逐份比對只差那一個值，也不用動內容 digest。
4. 吸血版本只做打擊、範圍的主動技，最多 3 張：接受，和 4.1.34 第 10 點一致。
5. 覆蓋表量的是「現有候選加上吸血」：接受。
