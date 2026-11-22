# Phase HC-7 報告：其餘 config 搬家、剩下的 text 收尾

依據：`docs/phases/PhaseHC-7計畫.md`；做法照 HC-4d、HC-6a、HC-6b 與各段的開發 PM 裁定。
基準：main `7772b2ba9`。分支 `worktree-agent-ab3c29ee01d7dc811`，沒 push。
數值一律照現值搬，沒試數值、沒跑模擬。沒動 `docs/design/`、`config/`、`CLAUDE.md`、計畫檔。

## a. engine、world、剩下的 text

### a.0 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| a.1 engine 的 config | `7c05bbfba` | 暴擊範圍下限、開場狀態回合上限、破甲預設降幅、部位「遠處」格數、灌注施放的選取分數搬進 content；符文輪數、破誓回合改必填 |
| a.2 world 的 config | `21728db56` | 開局結束等級、新手任務步數、看示範關鍵字數搬進 `world/newcomer.yaml`；沒有世界規則的備用值拿掉，或合成載入層一份；請求上限改判 guard |
| a.3 剩下的後端 text | `b5172811d` | 誓約冷卻組字、拿掉「沒寫＝5／4」；7 個檢查的數字搬進 content；結構性的改判 const |
| 收尾 | `b40c31cd7` | `--md` 重產 `寫死數值-清單.md` |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff check、ruff format --check、mypy、lint-imports、`classify.py --check`、`trpg content check` 與相關測試（經看門狗）。

### a.1 engine（config 17 → 0）

**搬進 content**（`Ruleset` 多的欄位都必填，內容檔寫明現值）：

| 原本 | 搬到 | 值 |
|---|---|---|
| `rules/combat.py` 3 處、`skills/targeting.py`、`summons/variants.py` 的 `max(2, …)`／`_MIN_CRIT` | `core.yaml` 的 `crit_range_floor` | 2 |
| `engine/battle.py` 的 `OPENING_STATUS_MAX_DURATION`（API `world_growth_view` 也用） | `core.yaml` 的 `opening_status_max_duration` | 2 |
| `rules/statuses.py` 的 `DEFAULT_DEFENSE_BREAK` | `core.yaml` 的 `defense_break_default_permille` | 100 |
| `engine/parts.py` 的 `FAR_BEYOND`（距離 > 3） | `core.yaml` 的 `boss_parts.high_or_far_distance`（距離 ≥ 4） | 4 |
| `skill_infusion.py` 的 `_ENEMY_POINTS`、`_ALLY_HIT_POINTS` | `ai_profiles.yaml` 的 `heuristics.infused_pick`（`enemy_points`、`ally_hit_penalty`） | 10、15 |

- `PART_REASON_ZH["need_high_or_far"]` 改成 `{far}` 占位。新函式 `part_reason_zh(rules, reason)` 填格數，API 與 `check_target_part` 改呼叫它；字不變。
- **改必填**：
  - `AttackAffix.rune_rounds` 在 `rune: inscribe` 時必填。唯一一條內容寫了 2，`DEFAULT_RUNE_ROUNDS` 刪掉。
  - `OathSetup.penalty_rounds` 拿掉預設 2。唯一的呼叫點 `world/oaths.py` 本來就帶 `oaths.yaml` 的值。
- **改判 guard**：`ChangeTileEffect.height` 的 `le=3` 改讀 `content/maps.py` 的 `MAX_HEIGHT`（地圖高度格式）。
- **改判 const**（理由寫在 `classes.yaml`）：
  - `effects/handlers.py`、`preview.py` 的「骰數 × 2」：暴擊的定義是骰子顆數加倍（見待決 1）。
  - `UnitState.ap_per_turn = 3`：只給 AP-1（`/134`）以前存下的戰鬥狀態 JSON 相容。新單位一律由 `make_unit` 照 `core.template_ap_per_turn` 帶入（見待決 2）。
- **LOG_FORMAT 判斷：不升**（`docs/phases/戰鬥紀錄格式變更.md` 1.2）。
  - 事件、動作、狀態的欄位沒有增減；同一規則包與步驟結算相同（78 場 different=0）。
  - 規則包多了新欄位，`ruleset_hash` 會變，舊紀錄因雜湊不符被拒（1.2 的既有說明）。
  - 但新欄位是必填：舊紀錄內嵌的規則包在算雜湊之前，就會先在 pydantic 驗證失敗，訊息是驗證錯誤原文。這是 b.4（HC-4c 裁定 1）要處理的，b 段一起做（待決 7）。
- 新測試 `tests/engine/test_rules_from_content_hc7.py`：值照搬、缺欄位驗證失敗、暴擊下限與部位格數改了會跟著變、符文輪數與破誓回合必填。
- 文件：`docs/dev/上手-引擎戰鬥結算.md` 第七節 config 類的例子原本是 `DEFAULT_DEFENSE_BREAK`，換成 b 段的 `py-llm-config-config-number`。

### a.2 world（config 42 → 0；api 的 `NO_RULES_WALK_MAX_STEPS` 1 筆一起）

**搬進 content**：

| 原本 | 搬到 | 值 |
|---|---|---|
| `world/growth.py` 的 `OPENING_END_LEVEL` | `world/newcomer.yaml` 的 `opening_end_level`（`opening_limits.opening_end_level(library)`） | 4 |
| `world/opening_limits.py` 的 `STARTER_STEPS` | `world/newcomer.yaml` 的 `starter_steps`（`starter_steps(library)`） | 2 |
| `world/opening.py` 的 `MAX_TRIAL_KEYWORDS` | `world/newcomer.yaml` 的 `range.trial_keywords_max` | 2 |
| `world/solutions.py` 的 `MAX_SKILL_TIER` | 改讀 `core.skill_limits.tiers` | 5 |

- 呼叫端改成帶內容庫：`flash_blocked_zh(library, char)`、`opening_limits(library, char)`、`reselect_window_problem(library, char)`、`holds_step(library, …)`、`reselect_weapon_zh(library)`。
- `opening.py` 模組層的兩句擋下原因改成 `{level}` 占位，用的時候代入；字不變。
- 沒有 `world/newcomer.yaml` 時，這幾個函式報 `WorldError`。呼叫點都在「角色有開局狀態」之後，正式內容一定有這個檔。

