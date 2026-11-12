# Phase UI-1 報告：800×600 戰鬥紀錄面板被主角卡蓋住

來源：`docs/phases/PhaseBS-2b報告.md` 待決 1；美術說明在 `claude/art-pm-9-027334:docs/art/BS-2驗收.md` 末節「複驗 BS-2b」。

## 1. 改法

採美術建議的第一種：**800 時紀錄面板從主角卡下緣開始，高度跟著縮**（不收主角卡）。

- `battle/logRoom.ts`：新增純函式 `heroLogCap(dockBottom, heroBottom)`＝紀錄底邊 − 主角卡下緣 − 8px（`LOG_ROOM_GAP`，和選取面板讓位同一個間距），不到 3 行時給 3 行；`logDockMaxHeight(limit, heroCap)` 統一算 `max-height`：選取中照舊用 6A-4c 的 `logLimit`（選取面板在主角卡下面，比較嚴），沒選取時用 `min(58%, heroCap px)`，都沒有時不寫 style。
- `screens/battle/useLogRoom.ts`：新增 `useHeroLogCap(boardRef, bottomKey)`，量 `.bhud-hero` 與 `.log-dock`；戰場、主角卡（例如打開「詳細」）、紀錄大小改變時重量，底部列高度改變（紀錄底邊跟著移）也重量。
- `ui/BattleLogDock.tsx`：`heroCap` 屬性；只加 `max-height`，**不加 `squeezed`**，清單照原本的伸縮方式（`flex: 0 1 320px`）縮短。
- `styles/log-dock.css`：`.log-dock-icon` 加 `flex-shrink: 0`。紀錄被壓矮時原本連圖示一起縮（28→23px），現在只縮清單。1600 沒被壓，不受影響。

**1600 為什麼不變**：1600×900 量到的上限是 552px，紀錄的 58% 是 352px，`min(58%, 552px)` 取 58%，和修前同一個值；同一頁拿掉 style 前後量到的紀錄、清單、圖示位置完全相同（下表）。

## 2. 實機驗證（無頭 Chrome 真 1 倍，DPR 1）

伺服器 `trpg serve --port 9672`（`TRPG_DEV_ROUTES=1`、存檔在暫存區），無頭 Chrome `--headless=new --mute-audio --disable-gpu --remote-debugging-port=9673`，頁面 `/?dev=1&mute=1&anim=0.1`；匕首＋隱蔽＋標記開局，按兩次「結束回合」累積紀錄後展開。修前＝同一頁把紀錄的 style 拿掉再量（A/B）。

| 視窗 | 主角卡 下緣 | 紀錄 上緣（修前 → 修後） | 紀錄高 | 標題列 | 擲骰細節 | 釘選 | 紀錄圖示 |
|---|---|---|---|---|---|---|---|
| 800×600 | 156 | **102 → 164** | 348 → 286 | 被主角卡蓋（`stat-chip`）→ **ok** | 被蓋（`hud-icons`）→ **ok** | 被蓋 → **ok** | ok |
| 1600×900 | 156 | 364 → 364 | 352 → 352 | ok | ok | ok | ok |

- 標題列、鈕的判定是 `document.elementFromPoint(中心點)` 是不是它自己（或子元素）。
- **實際點擊**（800×600，CDP `Input.dispatchMouseEvent` 在鈕的中心點按下放開）：擲骰細節 (138,191) 點兩次 `aria-pressed` false→true→false；釘選 (212,191) 點兩次「釘選」→「取消釘選」(pressed=true)→「釘選」，最後回到沒釘選。
- 1600 修前修後：紀錄 `8,364,252,352`、清單 `21,407,226,266`、圖示 `8,688,30,28` 全同。

## 3. 截圖（`docs/art/shots/ui1/`，jpg 80，都 ≤ 300 KB）

| 檔案 | 內容 | 大小 |
|---|---|---|
| `ui1_log_800.jpg` | 800×600 展開紀錄：標題列與擲骰細節、釘選鈕在主角卡下面；滑鼠停在釘選鈕上，說明卡「釘選：一直顯示完整紀錄」打得開 | 73 KB |
| `ui1_log_1600.jpg` | 1600×900 展開紀錄，版面和修前相同 | 129 KB |

## 4. 測試與檢查

新增 `client/src/ui/ui1LogHeroCap.test.ts`（8 項）：上限算式（800 實量 450−156−8＝286）、量不到時不限、不到 3 行給 3 行、沒選取時只加 `max-height` 不加 `squeezed`、1600 上限 552 走 `min(58%, …)`、選取中照舊用選取面板上限、`BattleScreen` 有接 `useHeroLogCap` 與 `heroCap`、圖示 `flex-shrink: 0`。

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| 相關 vitest（`ui1LogHeroCap`、`battleLogRoom`、`battleHud`、`dev/layoutSmoke`，42 項） | 0 |
| `corepack pnpm -C client test --run`（334 檔、4319 項） | 0 |
| `corepack pnpm -C client build` | 0 |

沒有重產雜湊或快照；沒跑 `scripts/check.py`。

## 5. 待 PM 決定

1. **主角卡很高時**（例如打開「詳細」，最高 30vh）紀錄會跟著縮；可用高度不到 3 行（約 131px）時給 3 行，那時會疊到主角卡下面（和選取面板讓位的 `tight` 同一套）。800×600 目前沒打開詳細時有 286px，不會碰到。保守做法，不另收主角卡。
2. 大世界畫面（`WorldHud`）沒有這個戰鬥紀錄面板，沒動。

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（無衝突）。合併後前端 typecheck 0、vitest 4319 passed、build 0。待決 1（主角卡開「詳細」時紀錄縮到 3 行仍可能疊）：接受，交美術 PM 判斷；2（大世界無此面板）：接受。
