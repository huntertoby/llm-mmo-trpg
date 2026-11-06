# Phase 3H-8 報告：工坊選項與說明整修

規格：`Phase3H計畫.md` 8.2 節；證據：`工坊盤點-2026-10-24.md` #7～#11、#13、玩法 PM 第 4 題。

## 逐項做了什麼

1. **第二屬性與專精選單（#7）**。新檔 `skillgen/option_scaling.py`，欄位放在「稀有度」步驟（縮放範圍要看已填的效果與形狀，基本設定步驟時還不知道）。
   - 第二屬性 `secondary_scaling_attr`：只有法術技、稀有度達 `core.dual_scaling_min_rarity`（目前史詩）才列出；選項 ＝ `library.skill_scaling.allowed_attrs(試組技能, library.weapons)` 減掉主屬性。**武器技不列**。已經填了第二屬性但稀有度不夠時仍列出，才能按「不使用」取消。
   - 專精 `mastery`：沒有第二屬性時列出；選項用 schema 試組決定（射程專精要有 `shape.range`、持續專精要有 `apply_status`），不另寫規則；武器技也有專精（照 3H-6 看武器屬性）。
   - 前端：選第二屬性會自動拿掉專精（`draft.ts` `selectChoice`）。稀有度步驟的 `notes_zh` 補一句「第二縮放屬性至少○○；專精與第二屬性只能擇一」（稀有度名稱取自設定）。
2. **耐力與代價說明（#8、#9）**。新檔 `skillgen/option_rules.py`：`resource_cost_text` 由 `core.resources.stamina_regen`、`roguelite.refill_after_battle`、`campfire_after` 產生耗費資源說明（耐力：每回合開始回復 N 點、每場打贏後回滿；法力：戰鬥中不回復、只有營火回滿）；`cost_step_text` 讓「代價」步驟說明依類別寫法力或耐力（還沒選類別時兩者並寫）。
3. **組合規則（#10）**。`composition_info` 把原語的 `position`、`sole_effect`、`others_affect`、`max_per_skill` 放進選項 `info`（`composition` 原始規則、`badges_zh` 標章、`rules_zh` 說明句）；`active_only` 幾乎每個原語都是，不當標章。`composition_block` 依已填的效果與種類算出「現在不能加」的原因（`info.unavailable_zh`）：達每技能上限、唯一效果與其他效果互斥、其他效果還沒寫 `affects: self`、種類不是主動技；已有「其他效果限自己」的效果時，新加效果帶 `info.forced_affects`，前端 `addEffect` 自動寫入。前端效果卡顯示標章（必須第一個／必須最後一個／唯一效果／最多 N 個／其他效果限自己）、規則句（黃）、不可用原因（紅）並停用按鈕。位置規則（第一個／最後一個）不擋選取（使用者可用 ↑↓ 調整），只標示。
4. **狀態選單（#11）**。`ParamContext.keep_status` 排除 `budget_points` 為空的狀態（只影響 `apply_status`）。
5. **玩家／開發者模式（#13）**。預設玩家模式；網址 `?dev=1`（沿用 `isDevMode`）為開發者模式。
   | 項目 | 玩家模式 | `?dev=1` |
   |---|---|---|
   | 「隨機一個」的種子 | 不顯示，每次按由程式抽 | 顯示、可指定 |
   | 「裝上試玩」的種子 | 不顯示（開啟時抽好） | 顯示、可指定 |
   | 匯出 | 後端預設只允許合法技能（`POST /api/workshop/export` 不合法回 422，列出問題）；前端按鈕在不合法時停用並說明 | 送 `allow_illegal: true`，可匯出不合法半成品 |
   | 隨機技能的暫定 concept | 卡片不顯示（`WorkshopCheck.concept_provisional`、`SkillCardView hideConcept`） | 顯示 |
   | 說明文字 | 去除「交給 PM」「種子」等開發用語 | 原文 |
   `concept_provisional` 以卡片 concept 含「暫定」判斷（常數 `PROVISIONAL_MARK`，在 `routes/workshop.py`）；沒有改隨機組合器，避免和 3H-7 衝突。
6. **測試與實機**。新 `tests/skillgen/test_workshop_3h8.py`（9 項）、`tests/api/test_workshop_api.py` 加 2 項、`client/src/workshop/options3h8.test.ts`（4 項）。實機 1600×900：玩家模式（種子全數消失、不合法技能的下載鈕停用、concept 隱藏、第二屬性選了之後專精消失、效果卡標章與不可用原因、專精晶片的說明卡可正常浮出）與 `?dev=1`（種子、匯出、concept 都在）各看一次；測完已還原視窗並只關自己啟動的 8013 伺服器。

## 檢查結果

`ruff check`、`ruff format --check`、`mypy`（657 檔）、`lint-imports`（7 條）通過；`pytest tests/skillgen tests/api tests/test_architecture.py`（1570）、`tests/cli`、vitest 887、`pnpm build` 通過。OpenAPI 與 `schema.d.ts` 已重產（CLI 與前端快照不需更新）。未跑 `scripts/check.py` 全量。

## noqa

無新增。

## 與 3H-7 合併時要注意

- 我改了 `options.py`（`_step` 加 `description` 關鍵字參數、`_primitive_choice` 的 info、`_effects_step`、`_resource_field`、`_cost_step`、`_rarity_step`）、`option_params.py`（`keep_status`）；3H-7 若也改 `options.py` 的縮放欄位，請留意 `_scaling_field`（我沒動它）。
- **目前第二屬性選項不準，等 3H-7**：`allowed_attrs` 現在對沒有標籤的火焰法術回傳身體類（力量／敏捷／體質），所以實機看到智力主屬性的火球，第二屬性選單是力量／敏捷／體質。3H-7 主題改由效果推導後會自動變正確（程式只呼叫 `allowed_attrs`，不用再改）。
- `tests/skillgen/test_workshop_options.py::test_random_skills_fit_the_options` 我暫時過濾掉 `secondary_scaling_attr` 的問題（現在組合器的 `dual_attrs` 會抽到範圍外的第二屬性，選項會回報「不是合法的選項」）；3H-7 讓組合器從允許範圍抽之後，請拿掉這個過濾。
- 主屬性選單（基本設定步驟）沒有限範圍，仍是六選一，由 3H-7 的驗證器 `scaling.range` 擋。

## 待 PM 決定

1. 玩家模式的前端工坊目前仍有「進階：直接編輯 YAML」與即時檢查面板的規則代碼（`budget.weak` 等）；規格沒有要求拿掉，是否在玩家模式隱藏？
2. `?dev=1` 的偵測是讀網址（沿用 `isDevMode`），玩家可自行加參數；若之後要真的區分（例如大世界主城），需要由帳號／設定給。
3. 位置規則（必須第一個／最後一個）只標示不擋選取；若要在加入時自動排到正確位置，需要另做（約 0.1 段）。
4. `concept_provisional` 用「含『暫定』」判斷；若之後把組合器的暫定句改成中性句（盤點 #13 的另一個選項），這個旗標與常數可一併拿掉。
