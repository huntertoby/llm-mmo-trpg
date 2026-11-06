# Phase 3-33d 報告｜灌注技能

> 規格：`docs/phases/Phase3計畫.md` 36.5；設計：`docs/design/06-技能.md` 6.29.3。數值都是初值（`content/rules/core.yaml`、`content/ai_profiles.yaml`），沒有調任何既有數值。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| 動作 | `infuse_skill`（`summon_id`、`skill_id`；`summon_infuse_ap_cost` = 1 AP）：施放者 **當下** 付法力、HP 代價、每場次數與冷卻（`pay_skill_cost`，冷卻當下開始算），自身狀態代價（`cost.self_status`）也當下加在施放者身上；不列入 `legal_actions`（同 `command_summon`），歸在 `SUMMON_ACTION_TYPES` | `engine/actions.py`、`engine/skill_infusion.py`（`do_infuse_skill`） |
| 快照 | `UnitState.infused_skill: InfusedSkill`（技能、施放者、**灌注當下的有效屬性**、技能等級、輪數）與 `infused_round`；同 3-33b 成長快照、陷阱 `attributes` 的做法 | `engine/state.py` |
| 施放 | 召喚物 **下一個自己的回合開始時**（回合開始的狀態、表面、區域、延遲段與被動 `on_turn_start` 之後、行動之前）施放：暫時借用快照屬性、施放者武器與技能等級（`borrowed`，施放完還原），原點＝召喚物位置、射程／視線／形狀都以召喚物計算；佔用召喚物 `summon_infused_cast_ap_cost` = 1 AP（取代一次普攻，之後照常行動）；不付代價、沒有失手反噬 | `engine/skill_infusion.py`（`release_infusion`）、`engine/turns.py`、`engine/skills/interpreter.py`（`run_infused`） |
| 目標依模式 | 集火＝只選範圍含集火目標的選取（打不到就放棄）；守護我＝優先打「威脅施放者」的敵人（敵人武器射程＋速度 ≥ 與施放者距離），沒有就同跟隨；跟隨／待命＝在所有合法選取中評估（敵人數 ×10 − 被波及友方 ×15，次序看敵人損失 HP 比例；支援技能看友方數）。選不到 → `infusion_fizzled(no_target)`；回合開始被暈眩等控制 → `infusion_fizzled(controlled)`；法力與冷卻都不退 | `engine/skill_infusion.py`（`_pick`、`_mode_filter`） |
| 限制 | 每隻每輪 1 次、同時只有 1 招待施放；圖騰、別人的、暈眩中的、**會在施放者本回合結束時到期（來不及施放）** 的召喚物不能灌注；技能禁止：非主動、傳說、召喚（含獻祭召喚物）、改變規則類（改寫規則型原語與規則改變）、複合（`followup`）、陷阱、需要層數、火器（需彈藥）；施放者的資源問題（法力、冷卻、沉默、武器…）照 `resource_problem`。全部附中文原因 | `skill_ban`、`skill_infuse_problem`、`summon_target_problem` |
| 倒下／消失 | 施放前倒下或消失：灌注隨牠離場，法力與冷卻不退（沒有額外事件） | — |
| 預覽 | `/preview` 支援 `infuse_skill`：`Preview.infusion`（召喚物 ID、原點＝目前位置、依目前模式會選的目標、範圍格與單位、`no_target`），`affected_tiles` 改為這個範圍、`ap_cost` = 1 | `engine/preview.py`、`api/schemas.py`（`InfusionPreviewOut`） |
| AI | 效用 AI 的施放者（敵我對稱，含自動代打）評估每個「召喚物 × 可灌注技能」：在假設狀態讓召喚物以快照數字從自己位置施放牠會選的選取，取完整預覽分數 × `infuse_value_permille`（700‰）× 存活機率（HP ÷（HP ＋ 能打到牠的敵人數 × `infuse_threat_damage` 4））；高於其他動作的最佳分數才灌注；被嘲諷時不考慮 | `engine/ai/infuse.py`、`engine/ai/utility.py`（`_best_infusion`）、`content/ai_profiles.yaml` |
| 事件／紀錄 | `skill_infused`「A 把「火焰箭」灌注給 元素之靈1（AP 1，法力 6；下回合開始時施放）」、`infused_skill_cast`「元素之靈1 施放灌注的「火焰箭」 → 盜賊2（從 (2, 3)）→ 影響 1 格」、`infusion_fizzled`「…選不到目標，灌注的「…」失效（法力與冷卻不退）」 | `engine/events.py`、`narrative/events.py` |
| 視圖／API | `UnitView.infused_skill_id`／`infused_skill_name_zh`／`infused`、`BattleView.summon_infuse_ap_cost`；`GET /api/battles/{id}/summons/{sid}/infuse-options`（召喚物或 AP 的問題＋每招主動技能的中文原因）；OpenAPI 與 `schema.d.ts` 重產 | `engine/view.py`、`api/routes/battles.py`、`api/sessions.py` |
| 前端 | 召喚物操控面板每隻多「灌注（1 AP）」（不能用時 `PartTip` 說明＋旁邊文字原因）→ 技能選單（技能列樣式＋圖示；不能灌注的變灰、下方顯示中文原因）→ 滑過技能預覽：地圖標出召喚物原點、目標（紅）與範圍（橘），選單下方一行「從 (2, 3) 施放 → 盜賊2」或選不到目標的警告 → 點一下灌注；列上顯示「待施放：火焰箭（下回合開始時）」，地圖上召喚物頭上畫紫框「灌」徽章；動作標籤「灌注：火焰箭 → 元素之靈1」；說明全用 `PartTip`，沒有原生 `title` | `battle/summonControl.ts`、`ui/SummonPanel.tsx`、`screens/BattleScreen.tsx`、`render/unitLook.ts`、`render/unitSprite.ts`、`battle/drawModel.ts`、`battle/actions.ts`、`styles.css` |
| 格式 | `LOG_FORMAT` `/50 → /51`（PM 合併時定號） | `engine/runner.py` |

