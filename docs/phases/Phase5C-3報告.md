# Phase 5C-3 完成報告：預設傭兵、劇情夥伴阿岳與誓約

> 規格：`docs/phases/Phase5計畫.md` 第 24 節（本段新增）。分支 `worktree-agent-a06f68f440a38bf3d`。

## 1. 交付

| 項目 | 內容 | 主要檔案 |
|---|---|---|
| 規格 | 第 24 節「5C-3 詳細規格」（只根據已寫入的設計；沒寫的列代決） | `docs/phases/Phase5計畫.md` |
| 預設傭兵 | `mercenaries.yaml` `default_party: [merc_tiebi, merc_huichun]`；`new_character` 帶這 2 名（9.6.11 5C-2 代決），可在城鎮 `hire` 改成獨行 | `content/world/mercenaries.yaml`、`world_mercenaries.py`、`world/step.py`、`world/party.py` |
| 劇情夥伴 | `companions`（阿岳：`hunter_ayue`、底稿 `build_ranged`、打贏 +2／每天 +6）；任務 `companion` 欄位（新手鏈、主線第 1 章）；每個世界動作後 `sync_companions`：接任務加入、隊伍滿替掉第 2 名、任務都結束離隊並還原；夥伴在隊時 `hire` 上限少 1、玩家自己 `hire` 後不還原；出場排在傭兵、影子之後，照主角等級成長；帶阿岳打贏給好感度（5B-4d 的阿岳部分） | `world/companions.py`（新）、`world/battle.py`、`content/world/quests/cloud_ridge.yaml` |
| 誓約模板 | `content/world/oaths.yaml`：18.6 的 15 種（中文名、說明、參數中文名、選項中文名、判定、`bind`、模板 6 的 `difficulty_by`）；加成依難度查表、破誓 2 回合 | `content/world/oaths.yaml`、`world_oaths.py`、`content/statuses.yaml`（4 個狀態） |
| 引擎判定 | `trpg.engine.oaths`：`BattleSetup.oath`、`BattleState.oath`；開場掛加成、`Ctx.emit` 掛鉤看事件判定、結算收尾移除加成＋破誓 2 回合＋`oath_broken`；戰鬥結束判定「每場至少……」。`LOG_FORMAT` `/106` → `/107` | `engine/oaths.py`（新）、`setup.py`、`state.py`、`battle.py`、`turns.py`、`context.py`、`events.py`、`docs/phases/戰鬥紀錄格式變更.md` |
| 世界接線 | 開戰帶 `oath_setup`；戰後世界事件 `oath_broken`／`oath_kept`、`LastBattle.oath`／`oath_broken`；立誓佔 1 格被動（被動滿 3 招拒絕；有誓約時換技能、三選一、閃現照被動 −1） | `world/oaths.py`（新）、`world/growth.py`、`world/quests.py` |
| API／前端 | 誓約模板的說明、加成、判定時機、違反後果、佔被動欄位；參數下拉用中文；開場說明加誓約一句；隊伍面板顯示夥伴與「佔 1 個隊友位」、雇用上限少 1；新事件句子；建角說明改成預設帶鐵壁、回春；狀態圖示 4 個 | `api/world_growth_view.py`、`world_party_view.py`、`client/src/world/*`、`client/src/render/statusIcon.ts`、`client/openapi.json` |

## 2. 誓約模板摘要（18.6 → `oaths.yaml`）

