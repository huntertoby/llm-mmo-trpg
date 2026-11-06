# Phase RT-2 報告：事件插圖補主城背景、荒原祭壇換火盆

實作者，2026-11-04。依據 `docs/art/區域主題移植需求.md` 第 2 節，樣子照 `docs/art/shots/region/region-themes.png` 右欄。只改了 `client/`。

## 做了什麼

1. **第三種背景 `capital`（主城）**：`EventArtBg` 改成 `"cloud" | "ashen" | "capital"`。
   - **地面**：直接用主城實地圖的石板畫法，也就是 `terrainArt.drawTile`，區域 `capital`，金色嵌線照 6Q-1 的 `CAPITAL_INLAY`。沒有另畫一套。
   - **石板提亮**：地面上加一層米白（`CAPITAL_WASH`），讓插圖縮小後看起來是「白石板」。
   - **點綴**：右上角遠處有一角藍頂白牆，用 `capitalArt.paintBuilding` 的 `stone_hall` 縮成 0.55 倍來畫。另有兩盞源晶燈，用 `drawCrystalLamp` 縮成 0.8 倍來畫。左邊那盞放低一點，避開事件小牌。
   - **10 種場景都有主城版**。主城版不畫竹林、松樹、花、草地、黃土路、霧、荒原枯草和石燈籠。祭壇的光改成紫晶光。
2. **荒原的「祭壇・機遇」**：兩座石燈籠換成角魔火盆（新的 `hornBrazier`）。
   - 火盆是黑鐵三腳架加鐵碗，碗緣有小彎角，碗裡三簇火、有橘色火光暈和餘燼。
   - 位置和大小照原本的燈籠：(1.6T, 0.6T)、(4.4T, 0.6T)，佔一格。
   - 雲嶺版的石燈籠保留。
3. **背景怎麼挑**（`eventArtBg`）：
   - `ashen_waste` 用荒原背景；
   - `capital` 用主城背景；
   - 沒有區域時（`null`、`undefined`、空字串、`hub`）退回主城版本；
   - 雲嶺和其他區（含不認得的值）照舊用雲嶺背景。
   - 伺服器原本就送 `region=char.region`，**沒有新增伺服器欄位**。
4. **開發頁** `event-art-gallery.html`：多加主城 10 種事件卡。raw 模式改用 `eventArtBg` 挑背景。

## 檔案清單

- `client/src/render/eventArt.ts`：新增 `capital` 背景、`EVENT_ART_BGS`、`ALTAR_GLOW`；改寫 `eventArtBg`；調整各場景的主城分支和荒原火盆。
- `client/src/render/eventArtCapital.ts`（新檔）：`capitalTile`、`capitalBackdrop`、`CAPITAL_LAMPS`、`CAPITAL_WASH`。
- `client/src/render/eventArtParts.ts`：新增 `hornBrazier`。
- `client/src/render/eventArt.test.ts`：更新原有的背景測試，再加 7 個測試。
- `client/src/dev/eventArtGallery.tsx`：加入主城 10 種。
- `docs/art/rt2_before_cards.png`、`docs/art/rt2_after_cards.png`：前後對照。上排是雲嶺的伏擊、雲嶺的祭壇、荒原的伏擊；下排是荒原的祭壇、主城的伏擊、主城的祭壇。
- `docs/art/rt2_after_all_scenes.png`：改完後的全部插圖，包括主城 10 種。

## 測試

- `eventArt.test.ts` 有 21 個測試（原本 14 個）。新加的測試涵蓋：
  - 主城 10 種都不會畫到竹林、松樹、草地、霧和石燈籠；
  - 雲嶺伏擊仍有竹林（對照組）；
  - 荒原祭壇是兩座火盆，位置同原本的燈籠；雲嶺祭壇是石燈籠；
  - 火盆有火焰和火光；
  - 主城祭壇是紫晶光；
  - 沒有區域時退回主城（EventCard 是 `data-bg="capital"`）；
  - 主城 10 種彼此不同，也和雲嶺、荒原不同；
  - 確定性測試擴大到三種背景。
- client 全部 vitest：2421 個測試中 2420 個通過，1 個失敗。失敗的是 `inkRace.test.ts` 的全組合自測。這個檔和這次的修改無關，單獨重跑 18 個全部通過，推測是全量跑時負載太重造成的偶發失敗。
- `corepack pnpm -C client build`：結束碼 0。

## 待 PM 決定

1. **改到了 `client/src/render/`**：派工寫「不碰 `client/src/render/`」，但事件插圖的程式本來就放在 `render/eventArt*.ts`，這次一定要改。
   - 我只改 `eventArt.ts`、`eventArtParts.ts`，加了 `eventArtCapital.ts`，都是事件插圖專用的檔。
   - 戰鬥渲染、`portrait`、`hitStop` 等其他檔案都沒碰。
   - 另外有讀取、沒有修改：`capitalArt`、`terrainArt`。
2. **石板提亮**：主城實地圖的石板本來偏灰（`PAL.stone`）。插圖多疊了一層 0.28 的米白，才接近樣張的白石板。
   - 這一層只在插圖裡，實地圖不變。
   - 如果要和實地圖完全一致，把 `CAPITAL_WASH` 改成透明就好。
3. **沒有區域時退回主城**：原本是退回雲嶺，這次照派工改成 hub／主城。
   - 現行伺服器都會送區域，所以實機畫面不受影響。
4. **荒原祭壇中間的青石板**：這是原本就有的畫法，跟著雲嶺。需求沒有提，所以沒有改。要不要換成荒原的石台，請美術 PM 決定。
5. **目前主城實際上沒有事件**：主城地圖設定為沒有遇敵和事件，所以主城背景要等 RT-5 的 `awaken` 才會在實機出現。
   - 這次的截圖來自開發頁的事件卡，用的是正式的 EventCard 元件和假資料。
