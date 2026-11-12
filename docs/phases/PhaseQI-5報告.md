# Phase QI-5 報告：⑦ HUD Q 版小圖示（搬畫法、接線、開發頁、截圖）

> 實作者（Opus 5.5），2026-11-12。需求：`docs/art/Q版小圖示-HUD移植需求.md`（第 4 節開發 PM 已定，照美術建議；圖釘 A）。起點：本機 main `91a7d14b`（含 `9abb4cd1`）。未 push。後端、`content/` 沒動。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| 搬畫法 | 新檔 `client/src/render/qIcon/hud.ts`：由 `docs/art/sample/qIconsHud.js`（第 2 版）逐行搬，50 個圖示＋`crescent`、`gearArt`、`b10`、`from48`、`cardLike`、`paint`、`canvas`、`glyph`、`def`、`pinCanvas`、`pinBadge`、`tone3`、`crestId`。`legacy48.ts` 的 `ART.hud` 加 `bag`、`exit`（照樣張字面色，木色不換 `M.wood`） | `18845504` |
| 接線 | 新 `render/hudIcon.ts`（快取、名字對照、圖釘、`installPinBadge`）、`ui/HudGlyph.tsx`（`IconCanvas`／`HudGlyph`：畫布＝顯示 × 2、CSS 不縮放）。`HudBarIcon`、`HudIcon`、`BattleToolIcon`、`SettingsHead`、`RegionCrest`、`StatGlyph` 改 canvas、**props 不變**；狀態卡源力圓點換 9px 小晶石 canvas；`HoverFloat` 的 `PinIcon` 與 `.float-card.pinned::after` 換圖釘 A | `a7a37b0e` |
| 開發頁 | `client/dev/hud-gallery.html`＋`src/dev/hudGallery.ts`：`?set=a|weather|moon|pip|pin|hash`、`&res=`、`&zoom=`、`&grp=`、`&label=0` | `c6e87291` |
| 測試 | 新 `render/qIcon/qIconHud.test.ts`（16 項）；改寫既有 6 項（第 3 節） | `e8df07fe`、`a7a37b0e` |
| 截圖 | `docs/art/shots/qi5/` 10 張 | `c9608040` |
| 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md` | 本 commit |

## 2. 逐條對需求

| 需求 | 結果 |
|---|---|
| 1.1 功能列 8 | `HudBarIcon` → `bar_I…bar_M`；淺色圓底（`HUD_BACKING` 半徑 15.5/48、細框）畫在畫布最底層，圖樣 74%（`paint` 的 `grp === "bar"`）。`HUD_BACKING*`、`SNEAK_MOON` 仍由 `HudBarIcons.tsx` 匯出（值改從 `qIcon/hud.ts` 的 `BACKING*` 來，同一份） |
| 1.1 通用小圖 18 | `HudIcon` 名字 → id（`HUD_ICON_ID`）；`scroll`＝`bar_J`、`notes`＝`bar_N`，不畫圓底（`frame: "none"`，需求 3 第 2 點：任務 20／14、留言 13）；月亮 `moon` 與夜晚 `night` 分開 |
| 1.1 戰鬥工具鈕 7 | `BattleToolIcon` → `t_*`（反應設定＝第④批回轉箭頭；版面＝齒輪；離開＝風格樣張；預告＝沙漏） |
| 1.1 資源小圖 4 | `StatGlyph` 的移動、護盾、武器、彈藥 → `r_*`（走卡片小圖路徑 ±10 單位、16 → 圖樣 13.44、不包外框）；AP、法力、源力、反應照舊 `ChipGlyph`（樣張 `r_ap` 等＝同一張 `cardCanvas`） |
| 1.1 設定標題 3 | `SettingsHead` → `s_sound`、`s_motion`、`s_hint`（＝燈泡同一份） |
| 1.1 區域紋章 6 | `RegionCrest` → `crestId(region)`（五區＋其他區菱形）；區域色＝`regionThemeFor(region).accent` 三階（`tone3`）；框（深藍底、金框 1.6、區域色 55% 細環）照現行原樣畫在畫布裡 |
| 1.1 源力圓點 | `StatChipView` 的源力圓點 → `pip_on`／`pip_off` 9px canvas（`class="stat-pip source[ on]"`）；AP、彈藥圓點照舊 |
| 1.1 圖釘 | 圖釘 A：`PinIcon`（標題列：已釘紅頭／未釘灰鋼 55%；底部提示列：未釘）＝`cardGlyphCanvas("pin", 13, …)`，和 `PinGlyph` 同一張畫布；`::after` 金圓底照留、裡面 12px 換紅頭（`installPinBadge` 把 Q 版畫布轉 PNG 掛 `<html>` 的 `--float-pin-glyph`）。`PinGlyph` 沒動 |
| 1.2 不動的 | 框、已是 Q 版的、風架勢狀態卡、`KeywordIcon`、AP／彈藥圓點都沒動 |
| 2 同一份畫法 | 能呼叫的都呼叫（`QP.entry`、`QS.ACT.shield`、`EMBLEM.ice`、`ART.hud.move/bag/exit`、`QP.cardCanvas`）；`r_*` 沒加進 `QP.CARD`（見待決 3） |
| 3 第 1～8 點 | 74%、大小、≤14px 不包外框、共用畫法、天氣（風不呼叫風架勢）、紋章三階、說明卡角落、7 個不畫：測試 T1～T3 鎖住，截圖 1～4、10 |
| 4 第 1 點 | 新畫的在 `qIcon/hud.ts`；`bag`、`exit` 在 `legacy48.ts`；六個元件 props 不變 |
| 4 第 2 點 | 7 個名字（bag、book、growth、shadow、map、boots、pin）從 `HudIconName` 刪掉，沒畫新圖（全專案沒有呼叫處，typecheck 過） |
| 4 第 3 點 | 死碼見第 5 節 |
| 4 第 4 點 | `.stat-pip.source`：`display: block; border: none; border-radius: 0`；寬高 9px（`.stat-pip`）與 `.stat-pips` 的 gap 3px 照現行；刪 `.stat-pip.source.on` |

## 3. 改到的既有測試（舊 → 新）

1. `world/hud.test.ts`「7 顆鈕各畫自己的定稿圖示（48×48 畫布）」：舊＝`btn-bag` 含 `viewBox="0 0 48 48"` → 新＝含 `<canvas class="hud-icon hud-bar-icon" width="70" height="70" style="width:35px;height:35px"`（其他 `data-bar-icon` 斷言不變）。
2. 同檔「背包是梯形袋身＋前蓋＋金扣＋斜提把；潛行是兜帽人影＋虛線足跡」（查 SVG 的 `data-part`）→「QI-5：8 顆對到第⑦批 Q 版圖示；背包＝風格樣張後背包、潛行＝第④批兜帽」（`BAR_ICON_ID`、`src`）。
3. `ui/narrowSkillLayout.test.ts`「小修 5：圖示墊淺色圓底」：舊＝SVG 有 `fill=SNEAK_MOON` 的 `sneak-moon` 圓、在 `<path` 之前 → 新＝輸出 canvas，假畫布上第一筆填色是 `HUD_BACKING`、在第一張圖樣之前（亮度、停用 0.6 斷言不變）。
4. 同檔「追加 2／小修 3：每一顆最下層都是同一個淺色圓底」：舊＝SVG 第一個子元素是 `<circle class="hud-bar-backing" fill=…>` → 新＝8 顆假畫布都先填圓底、圓心 17.5、半徑 15.5/48×35、細框色 `HUD_BACKING_EDGE`。
5. `ui/sharedPopup.test.ts`「每區的標題有自己的圖示」：`<svg[^>]*data-icon="motion"` → `<canvas class="settings-head-icon" width="32" height="32" style="width:16px;height:16px"[^>]*data-icon="motion"`。
6. `ui/entryScreen.test.ts`「五區紋章各有自己的圖樣、配區域色」：舊＝SVG 字串含 accent、5 個圖樣字串不同 → 新＝canvas 帶 `data-crest`、5 區 `crestId` 不同、`hub`→`c_other`、假畫布上細環的 `strokeStyle` 是 `regionThemeFor(區).accent`、元件原始碼傳 `opt={{ accent }}`。

**雜湊／快照**：沒有重產任何快照或 fixture；`render/__snapshots__/`、`qi3bStatusBaseline.json`、`qi2dBaseline.json` 都沒動（`r_*` 沒加進 `QP.CARD`，部件基準不受影響）。

## 4. (a) 和樣張指紋比對；結束碼；浮動卡；截圖

**(a) 指紋**：`uv run python docs/art/sample/tools/qicons_shots.py --hash hud`（包一層換成自己的 `--user-data-dir`）與 `hud-gallery.html?set=hash`（自己的 vite 5315，無頭 Chrome `--disable-gpu --mute-audio`，同一個 FNV 算法與行格式）逐行比：**53 行全部相同**（50 個圖示 × 遊戲裡每個大小 × res 2／1、`pin_a`、`pin_off`、`pinbadge_a`）；樣張另外 2 行 `pin_b`、`pinbadge_b` 是圖釘 B，沒搬、不比。紋章的指紋用樣張的 `REGION_ACCENT`；`qIconHud.test.ts` 鎖住它和遊戲 `regionThemeFor(區).accent` 6 區逐一相同。

**結束碼**（交件前各跑一次）：`corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（309 檔、3992 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告）。相關 vitest（`src/render/qIcon/ src/test/ src/ui/ src/world/ src/render/qi2cWiring.test.ts src/render/qi2cStatusUnchanged.test.ts src/dev/layoutSmoke.test.ts`）102 檔 1416 項過。

