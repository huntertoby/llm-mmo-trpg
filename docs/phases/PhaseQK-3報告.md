# Phase QK-3 報告：召喚物 17、形態 10、額外裝備 17 件改 Q 版

> 實作者：worktree `dev/qk3`（從 main `5dd15774` 開）。沒有 push、沒有 rebase。依據：`docs/art/QK移植需求.md`（第 2 版）第 0 節＋第 4 節；真相來源 `docs/art/sample/qSummon.js`、`qForm.js`、`qGearExtra.js`、`qDoll.js` 新形制（`89f5e3f8`）。樣張照改寫進 client，**沒有 import 樣張程式**；不改規則、資料、存檔、重播。

## 0. 樣張 → client 檔案對照

| 樣張 | client | 說明 |
|---|---|---|
| `qDoll.js` 的 `body.form: scale`、`cowl()`、`handFormUnder／Over`（fingerless、mail） | `client/src/render/qGearForms.ts`（新）＋`qGear.ts`／`qDoll.ts` 呼叫點 | 只在資料有這個 `form` 時生效，其他裝備一像素不變 |
| `qGearExtra.js` 的 13 件＋骷髏肋骨 | `client/src/render/qGearForms.ts` | **不用色鍵遮罩**：樣張的 torso／free／top／hand 四層，改成在 qDoll 的圖層順序裡找對應位置畫（見第 1 節） |
| `qSummon.js` 的畫法層 H、`qCreature.js` 的 `layer` | `client/src/render/qSummonCore.ts`（新） | 平塗＋縫線＋剪影外框 1.3；沒有 DOM 時直接畫平塗 |
| `qSummon.js` 非人形 13 種、陣營環大小、圖騰光環 | `client/src/render/qSummon.ts`（新） | |
| `qSummon.js` 的 `HUMAN`、`doll()`（人形 4 種） | `client/src/render/summonArt.ts`（改寫，API 不變） | Q 版紙娃娃＋整隻染色＋半透明，不發外光 |
| `qForm.js` 10 種、`formRing` | `client/src/render/qForm.ts`（新）＋`inkForm.ts`（改寫，API 不變） | `roc`＝樣張的 `bird` |
| `q-summons-forms.html`、`q-gear-extra.html` 的版面 | `client/qk3-gallery.html`＋`client/src/dev/qk3Gallery.ts`（新） | 同比例、同腳底位置，給並排圖用 |

### 擴充點（給 QK-8）
`qGearForms.ts` 每一層一個函式，依 `kind`／`form` 判斷，認不得就不畫：`bodyPattern`（軀幹紋，在 `body()` 裡）、`drawTorsoForms`（剪在軀幹裡）、`drawFreeForms`（身體之後、手臂之前）、`drawTopForms`（正面側面在最後、背面在披風之前，挖掉頭）、`handFormUnder／Over`（`arm()` 裡拳頭前後）、`drawLegForm`（每條腿的座標系，走路跟著動）、`cowl`／`headgearClip`／`drawHeadFormTop`（頭那一段）。QK-8 的赤膊、頸飾、手持物照同一個檔加。

## 1. 完成表

