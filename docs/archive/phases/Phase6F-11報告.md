# Phase 6F-11 報告：6F-10b 驗收的補修（800 寬召喚物標記、最上排飄字、一般單位「+N」、徽章數字、世界畫面黏字）

實作者，2026-11-05。分支 `worktree-agent-a75be397fd6c53834`，從 main `28968815` 開始（含 6F-10b 與 `docs/archive/art/6F-10b檢查.md`）。沒有 push，也沒有合併。

**範圍**：只改 `client/`，只改外觀與顯示。
- 沒碰：skillgen、內容、人物繪製。
- 沒有新增相依套件、原生 `title=`、`Math.random`。

**依據**：`docs/archive/art/6F-10b檢查.md`「下一段要修」1～3。

**截圖方式**（同 6F-10b）
- 無頭 Chrome（`--mute-audio`，網址加 `?mute=1`），用 `Emulation.setDeviceMetricsOverride` 把視窗真的設成檔名上的尺寸（device scale 1）。
- **全圖和放大圖是同一幀**：每組只拍一次全畫面 PNG，`_zoom` 是在頁面裡用 canvas 從同一張圖裁出來、最近鄰放大。
- 實機量到的地圖縮放（開闊平原）：1600×900 是 127.5%、1040×624 是 79.6%、800×600 是 64.6%。
- 戰鬥畫面都是正式畫面。狀態是攔下戰鬥 API 的回應補上去的（守護、強化、虛弱共 3 個），做法和 6F-10b 一樣：
  - 召喚物：只補召喚物；
  - 一般單位：開戰前就攔，補給所有沒有狀態的單位。
- 世界畫面是正式畫面（新建角色、在主城、先關掉開場對話框）。
  - 任務和線頭：新角色沒有，所以攔下 API 回應各補 1 筆（「霧渡鎮的委託」「蘆葦地裡的爪痕」）。右下角任務追蹤也會出現這一筆。
  - 公告板的賽季 Boss、聯賽：用真的資料。

---

## 1. 800 寬（縮放 ≤ 70%）的召喚物標記

做法（純函式在新檔 `render/rowLayout.ts`，由 `unitSprite.ts` 接上）：

**狀態列**
- 縮放 ≤ 70% 時（`isCompactRow`）只顯示 1 個圖示，後面接「+N」，N ＝ 狀態總數 − 1。
- 「+N」是一般大小的字，不是角標：
  - 粗體白字加深色描邊；
  - 字級 9 × 反向放大倍率，畫面上和圖示的圖案一樣是 10px；
  - 放在圖示右邊，中間留空隙，不蓋圖示。
- 召喚物的狀態列靠左，把右上角讓給徽章。

**回合數徽章**
- 徽章自己也是「最小尺寸標記」（`registerMark`，數字畫面上至少 10px，見第 4 項）。
  - 800 寬時放大 1.55 倍，畫面上的半徑是 7.0px。
- 數字改成粗體加深色描邊（`SUMMON_BADGE_STROKE` 3）。
- 放不下原位時，徽章放在格子右上角（`summonBadgeCorner`）：
  - 整顆（含外框線）離格子邊緣 1.5px；
  - 不壓格線、不跨進隔壁格（6F-10b 是壓出右緣 3px）。
- 「+N」字的筆畫下緣比圖示下緣低 0.9（`ROW_PLUS_DROP`），和徽章至少留 1px。

**截圖**（覆蓋舊檔）
- `6f10b_summon_800`、`6f10b_summon_800_zoom`：
  - 狀態列是 1 個圖示加「+2」，「+2」不蓋圖示；
  - 徽章「3」讀得出來，整顆在格子裡。
- `6f10b_summon_800_panel_zoom` 也從同一幀重裁。內容和舊檔一樣，所以 git 沒有變更。
- 另外補拍：
  - `6f11_1_summon_1040`、`_zoom`：見待決 1；
  - `6f11_1_summon_1600`、`_zoom`：1600 寬照舊，只有數字多了描邊。

## 2. 最上排的飄字

- **頭頂空間的上限再往下 7px**（`FLOAT_TOP_SHIFT_PX`，畫面 px）。換成世界座標是 7 ÷ 縮放，所以 1600 寬和 800 寬在畫面上都是 7px。
- **另外加了一條規則**：
  - 一組字停住時如果已經在戰場上緣以內，飄到最高也不會超出上緣（`capRise`）；
  - 離上緣不到 2px 的字就不往上飄，只彈一下；
  - 停住時本來就在上緣外的（第一排的人頭上沒空間），照 6F-10 的規則，上界是畫布上緣。
