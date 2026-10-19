# Phase 3D-4b 報告：召喚（圖騰、內容與網頁）

## 1. commit

| commit | 內容 |
|---|---|
| f9760ee | 圖騰（單位範本 `totem`、事件 `totem_pulsed`、光環結算）、召喚物「戰意圖騰」、技能「召喚元素之靈」「立起圖騰」、build「召喚師」、召喚 AI 係數搬進 `content/ai_profiles.yaml`、AI 對圖騰的評分與選位、預算公式、`skills show` 去掉召喚的「（自己）」、CLI 網格與單位表標示、`LOG_FORMAT` `/24`、CLI 快照重錄 |
| 34c0344 | 預覽回傳 `summons`、`UnitView.totem_radius`；網頁：召喚物外觀、HUD 召喚物清單、行動順序列、技能預覽、圖騰光環；OpenAPI／型別重產；vitest 與 API 測試 |
| （接著一個 commit） | `tests/api/test_routes.py` 預覽欄位清單加 `summons` |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 圖騰（引擎與資料）

- `content/units/summons/summon_war_totem.yaml`：戰意圖騰，HP 18、`speed: 0`、`ai_profile: guard`、`reactions: []`、`totem: {radius: 2, status: empowered, duration: 2}`。
- `UnitTemplate.totem`（`TotemSpec`：`radius` 1–4、`status`、`duration` 1–4）：必須是召喚物且 `speed` 為 0（schema 檢查）；狀態必須是既有的有益狀態（載入時檢查）。
- 規則（`trpg.engine.summons.pulse_totem`、`turns.start_turn`）：圖騰的回合 AP 為 0（不攻擊、不施放、不移動，合法動作只剩結束回合，驅動迴圈自動結束）；**自己的回合開始時**，曼哈頓距離 `radius` 內的友方（含召喚者；不含圖騰自己與其他圖騰）依單位 ID 順序獲得（或刷新）光環狀態，來源記為圖騰。範圍內沒有友方時不發事件。
- 新事件 `totem_pulsed`（圖騰、狀態、持續、半徑、目標清單），後面接各目標的 `status_applied`。紀錄文字：「戰意圖騰1 散發光環（2 格內）：A、B 獲得「激昂」」。
- 圖騰與其他召喚物共用 3D-4a 的持續、上限（同召喚者最多 2 個，最舊的消失）、召喚者離場即消失、不計勝負、無源力等規則。

### 2.2 內容與預算

- 技能 `skill_summon_spirit`（召喚元素之靈：AP 1、法力 10、冷卻 4、指定格射程 4、持續 3 輪，預算 96.0%）、`skill_plant_totem`（立起圖騰：AP 1、法力 8、冷卻 4、射程 3、持續 2 輪、縮放 wis，預算 73.7%）；既有的「喚起骷髏」不變。
- `content/skill_budget.yaml` 新增 `totem_expected_allies_permille: 1000`；圖騰點數 ＝ 光環狀態的 `budget_points` × 預期受惠友方數 × `duration` × `summon_round_value_permille`（沿用 800‰）。
- build「召喚師」`build_summoner`（放在 builds.yaml 最後，不改既有 build 的順序）：火焰法杖、`archer`、HP 42、法力 40；技能 召喚元素之靈、喚起骷髏、立起圖騰、寒鎖。**不帶攻擊技能**（帶火焰箭時 AI 偏好直接攻擊，50 場中 23 場完全不召喚；拿掉後 15 場）。
- `build_trapper` 仍裝著 3D-4a 的「喚起骷髏」（避免動到既有 build 的快照與測試）。

### 2.3 AI 係數（0.9 #8）

`content/ai_profiles.yaml` 新增 `summon: {hit_permille: 500, distance_cost_permille: 100, totem_ally_points: 3}`（`SummonAiRules`，與 `trap`、`rewrite` 同樣由表格層填入每個行為模式）；原本寫在 `engine/ai/summon.py` 的 `SUMMON_HIT`、`SUMMON_DISTANCE_COST` 常數刪除。圖騰的 AI：位置估計看光環內的友方數（沒有友方就不納入），評分 ＝ `support` 權重 × 狀態在 `ally_status_values` 的價值（沒列出用 `totem_ally_points`）× 範圍內友方數 × 持續輪數 × `hit_permille`。

