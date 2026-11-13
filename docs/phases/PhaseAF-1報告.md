# Phase AF-1 報告：A 段規則小修、中毒 2 階白板、凝神（引擎＋內容＋測試）

依據：使用者對 `docs/玩法PM交接.md` 4.1.1 A 段 5 題「都照建議」（玩法 PM 寫入設計，commit `809c61f5b`：05 5.7、06 6.32.1、18、19）；追加三項依 `docs/玩法PM交接.md` 4.1.3（commit `a3bdf3110`）。
基準：main `e30a94693`（含 KW-2，`c9f644443` 起；中途 `git merge main` 拿到 `a3bdf3110`）。
依使用者 11-13 指示沒有跑平衡模擬或量測；沒跑全量 `scripts/check.py`。只動後端、內容、測試與文件；前端只重產一個夾具（見第 1 節第 4 點）。

## 1. 做了什麼

**1. 白板測試放寬整個拿掉，改補內容**（4.1.3 第 11 點）

- 先照派工把 KW-2 的 `_composes()` 收窄成明確清單 `KNOWN_GAPS`＋「清單內確實組不出來」的提醒斷言；收到追加後補內容，**連同 `KNOWN_GAPS` 與提醒斷言整個拿掉**，`tests/skillgen/test_whiteboard.py` 回到 KW-1 時的嚴格條件（有主動白板配方的關鍵字一定是組合器白板），沒有任何例外。
- 原因：中毒的主動配方（淬毒、毒沼、瘴氣）都是點數固定的「施加中毒／造毒液」，2 階起調不進預算窗（每個配方 × 40 種子的 `_attempt` 全是 `Retry`），所以 2 階以上**不論武器類別**都組不出中毒的主動白板（不只法器）。
- 補 1 個配方 `bone_rot`「蝕骨咒」（`content/skill_composer.yaml`）：對中毒目標的條件傷害（`strike`、毒素傷害、`target_has_status: poison`）、`min_tier: 2`、只出法術。實測 2、3 階 × 四種武器類別 × 20 種子全部組得出來、推導得出中毒；1 階的結果與改前逐字相同（`min_tier: 2`）。另一個例子「毒霧彈」（範圍施加中毒）照現行結構就是 2 階組不出來的那一類，沒有補。

**2. 05 5.7 瞄準預告**

- **隊友擋在中間＝改打擋住的人**：`lock_on.lock_victim`——直線上有目標陣營的存活單位時改打離弓手最近的那個（照一般施放對他選取）；`delayed._release_lock` 先發新事件 `lock_intercepted`（`unit_id`、`skill_id`、`name_zh`、`target_id`＝原本瞄準的人、`blocker_id`），再結算。擋住的人本身選不到（例如他是 2 格外的隱蔽）時才照舊 `lock_on_blocked` 落空（保守做法，見第 6 節）。戰鬥紀錄句子：「⛨ X 擋在 Y 前面：「鶴唳穿雲」改打在 X 身上」。
- **隱蔽照一般隱蔽規則**：拿掉「不論距離都落空」；射出時照一般施放的選取（2 格內照射）。選不到而且目標是看不見的隱蔽時記 `lock_on_concealed`，其他記 `lock_on_lost`。
- **只限敵方**：`targeting.aims_first(caster, skill)`（`lock_on` 而且施放者不是 `Team.ALLY`；`lock_on` 照樣匯出）是唯一的判斷，施放、選目標（不給物件）、預覽的 `lock_fire` 都走它。內容檢查本來就只准 `enemy_only` 招帶 `lock_on`；這條擋的是「玩家方用到敵人的招」（例如複製技能），放出去就是一般施放。
- AI 的「現在就射出」估值（`Preview.lock_fire`）不算擋箭，照舊。

**3. 18、19 核對**

- 符籙師的「強力一擊」＝**定身符**（`skill_binding_talisman`，`lock_on: true`；符籙師另一招是寂言咒，雷符師變體也保留定身符）。RG-1 已做，沒改。
- 熔岩彈（`skill_lava_bomb`）：`burning` 2 回合、沒有造火地；噴岩龜身上沒有火牆。RG-1 已做，沒改。

