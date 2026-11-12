# Phase RT-3b 報告：等待動畫驗收修正，以及 6F-7 驗收的追加項

實作者，2026-11-05。分支 `worktree-agent-afe01600f587596e6`，從 main `d9b3b295` 開始（含 RT-3 驗收紀錄 `docs/archive/art/RT-3檢查.md` 與 6F-7）。沒有 push，也沒有合併。

**範圍**：只改 `client/`，只換外觀與顯示。
- 沒碰：world 的預先生成時機與 API（6L-2b）、skillgen 與內容（6F-4d）、人物繪製。
- 沒有新增相依套件、原生 `title=`、`Math.random`。

**依據**
- `docs/archive/art/RT-3檢查.md`：必修 1～6、小修 2 項。
- 專案 PM 轉達美術 PM 對 6F-7 的回覆，追加 2 項。
- `docs/archive/art/6F-7檢查.md`（分支 `claude/art-pm-8f4e6d`）：必修 2 項、小修 5 項。

報告分成三部分：A 是 RT-3 驗收，B 是追加的 2 項，C 是 6F-7 驗收的 7 項。

---

## A. RT-3 驗收（`docs/archive/art/RT-3檢查.md`）

### A1 必修 1：判定等待把事件卡撐高（退步）

**原因**：中上方的欄（`.world-hud-center`）有 `max-height`，而且 `overflow: auto`。事件卡被撐高後，整張卡在欄裡捲，所以卡的下緣被欄切平，「0／500」和「擲骰」被擠到可視區外。

**做法**
- 欄改成直的 flex，事件卡可以縮（`flex: 0 1 auto; min-height: 0; overflow: hidden`）。外框整張留在欄裡，四角飾件都在。
- 卡片內容在 `.ui-popup-body` 裡捲（`overflow-y: auto`）。
- 上下加漸隱，和 hud 面板同一套：
  - 下緣：sticky 32px，後 55% 是實色；
  - 上緣：56px，捲下去後才出現。
- 自動捲動：新增 `ui/scrollReveal.ts`。
  - `WaitScene` 出現時、狀態變成失敗（多了重試鈕）時，把自己捲進可視範圍，上下各讓出 40px，比 32px 的漸隱多一點。
  - 判定時傳 `revealUntil={「擲骰」那一列}`，沙漏和「擲骰」一起捲進來。
  - 不用 `scrollIntoView`，因為它會連外層 `overflow: hidden` 的舞台一起捲。
  - 由內往外，每一層捲動區都處理一次。原因是 NPC 的對話紀錄本身也是捲動區，但它沒有超出，真正要捲的是外面的面板。
- **實測**（自己寫的 `vis` 量測：元素整個落在捲動區裡，而且離下緣至少 30px）：

  | 畫面 | 等待中：沙漏、「擲骰」 | 失敗：沙漏、重試鈕 |
  |---|---|---|
  | capital800 | 都 VISIBLE | 都 VISIBLE |
  | capital1600 | 都 VISIBLE | 都 VISIBLE |
  | cloud1600 | 都 VISIBLE | 都 VISIBLE |
  | ashenfixed1600 | 都 VISIBLE | 都 VISIBLE |

### A2 必修 2：失敗時自動捲到重試鈕

- 和 A1 是同一套機制。
- **800 的 NPC 面板**：
  - 原本 `NpcPanel` 有一個 hook 寫在提早 `return null` 之後，hook 的順序不固定。這次移到前面。
  - 失敗時，面板自動往下捲 38px，「再試一次」完整露出（`rt3_live_capital800_npc_fail`）。
- **800 的判定**：沙漏和重試鈕都在畫面內（`rt3_live_capital800_judge_fail`）。

### A3 必修 3：設定面板上緣的漸隱

- 32px → 56px。上面 60%（約 34px）是實色，下面 40% 才漸到透明。
- `z-index` 2 → 5，勾選框這類原生控制項也蓋得住。
- 加高之後，捲動時漸隱會蓋住 hud 面板 sticky 的關閉鈕，所以關閉鈕的 `z-index` 改成 6。
- 對照 `rt3_fade_800_end`：被切的那一行和勾選框完全淡掉，下一行「不放雷聲……」也有一半在漸隱裡。

