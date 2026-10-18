# PM 交接文件

> 給接手的 PM（新對話中的 Claude）。最後更新：2026-10-18，Phase 2A 全部完成時。
> 讀完本檔再讀 `CLAUDE.md` 與 `docs/專案計畫.md`（總覽，約 1 萬字元）即可接手；設計細節依需要讀 `docs/design/` 下的主題檔。

---

## 1. 你的角色

- 你是 **PM**：和使用者討論設計、做技術決定、撰寫階段規格、派實作 agent、驗收、推送與同步。**不要自己寫大量程式碼**，實作交給 agent。
- 使用者（GitHub：huntertoby）是 **最終決策者**，不是工程師，偏好用繁體中文溝通。
- 使用者的習慣：
  - 設計問題喜歡先討論、比較選項，再說「好 寫入」才寫進計畫。重大設計變更請先問，不要自己寫入。
  - 技術細節（程式架構、測試方式、數值初始值）可以由 PM 直接決定，事後簡短說明即可。
  - 回覆要精簡、有結論；用表格整理選項。

## 2. 專案現況

| 階段 | 狀態 | 規格／報告 |
|---|---|---|
| Phase 0 基礎建設 | ✅ 完成 | `docs/phases/Phase0計畫.md`／`Phase0報告.md` |
| Phase 1A 戰鬥核心 | ✅ 完成 | `Phase1計畫.md` 第 5 節／`Phase1A報告.md` |
| Phase 1B 環境與戰術 | ✅ 完成 | `Phase1計畫.md` 第 6 節／`Phase1B報告.md` |
| Phase 1C 掩護與牆壁 | ✅ 完成 | `Phase1C計畫.md`／`Phase1C報告.md` |
| Phase 2A-1 技能資料與解譯器 | ✅ 完成 | `Phase2A計畫.md` 第 5 節／`Phase2A-1報告.md` |
| Phase 2A-2 條件與 AI | ✅ 完成 | `Phase2A計畫.md` 第 6 節／`Phase2A-2報告.md` |
| **Phase 2B 預算與隨機組合器** | ⏭️ 下一步 | 尚未撰寫規格 |

- 2A 的規則決定（使用者已同意）：範圍技能每個目標各擲命中骰；技能直接效果預設不誤傷友方，`affects: all` 為可選的「敵我不分」標記（2B 給預算折扣）；有害表面敵我不分、有益表面只幫施放者陣營、地圖表面中立；法力戰鬥中不回復；冷卻 1 ＝ 每回合一次；法術屬性倍率 0.5。

- 最新 commit 在 GitHub `huntertoby/llm-mmo-trpg`（私人）的 `main`；CI（Windows／Ubuntu × Python 3.12／3.13）全綠。
- 702 個測試（另有 4 個 `slow` 平衡測試預設不跑）；17 個示範技能（`trpg skills list`）；`trpg battle --map <id> --seed <n>` 可在終端機跑完整戰鬥並重播。
- 示範地圖：`test_flat_6x6`、`test_heights_8x8`、`bridge_chasm`、`oil_depot`、`swamp`、`ruined_fort`。

## 3. 下一步：Phase 2B

依 `docs/專案計畫.md` 第 14 節 Phase 2 與 `docs/design/06-技能.md`。技能格式與解譯器已完成（2A），剩下：

| 子階段 | 內容 |
|---|---|
| 2B | 預算計算（6.5，含 AP 係數、`affects: all` 的折扣）、硬性上限與互斥規則（6.6）、骨架（6.9，`content/skeletons/`）、稀有度限制（6.12）、隨機組合器；新狀態（slow、root、stun、weaken、vulnerable、bleed、poison）與控制遞減；預算驗收：隨機 1,000 個技能全部可執行且無例外 |
| 2C | 批次模擬器與報表（DPR、控制回合、異常）、build × 地圖類型矩陣（6.8）、補齊 8 種地圖類型（`docs/design/05-戰鬥.md` 5.1）、示範地圖與敵人的平衡 |

