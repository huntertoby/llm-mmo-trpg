# Phase 3C-4b 報告：`redirect_damage`、`copy_skill`、`extra_reaction`

## 1. commit

| commit | 內容 |
|---|---|
| 2d99126 | 引擎與內容：三個改寫規則型原語（`content/skill_primitives.yaml`）、狀態 `soul_link`、`BattleState.casts`、`UseSkill.copy_cast`／`Decision.copy_cast`、暫停種類 `copy_skill`、新事件、AI 評分、紀錄文字、三個手寫技能與 build 裝備、`LOG_FORMAT` `/15`；測試 |
| 5c616fa | API 與前端：`DecisionRequest.copy_cast`、`BattleResponse.copy_options`、OpenAPI／`schema.d.ts` 重新產生、第二段選取的畫面（`CopyDialog`、`copyMode`）；API 測試與 vitest |
| （本報告） | 報告 |

## 2. 交付項目

### 2.1 `redirect_damage`（狀態 `soul_link`）

- 原語 `redirect_damage`（`permille` 100–500、`duration` 1–3，只能對友方、不含施放者）：對目標施加 `soul_link`（`StatusDef.redirects_damage: true`；`StatusInstance.amount` 存轉移千分比、`source_id` 是承受轉移的施放者）。新的連結一律取代舊的；對施放者自己施放發出 `effect_fizzled(self_link)`。
- 規則在 `effects/handlers._damage`：護盾吸收之後、真正會扣 HP 的部分，有 `permille`‰ 轉給施放者，**直接扣 HP**（不經護盾、抗性、元素修正）；施放者的 `undying` 照常生效；HP 歸零則倒下。`DamageDealt.redirected` 記錄轉出的點數，緊接著 `DamageRedirected` 事件。墜落、致命地形與 `lethal` 不轉移（與 `undying` 同一組保守規則）。
- **與 `intercept` 同時**：攔截發生在傷害之前（攻擊改由守護者承受），所以傷害落在守護者身上之後才看守護者有沒有連結；原目標的連結不轉移。
- **施放者倒下**：連結立即移除（`is_removed_with_source` 加入 `redirects_damage`，`status_removed` 原因 `source_lost`）；轉移本身讓施放者倒下時同樣處理。

### 2.2 `copy_skill`

- 戰鬥狀態新增 `casts`（本輪以 `UseSkill` 施放過的主動技能，依序，每次記錄時丟掉舊輪；可序列化、可重播）。複製對象 ＝ 本輪內 **最後一個別人施放的** 技能（複製者自己的施放不算，也不會蓋掉別人的）；施放者必須仍在場上、複製者看得到它（`has_line_of_sight`）。
- 不能複製：傳說、含改寫規則型原語（含 `copy_skill` 自己）、陷阱技能、非主動、有層數需求（`cost.stacks`）的技能。沒有可複製的技能、或複製的技能沒有任何合法選取時，`copy_skill` 技能 **不能施放**（`skill_problem`，不在 `legal_actions`，直接施放回中文錯誤，例如「本輪還沒有其他單位施放過技能，沒有技能可以複製」）。
- 施放：以複製者的身分、複製者自己的屬性與武器，立即結算被複製技能的效果；**不扣法力與 AP、不進冷卻、不花源力**；射程、視線、目標、技能條件與沉默仍要合法，**不檢查 `weapon_req`**（見待決 #2）。事件 `SkillCopied`，接著是一般的施放結算（命中、傷害、被動觸發都照常）。`casts` 在這次施放結束之後才更新，所以複製不會改寫「最後施放」。
- 形狀與結構：`copy_skill` 必須是主動技能、形狀 `self`、技能唯一的效果（`SkillDef._check_copy_skill`）。
- **兩段選取（pending）**：玩家送出沒有 `copy_cast` 的 `UseSkill` → `resolve` 暫停（在付任何代價之前），`Pending.kind == "copy_skill"`、`skill_id` ＝ 施放的複製技能、`copy_skill_id` ＝ 被複製的技能；`PendingResolution` 存基礎狀態與原動作（和反應詢問同一套存讀）。以 `Decision(accept=True, copy_cast=<選取>)` 繼續（重新結算 `UseSkill.copy_cast=選取`，與一次送完整動作結果逐位元相同），`accept=False` 放棄（回到施放之前，不付代價），選取不合法或沒給選取時拋 `IllegalActionError`、暫停不變。預覽沒有 `copy_cast` 的動作時不暫停（只算到複製之前）。
- `legal_actions` 只列 **一個** 沒有 `copy_cast` 的動作（前端沿用既有的技能按鈕）；AI 用 `legal_actions_with_areas(expand_copy=True)`，每個合法選取各一個完整動作（影響範圍是被複製技能的），評分與篩選（`skill_estimate`）看被複製技能的效果；`runner.accept_all`（預設的 `decide`）遇到複製暫停取第一個合法選取，所以沒有自訂 `decide` 的驅動迴圈也不會卡住。

