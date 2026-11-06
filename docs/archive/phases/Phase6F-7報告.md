# Phase 6F-7 報告：美術 PM 驗收 UI-E1b 與 6F-6 的修正

> 2026-11-05，實作者（agent）。分支 `worktree-agent-af3ad387ef139c271`，基準是 main `14a2a3f7`（已含 UI-E1b、6F-6）。沒有 push，也沒有合併。
> 依據：美術 PM 的驗收紀錄 `docs/archive/art/UI-E1b與6F-6檢查.md`（分支 `claude/art-pm-8f4e6d` 的 commit `360f6984`）。
> **只改 `client/`**，只換外觀與顯示，規則、內容檔、Python、API 都沒動。
> 沒碰的範圍：人物繪製、`src/trpg/llm`、`content/llm`、白板與新手任務內容（6F-4c）、等待動畫（RT-3）、捲動區上下緣的漸隱（RT-3）。
> 沒有新增相依套件、原生 `title=`、`Math.random`。

## 1. 逐項

截圖都是視窗**真的設成**檔名寫的寬度後拍的，沒有裁切，也沒有放進大畫布。
- `_zoom` 是另外附的放大圖：同一個畫面只拍技能列或功能列那一塊，放大 1.6～2 倍。
- 實機畫面都是 API 8388 的正式 build。

| # | 項目 | 做了什麼 | 截圖 |
|---|---|---|---|
| 1（必修） | 技能長名的代價列 | 新增純函式 `ui/skillCost.ts`，先估寬度：中文 1em、半形 0.6em、空白 0.3em，每行可用 10.8em。<br>放不下時依序處理：<br>① 原樣放得下就不動；<br>② 放不下就把每段換成縮寫（「AP 2」→「AP2」、「法力 5」→「法5」、「冷卻 2 回合」→「冷2」，還有耐、源、HP、每場、傳說、代價、維持、反噬）；<br>③ 還是放不下，就從後面拿掉不是 AP、冷卻的段，最後一段加「…」。<br>**AP 與冷卻一定留著**。「・」只放在段與段之間，所以整行不會以「・」結尾。<br>名字兩行（`xlong`）時代價只有一行，其他照舊兩行。<br>結果：「灰燼與霜雪交織的鎖鏈陷阱」顯示「AP2・法5・冷2」；6F-6 已驗收的一般按鈕（兩行）不變。完整代價照舊在滑過的技能卡上。 | `6f7_01_skillbar_longname_1040`、`_1040_zoom`、`_800`、`_800_zoom`（對照 `6f6_05_skillbar_longname_after`） |
| 2（必修） | 重拍 3 張 | 開發頁 `story-gallery.html` 的舞台原本固定 1040×720，所以以前拍的不是真的 800 或 1600 版面。`#encounter`、`#reaction` 改成鋪滿視窗（`Stage fill`，100vw × 100vh），然後真的把視窗設成 800×600、1600×900 再拍。<br>拍的時候頁面寬度等於視窗寬度，飾件量測 `__corners()` 回空。 | 照原檔名覆蓋：`ue1b_09_encounter_800`、`ue1b_09_encounter_1600`、`ue1b_09_reaction_1600` |
| 3 | 戰鬥 800 寬 | **地圖往右讓**：自動填滿時，捲動區左右加內距，地圖在兩欄 HUD 中間置中。<br>&nbsp;&nbsp;- 讓開的寬度 ＝ 主角卡欄寬＋兩邊間距、戰況框欄寬＋兩邊間距（`stageLayout.hudSideInsets`，跟 CSS 的 `--hud-left-w`／`--hud-right-w` 一致，窄視窗時收窄，測試會比對）。<br>&nbsp;&nbsp;- 手動縮放時不讓。<br>&nbsp;&nbsp;- 800×600 實測：主角卡右緣 238，地圖 254～566，戰況框從約 582 起，沒有重疊。<br>**說明框**：<br>&nbsp;&nbsp;- 不再跟著底下的單位變淡（`hudFade` 拿掉 `mode` 這一塊），底色改成不透明的 `--ui-navy`；<br>&nbsp;&nbsp;- 寬度含內距與框，文字照框寬換行，「Esc」完整顯示（scrollWidth ＝ clientWidth ＝ 228）。 | `6f7_03_battle_800`（對照 `6f6_04_skillbar_800_after_full`）、`6f7_03_battle_1040`、`6f7_03_battle_1600` |
| 4 | 任務框標題 | 任務名最多兩行，超過兩行才加省略號（`-webkit-line-clamp: 2`）。框寬不變。 | `6f7_04_cloud_hud_1600`（「找頭上有「！」的渡婆婆／說話」兩行）、`6f7_04_cloud_hud_800` |
| 5 | 工具列 R 鈕 | 潛行圖示墊一個淺色月光圓底（`#d4dbef`，細框 `#8a94b8`）。圓底不超出原本圖形的範圍，所以功能列右上的飾件量測照舊通過。<br>停用時照舊灰階，不透明度 0.35 → 0.6。<br>在鐵匠鋪實測：功能列整條變淡（faded）、R 也是停用，仍然看得出是兜帽。 | `6f7_05_capital_hud_800`、`_1600`、`6f7_05_smithy_1280`、`6f7_05_smithy_bar_1280_zoom`、`6f7_05_smithy_800`、`_bar_800_zoom`、`6f7_05_smithy_1600` |
| 6 | 路線圖 | 節點圓改成 `position: relative; z-index: 1`，疊在連線上面。連線從上一個節點中心畫到這一個節點中心（`top: -50%; height: 100%`）。節點底色不透明，所以看得到的只有兩個圓之間那一段。 | `6f7_06_route_map_1600`、`_800` |
| 7 | 停用的「繼續」、紫色光環 | **「繼續」**：停用時不透明度 0.7（原本 base.css 是 0.45），字色 `#b4b4c6`。<br>**光環**：新增 `render/effectLayer.ts`，特效層由下到上是 `groundFx` → `floatRings` → `effects`。狀態光環改成一個獨立的特效，標 `layer: "under"`，放進浮動字下面那一層，「暴擊 −9」會蓋在光環上面。 | `6f7_07_home_no_char_800`、`_1600`；`6f7_07_float_ring_after`、`_after_b`（6F-6 開發頁場景 1，對照 `6f6_01_float_after`） |
| 8 | 千分比改百分比 | 只改顯示，內部照舊用千分比。共用 `battle/previewText.percent`：除以 10，整數不寫小數，否則四捨五入到一位小數（120 → 12%，125 → 12.5%）。<br>全站掃 `client/src` 給玩家看的「‰」，改了三處：<br>① 完整技能三選一的說明：「預算 +120‰」→「+12%」（`run/flash.ts`，新常數 `COMPLETE_BONUS_PERMILLE = 120`）；<br>② 技能工坊的複合加成公式：「× (1000 ＋ N‰) ÷ 1000」→「× (100% ＋ N%)」；<br>③ 戰場變奏的加價：改用同一個函式。<br>其他顯示（命中率、詞條、反應代價、Boss 階段等）本來就換成百分比了。 | `6f7_08_complete_offer_1600`、`_800` |