寫 2B 規格前先讀 `docs/phases/Phase2A-2報告.md` 的第 6、7 節。**2A-2 遺留、PM 已有傾向的待辦**：
1. **平衡**：加了技能後我方勝率偏高（bridge_chasm 90%、ruined_fort 85%），敵人技能 80 場只用 62 次 → 2C 統一調整（陣容、敵人技能、英雄法力）。
2. **AI 效能**：ruined_fort 每動作中位數約 7 ms（目標 ≤ 8 ms），餘裕小。2B 加入隨機技能後若變慢，優先做視線快取與合併重複預覽。
3. **冷門技能**：隱匿、喚潮、石牆術幾乎不被 AI 使用（缺少對應的位置價值）。2C 的 build 矩陣會暴露這個問題；可考慮讓 AI 評估「水面＋雷電」這類組合。
4. **條件語意**（2A-2 報告第 6 節第 4 點）：技能層級的目標條件在範圍技能上為「至少一個對象成立」——暫時接受。
5. `legal_actions_with_areas` 新引擎 API：接受。

## 4. 已確認但尚未落地的設計決定

- 戰鬥節奏目標：一般遭遇 4–6 輪、Boss 戰 6–10 輪（使用者已同意）。
- 元素與表面的中文名稱之後再定，現在的暫定即可。
- 吊橋深淵兩端開了繞行通道（為了節奏），先接受，做地圖類型時再檢討。

## 5. 仍待使用者決定的設計問題

見 `docs/專案計畫.md` 第 3.2 節，重點：
- #5 世界觀與美術風格（未定；Phase 3 寫 prompt 前要定）
- #8 技能等級成長方式（暫定靠使用成長）
- #9 技能欄位數量（暫定主動 6、被動 2、反應 1）

## 6. 工作流程（照做即可）

### 6.1 環境

- 雲端工作區通常是全新的：先用 `mcp__claude-code-remote__add_repo`（owner `huntertoby`、repo `llm-mmo-trpg`、access `push`）加入並 clone，路徑依工具回傳。
- **PyPI 要走代理**：每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`，再 `uv sync`。
- 使用者電腦的資料夾：`F:\PythonProject\LLM-MMO-TRPG`（也是 git repo，origin 指向 GitHub）。透過 `mcp__remote-devices__*` 存取；那邊的 shell **沒有網路**、Python 只有 3.10，不能在那邊跑專案。

### 6.2 一個階段的流程

1. **寫規格** `docs/phases/PhaseX計畫.md`：目標、範圍外、工作環境、交付項目、驗收條件（每條可驗證）、報告格式。上一階段報告的「待 PM 決定」放在新規格開頭的「PM 決定」表。**規格要小**：一個 agent 的工作量控制在約 30 分鐘、25 萬 token 以內。
2. **commit 並 push 規格**。
3. **派 agent**：`Agent` 工具，`subagent_type: general-purpose`、`run_in_background: true`、**`model: sonnet`**（規格清楚的實作用 Sonnet 省額度；若品質不佳再換 Opus）。prompt 範本見 6.3。
4. **等通知**，不要輪詢。使用者問進度時用 `git log --format='%cd %h %s' --date=format:%H:%M <base>..HEAD` 回報。
5. **驗收**（自己做，不只看報告）：`uv run python scripts/check.py`；挑一張地圖換一個種子跑 `trpg battle ... --log-json` 再 `trpg battle replay`；抽查一兩個關鍵設計（例如引擎內沒有浮點 log、沒有 `random`）。
6. **push**，然後 **同步到使用者電腦**（6.4）。
7. 向使用者回報：做出了什麼（附一小段戰鬥紀錄）、待決定項目怎麼處理、哪些需要使用者決定。

### 6.3 派 agent 的 prompt 範本

```
你是這個專案的實作者（implementer）。PM 已寫好規格，請實作 **Phase X｜名稱**。

專案位置：<repo 路徑>（main 分支，目前 HEAD 為 <hash>）。