**浮動卡（6.5.1）**：自己的 `trpg serve`（8155，存檔在暫存區）、無頭 Chrome（9335），1600×900 與 800×600 各跑一次：
- 說明卡（主角卡源力小圖的 `<Hint>`）：100 ms 還沒開、500 ms 開 → 沿直線滑進卡片仍開著 → 卡內捲動：內容一次放得下（`scrollHeight − clientHeight = 0`）→ 點一下釘住（`.float-card.pinned`，`::after` 的背景是 `url("data:image/png…")`）→ 滑鼠移走仍在 → Esc 關閉。兩尺寸都過。
- 格子資訊卡（敵人格）：滑過開、圖釘是 canvas、未釘時不另外 CSS 變淡（opacity 1，圖本身 55%）→ Shift＋點釘住 → 滑進卡片仍開著 → 沒有可捲的 → Esc 關閉。兩尺寸都過。
- `__layoutSmoke.runCase`：1040×624、800×600 全 PASS；1600×900 第一次 1 項 FAIL（「更多動作」選單滑過時說明卡 0 張，時序），重跑兩次全 PASS。

**截圖**（`docs/art/shots/qi5/`，10 張；dev 頁 PNG 裝置像素比 1、最近鄰；實機 jpg 80；單張 ≤ 199 KB）

