# Phase QK-4 報告：異形、頭目 Q 版造型與分部件動畫

> 實作者：worktree `dev/qk4v2`（從 main `5dd15774` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md` 第 2 版第 0 節、第 5 節；真相來源 `docs/art/sample/qCreature.js`、`qBoss.js`、`qCreatureAnim.js` 與三個樣張頁。照點列改寫進 client，沒有 import 樣張程式。只換畫法與動畫；規則、資料、存檔、重播沒動（`drawModel` 只多帶一個畫面用的 `bossPhase`）。

## 完成表

| 項目 | 狀態 | 檔案 |
|---|---|---|
| 畫法層：純色平塗、部件縫線、1.3 剪影外框（16 方向 × 3 圈膨脹）、霧下緣 3 段淡出、頭目外光（剪影膨脹）、白閃（剪影染白） | 完成 | `client/src/render/qCreatureLayer.ts`（離屏畫布有池） |
| 14 種身形 16 款 × 6 材質：方眼＋高光、Q 大頭 10 款、材質平塗紋樣（熔岩裂縫、源晶亮面＋背刺、青石刻符、木紋、霧漩渦、毛皮肚色；tiny／small 簡化 1 筆） | 完成 | `inkCreature.ts` |
| 元素色（熔岩聖＝乳白鋸齒＋小十字、源晶暗＝深靛紫）、玄武岩提亮 `#4a3631` | 完成 | `inkCreature.ts`、`qCreatureElem.ts` |
| 特徵、精英詞綴（黃煙／霧團／霧隱無外框半透明、其他細外框）、精英金環＋金菱形（Q 版外框色、亮點） | 完成 | `inkCreature.ts`、`unitSprite.ts eliteRing` |
| 頭目 2 位：灰燼之心（10 殼片掛點、3 階段、核心光暈當外光）、碎晶之主（晶冠、浮晶、4 階段、傳說金剪影外光）；東側整隻鏡像 | 完成 | `qBoss.ts`；範本 `ashen_heart`／`rift_shard_lord` 走頭目畫法，階段照 `boss_phase`（沒有時灰燼之心看熔殼） |
| 動畫：16 款 × 待機、移動、受擊、倒下＋35 個攻擊（依動作類型）；頭目 `act()` 攻擊、受擊、倒下＋待機 16 格 | 完成（蜘蛛、蛇、晶靈也做了，沒延） | `qCreatureAnim.ts`、`qBoss.ts` |
| 戰場接法：移動＝每款移動片段；技能出招依動作類型挑攻擊（衝鋒／召喚／位移／範圍／吐息照片段，其他看距離：自己＝範圍、>1 格＝遠程、相鄰＝普攻）；受擊、倒下、倒地；異形待機（8 格、id 雜湊相位） | 完成 | `creaturePose.ts`、`BattleRenderer.ts`（2 處）、`idleMotion.ts`、`reactClips.ts`（異形閃避／彈開／勝利） |
| dev 畫廊 | 完成 | `client/creature-gallery.html`（預設造型頁、`?anim=<身形>`、`?boss=atlas`、`?boss=page`、`?view=strip`、`&reduce=1`） |

## 截圖（`docs/art/shots/qk4/`）

- `compare/q-creature-<身形>-compare.gif` × 16：**左＝樣張、右＝遊戲**，每款每個動作逐格（待機 8、移動 8×2、各攻擊、受擊、倒下；時間照樣張 gif），縮 50%。左邊用樣張頁 `q-creature-anim.html?atlas=` 當下畫出來的格（見下方「發現」）。
- `compare/q-creature-{hound,golem,wisp,bird}-reduce-compare.gif`、`compare/q-boss-reduce-compare.gif`：`&reduce=1` 對照。
- `compare/q-boss-compare.gif`：頭目 111 格（含灰燼之心第 2 階段外觀的受擊）。
- `compare/qk4_creatures_page_compare.jpg`、`qk4_bosses_page_compare.jpg`：造型頁整頁（左樣張頁、右遊戲畫廊，同版面；遊戲頁沒畫 C 版欄與 Q 主角）。
- 實機（`TRPG_DEV_ROUTES=1`、開發模式、靜音、弓）：`qk4_battle_boss_1600.jpg`（熔心坑：灰燼之心＋2 隻殼縫餘燼蜥）、`qk4_battle_boss_1600_zoom.jpg`、`qk4_battle_boss_800.jpg`、`qk4_battle_creatures_1600.jpg`（熔岩洞窟：熔岩甲蟲群）、`qk4_battle_creatures_1600_zoom.jpg`、`qk4_battle_idle_3moments.jpg`（隔 0.7 秒三張，待機有動）。

