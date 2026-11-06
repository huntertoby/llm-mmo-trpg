# Phase 3G-5a 報告：裝備圖示產生器（G5a）

規格：`docs/phases/Phase3G計畫.md` 第 0 節 G5a；`docs/art/裝備外觀移植需求.md` 圖示部分（第 0～3、5、6 節）。紙娃娃（第 4 節）是 G5b，未做。
分支 `worktree-agent-a041c8bacd2127e86`（從 main 5fa60fc 分出），未 push、未合併。

## 新增與修改

| 檔案 | 內容 |
|---|---|
| `content/equipment/appearance.yaml` | 外觀清單：42 個造型（主手 17、副手 4、身體 5、頭 5、手 4、腳 4、項鍊 2、戒指 1）、各形制、可用／預設材質、10 材質、8 染色、5 稀有度、10 關鍵字（id 同 3-24b1）；legacy 的 `gun`／`gloves`／`bracelet` 不收 |
| `src/trpg/content/appearance.py` | pydantic schema `AppearanceTable`、`derive_keywords`（由詞條推導）、`item_appearance_problems`、匯出前端 JSON |
| `src/trpg/content/equipment.py` | `ItemDef` 新增選填 `kind／form／material／dye／style／rarity` |
| `src/trpg/content/library.py` | 載入清單；關鍵字須是 `skill_keywords.yaml` 的 id；items.yaml 寫了的外觀欄位須認得且相容 |
| `content/items.yaml` | 13 件測試物品補上外觀 |
| `src/trpg/engine/gear_state.py`、`gear.py` | `GearItem` 帶外觀欄位（預設空字串）與推導出的 `keywords`；不動結算 |
| `src/trpg/engine/view.py` | 新增 `AppearanceView`，`EquipmentSlotView.appearance`（只新增欄位）；`openapi.json`、`schema.d.ts` 重產 |
| `scripts/export_appearance.py`、`client/src/render/gearAppearance.json` | 前端用的清單（真相來源是 yaml；`tests/content/test_appearance.py` 檢查沒有過期） |
| `client/src/render/artPalette.ts` | 檔尾新增裝備色票（材質、染色、關鍵字、稀有度、描邊） |
| `client/src/render/gearIcon.ts` | 圖示產生器：`resolveGear`、`drawGear`、`gearIconKey`、`gearIconCanvas`（快取）；畫法由 `gearArt.js` 移植成 TypeScript |
| `client/src/ui/GearIcon.tsx`、`UnitInfo.tsx`、`styles.css`（檔尾） | 單位資訊顯示「裝備：」一排 32px 圖示（滑過看名稱與詞條） |
| `client/gear-gallery.html`、`client/src/dev/gearGallery.ts` | 開發用一覽頁（不進正式 build）；`pnpm dev` 後開 `/gear-gallery.html` |
| `docs/phases/img/3G-5a-overview.png`、`-variants.png`、`-sizes.png` | 全部造型總覽、材質／染色／關鍵字／稀有度／特殊、64／48／32px 對照 |

## 設計重點

- **外觀只由資料決定**：後端只傳原始欄位（沒寫＝`null`）與推導的 `keywords`；驗證與預設只在前端 `resolveGear`（單一處），不認得一律退回預設不丟例外。沒有 `kind` 時依欄位退回預設造型（頭→頭盔…），`kind` 寫了但不認得才退回劍。
- **關鍵字推導**：第 3 類詞條取其 `keyword`（暫定寫法 `shock` 對照成 `charged`）；第 4 類 `add_element`（火／水／雷／冰→點燃／潮濕／帶電／冰凍）與 `on_hit_status: marked`→標記；依詞條順序去重取前 2 個。
- **尺寸**：≤ 36px 不畫關鍵字小圖樣，元素混色與稀有度外框照留；快取鍵含「是否小圖」與像素大小，由解析後欄位組成（與屬性順序無關，不認得的值與預設值同鍵）。
- 不改引擎結算、不改 `LOG_FORMAT`（`GearItem` 只新增有預設值的欄位；`ItemDef` 只新增選填欄位）。