### 2.3 `extra_reaction`

- 原語 `extra_reaction`（`amount` 固定 1，自己或友方）：`UnitState.extra_reactions += amount`；反應上限 ＝ `reactions_per_round + extra_reactions`（`state.reaction_limit`，反應、藉機攻擊、視圖的 `reaction_available`、AI 的藉機攻擊估計共用）；每輪開始時歸零（`turns._end_round`）。事件 `ReactionsGranted`。

### 2.4 內容

| 項目 | 內容（數值皆為初值，未經模擬） |
|---|---|
| `redirect_damage` | 改寫規則型、最低稀有度 epic、固定 7 點；`soul_link` 預設 3 回合、無 `budget_points`（只能由此原語施加） |
| `copy_skill` | 改寫規則型、epic、固定 9 點；`acts_on: caster`、只能搭配 `self` 形狀 |
| `extra_reaction` | 改寫規則型、epic、每次 7 點（`per_amount`；原本 5 點時只有 58.5%，低於合格下限 70%） |
| 光環骨架 | 核心原語加入這三個 |
| 魂結 `skill_soul_bond`（epic） | 單體友方（射程 4）`redirect_damage` 400‰、3 回合；法力 6、冷卻 4（無源力，走 6.6 的「冷卻 ≥ 4」）；預算 81.3%；`build_guardian` |
| 警戒號令 `skill_vigil_call`（epic） | 單體友方（射程 4）`extra_reaction` +1；法力 4、冷卻 4；預算 82.0%；`build_guardian` |
| 鏡像施法 `skill_mirror_cast`（legendary） | 自身形狀 `copy_skill`；AP 1、冷卻 2、源力 1；預算 95.2%；`build_support` |
| AI（`ai_profiles.yaml` 的 `rewrite:`） | 新增 `redirect_points: 24`（× 目標已損失 HP 比例，施放者 HP 不到一半不連結）、`reaction_points: 8`（目標有反應規則才有價值） |

六個改寫規則型原語（`grant_ap`、`reset_cooldown`、`cheat_death`、`redirect_damage`、`copy_skill`、`extra_reaction`）都有手寫技能且都被 build 裝備（`test_all_six_rule_rewrite_primitives_have_equipped_hand_written_skills`）。

### 2.5 CLI、API、前端

- CLI 紀錄文字：`✦ A 複製了 B 的「技能」（不扣法力與 AP、不進冷卻）→ 影響 n 格`、`✦ A 分擔了 B 的 n 點傷害（靈魂連結），HP a → b`、傷害行加「（n 點轉給連結者）」、`X 本輪的反應次數 +1（額外共 1 次）`；`skills show` 的效果文字涵蓋三個原語。
- API：`DecisionRequest` 加 `copy_cast`（`UseSkill | null`）；`BattleResponse.copy_options`（複製暫停時，被複製技能目前所有合法的選取；其他時候空）；`Pending.copy_skill_id`；`StepOut` 的決定步驟帶 `copy_cast`。重新產生 `client/openapi.json`、`schema.d.ts`（遞迴的 `UseSkill` 在 OpenAPI 變成 `UseSkill-Input`／`UseSkill-Output` 兩個，前端型別別名改取 `-Output`）。
- 前端兩段選取：點技能按鈕（沒有目標，行為同其他自身技）→ 伺服器暫停 → `BattleScreen` 把 `copy_options` 建成一個模式（`copyMode`，沿用高亮與點選邏輯，目標格高亮）＋ `CopyDialog`（提示「要複製『橫掃劈砍』：在戰場上點選高亮的目標（共 n 個可選），或放棄施放」與「放棄施放」按鈕）；點目標 → `POST /decision {accept: true, copy_cast}`，放棄 → `{accept: false}`。被複製技能的名稱從 `/api/skills/{id}` 取得。懸停預覽在這一段停用（伺服器暫停時不收 `/preview`，見待決 #6）。

