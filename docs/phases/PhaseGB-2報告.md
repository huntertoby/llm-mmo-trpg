# Phase GB-2 報告｜巨型頭目：灰燼之心內容＋熔心坑改圖＋工坊白名單

> 實作者（Opus 5.5），2026-11-14，起點 main `47c301d3a`（含 GB-1c 合併與裁定）。規格：`docs/phases/PhaseGB計畫.md` 第 6 節（6.1～6.5）、第 4 節 GB-2 列、0.2 R5～R7、0.3 T17、T20、第 11、12 節與末節「開發 PM 裁定」（R1～R7 照建議、R6 選 A；#164）。設計：`docs/design/19-灰燼荒原與賽季主線.md` 19.2.3（含「巨型頭目段 GB 補定的細節」）、`docs/design/05-戰鬥.md` 5.12。GB-1c 裁定：第 1 排火地（階段 `tiles`）與 `grow_surface` 一起寫——已照做。
> 引擎結算、AI 評分、`client/`、設計文件都沒動。**有一項規格做不到**（吸氣「4 格內」，第 7 節第 1 點、待決 1），照最保守做法沒改形狀。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 灰燼之心（6.1） | `footprint: 3`；部位 `shell_seam`（殼縫，`tiles` (−1,0)、(1,0)，`counts_as_behind`，破＝停 `molten_shell`）、`vent`（熔岩噴口，北排 3 格，`reach: ranged`，破＝永久封 `skill_lava_splash`）、`core`（核心，中心格，`melee_from: any_face`，`exposed_in: [breath, meltdown]`，破＝打斷蓄力＋封 `skill_heart_inhale` 2 輪）；部位血量各 200‰ 占位（加總 600‰），護甲抗性不寫。第 2 階段召喚拆成兩筆 `count: 1`，`at` (3, 3)、(7, 3)。第 3 階段 `tiles` 改成南緣外一排 (4, 5)、(5, 5)、(6, 5) ＋ `grow_surface: {surface: fire, max_rows: 4}`。檔頭註解寫 #152、#164、19.2.3、占位值。技能 ID 沒增減 | `edd6977d8` |
| 熔心坑（6.2） | 敵方起始 `[(5, 3), (2, 4), (8, 4), (5, 6)]`、`giant_facing: {ashen_heart: south}`；矮牆 (4, 9)、(7, 9)；冷卻井 (3, 4)、(7, 4)、(3, 8)、(8, 8)；高台 (2, 9)、(9, 9) 高 1；坑底 8×8、岩漿、通路、我方起始區不變；檔頭註解改成新配置 | `edd6977d8` |
| 技能（6.3） | `skill_lava_splash`：`shape: self`（不選格）、`followup.anchor: farthest_enemy`，名稱照舊「熔岩濺落」。`skill_heart_inhale`：**只加註解**（形狀改不了，第 7 節第 1 點） | `edd6977d8` |
| 被固定答案打到的測試 | 7 檔（第 4 節） | `edd6977d8` |
| 工坊白名單（6.4） | `content/tuning_fields.yaml` 加 `parts[*].on_break[*].rounds`、`phases[*].grow_surface.max_rows`（都 `existing_only`）；`api/tuning/objects.py` 的展開（`_BREAK_FIELD_TYPES`）、標籤、擋的範圍、沒寫時的說明；新測試 `tests/api/tuning/test_giant_tuning_gb2.py`（T-A1 四項、T-A2 一項）。`src/trpg/content/tuning_fields.py` 不必改（`_leaf_ok` 本來就吃 `int | None`） | `67ea2216d` |
| CLI 快照 | 重產 `skills_list`、`skills_show_all/05` 兩鍵 | `a7e0ecb7f` |
| 文件 | 本報告；`docs/dev/上手-內容資料與模擬.md`（第二節延遲段錨點、第四節第 53 點、第七節 GB-2 欄位） | 第 4 個 commit |

## 2. 逐條驗收（6.5）

