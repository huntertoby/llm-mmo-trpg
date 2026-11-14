# Phase GB-3 報告｜巨型頭目 AI（T17、T18；殼縫算背後、部位站位）

> 實作者（Opus 5.5），2026-11-14，起點本機 main `cb83fc060`（含 GB-2、GB-2b）。中途使用者電腦關機，worktree 沒有留下改動，從頭重做；改前基準與比對都在重做後重跑。
> 依據：`docs/phases/PhaseGB計畫.md` 第 7 節、第 4 節 GB-3 列、0.3 T17、T18、第 11、12 節、末節開發 PM 裁定；`PhaseGB-1c報告.md` 待決 6、`PhaseGB-2報告.md` 待決 6、`PhaseGB-2b報告.md`；設計 `docs/design/19-灰燼荒原與賽季主線.md` 19.2.3、`docs/design/05-戰鬥.md` 5.12（D13、D21）。
> 只動 AI 估值與 AI 內容；引擎結算、事件、`state.py`、`api/`、`client/`、設計文件都沒動。**沒有量勝率、沒有跑平衡模擬**（使用者 11-13）。`LOG_FORMAT` 不升（AI 不是結算規則，T19）。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 殼縫算背後（GB-1c 待決 6） | `ai/parts.py::behind_spot(xy, 敵人)`＝`is_behind` 或「貼著巨型頭目 `counts_as_behind`、還沒破、已露出的部位格」。換掉 AI 裡所有背後估值：`position._facing_terms` 的 `backstab`、`silent_behind_extra`、`circle_back_extra`（條件改 `_open_behind_at`：背後格＋開著的 `reach: behind` 部位，或貼著開著的殼縫）、`skill_estimate` 瞬步落點的 `shadowstep_behind`。一格單位不能有綁格部位，結果＝原本的 `is_behind` | `19c0f41e0` |
| 隊友的部位站位（第 7 節第 2 點） | `ai/parts.py::giant_part_spot_extra`，權重 `giant_spot_bonus`（占位 6，表格層級 `parts:` 填入每個模式）：玩家方、非召喚物；近戰貼著某個開著、`reach` 不是 `ranged` 的部位格（`melee_from: any_face` 時貼任一面），或遠程有一格 `reach: ranged` 部位格在普攻射程內（`attack_reach`，含弓的高處射程）而且看得到（`ignore_unit`＝巨人）——每名巨人一次。放在 `_enemy_terms`，移動候選排序吃得到。高台不另加分 | 同上 |
| 隊友挑部位（第 7 節第 1 點） | 不改程式：PB-1b 的 `_with_parts` 用 `part_targets`，GB-1c 的綁格條件自然生效；本段補測三種場面（殼縫、蓄力時的核心、噴口） | 同上（測試在 `a426977fd`） |
| 頭目護面（D13、T18） | `ai/parts.py::guard_face_extra`，權重 `guard_face_bonus`（占位 3，表格層級 `parts:` 填入）：巨型頭目有綁格部位剩血 ≤ `near_break_permille`（500）時，這次動作打到的敵人每名貼著那個部位格子的（`any_face` 時貼任一面）加分。掛在 `scoring._preview_score` 尾巴的 `_target_bias`（打到的人＝預覽最多後果裡受傷的單位、以動作前位置算，× 命中率） | 同上 |
| 餘燼蜥追遠（D21、T17） | 新 `ai/leader.py`：`prefer_far_from_leader`（占位 3）。打誰：`far_target_extra`＝打到的敵人離自己陣營頭目（`boss` 標籤、存活、ID 最小）最近佔格的最遠距離 × 權重（同樣經 `_target_bias`，× 命中率）；往哪走：`far_from_leader_extra`＝從這格打得到的敵人裡離頭目最遠的距離 × 權重（位置價值）。只給殼縫餘燼蜥：新行為模式 `ember_brood`（莽夫權重＋這一項），`content/units/heart_ember_lizard.yaml` 的 `ai_profile: brute` → `ember_brood`。軟偏好、不強制 | 同上 |
| 內容 | `content/ai_profiles.yaml`：`parts:` 加 `guard_face_bonus: 3`、`giant_spot_bonus: 6`（附說明）；新模式 `ember_brood`；`src/trpg/content/environment.py`：`AiWeights` 三個欄位、`PartAiRules` 兩個欄位、`_share_status_values` 的 `keys` | 同上 |
| 測試 | 新 `tests/engine/test_giant_ai_gb3.py`（27 個） | `a426977fd` |
| 文件 | 本報告；上手筆記第二節「AI 怎麼選招」第 6 點、第四節第 53 點、第五節測試表 | 見第 11 節 |

