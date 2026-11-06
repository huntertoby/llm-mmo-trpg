# Phase 3D-8d 報告：朝向與背刺（朝向、`from_behind`、瞬步 `shadowstep`、潛行偷襲 `self_concealed`）

## 1. commit

| commit | 內容 |
|---|---|
| b7997f2 | 引擎與內容：`UnitState.facing`、`engine/rules/facing.py`（朝向、背後格、開場朝向）、主動移動與攻擊／施放後轉向；背刺與潛行偷襲加成（`combat.positional_bonus`，`attack_rolled.backstab`／`ambush`）、偷襲後移除隱蔽（`status_removed` 原因 `ambushed`）；條件 `from_behind`、`self_concealed`；原語 `shadowstep`（`landing: choose \| behind`，移動方式 `shadowstep`）；預覽命中率含背刺、`Preview.backstab` 與說明；AI 權重 `backstab`／`back_exposed` 與瞬步估計；`sim maps` 的「背刺與偷襲」計數；示範技能「瞬步背刺」「暗影突襲」、build 調整；`tests/engine/test_facing_backstab.py`（27） |
| be97881 | 視圖 `UnitView.facing`、API `PreviewOut.backstab`、CLI 單位列「面向東→」；`LOG_FORMAT` `/31` → `/32`；OpenAPI、`schema.d.ts`、CLI 快照重錄；`tests/api/test_shadowstep_api.py`（5）、CLI 朝向測試 |
| be665f6 | 網頁：單位圖示的朝向箭頭、單位資訊的「朝向（背後格）」、一般瞬步的兩段選取提示、預覽落點「瞬」與文字；`SkillCard.effect_ids`；vitest `facing.test.ts`（6） |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 朝向（9.1）

- `UnitState.facing`（`north`／`east`／`south`／`west`，預設 `east`），`clone`、JSON 序列化、重播都包含；`UnitView.facing` 給網頁與 API。
- **開場**：每個陣營面向「敵方起始位置的重心」相對「己方起始位置的重心」的方向（主軸；兩軸相同取左右）；算不出來時我方朝東、敵方朝西（`opening_facing`）。目前所有地圖都是我方在左、敵方在右，所以實際上是我方朝東、敵方朝西。戰鬥中出現的援軍面向場上存活敵人的重心；召喚物與召喚者同向。
- **自動更新**：
  - 主動移動（`arrive` 的 `walk`／`dash`／`leap`）：面向這一步的方向。直線衝撞 `charge_through` 的每一步是 `dash`，所以面向衝撞方向；跳躍面向起點 → 落點的主軸。
  - 瞬步落地後面向目標。
  - 普攻（含藉機攻擊、監視射擊等反應普攻）結算完後面向目標；攻擊物件面向物件。
  - 對單位（或物件）施放的主動技能、`shape: single` 的反應技：結算完後面向「施放時」主要目標的位置。以格子、方向或自身為目標的技能不改朝向；被動、陷阱、區域的效果不改。
  - 被推、被拉、傳送（自己 `teleport` 與被傳送 `teleported`）、交換位置都不改朝向；被攻擊的一方不轉身。
- 「兩軸距離相同」時取左右（沿用 `geometry.axis_direction`）。
- 朝向沒有新增事件：改變都由既有事件（`unit_moved`、`attack_rolled`、`skill_used`）推得，狀態由重播重建；視圖直接帶 `facing`。
- **確認「朝向只影響背刺相關的結算」**：把 `backstab_hit_bonus`、`backstab_crit_range_bonus`、`ambush_hit_bonus` 與 AI 的 `backstab`／`back_exposed` 都設為 0（另一份 content 複本），用目前的程式跑，和 HEAD（37ac189，`git archive` 匯出的舊程式）比對 `--log-json` 的動作與事件（去掉新欄位 `backstab`／`ambush`）：11 場（CLI 快照的 7 場，加上 `dark_forest` 3 `build_ranged`、`swamp` 1 `build_trapper`、`open_plain` 2 `build_winged`、`narrow_halls` 1 `build_ranged`、`dark_forest` 0 `build_charger`）**全部逐事件一致**。所以朝向本身只透過背刺、潛行偷襲與 AI 的朝向權重影響結果。

### 2.2 背刺、瞬步、潛行偷襲（9.2）

