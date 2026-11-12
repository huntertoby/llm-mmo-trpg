# Phase BS-1 完成報告｜連續背刺（#157）＋ DD-3 雙牙兩下命中中毒（#158）

> 規格：沒有另寫計畫檔，以設計文件為準——#157：`docs/玩法決定紀錄.md` #157、`docs/design/06-技能.md` 6.21.1、`docs/design/05-戰鬥.md` 5.1「朝向與背刺」；#158：`docs/玩法決定紀錄.md` #158、`docs/design/08-裝備.md` 8.11「雙牙、刃舞的雙匕首特色」。前端（「背刺・無聲（不會轉身）」字樣、「要拿匕首類」標灰）是之後的 BS-2，本段只做後端與預覽／紀錄的資料。
> 基準：main `daf4dae4`（LW-1 之後，`LOG_FORMAT` `/118`）。
> 使用者 2026-11-13 指示：「都不用再量數值了 寫個可能有問題記在.md上就好了 平衡 之後再說 先做遊戲」——本段**沒有**跑任何平衡模擬或報表；疑慮列在第 6 節。不變比對（正確性）照做。

## 0. 依設計整理的規格要點

**#157 連續背刺**

1. 一般規則不變：被近戰攻擊（不論命中）就轉向攻擊者；背刺命中 +2、暴擊範圍 +1；敵我、頭目都適用。只有 B、C 兩種例外。
2. **B 從隱蔽中出手**：攻擊者帶 `concealed` 時的近戰攻擊，目標不轉向；出手後照舊脫離隱蔽（潛行偷襲）。任何武器、敵我都適用。
3. **C 無聲**（修正效果 `silent_strike`）：持有者的近戰攻擊（普攻、武器技、反應攻擊）不讓目標轉向；只在手持匕首、雙匕首時生效（換武器不成立）；來源只限隱蔽關鍵字的技能與被動（被動常駐，或主動技能給幾回合），不能是詞條或武器特性，放錯地方驗證擋下（含 LLM、工坊）；只管自己的攻擊（隊友正面照轉、目標自己回合照轉）；敵方預設沒有。
4. 示範（初稿）：被動「無聲步」、主動「影纏」（傷害；手持匕首類時接下來 2 回合獲得無聲）。
5. 預覽與紀錄顯示「背刺・無聲（不會轉身）」（資料由本段給，字由 BS-2 接）。
6. AI：持有無聲時留在目標背後、不要走開，併進 PB-1b2 的繞背站位分。
7. 數值工坊開放：背刺命中加成、背刺暴擊範圍、潛行偷襲命中加成、無聲的預算成本（被動常駐、主動給的回合數各一）。

**#158 雙牙**

1. 拿掉「拿雙匕首多一段傷害」，只留一個傷害效果。
2. 拿雙匕首、兩下都命中同一目標時，第二下命中時上既有的「中毒」一次；第一下打倒、任一下沒中、任一下被守護者攔下、沒拿雙匕首都不成立。是 #153「附加效果看第一個命中」的例外。
3. 引擎新增「這次施放每一下都命中」條件（定名 `all_strikes_hit`），第一版只有雙牙用（LLM、閃現、詞條之後再問）。
4. 雙牙算「中毒」關鍵字的製造者；刃舞不改；中毒回合數開進數值工坊。

## 1. 做了什麼

### 1.1 #157 連續背刺

**引擎**