## 2. 驗收證據

| 驗收項 | 證據 |
|---|---|
| 扣法力與冷卻時機 | `tests/engine/test_skill_infusion.py`：`test_infusing_costs_one_ap_and_the_skills_mana_and_cooldown_now`（灌注當下 AP −1、法力 −3、冷卻 2，尚無傷害事件）、`test_the_summon_casts_...`（施放時冷卻不重算、召喚物 AP −1） |
| 快照不隨施放者之後變化 | `test_the_snapshot_does_not_follow_the_casters_later_attributes`（灌注後改施放者智力→傷害相同；灌注前改→不同）、`test_the_summon_gets_its_own_attributes_back_after_casting` |
| 原點與射程以召喚物為準 | `test_the_summon_casts_at_the_start_of_its_next_turn_from_its_own_tile`（施放者打不到、召喚物打得到；`origin` = 召喚物位置）、`test_out_of_the_summons_range_the_infusion_fizzles_without_refund` |
| 三種模式的目標選擇 | `test_follow_picks_the_best_selection_for_an_area_skill`、`test_focus_casts_at_the_chosen_target`、`test_focus_on_an_unreachable_target_gives_up`、`test_guard_prefers_the_enemy_threatening_the_caster`、`test_support_skills_target_allies` |
| 每輪 1 次、禁止類別 | `test_once_per_summon_per_round_and_one_pending_skill`、`test_needs_ap_mana_and_an_own_live_summon`、`test_forbidden_skill_kinds_are_greyed_with_reasons`（召喚、傳說、複合、改寫規則）、`test_the_infuse_menu_lists_active_skills_with_reasons`、`test_a_summon_expiring_at_the_end_of_this_turn_cannot_be_infused` |
| 倒下不退還 | `test_a_summon_that_falls_before_casting_loses_the_infusion`、`test_a_stunned_summon_drops_the_infusion` |
| 預覽 | `test_preview_shows_the_range_from_the_summon`（原點、目標、範圍、`no_target`）、API `test_infuse_options_preview_and_infuse` |
| AI 會灌注 | `test_the_ai_infuses_when_only_the_summon_can_reach`、`test_the_ai_does_not_infuse_when_weighted_off` |
| 同種子確定、`--log-json` ＋ `replay` | `test_same_seed_same_result`、`test_an_ai_battle_with_infusions_replays_identically`（dev_summoner 打 bandit_lair，AI 實際灌注、重播終局與事件序列一致）；CLI `trpg battle --map open_plain --seed 7 --ally-build build_summoner,build_trapper --log-json` ＋ `replay` 通過（這場 AI 沒有灌注，只驗證格式） |
| API | `tests/api/test_summon_control_api.py`：選單（召喚技能附「召喚技能不能灌注」）、預覽 `infusion.origin`、灌注事件文字、灌注後選單回報「待施放」；別人的單位回報「不是你的召喚物」 |
| 前端 | `client/src/battle/summonInfuse.test.ts`（灌注鈕的限制、選單變灰原因、召喚物側問題、動作與標籤、預覽說明與紅框、待施放文字、「灌」徽章）；`tsc`、vitest 737 通過、`pnpm build` 成功 |

被迫改的既有測試：`LOG_FORMAT` 斷言（9 個檔）、`test_vault.py` 的基本動作分類（多了 `infuse_skill`）、`test_routes.py` 的預覽欄位集合（多了 `infusion`）。

### 2.1 瀏覽器實測（`dev_summoner`，吊橋深淵，自己起的伺服器 8767 埠；未動 8000 埠，結束後已關閉）

