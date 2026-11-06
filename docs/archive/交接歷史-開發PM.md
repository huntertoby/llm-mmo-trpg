# 開發 PM 交接歷史（歸檔）

> 開發 PM 交接文件的歷任進度小節，2026-10-22～10-31；現況以 `docs/開發PM交接.md` 為準。
> 各節保留原標題與日期，由新到舊排（DOC-B M1 自 `docs/開發PM交接.md` 第 3 節搬出，原文未改；文中「本檔 3.3」「本檔 6.1」等指的是當時的交接文件節號）。

---

### 3.00000 接手第一件事（2026-10-31 第五任交接，最新，優先於下面各節）

> 使用者：「但我覺得對話太長了 要你們交接」。第五任開發 PM `local_ab425b7d` 到此交接。專案 PM `local_69ff6dd8-1a56-4d3a-950d-054825e07625`、玩法 PM `local_9c79efb1-a93e-4b28-8a2f-7c97ec50b846`、美術 PM `local_cb74dfda-1832-4c4b-bf87-d4dcb9fbf335`（交接後 id 可能換，以專案 PM 通知為準）。

**1. 進度**
- **Phase 3W**（白板與閃現）完成，含審查整理 3W-R1／R2（`Phase3W計畫.md` 第 4、6 節）。
- **4-L9～4-L11b**：真模型評估（`Phase4-L9報告.md`）→ 4-L10 schema／提示修正（升級候選 28% → 62%）→ 4-L11 敘事對齊效果與世界觀詞上限、卡片重複行 → 4-L11b 詞表（燃燒、易傷、比喻跳過、missing_added 放寬）。樣本：`docs/phases/4-L9/AI生成樣本.md`、`AI生成樣本_4L11.md`；多樣性量測 `閃現提議多樣性.md`；查修 `閃現轉型與護盾模板查修報告.md`、`複合技轉型報告.md`。
- **平衡階段**（`docs/phases/PhaseBAL計畫.md`，驗收紀錄在第 2 節、新順序在第 3 節）：BAL-1～BAL-9c、BAL-10a／10b 完成並驗收（靈感每勝 2、三種閃現 AI、姿態／形態幅度、難度倍率、守點、第 3 場 3 名、Boss 援軍 1、盜賊隊長、AI 修正、武器數值、boss_approach 10、頭目 HP 700‰、弓手護衛 1d6、弩 pierce_permille 400、小變化模板補第一段）。
- **BAL-10c**（變身姿態只出修正類、進入代價 −1 可減法力／耐力、`mod_cost` 不讓代價消失、閃現目錄依種子打亂）：見本節第 2 點的狀態。

**2. 交接時的狀態**：BAL-10c 已交件、合併並 push（報告 `docs/phases/BAL-10c報告.md`；合併後 ruff、format、mypy、lint-imports、skillgen／llm／content／roguelite／narrative／cli pytest 6407 通過、swamp 種子 7 重播通過；最後一次**全量**是 BAL-9 合併後：pytest 10793、vitest 1176）。四位 PM 的交接 commit（專案 PM 2da95ec0、玩法 PM 6ef9bb2a／1dd74ae9／d343796d／8cd9a725／01ebc927、美術 PM c14a80fc）都已併入並 push，main ＝ origin/main。**沒有 agent 在跑**。工作區只有不明的 `tmp_x`（不是開發 PM 建的，不要動）。`LOG_FORMAT` `/90`、存檔 `trpg-run/13`。
- BAL-10c 待決（交玩法 PM）：8 個變身姿態各階第 1 次只剩 1 個選項（只能新增非費用的形態旋鈕或接受）；`mod_cost` 只對 2 格以上代價出，內建幾乎沒有；打亂是否降低位置偏好待下次真模型量測。
- 新開發 PM 建議先跑一次全量（`UV_NO_SYNC=1 uv run pytest -q tests -n 6 -m "not llm" --timeout=3000` 加 vitest、build），因為 BAL-9c～10c 之間只跑相關檢查。

