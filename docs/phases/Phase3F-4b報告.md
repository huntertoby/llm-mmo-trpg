# Phase 3F-4b 報告：複合技能的延遲段、AI、技能工坊、戰鬥網頁

> 規格：`docs/phases/Phase3F計畫.md` 0.4、0.5、4.2、4.3（3F-4b，含「3F-4a 留下的」）；設計：`docs/design/06-技能.md` 6.23。規格與設計沒有衝突（設計 #5 的「第一段：任何」照做，見待決 #3）。

## 1. commit

| commit | 內容 |
|---|---|
| 34768d0 | 引擎：`followup.when: delayed` 與 `release: next_turn \| attacked`（schema）、狀態 `charging`、`engine/delayed.py`（蓄力、釋放、取消、`charge_infos`）、`interpreter.run_delayed`、回合開始釋放、被攻擊釋放（`skill_triggers`）、新事件 `followup_charged`／`followup_cancelled`、效果 `cancel_charge`、預覽／環境預告（`Telegraph.charges`）／視圖（`StatusView.skill_id`／`release`／`charge_tiles`）、敘事文字；預算 `composite_delayed_discount_permille`（800‰）與 CLI「× 延遲折扣」；示範技能「蓄力斬」「格擋反擊」與裝備調整；`tests/engine/test_delayed_followup.py`（28） |
| 566b5d3 | AI：`composite_estimate` 涵蓋六種（延遲段看預計範圍）、`choose_followup` 回答第二段暫停（`runner.accept_all`）、延遲段加分 `delayed_enemy_points`／`delayed_attacked_permille`；`tests/engine/test_composite_ai_kinds.py`（7） |
| e788f92 | API：`TelegraphOut.charges`（含中文 `text`）、第二段暫停中的 `/preview`；OpenAPI 與 `schema.d.ts`；`tests/api/test_delayed_api.py` |
| 7797ed9 | 工坊後端：「第二段」步驟（`followup.when` → `followup.release` → 骨架 → 形狀 → 效果與 `followup.condition`），各種類的限制；位移骨架可選環形（聚集段）；`tests/skillgen/test_workshop_kinds.py`（12） |
| 45fa175 | API：預覽的 `followup_when` |
| 7b9699c | 網頁：第二段暫停的選取（模式＋`FollowupDialog`，滑過預覽、點選送出、Esc 放棄）、蓄力倒數徽章「蓄1」、環境預告的蓄力列與格子標記「蓄」、單位資訊與 HUD 的蓄力說明、預覽依種類的第二段說明、工坊「第二段」步驟（換種類重設第二段）；vitest |
| ecb01a6 | 測試：預覽欄位清單多 `followup_when` |
| 454bfc0 | 修正：技能卡片 `followup_when`，網頁只有「位移 → 動作」走兩段選取（其他種類照第一段選取） |
| 6d77504 | 修正：行動面板提示文字涵蓋第二段 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。

## 2. 交付項目

### 2.1 延遲段（資料格式與結算）

```yaml
# content/skills/skill_charged_cleave.yaml（節錄）：蓄力斬
skeleton: aura
shape: {type: self}
effects: [{type: shield, dice: 1d4, affects: self}]      # 第一段：架刀蓄力（護盾）
followup:
  when: delayed
  release: next_turn          # 施放者下回合開始時釋放
  skeleton: area
  shape: {type: square3, range: 0}
  effects: [{type: damage, multiplier_permille: 1000}]
# skill_parry_riposte.yaml：格擋反擊——同樣第一段護盾；release: attacked、十字、武器 ×0.9
```