| # | ID | 難度 | 判定 | 時機 |
|---|---|---|---|---|
| 1 | `oath_no_heal` | 中 | `forbid_skill_tag` [heal] | 戰鬥中（施放） |
| 2 | `oath_no_retreat` | 中 | `no_retreat` | 戰鬥中（主動移動每一步） |
| 3 | `oath_attack_each_turn` | 易 | `attack_each_turn` | 戰鬥中（回合結束） |
| 4 | `oath_hold_high_ground` | 難 | `end_turn_high`（高度 ≥ 1） | 戰鬥中（回合結束） |
| 5 | `oath_no_category`（技能類別：法術／武器技） | 中 | `forbid_skill_category` | 戰鬥中（施放） |
| 6 | `oath_melee_kills`（人數 1～2） | 易（1）／中（2） | `min_melee_kills` | **戰鬥結束** |
| 7 | `oath_no_items` | 易 | `forbid_skill_tag` [gear] | 戰鬥中（施放） |
| 8 | `oath_no_reactions` | 中 | `forbid_reaction` | 戰鬥中（反應發動） |
| 9 | `oath_one_element`（元素 9 種） | 難 | `damage_element_only` | 戰鬥中（造成傷害） |
| 10 | `oath_protect_allies` | 難 | `protect_allies`（召喚物不算） | 戰鬥中（隊友倒下） |
| 11 | `oath_still_first_turn` | 易 | `no_move_first_turn` | 戰鬥中（第 1 個回合主動移動） |
| 12 | `oath_apply_status`（狀態 10 種、次數 2～4） | 中 | `min_status_applied` | **戰鬥結束** |
| 13 | `oath_no_early_defense` | 中 | `forbid_skill_tag_until_hp` [defense, shield, guard]、500‰ | 戰鬥中（施放） |
| 14 | `oath_no_surface` | 中 | `end_turn_off_surface` | 戰鬥中（回合結束） |
| 15 | `oath_solo` | 難 | `solo` | 開場（有隊友就違反） |

加成（初值）：易 攻擊傷害 +5%、中 +10%、難 +15%（`oath_bonus_*`，neutral、不倒數、不能被驅散）。破誓 `oath_broken`：造成的攻擊傷害 −10%、受到的傷害 +10%，2 回合。

## 3. 違反判定方式

- 全部由引擎依 **戰鬥事件** 判定（`Ctx.emit` 的掛鉤，事件當下的戰鬥狀態），不擲骰、不讀時間；違反只記下，等該次結算收尾（`finish_resolution`）才移除加成、施加破誓、發 `oath_broken`，同一場只違反一次；重播逐位元相同（`/107`）。
- **戰鬥中能判的 13 種**：1、2、3、4、5、7、8、9、10、11、13、14、15（15 在開場判定）。
- **只能事後（戰鬥結束時）判的 2 種**：6（近戰擊殺數）、12（施加狀態次數）——戰鬥結束時發 `oath_broken`（`at_end`），沒有效果，只記在世界事件與最近一次戰鬥。
- 世界層從這場戰鬥的事件產生 `oath_broken`／`oath_kept`；誓約本身不解除（06 6.26「下一場恢復」）。
- 測試：`tests/engine/test_oaths.py`（每種戰鬥中判定的行為一致測試——自動對戰的事件裡第一個違反事件之後才有 `oath_broken`、加成移除、破誓 2 回合、只違反一次；兩種戰鬥結束判定；`solo`；沒有誓約時不變）。

## 4. 瀏覽器驗證紀錄

Claude_Browser；`.scratch_5c3/serve.py` 在 **8090** 提供 API＋`client/dist`、存檔 `.scratch_5c3/saves`；`TRPG_LLM_BASE_URL=http://127.0.0.1:9/v1`、`TRPG_LLM_GENERATE=false` 降級。

1. 經 API 建角色「阿霧」（火焰法杖）→ 首頁「進入大世界（測試）」→ 進入：隊伍面板「隊伍 3 人／阿霧 主角／鐵壁 盾衛・守護・1 級・打法 預設（守衛）／回春 醫者・輔助・1 級・打法 預設（支援）」。
2. 「霧渡新手路」按「接任務」：隊伍變成「阿霧／鐵壁／阿岳 獵戶・劇情夥伴」，下方「阿岳（霧渡新手路）跟著你，佔 1 個隊友位；任務結束後離隊」；紀錄「接下任務「霧渡新手路」。」「阿岳加入隊伍（替下回春）：劇情夥伴，任務結束後離隊。」
3. 「成長與技能」→ 誓約區：「誓約佔 1 格被動欄位（立誓後被動技能最多裝 2 招）。違反：本場加成移除＋〔破誓〕2 回合：造成的攻擊傷害 −10%、受到的傷害 +10%；下一場恢復…」；模板下拉 15 種（含難度）。選「只用某一種元素的技能造成傷害（難）」→ 顯示說明、「加成：〔誓約之力・難〕：造成的攻擊傷害 +15%」「戰鬥中判定：違反時立刻移除加成」、參數「元素：」下拉（物理、火焰、冰霜…中文）→ 選火焰 → 按「立誓」→「目前的誓約：只用某一種元素的技能造成傷害（難度 難・元素：火焰）」。
4. 在霧渡鎮與渡口石階來回走（以頁面 `fetch` 送 travel）到遇敵，重新整理：遇敵面板「我方：主角（開場 HP 40）＋鐵壁、阿岳」「誓約「只用某一種元素的技能造成傷害」：主角帶〔誓約之力・難〕：造成的攻擊傷害 +15%，違反就移除。」→ 按「開戰」：戰鬥畫面我方阿霧、鐵壁、阿岳；主角卡「狀態 誓約之力・難、護盾 11（2 回合）」，`/api/battles/{id}` 主角 `oath_bonus_hard`（`remaining: null`）。
5. 本段沒有新增浮動卡（誓約與隊伍的新說明都是面板內文字），沒有做 6.5.1 的滑進／捲動／釘住測試。
6. 結束時只停了自己開的伺服器（`TaskStop`）、關閉自己開的分頁。驗證後把建角說明「一開始獨行」改成「一開始帶系統傭兵鐵壁、回春」（`WorldCharacterPicker.tsx`，`npm run build` 重跑過）。

