# 上手：roguelite 開局與入門期（`src/trpg/roguelite/`、`src/trpg/world/`、`src/trpg/api/`）

> 給實作 agent：派工 prompt 指到這份時，讀完就能動手改開局、選大類、葛蘭的正式選定、入門期限制、重選、提示旗標、靶場試打。
> 2026-11-12 整理（同日 PR-2a 更新第一、二、四、五節），依據當時的 main：`WORLD_RULES_VERSION` 25、`CHAR_FORMAT` `trpg-char/13`、`WLOG_FORMAT` `trpg-wlog/9`、`SAVE_FORMAT` `trpg-run/13`、`LOG_FORMAT` `trpg-battle-log/113`。
> 設計的真相來源：`docs/design/21-探索地圖與城鎮.md` 21.5（開局、工坊靶場、測試模式）、`docs/design/06-技能.md` 6.27.3（起始技能）。這份只寫程式在哪、怎麼接。
> 改到這一塊時順手更新這份。

## 一、這一塊在哪些檔

| 檔案 | 職責 |
|---|---|
| `src/trpg/world/opening.py` | 開局的主檔：`new_opening(seed)`、開局閘門 `opening_gate`（各階段能做的動作）、畫面用的 `opening_limits(char)`、選大類 `apply_opening_class`、舊的一次選定 `apply_opening_confirm`、推薦關鍵字 `recommended_keywords`、靶場內容 `range_content`、沙盒試打 `range_trial`／`trial_seed`、`mentor_town`；PR-2a 起：測試模式的設定 `_practice_setup`、工坊師傅的「靶場試玩」`own_practice`／`practice_seed`、能不能開 `practice_problem`（原因句 `PRACTICE_*_ZH`） |
| `src/trpg/world/opening_choice.py` | 正式選定（OB-2）：`choice_problem`、`place_ok`／`place_problem`、`starter_steps_done`、`apply_formal_choice`，以及依階段分流的 `apply_opening_confirm` |
| `src/trpg/world/opening_reselect.py` | 4 級前的免費重選（OB-3）：`reselect_problem`（OB-6 起先呼叫 `reselect_window_problem`＝只看資格：已選定、等級、沒用過）、`apply_reselect`、`reselect_losses`／`reselect_returns`、`starter_item_id`（OB-6 抽出 `weapon_item_id`）；開局結束 `close_opening` |
| `src/trpg/world/opening_limits.py` | 入門期的戰鬥閘與活動限制（OB-4）：`in_starter_period`、`STARTER_STEPS`、`spawn_hidden`、`fight_problem`、`solution_problem`、`spot_problem`、`holds_step`、`stuck_conditions`；被擋的原因文字 `FIGHT_ZH`、`FLASH_ZH`、`SOLUTION_ZH`、`OBJECT_ZH` |
| `src/trpg/world/state.py` | `CharacterState`（含 `opening: OpeningState \| None`、`hints_seen`、`hints_off`、`level_seen`）、`OpeningState`、`CHAR_FORMAT`、`LEGACY_CHAR_FORMATS` |
| `src/trpg/world/actions.py` | 世界動作與事件的型別：`OpeningClassAction`、`OpeningConfirmAction`、`OpeningReselectAction`、`HintSeenAction`、`HintsOffAction`、`HintsResetAction`、`UI_NOTE_ACTIONS`；事件 `OpeningClassChosenEvent`、`OpeningConfirmedEvent`、`OpeningReselectedEvent` |
| `src/trpg/world/step.py` | `world_step(library, world, char, action, now)`：純函式入口；分派表 `HANDLERS`；`new_character`；提示旗標常數 `LESSON_ALLOCATE`、`LESSON_ALLOCATE_SKIP`、`LESSON_ALLOCATE_LEFT`、`LESSON_ALLOCATE_AGAIN` |
| `src/trpg/world/growth.py` | 升級與成長；`OPENING_END_LEVEL`（4）；入門期升級自動配點（`gain_xp`）；4 級前不能閃現的判斷在這裡 |
| `src/trpg/world/quests.py` | 任務推進；延後的三選一 `issue_deferred_offers`、`_note_granted`（把三選一拿到的招記進 `opening.granted_skills`） |
| `src/trpg/world/save.py` | 存檔格式與版號：`WORLD_RULES_VERSION`（每一版改了什麼寫在常數下面的說明）、`WLOG_FORMAT`、`dumps_char`／`loads_char`、`content_digest`、`log_rules_key` |
| `src/trpg/world/battle.py` | `prepare_battle(library, char)` 組出戰鬥設定；`fight` 把打完的步驟回寫世界；主角出場函式 `hero_spawn`（PR-2a 起公開，靶場試玩共用） |
| `src/trpg/roguelite/start.py` | 起始配備的共用函式：`new_keyword_run`（武器＋關鍵字 → 起始 2 招）、`starter_pools`、`starting_skill`、`start_hero`、`recommended_allocation`、`recommended_level_up`、`start_weapons` |
| `src/trpg/roguelite/save.py` | 一輪存檔 `SAVE_FORMAT`、`COMPATIBLE_FORMATS`、`ruleset_hash(library)` |
| `src/trpg/api/world.py` | `WorldStore`：鎖、日誌、存檔、`act`、`sync`、`create`；PR-2a：一角色一場試打 `close_trial`／`track_trial`（`_trials` 只在記憶體） |
| `src/trpg/api/sessions.py` | 戰鬥工作階段表 `SessionStore`；PR-2a 加 `discard(battle_id)`（不存在不報錯） |
| `src/trpg/api/routes/world.py` | 端點（前綴 `/api/world`）：`POST /characters`、`GET /characters/{id}`、`POST /characters/{id}/actions`、`POST /characters/{id}/range/trial`、`GET /characters/{id}/range/recommend`、`POST /characters/{id}/battle`；PR-2a：`POST /characters/{id}/range/practice`（靶場試玩，無 body）、`DELETE /characters/{id}/range/trial`（刪掉該角色目前的試打，沒有也 204） |
| `src/trpg/api/world_range.py`、`world_range_schemas.py` | 靶場與選定畫面的資料：`range_view`（→ `WorldView.opening`）、`range_recommend`、`open_range_trial`；`RangeView`、`RangeChoiceView`、`RangeReselectView`；PR-2a：`open_range_practice`、`close_range_trial`、`workshop_view`（→ `WorldView.workshop`，`WorkshopView`）、標題前半 `PRACTICE_TITLE_ZH` |
| `src/trpg/api/world_newcomer_view.py` | 新手引導畫面資料：`guide_view`、`lesson_view`（`LessonView.kind` 含 `choose`）、`level_up_view`、`battle_hints`、`hints_view`、`lesson_seen`；提示旗標 ID 常數 `OPENING_SEEN`、`LESSON_SEEN_PREFIX`、`PRACTICE_SEEN` |
| `src/trpg/api/world_schemas.py` | `WorldView`（`opening`、`limits`、`workshop` 等欄位） |
| `src/trpg/api/world_dev.py` | 開發用入口（Boss 戰排演、傳送），要 `TRPG_DEV_ROUTES=1` |
| `src/trpg/api/tuning/` | 數值工坊（NW-1a，前綴 `/api/tuning`）：`dev_mode` 且 `TRPG_TUNING=1` 才掛，帶轉發標頭 403；細節在 `上手-內容資料與模擬.md` 第七節 |
| `src/trpg/server/season_policy.py` | 季末重置時每個存檔欄位怎麼處理的表（新加存檔欄位必須登記） |
| `content/world/newcomer.yaml` | 新手內容：`mentor_npc`、各段台詞、`range:`（`racks`、`placeholder_weapon`、`map`、`dummies`、`demos`、`starters`、`keeper_object`、`choose*`、PR-2a 的工坊師傅選單 `workshop`；`max_rounds` 測試模式不用）；schema 在 `src/trpg/content/world_newcomer.py`（`WorkshopContent`） |
| `content/world/fields/capital/capital.yaml` | 主城實地地圖；`workshop_master` 的 `panel: workshop`（PR-2a，`ObjectPanel` 多了 `workshop`）、`training_range` 的說明卡 |
| `src/trpg/api/opening_gear_note.py` | 卡片多寫的一行（OB-6）：入門期的入門武器「借的、不能賣寄分解」、還能重選時的起始武器「重選會收回」；`HeroGearSlotOut.opening_note_zh`、`BagItemView.opening_note_zh` |
| `client/src/world/range.ts`、`RangeScreen.tsx`、`RangeClassPick.tsx`、`RangeParts.tsx` | 前端的選大類、正式選定與重選畫面；`rangeMode()` 回 `class`／`choose`／`reselect`；重選的確認彈窗 `ReselectConfirmDialog`、小牌 `reselectBadge` |
| `client/src/world/ReselectEntry.tsx` | 葛蘭面板、主城靶場面板上方的「重選」鈕（`opensReselect`）；配點收尾彈窗的兩段 `allocateClosingLines` |

