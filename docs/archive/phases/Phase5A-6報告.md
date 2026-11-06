# Phase 5A-6 完成報告：大世界成長接點

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 12 節（先寫入規格、commit `b9b1de4b`，再實作；和 5A-5 合併後 5A-5 是第 11 節、本段改為第 12 節，「之後各段規格」改為第 13 節）。
> 只做引擎、`trpg.world`、content 的接點；沒有動 `src/trpg/api/`、`client/`（5A-5）、`trpg.roguelite` 的函式簽名與原型行為、經驗曲線與遭遇強度（5A-SIM）。
> 開發 PM 中途轉達：**增援照玩法 PM 定**（18.4 補充末尾，main `5cbda759`），已取代派工裡的保守做法。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5A-6 詳細規格 | `docs/phases/Phase5計畫.md` 第 12 節 | `b9b1de4b` |
| 2 | 引擎：先手陣營、開場狀態；戰鬥紀錄 `/99` → `/100` | `src/trpg/engine/{setup,battle,runner}.py`、`docs/phases/戰鬥紀錄格式變更.md`、`tests/engine/test_first_team.py`、測試裡的版號字串 | `2c36375e` |
| 3 | 成長接點（共用升級、07 7.6 階級、閃現等世界動作、誓約接點、`next_battle`、增援、暗門先手） | `src/trpg/world/{growth（新）,battle,encounters,actions,state,step,town,situations}.py`、`src/trpg/content/{world_oaths（新）,world_rules,world_encounters,library}.py`、`content/world/rules.yaml`、`content/world/encounters/cloud_ridge.yaml` | `79981ad7` |
| 4 | 測試 | `tests/world/test_{growth,flash_world,next_battle,oath}.py`（新）、`test_replay.py`（加）、`tests/content/test_world_encounters.py`（加） | 見 git log |
| 5 | 本報告 | `docs/phases/Phase5A-6報告.md` | 最後一筆 |

### 1.1 重用 roguelite 的方式（`trpg.world.growth`）

- `as_run(char)`／`from_run(char, run)`：角色轉成 `RunState`（成長欄位同名同型別，一輪的進度欄位用空值），呼叫 roguelite 的純函式後把成長欄位寫回。roguelite 一行都沒改。
- `world_library(library)`：roguelite 從 `library.roguelite.offer_tier_by_level` 查角色階級，大世界用這個內容庫視圖（`dataclasses.replace`，同 `trpg.sim`）把那張表換成 `hero_growth.skill_tier_by_level`（07 7.6：1～3 級 1 階、4～7 級 2 階、8～10 級 3 階）。閃現出題、傳承、升階重配因此都用 07 7.6；原型照舊 `[1,1,2,2,3,3]`。
- 角色技能種子 `fnv1a64("{season_seed}:{character_id}:skills")`：閃現選項（roguelite 標籤 `flash/<技能>/<第幾次>/<重閃次數>`）、傳承、升階重配用；不佔世界亂數串流。

### 1.2 共用升級 `gain_xp`

戰鬥（`_won`）與情境判定（`_apply_outcome`）都改呼叫 `gain_xp(library, world, char, xp)`；之後的任務來源也呼叫它。每升 1 級：屬性點 ＋2、靈感 ＋2（06 6.34.2 大世界）、最大 HP／法力增加量加到目前值（roguelite `with_hp_change`）；全部升完後角色階級變了就 `sync_skill_tier` 重配（手寫技能 → `<原 ID>_t2`，閃過的技能照新階級重推歷程）。等級上限 10（`hero_growth.level_cap`），經驗門檻仍是原型的（到 6 級，5A-SIM 再定）。

### 1.3 狀態欄位（`CharacterState`，全部有預設值，`trpg-char/1` 不升版號）

`insight`、`flash`、`flash_bases`、`pending_flash`、`generated_skills`、`skill_usage`、`skill_tier`、`attribute_spent`、`elite_kills`、`oath`、`oath_cooldown_until`。`new_character` 記 `skill_tier = 1`（開局不重配）；舊角色 `skill_tier = None`，下次升級時照角色階級同步一次。

## 2. 各接點的世界動作

