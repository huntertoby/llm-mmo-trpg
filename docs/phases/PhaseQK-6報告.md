# Phase QK-6 報告：#137 外觀選項 Q 版補畫、獸耳四種、建角／主城預覽改 Q 版即時畫

> 實作者：worktree `dev/qk6`（從 main `9c4f6db9` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md` 第 0、7 節；`docs/art/外觀變化方案.md` 第 1、2 節、`shots/misc/appearance-vary.png`；`Phase6R-2報告.md`、`PhaseQK-6a報告.md`、`PhaseQK-1報告.md`、`PhaseQK-2報告.md`。不改規則、資料、存檔、重播；沒動 `qDoll.ts`、`qGear*`、召喚物／形態／異形／頭目檔。

## 0. 盤點結果

QK-1 移植 `qDoll.js` 時，臉型 4、眼睛 4、睫毛、新髮型 4（齊肩、馬尾、雙馬尾、刺蝟）＋光頭、髮髻、鬍子樣式（短鬍渣、八字、山羊、大鬍子）的畫法已經在 `qHead.ts`，獸耳四種耳尾在 `qRace.ts`，體型 `frame`（slim ×(0.92, 1.02)、broad ×(1.08, 0.98)）已經在 `qDoll.ts`。**缺的是接線**：`appearance.withLookChoice` 還停在 6R-2 的「現有部件」對照（新髮型畫成長髮／短髮、只認大鬍子、臉型眼睛睫毛體型獸耳都丟掉），所以 `DollLook.custom` 一直沒傳到 Q 版。這段把接線補上，並逐項並排確認畫出來和樣張一致。

## 1. 完成表

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 補畫（接線） | 新檔 `client/src/render/qLook.ts`：`applyLookChoice`（資料值 → 樣張欄位：`face`、`eye_style`→`eyeStyle`、`lashes`、`hair` 8 種、`beard`：stubble→`short`、mustache、goatee、full＝`beard: true`＋`full`、none＝拿掉種族鬍子；`frame`；`beast_ears`→`beastEars`；預設值〔圓臉、方眼〕不寫欄位＝和沒選逐像素相同）、`qFrameScale`。`appearance.ts`：`Look` 加 `face`／`eyeStyle`／`lashes`／`beardStyle`／`frame`／`beastEars`、`hair` 加 4 個值；`withLookChoice` 改呼叫 `applyLookChoice`（仍在種族預設之後）。頭像（`qPortrait.ts`）本來就用 `drawQ` 的同一份頭部畫法，配件層也已套 build＋frame，所以自動跟著變，不用改 | `4fa7efeb` |
| 1 | 體型 3 | `qDoll.ts` 已照 `qDoll.js` 畫 `frame`，**不需要改 `qDoll.ts`**，沒有待接的一行 | — |
| 2 | 獸耳四種 | 狐、貓、狼、兔耳＋對應尾巴（`qRace` 的 `beastEar`／`TAIL[beastEars]`），四方向 3 倍特寫逐張 | `8748c505`、`c52715cf`（搬資料夾） |
| 3 | 預覽 Q 版即時畫 | 新檔 `client/src/render/qLookPreview.ts`：`drawQLookPreview` 直接畫在 `<canvas>`（依 CSS 大小 × devicePixelRatio 取樣，單位框 −56～4 撐滿高度，影子同戰場），不再轉成 `<img>` 的 data URL。`LookPreview`（建角頁與主城「成長」→「外觀與種族」共用）改用畫布＋`ResizeObserver`（窄版縮小時重畫，不糊）。CSS：畫布高度 `--look-h`、寬度 `aspect-ratio 52/60`；6R-2b 的窄版規則（建角外觀步驟固定上方 90px、主城 sticky 100px）同時套到畫布；窄版非外觀步驟的 140px 預覽框畫布 100px。選單下方「要等 Q 版才畫得出來」的說明拿掉 | `867915a4` |
| 4 | 一般敵人 | QK-6a 挑的 `doll.custom` 走同一條 `resolveDoll` → `withLookChoice` → Q 版，戰場畫得出刺蝟、馬尾、齊肩、鬍渣、八字、山羊鬍；截圖證明（第 3 節） | `101a32a7` |
| — | dev 畫廊 | `doll-gallery.html?skin=q&set=look`（35 列外觀選項 × 四方向，版面同 parts；外觀走遊戲的 `withLookChoice`、衣服顏色照樣張；`window.__qkLookRows` 給比對腳本）；`&set=enemy`（盜賊 4 範本 × 8 種髮型鬍子組合，正面＋朝東，遊戲畫法與材質色） | `8748c505`、`101a32a7` |

## 2. 並排圖（`docs/art/shots/qk6/compare/`，35 張＋總表 4 張）

- **左**：`docs/art/sample/qDoll.js`（`appearance-vary.png` 用的同一份畫法，在 `appearance-vary.html` 頁面裡呼叫 `QDoll.stamp`）四方向；**右**：遊戲（`doll-gallery.html?skin=q&set=look`）。3 倍、版面同 `closeup/parts`。`appearance-vary.png` 本身只有正面小圖，所以左邊改用同一份程式出四方向（見待決 1）。
- 列：臉型 `f1～f4`、眼睛 `e1～e4`、睫毛 `l1`（方眼）`l2`（大眼）、髮型 `h1～h8`（短、長、齊肩、馬尾、雙馬尾、刺蝟、髮髻、光頭）、矮人 `d1` 光頭 `d2` 髮髻、鬍子 `b1～b5`（無、鬍渣、八字、山羊、大鬍子）、體型 `r1～r3`、獸耳 `x1～x4`（狐、貓、狼、兔）、頭飾規則 `g1` 馬尾＋頭盔、`g2` 雙馬尾＋頭盔、`g3` 馬尾＋兜帽。
- 像素差（任一通道差 > 24 的像素占比，扣標題列）：全部 **0.27～0.48%**，只有外框反鋸齒；獸耳四列 0.42～0.48% 最高（耳朵細尖、邊多）。總表 `_sheet_01～04.jpg`。
- 獸耳四種 3 倍特寫（遊戲畫的，四方向逐張）：`docs/art/shots/qk6/beast/qk6_beast_{fox,cat,wolf,rabbit}_3x.jpg`。

## 3. 實機截圖（`docs/art/shots/qk6/`，7 張，jpg 80，最大 182 KB）

- `qk6_create_look_1600.jpg`：建角外觀步驟（獸耳族：尖下巴、大眼、雙馬尾、兔耳、纖細、睫毛），左側 Q 版即時預覽。
- `qk6_create_look_800.jpg`：800×600（人類：方臉、笑眼、刺蝟、八字鬍、壯碩），預覽固定上方（畫布 78×90）、選單在下面捲，沒有水平捲動。
- `qk6_town_look_1600.jpg`：主城「成長（G）」→「外觀與種族」→改外觀（蛋臉、圓點、齊肩、山羊鬍、睫毛）。
- `qk6_town_look_800.jpg`：800×600（矮人：光頭、鬍渣、尖下巴），選單捲到髮色，預覽與方向鈕 `sticky` 在上方。
- `qk6_battle_enemies_1600.jpg`＋`qk6_battle_enemies_1600_zoom.jpg`（3 倍）：開發模式單場「沼澤」種子 392，盜賊 `unit_0004` 刺蝟＋八字鬍、盜賊盾兵 `unit_0005` 刺蝟＋山羊鬍（戴頭盔，刺蝟被蓋住）、盜賊弓手 `unit_0006` 短髮＋鬍渣（兜帽）；頭目 `unit_0007` 沒有 `custom`、外觀固定。
- `qk6_enemy_looks_gallery.jpg`：同一套遊戲畫法，盜賊、弓手、盾兵、新手 × 8 組（刺蝟／馬尾／齊肩／長／短 × 無／鬍渣／八字／山羊／大鬍子＋膚色、髮色），正面＋朝東，證明 QK-6a 範圍內每個值都畫得出來。

截圖方式：worktree 內 `TRPG_DEV_ROUTES=1 uv run trpg serve --port 8144`、`vite --port 5186`（畫廊）、`python -m http.server 8166`（樣張），Playwright＋系統 Chrome（headless、`--mute-audio`、`?mute=1`）；三個伺服器都用自己的 PID 結束。

## 4. 測試與驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 254 檔、3171 項全過（`qSelfTest.test.ts`、`inkWeaponFrame.test.ts` 照跑、沒改） |
| 快照重產 | **沒有**（沒有快照變動） |
| 新測試 | `client/src/render/qLook.test.ts`（6 項：沒選＝原樣、各欄位對照、新髮型照值、鬍子五種含 none 拿掉種族鬍子、疊在種族之後傳到 Q 版小人、體型縮放同 `qDoll.js`） |
| 改寫的測試 | `client/src/run/lookOptions.test.ts`「選的外觀疊在種族外觀之後」：6R-2 斷言馬尾畫成 `long`（現有部件），改成照值 `ponytail` |
| `tsc --noEmit`、`vite build` | 過（只有原本的 chunk 大小提醒） |
| 排版煙霧（`__layoutSmoke.runCase`，`?dev=1&anim=0.1&mute=1`） | 1600×900、1040×624、800×600 都 13 PASS、0 FAIL |
| 6.5.1 實測（建角頁種族卡，外觀步驟所在頁） | 1600×900、800×600：滑過開卡 → 直線滑進卡片仍開 → 滾輪（卡片內容不需捲動）→ 點一下釘住、滑鼠離開仍在 → Esc 關閉；卡片在畫面內。本段沒有新增浮動卡（預覽是固定區塊） |
| Python | 沒改伺服器、資料，沒跑 pytest |

## 5. 待 PM 決定

1. **並排左邊用 `qDoll.js` 出四方向**：`appearance-vary.png` 第 1 節只有正面、約 1.9 倍的小圖，無法逐格四方向對；左邊改用產生那張圖的同一份 `qDoll.js`（`appearance-vary.html` 裡 `QDoll.stamp`）出 3 倍四方向。要另附 png 裁切對照請告知。
2. **動到 `client/src/render/appearance.ts`**（不在原檔案清單）：外觀選項接到紙娃娃的唯一入口是 `withLookChoice` 與 `Look` 型別，只改這兩處（`Look` 加 6 個選填欄位、`hair` 加 4 個值、`withLookChoice` 改呼叫 `qLook.applyLookChoice`）。QK-3／QK-4 合併時若同檔有衝突，保留雙方即可。
3. **C 畫風**（`setDollSkin("c")`，只剩測試在用）遇到新髮型值時畫成短髮（`inkDoll` 只認 long），沒再做對照。
4. **刺蝟＋頭巾**：照 `qHead` 的規則，頭巾不算整個蓋住，刺蝟的尖從頭巾上緣露出（`qk6_enemy_looks_gallery.jpg` 第一列）；頭盔、兜帽會蓋住。請美術 PM 看是否要讓頭巾也蓋住刺蝟。
5. **選單選項沒有小圖**：樣張第 4 節的選項按鈕是頭像縮圖；規格只寫預覽改 Q 版，選項仍是文字按鈕。要加縮圖（每個選項一個 52px Q 版頭）請排段。
6. **預覽框單位範圍 −56～4**：拿杖、長槍時武器尖會被裁掉一點（高帽、兔耳在範圍內）。要整把武器入鏡就把上緣調到約 −64（人會小約 12%）。
7. QK-6a 待決照舊（「粗獷／柔和」軟性抽、臉型眼睛體型不挑、種族範圍不換引擎種族），本段沒動。

---

## QK-6b：美術修好的樣張移植＋QK-8 待決 4

> worktree `dev/qk6b`（從 main `532a3903` 開）。依據：美術 commit `e8a5a73d`（`docs/art/shots/misc/qk6-fix-compare.png`）、`PhaseQK-8報告.md` 第 7 節待決 4。沒動 `qDoll.ts`、`qPortrait.ts`、content。

### 1. 完成表

| 項目 | 做法 | commit |
|---|---|---|
| 兔尾 | `qRace.ts` `TAIL.rabbit`：固定米白 `#efe6d6`（`tailColor` 有寫時照寫）＋深 20% 描邊 0.7，不再混髮色 | `c1efe177` |
| 狼耳 | `qRace.ts` `beastEar`：底寬 3.7（x 4～7.7）、耳尖 −47；外緣深 38% 的四邊形寬邊；內側灰 `#a9a9b2`。狐、貓、兔耳不動 | `c1efe177` |
| 鬍渣 | `qHead.ts` `beard`：短鬍渣先 `headShape` 裁切，只畫在臉內 | `c1efe177` |
| 方臉、心形臉背面 | `qHead.ts` `hair` 背面：圓形髮罩後再補一層同臉型、以頭心 (0,−29) 放大 1.04 的頭髮 | `c1efe177` |
| 八字鬍（QK-8 待決 4） | `world/npcLook.ts` `portraitDollLook`：地圖紙娃娃（`mapExtras`）遇到頭像配件 `mustache` 且沒有大鬍子時，`doll_look.custom = { beard: "mustache" }`，走 QK-6 的 `withLookChoice` → `beardStyle: mustache`。content 已有 `extras: [mustache]`，不需補欄位；頭像本身照舊由 `qPortraitPrep` 畫 | `4438e24e` |

