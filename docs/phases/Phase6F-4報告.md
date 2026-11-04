# Phase 6F-4 報告：新手前 10 分鐘（C1～C3、#128、#129、#130、#133 配點教學與葛蘭、6F-2b）

> 實作者：implementer agent（2026-11-04），**接手前一位停在中途的 WIP**（`a0eadaf2`，分支 `worktree-agent-a070af488925050e1`）。
> 基準：main `664f7339`（含 6V-1、6V-2、6H-1b、6E-W 調整）。因為 worktree 已經在 `664f7339`、和 WIP 分岔，`--ff-only` 不成立，改成 `git merge a0eadaf2`（沒有衝突；效果和「先 ff 到 WIP 再合 main」相同）。
> 分支 `worktree-agent-a39d71366b592a6df`，沒有 push、沒有合併回 main。
> 截圖：`docs/art/6f4_*`（無頭 Chrome `--mute-audio`、網址 `?mute=1`，自己的伺服器 8344、CDP 9344、自己的存檔資料夾，Mock LLM）。

## 0. 接手時的盤點

前一位改了 33 個檔，沒跑過 lint 和測試。逐檔讀過之後：

| 狀態 | 項目 |
|---|---|
| **做完（後端）** | C1 陣容（`bandit_rookie`、`bandit_archer_rookie`、AI 模式 `rookie`、渡口石階高度改成平台和石階底同高、遭遇表換成新手版）；C2（`StepReward.level_to`、`xp_to_level`、新手鏈三步 `level_to: 2／3／4`）；C3／#133 推薦配法（`recommended_allocation`、`recommended_level_up`、大世界建角 `allocation="recommended"`）；#128（`newcomer_guarded`）；#129（`starting_skill(prefer_uses=…)`、`links_between`、開局預覽的 `links`、`recommended`）；#130（第 1 步 mix 1／1／1、`_Maker.make_pair` 雙關鍵字橋接）；#133 內容（`newcomer.yaml` 的葛蘭台詞、屬性說明、升級畫面、`mentor_npc`；葛蘭人設卡與外觀資料；導師堂門口站位）；配點教學與升級畫面的 API（`LessonView.kind="allocate"`、`LevelUpView`）；6F-2b 提示紀錄的角色欄位與三個動作（`hint_seen`、`hints_off`、`hints_reset`，戰鬥中、待選時也能送）；`trpg-char/7`；`WORLD_RULES_VERSION` 9；6F-2b 四句定稿。 |
| **做一半** | 建角頁（`StartPicker` 的觸發關係、`WorldCharacterPicker` 的自動配點文字）做了，**世界畫面完全沒接**（配點教學面板、升級畫面、提示紀錄改用伺服器、「重新顯示提示」都沒有）；`schema.d.ts` 只生成了一部分（缺 hints、level_up、allocate）。停下時正在加的「preview 路由」就是 `/api/runs/start-preview` 的 `links`／`recommended`，已經寫完。 |
| **有問題** | 32 個既有測試失敗（版號、`trpg-char/6`、mix、NPC 數、地圖雜湊、HP 遷移表、掉落家族、聊天表沒有葛蘭、沒有 NPC 檔時 `mentor_npc` 檢查擋載入、`unitDolls.json` 過期）；新手三步的 `win_battle` 被加上 `group`（只算固定戰），這是規則改動、規格沒寫，見 2.1；`bandit_rookie` HP ×0.8 沒有模擬依據（實測 A、B 渡口勝率 90%）。 |
| **沒做** | C1 模擬腳本與摘要表、所有新測試、客戶端世界畫面、設定的「重新顯示提示」、`tests/api/conftest.py` 註解、致命地形文字和 05 的核對、OpenAPI 全量重生、報告與截圖。 |

## 1. 逐項做了什麼

