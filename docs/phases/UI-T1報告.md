# UI-T1 報告：試玩回報的介面小修（黑屏、跑步跳字、最上排頭被切、被動・被動）

分支 `worktree-agent-a362e0201b24529c9`（基於 main `35174a95`）。只改 `client/`，沒有動 `src/`。

| commit | 內容 |
|---|---|
| `7a776576` | 第 4 項：技能卡標題不再出現「被動・被動」 |
| `15e8113b` | 第 1 項：戰場地圖黑屏（Pixi 全域資源被釋放）＋繪製器壞掉時自動重建 |
| `d8f59ffd` | 第 2 項：跑步的浮動字樣；浮動字樣不超出地圖左右邊緣 |
| `26b40c9d` | 第 3 項：畫布上方預留單位頭頂空間 |

檢查：`npx vitest run` 121 檔 1180 測試全過；`npm run build`（tsc＋vite build）通過。沒有改 `src/`，所以沒有跑 pytest。

---

## 1. 黑屏（地圖整塊黑，F5 才恢復）

### 根因（已確認）

`BattleRenderer.destroy()` 呼叫 `app.destroy(true, { children: true })`。在 Pixi 8.22，第一個參數是 `true` 時，
`AbstractRenderer.destroy` 會呼叫 **`GlobalResourceRegistry.release()`**，把**整個頁面共用**的批次池（`Batcher.mjs` 的 `batchPool`）、
貼圖池（`TexturePool`）、畫布貼圖快取等全部清掉。批次池的陣列裡留著「已經借給其他繪製器、正在使用中」的批次，
所以只要**另一個繪製器還活著且已經畫過**，它手上的批次就被銷毀了：

1. 下一幀 `DefaultBatcher.break` 讀到被清掉的批次（`Cannot read properties of null (reading 'clear')`），算繪失敗；
2. Pixi 的 ticker 在監聽丟例外時不會排下一幀（`Ticker._tick` 先 `update` 才 `requestAnimationFrame`），
   畫布停在最後一幀，剛改過大小（`renderer.resize`）時就是整塊底色＝黑屏；回合列、紀錄、技能列（DOM）都正常；
3. 壞掉的繪製器之後被銷毀時，會把壞掉的批次**還回全域池**，下一個繪製器借到同樣會壞——所以連戰下一場仍可能黑，
   只有 F5（整個 JS 環境重來）一定恢復。

### 重現步驟

確定可重現（每次都黑）：在戰鬥畫面開著時，讓**另一個** `BattleRenderer` 建立後銷毀（模擬「前一個繪製器比新的晚銷毀」）：

1. `http://127.0.0.1:5180/?dev=1&screen=level_up`（`TRPG_DEV_ROUTES=1` 的後端）→ 配點、確定 → 「開始第 2 場」，地圖正常；
2. 主控台執行
   `const m = await import('/src/render/BattleRenderer.ts'); const d = document.createElement('div'); document.body.appendChild(d); const r = new m.BattleRenderer(); await r.init(d); r.destroy();`
3. 戰場地圖立刻整塊黑，主控台每幀 `TypeError ... reading 'clear'`；
   直接呼叫 `GlobalResourceRegistry.release()` 也是同樣結果。

使用者的情境：使用者目前是用 **Vite 開發伺服器（5173）** 試玩（本機 5173 正在監聽），有 React StrictMode（掛載時效果跑兩次，
第一個繪製器在第二個建立之後才銷毀）與熱更新（PM 在主資料夾合併／拉取時檔案改變 → Fast Refresh 重建繪製器）。
我在 dev 伺服器上試過：從選路進戰鬥、回到一輪再繼續（StrictMode）各 15～25 次、讀檔／重新整理後再進、
連續快速熱更新——**自然流程下只在「WebGL context 遺失再恢復後又熱更新」重現過一次黑屏**（之後同樣步驟沒再重現），
其餘都正常；記錄 `release()` 的時間點，StrictMode 下都發生在新繪製器第一次算繪之前（剛好沒事）。
也就是說：機制確定（任何「舊繪製器的 `destroy(true)` 晚於新繪製器開始算繪」都會黑，且壞掉會傳給下一個繪製器），
但使用者那次是哪一個時序觸發的（StrictMode／熱更新／GPU 壓力下 context 遺失）我無法 100% 指認。
使用者的 GPU 同時跑本機模型，WebGL context 遺失也是可能的觸發點，所以下面的修法兩種都處理。

