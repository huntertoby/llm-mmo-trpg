# Phase LW-1 完成報告｜獨狼條件 `lone_wolf`（#156）引擎＋內容、碎晶之主 B「被定身時不能閃擊」

> 規格：沒有另寫計畫檔，以設計文件為準——`docs/玩法決定紀錄.md` #156（使用者：「獨狼B」「獨狼規則 是」）、`docs/design/06-技能.md` 6.37 與 6.3 條件清單、`docs/design/08-裝備.md` 8.21.6、`docs/design/09-世界與敘事.md` 9.6.9；碎晶之主 B 依 `docs/phases/PhaseBAL-21c報告.md` 第 6 節候選表 B 列。前端（隊伍面板提示、條件不成立標灰）是之後的 LW-2，本段不做。
> 基準：main `ce997e53`（TXT-1 之後）。
> 使用者 2026-11-13 新指示（開發 PM 轉達）：「都不用再量數值了 寫個可能有問題記在.md上就好了 平衡 之後再說 先做遊戲」。trapper × 30 在收到前已跑完，結果照樣列在第 4 節；平衡上的疑慮列在第 6 節，沒有另外量。

## 0. 依設計整理的規格要點

1. **判定**：開戰那一刻，單位的陣營除了自己沒有其他單位＝獨狼；**整場固定**（之後隊友倒下、離場不會變成獨狼，有單位加入也不會失去）。和誓約「單獨作戰」同一個判定。
2. **不算隊友**：自己的召喚物與分身、三方混戰的第三方。**算隊友**：系統傭兵、朋友的影子、劇情夥伴、其他玩家。
3. **影子被借出時一律不成立**（身邊一定有招募者）；賽季影子循環賽（單挑）照判定成立。
4. **通用條件，不是新關鍵字**：主動、被動、反應、裝備詞條、LLM 生成都能用；預算照帶條件的招算；08「獨自」條件詞條用同一個判定；可和誓約疊加；AI 不改。
5. **示範（初稿）**：孤狼撲擊（近戰單體、獨狼時多一段傷害）、無人掩護（遠程單體、獨狼時射程 +1、打出後隱蔽）、獨行者（被動：獨狼時造成傷害提高、受到傷害降低）、獨行的（詞條：獨狼時某一項屬性提高）。倍率交數值工坊。
6. **碎晶之主 B**：新增「施放者沒有某狀態」技能條件，只加在 `skill_rift_flicker`（含升階版），條件 `root`；**不**做「定身擋所有自身傳送」的通用規則；AI 被定身時改選別的招。

## 1. 做了什麼

**引擎**

- `src/trpg/engine/lone_wolf.py`（新）：`mark_lone_wolves(state)`——同陣營沒有其他**非召喚**單位就是獨狼。`begin_battle` 放好單位、開場狀態之前呼叫一次（`battle.py`），寫進 `UnitState.lone_wolf`（`state.py`；`exclude_if` 空值，`false` 不輸出；`clone()` 已加）。之後召喚、援軍、階段召喚出來的單位一律 `false`，既有單位的值不再變。
- 條件 `lone_wolf`、`self_lacks_status` 加進 `CASTER_CONDITIONS`（只看施放者）；`engine/skills/conditions.py::_caster_condition_met` 讀 `caster.lone_wolf`／`not caster.has_status(status)`。技能層級、效果層級、修正規則、被動觸發都走同一個函式。
- 08「獨自」詞條：`gear/core.py::_self_condition` 認 `lone_wolf`，`equipment.SELF_EVALUABLE_CONDITIONS` 加進去（防禦類條件數值可以用）。
- 誓約「單獨作戰」（`oaths.py`）改讀同一個旗標（原本自己數一次，結果相同）。

**內容 schema、驗證、LLM**

