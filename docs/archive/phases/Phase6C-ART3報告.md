# Phase 6C-ART3 完成報告：事件卡墨線圖示

實作者，2026-11-04。分支 `phase6c-art3`（worktree `.claude/worktrees/g6cart3`，從 main `1d9013a6` 開出，含 6N-10 與 6C-ART2）。

規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-ART3 列（含順手項）、`docs/archive/art/Phase6剩餘美術移植需求.md` 第 4 節、樣張 `docs/art/sample/story-icons.html`、`attr-icons.html`、`docs/archive/art/6B-ART1與6C-ART2與6N-1檢查.md` 待決點 2。

## 1. 做了什麼

| 項目 | 檔案 | 內容 |
|---|---|---|
| 墨線圖示畫法 | 新檔 `client/src/render/storyIconArt.ts` | 照樣張逐筆移植：選項 8 種、其他 4 種（線索、模型關閉、說書人、說明）＋事件線、六屬性、d20。用 `inkStyle.ts` 的 `ink`、`stroke`、`ellPts`，在 48×48 的框裡畫；外圈是深底 `#2a241e` 加圖示色圓環（線寬 `max(1.2, s×0.06)`，裁在圓內）。依大小畫成離屏圖、轉成圖片網址快取（和 `portrait.ts` 同做法）；沒有 DOM 時回傳 `null` |
| 元件 | `client/src/world/StoryIcons.tsx` | `SolutionGlyph`、`AttrIcon`、`D20`、`MiscGlyph` 介面不變，裡面改成 `<img>`（離屏圖）；沒有 DOM 時留同大小的框，照樣帶 `data-icon`／`data-attr`／`data-ring`（d20 帶 `data-color`、`data-value`）。舊的 SVG 簡圖刪掉 |
| d20 規則 | `storyIconArt.ts` | 29px 以上才寫點數，28px 以下不寫字、小圖的點數不進快取鍵；DC 照舊由呼叫端寫在旁邊（事件卡、結果卡本來就這樣） |
| 擲骰動畫 | `client/src/world/StoryParts.tsx` | 兩顆骰子改成 64px 的墨線 d20；翻滾時不寫字，停下才寫點數。用到的那顆照結果色，**自然 20 金 `#ffe08a`、自然 1 灰 `#c8c0b8`**（`usedDieColor`）。翻滾的 CSS 動畫、`diceFrame`、計時器都沒動 |
| 大小 | `client/src/world/EventCard.tsx` | 選項按鈕上的圖示 24px（情境判定標題列的選項圖示也是 24）；其他維持原大小（提示 18、說明 12～14、線索 16、DC 旁的 d20 20～24） |
| 小牌圖示顏色（順手） | `client/src/render/eventArtParts.ts`、`eventArt.ts` | `ICON` 多一個選填參數 `ink`：只有黑色的 `bang`（驚嘆號）、`ask`（問號）會用它。事件插圖的小牌傳 `BADGE_ICON_INK = "#f2e6c8"`，所以「古碑」「村民求助」的圖示變淺色；頭上泡泡沒傳，照舊是黑色；彩色圖示（劍、金幣、火、門戶、便條、警告）不理這個參數，維持原色 |
| 開發頁 | `client/src/dev/storyGallery.tsx` | 新增 `?mode=icons`：圖示總表（64／24／18 三種大小，對照樣張） |

沒有改規則，沒有新增伺服器欄位，也沒有新增相依。只動了 `client/` 和 `docs/`，沒有碰 6N-4 的檔案（受擊、閃避、格擋、倒下、技能播放）。

## 2. 測試

- 新增 `client/src/render/storyIconArt.test.ts`（13 項），內容如下。
  - **每種圖示都在**：8 種選項、其他 5 種、六屬性都有畫法，外圈色照樣張；每個圖示在 18、24px 都有深底、圓環、裁切、縮到 48 格，而且有填色和描線；同一個圖示畫兩次完全一樣。
  - **d20**：64px 寫點數；16～28px 不寫字、沒有外圈；小圖的點數不進快取鍵；自然 20 金、自然 1 灰，其他照結果色；元件在小尺寸時 `data-value=""`。
  - **擲骰動畫**：翻滾中兩顆都不寫字、不塗結果色，大小是 64px；停下後寫點數、塗結果色；自然 20 和自然 1 分別塗金、灰。
  - **元件介面不變**：沒有 DOM 時每種圖示都帶圖示鍵與外圈色；有 DOM 時輸出 `<img>`，同一個圖示同一大小只畫一次。
  - **顏色規則**：古碑、村民求助的小牌圖示用 `#f2e6c8`，不再出現黑色；泡泡裡的問號、驚嘆號仍是黑色；彩色的金幣即使傳了淺色也照原色畫。
