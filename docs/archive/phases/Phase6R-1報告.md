# Phase 6R-1 報告：#138 獸耳族（原狐族）＋ B 種族勝率矩陣 ＋ C 戰場捷徑檢查

> 實作者：worktree 分支 `worktree-agent-a34a1a05b43bf500e`（從 `3194c156` 開始）。沒有 push、沒有合併。
> 依據：`docs/玩法決定紀錄.md` #138；`docs/design/07-角色成長.md` 7.7（種族表、實作細節第 6 點）；09 9.6.4、9.6.11；18 開頭、事件 18、霜音；玩法 PM 筆記「新種族獸族人」「種族讓任務過易盤點」（B、C 的定義）。

## 1. 每一項做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 獸躍、輕身 | 種族 ID 照舊 `fox`，名稱「獸耳族」。種族技 `race_beast_leap`：效果類型 `leap`（`range: 3`、`max_rise: 2`），1 AP、每場 1 次。落點＝曼哈頓 3 格內、可站、沒有單位、不是致命地形、最多比起點高 2 層（往下不限）。**不能越過牆**寫成 `leap_path_clear`：起點到落點要有一條最短路徑（每步曼哈頓距離少 1）中間格都不是「牆壁地形／同時擋行動與視線的物件（石柱、土牆、冰牆、枯樹）／比起點高出 2 層以上的地形」；單位、矮牆、木箱、倒木、油桶、深淵與岩漿缺口可以越過。不看視線。落地走 `MoveUnitEffect(mode="leap")`：不付移動點數、不觸發藉機攻擊、觸發落點陷阱與表面。被動 `beast_light_body`：規則 `fall_immunity`，`arrive`（自己走下、被推下、跳下）與 `heights`（腳下被降低）都不發 `unit_fell`，所以不受傷；致命地形照舊。攀跳的「跳下去會摔傷」對輕身不適用 | `content/races.yaml`、`src/trpg/content/races.py`、`src/trpg/engine/race/skills.py`、`engine/rules/race.py`、`effects/handlers.py`、`heights.py`、`basics.py` |
| 2 | 舊狐族退役 | `race_foxfire_decoy`、`fox_keen_senses` 從種族表拿掉（yaml 留註解）；`summon_foxfire_decoy` 範本、`decoy` 效果、`detect_hidden_nearby` 規則的引擎程式都保留。舊測試改用測試專用的舊狐族定義（`tests/engine/race_helpers.py` 的 `legacy_fox`） | 同上、`tests/engine/race_helpers.py` |
| 3 | AI | `engine/ai/race.py` 加 `leap` 估值：往上跳、落地後打得到敵人才用；分數＝高度差 ×10 ＋ 打得到的敵人數 ＋ 越近越好。輕身：`is_risky_move` 不把往下當風險；`terrain._pit_victims` 不算輕身的敵人；新表格層級 `race_ai.light_body_height: 4`（輕身單位每層高度位置加分＝主動找高處） | `engine/ai/race.py`、`ai/utility.py`、`ai/terrain.py`、`content/ai_profiles.yaml`、`content/environment.py` |
| 4 | 判定加值 | `situation_rules.yaml`：`fox: climb`（交涉不再有種族） | `content/world/situation_rules.yaml` |
| 5 | `look.beast_ears` | `RaceLook.beast_ears: fox/cat/wolf/rabbit`（可省略），`races.yaml` 的 fox 填 `fox`；前端沒畫（`raceLooks.json` 照匯出腳本重產） | `content/races.py`、`client/src/render/fixtures/raceLooks.json` |
| 6 | 雲嶺事件 | 事件 18 改「獸耳族旅人（狐系血脈）」、賭注「獸耳族的好感度」、解法說明「獸耳族主角有專屬對話選項，不加數值」；情境 `fox_persuade` 文字；social 註解；霜音 hooks。**霜音專屬對話**：`TalkEntry` 加 `races`（只對這些種族的主角說），霜音多一條 `frost_chime_kin`（中立級、只給獸耳族）。攀爬跳躍補進 `deserter_hide`（雲嶺）、`sandstorm_track`、`brood_sneak`、`noon_altar_endure`（荒原，必要時補 `dex`） | `content/world/events|situations|social|npcs/…`、`content/world_quests.py`、`world/affinity.py` |
| 7 | 地圖崖台 | 雲嶺三張實地地圖各加 1 處 2 層崖台（見第 5 節），都附走得上去的坡，死角、不通往出口 | `content/world/fields/cloud_ridge/*.yaml` |
| 8 | 免費換種族 | 新世界動作 `change_race`（`POST /api/world/characters/{id}/actions`，`{"kind":"change_race","race":"elf"}`）：在主城、沒有待處理遭遇、這一季還沒用過；開放的季寫在 `world/season.yaml` 的 `free_race_change_seasons: [s1]`。角色欄位 `free_race_change_used`（數值類，季末清掉；`season_policy` 已分類）。世界畫面角色欄多 `race`、`free_race_change`、`free_race_change_zh`。前端：世界側欄角色狀態下面一行（下拉選種族＋「換種族」，有確認框；不在主城時灰掉並寫原因），沒有新畫面 | `world/race_change.py`、`world/actions.py`、`world/state.py`、`world/step.py`、`api/world_presenter.py`、`api/world_schemas.py`、`client/src/world/RaceChange.tsx` |
| 9 | 版號 | 見第 2 節 | `world/save.py`、`world/state.py` |
| 10 | 快照 | 見第 3 節 | — |
| 11 | C 捷徑檢查 | `trpg.sim.leap_check`＋`scripts/leap_shortcuts.py`＋`tests/sim/test_leap_check.py`；結果見第 4 節 | — |
| 12 | B 勝率矩陣 | `scripts/race_matrix.py`；結果見第 6 節 | — |
| 13 | 內容檢查 | `trpg content check` 通過；情境覆蓋表（6Q-A）0 列標出：獸耳族雲嶺 3 個、荒原 3 個攀爬跳躍模板 | — |