## 2. 檔案清單

- **新增**：
  - `client/src/ui/skillCost.ts`
  - `client/src/render/effectLayer.ts`
  - `client/src/ui/fix6f7.test.ts`
- **修改**：
  - 戰鬥：`ui/SkillBar.tsx`、`battle/stageLayout.ts`、`battle/hudFade.ts`、`screens/battle/useBoardViewport.ts`、`screens/BattleScreen.tsx`
  - 繪製：`render/BattleRenderer.ts`、`render/vfxEffects.ts`
  - 大世界與一輪：`world/HudBarIcons.tsx`、`run/flash.ts`、`run/flash.test.ts`、`screens/RunCompleteOffer.tsx`（只改註解）、`ui/workshop/CheckPanel.tsx`
  - 開發頁：`dev/storyGallery.tsx`
  - 樣式：`styles/battle-hud.css`、`styles/entry.css`、`styles/world-hud.css`
- **截圖**：
  - `docs/art/6f7_*`，22 張；
  - 覆蓋 `ue1b_09_encounter_800`、`ue1b_09_encounter_1600`、`ue1b_09_reaction_1600`。
- **commit**：`73dae15a`、`91c581f5`、`c178cc93`、`a8adcb96`、`df5b68f1`、`532612c8`（重拍）、`69bd19e7`、`5cadfc64`，以及報告。

## 3. 測試與檢查

- **新增 vitest**：`fix6f7.test.ts`，19 項。
  - 代價：縮寫、估寬；兩行照原樣；一行時縮寫成「AP2・法5・冷2」；拿掉段時加「…」，AP 與冷卻一定留著。
  - 代價的組合掃描：任何組合、一行或兩行都放得下，不以「・」結尾，有冷卻就留著冷卻。
  - 技能列 SSR 輸出。
  - 開發頁舞台鋪滿視窗。
  - 戰鬥 HUD：讓開的寬度和 CSS 一致；800 寬時地圖不碰兩欄；手動縮放時不讓；說明框不變淡、不透明、會換行。
  - 任務名兩行。
  - R 圓底的亮度與圖層順序；停用時不透明度 0.6。
  - 路線圖的圖層順序。
  - 「繼續」停用時不透明度 ≥ 0.6。
  - 特效圖層順序：地上特效 → 光環 → 浮動字。
  - 千分比轉百分比，以及三選一說明、工坊公式不再出現 ‰。
