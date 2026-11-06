# Phase 6F-4b 報告：#129 利用者白板、新手只算固定戰、葛蘭傳聞、配點教學點數、九轉回天

- 依據：6F-4 報告「待 PM 決定」2～5（玩法 PM 已決定）；追加：九轉回天改回原名（#126）、白板配方和手寫技能同名清單。
- 分支：worktree 分支（未 push、未合併）。基底 `9682ce4e`（含 6F-4、6L-1）。

## 1. 逐項做了什麼

| # | 項目 | 做法 |
|---|---|---|
| 1 | **#129 利用者白板** | 組合器自動生成「條件傷害」白板，不手寫池子（見 1.1）。起始第 2 招在一般白板沒有利用第 1 個關鍵字時，改出生成的利用者白板，再沒有才看手寫池。A、B 從 0／10 變 10／10 有觸發關係（第 2 節）。 |
| 2 | **新手三步只算固定戰** | `content/world/quests/cloud_ridge.yaml` 三步的 `win_battle` 各加 `group`（`bandit_raiders`、`mist_wolf_pack`、`terrace_clash`），只改內容。 |
| 3 | **葛蘭的傳聞** | `content/world/social/cloud_ridge.yaml` 的 `gran_rumor` 改成定稿：「他說源晶裂痕那邊的霧最近濃得不像天氣，「像有什麼在底下呼吸。」」。外層引號照同檔其他句子的寫法省略，內層改用「」。祕密照 6F-4 暫定版。 |
| 4 | **配點教學的點數從規則讀** | `LessonView` 多 `start_points`，值取 `roguelite.yaml` 的 `start_free_points`。`OpeningDialog` 改成「開局的 {start_points} 點……共 {start_points＋points} 點」，畫面不再寫死 4。已重產 `openapi.json`、`schema.d.ts`。 |
| 追加 1 | **九轉回天改回原名** | `skill_nine_turns_revival` 的 `name_zh` 改回「九轉回天」，id 不變，描述保留 6L-1 的中性版本。6L-1 跟著改名的程式註解、測試與 `sect_steward.yaml` 註解也一起改回。「雲嶺池專用」見 1.3。 |
| 追加 2 | **同名清單** | 只列出來、不改名，內容檢查也沒動（第 5 節）。 |
| 5 | **版號** | `WORLD_RULES_VERSION` 9 → 10，已補 docstring。roguelite 舊 run 不受影響（第 4 節）。 |

### 1.1 利用者白板的做法

- **內容**（`skill_composer.yaml` 的 `whiteboard.exploit`）：
  - 條件種類 `conditions: [target_has_status, target_on_surface]`。
  - 每個狀態或表面的用字，放在 `statuses`、`surfaces`：名稱前綴、說明用的對象、敘事。
  - 每種傷害元素的用字，放在 `carriers`：物理、火焰、雷電、冰霜、暗影。
- **生成**（新模組 `trpg.content.whiteboard_exploit.exploit_recipes`，純函式）：
  1. 從關鍵字推導表找出每一條這兩種條件的專屬利用規則，共 10 條：燃燒、火裡、油上、水中、冰凍、冰上、倒地、標記、中毒、毒液裡。
  2. 每一條配上每一種元素，做成一個配方：一段單體傷害，帶這個條件。
  3. 配方的 `keyword` 是元素製造的關鍵字（物理就用條件利用的那個），`uses` 是條件利用的關鍵字。
  4. 名稱是前綴加名詞，例：趁燃雷擊、碎凍影擊、涉水雷擊。都以「擊」結尾，所以武器版同名。
  5. 手寫配方已經有的同一組不再生成：順水重擊（物理＋水中）、趁勢補刀（物理＋倒地）。
  - 新增關鍵字或利用規則時只要補用字，不用改程式（守則 4）。
