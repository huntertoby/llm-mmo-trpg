# Phase 6D-5 報告：大世界圖（M）＋主城規則＋荒原首次走過渡口才亮起

**依據**：
- `docs/phases/Phase6計畫.md` 第 1 節 6D-4、6D-5 列
- `docs/design/21-探索地圖與城鎮.md` 21.1、21.9 第 4、5 條、21.10；09 9.6.5、9.6.9；19.9
- 玩法 PM 主城草稿（2026-11-04，未寫入設計文件）第 3、4 節
- `Phase6D-4報告.md` 待決與第 7 節、`Phase6C-5報告.md`、`Phase6C-6報告.md`

開工時 `git merge main`：沒有衝突，含 6C-5、6C-6、6D-4。沒有改引擎（`trpg.engine`）。

## 1. 主城的表示法與抵達

**表示法**：角色在主城（含室內）時 `region = location = "capital"`。這和 6D-4 的實地地圖（`region: capital`、`location: capital`）一致，也是原本 `use_teleport_stone` 傳到 `stone_capital` 時自然會寫進去的值。

- 主城不在 `content/world/maps/`。`world/common.py` 的 `world_map_of("capital")` 回傳臨時組的一張地點圖（`capital_map`），只有一個城鎮地點 `capital`、沒有連線。
- 這張圖不放進 `library.world_maps`，所以內容檢查、區域清單、季末重置等列舉都看不到它。
- 好處：「所在地點是城鎮」的既有規則直接套用，不用逐一加例外（休息、換技能、雇用、酒館、不能紮營、不能潛行、沒有遇敵與事件、賽季 Boss 從城鎮挑戰）。
- 傳送到主城不把 `capital` 記進 `visited_towns`（它不是區域）。`visited_locations` 會記一筆 `capital/capital`，沒有影響。

**抵達**：
- `stone_capital` 一開始就解鎖（`atlas.unlocked_stones`）。規則上算解鎖，但**不寫進** `teleport_stones`，所以存檔格式不變。
- 從任何城鎮或站在任何傳送石上都能去主城：
  - 用傳送石選單：`use_teleport_stone(stone_capital)`；
  - 用城鎮傳送：`teleport(region=capital)`。
- `teleport` 動作加一種出發點：站在傳送石上（`on_stone`），由 `step._teleport` 用 `teleport_origin` 判斷。這對應 21.1「站在傳送石上打開大世界圖，可以點已開放區的城鎮」。
- 離開主城：`teleport(region=X)` 回到 X 的城鎮，或 `use_teleport_stone` 傳到已解鎖的傳送石。

**安全區**（主城算城鎮，照現行城鎮的規則）：
- 沒有敵人：6D-4 沒有 spawns，`field_enemies` 對城鎮不開趟。
- 只有非戰鬥事件：只有酒館的傳聞。傳送、在城裡走、進出室內都不擲事件。
- 不算一步：不推進事件步數、不抽亂數、不花補給（有測試）。
- 不能紮營（「城鎮裡直接休息，不用紮營」），也不能潛行。
- 可以換技能、配點、換裝：`at_service` 認城鎮。
- 休息：照現行城鎮規則，在主城任何地方都能休息。畫面上的入口是整備亭面板與酒館。
- 全滅照 9.6.9 回本區小鎮：`battle._lost` 用戰鬥所在區的城鎮，主城不會出現在野外戰鬥裡。

## 2. 主城的功能物件接上面板

沒有新增設施種類，用的是「把情境物件接到既有面板」。主城的情境物件補上 `name_zh`、`note_zh`。前端在 `field.region == "capital"` 時，照 `atlasModel.capitalPanel` 對應：

| 物件 | 開的面板 |
|---|---|
| 封印台、守印人、裂界投影、擊殺石碑 | 公告板（`board`）：有賽季 Boss 區的封印鑰匙進度、挑戰鈕、通關評分榜 |
| 循環賽報名台 | 循環賽（`league`） |
| 整備亭 | 新的小面板 `pavilion`：休息、換技能、配點、換裝四個鈕，各自開既有面板 |
| 書記、魔導書書架 | 技能（`skills`） |
| 許願池、守池人、靶場、工坊師傅 | 說明卡，寫「還沒開放」。大世界沒有許願與工坊的功能可以接 |
| 浮橋 | 說明卡（「看橋頭的石碑」） |
| 五座橋頭石碑（`stele_<區域>`） | 新面板 `stele`：該區的傳送選單（見下） |