| 接點 | 世界動作（`kind`） | 地點與條件 | 重用 | 事件 |
|---|---|---|---|---|
| 配點 | `allocate`（`attributes`） | 沒有遭遇；點數 ≤ 未分配 | `allocate_attributes`＋`with_hp_change` | `attributes_allocated` |
| 重配 | `respec` | 城鎮或營火 | `respec_attributes` | `attributes_respecced` |
| 閃現／重閃 | `flash`（`skill`、`slot`、`category`） | 城鎮或營火；先上場用過；點數 | `open_flash` | `flash_offered` |
| 選閃現 | `flash_pick`（`pick`、`unequip`） | 有待選；**有待選時其他動作一律拒絕** | `pick_flash` | `flash_picked` |
| 溶掉 | `dissolve`（`skill`） | 城鎮或營火 | `dissolve`（退一半） | `skill_dissolved` |
| 傳承 | `inherit`（`skill`、`source`、`records`） | 城鎮或營火 | `inherit` | `skill_inherited` |
| 立誓 | `swear_oath`（`proposal`＝模板＋參數、`player_text`、`source`、`prompt_version`） | 城鎮或營火；沒有誓約；過了冷卻；模板與參數合法（`oath_problems`） | — | `oath_sworn` |
| 解除誓約 | `release_oath` | 有誓約；冷卻 86400 秒（#106） | — | `oath_released` |
| 換技能（5A-4） | `loadout` | 改用 roguelite `set_loadout`，閃現後的生成技能也能換 | `set_loadout` | `loadout_changed` |
| 升級 | （戰鬥、情境判定的回寫） | — | `level_for`、`with_hp_change`、`sync_skill_tier` | `leveled_up`（加 `insight`、`skill_tier`）、`skill_tier_changed` |
| 先上場用過 | （`fight` 的回寫，勝負都算） | — | `collect_usage`、`after_battle_flash`（**丟掉它算的每勝靈感**，06 6.34.2 一般戰鬥不給） | — |
| 精英首殺 | （`fight` 打贏） | 每種一次 | — | `insight_gained`（`elite:<種類>`） |

**戰鬥接線**（`trpg.world.battle.prepare_battle`，簽名不變，`PreparedBattle` 多 `reinforcements`、`first_team`、`hero_statuses` 三個有預設值的欄位）：

- 規則包加入主角的 `generated_skills`。
- `next_battle` 的 buff／debuff → 主角 `UnitSpawn.opening_statuses`（擲先攻前掛上，持續回合照狀態預設；同一狀態只掛一次）。打完一場（勝負都算）清空，撤退不消耗。
- **增援（玩法 PM 定）**：`reinforce_lineup`——每一筆 `reinforce`，從同地點遭遇表各陣容出現過的非精英單位（去重、排序；已到遠程上限 2 就不抽遠程）用 `"{battle_seed}:reinforce"` 均勻抽 1 名排在陣容最後，照地點等級成長；陣容已滿 4 名改成敵人先手。增援併進 `lineup`，看陣容時就看得到。
- **暗門先手**：`content/world/encounters/cloud_ridge.yaml` 的 `cliff_gang_fort` 加 `ally_first_threads: [gang_fort_secret_door]`；角色持有這條有效個人線頭（以遭遇時間 `at` 判定到期）→ `BattleSetup.first_team = ally`。和「敵人先手」同時成立時抵銷。
- 引擎 `BattleSetup.first_team`：該陣營依原本的先攻順序排在行動順序最前面，其他單位照原順序接在後面（引擎的行動順序整場固定）。

## 3. 可重播證明

- 全部新動作在 `WorldAction` 判別聯集裡、寫進 `trpg-wlog/1`；閃現選項連同套用後的技能存在角色的 `pending_flash`，`flash_pick` 不重抽；LLM 閃現提議沒接（`llm=False`），重播不呼叫 LLM。誓約的提議與原文隨動作進日誌。
- 戰鬥設定只由「角色快照＋遭遇＋內容庫」決定（`next_battle`、線頭、生成技能都在快照裡），增援亂數只來自 `battle_seed`。
- `tests/world/test_replay.py::test_replay_with_growth`：配點 → 閃現 → 選 → 立誓 → 遇敵 → 戰鬥（升級）→ 回小鎮 → 溶掉 → 解除誓約，日誌寫出讀回（`dumps_log`／`loads_log`）重播兩次，世界與角色 JSON 逐字相同、事件相同、等於現場套用的結果。5A-4、5B-2 的重播測試照舊通過。
- `test_next_battle.py`：同一個角色快照 `prepare_battle` 兩次結果相等（含增援）。
- 原型重播：`trpg battle --map swamp --seed 7 --log-json` ＋ `trpg battle replay` 通過（88 個動作、313 個事件，和 `/99` 時相同——新欄位是預設值時結算不變）。
- `trpg.world` 內沒有時間、`random`、`uuid4`、`hash()`（`tests/test_architecture.py` 通過）。`world_library` 的模組層快取只為了沿用視圖上的重配快取（存著原內容庫本身，`id` 不會被重用），不影響結果。