### A4 必修 4：「請稍候」彈窗不透明

- `.ui-popup.world-hud-dialog` 的底色改成實色 `--ui-navy`，不透明度從 0.97 變成 1。
- 實測：計算出的底色是 `rgb(30, 34, 54)`，彈窗內看不到事件卡的鬼影（`rt3_live_*_skill_wait_*`）。
- 彈窗左右露出的，是比彈窗寬的事件卡外緣，不是透出來的。

### A5 必修 5：開發頁 NPC 的「完成」狀態

- `WaitScene` 在 `npc`＋`done` 時，不畫畫布、不畫泡泡，直接顯示 `doneText` 的回覆文字。
- 開發頁傳一句範例回覆。正式畫面照舊由對話紀錄接手。
- 截圖：`rt3_done_all`、`rt3b_npc_done_3regions`。

### A6 必修 6：重拍

**NPC 失敗沒拍到的原因**：雲嶺真的有渡婆婆，所以聊天會成功。

**改了注入腳本**（`scratchpad/rt3b/inject.js`）：
- 新增 `chatFail`、`answerFail`：等完延遲後固定回 503。
- 荒原的主題原本會跑回雲嶺：其他世界端點回來的畫面資料（例如 `{ world: {...} }`）沒有換區域。現在所有世界端點都會換 `field.region`。

**重拍結果**

| 原檔名（照原名覆蓋） | 現在拍到的 |
|---|---|
| `rt3_live_cloud1600_npc_fail` | 雲嶺，泡泡變灰、失敗句、「再試一次」 |
| `rt3_live_ashenfixed1600_npc_fail` | 荒原主題（鐵框、橘色）的失敗狀態，`data-region=ashen_waste` |
| `rt3_live_capital800_judge_wait` | 沙漏，「擲骰」在同一畫面 |
| `rt3_live_capital800_judge_fail` | 灰沙漏、重試鈕、「擲骰」都在 |
| `rt3_skill_t150`～`t3000` | 視窗真的設成 1100×560 再拍，沒有裁切。拍到卡框底邊和短句 |

**其他重拍**（同一支腳本，全部照原名覆蓋）
- `rt3_live_{capital1600,capital800,cloud1600,ashenfixed1600}_*`：全部 4 組。
- 開發頁：`rt3_*_3regions`、`rt3_*_t*`、`rt3_reduced_all`、`rt3_done_all`、`rt3_line2_all`、`rt3_long_line_all`。
  - 全部改成把視窗設成截圖尺寸再拍：單區 1100×560、三區 1600×560、整頁 1600 寬。
- `rt3_fade_800_top0／mid／end`、`rt3_float_1600_pinned`、`rt3_float_800_pinned`。

**新增截圖**
- `rt3b_{capital800,capital1600,cloud1600,ashenfixed1600}_event_top／mid／end`：事件卡捲到最上、一半、最下。四角飾件、上下漸隱都在。

### A7 小修：沙漏翻轉超出羊皮紙

- 新增 `hourglassExtent(角度, 縮放)` 和 `hourglassFlipScale(角度)`。翻轉中跟著角度縮小，外接框離羊皮紙邊至少 1px；直立時不縮。
- 截圖：`rt3b_hourglass_flip_t60`、`t100`、`t140`、`t180`。

### A8 小修：封蠟

- 原本是平面六角形加一個圈。改成：
  - 不規則的蠟緣：18 點，用 `fmix32` 算出的固定點列，再用二次曲線接圓；
  - 右下陰影；
  - 壓下去的圓餅：內圈較暗，左上亮、右下暗，做出斜面；
  - 壓印紋：八道星芒，加一圈小點；
  - 左上高光。
- 確定性：每次畫都一樣，不用 `Math.random`。
- 截圖：`rt3b_seal_done_3regions`、`rt3b_seal_wait_3regions`。

---

## B. 追加 2 項（美術 PM 對 6F-7 的回覆）

### B1 800×600 戰鬥的地圖只讓出左欄

- `hudSideInsets` 的 `right` 改成 0。
- 地圖現在放在左欄右邊到畫面右緣之間置中。800 寬時地圖在 340～707，自動縮放 77%。
- 截圖：`rt3b_03_battle_800`，另有 `_1040`、`_1600`。
- **右上戰況框會蓋到地圖右上角**：800 寬時，戰況框 582～792、y 8～105，蓋到地圖右上大約 1～2 格。照指示沒有硬改，列在待決 1。

