# Phase 3D-5 報告：持續區域 `zone`

## 1. commit

| commit | 內容 |
|---|---|
| b41030e | 引擎、內容、AI、紀錄、CLI、視圖：原語 `zone`（三種錨點、`enter`／`turn_start` 結算、移動、表面、到期、施放者離場、上限）、戰鬥狀態 `zones`／`next_zone_id`、四個事件、環境預告、`BattleView.zones`、預算、AI（選位置、收益、避開）、技能說明文字、CLI 網格／圖例／單位表／預告；「戰歌」改寫成跟隨型區域、新技能「火牆」裝進 `build_summoner`；OpenAPI 與 `schema.d.ts` 重產；測試 |
| 6719caf | `LOG_FORMAT` `/25`；CLI 快照重錄（只有 `skills_list`、`skills_show_all`） |
| 56e555e | 網頁：區域半透明底色與方向箭頭、HUD 區域清單、滑過格子的區域說明、環境預告的區域格標記、技能預覽的區域行；vitest |
| 951f0cd | API 測試（視圖、預告、預覽） |
| e53d263 | 測試型別修正（mypy） |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 原語與資料（`content/skill_primitives.yaml`、`EffectSpec`）

```yaml
- type: zone
  anchor: tile | caster | moving
  when: enter | turn_start | both      # 規格寫作 on，見 7 #1
  duration: 1–4                        # 輪
  affects: enemies | allies | all      # 必須明寫
  effects: [1–2 個 damage／heal／shield／apply_status，不可自帶 affects／condition]
  speed: 1–2                           # 只有 moving
  surface: <表面>                      # 可選：新覆蓋的格子留下表面
```

- 結構檢查（`SkillDef._check_zone`）：只能用在主動技能、必須是技能唯一的效果；`moving` 的形狀必須是 `line`／`cone`（沿施放方向前進）且要填 `speed`；`caster` 的形狀必須是 `self`／`ring`／`allies_in_radius`；`anchor`、`when`、`speed`、`effects` 只屬於 `zone`。跨檔案檢查把 `effects` 當成同一技能的效果檢查（`_zone_problems`）。
- 骨架：`aura`（跟隨型光環）與 `control`（控場區域）的核心原語加 `zone`；隨機組合器不使用（`_HAND_WRITTEN_PRIMITIVES`）。
- `core.yaml`：`zone_limit_per_owner: 2`。

### 2.2 引擎（`trpg.engine.zones`）

- **狀態**：`BattleState.zones: list[ZoneState]`（依編號）與 `next_zone_id`。`ZoneState` 存施放者、陣營、技能、錨點、格子（`tile`／`moving` 為絕對座標；`caster` 存形狀與半徑，每次以施放者目前位置展開）、方向、速度、`expires_round`、施放者屬性快照。可序列化、`clone` 涵蓋。
- **建立**：`_Cast.zone` → `create_zone`：超過上限時最舊的先消失（`limit`）、發 `zone_created`、覆蓋的格子留表面、格內的對象算「進入」。
- **進入（`enter`）**：單位的位置從區域外變成區域內才算——單位移動（走路、衝鋒、推擊、傳送、交換都經過 `arrive`）、區域建立、移動型前進、跟隨型隨施放者移動都會造成；在區域內移動、站著不動不算，所以同一次進入只結算一次。記在 `Ctx.zone_entries`，效果佇列清空時（表面、陷阱之後）結算。施放者相對於自己的跟隨型區域不動，不算進入。
- **回合開始（`turn_start`）**：`start_turn` 在表面的回合開始效果之後、陷阱倒數之前，依區域編號結算。
- **結算**：`use_zone_effects`：施放者是建立時的快照（同陷阱），對象只有該單位，效果自動命中、狀態照常擲抵抗，觸發深度 +1（受 `max_trigger_depth` 限制），所以 `on_damaged`、`on_kill` 等既有觸發照常發生。區域不是表面，不觸發 `on_enter_surface`。
- **移動**：環境回合在火勢蔓延之後（`move_zones`）：先讓「施放者不在場而到期」的區域消失，再讓移動型依編號前進 `speed` 格，一次一格（`speed 2` 時中間的格子也會掃到單位）；走到牆壁或地圖外的格子消失，全部消失時區域消失（`blocked`）。每一步發 `zone_moved`，新覆蓋格留表面、上面的對象算進入。跟隨型隨施放者移動時不發事件。
- **消失**：施放者在 `expires_round`（施放輪 ＋ `duration`）那一輪的回合結束時（與召喚物同一規則：每個單位恰好經過 `duration` 次回合開始）；施放者不在場時在那一輪的環境回合；施放者倒下、撤離、（召喚物）消失時跟隨型區域消失（`owner_gone`），固定型與移動型保留到期。
- **事件**：`zone_created`、`zone_moved`、`zone_triggered`（`enter`／`turn_start`、深度）、`zone_expired`（`timeout`／`owner_gone`／`limit`／`blocked`，帶消失前的格子）。
- **環境預告**：`TelegraphChange` 新種類 `zone_moved`（`tiles` ＝前進後的格子）與 `zone_expired`；同一區域一次環境回合只列一項。預告是在狀態複本上跑同一段環境回合，所以區域掃到單位的傷害也會以 `unit_damaged` 出現在預告裡。
- **視圖**：`BattleView.zones: ZoneView[]`（雙方都看得到）：名稱、施放者、錨點、對象、時機、目前格子、方向、速度、消失輪、是否有害、`next_cells`（移動型下一次環境回合後的格子）。