- `src/trpg/engine/quiet_strikes.py`（新）：`no_turn_reason(state, attacker, skill=None, *, modified=True)` → `concealed`（命中判定當下帶隱蔽，B 先判）／`silent`（C）／`None`。無聲只算普攻（含藉機攻擊等反應攻擊）與 `category: weapon` 的技能，而且是 `modified` 的施放（被動與陷阱觸發不是「你的動作」）。
- 普攻 `reactions.perform_unit_attack`：第一下之前判斷，有原因就不記轉身（`turns` 空）；每一下（連擊、分裂、詞條連擊）的 `attack_rolled` 帶 `no_turn`。
- 技能 `skills/cast.py::Cast.roll_one`：有原因就不記 `melee_victims`；守護者攔下時「把最後一筆換成守護者」也只在沒有例外時做（守護者也不轉）。原本的條件「近戰且清單不空」保留，所以雙匕首第二下被攔的既有行為不變。
- `modifiers.silent_strike(state, unit, use)`、`SILENT_WEAPONS`（`dagger`、`dual_dagger`；看 `unit.weapon`＝實際出手的武器，形態中的天生武器不算）；`CHANGE_HANDLERS` 登記。`unit_rules` 改讀 `unit.all_skills`：`grant_skill` 暫時給的修正技能也生效（只有「只含無聲」的修正技能能被給，見下）。
- 事件 `attack_rolled.no_turn`（`concealed`／`silent`／`None`，`exclude_if` None：沒有例外時 JSON 逐字不變）。
- 預覽 `Preview.no_turn`（目標 ID）、`no_turn_reason`，`notes` 每個目標一句：「背刺・無聲（不會轉身）：盜賊」「從隱蔽中出手（不會轉身）：盜賊」。API `PreviewOut.no_turn`、`no_turn_reason`（`| None = None`，前端型別不變成必填）；openapi 與 `schema.d.ts` 重產。
- 戰鬥紀錄文字（`narrative/events.py`）：命中判定那行尾巴加「［背刺・無聲（不會轉身）］」／「［無聲（不會轉身）］」／「［隱蔽出手（不會轉身）］」。
- AI：`ai/parts.py::silent_behind_extra`（併在 `circle_back_extra` 旁），`position._facing_terms` 呼叫：持有無聲（手持匕首類、近戰）時站在相鄰敵人背後格，每名加 `silent_behind`（`ai_profiles.yaml` 的 `facing:` 表，占位 4，疊在 `backstab` 4 上）。敵我同一套。

**內容 schema 與驗證**

- `ModifierChange.silent_strike`（只能 `true`，`exclude_if` None：既有修正技能序列化與 parity 雜湊不變）；`content/modifier_changes.yaml` 一筆（`applies_to: [all_attacks]`、`self_only`、`true_only`、預算 `flag`）；卡片文字「無聲：手持匕首或雙匕首時，你的近戰攻擊不會讓目標轉身（可以留在背後連續背刺）」；工坊選項 bool。隨機組合器不用它（`_LADDERS` 沒列）。
- 關鍵字：`skill_keywords.yaml` 隱蔽的 `uses` 加 `{change: silent_strike}` 與 `{effect: grant_skill, skill: skill_silent_step}`。
- `src/trpg/content/silent_strike.py`（新）：`carries_silent`（自己帶 `silent_strike`，或 `grant_skill` 給出帶無聲的技能）、`silent_strike_problems`：帶無聲的技能**專屬關鍵字必須恰好只有 `concealed`**。三處擋：內容載入（`skill_checks._check_keywords` 之後）、`validate_skill`（規則碼 `silent_strike.source`，LLM 提議 `evaluate_proposal`、工坊、白板共用）、詞條「授予動作」（`gear_checks._action_problems`：給出的主動技若會給無聲就擋）。詞條本身沒有修正規則欄位、武器特性是固定清單，所以結構上放不進去。
- `grant_skill` 的例外：`is_silent_grant`（修正技能、不需啟動、每條規則都是 `silent_strike`）可以被給（`granted_skill_problems`）；預算改每回合 `skill_budget.yaml` 的 `silent_strike_round_milli`（占位 600＝0.6 點／回合）。被動常駐的價值 `modifier.points_milli.silent_strike`（占位 360 × 所有攻擊 10 次＝3.6 點）。
- LLM 與工坊：修正型骨架本來就不開放 LLM 提議；`grant_skill` 能選的技能（LLM 的 `proposal/params.py::grantable_skills`、工坊的 `option_params` 技能選單）多了「只含無聲」的修正技能（和 `granted_skill_problems` 同一套），所以 LLM／工坊可以組「給無聲步」的招，放在隱蔽以外的主題時由 `validate_skill` 的 `silent_strike.source` 擋下（`evaluate_proposal` 走同一個函式，有往返測試）。