## 二、資料怎麼流

**角色的開局階段**（`OpeningState.stage`）

```
建角（opening = new_opening(seed)，stage=pick_class，拿佔位武器、沒有技能）
  └─ opening_class {weapon_class}      → stage=starter（入門武器＋入門招，開局 4 點自動配）
       └─ 打完新手任務前 2 步、回葛蘭所在的城鎮或主城
            └─ opening_confirm {weapon, keywords} → stage=chosen（正式選定）
                 ├─ opening_reselect {weapon, keywords}（4 級前一次；reselect_used）
                 └─ 升到 OPENING_END_LEVEL（4）且延後的三選一都選完 → close_opening：opening = None
```

`opening is None` 的角色（舊角色、已結束開局）不受這一塊任何判斷影響。「入門期」＝`in_starter_period(char)`：`opening` 不是 `None` 而且 `stage` 不是 `chosen`（`pick_class` 也算）。

**一個世界動作**

1. 前端 `POST /api/world/characters/{id}/actions`（body 是 `WorldActionRequest`，`kind` 分辨）。
2. `routes/world.py::post_action` → `world_flow.act_with_story` → `WorldStore.act` → `WorldStore._apply`：取 `now`、在世界的鎖內呼叫 `world_step`。
3. `world_step` 開頭先 `opening_gate(library, world, char, action)`：照 `_STAGE_RULES[stage]` 的規則逐條檢查，被擋就拋 `WorldActionError`（原因是中文，直接顯示給玩家）。`pick_class` 是白名單 `_PICK_CLASS_ALLOWED`、`starter` 是黑名單 `_STARTER_BLOCKED` 加幾條細則（主手、只限防具、`_fight_rule`）。
4. 過了閘門再檢查待選的閃現與三選一，然後從 `HANDLERS` 找處理函式；開局的三個動作分別進 `apply_opening_class`、`opening_choice.apply_opening_confirm`、`opening_reselect.apply_reselect`。
5. 動作之後 `advance_quests` 推進任務（入門期給招的步驟被 `holds_step` 留住）、整理裝備來歷。
6. `_apply` 把成功的動作取 `seq` 寫進日誌（`log.jsonl`，append），再寫角色與世界快照；回 `WorldView`。