### B2 工具列所有圖示墊淺色圓底

- `HudBarIcon` 的最下層，每一顆都墊同一個淺色圓底。
  - 顏色和 6F-7 R 鈕的月光同色 `#d4dbef`，細框 `#8a94b8`，半徑 15.5。
  - 圓在 8～40 之內，不會碰到功能列右上的飾件。
- 涵蓋大世界和鐵匠鋪的功能列 I K G J Y N R、地圖 M 鈕，以及左上的影子小鈕。
- 停用時照舊是不透明度 0.6，實測 R 停用時 `opacity` 是 `0.6`。
- 截圖：
  - 大世界：`rt3b_bar_capital_1600`、`rt3b_bar_capital_800`；
  - 鐵匠鋪：`rt3b_bar_smithy_1600`、`rt3b_bar_smithy_1040`、`rt3b_bar_smithy_800`；
  - 每一張都另附功能列放大 `_zoom`，以及左上影子小鈕放大 `_shadow_zoom`。

---

## C. 6F-7 驗收的 7 項（`docs/archive/art/6F-7檢查.md`）

### C1 必修：技能名斷行

**長名字**
- `skillCost.skillNameLines` 由程式決定斷點：
  - 每行都要放得下，每行至少 2 個字；
  - 優先斷在「的、之、與、和、・」或空白後面，其次是兩行平均。
- 結果：「灰燼與霜雪交織的／鎖鏈陷阱」。
- 兩行放不下時，縮到 10px（`tight`）。還放不下，第二行加「…」。
- `SkillName` 元件每行畫一個不換行的區塊，加 `aria-label` 放完整名字。

**代價**
- 「・」改成接在下一段的開頭，換行點在「・」之前，行尾不留「・」。
- 例子：「AP 2・法力 6」換行後是「・冷卻 3 回合」。

截圖：`rt3b_01_skillbar_longname_1600`、`_1040`、`_800`（各附 `_zoom`），以及 `rt3b_03_battle_*`。

### C2 必修：戰鬥紀錄的底條伸進地圖

- 紀錄、每一條紀錄、展開的清單，最寬都是 `var(--hud-left-w)`：800 寬時 230px，其他 252px。
- 文字放不下時加省略號。
- 實測右緣：800 → 238，1040、1600 → 260。地圖從 340（800）、434（1040）起，沒有重疊。
- 截圖：`rt3b_03_battle_800`、`_1040`、`_1600`。

### C3 小修：Y 鈕和左上影子小鈕看不見

- 同 B2。截圖：`rt3b_bar_*_zoom`、`*_shadow_zoom`。

### C4 小修：窄視窗的室內地圖

- 改了 `camera.clampAxis`。條件是：地圖比安全區大，但扣掉下方工具列後放得下。
- 這時整張往上對齊：下緣停在工具列上方，留 32px（`HUG_GAP`；空間不夠就少留）。
- 6F-3 的規則保留：主角一定在安全區裡。貼齊後主角會跑進左上主角卡那一帶時，照舊跟著主角捲。
- 800×600 鐵匠鋪實測：畫布 102～514，工具列從 546 開始。兩個「出」格子完整露出，I、K、G 看得見，工具列也不再整條變淡。
- 截圖：`rt3b_bar_smithy_800`、`_1040`、`_1600`。

### C5 小修：選取中技能鈕的代價對比太低

- 選取時代價改成 `#e4e8f6`，在藍底 `#3d5a99` 上的對比約 6:1；原本的灰字約 2.4:1。
- 截圖：`rt3b_03_battle_*`、`rt3b_01_*`（選取中的「捕獸夾」）。

### C6 小修：說明框把「右鍵」拆成兩行

- 新增 `ui/keepWords.tsx`：右鍵、左鍵、Esc、Shift 這類操作詞包成不換行的小段。其他字照常換行。
  - 沒有用 `word-break: keep-all`，因為那會讓長句整段不換行而超出框。