另外修了一個 B 模擬抓到的舊問題：龍息震退的 AI 估值在敵人站地圖邊（推開的下一格在地圖外）時會越界（`IndexError`，或在右邊緣讀到下一列的格子）。`engine/ai/race.py` 加了地圖範圍檢查，`test_dragon_breath_ai_handles_targets_on_the_map_edge` 是回歸測試。

## 2. 版號

| 版號 | 變動 | 理由 |
|---|---|---|
| `WORLD_RULES_VERSION` | 19 → **20** | 戰鬥規則（獸躍、輕身）會讓同一份世界日誌打出不同結果；聊天內容可以依種族過濾；新動作 `change_race`。docstring 已補 |
| `CHAR_FORMAT` | `trpg-char/9` → **`trpg-char/10`** | 多了選填欄位 `free_race_change_used`；`/1`～`/9` 照讀（`/9` 的裝備來歷不重算成綁定）。測試：`tests/world/test_race_change.py::test_old_character_files_load_as_not_used` |
| `WLOG_FORMAT`、`WORLD_FORMAT` | 不變 | 日誌結構、世界結構沒變 |
| `LOG_FORMAT`（戰鬥紀錄） | 不變 | 誘餌程式保留；`UnitFell` 欄位沒改；新效果類型與被動規則是規則包內容（規則雜湊自動變） |

## 3. 快照與結束碼

