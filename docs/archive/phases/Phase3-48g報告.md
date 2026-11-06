# Phase 3-48g 報告：裝備分頁屬性詞條可換屬性、成對武器勾選、武器外觀元素色

規格：`docs/phases/Phase3計畫.md` 第 57 節（第 1、2、3a 點；第 3 點不改）。

## 做了什麼

1. **屬性詞條可換屬性**（`CustomItemForm.tsx`、`gearDraft.ts`）：`affix_attr_*` 那一列多一個「屬性」下拉，可直接換成其他屬性（等於換成同類的另一個詞條 id；數值保留並夾在新詞條範圍內；已被其他列用掉的屬性不列）。`swapAffix`／`isAttrAffix` 為純函式，有 vitest。詞條區標題下加一句說明：屬性詞條可換屬性、數值可調，其他詞條要換種類請先移除再重新加入。
2. **成對武器勾選資料驅動**：
   - `GearWeaponInfo` 新增 `pairable`（API；`client/openapi.json`、`schema.d.ts` 已重產）：單手武器，且內容庫有以它為武器的成對物品（`paired: true`）才為真。目前只有匕首（`item_test_twin_daggers`）；3I-4 加入雙匕首、雙手槍物品後自動出現，不必改程式。
   - 前端只有所選武器 `pairable` 才顯示勾選框（單手劍、所有雙手武器、沒選武器都不顯示）；換成不能成對的武器時自動取消勾選；`draftProblems` 補即時提示（雙手武器不能是成對武器）。
   - 伺服器：`loadout_problems` 新增「雙手武器（X）不能是成對武器」，與副手檢查（`occupiesOffHand`、3I-2 副手）並存、不衝突。
3. **武器外觀元素色**（3a）：`draftLook` 現在帶 `element`（明確選了外觀造型時也沿用所選武器的元素）；`GearLook` 新增 `element`，`resolveGear` 把 fire／water／lightning／ice 轉成對應元素關鍵字（ignite／wet／charged／frozen，沿用既有混色與快取鍵，不新增美術）；physical、holy 等沒有色的元素不套色。

## 掃描清單

- 加入後不能改的欄位：屬性詞條（已改為可換）；其他詞條只能移除再加（已加說明）；數值、武器、外觀造型、傳說、成對、副手種類都能隨時改。
- 戰鬥中紙娃娃（`resolveDoll`→`weaponLook`）、單位資訊與英雄面板的武器圖示（`weaponIconItem`）、開局選單的武器圖示：本來就依 glossary 的 `look.element` 上色，沒有缺。缺的只有裝備分頁預覽與格子圖示（已接上）。
- 元素灌注後的武器外觀是否變色：目前不會變（外觀只看 `weapons.yaml` 的 `look.element`，戰鬥中的元素灌注不影響紙娃娃或圖示）。沒有新增美術，列入待決。
- 測試物品（`items.yaml`）沒有帶武器元素的物品外觀，`item.appearance` 也不含元素，格子裡的內容庫物品因此不變色；只有手動組裝（與其格子圖示）有。

## 測試

- vitest 全量：918 通過，1 失敗為既有問題（見待決）；新增 4 個測試於 `client/src/gear/gearPreview.test.ts`（元素傳遞、三種法杖快取鍵不同、成對規則、換屬性）。fixture `catalog.json` 的武器加上 `pairable`。
- `corepack pnpm -C client build` 通過。
- pytest：`tests/api`＋`tests/content` 與 `-m "slow or not slow" tests/cli`：1442 通過（含新增 API 目錄 `pairable` 測試、雙手成對規則測試）；ruff、format、mypy 通過。
- 排版煙霧檢查（先 `localStorage.clear()`）：1600×900、800×600、1600×900＋shortBottom 全 PASS。
- 內建瀏覽器實測（埠 8015，已關閉）：工坊→裝備→主角裝備的「主手」→手動組裝。
  - 選火焰、冰霜、雷電、單手劍時，預覽圖示平均色分別為 (65,57,58)、(58,66,73)、(65,66,63)、(56,59,66)，圖示資料長度各不相同，冰霜偏藍、雷電偏黃綠、火焰偏紅，三者互異。
  - 成對勾選：單手劍、火焰法杖不出現；選匕首才出現。
  - 加入「力量 +1」後下拉可選力量／敏捷／體質／智力／感知／意志，換成意志後該列顯示「意志 +1」。
  - 螢幕截圖工具逾時，只能用像素統計與頁面文字佐證，沒有存圖。

## 待 PM 決定

1. `src/ui/floatCardRule.test.ts` 的「`role=tooltip` 只出現在共用浮動卡元件」在本 worktree 一開始就失敗：`client/src/dev/layoutSmoke.ts` 含 `role=tooltip` 字樣（3-47 引入，與本段無關）。建議把該檔加入規則白名單或改寫量測用字。
2. 元素灌注後的武器外觀是否要變色（上述現況為不變）；要做需美術 PM 定色與疊層。
3. 成對武器目前由「有 `paired: true` 物品的武器」推導 `pairable`；若 3I-4 決定用獨立武器（如 `dual_dagger`）而非「匕首＋paired」，推導規則仍成立；若想用武器欄位明示，再改成資料欄位。
