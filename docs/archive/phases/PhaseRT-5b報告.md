# Phase RT-5b 報告：主城開場的驗收修正

實作者，2026-11-05。分支 `worktree-agent-ab00a1de28d54f7bf`（從 main `b2186dd1` 開始），沒有 push、沒有合併。

**依據**：`docs/art/RT-5檢查.md`（美術 PM 驗收：必修 1～7、小修 8～9、待判斷 a～f）、`docs/art/區域主題移植需求.md` 第 5 節、樣張 `capital-opening.png`；玩法 PM 決定：守印人站位（交接 3.5 `a61885f5`）、任務欄改「找渡婆婆」、地名小牌維持「樞島」、浮橋只畫斷繩斷板（交接 3.5 `a975018e`）。

**範圍**：
- 沒碰戰鬥畫面的 `rowLayout.ts`、`badgeLayout.ts`、`heightMark.ts`、`unitSprite.ts`、`BattleRenderer.ts`。
- 沒碰伺服器的交易、郵寄、掉落與存檔版號；這段**完全沒有改 `src/trpg`**，也沒有改 API（`openapi.json` 不變）。
- 沒改人物畫法（紙娃娃部件），只改醒來插圖裡主角的位置與角度。
- 沒有新增相依套件、原生 `title=`、`Math.random`。

**先講結論**
- 必修 1～8、小修 9～10 都修了，每項 1600×900 與 800×600 都有截圖，加同一幀的 `_zoom`，共 57 張 `docs/art/rt5b_*`。
- 新角色實際跑 ①→④：1600×900 全程 25.3 秒、800×600 24.4 秒，沒有戰鬥、沒有遭遇。
- 到過霧渡鎮之後再開大世界圖：雲嶺沒有傳送鈕、沒有「免費」字樣，說明卡是「雲嶺：已開放・你在這裡・點了看區域圖」。
- client 全部 vitest：258 個檔、2963 項全過。

---

## 1. 每項做了什麼

### 共用做法：要看得到的東西避開 HUD（必修 1、2、5）

新檔 `client/src/world/hudAvoid.ts`，純函式：

- **HUD 的實際矩形** `hudAvoidRects`：主角卡、隊友卡、影子鈕、地名、小地圖、時間天氣鈕、金幣欄、任務欄、功能列，加上說明列（「點格子走過去……」，`captionRect`，照 CSS 的位置算）。
  - 原本的 `hudInsets` 只把 HUD 簡化成四邊寬度。主角留在中央夠用，但地圖邊上的石碑、站在主角旁邊的人還是會被蓋住。
- **鏡頭微調** `nudgeCamera`：
  - 跟隨主角的鏡頭算好之後，在附近最多 96 像素（2 格）內，找一個讓「已經露出一部分的重要東西」整個露出來的位置。重要東西是：開場說話的人、主線給任務的人、橋頭石碑（含小牌與那一座浮橋）。
  - 照樣夾在地圖邊界內，主角不能被 HUD 蓋住。完全在畫面外的東西不拉鏡頭。
  - 往下可以多捲到說明列上面（`hudReach`），地圖最下排的浮橋不會被說明列壓住。
  - 候選位置固定順序，同分取移動最少、先試的那個。沒有亂數，同樣輸入同樣結果。
- **石碑小牌換邊** `placeTag`：預設在石碑上方。
  - 壓到 HUD 時，依序試：上方往內推、石碑左邊、右邊、下方。
  - 石碑被下方功能列或說明列蓋住時，小牌抬到說明列上面（最多抬 2 格，`data-side="lift"`）。
  - 都放不下而且預設位置會壓到 HUD 時先不畫（`data-side="hidden"`）。只是出了畫面邊、沒壓到 HUD 的，照預設跟著鏡頭移出去。
- 接線：`WorldScreen` 把 `avoid`、`reach` 傳給 `WorldField`；`WorldField` 算鏡頭時呼叫 `nudgeCamera`；`FieldSteleTags` 用 `placeTag`。就地開打框住戰場（`frame`）時不微調。

### 必修 1：東側石碑小牌被小地圖、時間天氣鈕蓋住，石碑被金幣欄蓋住