| 指令 | 結果 |
|---|---|
| `uv run python -m tests.skillgen.test_refactor_3wr2` | 0；只有換行符變動（CRLF），內容沒變，已還原 |
| `UPDATE_CLI_SNAPSHOTS=1 uv run pytest -m "slow or not slow" tests/cli/test_output_snapshots.py` | 0；25 passed，**快照檔沒有變**（快照的場次沒有狐族角色，也沒有用到被修的龍息 AI 邊界情況） |
| `pytest -n 8 tests/cli`（含 `test_run_cli`） | 136 passed，不用重篩種子 |
| `ruff check src tests scripts`／`ruff format --check`／`mypy src`／`lint-imports` | 0／0／Success（542 檔）／13 kept 0 broken |
| `trpg content check` | 0 |
| `trpg battle --map swamp --seed 7 --log-json X && trpg battle replay X` | 0／重播通過（88 動作）；另跑 `cliff_outpost --ally-race fox,fox,fox` 重播通過，獸躍有用到 |
| 相關 pytest（engine、narrative、content、world、api、server、architecture） | 最後一次 world/api/server 全目錄：除了下面已修正的檔案全過；修正後相關檔案重跑全過 |
| client：全部 `vitest`、`tsc --noEmit`、`corepack pnpm -C client build` | 262 檔 2999 passed／0／0（只有原本的 chunk 大小警告） |

## 4. C 戰場捷徑檢查

**做法**（`src/trpg/sim/leap_check.py`，只呼叫引擎的規則函式）：每張地圖建一個只有獸耳族探針的戰鬥狀態，跑三層最短路徑（成本＝移動點數）：走路（`step_cost`）、走路＋攀跳（`vault_plan`，所有種族都能用）、再加一次獸躍（`leap_problem`，成本＝曼哈頓距離；平地上不會變短）。量三件事：

1. 起點 → 目標（戰鬥地圖：我方起始區 → 撤離格、守點、敵方起始區＝Boss；實地地圖：入口、出口、門 → 出口、門、駐守、事件點、NPC、營火）比「走路＋攀跳」短幾格，超過 2 格標出。
2. 只有獸躍到得了的格（跳進封閉區）。
3. 省最多的單次獸躍（參考）。

**範圍**：`content/maps` 全部 17 張戰鬥地圖（含 Boss 地圖 `cloud_summit`、`molten_heart_pit`、`rift_gate`、`bandit_lair`，以及每張的撤離／守點輪替）＋ 雲嶺與荒原 40 張實地地圖（含城鎮與室內）；主城不查。約 10 秒。

**結果**：

- **牆、石柱、土牆、冰牆、枯樹從來沒被跳過**；沒有任何目標是「只有獸躍到得了」。合成地圖測試：牆圍、石柱圍的封閉區跳不進去；矮牆圍的跳得進去（照 7.7）。
- 撤離、守點、Boss 的路徑：所有戰鬥地圖最多短 2 格（`bridge_chasm`、`cliff_outpost`、`lava_crossing`）。
- 新加的三處崖台：最多短 1 格（攀跳本來就上得去）。
- **被標出的兩項（待 PM 決定，第 8 節 1、2）**：
  - `dark_forest`（戰鬥地圖）：(4, 4)、(5, 5) 兩格被牆、倒木、枯樹圍住，只有越過倒木才進得去。照 7.7 字面（可以越過物件）是合法的，但跳進去之後近戰敵人碰不到（倒木打得破）。
  - `lava_cave`（荒原實地地圖）：跳過 2 格寬的岩漿溝，從出口到熔岩洞主（`cave_lord`）短 8 格、到事件點 `molten_lord_pool` 短 6 格。7.7 沒寫深淵、岩漿能不能越過；目前照字面「只有牆與石柱擋」。
- 其他較大的單次捷徑（不影響目標路徑，給美術與玩法參考）：`ruined_fortress` 越過封住缺口的矮牆（省 30 格）、`gang_convoy_road` 省 14、`lava_crossing` 省 13、`cliff_outpost` 省 10。

完整表：`uv run python scripts/leap_shortcuts.py`（有標出時結束碼 1）。`tests/sim/test_leap_check.py`（slow）把上面兩項列為已知，新出現的就失敗。

## 5. 崖台位置（給美術 PM）

都用現有的高度畫法（格子標「▲3」「▲2」）。崖台是死角，不通往出口、門、暗門；每處都有走得上去的坡。