| 檔 | 對到第 5 節 | 內容 |
|---|---|---|
| `docs/art/shots/qi5/1-dev-bar-gen-true1x-dpr2-x4.png` | 1、2 | 功能列 8（24／27／35、任務 14／20、留言 13、地圖 23）、通用小圖 16，每格真 1 倍＋res 2，×4 |
| `docs/art/shots/qi5/2-dev-tool-res-set-pip-crest-true1x-dpr2-x4.png` | 3、4、5、6 | 工具鈕 20、資源小圖 8 個 16、設定標題 16、源力圓點 9、紋章 30／34，真 1 倍＋res 2，×4 |
| `docs/art/shots/qi5/3-dev-weather-moon-pip-true1x.png` | 6、7、2（月亮／夜晚） | 天氣六種：大世界 15（有字）、戰鬥 18（只有圖示）、風架勢狀態卡 20 對照、最近鄰；時間欄＋天氣欄並排；源力 3 格亮暗混排 ×6 |
| `docs/art/shots/qi5/4-dev-pin-true1x-dpr2.png` | 8 | 浮動卡標題列（未釘／已釘）、底部提示列、說明卡角落、技能卡 `PinGlyph` 並排，真 1 倍與 res 2 |
| `docs/art/shots/qi5/5-world-1600-funcbar-card-k.jpg` | 1、9 | 實機大世界 1600×900：功能列 8 顆、技能鈕說明卡標題 24、月亮＋夜晚、金幣、任務幣、補給、靈感點、階級、城鎮、齒輪、任務卷軸 |
| `docs/art/shots/qi5/6-world-800-settings-head.jpg` | 4、9 | 實機大世界 800×600：設定面板的聲音、減少動態標題 |
| `docs/art/shots/qi5/7-battle-1600-hud-unitfloat-unpinned.jpg` | 3、4、6、8、9 | 實機戰鬥 1600×900：工具鈕、天氣晴 18、主角卡資源列＋源力晶石、格子資訊卡（未釘灰鋼圖釘、底部提示列、武器小圖、`PinGlyph`） |
| `docs/art/shots/qi5/8-battle-800-hud-unitfloat-pinned.jpg` | 8、9 | 實機戰鬥 800×600：格子資訊卡釘住（紅頭圖釘） |
| `docs/art/shots/qi5/9-battle-1600-pinned-hint-badge-dpr2.jpg` | 6、8 | 實機 1600、DPR 2 特寫：釘住的說明卡角落（金圓底＋紅頭）、主角卡 AP／靴子／反應／源力 1 亮 2 暗 |
| `docs/art/shots/qi5/10-create-1600-origin-crest30-dpr2.jpg` | 5 | 實機建角畫面出身卡紋章 30，DPR 2 |

