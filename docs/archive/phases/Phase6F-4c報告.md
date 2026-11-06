# Phase 6F-4c 報告：利用者白板進一般三選一、第 2 招對上造得出來的、區域技能池、巨劍與弓的觸發招、改名、梯田巡邏

- 依據：6F-4b 報告「待 PM 決定」1～5（玩法 PM 已決定，都在已寫入規則的範圍內；06 6.34.1、6.27.3；#129、#130）。
- 分支：worktree 分支（未 push、未合併）。基底 `2ec6434d`（含 6F-4b、6L-2）。

## 1. 逐項做了什麼

| # | 項目 | 做法 |
|---|---|---|
| 1 | **利用者白板進一般三選一、#130 雙關鍵字橋接** | 見 1.1。預算、白板檢查、`validate_skill` 都沒放寬；witness 的既有建構不變。 |
| 2 | **第 2 招優先對上第 1 招造得出來的** | 新模組 `trpg.skillgen.exploit_match`（見 1.2）。A、B 的第 2 招全部對上（第 2 節）。 |
| 3 | **`pool_regions`** | `SkillDef.pool_regions`（選填，省略不輸出）。內容檢查：區域 ID 要在 `regions.yaml`、不可是空串列。大世界候選池依 `CandidateRequest.region`（6L-1／6L-2 傳進來的取得地點區域）過濾；`region` 為 `None`（roguelite、創角）照舊。九轉回天設 `[cloud_ridge]`，6F-4b 的註解已換掉；沒設 `enemy_only`。見 1.3。 |
| 4 | **巨劍、弓的手寫觸發招** | 4 招，每招單一效果（第 5 節）。都通過 `validate_skill`、`trpg content check`、witness。巨劍 0→5／10、弓 0→10／10 有觸發關係（第 2 節）。 |
| 5 | **名稱用字** | `skill_composer.yaml` 的 `exploit.statuses`／`surfaces`：履冰→踏冰、循印→追印、乘毒→趁毒。 |
| 6 | **梯田巡邏平衡** | 新陣容 `terrace_patrol`（2 名修士雜兵，拿掉劍客與補師），只用在雨中梯田（田埂巡邏駐守點、地點遭遇表）。`sect_patrol` 與單位數值都沒動。掃描見第 3 節。 |
| 7 | **10 個同名白板改名** | 第 5 節。召喚類一律用「喚出」前綴（照手寫卡面「喚出鷹隼」「喚出影魅」「喚出爆裂傀儡」的寫法）。 |
| 8 | **版號** | `WORLD_RULES_VERSION` 11 → 12，docstring 已補。roguelite 舊 run 不受影響（第 4 節）。API 型別沒變（`export_openapi` 重跑後 `openapi.json` 無差異，所以不用 `gen:api`）。 |
| 9 | **快照** | `tests/skillgen/fixtures/refactor_3wr2.json`、CLI 快照照檔頭重產，差異都是預期的（第 6 節）。另外加技能要重產的 `client/src/render/fixtures/skill_icons.json` 也重產了（`uv run python -m tests.narrative.icon_fixture`）。 |

### 1.1 利用者白板進一般三選一、#130 橋接

- `compose_whiteboard` 多兩個參數：
  - `exploit_uses`：沒指定 `uses` 時，`keyword` 的一般配方再混進「利用這些關鍵字」的利用者白板，只有主動。
  - `targets`：和 `uses` 一起用，只挑這些條件對象（第 2 項用）。
  - 兩個都省略時和以前完全相同（`test_plain_whiteboards_never_use_generated_recipes` 照舊通過）。
- 白板候選產生器（`whiteboard_candidates._Maker`）每張主動白板都傳 `exploit_uses`＝玩家持有的關鍵字。例：持有點燃時，帶電白板的配方池多了趁燃雷擊、踏焰雷擊、沾油雷擊。
- **#130 橋接**（`make_pair`）：先試利用者白板，一個關鍵字由傷害元素製造、另一個由條件利用，兩種順序都試；沒有再走原本的一般白板、手寫池。
  - 雙關鍵字白板只有主動，所以橋接先照種類比例擲骰（獨立的 `fork("kind/pair")`）。擲到被動、反應時不試雙關鍵字，照舊放寬成單一關鍵字。
  - 不擲的話橋接格幾乎都變主動，主動比例從 70% 變 82%，違反 07 7.6 的 70／20／10。`test_candidate_kinds_follow_the_70_20_10_ratio` 抓到，已修正。
