# Phase RG-2 報告：陷阱痕跡、精英單挑、荒原狂戰士（引擎＋世界＋內容）

規格：`docs/phases/PhaseRG計畫.md` 第 2 節（RG-2）。依據 #162（05 5.7、06 6.3.1、09 9.6.6、18、19）；背景 `PhaseRG-1報告.md`（含開發 PM 裁定）。使用者核可排段：「兩題都排」。
基準：main `f49912db6`（worktree 開工時落後 main，先 fast-forward 才拿到 RG 規格與 KW-1）。KW-1 已合併，所以荒原狂戰士沒有拆成 RG-2b。
依使用者 11-13 指示沒有跑平衡模擬或量測；疑慮寫在第 9 節。沒動 `docs/design/`、`skill_keywords`、資源機制、既有技能內容、skillgen 程式；沒碰 KW-1b 在修的 4 個測試檔。

## 1. 做了什麼

**敵方陷阱的可疑痕跡**（05 5.7、06 6.3.1）

- `TrapState.traced_by`（看到痕跡的陣營，沒有時不輸出）；`traps.trace_traps`：**只對玩家方**（`Team.ALLY`，含召喚物）在移動抵達與回合開始時（和感知的 `detect_traps` 同兩處，接在它後面），曼哈頓 `core.trap_trace_radius`（新欄位，`core.yaml` 寫 2，開放工坊）格內、還沒揭露、還沒記過的敵方陷阱記成痕跡，發 `trap_traced`（只帶格子；事件過濾只給該陣營）。放陷阱當下的狐族靈覺那一處不接，放置那一刻不算痕跡。
- 看到就留著，直到觸發、過期、被揭露（`reveal_traps` 揭露時把該陣營從 `traced_by` 拿掉，改列在 `revealed_to`）。
- 痕跡不改可見性：路徑、AI、預覽照舊只看 `visible_traps`／`strip_hidden_traps`（我方 AI 不繞路、預覽不洩漏種類；敵方 AI 照舊看不到玩家的陷阱）。
- 視圖 `BattleView.trap_traces`（格子清單；沒有時 `null`，前端既有的測試夾具不用補欄位）。
- **看那一格一眼**：非玩家方放陷阱時緊接在 `trap_placed` 之後發 `trap_glance`（放置者、格子；所有人可見）。只是演出事件，不改面向、那一格不因此變成痕跡。
- 戰鬥紀錄句子：「？X 注意到 (x, y) 有可疑的痕跡」「X 朝 (x, y) 瞄了一眼」。

**精英單挑**（09 9.6.6）

- 內容：`FixedElite.duel`（沒填不輸出）。第一季 4 場：北坡狼王（`north_slope` 固定精英＋`north_wolf_king` 懸賞）、疤面（`scarface` 懸賞＋`scarface_rises` 遭遇變化）、熔爐督工「鍛疤」（`overseer_camp` 固定精英＋`furnace_overseer` 懸賞；盜賊隊長變體＋硬殼的，招式是劈砍、旋風腿、撕裂打擊與招架反擊，沒有補血）、熔核領主（`molten_lord` 懸賞）。
- 提出：`world/duel.py::offer_duel`，接在 `solutions.make_encounter` 最後（移動遇敵、實地接觸、情境物件、戰鬥解法都走它）；陣容排最前的精英帶 `duel` → `EncounterResult.duel = "offered"`（`EncounterLineup.duel` 標記，`roll_lineup` 從三種精英來源帶出）。不耗亂數。
- 新世界動作 `duel_choice {accept}`：只在 `offered` 時可送 → `accepted`／`declined`，發 `duel_chosen`。戰鬥中由 API 既有的「戰鬥進行中」擋下。**還沒選就開打＝拒絕**（`prepare_battle` 只認 `accepted`）。
- 接受：`prepare_battle` 的我方只有主角（傭兵、影子、劇情夥伴不上場），敵方只有精英本人（`PreparedBattle.fielded`：陣容其他成員與第三方不上場）；戰鬥中召出的召喚物照常；雙方獨狼自然成立。
- 獎勵：`PreparedBattle.lineup` 仍是整個陣容，經驗、金錢、精英首殺、懸賞、區域 Boss 保底、主手同大類照它算；掉材料的成員在單挑時照整個敵方陣容（`roll_loot(..., duel=True)`）。實測北坡狼王種子 0、1：一對一與全隊打贏後，角色存檔只有 HP、法力、耐力、技能用法統計、上一場的輪數不同，經驗、等級、靈感、精英首殺、金錢、任務幣、材料、裝備逐欄相同，世界事件除了輪數與剩餘血量也相同。
- 遇敵面板 `EncounterView.duel`、`duel_zh`（例「狂暴的霧狼要求一對一：接受＝只有你和它，拒絕＝照原本全隊打；兩邊獎勵一樣。」）；接受後 `enemies` 只列精英、`allies_zh` 寫「一對一，隊友在外面等」。世界事件句子「接受單挑：一對一，隊友在外面等。」「拒絕單挑：照原本全隊打。」
- 前端畫法（對話框）在 RG-3；API 欄位已加（`DuelChoiceAction` 進 `WorldActionRequest`），重產 `client/openapi.json`、`client/src/api/schema.d.ts`，`typecheck` 過。