**4. 06 6.32.1 一次出招最多 +1**

- `stack_gain._collect(..., once=True)` 不再分目標：同一個持有者、同一種層數在一次出招（`holding` 括號）內只記一筆。武器技（連擊點）原本是「同一個目標一次」→ 範圍武器技打中好幾個人也只 +1；普攻（氣）原本沒有上限 → 雙匕首普攻打兩下也只 +1。
- 連擊的說明字（`content/skill_keywords.yaml`）括號改成「（一次出招最多 1 點）」（4.1.3 第 10 點）。

**5. 凝神拿掉定身代價**（4.1.3 第 2 點）

- `content/skills/skill_centering.yaml`：`cost` 拿掉 `self_status: root`，施放台詞改成不提「釘在原地」；護盾、+1 專注、法力 2、冷卻 1 不動（省下的預算照工坊）。仍通過預算與結構驗證。
- 前端夾具 `client/src/render/fixtures/skill_icons.json` 跟著重產（凝神的代價少了定身那一筆，`uv run python -m tests.narrative.icon_fixture`）；qIcon、`skillIcon`、`qi2cWiring` 的 vitest 都過。這是 `client/` 裡唯一動到的檔案。

**6. KW-2 其他示範招改寫**：全部接受，沒動（4.1.3 第 3 點）。

## 2. commit

| commit | 內容 |
|---|---|
| d249dda7e | 收窄成 `KNOWN_GAPS` 的中途版（之後被下一個 commit 取代；保留在歷史裡） |
| dee4b8f82 | 內容：`bone_rot` 蝕骨咒；拿掉白板測試的放寬 |
| 38b165b06 | 引擎：擋箭改打擋住的人、隱蔽照一般規則、只限敵方、一次出招最多 +1、`LOG_FORMAT` `/122`、測試 |
| 5af217b92 | 內容：凝神、連擊說明字；重產圖示夾具、CLI 快照 2 鍵、parity 2 筆 |
| （本報告的 commit） | 文件：本報告、紀錄格式文件 `/122`、上手筆記 |

## 3. 不變比對與快照（先預測再比對）

| 項目 | 預測 | 實際 |
|---|---|---|
| 只補 `bone_rot`（引擎未改）時的 `tests/cli`＋`tests/api`（含 slow：CLI 快照、`test_sim_real`）與 `tests/skillgen`、`tests/content`、`tests/roguelite` | 只有固定種子在 2 階以上抽到中毒白板候選的才會變；現有快照的戰鬥鍵不經過三選一 | 全過，沒有要重產的（`1456 passed, 1 skipped`；`7637 passed, 14 skipped`） |
| 不變比對（改前＝main `e30a94693` 用 `git archive` 解開、`PYTHONPATH` 指過去；8 張地圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，地圖預設陣容、效用 AI、`max_rounds=30`；比整份事件、步驟、去掉內嵌規則包的最終狀態） | 8 張圖的預設陣容沒有瞄準招的敵人（雲鶴使、符籙師、噴岩龜都不在），也沒有任何單位帶消耗連擊點或氣的技能（不會自動累積），所以全部逐字相同；`ruleset_hash` 全變（技能表的凝神、關鍵字表的說明字都在規則包裡；組合器配方不在） | `battles=46 events=20499 different=0 ruleset_hash_changed=46` |
| 一場重播 `open_plain` 種子 7 | 通過 | 「重播驗證通過：91 個動作、383 個事件，最終狀態一致（open_plain，種子 7）」 |
| slow：CLI 快照、`test_refactor_parity`、engine 的 slow 檔 | CLI：`skills_list`（凝神的代價欄少了定身）與凝神所在的分片 `skills_show_all/01`（429 招、每片 27 招，凝神排第 41）共 2 鍵；戰鬥鍵不變。parity：只有 `skill_centering` 的完整強度與升階重配兩筆（閃現對照取樣若含凝神再多一筆）；engine slow 不變 | 失敗的正好是這 4 鍵（`skills_list`、`skills_show_all/01`、`test_complete_strength_unchanged[skill_centering]`、`test_retier_unchanged[skill_centering]`），其餘 `976 passed, 4 xfailed`。CLI 用 `UPDATE_CLI_SNAPSHOTS=1` 只重產這 2 鍵；parity 夾具只手改 `skill_centering` 這 2 筆（整份重產會連閃現取樣一起換掉，沒用），之後 `952 passed` |

