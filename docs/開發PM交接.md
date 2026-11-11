# 開發 PM 交接文件

> 給接手的 **開發 PM**（新對話中的 Claude）。最後更新：**2026-11-07**。**只讀本檔就能接手**；需要時再讀 `CLAUDE.md`、`docs/專案計畫.md`（總覽）與本檔指到的計畫檔。
> 現況一句話（2026-11-07）：**Q 版 QK-1～9 結案、整理提案大部分完成；全部已 push，暫停中等使用者 Windows 測試**。最新狀態與待排見 **3.1**（優先於下面各節）。

---

## 1. 你的角色與組織

- 2026-10-22 起的架構：**專案 PM** 對接使用者，底下有 **玩法 PM**（`docs/玩法PM交接.md`）、**開發 PM**（本檔）、**美術 PM**（`docs/美術PM交接.md`）。各 PM 以 `SendMessage` 互相傳話。
- 開發 PM 的工作：把玩法／美術／使用者的決定寫成階段規格（`docs/phases/`）、派實作 agent、驗收、合併、push、回報。**不要自己寫大量程式碼**，實作交給 agent；小修（幾行）可以自己做。
- 分工：玩法 PM 只改 `docs/玩法PM交接.md`、`docs/玩法決定紀錄.md`、`docs/design/`；美術 PM 在自己的分支改 `docs/art/`、`docs/美術PM交接.md`，**由開發 PM 併進 main**；開發 PM 改 `docs/phases/`、本檔、程式，以及 `docs/專案計畫.md` 的決定紀錄（使用者同意後）。
- 玩法決定的狀態：排入或完成時，改 `docs/玩法決定紀錄.md` **第 1 節索引那一列**（「已排入（階段 X）」→「✅ 已完成」；原話在 `docs/archive/玩法決定紀錄_1-138.md`）。
- 使用者（GitHub：huntertoby）是 **最終決策者**，不是工程師。**所有回覆一律用繁體中文**，精簡、有結論，用表格比較選項；設計問題先問，技術細節（架構、測試、數值初值、排程、拆段）可直接決定並簡短說明。**下載任何外部檔案前要使用者明確同意**（3-13 的 Kenney 已同意，之後已移除）。

## 2. 專案現況

> 2026-11-07 更新。已結案的報告都在 `docs/archive/phases/`（索引 `docs/archive/phases/README.md`）；計畫檔全部留在 `docs/phases/`，已結案的第 2 行有「本階段已結案」標記。

| 階段 | 狀態 | 規格／報告 |
|---|---|---|
| Phase 0、1（基礎建設；1A 戰鬥核心、1B 環境、1C 掩護） | ✅ | `Phase0計畫.md`、`Phase1計畫.md`、`Phase1C計畫.md` |
| Phase 2A～2H（技能資料、解譯器、預算、組合器、模擬器、補模板 A／B、冰凍與屬性連動、整理） | ✅ | `Phase2*計畫.md` |
| Phase 3 網頁＋roguelite（3-1～3-55）與 3C～3W 系列（3C／3D 補模板、3E 整理、3F 工坊與複合技、3G 裝備詞條、3H 屬性、3I 第二批武器、3J 形態、3K 戰後裝備、3R 種族、3S 側面紙娃娃、3T／3U 整理與試玩修正、3W 白板與閃現、C 畫風） | ✅；**3E-2、3E-3 未做**（`Phase3E計畫.md` 3.2，可穿插） | `Phase3計畫.md`、`Phase3<X>計畫.md`、`PhaseC畫風計畫.md`（第 0 節與各節末是驗收） |
| Phase 4 LLM 技能生成（4-L1～4-L11b） | ✅；4-L11 小待辦：閃現 `name_offer` 遊戲內命名未接（接時傳 `before`）、形態／規則修正技能的效果比對未納入一致性檢查 | `Phase4計畫.md`、`Phase4-LLM技能提議設計.md`、真模型樣本 `docs/phases/4-L9/` |
| Phase 5 大世界第一版（5A 地點與城鎮、5B 事件與故事線、5C 組隊與傭兵、5D 經濟、5E Discord 與帳號、5F 賽季與 Boss） | ✅ | `Phase5計畫.md`、`docs/部署說明.md` |
| 平衡 BAL-1～19g（含 PERF-1） | ✅（使用者 2026-10-31 取消「一輪勝率」目標） | `PhaseBAL計畫.md`（驗收在第 2 節末與第 4～12 節）、`docs/archive/phases/BAL-*報告.md` |
| Phase 6 可走動的大世界（#120）已結案系列：6S 安全、6A 去文字化與戰鬥 D 版、6B 銜接與霧渡鎮、6C 雲嶺、6D 荒原與主城、6E 霧牆／冰面／開打距離、6M 動畫、6N-1～10 動畫第二批、6H 打擊感、6L 提示詞語氣、6P 收尾小項、6Q 美術打磨、6V 主城 NPC 外觀、6F-1～19 試玩修正與格子碰撞（6F-19 美術通過）、RT-5 主城開場 | ✅ | `Phase6計畫.md`、收尾報告 `Phase6報告.md`；各段報告在 `docs/archive/phases/`（`Phase6F-19報告.md`、`Phase6F-ART1／1b報告.md` 留在 `docs/phases/`） |
| Phase 6 其餘系列：6T 交易（6T-1a～1d ✅；6T-2 交易所待排）、6R（6R-F、6R-P、6R-1、6R-2／2b ✅）、UI-E（E1～E4、E3b／E3c ✅）、RT-1～6 ✅、AU-1～3 ✅、PERF-2／3 ✅、UI-T1 ✅、Phase 7 前置 ✅、6F-20～22 ✅、MAP-1 ✅、HID-1（#144）✅、TR-1（#134 靶場開局）✅ | ✅（剩 HID-1b 等，見 3.1 第 3 點） | 報告 `docs/phases/Phase<段>報告.md` |
| Q 版重製 QK-1～9（＋各段 b／c 小修） | ✅（2026-11-07 美術全部結案） | 規格 `docs/art/QK移植需求.md`；報告 `docs/phases/PhaseQK-*報告.md`；檢查 `docs/art/QK-*檢查.md` |
| MAC-1 Mac 相容、MAC-2 LM Studio MLX 相容、LLM-1（1A／1B／1C） | ✅ | `PhaseMAC-1報告.md`、`PhaseMAC-2報告.md`、`PhaseLLM-1報告.md` |
| 整理提案：DOC-A、DOC-B、CODE-1～3、I8、R1a～R1e、R2、R3、R4 | ✅；R5、R6 待排 | `docs/phases/整理提案-程式.md`；各段 `Phase<段>報告.md` |

- 測試：**2026-11-07 全量 pytest 15349、vitest 3301**（Mac mini，`-n 4`；模型載著時不跑全量）。版號：`WORLD_RULES_VERSION` 22、`trpg-wlog/9`、`trpg-char/12`、world/4、`LOG_FORMAT` `trpg-battle-log/112`（舊紀錄與戰鬥中存檔無法讀取，已接受）。
- 內容：手寫技能約 390 檔（`content/skills/`，BAL-19 補 76 招）；模擬用 build 與白板主角在 `content/sim/builds.yaml`；戰鬥地圖 `content/maps/` 17 張（含靶場 `training_range`、Boss 圖 `bandit_lair`）；實地地圖 `content/world/fields/`（雲嶺 18、荒原 18、主城 1、室內 7，`Phase6報告.md`）。
- 主要指令（Mac：每個 shell 先 `export PATH="$HOME/.local/bin:$PATH"`）：`uv run trpg battle --map <id> --seed <n> [--log-json f]`、`uv run trpg battle replay f`、`uv run trpg map list`、`uv run trpg sim maps|matrix|skills|completion`、`uv run trpg skills list|budget|random`、`uv run trpg run new|auto|show`、`uv run trpg llm ping`、`uv run trpg serve --port <空埠>`（8000 是使用者的）；前端 `pnpm -C client build|test|typecheck|gen:api`。

