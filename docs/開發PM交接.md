# 開發 PM 交接文件

> 給接手的 **開發 PM**（新對話中的 Claude）。最後更新：**2026-10-23**。**只讀本檔就能接手**；需要時再讀 `CLAUDE.md`、`docs/專案計畫.md`（總覽）與本檔指到的計畫檔。
> 現況一句話（2026-10-23 第二次交接）：**Phase 4 完成 4-L1～4-L5c，介面完成 3-35～3-38（字型、狀態圖示、戰場效果、區域主題、雲嶺、可燃淡化）；使用者暫停，沒有 agent 在跑**。下一步見 **3.00**。

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
3. 介面／美術：**3-37c 雲嶺服裝部件**（`Phase3計畫.md` 41.3，後放）；五區其他區等美術 PM。
4. **3E-3**（`Phase3E計畫.md` 3.2）可穿插；平衡 B1～B9（本檔 3.3）延後。

**本機模型（真模型測試）**：`F:\WSL\settings.ini` PORT 已改 8001（使用者 2026-10-23）；`config/llm.toml` → `http://localhost:8001/v1`、`swift`、**`enable_thinking=false`**（Qwen3 預設思考會用光 2048 輸出、回空）。strict JSON schema（含 `$ref`／`oneOf`，根層 `oneOf` 也可）vLLM 接受；schema 不佔 prompt token（最大題目實際 2,525）。關思考約 4～13 秒／次。測試：`uv run trpg llm ping`、`uv run trpg llm propose -n 10 --seed 0`（小測試）、`uv run pytest -m llm`。開發與自動測試一律 Mock；模型由使用者用 `F:\WSL\start.bat` 啟動，連不上或顯存不足時回報專案 PM，不要請使用者改 settings.ini。**預覽伺服器不要用 8000（使用者）或 8001（模型）**：`.claude/launch.json` 有 `trpg-serve-verify`（8011）。

**`check.py --full` 變慢（已解決，2026-10-23，`dabb5a9`）**：原因是 3E-2f 起每次建構 `EffectSpec` 都經 `default_content_dir()` 做 `Path.resolve()`（Windows 很慢，`run auto` 一半時間在這）；`bundled_content_dir()` 加 `@cache`、`run auto` 十種子測試改參數化。`--full` 28 分 → **6 分 38 秒**。之後若再變慢，先用 `--durations=30` 加 cProfile 單跑 `trpg run auto --seed 1` 找熱點。

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

> **使用者決定（2026-10-23）**：「幫我在後面加個平衡phase 這些都先往後延吧 因為都會陸續改 感覺現在平衡沒意義」——平衡工作全部移到獨立的平衡階段（位置照舊：Phase 4 之後、Phase 5 之前，`docs/專案計畫.md` 第 14 節）。之後各段驗收**確認功能正確、重播一致、沒有明顯壞掉**（某招完全無效、某種召喚物必死）；**數值仍要判斷並記錄**（使用者補充：「數值可能還是要判斷 然後記錄起來可能會很強或很弱 但是在加新功能 新開發 還是給予建議 但是不做開發平痕」）——從報告、少量測試或玩法 PM 的判斷看出可能偏強或偏弱時，寫進下表並附**建議值與來源**；不派平衡段、不跑大型模擬、不為數值反覆調整，新功能照設計初值實作。

**平衡階段清單（Phase 3 後期新增，2026-10-23 整理）**

| # | 項目 | 來源 | 內容與門檻 |
|---|---|---|---|
| B1 | 普攻流對照 | 3-32a～d（`Phase3計畫.md` 35.4a） | AI 有 ≥ 2 敵可打時範圍技選用率 40% → ≥ 70%；改完背景跑 200 場：Boss 擊殺輪數比 ≥ 0.90、範圍清場輪數比 ≥ 1.15；仍不達標才動基礎普攻（不再動連擊、分裂、精通）。`scripts/sim_attack_flow.py --diagnose` |
| B2 | 召喚流對照（原 3-33g） | 36 節段表 | 長戰單體、範圍戰、Boss 戰三情境；長戰輸出不超過技能流與普攻流；含灌注（1 AP、AI 權重 700）、操控半徑與自動切換門檻、群召／精英反推的預算點數、精英 +50% 與全身上限、數量型進化與上限 1 的互動、召喚物倒下爆炸／治療 1d8 |
| B3 | 召喚物存活門檻 | 36.4b、36.8a（06 6.29.7） | 一般戰鬥被打倒 ≤ 50% 且 ≥ 10%（±10 個百分點）、Boss 戰被打倒 ≤ 50%；戰意圖騰、殘影係數未模擬 |
| B4 | 召喚持續輪數與預算 | 36.7b、玩法 PM | 特性計入預算後多數召喚縮成 2 輪，看是否放寬召喚預算；拉扯／高台計價初值各每輪 1000‰；召喚物特性係數；17 種召喚技只有 9 種三支進化齊全（骷髏、傀儡、雷靈貼上限） |
| B5 | 召喚物 AI | 3-33e2b #2 | AI 對護盾、拉扯、高台、纏住估值 0；高台圖騰包勝率 60% → 檢查 AI 是否把遠程角色帶上高台 |
| B6 | 刃刻降階 | 3-31（34.1） | 刃刻 2 階，看能否降回 1 階；`per_turn_limit_uses: 8`、`on_hit_rune_permille: 270` |
| B7 | Boss 公平性 | 06 6.29.7、8.25 | Boss 對召喚物 ×2、擋路加分 60；普攻流不能成為打 Boss 唯一解；Boss 戰勝率（無召喚對照包 0–12%）與輪數 6–10 |
| B8 | 戰場變奏 | 33.1a、33.2a | 變奏加價 10%、射程每格 5%、AI `variant_position_bonus` 3、組合器變奏機率、進化模板曝光 |
| B9 | 法力續航 | 3-32d #3 | 目前沒有法力自動回復；技能流 Boss 戰 19% 回合缺法力，要加時先定「對所有單位或只對玩家方」 |

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

1. **寫規格** `docs/phases/PhaseX計畫.md`：目標、範圍外、工作環境、交付項目、驗收條件（每條可驗證）、報告格式。上一階段報告的「待 PM 決定」放在新規格開頭的「PM 決定」表。**規格要小**：一個 agent 的工作量控制在約 30 分鐘、25 萬 token 以內，範圍以「一套規則 ＋ 其測試」為上限。
2. **commit 並 push 規格**。
3. **派實作 agent**：`Agent` 工具，`subagent_type: general-purpose`、`run_in_background: true`，模型依 6.3 選。prompt 範本見 6.4。
4. **等通知**，不要輪詢。使用者問進度時用 `git log --format='%cd %h %s' --date=format:%H:%M <base>..HEAD` 回報。
5. **功能驗收**（自己做，不只看報告）。**檢查分級（2026-10-23 使用者同意，專案 PM 傳達「好」）**：
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
  2. **離開寬限＋橋接區**：離開觸發元素後約 250ms 寬限，觸發元素與卡片之間有透明橋接區；途中經過其他觸發元素不換卡。**例外：格子資訊卡** 換到另一個有內容的格子只等 80ms（`TILE_SWITCH_MS`；2026-10-23 使用者：「從一個草地 到另一個草地字卡響應速度太慢了」），滑到沒內容的地方或離開卡片仍是 250ms。
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
