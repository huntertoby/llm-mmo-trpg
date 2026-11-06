# Phase 3-16b 報告｜紙娃娃小人（含 3-16a 小修與美術小修）

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 11456a5 | 後端 `UnitView.weapon_id`（只新增欄位）、重產 `openapi.json`／`schema.d.ts`、pytest |
| 837d0b9 | `heightModel.ts` 刪除 `sides`／`shadows`／`SideFace`／`Shadow`／`sideThickness`／`shadowWidth` 與對應測試；高度徽章只標與鄰格不同高的格子 |
| a8a3293 | 美術小修（草叢、煙霧、黑暗、聖光、碎石、薄冰） |
| 3d87faa | 紙娃娃：`render/appearance.ts`、`render/paperdoll.ts`、`ArtTextures.figure`、`BattleRenderer.unitSprite` 改版、致命 × 框淡化、單位依 y 排序、`ringArrow` |
| 7dfd441 | 截圖 |

## 2. 驗收逐條

| 條件 | 結果與證據 |
|---|---|
| `UnitView.weapon_id` 新增，API 檔重產 | 通過。`tests/engine/test_view.py::test_the_view_describes_the_map_and_units`；`schema.d.ts` 只多這個欄位 |
| 分層繪製（披風→腳→身→手→披風（背）→頭→髮→頭飾→主手→副手），背面武器在身後 | 通過。`paperdoll.ts` `drawFigure`；截圖 `3-16b-facings-*.jpg` |
| 主手依武器外觀表，未知依 `weapon_class`，都沒有畫劍；雙手武器副手留空 | 通過。`paperdoll.test.ts`（weaponLook、雙手武器）。注意：`UnitView` 只加 `weapon_id`，前端目前拿不到 `weapon_class`，所以實際上未知武器一律畫劍（函式已支援傳入 class） |
| 防具、膚色、髮型由外觀表（鍵 `template_id`）；未知範本依陣營預設；召喚物用骷髏；不認得 kind 只跳過該欄位；材質未知用布料色、元素未知不套色 | 通過。`resolveDoll` 系列測試 |
| 朝向（south 正面、north 背面不畫臉、east／west × 0.9 眼睛偏、主手在前）、底圈朝向尖角、倒地、圖騰 | 通過。`handSides`、`ringArrow` 測試；截圖 `3-16b-facings-*`、`3-16b-downed-totem.jpg` |
| 保留陣營辨識、HP 條、代號、狀態徽章、行動中、英雄外圈 | 通過（實機截圖 `3-16b-summon-*`、`3-16b-battle-party.jpg`）：陣營底圈三色、代號改為左下小圓標、行動中為黃色虛線橢圓、英雄為白色外圈、炸彈／蓄力／召喚輪數／倒地徽章保留（蓄力徽章移到左上以免與代號重疊） |
| 高度標記只標與任一鄰格不同高的格子 | 通過。`art.test.ts`「高度徽章」；地圖外不算鄰格 |
| 致命 × 框淡化 | 通過（alpha 0.8→0.3、0.6→0.22，線寬 1.5） |
| 刪除 `heightModel.ts` 不再使用的部分，保留懸崖線與 `clientToTile` 測試 | 通過 |
| 快取（範本＋裝備＋朝向＋姿勢），禁 `Math.random` | 通過。`dollKey`（鍵排序）；測試中 `Math.random` spy 未被呼叫 |
| 檢查 | `uv run python scripts/check.py` 全過；`pnpm -C client build` 成功；ruff／format／mypy／client typecheck 全過 |

## 3. 複雜度 noqa

無新增、無移除（繪圖拆成小函式，未超過 C901 15）。

## 4. 修改既有測試期望

- `drawModel.test.ts`：單位順序改為「倒下的在前，其餘依 y 由上往下」（移植需求第 2 節第 11 層）。
- `art.test.ts`：`heightBadgeText` 改為 `(model, tile)`，期望改為「邊緣才標」。
- `heightModel.test.ts`：刪除側面、投影相關案例。
- `testFixtures.ts`：UnitView fixture 加 `weapon_id`。

## 5. 美術小修（美術 PM 檢查 3-16a 的 7 項）

| # | 處理結果 |
|---|---|
| 1 草叢 | 重畫：3–4 簇深色（`#3f6e2a`，色票新增 `bush`）草葉＋亮色（`#8dbb62`）葉片，下方淡影子，約佔格子 70%；放在草地上仍較深、較高 |
| 2 黑暗 | 移除橢圓斑塊，改深紫徑向暈染（中心較深）＋2–3 道捲曲煙絲 |
| 3 煙霧 | 色票 `#dcdfe6`，底色透明度 0.35，4–6 個較大半透明雲團。限制：貼圖以格子為界裁切，雲團只能貼著格緣被切，**無法超出格子**（要超出需把表面層獨立成未裁切的圖層，未做） |
| 4 高度徽章 | 同驗收（只標邊緣） |
| 5 聖光 | 底色 `#ffe58a`、透明度 0.5，中心徑向光暈，十字閃光保留 |
| 6 碎石 | 3–5 塊大石，約佔 70%，加亮面與影子 |
| 7 薄冰 | 邊緣改不規則十一邊形，從一點放射 6 道折線裂紋 |