## 3. 下一步

### 3.00 交接（2026-11-11，對話中斷後換新 session；最新，優先於 3.0、3.1）

> 使用者：「你們被中斷了 因為某些原因 然後我想要換session 請交接」。前一個 session 結束時，下面三段的 agent 都**沒有交件**，且已不在執行（換 session 後沒有完成通知）。PM id 換新後以專案 PM 的開場訊息為準。專案 PM 交接在 main `4e712b6c`。

1. **main**：`4e712b6c` 已 push。最後一次全量是 CB-1 合併後（pytest 15580、vitest 3386）；之後的 PR-1、OB-1 只跑了快速檢查，**接手後第一次合併要跑 `check.py --full`**。
2. **三段未完成的分支**（worktree 在 `.claude/worktrees/agent-<id>/`，被執行環境鎖住，不要 `-f -f` 硬拆）：

   | 段 | 分支 | 狀態 | 接手建議 |
   |---|---|---|---|
   | **CB-2d**（#149 收尾，規格 `PhaseCB-2d計畫.md`） | `worktree-agent-a3e10e808e675a882`，HEAD `03ab3c13` | 已 commit：換招（`shock_follow` → `skill_spark_chain`、`whirlwind` → `execute`）、`aim_hit_permille` 700、`magma_slug` 智力 8、種子與快照、**已 revert 減 1 人（`dd96a754`）並改梯田盜賊 HP −10%（`44f5575f`）**、已 merge main。**沒做**：revert 後的種子／快照重確認與測試重跑、trapper 補到 30 場、更新報告（`PhaseCB-2d報告.md` 還是減 1 人的舊結論，要改成 HP −10% 與倒下率，並註明 CB-2a 第 1 階段輪數更正：只算本體約第 5.4 輪、32 場 29 場進入） | 派收尾 agent 在這個分支做完上述三件，再合併、跑全量 |
   | **OB-2**（#150 三選一延後、正式選定、推薦、入門期不存影子，規格 `PhaseOB-2計畫.md`） | `worktree-agent-abbd5c1b1f5e033c9`，HEAD `29252e19` | **沒有任何 commit 或改動**，等於沒開始 | 依規格重派（基準用最新 main） |
   | **PR-1b**（#147 灌注／指揮算放招、主角進致命地形回位、裝備充能補滿，規格 `PhasePR-1b計畫.md`） | `worktree-agent-a131ac84f73fb7f0e`，HEAD `29252e19` | **沒有 commit，但有未 commit 的改動**：`engine/battle.py`、`practice.py`、`state.py`、`triggers.py`、`turns.py`、`tests/engine/test_practice_mode.py`（+271／−13），沒驗證過 | 派收尾 agent 在這個 worktree 檢查、補齊、commit、跑驗收（含「實戰不變」逐筆比對）；不確定就重派 |

3. **待排順序**：CB-2d 收尾 → OB-2、PR-1b → OB-3（重選、閃現 4 級限制、配點教學）、OB-4（戰鬥閘，可與 OB-2 平行）→ OB-5（前端；**順手**：鳥走路接攻擊略過落地／起飛、異形向正南／正北施放不翻面（人形不動），補拍 `1b`、`1c` 與鳥的連拍，見 `docs/art/CB-2b檢查.md`）→ OB-6（正式選定與重選畫面、台詞入檔、入門配備打第 1、2 步的小模擬，**含雨中梯田與竹林小徑重量**，超標先調 `terrace_patrol`）→ PR-2（#147 接線、出發後回靶場：工坊師傅加一項＋葛蘭畫面也能試打）→ 1 階技能平衡（遠程優先）。拆段與檔案清單：共用筆記 `盤點-150與147.md`（專案 PM 給的共用筆記資料夾）。
4. **小項**（不單獨開段，碰到時順手）：`badgeCapsule.test.ts` 拆檔（vitest wall 下限）；`damage_object` 是第 4 份傷害算式；預覽與結算的最低傷害來源分歧風險；建角與 roguelite 開局沒選出身時開始鈕只變灰、沒提示缺什麼；`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` 用隨機種子、基準就會機率性失敗（改固定種子）；`scripts/cb2a_sim.py` 把源晶柱 `surge` 算進第 1 階段；`environment.py` 的 `aim_hit_permille` schema 預設仍是 500。
5. **等別人**：
   - **2026-11-11 使用者四項決定**（專案 PM 轉達，累積到下一段順手處理）：① #148 示範招「按玩法pm決定」→ 玩法 PM 建議 B（換成不綁武器的招：近戰瞬步背刺＋先發制人、遠程淬毒箭＋燧石飛刃、法器不變）；玩法 PM 會來核對這 4 招是否真的不綁武器、不低於普攻，定案後排進 #150 入門招，**定案前入門招照舊從資料讀，不要寫死**。② 墨線小圖示改 Q 版「好」→ 等美術 PM 樣張過審再排段；美術開畫圖 agent 前會先對名額（合計最多 4 個）。③ 蓄力強招在隱蔽單位的預告「按玩法pm決定」→ 維持不遮，不用改。④ Mac 本機測試角色「測試」：「刪」→ **已決定刪除，下次在 Mac 上工作時執行**（只刪這一個角色；Windows 的 `saves/` 查過沒有這個角色）。
   - **美術 PM**：5 款異形第二種近戰片段在畫（之後一個審查 agent）；#150／#147 的 3 項樣張（選大類、出發後入口、測試模式版面）排在後面。
   - **#148 示範招定案（玩法 PM 2026-11-11，`docs/design/21` 21.5、決定紀錄 #148，main `4ec2ab3b`；使用者原話「按玩法pm決定」）— 待排，OB-2 合併後併進下一個 #150 段**：近戰 `skill_shadow_backstab`＋`skill_wild_blade`；遠程 `skill_rng_venom_arrow`＋`skill_oil_spark_throw`；法器不變。改 `content/world/newcomer.yaml` 的 demos 與註解、`tests/world/test_opening.py` 的 `DEMOS_148`；燧石飛刃示範卡片說明加「靶場的油桶打破會流出油」；加測試：示範招不得有 `weapon_only` 或綁武器、副手的條件。核對數字在共用筆記 `核對-148示範招B案.md`。PR-1b 報告第 5 節的 5 點，玩法 PM 同意照最保守做法。
   - **平衡待辦（玩法 PM 記的，現在不調）**：雙匕首上 2 AP 單擊招只有普攻的 0.5～0.7；瞬步背刺在普通木樁第二次起背後格被石柱占住只剩約 0.48；1 階遠程武器技沒有一招無條件 ≥ 普攻（玩法 PM 接受，不為此調）；`ruined_fort` 25%、霧鎖真人 91～95%（目標 70%）、門檻 8 後「瞄準」價值下降、雨中梯田暫時接受最差約 48%、trapper 打碎晶之主若 < 40%。
6. **Windows 注意**：GitHub 帳號已是 huntertoby，可以 push（不要動憑證設定）。建置在 `client` 內 `npx vite build`；`corepack pnpm -C client typecheck`；worktree 內 `uv sync --frozen --offline`、`corepack pnpm -C client install --frozen-lockfile --offline`；**不下載 pnpm 10（使用者沒同意）**。預覽埠不要用 8000（使用者）、8001（本機 LLM），也避開 8092。Agent 的 worktree 從 `origin/main` 分出，**派工前先 push 規格**。派工 prompt 加「涉及放寬既有規則或驗證的一律先回報」（CB-2d 曾自行放寬陣容下限）。改到技能池或內容的段，驗收要列 `tests/skillgen`、`tests/narrative`、`tests/roguelite`（CB-2a 曾漏）。

