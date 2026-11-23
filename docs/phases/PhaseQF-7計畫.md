# Phase QF-7 計畫：小修合併段（佇列 (ak)、(al)）

> 來源：
> - (ak)：E6-c2 報告待決 4。旁白只有一段、又有「多講一點」按鈕時，補上旁白後卡片仍會長高。美術的要求見 `docs/art/WM-1驗收.md`。
> - (al)：E6-c2 報告待決 5。後端 `world_crafting_view` 的鐵匠裝備說明也用「；」接文字，會出現「。；」。美術的要求見 `docs/art/E6-b2驗收.md`。
>
> 玩法 PM 同時在自己的分支寫第 10 步的內容（只動 `content/`）。這段不要碰 `content/`。

## 範圍

1. **(ak) 旁白卡片不長高**：旁白只有一段、又有「多講一點」按鈕時，占位和補上後的卡片高度、按鈕位置要一樣。做法照 E6-c2 的說書人框，挑最小的改法。
2. **(al) 去掉「。；」**：後端 `world_crafting_view` 用「；」接之前，先拿掉每段結尾的「。」。前端在 E6-c2 已經改了，這次只改後端這一處。

## 不做

- 不改規則、不改數值，不改 `docs/design/`、`config/`、`content/`。

## 驗收

- **測試**：
  - (ak) 驗結構：占位和補上後是同一個框，框以外的內容逐字相同。
  - (al) 不再出現「。；」。
- **截圖**：存到 `docs/art/shots/qf-7/`。
  - (ak)：800 寬的占位、補上各一張，兩張按鈕位置要一樣，用無頭 Chrome 量高度並附上數字。
- **結果不變**：三項比對都要 different=0；CLI 快照有差異的話逐條列出。
- **靜態檢查**，結束碼都要是 0：ruff、format、mypy、lint-imports、tsc、vitest、build。
- **全量檢查**：全部 commit 之後跑 `check.py --all`（預先授權），再跑 slow 的 parity 和 cli。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseQF-7報告.md`。