**正式選定與重選的內部順序**：兩個檔的檔頭各有逐步清單，理由在 `docs/phases/PhaseOB-2報告.md` 第 2 節、`PhaseOB-3報告.md` 第 4 節。共同點：全部檢查完才動狀態；起始 2 招用 `opening.seed` 經 `new_keyword_run` 取（和靶場預覽同一套，預覽看到的就是拿到的）；先收回舊招再給新招；屬性點全數照推薦配法寫進 `attribute_spent`；最後才出延後的三選一（一次一組，選完才出下一組）。

**畫面資料**

- `GET /api/world/characters/{id}` → `WorldView`。`opening`（`RangeView`）在 `opening` 還沒結束時才有；`RangeView.choice` 只在 `starter`、`RangeView` 的重選資料只在 `chosen`。
- `WorldView.limits`：系統 → 原因，來自 `opening.opening_limits(char)`，和閘門用同一張表，所以畫面寫的原因和送出被拒的句子一致。
- 可以正式選定時 `lesson_view` 回 `kind="choose"`，前端自動開整頁；這個教學不記「看過」，選定前每次到都會出。
- 推薦關鍵字：`GET …/range/recommend?weapon=<id>`（唯讀、不寫日誌；不能選定也不能重選時 422）。
- 武器清單與關鍵字預覽沿用一輪的 `GET /api/runs/start-options`、`POST /api/runs/start-preview`，帶 `RangeView` 給的 `seed`。
- **重選（OB-6）**：`RangeView.reselect`（`stage == chosen` 才有）除了 OB-3 的 `available`／`blocked_zh`／`returned_zh`／`weapon_returned`／`lost_zh`，多了 `window_open`（＝`reselect_window_problem is None`，任務欄「{before_level} 級前可重選一次」小牌照它顯示，不管人在哪）、`place_zh`（去哪裡重選，和不在那裡被拒同一句）、`in_capital`、`here_zh`（標題牌的地方）、`speaker`／`lines`／`done`（葛蘭或守印人；台詞在 `newcomer.yaml` 的 `range.reselect*`）、`npc`／`objects`（面板入口）。重選頁**不自動開**：只由葛蘭面板、主城靶場面板的「重選」鈕與頂列的鈕打開（`WorldScreen` 的 `reselectOpen`）；按確定先開確認彈窗；完成後先出 `done` 的彈窗，按「好」才開三選一（同正式選定的 `holdOffer`）。
- `LessonView.reselect_reminder`（OB-6 Q2）：正式選定後配點教學（`respec`）收尾彈窗的第二段，還有重選資格時才有。
- `GrowthView.starter_note_zh`：入門期接在服務說明後面的那一句。

