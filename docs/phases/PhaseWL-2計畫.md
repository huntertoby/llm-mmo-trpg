# Phase WL-2 計畫：地圖類型清單搬進資料檔

> 來源：使用者原話（專案 PM 轉，2026-11-22）：「搬」。問題是：要不要把 `src/trpg/content/maps.py` 的 `Archetype` Literal 和 `ARCHETYPES` 11 種搬進資料檔，讓以後加新類型的地圖只改資料。
> 做法比照 WL-1 a 段（骨架清單改從資料讀）。
>
> 原則：**結果完全不變**，只是加新類型時不用改程式。
>
> 這段和 KD-1、HC-8 平行。**不要改**：
> - `content/tuning_fields.yaml`、`api/tuning/`；
> - `src/trpg/engine/`、`content/rules/`；
> - `client/src/world/growthPanel.ts`、`OpeningDialog.tsx`。
>
> `classes.yaml` 和清單文件三邊都會改，合併時保留兩邊。

## 範圍

1. **類型清單改從資料讀**：
   - `maps.py` 的 `Archetype` Literal 和 `ARCHETYPES`，改成以資料為唯一來源。資料放哪由你定，例如 `content/maps/archetypes.yaml`，或每張地圖檔的欄位。
   - 型別改成 `str`，載入時驗證。不認得的類型由 `trpg content check` 擋下，錯誤訊息用中文。
   - 會用到清單順序的地方，照資料檔的順序；結果要和現在逐字相同。
2. **特殊用途改用資料欄位**：
   - `TEST_ARCHETYPE`、`TRAINING_ARCHETYPE`、`BOSS_ARCHETYPE` 這三種不進一般抽選。改用資料欄位表示，例如 `in_random_pool: false`。
   - 程式不能依賴特定類型的 id 字串。真的需要找「靶場用哪張」這類的，改成讀資料欄位，例如 `role: training`。
3. **盤點並改掉寫死的分支**：
   - 先 grep，找出依類型 id 寫死的分支。範圍包括：
     - roguelite 抽圖、sim 預設地圖、`sim/matrix.py`、`cli/sim.py`；
     - `api/sessions.py`、`world/battlefield.py`、`world_map.py`、`world_season.py`、`regions.py`、`workshop.py`、`giant_checks.py`；
     - 前端；
     - `attack_flow_report`。
   - 列成一張表寫進報告：檔案、行號、原本怎麼寫、改成讀哪個欄位。
   - 屬於行為的分支（某種類型有特殊玩法）保留，但要確認：加一種沒有特殊行為的新類型時，這些分支都會走預設，不會報錯。
   - 測試裡寫死的類型數（11），改成讀 `tests/content_counts.json` 快照。做法同 WL-1 a 段。
4. **新類型只寫資料**：
   - 用測試內容多加一種類型，只寫資料，要能載入、驗證、抽選、開戰。
   - 加一個 `in_random_pool: false` 的類型，確認它不會被抽到。
5. **收尾**：`classify.py --check` 要通過，`--unused` 沒有輸出，並重產清單文件。

## 不做

- 不改任何地圖內容和抽選權重，也不改數值。
- 不改 `docs/design/`、`config/`。

## 驗收

- **結果完全不變**：下面這些都要 different=0：
  - 442 招逐招預算；
  - a 段那組 78 場（`compare78.py`）；
  - census 小樣本；
  - CLI 快照、parity、前端夾具；
  - roguelite 同一個種子抽到的地圖序列。這一項要寫測試鎖住。
- **新類型只寫資料**：第 4 項的測試要通過。
- **靜態檢查**：下面這些的結束碼都要是 0：
  - ruff、format、mypy、lint-imports；
  - `trpg content check`、`classify.py --check`；
  - tsc、vitest、build。
- **全量檢查**：全部 commit 之後，**先問開發 PM「準備跑 check.py」**，收到回覆才跑。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseWL-2報告.md`。
