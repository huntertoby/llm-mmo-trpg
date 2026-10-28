# Phase C-2a 報告｜紙娃娃 C 畫風：其餘防具與副手

規格：`docs/phases/PhaseC畫風計畫.md` C-2a 節；需求 `docs/art/C畫風移植需求.md` 第 0、3、4 節；畫法對照 `docs/art/sample/storyDoll.js`。另併入美術 PM 驗收 C-1b 的 3 個必修（`docs/art/C-1b檢查.md`）。只動前端，沒動 Python、`look` 與裝備資料、API、引擎、裝備圖示、`docs/art/`、計畫檔。

## 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/inkArmor.ts`（新） | 身體 `mail`（鎖環點紋／鱗甲小弧）、`coat`（開衩下襬、翻領、金扣；`cape` 形制多一片肩披；正、背、側）；頭 `wide_hat`、`cap`（皮／毛邊）、`bandana`（正面側邊垂尾、背面腦後結）、`crown`（紅寶石）、`greathelm`（眼縫、鼻條）、`horned_helm`（沿用 C 頭盔＋兩支角，側面遠側角暗 30% 先畫）；手 `gloves`（plain／fingerless／long）、`gauntlets`（plate／mail，前臂袖口）、`bracers`（leather／ring，手露膚色），袖口沿前臂傾角畫；腳 `shoes`（低鞋、綁腿 `wrapped`）、`iron_boots`（高筒、`sabaton` 尖頭） |
| `client/src/render/inkOffhand.ts`（新） | `shield_kite`：正面鳶盾／塔盾（盾面、盾緣、中脊、鉚釘）、側面一條邊（身體之後、頭之前）、背面木色＋皮帶；`tome`：正面立在身側（封面、書脊、頁邊、扣）、`scroll` 卷軸匣；`orb`：正面托在掌上（`floating` 浮在手上方＋環），光暈用元素色（同心半透明圓，沒有元素用材質色）；側面書、法球畫在身體後面、拿在遠側手 (5.6,−27)、往前移到身體外（x 約 6～10）、暗 25% |
| `client/src/render/inkDoll.ts` | 掛入上述；腿的靴高依 `footTop()`（鞋 −3.4、鐵靴 −9）；`mail` 躯幹改用裝備色（原固定鐵色，照需求「顏色照 itemColors」）；`coat` 不畫腰帶；手改由 `drawInkHand()` 畫（正、背傾角 ±0.32 rad、側面 −0.54）；書、法球側面統一走 `legacyHeld`（遠側、暗 25%），不再用舊 `offhandSide` |
| `client/src/render/inkGear.ts` | 美術 PM C-1b 必修 2、3（見下）；匯出 `darken`、`metalOf`、`drawHelmet` 給新檔用 |
| `client/src/dev/dollGallery.ts` | 新增 ⑨（身體、頭、手、腳、副手各形制 × 四朝向）、⑩（重甲、旅人、術士三套 × 四朝向） |
| 測試 | `inkArmor.test.ts`（新，8 個）；`inkGear.test.ts`、`dollGear.test.ts` 配合新畫法更新 |

## 美術 PM C-1b 必修

1. **側面圓盾盾邊**：程式本來就在 (7,−23) 畫 2×7 窄橢圓、畫在身體之後、頭之前（與 `storyDoll.js` `offhand()` 相同），單元測試與瀏覽器單張放大渲染（藍色窄橢圓出現在胸前、手與劍之後）都確認有畫。但 4 px 寬的邊大半被近側手與劍的握柄遮住，在 52px 縮圖幾乎看不到，可能就是驗收時「不見」的原因。**位置與順序沒改**，新增測試固定「盾邊色在身體之後、膚色頭之前」。請美術 PM 重驗；若仍要更明顯，請告知要把橢圓外移幾 px（見待決 1）。
2. **斧頭**：正面、背面的斧頭左右翻轉（大刃朝外、小刃朝內）；成對時兩把都朝外（副手原本的鏡像與翻轉抵銷）；側面不變。`inkGear.test.ts`「握點」測試。
3. **匕首**：正面往外斜 0.5 rad，成對時副手鏡像也朝外；側面仍 0.75、背面仍豎直。`curved` 劍身弧度沒做（美術 PM 說不強制，C-2b 順手再說）。
4. **書、法球位置**：照美術 PM 回覆實作（側面遠側手、身體外 x 約 6～10、暗 25%；正面書立身側、法球托掌帶元素光暈；背面被身體遮大半）。

## 驗收對照