- **schema**：`release` 只有 `when: delayed` 可以（也必須）指定；第一段「任何」——不能有 `FOLLOWUP_FORBIDDEN` 的原語，但允許一個自身位移（例如跳過去、下回合砸地）；第二段形狀限 `DELAYED_SHAPES`（`cross`／`square3` `range: 0`、`ring`），不能有位移、召喚、區域、陷阱等。
- **等待＝狀態**：第一段結算完、施放者還站著且沒被控制時，身上加 `charging`（`StatusInstance.skill_id`＝技能、`source_id`＝自己、`remaining`＝1），發出 `followup_charged`（`release`、以目前位置推算的 `tiles`）。狀態本身就是等待中的延遲段，所以存讀檔與重播不需要新欄位。`charging` 是 `neutral`、`beneficial`、`expires: never`、沒有 `budget_points`：不會被淨化、驅散或奪取，技能也不能施加。同一時間只有一個蓄力，再施放另一個延遲段時舊的取消（`replaced`）。
- **釋放（`next_turn`）**：施放者下回合開始時，在狀態與表面的回合開始效果、持續區域、陷阱、圖騰之後、被動 `on_turn_start` 之前（`turns._turn_start_hooks`），以施放者 **當下** 的位置為中心結算第二段：`skill_followup`（`when: delayed`）＋第二段的事件。不付代價（施放時已付），命中照常擲骰，結算後照常 `after_attack`（朝向、潛行偷襲）。
- **釋放（`attacked`）**：到施放者下回合開始之前，被敵人攻擊（`attack_rolled`，不論命中與否）時，`skill_triggers.observe` 記一筆 `Fired`（`delayed_release`），等那次攻擊／施放整個結算完才釋放（同被動觸發，深度計入 `max_trigger_depth`）。同一次範圍攻擊的多個擲骰只釋放一次。沒被攻擊就在下回合開始時失效（`followup_cancelled`：`expired`）。
- **取消**：施放者倒下（`unit_downed` 的觸發）、被施加 `skip_turn` 的狀態（暈眩、冰凍；`status_applied` 的觸發）時立即取消（`followup_cancelled`：`downed`／`controlled`）；施放當下已被控制則不蓄力（`effect_fizzled`：`followup_caster_down`）。
- **預告與顯示**：`Telegraph.charges`（API `TelegraphOut.charges`：施放者、技能、釋放時機、`remaining`、`pos`、`tiles`、中文 `text`）；`StatusView` 多 `skill_id`／`release`／`charge_tiles`；預覽的 `landing`／`followup_tiles` 是預計範圍、`followup_when` 是種類。延遲段在施放者的回合開始時結算，不在環境回合，所以不影響環境預告的 `events`／`changes`，另列一欄。

### 2.2 預算

延遲段：（第一段 ＋ 第二段 × `composite_delayed_discount_permille` 800‰）× 1.15（同 3F-4a 的觸發機率位置；兩種釋放共用同一個折扣）。`trpg skills budget` 顯示「× 延遲折扣 800‰」。

| 技能 | 內容 | 預算 | 裝在 |
|---|---|---|---|
| 蓄力斬 `skill_charged_cleave`（武器技近戰、T1、AP 2、法力 5、冷卻 3） | 自身護盾 1d4 → 下回合開始時方陣武器 ×1.0 | （2.50 ＋ 14.00 × 0.8）× 1.15 ＝ 15.76 ÷ 16.45 ＝ **95.8%** | `build_push`，換下「閃現」（閃現仍在 build_assassin 等 5 個 build） |
| 格擋反擊 `skill_parry_riposte`（武器技近戰、T1、AP 2、法力 4、冷卻 2） | 自身護盾 1d4 → 被攻擊時十字武器 ×0.9 | （2.50 ＋ 11.34 × 0.8）× 1.15 ＝ 13.31 ÷ 15.68 ＝ **84.9%** | `build_tank`，換下「盾擊」（盾擊仍在 build_wallburn 與敵方盾兵；和嘲諷搭配） |
| 回馬斬（3F-4a） | — | 71.9% | 由 `hero_fighter` 搬到 **`build_assassin`，換下「處決」**（處決仍在 hero_fighter） |

### 2.3 AI（3F-4a 的四種 ＋ 延遲段）

- **候選估計**（`engine/ai/composite.py` 的 `composite_estimate`）：六種一律估計「影響範圍內敵人數 × 3 − 友方 × 3」，沒有敵人不納入；`legal_actions` 對 `after_action`／`on_kill`／`on_hit` 只列第一段，範圍就是第一段的；延遲段看以施放者目前位置推算的預計範圍。上限仍是每技能 `skill_candidates`（3）個完整預覽。
- **第二段的暫停**：`runner.accept_all`（自動對戰的決策）改呼叫 `choose_followup`：第二段只是一個自身位移（打帶跑）時選離最近敵人最遠的落點；其他選範圍內「敵人 − 友方」最多的選取，沒有正分時放棄。
- **延遲段收益**：預覽沒有第二段的傷害，所以在 `_rewrite_gains` 加上「預計範圍內（敵人 − 友方）× `delayed_enemy_points`（5）」，被攻擊才釋放的再 × `delayed_attacked_permille`（600‰），放 `content/ai_profiles.yaml`。
- `uv run trpg sim maps --seeds 5 --ally-build <build>`（各 10 張地圖 × 5 場，例外：無）的使用紀錄（次／場、命中率）：