**靶場試打（沙盒）**：`POST …/range/trial` → `open_range_trial` → `opening.range_trial` 在記憶體組一場（靶場地圖、木樁、主角拿選的武器＋示範招或關鍵字起始招），開在戰鬥工作階段表但**不登記成角色的戰鬥**，所以打完不回寫：不寫日誌、不改角色、不給經驗掉落。之後的操作走一般的 `/api/battles`。

**靶場試玩（PR-2a）**：主城工坊師傅那裡用角色**自己的技能與裝備**打木樁。`POST …/range/practice` → `open_range_practice`：先問 `opening.practice_problem(library, char, in_battle=…)`（不在主城 → 還在選大類 → 戰鬥中或有遭遇 → 有待選的閃現或三選一；有原因就 422，字＝原因），再 `opening.own_practice` 組設定：主角用 `world.battle.hero_spawn`（技能列含生成技能與武器混用規則、裝備＝`hero_loadout` 含共鳴），HP、法力、耐力給滿（`None`），不帶腰包道具、誓約、`next_battle` 狀態，隊友不上場；種子 `practice_seed(角色 ID)`；標題「靶場試玩：{武器}」。和開局試打一樣是沙盒。

**一角色一場**：`WorldStore._trials` 記「角色 → 目前的試打 battle_id」（只在記憶體）。`range/trial`、`range/practice` 開新場前先 `close_trial`（`SessionStore.discard` 舊場），開完 `track_trial`；`DELETE …/range/trial` 刪掉目前那場（沒有也 204）。前端離開靶場時要呼叫 DELETE（PR-2b 做）。擁有者檢查靠 `/api/world` 路由既有的 `require_world_access`（別人的角色 404）與戰鬥的 `owner`。

**工坊師傅選單（`WorldView.workshop`，PR-2a）**：`world_range.workshop_view`；人在主城、`range.workshop` 有寫才有。文字讀 `newcomer.yaml`，標頭前面加 `capital_name`；`practice_available`／`practice_blocked_zh` 和端點同一個 `practice_problem`；`practice_new`＝`PRACTICE_SEEN` 不在 `hints_seen`。前端點「靶場試玩」時送既有的 `hint_seen {ids: [seen_id]}`（後端沒有新動作）。主城 `workshop_master` 的 `panel: workshop`；前端 `atlasModel.objectHud` 在 PR-2b 接上面板前先略過 `workshop`（照舊開說明卡）。

**測試模式（#147）目前的接線狀態**（PR-2a 完成後端）：引擎端在 `trpg.engine.practice.PracticeRules`（見 `docs/dev/上手-引擎戰鬥結算.md`）。工坊靶場的每一場（選大類與正式選定、重選畫面的 `range/trial`、工坊師傅的 `range/practice`）都由 `opening._practice_setup` 組：`practice=PracticeRules()`、`max_rounds=None`、我方先手（`range.max_rounds` 留著但測試模式不用）。畫面靠 `BattleView.practice`（`state.practice is not None`）。實戰、技能工坊（3F，`/api/battles` 帶 `training_range`）、roguelite 一輪、循環賽、開發用 Boss 排演都不帶，`practice` 為 `False`（`tests/api/test_pr2a_range_practice.py` A2 鎖著）。前端 HUD 的分支是 PR-2b、木樁與場景畫法是 PR-2c。

**提示旗標 `hints_seen`**

