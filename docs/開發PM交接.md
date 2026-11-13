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

**2. 最後一次全量**：2026-11-14 8b5afebcf 全過，push 到 851d97f72（pytest 17481、vitest 4489、build 0），含 FL-1i（營火「轉型除外」、「強度」不拆；資訊卡計量 RG-5 已做）。前一次 11-13 push 67a9b8207 含 RG-5b、RG-7、RG-8、FL-1h。版號 LOG_FORMAT /125、WORLD_RULES_VERSION 33、CHAR_FORMAT /15。

**3. 執行中的 agent（分支）**：
- PB-1e（頭目部位美術移植＝(e)，移植需求 11-12 已交、OCL-1b 已合，不用再等）、FL-1j（斷行＝(e3o)），11-14 從 c149b1793 派出，各自 worktree，不碰同一批檔案。

**4. 待排（依序，注意檔案衝突）**：
> 11-13 清理：KW-2、RG-3、(e3f)(e3h)(e3i)(e3j)(e3k)(e3l)(e3m)(e3) 都已做完（RG-7、RG-8、FL-1h 合併；其中 (e3k) 已在 AF-1、(e3l) 已在 RG-4、PNL-4 可修 2 已在 LW-2b，派工前先 grep 報告確認沒做過）。
- 開發頁之後：要不要所有裝備都顯示形制名（RG-8 待決 1），等美術或玩法提出。LW-2 待決 6「現在不能用」那行加底色仍等美術答覆。
- (e3o) 已完成（FL-1j 11-14 合併）。原：下一段動到閃現／重閃／成長面板字時（美術 11-14 FL-1i 待決 3，docs/art/FL-1b驗收.md 末節）：「傷害」「轉型」加進不可拆詞；數字和單位不拆（例「1 回合」）；成長面板藍字「可以重閃第 3 格轉型」斷在「轉／型」一起改。
- (e3n) 已完成（FL-1i 11-14 push）。原：11-14 派 FL-1i：營火「轉型除外」、轉型句「強度」不可拆（美術 4865d5d38）、單位資訊卡層數換 HUD 計量（KW-3 待決 3，docs/art/RG-4驗收.md 末節）。原條：下一段動到營火或重閃字時：營火說明行「新選項整招不會比現在弱」加「轉型除外」，改字與 1 個測試（玩法PM交接 4.1.8，FL-1h 待決 7）。
- 美術 RG-5 裁定的「之後再做」：開墨線畫風時補 inkOffhand；動遮擋外框時高低差遮擋照實際外形。
(派工提醒，11-13 使用者「都裝」) 使用者層級已裝 skill：pixijs（v8 指南；碰 PixiJS 時用，派工單寫明「只讀這次要碰的 1～3 個主題檔，不要整份讀」）、property-based-testing（hypothesis 性質測試；守確定性重播、存檔讀回、正規化；不加新相依）。
(派工規定，11-13 使用者「ok那就照建議」) 目標瀏覽器：主力為電腦版 Chrome、Edge（Windows、Mac），畫面、功能與截圖驗收以這兩個為準；Firefox、Safari（含 iPhone、iPad 上所有瀏覽器）要能玩、外觀可降級，用新 CSS 寫法要確認舊瀏覽器只是變陽春不會壞；相容性一律查 caniuse 或 MDN，不照 modern-web-guidance 工具的資料。前端派工單都要寫這條。
(e3g) 選做，下次動到 skillgen/candidates.py 許願橋接時：搜尋上限只留一部分（例如一半）給「第 1＋第 2 關鍵字」，用完再試其他配對（玩法 PM 11-13，不另開段）。
(訊息規定，11-13 使用者「照做」) 給專案 PM 只在三種時候發：push 完成、需要使用者或其他 PM 決定、卡住；交件／合併／派工併進下次 push 訊息。內容超過約 10 行或有清單要轉，寫進 repo 檔（報告或交接某節），訊息只寫一兩行「請看某檔第幾節」＋要誰決定什麼。同一次 push 要轉玩法／美術 PM 的事合成一則。
(e) PB-1e：**11-14 已派**（美術移植需求 `docs/art/頭目部位-移植需求.md` 11-12 就交了，本條曾誤寫「等美術」造成白等）。資訊面板移植已由 PNL 系列做完（PNL-4 結案）。
(f) 段 2 不動巨型頭目＋灰燼之心（5.12.8；前端在 OCL-1 之後，已滿足）：**11-14 開發 PM 寫規格中**（`docs/phases/PhaseGB計畫.md`），不等任何人。