- 原因：只往下推 7px 時，同一個「−7」在剛出現時是在上緣以內，但之後繼續往上飄，還是會飄到上緣外約 13px（實測連拍）。
- **截圖**（開闊平原、種子 1，主角在 (0,3) 撞到地圖邊緣兩次）：
  - `6f11_2_top_1600`、`_zoom`：四個字都在，「−7」在草地上緣以內。
  - `6f11_2_top_800`、`_zoom`：同上。
  - `6f11_2_top_1600_peak`、`_zoom` 和 `6f11_2_top_800_peak`、`_zoom`：飄到最高、快淡出時，「−7」仍在上緣以內。

## 3. 一般單位的「+N」

- **1600、1040 寬**：改成角標，和 6F-10b 召喚物的角標一樣（`SUMMON_MORE_R` 4）。
  - 角標接在第 2 個圖示右上角外側，放得下時完全不重疊（`moreDx` ＝ `SUMMON_MORE_DX_MAX`）。
  - 整排夾在格子裡（`fitRow`，和召喚物同一套讓步順序）。
- **800 寬**：照第 1 項，1 個圖示加一般大小的「+N」字，整組置中。
- **截圖**（三組放大的都是主角 (0,3)、戰士隊友 (1,2)、盜賊 (1,3)）：
  - `6f11_3_unit_1600`、`_zoom`：2 個圖示，「+1」角標在第 2 個圖示外面。
  - `6f11_3_unit_1040`、`_zoom`：同上。
  - `6f11_3_unit_800`、`_zoom`：1 個圖示加「+2」字。

## 4. 徽章數字至少 10px

- 召喚物回合數徽章的倍率 ＝ max(1, 10 ÷ (字級 10 × 縮放))（`summonBadgeScale`）。
- 數字在畫面上一律 ≥ 10px，半徑跟著 ≥ 7px：
  - 1600 寬：倍率 1，數字 12.8px；
  - 1040 寬：倍率 1.26，數字 10px；
  - 800 寬：倍率 1.55，數字 10px。
- 繪製器建立單位與改變縮放時，先套用徽章、再套用狀態列（`unitMarksOf`）。狀態列重排時會一起搬徽章。
- 重排的回呼多傳了地圖縮放（`Relayout = (k, boardScale)`），精簡列要用它判斷。
- **截圖**：第 1 項的 `6f10b_summon_800*`、`6f11_1_summon_1040*`、`6f11_1_summon_1600*`。

## 5. 世界畫面 6 處黏字

- 新增 `.lead-gap { margin-inline-start: 0.75em; }`（`styles/base.css`），間距和 6F-10b 的 `SummonTitle` 一樣是 0.75em。
- 6 處都把行首的全形空白拿掉，改成在那個 span 加上 `lead-gap`。實測 margin 是 9px。

| 位置 | 截圖 |
|---|---|
| `world/QuestLog.tsx` 28 行（任務名稱｜種類・委託人） | `6f11_5_quest_1600`、`_zoom` |
| `world/QuestLog.tsx` 56 行（線頭｜範圍・到期・NPC・地點） | `6f11_5_thread_1600`、`_zoom` |
| `world/WorldGrowth.tsx` 49 行（成長與技能｜Lv…） | `6f11_5_growth_1600`、`_zoom` |
| `world/LeaguePanel.tsx` 76 行（報名中｜賽季第 N 天…） | `6f11_5_league_1600`、`_zoom` |
| `world/BoardPanel.tsx` 154 行（碎晶之主｜封印中） | `6f11_5_board_1600`、`_zoom` |
| `run/FlashChooser.tsx` 86 行（閃現「點燃」｜第 1 次） | `6f11_5_flash_1600`、`_zoom`（開發入口 `/?dev=1&screen=flash`） |

- **原始碼掃描**（`fix6f11.test.ts`）：所有 `.tsx` 都不准有「縮排後第一個字是全形空白」的行。
  - 句子中間的全形空白 JSX 會保留，不在掃描範圍。

---

## 驗證

**排版煙霧檢查**
- 網址 `/?dev=1&anim=0.1&mute=1`，先 `localStorage.clear()` 再重新載入，跑 `__layoutSmoke.runCase('6F-11')`。伺服器帶 `TRPG_DEV_ROUTES=1`。
- 1600×900、1040×624、800×600 三個尺寸都是「全 PASS」，各 12 列。
- 主控台照舊有 React 的 `flushSync` 警告（`BattleScreen`，6F-10 就有，這次沒改）。