**3. 平衡方向（使用者 2026-10-31）**：「反正到時候大世界又不會要求你要打5局就要打BOSS…本來打不過就要練等不是嗎」→ **不追一輪勝率**；重心放在會帶到大世界的東西（單場難度、武器、技能數值、召喚、AI、資源）。已定的原型數值不再調。原型數值玩法 PM 可直接定；會帶到大世界的規則回使用者；**已寫入設計文件的決定只有使用者能改**（玩法 PM 自己定的細節由玩法 PM 改）。

**4. 下一步（依序）**
1. **BAL-10d 收束**（#74，06 6.34.4，`1dd74ae9`）：照原規格；把「放棄一部分 → 換核心數值」做成共用機制；量收束火球閃滿倍數、AI 選中比例，以及兩種練法比較（第 1、2 次收束＋蓄力 vs 第 1、2 次擴範圍、第 4 次收束；確認預算守恆、不超過 3 倍上限）。範圍在 `PhaseBAL計畫.md`。
2. **BAL-10e 收回家族**（#75，`8cd9a725`）：精煉、合體、專注、陷阱／地面格收束；做完重掃 BAL-10a 不足名單（`scripts/flash_minor_coverage.py`）。
3. 下次使用者開模型時：`scripts/eval_flash_diversity.py --real` 重量位置偏好（打亂後「第一個提議取自前三分之一」應接近 33%）。
4. **預算旋鈕查修**：約 300 次 keyword_exploit／keyword_imbue 結構合法但重調不進預算窗；姿態冷卻折抵另訂（遠小於主動技）；舊 `mod_potency` 等階梯改細（接續段 100‰、形態 50‰、修正傷害 25‰ 都大於一次閃現 +40‰）。
5. **技能數值批**：5 個沒有前段的 build（assassin、support、charger、gambler、seer）、偏強 fire／summoner、火系法力費用（火焰流 Boss 戰短缺 29%）、修正型被動幅度階梯（B-3W-5）、完整技能 +150‰ 超標、層數待辦（B-3W-4）、小變化補第二段（被動與反應、工具技／召喚／常駐／地面格／陷阱；觸發冷卻守 6.6）。
6. **召喚**（B2～B4；順便看有召喚 Boss 戰 10.8 輪是否降到 ≤ 10，否則考慮頭目 650‰；Boss 戰灌注）。
7. **資源（法力）**（B9、B11、B14、B15；「法力回滿時機」屬規則）。
- 規則待辦（玩法 PM 記著，之後整理給使用者）：Boss 戰「頭目死、護衛撤退」；B-3W-2 輔助→被動轉型。
- 4-L11 後的小待辦：閃現 `name_offer` 遊戲內命名尚未接（之後接時傳 `before`）；形態／規則修正技能的效果比對未納入一致性檢查。
- 伺服器警告「oneOf … falling back to anyOf」（vLLM xgrammar）：4-L10a 拆分支造成，不影響正確性；可排小段給分支加互斥固定欄位。

**5. 這任學到的做法**
- **等待一律用完成通知**，派工 prompt 必寫「不准用 `until grep ...; sleep` 輪詢迴圈」（曾掛 2～4 小時，見記憶 no-until-poll-loops）。
- pytest 指令加 `--timeout=1800`、不要用管線接 pytest 輸出；`tests/cli` 加 `--timeout=3000`。
- 兩個 agent 都會重挑種子時（例如一個改 AI、一個改數值），合併易在測試檔衝突；改成後一段在前一段合併後重挑，或由後一段 `merge` 前一段分支再解衝突（BAL-4c 的做法）。
- 量測先、套用後：平衡段一律「只在模擬覆寫量測 → PM 定值 → 寫進 content → 複測」；寫死數值的測試改讀 content；靠種子的測試重挑種子、斷言不改。
- 真模型評估：本機 8001 由使用者開關，絕不結束它；開跑前先問專案 PM 模型是否開著；樣本用固定種子以便新舊對照。
- 系統 `python` 是 Windows Store 空殼，一律 `uv run python`；用 Python 寫檔要 `newline="
"`，避免 CRLF。

### 3.0000 接手第一件事（2026-10-29 第五次，最新，優先於下面各節）

> **2026-10-30：Phase 3W（白板與閃現）全部完成並 push，含整理子階段 3W-R1／R2；下一步待專案 PM 與使用者決定（4-L9 等使用者開本機模型）。**
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

