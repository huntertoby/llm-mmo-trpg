# Phase OB-2 報告：#150 三選一延後、正式選定、關鍵字推薦、入門期不存影子

> 實作者：worktree 基準 main `26916cbb`。沒有 push、沒有 merge。依據：`docs/phases/PhaseOB-2計畫.md`、`docs/design/21` 21.5（#150 第 1～9 點）、`docs/phases/PhaseOB-1報告.md`、共用筆記 `盤點-150與147.md` 第 1.1、1.2、4.3 節。沒有動 `src/trpg/engine/`、`src/trpg/roguelite/`、`tests/engine/`、`content/`、CLI 快照。

## 1. 交付項目

| # | 項目 | 做法 |
|---|---|---|
| 1 | 第 1、2 步三選一延後 | `world/quests.py::_complete_step`：`defers_offer`（`opening.stage == "starter"` 且任務 `kind: starter`）成立時記進 `opening.deferred_offers`（`DeferredOffer{quest, step}`，`step` 是步驟在任務裡的索引），不出題、不動 `offers_made`；經驗、靈感、`level_to` 照舊。背景預先計算（`api/offer_prefetch.py`）同條件跳過，不白算 |
| 2 | 正式選定 | 新模組 `world/opening_choice.py`。`opening_confirm` 依階段分流：`pick_class`＝舊的一次選定（不變）、`starter`＝正式選定、`chosen`＝閘門擋（`_chosen_rule`：「已經正式選定武器與關鍵字了」）。順序見第 2 節 |
| 3 | 關鍵字推薦 | `world/opening.py::recommended_keywords(library, char, weapon)`（純函式）；`RangeView.recommended_keywords`（必填，0～2 個） |
| 4 | 入門期不存影子 | `world/shadows.py::save_after_prep`：`opening is not None and stage != "chosen"` 時跳過 |
| 5 | openapi | `client/openapi.json`、`client/src/api/schema.d.ts` 重產；`client/src/world/range.test.ts` 的 fixture 補 `recommended_keywords` |

入門招一律從 `range.demos` 讀（`world/opening.py::starter_skill_ids`，含升階重配後改名成 `<原 ID>_t<階級>` 的），程式與測試都沒有寫死技能 ID。所有新判斷都以 `char.opening is not None` 為前提。

## 2. 正式選定的順序與理由

`apply_formal_choice`（`world/opening_choice.py`）：

| 步 | 做什麼 | 為什麼排在這裡 |
|---|---|---|
| 1 | 檢查：入門期、新手任務打完前 2 步、人在葛蘭所在的城鎮或主城、沒有待處理的遭遇、武器在靶場、關鍵字合法 | 全部檢查完才動狀態，不合法時角色不變 |
| 2 | 依開局種子取起始 2 招（`new_keyword_run`） | 和靶場預覽同一套、同一個種子，預覽看到的招就是拿到的招；關鍵字的檢查也在這裡 |
| 3 | 收回入門招：裝備中與備用的入門招，連同 `flash`、`flash_bases`、`skill_usage`、`skill_regions`、`generated_skills` 的對應項 | 先收回再給新招：新的起始技能剛好和入門招同一招時（例：火焰法杖＋點燃），留下的是新給的那一招、紀錄是空的 |
| 4 | 雙手或成對武器：穿著的副手收進背包（背包放不下就拒絕） | 比照換主手的既有規則，避免雙手武器配副手的不合法狀態；要在換武器之前擋 |
| 5 | 換武器、依新武器的大類重建基礎值（`start_hero`）；名字、種族、外觀照舊 | 入門武器不是物品，換掉 `hero.weapon` 就是收回 |
| 6 | 全部點數重配：開局 4 點＋已分配＋未分配，照推薦配法，全數寫進 `attribute_spent`，`attribute_points` 歸 0 | 配法＝開局點照 `recommended_allocation`、其餘每級一份照 `recommended_level_up`，等於用這套配備從 1 級照推薦升上來；全寫進 `attribute_spent` 之後才退得回（配點教學 OB-3 要用） |
| 7 | 起始 2 招照角色目前的階級重配（`sync_tier`；1～3 級是 1 階，不變），排在裝備最前面；其他來源學到的招照原順序排後面 | 起始 2 招固定在前兩格（推薦配法、配點教學都看前兩招） |
| 8 | 最大 HP、法力、耐力的變化走 `with_hp_change`，再把 HP、法力回滿 | 規格指定走 `with_hp_change`；回滿是 PM 決定 |
| 9 | `opening`：`stage=chosen`、`weapon`、`keywords`、`weapon_class`（新武器的大類）、`granted_skills`＝起始 2 招 | 之後的三選一出題要看到正式的主角 |
| 10 | 依序出 `deferred_offers` 的三選一（`quests.py::issue_deferred_offers`） | 最後才出：候選依正式的武器、招、屬性產生。規則和當場出題是同一個 `_offer`（同技能種子、同 `offers_made` 計數、`mix`／`min_passive`／偏向照任務資料）；取得地點用任務所在的區域，在主城選也一樣 |

