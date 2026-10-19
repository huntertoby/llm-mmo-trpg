# Phase 3C-5b 報告：穿透 `pierce` ＋ 三種物件原語的 AI 與網頁預覽

## 1. commit

| commit | 內容 |
|---|---|
| f397e50 | 穿透：技能欄位 `pierce`、修正規則 `grant_pierce`、核心規則 `pierce_behind_permille`、預算（`pierce_bonus_permille`、`grant_pierce` 點數）、事件 `shot_pierced`、紀錄文字、兩個示範技能與 build_ranged 裝備、`LOG_FORMAT` `/17`；`tests/engine/test_pierce.py`（18） |
| bc39f43 | AI：投擲與推倒的便宜估計（`engine/ai/scene_objects.py`）；`sim maps` 統計 `scene_events` 並新增 `--ally-build`；`tests/engine/test_scene_ai.py` |
| 600dc46 | 卡路檢查模擬推倒（0.11 #7，`sim/push_check.py`）；`tests/sim/test_push_check.py` |
| 4ca4dff | 預覽資料 `Preview.pierce／topples／hurls` 與 API `PreviewOut` 對應欄位、重新產生 `openapi.json`／`schema.d.ts`；`tests/engine/test_scene_preview.py`、API 測試 |
| d05d962 | 網頁：投擲「選物件 → 選落點」兩段選取（0.11 #4）、穿透路線／穿過的物件、推倒壓住範圍、投擲物件與落點的標記與預覽文字；vitest |
| 29bee8b | 測試：AI 穿透、推倒戰鬥的重播 |
| （本報告） | 報告 |

（開發期間 main 上沒有其他 session 的 commit。）

## 2. 交付項目

### 2.1 穿透（7A.4）

- **技能欄位 `pierce: true`**（`SkillDef.pierce`）。schema 檢查：主動技能或反應技、形狀只能是 `single`（射程必須大於 1）或 `line`、`weapon_req` 不能是近戰、必須有傷害效果。實際生效另看引擎：近戰性質的技能（武器射程 ≤ 近戰上限）不會穿透，所以 `grant_pierce` 套到近戰武器技也無效（`targeting.pierce_active`）。
- **無視半掩護**：`AttackProfile.pierce` 為真時 `half_cover` 回傳 `None`（命中判定與預覽共用同一條路徑）。全掩護與視線規則不變：石柱（阻擋視線）照樣擋住單體技與直線。
- **穿過 `penetrable` 物件**（`engine/pierce.py` 的 `pierce_trace`，只讀狀態）：
  - 單體：施放者到目標的 Bresenham 直線（只畫一個方向）上的 `penetrable` 物件（木箱、倒木）。物件受 **全額傷害**（沒有 700‰ 折扣；即使這一擊失手也一樣，與範圍技對物件的傷害一致），目標受 `pierce_behind_permille`（初值 700‰，`content/rules/core.yaml`）。
  - 直線：影響範圍依距離排序，第一個 `penetrable` 物件之後的所有單位都受 700‰；物件前面的單位全額。直線遇到阻擋視線的物件仍停在它那一格（既有規則）。
  - 新事件 `shot_pierced`（施放者、技能、穿過的物件與位置、後方單位、折扣、路線），只在射線穿過至少一個物件時發出；CLI 文字：`➤ 「穿甲箭」穿過了 倒木 (4, 3)，後方 盜賊2 只受 70% 傷害`。
- **改造型 `grant_pierce`**：`ModifierChange.grant_pierce: true`（只能是 `true`、只能套在 `skill_tags`／`all_skills`，基本動作不行；條件只能看持有者自己）。示範技能「穿木箭術」`skill_timber_piercer`（epic 改造型）：帶 `ranged` 標籤的技能獲得穿透。
- **預算**：`content/skill_budget.yaml` 新增 `pierce_bonus_permille: 150`（有 `pierce` 的技能總點數 × 1.15，在 `trpg skills budget` 顯示為協同「pierce ×1.15」）與 `modifier.points_milli.grant_pierce: 1200`（每次使用的價值；3 次使用 ≈ 3.6 點）。全部是初值、未經模擬。
- **示範技能**（皆通過預算與結構驗證，裝備在 `build_ranged`）：

