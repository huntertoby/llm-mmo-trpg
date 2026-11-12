# Phase PR-2a 報告｜靶場測試模式：後端接線

> 規格：`docs/phases/PhasePR-2計畫.md`（PR-2a 一節；「第 1～10 點已定」取代原待確認表）。規則：`docs/design/21-探索地圖與城鎮.md` 21.5 第 9 點（含「PR-2 補充」）與測試模式第 6、7 點。字串：玩法 PM 定稿 `台詞-OB5與PR2定稿.md`「PR-2 字串」「工坊師傅（PR-2）」兩表（逐字）。
> 基底：本機 main `88909dec`（含 OB-6a、CB-3c）。未 push。

## 1. Commit

| commit | 內容 | 對應交付 |
|---|---|---|
| `925c5780` | `BattleView.practice`（`state.practice is not None`）；重產 OpenAPI 與 `schema.d.ts` | 1、7 |
| `25724e2d` | 開局試打一律測試模式（`_practice_setup`：`practice=PracticeRules()`、`max_rounds=None`）；`practice_problem`、`own_practice`、`practice_seed`；`world/battle.py` 的 `_hero_spawn` 公開成 `hero_spawn`（行為不變）；`range.max_rounds` 註明測試模式不用 | 2、3 |
| `9c25b8cf` | `SessionStore.discard`；`WorldStore.close_trial`／`track_trial`（一角色一場）；`POST …/range/practice`、`DELETE …/range/trial`；`range/trial` 開新場前先刪舊場；重產型別 | 4、7 |
| `f5522945` | `newcomer.yaml` `range.workshop`（`WorkshopContent`）；`ObjectPanel` 加 `workshop`、`capital.yaml` `workshop_master` 加 `panel: workshop`；`training_range` 說明卡換定稿句（P4）；`WorldView.workshop`（`WorkshopView`）、`PRACTICE_SEEN`；重產型別；為了 typecheck 改兩個前端檔（第 4 節） | 5、7 |
| `221b3b7c` | `tests/api/test_pr2a_range_practice.py`（A1～A10）；`client/src/world/capitalFigures.test.ts` 期望值 | 6 |
| （本報告的 commit） | 本報告、`docs/dev/上手-roguelite開局與入門期.md` | 8 |

## 2. 做了什麼

1. **`BattleView.practice: bool = False`**（`src/trpg/engine/view.py`）：`project_for` 填 `state.practice is not None`。不進 `BattleLog`、不動規則包雜湊。`tests/cli/test_output_snapshots.py` 快照沒變（見第 3 節）。
2. **開局試打帶測試模式**：`opening.range_trial` 改用 `_practice_setup`（地圖、規則包、單位、`max_rounds=None`、我方先手、`practice=PracticeRules()`）；木樁抽成 `_dummy_spawns`。選大類、葛蘭／主城的正式選定、重選畫面的「拿起試打」「看示範」都走這裡，一起變測試模式。
3. **靶場試玩**（`src/trpg/world/opening.py`）：
   - `practice_problem(library, char, *, in_battle)`：依序 不在主城 → `pick_class` → 戰鬥中或有遭遇 → 有待選閃現或三選一；其他 `None`。`pending_encounter` 直接讀角色（等效簽名）。
   - `own_practice(library, char)`：主角＝`world.battle.hero_spawn(library, char, 1, (), statuses=())` 再把 `hp`／`mana`／`stamina` 設 `None`（給滿）、位置 `range.hero_at`；不帶腰包道具、誓約、`next_battle` 狀態；只有主角＋`range.dummies`；規則包加生成技能（依 ID 排序，同 `prepare_battle`）；種子 `fnv1a64(f"practice|{角色 ID}") & MASK64`。
4. **工作階段表與端點**：
   - `SessionStore.discard(battle_id)`（不存在不報錯）。
   - `WorldStore._trials`（角色 → battle_id，只在記憶體）；`close_trial` 刪舊場、`track_trial` 記新場（兩個請求同時開時也刪掉前一場）。
   - `POST /api/world/characters/{id}/range/practice`（無 body）→ `RangeTrialResponse`（`title_zh`「靶場試玩：{武器}」、`demo=False`、`skills_zh`＝主角技能名）；不能開 422，`detail`＝`practice_problem` 的字。
   - `DELETE /api/world/characters/{id}/range/trial` → 204（沒有也 204）。擁有者：`/api/world` 路由既有的 `require_world_access`（別人的角色 404）；開的戰鬥 `owner` 照舊記帳號。
