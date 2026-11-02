# Phase 5A-2 完成報告：`trpg.world` 套件骨架

> 實作者：implementer agent（2026-11-02）。規格：`docs/phases/Phase5計畫.md` 第 6 節（本段先寫入規格、commit `8a9cd623`，再實作）。
> 只動 `src/trpg/world/`（新）、`src/trpg/content/world_rules.py`（新）、`src/trpg/content/library.py`、`content/world/rules.yaml`（新）、`tests/world/`（新）、`tests/test_architecture.py`、`pyproject.toml`（import-linter）、`docs/phases/Phase5計畫.md`（第 6 節）。沒有動 API、前端、引擎、roguelite、`content/skills/`、`src/trpg/skillgen/`。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5A-2 詳細規格（計畫第 6 節，原第 6 節改為第 7 節） | `docs/phases/Phase5計畫.md` | `8a9cd623` |
| 2 | 世界規則數值與 schema、`ContentLibrary.world_rules`、跨檔案檢查 | `content/world/rules.yaml`、`src/trpg/content/world_rules.py`、`library.py` | `07401c99` |
| 3 | `trpg.world` 套件；import-linter 2 條新契約＋3 條加 `trpg.world`；架構測試 | `src/trpg/world/`、`pyproject.toml`、`tests/test_architecture.py` | `757a76cf` |
| 4 | 測試（84 個） | `tests/world/` | `fba50839` |
| 5 | 本報告 | `docs/phases/Phase5A-2報告.md` | |

## 2. 模組結構（`src/trpg/world/`）

| 模組 | 內容 |
|---|---|
| `clock.py` | `GAME_DAY_SECONDS=1800`、`WEATHER_PERIOD_SECONDS=900`、`UTC_OFFSET_SECONDS=8h`、`REFRESH_HOUR=6`；`game_day_index`、`half_day_index`、`day_phase`（前半白天、後半夜晚）、`game_clock`（遊戲日從 06:00 起）、`refresh_day`（台北 6 點為界）、`next_refresh_at`。只吃 `now`（UTC 秒整數），不讀時間。 |
| `rng.py` | `derive_seed(season_seed, character_id, stream, counter) = fnv1a64("{seed}:{char}:{stream}:{counter}")`；`region_seed`（角色段 `@<region>`）；`draw(seed, char, stream) → (Rng, 計數+1 的角色)`。串流：`travel`、`battle`、`reveal`、`weather`。 |
| `state.py` | `WorldState`（`trpg-world/1`：`season_id`、`season_seed`、`season_start`、`flags`、`cleared`）、`CharacterState`（`trpg-char/1`：`hero`、`origin`、`level`、`xp`、`hp`、`mana`、`stamina` 同 `RunState`；`region`、`location`、`supplies`、`revealed`、`perception_marks`、`rng_counters`、`pending_encounter`、`camped_at`）、`EncounterResult`、`LocationRef`、`ClearedLocation`、`PerceptionMark`。集合欄位一律排序、驗證時拒絕未排序或重複。 |
| `actions.py` | 動作 `TravelAction(to, hasten)`、`CampAction`；事件 `traveled`、`encounter_check`、`encounter`、`perception_check`、`location_revealed`、`camped`（pydantic 判別聯集）。 |
| `weather.py` | `weather_at(library, world, region, now)`：同區同半天所有人相同，依 `rules.yaml` 白天／夜晚權重抽，不存狀態。 |
| `step.py` | `world_step(library, world, char, action, now) → StepResult(world, char, events)`；`new_character`、`max_hp`／`max_mana`（同 `RunState` 公式）、`perception_modifier`（同引擎檢定修正）、`camp_problem`、`reveal_location`。 |
| `replay.py` | `WorldLogEntry(seq, now, character_id, action)`、`replay(library, world, characters, entries)`（`seq` 嚴格遞增、`now` 不倒退）。 |
| `save.py` | `dumps_/loads_world`、`_char`、`_log`（JSON 排序鍵、UTF-8；日誌第一行 `{"format": "trpg-wlog/1"}`）；未知 `format` 拒絕；`write_atomic`（暫存檔＋`os.replace`）。 |
| `errors.py` | `WorldError`、`WorldActionError`、`WorldReplayError`、`WorldSaveFormatError`。 |

