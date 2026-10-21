# PM 交接文件

> 給接手的開發 PM（新對話中的 Claude）。最後更新：2026-10-20。**Phase 3C、3D、3E-1、3F 與 3-5、3-6 已完成並驗收**；目前在等 **使用者在網頁試玩一整輪**（回饋：規則與玩法交給玩法 PM，介面問題排成 3-7）。接手後先讀第 3.0 節。
> 讀完本檔再讀 `CLAUDE.md` 與 `docs/專案計畫.md`（總覽，約 1 萬字元）即可接手；設計細節依需要讀 `docs/design/` 下的主題檔。

---

## 1. 你的角色

- 你是 **PM**：和使用者討論設計、做技術決定、撰寫階段規格、派實作 agent、驗收、推送。**不要自己寫大量程式碼**，實作交給 agent。
- 使用者（GitHub：huntertoby）是 **最終決策者**，不是工程師。**所有回覆一律用繁體中文**（對話變長、看了很多英文輸出後容易不自覺切成英文，要特別注意）。
- 使用者的習慣：
  - 設計問題喜歡先討論、比較選項，再說「好 寫入」才寫進計畫。重大設計變更請先問，不要自己寫入。
  - 技術細節（程式架構、測試方式、數值初始值）可以由 PM 直接決定，事後簡短說明即可。
  - 回覆要精簡、有結論；用表格整理選項。

## 2. 專案現況

| 階段 | 狀態 | 規格／報告 |
|---|---|---|
| Phase 0 基礎建設 | ✅ 完成 | `docs/phases/Phase0計畫.md`／`Phase0報告.md` |
| Phase 1A／1B／1C 戰鬥核心、環境、掩護 | ✅ 完成 | `Phase1計畫.md`、`Phase1C計畫.md`／各報告 |
| Phase 2A 技能資料、解譯器、條件與 AI | ✅ 完成 | `Phase2A計畫.md`／`Phase2A-1、2A-2報告.md` |
| Phase 2B 新狀態、預算驗證、隨機組合器 | ✅ 完成 | `Phase2B計畫.md`／`Phase2B-1～3報告.md` |
| Phase 2C-1 批次模擬器與報表 | ✅ 完成 | `Phase2C計畫.md` 第 3 節／`Phase2C-1報告.md` |
| Phase 2C-2 控制分派與戰術指令 | ✅ 完成 | `Phase2C計畫.md` 第 4 節／`Phase2C-2報告.md` |
| Phase 2C-3 地圖類型與 build 矩陣 | ✅ 完成 | `Phase2C計畫.md` 第 5 節／`Phase2C-3報告.md` |
| Phase 2C-4 Phase 2 收尾 | ✅ 完成（Phase 2 結束，驗收 11 ✅／2 ⚠️ 觸發移到補模板 B） | `Phase2C-4計畫.md`／`Phase2C-4報告.md` |
| Phase 2D-1 保護、增益與嘲諷 | ✅ 完成（1141 測試；待 PM 決定已處理於 2D 計畫 4.0） | `Phase2D計畫.md` 第 3 節／`Phase2D-1報告.md` |
| Phase 2D-2 負面狀態、術士與收尾 | ✅ 完成（1172 測試；2D 驗收 7 條全 ✅） | `Phase2D計畫.md` 第 4 節／`Phase2D-2報告.md` |
| Phase 2E-1 觸發核心 ＋ 被動 | ✅ 完成（1230 測試；Phase 2 ⚠️ #1、#11 已補） | `Phase2E計畫.md` 第 3 節／`Phase2E-1報告.md` |
| Phase 2E-2 反應技、擋攻擊、姿態 | ✅ 完成（1286 測試） | `Phase2E計畫.md` 第 4 節／`Phase2E-2報告.md` |
| Phase 2E-3 層數、陷阱與收尾 | ✅ 完成（1341 測試；2E 驗收全 ✅；待 PM 決定已處理於 3.2） | `Phase2E計畫.md` 第 5 節／`Phase2E-3報告.md`（5.4 為 2E 驗收總表） |
| Phase 2F 整理（Phase 3 前審查的結論） | ✅ 完成（1395 測試；noqa 19→14；對照戰鬥不變；completion 1800 場異常 0） | `Phase2F計畫.md`／`Phase2F-1、2F-2報告.md` |
| Phase 2G 完整性檢查的補強 | ✅ 完成（1427 測試；12 個示範技能；覆蓋率測試允許清單為空；待 PM 決定見計畫 0.1、0.2） | `Phase2G計畫.md` |
| Phase 2H 冰凍、自身狀態代價、雙屬性與專精 | ✅ 完成（1486 測試；`LOG_FORMAT` /11；待 PM 決定見計畫 0.1、0.2；completion 1800 場、matrix 2400 場異常 0） | `Phase2H計畫.md` |
| Phase 3D 補模板 D（玩法 #5～#12：位移、召喚、區域、改變規則型傳說、賭博型、常見技能、背刺與朝向……） | ✅ 全部完成（3D-1～3D-8d；驗收紀錄在計畫 0.4～0.18） | `Phase3D計畫.md`／`Phase3D-*報告.md` |
| Phase 3E 審查後整理 | 3E-1 ✅；**3E-2、3E-3 排在 Phase 4 之前**（未做） | `Phase3E計畫.md`／`Phase3E-1報告.md` |
| Phase 3F 技能工坊、靶場、複合技能（玩法 #14、#15） | ✅ 全部完成（3F-1～3F-4b；驗收紀錄在計畫 0.1～0.6） | `Phase3F計畫.md`／`Phase3F-*報告.md` |
| **Phase 3 網頁 ＋ roguelite** | 3-1～3-4b ✅（網頁單場戰鬥）；3-5a ✅（一輪核心、存檔 `trpg-run/1`、API、CLI `trpg run`）；3-5b ✅（Boss 地圖 `bandit_lair`）；3-5c ✅（一輪的網頁畫面，兩段平行）；3-6 ✅（自動存檔、重新整理接回、紀錄還原）；**等使用者試玩** | `Phase3計畫.md`（0 節為決定與驗收紀錄，0.11 為 3-5 的使用者決定；第 7 節為 3-5 規格）／`Phase3-*報告.md` |
| Phase 3C 補模板 C（撥開、修正規則、撞擊與觸發、源力與傳說、改寫規則、場景物件原語、收尾） | ✅ 全部完成（3C-1～3C-6b；驗收紀錄與打法差異檢查在計畫 0.5～0.14） | `Phase3C計畫.md`／`Phase3C-*報告.md` |