**HC-4d 裁定 2（沒有世界規則時的備用值）**：先把所有備用值改成報錯，跑一輪 world、api、server、bot、sim、roguelite 測試。只有兩個專測備用值的測試碰到：
- **改必填（沒有就報錯）**：
  - `calendar_of`、`week_days`、`_walk_max_steps` 改走 `rules_of`；`NO_RULES_CALENDAR`、`NO_RULES_WEEK_DAYS`、`NO_RULES_WALK_MAX_STEPS` 刪掉。
  - `companions._max_hired`、`shadows.record_lent` 沒有傭兵表時報錯（原本是 2、20）。
- **真的需要的兩處，只留一份、放在 content 載入層**（規則 `py-content-no-file-fallbacks`，config done）：
  - `content/world_rules.py` 的 `FALLBACK_CALENDAR`（480、6）：呼叫 `trpg.world.clock` 沒給日曆時用（伺服器公告沒有內容庫的舊路徑、測試）。取代 `clock.py` 的 `UTC_OFFSET_SECONDS`、`REFRESH_HOUR` 與 `calendar.py` 的 `NO_RULES_CALENDAR` 兩份。
  - `content/world_quests.py` 的 `NO_FILE_AFFINITY_RULES`：沒有 `world/affinity.yaml` 時由載入器放進 `WorldQuestContent.affinity`（型別不再是 `| None`），取代 `world/affinity.py` 的 `DEFAULT_AFFINITY_RULES`。「沒有聊天內容照樣能聊、算中立」的測試仍需要它。
- 新測試 `tests/world/test_rule_defaults_hc7.py`：兩份備用值和內容檔相同；沒給日曆的時鐘和 `day_of` 相同；沒有世界規則與新手檔時報錯。

**改判 guard**（22 筆，`py-world-action-request-guards`、`py-world-state-format-guards`）：動作請求與存檔的格式上限。真正的規則上限在內容檔，由規則檢查：
- 雇傭 8（`max_hired` 2）、許願關鍵字 4（`wish.max_keywords` 2）、開局與重選關鍵字 4、傳承 2（`max_carry`，同值，見待決 4）；
- 打造材料 5（`flavor_max` 3）、物品等級 99、詞條位置 0～7、強化 0～10（`enhance.max_level` 3）；
- 買 10、賣 99、腰包 10、戰後丟棄 40、郵件附件 10（`max_attachments` 3）、郵寄金幣 1000 萬。

**改判 const**：`clock.py` 的 `GAME_DAY_SECONDS`（30 分鐘）、`_GAME_DAY_START_MINUTE`（06:00）。
- 這是世界時間軸的格式：`day_phase(now)` 等直接從 UTC 秒數算，拿不到內容庫；改了舊世界的日序與天氣全部重排。
- `CalendarRules` 的說明本來就寫「遊戲日長度與天氣週期是使用者定的常數」（見待決 3）。

其他：
- `WORLD_RULES_VERSION` 沒升：世界推進的規則沒變，`world/rules.yaml` 沒有新鍵。`newcomer.yaml`、`encounters/*.yaml` 多了鍵，內容 digest 本來就會變。
- 測試改寫（只換取值方式，斷言意思不變）：`test_affinity.py`、`test_field.py`、`test_rule_defaults_hc4d.py`、`test_opening_*.py`、`test_ob5_screen_data.py`、`test_ob6_reselect.py`、`test_opening_flash.py`、`test_newcomer_content.py`、`test_world_quests.py`。
- 新的 `tests/world/opening_rules.py`：從正式內容讀一次開局的兩個數字給測試用。

### a.3 剩下的後端 text（30 → 3）

**玩家看到的字改了的兩處（改前 → 改後）**：

| 位置 | 改前 | 改後 |
|---|---|---|
| 誓約冷卻：`world/growth.py` 擋下的原因、`api/world_growth_view.py` 的立誓檢查與動作紀錄，共 3 處 | 寫死「解除誓約後 1 天內不能再立誓」「現實 1 天內不能再立誓。」 | 從 `oaths.yaml` 的 `cooldown_seconds` 組字（`content/world_oaths.py` 新函式 `cooldown_zh`）：整除 86400 寫「N 天」，不整除寫「N 小時」（四捨五入，同前端 `aboutDurationText`）。目前 86400 →「1 天」，**三處組出來和改前逐字相同** |
| 數值工坊 `api/tuning/objects.py` 的 `_DEFAULTS_ZH` | 移動力 `speed`「沒寫＝5」、表面生長排數 `phases[*].grow_surface.max_rows`「沒寫＝4」 | 兩條拿掉，`default_zh` 是 `None`，欄位旁不再顯示「沒寫＝…」。schema 已必填，這兩句本來就不會出現 |

**數字搬進 content，檢查與說明都讀它**（現值組出來字不變）：

| 原本寫死 | 搬到 | 值 |
|---|---|---|
| 塔盾「攻擊者高 2 層以上時無視」（引擎的 `+ 1`） | `core.yaml` 的 `tower_shield_cover_height`，說明寫它 +1 層 | 1 |
| 武器元素詞條同一件最多 1 條 | `rules/equipment.yaml` 的 `max_weapon_element_affixes` | 1 |
| 稀有度以外的 build 詞條、觸發詞條每件最多 1 條 | `item_gen.yaml` 的 `extra_build_affixes_max`、`trigger_affixes_max` | 1、1 |
| 靶場示範招要 1 階 | `world/newcomer.yaml` 的 `range.demo_tier` | 1 |
| 規則改變型傳說每人最多裝 1 個 | `core.yaml` 的 `skill_slots.rule_change`（API 的 `SkillSlotsOut` 沒加這一鍵） | 1 |
| 一場最多 1 名精英 | `world/encounters/*.yaml` 的 `elite_cap`（兩區） | 1 |
| 數量型分歧「count: 2 必須…」 | 照收到的 `count` 組字 | — |
| 提議提示詞「range_delta 只能填 1 或 2」 | 照提議模型的 `RangeDelta = Literal[1, 2]`（`skillgen/proposal/builder.py`）組字 | 1、2 |

**工坊新開 3 格**：照 HC-W2 的「每個整數不是開了，就是列為結構」測試；同一張表的 `max_affixes_per_item` 本來就開了。

| 表 | 欄位 | 中文名 | 建議範圍 |
|---|---|---|---|
| 裝備規則 `equipment` | `max_weapon_element_affixes` | 每件最多幾條武器元素詞條 | 1～2 |
| 物品生成 `item_gen` | `extra_build_affixes_max` | 每件最多幾條稀有度以外的詞條 | 0～2 |
| 物品生成 `item_gen` | `trigger_affixes_max` | 每件最多幾條觸發詞條 | 0～2 |

