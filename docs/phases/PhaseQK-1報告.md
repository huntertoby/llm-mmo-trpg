# Phase QK-1 報告：Q 版人物移植第一段（畫法層＋人形本體＋骨架＋10 族＋裝備與 21 種武器＋關鍵姿勢與手臂規則＋新部件）

> 實作者：worktree `dev/qk1`（從 main `d5f4aa13` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md` 第 0 節與第 2 節；真相來源 `docs/art/sample/qDoll.js`（＋`raceArt.js`、`parts-extra.js`）。

## 0. 樣張資料結構對到 client 哪些檔

樣張是一個 1400 行的 IIFE，靠模組變數（`POSE`、`WEST`、`TINT`、`FAR`、`SEAM`…）在函式間傳狀態。照點列與規則改寫成 TypeScript，**沒有 import 樣張程式**：

| 樣張 | client | 說明 |
|---|---|---|
| 模組變數、`fk`／`ik`／`elbowTo`、`ARM_SPREAD_SET`（A、E）、`mix`、`colors`、`wc` | `client/src/render/qCore.ts` | 狀態集中在一個物件 `S`；`ARMS.cur` 預設 E（自測比寬度時暫換 A）；顏色走 hooks（遊戲用 `itemColors`，畫廊用樣張色） |
| `QW`（21 種武器＋拄劍短劍）、`qWeapon`、`ALIAS`、`mainWeapon`、`offDagger`、`TWO`；`paperdoll.js` 的 `drawWeapon／drawWeapon2`（盾、書、法球） | `client/src/render/qWeapons.ts` | `pdHeld` ＝ 樣張 `PD.drawWeapon` |
| `raceArt.js`（體型、尾巴、龍翼背刺、臉、耳、帽子避讓、角、`RACES`） | `client/src/render/qRace.ts` | |
| `headShape`、`eyes`、`beard`、`hairBehind`、`head`、`PD_hair`、`Q_headgear` | `client/src/render/qHead.ts` | |
| `leg`、`body`、披風、盾三面、`backItem`、`waistItem`、`neckItem`、`crest` | `client/src/render/qGear.ts` | |
| `arm`（手臂規則全部欄位）、`armEdge`、`fistEdge`、`glove`、`shieldArmBack`、`KEY`、`GS_ATK`、`keyOf`、`sidePlan`、`bowFace`、`bowStill`、`wrap`、`draw` | `client/src/render/qDoll.ts` | `KEY()` 依手臂規則算（E／A 各一份） |
| `stamp`（離屏剪影、圓盤膨脹外框、拿弓閉合）、`BOX` | `client/src/render/qStamp.ts` | `qStamp`（畫廊，同樣張介面）、`qStampLocal`（遊戲，依目前縮放 3 倍取樣） |
| `selfTest`（武器 13×4、`cloakTest`、`two`、`handTest`、`gripTest`、`crossTest`、`offArmTest`） | `client/src/render/qSelfTest.test.ts`＋`client/src/test/vecRaster.ts` | vitest 沒有 Canvas：寫了一個向量點取樣畫布做像素檢查 |
| `closeups.html` 的格子定義、`anim.js` 的 `unit`／命中格、`idleWeapons.js` 的待機、`paperdoll.js` 的 `ITEMS`／`TEMPLATES` | `client/src/render/qSample.ts`、`client/src/dev/qGallery.ts` | 只給畫廊與自測用 |
| 遊戲外觀 `DollSpec` → Q 版 | `client/src/render/qSpec.ts` | 成對匕首 → `paired`；赤膊 → 膚色上衣 |

沒移植：`armBent`（只在 `ARM.elbow` 時走，E 沒有）、`ARM_DX` 斜肩（E 的 dx 0）、`TWO.pts`／`zh`（只給已刪的求解器）。

## 1. 完成表（第 2 節 11 項）

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 畫法層 | `inkStyle.ts` 加 `DollSkin`（`"q"`／`"c"`）與 `dollSkin()`／`setDollSkin()`，**預設 Q**；`paperdoll.drawFigure` 走 Q：地上影子（深色橢圓，在外框外）→ `qStampLocal`（離屏、剪影、12 方向線段膨脹的圓盤外框 1.3 單位、拿弓閉合）。離屏至少 3 倍取樣（1 倍時外框糊成灰霧，見 `cf8958f8`）。墨線排線、筆觸都不畫。沒有 DOM（vitest）時直接畫填色 | `cd692946`、`314e1095`、`cf8958f8` |
| 2 | 人形本體與骨架 | 頭、身、腿、臂、手、臉換成 Q 版尺寸；關節髖 −9、膝 −5、肩 −20（側面肩線 x 2、正背 ±8.5）、肘 −15、手 −9.5、頭心 −29。`inkDoll.ts` 匯出 `DOLL_JOINTS`；`skillClips.anchorPoint` 改成 Q 版時用這一份（`anchorPointQ`）；`BattleRenderer` 特效起點的武器長度改用 Q 版 `QW` 的 len。`DOLL_HEAD_TOP` 53 → **38**（量出來：頭頂 −37.5、頭髮 −38.6；規格寫「約 −46」，見待決 1）。`DOLL_H` 88 → 64 **沒做**（見待決 2） | `e0e90377`、`314e1095` |
| 3 | 頭與頭髮四方向、12 種頭飾四面 | 照 `qDoll.js`（側臉前半一隻眼、鼻尖、腮紅，長髮只在耳後；兜帽、頭盔、角盔、巫師帽、便帽、頭巾、頭冠、寬帽、面紗、護目鏡、王冠、全罩盔） | `ec733d08` |
| 4 | 手臂規則 | `ARM_SPREAD_SET.E` 全部欄位（a 0.325、sw 1、bk −1、shf、po 0、shA 0.2、ea 0.09、edge inner 0.9／0.45、fist ring 0.9／0.45、sideOne）與 `outOf`、`FILLARM`、`FREEARM`、`SEAMIN`、`ONE`；袖子描邊（打直一圈、彎肘兩段）、布料內線、拳頭圈、盔甲袖子深一階、遠側暗一階 | `8ffcf2a4` |
| 5 | 關鍵姿勢表 | `KEY` 6 類 × 正、背、側（`sideW` 朝西手性互換）、雙手劍拄劍、出招 Q 版專用關鍵姿勢（`atk`：雙手劈 `GS_ATK`、長柄刺、鐮收割、弩槍瞄準；`bowAim`：弓拉到臉頰）。單手武器照 6M／6N 片段，武器角度＝手臂角度＋wpn。6N 片段另一隻手的手勢（`armF`）在另一隻手空著時照用 | `8ffcf2a4`、`314e1095` |
| 6 | 10 族 | `raceArt.js` 全部；遊戲資料的龍裔 `pattern: dragonscale` 畫成樣張龍裔的「少量鱗」（dragonQ 菱形鱗＋眉骨），豎瞳照資料畫（見待決 3） | `e5fedb1a` |
| 7 | 既有裝備 | 布、皮、鎖、板、袍、外套、兜帽、帽、尖帽、頭盔、靴、脛甲、披風、圓盾、鳶盾、聖盾、塔盾、書 | `e0e90377` |
| 8 | 21 種武器 | `QW` 表（劍、雙手劍＋拄劍兩種短劍、魔導劍、刀、匕首、成對、斧、鎚／釘頭錘、長槍、鐮、鞭、拳套、杖、法球、弓、弩、槍三種形制）＋`pdHeld`。魔導劍源晶槽有元素時換元素色（Phase 3I-3 規則照舊，樣張沒寫元素） | `cdd4bcdb` |
| 9 | 新部件 9 種 × 四面 | 箭袋、背包、卷軸筒、劍鞘、腰包、項鍊、念珠、胸前紋章、護腕 | `e0e90377`、`8ffcf2a4` |
| 10 | 體型 | stout ×(1.12, 0.88)、tall ×(0.96, 1.1)、標準照現行 `buildScale`；矮人資料就是 stout | `e5fedb1a` |
| 11 | 第 0.3 節三點 | 見第 2 節 | `8ffcf2a4`、`4cf6c043` |

另：dev 畫廊 `client/doll-gallery.html?skin=q&set=key|parts|walk`（`client/src/dev/qGallery.ts`，`c71df733`、`0cf8f6f9`）；並排與鎖格腳本 `docs/art/sample/tools/qk_compare.py`；selfTest vitest（`b534b594`）。

## 2. 第 0.3 節三點怎麼處理

1. **雙手劍遠側手接自己深一階的袖子**：側面關鍵姿勢裡，近側手臂畫完之後，把遠側手臂（暗一階、只露胸前那段）再畫一次，剪裁在「近側手臂中線往上 1.2 單位」以上，所以上面那隻拳頭和自己的袖子連起來、近側手臂的下半仍蓋在前面。拄劍（`r01` 東）、待機（`i15`）、出招（`a14`、`g1～g3`）都吃。`qDoll.ts` 的 `gsFarSleeve`。
2. **單手劍四指握法**：劍、刀、魔導劍在正面、背面、側面（含出招片段）都在拳頭上補一條橫過握把的四指（同杖的 `wrap`），握把從拳頭上下穿出；遠側手只畫在拳頭輪廓裡。`qDoll.ts` 的 `swordGrip`／`sideSwordGrip`。**這一點會讓鎖格 `r09` 東西、`i02` 兩格多出四指**（第 4 節）。
3. **朝西遠側伸去握長柄的手（`r03`、`r04`、`r08` 西）**：遠側右肩點往後 1.4（x 2 → 0.6），手臂照新肩點直指原本的拳頭位置、按比例伸長，拳頭和柄的位置不動；上臂變低一點，和下巴之間露出縫。`qDoll.ts` 的 `WEST_FAR_BACK`。

## 3. 快照與測試的變動

- **重產**：`client/src/render/__snapshots__/inkDollSnapshot.test.ts.snap`（5 組，Q 版的畫布指令流）。`creaturePose` 快照沒動（異形是 QK-4）。
- **C 畫法的測試改成指定 C**（斷言一行沒改；畫法層預設改 Q 之後，這些檔案測的是 C 的墨線畫法本身，在檔案開頭或該項開頭 `setDollSkin("c")`）：
  - 整個檔案：`inkDoll.test.ts`、`inkGear.test.ts`、`inkPose.test.ts`、`inkSect.test.ts`、`inkArmor.test.ts`、`inkWeapons.test.ts`、`world/capitalOpeningReview.test.ts`（開場半坐起撐地，QK-2 恢復暫停畫面時重做）。
  - 單項：`dollGear.test.ts`「成對武器與拳套」（數 C 的 rotate 次數）、`dollHit.test.ts`「白閃用的身體另畫一次」（數畫布編號，Q 的外框另開離屏畫布）、`eventArt.test.ts`「同一場景只畫一次」（數 createElement）、`summonArt.test.ts`「霧影貼圖」（找 C 的斜線影子）、`skillClips.test.ts`「front views use the hands」（C 的手在 ±9）。
- `inkWeaponFrame.test.ts` 照跑、沒改，全過（它測的是 C 的武器座標）。
- `unitSprite.ts`：異形「比人形矮」的門檻改跟 C 人形頭頂比（`DOLL_HEAD_TOP_C`），因為異形還是 C 的尺寸（QK-4 才換）；否則所有異形都算「比人形高」，`art5.test.ts` 會失敗。
- **新測試** `client/src/render/qSelfTest.test.ts`（9 項，第 0.4 節 8 條）：13 種武器 × 東西出招／靜止作用端不朝後、作用端在畫布內、正背看得到作用端（弩背面被擋）；Q 版出招關鍵姿勢作用端在前；雙手武器正背側兩手在握把上；手在握把上（像素）；刃不被手臂蓋住 ≤ 3%（像素）；背面披風在最上層（順序＋像素）；背面手被身體擋住；背面副手（持盾露前臂 ≥ 4 單位²、書只露 0.2～2）；正面背面輪廓不比手臂規則 A 寬（空手、拳套除外：E 的空手用使用者定案的 ea 0.09，A 是直垂，定案本來就寬 1.5 單位）。

## 4. 並排圖與鎖格

- 並排圖（左：`docs/art/closeup/` 樣張、右：遊戲畫的，畫廊用樣張色）：`docs/art/shots/qk1/compare/`，key 95 張、parts 62 張逐格 jpg，另有 `_sheet_key_*.jpg`、`_sheet_parts_*.jpg` 總表（每頁 12 格）。
- 鎖格 13 格（`closeup/locked/`）像素差（任一通道差 > 8 的像素占比；標題列一律 0 差）：

| 鎖格 | 差（占比） | 原因 |
|---|---|---|
| key/a08_gauntlet | 0.23% | 只有邊緣反鋸齒（無頭 Chrome 與美術 PM 的 Mac 渲染差） |
| key/a09_staff | 0.40% | 同上 |
| key/a11_bow | 0.35% | 同上 |
| key/b4_bow_draw2 | 0.51% | 同上 |
| key/b5_bow_full | 0.51% | 同上 |
| key/b6_bow_release | 0.40% | 同上 |
| key/i02_sword_shield_mid | 0.53% | 反鋸齒＋第 0.3 節第 2 點的單手劍四指 |
| key/i02_sword_shield_start | 0.56% | 同上 |
| key/i09_gauntlet_mid | 0.23% | 反鋸齒 |
| key/i09_gauntlet_start | 0.27% | 反鋸齒 |
| key/r09_sword-shield_east | 0.64% | 反鋸齒＋單手劍四指 |
| key/r09_sword-shield_west | 0.36% | 反鋸齒＋單手劍四指 |
| parts/s06_04 | 0 | 完全一致 |

標題列（字型）每格 0 差。逐格差異圖看過 `a08`、`r09` 東：除了四指，只有輪廓邊緣一圈 1 px 的反鋸齒差。

## 5. 截圖（`docs/art/shots/qk1/`，7 張，jpg 80，最大 249 KB）

- `docs/art/shots/qk1/qk1_battle_1600.jpg`＋`docs/art/shots/qk1/qk1_battle_1600_zoom.jpg`（地圖區放大 2 倍）：開發模式「一鍵開局」的戰場。
- `docs/art/shots/qk1/qk1_battle_800.jpg`：同一場 800×600。
- `docs/art/shots/qk1/qk1_town_1600.jpg`＋`docs/art/shots/qk1/qk1_town_1600_zoom.jpg`：新角色（龍裔）在主城醒來。
- `docs/art/shots/qk1/qk1_town_800.jpg`：同一處 800×600。
- `docs/art/shots/qk1/qk1_walk_4dir.jpg`：走路四方向連拍（遊戲的畫法＋6M-3 走路片段，劍盾、杖書、弓、雙手劍 × 南北東西 × 8 格，2 倍）。

## 6. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 251 檔、3152 項全過（含新的 `qSelfTest.test.ts` 9 項、`inkWeaponFrame.test.ts` 照舊） |
| `tsc --noEmit`、`pnpm build` | 過（只有原本的 chunk 大小提醒） |
| 排版煙霧檢查 1600×900、1040×624、800×600 | 三個都 12 PASS、1 FAIL：「戰鬥：四角飾件沒有壓到內容」（主角卡左下飾件 × 技能晶片），**和 6F-22 報告記的一樣，main 上就 FAIL**，本段沒動 HTML／CSS |
| Python | 沒改伺服器、資料欄位，沒跑 pytest |

## 7. 待 PM 決定

1. **`DOLL_HEAD_TOP` 用 38**（從 `qDoll.js` 量：頭頂 −37.5、頭髮 −38.6）；規格寫「頭頂約 −46」，可能是把帽子或身高 46 算進去。狀態列、浮動字、頭上眼睛跟著降。要 46 的話改一個常數。
2. **`DOLL_H` 沒從 88 縮到 64**（選做）：`inkDoll.test.ts`（C 畫法的測試）斷言畫布 ≥ 76，縮了要改那條斷言，照規則沒改。Q 版頂到約 −52，64 夠；要縮的話 PM 同意改那條測試即可。
3. **龍裔臉**：遊戲資料是 `dragonscale`＋豎瞳＋鱗脊＋背刺。照規格第 6 項「少量鱗、豎瞳」，`dragonscale` 畫成樣張龍裔的菱形鱗（dragonQ），豎瞳照資料畫，**鱗脊在 dragonQ 時不畫**（會和額頭那片菱形鱗疊在一起）；背刺照畫（正面、側面被身體擋住，背面露在背上）。樣張龍裔第 7 版是拿掉豎瞳的，和規格「豎瞳」相反，請美術 PM 確認。
4. **戰場上的人變小**：Q 版身高 38（頭頂）比 C 的 53 矮，`DOLL_SCALE` 0.92 沒動，戰場上的人看起來小一號（見 `qk1_battle_1600_zoom.jpg`）。要不要把 Q 版的戰場縮放調大（例如 ×53/46），請美術 PM 決定。
5. **Q 版還不會畫的部件**（不出錯、直接不畫，QK-3 補）：拂塵、符紙、傀儡線、藥葫蘆、木偶箱、腰掛黃符、圍裙、劍穗、白羽披肩。赤膊先畫成膚色上衣。槍的 trident／halberd 形制、杖的權杖／圖騰／魔杖形制照 `QW` 只有一種畫法。
6. **雙手武器的出招片段**：Q 版專用關鍵姿勢（`atk`、`bowAim`）已能畫（畫廊 a、g、b 列），但戰鬥的出招片段仍是 6M／6N（給 `wpn`），沒有改成驅動 `atk`——那會改姿勢片段，超出本段。要不要在 QK-5 接上請 PM 決定。
7. **貼圖成本**：Q 版每張貼圖要多做一次 12 方向膨脹（離屏 3 倍）。實機戰場、主城看不出卡頓，但片段格數多時第一次產生貼圖會比 C 慢；有需要再把離屏框從 128×112 縮到實際需要的大小。
8. **頭像、形態、異形、召喚物的人形部分**：頭像（`portrait.ts`）和事件插圖仍呼叫 `drawFigure`，所以已經自動變成 Q 版的身體（頭像配件還是 C 的座標，QK-2 重做）；建角頁預覽也是 Q 版（QK-2 恢復暫停畫面時一起看）。
9. 0.3 節三點都是照規則畫的，請美術 PM 在並排圖 `r01`、`i15`、`a14`、`g1～g3`、`r03`／`r04`／`r08` 西、`r09`、`i02`、`a01～a04` 看。

## 8. 下一步

QK-1 做完。照需求第 1 節：先交美術 PM 與使用者看畫廊（`doll-gallery.html?skin=q`）和走路連拍，確認「是這個味道」再開 QK-2。

## QK-1b：QK-1 驗收退回的修正（`docs/art/QK-1檢查.md`）

> 實作者：worktree `dev/qk1b`（從 main `2e92c5ad` 開）。沒有 push、沒有 rebase。

### 1. 各項

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 雙手劍遠側手接暗一階的前臂 | **QK-1 的 `gsFarSleeve` 沒生效的原因**：它在近側手臂畫完後，把遠側手臂剪裁在「近側手臂中線往上 1.2」那一側再畫一次。(a) 出招（`a14`、`g1～g3`）遠側拳頭其實在近側手臂中線的**下方**，剪裁區裡沒有遠側手臂，等於什麼都沒畫；遠側手臂本來那一次又被 `x > 3.2` 剪掉，只剩近側手臂邊上一條細縫。(b) 拄劍、待機（`r01`、`i15`）遠側拳頭在上方、條件成立也有畫，但露出來的那條在下巴高度，被之後才畫的頭蓋掉，剩下的又被拳頭蓋住。改法：用外積判斷遠側拳頭在近側手臂哪一邊——**下方**（出招）→ 遠側手臂整隻畫在胸前（不剪 `x > 3.2`）、在近側手臂之下，看得到暗一階的上臂＋前臂接到拳頭；**上方**（拄劍、待機）→ 近側手臂畫好後，從肩到拳頭補一段打直的暗袖子（剪 `x > 3.2`），蓋在近側上臂上緣、頭之下 | `b91356c9` |
| 2 | 朝西遠側握長柄的手 | 肩點後移維持 1.4，另外**肩點往下移 2.5**（`WEST_FAR_DROP`，`SideArm.dy`），手臂重新瞄準原本的拳頭位置、按比例伸長；拳頭與柄位置不動。上臂上緣離開下巴，中間露出身體前緣與外框 | `81464d6e` |
| 3 | 「杖＋書」不套肩點後移 | 有副手（書）的杖不走第 2 項；`r10` 西、`parts/s11_05` 回到和樣張一致。`r08` 西的小圓頭（遠側上臂的肩頭圓角從下巴邊冒出來）在第 2 項把肩點下移後消失 | `0b36c627` |
| 4 | 四指握法柄尾從拳頭下緣穿出 | `swordGrip` 先畫柄尾（武器座標 y 1～3.9，拳頭半徑 2.4，露出 1.5），再畫四指；正面、背面照武器原點（`swOff`）畫 | `3ffa90ae` |
| 5 | 匕首、成對武器四指握法 | `GRIP` 表加 `dagger`、`paired`（柄寬 1.6）；成對武器副手那把（正面、背面、側面）也畫。鞭不改。`swOff`（劍往外偏 1）仍只給劍類，匕首位置不動 | `85b76133` |
| 6 | 龍裔豎瞳 | `Q_RACES` 的龍裔加 `slitEyes`（畫法照樣張 `raceArt.js` 的 `slitEyes`：金色橢圓＋黑色豎線）。遊戲資料的龍裔本來就是 `slit_eyes: true`，遊戲畫面 QK-1 起就有 | `ca6cb430` |

另：dev 畫廊加 `doll-gallery.html?skin=q&set=extra`（匕首、成對武器、劍、龍裔各四方向，樣張沒有的補拍格，`d10ab343`）；快照重產 `a47c41c0`。

### 2. 並排圖（`docs/art/shots/qk1/compare_v2/`，56 張 jpg，共 3 MB）

- `<項次>_<key|parts>_<格>.jpg`：左樣張、右 QK-1b。
- `<項次>_<key|parts>_<格>_zoom3.jpg`：變動區域 3 倍放大，**左樣張｜中 QK-1｜右 QK-1b**。
- 第 1 項：`a14`、`r01` 東西、`i15` 兩格、`g1～g3`；第 2 項：`r03`、`r04`、`r08` 西；第 3 項：`r10` 西、`parts/s11_05`；第 4 項：`i01～i04` 各兩格、`r09` 正面；第 5 項：`a04`、`i05` 兩格；第 6 項：`parts/s03_04`。
- `extra_x01_dagger.jpg`、`extra_x02_paired.jpg`（四指握法四方向）、`extra_x03_sword.jpg`（柄尾四方向）、`extra_x04_dragonkin.jpg`（豎瞳四方向）。
- 這次出圖改用 Playwright 開系統 Chrome（GPU）；無頭 `--disable-gpu` 在這台 Mac 上一格要 90 秒。反鋸齒和 QK-1 的出圖略有差（例如 `a08` 0.23% → 0.29%、`s06_04` 0 → 0.06%），所以下表另用同一環境把 QK-1（`2e92c5ad`）重出一次當基準。

### 3. 鎖格 13 格（同一環境：QK-1 → QK-1b）

| 鎖格 | QK-1 | QK-1b | 說明 |
|---|---|---|---|
| a08、a09、a11、b4、b5、b6、i09 兩格、`parts/s06_04` | 不變 | 不變 | 只有反鋸齒（0.06～0.66%） |
| i02_sword_shield_mid | 0.60% | 0.66% | 第 4 項柄尾 |
| i02_sword_shield_start | 0.63% | 0.69% | 第 4 項柄尾 |
| r09_sword-shield_east | 0.72% | 0.79% | 第 4 項柄尾 |
| r09_sword-shield_west | 0.41% | 0.41% | 不變（劍在遠側、身體後面） |

QK-1 → QK-1b 有變的格子（差 > 0.01%）：key `a01～a04`、`a14`、`g1～g3`、`i01～i05`（各兩格）、`i15` 兩格、`r01` 東西、`r03`／`r04`／`r08`／`r10` 西、`r09` 正背東；parts `s03_04`（豎瞳）、`s11_01～s11_04`（劍盾柄尾）、`s11_05`（回到樣張）。

### 4. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 251 檔、3152 項全過（`qSelfTest` 9 項、`inkWeaponFrame` 照過） |
| 快照重產 | `client/src/render/__snapshots__/inkDollSnapshot.test.ts.snap`（5 組：人形範本、10 族、各欄位、武器、體型；柄尾、朝西長柄、雙手劍遠側手） |
| `tsc --noEmit`、build | 過 |
| Python | 沒動，沒跑 |

### 5. 待 PM 決定

1. **拄劍、待機的遠側袖子仍偏淡**：照「暗一階」（0.12）畫，3 倍圖看得到暗袖子接進上面那隻拳頭（`1_key_r01_gs-plant_east_zoom3.jpg`），但上方被下巴、右邊被拳頭夾住，只露約 2 單位。要更明顯可以加深（例如 0.2）或讓袖子再往左延伸到肩；請美術 PM 看圖決定。左端在 `x = 3.2` 是直切（和其他遠側手臂同一條身體前緣）。
2. **出招時遠側手臂整隻畫在胸前**（上臂從肩往下、前臂折回拳頭），是「遠側手臂伸到身體前方」的畫法；肩頭和近側肩頭疊在一起。
3. **龍裔豎瞳的顏色**照樣張 `slitEyes`（金色、發一點光），第 7 版審查說過「金色豎瞳…像貓」；要改成琥珀色（`look.eyes`）不發光，改一處即可。
4. 背面的劍、匕首也畫四指與柄尾（和 QK-1 背面四指一致）。

## QK-1c：QK-1 結案前的最後兩項（`docs/art/QK-1檢查.md` 第 4 節決定）

> 實作者：worktree `dev/qk1c`（從 main `98148515` 開）。沒有 push、沒有 rebase。

### 1. 各項

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 拄劍、待機的雙手劍遠側暗袖子 | `gsFarSleeve` 不再是「肩到拳頭打直、剪在 `x > 3.2`」：改用 `ik(肩點, 遠側拳頭, "down")`，上臂、前臂各取肩到拳頭距離的 0.75 倍（`GS_SLEEVE_SAG`），從肩點往下垂出手肘、再折回拳頭；剪裁改從肩點 `x = sx` 起（`sideArm` 新的 `"sleeve"` 模式），暗度 0.2（`GS_SLEEVE_DARK`）。仍畫在近側手臂之後、頭之前，所以手肘那段會蓋住近側前臂上緣一點。出招（遠側拳頭在下方，`gsFar` = `"chest"`）沒動 | `19fe6717` |
| 2 | 龍裔豎瞳 | `qRace.ts`：拿掉 `shadowColor`／`shadowBlur`（不發光），橢圓色由 `#ffcf4a` 改成 `look.eyes`（龍裔 `#9a4a12`，即樣張 `raceArt.js` 的琥珀色）；黑色豎線不變 | `773fc1f2` |

