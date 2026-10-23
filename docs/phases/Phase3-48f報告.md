# Phase 3-48f 報告：符文讀取提示、示範技能、套用玩家語氣說明

規格：`docs/phases/Phase3計畫.md` 第 56 節（含 3a），加上玩法 PM 對 3-48d 的兩項追加。

## 1. 工坊提示（第 1 點）

- `trpg.skillgen.options._rune_hint`：草稿有刻印、又有給友方的增益（`affects` 為友方／全體的護盾、治療、給 AP、免死、淨化，或有益狀態），而且沒有任何讀取符文的條件（技能條件或任一效果條件是 `on_own_rune`、或有 `detonate_runes`）時，效果步驟的備註顯示規格文字（`RUNE_HINT_ZH`）。
- 測試：`tests/skillgen/test_workshop_rune_hint_48f.py`（有提示／沒有友方增益不提示／有讀取者或技能條件不提示）。

## 2. 示範技能（第 2 點）

- **進攻向：`skill_rune_snare`（符紋絆腳）**，被動、epic、`on_hit`（target other）、條件 `on_own_rune`、效果緩速 4 輪（對敵人）。用現有機制組成（同 `skill_tide_snare` 的做法）。預算 3.60／4.52 ＝ **79.6%**（持續 2 輪只有 39.8%、3 輪 59.7%，所以取 4 輪）。
  - 行為測試 `tests/engine/test_rune_snare_48f.py`：敵人站在自己符文上被命中 → 緩速；沒符文、站在別人符文上、符文在別格 → 不觸發；卡片文字有條件與緩速；驗證器通過、預算在 70～100%。
- **守護符陣（被動，回合開始時 2 格內站在你符文上的友方獲得護盾）：現有觸發與條件組不出來，沒有實作，等 PM 決定。** 缺的是：
  1. 被動技能的觸發 `trigger.target` 只有 `self`／`other`；`target: self` 時驗證器（`passive.affects`）規定所有效果的 `affects` 只能是 `self`。
  2. `on_turn_start` 沒有「另一方」（`has_other: false`），所以不能用 `target: other`。
  3. 被動沒有「以持有者為中心的範圍＋對友方結算」的機制（被動的 `shape` 只能是 `self`）。
  - 可行的替代方案（請 PM／玩法 PM 選）：(a) 做成主動技能：`allies_in_radius`（半徑 2）＋護盾，效果加條件 `on_own_rune`（現有機制即可組出，但不是被動）；(b) 擴充被動：允許 `on_turn_start` 的被動帶範圍形狀並對友方結算（需要新增觸發／驗證器規則，屬於新原語層級，我沒有做）。

## 3. 玩家語氣說明（第 3a 點）

- 新資料檔 `content/workshop_text.yaml`（149 筆；`id`、`source`＝程式裡的原文、`player`＝玩家語氣、選填 `scope`）；schema `WorkshopTextTable`（`trpg.content.workshop`），載入進 `ContentLibrary.workshop_text`（不屬於規則包）。程式不讀共用資料夾。
- `option_player._player_text`：先依原文（與欄位範圍）查表，有就顯示玩家語氣、原文放 `dev_description_zh`（`?dev=1` 顯示原文）；沒有對到的維持 3-48c 的程式化處理。同一段原文要用不同說法的只有「層數 ID（stacks.yaml）」（累積／消耗），用 `scope`（`add_stack.stack`、`consume_stack.stack`）區分。
- 測試 `tests/skillgen/test_workshop_text_48f.py`：149 筆、現在程式會產生的每一段開發者語氣原文都有改寫、每筆改寫都用得到、玩家模式顯示改寫且 dev 保留原文、scope 查表、衝突檢查。
- 預算公式不在說明裡：預算面板（`budget` 回傳的 `coefficient_label`、`allowance_parts`、`condition_multiplier`）本來就顯示，維持原樣。
- `test_player_text.py` 的英文掃描加了一個例外：`tide_pierce`（見下表第 8 項）。

### 句子與實際規則對不上的地方（交玩法 PM，沒有改句子或規則）