## 2. 逐條驗收

| 驗收 | 結果 | 證據 |
|---|---|---|
| 熔心坑以外逐字不變（7 張地圖 × 種子 1、2 ＋ `rift_gate`、`cloud_summit` × 種子 3～12，共 34 場） | 過：`different=0` | 第 4 節 |
| 熔心坑改前改後勝方、輪數；都能結束；重播一致 | 過：12 場都在 6 輪內結束；`trpg battle replay` 種子 1「重播驗證通過：83 個動作、485 個事件，最終狀態一致」；`test_molten_heart_pit_finishes_and_replays` 比事件與最終狀態 JSON | 第 4 節 |
| CLI 快照先預測再跑 | 預測 0 鍵；`uv run pytest -q -n 8 tests/cli -m slow` → 44 passed，結束碼 0，沒有重產任何鍵 | 第 6 節 |
| `LOG_FORMAT` 不升 | 不升（仍 `/128`）：事件、動作、狀態欄位、結算都沒變；`hash_ruleset` 改前＝改後 | 第 4 節 |
| 行為測試：每條固定場面比分數、確定性、沒有巨人時 `rank` 逐字不變 | 過：`tests/engine/test_giant_ai_gb3.py` 27 passed | 第 3 節 |
| 巨型頭目自己的選招與站位在熔心坑驗（GB-2 待決 6） | 過：`test_the_heart_measures_its_bolt_from_the_nearest_tile`（法師站 (5, 9)：到最近佔格 5 格＝火球射程、到中心 6 格，`rank` 有正分的火球；AI 不結束回合）；站位：頭目速度 0、不動，只有選招 | 第 3 節 |

靜態檢查（commit 前）：`ruff check` All checks passed、`ruff format --check` 通過、`mypy` Success（1612 files）、`lint-imports` 14 kept 0 broken，結束碼都 0。`trpg content check` 結束碼 0（690 個檔案、429 個技能）。

相關測試：`tests/engine/test_parts_ai_pb1.py`、`test_giant_gb1a/1b/parts_gb1c/inhale_gb2b.py`、`tests/content`、`tests/world/test_ashen_waste.py`、`test_enemy_ai_moves_149.py`、`tests/engine/test_skill_ai_scenarios.py` → 3297 passed；`tests/engine/*ai*.py`＋`test_quiet_strikes_bs1.py`、`test_mist_lock_parts_pb1.py`、`test_boss_parts_pb1.py`、`tests/api/tuning/test_parts_pb1n.py`、`test_giant_tuning_gb2.py` → 469 passed，結束碼 0。

## 3. 新測試（`tests/engine/test_giant_ai_gb3.py`）

合成巨人沿用 GB-1c 的競技場（中心 (6, 6)、朝南；殼縫 (5, 6)、(7, 6)；噴口北排；核心第 2 階段露出），噴口拿掉 `armor_bonus` 方便比分數。