### 2.3 預算（`skill_budget.yaml`，初值）

點數 ＝ `effects` 的基礎點數合計 × 形狀格數 × `duration` × `zone_cell_round_permille`（120‰）×（`both` 時 `zone_both_permille` 1500‰）×（`moving` 時 `zone_moving_permille` 1500‰）＋ 表面點數 × 新覆蓋格數 × `zone_surface_permille`（300‰）。形狀倍率不另外套用（格數已算進觸發次數）。格數為純幾何（`line` size、`cone` size²、`allies_in_radius` 2r²＋2r＋1……）。

### 2.4 示範技能與 build

- **戰歌** `skill_war_hymn`（改寫，`build_support`）：原本「施放當下 2 格內友方獲得激昂 4 回合」，改為跟隨型區域：形狀 `allies_in_radius` 半徑 2，3 輪，`when: both`，友方進入或在區域內開始回合時獲得激昂 1 回合。預算 84.3%（原 86.4%）。
- **火牆** `skill_fire_wall`（新增，T2 稀有，AP 2、法力 10、冷卻 4，`build_summoner`）：形狀錐形 2（正前方 1 格 ＋ 第 2 排 3 格），移動型速度 1、2 輪、`when: both`，敵人受 1d6 火焰傷害（＋智力縮放），經過的格子留下火焰。預算 81.6%。
- 火牆一開始放在 `build_trapper`，但陷阱流因此幾乎不再放陷阱與喚起骷髏（既有的陷阱、召喚整場測試都失效），改放召喚師（主動 4 → 5 個，召喚仍正常，見 3 驗收 4）。

### 2.5 AI（`trpg.engine.ai.zone`；係數在 `ai_profiles.yaml` 的 `zone:`）

- 選位置（便宜估計）：格內對象 × 3 ＋ 移動路徑上（`duration × speed` 步內會經過）的對象 × 2；有害區域數敵人（`affects: all` 扣格內友方），有益區域數友方（含自己）；沒有對象時不納入候選。
- 收益：建立當下在區域內的對象由預覽事件計算；之後的觸發估計為「每次觸發的價值 × 格內與路徑上的對象數（路徑 × `path_permille` 500‰）× 剩餘輪數 × `likelihood_permille`（400‰）」。
- 避開：位置價值中，站在「別的陣營建立、會傷害自己」的區域格與站在有害表面一樣扣 `hazard`（最簡單近似：只看目前的格子，不看移動型下一輪的位置）。

### 2.6 紀錄、CLI、技能說明

- 紀錄：「召喚師英雄 展開持續區域「火牆」：(5, 1)、(4, 2)…（每次環境回合向東前進 1 格，第 3 輪 召喚師英雄 的回合結束時消失）」「「火牆」區域向東前進：…」「◇ 盜賊2 進入「火牆」區域（深度 1）」「◇ X 在「戰歌」區域內開始回合」「時間到了：X 的「火牆」區域消失了」。
- CLI 網格：區域涵蓋的空格標 `!`（單位、物件、陷阱、源泉優先）；圖例加「! 持續區域」；單位表下方每個區域一行（名稱、施放者、對象、錨點、消失輪、格子、本輪結束時的位置）；環境預告加「「火牆」區域將向北前進到 …」。
- `trpg skills show`：「建立持續 2 輪的區域（每次環境回合向施放方向前進 1 格）：敵人進入區域或在區域內開始回合時，1d6＋智力加成的火焰傷害；區域經過的格子留下「火焰」」。