| 項目 | 做法 | commit |
|---|---|---|
| 額外裝備 17 件 | 鱗甲、斗篷帽、露指手套、鎖鏈護手照 `qDoll.js`；獵裝（口袋、斜背帶、加長下襬）、全身板甲（護頸、腿甲裙）、披風外套（短披肩）、圍裙、毛帽（側面帽舌剪掉＋毛邊護耳）、長皮手套、臂環（不畫皮護腕）、綁腿鞋、尖頭鐵靴、護膝脛甲、吊牌、符牌、骨符照 `qGearExtra.js`。手部件畫在 `arm()` 裡（武器、盾、背面披風照原本圖層蓋在上面）；只在正面的部件側面在前緣、背面不畫；戒指不畫。遊戲資料的骷髏（`body: ribs`）也吃肋骨 | `cd124d21`、`2b974ff6` |
| 召喚物 17 種 | 非人形 13 種四方向（漂浮靈、構造體、圖騰、藤蔓只移眼睛、背面不畫眼睛；野獸畫側面，朝南用朝東、**朝北用朝西**）；人形 4 種用 Q 版紙娃娃：骷髏照範本（＋肋骨）、影魅與守護靈照樣張外觀、殘影複製召喚者＋身後淡影；**不發外光**，改半透明＋整隻染色；霧影（遊戲才有）照 5F-ART1。非人形和紙娃娃同一個戰場縮放（大小畫進貼圖）；陣營底圈比石像、戰狼的身體寬 | `7866282c`、`fd1bd6c5` |
| 形態 10 種 | 四方向；帶主角主色；縮放＝小人縮放 × size（比同類召喚物大一號，龍寬 1.5 格內）；側面形態朝西、朝北鏡像，正面形態朝北畫背面；形態光環＝陣營底圈＋藍紫外環＋8 刻點，平塗不發光；暗影形態下緣 3 段淡出 | `d30b9ebb` |
| 並排畫廊 | `qk3-gallery.html`：召喚物、形態用遊戲的貼圖產生器＋陣營底圈；裝備用 `qStamp`＋樣張色（同 QK-1 特寫） | `2b974ff6` |

## 2. 截圖（`docs/art/shots/qk3/`）

- 並排圖 48 張（左樣張、右遊戲，`docs/art/shots/qk3/compare/`，共 1.3 MB）：
  - `docs/art/shots/qk3/compare/summon_01_skeleton_warrior.jpg` … `summon_17_plateau_totem.jpg`（南、東、西、北）
  - `docs/art/shots/qk3/compare/form_01_bear.jpg` … `form_10_dragon.jpg`（南、東、西、北；主色藍、元素冰）
  - `docs/art/shots/qk3/compare/gear_01_scale_mail.jpg` … `gear_17_charm_bone.jpg`（正面、背面、朝東、朝西）
  - `docs/art/shots/qk3/compare/hero_gloves_long.jpg`、`hero_bracer_ring.jpg`、`hero_gauntlet_mail.jpg`、`hero_gloves_fingerless.jpg`（拿劍盾披風那列：hero_fighter＋手部件＋鱗甲）
- 實機（`?mute=1`，開發包＋固定種子 1）：
  - `docs/art/shots/qk3/qk3_wolf_battle_1600.jpg`＋`docs/art/shots/qk3/qk3_wolf_battle_1600_zoom.jpg`：戰狼包放出戰狼（朝東）
  - `docs/art/shots/qk3/qk3_form_battle_1600.jpg`＋`docs/art/shots/qk3/qk3_form_battle_1600_zoom.jpg`：獸變包變身狼人（朝東、藍紫外環）
- 出圖：Playwright＋系統 Chrome（非無頭、`--mute-audio`）。樣張頁另外注入同版面的出圖函式（和 `qk3Gallery.ts` 同比例、同腳底），腳本在 scratchpad，沒進 repo。

## 3. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 252 檔、3162 項全過（`qSelfTest` 9 項、`inkWeaponFrame` 照跑沒改） |
| 快照重產（`vitest run -u`） | `client/src/render/__snapshots__/inkDollSnapshot.test.ts.snap`：只有 2 組變（`summon_skeleton_warrior`、`body:ribs`，肋骨）；其他 17 件新形制資料不在快照的 kind 表裡，原有裝備一像素不變 |
| `tsc --noEmit`、`pnpm -C client build` | 過 |
| 排版煙霧檢查 1600×900、1040×624、800×600 | 三個都 12 項全 PASS（「四角飾件」這次也 PASS） |
| 並排目視 | 召喚物、形態、裝備逐列和樣張一致；差異只有第 4 節第 1～3 點（陣營環是遊戲的底圈） |
| Python | 沒改伺服器、資料、存檔，沒跑 pytest |