## 4. 代決

| # | 事項 | 代決 | 誰定 |
|---|---|---|---|
| 5A6-1 | 主角階級表 | 07 7.6（`hero_growth.skill_tier_by_level`，和 `enemy_growth` 同表） | **玩法 PM 定** |
| 5A6-2 | 增援 | 18.4 補充（同地點遭遇表、種子、非精英、照地點等級；滿 4 名改敵人先手） | **玩法 PM 定**（main `5cbda759`） |
| 5A6-3 | 增援的抽法 | 同地點各陣容出現過的非精英單位去重排序後均勻抽；已到遠程上限不抽遠程；多筆增援各抽 1 名，滿 4 名（或沒有可抽的）就改敵人先手 | 開發 PM 定 |
| 5A6-4 | 「先手」的引擎意思 | 該陣營依先攻排最前、另一陣營接在後面（整場固定）；我方與敵人先手同時成立時抵銷 | 開發 PM 定 |
| 5A6-5 | 等級上限與到頂 | 上限 10；超過的經驗照累積、不換算 | 開發 PM 定 |
| 5A6-6 | 花靈感與重配的地點 | 閃現、重閃、溶掉、傳承、重配：城鎮與營火；配點：任何沒有遭遇的時候 | 開發 PM 定 |
| 5A6-7 | 「每種」精英 | 精英範本以單位 ID 算；一般單位套詞綴以「單位＋詞綴」算（例：北坡狼王 `mist_wolf+berserk`） | 開發 PM 定 |
| 5A6-8 | `next_battle` 的消耗 | 下一場（勝負都算）全部消耗；撤退不消耗；同一狀態只掛一次、回合照狀態預設、不擲抵抗 | 開發 PM 定 |
| 5A6-9 | 誓約模板 | 只有 schema（`trpg.content.world_oaths`）、動作、測試樣本（3 種）；`world/oaths.yaml` 不存在時立誓被拒；18.6 的 15 種與戰鬥判定在 5C-3 | 開發 PM 定 |
| 5A6-10 | 誓約冷卻 | 86400 秒（現實 1 天），在 `oaths.yaml` 的 `cooldown_seconds` | 開發 PM 定 |
| 5A6-11 | 角色技能種子 | `fnv1a64("{season_seed}:{character_id}:skills")` | 開發 PM 定 |
| 5A6-12 | 戰鬥紀錄版號 | `first_team`、`opening_statuses` 進紀錄 → `/100`；`/99` 紀錄不能重播（照慣例）；roguelite 戰鬥中的存檔照舊丟掉進行中的戰鬥 | 開發 PM 定 |
| 5A6-13 | 新角色的屬性點 | `new_character` 不知道開局怎麼配點，`attribute_spent` 從空開始：重配只退之後分配的點（同 roguelite 舊存檔） | 開發 PM 定（實作補） |
| 5A6-14 | 情境判定的升級事件 | `leveled_up` 排在 `situation_result` 之後、揭露與線頭之前 | 開發 PM 定（實作補） |

## 5. 待 PM 決定

1. **API／前端（已合併的 5A-5）**：看陣容用的是 `prepare_battle(...).lineup`，增援自動顯示；`first_team`、`hero_statuses`、新事件（`insight_gained`、`skill_tier_changed`、`flash_*`、`oath_*` 等）還沒有中文呈現。`WorldActionRequest` 只收 5A-4 的動作，新的世界動作（配點、重配、閃現、選閃現、溶掉、傳承、立誓、解除誓約）還沒有 API 與畫面——需要另排一段。
   - 和 5A-5 合併時：`CharacterState.generated_skills` 兩邊都加了，保留 5A-5 的欄位位置與排序檢查；`town.loadout` 改用本段的 roguelite `set_loadout`；`prepare_battle` 保留本段版本（生成技能已併進規則包）。5A-5 的 `tests/world/test_generated_skills.py`、`tests/api/test_world_api.py` 照舊通過。
