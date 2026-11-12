# 小圖示改 Q 版：第 7 批 HUD（第 1 版，暫停中）

> 畫圖 agent，2026-11-12（Opus 5.5）。

## 暫停時進度（2026-11-12，美術 PM 通知暫停，使用者要先做另一項）

**做完的**：讀完上手筆記、規則 14 條、第 5 批與⑤b 紀錄、`HUD功能列圖示.md`、品質底線；遊戲端 7 個檔的盤點（下面第 1 節，還沒畫圖）。
**還沒做**：畫法檔 `sample/qIconsHud.js`、樣張頁 `sample/q-icons-hud.html`、現行打包 `tools/qHudLive.js`、`qicons_shots.py` 的 `hud` 目標、截圖、自查、`上手-畫法.md` 與 `sample/README.md` 的更新。這次只 commit 了這份紀錄。
**下一步**：
1. 現行那一欄：用 vite lib 模式打包遊戲端元件（`HudBarIcon`、`HudIcon`、`BattleToolIcon`、`SettingsHead`、`RegionCrest`，加 `render/skillIcon.ts` 的 `cardGlyphCanvas`），用 `react-dom/server.browser` 的 `renderToStaticMarkup` 輸出 SVG 字串，產物 `tools/qHudLive.js`。worktree 沒有 `node_modules`：`react`、`react-dom`、`yaml` 用 alias 指到主資料夾 `client/node_modules`，`pixi.js` 設 external。`StatGlyph` 的 4 個 SVG（`STAT_PATHS` 沒匯出）、`HoverFloat` 的 `PinIcon`、`float-card.css` 的 `.float-card.pinned::after` 圖釘照抄進頁面並註明出處。（進入點草稿只在暫存資料夾，接手時重寫。）
2. 畫 Q 版（清單見第 2 節），再做樣張頁、真 1 倍、自查、截圖、紀錄。
3. `qicons_shots.py`：`hud` 改指第 7 批，風格樣張的 HUD 特寫改叫 `style-hud`（照 `status`／`style-status` 的做法）。

**還沒決定的事**（要美術 PM 或開發 PM 定，接手後寫進正式的第 7 節）：
- 圖釘統一：A＝Q 版紅頭／灰鋼（第④批 `card.pin`），B＝Q 版金頭（照浮動卡金色）；兩種都要並排畫，不由畫圖 agent 選。
- 月亮（時間・夜）與夜晚（天氣）現行共用同一條路徑（只差色），要分開還是合併：傾向合併成同一題材（新月）、天氣「夜晚」暗一階，理由待圖做出來再寫。
- 通用小圖有 7 個沒有任何地方用（見 1.2），要不要照畫。
- `hud.css` 的 `.source-pips` 菱形沒有地方用（死 CSS）；狀態卡的源力圓點 `.stat-pip.source` 要不要也換成小晶石。

## 1. 盤點（以遊戲端為準，只讀 `client/src/`）

和樣張第 1 節的「65」不同，遊戲端照實數如下（合計 58 個圖示＋源力圓點 1 個建議新增）。

### 1.1 功能列 8（`world/HudBarIcons.tsx`，48 格 SVG、墨線、底下墊淺色圓底 `HUD_BACKING`）
I 背包、K 技能、G 成長、J 任務、Y 影子、N 留言、R 潛行、M 地圖。尺寸：功能列鈕 46 → 圖示 35；影子鈕 36 → 27；地圖鈕 30 → 23；說明卡標題 24。

### 1.2 通用小圖 25（`world/HudIcons.tsx`，24 格 SVG 平塗）
實際有用到的 18 個：`rank` 18（頭像旁階級鈕）、`gear` 17（設定鈕）、`town` 15（地名條）、`warn` 15（地名條限制）／13（浮動提示）、`scroll` 20（任務追蹤收合鈕 36×0.55）／14（任務卡標題）、`notes` 13（浮動提示）、`sun`／`moon` 15（時間）、`clear`／`rain`／`fog`／`snow`／`wind`／`night` 15（大世界天氣）、18（戰鬥天氣 `BattleStatusBox`）、`coin` 15（金幣）、`token` 15（任務幣）、`ration` 15（補給）、`bulb` 15（靈感點）。
沒有任何地方用到的 7 個：`bag`、`book`、`growth`、`shadow`、`map`、`boots`、`pin`。
和功能列同題材的 7 個：`bag`＝I、`book`＝K、`growth`＝G、`scroll`＝J、`shadow`＝Y、`notes`＝N（現行畫成對話框，功能列是便條紙）、`map`＝M。`boots` 是舊的「趕路」，現在 R 是潛行；`moon` 與 `night` 同一條路徑只差顏色。