- 1600×900 開場畫面：鏡頭往右移一點，「魔導樞市／之後的賽季」小牌與石碑都在右欄左邊，沒壓到金幣欄。
- 800×600：開場看不到東側石碑，所以從新角色走過去拍。小牌與石碑都在小地圖、金幣欄左邊。
- 截圖：
  - `rt5b_1_plaza_1600.png`／`_zoom`（開場，按過「站起來」）
  - `rt5b_1_east_1600.png`／`_zoom`、`rt5b_1_east_800.png`／`_zoom`（走到東側石碑旁）
  - `rt5b_1_plaza_800.png`／`_zoom`（800 開場；東側石碑不在畫面內，zoom 是守印人那一塊）

### 必修 2：南側「灰燼荒原／尚未開放」被技能列蓋住

- 走到南邊：鏡頭往下多捲，兩座南側石碑、小牌與浮橋都在說明列上面。
- 從南邊走回西邊、荒原石碑在畫面下緣被說明列蓋住時，小牌抬到說明列上面。這就是原本 `steles_west_1600` 那一種畫面。
- 截圖：
  - `rt5b_2_south_1600.png`／`_zoom`、`rt5b_2_south_800.png`／`_zoom`
  - `rt5b_7_bridge_west_1600.png`：原本出問題的那一種畫面。荒原小牌約在 772,728，說明列上緣是 783。

### 必修 3：雲嶺浮動卡的字被圖釘切掉

- 原因：說明文字每一段都是 `nowrap`。兩個 nowrap 的 span 之間 Chrome 不會斷行，整句擠成一行，被卡片寬度切掉。
- 改法（`AtlasMap.tsx` 的 `HintPhrases`、`atlas.css`）：
  - 段與段之間放 `<wbr>`，換行只發生在段落之間（`word-break: keep-all`）。
  - 一段比卡片還寬時，才在段內斷開（`overflow-wrap: anywhere`）。
- 釘住時右上角的金色圖釘往外凸 6px，會壓到第一行最後幾個字。`float-card.css` 讓**所有釘住的說明卡**（`float-panel`、`part-tip-box`）右邊多留 18px。依流程改善 E，同類問題一次修好。
- 結果：卡片換成兩行「雲嶺：已開放・點了看區域圖・／點城鎮傳送到霧渡鎮（第一次免費）」，高 52px。`scrollWidth` 等於 `clientWidth`（238），沒有被切掉。
- 截圖：`rt5b_3_float_1600_pinned.png`／`_zoom`、`rt5b_3_float_800_pinned.png`／`_zoom`。

### 必修 4：醒來插圖

- 檔案：`eventArtAwaken.ts`。
- **主角**：照樣張移到晶柱右側。
  - 躺著：腳在光圈中心右邊 96。
  - 半坐起：腳在中心右邊 80、往下 46。
  - 半坐起的角度從 41° 改成約 24°，看得出是在坐起來。
  - 頭不壓晶柱，也不壓在光圈東北邊雲嶺那顆光點上。
- **晶冠紫旗**：原本在正後方，旗桿穿過遠處的藍頂建築（4.2～5.7 格）。改到晶柱左後方（2.75 格），旗桿與旗面都在建築左邊，也不碰晶柱。
- 800 寬是同一張插圖縮放，兩個問題一起修好。
- 截圖：`rt5b_4_awaken_1600.png`／`_zoom`、`rt5b_4_awaken_800.png`／`_zoom`。

### 必修 5：ferry_800 渡婆婆被提示列、技能列蓋住

- 渡婆婆是主線給任務的人，是鏡頭微調的目標。
- 800×600 抵達時鏡頭往下約 78px：渡婆婆整個人在說明列上面，主角還在畫面中上。
- 截圖：`rt5b_5_ferry_800.png`／`_zoom`、`rt5b_5_ferry_1600.png`／`_zoom`。
  - 1600 本來就看得到，鏡頭沒動。

### 必修 6：守印人的泡泡

- **整句留 8 秒**（`opening.GUIDE_BUBBLE_MS`）：之後收成只剩「！」（`data-guide="folded"`）。說明卡多一句「點了看指示」。
- **點了展開**：點收起的「！」會展開整句，再留 8 秒，不會走過去。展開時點「！」照舊走過去、開公告板。
- **「！」留到到過霧渡鎮**：收起後「！」照舊在，直到伺服器不再給開場（到過霧渡鎮）。
- **邊緣的「↗」**：字重 900、15px（收起時 17px）、金色 `#f2b416`，加深色描邊，在米色泡泡上看得清楚。收起時箭頭放在「！」旁邊。
- **泡泡位置**：
  - 守印人搬到傳送陣旁之後，上面放得下時泡泡放在頭頂往左上（`nw`），不蓋到東邊剛醒來的主角與晶柱。
  - 上面放不下時，照原本的做法放左邊。
  - 夾到畫面邊上時，泡泡往畫面中間那一邊放，避免壓到左上的隊友卡。
  - 離畫面左右邊留 26px，避免「！」加箭頭被切掉一半。