| 技能（build） | 有使用紀錄的地圖 |
|---|---|
| 蓄力斬（build_push） | **10／10**：bridge 0.2、cliff 0.4、dark_forest 0.8、frozen_lake 0.4、lava 0.6、narrow_halls 0.2、oil_depot 0.2、open_plain 0.4、ruined_fort 0.6、swamp 0.6 |
| 格擋反擊（build_tank） | 1／10：open_plain 0.2（命中 100%、4.0） |
| 回馬斬（build_assassin） | 3／10：dark_forest 0.2、frozen_lake 0.8、swamp 0.2 |
| 引力爆（build_fire） | 8／10（dark_forest 1.0、swamp 0.6，其他 0.2） |
| 死亡迴旋（build_bomber） | 3／10：lava 0.2、open_plain 0.4、ruined_fort 0.4（命中 100%） |
| 破甲連擊（build_striker） | 8／10（swamp 1.6、dark_forest／oil_depot／ruined_fort 0.8） |

  報表的「異常」欄只有平衡旗標（`one_shot` 共 13 次、`long_battle` 3、`draw` 1、`boss_burst` 1），沒有錯誤；本段沒有和改動前比較（待決 #7）。

### 2.4 技能工坊（六種都能組）

「動作段」步驟改名 **「第二段」**，欄位依序展開（都是 `followup.*` 點號路徑，網頁照一般欄位處理）：

1. `followup.when`「接第二段」：只列第一段目前能接的種類（`kind_eligible`，與 schema 的結構規則相同：位移 → 動作要一個自身位移；聚集要一個 `pull` 加十字／方陣／環形；擊殺、命中要有傷害；延遲段允許一個自身位移……）。不選＝普通技能。
2. 延遲段多 `followup.release`「何時釋放」（下回合開始時／被攻擊時，必填）。
3. `followup.skeleton`（打帶跑只能「位移」）→ `followup.shape`（依種類：延遲段 `DELAYED_SHAPES`、擊殺含指定格、打帶跑是位移原語的形狀；十字、方陣的射程固定——聚集為聚集段的射程，其他為 0）→ `followup.effects`（打帶跑只能一個自身位移；擊殺可含一個自身位移；其他不能有位移、召喚、區域、陷阱；上限＝4 − 第一段效果數）＋ **`followup.condition`**（3F-3b 待決 #4：第二段的條件，`requires_condition` 的骨架也開放）。
- 沒有 `when` 但有 `followup.skeleton` 的舊草稿視為「位移 → 動作」。位移骨架的形狀多「環形」（只能當聚集段，說明裡註明）。
- 檢查與預算仍全部走 `trpg.content`／`trpg.skillgen` 既有函式。

### 2.5 戰鬥網頁

- **第二段暫停的選取**（`battle/followup.ts`、`ui/FollowupDialog.tsx`）：`pending.kind == "followup"` 時，`followup_options` 變成一個選取模式（同複製技能）：戰場高亮落點格／目標單位／方向，**滑過會預覽第二段**（新的伺服器端「暫停中預覽」：暫停前的狀態帶著這個選取重新模擬原本的施放，與 `/decision` 結果一致；0.5 #8），點選送 `/decision`（`followup_target`），Esc 或「放棄第二段」只略過第二段。
- **延遲段倒數**：蓄力中的單位左下角紫色徽章「蓄1」；單位資訊與 HUD 狀態「蓄力「蓄力斬」：下回合開始時釋放，以自己為中心影響 9 格」；環境預告側欄列出每個蓄力（`charges[].text`），格子上施放者標「蓄1」、預計範圍標「蓄」（紫色，滑過看說明）。
- 預覽的第二段說明依種類（`followup_when`）：延遲段寫「延遲段：施放後開始蓄力……目前預計影響 N 格（紫色），倒下、暈眩或冰凍會取消」。
- **只有「位移 → 動作」用兩段選取**（技能卡片 `followup_when`）；其他種類照第一段選取（蓄力斬點技能後按施放，回馬斬點方向——結算到第二段才暫停）。

