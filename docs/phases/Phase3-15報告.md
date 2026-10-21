# Phase 3-15 報告｜滑過格子顯示地形資訊卡

分支：`worktree-agent-ae2c881e91b64234d`（從 main 的 02d3e3c 開出，未 push）。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `77afaad` | 後端：`trpg/narrative/tile_info.py` 由內容資料產生地形、表面、物件的中文說明；`/api/glossary` 每筆加 `rules_zh`；重產 `openapi.json`、`schema.d.ts` |
| `f30a0b1` | 前端：`battle/tileInfo.ts`（卡片內容組合）、`ui/TileCard.tsx`、`BattleScreen` 的浮動卡改為單位卡＋地形卡；`fixtures/glossary.json` 重存；vitest |
| `a29127a` | `ui/HoverFloat.tsx`（量測卡高、不超出戰場）、字級微調、截圖 |
| （本報告 commit） | `docs/phases/Phase3-15報告.md` |

做法重點：
- 說明全由資料產生（守則 4）：不手寫每種內容的句子，只有「標籤／欄位／互動結果 → 中文短句」對照表放在 `tile_info.py` 一處。
- 靜態說明走既有 `/api/glossary`（`GlossaryEntry.rules_zh`），沒有新增端點；動態部分（剩餘回合、HP、區域、預告、陷阱）由前端從 `BattleView` 組合。
- `BattleScreen.tsx` 的改動：新增兩個 import、一行 `tileSections(...)`、把原本的區域／預告 `<ul>` 換成 `<TileCard>`（區域與預告文字併入卡片的「持續區域與預告」段）、`div.unit-float` 換成 `HoverFloat`。沒有動繪圖與其他滑過處理；沒有動 `battle/glossary.ts`、`render/`。

## 2. 驗收條件逐條

1. **說明產生函式 pytest：通過。** `tests/narrative/test_tile_info.py`
   - `test_every_terrain_surface_object_has_rules`：每種地形、表面、物件都非空。
   - `test_all_object_tags_have_text`、`test_unknown_terms_is_a_warning_not_an_error`（`unknown_terms()` 目前為空；有未知項時 `warnings.warn` 並顯示原名，不出錯）、`test_unknown_tag_shows_its_raw_name`。
   - `test_ice_water_oil_smoke`、`test_crate_pillar_barrel_ice_wall`：冰面（敏捷檢定、滑倒、火焰：變成水、之後變成水）、水（雷電傳導、冰霜結冰）、油（可燃、火焰：變成火焰）、煙霧（擋視線、隱蔽、風：消失）、木箱（可推動、半掩護、可燃、可被穿透、風：被推動）、石柱（可推倒、擋視線、風：被推倒）、油桶（碰火爆炸、3×3、漏出油）、冰牆（遇火融化、火焰：融化消失）。
   - `tests/api/test_views_glossary.py::test_glossary_has_static_rules_for_tiles`：API 回傳每筆都有 `rules_zh`。
2. **圖例與資訊卡用語一致：通過。** `test_legend_uses_the_same_terms`（後端致命地形用語與 `legend.ts` 一致）；vitest `legend uses the same terms`（`致命地形`、`燃燒中`、`陷阱`、`持續區域` 四個詞由 `tileInfo.ts` 匯出並比對 `BASE_LEGEND`）。圖例本身沒有改字。
3. **vitest 資訊卡內容組合：通過。** `client/src/battle/tileInfo.test.ts`（9 項）：普通地面一行、高度、深淵多行規則、冰面剩餘回合、物件 HP／燃燒、冰牆剩餘回合、可見陷阱、持續區域與預告文字併入、無此格回傳空。與單位卡合併：`BattleScreen` 在單位卡下方接地形卡（同一個浮動容器），截圖 `3-15-unit-on-ice` 為證；合併本身是版面組合，沒有獨立的單元測試。
4. **瀏覽器截圖：完成。** 見第 6 節；存成 `.jpg`（工具輸出格式，非 `.png`）。
5. **`check.py` 全過、`pnpm build` 成功：通過。** `check.py` 八項全部通過（含 pytest 全量、vitest 392 項）；`corepack pnpm -C client build` 成功。

## 3. 複雜度 noqa

新增 0 個；noqa 總數前後都是 55（`src` 下 grep 計數）。

## 4. 修改既有測試期望值

無。`client/src/battle/fixtures/glossary.json` 以真實 API 重存（每筆多 `rules_zh`），既有 vitest 全數仍通過。

## 5. 待 PM 決定

