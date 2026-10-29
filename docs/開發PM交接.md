# 開發 PM 交接文件

> 給接手的 **開發 PM**（新對話中的 Claude）。最後更新：**2026-10-28**。**只讀本檔就能接手**；需要時再讀 `CLAUDE.md`、`docs/專案計畫.md`（總覽）與本檔指到的計畫檔。
> 現況一句話（2026-10-29 第五任，晚）：**3J、C 畫風、3R、3T 整理、Phase 4 的 4-L6～4-L8b 與 4-L6b 完成；4-L9 真模型評估依使用者指示延後（「4-L9先不做 改天」），等專案 PM 通知**。沒有 agent 在跑。下一步見 **3.0000**。

---

## 1. 你的角色與組織

- 2026-10-22 起的架構：**專案 PM** 對接使用者，底下有 **玩法 PM**（`docs/玩法PM交接.md`）、**開發 PM**（本檔）、**美術 PM**（`docs/美術PM交接.md`）。各 PM 以 `SendMessage` 互相傳話。
- 開發 PM 的工作：把玩法／美術／使用者的決定寫成階段規格（`docs/phases/`）、派實作 agent、驗收、合併、push、回報。**不要自己寫大量程式碼**，實作交給 agent；小修（幾行）可以自己做。
- 分工：玩法 PM 只改 `docs/玩法PM交接.md`、`docs/玩法決定紀錄.md`、`docs/design/`；美術 PM 在自己的分支改 `docs/art/`、`docs/美術PM交接.md`，**由開發 PM 併進 main**；開發 PM 改 `docs/phases/`、本檔、程式，以及 `docs/專案計畫.md` 的決定紀錄（使用者同意後）。
- 玩法決定的狀態：排入或完成時，改 `docs/玩法PM交接.md` **決定總表那一列**（「已排入（階段 X）」→「✅ 已完成」）。
- 使用者（GitHub：huntertoby）是 **最終決策者**，不是工程師。**所有回覆一律用繁體中文**，精簡、有結論，用表格比較選項；設計問題先問，技術細節（架構、測試、數值初值、排程、拆段）可直接決定並簡短說明。**下載任何外部檔案前要使用者明確同意**（3-13 的 Kenney 已同意，之後已移除）。

## 2. 專案現況

| 階段 | 狀態 | 規格／報告 |
|---|---|---|
| Phase 0、1（基礎、戰鬥核心、環境、掩護） | ✅ | `Phase0計畫.md`、`Phase1計畫.md`、`Phase1C計畫.md` |
| Phase 2A～2H（技能資料、解譯器、預算、組合器、模擬器、補模板 A／B、整理） | ✅ | `Phase2*計畫.md`／報告 |
| Phase 3C、3D（補模板 C、D：撥開、源力、傳說、召喚、區域、背刺……） | ✅ | `Phase3C計畫.md`、`Phase3D計畫.md`（第 0 節為驗收與決定） |
| Phase 3E 審查後整理 | 3E-1 ✅；**3E-2、3E-3 未做（Phase 4 前）** | `Phase3E計畫.md` |
| Phase 3F 技能工坊、靶場、複合技能 | ✅ | `Phase3F計畫.md`（0.6 含 3F-4b 瀏覽器補測） |
| **Phase 3 網頁 ＋ roguelite** | **3-1～3-17 全部 ✅**（見下表） | `Phase3計畫.md`（第 0 節與各節末的「驗收」小節是決定與驗收紀錄） |

Phase 3 各段（`Phase3計畫.md` 節號；報告 `Phase3-*報告.md`）：

| 段 | 內容 | 驗收紀錄 |
|---|---|---|
| 3-1～3-4b | API、前端骨架、戰鬥 UI、反應詢問、隊友指令 | 0.6～0.10 |
| 3-5a／b／c、3-6 | 一輪（存檔 `trpg-run/1`、Boss 地圖 `bandit_lair`、網頁畫面、自動存檔、重新整理接回） | 0.12～0.15 |
| 3-7 | 體質加 HP、升級 +5% HP、中毒／流血體質抵抗（玩法 #16） | 10.4 |
| 3-8 | 戰鬥畫面重新配置（#17） | 11.4 |
| 3-9a／b | 地圖回饋（浮動數字、字樣、連線、位移動畫）、分組戰鬥紀錄（#18） | 12.4 |
| 3-10 | 慢速、可拖曳版面與地圖縮放、推不動的原因（含修好「物件在左／上緣時 API 500」） | 13.5 |
| 3-11 | 暫時障礙（`create_obstacle.duration`）、`smoke` 表面（#19） | 14.4 |
| 3-12 | 技能特效（元素 × 形狀 × 遠近自動組合，`battle/vfx.ts`） | 15.4 |
| 3-13 | Kenney 原型美術（**已被 3-16a 取代、素材已移除**） | 15.5 |
| 3-14 | 高度表現（崖面、懸崖線、高處陰影） | 17.0 |
| 3-15 | 滑過格子的地形資訊卡（說明由 `trpg.narrative.tile_info` 從資料產生，#20） | 16.4 |
| 3-16a／b | 美術 PM 的程式繪製版：地形、表面、物件（`render/art*.ts`、`terrainArt.ts`、`objectArt.ts`）、紙娃娃小人（`render/paperdoll.ts`、`appearance.ts`；`UnitView.weapon_id`） | 17.2、17.3 |
| 3-17 | 組裝式技能圖示（`SkillCard.icon` 由 `trpg.narrative.skill_icon` 推導；`render/skillParts.ts`、`skillIcon.ts`，#21） | 18.3 |
| 其他 | 白板主角 `build_blank_warrior`、`build_blank_mage`（`blank: true`，不進模擬） | commit c09c339 |

- 測試：**約 4100 個 pytest ＋ 657 個 vitest**（3-27 後）（`check.py` 一併跑，本機約 1–2 分鐘）；`LOG_FORMAT` 為 `trpg-battle-log/46`（3-20～3-29、3G 之後；舊紀錄與戰鬥中存檔無法讀取，已接受）。
- 內容：22 個模擬用 build ＋ 2 個白板主角（`content/sim/builds.yaml`）；手寫技能 152 個；正式地圖 10 張 ＋ 靶場 `training_range` ＋ Boss 地圖 `bandit_lair`。
- 主要指令：`trpg battle --map <id> --seed <n> [--log-json f]`、`trpg battle replay f`、`trpg map list`、`trpg sim maps|matrix|skills|completion`、`trpg skills list|budget|random`、`trpg run new|auto|show`、`uv run trpg serve`（網頁，預設 8000 埠）。
- 一輪的平衡現況：AI 代打種子 1～10 勝 2 場（3-7 後）。

## 3. 下一步

### 3.0000 接手第一件事（2026-10-29 第五次，最新，優先於下面各節）

> 第五任開發 PM 的 session：`local_ab425b7d`（由專案 PM `local_69ff6dd8-1a56-4d3a-950d-054825e07625` 啟動）。**下面 3.000 第 5 點的各 PM session id 已過期**：專案 PM `local_69ff6dd8-1a56-4d3a-950d-054825e07625`、玩法 PM `local_9c79efb1-a93e-4b28-8a2f-7c97ec50b846`、美術 PM `local_cb74dfda-1832-4c4b-bf87-d4dcb9fbf335`（美術分支 `claude/art-pm-fcab45`）。