### 2.4 文字（0.9 #10）

`trpg skills show` 的召喚效果不再帶「（自己）」；圖騰技能的說明寫明「不移動、不攻擊，每次行動開始時讓 2 格內的友方獲得「激昂」2 回合」。

### 2.5 CLI

- 網格：召喚物不分陣營，一律用數字代號 1–9（超過 9 個循環），不佔隊伍字母；圖例加「1–9 召喚物（單位表有召喚者與到期輪）」。
- 單位表：召喚物後面加「［召喚物／圖騰：X召喚，第 N 輪結束時消失］」。

### 2.6 網頁

- API：`PreviewOut.summons`（召喚位置、範本、HP、到期輪、圖騰半徑、因上限被擠掉的舊召喚物）；`UnitView.totem_radius`。
- 格子上：召喚物畫成**菱形加青綠外框**（一般單位是圓形），右上角小徽章顯示剩餘輪數（圖騰顯示「圖」）；代號用數字 1–9；在場圖騰的光環範圍有淡青色底色。
- HUD：主角下方「召喚物：」清單，每隻一行「名稱　HP　剩 N 輪（第 E 輪結束時消失）　圖騰：R 格內的友方獲得增益」。
- 行動順序列：召喚物的方塊有虛線青綠外框與右上角剩餘輪數，滑過顯示召喚者與剩餘輪數（本來就跟在召喚者後面，由 `turn_order` 決定）。
- 單位資訊：標籤加「召喚物／圖騰」，多「召喚者」列與「光環」列。
- 技能預覽：召喚位置標「召」（圖騰標「圖」並塗出光環範圍）、被擠掉的舊召喚物標「消」；預覽文字一行「召喚：骷髏戰士（HP 20）出現在 (x, y)，緊接在你之後行動，第 N 輪你的回合結束時消失」，超過上限時加警告行。

## 3. 驗收條件逐條（3D-4b）

### 驗收 1：圖騰不移動、光環與每回合效果正確

| 項目 | 證據 |
|---|---|
| 圖騰範本與 schema | `tests/engine/test_totem.py::test_the_totem_template_is_an_immobile_summon`、`test_a_totem_must_be_a_speed_zero_summon` |
| 不移動、不攻擊（敵人就在旁邊也只剩結束回合） | `test_the_totem_neither_moves_nor_attacks`；整場 `test_the_summoner_build_summons_and_the_totem_empowers_allies_in_a_full_battle`（沒有 `attack_rolled`、`unit_moved`） |
| 光環範圍（含召喚者、不含範圍外與敵人）、持續 2 回合、來源為圖騰 | `test_the_totem_empowers_allies_within_its_radius_each_turn` |
| 每輪刷新 | `test_the_aura_refreshes_every_round` |
| 範圍內沒有友方不發事件 | `test_no_pulse_event_when_nobody_is_in_range` |
| 圖騰不互相加成 | `test_two_totems_do_not_buff_each_other` |
| 紀錄文字、CLI 標示 | `tests/narrative/test_summon_text.py::test_the_totem_pulse_and_cli_marks_summons` |
| 重播一致 | `test_a_totem_battle_replays_exactly`（swamp、種子 4、`build_summoner`：狀態 JSON 與事件逐字相同）；既有 `test_a_summoning_battle_replays_exactly` 仍過 |

### 驗收 2：召喚師 build 在 `trpg sim maps --seeds 5` 有召喚紀錄

`uv run trpg sim maps --seeds 5 --ally-build build_summoner`（10 張地圖 × 種子 0–4 ＝ 50 場；沒有 exception、max_actions、draw 異常，只有 1 次 `one_shot` 資訊類）。報表的「單位範本」表有 `summon_*` 各列、「技能使用」表有 `skill_plant_totem`（最後一張地圖 0.80 次／場）。以同樣的 50 場另用腳本（不是正式模擬）統計召喚事件：