- 套用在操作說明句（`OpHint`）、`PartTip` 說明卡、技能列的提示句。
- 截圖：`rt3b_03_battle_800`。斷行變成「…Esc」換行「／右鍵取消。」，「右鍵」沒有被拆開。

### C7 小修：`ue1b_09_reaction_1600` 的孤字與框底空白

**孤字**
- 詢問視窗的段落、說明句加 `text-wrap: pretty`。
- 現在第二行是「標示）。」，不再只剩「示）。」。

**框底空白**
- 原因：下緣漸隱是一塊 32px 的 sticky 色塊，內容沒有超出時，它只是空白。
- `PopupFrame` 量捲動區有沒有超出，標上 `data-overflow`。量的時候扣掉漸隱自己的高度，避免來回跳。
  - 每次重繪時量一次；捲動區或它的子元素大小改變時，由 `ResizeObserver` 再量一次。
- 沒有超出時，色塊高度設成 0。框底比原本少了約 16px。
- 截圖：`rt3b_reaction_1600`、`rt3b_reaction_800`。原檔 `ue1b_09_reaction_1600` 沒有覆蓋，是另外拍的新檔。

---

## 驗證

**排版煙霧檢查**
- `/?dev=1&anim=0.1&mute=1`，先 `localStorage.clear()`，再跑 `__layoutSmoke.runCase('RT-3b')`。伺服器帶 `TRPG_DEV_ROUTES=1`。
- 1600×900、1040×624、800×600 三個尺寸都是「全 PASS」，共 33 列。

**6.5.1 浮動卡實測**（功能列「技能」鈕的說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓（707～821） | ✓（436～550） |
| 滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片 106px，沒有可捲的內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 關閉 | ✓ | ✓ |

**交件前的完整檢查**
- client 全部 vitest：**246 個檔、2769 項全過**，結束碼 0。
- `corepack pnpm -C client build`（含 `tsc --noEmit`）：結束碼 0。

**靜音**
- 無頭 Chrome 都加 `--mute-audio`，網址都加 `?mute=1`。
- 拍主城、雲嶺之前，都先跑 `close.js` 關掉開場對話框。

**程序**
- 自己啟動的：API 8359、vite 5359、CDP 9479～9589 的無頭 Chrome。
- 結束時用工作 ID 或 PID 關掉。vite 留下一個子程序佔著 5359，確認是自己啟動的那一個之後才用 PID 結束。
- 5355 被別的程序佔著（沒查是誰的，也沒動它），所以改用 5359／8359。
- 沒碰 8000、8001、8010、8366、5366、`tmp_x`、`saves/`。
- 測試存檔、腳本放在 `scratchpad/rt3b/`、`scratchpad/f7b/`，沒有 commit。`client/vite.rt3b.config.mts` 是暫時設定，也沒有 commit。

## 檔案清單

**新增**
- `client/src/ui/scrollReveal.ts`
- `client/src/ui/keepWords.tsx`
- `client/src/ui/rt3b.test.ts`
- `client/src/ui/rt3b6f7.test.ts`
- 截圖 `docs/art/rt3b_*`
- 本報告

**修改**
- 等待動畫：
  - `ui/WaitScene.tsx`：自動捲動、NPC 完成顯示文字
  - `ui/waitScene.css`
  - `render/waitArt.ts`：沙漏範圍、封蠟
  - `dev/waitGallery.tsx`
- 事件卡、NPC：`world/EventCard.tsx`、`world/NpcPanel.tsx`
- 彈窗：`ui/PopupFrame.tsx`（`data-overflow`）
- 戰鬥：`battle/stageLayout.ts`、`ui/SkillBar.tsx`、`ui/skillCost.ts`
- 說明句：`ui/OpHint.tsx`、`ui/PartTip.tsx`
- 大世界：`world/HudBarIcons.tsx`、`world/camera.ts`
- 樣式：`styles/theme.css`、`styles/world-hud.css`、`styles/battle-hud.css`、`styles/skill-bar.css`、`styles/base.css`
- 測試：`ui/waitScene.test.ts`、`ui/fix6f7.test.ts`、`ui/skillBar6f6.test.ts`、`ui/textless6a3.test.ts`
  - 跟著新的「・」位置、名字分行、操作詞小段，更新期望值。