- 內容：表格層級的占位值填進每個模式（3、6）；只有 `ember_brood` 有 `prefer_far_from_leader`（3）；只有 `heart_ember_lizard` 用它；`ember_brood` 去掉這一項＝莽夫。
- 殼縫算背後：`behind_spot` 對殼縫兩側為真、前殼與噴口那一排為假、殼縫破了變假；一格單位＝`is_behind`；`backstab`、`circle_back_bonus` 在殼縫旁加滿、前殼為 0、殼縫破了為 0；無聲（匕首＋無聲步）殼縫旁 5、前殼 0。
- 部位站位：近戰殼縫旁加、前殼第 1 階段不加、第 2 階段核心 `any_face` 加；遠程 (6, 12) 打得到噴口加、(12, 12) 射程外不加；近戰斜角不算、遠程貼著殼縫也看噴口；噴口破了不加；敵方不加。
- 挑部位：近戰殼縫旁「殼縫」分數 > 本體；第 2 階段蓄力中、核心快破時打核心；遠程噴口快破時打噴口最高。
- 護面：計數（沒快破 0、殼縫快破時只算殼縫旁的人、破了 0；核心快破時前面的人也算）；頭目普攻分數差＝命中率 × `guard_face_bonus`。
- 追遠：`leader_of`；`far_target_extra` 近 3×1、遠 3×3、兩人取最遠；`rank` 打遠的人分數較高，權重 0 時兩邊同分（差來自 T17）；位置項。
- 沒有巨人的場面（霧鎖真人＋盜賊）每名單位 `rank` 與三個新權重全 0 時逐字相同；我方用 `ember_brood`（沒有頭目）＝莽夫；確定性。
- 熔心坑：火球量到最近佔格；跑完一場並重播一致。

## 4. 不變比對

腳本在 scratchpad（未 commit）：改前用 `git archive cb83fc060 src content` 解開，`PYTHONPATH` 指舊 `src`、`TRPG_CONTENT_DIR` 指舊 `content`；兩邊都跑 `trpg battle --map … --seed … --log-json`（地圖預設陣容、效用 AI、`max_rounds=30`），比整份紀錄（拿掉 `ruleset_hash`、`final_state.ruleset`、`setup.ruleset`）。

- 熔心坑以外 34 場：**`different=0`**；`ruleset_hash` 46 場改前＝改後。
- 三個雜湊：`hash_ruleset` 改前＝改後＝`3db78bc64322cc808f12a25fa3f830d32680b6fb2143dcd35d84a812d060059f`（AI 表與單位範本的 `ai_profile` 不在規則包裡），所以一輪存檔的 `ruleset_hash` 也不變；世界日誌 `content_digest` **會變**（`2343c880…0b0d` → `ad8b22b9…e3a6`），因為 `content/ai_profiles.yaml` 與 `heart_ember_lizard.yaml` 改了——預期（內容改了 digest 就變），沒有測試寫死它。
- 剝掉的預設鍵：無（狀態、事件沒有新欄位）。
- 熔心坑 12 場（只列不評；勝方／輪數／事件數／動作數）：

| 種子 | 改前（GB-2b） | 改後（GB-3） |
|---|---|---|
| 1 | 敵／4／454／74 | 敵／4／485／83 |
| 2 | 敵／5／489／89 | 敵／4／439／84 |
| 3 | 敵／4／451／85 | 敵／5／510／88 |
| 4 | 我／6／521／100 | 敵／5／440／74 |
| 5 | 敵／5／402／82 | 敵／5／404／70 |
| 6 | 敵／5／537／97 | 敵／5／532／83 |
| 7 | 敵／7／573／115 | 敵／4／407／75 |
| 8 | 敵／5／372／65 | 敵／5／394／56 |
| 9 | 敵／6／363／69 | 敵／5／448／84 |
| 10 | 敵／4／422／78 | 敵／6／559／101 |
| 11 | 敵／6／568／90 | 敵／5／484／71 |
| 12 | 敵／6／500／96 | 敵／6／560／104 |

12 場全部變（預期：隊友開始走去殼縫、打部位，蜥蜴改追站得遠的人）。行為觀察（12 場加總，只看行為不看勝率）：選部位的攻擊 殼縫 102 → 129、噴口 9 → 16、核心 27 → 22；破掉的殼縫 6 → 12 次、核心 4 → 2 次；走到殼縫攻擊位 (3, 3)、(7, 3) 10 → 13 次、走上高台 13 → 10 次。12 場都在 30 輪內結束（最多 6 輪）。