- `CharacterState.hints_seen: tuple[str, ...]`，**必須排序且不重複**（有 validator）。寫入一律 `tuple(sorted({*seen, 新 ID}))`。
- 來源一：前端送 `hint_seen {ids, level}`（`step._hint_seen`）；`hints_reset` 清空、`hints_off` 關短提示。這三個屬於 `UI_NOTE_ACTIONS`，戰鬥中、有待選項時也能送，開局閘門的白名單也放行。
- 來源二：規則程式自己記（例：略過配點教學後換了地點記 `LESSON_ALLOCATE_LEFT`）。這種會影響重播結果，屬於規則改動。
- ID 慣例：戰鬥短提示的 ID、`opening`（開場看過）、`lesson:<種類>`（教學；前綴常數 `LESSON_SEEN_PREFIX` 在 `world_newcomer_view.py`）、`range:practice`（點開過工坊師傅的「靶場試玩」，`PRACTICE_SEEN`，PR-2a；「重新顯示提示」清掉後「新」小牌會再出現，玩法 PM 同意）。
- 新的「只出一次」旗標優先放 `hints_seen`，不要加存檔欄位。

## 三、必守的規矩

1. **世界規則是純函式**：`world_step` 不讀時間（`now` 由 `WorldStore` 傳入）、不呼叫 LLM、亂數只從 `trpg.world.rng` 依賽季種子衍生。不合法就拋 `WorldActionError`，狀態不變（模型不可變，用 `model_copy(update=…)`）。
2. **版號何時加一**（`docs/開發PM交接.md` 6.6；細節在 `save.py` 常數下的說明）：

   | 版號 | 在哪 | 什麼時候加 |
   |---|---|---|
   | `WORLD_RULES_VERSION` | `world/save.py` | 改了 `trpg.world` 的規則**程式**、同一份世界日誌會重播出不同結果（走路、遇敵、任務推進、閘門由擋變放或反過來、新動作）。同一個 commit 手動加一，並在常數下的清單加一條說明。只改 `content/`、純顯示、API、前端不用加。**不確定就加**。 |
   | `CHAR_FORMAT` | `world/state.py` | `CharacterState`（含巢狀模型如 `OpeningState`）加欄位或改結構。舊版號加進 `LEGACY_CHAR_FORMATS`，新欄位給預設值讓舊檔讀得進來。 |
   | `WLOG_FORMAT` | `world/save.py` | 日誌一筆的結構變了。只是動作 union 多一種不用加（OB-1、OB-3 都沒加）。 |
   | `LOG_FORMAT` | `engine/runner.py` | 動到引擎的紀錄結構或結算；這一塊通常不碰。 |
   | `SAVE_FORMAT` | `roguelite/save.py` | `RunState`／一輪存檔的結構變了；舊版號進 `COMPATIBLE_FORMATS` 並寫轉換。 |

   改版號時 `tests/world/test_opening_stages.py::test_versions` 的字面值要跟著改；兩段同一批上線只加一次，合併時由 PM 對齊。
3. **加存檔欄位要登記季末重置**：`tests/test_architecture.py::test_every_saved_field_has_a_season_reset_kind` 會擋沒登記在 `server/season_policy.py` 的欄位。改到存檔欄位的段，相關測試一定包含 `tests/test_architecture.py`。
4. **已寫入設計文件的規則不能自己放寬**（`CLAUDE.md` 角色分工）：閘門、條件、次數這類規則有疑問就照最保守的做並寫進「待 PM 決定」；被擋的原因文字是暫定可以改字，但不能改判斷。
5. **畫面與規則用同一個函式**：敵人顯示與接觸判定共用 `field_enemies._shown`、被擋原因共用 `opening_limits`／`opening.opening_limits`、紮營條件共用 `step.camp_problem`。新增限制時先找有沒有現成的共用點，不要在 API 層另寫一份判斷。
6. **匯入方向**：`opening_limits.py` 只依賴內容與狀態，`quests`、`solutions`、`field_things` 都要用它，所以它不能匯入其他世界邏輯；`opening_choice` 匯入 `quests`，反過來不行。`trpg.world` 不能匯入 `trpg.api`。
7. **文字讀內容檔**：地名、台詞、頭像、入門招 ID 都從 `newcomer.yaml` 與伺服器來；前端靶場的四個檔不能出現技能 ID 或寫死「主城」（vitest 掃原始碼，`client/src/world/range.test.ts`）。
8. **API 欄位變了要重產型別**：`uv run python scripts/export_openapi.py` 再 `corepack pnpm -C client gen:api`，`client/openapi.json` 與 `client/src/api/schema.d.ts` 一起 commit（`tests/api/test_openapi_snapshot.py` 會擋）。

