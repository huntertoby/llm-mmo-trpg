# 開發 PM 交接文件

> 給接手的 **開發 PM**（新對話中的 Claude）。最後更新：**2026-11-07**。**只讀本檔就能接手**；需要時再讀 `CLAUDE.md`、`docs/專案計畫.md`（總覽）與本檔指到的計畫檔。
> 現況一句話（2026-11-12）：**#150 開局先玩再定的後端與前端第一段（OB-1～OB-5）、#149 頭目招式與異形第二種近戰動畫都已上 main；接著是 PR-2、OB-6 與上手筆記**。最新狀態與待排見 **3.000**（優先於下面各節；第 2 節的表與版號停在 2026-11-07，以 3.000 為準）。

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

### 3.0000 現況（2026-11-13，第八任開發 PM；壓縮前更新，最新）

> 換手方式改成壓縮（使用者 2026-11-12 原話「改」）：PM 對話約 40 萬 token 時，在段落點更新本節並 commit，告訴專案 PM「請壓縮」，由使用者按「壓縮工作階段」；session id 不變、在跑的 agent 照樣回來。第七任的 3.0000 已搬到 `docs/archive/交接歷史-開發PM.md` 開頭。PM id：專案 PM `local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa`、玩法 PM `local_da4b4c03-a86c-4afe-b898-68314e032524`、**美術 PM 第九任 `local_e3d7ae7a-abaf-485f-9b62-c614293794e9`**（分支 `claude/art-pm-9-027334`，只動 docs/，併前用 `git log --no-merges --format= --name-only main..<hash>` 確認）。模型：PM 與所有 agent、子 agent 一律 Opus 5.5。

**1. 本任上了 origin/main 的段**（報告都在 `docs/phases/Phase<段>報告.md`）：NW-1b、QI-4b、BAL-21b（放寬驗證使用者選 C）、OCL-1a／1b／1c（剪影外框結案）、VFX-1、BAL-21c、BAL-21e、PB-1a／1b／1c（頭目部位段 1）、QI-5（⑦ HUD）、NW-2a／2b（數值工坊技能）、DD-1／1b／2（#153 雙匕首）、OB-7／7b／8（#154 開局只帶賽倫、#155 遭遇大小、渡口 2 打 1）、FIX-ATLAS1（荒原空框）、FIX-ATLAS2（鎖住浮島滑過微亮 16%）。版號：`LOG_FORMAT` /117、`WORLD_RULES_VERSION` 27。worktree 清理全部做完（殘留 152＋保留 63＋孤兒 1 都已刪，主資料夾 install／build 0，F 槽可用約 356 GB）；保留清單 `docs/archive/worktree清理保留清單.md` 留作紀錄。

**2. 最後一次全量**：2026-11-14 e2bab3fe1 全過並 push（pytest 17682、vitest 4676、build 0），含 NW-3d（LLM 提議與技能工坊造牆物件改用組合器候選、1600 黑煙壓到 HUD 下）。版號 LOG_FORMAT /128、WORLD_RULES_VERSION 33、CHAR_FORMAT /15。**合併動到事件或 API 的段後，先重產 OpenAPI 再跑全量；有 agent 在跑測試時全量常在 99% 卡死，盡量等 agent 都回來再跑。**

