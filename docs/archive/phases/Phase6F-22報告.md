# Phase 6F-22 報告：被前方高台擋住的單位，HUD 照常畫在高台之上

> 實作者：worktree `dev/6f22`（從 main `87764b8e` 開）。沒有 push、沒有 rebase。依據：`docs/art/6F-21檢查.md` 第 5 節（美術 PM 11-06 決定）。

## 1. 完成表

| # | 做什麼 | 結果 | commit |
|---|---|---|---|
| 1 | 圖層 | 繪製器新增全域圖層 `hudTop`（Pixi `RenderLayer`），排在剪影虛線（`silhouettes`）之後、游標高亮（`hover`）之前。單位被南邊高台擋住（`occluded`，和畫剪影同一個判斷的高台部分）時，`RowStack.attachHud` 把 HP 條（含護盾條）、狀態列（含「+N」膠囊）、朝向三角形、召喚物回合數、倒下徽章、炸彈／蓄力／灌注徽章掛到這一層；身體照舊被擋、畫剪影。節點仍是單位圖層的子節點（位置、透明度、升降跟著單位），照子節點順序掛，徽章仍在 HP 條與狀態列之上。沒被擋的單位不呼叫、不變 | `63e7c3be` |
| 2 | 節點標籤 | HP 條 `hp-bar`、非朝南的朝向三角形 `facing-arrow`、倒下徽章 `downed-badge`（`render/minMark.ts`）。朝南、有 HP 條的三角形照 6F-21b（`arrowTop` 或南邊一排的 `under`，本來就在高台之上），不動 | `63e7c3be` |
| 3 | 移動、轉身 | 移動途中（`attachMarks` 換排）HUD 先回到跟著單位畫、徽章回所在那一排的 `marks`（剪影本來就藏起來）；停下重畫、轉身重建時再依新位置判斷 | `63e7c3be` |
| 4 | 測試 | `client/src/ui/occludedHud.test.ts`（6 項）：節點都有標籤、擋住時各 HUD 節點掛在高台之上的層且仍是子節點、非 HUD 節點不動、順序；沒被擋不變；移動途中回原層；召喚物回合數與倒下徽章；接線（層順序、只在 `occluded` 時給層、畫單位與轉身各一處） | `63e7c3be` |
| 5 | 補拍 | 見下 | `01ca5c43` |

## 2. 截圖（`docs/art/shots/6f22/`，4 張，jpg 80，最大 116 KB）

開闊平原（排版煙霧檢查的種子與弓），攔下戰鬥回應：弓手隊友 (1, 5) 改成朝東、HP 60%、護盾、蓄力＋燃燒＋緩速＋防禦（蓄力徽章＋「+3」膠囊），自己那格 ▲0、南邊 (1, 6) 改成 ▲2／▲3。主角回合、畫面靜止才拍；`_zoom` 是同一幀裁切放大 2.5 倍。

- `docs/art/shots/6f22/6f22_occluded_high2_1600.jpg`＋`docs/art/shots/6f22/6f22_occluded_high2_1600_zoom.jpg`：南邊 ▲2。腳被高台蓋住，HP 條、「+3」膠囊、朝東三角形、蓄力徽章畫在高台北緣之上，看得到血量。
- `docs/art/shots/6f22/6f22_occluded_high3_1600.jpg`＋`docs/art/shots/6f22/6f22_occluded_high3_1600_zoom.jpg`：南邊 ▲3，高台蓋得更多，HUD 一樣在上面。

## 3. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 248 檔、3118 項全過 |
| `tsc --noEmit`、`pnpm build` | 過（只有原本的 chunk 大小提醒） |
| 排版煙霧檢查 1600×900、1040×624、800×600 | 三個都 13 PASS、0 FAIL |

## 4. 待 PM 決定

1. **屋頂蓋住屋後的人**（6B-ART1 `roofCovers`，同樣畫剪影）：規格只說高台，這次沒改，HUD 照舊可能被屋頂蓋住。要不要比照？
2. **HUD 在全域層的副作用**：被擋單位的 HUD 現在在所有排之上，所以（a）南邊高台上若站著人、他的頭伸進北邊這格時，北邊這個人的 HP 條會畫在他身上；（b）被擋那格若有煙霧、黑暗的上層霧，HUD 不再被霧蓋住。截圖情境沒有出現這兩種，照規格「HUD 照常畫在高台之上」優先。
3. 護盾條只有 2 px，在移動格的淺藍框線旁 zoom 上不太分得出來（圖層和 HP 條相同，測試有涵蓋）；沒改尺寸。

