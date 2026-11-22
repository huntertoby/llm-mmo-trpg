# Phase WL-2 報告：地圖類型清單搬進資料檔

依據：`docs/phases/PhaseWL-2計畫.md`。基準：main `64ec5d206`。分支 `worktree-agent-a351702f31123db08`，沒 push。
沒改數值、地圖內容、抽選權重；沒動 `docs/design/`、`config/`、`CLAUDE.md`、計畫檔，也沒碰 KD-1／HC-8 的檔（`tuning_fields.yaml`、`api/tuning/`、`engine/`、`content/rules/`、`growthPanel.ts`、`OpeningDialog.tsx`）。`classes.yaml` 沒改。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 類型清單從資料讀 | `966858752` | 新檔 `content/map_archetypes.yaml`；刪 `Archetype` Literal、`ARCHETYPES`；型別改 `str`，載入器驗證；矩陣類型欄照資料順序；鎖 roguelite 抽圖序列；`content_counts` 加 `map_archetypes` |
| 2 特殊用途改資料欄位 | `376e5ab1d` | `in_random_pool`、`role`；刪 `TEST/TRAINING/BOSS_ARCHETYPE`、`LEAGUE_EXCLUDED_ARCHETYPES`、giant_checks 的 `BOSS_ARCHETYPE`、`RegionDef` 的寫死禁用清單 |
| 3 寫死分支盤點 | `3ac3828ca` | 防回歸測試 `tests/test_no_archetype_literals.py`；前端新類型走預設的 vitest；上手筆記 |
| 4 新類型只寫資料 | `cfff400ba` | `tests/content/test_map_archetype_new_type.py` |
| 5 收尾 | `f3e7ac1e1` | `classify.py --md` 重產清單 |
| 報告 | 本檔 | |

## 2. 第 1 項：類型清單從資料讀

- 資料：`content/map_archetypes.yaml`（`archetypes:` 一列一種；順序＝原本 `ARCHETYPES` 的順序）。不放在 `content/maps/` 底下，因為那個資料夾每個檔都當成一張地圖。
- Schema（`trpg.content.maps`）：`MapArchetypeDef`（`id`、`in_random_pool`、`role`）、`MapArchetypeTable`（id 不可重複；`ids()`、`get()`、`unknown_problem()`、`in_random_pool()`、`has_role()`、`role_ids()`、`role_label()`）。
- `MapDef.archetype: str`（`ID_PATTERN`）、`RegionDef.map_pool: tuple[str, ...]`。
- 載入（`library/load.py`）：
  - `map_archetypes.yaml` 必填，在 `regions.yaml` 前讀（`files` 順序只多這一個檔，在 `item_gen` 與 `regions` 之間）。
  - 地圖：`未知的地圖類型 'volcano'（可用：bridge_chasm、…）`，錯誤指向該地圖檔。
  - 區域：`區域 cloud_ridge 的 map_pool：未知的地圖類型 'volcano'（可用：…）`，指向 `regions.yaml`。
- `ContentLibrary.map_archetypes`，跟著 `load_library(資料夾)` 走，**不靠 `TRPG_CONTENT_DIR`**（和 WL-1 的骨架不同；schema 層不驗類型，只驗格式）。
- 會用到清單順序的地方只有 `trpg sim matrix` 的類型欄：`format_matrix(report, archetype_order=())`，CLI 傳 `library.map_archetypes.ids()`，結果和原本逐字相同。不傳時照報表裡出現的順序（只有單元測試這樣呼叫）。
- roguelite 的 `make_plan` 本來就是 `sorted(...)` 類型，不看清單順序，沒動。
- 鎖住：`tests/roguelite/test_start.py::test_the_same_seed_draws_the_same_map_sequence`（種子 0、3、7 的地圖＋勝利條件，值取自基準 `64ec5d206`）。
- 計數：`tests/content_counts.json` 加 `map_archetypes: 11`；`test_map_archetypes.py` 改讀它，並改成「進抽選的類型＝8 種一般類型」「role 對應」。

## 3. 第 2 項：特殊用途改用資料欄位

