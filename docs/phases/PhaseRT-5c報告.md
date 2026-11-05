# Phase RT-5c 報告：主城開場第二次驗收修正

實作者，2026-11-05。分支 `worktree-agent-a63bf44178d97a04e`（從 main `c64b2b8e` 開始），沒有 push、沒有合併。

**依據**：`docs/art/RT-5b檢查.md`（必修 1～4、小修 5～10）。

**範圍**
- 沒碰戰鬥畫面：`rowLayout.ts`、`badgeLayout.ts`、`heightMark.ts`、`heightTag.ts`、`unitSprite.ts`、`BattleRenderer.ts`。
- 沒碰郵寄、交易、裝備規則和版號。`src/trpg` 完全沒改，API 也沒改。
- 沒新增或修改紙娃娃的部件、頭像畫法。必修 1 只用既有的骨架姿勢（6M-1 `InkPose`）。
- 沒改地圖內容檔，所以不用跑 `trpg content check`，`RULE_HASHES` 也不用動。

---

## 1. 每項做了什麼

### 必修 1：半坐起（做法：**髖部彎**，沒有改成躺平）
- 檔案：`client/src/render/eventArtAwaken.ts`。
- 原本是把整個人轉 -0.42。現在整個人不轉，改用紙娃娃既有的骨架姿勢 `AWAKEN_SIT_POSE`：
  - `hipN`、`hipF` 各 90°：兩條腿在髖部往前抬，平貼地面，腳朝東。
  - `lean` -0.42：上半身以髖為軸往後仰約 24°。
  - `arm` 1.45、`armF` 1.35：兩手往後下撐地。
- 再整個往下放 13.5，讓屁股和腿貼在地上。
- 影子移到屁股和腿下面。躺著那一格照舊。
- 這是 6M-1 已有的骨架參數（腿、上身、手臂各自在關節轉），部件形狀和頭像都沒改。
- 截圖：
  - `rt5c_1_halfsit_1600.png`／`_zoom`／`_hero_zoom`
  - `rt5c_1_halfsit_800.png`／`_zoom`／`_hero_zoom`
  - `_hero_zoom` 是同一幀主角附近再放大。

### 必修 2：夾在畫面邊的箭頭
- 文字箭頭改成 SVG 元件 `EdgeArrow`（`FieldHeads.tsx`）：
  - 20×20 畫面像素。
  - 金色筆畫 3.5px，底下先畫一層 7.5px 的深色 `#3a2406`，每邊多出 2px 描邊。
  - 方向用旋轉（`opening.EDGE_ANGLE`）。
- 泡泡名字旁和收起來的「！」旁都用這個元件。CSS 在 `fieldPeople.css`。
- 截圖：
  - 800：`rt5c_2_arrow_800.png`／`_zoom`（展開時，6 倍放大）、`rt5c_2_arrow_folded_800.png`／`_zoom`（收起時）。
  - 1600：`rt5c_2_arrow_1600.png`／`_zoom`。**1600×900 時主城整張地圖都在畫面內，守印人不會出畫面，所以不會夾邊**（見第 2 節第 1 點）。這兩張是對照，泡泡在原位。

### 必修 3：「灰燼荒原」小牌蓋住主角
- `hudAvoid.placeTag` 多一個參數 `blockers`：地圖上每個人物的範圍（`unitRect`），從頭上的「！」到腳下的徽章和光圈。
- 候選位置照舊依序試：上、上偏右、上偏左、左、右、下、抬高。小牌要同時不壓 HUD、不蓋人物。
- 都放不下時，退回 RT-5b 的順序（只避開 HUD），再不行就先不畫。
- `FieldSteleTags` 從 `WorldField` 拿到所有人物的格子（`model.units`）。
- 結果：主角站在荒原石碑正上方時，小牌換到石碑左邊（`data-side="w"`）。
- 截圖：`rt5c_3_tag_1600.png`／`_zoom`、`rt5c_3_tag_800.png`／`_zoom`。

