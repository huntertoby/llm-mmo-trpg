# Phase AR-SK2 報告：SK-2 三個新原語的美術移植（前端）

> 依據：`docs/art/SK-2原語-移植需求.md`（6 項）、`docs/art/SK-2原語-美術.md`（以「第 2 版」為準）、樣張 `docs/art/sample/sk2Primitives.js`／`sk2-primitives.html`。
> 分支 `worktree-agent-abeaeb81e526bdc17`（起點 main `89006d7c4`）。沒有改 `docs/design/`、`config/`、引擎規則、Python，也沒有碰 SK-2b 的檔案（組合器、驗證器、LLM、淨化、疾病擴散後端、`llmFlow.ts`）。

## 0. 結論

| 項目 | commit | 一句話 |
|---|---|---|
| 0 修 main 的兩個 vitest 失敗 | `2be9e29c5` | `point_blank`、`long_range` 條件用 `COND_ALIAS` 明確退回（借「夾擊」「目標落單」） |
| 1 部件圖樣 | `8ff098060` | 吸收表面、疾病擴散、鉤的專屬圖樣；拿掉三筆暫借；病菌黃綠進 `palette.ts` |
| 2～4 三種演出 | `e68352878` | 吸收表面（表面提早收縮、光柱上下兩層、冰晶、光球、收益圖樣）、疾病擴散（範圍格、弧線、虛線、V、箭頭）、鉤三種（一般、熔岩前煞住、拉不動改撞擊） |
| 5 鎖鏈與虛線的畫面下限 | `e68352878`（畫法）＋`8f5d1b1cf`（測試） | K＝max(1, 3 ÷ (4.2 × 地圖縮放))，鏈節、間距、外框、鉤頭、擴散虛線、箭頭、V 都乘 K |
| 6 「會擴散」記號與用字 | `0eed0ad2b` | B 案記號（戰場狀態列、HUD 狀態卡 20）、狀態卡標籤「會擴散」＋說明一行、浮字統一成「擴散」 |
| 截圖、開發頁 | `3ab05456d` | `client/dev/arsk2-gallery.html`、`sk2-gallery.html` 加 `&strip=`、`&w=`；10 張截圖 |

項目 2～5 共用同一條「事件 → 演出描述 → 效果 → Canvas 畫法」，拆不開，所以 2～4 一個 commit、5 的畫法在同一個 commit 裡，另外補一個測試 commit。

## 1. 各項做法

### 1.0 兩個 vitest 失敗
- 原因：SK-1 加了 `point_blank`（貼身）、`long_range`（遠距）兩個條件，`QP.COND` 沒有圖。移植需求與樣張都沒有距離類的圖樣。
- 做法：`qIcon/parts.ts` 加 `COND_ALIAS`（同 `EFFECT_ALIAS`、`TRIG_ALIAS` 的做法），`entry("condition", …)` 先查它；`skillParts.KNOWN_PARTS.conditions` 含別名。
  - 貼身 → 夾擊（`flanked`：人形兩側貼著紅色敵方三角）
  - 遠距 → 目標落單（`target_isolated`：光柱下一個孤立的人形）
- 沒有改兩個測試的斷言。`n(QP.COND)` 仍是 22。