| # | 說明（id） | 問題 |
|---|---|---|
| 1 | 原語.cheat_death、原語.dispel | 玩家語氣寫「免死」，但狀態的中文名是「不死」（`statuses.yaml` undying、原文也是不死）。介面其他地方會顯示「不死」。 |
| 2 | 原語.cleanse | 寫「移除所有負面狀態」；原文與引擎是移除所有「非有益」狀態，中性狀態（隱蔽、不死、靈魂連結、姿態）也算。請確認是否要連中性一起移除，或改句子。 |
| 3 | 原語.intercept | 寫「替身」；原語的中文名是「替隊友擋攻擊」。「靈魂連結」那條也用「替身」比較。 |
| 4 | 原語.gamble | 「反噬……不能是暈眩、跳過回合或持續傷害」，規則是「不能是硬控、跳過回合或持續傷害」，硬控比暈眩寬（含定身、倒地等）。「可以設定成功時傷害加倍」：倍率可自訂（×0.1～×10），不只加倍。 |
| 5 | 原語.damage.on_kill | 寫「……治療、護盾或狀態」，沒說明狀態必須是有益的；本段新增驗證器限制（見第 4 節），句子建議補上。 |
| 6 | 原語.summon.trait | 「（堅韌、迅捷、銳利）」是寫死的名稱，核心規則的小特性清單改了就對不上。 |
| 7 | 原語.inscribe | 「最多 5」是寫死的（原文是「上限 5」），與 `core.yaml` 的刻印持續上限同步，之後調整要一起改。 |
| 8 | 工坊.variants.variants.id | 句子保留英文範例 `tide_pierce`，與玩家模式不顯示英文代號的規則（3-48）有出入；欄位本身確實要輸入英文代號，所以我在英文掃描測試放行這一個詞。 |
| 9 | 「給予行動點」（原語名） | 玩家可見名稱仍是「行動點」，與其他處的「AP」不一致（本段只統一了「返還行動點」→「返還 AP」）。 |

## 4. 3-48d 追加（玩法 PM 的回覆）

1. `option_nested._SPECIAL` 賭注專用效果：
   - 傷害倍率：說明「這一次施放的所有傷害乘上倍率（×2＝加倍）。」欄位名「倍率」；
   - 反噬自傷：說明「你自己也受到這一次造成傷害的一部分（不會致命，HP 至少留 1）。」欄位名「反噬比例（%）」；
   - 內部仍存千分比。`FieldSpec` 新欄位 `display`（`multiplier`／`percent`），前端 `FieldEditor` 的數字欄位依此換算顯示與輸入（×1.5、25%，範圍提示同），已重產 OpenAPI 與 `schema.d.ts`。
   - 「返還行動點」→「返還 AP」：`option_nested`、`player_text`（`plainify` 對照表）；其他玩家可見處（`api/player_text.py`、引擎說明）本來就是「返還 AP」。
2. 擊殺時效果（`on_kill`）施加的狀態必須有益：驗證器新規則 `on_kill.beneficial`（`validate._on_kill_status_violations`，附中文原因「擊殺時效果會作用在你自己身上，只能施加有益的狀態；『某狀態』是負面狀態」）。工坊檢查、LLM 提議、YAML 匯入都走 `validate_skill`，一起擋下。**內建技能沒有違反的。**
3. 測試：`tests/skillgen/test_workshop_48f.py`（單位與文字、ap 名稱、負面狀態被擋且有原因、有益不擋、驗證器規則、內建無違反）；vitest `client/src/workshop/display48f.test.ts`。

## 5. 其他

- 新技能的連帶更新：`client/src/render/fixtures/skill_icons.json` 已重產；CLI 快照以 `UPDATE_CLI_SNAPSHOTS=1` 重跑（見驗收）；關鍵字池由驗證器／推導表自動歸池（技能帶 `on_own_rune` 條件 → 利用「符文」關鍵字）。
- 順手修：`client/src/workshop/nested48d.test.ts` 的 FieldSpec 夾具補 `plain_value: false`（協調者提醒；main 已修，合併時可能衝突，取任一邊即可）。

## 驗收

見交付訊息中的結果清單（pytest content／skillgen／engine／narrative／api、`-m "slow or not slow" tests/cli`、vitest、build、ruff、format、mypy）。