## 3. 驗收條件逐條（4.3，3F-4b）

| 條件 | 結果與證據 |
|---|---|
| 延遲段的倒數 | `test_casting_charges_and_the_slash_lands_when_the_next_turn_starts`（`charging`：`skill_id`、`remaining 1`；`followup_charged` 9 格；下回合開始 `skill_followup(when=delayed)`，方陣內兩人受傷、外面的沒有；敘事文字）、`test_the_release_is_centred_where_the_caster_stands_now`、`test_a_release_with_nobody_around_still_resolves_without_hits`；網頁 vitest `battle/followup.test.ts`（徽章、說明） |
| 條件觸發（本輪被攻擊） | `test_being_attacked_releases_the_riposte_after_the_attack`（`attack_rolled` 之後才 `skill_followup`；十字內兩人受傷、對角的沒有）、`test_only_one_riposte_per_charge`、`test_an_unattacked_riposte_expires_when_the_next_turn_starts` |
| 取消（倒下、暈眩、冰凍） | `test_downed_stunned_or_frozen_casters_lose_the_charge[stun／frozen／lethal]`（`followup_cancelled` 的 `controlled`／`downed`，之後不釋放）、`test_other_statuses_keep_the_charge`、`test_a_controlled_caster_never_charges`、`test_charging_cannot_be_cleansed_or_dispelled` |
| 環境預告 | `test_the_telegraph_and_the_view_show_the_countdown_and_the_area`；API `tests/api/test_delayed_api.py::test_the_charge_shows_in_the_preview_the_view_and_the_telegraph`（預覽範圍、視圖 `charge_tiles`、`telegraph.charges` 與「正在蓄力「蓄力斬」：下回合開始時釋放」）；vitest（環境預告標記與列表） |
| 序列化、重播 | `test_the_charge_survives_save_and_load`、`test_a_battle_with_a_charge_replays_exactly`（`run_battle` → `replay` 與 `BattleLog` JSON 往返逐字一致）；CLI：`trpg battle --map swamp --seed 0 --ally-build build_push --log-json` → `trpg battle replay`：「重播驗證通過：109 個動作、336 個事件，最終狀態一致」 |
| 工坊能組出六種複合技能 | `tests/skillgen/test_workshop_kinds.py::test_each_kind_walks_through_the_options_to_a_legal_skill[7 個示範技能]`（每加一個第二段欄位都在選項內、最後完整且合法、預算與內容庫相同）、`test_kinds_follow_the_first_part`、`test_the_delayed_kind_asks_when_to_release_and_limits_the_shapes`、`test_hit_and_run_offers_only_the_move_skeleton_and_one_self_move`、`test_the_gather_burst_range_is_fixed_to_the_gather_range`、`test_a_second_part_condition_is_offered_and_checked`；`test_every_shipped_skill_fits_the_options` 不再略過任何技能；API 試玩：`test_a_workshop_delayed_skill_can_be_tried_out_and_charged`。**瀏覽器由 PM 驗收（第 6 節）** |
| AI 在 `sim maps` 有使用紀錄 | 2.3 表：六個示範技能都有紀錄；測試 `tests/engine/test_composite_ai_kinds.py`（打帶跑選最遠落點、擊殺選有敵人的目標、沒有值得的選取放棄、六種都有估計、預計範圍沒有敵人不納入、被包圍時會蓄力、AI 施放回馬斬並回答暫停） |
| 3F-4a 留下的 | 工坊第二段的條件與 `when`（2.4）；AI 回答暫停（2.3）；回馬斬換進 build_assassin（2.2）；暫停中的第二段預覽：`tests/api/test_delayed_api.py::test_the_paused_second_part_can_be_previewed`（預覽格＝落點，其他動作 400、暫停不變） |
| `check.py` 全過 | `uv run python scripts/check.py`（HEAD 454bfc0）：ruff、format、mypy、lint-imports、pytest **3200** 個、client install／typecheck、vitest **216** 個——「全部檢查通過。」；`corepack pnpm -C client build` 成功（只有既有的 chunk 大於 500 kB 警告） |

