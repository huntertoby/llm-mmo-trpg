# Phase HC-3 計畫：前端寫死的規則改由後端提供

> 來源：`docs/phases/寫死數值-清單.md` HC-3 節；`docs/phases/PhaseHC-2報告.md` 裁定 3。
> 原則：前端不再寫死遊戲規則，改讀 API；畫面顯示要和現在一樣。

## 範圍
1. **閃現與技能欄**（清單 HC-3 a）：
   - 要改的：`run/flash.ts` FALLBACK、`run/flow.ts` SLOT_LIMITS、`ui/SkillCardView` SOURCE_MAX、`gear/affixStatus`、`run/StartPicker`。
   - 改成讀 API。後端已有欄位就直接用；沒有的就在對應 schema 加欄位，值取自 content。
   - FALLBACK 這類保底值，只在 API 沒給時才用，而且要和後端一致。最好能拿掉；拿不掉的話，加測試比對後端的值。
2. **大世界與工坊**（清單 HC-3 b）：
   - 要改的：`bagGrid`、`fieldModel` WALK_MAX、`hud` 鐘點、`tuning/*` 的預設種子數與上限，都要和 `api/tuning/schemas.py` 對齊。
3. **營火夾具換新單位**（HC-2 待決 3）：
   - `client/src/.../run_campfire.json` 的技能卡、裝備詞條，用伺服器現在的輸出重抓。
   - `flashChoice.json` 的主角跟著改。
   - 不能手改數字。用腳本從真的 run 產生，或用現有的匯出腳本。

每處改完，`classes.yaml` 裡對應的前端（ts）規則從 todo 改成 done。只改 ts 那一區的規則。

## 驗收
- 畫面不變：每項挑一個畫面截圖，前後各一張，存在 `docs/art/shots/hc-3/`。測試要靜音。
- 後端有改的話：ruff、format、mypy、lint-imports 都要 0，OpenAPI 重產，相關測試分目錄跑。
- 前端：tsc、vitest 全部、build 都要 0。`classify.py --check` 要 0。
- 每項一個 commit。報告寫在 `docs/phases/PhaseHC-3報告.md`，附前端 config todo 剩幾筆。