| # | 項目 | 做法與結果 |
|---|---|---|
| 1 | **C1 渡口陣容** | `bandit_raiders`＝`bandit_rookie` ×2＋`bandit_archer_rookie` ×1。新手盜賊用 AI 模式 `rookie`（莽夫權重，但推撞、環境擊殺、利用地形全為 0）；弓手用護衛弓 `bow_guard`（1d6）。渡口石階中段平台改成和石階底同高（只有石階頂高 1），弓手不會站高處。用 `scripts/f4_newbie_sim.py` 掃 HP 倍率（×0.8／×0.7／×0.6），**定 ×0.6**：`bandit_rookie` 29→17（體質 12，最終 HP 23）、`bandit_archer_rookie` 31→19。結果見第 3 節：四種開局渡口 95～100%、主角倒下 5～15%；竹林、梯田 100%。 |
| 2 | **C2 升級** | 新手鏈三步完成時補到剛好 2、3、4 級（`level_to`：給的經驗＝下一級門檻 − 目前經驗，和 `xp_source` 取大的）。模擬裡三步打完的等級都是 2、3、4。升級畫面 `WorldView.level_up`（共用 `DialogFrame`）：「升到 2 級：屬性點 +2、靈感 +2。回霧渡鎮找導師堂的葛蘭，學怎麼配點。」——**靈感照規則顯示 +2**（見待決 1）。看過記在角色的 `level_seen`。 |
| 3 | **C3／#133 推薦配法** | 開局：兩招縮放屬性相同 → 4 點全給；不同 → 2／2（奇數多的給第 1 招）。升到 2 級：升級的 2 點給兩招中目前比較低的屬性，一樣高給第 1 招的。大世界建角一律照推薦配法自動配好；roguelite 原型不變（`allocation` 省略時照舊）。 |
| 4 | **#128 新手保護** | 新手任務鏈（`kind: starter`）的固定戰（`until_quest` 指到它的駐守）被敵人先看到時改成「沒有先手」（開打距離跟著沒有先手走，隔 3 格）；從背後碰到照樣我方先手；同圖其他巡邏、駐守照一般規則。**模擬 240 場固定戰，敵方先手 0 次**（全部是「沒有」，因為 BFS 走法都是正面走進視野）。 |
| 5 | **#129 起始協同** | 第 2 招優先挑「利用第 1 個關鍵字」的白板，白板沒有再看手寫池，都沒有照舊；不指定時亂數與結果完全不變。建角畫面在關鍵字下方標「觸發關係：水彈製造潮濕 → 導電連擊利用潮濕」，沒有時寫「這兩招沒有互相觸發……」。**實測：A（火焰法杖點燃＋帶電）、B（匕首冰凍＋隱蔽）、巨劍、弓 10 個種子都沒有觸發關係**；雷電法杖潮濕＋帶電 5／10 有（見待決 2）。 |
| 6 | **#130 第 1 步三選一** | 第 1 步 mix 1／1／1，第 2、3 步維持 1／0／2。橋接先試「同時帶持有最多的兩個關鍵字」：組合器對兩個關鍵字各試 `tries` 個主動白板種子，取第一張推導出的關鍵字同時含兩者的；沒有再看手寫池；都沒有照 6.27.4 放寬成只帶另一個。**可行解**：候選都是組合器實際做出、`validate_skill` 通過的技能（6E-W 的「至少一份合法解才出題」在這裡天生成立），測試逐張檢查 `validate_skill == []`，雙關鍵字橋接時檢查推導出的關鍵字真的含兩個。 |
| 7 | **#133 配點教學與葛蘭** | 葛蘭（`npcs/cloud_ridge.yaml`）：霧渡鎮導師堂駐堂導師，人設照 18.5；外觀只填 `portrait.look`／`gear`／`extras` 資料（藍紫外套金邊、鋼護手、短鬚、舊疤），**沒有改任何繪製程式**；站在導師堂門口 `[2, 12]`；聊天的傳聞與祕密兩句（暫定，見待決 4）。閃現、重閃的導師台詞改由葛蘭說。教學順序：升到 2 級、回到葛蘭所在的霧渡鎮、還有沒分配的點 → **先跳配點教學**（`AllocateLessonDialog`，共用 `DialogFrame`）：葛蘭兩句、「開局的 4 點已經照推薦配好，加上這次升級的 2 點，共 6 點」、這次的推薦配法、07 7.2 的範例（智力 14、力量 12）、「在城鎮或營火都能免費重配」、六個屬性滑過看白話說明（第 1 行「你的技能：…」由 `hero.attribute_affects` 帶入，用共用 `Hint`，沒用原生 `title=`）；按鈕「✦ 推薦配法」（送 `allocate`）、「自己配（成長面板 G）」、「之後再說」。教完或略過之後才跳 6F-2 的第一次閃現教學，最前面加一句葛蘭的「好。接下來看看你剛才用過的那一招。」（略過時是「隨時回來找我。」）。建角頁只顯示自動配好的結果：「屬性：智力 +4（照推薦配法自動配好）。之後導師會教你自己配。」 |
| 8 | **6F-2b** | 「只出一次」「不再顯示」改記在角色上：`CharacterState.hints_seen`（戰鬥短提示 ID、`opening`、`lesson:<種類>`）、`hints_off`、`level_seen`。客戶端拿掉 localStorage（`battleHints.ts`、`OpeningDialog.tsx`），開場、教學、升級畫面、戰鬥短提示都讀 `WorldView.hints`；戰鬥中出現或按「不再顯示提示」時送動作、不更新畫面（戰後同步一起回來）。設定（齒輪）加「提示」一區「重新顯示提示」（送 `hints_reset`；升級畫面的紀錄不清）。四句定稿已寫進 `newcomer.yaml`，測試逐字比對。**致命地形那句和 05 核對過**：05 5.5、`engine/triggers.py` 的 `entered_deadly_terrain`——非精英（主角、隊友都是）進入深淵、岩漿、冰窟直接致死，精英與 Boss 才改 30% 最大 HP 並傳回安全格；滑行不會自己滑進去（05 第 96 行）。「被推進去會直接倒下」一致。`tests/api/conftest.py` 的 `_old_spawn` 加註解：測試捷徑，正式開局照 #125 在主城出生。 |
| 9 | **版號** | 見第 2 節。 |