- 一般三選一裡利用者白板的比例（`scratchpad` 試算，1 階、各 100 組種子）：

  | 開局（各持有 1 招） | 加深 | 橋接 | 新方向 | 橋接是雙關鍵字 |
  |---|---|---|---|---|
  | A 點燃＋帶電 | 37% | 80% | 22% | 65% |
  | B 冰凍＋隱蔽 | 44% | 79% | 7% | 65% |
  | 巨劍 倒地＋撞擊 | 41% | 0% | 5% | 65%（都是手寫池的踢滾、拖地摔） |

  加深格約 4 成是利用者白板：該關鍵字的物理和本元素條件傷害都算「利用持有的關鍵字」，數量和原本的配方差不多（待決 1）。

### 1.2 第 2 招對上第 1 招造得出來的（`exploit_match.made_targets`）

1. **效果直接施加的**：效果寫了 `status`（不是只對自己或友方）或 `surface`（造表面、區域）；另外 `exploit.effect_statuses` 列的原語也算（擊倒、衝擊波、推倒 → 倒地）。含第二段、變奏與 `then`。
2. **都沒有時看傷害元素**：`exploit.element_statuses`，火焰 → 燃燒、冰霜 → 冰凍、毒素 → 中毒。
   - 這是照玩法 PM 的例子「火球對應趁燃、不配沾油」寫的。**引擎裡火焰傷害本身不會施加燃燒**，所以這是設計上的對應，不是結算事實（待決 2）。
   - 對應表寫在內容裡，pydantic 檢查狀態都要有用字。

`starting_skill(..., first=第 1 招)`（`_pick_starters` 和建角預覽 `/start-preview` 都會傳）。第 2 招依序挑：

1. 一般白板利用第 1 個關鍵字、而且條件對得上。
2. 條件對得上的利用者白板，用新的亂數串流 `fork("exploit/made")`。
3. 利用它的一般白板（6F-4b 照舊）。
4. 任何利用它的利用者白板（6F-4b 照舊，`fork("exploit")`）。
5. 手寫池。

第 1 招什麼都造不出來時（例：順水重擊、雷擊），結果和 6F-4b 相同。

### 1.3 區域技能池

- `trpg.content.player_pool.in_region_pool(skill, region)` 用在三個地方：
  - 白板產生器的手寫池補位（`_from_pool`）；
  - 完整三選一的關鍵字池（`candidates._pool`）；
  - 通用池（`_general_pool`）。
- 大世界取得技能的兩個入口都帶區域：任務三選一 `char.region`、機遇 `trigger.region`。
- **注意**：九轉回天目前本來就進不了任何候選池。
  - 它沒有專屬關鍵字，所以不在關鍵字池。
  - 它有通用歸類（潮濕 × 治療），所以也不在通用池。
  - 這次的設定是預先擋住。以後它若進池，也只會在雲嶺出現（測試用別的技能暫時設 `pool_regions` 驗證過濾）。

## 2. 起始兩招的觸發關係（`scripts/f4c_starter_links.py`，種子 1～10）

- 「關鍵字」：6F-4b 的量法（`links_between`）。
- 「造得出」：有觸發關係，而且第 2 招的條件對象是第 1 招實際造得出來的；沒有條件對象的算對得上。
- 「前」是 `2ec6434d`（6F-4b＋6L-2）的程式與內容。

| 開局 | 前：關鍵字 | 前：造得出 | 後：關鍵字 | 後：造得出 | 後的起始兩招（次數） |
|---|---|---|---|---|---|
| A 火焰法杖 點燃＋帶電 | 10/10 | 5/10 | 10/10 | **10/10** | 火球＋趁燃雷擊 ×4、火焰爆＋趁燃雷擊 ×4、炎流＋趁燃雷擊 ×1、點燃＋趁燃雷擊 ×1 |
| B 匕首 冰凍＋隱蔽 | 10/10 | 3/10 | 10/10 | **10/10** | 寒息斬＋碎凍影擊 ×3、冰錐＋碎凍影擊 ×2、寒息＋碎凍影擊 ×2、冰錐刺＋碎凍影擊 ×2 |
| 巨劍 倒地＋撞擊 | 0/10 | 0/10 | **5/10** | **5/10** | 絆擊＋踢滾 ×4、趁勢補刀＋拖地摔 ×4、絆擊＋拖地摔 ×1、趁勢補刀＋踢滾 ×1 |
| 弓 標記＋高處 | 0/10 | 0/10 | **10/10** | **10/10** | 烙印＋臨高點殺 ×3、烙印擊＋居高追獵 ×3、烙印＋居高追獵 ×3、烙印擊＋臨高點殺 ×1 |
| （參考）雷電法杖 潮濕＋帶電 | 5/10 | 5/10 | 5/10 | 5/10 | 順水重擊＋涉水雷擊 ×5、水彈＋涉水雷擊 ×5 |