| 驗收 | 結果 | 證據 |
|---|---|---|
| 1. `trpg content check`；6.5 列的測試 | 過 | `content check`：「共 690 個檔案；跨檔案檢查…通過；429 個技能通過預算與結構驗證」，結束碼 0。相關測試見下（第一次跑 11 個失敗＝第 4 節的固定答案，逐項改完後全過） |
| 2. 不變比對 | 過：除熔心坑 12 場外 34 場 `different=0` | 第 3 節 |
| 3. CLI 快照逐鍵預測 | **預測與實際不同**：預測 `/05` 一鍵，實際 `skills_list` ＋ `/05` 兩鍵 | 第 4 節 |
| 4. 前端夾具 | `unitDolls.json` 不變（`doll` 沒改）；**`skill_icons.json` 會變一筆**（熔岩濺落），沒重產（`client/` 不動） | 第 4 節、待決 2 |
| 5. 一場紀錄＋重播 | `molten_heart_pit` 種子 2：86 動作 468 事件、種子 7：94 動作 506 事件，都「重播驗證通過」；另跑種子 1、3、9、12 也都通過（事件數與不變比對那一份逐場相同＝跨行程確定） | `trpg battle`、`trpg battle replay` 結束碼 0 |
| 6. 報告含平衡疑慮 | 第 9 節 | |

靜態檢查（commit 前）：`ruff check` All checks passed、`ruff format --check` 2717 files already formatted、`mypy` Success（1608 files）、`lint-imports` 14 kept 0 broken，結束碼都 0。

相關測試（`-n 8`，不帶 `-m`）：`tests/content`、`tests/api/tuning`、`tests/narrative`、`tests/test_architecture.py`、`tests/api/test_encounter_look_uie3b.py`、`tests/api/test_client_fixtures.py`、`tests/api/test_delayed_api.py`、`tests/engine/` 的 `test_enemy_skills_149.py`、`test_lava_splash_bal21b.py`、`test_source.py`、`test_delayed_anchor_bal21.py`、`test_giant_gb1a.py`、`test_giant_gb1b.py`、`test_giant_parts_gb1c.py`、`test_boss_phases.py`、`tests/server/test_season_reset.py`、`tests/world/` 的 `test_ashen_waste.py`、`test_enemy_ai_moves_149.py`、`test_thread_endings.py`（凡是 `tests/` 裡提到 `ashen_heart` 的檔都在內）。結果：**只剩 `tests/narrative/test_skill_icon.py::test_client_fixture_is_current` 1 個失敗**（`client/` 的圖示夾具要重產，待決 2），其餘全過。交件前 `tests/cli -m slow`：重產兩鍵後 44 passed。

## 3. 不變比對（5.4 的 46 場）

腳本在 scratchpad（未 commit）：改前用 `git archive 47c301d3a src content` 解開、`PYTHONPATH` 指向舊 `src`（內容跟著舊 `src`）；地圖預設陣容、效用 AI、`max_rounds=30`；每場比完整事件 JSON、步驟、輪數、勝方、最終 `rng_state`、最終狀態 JSON（拿掉 `final_state.ruleset`）。**沒剝其他鍵**。

- 熔心坑以外 34 場（7 張地圖 × 種子 1、2 ＋ `rift_gate`、`cloud_summit` × 種子 3～12）：**`different=0`**；46 場改前事件總數 20499（同 GB-1a～1c）。
- 熔心坑 12 場全部不同（內容改了，預期）。只列不評：

| 種子 | 改前 勝方／輪／事件 | 改後 勝方／輪／事件 | 改後：部位受傷／破壞次數、施放（濺落／吸氣） |
|---|---|---|---|
| 1 | 敵／4／444 | 敵／4／466 | 7／1、1／1 |
| 2 | 敵／6／617 | **我**／5／468 | 9／2、1／0 |
| 3 | 敵／5／349 | 敵／4／380 | 11／1、1／1 |
| 4 | 敵／5／512 | 敵／5／488 | 13／1、1／1 |
| 5 | 敵／5／421 | 敵／5／402 | 6／0、2／0 |
| 6 | 敵／7／613 | 敵／5／540 | 10／1、1／1 |
| 7 | 敵／6／529 | 敵／6／506 | 8／0、2／1 |
| 8 | 敵／5／516 | 敵／5／372 | 11／0、2／0 |
| 9 | **我**／6／489 | 敵／6／362 | 6／0、3／0 |
| 10 | 敵／5／428 | 敵／4／426 | 3／0、1／1 |
| 11 | 敵／6／540 | 敵／5／523 | 8／1、1／1 |
| 12 | 敵／8／551 | 敵／5／458 | 7／0、2／0 |

  變化原因：灰燼之心變 3×3（佔格、相鄰 12 格、R2 自身範圍變大、視線被身體擋）、部位分流（隊友 AI 已會打部位：PB-1b 的部位變體）、熔岩濺落落在最遠的敵人、第 2 階段蜥蜴從兩側出、第 3 階段火地往南長、改圖。12 場都在 30 輪內分出勝負、重播一致（第 2 節第 5 列）。
