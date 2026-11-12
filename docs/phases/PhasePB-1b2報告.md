# Phase PB-1b2 完成報告｜隊友繞背站位分＋部位測試改讀內容

> 依據：開發 PM 派工（A：玩法 PM 定的「繞背」站位分，只改 AI、不改規則、設計文件不動；B：PB-1n 待決 4，開發 PM 定要做）。
> 基準：本機 main `5a85bf43`（`git merge --ff-only main`；`d475815d`、`04610c8f` 都是祖先）。未 push。

## 1. 做了什麼

| commit | 內容 |
|---|---|
| `368221fa` | B：`tests/engine/test_mist_lock_parts_pb1.py` 的部位血量‰與長劍降傷‰改讀內容原始 YAML |
| `7ad379d4` | A：繞背站位分（`ai/parts.py::circle_back_extra`，`position._facing_terms` 呼叫）；`AiWeights.circle_back_bonus`、`PartAiRules.circle_back_bonus`；`content/ai_profiles.yaml` 的 `parts:` 加 `circle_back_bonus: 6`（占位）；`content/tuning_fields.yaml` 的 `kind: ai` 加一列（中文說明，建議 0～20）；工坊 AI 表提示「8 個值」→「9 個值」；B：`test_parts_ai_pb1.py` 的 8 個占位值改讀內容；新測試 6 項 |
| `23abe8fe` | 上手筆記：`上手-引擎戰鬥結算.md` 第二節第 5 點補繞背、第四節加第 23、24 點；`上手-內容資料與模擬.md` 的收編清單改寫 |
| （本報告） | `docs/phases/PhasePB-1b2報告.md` |

**繞背規則（落地）**：位置價值加 `circle_back_bonus` × 符合條件的頭目數。條件全部成立才加：

- 行動者是玩家方（`Team.ALLY`）、不是召喚物（同 `picks_parts`／R9）、武器近戰（`weapon.is_melee`，同既有背刺項）；
- 站在頭目的背後格（`is_behind`，相鄰）；
- 頭目有 `reach: behind`、目前階段在 `exposed_in`（沒寫＝都露出）、還沒破的部位。

它是位置價值的一項，所以移動候選的排序（`virtual_move_score`）與完整預覽的分數都會用到；藉機攻擊（有風險的移動跑完整預覽）、危險表面與敵方區域（`hazard`）、強招預告等原本的站位扣分一項都沒動。值經 `_share_status_values` 從表格層級 `parts:` 填進每個行為模式的 `weights`（同 `guard_back_bonus`）。沒有部位的單位與戰鬥一律 0（`w.circle_back_bonus` 為 0 時連函式都不呼叫）。

## 2. 新測試（`tests/engine/test_parts_ai_pb1.py`）

| 測試 | 驗什麼 |
|---|---|
| `test_standing_behind_the_boss_with_the_dantian_exposed_adds_the_bonus[mist_lock/return_to_one]` | 站在背後格、氣海露出：位置價值正好多 `circle_back_bonus`（其他站位項不變） |
| `test_no_circle_back_bonus_without_an_open_behind_part` | 劍陣（氣海沒露出）、氣海已破、站在正面：0 |
| `test_only_player_side_melee_non_summons_circle_back` | 弓手（遠程）、召喚物、敵方：0 |
| `test_a_big_enough_bonus_walks_the_hero_behind_the_boss` | 斜前方的英雄：加分 0 時不移動，加分夠大時走到背後格；到了背後格部位變體有氣海 |
| `test_circle_back_leaves_scenes_without_parts_unchanged` | 沒有部位的頭目（盜賊）站在背後：加分 50 與 0 的 `rank` 動作與分數完全相同 |

## 3. 不變比對

腳本在 scratchpad（未 commit）：地圖預設陣容、效用 AI、`max_rounds=30`；改前（`5a85bf43`）與改後各跑一次，每場比對整份 `BattleLog` JSON（事件、步驟、最終狀態含 `rng_state`），沒有剝掉任何鍵。

- 8 張地圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12：`battles=46 events=20491 different=1`。
- **沒有部位的 34 場 `different=0`**；`cloud_summit` 12 場中 11 場也逐字相同。
- 唯一變的是 **`cloud_summit` 種子 2**：第 95 個步驟（第 5 輪，鎖霧階段，拂塵已破），劍士（HP 8）原本往 (1,3) 退，改成繞到真人背後格 (2,4)（真人面北）。事件 469 → 477，步驟數 96、輪數 5、勝方（敵方）、各單位最終 HP 都相同；部位動作同為拂塵 3 次、破 1 次。
- `LOG_FORMAT` 不升（只改 AI 的選擇）。`content/ai_profiles.yaml` 改了，所以一輪存檔的 `ruleset_hash` 與世界日誌的 `content_digest` 會變（同 PB-1b，重開伺服器後進行中的一輪從頭開始）；`hash_ruleset` 不含 AI 表。
- CLI 快照：`tests/cli/test_output_snapshots.py -m slow` 24 passed，**0 個鍵變動、沒有重產**。
- 固定種子測試：沒有任何一個需要換種子（`test_boss_battle.py`、`test_season_boss.py`、`test_enemy_ai_moves_149.py`、`test_shard_lord_first_phase.py` 照舊通過）。

## 4. 補量（`scripts/pb1_parts_report.py`，霧鎖真人 × 8 build × 種子 0～12，部位關／開，`--jobs 4`，經開發 PM 同意）

「部位關」組沒有部位，繞背不作用，所以和 PB-1d 的關組數字完全一樣（勝率 99/104、10.0 輪），可直接當對照。

