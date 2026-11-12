# Phase QK-2 報告：Q 版頭像、頭像配件跟著體型、重拍頭像類、恢復暫停的畫面

> 實作者：worktree `dev/qk2`（從 main `5dd15774` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md` 第 0、3 節；真相來源 `docs/art/sample/qPortrait.js`、`q-portraits.html`（＋頭像用到的 `qNpc.js` 的 `prep`、`PART`、`stamp`、`skinMask`）。不改規則、資料、存檔、重播；沒動 `qDoll.ts`、`qHead.ts`、`qGear*`、`inkCreature`、`creaturePose`、`summonArt`、`inkForm`。

## 1. 完成表

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 頭像 | 新檔 `client/src/render/qPortrait.ts`：Q 版紙娃娃正面（`drawQ`，不描外框）＋頭像部件，B（身後）＋本體＋C（和本體一起描）三層合起來描同一圈 1.3 單位剪影外框；D 層（表情、義眼、符文、霧、十字）蓋在外框之後。每 42 單位對應邊長、頭心在 0.53。離屏至少 192px 取樣（小的從 192 縮下來，同樣張），並照目前畫布縮放加倍。`portrait.ts` 改成 Q 版（剪影、框線照樣張的內縮畫法），沒有 DOM 時直接畫填色（vitest 用） | `1bdce2bf` |
| 1 | 好感五級 | 換眼、眉、嘴（被護目鏡、義眼、餘燼眼、面紗遮住的不換，配件畫在表情上面）；`drawMoodBadge` 頭頂徽章五級五色。遊戲接線：NPC 面板頭像（`HudNpcPanel` 48px）帶表情；`RankFace`（場上 NPC 頭頂、NPC 面板角落）換成 Q 版徽章 | `1bdce2bf`、`83ab969c` |
| 2 | 頭像配件 23 個 | 全部照 `qPortrait.js` 的點列：外框層（earring、coral、crest、circlet、戴帽時的 goggles、post_badge＋部件 douli〔wide_hat〕、headband、goggles_up、fur_collar、mailbag）；臉上（scar、wrinkles、soot、ember_eye、cyber_eye、rune、mist、apron_cross）；fox 整張狐臉。沒戴帽時 cap／bandana／goggles 換成 Q 版頭部裝備、mustache 換成鬍子樣式（`qPortraitPrep`＝樣張 `QNpc.prep`） | `1bdce2bf` |
| 3 | 配件跟著體型 | 配件層先套 build（stout 1.12×0.88、tall 0.96×1.1）與 frame 再畫；頭心高度跟著 build 算。疤、皺紋、煤灰只畫在臉的皮膚區域（本體填色層裡膚色 ±26 的像素，扣掉頭髮、帽、鏡片、鬍子；6T-1d 決定）。驗收圖 `docs/art/shots/qk2/qk2_build_192.jpg`（老鐵標準、灰鴿 tall、鉚釘與爐叔 stout，左樣張右遊戲） | `1bdce2bf` |
| 4 | 重拍 | 37 位頭像逐張並排、好感五級並排（`docs/art/shots/qk2/compare/`）；遇敵卡頭像（UI-E3b 裁法 36px、上半身 62% 照舊，`enemyThumb.tsx` 沒改，本來就走 Q 版紙娃娃）；種族卡 10 族（新的 `client/src/run/raceFace.ts`：該族預設外觀＋預覽布衣，用同一套頭像畫法，框色＝發源區） | `21c3cd75`、`ebb89683` |
| 5 | 恢復暫停畫面 | **建角頁**：種族卡補上頭像（`RaceOriginPicker` 的 `RaceFace`，52px；沒有 DOM 時留原本的空框）；預覽（`LookPreview`）QK-1 起已是 Q 版，照用。**主城開場 ①**：`eventArtAwaken.ts` 加 Q 版擺法 `AWAKEN_HERO_Q`／`AWAKEN_SIT_POSE_Q`（見第 2 節），躺姿與位置不動。**靶場 ②③**：見待決 1 | `21c3cd75`、`b9eea94a` |

dev 畫廊：`client/story-gallery.html#qportraits`（37 位 96px、192px 體型、好感五級＋徽章、56／28px、種族卡；`window.__qp(id, size, level)`、`window.__qrace(race, size)` 給出圖腳本）；`client/event-art-gallery.html?mode=awaken`（醒來插圖 × 人類／矮人／龍裔；`&pose=hipN,lean,arm,armF,drop` 調姿勢用）。

