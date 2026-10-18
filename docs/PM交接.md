# PM 交接文件

> 給接手的 PM（新對話中的 Claude）。最後更新：2026-10-18 晚上，Phase 2C-3 完成時。
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
| Phase 1A／1B／1C 戰鬥核心、環境、掩護 | ✅ 完成 | `Phase1計畫.md`、`Phase1C計畫.md`／各報告 |
| Phase 2A 技能資料、解譯器、條件與 AI | ✅ 完成 | `Phase2A計畫.md`／`Phase2A-1、2A-2報告.md` |
| Phase 2B 新狀態、預算驗證、隨機組合器 | ✅ 完成 | `Phase2B計畫.md`／`Phase2B-1～3報告.md` |
| Phase 2C-1 批次模擬器與報表 | ✅ 完成 | `Phase2C計畫.md` 第 3 節／`Phase2C-1報告.md` |
| Phase 2C-2 控制分派與戰術指令 | ✅ 完成 | `Phase2C計畫.md` 第 4 節／`Phase2C-2報告.md` |
| Phase 2C-3 地圖類型與 build 矩陣 | ✅ 完成 | `Phase2C計畫.md` 第 5 節／`Phase2C-3報告.md` |
| **Phase 2C-4 Phase 2 收尾** | 🔨 實作中 | `Phase2C-4計畫.md`（範圍見第 3 節） |

- 最新 commit 在 GitHub `huntertoby/llm-mmo-trpg`（私人）的 `main`；使用者電腦已同步到 `02b17ba`（之後只多了文件 commit）。
- 1037 個測試（6 個 `slow` 預設不跑，其中 3 個平衡測試已知失敗）。
- 主要指令：
  - `trpg battle --map <id> --seed <n> [--ally-commander id] [--enemy-commander id] [--log-json f]`、`trpg battle replay f`
  - `trpg map list`（10 張正式地圖，8 種類型都有）
  - `trpg sim maps [--maps a,b] [--seeds 20] [--jobs N] [--enemy-commander id]`：勝率、DPR、控制回合、技能使用率、異常
  - `trpg sim matrix [--seeds 20] [--jobs N]`：6 個 build × 8 種地圖類型（20 種子約 9 分鐘，`--jobs 2`）
  - `trpg sim skills [--demo] [--random N]`：技能對同階標準敵人的 DPR
  - `trpg skills list／budget --all／random --seed N`；`scripts/skill_fuzz.py --count 1000`
- 腳本指揮官（`trpg.sim.commanders`）：`focus_lowest_hp`、`protect_weakest`、`hold_start`、`use_env`。

## 3. 下一步

### 3.1 使用者已同意的方向（2026-10-18）

**先確定遊戲能 work，平衡延後。** 平衡要等效果模板補齊後再一次調，不然補完又要重調。順序：

1. **2C-4｜Phase 2 收尾**（小，一位實作者）
2. **補模板 A**：`shield`、`damage_reduction`、`taunt`、`buff_attr`、`haste`、`heal_over_time`、`cleanse`，加上 `fear`、`silence`、`blind`、`mark` 等狀態；讓技能能施加 `defending`。解鎖坦克、輔助、治療、術士。
3. **補模板 B**：事件觸發系統（`on_hit`、`on_damaged`、`on_turn_start`……）→ 啟用被動、反應、姿態、陷阱骨架；層數累積／消耗（`builder_finisher`）；替隊友擋攻擊的反應技。
4. **最小網頁畫面**（Phase 4 的一部分提前：格子地圖、點選移動與攻擊）。
5. **Phase 3** LLM 技能生成（含 LLM 戰術指揮官）。
6. 之後才回頭做平衡（見 3.3）。召喚物範圍最大，放更後面。

（模板 A／B 與網頁的階段名稱、是否改動 `docs/專案計畫.md` 第 14 節的階段順序，由接手 PM 和使用者確認後再寫入。）

### 3.2 2C-4 的範圍（PM 與使用者已討論，接手 PM 寫成規格）

