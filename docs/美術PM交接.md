# 美術 PM 交接文件

> 給接手的美術 PM（新對話中的 Claude）。最後更新：2026-10-22。讀完本檔再讀 `CLAUDE.md`、`docs/專案計畫.md`（3.1、待決定 #5）與 `docs/phases/Phase3計畫.md` 第 15 節（3-12～3-14）即可接手。

## 1. 角色

- **美術 PM**：負責畫面風格的提案與樣張——色票、圖層規則、素材來源與授權、技能圖示與特效的視覺語言。對應待決定 #5「世界觀與美術風格」的美術半邊（世界觀屬玩法 PM）。
- 使用者（huntertoby）是 **最終決策者**，不是工程師。一律用繁體中文；回覆精簡、有結論，比較用表格，附截圖。
- 與其他角色的分工：

| 角色 | 交接文件 | 和美術 PM 的關係 |
|---|---|---|
| 開發 PM | `docs/PM交接.md` | 使用者採用美術提案後，由開發 PM 寫成階段規格、派實作者；美術 PM 不改 `docs/phases/`、不改正式程式 |
| 玩法 PM | `docs/玩法PM交接.md` | 世界觀、題材由玩法 PM 和使用者討論；美術風格要配合 |
| 實作者 | — | 照開發 PM 的規格做；美術 PM 可以提供樣張程式當參考 |

## 2. 工作方式

1. **在獨立 worktree 分支做樣張**，不合併進 main，不動開發 PM 正在進行的段落（目前 3-13 原型美術、3-15 地形資訊卡）。
2. 樣張做成 **獨立網頁**（`docs/art/sample/`），不接進遊戲：場景資料一份（`scene.js`），多種畫法共用，確保比較的是「同一個畫面」。
3. **截圖**：用無頭 Chrome 直接拍（不需要啟動伺服器）：

   ```bash
   "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --user-data-dir=<scratchpad>/chrome-prof --allow-file-access-from-files --virtual-time-budget=3000 --force-device-scale-factor=1.5 --window-size=2040,665 --screenshot=docs/art/art-compare.png "file:///<worktree>/docs/art/sample/compare.html"
   ```

   （Edge 無頭模式在使用者電腦上沒有輸出，用 Chrome 並指定 `--user-data-dir`。）
4. 截圖存 `docs/art/`，用 `SendUserFile` 傳給使用者，再附比較表與建議。
5. **素材授權**：只用 CC0 或自製；任何下載前先取得使用者同意（3-13 的 Kenney 已同意）。每個外部素材都要留原始 License 檔與來源紀錄。
6. **規則優先於圖**：LLM 會不斷生成新技能、之後也會有新內容，所以提案要寫成「哪些資料欄位決定外觀」的規則，新內容沒有對照時要有預設，不得出錯（和 3-12 特效、3-13 對照表的原則一致）。

## 3. 結論紀錄

### 3.1 第一次比較：色塊 × Kenney × 程式繪製（2026-10-22）

- 樣張：`docs/art/art-compare.png`、`art-compare-zoom.png`、`skill-icons.png`；比較全文 `docs/art/美術風格比較.md`；程式 `docs/art/sample/`。
- Kenney 版是 3-13 **進行中未合併** 的對照表重畫（圖檔複製在 `docs/art/sample/kenney/`，CC0）。
- 美術 PM 的建議：
  1. **技能圖示用程式生成**（元素 → 底色與紋理、形狀＋射程 → 主圖、骨架 → 徽章、稀有度 → 外框），資源包做不到。
  2. 地形、物件、單位 **建議改用程式繪製**（一致、新內容自動有圖），Kenney 為備案；屬品味問題，由使用者看圖決定。
  3. 兩者都是原型美術；正式風格待世界觀定調後再找畫師或商用素材，沿用同一套圖層規則。
- **3-13 完成後要補一張正式對比**（目前的 Kenney 版是進行中的狀態，使用者看到的版本可能較新）。
- **狀態：等使用者決定。** 採用的話由開發 PM 排段（技能圖示約半段；地形／物件／單位約一段，建議在 3-13 合併後、3-14 高度表現前後一起考慮）。

### 3.2 人物改成紙娃娃小人（2026-10-22）

- 使用者：「畫得很好，人物可以像 Kenney 那種小人嗎？預想衣服可以組裝，到時候會有裝扮不同的部分。」
- 已做：`docs/art/sample/paperdoll.js`（分層小人）、`dolls.html`（樣張頁）、`docs/art/paperdoll.png`；對比圖的程式繪製版單位已換成小人。細節見 `docs/art/美術風格比較.md` 末節。
- 使用者另傳話：不用等 3-13，照美術 PM 自己的想法做；Kenney 版標「非最終版」，3-13 完成後補正式對比。

### 3.3 使用者採用程式繪製版（2026-10-22）

- 使用者原話：「我覺得你的這個做得很好，跟玩法 PM 講，可以用這版你做的美術了。」
- 採用範圍：程式繪製版的地形、表面、物件、紙娃娃小人，以及技能圖示自動生成（樣張 `docs/art/sample/`）。
- 已通知玩法 PM；由開發 PM 排進階段規格（移植成 `client/src/render/` 的正式程式，取代或接在 3-13 的 Kenney 對照之後）。
- 第 3.1 節的「等使用者決定」已結案；3-13 完成後的正式對比可以省略，除非使用者要。

### 3.4 組裝式技能圖示（玩法 #21，2026-10-22）

- 使用者：「技能是組裝的，所以我也希望圖示是組裝的，能了解組裝概念。」玩法 PM 規劃見 `docs/玩法PM交接.md` #21。
- 樣張：`docs/art/sample/assembled.html`（`?all` 看全部 152 個）、截圖 `docs/art/skill-icons-assembled.png`、`skill-icons-all.png`。
- 程式：`parts.js`（部件圖示庫：效果原語、狀態、表面、條件、代價、觸發、修正）、`assembled.js`（`partsOf` 拆解＋圖示＋組裝列）、`skillsData.js`（由 `tools/export_skills.py` 從 `content/` 匯出）。
- 視覺決定：類型用外框形狀（不用角標）；效果列核心大圓、附帶小圓，最多 4 個；被動、反應的主圖換成觸發時機；小圖右下一個大圓放核心效果。
- **狀態：等使用者看圖。** 採用後要補進 `docs/art/移植需求.md`（新增 5.3：部件圖示庫、`partsOf`、SkillCard 還需要的欄位：效果清單含狀態／表面 id、條件 id、代價、followup 的 when 與第二段、modifiers、trigger／reaction 事件）。

## 4. 待辦與想法

- 已寫好給開發 PM 的需求摘要：`docs/art/移植需求.md`（2026-10-22）。
- 樣張尚未涵蓋：煙霧、冰牆、荊棘牆、碎石、薄冰、陷阱、持續區域、圖騰、倒地、狀態圖示。
- 世界觀定調（待決定 #5）後重新檢查色票（例：暗黑奇幻 → 降低彩度；童話 → 提高彩度與圓角）。