**實機未看**：存檔、離開工具鈕（單場戰鬥沒有，只有開發頁）；資源小圖護盾、彈藥（示範單位沒有護盾、沒有槍）；天氣雨、霧、雪、風（實機只拍到晴、夜晚）；其他區菱形紋章（建角只有五區）；紋章 34（遊戲預設值，目前呼叫處只用 30）。都在開發頁 1～3 張。

## 5. (b) 死碼的去留、(c) 7 個名字

**刪了（沒有呼叫處）**：`StatusCardParts.tsx` 的 `STAT_PATHS` 與 `INK`；`HoverFloat.tsx` `PinIcon` 的 SVG 路徑；`float-card.css` `::after` 的 SVG data URL、`.unit-float .tile-pin-icon` 的 `color`／`opacity`、整條 `.unit-float.pinned .tile-pin-icon`；`hud.css` 的 `.source-pips`、`.source-pip`、`.source-pip.filled`；`status-card.css` 的 `.stat-pip.source.on`。另外被換掉的元件本體也刪了：`HudBarIcons.tsx` 的墨線 SVG（`Ink`、`Line`、`Dot`、`smoothPath`、`wobble`、`seedOf`、`rng`、`ellPts`、`ICONS`）、`HudIcons.tsx` 的 `PATHS`、`BattleToolIcons.tsx` 的 `PATHS`、`SettingsHead.tsx` 的 `Icon`、`CreateIcons.tsx` 的 `crestGlyph` 與 `NAVY`（全專案沒有其他呼叫處；見待決 1）。

**別處在用而留下**：無。`CREST_REGIONS`（`CreateIcons.tsx`）仍匯出、沒人用，照舊留著。