## 5. 用了 18 的哪些內容

18.5 阿岳（獵戶、劇情夥伴、主線第 1 章同行）、18.6 誓約模板 15 種、18.7.1 第 1 步「阿岳加入」、18.7.6 阿岳好感度 +2／每天 +6。

## 6. 代決（規格 24.12）

| # | 事項 | 代決 |
|---|---|---|
| 5C3-1 | 預設傭兵放哪 | `mercenaries.yaml` `default_party`（鐵壁＋回春） |
| 5C3-2 | 阿岳的 build | 18 只寫「獵戶」→ 最接近的 `build_ranged`（弓） |
| 5C3-3 | 阿岳跟哪些任務 | 新手鏈與主線第 1 章（18.5）；接任務時加入，兩個都結束才離隊 |
| 5C3-4 | 替掉誰、怎麼還原 | 滿員替掉出場順序第 2 名；離隊時有空位才還原；中途 `hire` 就不還原 |
| 5C3-5 | 阿岳好感度上限 | 每天（6 點刷新）累計 +6；只看打贏且隊伍有阿岳 |
| 5C3-6 | 加成與破誓數值 | 易 +5%／中 +10%／難 +15% 攻擊傷害；破誓 −10% 造成、+10% 受到，2 回合（初值） |
| 5C3-7 | 模板 6 難度 | N＝1 易、N＝2 中 |
| 5C3-8 | 「道具」 | 戰鬥中還沒有道具：先判「裝備給的技能」（`gear` 標籤）；5D 接上只改 content |
| 5C3-9 | 「防禦技能」 | `defense`、`shield`、`guard` 標籤 |
| 5C3-10 | 「反應」 | 自己發動任何反應就違反；不自動關掉反應設定 |
| 5C3-11 | 戰鬥結束才判的模板 | 只記錄，不另給懲罰 |
| 5C3-12 | 違反後 | 誓約不解除、下一場照樣有加成；一場只違反一次 |
| 5C3-13 | 被動欄位 | 被動已滿 3 招時拒絕立誓；有誓約時所有裝技能的地方照被動 −1 |
| 5C3-14 | `solo` | 開場有其他我方非召喚單位就違反 |
| 實作 | 「主動移動」「高處」「元素」 | 移動模式 walk／dash／leap／shadowstep；高度 ≥ 1；元素判定不算墜落、撞擊、推倒、致命地形、反噬 |
| 實作 | 沒有傭兵名單的內容資料夾 | 不檢查任務的 `companion`（夥伴不會加入）；沒有人設卡時不檢查夥伴的 NPC |

## 7. 待 PM 決定／待辦