`trpg.world` 只匯入 `trpg.shared`、`trpg.content`（本段沒用到 engine／roguelite；HP／法力上限直接用 `CoreRules` 的同一個公式）。

### 規則摘要

- **移動**：只能走鄰居；未發現的隱藏地點、旗標未成立的 `unlock_flag` 地點、有未處理遭遇時不能走；趕路扣 `hasten.cost` 補給、機率 ×500‰。遇敵機率＝min(500, 150＋30×(目的地 `level_max`−1))‰，城鎮與傳送點 0；機率 0 也照擲（亂數消耗固定）。遇敵 → `pending_encounter`（地圖從目的地 `battle_maps` 抽、32 位元戰鬥種子、當下天氣與日夜、時間），角色仍抵達目的地。
- **感知判定**（#112）：抵達後對每個相鄰的隱藏地點（`reveal` 含 `perception_nearby`、還沒發現、今天沒判過；鄰居依 ID 排序）擲 d20＋感知修正 ≥ 10＋`level_min`÷2；記錄 `refresh_day`；失敗無懲罰。雲嶺實際只有鶴歸崖（DC 13）會被判；丹爐洞只有 `situation` 不判。
- **紮營**（#114）：城鎮（直接休息，5A-4）、精英巢穴、Boss 地點不行；營地要 `world.cleared` 有它且 `now < respawn_at`；花 1 補給；HP、法力回滿、耐力設 `None`（滿）、`camped_at` 記地點，移動就清掉。

## 3. 確定性與重播測試

- 引擎內沒有讀時間、`random`、`uuid4`、內建 `hash()`：`tests/test_architecture.py` 把 `world` 加入確定性套件，掃描器新增「禁止呼叫內建 `hash()`」（全部確定性套件都適用；目前 `src/` 沒有任何呼叫）。
- `test_rng.py`：衍生字串格式的固定測試向量（改了會讓舊日誌重播不同）、各段改變都改變種子、`draw` 只推進自己的串流、天氣同區同半天相同、權重 0 抽不到、賽季種子不同則天氣序列不同。
- `test_replay.py`：60 步雙角色的實際遊玩 vs. 從初始快照重播，快照 JSON（世界＋角色）逐字相同、重播兩次事件相同；日誌寫出再讀回重播相同；`seq` 重複、時間倒退、未知角色 → `WorldReplayError`；**hypothesis**（25 例）：隨機賽季種子＋隨機動作序列，重播快照與實際遊玩逐字相同。
- `test_save.py`：三種格式往返相等且再序列化逐字相同；9 種壞格式拒絕；未排序集合拒絕；原子寫檔不留暫存檔、LF 換行。

## 4. 檢查結果

- 測試與靜態檢查見第 7 節。
- `uv run trpg content check`：列出「`world/rules.yaml`：補給上限 10、紮營 1、遇敵 150～500‰、5 區天氣」。
- 沒動戰鬥，不需戰鬥重播；沒跑全量 `scripts/check.py`。

## 5. 代決清單（開發 PM 規格 6.9 ＋ 實作時補的，都照最保守做法）