**3. 執行中的 agent（分支）**：
- **2026-11-22 晚 現況（優先於以下各行）**：已 push：HC-6c（68854a87c＋裁定 b48963e3c）、WL-1 a（eb1f0bd25）／b（d5ac5e359）／c（cd1ac51b4，裁定 1592db687；美術結案 0c31dcf5f）、E2～E5 草案（`docs/phases/E2-E5草案.md`，d6b9fa7de）。進行中：E1（計畫 `PhaseE1計畫.md`，規則 08 8.28／#174；LOG_FORMAT 升 /136 已同意；跑全量前會先問）。等待：E2～E5 的 21 題裡 9 題玩法代決 A，12 題轉使用者（第一波 E2-2、E5-1、E5-2、E5-4、E5-5、E5-6 定了才派 E2∥E5；第二波 E3-2、E3-4、E4-2～4-5 定了才派 E3∥E4）。佇列新增：(f) 「擊中時」統一成「命中時」（玩法 PM 定，content／client 約 7 處，含反咒觸發格）；(g) 表面、物件、元素、條件、觸發找不到名稱時仍露英文 id，下次一起問玩法用字；(h) `skeletonName` 的 override 參數沒人用，碰 `skillIcon.ts` 時刪；(i) `_OFFHAND_ZH`、`_ELEMENT_ZH` 和資料 `name_zh` 重複；(j) 內容資料夾要跟著 `load_library` 走（E 系列碰載入層時做）；(k) `tests/infra/test_xdist_loadgroup.py` 單 worker 當掉那題 240 秒在全量負載下不夠，照 QF-4b 放寬；(m) E1 美術小修（`docs/art/E1驗收.md`）：技能列副標題只寫裝備名（玩法 PM 定 A，放不下截斷尾巴），說明卡金框和卡片之間的 3 px 縫拿掉；和 (f)「擊中時」一起併進 KD-1；(n) E3 要一併做：E2 裁定 1，數值型地形規則數字不同時取較強的那條（8.29 已補，0633bbb8d）；裝備較強時角色面板註明種族那條被蓋過，種族較強或一樣強時裝備那條標灰；E2 裁定 4，AI 表面傷害免疫接在 `_harmful` 的回合開始傷害段；(o) 8.29 E5 第 7 點：一招只套一種變形，技能卡要註明「已有其他變形」，下次碰前端時做（玩法 83a86d390）；(p) E5 裁定 6：AI 便宜估計 `skill_estimate.py` 不知道閘門降傷，下次碰時改；(q) WL-2 裁定 1、4：前端 TryoutPanel、tryout.ts 改讀 API 地圖摘要的 `role`，並加 role 存在檢查（照 WL-1 b）；(r) 組合器 seed 238 組出只有預支（borrow_ap，預算 0）的光環，`test_one_thousand_seeds_are_all_valid_and_spread_out`（slow）失敗：改組合器不出零預算單效果或改檢查規則，另開小段；(s) TS-1 裁定 2：讓 check.py 自己認同內容同基準的分流戳記（之後再議）；(t) E3 用字已定（8.29，玩法 15288ecb4），下次碰路徑預覽／表面說明時做：走路預覽在起點與途經畫出會留下的格子（停點不畫），預覽牌加一行「沿路留下冰 N 格（M 回合後消失）」，非冰換表面名；霜行冰的名詞說明照 8.29 寫（持有者名字、剩 N 回合、到期直接消失不變水、自己踩不滑、其他人照一般冰檢定）；美術 E3 驗收（`docs/art/E3驗收.md`）小修 3 件併進 (t)：「被蓋過」加註改灰（HUD 與角色面板）、台階「▲N」畫在路徑線上面、HUD 種族那行加 `text-wrap: pretty`；另查環境預告 (1,3) 重複兩行是否為同一件事（是就改成原行標金）；將留冰的格子不要畫成冰，用框線加預覽牌文字（玩法同意）；種族被動加註改成不用括號、HUD 與角色面板同一套（玩法 PM 定）：「被動「X」・有作用」／「被動「X」・水的部分被身體的「〇〇」蓋過，其他有作用」／「被動「X」・被腳的「〇〇」蓋過，沒有作用」（〇〇＝裝備名，灰色只套沒作用那段）；E3 已合併 db25a8f1b，裁定 967569588；美術 E4 驗收小修與 on_block／on_displace 圖示移植已在 E4b 做完（dc0086a21），E4 美術結案；(t) 再加：所有用「・」分點的說明框都改懸掛縮排、共用同一個 CSS class（E4b 的 `part-tip-bullet`），挑 2～3 種 800 寬各補拍一張（美術 96a5cb9de）；(u) E4 第 8 點：被動技 `reaction` 篩選 id 加存在檢查，LLM／組合器開放篩選等 E6；E4 已合併 0e103d5ff；CR-1 已合併 d7b642c4a；(v) CR-1 第 8 點：角色面板顯示暴擊傷害 N%（用字玩法 PM 定）；進行中（11-23）：TS-2＝testmon 試用（`PhaseTS-2計畫.md`，已授權跑多次全量，其他 agent 的全量要排在它的空檔）、E3b＝佇列 (t)（`PhaseE3b計畫.md`，跑全量前會問），再開 TS-1 B（testmon：pytest-testmon 2.3.0＋coverage 7.17.1，只放開發相依，專案 PM 已同意；試用規則：只試只改後端、每次分流再全跑對照、漏抓記報告）；(l) 實作者先問「準備跑 check.py」時，可能在回覆送到前就交件，交件後再用 SendMessage 叫回來跑。
- **2026-11-22 現況（優先於以下各行）**：已 push：HC-6a（3940021d3＋裁定 4cb00d459）、Swift 27B 量測與 config 改預設（54c11334b，報告 `docs/phases/Swift-Qwen27B品質評估.md`，待使用者決定：說書人簡體檢查、許願超過 10 秒、三選一退回 10%）、GS-3（21ca8f2cc＋裁定 f6fae5385；數值待決 1、2 轉使用者）、HC-6b 計畫（add305d93）。進行中：HC-6b。之後 HC-7（含 HC-6a 留下 26 筆 text、誓約冷卻「1 天內」從秒數組字、world fallback、重播／季存檔驗證失敗的中文訊息）→ 計數／白名單 → E1～E5 → E6。佇列新增（玩法 PM 定，06 6.30「GS-3 後補」32f6c3325）：(a) 化形守護護盾 ‰ 加只給升階重配用的旋鈕（照 6.34.9 維持原比例；組合器、LLM 不用），併進下一個碰技能的小段；(b) 進入時效果擲命中不用掉形態「下一次攻擊」獎勵，下次碰形態順手改；(c) 高階化身閃現照現行，不做專屬。另：`test_wish_pregen.py` 全量平行時 10 秒等待偶發失敗，下次碰許願預生成時處理。
- **2026-11-21 晚 現況（優先於以下各行）**：
  - **已 push 到 main `0be842398`**：
    - HC 系列：HC-B、HC-W2、QF-3a、HC-4a～4d、HC-5a、HC-5b。config todo 後端 164 筆；`src/trpg/content/`、`skillgen/` 都是 0。
    - QF-4、QF-4b：護主配方加快取，慢測試 600 秒放寬已拿掉。
    - 使用者直接改的 10 格平衡數值：雙牙 1320、影縛 1350、silent_strike 420，這 3 格取最接近又合格的值；梯田盜賊跟著改成 180。
    - GS-1：#171 護主不獨佔、#172 形態只出主動題。
    - 配方盤點：`docs/phases/盤點-2026-11-21/`。
  - **進行中**：GS-2，形態補 8 招手寫技能，計畫 `PhaseGS-2計畫.md`。
  - **之後**：HC-6 文字（含 HC-5b 裁定 4 的 `wish_cards`「3 張」）→ HC-7（含 HC-4c 裁定 1：重播與賽程封存驗證失敗時改給中文說明；HC-4d 裁定 2 的世界備用值）→ 計數／白名單 → E1～E5 → E6。
  - **順手項**（排進任一段）：`recipe_census` 的設計鍵要算進召喚物種類，否則召喚 2～3 階會誤報成薄格（專案 PM 轉玩法 PM，272b92cc9）。
  - **流程**：
    - agent 交件前全部 commit 之後，先問 PM 才跑 `check.py`。PM 只在 main 沒動過時回「可以跑」；main 動過就回「不用跑」，由 PM 合併後在 main 上跑。
    - commit 和 push 分成兩個指令下。
    - 用 Python 寫檔要 `newline=""`。