- 截圖（1600、800 各一組，都附 zoom）：
  - 完整句：`rt5b_6_guide_open_*`
  - 收起只剩「！」：`rt5b_6_guide_folded_*`
  - 點了再展開：`rt5b_6_guide_expand_*`
  - 實機：8.6 秒後沒有泡泡，點了以後泡泡回來（`shots_*.json` 的 `bubbleAfter8s: false`、`bubbleAfterClick: true`）。
  - 夾邊加金色箭頭的樣子：`rt5b_1_east_800.png` 左下角（走遠後守印人在畫面外）。

### 必修 7：浮橋斷口

- 檔案：`capitalArt.drawSkyBridge`，地圖格數不變。
- 由內往外的畫法：
  - 三塊整齊的木板。
  - 一塊斷了一半的木板：鋸齒斷口、淺色木心、一條裂痕。
  - 缺一塊：露出底下藍灰的雲影，一眼看得出是空的。
  - 一塊脫落、歪掛的碎板（兩端都是斷口，底下有影子）。
  - 最外端再缺一塊。
- 斷繩比繩欄粗（2.6）、深色，從斷口往外垂，末端散成三股。最後一根繩柱留在斷口前。
- 截圖：
  - 西：`rt5b_7_bridge_west_1600.png`／`_zoom`、`rt5b_7_bridge_west_800.png`／`_zoom`
  - 南：`rt5b_2_south_*_zoom`、`rt5b_9_*`
  - 東：`rt5b_1_east_*_zoom`

### 必修 8：守印人站位

- 依據：玩法 PM 決定（交接 3.5 `a61885f5`）。
- `content/world/fields/capital/capital.yaml`：守印人從封印廣場 [25, 3] 移到 [14, 12]。
  - 位置：傳送石 [15, 11] 西南邊相鄰的空格（石板地、沒有物件）。
  - 不在傳送石、抵達點 [16, 11]，也不在往北（導師殿）、東（鐵匠鋪）、南（傭兵營）的通道上。情境物件照舊不擋路。
- 面向從西改成東，面向剛醒來的主角。這是畫法欄位，見第 2 節第 3 點。
- 更新的測試：
  - `tests/world/test_capital_figures_6v1.py`（格子）
  - `client/src/world/figures6v1.test.ts`（格子、面向、點那一格的互動）
- `trpg content check` 通過（主城 1／1）。
- CLI 快照：`tests/cli/test_output_snapshots.py`（`-m "slow or not slow"`）25 passed，沒有變，不用重產。
- 截圖：`rt5b_8_keeper_1600.png`／`_zoom`、`rt5b_8_keeper_800.png`／`_zoom`。

### 小修 9：南側兩座浮橋對準石碑

- 荒原的石碑 [17, 22] → [16, 22]，霜潮的石碑 [28, 22] → [29, 22]。
- 兩座都站在自己浮橋那一欄的橋頭，`objects` 的石柱與 `situation_objects` 一起移。
- 浮橋本身沒動，地圖格數不變。
- 截圖：
  - `rt5b_9_align_1600.png`：與 `rt5b_2_south_1600.png` 同一幀。附 `_zoom`（兩座一起）與 `_frost_zoom`。
  - `rt5b_9_frost_800.png`／`_zoom`：800 寬一次看不到兩座，荒原那座看 `rt5b_2_south_800`。

### 小修 10：主線「！」比支線突出；任務欄

- **任務欄**：玩法 PM 決定（交接 3.5 `a975018e`），已照改。
  - `content/world/newcomer.yaml` 的 `guide_town_zh` 從「找頭上有「！」的渡婆婆說話」改成「找渡婆婆」。文字放在內容檔，畫面沒有寫死。
  - `tests/api/test_newcomer_api_6f2.py` 跟著改。