1. **代決 5A2-1**：時鐘常數（30 分鐘、半天、+8、6 點）寫在程式，不放 content（使用者已定的值，改要回使用者）。
2. **代決 5A2-2**：遊戲日對齊 Unix 紀元（因此每天 6 點刷新一定是遊戲日開頭）；遊戲日從遊戲內 06:00 開始，前半白天、後半夜晚。
3. **代決 5A2-3**：數值初值（`content/world/rules.yaml`）：補給上限 10、新角色 5、紮營 1、趕路 1 補給 ×500‰、遇敵 150＋30/級、上限 500‰、天氣權重（傾向 3、其他 1；`night` 天氣只在夜晚半天抽；晶冠、樞市的「夜」傾向加在 night）。之後用模擬定。
4. **代決 5A2-4**：遇敵用目的地 `level_max`；城鎮、傳送點 0；遇敵後角色仍抵達目的地（感知判定照做），遭遇擱在角色上，處理前不能移動或紮營（5A-4 開戰後清掉）。目的地沒有戰鬥地圖（村落、祭壇等）時 `battle_map=None`，由 5A-4 從區域地圖池挑。
5. **代決 5A2-5**：感知 DC 的「建議等級」用隱藏地點的 `level_min`（雲嶺兩個都是單一等級，不影響）。
6. **代決 5A2-6**：傳送點、商隊、異象可以紮營；城鎮不能「紮營」（城鎮休息是 5A-4 的服務，回傳「城鎮裡直接休息」）。
7. **代決 5A2-7**：天氣的角色段用 `@<region>`、計數用半天序號。
8. **代決 5A2-8**：重播從「初始世界＋初始角色快照」開始，角色建立不進日誌（5E-1 再做）。
9. **代決（實作補）**：`new_character` 的英雄範本由呼叫端給（`UnitTemplate`），本段沒有創角流程；角色 ID 照 `ID_PATTERN`。
10. **代決（實作補）**：`world_rules` 是選填檔（不在 `KNOWN_CONTENT_FILES`，同 `dev_starters.yaml`）：舊測試複製的精簡 content 沒有它時 `world_rules=None`，呼叫世界規則才報錯。
11. **代決（實作補）**：`perception_marks` 每個隱藏地點只留最後一次（足以判斷「今天判過沒」）。
12. **代決（實作補）**：日誌標頭只有 `format`（不帶賽季 ID）；`now` 不可倒退、`seq` 嚴格遞增（單一寫入佇列保證）。

## 6. 待 PM 決定

- **任務指示的編號對照**：派工訊息寫「#113 隱藏地點感知」「#115 營火」，09 9.6.11 實際是 **#112**（感知）、**#114**（營火）；#113 是野外回復、#115 是方法分類。本段照 9.6.11 的內容做、文件引用實際編號。
- 「已清空」的寫入與重生時間（9.6.7 #15「一段時間後重生」）：本段只讀 `world.cleared`；重生秒數由 5A-4／5F-1 定（建議放 `rules.yaml`）。
- 遭遇時角色已抵達目的地；若 5A-4 的「戰前看陣容可撤退」要退回出發地，需要在 `EncounterResult` 加 `from_location`（目前事件 `traveled` 有記，但遭遇本身沒存）。
- 用了 18 號文件的內容：只用了 5A-1 已載入的雲嶺地點圖（鶴歸崖、丹爐洞的隱藏方式與等級、`ashen_ferry` 的 `unlock_flag`）；05 5.1 的雲嶺「霧、雨」天氣傾向。

## 7. 檢查紀錄

- `uv run pytest -q tests/world tests/content tests/test_architecture.py -n 8 --timeout=1800`：**1801 passed**（73 秒；其中 `tests/world` 84 個）。之後把掃描器的呼叫檢查拆成 `_call_violations`（PLR0912）、`test_clock.py` 的 `_ts` 改參數，重跑 `tests/world/test_clock.py tests/test_architecture.py`：16 passed。
- `ruff check .`：通過；`ruff format --check .`：1507 files already formatted。
- `mypy`（strict，全專案 967 檔）：Success。
- `lint-imports`：9 個契約全部 KEPT（新增「world 不得匯入上層模組」「下層模組不得匯入 world」；engine、narrative、shared 契約加上 `trpg.world`）。
- `uv run trpg content check`：通過，列出 `world/rules.yaml` 摘要。