### 2.7 網頁

- 格子：區域格畫半透明底色加細框（有害橘紅、有益黃色），移動型每格左下角畫方向箭頭（↑→↓←）。
- HUD：主角面板「持續區域：」清單，每個區域一行「火牆（A 召喚師英雄）：影響施放者的敵人，進入或回合開始時結算，每次環境回合向北前進 1 格，剩 3 輪（第 3 輪結束時消失）；本輪結束時移到 (0, 3)、(1, 3)、(0, 4)」。
- 滑過格子：環境預告側欄的滑過說明列出涵蓋這格的區域（同上一行）。
- 環境預告：`zone_moved` 的每一格標「域」，`zone_expired` 標「散」。
- 技能預覽：多一行「區域：召喚師英雄 展開持續區域「火牆」：…」（取自預覽事件）。
- 舊的錄製回應沒有 `zones` 欄位時視為沒有區域（`realResponse.test.ts` 的錄製檔未重錄）。

## 3. 驗收條件逐條（5.1）

### 驗收 1：三種錨點、`enter`／`turn_start`、移動、留下表面、到期、施放者倒下、上限

`tests/engine/test_zones.py`：

| 項目 | 測試 |
|---|---|
| 固定型建立、格內敵人立即結算、事件與深度 | `test_a_tile_zone_covers_the_skill_area_and_hits_enemies_already_inside` |
| 走進去結算一次、在區域內移動不重複、走出再走回是新的進入 | `test_walking_into_the_zone_triggers_once_and_moving_inside_does_not_retrigger` |
| `turn_start` 只在回合開始、`enter` 不在回合開始 | `test_turn_start_inside_the_zone_triggers_and_the_enter_only_zone_does_not` |
| `affects` 敵我 | `test_a_zone_does_not_affect_the_wrong_side` |
| 到期（施放者第 `duration` 輪後的回合結束） | `test_the_zone_expires_at_the_owners_turn_end_after_duration_rounds` |
| 跟隨型跟著施放者、移到隊友身上算進入 | `test_a_caster_zone_follows_the_caster_and_covers_allies_it_reaches` |
| 施放者不會進入自己的跟隨型區域 | `test_the_caster_never_enters_its_own_following_zone` |
| 施放者倒下：跟隨型消失、固定型保留到那一輪環境回合 | `test_downing_the_caster_removes_a_following_zone_but_keeps_a_tile_zone` |
| 移動型每次環境回合前進、掃到站著不動的敵人 | `test_a_moving_zone_advances_each_environment_turn_and_hits_units_it_reaches` |
| `speed 2` 一格一格走 | `test_a_moving_zone_with_speed_two_steps_cell_by_cell` |
| 撞牆的格子消失、全部消失時 `blocked` | `test_a_moving_zone_loses_cells_at_walls_and_expires_when_blocked` |
| 留下表面（建立者為施放者，只在新覆蓋的格子） | `test_a_moving_zone_leaves_its_surface_on_every_newly_covered_tile` |
| 上限 2：最舊的消失 | `test_the_zone_limit_removes_the_oldest_zone` |
| 結構錯誤（8 種）、唯一效果、欄位歸屬、示範技能 | `test_zone_structure_errors`、`test_zone_must_be_the_only_effect_and_zone_fields_belong_to_zone`、`test_the_demo_zone_skills_are_valid_and_equipped` |

### 驗收 2：環境預告顯示下一輪位置；區域進入觸發既有觸發而不重複、不觸發 `on_enter_surface`

- `test_the_telegraph_shows_where_the_zone_moves_next_and_matches_the_real_move`：預告的 `zone_moved.tiles` ＝ `next_zone_cells` ＝ 實際前進後的格子；預告的 `unit_damaged` 與實際環境回合的傷害對象一致。
- `test_the_view_lists_zones_for_both_sides`（雙方視圖都有 `next_cells`）；API：`tests/api/test_zone_api.py::test_the_fire_wall_shows_in_the_view_and_the_telegraph`（預告的 `tiles` ＝ 視圖的 `next_cells`、中文 `text`）。
- `test_zone_damage_triggers_on_damaged_once_per_entry`：敵人走過區域（進入後再走一格），`on_damaged` 被動只觸發 1 次。
- `test_entering_a_zone_is_not_entering_a_surface`：施放者帶 `on_enter_surface` 被動，敵人進入（沒有表面的）區域不觸發。
- `test_zone_triggers_respect_the_trigger_depth_limit`：`max_trigger_depth 0` 時區域不結算，發 `trigger_limit_reached`。
- CLI：`tests/narrative/test_zone_text.py::test_the_cli_marks_zones_and_forecasts_their_move`。