- 三個雜湊（改前 → 改後）：

| | 改前 `47c301d3a` | 改後 | 歸因 |
|---|---|---|---|
| `hash_ruleset` | `ae4b48df…b050` | `1bcc22eb9681dfd95e768e7d4b746a1343ba9b7873728b81e78264ae5bd222ba` | 只把 `skill_lava_splash.yaml` 換回舊檔重算＝`ae4b48df…b050`（吸氣只改註解，不影響） |
| `ruleset_hash` | `6e0f469d…efbb` | `6380c88590ee8f27abbcb587549113a37c41f73a8f19c753f36faa2bd16730fe` | 本段改的 5 個內容檔（兩技能、單位、地圖、`tuning_fields.yaml`）換回舊檔重算＝改前值 |
| `content_digest` | `50be396d…8883` | `acc182c5752aa343e3253e8d8602789fffdc42127d045049c42c9216a4f20ccb` | 同上＝改前值 |

## 4. 快照與既有測試的變動

**CLI 快照**：預測只有 `skills_show_all/05`；實際 `skills_list` 也變。查證：`trpg skills list` 每招第二行是形狀摘要（「方陣（射程 4）：護盾…」→「自身：護盾…」），改前改後的列表輸出只差這一行；`skills show skill_lava_splash` 只差「形狀 方陣（射程 4）→ 自身」，`skill_heart_inhale` 逐字相同。把 `skill_lava_splash.yaml` 換回舊檔再跑這兩鍵＝舊雜湊（`b28f2082…`、`273c152b…`）。只用 `UPDATE_CLI_SNAPSHOTS=1 … -k "skills_list or 05"` 重產這兩鍵；7 個戰鬥鍵與其他 15 片不變。

**被固定答案打到的測試**（拿掉本段改動就回到舊值；斷言沒放寬、沒換種子）：

| 測試 | 原因 | 改法 |
|---|---|---|
| `tests/content/test_boss_parts_content.py::test_units_without_parts_do_not_output_the_key` | 有部位的範本清單多了灰燼之心 | `[MIST]` → `["ashen_heart", MIST]` |
| `tests/content/test_ashen_waste_content.py::test_5f5b_balance_values` | 召喚拆成兩筆 | `["heart_ember_lizard"]` → 兩筆 |
| `tests/content/test_delayed_anchor_content.py::test_unset_fields_are_not_serialized` | 熔岩濺落的錨點 `cast_tile` → `farthest_enemy` | `ANCHORED_BUILTINS` 改成「技能 ID → 錨點」 |
| `tests/content/test_giant_content_gb1a.py::test_current_content_has_no_giant_problems` | 內容第一次有巨型單位 | 「沒有巨型單位」→「只有灰燼之心」，`check(lib) == []` 照舊 |
| `tests/content/test_giant_content_gb1a.py::test_giant_facing_must_name_a_known_template` | 只傳 `open_plain` 一張地圖時，熔心坑的世界遭遇被報「戰鬥地圖必須全是頭目地圖」 | 傳 `{**lib.maps, "open_plain": m}`；期望的唯一一條錯誤不變 |
| `tests/api/tuning/test_parts_pb1n.py::test_units_without_parts_get_no_part_fields` | 拿灰燼之心當「沒有部位的頭目」 | 改用 `rift_shard_lord` |
| `tests/engine/test_lava_splash_bal21b.py`（3 項） | 形狀 `square3` 射程 4 → `self`、錨點、施放不帶 `target_pos` | 數字表改新值；施放不帶格子；落點 `SPOT` 改成最遠的敵人 (4, 5)（(4, 4) 距 3、(4, 5) 距 4），3×3 照樣打到兩人、留火地 |
| `tests/world/test_enemy_ai_moves_149.py`（灰燼之心 2 列） | 範本搬到 9×9 空地圖放兩隻：3×3 重疊、而且巨人只能在頭目地圖 | `_phase_template` 本來就拿掉 `immovable`、補速度，再加 `footprint: 1`、`parts: ()`（這檔只驗 AI 選招）；兩招照樣被選到 |