- 同 3-33b／3-33c：**畫布的滑鼠點擊不會觸發**，召喚與按鈕點擊改用 `javascript_tool`（對畫布送 pointer 事件、對按鈕 `click()`、滑過用 `mouseover`）；畫面與截圖是真的。
- 召喚元素之靈 →「召喚物操控」多了「灌注（1 AP）」（`docs/phases/img/3-33d-summoned.jpg`）。
- 按「灌注」→ 選單：「召喚元素之靈」變灰並顯示「召喚技能不能灌注：召喚元素之靈」、「火焰箭」可用 → 滑過火焰箭：地圖標出召喚物原點與目標盜賊2，選單下方「從 (2, 3) 施放 → 盜賊2」（`3-33d-infuse-preview.jpg`）。
- 點火焰箭 → 紀錄「冒險者 把「火焰箭」灌注給 元素之靈1（AP 1，法力 6；下回合開始時施放）」、列上「待施放：火焰箭」、灌注鈕灰掉附原因、召喚物頭上紫框「灌」（`3-33d-pending-badge.jpg`）。
- 結束回合 → 紀錄「元素之靈1 施放灌注的「火焰箭」 → 盜賊2（從 (2, 3)）→ 影響 1 格」，盜賊2 受傷燃燒，徽章消失（`3-33d-cast.jpg`）。
- **6.5.1 浮動卡**（面板標題「召喚物操控 ⓘ」的 `PartTip`，內容已含灌注說明）：1600×900 與 800×600 各跑一次腳本——滑入 60ms 時未顯示、約 300ms 顯示（延遲）→ 離開觸發元素移到卡片上仍開著 → 點一下釘住（`pinned`）→ 滑鼠離開仍開著 → Esc 關閉，全部通過；卡片高 311px，兩種尺寸都在視窗內、**沒有可捲動的內容**（「捲到底」無法驗證，同 3-33c）。卡片 portal 在 body（`3-33d-float-card-1600.jpg`）。800×600 時操控面板本身內容超出高度、面板內捲動正常（`3-33d-infuse-800x600.jpg`）。
- 截圖皆為 jpg（瀏覽器工具只輸出 jpg）。

## 3. 規則與行為的取捨（保守做法）

1. **「取代或先於普通行動」→ 先於、佔 1 AP**：召喚物回合開始時先施放，扣牠 1 AP（等同一次普攻），之後照常行動（AP 3 時還能打 2 次）。
2. **目標選擇在引擎內（確定性評估），不用效用 AI**：灌注是在回合開始時強制結算的（同 3F-4b 延遲段），引擎不能讀 AI 權重；評估規則見第 1 節。預覽用同一個函式，所以預覽的選擇與「當下的狀態下會選的」一致（實際在下回合開始時才選）。
3. **借用的數字**：快照屬性＋施放者武器（武器技的傷害骰、命中、「武器射程」都是施放者的）＋技能等級；**不套施放者的修正規則（被動修正、裝備的技能強化）與戰場變奏**；召喚物自己的狀態（增益、沉默、隱蔽）照常生效。施放期間被反應打到時，召喚物的防禦也暫時用快照屬性。
4. **不觸發施放者的「施放時」被動**（`on_cast_tag`、`copy_skill` 的施放紀錄、`cast_tag_this_turn`），召喚物也不觸發；灌注事件是 `skill_infused`，不是 `skill_used`。
5. **禁止清單**比規格多了：陷阱技能、需要層數的技能、火器技能（需彈藥）、非主動（姿態、常駐類）；以及「本回合結束就到期」的召喚物（來不及施放，避免白付法力）。
6. **暈眩時**：回合開始被控制就放棄（`controlled`），不保留到下一回合。

## 4. 待 PM 決定

1. **`LOG_FORMAT` 定為 `/51`**（3-33e1、3-32b 若也改格式，合併時依實際順序定號）。
2. **AI 權重初值** `infuse_value_permille` 700、`infuse_threat_damage` 4，召喚物施放佔 1 AP（`summon_infused_cast_ap_cost`）、灌注 1 AP，都未經模擬；建議 3-33g 對照模擬時看灌注次數與召喚流輸出。
3. **目標選擇用引擎內的簡單評估**（第 3.2 點），不是效用 AI 的完整評分；若要用 AI 評分需把 AI 權重放進規則集，或改成召喚物自己出的動作。
4. **借用的範圍**（第 3.3 點）：武器也借、修正規則與變奏不借；是否改成「只借屬性、用召喚物自己的武器」請決定。
5. **額外禁止**的技能類別（第 3.5 點）是否接受；尤其陷阱與火器技能。
6. **倒下或消失時沒有事件**（灌注隨單位離場）；若要在紀錄寫「灌注失效」需加觸發。
7. **瀏覽器實測缺口**：畫布點擊靠 JS 事件；浮動卡內容不夠高，「卡片內捲到底」未能驗證；CLI 抽查的那場 AI 沒有灌注（AI 灌注的重播由 pytest 驗證）。

## 5. noqa

沒有新增複雜度類 noqa（`C901`／`PLR0911`／`PLR0912`／`PLR0915`）。新增 `# noqa: PLC0415`（函式內 import，避免循環匯入）：`skill_infusion.release_infusion` 匯入技能解譯器（同 `delayed._release`）；測試內數處（沿用既有作法）。

## 6. 最終檢查

- 完整 `uv run python scripts/check.py` **全部通過**：ruff check、ruff format --check、mypy、lint-imports（6 契約）、pytest **4442 通過**（9 分 9 秒）、client typecheck、vitest 737 通過；另 `pnpm build` 成功。
- CLI：`trpg battle --map open_plain --seed 7 --ally-build build_summoner,build_trapper --log-json` ＋ `trpg battle replay` 驗證一致（139 個動作、424 個事件）。