### 必修 4：夾邊的泡泡落在 B 頭上
- `opening.guideAnchor` 多一個選項 `{ others, bubble }`。`others` 是其他人物的頭頂，`FieldHeads` 用 `headAnchor` 算好傳進來。
- 夾到邊上以後，如果「！」（含箭頭）或整句泡泡壓到別人的頭，就沿著夾住的那條邊挪開：
  - 夾在上下邊時左右挪，夾在左右邊時上下挪。
  - 每次挪 8，最多 240，挪得少的位置先試。
  - 找不到兩個都不壓的位置時，至少讓「！」不壓到別人的頭。
- 截圖：
  - `rt5c_4_bubble_800.png`／`_zoom`：「！」離開 B 頭頂，在 B 右上方，泡泡也沒蓋到 A、B。
  - `rt5c_4_bubble_1600.png`／`_zoom`：開場畫面對照。1600 不會夾邊。

### 小修 5：鏡頭往上偏時的深色帶
- `hudReach.top` 改成右上地名列的下緣（1600×900 約 40px）。原本是左欄隊友卡的下緣（220px）。
- `WorldField` 再扣掉畫布頂端給高物件留的透明區（`topReserve`），所以深色帶從第一排格子算起。
- `nudgeCamera` 多一步 `trimTopBand`：跟隨鏡頭本身留了太高的深色帶時往下收。
  - 條件：主角不會因此被 HUD 蓋住，看得到的目標也不能變少。
  - 每 8px 試一次，收不完就收一部分。
- 鏡頭微調照舊一直開著。
- 結果：東側 1600 深色帶從約 128px 降到約 40px，和「樞島」地名列下緣同高。
- 截圖：`rt5c_5_band_1600.png`／`_zoom`。

### 小修 6：兩格寬的浮橋只畫一個斷口
- 檔案：`capitalArt.drawSkyBridge`。
- 接鄰那一邊的木板畫到格子邊，接縫不描邊（新函式 `joinedPlank`），並裁在格子內。
- 斷口只畫在右端那一格（`railR`）：斷了一半的木板、缺板的雲影、脫落的碎板。
- 另一格的木板整齊排到斷口那一排就停。繩欄照舊在斷口斷開。
- 單格的橋畫法不變。
- 截圖：`rt5c_6_bridge_1600.png`／`_zoom`（西側雲嶺浮橋）。南側也可以看 `rt5c_3_tag_*_zoom` 下緣。

### 小修 7：說明列壓在荒原石碑碑面上
- 原因：主角站在西邊時，要露出荒原碑身，鏡頭得往下移約 133px，超過微調上限 96px（2 格）。
- 做了兩件事：
  1. **鏡頭微調**：
     - 目標改成加權（`NudgeTarget.weight`）：碑身和主線的人 3 分，石碑＋小牌＋整座浮橋 1 分。
     - 除了每 8px 的步距，也試「目標的邊剛好貼齊 HUD 邊」的位置（`edgeStops`）。
  2. **說明列水平挪開**：`captionShift` 加上 `WorldField` 的 `--cap-dx`。
     - 鏡頭移不開、說明列仍壓到碑身或主線的人時，說明列往旁邊挪。
     - 挪得少的那一邊先試。挪過去不能壓到別的 HUD，也不能出畫面。
     - 動畫 0.15 秒。
- 這個畫面裡說明列往左挪了 149px（`data-shift="-149"`）。
- 截圖：`rt5c_7_caption_1600.png`／`_zoom`。

### 小修 8：東側浮橋第二段被任務欄蓋住
- 鏡頭微調的浮橋目標，從 `bridge_<區域>` 那一格改成連到所有相鄰的浮橋格（`bridgeCells`），所以兩段都算進去。
- 東側 1600：浮橋兩段都在任務欄左邊。
- 截圖：`rt5c_8_eastbridge_1600.png`／`_zoom`。