### 1.1 修掉的既有測試（因規則或內容改動而更新期望值）

`trpg-char/6 → /7`（7 處）、`WORLD_RULES_VERSION`、第 1 步 mix（`test_world_5b4b`、`test_offer_prefetch`、`test_quests`）、第 1 步經驗（300 → 補到 2 級的 950）、雲嶺 NPC 9 → 10、聊天表要涵蓋葛蘭、霧渡鎮規則雜湊（多了葛蘭站位）、渡口高度 {0,1,2} → {0,1}、HP 遷移表加兩個新手單位、掉落家族加兩個新手單位、`unitDolls.json`（`export_client_fixtures`）、紙娃娃指令流快照（只多兩個新單位，舊單位逐字不變）、`test_field_ctx_replay` 的比較拿掉三個新欄位（雜湊不變）。

### 1.2 檔案清單（相對 main `664f7339`）

- 後端：`src/trpg/roguelite/start.py`、`src/trpg/skillgen/whiteboard_candidates.py`、`src/trpg/world/{actions,field_enemies,growth,quests,save,state,step}.py`、`src/trpg/content/{library,world_newcomer,world_quests}.py`、`src/trpg/api/{world,world_newcomer_view,world_presenter,world_schemas,run_schemas}.py`、`src/trpg/api/routes/runs.py`
- 內容：`content/ai_profiles.yaml`、`content/units/bandit_rookie.yaml`（新）、`content/units/bandit_archer_rookie.yaml`（新）、`content/world/{encounters,npcs,quests,social}/cloud_ridge.yaml`、`content/world/fields/cloud_ridge/{ferry_steps,mist_ferry}.yaml`、`content/world/{newcomer,loot}.yaml`
- 客戶端：`client/src/world/{OpeningDialog,battleHints,WorldHud,WorldCharacterPicker}.tsx|ts`、`client/src/world/HintsSettingsSection.tsx`（新）、`client/src/ui/BattleHints.tsx`、`client/src/screens/WorldScreen.tsx`、`client/src/run/StartPicker.tsx`、`client/src/styles/{run,world-hud}.css`、`client/src/api/{types.ts,schema.d.ts}`、`client/openapi.json`、`client/src/render/fixtures/unitDolls.json`、`client/src/render/__snapshots__/inkDollSnapshot.test.ts.snap`
- 腳本：`scripts/f4_newbie_sim.py`（新）
- 測試：`tests/world/test_newcomer_6f4.py`（新，13 個）、`tests/api/test_newcomer_api_6f4.py`（新，4 個）、`tests/world/test_quests.py`（第 1 步改 1／1／1＋可行解、第 2 步 1／0／2 新增）、其餘見 1.1
- 截圖：`docs/art/6f4_*.png`（7 張）

