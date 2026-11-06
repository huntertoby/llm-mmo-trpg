# Phase 6F-6 報告：戰鬥介面小修

> 2026-11-05，實作者（agent）。worktree 分支，沒有 push，也沒有合併。基準是 main `2b92b4b1`。
> 範圍：巡檢（`docs/phases/Phase6實機巡檢.md`）的 bug 8、9、11、13、14、16，加上 6V-2b 檢查第 3 節第 1 點（半沉渡船）。
> **只改 `client/`**：沒有改規則、內容檔、Python。沒碰人物繪製（inkDoll、inkStyle、portrait）、`src/trpg/llm`、`content/llm`、
> world 的閃現與劇情技能，也沒碰首頁、建角頁、主角卡、遇敵卡、設定面板、浮動說明卡、`PopupFrame`。沒有新增相依套件。
> 沒有新增原生 `title=`、`Math.random`。

## 1. 逐項

| # | 項目 | 做了什麼 | 截圖 |
|---|---|---|---|
| 1 | 浮動字重疊（bug 8） | **原因有三個**：<br>① 每一步各自從第 0 個算位置，陷阱夾住那一拍和接著的傷害那一步會疊在同一個高度；<br>② 一般字約 28 px 高，舊的間距只有 22 px；後出現的字比較晚開始飄，先出現的字往上追；<br>③ 第一排的人頭頂沒有空間時，每個字都被壓到同一個高度。<br>**做法**（新的 `render/floatStack.ts`，純函式）：<br>- 同一格的字照**實際高度**累加，字距 2 px；<br>- 同一格前幾步的字還沒播完時，新的一組接在舊的上面，再多留一段飄的距離（22 px）；<br>- 同一組的字**一起飄**，只有「彈一下」照各自的延遲；<br>- 頭頂上方放不下時，**整組一起往下推**，讓最上面那個字剛好在上限。順序、間距都不變，下面的字可能蓋到身體。這和 6N-7「寧可蓋到身體也不切掉字」的取捨一致。<br>狀態字（＋倒地）一起排。格子上的光環照舊。 | `6f6_01_float_before/after` |
| 2 | 「閃避／失手」用語（bug 9） | 6N-6 的規則（能動的寫閃避；冰凍、暈眩、倒地、定身寫失手）**浮動字、閃避片段都已經照做**。逐處檢查後，只剩一個漏洞：**只看步後的畫面**判斷能不能動，所以有兩種情況會判錯：<br>- 同一步先沒打中，後面才被凍住：寫成「失手」，應該是閃避；<br>- 同一步先站起來，後面才沒打中：反過來判錯。<br>**做法**：新的 `feedback.immobilityOf`。從步前的畫面開始，照事件順序套上 `status_applied`、`status_removed`、`status_converted`，用事件的 `seq` 查「打的那一刻」。<br>浮動字（`feedbackFor`）和閃避片段（`vfxFor`）都改用它。正式播放（`playback.ts`）會傳步前畫面；沒傳的呼叫端照舊看步後畫面。<br>**戰鬥紀錄照舊**：伺服器寫「失手」，這段沒改。<br>其他寫「閃避」「失手」的地方也都看過了：技能預覽的「失手反噬」是規則用語，開發頁的字只是標籤，都不受影響。 | `6f6_02_miss_before/after` |
| 3 | 技能列截斷（bug 11） | - **按鈕固定寬 184 px**：原本 78～190 px 看字長，冷卻時代價只剩「冷卻 2」，按鈕變窄，後面的按鈕往前跳。<br>- **第二行（代價）**：每段（AP、法力、冷卻）不拆開，段與段之間可以換行，最多兩行，字級 11 px。「・」接在前一段後面，所以新的一行不會以「・」開頭。<br>- **技能名**：超過 6 個字改成 12 px；超過 9 個字改成 11 px、最多兩行，代價收成一行。<br>只改技能列本身（`SkillBar.tsx` 的技能鈕、`skill-bar.css`），沒動主角卡和外框。<br>1040 寬時每排從 4 顆變 3 顆，高度一樣是兩排（6 招）。 | `6f6_03_skillbar_1040_*`、`6f6_04_skillbar_800_*`、`6f6_05_skillbar_longname_*` |
| 4 | 範圍技畫到地圖外（bug 13） | **原因**：聖光的爆發從格子中心往上畫 1.3 格的光柱，第一排會畫進畫布上方給頭頂預留的那一條，也就是深色邊。<br>**做法**（新的 `render/mapClip.ts`）：<br>- **地上的特效裁在地圖矩形內**：範圍每格的爆發（含光柱）、扇形、落在目標格的片段特效（光柱、地上的法陣）。<br>&nbsp;&nbsp;- 特效標 `clip: "map"`，放進用遮罩裁切的 `groundFx` 圖層；<br>&nbsp;&nbsp;- 矩形的上緣是第一排最高那格的頂面，平地是 0。<br>- **跟著人的特效不裁**：蓄力、刀光、飛行物、受擊、浮動字。所以第一排的人頭頂照舊看得到。<br>- **範圍預覽只畫地圖內的格子**（`clipHighlights`）：移動、目標、影響範圍、施放範圍、方向、選好的物件、環境預告。 | `6f6_06_aoe_clip_before/after` |
| 5 | 敵人屍體的復活愛心（bug 14） | `drawModel.showsRevivable`：伺服器的 `revivable` 不分陣營，畫面只在**主角那一邊**的倒地者畫愛心和虛線圈。<br>敵人和第三方倒地時畫成「救不回來」：灰色墓碑、去色。<br>主角不在畫面資料時，當作 `ally`（同 `playback.ts`）。 | `6f6_07_heart_before/after` |
| 6 | 鐵砧遮擋（bug 16） | **在現在的 main 上重現不出來**：<br>- 主角站在鐵砧南邊 (4,3)：主角蓋住鐵砧；<br>- 站在北邊 (4,1)：被鐵砧擋住下半身；<br>- 站在東邊同一排 (5,2)：主角在前面。<br>這三種都已經是 6V-4b 的 y 排序，因為家具本來就放在所在排的物件層。巡檢是在舊版 `80d674c1` 看到的，那時鐵匠鋪的版面也不一樣（石師傅的位置不同）。<br>**這段做的**：把「物件和家具放進所在排的物件層」抽成 `sceneryLayer.objectLayerOf`，戰場改用它，並加測試鎖住順序（同 6V-4b 的裝飾）。<br>補拍了霧渡鎮鐵匠鋪：正式建角 → 傳送到雲嶺 → 正式的 walk 走進石記鐵鋪 → 重新載入正式畫面。<br>「按 E 沒有打造面板」屬於規則或功能，沒做（見待決 3）。 | `6f6_08_smithy`、`6f6_08_smithy_south/north/east_zoom` |
| 7 | 半沉渡船的木箱 | 新的 `render/submerged.ts`：物件站在畫成深水的深淵格（`look.chasm_style: deep_water`）上時：<br>- 水線（格子 60% 高）以上照常；<br>- 水線以下半透明（45%），並染上深水的底色 #34495c；<br>- 再畫一條淡藍水線加兩個小波紋。<br>只改畫法：地形仍是 chasm，物件、規則都沒動。目前只有灰渡口的 (2,7)、(3,7) 兩個 crate 符合。 | `6f6_09_ferry_before/after`、`6f6_09_ferry_after_full` |
| 8 | 巡檢清單其他低嚴重度的戰鬥介面項目 | - bug 7（勝利面板的重播指令）、bug 10（重新載入後跳「敵方先手」）：6F-3 已經修好（只在 `?dev=1` 顯示、只在第 1 輪跳出），實機確認過，這段沒再改。<br>- bug 11 的後半（冷卻時按鈕變窄、後面的往前跳）：在第 3 項一起修了。<br>- 其他項目不是戰鬥介面，或在別段的範圍內，沒碰：<br>&nbsp;&nbsp;- 12（主城沒有 NPC，屬於內容）；<br>&nbsp;&nbsp;- 15（設定齒輪，AU-1／UI-E1b）；<br>&nbsp;&nbsp;- 17（傳聞內容）；<br>&nbsp;&nbsp;- 18（大世界圖的說明框，浮動卡屬於 UI-E1b）。 | — |

