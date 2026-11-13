# Phase RG-1 報告：瞄準預告與盾兵（引擎＋內容）

規格：`docs/phases/PhaseRG計畫.md` 第 1 節（RG-1）。依據 #162（05 5.7、09 9.6.6、18、19；設計 commit 967363244）。

## 1. 做了什麼

**瞄準預告**（`lock_on`）

- 技能欄位 `SkillDef.lock_on`（沒填不輸出，既有技能的序列化與雜湊不變）；內容檢查 `_lock_on_problems`：只能是 `enemy_only`、一般主動、單體、沒有第二段與陷阱、第一個效果對敵人。
- 施放＝瞄準：`interpreter.use_skill` 付完代價走 `delayed.charge_lock_on`——施放者帶 `charging`（`StatusInstance.lock_target`）、發 `followup_charged`（`lock_target_id`，`pos`／`tiles`＝目標當下的格子）、面向目標，不擲命中。
- 射出：施放者下回合開始 `_release_lock`；`lock_on.lock_problem` 依序檢查目標倒下（`lock_on_lost`）、隱蔽不論距離（`lock_on_concealed`）、一般選取的射程與視線（`lock_on_lost`）、目標隊友擋在中間（`lock_on_blocked`，施放者自己陣營不擋），都過才照一般施放結算（`run_delayed`，不再付代價）。
- 打斷：`hit_reactions` 開頭，瞄準中被敵人近戰命中 → `followup_cancelled`（`interrupted`）。遠程打中不打斷。
- 預告與 API：`ChargeInfo`／`TelegraphCharge`／`ChargeOut` 多 `lock_target_id`；預告文字「正在瞄準 X」；戰鬥紀錄「◎ 雲鶴使 瞄準了 盜賊」與三種落空句、打斷句。重產 `client/openapi.json`、`schema.d.ts`；前端畫法不動（目標格照既有的「蓄」預計範圍顯示，RG-3 再畫準星與線）。
- legal_actions 不列瞄準招的物件目標。

**盾兵掩護**（`shield_guard` 標籤）

- `rules/combat.half_cover`：場上沒有掩護物時看 `_guard_cover`（目標是遠程＝武器不受高度限制；相鄰同陣營帶 `shield_guard` 的單位在攻擊者那一側，幾何同半掩護物件），再看塔盾；懲罰 `core.shield_guard_hit_penalty`（新欄位，`core.yaml` 寫 2，開放工坊）。
- `attack_rolled.cover_unit_id`（沒有不輸出）；紀錄「盾兵掩護 −2［命中 −2：被持盾弟子的盾擋住］」；預覽說明「盾兵掩護 −2：被 持盾弟子 的盾擋住」。

**AI**

- 盾兵站位：位置價值 `screen`（`AiWeights`；`guard` 模式 12）——每替一名相鄰遠程同伴擋住至少一名打得到他的遠程敵人加分，只算帶標籤的單位。遠程的 `cover` 項也算盾兵。實測：盾兵從 (6, 7) 直接走到弓手與敵人之間的 (5, 4)。
- 敵人會瞄準：`preview` 對瞄準招另算「現在就射出」的預覽 `Preview.lock_fire`（`Ctx.fire_lock`，只能在預覽模擬用），`scoring._lock_gains` 用它 × `rewrite.lock_on_permille`（初值 700）。

**內容**（數值初值，照工坊）

| 新 | 給誰／在哪 | 取代 |
|---|---|---|
| `skill_crane_piercing_shot` 鶴唳穿雲（2 AP、耐力 10、冷卻 2；×1000，居高 +×800） | 雲鶴使（冰鶴使跟著） | 高處狙擊（主角弓手的不動） |
| `skill_binding_talisman` 定身符（1 AP、法力 5、冷卻 2；1d4 冰＋定身 1） | 符籙師（雷符師跟著） | 寒鎖（主角法師的不動） |
| `skill_lava_bomb` 熔岩彈（2 AP、法力 10、冷卻 4；3d8 火＋燃燒 2） | 噴岩龜 | 火牆 |
| `sect_shield_disciple` 持盾弟子（照盜賊盾衛；盾擊、嘲諷吼） | 雲海吊橋「吊橋盾陣」、古松祭壇「祭壇盾陣」 | 新陣容，原陣容不動 |
| `molten_shell_trooper` 熔殼甲兵（熔岩甲蟲體型；盾擊、破城衝撞） | 焦油坑「熔殼與噴岩龜」、熔岩洞窟「洞窟熔殼陣」 | 新陣容，原陣容不動 |