- **主線「！」**：`.field-alert.main`。
  - 21×24（支線 16×18），金色漸層、深棕粗框。
  - 外面兩層金色光暈。
- **哪一位是主線**：`opening.mainQuestNpc`。
  - 條件：到了新手小鎮、還沒接新手任務時，伺服器指引（`guide.text_zh`）點名、頭上有任務「！」的 NPC。
  - 開場時守印人的「！」也用主線樣式。
  - 支線照舊：黃底任務、藍底傳聞。
- 截圖：`rt5b_10_alerts_1600.png`／`_zoom`、`rt5b_10_alerts_800.png`／`_zoom`。
  - 渡婆婆是金色加光暈。
  - 另外兩位（`shopkeeper_liu`、`gran`）的「！」是藍色傳聞，照舊。
  - 任務欄寫「找渡婆婆」（1600 的 `rt5b_5_ferry_1600.png`；800 寬時任務欄照 6F-3 收合成圖示）。

### 補拍：到過霧渡鎮之後再開大世界圖

- `rt5b_atlas_after_1600.png`／`_zoom`、`rt5b_atlas_after_800.png`／`_zoom`。
- 雲嶺的傳送鈕不在了（人就在雲嶺），整頁 `innerText` 沒有「免費」。
- 滑過雲嶺的說明卡是「雲嶺：已開放・你在這裡・點了看區域圖」。

### 照收，不用改

- 地名小牌只寫「樞島」。
- RT-5 報告第 6 節的 #3、#4、#7、#8。

## 2. 待 PM 決定

1. **主線給任務的人怎麼認**：用前端比對伺服器指引的文字裡有沒有 NPC 的名字（「找渡婆婆」裡有「渡婆婆」）。
   - 這樣做是為了不改 API：交易、郵寄的 agent 同時在改伺服器，改 `openapi.json` 容易衝突。
   - 指引改寫成不含名字時就認不出來，畫面會退回一般的「！」，不會出錯。
   - 要穩一點，可以之後在 `GuideView` 加 `npc` 欄位（新手任務給任務的人）。
2. **鏡頭微調一直開著**：不只開場，走路時只要石碑或主線的人露出一部分，鏡頭就會在 2 格內偏一點。
   - 理由：必修 2 的畫面（南側小牌被技能列蓋住）是走路途中拍的，不是開場畫面。
   - 1600×900 開場時鏡頭往上偏了約 85px：北側晶冠石碑那一排露出來，主角在畫面中下。
   - 如果覺得走路時鏡頭偏離中央會不舒服，可以改成只在開場期間微調。
3. **守印人的面向**：站位依玩法 PM 決定。面向從西改成東，面向剛醒來的主角，這一點是我做的。
4. **石碑小牌放不下時先不畫**：小牌放不下、而且會壓到 HUD 時，先藏起來，鏡頭走開就回來。這種情況石碑本身也幾乎被蓋住。
5. **浮動卡的圖釘留白套用到所有釘住的說明卡**：右邊多 18px，避免同樣的切字。卡片釘住時會稍微變寬一點。
6. **展開泡泡的計時**：點了展開後，重新算 8 秒再收起。

## 3. 驗證與結束碼

**截圖方式**
- 無頭 Chrome，加 `--mute-audio`；網址加 `?mute=1`。
- 用 `Emulation.setDeviceMetricsOverride` 把視窗真的設成檔名上的尺寸（device scale 1）。
- 全圖與 `_zoom` 是同一幀：只拍一次 PNG，zoom 從同一張裁出、最近鄰放大。
- 交件前用 `file` 核對：28 張全圖都是 1600×900 或 800×600，和檔名一致。

**①→④ 實測**（`scratchpad/rt5b/flow.mjs`）
- 從按「建立並在主城醒來」到站上霧渡鎮：1600×900 是 25.3 秒，800×600 是 24.4 秒。
- 含模擬看字的停頓（醒來 5 秒、廣場 4 秒、大世界圖約 5 秒）。
- 建角頁到醒來卡約 4.4 秒。
- 全程沒有戰鬥畫面、沒有遭遇卡。
- 第一次傳送鈕寫「傳送到霧渡鎮（免費）」，抵達後 `--rt-accent` 是 `#6aa84a`。

**6.5.1 浮動卡實測**（大世界圖上雲嶺浮島的說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓ | ✓ |
| 分 6 步滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片 52px 高、沒有可捲內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 先關卡片，大世界圖還開著 | ✓ | ✓ |
| 字沒被切掉（`scrollWidth`＝`clientWidth`＝238，兩行） | ✓ | ✓ |