| 項目 | 實作 |
|---|---|
| `from_behind` | 施放者站在目標的 **相鄰背後格**（目標朝向的反方向那一格；只算相鄰，見待決 #2）。單位條件（`_UNIT_CONDITIONS`），可用在技能條件、效果條件與修正規則；`harshness: common`、最低 rare |
| 背刺加成 | `content/rules/core.yaml`：`backstab_hit_bonus: 2`、`backstab_crit_range_bonus: 1`。命中判定時（`roll_attack` → `positional_bonus`）若攻擊參數是近戰（`profile.melee`：普攻用近戰武器、武器技且武器是近戰）且攻擊者在目標背後格，命中 +2、暴擊範圍擴大 1（單手劍 20 → 19–20、匕首 19 → 18–20）。Boss 照常適用。`attack_rolled.backstab`（加值）記錄；紀錄文字「X 從背後攻擊 Y：… 背刺 +2 …」「從背後以「瞬步背刺」攻擊」 |
| 預覽 | 普攻與技能的命中率、暴擊率都含背刺與偷襲（技能以出手位置計算，瞬步、衝鋒後的位置也對）；`Preview.backstab`／`PreviewOut.backstab` 列出會被背刺的單位；`notes` 加「背刺 盜賊2：命中 +2、暴擊範圍 +1（從背後近戰攻擊）」「潛行偷襲：隱蔽中出手，命中 +2（攻擊結算完後脫離隱蔽）」，網頁預覽直接顯示 |
| `shadowstep` | `{type: shadowstep, landing: choose \| behind}`；結構型、rare、`budget_basis: fixed` 4 點、`acts_on: caster`；必須是技能第一個效果，`choose` 搭配 `unit_then_tile`、`behind` 搭配 `single`（schema 檢查）。目標必須是敵人。**choose**：兩段選取（敵人 → 他相鄰的合法格），沿用 `unit_then_tile` 的候選列舉與網頁兩段選取。**behind**：目標背後格；被占或不可站立時改為相鄰的其他合法格中離背後格最近的（Chebyshev 距離，所以先左右兩側、再正面；同距離依上、右、下、左），都沒有則不能施放（不在 `legal_actions`，`IllegalActionError`「身旁沒有可以瞬步落腳的空格」）。落點條件：在地圖內、可站立、不是致命地形、沒有其他單位、與目標高度差 ≤ `melee_height_limit`。移動方式 `shadowstep`：不墜落、不觸發藉機攻擊／`enemy_enters_adjacent`／監視射擊、不觸發 `on_enter_surface` 被動；落點的陷阱與表面照常。落地後面向目標，之後的效果以落點結算（影響範圍原點改為落點），所以接在後面的近戰傷害吃到背刺。定身、倒地不能施放 |
| `self_concealed` | 施放者帶 `concealed` **狀態**（黑暗表面、草叢不算，見待決 #4）。施放者條件（`CASTER_CONDITIONS`）；`harshness: harsh`、最低 rare |
| 潛行偷襲加成 | `ambush_hit_bonus: 2`：攻擊者帶 `concealed` 狀態時每次命中判定 +2（`attack_rolled.ambush`）。現有規則沒有「攻擊後移除隱蔽」，所以新增：普攻結算完、或一次施放（主動技能、反應技）的所有命中判定與效果結算完之後，若有任何一次判定是偷襲，移除 `concealed`（`status_removed` 原因 `ambushed`，紀錄「X 的「隱蔽」在偷襲之後解除了」）。多目標技能每個目標都吃到加成；效果條件 `self_concealed` 在同一次施放內都成立 |

- 預算：`shadowstep` 固定 4 點；條件折扣用既有倍率（common 0.85、harsh 0.6）。背刺加成本身不計價（見待決 #6）。
- 骨架：`strike` 的形狀加 `unit_then_tile`（只給手寫技能）、附帶效果加 `shadowstep`；`displace` 核心加 `shadowstep`；隨機組合器不產生（`_HAND_WRITTEN_PRIMITIVES`）；機制標籤歸 displace。
- 修正規則：`from_behind` 可用在 `hit_bonus`、`damage_permille` 等（測試 `test_from_behind_condition_and_modifier`）；選目標之前就決定的修正（`SELF_ONLY_CHANGES`）仍只允許 `self_hp_below`。

### 2.3 示範技能與 build

