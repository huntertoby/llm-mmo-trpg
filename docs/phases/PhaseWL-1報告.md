# Phase WL-1 報告：去掉寫死的計數與白名單（a 段：後端與測試）

依據：`docs/phases/PhaseWL-1計畫.md`。基準：main `a71ce2dc3`。分支 `worktree-agent-a9865f3634c0df0cf`，沒 push。
沒改數值、沒動 `docs/design/`、`config/`、`CLAUDE.md`、計畫檔。前端沒動（b 段）。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 `SKELETON_IDS` 改從資料讀 | `8a1bdb01c` | 刪掉常數；骨架清單＝`content/skeletons/` 的檔，順序照新欄位 `order`；只寫資料加骨架的測試 |
| 2 其他同類的寫死清單 | `860c0314c` | 盤點（第 3 節）；圖示的兩份元素代碼改由 `Element` 推，不再各抄一份 |
| 3 測試的內容計數改從快照推 | `90c7b8b1c` | `tests/content_counts.json`＋`tests/content_counts.py`＋過期檢查；改 10 筆斷言；上手筆記 |
| 4 收尾 | `edc1588a4` | `classify.py --md` 重產清單；`--check` 0、`--unused` 沒有輸出 |
| 報告 | `1c33212f3` 起稿；之後一個 commit 補結果 | |

## 2. 第 1 項：骨架清單從資料讀

### 2.1 做法

- 每個 `content/skeletons/<id>.yaml` 加 `order`（10、20、…、160，照原本 `SKELETON_IDS` 的順序）。`strike.yaml` 檔頭補一行說明。
- `SkeletonDef.order: int`（≥ 0，必填）。
- 新函式 `trpg.content.yaml_sources.skeleton_ids()`（由 `trpg.content.skills` 匯出）：讀目前內容資料夾的 `skeletons/*.yaml`，依 `order`（同值依 ID）排序。
  - 跟著 `TRPG_CONTENT_DIR` 走，做法和 `EffectSpec` 的範圍表一樣：以環境變數的值當快取鍵，每個資料夾只讀一次。
  - 同模組其他清單固定讀內建 `content/`；這份是例外，模組說明已註明。
- 原本用 `SKELETON_IDS` 的地方都改呼叫 `skeleton_ids()`：
  - cli（兩個 `--skeleton` 的 `choices`）；
  - `SkillDef.skeleton`、`FollowupSpec.skeleton` 的驗證（錯誤訊息逐字相同）；
  - `PrimitiveDef` 的 `allowed_skeletons`；
  - 工坊的骨架選單（`skillgen/options.py`）、動作段的骨架（`option_followup.py`）。
- `SkeletonDef` 拿掉「id 必須在清單內」：清單就是檔案本身，檔名＝id 由 `_load_dir` 檢查。
- `_check_skill_rules` 原本的「缺少骨架資料檔」改成兩項（新函式 `_check_skeleton_index`）：
  - `order` 不可重複；
  - 技能和複合技能第二段用到的骨架都要有資料檔，訊息仍是「缺少骨架資料檔：trap（skill_… 用到）」。
- 型別本來就是 `str`，沒有 `Literal` 要改。

### 2.2 順序逐字相同

`skeleton_ids()` 現在回傳 strike、area、control、displace、builder_finisher、combo、trap、aura、summon、reaction、stance、passive、modifier、consume_status、rune、sacrifice，和原本的常數相同。所以工坊選單、CLI 的 `choices`、錯誤訊息的「可用：」都不變。第 6 節的 CLI 快照、parity、前端夾具也都沒變。

`library.skeletons` 仍照檔名字母排序。很多地方逐一走它（隨機組合器、玩家文字、保底），這個順序沒動。

### 2.3 依 id 分支的程式

沒動。新骨架沒有特殊行為時都走預設，測試裡實際組出、驗證過：

- `random_composer.py`：`_skeleton_feasible` 看 `ComposerTraits` 欄位；`kind in ("reaction", …)`、`_STACK_SKELETON` 都是等值比較，不在就走一般主動骨架。
- `validate.py`：`COMPOSITE_SKELETON` 是等值比較。`library.skeletons[skill.skeleton]` 在 schema 驗證之後才會走到，未知的骨架在那之前就被擋下。
- `composer_recipes.py`、`flash_major.py`：只是產生指定骨架（summon、passive、reaction…）的技能，不讀輸入的骨架。
- `proposal_topup.py` 的 `FILLER_PREFERENCE`：表外的骨架依核心效果的對象決定（原本就有的預設）。

### 2.4 新骨架只寫資料的測試（`tests/content/test_skeleton_from_data.py`）

測試把正式內容複製一份，加 `skeletons/test_burst.yaml`（打擊的結構，`order: 999`）和一招用它的手寫技能 `skill_test_burst`，再設 `TRPG_CONTENT_DIR`：