## 3. 驗收條件逐條

1. **三個原語的規則與邊界** — `tests/engine/test_rewrites_4b.py`（45 個）
   - `redirect_damage`：施加與取代 `test_redirect_damage_links_an_ally_to_the_caster`、`test_a_new_link_replaces_the_old_one`、對自己無效 `test_redirect_damage_on_the_caster_does_nothing`；轉移的數值與 HP 守恆 `test_redirected_damage_goes_to_the_caster_and_not_the_ally`、`test_redirect_takes_the_part_that_got_past_the_shield`；**與 `intercept` 同時** `test_intercept_comes_first_and_the_link_follows_the_guardian`；**轉移後施放者倒下** `test_the_caster_going_down_from_the_transfer_ends_the_link`、`test_undying_on_the_caster_survives_the_transfer`；墜落與致命地形不轉移 `test_falls_and_deadly_terrain_are_not_redirected`；schema（不能對敵、≤ 500‰）`test_the_link_cannot_target_enemies_or_exceed_half`；AI `test_the_ai_links_a_wounded_ally_only_when_the_caster_is_healthy`。
   - `copy_skill`：記錄與序列化 `test_the_last_cast_is_recorded_and_survives_serialization`；免費複製 `test_copy_skill_casts_the_last_skill_for_free`；**沒有可複製技能時不能施放**（不在 `legal_actions`、直接施放被拒）`test_nothing_to_copy_means_the_skill_cannot_be_cast`；跨輪、自己的、施放者倒下或看不到 `test_only_the_skill_cast_this_round_can_be_copied`、`test_a_skill_cast_by_the_copier_itself_cannot_be_copied`、`test_the_copier_own_casts_do_not_hide_the_last_cast_by_someone_else`、`test_the_original_caster_must_be_alive_and_visible`；**不能複製的類型** `test_some_skills_cannot_be_copied`（傳說、改寫規則型、層數需求、陷阱、反應技）、`test_a_plain_copy_skill_cannot_be_copied_either`；目標與射程合法性 `test_the_copy_needs_a_legal_target_and_the_right_skill`；沉默 `test_copying_still_needs_no_silence`；不檢查武器需求 `test_the_weapon_requirement_is_not_checked_when_copying`；形狀與唯一效果 `test_copy_skill_must_be_the_only_effect_and_self_shaped`。
   - `extra_reaction`：**到期** `test_extra_reaction_raises_the_limit_until_the_next_round`（走完一輪後歸零）；實際多反應一次 `test_an_extra_reaction_allows_a_second_reaction_in_the_same_round`；不能對敵 `test_extra_reaction_cannot_target_enemies`；AI `test_the_ai_gives_extra_reactions_only_to_units_that_react`。
