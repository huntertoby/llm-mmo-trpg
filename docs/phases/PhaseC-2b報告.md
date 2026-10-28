# Phase C-2b 報告｜紙娃娃 C 畫風：其餘武器、成對武器、清舊程式

規格：`docs/phases/PhaseC畫風計畫.md` C-2b 節；需求 `docs/art/C畫風移植需求.md` 第 0、4 節與檢查清單「裝備與武器」；畫法對照 `docs/art/sample/storyDoll.js`。另併入專案 PM 轉達的美術 PM 對 C-2a 待決的回覆。只動前端，沒動 Python、`look` 與裝備資料、API、引擎、裝備圖示、`docs/art/`、計畫檔。

## 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/inkWeapons.ts`（新） | `greatsword`（雙手／斬馬／鋸齒）、`hammer`（釘頭／連枷／戰錘）、`spear`（單尖／戟／三叉戟）、`crossbow`（輕／重／連弩）、`longgun`（燧發／獵槍／狙擊）、`shotgun`（喇叭口／雙管／滑套）、`pistol`（燧發／左輪／袖珍）、`fist`（指虎／拳刃／爪）、`scythe`、`whip`（皮／鏈／刃）、`sword`／`arcane`（魔導劍，源晶槽元素色、三個淡白符文、黃銅齒輪護手）、`staff`／`scepter`、`staff`／`totem`。全用 `ink()`／`stroke()`，輪廓沿用現行造型（放大約 1.3 倍到 C 骨架），顏色照 `itemColors()`（金屬用 `metalOf`）。外側統一朝 +x：正面主手（畫面左）翻轉、副手（鏡像）與背面主手不翻轉，側面前方即 +x。握法：正面、背面略往外斜（巨劍 0.18、錘 0.2、矛、鐮刀 0.12、拳套 0.1 rad），側面往前傾（巨劍 0.8、錘 0.5、矛 0.4、鐮刀 0.3、拳套 1.2 rad，權杖、圖騰杖 0.4），槍弩朝外上抬 0.35 rad、側面近乎水平（遠側再往下 0.2 rad）。遠側那把暗 25%。 |
| `client/src/render/inkDoll.ts` | `legacyHeld` 掛入新武器；成對武器的握點沿用 C-1b（正面副手＝鏡像在畫面右手；側面遠側 (5.6,−27)、身體後、往前上錯開約 3px；背面兩把都在身體後）。拿掉 `InkHooks.headgear`、`InkHooks.offhandSide`（未知 kind 的退路，已無人使用） |
| `client/src/render/inkGear.ts` | `sword` 的 `curved`、`dagger` 的 `kris` 刀身往前彎約 3px（越靠尖端彎越多）；側面圓盾盾邊中心 x 7→8.5、rx 2→2.6（美術 PM 回覆 1） |
| `client/src/render/inkOffhand.ts` | 側面鳶盾、塔盾外移約 1.8 px（盾面至少一半露在手與劍柄外）；側面書、法球中心外移到 x≈9（約露出一半）（回覆 2） |
| `client/src/render/inkArmor.ts` | 脛甲 `knee` 護膝：每條腿膝蓋 (±2.7, −9) 一個鋼色小橢圓 2.4×1.8；正面兩條腿、側面只畫近側腿、背面不畫（回覆 3） |
| `client/src/dev/dollGallery.ts` | 新增 ⑪ C-2b：近戰、長柄／杖／鞭／弩、槍、成對武器、護膝與側面副手外移，各四朝向 |
| 測試 | `inkWeapons.test.ts`（新，8 個）；`dollGear.test.ts`、`paperdollSideWeapon.test.ts` 配合新畫法與刪除調整 |

## 清舊程式

用搜尋確認無其他使用者後刪除：

- 整檔刪除：`paperdollSide.ts`（`drawFigureSide`）與 `paperdollSide.test.ts`、`paperdollSideGear.ts`（頭部、副手、披風側面函式與 `drawHornSide`；`dark` 改成 `paperdoll.ts` 內的小函式）。
- `paperdoll.ts`：`drawHelmet`、`drawBandana`、`drawHeadgear`、`drawShield`、`drawWeapon` 內的 `shield_round`／`shield_kite`／`tome`／`orb` 分支、`legacyHooks` 的 `headgear`／`offhandSide`、`HEAD_GEAR_SCALE`，及不再使用的匯入。
- `paperdollGear.ts`：`bootHeight`、`drawFeet`、`drawCoat`、`drawMailPattern`、`drawHandsGear`、`drawWideHat`、`drawCap`、`drawGreathelm`、`drawOrb`、`drawTowerShield`。
- **刻意保留**：`drawWeapon` 的所有武器分支與 `paperdollGear.ts` 的 `drawHammer`／`drawSpear`／`drawFist`／`drawScythe`／`drawWhip`／`drawPistol`／`drawShotgun`、`paperdoll.ts` 的 `drawBlade`／`drawArcaneParts`／`drawScepter`／`drawTotemStaff`／`drawStaff`／`drawBow`／`drawCrossbow`／`drawLongGun`：`drawWeaponAlone`（武器小圖示 `weaponIcon.ts`）與 `drawWeaponSide`（`paperdollSideWeapon.test.ts`）仍走它們。`sideWeaponPose`／`paperdollSideWeapon.ts` 同理保留。`arcaneBlade.test.ts`、`weapons24a2.test.ts` 仍測這條路徑並通過。