### 1.1 部件圖樣（移植需求第 1 項）
- `sk2Primitives.js` 第 2 版的 `germ`、`hookJ`、`hookArt`、`link`、`absorbArt`、`contagionArt`、`hookChip` 逐行搬進 `qIcon/parts.ts`（`SK2_EFFECT`，接在 `EFFECT` 最後）。縮放照第 2 版自查表：吸收表面 0.86（往下 0.3）、疾病擴散 30／26 是 0.80、18 是 0.98、鉤 0.88。鋼色用第 2 版提亮的 `#dfe5ec`／`#9aa4b0`。
- `EFFECT_ALIAS` 拿掉 `absorb_surface`、`contagion`、`hook` 三筆（`reroll` 照舊）。
- 病菌黃綠：`palette.ts` 的 `GERM_COLORS`（身 `#c4e44c`、亮 `#f0ffb0`、暗 `#7a9a26`、刺頭 `#e2f47a`）。
- 和樣張不同的地方（不改畫法）：樣張的 `ln(..., "butt")` 改傳 `"miter"`。遊戲端 `core.ln` 的第 5 個參數是 lineJoin，不是 `"round"` 時線端一律畫成 butt；這幾條線都只有兩點，join 不影響。
- 吸收表面的 `T`（表面色）：遊戲端照樣張畫預設水色，沒有照技能的表面染色（美術 5.1 第 2 點說由開發決定，這裡採保守做法）。
- 有改到既有測試，都是「新增部件時要跟著更新的清單」，沒有放寬斷言：
  - `qIconSkills.test.ts` 的數量：效果 51 → 54。效果碼總數仍是 58，因為圖 +3、暫代 −3。
  - `qIconQi2d.test.ts` 的 `ADDED_PARTS`：加三個效果。它們是基準錄好之後才加的部件，沒有開工前的雜湊；LW-1、KW 這幾段也是這樣處理。

### 1.2～1.4 三種演出（移植需求第 2～4 項）
- **描述**（`battle/sk2Fx.ts`，純函式）：輸入是這一步的事件、前後的畫面和技能卡，輸出 `Sk2Fx[]`。
  - 吸收表面：讀 `surface_absorbed`。
  - 疾病擴散：讀 `disease_spread`。範圍格照引擎量距離的方式算：單位距離，量到最近佔格，1～`CONTAGION_RADIUS` 格；巨型單位是外圍一圈。被選中的是被傳染的人佔的格中，離倒下的人最近的那一格。
  - 鉤：技能卡帶 `hook` 原語時，讀 `skill_used` 之後的強制位移、`push_resisted`、`collided`。分三種：
    - `pull`：一般拉回。
    - `brake`：有移動、停下時和施放者不相鄰、沒有撞擊。這就是引擎的 `stop_before_deadly`，前面那一格當作熔岩。
    - `immovable`：沒移動，而且推不動。
- **接到播放**（`playback.stepSkill` → `StepVfx.sk2`）：
  - 時間不縮放，由繪製器乘播放速度的倍率。
  - 擴散從倒下的人的倒下片段開始。
  - 鉤記錄要換成鎖鏈的那一段特效（`castIndex`）、拉的開始時間（`leadMs`）和出招後位移的總長。
- **繪製**：
  - `render/sk2Effects.ts`：每個演出一張只框住用到範圍的離屏 canvas，每一格重畫後更新貼圖。
    - 單位之上的放效果層。
    - 單位之下的照排切段，掛在各排的表面裝飾層，重畫時會再掛回去。這兩樣是吸收表面的光柱、擴散的範圍格與地上的 V。
  - `render/sk2FxArt.ts`：時間軸與畫法照樣張的 `sceneAbsorb`／`sceneContagion`／`sceneHook` 與第 2 版的可修 1、4、5、7。
  - `vfxLayer.playVfx`：鉤的那一段一般特效（光束）不播，改畫鎖鏈。減少動態時不播 SK-2 演出。
- **吸收表面的表面收縮**：用 `surfaceAnim` 的消失動畫（`SurfaceAnimator.absorbNow`），在演出的 150 ms 就讓那一格往中心收縮，不等這一步重畫。
  - 做法：下面墊一張沒有表面的地形貼圖，上面疊舊的樣子，用縮小的圓遮住。
  - 這一步重畫時，同一個變化接著播，不重播。
- **鉤**：
  - 鏈子起點是 `playSkill` 給的作用端，也就是 `yank` 的副手。
  - 被拉的人照實際的單位節點位置走，鏈子跟著變短。
  - 熔岩前煞住：塵土 ×1.5、往熔岩方向的兩道拖痕、熔岩火舌、火星，鏈子垂下再收回。
  - 巨型頭目：鏈子繃直、微抖、白光加亮邊，受鉤點往施放者那一側放射 4 道緊繃線，之後鉤脫開、鏈子成波浪彈回，加撞擊星。

