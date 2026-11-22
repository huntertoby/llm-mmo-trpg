# Phase HC-8 計畫：寫死清單最後兩組（畫面 2 句、工坊工具 10 項設定）

> 來源：使用者回答專案 PM 的兩題，原話「都搬」。專案 PM 於 2026-11-22 轉達。
> - 畫面寫死的 2 句：`ts-ui-text` 2 筆。
> - 工坊工具自己的 10 項設定：`py-api-tuning-tool-settings` 10 筆。
>
> 另外三組**維持不搬**：schema 上限 18 筆、llm 預設 8 筆、無檔時的備用值 10 筆。
> 暴擊倍率可變還在等玩法 PM 出題。**`_damage_rolls` 的 ×2 不要動。**
>
> 這段和 KD-1 平行。**不要改** `content/tuning_fields.yaml`、`api/tuning/objects.py`、引擎、`content/rules/`，那些是 KD-1 在改的檔案。

## 範圍

1. **屬性點的 2 句說明改從資料組字**：
   - 要改的兩處：
     - `client/src/world/growthPanel.ts` 的 `ATTR_PER_LEVEL_ZH`「升級時每級 +2」；
     - `client/src/world/OpeningDialog.tsx` 的 `ALLOCATE_EXAMPLE_ZH`（配點範例）。
   - 數字從資料來，例如 `attribute_points_per_level`、開局點數、屬性起始值，再照 ×10 量尺換算成玩家看到的數字。
   - 換算方式沿用前端現有的顯示換算（先 grep 屬性的顯示換算），不另外寫一份。API 沒帶到的值就加欄位，新欄位要有預設值，並重產 OpenAPI 和前端型別。
   - 用目前的值組出來的字，要和現在**逐字相同**，並且要有 vitest。
   - 另外測一組改過的值，例如每級 3 點、開局 6 點，字和例子裡的數字都要跟著變，句子也要通順。
   - 配點範例如果有「一樣高就給第 1 招」這類規則用字，照現行規則組字，不要改規則。
2. **工坊工具的 10 項設定搬到使用者能改的設定檔**：
   - 要搬的項目：
     - `api/tuning/schemas.py`：`SMALL_SAMPLE`、`MAX_RATIO_SEEDS`、`SIM_DEFAULT_SEEDS`、`MAP_DEFAULT_SEEDS`、`MAX_SIM_MAPS`、`MAX_SIM_BATTLES`、`RATIO_DEFAULT_SEEDS`、`RATIO_MAX_WORK`；
     - `drafts.py` 的 `DRAFT_NAME_MAX`；
     - `skills.py` 的 `MAX_GROUP`。
   - 這些是開發工具的設定，不是遊戲規則，所以放 `config/`。建議新檔 `config/tuning.toml`，比照 `config/llm.toml`、`server.toml` 的讀法：
     - 用 pydantic 驗證；
     - 程式裡的預設值等於現在的值；
     - 支援使用者自己的 `*.local.toml` 覆寫，照現有的 local 覆寫慣例。
   - 每一項都要附中文說明：這個數字管什麼、調高或調低會怎樣，寫成 toml 註解，並寫進 `docs/dev/上手-數值工坊.md`。
   - 值一律不變。報告列出每一項：原本在哪裡、現在讀哪個鍵、值是多少。
3. **收尾**：
   - 搬完變成 0 筆的兩條規則，從 `classes.yaml` 刪掉。
   - 沒歸類的要是 0，`--unused` 沒有輸出。
   - 重產 `docs/phases/寫死數值-清單.md`。

## 不做

- 不搬其餘三組，不動暴擊倍率。
- 不改任何數值。玩家看到的字在目前的值下一字不變。
- 不改 `docs/design/`；`config/` 只新增檔案或鍵，不改既有的值。

## 驗收

- **字不變**：第 1 項用目前的值組字，要逐字相同；改值的那組也要有 vitest。
- **設定不變**：工坊的 API 用固定請求比對前後的回應。除了新欄位，其他都要 different=0。
- **截圖**：成長面板和開局配點畫面各一張，存進 `docs/art/shots/hc-8/`。網址加 `?mute=1`。
- **靜態檢查**：下面這些結束碼都要是 0：
  - ruff、format、mypy、lint-imports；
  - `trpg content check`、`classify.py --check`；
  - tsc、vitest、build。
- **全量檢查**：全部 commit 以後，**先問開發 PM「準備跑 check.py」**，收到回覆才跑。另一個 agent 也會跑全量，兩邊不能同時跑。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-8報告.md`。