| 項目 | 次數 |
|---|---|
| 有召喚的場數 | 35 / 50 |
| 戰意圖騰 | 36 |
| 骷髏戰士 | 22 |
| 元素之靈 | 7 |
| 召喚物攻擊次數 | 53 |
| 圖騰光環事件 | 47 |
| 到期消失／超過上限／召喚者離場 | 19／2／2 |
| 召喚物被打倒 | 14 |
| 50 場全部分出勝負 | 是 |

測試：`test_the_summoner_build_also_summons_skeletons_and_spirits`（三種召喚物都出現）。

### 驗收 3：網頁、vitest、check.py、重播

- vitest：`client/src/battle/summons.test.ts`（7 個：剩餘輪數、HUD 清單、數字代號、繪製模型的召喚物與光環、光環格子、召喚預覽的位置與文字、圖騰預覽與被擠掉的舊召喚物）；`drawModel.test.ts` 既有測試仍過。共 118 個。
- API：`tests/api/test_summon_api.py::test_the_preview_shows_the_summon_site_and_the_view_marks_totems`；`tests/engine/test_totem.py::test_the_preview_lists_the_summon_and_the_oldest_it_replaces`。
- `uv run python scripts/check.py` 全部通過（ruff、format、mypy、lint-imports、pytest 2363 個、client typecheck、vitest 118 個）。
- 網頁顯示請 PM 用瀏覽器驗收，重現步驟：
  1. 啟動伺服器與前端，開始畫面選地圖 `swamp`、build「召喚師」、種子 3。
  2. 第 1 輪主角回合：點技能列「立起圖騰」，滑過 (3, 5) 等射程 3 內的空格：該格標「圖」，2 格內塗淡青色光環，預覽文字有「召喚：戰意圖騰（HP 18）出現在 (3, 5)……第 3 輪你的回合結束時消失；圖騰不移動、不攻擊……」；點下去施放。
  3. 施放後：格子上出現青綠外框的菱形（代號 1、右上角「圖」）、光環底色；HUD「召喚物：」列出戰意圖騰與剩餘輪數；行動順序列在主角後面多一個虛線方塊；點選圖騰看單位資訊（召喚者、剩餘輪數、光環）。主角結束回合後，圖騰行動，紀錄有「戰意圖騰1 散發光環……」。
  4. 另在任一地圖用同 build：點「喚起骷髏」（射程 3）或「召喚元素之靈」（射程 4）看預覽的「召」標記；同時存在 2 個後再施放第 3 個，預覽會標「消」並有上限警告。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/engine/test_summon_ai.py` | `SUMMON_HIT`／`SUMMON_DISTANCE_COST` 常數搬進 `ai_profiles.yaml`，改用 profile 的 `summon` 係數；`summon_gains` 第 4 個參數由權重改為整個行為模式 |
| `tests/content/test_sim_builds.py` | build 14 → 15（`BUILD_IDS` 加 `build_summoner`、測試改名） |
| `tests/content/test_summon_content.py` | 召喚物範本 2 → 3 |
| `tests/cli/test_budget_cli.py` | 技能總數 105 → 107 |
| `tests/cli/test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/23` → `/24` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 重錄（多 2 個技能、召喚效果去掉「（自己）」）；戰鬥類快照沒有變 |
| `tests/api/test_routes.py` | 預覽回應多 `summons` 欄位 |
| `client/src/battle/testFixtures.ts` | `UnitView` 多 `totem_radius` |

## 5. 新增的複雜度 noqa

沒有 C901、PLR0911、PLR0912、PLR0915。開發中 `ai/summon._value` 超過 PLR0917（位置參數 > 5），改成 `*` 之後的關鍵字參數，沒有加 noqa。測試內延後匯入的 `PLC0415`（`test_totem.py`）不是複雜度類。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/24`**（本段只升一次）：單位範本多了 `totem`、新事件 `totem_pulsed`、圖騰的回合 AP 為 0、預算規則 `totem_expected_allies_permille`；`/23` 的規則包沒有 `totem` 欄位，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **圖騰只做 1 種（光環），且是「圖騰自己回合開始時」給範圍內友方狀態**，不是「友方回合開始時檢查附近有沒有圖騰」。所以光環涵蓋的是圖騰行動那一刻的位置，狀態持續 2 回合；在先攻順序上排在圖騰前面的友方要晚一點才拿到。每回合效果版（對敵人施加狀態）引擎沒做（`TotemSpec` 只有友方）。
2. **光環半徑 2，不是規格文字的「相鄰」**：半徑 1 幾乎只有召喚者受惠；`radius` 是資料欄位，要改相鄰只改 yaml。
3. **圖騰持續 2 輪**：受預算限制（`duration 3` 會到 110%）；圖騰實際只發 2 次光環。要更久需調整法力／冷卻代價或預算係數。
4. **圖騰預算與 AI 都是初值**：`totem_expected_allies_permille` 1000、AI 的 `totem_ally_points` 3；沒有模擬調整。召喚師 build 的勝率沒看（未要求）。
5. **召喚師不帶攻擊技能**：帶火焰箭時 AI 偏好直接攻擊而少召喚。這是 AI 係數問題，平衡階段再處理；`build_trapper` 仍裝「喚起骷髏」。
6. **召喚物在實戰中仍然很快被打倒**（承 4a #9）：50 場中 14 隻在到期前倒下，沒有調整數值。
7. **CLI 的召喚物代號用數字 1–9**（網頁一致）；超過 9 個後循環，只有在多人多召喚時可能出現，需要時再改。
8. **預覽的 `summons` 取自「最多後果」模擬**，召喚位置合法時一定出現；單位 ID 是模擬中的 ID（與真正施放後的 ID 相同，因為 ID 依建立順序分配）。
9. **網頁圖騰的光環底色畫在所有在場圖騰上**（包含敵方；目前敵方不會召喚）；沒有逐單位開關。
10. **`trpg sim maps` 報表沒有專屬的召喚次數欄**（只有單位範本列與技能使用列）；本報告的次數用一次性腳本統計，沒有改模擬指標。