## 2. 截圖（`docs/art/6f6_*`，23 張，全部靜音）

- **靜音**：無頭 Chrome 加 `--mute-audio`，網址加 `?mute=1`。
- **「前」的截圖**怎麼拍：
  - 實機畫面：把 `2b92b4b1` 建置的 `client/dist` 暫時換回去拍，拍完再換回來；
  - 開發頁：把 6 個改過的原始檔暫時 checkout 回 `2b92b4b1` 拍，拍完 `git checkout HEAD` 還原。

| 檔案 | 內容 | 來源 |
|---|---|---|
| `6f6_01_float_before/after` | 左：陷阱夾住那一步「暴擊 −9／擊倒／＋倒地」；右：「＋11盾」後接下一步的「閃避」。前：三行壓在一起、盾和閃避疊住。後：一行一行錯開 | 開發頁 `fix6f6-gallery.html` 場景 1（正式的 playbackPlan → frameOps → BattleRenderer） |
| `6f6_02_miss_before/after` | 左：同一步先沒打中、後面才被凍住；右：本來就暈眩。前：兩個都寫「失手」。後：左「閃避」、右「失手」 | 開發頁場景 2 |
| `6f6_03_skillbar_1040_before/after`（＋`_after_full`） | 1040×624，陷阱流放完捕獸夾（冷卻 2）。前：「AP 2・法力 6・冷卻 3 …」被截斷，冷卻中的捕獸夾變窄。後：代價兩行、按鈕同寬 | 實機（開始畫面的正式開戰，`hero_build=build_trapper`；真的點技能、點格子） |
| `6f6_04_skillbar_800_before/after`（＋`_after_full`） | 800×600 同上 | 實機 |
| `6f6_05_skillbar_longname_before/after` | 800×600。用技能工坊「裝上試玩」的自訂技能欄位放兩個長名字（8 字、12 字）。後：8 字縮一號，12 字兩行 | 實機（`custom_skills`） |
| `6f6_06_aoe_clip_before/after` | 聖光爆發（方陣）打在地圖左上角，橘色是範圍預覽（含地圖外的格子）。前：光柱畫到地圖上方的深色邊。後：裁在地圖內 | 開發頁場景 3 |
| `6f6_07_heart_before/after` | 倒地的隊友和倒地的敵人，伺服器的 revivable 都是真。前：兩個都有綠色愛心。後：敵人是灰色墓碑 | 開發頁場景 4 |
| `6f6_08_smithy`、`_south_zoom`、`_north_zoom`、`_east_zoom` | 霧渡鎮石記鐵鋪，主角在鐵砧的南、北、東 | 實機（正式建角、傳送、walk，重新載入正式畫面；開場對話框按「知道了」關掉） |
| `6f6_09_ferry_before/after`（＋`_after_full`） | 灰渡口的半沉渡船：兩個木箱。前：乾木箱浮在深水上。後：有水線，水線以下半透明、帶水色 | 實機（另一個 `TRPG_SEASON_START=2026-10-25` 的世界，埠 8389；從霧渡鎮正式 walk 過渡口） |

