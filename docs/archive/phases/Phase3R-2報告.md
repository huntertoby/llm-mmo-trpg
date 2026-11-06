# Phase 3R-2 報告｜種族技與環境被動結算

> 規格：`docs/phases/Phase3R計畫.md` 4.2；設計：`docs/design/07-角色成長.md` 7.7（含 2026-10-29「實作細節」）。
> 範圍：10 招種族技與 10 項環境被動的引擎結算、合法動作、AI 使用條件、卡片與 HUD、地圖標籤 `forest`、戰鬥紀錄與存檔、`LOG_FORMAT` `/82`。
> 不含：開局選種族與出身的流程、外觀（3R-3）。形態技能（3J-4）由另一個 agent 做，沒有碰。

## 1. 交付

| 項目 | 位置 |
|---|---|
| 種族技動作 `use_race_skill`（合法性、列舉、結算） | `src/trpg/engine/race_skills.py`；動作 `UseRaceSkill`（`engine/actions.py`）；事件 `RaceSkillUsed`（`engine/events.py`） |
| 環境被動查詢（視線、靈覺、元素抗性、滑倒、導電、獸人減距、燃燒、雨天移動） | `src/trpg/engine/rules/race.py`，各結算點只呼叫這裡的函式 |
| AI 使用條件 | `src/trpg/engine/ai/race.py`（`UtilityAI.__call__` 開頭先問） |
| 單位種族欄位 | `UnitTemplate.race`、`UnitState.race`；種族資料嵌入規則包 `Ruleset.races`（重播不依賴資料檔） |
| 地圖標籤 | `MapDef.tags`、`BattleState.map_tags`；`content/maps/dark_forest.yaml` 加 `tags: [forest]` |
| 新狀態與誘餌 | `content/statuses.yaml` 的 `race_adapt`、`race_stonewall`；`content/units/summons/summon_foxfire_decoy.yaml`＋`summon_looks.yaml` |
| 推擊效果新欄位 | `PushEffect.pull`（拉不吃獸人減距）、`PushEffect.harmless`（被擋只停下、不算撞擊） |
| 前端 | `client/src/battle/race.ts`（模式、卡片文字、HUD 文字）；`SkillBar` 的種族技按鈕組（金邊、浮動卡）；`Hud`／`UnitInfo` 種族行；狀態圖樣 `race_adapt`、`race_stonewall` |
| 指定種族的入口 | `trpg battle --ally-race／--enemy-race`、`trpg run new|auto --race`、`POST /api/runs` 的 `race`、build 英雄的 `hero.race`（資料欄位） |
| 紀錄格式 | `LOG_FORMAT` `/81` → `/82`（`runner.py` 文件字串與測試字面值一起改） |

## 2. 種族技效果對映（「最少新程式」的做法）

3R-1 的封閉效果清單不新增原語，也不走技能解譯器（種族技是動作，不是技能），直接對映到既有的效果佇列：

| 效果 | 種族 | 對映 |
|---|---|---|
| `bonus_move` | 人類 應變 | 直接加 `move_points`；另有 `ignore_opportunity_attack` 對映到狀態 `race_adapt`（`reactions.opportunity_attacks` 開頭略過；到自己下回合開始失效） |
| `conceal_self` | 精靈 林隱 | `ApplyStatusEffect concealed`；必須站在草叢（`conceal` 物件）或黑暗表面，已隱蔽或被揭露時不合法 |
| `decoy` | 狐族 狐火誘餌 | 新增 1 HP 的誘餌單位（召喚物範本 `summon_foxfire_decoy`，不行動），`reactions.try_intercept` 最前面攔下敵人對該陣營「已命中的單體攻擊」（普攻與技能共用），誘餌隨即消失（`summon_expired` 原因 `decoy_hit`）；同時只有一個、3 輪後消散 |
| `push` | 龍裔 龍息震退 | 錐形內所有單位（不含自己，由遠到近）各一個 `PushEffect(harmless=True)` |
| `pull` | 海民 拋錨 | `PushEffect(pull=True, harmless=True)`，方向＝目標往施放者的主軸向 |
| `immovable` | 矮人 穩若磐石 | 狀態 `race_stonewall`：`world.push_distance` 回 0（推、拉、風、衝撞都擋；基本動作推擊變成不合法）、`apply_status` 擋 `prone` |
| `restore_choice` | 晶能義體人 過充 | 直接回復耐力或法力（動作帶 `choice`），不超過上限，滿了不合法 |
| `hurl_object` | 獸人 蠻力投擲 | `HurlObjectEffect(ignite=False)`，不加傷害，其餘照物件規則 |
| `create_surface` | 角魔 炎印、鱗族 潮息 | `CreateSurfaceEffect`（自身一格／3×3 方陣，隊伍標記為施放者陣營） |