1. **完成**（驗收紀錄）：3-54c／d／e（`Phase3計畫.md` 66～68 節）；3J-1a～3J-5、3J-4b／4c（`Phase3J計畫.md` 4.x）；C-1a～C-3（`PhaseC畫風計畫.md`，美術 PM 檢查在 `docs/art/*檢查.md`）；3R-1～3R-3c（`Phase3R計畫.md` 4.x）。技能 301；`LOG_FORMAT` `/85`；存檔 `trpg-run/7`；最後全量 pytest 8527、vitest 1103。
2. **2026-10-29 晚更新**：3T（1～8）、3R-4（鱗族 #68）、4-L6／6b／7／8／8b 全部完成並 push；技能 301、`LOG_FORMAT` `/87`、存檔 `trpg-run/10`；最後全量 pytest 8766、vitest 1145。**下一步：等專案 PM 通知使用者開本機模型後做 4-L9**（`Phase4計畫.md` 表格 4-L9 列與 3C 節 4～6）；不進平衡階段或 Phase 5。派工的 pytest 一律 `-m "(slow or not slow) and not llm"`。
2b. **（舊）進行中**：Phase 3T（`Phase3T計畫.md`，兩份後段審查的整理）：3T-1（change 種類與預算旋鈕進 YAML，opus）、3T-4（前端整理）；之後 3T-2 → 3T-3（可和 Phase 4 平行）→ **Phase 4 從 4-L6 起**（`Phase4計畫.md`）。
3. **待使用者決定**：鱗族「水與冰面移動不花額外點數」（引擎本來沒有額外花費，被動實際只有不滑倒；玩法 PM 已交專案 PM）。
4. **待辦（不擋 Phase 4）**：AI 不施放純地形技能（大地崩陷）；`Phase3T計畫.md` 第 1 節末的延後項；晶能義體人辨識樣張（美術 PM 之後出）；召喚物實戰外觀美術 PM 尚未看（等有可選的召喚角色）。
5. **經驗**：兩個 agent 同時遞增 `LOG_FORMAT` 幾乎每次都撞，合併時取較大＋1，用 `git grep "battle-log/NN"` 找齊字面值（含 `endswith("/NN")`），`runner.py` 文件字串要補齊每一版；agent 一次跑全部 tests 曾讓 xdist 卡住，派工 prompt 要寫「不要一次跑全部 tests、跑測試時不要同時改檔」；審查 agent 沒用 worktree 時會直接 commit 到 main，合併前看 `git status`。

### 3.000 接手第一件事（2026-10-28 第四次交接，最新，優先於下面各節）

> 上一任開發 PM：`local_e6fcf372`（2026-10-24 接手，做到 3-54b 暫停；使用者換對話）。**只讀本節就能開始**，細節再看本節指到的檔案。和使用者、各 PM 一律用繁體中文。

**1. 現況（交接時）**
- main ＝ origin/main ＝ `030fa5ef`（含本節更新後的 commit），工作區乾淨（只有不明的 `tmp_x`，不是開發 PM 建的，不要動）。**沒有任何 agent 在跑**。使用者在 3-54b 後暫停：「做到 3-54b 先停 token 要沒了」——**恢復前不要派新段**，等專案 PM 轉達。
- 最後一次全量（除 `llm`）：pytest 7873、vitest 994、mypy、lint-imports、重播全過。`LOG_FORMAT` `/77`；存檔 `trpg-run/6`；內建技能 268＋後續段落新增（以 `content/skills/` 為準）。
- worktree：`git worktree list` 還有 5 個舊的 locked 登記（`agent-a1403…`、`a423…`、`a57d…`、`a9173…`、`aa62…`，前任遺留，分支已合併或作廢）與 3 個美術 PM 的 worktree（`art-pm-20b75c`、`art-pm-5ea9fb`、`art-style-sample-404539`，**不要刪**）。`.claude/worktrees/` 底下約 38 個資料夾是已刪分支的殘留（檔案被鎖、`git worktree remove` 刪不乾淨），可在沒有 agent 時手動清，刪之前確認裡面的 `client/node_modules` **不是連結**。

**2. 恢復順序**
1. **3-54c 種子技能**（`Phase3計畫.md` 第 64 節）：風 6、毒 6、大地 4、神聖 2（06 6.33）；「清風」用清除表面效果（#63，不靠風元素、不觸發擴散）；**補完毒種子後刪 `content/skill_keywords.yaml` 中 `poisoned` 的 `start_hidden`，並拿掉 3-53 的保守測試標記**（`EXTRA_KEYWORDS`、`test_pools_24c.py` 的 `short == {"poisoned": 1}`、`test_keyword_start.py` 起始技能剛好 1 招）。
2. **3J 形態**（`Phase3J計畫.md`）。
3. **3R 種族與出身**（`Phase3R計畫.md`；**2026-10-29 使用者「外觀先等」：3R-3a／b 種族外觀（含成對武器錯開小修）與 3J-5 先不做，等 C 手繪墨線畫風定案〔美術 PM `claude/art-pm-fcab45`〕再用新畫風做**；3R-3a 含 3S-3 美術小修：成對武器遠側的手槍、斧、錘往前上方錯開約 3px；種族角可用 `paperdollSideGear.drawHornSide`、側面種族部件掛 `SideHooks.race`）。
4. **Phase C 紙娃娃 C 畫風**（`PhaseC畫風計畫.md`，2026-10-29 排入）：C-1a、C-1b、C-2 要在 3J-5 與 3R-3a／b 之前，C-3 召喚物（使用者 2026-10-29 決定做）排在 C-2 之後；可和 3J、3R 的規則段平行。
5. **Phase 4**（4-L6 起，`Phase4計畫.md`）。

**3. 待玩法 PM 決定（恢復時先問）**
- 3-54b：「大地元素」定義（現為標籤 `earth` 或效果元素 `earth`）；工坊不能選標籤，純地形技能做不出來；石膚、震波沒限大地；震波仍要命中；石膚、震波、擴散 2 格預算初值；`content/workshop_text.yaml` 新增的震波與擴散格數說明是初稿。
- 3-55：工坊沒有主角手上武器的來源（App 沒傳 `heroWeapon`，API `/api/workshop/options`、`/api/workshop/check` 已支援 `weapon`）；無持有者卡片「縮放：武器的屬性」仍泛稱；「手持指定武器」命名。
- 各段驗收紀錄（含已回覆的待決）：`Phase3計畫.md` 51～65 節（含 60b、60c、62b、63b、64.1）、`Phase3I計畫.md` 4.1～4.6、`Phase3K計畫.md` 5.1～5.4、`Phase3S計畫.md` 檔尾。

**4. 平衡待辦**：本檔 3.3 的 B1～B25（使用者：平衡延後，驗收時只判斷並記錄、不調）。