**沒重產的夾具**：`client/src/render/fixtures/skill_icons.json` 的 `skill_lava_splash` 一筆（`segments[0]` 的 `shape_id` `square3` → `self`、`range` 4 → null，`art.motion` `area` → `aura`；其他招逐字不變，用 `tests.narrative.icon_fixture.render()` 對比確認）。派工禁止動 `client/`，所以 `test_client_fixture_is_current` 目前紅，待決 2。

## 5. 改了哪些呼叫點（檔案 × 處數）

| 檔案 | 處 | 說明 |
|---|---|---|
| `content/units/ashen_heart.yaml` | 4 | `footprint`、`parts`、第 2 階段 `spawns`、第 3 階段 `tiles`＋`grow_surface`；檔頭 |
| `content/maps/molten_heart_pit.yaml` | 5 | `heights` 第 9 列、`objects`、`surfaces`、`start_zones.enemy`、`giant_facing`；檔頭 |
| `content/skills/skill_lava_splash.yaml` | 2 | `shape`、`followup.anchor`；檔頭 |
| `content/skills/skill_heart_inhale.yaml` | 0 | 只加註解 |
| `content/tuning_fields.yaml` | 2 | 兩個欄位 |
| `src/trpg/api/tuning/objects.py` | 5 | `_DEFAULTS_ZH` 兩筆、`_BREAK_FIELD_TYPES`、`_part_skipped`、`_part_label`（限時封招）、`_default_zh` 先查表、`_part_limits`（`rounds` ≥ 1）、`field_limits`（`max_rows` 1～9） |

`heart_ember_lizard.yaml` 不必改（開場位置在地圖、召喚位置在頭目範本）。`src/trpg/content/tuning_fields.py` 不必改。GB-1a 待決 7（改成巨人後內容檢查擋到別處）：**沒有擋到**——賽季檔（`season.yaml` 的 `heart_pit_boss`）、世界遭遇 `ashen_heart_court`（地點 `molten_heart_pit` 的戰鬥地圖只有頭目圖）、主線委託、掉落、事件都通過 `content check` 與 `tests/server/test_season_reset.py`、`tests/world/test_ashen_waste.py`、`test_thread_endings.py`。

## 6. 新增 `# noqa`

沒有。

## 7. 規格沒寫到或做不到、採保守做法的地方

1. **吸氣「範圍光環 4」寫不出來**（6.3、R7）：`skill_heart_inhale` 是聚集段（`followup.when: after_gather`），內容 schema 規定聚集段第一段只收 `cross`／`square3`／`ring`（`content/skills/constants.py::GATHER_SHAPES`，`followup.py::_check_after_gather`）；`ring` 半徑上限 2，範圍光環（`allies_in_radius`）半徑上限 3（`content/skill_shapes.yaml`，LLM 也讀這份）。實測 `content check` 兩條都擋。要做到得改內容 schema（聚集段收範圍光環、半徑允許 4——可比照十字 `arm` 用「只有內建內容能寫」的 `content_params`），會牽動 skillgen 選項與 LLM schema，超出本段範圍。**保守做法：形狀不改**（環形 2；GB-1b 的 R2 量法下＝離最近佔格切比雪夫距離恰為 2 的 24 格，拉的方向已由引擎 T7 往最近佔格），只在檔頭寫明。所以這招本段**實際沒變**（技能卡、規則包都不變）。待決 1。
2. **熔岩濺落的技能卡文字**仍寫「下回合開始時在施放時選的格子釋放」（`narrative/skills.py` 的延遲段錨點句只認 `cast_tile` 的寫法）；實際是落在最遠的敵人那一格。敘事不在本段範圍、說書人與戰鬥紀錄（GB-1c 已有「熔岩噴向最遠的 X」）不受影響。待決 3。
3. **工坊欄位**：`rounds` 與 `max_rows` 都設 `existing_only`（永久封招加 `rounds`、沒有生長表面的階段加 `max_rows` 都是結構，不是調數值）；建議範圍 `rounds` 1～5、`max_rows` 1～6（擋的範圍照 schema：`rounds` ≥ 1、`max_rows` 1～9）。限時封招的標籤寫技能 ID（「封住「skill_heart_inhale」的回合數」：`objects.py` 的標籤函式只拿得到單位 YAML，沒有內容庫）。
4. **第 2 階段召喚位置** (3, 3)、(7, 3) 正好是殼縫的近戰攻擊位（T20 原樣）：有人站著時照現行找最近的安全格。
5. 熔心坑敵方起始第 4 格 (5, 6) 是備用（預設陣容 3 隻用不到）。

