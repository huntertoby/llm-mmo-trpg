# Phase PB-1e 完成報告｜頭目部位美術移植（頭頂部位小格、亮起、正式破壞演出與外觀）

> 規格：`docs/art/頭目部位-移植需求.md`（1.2、2.3、2.4、3.4～3.6、第 4 節第 2～4 點、5.2）；`docs/phases/PhasePB-1計畫.md` T14、T15、PB-1e 列；`docs/phases/PhasePB-1c報告.md` 待決 6。畫法照 `docs/art/sample/bossParts.js`（第 2 版）、紀錄 `docs/art/頭目部位.md` 第 3.6、8、12 節。
> 基準：main `c149b1793`（開工時 worktree 已在這裡）。開工前 grep 過，PB-1e 沒有人做過。只改 `client/`、測試、本報告與上手筆記；沒有改引擎、API、設計文件。

## 1. commit

| commit | 內容 |
|---|---|
| `be1d83232` | 主體：頭頂部位小格、南邊有人時 HUD 改掛 `hudTop`、選單滑過亮起＋狀態列／蓄力徽章 40%、5 格破壞演出＋「破」字、拂塵剪短／劍斷／氣海裂痕與氣旋、地上掉落物、「{部位} 破！」提前到命中 |
| `40c253a27` | 金菱形不再蓋住部位小格；選單內說明卡點一下會選了那一列並送出攻擊（PB-1c 起的 bug）修好；測試 `battle/pb1eParts.test.ts`、`render/pb1eArt.test.ts`；開發頁 `client/dev/pb1e-gallery.html` |
| （本報告） | 報告、上手筆記第 165～168 點、截圖 10 張 |

主要檔案：`client/src/battle/partStrip.ts`（純函式）、`render/bossPartArt.ts`、`render/partLayer.ts`、`render/partBreakFx.ts`；改：`battle/drawModel.ts`（`UnitDraw.parts`／`partHudUp`／`partFx`）、`render/unitSprite.ts`、`render/battle/unitLayer.ts`、`render/rowLayers.ts`、`render/minMark.ts`、`render/qCore.ts`／`qSpec.ts`／`qWeapons.ts`／`qNpcHeld.ts`／`qNpc.ts`／`paperdoll.ts`、`render/resultEffects.ts`、`battle/specials.ts`（`partId`）、`battle/feedback.ts`／`playback.ts`、`ui/PartMenu.tsx`、`screens/BattleScreen.tsx`。

## 2. 逐條對照移植需求

| 需求 | 做法 | 驗收 | 截圖 |
|---|---|---|---|
| 1.2-1／2.3 頭頂部位小格 | HP 條正下方共用黑底：隔 0.8、三條各 11.2 寬、間隔 1.6、高 2.6、底邊 0.8，順序拂塵｜氣海｜長劍；「×」5.6；顏色照 2.2（米白／灰紫空槽／暗紅＋紅×外框色襯邊／未露出幾乎黑）；看不到資訊時三格都未露出 | `pb1eParts.test.ts`（排法、順序、隱蔽）、`pb1eArt.test.ts`（節點、hpBoxOf） | 1、2 |
| 2.3 800 寬最小尺寸 | 只放大高度：條高畫面 ≥2 px、×≥4 px、寬不變（`stripLayout`；部位小格是 `registerMark` 的標記，縮放改變時重畫，倍率固定 1） | `pb1eParts.test.ts`「800 寬」、`pb1eArt.test.ts`「地圖縮小時重畫」 | 2 |
| 2.3 朝南三角形 | `facingArrowPoly` 用「HP 條＋部位條」下緣（上緣離 0.5）；800 寬條變高時用節點 `pivot` 跟著往下 | `pb1eArt.test.ts` | 1、2 |
| 3.4 南邊有人改掛 `hudTop` | `UnitDraw.partHudUp`（有部位、南邊那格站著沒倒下的人）→ HP 條、護盾條、部位條、狀態列（含+N）、蓄力徽章、朝南三角形一起掛 `hudTop`；人走開照 `view` 重畫回 `marks`。部位條在 `hpBoxOf` 裡（徽章避讓）；紅框照 HID-1b 在單位之下（沒改） | `pb1eParts.test.ts`、`pb1eArt.test.ts`；原有 `occludedHud`、`southArrow` 照過 | 3、4 |
| 1.2-3／3.5 滑過亮起 | 部位遮罩由畫法直接給（`partLayer.renderPartLayer`：照常畫小人，只有正在畫那件手持物時上色、其他零件 `destination-out`，被手臂身體擋住的自然不算；同時用 `POSE.probe` 記下手持物變換）；亮青白 1.4＋外框色 0.9＋35% 填，描邊用距離轉換（`sqDistTo`，＝圓盤膨脹）；氣海是柔光＋兩道逗號氣痕（`glowQi`） | `pb1eArt.test.ts`（像素） | 3、4、8、9 |
| 3.5 選單打開 40% | `PartMenu.onFocus` → `BattleRenderer.setPartFocus`：狀態列（含+N）、蓄力徽章 alpha 0.4，關掉回 1；HP、護盾、部位條不淡；重畫場景後再套 | `pb1eArt.test.ts`「接線」 | 3、4 |
| 3.6 破壞演出 5 格 | `resultEffects` 的 `part_break` → `partBreakEffect`：80／80／160／160 ms 後定格；人物部分（部位白閃 0.9、亮金白裂紋、斷了但地上還沒掉落物）由繪製器蓋過（`setPartFx`），身上以外（burst、shard、ring、puff、dust、飛出的白毛／劍尖、「破」）畫在跟著頭目的貼圖；頭頂那一條第 1～3 格是空槽、第 4 格打叉。不擋回合 | `pb1eArt.test.ts`（時間、格） | 5、10 |
| 3.6「破」字 | 黑圓 72%、外圈紅 1.5、字亮黃 14 粗，掛在部位上方：拂塵 (+3,−14)、長劍 (−3,−15)、氣海 (+15,−2)；朝西左右對調 | 截圖 | 5 |
| 3.6 破壞後外觀 | 人物畫法三個旗標：拂塵剪短（`QItem.cut`，柄頂三撮短毛＋剪口，一起描外框）、劍斷（`QItem.broken`，裁到鋸齒斷口，側面斷口往刃尖 2.8）、氣海裂（`QUnit.dantian = "crack"`，三道深青裂痕＋四團淡霧，不描外框）；掉落物兩個小圖在環的左右兩端外 | `pb1eArt.test.ts`（旗標接到 Q 版） | 6 |
| 3.6 腹前氣旋 | 氣海露出（鎖霧、歸一）且沒破才畫；在 qStamp「外框之上」那層畫、側面挖掉主手武器（刃、護手、柄、握劍的手，照記下的變換與劍形）＝排在武器之下 | 截圖 | 7 |
| PB-1c 待決 6 | 「{部位} 破！」提前到命中那一刻（`playback.frameOps` 把 `early` 的浮字放在特效之後、重畫之前），和白閃同時（實機連拍 #27） | `pb1eParts.test.ts` | 10 |