## 驗收摘要

- 逐格像素比對（門檻 40 的差異像素數）：16 款 gif 每款中位數 0；差最多的幾格都是**樣張自己晚一格**（樣張 atlas 用 `t = f × 83.33` 再 `floor(t / 83.33)`，浮點誤差讓某些格停在前一格）；遊戲照片段定義的格。頭目 111 格中位數 0，同一原因。精英金環、詞綴、頭目外光跟著動不脫離（gif 右隻）。
- vitest 全量 254 檔 3175 個全過；typecheck、build 過；排版煙霧三尺寸**全 PASS**（「四角飾件」這次也 PASS）。
- 新測試：`qCreatureAnim.test.ts`（16 款／35 攻擊、確定性、數值有限、播完回原樣、倒下停最後一格、id 相位、減少動態、類型挑攻擊、**作用端在畫布內**、每格畫得出且指令流相同）、`qBoss.test.ts`（範本→頭目、階段、確定性、殼片名稱雜湊、片段、減少動態、戰場接法、遠程特效只在 fxAll）。
- 更新的既有測試（斷言意圖不變、改成新畫法的值）：`inkCreature.test.ts`（玄武岩色 `#3b2c28`→`#4a3631` 兩處）、`creaturePose.test.ts`（6M-2 的 4 個整隻片段換成 Q 片段引用：純函式、量化、受擊回原樣、倒下停住、走路循環、影子不動）、`bodyAnim.test.ts`（白閃改在剪影層，3 個測試照新流程驗）、`reactClips.test.ts`、`resultClips.test.ts`（異形受擊／倒下／站起改看片段）。
- 快照重產（`vitest run -u`）：`client/src/render/__snapshots__/creaturePose.test.ts.snap`（異形靜態指令流）。

## 發現

- 樣張 gif（`shots/anim/q-creature-*.gif`）有幾格比現在的 `qCreatureAnim.js` 舊（例如傀儡雙拳震地第 8 格 gif 還舉著手、程式已砸地）；並排圖左邊改用樣張頁當下畫的格，時間仍照 gif。
- 一開始的版本有 save／restore 不成對（整隻 root 變換多 save 一次），已修，加了每格指令流測試。

## 待 PM 決定

1. **飛向目標的特效**（飛行物、命中爆開、雷、射線、恐懼波、油團）：戰場上技能特效本來就畫，貼圖再畫會重複，所以標 `ranged` 只在畫廊畫（`fxAll`）；蓄力光、吐息、震地環、咬合、爪痕、塵土照畫。要不要改成貼圖也畫，請美術 PM 定。
2. **攻擊片段的時間**：異形攻擊片段塞進技能時間軸「出招」那一列的長度裡播（含蓄力），命中那一刻沒有特別對齊片段的出手格。保守做法；要對齊要動 `skillSequence`。
3. **頭目待機**：16 格一圈 5278 毫秒（灰燼之心呼吸剛好兩次）；碎晶之主的浮動、碎晶繞行週期不整除，一圈接回時有一小跳。
4. 狀態列避開矮異形的判斷（`statusRowY`）還是拿 C 人形頭頂比（沒改，保守）；頭目改用 qBoss 的頭頂高度。
5. 改到清單外、但都是異形／頭目分支的檔：`battle/drawModel.ts`（多 `bossPhase`）、`idleMotion.ts`（異形待機分支）、`BattleRenderer.ts`（出招挑類型、待機接法 2 處）、`reactClips.ts`（異形閃避、彈開、勝利改整隻小動作）。`unitSprite.eliteRing` 改 Q 版外框色與金菱形亮點，人形精英也跟著變；人形詞綴位置 `HUMANOID_FX` 改照 Q 頭（頭頂 -38，同樣張 `HUMANOID_INFO`）——和 QK-8 人形敵人有交集。
6. 連心的：樣張貼圖裡的兩段示意虛線沒畫（戰場的連線由 BattleRenderer 畫，同舊做法）。
7. 畫廊為了和樣張比對，「精英＋外光」那隻照樣張 ×1.15；遊戲規則照舊（頭目不放大）。

## Commit

- `30b5aa03` feat(art): QK-4 Q-style creatures, bosses and per-part creature clips
- `643c07fb` fix(art): QK-4 pose save/restore leak, canvas pool, anim tests and sample compare shots
- `16987d94` feat(battle): QK-4 wire Q creature idle, typed attacks, boss phase and lighter dodge
- （本報告與實機截圖）docs(phases): QK-4 report and live battle shots

出圖：Playwright＋系統 Chrome（非無頭），腳本在 scratchpad 沒進 repo。
