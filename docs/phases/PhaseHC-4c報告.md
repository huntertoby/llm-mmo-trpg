# Phase HC-4c 報告：AI 與環境的預設值搬進 content

依據：`docs/phases/PhaseHC-4c計畫.md`；HC-4b3 報告最後的開發 PM 裁定 3～5；做法照 HC-4a、HC-4b、HC-4b2、HC-4b3。
基準：main `2415203c9`（worktree 開工時在 `9ae77fc67`，先 fast-forward）。分支 `worktree-agent-aa9c54be9c8a7a0dc`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`。前端沒改。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 HC-4b3 收尾 | `0ee4280b9` | 閃現表剩下的幾格改必填；刪 `scale_permille`；刪 11 條 0 筆的 done 規則 |
| 2 AI 與環境搬家 | `f6bd6cffa` | `environment.py` 的 AI 規則預設值改必填；`engine/ai/*` 的模組常數搬到 `ai_profiles.yaml` 的 `heuristics:`，經 `Ruleset.ai` 帶進引擎；剩下的結構常數改判 const／guard；開 35 格進工坊 |
| 修正 | `18bedd058` | `scripts/x10/fields.yaml` 列入新的 AI 欄位（量類換算清單，`test_x10_fields`） |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試；第 1 項另跑逐招預算與閃現出題比對，第 2 項另跑 78 場戰鬥比對與 AI 表的 `model_dump` 比對。

## 2. 第 1 項：HC-4b3 收尾（裁定 3～5）

### 2.1 改成必填（值以內容檔為準）
| 欄位 | 程式原本的預設 | 內容檔 | 處理 |
|---|---|---|---|
| `FlashRules.tighten_permille` | 100 | 100 | 必填（原本被 `py-percent-conversion` 當 const；拿掉預設後這筆數字消失，不用再改歸類） |
| `FlashRules.form_magnitudes` | `range(1000, 2001, 50)` | 21 格，同值 | 必填 |
| `FlashRules.insight_per_win` | 1 | 2 | 必填；一直生效的是內容檔的 2，照 2 |
| `CompleteSkillRules.cost_cuts` | 五項、步距都是 1 | 五項，法力、耐力步距 10 | 必填；`CostCut.step` 也必填 |
| `PriceRule.min_categories` | 1 | `open` 2；`focused` 沒寫 | 必填；`focused` 先寫進 `min_categories: 1`（原本靠預設） |

### 2.2 刪掉 `TransformTemplate.scale_permille`
- 刪前 grep：`client/`、`content/`、`tests/`、`src/`、`docs/design/`。
  - 前端只有工坊技能批次改的 `op.kind: "scale_permille"`（`api/tuning/schemas.py` 的另一個欄位），和這個欄位無關。
  - `content/` 只有 `flash_templates.yaml` 的 `to_passive_on_hit`（500）、`to_reaction_melee`（600）兩行宣告，沒有程式讀。
  - `affixes.yaml`、`equipment.py`、`gear_checks.py`、`engine/gear/enhance.py` 的 `scale_permille` 是詞條的另一個欄位。
  - `docs/design/` 沒有提到。
- 所以刪掉欄位、驗證、內容檔的兩行；`ContentModel` 不收多餘欄位，寫了就驗證失敗（新測試）。
- `TransformTemplate` 的 docstring 一併改寫；`test_rule_defaults_hc4b3.py` 拿掉這格的兩個案例。

### 2.3 刪掉 11 條 0 筆的 done 規則
`ts-flash-fallback`、`ts-slot-limits`、`ts-source-max`、`ts-attr-base`、`ts-start-keywords`、`ts-affix-duplicate`、`ts-walk-max`、`ts-tuning-server-limits`（HC-3），`py-scale-one-defaults-content`、`py-scale-one-defaults-misc`（HC-2），`py-content-rule-bounds-boss-parts`（HC-4a）。
- 刪完 `classify.py --check` 0、沒歸類 0、各類筆數不變。
- HC-2 那兩條上面的專查說明（為什麼量類的「預設 1」要另外查）留著當紀錄，加一行註明規則已刪。
- 0 筆的 todo 規則照裁定不動（`py-scale-names` 等 3 條 scale、`py-content-loader-config-number` 等 8 條）。

## 3. 第 2 項：AI 與環境搬家（config todo 145 筆 → 0）

### 3.1 `content/environment.py`（90 筆）
- **改必填**（`ai_profiles.yaml` 的表格層級都有寫、值相同）：
  - `TrapAiRules`、`GambleAiRules`、`SelfCostAiRules`、`StanceAiRules`、`FormAiRules`、`SummonAiRules`、`ZoneAiRules`、`RuneAiRules`、`TerrainAiRules`、`OrderBonuses`、`RunAiRules`、`BasicActionAiRules`：全部數字欄位（含 0、1000 這類掃描器不列的預設，內容檔也都有寫）。`SummonAiRules.auto_focus_boss` 也改必填。
  - `AiProfileTable`：`move_candidates`、`trap_likelihood_permille`，以及 13 張子表本身。`AiProfile` 的 `trap_likelihood_permille` 與 13 張子表也必填（由表格層級填入，跟原本一樣）。
  - `AiWeights.hold_radius`（`objective_ai` 有寫）。
- **沒寫的先寫進 content，再改必填**：
  - `skill_candidates: 3`（表格層級）。
  - `rewrite:` 的 `delayed_heal_points` 5、`priority_kill_points` 10、`interrupt_points` 12、`formation_break_points` 10、`ward_kill_points` 12、`share_discount_permille` 500。
  - `AiWeights` 的 `charge_per_enemy` 3、`shadowstep` 3、`shadowstep_behind` 2：寫進表格層級的 `skill_ai`（原本就是「填入每個行為模式、模式自己列出的優先」）。`assassin` 自己寫的 6、3 照舊優先。
- **程式和內容檔不同的幾格**：`move_candidates`（程式 8、內容 6）、`basic.aim_hit_permille`（500、700）、`summon.infuse_threat_damage`（4、2）。一直生效的是內容檔，照內容檔，結果不變。
- `AiWeights` 其他預設 0 的權重（「未列出的權重為 0」）和 `PartAiRules` 的 0 不在 config 清單，沒動。

### 3.2 `engine/ai/*`（55 筆）
**新開的內容區塊**：`ai_profiles.yaml` 的 `heuristics:`，schema 是 `environment.py` 的 `AiHeuristics`，分三組：
- `race`：種族技的使用條件；
- `estimate`：便宜估計，決定誰值得跑完整預覽；
- `scoring`：不分行為模式的共用評分數值。

另外在既有的 `rewrite:` 加一格 `redirect_min_hp_permille`。

**怎麼帶進引擎**：
- `Ruleset` 加必填欄位 `ai: AiHeuristics`，載入時從 `ai_profiles.heuristics` 帶入，`load.py` 一行。
- 引擎的函式都拿得到 `state`，改讀 `state.ruleset.ai.<組>.<欄>`。引擎沒有讀檔，也沒有新的匯入方向（lint-imports 14 kept）。
- 規則包多了 `ai`，所以 `ruleset_hash` 會變（計畫說是預期的）。
- 沒有新開檔：AI 數值本來就都在 `ai_profiles.yaml`，工坊的「AI 估值表」也是這個檔。
- 沒放進 `core.yaml`：放那裡會拆成兩個檔，工坊要另外放到「核心戰鬥規則」表。

| 原本 | 搬到 | 值 |
|---|---|---|
| `race.py` `_MIN_AP_AFTER`、`_RESTORE_MIN_DEFICIT`、`_MIN_CLUSTER`、`_LEAP_RISE_POINTS` | `heuristics.race.min_ap_after`、`restore_min_deficit`、`min_cluster`、`leap_rise_points` | 2、6、2、10 |
| `race.py` `_near_score(7)`、`(3)`、`(2)` | `race.conceal_near`、`immovable_near`、`surface_near` | 7、3、2 |
| `race.py` 震退 `+2`、`+3` | `race.push_enemy_points`、`push_deadly_points` | 2、3 |
| `race.py` 拋錨 `hp * 2 <= max_hp`、`+2` | `race.pull_low_hp_permille`、`pull_low_hp_points` | 500、2 |
| `race.py` 過充 `current * 2 <= maximum` | `race.restore_low_permille` | 500 |
| `race.py` 應變 `move_points + 2` | 讀種族技效果 `bonus_move` 的 `amount`（見待決 2） | 內容寫 2 |
| `skill_estimate.py` 敵 `+3`、支援友 `+2`、其他友 `−3` | `estimate.enemy_points`、`support_points`、`ally_penalty` | 3、2、3 |
| `skill_estimate.py` 陷阱 `× 4`、場地 `2` | `estimate.trap_enemy_points`、`field_cover_points` | 4、2 |
| `composite.py` `3 * enemies - 3 * allies` | `estimate.composite_enemy_points`、`composite_ally_penalty` | 3、3 |
| `zone.py` `3 * inside + 2 * along` | `estimate.zone_inside_points`、`zone_path_points` | 3、2 |
| `scene_objects.py` `_ENEMY_VALUE`、`_FRIEND_PENALTY` | `estimate.scene_enemy_points`、`scene_friend_penalty` | 3、3 |
| `terrain.py` `_ENEMY_VALUE`、`_ALLY_VALUE`、`_PIT_VALUE` | `estimate.terrain_lower_points`、`terrain_raise_points`、`terrain_pit_points` | 3、2、2 |
| `displace.py` `_DEADLY_HARM`、`_SURFACE_HARM`、`_TRAP_HARM` | `estimate.displace_deadly_points`、`displace_surface_points`、`displace_trap_points` | 10、4、3 |
| `summon.py` `_ESTIMATE_BASE`、獻祭 `3 *`、`2 *` | `estimate.summon_base_points`、`sacrifice_enemy_points`、`sacrifice_ally_points` | 20、3、2 |
| `rune.py` `_CELL_SCORES = {0: 3, 1: 2, 2: 1}` | `estimate.rune_cell_points: [3, 2, 1]`（索引＝距離） | 同 |
| `moves.py` `_OBJECT_NEAR_ENEMY` | `estimate.object_near_enemy` | 2 |
| `charge.py` `_DEFAULT_BUFF_VALUE`、`zone.py`、`gains.py` 的 `.get(…, 3)` | `scoring.unlisted_status_value`（三處同一個意思，見待決 3） | 3 |
| `gains.py` `_POSSIBLE_KILL_DIVISOR`、`priority.py` `_POSSIBLE_DIVISOR` | `scoring.possible_kill_divisor`（原本兩個常數、docstring 寫「同」） | 4 |
| `gains.py` `_DEFEND_RADIUS`（`scoring.py` 也匯入） | `scoring.defend_radius` | 6 |
| `objective.py` `_THREAT_RADIUS` | `scoring.hold_threat_radius` | 6 |
| `gains.py` `_SURFACE_HARM` | `scoring.surface_friend_harm` | 8 |
| `position.py` `_KEEP_DISTANCE`、`_FORMATION_STEP` | `scoring.keep_distance_radius`、`formation_step` | 2、100 |
| `displace.py` `_LOW_HP_PERMILLE`、`_EXPOSURE_RADIUS` | `scoring.hurt_hp_permille`、`exposure_radius` | 400、2 |
| `scoring.py` 靈魂連結 `actor.hp * 2 >= actor.max_hp` | `rewrite.redirect_min_hp_permille` | 500 |

- 「一半」的判斷 `x * 2 <= y` 改成 `x * 1000 <= y * 500‰`，整數上等價。
- 沒有 `state` 的小函式加了參數：`is_hurt(state, unit)`、`scene_objects._value(state, …)`、`rune._cell_score(state, …)`、`position._keep_radius(state, unit)`。
- `race.py` 的計分函式改成執行時從 `state.ruleset.ai.race` 讀，`_near_score` 改收一個「從規則取格數」的函式。

**純結構常數與護欄**（照分類規則改判，寫了理由，沒有硬搬）：

| 位置 | 數字 | 判斷 | 理由 |
|---|---|---|---|
| `orders.py` `HoldPosition.radius` 的 `le=3` | 3 | guard | 守位指令的格式上限；召喚物的 `follow_radius`、`guard_radius` 用同一個指令，schema 也是 `le=3`，三處一致 |
| `rune.py` `rune_gains` 的距離鍵 `{0, 1, 2}` 與 `99` | 2、99 | const | 鍵是「腳下／相鄰／近」的結構（比例本來就在 `rune:`）；99 是「沒有敵人」的哨兵值 |
| `summon.py` 圖騰 `min(rounds, 99)` | 99 | const | 輪數的上限護欄（剩餘輪數由到期輪算出，不會到 99） |
| `scoring.py` `len(chances) < 2` | 2 | const | 多目標加分的定義：至少打到 2 名敵人才算多目標 |

這四條規則改成 const／guard 的 done，note 寫上理由。其餘 13 條 engine/ai 規則和 `py-content-environment-config-number` 搬完都是 0 筆，照 HC-4b 裁定 1 刪掉（計畫寫「status 改成 done」；照前例不留 0 筆的 done，見待決 4）。

### 3.3 開進工坊（AI 估值表，35 格，分 8 組）
工坊已有 `ai` 表（`ai_profiles.yaml`），新欄位都放進去，每格有 `group_zh`。以前的 13 格沒有分組，照舊。表單頂端的提示加一行說明這段新開的分組。

| 分組 | 欄位 | 名稱 | 建議範圍 |
|---|---|---|---|
| 改寫與源力 | `rewrite.ap_points` | 給 AP 的價值 | 0～12 |
| 改寫與源力 | `rewrite.ally_ap_permille` | 給隊友 AP 的比例（‰） | 0～1000 |
| 改寫與源力 | `rewrite.source_points` | 源力的機會成本 | 0～10 |
| 改寫與源力 | `rewrite.undying_points` | 免死的價值 | 0～80 |
| 改寫與源力 | `rewrite.revive_points` | 復活的價值 | 0～60 |
| 改寫與源力 | `rewrite.priority_kill_points` | 先打補師的加分 | 0～30 |
| 改寫與源力 | `rewrite.interrupt_points` | 打斷蓄力的加分 | 0～30 |
| 召喚 | `summon.hit_permille` | 召喚物傷害的折合（‰） | 200～1000 |
| 召喚 | `summon.totem_ally_points` | 圖騰光環的價值 | 0～10 |
| 召喚 | `summon.infuse_value_permille` | 灌注的價值（‰） | 0～2000 |
| 召喚 | `summon.infuse_threat_damage` | 灌注時估的威脅 | 0～10 |
| 區域、陷阱、刻印與地形 | `trap_likelihood_permille` | 陷阱踩中機率（‰） | 200～1000 |
| 區域、陷阱、刻印與地形 | `trap.max_active` | 同時最多幾個陷阱 | 1～5 |
| 區域、陷阱、刻印與地形 | `zone.likelihood_permille` | 區域之後觸發的比例（‰） | 100～1000 |
| 區域、陷阱、刻印與地形 | `rune.inscribe_points` | 刻印的價值 | 0～12 |
| 區域、陷阱、刻印與地形 | `terrain.height_points` | 改變高度的價值 | 0～10 |
| 姿態、形態與代價 | `stance.cancel_hp_below_permille` | 取消危險姿態的 HP 門檻（‰） | 100～800 |
| 姿態、形態與代價 | `form.enter_value` | 進入形態的價值 | 0～16 |
| 姿態、形態與代價 | `self_cost.stun_hp_below_permille` | 自暈技能的 HP 門檻（‰） | 100～900 |
| 姿態、形態與代價 | `gamble.hp_floor_permille` | 賭博技能的 HP 下限（‰） | 0～600 |
| 戰術指令 | `orders.focus_permille` | 集火的收益倍率（‰） | 1000～3000 |
| 戰術指令 | `orders.hold_weight` | 守位每格的扣分 | 0～40 |
| 戰術指令 | `orders.environment_permille` | 利用環境的收益倍率（‰） | 1000～4000 |
| 跑步與基本動作 | `run.pursue_points` | 跑步追擊的分數 | 0～12 |
| 跑步與基本動作 | `run.retreat_hp_permille` | 跑步撤離的 HP 門檻（‰） | 100～700 |
| 跑步與基本動作 | `basic.guard_points` | 守護隊友的加分 | 0～10 |
| 跑步與基本動作 | `basic.swap_points` | 換位的分數 | 0～12 |
| 跑步與基本動作 | `basic.aim_hit_permille` | 瞄準的命中率門檻（‰） | 300～900 |
| 種族技 | `heuristics.race.conceal_near` | 林隱：敵人多近才用 | 2～10 |
| 種族技 | `heuristics.race.leap_rise_points` | 獸躍：每升一層的分數 | 1～20 |
| 種族技 | `heuristics.race.restore_min_deficit` | 過充：缺口多少才用 | 1～15 |
| 共用評分 | `heuristics.scoring.unlisted_status_value` | 沒列出的狀態價值 | 0～8 |
| 共用評分 | `heuristics.scoring.defend_radius` | 防禦看幾格內的敵人 | 2～10 |
| 共用評分 | `heuristics.scoring.surface_friend_harm` | 害隊友踩有害表面的扣分 | 0～16 |
| 共用評分 | `heuristics.scoring.hurt_hp_permille` | 快倒下的門檻（‰） | 200～600 |

- 每格都有中文名稱，說明都寫了調高、調低的效果；千分比寫了只能 0～1000（或至少 1000）。現值都在建議範圍內（測試檢查）。
- 表格層級的值會填入每個行為模式，行為模式自己寫的優先。所以只開沒有行為模式覆寫的格；`seer` 覆寫的 `rewrite.mana_points`、`cooldown_points` 沒開。
- **沒開的**（數量多、意思相近，只開了代表性的幾格）：
  - `rewrite` 其餘 21 格（另有 `seer` 覆寫的 2 格），`summon` 其餘 12 格（另有一個布林）；
  - `trap` 的 `near` 與形狀係數，`zone.path_permille`，`rune` 的比例與讀取分，`terrain.pit_points`，`gamble.low_hp_permille`；
  - `self_cost`、`stance`、`run`、`basic` 的其餘格，`orders.retreat_weight`、`protect_min`；
  - `heuristics.race` 其餘 9 格，`heuristics.scoring` 其餘 5 格；
  - 整組 `heuristics.estimate`（22 格，只影響候選排序、不直接決定動作，調了不容易看出效果）；
  - 搜尋寬度 `move_candidates`、`skill_candidates`（程式參數）。

### 3.4 測試
- **新增** `tests/content/test_rule_defaults_hc4c.py`：
  - 閃現表 7 格與 AI 表 28 格，少寫一格就驗證失敗；
  - 閃現與 AI 的值照內容檔；`scale_permille` 寫了就失敗；
  - `ruleset.ai` 等於 `ai_profiles.heuristics`；
  - 改規則包的 `scoring` 後，`exposure`、`is_hurt` 跟著變（引擎讀規則包，不是模組常數）。
- **新增** `tests/api/tuning/test_workshop_open_hc4c.py`：35 格的值、分組、說明與建議範圍；草稿驗證通過；超過 1000‰ 被擋。
- **改**（因為程式預設值拿掉了）：
  - `test_ai_weights.py`：改讀內容檔的 `skill_ai` 與 `brute` 的權重。
  - `test_objective_ai.py`、`test_nw3b_small.py`：`AiWeights` 補上必填的四格。
  - `test_traps.py`：`TrapAiRules` 補兩格；兩個測試改成從表格層級的 `trap` 只換要測的那一格。原本用 `{"near": 1}` 靠預設補齊。
  - `test_x10_scale.py`：`SummonAiRules` 改從內容檔複製。
  - `test_parts_pb1n.py`：AI 表的欄位清單只比沒分組的舊欄位。

## 4. 不變比對（基準 `git archive 2415203c9 src content config`）

腳本沿用 HC-4b3（scratch，沒進 repo）。改前、改後各用自己的 `src/` 與 `content/`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`，並確認載入的 `trpg` 路徑）。

| 比對 | 時機 | 結果 |
|---|---|---|
| 逐招預算 434 招（`BudgetReport` repr＋`validate_skill` 違規） | 第 1 項後、最後 | `skills=434 same=434 different=0` |
| 閃現出題（`flash_dump.py`：規則、計價、加成、退回、406 招完整技能、174 組出題 1322 筆） | 第 1 項後、最後 | 全部 `different=0` |
| 78 場戰鬥（`--log-json` 去掉 `ruleset_hash` 與內嵌規則包，加上文字輸出；含 AI 的每個動作） | 第 2 項、最後 | `battles=78 events=26446 different=0` |
| AI 表 `AiProfileTable.model_dump`（基準 vs 新） | 第 2 項 | 見 4.1 |

### 4.1 預測會變的地方（逐鍵核對）
- **規則包**：78 場的內嵌規則包只多了 `ruleset.ai`，三組 43 格，值同上表，沒有其他差異，所以 `ruleset_hash` 會變。
- **AI 表 `model_dump`**：17 處不同，都是新增。
  - `heuristics` 整組；
  - 表格層級與 12 個行為模式的 `rewrite.redirect_min_hp_permille: 500`；
  - `skill_ai` 多了 `charge_per_enemy`、`shadowstep`、`shadowstep_behind`。
  - 12 個行為模式的 `weights` 全部相同，沒有其他差異。
- **閃現表 `model_dump`**：10 個轉型模板少了 `scale_permille` 這個鍵（2 個原本 500、600，8 個 `None`），沒有其他差異。這份 dump 不進雜湊、存檔或 API。
- parity 夾具、CLI 快照：沒有重產，slow 測試照原樣通過（第 5 節）。
- OpenAPI：重產後 `client/openapi.json` 沒有差異（規則包不在 API 裡；工坊的提示文字不在 schema 裡）。

## 5. 檢查（最後一個程式 commit `f6bd6cffa`；之後的 `18bedd058` 只改 `scripts/x10/fields.yaml`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1768 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 逐招預算比對 434 招 | different=0 |
| 閃現出題比對 | different=0 |
| 78 場戰鬥比對 | different=0 |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979 passed） |
| 前端 tsc／vitest／build | 沒跑（前端沒改） |

分目錄（`run_pytest.py -q tests/<目錄> -n 8`，一次一組，`llm` 與 `skillgen` 不同時跑）：

| 目錄 | 結束碼 | 結果 |
|---|---|---|
| api | 0 | 1390 passed、1 skipped |
| bot | 0 | 67 |
| cli | 0 | 148 |
| content | 0 | 3277 |
| engine | 0 | 5120（開發中一輪 2 failed：`test_traps.py` 兩個測試靠 `TrapAiRules` 預設值補齊部分欄位，改成從表格層級只換一格後通過） |
| infra | 0 | 9 |
| llm | 0 | 495 |
| narrative | 0 | 479 |
| roguelite | 0 | 279 |
| server | 0 | 77 |
| shared | 0 | 76 |
| sim | 0 | 180 |
| skillgen | 0 | 4637 passed、7 skipped |
| world | 0 | 1328 |
| 頂層 `tests/test_*.py` | 1 → 0 | 第一輪 2 failed：`test_x10_fields`、`test_x10_rescale` 要求 `scripts/x10/fields.yaml` 列出新欄位（`heuristics.*`、`skill_candidates`、`skill_ai` 三格）。補上（`18bedd058`）後重跑 257 passed |

- 看門狗沒有回報 worker 掛掉或卡住（log 沒有 `node down`、沒有 `stuck.txt`）；保留的留證資料夾是有失敗的那兩輪自動留下的。

## 6. config todo 與歸類（`classify.py --stats`）

| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `2415203c9` | 699 | 38 | 8887 | 194 | 397 |
| 後端 交件 | **554** | 38 | 8893 | 194 | 398 |
| 前端（沒改） | 26 | 0 | 5440 | 98 | 0 |

- **config 少 145**：`environment.py` 90、`engine/ai/*` 55，兩區都是 0。
  - 141 筆搬進 content；
  - 4 筆改判，進 const 3、guard 1（3.2 的表）。
- **const 多 6**：改判 3 筆；新 docstring、提示文字裡的數字、引用約 +4；拿掉的 `tighten_permille` 100 −1。
- 0 筆而刪掉的規則：
  - 第 1 項的 11 條；
  - 第 2 項的 `py-content-environment-config-number` 和 13 條 `py-engine-ai-*-config-number`。
- 清單的 HC-4 c 項在 `classes.yaml` 的 `plan` 裡還是原文（只是建議分段），沒改。`寫死數值-清單.md` 用 `--md` 重產。

## 7. 待 PM 決定（都照最保守的做了）

1. **AI 數值的放法**：新開 `ai_profiles.yaml` 的 `heuristics:`，經 `Ruleset.ai` 帶進引擎，沒放 `core.yaml`。
   - 理由：AI 數值和工坊的 AI 估值表都在這個檔。
   - `Ruleset.ai` 是必填欄位。舊的戰鬥存檔或紀錄如果嵌著舊規則包（沒有 `ai`），讀回時會驗證失敗。
   - 和 HC-4b2 在 `core` 加 `modifier_bounds` 是同一種影響。測試夾具沒有嵌規則包，不受影響。
2. **應變的「多走 2 格」改讀種族技效果的 `amount`**，沒有另開一格。
   - 那個 2 就是 `races.yaml` 應變 `bonus_move` 的 `amount: 2`。另開一格就會有兩個地方要一起改，所以照 HC-4b3 `_MAX_FORM_MAGNITUDE` 的做法讀原資料。
   - 現有內容結果不變。自訂種族的 `amount` 不是 2 時，AI 會照實際值判斷，這是行為上的修正。
3. **合併成一格的常數**：
   - 「沒列出的狀態價值 3」原本有三處：充能的增益、區域的增益、淨化的減益，合成 `scoring.unlisted_status_value`；
   - 「只是可能的擊倒 ÷4」原本有兩個常數，合成 `scoring.possible_kill_divisor`。
   - 要分開調的話，拆成兩、三格就好。
4. **搬完的規則刪掉，沒改成 done**：計畫寫「改完的那一區 status 改成 done」。但搬完都是 0 筆，照 HC-4b 裁定 1 與 HC-4b2、HC-4b3 的前例，不留 0 筆的 done。剩下的 4 條改判 const／guard 的 done。
5. **四個改判的結構常數**（3.2 的表）：
   - 守位半徑 `le=3` 判 guard；
   - 刻印距離鍵與 99、圖騰的 `min(rounds, 99)`、多目標「至少 2 名」判 const。
   - 要改成 config 的話告訴我。
6. **`AiProfile` 的 13 張子表改必填**：原本的預設值會用 `TrapAiRules()` 這類全預設的子表。子表欄位改必填後，這個預設建不出來，所以一併改必填（照舊由表格層級填入）。單獨驗證一個行為模式時要帶齊子表。
7. **工坊只開了 35 格**（3.3 列了沒開的）。整組便宜估計沒開，因為它只影響候選排序。
8. **範圍外的小改動**：
   - `api/tuning/objects.py` 的 AI 表頂端提示加一行。
   - 前面列的測試因為程式預設值拿掉而改寫，只換建構方式，斷言的意思不變。
   - `scripts/x10/fields.yaml` 的 AI 段把新欄位列為「不換算」（點數、格數、‰，不是量類）。

## 8. 平衡疑慮（無）

沒有。只換數字放的地方；434 招預算、閃現出題、78 場戰鬥（含 AI 每個動作）逐項相同。

## 開發 PM 裁定（2026-11-21）

合併進 main（`--no-ff`）。合併後在 main 重跑 ruff、format、mypy、lint-imports、`classify.py --check`、`trpg content check`，結束碼都是 0。全量檢查由 push hook 跑。

待 PM 決定的 8 件：
1. **`Ruleset.ai` 必填，舊戰鬥紀錄讀不回來**：照做。
   - 已查過只有戰鬥紀錄（`BattleLog`）內嵌整份規則包。一輪存檔、世界存檔、聯賽都只存雜湊或規則鍵，不受影響。
   - `docs/phases/戰鬥紀錄格式變更.md` 1.2 已定：規則包資料結構改變時不升 `LOG_FORMAT`，舊紀錄被拒絕重播。HC-4b2 的 `modifier_bounds` 也是一樣。
   - 差別只在拒絕時給的訊息：現在是 pydantic 驗證失敗，不是雜湊不符的中文說明。
   - 排進佇列：重播與賽程封存讀到驗證失敗時，改給同一句中文說明（HC-7 b 順手做）。
2. **「應變」改讀效果的 `amount`**：照做。現有內容結果不變；自訂種族照實際值判斷，比較合理。
3. **兩組同義常數各合成一格**：照做。
4. **搬完 0 筆的規則直接刪掉**：照做，和前例一致。
5. **4 筆改判 guard 或 const**：照做。
6. **`AiProfile` 的 13 張子表改必填**：照做。
7. **工坊只開 35 格代表性欄位**：照做。沒開的清單留在報告 3.3，使用者要調再開。
8. **範圍外的小改動**：接受。
