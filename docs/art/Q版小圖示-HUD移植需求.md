# Q 版小圖示第⑦批（HUD）：移植需求（給開發 PM）

美術 PM（第八任），2026-11-12。Q 版小圖示的第五份移植需求，對應「⑦ HUD」。格式照 `Q版小圖示-關鍵字移植需求.md`。

- **定案依據**：
  - 使用者 2026-11-11 同意把墨線小圖示改 Q 版（原話「好」）。
  - 使用者 2026-11-12 看過第 2 版，沒有意見：「要改數值的都給我改就好 其他都按照建議」（專案 PM 轉達）。
  - 圖釘選 **A**（開發 PM 定）。
- **樣張版本**：第 2 版 `9a2bd94f`、`cebc4e6a`；複審通過 `3fa4c9de`（`Q版小圖示-第7批HUD-審查.md`「第 2 版複審」）。**以這版之後的 `docs/art/sample/` 為準**。畫法 `qIconsHud.js`、頁 `q-icons-hud.html`、現行打包 `tools/qHudLive.js`（只給樣張左欄對照，不搬）。
- **紀錄**：`docs/art/Q版小圖示-第7批HUD.md`。第 1 節盤點、第 2 節清單、第 3 節大小、第 9 節給開發的重點；本文整理後**取代**第 9 節與第 11 節，和紀錄有出入時以本文為準。
- **沿用 QI-1 的決定**（`PhaseQI-1計畫.md` 0.0 節）：畫布＝顯示尺寸 × `ICON_RES`（2），圖樣貼整數裝置像素（`blit`），開發頁可切 1 倍給驗收用。

## 1. 範圍

### 1.1 要換掉的（清單見紀錄第 2 節，50 個圖示＋圖釘＋源力圓點）

| 類 | 遊戲端位置 | 數量 |
|---|---|---|
| 功能列 | `world/HudBarIcons.tsx` | 8 |
| 通用小圖（只換有用到的） | `world/HudIcons.tsx` | 18（月亮、夜晚分成兩個） |
| 戰鬥工具鈕 | `ui/BattleToolIcons.tsx` | 7 |
| 資源小圖（舊 SVG 那 4 個） | `ui/StatusCardParts.tsx` 的 `STAT_PATHS`：移動、護盾、武器、彈藥 | 4 |
| 設定標題 | `ui/SettingsHead.tsx` | 3 |
| 區域紋章（只換圖樣） | `ui/CreateIcons.tsx` 的 `RegionCrest` | 6 |
| 源力圓點（新增） | `styles/status-card.css` 的 `.stat-pip.source` → 9px canvas，亮／暗兩款 | 2 |
| 圖釘 | `ui/HoverFloat.tsx` 的 `PinIcon`；`styles/float-card.css` 的 `.float-card.pinned::after` 圓底裡的圖釘 | 2 處 |

### 1.2 不動的
- 框（規則 13）：功能列淺色圓底 `HUD_BACKING`、紋章六角金框＋深藍底＋區域色細環、說明卡角落的金圓底＋深藍外圈。
- 已是 Q 版的：資源小圖 AP、法力、源力、反應（QI-2c）；技能卡的 `ChipGlyph`、`EffectGlyph`；`PinGlyph`（技能卡、戰鬥紀錄、單位資訊，第④批紅頭／灰鋼）。
- 第⑤批風架勢的螺旋紋章：天氣「風」只換 HUD 那一份，狀態卡的風架勢不動。
- 建角畫面的 `KeywordIcon`（題材同⑤b，不在這批）。
- AP、彈藥的圓點（`.stat-pip` 其他款）。

### 1.3 行為改變（要講明）
1. **圖釘 A**：全遊戲統一第④批紅頭（已釘）／灰鋼 55%（未釘）。浮動卡的「已釘」從金色變紅色；說明卡角落的金圓底內改放紅頭圖釘（樣張 `pinBadge("a")`）。`PinGlyph` 不動，只改 `PinIcon` 與 `::after` 的圖。
2. **月亮與夜晚分開**：時間欄 `moon`＝大新月；天氣 `night`＝小新月＋兩顆星。
3. **源力圓點換小晶石**：亮＝第④批晶石撐滿 9px、暗＝同形紫框深底。`hud.css` 的 `.source-pips` 菱形是死 CSS，一起刪。
4. 潛行（R）改紫兜帽黃眼、反應設定改綠色回轉箭頭、影子（Y）換題材、天氣「風」「霧」換形、金幣大幣上的星換刻痕：都是使用者已看過的（第 6 節）。

## 2. 來源與依賴

**移植方式**：照前幾段，逐行搬樣張，只做型別調整，檔頭寫「和樣張不同」。同一個題材只有一份畫法，**能呼叫已移植的 `client/src/render/qIcon/` 就呼叫，不要另畫一份**。比對用 `uv run python docs/art/sample/tools/qicons_shots.py --hash hud`（55 行：50 個圖示＋圖釘 3＋說明卡角落 2；只做 A，B 那幾行不用對）。