- **只在指定 `uses` 時才出**：`compose_whiteboard(..., uses=…)`，目前只有起始第 2 招會用。一般的升級、任務三選一不會抽到，所以原本的候選和亂數都不變（測試 `test_plain_whiteboards_never_use_generated_recipes`）。
- **驗證**（`whiteboard_check`）：
  - 原本只有潮濕、倒地、撞擊可以帶條件，現在多一種情形也可以：唯一的效果是傷害，條件是 `exploit.conditions` 的一種（`is_exploit`）。
  - 關鍵字數量：把條件拿掉後最多 1 個關鍵字，條件最多再帶 1 個。例：趁燃雷擊製造帶電、利用點燃。
  - 「兩個製造」照舊擋下（測試 `test_two_made_keywords_are_still_rejected`）。
  - 預算比例、形狀、費用的檢查都不變。
- **內容檢查**（`exploit_problems`，在 `load_library` 的同名檢查旁邊）：
  - 推導表的每個條件都要有用字。
  - 生成的配方不可和其他配方同名，id 不可重複。
  - `trpg content check` 通過。
- **6E-W witness**（`proposal_witness`）：
  - 原本的建構只看「效果」寫法，所以 B 的題目（冰凍＋隱蔽、傷害核心、近戰）找不到可行解。這招轉成提議其實能通過完整驗證。
  - 現在一般建構都不合格時，再試幾份條件傷害（`exploit_proposals`）。原本就找得到的題目結果不變，驗證也沒放寬。
  - A、B、雷法杖 30 招的題目都找得到可行解（測試 `test_starters_link_and_have_a_witness`）。

### 1.2 起始順序（`roguelite/start.py` 的 `starting_skill`）

1. 一般白板有利用第 1 個關鍵字的 → 用它。這和以前相同。
2. 沒有 → 用生成的利用者白板（`_exploit_starter`，獨立亂數 `fork("exploit")`）。
3. 再沒有 → 用手寫池裡利用它的。
4. 都沒有 → 照舊。

不傳 `prefer_uses` 時結果完全不變。第 1 招也不變。

### 1.3 九轉回天的「雲嶺池專用」

內容裡沒有「區域技能池」的欄位：技能只有 `enemy_only`，沒有 `region`。區域風格只影響 LLM 命名。

照最保守的做法：

- 改回名稱，在 YAML 檔頭加註「雲嶺池專用（#126）」。
- 技能池的歸屬不變：它仍是玩家技能，不是 `enemy_only`。

要真的限制在雲嶺，有兩種做法（待決 3）：

- 設 `enemy_only: true`：玩家完全拿不到，它本來就只在青霧執事身上。
- 新增區域欄位：要改 `player_skills` 和呼叫端。

## 2. 起始兩招的觸發關係（`scripts/f4b_starter_links.py`，種子 1～10）

「前」是關掉 `whiteboard.exploit`，等同 6F-4。

| 開局 | 前（6F-4） | 後（6F-4b） | 後的起始兩招（次數） |
|---|---|---|---|
| A 火焰法杖 點燃＋帶電 | 0/10 | **10/10** | 火球＋沾油雷擊 ×3、火焰爆＋趁燃雷擊 ×2、炎流＋踏焰雷擊 ×1、火焰爆＋踏焰雷擊 ×1 |
| B 匕首 冰凍＋隱蔽 | 0/10 | **10/10** | 冰錐＋履冰影擊 ×2、寒息＋碎凍影擊 ×2、寒息斬＋碎凍影擊 ×2、冰錐刺＋碎凍影擊 ×2 |
| 巨劍 倒地＋撞擊 | 0/10 | 0/10 | 絆擊＋乘勢重擊 ×3、趁勢補刀＋頂撞 ×3、絆擊＋頂撞 ×2、趁勢補刀＋乘勢重擊 ×2 |
| 弓 標記＋高處 | 0/10 | 0/10 | 烙印＋隆地 ×6、烙印擊＋隆地 ×4 |
| （參考）雷電法杖 潮濕＋帶電 | 5/10 | 5/10 | 順水重擊＋涉水雷擊 ×5、水彈＋涉水雷擊 ×5 |

- 巨劍、弓沒有變。撞擊、高處沒有「以傷害元素製造」的寫法，條件傷害做不出「利用倒地的撞擊招」或「利用標記的高處招」。
- 雷法杖的第 2 招從手寫的導電連擊換成白板「涉水雷擊」（照 #129「白板優先」）。有觸發關係的比例不變：第 1 招抽到順水重擊時，它是利用者，不製造潮濕。