## 8. 代表性輸出

`uv run trpg battle --map swamp --seed 3 --ally-build build_summoner`（連續一段，輸出第 76–90 行）：召喚師英雄在第 1 輪立起戰意圖騰，緊接著結束回合；圖騰（AP 0、移動 0）行動，為 2 格內的三名友方加上「激昂」。

```
  召喚師英雄 以「寒鎖」攻擊 盜賊頭目：d20=5 修正 +1 熟練 +2 = 8（目標 11）→ 失手
  ⟳ 盜賊頭目 反應：藉機攻擊
  盜賊頭目 攻擊 召喚師英雄：d20=3 修正 +1 熟練 +2 = 6（目標 11）→ 失手
  召喚師英雄 從 (0, 6) 移動到 (2, 6)（消耗 2 移動）
  召喚師英雄 施放「立起圖騰」（AP 1，法力 8，冷卻 4 回合）→ 影響 1 格
  召喚師英雄 召喚了 戰意圖騰1，出現在 (3, 5)（緊接在 召喚師英雄 之後行動，第 3 輪 召喚師英雄 的回合結束時消失）
  召喚師英雄 攻擊 盜賊弓手：d20=10 修正 +0 熟練 +2 = 12（目標 11）→ 命中
    盜賊弓手 受到 7 點火焰傷害［骰 4］（元素修正 ×1.25）（天氣 ×0.7），HP 20 → 13
  召喚師英雄 結束回合
— 戰意圖騰1 的回合（AP 0，移動 0）
  戰意圖騰1 散發光環（2 格內）：召喚師英雄、標準隊友（戰士）、標準隊友（弓手） 獲得「激昂」
  召喚師英雄 獲得狀態「激昂」（2 回合）
  標準隊友（戰士） 獲得狀態「激昂」（2 回合）
  標準隊友（弓手） 獲得狀態「激昂」（2 回合）
  戰意圖騰1 結束回合
～ 環境回合 ～
  (1, 1) 出現了水
  (6, 1) 出現了水
```