## 四、常踩的坑

1. **入門招靠 `range.demos` 辨識，不是記在角色身上**。上線後若換示範招，已在入門期的角色身上的舊入門招不會被收回；要改成記在 `OpeningState` 就得加欄位、升 `CHAR_FORMAT`。（`docs/phases/PhaseOB-2報告.md` 待決 8）
2. **`STARTER_STEPS` 原本有兩份**（`opening_limits` 與 `opening_choice`），因為匯入方向不能互相引用；OB-5 已改成單向匯入。新加共用常數時放在 `opening_limits.py`。（`PhaseOB-4報告.md` 待決 7、`PhaseOB-5報告.md` 1.2）
3. **`tests/world` 的 `library` fixture 沒有實地地圖**（`without_fields`）。戰鬥閘認「新手前兩步的固定戰」是看任務資料的 `win_battle` 條件，不是看地圖的 `spawns`；改成看地圖會讓既有測試全掛。需要實地地圖的測試用根目錄 `tests/conftest.py` 的 `field_library`。（`PhaseOB-4報告.md` 第 2 節）
4. **入門期歸零遇敵機率時擲骰照擲**（`step._travel_to`）：亂數消耗次數不能變，否則之後的結果全部位移。隱藏敵人時巡邏步數、陣容種子也照算。（`PhaseOB-4報告.md` 第 2 節）
5. **給招的任務步驟在入門期是「先不結算」**：狀態型條件（到某地、線頭、好感度）選定後下一個動作會補算；**事件型條件**（當下那次情境判定）不會補算。新增給招步驟時跑 `tests/world/test_opening_limits.py::test_skill_reward_steps_stay_reachable_after_choice`，它用 `stuck_conditions` 掃全部任務。（`PhaseOB-4報告.md` 待決 2、第 7 節）
6. **被隱藏的敵人仍算「還在」**：要先清空才能紮營的地點，入門期改成「還在的敵人自己全都看不到時不擋」（`field_enemies.hidden_only`）；「已清空」的顯示沒有跟著變。（`PhaseOB-4報告.md` 第 7 節）
7. **推薦關鍵字很貴**：一把武器最多試 11 個關鍵字、約 0.5 秒，靶場 23 把全算約 11 秒，不能放進每次重畫的 `RangeView`。現在只算手上那把並有快取，其他武器走 `range/recommend` 端點。（`PhaseOB-2報告.md` 待決 2）
8. **可以重選時推薦是空的**：第 1 個推薦看入門招的使用次數，而那些紀錄在正式選定時就收回了。（`PhaseOB-3報告.md` 待決 1）
9. **正式選定與重選會同步算三選一**，每組約 1～3 秒，背景預先計算幫不上；畫面要有等待提示。重選後 `offers_made` 繼續往下數，所以同一套選擇重選出來的三選一和第一次不同。（`PhaseOB-2報告.md` 待決 5、`PhaseOB-3報告.md` 待決 2、10）
10. **起始武器本體靠物品 ID `base_<武器 ID>` 認**；別人寄來同一種基礎武器時分不出來。（`PhaseOB-3報告.md` 待決 3）
11. **`pick_class` 階段後端仍收舊的一次選定 `opening_confirm`**（`test_pick_class_stage_keeps_old_one_shot_confirm` 鎖著）；前端已不送。要拿掉是規則改動，先問 PM。（`PhaseOB-5報告.md` 待決 2）
12. **開發用端點不受閘門保護**：`api/world_dev.py` 直接塞進去的遭遇，在入門期會被 `fight_problem` 擋住、只能撤退。寫實機腳本時先讓角色完成選定。（`PhaseOB-4報告.md` 待決 9）
13. **定稿換字會打到靠關鍵字比對的測試**：原本用「入門期」三個字比對的斷言，定稿句子沒有這三個字就失敗。斷言盡量比對常數（例 `match=BLOCKED`），不要比對片段。（`PhaseOB-5報告.md` 1.3）
14. **八個測試目錄用一個 pytest 一次跑會卡住**（OB-3 兩次都卡），改成分批跑。（`PhaseOB-3報告.md` 第 8 節）
15. **`test_dev_boss_rehearses_to_the_boss_charge` 曾經不穩**，已用固定世界種子與角色 ID 修穩；新寫的 API 測試不要依賴 `secrets` 產生的種子或 ID。（`docs/開發PM交接.md` 3.000 第 1 點）
16. **入門武器在入門期不是物品**（主手不能換，所以永遠是 `hero.weapon` 合成的 `base_<武器>`），卡片寫的「不能賣、寄、分解」是靠「送不出去」成立：賣是 `item` 格式不合（422）、寄與分解是背包裡找不到（`tests/api/test_ob6_reselect.py::test_starter_weapon_card_and_every_cannot_is_refused`）。之後若讓入門武器變成背包物品，要補真正的擋法。（`PhaseOB-6a報告.md` 待決）
17. **窄版（< 1040）任務欄預設收合**，重選小牌在收合的捲軸圖示上看不到，要展開才看得到。（`PhaseOB-6a報告.md` 待決）
18. **pytest 的檔案參數順序**：`tests/api/<檔>` 排在 `tests/test_architecture.py` **後面**時，`tests/api/conftest.py` 不會套到那個檔（`make_client` 找不到、`capital_spawn` 不生效）。一次跑多個檔時把 `tests/test_architecture.py` 放最後。（`PhasePR-2a報告.md` 第 3 節）
19. **`BattleView` 加有預設值的欄位，前端測試的 `smallView`（`client/src/battle/testFixtures.ts`）也要補**：產生的型別在輸出模型裡是必填，typecheck 會擋。（`PhasePR-2a報告.md` 第 4 節）
20. **開局只帶賽倫、阿岳第 1 步打完才入隊（OB-7，#154）**：`content/world/mercenaries.yaml` 的 `default_party` 只剩 `merc_tiebi`；任務 `starter_ferry` 的 `companion_after: ferry_bandits`（`trpg.world.companions._joined_yet`，那一步完成才算該在隊）。賽倫其實從建角就在隊上（選大類階段沒有戰鬥，玩家感受不到），台詞在確定出發後才由 `WorldView.party_intro` 給前端播。量頭目的 `sim/boss_probe.py` 改用 `PROBE_PARTY`（賽倫＋回春）不跟 `default_party`；凍結重播 `tests/world/test_field_ctx_replay.py` 也寫死 `FROZEN_PARTY`。
21. **隊友的台詞與來歷（OB-7）**：`WorldView.party_intro`（`api/world_party_intro.py`）一次給一段沒播過的（賽倫先，條件：`opening` 不是 `None`、`stage != pick_class`、他是開局那一位且在隊上；夥伴：在隊上、有 `join_lines`）；看過＝`hints_seen` 有 `intro:<成員 ID>`，前端送既有的 `hint_seen`。`PartyMemberView.backstory_zh`：賽倫看 `party.is_escort`（`hire` 換下他時規則記劇情旗標 `escort_parted`，`WORLD_RULES_VERSION` 27）、夥伴讀 `CompanionDef.backstory_zh`。