- `test`、`training`、`boss` 三列加 `in_random_pool: false` 與同名的 `role`。
- `role` 的值是 `Literal["test", "training", "boss"]`（用途，不是類型 id）；程式一律問 `has_role(類型, 用途)`、`in_random_pool(類型)`。
- 原本 `RegionDef` 的「map_pool 不可含 test、training、boss」搬到載入器（`_region_pool_problems`），訊息相同：`區域 X 的 map_pool 不可含 boss`。
- 錯誤訊息裡原本寫死的類型名改由資料帶入（`role_label`），現在的資料下逐字相同：`地圖 X 的類型必須是 training，收到 Y`、`不是 Boss 地圖（archetype: boss）`。
- 介面變動（加參數 `archetypes`／`archetype_table`）：`roguelite_problems`、`workshop_problems`、`giant_problems`、`world_map_problems`、`season_problems`、`_load_world_maps`、`_load_world_season`；呼叫它們的測試都改了。

## 4. 第 3 項：寫死分支盤點

用 grep 掃 `archetype` 與 `"test"/"training"/"boss"`（後端、前端、`attack_flow_report`）。**依類型 id 寫死的共 21 處（後端 18、前端 3）；改了 18 處，前端 3 處沒改**（見第 7 節第 1 點）。另外 4 處是常數／型別定義（`Archetype`、`ARCHETYPES`、三個 `*_ARCHETYPE`、giant_checks 的 `BOSS_ARCHETYPE`、`LEAGUE_EXCLUDED_ARCHETYPES`），都刪了，不在下表。行號是基準 `64ec5d206` 的。

| 檔案:行（基準） | 原本 | 改成 |
|---|---|---|
| `content/regions.py:23,39` | `_POOL_BANNED = {test, training, boss}` | 載入器 `_region_pool_problems`：`not in_random_pool` |
| `content/roguelite.py:228` | `archetype == TRAINING_ARCHETYPE` | `has_role(…, "training")`；另加：其他 `in_random_pool: false` 也不能進池（第 7 節第 2 點） |
| `content/workshop.py:70,72` | `!= TRAINING_ARCHETYPE`、訊息帶常數 | `has_role(…, "training")`、`role_label("training")` |
| `content/world_map.py:367` | `== BOSS_ARCHETYPE` | `has_role(…, "boss")` |
| `content/world_season.py:695,696` | `!= "boss"`、訊息寫死 `archetype: boss` | `has_role(…, "boss")`、`role_label("boss")` |
| `content/world_season.py:778` | `in LEAGUE_EXCLUDED_ARCHETYPES` | `not in_random_pool(…)` |
| `content/library/giant_checks.py:147` | `!= BOSS_ARCHETYPE`（地圖預設陣容） | `has_role(…, "boss")` |
| `content/library/giant_checks.py:168` | 同上（一輪的頭目戰） | 同上 |
| `content/library/giant_checks.py:223` | 同上（大世界頭目地點） | 同上 |
| `api/sessions.py:419` | `!= BOSS_ARCHETYPE`（`playable_maps`） | `has_role(…, "boss")` |
| `api/sessions.py:420` | `!= TRAINING_ARCHETYPE`（`playable_maps`） | `has_role(…, "training")` |
| `api/sessions.py:508` | `!= TRAINING_ARCHETYPE`（靶場才能選對手） | `has_role(…, "training")` |
| `cli/sim.py:39` | `not in (TRAINING, BOSS)`（模擬預設地圖） | `in_random_pool(…)`（`test_*` 前綴的地圖 id 檢查保留） |
| `world/battlefield.py:375` | `== BOSS_ARCHETYPE`（頭目戰不切實地地圖） | `has_role(…, "boss")` |
| `world/battle.py:174` | `map_pool - {"boss"}`（大世界抽圖） | 只留 `in_random_pool` 的類型 |
| `sim/matrix.py:443` | `ARCHETYPES` 的順序 | `format_matrix` 的 `archetype_order`（CLI 傳資料順序） |
| `sim/leap_check.py:331` | 合成地圖 `"archetype": "test"` | `role_ids("test")[0]` |
| `client/src/ui/workshop/TryoutPanel.tsx:121` | `archetype === "training"`（選單附註「試玩專用，預設」） | **沒改** |
| `client/src/ui/workshop/TryoutPanel.tsx:122` | `archetype === "boss"`（選單附註「頭目地圖」） | **沒改** |
| `client/src/workshop/tryout.ts:19` | `isTrainingMap`：`archetype === "training"` | **沒改** |