| 條件 | 結果 | 證據 |
|---|---|---|
| `mail`、`coat`（含形制）C 版，四方向 | 通過 | `inkArmor.test.ts`「每種形制四方向…」「身體」；截圖 `C-2a-doll-gallery-body-head-south.jpg`、`-east.jpg`、`-four-facings.jpg` |
| 頭 `hat`（wide）、`circlet`（bandana／crown）、`cap`、`helmet` 其他形制（horned／greathelm） | 通過 | 「頭」測試（七種 × 前背側）；截圖同上 |
| 手 `cloth_gloves`、`leather_gloves`、`gauntlets`、`bracers` 畫出造型 | 通過 | 「手」測試（用裝備色／露膚色、袖口）；`C-2a-doll-gallery-hands-feet-south.jpg` |
| 腳 `shoes`、`iron_boots` | 通過 | 「腳」測試；同上截圖 |
| 副手 `kite_shield`（含塔盾）、`tome`、`orb`；側面在身體後面、書不被身體遮掉；盾正面圓面／側面一條邊／背面木色＋皮帶 | 通過 | 「副手」「側面書、法球…」測試；`C-2a-doll-gallery-offhand-south-north.jpg`、`C-2a-doll-gallery-four-facings.jpg` |
| 沿用現行輪廓、改用 `ink()`／`stroke()`、顏色照 `itemColors()` | 通過 | 測試驗證填色等於 `itemColors`；金屬類用 `metalOf`（同 C-1b） |
| 不認得的 kind／form／材質／顏色／元素 → 預設，不報錯 | 通過 | 「手」「副手」測試的壞值案例；`dollGear.test.ts` 全組合自測（`gear-all`）通過 |
| 確定性、不用 `Math.random()` | 通過 | 「每種形制四方向都畫得出來、重畫完全相同、不用 Math.random」（spy） |
| 檢查清單「裝備與武器」防具與盾打勾 | 通過（防具與盾）；武器留 C-2b | 見上 |
| tsc、vitest | 通過 | `corepack pnpm -C client exec tsc --noEmit` 無輸出；`vitest run src/render src/dev` 27 檔 272 測試全過（含 `dollGear.test.ts`、`paperdoll*.test.ts`） |
| build | 通過 | `corepack pnpm -C client build` 成功 |
| 排版煙霧檢查 | 通過 | 1600×900、800×600、1600×900 shortBottom 皆全 PASS（每次載入後第一次 `runCase` 會因戰鬥尚未開出而全 FAIL，再跑一次即 PASS，與 C-1a 報告相同的既有現象，與本段無關）；`localStorage.clear()` 先做 |
| 截圖 | 完成 | `docs/phases/img/C-2a-doll-gallery-four-facings.jpg`（三套 × 四朝向）、`C-2a-doll-gallery-body-head-south.jpg`、`-body-head-east.jpg`、`-hands-feet-south.jpg`、`-offhand-south-north.jpg`、`C-2a-gear-gallery.jpg`（裝備圖示本段不動）、`C-2a-battle.jpg`（內建瀏覽器只能存 JPEG） |

`doll-gallery`、`gear-gallery` 是 vite 開發頁（`trpg serve` 不含），本段用 `vite --port 5190` 看，檢查完已關閉；`trpg serve --port 8014` 也已關閉，只關自己的 PID。

## 舊程式（留給 C-2b 清）

本段之後不再被畫圖路徑使用：`paperdoll.ts` 的 `drawHelmet`、`drawBandana`、`drawHeadgear` 的 horned／greathelm／wide／cap／crown／bandana 分支；`paperdollGear.ts` 的 `drawFeet`、`drawCoat`、`drawMailPattern`、`drawHandsGear`、`drawWideHat`、`drawCap`、`drawGreathelm`、`drawOrb`、`drawTowerShield`；`paperdollSideGear.ts` 的頭部、副手函式；`InkHooks.headgear`、`InkHooks.offhandSide`（目前只剩未知 kind 的退路）。`drawFigureSide` 與其測試仍引用，與 C-1b 報告一致，等 C-2b 一併刪除。武器小圖示用的 `drawWeapon` 分支不動。

## 待 PM 決定

1. **側面圓盾盾邊**：見必修 1，沒改位置；若美術 PM 重驗仍嫌不明顯，要不要把橢圓外移（例如 x 7→8）或加粗？
2. **`mail` 軀幹顏色**改用 `itemColors`（C-1a 固定鐵色）；預設材質若為鋼，畫面會略亮。
3. 鎖甲紋路是 36 筆左右的短筆畫，只畫在躯幹中央 ±4.6 px，不延伸到袖子。
4. `coat` 不畫腰帶、下襬長到 −5（蓋住大半條腿），`cape` 形制的肩披只畫在肩上。
5. 手套與護手的袖口順著前臂傾角畫（正、背 ±0.32 rad、側 −0.54 rad）；正面持盾時被盾遮住的那隻手本來就不畫。
6. 角盔側面兩支角：遠側角 x 更靠後且暗 30%（沿用舊畫法的色）；正面兩支角朝外上。
7. `bandana` 垂尾在正面、側面畫在右側（舊畫法也是），背面畫腦後結。
8. 鐵靴 `sabaton` 尖頭只加長鞋尖（正面 7、側面 9.8），其他靴型不動；`greaves` 的 `knee` 護膝仍沒畫（C-1b 範圍，C-2b 或後續確認）。
9. 側面書、法球統一畫在遠側手後面，但身體不遮掉的部分只有前緣約 4 px；若美術 PM 要更明顯，可再外移。
10. 倒地姿勢、`stout`／`tall` 沒另外驗證新部件（只確認不報錯、確定性）。