## 3. 新手鏈模擬（`scripts/f4_newbie_sim.py 10`，目前內容：只算固定戰）

每種開局 10 個角色，三場依序打。先手欄是「敵方／沒有／我方」。

| 開局 | 地點 | 勝 | 主角倒下 | 先手 | 打完等級 | 路上其他戰 |
|---|---|---|---|---|---|---|
| A 火焰法杖 點燃＋帶電 | ferry_steps | 10/10（100%） | 0/10（0%） | 0/10/0 | 2 | 0 |
| A 火焰法杖 點燃＋帶電 | bamboo_path | 9/10（90%） | 5/10（50%） | 0/10/0 | 2、3 | 0 |
| A 火焰法杖 點燃＋帶電 | rain_terraces | 5/5（100%） | 3/5（60%） | 0/5/0 | 4 | 8 |
| B 匕首 冰凍＋隱蔽 | ferry_steps | 10/10（100%） | 0/10（0%） | 0/10/0 | 2 | 0 |
| B 匕首 冰凍＋隱蔽 | bamboo_path | 10/10（100%） | 2/10（20%） | 0/10/0 | 3 | 0 |
| B 匕首 冰凍＋隱蔽 | rain_terraces | 5/5（100%） | 4/5（80%） | 0/5/0 | 4 | 8 |
| 近戰 巨劍 倒地＋撞擊 | ferry_steps | 10/10（100%） | 1/10（10%） | 0/10/0 | 2 | 0 |
| 近戰 巨劍 倒地＋撞擊 | bamboo_path | 10/10（100%） | 1/10（10%） | 0/10/0 | 3 | 0 |
| 近戰 巨劍 倒地＋撞擊 | rain_terraces | 7/7（100%） | 4/7（57%） | 0/7/0 | 4 | 6 |
| 遠程 弓 標記＋高處 | ferry_steps | 9/10（90%） | 1/10（10%） | 0/10/0 | 1、2 | 0 |
| 遠程 弓 標記＋高處 | bamboo_path | 9/9（100%） | 1/9（11%） | 0/9/0 | 3 | 1 |
| 遠程 弓 標記＋高處 | rain_terraces | 5/5（100%） | 0/5（0%） | 0/5/0 | 4 | 7 |

- **每一步都打到固定戰**：
  - 渡口、竹林的固定戰打到 9～10／10。弓有 1 人在渡口就輸了。
  - 梯田的「勝」欄分母（5～7）就是打到 `terrace_clash` 的人數。
- **梯田沒打到的人都是輸在巡邏**：另跑一次診斷腳本（`scratchpad/f4c/diag.py`，只在本機），結果是這樣：
  - 沒打到梯田固定戰的角色，全都是在梯田路上輸給巡邏 `sect_patrol`，被送回霧渡鎮，這時任務停在第 2 步完成。
  - 打贏巡邏的角色，任務仍停在第 2 步，照樣得去打 `terrace_clash`。所以「打贏巡邏就完成那一步、固定戰消失」的情形不再發生。
- **和 6F-4 的試算比**（`F4_FIXED_ONLY=1`，20 場）：
  - 梯田打到的比例低一些：6F-4 是 75～80%，這次 50～70%。
  - 巨劍、弓的起始技能這次沒變，比例也一樣低，所以主要是場數少，加上世界種子隨機（6F-4 待決 7）。
  - 梯田巡邏偏強，主角倒下 0～80%，可另外排平衡；這次沒調數值。
- 敵方先手 0 次（#128 照舊）。

## 4. 版號

- **roguelite**：
  - 存檔裡存的是生成的技能定義（`run.generated_skills`）和目前的候選，戰鬥之間的存檔不會重算。
  - 戰鬥中的存檔因為內容雜湊變了，照既有規則捨棄那場、回到節點開頭（3W-R1）。
  - 一般三選一不抽生成的配方，所以之後的候選也不變。只有新開局的第 2 招會不同。
  - `SAVE_FORMAT` 不用升。