### 3.0 現況（2026-11-10，Windows；優先於 3.1）

> 第四組 PM（Windows）：專案 PM `local_1dc515fa-6fa4-4841-956e-bdff26ae2844`、玩法 PM `local_0a6fbf09-b1f7-4040-b5b4-98537b4efa82`、美術 PM `local_88eb1048-c8a4-4601-b42a-2b2e2664de37`。

1. **恢復順序（使用者「go」）**：① mypy＋測試省時 ✅ ② 傷害公式合一、`unit_downed` 鎖定 ✅ ③ HID-1b（規格 `PhaseHID-1b計畫.md`）④ #146、#148、#149（模擬排在 #149 之後一起跑；開段前請玩法 PM 附使用者原話確認 `hit_target` 的適用範圍；#149 加招前問美術 PM 動畫）⑤ #150（以 `docs/design/21` 21.5 為準，台詞由玩法 PM 補；#148 要先做）、再 #147 ⑥ 1 階技能平衡。`docs/部署說明.md` Windows 段穿插，**不下載 pnpm 10（使用者沒同意）**。其餘待排見 3.1 第 3 點。
2. **批次 1（PERF-4、PERF-4b、ENG-1）合併後全量**：pytest 15421 passed、501 秒（參考值 668 秒，負載不同）；vitest 3315 passed，平均約 50.6 秒（同條件改前 62.2 秒，約快 19%，盤點的 27～32 秒沒有重現）；mypy 0 錯誤。
3. **盤點結論與待決**：共用筆記 `盤點-總結與排序.md`。使用者預設：R7 等省時做完再看、R8／R9 不做、R10 Defender 不動。結構債 S4～S8 不單獨開段，改到時順手。
4. **累積的小項**：`badgeCapsule.test.ts` 拆檔（vitest 全量的 wall 下限）；`damage_object`（`effects/world.py`）是第 4 份傷害算式；預覽用 `core.min_damage_on_hit`、結算用 `effect.min_damage`，目前一致，若技能自訂 `min_damage` 會分歧；建角與 roguelite 開局沒選出身時按鈕只變灰，要提示缺什麼；`test_demo_balance` 的 xfail 全部 XPASS，是否移除待定；R3 快取上限 64、R5 `SCRYPT_N` 2**4 是初值。
   - **批次 2 完成（main 74225ed1）**：HID-1b、HID-1c（美術結案）、CB-1（#146、#148）、CB-2a（#149 補招與模擬，報告 `PhaseCB-2a報告.md`，待玩法 PM 審數值）、CB-2b、CB-2c（美術結案）。全量 pytest 15580、vitest 3386。
   - **下一個碰前端的段要順手做**（美術 PM，`docs/art/CB-2b檢查.md`）：① 移動後緊接同一隻鳥的攻擊，略過移動結尾的落地與攻擊開頭的起飛，補拍一組連拍；② 確認 `cb2c` `1b`、`1c` 蜥蜴孵化後朝向翻轉只是開發頁手寫狀態、實戰不會，結果回美術 PM。
   - **等美術 PM**：5 款異形（hound、feline、bear、boar、lizard）第二種近戰片段，招單已定，要通知它有 agent 名額就派畫圖。**等使用者**：#148 示範招的附帶效果綁武器，要保留加說明還是換招（玩法 PM 在問）。
   - **教訓**：實作者只跑規格列的目錄時，`tests/skillgen`、`tests/narrative`、`tests/roguelite` 的固定名單與 fixture 會漏；改到技能池或內容的段，規格要把這幾個目錄列進去。
5. **環境坑**：Agent 工具的 worktree 會從 `origin/main` 分出，派工前要先 push，否則 agent 拿不到規格。完成的 agent worktree 會被執行環境鎖住（lock reason: claude agent），不要用 `-f -f` 硬拆。slow 測試要用 `-m "not llm"` 配 `TRPG_FULL=1` 才會跑到。Python 用 `uv run`；worktree 內 `uv sync --frozen --offline`、`corepack pnpm -C client install --frozen-lockfile --offline`；建置 `npx vite build`。

### 3.1 現況（2026-11-07 收尾）

> 3.1 最新；3.2、3.3 是前兩次交接，只為了查脈絡。2026-11-06～11-07 的進度流水（原 3.1）在 `docs/archive/交接歷史-開發PM.md` 末段；更早的歷任小節也在那裡。
> PM id（第三組）：專案 PM `local_e92f686b-c8bd-4b4d-9e22-f0b23d3dc696`、玩法 PM `local_156847a7-c020-45da-84a7-8ced1469e490`、美術 PM `local_42bc346b-cc13-48da-b901-bb0d0b235c64`。美術 PM 的分支 `claude/art-pm-90ce85`（worktree `.claude/worktrees/art-pm-90ce85`）由開發 PM 併進 main；它常只在本機 commit、沒 push，合併時用本機分支。

1. **main 現況**：全部 push，工作樹乾淨，沒有在跑的開發 agent。最後一次全量（TR-1 合併後）：pytest 15349 過（唯一失敗已修：`CharacterState.opening` 補進季末政策 `b9678d36`）、vitest 3301、build、重播全過。版號：`CHAR_FORMAT` **`trpg-char/12`**（TR-1 加 `opening`，舊存檔一律當已完成開局）、`WORLD_RULES_VERSION` **22**、`trpg-wlog/9`、提示詞 `skill-proposal/14`、`storyteller/5`、`situation-check/4`、`flash-variation/5`。import-linter 14 條、複雜度 `noqa` 7 處。
2. **這兩天完成的段**（報告都在 `docs/phases/`，美術檢查在 `docs/art/*檢查.md`）：
   - 環境與 LLM：MAC-1、MAC-2、LLM-1（1A／1B／1C，結案：提議 prompt 回到改前結構）。
   - 整理提案（`docs/phases/整理提案-程式.md`）：文件 DOC-A／DOC-B；程式 CODE-1～3（I1～I7）、I8、R1a～R1e（拆 events、library、ai/utility、skillgen/proposal、BattleRenderer）、R2（測試檔改名）、R3（engine 無循環匯入）、R4（長函式）。剩 R5、R6。
   - Phase 6：6T-1d、UI-E3b／E3c、6R-2（＋6R-2b）、6R-1c、6F-20、6F-21（＋21b）、6F-22（＋22b）、MAP-1、RT-6（＋6b）、HID-1（#144）、TR-1（#134 靶場開局）。
   - **Q 版 QK-1～9 全部結案**（使用者「先讓q板完成」；規格 `docs/art/QK移植需求.md` 第 2 版＋更正 `fcacaa70`）：人物、10 族、裝備、武器、頭像、NPC、召喚物、形態、異形 16 款、頭目 2 位、動畫（含正背面五類攻擊、武器待機、分部件異形動畫）、戰場 ×1.15。