## 4. 修改既有測試與快照的原因

| 檔案 | 原因 |
|---|---|
| `tests/engine/test_composite_followups.py` | 回馬斬的裝備改為 build_assassin（示範技能表、重播測試的主角）；刪除 `test_the_ai_does_not_use_the_new_kinds_yet`（AI 現在會用，改由 `test_composite_ai_kinds.py` 測） |
| `tests/content/test_coverage.py` | `charging` 由 `followup.when: delayed` 產生（同 `time_bomb` ← `delayed_damage` 的做法），允許清單仍為空 |
| `tests/content/test_sim_builds.py` | build_push 的「閃現」換成蓄力斬，替換字串跟著改 |
| `tests/skillgen/test_budget.py`、`test_validate.py` | 狀態表多 `charging`（沒有預算點數、`beneficial`） |
| `tests/cli/test_budget_cli.py` | 技能數 147 → 149 |
| `tests/sim/test_matrix.py` | build_push 的第三個技能變成蓄力斬 |
| `tests/engine/test_scene_ai.py` | build_push 換技能後，lava_crossing 種子 0 不再推倒石柱；改用種子 1（仍推倒、重播通過） |
| `tests/skillgen/test_workshop_options.py` | 不再略過 3F-4a 的四種 |
| `tests/skillgen/test_workshop_followup.py`、`tests/api/test_workshop_api.py` | 步驟改名「第二段」、欄位先是 `followup.when`；「只有位移技能才有這一步」改為「位移 → 動作只列給位移技能」 |
| `tests/api/test_reactions_telegraph.py`、`tests/api/test_routes.py` | 環境預告多 `charges`、預覽多 `followup_when` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 `skills_list`、`skills_show_all`（新增 2 個技能、回馬斬改裝備）、`battle_frozen_lake_push_3`（build_push 換技能）、`battle_oil_depot_fire_7`（AI 會用引力爆）；其他 4 場不變 |
| client：`bombs.test.ts`、`drawModel.test.ts`、`polish3c6a.test.ts`、`telegraph.test.ts`、`zones.test.ts`、`workshop/followup.test.ts`、`battle/composite.test.ts` | 型別多了 `charges`／`charge_tiles`（產生的型別為必填）；步驟名稱改「第二段」；複合標記只給「位移 → 動作」 |

## 5. 新增的複雜度 noqa

**沒有新增** C901、PLR0911、PLR0912、PLR0915（`start_turn` 超過分支上限，拆出 `_turn_start_hooks`；預覽的 `_followup_info` 超過 return 上限，拆出 `_simulated_second`）。`skillgen/option_followup._effects_field` 有 `# noqa: PLR0917`（6 個位置參數，不屬複雜度類）。

## 6. PM 瀏覽器驗收步驟

先 `corepack pnpm -C client build`（已建置）再 `uv run trpg serve`，開 http://127.0.0.1:8000/。**8000 埠目前有一個舊程序在跑（PID 47004），請先關掉再啟動**，否則看到的是舊版。

### 6.1 工坊組一個延遲段技能並在靶場施放（看倒數）