- 最新 commit 在 GitHub `huntertoby/llm-mmo-trpg`（私人）的 `main`；2026-10-19 起使用者電腦的資料夾就是工作資料夾（見 6.1），push 前確認 `git status` 乾淨即可。
- **3200 個 pytest ＋ 216 個前端 vitest**（`check.py` 一併跑，本機約 1–2 分鐘）；`LOG_FORMAT` 為 `trpg-battle-log/34`；`slow` 預設不跑；平衡測試 `test_demo_map_win_rate_and_length` 標 `xfail(strict=False)`，目前 2 xfail、2 xpass）。
- 主要指令：
  - `trpg battle --map <id> --seed <n> [--ally-build build_a,build_b] [--ally-commander id] [--enemy-commander id] [--log-json f]`、`trpg battle replay f`
  - `trpg map list`（10 張正式地圖，8 種類型都有）
  - `trpg sim maps [--maps a,b] [--seeds 20] [--jobs N] [--enemy-commander id]`：勝率、DPR、控制回合、技能使用率、異常
  - `trpg sim matrix [--seeds 20] [--jobs N]`：12 個 build × 8 種地圖類型，含保護矩陣（20 種子在雲端 `--jobs 2` 約 15 分鐘；`--jobs` 預設用全部核心）
  - `trpg sim skills [--demo] [--random N]`：技能對同階標準敵人的 DPR
  - `trpg sim completion [--maps a,b] [--seeds 20] [--jobs N]`：9 種指揮官設定 × 地圖的完成度檢查（exception／max_actions／draw 必須為 0；全量在雲端 `--jobs 2` 約 14 分鐘；`--jobs` 預設用全部核心）
  - `trpg skills list／budget --all／random --seed N`；`scripts/skill_fuzz.py --count 1000`