盾兵外觀先暫代：持盾弟子＝修士袍＋鳶盾，熔殼甲兵＝熔岩甲蟲外觀（美術需求在規格第 5 節）。

## 2. commit

| commit | 內容 |
|---|---|
| 3b950b024 | 規格 `PhaseRG計畫.md` |
| 254cb0e12 | 引擎：瞄準預告、盾兵掩護、`LOG_FORMAT` `/120`、測試 |
| f022cec23 | 內容：三招、兩名盾兵、遭遇表、AI 估值、前端夾具與 API 型別 |
| （本報告的 commit） | 測試同步、CLI 快照、上手筆記、紀錄格式文件、報告 |

## 3. 確定性：預測與實際

| 項目 | 預測 | 實際 |
|---|---|---|
| 不變比對（改前＝`git archive 3b950b024`，8 張地圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，比整份事件、步驟、去掉內嵌規則包的最終狀態） | 地圖預設陣容沒有雲鶴使、符籙師、噴岩龜、盾兵，全部逐字相同；`ruleset_hash` 全變（新增內容） | `battles=46 events=20499 different=0`，`ruleset_hash` 46／46 變 |
| CLI 快照（slow，24 鍵） | 7 場戰鬥鍵不變；`skills_list` 與 `skills_show_all/00～15` 共 17 鍵變（新增 3 招，第一招 `skill_binding_talisman` 排在 b 開頭，16 片全部位移；腳本先算過分片） | 失敗的正好是這 17 鍵，只重產這 17 鍵；之後 24 passed |
| 其他 slow（engine 的 5 個 slow 檔、`test_refactor_parity`、`test_leap_check`） | 不變（不用到這些敵人；3W-R2 對照只看玩家技能，新招都是 `enemy_only`） | `905 passed, 4 xfailed`，沒有要重產的 |
| 一場重播 `open_plain` 7 | 通過 | 「重播驗證通過：91 個動作、383 個事件，最終狀態一致」 |
| 帶瞄準與盾兵的自動對戰重播（scratchpad 腳本，雲鶴使＋持盾弟子＋噴岩龜 對 戰士＋弓手＋法師，種子 1～3） | 事件與最終狀態一致 | 3 場都一致；瞄準 2／1／1 次、打斷 1／0／1 次 |
| 性質測試（hypothesis） | 瞄準與射出同輸入同事件；沒有盾兵時掩護只來自物件 | 通過 |

## 4. 版號