## 五、相關測試檔

| 改了什麼 | 跑哪些 |
|---|---|
| 開局階段、閘門、版號 | `tests/world/test_opening.py`、`tests/world/test_opening_stages.py` |
| 正式選定 | `tests/world/test_opening_choice.py`、`tests/api/test_opening_choice_api.py` |
| 開局隊友、阿岳入隊時機、台詞與來歷（OB-7） | `tests/world/test_companions.py`、`tests/world/test_party.py`、`tests/api/test_ob7_party_intro.py`、`tests/content/test_world_mercenaries.py` |
| 重選、開局結束 | `tests/world/test_opening_reselect.py`、`tests/world/test_opening_end.py`；重選畫面資料、雇用與影子句、卡片的「不能」（OB-6）：`tests/api/test_ob6_reselect.py` |
| 入門期限制 | `tests/world/test_opening_limits.py`、`tests/api/test_opening_flash.py` |
| 選大類 API、靶場 API、試打 | `tests/api/test_opening_class_api.py`、`tests/api/test_range_api.py`、`tests/api/test_capital_opening_api.py` |
| 測試模式接線、靶場試玩、工坊師傅選單、一角色一場（PR-2a） | `tests/api/test_pr2a_range_practice.py`（A1～A10）；主城物件的 `panel`：`tests/world/test_capital.py`、`tests/world/test_capital_figures.py`、`client/src/world/capitalFigures.test.ts` |
| 教學、提示、新手引導 | `tests/api/test_opening_lessons.py`、`tests/api/test_newcomer_api.py`、`tests/world/test_newcomer.py` |
| `newcomer.yaml`、靶場地圖 | `tests/content/test_newcomer_content.py`、`tests/content/test_training_range.py` |
| 存檔格式、重播 | `tests/world/test_save.py`、`tests/world/test_replay.py`、`tests/world/test_quest_replay.py`、`tests/world/test_field_ctx_replay.py`（用 `tests/world/frozen_replay/` 的凍結內容） |
| 存檔欄位、依賴方向 | `tests/test_architecture.py` |
| API 結構 | `tests/api/test_openapi_snapshot.py`、`tests/api/test_world_api.py` |
| 起始技能、配點 | `tests/roguelite/test_keyword_start.py`、`tests/roguelite/test_start.py`、`tests/roguelite/test_start_allocation_mean.py` |
| 一輪存檔 | `tests/roguelite/test_save.py` |
| 前端選定與重選畫面 | `client/src/world/range.test.ts`（OB-6 的重選頁、確認彈窗、入口、小牌在最後一個 describe）、`limits.test.ts`（三選一捲回最上面、鐵匠預設防具、卡片那一行）、`capitalOpening.test.ts`、`capitalOpeningReview.test.ts` |