- 腳本指揮官（`trpg.sim.commanders`）：`focus_lowest_hp`、`protect_weakest`、`hold_start`、`use_env`。
- **22 個 build**（`content/sim/builds.yaml`；3C、3D 新增 charger、banisher、summoner、gambler、seer、bomber、winged、telekinesis、wallburn、detonator 等；手寫技能約 150 個）。另有 `trpg run new|auto|show`（roguelite 一輪）、`trpg map list`（正式地圖 10 張 ＋ 靶場 `training_range` ＋ Boss 地圖 `bandit_lair`）。以下為 Phase 2 時的舊描述：62 個手寫技能（2G、2H 後每個已定義的骨架、觸發時機、反應事件、條件、原語、狀態、層數都至少有一個手寫技能使用，且每個手寫技能都有 build 或單位裝備，由 `tests/content/test_coverage.py` 檢查）。
- 技能系統（2E 後）：12 個骨架中 11 個可用（只有 `summon` 停用）；觸發時機 `content/skill_triggers.yaml`；層數 `content/stacks.yaml`；技能觸發深度上限 `max_trigger_depth: 3`。`LOG_FORMAT` 為 `trpg-battle-log/11`（2H-1 起；舊紀錄不能重播）。

## 3. 下一步

> 另有 **玩法 PM**（`docs/玩法PM交接.md`）：和使用者討論玩法，決定記在該檔第 3 節（#1～#15，目前全部「已排入」或已完成）。新決定標「已決定，待排入」時由你排進規格，排入後把狀態改成「已排入（階段 X）」。玩法 PM 只改該檔與 `docs/design/`；你改 `docs/phases/`、本檔與程式。玩法 PM 會用 `SendMessage` 傳話給你，你回覆的內容會轉給他。

### 3.0 接手後要做的（2026-10-20）

1. **確認環境**：`git status` 乾淨；`uv run python scripts/check.py` 全過（約 1–2 分鐘）。注意 8000 埠常被使用者自己開的 `scripts/play.py` 佔用（舊版程式）：**不要關使用者的程序**，用 `preview_start` 時會自動改用 8001。
2. ~~3-5c、3-6~~ ✅（驗收紀錄 `Phase3計畫.md` 0.14、0.15；3F-4b 瀏覽器補測記在 `Phase3F計畫.md` 0.6）。試玩回饋已做：~~3-7 體質與升級 HP（玩法 #16）~~、~~3-8 戰鬥畫面重新配置（#17）~~、~~3-9 戰鬥回饋（#18）~~ ✅（`Phase3計畫.md` 10.4、11.4、12.4）。下一個介面段編號用 3-10。
3. **使用者試玩**（`docs/專案計畫.md` 第 14 節 🎮 戰鬥手感檢查）：使用者關掉舊的 `scripts/play.py`，執行 `uv run trpg serve`，開 http://127.0.0.1:8000/ →「開新一輪」。AI 代打 10 種子 2 勝（3-7 後）。試玩回饋：規則與玩法交給玩法 PM，介面問題排成 3-10（已累積：一輪中英雄面板顯示武器）。
4. **Phase 3 結束時派審查 agent**（6.5），範圍 `2c42268..HEAD`（上一次審查涵蓋到 3C／3D 結束；之後是 3E-1、3-5、3F）。結論排進 3E-2／3E-3 或新的整理段。
5. **Phase 4（LLM 技能生成）之前**：做 3E-2（數值上下限以 YAML 為唯一來源、落點函式合併）、3E-3（interpreter 拆成原語 handler 註冊表）；並定 #5 世界觀與美術風格。工坊的選項推導（`trpg.skillgen` 的 `draft_options`）可直接拿來約束 LLM。
6. **畫面與手感提升（2026-10-22 使用者決定，待排入 Phase 3 介面段）**：使用者表示「美術醜醜的就玩不下去」，會擋住戰鬥手感檢查，所以排在手感檢查前。範圍約 3～3.5 段，**只動前端繪圖**（`render/BattleRenderer.ts` 與 `battle/` 的繪圖資料），不改引擎、API，也不改 `docs/專案計畫.md` 3.1（仍是 2D 俯視角）。建議順序：
   - **技能特效**（約 1～1.5 段）：飛行物、命中爆發、範圍效果、9 元素配色與粒子、打擊感（輕微震動、受擊閃白、暴擊放大）、施放蓄力。**必須用「元素 × 形狀 × 遠程／近戰」自動組合**，不可逐招手做（Phase 4 的 LLM 技能數量無上限）。所需資訊在既有事件裡：`skill_used`（施放者、`tiles`）、`damage_dealt`（`element`、`crit`）；形狀從技能卡取得。
   - **原型美術**（約 1～1.5 段）：地形圖塊、角色與敵人圖、配色、字體。先用免費可商用素材（例如 Kenney CC0），授權記在報告裡。目標是「看起來像一款遊戲」，不是定案美術。
   - **高度表現（方案 A）**（約 0.5～1 段）：高格往下畫側面（有厚度）、高台投影、高度差大的邊緣畫懸崖線、單位在高處加底座或陰影。點選與預覽的方式不變。
   - 3D 與等角（方案 B）不做；等到定 #5 世界觀與美術風格時，再用風格樣張比較「精緻 2D／等角／3D」。屆時若選等角或 3D，要修改專案計畫 3.1 的已決定事項，需使用者明確同意。可行性比較（等角約 2～2.5 段，真 3D 約 3～4 段不含美術；引擎與 API 都不用改）由 3D 可行性討論對話整理。