### 小修 9：浮動卡第一行結尾的「・」
- 原因：「・」是不能放在行首的字（禁則），換行時瀏覽器把它推到上一行的行尾。
- 改法（`AtlasMap.HintPhrases`、`atlas.css`）：
  - 每一段改成 inline-block，「・」放在段尾。
  - 排好之後量每段的 `offsetTop`。段尾剛好是行尾時，那個「・」用 `visibility: hidden` 藏起來，寬度不變，不會又把下一段拉上來。
  - 用 ResizeObserver 重量（釘住時卡片會變寬 18px）。
- 實測 `innerText`：「雲嶺：已開放・點了看區域圖⏎點城鎮傳送到霧渡鎮（第一次免費）」，第一行結尾沒有「・」。`scrollWidth`＝`clientWidth`＝238。
- 截圖：`rt5c_9_float_1600_pinned.png`／`_zoom`、`rt5c_9_float_800_pinned.png`／`_zoom`。

### 小修 10：完整名字測試
- 新函式 `opening.mentionsName(text, name, others)`。名字算「完整」要同時符合：
  - 前後是句子頭尾、標點、空白，或指引常用的動詞、助詞（例：「找」「向」「說」「的」）。
  - 這一段不能落在同一句裡另一個更長的名字裡。
- `mainQuestNpc` 改用 `mentionsName`，不再用子字串 `includes`。
- 新測試：
  - `client/src/world/rt5c.test.ts`：
    - 內容鎖：`guide_town_zh` 和 `guide_capital_zh` 都含新手任務給任務的人（`starter_ferry.giver`）的完整名字「渡婆婆」；別名「婆婆」不算。
    - 反例：「婆婆」配不到「找渡婆婆」。地圖上只有「婆婆」有任務「！」時，指引「找渡婆婆」不會認「婆婆」當主線。
  - `tests/content/test_newcomer_guide_name_rt5c.py`：Python 端同樣的內容鎖，從內容庫讀新手任務、NPC 名字和別名。

## 2. 待 PM 決定

1. **必修 2、4 在 1600×900 沒有夾邊畫面**：主城整張地圖的寬度放得下，上下最遠也看得到守印人，所以 1600 寬不會夾邊。1600 那兩張是對照。如果還是要 1600 的夾邊畫面，需要另外做開發頁。
2. **小修 5「HUD 高度」怎麼解讀**：
   - 現在照右上地名列「樞島」的下緣，1600×900 約 40px。
   - 原本的上限是左欄隊友卡下緣（220px），那時候 RT-5b 的 70px 就已經在上限內，所以我判斷美術 PM 指的是比較矮的那條。
   - 另外也把跟隨鏡頭本身留的深色帶收進來（條件是主角不被蓋、目標不變少）。
3. **小修 7 的說明列會水平挪**：只有在鏡頭微調移不開、說明列還壓到碑身或主線的人時才挪。如果不希望說明列移動，可以改成這時候藏起來。
4. **鏡頭微調的權重**：碑身和主線的人 3 分，石碑＋小牌＋浮橋 1 分。原因是小牌壓到 HUD 時還能自己換邊，碑身被壓到比較明顯。
5. **小牌避不開人物時的退路**：先退回只避開 HUD（可能蓋到人物），再不行才藏起來。截圖裡沒有出現這種情況。
6. **完整名字的前後字表**（`NAME_BEFORE`／`NAME_AFTER`）：照現在的指引句挑的。指引改寫時，如果名字前後接了表外的字，就認不出來，畫面會退回一般的「！」，不會配錯人。

## 3. 技術債

- **`GuideView` 之後加 `npc` 欄位**（新手任務給任務的人的 ID）。加了以後前端不用再比對名字，`mentionsName` 只留著當沒有欄位時的退路。這段沒改 API，是為了不和同時進行的郵寄、交易 agent 衝突。
- 鏡頭微調多了貼邊候選（`edgeStops`），每次重算鏡頭的組合比 RT-5b 多。主城約 10 個目標、10 塊 HUD，實測沒有卡頓。如果之後目標多很多，可以考慮限制候選數。

## 4. 驗證與結束碼