5. **工坊師傅選單**：`range.workshop`（`master_object`、`title_zh`、`line`、`practice_zh`／`practice_note_zh`、`rework_zh`／`rework_note_zh`、`footer_zh`，字逐字照定稿）；`WorldView.workshop: WorkshopView | None`（人在主城、有 `range.workshop` 才有）：`title_zh`（前加 `capital_name`）、`capital_zh`、`speaker`（`workshop_master` 情境物件的 `figure.portrait`，和 `_keeper` 共用 `_capital_figure`）、`line`、兩列、`footer_zh`、`practice_available`、`practice_blocked_zh`、`practice_new`、`seen_id`。`PRACTICE_SEEN = "range:practice"` 在 `api/world_newcomer_view.py`。後端沒有新動作。
6. **測試**：見第 3 節。
7. **型別**：`scripts/export_openapi.py`、`gen:api` 三次（每個改 API 的 commit 各一次），`client/openapi.json` 與 `client/src/api/schema.d.ts` 一起 commit；`corepack pnpm -C client typecheck` 結束碼 0。
8. **上手筆記**：`docs/dev/上手-roguelite開局與入門期.md` 更新第一節（檔案表：`opening.py`、`battle.py`、`world.py`、新列 `sessions.py`、`routes/world.py` 新端點、`world_range*`、`world_newcomer_view.py`、`world_schemas.py`、`newcomer.yaml`、新列 `capital.yaml`）、第二節（新增「靶場試玩」「一角色一場」「工坊師傅選單」三段、改寫「測試模式目前的接線狀態」、提示旗標 ID 慣例加 `range:practice`）、第四節（新坑 18、19）、第五節（測試表加 PR-2a 一列）、檔頭日期。

## 3. 逐條驗收

| 驗收 | 結果 | 證據 |
|---|---|---|
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 通過 | `All checks passed!`、`2340 files already formatted`、`Success: no issues found in 1443 source files`、`Contracts: 14 kept, 0 broken.` |
| 新增複雜度 noqa | 沒有 | — |
| 規格列的 pytest 批次＋新測試檔 | 133 passed | `pytest -q tests/world/test_opening.py tests/world/test_opening_stages.py tests/api/test_range_api.py tests/api/test_capital_opening_api.py tests/api/test_openapi_snapshot.py tests/api/test_world_api.py tests/api/test_pr2a_range_practice.py tests/test_architecture.py -n 8` → `133 passed`（**`tests/test_architecture.py` 要放最後**，見下方「pytest 參數順序」） |
| `tests/engine/test_practice_mode.py`、`tests/engine/test_view.py`、`tests/cli/test_output_snapshots.py` | 63 passed，快照沒變 | `git status` 在跑完後只有 `view.py` 的改動，`tests/cli` 下沒有任何檔變 |
| 其他相關 | 243 passed | `tests/content/test_newcomer_content.py`、`test_training_range.py`、`test_capital_field.py`、`tests/api/test_ob5_screen_data.py`、`test_ob6_reselect.py`、`test_opening_class_api.py`、`test_newcomer_api.py`、`test_opening_choice_api.py`、`test_opening_lessons.py`、`tests/world/test_capital.py`、`test_capital_figures.py`、`test_opening_choice.py`、`test_opening_reselect.py`、`test_opening_limits.py`、`test_opening_end.py` |
| 行為一致測試 A 組 | 全過（25 項） | 下表 |
| 一場重播 | 通過 | `trpg battle --map open_plain --seed 7 --log-json b.json` 結束碼 0；`trpg battle replay b.json` →「重播驗證通過：91 個動作、383 個事件，最終狀態一致（open_plain，種子 7）。」 |
| 測試模式試打的 `to_log()` 用 `trpg battle replay` | 通過 | 暫存腳本開 `own_practice` 那場、主角 5 個動作後 `to_log()` 寫 JSON → `trpg battle replay p.json` →「重播驗證通過：20 個動作、89 個事件，最終狀態一致（training_range，種子 14778934076249091018）。」（20＝主角 5 步＋木樁 AI 的步） |
| `WORLD_RULES_VERSION`、`CHAR_FORMAT`、`LOG_FORMAT` | 都沒變 | `tests/world/test_opening_stages.py::test_versions` 字面值沒動且通過 |
| `trpg content check` | 通過 | 「共 658 個檔案；跨檔案檢查…通過；402 個技能通過預算與結構驗證。」 |
| `corepack pnpm -C client typecheck` | 結束碼 0 | `tsc --noEmit` 無輸出 |
| （順手）`corepack pnpm -C client test` | 3526 passed（修正 1 個內容期望值後） | 第一次跑 `capitalFigures.test.ts` 的「位置與面板照舊」因 `workshop_master` 多了 `panel` 失敗，改期望值後該檔與 `atlas.test.ts` 26 passed；其餘 285 檔原本就過 |

