# Phase 3G-4 報告：裝備測試介面（G4）

規格：`docs/phases/Phase3G計畫.md` 第 0 節、第 4 節；設計：`docs/design/08-裝備.md` 8.23、8.24。
分支 `worktree-agent-ab3c92642be73b8cd`（從 main 的 1836801 分出），未 push、未合併。沒有改詞條結算（`engine/gear.py`、`modifiers.py` 等）、沒有動 roguelite；`styles.css` 只在檔尾新增；API 型別只新增欄位。

## 新增與修改

| 檔案 | 內容 |
|---|---|
| `src/trpg/api/gear.py` | 目錄 `gear_catalog`、驗證與套用 `gear_problems`／`equip_gear`：自訂物品 → `ItemDef` 後 **沿用引擎的** `item_problems`（詞條在白名單、可掛在此欄位／武器／標籤、數值在初值範圍、條數）、`item_appearance_problems`、`loadout_problems`（種類、占用、同一枚戒指、代價型條數）、`weapon_problem`；錯誤訊息把物品與詞條 id 換成名稱 |
| `src/trpg/api/gear_schemas.py` | `GearChoice`（`item_id` 或 `custom` 二選一）、`GearCustomItem`（詞條只能是白名單 id ＋ 數值）、`GearCatalog`、`GearCheck`… |
| `src/trpg/api/routes/gear.py` | `GET /api/gear/catalog`、`POST /api/gear/check`（合法時回傳開戰時的主角 `UnitView`） |
| `src/trpg/api/schemas.py`、`sessions.py`、`app.py` | `CreateBattleRequest.equipment`（新增欄位）；`SessionStore.base_setup` 拆出、`_setup` 先換裝備（主手武器物品會換主角的武器）再裝自訂技能；`GearRequestError` → 422 |
| `src/trpg/engine/gear_view.py`、`view.py` | 新增 `UnitView.gear_totals`（唯讀）：每個加成的實際值、截斷前的值、是否被截斷、條件、每條詞條的貢獻與遞減權重；只讀 `GearState`，不參與結算 |
| `client/src/gear/gearDraft.ts` | 手動組物品與整組穿戴的本機檢查（與後端同規則、同用語）、請求格式、數值顯示、暫存 |
| `client/src/screens/GearScreen.tsx`、`ui/gear/*` | 裝備分頁：左 3×3 欄位格（64px 圖示）、右測試物品清單（每列 48px 圖示＋名稱＋詞條摘要，不做背包格）、手動組裝表單、英雄面板、進靶場 |
| `client/src/ui/GearTotals.tsx`、`UnitInfo.tsx` | 加成來源列表（完整版給英雄面板、精簡版給單位資訊小卡，來源放滑過提示） |
| `client/src/screens/WorkshopScreen.tsx` | 加「技能｜裝備」分頁（分頁記在瀏覽器，從戰鬥回來停在原處） |
| `client/openapi.json`、`schema.d.ts`、`api/types.ts`、`api/client.ts` | 重產與別名（只新增） |
| `tests/api/test_gear_api.py`（11 個）、`client/src/gear/gearDraft.test.ts`（22 個）、`client/src/gear/fixtures/*.json` | 測試與後端真實回應 fixture |
| `docs/phases/img/3G-4-*.png` | 5 張截圖 |

## 設計重點

- **只能提議、由引擎裁決**：手動組的物品在前端只能從白名單下拉選詞條（不能掛的詞條灰掉並附原因）、數值輸入限制在初值範圍；伺服器再以引擎的同一批驗證函式裁決，前端的本機檢查只是即時提示。LLM 之後走同一條路（`GearCustomItem` ＝ 白名單 id ＋ 數值）。
- **進戰鬥**：`POST /api/battles` 的 `equipment`；快照內嵌在 `BattleSetup`，下載的紀錄可直接 `trpg battle replay`（有測試）。沒選的欄位是空的；主手選了武器物品時主角的武器跟著換（技能與武器不相容時回報原因）。
- **加成來源**：`gear_totals` 由 `GearState.merged／uncapped／bonuses` 組成。傷害加成的上限是「所有行合計」，所以各行維持原值、另有一行「傷害加成合計」標出截斷前後；移動的截斷在移動那一行標示。