1. 首頁「進入技能工坊」→ **骨架**點「光環」→ 下一步。
2. **基本設定**：名稱「蓄力試斬」；種類「主動」；類別「武器技」→ 武器需求「近戰武器」；縮放屬性「力量」；階級 1；AP 2 → 下一步。
3. **形狀**：「自身」→ 下一步。**效果**：新增「護盾」，骰子 1d4、對象「自己」→ 下一步。
4. **第二段**：「接第二段」點 **「延遲段」** → 出現「何時釋放」點「下回合開始時」→「第二段的骨架」點「範圍」→「第二段的形狀」點「方陣」（射程固定 0）→「第二段的效果」新增「傷害」，倍率 1000（「第二段的條件」不選）→ 下一步。
5. **條件**不選 → **代價**：法力 5、冷卻 3 → **稀有度**「稀有」。右側即時檢查應為「合法」、`95.8%・合格`；點數明細有「第一段」「延遲段」兩個表與「× 延遲折扣 800‰」。（想試被攻擊才釋放：步驟 4 改選「被攻擊時」、形狀「十字」、倍率 900，AP 2、法力 4、冷卻 2 → 84.9%。）
6. 「裝上試玩」：主角 build「衝鋒流」、換掉「蠻牛衝陣」、地圖「靶場」、對手「木樁」（被攻擊時釋放請選「會反擊」）→「裝上試玩」。
7. 走到木樁旁邊（相鄰），技能列點「蓄力試斬」：預覽寫「延遲段：施放後開始蓄力……目前預計影響 9 格（紫色）」，紫色方陣以主角為中心 → 按面板上的施放（自身形狀，或點主角）。
8. 施放後：主角圖示左下角紫色徽章 **「蓄1」**；單位資訊的狀態「蓄力「蓄力試斬」：下回合開始時釋放，以自己為中心影響 9 格」（HUD 寫「蓄力：下回合開始時釋放…」）；**環境預告**側欄多一行「（主角名） 正在蓄力「蓄力試斬」：下回合開始時釋放，以自己為中心影響 9 格」，格子上主角標「蓄1」、周圍 8 格標「蓄」（滑過看說明）。
9. 結束回合 → 下回合開始時戰鬥紀錄出現「✦ … 釋放蓄力，以 (x, y) 為中心 接著施展「蓄力試斬」的第二段」與對木樁的攻擊；徽章消失。（施放後再走動，範圍跟著主角移動。）
   - 內建示範：首頁一般戰鬥的我方 build 選「位移流」（蓄力斬）或「坦克」（格擋反擊）也可以直接試。

### 6.2 工坊組一個「擊殺 → 接下一段」（`on_kill`）技能

1. 骨架「打擊」；基本設定同 6.1（武器技、近戰、力量、階級 1、AP 2），名稱「連殺斬」。
2. 形狀「單體」射程 1；效果「傷害」倍率 **1200**。
3. **第二段**：「接第二段」點 **「擊殺 → 接下一段」** →「第二段的骨架」「打擊」→「第二段的形狀」「單體」射程 3 →「第二段的效果」新增「衝鋒」再新增「傷害」倍率 1000。
4. 代價法力 5、冷卻 3；稀有度「稀有」→ 即時檢查「合格」（約 79.7%），明細「第一段」「擊殺後的第二段」與「× 觸發機率 300‰」。（倍率 1000 會是 69.9% 過弱。）
5. 裝上試玩：「衝鋒流」、換掉「蠻牛衝陣」、「靶場」、對手 **「會反擊」**（有盜賊，打得倒）。對殘血的盜賊施放：打倒時戰鬥暫停，出現「第二段：選擇目標」視窗，戰場高亮 3 格內的敵人；**滑過會預覽第二段（紫色）**，點一個就衝過去再砍；按 Esc 或「放棄第二段」只略過第二段。沒打倒時紀錄寫「沒有達成條件（擊殺或命中）：第二段不結算」。
   - 暫停 UI 也可以用內建的回馬斬看（一定會暫停）：首頁一般戰鬥選「刺殺」build（build_assassin），對相鄰敵人施放回馬斬（點方向），第一段結算後選 2 格內的落點。

## 7. `LOG_FORMAT`

維持 **`/34`**。新增的是：狀態表的 `charging`、`FollowupSpec.release`（有預設值）、`followup.when` 的新值 `delayed`、新事件 `followup_charged`／`followup_cancelled`、新效果 `cancel_charge`、`StatusView` 的新欄位；舊紀錄沒有延遲段，規則包與事件照常讀取與重播（全量測試中的舊紀錄與重播測試都通過）。等待中的延遲段就是 `StatusInstance`（既有欄位），roguelite 戰鬥中的存檔照常讀取。

## 8. 待 PM 決定（最多 10 點）