1. **LLM 把玩家誓詞轉成模板**（06 6.26 安全流程）：API 照 5A-7 只收 `source: "menu"`；`OathProposal`／`oath_problems` 已可給 LLM 層用，轉換與「轉不出來時提議最接近的模板」待排。
2. **戰鬥畫面「會違反誓約的動作在按下前先警告」**（6.26 介面）沒做。
3. 戰鬥結束才判的違反（模板 6、12）目前只記錄——要不要把破誓帶到下一場？（6.26 說「下一場恢復」，所以先不帶）
4. 反應模板（8）是「發動就違反」還是「立誓後自動關掉反應」？
5. 數值（加成三檔、破誓）是初值，平衡階段再定。
6. 阿岳隊伍面板的打法顯示「預設」（`build_ranged` 沒設 `ai_profile`）；夥伴的打法設定沒開放。
7. 5B-4d 其他好感度來源（柳掌櫃、小蓮）未做。

## 8. 檢查

- `ruff check .`、`ruff format --check .`、`mypy`（1076 檔）、`lint-imports` 通過。
- `tests/world tests/content tests/api`、`tests/engine`、`tests/narrative`、`tests/skillgen/test_budget.py`、`tests/test_architecture.py` 通過；`tests/cli -m "slow or not slow" --timeout=3000` 見最後一次合併後的紀錄。
- `npx vitest run`、`npm run build` 通過。
- 既有測試照新規則改：新角色預設 2 名傭兵（`test_battle_setup`、`test_party`、`test_shadows`、`test_quests`、`test_world_party_api`、`test_world_events_api`）、真內容有誓約模板（`test_world_growth_api`、`test_oath`）、`/106` → `/107` 字串、狀態覆蓋允許清單與圖示數 101 → 105。


## 5C-3b：誓約補完與阿岳打法（玩法 PM 2026-11-03 決定）

`LOG_FORMAT` `/107` → `/108`（`docs/phases/戰鬥紀錄格式變更.md`）。

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 戰後才判出的違反帶到下一場 | 戰鬥結束才判的違反（每場近戰擊殺、每場施加狀態）→ `CharacterState.oath_broken_next`；下一場 `OathSetup.start_penalty_rounds`＝2，開場施加破誓 2 回合，**加成照常**。每打完一場重新判定；解除、重新立誓也清掉 | `world/oaths.py`（`oath_carries`）、`world/battle.py`、`world/state.py`、`engine/oaths.py`（`open_oath`） |
| 2 | 「不使用反應」自動關反應 | 開場把持有者所有反應規則設成 `off`（每條發 `reaction_mode_set`）；玩家自己再打開、之後觸發仍算違反（原判定不變）；模板說明加一句 | `engine/oaths.py`（`_turn_reactions_off`）、`content/world/oaths.yaml` |
| 3 | 按下前的違反警告 | 引擎 `oath_warning`：預覽模擬後誓約變成違反＝「會違反」，只有最多後果的模擬違反＝「可能會違反」，附原因與後果；`forbid_reaction` 打開反應設定直接警告。`PreviewOut.oath_warning`、`BattleResponse.oath_active`。前端：有誓約未違反時，主角動作送出前先問預覽，有警告就跳 `OathWarningDialog`（共用 `DialogFrame`） | `engine/oaths.py`、`engine/preview.py`、`api/schemas.py`、`client/src/battle/oathWarning.ts`、`client/src/ui/OathWarningDialog.tsx`、`useBattleActions.ts` |
| 4 | 阿岳遠程保持距離 | `companions` 新欄位 `ai_profile`，阿岳設 `archer`（弓手，`keep_distance`）；隊伍面板打法顯示弓手 | `content/world/mercenaries.yaml`、`world/companions.py`、`api/world_party_view.py` |

### 測試與瀏覽器實測
- `tests/engine/test_oaths.py`（開場破誓、自動關反應、重開後觸發才違反、警告與真實結算一致）、`tests/world/test_oath.py`、`tests/world/test_companions.py`、`tests/api/test_oath_warning.py`、vitest `oathWarning.test.ts`；OpenAPI 重產。
- Claude_Browser，後端 8110、1600×900：立「每回合至少攻擊一次」，開戰，主角按「結束回合」跳出誓約警告；取消後仍是主角回合；再按並「仍要執行」才結束。使用既有 `DialogFrame`，未做 800×600 與釘住／捲動測試。已停掉自己的伺服器。

### 待 PM 決定
1. 警告只在主角自己的動作送出時問；複製技能／複合技能第二段選目標、反應詢問（`prompt`）接受反應都不問。
2. 技能列按鈕上沒有預先標「會違反誓約」，只有按下後確認。