**不是依類型 id 的（沒動）**：

- `world_map.py:368,370` 的 `loc.kind != "boss"` 是地點種類；
- `attack_flow_report.py:75` 的 `Scenario("boss", …, "bandit_lair")` 是情境 id 加地圖 id；
- `summon_report.py:54` 的 `BOSS_MAP = "boss"` 是報表的特殊地圖鍵；
- `roguelite/start.py` 的抽圖只比 `archetype == a`（a 來自資料）；
- `StartScreen.tsx:166` 只顯示類型字串。

**新類型走預設**：表中每一處，沒寫 `role`、`in_random_pool` 預設 true 的類型都走「一般地圖」的分支：

- 會進抽選、會進模擬預設與一般列表；
- 不是靶場、不是頭目地圖；
- 前端沒有附註，也不送對手。

第 4 項的測試、vitest `treats a map of a new archetype like any ordinary map` 有實際跑過。

**防回歸**：`tests/test_no_archetype_literals.py` 掃 `src/trpg`，擋 `archetype ==/!= "…"`、`archetype in ("…")`、`map_pool - {"…"}`、`*ARCHETYPE(S) = …` 常數、`type …Archetype = Literal`。
- 對基準跑會抓到 9 處，現在 0。
- 前端那 3 處列在 `FRONTEND_KNOWN`，只能變少。

**測試裡寫死的類型數**：沒有 `== 11` 這種斷言，原本是 `set(ARCHETYPES) == 8 種 ∪ 3 種`；改成讀 `COUNTS["map_archetypes"]`（第 2 節）。

## 5. 第 4 項：新類型只寫資料（`tests/content/test_map_archetype_new_type.py`）

做法：把正式內容複製一份，只改資料，再用 `load_library(資料夾)` 載入（不用設環境變數）。

- `map_archetypes.yaml` 加兩種類型：
  - `dunes`：沒有 `role`；
  - `sealed`：`in_random_pool: false`。
- 加兩張地圖：
  - `sand_dunes`：照 `open_plain`，只換 id 與類型；
  - `sealed_vault`：照 `swamp`，只換 id 與類型。
- `sand_dunes` 放進 roguelite 地圖池，`dunes` 放進雲嶺的區域地圖池。

結果：

- 載入成功，`ids()` 最後兩個是 `dunes`、`sealed`；
- roguelite：30 個種子裡抽得到 `sand_dunes`，同一輪類型仍不重複；`sealed_vault` 沒被抽到；
- 大世界：雲嶺 60 個種子的遭遇抽得到 `sand_dunes`，抽不到 `sealed_vault`；
- 模擬預設地圖有 `sand_dunes`、沒有 `sealed_vault`；網頁地圖列表有 `sand_dunes`；
- `sand_dunes` 跑 2 場戰鬥都完成，沒有例外；
- `sealed_vault` 放進 roguelite 池會被擋下：`不進抽選的地圖類型（in_random_pool: false）不能進地圖池：sealed_vault`；
- `sealed` 放進區域池會被擋下：`區域 cloud_ridge 的 map_pool 不可含 sealed`。

## 6. 一致性比對與檢查

### 6.1 一致性比對（基準 `git archive 64ec5d206 src content scripts`）

| 比對 | 結果 |
|---|---|
| 地圖類型相關輸出（`wl2_dump.py`）：roguelite 60 個種子的地圖、勝利條件、戰鬥種子、敵人；模擬預設地圖；`playable_maps` 四種組合；矩陣全類型的文字報表 | 位元組相同（第 1、2 項後各比一次） |
| 逐招預算＋驗證 442 招（`hc7b_dump.py`） | `same=442 different=0` |
| 每張地圖 3 種子 | `battles=51 different=0` |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | `cells=204 different=0`（不看 `timing`） |
| 78 場（`compare78.py`；合併後對 main `c9acff0d7`） | `battles=78 events=26741 different=0`；內嵌規則包差異 0 條 |
| CLI 快照、parity、前端夾具 | 全量裡的對應測試都通過（6.3） |