1. **「本輪被攻擊」的解讀**：到施放者 **下回合開始之前**（不是本輪結束；施放者在本輪最後行動時也有一整輪的窗口）被敵人 **擲命中攻擊**（普攻或技能，命中與否都算）就釋放；自動命中的效果、炸彈、表面、環境不算；沒被攻擊就在下回合開始時失效。
2. **延遲段形狀只開放以施放者為中心**（十字、方陣 `range: 0`、環形）；範圍跟著施放者移動（施放後還能走）。單體／方向型的延遲段（要在施放時鎖定目標或方向）沒有做。
3. **第一段「任何」**：允許一個自身位移（跳過去、下回合砸地），其他 `FOLLOWUP_FORBIDDEN`（召喚、區域、陷阱、複製、規則改變、賭注、投擲）仍禁止。
4. **同一時間只有一個蓄力**（新的取代舊的，`replaced`）；`charging` 中性、有益，不被淨化、驅散、奪取；倒數固定 1（下回合）。
5. **折扣 800‰ 兩種釋放共用**、加成仍 ×1.15，未經模擬；兩個示範都用護盾當第一段（蓄力斬 95.8%、格擋反擊 84.9%）。護盾預算只算骰子平均，實際護盾含力量加成（例：1d4 → 10 點），是既有規則，待平衡階段一起看。
6. **裝備**：蓄力斬換下 build_push 的閃現；格擋反擊換下 build_tank 的盾擊；回馬斬由 hero_fighter 搬到 build_assassin 換下處決（hero_fighter 不再有回馬斬，避免預設主角的戰鬥改變）。
7. **AI 的近似很簡單**：打帶跑一律跳離敵人最遠處；延遲段加分是常數（每個敵人 5 點、被攻擊型 × 600‰）；格擋反擊的使用率很低（10 張地圖只有 1 張有紀錄）。sim 的平衡旗標（one_shot 等）沒有和改動前比較。
8. **釋放時的細節**：不付代價；被攻擊型等那次攻擊整個結算完才反擊（同被動觸發），觸發深度計入上限；釋放後照常轉向與移除潛行；釋放的攻擊也會觸發對方的反應（例：木樁、盜賊的格擋）。
9. **工坊**：步驟改名「第二段」；位移骨架的形狀多「環形」（只能當聚集段，否則檢查會擋）；第二段的條件開放，`requires_condition` 的骨架也可以當第二段的骨架。
10. **`LOG_FORMAT` 維持 `/34`**（理由見第 7 節）。

## 9. CLI 輸出節錄

`uv run trpg battle --map swamp --seed 0 --ally-build build_push`（位移流英雄施放蓄力斬，兩個敵人回合後在自己的回合開始時釋放；連續兩段，未剪接）：

```text
— 位移流英雄 的回合（AP 3，移動 5，法力 14/20）
  位移流英雄 施放「蓄力斬」（AP 2，法力 5，冷卻 3 回合）→ 影響 1 格
    位移流英雄 獲得 10 點護盾
  ◷ 位移流英雄 開始蓄力「蓄力斬」：下回合開始時釋放（以自己為中心，目前預計影響 9 格）
  位移流英雄 從 (1, 3) 移動到 (2, 3)（消耗 1 移動）
  位移流英雄 攻擊 盜賊盾衛：d20=20 修正 -1 熟練 +2 = 21（目標 11）→ 自然 20，暴擊！
  ⟳ 盜賊盾衛 反應：格擋（耐力 −10）
    盜賊盾衛 受到 6 點物理傷害［骰 5+4］（元素修正 ×0.9）（格擋/加成 ×0.5），HP 32 → 26
```

```text
— 位移流英雄 的回合（AP 3，移動 5，法力 9/20）
  ✦ 位移流英雄 釋放蓄力，以 (3, 4) 為中心 接著施展「蓄力斬」的第二段→ 影響 9 格
  位移流英雄 以「蓄力斬」攻擊 盜賊弓手：d20=15 修正 +0 熟練 +2 = 17（目標 11）→ 命中
  ⟳ 盜賊弓手 反應：格擋（耐力 −10）
    倒木 受到 8 點物理傷害［骰 4］，HP 20 → 12
    盜賊弓手 受到 5 點物理傷害［骰 7］（格擋/加成 ×0.5），HP 21 → 16
```

```text
$ uv run trpg skills budget skill_parry_riposte
  【延遲段】骨架 area  形狀 cross
    2. damage          武器 ×0.9           形狀 ×1.8   對象 ×1    條件 ×1     ＝ 11.34（基礎 6.30）
  複合加成 +150‰：（2.50 ＋ 11.34 × 延遲折扣 800‰）× (1000 + 150) ÷ 1000 ＝ 13.31
  比例 ＝ total ÷ 可用預算 ＝ 84.9%（合格區間 70.0%–100.0%）→ 合格
```