- 改了 `client/src/world/story6c7.test.ts` 的一行：原本檢查 SVG 的 `fill="結果色"`，改成檢查 `data-color="結果色"`。
- **說明卡仍在**：`story6c7.test.ts` 和 `eventArt.test.ts` 原有的事件卡、結果卡測試全部通過（`world-dc`、`world-methods`、`world-result-formula`、`world-clues` 等 Hint 包住的元素照舊都在）。
- 執行結果：
  - `vitest run src/world src/dev src/render/storyIconArt.test.ts src/render/eventArt.test.ts src/render/portrait.test.ts`：35 檔 400 項全過；
  - `tsc --noEmit` 通過；
  - `vite build` 通過。
  - 沒有跑全量。

## 3. 截圖（`docs/art/`）

截圖方式：自己開的 vite（埠 5329），用無頭 Edge 開 `story-gallery.html`／`event-art-gallery.html` 截圖。內建瀏覽器分頁已滿，沒有關別人的分頁。

| 檔案 | 內容 |
|---|---|
| `6cart3_event.jpg` | 事件卡：古碑小牌的淺色問號、選項按鈕 24px 墨線圖示、情境判定列（d20＋DC 13、屬性、說明、線索） |
| `6cart3_roll.jpg` | 情境判定擲骰停下：64px 兩顆 d20 寫點數，用到的那顆是成功綠、沒用到的變淡 |
| `6cart3_rolling.jpg` | 擲骰翻滾中（`t=300`）：不寫字 |
| `6cart3_icons.jpg` | 圖示總表：選項 8、其他 5、六屬性、d20（一般／大成功金／大失敗灰；DC 旁的小 d20） |
| `6cart3_badges.jpg` | 事件插圖總表：古碑「?」、村民求助「!」小牌是淺色，泡泡裡仍是黑色，其他彩色小牌不變 |

## 4. 檢查清單（需求文件第 4 節）

- [x] 8 種選項、d20、4 種其他圖示和樣張一致（畫法逐筆照 `story-icons.html`，同一套部件名稱，所以抖動種子也一樣；見 `6cart3_icons.jpg`）。
- [x] 18px 時仍分得出來（`6cart3_icons.jpg` 第三欄：雙劍、泡泡、兜帽、放大鏡、拳頭、四葉草、門、錢袋都看得出來）。
- [x] d20 小尺寸不寫字，DC 寫在旁邊。
- [x] 大成功金、大失敗灰。
- [x] 順手項：小牌上的黑色圖示改用淺色 `#f2e6c8`，其他彩色圖示不動（`6cart3_badges.jpg`）。
- [x] 元件介面（`SolutionGlyph`、`AttrIcon`、`D20`、`MiscGlyph`）不變。
- [x] 擲骰動畫：兩顆骰子用這個 d20，翻滾時不寫字、停下才寫點數，大小 64px。

## 5. 待 PM 決定（都照最保守的做法先做了）

1. **「大成功」「大失敗」的判斷**：情境判定的規則沒有大成功、大失敗（結果只有成功、勉強、失敗）。我只改外觀：用到的那顆骰子點數是 20 就塗金、是 1 就塗灰，其他照結果色。規則和伺服器都沒動。
2. **事件線（`thread`）圖示**：樣張沒有這個圖示，事件卡上又有用到，所以照同一套畫法補了一個：金色抖動線，兩端各一個淺色圓點，外圈也是金色。
3. **畫法**：派工訊息寫「程式繪製 SVG」，需求文件寫「離屏圖、轉成圖片網址快取（和 `portrait.ts` 同做法）」。我照需求文件用 Canvas 離屏繪製，同樣是程式繪製，沒有外部素材。
4. **64px d20 的點數**：點數寫在中央三角面上，三角形的邊線會從字後面穿過，和樣張一樣。如果要更清楚，可以給字加一圈淺色描邊。
5. **工作環境**：派工時的 worktree（`worktree-agent-ae05375601d77d80e`）連同它的分支在途中被移除了，所以我自己從 main 開了 `phase6c-art3`（`.claude/worktrees/g6cart3`）。`client/node_modules` 是指向主 checkout 的 junction，沒有另外安裝相依；`uv run` 在這個 worktree 建了 `.venv`。這兩個都在 gitignore 裡，沒有 commit。