**開發頁**：新的 `client/fix6f6-gallery.html`、`src/dev/fix6f6Gallery.ts`。

- 實機很難湊出的固定狀態放在這裡：同一格好幾個字、同一步先沒打中才被凍住、角落的範圍技、敵方屍體 revivable 為真。
- 全部走正式的播放流程和繪製器。
- 和其他開發頁一樣不進正式 build：`pnpm dev` 後開 `/fix6f6-gallery.html`。

## 3. 檔案清單

- **新增**：
  - `client/src/render/floatStack.ts`
  - `client/src/render/mapClip.ts`
  - `client/src/render/submerged.ts`
  - `client/src/dev/fix6f6Gallery.ts`、`client/fix6f6-gallery.html`
- **修改**：
  - `client/src/render/BattleRenderer.ts`：浮動字排版、`groundFx` 遮罩、範圍預覽裁切、半沉物件、`objectLayerOf`
  - `client/src/render/vfxEffects.ts`：爆發、扇形標 `clip: "map"`
  - `client/src/render/sceneryLayer.ts`：`objectLayerOf`
  - `client/src/battle/feedback.ts`：`immobilityOf`、`immobilityIn`
  - `client/src/battle/vfx.ts`、`client/src/battle/playback.ts`：傳打的那一刻
  - `client/src/battle/drawModel.ts`：`showsRevivable`
  - `client/src/ui/SkillBar.tsx`：`costParts`、`skillNameClass`、代價分段
  - `client/src/styles/skill-bar.css`