**荒原狂戰士**（19.2.1；#161 的怒氣，KW-1 已合併）

- 新敵人 `ashen_berserker` 荒原狂戰士（人形、斧，HP 34（最終 46）、速度 5、護甲 2；初值照工坊）：`skill_seething_rage` 怒火中燒（既有被動：受傷 +1 怒氣、一點護盾）＋新招 `skill_berserker_fury_cleave` 狂怒劈砍（`enemy_only`；條件 `self_stack_at_least` 怒氣 4 層＝上限；×1300，花光怒氣每層 +20%，同怒氣爆發；2 AP、耐力 10、冷卻 1）。怒氣的累積照 KW-1 的機制（身上帶消耗怒氣的招，受傷自動 +1），沒有自己做資源機制。
- 遭遇：一般營地「斷崖幫運輸道路」（`gang_convoy_road`）加新陣容「運輸隊的狂戰士」（狂戰士＋盜賊＋斷崖幫火槍手），原陣容不動（權重 2:1:1）。
- 外觀先用盜賊的紙娃娃換配色（美術 PM 之後出圖）。重產 `unitDolls.json`、`skill_icons.json`，`inkDollSnapshot` 只多一行 `ashen_berserker`。

## 2. commit

| commit | 內容 |
|---|---|
| 43e878ed2 | 引擎：陷阱痕跡、看一眼、`LOG_FORMAT` `/121`、測試 |
| 4f026827a | 世界：精英單挑、`duel_choice`、一對一組場、獎勵、`WORLD_RULES_VERSION` 31、`CHAR_FORMAT` `/15`、OpenAPI 與前端型別、測試 |
| 52ae5b15b | 內容：荒原狂戰士與狂怒劈砍、遭遇表、計數與前端夾具同步、測試 |
| （見最後一個 commit） | CLI 快照 17 鍵、紀錄格式文件、上手筆記、本報告 |

## 3. 確定性：預測與實際

| 項目 | 預測 | 實際 |
|---|---|---|
| 不變比對（改前＝main `f49912db6` 未改動時跑一次存 JSON、改後再跑；8 張地圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，效用 AI、`max_rounds=30`，比整份事件、步驟、去掉內嵌規則包的最終狀態） | 地圖預設陣容沒有人會放陷阱（只有 `skill_bear_trap`、`skill_cinder_mine`、`skill_venom_pit` 三招陷阱，沒有任何敵人範本帶）、不用到新敵人，全部逐字相同；`ruleset_hash` 全變（`core` 多 `trap_trace_radius`、新增內容） | `battles=46 events=20499 different=0 ruleset_hash_changed=46` |
| CLI 快照（slow，24 鍵） | 7 場戰鬥鍵不變（陷阱型的 `build_trapper` 是我方放陷阱，不發痕跡也不發看一眼）；`skills_list` 與 `skills_show_all/00～15` 共 17 鍵變（新招 `skill_berserker_fury_cleave` 排在第 21 位、分片大小 413 招時仍 26，所以 16 片全部位移） | 失敗的正好是這 17 鍵，只重產這 17 鍵；之後 24 passed |
| 其他 slow（engine 的 5 個 slow 檔、`test_refactor_parity`、`test_leap_check`、`tests/cli`） | 不變（不用到陷阱痕跡；新招是 `enemy_only`，3W-R2 對照只看玩家技能） | `949 passed, 4 xfailed`，沒有要重產的 |
| 一場重播 `open_plain` 7 | 通過 | 「重播驗證通過：91 個動作、383 個事件，最終狀態一致（open_plain，種子 7）」 |
| 陷阱痕跡的性質測試（hypothesis） | 任意位置與半徑：只有玩家方、距離 ≤ 半徑時記痕跡；同輸入兩次逐字相同 | 通過 |
| 單挑的世界重播 | 「遭遇（提出）→ `duel_choice` → `fight`」的日誌重播出逐字相同的世界與角色 | 通過（`test_world_replay_of_a_duel_matches_live_play`） |
| 地圖規則雜湊 `RULE_HASHES` | 不變（沒動實地地圖） | 不變（`tests/content` 全過） |

