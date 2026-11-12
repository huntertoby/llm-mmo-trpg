# Phase PB-1b 完成報告｜部位系統段 1b：AI（隊友挑部位、頭目護背）

> 規格：`docs/phases/PhasePB-1計畫.md` 第 0 節（R1～R9 使用者「照建議」、T1～T16 照建議）與第 5 節（PB-1b）；PB-1a 報告末節開發 PM 裁定照辦。設計依據 `docs/design/05-戰鬥.md` 5.12.2 第 11 點（D11、D12）。
> 基準：本機 main `b004636e`（含 PB-1a，worktree 以 `git merge --ff-only main` 帶入）。本段只做 1b；前端（1c）、數值工坊（1n）、模擬報表（1d）沒有動。

## 1. 做了什麼

| commit | 內容 |
|---|---|
| `01328a8f` AI 本體＋測試 | `content/ai_profiles.yaml` 加 `parts:`（T13 的鍵與占位值，註解寫「占位，NW-3 開放後由使用者調」）；schema `PartAiRules`（`src/trpg/content/environment.py`；`AiProfileTable.parts`，`guard_back_bonus`、`near_break_permille` 另外填進每個行為模式的 `AiWeights`，同 `facing:` 的做法）；新檔 `src/trpg/engine/ai/parts.py`（`picks_parts`、`part_variants`、`part_score`、`guard_back_extra`）；`UtilityAI.rank` 最後呼叫 `_with_parts` 展開部位變體（`ai/utility/policy.py`）；`position._facing_terms` 的 `back_exposed` 多加 `guard_back_extra`；新測試 `tests/engine/test_parts_ai_pb1.py`（12 項） |
| `c364a8d8` 上手筆記 | `docs/dev/上手-引擎戰鬥結算.md`：第一節 `ai/` 列加 `parts.py`；第二節「AI 怎麼選招」加第 5 點「部位變體」；第四節加第 18 點「改 AI 的不變比對」；第五節頭目部位列加 `test_parts_ai_pb1.py` |
| （本報告） | `docs/phases/PhasePB-1b報告.md` |

**規則怎麼落地（對照規格第 5 節）**

- 5.1 價值表：`parts: {seal_skill: 8, interrupt_charge: 10, stat_down: 4, control: 6, stop_mechanic: 8, priority_bonus: 6, guard_back_bonus: 3, near_break_permille: 500}`（全部是 T13 的占位）。
- 5.2 誰挑部位：`picks_parts`——行動者 `team is Team.ALLY`、不是召喚物（R9），而且場上有任何帶 `parts` 的單位。效用 AI 不知道誰是真人，所以「玩家方由效用 AI 控制的單位」就是玩家方全部經過 `UtilityAI` 的單位（隊友、影子、自動推進時的玩家角色）。
- 5.2 變體：對 `rank` 已評分的每個 `Attack`／`UseSkill`（`target_part` 為空），用 PB-1a 的 `part_targets(state, action)` 取 `ok` 的部位，`model_copy(update={"target_part": ...})` 產生變體，依部位 ID 排在本體後面。目標沒有部位時 `part_targets` 回空，什麼都不產生。
- 5.2 分數：變體跑自己的 `score_action`（完整預覽；部位護甲不同時命中率也跟著變），再加 `part_score`：
  - 破壞效果價值＝`on_break` 各項的 `parts.<type>` 相加；
  - 進度＝預覽最少後果裡這個部位的 `part_damaged.amount` 合計 ÷ 部位剩餘血量，上限 1（`Fraction`）；
  - 最多後果有這個部位的 `part_broken`，而且「能封下一招」（`seal_skill` 的招在頭目目前的 `skills`、還沒封、`resource_problem` 為 `None`＝冷卻外、法力等資源夠）或「能打斷」（頭目身上有 `charging`，部位有 `interrupt_charge`，或 `seal_skill` 封的就是蓄力中那一招）時加 `priority_bonus`。
- 5.2 同分：`UtilityAI.__call__` 取「嚴格大於」的最高分，變體排在本體後面、彼此依部位 ID，所以同分本體優先、再照部位 ID（D11）。
- 5.3 頭目護背：`guard_back_extra(unit, w)`——單位有 `reach: behind`、還沒破、剩餘血量 × 1000 ≤ 部位最大血量（`max_part_hp(unit.max_hp, part)`）× `near_break_permille` 的部位時回 `guard_back_bonus`，否則 0。`_facing_terms` 在原本扣 `back_exposed` 的同一個條件下多扣這個數。沒有部位的單位一律 0。
- 5.4 候選數：採「**在 `skill_candidates` 截斷之後才展開**」——變體只從已經評分的候選產生，另計、不佔 `skill_candidates`／`move_candidates` 的名額，本體候選一個都不少。