說明都寫了調高、調低的效果。其他新欄位沒開，見待決 6。

**改判 const**（結構，理由寫在 `classes.yaml`）：
- `engine/activations.py`「同時最多 1 個規則改變」：引擎一個單位只放一個生效中的規則改變（`active_rule_change` 回傳單一個）。
- `narrative/action_info.py` 6 筆：跑步每回合 1 次是布林旗標 `ran_this_turn`；推動、撥開物件 1 格是一步（`interact_direction` 回單位向量）。
- `narrative/events.py`、`summon_info.py` 4 筆：圖騰拉近 1 格是一步（`_pull_step`）；絆倒、纏住每輪 1 次是 `trip_round`、`snare_round` 記上次觸發的輪數。
- `content/skills/skill.py` 2 筆：「花 1 或 2 點源力」「必須搭配 count: 2」是 `SkillDef` 驗證裡舉的現值例子。上限本身在 `skill_limits.max_source_cost`、`max_summon_count`，由 Ruleset 層檢查並組字。

**留 text 的 3 筆**（見待決 5）：`skills/specs.py` 兩種觸發的「max_per_round 只能是 1」、`world_economy.py` 的「道具技能必須是 1 AP」。

新測試 `tests/content/test_text_from_content_hc7.py`：冷卻的天／小時寫法、塔盾、武器元素、規則改變型傳說；改值後字會跟著變。

### a.4 比對（基準 `git archive 7772b2ba9 src content scripts tests config`）

腳本放在 scratch，沒進 repo：沿用 GS-3 的 `budget434.py`、`budget_cmp.py`、`census_cmp.py`、`compare78.py`，另寫 `textdump.py`。基準執行時確認載入的 `trpg` 來自基準那份。

| 比對 | 時機 | 結果 |
|---|---|---|
| 逐招預算 442 招（`BudgetReport` repr＋`validate_skill` 違規） | a.1 後、a.3 後 | `same=442 different=0` |
| 78 場戰鬥（去掉 `ruleset_hash` 與內嵌規則包，加文字輸出） | a.1 後、a.3 後 | `battles=78 events=26206 different=0` |
| 內嵌規則包的差異 | a.3 後 | 只有 8 個新欄位：`ai.infused_pick`、`core.boss_parts.high_or_far_distance`、`core.crit_range_floor`、`core.defense_break_default_permille`、`core.opening_status_max_duration`、`core.skill_slots.rule_change`、`core.tower_shield_cover_height`、`equipment.max_weapon_element_affixes` |
| 組合器 census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | a.3 後 | `cells=204 same=204 different=0`，其餘欄位也相同 |
| 閃現出題 | 交件前 | slow parity（`test_refactor_parity.py`：閃現出題、完整技能、升階）照原夾具通過，見 a.6 |
| 說明文字（`textdump.py`：部位原因 14 種、副手特性 4 種、工坊預設說明、誓約紀錄、看示範上限） | a.3 後 | 只有工坊預設說明少了「沒寫＝5」「沒寫＝4」兩條，其餘相同 |
| 提示詞 | a.3 後 | `tests/llm/test_prompts.py` 雜湊快照、`test_variant_range_lb2b.py` 通過 |
| CLI 快照、parity、前端夾具 | 交件前 | 都沒重產，照原樣通過（a.6）。這段沒有改 API 型別，`openapi.json` 與夾具不變 |

### a.5 筆數（`classify.py`）

| | config | 其中 todo | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|---:|
| 後端 基準 | 181 | 181 | 18 | 9181 | 30 | 452 |
| 後端 a 段交件 | 131 | **121** | 18 | 9223 | **3** | 475 |
| 前端（不動） | 15 | 15 | 0 | 5490 | 23 | 0 |

- 後端 config 依區塊：
  - engine 17 → 0、world 42 → 0；
  - api 81 → 80（`NO_RULES_WALK_MAX_STEPS`）；
  - content 0 → 10（載入層的兩份備用值，config done）；
  - llm 35、server 4、narrative 1、roguelite 1 不動（b 段；narrative、roguelite 各 1 筆規格沒列，見待決 10）。
- 沒歸類 0；`--unused` 沒有輸出。
- 刪掉的規則（搬完 0 筆）：engine 10 條、world 9 條（含 `py-world-no-rules-fallbacks`、`py-world-clock-const-number`）、text 10 條。

### a.6 檢查

`git merge --no-edit main`：Already up to date（main 還在 `7772b2ba9`）。

| 檢查 | 結束碼 |
|---|---|
| `scripts/check.py`（ruff、format、mypy、lint-imports、pytest、前端 install／typecheck／test、situation coverage） | 0（pytest 18222 passed、8 skipped；vitest 4841 passed）；已寫下通過戳記 |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed） |
| `pnpm -C client build`（Bash 裡沒有 pnpm，用 `corepack pnpm`） | 0 |
| `trpg content check` | 0（704 檔、442 技能） |
| `classify.py --check` | 0（沒歸類 0） |

跑完之後沒有改程式；本報告是唯一之後加的檔（只有 `.md`）。

### a.7 複雜度與 noqa

沒有新加 `# noqa`。

### a.8 待 PM 決定（都照最保守的做了）