| 地圖 | 崖台格（高） | 比旁邊高 | 坡（高） | 截圖 |
|---|---|---|---|---|
| 北坡獵場 `north_slope` | (12, 9)、(12, 10)（3） | 西、北的草甸高 1 → 2 層 | (11, 10)（2） | `docs/art/6r1_ledge_north_slope_1600(_zoom).jpg` |
| 斷崖幫寨 `cliff_gang_fort` | (8, 5)、(9, 5)（3）：寨中西北角的貨台 | 寨中高 1 → 2 層 | (10, 5)（2） | `docs/art/6r1_ledge_gang_fort_1600(_zoom).jpg` |
| 鶴歸崖 `crane_cliff` | (12, 10)、(12, 11)（2）：下層東側 | 下層高 0 → 2 層 | (13, 11)（1） | `docs/art/6r1_ledge_crane_cliff_1600(_zoom).jpg` |

獸躍實機截圖（斷崖幫寨就地開打的戰場，弓手獸耳族主角）：

- `docs/art/6r1_leap_targets_1600(_zoom).jpg`：按「獸躍」後的紅框落點（16 格），含 ▲3 貨台；寨牆另一側沒有落點。
- `docs/art/6r1_leap_landed_1600(_zoom).jpg`：跳上貨台後，「高地 ▲3」、獸躍剩 0／1、紀錄「跳躍到 (5, 3)」。

截圖方式：正式遊戲（`trpg serve` 8123，存檔在 `scratchpad/r6saves`，用 `scratchpad/seed_6r1.py` 建角色後把位置改到崖台旁），無頭 Chrome `--headless=new --mute-audio`、網址 `?mute=1`、CDP 把視窗設成 1600×900；`_zoom` 是同一幀裁出放大 2 倍（800×450）。伺服器已用自己的工作 ID 結束。

## 6. B 種族勝率矩陣

**做法**（`scripts/race_matrix.py`，只量不調）：走大世界真正的開戰路徑（`prepare_battle`），雲嶺＋荒原每張實地地圖上的每一隊駐守＝一個遭遇組合（51 個，含新手三場固定戰、精英巢穴、兩區 Boss 地圖）。主角從入口照走路規則走到那一隊 3 格內就地切 12×12（48 個切成功，3 個村落守點戰用模板地圖），主角照建議等級成長、只換種族，隊友＝預設傭兵。build：`build_ranged`、`build_charger`。先每組 20 場（10 種子 × 2 build）＝10,200 場，例外 0；標出的 11 組補到 60 場。總時間約 1 小時（和快照、測試同時跑）。賽季 Boss（裂界門）沒包含（另一條開戰路徑）。

**區域 × 種族（每格 1,000 場左右）**

| 區域 | 人類 | 精靈 | 獸耳族 | 龍裔 | 矮人 | 晶能義體人 | 獸人 | 角魔 | 鱗族 | 海民 | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 雲嶺 | 92% | 92% | 92% | 92% | 92% | 91% | 92% | 92% | 92% | 92% | 92% |
| 灰燼荒原 | 72% | 72% | 71% | 70% | 70% | 69% | 72% | 69% | 68% | 70% | 70% |
| 全部 | 82% | 82% | 81% | 81% | 80% | 80% | 82% | 80% | 80% | 81% | 81% |
| 主角倒下率 | 23% | 23% | 23% | 25% | 25% | 25% | 22% | 26% | 25% | 24% | — |

**區域層級沒有任何一族超過平均 +10。** 獸耳族和其他族一樣（雲嶺 92%、荒原 71%）。

**遭遇組合層級（20 場篩出、補到 60 場）**

