# Phase 3J-5 報告｜形態外觀（C 畫風）

規格：`docs/phases/Phase3J計畫.md` 第 4.7 節；需求 `docs/art/C畫風移植需求.md` 第 5 節與檢查清單「形態」、`docs/art/形態外觀.md` 定稿方向；畫法照 `docs/art/sample/storyDoll.js` 的 `FORMS`／`aura`／`drawForm`。只動前端，沒動 Python（`UnitView.form` 的 `look`、`element` 夠用）、引擎、`docs/art/`、計畫檔。

## 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/inkForm.ts`（新） | 10 種形態的 `ink()`／`stroke()` 畫法（熊、狼人、龍、貓、鳥、惡魔、巨人、元素化身、暗影、樹人，座標照樣張搬成 TS）；`FORM_ARTS`（含 `size`、畫出來的最高點 `top`）；`FORM_LOOKS`：形態外觀 id（`forms.yaml` 的 `look`，`form_bear`…）→ 畫法 id（`form_elemental` → `avatar`）；`formArtOf`（不認得 → `null`）；`formHeroColor`（身體裝備 color → 披風 color → 陣營藍 `#4f7fbf`）；`formAuraColor`／`drawFormAura`（元素色虛線橢圓、線寬 1.1、虛線 2.4／1.6、18% 同色填色；無元素 `#9a86ff`）；`formScale`、`formAuraRadius`、`formRowRise`；`renderFormCanvas`／`renderAuraCanvas`。 |
| `client/src/render/artTextures.ts` | 新增 `form()`（鍵 ＝ 畫法＋主色＋元素＋朝向＋姿勢）、`formAura()`（鍵 ＝ 顏色＋半徑）兩種快取貼圖，走同一套 `used` 清理。 |
| `client/src/render/unitSprite.ts` | 單位有形態且認得外觀 id → 用形態貼圖取代紙娃娃（同樣的腳底錨點與 `DOLL_SCALE` 基準）；腳下加手繪光環（畫在隊伍底圈之上、小人之下）；不認得的 id、空字串、貼圖畫不出來 → 退回原角色紙娃娃，光環照畫；頭頂狀態列依形態高度再上移（`formRowRise`）。召喚物與沒有形態的單位路徑不變。 |
| `client/src/battle/drawModel.ts` | `UnitDraw.form`（`look`、`element`），來自 `UnitView.form`。 |
| `client/src/render/inkGear.ts`、`inkArmor.ts`、`inkDoll.ts` | 美術 PM 小修（C-2b 驗收）：正面彎刀弧度改往外彎；板甲腿上的護膝改用比鋼色亮 35% 的顏色（`lighten`），仍走 `ink()` 保留墨線。 |
| `client/form-gallery.html`、`client/src/dev/formGallery.ts`（新） | 開發用檢查頁：10 種 × 四朝向（左上是變身前的角色同比例對照）、元素、不認得的 id／倒地／朝北、頭頂狀態列、變身前後小戰場；`#south／north／east／west／element／unknown／status／battle` 只顯示一段（改 hash 後要重新載入）。 |
| `client/src/render/inkForm.test.ts`（新） | 26 個測試，見下。 |

## 規則與做法

- **朝向**：樣張的形態只有側面（朝東）。東、南畫朝右，西、北左右鏡像（`scale(-1,1)`），四方向都有，但南、北不是真正的正面、背面。
- **縮放**：照樣張戰場的做法，畫面縮放 ＝ `0.6 × min(size, 1.3)`（相對 52px 虛擬格），龍 1.5、巨人 1.45 封頂在 1.3 的縮放，免得超出一格太多；`size` 仍照 `FORMS`（光環半徑 ＝ `16 × size ×` 縮放）。形態貼圖畫布 96×88（比小人 64×88 寬，龍的尾巴與吐息才不會被切掉）。
- **倒地**：整個形態旋轉 90° 躺下（與小人同一種做法，套同樣的透明度與去色）。實際遊戲中倒下會解除形態，這條路徑只是防呆。
- **影子**：形態畫布內畫 C 畫風的短斜線影子（`shadow()`），沒有黑色外框；鳥身體離地、影子在地上。
- **主色**：`resolveDoll` 後取 `gear.body.color`，沒有再取 `gear.cloak.color`，再沒有用陣營藍；非 `#rrggbb` 的值跳過。
- **元素**：只認 fire／ice／lightning；元素化身、龍的身體與吐息色、光環色都用它；不認得的元素（`plasma` 等）光環用 `#9a86ff`、身體用火（樣張的預設）。
- **頭頂狀態列**：形態最高點（量自畫法座標，`top`）超過小人最高點（44 虛擬單位）的部分往上移；熊、貓比小人矮不移，樹人最多（約 8px 級）、龍、狼人次之。
- 沒有新增 `form_looks` 資料檔／schema：`forms.yaml` 已有 `look` 欄位，前端用 `FORM_LOOKS` 對照表（測試保證 `forms.yaml` 的每個 `look` 都有畫法）。

## 驗收對照

