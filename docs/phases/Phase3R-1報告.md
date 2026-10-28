# Phase 3R-1 報告｜種族資料與防最佳解驗證

> 規格：`docs/phases/Phase3R計畫.md` 的 3R-1；設計：`docs/design/07-角色成長.md` 7.7、`docs/design/09-世界與敘事.md` 9.6.5。
> 範圍只有資料、schema、驗證與 `trpg content check`；種族技與環境被動的引擎結算、AI 使用條件在 3R-2；開局流程與外觀在 3R-3。

## 1. 交付

| 項目 | 位置 |
|---|---|
| schema 與驗證 | `src/trpg/content/races.py`（`RaceTable`、`OriginTable`、`RaceSkill`、`RacePassive`、`RaceLook`、`forbidden_key_problems`、`race_reference_problems`） |
| 10 族資料 | `content/races.yaml`（名稱、代表界域、1 招種族技、1 項環境被動、預設外觀；數值照 7.7 表） |
| 5 區出身 | `content/origins.yaml`（預設外觀、開場劇情鍵、NPC 態度；不含任何戰鬥數值） |
| 載入與 CLI | `registry.py` 加入兩檔（`trpg content check` 會列出）；`library.py` 新增 `ContentLibrary.races`／`origins` 與跨檔案檢查 |
| 測試 | `tests/content/test_races.py`（53 項） |

## 2. 防最佳解原則 → 驗證規則

| 原則（7.7） | 驗證 | 狀態 |
|---|---|---|
| 1 不給純數值（傷害、命中、暴擊、最大 HP、AP、屬性） | 載入前遞迴檢查禁用欄位名與禁用效果類型（`damage`、`delayed_damage`、`grant_ap`、`heal` 等），訊息：「種族不得給○○（防最佳解原則 1…）」；`extra="forbid"` 擋其餘未知欄位 | 機器檢查 |
| 2 只給功能型、看情境的效果 | 種族技效果類型與環境被動規則都是**封閉清單**（`RACE_EFFECT_SPECS`、`PASSIVE_RULE_SPECS`），各類型只能填自己的參數；推、拉須明寫 `no_collision_damage: true`、投擲須 `no_damage: true`（不加傷害）；元素減傷只能為負且 ≤ 250‰；視線懲罰減免 ≤ 500‰ | 機器檢查 |
| 3 強度小於半個技能欄 | 種族技 `ap_cost` 固定 1、`uses_per_battle` 1～2、`occupies_skill_slot` 必為 false、效果最多 3 個 | 機器檢查 |
| 4 不給元素專屬機制（6.33） | 無法機器檢查（「龍裔 −20% 火焰傷害」本身是 7.7 表指定） | 人工審（見待 PM 決定） |
| 5 主城可重選種族 | 大世界功能，本段不做 | 不適用 |

出身不影響戰鬥：`OriginDef` 無任何數值欄位，同樣套用禁用欄位檢查。

## 3. 驗收條件逐條證據

| 條件 | 證據 |
|---|---|
| 10 族、每族 1 招種族技＋1 項環境被動＋預設外觀 | `test_bundled_races_load`、`test_each_race_has_one_skill_and_one_passive_with_rules`、`test_two_races_per_realm`、`test_table_values_match_design_7_7` |
| 碎界五區出身（預設外觀、開場劇情鍵、NPC 態度），不影響戰鬥 | `test_bundled_origins_cover_five_realms`、`test_origin_cannot_carry_combat_numbers`（6 種戰鬥欄位）、`test_origin_extra_unknown_field_rejected` |
| 故意寫壞（傷害／命中／暴擊／HP／AP／屬性）載入失敗並給中文原因 | `test_pure_numbers_are_rejected`（14 組：種族、種族技、被動各處）、`test_damage_in_effect_params_is_rejected`、`test_damaging_effect_types_are_rejected` |
| 種族技 1 AP、每場 1～2 次、不佔技能欄、不加傷害 | `test_skill_budget_rules`（ap_cost 0／2、次數 0／3、佔欄）、`test_too_many_effects_are_rejected`、`test_push_must_declare_no_collision_damage` |
| 被動只能是環境小規則 | `test_unknown_passive_rule_is_rejected`、`test_passive_resist_is_capped`、`test_passive_cannot_boost_damage_taken_up`、`test_sight_reduction_capped_at_half` |
| 跨檔案：界域、形狀、天氣、地形存在；五區各有出身 | `test_library_rejects_unknown_realm`、`test_library_rejects_unknown_shape`、`test_library_requires_origin_for_every_realm` |
| `trpg content check` 檢查 | `test_content_check_cli_lists_races_and_origins`；指令輸出含「races.yaml：10 個種族…」「origins.yaml：5 個出身（不影響戰鬥）」 |
| 行為一致測試（第 3 節）中屬於 3R-1 的部分 | 防最佳解驗證已完成；「卡片數值＝實戰結算」與「被動有／無種族」表格測試屬 3R-2 |