被動對映（`engine/rules/race.py`）：

| 被動 | 結算點 |
|---|---|
| 人類 明視 | `geometry.sight_range(state, viewer)`：天氣縮減的視線距離回復 500‰（進位）；`combat.concealed_max_distance(state, viewer)`：夜晚縮短的隱蔽選取距離同樣回復 |
| 精靈 林間視野 | 同 `sight_range`：地圖帶 `forest` 標籤時 +1（`sight_bonus_on_map_tag`，取代 3R-1 的 `sight_bonus_on_terrain`／草地） |
| 狐族 靈覺 | `combat.sees_hidden`：2 格內隱蔽單位對他無效（無劣勢、無選取距離限制）；`traps.detect_traps`：移動抵達、回合開始、敵人在身旁放陷阱時揭露 2 格內的敵方陷阱 |
| 龍裔 耐火鱗 | `lifecycle.make_unit`：開戰時把火元素 −200‰ 併入 `element_mods`（與一般元素抗性同公式） |
| 矮人 穩健步伐、鱗族 流線身形 | `handlers.enter_surface`：冰面的滑倒檢定略過（鱗族水與冰都不滑） |
| 晶能義體人 絕緣 | `interactions` 的導電：站在水上的義體人不在導電對象內 |
| 獸人 沉穩重心 | `world.push_distance(…, direction)`：「推」的路徑（含落點）有岩漿或深淵時距離 −1（最少 0）；拉與傳送不減；事件 `push_resisted` 原因 `race_heavy` |
| 角魔 炎膚 | `surface_entered` 觸發與 `turns._surface_turn_start`：火焰表面的燃燒略過 |
| 海民 雨中海步 | `statuses.move_points_for_turn(…, weather_id)`：下雨 +1 |

## 3. 驗收條件逐條

| 條件 | 證據 |
|---|---|
| 1. 10 招種族技與 10 項環境被動照 7.7 結算 | `tests/engine/test_race_skills.py`（33 項，每招一組）、`tests/engine/test_race_passives.py`（36 項，每項 × 有／無該種族）；`test_every_passive_rule_has_a_behaviour_test` 鎖住封閉清單 |
| 2. 種族技 1 AP、每場 1～2 次、不佔技能欄；合法動作、卡片、HUD 另列；AI 會用 | `test_race_skill_costs_one_ap_and_counts_its_uses`、`test_uses_per_battle_limit_is_enforced`、`test_legal_actions_list_race_skill_and_every_one_resolves`；前端 `race.test.ts`（13 項）、瀏覽器實測（第 5 節）；`test_race_battles.py::test_ai_uses_the_race_skill_and_the_replay_matches`（7 個種族在 `dark_forest` 三個種子內 AI 一定會用） |
| 3. 地圖標籤 `forest`：`dark_forest` 加上，其他依草叢多寡判斷 | 只有 `dark_forest`（見第 4 節判斷依據）；`test_forest_tag_is_on_dark_forest_only`、`test_elf_forest_sight_bonus_only_on_forest_maps` |
| 4. 種族來源：主角（一輪）與 reference build 可指定；沒指定時無種族 | `with_race`（`roguelite/start.py`）、`trpg run new --race`、`POST /api/runs` 的 `race`、`trpg battle --ally-race`、build 英雄 `hero.race`；`tests/roguelite/test_race_start.py`、`tests/cli/test_race_cli.py`、`tests/api/test_runs_api.py`（2 項）；沒指定＝無種族（見待 PM 決定 #9） |
| 5. 行為一致測試 | 每項被動 × 有／無種族：`test_race_passives.py` 全部；每招種族技卡片＝實戰：`test_race_skills.py` 的 `_numbers(description_zh)` 對照資料與結算（應變 +2、誘餌 2 格、震退 1 格、過充 10、投擲 2 格、潮息 2 格、拋錨 2 格／4 格）；獸人被推 × 路徑上有無岩漿／深淵 × 來源：`test_orc_is_pushed_one_less_when_the_path_ends_in_lava_or_chasm`（岩漿、深淵）、`test_orc_reduction_counts_hazards_anywhere_on_the_path`、`test_orc_is_not_reduced_without_hazard_on_the_path`、`test_orc_is_not_helped_when_pulled`、`test_orc_reduction_applies_to_wind_pushes`、`test_orc_shove_action_is_illegal_when_reduction_leaves_zero`（技能推擊／風／基本動作推擊；衝撞推開與技能推擊同為 `PushEffect`，由前者覆蓋）；拋錨被擋就停、不吃撞擊：`test_anchor_haul_stops_when_blocked_and_never_collides`；重播一致：`test_ai_uses_the_race_skill_and_the_replay_matches`、`tests/cli/test_race_cli.py::test_battle_with_ally_races_uses_race_skills_and_logs_them`（含 `battle replay`） |
| 6. 驗收指令 | pytest（engine、content、skillgen、narrative、roguelite、api、`-m "slow or not slow" tests/cli --timeout=3000`）：見第 6 節；vitest 1080 項（含 race.test.ts 13 項）、`corepack pnpm -C client build`、`ruff check`、`ruff format --check`、`mypy`（750 檔）、`lint-imports`（7 契約）通過；一場含種族技的重播：`trpg battle --map dark_forest --seed 1 --ally-race fox,fox,fox --log-json …` 後 `trpg battle replay` 顯示「最終狀態一致」 |