## 驗收對照

| 條件 | 結果 | 證據 |
|---|---|---|
| 其餘武器 kind（含形制）都有 C 版，正、背、側 | 通過 | `inkWeapons.test.ts`「每種 kind × 形制 × 四方向…」；截圖 `C-2b-doll-gallery-melee-south-north.jpg`、`-melee-poles-east.jpg` |
| 魔導劍、權杖、圖騰杖；`sword` curved 弧度 | 通過 | 「魔導劍…」「curved、kris 刀身有弧度」；截圖 |
| 成對武器：正面副手＝鏡像（畫面右手）、側面遠側 (5.6,−27) 往前上錯開約 3px 在身體後、背面兩把都在身體後 | 通過 | 「成對武器…」測試；`C-2b-doll-gallery-pairs-south-north-east.jpg`、`-pairs-knee-west.jpg` |
| 所有武器握在手上、不空白 | 通過 | `dollGear.test.ts` 全組合自測（`gear-all`）；截圖 |
| 不認得的形制、材質、顏色、元素 → 預設，不報錯；不用 `Math.random()`；重畫完全相同 | 通過 | `inkWeapons.test.ts` 前兩個測試 |
| 美術 PM 回覆 1～3（圓盾盾邊、書與法球外移、護膝） | 通過 | 「C-2a 待決回覆」測試；`C-2b-doll-gallery-pairs-knee-west.jpg`（盾、書、法球外移）。護膝在板甲（鋼腿）上與腿同色，縮圖不顯眼，橢圓有畫（測試固定正面兩條腿、側面近側、背面不畫） |
| 清舊程式；`drawWeapon` 小圖示分支不刪 | 通過 | 上節；`gear-gallery` 圖示無變化（`C-2b-gear-gallery.jpg`）；全量 vitest 110 檔 1037 測試全過 |
| tsc、vitest、build | 通過 | `tsc --noEmit` 無輸出；`vitest run`（整個 client）通過；`corepack pnpm -C client build` 成功 |
| 排版煙霧檢查 | 通過（有已知抖動） | 1600×900、800×600、1600×900 shortBottom 皆全 PASS（先 `localStorage.clear()`；載入後第一次 `runCase` 全 FAIL 是已知現象，再跑一次；shortBottom 第一次跑出現一次「更多動作選單說明卡 0 張」，重跑全 PASS，與 C-1b 報告的既有抖動同類，本段沒動版面） |
| 截圖 | 完成 | `docs/phases/img/C-2b-doll-gallery-melee-south-north.jpg`、`-melee-poles-east.jpg`、`-pairs-south-north-east.jpg`、`-pairs-knee-west.jpg`（四方向含成對武器）、`C-2b-gear-gallery.jpg`、`C-2b-battle.jpg`（內建瀏覽器只能存 JPEG） |

`doll-gallery`、`gear-gallery` 是 vite 開發頁，用 `vite --port 5192`；實戰用 `trpg serve --port 8014`。兩者都已只用自己的 PID 關閉，視窗已 `resize_window` 回 `desktop`。

## 待 PM 決定

1. 側面槍、弩的長度受 64px 畫布限制（手在 x≈4.6，槍口不能超過約 x=31），所以狙擊火槍縮成 25；錘、矛、鐮刀的側面傾角也比現行畫法小（0.5／0.4／0.3），避免頭部被畫布邊緣切掉。若要更大要先放寬畫布寬度（影響所有小人快取）。
2. 矛、錘柄的長度比現行放大 1.3 倍稍短（矛 44、戰錘柄 31），同樣為了不超出畫布與蓋住臉。
3. 正面、背面的槍與弩朝外上抬 0.35 rad，槍托在手內側會壓在身體上；沿用現行畫法的姿勢，樣張沒畫。
4. 魔導劍預設劍身色用冷灰 `#8a93a8`（有 `color` 才用指定色，不隨材質），沿用現行畫法的設定。
5. 圖騰杖側面額外往前 2px、傾 0.4 rad（現行 0.65 會超出畫布），頂端羽毛縮小；樣張沒畫。
6. `wand`（短杖）仍用 C 杖縮小 0.75 倍（C-1b 待決 2），美術 PM 已同意。
7. 護膝在板甲上與腿同色；若要更明顯可改成亮一點的鋼色或加描邊（目前 `shade:false`）。
8. 清舊保留了 `drawWeapon` 的全部武器分支給武器小圖示與 `drawWeaponSide` 測試使用；若之後小圖示也要換 C 畫法，可再整批刪掉 `paperdoll.ts`、`paperdollGear.ts` 的武器函式與 `paperdollSideWeapon.ts`。
9. 內建瀏覽器截圖為 JPEG，副檔名用 `.jpg`（同 C-1a、C-1b）。