### 3.0.1 使用者已做的決定在哪裡

| 主題 | 位置 |
|---|---|
| Phase 3 網頁與 roguelite（含 3-5：戰鬥間不回復只在營火回滿、隊友維持標準兩名、每場固定經驗、專屬 Boss 地圖） | `Phase3計畫.md` 0.2、0.11 |
| 3C（撥開、改寫規則 6 個全做、觸發 4 個、被動欄位 3、源力、場景物件） | `Phase3C計畫.md` 0.1 |
| 3D（傳說三擇一、常駐傳說限時／整場、致命地形傳送保留屬性影響、被近戰攻擊後轉身等） | `Phase3D計畫.md` 0.1、0.6；`Phase3C計畫.md` 8.2B |
| 技能工坊、靶場、複合技能與排程 | `Phase3F計畫.md` 0 節、第 3、4 節開頭 |
| CI 只手動觸發 | 本檔 6.1 |
| 玩法決定 #1～#15 原文 | `docs/玩法PM交接.md` 第 3 節；設計細節 `docs/design/06-技能.md` 6.14～6.23、`05-戰鬥.md` 5.1 |

### 3.0.2 各段「待 PM 決定」的處理狀態

- 3C、3D、3E-1、3F、3-5a、3-5b 各段報告的「待 PM 決定」都已逐條處理，寫在各計畫檔第 0 節的驗收表（「接受」「平衡階段」「排進某段」）。
- **仍未落地、已排定的**：上面 3.0 第 2 點（3-5c 小修）、第 5 點（3E-2、3E-3）。
- **標「平衡階段」的**：見 3.3 末尾「3C／3D／3F 後新增」。

### 3.0.3 前一位 PM 的備註

- 瀏覽器驗收技巧：用 `javascript_tool` 設定選單（原生 setter ＋ `change` 事件）與點按鈕；地圖格子用 `computer` 點擊前先 `screenshot` 看當下座標框架（框架會在 800×600 與其他大小間變動，點錯格時多半是用了舊截圖的座標）。用 API 查合法動作或錯誤原因很快（`/api/battles/{id}`、`/preview`）。
- 實作 agent 偶爾把多段的戰鬥紀錄拼成一段回報；驗收時自己跑一場 `trpg battle ... --log-json` ＋ `replay` 確認。
- PM 對話很長時用量高；一個大階段結束就更新本檔並交接。

### 3.1 使用者已同意的方向（2026-10-18，已寫入 `docs/專案計畫.md` v0.2.1 第 14 節）

**先確定遊戲能 work，平衡延後。** 順序：

| 階段 | 內容 | 檢查點 |
|---|---|---|
| ~~Phase 2D｜補模板 A~~ ✅ | `shield`、`damage_reduction`、`taunt`、`buff_attr`、`haste`、`heal_over_time`、`cleanse`；`fear`、`silence`、`blind`、`mark` 等狀態；技能可施加 `defending`。解鎖坦克、輔助、治療、術士 | — |
| ~~Phase 2E｜補模板 B~~ ✅ | 事件觸發系統（`on_hit`、`on_damaged`、`on_turn_start`……）→ 被動、反應、姿態、陷阱骨架；層數累積／消耗（`builder_finisher`）；替隊友擋攻擊的反應技。補上 Phase 2 驗收中標 ⚠️ 的兩條（技能層級觸發、觸發深度上限） | — |
| **Phase 3｜網頁 ＋ roguelite** | （原 Phase 4，**已與 Phase 3 調換**）FastAPI ＋ React／PixiJS、roguelite 循環；升級選項先用隨機組合器；隊友指示只做快捷按鈕；美術用色塊 | 🎮 戰鬥手感檢查 |
| **Phase 4｜LLM 技能生成** | （原 Phase 3）LLM 技能生成、LLM 戰術指揮官、LLM 命名、文字隊友指令，接進網頁。開始前要定 #5 世界觀與美術風格 | 🎯 好玩檢查點 |
| 平衡 | 見 3.3 | — |