**(c)**：`bag`、`book`、`growth`、`shadow`、`map`、`boots`、`pin` 從 `HudIconName` 刪掉，沒指到其他圖、沒畫新圖。

## 6. 和樣張不同的地方

- 依賴改 import（`core`、`legacy48`、`parts`、`skills`、`status`）；`canvas(id, px, res, opt)`（樣張 `(id, px, zoom, opt)`）。
- 紋章色由呼叫端傳 `opt.accent`；沒傳時用樣張 `REGION_ACCENT`。
- 沒搬：`V1`／`canvasV1`、圖釘 B 與深色剪影（`PIN.b`、`PIN.ink`、`pinArt`）、`live`／`topic` 欄、`GRP_ZH`。`pinCanvas(pinned, px, res)` 直接回傳 `cardCanvas`（樣張複製一份，像素相同）。
- 超過 80 行的函式：沒有。

## 7. 待 PM 決定

1. **被換掉的 SVG 本體一起刪了**（第 5 節）：需求只點名 4 項死碼，其他 SVG 本體不刪就要另外匯出才過得了 `noUnusedLocals`；`docs/art/sample/tools/qHudLive.js`（樣張左欄的「現行」打包）若要重產，現行已是 Q 版。若要保留舊 SVG 當 `LEGACY_*`，可從 `18845504~1` 撿回。
2. **大世界 HUD 整塊 CSS `scale`，畫布會被重新取樣**：`world-hud-inner` 在 1600 寬是 `scale(1.25)`、800 寬 `scale(0.7)`，功能列 35 的畫布在螢幕上是 43.75 / 24.5 px，外框 1px 不會剛好對到裝置像素（以前的 SVG 縮放不糊）。要清楚得把縮放傳進圖示、照實際大小出圖，範圍超出本段。戰鬥 HUD 沒有縮放，但部分圖示左上角落在小數位置（例：天氣 x＝1434.30），和 QI-2c 的 `ChipGlyph` 一樣。
3. **`r_move`／`r_shield`／`r_weapon`／`r_ammo` 沒加進 `QP.CARD`**（需求寫「可以」）：加了會改 `QP.CATS` 的清單，動到 `qi2dBaseline` 的部件基準與第④批樣張指紋；改放 `qIcon/hud.ts`，畫法與路徑相同（指紋相同）。
4. **說明卡角落的紅頭圖釘用 PNG data URL 掛 CSS 變數**（`installPinBadge`，`main.tsx` 啟動時做一次）：`::after` 的位置跟著卡片，可能落在小數像素；開發頁（`hud-gallery`）沒有呼叫它。不想用 CSS 變數的話要改成真的 DOM 元素。
5. **`.stat-pip.source` 改 `display: block`**：canvas 在 inline-flex 裡本來就是 flex 項目，加 `display: block` 只為了不受行內基線影響；大小、間距不變（截圖 9 可看）。
6. **`__layoutSmoke` 1600 第一次有 1 項時序 FAIL**（「更多動作」選單滑過時說明卡 0 張），重跑兩次全 PASS，和本段無關，列記錄。
7. **新加一個 `.venv`**：worktree 第一次 `uv run` 建立（在 `.gitignore` 內），不影響。

## 8. 給使用者的檢查重點（重開伺服器後）

- 大世界功能列 8 顆、時間天氣列（夜晚＝月亮＋另一個星星月亮）、金幣、任務幣、補給、靈感點、階級、城鎮、齒輪、任務卷軸、浮動提示的警告／留言都是 Q 版。
- 戰鬥右上工具鈕（反應設定變成綠色回轉箭頭）、天氣格、主角卡的靴子、源力圓點變小晶石、格子資訊卡的圖釘變紅頭／灰鋼、釘住的說明卡右上角金圓底裡變紅頭圖釘。
- 設定面板三個標題、建角出身卡的紋章。
- 需求第 6 節「交使用者時已講明」9 點本段照做，沒改。