**5. 流程（照做）**
- **流程改善 A～F**（2026-10-24 使用者同意，細節在本檔 6.2 與 6.5.1）：A 決策影響盤點（寫規格前先盤點受影響的既有功能）；B 行為一致測試（規則句一律要實際跑引擎的表格測試）；C 已寫入設計文件的決定只有使用者能改（PM 之間不在對話裡放寬，玩法 PM 也不能自己改已寫入的規則，要問使用者）；D 排版煙霧檢查（`window.__layoutSmoke`，先 `localStorage.clear()`）；E 一次出事就全面掃描；F 禁止結束不是自己啟動的程序。
- **派工**：同時最多 2 個 agent；規格寫明 `tests/engine` 與 `-m "slow or not slow" tests/cli --timeout=3000`；agent 開工先 fast-forward 到 main；不准建 `client/node_modules` 連結（`corepack pnpm -C client install --offline --frozen-lockfile`）；agent 回報後若顯示「waiting on its own background work」用 `TaskStop`。
- **合併**：`git merge --no-ff` 後在 main 跑「除 llm 的全量」（`UV_NO_SYNC=1 uv run pytest -q tests -n 8 -m "not llm" --timeout=3000`，加 ruff、format、mypy、lint-imports、`corepack pnpm -C client build`、vitest、一場重播；約 8～20 分，背景執行），**全過才 push**；背景檢查跑時不要改工作區。兩個 agent 同時加技能或遞增 `LOG_FORMAT` 必撞：`skill_icons.json`（`uv run python -m tests.narrative.icon_fixture`）、CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`）取 `--theirs` 再重產；`LOG_FORMAT` 取較大＋1、`runner.py` 文件字串兩段都保留、測試字面值一起改；改了 API 型別要重產 OpenAPI（`uv run python scripts/export_openapi.py` → `corepack pnpm -C client gen:api`）並修 vitest 夾具。
- **已知地雷**：
  - 前端指令一律 `corepack pnpm -C client …`（在 `client` 資料夾內執行 build／vitest）；`node_modules` 壞了用 `corepack pnpm -C client install --offline --frozen-lockfile --force` 從本機快取還原，不要下載。
  - Windows 路徑：`Path.resolve()` 很慢（內容庫已快取 `bundled_content_dir`）；Git Bash 下用 `/f/...`，PowerShell 與工具參數用 `F:\...`；暫存腳本放 scratchpad 或 `$TEMP`，不要放專案資料夾（會被 ruff 掃到）。
  - 不要 `taskkill /IM python.exe`、`pkill` 之類；只停自己的 PID。預覽伺服器不要用 8000（使用者）、8001（本機 LLM）——`.claude/launch.json` 有 `trpg-serve-verify`（8011）。
  - **兩個開發 PM 同時動 main 的教訓**：2026-10-24 交接時前任其實還在執行、直接在主資料夾改檔，差點互相覆蓋。接手先 `git status`、`git worktree list`、`list_sessions` 確認前任是否 idle，有人在動就停手並問專案 PM 由誰做。其他 PM（專案、玩法）也會在 main 上 commit 並 push，可能把你尚未全量檢查的合併一起推出去——合併後盡快跑全量。
  - 測試偶發：召喚物 HP 斷言在多 agent 搶 CPU 時偶發失敗，單獨重跑會過；`tests/cli/test_output_snapshots.py` 單一測試接近 300 秒，一律加 `--timeout=3000`。
- **回報**：只在「驗收合併完成（附給使用者的檢查重點）」「卡住」「需要決定」時傳給專案 PM `local_46ffc72c-28dd-48aa-9eb7-f1724ef32432`；規則問題直接問玩法 PM `local_e3a02b51-b04a-41ac-a356-7aef049c8be2`；美術驗收找美術 PM `local_1501da38-7be4-4aad-8915-c16e592f04f3`（分支 `claude/art-pm-5ea9fb`，由開發 PM 併進 main）。

### 3.00 接手第一件事（2026-10-23 第二次交接，最新，優先於下面各節）

**目前停在哪（使用者暫停）**：使用者：「做完這些後就先停」（專案 PM 轉達）。**沒有任何 agent 在跑**；main 與 origin 一致、`check.py --full` 在 3-37b 後跑過（5178 pytest＋816 vitest，唯一失敗是雲嶺改名造成的 CLI 快照，已更新 `75b8a95`）。**恢復前不要派新段**，等專案 PM 轉達使用者恢復。

**這一輪完成的（2026-10-23）**：
| 段 | 內容 | 驗收紀錄 |
|---|---|---|
| — | `check --full` 28 分 → 6 分 38 秒（`bundled_content_dir` 快取） | 本節下方 |
| 4-L4 | schema 子集、`available` 格式、`build_proposal_prompt` | `Phase4計畫.md` 4.4 |
| 4-L5 | 重試迴圈、預算器補數值、引擎修補、三層退回、`trpg llm propose` | 4.5（第一次真模型小測試：退回 50%） |
| 4-L5b | 隱藏組合規則進 YAML／schema（`form`）、狀態依稀有度篩、先修可修再回報、骨架資訊進 `available` | 4.6（第二次小測試：種子 0 退回 10%） |
| 4-L5c | 開關只能 true、列舉去掉不能施加的狀態、估算不算 schema、專屬錯誤代碼、CLI 不出不可能題目 | 4.7 |
| 3-35 | 前端字型 Noto Sans TC（400／700 自帶） | `Phase3計畫.md` 39.1 |
| 3-36a／b | 狀態圖示、戰場效果（美術 PM 驗收通過） | 40.1.1、40.2.1 |
| 3-37a／b | 區域主題底層、雲嶺換皮（`bridge_chasm`→雲海吊橋、`dark_forest`→竹林） | 41.1.1、41.2.1 |
| 3-38 | 可燃標記平時淡化（使用者選 C） | 42.1 |
| 小修 | 嘲諷 `control_group: mental`＋`budget_points` 3（玩法 PM）；拖曳線位置（`358a43a`）；格子資訊卡換格 80ms（`f64bb3b`，規則見 6.5.1）；雲海山谷調暗 | 各自 commit |

**恢復後的下一段（依序）**：
1. **4-L6**：接進候選產生器（`llm` 來源、寫進 run 紀錄、重播不呼叫 LLM、Mock 失敗仍 3 個候選、設定可關 LLM）＋ **3C 節原語多樣性 1～3**（題目指定核心原語、輪替選單、run 內配額；使用者 2026-10-23 決定）＋ **LLM 技能強制帶題目關鍵字**（4-L5 待決 #1；小測試的 `keyword.required`）。規格要先寫進 `Phase4計畫.md`（照 3A～3E 格式）。可與 4-L7（名稱與敘事）平行。
2. 4-L8（開放更多結構；`budget.over`／無旋鈕結構 44／161、AP／冷卻旋鈕、`unit_then_tile` 等旗標）→ 4-L9（真模型評估＋3C 節強制／自由測試）。
3. ~~3-41a／b 說明文字整修~~ **已完成（2026-10-23，`Phase3計畫.md` 45.3～45.4）**。
3a. ~~3H 屬性系統~~ **已完成（2026-10-24）**：3H-1～3、3H-5（耐力每回合 +5、戰後回滿）、3-41c；驗收見 `Phase3H計畫.md` 第 5、6 節。`LOG_FORMAT` 現為 `/61`。
3b. ~~3-41c~~ 已完成（`Phase3計畫.md` 45.6）。
3c. **排程（2026-10-24，使用者定）**：3H-7＋3H-8 → 3-47 → **3I 第二批武器＋魔劍士**（`Phase3I計畫.md`，1～4）→ **3J 形態系統**（`Phase3J計畫.md`，約 4.4～5.2 段）→ Phase 4（4-L6 起；含「自然」主題）。待排：戰後裝備三選一（玩法 PM 備設計中）。三個小原語中的定向蓄力已提前到 3J，其他兩個排在平衡階段之後。
4. 介面／美術：**3-37c 雲嶺服裝部件**（`Phase3計畫.md` 41.3，後放）；五區其他區等美術 PM。
5. **3E-3**（`Phase3E計畫.md` 3.2）可穿插；平衡 B1～B9（本檔 3.3）延後。

**本機模型（真模型測試）**：`F:\WSL\settings.ini` PORT 已改 8001（使用者 2026-10-23）；`config/llm.toml` → `http://localhost:8001/v1`、`swift`、**`enable_thinking=false`**（Qwen3 預設思考會用光 2048 輸出、回空）。strict JSON schema（含 `$ref`／`oneOf`，根層 `oneOf` 也可）vLLM 接受；schema 不佔 prompt token（最大題目實際 2,525）。關思考約 4～13 秒／次。測試：`uv run trpg llm ping`、`uv run trpg llm propose -n 10 --seed 0`（小測試）、`uv run pytest -m llm`。開發與自動測試一律 Mock；模型由使用者用 `F:\WSL\start.bat` 啟動，連不上或顯存不足時回報專案 PM，不要請使用者改 settings.ini。**預覽伺服器不要用 8000（使用者）或 8001（模型）**：`.claude/launch.json` 有 `trpg-serve-verify`（8011）。

**`check.py --full` 變慢（已解決，2026-10-23，`dabb5a9`）**：原因是 3E-2f 起每次建構 `EffectSpec` 都經 `default_content_dir()` 做 `Path.resolve()`（Windows 很慢，`run auto` 一半時間在這）；`bundled_content_dir()` 加 `@cache`、`run auto` 十種子測試改參數化。`--full` 28 分 → **6 分 38 秒**。之後若再變慢，先用 `--durations=30` 加 cProfile 單跑 `trpg run auto --seed 1` 找熱點。

**待查（2026-10-23 發現）**：`tests/engine` 裡召喚物 HP 的兩個測試（石像 `summon_golem`、骷髏 `summon_skeleton_warrior` 的 max_hp 斷言）在 `tests/roguelite`～`tests/engine` 九個資料夾一起 `-n 8` 時偶發失敗、重跑通過；單獨或兩兩組合都過 → 疑似某測試改了共用狀態（3-41a 的 `content/summons.py` 或內容庫快取）沒還原。下次全量檢查若再出現就追。

**驗收動畫的方法（2026-10-23 起）**：網址加 `?anim=0.1`（再慢 10 倍，可配播放列「極慢」再 ×5），內建瀏覽器每張截圖約 1 秒也能抓到移動中途的畫面。

**這一輪學到的**：合併前「相關測試」範圍要含 `tests/skillgen`（嘲諷改動時漏跑 `test_budget` 寫死的點數）；`.claude/worktrees/` 舊資料夾會累積（2026-10-23 清過 42 個，約 3 GB），合併後記得 `git worktree remove` ＋ 刪分支；主資料夾有不明的 `tmp_x`（不是開發 PM 建立的，沒動）。

**其他待辦位置**：
- **3E-3**（可在 Phase 4 期間穿插，一次最多 2 個 agent）：`Phase3E計畫.md` 3.2。
- **平衡階段清單 B1～B9**：本檔 3.3（使用者：平衡延後，驗收時仍判斷並記錄數值、不調）。
- 審查全文：`docs/phases/Phase3審查-Python.md`、`Phase3審查-前端.md`。