## 2. 逐條驗收（規格 5.5）

`tests/engine/test_parts_ai_pb1.py`（霧鎖真人正式內容、實際跑效用 AI 與預覽）：

| 規格 5.5 | 測試 |
|---|---|
| 價值表占位值、填入行為模式 | `test_the_value_table_has_placeholder_values` |
| 變體排在本體後、依部位 ID | `test_variants_follow_the_body_in_part_id_order`（歸一、背後格：本體、氣海、長劍、拂塵） |
| 歸一中蓄力蓄力斬、長劍一下打得破 → 選長劍 | `test_a_charging_boss_makes_the_sword_the_pick_when_it_can_break` |
| 拂塵快破、霧遁可用 → 優先拂塵 | `test_a_nearly_broken_whisk_is_picked_while_mist_shift_is_ready` |
| 優先分的條件（下一招／冷卻中） | `test_priority_needs_the_next_skill_or_a_charge`（可用＝價值＋優先分；冷卻中只剩價值 × 進度） |
| 進度比例＝最少後果部位傷害 ÷ 剩餘血量 | `test_progress_is_part_damage_over_remaining_hp` |
| 打不到 → 本體 | `test_no_reachable_part_means_the_body`（劍陣、拂塵已破：沒有變體） |
| 同分本體優先 | `test_ties_keep_the_body`（價值全設 0：變體與本體同分，選本體） |
| 召喚物與敵方不挑部位（R9） | `test_summons_and_enemies_never_pick_parts` |
| 頭目背後部位快破時背對攻擊者扣分增加（固定場面比分數） | `test_the_boss_guards_its_back_when_the_dantian_is_nearly_broken`（氣海剩一半：位置價值正好少 `guard_back_bonus`；破了之後回到 0） |
| 確定性 | `test_the_ai_is_deterministic_with_parts` |
| 沒有部位的場面 `rank` 逐字不變 | `test_scenes_without_parts_rank_exactly_as_before`（每個候選都在 `legal_actions` 裡、沒有 `target_part`；部位價值表全 0 與預設兩種 `rank` 的動作與分數完全相同） |

## 3. 不變比對（規格 5.6）

腳本在 scratchpad（未 commit），比照 PB-1a：地圖預設陣容、效用 AI、`max_rounds=30`；改前（`b004636e`，`content/` 與程式都未改）與改後（`01328a8f`）各跑一次，每場比對完整事件 JSON、步驟、最終狀態 JSON（含 `rng_state`、輪數、勝方）。**沒有剝掉任何鍵。**

- 8 張地圖 × 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12：`battles=46 events=20493`。
- **除 `cloud_summit` 外 34 場 `different=0`**（`molten_heart_pit`、`rift_gate` 的種子 1～12，其他 6 張圖的種子 1、2）。
- **`cloud_summit` 12 場全部變了（預期：隊友開始打部位）**，勝方 12 場都不變：

| 種子 | 事件數 改前 → 改後 | 輪數 | 勝方 | 打部位的動作 | `part_damaged` | 破壞 |
|---|---|---|---|---|---|---|
| 1 | 516 → 471 | 6 → 5 | 我方 | 5 | 6 | 2 |
| 2 | 464 → 469 | 5 → 5 | 敵方 | 3 | 3 | 1 |
| 3 | 460 → 465 | 5 → 5 | 敵方 | 3 | 3 | 1 |
| 4 | 522 → 599 | 6 → 7 | 敵方 | 4 | 3 | 0 |
| 5 | 458 → 463 | 5 → 5 | 敵方 | 5 | 3 | 1 |
| 6 | 576 → 543 | 9 → 7 | 敵方 | 9 | 5 | 1 |
| 7 | 480 → 541 | 6 → 7 | 敵方 | 5 | 4 | 1 |
| 8 | 587 → 533 | 7 → 6 | 我方 | 8 | 6 | 2 |
| 9 | 366 → 372 | 4 → 4 | 敵方 | 4 | 3 | 1 |
| 10 | 480 → 542 | 7 → 8 | 敵方 | 2 | 3 | 1 |
| 11 | 578 → 583 | 6 → 6 | 我方 | 11 | 4 | 1 |
| 12 | 709 → 613 | 11 → 8 | 敵方 | 8 | 3 | 1 |

  - 平均事件差 −0.2（絕對值平均 37.8）。12 場合計：打部位的動作 67 次（拂塵 55、長劍 12；氣海 0——要站背後近戰才選得到，預設陣容沒有走到那一格的時機）；`part_damaged` 46 次（拂塵 37、長劍 9；其餘沒命中）；破壞 13 次（拂塵 11、長劍 2），每次拂塵破都封住霧遁（`skill_sealed` 11）。
