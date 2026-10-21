# Phase 3-18b 完成報告｜單位外觀、倒地與其他介面小修

分支 `worktree-agent-aeebfd3f1d455d2ea`（從 `b08c9e7` 分出，未 push、未合併）。`uv run python scripts/check.py` 全過（ruff、format、mypy、import-linter、pytest、client typecheck、vitest）；`corepack pnpm -C client build` 成功。

## 逐條驗收（19.6）

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | vitest：倒地兩種狀態繪製資料、`weapon_class` 退回、狀態徽章對應、特效推導新增四種 | 過。`render/unitLook.test.ts`（倒地可復活／救不回／不含文字／閃動週期、`statusBadges` 對應 `time_bomb`／`charging`）；`render/appearance318b.test.ts`（四個外觀、未知武器依類別退回、武器小圖示）；`render/lowWall.test.ts`；`battle/vfx318b.test.ts`（水花、狀態上色、傳送消散出現、傳說蓄力共 9 條）；`battle/tileCard318b.test.ts`（資訊卡） |
| 2 | pytest：`UnitView.weapon_class` 對所有內容武器有值 | 過。`tests/engine/test_view.py::test_every_content_weapon_has_a_weapon_class_in_the_view`；另 `tests/api/test_runs_api.py` 驗英雄的 `weapon_name_zh`／`weapon_class`、`tests/narrative/test_skill_icon.py` 驗延遲回合數 |
| 3 | 截圖 | 見下表 |
| 4 | `check.py` 全過、`pnpm build` 成功 | 過（見上） |

截圖（`docs/phases/img/`，用暫時的 harness 頁面以真實 `BattleRenderer`／元件繪製，harness 未提交）：
- `3-18b-downed-wall-badges.png`：可復活（B、D：愛心徽章＋綠虛線橢圓閃動＋透明 0.6）與救不回（a：墓碑徽章、去色、灰底圈）、三格相連矮牆加單獨一格、炸彈與蓄力徽章（部件庫圖示）、站在高台上的單位（底座陰影，給美術 PM 判斷）。
- `3-18b-four-units.png`：由左至右 軍閥、頭目、風暴法師、紫袍法師、隊友戰士、主角戰士、隊友弓手、主角弓手。
- `3-18b-tile-cards.png`：有持續時間／永久表面（沒有「由技能產生時持續」）／木箱標籤一行／油桶／收起。
- `3-18b-hero-weapon.png`：英雄面板的武器名稱＋小圖示（含未知武器退回杖）。
- `3-18b-teleport-vanish.png`、`3-18b-teleport-appear.png`：傳送起點消散、終點出現。
- `3-18b-marks-over-height.png`：移動、預覽、攻擊框畫在南邊高格之上。

## 19.5 各項