## 2. 開場半坐起（Q 版）

Q 版骨架和 C 有兩點不同：髖角正值是往後（C 是往前），而且 `lean` 會連腿一起繞髖轉。所以 Q 版用 `hipN/hipF −0.6` 把後仰抵掉、腿平貼地面；Q 版腿短、髖在 −9，往下放 4.5 屁股就貼地。Q 版手臂只到腰（肩到手約 10.5），C 的 `reach`（拉長臂長）Q 版骨架沒有、`qDoll.ts` 不能改，所以上身後仰改成約 46°（C 是 34°），兩手（`arm 0.75`、遠側 `armF 1.3` 再往後）剛好往後撐到地面。並排看 `docs/art/shots/qk2/qk2_awaken_q_3races.jpg`。

## 3. 並排比對（左樣張、右遊戲，192px）

37 位逐張像素差（任一通道差 > 24 的像素占比）：大多 0.4～1.6%，差在遊戲的裝備色走材質色表（`itemColors`）、主城框色（見待決 3）與反鋸齒。差比較大的：

| 頭像 | 差 | 原因 |
|---|---|---|
| 小蓮 | 14.9% | 樣張用★示範配色（月白袍、粉髮帶），規格寫不實作；遊戲照 content（淺綠袍、綠髮帶） |
| 鍛疤 | 12.3% | 板甲色：遊戲照材質色表（較亮的鋼），樣張是暗鐵色 |
| 守池人 | 6.6% | 法球光暈大小（遊戲的元素色＋光暈照 QK-1 的 `pdHeld`） |
| 郵差 3 位 | 2.2～3.0% | 樣張有帽徽 `post_badge`、郵袋 `mailbag`，content 沒寫（待決 2）；遊戲兩個配件都會畫 |
| 爐叔 | 1.8% | 樣張赤膊是 QK-8 的 `body.kind: bare`（內線、腋下陰影），遊戲照 QK-1 的 `qSpec` 畫成膚色上衣 |

## 4. 測試、快照與驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 253 檔、3165 項全過（含 `qSelfTest.test.ts`、`inkWeaponFrame.test.ts` 照舊） |
| 快照重產 | **沒有**（沒有快照變動） |
| 改寫的測試 | `client/src/render/portrait.test.ts`：6T-1d soot 的 C 座標斷言與 RT-4 四個配件的 C 座標斷言改成 Q 版（42 單位／0.53、soot 裁在臉的皮膚區域且在右頰、配件在 build 之後畫、23 個配件都畫得出來、好感五級互不相同、被遮住的不換、徽章五色、`qPortraitPrep` 換算、級別對照）；框色、傭兵 9 位、快取鍵的斷言照舊 |
| 新測試 | `client/src/render/eventArtAwakenQ.test.ts`（Q 版醒來擺法；C 的擺法照舊鎖在 `capitalOpeningReview.test.ts`） |
| `tsc --noEmit`、`vite build` | 過 |
| 排版煙霧（`__layoutSmoke.runCase`，`?dev=1&anim=0.1`） | 1600×900、1040×624、800×600 都 13 PASS、0 FAIL |
| 6.5.1 實測（建角頁種族卡的說明卡） | 1600×900、800×600：滑過開卡 → 滑進卡片 → 捲到底 → 點一下釘住（滑鼠離開仍在）→ Esc 關閉，全部正常 |
| Python | 沒改伺服器、資料，沒跑 pytest |

## 5. 截圖（`docs/art/shots/qk2/`，10 張 jpg 80，最大 243 KB）