3. **暫停中＝待排（恢復時照順序；使用者 11-07：「跑中都跑完後 不要開新的…我要在windows上測試」）**：
   1. **HID-1b**（`docs/art/HID-1檢查.md`）：「？」與所有 HUD 畫在霧上（人物留霧下）；HP 條與「？」畫在攻擊紅框上；**玩法 PM 條件**：預告（`TelegraphChangeOut` 的 `before/after/amount/text`）對隱蔽且未揭露的單位不得帶出 HP／護盾／狀態（目前可能洩漏狀態到期，要查）；戰鬥主角卡左下「四角飾件」`runCase` 舊 FAIL（依種子出現）；補拍 4 張（1600 選「移動」一般敵人、隱蔽敵人；四角飾件 800、1600）。
   2. **`docs/部署說明.md` Windows 段改寫**（使用者 11-07 Windows 實測）：pnpm 12 在 Windows 全域與 `npx` 都裝不起來（「`...\pnpm\pnpm` 不是內部或外部命令」），`npm install` 報 `EUNSUPPORTEDPROTOCOL workspace:`；可行做法 `cd client; npx vite build`（相依自 10-20 沒變）；git `unknown write failure on standard output` 用 `git config --global core.pager ""`。**建議同段評估把 `client/package.json` 的 `packageManager` 從 `pnpm@12.14.0` 降到 Windows 可用的穩定版（例 pnpm 10.x）**：`pnpm-lock.yaml` 是 `lockfileVersion: '9.0'`，pnpm 9／10 都讀得懂；驗證要先下載 pnpm 10（**下載前要使用者同意**），在 Mac 與 Windows 各跑 `pnpm install --frozen-lockfile`、build、vitest 確認；`scripts/check.py`、`pnpm_command()` 的版本讀取跟著改。
   3. **外觀選單選項改頭像小圖＋郵寄寄件人 Q 版頭像**（美術 PM 併一小段；樣張 `docs/art/外觀變化方案.md` 第 4 節；寄件人要 API 多帶外觀）。
   4. **propose 第 9 題 collision** 每次 `keyword.required` 退回（0.25 段，等玩法 PM 一起看 collision 的 ways）。
   5. **R5**（tests 同名 helper 收斂，含 R2 合併時加前綴的 `_6f4_ok`／`LIB_48F` 等；bal／L／E／G 系列 56 個測試檔改名一併）、**R6**（client 測試 `as unknown as` → 型別化 fixture）。
   6. 其他小項：TR-1 待決 10 點（示範招 6 招、守印人台詞、木樁外觀等交玩法／美術 PM，`docs/phases/PhaseTR-1報告.md` 第 4 節）；人形倒下實機補拍（有人加 AI 代打選項時順手）；`build_proposal_models` 92 行；R1e 各層 `protected` 介面收窄；I8 驗收時在本機存檔建了測試角色「測試」（使用者決定是否清）。
4. **平衡與 LLM 的長期待辦**：原 3.3 平衡待辦核對後剩的列在 `docs/phases/PhaseDOC-B報告.md` 第 2 節（規則類 B-3W、B-3W-2 要回使用者；其餘是未單獨量測的初值與 AI 行為）；LLM 效能（E4B 每題約 14～17 秒、12B 約 59 秒）與「多講一點接線」、12B 基準等專案 PM 指示再排。
5. **開發入口**（QK-9b，只在開發模式＋`TRPG_DEV_ROUTES=1`、前端 `?dev=1`）：開場朝向 `&bossface=`、開場召喚物／形態 `&bossopen=summon|form`、傳送 `&tp=<region>`（`dev-teleport` 直接改角色存檔、不寫世界日誌，該角色之後的世界日誌重播會對不上，專案 PM 已轉知使用者、接受）。畫廊在 `client/dev/*-gallery.html`（I8 搬過）。
6. **環境**：見 §6.1（Mac）。Windows 測試指令見部署說明（待第 3.2 條改寫）。名額：開發同時 ≤ 3、全專案 ≤ 4，平行的 agent 不改同一批檔案；agent 一律帶 `model: "opus"`。

### 3.2 開發 PM 收尾（2026-11-05，使用者重開電腦前）

> （當時的 PM id 已失效，現行 id 見 3.1。）美術 PM 的文件分支由開發 PM 併進 main。
> 待排段的完整清單在 Windows 的共用筆記 `開發PM-待排段-1104.md`（這台拿不到；共用筆記資料夾由專案 PM 的開場訊息給，Mac：`~/Library/Application Support/Claude/side-session-notes/<專案 PM id>/`）。

1. **main 現況**：`2457e3f2` 之後只多了文件合併，全部已 push。最後一次全量（6R-1 合併後）：pytest 15197、vitest 3028、build、重播全過；之後 6T-1c、UI-E3 合併只跑前端與相關測試（vitest 3045）。版號：`WORLD_RULES_VERSION` **20**、`trpg-wlog/9`、`trpg-char/10`、world/4、`LOG_FORMAT` /112。
2. **這幾天上 main 的段**（報告都在 `docs/phases/`，美術檢查在 `docs/art/*檢查.md`（已結案段的在 `docs/archive/art/`））：
   - 6F-4g、6F-4h（起始協同：追印絆擊）— 玩法 PM 確認，6F-4 系列完成。
   - 6F-14～6F-19（格子碰撞：三角形避讓、有人站不畫 ▲N、「+N」膠囊）— **6F-19 美術通過，系列結案**。
   - RT-5、RT-5b～RT-5d（主城開場四格）— **RT-5d 美術通過，系列結案**。
   - 6T-1a（交易前置、郵寄伺服器、#135 掉落）、6T-1b（郵寄前端、別大類主手可換、過期信自動退回）、6T-1c（郵寄驗收修正、寄件填數量、郵差分頁台詞）。
   - 6R-1（#138 獸耳族：獸躍、輕身、崖台、免費換種族；B 矩陣、C 捷徑檢查）— 美術過了崖台，**缺兩種補拍**（見第 4 點）。
   - UI-E3／UI-E4（背包格子、SkillTile、雇用圖示列、出口木牌）— 美術退回 3 必修＋8 小修（併進 UI-E3b）。
3. **未完成的段（都只在本機 worktree 分支，沒有 push、沒有合併）**：

   | 段 | 分支 | 最後 commit | 狀態 | 下一步 |
   |---|---|---|---|---|
   | 6T-1d 郵寄收尾＋soot＋全遊戲按鈕滑過 | `worktree-agent-aa505caec1aede557` | `15139179` | 7 項程式完成、相關 vitest 過；**截圖、全量 vitest、煙霧檢查未做** | 拍 `6t1d_*`（soot 頭像 5 位、郵寄修正、按鈕滑過／停用），交件檢查，合併後送美術 PM |
   | UI-E3b 遇敵卡頭像、傭兵 `skill_ids`＋UI-E3c（UI-E3 退回的 11 項） | `worktree-agent-af9447930647c770b` | `22a64706` | 伺服器欄位完成（相關 pytest、mypy、重播過）；UI-E3c 2、3、4、11 已改未驗；1、5 做一半；6～10 未做；前端遇敵卡縮圖、金環未做 | 照 `docs/phases/PhaseUI-E3b報告.md`（在 Windows 分支，尚未 push）的下一步做完，拍 `uie3b_*`、`uie3c_*` |
   | 6R-2 #137 外觀與中性稱謂＋6R-1 補拍 | `worktree-agent-aae0ccf14bc44eab2` | `4442d65e` | 只有盤點報告，程式未動 | 照 `docs/phases/Phase6R-2報告.md`（在 Windows 分支，尚未 push）第 3 節從 `LookChoice`／`look_options` 開始；範圍見玩法 PM 93beba59（先資料、稱謂、掃「他／她」、LLM 指令；外觀選單用現有部件） |

   - 接手時：分別對這三個分支派 agent 接著做（`git merge main` 後繼續，不要 rebase）；6T-1d 與 UI-E3b 都改 client，但檔案不重疊；6R-2 改 races.yaml、建角、模板與 LLM 指令，和另外兩段不重疊。