**A 組對照**（`tests/api/test_pr2a_range_practice.py`；世界種子 `20261112`、角色 ID `c_pr2a0001` 起依建角順序固定）

| # | 測試 | 斷言重點 |
|---|---|---|
| A1、A2（靶場） | `test_a1_a2_range_entries_are_sandboxed_test_mode[pick_class_trial / choice_screen_trial / own_practice]` | 三種入口各開一場、經 `/api/battles/{id}/actions` 放招、普攻、走路、放招、普攻；每個回應 `view.practice is True`、`max_rounds is None`；之後 `dumps_char`、`dumps_world`、日誌筆數、`world.json` 內容全同；`GET …/characters/{id}` 的 `battle_id is None` |
| A2（其他） | `test_a2_world_encounter_is_not_test_mode`、`test_a2_workshop_3f_is_not_test_mode`、`test_a2_roguelite_run_battle_is_not_test_mode`、`test_a2_league_match_is_not_test_mode` | `practice is False`、`max_rounds` 照原值。循環賽用 `world.league.match_setup` 組一場（循環賽重播端點用的就是當初 `match_setup` 的紀錄），不跑整個賽程 |
| A3 | `test_a3_test_mode_rules_through_the_api` | 預覽普攻 `hit_permille == 1000`；放一招有冷卻的技能後冷卻全 0、HP／法力為滿、AP＝`ap_cap`、輪數 +1、主角沒有 `end_turn` 步；普攻再 +1；走路輪數不變 |
| A4 | `test_a4_own_skills_and_gear` | 帶裝備、腰包、誓約、`next_battle`、HP 1 的角色：技能列＝`hero_spawn`（實戰）的技能列、不含腰包道具；裝備相同且非空；開場狀態空（實戰有 `poison`）；HP／法力／耐力 `None`；沒有誓約；只有主角＋木樁；種子＝`practice_seed`；API 的標題、`skills_zh`；開完後 `next_battle`、腰包、誓約都沒被消耗 |
| A5 | `test_a5_screen_and_endpoint_agree[done_in_capital / starter_in_capital / chosen_in_capital / pick_class / in_misty_town / in_battle / pending_encounter / pending_flash / pending_offer]` | `workshop.practice_available` 與端點 200／422 一致；422 的 `detail`＝`practice_blocked_zh`＝`practice_problem`；霧渡鎮 `workshop is None` |
| A6 | `test_a6_new_badge_follows_hints_seen` | `practice_new` 依序 `True`、`False`、`True`；`hint_seen` 前後日誌多一筆；`WORLD_RULES_VERSION` 仍是 25 |
| A7 | `test_a7_one_sandbox_per_character`、`test_a7_trial_and_practice_share_the_slot`、`test_a7_other_accounts_cannot_open_or_delete` | 同角色連開兩次，第一場 404、`len(store.battles)` 不增；DELETE 後 404、再 DELETE 也 204；別的角色的那場還在；開局試打與靶場試玩共用一格；開發模式關時別的帳號開、刪、讀都 404 |
| A8 | `test_a8_workshop_3f_keeps_cooldowns_and_end_turn` | 技能工坊放招後冷卻 > 0、輪數不變、`end_turn` 仍在合法動作 |
| A9 | `test_a9_practice_log_replays` | 5 個動作後 `to_log()` → JSON 檔 → `BattleLog` → `log_replay_problem is None`；`setup.practice` 有值 |
| A10 | `test_a10_workshop_text_matches_the_final_strings` | 標題「樞島工坊・靶場與改造」、台詞、兩列、面板下說明、三句原因、主城靶場說明卡逐字等於定稿；`workshop_master.panel == "workshop"`；師傅有頭像 |

**pytest 參數順序**：`pytest … tests/api/test_world_api.py tests/test_architecture.py tests/api/<任何檔>` 時，排在 `tests/test_architecture.py` 後面的 `tests/api` 檔拿不到 `tests/api/conftest.py`（`fixture 'make_client' not found`、`capital_spawn` 不生效）。用既有的 `tests/api/test_range_api.py` 也重現（`28 passed, 13 errors`），和本段的改動無關；把 `tests/test_architecture.py` 放最後就全過。已寫進上手筆記第四節第 18 點。

**長時間單場的耗時**（規格範圍外的量測）：靶場試玩一場打到 318 步，`BattleSession.history()` 從頭重播一次 0.017 秒；20 步時 0.003 秒。

## 4. 和規格不同的地方