### 修法（`client/src/render/BattleRenderer.ts`、`client/src/ui/BattleCanvas.tsx`）

1. **銷毀時不釋放全域池**：改成 `app.destroy({ removeView: true }, { children: true })`；全域池改為「最後一個繪製器銷毀後」
   才釋放（模組內計數 `liveRenderers`，`releaseIfLast()`），順便清掉壞掉的批次，不會傳給下一個繪製器。
2. **算繪有防護**：拿掉 Pixi 預設掛在 ticker 上的 `app.render`，改掛 `safeRender`（try/catch）；我們自己的 ticker 監聽
   （小人脈動、特效）也包起來。例外時標記壞掉、主控台印 `[BattleRenderer] 戰場繪製失敗，重建繪製器`，通知 `onBroken`。
3. **WebGL context 遺失**：`webglcontextlost` 後 2 秒內沒恢復就視為壞掉；恢復時重畫目前畫面。
4. **自動重建**：`BattleCanvas` 收到 `onBroken` 後換一個新的繪製器並畫上最新的畫面（等於只對地圖做一次 F5）；
   10 秒內最多 3 次，避免一直壞時無限重建。初始化失敗也走同一條路。
5. 銷毀後計時器還在跑的移動補間／特效，移除 ticker 時改用 `ticker?.remove`，不再在銷毀後丟錯。

### 驗證

- 上面的重現步驟 2：修好後地圖不受影響（截圖確認仍正常）。
- 直接呼叫 `GlobalResourceRegistry.release()` 弄壞目前的繪製器：主控台印一次「戰場繪製失敗，重建繪製器」，
  畫布換成新的（`canvas` 元素不同），地圖在 1 秒內恢復，戰鬥照常進行。
- WebGL `WEBGL_lose_context` 遺失→恢復：地圖恢復正常；之後回到一輪、再進戰鬥也正常。
- 回到一輪 ↔ 繼續戰鬥 25 次、熱更新 `BattleRenderer.ts` 多次：地圖都正常、context 沒有遺失。
- 正式建置（`client/dist` 由 8020 的 `trpg serve` 提供）進戰鬥正常。

---

## 2. 啟用跑步沒有跳字

**原因**：地圖回饋（`client/src/battle/feedback.ts`，3-9a）的事件對照表沒有 `unit_ran`，跑步只寫進戰鬥紀錄。

**修法**：`unit_ran` 在跑的人頭上跳「跑步 移動＋N」（N＝`bonus`，黃色「好字樣」）。玩家、隊友、敵人跑步都會跳。
另外邊緣欄的單位浮動字樣原本會被地圖左右邊緣切掉（第一列的主角跑步時只看到「移動＋3」），
`BattleRenderer.makeEffect` 改為把浮動字樣的水平位置往內推，不超出地圖寬度（所有浮動字樣共用）。

**驗證**：vitest（`uiT1.test.ts`：`unit_ran` → `跑步 移動＋3`）；瀏覽器實測：敵人、隊友、主角（第 0 欄）按「跑步」後都在頭上跳出完整的「跑步 移動＋3」。

---

## 3. 最上面一排的角色頭被切