4. **待排（依優先）**：
   - **6F-20**（約 0.25，美術 6F-19檢查）：放不下兩圖示的 9 種改回「1 圖示＋+1」（控制＞減益＞增益）、膠囊「+」加長到約 6.5、預覽框最後一行被技能列切、浮動卡最下提示沒圓角、主城 800 任務鈕壓房子與技能卡蓋「WASD」。
   - **6R-1 補拍**（併進 6R-2）：獸躍弧線 GIF 或三連拍、獸耳族建角卡 1600／800。
   - dark_forest 改地圖（被倒木圍住的 2 格要走得進去）。
   - 朝南三角形移出 HP 條；戰鬥撤離「出」框內放小路牌圖示（美術另想）。
   - RT-5 結案後順手：1600 夾邊「！」上邊界確認、rt5d_3 說明列壓木橋。
   - 6F-5 #134 靶場開局（前置 RT-5 已完成；建角三步要等 UI-E1 create-v2 與 Q 版）。
   - QK-1～7 Q 版回歸（等使用者確認樣張；美術 PM 在畫第 17 版）。郵差 `mailbag`、場上 soot、beast_ears 畫法都等 QK。**soot 頭像落點併進 QK**（美術 PM 11-06）：QK 換 Q 版頭像時，頭像配件要先套 `buildScale` 畫在紙娃娃體型座標裡，soot、護目鏡等落點與裁切跟著體型走；QK 頭像驗收拍 tall、stout、一般各一張；之前不做暫時修正。
   - 6T-2 交易所（郵寄上線後）、AU-3、RT-2 補、UI-E1、多講一點接線、角色列表 last_played、12B／31B 基準（等使用者把 LM Studio context 調大）。
   - **Phase 6 收尾報告**：上面做完後再回專案 PM。
5. **這幾天學到的**：
   - `python` 在 Git Bash 是 Windows Store 空殼（結束碼 49、不執行）；腳本一律 `uv run python`，衝突手動用 Edit 解。
   - 6T-1a 合併後全量抓到兩個 agent 漏掉的：主手掉落改 50% 別大類後，舊 loot 測試要固定同大類；新的必填 API 欄位要補 client 測試 fixture，否則 `tsc` 不過（vitest 不查型別，一定要看 build 結束碼）。
   - 改主城或城鎮地圖都要更新 `tests/content/test_field_buildings.py` 的 `RULE_HASHES`；兩段同時改同一張圖會衝突，合併時用最後的內容重算。
   - 效能測試在全量並行下會超時：取 3 次最快（6F-16 起）。
   - agent 有時停在「等背景工作」但其實已經沒有背景程序：送訊息叫它直接重跑、確認跑完再結束。
   - 名額：開發最多 3 個，全專案 ≤ 4；美術 PM 開 2 個時開發降到 2 個。每次派段前先問美術 PM 現在幾個。

### 3.3 第六任開發 PM 進度（2026-11-02）

> 第六任開發 PM（2026-11-02；當時的 PM id 已失效，現行 id 見 3.1）。

1. **完成**（驗收紀錄都在 `docs/phases/PhaseBAL計畫.md` 第 2 節末與第 4～10 節）：BAL-10d／10e（收束、收回家族，`trpg.skillgen.flash_trade`）、BAL-11（預算旋鈕查修）、BAL-12a～12f（技能數值、#76 升階持續上限 6＋強度）、BAL-13a～13e（元素協同、弱 build、#77 連鎖衰減、#78 擴散每輪一次）、BAL-14a～14c（召喚、#79 刪 `boss_blocker_points`）、BAL-15a（法力量測）。`LOG_FORMAT` `/94`；最後全量 pytest 11067、vitest 1176。
2. **進行中**：BAL-15b（#80 敵我同一套資源公式＋模擬 build 資源基礎對齊主角）。
3. **玩法 PM 已接受、不再調**：storm 73%、fire 79%、summoner 74%、精英召喚 86%／群召 88%；「沒有價值的技能」名單原型不換（大世界再量）；頭目 HP 700‰（「頭目死、護衛撤退」待大世界問使用者）。
4. **下一步**：BAL-15b 驗收後，交接歷史 3.00000 第 4 點（`docs/archive/交接歷史-開發PM.md`）的清單已大致做完；剩「下次使用者開模型時 `scripts/eval_flash_diversity.py --real`」、4-L11 小待辦、vLLM oneOf 警告。問專案 PM 下一個大方向。
6. **加速方案（2026-11-02，使用者「好那都改 寫入」，已寫進 CLAUDE.md 第 11 條）**：全量每 2～3 段跑一次，合併時只跑 ruff、format、mypy、lint-imports、相關測試、一場重播；待決的原型數值／解讀類由 agent 照保守預設做完，確認累積到下一段，不另開收尾段（規則類照舊先問）；agent 開發中只跑直接相關的測試檔，CLI 快照與大範圍測試只在交件前跑一次；全量用 `-n 12`～`-n 14`、全量期間不跑模擬；CLI 輸出快照拆成可平行的小測試（排在 BAL-17 之後的一小段 PERF-1）。Windows Defender 排除由使用者自己決定，不要動。
5. **做法**：全量檢查不要和模擬同時跑（曾因資源不足讓 xdist worker 掛掉）；agent 暫存放各自 worktree 的 `.scratch_<段>/`，不用共用 scratchpad（曾誤跑別段的同名腳本）；兩段都改引擎時排先後，後段 merge main 再重產快照；agent 改 content 數值後常漏跑 `tests/api`、CLI 輸出快照，合併後全量會抓到。

### 3.4 已接受的技術細節（不用再問）

2C-1～2C-3 報告的其他「待 PM 決定」都已接受，例如：傷害只算實際扣血、友軍誤傷另列；墜落／致命地形／爆炸／燃燒的傷害由引擎帶來源；`boss_burst` 門檻 60%；滑倒停在友軍格時退回最近空格（以 teleport 事件表示，客戶端之後要處理）；policy／指揮官 factory 必須是模組層級類別（`--jobs` 要 pickle）。

## 4. 已確認但尚未落地的設計決定

- 戰鬥節奏目標：一般遭遇 4–6 輪、Boss 戰 6–10 輪。
- 元素與表面的中文名稱之後再定。
- 吊橋深淵兩端的繞行通道先接受。
- 冰窟＝致命地形（`ice_hole`）＋可破壞的薄冰（`thin_ice`）。

## 5. 仍待使用者決定的設計問題

- **敵方陷阱（2026-10-19 標記）**：2E 不給敵人陷阱技能（引擎已對稱支援，陷阱只有放置者陣營看得見）。之後可能讓敵人有陷阱，屆時要給玩家「察覺」的機會，例如相鄰時顯示，或用感知判定。建議在 Phase 3 網頁試玩時決定。

見 `docs/專案計畫.md` 第 3.2 節：#5 的世界觀（Phase 4 寫 prompt 前要定；美術原型已決定程式繪製）、#8 技能等級成長方式、#9 技能欄位數量。

## 6. 工作流程（照做即可）

### 6.1 環境（2026-11-06 起在使用者的 Mac mini 上執行）