1. **改了「只改」清單外的三個前端檔**（為了 `typecheck` 與 vitest 過）：
   - `client/src/battle/testFixtures.ts`：`smallView` 補 `practice: false`。產生的型別裡輸出模型的 `practice` 是必填，不補 typecheck 失敗。
   - `client/src/world/atlasModel.ts` `objectHud`：`panel === "workshop"` 先回 `null`（照舊開說明卡）。`ObjectPanel` 多了 `workshop` 後 `HudPanel` 沒有這一項，typecheck 失敗；若改 `hud.ts` 加進 `HudPanel`，在 2b 之前點師傅會開出空白（`WorldScreen` 的 `default: return null`），所以選最保守的「照舊開說明卡」。**2b 要拿掉這個判斷**並在 `HudPanel`／`WorldScreen` 接上面板。
   - `client/src/world/capitalFigures.test.ts`：「位置與面板照舊」的期望值 `workshop_master.panel` 改成 `"workshop"`（和 Python 那兩個測試同一件事）。
2. `WorkshopContent` 多一個 `master_object`（頭像取哪個情境物件；比照 `keeper_object`），規格的欄位列表沒寫。
3. `practice_problem` 的簽名只有 `in_battle`（遭遇直接讀 `char.pending_encounter`），規格寫「或等效簽名」。

## 5. 更動的既有測試

| 檔 | 改動 | 理由 |
|---|---|---|
| `tests/world/test_capital_figures.py` | `ORIGINAL["workshop_master"]` 的 panel `None` → `"workshop"` | 交付 5 的內容改動（`test_four_keepers_have_figure_at_original_cell[workshop_master]`、`test_world_view_carries_figures`） |
| `tests/world/test_capital.py::test_capital_objects_carry_panel_and_stele` | 期望的 `panels` 加 `"workshop_master": "workshop"` | 同上 |
| `client/src/world/capitalFigures.test.ts` | 同上（前端那份） | 同上 |

規格預期會改的 `tests/world/test_opening.py`、`tests/api/test_range_api.py` 不用改（沒有斷言 `max_rounds`；`test_trial_is_sandbox` 的 `end_turn` 在測試模式仍合法）。其他斷言都沒放寬。

## 6. 版號

`WORLD_RULES_VERSION`（25）、`CHAR_FORMAT`（`trpg-char/13`）、`LOG_FORMAT`（`trpg-battle-log/113`）、`WLOG_FORMAT`、`SAVE_FORMAT` 都沒變。理由：試打與靶場試玩不經過 `world_step`、不寫日誌；「新」小牌用既有的 `hint_seen`；角色存檔沒有新欄位；引擎只多了畫面欄位。

## 7. 複雜度 noqa

沒有新增。

## 8. 暫定字串

| 位置 | 現在的字 | 出現時機 |
|---|---|---|
| `opening.PRACTICE_PLACE_ZH` | 靶場試玩要到{主城地名}的工坊靶場找工坊師傅 | 不在主城時打 `POST …/range/practice` 的 422（畫面上不在主城時沒有師傅選單，所以玩家正常看不到） |
| `world_range.PRACTICE_TITLE_ZH` | 靶場試玩（＋「：{武器}」） | 定稿字，列出供對照 |

其餘新字（三句原因、師傅台詞、兩列、面板下說明、靶場說明卡）都是定稿原字。

## 9. 實機未看

2a 沒有畫面；沒有開伺服器、沒有開瀏覽器，沒有殘留程序。

## 10. 待 PM 決定

1. **不在主城的原因句**（暫定「靶場試玩要到{主城地名}的工坊靶場找工坊師傅」）：定稿沒有這句；畫面上看不到，只在直接打端點時出現。
2. **擋的順序**：不在主城 → 還在選大類 → 戰鬥／遭遇 → 待選閃現／三選一（同時符合多條時只回第一條）。
3. **主城室內也能開**：`in_capital` 只看區域（含 7 張室內圖），在主城室內打端點也能開；畫面上只有工坊師傅一個入口，實際不影響。
4. **`atlasModel.objectHud` 的過渡判斷**（第 4 節第 1 點）：2a 先合併時點工坊師傅照舊開說明卡（字「「工坊還在整理。」靶場與改造技能還沒開放。」，`note_zh` 照規格保留）；2b 接上面板時拿掉。
5. **開局試打標題**照舊是「靶場試打：{武器}」／「看示範：{武器}」；OB-5 定稿表寫「靶場試打：{武器}＋{招 1}、{招 2}」，本段範圍外沒改（若前端自己組就不用動）。
6. **沒按離開就關頁的沙盒**：一角色最多留一場，下次開或伺服器重啟才清；沒有逾時清理。
7. **循環賽的 A2**用 `match_setup` 組一場驗證，沒跑整個賽程＋重播端點（要約 10 秒以上的整季循環賽）。
8. **`range.max_rounds`** 仍在 schema 驗證（1～200）但不用；要拿掉要改內容檔與 schema。