## 5. 改了哪些呼叫點

| 檔案 | 處數 | 內容 |
|---|---|---|
| `engine/ai/parts.py` | 新函式 6（`behind_spot`、`giant_part_spot_extra`、`guard_face_extra` 與小工具）＋改 2（`circle_back_extra`、`silent_behind_extra`） | |
| `engine/ai/leader.py` | 新檔 | T17 |
| `engine/ai/utility/position.py` | 3 | `backstab` 改 `behind_spot`；`_enemy_terms` 加部位站位、追遠兩項 |
| `engine/ai/utility/scoring.py` | 1＋新 `_target_bias` | 只在 `prefer_far_from_leader` 非 0，或行動者是巨人且 `guard_face_bonus` 非 0 時算（其他動作分數不加 0 以外的值） |
| `engine/ai/utility/skill_estimate.py` | 1 | 瞬步落點的 `shadowstep_behind` 改 `behind_spot` |
| `content/environment.py` | 3 | 欄位與表格層級合併 |
| `content/ai_profiles.yaml`、`content/units/heart_ember_lizard.yaml` | 2 | 占位值、新模式；**後者在派工範圍表外**（「只給 `heart_ember_lizard`」最小的做法，見第 8 節） |

刻意不改：`guard_back_extra`（只看 `reach: behind`；巨人背面是岩漿、不轉身，`back_exposed` 對不動的巨人沒有作用）；`policy.py`（部位變體照舊，不必改）；`api/`、`client/`（GB-4a）；數值工坊白名單（`content/tuning_fields.yaml` 不在本段範圍，見待決 3）。

## 6. 快照與既有測試變動

- CLI 快照：預測 0 鍵（戰鬥鍵都是一般地圖、`ruleset_hash` 不變、技能卡沒改）；實際 `tests/cli -m slow` 44 passed，0 鍵變動。
- 既有測試：沒有任何既有測試要改（`test_the_value_table_has_placeholder_values` 要求 YAML 列齊 `PartAiRules` 每個欄位，新鍵已寫進 YAML）。沒有換種子。

## 7. 新增 `# noqa`

無。

## 8. 規格沒寫到、採保守做法的地方

1. **「只給 `heart_ember_lizard`」的做法**：新行為模式 `ember_brood`（莽夫＋`prefer_far_from_leader: 3`），改那個範本的 `ai_profile`。程式不寫範本 ID；`ember_brood` 不在傭兵可選打法（`mercenaries.yaml` `ai_choices` 是明列的）。動到派工範圍表外的 `content/units/heart_ember_lizard.yaml` 一行。
2. **「頭目」怎麼找**：同陣營、帶 `boss` 標籤、存活、ID 最小的一名；沒有就 0。距離量到它的最近佔格（`dist_to`）。
3. **追遠的兩半**：T17 只寫「目標離頭目越遠分數越高」。只加在打誰上不會讓蜥蜴走向遠的人，所以位置價值也加一項（從這格打得到的敵人裡最遠的距離 × 權重）；兩半同一個權重。
4. **護面「和那個部位的格子相鄰」**：照 T18 字面看部位格四方向相鄰；核心是 `any_face`（中心格四周都是自己的佔格），照「打站在那一面的人」解成貼任一面都算。噴口旁能站的只有 (3, 2)、(7, 2) 這類角落外側，遠程從遠處打噴口不會觸發護面——照字面。
5. **打到的人**：預覽最多後果裡受到傷害的單位（以動作前位置），護面與追遠都乘命中率（沒有命中判定的招 × 1）。延遲段（熔岩濺落）施放當下沒有傷害，所以不吃這兩項——它本來就由引擎選最遠的人。
6. **部位站位的範圍**：近戰只看 `reach` 不是 `ranged` 的部位；遠程只看 `reach: ranged` 的部位（規格寫「遠程站在看得到、打得到噴口的格子」）。遠程能打殼縫、核心不另加站位分。每名巨人最多一次，和繞背可疊加（殼縫旁 = 背刺 4 ＋繞背 6 ＋部位站位 6）。
7. **`giant_spot_bonus` 占位 6**：規格只寫「占位」，照繞背 `circle_back_bonus` 的 6。
8. **背後估值的範圍**：除了待決 6 點名的無聲留背與繞背，`backstab` 位置項與瞬步落點的 `shadowstep_behind` 也一起改（都是「站這格算不算背後」的同一個判斷）。技能層級的「目標背後」條件仍不吃殼縫（GB-1c 待決 4，PM 已同意之後再補）。