- 截圖：照原名覆蓋的 `docs/art/rt3_*`，見 A6。

## 測試數

- `rt3b.test.ts`：19 項，涵蓋 RT-3 的 8 項。
  - 捲動距離計算；只捲最近的捲動區，不動外層舞台；`until` 一起帶進來；
  - WaitScene、EventCard、NpcPanel 接線；
  - 事件卡 flex、可捲、上下漸隱；
  - 上緣漸隱 56px、60% 實色、z-index；
  - 彈窗不透明度 ≥ 0.96（實際是 1）；
  - NPC 完成＝純文字；
  - 沙漏原本會超出、翻轉 0～180 度都收在紙裡、畫法有縮放；
  - 封蠟點列固定而且不規則、二次曲線蠟緣、壓印、確定性、`Math.random` 換成會丟例外的函式也畫得出來；
  - 原始碼掃描：不用 `Math.random`、不用原生 `title=`。
- `rt3b6f7.test.ts`：13 項，涵蓋 B 和 C 的 9 項。
  - 右欄 0；
  - I K G J Y N R M 都墊圓底，圓底是最下層、亮度夠、在範圍內，停用 0.6；
  - 名字斷點例子與 10～27 字全掃描；
  - 代價組合掃描，行尾不留「・」；
  - 紀錄寬度；
  - 室內鏡頭：貼齊、留距、主角仍在安全區；
  - 對比 ≥ 4.5；
  - 操作詞小段；
  - `text-wrap: pretty`、`overflowFlag`、沒超出時漸隱高度 0。
- 改過的測試：`waitScene.test.ts` 1 項、`fix6f7.test.ts` 3 項、`skillBar6f6.test.ts` 1 項、`textless6a3.test.ts` 2 項。
- 浮動卡規則（`floatCardRule.test.ts`）照舊全過。

## commit

- `f34d418b`：RT-3 的程式修正
- `625e22fa`：RT-3 的重拍與新截圖
- `7b46034b`：6F-7 追加項
- `3b7db99c`：室內鏡頭留距與截圖
- 最後是浮動卡截圖與本報告

## 待 PM 決定

以下都照最保守的做法先做完了：

1. **800 戰鬥的右上戰況框蓋到地圖右上角**：只讓左欄後，戰況框蓋到地圖右上大約 1～2 格（`rt3b_03_battle_800`）。照指示沒有硬改。可以選：
   - 地圖往左靠，不置中；
   - 右上框在地圖上照舊變淡；
   - 維持現狀，玩家手動縮放。
2. **事件卡整張可捲**：判定的沙漏放在說書人框下面（RT-3 待決 5 的位置）。卡片變高時，上方的插圖會先被捲走。自動捲動會把沙漏和「擲骰」帶進畫面，但插圖要往上捲才看得到。
3. **上緣漸隱 56px 比較高**：設定、背包這類 hud 面板捲下去後，最上面約 34px 是實色。800 寬設定面板的可視高度是 337px，扣掉後約剩 280px。
4. **工具列的淺色圓底也加在地圖 M 鈕、滑過說明卡標題的小圖示上**（同一個元件），讓所有工具列圖示一致。淺色的 N（留言紙）、M（地圖）放在淺色圓底上，對比比原本低一點，但還有墨線外框看得出形狀。
5. **室內地圖往上對齊**：只在「比安全區大、但扣掉工具列放得下」時生效。這時地圖上緣可能被左上主角卡蓋到一角，蓋到的是房間左上的牆，不是出口。主角走到房間最上面那幾格時，照 6F-3 的規則改回跟著主角，鏡頭會往下捲一點。
6. **操作詞清單**（右鍵、左鍵、滑鼠、長按、Esc、Shift、Ctrl、Enter、空白鍵）是我定的。有其他詞要加，改 `KEEP_WORDS` 就好。
7. **`text-wrap: pretty`** 是瀏覽器的版面功能，Chrome 117 以後支援。舊瀏覽器只是照舊斷行，不會壞。
8. **反應詢問的新截圖**用新檔名 `rt3b_reaction_1600`、`rt3b_reaction_800`，沒有覆蓋 UI-E1b 已結案的 `ue1b_09_reaction_1600`。要覆蓋的話，換個檔名就好。