### 2.1 沿用已移植的（直接呼叫）

| 圖示 | 呼叫 |
|---|---|
| 潛行 `bar_R` | `parts.ts` `STATUS.concealed`（兜帽） |
| 警告 `warn` | `parts.ts` `CARD.drawback` |
| 雪 `snow` | `status.ts` `EMBLEM.ice` 的雪花（不帶臂章，放大 1.32） |
| 反應設定 `t_reactions`、資源「反應」 | `parts.ts` `CARD.reaction` |
| 環境預告 `t_telegraph` | `parts.ts` `CARD.delayed`（沙漏） |
| AP、法力、源力 | `parts.ts` `CARD.ap`／`mana`／`source`（現行已接） |
| 移動 `r_move` | `legacy48.ts` `ART.hud.move` 經 `from48` |
| 護盾 `r_shield` | `skills.ts` `ACT.shield`（`["#6ab8f0", "#cfe8ff"]`） |
| 武器 `r_weapon` | `parts.ts` `SKELETON.strike` |
| 源力圓點亮 `pip_on` | `parts.ts` `crystal` |
| 圖釘（A、未釘） | `parts.ts` `CARD.pin`（`cardCanvas("pin", px, 1, { pinned })`） |

資源小圖 4 個走 `cardGlyphCanvas` 同一條路徑（±10 單位、≤14px 不包外框），可以直接加進 `CARD`。

### 2.2 風格樣張裡、還沒移植的（這批要搬）
- `qIcons.js` 的 `ART.hud.bag`（背包 `bar_I`）、`ART.hud.exit`（離開 `t_exit`）。建議放進 `legacy48.ts`，和 `ART.hud.move` 同處，由開發定。

### 2.3 這批新畫的（從 `qIconsHud.js` 搬）
- 功能列 6：技能、成長、任務、影子（`shadowArt`）、留言、地圖。任務、留言和通用小圖 `scroll`、`notes` 同一份畫法（大小兩形，規則 8）。
- 通用小圖：階級、齒輪（`gearArt`）、城鎮、太陽、月亮、晴、雨、霧（`fogArt`）、夜晚、風（`windArt`）、金幣（`coinArt`，是風格樣張 `item.gold` 的改版，**用這一份，不要呼叫物品「金幣」**）、任務幣、補給、燈泡。
- 戰鬥工具鈕：隊友指令、圖例、存檔。版面 `t_layout`＝`gearArt`。
- 資源小圖：彈藥 `r_ammo`。
- 設定標題：聲音、減少動態；提示 `s_hint`＝燈泡。
- 源力圓點暗 `pip_off`。
- 紋章 5 個圖樣＋樞市＝`gearArt` 染區域色。
- 共用零件 `crescent`、`b10`、`from48` 等，照樣張搬。

建議新檔 `qIcon/hud.ts`，由開發定（第 4 節第 1 點）。

## 3. 一定要做對的重點

1. **功能列圖樣佔 74%**：淺色圓底照留（半徑 15.5/48），圖樣畫在 74% 的方框裡、可以畫到圓底外面，不是縮進圓底。8 顆一起照 74%。
2. **大小**（紀錄第 3 節）：功能列鈕 46 → 圖示 35、影子鈕 36 → 27、地圖鈕 30 → 23、說明卡標題 24；任務卷軸 20／14、留言 13 是通用小圖的大小、不畫圓底。通用小圖 15、階級 18、齒輪 17、警告 13／15、戰鬥天氣 18。工具鈕 20、資源小圖 16、設定標題 16、源力圓點 9、紋章 34／30（圖樣 60% 置中）、圖釘 13、說明卡角落 18 圓底內 12。
3. **≤14px 不包外框**（警告 13、任務 14、留言 13、圖釘 13、源力圓點 9）；`o.small`＝≤24、`o.tiny`＝≤14。
4. **同一個畫法共用**：齒輪三處（設定、版面、樞市紋章）、燈泡兩處（靈感點、提示）、回轉箭頭兩處（資源「反應」、反應設定）。
5. **天氣**：戰鬥天氣 `BattleStatusBox` 18px **只有圖示、沒有字**，六種（晴、雨、霧、雪、風、夜晚）要彼此分得開。風、霧照第 2 版的 `windArt`、`fogArt`（細節見紀錄第 9 節），**風不呼叫風架勢**。
6. **紋章顏色**：區域 `accent` 三階（本色、混白 40%、混黑 28%）；新區域沒有專屬圖樣時用菱形寶石。
7. **說明卡角落**：金圓底（`--ui-gold-hi`）＋深藍 1.5px 外圈照現行，裡面 12px 換紅頭圖釘（`pinBadge("a")`）。
8. **沒用到的 7 個通用小圖不畫**（`bag`、`book`、`growth`、`shadow`、`map`、`boots`、`pin`）。要留名字的話，指到同題材的圖（樣張 `?part=unused` 有示範）。

## 4. 要開發 PM 決定的事