1. **倒地圖示**：新檔 `render/unitLook.ts`（純資料 `downedLook`、`pulseAlpha`）、`render/unitSprite.ts`（繪製）。紅叉與文字全拿掉；透明度與去色（`ColorMatrixFilter`）只套在小人。
2. **外觀小修**：`appearance.ts`，新增 `dark_cape`、`storm_robe`、`storm_hat`；軍閥移除 `rarity`（不加外光）。
3. **`weapon_class`**：`UnitView.weapon_class`（後端）→ `UnitDraw.weaponClass` → `resolveDoll`（原有 `weaponLook` 已支援類別退回）。`client/openapi.json`、`schema.d.ts` 已重產。
4. **狀態徽章**：炸彈、蓄力徽章改用 `skillIcon.statusTile` 的圖示（黑底圓＋狀態色外框＋右下數字）。地圖上原本只有這兩種狀態徽章，沒有新增其他狀態。
5. **地形資訊卡**：物件標籤（前 N 行，N ＝ glossary 的 `tags` 數）濃縮成一行、去括號補充；永久表面（`surface_remaining` 為 null）不寫「由技能產生時持續…」；格子上有單位時可收起（只留地形標題），在「版面」面板勾選，存 localStorage（`battle/tileCardPrefs.ts`）。
6. **特效補強**：水表面（`surface_changed` cause `effect`、after `water`）用 `water` 水花；無傷害技能取施加的第一個狀態，色取 `skillParts.statusColor`（`render/statusVfx.ts`，與圖示同一份）；傳送類位移（fade）起點消散、終點出現（`vfx.warpPlan`、`vfxEffects.warpEffects`，掛在 `animate`）；傳說技能蓄力 380ms（一般 160ms）＋金色匯聚光點、反向符文環、光柱。配色優先序：傷害元素 → 觸及元素 → 水 → 治療護盾 → 狀態 → 預設。
7. **英雄面板武器**：`HeroOut` 新增 `weapon_name_zh`、`weapon_class`；`RunHeroPanel` 顯示武器小圖示（`render/weaponIcon.ts`，用小人手持的同一套畫法並自動縮放填滿）＋名稱。
8. **矮牆**：`objectArt.ts` 的 `lowWall` 照 `docs/art/矮牆.md`。
9. **3-18a 遺留**：延遲回合數改由延遲段 `release` 對照（`narrative/skill_icon._DELAY_ROUNDS`，見待決定 1）；刪除 `.asm*` CSS；**「隨機一個」**原因在前端：草稿非空時用 `window.confirm`，內嵌瀏覽器直接回傳 false，按鈕變成什麼都不發生（已用瀏覽器重現，`confirm()` 回傳 `false`，且沒有發出 `/workshop/random`）。改成頁內二段確認（按鈕變「確定取代並隨機」＋「取消」），已在瀏覽器驗證。
10. **3-19 遺留**：高亮改畫在 `marks` 圖層（所有排之上，仍用抬高座標）；`RowStack` 移除 `marks`；▲N 徽章原本就只標與鄰格不同高的格子（`heightBadgeText`＋既有測試，非每格都標），未改；底座陰影保留（截圖給美術 PM）；`BattleRenderer.ts` 由 924 行降到 **781 行**（單位繪製、徽章、倒地搬到 `unitSprite.ts`，文字工具搬到 `labels.ts`，效果啟動收成 `launch()`）。

## 新增的複雜度 noqa

無。

## 待 PM 決定

1. **延遲回合數**：規則上延遲段的 `release`（`next_turn`、`attacked`）都是 1 回合，沒有可設的回合數欄位，所以「實際值」仍是 1，只是改成由資料推導。限時傳說（`activation: timed`，`legendary_timed_rounds`）的「延遲」代價目前沒有數值；若要寫「3 回合」需讓 `icon_of` 取得規則（後端改動）。
2. **資訊卡標籤濃縮**會丟掉括號內的數值（例如半掩護的「命中 −2」），仍可在說明文字或圖例查；是否保留？收起狀態只留地形標題，區域與陷阱資訊也一併收起。收起的開關放在「版面」面板，因為浮動卡 `pointer-events: none` 且滑開就消失。
3. **清空重來**（`WorkshopScreen.reset`）同樣用 `window.confirm`，在內嵌瀏覽器會有同樣的無反應問題，這段沒動（僅改「隨機一個」）。
4. **匕首小圖示**因原畫法本身有傾斜再加斜放，看起來偏直；其他武器沒問題。
5. 高亮現在蓋在單位之上（色塊半透明）；若要在單位之下需把高亮拆成「地面層」與「單位層」。
6. 水花配色與狀態色是新增的配色鍵（`water`、`status:<id>`），傳送特效顏色寫死為淡紫（`BANISH`，與放逐高亮同色系）；傳說蓄力金色寫死。是否要納入 `ELEMENT_COLORS` 統一管理？
7. 截圖為 harness 頁面（真實渲染程式，非整個戰鬥畫面流程）；截圖檔是由瀏覽器 JPEG 轉存的 PNG。
8. 開發中誤把預覽面板屬於 PM 工作階段的 `tab-2`（原指向 `127.0.0.1:8319`）導向了 harness 頁，之後無法導回；需要的話請 PM 自行重開該分頁。