檢查：`ruff check`、`ruff format --check`、`mypy`（741 檔）通過；`tests/content/test_races.py`、`tests/content/test_loader.py`、`tests/content/test_skill_scaling.py`、`tests/test_architecture.py`、`tests/cli/test_cli.py`、`tests/cli/test_budget_cli.py` 通過。未跑完整 `scripts/check.py`（依守則 11）。

複雜度類 `noqa`：**無新增**。

## 4. 待 PM 決定

1. **種族技效果的表達方式**：7.7 的效果（應變、林隱、狐火誘餌、過充、穩若磐石…）多數無法用現有原語表達（例如「多 2 移動且不觸發藉機攻擊」、「站草叢立刻隱蔽」、「誘餌」、「耐力／法力擇一」；`hurl_object` 原語要求 `dice`、`push`／`pull` 預設吃撞擊傷害）。本段採**種族技專用的封閉效果清單**（`bonus_move`、`ignore_opportunity_attack`、`conceal_self`、`decoy`、`push`、`pull`、`immovable`、`restore_choice`、`hurl_object`、`create_surface`），3R-2 再決定要對映到現有原語、新增原語或直接在引擎實作。
2. **推、拉、投擲「不加傷害」**：資料以 `no_collision_damage`／`no_damage` 旗標宣告。拋錨（拉）也一併設為不吃撞擊傷害；7.7 只明寫龍息震退與蠻力投擲「不加傷害」，拋錨是否仍吃撞擊傷害請確認（較保守＝不吃）。
3. **「森林地圖視線 +1」（精靈）**：目前以地形 `grass` 表達（`sight_bonus_on_terrain`）。專案沒有「森林地圖」標籤，3R-2 需決定是「站在／看向草地」或地圖屬性。
4. **「在岩漿、深淵旁被推時少推 1 格」（獸人）**：以 `terrain: [lava, chasm]` 表達；「旁」的定義（落點或路徑相鄰）留給 3R-2。
5. **龍裔 −20% 火焰傷害**：是 7.7 表指定的元素減傷，但與原則 4「不給元素專屬機制」及「不給純數值」的界線可能有爭議；驗證器只允許「負值、≤ 250‰」的元素減傷，是否要禁止請玩法 PM 裁示。
6. **預設外觀欄位**：`RaceLook` 照 `raceArt.js` 的 `look`（駝峰改底線，如 `hair_color`）；龍裔採定案版（`horns: dragon`、`pattern: dragonscale`、`tail: dragon`、`slit_eyes`、`ridge`、`spines`、`scale_color: #c8402a`）。其餘種族的 `hair`／`ears`／`tail` 等值是自由 ID，畫法與合法值留給 3R-3 對照前端決定。
7. **出身內容**：`default_look`（`outfit_tint`／`accent`）、`npc_attitude`（friendly／neutral／wary，出身地一律 friendly，灰燼荒原對晶冠、雲嶺設為 wary）、`opening_key`（`opening_<界域>`）都是我依 9.6.5 的風格寫的**初值**，開場劇情的實際內容、出身任務與態度細節請玩法 PM 定案；目前沒有任何程式讀取 `opening_key`。
8. **`races.yaml`／`origins.yaml` 為選用**：與 `regions.yaml` 一樣，內容資料夾缺這兩檔時載入不報錯（`ContentLibrary.races`／`origins` 為 `None`），但只有一個存在會報錯。3R-3 開局流程啟用後可改為必備。
9. **每界域種族數**：資料是每區 2 族（照 7.7 表）；驗證器不強制，只有測試 `test_two_races_per_realm` 把關。
