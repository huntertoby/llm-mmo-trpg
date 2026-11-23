# Phase QF-6 計畫：後端小修合併段（佇列 (u)、(p)、(i)、(r)）

> 來源：開發 PM 交接佇列 (u)、(p)、(i)、(r)。
> - (u)：E4 報告第 8 點。
> - (p)：E5 裁定 6。
> - (r)：slow 測試 `test_one_thousand_seeds_are_all_valid_and_spread_out` 在 seed 238 失敗。
>
> 和 QF-5 平行。QF-5 只改 `client/`，必要時再加後端傳變形生效資訊的那一處，這段不要碰 `client/`。

## 範圍

1. **(u) 被動技 reaction 篩選檢查**：被動技 `reaction` 篩選裡的 id，載入內容時要檢查存在。找不到就報錯，訊息寫出技能 id 和找不到的那個 id。LLM、組合器開放這個篩選要等 E6，這段不做。
2. **(p) AI 估計補閘門降傷**：AI 的便宜估計（`skill_estimate`，位置在 `src/trpg/engine/ai/` 一帶）目前不知道變形閘門的降傷，要補上。
   - 估計要用和結算同一份閘門資料，不另外再算一套。
   - 這一項會改變 AI 的選擇，78 場和 census 可能出現差異。逐條列出差異，說明每一條都來自這一項。
   - **不用調數值、不用量平衡**。有疑慮寫進報告，由 PM 轉玩法。
3. **(i) 去掉重複對照表**：`_OFFHAND_ZH`、`_ELEMENT_ZH` 和資料裡的 `name_zh` 重複。改成讀資料，顯示文字必須完全不變。CLI 快照有任何差異都要列出來，而且應該是 0。
4. **(r) 組合器不再組出零預算光環**：組合器組出了只有預支（`borrow_ap`，預算 0）這一個效果的光環。照最保守的做法：組合器不組出「只有零預算單一效果」的光環，檢查規則不放寬。
   - seed 238 要恢復通過。
   - 其他 seed 的結果有變的話，報告列出變了幾個。

## 不做

- 不改規則，不改數值，不改 `docs/design/`、`config/` 既有的值，不碰 `client/`。

## 驗收

- **結果不變**：
  - (u)、(i) 不能改變任何結果。
  - (p) 的差異要逐條列出，並說明來源。
  - (r) 只影響組合器的輸出，442 招逐招預算要 different=0。如果不是 0，列出來、說明原因。
- **測試**：
  - (u)：找不到 id 時會報錯。
  - (p)：有閘門時，估計的傷害會降。
  - (r)：在 `-m slow` 下跑那一題，要通過。
- **靜態檢查**，結束碼都要是 0：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check`。
- **全量檢查**：全部 commit 之後，用 SendMessage 問開發 PM「QF-6 準備跑 check.py」。**收到「可以跑」才跑** `check.py --all`，再跑 slow 的 parity 和 cli。在那之前不要交件。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseQF-6報告.md`。