- **大世界**：`WORLD_RULES_VERSION` 9 → 10，docstring 已補 10 的說明。
  - 第 1 項改了程式（起始第 2 招、白板檢查），同樣的建角日誌會給出不同的起始技能。
  - 第 2 項是內容，內容 digest 本來就會變。
  - 兩者一起升，保守。
- **API**：`LessonView.start_points`（新欄位，預設 0），已跑 `export_openapi` 和 `gen:api`。

## 5. 白板配方和手寫技能同名（兩邊都會進大世界玩家池的）

條件：

- 手寫那邊：不是 `enemy_only`，不是傳說，不是形態，種類是主動、被動或反應，而且至少有一個專屬關鍵字。這些才會從大世界的手寫池補位（`whiteboard_candidates._from_pool`）。
- 白板那邊：配方在大世界的階級內出得到。

| 名稱 | 白板配方（關鍵字、最低階級） | 手寫技能（階級、稀有度、關鍵字） |
|---|---|---|
| 毒霧 | `venom_mist`（中毒，1 階，`max_tier: 1`） | `skill_venom_cloud`（2 階、稀有、中毒） |
| 連鎖閃電 | `chain_lightning`（帶電，3 階） | `skill_chain_lightning`（2 階、稀有、帶電） |
| 召喚元素之靈 | `summon_spirit`（召喚物，1 階） | `skill_summon_spirit`（1 階、稀有、召喚物） |
| 喚起骷髏 | `summon_skeleton`（召喚物，1 階） | `skill_raise_skeleton`（1 階、稀有、倒地／召喚物） |
| 召喚火靈 | `summon_fire`（點燃，2 階） | `skill_summon_fire_spirit`（1 階、稀有、點燃／召喚物） |
| 召喚冰靈 | `summon_ice`（冰凍，2 階） | `skill_summon_ice_spirit`（1 階、稀有、冰凍／召喚物） |
| 召喚雷靈 | `summon_thunder`（帶電，2 階） | `skill_summon_thunder_spirit`（1 階、稀有、帶電／召喚物） |
| 召喚水精 | `summon_sprite`（潮濕，2 階） | `skill_summon_water_sprite`（1 階、稀有、潮濕／召喚物） |
| 召喚戰狼 | `summon_wolf`（倒地，2 階） | `skill_summon_war_wolf`（1 階、稀有、倒地／召喚物） |
| 召喚石像 | `summon_golem`（撞擊，2 階） | `skill_summon_golem`（1 階、稀有、撞擊／召喚物） |

沒有列的 4 個是捕獸夾、回氣、回春（2 個配方）。手寫那邊沒有專屬關鍵字，大世界的手寫池補位不會挑到它們，只在原型和通用池用得到。生成的利用者白板沒有和手寫技能同名的。

## 6. 檔案清單

- 新增：
  - `src/trpg/content/whiteboard_exploit.py`
  - `scripts/f4b_starter_links.py`
  - `tests/skillgen/test_exploit_6f4b.py`
  - `docs/archive/phases/Phase6F-4b報告.md`
- 內容：
  - `content/skill_composer.yaml`（`whiteboard.exploit`）
  - `content/world/quests/cloud_ridge.yaml`（3 行 `group`）
  - `content/world/social/cloud_ridge.yaml`（葛蘭傳聞）
  - `content/skills/skill_nine_turns_revival.yaml`、`content/units/sect_steward.yaml`（註解）
- 程式：
  - `src/trpg/content/composer_rules.py`（`ExploitRules` 等、`WhiteboardRecipe.uses`）
  - `src/trpg/content/library.py`（內容檢查）
  - `src/trpg/skillgen/whiteboard.py`（`uses`）、`src/trpg/skillgen/whiteboard_check.py`（`is_exploit`）
  - `src/trpg/skillgen/proposal_witness.py`（`exploit_proposals`）
  - `src/trpg/roguelite/start.py`（`_exploit_starter`）
  - `src/trpg/api/world_schemas.py`、`src/trpg/api/world_newcomer_view.py`（`start_points`）
  - `src/trpg/world/save.py`（版號 10）
  - 註解改回九轉回天：`src/trpg/content/environment.py`、`src/trpg/engine/ai/composite.py`、`src/trpg/engine/ai/priority.py`