- A 前的 5 次不算數：火球＋沾油雷擊 ×3 之類，第 1 招不造油。B 前的 7 次也一樣，例：冰錐＋踏冰影擊，第 1 招不造冰面。
- 巨劍 5／10：第 2 招一律是踢滾或拖地摔，都利用倒地。但第 1 招有一半是**趁勢補刀**，它只利用倒地、不製造倒地，所以兩招接不起來（待決 3）。
- 雷法杖照舊：第 1 招是順水重擊時，它利用潮濕、不造水。

## 3. 梯田巡邏平衡掃描（`scripts/f4c_terrace_sweep.py`）

- 照 `f4_newbie_sim.py` 的玩法：每個角色先打完新手第 1、2 步，再從竹林小徑一路走到梯田固定戰。路上碰到的每一場都打（BFS、效用 AI 代打、三選一跳過）。
- 只在記憶體裡換掉梯田田埂巡邏那個駐守點的陣容。
- 分母是打到第 3 步的角色數。「倒下」是第 3 步路上（巡邏或固定戰）主角倒下過。

**第一輪**（每種開局 10 人，4 種開局）：

| 梯田巡邏陣容 | 倒下（≤40%） | 固定戰勝（≥80%） | 巡邏戰 | 輸給巡邏 |
|---|---|---|---|---|
| 原本 4 名（2 雜兵＋劍客＋補師） | 23/40（57%） | 25/40（62%） | 33 | 15 |
| 3 名：雜兵＋劍客＋補師 | 20/39（51%） | 32/39（82%） | 31 | 7 |
| 3 名：2 雜兵＋劍客 | 21/39（53%） | 35/39（89%） | 32 | 3 |
| 3 名：2 雜兵＋補師 | 12/40（30%） | 40/40（100%） | 31 | 0 |
| 2 名：雜兵＋劍客 | 10/36（27%） | 36/36（100%） | 23 | 0 |
| 2 名：雜兵＋補師 | 9/40（22%） | 40/40（100%） | 27 | 0 |
| 2 名：2 雜兵 | 7/39（17%） | 39/39（100%） | 25 | 0 |

**第二輪**（每種開局 20 人，只跑候選；另外拆開倒在哪一場、列最差的開局）：

| 梯田巡邏陣容 | 倒下（≤40%） | 倒在巡邏 | 倒在固定戰 | 最差開局倒下 | 固定戰勝（≥80%） | 巡邏戰 | 輸給巡邏 |
|---|---|---|---|---|---|---|---|
| 原本 4 名（2 雜兵＋劍客＋補師） | 50/78（64%） | 40 | 22 | 85% | 55/78（70%） | 58 | 22 |
| 3 名：2 雜兵＋補師 | 35/78（44%） | 14 | 32 | 57% | 77/78（98%） | 61 | 1 |
| 2 名：雜兵＋劍客 | 38/77（49%） | 16 | 31 | 63% | 75/77（97%） | 56 | 0 |
| 2 名：雜兵＋補師 | 23/73（31%） | 5 | 22 | 70% | 73/73（100%） | 56 | 0 |
| 2 名：2 雜兵 | 22/78（28%） | 3 | 22 | 42% | 78/78（100%） | 59 | 0 |

**選定**：`terrace_patrol` ＝ 2 名修士雜兵（拿掉劍客與補師）。
- 第一輪 10 人時「2 雜兵＋補師」看起來達標（30%），第二輪 20 人變成 44%，不達標。
- 第二輪裡合計達標（倒下 ≤ 40%、固定戰勝 ≥ 8/10）的只有「雜兵＋補師」（31%）和「2 雜兵」（28%）；後者最差的開局也只有 42%，所以選它。
- **目前內容的驗證**（`--current`，每種開局 20 人）：