## 驗收清單對照（美術 PM 第 6 節）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 9 格全部造型與形制 | 一覽頁 ①（`3G-5a-overview.png`）：42 造型全形制；供美術 PM 與 `gear-all.png` ① 逐格比對（待美術 PM 目視） |
| 2 | 材質 10 種 | ②：鐵鋼銀分得出來、銀有亮線、晶石遇元素整塊換色（④ 的晶石匕首列） |
| 3 | 染色 8 種 | ③：皮、布變色，鐵劍不變 |
| 4 | 關鍵字 10 種 | ④、④b：4 種元素混色、全部有小圖樣；2 個關鍵字各畫一處 |
| 5 | 稀有度 4 種（含傳說共 5） | ⑤：外框色、右上角標、史詩光暈；32px 小圖也看得出差別 |
| 6 | 成對武器 | 圖示畫兩把（⑥）；紙娃娃與副手格占用顯示屬 G5b，未做 |
| 7 | 紙娃娃 6 套 | G5b，未做 |
| 8 | 退回預設 | vitest：不認得的 kind／form／material／dye／keyword／rarity／style 都不壞；一覽頁 ⑥ 有「不認得→劍」 |
| 9 | 效能 | 圖示依解析後欄位快取成離屏貼圖（`gearIconCanvas`），同外觀共用；未做 50 件的實測計時（見待決定） |

移植需求第 5 節測試：全組合不丟例外（vitest：造型×形制（含不認得）×材質（含不認得）×13 組關鍵字，共 2 萬多種，另造型×形制×稀有度×大小圖×染色）；`resolve` 預設（不認得→劍、布頭盔→鐵、金屬染色無效、頭冠金／頭巾布、臂環銅）；快取鍵穩定。「`dollItem` 對照」屬紙娃娃，未做。

自動化結果：`uv run python scripts/check.py` 全過（ruff、format、mypy、lint-imports、pytest、client typecheck、vitest 593）；`corepack pnpm -C client build` 成功（僅有既有的 chunk 大小警告）。新增 pytest：`tests/content/test_appearance.py`（20 個）；vitest：`gearIcon.test.ts`（19 個）。

## 新增的複雜度 noqa

無。

## 待 PM 決定

1. **樣張的主手數量**：移植需求寫「主手 19 種造型」，`gearArt.js` 非 legacy 的主手造型實際是 17 個（總計 42）；以樣張為準，若漏了請告知。
2. **關鍵字 id**：圖示用 3-24b1 的 id（`charged`、`frozen`、`collision`、`marked`、`high_ground`、`concealed`）。`affixes.yaml` 現有 `keyword: shock` 以別名對照為 `charged`；G2 若把詞條改成 `charged`，別名可刪。
3. **關鍵字推導範圍**：目前只由第 3、4 類詞條推導；`high_ground`、`concealed`、`summon`、`collision` 沒有詞條會推導出來（第 6、7 類觸發／充能之後可擴充）。
4. **稀有度**：`ItemDef.rarity` 選填，沒寫時傳說物品＝`legendary`、其餘 `common`；稀有度由誰決定（引擎掉落時）留待大世界。
5. **`kind` 缺漏的預設**：沒有 `kind` 時依欄位退回預設造型（頭盔、鎖甲、皮手套、皮靴、墜飾、戒指、圓盾、劍），是本段自行加的保守規則。
6. **items.yaml 驗證較嚴**：本專案寫在 `items.yaml` 的外觀欄位載入時嚴格檢查（造型須符合物品種類與 `paired`、材質與染色須相容）；LLM 產生的物品仍走「退回預設」。
7. **風格**：`style` 欄位已驗證但前端一律畫 `common`（風格包未做）。
8. **效能**：沒有量測 50 件以上的繪製時間，只確認有快取；美術 PM 驗收時請在實際背包介面看（G4）。
9. **圖示位置**：目前只放在單位資訊的「裝備：」一排（32px）；英雄面板與 G4 測試介面（64／48px）之後用 `GearIcon` 元件即可。
10. **一覽頁**：`client/gear-gallery.html` 為開發用，不進正式 build；若不想留在倉庫可刪。