**內容**

| 檔案 | 內容 | 預算 |
|---|---|---|
| `skills/skill_silent_step.yaml` 無聲步 | 修正型被動（史詩）、`all_attacks` → `silent_strike: true`、標籤 `stealth` | 85.7% |
| `skills/skill_shadow_bind.yaml` 影纏 | 近戰武器技（稀有、`combo` 骨架、2 AP、耐力 8、冷卻 2）：武器倍率 1450；手持匕首或雙匕首時 `grant_skill` 無聲步 2 回合（`wielding_weapon` dagger `any_of` dual_dagger） | 71.2%（倍率 1000 時 49%，取合格內最低的一階） |

兩招都進 `test_coverage.py::_POOL_ONLY`（`builds.yaml` 是模擬回歸範本，不為示範改動）。

**數值工坊**：`tuning_fields.yaml` 新兩類對象——`rules`（`rules/core.yaml`：`backstab_hit_bonus`、`backstab_crit_range_bonus`、`ambush_hit_bonus`）與 `budget`（`skill_budget.yaml`：`modifier.points_milli.silent_strike`、`silent_strike_round_milli`）。`TARGET_MODELS` 加 `CoreRules`、`BudgetRules`；`TABLE_KINDS`（`ai`、`rules`、`budget`）共用 `api/tuning/objects.py` 的「全體共用的表」分支（名稱、提示 `TABLE_NOTES_ZH`）；`TuningCategory` 多 `rules`。影纏給的回合數是技能欄位（`effects[*].duration`，`grant_skill` 已在白名單）。**前端還沒接這兩類**（見待決 2）。

### 1.2 #158 雙牙（DD-3）

- 條件 `all_strikes_hit`（`skill_conditions.yaml`，`harsh`、`rare`，`handwritten_only: true`）：`REQUIRED_CONDITIONS` 19 → 20；條件句「每一下都命中同一個目標（雙匕首兩下都中）」。
- 引擎 `Cast`：帶這個條件的效果在第一輪與 `_strike_effects` 都跳過；`extra_strikes()` 打滿、每一下都命中原本的目標（沒被守護者攔：`redirected`；`enemies[0] is original`）才 `settle_all_strikes()` 結算一次（在最後一下的傷害之後）。`Cast.holds` 回 `all_strikes_landed`；`condition_met` 在施放以外一律不成立。不打兩下時永遠不結算。
- 驗證：只能寫在效果的 `condition`（技能、第二段、修正規則的條件與 `any_of` 都擋，`skills/problems.py::_all_strikes_problems`）。`handwritten_only`（新欄位，沒填不輸出）：LLM schema 不列（`builder._condition_union`）、工坊／白板選項標 `unavailable_zh`、`validate_skill` 擋「不是內建、不是開局包、沒有 `parents`」的技能（`condition.handwritten_only`）——比照 LW-1 的 `self_lacks_status`，但從內建技能進化或閃現改寫的照原招保留。
- `sim/skill_ratio.py`：`all_strikes_hit` 和 `wielding_weapon` 一樣不另做情境（`_NATURAL_CONDITIONS`），比值腳本跑到雙牙不會 `ValueError`。
- 內容 `skill_twin_fang.yaml`：效果剩「傷害 1350」＋「`apply_status` 中毒 3 回合，條件 `all_strikes_hit`」（中毒回合數寫明，數值工坊 `effects[*].duration` 會展開）。倍率 1150 時預算 62.8%（過弱，條件效果打 6 折），取合格內最低的一階 1350（71.7%）。
- **關鍵字池**（對照改前 `daf4dae4`）：雙牙原本沒有任何專屬關鍵字（基礎技能、通用池），現在專屬「中毒」製造者；中毒池 16 → 17 招、隱蔽池 42 → 44 招（多無聲步、影纏）。開局技能池與候選產生器只看專屬關鍵字，所以抽到中毒主題時會多一個候選雙牙、不再當基礎技能出現；`skill_evolution`、隨機組合器不受影響（parity 只有三招的 `complete`／`retier` 變，見第 5 節）。推薦本身沒有寫死雙牙。
- 刃舞不改。