| 項目 | PB-1d 部位開（沒繞背） | PB-1b2 部位開（繞背 6） |
|---|---|---|
| 勝率 | 99/104（95%） | 99/104（95%） |
| 平均輪數 | 9.6 | 9.6 |
| 歸一回血總量（場均） | 416（4.0） | 414（4.0） |
| **氣海被選** | 6 次（主角 3、merc_tiebi 3） | **9 次**（主角 3、merc_tiebi 6） |
| **氣海被破** | 0/104 | **0/104** |
| 拂塵破 | 102/104 | 102/104 |
| 長劍破 | 68/104（致命一擊 25） | 66/104（致命一擊 24） |
| 氣海可選原因：不相鄰／相鄰但不在背後／可選 | 228／125／4 | 226／132／4 |

分 build 勝率（開組）：striker 13/13、fire 13/13、storm 13/13、ranged 13/13、tank 13/13、guardian 13/13、healer 12/13、**trapper 9/13（69%，和沒繞背、部位關都一樣）**；與 PB-1d 的開組逐項相同。

**觀察（不建議數值）**：占位 6 只讓氣海被選從 6 次到 9 次、仍 0 破；第 2、3 階段我方對頭目的攻擊有六成是遠程或不相鄰，相鄰的也多半直接攻擊而不先繞背（一次攻擊的分數量級約 50～100，站位分 6 不夠翻轉）。要不要加大由使用者在數值工坊調（「AI 估值表 → 隊友繞背的加分」）。

## 5. 測試舊→新（B，斷言的邏輯與強度不變）

| 檔案：測試 | 舊 | 新 |
|---|---|---|
| `test_mist_lock_parts_pb1.py::test_the_three_parts_follow_the_design_table` | 三個部位的 `hp_permille` 寫死 `200` | 讀內容原始 YAML 的各部位 `hp_permille`（`raw_hp_permille`）；ID、名稱、方向、露出階段、效果種類照舊寫死 |
| `test_mist_lock_parts_pb1.py::test_each_part_has_24_hp_at_120_hp` → **改名** `test_each_part_hp_is_its_permille_of_120_hp` | `part_hp == {"whisk": 24, "dantian": 24, "sword": 24}` | `part_hp == {部位: max(1, 120 × 原始 hp_permille // 1000)}`（現值算出來仍是 24） |
| `test_mist_lock_parts_pb1.py::test_the_content_hp_gives_the_same_ratio` | `set(part_hp.values()) == {hp * 200 // 1000}` | 逐部位字典比對 `max(1, hp × 原始 hp_permille // 1000)`（比原本的集合比對更嚴） |
| `test_mist_lock_parts_pb1.py::test_breaking_the_sword_lowers_damage_and_interrupts_the_cleave` | `("damage_dealt", 750)`、`damage_dealt_permille == 750` | 讀原始 YAML 長劍 `on_break[0].amount`（另斷言它是 `stat_down damage_dealt`、0 < 值 < 1000）後比對同兩處 |
| `test_parts_ai_pb1.py::test_the_value_table_has_placeholder_values` | `PartAiRules(8, 10, 4, 6, 8, 6, 3, 500)`；brute 的 `(3, 500)` | 原始 YAML `parts:` 的鍵集合 == `PartAiRules` 的欄位、`library().ai_profiles.parts == PartAiRules(**原始值)`；brute 的 `(guard_back_bonus, near_break_permille, circle_back_bonus)` == 原始值 |
| `tests/api/tuning/test_parts_pb1n.py` | `AI_PATHS` 8 個；`near = ai.fields[-1]` | 加 `parts.circle_back_bonus`；`near` 改用路徑找（新欄位排在最後，原本的「最後一個」不再是快破門檻；斷言不變） |

## 6. 結束碼（最後程式 commit `7ad379d4`）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1516 檔） |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 0 |
| pytest `-n 6`：`tests/engine` 的 AI 與部位相關（`test_parts_ai_pb1`、`test_ai_utility`、`test_ai_weights`、`test_skill_ai`、`test_support_ai`、`test_status_ai`、`test_displace_ai`、`test_boss_parts_pb1`、`test_mist_lock_parts_pb1`、`test_determinism`、`test_boss_phases`、`test_state_clone`、`test_preview`）＋ `tests/world` 頭目 AI 四檔 ＋ `tests/test_architecture.py` ＋ `tests/api/tuning` ＋ `tests/content` | 0：3421 passed |
| `uv run pytest -n 4 tests/cli/test_output_snapshots.py -m slow` | 0：24 passed |
| `trpg battle --map cloud_summit --seed 2 --log-json` ＋ `trpg battle replay` | 0／0：「重播驗證通過：96 個動作、477 個事件，最終狀態一致」 |

沒有跑完整 `scripts/check.py`；前端只有工坊的文字由後端產生，沒改前端程式。

## 7. 待 PM 決定

1. 繞背的「近戰」用 `weapon.is_melee`（同背刺位置分）；近戰的單體技能（武器是遠程時）不算——`part_targets` 判氣海時看的是這次攻擊的 `melee`，兩者在少數「遠程武器＋近戰技」的單位會不一致。
2. 只給 `Team.ALLY`、非召喚物（同 `picks_parts`）；第三方陣營不繞背。
3. 每名符合條件的頭目各加一次（同時站在兩名頭目背後會加兩次；目前沒有雙頭目戰）。
4. 占位 6 的效果很小（氣海被選 6→9、0 破，trapper 9/13 不變），量級由使用者在工坊調；本段不建議數值。
5. 既有測試 `test_scenes_without_parts_rank_exactly_as_before` 的「價值表全 0」用 `table.model_copy(update={"parts": ...})`，但填進 `weights` 的三個值（護背、快破、繞背）不會因此歸零（見上手第四節第 23 點）；那個測試的場面沒有部位，結論仍成立，未改。