- `docs/art/shots/qk2/qk2_create_1600.jpg`：建角頁（種族卡 10 族頭像、龍裔預覽）。
- `docs/art/shots/qk2/qk2_create_races_800.jpg`：800×600 種族卡。
- `docs/art/shots/qk2/qk2_awaken_1600.jpg`、`docs/art/shots/qk2/qk2_awaken_800.jpg`：主城開場 ① 醒來（半坐起）＋說書人頭像、隊友頭像。
- `docs/art/shots/qk2/qk2_awaken_q_3races.jpg`：醒來插圖 3 倍（人類、矮人、龍裔 × 躺著、半坐起；畫廊）。
- `docs/art/shots/qk2/qk2_npc_1600.jpg`、`docs/art/shots/qk2/qk2_npc_800.jpg`：主城守印人公告板的頭像。
- `docs/art/shots/qk2/qk2_encounter_zoom3.jpg`：遇敵卡頭像（頭目霧鎖真人、劍陣弟子、陣眼石靈；畫廊 `story-gallery.html#encounter-boss`，3 倍）。
- `docs/art/shots/qk2/qk2_portraits_gallery.jpg`：遊戲畫的頭像總表（37 位、體型、好感五級＋徽章、56／28px、種族卡）。
- `docs/art/shots/qk2/qk2_build_192.jpg`：配件體型驗收 192px（左樣張右遊戲）。
- 並排：`docs/art/shots/qk2/compare/qk2_portraits_01～04.jpg`（37 位，每頁 12 位）、`docs/art/shots/qk2/compare/qk2_levels.jpg`（好感五級 × 3 位）、`docs/art/shots/qk2/compare/<id>.jpg`（逐張 192px）。

## 6. 待 PM 決定

1. **靶場 ②③ 人物試用畫面不存在**：#134 靶場（`docs/art/靶場移植需求.md`，約 1.25 段）還沒實作，client 裡沒有這兩個畫面可恢復；戰鬥裡的主角本來就走 Q 版（QK-1 戰場截圖）。暫停清單上「恢復開工」的意思應是可以排 #134 了，請 PM 排段。
2. **郵差帽徽 `post_badge`、郵袋 `mailbag`**：畫法做好了（23 個配件都在），但 content 的郵差 `extras` 沒寫（樣張註明「content 還沒寫」）。照「不改資料」沒加；要的話在 `content/world/trade.yaml` 三位郵差的 `extras` 加上即可。
3. **主城頭像框色**：規格寫「框色照 RT-1」，現行（RT-4／capitalFigures 測試鎖住）主城是傭兵金 `#c8a868`；樣張主城是金 `#d9b24a`＋紫灰底；`region_themes.yaml` 的 capital `portrait_ring` 是紫 `#a898ff`。照最保守沿用現行傭兵金。晶冠、樞市、霜潮三區的**底色**換成樣張的（框色不變）。
4. **開場半坐起後仰約 46°**（C 是 34°）：Q 版骨架沒有臂長加量，`qDoll.ts` 不能改，只能靠多後仰讓手撐到地面。若要照「拉長臂長」做，需要在 `qDoll.ts` 的側面手臂加 `reach`（只給這一格用），請排給能改 `qDoll.ts` 的段。另外龍裔的尾巴在半坐起時跟著上身轉、往下穿過地面一點（`qk2_awaken_q_3races.jpg` 右下），同屬 `qDoll` 的事。醒來插圖裡的主角沿用 C 的 1.05 倍，Q 版人比 C 矮，看起來小一號（同 QK-1 待決 4 的戰場縮放問題）。
5. **毛領 `fur_collar`**：樣張是 `qDoll` 的頸飾（畫在手臂下）；client 的 `qGear.neckItem` 還不認得（QK-8），這段畫在頭像的外框層、挖掉頭，所以會壓在肩上一點點（阿岳）。QK-8 把頸飾做進 `qDoll` 後可改走頸飾。
6. **赤膊**（爐叔）：照 QK-1 的 `qSpec` 畫成膚色上衣，樣張的赤膊細節（內線、腋下陰影）是 QK-8 的 `body.kind: bare`。
7. **好感表情只接了 NPC 面板頭像**：對話泡泡、事件卡的說話者頭像沒有好感資料，照普通畫。頭頂徽章（場上 NPC、NPC 面板角落）全部換成 Q 版五色（原本 `RANK_FACE` 的臉色只剩中文名還在用）。
8. 種族卡頭像用「該族預設外觀＋預覽的布衣」，框色＝發源區（傭兵金以外照 `PORTRAIT_REGION`）。樣張沒有種族卡頭像，請美術 PM 看 `qk2_create_1600.jpg`。