**5. 本任新增的做法（照做）**：
- **2026-11-13 起不再排平衡量測或模擬報表**（使用者原話：「都不用再量數值了 寫個可能有問題記在.md上就好了 平衡 之後再說  先做遊戲」，專案 PM 轉達）：規格與派工不再要求模擬報表、比值表、倒下率報表；SR-1 後續（68 招補量、跨類別基準）不做。**仍要做**確定性與不變比對（沒帶新功能的戰鬥逐字不變、重播一致、快照逐鍵說明）。agent 在報告開「平衡疑慮」一節列出疑慮，PM 轉給玩法 PM 記進 `docs/design/平衡待查.md`（agent 不改 docs/design/）。
- 規格內的規則類待決一律經專案 PM 問使用者並附原話；agent 的保守解讀屬設計細節時交玩法 PM 確認（例 DD-1 八項、OB-7 三項）。
- agent 判斷「版號是否已 push」前要先 `git fetch`（DD-1b 曾因沒 fetch 誤判 /116 未 push）。
- 兩段都重產 `client/openapi.json`／`schema.d.ts` 時合併會衝突：用合併後的後端 `uv run python scripts/export_openapi.py`＋`corepack pnpm -C client gen:api` 重產，跑 `tests/api/test_openapi_snapshot.py` 與 typecheck 確認。
- 全量在 99% 附近偶發 xdist worker「node down: Not properly terminated」後卡死（11-13 兩次，log 停止寫入超過 10 分鐘就是卡住）：TaskStop 自己的全量再重跑。11-13 第三、四次（10 與 8 worker）都發生在三個 agent 同時跑測試和瀏覽器時；沒有 agent 時用 `--max-worker-restart=0` 單跑 pytest 全過、沒掛，推測是機器資源不夠而不是某個測試。全量盡量在沒有 agent 跑測試時跑，用 8 worker。
- 不要在前景 Bash 用 `&` 丟背景（拿不到完成通知）；全量一律 `run_in_background`。
- 各段報告末節「開發 PM 裁定」記錄技術待決的決定。
- **寫「等某人」之前先查**（11-14 專案 PM，第三次清單過時造成白等／白做）：待排條目寫「等美術／玩法」前，先 grep 對方交接檔與 `docs/art/`（或 `docs/玩法PM交接.md`）確認真的還沒交；派工前先 grep `docs/phases/` 報告確認沒做過。每次 push 後順手掃一遍待排，把已交、已做的改成實際狀態。

### 3.0001 待轉其他 PM（開發 PM 寫，專案 PM 照這節轉；轉完可刪該列）

> 11-13 整理：KW-1、KW-1b、KW-2、RG-1、RG-2、RG-4、RG-5、AF-1、KW-3、WP-3b、RR-2、斷喉「每點」、平衡疑慮各列已由玩法 PM 4.1.1～4.1.7、平衡待查 22～26 條、美術 RG-4／5／6、RR-2、WP-3b 驗收處理完，已刪。

| 給誰 | 來源 | 要做的事 | 細節在 |
|---|---|---|---|
| 美術 PM | FL-1j | 複驗 `docs/art/shots/FL-1j/`（「傷害」「轉型」不拆、數字＋單位黏合、藍字整段換行）；待決 2：一般詞仍會在字中間斷（一輪 800「本／回合」、408「雷／電」、376「點／燃」「原／本比」「發／動」），要不要處理、做到哪裡 | `docs/phases/PhaseFL-1j報告.md` 第 4 節、待決 |

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

- PM 對話本身是最大的隱藏成本（每一步都會重新處理整段對話）。**對話變長時（例如完成一個大階段後），更新本檔並請使用者開新對話。**
- 實作 agent 依 6.3 選模型（預設 Sonnet）；規格要小；agent 開發中只跑相關測試（CLAUDE.md 守則 11）。
- PM 讀文件只讀需要的：總覽 ＋ 對應的 `docs/design/` 主題檔 ＋ 最新一份報告。不要讀整份舊報告或舊對話。