## 6F-22b：6F-22 驗收後的修正

> 依據：`docs/art/6F-22檢查.md` 第 2 節（美術 PM 11-07）。worktree `dev/6f22b`（從 main `aec794a4` 開），沒有 push、沒有 rebase。

### 1. 完成表

| # | 做什麼 | 結果 | commit |
|---|---|---|---|
| 1 | 資訊洩漏查核 | 見下面「查核結論」；現況沒有洩漏，不用改繪製邏輯，寫測試鎖住 | `99e320a9` |
| 2 | 屋頂後的單位 | `hudLayerOf` 改成 `occluded(model, u) \|\| roofCovers(model.scenery, u)`：屋頂蓋住屋後那一列的人（6B-ART1，同樣畫剪影）時，HUD 一樣掛 `hudTop`（畫單位與轉身兩處共用這個判斷） | `99e320a9` |
| 3 | 護盾條外框 | 護盾條照舊 2px、淺藍 `0x9fd8ff`；底下先畫一圈 1px 黑框（`SHIELD_OUTLINE`，和 HP 條的黑底同色）。`hpBoxOf` 跟著含外框（徽章讓開 HP 條的方框多 1px） | `99e320a9` |
| 4 | 「▲N」被蓋 | `heightMarkAtCorner`（`render/heightMark.ts`）：北邊那格有人、而且被這一格擋住（這格比較高 ＝ 他的 HUD 在 `hudTop`）時，「▲N」改放這一格左下角（底離下緣和原本離上緣一樣 `HEIGHT_MARK_BG.y`，跟著倍率重排，`heightMarkCornerDrop`）；其他情況照舊左上角 | `99e320a9` |
| 5 | 補拍 | 見第 3 節 | 本節 commit |

### 2. 第 1 項查核結論（資訊洩漏）

- **現況沒有洩漏。** 戰鬥裡沒有「單位看不見（不顯示或只顯示「?」）」的狀態：
  - 伺服器：`trpg.engine.view.battle_view` 把所有在場單位（含 HP、護盾、狀態）完整送給前端，`UnitView` 沒有「看不見」的欄位。隱蔽（`concealed` 狀態、黑暗表面、草叢）在規則上只是戰鬥修正（遠程射程上限、潛行偷襲），不是隱形。
  - 前端：`buildDrawModel` 只濾掉不在場的單位（`onField`）；煙霧、黑暗只在單位下半身疊一層霧（`drawVeils`），隱蔽的人畫成半透明（`CONCEALED_ALPHA` 0.55）。身體一直看得到，所以 HUD 照畫，符合美術 PM「單位本身看得到時 HUD 照畫」。
  - 繪製器沒有任何地方把單位身體設成 `visible = false` 或透明 0 而留下 HUD。
- **6F-22 改掛 `hudTop` 之後**：HUD 節點只用 `RenderLayer.attach` 換畫的順序，父節點仍是單位圖層；Pixi 的可見度（`globalDisplayStatus`）與透明度（`groupAlpha`）照場景樹由單位圖層往下傳，所以將來若身體被藏起來，掛在 `hudTop` 的 HUD 也一起不畫。**走路途中**（`attachMarks` 讓 HUD 回原層）也一樣。
- **測試**：`client/src/ui/hiddenUnitHud.test.ts`（10 項），第 1 項相關的 5 項在 describe「6F-22b 第 1 項：看不見的單位不畫 HUD（資訊洩漏）」：
  - 「現況：煙霧、黑暗裡隱蔽的敵人照常畫出（身體在、半透明），HUD 照畫——單位看得到」
  - 「伺服器的 UnitView 沒有「看不見」的欄位（多了這種欄位時這裡會失敗：要一起讓 HUD 跟著不畫）」：掃 `api/schema.d.ts` 的 `UnitView`，出現 `hidden`／`visible`／`unseen`／`revealed`／`obscured` 這類欄位就失敗
  - 「擋住時掛在 hudTop：身體藏起來（visible = false）或透明（alpha 0）時，HUD 跟著不畫；看得到時照畫」：用 Pixi 真正的 `updateRenderGroupTransforms` 算出每個 HUD 節點的可見度與透明度
  - 「沒被擋……與移動途中回原層後，一樣跟著身體藏起來」
  - 「HUD 只用 RenderLayer.attach 換畫的順序，不搬到別的容器」