| 技能 | 內容 | 預算 |
|---|---|---|
| 穿甲箭 `skill_armor_piercing_arrow`（rare，武器技，AP 2） | 單體、武器射程、傷害 ×1.4、`pierce: true`；法力 5、冷卻 2 | 71.6% |
| 穿木箭術 `skill_timber_piercer`（epic，改造型） | `skill_tags: [ranged]` → `grant_pierce` | 85.7% |

- 隨機組合器不產生 `pierce`（欄位預設 `false`，既有種子的隨機技能不變）。
- 技能卡片的形狀文字加上「・穿透」（`narrative.skills.skill_shape_text`，`skills list／show` 與網頁卡片共用）；改造規則文字「遠程單體與直線技能獲得穿透（無視半掩護，穿過木製物件）」。

### 2.2 AI（7A.5）

- `engine/ai/scene_objects.py`：`UtilityAI` 對每個技能原本就是「便宜估計 → 每種技能只保留前 `skill_candidates` 個跑完整 `preview`」，但投擲的估計只看落點格上有沒有單位，推倒只看物件有沒有 HP，所以大多數好的組合進不了候選。新增 `scene_estimate`（純幾何、不跑引擎）：
  - 投擲：落點單位（敵 +3、友 −3）＋ 物件 `explosive` 時爆炸半徑（切比雪夫）內的單位；沒有任何敵人受影響就不納入候選。列舉（物件 × 落點）再多也只對前幾名跑完整預覽（`test_the_number_of_full_previews_per_skill_stays_bounded`）。
  - 推倒：物件往遠離施放者的主要軸向倒下，`topple_line` 壓住的單位（敵 +3、友 −3）；沒有敵人被壓就不納入。
- **穿透**不需要額外的 AI 程式：命中率來自預覽（`skill_profile` 已帶 `pierce`），掩護後的敵人命中率更高（`test_the_ai_sees_the_pierce_hit_chance_behind_cover`）。
- **`trpg sim maps` 新增兩項**（讓驗收條件 2 可以量測）：
  - `--ally-build a,b`：我方改用 build 英雄（不足 3 人以標準隊友補齊，與 `trpg battle --ally-build` 相同；預設陣容的英雄沒有這些技能，所以不指定 build 就不會有使用紀錄）。
  - 報表新增「場景物件（整批合計）」：`scene_events`（`hurled`／`toppled`／`pierced` 的事件次數；`BattleMetrics.scene_events`、`BatchReport.scene_events`，預設空，JSON 向下相容）。
- 使用紀錄（`trpg sim maps --maps <地圖> --ally-build <build> --seeds 5`，種子 0–4；下表為事件次數，括號內為該技能的使用次數／場）：

| build | 地圖 | 場景物件事件 |
|---|---|---|
| build_ranged（穿甲箭） | narrow_halls | 0（穿甲箭 1.60 次／場） |
| | oil_depot | 穿透 1 |
| | ruined_fort | 0（1.40 次／場） |
| | dark_forest | 穿透 6 |
| | swamp | 穿透 1 |
| | cliff_outpost | 穿透 2、推倒 1 |
| | lava_crossing | 穿透 2 |
| build_fire（念力投擲） | narrow_halls | 投擲 6（1.20 次／場） |
| | ruined_fort | 投擲 3（0.60） |
| | cliff_outpost | 投擲 3（0.60） |
| | oil_depot／dark_forest／swamp／lava_crossing | 0 |
| build_push（震地推倒） | cliff_outpost | 推倒 1（震地推倒 0.20 次／場） |
| | lava_crossing | 推倒 3（互動推石柱，不是技能） |
| | narrow_halls／oil_depot／ruined_fort／dark_forest／swamp | 0 |

  三種都有紀錄；推倒偏少（見待決 #3）。