- **測試（新增）**：
  - `client/src/battle/fix6f6.test.ts`（15 項）：
    - 浮動字錯開：照高度累加、陷阱夾住三行不重疊、下一步接在上面、同組一起飄、頭頂放不下時整組往下推；
    - 閃避／失手：同步驟凍住寫閃避、暈眩寫失手、先站起來寫閃避、停頓已跳過的事件仍算進去、沒有步前畫面照舊；
    - 愛心的顯示條件：我方有，敵方和第三方沒有，跟著主角的陣營；
    - 範圍裁切：預覽裁切、裁切矩形、哪些特效標 `map`。
  - `client/src/ui/skillBar6f6.test.ts`（4 項）：代價分段、長名字的 class、SSR 輸出、CSS 固定寬與兩行上限。
  - `client/src/world/fix6f6world.test.ts`（5 項）：
    - y 排序：鐵砧在所在排的物件層、畫布兩格高；南、同排的人後畫，北邊的人先畫；
    - 灰渡口兩個 crate 在深水上、岸上的廢鐵堆不算、預設深淵不算、水線位置。
- **commit**（worktree 分支 `worktree-agent-ab176d9d6ab5758a3`）：
  - `3271a43e` 浮動字錯開
  - `e4ed8dcd` 閃避／失手照打的那一刻
  - `e943d794` 愛心只在我方＋測試
  - `a3b8350a` 範圍裁切
  - `0c1f7862` 技能列
  - 測試的 node:fs 動態載入
  - `4a3bb7f8` 鐵砧 y 排序＋渡船水線
  - `eaafcdcf` 整組往下推＋開發頁
  - 報告與截圖

## 4. 測試與檢查

- **新增 vitest**：24 項（15＋4＋5）。
- **client 全部 vitest**（交件前跑一次）：**240 檔、2660 項通過**，結束碼 0。
- **`corepack pnpm -C client build`**：結束碼 0（含 `tsc --noEmit`）。
- **排版煙霧檢查**：
  - 做法：`/?dev=1&anim=0.1`，先 `localStorage.clear()`，再跑 `__layoutSmoke.runCase`。伺服器帶 `TRPG_DEV_ROUTES=1`，埠 8388。
  - 結果：1600×900、1040×624、800×600 三種尺寸**全 PASS**，每種 9 項，共 27 項。
- **6.5.1 浮動卡**：這段沒有新增彈出層，也沒動浮動卡。技能卡的滑過、釘住由煙霧檢查的「浮動卡有底色」「更多動作選單」兩項涵蓋，都 PASS。
- **程序**：
  - 伺服器 8388、8389，Chrome（CDP 9488），vite 5391，都是自己啟動、用 PID 或工作 ID 結束；
  - 5388 已經被別的程序佔用，所以 vite 改用 5391；
  - 沒碰 `tmp_x`、`saves/`。存檔放在 `scratchpad/f6/saves`、`saves2`。

## 5. 待 PM 決定

1. **鐵砧遮擋（bug 16）重現不出來**：南、北、東三個位置的截圖都正確。如果美術 PM 看到的是別的情況（例如走路途中某一格），請附位置。這段只加了測試鎖住順序。
2. **單位資訊卡的「倒下・可復活」字樣**（`ui/UnitInfo.tsx`）：敵人倒地時仍會這樣寫，因為伺服器的 `revivable` 不分陣營。這張卡屬於浮動說明卡，是 UI-E1b 正在改的範圍，所以沒動。建議 UI-E1b 合併後順手改成 `showsRevivable`（一行）。
3. **鐵匠鋪按 E 沒有打造面板**（bug 16 後半）：屬於功能（打造入口），不是畫法，沒做。
4. **頭頂放不下時整組往下推**：最上面幾排的人，底下的字（通常是傷害數字）會蓋到身體。原型做法照 6N-7 的取捨。如果美術希望改成往左右分開，要另外定排法。
5. **技能鈕固定 184 px**：1040 寬時每排從 4 顆變 3 顆。6 招以內高度不變；8 招以上會多一排。這是原型數值，PM 可以再調，例如改成 172 px 讓 1040 寬時一排 4 顆。
6. **半沉的判斷**：只看「深淵格＋`chasm_style: deep_water`」。之後如果淺水或沼澤上也有半沉的物件，要另外加資料欄位（例如物件的 `look: sunken`），屬於內容格式，這段沒做。