1. **暴擊「骰數 × 2」改判 const**（a.1）：當成暴擊的定義，沒搬。要可調的話加 `core.crit_dice_multiplier`，結算一處、預覽兩處改讀即可。
2. **`UnitState.ap_per_turn = 3` 改判 const**（a.1）：只給 AP-1 以前的舊狀態 JSON 相容。拿掉預設會讓那些舊存檔讀不進來，所以留著。
3. **遊戲日長度 30 分鐘、遊戲日從 06:00 開始改判 const**（a.2）：時鐘函式拿不到內容庫，改了會重排舊世界的日序與天氣。要搬進 `world/rules.yaml`，得讓 `day_phase` 等十幾個呼叫點帶規則，建議另排。
4. **請求格式上限和規則同值的一處**（a.2）：`InheritAction.records` 的 `max_length=2` 和閃現規則的 `max_carry`（2）同值。工坊把 `max_carry` 調到 3 以上時，請求會先被 pydantic 擋下。現在照 guard 留著；建議 b 段改成較寬的格式上限，或改讀規則。
5. **留 text 的 3 筆**（a.3）：觸發的「max_per_round 只能是 1」（`TriggerSpec`）與道具技能 1 AP（`WorldItemDef`）的檢查拿不到規則包。要搬就得把檢查移到 Ruleset 層或改成跨檔案檢查，錯誤出現的地方會變（同 HC-4d 待決 4）。這是規則類，先問。
6. **新欄位只開了 3 格進工坊**（a.3）：`crit_range_floor`、`opening_status_max_duration`、`defense_break_default_permille`、`boss_parts.high_or_far_distance`、`tower_shield_cover_height`、`skill_slots.rule_change`、`infused_pick`、`newcomer.yaml` 的四格、`elite_cap` 都沒開（規格沒要求，多是規則型上限）。要開再說。
7. **舊戰鬥紀錄的錯誤訊息**（a.1）：新欄位必填，舊紀錄在雜湊比對前就因 pydantic 驗證失敗，訊息是驗證錯誤原文。已排在 b.4，b 段一起處理。
8. **前端的「1 天內」**（`WorldGrowth.tsx` 兩處）沒動：a 段只做後端。建議 b 段前端改由 API 帶冷卻秒數。
9. **範圍外的小改動**：
   - `world_growth_view` 的誓約紀錄沒有誓約表時，用 `OathTable` 的預設秒數組字；
   - `api/world_newcomer_view.py` 的 `_reselect_reminder` 多帶內容庫；
   - 凍結複本 `tests/world/frozen_replay/encounters.json` 補 `elite_cap: 1`（只新增鍵，凍結重播照舊通過）；
   - 前面列的測試因取值方式改變而改寫。
10. **規格沒列的 config 2 筆**：`narrative/storyteller.py` 的重試次數、`roguelite/state.py` 的傳承上限，a、b 兩段都沒寫到。建議併進 b 段（和 llm 的重試設定、a.2 待決 4 的傳承上限一起）。

## 開發 PM 裁定 a 段（2026-11-22）

驗收通過，fast-forward 進 main 並 push（7e954fe98）。check.py 0（pytest 18222、vitest 4841），slow parity＋cli 995，build 0；442 招、78 場、census 204 格 different=0。

1. 暴擊骰數 ×2 改判 const：接受（暴擊的定義）。
2. `UnitState.ap_per_turn = 3` 改判 const：接受（只給舊狀態相容）。
3. 遊戲日 30 分鐘、06:00 改判 const：接受；要搬再另排（記佇列）。
4. `InheritAction.records` 上限：併進 b 段，改讀 `max_carry` 或放寬成格式上限。
5. 留 text 的 3 筆：把檢查移到 Ruleset 層只改錯誤出現的位置、不改規則值（同 HC-4d 裁定 4 的前例），併進 b 段。
6. 新欄位只開 3 格：接受，使用者要調再開。
7. 舊戰鬥紀錄錯誤訊息：b.4。
8. 前端「1 天內」：b 段改由 API 帶冷卻秒數，前端照同一規則組字。
9. 範圍外小改動：接受。
10. storyteller 重試次數、roguelite 傳承上限：併進 b 段。

## b. api、llm、server、前端剩下的 config（併 a 段裁定 4、5、7、8、10，HC-6b 裁定 3、6）

基準：main `88fed5af7`（a 段裁定）。分支 `worktree-agent-a5633a104c78e179f`，沒 push。
數值一律照現值搬，沒試數值、沒跑模擬、沒呼叫真的 LLM。沒動 `docs/design/`、`CLAUDE.md`、計畫檔、`config/`。

### b.0 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| b.1 api（含 api/tuning、server 的留言） | `acef1c102` | 規則數字搬進 content；回應欄位的預設值改必填；工坊工具設定只留一份；請求格式上限、結構數字改判 guard／const |
| a 段裁定 4、10 | `4c143b6b3` | 世界 `InheritAction`、roguelite `InheritChoice` 的 `records` 改成格式上限，帶幾個照規則 `max_carry` |
| b.2 llm（含 narrative 說書人） | `0ea838541` | 重試、提醒線、連線逾時讀 `LLMConfig` 的 schema 預設；挑選模式的時間預算搬進 content |
| b.3 server、前端 | `0fa58b2d1` | 前端的 `?? 30`、晶能對照表拿掉；受擊門檻改判 layout；循環賽人數改判 const |
| a 段裁定 8 | `a2433e825` | `OathView.cooldown_seconds`；前端誓約的「1 天內」照秒數組字 |
| b.4（HC-4c 裁定 1） | `753ff2e09` | 重播、賽程封存讀到驗證失敗的紀錄給中文說明 |
| b.5（HC-6b 裁定 6） | `2c69058d8` | 工坊的階級、AP 選項改由 API 帶（`GameRulesOut.skill_tiers`、`max_ap_cost`） |
| a 段裁定 5＋收尾 | ``6e00b5cb1`` | 留 text 的 3 筆搬進 content、檢查移到上一層；刪 0 筆規則；上手文件 |
| 清單重產 | ``006665703`` | `--md` 重產 `寫死數值-清單.md` |
| check.py 修正 | `cae3d12b6` | `scripts/x10/fields.yaml` 補新欄位；兩個觸發時機測試改查 Ruleset 層 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff check、ruff format --check、mypy、lint-imports、`classify.py --check` 與相關測試（經看門狗）；有前端改動的另跑 tsc 與相關 vitest。

### b.1 api（config 80 → 10，全部 done）

**搬進 content**（新欄位都必填，內容檔寫明現值）：