### 1.5 畫面下限（移植需求第 5 項）
- `sk2FxArt.chainMinK(地圖縮放)`。效果建立時讀繪製器的地圖縮放：1600 寬（1.31）時 K＝1.00，800 寬（0.53）時 K＝1.35。
- 乘 K 的部分：鏈節長、間距、外框粗線、鉤頭、擴散的虛線寬與間隔、末端箭頭、地上三個 V。
- 測試 `render/arSk2Art.test.ts`。

### 1.6 「會擴散」記號與用字（移植需求第 6 項、第 2 節）
- **記號**：`render/spreadMark.ts` 逐行搬 B 案（框頂右段正上方一顆孢子，加一顆往右上跳的小點，全部在框線外面）。用哪一種排法看畫面上的框邊長，小於 14 px 用頭頂的排法。
- **戰場狀態列**（`unitSprite.statusRow`）：帶 `contagious` 的狀態在圖示上疊一張記號貼圖，四周各留 7 px。記號排在「+N」膠囊之前，所以膠囊畫在上面、不會被蓋到。
- **HUD 狀態卡 20**（`StatusBadge`）：另疊一張 36 px 的 canvas（`.stat-spread`，絕對定位、四周多 8 px、不擋滑鼠），往上凸出約 7 px。
- **型別**：`api/types.ts` 的 `StatusView` 加選填 `contagious`；`drawModel` 帶 `spreadIds`。沒有會擴散的狀態時不多這個鍵，既有快照不變。
- **用字**：照移植需求第 2 節。
  - 狀態卡名稱後面加標籤「會擴散」（`PartTip` 新增選填 `tags`）。
  - 說明多一行，用需求表上的原句。
  - 浮字：`contagion_marked` 與 `disease_spread` 都改成「擴散」，`WORD_CONTAGIOUS`（「會傳染」）拿掉。依據是交接 4.1.28 第 6 點的「發生時的浮字統一成『擴散』」。

## 2. 逐項對照移植需求

| # | 需求 | 狀態 | 截圖 |
|---|---|---|---|
| 1 | 拿掉三筆暫借、`EFFECT` 加三個圖樣、30／26／18 縮放、病菌黃綠進 `palette.ts` | 完成 | `1-icons.png` |
| 2 | 吸收表面：表面沿用消失動畫往中心收縮＋冰晶；光柱分單位下、上兩層；頭頂浮起收益圖樣 | 完成（差異見第 5 節第 1 點） | `2-anim-absorb.jpg` |
| 3 | 疾病擴散：候選格亮起、弧線、虛線軌跡、箭頭、地上的 V；範圍照引擎量距離 | 完成（差異見第 5 節第 2 點） | `3-anim-contagion.jpg` |
| 4 | 鉤三種；鏈子起點在副手 | 完成（差異見第 5 節第 3 點） | `4-anim-hook.jpg`、`5-anim-hook-lava.jpg`、`6-anim-hook-giant.jpg` |
| 5 | K＝max(1, 3 ÷ (4.2 × 地圖縮放))；鏈節、間距、外框、鉤頭、擴散虛線與 V 乘 K | 完成 | `7-hook-800-true1x.png`、`8-contagion-800-true1x.png` |
| 6 | B 案記號、條件 `contagious`、前端型別選填欄位、不裁切、「+N」膠囊不被蓋 | 前端完成；後端還沒輸出這個欄位（待決 1） | `9-status-field-1600-800.png`、`10-status-card.png` |

## 3. 截圖（`docs/art/shots/ar-sk2/`，10 張）

無頭 Chrome 的參數：`--headless=new --mute-audio --remote-debugging-address=127.0.0.1 --force-device-scale-factor=1`，CDP `deviceScaleFactor 1`，量到 `devicePixelRatio = 1`，網址帶 `mute=1`。用的埠：vite `127.0.0.1:5293`、除錯埠 9741，開之前兩個都沒人用。結束時只停了自己起的 vite 與 Chrome，兩個埠都已沒在聽。截圖腳本放在暫存區，沒有 commit。