| 梯田巡邏陣容 | 倒下（≤40%） | 倒在巡邏 | 倒在固定戰 | 最差開局倒下 | 固定戰勝（≥80%） | 巡邏戰 | 輸給巡邏 |
|---|---|---|---|---|---|---|---|
| A 火焰法杖 點燃＋帶電 | 10/20（50%） | 1 | 9 | 50% | 19/20（95%） | 15 | 0 |
| B 匕首 冰凍＋隱蔽 | 5/19（26%） | 0 | 5 | 26% | 18/19（94%） | 16 | 0 |
| 近戰 巨劍 倒地＋撞擊 | 8/20（40%） | 1 | 8 | 40% | 20/20（100%） | 14 | 0 |
| 遠程 弓 標記＋高處 | 3/20（15%） | 0 | 3 | 15% | 20/20（100%） | 14 | 0 |
| 合計 | 26/79（32%） | 2 | 25 | 50% | 77/79（97%） | 59 | 0 |

- 註：同一個陣容兩次量的結果差到 1～2 成。原因是大世界種子每次建世界都不同（6F-4 待決 7），角色數也少。
- 合計倒下 32%、固定戰勝 97%，達標。倒下幾乎都在固定戰 `terrace_clash`（三方戰，25／27），巡邏戰 59 場 0 敗。固定戰這次照指示沒動，A 單看開局仍 50%（待決 4）。

## 4. 版號

- **大世界**：`WORLD_RULES_VERSION` 11 → 12。
  - 第 1、2、3 項改了程式，同樣的建角日誌和任務三選一會給出不同的技能。
  - 第 4、6 項改了內容，內容 digest 本來就會變。
  - docstring 已補 12 的說明。
- **roguelite 舊 run 不受影響**：
  - 存檔存的是生成的技能定義（`run.generated_skills`）和目前的候選，戰鬥之間的存檔不會重算。
  - `pool_regions` 是選填欄位，省略時不輸出，所以舊 run 的技能序列化與雜湊不變。
  - roguelite 的請求不帶區域，`in_region_pool` 一律放行。
  - 之後的候選會不同（一般三選一混進利用者白板、橋接先試它），新開局的第 2 招也會不同。戰鬥中的存檔因為內容雜湊變了，照既有規則捨棄那場、回到節點開頭（3W-R1）。
  - 沒有 run 層級的重播；戰鬥重播 `trpg battle --map swamp --seed 7` 每次 commit 前都驗證通過（88 個動作、313 個事件）。
  - `SAVE_FORMAT` 不用升。
- **API**：型別沒變。`SkillDef` 多的欄位不在 API 型別裡，`export_openapi` 重跑後沒有差異。

## 5. 新招與新名（名稱都是暫定，請玩法 PM 確認）

**新的手寫觸發招**：

- 四招都是 1 階、稀有、主動、單一效果。
- 都不是白板：白板檢查不允許「製造＋利用」兩個關鍵字放在非傷害效果上，這次也沒放寬。所以它們放在手寫池，起始第 2 招在白板、利用者白板都沒有時才從這裡挑。

| ID | 名稱 | 池 | 效果 | 預算 |
|---|---|---|---|---|
| `skill_prone_kick` | 踢滾 | 撞擊（利用倒地） | 近戰武器技、AP 1：只推倒地的目標 2 格，撞擊傷害 3d6（預設 1d6） | 80% |
| `skill_prone_drag` | 拖地摔 | 撞擊（利用倒地） | 近戰武器技、AP 1、射程 2：只拉倒地的目標 2 格，撞擊傷害 4d6 | 82% |
| `skill_rng_high_mark_shot` | 居高追獵 | 高處（利用標記） | 遠程武器技：只能對被標記的目標用（技能條件），站得比它高時才有傷害（×2.2） | 74% |
| `skill_rng_high_point_kill` | 臨高點殺 | 高處（利用標記） | 遠程武器技：要站得比目標高才能用（技能條件），只傷被標記的目標（×2.2） | 74% |

- 高處的兩招要兩個條件：技能條件帶一個關鍵字、傷害條件帶另一個。單一效果裡，條件是唯一能同時帶「標記」和「高處」的寫法。
- **witness**：原本的建構找不到兩個條件的寫法，所以 `proposal_witness` 多一種建構 `condition_proposals`。
  - 一個關鍵字的利用條件放在傷害上，另一個放在技能的使用條件。
  - 只在原本的建構和 6F-4b 的條件傷害都找不到時才試，原本就有可行解的題目結果不變。
  - 驗證照舊走完整的 `evaluate_with_repair`，沒有放寬。

**改名**：