**沒碰**：`client/src/render/` 的繪製與頭像部件（只動了 fixtures JSON 與快照）、`src/trpg/llm`、`content/llm`、世界 HUD 的彈窗與鏡頭（配點教學、升級畫面都用共用 `DialogFrame`；`WorldHud.tsx` 只多一個可選 prop 傳「重新顯示提示」進齒輪面板）、主城廣場、公告板、室內。

## 2. 版號

- **`WORLD_RULES_VERSION` 8 → 9**（`save.py` 文件字串補第 9 條，並把它排到第 8 條後面）：#128 新手保護改了開打先手與距離（同樣的走路日誌開出不同戰場）；`level_to` 改了完成一步給的經驗；三個只記紀錄的動作在戰鬥中、待選時也能做。
- **`CHAR_FORMAT` `trpg-char/6` → `/7`**：多了 `hints_seen`、`hints_off`、`level_seen`；`/1`～`/6` 照讀，舊角色的 `level_seen` 補成目前等級（不跳舊的升級畫面）。
- **wlog 照慣例不變**（`trpg-wlog/7`；6C-R3 起靠日誌標頭的規則鍵標成「規則已變、不能重播」）。
- API 有新欄位與新動作，已跑 `scripts/export_openapi.py` 與 `gen:api`；`test_openapi_snapshot` 通過。

## 3. 模擬摘要（`scripts/f4_newbie_sim.py`，每種開局 20 場）

流程：在暫存資料夾建新角色（跳過主城那段）→ 接新手任務 → BFS 一次走一格，到下一張圖、走進固定戰那一隊的視野（盡量避開其他隊的視野，碰到照打）→ 效用 AI 代打主角 → `fight` → 三選一跳過。輸了就停。世界種子每次隨機，數字有 ±1～2 場的雜訊。

**調 HP（只打渡口）**

| 倍率 | A 勝／倒 | B 勝／倒 | 巨劍 勝／倒 | 弓 勝／倒 |
|---|---|---|---|---|
| ×0.8（前一位） | 90%／25% | 90%／10% | 100%／0% | 95%／30% |
| ×0.7（20／22） | 95%／35% | 100%／5% | 100%／5% | 95%／10% |
| **×0.6（17／19，採用）** | 100%／10% | 100%／0% | 100%／5% | 100%／5% |

**採用值、三場全打（目前內容：任一場在該地點打贏都算完成那一步）**

SIM_FINAL

**試算：新手各步只算固定戰（`F4_FIXED_ONLY=1`，只改記憶體，見待決 3）**

SIM_FIXED

## 4. 測試

- Python：`tests/world`、`tests/api`、`tests/content`、`tests/roguelite`、`tests/skillgen` 全部（`-n 8`）：PYTEST_SUMMARY。新加 17 個（`test_newcomer_6f4.py` 13、`test_newcomer_api_6f4.py` 4），`test_quests.py` 改寫 1 個、新增 1 個。
- 每次 commit 前：`ruff check`、`ruff format --check`、`mypy src`（516 檔無錯）、`lint-imports`（13 個契約全過）、重播 `trpg battle --map swamp --seed 7` → `battle replay` 通過（88 個動作、313 個事件）。
- 客戶端：`vitest` 全部 228 檔、2494 個通過（紙娃娃快照只多兩個新單位）；`corepack pnpm -C client build` 通過（只有既有的 chunk 大小警告）。
- 沒跑 Python 全量。

## 5. 實機（截圖）