- **2026-11-21 現況（優先於本行以前的現況）**：已 push 到 main `4d53775e5`：X10 全系列、AR-X10、HC-1、HC-2、QF-2、HC-3、HC-4a。寫死數值集中化照使用者「全部集中化先做完」進行：用 `scripts/hardcoded/classify.py`（分類 config／scale／const／text／layout／guard）加 `tests/test_hardcoded_scan.py` 管，清單在 `docs/phases/寫死數值-清單.md`，合併衝突時用 `--md` 重產。進行中：HC-B（專案 PM 轉使用者：工坊改不到原語預算，例如升起地形；計畫 `PhaseHC-B計畫.md`，做完回專案 PM 一行）。之後：形態、裝備規則、物品生成開進工坊 → HC-4b（技能規則，含 `_check_tier_budget` 1～5、刪 classes.yaml 戰鬥核心 6 條 done 規則）→ HC-4c AI 與環境 → HC-4d 世界（含 content 時段表，前端 hud 鐘點改讀）→ HC-5 skillgen 常數 → HC-6 文字（含工坊 15 筆分類、祝禱骰子字、地面 tooltip、組裝列說明、名詞表骰子欄位、路徑預覽的「要多擲」狀態）→ HC-7 → 計數／白名單 → E1～E5 → E6 → 50 條內容（`內容擴充評估.md`）。分類守則：結構性的數字在 classes.yaml 寫 const 規則附理由，不改寫語法躲掃描。佇列另加：營火「重閃」按鈕統一懸掛縮排（`docs/art/HC-3看圖.md`）。其餘佇列同下一行。
- **2026-11-20 現況（優先於本行以前的現況）**：已 push 到 main `bf39399f1`：AP-1、AP-2、AP-2b、AR-AP2、QF-1、X10-1、X10-2a、X10-2b（量類 ×10 已生效，`core.yaml` `quantity_scale: 10`；LOG_FORMAT /135、PROMPT_VERSION skill-proposal/24）。舊存檔已照使用者「清掉重來」做季末重置（s1→s2，開賽日 2026-11-20），備份在 `saves_backup/`（已 gitignore）。段要拆小：每段 2～3 件、同一塊。agent 交件前要跑全部非 slow 測試（X10-2b 曾只跑 slow cli 漏掉 7 個）；2026-11-21 起改成全部 commit 後，在 worktree 跑一次 `scripts/check.py`（使用者：「改成一次跑完」「拿掉第二次重複的測試」）。下一段：X10-3（前端位數、骰子顯示要先問玩法／美術 PM、工坊換算紀錄、掃說明文字的量類數字、讀到舊單位存檔就拒絕並提示）；之後 #169 招牌效果、傳說、獨特裝備（`docs/design/08` 8.27）。佇列：`tests/skillgen/helpers.py` 預設耐力 8 改新單位；給精英、頭目裝預支；`every_n_hits` 工坊鍵；SK-5 數字鍵係數表上工坊；SK-3b 新觸發裝備詞條；`test_flash_economy` 種子 5 一輪 138 秒；重抽提示詞模式；has_keyword；LB-2c `_topup_advice`；PK-4 等使用者通知 Gemma；SK-3d 絆倒不做。
- BM-1（前端：800 頭目狀態列、延遲預告字、flushSync）、NW-3、GB-4c、NW-3b 都已 push。NW-3c、GB-4d、NW-3d 也已 push。LB-1／LB-1b（本機模型比較、Gemma 重測）已 push（報告 PhaseLB-1報告.md；重要發現：llm.toml 的 enable_thinking 在 LM Studio 無效，要 reasoning_effort=none）。LB-2（LLM 失敗診斷：記錄、schema 相容、溫度、prompt）已 push（d96b5a974，全量 pytest 17698、vitest 4676；改後重測因 GPU 沒載滿未跑）。LB-2b（Q12 被動引導、變奏開放 range_delta、改後重測、上手筆記的換模型規則）已 push（全量 pytest 17709、vitest 4676）；待決 2～3 轉玩法（3.0001），4～6 等玩法答覆後排 LB-2c。LB-CF（config 預設 Gemma＋reasoning_effort=none，實機確認完整技能格有 LLM 候選）、LB-2c（不要求就不給變奏、開放 self_on_high_ground、被動 schema 固定、Gemma 重測 15/18/2）已 push（全量 pytest 17721、vitest 4676）；LB-2c 待決 1（_topup_advice 沒套被動過濾）與 schema 上限餘裕等挑選模式提案結論；挑選模式提案：使用者第 6 節 5 題「都建議A 但是做出來後 來你來去做裁判 看紙面數據 哪個看起來比較好 比較有趣跟全面」→ PK-1（挑選核心＋比較腳本；沒接出題流程，現行不變）已 push，比較文件 docs/phases/PhasePK-1比較.md 交專案 PM 當裁判 → 裁判結論挑選模式勝，使用者「先修」：PK-1b（手寫不進候選、元素相合、打分細化、濫用詞、怪條件扣分）已 push（全量 pytest 17819、vitest 4676）；裁判挑選模式勝，使用者「先把挑選模式接到「升級三選一」和「完整技能」這兩處，用開關控制，預設打開 好」「我打算全面採用這個方式了」→ **挑選模式佇列**：PK-2（接升級三選一含白板格、完整技能；開關 skill_pick.yaml enabled 預設開；有沒有料；名稱詞組加嚴）已 push（全量 pytest 17851、vitest 4676）→ PK-3（閃現、重閃＋玩法 4.1.23 組合器不產兩種怪條件＋4.1.24 跟主路線改扣分、單薄擠掉、閃現命名只擋多字老套詞）已 push（單張格 50%→19%、請 LLM 49%→81%）；PK-4（許願池願望驅動＋4.1.25 閃現跨類借候選、描述擋多字老套詞）已 push（全量 pytest 17917、vitest 371 檔、build 0）。**2026-11-16 使用者「做完許願池就先停」（每週額度 94%）：目前停工，不派新段、不開審查、不跑模擬。****2026-11-19 復工**（使用者「已經重設額度了」，專案 PM 轉）：TL-1、TL-2、PK-4b、WC-1、SK-2 已合併（本機 main，未 push；WC-1 已回專案 PM）；SK-1、SK-3（計畫 PhaseSK-3計畫.md）在跑；SK-1 合併後全量檢查再 push（含專案 PM 的 6fdbf46ad 等）。**SK-2b 待排**（SK-1 合併後）：新原語接進出題（組合器排除表、llm_topic.core_exclude、LLM schema）＋工坊白名單＋玩法答覆（已答，玩法交接 4.1.28、26b489f65：水→目標格造水帶潮濕，油煙不換元素；推不動照字面；擴散一次只傳剩餘回合最多的一種〔同回合燃燒＞流血＞中毒〕、可連鎖；AI 不加分；接出題：鉤＝位移骨架核心直線 1 階可出，吸收＝打擊、蓄力／終結附帶＋光環核心只吸腳下，擴散只附在燃燒／流血／中毒效果上、組合器已帶才加，稀有度照 6.12）；SK-2 美術樣張已過審並併進 main（0115c2742）：**AR-SK2 待排**（SK-3 交件後派，免得前端戰鬥演出檔撞）照 docs/art/SK-2原語-移植需求.md 6 項（部件圖樣、三種演出、鎖鏈最小粗細、會擴散記號；浮字「擴散」、狀態卡標籤「會擴散」），截圖交美術 PM 驗收。SK-2b 已派（計畫 PhaseSK-2b計畫.md）。WC-1 待決 1、2、5 經專案 PM 轉玩法。PK-4 真模型量測卡住（LM Studio 載的是 Qwen 不是 Gemma，已請專案 PM 轉使用者換）；PK-4 待決玩法已答（玩法交接 4.1.27、0c7bc4d5c，雙關鍵字是使用者「A 至少一個（建議）」，其餘是玩法 PM 照做法定、使用者還沒看過，51285bda9）：2、3、4 不改；**WC-1 待排（TL 任一段交件就派，排在 PK-4b 前）**：使用者「哪些願望做不到、缺的是配方還是骨架 這個不能先出嗎?」→ 許願池每個標籤與每對標籤，用組合器跑各階級、稀有度的成功率；做不到的分成 (a) 缺配方、(b) 規則禁止、(c) 沒有原語；輸出 docs/phases/許願覆蓋表.md；只量不改程式，不用 LM Studio；完成回專案 PM 一行。寫新腳本算實作，用 Opus。**PK-4b 待排**（有空的 agent 名額就派，小段）：許願池三選一不顯示「偏離路線」；挑選模式（pick: llm，含許願、閃現、升級）也顯示「源晶推演」小標，說明句「這張技能的名字和描述由本機模型取；效果和數值都照規則出題。」，自由設計（source: llm）說明照舊。恢復後（週三額度重設後）佇列最前面，使用者「做」：TL-1 截圖比對腳本（新舊截圖逐張像素差異，列有變化的圖與比例，門檻做參數，以 docs/art/、docs/dev/ 現有截圖流程為準）與 TL-2「誰在等誰」掃描腳本（掃 docs/*PM交接.md 的「等…」「待…」「等使用者」，附檔案、行號、小節標題），各 1 個 agent 可平行、不改同一批檔案；接著：PK-4 真模型量測（LM Studio 當時沒載入模型；載好 Gemma 後跑 scripts/wish_compare.py run 再 report，注意許願可能逼近 10 秒門檻）；PK-4 待決 2～6 一次轉玩法；再接 #166 佇列；剩 19% 單張格要補配方，和完整盤點一起排。**#166 骨架擴充佇列**（使用者「8 B 其他都照建議」，06 6.38，玩法交接 4.1.26）：PK-4 之後 → SK-1（第 1 組：距離條件、移動過折扣接工坊、閃現側變與 10 種小變化〔補 PK-3 單張格〕、新方向打分優先製造卡、變奏讀本回合施放過 X）→ SK-2（第 2 組：吸收表面、鉤、推不動算撞擊、疾病擴散；以引擎為主，可和 SK-1 平行但不碰組合器／挑選／閃現檔）→ SK-3（第 3 組：你造的關鍵字被利用時、戰前佈置、重擲；接在 SK-2 後，同碰引擎觸發）；之後：下一招修飾、行動順序條件→ PK-4（許願池願望驅動，照 07 7.6、#165；完成後再決定自由設計程式刪不刪）；第 2～4 段等裁判結果；使用者「先補這個」：RC-0 組合器配方盤點已 push（cbc8380f6；真正的洞 82 空＋14 薄）；RC-1 補配方（會出題的空格 102→32、薄 14→4；Q12 1～4 階 200/200；Q4 照使用者「A」只修評估題）已 push；RC-1b（伴生／護主帶召喚物關鍵字、知道種類的呼叫端傳種類、潮濕被動測試放行經使用者「A」）已 push（7b8f61288，全量 pytest 17771、vitest 4676）。佇列新增：組合器 has_keyword 把戰場變奏算進去、三選一與退回路徑不算，不一致（只浪費嘗試），下次碰組合器順手統一；完整盤點下次碰組合器時用 scripts/recipe_census.py 重跑；模型與 config 等使用者選；下一個大段等專案 PM 問使用者（建議 05 5.12.8 段 3 碎晶之主部位）。GB-2～4a 已 push（a7dc58ca0）；PB-1f 已合併（PB-1e 美術結案，開發 PM 自看截圖）。其餘已 push（47043706a）。

**4. 待排（依序，注意檔案衝突）**：
> 11-13 清理：KW-2、RG-3、(e3f)(e3h)(e3i)(e3j)(e3k)(e3l)(e3m)(e3) 都已做完（RG-7、RG-8、FL-1h 合併；其中 (e3k) 已在 AF-1、(e3l) 已在 RG-4、PNL-4 可修 2 已在 LW-2b，派工前先 grep 報告確認沒做過）。
- 開發頁之後：要不要所有裝備都顯示形制名（RG-8 待決 1），等美術或玩法提出。LW-2 待決 6「現在不能用」那行加底色仍等美術答覆。
- (e3z) 已完成（NW-3d 11-14 合併）（另含玩法 4.1.16：LLM 提議與技能工坊造牆物件改用組合器候選）。原：下一個前端段：1600 寬噴口破的黑煙也壓到頭頂 HUD 下緣以下（美術 GB-4d 待決 1 更正，`docs/art/GB-4b驗收.md` 末節 0a93ed38；GB-4d 只做了 800，拿掉 `isCompactRow` 判斷即可）。
- (e3z2) 追蹤：熔心吐息改用自己的演出（現在第 2 階段播吸氣、第 3 階段冒熔岩柱；前端要多傳技能 id 給片段對應），等美術出吐息演出需求再排。
- (e3y) 已完成（GB-4d）。原：下一個前端段（美術 GB-4c 待決裁定，`docs/art/GB-4b驗收.md` 末節 1767c4d8）：第 2 階段熔心吸氣不畫熔岩柱（現在借用噴發片段）；800 寬噴口破第 4 格黑煙壓到頭頂 HUD 下緣以下。待決 2 照現狀。BM-1 待決 1 已在 GB-4c 做完。
- (e3s)(e3x) 已完成（NW-3、NW-3b 11-14 合併）。原 (e3x)：`prefer_far_from_leader` schema 加下限（下一個動內容 schema 的段）；單位表單「數值工坊 NW-3 才開」字面過時要改（下一個動工坊的段）。另 NW-3 待決 4：玩法 PM 定只在工坊加提示、物件 HP 不進技能預算，提示字見 `docs/玩法PM交接.md` 4.1.14（commit 0d05fe1a6），併下一個動工坊的段。
- (e3r)(e3t)(e3v) 已完成（BM-1 11-14 合併）。
- 美術 RG-5 裁定的「之後再做」：開墨線畫風時補 inkOffhand；動遮擋外框時高低差遮擋照實際外形。
(派工提醒，11-13 使用者「都裝」) 使用者層級已裝 skill：pixijs（v8 指南；碰 PixiJS 時用，派工單寫明「只讀這次要碰的 1～3 個主題檔，不要整份讀」）、property-based-testing（hypothesis 性質測試；守確定性重播、存檔讀回、正規化；不加新相依）。
(派工規定，11-13 使用者「ok那就照建議」) 目標瀏覽器：主力為電腦版 Chrome、Edge（Windows、Mac），畫面、功能與截圖驗收以這兩個為準；Firefox、Safari（含 iPhone、iPad 上所有瀏覽器）要能玩、外觀可降級，用新 CSS 寫法要確認舊瀏覽器只是變陽春不會壞；相容性一律查 caniuse 或 MDN，不照 modern-web-guidance 工具的資料。前端派工單都要寫這條。
(e3g) 選做，下次動到 skillgen/candidates.py 許願橋接時：搜尋上限只留一部分（例如一半）給「第 1＋第 2 關鍵字」，用完再試其他配對（玩法 PM 11-13，不另開段）。
(訊息規定，11-13 使用者「照做」) 給專案 PM 只在三種時候發：push 完成、需要使用者或其他 PM 決定、卡住；交件／合併／派工併進下次 push 訊息。內容超過約 10 行或有清單要轉，寫進 repo 檔（報告或交接某節），訊息只寫一兩行「請看某檔第幾節」＋要誰決定什麼。同一次 push 要轉玩法／美術 PM 的事合成一則。
(e) PB-1e、PB-1f 已 push（美術結案）。
(f) GB 段（巨型頭目＋灰燼之心）11-14 全部做完並 push（GB-1a～4b、2b～2d；4c 併進 4b），冷卻井 CW-1 也已 push。

**5. 本任新增的做法（照做）**：
- **2026-11-13 起不再排平衡量測或模擬報表**（使用者原話：「都不用再量數值了 寫個可能有問題記在.md上就好了 平衡 之後再說  先做遊戲」，專案 PM 轉達）：規格與派工不再要求模擬報表、比值表、倒下率報表；SR-1 後續（68 招補量、跨類別基準）不做。**仍要做**確定性與不變比對（沒帶新功能的戰鬥逐字不變、重播一致、快照逐鍵說明）。agent 在報告開「平衡疑慮」一節列出疑慮，PM 轉給玩法 PM 記進 `docs/design/平衡待查.md`（agent 不改 docs/design/）。
- 規格內的規則類待決一律經專案 PM 問使用者並附原話；agent 的保守解讀屬設計細節時交玩法 PM 確認（例 DD-1 八項、OB-7 三項）。
- agent 判斷「版號是否已 push」前要先 `git fetch`（DD-1b 曾因沒 fetch 誤判 /116 未 push）。
- 兩段都重產 `client/openapi.json`／`schema.d.ts` 時合併會衝突：用合併後的後端 `uv run python scripts/export_openapi.py`＋`corepack pnpm -C client gen:api` 重產，跑 `tests/api/test_openapi_snapshot.py` 與 typecheck 確認。
- 全量在 99% 附近偶發 xdist worker「node down: Not properly terminated」後卡死（11-13 兩次，log 停止寫入超過 10 分鐘就是卡住）：TaskStop 自己的全量再重跑。11-13 第三、四次（10 與 8 worker）都發生在三個 agent 同時跑測試和瀏覽器時；沒有 agent 時用 `--max-worker-restart=0` 單跑 pytest 全過、沒掛，推測是機器資源不夠而不是某個測試。全量盡量在沒有 agent 跑測試時跑；QF-3a 起 `scripts/check.py` 預設 12 worker，看門狗會自動收樹重跑。
- 不要在前景 Bash 用 `&` 丟背景（拿不到完成通知）；全量一律 `run_in_background`。
- 各段報告末節「開發 PM 裁定」記錄技術待決的決定。
- **寫「等某人」之前先查**（11-14 專案 PM，第三次清單過時造成白等／白做）：待排條目寫「等美術／玩法」前，先 grep 對方交接檔與 `docs/art/`（或 `docs/玩法PM交接.md`）確認真的還沒交；派工前先 grep `docs/phases/` 報告確認沒做過。每次 push 後順手掃一遍待排，把已交、已做的改成實際狀態。

### 3.0001 待轉其他 PM（開發 PM 寫，專案 PM 照這節轉；轉完可刪該列）

> 11-13 整理：KW-1、KW-1b、KW-2、RG-1、RG-2、RG-4、RG-5、AF-1、KW-3、WP-3b、RR-2、斷喉「每點」、平衡疑慮各列已由玩法 PM 4.1.1～4.1.7、平衡待查 22～26 條、美術 RG-4／5／6、RR-2、WP-3b 驗收處理完，已刪。

| 給誰 | 來源 | 要做的事 | 細節在 |
|---|---|---|---|
| 玩法 PM | CW-1 | 平衡疑慮（沒量）：原本開場就有的永久水現在要先打破井；AI 不會專門打井；(3, 4)、(7, 4) 兩口井的 3×3 會鋪到餘燼蜥腳下與殼縫攻擊位；熔心坑 12 場裡 8 場打破至少一口井 | `docs/phases/PhaseCW-1報告.md` 平衡疑慮 |
| 玩法 PM | GB-3 | 熔心坑改後 12 場都是敵方勝（改前 11 敵 1 我）；平衡疑慮：蜥蜴追遠＋熔岩濺落打最遠的人、殼縫更早破、近戰集中在兩側（都沒量），請記平衡待查 | `docs/phases/PhaseGB-3報告.md` 第 4、10 節 |

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

### 6.1 環境（2026-11-21 起在使用者的 Windows 機器上執行）

- **機器**：Windows 11（16 核，Git Bash）。PM 與實作 agent 都在這台的 Claude Code 執行，專案資料夾 `F:\PythonProject\LLM-MMO-TRPG`（Git Bash 寫 `/f/PythonProject/LLM-MMO-TRPG`；origin 指向 GitHub `huntertoby/llm-mmo-trpg`，私人）；每段合併後開發 PM 自己 `git push`。先確認 `git status` 正常、`uv run python --version` 是 3.12。
- **Python**：Git Bash 的 `python` 是 Windows Store 空殼（結束碼 49），一律 `uv run python`；`/tmp` 從 python 用不了，暫存檔放 scratchpad。不重裝（`uv sync`、`pnpm install` 已做好）。Mac 時期的說明見 `docs/archive/交接歷史-開發PM.md`。
- **前端**：Node 26 沒有 corepack，一律 `pnpm -C client <build|test|typecheck|gen:api>`；程式裡找 pnpm 的邏輯在 `pnpm_command()`（`src/trpg/cli/frontend.py`，corepack 缺席時退到 pnpm／npx）。
- **埠**：預覽伺服器不用 8000（使用者的 `trpg serve`）與 8001（本機 LLM）；自己開的 `uv run trpg serve --port <空埠>` 只用它的 PID 關，不用 `pkill`／`killall`（守則 13）。
- **本機 LLM**：LM Studio（MLX 引擎）＋ `gemma-4-12b-it` 在 `127.0.0.1:1234`；設定 `config/llm.local.toml`（gitignored），跑的時候帶 `TRPG_LLM_CONFIG=config/llm.local.toml`；MLX 不支援 schema `oneOf`，`oneof_as_anyof` 預設開（MAC-2），`uv run trpg llm ping` 會印伺服器接受的 schema 寫法；真模型測試 `uv run pytest -q tests/llm -m llm`。**模型載著時不要跑全量 pytest**（記憶體只剩約 30%）。
- **全量**：一般全量由 push hook 跑（`.claude/pm-workflow.json`；只改 `*.md` 的 push 略過檢查），PM 不另外手動跑；階段結束審查前跑一次 `uv run python scripts/check.py --full`。平行數 `TRPG_PYTEST_WORKERS`（QF-3a 起預設 12；全量期間不跑模擬；pytest 步驟走看門狗 `scripts/run_pytest.py`）。2026-11-06 全量：pytest 15217、vitest 3045。兩個 vitest 雜湊快照（`creaturePose.test.ts`、`inkDollSnapshot.test.ts`）在 MAC-1 改成固定 6 位小數，**回 Windows x64 要再跑一次**。
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
3. **派實作 agent**：`Agent` 工具，`subagent_type: pm-workflow:implementer`、`model: opus`、`isolation: worktree`、`run_in_background: true`（模型見 6.3）。prompt 範本見 6.4。
4. **等通知**，不要輪詢。使用者問進度時用 `git log --format='%cd %h %s' --date=format:%H:%M <base>..HEAD` 回報。
5. **功能驗收**（自己做，不只看報告）。**檢查分級（2026-10-23 使用者同意，專案 PM 傳達「好」）**：
   - **排版煙霧檢查（2026-10-24，流程改善 D；3-47 起有工具）**：凡是動到前端的段，合併後在內建瀏覽器跑 `window.__layoutSmoke`（`client/src/dev/layoutSmoke.ts`，純函式 `evaluate` 有 vitest；不需安裝任何套件）。步驟：① `pnpm -C client build`，背景啟動 `uv run trpg serve --port <空的埠>`（只關自己的）；② 每個情況先 `resize_window`，先 `javascript_tool` 執行 `localStorage.clear()`（有舊的一輪存檔時頁面會接回去、全部量不到），再 `navigate` 到 `/?dev=1&anim=0.1`（6F-1 起正式首頁只剩「開始」，煙霧檢查要在開發模式跑），再 `javascript_tool` 執行 `await window.__layoutSmoke.runCase("標題")` 取得 PASS／FAIL 表；三個情況：1600×900、1040×624、800×600（6A-4g 起拿掉 `shortBottom` 與拖曳線：戰鬥改成 HUD 疊在鋪滿的戰場上，改量 HUD 各塊不重疊、不出畫面）；③ 結束 `resize_window` preset `desktop`。量：結束回合寬度 ≥ 右欄 90%、播放列與按鈕在畫面內且一行、格子資訊卡提示列在底色內、「更多動作」選單開著時沒有說明卡、沒有 `.hint-tip` 外框。固定種子與起始武器（弓），結果可重現；全 PASS 才算過。新增版面元件時把它的量測加進 `layoutSmoke.ts`。`?anim=0.1` 可放慢動畫逐格截圖。
   - **一次出事就全面掃描（流程改善 E）**：同類錯誤第一次出現時，就全專案掃描同樣寫法並寫成常駐規則，不要只修那一處（反例：說明卡包一層造成的排版錯誤先後出了三次）。
   - **每段合併只跑快速檢查**：`ruff check`、`ruff format --check`、`mypy`、這段改到的 pytest 檔與相關前端測試、一場 `--log-json` ＋ `replay`；有改前端才跑 `pnpm build`。
   - **全量交給 push hook**（2026-11-21 使用者選「拿掉 PM 手動那次」，CLAUDE.md 第 11 條）：PM 不再手動跑一般全量；Phase 結束審查前照舊跑一次 `scripts/check.py --full`。
   - **同時進行的 agent 最多 4 個、不可改同一批檔案**（2026-11-04 使用者「同意，改第 11 條」）。**開發 PM 自己最多 3 個**，留 1 個給美術 PM 派畫圖與審查 agent（2026-11-04 晚，使用者：「感覺美術也要像開發PM那樣」，專案 PM 轉）。改到存檔欄位或技能池的段，相關測試要包含 `tests/test_architecture.py`；pytest 不用 `-n auto`。3-34 起：`scripts/check.py`（快速版，約 3 分鐘，不含 slow）、`scripts/check.py --full`（含 slow 與前端完整組合 `TRPG_FULL=1`，約 10 分鐘）；平行數 `TRPG_PYTEST_WORKERS`（QF-3a 起預設 12，可設 `auto`）。長指令要加 timeout（Bash 預設 2 分鐘會中斷）或背景執行。3E-2c 起：pytest-timeout（一般 300 秒、slow 1800 秒）；agent 在自己的 worktree 跑測試，加 `UV_NO_SYNC=1`（或 `uv run --frozen`）避免測試中途重裝套件。
   - 原寫法：`uv run python scripts/check.py`；挑一張地圖換一個種子跑 `trpg battle ... --log-json` 再 `trpg battle replay`；抽查一兩個關鍵設計（例如引擎內沒有浮點 log、沒有 `random`）。大型模擬（completion、matrix）由 PM 在驗收時於背景跑，不放進實作子階段。
6. **大階段結束時（例如 2E、Phase 3 結束）派審查 agent**（6.5），把結論中要處理的項目排進下一份規格。
7. **push**。
8. 向使用者回報：做出了什麼（附一小段戰鬥紀錄）、待決定項目怎麼處理、哪些需要使用者決定。

### 6.3 模型選擇

照 `CLAUDE.md`「角色分工」的模型規定：實作、修 bug、審查一律 `opus`；只有固定步驟、可核對的工作（`pm-workflow:finder` 找資料、跑檢查、截圖、量測、重產夾具、搬檔）可用 Haiku。

- **全部測試同一時間只跑一份**（2026-11-21 使用者：「好，請開發 PM 錯開跑」）：
  - 範圍：agent 交件前的 `check.py`、push hook 的檢查。
  - 平行的兩個 agent 由 PM 排先後，hook 推送時不能有 agent 在跑全部測試。
  - 有負載時，`tests/api/test_wish_api_wp2.py::test_text_wish_wait_then_act` 這類等待牆鐘的測試會逾時失敗。
- **合併與推送的順序（tree 戳記）**：
  - agent 的 `check.py` 戳記綁 tree。main 沒動過時，用 `--no-ff` 合併後 tree 和 agent 分支相同。
  - 合併後**先 push**，hook 會略過完整檢查。
  - 裁定是只改 `.md` 的 commit，再 push 一次（`skip_checks_if_only` 會略過）。
  - main 已經有別的改動、tree 本來就不同時，就把裁定一起寫好再推，只跑一次全量。

### 6.4 派實作 agent 的 prompt 範本

```
你是這個專案的實作者（implementer）。PM 已寫好規格，請實作 **Phase X｜名稱**。

專案位置：目前資料夾（main 分支，目前 HEAD 為 <hash>）。

請依序：
1. 讀 `CLAUDE.md`（特別是守則 11 節省 token、守則 12 複雜度）。
2. 讀 `docs/phases/PhaseX計畫.md`——這是你的規格。
3. 讀規格指定的前一階段報告與 `docs/design/` 主題檔（只讀指定的）。
4. 開發中只跑相關測試檔；每次 commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；開發中不跑完整的 `scripts/check.py`；pytest 平行最多 `-n 8`，**一律經看門狗跑：`uv run python scripts/run_pytest.py -q <路徑> -n 8`，不直接 `uv run pytest`**（QF-3a，說明見 `docs/dev/上手-測試.md`；worker 掛掉時回報保留的 `.claude/pm-logs/pytest/` 資料夾）。**交件前全部 commit 之後**，在自己的 worktree 跑一次 `uv run python scripts/check.py --all`（2026-11-22 TS-1 起 check.py 不加參數會依改動分流，分流戳記 hook 不認；CLAUDE.md 第 11 條 794866c78）。它跑全部非 slow 測試，經看門狗；通過會寫下 tree 戳記，PM 合併後 tree 沒變，push hook 就略過完整檢查（2026-11-21 使用者：「拿掉第二次重複的測試」）。跑完不要再改檔。再加規格指定的 slow 測試。同一時間只跑一份全部測試（使用者：「好，請開發 PM 錯開跑」）。**派工時 PM 二選一寫進 prompt**（2026-11-22，GS-3、HC-6b 兩次問完沒等回覆就交件，多一輪來回）：① 那段期間確定沒有別的全量：prompt 直接寫「全部 commit 後先 `git merge --no-edit main`，直接跑 check.py 和 slow，不用先問」；② 有別的 agent 也可能跑全量：prompt 寫「commit 完先 merge main，用 SendMessage 問 PM 能不能跑，**收到回覆前不要交件、也不要結束這一輪**（呼叫 SendMessage 後用完成通知等）」。Python 一律用 `uv run python`（Mac 每個 shell 先 `export PATH="$HOME/.local/bin:$PATH"`；Windows 直接打 `python` 是商店空殼）；前端 `pnpm -C client …`。
5. 不要 push。
6. 逐條自我檢查驗收條件（要有測試名稱或指令輸出為證）。依邏輯分 commit，結尾帶 Co-Authored-By 一行（依你的系統提示）。
7. 撰寫並 commit `docs/phases/PhaseX報告.md`；若新增了複雜度類 noqa（C901、PLR0911、PLR0912、PLR0915），在報告中逐一列出理由。

若改到前端：彈出卡片一律用共用浮動卡元件（本檔 6.5.1）；交件截圖照本檔 6.5.2（`docs/art/shots/<段>/`、≤ 10 張、jpg 80、單張 ≤ 300 KB），並在瀏覽器實測「從觸發元素滑進卡片 → 捲到底 → 釘住 → 關閉」（1600×900 與 800×600），結果寫進報告。

**對外資料帶「誰在看」**（CLAUDE.md 第 14 條，2026-11-22）：新增或修改送給玩家的視圖（API 回應、前端、LLM 敘事提示）時，先問「這個玩家看得到嗎」，依觀看者過濾陣營、視野、隱蔽、陷阱；完整資料只給 GM／除錯工具。舊視圖不用全面改（等多人階段），但新的不要再漏。

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
   新增或修改的對外視圖（API、前端、LLM 敘事提示）有沒有依觀看者過濾（守則 14：「這個玩家看得到嗎」）。
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
- **例外（2026-11-12 使用者選 A，原話：「A」；問題是「小圖示的放大特寫截圖，可不可以用 PNG 存進專案？」）**：只有**真 1 倍／最近鄰放大的特寫**可以用 PNG（驗收看單像素硬邊，jpg 會糊掉），仍算進每段 10 張、單張仍 ≤ 300 KB；情境圖、版面照舊 jpg 80。
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

- PM 對話本身是最大的隱藏成本（每一步都會重新處理整段對話）。**對話變長時，先更新本檔現況並 commit，再壓縮；不換對話。**
- 實作 agent 一律 Opus（6.3）；規格要小；agent 開發中只跑相關測試（CLAUDE.md 守則 11）。
- PM 讀文件只讀需要的：總覽 ＋ 對應的 `docs/design/` 主題檔 ＋ 最新一份報告。不要讀整份舊報告或舊對話。