### 2.3 卡路檢查模擬推倒（0.11 #7）

`sim/push_check.py` 的 `_find_topples`：對每個 `topplable` 物件、四個方向各模擬一次推倒（`topple_line`：原格空出、倒塌物擋在最後一格），報表多兩欄「可推倒物件」「單次推倒會封路」；原本不通的地圖也列出「推倒後能打通」（併入「單次移動可打通」欄，前綴「推倒」）。`uv run python scripts/map_push_check.py`：10 張正式地圖狀態全部「通」，單次移動與單次推倒都沒有封路。

### 2.4 網頁（7A.5，PM 用瀏覽器驗收）

- **投擲兩段選取（0.11 #4）**：`TargetSet.hurls`（物件 → 落點 → 動作）取代「每個物件只取第一個落點」。選了投擲技能後：第 1 段紅框標出可舉起的物件，點物件 → 該物件以青色粗框標示，紅框改成它的合法落點（第 2 段）；點落點送出；再點別的物件改選、點同一個物件取消；面板顯示「第 1 段／第 2 段」提示與「重選物件」。Esc／右鍵／換技能／回應更新都會回到第 1 段。複製技能（`copy_skill`）複製投擲技能時同樣兩段（送出走 `/decision`）。
- **預覽**（`PreviewOut.pierce／topples／hurls`，由引擎 `Preview` 提供；舊測試的假資料缺欄位時視為空）：
  - 穿透：路線上的黃點、穿過的物件青框「穿」、後方單位橘框「70%」；文字「穿透：穿過倒木(2, 5)（物件受全額傷害），後方 … 只受 70% 傷害」，沒有穿過物件時「穿透：無視半掩護」。
  - 推倒（互動的推、推擊技能、推倒技能，對 `topplable` 物件）：壓住的格子紅色斜線「壓」、倒塌物位置「礫」；文字「推倒：石柱(4, 2)往東倒下，壓住 (6, 2)（壓到 …）；倒塌物留在 (6, 2)」。
  - 投擲：被舉起的物件「舉」、落點「落」；文字「投擲：油桶(3, 3) → (3, 2)，在落點爆炸」，連鎖列出爆炸。
- 已用瀏覽器（本機 `trpg serve`）實際操作驗證下列三個情境（重現步驟見待決 #9）。

## 3. 驗收條件逐條（3C-5b）

1. **穿透**（`tests/engine/test_pierce.py`，18 個，全過）
   - 無視半掩護：`test_pierce_ignores_half_cover`（對照一般火焰箭 −2、穿透 0）、`test_the_preview_hit_chance_ignores_cover_and_matches_the_roll`。
   - 穿過 `penetrable` 物件、物件與後方目標都受傷、後方打折：`test_the_shot_passes_a_crate_which_takes_full_damage_while_the_target_takes_70_percent`（木箱受全額、目標 700‰、`shot_pierced` 內容）、`test_a_fallen_log_is_pierced_too_and_a_shot_without_objects_emits_nothing`、`test_the_line_passes_a_crate_and_only_the_units_behind_it_are_discounted`（直線：木箱前不打折、後面兩個都打折）、`test_a_penetrable_object_beside_the_route_is_untouched`。
   - 被石柱擋住：`test_a_stone_pillar_still_blocks_the_shot`（單體：視線被擋）、`test_a_pillar_stops_the_line`（直線：後方打不到）。
   - `grant_pierce` 有效：`test_grant_pierce_gives_a_tagged_skill_pierce`（火焰箭有／沒有穿木箭術）、`test_grant_pierce_needs_the_tag_the_shape_and_a_ranged_skill`、`test_a_basic_attack_cannot_pierce`。
   - schema 與預算：`test_pierce_is_limited_to_ranged_single_and_line_skills`（5 組不合法）、`test_grant_pierce_must_be_true_and_cannot_target_basic_actions`、`test_pierce_adds_the_budget_bonus_from_the_content_file`；`tests/content/test_modifier_schema.py::test_every_change_kind_has_a_valid_example` 含 `grant_pierce`。