**原因**：`topReserve`（`client/src/battle/elevation.ts`）只預留「最高格的抬高量」，沒有算單位紙娃娃高出所在格頂邊的部分。
紙娃娃腳底在格子中心下方 0.23 格，尖帽頭頂約在腳底上方 70 虛擬像素 × (48/52 × 0.92) ≈ 59.4 → 超出格頂約 24.4 模型像素；
非人形召喚物畫布頂約超出 26.6。平地地圖預留 0，最上排的頭就被畫布上緣切掉。

**修法**：新增 `UNIT_HEADROOM = 28`（模型像素）。預留改為 max(最高格抬高量, 每一排「該排格子抬高＋28 − 排號×格寬」)，
依地圖格子算（不看單位目前位置，單位移動時畫布大小不跳）。**紙娃娃尺寸沒有改**。畫布高度多約 28 模型像素，
自動縮放會略小一點（10×10 平地地圖約 −6%）。點選換算（`clientToTile`）、資訊卡位置（`cardPlacement`）、場景位移都由同一個 `topReserve` 推出，一起跟著變。

**驗證**：vitest（`elevation.test.ts` 更新預期值；`uiT1.test.ts` 用 `paperdoll.ts` 的實際常數檢查 28 蓋得住紙娃娃與召喚物）；
瀏覽器：雲海吊橋把主角移到第 0 排，頭與帽子完整顯示在上方預留帶內。

---

## 4. 選新技能卡片「被動・被動」重複

**原因**：`SkillCardView` 標題列是「稀有度・種類・骨架・類別」；被動、姿態、修正、反應技的骨架名（`content/skeletons/*.yaml` 的 `name_zh`：
被動、姿態、修正、反應技）與種類字樣相同或以它開頭，所以出現「被動・被動」「姿態・姿態」「修正（改造／修正）・修正」「反應・反應技」。

**修法**：前端 `skeletonLabel()`（`client/src/battle/source.ts`）：骨架名與種類相同或以種類開頭時不顯示。主動技能的骨架（打擊、範圍、控場…）照常顯示。
沒有動 `src/trpg/narrative`（API 的 `skeleton_zh` 不變）。

**驗證**：vitest（`uiT1.test.ts`）。瀏覽器上這次的升級三選一都是主動技能，沒抽到被動卡，所以只用測試驗證。

---

## 使用者需要做什麼

- **用 Vite 開發伺服器（5173）試玩**：合併進 main 後檔案會熱更新；為保險起見**重新整理一次頁面**（F5）即可，不必重開伺服器。
- **用 `trpg serve`（8000）試玩**：要**重新建置前端**（`corepack pnpm -C client build`），再重新整理頁面；伺服器不用重開。
- 後端沒有改動。

## 待 PM 決定

1. **頭頂預留 28 模型像素**會讓地圖自動縮放略小（10×10 平地約 6%），最上方多一條深色帶（在高處地圖原本就有）。若美術 PM 希望換成「上方帶畫成地形延伸」或調整數值，再排小修。紙娃娃尺寸沒有動。
2. **黑屏的自然觸發時序**沒能 100% 指認（見第 1 節）；修法同時處理「全域池被清」「算繪例外」「WebGL context 沒恢復」三種情形並會自動重建。若之後仍出現，請使用者打開主控台看有沒有 `[BattleRenderer] 戰場繪製失敗，重建繪製器`，把那行與上一行錯誤回報。
3. 戰鬥中主控台一直有 React 的 `flushSync was called from inside a lifecycle method` 警告（`usePlayback` 在掛載的效果裡 `flushSync`），本段沒有處理，與黑屏無直接關係，可另排。
4. 排版煙霧檢查在戰鬥畫面報兩筆既有的戰鬥紀錄溢出（`span.log-text` 257>252），與本段無關。
5. 驗證用的 `.claude/launch.json`（worktree 內）沒被預覽工具讀到（它讀主資料夾的設定），所以後端 8020、前端 5180 是我用背景指令起的，已全部停止；前端代理用 `.scratch_ui/vite.verify.config.ts`（未 commit）。`client/vite.config.ts` 沒有改。