**部位遮罩怎麼取得（報告要寫明 b）**：見上表「滑過亮起」——畫法直接給，不用換色相減。`qWeapons.mainWeapon` 畫手持物時設 `S.PAINT`，`partLayer` 用一層 context 代理決定上色或挖掉。

**第 4 節第 2～4 點怎麼處理（報告要寫明 a）**：
- 2（800 寬狀態圖示蓋下腹）：**維持現行狀態列位置**（選單打開時已淡到 40%，氣旋、裂痕、亮起都透得出來，截圖 4）。改排法會動到所有單位的狀態列與徽章避讓，列為待決。
- 3（「1」與「+1」相鄰）：用遊戲端實際的 `layoutBadges` 看（開發頁 800、狀態 2 個＋蓄力，截圖 4）：蓄力數字和狀態列沒有讀成「1+1」的相鄰；沒有改。
- 4（三角形壓臉）：**代決：改掛最上層時三角形以上緣中點縮成 0.6 倍**（`PART_HUD_UP_ARROW`，上緣仍離部位條 0.5）。只在頭目南邊有人時。

## 3. 瀏覽器實測（6.5.1；1600×900、800×600；無頭 Chrome `--mute-audio`、`?mute=1`）

進場：自己的 `trpg serve --port 8796`（`TRPG_DEV_ROUTES=1`、存檔在 scratchpad）、無頭 Chrome CDP 127.0.0.1:9351；雲頂觀種子 1、`build_ranged`、工坊試玩（`skill_piercing_shot` 換 id），主角每回合往 (9,2) 走到第 3 輪（真人在 (2,1)、劍陣、只有拂塵可打）；開發選單「一鍵開局」那一次 `POST /api/battles` 用 CDP `Fetch` 換成這場（上手第 168 點）。

| 檢查 | 1600 | 800 |
|---|---|---|
| 點頭目開選單、滑過拂塵列 → 頭目身上拂塵亮起、狀態列淡化 | ✓ | ✓ |
| 選單內滑過「破掉會」→ 說明卡出現 → 經橋接區滑進卡片仍開著 | ✓ | ✓ |
| 卡內捲到底（內容一行，scrollHeight＝clientHeight 52，捲動後仍開著） | ✓ | ✓ |
| 點卡片釘住、選單仍開著 | ✓（修好前：點卡片＝選了拂塵、直接送出攻擊） | ✓ |
| Esc：說明卡與選單一起關（PB-1c 裁定照現狀） | ✓ | ✓ |
| 破壞演出實機（回應補 `part_broken`，`anim=0.1` 連拍） | ✓ 浮字與白閃同時、5 格照順序、落地後打叉；console 無錯 | 未拍 |

## 4. 截圖（`docs/art/shots/pb1e/`，10 張；開發頁＝真的 `BattleRenderer`、頭目一帶最近鄰放大）