- **三個雜湊**（`content/ai_profiles.yaml` 改了）：

| | 改前 | 改後 | 改後把 `ai_profiles.yaml` 換回舊檔 |
|---|---|---|---|
| `hash_ruleset` | `a2fb31c0d6d1fd3f8a5740cdc77d73422056ec5a060f47515216d1db6f710ce0` | 同左 | 同左 |
| `ruleset_hash`（一輪存檔） | `c08ffa8eb8c3d1fa2046ededf92f822721f5d682fe5bc97ff76b46bdce6cadd6` | `333ea4571f15c6847b848ff7dcdf1b8cbe8ce82e72f472fdffa7893d526e18f1` | `c08ffa8e…cadd6`（回到改前） |
| `content_digest`（世界日誌） | `bfaa6d506c4bbc5cd397e2186099deb4344a3c564864f08eb27c27b9b606d09a` | `86f650e4166130812b251593d315e4dd58d7ad05135cd428ab8b67c22bdb2a3f` | `bfaa6d50…6d09a`（回到改前） |

  「換回舊檔」的做法：把 `content/` 複製到暫存、只用 改前的 `content/ai_profiles.yaml`（`b004636e`） 蓋掉那一檔，`load_library(暫存)` 重算；同一份複本換回新檔則算出改後的值，證明複製本身不影響、變動只來自 `ai_profiles.yaml`。
- `LOG_FORMAT` 不升：本段沒有改事件、動作、狀態欄位與結算規則（只改 AI 的選擇；`target_part` 欄位 1a 已有，紀錄格式仍是 `/115`）。

## 4. 測試與檢查（結束碼）

交件前在 `c364a8d8`（程式與 `01328a8f` 相同）跑，每個指令的結束碼分開記：

| 指令 | 結束碼與結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1499 個檔無問題） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| AI 相關 pytest（`-n 6`）：`test_parts_ai_pb1.py`、`test_ai_utility.py`、`test_ai_weights.py`、`test_skill_ai.py`、`test_support_ai.py`、`test_status_ai.py`、`test_displace_ai.py`、`test_boss_parts_pb1.py`、`test_mist_lock_parts_pb1.py`、`test_determinism.py`、`tests/world/test_enemy_ai_moves_149.py`、`test_shard_lord_first_phase.py`、`test_boss_battle.py`、`tests/content`、`tests/test_architecture.py` | 0：3202 passed |
| 其他受影響範圍（`-n 8`）：`tests/world`、`tests/api`、`tests/sim`、`tests/roguelite`、`tests/cli`（非 slow）、`test_boss_phases.py`、`test_enemy_skills_149.py`、`test_runner_advance.py`、`test_ruleset_hash.py`、`test_boss_triggers.py`、`test_state_clone.py`、`test_preview.py` | 0：2907 passed、1 skipped |
| `uv run pytest -n 8 tests/cli/test_output_snapshots.py -m slow` | 0：24 passed，**0 個鍵變動、沒有重產** |
| `trpg battle --map cloud_summit --seed 2 --log-json` ＋ `trpg battle replay` | 0／0：「重播驗證通過：96 個動作、469 個事件，最終狀態一致」；紀錄裡有 3 個帶 `target_part` 的動作 |

沒有跑完整 `scripts/check.py`、`trpg sim`（守則 11；PM 全量期間）。不變比對的 46 場對戰經開發 PM 同意後單程序跑。

## 5. 快照與既有測試的變動

- **沒有改任何既有測試**、沒有換固定種子：`cloud_summit` 相關的固定種子測試（`tests/world/test_boss_battle.py`、`test_enemy_ai_moves_149.py`、`test_season_boss.py`、`test_boss_phases.py` 等）全部照舊成立。
- CLI 快照 0 個鍵變動（快照裡沒有帶部位頭目的地圖）；雜湊、夾具沒有重產。

