# Phase OB-1｜#150 開局先玩再定：存檔、選大類、動作閘門

> 來源：`docs/玩法決定紀錄.md` #150、`docs/design/21-探索地圖與城鎮.md` 21.5（共 9 點，第 9 點是玩法 PM 定的細節，commit 5bb8465b；**以 21.5 為準**）。使用者原話：「我感覺什麼都不懂就要決定自己的走向不ok」→「好 寫入」。
> 盤點：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\盤點-150與147.md`（第 1.0、1.1、2、4.3 節）。#150 共 6 段（OB-1～6），本段是第 1 段。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 舊「靶場中」角色（`opening: {seed}`、等級 1） | 升級成 `stage=pick_class`，走新流程 |
| 已完成開局（`opening: null`） | 不受影響，沒有重選 |
| 舊流程建角（`weapon`＋`keywords` 都給） | **只留開發模式**；正式模式拒絕。測試用統一開關（`conftest` 或環境），不要逐一改 35 個測試檔 |
| 版號 | `CHAR_FORMAT` → `trpg-char/13`、`WORLD_RULES_VERSION` → 23、`trpg-wlog` 不升 |
| `OpeningConfirmAction` | 不可刪或改名 |
| 全部武器可試 | 確定時只記大類 |
| 入門招 | **尚未定案**（等使用者答 #148）。一律從資料讀 `range.demos`，不要寫死，之後換招只改資料 |

## 範圍外（後面的段）

- OB-2 三選一延後、正式選定、推薦、屬性重配；OB-3 重選、閃現限制、配點教學；OB-4 戰鬥閘（第 1、2 步以外的敵人）；OB-5／6 前端、台詞、小模擬。
- 本段不改前端畫面；API 欄位要能給之後的前端用。不動 `src/trpg/engine/`（PR-1 平行在改）與 `roguelite/`。

## 交付項目（對應盤點 1.0、1.1）

1. `OpeningState`（`src/trpg/world/state.py:425`）加欄位：`stage`、`weapon_class`、`deferred_offers`、`weapon`、`keywords`、`reselect_used`、`granted_skills`。全部放在 `OpeningState` 內，`CharacterState` 頂層不加欄位。`_upgrade_format` 處理 `/12` → `/13`。
2. `newcomer.yaml` `range` 加 `starters: {melee: one_handed_sword, ranged: bow, focus: fire_staff}`，`RangeContent`、`_range_problems` 加檢查。
3. 新動作 `opening_class {weapon_class}` 與事件：給入門武器、入門招（資料）、4 點自動配（`recommended_allocation`）；`world/step.py` 分派、`api/world_presenter.py` 事件句、`RangeView` 帶階段。
4. `opening_gate` 分階段：`pick_class` 白名單；`starter` 黑名單（`equip` 到 `main_hand`、`change_race`、閃現類，以及 21.5 第 7、9 點列出的）。結構要讓 OB-2、OB-4 接得上。
5. 升級自動配點：`gain_xp` 在 `stage == "starter"` 時照 `recommended_level_up` 配掉。
6. 入門武器不能賣、寄、分解：照盤點是自然做不到，補測試鎖住。

## 受影響的既有功能

見盤點 4.3。所有新判斷都以 `char.opening is not None` 為前提，舊角色與 roguelite 不變。

## 行為一致測試

- 表格測試，**實際跑世界動作**：`pick_class` → `starter` 的轉換；三種大類各拿到正確武器、招、4 點配點；`/12` 三種舊存檔（已完成、靶場中、無 opening）升級結果；`starter` 階段每個被擋與不被擋的動作；升級自動配點數字與 `recommended_level_up` 一致。
- 世界日誌重播：一條新流程的世界日誌能重播一致。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/world`、`tests/api`、`tests/content`、`tests/narrative`、`tests/skillgen`、`tests/roguelite`、`tests/server`、`tests/test_architecture.py` 通過。
- 一場戰鬥 `--log-json` ＋ `replay` 通過。
- `client/openapi.json`、`schema.d.ts` 重產；`corepack pnpm -C client typecheck` 結束碼 0（新必填欄位補 fixture）。

## 報告

`docs/phases/PhaseOB-1報告.md`：逐條驗收、版號與遷移、`opening_gate` 的結構說明（給 OB-2、OB-4）、待 PM 決定。