**6.5.1 浮動卡實測**（功能列「技能」鈕的說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓（707～821） | ✓（436～550） |
| 滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片 106px，沒有可捲的內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 關閉 | ✓ | ✓ |

截圖：`6f11_float_1600_pinned`、`6f11_float_800_pinned`。

**交件前的完整檢查**
- client 全部 vitest：**251 個檔、2851 項全過**，結束碼 0。
- `corepack pnpm -C client build`（含 `tsc --noEmit`）：結束碼 0。

**程序**
- 自己啟動的程序：
  - API 8359（`scratchpad/f11/serve.py`，用主資料夾 `.venv` 的 Python 跑 worktree 的 `src`，存檔在 `scratchpad/f11/saves`）
  - vite 5359（暫時設定 `client/vite.f11.config.mts`，沒有 commit，交件前刪除）
  - CDP 9591 的無頭 Chrome
  - 煙霧檢查自己啟、自己關的無頭 Chrome（9593）
- 結束時只用這些程序的 PID 關掉。
- 沒碰 8000、8001、8010、`tmp_x`、`saves/`。暫存都在 `scratchpad/f11/`，沒有 commit。

## 檔案清單

**新增**
- `client/src/render/rowLayout.ts`：狀態列與回合數徽章的排法（純函式）
  - 從 `unitSprite.ts` 搬來的常數與 `summonRowLayout`；
  - 新增 `isCompactRow`、`compactRow`、`unitRowLayout`、`fitRow`、`summonBadgeScale`、`summonBadgeCorner`、`summonBadgeAlone`；
  - 新增檢查重疊用的幾何工具 `rowShapes`、`rowSpan`、`circleHitsBox`、`circleHitsCircle`。
- `client/src/ui/fix6f11.test.ts`
- 截圖 `docs/art/6f11_*`，共 34 張：
  - 召喚物 4 張
  - 最上排飄字 8 張
  - 一般單位 6 張
  - 世界畫面黏字 12 張
  - 浮動卡 2 張
- 本報告

**覆蓋**
- `docs/art/shots/6f10b/6f10b_summon_800.jpg`、`6f10b_summon_800_zoom.jpg`
- `6f10b_summon_800_panel_zoom.jpg` 從同一幀重裁，內容沒變

**修改**
- `client/src/render/unitSprite.ts`：
  - `statusRow` 改用 `unitRowLayout`、`summonRowLayout`，新增精簡列「+N」字（`plusText`）、角標（`moreTag`）；
  - `summonBadge` 登記成標記、數字加描邊；
  - 搬走的常數照舊從這裡匯出。
- `client/src/render/minMark.ts`：`MIN_BADGE_FONT_PX`、`SUMMON_BADGE_LABEL`（從 unitSprite 搬來）、`Relayout` 多傳縮放、`unitMarksOf`
- `client/src/render/BattleRenderer.ts`：
  - `scaleUnitMarks`（徽章與狀態列一起套用）；
  - `floatRoom` 加 `floatTopShift`；
  - `capRise`、`groupRestTop`、`mapTopY`。
- `client/src/render/floatStack.ts`：`FLOAT_TOP_SHIFT_PX`、`floatTopShift`、`capRise`
- `client/src/styles/base.css`：`.lead-gap`
- `client/src/world/QuestLog.tsx`、`WorldGrowth.tsx`、`LeaguePanel.tsx`、`BoardPanel.tsx`、`client/src/run/FlashChooser.tsx`：行首全形空白 → `lead-gap`
- 舊測試跟著新規則改（舊規則被美術 PM 這次的決定取代）：
  - `client/src/ui/fix6f10.test.ts`：召喚物各縮放的檢查改成照實際縮放算徽章倍率與精簡列，用圓和方框檢查重疊；「放不下時」改看右上角。
  - `client/src/ui/fix6f10b.test.ts`：800 寬的角標、靠右緣壓出 3px 的檢查改成精簡列與右上角；接線字串跟著改。
  - `client/src/ui/fix6f9.test.ts`：接線改看 `scaleUnitMarks`。

## 測試數