- 使用者選這個順序的理由：先有畫面才能判斷好不好玩；試玩時 build 種類要齊全（所以模板 A、B 在網頁之前）。
- 召喚物範圍最大，放在更後面。
- 2E 使用者決定（2026-10-19）：拆三段；層數支援施放者型與目標型；姿態 1 AP 進入、持續到取消；陷阱對敵方隱藏。見 `Phase2E計畫.md` 0.2。
- **Phase 3 是下一步，規模很大**：寫規格前先跟使用者確認拆法（建議方向：FastAPI 本機 API 與戰鬥狀態序列化 → 前端格子渲染與操作 → 技能／反應／預覽等戰鬥 UI → roguelite 循環與存檔），每段控制在約 30–45 分鐘；前端技術（React ＋ PixiJS）見 `docs/design/12-技術與結構.md`。使用者要在瀏覽器試玩，做 `docs/專案計畫.md` 第 14 節的「戰鬥手感檢查」。
- Phase 3 時要處理的既有約定：滑倒退回以 teleport 事件表示（3.4）；陷阱只對放置者陣營顯示（CLI 已用 `^`）；`pending`／`resume` 的反應詢問要有 UI。

### 3.1.1 Phase 2 還沒補的模板（**已由 Phase 3C、3D 全部補齊**；本節僅供歷史參考）

| 類別 | 還沒做的 | 影響 |
|---|---|---|
| 召喚 | `summon` 骨架（唯一停用的骨架） | 召喚流 build 做不出來；之前決定放後面 |
| 改寫規則型（傳說） | `grant_ap`、`reset_cooldown`、`cheat_death`、`copy_skill`、`redirect_damage`、`extra_reaction` | 傳說稀有度沒有專屬內容 |
| 修正型被動 | 「燃燒中的敵人受到傷害 +10%」這類常駐加成（2E 只做觸發型，決定 E） | — |
| 增益互動 | `steal_buff`、驅散敵方增益、`restore_resource` | — |
| 零星原語 | `delayed_damage`、`execute_bonus`、`swap`、`leap`、`grant_advantage_next`、`ignite_tile`（`conceal` 已有，是狀態 `concealed`） | 部分可用現有原語近似 |
| 條件 | `moved_this_turn`、`adjacent_ally`、`target_isolated`、`first_round`（現有 5 種） | 連段骨架的「本回合做過某事」做不出來 |

PM 建議（已跟使用者說過）：不擋 Phase 3；召喚與連段條件是整類 build 的缺口，Phase 3 試玩後看需要再排「補模板 C」。

### 3.1.2 加快階段速度（2E 的經驗，寫下一份規格時照做）

- 2E 三段實際：2E-1 48 分、2E-2 56 分、2E-3 100 分（規格估 30 分）。分析 agent 紀錄：約一半時間在 **等全量 pytest／`check.py`**（單次 6–10 分鐘，每段跑 2–3 次），另一半是模型思考與撰寫；2E-3 多出的約 30 分鐘是全量 completion（14 分）＋ matrix（約 15 分）。
- 規格的「工作環境」一節要寫明：**開發中只跑相關測試檔；全量 `check.py` 只在子階段最後跑一次**（commit 前只跑 ruff、mypy 與相關測試）。
- 大型模擬（completion、matrix）**不要放在實作子階段裡**：獨立成一個小收尾段，或由 PM 驗收時自己在背景跑。
- `pytest-xdist` 已引入（2026-10-19），全量測試平行跑；工作環境改到使用者電腦（見 6.1）。
- 一段的範圍以「一套規則 ＋ 其測試」為上限；像 2E-2 一次三套規則（反應、攔截、姿態）就會超時。

### 3.2 2E-3 報告「待 PM 決定」的處理（已接受；寫 Phase 3 規格時放進開頭的「PM 決定」表）

| # | 項目 | 決定 |
|---|---|---|
| 1 | 放置陷阱時同格被拒會洩漏隱藏陷阱的存在 | 接受；目前只有玩家放陷阱。敵方陷阱屬第 5 節的待決定問題，屆時一起處理 |
| 2 | 放置者倒下或逃離時其陷阱全部移除 | 接受 |
| 3 | 傳送不觸發陷阱，步行與強制位移會 | 接受 |
| 4 | 施放者型 `add_stack` 要命中才累積 | 接受 |
| 5 | 目標型層數到期那一輪回合開始時清空 | 接受 |
| 6 | 陷阱超過觸發深度上限時留在原地、不結算 | 接受 |
| 7 | 陷阱觸發後被定身或暈眩則移動中止 | 接受 |
| 8 | 陷阱係數 800、終結技期望 500、AI 陷阱機率 700 等初值；`build_trapper` 常把陷阱放在角落、灰燼地雷很少用 | 平衡階段（3.3） |
| 9 | 矩陣報表沒有 `trigger_limit` 欄位（抽樣 360 場為 0） | 接受；平衡階段或需要時再加欄位 |
| 10 | 傷害標籤改為「（格擋/加成 ×x）」 | 接受 |