### 測試照新畫法更新的地方（斷言的目的沒變，只換成 Q 版的對應物）
- `summonArt.test.ts`：背面不畫眼睛改數 `fillRect`（Q 方眼），野獸拿掉（樣張朝北用朝西側面，看得到眼睛）；野獸朝北改成鏡像；影子改「平塗深色橢圓、只在 ground 層」；圖騰光環半徑 17 → 約 22.9（第 4 節第 2 點）；「墨線」改「不發外光」；守護靈副手 `shield_round` → `shield_kite`（樣張）；人形款式樣式表改成樣張的染色＋透明度（無 glow）；殘影改驗「沒有外光、身後淡影 0.22」。
- `inkForm.test.ts`：「墨線」改「有縫線、不發外光」；鏡像只限側面形態（正面形態改驗北≠南）；倒地改驗 `rotate(π/2)`（鳥翅膀本身有小角度）；熊毛色混主色 0.3 → 0.25；元素只有火冰雷、其他退回火（樣張；`forms.yaml` 的 `element_choices` 也只有這三種）；光環改 Q 版外環＋刻點；光環半徑、縮放、樹人 top 換 Q 版公式；狀態列「矮的形態」拿掉熊（Q 版熊頭放大 1.3，比小人高；`formRowRise` 目前沒有呼叫端）。
- `silhouetteFlash.test.ts`：影子的記號從 C 的斜線色換成 Q 的平塗影子色。

## 4. 待 PM 決定

1. **陣營環沿用遊戲的底圈**：樣張召喚物腳下是淡綠平塗環（`#7dffb0`，半徑 13）、形態是藍環＋藍紫外環。遊戲每個單位腳下已有陣營底圈（召喚物青綠、我方藍，含倒地虛線、精英環、面向箭頭），這段**沒有另畫樣張的環**，只把召喚物的底圈放寬到樣張的半徑（石像 22×1.25、戰狼 25 往頭的方向移 3），形態只疊藍紫外環＋刻點。要換成樣張的淡綠平塗環請美術 PM 決定（QK-4 的敵方紅環同一題）。
2. **戰意圖騰的虛線光環放大**：遊戲底圈（約 20.3 單位、扁度 0.42）比樣張的環大，樣張半徑 17 的光環會被蓋住，改成在底圈外 2.6（約 22.9、扁度跟底圈）。
3. **形態光環不吃元素色**：照樣張固定藍紫；`formAuraColor` 只留作貼圖快取鍵。原本 3J-5 的「元素色光環」不見了。
4. **元素之靈（`elemental_spirit`）與火冰雷水以外的元素**：樣張漂浮靈只有火、冰、雷、水四套配色，其他（含沒元素、灌注成擊倒等）照樣張退回火靈。
5. **圍裙用 `waist: {kind: "apron"}` 表示**（裝備資料沒有圍裙，這是樣張新部件）；QK-8 的 NPC 圍裙（`qNpc.js`，`body.apron`）是另一個畫法，要不要統一由 PM 決定。腰帶扣照樣張露在圍裙上。
6. **吊牌、符牌、骨符**：Q 版畫好了（`neck: {kind: "pendant", form: "tag"}`／`{kind: "charm", form: "tablet"|"bone"}`），但遊戲的 `dollGear` 照舊不把頸飾、戒指放上紙娃娃（「項鍊與戒指不畫」），所以玩家穿上不會出現；要接上得改 `dollGear.ts` 的 `DOLL_SLOT`（不在本段檔案範圍）。
7. **非人形召喚物的戰場大小**：從 C 的 64×64 畫布 ×1.15 改成和紙娃娃同一個縮放（樣張的比例），大型（石像）比以前大、小型（水精、鷹隼）比以前小。`paperdoll.ts` 的 `SUMMON_*` 常數不再被戰場使用（沒刪，不在本段檔案範圍）；`artTextures.ts` 的解析度仍用 `BEAST_DISPLAY`（只影響清晰度）。
8. **形態縮放拿掉 1.3 封頂**：照樣張用 size 本身（龍 1.5、巨人 1.45）；樣張驗過龍寬在 1.5 格內。
9. **畫法層和 QK-4 重複**：`qSummonCore.ts` 的 `layer`、`ink` 等和 QK-4 要移植的 `qCreature.js` 畫法層是同一套。兩段平行、不能改同檔，合併後可以收成一份（建議由後合併的那段處理）。
10. **綁腿鞋側面**：布條畫在每條腿自己的座標系（走路時跟著腿），站好時兩腿的布條同一條斜線，和樣張「連成一條」幾乎一致，但近側腿蓋住遠側腿那一小段時布條略短。
