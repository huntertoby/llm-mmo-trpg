# Phase QK-5 報告：片段微調、出招接 Q 版姿勢、正面／背面走路與五類攻擊、戰場人物放大 1.15 倍、累積追加項

> 實作者：worktree `dev/qk5`（從 main `532a3903` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md` 第 0 節、第 6 節；真相來源 `docs/art/sample/qAnimFB.js`、`q-anim-fb.html`、`shots/anim/q-fb-strip.png`、`qDoll.js` 的 `POSE.fb`／`fbApiOf`。照點列改寫進 client，沒有 import 樣張程式。規則、資料、存檔、重播沒動（Python 沒改）。

## 1. 完成表

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 正面／背面五類攻擊（劍、長槍、弓、法杖、拳） | 新檔 `render/qAnimFB.ts`：樣張 `C` 表 5 類 × 正背 × 7 關鍵幀照搬（數值不改），寫成資料（手的目標、打直／IK、手肘方向、起伏、抬腳、杖頭光、ops）。三層 under／over／top 由 `qDoll.drawBody` 在身體之前、身體之後頭之前、頭之後呼叫（同樣張 `POSE.fb`），畫圖工具照 `fbApiOf`（手臂彎肘兩段描邊、打直一圈；武器 2×2 縮短；斜看的弓）。正面作用端放大（槍頭 1.5～2 倍、拳頭 1.4→2 倍、杖頭 1.45）、背面只露尖端、背面箭被頭擋住都照樣張 ops。**插值**：`fbt`（0～6 連續）在相鄰兩幀間內插手的目標、起伏、抬腳、光、武器角度（走最短邊）、縮短比例、槍長、弓弦；兩幀圖層結構不同時過半換結構。副手有盾、書、法球時畫在副手上（正面在副手臂之後、背面在身體之前） | `36e03711` |
| 1 | 背面前傾 | 背面五類幀 0→6：0、0.05、0.08、0.10、**0.12（命中）**、0.05、0（收招回正）。畫法：腰以上以髖為軸往上拉長 `1＋0.5×傾角`（相機在後上方，往遠處傾時頭往畫面上方移），腿另外抵銷（見待決 1） | `36e03711` |
| 1 | 接到戰場 | `skillSequence` 的蓄力、出招、收勢三列帶 `fb`（類別由武器種類＋施放方式決定：劍／刀／斧／鎚／匕首／雙手劍／魔導劍近戰＝劍；長槍近戰；拳套與空手近戰＝拳；弓遠程；法杖遠程）。`BattleRenderer` 只在 Q 版、施放者朝南／朝北時改畫關鍵幀：蓄力 0→2、出招 2→4（命中點）→6、收勢停 6 過半回站好；片段時間照舊量化 16 格。特效起點（飛行物、射線）照關鍵幀的作用端：弓正面從胸前、背面從頭頂上方飛出 | `106b7f30` |
| 1 | 出招接 Q 版關鍵姿勢 `atk`、`bowAim`（側面） | `qAnimFB.qKeyAttackPose`：雙手劍蓄力 atk 0→0.5（舉到臉前上方）、出招到命中 →1（劈）；長槍、鐮 0→0.35→1；弩、火槍蓄力即瞄準 1；弓蓄力 bowAim 0→1、拉弦 0→4，命中（放箭）放開。手臂、武器改由關鍵姿勢決定，身體前傾、跨步、起伏照片段。`InkPose` 加 `atk`、`bowAim`、`fbk`、`fbt`（排在最後，舊貼圖鍵不變） | `95f0a241` |
| 1 | 走路小修 | 雙手劍側面走路改「提劍」（atk 0：雙手握柄、劍往前上斜，擺幅 ×0.25），不再拄劍斜穿小腿；法杖、拄地長柄走路手臂擺幅減半、杖身只跟著轉 0.3。正面、背面走路本來就照樣張（抬腳＋起伏＋兩手上下），並排圖逐格對過 | `6364f9ea` |
| 1 | 腿短片段微調 | Q 版專用的收斂 `qSpec.qLegFit`（C 畫法、片段資料不動）：膝 ≤ 0.9、髖 −0.7～0.75、往下沉的 bob ×0.6 最多 3.2；另外 `qDoll` 在 bob > 0 時腿往上抵銷（腳留在地上，大腿收到身體後面）。涵蓋跳躍收腿（leap_air）、蹲低（crouch_place、kneel_lift、press_lower、閃避蹲低）、跪地（stab_ground、ground_punch、palm_ground、rally_up）、掃腿、跺腳、倒下前膝軟、陷阱夾住等。獸躍弧度在 `motionClips`（6R-1c 定案：從較高一端往上 14＋級差×6），本段沒動，只換姿勢 | `70f5e908` |
| 1 | 戰場人物放大 1.15 倍 | `DOLL_SCALE` 0.92 → **1.06**。形態、召喚物、異形的縮放也乘這個常數，一起放大（比例不變）。巫師帽＋彎角最高 59.3 單位（量的，含外框）→ 頭頂超出本格上緣約 23px（48px 格），在 28 的頭頂預留內；HP 條、狀態列、朝向三角形、徽章都照 `DOLL_SCALE` 算，實機看不出錯位。紙娃娃畫布 `DOLL_H` 88 → 92（腳底下多留 4：正面長槍刺向鏡頭時槍頭到腳底下 +8.5） | `d74066a2`、`106b7f30` |
| 1 | 龍（1.5）、巨人（1.45）形態 | 放大後龍頭頂 75 單位會超出頭頂預留（最上排被切）。`inkForm.formScale` 加上限：頭頂不超過預留（52px 格 68.3 單位）→ 龍實際 ×1.44、巨人 ×1.49（仍比放大前的 1.38、1.33 大），其他形態照 1.06 × size。龍、巨人仍會伸進上一格（QK-3 起就是），蓋到上一排的 HP 條下緣 | `4d03af93` |
| 2 | 開場醒來插圖 | `qDoll` 側面空著的手吃臂長加量 `reach`／`reachF`（只有這一格用）。Q 版半坐起：後仰 0.6（約 34°，原本 46°），近側手 arm 0.98、reach 0.26，遠側 armF 1.23、reachF 0.45：兩手打直往後撐在地面線上（近側在髖後約 9.5、遠側再往後 4）；髖 −0.5 腿平貼。半坐起那格地面以下不畫（龍裔等的尾巴不穿地，手、屁股的外框留 1.5） | `0386c144` |
| 2 | 異形攻擊命中對齊出手格（QK-4 待決 2） | `qCreatureAnim.creatureAttackHitU`：照戰場量化（12 格）逐格找第一個出現出手特效（揮爪、咬合、震地環、爆開、雷、射線、吐息、火焰、碎晶、落石、任何飛向目標的特效）的格；沒有就取往前推最遠那格。`skillSequence` 新增 `StrikeOf`：施放者是異形時，出招那一列＝異形片段原長，命中點＝出手格，蓄力列不播；特效、扣血、停頓照命中點對齊（`viewGrip.creatureStrikeInView` 照 `before` 畫面算，純函式）。頭目照舊（見待決 4） | `e212ac61` |
| 2 | 人形詞綴位置 | `HUMANOID_FX`（QK-4 改成 Q 頭頂 −38）是虛擬單位、跟著 `DOLL_SCALE` 放大，沒改 | — |
| 2 | QK-6 補拍 | 竹林種子 392：盜賊 ×3（unit_0004～0006）外觀各不同（鬍子、膚色、髮型）；同種子重開，同一個 id 外觀相同（地圖區差異 0.77%，只有待機動作的時間差） | `2ab8bd6d` |
| 追加 | 規則武器 `fist` ＝空手 | `qSpec.qUnitOf`：主手、副手 kind `fist` 不傳給 Q 版（畫空手拳頭，赤膊武僧不戴拳套）；拳套只給 `gauntlet`。規則資料不動 | `4f9e8ca9` |
| 追加 | QK-8 小修 1、2 | 見第 6 節 | `e29652a7` |
| 3 | 快照、gif、截圖 | 見第 3、4 節 | `2ab8bd6d`、`4b19bfdf` |

dev 畫廊：`doll-gallery.html?skin=q&set=fb`（關鍵幀；`&steps=25` 插值格；`window.__qkFb.cell(kind, view, u)`）、`&legs=1`（腿短收斂前後）、`&align=1`（異形命中對齊）；`skill-gallery.html#fb`（正式串接器＋繪製器，上排朝南、下排朝北五類）。