### 驗收 3：序列化、重播、`sim completion`、`check.py`

- 序列化：`test_zones_survive_serialization`（`state_to_json` 往返相同）；`tests/engine/test_state_clone.py` 涵蓋 `zones`。
- 重播：`tests/engine/test_zone_ai.py::test_a_zone_battle_replays_exactly`（swamp 種子 0，`build_summoner`，狀態 JSON 與事件逐字相同）；CLI：`trpg battle --map dark_forest --seed 0 --ally-build build_summoner --log-json …` → `battle replay`「重播驗證通過：55 個動作、235 個事件，最終狀態一致（dark_forest，種子 0）」；`oil_depot` 種子 2（`build_trapper,build_support`，開發中火牆仍在陷阱流時）「104 個動作、495 個事件」。
- `uv run trpg sim completion --seeds 3`：270 場，「異常合計：exception 0、max_actions 0、draw 0 —— 通過」（21.7 秒）。
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（2404 passed）、client install／typecheck／test（vitest 124）全部通過。（第一次跑時 mypy 抓到測試檔的型別問題，修正後 commit e53d263 再跑一次全過。）
- 另外跑了 `trpg sim maps --seeds 5 --ally-build build_summoner`／`build_support`（各 50 場，異常：無），並用一次性腳本統計：

| build | 有建立區域的場數 | 建立次數 | 進入結算 | 回合開始結算 | 前進 | 消失（到期／施放者離場） | 我方勝 |
|---|---|---|---|---|---|---|---|
| 召喚師（火牆） | 37 / 50 | 37 | 68 | 16 | 59 | 16／0 | 43 / 50 |
| 輔助（戰歌） | 50 / 50 | 93 | 360 | 436 | — | 51／13 | 33 / 50 |

AI 會用：`test_the_ai_casts_the_fire_wall_and_it_moves_and_burns_enemies`、`test_the_ai_casts_the_war_hymn_and_allies_walk_into_it`；估計、收益、避開：`test_the_estimate_counts_enemies_in_the_zone_and_on_its_path`、`test_the_gains_value_future_triggers_of_a_new_zone`、`test_the_ai_treats_an_enemy_harmful_zone_as_a_hazard`。

### 驗收 4：網頁（PM 用瀏覽器驗收）；vitest