之後玩家照既有的 `offer_pick` 一組一組選；選到的招記進 `granted_skills`（`quests.py::_note_granted`，OB-3 重選要收回）。事件：`OpeningConfirmedEvent`（沿用）＋每組一個 `SkillOfferedEvent`。

## 3. 版號

| 項目 | 變動 | 理由 |
|---|---|---|
| `WORLD_RULES_VERSION` | 23 → 24 | 同一份日誌重播結果會變：入門期的新手步驟不再當場出三選一、入門期不存影子、`opening_confirm` 在入門期從拒絕變成正式選定。`save.py` 有寫說明 |
| `CHAR_FORMAT`、`trpg-wlog`、`LOG_FORMAT`、`RULE_HASHES` | 不變 | 欄位 OB-1 已加；沒有新動作、新事件 |

`tests/world/test_opening_stages.py::test_versions` 的字面值 23 跟著改成 24，這是本段唯一改到的既有測試斷言。沒有放寬任何既有規則、驗證或斷言。

## 4. 驗收

| 條件 | 結果 |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 2276 files already formatted |
| `uv run mypy` | Success: no issues found in 1429 source files |
| `lint-imports` | 14 kept, 0 broken |
| `tests/world tests/api tests/content tests/narrative tests/skillgen tests/roguelite tests/server tests/test_architecture.py`（`-n 8`） | 9523 passed、15 skipped、0 failed（7 分 07 秒；`test_dev_boss_rehearses_to_the_boss_charge` 這次也過） |
| `trpg battle --map swamp --seed 7 --log-json` ＋ `battle replay` | 重播驗證通過：63 個動作、235 個事件，最終狀態一致 |
| `corepack pnpm -C client typecheck` | 結束碼 0 |

行為一致測試（`tests/world/test_opening_choice.py` 20 個、`tests/api/test_opening_choice_api.py` 5 個、`tests/api/test_offer_prefetch.py` 加 1 個）：

| 規格 | 測試 |
|---|---|
| 三大類 × 入門期打完第 1、2 步 → 正式選定（真的打兩場固定戰、真的送動作） | `test_formal_choice_after_two_steps`（3 組，都換到別的大類）：每步驗經驗、靈感、升級自動配點、不出題、`offers_made` 不動；選定後驗武器、招、整個主角範本、8 點全在 `attribute_spent`、HP 法力回滿、入門招與 `skill_usage`／`flash` 收回、三選一順序與 `mix`、選完記進 `granted_skills`、不能再選 |
| 三選一的亂數與不延後時一致 | `test_deferred_offers_match_undeferred_rule`（和「同一個角色照舊流程一步一步完成」逐組相等）、`test_formal_choice_is_deterministic`、`test_offers_use_quest_region_when_chosen_in_capital` |
| 舊角色不變 | `test_other_quests_and_done_characters_still_offer_at_once`、`test_pick_class_stage_keeps_old_one_shot_confirm` |
| 條件 | `test_choice_needs_two_steps`、`test_choice_needs_mentor_town_or_capital`、`test_choice_rejects_bad_weapon_or_keywords`（失敗時角色不變） |
| 入門期手動配點、重配不影響結果 | `test_manual_respec_before_choice_does_not_change_result` |
| 副手 | `test_two_handed_choice_stows_off_hand` |
| 關鍵字推薦 | `test_recommended_first_keyword_follows_usage`（3 組 × 4 種用法）、`test_recommended_second_keyword_links_with_first`、`test_recommended_keywords_only_in_starter_stage` |
| 影子 | `test_shadow_saved_only_after_formal_choice` |
| 世界日誌重播 | `test_full_flow_log_replays_identically`：選大類 → 打新手第 2 步 → 走回霧渡鎮 → 休息（不存影子）→ 正式選定 → 選三選一 → 休息（存影子），重播與存檔往返一致 |