2. **`copy_skill` 的 pending 在 API 與前端可操作，存讀正確**
   - 引擎：暫停與繼續 `test_a_bare_copy_pauses_and_resumes_with_the_choice`（暫停的狀態 `state_to_json`／`state_from_json` 之後仍等於原 `pending`，繼續的結果與一次送完整動作逐位元相同）、放棄 `test_declining_the_copy_costs_nothing`、壞選取 `test_a_bad_choice_keeps_the_pause`、預覽 `test_the_preview_of_a_bare_copy_does_not_pause`、`legal_actions` 與 AI 展開 `test_legal_actions_list_one_bare_copy_and_the_ai_gets_the_expanded_ones`、AI 實際選用 `test_the_ai_copies_a_skill_with_a_useful_target`。
   - API：`tests/api/test_copy_api.py`（5 個，`oil_depot` 種子 4 `build_support`）：`test_the_first_step_pauses_and_lists_the_copy_options`（`awaiting: decision`、`pending.kind`、`copy_options`、GET 讀回、工作階段狀態存讀、未付代價、暫停時 `/actions` 回 409）、`test_the_second_step_completes_the_copy`（含 `skill_copied` 事件、源力 −1、**戰鬥紀錄重播**，`trpg battle replay` 通過）、`test_declining_the_second_step_costs_nothing`、`test_a_bad_second_step_is_400_and_keeps_the_pause`、`test_a_complete_copy_action_works_in_one_request`。
   - 前端：`targeting.test.ts` 的 `copy_skill second step`（2 個：模式與點選、提示文字）；`corepack pnpm -C client typecheck` 通過。**瀏覽器操作由 PM 驗收**：`build_support` 英雄、地圖 `oil_depot`、種子 4，第 3 輪輪到主角時「鏡像施法」可用（盜賊頭目本輪施放了橫掃劈砍）；點它 → 出現「複製技能：選擇目標」卡片，敵人（含高亮）可點。
3. **`check.py` 全過；重播一致；六個原語都有手寫技能**
   - `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（收集 1918 個，另 7 個預設不跑）、client install／typecheck／vitest（78）全部通過。
   - 重播：`tests/engine/test_rewrites_4b.py::test_demo_battles_use_the_new_primitives_and_replay`（3 個：`build_support`／`oil_depot` 種子 4 含 `SkillCopied`、`build_guardian`／`open_plain` 種子 2 含 `DamageRedirected` 與 `ReactionsGranted`；事件與最終狀態逐位元一致）；CLI：`trpg battle --map oil_depot --seed 4 --ally-build build_support --log-json … ` → `trpg battle replay`：「重播驗證通過：123 個動作、367 個事件，最終狀態一致（oil_depot，種子 4）。」
   - 六個原語都有手寫技能且被 build 裝備：`test_all_six_rule_rewrite_primitives_have_equipped_hand_written_skills`；`tests/content/test_coverage.py` 允許清單維持為空（`soul_link` 由 `redirect_damage` 間接施加，加進 `_STATUS_VIA_PRIMITIVE`）。

## 4. 修改既有測試的原因

- `tests/content/test_skill_rules_content.py`：光環骨架的核心原語多三個；改寫規則型原語（現共六個）的最低稀有度是 epic。
- `tests/content/test_coverage.py`：`_STATUS_VIA_PRIMITIVE` 加 `soul_link → redirect_damage`。
- `tests/content/test_legendary_schema.py`：示範傳說清單加 `skill_mirror_cast`、原語涵蓋加 `copy_skill`。
- `tests/skillgen/test_budget.py`、`test_validate.py`：狀態表多了 `soul_link`（沒有預算點數、有益）。
- `tests/skillgen/test_random_composer.py`：組合器不使用的改寫規則型原語現共六個。
- `tests/engine/test_view.py`、`tests/api/test_routes.py`：公開的 `pending` 欄位多了 `copy_skill_id`；決定步驟的 JSON 多了 `copy_cast: null`。
- `tests/cli/test_battle_cli.py`、`test_skills_cli.py`：`LOG_FORMAT` `/14` → `/15`；`test_budget_cli.py`：技能數 75 → 78（3 處）。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json` 3 筆）：`skills_list`、`skills_show_all`（多了 3 個技能）、`battle_bridge_guardian_11`（`build_guardian` 多了魂結與警戒號令，AI 的選擇改變）。其餘 6 筆不變。

## 5. 新增的複雜度 noqa