## 4. 版號

- `LOG_FORMAT`：`/121` → `/122`。結算語意改了（擋箭改打擋住的人、隱蔽、只限敵方、連擊點與氣的上限）＋新事件 `lock_intercepted`。同步 9 處寫死 `trpg-battle-log/122` 的字串（`tests/cli/` 6 個檔 7 處、`test_gear_g2.py`、`test_gear_g3a.py`）與 3 個 `endswith("/122")`（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`）；`docs/phases/戰鬥紀錄格式變更.md` 加 `/122` 一條。
- `WORLD_RULES_VERSION`：**不升**（31）。只有世界規則的**程式**改了才要手動升；這段沒動 `world/`。世界日誌的規則鍵本來就含戰鬥紀錄版號與內容 digest，`/122` 與內容變動會自動把舊日誌標成規則已變。
- `CHAR_FORMAT`：**不升**（`/15`），存檔欄位沒變。
- API：只新增事件型別 `lock_intercepted`（事件不在 OpenAPI 裡，前端不用重產型別）；沒改既有欄位。

## 5. 檢查（交件前）

| 檢查 | 結束碼 |
|---|---|
| `ruff check` | 0 |
| `ruff format --check` | 0（2671 個檔） |
| `mypy` | 0（1593 個檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（429 招通過預算與結構驗證） |
| 直接相關 pytest（改完引擎與內容後）：`tests/engine`（`-n 4`） | 0（4695 passed） |
| `tests/roguelite`、`tests/skillgen`、`tests/world`、`tests/api`、`tests/sim`、`tests/narrative`、`tests/content`、`test_af1_rules.py`（`-n 8`；預測：連擊／氣的上限不影響固定種子的 run auto，沒有要重產的） | 0（10881 passed、15 skipped） |
| `tests/cli`（非 slow）、`test_architecture.py` | 0（148 passed；13 passed） |
| slow：CLI 快照＋`test_refactor_parity`（重產預測內的 4 鍵後） | 0（952 passed） |
| 前端 vitest `src/render`（只重產了 `skill_icons.json`） | 0（107 個檔、1488 passed） |
| 重播 `open_plain` 7、`cloud_summit` 4 | 0（都「重播驗證通過」） |

## 6. 待 PM 決定

1. **擋住的人本身選不到時**（例如擋住的人是 2 格外的隱蔽、或他身上有讓這招不合法的條件）：現在照舊整發落空（`lock_on_blocked`），沒有改打目標本人。設計文件只寫「改打擋住的人」，沒寫這種情況；保守選了不打任何人。
2. **好幾個人擋在中間**：打直線上離弓手最近的那個（實際被箭碰到的第一個）。
3. **只限敵方的範圍**：`Team.ALLY` 以外（敵方、第三方混戰）都會瞄準。第三方（`Team.THIRD`）是「和雙方都敵對」的怪物，照「敵人」處理。
4. **設計文件同步**：06 的 6.27.1 表格與 6.32.1 示範招清單仍寫「凝神 +1 但這回合不能移動」，需玩法 PM 依 4.1.3 第 2 點改寫（開發不改 `docs/design/`）。
5. **被動另開的攻擊**：一次出招的上限以「同一次施放或一次普攻的結算括號」為界；被動觸發另外打出的武器技或普攻（在 `settle` 裡另一批）仍各自 +1。目前沒有這種內容，若玩法 PM 認為也該算同一次出招再改。