| 原本 | 搬到 | 值 |
|---|---|---|
| `api/attribute_text.py` 的 `_EARLY_TIER` | `roguelite.yaml` 的 `route_hint_tier` | 2 |
| `api/flash_changes.py` 的 `_SHIELD_DEFAULT_DURATION` | 改讀狀態表的預設回合（同引擎 `_shield`：`spec.status` 或 `shielded` 的 `duration`） | 2 |
| `api/world_pregen.py` 的 `WAIT_SECONDS`、`STORY_WAIT_SECONDS`、`FLASH_LIMIT`、`STORY_LIMIT` | `skill_pick.yaml` 的 `pregen`（`WorldPregen.wait_seconds` 等改成 `None`＝照這一筆的內容庫，測試仍可覆寫） | 10、2、3、2 |
| `api/world_field_people.py` 的 `TOWN_FRIENDS_MAX`；`world_field_things.py` 的 `FOOTPRINT_FRIENDS_MAX`、`PRINTS_MAX` | `world/rules.yaml` 的 `display`（`town_friends`、`footprint_friends`、`footprint_prints`） | 8、3、8 |
| `server/notes.py` 的 `NOTE_MAX_LEN`、`BOARD_NOTES`、`FOOTPRINT_MAX` | `world/rules.yaml` 的 `notes.max_chars`、`display.note_board`、`display.note_footprints`（API 帶進 `trpg.server.notes`） | 50、20、10 |
| `api/world_party_view.py` 的 `REPORTS_SHOWN` | 改讀 `world/mercenaries.yaml` 的 `shadow_reports_kept`（同值，見待決 5） | 20 |
| `api/world_story_schemas.py` 的 `CARE_CITE_MAX` | 改讀 `content/world_situations.py` 的 `MAX_CARE_CLAIMS`（用心清單項數） | 4 |
| `CreateBattleRequest.max_rounds` 的預設 30 | 省略＝`workshop.yaml` 的 `max_rounds`（見待決 6） | 30 |
| `WorkshopRandomRequest.tier` 的 `le=5` | 端點照 `core.skill_limits.tiers` 檢查（422 中文說明） | 5 |
| 工坊分組改的 `_SCALAR_LIMITS`（AP 1～3、冷卻 1～6） | `core.skill_limits.max_ap_cost`、`max_cooldown` | 3、6 |
| 工坊欄位範圍 `max_rows` 1～9、吸血 1～500 | 讀 `PhaseGrowSurface`、`StructureRules` 的 schema 上下限（`field_bounds` 移到 `content/schemas.py` 共用） | 9、500 |
| 工坊欄位範圍 部位抗性 ±1000、`damage_dealt` 1～999 | `±_PERMILLE`、`_PERMILLE − 1`（同 `PartDef`、`StatDownBreak` 的驗證） | — |

- 世界畫面、留言板的 `rules_of(library)` 一律有 `world/rules.yaml`（新加 `display`、`notes`）；凍結複本 `tests/world/frozen_replay/world_rules.json` 只補這兩個鍵（凍結重播照舊通過）。
- **HC-6b 裁定 3（新欄位的預設值）**：`GameRulesOut` 的 HC-6b 欄位、`TuningStatus.draft_name_max`、`TuningSimOptions` 的 `map_default_seeds`／`map_seconds_per_battle`／`ratio_max_work`／`ratio_battles_per_second`、`PartyView.free_slots`、`LocationBoard.max_len` 拿掉預設、改必填（伺服器本來就一律填）。`_world_text_rules` 缺 `world/event_rules.yaml`、循環賽、`world/enemies.yaml` 時改成報錯（原本照欄位預設）；跑過 api 全部測試沒有碰到。
- **工坊工具設定只留一份**（規格 b.1）：預設種子、模擬場數與工作量上限、樣本小門檻、地圖數上限集中在 `api/tuning/schemas.py`（`SIM_DEFAULT_SEEDS`、`MAP_DEFAULT_SEEDS`、`MAX_SIM_MAPS`、`MAX_SIM_BATTLES`、`RATIO_DEFAULT_SEEDS`、`RATIO_MAX_WORK`、`SMALL_SAMPLE`、`MAX_RATIO_SEEDS`），`service.py`、`ratios.py`、`sim_jobs.py` 的舊名字改成指向它（照舊匯出）；`DRAFT_NAME_MAX`、`MAX_GROUP` 本來就只有一份。規則 `py-api-tuning-tool-settings`（config done）：工具本身的設定，不是遊戲規則，不進 content（見待決 3）。
- **改判 guard**（`py-api-request-format-guards`、`py-api-world-pregen-queue-guard`）：手動組物品的詞條 8（＝`EquipmentRules.max_affixes_per_item` 的 le；規則值 4）、單場戰鬥輪數 200、工坊請求的清單長度、全服預先生成暫存區 12。靶場看示範的關鍵字請求 2 → 4（同開局選關鍵字的格式上限，規則 `range.trial_keywords_max` 2 照舊由試打檢查；見待決 7）。
- **改判 const**（`py-api-structure-const-number`）：等待的輪詢間隔 0.05 秒、工坊欄位路徑段數、「2 AP 條件型」預設組本身、四捨五入的 ×2、「2 級＝第一次升級」。工坊的「遠程」（射程 2 格以上）清單與分組改共用 `skill_ranged` 一份。

### a 段裁定 4、10（傳承上限）

- `InheritAction.records`、`InheritChoice.records` 的 `max_length=2` 改成 `INHERIT_RECORDS_FORMAT_MAX`（`content/flash_templates.py`：`major_flash` 的 schema 上限 9 − 1 ＝ 8）。帶幾個照規則 `max_carry`（`major_flash − 1`，現值 2），由 `roguelite.flashes` 的傳承檢查擋下並說明「最多帶走 2 個小變化」。
- 工坊把 `major_flash` 調高時，請求不會先被 pydantic 擋下。`openapi.json` 兩處 `maxItems` 2 → 8。
- 新測試 `tests/roguelite/test_inherit_records_hc7b.py`。

### b.2 llm（config 35 → 8，全部 done；narrative 1 → 0）

- **部署設定讀 `LLMConfig` 的 schema 預設**：`llm/config.py` 加 `LLM_DEFAULTS = LLMConfig()`（唯一一份預設）。
  - 重試次數 3：`DEFAULT_FLASH_ATTEMPTS`、`DEFAULT_PICK_ATTEMPTS`、`DEFAULT_MAX_ATTEMPTS`、`DEFAULT_STORY_ATTEMPTS`（劇情技能）、`DEFAULT_WISH_ATTEMPTS` 與各函式的 `max_attempts=3` → `LLM_DEFAULTS.max_retries`。伺服器、命令列本來就傳 `config.max_retries`。
  - 退回率提醒 200‰（`llm_source`、`flash_eval`、`flash_propose`、`propose`）→ `LLM_DEFAULTS.fallback_alert_permille`。
- **`LLMConfig` 新加的鍵**（`config/llm.toml` 沒加、既有值沒改；預設等於原本程式裡的值）：

