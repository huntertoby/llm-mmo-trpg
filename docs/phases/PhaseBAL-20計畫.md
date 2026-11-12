# Phase BAL-20 計畫｜AI 估值表補燃燒（餘燼啃咬施放率）

> 開發 PM（第六任）2026-11-12。先讀 `docs/dev/上手-內容資料與模擬.md`、`docs/dev/上手-引擎戰鬥結算.md`（AI 評分那節）。

## PM 決定（玩法 PM 2026-11-12 定，記在 `docs/玩法決定紀錄.md` #149；不要再問）

| # | 決定 |
|---|---|
| D1 | 採做法 A：`content/ai_profiles.yaml` 的 `status_values` 補 `burning: 3`。只改這一個數值，不改引擎、不改技能資料 |
| D2 | 熔爐母獸灌注給幼蜥算有放（合計約 40%），不另處理 |
| D3 | 做法 B（倍率 1200‰）、C（幼蜥改狡猾）不選 |
| D4 | **過關條件**（比照隱蔽分數那次，`docs/玩法決定紀錄.md` 第 263 行附近）：① 我方 fire build 與帶燃燒招的我方 AI 隊友，勝率變動不超過 3 個百分點（附前後對照表）；② 三頭目沒有招每回合施放率跌破 10%（灰燼之心 `heart_inhale` 16% 可以）。**超過任一條就不要合併**：照實寫進報告，由開發 PM 回玩法 PM |

## 依據

- 共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\調查-餘燼啃咬施放率.md`（量測做法、重現指令、做法 A 的試算）。
- 同資料夾 `調查-AI隱蔽分數與碎晶之主兩招.md`（上次同類變更怎麼量我方勝率）。
- `scripts/cb2e_sim.py`（頭目施放率）。

## 交付

1. `content/ai_profiles.yaml` 補 `burning: 3`（一個 commit）。
2. **行為一致測試**：一個 pytest，實際跑 AI 評分（`scoring.py`），斷言 T1 餘燼啃咬對同一目標的分數高於普攻（改前低 6 分，改後應較高），並斷言估值表讀到的 `burning` 值等於內容檔的值（不手寫數字）。
3. 既有 AI 固定種子測試若因此改變：逐一看是行為改變還是種子巧合；只更新期望值或換種子，不改測試要驗的東西，逐項寫進報告。
4. 量測（只在最後各跑一次完整量測，現況與改後用同一批種子配對；程序池最多 6）：
   - 5 種帶 `skill_ember_bite` 的單位每回合施放率（照調查筆記的重現指令）。
   - D4 ①：我方 fire build、帶燃燒招的我方 AI 隊友勝率前後對照。
   - D4 ②：三頭目每招每回合施放率前後對照（`scripts/cb2e_sim.py`）。
5. 報告 `docs/phases/PhaseBAL-20報告.md`：前後對照表、D4 兩條是否通過、重現指令與耗時、「待 PM 決定」最多 10 點；順手更新 `docs/dev/上手-內容資料與模擬.md`（AI 估值表一節）。

## 驗收條件

1. 交付 2 的測試過；`tests/` 下 AI 評分、內容與引擎相關測試檔過（列出跑了哪些）。
2. `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy`、`uv run lint-imports` 結束碼 0；一場 `trpg battle … --log-json` 加 `replay` 通過。
3. 交付 4 三張表齊全；D4 兩條逐條寫明通過或不通過。
4. 除 `content/ai_profiles.yaml`、新測試、必要的測試期望值與文件外沒有變動。

## 工作環境與規矩

- Windows：`uv run python`；新 worktree 先 `uv sync --frozen`，之後加 `UV_NO_SYNC=1`；pytest 平行最多 `-n 8`；不跑完整 `scripts/check.py`、不跑 `trpg sim completion`／`matrix`；量測總時間控制在 30 分鐘內。
- 不啟動伺服器；不結束不是自己啟動的程序；等待用完成通知，不寫 until／while 輪詢迴圈。
- 子 agent 一律 Opus 5.5（`model: "opus"`）並往下傳。
- 不要 push；commit 結尾帶 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