- `REQUIRED_CONDITIONS` 17 → 19；`content/skill_conditions.yaml` 加兩筆：`lone_wolf`（`harsh`、`rare`；初值，未經模擬）、`self_lacks_status`（參數 `status` 必填、`budget_permille: 1000`＝不打折、`enemy_only: true`）。
- `ConditionDef.enemy_only`（新，沒填不輸出）：非 `enemy_only` 技能用到就驗證失敗（`skills/problems.py::_enemy_only_condition_problems`，涵蓋技能、效果、第二段、修正規則與 `any_of`）；LLM 提議 schema 不列（`proposal/builder.py::_condition_union`）；技能工具選項標 `unavailable_zh`（`option_params.condition_choice`）。`lone_wolf` 照一般條件開放（LLM schema 自動多 `Condition_lone_wolf`）。
- 條件句：`lone_wolf`＝「獨狼（開戰時我方只有你）」；`self_lacks_status`＝「自身沒有狀態「定身」」（`conditions.py::_STATUS_TEXT`）。
- 隨機組合器（`skill_composer.yaml`）**沒有**加獨狼條件（加了會改所有種子的組合結果與 parity；列待決）。

**內容**

| 檔案 | 內容 | 預算 |
|---|---|---|
| `skills/skill_lone_wolf_pounce.yaml` 孤狼撲擊 | 近戰武器技、2 AP、耐力 8、冷卻 2；武器倍率 1000 ＋ 獨狼時再一段 1000 | 71.4% |
| `skills/skill_unguarded_shot.yaml` 無人掩護 | 遠程武器技、2 AP、耐力 10、冷卻 2；武器倍率 1400；獨狼時自己隱蔽 2 回合。**射程 +1 沒做**（沒有「條件成立時射程改變」的結構，待決） | 73.7%（倍率 1000 時 55.9% 過弱，取合格內最低的一階） |
| `skills/skill_lone_strider.yaml` 獨行者 | 被動、技能條件 `lone_wolf`、每個自己的回合開始給自己激昂（`magnitude_permille` 1100）＋護衛（1000），持續 2；用既有狀態（新狀態要先有 Q 版圖樣，見第 6 節） | 72.0%（兩個都 1000 時 68.6%） |
| `affixes.yaml` `affix_cond_lone_defense`「獨行的：獨狼時防禦 +{n}」 | 條件數值、身體／頭／手／腳、100～200‰；`item_gen.yaml` `conditional_rates: common`、**`held_back_affixes`（新欄位）暫不進產生器** | — |
| `skills/skill_rift_flicker.yaml` 界隙閃擊 | `condition: {type: self_lacks_status, status: root}`；升階版（`grow_enemy` 的 `_t3`）一起帶 | 95.2%（不變） |

- `ItemGenRules.held_back_affixes`（新）：`item_gen._fits`（掉落、傭兵、重骰）與 `world/crafting.py`（打造候選）都排除；物品與測試可以直接帶。原有清單為空，產生結果不變。
- 數值工坊：示範的倍率都落在既有的技能欄位（`effects[*].multiplier_permille`、`effects[*].duration`、`effects[*].magnitude_permille`，已寫值所以會展開）；`tuning_fields.yaml` 只改 `magnitude_permille` 的說明（加「數值型狀態的強度，例：獨行者」）。**條件本身的預算倍率（`skill_conditions.yaml` 的 `lone_wolf`）與詞條數值範圍沒有開**：要新的對象種類＋前端分頁，列待決。

**版號**：`LOG_FORMAT` `/117` → `/118`（`UnitState` 加欄位、新條件）；`docs/phases/戰鬥紀錄格式變更.md` 加一條；測試裡寫死的版號 10 處一起改。`git fetch` 後 origin/main 仍是 `/117`。`WORLD_RULES_VERSION` 不動（世界規則沒變；日誌規則鍵本來就含 `LOG_FORMAT`）。

**前端（只為了既有測試，不是 LW-2）**：名詞表快照 `glossary.json` 多兩個條件；`render/qIcon/parts.ts` 的 `COND` 加兩筆**暫代**（獨狼借「目標落單」、施放者沒有某狀態借「目標帶有狀態」，沒有新畫）；`qIconQi2d.test.ts` 加 `ADDED_PARTS` 與 3 招 `ADDED_AFTER_BASELINE`、`qIconSkills.test.ts` 條件 17 → 19、招數 404 → 407。

## 2. 測試

新增：