`fix6f11.test.ts` 共 18 項：
- **第 1 項（7 項）**
  - 精簡列只在縮放 ≤ 70%；
  - 800 寬 1 個圖示加「+N」，字不蓋圖示、畫面上 ≥ 10px；
  - 800 寬徽章半徑 ≥ 7px、數字 ≥ 10px；
  - 800 寬徽章整顆在格子裡，和狀態列（含描邊）至少留 1px，狀態列在格子裡、在 HP 條之上；
  - 1600 寬照 6F-10b；
  - 1040 寬右上角、不重疊；
  - 有炸彈時也不重疊。
- **第 3 項（2 項）**
  - 1600、1040 角標完全在圖示外、整排在格子裡；
  - 800 精簡列置中。
- **第 4 項（3 項）**
  - 各縮放數字 ≥ 10px、半徑 ≥ 7px；
  - 徽章是標記、套用順序（徽章先）、重排拿得到縮放；
  - 接線。
- **第 5 項（2 項）**
  - 原始碼掃描：所有 `.tsx` 沒有行首全形空白；
  - 6 處都用 `lead-gap`，CSS 有規則。
- **原始碼掃描（1 項）**：這次動到的檔案不用 `Math.random`、不用原生 `title=`。
- **第 2 項（3 項）**
  - 7px 在三個尺寸都是畫面 7px；
  - `capRise` 的規則；
  - 接線。

`fix6f10.test.ts` 19 項、`fix6f10b.test.ts` 12 項、`fix6f9.test.ts`、浮動卡規則 `floatCardRule.test.ts` 全過。

## commit

- `62e9f9ab`：800 寬精簡狀態列、所有單位的「+N」角標、徽章數字至少 10px（第 1、3、4 項）
- `4fcef4be`：飄字的頭頂空間再往下 7px，停住時在上緣以內的不飄出去（第 2 項）
- `059ef94d`：世界畫面改用 `lead-gap`，加原始碼掃描（第 5 項）
- 最後是截圖與本報告

## 待 PM 決定

以下都照最保守的做法先做完了：

1. **1040 寬的召喚物**：徽章數字要 ≥ 10px，徽章放大 1.26 倍後原位會超出格子，所以也放到右上角。
   - 2 個狀態：照樣顯示 2 個圖示。
   - 3 個以上：「+N」角標會撞到右上角的徽章，所以改成和 800 寬一樣的 1 個圖示加「+2」字（`6f11_1_summon_1040_zoom`）。
   - 規格只寫了「一般單位 1040 用角標」，召喚物 1040 沒寫。
2. **徽章放在右上角，會蓋到骷髏頭部右邊和武器上端**（800、1040）。
   - 格子只有 31px（800 寬）。徽章直徑 14px、圖示 12px、「+N」字 10px，三樣同時在格子裡，就一定會蓋到身體某處。
   - 右上角是唯一能讓三樣不互相重疊、又不超出格子的位置。
3. **第 2 項多加了一條規則**（`capRise`）：停住時在戰場上緣以內的字不會飄出上緣，最上面那個字幾乎不往上飄，只彈一下。
   - 只往下推 7px 時，「−7」飄到最高還是會超出上緣約 13px。
   - 如果只要照字面往下 7px、照常往上飄，拿掉 `capRise` 這一行就可以。
4. **800 寬「+N」字的描邊下緣**比圖示下緣低約 2.6px（世界座標）。單位有護盾時，會蓋到護盾條上緣約 1px（沒有護盾時離 HP 條還有 0.7px）。
   - 原因：要讓字離右上角的徽章至少 1px。
5. **手動把地圖縮到 50%**：格子只剩 24px，徽章和狀態列疊不下，會有重疊；精簡列也可能超出格子左緣。
   - 測試只檢查到 60% 以上。
6. **召喚物身上有定時炸彈**（800、1040）：炸彈徽章本身沒有反向放大，可能和右上角的回合數徽章靠得很近。這次沒有實機拍到這個情況。
7. **1040 寬一般單位的「+1」角標**：字是 7 × 1.4 倍，畫面上約 7.8px，圓的半徑約 4.4px，比較小。
   - 這是 6F-10b 召喚物角標的大小，這次沒有放大。
8. **「徽章數字至少 10px」只套在召喚物回合數徽章**。炸彈、蓄力、灌注的徽章沒有改。
9. **`lead-gap` 用 0.75em**（約 9px），和 6F-10b 的 `SummonTitle` 一樣。原本的全形空白是 1em。
10. **1600 寬召喚物徽章的數字也多了深色描邊**。描邊的規則不分尺寸，所以 1600 寬的外觀也有小小的變化。