| 檔案 | 實機／開發頁 | 對應 5.2 |
|---|---|---|
| `docs/art/shots/pb1e/1-strip-1600.png` | 開發頁 1600（地圖 1.31）×4：完好、破壞中、已破壞、未露出、隱蔽、護盾＋部位條 | 1、4 |
| `docs/art/shots/pb1e/2-strip-800.png` | 開發頁 800（0.53）×8：同上 | 1、4 |
| `docs/art/shots/pb1e/3-hud-hover-1600.jpg` | 開發頁 1600：南邊有人／沒人／朝東；滑過拂塵、氣海、長劍（狀態 3 個＋蓄力 40%）、沒開對照、背面氣海、氣海已破 | 2、3、4 |
| `docs/art/shots/pb1e/4-hud-hover-800.jpg` | 開發頁 800：同上 | 2、3、4 |
| `docs/art/shots/pb1e/5-break.jpg` | 開發頁 1600：拂塵、長劍、氣海（背面）各 5 格，含「破」位置 | 5 |
| `docs/art/shots/pb1e/6-after.jpg` | 開發頁 1600：正面、朝東、朝西、背面 × 完好／拂塵破／長劍破／氣海破／全破 | 6 |
| `docs/art/shots/pb1e/7-qi.jpg` | 開發頁 1600：鎖霧、歸一有氣旋；劍陣、氣海破沒有；朝東在劍柄之下、朝西 | 7 |
| `docs/art/shots/pb1e/8-game-1600-menu.jpg` | 實機 1600：選單滑過拂塵、說明卡釘住 | 3、浮動卡 |
| `docs/art/shots/pb1e/9-game-800-menu.jpg` | 實機 800：同上 | 3、浮動卡 |
| `docs/art/shots/pb1e/10-game-break-1600.jpg` | 實機 1600 連拍（頭目一帶 ×3）：拂塵破壞演出 | 5 |

**實機未看**（用開發頁畫）：南邊有人的 hudTop、氣海與長劍的亮起與破壞（實機只到劍陣）、四方向破壞後外觀、氣旋、800 寬的破壞演出、800 寬選單放頭目上方（同 PB-1c）。

## 5. 結束碼（交件前）

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（356 檔、4510 項） |
| `corepack pnpm -C client build` | 0 |

Python 沒改，沒跑 ruff／mypy／pytest。沒跑 `scripts/check.py`、沒跑模擬、沒 push。自己啟動的 vite（8795）、`trpg serve`（8796）、無頭 Chrome（9351）都已關，三個埠沒有監聽。

## 6. 舊測試的改動

- `battle/pb1cPartBreak.test.ts`：`part_break` 多帶 `partId`（期望值加一欄）；「不動 `unitLayer.ts`、`case "part_break": return []`」那一項是 PB-1c 的範圍限制，PB-1e 改成「`part_break` 接到 `partBreakEffect`」。
- 其他舊測試的字串掃描（`occludedHud`、`southArrow`、`statusBadges`）照原字串保留接線寫法，沒改斷言。快照、雜湊、夾具都沒重產（沒有部位的單位 `DollSpec` 不帶 `parts`，貼圖鍵不變）。

## 7. 規格沒寫到、採保守做法的地方

1. 南邊那格「有單位」只算站著的（倒下的躺著、不會擋到部位條），同 6F-21b 的判斷。
2. 演出中斷掉的那一條：第 1～3 格畫成空槽、第 4 格才打叉（伺服器的 `view` 在命中＋停頓後就是已破壞）。
3. 滑過「打不到」或「未露出」的部位也亮起（實體還在）；已破壞的不亮。
4. 部位條與 HP 條改掛南邊一排的 `under`、排在金菱形之後（金菱形原本會蓋住中間那一條）；HP 條原本也被金菱形蓋一點，這次一起蓋回來（只有有部位的單位）。
5. 「破」字的大小是模型 px（半徑 10、字 14），800 寬畫面上約 5 px 半徑，沒有反向放大（需求沒寫）。

## 待 PM 決定

1. **「拂塵 破！」浮字蓋住「破」字記號**（實機連拍 #32～37）：浮字照 PB-1c 待決 6 提前到白閃那一刻，但它停在頭頂、正好在部位上方的「破」之上。建議：拿掉浮字（「破」記號已經講了），或浮字往上錯開；請美術 PM 看截圖 10 定。
2. 第 4 節第 4 點代決：南邊有人時朝南三角形縮成 0.6 倍（數值可調）。
3. 第 4 節第 2 點（800 寬狀態圖示蓋下腹）維持現狀；要改狀態列排法另排段。
4. 選單內說明卡點一下會選了那一列並送出攻擊——PB-1c 起就有、這段順手修了（`PartMenu` 列只認列裡面的點擊）；其他把 `<Hint>` 放在可點元素裡的地方可能有同樣問題，要不要排一次全面檢查。
5. 「破」字記號在 800 寬沒有反向放大（約 5 px 半徑），要不要比照預告格記號加最小尺寸。
6. 實機只拍得到劍陣階段（拂塵），氣海、長劍與南邊有人的 hudTop 只有開發頁；要不要另排佈局拍歸一階段。