| 檔案 | 內容 |
|---|---|
| `tests/engine/test_lone_wolf_lw1.py` | 隊伍組合（獨行、敵人多寡、帶 1～2 名隊友、第三方不算）、敵方也適用、召喚物不算、整場固定（隊友倒下仍不成立）、序列化往返、不成立時 JSON 不帶鍵、條件句；孤狼撲擊獨狼時兩下／不成立一下、無人掩護獨狼時隱蔽、獨行者只在獨狼時回合開始掛激昂＋護衛（受傷倍率 < 1000）、獨行的詞條獨狼時防禦 +150‰／帶隊友 0 |
| `tests/engine/test_rift_flicker_root_lw1.py` | 條件與預算（`budget_permille` 1000）、升階版帶條件、被定身時不在 `legal_actions`、緩速／虛弱不擋、其他技能沒有這個條件（不是通用規則）、被定身時效用 AI 不選界隙閃擊 |
| `tests/world/test_lone_wolf_world_lw1.py` | 走 `prepare_battle`：獨行成立；帶傭兵不成立；帶朋友的影子時主角與影子都不成立 |
| `tests/skillgen/test_lone_wolf_skillgen_lw1.py` | LLM schema 有 `Condition_lone_wolf`、沒有 `Condition_self_lacks_status`；選項標不可選；玩家技能用 `self_lacks_status` 驗證失敗、界隙閃擊通過；三招示範通過驗證 |

改到的既有測試（都是登記處或寫死的數字，斷言不放寬）：`test_skill_scaling.py` 404 → 407、`test_equipment_content.py` 78 → 79 條詞條（白名單加一筆）、`test_tuning_fields_nw2a.py` 401 → 404 個技能檔、`test_coverage.py` `_POOL_ONLY` 加三招（`builds.yaml` 都帶隊友，不為示範改模擬範本）、`test_skill_icon_art_qi2a.py` 404 → 407、`test_proposal.py::test_hints_become_schema_descriptions`（`enemy_only` 條件改斷言**不在** schema）、`refactor_3wr2.json` 只**加**三招的 `complete`／`retier`（其他鍵沒動）、`skill_icons.json` 重產（多三招；界隙閃擊只多 `condition` 一欄，`art` 不變）。

## 3. 不變比對

腳本在 scratchpad（不進 repo）：地圖預設陣容、效用 AI、`max_rounds=30`；改前（`git archive` `ce997e53` 的 `src`＋`content`，`PYTHONPATH` 指過去）與改後各跑一次，逐場比對整份事件、步驟、最終狀態（含 `rng_state`）。**最終狀態去掉 `ruleset` 一鍵**：狀態 JSON 內嵌整個規則包，新增條件與技能一定改它（`ruleset_hash` 46／46 場都變，原因就是內容）。

- 8 張地圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖（含碎晶之主的 `rift_gate`）× 種子 3～12：**`battles=46 events=20499 different=0`**。
- 這 46 場沒有任何單位是獨狼（最終狀態沒有 `lone_wolf` 鍵），`rift_gate` 預設陣容的頭目沒進到放界隙閃擊的階段（`skill_rift_flicker` 施放 0 次），所以全部逐字相同；有差異的只有第 4 節的大世界頭目戰。

## 4. 碎晶之主 B：trapper × 30（收到「不用量數值」前已跑完）

走 BAL-21c 同一條真實路徑（`sim.boss_probe.character` → `prepare_battle`，種子 0～29，雙方效用 AI）；改前同上用 `ce997e53` 的 `src`＋`content`。改前的數字和 BAL-21c 報告第 6 節對得上（第 3 階段 13 次、12／13 帶定身、10 勝）。

| trapper 30 場 | 改前 | 改後 |
|---|---|---|
| 勝場 | 10 | 12（翻轉 2 場：種子 6、23 敗 → 勝；沒有勝 → 敗） |
| 進入第 3／第 4 階段 | 18／18 | 18／16 |
| 第 3 階段界隙閃擊（＝傳送次數） | 13 | 2 |
| **第 3 階段傳送時身上有定身** | **12／13** | **0／2** |
| 第 4 階段界隙閃擊（＝傳送） | 12 | 9 |
| 第 4 階段傳送時有定身 | 3／12 | 0／9 |
| 總輪數 | 513 | 502 |
| 逐場完全相同 | — | 17／30（沒進到被定身還想閃的場次） |

## 5. 檢查與結束碼