### 1.3 版號

- `LOG_FORMAT` `/118` → `/119`（事件多 `no_turn`、結算改變）；`docs/phases/戰鬥紀錄格式變更.md` 加一條；測試寫死的版號 9 處＋開發 PM 指出的三個 slow 測試（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py` 的 `endswith`，main 上另一個 agent 改成 `/118`，本段改 `/119`，合併時會衝突）。`git fetch` 後 origin/main 仍是 `/117`（`/118` 的 LW-1 還沒 push），照指示另升 `/119`。
- `WORLD_RULES_VERSION` 不動（世界規則沒變；日誌規則鍵本來就含 `LOG_FORMAT` 與內容 digest）。

### 1.4 前端（只為了既有測試與型別，不是 BS-2）

`openapi.json`／`schema.d.ts` 重產；`glossary.json`（多 `all_strikes_hit` 條件）、`skill_icons.json`（多兩招、雙牙變）、`skillCards.json`（雙牙變）重產；`render/qIcon/parts.ts` 加兩筆**暫代**：條件 `all_strikes_hit` 借「手持指定武器」、修正 `silent_strike` 借條件「潛行偷襲」的兜帽（沒有新畫）；`qIconSkills.test.ts` 條件 19 → 20、修正 21 → 22、招數 407 → 409；`qIconQi2d.test.ts` 加 `ADDED_PARTS` 兩筆、`ADDED_AFTER_BASELINE` 兩招、新的 `CONTENT_CHANGED`（雙牙主圖跟著內容變）、修正技對照排除基準之後的新招。

## 2. 測試

新增：

| 檔案 | 內容 |
|---|---|
| `tests/engine/test_quiet_strikes_bs1.py`（23） | 一般背刺照轉；B：隱蔽普攻（匕首、單手劍、雙手劍）不轉、脫離隱蔽、下一下照轉；隱蔽武器技不轉；敵方隱蔽也適用；C：匕首／雙匕首普攻不轉、留在背後下一下仍背刺、紀錄文字；單手劍、矛、雙手劍不成立；武器技不轉；藉機攻擊（反應攻擊）帶 `silent`；沒有修正規則時沒有原因、被動觸發不算；隊友從正面打照轉；目標自己回合出手照轉、刺客得再繞背；守護者攔下無聲的一擊也不轉；影纏拿匕首給 2 回合無聲、之後普攻不轉；拿劍不給；已裝無聲步時 fizzle；預覽 `no_turn`、`no_turn_reason`、notes「背刺・無聲（不會轉身）」「從隱蔽中出手（不會轉身）」；沒有例外時事件 JSON 不帶 `no_turn`；AI 留背加分（換劍、側面、沒有無聲都是 0） |
| `tests/engine/test_twin_fang_dd3.py`（12） | 雙牙只剩一個傷害＋條件中毒、回合數讀現值；兩下都中中毒一次且在最後一下傷害之後；中／沒中、沒中／中、都沒中不中毒；第一下打倒不中毒；拿匕首、單手劍不中毒（只打一下）；守護者攔下不中毒；最多後果預覽有中毒、最少沒有；條件在施放外不成立；技能層級與 `any_of` 擋下 |
| `tests/skillgen/test_silent_strike_bs1.py`（9） | 兩招示範通過、帶無聲；影纏改火焰、無聲步加「帶火」都被 `silent_strike_problems` 與 `validate_skill` 擋；LLM：schema 的 `grant_skill` 列舉有無聲步，火焰版影纏的提議往返被 `silent_strike.source` 擋、原版影纏不擋；詞條授予影纏被擋；`grant_skill` 只能給「只有無聲」的修正技；關鍵字池（隱蔽有兩招、中毒有雙牙）；`all_strikes_hit` 不在 LLM schema、選項標不可選、工坊／升等／掉落來源的新技能擋、從雙牙進化的不擋 |

改到的既有測試（登記處或寫死的數字，斷言不放寬）：`test_skill_scaling.py` 407 → 409、`test_skill_icon_art_qi2a.py` 407 → 409、`test_tuning_fields_nw2a.py` 404 → 406 個技能檔、`tuning/test_yaml_patch_nw2a.py` 404 → 406、`test_coverage.py` `_POOL_ONLY` 加兩招、`test_modifier_schema.py` 加 `silent_strike` 範例、`test_proposal.py`（`handwritten_only` 條件斷言不在 schema）、`tests/api/test_routes.py` 預覽回應的鍵多 `no_turn`、`no_turn_reason`、`refactor_3wr2.json` 只動三招的 `complete`／`retier`（雙牙內容變、兩招新招；其他鍵沒動，`flash` 全部不變）、CLI 快照 7 鍵（第 5 節）。

## 3. 不變比對

腳本在 scratchpad（不進 repo）：`sim.batch.map_spec`（地圖預設陣容、效用 AI、`max_rounds=30`）＋`run_battle`，存整份紀錄去掉 `format`、`ruleset_hash`、`setup.ruleset`、`final_state.ruleset`；改前用 `git archive daf4dae4 src content` 解開、`PYTHONPATH` 指過去。8 張地圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12。

**`battles=46 events=20499 different=6`**；40 場逐字相同。6 場都在 `cloud_summit`，逐場歸因（分歧點之前都有 `no_turn: concealed` 的隱蔽近戰出手；沒有無聲、沒有雙牙施放）：

| 場次 | 隱蔽近戰出手（攻擊者 → 目標） | 差異 |
|---|---|---|
| `cloud_summit` 10 | 1 次（`unit_0004` → `unit_0001`，seq 191） | 只差 `no_turn` 欄位；事件順序、數值、最終狀態相同 |
| `cloud_summit` 12 | 1 次（`unit_0008` → `unit_0002`，seq 589） | 只差 `no_turn` 欄位，最終狀態相同 |
| `cloud_summit` 8 | 2 次（`unit_0004`、`unit_0009` → `unit_0001`，第一次 seq 184） | 只差 `no_turn` 欄位，最終狀態相同 |
| `cloud_summit` 9 | 1 次（`unit_0004` → `unit_0002`，seq 323） | 只差 `no_turn` 欄位，最終狀態相同 |
| `cloud_summit` 5 | 2 次（第一次 seq 387） | 第 392 個事件起分歧（目標沒轉身，之後的行動不同）；勝方不變（敵方）；最終狀態（去掉規則包）相同 |
| `cloud_summit` 6 | 2 次（第一次 seq 474） | 第 478 個事件起分歧；勝方不變（敵方）；最終狀態 `unit_0002.facing` east → west |

`ModifierChange.silent_strike` 改成不輸出空值之後重跑一次改後，結果相同。

## 4. 數值工坊欄位（占位，沒調）

| 對象 | 路徑 | 現值 |
|---|---|---|
| 核心戰鬥規則 | `backstab_hit_bonus` | 2 |
| 核心戰鬥規則 | `backstab_crit_range_bonus` | 1 |
| 核心戰鬥規則 | `ambush_hit_bonus` | 2 |
| 技能預算表 | `modifier.points_milli.silent_strike` | 360（無聲被動 3.6 點） |
| 技能預算表 | `silent_strike_round_milli` | 600（主動給 1 回合 0.6 點） |
| 雙牙 | `effects[1].duration`（中毒回合） | 3（狀態預設） |
| 影纏 | `effects[1].duration`（給無聲回合） | 2 |
| AI 估值 | `facing.silent_behind` | 4（沒開進工坊，AI 表只開 `parts.*`，見待決 2） |

## 5. 檢查與結束碼

| 指令 | 結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1537 個檔） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| `uv run trpg content check` | 0（667 個檔、409 個技能） |
| `trpg battle --map open_plain --seed 7` ＋ `battle replay` | 0：重播驗證通過（91 個動作、383 個事件） |
| 相關 pytest（`tests/api`、`tests/content`、`tests/skillgen`、`tests/narrative`、`tests/sim/test_skill_ratio.py`、架構、原語覆蓋、engine 的朝向／背刺／連擊／守護者／確定性／預覽／修正規則／AI／重播／視圖／敵人招式、`tests/world/test_enemy_ai_moves_149.py`、CLI 非 slow，`-n 8`） | 第一次 2 failed／9283 passed：`test_routes.py` 預覽回應的鍵（多 `no_turn`、`no_turn_reason`，補進期望集合）、`test_workshop_options.py`（工坊的 `grant_skill` 選單不含無聲步 → 選單與 LLM 列舉都加「只含無聲」的修正技）；修完重跑 `tests/api tests/skillgen tests/content/test_coverage.py -n 8`：0（5197 passed、15 skipped）；`tests/content -n 4`：0（3027 passed）；engine、narrative、sim、架構各組：0 |
| slow：`tests/skillgen/test_refactor_parity.py -m slow` | 第一次 22 failed（`ModifierChange` 多一個 `null` 欄位讓所有修正技的 `retier` 雜湊變、雙牙兩鍵）；改成不輸出空值後只剩雙牙 2 項；只更新三招的 `complete`／`retier` 後 0 |
| slow：`test_refactor_parity.py`、`test_proposal_l8.py`、`test_proposal.py`、`tests/cli -m slow`（含 `test_run_cli.py` 固定種子一輪、CLI 快照）最後一次 | 0（940 passed） |
| `test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py` 的版號斷言（`/119`） | 0 |
| `tests/cli/test_output_snapshots.py -m slow` | 改前 7 failed／17 passed；只重產那 7 鍵後 24 passed |
| `corepack pnpm -C client exec vitest run` | 0：328 檔、4272 passed |
| `corepack pnpm -C client typecheck` | 0 |

**CLI 快照逐鍵說明**（`tests/cli/snapshots/cli_output_hashes.json`，7 個戰鬥鍵與 `skills_show_all/00～09` 不變）：

| 鍵 | 原因 |
|---|---|
| `skills_list` | 多兩招（無聲步、影纏）、雙牙的效果摘要變 |
| `skills_show_all/10` | 分片照技能 ID 排序切 26 招一片：`skill_shadow_bind`、`skill_silent_step` 插進這片，`skill_splash_flask`、`skill_st_dawn_vigil` 移到下一片 |
| `skills_show_all/11`、`/12`、`/14`、`/15` | 前一片插入兩招造成的整片位移（每片進兩招、出兩招；`/15` 最後一片多兩招） |
| `skills_show_all/13` | 位移，加上含雙牙（效果改了） |

歸因：scratchpad 的 `shards.py` 用「改後全部 ID」與「去掉兩招的 ID」各切 16 片，列出成員不同或含雙牙的片＝`10`～`15`，加 `skills_list`，和實際失敗的 7 鍵相同。

沒跑 `scripts/check.py`、沒跑任何平衡模擬。

## 6. 平衡疑慮（沒量，只列出）

1. **B 讓隱蔽系一律連打**：任何武器從隱蔽中近戰出手都不轉身；有「打出後再隱蔽」的招（例：無人掩護、霧遁）就能每回合背刺。雲頂觀的霧遁敵人也吃到（不變比對 6 場）。
2. **無聲步 3.6 點（史詩 85.7%）**：搭雙匕首普攻／武器技每回合兩下背刺（命中 +2、暴擊 19–20），預算只算「每次攻擊值 0.36 點」。設計就提醒「刺客最強的時刻，預算成本要在工坊盯著」。
3. **影纏 1450 倍率**：為了過預算（給無聲每回合只值 0.6 點）倍率被拉到 1.45，不拿匕首時也是一支 1.45 倍、冷卻 2 的近戰武器技。
4. **雙牙改成 1350 單段**：不拿雙匕首的近戰（含霧狼、灰燼獵犬這兩種敵人）每次從 1.15 變 1.35，**敵人的雙牙變痛**；拿雙匕首的玩家從「四段（2 × 1.15＋2 × 1.0）」變成「兩段 1.35＋偶爾中毒」，明顯變弱。
5. **`all_strikes_hit` 預算倍率 0.6（harsh）**：實際成立率約「兩下命中率相乘」再乘「拿雙匕首」，0.6 可能偏高（中毒點數被高估）。
6. **AI 留背 `silent_behind` 4**：疊在 `backstab` 4 上，持有無聲的近戰 AI 會很黏背；沒量會不會因此不去打更值得打的目標。
7. **守護者攔下無聲的一擊也不轉**：攔截者（坦克）常常就站在旁邊，若之後想讓坦克「被打會轉向刺客」當反制，這條要再定。

## 7. 待 PM 決定

1. **影纏「接下來 2 回合」的算法**：`grant_skill` 在自己回合結束時倒數，`duration: 2`＝施放那回合剩下＋下一個自己的回合（中間別人的回合也有，能藉機攻擊）。若要「施放後再兩個完整回合」改成 3。影纏這一下本身沒有無聲（施放結算完才獲得）。
2. **數值工坊前端還沒接** `rules`、`budget` 兩類對象（後端 `/api/tuning/objects?kind=rules|budget` 已有，`TuningScreen` 只抓 `unit`、`ai`）；AI 表的 `facing.silent_behind` 也沒開（AI 表目前只開 `parts.*`）。建議併入 BS-2 或 NW-3。
3. **「隱蔽關鍵字的技能」的解讀**：帶無聲的技能**專屬關鍵字必須恰好只有隱蔽**（無聲本身推導成隱蔽），所以「毒＋無聲」「火＋無聲」這類混主題的都擋。是比較嚴的讀法。
4. **無聲看「實際出手的武器」**：形態（化形）中用天生武器普攻不算匕首類；武器技在形態中仍看手上武器，但本段一律看 `unit.weapon`（形態中不成立）。
5. **無聲只算普攻與武器技**（`category: weapon`）；拿匕首放近戰法術（`category: spell`、射程 1）仍會讓目標轉身。B（隱蔽）則不分技能類別。
6. **守護者攔下時也不轉**（B、C 都是）：設計只說「目標不轉向」，攔截者轉不轉沒寫；採「這次攻擊誰都不轉」。
7. **雙牙、影纏的倍率是為了過預算的最低一階**（雙牙 1150 → 1350、影纏 1000 → 1450），請使用者在工坊調；或把 `all_strikes_hit` 的預算倍率、無聲每回合價值調高，倍率就能降。
8. **`all_strikes_hit` 的「只給手寫技能」**：擋的是「不是內建、不是開局包、沒有 `parents`」的技能；從雙牙進化、閃現改寫出來的技能保留條件（照原招）。若連進化版也要拿掉，要改閃現。
9. **無聲的 Q 版圖示與「每一下都命中」條件圖示是暫代**（借兜帽、借單手劍），請美術 PM 出圖。
10. **版號**：`/118` 還沒 push 就升 `/119`（照「先 fetch」的指示另升）；三個 slow 測試的 `endswith` 和 main 上的改動會衝突，合併時取 `/119`。

## 8. 新增的複雜度類 noqa

無。`Cast.__init__` 已在 `PLR0915` 上限（50 句），新旗標 `all_strikes_landed`、`redirected` 改成類別屬性當預設；`preview()` 同樣在上限，把三個回傳值併成一個 `_no_turn_info`。