**截圖**
- 無頭 Chrome 加 `--mute-audio`，網址加 `?mute=1`。用 `Emulation.setDeviceMetricsOverride` 把尺寸真的設成 1600×900、800×600（device scale 1）。
- 每張全圖只拍一次，`_zoom` 從同一張裁出來、最近鄰放大。
- 交件前用 `file` 核對：15 張全圖都和檔名上的尺寸一致。
- 全部 32 張 `docs/art/rt5c_*`。

**①→④ 實測**（新角色，從按「建立並在主城醒來」到站上霧渡鎮）
- 1600×900：25.7 秒（建角到醒來卡 4.5 秒）。
- 800×600：24.4 秒。
- 都含模擬看字的停頓，全程沒有戰鬥、沒有遭遇。
- 第一次傳送鈕寫「傳送到霧渡鎮（免費）」。抵達後任務欄是「找渡婆婆」，渡婆婆是主線「！」。

**6.5.1 浮動卡實測**（大世界圖上雲嶺浮島的說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓ | ✓ |
| 分 6 步滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關（卡片 52px 高，沒有可捲內容） | ✓ | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 先關卡片，大世界圖還開著 | ✓ | ✓ |
| 字沒被切掉（`scrollWidth`＝`clientWidth`＝238），第一行結尾沒有「・」 | ✓ | ✓ |

**排版煙霧檢查**
- 網址 `/?dev=1&anim=0.1&mute=1`，先 `localStorage.clear()`。
- 1600×900、1040×624、800×600：39 列 PASS、0 FAIL，結束碼 0。

**每次 commit 前**（最後一次程式 commit 之後跑）
- `ruff check`：0。
- `ruff format --check`：0（2212 files already formatted）。
- `mypy src`：0（540 source files）。
- `lint-imports`：0（13 kept、0 broken）。
- 重播：`trpg battle --map swamp --seed 7 --log-json` 結束碼 0；`trpg battle replay` 結束碼 0（88 個動作、313 個事件，最終狀態一致）。

**相關 pytest**：12 passed，結束碼 0。
- `tests/content/test_newcomer_guide_name_rt5c.py`
- `tests/content/test_newcomer_content_6f2.py`
- `tests/api/test_newcomer_api_6f2.py`
- `tests/api/test_opening_rt5.py`

**前端**
- 新增 `client/src/world/rt5c.test.ts`，18 項。
- `rt5b.test.ts` 拿掉「半坐起角度 0.2～0.6」那兩行，改由 rt5c 測試鎖住髖部彎。
- client 全部 vitest：260 個檔、2990 項全過，結束碼 0。
- `corepack pnpm -C client build`：結束碼 0（只有原本就有的 chunk 大小提醒）。

**複雜度**：沒有新增 `noqa`。

## 5. 檔案

**修改**
- `client/src/render/eventArtAwaken.ts`、`client/src/render/capitalArt.ts`
- `client/src/world/FieldHeads.tsx`、`opening.ts`、`hudAvoid.ts`、`WorldField.tsx`、`AtlasMap.tsx`、`rt5b.test.ts`
- `client/src/world/fieldPeople.css`、`client/src/styles/world-hud.css`、`client/src/styles/atlas.css`

**新增**
- `client/src/world/rt5c.test.ts`
- `tests/content/test_newcomer_guide_name_rt5c.py`
- `docs/art/rt5c_*`（32 張）
- 本報告

## 6. 程序

- API 伺服器 8477：`scratchpad/rt5c/serve.py`，用 worktree 的 `.venv` 和 `client/dist`，存檔在 `scratchpad/rt5c/saves`。背景工作 `b0nvxbgqw`，已用 TaskStop 結束。
- 無頭 Chrome，CDP 9477（`--mute-audio`）：PID 3200，已用 `taskkill /PID 3200 /T` 結束，只結束這一棵程序樹。
- 結束後確認 8477、9477 都沒有在監聽。
- 沒碰 8000、8001、8010、`tmp_x`、`saves/`。
- 暫存都在 scratchpad 的 `rt5c/`，沒有 commit。
- worktree 裡跑了 `uv sync --frozen` 和 `corepack pnpm -C client install --frozen-lockfile`，是環境用的，不 commit。