**排版煙霧檢查**
- 網址 `/?dev=1&anim=0.1&mute=1`，先 `localStorage.clear()` 再重新載入，跑 `__layoutSmoke.runCase`。
- 1600×900、1040×624、800×600 都是全 PASS（共 39 列 PASS、0 FAIL）。
- 結束碼 0（`scratchpad/rt5b/smoke.log`）。

**每次 commit 前**（最後一次程式 commit 之後重跑）
- `ruff check`：0（All checks passed）。
- `ruff format --check`：0（2195 files already formatted）。
- `mypy src`：0（Success，531 source files）。
- `lint-imports`：0（13 kept、0 broken）。
- 重播：`trpg battle --map swamp --seed 7 --log-json` 結束碼 0；`trpg battle replay` 結束碼 0（88 個動作、313 個事件，最終狀態一致）。

**相關 pytest**（`-n 8`）：119 passed，結束碼 0。
- `tests/api/test_opening_rt5.py`
- `tests/api/test_newcomer_api_6f2.py`
- `tests/world/test_capital.py`
- `tests/world/test_capital_hub.py`
- `tests/world/test_newcomer_6f2.py`
- `tests/world/test_capital_figures_6v1.py`
- `tests/world/test_capital_figures_6v3.py`
- `tests/content/test_capital_field.py`
- `tests/content/test_newcomer_content_6f2.py`

**內容與快照**
- `trpg content check`：通過（648 個檔案、跨檔案檢查與連通性通過；主城 1／1）。
- `tests/cli/test_output_snapshots.py`（`-m "slow or not slow"`）：25 passed，結束碼 0，快照沒變。

**前端**
- 新測試 `client/src/world/rt5b.test.ts`：14 項，涵蓋：
  - HUD 矩形、小牌換邊、抬高與藏起
  - 鏡頭微調（主角不被蓋、在畫面外不拉、確定性）
  - 泡泡收起與展開、`nw` 位置
  - 主線「！」、任務欄文字
  - 醒來插圖位置、斷橋畫法
  - 守印人站位、南側石碑對齊（直接讀內容檔）
- client 全部 vitest：258 個檔、2963 項全過，結束碼 0。
- `corepack pnpm -C client build`：結束碼 0（只有原本就有的 chunk 大小提醒）。

複雜度：沒有新增 `noqa`。

## 4. 檔案清單

**新增**
- `client/src/world/hudAvoid.ts`
- `client/src/world/rt5b.test.ts`
- 截圖 `docs/art/rt5b_*`（57 張）
- 本報告

**修改**
- 內容：`content/world/fields/capital/capital.yaml`（守印人、南側兩座石碑）、`content/world/newcomer.yaml`（`guide_town_zh`）
- 畫法：`client/src/render/eventArtAwaken.ts`、`client/src/render/capitalArt.ts`
- 畫面：
  - `client/src/screens/WorldScreen.tsx`
  - `client/src/world/WorldField.tsx`、`FieldHeads.tsx`、`fieldPeople.ts`、`opening.ts`、`AtlasMap.tsx`
- 樣式：`client/src/world/fieldPeople.css`、`client/src/styles/atlas.css`、`client/src/styles/float-card.css`
- 測試：
  - `tests/api/test_newcomer_api_6f2.py`、`tests/world/test_capital_figures_6v1.py`
  - `client/src/world/figures6v1.test.ts`、`client/src/world/rt5.test.ts`（夾邊距離 12 → 26）

## 5. 程序

- 自己啟動的程序：
  - API 8476：`scratchpad/rt5b/serve.py`，用 worktree 的 `.venv` 與 `client/dist`，存檔在 `scratchpad/rt5b/saves`。背景工作 `b54oia3m4`。
  - CDP 9476 的無頭 Chrome（`--mute-audio`）：PID 46320。
- 結束時只用背景工作 ID 與這個 PID 關掉。
- 沒碰 8000、8001、8010、`tmp_x`、`saves/`。
- 暫存都在 `scratchpad/rt5b/`，沒有 commit。
- worktree 裡跑了 `uv sync --frozen` 和 `corepack pnpm -C client install --frozen-lockfile`。這兩個是 worktree 的環境，不 commit。