| 條件 | 結果 | 證據 |
|---|---|---|
| 10 種用 `ink()` 畫、四方向、倒地照現行做法 | 通過 | `10 種 × 四方向 × 站立／倒地都畫得出來…`、`西與北是左右鏡像…`；截圖 `3J-5-forms-{south,north,east,west}.jpg` |
| 帶主角主色、比召喚物大一號（`size`）、元素化身與龍吃元素色 | 通過 | `帶主角主色…`（10 種換主色都換顏色）、`大小倍率照樣張`、`元素化身與龍吃元素…`、`主色取自單位身體裝備的 color…`；`3J-5-forms-elements.jpg` |
| 腳下光環：元素色虛線橢圓（1.1／2.4、1.6）＋18% 填色；無元素 `#9a86ff` | 通過 | `手繪光環…`、`光環色…`；單位測試 `有形態：畫形態貼圖…、帶光環；元素色光環` |
| 不認得的形態 id → 退回原角色紙娃娃＋光環，不報錯 | 通過 | `不認得的形態 id：退回原角色紙娃娃＋光環，不報錯`（`form_unknown`、空字串）、`不認得的外觀 id…`、`形態貼圖畫不出來…退回紙娃娃`；`3J-5-forms-unknown.jpg` |
| 快取成貼圖；頭頂狀態列跟體型上移；影子同 C 畫風 | 通過 | `貼圖快取鍵含畫法、主色、元素、朝向、姿勢`、`狀態列：矮的形態不下移…`；`3J-5-forms-status-row.jpg` |
| 美術 PM 小修：正面彎刀往外彎、側面不動；板甲護膝亮 35% 保留墨線 | 通過 | `正面彎刀往外彎…`（主手往畫面左、副手往右）、`側面彎刀不動`、`背面不動`、`板甲腿的護膝比鋼色亮 35%…其他腿不變`；既有 `inkWeapons.test.ts` 的護膝、彎刀測試仍通過；`3J-5-fix-curved-knee.jpg` |
| vitest、tsc、build | 通過 | `corepack pnpm -C client exec tsc --noEmit` 無輸出；整個 client `vitest run`：111 檔 1063 測試全過；`corepack pnpm -C client build` 成功 |
| 排版煙霧檢查 | 通過 | 1600×900、800×600、1600×900 shortBottom 三個情況各「全 PASS」（先 `localStorage.clear()`；載入後第一次 `runCase` 全 FAIL 是已知現象，再跑一次） |
| 內建瀏覽器截圖：10 種形態四方向、實戰變身前後各一張 | 完成 | `docs/phases/img/3J-5-forms-south／north／east／west.jpg`（格子字母 A＝變身前的戰士、B 熊、C 貓、D 鳥、E 元素化身、F 狼人、G 惡魔、H 巨人、I 暗影、J 樹人、K 龍；圖下方的文字標籤因頁面樣式排成兩行，順序以此為準）、`3J-5-battle-before.jpg`／`3J-5-battle-after-bear.jpg`（真實伺服器、`build_form_tester` 一場冰湖，施放「化身為熊」前後）、`3J-5-gallery-battle.jpg`（檢查頁變身前後）、`-forms-elements.jpg`、`-forms-unknown.jpg`、`-forms-status-row.jpg`、`-fix-curved-knee.jpg`。內建瀏覽器只能存 JPEG |
| 美術 PM 用檢查清單「形態」驗收 | 待美術 PM | 檢查頁：開發伺服器 `vite --port <埠>` 後開 `/form-gallery.html#east`（等） |

## 測試（`client/src/render/inkForm.test.ts`，26 個）

資料與外觀 id（3）、10 種畫法（5）、主色與光環（4）、體型（3）、單位畫法（7，用假 `ArtTextures` 檢查走形態貼圖還是紙娃娃、光環色、主色來源）、美術 PM 小修（4，用會追蹤變換矩陣的假 Canvas 量刀尖的畫面座標）。

## 待 PM 決定

1. **南、北朝向用側面畫法**：樣張只有側面，所以南＝東、北＝西（鏡像）。若要真正的正面、背面，要美術 PM 補樣張（約 10 種 × 2 張）。
2. **龍與巨人縮放封頂在 1.3**：照樣張戰場的 `0.6 × min(size,1.3)`，所以畫面上龍、巨人與熊、樹人一樣大（龍本身畫得較寬、巨人畫得較高）。若要完全照 `size`（龍 1.5），龍會超出格子約 25%，要不要放大請美術 PM 決定。
3. **倒地的形態**：以旋轉 90° 躺下（水平的熊、貓、龍旋轉後會變成直立，看起來不自然）。實際上倒下會解除形態所以看不到；若之後有「形態中倒地不解除」的規則，要另畫。
4. **不認得的元素**：身體用火色（樣張預設）、光環用 `#9a86ff`；兩者不一致，目前資料只有 fire／ice／lightning。
5. **護膝亮色的適用範圍**：我解讀為「身穿板甲時」（腿是鐵／鋼色）才改用亮 35% 的顏色，其餘身體裝備的護膝不變；若美術 PM 的意思是所有護膝都要，改一個條件即可。
6. **彎刀往外彎只改 `sword` 的 `curved`**，`dagger` 的 `kris` 沒動（規格只寫彎刀）；背面彎刀原本就往身體內側彎（被身體擋住），依「側面不動」精神也沒動。
7. **主色取身體裝備的 `color`（染色）**：沒有染色的身體裝備（只有材質）時取披風、再沒有用陣營藍；若要「材質主色」也算，要擴充取色規則。
8. **頭頂狀態列的上移量**用畫法最高點估算（`FORM_ARTS.top`，手量自座標），非精確值；樹人的葉冠與狀態列仍可能輕微相鄰。
9. 檢查頁 `form-gallery.html` 與其他 dev 頁一樣只在 vite 開發伺服器上，不進 build。