## QK-2b：驗收後小修（`docs/art/QK-2檢查.md` 小修 1、2，補圖 3、4，決定「主城框色」；另加 QK-8 待決 1）

> worktree `dev/qk23b`（從 main `380eb1bb`，中途 `git merge main` 拿到 QK-8／QK-4，沒有 rebase、沒有 push）。

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 關鍵字浮動卡殘留 | **原因**：建角頁捲回上方時，觸發元素（起始關鍵字按鈕）整個捲出視窗，`FloatCard` 的捲動監聽仍照「往內推」把卡片夾在視窗底邊（y≈828，正好壓到龍裔說明卡），要等 250ms 寬限（滑鼠沒動時瀏覽器也不一定送離開事件）才關；截圖腳本捲動後立刻拍就拍到。已在瀏覽器重現（捲動後 50ms 卡片在 y=827）。**修法**：`floatCard.ts` 加 `anchorOutOfView`、`FloatController.triggerOutOfView()`；`useFloatCard.tsx` 量位置時觸發元素整個在視窗外、卡片沒釘住就立刻關（釘住的照舊）。vitest：`floatCard.test.ts`「QK-2b：觸發元素捲出視窗」4 項 | `1938746b` |
| 2 | 主角頭像改 Q 版 | 新檔 `client/src/ui/heroFace.tsx`（`HeroFace`、`fieldHeroInput`、`unitHeroInput`、`heroRing`）：主角的紙娃娃外觀（範本、`doll_look`〔含外觀選項 `custom`〕、種族外觀〔龍裔的角〕、裝備）走 NPC 頭像同一套（`specFigure`＋`drawPortraitFrame`，不畫武器），框色＝出身區（沒有出身＝傭兵金）。三處：我的角色清單（`WorldCharacterPicker`）、探索 HUD 主角卡（`WorldHud`→`HeroCard`）、戰鬥 HUD 主角卡（`Hud`→`HeroCard`，`BattleScreen` 新 prop `heroOrigin`，大世界與一輪都帶）。後端加純顯示欄位：`WorldCharacterSummary`、`WorldCharacterView` 的 `hero_look`（`FieldHeroView`）與 `origin_realm`，`HeroOut.origin_realm`；重產 `openapi.json`、`schema.d.ts`。測試：`ui/heroFace.test.ts`（9 項）、`tests/api/test_look_api.py::test_hero_face_fields_for_q_portrait`；`sharedPopup.test.ts` 戰鬥主角卡斷言改成 Q 版頭像 | `a20358d9` |
| 3 | 主城框色 | `PORTRAIT_REGION.capital = ["#a898ff", "#2a2a44", "#7a7aa8"]`（框色＝`region_themes.yaml` capital `portrait_ring`；底色用樣張主城紫灰）。`capitalFigures.test.ts` 原本鎖傭兵金 `#c8a868`，改成鎖晶紫；`portrait.test.ts` 加一項（和 `regionThemeFor("capital").portrait_ring` 一致） | `6b3b8304` |
| 4 | 補圖 | 見下 | `9d845218` |
| 追加 | 毛領走頸飾（QK-8 待決 1） | `qPortraitPrep`：`fur_collar` 改成 `gear.neck = {kind: "fur_collar", material: "fur"}`，由 `drawQ` 的 `neckItem`（QK-8 的 `neckWide`）畫在身體那層、手臂與頭下面，不再畫在頭像的外框層；拿掉頭像自己的毛領部件與用不到的 `headClip`。`qDoll.ts`、`qGear*` 沒改。`portrait.test.ts` 加 2 項 | `9246c3d0` |