- **client 全部 vitest**（交件前跑一次）：**243 檔、2710 項通過**，結束碼 0。
  - `floatCardRule.test.ts` 也在裡面：禁用原生 `title=`。
  - 這段沒有新增 `Math.random`。
- **`corepack pnpm -C client build`**：結束碼 0，含 `tsc --noEmit`。
- **排版煙霧檢查**：先 `localStorage.clear()`；伺服器加 `TRPG_DEV_ROUTES=1`，埠 8388。

  | 項目 | 網址 | 1600×900 | 1040×624 | 800×600 |
  |---|---|---|---|---|
  | `runCase` | `/?dev=1&anim=0.1&mute=1` | 全 PASS | 全 PASS | 全 PASS |
  | `runEntry` | `/?mute=1` | 全 PASS | 全 PASS | 全 PASS |
  | `runScreens` | `/?dev=1&anim=0.1&mute=1` | 全 PASS | 全 PASS | 全 PASS |

  三種檢查、三種尺寸合計 450 列 PASS（`runCase` 33 列、`runEntry` 加 `runScreens` 417 列）。拍大世界時另外跑 `corners()`，全部回空。
  - 第一次拍時抓到一個問題：R 的圓底太大，伸進功能列右上的飾件。已縮小並重拍。
- **6.5.1 浮動卡實測**：技能鈕的技能卡（這段改了技能鈕）。

  | 步驟 | 1600×900 | 800×600 |
  |---|---|---|
  | 滑過約 450ms 後出現，貼齊上方 | ✓（卡片 718～837，觸發元素頂端 837） | ✓（314～433，觸發元素頂端 433） |
  | 滑進卡片後不關 | ✓ | ✓ |
  | 卡內捲到底 | 卡片 119px，沒有可捲的內容，只確認捲動不關 | 同左 |
  | 點一下釘住（class 有 `pinned`） | ✓ | ✓ |
  | 滑到空白處不關 | ✓ | ✓ |
  | Esc 關閉 | ✓ | ✓ |

  另外看到一件事：釘住後滑到右上的工具鈕，另一張說明卡會取代它。這是「同時只開一張」的既有規則，不是錯。
- **靜音**：無頭 Chrome 加 `--mute-audio`，網址都加 `?mute=1`。拍主城前先關掉開場對話框（「知道了」）。
- **程序**：
  - 自己啟動的有：API 8388、vite 5397、Chrome（CDP 9488，PID 71628），結束時都用工作 ID 或 PID。
  - **5391 被別的程序佔著**（只看到埠被佔，沒查是誰的，也沒動它），所以 vite 改用 5397。
  - 沒碰 `tmp_x`、`saves/`。暫存放在 `scratchpad/f7/`，沒有 commit。

## 4. 待 PM 決定

以下都照最保守的做法先做完了：

1. **800 寬的地圖變小**：自動填滿時地圖改放在兩欄 HUD 中間，800×600 的開闊平原從 77% 變成 65%。1040 是 92%，1600 是 139%（高度先頂到上限，沒影響）。地圖不再被 HUD 蓋住，但格子小一點，玩家可以按「＋」手動放大（手動縮放時不讓）。如果希望只讓左欄、右上戰況框照舊疊在地圖上，改 `hudSideInsets` 的 right 就好。
2. **代價縮寫的字**：照美術 PM 的例子用「AP2・法5・冷2」，其他段的縮寫是我定的：耐N、源N、HPx%、每場N、傳說、被動、代價、維持、反噬。只有名字兩行、代價只剩一行時才縮寫。一般按鈕放得下兩行，照舊寫全名。
3. **估寬是保守估計**：每行抓 10.8em，中文 1em、半形 0.6em。實際字型比估的窄一點，所以偶爾會比必要的早一點縮寫。
4. **Y（影子）圖示也偏暗**：和 R 一樣是深色人形，但有亮紫的虛線和眼睛，美術 PM 沒有點名，所以沒改。
5. **自訂裝備表單的詞條數值**（`ui/gear/CustomItemForm.tsx`）：輸入框本身是千分比，旁邊寫「（千分比，100 ＝ 10%）」。改成輸入百分比會改到輸入的意思，不只是顯示，所以沒動。同一行的數值範圍本來就顯示成百分比。
6. **伺服器與內容檔的「‰」**：`content/modifier_changes.yaml` 的名字（例如「傷害 ±‰」）、CLI 的預算報表都不在 `client/` 範圍內。目前前端顯示詞條時會把數值換成百分比，但如果名字本身帶「‰」字樣，還是會顯示出來；要改得動內容檔。
7. **光環截圖**：開發頁是連拍挑出光環和「暴擊 −9」同時在的那一格（1 倍）。放大截圖時 WebGL 畫布不會重畫，所以這一張沒有附放大圖。