- 載入成功，`skeleton_ids()` 最後一個是 `test_burst`；
- 手寫技能 `validate_skill` 沒有違規；
- `compose_random_skill(7, skeleton="test_burst")` 組得出技能，而且驗證通過；
- 工坊骨架選單最後一個是它；
- 沒設 `TRPG_CONTENT_DIR` 時被擋下，訊息是「未知的骨架 'test_burst'」；
- `order` 重複時被擋下，訊息是「骨架的 order 重複：strike、test_burst」。

## 3. 第 2 項：其他同類的寫死清單（盤點）

先掃 `src/trpg` 所有模組層與函式內的字串元組、集合、字典鍵，和 `content/` 的 id 對照。腳本放在 scratch，沒進 repo：`scan_lists.py`、`scan_full.py`。

| 類別 | 例子 | 處理 |
|---|---|---|
| 抄了一份內容 id、能直接改 | `narrative/skill_icon.py` 的 `ELEMENT_IDS`、`skill_icon_art.py` 的 `_ELEMENT_IDS`（兩份一樣的 9 個元素） | **改**：`tuple(e.value for e in Element)`，順序相同。元素本身是 `Element` 列舉（同 `Surface` 一類），所以來源是列舉，不是 `elements.yaml` |
| 引擎實作清單（資料必須涵蓋） | `REQUIRED_SHAPES`（13）、`REQUIRED_CONDITIONS`（24）、`REQUIRED_STATUSES`（14）、`WeatherTable` 的 clear／rain／fog／night | 不改。這些是「引擎認得、資料要有」，方向和白名單相反，加內容不用改。和 `REQUIRED_TRIGGERS` 同類，屬 E 系列 |
| 引擎觀察點 | `SKILL_REACTION_EVENTS`（9）、`REROLL_EVENTS`、`REQUIRED_TRIGGERS` | 不改（E 系列） |
| `Literal`／列舉判別欄位 | 詞條 `kind`、`RuleChangeKind`、`SkillKind`（`FLASH_KINDS`、`SKILL_KINDS`、`_KINDS`…）、`AffinityRank`、`Surface`、`Element` | 不改（E 系列） |
| 行為用的子集 | `FILLER_PREFERENCE`、`CLOSED_SKELETONS`、`_FOLLOWUP_SKELETONS`、`_HAND_WRITTEN_PRIMITIVES`、`ON_HIT_PRIMITIVES`、sim 的 build／地圖選擇、`enemy_moves.EXEMPT` | 不改。是行為，不是整份清單 |
| 引擎處理器表 | `engine/preview.py`、`engine/ai/coverage.py`、`narrative/skills.py` 以原語為鍵的字典 | 不改。每個原語都有自己的處理 |
| 中文名稱表（後端） | `equipment.py` 的 `_OFFHAND_ZH`（和 `offhands.yaml` 的 `name_zh` 相同）、`api/tuning/objects.py` 的 `_ELEMENT_ZH`（和 `elements.yaml` 相同，加上 `chosen`） | **沒改**，待 PM 決定（第 8 節第 3 點） |

## 4. 第 3 項：內容計數改從快照推

- 快照：`tests/content_counts.json`（鍵照字母排序的 JSON）。
- 怎麼數：`tests/content_counts.py` 的 `COUNTERS`（正式內容庫）。測試用 `COUNTS["skeletons"]` 這種寫法。
- 重產：`uv run python -m tests.content_counts`（寫進 `docs/dev/上手-內容資料與模擬.md` 第四節第 1 點、第五節「技能」列）。
- 過期檢查：`tests/test_content_counts.py`。算出來和快照不同就失敗，並提示重產指令。
- 現在的快照：affixes 81、keywords 16、skeletons 16、skill_files_without_gear 439、skill_triggers 17、skills 442、statuses 119。
  - `statuses`、`skill_triggers` 後端沒有斷言在用，先放著，b 段前端可以讀同一份。

### 改過的斷言（10 筆）

| 檔案 | 原本 | 現在讀 |
|---|---|---|
| `tests/content/test_skill_rules_content.py`（測試改名 `test_every_skeleton_has_a_data_file`） | 16 | `COUNTS["skeletons"]` |
| `tests/content/test_equipment_content.py`（測試名拿掉 81） | 81 | `COUNTS["affixes"]` |
| `tests/api/test_gear_api.py` | 81 | `COUNTS["affixes"]` |
| `tests/content/test_skill_scaling.py` | 442 | `COUNTS["skills"]` |
| `tests/narrative/test_skill_icon_art_qi2a.py` | 442 | `COUNTS["skills"]` |
| `tests/api/tuning/test_yaml_patch_nw2a.py` | 439 | `COUNTS["skill_files_without_gear"]` |
| `tests/content/test_tuning_fields_nw2a.py` | 439 | `COUNTS["skill_files_without_gear"]` |
| `tests/skillgen/test_stack_keywords_kw1.py` | 16 | `COUNTS["keywords"]` |
| `tests/skillgen/test_wish_pick_pk4.py` | 16 | `COUNTS["keywords"]` |
| `tests/content/test_skills_content.py`（不是計數；`SKELETON_IDS` 改成 `skeleton_ids()`） | — | `skeleton_ids()` |