## 2. 改到清單外的檔（都很小）

- `battle/playback.ts`、`battle/viewGrip.ts`、`screens/battle/usePlayback.ts`：把異形片段時間（`StrikeOf`）接進播放計畫（多一個選填參數）。
- `render/inkForm.ts`（＋測試）：龍、巨人形態縮放上限。
- `render/summonArt.test.ts` 一行字面值（召喚物光環半徑 22.9 → 20.26，因為 `TEAM_RING_U` 本來就用 `DOLL_SCALE` 算）；`summonArt.ts` 沒動。QK-2b／3b 合併時若同一行有衝突，取 20.26。
- 測試斷言改值（意圖不變）：`inkDoll.test.ts`、`artTextures.test.ts`（DOLL_SCALE 1.06）、`battle/uiT1.test.ts`（頭頂預留改量 Q 版最高頭頂 60）、`eventArtAwakenQ.test.ts`（Q 版改用 reach、後仰 34°）、`inkForm.test.ts`。

## 3. 截圖（`docs/art/shots/qk5/`）

- **五類 × 正背關鍵幀並排**（上樣板 `qAnimFB.js`、下遊戲）：`compare/fb_{sword,spear,bow,staff,gauntlet}_{front,back}.jpg`，另 `compare/fb_walk_{front,back}.jpg`。特效、傷害數字是戰場另畫的，遊戲那列不畫。
- **插值連拍**：`qk5_fb_game_interp.gif`（10 列 × 25 格，0→6 連續）。
- **實機連拍**：`qk5_live_fb_burst.jpg`（`skill-gallery#fb`，0～1100ms 每 120ms 一張；上排朝南、下排朝北）。
- **放大 1.15**：`qk5_battle_scale_1600.jpg`、`_1040.jpg`、`_800.jpg`、`_1600_zoom3.jpg`（角盔頭目、弓手、HP 條、朝向三角形）；`qk5_forms_scale_south.jpg`（形態一覽）。
- **醒來插圖**：`qk5_awaken_3races.jpg`（人類、矮人、龍裔 × 躺／坐）、`qk5_awaken_sit_zoom.jpg`。
- **異形命中對齊前後**：`compare/creature_hit_align_before_after.jpg`（16 款普攻，扣血那一刻：左 QK-4、右 QK-5）。
- **QK-6 補拍**：`qk5_qk6_same_template_1600.jpg`、`qk5_qk6_same_template_zoom3.jpg`。
- 走路小修前後：`qk5_walk_fix_before_after.jpg`；腿短收斂：`qk5_short_legs_fit.jpg`；護法武僧空手：`qk5_fist_warrior_monk_4dir.jpg`。