| 遭遇組合 | 種族 | 20 場 | 60 場 | 組合 10 族平均（20 場） | 判定 |
|---|---|---:|---:|---:|---|
| 荒原 枯木林 `colossus_smoke` | 龍裔 | 90% | 82% | 78% | 回落，正常 |
| 荒原 熔岩洞 `cave_beetles` | 人類、精靈、獸耳族、獸人 | 75～80% | 都是 60% | 64% | 回落；四族結果逐場相同（種族技沒用上） |
| 荒原 熔岩洞 `cave_lord` | 晶能義體人 | 60% | **60%** | 46% | **仍高 14**（待 PM，第 8 節 4） |
| 荒原 黑曜谷 `obsidian_mix` | 海民 | 60% | 55% | 49% | 回落 |
| 荒原 焦油坑 `tar_tortoises` | 龍裔 | 70% | 58% | 56% | 回落 |
| 雲嶺 斷崖幫寨 `cliff_gang_hounds` | 龍裔 | 100% | 97% | 88% | 高 9，在誤差內 |
| 雲嶺 藥師谷丹爐 `furnace_steward` | 晶能義體人 | 85% | 72% | 72% | 回落 |
| 雲嶺 藥師谷丹爐 `furnace_tide` | 海民 | 100% | **92%** | 80% | **仍高 12**（待 PM，第 8 節 4） |

注意：組合平均只有 20 場（約 ±10），上面兩項要確認的話，建議那兩個組合 10 族都補到 60 場（約 1,200 場、5 分鐘）。原則 4 的判定是「區域（含 Boss）」層級，這一層沒有超標。數值建議交給 PM，我沒有調。

## 7. 複雜度 noqa

沒有新增 `C901`／`PLR0911／0912／0915` 的 noqa（`leap_problem`、`_candidates`、`race_change_problem`、`leap_check._edges` 都拆成小函式）。

## 8. 待 PM 決定

1. **獸躍能不能越過致命地形缺口（深淵、岩漿）**：7.7 只寫「可以越過單位、矮牆、物件，不能越過牆與石柱」。照字面現在可以跳過 2 格寬的岩漿／深淵（攀跳只能跳 1 格）。C 檢查唯一超過 2 格的目標路徑就是這個：`lava_cave` 跳過岩漿溝到熔岩洞主短 8 格。這是規則類，請回使用者或玩法 PM；如果要擋，改 `leap_blocks_at` 一行並補測試即可。
2. **`dark_forest` 的兩個封閉小格**（牆＋倒木＋枯樹圍住，只有越過倒木進得去，近戰碰不到）：建議內容修（把圍住的倒木換成草叢或挪開一格），我沒動戰鬥地圖。
3. **獸躍的 AI 只在「往上、而且落地打得到人」時用**（條件式路徑）；一般效用評分仍可能把它當成 1 AP 的平移位移。`race_ai.light_body_height: 4` 是初值。
4. **B 的兩個組合**：熔岩洞主＋晶能義體人（60 場 60%，組合平均 46%）、藥師谷丹爐 `furnace_tide`＋海民（92% 對 80%）。建議先把這兩組 10 族都補到 60 場再決定要不要調內容（盤點原則 4：調內容，不調種族）。
5. **建角簡介字數上限**：#138 定稿的獸耳族簡介 41 字，超過原本的 40 字上限，我把 `RACE_BLURB_MAX` 放寬到 48。建角卡排版要不要另外看，請美術 PM 確認。
6. **事件 18「獸耳族主角有專屬對話選項」**：事件骨架沒有「依種族出現的解法」機制，我只寫在解法說明裡（說書人看得到），沒有新增機制；霜音的專屬對話則用 `TalkEntry.races` 做成真的聊天內容（`frost_chime_kin`，台詞是我暫定的問句）。要不要給事件 18 也做依種族的選項，請玩法 PM 定。
7. **免費換種族的地點與對象**：照 #108「在主城重選種族」限主城；所有角色這一季都有一次（不只舊狐族，避免要分辨誰是舊角色）。換種族不改紙娃娃（前端本來就照種族預設畫跟著種族的部件）。#108 的付費重選還沒做。
8. **雲嶺攀爬跳躍模板**：盤點表的 `acolyte_find_way` 已經 3 種方法、3 種屬性（上限），沒加；改加在 `deserter_hide`，雲嶺達 3 個。
9. **輕身的攀跳**：輕身單位可以用攀跳往下跳 2 層以上（原本因為「會摔傷」不准）。
10. 賽季 Boss（裂界門）沒進 B 矩陣（開戰路徑不同），需要的話下一段補。

## 9. commit

（見最後回覆）