### 1.3 戰鬥工具鈕 7（`ui/BattleToolIcons.tsx`，20px，鈕 28）
`reactions` 盾＋閃電、`orders` 旗、`legend` 打開的書、`layout` 齒輪（同題材＝通用小圖 `gear`）、`save` 磁片、`exit` 門＋箭頭（風格樣張已有 Q 版「離開」）、`telegraph` 沙漏（同題材＝第④批 `hourglass`）。

### 1.4 資源小圖 8（`ui/StatusCardParts.tsx` 的 `StatGlyph`，16px）
`ap`、`mana`、`source`、`reaction` 已經是 Q 版（呼叫 `ChipGlyph`＝第④批卡片小圖，QI-2c 已接；源力已是晶石）。
`move`（靴）、`shield`（盾）、`weapon`（斜劍）、`ammo`（子彈）仍是舊 SVG（`STAT_PATHS`）。
源力的其他顯示：狀態卡的 `.stat-pip.source` 淡紫圓點 9px（3 格）、跑團面板與技能卡的「●○」文字；`hud.css` 的 `.source-pips` 菱形沒有使用。
技能卡的 `ChipGlyph` 13 個、`EffectGlyph` 8 個是第④批的範圍，已是 Q 版，不算在這批。

### 1.5 設定標題 3（`ui/SettingsHead.tsx`，16px）
`sound` 喇叭、`motion` 圓球加速度線（減少動態）、`hint` 燈泡（同題材＝通用小圖 `bulb`）。

### 1.6 圖釘（遊戲端實際有 3 種畫法）
- `PinGlyph`（`ui/SkillCardGlyphs.tsx`，13px canvas，第④批 Q 版：已釘紅頭、未釘灰鋼 55%）：技能卡、戰鬥紀錄欄、單位資訊。
- `PinIcon`（`ui/HoverFloat.tsx`，13px SVG、`currentColor`：未釘 `--muted` 50%、已釘 `#ffd04a` 金）：格子／單位浮動卡的標題列右側與底部提示列。
- `.float-card.pinned::after`（`styles/float-card.css`，18px 金圓底＋深色圖釘剪影）：釘住的說明卡右上角。
- 另有通用小圖 `pin`（金色，沒用到）。

### 1.7 區域紋章 6（`ui/CreateIcons.tsx` 的 `RegionCrest`，30／34px，六角金框＋深藍底，圖樣用區域強調色）
晶冠王冠、雲嶺雙峰、樞市齒輪、荒原火焰、霜潮浪紋、其他區菱形。框不動（規則 13），只換圖樣。
同檔的 `KeywordIcon` 12 個（建角畫面 15px）不在這批清單內，題材和⑤b 關鍵字相同，沒有畫。

## 2. 預定的做法（未開始）

- 沿用、不另畫：AP、法力、耐力、源力、反應（第④批卡片）；移動靴、離開、背包（風格樣張 `Q.ART.hud`）；沙漏（第④批）；護盾（第③批）；武器斜劍（第④批 `bladeSword`）；警告三角（第④批卡片「缺點」）；金幣（風格樣張物品）；雪花、旋風（第⑤批元素架勢紋章）。
- 同題材一份、大小兩形（規則 8）：功能列 7 個與通用小圖 7 個；齒輪（設定＝版面）；燈泡（靈感點＝提示）。
- 新畫：技能書、成長苗、任務卷軸、影子、留言便條、潛行兜帽、地圖、階級、城鎮、太陽、月亮、晴、雨、霧、任務幣、補給、燈泡、反應鈕、隊友指令旗、圖例書、存檔、子彈、喇叭、減少動態、金頭圖釘、區域紋章 6、源力小晶石圓點。