2. **AI 使用紀錄**：見 2.2 的表（`trpg sim maps --ally-build …`，三種原語都有次數）。測試：`tests/engine/test_scene_ai.py`（投擲估計含爆炸範圍、木箱只在落在敵人身上時有估計、AI 選油桶與敵人旁的落點、候選數有上限、推倒估計需要敵人在倒下的方向上、AI 推倒石柱壓到兩個敵人、穿透命中率、`sim` 事件統計與 `--ally-build`）；重播：`test_an_ai_battle_with_pierce_shots_replays`（dark_forest 種子 0、build_ranged）、`test_an_ai_battle_with_a_topple_replays`（lava_crossing 種子 0、build_push）。
3. **網頁預覽三種都能顯示**：vitest 92 個（原 78，新增 14）——`scenePreview.test.ts`（標記與文字：穿透路線／物件／後方單位、推倒壓住格與倒塌物、投擲舉起與落點、四個方向名稱、併入預覽文字）、`targeting.test.ts` 的「hurling an object」（依物件分組、第 1 段高亮可舉起的物件且點擊不產生動作、第 2 段只高亮該物件的落點並回傳該物件的動作、同一落點兩個物件各得各的動作、提示文字）。伺服器端：`tests/engine/test_scene_preview.py`（7）、`tests/api/test_hurl_api.py::test_the_preview_of_a_pair_shows_the_object_and_the_landing`、`tests/api/test_routes.py` 的預覽欄位集合。畫面請 PM 用瀏覽器驗收（重現步驟見待決 #9）。
4. **`check.py` 全過；重播一致**
   - `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（1993 passed）、client install／typecheck／vitest（92）全部通過。
   - 重播：`trpg battle --map dark_forest --seed 0 --ally-build build_ranged --log-json …` → `trpg battle replay`（測試 `test_an_ai_battle_with_pierce_shots_replays`）通過；lava_crossing 種子 0 build_push 同（推倒）；既有的投擲重播測試（`test_an_ai_battle_hurls_objects_and_replays`）仍通過。

## 4. 0.11 必修項

- **#4 網頁兩段選取**：完成（2.4）。
- **#7 卡路檢查模擬推倒**：完成（2.3）。
- **#9 AI 評估**：完成（2.2；推倒的 AI 使用率仍低，見待決 #3）。

## 5. 修改既有測試的原因

- `tests/content/test_modifier_schema.py`：`VALID_CHANGES` 補 `grant_pierce`（斷言「每種 change 都有合法範例」）。
- `tests/cli/test_budget_cli.py`：技能數 80 → 82（兩個示範技能，三處斷言）。
- `tests/cli/test_battle_cli.py`、`test_skills_cli.py`：`LOG_FORMAT` `/16` → `/17`。
- `tests/api/test_routes.py::test_preview_returns_the_numbers_and_does_not_change_the_session`：預覽回應的欄位集合多了 `pierce`、`topples`、`hurls`。
- `tests/sim/test_push_check.py::test_official_maps_are_all_connected_and_the_table_renders`：另外斷言沒有「單次推倒會封路」且有可推倒物件。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json` 2 筆）：`skills_list`、`skills_show_all`（多 2 個技能、形狀文字多「・穿透」）。其餘 7 筆（含全部戰鬥）不變。

## 6. 新增的複雜度 noqa