| # | 項目 | 美術建議 |
|---|---|---|
| 1 | 檔放哪、怎麼切 | 新畫的放 `qIcon/hud.ts`；`ART.hud.bag`、`exit` 放 `legacy48.ts`。SVG 元件（`HudBarIcon`、`HudIcon`、`BattleToolIcon`、`SettingsHead`、`RegionCrest`、`StatGlyph`）改成 canvas 時保留原本的 props。由開發定 |
| 2 | `HudIcon` 沒用到的 7 個名字 | 刪掉，或指到同題材的圖；不要畫新圖 |
| 3 | 換完後的死碼：`STAT_PATHS`、`PinIcon` 的 SVG 路徑、`::after` 的 SVG data URL、`.source-pips` | 沒有呼叫處就刪，有別處在用就列進報告 |
| 4 | 源力圓點換 canvas 後 `.stat-pip.source` 的 CSS | 由開發定；位置、間距照現行 |

**需要玩法 PM 決定的：沒有。** 後端不用動。

## 5. 驗收（美術 PM 會看的截圖）

每項都要有截圖；實機到不了的，用開發頁畫出來並寫「實機未看」。網址一律加 `?mute=1`，無頭 Chrome 加 `--mute-audio`。開發頁照 QI-1 加 `?px=`、`&res=1|2`、`&zoom=`。**最小尺寸交兩種：真 1 倍＋DPR 2**，都用最近鄰放大，裝置像素比 1 拍。只有真 1 倍與最近鄰特寫可以用 PNG（單張 ≤300 KB），其他用 jpg 80；**每段 ≤10 張**。存 `docs/art/shots/<段名>/`。

| # | 要看的 | 尺寸 | 對照（`docs/art/` 下） |
|---|---|---|---|
| 1 | 功能列 8 顆實機（淺色圓底上，圖樣 74%） | 35、27、23 實機，jpg；另附 24 真 1 倍 | `closeup/qicons/hud/a-bar-1.png`、`a-bar-2.png`；`shots/qicons/true1x/hud-t1-01.png` |
| 2 | 通用小圖 18 個（含月亮、夜晚並排） | 15、13、17、18 真 1 倍＋DPR 2 | `closeup/qicons/hud/a-gen-1～3.png`、`moon.png`；`true1x/hud-t1-01～02.png` |
| 3 | 資源列 8 個（4 個已是 Q 版的一起排） | 16 真 1 倍 | `closeup/qicons/hud/a-res.png`；`true1x/hud-t1-03.png` |
| 4 | 戰鬥工具鈕 7 個、設定標題 3 個 | 20、16 真 1 倍 | `closeup/qicons/hud/a-tool.png`、`a-set.png`；`true1x/hud-t1-03.png` |
| 5 | 區域紋章 6 個 | 34、30 真 1 倍 | `closeup/qicons/hud/a-crest-1.png`、`a-crest-2.png`；`true1x/hud-t1-04.png` |
| 6 | 源力晶石亮、暗（3 格裡亮暗混排） | 9 真 1 倍 | `closeup/qicons/hud/a-pip.png` |
| 7 | 天氣六種：大世界 15（旁邊有字）與戰鬥 18（只有圖示）各一排，加狀態卡風架勢對照 | 15、18 真 1 倍 | `closeup/qicons/hud/v2-weather.png` |
| 8 | 圖釘三處：浮動卡標題列（已釘／未釘）、浮動卡底部提示列、釘住的說明卡角落；技能卡 `PinGlyph` 並排確認同一個 | 13、18 真 1 倍 | `closeup/qicons/hud/pin.png`（A 欄）；`true1x/hud-pin-01.png` |
| 9 | 1600×900 與 800×600 實機情境各一張（大世界 HUD、戰鬥 HUD 各至少一張） | 實機，jpg | `shots/qicons/hud-scene.jpg`、`hud-scene@2x.jpg` |

報告另外寫明：(a) 和樣張指紋比對的結果（相同幾行，不同的列原因）；(b) 第 4 節第 3 點死碼的去留；(c) `HudIcon` 7 個沒用到的名字怎麼處理。

## 6. 交使用者時已講明的（記錄）
1. 潛行（R）從灰兜帽青眼改成第④批的紫兜帽黃眼（和「隱蔽」「潛行偷襲」同一個）。
2. 反應設定鈕從「盾＋閃電」改成綠色回轉箭頭（原構圖撞「帶電護盾」）。
3. 功能列的淺色圓底大多被圖蓋住（圖樣 74%）。
4. 天氣「夜晚」和時間「夜」分成兩個圖。
5. 源力圓點換成小晶石是新增的。
6. 影子（Y）是一個米白人形＋腳下斜躺的紫色長影子。
7. 天氣「風」改兩道風線，和風架勢的螺旋分開；天氣「雪」繼續和冰架勢共用雪花；天氣「霧」拿掉雲、只剩三道霧帶。
8. 金幣大幣上的星換成刻痕（星只留給任務幣）。
9. 圖釘統一紅頭：浮動卡「已釘」從金變紅。
