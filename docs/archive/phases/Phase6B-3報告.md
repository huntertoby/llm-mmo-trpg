# Phase 6B-3 完成報告：可走動畫面

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 0、3、5 節；`Phase6B-2報告.md`；21.1、21.2、21.7。
> 疊在 6B-2 分支（`worktree-agent-acb2e67f0017e9106`）上，合併時沒有衝突。沒有改引擎，也沒有動 `inkDoll.ts`、`inkWeapons.ts`、`inkPose.ts`、`inkCreature.ts` 和戰鬥狀態卡元件。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| 組圖、路徑、方向鍵、互動的純函式 | 新檔 `client/src/world/fieldModel.ts` |
| 可走動畫面元件 | 新檔 `client/src/world/WorldField.tsx`（沿用 `ui/BattleCanvas` 和 `BattleRenderer`） |
| 接到世界畫面 | `client/src/screens/WorldScreen.tsx`：有 `field` 時畫可走動畫面，沒有時畫節點圖；換地圖跳地名；互動時開對應面板 |
| 型別 | `client/src/api/types.ts`：`FieldView`；`WorldAction` 加上 `walk`、`use_teleport_stone` |
| 樣式 | `client/src/styles/world.css`：淡出淡入、地名條、面板閃一下 |
| NPC 卡定位 | `client/src/world/NpcPanel.tsx`：每張卡加 `data-npc`、`tabIndex=-1`（只加屬性） |
| 伺服器補的欄位（只加不改） | `api/world_field_schemas.py`、`api/world_field_view.py`，見第 3 節；OpenAPI 已重產 |
| 測試 | `client/src/world/fieldModel.test.ts`（19 項）；`tests/api/test_world_field_api.py` 加欄位斷言，另加一項 `test_field_view_stone_targets` |
| 截圖（寬 800） | `docs/art/6b3_mist_ferry.jpg`、`docs/art/6b3_ferry_steps.jpg`、`docs/art/6b3_place_name.jpg` |

## 2. 對照規格

**5.1 畫面**
- `field` 組成假的 `BattleView`，交給 `buildDrawModel`。地形、高低差、表面、物件都照戰鬥的畫法；`region` 跟著所在區，所以換皮自動生效。
- 主角是單位 `field_hero`，站在 `field.me` 的位置與朝向。紙娃娃需要的外觀（範本、`doll_look`、武器、種族外觀、裝備外觀）由新欄位 `field.hero` 提供。
- NPC 是我方的紙娃娃單位，範本 ID 是 `npc_<id>`，對照不到外觀時照陣營用預設外觀。
- 標示：
  - 出口用戰鬥的出口格標記（淡綠框加「出」）。
  - 門與傳送石借用環境預告的半透明框加小圖示：門是「門」；傳送石是「◆」，已解鎖藍色、未解鎖紫色。
- 滑鼠滑過時，地圖下方顯示一行說明：出口往哪裡、門通到哪裡、NPC 名字、設施名稱。
- 沒有 `field` 時照舊畫節點圖（`mapPaneKind`）。戰鬥畫面沒有改。

**5.2 走路**
- 點格子：前端用 BFS 算四方向路徑。
  - 鄰格順序固定為北、東、南、西。
  - 路上避開出口、門、傳送石，因為伺服器踩到就會停下；只有終點可以是它們，真的避不開才穿過去。
  - 超過 30 格時切成好幾次 `walk`。
- 方向鍵／WASD：一次走一格，排進佇列，同時只有一個請求在路上。佇列最多排 3 步。走不過去的方向不送請求。
- 以伺服器結果為準：
  - 先送出，成功後才逐格平移（每格 120 ms），再套用新畫面。
  - 伺服器提早停下時（踩到傳送石、出口），動畫走到它回報的格子為止，剩下的佇列清掉。
  - 失敗時顯示錯誤，畫面用原位置重畫。
- 換地圖：先淡出 0.22 秒，再套用新畫面淡入。畫面上方只跳一行地名，約 2 秒後淡出，不寫旁白。
- 遇敵：伺服器回來帶 `encounter` 時停止走路，照現行流程由右欄開戰或撤退。有遭遇時不收走路輸入。

**5.3 互動**
- 點設施或 NPC：不在旁邊就先走到最近的相鄰可站格，走到之後才互動。
- 按 E：先看面向的那一格，再依北、東、南、西找相鄰格，最後是腳下。
- 各種目標開什麼：