## 4. 版號

| 版號 | 變更 | 原因 |
|---|---|---|
| `LOG_FORMAT` | `/120` → `/121` | `TrapState.traced_by`、新事件 `trap_traced`、`trap_glance`、新的結算規則（玩家方記痕跡）。同步 9 處寫死 `trpg-battle-log/121` 的測試（`tests/cli/` 6 個檔 7 處、`test_gear_g2.py`、`test_gear_g3a.py`）與 3 個 `endswith("/121")`（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`，都跑過、重播仍一致）。`docs/phases/戰鬥紀錄格式變更.md` 加 `/121` 一條。 |
| `WORLD_RULES_VERSION` | 30 → 31 | 新世界動作 `duel_choice`、遇敵時提出單挑、接受時組場改變、單挑時掉材料的成員改成整個陣容。同步 `tests/world/test_opening_stages.py::test_versions`、`tests/api/test_pr2a_range_practice.py`。`world/save.py` 常數下的清單加第 31 條。 |
| `CHAR_FORMAT` | `trpg-char/14` → `trpg-char/15` | `EncounterResult.duel` 在角色存檔裡（`pending_encounter`）。規格寫「在角色存檔裡就升」，照做；`None` 不輸出、`/14` 加進 `LEGACY_CHAR_FORMATS` 照讀。15 個測試檔的 `trpg-char/14` 字面一起換。 |
| `trpg-wlog` | 不變 | 動作 union 多一種（WP-1 的前例） |
| 地圖規則雜湊 | 不變 | 沒動實地地圖 |
| `SAVE_FORMAT` | 不變 | |

## 5. 改動的既有測試（都是內容增加或版號帶來的，斷言意義不變）

- 版號：上一節列的 `LOG_FORMAT`、`WORLD_RULES_VERSION`、`CHAR_FORMAT` 同步。
- `tests/api/tuning/test_rules_budget_bs1.py`：核心欄位多 `trap_trace_radius`。
- 新招與新敵人（上手筆記第 37 點那一串）：`test_con_hp.py` 的 `OLD_HP` 加 `ashen_berserker: 46`；`test_skill_scaling.py`、`test_skill_icon_art_qi2a.py` 412 → 413；`test_tuning_fields_nw2a.py`、`test_yaml_patch_nw2a.py` 技能檔 409 → 410；`test_enemy_only.py` 清單加狂怒劈砍；`test_coverage.py` 拿掉 `self_stack_at_least` 的「還沒有手寫技能」允許項（狂怒劈砍是第一招）。
- 前端：`qIconSkills.test.ts` 412 → 413、`qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE` 加一招、`inkDollSnapshot` 只多一行；重產 `unitDolls.json`、`skill_icons.json`、`openapi.json`、`schema.d.ts`。
- CLI 快照 17 鍵。

新增測試：`tests/engine/test_trap_traces_rg2.py`（14）、`tests/world/test_elite_duel_rg2.py`（25）、`tests/engine/test_ashen_berserker_rg2.py`（7）。

## 6. 檢查結束碼

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0（1590 個檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（674 個檔、413 個技能） |
| 直接相關 pytest（`tests/world`、`tests/api`、`tests/content`、`tests/narrative`、`tests/cli`、架構、`test_enemy_only`、engine 的陷阱／視圖／事件過濾／決定性／clone／重播／版號／KW-1／RG-1 相關檔與 3 個新檔，`-n 8`） | 1：6789 passed、1 skipped、**1 failed**——`tests/cli/test_llm_propose_cli.py::test_mock_n3_snapshot`，在 main `f49912db6`（未改動）上一樣失敗（KW-1 的四個關鍵字改了 Mock 提議的快照），是派工註明 KW-1b 在修、這段不碰的檔；其餘全過 |
| slow：CLI 快照 | 0（重產 17 鍵後 24 passed） |
| slow：engine 5 檔＋`test_refactor_parity`＋`test_leap_check`＋`tests/cli`（`-m slow -n 8`） | 0（949 passed、4 xfailed） |
| `trpg battle --map open_plain --seed 7` ＋ `battle replay` | 0、0 |
| 前端 `typecheck` | 0 |
| 前端 `vitest run`（全部，`--maxWorkers=4`） | 0（345 檔、4398 項） |

沒跑全量 `scripts/check.py`、沒跑模擬報表（守則 11）。

## 7. 待 PM 決定

規格第 6 節第 12、13 條照最保守做完：

1. **陷阱痕跡看到就留著**（規格 12）：走遠也不消失，直到觸發、過期、被揭露。
2. **單挑沒選就開打＝拒絕**（規格 13）：前端 RG-3 之前也能照常打。

實作中多出的（都照最保守）：

3. **看一眼不改面向**：`trap_glance` 只是事件，頭轉向那格是 RG-3 的畫面演出；引擎的面向影響背刺，不動。
4. **看一眼只在非玩家方放陷阱時發**（敵方、第三方）；玩家方放陷阱不發。
5. **痕跡的檢查點同感知**：移動抵達（含被推、傳送抵達）與回合開始；被強制移動到 2 格內也算。
6. **單挑在遇敵當下判定提出**（`make_encounter`），所以移動遇敵、實地接觸、情境物件、戰鬥解法都會提出；同一位精英在固定精英與懸賞兩處都標 `duel`（北坡狼王、鍛疤），疤面在懸賞與遭遇變化兩處都標。熔岩洞窟平常的「熔核領主的熔岩池」陣容裡，熔核領主是陣容成員而不是固定精英，不提單挑（只有懸賞那場提）。
7. **單挑時夥伴好感與影子借用照舊算**：「帶夥伴打贏」的好感、影子主人每天第一次被借用的任務幣，在一對一時夥伴和影子沒上場仍照給（照「兩邊獎勵完全一樣」）。另一種讀法是沒上場就不算。
8. **單挑時的增援與下一場修正**：情境判定的增援照加進陣容（影響獎勵、不上場），「增援已滿＝敵人先手」照算；下一場的 buff／debuff 照套在主角、照消耗；誓約照帶。
9. **第三方在單挑時不掉材料**（沒上場）。第一季 4 場單挑的陣容都沒有第三方，目前碰不到。
10. **`CHAR_FORMAT` 升到 `/15`**：規格要求；但 `duel` 是選填、`None` 不輸出，照 RR-1 的前例其實可以不升。
11. **狂戰士的強力一擊另做一招**（`skill_berserker_fury_cleave`，`enemy_only`，怒氣滿 4 層才能放），沒有直接用怒氣爆發（怒氣爆發 0 層也能放，做不出「滿了才打」）。放在「斷崖幫運輸道路」的新陣容（狂戰士＋盜賊＋火槍手）；設計只寫「一般營地」。
12. **`trap_trace_radius` 開放工坊**（同 RG-1 的盾兵懲罰）；`BattleView.trap_traces` 沒有痕跡時是 `null` 不是空陣列（避免前端 40 個測試夾具補必填欄位）。

## 8. 需要使用者決定的事

- 第 7 節第 7 條：一對一時，沒上場的夥伴好感、影子借用獎勵要不要照給（目前照給）。
- 第 7 節第 11 條：荒原狂戰士放在哪個營地、強力一擊的數值（初值 ×1300、滿 4 層每層 +20%）。數值照工坊。

## 9. 平衡疑慮（沒量）

- 精英單挑少了小怪，強 build 可能一律接受，精英巢穴變簡單（`平衡待查.md` 第 21 條 3 已列）。反過來，1 級主角獨自打北坡狼王（5 級、狂暴的）用效用 AI 代打 12 個種子只贏 2 場——單挑本來就是給打得贏的 build 選的。
- 狂戰士滿怒氣一擊 ×1300 再 +80%，加上怒火中燒每輪一點護盾；近戰 build 連續打它時容易吃到滿怒氣的一擊。
- 陷阱痕跡第一季碰不到（沒有會放陷阱的敵人）。