- 前端：
  - `client/src/world/OpeningDialog.tsx`（一行文字）
  - `client/openapi.json`、`client/src/api/schema.d.ts`（重產）
- 測試：
  - `tests/world/test_newcomer_6f4.py`：#129 的期待改成 A 有觸發、巨劍照舊；新增固定戰測試；`start_points`。
  - `tests/world/test_quests.py`：`_won` 在新手三個地點預設用固定戰陣容；真實戰鬥測試帶固定戰接觸。
  - `tests/api/test_world_events_api.py`：新手第一步的遭遇設成固定戰。
  - 改回九轉回天的名字：`tests/engine/test_boss_phases.py`、`tests/engine/test_mechanics_5am1.py`、`tests/content/test_skill_scaling.py`。

## 7. 測試

- Python（相關的，`-n 8`）：`tests/skillgen`、`tests/roguelite`、`tests/world`、`tests/content`、`tests/test_architecture.py`、`tests/engine/test_boss_phases.py`、`tests/engine/test_mechanics_5am1.py`，加上 11 個相關的 `tests/api` 檔。結果 **7906 通過、14 略過、0 失敗**。
  - 新增 `tests/skillgen/test_exploit_6f4b.py` 共 10 個測試。
  - `tests/world/test_newcomer_6f4.py` 新增 1 個測試。
- `trpg content check` 通過：641 個檔、392 個技能。

- client：vitest 236 個檔、2606 個測試全過；`corepack pnpm -C client build` 結束碼 0。
- 每次 commit 前：`ruff check`、`ruff format --check`、`mypy src`（522 檔）、`lint-imports`（13 個契約）都過；重播 `trpg battle --map swamp --seed 7` 驗證通過（88 個動作、313 個事件）。
- 沒跑 Python 全量（照指示）。

## 8. 待 PM 決定

1. **一般三選一要不要也出利用者白板**：目前只在起始第 2 招出（指定 `uses`），升級、任務三選一不抽，這是保守做法，候選不變。
   - 混進一般池的話：帶電池的主動配方會從 5 個多出約 10 個「X 雷擊」，原本的配方被稀釋。
   - #130 的橋接（`make_pair` 要兩個關鍵字）也可以先試 `uses`，目前組合器做不出雙關鍵字白板，只能退回手寫池。
   - 這兩項都會改大世界候選，要升版。
2. **關鍵字層級的觸發 ≠ 實際好配**：A 的「火球＋沾油雷擊」在關鍵字上算觸發（都屬點燃），但火球不造油。
   - 可以讓起始第 2 招優先挑「第 1 招實際會造出的狀態或表面」對應的條件，例：火球 → 趁燃。
   - 這要再定一條規則，沒做。
3. **九轉回天「雲嶺池專用」要怎麼落實**：目前只有註解標記，見 1.3。可以選 `enemy_only: true`，或新增區域欄位。
4. **巨劍、弓仍沒有觸發關係**：條件傷害做不出製造撞擊或高處的招。要讓它們有，得在手寫池補「利用倒地的撞擊招」「利用標記的高處招」，或讓利用者白板允許「推撞＋條件」這類兩效果，後者是規則。
5. **名稱用字**：生成的名稱前綴（趁燃、碎凍、踏焰、沾油、涉水、履冰、伏地、循印、乘毒、浸毒）和名詞（重擊、炎擊、雷擊、霜擊、影擊）是我暫定的，請玩法 PM 看。
   - 「伏地」「乘毒」都配物理時已被手寫配方取代，不會出現。
   - 「伏地」另外會配到其他元素，例「伏地雷擊」。
6. **witness 的條件傷害建構**會讓少數原本被判不可行的 LLM 題目變成可行。例：冰凍＋隱蔽、傷害核心。原本可行的題目不受影響。大世界目前不開 LLM，roguelite 的提議紀錄照舊記在日誌。