**常駐規則（都在本檔，照做）**：
- 回報：PM 之間只在「某段驗收合併完成（附給使用者的檢查重點）」「卡住」「需要決定」時傳訊息；不傳告知類（6.2 開頭）。
- 檢查：每段合併只跑快速檢查（ruff、format、mypy、相關測試、一場重播、有改前端才 `pnpm build`）；全量 `check.py --full` 每 2～3 段一次（6.2 第 5 點；CLAUDE.md 守則 11）。同時最多 2 個 agent；agent 不跑全量；長指令加 timeout 或背景執行；agent 在自己的 worktree 跑並用 `UV_NO_SYNC=1`。
- git：共用資料夾只用 `git pull --ff-only`，不 rebase；push 前 `git log origin/main..HEAD` 確認沒有別人的 commit（6.6 第一條）。
- 直接打 `python` 可能是 Windows 商店空殼，一律 `uv run python`；臨時腳本放 scratchpad 或 `$TEMP`，不要放在專案資料夾（會被 ruff 掃到）。
- `LOG_FORMAT` 目前 `/57`；平行段落同時遞增時，合併者改成下一號、`runner.py` 文件字串都保留、測試的 `trpg-battle-log/N` 一起改。
- 前端彈出 UI 一律用共用浮動卡元件（6.5.1）。
- agent 回報後若顯示「waiting on its own background work」，用 `TaskStop` 停掉。

### 3.0 接手後要做的（2026-10-22）

> **最新狀態（2026-10-23）**：Phase 3、結束審查、3E-2a～g 全部完成；`LOG_FORMAT` `/57`。**Phase 4 開工**：使用者已決定 5 題（碎界、本機 vLLM 模型、LLM 只選結構、加給 LLM 的短說明、重試 3 次＋退回率 20% 警示），規格 `docs/phases/Phase4計畫.md`（4-L1～L9）。已派 4-L1（LLMClient＋本機 OpenAI 相容 client）與 4-L3（提議模型正式化＋`llm_hint`）。**待使用者**：把 `F:\WSL\settings.ini` 的 `PORT` 改成 8001（避開 `trpg serve` 的 8000）。3E-3 可穿插；平衡在平衡階段（3.3 B1～B9）。

> （2026-10-22 暫停後已恢復，「繼續」；3-33e2b 已驗收 push，3-33e2a 由合併 agent 處理衝突中。）