出圖：Playwright＋系統 Chrome（`vite --port 5191`、`trpg serve --port 8147`、樣張 `http.server 8166`），腳本在 scratchpad。

## 4. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 261 檔、3213 項全過（`qSelfTest`、`inkWeaponFrame`、`idleWeapons`、`qCreatureAnim` 照過、沒改） |
| 新測試 | `qAnimFB.test.ts`（9 項：7 幀與背面前傾範圍、插值連續、每 0.25 幀作用端在畫布內與武器有畫、確定性、正背不是鏡像、沒給 fbk 不變、類別對照與時間對照、技能時間軸帶 fb、側面 atk／bowAim、腿短收斂）、`battle/creatureStrike.test.ts`（16 款攻擊出手格、時間軸對齊）、`qFist.test.ts`、`qGearTrim.test.ts` |
| 快照重產 | `render/__snapshots__/inkDollSnapshot.test.ts.snap`：`weapons` 的 `fist`、`pair:fist・claw`（空手）；單位範本 12 個修士（長袍邊色、念珠）；`neck:beads` |
| `tsc --noEmit`、`vite build` | 過（只有原本的 chunk 大小提醒） |
| 排版煙霧 1600×900、1040×624、800×600 | 三個都 13 PASS、0 FAIL |
| 6.5.1 | 本段沒有新增浮動卡；煙霧檢查的滑入、說明卡、更多動作選單照過 |
| Python | 沒動，沒跑 |