### 截圖（`docs/art/shots/qk2/`，`_v2`，11 張，jpg 80，最大 205 KB）

- `docs/art/shots/qk2/qk2_create_east_1600_v2.jpg`、`qk2_create_west_1600_v2.jpg`、`qk2_create_back_1600_v2.jpg`：建角頁預覽朝東、朝西、背面（龍裔＋馬尾＋山羊鬍；上方「我的角色」已是 Q 版頭像）。
- `docs/art/shots/qk2/qk2_create_east_800_v2.jpg`：800×600 建角外觀步驟。
- `docs/art/shots/qk2/qk2_npc_1600_v2.jpg`、`qk2_npc_800_v2.jpg`：霧渡鎮渡婆婆的 NPC 面板 48px 頭像（好感表情＋角落徽章）。好感是**截圖時攔截回應把 rank 改成 trusted**（伺服器沒有改好感的開發路由），所以面板文字仍寫「中立」；畫法照實際資料走。
- `docs/art/shots/qk2/qk2_hero_list_1600_v2.jpg`：我的角色清單（龍裔／灰燼荒原橘框、獸耳兔耳／雲嶺綠框、精靈／晶冠藍框、矮人／魔導樞市青框）。
- `docs/art/shots/qk2/qk2_hero_hud_1600_v2.jpg`：探索 HUD 主角卡（赤角：龍裔、馬尾、山羊鬍、灰燼荒原出身）。
- `docs/art/shots/qk2/qk2_hero_battle_1600_v2.jpg`：戰鬥 HUD 主角卡（開發頭目戰）。
- `docs/art/shots/qk2/qk2_hero_faces_zoom3_v2.jpg`：上面三處＋NPC 面板頭像 3 倍特寫。
- `docs/art/shots/qk2/qk2_fur_collar_ayue_v2.jpg`：阿岳毛領，左改前（QK-2 並排）、右改後 192px／48px／48px×4。

### 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 260 檔、3221 項全過（含 `qSelfTest`、`inkWeaponFrame` 照跑沒改）；**沒有快照重產** |
| `tsc --noEmit`、`vite build` | 過 |
| Python | `ruff check`、`ruff format`（改到的檔）、`mypy`、`lint-imports` 過；`test_look_api.py`、`test_openapi_snapshot.py`、`test_run_origin_api.py`、`test_client_fixtures.py`、`test_architecture.py` 過 |
| 排版煙霧（`?dev=1&anim=0.1&mute=1`） | 1600×900、1040×624、800×600 都 13 PASS、0 FAIL |
| 6.5.1 實測（建角頁種族卡） | 1600×900、800×600：滑過開卡、卡在畫面內 → 直線滑進仍開 → 滾輪仍開 → 點一下釘住、滑鼠離開仍在 → Esc 關閉 |
| 小修 1 實測 | 1600、800：滑過關鍵字開卡 → `scrollTo(0,0)` 後 60ms 卡片已關（改前 50ms 時卡片還夾在 y=827） |

### 待 PM 決定（QK-2b）

1. **「隊伍面板的主角頭像」**：全專案用通用臉的只有 `HeroCard`（探索、戰鬥）與角色清單，已全換；「隊伍」面板（`PartyPanel`）的成員列本來就只有文字、沒有頭像，我解讀為戰鬥 HUD 主角卡，沒有在隊伍面板新增頭像。要加的話另排。
2. **主角卡框色改成出身區**（規格寫的），不再跟著目前區域變色；舊的 `HudPortrait`（框色淡入）只剩舊伺服器沒給外觀時的退路。
3. **後端加了純顯示欄位**（角色清單原本沒有種族、外觀、出身）：`hero_look`、`origin_realm`、`HeroOut.origin_realm`，不影響規則、存檔、重播。
4. 循環賽重播的戰鬥主角卡框色用傭兵金（重播的主角不一定是自己；開發頭目戰用自己的出身）。
5. 毛領改走頸飾後，頭像裡毛領上緣被頭蓋住、兩側被手臂蓋住，看起來比改前細一些（和地圖紙娃娃一致）。