- vitest：`client/src/battle/zones.test.ts`（6 個：剩餘輪數、繪製模型的格子顏色與箭頭、說明與下一輪位置、滑過格子、預覽行、預告的區域格標記）；共 124 個。
- 我用內建瀏覽器跑過一次（`trpg serve` ＋ 建置好的前端）：預覽行、HUD 清單、預告標記與滑過說明都出現；格子底色在縮小的截圖上看得到，細節請 PM 確認。
- 重現步驟：
  1. `corepack pnpm -C client build` 後 `uv run trpg serve`（或 `scripts/play.py`），開始畫面選地圖 `swamp`（沼澤）、build「召喚師」、種子 `0`，開始戰鬥。
  2. 第 1 輪輪到「召喚師英雄」（在 (0, 6)，前面的隊友與敵人已自動行動）：點技能列「火牆」，滑過主角正上方的方向格 (0, 5)：預覽有「區域：召喚師英雄 展開持續區域「火牆」：(0, 4)、(1, 4)、(0, 5)（每次環境回合向北前進 1 格，第 3 輪 召喚師英雄 的回合結束時消失）」、確定「盜賊 受到傷害／倒下」。點 (0, 5) 施放。
  3. 施放後：(0, 4)、(1, 4)、(0, 5) 三格橘紅色半透明底並有 ↑ 箭頭（也有火焰表面）；HUD「持續區域：火牆（A 召喚師英雄）…剩 3 輪（第 3 輪結束時消失）；本輪結束時移到 (0, 3)、(1, 3)、(0, 4)」；環境預告列出「「火牆」區域將向北前進到 (0, 3)、(1, 3)、(0, 4)」，這三格標「域」；滑過 (0, 4) 時側欄最上方顯示區域說明。
  4. 結束回合，等環境回合播完：區域底色移到 (0, 3)、(1, 3)、(0, 4)；紀錄有「「火牆」區域向北前進：…」。第 3 輪主角回合結束時區域消失。
  5. 跟隨型：同一頁面改選 build「輔助」（任一地圖、任一種子），主角回合點「戰歌」→ 按「施放」：主角 2 格內黃色底；移動主角時黃色底跟著移動，走到隊友身邊時紀錄出現「◇ 隊友 進入「戰歌」區域」與「獲得狀態「激昂」」。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/engine/test_state_clone.py` | `BattleState` 新欄位 `zones` 是串列（複製時另建），加進「另外複製的欄位」清單 |
| `tests/content/test_skill_rules_content.py` | `control`、`aura` 骨架的核心原語多了 `zone` |
| `tests/cli/test_budget_cli.py` | 技能總數 107 → 108（新增火牆） |
| `tests/cli/test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/24` → `/25` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 重錄（多火牆、戰歌改寫）；戰鬥類快照沒有變 |
| `client/src/battle/testFixtures.ts` | `BattleView` 多 `zones` |

## 5. 新增的複雜度 noqa

沒有 C901、PLR0911、PLR0912、PLR0915。開發中三處超標都以拆函式解決：`skill_estimate` 的陷阱／召喚／區域估計抽成 `_placement_estimate`；`render_telegraph` 的區域預告改為過濾後另外附加；AI 的狀態價值抽成 `_status_value`。`create_zone` 有 `# noqa: PLR0917`（位置參數 6 個，不是複雜度類）；`zones.py` 的延後匯入 `PLC0415` 同陷阱模組（效果佇列匯入本模組）。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/25`**（本段只升一次）：新原語 `zone`（`EffectSpec` 新欄位 `anchor`／`when`／`speed`／`effects`）、核心規則 `zone_limit_per_owner`、預算規則 `zone_*`、戰鬥狀態 `zones`／`next_zone_id`、四個新事件，戰歌改寫；`/24` 的規則包沒有這些欄位，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **欄位名 `when` 而不是規格的 `on`**：PyYAML（YAML 1.1）會把鍵 `on` 讀成布林值 `True`，資料檔寫 `on:` 會壞掉，所以用 `when: enter | turn_start | both`。
2. **「進入」的定義**：位置從區域外變成區域內才算，包含區域建立在單位身上、移動型掃到、跟隨型移到單位身上，也包含傳送、交換、推擊進去（陷阱是傳送不算）；在區域內移動不重複結算，但走出再走回是新的進入（沒有「每輪每單位一次」的限制）。若要限制來回進出刷傷害，可再加次數上限。
3. **區域效果沿用施放者在建立時的屬性快照與技能的縮放屬性**：火牆每次 1d6＋智力加成（實戰約 11–13 點），預算只算骰子平均（與其他法術一致）。跟隨型也用快照，不會隨施放者之後的增益變化。
4. **`affects: all` 不影響施放者自己**（沿用被動與陷阱「自動命中但不打自己」的規則）；火牆留下的火焰表面則照常燒到任何人（實戰中隊友會走進火焰而燃燒；AI 對火焰表面本來就有 `hazard` 扣分）。
5. **持續時間與召喚物同一規則**：施放者第 `duration` 次回合結束時消失（施放當回合不算），施放者不在場時改在那一輪的環境回合消失；移動型因此前進 `duration` 次。
6. **區域必須是技能唯一的效果**；`moving` 只能用 `line`／`cone`（沿施放方向前進，火牆用錐形 2 做出「前排 3 格」的牆），`caster` 只能用 `self`／`ring`／`allies_in_radius`。沒有新增「垂直於施放方向的直線牆」形狀。
7. **示範技能的位置**：火牆放 `build_summoner`（主動 5/6），不是陷阱流（放陷阱流時 AI 幾乎不再放陷阱與召喚，既有測試失效）；戰歌原本的「施放當下 4 回合激昂」改成跟隨型區域（3 輪、每次 1 回合），AI 使用次數很高（每場約 1.8 次）。3C-6 整理 build 時請一併看。
8. **預算與 AI 係數都是初值**：`zone_cell_round_permille 120`、`both 1500`、`moving 1500`、`surface 300`；AI `likelihood_permille 400`、`path_permille 500`；沒有模擬調整。召喚師 50 場勝 43、輔助 50 場勝 33（未要求，只是統計）。
9. **AI 避開區域只看目前的格子**，不看移動型下一輪會到的位置；也不會為了把敵人推進區域而特別加分（推擊的評分只看有害表面）。
10. **跟隨型區域隨施放者移動時不發事件**（格子由施放者位置決定，視圖每次更新）；CLI 與網頁都以目前視圖顯示，紀錄裡只看得到「進入」與「回合開始」的結算行。