| 指令 | 結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1530 個檔） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| `uv run trpg content check` | 0（665 個檔、407 個技能） |
| `trpg battle --map open_plain --seed 7` ＋ `battle replay` | 0：重播驗證通過（91 個動作、383 個事件） |
| `pytest tests/api tests/cli tests/test_architecture.py -n 8` | 1：2 failed／1315 passed——`test_gear_api.py` 寫死詞條 78、`tuning/test_yaml_patch_nw2a.py` 寫死技能檔 401（各改成 79、404）；這兩檔重跑在下一列，0 |
| 相關 engine／world（`test_lone_wolf_lw1`、`test_rift_flicker_root_lw1`、`test_rift_flicker_bal21c`、`test_gear*`、`test_state_clone`、`test_determinism`、`test_skill_determinism`、`test_pending_serialization`、`test_runner_advance`、`test_ruleset_hash`、`test_skill_ai`、`test_boss_phases`、`test_enemy_skills_149`、`test_oaths`、`tests/world/test_lone_wolf_world_lw1`、`test_shadows`、`test_oath`、`test_enemy_ai_moves_149`、`test_shard_lord_first_phase`、`test_crafting`）＋ `tests/api/test_gear_api.py`、`tests/api/tuning/test_yaml_patch_nw2a.py` | 0：359 passed |
| `pytest tests/content tests/skillgen tests/narrative -n 8` | 0：7512 passed、14 skipped（第一次跑時一個 xdist 工作行程異常結束〔node down〕卡住，停掉重跑一次全過） |
| slow：`tests/skillgen/test_refactor_parity.py`、`test_proposal_l8.py`、`test_proposal.py`、`tests/cli/test_run_cli.py -m slow` | 0：910 passed（parity 只**加**了三招兩筆，其餘夾具沒重產；固定種子一輪不變） |
| `tests/cli/test_output_snapshots.py -m slow` | 改前 12 failed／12 passed；只重產那 12 鍵後 0 |
| `corepack pnpm -C client exec vitest run` | 0：326 檔、4239 passed |
| `corepack pnpm -C client typecheck` | 0 |

沒改 API，不必重產 openapi。沒跑 `scripts/check.py`。

**CLI 快照逐鍵說明**（`tests/cli/snapshots/cli_output_hashes.json`，重產 `-k` 只選這 12 鍵；7 個戰鬥鍵與 `skills_show_all/00～04` 不變）：

| 鍵 | 原因 |
|---|---|
| `skills_list` | 多三招（孤狼撲擊、無人掩護、獨行者） |
| `skills_show_all/05` | 分片照技能 ID 排序切 26 招一片：`skill_lone_strider`、`skill_lone_wolf_pounce` 插進這片，`skill_marrow_thorn`、`skill_mirror_cast` 移到下一片 |
| `skills_show_all/06`～`/12` | 前一片插入兩招造成的整片位移（每片進兩招、出兩招）；`/07` 另含 `skill_rift_flicker`，`skills show` 多一行「使用條件 自身沒有狀態「定身」」 |
| `skills_show_all/13` | `skill_unguarded_shot` 插進這片，加上位移（進三招、出三招） |
| `skills_show_all/14`、`/15` | 位移（`/15` 最後一片多三招） |

歸因的做法：scratchpad 的 `shards.py` 用「改後全部 ID」與「去掉三招的 ID」各切 16 片，列出成員不同或含界隙閃擊的片＝剛好 `05`～`15`，和實際失敗的 11 片相同。

## 6. 平衡疑慮（沒量，只列出）

1. **`lone_wolf` 是 `harsh`（預算倍率 0.6）**：獨行時整場都成立，等於帶條件的效果打六折就能常駐；對真的獨行的玩家可能太便宜。另一方面整場不帶隊友的代價很大（頭目照 3 人設計），所以也可能剛好。
2. **獨行者**用激昂（屬性 +2，幅度 1100）＋護衛（受傷 −30%）常駐：護衛 −30% 對單人很有感，可能偏強；「造成傷害提高」是靠屬性縮放間接提高，不是直接的倍率。
3. **無人掩護**沒有射程 +1，為了過預算把倍率拉到 1400：不獨行時也是一支 1.4 倍的遠程武器技，比同類「隱匿射擊」（1000 ＋ 隱蔽時 1300）在一般隊伍裡更好用。
4. **孤狼撲擊**獨狼時兩段各 1000（共 2 倍），預算只有 71.4%；帶隊友時只剩 1 倍、冷卻 2、耐力 8，偏弱。
5. **獨行的**詞條只能做成防禦 +10～20%（條件數值沒有「屬性」這一種）；成立率等級取 `common`（最貴），獨行時其實是 100% 成立。
6. **碎晶之主 B** 讓 trapper 勝場 10 → 12（30 場），頭目第 4 階段仍會閃；其他 build 沒量。帶控制（定身）的 build 對碎晶之主變得相對更好打。
7. 敵方單獨一名的戰鬥（頭目單獨出場、渡口的單隻 `bandit_rookie`）敵人也是獨狼；目前沒有敵人帶獨狼條件，之後給敵人加獨狼招要留意。