- **特別久**：`tests/skillgen/test_player_text.py` 裡有一項單獨要約 295 秒（待標 slow），不要為了這一塊去跑整個 `tests/skillgen`。`tests/roguelite/test_flash_run.py`、`test_flash_llm_run.py`、`test_offers.py` 有 slow 項（預設不跑）。
- `tests/world` 整個目錄很大，開發中只挑上表的檔；交件前才整個目錄跑一次（`-n 8`）。
- OB-5 補的畫面資料（`WorldView.limits`、各面板的不可用原因）測試在 `tests/api/test_ob5_screen_data.py`。

## 六、要跑的最小檢查

```bash
# 新 worktree 第一次（之後才加 UV_NO_SYNC=1）
uv sync --frozen

UV_NO_SYNC=1 uv run ruff check .
UV_NO_SYNC=1 uv run ruff format --check .
UV_NO_SYNC=1 uv run mypy
UV_NO_SYNC=1 uv run lint-imports

# 直接相關的測試（依上表挑；不要帶 -m）
UV_NO_SYNC=1 uv run pytest -q tests/world/test_opening_stages.py tests/world/test_opening_choice.py -x
UV_NO_SYNC=1 uv run pytest -q tests/world/test_opening.py tests/world/test_opening_limits.py tests/world/test_opening_reselect.py tests/world/test_opening_end.py tests/api/test_opening_choice_api.py tests/api/test_range_api.py tests/test_architecture.py -n 8

# 改了 newcomer.yaml 或其他內容
UV_NO_SYNC=1 uv run trpg content check
UV_NO_SYNC=1 uv run pytest -q tests/content/test_newcomer_content.py tests/content/test_training_range.py

# 改了 API 欄位
UV_NO_SYNC=1 uv run python scripts/export_openapi.py
corepack pnpm -C client gen:api
UV_NO_SYNC=1 uv run pytest -q tests/api/test_openapi_snapshot.py
corepack pnpm -C client typecheck

# 一場重播（每段合併的固定項目）
UV_NO_SYNC=1 uv run trpg battle --map open_plain --seed 7 --log-json <暫存>/b.json
UV_NO_SYNC=1 uv run trpg battle replay <暫存>/b.json
```

- 有改前端才跑 `corepack pnpm -C client test`（或只跑相關檔：`corepack pnpm -C client exec vitest run src/world/range.test.ts`）與 build；細節見 `docs/dev/上手-前端戰鬥畫面與動畫.md`。
- 要開伺服器實測：`uv run trpg serve --port <PM 指定的埠>`，不用 8000、8001；存檔目錄用環境變數 `TRPG_SAVE_DIR` 指到暫存區，不要寫進專案的 `saves/`；結束時只用自己記下的 PID 關（守則 13）。
- 不跑 `scripts/check.py`、不跑大型模擬。