## 8. 代表性輸出

`uv run trpg battle --map dark_forest --seed 0 --ally-build build_summoner`（連續一段，輸出第 55–101 行）：召喚師英雄向東升起火牆，當場燒到盜賊3；環境回合火牆向東前進一格，掃到原本在前方的盜賊弓手（倒下）與盜賊2。

```
— 召喚師英雄 的回合（AP 3，移動 5，法力 40/40）
  召喚師英雄 從 (0, 3) 移動到 (3, 2)（消耗 4 移動）
  召喚師英雄 施放「火牆」（AP 2，法力 10，冷卻 4 回合）→ 影響 4 格
    召喚師英雄 展開持續區域「火牆」：(5, 1)、(4, 2)、(5, 2)、(5, 3)（每次環境回合向東前進 1 格，第 3 輪 召喚師英雄 的回合結束時消失）
  (5, 1) 出現了火焰
  (4, 2) 出現了火焰
  (5, 2) 出現了火焰
  (5, 3) 出現了火焰
  草叢 (5, 1) 著火了（1 次環境回合後燒毀）
  草叢 (4, 2) 著火了（1 次環境回合後燒毀）
  盜賊3 獲得狀態「燃燒」（2 回合）
  ◇ 盜賊3 進入「火牆」區域（深度 1）
    盜賊3 受到 13 點火焰傷害［骰 5］，HP 30 → 17
  召喚師英雄 施放「寒鎖」（AP 1，法力 5，冷卻 2 回合）→ 影響 1 格
  召喚師英雄 以「寒鎖」攻擊 盜賊1：d20=16 修正 -1 熟練 +2 = 17（目標 11）→ 命中
    盜賊1 受到 9 點冰霜傷害［骰 1］，HP 30 → 21
  召喚師英雄 對 盜賊1 施加「定身」（智力 16 vs 力量 12）：d20=2 修正 +2 熟練 +2 = 6（目標 11）→ 被抵抗
  盜賊1 抵抗了「定身」
  召喚師英雄 結束回合
— 盜賊2 的回合（AP 3，移動 5）
  盜賊2 從 (8, 5) 移動到 (6, 3)（消耗 4 移動）
  盜賊2 獲得狀態「防禦」
  盜賊2 結束回合，保留 1 AP
— 標準隊友（戰士） 的回合（AP 3，移動 5）
  標準隊友（戰士） 從 (1, 4) 移動到 (4, 2)（消耗 5 移動）
  標準隊友（戰士） 獲得狀態「燃燒」（2 回合）
  標準隊友（戰士） 獲得狀態「防禦」
  標準隊友（戰士） 結束回合，保留 1 AP
～ 環境回合 ～
  ＊ 草叢 (5, 1) 燒毀！
  ＊ 草叢 (4, 2) 燒毀！
  (6, 2) 出現了火焰
  倒木 (6, 2) 著火了（1 次環境回合後燒毀）
  (4, 3) 出現了火焰
  倒木 (4, 3) 著火了（1 次環境回合後燒毀）
  (6, 3) 出現了火焰
  草叢 (6, 3) 著火了（1 次環境回合後燒毀）
  盜賊2 獲得狀態「燃燒」（2 回合）
  「火牆」區域向東前進：(6, 1)、(5, 2)、(6, 2)、(6, 3)
  (6, 1) 出現了火焰
  盜賊弓手 獲得狀態「燃燒」（2 回合）
  ◇ 盜賊弓手 進入「火牆」區域（深度 1）
    盜賊弓手 受到 12 點火焰傷害［骰 2］（元素修正 ×1.25），HP 2 → 0
  ＊ 盜賊弓手 倒下了！
  ◇ 盜賊2 進入「火牆」區域（深度 1）
    盜賊2 受到 11 點火焰傷害［骰 3］，HP 30 → 19
```

下一輪開始時的單位表與預告（同一場第 122–123 行）：

```
  ! 區域「火牆」（召喚師英雄，影響敵方，每次環境回合向東前進 1 格，第 3 輪 召喚師英雄 的回合結束時消失）：(6, 1)、(5, 2)、(6, 2)、(6, 3)；本輪結束時向東移到 (7, 1)、(6, 2)、(7, 3)
  環境預告：…；「火牆」區域將向東前進到 (7, 1)、(6, 2)、(7, 3)；…
```