## 7. 待 PM 決定

1. **無人掩護的「獨狼時射程 +1」沒做**：技能結構沒有「條件成立時射程改變」；要做得加引擎（例：`shape.range_bonus` 帶條件）另排段。目前用「倍率 1400」補預算。
2. **獨行的詞條做成防禦**：設計是「某一項屬性提高」，條件數值只支援命中／傷害／防禦三種；要屬性加值需引擎（條件數值多一種 `attribute`）。
3. **獨行的詞條暫不進產生器**（`held_back_affixes`）：加進去會改所有固定種子的掉落、傭兵裝備與打造結果；何時排入、成立率等級（現 `common`）由 PM 定。
4. **數值工坊沒開條件的預算倍率**（`skill_conditions.yaml` 的 `lone_wolf` `harshness`／`budget_permille`）與詞條數值範圍：要新增對象種類與前端分頁（`TuningCategory`、清單分組），建議併入 LW-2 或 NW-3。示範三招的倍率已在現有技能欄位可調。
5. **獨行者用既有狀態**（激昂＋護衛），沒有新做「獨行」狀態：新狀態要美術先出 Q 版圖樣、`statusFit.json` 要真瀏覽器重量。若要專屬狀態請排美術。
6. **隨機組合器沒加獨狼條件**（`skill_composer.yaml` `self_conditions`）：加了會改閃現／白板的組合與 parity 夾具。LLM 提議已可用。
7. **「算隊友」的範圍**：目前是「開場同陣營的任何非召喚單位」，所以護送／守點戰開場就在我方的 NPC 單位也算隊友（獨狼不成立）。設計沒寫到這種單位，採保守解讀。
8. **敵方也適用**：判定不分陣營（頭目單獨開場時是獨狼）。設計寫「我方」，目前沒有敵人帶獨狼條件所以沒有實際影響；要限定我方再說。
9. **影子「一律不成立」靠自然判定**：借出的影子一定和招募者同陣營開場，所以不成立；沒有另加「影子旗標」。若之後出現影子單獨出戰的借用情境（不是循環賽），要再加明確旗標。
10. **前端 Q 版圖示的兩個條件是暫代**（借現有部件）：請美術 PM 出 `lone_wolf`（與 `self_lacks_status`，只給敵人專用招）的條件圖樣。

## 8. 新增的複雜度類 noqa

無。`content/skills/conditions.py::_single_condition_text` 原本會超過 `PLR0911`，改成查 `_STATUS_TEXT` 表，沒加 noqa。

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（無衝突）。合併後 ruff、format、mypy、lint-imports、trpg content check 0；tests/cli＋api＋content 4326 passed；CLI 快照 slow 24 passed。CLI 快照 12 鍵重產：agent 以腳本預測受影響鍵與實際失敗鍵完全一致（新增三招造成分片位移＋界隙閃擊多一行條件），接受。不變比對 46 場 different=0（排除內嵌規則包一鍵）。LOG_FORMAT /118。

設計細節的保守解讀（1 射程 +1 未做、2 詞條做成防禦、3 詞條暫不進產生器、7 護送 NPC 算隊友、8 不分陣營）轉玩法 PM 確認；4 工坊開條件倍率與詞條範圍：使用者已指示先做遊戲、平衡之後再說，記入待排不併 LW-2；5、10 暫代圖樣與專屬狀態轉美術 PM；6 隨機組合器不加：接受；9 影子借出靠一般判定：接受。平衡疑慮 7 點轉玩法 PM 記進 docs/design/平衡待查.md。