### 6.2 開發中的檢查

每項 commit 前都跑了下面這些，結束碼都是 0：

- ruff check、ruff format --check、mypy（src tests scripts）、lint-imports；
- `trpg content check`（705 檔、442 技能）、`classify.py --check`（沒歸類 0）、`--unused`（沒有輸出）；
- 相關測試：`tests/content`、`tests/world`、`tests/roguelite`、`tests/api`、`tests/sim`、`tests/cli`；
- vitest `workshop.test.ts`（31 passed）。

第 2 項第一次跑時有 4 個失敗，都是測試要跟著改：
- 新訊息的措辭；
- `RegionDef` 不再擋 `test`／`training`／`boss`。

改完後重跑通過。

### 6.3 全量

開發 PM 排程後，全部 commit 完 `git merge --no-edit main`（合進 main `c9acff0d7`，含 KD-1、HC-8），merge commit `f1692fc15`。
- 衝突只有 `docs/phases/寫死數值-清單.md`：取 main 那份後用 `--md` 重產。
- `content_counts.json` 自動合併，兩邊都保留（`map_archetypes 11`、`statuses 120`）。
- `classify.py --check` 0、`--unused` 沒有輸出。

| 檢查 | 結束碼 |
|---|---|
| `scripts/check.py` | 0（pytest 18430 passed、8 skipped；vitest 4905 passed）；已寫下通過戳記 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed） |
| `corepack pnpm -C client build` | 0 |
| `compare78.py` | 0（different=0） |

跑完之後只改了本報告（`.md`），沒有改程式。

## 7. 待 PM 決定

1. **前端 3 處仍看類型 id**（`TryoutPanel.tsx` 兩個附註、`tryout.ts` 的 `isTrainingMap`）。
   - 要改成讀資料，API 的地圖摘要（`MapSummary`）要加 `role`。這會改 `schema.d.ts` 與前端夾具 `workshop/fixtures/arena.json`，和驗收的「前端夾具 different=0」衝突，所以這段沒改。
   - 新類型走預設（沒有附註、不是靶場），不會報錯；有 vitest 與防回歸測試鎖住。
   - 要做的話，下一段加 `role` 並重產夾具。
2. **roguelite 地圖池變嚴**：原本只擋靶場類型；現在所有 `in_random_pool: false` 的類型都擋（新訊息「不進抽選的地圖類型…」），靶場的訊息照舊。
   - 現有內容沒有受影響。
   - 理由：欄位名就是「進不進抽選」，roguelite 池是一般抽選。
   - 要維持只擋靶場的話，刪掉這條即可。
3. **`role` 沒有限制「同一用途只能有一種類型」**，也沒有限制「有 role 的一定 `in_random_pool: false`」。
   - 判斷都用 `has_role`，多種也能運作。
   - 錯誤訊息用 `role_label` 把多個 id 以「、」連起來。
4. **沒有「程式需要的用途」必備檢查**（類比 WL-1 b 段的骨架）。
   - 拿掉 `role: training` 的類型時，`workshop.yaml` 的檢查會擋下（訊息「類型必須是 role: training」）。
   - 拿掉 `role: test` 的類型時，`sim/leap_check.py` 的 `field_as_battle_map` 會 IndexError（開發用量測工具）。
   - 拿掉 `role: boss` 的類型時，頭目地圖、賽季 Boss 的檢查會擋下。
   - 要不要加中文的必備檢查，請 PM 決定。
5. **`format_matrix` 不傳順序時**照報表出現的順序，不再是內建清單。CLI 有傳，結果不變；只有單元測試這樣呼叫。
6. **`map_archetypes.yaml` 必填**：沒有這個檔的內容資料夾會載入失敗。目前沒有不完整的測試內容資料夾。

## 8. 複雜度與 noqa

沒有新加 `# noqa`（測試裡兩處既有寫法的 `PLC0415` 函式內匯入除外，照該檔原本的風格）。`_world_problems` 的參數超過 5 個位置參數上限，新參數改成 keyword-only。