## 6. 新增的複雜度 `# noqa`

- `ai/utility/policy.py::UtilityAI._with_parts`：`# noqa: PLR0917`（位置參數 6 個）。理由：要把 `rank` 已算好的 `profile`、`before`、`orders`、`walk` 原樣傳給 `score_action`，和同檔既有的 `_score_other`、`_skill_candidates`（也是 `# noqa: PLR0917`）同一個形狀；沒有複雜度（C901／PLR0912）類的新增 `# noqa`。`rank` 原本只差一個分支就超過 `PLR0912`，所以「行動者會不會挑部位」的判斷放在 `_with_parts` 裡，不加在 `rank`。

## 7. 規格沒寫到、採保守做法的地方

1. **變體的「本體分」用變體自己的預覽分數**，不是拿本體動作的分數再加部位分。規格 5.2「變體跑 `preview`，分數＝本體分＋部位分」；部位有 `armor_bonus` 時命中率不同，用本體的分數會算錯。副作用：變體預覽裡的破壞效果事件（例：`status_removed`、`followup_cancelled`）若本身有 AI 收益，會再算一次——霧鎖真人的三個部位目前在 `_gains` 裡沒有對應收益（封招、停機制、降傷都不是 `status_values` 裡的狀態），實際不重複。
2. **部位分不乘命中率**：照規格公式字面（價值 × 進度 ＋ 優先分）；本體分已含命中率。部位分要不要也乘命中率列入待決。
3. **部位分不乘行為模式的 `damage` 權重**（`status_values` 會乘）：同上照字面；占位值的量級由使用者在數值工坊調。
4. **「快破」的最大血量**用 `max_part_hp(目前 max_hp, part)` 重算（開場值沒有另存）；戰鬥中 `max_hp` 改變時門檻跟著變。霧鎖真人戰鬥中沒有改 `max_hp` 的效果。
5. **頭目護背不看部位有沒有露出**：照規格字面「有 `reach: behind` 的部位、剩餘血量 ≤ 門檻」；已破的不算。
6. **「玩家方」＝`Team.ALLY`**；第三方（三方混戰）的單位不挑部位。
7. **瞄準（`Aim`）的估值只看本體候選**：`_score_aim` 在變體展開之前算，部位變體不影響瞄準的分數。
8. **蓄力武器普攻、召喚物、範圍技等**能不能帶部位完全交給 PB-1a 的 `part_targets`（不另寫規則）。

## 8. 影響

- 雲頂觀（`cloud_summit`）頭目戰的隊友開始打拂塵、長劍（見第 3 節）；勝方在比對的 12 場都不變。其他地圖逐字不變。
- `ai_profiles.yaml` 改了 → 一輪存檔的 `ruleset_hash`、世界日誌的 `content_digest` 都變：重開伺服器後進行中的一輪從頭開始、舊世界日誌標成不能重播（同 PB-1a）。戰鬥紀錄格式沒變。
- **請使用者重開伺服器檢查的重點**：介面還點不到部位（1c）；可以看雲頂觀頭目戰的戰鬥紀錄裡隊友「打拂塵」、拂塵破了之後真人不再霧遁。

## 9. 待 PM 決定

1. 部位分要不要乘命中率（目前不乘，照規格公式；第 7 節第 2 點）。
2. 部位分要不要乘行為模式的 `damage` 權重，和 `status_values` 同一個量綱（目前不乘；第 7 節第 3 點）。
3. 變體分數用變體自己的預覽（含部位護甲的命中率），破壞效果事件若日後有 AI 收益會和部位分重複算（目前霧鎖真人沒有；第 7 節第 1 點）。
4. 頭目護背不看部位有沒有露出（照字面；第 7 節第 5 點）。
5. 第三方陣營（三方混戰）不挑部位，只有 `Team.ALLY`（第 7 節第 6 點）。
6. 預設陣容 12 場氣海一次都沒被打（要背後近戰），拂塵破 11 次、長劍破 2 次；是否需要隊友主動繞背打氣海（目前只有既有的 `backstab` 位置分，沒有為部位加站位分），留給 PB-1d 報表再看。
7. `parts:` 的 8 個值全是 T13 占位，等 NW-3／PB-1n 開放後由使用者調。
