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

## QK-4b：樣張修正移植＋QK-4 累積待修

> worktree `dev/qk4b`（從 main `b98033fb`）。依據：`docs/art/QK-4檢查.md` 第 2～4 節、對照圖 `docs/art/shots/misc/qk4b-sample-fix.png`、`docs/art/頭目造型.md` 第 4 節（×1.6、外光）、樣張 `127baf80`。沒有 push、rebase。規則、資料、存檔、重播沒動（Python 沒改）。`qAnimFB.ts`、`qDoll.ts` 沒動。

### 完成表

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 熊、野豬側倒；四足獸閉眼 × | `qCreatureAnim.deathSide`（照樣張，四腳往前後攤開、頭垂地、u≥0.6 閉眼）；犬狼、豹、蜥蜴的 `deathQuad` 也在 u≥0.6 閉眼（美術 PM 決定 4）。`QPartPose.eyeShut` → `inkCreature.eye` 畫深色 × | `c9221897` |
| 2 | 傀儡崩塌 | `QPartPose.split`（照樣張 `POSE.split`）：軀幹沿裂縫 3 塊各自位移旋轉（`inkCreature.drawSplit`，clip 多邊形）；頭往後滾一圈多、手臂散落、腿垮成殘樁 | `c9221897` |
| 3 | 鳥待機收翅＋起飛／落地 | 待機照樣張（落地 dy 9、第 6～7 格抖翅）。整段移動的開頭、結尾 333 毫秒（約 4 格）過場 `creaturePose.perchAt`（量化 1／0.75／0.5／0.25／0）：身體、頭、尾內插，翅膀不內插（收翅與拍翅 sy 正負相反，中間會變一條線）＝落地收翅 → 抖翅半開 → 拍翅。戰場站好（沒有動畫）的鳥畫待機第 0 格（`unitSprite.creatureRestPose`），減少動態也一樣是收翅 | `c9221897`、`52e2d01a` |
| 4 | 頭目 ×1.6、HUD 在剪影上方 | `HUGE_FIELD_SCALE` 0.9 → `qBoss.BOSS_FIELD_SCALE`＝1.6（只認頭目範本）；貼圖解析度 ×1.6（`artTextures.creatureRes`）。`unitSprite.bossHudDy`：HP 條、狀態列、炸彈／蓄力／灌注徽章、朝向三角形整組照一般單位排好再平移到頭頂上 2px（避讓關係不變）；最上排不超出頭頂預留。頭目的三角形畫在身體之後、不掛南邊一排。`BOSS_BOX.top` 改量到含外框＋外光（灰燼之心 −55、碎晶之主 −106，含浮動） | `d682b089` |
| 5 | 外光沿輪廓 | 兩位頭目都是剪影外 2.2、80% 傳說金（`BOSS_GLOW_W／A`，同樣張）；灰燼之心的核心光暈只在火焰箭蓄力（flare）時畫；熔毀橘光、碎晶之主胸口核心光照舊 | `d682b089` |
| 6 | 兔尾側面 | `qRace` 側面 (6, −10.5) → (8, −8.5) | `90bcbba5` |
| 7 | 方臉、心形臉正面頭頂 | `qHead.hair` 正面：髮際線以上裁切、臉型放大 1.04 的髮色塊（同樣張） | `90bcbba5` |
| 8 | 大鬍子側面 | 大鬍子在 `qRace.raceFace`（不在 `qHead`）：側面裁掉臉前緣以外，下巴下垂保留 | `90bcbba5` |
| 9 | 頭目 gif | 兩位各一張、每格自己的色盤；每個階段先放待機 16 格再放各片段（畫廊 `?boss=atlas&who=ah|sl`，同樣張 `?boss=atlas&who=`） | `fed3bdef` |
| 10 | 灰燼之心狀態列疊在核心 | 併第 4 項（狀態列在剪影上方） | `d682b089` |
| 11 | 人形敵人疊精英詞綴 | `skill-gallery.html#elite`（正式繪製器）：盜賊一般 vs 精英 × 9 組詞綴、異形精英對照 | `a2121625` |
| 12 | 異形普攻特效 | ① 飛行物、射線、扇形從異形的嘴發出（頭目：灰燼之心核心、碎晶之主前手晶；`inkCreature.creatureMouth`，原本用人形的作用端）② 普攻的特效沒有飛出去的東西（相鄰＝揮砍）時，出招列帶 `ownFx`，片段自己的射線／飛行物照畫（晶塔普攻射線）；遠程普攻已有飛行物的不重複畫。`skill-gallery.html#creature` | `40c1084a` |
| 13 | 碎晶之主待機小跳 | 待機一圈（`loop`＝0～1）時每個振盪的週期取整成一圈整數次（`qBoss.osc／cyc`），u＝1 與 u＝0 同一格；灰燼之心呼吸本來就整除 | `d682b089` |
| 14 | 頭目命中對齊出手格 | `qBoss.bossPlan`（從 `bossAct` 拆出的純函式）＋`bossAttackHitU`（戰場量化 12 格，第一個出手特效格；沒有＝往前推最遠格）；`viewGrip.creatureStrikeInView` 頭目照 `bossAttackClip`（階段、動作類型）回片段長與出手格，接上 QK-5 的 `StrikeOf` | `d682b089` |