| 截圖 | 內容 |
|---|---|
| `6f4_create_A.png` | 建角：火焰法杖點燃＋帶電。觸發關係「這兩招沒有互相觸發」（灰），屬性「智力 +4（照推薦配法自動配好）。之後導師會教你自己配。」 |
| `6f4_create_links.png` | 建角：雷電法杖潮濕＋帶電，「觸發關係：水彈製造潮濕 → 導電連擊利用潮濕」（金色標出） |
| `6f4_capital_opening.png` | 建好後在主城醒來，開場兩句＋定稿的「走到中央廣場的傳送陣，或按 M 選雲嶺的霧渡鎮」 |
| `6f4_level_up.png` | 打完渡口回霧渡鎮：升級畫面 |
| `6f4_gran_allocate.png` | 接著是葛蘭的配點教學（兩句、共 6 點、推薦智力 +2、範例、免費重配、六個屬性、三個按鈕） |
| `6f4_flash_after_allocate.png` | 按「推薦配法」後：智力 +2（法力上限 67 → 73），接第一次閃現教學，第一行是葛蘭的「好。接下來看看你剛才用過的那一招。」 |
| `6f4_settings_reset_hints.png` | 齒輪設定多了「提示｜重新顯示提示」；按了之後剛略過的閃現教學又出現 |

建角與教學都是從正式首頁「開始」用滑鼠事件操作；渡口那一場是伺服器停下時用同一套 `world_step`（腳本走路＋效用 AI 代打）推進，再重開伺服器接著看（畫面沒有自動戰鬥鈕）。滑過屬性的浮動說明用合成事件叫不出來，沒有截到。

## 6. noqa

- `src/trpg/api/world_newcomer_view.py`：`char.level < 2  # noqa: PLR2004 - 2 級＝第一次升級`（前一位加的；2 是規格裡的「升到 2 級」，抽常數反而難讀）。
- `scripts/f4_newbie_sim.py`：`len(sys.argv) > 2  # noqa: PLR2004`（命令列參數位置）。
- 沒有新的 `C901`／`PLR0912` 類 noqa。

## 7. 待 PM 決定

1. **升級畫面的靈感數字**：玩法 PM 稿寫「靈感 +1」，但規則（`world/rules.yaml` `insight_per_level: 2`、07「每升 1 級 2 點」）是 +2。畫面照規則顯示 +2（文字樣板 `{insight}` 從規則帶）。如果稿子的 +1 指的是「新手第 1 步給的 1 點」，可以改成另一種說法；要改數字就是規則類，回到使用者。
2. **#129 對 A、B 沒有效果**：起始白板是組合器的「單一效果」模式，不會產生「利用 X」的招；手寫起始池裡利用點燃的帶電招、利用冰凍的隱蔽招都沒有，所以照規格「池裡沒有照舊」，A、B、巨劍、弓 10 個種子都沒有觸發關係（建角畫面如實寫「沒有互相觸發」）。要讓 A、B 有協同，得讓起始白板能做出「利用第 1 個關鍵字」的變體，或在手寫池補招——兩者都是內容或組合器的範圍擴大，沒做。
3. **新手步驟要不要只算固定戰**：前一位把三步的 `win_battle` 加了 `group`（只有打贏固定戰才算），規格沒寫、屬規則，我先撤回（保守）。但模擬顯示目前在竹林、梯田打贏巡邏（`bandit_wolf_handler`、`sect_patrol`）也會完成那一步，固定戰隨之消失：三場全打的梯田固定戰只有 2～6 場真的打到（第 3 節），教學主題（反應與格擋）可能被跳過。內容已支援（`WinBattle.group`，5B-4b），決定要的話只改 `quests/cloud_ridge.yaml` 三行。試算見第 3 節第三張表。
4. **葛蘭的聊天兩句**（傳聞、祕密）是我暫定的；`tests/content/test_world_quests.py` 要求每個 NPC 都有這兩種。
5. **配點教學的「共 6 點」**：畫面用「開局 4 ＋這次升級的點」算，開局點數寫死成 4（和 `start_free_points` 一致）；之後若改開局點數要一起改。
6. **主角倒下**：渡口目標達成；竹林 10～17%、梯田 0～33%（場數少），規格只對渡口設上限。
7. **模擬的雜訊**：`create_app` 的世界種子每次隨機，同一組設定重跑會差 1～2 場；要完全可重現得讓腳本固定世界種子（需要改 API 層的建世界參數或在腳本裡先寫世界檔），沒做。
