# Phase HC-6b 計畫：API 與前端說明文字裡的寫死數字改從資料帶入

> 來源：
> - `docs/phases/寫死數值-清單.md` HC-6 節 c 項。
> - 使用者「全部集中化先做完」。
> - HC-6a 開發 PM 裁定 1、6（`docs/phases/PhaseHC-6a報告.md` 最後一節）。
>
> 原則同 HC-6a：**玩家看到的字不變**。只把字裡寫死的規則數字，改成從 API 帶來的資料或常數組字。目前的值不變，組出來的字就要和現在逐字相同。

## 範圍

1. **`src/trpg/api/` 的 text 34 筆**：
   - 用 `classify.py --dump text` 列出確切清單。
   - 做法同 HC-6a：照規則包、schema 常數組字，不另外寫一份常數。
2. **前端的 text 98 筆**（`client/src/` 的 battle、gear、run、screens、tuning、ui、world）：
   - 數字要從後端來的，就讓 API 回應帶那個值，前端組字。
     - API 有改要重產 OpenAPI 和前端型別。
     - 新欄位一律有預設值，舊存檔、舊回應照樣能讀。
   - 前端本來就有的資料（例如技能卡已有的欄位），直接用那個欄位組字。
3. **一併處理的介面文字項目**：
   - 工坊前端 15 筆；
   - `base_points` 的說明用字；
   - 沒有技能的形狀；
   - 祝禱的骰子字；
   - 地面提示；
   - 組裝列的說明；
   - 詞彙表的骰子欄；
   - 路徑預覽的重擲狀態。
   - 每項開工先確認在 `--dump text` 裡，或是清單文件裡有記。找不到的寫進報告，不要自己擴大範圍。
4. **`wish_cards` 的連動字**（HC-6a 裁定 1）：
   - 範圍：許願畫面、許願三選一畫面、工坊相鄰兩格的說明。
   - 寫死的「三選一」「挑 3 張」改成讀 `wish_cards`。
   - 目前值 3 的時候，字要和現在逐字相同。
   - 張數改成 2、4、5 時，字也要通順。中文數字的寫法要定一個規則，寫進報告。
5. **收尾**：
   - 搬完變成 0 筆的規則刪掉。
   - HC-6a 裁定 6：基準時就是 0 筆的 9 條 config／scale 規則一起刪。
   - 刪完以後，沒歸類的要是 0。
   - 真的是語法用字的，照 `classes.yaml` 改判 const，並寫理由。

## 不做

- 不改任何數值，也不改玩家看到的字（第 4 項只在張數改了以後才會不同）。
- HC-6a 留下的 26 筆後端 text、誓約冷卻「1 天內」，都留給 HC-7。
- 不改 `docs/design/`、`config/`。

## 驗收

- **字不變**：
  - CLI 快照、parity、前端夾具都不能變。有變就是錯了；只有 API 新欄位造成的夾具變動除外，要逐鍵列出。
  - 前端：
    - 每個改到的元件都要有 vitest。用目前的值組出來的字，要和改前的字串逐字相同。
    - `wish_cards` 另外測 2 和 5。
  - API：改到的 view，用固定的請求比對前後回應。除了新加的欄位，其他都要 different=0。
- **一致性**：434→438 招的逐招預算、78 場戰鬥都要 different=0（這段不該動到）。
- **靜態檢查**：下面這些結束碼都要是 0：
  - ruff、format、mypy、lint-imports；
  - `trpg content check`；
  - `classify.py --check`；
  - tsc、vitest、build。
- **截圖**：改到的畫面各截 1 張存進報告附的資料夾，至少要有許願、工坊、戰鬥提示。
  - 開瀏覽器要靜音。
  - 不用 8000、8001 埠。
- **測試**：
  - 開發中經看門狗只跑相關的測試。
  - **交件前全部 commit 之後，先問開發 PM「準備跑 check.py」**：
    - 收到回覆後，照指示先 `git merge --no-edit main`，再跑 `uv run python scripts/check.py` 和 `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli`。
    - 有失敗就修好、commit、重跑，直到全部通過。
    - 沒收到回覆不要交件。
- **commit 與報告**：
  - 每項一個 commit。
  - 報告寫在 `docs/phases/PhaseHC-6b報告.md`，附上：
    - 前、後端各剩幾筆 text；
    - 改判 const 的清單；
    - API 新增的欄位；
    - 截圖路徑。