截圖 `docs/phases/img/3-16b-art-fixes.jpg`：草叢／碎石／薄冰（石、草、土上）與煙霧／黑暗／聖光（石、草上，並列油表面做對照）。這張是用臨時頁面直接呼叫 `drawTile`／`drawObject` 畫出（臨時頁面已刪除、未提交），**不是在靶場以工坊製造**。

## 6. 外觀表（`render/appearance.ts`）

武器外觀（`weapon_id` → 主手 kind；元素取自武器）：`one_handed_sword`→sword（鋼）、`greatsword`→greatsword（雙手）、`dagger`→dagger（鐵）、`bow`→bow（木，雙手）、`fire_staff`／`lightning_staff`／`frost_staff`→staff＋火／雷／冰（雙手）。元素色取自 `ELEMENT_VFX` 主色（物理不套色）。

範本外觀（鍵 `template_id`；`weapon_id` 決定主手，副手在雙手武器時為空）：

| 範本 | 身 | 頭 | 手／腳 | 副手／披風 | 備註 |
|---|---|---|---|---|---|
| hero_fighter | 板甲 | — | 鐵手套／脛甲 | 圓盾／藍披風 | 棕短髮 |
| hero_mage | 法袍 | 法師帽 | —／靴 | 魔典（雙手法杖時省略） | 白長髮 |
| hero_archer | 綠皮甲 | 綠兜帽 | 手套／靴 | — | 橘長髮 |
| bandit | 皮甲 | 紅頭巾 | —／靴 | — | |
| bandit_archer | 皮甲 | 褐兜帽 | —／靴 | — | |
| bandit_shieldbearer | 鎖甲 | 鐵盔 | —／靴 | 鳶盾；主手生鏽 | |
| bandit_boss | 鎖甲 | 角盔 | 鐵手套／脛甲 | 紅披風 | 史詩外光 |
| summon_skeleton_warrior | 肋骨 | — | — | 主手生鏽 | 骷髏臉 |
| 補充：hero_stormcaller | 法袍 | 法師帽 | —／靴 | — | 藍髮 |
| 補充：bandit_warlord | 板甲 | 角盔 | 鐵手套／脛甲 | 紅披風 | 史詩外光 |
| 補充：sim_companion_fighter／archer | 同 hero_fighter／hero_archer | | | | 隊友實機看到是預設外觀，故補 |

退回：未知範本我方＝布衣＋靴、敵方＝皮甲＋頭巾＋靴；未知召喚物＝骷髏；圖騰（`totem`）＝圖騰柱；訓練木樁等未列範本走陣營預設。

## 7. 待 PM 決定

1. **`weapon_class` 未加進 `UnitView`**（指示只加 `weapon_id`）。目前武器 id 不在表內時一律畫劍；若要弓／杖也能退回，需再新增 `weapon_class` 欄位（只新增欄位）。
2. **雙手武器副手留空**依 `weapons.yaml`：法杖、弓都是雙手，所以法師的魔典不會出現（樣張有）。若要保留法師拿書，需改 `two_handed` 或另訂規則。
3. 補充範本（stormcaller、warlord、sim_companion_*）與樣張不同，請美術 PM 過目；`training_dummy`、`std_enemy_t*` 目前是敵方預設外觀，木樁沒有專屬造型。
4. 錘、長柄、弩（移植需求 D）未做；不認得的主手 kind 會跳過。
5. 煙霧雲團無法超出格子（見第 5 節 #3），要做需調整貼圖／圖層架構。
6. 美術小修截圖不是用工坊靶場產生；PM 若要實機證據，可用工坊製造相關表面。
7. 倒地姿勢是整個小人旋轉 90° 躺下（頭朝右、半透明），原有的紅色叉叉保留；是否去掉叉叉請看實機。
8. 單位排序改為依 y（倒下者在底層）；同一 y 的單位依 ID 順序，視覺上無碰撞處理。
9. 截圖限制：內建瀏覽器窗格實際解析度偏低，1600×900 設定下截圖只有 800×450，細節以 800×450 視窗或遊戲內放大截取（`3-16b-battle-1600x900.jpg` 為 1600×900 全畫面）。
10. 蓄力徽章位置從左下移到左上（代號小標佔了左下），炸彈徽章仍在右下。

## 8. 截圖（`docs/phases/img/`）

- `3-16b-battle-1600x900.jpg`：1600×900 戰鬥全畫面
- `3-16b-battle-party.jpg`：我方戰士、法師（召喚師）、弓手與盜賊系列同場
- `3-16b-facings-fighter-mage.jpg`、`3-16b-facings-archer-bandit.jpg`、`3-16b-facings-boss-skeleton.jpg`：四個朝向
- `3-16b-summon-skeleton.jpg`、`3-16b-summon-totem.jpg`：召喚物與圖騰（實機）
- `3-16b-downed-totem.jpg`：倒地姿勢與圖騰柱
- `3-16b-art-fixes.jpg`：美術小修