2C-4、2D、2E-1、2E-2 的「待 PM 決定」都已處理，見各計畫檔開頭的 PM 決定表（`Phase2D計畫.md` 0、4.0；`Phase2E計畫.md` 0.1、4.0、5.0）。

### 3.3 延後到平衡階段的累積待辦

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

### 3.4 已接受的技術細節（不用再問）

2C-1～2C-3 報告的其他「待 PM 決定」都已接受，例如：傷害只算實際扣血、友軍誤傷另列；墜落／致命地形／爆炸／燃燒的傷害由引擎帶來源；`boss_burst` 門檻 60%；滑倒停在友軍格時退回最近空格（以 teleport 事件表示，客戶端之後要處理）；policy／指揮官 factory 必須是模組層級類別（`--jobs` 要 pickle）。

## 4. 已確認但尚未落地的設計決定

- 戰鬥節奏目標：一般遭遇 4–6 輪、Boss 戰 6–10 輪。
- 元素與表面的中文名稱之後再定。
- 吊橋深淵兩端的繞行通道先接受。
- 冰窟＝致命地形（`ice_hole`）＋可破壞的薄冰（`thin_ice`）。

## 5. 仍待使用者決定的設計問題

- **敵方陷阱（2026-10-19 標記）**：2E 不給敵人陷阱技能（引擎已對稱支援，陷阱只有放置者陣營看得見）。之後可能讓敵人有陷阱，屆時要給玩家「察覺」的機會，例如相鄰時顯示，或用感知判定。建議在 Phase 3 網頁試玩時決定。

見 `docs/專案計畫.md` 第 3.2 節：#5 世界觀與美術風格（新 Phase 4 寫 prompt 前要定；Phase 3 網頁先用色塊）、#8 技能等級成長方式、#9 技能欄位數量。

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

1. **寫規格** `docs/phases/PhaseX計畫.md`：目標、範圍外、工作環境、交付項目、驗收條件（每條可驗證）、報告格式。上一階段報告的「待 PM 決定」放在新規格開頭的「PM 決定」表。**規格要小**：一個 agent 的工作量控制在約 30 分鐘、25 萬 token 以內，範圍以「一套規則 ＋ 其測試」為上限。
2. **commit 並 push 規格**。
3. **派實作 agent**：`Agent` 工具，`subagent_type: general-purpose`、`run_in_background: true`，模型依 6.3 選。prompt 範本見 6.4。
4. **等通知**，不要輪詢。使用者問進度時用 `git log --format='%cd %h %s' --date=format:%H:%M <base>..HEAD` 回報。
5. **功能驗收**（自己做，不只看報告）：`uv run python scripts/check.py`；挑一張地圖換一個種子跑 `trpg battle ... --log-json` 再 `trpg battle replay`；抽查一兩個關鍵設計（例如引擎內沒有浮點 log、沒有 `random`）。大型模擬（completion、matrix）由 PM 在驗收時於背景跑，不放進實作子階段。
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
4. 開發中只跑相關測試檔；每次 commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**完整的 `uv run python scripts/check.py` 只在最後跑一次**。
5. 不要 push。
6. 逐條自我檢查驗收條件（要有測試名稱或指令輸出為證）。依邏輯分 commit，結尾帶 Co-Authored-By 一行（依你的系統提示）。
7. 撰寫並 commit `docs/phases/PhaseX報告.md`；若新增了複雜度類 noqa（C901、PLR0911、PLR0912、PLR0915），在報告中逐一列出理由。

規格沒寫到的採最保守做法並寫進報告「待 PM 決定」。不要修改 `docs/專案計畫.md`、`docs/design/`、`CLAUDE.md`、`docs/phases/` 下的計畫檔。

最終回覆用繁體中文：commit 列表、驗收逐條結果、「待 PM 決定」（最多 10 點）、一段代表性的 CLI 輸出節錄。
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

### 6.6 注意事項（踩過的坑）

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