沒有新增複雜度類 noqa。

## 5. 待 PM 決定

1. **正式選定多一個條件：新手任務打完前 2 步**。規格的交付項目只寫地點；21.5 第 3 點寫「打完竹林小徑回霧渡鎮」，OB-1 的 `test_starter_blocks` 也斷言入門期一開始送 `opening_confirm` 會被擋，所以照設計加上。「2」是程式常數 `opening_choice.STARTER_STEPS`（OB-4 戰鬥閘可共用），新手任務＝新手區 `kind: starter` 的任務。沒有設定導師 NPC 的內容，任何城鎮都能選（同配點教學）。
2. **`RangeView.recommended_keywords` 只照目前手上的武器（入門武器）算**。第 2 個關鍵字要看「這把武器實際給的起始兩招有沒有觸發關係」，一把武器最多要試 11 個關鍵字，實測約 0.5 秒；靶場 23 把全算約 11 秒，不能放進每次都重畫的畫面資料。現在只在「入門期、已經可以選定」時算、有快取。純函式已經收 `weapon`；OB-5 要逐把武器標推薦的話，建議加一個帶武器的查詢端點。
3. **照現在的內容，近戰與遠程只推薦得出 1 個關鍵字**：近戰＝隱蔽（瞬步背刺，同次數取前面那招）、遠程＝撞擊（散彈驅離），這兩個關鍵字找不到能互相觸發的第 2 個（開局種子 7、靶場 23 把武器逐把實測都沒有）；法器＝點燃＋帶電。照「沒有就不標」處理。要保證有 2 個的話需要另外定規則（例如第 1 個順延到有搭配的候選：近戰的倒地就有）。
4. **兩組延後的三選一在選定當下一次出完**，第 2 組出題時不知道第 1 組選了什麼（不延後時是選完第 1 組才打第 2 步）。
5. **正式選定要同步算兩組三選一**，每組約 1～3 秒（背景預先計算不知道玩家會選什麼，幫不上）；OB-5 的畫面要有等待提示。
6. **`deferred_offers` 選定後不清**：留給 OB-3 重選時照它重新出題，也靠它認出哪些三選一的招要記進 `granted_skills`。
7. **`chosen` 階段的 `opening` 還不會清掉**（到 4 級清成 `None` 是 OB-3）：在那之前正式選定過的角色一直不能溶掉、傳承。目前前端不送 `opening_class`，玩家碰不到。
8. **入門招靠 `range.demos` 辨識**：#148 定案若換招，已經在入門期的角色身上的舊入門招不會被收回。上線前換招沒有影響；上線後要換的話，得在 `OpeningState` 記下實際給的招（要加欄位、升 `CHAR_FORMAT`）。
9. **入門期從其他來源學到的招（機遇、非新手任務的三選一）選定時保留**，排在起始 2 招後面；入門期若先打完第 3 步，它的三選一也會延後、選定時一起出（OB-4 戰鬥閘上線後碰不到）。
10. **選雙手或成對武器時副手收進背包，背包放不下就不能選**（比照換主手；21.5 只寫了重選的背包邊界）。
11. **事件與台詞**：沿用 `OpeningConfirmedEvent`，句子還是「帶著…出發：起始技能…」；三選一延後沒有事件（步驟完成事件照舊）。台詞與提示留給 OB-5／6。
12. `pick_class` 階段送 `opening_confirm` 仍是舊的一次選定（OB-1 待決 1，OB-5 換前端時收掉）。