1. **確認環境**：`git status` 乾淨；`uv run python scripts/check.py` 全過。使用者常自己開 `uv run trpg serve` 佔用 8000 埠：**不要關使用者的程序**，`preview_start` 會自動改用 8001。程式改動後要 `corepack pnpm -C client build` 並請使用者 **重開伺服器** 才看得到。
2. **使用者的 🎮 戰鬥手感檢查**（`docs/專案計畫.md` 第 14 節；問題清單在 `docs/玩法PM交接.md`）：回饋中規則與玩法交給玩法 PM，介面問題排成下一個介面段（**編號從 3-18 起**）。
3. **下一步（2026-10-22 交接；使用者選 A）**：
   - **3-25 戰場變奏**（玩法 #25，`docs/design/06-技能.md` 6.24）：**由接手的開發 PM 撰寫規格並派工**。排程表在 `Phase3計畫.md` 第 21 節；6.24 的變奏可帶關鍵字（3-24b 已做關鍵字推導，推導分級見 26.3：開局與候選只用專屬規則）。新規格請寫在 `Phase3計畫.md` 第 33 節之後（第 30、31 節是 3-28、3-29，第 32 節是 3-30 試玩回饋小修）。
   - **第二次試玩回饋**：與 3-25 同時進行；回饋由專案 PM 轉來，排成新的介面小修段（編號接 3-30 起）。
     - 清單在 `Phase3計畫.md` 第 32 節：#1 浮動卡互動規則一致化（32.1，2026-10-22 已派工）。
   - 之後加排：3-31 普攻與符文（#39）、3-32 普攻流（#40）、3-33a～h 召喚物（#41，`Phase3計畫.md` 第 36 節）。**使用者同意召喚物全部做完再做結束審查**（「可以」，2026-10-22）。
   - **🎮 戰鬥手感檢查點：使用者確認通過（2026-10-22）**——使用者原話：「3 我就不用了 我覺得還行了 之後再修就好」（「3」＝收尾流程中的「使用者試玩確認」）。收尾順序：排定的段（3-33d～h、3-32b、3-32d 普攻流修正）做完 → 直接 Phase 3 結束審查 → 3E-2／3E-3；中間不等使用者試玩，之後有試玩回饋照常插隊小修。
   - **收尾順序（2026-10-23 更新，使用者：平衡延後）**：3-33f2 push → 3-33h2 → Phase 3 結束審查 → 3E-2／3E-3 → Phase 4。3-33g 移到平衡階段（3.3 B2）。
   - 3-33 全部完成後：**Phase 3 結束審查**（下一點）→ 3E-2／3E-3（第 5 點）→ Phase 4。
   - 3-28 已完成先前累積的介面小修（`Phase3計畫.md` 24.4 清單清空）；3-29 修好衝鋒類技能打不到貼牆／地圖邊的敵人（請使用者試玩時實機確認點敵人格的體驗）。
   - 待玩法 PM 回覆：3-26b #1 是否補輔助類進化模板（47 招主動技沒有合格進化）。
   - **已知問題**：多個 agent 同時跑全量 `check.py` 時，平行 pytest 會在 98% 停住（3-24c、3-27 都遇過，PM 單獨跑會過）→ 審查時查原因；一次最多平行 2～3 個 agent，PM 合併後自己跑一次全量（可能超過 10 分鐘，用背景執行）。
   - 合併慣例：平行段落常同時遞增 `LOG_FORMAT`（目前 `/46`），合併時改成下一號、`runner.py` 文件字串兩段都保留、測試的 `trpg-battle-log/N` 與 `endswith("/N")` 一起改；產生檔 `client/src/render/fixtures/skill_icons.json`（`uv run python -m tests.narrative.icon_fixture`）、CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`）、OpenAPI 重產；`styles.css` 衝突多半在檔尾，兩邊保留並補回被切掉的 `}`。agent 回報後常不會自己結束，收到報告就 `TaskStop`；brief 結尾加「完成回覆後就結束，不要留下背景工作」。
   - 美術 PM 的成果在分支 `claude/art-pm-20b75c`，由開發 PM 併進 main（`git merge --no-ff`）。
4. **Phase 3 結束審查**（6.5）：範圍 `2c42268..HEAD`（上一次審查到 3C／3D 結束；之後是 3E-1、3-5～3-27、3F、3G）。範圍很大，建議拆成 2～3 個審查 agent（引擎與內容／前端 `client/src/render/`、`BattleScreen.tsx`／roguelite 與裝備）。另請查：多 agent 時全量 pytest 卡在 98%、各段新增的 `PLR0917`／`PLC0415` noqa。**必查：全站浮動卡一致性**——盤點所有彈出 UI（卡片、說明框、資訊卡、選單）是否都已改用共用元件並符合 6.5.1，列出未改的位置。另查 3-25a 合併後一次全量 pytest 平行收集時的 `ImportError`（`tests/engine/test_variant*.py`，重跑通過）。結論排進 3E-2／3E-3 或新的整理段。
5. **Phase 4（LLM 技能生成）之前**：3E-2（數值上下限以 YAML 為唯一來源、落點函式合併、`FieldSpec` 旗標、原語 `player_description`、效果／條件／觸發中文名進 glossary API）、3E-3（interpreter 拆成原語 handler 註冊表）；待決定 #5 的 **世界觀**（美術原型已決定：程式繪製）。隨機組合器目前不產生暫時障礙與煙霧（3-11 #8），Phase 4 生成時一併開放。工坊的選項推導（`trpg.skillgen` 的 `draft_options`）與 `icon_of`、`tile_info` 可直接給 LLM 流程用。

### 3.0.1 使用者已做的決定在哪裡

| 主題 | 位置 |
|---|---|
| 玩法決定 #1～#21 | 總表 `docs/玩法PM交接.md`；全文 `docs/玩法決定紀錄.md`；設計細節 `docs/design/` |
| 美術：原型採程式繪製（地形、紙娃娃、組裝式技能圖示） | `docs/專案計畫.md` 3.2 #5；`docs/美術PM交接.md`；需求 `docs/art/移植需求.md` |
| 畫面與手感提升（不做 3D／等角，2D 俯視角） | `Phase3計畫.md` 第 15 節開頭 |
| Phase 3 網頁與 roguelite（戰鬥間不回復只在營火回滿、隊友維持標準兩名、每場固定經驗、專屬 Boss 地圖） | `Phase3計畫.md` 0.2、0.11 |
| 3C、3D、3F | `Phase3C計畫.md` 0.1；`Phase3D計畫.md` 0.1、0.6；`Phase3F計畫.md` 0 節 |
| CI 只手動觸發 | 本檔 6.1 |

### 3.0.2 各段「待 PM 決定」的處理狀態

- 所有已完成段的「待 PM 決定」都已逐條處理，寫在各計畫檔的驗收小節（「接受」「平衡階段」「排進某段」）。
- **已排定但未落地**：上面 3.0 第 3 點（3-18 介面小修）與第 5 點（3E-2、3E-3）。
- **標「平衡階段」的**：見 3.3。

### 3.0.3 前一位 PM 的備註

- **平行開發**：前端段落常用 `isolation: "worktree"` 平行派兩個 agent，在 prompt 寫明「誰負責哪些檔案、API 型別只新增」；合併用 `git merge --no-ff`，衝突多半在 `styles.css` 檔尾或 `client.ts` import（兩邊都保留）；`openapi.json`／`schema.d.ts` 衝突時重跑 `uv run python scripts/export_openapi.py` 與 `corepack pnpm -C client gen:api`。合併後自己跑 `check.py` ＋ `pnpm build`。實作 agent 偶爾在主資料夾留 log 檔，合併前 `git status` 清掉。
- **瀏覽器驗收**：用 `javascript_tool` 設選單（原生 setter ＋ `change`）與點按鈕；格子用 `computer` 點前先 `screenshot`。內建瀏覽器模擬 1600×900 時 **截圖會縮成只佔左上角**，那是截圖工具的問題；版面以 DOM 量測為準（`innerWidth`、`getBoundingClientRect`）。播放速度存在瀏覽器，若停在「略過」會看不到動畫。
- 用 API 查合法動作或錯誤原因很快（`/api/battles/{id}`、`/preview`）；一輪可用腳本 `auto_play` ＋ `write_save` 推進到指定節點再從網頁「繼續一輪」讀取。
- 驗收時自己跑一場 `trpg battle ... --log-json` ＋ `replay` 確認。
- PM 對話很長時用量高；一個大階段結束就更新本檔並交接。

### 3.1 使用者已同意的方向（2026-10-18，已寫入 `docs/專案計畫.md` v0.2.1 第 14 節）

**先確定遊戲能 work，平衡延後。** 順序：

| 階段 | 內容 | 檢查點 |
|---|---|---|
| ~~Phase 2D｜補模板 A~~ ✅ | `shield`、`damage_reduction`、`taunt`、`buff_attr`、`haste`、`heal_over_time`、`cleanse`；`fear`、`silence`、`blind`、`mark` 等狀態；技能可施加 `defending`。解鎖坦克、輔助、治療、術士 | — |
| ~~Phase 2E｜補模板 B~~ ✅ | 事件觸發系統（`on_hit`、`on_damaged`、`on_turn_start`……）→ 被動、反應、姿態、陷阱骨架；層數累積／消耗（`builder_finisher`）；替隊友擋攻擊的反應技。補上 Phase 2 驗收中標 ⚠️ 的兩條（技能層級觸發、觸發深度上限） | — |
| **Phase 3｜網頁 ＋ roguelite** | （原 Phase 4，**已與 Phase 3 調換**）FastAPI ＋ React／PixiJS、roguelite 循環；升級選項先用隨機組合器；隊友指示只做快捷按鈕；美術先用程式繪製（3-16） | 🎮 戰鬥手感檢查 |
| **Phase 4｜LLM 技能生成** | （原 Phase 3）LLM 技能生成、LLM 戰術指揮官、LLM 命名、文字隊友指令，接進網頁。開始前要定 #5 的世界觀 | 🎯 好玩檢查點 |
| 平衡 | 見 3.3 | — |

- 使用者選這個順序的理由：先有畫面才能判斷好不好玩；試玩時 build 種類要齊全（所以模板 A、B 在網頁之前）。
- 召喚物範圍最大，放在更後面。
- Phase 3 已完成到 3-17（見第 2 節），下一個檢查點是使用者的 🎮 戰鬥手感檢查。

### 3.1.2 加快階段速度（2E 的經驗，寫下一份規格時照做）

- 2E 三段實際：2E-1 48 分、2E-2 56 分、2E-3 100 分（規格估 30 分）。分析 agent 紀錄：約一半時間在 **等全量 pytest／`check.py`**（單次 6–10 分鐘，每段跑 2–3 次），另一半是模型思考與撰寫；2E-3 多出的約 30 分鐘是全量 completion（14 分）＋ matrix（約 15 分）。
- 規格的「工作環境」一節要寫明：**開發中只跑相關測試檔；全量 `check.py` 只在子階段最後跑一次**（commit 前只跑 ruff、mypy 與相關測試）。
- 大型模擬（completion、matrix）**不要放在實作子階段裡**：獨立成一個小收尾段，或由 PM 驗收時自己在背景跑。
- `pytest-xdist` 已引入（2026-10-19），全量測試平行跑；工作環境改到使用者電腦（見 6.1）。
- 一段的範圍以「一套規則 ＋ 其測試」為上限；像 2E-2 一次三套規則（反應、攔截、姿態）就會超時。

### 3.3 延後到平衡階段的累積待辦

- **B-3W（2026-10-29，玩法 PM #70）**：全指定類別的玩家一季約只能練滿 2～3 招（不指定約 5 招）；平衡階段模擬兩種玩家（全指定／全不指定）後，再決定靈感點總量。
- **B-3W-2（2026-10-29，玩法 PM）**：補「輔助 → 被動」轉型（例：回合開始時，1 格內的友方回復少量生命）；目前輔助技只能轉防守姿態與召喚。
- **B-3W-3（2026-10-29，3W-2b）**：姿態等級表（預算 15／17／19／22／28、傷害 +10～30%）、維持費換算（每點 2 耐力或 1 法力、折抵 200‰）、護盾反傷 2、結束回復 3、先機標記實測 2～3 回合，都是初值；轉型後的姿態一律扣法力（即使原招是武器技）待確認。
- **B-3W-4（2026-10-30，玩法 PM 6fc1e9b0）**：升階時狀態／表面持續回合上限 10，3 階淬毒、毒反擊到頂後偏弱；施加狀態沒有層數參數，平衡階段再決定是否加層數。

> **使用者決定（2026-10-23）**：「幫我在後面加個平衡phase 這些都先往後延吧 因為都會陸續改 感覺現在平衡沒意義」——平衡工作全部移到獨立的平衡階段（位置照舊：Phase 4 之後、Phase 5 之前，`docs/專案計畫.md` 第 14 節）。之後各段驗收**確認功能正確、重播一致、沒有明顯壞掉**（某招完全無效、某種召喚物必死）；**數值仍要判斷並記錄**（使用者補充：「數值可能還是要判斷 然後記錄起來可能會很強或很弱 但是在加新功能 新開發 還是給予建議 但是不做開發平痕」）——從報告、少量測試或玩法 PM 的判斷看出可能偏強或偏弱時，寫進下表並附**建議值與來源**；不派平衡段、不跑大型模擬、不為數值反覆調整，新功能照設計初值實作。

**平衡階段清單（Phase 3 後期新增，2026-10-23 整理）**

| # | 項目 | 來源 | 內容與門檻 |
|---|---|---|---|
| B1 | 普攻流對照 | 3-32a～d（`Phase3計畫.md` 35.4a） | AI 有 ≥ 2 敵可打時範圍技選用率 40% → ≥ 70%；改完背景跑 200 場：Boss 擊殺輪數比 ≥ 0.90、範圍清場輪數比 ≥ 1.15；仍不達標才動基礎普攻（不再動連擊、分裂、精通）。`scripts/sim_attack_flow.py --diagnose` |
| B2 | 召喚流對照（原 3-33g） | 36 節段表 | 長戰單體、範圍戰、Boss 戰三情境；長戰輸出不超過技能流與普攻流；含灌注（1 AP、AI 權重 700）、操控半徑與自動切換門檻、群召／精英反推的預算點數、精英 +50% 與全身上限、數量型進化與上限 1 的互動、召喚物倒下爆炸／治療 1d8 |
| B3 | 召喚物存活門檻 | 36.4b、36.8a（06 6.29.7） | 一般戰鬥被打倒 ≤ 50% 且 ≥ 10%（±10 個百分點）、Boss 戰被打倒 ≤ 50%；戰意圖騰、殘影係數未模擬 |
| B4 | 召喚持續輪數與預算 | 36.7b、玩法 PM | 特性計入預算後多數召喚縮成 2 輪，看是否放寬召喚預算；拉扯／高台計價初值各每輪 1000‰；召喚物特性係數；17 種召喚技只有 9 種三支進化齊全（骷髏、傀儡、雷靈貼上限） |
| B5 | 召喚物 AI | 3-33e2b #2 | **3H 後 AI 灌注頻率大降**（dev_summoner／bandit_lair 40 場只有 2 場灌注，3H 前前 8 場內就有）；AI 對護盾、拉扯、高台、纏住估值 0；高台圖騰包勝率 60% → 檢查 AI 是否把遠程角色帶上高台 |
| B6 | 刃刻降階 | 3-31（34.1） | 刃刻 2 階，看能否降回 1 階；`per_turn_limit_uses: 8`、`on_hit_rune_permille: 270` |
| B7 | Boss 公平性 | 06 6.29.7、8.25 | Boss 對召喚物 ×2、擋路加分 60；普攻流不能成為打 Boss 唯一解；Boss 戰勝率（無召喚對照包 0–12%）與輪數 6–10 |
| B8 | 戰場變奏 | 33.1a、33.2a | 變奏加價 10%、射程每格 5%、AI `variant_position_bonus` 3、組合器變奏機率、進化模板曝光 |
| B9 | 法力續航 | 3-32d #3 | 目前沒有法力自動回復；技能流 Boss 戰 19% 回合缺法力，要加時先定「對所有單位或只對玩家方」 |
| B10 | 普攻屬性倍率 | 玩法決定 #45（2026-10-23） | 普攻的屬性倍率偏弱（例：力量 × 0.3），3H-1 後重量 |
| B11 | 法力、耐力係數 | #45、`Phase3H計畫.md` 3H-2 | 07 7.2 的資源上限係數（武器大類基礎、×2）與法力換耐力的預算換算；「每場法力回滿」（待使用者決定）要連耐力一起考慮 |
| B12 | 心智三分後的流派 | #45、3H-1 | 約 31 招改看意志後，召喚流、暗影流重量（勝率、輸出、資源不足回合） |
| B13 | 屬性常駐數值係數 | #45、`Phase3H計畫.md` 3H-1 第 6 點 | 每 4 點一階的門檻與每階數值，特別是智力「表面與持續區域 +1 回合」 |
| B14 | 敵我同一套資源公式 | 3H-2 待決 #4、玩法 PM 2026-10-23 | 原則上要（公平，朋友的影子也同規則），但會動敵方平衡：敵人、隊友、召喚物的法力／耐力改用和主角相同的上限公式，平衡階段一起做 |
| B15 | 法力回復 | 3H-2 待決 #1、3H-5 | 耐力回復已做（每回合 +5、戰後回滿，使用者選 A）；之後耐力不足幾乎消失，**短缺都是法力**（近戰長戰與 Boss 約 24%、弓手 Boss 17%、召喚師 Boss 38%）；**使用者決定法力維持只在營火回滿**（2026-10-24 原話：「法力維持只在營火回滿」）→ 法力短缺留給平衡階段用技能費用、上限係數處理，不改回復規則 |
| B16 | 3I-1 新武器傷害骰 | `Phase3I計畫.md` 4.1 | 拳套 1d8（雙手＋反擊）、鐮刀 1d10（雙手＋收割）、鞭 1d6（單手、射程 2＋纏繞）為初值；白板 700 場：拳 61%／鐮 58%／鞭 66%（單手劍 58%），鞭 DPR 最低但生存最高。依真實配點 build 再看 |
| B17 | 圓盾格擋強化 | `Phase3I計畫.md` 4.2 | 縮放值 × 5‰、最多 +10%（格擋 50% → 最高 60%），初值未模擬 |
| B18 | 3I-4 雙匕首偏強 | `Phase3I-4報告.md`、玩法 PM 2026-10-24 | 勝率 67.5%、DPR 7.22（單手劍 +35%）。平衡時先試「背刺只加成第一下」，不夠再降 1d3×2 |
| B19 | 3I-4 霰彈槍偏弱 | 同上 | 勝率 31.9%，主因 AI 不貼近；平衡時先修 AI 站位（往 1～2 格靠，效用 AI 位置價值），再重量，修好前不調傷害 |
| B20 | 3-50 代價換強度的 AI 與組合器初值 | `Phase3-50報告.md`、玩法 PM 2026-10-24 | 自暈 AI 條件（HP 50%、6 格內）、透支條件（波及 ≥ 2）、組合器產生透支機率 40‰；未模擬 |
| B21 | 魔劍斬改武器技 | `Phase3I-3報告.md`、玩法 PM 2026-10-24 | 近戰武器技＋智力，耐力 10、倍率 2.4，剛過預算下限的初值，未模擬 |
| B22 | 3K-1 物品產生器初值 | `Phase3K-1報告.md`、玩法 PM 2026-10-24 | 小部位（副手、手、腳、戒指）詞條預算 4～9 點，稀有／史詩常只 1 條，手腳 build 詞條出現率 17%；「傷害 +2%＝3 點」；條件成立率 0.6／0.35／0.2；代價型單位價；充能與代價型詞條第一版不產生（裝備段再開）；等級 9、10 優良主手產生不出來（Phase 5 掉落前處理） |
| B23 | 3I-5 親和出現率 | `Phase3I-5報告.md`、玩法 PM 2026-10-24 | 組合器只替換既有常見條件，實際出現率低於 400‰；等 Phase 4 LLM 依主角武器加親和條件後一起看。裝填類招牌技（讀取／操作彈匣的新原語）待需求出現再評估 |
| B24 | 3K-2b 防具基礎防禦與基礎份額 | `Phase3K-2b報告.md`、玩法 PM 2026-10-24 | 布袍 1、外套 2、皮甲 3、鎖甲 5、板甲 7，頭手腳 1，每級 3 點；基礎份額照 8.22 比例換算（3K-2c）的係數 |
| B25 | 3-54a 風的初值 | `Phase3-54a報告.md`、玩法 PM 2026-10-24 | 吹送每格 1 點、風壓撞擊每顆撞擊骰 +0.5 點、擴散不計點、組合器吹送機率 80‰；未模擬 |

- **召喚物（玩法 PM 2026-10-23）**：特性計入預算後多數召喚縮成 2 輪，召喚專精補回，平衡階段看是否放寬召喚預算；高台圖騰包勝率 60% 偏低 → 檢查 AI 是否把遠程角色帶上高台（AI 問題）；AI 對護盾／拉扯／高台／纏住的估值（3-33g）。
- **普攻流（3-32d，玩法 PM 2026-10-22）**：AI 有 ≥ 2 敵可打時範圍技選用率 40% → 目標 ≥ 70%；改完背景跑 200 場（`scripts/sim_attack_flow.py --diagnose`），門檻 Boss 擊殺輪數比 ≥ 0.90、範圍清場輪數比 ≥ 1.15；仍不達標才動基礎普攻，不再動連擊、分裂、精通。
- 勝率：大多數地圖我方 70–95%（2C-4 後 `lava_crossing` 75%、`ruined_fort` 70%），`oil_depot` 偏難（保留）；目標 35–65%、一般遭遇 4–6 輪。
- build 矩陣（`Phase2C-3報告.md`）：`build_storm` 8 種類型中 7 種前段；`build_tank` 曾 0 種（原因是 **沒有保護型模板**，補模板 A 後重測）；2C-4 改 AI 後標準 2 不通過的變成 `build_assassin`。
- AI 很少用控場、位移、場地技能；控制回合每場接近 0。所有 AI 權重、狀態價值、指令加成（集火 ×1.5 的算法等）未經模擬。
- `skill_fire_bolt` 的 DPR 超過同階 P95 × 1.2。
- 結構型原語點數偏低（2B-3 #3）；技能報表在平地 1 對 3，控場、位移、光環骨架的 DPR 偏低，可能要另設情境。
- 冰面 DEX DC12 滑倒對 AI 的影響未評估；敵方集火時 `bridge_chasm` 我方勝率反而上升，原因未查。
- 代價折抵總上限已定為 +500‰；組合器權重已搬到 `content/skill_composer.yaml`。
- **2D 後新增**：`build_tank` 改版（嘲諷＋護盾、`guard` 行為模式）後前段類型 2 → 0、英雄 DPR 5–8 → 1–2.5（疑似 `guard` 的 damage 權重 3 讓坦克太被動）；`build_healer` 也 0 次前段。保護矩陣有數字但沒轉成勝率——要決定保護型 build 的評估指標（標準 2 是否改看保護矩陣）或調 AI／數值。
- **2E-2 後新增**：`build_guardian`（攔截＋姿態）小樣本 8 張地圖 4 張第 1，可能偏強；姿態狀態 11 點只合階級 1，高階由組合器加護盾湊預算；反應技在 fuzz 中很少觸發（7/70）。
- **2E-3 後新增**：build 矩陣（12 個 build、2400 場、異常 0）6.8 標準 1 通過、標準 2 不通過：`build_tank`、`build_striker` 沒有任何前段類型；`build_trapper` 的 AI 陷阱擺位差（常放角落）。
- **2H 後新增**：新數值（`frozen` 點數 8、`self_status` 折抵 40‰／點、AI 自身狀態成本、組合器雙屬性 250‰、專精 300‰）都未經模擬；`skill_arcane_blade` 裝在智力 10 的 build_push。2H 驗收時 matrix 標準結果與 2G 相同（標準 1 `build_storm`；標準 2 `build_tank`、`build_assassin`、`build_healer`）。
- **2G 驗收時（PM 本機跑）**：completion 全量 1800 場異常 0（90 秒）；build 矩陣 2400 場異常 0、平手 1（103 秒）。6.8 標準 1 不通過（`build_storm` 8 類型全前段）；標準 2 不通過：`build_tank`、`build_assassin`、`build_healer`。`build_tank` 英雄 DPR 約 1–2.5。
- **2G-2 後新增**：12 個示範技能的數值只為通過預算（致命破綻、天賜好運靠冷卻湊預算；天賜好運護盾 1d4 太小）；AI 把「築高台」當攻擊技、升高敵人腳下的格子；敵方單位沒有被動、反應、姿態。
- **2G-1 後新增**：`build_tank` 主動技能 6 個（加了破甲擊、碎甲重擊）但法力只有 20。
- 控制回合統計（`CONTROL_STATUSES`）只算 stun、root、slow，未含 feared、silenced、blinded、taunted。
- **3C／3D／3F 後新增（2026-10-20）**：
  - matrix（22 build × 10 地圖、2200 場、異常 0）：偏強 `build_storm`（92.5%）、`build_detonator`（89.4%）、`build_fire`（90.0%）；偏弱 `build_assassin`（56.9%）、`build_winged`、`build_gambler`、`build_tank`；前段 0 次的 7 個 build（`Phase3C-6b報告.md`）。撞擊流（push、wallburn）不如預期，先查 AI 推擊評估。建議合併 wallburn→push、detonator→warlock、tank→guardian（未決定）。
  - roguelite：`trpg run auto` 10 種子只贏 3 輪（戰鬥間不回復累積）；Boss 地圖標準陣容勝率 30%、平均 7.9 輪；開局屬性六項 10 ＋ 4 點比 build 英雄弱。等 3-6 試玩再決定（多營火、調 Boss、調開局）。
  - 所有 3C／3D／3F 新原語、觸發、條件、複合技能的預算係數與 AI 權重都是初值，未經模擬（各計畫檔 0 節標「平衡階段」的項目）。
  - 背刺：被近戰攻擊後轉身後，刺殺 build 每場約 1.8 次背刺；AI 權重 `backstab` 4、`back_exposed` 3。
  - 召喚物很快被打倒；AI 隊友會走進我方火牆留下的火；定時炸彈不分敵我會炸到隊友。
  - 純數值的修正型被動「打法差異」只有 0–1 分（`Phase3C計畫.md` 0.14），Phase 4 生成時要避免大量產生。
- `skill_dread_gaze`、`skill_hush` 貼著預算下限 70.4%；`skill_hex_bolt` 的 `marked` 只有 1 回合；AI 會對已被標記的目標重複施放咒印飛彈。

- **3-5～3-17 後新增（2026-10-22）**：
  - 一輪：AI 代打 10 種子 2 勝（3-7 後）；Boss 戰中主角不動時頭目與弓手守在原地 → 30 輪平手（AI 是否要主動進攻）；等級 HP 加成向下取整（基礎 40 每級 +2）；玩家配體質的強度未測（AI 不配體質）。
  - 3-7：流血／中毒可被體質抵抗後依賴它們的 build 變弱，matrix 未重跑。
  - 3-11：暫時障礙持續時間係數（`content/skill_budget.yaml` 的 `obstacle_duration_permille`）未經模擬；冰牆、荊棘牆為過預算下限附帶表面；煙霧彈 5 回合與煙霧箭相近。

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

### 6.1 環境（2026-10-19 起改在使用者的 Windows 電腦上執行）

- **先確認你在對的環境**：在專案資料夾執行 `uv run python --version` 應為 3.12（直接打 `python` 會是系統的 3.11，不算數）、`git status` 正常。若你跑指令的工具是「在使用者電腦上執行指令」（`mcp__remote-devices__device_bash`，Linux 虛擬機、Python 3.10、不能刪檔、git 會卡鎖定檔），代表你是**連到電腦的雲端對話，不是本機 Claude Code**：不要在虛擬機裡建環境或跑測試，請使用者改在 Windows 開本機 Claude Code（PowerShell 在專案資料夾執行 `claude`，或桌面 app 的 Code 分頁選本機資料夾）。
- PM 與實作 agent 都在使用者電腦上的 Claude Code 執行，專案資料夾就是 `F:\PythonProject\LLM-MMO-TRPG`（origin 指向 GitHub `huntertoby/llm-mmo-trpg`，私人）。**不再需要 clone、代理設定或 bundle 同步**；完成後直接 `git push`。
- 電腦：Ryzen 7 9800X3D（8 核 16 緒）。全量測試 `check.py` 用 `pytest -n auto` 平行跑；`trpg sim` 的 `--jobs` 預設 0＝全部邏輯核心。雲端 2 核時的基準：全量 pytest 單執行緒 4 分 33 秒，`-n auto`（2 核）2 分 47 秒；本機預期 1 分鐘內。
- 專案設定 `.claude/settings.json`（已進 git）：常用指令（`uv run`、`uv sync`、git 的讀取與 commit／push、`trpg`）免確認、檔案編輯自動接受、`PYTHONUTF8=1`（避免 Windows 主控台 cp950 印中文出錯）。**背景 agent 若卡在確認提示，表示它用了清單外的指令**：把該指令加進清單，或在規格裡改用清單內的寫法。
- **GitHub Actions CI 只手動觸發**（2026-10-19 使用者決定，私人 repo 每月 2000 分鐘額度曾用完）：推送不會自動跑檢查，驗收一律以本機 `check.py` 為準；需要時在 GitHub Actions 頁面按「Run workflow」。
- Claude Code 在 Windows 上的 shell 是 Git Bash，指令照 Linux 寫法（`/` 路徑、`&&`）。
- 第一次在本機開工時先確認：`uv --version`（沒有就請使用者安裝 uv）、`uv sync`、`uv run python scripts/check.py` 全部通過，並記下全量時間更新上面的數字。
- 使用者電腦要保持開機、不睡眠，Claude app 要開著；中途斷掉時進度在 commit 裡，照 6.6 第一點派收尾 agent。
- **備用：雲端模式**（使用者不在電腦旁、想從手機派工時）：`mcp__claude-code-remote__add_repo`（owner `huntertoby`、repo `llm-mmo-trpg`、access `push`）clone，每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`，完成後 push，請使用者在 Windows 上 `git pull`。