## 逐條驗收（規格第 4 節）

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | 「裝備」分頁：左 9 欄位格 3×3、每格 64px；右物品清單每列 48px 圖示＋名稱＋詞條摘要；不做背包格 | 通過。`3G-4-gear-tab.png`；`SlotGrid.tsx`（`GearIcon size=64`）、`ItemList.tsx`（`size=48`） |
| 1 | 為 9 個欄位選測試物品 | 通過。`3G-4-gear-tab.png`；`test_check_test_items_returns_hero_with_bonus_sources` |
| 1 | 手動組物品：選欄位、從白名單掛 1～4 條、數值在初值範圍內 | 通過。`3G-4-custom-item.png`；vitest「選單依物品種類標出不能掛的詞條」「數值限制在初值範圍內」「沒有詞條、超過上限、重複、數值超出範圍」；後端 `test_illegal_custom_items_report_chinese_reasons`（超出範圍、不在白名單、不能掛此欄位、5 條、0 條、傳說） |
| 1 | 不合法時顯示原因（占用、代價型超過 2 條等） | 通過。`3G-4-illegal-reasons.png`：「主手是雙手或成對武器（試煉戰錘），副手被占用，不能放 試煉圓盾」「同一枚戒指不能裝兩次」「代價型詞條全身最多 2 條（目前 4 條）」；後端同樣有中文原因（不含內部 id）；`test_check_*`、`test_battle_creation_rejects_illegal_equipment_with_reasons`（422） |
| 2 | 英雄面板與單位資訊顯示裝備與詞條文字 | 通過。`3G-4-hero-sources.png`（英雄面板：32px 圖示、每項加成）；單位資訊小卡：「裝備：」圖示一排（G5a）＋「裝備加成」（用 DOM 文字驗證：最大 HP +8、火焰抗性 +10%、傷害 +20%、受到的傷害 +10%、防禦 +15%（條件）、命中 +1（條件）） |
| 2 | 數值旁標出「來自裝備」及遞減、截斷後的實際值 | 通過。每行有「來自裝備」標籤；來源行標「遞減：50%／25%／不生效」；`傷害加成合計 +50%（截斷前 +56.2%）已截斷`（`3G-4-hero-sources.png`）；vitest「傷害加成超過上限」「條件數值標出條件；遞減在來源裡標出權重」（用後端真實回應）；後端 `test_diminishing_is_shown_in_sources…`、`test_damage_cap_is_marked_as_truncated` |
| 3 | 預覽浮動卡的數字包含裝備加成 | 通過。`3G-4-preview-with-gear.png`：遠程英雄穿「玻璃項鍊（傷害 +20%）」等，普攻預覽「命中 75%　暴擊 5%　傷害 6–24（期望 8.2）」；同種子無裝備為 5–20（期望 6.6）（`/preview` 實測，兩次 API 回應：最小 5→6、最大 20→24）。引擎面由 G1 的 `test_preview_includes_gear_hit_and_damage` 守住 |
| — | vitest：裝備分頁的合法性、數值顯示 | 通過：`gearDraft.test.ts` 22 個（全部 vitest 615 個通過） |
| — | 含自訂裝備的戰鬥紀錄可重播 | 通過：`test_custom_gear_battle_log_replays`（`--log-json` 同格式，`cmd_replay` 一致） |
| — | 截圖 `docs/phases/img/3G-4-*.png` | 5 張：`gear-tab`（裝備分頁）、`custom-item`（手動組物品）、`illegal-reasons`（不合法原因）、`hero-sources`（英雄面板的加成來源，含截斷）、`preview-with-gear`（預覽數字含裝備） |
| — | `check.py` 全過、`pnpm build` 成功 | 見文末「最終檢查」 |