| 原名 | 新名（法術版／武器版） |
|---|---|
| 利用者前綴 履冰、循印、乘毒 | 踏冰、追印、趁毒（例：踏冰影擊、追印雷擊、趁毒炎擊） |
| 毒霧 `venom_mist` | 瘴氣／瘴氣斬 |
| 連鎖閃電 `chain_lightning` | 跳躍電弧／跳躍電弧擊 |
| 召喚元素之靈 `summon_spirit` | 喚出元素火花 |
| 喚起骷髏 `summon_skeleton` | 喚出骸骨僕從 |
| 召喚火靈 `summon_fire` | 喚出火苗精 |
| 召喚冰靈 `summon_ice` | 喚出霜晶精 |
| 召喚雷靈 `summon_thunder` | 喚出電光精 |
| 召喚水精 `summon_sprite` | 喚出水滴精 |
| 召喚戰狼 `summon_wolf` | 喚出幼狼 |
| 召喚石像 `summon_golem` | 喚出小石像 |

- 召喚類用「喚出」前綴。手寫卡面有「召喚〇」和「喚出〇」兩種寫法，「召喚〇」都是手寫技能自己的名字，所以白板改用「喚出」才不會撞名，也和玩法 PM 的例子「喚出火苗精」一致。
- 手寫技能的名字都沒動。改名後這 10 個白板不再和手寫技能同名（測試 `test_renamed_words`）。
- 另有一個修正型被動 `poison_exploit`「乘毒追擊」（3 階）不是利用者前綴，沒改。

## 6. 快照與夾具

- `refactor_3wr2.json`：
  - 新增 4 招的完整技能強度與升階雜湊。
  - 閃現對照取「ID 排序後等距約 40 招」，新技能讓取樣位置往後移，所以換了一批技能的閃現雜湊。兩邊都有的技能，雜湊全部相同。
  - 九轉回天的完整強度與升階雜湊變了：技能多了 `pool_regions` 欄位，序列化跟著變。
  - 其他都沒變。
- CLI 快照：只有 `skills_list` 和 `skills_show_all` 的第 07～15 段變了，都是技能清單多了 4 招。戰鬥、run 的快照都沒變。
- `skill_icons.json`：加技能後重產。

## 7. 檔案清單

- 新增：
  - `src/trpg/skillgen/exploit_match.py`
  - `content/skills/skill_prone_kick.yaml`、`skill_prone_drag.yaml`、`skill_rng_high_mark_shot.yaml`、`skill_rng_high_point_kill.yaml`
  - `scripts/f4c_starter_links.py`、`scripts/f4c_terrace_sweep.py`
  - `tests/skillgen/test_exploit_6f4c.py`
  - `docs/phases/Phase6F-4c報告.md`
- 內容：
  - `content/skill_composer.yaml`（前綴改字、10 個白板改名、`effect_statuses`、`element_statuses`、註解）
  - `content/skills/skill_nine_turns_revival.yaml`（`pool_regions`、註解）
  - `content/world/encounters/cloud_ridge.yaml`（`terrace_patrol`；雨中梯田的地點遭遇表改用它）
  - `content/world/fields/cloud_ridge/rain_terraces.yaml`（田埂巡邏改用 `terrace_patrol`）
- 程式：
  - `src/trpg/content/composer_rules.py`（`ExploitRules.effect_statuses`、`element_statuses`）
  - `src/trpg/content/skills/skill.py`（`pool_regions`）
  - `src/trpg/content/library.py`（`pool_region_problems`）
  - `src/trpg/content/player_pool.py`（`in_region_pool`）
  - `src/trpg/content/whiteboard_exploit.py`（快取、說明）
  - `src/trpg/skillgen/whiteboard.py`（`exploit_uses`、`targets`）
  - `src/trpg/skillgen/whiteboard_candidates.py`（混進利用者白板、橋接、區域）
  - `src/trpg/skillgen/candidates.py`（區域）
  - `src/trpg/skillgen/proposal_witness.py`（`condition_proposals`）
  - `src/trpg/roguelite/start.py`（`first`、`_linked_starter`）
  - `src/trpg/api/routes/runs.py`（建角預覽傳第 1 招）
  - `src/trpg/world/save.py`（版號 12）
- 測試與夾具：
  - `tests/skillgen/test_whiteboard_3w4.py`（橋接允許雙關鍵字）
  - `tests/skillgen/test_exploit_6f4b.py`（說明）
  - `tests/world/test_newcomer_6f4.py`（巨劍改成有觸發招）
  - `tests/content/test_coverage.py`（4 招列入由池給出的技能）
  - `tests/content/test_skill_scaling.py`（392 → 396）
  - `tests/content/test_cloud_fields.py`（梯田巡邏的接觸點）
  - `tests/skillgen/fixtures/refactor_3wr2.json`、`tests/cli/snapshots/cli_output_hashes.json`、`client/src/render/fixtures/skill_icons.json`