| 檔案 | 內容 |
|---|---|
| `1-icons.png` | 三個部件的組裝列 30／26／18（2 倍）＋真 1 倍 ×6 最近鄰＋18 的 2 倍 ×4 |
| `2-anim-absorb.jpg` | 吸收表面關鍵影格 100～900 ms：冰面收縮、冰晶螺旋、光球、頭頂冰晶、杖頭染色 |
| `3-anim-contagion.jpg` | 疾病擴散 1100～1700 ms：範圍格（被選中那格加框）、火團沿弧線跳到盜賊2、虛線軌跡、箭頭、著火 |
| `4-anim-hook.jpg` | 鉤（一般）：射出、鉤住、拉回 3 格、收回 |
| `5-anim-hook-lava.jpg` | 鉤（熔岩前煞住）：鏈子跨過熔岩、煞住的塵土與拖痕、熔岩火舌、鏈子垂下 |
| `6-anim-hook-giant.jpg` | 鉤（巨型頭目拉不動）：繃緊、頭目白閃、鉤脫開彈回、撞擊星 |
| `7-hook-800-true1x.png` | 800 寬真 1 倍的鎖鏈（K 1.35） |
| `8-contagion-800-true1x.png` | 800 寬真 1 倍的擴散虛線、V、箭頭 |
| `9-status-field-1600-800.png` | 戰場狀態列 1600、800 真 1 倍。上排由左到右是燃燒擴散、燃燒、流血擴散、流血、中毒擴散、中毒；下排一個帶 4 種的（800 寬是精簡列加「+N」膠囊）。附狀態列 ×5／×8 最近鄰 |
| `10-status-card.png` | HUD 狀態卡 20（一般和會擴散並排）、點開第一個會擴散燃燒的說明卡（標籤「會擴散」加說明一行）、真 1 倍 ×8 最近鄰 |

重拍方式：
- 開發頁 `client/dev/arsk2-gallery.html?part=icons|field|card`。
- 演出用 `client/dev/sk2-gallery.html?case=<案例>&strip=<毫秒,…>&scale=0.9`，真 1 倍改帶 `&w=800`。

### 實機未看
- 真人戰鬥裡沒有招用到這三個原語，因為接進出題是 SK-2b 的範圍。所以演出只在開發頁用真引擎事件看過。
- 後端還沒輸出 `contagious`，實機的狀態列與狀態卡看不到記號，截圖是開發頁的假資料。
- 演出開發頁的事件夾具沒帶 `contagious`，所以 `3-anim-contagion.jpg` 裡盜賊2 的新燃燒沒有記號。
- 浮動卡巡檢（滑進卡片、卡內捲到底、釘住、關閉，1600×900 與 800×600）沒做，只拍了點開的說明卡。

## 4. 測試與檢查

| 檢查 | 結束碼 |
|---|---|
| `corepack pnpm -C client exec tsc --noEmit` | 0 |
| `vitest run`（全部，376 檔、4706 個） | 0 |
| `corepack pnpm -C client build` | 0 |
| 新增測試：`battle/arSk2Fx.test.ts`（8）、`render/arSk2Art.test.ts`（2）、`render/arSk2SpreadMark.test.ts`（5） | 0 |

開發中另外分次跑過 `src/render`、`src/battle`、`src/ui`、`src/screens`，都是 0。沒有改 Python，所以沒跑 ruff、mypy、pytest。

## 5. 和樣張不同、或沒做到的地方

1. **吸收表面**：
   - 單位與表面用遊戲端現行的畫法。
   - 副手位置用施放者格子中心推估（往背後 4、往上 4），沒有讀紙娃娃的手；杖頭用 `playSkill` 的作用端。
   - 樣張裡施放者的姿勢沒做，身體照 `skillClips` 的 `press_clear`。
   - 如果這一步在收縮播完前就重畫（例如沒有飛行物的招），表面會直接消失。