| 鍵 | 預設 | 原本 | 怎麼生效 |
|---|---|---|---|
| `probe_timeout_s` | 3.0 | `api/llm_source.DEFAULT_PROBE_TIMEOUT_S` | `LocalLlmProvider` 建構時沒給逾時就讀設定檔的值 |
| `situation_attempts` | 2 | `llm/situation.DEFAULT_SITUATION_ATTEMPTS` | `propose_situation` 沒給 `attempts` 時讀 client 帶的設定（`client_config`；Mock 用預設） |
| `story_attempts` | 2 | `narrative/storyteller.DEFAULT_STORY_ATTEMPTS`（a 段待決 10） | `tell_story` 同上 |

- **遊戲規則搬進 content**：挑選模式等本機模型的時間預算 `skill_pick.yaml` 的 `budget_seconds`（`flash`、`offer`、`wish` 各 10 秒；原本 `FLASH_PICK_BUDGET_S`、`OFFER_BUDGET_S`、`WISH_PICK_BUDGET_S`）。`budget_s` 省略＝讀內容。
- 許願對關鍵字的上限 `max_keywords=2` 預設改讀 `world/rules.yaml` 的 `wish.max_keywords`（`wish_max_keywords`）。
- 提示詞的名稱、描述字數改用 `skillgen/flash_text.py` 那一份（同值 12、40；兩邊原本各寫一份）。`MAX_SCHEMA_BRANCHES`、`WISH_REPLY_MAX_CHARS`、Mock 的挑選序 `(0, 1, 2)` 改判 const（同 `flash_text` 的前例，`py-llm-format-const-number`）。
- 規則 `py-llm-config-config-number` 改成 config done（`config/llm.toml` 的 schema 預設）。
- 新測試 `tests/llm/test_llm_defaults_hc7b.py`。

### b.3 server、前端（server config 4 → 0；前端 config 15 → 0）

- server：留言 3 筆見 b.1；`league.MIN_ENTRIES`（2）改判 const（循環賽至少要 2 人才有對手，`py-server-league-const-number`）。
- 前端：
  - `GearScreen.tsx`、`workshop/tryout.ts` 的 `max_rounds: arena?.max_rounds ?? 30` → 沒有靶場設定時不送，伺服器照 `workshop.yaml`（b.1）。
  - `ui/statusCard.ts` 的 `CRYSTAL_SURGE_TIER` 對照表 → `CRYSTAL_SURGE_RE` 照 ID 樣式（`crystal_surge`＝1、`crystal_surge_<階>`；同元素架勢的做法）。
  - `battle/impact.ts` 的 `TIER_PERMILLE`、`battle/vfx.ts` 的 `HEAVY_HIT_PERMILLE` 改判 layout（原規則 note「呈現用的門檻，PM 可改判 layout」；只決定頓格與震動）。
  - 工坊的階級、AP 8 筆見 b.5。

### a 段裁定 8（前端的「1 天內」）

- `OathView` 多 `cooldown_seconds`（`world/oaths.yaml` 的 `cooldown_seconds`；沒有誓約表時用 `OathTable` 的預設，同誓約紀錄的說明）。
- `WorldGrowth.tsx` 兩處改成 `durationText(oath.cooldown_seconds)`（`ui/rulesText.ts` 新函式，整天「N 天」、不整天「N 小時」四捨五入，同後端 `cooldown_zh`；`aboutDurationText` 改成「約 」＋它）。**目前 86400 秒組出來和改前逐字相同**（`ui/hc7bDurationText.test.ts`）。

### b.4 重播與賽程封存的驗證錯誤（HC-4c 裁定 1、a 段裁定 7）

- `engine/runner.py` 新函式 `log_invalid_problem(error)`：「紀錄的內容和目前的資料格式對不上（N 處）：紀錄被修改過，或規則資料的結構在紀錄之後改變，無法確定重播結果一致」——和「雜湊不符」同一類，不帶驗證錯誤原文。
- 用在三處：`trpg battle replay`、循環賽的 `LeagueStore.log`（重播端點，409）、賽季封存檢查 `_replay_problems`。
- 測試 `tests/server/test_log_invalid_hc7b.py`：用一份「舊格式」紀錄（紀錄版號相同，內嵌規則包少了 a 段新增的必填 `core.crit_range_floor`），三處都給中文說明、不含 `Field required` 等原文。

### b.5 工坊的階級與 AP 選項（HC-6b 裁定 6）

- `GameRulesOut` 多 `skill_tiers`（`core.skill_limits.tiers`，5）、`max_ap_cost`（`skill_limits.max_ap_cost`，3）。
- 數值工坊篩選列 `tuning/skillModel.ts` 的 `FILTER_ROWS` 改成 `filterRows(rules = gameRules())`：階級 1～`skill_tiers`、AP 1～`max_ap_cost`。技能工坊「隨機一個」的階級選單 1～`skill_tiers`（`ToolPanels.tsx`）。
- **階級讀哪個上限**：照裁定讀 `skill_limits.tiers`。隨機一個本來就是 1～5，字不變；**數值工坊的篩選列原本只有 1～3 階，現在多了「4 階」「5 階」兩顆**（見待決 1）。AP 1～3 不變。
- 截圖（建置後的前端＋`trpg serve --port 8123`，存檔放 scratch、`TRPG_TUNING=1`）：`C:\Users\tobby\AppData\Local\Temp\claude\9f1b79de9b6f77a5\9d8cd6cd-f0cd-4696-a663-73ef271d469e\scratchpad\hc7b_tuning_filter.jpg`（篩選列階級 1～5、AP 1～3）。

### a 段裁定 5（留 text 的 3 筆，text 3 → 0）

照 HC-4d 裁定 4 的前例：規則值不變，只改錯誤出現的地方。

| 原本 | 搬到 | 檢查移到 |
|---|---|---|
| `TriggerSpec` 的 `on_ap_spent_all`、`on_keyword_exploited`「max_per_round 只能是 1」 | `skill_triggers.yaml` 兩個時機的 `max_per_round: 1`（`SkillTriggerDef.max_per_round`，沒寫＝不限） | Ruleset 層的 `_trigger_problems`（技能檢查，載入內容庫或 `validate_skill` 時） |
| `WorldItemDef` 的「道具技能必須是主動、1 AP（8.17）」 | `world/items.yaml` 的 `item_skill_ap_cost: 1` | 物品表 `WorldItemTable`（整張表的驗證） |

- 說明照內容組字，現值組出來和改前逐字相同。物品那一句不再和同一件物品的其他問題（標籤、使用次數）併成一句。
- 閃現的「每回合觸發次數 +1」（`_op_trigger_cap`）碰到這兩個時機：原本在建草稿時被擋、現在由 `validate_skill` 擋，兩者都讓那個變化不出現（逐招預算、閃現 parity 不變）。
- 新測試 `tests/content/test_text_rules_hc7b.py`。