- **機器**：Mac mini（arm64、16 GB、zsh）。PM 與實作 agent 都在這台的 Claude Code 執行，專案資料夾 `/Users/toby/PycharmProjects/llm_rpg`（origin 指向 GitHub `huntertoby/llm-mmo-trpg`，私人）；完成後直接 `git push`（何時 push 由專案 PM 統一說）。先確認 `git status` 正常、`uv run python --version` 是 3.12。
- **uv** 在 `~/.local/bin`：每個 shell 先 `export PATH="$HOME/.local/bin:$PATH"`；Python 一律 `uv run python`。不跑 brew、不重裝（`uv sync`、`pnpm install` 已做好）。
- **前端**：Node 26 沒有 corepack，一律 `pnpm -C client <build|test|typecheck|gen:api>`；程式裡找 pnpm 的邏輯在 `pnpm_command()`（`src/trpg/cli/frontend.py`，corepack 缺席時退到 pnpm／npx）。
- **埠**：預覽伺服器不用 8000（使用者的 `trpg serve`）與 8001（本機 LLM）；自己開的 `uv run trpg serve --port <空埠>` 只用它的 PID 關，不用 `pkill`／`killall`（守則 13）。
- **本機 LLM**：LM Studio（MLX 引擎）＋ `gemma-4-12b-it` 在 `127.0.0.1:1234`；設定 `config/llm.local.toml`（gitignored），跑的時候帶 `TRPG_LLM_CONFIG=config/llm.local.toml`；MLX 不支援 schema `oneOf`，`oneof_as_anyof` 預設開（MAC-2），`uv run trpg llm ping` 會印伺服器接受的 schema 寫法；真模型測試 `uv run pytest -q tests/llm -m llm`。**模型載著時不要跑全量 pytest**（記憶體只剩約 30%）。
- **全量**：`uv run python scripts/check.py`（`--full` 含 slow 與前端完整組合）；平行數 `TRPG_PYTEST_WORKERS`（預設 8；全量 12～14，全量期間不跑模擬）。2026-11-06 全量：pytest 15217、vitest 3045。兩個 vitest 雜湊快照（`creaturePose.test.ts`、`inkDollSnapshot.test.ts`）在 MAC-1 改成固定 6 位小數，**回 Windows x64 要再跑一次**。
- **GitHub Actions CI 只手動觸發**（2026-10-19 使用者決定，額度曾用完）：驗收一律以本機 `check.py` 為準。
- 專案設定 `.claude/settings.json`（已進 git）：常用指令免確認、檔案編輯自動接受、`PYTHONUTF8=1`。**背景 agent 卡在確認提示，表示它用了清單外的指令**：把該指令加進清單，或在規格裡改用清單內的寫法。
- 使用者電腦要保持開機、不睡眠，Claude app 要開著；中途斷掉時進度在 commit 裡，照 6.6 第二點派收尾 agent。
- **回 Windows 時**：Git Bash 的 `python` 是 Windows Store 空殼（結束碼 49），一律 `uv run python`；前端用 `corepack pnpm -C client …`；路徑（`F:\PythonProject\LLM-MMO-TRPG`、`/f/...`）與其他 Windows 說明見 `docs/archive/交接歷史-開發PM.md`（3.000 第 5 點、3.00）。

### 6.2 一個階段的流程

> **PM 之間的訊息（2026-10-23 使用者同意，為了省 token）**：只在 ① 某段驗收合併完成（附給使用者的檢查重點）② 卡住 ③ 需要對方或使用者決定 時傳訊息；不傳「已轉給」「已記下」「已排入」「副知」「還在等」這類告知，收到告知也不回覆；要留紀錄就寫進文件或 commit。理由：每則訊息都會叫醒一個 50 萬 token 以上的長對話。使用者原話：「2的部分就好 1的話 我等你們收尾phase3就會叫他們做了」。
>
> **回報規則（2026-10-22 使用者指示）**：PM 的 context 只放決策，不放細節。開發 PM 回報專案 PM 時只寫結論與摘要（做了什麼、結果、卡在哪、要使用者決定什麼），細節放進文件、只附檔案位置與 commit；派出的實作／審查 agent 也只回摘要；驗收時不把整份測試輸出或 diff 讀進 context，抽查即可。**回報時機**：只在某段驗收合併、卡住、或需要使用者／其他 PM 決定時回報（附「請使用者重開伺服器檢查的重點」）；「還在等、沒有新進度」不回報。

0. **決策影響盤點（2026-10-24 使用者同意流程改善 A）**：每個玩法／美術決定寫入後、寫規格前，開發 PM 先做一次只讀盤點「現行程式哪裡受影響」（引擎、內容資料、工坊、隨機組合器、LLM 提議、介面、存檔、測試），結果寫進規格的「受影響的既有功能」段。起因：#45 寫入後只做新功能，工坊與驗證器沒跟著改，造成武器技屬性漏洞與工坊違規技能（`docs/archive/phases/工坊盤點-2026-10-24.md`）。
1. **寫規格** `docs/phases/PhaseX計畫.md`：目標、範圍外、工作環境、交付項目、驗收條件（每條可驗證）、報告格式。**必填兩段（2026-10-24，流程改善 A、B）**：① **受影響的既有功能**（第 0 步盤點結果，每項寫要改或不改的理由）；② **行為一致測試**——凡是規則句（看什麼屬性、花什麼資源、誰能抵抗、說明文字寫的數字），一律要求「實際跑引擎」的表格測試，不只測資料與驗證器（範例：3-41c 的傷害算法與引擎 `damage_dealt` 逐一比對）。上一階段報告的「待 PM 決定」放在新規格開頭的「PM 決定」表。**規格要小**：一個 agent 的工作量控制在約 30 分鐘、25 萬 token 以內，範圍以「一套規則 ＋ 其測試」為上限。
2. **commit 並 push 規格**。
3. **派實作 agent**：`Agent` 工具，`subagent_type: general-purpose`、`run_in_background: true`，模型依 6.3 選。prompt 範本見 6.4。
4. **等通知**，不要輪詢。使用者問進度時用 `git log --format='%cd %h %s' --date=format:%H:%M <base>..HEAD` 回報。
5. **功能驗收**（自己做，不只看報告）。**檢查分級（2026-10-23 使用者同意，專案 PM 傳達「好」）**：
   - **排版煙霧檢查（2026-10-24，流程改善 D；3-47 起有工具）**：凡是動到前端的段，合併後在內建瀏覽器跑 `window.__layoutSmoke`（`client/src/dev/layoutSmoke.ts`，純函式 `evaluate` 有 vitest；不需安裝任何套件）。步驟：① `pnpm -C client build`，背景啟動 `uv run trpg serve --port <空的埠>`（只關自己的）；② 每個情況先 `resize_window`，先 `javascript_tool` 執行 `localStorage.clear()`（有舊的一輪存檔時頁面會接回去、全部量不到），再 `navigate` 到 `/?dev=1&anim=0.1`（6F-1 起正式首頁只剩「開始」，煙霧檢查要在開發模式跑），再 `javascript_tool` 執行 `await window.__layoutSmoke.runCase("標題")` 取得 PASS／FAIL 表；三個情況：1600×900、1040×624、800×600（6A-4g 起拿掉 `shortBottom` 與拖曳線：戰鬥改成 HUD 疊在鋪滿的戰場上，改量 HUD 各塊不重疊、不出畫面）；③ 結束 `resize_window` preset `desktop`。量：結束回合寬度 ≥ 右欄 90%、播放列與按鈕在畫面內且一行、格子資訊卡提示列在底色內、「更多動作」選單開著時沒有說明卡、沒有 `.hint-tip` 外框。固定種子與起始武器（弓），結果可重現；全 PASS 才算過。新增版面元件時把它的量測加進 `layoutSmoke.ts`。`?anim=0.1` 可放慢動畫逐格截圖。
   - **一次出事就全面掃描（流程改善 E）**：同類錯誤第一次出現時，就全專案掃描同樣寫法並寫成常駐規則，不要只修那一處（反例：說明卡包一層造成的排版錯誤先後出了三次）。
   - **每段合併只跑快速檢查**：`ruff check`、`ruff format --check`、`mypy`、這段改到的 pytest 檔與相關前端測試、一場 `--log-json` ＋ `replay`；有改前端才跑 `pnpm build`。
   - **全量 `check.py` 每 2～3 段合併跑一次**，以及 Phase 結束審查前一次（3-34 之後用 `scripts/check.py --full` 含 slow）。
   - **同時進行的 agent 最多 4 個、不可改同一批檔案**（2026-11-04 使用者「同意，改第 11 條」；全量每 1～2 段合併跑一次）。**開發 PM 自己最多 3 個**，留 1 個給美術 PM 派畫圖與審查 agent（2026-11-04 晚，使用者：「感覺美術也要像開發PM那樣」，專案 PM 轉）。改到存檔欄位或技能池的段，相關測試要包含 `tests/test_architecture.py`；pytest 不用 `-n auto`。3-34 起：`scripts/check.py`（快速版，約 3 分鐘，不含 slow）、`scripts/check.py --full`（含 slow 與前端完整組合 `TRPG_FULL=1`，約 10 分鐘）；平行數 `TRPG_PYTEST_WORKERS`（預設 8，可設 `auto`）。長指令要加 timeout（Bash 預設 2 分鐘會中斷）或背景執行。3E-2c 起：pytest-timeout（一般 300 秒、slow 1800 秒）；agent 在自己的 worktree 跑測試，加 `UV_NO_SYNC=1`（或 `uv run --frozen`）避免測試中途重裝套件。
   - 原寫法：`uv run python scripts/check.py`；挑一張地圖換一個種子跑 `trpg battle ... --log-json` 再 `trpg battle replay`；抽查一兩個關鍵設計（例如引擎內沒有浮點 log、沒有 `random`）。大型模擬（completion、matrix）由 PM 在驗收時於背景跑，不放進實作子階段。
