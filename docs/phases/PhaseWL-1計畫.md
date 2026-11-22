# Phase WL-1 計畫：去掉寫死的計數與白名單（a 段：後端與測試）

> 來源：
> - `docs/phases/內容擴充評估.md`「建議施工順序」第 1 項：`SKELETON_IDS` 從資料讀；測試計數從快照推；前端退回圖示。
> - 使用者原話（專案 PM 轉）：「那種以後想加骨架 詞條 等東西 只需要+CONFIG就會調動現有的東西去做之類的」。
> - 專案 PM 排定順序第 3 項「拿掉寫死的數量與白名單」。
>
> 這段只做 a：後端與測試。b 段「前端退回圖示」要美術 PM 先同意，另外排。
>
> 原則：**行為、數值、玩家看到的字都不變**。只是讓「加一種骨架、詞條、狀態」時，不用再去改程式裡的清單和測試裡的數字。

## 範圍

1. **`SKELETON_IDS` 改從資料讀**（`src/trpg/content/skills/constants.py`）：
   - 骨架清單以 content（`skill_rules` 的 `skeletons` 或對應的檔）為唯一來源。用到 `SKELETON_IDS` 的地方都改讀資料，包括 cli、skill_checks、primitives、skill、specs、skill_rules、skillgen 的 options、option_followup。
   - 型別若是 `Literal` 或 enum，改成 `str` 加載入時驗證（不認得的 id 由 content check 擋下，錯誤訊息用中文）。
   - **依特定 id 分支的程式不動**，例如 `random_composer.py`、`validate.py`、`composer_recipes.py`、`flash_major.py`。那是行為，不是白名單。但要確認：新加一種沒有特殊行為的骨架時，這些分支都會走預設，不會報錯。
   - 順序如果有意義（例如工坊、CLI 的排列），照資料檔的順序，結果要和現在逐字相同。
   - 要有測試：用測試內容多加一種骨架（只寫資料），可以載入、驗證、組出技能，不用改程式。
2. **其他同類的寫死清單**：先 grep 找出「content 已經有、程式裡又抄一份 id 清單」的地方，例如詞條種類、狀態、觸發時機的 id 元組。
   - 能直接改讀資料的就改，做法同第 1 項。
   - 牽涉到引擎觀察點、`Literal` 判別欄位的，例如 `REQUIRED_TRIGGERS`、詞條的 `kind`、`Surface`，這段不改。那些屬於 E1～E6，列進報告。
3. **測試裡寫死的內容計數改從快照推**：
   - 對象是數內容數量的斷言，例如骨架 16、詞條 81、狀態 119、觸發時機 17。改成比對一份快照檔，放在 `tests/` 底下，格式由你定。
   - 快照要能用一個指令重產，指令寫進報告和 `docs/dev/` 對應的上手筆記。
   - 加內容的人只要重產快照、看 diff，不用逐個改測試。
   - **幾何、骰子、結算結果的數字不是內容計數，不要動**。例如 `ring` 有 16 格、`crit_range == 17`。
   - 改過的斷言在報告裡列一張表：檔案、原本的數字、現在讀哪裡。
4. **收尾**：
   - `classify.py --check` 要通過，`--unused` 沒有輸出。
   - 有新的數字字面值，照 `classes.yaml` 歸類；搬完變成 0 筆的規則刪掉。

## 不做

- 前端徽章、名稱表、圖示（b 段）。
- 引擎觀察點、`Literal` 判別欄位、`Surface`（E 系列）。
- 不改數值，不改 `docs/design/`、`config/`。

## 驗收

- **結果不變**：
  - 442 招的逐招預算、78 場戰鬥（`compare78.py`）、組合器 census 小樣本，都要 different=0。
  - CLI 快照、parity、前端夾具都不變。
- **新骨架只寫資料**：第 1 項的測試要通過。
- **靜態檢查**：下面這些結束碼都要是 0：
  - ruff、format、mypy、lint-imports；
  - `trpg content check`、`classify.py --check`；
  - tsc、vitest、build。
- **測試**：
  - 開發中經看門狗只跑相關的測試。
  - 全部 commit 之後，照派工的指示跑 `uv run python scripts/check.py` 和 slow 的 parity、cli。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseWL-1報告.md`。

---

# b 段：前端退回圖示（a 段合併後才派）

> 來源：
> - 美術 PM 裁定 `docs/art/WL-1b退回圖示.md`：同意，沿用現行的退回畫法，不畫新圖。
> - 玩法 PM 定用字（2026-11-22）：骨架名稱找不到時顯示「未知骨架」。

## 範圍

1. **骨架名稱改從資料讀**：`skillIcon.ts` 的 `SKELETON_NAME[skeleton] ?? skeleton` 改成讀後端帶來的骨架中文名（`content/skeletons/*.yaml` 的 `name_zh`），前端的表只用來覆寫。
   - API 沒帶名稱就加欄位，欄位要有預設值，並重產 OpenAPI 和前端型別。
   - 資料裡也找不到名稱時，顯示「未知骨架」。玩家畫面不能出現英文 id。
   - 目前 16 種骨架顯示的字要和現在逐字相同。
2. **每條路都走得到退回畫法，不會壞**：
   - 狀態圖示照 `qIcon/status.ts` 的 `paintUnknown`；骨架徽章和其他部件圓片照 `qIcon/parts.ts` 的 Q 版問號。
   - 沒有名稱、空字串、`null` 都要畫得出來，不能丟錯誤，也不能整格空白。
3. **待畫清單快照**：寫一個 vitest，列出目前所有走到退回畫法的 id（狀態、骨架、部件），存成快照。這份清單就是美術的待畫清單。

## 驗收

- 截圖照 `docs/art/WL-1b退回圖示.md` 最後一節的 3 組，在開發頁拍，網址加 `?mute=1`，存到 `docs/art/shots/wl-1b/`。第 1 組要和 QI-3a 的 `3a-05` 長得一樣。
- tsc、vitest、build 的結束碼都要是 0。有動到後端時，再加 ruff、format、mypy、lint-imports、`classify.py --check`。
- 全部 commit 之後，照派工的指示跑全量檢查。報告接在 `docs/phases/PhaseWL-1報告.md` 的 b 節。
