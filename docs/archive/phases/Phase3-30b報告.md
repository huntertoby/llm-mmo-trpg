# Phase 3-30b 報告｜第 32.2 項 浮動卡共用元件補齊＋單位資訊卡捲動

> 範圍：只動前端（`client/`）。沿用 `floatCard.ts`、`useFloatCard.tsx`（3-30 報告）。

## 1. 做了什麼

1. **單位資訊卡完全比照 32.1 的規則**（PM 補充：「主要是滑鼠滑掉就會消失」）。新增純邏輯 `client/src/ui/hoverCard.ts`（`TileCardController`）與 React 接頭 `useTileCard.ts`，`HoverFloat.tsx` 改寫：
   - 滑過有內容的格子立即顯示（格子沒有按鈕，不加 150ms 延遲，見「待 PM 決定」#1）。
   - 離開原格子後有 250ms 寬限：滑向卡片途中經過其他格子，寬限期內**保持原卡**；滑進卡片（含橋接區）後保持開著；離開卡片再有 250ms 寬限才換成滑鼠所在格子或關閉。
   - 卡片與格子之間 8px 的透明橋接區（外框 padding，位置往格子方向多挪 8px）。
   - 點卡片釘住（金色外框）；Esc、點外面關閉；關閉後滑鼠不換格子就不會自己跳出來。
   - 與技能卡共用「同時只開一張」登記（`floatCard.ts` 匯出 `claim/release`，介面 `Dismissable／Holdable`）；卡片內的部件說明框開著時（`hold`）不換卡。
   - 卡片事件不經 React 樹冒泡到戰場（滑過、右鍵、點擊不會算成底下的格子）。
2. **最大高度與捲動**：卡片改用 portal 放在 `body`、`position: fixed`。原因：舊的卡片放在戰場捲動容器（`.board-scroll`）裡，800×600 時戰場可視區只有約 300px，卡片被裁掉，這才是試玩看到「捲不下去」的主因。現在量測戰場區可見範圍與視窗，最大高度 `cardMaxHeight`（不超出可見範圍與視窗、上下各留 4px、下限 120px），位置夾進可見範圍；超出時卡片內 `overflow-y: auto`、`overscroll-behavior: contain`（滾輪、觸控）。內容展開／收合以 `ResizeObserver` 重新量測。
3. **裝備加成預設摺疊**：`GearTotals`（compact）標題列改為按鈕「▸ 裝備加成（N 條）」，點開展開（`gearFold.ts`）。
4. **反應設定、裝備改用共用浮動卡**：反應規則名稱、單位資訊卡的裝備圖示、英雄面板（裝備測試）的裝備圖示用 `PartTip`（內含 `useFloatCard`）；裝備欄位格 `SlotGrid` 用 `PartTip pin={false}`（只顯示，點擊仍是選取欄位）。原生 `title` 已移除。
5. **工坊選項按鈕下方被擋住的一小塊**：`pin={false}` 的 `PartTip`（包在可點選東西裡）說明框加 `no-bridge`（`pointer-events: none`），不再攔截滑鼠；可釘住的說明框維持原樣。

## 2. 驗收證據

- vitest 新增 `client/src/ui/hoverCard.test.ts` 12 項（全過）：滑過顯示與 250ms 寬限、途中經過其他格子保持原卡、進入卡片後不換、離開卡片後寬限、寬限內滑回原格、無內容不顯示、釘住後不換不關、dismiss（Esc／點外面）與同格不再跳出、`hold`、與技能卡同時只開一張、`cardMaxHeight`、裝備加成摺疊標題。vitest 環境是 node（無 DOM），所以三處（資訊卡、反應、裝備）的「顯示／關閉」以共用控制器的測試涵蓋（反應與裝備直接用已有 15 項測試的 `FloatController`），DOM 行為靠下面的瀏覽器實測。
- 瀏覽器實測（本機另起埠 5183／8011，已關閉；`?dev=1`，用「裝備」頁穿上 6 件裝備後「進靶場」，主角有 7 條裝備加成）：
  - 1600×900：資訊卡出現、裝備加成摺疊、點開展開後可看完整（高度 459px，小於上限 646px，不需捲動）。`3-30b-unit-card-1600x900-folded.jpg`、`…-expanded.jpg`。
  - 800×600：卡片最大高度 324px（戰場可視區內）；展開裝備加成後內容 493px，**滾輪捲到最底**（`scrollTop + clientHeight = scrollHeight`），最底看得到地形列。`3-30b-unit-card-800x600-scrolled-bottom-pinned.jpg`（釘住狀態）。
  - **從角色格子滑到卡片、在卡片內捲到最底（未釘住）**：滑到主角格 → 橋接區 → 卡片內 → 滾輪向下，卡片未關閉、`pinned=false`、捲到最底（scrollTop 35＝scrollHeight 359 − clientHeight 324）。`3-30b-unit-card-800x600-hover-path-scrolled.jpg`。
  - 釘住後捲動不關閉；Esc 關閉（DOM 確認卡片移除）。
  - 卡片內的裝備圖示滑過顯示浮動說明框（`3-30b-gear-tip-in-unit-card.jpg`），說明框開著時資訊卡不關。
- `uv run python scripts/check.py` 全過；`pnpm -C client build` 成功（僅既有的 chunk 大小警告）。
- 截圖一律 `.jpg`（環境無轉檔工具）。

## 3. 待 PM 決定

1. **資訊卡不加 150ms 開啟延遲**：格子沒有按鈕、玩家會頻繁掃過戰場，延遲會讓資訊卡變遲鈍；維持立即顯示，只在「換卡」時有 250ms 寬限（也就是滑到另一個單位要等 250ms 才換卡）。若要連顯示也延遲 150ms，改 `TileCardController.setHover`。
2. 因為寬限，滑到**另一個單位**時卡片換得比以前慢 250ms；若嫌慢可縮短寬限（目前與 32.1 共用 `CLOSE_GRACE_MS`）。
3. 資訊卡改成 portal＋fixed 後，位置夾進戰場區可見範圍；在 800×600 這類小視窗時，卡片可能蓋住滑鼠所在的格子（無法同時顧到「貼齊格子」與「不超出可見範圍」）。
4. 裝備欄位格（`SlotGrid`）與工坊選項的說明框只在滑過時顯示、不攔截滑鼠（`no-bridge`），因此不能滑進去、也不能釘住（它們本身是可點選的按鈕）。
5. 反應設定的說明框、觸控與鍵盤 Tab 仍只有邏輯測試，未實機驗證；反應設定面板未在瀏覽器逐項實測（與裝備說明框共用同一個 `PartTip`）。
6. 瀏覽器實測的「滑過途中經過其他格子」受工具限制（滑鼠是瞬間移動），計時行為以單元測試驗證。
