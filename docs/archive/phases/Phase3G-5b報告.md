# Phase 3G-G5b 報告：紙娃娃擴充（換裝時戰場小人跟著變）

> 實作者：implementer（sonnet）。只動前端繪圖與唯讀外觀資料；沒有改引擎、API 型別、`styles.css`。

## 1. 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/dollGear.ts`（新） | 外觀欄位 → 紙娃娃部件：`dollItem()`、`dollGear()`；經 G5a 的 `resolveGear` 驗證與補預設；項鍊、戒指回傳 null；成對武器副手複製主手 |
| `client/src/render/paperdollGear.ts`（新） | 新部件的畫法：寬簷帽、皮帽／毛帽、全罩盔、外套、鱗甲紋、臂環／露指／長手套、鐵靴／布鞋綁帶／護膝、錘（釘頭錘、連枷）、矛（戟、三叉戟）、手槍、霰彈槍、拳套、鐮刀、鞭、法球、塔盾 |
| `client/src/render/paperdoll.ts` | 接上新部件；半身板甲無肩甲、短袍下襬較短；髮頂遮蓋加入全罩盔與皮帽；副手手持物（成對武器、拳套）鏡像 |
| `client/src/render/appearance.ts` | `DollInput.equipment`；`KNOWN_KINDS` 擴充；`MATERIAL` 新增銅、銀、晶石（原 7 種不動）；有穿的欄位覆蓋，沒穿的沿用範本 |
| `client/src/battle/drawModel.ts`、`unitSprite.ts` | `UnitView.equipment` 經 `UnitDraw.equipment`（選填）傳到 `resolveDoll` |
| `client/src/render/dollGear.test.ts`（新） | 16 個測試（含 5,000+ 組全組合 × 4 朝向不丟例外、不用 `Math.random`） |
| `client/doll-gallery.html`、`src/dev/dollGallery.ts`（新） | 開發用紙娃娃一覽，不進正式 build；網址 `#①`～`#⑤` 可只看某段 |

快取鍵沿用 `dollKey`（規格物件排序後序列化），外觀不同則不同。換裝後進靶場是新戰鬥，貼圖依新鍵產生，無需額外失效處理。

## 2. 對照美術 PM 驗收清單

| # | 項目 | 結果 |
|---|---|---|
| 6 | 成對武器：紙娃娃兩手各一把 | 通過。雙匕首、雙手槍主副手各一把，副手鏡像向外張開；測試以 `rotate` 次數驗證（單把 1、成對 2）。圖示與副手格「占用」顯示屬 G5a／G4，本段未動。截圖 `img/3G-5b-paired.png`、`img/3G-5b-arena-paired.png` |
| 7 | 紙娃娃 6 套，四個朝向、頭髮遮蓋 | 通過。6 套（鐵壁騎士、烈焰法師、影刃、鷹眼槍手、撼地者、潮雷念動）× 4 朝向見 `img/3G-5b-sets.png`；髮頂遮蓋以測試驗證（頭盔、全罩盔、皮帽不畫髮頂，寬簷帽照樣品不遮）。**請美術 PM 目視確認細節。** |
| 8 | 退回預設 | 通過。不認得的 kind／form／材質／染色／關鍵字、造型與欄位不符皆不丟例外（`img/3G-5b-fallback.png`） |
| 5.3 | `dollItem()` 對照涵蓋每個 kind；項鍊戒指 null；成對各一把 | 通過（測試逐 kind × form 驗證） |
| 5.1 | 全組合不丟例外 | 通過（紙娃娃部分；圖示部分見 G5a） |
| G5b | G4 換裝後靶場小人跟著變 | 通過。實測：裸裝（`img/3G-5b-arena-bare.png`）→ 穿角盔、鎖甲、圓盾、手套、靴（`img/3G-5b-arena-equipped.png`）→ 雙匕首（`img/3G-5b-arena-paired.png`） |

另有：`img/3G-5b-slots.png` 各欄位換裝對照（正面＋背面）。

## 3. 驗證

- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、client typecheck、client test 通過；其中 pytest 步驟第一次顯示失敗（同時三個 agent 在跑，機器很慢，疑似逾時），單獨重跑 `uv run pytest -n auto -q` 為 **3890 passed**。
- `corepack pnpm -C client build` 成功。
- 沒有新增任何 noqa；本段無 Python 變更。

## 4. 待 PM 決定

1. 稀有度外光：穿了史詩／傳說裝備時，小人加外光（取最高；範本原有的外光保留）。樣張是依單位資料，這是我的推定。
2. 護手（`gauntlets`）的袖口只在裝備指定形制時才畫，舊範本（無形制）維持原畫面，避免舊單位外觀改變。
3. 沒穿的欄位沿用範本（例如範本的披風、盾）；若要「有裝備系統的單位完全不套範本」需另議。
4. 主手裝備沒寫造型（`kind` 為空）時沿用武器 id 的外觀。
5. 是否雙手：優先依武器 id 外觀表；表裡沒有的新武器才依造型判斷（杖除權杖、短杖外為雙手；錘除釘頭錘外為雙手；矛、鐮刀、弩、長槍、霰彈槍、巨劍、弓為雙手）。
6. 火器畫法沿用 3-24a2 已有的長槍風格，手槍與霰彈槍照同風格新畫，與樣張的 `gun` 畫法不同。
7. 短杖（`wand`）、劍與斧的形制（彎刀、闊劍等）、弓與巨劍的形制在紙娃娃上沒有差異（樣張也沒畫）。
8. 副手法球／書／盾以外的手持物才鏡像；拳套兩手都畫，副手無裝備時才畫第二個拳套。
9. 成對武器雙匕首在正面是短小的交叉位置，辨識度偏低，是否放大請美術 PM 看圖。
10. 紙娃娃的材質色票沿用原 7 種，鐵、鋼與裝備圖示的鐵、鋼色略有差異（為了舊單位不變）；是否統一請美術 PM 決定。