### b.6 API 新欄位與夾具

| 型別 | 欄位 | 變動 |
|---|---|---|
| `GameRulesOut` | `skill_tiers`、`max_ap_cost` | 新增 |
| `GameRulesOut` | HC-6b 的 21 個欄位 | 拿掉預設、必填 |
| `OathView` | `cooldown_seconds` | 新增 |
| `LocationBoard` | `max_len` | 拿掉預設 50、必填 |
| `PartyView` | `free_slots` | 拿掉預設 2、必填 |
| `TuningStatus` | `draft_name_max` | 拿掉預設、必填 |
| `TuningSimOptions` | `map_default_seeds`、`map_seconds_per_battle`、`ratio_max_work`、`ratio_battles_per_second` | 拿掉預設、必填 |
| `CreateBattleRequest` | `max_rounds` | `int`（預設 30）→ `int \| null`（省略＝`workshop.yaml`） |
| `WorkshopRandomRequest` | `tier` | 拿掉 `maximum: 5`（端點檢查） |
| `RangeTrialRequest` | `keywords` | `maxItems` 2 → 4 |
| `InheritAction`、`InheritChoice` | `records` | `maxItems` 2 → 8 |

- 前端夾具只有 `client/src/battle/fixtures/glossary.json` 的 `rules` 多兩鍵：`skill_tiers: 5`、`max_ap_cost: 3`。其餘夾具（`unitDolls`、`raceLooks`、`skillCards`）重產後不變。
- `openapi.json`、`schema.d.ts` 照上表重產。前端測試裡手寫的 `OathView` 物件補 `cooldown_seconds: 86400`（`growth.test.ts`、`pnl2Growth.test.ts`、`fl1cFlashNone.test.ts`、開發頁 `dev/panelGallery.tsx`）。

### b.7 玩家（與開發者）看到的字

| 位置 | 改前 | 改後 |
|---|---|---|
| 數值工坊篩選列「階級」 | 1 階、2 階、3 階 | 1 階～5 階（多 4、5 階；b.5，待決 1） |
| `trpg battle replay` 讀到驗證失敗的紀錄 | 「不是有效的戰鬥紀錄：」＋換行＋pydantic 原文 | 「不是有效的戰鬥紀錄：紀錄的內容和目前的資料格式對不上（N 處）：…無法確定重播結果一致」 |
| 循環賽重播讀到驗證失敗的紀錄 | 未攔截的驗證錯誤（500） | 409「這一場不能重播：紀錄的內容和目前的資料格式對不上（N 處）：…」 |
| 賽季封存檢查 | 「戰鬥紀錄的內容不合法：N 個錯誤」 | 同上一句的說明 |
| 技能工坊「隨機一個」送 6 階以上 | pydantic 422 | 422「技能階級只有 1～5（這次 N）」 |
| 靶場看示範送 3～4 個關鍵字 | pydantic 422 | 試打檢查「看示範最多 2 個不同的關鍵字」 |
| 傳承送 3～8 個變化 | pydantic 422 | 傳承檢查「最多帶走 2 個小變化」 |
| 誓約「解除後現實 1 天內…」兩處 | 前端寫死 | 照 `cooldown_seconds` 組字，現值逐字相同 |
| 內容檢查：觸發時機每輪次數、道具技能 AP | 讀檔時的 ValidationError | 字相同；觸發時機改在內容庫的技能檢查報、道具 AP 改在物品表報 |

其餘畫面文字不變：CLI 快照、parity、前端夾具（除上面兩鍵）照原樣通過。

### b.8 LOG_FORMAT／PROMPT_VERSION 判斷

- **LOG_FORMAT 不升**（`docs/phases/戰鬥紀錄格式變更.md` 1.2）：事件、動作、狀態的欄位沒有增減，結算不變（78 場、51 場都 different=0）。規則包多了 `skill_triggers[*].max_per_round`，`ruleset_hash` 會變，舊紀錄照 1.2 被拒；讀不進的舊紀錄現在給 b.4 的中文說明。
- **PROMPT_VERSION 不升**：提示詞的文字與 schema 沒變（字數上限改讀 `flash_text` 同值；`tests/llm/test_prompts.py` 雜湊快照通過）。
- `WORLD_RULES_VERSION` 不升：`world/rules.yaml` 多的 `display`、`notes` 只管畫面筆數與留言字數，世界推進的規則沒變（內容 digest 本來就會變）。

### b.9 比對（基準 `git archive 88fed5af7 src content scripts tests config`）

腳本放在 scratch，沒進 repo：`hc7b_dump.py`（逐招 `BudgetReport` repr＋`validate_skill` 違規；每張有預設陣容的地圖 × 種子 1～3 的戰鬥，事件 JSON＋最終狀態）、`hc7b_cmp.py`。基準執行時確認載入的 `trpg` 來自基準那份。

| 比對 | 結果 |
|---|---|
| 逐招預算 442 招 | `same=442 different=0` |
| 78 場戰鬥（a 段同一組：`compare78.py`，15 張圖 × 種子 1、7＋開闊平原 8 個 build＋4 張頭目圖 × 種子 3～12；去掉 `ruleset_hash` 與內嵌規則包，加文字輸出；開發 PM 驗收前補跑） | `battles=78 events=26206 different=0`；內嵌規則包只差新欄位 `skill_triggers[*].max_per_round`（兩個時機 1、其餘 `None`） |
| 戰鬥（自己的組：17 張地圖 × 3 種子） | `battles=51 different=0` |
| 組合器 census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | `cells=204 same=204 different=0`（不看耗時欄位 `timing`） |
| 閃現出題、完整技能、升階 | slow parity（`test_refactor_parity.py`）照原夾具通過，見 b.11 |
| 提示詞 | `tests/llm/test_prompts.py` 雜湊快照通過 |
| 說明文字 | 名詞表 `rules` 除新兩鍵外相同（夾具對照）；誓約冷卻、線頭到期組字相同（vitest）；CLI 快照不變 |

### b.10 筆數（`classify.py`）