1. **移動成本**：`terrain.yaml` 沒有移動成本欄位（引擎也沒有），資訊卡只顯示高度、可否通行、致命、擋視線。若要顯示需先有規則。
2. **卡片高度**：單位卡（既有，偏高）＋地形卡合併後，在小視窗或小地圖上可能超過戰場高度，目前以 `HoverFloat` 量測並上移貼齊戰場邊界，仍超過時尾端會被裁切。若試玩覺得擠，可改為並排（左右兩張）或單位在格時地形卡只留標題。
3. **文字量**：油桶、木箱的卡片約 10 行。可考慮把「標籤」濃縮成一行（例如「不可通行・半掩護・可推動」），之後看試玩回饋。
4. **持久表面**：地圖上原有的冰、水、油是永久的，卡片沒有「剩 N 回合」；規則行仍寫「由技能產生時持續 3 回合」（描述技能產生版本）。這句在永久表面上可能讓人誤會，是否改成只在表面有剩餘回合時才顯示？
5. **互動只列第一條**：同一次觸及每類對象只套用第一條符合的規則（例如油桶的火焰只顯示「爆炸」，不顯示「點燃」），與引擎一致；否則會誤導。
6. **單位互動不列入**：`target: unit` 的互動只有在帶 `unit_surface`（站在水上被冰霜凍住）時才列入表面說明；風推單位等通則沒有放進格子卡。
7. **陷阱**：只顯示視圖中可見的（我方）陷阱，標題為「陷阱：技能名・剩 N 回合」；技能效果說明沒有帶出。
8. **截圖格式與取樣**：截圖為 `.jpg`；瀏覽器視窗在內建面板縮放後字小，截圖是用腳本觸發 `pointermove` 再擷取。實際滑鼠滑過的行為依賴同一個 `onPointerMove`，未另做真滑鼠錄影。
9. **埠號衝突**：規定的 8772 在我開始時已被別的程序佔用（未動它），我改用 8773 測試並已關閉自己的伺服器。
10. **圖例新增**：本段沒有替圖例新增地形、表面條目（圖例仍只講顏色與標記）；若要「地形圖例」，可直接用 `rules_zh` 產生。

## 6. 代表性輸出節錄

截圖（`docs/phases/img/`）：`3-15-ice.jpg`（冰面）、`3-15-water.jpg`（水，沼澤）、`3-15-crate.jpg`（木箱）、`3-15-stone-pillar.jpg`（石柱）、`3-15-oil-barrel.jpg`（油桶）、`3-15-unit-on-ice.jpg`（有單位的格子：單位卡＋地形卡）、`3-15-ice-hole.jpg`（冰窟，致命地形）。

### 標籤／欄位／互動 → 中文短句對照表（`tile_info.py`）

物件標籤（顯示順序同下）：

| 標籤 | 短句 |
|---|---|
| `blocks_move` | 不可通行 |
| `blocks_sight` | 擋視線（全掩護） |
| `half_cover` | 半掩護（遠程攻擊其後的目標，命中 −N；N 取自 `core.yaml`） |
| `conceal` | 站在同一格的單位隱蔽 |
| `over_chasm` | 架在致命地形上，可以走；被打破後格上的單位會落下 |
| `pushable` | 可推動 |
| `topplable` | 可推倒（往推的方向倒下，壓住後面 N 格；N 取自 `topple_length`） |
| `breakable` | 可被破壞 |
| `penetrable` | 可被穿透 |
| `flammable` | 可燃 |
| `explosive` | 碰火爆炸 |
| `conductive` | 導電 |
| `freezable` | 可結冰 |
| `meltable` | 遇火融化 |
| `extinguish` | 可熄滅火焰 |

物件其他欄位：`explosion` → 「爆炸範圍 3×3，2d6 火焰傷害」；`spill` → 「被傷害打破或摔破時（非被火引爆）漏出油」；`max_hp`／目前 HP 由前端以「HP 目前/最大」顯示。

地形：可走 → 「可通行」；不可走 → 「不可通行」；`deadly` → 「致命地形：被推進去的單位死亡（精英與 Boss 改受 30% 最大 HP 傷害）」（30% 取自 `deadly_terrain_elite_permille`）；`blocks_sight` → 「擋視線（全掩護）；一般攻擊無法破壞」。高度由前端顯示「高度 N」。

表面欄位：`duration`／`expires_to` → 「由技能產生時持續 N 回合，之後變成X」；`element` → 「帶有X元素（產生時會觸及格上的物件）」；`flammable` → 「可燃：火勢會蔓延過來」；`blocks_sight` → 「擋視線」；`conceal` → 「站在上面的單位隱蔽」；`beneficial` → 「對站在上面的友方有益」；`on_enter.check` → 「進入時 敏捷檢定 DC 12，失敗會倒地（滑倒判定）」；`on_enter.apply_status`／`on_turn_start.apply_status` → 「進入時／回合開始時獲得X」；`on_turn_start.damage` → 「回合開始時站在上面的單位受 1d4 毒素傷害」；`on_turn_start.heal` → 「回合開始時治療站在上面的友方 1d4」。

互動格式為「觸發：結果」；觸發是元素名（火焰、冰霜、雷電、風、神聖、大地……）或「在上面產生X」。結果對照：

| op | 短句 |
|---|---|
| `set_surface` | 變成X／消失 |
| `ignite_object` | 被點燃（燃燒後摧毀，並產生火焰） |
| `explode` | 爆炸 |
| `conduct` | 沿相連的水與導電物傳導，波及其上的其他單位 |
| `push` | 被推動（對 `topplable` 規則顯示「被推倒」） |
| `spread_surface` | 沿方向蔓延到下一格（X） |
| `fill_chasm` | 被填平，格子變成X |
| `destroy_object` | 被摧毀（對 `meltable` 規則顯示「融化消失」） |
| `apply_status` | 獲得X N 回合（對單位規則加前綴「站在上面的單位」） |
| `keep` | 維持原狀 |

前端動態段：地形標題「石地・高度 0」、表面「冰・剩 N 回合」、物件「木箱・HP 5/15・燃燒中・剩 N 回合消失」、陷阱「陷阱：技能名・剩 N 回合」、持續區域與預告（沿用 3D-5／3-3 既有文字）。規則只有一句時併在標題後（例：「石地・高度 0・可通行」，普通地面只佔一行）。
