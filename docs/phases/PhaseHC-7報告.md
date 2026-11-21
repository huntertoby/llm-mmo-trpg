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