| 技能 | 內容 | 預算 |
|---|---|---|
| 瞬步背刺 `skill_shadow_backstab`（rare、strike、武器技近戰、AP 2、`single` 射程 4、法力 5、冷卻 3） | `shadowstep landing: behind` ＋ 傷害 100% ＋ 傷害 50%（條件 `from_behind`：真的落在背後時才有；背後被占改落側面時沒有） | 85.0% |
| 暗影突襲 `skill_shadow_ambush`（rare、strike、武器技近戰、AP 2、`unit_then_tile` 射程 4、法力 6、冷卻 3） | `shadowstep landing: choose` ＋ 傷害 80% ＋ 傷害 80%（條件 `self_concealed`） | 86.3% |

- `build_assassin`（主動欄位已滿）：瞬步背刺換下先發制人、暗影突襲換下撕裂打擊（撕裂打擊仍在 `hero_fighter`）；先發制人改由 `build_gambler` 的空欄位接收。刺殺英雄原有的閃現（隱蔽 2 回合）、`flanker` AI 保留，閃現 → 暗影突襲是潛行偷襲的連招。
- 一般瞬步沒有另做「純瞬步」技能，`choose` 的示範就是暗影突襲（它同時示範 `self_concealed`）。

### 2.4 AI

- `content/ai_profiles.yaml` 新增表格層級 `facing: {backstab: 4, back_exposed: 3}`，填入每個行為模式的 `weights`（敵我同一套；模式自己列出的優先）。位置價值（`_facing_terms`）：
  - `backstab`：**近戰單位** 站在相鄰敵人的背後格，每個 +4（移動終點偏好繞背）。
  - `back_exposed`：結束移動時的朝向以「面向最近的敵人」近似（同距離取 ID 小者），背後格站著近戰敵人時 −3。
- 技能候選估計：瞬步 = 3 ＋（落在背後 2）＋ 落點（面向目標）的位置價值變化；之後照常跑完整預覽評分。
- `trpg sim maps --seeds 5 --ally-build build_assassin`（50 場）：每張地圖都有背刺紀錄，例如 `dark_forest`「背刺與偷襲（整批合計）：我方背刺 16 次、敵方背刺 22 次、我方偷襲 1 次」、`narrow_halls`「我方背刺 26 次、敵方背刺 7 次、我方偷襲 5 次」；瞬步背刺 0.6–1.2 次／場、暗影突襲 0–0.6 次／場；異常全部「無」。

### 2.5 網頁（PM 用瀏覽器驗收）

- 單位圖示外緣有白色小三角形箭頭（尖端指向朝向；倒下的單位不畫）；滑過單位的資訊面板多一行「朝向：東 →（背後 (2, 3)）」。
- 一般瞬步的兩段選取：第 1 段「點選要瞬步過去的敵人」、第 2 段「已鎖定盜賊2，點選要落在他身旁哪一格（落在他背後可以背刺）」；預覽在落點標「瞬」、文字「瞬步：刺殺英雄 瞬間出現在 (5, 3)，落地後面向目標（不會被藉機攻擊）」，命中說明列出「背刺 …」。分辨一般瞬步與傳送他人靠新增的 `SkillCard.effect_ids`（效果原語代碼）。
- `client/dist` 已用 `corepack pnpm -C client build` 重新建置；我只用 API 層驗證過以下兩個序列，沒有用瀏覽器實機操作。

**重現步驟（共用）**：`uv run python scripts/play.py`，開始畫面選 build「刺殺」（`build_assassin`）、地圖「開闊平原」（`open_plain`）、種子 **0**，開戰。第 1 輪輪到主角時（主角在 (0, 3) 朝東；盜賊2 已走到 (4, 3)、朝西，背後格是 (5, 3)；隊友弓手在 (4, 4)）：

1. **瞬步背刺**：點技能列「瞬步背刺」（AP 2、法力 5、冷卻 3）→ 點盜賊2 (4, 3)。預覽：落點 (5, 3) 標「瞬」、命中 70%、暴擊 15%（匕首 18–20）、說明「背刺 盜賊2：命中 +2、暴擊範圍 +1（從背後近戰攻擊）」。施放後紀錄「刺殺英雄 瞬步到 (5, 3)」「刺殺英雄 從背後以「瞬步背刺」攻擊 盜賊2：d20=2 … 背刺 +2 = 6（目標 11）→ 失手」，主角的箭頭朝西（面向盜賊2）。
2. **一般瞬步（暗影突襲）**：重開同一場（同 build、地圖、種子 0），點「暗影突襲」→ 第 1 段點盜賊2 (4, 3) → 第 2 段框出 (4, 2)、(5, 3)、(3, 3) 三格（(4, 4) 被隊友占住）。點 (5, 3)：預覽有背刺說明；點 (3, 3)：沒有背刺說明，命中 60%。以 (3, 3) 施放：紀錄「刺殺英雄 瞬步到 (3, 3)」「以「暗影突襲」攻擊 盜賊2 … → 失手」，主角箭頭朝東。