## 4. 地圖標籤判斷（規格第 3 點）

草叢多寡（草地格／草叢物件）：`dark_forest` 草地 92／100 格＋22 個草叢物件（竹林，`archetype: forest`）→ **加 `forest`**。`open_plain` 草地 94／100 但沒有任何草叢物件（草原不是森林）、`swamp` 只有 4 個草叢物件（沼澤）、`training_range` 3 個（靶場）、其餘 0 → **不加**。新增森林地圖只要在地圖檔寫 `tags: [forest]`，不改程式。

## 5. 前端實測（瀏覽器，`trpg serve --port 8014`，已停止）

- 用 API 的 `race` 開一輪（海民）：技能列多一組金邊的種族技按鈕「拋錨　1 AP・剩 1／1 次」；沒有合法目標時灰掉。窄版 HUD 多一段「種族：海民｜拋錨 剩 1／1 次｜被動：雨中海步（目前有作用）」（沼澤是雨天，被動亮起）。
- 浮動卡（共用 `useFloatCard`，沒有自己實作彈出層）：滑過按鈕顯示 → 滑進卡片仍開著 → Esc 關閉；800×600 時卡片完整在視窗內、頁面沒有橫向捲動（1024×768 同）。卡片內容短，沒有捲動需求。
- 沒做完整點擊流程（選種族的開局介面在 3R-3，目前要靠 API 指定）；「按鈕→選目標→送出」由 vitest 的模式與目標登記測試涵蓋（`race.test.ts`）。

## 6. 測試與檢查

見檔尾「最終檢查」。複雜度類 `noqa`：**無新增**（`library.load_library` 的 C901／PLR0912 以抽出 `_check_unit_races` 解決；`handlers.apply_status` 以抽出 `_status_blocked` 解決）。

## 7. 待 PM 決定