| 版號 | 變更 | 原因 |
|---|---|---|
| `LOG_FORMAT` | `/119` → `/120` | `StatusInstance.lock_target`、`followup_charged.lock_target_id`、`followup_cancelled`／`cancel_charge` 的 `interrupted`、`attack_rolled.cover_unit_id`；新結算規則（瞄準、盾兵掩護）。同步 8 個寫死字串的測試與 3 個 `endswith` 測試（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`，都跑過）。`docs/phases/戰鬥紀錄格式變更.md` 加 `/120` 一條。 |
| `WORLD_RULES_VERSION` | 不變（本 worktree 是 29；派工寫 30，可能是其他分支） | 世界規則程式沒改；遭遇表、單位、技能都是內容（內容雜湊會變） |
| 地圖規則雜湊 `RULE_HASHES` | 不變 | 沒動實地地圖 |
| `CHAR_FORMAT`、`SAVE_FORMAT`、`WLOG_FORMAT` | 不變 | 沒動存檔結構 |

注意：KW（#161）也可能升 `LOG_FORMAT` 到 `/120`；兩段一起合併時由 PM 對齊成 `/120`、`/121`。

## 5. 改動的既有測試（都是內容增加帶來的，斷言意義不變）

- `tests/content/test_con_hp.py`：`OLD_HP` 加兩名盾兵（36、48）。
- `tests/content/test_world_enemies.py`：雷符師與符籙師的招換成定身符；測試用變體的換招來源跟著改。
- `tests/world/test_enemy_smoke.py`：新敵人 33 → 35。
- `tests/skillgen/test_enemy_only.py`：敵人專用招清單加 3 招（只改測試檔，沒動 skillgen 程式）。
- `tests/api/tuning/`：核心欄位多 `shield_guard_hit_penalty`；技能檔 406 → 409；「升階說明」改看定身符（符籙師不再用寒鎖）。
- `tests/narrative/test_skill_icon_art_qi2a.py`、`tests/content/test_skill_scaling.py`：409 → 412 招；`tests/content/test_tuning_fields_nw2a.py`：技能檔 406 → 409。
- 前端：`qIconSkills.test.ts` 409 → 412、`qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE` 加 3 招、`inkDollSnapshot` 只多一行 `sect_shield_disciple`、`creatureAction.test.ts` 拿掉「噴岩龜火牆」那列（噴岩龜不再帶火牆；錐形由硫煙獸兩列涵蓋）。
- 重產：`unitDolls.json`、`skill_icons.json`、`client/openapi.json`、`schema.d.ts`、CLI 快照 17 鍵。

## 6. 檢查結束碼

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（412 個技能通過） |
| 直接相關 pytest（新測試、3 個 `endswith`、clone、determinism、延遲段、反應、預覽、AI、`tests/content`、`tests/narrative`、`tests/cli`、`tests/api/tuning`、夾具、OpenAPI、架構…，`-n 8`） | 0（最後一次：4236 passed 後修 2 個技能數斷言，再跑那 2 檔 436 passed） |
| 遭遇地點相關的 `tests/world`、`tests/api`（20 檔） | 0（277 passed） |
| slow：CLI 快照 | 0（重產 17 鍵後 24 passed） |
| slow：engine 5 檔＋`test_refactor_parity`＋`test_leap_check` | 0（905 passed、4 xfailed） |
| `trpg battle --map open_plain --seed 7` ＋ `replay` | 0、0（重播驗證通過） |
| 前端 `vitest run`（全部）、`typecheck` | 0（4385 passed）、0 |

沒跑全量 `scripts/check.py`、沒跑模擬報表（守則 11）。

## 7. 撞檔（KW 在做 #161）

沒動 `skill_keywords`、資源機制、既有技能內容、skillgen 程式。引擎裡和 KW 可能重疊的檔，都是只新增：

- `engine/reactions.py`：`hit_reactions` 開頭多 2 行（打斷瞄準）、匯入多兩個名字、`AttackRolled` 多帶一個欄位。
- `engine/skills/interpreter.py`：`use_skill` 多一個檢查與一個 `elif` 分支。
- `engine/skills/targeting.py`：`_candidates` 的物件目標條件多 `and not skill.lock_on`。
- `engine/ai/utility/scoring.py`：`_preview_score` 的 `_gains(...)` 改成 `_lock_gains(...)`（唯一改既有一行；沒有瞄準時結果相同），新增 `_lock_gains`。
- `content/skills/` 只新增 3 個檔；`content/units/` 改了三名敵人的 `skills` 一行。

## 8. 待 PM 決定

規格第 6 節列了 14 條（RG-1 用到 1～11、14）；實作中多出或要特別注意的：

1. **熔岩彈「造火地」做不到**（規格待決 7）：打擊骨架的附帶原語不能造表面、範圍骨架不能單體，先用燃燒 2 回合代替。要真的造火地得放寬骨架，是技能規則，請玩法 PM 決定。
2. **AI 的瞄準估值**：新加 `rewrite.lock_on_permille` 700（「現在就射出」的收益打七折）。結果和改之前的高處狙擊一樣：平地普攻比較划算、居高臨下才瞄準。雲鶴使先用鷹眼標記（2 AP）時剩 1 AP，放不了 2 AP 的瞄準。
3. **盾兵各多帶一招**：#149 一般敵人至少 2 招（工坊測試擋），持盾弟子加嘲諷吼（同盜賊盾衛）、熔殼甲兵加破城衝撞（同熔岩甲蟲）。
4. **玩家方 AI（隊友）不會把盾兵推開**：`expose`（把敵人推離掩護）只認掩護物件，沒有算盾兵；隊友照舊打。之後要的話是 AI 規則。
5. 瞄準招被沉默：定身符、熔岩彈是法術，沿用既有「法術型蓄力被沉默取消」；鶴唳穿雲是武器技，不吃沉默。

## 9. 需要使用者決定的事

- 規格第 6 節第 1 條（隊友擋在中間＝整發落空，還是改打擋住的人）、第 2 條（隱蔽不論距離都落空）、第 6 條（符籙師的強力一擊選定身符）——這三條會改玩家的手感，建議由玩法 PM 帶給使用者確認。
- 熔岩彈要不要真的造火地（上面待決 1）。

## 10. 平衡疑慮（沒量）

- 瞄準是「這回合付、下回合打」，弓手下回合還能普攻；輸出節奏和以前不同，可能更強也可能被應對到更弱。
- 盾兵不算遠程上限；雲海吊橋（遠程上限 1）加了「持盾弟子＋雲鶴使」，近戰 build 要繞路。
- 噴岩龜少了火牆（會移動的火區），換成單體高傷害；荒原的火地壓制變少。
- 熔殼甲兵 HP 48（最終）、護甲 5、火抗，近戰打起來可能很久。