## 3. 驗收條件逐條（9.3）

### 驗收 1：朝向

| 項目 | 證據 |
|---|---|
| 開場 | `test_opening_facing_faces_the_enemy_start_zone`（左右、上下、重心重合的預設）、`test_facing_between_takes_the_major_axis_and_prefers_left_right_on_ties`；CLI `test_the_unit_table_shows_each_units_facing` |
| 步行與衝鋒後更新 | `test_walking_faces_the_last_step`、`test_dash_leap_and_charge_face_the_way_they_moved`（衝鋒、跳躍、直線衝撞） |
| 攻擊後面向目標 | `test_attacking_and_casting_on_a_unit_face_the_target`（普攻、技能；被攻擊者不轉身） |
| 強制位移不改 | `test_forced_moves_teleports_and_swaps_keep_facing`（推擊、閃現傳送） |
| 序列化與重播 | `test_facing_round_trips_through_json_and_clone`、`test_ai_battle_with_backstabs_replays`（`dark_forest` 種子 3、`build_assassin`，`重播驗證通過`）；`tests/engine/test_state_clone.py` 自動涵蓋新欄位 |
| 舊行為只因朝向改變的部分 | 見 2.1 的比對（加成與 AI 權重歸零時 11 場逐事件一致）與第 4 節的快照說明 |

### 驗收 2：背刺

| 項目 | 測試 |
|---|---|
| 背後格近戰有加成、側面與正面沒有 | `test_a_melee_attack_from_behind_gets_hit_and_crit_bonuses`（背後 +2、自然 19 暴擊；側面自然 19 只命中）、`test_the_back_tile_is_opposite_the_facing` |
| Boss 也適用 | `test_bosses_can_be_backstabbed`（`bandit_boss`） |
| 遠程沒有 | `test_ranged_attacks_never_backstab` |
| 預覽與紀錄顯示「背刺」 | `test_the_preview_and_log_show_the_backstab`（命中率差 2/20、暴擊 2/20、`backstab == (U2,)`、notes 與紀錄文字） |
| 條件與修正規則 | `test_from_behind_condition_and_modifier` |

### 驗收 3：瞬步

| 項目 | 測試 |
|---|---|
| `choose` 兩段選取（引擎） | `test_choose_lists_every_adjacent_landing_and_uses_the_chosen_one`、`test_choose_rejects_far_tiles_and_allies` |
| `choose`（API） | `tests/api/test_shadowstep_api.py`：`test_choose_lists_enemy_and_adjacent_landing_pairs`、`test_posting_a_choose_pair_lands_there_and_previews_the_move`、`test_a_choose_with_only_the_enemy_is_rejected`、`test_behind_needs_only_the_enemy` |
| `choose`（網頁） | vitest `facing.test.ts`（瞬步模式、提示文字、預覽）；瀏覽器由 PM 驗收（2.5） |
| `behind` 背後格、被占改最近空格、都沒有不能施放 | `test_behind_lands_on_the_back_tile_and_the_damage_is_a_backstab`、`test_behind_takes_the_nearest_free_tile_when_the_back_is_taken`（側面、再正面）、`test_behind_cannot_be_cast_when_no_adjacent_tile_is_free` |
| 不觸發藉機攻擊 | `test_shadowstep_does_not_provoke_opportunity_attacks` |
| 接傷害吃到背刺 | `test_behind_lands_on_the_back_tile_and_the_damage_is_a_backstab`（兩個傷害效果的判定都 `backstab == 2`） |
| 落點互動、限制、schema | `test_the_landing_tile_interacts_as_usual`（火表面）、`test_shadowstep_needs_an_enemy_and_cannot_be_used_rooted`、`test_the_schema_checks_landing_and_shape`、`test_the_demo_skills_are_in_build_assassin` |

### 驗收 4：潛行偷襲

- `test_attacking_while_concealed_gets_the_ambush_bonus_and_reveals_the_attacker`（`ambush == 2`、`status_removed` 原因 `ambushed`、紀錄文字；沒隱蔽時 0）。
- `test_self_concealed_bonus_damage_needs_the_status_and_ends_it_after_the_skill`（隱蔽時暗影突襲兩次傷害、否則一次；施放後脫離隱蔽；條件判斷）。

