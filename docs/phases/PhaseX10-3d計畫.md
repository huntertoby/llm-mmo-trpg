# Phase X10-3d 計畫：×10 顯示的剩餘地方

> 來源：`docs/phases/PhaseX10-3b報告.md` 待決 4、5、6、7、10 與開發 PM 裁定；骰子顯示的定案寫在 `docs/phases/PhaseX10-3b計畫.md`。
> 小段。接在 X10-3c 補件合併之後。

## 範圍
1. 下面四處的骰子寫法，照 X10-3b 的規則改成只寫範圍（連接號用「–」），長說明多一行「擲 XdY，每點 ×10」：
   - 狀態說明
   - 地形說明
   - 主角面板的普攻
   - 閃現變化列表
   - 另外，`world_economy_schemas.py` docstring 裡的「回 2d6 HP」照新單位改。
2. 走路預覽 `client/src/battle/pathPreview.ts` 的範圍改用「–」。
3. `flashChoice.json` 的匯出腳本：
   - 先查它在 main 上報錯（`FlashStepError keyword_exploit`）的原因並修好；
   - 腳本裡的屬性值換成新單位；
   - 重產一次，報告列出 diff 的摘要。
4. 回復藥的範圍：
   - 能精確算的話，把體質加成算進範圍；
   - 算不準的話，長說明加一句「另加體質加成」。
   - 照最保守、不會說錯的那種做。

5. 美術驗收（`docs/art/X10-3b驗收.md`）：工坊的建議範圍維持全形「～」，不改；工坊不是玩家畫面。如果有 4 位數的範圍出現，補一張 800 寬真 1 倍的截圖。

## 驗收
- 截圖每項一張（1600 寬 jpg 80；800 寬真 1 倍 PNG 至少一張），存在 `docs/art/shots/x10-3d/`。測試要靜音。
- 快照先預測，再逐鍵重產。
- 後端：ruff、format、mypy、lint-imports 都是 0。交件前所有目錄的非 slow 測試各跑一輪，再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 前端：tsc、vitest 全部、build 都是 0。
- 每項一個 commit。報告寫在 `docs/phases/PhaseX10-3d報告.md`。