- 殿主、酒館、鐵匠、附魔、傭兵管事本來就是設施，照舊。
- 主城的鐵匠鋪原本沒有 `crafting.yaml` 的設施，打開會是空的。所以加了 `smithy_capital`、`enchanter_capital`（`region: capital`），並讓 `library.py` 的設施驗證認得主城這一個城鎮地點。

**石碑選單的三種狀態**（`SteleMenu`，資料來自 `WorldView.atlas`）：
- 已開放：有「傳送到〇〇」鈕，送 `teleport`；
- 未解鎖：寫條件；
- 之後的賽季：灰色，只寫「之後的賽季」。

## 3. 荒原：第一次要親自走過渡口

- **跨區出口**：原本 `field._take_exit` 遇到跨區出口會拒絕。現在改成 `_cross_region`：
  - 兩端地點的 `unlock_flag` 都要已開放，也就是雲嶺渡口要 `ashen_waste_open`；
  - 換到對面那一區的地點，站在對面 `arrive` 出口往內一格；
  - 抵達後 `world_step` 把灰渡口記進 `visited_locations`。
- **亮起**：`atlas.region_lit`。到過那一區的小鎮，或 `visited_locations` 裡有那一區的任何地點，就算亮起。荒原只能經由渡口進入，所以等於「親自抵達灰渡口」。亮起後就能從城鎮或傳送石傳到餘燼集，不用先到過餘燼集。
- **渡口不能直接傳送**：畫了跨區出口的渡口（雲嶺的渡口、荒原的灰渡口），`teleport` 會拒絕（「要走到盡頭的出口過去」）。「這裡」的傳送選項也不列，以免繞過走路。
- `teleport` 與跨區的 `use_teleport_stone`，條件從「`visited_towns` 有這一區」改成 `region_lit`，錯誤訊息不變。

## 4. 大世界圖（M）

- **後端**：`WorldView.atlas`（`AtlasView`，在 `api/world_atlas_view.py`）包含：
  - `regions`：照 `regions.yaml` 的順序；
  - `capital`；
  - `can_teleport`、`teleport_problem_zh`；
  - `art_url`：現在一律 `None`；
  - `maps`：已開放、但不是所在區的區域圖，給「點已開放區進該區的區域圖」用。`_map_view` 加上 `region` 參數，別區的圖沒有目前位置與相鄰。
- **三種狀態**（`atlas.region_state`）：
  - `open`：已亮起，或主城；
  - `locked`：有地點圖、還沒亮起。條件由內容推出：世界旗標還沒設時，寫「世界事件：霧潮入侵」（從 `season.yaml` 找設這個旗標的事件）；已開放時，寫「先走過雲嶺的「往灰燼荒原的渡口」」；
  - `later`：`regions.yaml` 有、但這一季沒有地點圖，寫「之後的賽季」。
- **前端**：`AtlasMap.tsx`、`atlasModel.ts`、`styles/atlas.css`。
  - 浮島是程式畫的：橢圓地面、倒三角岩塊、雲。主城在中央，有浮橋連線。
  - 方位照 6D-4 的浮橋：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮。
  - 已開放彩色，點了進區域圖；未解鎖和之後的賽季是灰色剪影並寫條件；自己所在的島有脈動圈。
  - 在城鎮或傳送石上打開時，已開放區的城鎮有「傳送到〇〇」鈕。
- **切換**：M 依序是區域圖 → 大世界圖 → 關閉；在主城直接開大世界圖。區域圖標題列另有「大世界圖（M）」鈕，Esc 關閉。HUD 的 M 鈕說明改成「地圖（M）」。
- 區域圖的傳送石：主城石算已解鎖；從大世界圖點進別區看時，也能點那一區已解鎖的傳送石（出發點照 `teleport_origin`）。

## 5. 存檔、測試、檢查

- **存檔格式不變**：`trpg-char/5`、`trpg-world/2`。主城石只是規則上解鎖、亮起由既有欄位推出，所以不遞增。
- **新增 `tests/world/test_capital.py`**（28 項）：
  - 主城石預設解鎖；
  - 4 種傳送進主城的方式（城鎮、野外傳送石 × 兩種動作）；
  - 不在城鎮或傳送石上不能去主城；
  - 離開主城；
  - 安全區表格：休息、酒館可以；紮營、潛行、travel、再傳主城不行；換技能可以；
  - 城裡走路與進室內不花東西、沒有遭遇；
  - 全滅不回主城；
  - 走過渡口亮起荒原，之後從城鎮傳到餘燼集；
  - 渡口兩端不能直接傳送；
  - 城鎮傳荒原要先走過；
  - 世界事件還沒結束時不能過渡口；
  - 大世界圖三種狀態表格（3 種情境 × 五區）；
  - 畫面：主城裡的 atlas、野外只能看、「這裡」的傳送選項；
  - **重播**：主城來回 6 個動作、走過渡口 → 回霧渡鎮 → 主城 → 傳到餘燼集，各重播兩次逐字一致，存檔讀寫一致。