2. **戰鬥紀錄 `/100`**：同時有別的段改引擎時，合併要再遞增一次版號。
3. **經驗曲線**：原型門檻只到 6 級，所以 8 級升 3 階目前到不了（階級表已照 07 7.6）；交 5A-SIM。
4. **其他靈感來源**：任務鏈段落、世界事件各 1 點（06 6.34.2）要等 5B-4、5F；到頂後經驗換靈感的比例待定。
5. **大世界的新技能來源**（任務、劇情、機遇、許願池的白板／完整技能三選一）與 LLM 閃現提議接線：之後的段；roguelite 的 `take_candidate`、`with_acquired` 可以照同樣的 `as_run` 方式接。
6. **誓約**：5C-3 要寫 `content/world/oaths.yaml`（18.6 的 15 種）、加成查表、違反判定（事件日誌）、佔被動欄位（06 6.26）、LLM 轉換（`<player_input>`）。
7. **先手的強度**：先手陣營整場都排在前面（引擎行動順序固定），比「只有第一輪先動」強；要不要改成只影響第一輪，需玩法 PM 定（要改引擎）。
8. **開場 debuff 不擲抵抗**：中毒、流血這類有 `save_attr` 的狀態，情境判定給的版本直接掛上；要不要擲抵抗待玩法 PM。

## 6. 檢查結果

交件前已 `git merge main`（含 5A-5 的 API 與前端、18.4 補充的增援）；衝突在 `world/{state,battle,town}.py` 與計畫文件，處理方式見第 5 節第 1 點。

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 通過（沒有新增 `# noqa`，`C901` 沒有超標） |
| `mypy`（strict，1011 檔） | 通過 |
| `lint-imports` | 9 條契約全部 KEPT |
| 合併前 `pytest tests/world tests/roguelite tests/content tests/engine/test_first_team.py tests/test_architecture.py -n 8` | 2324 passed |
| 合併後 `pytest tests/world tests/api/test_world_api.py tests/engine/test_first_team.py tests/test_architecture.py tests/content/test_world_encounters.py -n 8` | 286 passed |
| 合併後 `pytest tests/cli -m "slow or not slow" -n 8 --timeout=3000` | 180 passed（快照沒變） |
| 原型重播 `trpg battle --map swamp --seed 7 --log-json` ＋ `trpg battle replay` | 通過（88 個動作、313 個事件） |
| 世界日誌重播（`test_replay_with_growth`、`test_replay_with_battle_and_town`、5B-2 的重播） | 通過 |

沒有跑全量 `scripts/check.py`（PM 合併時跑）。

## 7. 5A-6b（玩法 PM 代決 2026-11-03）

- **先手只影響第 1 輪**：`begin_battle` 照 5A-6 把 `first_team` 陣營排在最前，並把正常先攻順序記進 `BattleState.normal_turn_order`；`turns._end_round` 在第 2 輪開始時還原（發 `turn_order_set`；第 1 輪中途離場的略過、中途加入的召喚物與復活單位接在後面）。我方與敵人先手同時成立仍互相抵銷。
- **開場 debuff 持續最多 2 回合**：`opening_statuses` 照舊不擲抵抗，施加時 `duration = min(狀態預設, 2)`（`OPENING_STATUS_MAX_DURATION`；預設不倒數的狀態維持原樣）。例：中毒預設 3 → 2。
- **`LOG_FORMAT` 遞增為 `/101`**（`BattleState` 新增欄位、第 2 輪順序結算改變）；`/100` 紀錄不能重播；`docs/phases/戰鬥紀錄格式變更.md` 已補條目；測試裡的字面值已改。
- 測試：`tests/engine/test_first_team.py` 新增「開場狀態上限 2」「先手只影響第 1 輪、第 2 輪恢復」。
- 待 PM 決定：第 5 節第 7、8 點已依此解決。