`qDoll.ts` 不需要接線（頭、頭髮、鬍子都在 `qHead.ts`）。

### 2. 並排圖（`docs/art/shots/qk6/compare_v2/`，9 張，左新樣張、右遊戲）

| 檔案 | 左 | 差（通道差 > 24，扣標題列） |
|---|---|---|
| `parts_s04_03.jpg`、`parts_s04_04.jpg` | `closeup/parts`（`e8a5a73d` 新版） | 0.01%、0.02% |
| `look_f3_square.jpg`、`look_f4_heart.jpg`（背面髮罩）、`look_b2_stubble.jpg`（含側面）、`look_x3_wolf.jpg`、`look_x4_rabbit.jpg` | `qDoll.js` 同 QK-6 版面四方向 | 0.31～0.48%（外框反鋸齒） |
| `npc_shopkeeper_liu.jpg`、`npc_tavern.jpg` | `q-npcs.html?z=2` | 0.21% |

### 3. 驗收

| 項目 | 結果 |
|---|---|
| 特寫 key 95＋parts 62（改前→改後，同一環境） | 只有 `parts/s04_03`、`s04_04` 變；key 95 張 0 差 |
| 鎖格 13 格（vs `closeup/locked/`，改前／改後） | 13 格全部與改前相同（0.12～0.91%，同 QK-1b 以來的基準） |
| vitest 全量 | 258 檔、3200 項全過（`qSelfTest` 照過）；**沒有快照重產** |
| 新測試 | `client/src/world/npcMustache.test.ts`（3 項：柳掌櫃 → `beardStyle mustache`；酒館老闆已有大鬍子照舊；頭像不加） |
| `tsc --noEmit`、`vite build` | 過 |
| content／pytest | 沒改 content，沒跑 |

出圖：worktree 內 `vite --port 8148`（`doll-gallery.html?skin=q&set=key|parts|look&dump=1`、`qk8-gallery.html` 的 `__qk8.row`），樣張用 `file://` 開 `tools/closeups.html`、`q-npcs.html`；Playwright＋系統 Chrome headless；vite 用自己的 PID 結束。

### 4. 待 PM 決定

1. **酒館老闆不另畫八字鬍**：content 是 `beard: true`＋`extras: [mustache]`；樣張 `qNpc.prep`／`qPortraitPrep` 規則是「已有大鬍子時八字鬍不畫」，照樣張只畫大鬍子（大鬍子本身已蓋住嘴上那塊，畫了也看不出）。地圖上與頭像、樣張一致。若要大鬍子上再疊一條深色八字鬍，需美術 PM 出樣張。
2. 美術追加的 3 個小改（兔尾位置、方臉正面頭頂兩角、大鬍子側面）：做完前沒收到轉達，**沒做**。