| | config | 其中 todo | scale | const | text | layout | guard |
|---|---:|---:|---:|---:|---:|---:|---:|
| 後端 b 段開工 | 131 | 121 | 18 | 9223 | 3 | 0 | 475 |
| 後端 b 段交件 | 28 | **0** | 18 | 9280 | **0** | 0 | 486 |
| 前端 b 段開工 | 15 | 15 | 0 | 5490 | 23 | 54759 | 0 |
| 前端 b 段交件 | **0** | 0 | 0 | 5491 | 22 | 54763 | 0 |

- 後端剩下的 config 都是 done：content 載入層的兩份備用值 10（a 段）、`LLMConfig` 的 schema 預設 8、數值工坊工具設定 10。
- 前端 text 23 → 22：`WorldGrowth.tsx` 確認解除那句改成組字後沒有數字了；說明那句的「1 天」也改成組字，但還有「同時 1 個」（誓約欄位數，不在這段範圍），照舊留 text（見待決 11）。
- 沒歸類 0；`--unused` 沒有輸出。
- 規則：刪掉 43 條（搬完或改判後 0 筆：api 21、llm 13、narrative 1、roguelite 1、server 2、text 2、前端 3）；新加 6 條改判用的（`py-api-tuning-tool-settings`、`py-api-request-format-guards`、`py-api-world-pregen-queue-guard`、`py-api-structure-const-number`、`py-llm-format-const-number`、`py-server-league-const-number`）。

### b.11 檢查

`git merge --no-edit main`：Already up to date（main 還在 `88fed5af7`）。

| 檢查 | 結束碼 |
|---|---|
| `scripts/check.py`（第一次） | 1：4 個失敗——`test_x10_fields`、`test_x10_rescale`（`scripts/x10/fields.yaml` 沒列新欄位）、`test_ap_content_ap2`、`test_keyword_exploited_sk3`（還在等 `TriggerSpec` 的 ValidationError）。修正在 `cae3d12b6`（清單補 `route_hint_tier`、`triggers[].max_per_round`、`display.*`、`notes.*`、`item_skill_ap_cost` 為 keep；兩個測試改查 Ruleset 層的訊息） |
| `scripts/check.py`（修正後重跑） | 0（pytest 18234 passed、8 skipped；vitest 4845 passed；ruff、format、mypy、lint-imports、前端 install／typecheck、situation coverage 都通過）；已寫下通過戳記 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed） |
| `corepack pnpm -C client build` | 0 |
| `trpg content check` | 0（704 檔、442 技能） |
| `classify.py --check` | 0（沒歸類 0；`--unused` 沒有輸出） |

跑完之後沒有改程式；本報告是唯一之後加的檔（只有 `.md`）。截圖用的 `trpg serve --port 8123`、瀏覽器分頁都已關掉。

### b.12 複雜度與 noqa

沒有新加 `# noqa`（拿掉兩個 `PLR2004`：工坊的「遠程」判斷合成一處）。

### b.13 待 PM 決定（都照最保守的做了）

1. **數值工坊篩選列多了 4、5 階**（b.5）：照 HC-6b 裁定 6 讀 `skill_limits.tiers`（5）。原本只有 1～3 階；要維持 3 階得另加一個「工坊篩選顯示到幾階」的鍵。
2. **情境判定、說書人的重試次數只對真的本機模型生效**（b.2）：`situation_attempts`、`story_attempts` 經 client 帶的設定讀（`OpenAICompatClient.config`）。`config/llm.toml` 沒加這兩鍵，寫了才會改。
3. **數值工坊的工具設定留在 `api/tuning/schemas.py`**（b.1）：預設種子、場數上限等判成工具設定（config done），沒進 content。
4. **畫面筆數放進 `world/rules.yaml` 的 `display`**（b.1）：城鎮站幾位朋友、腳印、留言板幾則、足跡幾筆。也可以判成 layout 留在程式。
5. **影子戰報顯示幾則改讀 `shadow_reports_kept`**（b.1）：同值 20；調高留存則數時顯示也跟著多。
6. **單場戰鬥省略輪數時讀 `workshop.yaml` 的 `max_rounds`**（b.1）：同值 30，也套到開發用的 `hero_build` 單場。
7. **請求格式放寬後，錯誤由規則說明**（b.1、裁定 4）：靶場看示範 2 → 4、傳承 2 → 8；超過規則的請求改成中文的規則錯誤（原本是 pydantic 422）。
8. **留言存檔不再擋字數**（b.1）：`LocationNote.text` 拿掉 `max_length`，寫入時照 `notes.max_chars` 檢查；規則調低時舊留言照讀。
9. **錯誤出現的地方改了**（裁定 5）：觸發時機每輪次數改在內容庫的技能檢查報；道具技能 AP 改在物品表報，不再和同件物品的其他問題併成一句。
10. **commit 的切法**：server 的留言和 API 共用參數，放在 b.1；b.3 之後 `tests/test_hardcoded_scan.py` 的前端抽查（受擊門檻改 layout、木樁 `?? 30` 拿掉）到 b.5 的 commit 才跟上，b.3 單獨跑那兩個抽查會失敗。
11. **前端留 text 的 22 筆**：規格沒列（HC-6c 另排的介面項目之外）；例如誓約說明的「同時 1 個」可改讀 `slot_zh`，這段沒動。

## 開發 PM 裁定 b 段（2026-11-22）

驗收通過，已 push（53b7c987f）。check.py 0（pytest 18234、vitest 4845），slow parity＋cli 995，build 0；442 招、78 場（events 26206）、51 場、census 204 格 different=0。後端 config todo 121→0、text 3→0；前端 config 15→0。工坊篩選列截圖已看。

1. 工坊篩選列階級 1～5：接受（照 `skill_limits.tiers`，技能本來就有 4、5 階）。
2. 情境判定與說書人重試次數從 client 設定讀：接受。
3. 工坊工具設定只留 `api/tuning/schemas.py`：接受。
4. 畫面列幾筆放 `world/rules.yaml` 的 `display`：接受。
5. 影子戰報顯示改讀 `shadow_reports_kept`：接受。
6. 單場省略輪數讀 `workshop.yaml` max_rounds：接受。
7. 格式上限放寬、超過規則改給中文規則錯誤：接受。
8. 留言只在寫入時照 `notes.max_chars` 檢查：接受。
9. 兩個檢查的錯誤位置改變、字照舊：接受（同 HC-4d 裁定 4）。
10. b.3 單獨跑有 2 個抽查失敗、b.5 才跟上：接受（合併後是 0）。
11. 前端剩 22 筆 text：併進 HC-6c。