## 5. 待 PM 決定

1. **背面前傾的畫法**：側面那種「以髖旋轉」在背面會變成往左右歪，所以照相機在後上方的透視，畫成腰以上往上拉長 `1＋0.5×傾角`（命中 0.12 → 頭往上約 1 像素）。看起來偏含蓄；要更明顯可加大係數，或改成整個上身往畫面上方平移。請美術 PM 看 `compare/fb_*_back.jpg` 第 3～5 格。
2. **正背五類只接這些組合**：劍類（劍、刀、斧、鎚、匕首、雙手劍、魔導劍）近戰、長槍近戰、拳／空手近戰、弓遠程、法杖遠程。成對武器、鐮、鞭、弩、火槍、法球，以及自身、地面施放，朝南北時照舊（armL／armR 上下位移）。雙手劍朝南北也用「劍」那組（單手揮），樣張沒有雙手劍的正背幀。
3. **特效位置**：戰場特效（揮砍弧、火花、傷害數字）本來就畫在目標身上與頭頂，沒有照樣張逐格搬；只有飛行物、射線的起點改用關鍵幀的作用端。樣張「箭越飛越小／越大」戰場沒做。
4. **頭目的攻擊片段**沒做命中對齊（頭目片段由 `qBoss` 依階段挑，另有時間表），照舊塞進出招列。
5. **徽章避臉的頭部圓**（`badgeLayout.FACE`）仍是 C 版的頭位置與 0.92；試過改成 Q 版＋1.06，20 個徽章排版測試（6F-12～6F-19 的情境）會變，保守沒改。實機看不出徽章蓋臉，要改請排段。
6. **龍、巨人形態縮放上限**：為了不超出頭頂預留 28，這兩種只放大到 ×1.44、×1.49（其他形態 ×1.06×size）。要整個照 1.15 就得把頭頂預留調高。
7. **戰場上的人形全部變大後**，最上排的人頭頂、高帽離畫布上緣更近（仍在預留內）；QK-1 的 `DOLL_H` 64 選做仍沒做（這次反而加到 92）。
8. **盜賊畫廊弓手改拿弓**（QK-6 可選）沒做：在畫廊試加 `weaponId: "bow"`，資料解析出來是弓，但畫廊格仍畫劍，原因沒查完，已還原；實機戰場的盜賊弓手是拿弓的（`qk5_battle_scale_1600_zoom3.jpg`）。

## 6. QK-8 小修 1、2（美術 PM QK-8 驗收，QK-5 一起做）

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 長袍邊色 | `qGear.body` 長袍前襟、下擺、側緣改讀 `look.trim ?? it.trim ?? 暗色`：霧鎖真人金邊 `#e8bb48`、小蓮竹青邊 `#6aa84a` 正確 | `e29652a7` |
| 2 | 護法武僧 | 空手拳頭（見完成表「規則武器 fist」，`4f9e8ca9`）；念珠沒指定顏色時用樣張 `qNpc.js` 的深褐 `#6a3a22`（`qGear.BEAD_COLOR`，不走木頭材質色） | `e29652a7` |

- 測試：`render/qGearTrim.test.ts`（長袍 trim 三方向、外觀 trim 優先、霧鎖真人 content 金邊傳到 Q 版、念珠四方向深褐、有指定顏色照用）。快照重產見第 4 節。
- 補拍（`docs/art/shots/qk8/compare_v2/`）：`monk_sect_mist_lock_master_4dir.jpg`、`npc_acolyte_xiaolian_4dir.jpg`、`monk_sect_warrior_monk_4dir.jpg`（qk8 畫廊同版面、3 倍、四方向）。

## 7. Commit

`4f9e8ca9`、`36e03711`、`106b7f30`、`95f0a241`、`6364f9ea`、`70f5e908`、`d74066a2`、`0386c144`、`e212ac61`、`e29652a7`、`2ab8bd6d`、`4d03af93`、`4b19bfdf`＋本報告。