6. **大階段結束時（例如 2E、Phase 3 結束）派審查 agent**（6.5），把結論中要處理的項目排進下一份規格。
7. **push**。
8. 向使用者回報：做出了什麼（附一小段戰鬥紀錄）、待決定項目怎麼處理、哪些需要使用者決定。

### 6.3 模型選擇

| 工作 | 模型 |
|---|---|
| 規格清楚、照做的實作（新增模板、狀態、內容、CLI、測試） | `sonnet` |
| 新架構或難以事後修改的設計（Phase 3 伺服器與前端骨架、存檔格式、Phase 4 LLM 流程與 prompt）、Sonnet 連續兩次做不好的子階段 | `opus` |
| 審查（6.5） | `opus` |

### 6.4 派實作 agent 的 prompt 範本

```
你是這個專案的實作者（implementer）。PM 已寫好規格，請實作 **Phase X｜名稱**。

專案位置：目前資料夾（main 分支，目前 HEAD 為 <hash>）。

請依序：
1. 讀 `CLAUDE.md`（特別是守則 11 節省 token、守則 12 複雜度）。
2. 讀 `docs/phases/PhaseX計畫.md`——這是你的規格。
3. 讀規格指定的前一階段報告與 `docs/design/` 主題檔（只讀指定的）。
4. 開發中只跑相關測試檔；每次 commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**不要跑完整的 `scripts/check.py`**（PM 合併後統一跑）；pytest 平行最多 `-n 8`。Python 一律用 `uv run python`（Mac 每個 shell 先 `export PATH="$HOME/.local/bin:$PATH"`；Windows 直接打 `python` 是商店空殼）；前端 `pnpm -C client …`。
5. 不要 push。
6. 逐條自我檢查驗收條件（要有測試名稱或指令輸出為證）。依邏輯分 commit，結尾帶 Co-Authored-By 一行（依你的系統提示）。
7. 撰寫並 commit `docs/phases/PhaseX報告.md`；若新增了複雜度類 noqa（C901、PLR0911、PLR0912、PLR0915），在報告中逐一列出理由。

若改到前端：彈出卡片一律用共用浮動卡元件（本檔 6.5.1）；交件截圖照本檔 6.5.2（`docs/art/shots/<段>/`、≤ 10 張、jpg 80、單張 ≤ 300 KB），並在瀏覽器實測「從觸發元素滑進卡片 → 捲到底 → 釘住 → 關閉」（1600×900 與 800×600），結果寫進報告。

規格沒寫到的採最保守做法並寫進報告「待 PM 決定」。不要修改 `docs/專案計畫.md`、`docs/design/`、`CLAUDE.md`、`docs/phases/` 下的計畫檔。

**禁止事項（2026-10-24，流程改善 F）**：不要用會結束不是自己啟動的程序的指令（`pkill python`、`killall node`、`taskkill /IM python.exe` 等）——使用者的 `trpg serve` 與其他 agent 會被一起關掉；要結束自己開的伺服器只用它的 PID。預覽伺服器不要用 8000（使用者的）或 8001（本機 LLM 模型）埠。不要改使用者的設定檔（`config/llm.local.toml`、`config/deploy.local.toml` 等）。

**測試與巡檢一律靜音**（2026-11-04，使用者：「你這邊測試聲音我會聽到ㄟ 可以不要嗎」）：
- 無頭 Chrome 和 Playwright 一律加 `--mute-audio`。
- 預覽、截圖、實機巡檢時，頁面載入前先把主音量設成 0，或用強制靜音參數，聲音不能從喇叭出來。
- vitest 一律用 mock 的 AudioContext。
- 不要用系統指令播放任何音檔。
- 試聽只用波形或數值驗證，聽感交給使用者。

最終回覆用繁體中文，只寫摘要：commit 列表、驗收是否全過（未過的逐條列出）、卡住的點、「待 PM 決定」（最多 10 點）。完整 log、測試輸出與逐條驗收證據寫進報告檔，不要貼在回覆裡。
```

### 6.5 審查 agent（大階段結束時）

目的是抓「測試抓不到」的品質問題。用獨立 agent，讓幾千行的改動不進 PM 對話，也讓沒參與撰寫的人用新眼光看。`model: opus`，`run_in_background: true`。

```
你是這個專案的程式碼審查者（reviewer），不修改任何檔案。請審查 <base>..HEAD 的改動（Phase X 全部）。

1. 讀 `CLAUDE.md`，再用 `git diff --stat <base>..HEAD` 看範圍，只讀需要的部分。
2. 找出：重複的邏輯、過長或過度分支的函式（含新增的複雜度 noqa）、違反守則 1–5 的地方（確定性、依賴方向、內容即資料）、
   只為通過測試而寫的特例、命名或模組放錯位置、之後 Phase 3／4 會卡住的設計。
3. 不要跑全量測試或大型模擬；需要時只跑相關測試檔。

最終回覆用繁體中文，最多 10 點，依嚴重度排序。每點：位置（檔案:行）、問題、建議修法、估計工作量（小／中／大）。
最後一行給整體評價：可直接進下一階段／建議先排一個整理子階段。
```

PM 看完結論，決定哪些排進下一份規格（或獨立一個小的整理子階段）；向使用者簡短回報。

### 6.5.1 前端浮動卡規則（常駐；2026-10-22 使用者：「這個彈出式ui的問題發生很多次的 看是要記在哪個.md 然後之後收尾也要看一下」）

