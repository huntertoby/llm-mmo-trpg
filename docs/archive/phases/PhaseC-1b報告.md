# Phase C-1b 報告｜紙娃娃 C 畫風：樣張畫過的裝備與武器

規格：`docs/phases/PhaseC畫風計畫.md` C-1b 節；需求 `docs/art/C畫風移植需求.md` 第 0、3、4 節；畫法對照 `docs/art/sample/storyDoll.js`。只動前端，沒動 Python、`look` 與裝備資料、API、引擎、裝備圖示。

## 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/inkGear.ts`（新） | 頭部裝備 `helmet`／`hood`／`wizard_hat`（正、背、側）；手持物 `sword`／`dagger`／`axe`／`staff`（杖頭光暈元素色，預設 `#8fe3ff`，用同心半透明圓疊出，不用漸層）／`bow`；圓盾 `shield_round`（正面圓面＋盾緣＋盾心、側面一條邊）。全用 `ink()`／`stroke()`，key 固定，不用 `Math.random()` |
| `client/src/render/inkDoll.ts` | 掛入：樣張畫過的走 C 畫法，其餘退回 `InkHooks`（現行畫法）。握點：正面主手 (−9,−23.2)、側面近側 (4.6,−24)、遠側 (5.6,−27)（比近側往前上錯開 3px、顏色暗 25%）；側面劍、匕首傾 0.75 rad、斧 0.6 rad，杖與弓直立；正面副手成對武器＝主手鏡像；背面主手鏡像、副手不鏡像（照樣張 `drawBack`）。側面書、法球改畫在身體後面（美術 PM 提醒；盾留在前面） |
| `client/src/render/paperdoll.ts` | 刪掉不再被走到的舊 `drawHood`、舊 `hood`／`wizard_hat` 分支 |
| `client/src/dev/dollGallery.ts` | 新增 ⑧ 段：四方向整套、C-1b 頭部裝備、武器與圓盾各四朝向 |
| `client/src/render/inkGear.test.ts`（新） | 9 個測試 |

身體 `shirt`／`leather`／`plate`／`robe`、腳 `boots`／`greaves`、披風，C-1a 已是 C 畫法（骨架中的腿、靴、身體、披風），本段沒有再改。

## 驗收對照

| 條件 | 結果 | 證據 |
|---|---|---|
| 樣張畫過的頭、武器、圓盾都有 C 版，四方向 | 通過 | `inkGear.test.ts`「整合：主手武器四方向…」「圓盾」「頭部裝備三方向」；截圖 |
| 握點照第 4 節（含側面錯開、背面主手在畫面右） | 通過 | 「握點」「成對武器」測試；截圖 `C-1b-doll-gallery-weapons-east.jpg` |
| 杖頭光暈用元素色、預設 #8fe3ff、不認得的元素退預設 | 通過 | 「法杖杖頭光暈」 |
| 確定性、不用 `Math.random()` | 通過 | 「同一件重畫完全相同…」（spy） |
| 沒換的 kind（魔導劍、權杖、圖騰杖、大盾等）不空白不報錯 | 通過 | 「樣張畫過的 kind 走 C 畫法，其餘回傳 false」；`dollGear.test.ts`、`paperdoll*.test.ts` 全過 |
| 不認得的材質、顏色、形制、元素 → 預設 | 通過 | 「不認得的材質、顏色…」 |
| vitest／tsc／build | 通過 | `vitest run src/render src/dev` 全過（26 檔）；`corepack pnpm -C client build`（含 tsc）成功 |
| 排版煙霧檢查 | 通過（有已知抖動） | 1600×900、800×600、shortBottom 各至少一次全 PASS。連續跑同一情況時，「更多動作選單」那項會隔次 FAIL（說明卡 0 張），改視窗大小不重新整理也會出現「找不到拖曳線」；與畫布繪圖無關（本段沒動版面），與 C-1a 報告的「首次 runCase」同類 |
| 截圖 | 完成 | `docs/phases/img/C-1b-doll-gallery-four-facings.jpg`、`C-1b-doll-gallery-weapons-east.jpg`、`C-1b-gear-gallery.jpg`（裝備圖示本段不動）、`C-1b-battle.jpg`（內建瀏覽器只能存 JPEG） |

## 舊程式處理（C-1a 待決 5）

- 已刪：`paperdoll.ts` 的 `drawHood`、`drawHeadgear` 的 `hood`／`wizard_hat` 分支（確定不在畫圖路徑上，無測試引用）。
- 留給 C-2：`paperdollSide.ts`（`drawFigureSide`）整支、`paperdollSideGear.ts` 的 `drawHoodSide`／`drawWizardHatSide`（`drawFigureSide` 與其測試仍引用）、`paperdollGear.ts` 的 `drawFeet`／`drawCoat`／`drawHandsGear`／`drawMailPattern`、`handSides`；`paperdoll.ts` 的 `drawWeapon` 內 sword／dagger／axe／staff／bow／圓盾分支仍被 `drawWeaponAlone`（武器小圖示）與 `drawWeaponSide` 使用，不能刪。

## 沒換畫法、留給 C-2 的副手物品

`shield_kite`（鳶盾、塔盾）、`tome`（書）、`orb`（法球）、`greatsword` 等其他手持物，以及頭部 `horned_helm`／`greathelm`／`cap`／`wide_hat`／`crown`／`bandana`，仍由現行畫法掛上。側面副手書、法球本段已先改畫在身體後面。

## 待 PM 決定

1. 樣張只畫「側面副手成對武器」，沒畫書、法球；本段書、法球側面畫在身體後面，但書的現行形狀在 x 4.5–9.5，被身體遮掉一部分，C-2 換畫法時要重新定位。
2. 魔導劍（`form: arcane`）、權杖、圖騰杖仍走現行畫法（需求寫 C-2）。`wand`（短杖）用 C 杖縮小 0.75 倍，樣張沒畫，請美術 PM 確認。
3. `sword` 形制 `broad` 劍身加寬 1.7 倍、其他形制（`curved`、匕首 `kris` 等）一律同一把，樣張沒畫形制差異。
4. 武器金屬色：沒有材質或材質為木時用鋼色，其餘用材質色（含元素混色）；弓與杖身固定木色（弓有指定 `color` 才用）。
5. 側面遠側成對武器多加了 25% 變暗（樣張沒有），讓兩把分得開。
6. 圓盾盤面色：有 `color` 用指定色；沒有材質用樣張藍 `#2f5fae`；有材質用材質色。
7. 內建瀏覽器截圖為 JPEG，副檔名用 `.jpg`（同 C-1a 待決 1）。
8. 排版煙霧檢查的抖動（見上）建議開發 PM 另案處理 `layoutSmoke` 的狀態重置。