**無**（沒有新增 C901、PLR0911、PLR0912、PLR0915）。`_damage` 一度超過 PLR0912，把轉移的判斷抽成 `redirect_link`／`_redirect`（沒有轉移時回傳空串列）解決；`_Cast.rewrite` 拆成 `rewrite`／`rewrite_status`／`copy_skill`。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/15`**（本段只升一次）。理由：戰鬥狀態多了 `casts`、單位多了 `extra_reactions`、`UseSkill.copy_cast`／`Decision.copy_cast`、暫停種類 `copy_skill`（`PendingResolution.copy_skill_id`）、新事件 `damage_redirected`／`skill_copied`／`reactions_granted`、`damage_dealt.redirected`、規則包多了三個原語與狀態 `soul_link`；`/14` 的紀錄無法由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **「最後一個被施放」的範圍**：規格寫「本輪內最後一個被友方或敵方施放」。實作為「本輪內最後一個 **別人** 施放的主動技能」（複製者自己的施放不算、也不會蓋掉別人的），而且只看那一個——如果它是傳說、改寫規則型、`copy_skill` 自己，就沒有東西可複製（不會往前找上一個可複製的）。這是最保守的字面解讀；若希望「往前找最近一個能複製的」，改 `copying.copy_source` 一處即可。另外「施放者看得到」解讀為「複製者看得到原施放者」（視線）。
2. **不檢查 `weapon_req`**：規格只要求「射程、目標」合法。若照武器需求，拿法器的主角幾乎複製不了任何敵人的技能（盜賊的技能都是近戰／遠程武器技），示範技能會形同虛設。傷害與射程照複製者自己的武器算（法器法師複製「橫掃劈砍」，傷害骰是自己法器的）。要加回武器需求只要在 `copy_free_problem` 補回 `weapon_problem`。
3. **不能複製的集合加了兩類**：陷阱技能與有層數需求（`cost.stacks`）的技能也不能複製（規格只列傳說、改寫規則型、`copy_skill`）——前者的「施放」是放置、後者會扣複製者自己的層數，行為不明，保守排除。反應技、姿態、被動本來就不是 `UseSkill` 的主動技能。
4. **複製的技能的觸發與修正**：複製後是一般的施放結算，所以複製者的修正規則（3C-2）、`on_cast_tag` 觸發、`mastery`、武器元素灌注都照常作用在複製的技能上；它不會寫進 `casts`（不能被「再複製」），但 `copy_skill` 技能本身會（所以接在它後面的 `copy_skill` 看到的是改寫規則型，不能複製）。
5. **`redirect_damage` 的轉移細節**：轉移的是護盾吸收之後的實際傷害；施放者 **直接扣 HP**（不經自己的護盾、抗性、元素修正，無法「再被轉走」），自己的 `undying` 仍可擋下；轉移不給精英擊殺源力。所有傷害原因（攻擊、技能、撞擊、狀態、表面、爆炸……）都轉移，只有墜落、致命地形與 `lethal` 不轉移。新連結取代舊連結（不疊加、不比較持續時間）。持續時間用狀態的 `turn_end` 倒數（帶有者的回合結束 −1），初值 3 回合、技能 `duration: 3`。
6. **前端只做最小**：複製暫停時沒有懸停預覽（伺服器在暫停時不收 `/preview`；要做需讓 `session.preview` 在暫停時以暫停前的狀態預覽，是小改動）；「放棄施放」是按鈕，`Esc` 不會放棄（`Esc` 只取消本地選取，暫停是伺服器端的）；被複製技能是誰施放的沒有顯示（只顯示技能名稱）。
7. **`copy_options` 與 `legal_actions` 不同形狀**：`legal_actions` 對複製技能只給一個沒有 `copy_cast` 的動作；API 客戶端若直接一次送完整動作（帶 `copy_cast`，用 `copy_options` 的某項）也可以，不經暫停（`test_a_complete_copy_action_works_in_one_request`）。LLM 與 3-5 之後的呼叫端要用哪一種由 PM 決定；我只保證兩種都可重播。
8. **OpenAPI 型別**：`UseSkill` 因為遞迴（`copy_cast: UseSkill | null`）被 FastAPI 拆成 `UseSkill-Input`／`UseSkill-Output` 兩個 schema，`client/src/api/types.ts` 的 `UseSkill`／`UseSkillAction` 別名改指 `-Output`。結構相同，只是型別名稱醜。
9. **AI 使用率**：鏡像施法在 `build_support` 的 24 場抽查（4 張地圖 × 6 個種子）中，8 場出現過合法機會（本輪要有敵人先施放、而且看得到），其中 7 場 AI 實際用了（源力只有 1，每場最多一次）；其餘 16 場沒有機會。`build_guardian` 的魂結在 16 場抽查（4 張地圖 × 4 個種子）中有 10 場出現（連結的是標準隊友），`bridge_guardian` 4 場都沒有出現。三個初值（`redirect_points: 24`、`reaction_points: 8`、複製沒有額外加分）未經模擬，3C-6 matrix 再看。
10. **預算初值**（未經模擬）：`redirect_damage` 固定 7、`copy_skill` 固定 9（不隨被複製技能的強度變動）、`extra_reaction` 每次 7；三個示範技能預算 81%／82%／95%。「複製最強的敵方技能」的上限由「不能複製傳說與改寫規則型」＋「本輪要有別人先施放」限制，是否過強留給平衡階段。

## 8. 代表性輸出

`uv run trpg battle --map oil_depot --seed 4 --ally-build build_support`（輸出第 225–252 行，連續未刪節；輔助英雄在第 3 輪以源力施放鏡像施法，複製剛才盜賊頭目施放的橫掃劈砍）：

```
  盜賊頭目 以「橫掃劈砍」攻擊 輔助英雄：d20=2 修正 +0 熟練 +2 = 4（目標 11）→ 失手
  盜賊頭目 以「橫掃劈砍」攻擊 標準隊友（弓手）：d20=3 修正 -1 熟練 +2 = 4（目標 11）→ 失手
    木箱 受到 16 點物理傷害［骰 1+6］，HP 15 → 0
  ＊ 木箱 (3, 2) 被摧毀！
  盜賊頭目 攻擊 標準隊友（弓手）：d20=5 修正 -1 熟練 +2 = 6（目標 11）→ 失手
  盜賊頭目 結束回合