- **所有彈出卡片、說明框、資訊卡都必須使用共用浮動卡元件**（3-30：`client/src/ui/floatCard.ts`、`useFloatCard.tsx`；格子觸發的資訊卡用 `hoverCard.ts` 的 `TileCardController`；部件說明框 `PartTip`），**不准各自實作**新的彈出層或用原生 `title` 代替。
- 行為規格（`Phase3計畫.md` 32.1、32.2）：
  1. **滑過延遲**：按鈕約 150ms 後顯示（格子資訊卡不加延遲，因為玩家常掃過戰場）。
  2. **離開寬限＋橋接區**：離開觸發元素後約 250ms 寬限，觸發元素與卡片之間有透明橋接區；途中經過其他觸發元素不換卡。**按鈕＋彈出選單**（2026-10-23，使用者：「彈出的視窗會沒有辦法按裝填」）：觸發按鈕若包了說明卡 `<Hint>`，選單打開時（按鈕要標 `aria-expanded`）說明卡不顯示、已開的立刻關（`Hint.tsx` 依 `aria-expanded` 判斷），否則說明卡會蓋住選單；新的彈出選單一律在觸發按鈕標 `aria-expanded`。掃描結果：目前只有「更多動作」包了 Hint；頂列的反應設定、隊友指令、圖例、版面沒包，不受影響。**CSS 注意（3-47 起）**：`<Hint>` 不再產生外層元素（事件與 ref 用 `cloneElement` 掛在唯一的子元素上；子元素必須是單一 DOM 元素，元件要在 Hint 裡自己再包一層元素），所以 `父 > 子` 選擇器照常可用，不需要 `> .hint-tip >`。舊版外包 `.hint-tip` 曾出事三次（拖曳線 `358a43a`、結束回合／播放速度 3-41b 後、說明卡蓋住選單），現由排版煙霧檢查（6.2 第 5 點）擋住。**例外：格子資訊卡（戰場地形／角色卡）不能滑進，只能點擊釘住**（3-40、3-40b，2026-10-23 使用者：「改成按左鍵」選 C、「滑鼠往左滑到彈出視窗固定的功能就不要了」）：沒釘住時卡片不接滑鼠（`pointer-events: none`），換格子立刻換卡、離開格子立刻關卡；沒有動作的格子左鍵點＝釘住、Shift＋左鍵任何格子＝釘住、不是自己的回合點任何格子＝釘住；再點同一格或 Esc 取消；有動作的點擊照常行動並關卡；釘住後才可滑進、點擊、捲動。卡片標題列右側圖釘（沒釘住淡色、釘住金色 `#ffd04a`）、底部一行在卡片底色內（沒釘住：「點擊釘住・Shift＋點：任何格」；釘住：「Esc 或再點一次：取消」）（美術 PM 定）。**其他浮動卡（按鈕、技能卡、裝備）照舊可滑進＋寬限**：它們的觸發元素左鍵是動作，且卡內有部件說明要再滑過。
  3. **可滑進卡片停留**：滑鼠在卡片上時不關閉。
  4. **點一下釘住**；**Esc 或點外面關閉**。
  5. **同時只開一張**（新的取代舊的；卡片內的部件說明框例外）。
  6. **貼齊觸發元素**（預設上方、無空隙），**超出畫面才翻轉或往內推**，左右不超出畫面。
  7. **最大高度不超出視窗／可見區域，超出時卡片內捲動**；捲動不關閉。卡片要 portal 到 body，避免被捲動容器裁掉。
  8. **鍵盤與觸控**：取得焦點時顯示、Tab 可進入卡片；觸控以點擊開關。
- 只要改到前端的段，派工 prompt 與驗收都要求：**瀏覽器實測「從觸發元素滑進卡片 → 在卡片內捲到底 → 釘住 → 關閉」**（1600×900 與 800×600），結果寫進報告；PM 驗收時抽查一處。
- 自動檢查（已在 `client/src/ui/floatCardRule.test.ts`；5D-R1 補上直接改 DOM 的 `style.position`）：`client/src` 中除共用元件外不得出現新的 `position: fixed`／`absolute` 彈出層或 `title=` 屬性（白名單列出例外）。

- **6.5.1 的明文例外（美術 PM 同意）**：技能面板的技能卡（UI-E3c 第 5 項）與雇用面板技能圖示的說明牌（UI-E3b，11-06）優先開在下方，因為往上開會蓋到主角卡／傭兵名字；其他浮動卡仍預設上方。

### 6.5.2 交件截圖規則（2026-11-06 使用者同意整理提案 S3）

- 交件截圖一律存 `docs/art/shots/<段>/`（段名小寫，例 `6f19`、`uie3b`）；每段 ≤ 10 張、jpg 品質 80、單張 ≤ 300 KB（GIF 只用在動畫段，一樣算張數）。
- 美術 PM 通過後，1600 寬與 800 寬各留 1 張，其餘從工作區 `git rm`（歷史仍在 git，不改寫歷史）。
- 舊截圖已依檔名前綴搬進 `docs/art/shots/<前綴>/`（DOC-A S1；張數 ≤ 2 的前綴在 `shots/misc/`），找舊圖用 `git ls-files 'docs/art/shots/**/<檔名>'`。
- 派工 prompt 與報告都寫完整路徑 `docs/art/shots/<段>/<檔名>`，不要寫裸檔名。

### 6.6 注意事項（踩過的坑）
- **agent 交件前必須關掉自己開的無頭 Chrome**（2026-11-07 使用者：「這個記起來 沒關的部分」）：TR-1 的 agent 交件後留下 7 組 `--headless=new` Chrome（資料夾在 worktree 的 `.scratch_*`），各吃約 60% CPU、一小時以上，全量 pytest 從 15 分拖到 45 分以上、負載 23。派工 prompt 一律寫：「交件前用自己記下的 PID 關掉伺服器與所有無頭 Chrome，`ps` 確認沒有殘留」；PM 合併後、清 worktree 前先跑 `ps -eo pid,command | grep "[G]oogle Chrome --headless"` 檢查，殘留的只用 PID 關、且只關 `--user-data-dir` 指向我們 worktree／scratchpad 的，使用者自己的 Chrome（`--user-data-dir` 在 `Library/Application Support`）絕不能動。

- **共用資料夾的 git 規則（所有 PM）**：主資料夾由專案 PM、玩法 PM、開發 PM 共用。更新一律用 `git pull --ff-only`（必要時 `git merge`），**不要 `git pull --rebase` 或 rebase**——會把別人尚未 push 的合併 commit 攤平（2026-10-22 發生過一次，內容無誤但失去合併紀錄）。commit 前先 `git status`，只 commit 自己改的檔；開發 PM 合併中時其他 PM 先別 pull。
- **Agent 可能中途停止**（用量上限、被手動停止、電腦睡眠）。進度會留在 commit 裡；派一個新的「收尾」agent：說明前一位的最後 commit、請它核對驗收條件、補齊缺漏、寫報告，不要重做。
- agent 還在跑時，工作區可能有未 commit 的半成品，**不要替它 commit**。
- **平行工作**（例如文件整理與程式實作同時進行）用 `isolation: "worktree"` 的 agent，完成後在 main 上 `git merge --ff-only <先完成的分支>`、再 `git merge --no-ff <另一個分支>`，合併後自己跑一次 `check.py` 與一場 `--log-json`／`replay`。兩個 agent 共用 CPU，同時跑全量測試會互搶，但仍比雲端快。
- **建立新的 GitHub repo** 要請使用者在網頁上建。
- 平衡調整很耗 token：讓 agent 寫腳本輸出摘要表，由 PM 決定數值，不要讓 agent 反覆試。
- **`WORLD_RULES_VERSION`（`src/trpg/world/save.py`，6D-R1）何時加一**：改了 `trpg.world` 的規則**程式**、會讓同一份世界日誌重播出不同結果時（走路、遇敵、感知、事件、戰鬥回寫的判法等），在同一個 commit 手動加一；只改內容資料（`content/`）或純顯示、API、前端不用加（內容 digest 已涵蓋）。不確定就加（代價只是舊日誌標成「規則已變、不能重播」）。
- 規格要求大型模擬時，寫明「只在最後跑一次全量」（2C-4 曾因完成度檢查跑兩次，用了 68 分鐘、28 萬 token）。

## 7. 節省 token 的原則

- PM 對話本身是最大的隱藏成本（每一步都會重新處理整段對話）。**對話變長時（例如完成一個大階段後），更新本檔並請使用者開新對話。**
- 實作 agent 依 6.3 選模型（預設 Sonnet）；規格要小；agent 開發中只跑相關測試（CLAUDE.md 守則 11）。
- PM 讀文件只讀需要的：總覽 ＋ 對應的 `docs/design/` 主題檔 ＋ 最新一份報告。不要讀整份舊報告或舊對話。