- **新增前端 `client/src/world/atlas.test.ts`**（9 項）：
  - 浮島狀態與字；
  - 區域圖資料的取法；
  - 說明列；
  - 元件畫面（傳送鈕、條件、灰色、自己的圈；只能看的時候沒有鈕）；
  - M 的切換順序；
  - 情境物件對面板；
  - 石碑三種狀態；
  - 整備亭四個鈕。
- **檢查結果**：
  - `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8 -x`：4169 passed、1 skipped
  - `ruff check .`、`ruff format --check .`、`mypy src`（511 檔）、`lint-imports`（13 kept）：通過
  - `trpg content check`：通過
  - swamp 種子 7 重播：通過（88 個動作、313 個事件）
  - 前端：`tsc --noEmit` 通過；vitest（atlas、regionModel、hud、fieldThings、mapView）104 passed；`pnpm build` 通過
  - OpenAPI 與 `schema.d.ts` 已重產
- **實測**：
  - 自己開的伺服器：埠 8309、暫存存檔、開發模式，直接掛 `client/dist`；1040×720。
  - 建角後傳主城：主城畫面正常。
  - M 開大世界圖；點雲嶺進區域圖。
  - 走到荒原石碑按 E：顯示「未解鎖：世界事件：霧潮入侵」。
  - 大世界圖點「傳送到霧渡鎮」：成功傳回。
  - 伺服器用完已關（只關自己開的那一個）。
- **截圖**：`docs/art/6d5_atlas.jpg`（大世界圖）、`docs/art/6d5_capital.jpg`（主城）、`docs/art/6d5_stele.jpg`（荒原的橋頭石碑選單）

## 6. 動到的檔案

- **後端**：
  - 新增 `src/trpg/world/atlas.py`、`src/trpg/api/world_atlas_view.py`
  - 修改 `world/common.py`（`capital_map`、`in_capital`）、`world/town.py`、`world/field.py`、`world/step.py`
  - 修改 `api/world_presenter.py`、`api/world_schemas.py`、`api/world_region_view.py`、`content/library.py`
- **內容**：`content/world/crafting.yaml`（主城鐵匠、附魔台）；`fields/capital/capital.yaml`、`interiors/capital_mentor_hall.yaml`（情境物件名稱與說明）
- **前端**：
  - 新增 `world/AtlasMap.tsx`、`world/atlasModel.ts`、`world/CapitalPanels.tsx`、`styles/atlas.css`、`world/atlas.test.ts`
  - 修改 `screens/WorldScreen.tsx`、`world/RegionMap.tsx`、`world/WorldHud.tsx`、`world/hud.ts`、`api/types.ts`、`styles/index.css`、`openapi.json`、`schema.d.ts`
- **測試**：新增 `tests/world/test_capital.py`
- 沒有新增 `# noqa`

## 7. 待 PM 決定

**規則類**（照最保守做法先做，需要確認）：
1. **走過渡口算不算「進入一張地圖」**：現在照原本渡口的傳送，不擲遇敵與事件、不花時間與補給。21.10 第 2 條說「進入一張地圖＝一步」，要不要改成擲骰？
2. **渡口兩端都禁止直接傳送**：包含荒原的灰渡口回雲嶺。原本的渡口傳送（舊的地點圖做法）在有實地地圖時就不能用了。
3. **在主城休息**：照現行城鎮規則，在城裡任何地方都能休息。草稿寫「在整備亭或酒館直接休息」，要不要限定站在旁邊？
4. **賽季 Boss 從主城挑戰時輸掉**：照現行做法回到出發的城鎮，也就是留在主城。這不是野外全滅，所以沒有套 9.6.9。

**原型與解讀類**（照預設做了）：
5. 浮島方位照 6D-4 的浮橋。等美術畫大世界圖時再一起定（6D-4 待決 4）。
6. 許願池、工坊靶場在大世界沒有現成功能，只開說明卡「還沒開放」。
7. 書記與魔導書書架開「技能」面板。目前只是自己的技能，不是全技能圖鑑。
8. 主城鐵匠鋪、附魔台的店名「樞島鐵匠鋪」「樞島附魔台」是我暫定的，沒有 `npc`。
9. 主城在大世界圖上的城鎮名用實地地圖的名字「樞島」，島名是「主城」。
10. 舊存檔如果已經到過餘燼集（`visited_towns` 有荒原），照樣算亮起，不要求重走渡口。