**無**（沒有新增 C901、PLR0911、PLR0912、PLR0915）。`budget._modifier_value` 加入 `grant_pierce` 後差點超過 PLR0911，改成併入既有的「沒有數值的改變」查表；`skill_estimate` 只加一個 return；`metrics_from_events` 既有的 noqa 涵蓋新增的分支。

## 7. `LOG_FORMAT`

**升為 `trpg-battle-log/17`**（本段只升一次）。新欄位與事件：技能 `pierce`、修正規則 `grant_pierce`、核心規則 `pierce_behind_permille`、事件 `shot_pierced`。`/16` 的紀錄沒有穿透技能，內容與事件不變，但規則包與事件種類不同，保守起見升版。

## 8. 待 PM 決定（最多 10 點）

1. **單體穿透也打折、有掩護時反而不划算**：規格寫「直線或射線上遇到 penetrable 物件時…後方目標受 700‰」，我把單體射線（施放者到目標的直線）也當成射線處理：目標與施放者之間的木箱／倒木只要在路線上，目標就只受 700‰（物件受全額）。木箱緊鄰目標時等於「換掉 −2 命中（約 +10% 命中率），付出 −30% 傷害」，對傷害不一定划算（穿甲箭的價值在命中率與同時打破掩護物）。若希望「穿透不吃折扣、只無視掩護」，把 `pierce_trace` 單體分支的 `behind` 設成空即可；`pierce_behind_permille` 也可調。
2. **穿透的路線只畫一個方向的 Bresenham**（施放者 → 目標）；視線檢查是雙向（既有規則）。斜向時兩條線可能經過不同的格子，目前只認施放者出發的那條。`penetrable` 物件目前只有木箱與倒木，沒有「木牆」。
3. **推倒的 AI 使用率仍低**：AI 只有「目前就能壓到敵人」才會推倒（估計＋預覽），不會為了推倒而先走位。`sim maps --seeds 5` 的 build_push 只有 cliff_outpost（1 次技能）與 lava_crossing（3 次互動推石柱）有紀錄；ruined_fort、narrow_halls、dark_forest 都是 0。要提高使用率需要在位置價值加「站在可推倒物件旁、敵人在倒下方向上」的項目，這會影響所有單位，這一段沒有做。
4. **投擲的使用率集中在走廊與廢墟**：build_fire 在 oil_depot 5 個種子都沒有投擲（油桶多、AI 先用火焰技能引爆）。`scene_estimate` 的分數（敵人 +3、友方 −3）是啟發式初值，與其他技能的便宜估計同一量級。
5. **`sim maps` 新增 `--ally-build`**：規格沒有要求，但驗收條件 2 需要它（預設陣容沒有這三種技能，不改陣容就不可能有使用紀錄）。輸出開頭多一行「我方 build：…」，沒有指定時與原本逐字相同。`BattleMetrics`／`BatchReport` 新增 `scene_events`（預設空），`sim maps --json` 的舊報表仍可讀。
6. **`pierce` 的限制放在 schema 與引擎兩層**：schema 只擋明顯不合法的組合（近戰武器技、非單體／直線形狀、射程 1 的單體、沒有傷害）；是否算「遠程」（武器射程 > 近戰上限）在施放時才判斷，所以 `weapon_req: any` 的法術技、或配近戰武器的 `grant_pierce` 目標不會報錯，只是不穿透。
7. **傷害文字把穿透折扣標成「格擋/加成 ×0.98」**：折扣包在傷害事件的 `multiplier_permille` 裡（與格擋、修正規則的倍率相乘），CLI 的傷害行沒有單獨說明；穿透有獨立的 `shot_pierced` 行（含 70%），所以資訊不缺，只是傷害行的倍率來源不明。要拆開需要在傷害事件加欄位（會再升 `LOG_FORMAT`）。
8. **預算全是初值、未經模擬**：`pierce_bonus_permille: 150`、`grant_pierce` 每次 1.2 點（使用次數沿用修正技能的表，3 次）、`pierce_behind_permille: 700`。穿甲箭 71.6%、穿木箭術 85.7%，都在合格區間的下緣到中段。3C-6 的 `sim matrix` 才看得出穿透射手在哪些地圖強。
9. **網頁畫面請 PM 驗收**（已用瀏覽器實測，截圖未存檔）：
   - 投擲兩段選取：`narrow_halls`、build 火焰流、種子 `9`；第 1 輪主角行動時選「念力投擲」→ 紅框三個物件（木箱、油桶、木箱）→ 點 (3, 3) 的油桶（青框）→ 紅框變成落點 → 滑過 (3, 2)：預覽「投擲：油桶(3, 3) → (3, 2)，在落點爆炸」。
   - 推倒：`ruined_fort`、build 位移流、種子 `6`；第 1 輪先移動到 (3, 2)（石柱 (4, 2) 的西邊），選「推動物件」滑過石柱：壓住 (6, 2)（(5, 2) 是牆，跳過）、倒塌物留在 (6, 2)。
   - 穿透：`swamp`、build 遠程、種子 `0`；第 1 輪選「穿甲箭」滑過敵人 d（盜賊頭目）：路線黃點、倒木 (2, 5)「穿」、d 標示「70%」。