## 8. 測試

- Python（相關的，`UV_NO_SYNC=1`，`-n 7`）：`tests/skillgen`、`tests/roguelite`、`tests/world`、`tests/content`、`tests/test_architecture.py`、`tests/narrative/test_skill_icon.py`，加上 23 個相關的 `tests/api` 檔。結果 **8057 通過、14 略過、0 失敗**。梯田陣容最後一次調整後，`tests/content`、`tests/world` 再跑一次：3713 通過。
  - 新增 `tests/skillgen/test_exploit_6f4c.py` 共 20 個測試。
- 快照（一般模式，含 slow）：`tests/cli/test_output_snapshots.py`、`tests/skillgen/test_refactor_3wr2.py` 910 通過。
- `trpg content check` 通過：646 個檔、396 個技能。
- client：vitest 238 個檔、2640 個測試全過；`corepack pnpm -C client build` 結束碼 0。
- 每次 commit 前：`ruff check`、`ruff format --check`、`mypy src`（530 檔）、`lint-imports`（13 個契約）都過；重播 `trpg battle --map swamp --seed 7` 驗證通過（88 個動作、313 個事件）。
- 沒跑 Python 全量（照指示）。

## 9. 待 PM 決定

1. **一般三選一的利用者白板比例偏高**：加深格約 4 成、橋接格約 8 成是利用者白板（1.1 的表）。
   - 原因：照「利用持有的關鍵字」混進的配方，數量和原本的配方差不多。
   - 要降的話可以設權重（例：混進的配方合計只佔一份），這是原型數值，沒有先改。
2. **「元素對應的狀態」不是結算事實**：火球對應趁燃是照玩法 PM 的例子，寫在 `element_statuses`（火焰 → 燃燒、冰霜 → 冰凍、毒素 → 中毒）。引擎裡火焰、冰霜傷害本身不施加燃燒或冰凍。
   - 要不要讓「火焰傷害有機率點燃」之類的規則跟上，是規則類，沒動。
   - 雷電、暗影沒有對應，第 1 招是雷擊時第 2 招照 6F-4b。
3. **巨劍只有一半接得起來**：第 1 招（倒地池）有一半是趁勢補刀，它只利用倒地、不製造倒地。
   - 要全接起來，得讓「第 1 招優先挑製造者」。#129 只規定第 2 招，所以沒做。
   - 雷法杖的順水重擊也是同一種情形。
4. **梯田的倒下多半在固定戰**：巡邏減人後幾乎不再輸給巡邏，但三方固定戰 `terrace_clash` 還是有 2～3 成倒下，A 和巨劍較高。
   - 合計 32% 達標，但單看開局 A 是 50%、巨劍 40%；量測波動大（世界種子隨機，同一陣容 10 人與 20 人差到 1 成多）。
   - 「≤ 40%」若是要每種開局都達標，只改巡邏做不到（巡邏減到 2 名後，倒下 25／27 在固定戰）。
   - 要更穩的話，可以把固定戰的盜賊換成新手版 `bandit_rookie`（渡口用的）。這不在這次「只改巡邏」的範圍。
5. **新招名稱**：踢滾、拖地摔、居高追獵、臨高點殺，以及第 5 節的改名，都請玩法 PM 確認。
6. **witness 多了兩個條件的建構**（`condition_proposals`）：
   - 會讓少數原本被判不可行的題目變成可行，例：標記＋高處、傷害核心、遠程。原本可行的題目不受影響。
   - 大世界目前不開 LLM，roguelite 的提議紀錄照舊記在日誌。
7. **梯田的地點遭遇表也改用 `terrace_patrol`**：
   - 內容規則要求實地地圖的駐守陣容在該地點的遭遇表裡（`test_spawns_use_this_places_groups_and_walkable_patrols`），所以雨中梯田的地點遭遇表也從 `sect_patrol` 換成 `terrace_patrol`。
   - 影響：梯田的隨機遭遇與增援也變輕（增援的單位池不再有修士劍客、補師）。
   - `sect_patrol` 本身沒動，但現在正式內容沒有地方用它，只剩測試 `test_world_season` 拿它當「超過 4 名」的例子。要保留或刪除請決定。