### 6.2 一個階段的流程

> **PM 之間的訊息（2026-10-23 使用者同意，為了省 token）**：只在 ① 某段驗收合併完成（附給使用者的檢查重點）② 卡住 ③ 需要對方或使用者決定 時傳訊息；不傳「已轉給」「已記下」「已排入」「副知」「還在等」這類告知，收到告知也不回覆；要留紀錄就寫進文件或 commit。理由：每則訊息都會叫醒一個 50 萬 token 以上的長對話。使用者原話：「2的部分就好 1的話 我等你們收尾phase3就會叫他們做了」。
>
> **回報規則（2026-10-22 使用者指示）**：PM 的 context 只放決策，不放細節。開發 PM 回報專案 PM 時只寫結論與摘要（做了什麼、結果、卡在哪、要使用者決定什麼），細節放進文件、只附檔案位置與 commit；派出的實作／審查 agent 也只回摘要；驗收時不把整份測試輸出或 diff 讀進 context，抽查即可。**回報時機**：只在某段驗收合併、卡住、或需要使用者／其他 PM 決定時回報（附「請使用者重開伺服器檢查的重點」）；「還在等、沒有新進度」不回報。

0. **決策影響盤點（2026-10-24 使用者同意流程改善 A）**：每個玩法／美術決定寫入後、寫規格前，開發 PM 先做一次只讀盤點「現行程式哪裡受影響」（引擎、內容資料、工坊、隨機組合器、LLM 提議、介面、存檔、測試），結果寫進規格的「受影響的既有功能」段。起因：#45 寫入後只做新功能，工坊與驗證器沒跟著改，造成武器技屬性漏洞與工坊違規技能（`docs/phases/工坊盤點-2026-10-24.md`）。
1. **寫規格** `docs/phases/PhaseX計畫.md`：目標、範圍外、工作環境、交付項目、驗收條件（每條可驗證）、報告格式。**必填兩段（2026-10-24，流程改善 A、B）**：① **受影響的既有功能**（第 0 步盤點結果，每項寫要改或不改的理由）；② **行為一致測試**——凡是規則句（看什麼屬性、花什麼資源、誰能抵抗、說明文字寫的數字），一律要求「實際跑引擎」的表格測試，不只測資料與驗證器（範例：3-41c 的傷害算法與引擎 `damage_dealt` 逐一比對）。上一階段報告的「待 PM 決定」放在新規格開頭的「PM 決定」表。**規格要小**：一個 agent 的工作量控制在約 30 分鐘、25 萬 token 以內，範圍以「一套規則 ＋ 其測試」為上限。
2. **commit 並 push 規格**。
3. **派實作 agent**：`Agent` 工具，`subagent_type: general-purpose`、`run_in_background: true`，模型依 6.3 選。prompt 範本見 6.4。
4. **等通知**，不要輪詢。使用者問進度時用 `git log --format='%cd %h %s' --date=format:%H:%M <base>..HEAD` 回報。
5. **功能驗收**（自己做，不只看報告）。**檢查分級（2026-10-23 使用者同意，專案 PM 傳達「好」）**：
   - **排版煙霧檢查（2026-10-24，流程改善 D；3-47 起有工具）**：凡是動到前端的段，合併後在內建瀏覽器跑 `window.__layoutSmoke`（`client/src/dev/layoutSmoke.ts`，純函式 `evaluate` 有 vitest；不需安裝任何套件）。步驟：① `corepack pnpm -C client build`，背景啟動 `uv run trpg serve --port <空的埠>`（只關自己的）；② 每個情況先 `resize_window`，先 `javascript_tool` 執行 `localStorage.clear()`（有舊的一輪存檔時頁面會接回去、全部量不到），再 `navigate` 到 `/?anim=0.1`，再 `javascript_tool` 執行 `await window.__layoutSmoke.runCase("標題")` 取得 PASS／FAIL 表；三個情況：1600×900、800×600、1600×900 加參數 `{shortBottom:true}`（底部列最矮）；③ 結束 `resize_window` preset `desktop`。量：結束回合寬度 ≥ 右欄 90%、播放列與按鈕在畫面內且一行、三條拖曳線貼齊（窄螢幕沒有拖曳線）、格子資訊卡提示列在底色內、「更多動作」選單開著時沒有說明卡、沒有 `.hint-tip` 外框。固定種子與起始武器（弓），結果可重現；全 PASS 才算過。新增版面元件時把它的量測加進 `layoutSmoke.ts`。`?anim=0.1` 可放慢動畫逐格截圖。
   - **一次出事就全面掃描（流程改善 E）**：同類錯誤第一次出現時，就全專案掃描同樣寫法並寫成常駐規則，不要只修那一處（反例：說明卡包一層造成的排版錯誤先後出了三次）。
   - **每段合併只跑快速檢查**：`ruff check`、`ruff format --check`、`mypy`、這段改到的 pytest 檔與相關前端測試、一場 `--log-json` ＋ `replay`；有改前端才跑 `pnpm build`。
   - **全量 `check.py` 每 2～3 段合併跑一次**，以及 Phase 結束審查前一次（3-34 之後用 `scripts/check.py --full` 含 slow）。
   - **同時進行的 agent 最多 2 個**；pytest 不用 `-n auto`。3-34 起：`scripts/check.py`（快速版，約 3 分鐘，不含 slow）、`scripts/check.py --full`（含 slow 與前端完整組合 `TRPG_FULL=1`，約 10 分鐘）；平行數 `TRPG_PYTEST_WORKERS`（預設 8，可設 `auto`）。長指令要加 timeout（Bash 預設 2 分鐘會中斷）或背景執行。3E-2c 起：pytest-timeout（一般 300 秒、slow 1800 秒）；agent 在自己的 worktree 跑測試，加 `UV_NO_SYNC=1`（或 `uv run --frozen`）避免測試中途重裝套件。
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
4. 開發中只跑相關測試檔；每次 commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**不要跑完整的 `scripts/check.py`**（PM 合併後統一跑）；pytest 平行最多 `-n 8`。直接打 `python` 可能是 Windows 商店空殼，一律用 `uv run python`。
5. 不要 push。
6. 逐條自我檢查驗收條件（要有測試名稱或指令輸出為證）。依邏輯分 commit，結尾帶 Co-Authored-By 一行（依你的系統提示）。
7. 撰寫並 commit `docs/phases/PhaseX報告.md`；若新增了複雜度類 noqa（C901、PLR0911、PLR0912、PLR0915），在報告中逐一列出理由。