### 驗收 5：網頁、vitest、sim、check、重播

- 網頁朝向箭頭：PM 用瀏覽器驗收（2.5）。vitest：`client/src/battle/facing.test.ts` 6 個。
- AI 背刺紀錄：`trpg sim maps --seeds 5 --ally-build build_assassin`（見 2.4）；`test_ai_values_standing_behind_and_dislikes_showing_its_back`。（預設陣容的 `sim maps` 沒有英雄 build，必須帶 `--ally-build build_assassin`，與 3D-8c 相同。）
- `uv run trpg sim completion --seeds 3`（270 場）：「異常合計：exception 0、max_actions 0、draw 0 —— 通過」。
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2835** 個）、client typecheck、vitest（**153** 個）全部通過。
- 重播：`test_ai_battle_with_backstabs_replays`；`trpg battle --map dark_forest --seed 3 --ally-build build_assassin --log-json …` → `trpg battle replay` 「重播驗證通過：125 個動作、316 個事件」。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_skill_rules_content.py` | `strike` 的形狀加 `unit_then_tile`、`displace` 核心加 `shadowstep` |
| `tests/sim/test_skill_fuzz.py::test_a_passive_is_fought_and_its_triggers_are_counted` | 種子 3 → 2：AI 加了朝向權重後走位改變，種子 3 的戰鬥裡「回氣」不再觸發（種子 2 觸發 2 次） |
| `tests/api/test_routes.py` | 預覽多 `backstab` 欄位 |
| `tests/cli/test_budget_cli.py` | 技能數 132 → 134 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/31` → `/32`（另新增朝向的 CLI 測試） |
| `tests/cli/snapshots/cli_output_hashes.json` | **重錄 9 筆**：`skills_list`、`skills_show_all`（新增 2 個技能）；7 場戰鬥全部改變——單位列多「面向…」，而且背刺與 AI 朝向權重改變了 6 場的走向（以真實數值比對舊版事件：`narrow_halls` 9 只有單位列文字不同、事件一致；`open_plain` 7 342 → 375 個事件、`oil_depot` 7 489 → 495、`frozen_lake` 3 339 → 431（4 → 7 輪）、`bridge_chasm` 11 391 → 389、`swamp` 5 233 → 231、`test_heights_8x8` 42 244 → 240 且勝方由我方變敵方）。把加成與 AI 權重歸零時這 7 場與舊版逐事件一致（2.1），所以差異都來自背刺相關的結算與 AI 選擇 |
| `client/src/battle/testFixtures.ts` | `UnitView` 多 `facing` |

## 5. 新增的複雜度 noqa

**沒有新增 C901、PLR0911、PLR0912、PLR0915。** `ai/utility._special_estimate` 加了瞬步分支後超過 PLR0911，改把直線衝撞的估計拆成 `_charge_estimate`；紀錄文字的情境加值拆成 `narrative.events._bonus_parts`。新增的 `_charge_estimate`、`_shadowstep_estimate` 沿用同檔案其他估計函式的 `# noqa: PLR0917`（位置參數多，不屬複雜度類）。

## 6. `LOG_FORMAT`