## 9. 影響

- 舊戰鬥紀錄：熔心坑的舊紀錄用新 AI 重跑會走不同的路，但紀錄重播只照動作列表，不受 AI 影響，`LOG_FORMAT` 不變、照常能重播。其他地圖逐字不變。
- 戰鬥中存檔：狀態欄位沒變，讀得回。世界日誌的 `content_digest` 變了（內容改了），和以往改內容一樣。

## 10. 平衡疑慮（不量，只記）

1. **蜥蜴追遠＋熔岩濺落打最遠的人**：遠程與高台同時被兩邊針對（規格第 10 節第 7 點的延續）；這次改後走上高台的次數反而少了，可能是隊友改去殼縫。
2. **殼縫更早破**：隊友更常打殼縫，熔殼（−40％）更早沒了（規格第 10 節第 5 點）。
3. **核心 any_face 的站位分讓近戰第 2 階段整圈都有加分**，殼縫旁另外疊背刺與繞背，近戰會更集中在兩側；兩側靠近第 3 階段火地與蜥蜴出生格 (2, 3)、(8, 3)。
4. 熔心坑改前改後勝方大多是敵方（GB-2b 起就如此）；本段不評。

## 11. 待 PM 決定

1. **新模式 `ember_brood`** 與改 `heart_ember_lizard.yaml` 的 `ai_profile`（範圍表外一行）：可以接受嗎？名稱「殼縫蟲群」與玩家看得到的說明字（召喚物說明會顯示行為模式，敵人不會）要不要改。
2. **護面對核心的解讀**（第 8 節第 4 點）：核心 `any_face` → 貼任一面都算。
3. **工坊白名單**：`parts.guard_face_bonus`、`parts.giant_spot_bonus` 與 `ember_brood` 的 `prefer_far_from_leader` 還沒進 `content/tuning_fields.yaml`（不在本段範圍；T17 寫「NW-3 開放後可調」），要不要併進下一個動工坊白名單的段。
4. **`giant_spot_bonus` 占位 6**（照繞背）與「遠程只看噴口」的範圍（第 8 節第 6、7 點）。
5. **追遠的位置項**（第 8 節第 3 點）：規格只寫打誰，本段多加了「往哪走」，同一個權重；要不要拆成兩個權重。
6. `content_digest` 會變（第 4 節）：照以往改內容的慣例，不另處理。

## 12. commit

| commit | 內容 |
|---|---|
| `19c0f41e0` | feat(ai)：殼縫算背後、部位站位、護面、追遠；內容占位值與 `ember_brood` |
| `a426977fd` | test(ai)：`tests/engine/test_giant_ai_gb3.py` |
| （本 commit） | docs：本報告、上手筆記 |

## 開發 PM 裁定（2026-11-14）

- 接受。熔心坑以外 34／0、`hash_ruleset` 不變、CLI 快照 0 鍵。
- 待決 1：接受新增行為模式 `ember_brood` 與 `heart_ember_lizard.yaml` 一行（規格範圍外但必要）；名稱說明字照現況。
- 待決 2、4、5、6：照目前做法（核心貼任一面算；占位 6；「打誰」「往哪走」共用一個權重，工坊開放後使用者覺得要分再拆）。
- 待決 3：三個新權重加進工坊白名單，併進下一個動 `tuning_fields.yaml` 的段（交接待排 (e3s)）。
- 熔心坑改後 12 場都是敵方勝，連同第 10 節平衡疑慮轉玩法 PM 記平衡待查（不量）。