10. **其他小處**：(a) 預覽的 `topples`／`hurls` 取自最多後果的模擬事件，推倒由「推的成功與否」決定時（推擊技能對石柱）預覽可能顯示「會倒」而實際失手時不倒；(b) 投擲兩段選取沒有在物件上預覽「舉起後」的狀態，第 1 段只高亮不預覽；(c) 倒塌物仍不可破壞（0.11 #7 轉給玩法 PM）。

## 9. 代表性輸出

`uv run trpg battle --map dark_forest --seed 0 --ally-build build_ranged`（輸出第 44–62 行，連續未刪節；遠程英雄移到 (3, 2)，用穿甲箭穿過倒木 (4, 3) 打後方的盜賊2——木箱（倒木）受全額傷害、盜賊2 只受 70%；接著「穿木箭術」讓高處狙擊也獲得穿透，失手時倒木照樣受傷）：

```
— 遠程英雄 的回合（AP 3，移動 5，法力 24/24）
  遠程英雄 施放「時隙湧流」（AP 1，冷卻 2 回合，源力 1）→ 影響 1 格
    ✦ 遠程英雄 花費源力：源力 1 → 0
    遠程英雄 獲得 2 AP（現在 4 AP）
  遠程英雄 從 (0, 3) 移動到 (3, 2)（消耗 4 移動）
  遠程英雄 施放「穿甲箭」（AP 2，法力 5，冷卻 2 回合）→ 影響 1 格
  遠程英雄 以「穿甲箭」攻擊 盜賊2：d20=13 修正 +0 熟練 +2 = 15（目標 11）→ 命中
  ➤ 「穿甲箭」穿過了 倒木 (4, 3)，後方 盜賊2 只受 70% 傷害
    倒木 受到 10 點物理傷害［骰 3］，HP 20 → 10
    盜賊2 受到 11 點物理傷害［骰 7］（格擋/加成 ×0.98），HP 30 → 19
  遠程英雄 施放「高處狙擊」（AP 2，法力 5，冷卻 2 回合）→ 影響 1 格
  遠程英雄 以「高處狙擊」攻擊 盜賊2：d20=4 修正 +0 熟練 +2 = 6（目標 11）→ 失手
  ➤ 「高處狙擊」穿過了 倒木 (4, 3)，後方 盜賊2 只受 70% 傷害
    倒木 受到 7 點物理傷害［骰 3］，HP 10 → 3
  遠程英雄 結束回合
— 盜賊1 的回合（AP 3，移動 5）
  盜賊1 從 (9, 6) 移動到 (7, 3)（消耗 5 移動）
  盜賊1 獲得狀態「防禦」
  盜賊1 結束回合，保留 1 AP
```
