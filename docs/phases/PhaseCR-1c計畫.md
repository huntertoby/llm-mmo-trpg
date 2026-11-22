# Phase CR-1c 計畫：一輪中的主角面板也顯示暴擊傷害＋看目標加成的提示

> 來源：
> - 用字：`docs/design/05-戰鬥.md` 5.4.2 第 8 點（玩法 PM，a0db544dc）。
> - 佇列：開發 PM 交接 (y)。
> - 前一段：`docs/phases/PhaseCR-1b報告.md`。單位卡的做法、`crit_damage_breakdown`、`crit_damage_detail_zh` 都在那裡。
>
> 和 TS-2 平行。TS-2 只動 `scripts/check.py`、`scripts/testmon_select.py`、`pyproject.toml`、`uv.lock`、`.gitignore`、`docs/dev/上手-測試.md`、`tests/infra/`，這段都不要碰。

## 範圍

1. **一輪中的主角面板**（`client/src/run/RunHeroPanel.tsx`）：
   - 和 CR-1b 戰鬥中的單位卡一樣，數值區一律顯示「暴擊傷害 N%」，「▸ 詳細」列出來源，用字相同。
   - 倍率由後端算，共用引擎的 `crit_damage_breakdown`，前端不重算。
   - 一輪中不在戰鬥裡，後端要從主角的裝備、種族、技能組出計算需要的狀態。用現有的、最小的做法，報告寫明怎麼做。
   - 守則 14：這是玩家自己的主角，可以全看。
2. **看目標的加成提示**：
   - 主角或單位身上有「條件看目標」的暴擊傷害修正技時，「▸ 詳細」最後加一行「另有看目標的加成，攻擊預覽時才算」。
   - 沒有這類修正技時不出現。
   - 單位卡和主角面板都要加。
   - 單位卡上，看不到修正技名稱的陣營要不要顯示這一行，照最保守的做：看不到就不顯示。報告寫明。

## 不做

- 不改規則、不改數值，不改 `docs/design/`、`config/` 既有的值。
- 技能卡用字不改（玩法 PM 定）。
- 不碰 TS-2 的檔案。

## 驗收

- **結果不變**：只改顯示，下面都要 different=0：
  - 78 場（`compare78.py`）
  - 442 招逐招預算
  - census 小樣本
  - CLI 快照不應該變。
- **測試**：
  - 主角面板分三種情況：沒截到、頂到上限、最低，再加上來源列。
  - 提示行：有、沒有兩種情況，單位卡和主角面板各測。
  - 看不到修正技名稱的陣營，提示行不顯示。
- **截圖**：存到 `docs/art/shots/cr-1c/`，交美術 PM：主角面板展開「▸ 詳細」，含提示行，1600 寬和 800 寬各一張。
- **靜態檢查**，結束碼都要是 0：
  - ruff、format、mypy、lint-imports
  - `trpg content check`、`classify.py --check`
  - tsc、vitest、build
- **全量檢查**：全部 commit 之後，用 SendMessage 問開發 PM「準備跑 check.py」。**收到「可以跑」才跑**，在那之前不要交件。之後跑 `check.py --all`，再跑 slow 的 parity 和 cli。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseCR-1c報告.md`。