`/31` → **`/32`**（本段升一次）：單位的 `facing`、核心規則 `backstab_hit_bonus`／`backstab_crit_range_bonus`／`ambush_hit_bonus`、`attack_rolled` 的 `backstab`／`ambush`、`status_removed` 的新原因 `ambushed`、條件 `from_behind`／`self_concealed`、原語 `shadowstep`（`EffectSpec.landing`、移動方式 `shadowstep`）、AI 權重 `backstab`／`back_exposed`。`/31` 的狀態沒有朝向，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **被攻擊的一方不轉身，背刺很常見**：設計是「面向最後移動或攻擊的方向」，所以被從背後砍的單位要等自己的回合攻擊或移動才轉身；sim 中雙方都大量背刺（`dark_forest` 5 場：我方 16、敵方 22 次；`oil_depot` 敵方 30 次）。若太頻繁，可考慮「被近戰攻擊命中後轉向攻擊者」或降低加成，平衡階段決定。
2. **`from_behind` 只算相鄰背後格**（規格允許擇一）：遠程攻擊永遠不是背刺；背刺加成只看攻擊參數是否近戰（法術一律不是）。長柄（射程 2）站在背後格也是近戰，但站在兩格外不算。
3. **朝向更新的範圍**：除了規格列的，還有藉機攻擊／監視射擊等反應普攻、`shape: single` 的反應技（面向觸發者）、攻擊物件；以格子、方向或自身為目標的技能不轉向。技能面向「施放時」目標的位置（目標被推開仍面向原方向，通常同軸）。
4. **潛行偷襲只看 `concealed` 狀態**（規格的 `self_concealed` 定義），站在黑暗表面或草叢的隱蔽沒有加成、也不會被移除；移除時機是「整次普攻或整次施放結算完」，多目標技能每個目標都吃 +2；反應技（例如迎頭痛擊）在隱蔽中出手也算偷襲（sim 有發生）。
5. **瞬步背刺的替代落點順序**：背後被占時取離背後格最近的相鄰格（Chebyshev 距離 → 左右兩側優先、正面最後；同距離依上、右、下、左）；施放者自己站的格子算空格；落點高度差 ≤ 近戰上限。瞬步不觸發 `enemy_enters_adjacent` 與監視射擊（比照跳躍），不算「本回合移動過」、不觸發 `on_move`。
6. **預算初值**：`shadowstep` 固定 4 點（同衝鋒 3、跳躍 3 再加一點落點保證）；`from_behind` common（0.85）、`self_concealed` harsh（0.6）；背刺與偷襲加成本身不計價（瞬步背刺幾乎必定背刺，等於白送 +2 命中與暴擊）。瞬步背刺原本傷害 100% 只有 66.9%（過弱），所以加上 `from_behind` 條件的 50% 傷害（85.0%）。
7. **build 變動**：`build_assassin` 以瞬步背刺換下先發制人、以暗影突襲換下撕裂打擊；先發制人移到 `build_gambler`（原本 5 個主動）。`strike` 骨架多了 `unit_then_tile` 形狀（只給手寫技能）。3C-6 整理 build 時再看。
8. **AI 朝向權重套用到所有行為模式**（規格「敵我同一套」）：`backstab` 4、`back_exposed` 3 是初值；因此所有 AI 戰鬥的走向都可能改變（第 4 節快照）。背對的判斷用「面向最近的敵人」近似，不模擬真正的最後一步方向。
9. **API 新增 `SkillCard.effect_ids`**（效果原語代碼）讓網頁分辨一般瞬步與傳送他人；移動方式多了 `shadowstep`（網頁動畫直接出現在落點）。沒有新增 `FacingChanged` 事件（規格允許不加）。
10. **開場朝向用起始位置的重心**：目前地圖都是左右對陣，結果等同「我方朝右、敵方朝左」；若之後有上下或包圍的地圖，各陣營整隊同一個朝向。援軍面向存活敵人的重心、召喚物與召喚者同向，規格沒寫。

## 8. 代表性的 CLI 輸出節錄

`uv run trpg battle --map dark_forest --seed 0 --ally-build build_assassin`，第 1 輪（連續的一段，未剪接）：盜賊3 走到 (5, 3) 時面向西，主角走到 (4, 2) 後施放「瞬步背刺」，瞬步到盜賊3 的背後 (6, 3)，兩段傷害（第二段是 `from_behind` 條件的 50%）都吃到背刺；接著再普攻一次，也是從背後：

```
— 盜賊3 的回合（AP 3，移動 5）
  盜賊3 從 (9, 4) 移動到 (5, 3)（消耗 5 移動）
  盜賊3 獲得狀態「防禦」
  盜賊3 結束回合，保留 1 AP
— 刺殺英雄 的回合（AP 3，移動 5，法力 20/20）
  刺殺英雄 從 (0, 3) 移動到 (4, 2)（消耗 5 移動）
  刺殺英雄 施放「瞬步背刺」（AP 2，法力 5，冷卻 3 回合）→ 影響 1 格
  刺殺英雄 瞬步到 (6, 3)
  刺殺英雄 從背後以「瞬步背刺」攻擊 盜賊3：d20=13 修正 -1 熟練 +2 背刺 +2 = 16（目標 11）→ 命中
  ⟳ 盜賊3 反應：格擋（耐力 −10）
    盜賊3 受到 3 點物理傷害［骰 3］（格擋/加成 ×0.5），HP 30 → 27
    盜賊3 受到 1 點物理傷害［骰 3］（格擋/加成 ×0.25），HP 27 → 26
  刺殺英雄 從背後攻擊 盜賊3：d20=4 修正 -1 熟練 +2 背刺 +2 = 7（目標 11）→ 失手
  刺殺英雄 結束回合
```