1. **狐火誘餌的語意**：7.7 只寫「敵人的下一次單體攻擊打它」。我做成：①誘餌是單位（1 HP、不行動、3 輪消散、同時 1 個）；②攔下「該陣營任何人」被敵人單體攻擊「命中後」的第一下（沒命中不消耗）；③誘餌被攔下後立刻消失、這次攻擊整個落空（等於誘餌吃掉）；④敵人也可以直接攻擊誘餌。要不要限定只保護施放者本人、或改成「攻擊前轉向」請裁示。
2. **蠻力投擲「油桶照樣會爆」**：照引擎的物件規則（`HurlObjectEffect`）：油桶只在技能帶火元素或落點有火焰時才爆；種族技不帶火，所以只在落點有火時爆炸。若設計意圖是「丟出去一定爆」要另外決定（那會變成傷害來源，與原則 1 衝突）。
3. **明視的進位與範圍**：「懲罰減半」我取回復 500‰、**進位**（對玩家有利）：濃霧視線 12 → 18；夜晚隱蔽目標選取距離 1 → 2。**不**處理濃霧的「遠程超過 4 格有劣勢」（那是命中劣勢，不是視線）。要不要連它也減半請裁示。
4. **鱗族「在水與冰面上移動不花額外點數」**：引擎本來就沒有水與冰面的額外移動花費（只有高度差），所以這半句目前沒有效果可給，被動實際只有「不滑倒」；測試鎖住「花費與平地相同」。若要有意義，需要另外的「水地形減速」機制（不在本段）。
5. **靈覺的揭露時機**：隱蔽單位在 2 格內時，對狐族視為不隱蔽（攻擊無劣勢、無選取距離限制）；陷阱在「移動抵達、回合開始、敵人在他身旁放陷阱」時揭露（不是連續偵測）。
6. **穩若磐石「2 回合」**：狀態 `duration: 2, expires: turn_end`＝施放的這個回合與下一個自己的回合結束時消失（中間敵人行動時有效）；狀態 `polarity: neutral`，不能被奪取或驅散。
7. **龍息震退／拋錨的對象**：龍息推開錐形內所有單位（含友軍；AI 有友軍在錐內不吐，玩家自行負責），錐內沒有單位不能用；拋錨只能對敵人、目標在 2 格以上（相鄰不合法）。拋錨拉的方向是「目標往施放者」的主軸向，斜向時取較長的軸。
8. **種族預設**：沒指定＝無種族（保守做法）；sim build、`trpg sim`、build 矩陣不帶種族，平衡階段要看「過充」「應變」勝率時，用 `--ally-race` 或 build 的 `hero.race` 指定。AI 使用條件（`ai/race.py`）是合理時機的啟發式，不追求最佳；獸人的蠻力投擲條件很嚴（只丟落點有火的油桶），三個種子裡常常用不到。
9. **`UnitSummoned` 事件給誘餌**：誘餌用既有的 `unit_summoned` 事件出現（`skill_id` 是種族技 ID，不是技能），日誌會寫「○○ 召喚了 狐火誘餌」；若要專屬文字請玩法 PM 給。種族技的前端選取沒有做「選落點時的預覽格子」（沿用技能的目標登記與預覽 API，預覽會正確顯示，但不另外畫範圍）。
10. **API 的 `race`**：`POST /api/runs` 新增選填欄位 `race`（未知種族回 422）。這是給 3R-3 開局介面接的水管；3R-3 若要改成別的形狀（例如放進開局配點）可以直接改。

## 最終檢查（最後一個程式 commit 之後）

- `pytest -n 8 -m "slow or not slow" tests --ignore=tests/llm --timeout=3000`：**8359 passed**、1 skipped、3 xfailed、1 xpassed（xfail／xpass 是既有的平衡延後項目 `test_demo_balance`），含 engine、content、skillgen、narrative、roguelite、api、cli（含 slow）、sim、shared、架構測試。
- `ruff check`、`ruff format --check`（1049 檔）、`mypy`（750 檔）、`lint-imports`（7 契約全 kept）、`trpg content check`（415 檔）通過。
- 前端：vitest 112 檔 1080 項、`tsc --noEmit`、`corepack pnpm -C client build` 通過；OpenAPI、`schema.d.ts` 與前端夾具已重產。
- CLI 快照（`tests/cli/snapshots/cli_output_hashes.json`）已用 `UPDATE_CLI_SNAPSHOTS=1` 更新（`LOG_FORMAT` 改為 `/82`）。
- 未跑完整 `scripts/check.py`（依守則 11，由 PM 跑）。
- 與 3J-4 合併時的衝突點：`LOG_FORMAT`（取較大＋1、`runner.py` 文件字串兩段都留、測試字面值一起改）、CLI 快照（取 `--theirs` 再重產）、`client/openapi.json`／`schema.d.ts`／前端夾具（重產）、`content/statuses.yaml`、`content/units/summons/`、`tests/content/test_summon_content.py`／`test_summon_looks.py`／`test_con_hp.py` 的清單。