## 8. 影響

- `LOG_FORMAT` 不升（`/128`）：只改內容與工坊，結算規則沒變（熔心坑的戰鬥變是因為內容）。舊熔心坑戰鬥紀錄內嵌當時的規則包，仍可重播；`ruleset_hash` 變 → 進行中的一輪從頭開始；`content_digest` 變 → 舊世界日誌標成不能重播（使用者 11-12「存檔都可以刪除」）。
- 戰鬥中存檔若停在熔心坑：讀回後照新內容（巨人佔格與舊位置不合），不寫遷移。
- 前端：灰燼之心現在是 3×3、有部位，但前端在 GB-4a／4b 前不認佔格，仍照 `UnitView.pos`＝中心格 (5, 3) 畫成 1 格。瀏覽器實測等 GB-4a。

## 9. 平衡疑慮（不量，只記）

規格第 10 節 8 條本段起全部進實戰（第 6 條火地生長、第 4 條熔岩濺落打最遠的人、第 7 條餘燼蜥追遠要等 GB-3 才有）。另外觀察到（只看不變比對的 12 場，不是量測）：

1. 預設陣容（戰士、弓手、法師）打熔心坑改前改後都幾乎全輸（12 場各 1 場勝），輪數略短（平均約 5.7 → 4.9 輪）；第 3 階段常在第 4～5 輪就到。
2. 部位在 12 場裡破了 7 次（隊友 AI 的 PB-1b 部位變體已在作用，GB-3 還沒加站位）；殼縫破＝熔殼提前沒了，可能讓第 1 階段很短（第 10 節第 5 條）。
3. 吸氣仍是環形 2（第 7 節第 1 點）：以 3×3 量只拉外面第 2 圈那 24 格的人（緊貼頭目的 12 格本來就相鄰、不拉；後段方陣照樣打到貼身的人），3～4 格外的人不受影響，和設計「4 格內」差很多。
4. 熔岩濺落第一段改成 `self` 後 AI 只評「放不放」：12 場每場都放 1～3 次。
5. 兩隻開場蜥蜴 (2, 4)、(8, 4) 和第 2 階段的兩隻 (3, 3)、(7, 3) 都在殼縫攻擊位附近，近戰繞去殼縫要先過蜥蜴。

## 10. 待 PM 決定

1. **吸氣「4 格內」**（第 7 節第 1 點）：要不要排一小段改內容 schema（聚集段收範圍光環＋內建內容可寫半徑 4），還是接受環形 2？目前形狀沒改。
2. **`client/src/render/fixtures/skill_icons.json` 要重產**（`uv run python -m tests.narrative.icon_fixture`，只變熔岩濺落一筆；圖示的動作從 `area` 變 `aura`）：派工禁止動 `client/`，合併時請 PM 或 GB-4a 順手跑；不跑的話 `tests/narrative/test_skill_icon.py::test_client_fixture_is_current` 會紅。圖示換成「光環」動作要不要美術看一眼。
3. **熔岩濺落技能卡寫「施放時選的格子」**（第 7 節第 2 點）：`narrative/skills.py` 要認 `farthest_enemy`（例「落在最遠的敵人那一格」），併進後面動 narrative 的段。
4. CLI 快照預測錯一鍵（`skills_list` 也會因形狀變）：規格 6.5 第 3 點的預測依據不成立，已寫進上手筆記第四節第 53 點。
5. 工坊兩個新欄位的建議範圍（`rounds` 1～5、`max_rows` 1～6）與 `existing_only`（第 7 節第 3 點）。
6. 第 2 階段蜥蜴落在殼縫攻擊位（第 7 節第 4 點），要不要往外移一格（例 (2, 3)、(8, 3)）。
7. `test_enemy_ai_moves_149.py` 的頭目階段測試現在把灰燼之心當 1 格、無部位放空地圖（只驗 AI 選招）；巨型頭目自己的選招與站位由 GB-3 在熔心坑驗。