請依序：
1. 讀 `CLAUDE.md`（特別是守則 11 節省 token）。
2. 讀 `docs/phases/PhaseX計畫.md`——這是你的規格。
3. 讀規格指定的前一階段報告與 `docs/design/` 主題檔（只讀指定的）。
4. 每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`；用 `uv sync` 與 `uv run python scripts/check.py` 驗證。
5. 只在 repo 內工作，不要使用 mcp__remote-devices__ 工具，不要 push。
6. 逐條自我檢查驗收條件（要有測試名稱或指令輸出為證）。依邏輯分 commit，結尾帶兩行：
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   Claude-Session: <本對話的 session 連結>
7. 撰寫並 commit `docs/phases/PhaseX報告.md`。

規格沒寫到的採最保守做法並寫進報告「待 PM 決定」。不要修改 `docs/專案計畫.md`、`docs/design/`、`CLAUDE.md`、`docs/phases/` 下的計畫檔。

最終回覆用繁體中文：commit 列表、驗收逐條結果、「待 PM 決定」（最多 10 點）、一段代表性的 CLI 輸出節錄。
```

（commit 結尾的 session 連結以新對話的系統提示為準。）

### 6.4 同步到使用者電腦

使用者電腦那邊沒有網路，用 git bundle：

```bash
# 雲端：產生從使用者電腦目前 HEAD 到 main 的 bundle
git bundle create /mnt/user-data/outputs/sync.bundle <使用者電腦的 HEAD>..main
```

1. `mcp__remote-devices__device_commit_files` 把 `/mnt/user-data/outputs/sync.bundle` 寫到 `F:\PythonProject\LLM-MMO-TRPG\sync.bundle`。
   **bundle 檔名每次都要不同**（例如 `sync-<hash>.bundle`）：同名檔案可能被快取成舊版，導致 `Already up to date` 卻沒有更新。
2. 若 git 回報 `unable to unlink … Operation not permitted`，先用 `mcp__remote-devices__device_request_delete_permission`（資料夾 `F:\PythonProject\LLM-MMO-TRPG`）取得刪除權限，清掉 `.git/*.lock` 與失敗 merge 留下的未追蹤檔案後重試。每個新對話都要重新取得。
3. `mcp__remote-devices__device_bash`：等檔案出現（迴圈檢查 `[ -s sync.bundle ]`）後 `git fetch sync.bundle main && git merge --ff-only FETCH_HEAD`，再 `rm sync.bundle`。**不要用 `-q`**，失敗才看得到原因。
3. 使用者電腦的 HEAD 用 `git log --oneline -1` 查。git 的檔案權限差異已用 `core.fileMode false` 處理。
4. 使用者也可以自己在 Windows 執行 `git pull`（origin 已設定為 GitHub）。

### 6.5 注意事項（踩過的坑）

- **Agent 可能中途停止**（用量上限或被手動停止）。進度會留在 commit 裡；派一個新的「收尾」agent：說明前一位的最後 commit、請它核對驗收條件、補齊缺漏、寫報告，不要重做。
- **stop hook 會要求 push 未推送的 commit**：agent 還在跑時，工作區可能有未 commit 的半成品，**不要替它 commit**；已 commit 的中途進度可以 push，但要告訴使用者「尚未驗收」。
- **平行工作**（例如文件整理與程式實作同時進行）用 `isolation: "worktree"` 的 agent，完成後再合併；`.claude/` 已加入 `.gitignore`。
- **建立新的 GitHub repo** 在這個環境做不到（權限只限已加入的 repo），要請使用者在網頁上建。
- 平衡調整很耗 token：讓 agent 寫腳本輸出摘要表，由 PM 決定數值，不要讓 agent 反覆試。

## 7. 節省 token 的原則

- PM 對話本身是最大的隱藏成本（每一步都會重新處理整段對話）。**對話變長時（例如完成一個大階段後），更新本檔並請使用者開新對話。**
- 實作 agent 預設用 Sonnet；規格要小；agent 開發中只跑相關測試（CLAUDE.md 守則 11）。
- PM 讀文件只讀需要的：總覽 ＋ 對應的 `docs/design/` 主題檔 ＋ 最新一份報告。不要讀整份舊報告或舊對話。