快照重產 `b9a3f980`。

### 2. 並排圖（`docs/art/shots/qk1/compare_v3/`，10 張 jpg，共 752 KB）

- `1_key_<格>.jpg`：左樣張、右 QK-1c；`1_key_<格>_zoom3.jpg`：**左樣張｜中 QK-1b｜右 QK-1c**（3 倍）。格子：`r01_gs-plant_east`、`r01_gs-plant_west`、`i15_greatsword_mid`、`i15_greatsword_start`。
- `2_extra_x04_dragonkin.jpg`：龍裔四方向，上 QK-1b、下 QK-1c；`2_extra_x04_dragonkin_zoom3.jpg`：臉部 3 倍（左 QK-1b｜右 QK-1c）。樣張第 7 版沒有豎瞳，所以這張不放樣張。
- 出圖方式同 QK-1b（Playwright＋系統 Chrome，`?skin=q&set=key|extra&only=…&dump=1`）；QK-1b 基準在同一環境、改動前先出。

### 3. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 251 檔、3152 項全過 |
| 快照重產 | `client/src/render/__snapshots__/inkDollSnapshot.test.ts.snap`（2 組：10 族〔豎瞳〕、武器〔雙手劍遠側袖子〕） |
| `tsc --noEmit`、build | 過 |
| Python | 沒動，沒跑 |

### 4. 待 PM 決定

1. 舊的 ink 紙娃娃（`inkRace.ts` 的 `drawEye`）豎瞳仍是金色 `#e8b830`（本來就不發光）；這次只改 Q 版。要一起改成琥珀色請說。