2. **疾病擴散**：
   - 倒下用現行的倒下片段。
   - 樣張裡「倒下時狀態列燃燒圖示外圈的虛線環脈動」沒做，因為狀態列在單位節點內部，效果層不知道它的位置。
   - 傳過去的狀態圖示是重畫時直接出現，沒有「從 1.6 倍縮回」。
   - 只有「這一步有技能特效」時才播。持續傷害在回合開始扣血倒下而擴散，沒有特效，只有浮字。
   - 範圍半徑在前端寫死成 1（`CONTAGION_RADIUS`，同 `core.yaml` 初值）。
3. **鉤**：
   - 巨型頭目的「左右晃 2.4」「法師被往前拖 3 px＋前傾」沒做，身體交給現行的受擊反應與 `yank` 片段。
   - 熔岩那一格用推算的（停下那格往施放者走一格），沒有讀地形。
   - 沒命中時不畫鎖鏈，只有「失手」的浮字。
4. **會擴散記號**：
   - 戰場一律用頭頂的排法，框 9 單位。地圖縮放 > 1.55 時畫面框邊長會超過 14 px，照美術規則應該換成狀態卡的排法，這裡沒換。
   - HUD 狀態卡往上凸出 7 px，可能壓到上方的版面，沒有做版面巡檢。

## 6. 新增 `# noqa`
沒有（沒改 Python）。

## 7. 待 PM 決定

1. **後端輸出 `contagious`**：前端已經收選填欄位，但 `engine/view.StatusView` 沒有這個欄位，實機看不到記號與標籤。
   - 建議的改法：加 `contagious: bool | None = None`，presenter 只在 True 時填，再重產 OpenAPI。
   - 這樣每個狀態的 JSON 會多一個 `null`，會動到 OpenAPI 快照，也可能動到 CLI 與紀錄快照。
   - 屬於引擎與 API 的改動，照保守做法沒做，要排一段做。
2. **給美術 PM：距離條件的暫代圖**：貼身借「夾擊」、遠距借「目標落單」。要專屬圖樣請美術出圖。
3. **給美術 PM：驗收第 5 節列的差異**：需要的話改樣張或另開一段補。
   - 擴散狀態列的虛線環脈動。
   - 狀態圖示從 1.6 倍縮回。
   - 巨型頭目晃動與法師前傾。
   - 吸收表面的副手是推估位置。
4. **原語說明還寫「會傳染」**（玩法 PM）：`content/skill_primitives.yaml` 的 `llm_hint`／`player_description`、`content/workshop_text.yaml`、名詞表 `glossary.json` 的 `contagion` 說明。
   - 這些是內容與 LLM 提示，SK-2b 也在改相關的部分，這次沒動。
   - 另外說明裡寫「傳給身邊的一個敵人」，和定案句「一名同伴」不一致。
5. **吸收表面部件照技能的表面染色**：目前一律水色（美術 5.1 第 2 點交給開發決定），要不要照 `surface:<id>` 染色。
6. **戰場記號的排法門檻**：地圖縮放超過約 1.55 時，要不要照畫面框邊長換成狀態卡的排法（第 5 節第 4 點）。

## 開發 PM 裁定（2026-11-19）

- **驗收通過，合併。** 只改前端，tsc、vitest（全部 4706 個）、build 都是 0。第 0 項用 `COND_ALIAS` 明確退回，沒改斷言。兩份「新增部件要跟著更新」的清單（效果圖數 51 → 54、`ADDED_PARTS`）是照需求新增部件，不算放寬，接受。美術截圖由美術 PM 驗收。
- 待決 1（後端輸出 `contagious`）、4（content、工坊、名詞表還寫「會傳染」「傳給敵人」，和定案句不一致）：併進 SK-3b。字照美術需求和玩法定案句改。
- 待決 2、3、5、6（距離條件的專屬圖樣、演出和樣張的差異、吸收圖樣染色、縮放後的記號排法）：轉美術 PM。