## 新增的複雜度 noqa

**沒有**。

## 待 PM 決定

1. **分頁位置**：規格寫「靶場或技能工坊加裝備分頁」，採技能工坊內的「技能｜裝備」分頁（首頁入口不變）；裝備測試固定用靶場（`workshop.yaml` 的地圖與對手），沒有開放其他地圖。
2. **「英雄面板」**：目前沒有獨立的英雄面板元件（一輪的 `RunHeroPanel` 屬 3-24b2 的範圍，沒動），所以以「裝備分頁左下的英雄面板」（開戰時的主角）與「單位資訊小卡」兩處顯示加成來源；一輪裡的英雄面板之後要顯示請另排。
3. **主手換武器**：主手選了武器物品時，主角的武器換成那把；若 build 的技能與新武器不相容，整組標為不合法並說明（例如 build_charger 換成弓）。沒選主手時沿用 build 的武器。
4. **沒選的欄位是空的**：build 英雄範本本身若帶裝備會被這組選擇整個取代。
5. **自訂物品**：只能自訂名稱、武器（主手）、成對、盾標籤（副手）、傳說旗標、外觀造型、詞條；外觀材質／染色／稀有度（推導）不開放；每個欄位的自訂草稿只存在這個畫面（暫存的是「已穿上」的選擇，存在 `localStorage` 的 `trpg-gear-test`）。
6. **不可用的詞條在選單裡灰掉**（附原因），所以介面上不能手動選出「不能掛在這個欄位」的詞條；這類原因由後端與本機檢查的單元測試涵蓋，截圖展示的是整組穿戴的問題（占用、戒指、代價型）。
7. **傷害加成合計行**：上限是「所有來源合計」，所以各行維持原值，另加一行「傷害加成合計」（各條件全成立時）標出截斷；移動加成的截斷直接標在移動那一行。單一元素抗性的截斷（取決於單位本身的抗性）沒有標示，只顯示裝備貢獻值。
8. **預覽**：預覽數字本來就含裝備（G1 引擎），G4 沒改引擎；裝備分頁沒有內建「試打預覽」，要看預覽請進靶場。
9. **`gear_totals` 在所有 `UnitView` 都會出現**（含敵人，沒有裝備時為空）；單位資訊小卡的精簡版把說明與來源放在滑過提示。
10. **截圖解析度**：內建瀏覽器面板約 800 px 寬，截圖以 940 px 版面縮放 0.85 拍攝；小卡（單位資訊）在面板高度不足時被裁切，所以單位資訊以 DOM 文字驗證。與 G2／G3 同時修改的檔案：`engine/view.py`（只加一個欄位與一行呼叫）；`gear_view.py` 只讀 `GearState` 的 `items／affixes／bonuses／merged／uncapped`，G2／G3 若改變這些欄位的意義請同步。

## 最終檢查

- ruff check、ruff format --check、mypy（471 個檔案）、lint-imports（6 個契約全 KEPT）：通過。
- pytest 全量 3799 個全部通過。**注意**：`scripts/check.py` 的平行全量 pytest 在三個 agent 同時跑、機器滿載時卡在 98% 之後（最後幾個重型測試遲遲沒有結束，被我中止），所以改為依目錄分開跑（`-n 4`）：api 217、cli 112、content 579、narrative 36、roguelite 65、shared 72、skillgen 563、engine 2058、sim 86、其餘 3 個檔共 11，全部通過、無失敗。`check.py` 其餘步驟（ruff、格式、mypy、import-linter）在中止前都已通過。
- client：`tsc --noEmit` 通過、vitest 56 檔 615 個通過（含新增 22 個）、`corepack pnpm -C client build` 成功（僅有既有的 chunk 大小警告）。
- 開發中另以本機伺服器（8765 埠，沒有碰 8000 埠）實際操作瀏覽器：穿裝備、手動組物品、不合法原因、進靶場、預覽。