### 截圖（`docs/art/shots/qk4/compare_v2/`）

- `creature_deaths_compare.jpg`：熊、野豬、傀儡、犬狼、豹、蜥蜴倒下 5、8、10、12 格（左樣張、右遊戲；犬狼豹蜥蜴的 × 是決定 4，樣張還沒改）。
- `bird_idle_takeoff.jpg`：樣張待機／遊戲待機 8 格＋遊戲起飛 5 格、落地 4 格（`creature-gallery.html?view=perch`）。
- `q-boss-ah-compare.gif`、`q-boss-sl-compare.gif`：左樣張、右遊戲，各自色盤；待機 16 格 × 每階段＋各片段。
- `doll_tail_face_beard.jpg`：樣張特寫 s03_05／s04_04／s12_01 vs 遊戲畫廊同格；方臉、心形臉四方向。
- `qk4b_battle_boss_1600.jpg`、`qk4b_battle_boss_1600_zoom.jpg`：實機熔心坑 1600×900（灰燼之心 ×1.6、HUD 在剪影上方、外光沿輪廓）；碎晶之主同一場把畫面資料的範本換掉拍（裂界門沒有開發入口，只換前端畫法）。
- `qk4b_creature_basic_attack.jpg`：`skill-gallery.html#creature`（正式串接器＋繪製器）300／450／600 毫秒：火塵蝠普攻火焰箭從嘴飛出、晶塔普攻射線、噴岩龜。
- `qk4b_elite_humanoid_affixes.jpg`：`skill-gallery.html#elite`。

### 驗收摘要

- 逐格比對（門檻 40 差異像素）：倒下 6 款中位數 0；鳥待機 0；灰燼之心 gif 中位數 0（待機第 3 階段約 300，滴落相位取整）；碎晶之主待機 6000～8000（**第 13 項首尾接上改了振盪週期，和樣張的相位不同**，動作片段中位數 0）。最大值都是「樣張慢一格」那幾格（同 QK-4）。
- vitest 全量 268 檔、3262 項全過；新測試 `qCreatureDeath4b.test.ts`（8 項）、`qBoss4b.test.ts`（7 項）、`creatureStrike.test.ts` +1 項。改值的既有測試：`ui/statusBadges.test.ts` 一行原始碼字面值（`registerBadges(…, hudDy)`，意圖不變）。
- 快照重產：`render/__snapshots__/inkDollSnapshot.test.ts.snap`——矮人 ×5（dwarf、+helmet、+hood、+robe+cape、+wizard）、`sect_mist_lock_master`、`sect_steward`（大鬍子側面裁切）。
- `tsc --noEmit`、`vite build` 過；排版煙霧 1600×900、1040×624、800×600 都 13 PASS、0 FAIL。

### 改到清單外的檔

- `render/BattleRenderer.ts`：鳥過場（`stepLeg` 多一個 `around`，walk 迴圈算前後腿長）、異形出手點（`creatureMouthWorld`）、出招列 `ownFx` → `fxAll`。三處都小，和 QK-5c 若同檔衝突以各自的段落合併即可。
- `render/artTextures.ts`：頭目貼圖解析度 ×1.6。

### 待 PM 決定

1. **碎晶之主待機的相位和樣張不同**：首尾接上的做法是把每個振盪週期取整成一圈整數次（浮動 2 次、繞行碎晶 1 圈…），樣張仍是線性時間（有小跳）。要逐格一致需樣張照同法改（`qBoss.ts osc／cyc`）。
2. **頭目的陣營環與精英金環**照一般單位大小（佔 1 格的意思），被 ×1.6 的剪影蓋住大半，只露金菱形；樣張的環跟著 ×1.6。要不要放大環？
3. **浮動字、敵群眼睛**仍從頭目剪影頂端（`unitTopY`）冒出，會穿過上移的 HUD；沒改（保守）。
4. **頭目放在最上排**時 HUD 被頭頂預留卡住，會疊在剪影上；碎晶之主高約 3 格，靠上兩排時頭也會超出畫布上緣（現有地圖頭目都不在上排）。
5. **鳥起飛／落地過場**是開發自訂（樣張沒有）：翅膀「收翅 → 抖翅半開 → 拍翅」，身體內插，約 333 毫秒；請美術 PM 看 `bird_idle_takeoff.jpg`。
6. **異形普攻**的解讀：特效路徑仍是 `vfxFor` 的普攻（遠程＝飛行物、相鄰＝揮砍），只改出手點（嘴）與「沒有飛出去的東西時畫片段自己的射線」；異形的武器類別沒有改成照 `weapon_id`（異形沒有骨架，法杖的起手、杖頭光不會畫）。
7. **gif 大小**：兩張各約 0.8 MB（110 格、每格自己的色盤），超過 6.5.2 單張 300 KB；縮更小會看不清。
8. 減少動態的頭目 gif 沒重拍（張數上限）；畫廊 `?boss=atlas&who=ah&reduce=1` 可直接看。

### Commit

`90bcbba5`、`c9221897`、`d682b089`、`40c1084a`、`a2121625`、`fed3bdef`、`52e2d01a`、`fdc06eeb`、`f434c383`＋本報告。

出圖：Playwright＋系統 Chrome（無頭；`vite --port 5197`、`trpg serve --port 8151`、樣張 `http.server 5198`），腳本在 scratchpad。