- 另外 `client/src/ui/occludedHud.test.ts` 的接線測試改成含屋頂；`client/src/ui/badgeCapsule.test.ts` 的「▲N」接線字串跟著改（多了左下角的重排）。

### 3. 截圖（`docs/art/shots/6f22/`，本段 8 張，jpg 80，最大 120 KB）

同 6F-22 的做法（排版煙霧檢查的種子與弓，攔下戰鬥回應：弓手隊友 (1, 5) 朝東、HP 60%、護盾、蓄力＋燃燒＋緩速＋防禦，南邊 (1, 6) 改 ▲2／▲3），但地圖現在是「雲海吊橋」（同一個種子，6F-22 時是開闊平原）。主角回合、「移動」選著（藍色移動格）、畫面靜止才拍；用 headless Chrome（CDP）在 1600×900 拍，`_zoom` 是同一場景裁切放大 2.5 倍。

- `docs/art/shots/6f22/6f22_occluded_high2_1600_v2.jpg`＋`docs/art/shots/6f22/6f22_occluded_high2_1600_v2_zoom.jpg`：▲2。護盾條有黑框、和旁邊移動格的淺藍框線分得開；「▲2」在那格左下角，沒被 HP 條蓋到。
- `docs/art/shots/6f22/6f22_occluded_high3_1600_v2.jpg`＋`docs/art/shots/6f22/6f22_occluded_high3_1600_v2_zoom.jpg`：▲3，同上，「▲3」在左下角。
- `docs/art/shots/6f22/6f22_roof_1600_v2.jpg`＋`docs/art/shots/6f22/6f22_roof_1600_v2_zoom.jpg`：屋頂後。開發用頁面 `ambient-gallery` 的雲嶺小鎮臨時改成酒館往南移 2 格、主角站在屋後那一列（臨時檔拍完已刪，不進 git）：身體被屋頂蓋住畫剪影，HP 條與朝向三角形畫在屋頂上。
- `docs/art/shots/6f22/6f22_smoke_concealed_1600_v2.jpg`＋`docs/art/shots/6f22/6f22_smoke_concealed_1600_v2_zoom.jpg`：煙霧中隱蔽的單位（弓手站在煙霧格、帶隱蔽，南邊 ▲2）。**因為現況沒有「看不見」的單位，拍不出「不顯示所以沒有 HUD」的畫面**：這張是「隱蔽但看得到（半透明）→ HUD 照畫」的現況。不畫 HUD 的部分以上面的測試鎖住。

### 4. 驗收

| 項目 | 結果 |
|---|---|
| vitest 全量 | 249 檔、3128 項全過 |
| `tsc --noEmit`、`pnpm build` | 過 |
| 排版煙霧檢查 1600×900、1040×624、800×600 | 三個都 12 PASS、1 FAIL。FAIL 是「戰鬥：四角飾件沒有壓到內容」（主角卡左下角飾件 × 技能晶片圖示 `svg.skill-chip-glyph`），**換回 main `aec794a4` 的繪製程式重 build 一樣 FAIL**，和本段無關（本段只動 Pixi 繪製，沒動 HTML）；6F-22 當時 13 PASS，可能是之後同一個種子的開局（地圖、技能）變了 |

### 5. 待 PM 決定

1. **「看不見的單位」目前不存在**：隱蔽只是戰鬥修正，伺服器把隱蔽敵人的位置與 HP 完整送來、前端照畫（半透明＋HUD）。若設計上要「煙霧／黑暗裡的敵人看不見」，要在伺服器端依陣營濾掉或遮住資料（`battle_view`），前端再補「不顯示」的畫法；這是規則／玩法問題，請玩法 PM 決定。前端已有測試：`UnitView` 一多了這類欄位就會提醒。
2. 排版煙霧檢查「四角飾件」那一項 FAIL（main 上也是），需要另排一段看主角卡飾件與技能晶片。
3. `docs/art/shots/6f22/` 現在共 12 張（6F-22 的 4 張＋本段 8 張）；本段自己是 8 張（≤ 10）。美術 PM 通過後照 6.5.2 清理。
4. 「▲N」改左下角只看北邊那格「有人而且被這一格擋住」；北邊的人在走路途中、或北邊的人 HUD 因其他原因（例如南邊沒人但狀態列很高）蓋到時不改，等重畫時再判斷。