若改到前端：彈出卡片一律用共用浮動卡元件（本檔 6.5.1），並在瀏覽器實測「從觸發元素滑進卡片 → 捲到底 → 釘住 → 關閉」（1600×900 與 800×600），結果寫進報告。

規格沒寫到的採最保守做法並寫進報告「待 PM 決定」。不要修改 `docs/專案計畫.md`、`docs/design/`、`CLAUDE.md`、`docs/phases/` 下的計畫檔。

**禁止事項（2026-10-24，流程改善 F）**：不要用會結束不是自己啟動的程序的指令（`taskkill /IM python.exe`、`taskkill /IM node.exe`、`pkill python` 等）——使用者的 `trpg serve` 與其他 agent 會被一起關掉；要結束自己開的伺服器只用它的 PID。預覽伺服器不要用 8000（使用者的）或 8001（本機 LLM 模型）埠。不要改使用者的設定檔（`F:\WSL` 等）。

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
- 自動檢查（待排入下一個前端段）：vitest 或 `tests/test_architecture.py` 加 grep 規則，`client/src` 中除共用元件外不得出現新的 `position: fixed`／`absolute` 彈出層或 `title=` 屬性（白名單列出例外）。

### 6.6 注意事項（踩過的坑）

- **共用資料夾的 git 規則（所有 PM）**：主資料夾由專案 PM、玩法 PM、開發 PM 共用。更新一律用 `git pull --ff-only`（必要時 `git merge`），**不要 `git pull --rebase` 或 rebase**——會把別人尚未 push 的合併 commit 攤平（2026-10-22 發生過一次，內容無誤但失去合併紀錄）。commit 前先 `git status`，只 commit 自己改的檔；開發 PM 合併中時其他 PM 先別 pull。
- **Agent 可能中途停止**（用量上限、被手動停止、電腦睡眠）。進度會留在 commit 裡；派一個新的「收尾」agent：說明前一位的最後 commit、請它核對驗收條件、補齊缺漏、寫報告，不要重做。
- agent 還在跑時，工作區可能有未 commit 的半成品，**不要替它 commit**。
- **平行工作**（例如文件整理與程式實作同時進行）用 `isolation: "worktree"` 的 agent，完成後在 main 上 `git merge --ff-only <先完成的分支>`、再 `git merge --no-ff <另一個分支>`，合併後自己跑一次 `check.py` 與一場 `--log-json`／`replay`。兩個 agent 共用 CPU，同時跑全量測試會互搶，但仍比雲端快。
- **建立新的 GitHub repo** 要請使用者在網頁上建。
- 平衡調整很耗 token：讓 agent 寫腳本輸出摘要表，由 PM 決定數值，不要讓 agent 反覆試。
- 規格要求大型模擬時，寫明「只在最後跑一次全量」（2C-4 曾因完成度檢查跑兩次，用了 68 分鐘、28 萬 token）。

## 7. 節省 token 的原則

- PM 對話本身是最大的隱藏成本（每一步都會重新處理整段對話）。**對話變長時（例如完成一個大階段後），更新本檔並請使用者開新對話。**
- 實作 agent 依 6.3 選模型（預設 Sonnet）；規格要小；agent 開發中只跑相關測試（CLAUDE.md 守則 11）。
- PM 讀文件只讀需要的：總覽 ＋ 對應的 `docs/design/` 主題檔 ＋ 最新一份報告。不要讀整份舊報告或舊對話。