| 目標 | 開啟 |
|---|---|
| `shop` | 商店 |
| `smithy`、`enchanter` | 鐵匠 |
| `notice_board` | 公告板 |
| `mentor` | 成長與技能 |
| `tavern` | 送 `tavern`（同右欄的「酒館」按鈕） |
| `hire` | 把右欄的「雇用隊友」按鈕捲進畫面並給焦點 |
| NPC | 把右欄那位 NPC 的卡片捲進畫面、給焦點並閃一下 |

- 傳送石：站在石上時，每一顆可去的傳送石各有一個「傳送：<地名>」按鈕，送 `use_teleport_stone`。沒有別的傳送石可去時，顯示「傳送石已點亮（還沒有別的傳送石可以去）」。

## 3. 伺服器補的欄位（只加不改）

| 欄位 | 用途 |
|---|---|
| `FieldTileView.walkable` | 和伺服器 `field_grid` 同一套可站判定：地形、物件、NPC 格、未發現的隱藏門。前端 BFS 不自己重算 `over_chasm`、`blocks_move` |
| `FieldView.max_climb` | `core.max_climb_height` |
| `FieldView.hero` | 主角外觀（`FieldHeroView`、`FieldGearLookView`），欄位同戰鬥的 `UnitView` |
| `FieldView.stone_targets` | 站在傳送石上時列出其他已解鎖的傳送石，依 ID 排序。原本畫面沒有這份清單，做不出「傳送」按鈕 |

- 都有預設值，不影響舊用戶端。`client/openapi.json`、`schema.d.ts` 已重產。

## 4. 測試與實測

**前端**
- `vitest run src/world src/battle/drawModel.test.ts src/dev`：18 個檔、134 項全部通過。
- `tsc --noEmit` 通過；`pnpm build` 通過，只有原本就有的 chunk 大小警告。

**後端**
- `tests/api/test_world_field_api.py`、`test_openapi_snapshot.py`、`tests/api/test_world*.py`、`tests/world/test_field.py` 通過。
- `ruff check`、`ruff format --check`、`mypy src`（500 檔）、`lint-imports`（13 kept）都通過。

**自己開伺服器實測**
- 環境：API 8295、vite 5296，存檔放 scratchpad 的暫存資料夾。用完已停掉兩個程序，暫存的 vite 設定也刪了。
- 開發模式建角，走了這些：
  1. 在霧渡鎮點東邊出口，小人逐格走過去，換到渡口石階，觸發了地點事件卡。
  2. 在渡口石階點西邊出口回霧渡鎮，上方跳出「霧渡鎮」。
  3. 方向鍵加 A 連按 4 次，從 x=22 走到 x=18，朝向 w。
  4. 點渡婆婆：走到她旁邊，右欄她的卡片拿到焦點並閃一下。
  5. 點傳送石：踩上去解鎖，顯示已點亮的提示。
  6. 點商店：左欄換成商店畫面。

## 5. 待 PM 決定（都已照最保守的做法做完）

1. **6B-2 的測試偶發失敗**：`tests/api/test_world_field_api.py::test_walk_and_stone_actions`，大約一半的次數日誌會多一筆 `narrate`，斷言 `["walk", "walk"]` 就失敗。
   - 推測是走進渡口石階時，有時會擲出地點事件並寫進說書紀錄（每次執行的角色 ID 和亂數不同）。
   - 和本段的改動無關，只動 6B-2 的部分時也一樣。我沒有改這個斷言，請開發 PM 決定修法，例如固定種子，或只比對 `walk` 這幾筆。
2. **「互動＝開現有面板」的對應**：見第 2 節的表。`hire` 和 NPC 沒有獨立面板，所以改成把右欄的按鈕或卡片捲進畫面並給焦點；捲動會帶動整頁，地圖可能跟著捲走。`tavern` 直接送 `tavern` 動作。正式的互動是 6B-4 的範圍。
3. **NPC 畫成預設紙娃娃**：人設卡沒有外觀資料，所以範本是 `npc_<id>`，照我方陣營用預設外觀，頭上也會有一般單位的小血條。正式外觀要等美術或 6B-4。
4. **方向鍵佇列最多 3 步**，超過的丟掉，免得放開鍵之後還一直走。按住鍵時是瀏覽器的連發速度。
5. **第一次載入不跳地名**：只有換到另一張實地地圖時才跳；從節點圖地點走進實地地圖也算換地圖。
6. **地圖縮放**：依左欄寬度和視窗高度縮放，倍率夾在 0.4～1.5。24×18 的霧渡鎮在 1024 寬的視窗約 0.54 倍；格子偏小，6B-5 的 HUD 可能要重新排版面。