— 輔助英雄 的回合（AP 3，移動 5，法力 13/40）
  輔助英雄 的「反射護幕」冷卻結束
  輔助英雄 的「順風」冷卻結束
  輔助英雄 施放「順風」（AP 1，法力 4，冷卻 2 回合）→ 影響 1 格
  輔助英雄 獲得狀態「加速」（2 回合）
  輔助英雄 獲得狀態「護衛」（2 回合）
  輔助英雄 施放「鏡像施法」（AP 1，冷卻 2 回合，源力 1）→ 影響 1 格
    ✦ 輔助英雄 花費源力：源力 1 → 0
  ✦ 輔助英雄 複製了 盜賊頭目 的「橫掃劈砍」（不扣法力與 AP、不進冷卻）→ 影響 4 格
  輔助英雄 以「橫掃劈砍」攻擊 盜賊頭目：d20=19 修正 +0 熟練 +2 = 21（目標 11）→ 命中
    油桶 受到 8 點冰霜傷害［骰 3］，HP 8 → 0
    盜賊頭目 受到 12 點冰霜傷害［骰 6］（格擋/加成 ×1.4），HP 50 → 38
  ＊ 油桶 (5, 3) 被摧毀！
  (5, 2) 出現了油
  (4, 3) 出現了油
  (5, 3) 出現了油
  輔助英雄 攻擊 盜賊弓手：d20=17 修正 +0 熟練 +2 = 19（目標 11）→ 命中
    盜賊弓手 受到 10 點冰霜傷害［骰 6］，HP 3 → 0
  ＊ 盜賊弓手 倒下了！
  ★ 輔助英雄 的被動「調息」觸發（回合結束時，深度 1）（法力 2）
    輔助英雄 回復 9 HP，HP 31 → 40
  輔助英雄 結束回合
```

同一場 `--log-json` 存檔後 `trpg battle replay`：「重播驗證通過：123 個動作、367 個事件，最終狀態一致（oil_depot，種子 4）。」