最後一列不是計數，所以計數斷言是 9 筆。另外 `test_skill_rules_content.py` 的「缺少骨架資料檔」測試照舊通過（訊息多了用到它的技能）。

### 沒動的

- 幾何、骰子、結算數字：`ring` 16 格、`crit_range == 17`、HP、金幣等。
- 規格本身的數字：子集的大小，例如 `filled == 47`（美術清單 36＋11）、`len(forms) == 14`、形態技 10、`len(new) == 35`。
- 其他內容表的總數：地圖 10／14／15、種族 10、開發起始包 29、誓約模板 15、外觀 42／10／8、召喚外觀 21、圖示道具 64、介面音 22、情境模板 30／12／10、古語 27、世界地圖 18／17、區域事件骨架 16、許願選單 16（`wish_menu` 不一定等於全部關鍵字）。待 PM 決定要不要併進快照（第 8 節第 2 點）。
- 前端測試的 119（`STATUS_IDS`）：屬 b 段。

## 5. 第 4 項：收尾

- `classify.py --check`：0，沒歸類 0。
- `--unused`：沒有輸出，所以沒有要刪的規則。
- 新增的數字字面值只在 docstring（`py-docstring` +3），清單用 `--md` 重產。

## 6. 一致性比對（基準 `git archive a71ce2dc3 src content scripts`）

腳本放在 scratch，沒進 repo，沿用 HC-7 的 `hc7b_dump.py`、`hc7b_cmp.py`、`hc7b_census_cmp.py` 和 `compare78.py`。基準執行時確認過，載入的 `trpg` 來自基準那份。

| 比對 | 結果 |
|---|---|
| 逐招預算＋驗證 442 招（`hc7b_dump.py`） | `same=442 different=0` |
| 每張地圖 3 種子 | `battles=51 different=0` |
| 78 場（`compare78.py`，同 a 段那組） | `battles=78 events=26206 different=0`；內嵌規則包差異 0 條 |
| 組合器 census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | `cells=204 different=0`（不看 `timing`） |

## 7. 檢查

開發中每項 commit 前跑 ruff check、ruff format --check、mypy、lint-imports、`trpg content check`、`classify.py --check` 與相關測試（經看門狗），結束碼都是 0。

**交件前全量**（全部 commit 後 `git merge --no-edit main`：合進 main `98ad9fa6f`，main 多的只有文件）：

| 檢查 | 結束碼 |
|---|---|
| `scripts/check.py` | 0（pytest 18256 passed、8 skipped；vitest 4866 passed）；已寫下通過戳記 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed） |
| `corepack pnpm -C client build` | 0 |
| `trpg content check` | 0（704 檔、442 技能） |
| `classify.py --check`／`--unused` | 0／沒有輸出 |

跑完之後只改了本報告（`.md`），沒有改程式。

## 8. 複雜度與 noqa

沒有新加 `# noqa`。「缺少骨架」和「order 重複」的檢查拆成 `_check_skeleton_index`，`_check_skill_rules` 沒有超過複雜度上限。

## 9. 待 PM 決定

1. **自訂內容資料夾要設 `TRPG_CONTENT_DIR`**：
   - schema 驗證時還沒有內容庫，所以 `skeleton_ids()` 跟著環境變數走（同 `EffectSpec` 的範圍表）。
   - 只用 `load_library(其他資料夾)`、沒設環境變數時，新骨架會被當成未知（測試有覆蓋這個行為）。
   - CLI 的 `--skeleton` 選項在建 parser 時讀，也看環境變數。
   - 要改成跟著 `load_library` 的資料夾走的話，要用 context 變數或 pydantic 的驗證 context，改動面大，這段沒做。
2. **其他內容計數**（第 4 節「沒動的」第 3 點）這段只做了規格點名的那幾類（骨架、詞條、技能、關鍵字；狀態、觸發時機只有前端在數）。其他也要併進快照的話，下一段順手加 `COUNTERS` 即可。
3. **後端的中文名稱表**：`_OFFHAND_ZH`、`_ELEMENT_ZH` 和資料的 `name_zh` 相同。改成讀資料要把副手表或內容庫一路傳進去，而且不加的話新副手只會顯示 id，不會報錯。這段沒做。
4. **拿掉「必須有這 16 種骨架」**：刪掉某個骨架檔時，如果還有技能用它，照樣擋下；沒有技能用的話就能載入。依 id 分支的程式（例如 `composer_recipes` 的 `library.skeletons["summon"]`）在骨架被刪時會出錯。照規格「資料是唯一來源」沒有再留一份必備清單，要不要對有特殊行為的骨架加必備檢查，請 PM 決定。
5. **`order` 的值**：用 10 的倍數，留空間插隊。`order` 是必填，沒有預設值（新骨架一定要決定排哪裡）。