| # | 項目 |
|---|---|
| 1 | 每場戰鬥都打得完：查 `lava_crossing` 有 1 場打滿 30 輪平手的原因（疑似雙方都不願過岩漿），修 AI 或地圖 |
| 2 | 每個 AI 行為模式都給基本的環境權重（目前 brute／archer／guard 的 env 權重為 0，`use_environment` 指令乘上去還是 0） |
| 3 | 3 個失敗的 slow 平衡測試改為已知問題（例如 `xfail` 附原因），勝率目標寫進報告 |
| 4 | 10 張地圖 × 20 種子，在「無指揮官」與各腳本指揮官設定下都沒有 exception／max_actions／draw |
| 5 | 逐條對照 `docs/專案計畫.md` 第 14 節 Phase 2 驗收，在報告中打勾，正式結束 Phase 2 |

**不做**：勝率、技能數值、AI 權重、指令加成的平衡；坦克強弱；火焰箭超標。

### 3.3 延後到平衡階段的累積待辦

- 勝率：大多數地圖我方 75–95%，`oil_depot` 10–45%（偏難可以保留）；目標 35–65%、一般遭遇 4–6 輪。
- build 矩陣（`Phase2C-3報告.md`）：`build_storm` 8 種類型中 7 種前段；`build_tank` 0 種（原因是 **沒有保護型模板**，坦克只是少帶技能的戰士，補模板 A 後重測）。
- AI 很少用控場、位移、場地技能；控制回合每場接近 0。所有 AI 權重、狀態價值、指令加成（集火 ×1.5 的算法等）未經模擬。
- `skill_fire_bolt` 的 DPR 超過同階 P95 × 1.2。
- 結構型原語點數偏低（2B-3 #3）；技能報表在平地 1 對 3，控場、位移、光環骨架的 DPR 偏低，可能要另設情境。
- 冰面 DEX DC12 滑倒對 AI 的影響未評估；敵方集火時 `bridge_chasm` 我方勝率反而上升，原因未查。
- 代價折抵總上限已定為 +500‰；組合器權重已搬到 `content/skill_composer.yaml`。

### 3.4 已接受的技術細節（不用再問）

2C-1～2C-3 報告的其他「待 PM 決定」都已接受，例如：傷害只算實際扣血、友軍誤傷另列；墜落／致命地形／爆炸／燃燒的傷害由引擎帶來源；`boss_burst` 門檻 60%；滑倒停在友軍格時退回最近空格（以 teleport 事件表示，客戶端之後要處理）；policy／指揮官 factory 必須是模組層級類別（`--jobs` 要 pickle）。

## 4. 已確認但尚未落地的設計決定

- 戰鬥節奏目標：一般遭遇 4–6 輪、Boss 戰 6–10 輪。
- 元素與表面的中文名稱之後再定。
- 吊橋深淵兩端的繞行通道先接受。
- 冰窟＝致命地形（`ice_hole`）＋可破壞的薄冰（`thin_ice`）。

## 5. 仍待使用者決定的設計問題

見 `docs/專案計畫.md` 第 3.2 節：#5 世界觀與美術風格（Phase 3 寫 prompt 前要定）、#8 技能等級成長方式、#9 技能欄位數量。

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
- **平行派工實例（2C-2／2C-3）**：兩個 `isolation: "worktree"` 的 agent 同時跑，完成後在 main 上 `git merge --ff-only <先完成的分支>`、再 `git merge --no-ff <另一個分支>`；這次沒有衝突。合併後自己跑一次 `check.py` 與一場 `--log-json`／`replay`。
- **同步失敗的殘留**：沒有刪除權限時 merge 會半途失敗，HEAD 不變但留下一堆未追蹤的新檔案。取得刪除權限後，刪掉 `.git/index.lock`、`.git/objects/maintenance.lock`、`.git/objects/pack/tmp_*`，以及 `git status` 列出的、正好是 bundle 裡新增的那些未追蹤檔案，再重新 `fetch`／`merge`。
- 大型模擬（`sim matrix --seeds 20`）要 9 分鐘以上，agent 會在背景等；通知可能先來一兩次「仍在等待」，不用處理。

## 7. 節省 token 的原則

- PM 對話本身是最大的隱藏成本（每一步都會重新處理整段對話）。**對話變長時（例如完成一個大階段後），更新本檔並請使用者開新對話。**
- 實作 agent 預設用 Sonnet；規格要小；agent 開發中只跑相關測試（CLAUDE.md 守則 11）。
- PM 讀文件只讀需要的：總覽 ＋ 對應的 `docs/design/` 主題檔 ＋ 最新一份報告。不要讀整份舊報告或舊對話。
