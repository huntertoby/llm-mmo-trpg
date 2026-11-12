# Phase RT-4 報告：傭兵外觀改成五區出身＋#131 改名

實作者，2026-11-04。規格：`docs/art/區域主題移植需求.md` 第 4 節、`docs/art/sample/merc-portraits.html`（NEW 表）、決定 #131（`docs/玩法決定紀錄.md`、`docs/design/09-世界與敘事.md` 9.6.8）。

## 1. 做了什麼

1. **改名（#131）**：9 名傭兵照 #131 改名；ID、build、職稱不變。開局帶 `merc_tiebi`、`merc_huichun`，也就是賽倫、回春，原本就是這兩名，所以 `default_party` 不用改。
2. **出身與外觀**：
   - `MercenaryDef` 新增 `origin` 和 `portrait` 兩個欄位：
     - `origin` 是出身區的 ID。載入時跨檔檢查它必須在 `regions.yaml` 裡。
     - `portrait` 的寫法同 NPC 人設卡（6C-7）。
   - 9 名的 look、gear、extras 照 NEW 表抄進 `content/world/mercenaries.yaml`：
     - 駝峰名稱改成底線，例如 `hairColor` 改成 `hair_color`。
     - 種族外觀（精靈、矮人、晶能義體人、角魔、獸人、海民）照 `raceArt.js` 展開。
3. **API**：
   - `MercenaryView` 新增 `origin`、`portrait`。
   - 重新產生 `client/openapi.json` 和 `client/src/api/schema.d.ts`。
4. **頭像**（`client/src/render/portrait.ts`）：
   - 新增三區的框色與底色：晶冠 `#8ab0ff`、樞市 `#4ad0c8`、霜潮 `#6ac0e8`，數值照樣張。
   - 新增 4 種配件 `crest`、`circlet`、`cyber_eye`、`coral`，座標與顏色照樣張的 `more()`。
   - 匯出 `PORTRAIT_EXTRAS`，列出畫得出來的配件名。
5. **獠牙**：
   - `NpcPortraitLook` 新增選填的 `tusks`，給獸人鏽牙用。
   - `npcLook.portraitRaceLook` 把獠牙帶進紙娃娃的種族部件。
   - schema 的 `extras` 沒有列舉（只檢查 ID 格式），pydantic 那邊不用改。
6. **雇用清單畫頭像**：
   - `client/src/world/PartyPanel.tsx` 的雇用清單，每名傭兵前面畫 48px 頭像，框色是出身區的顏色。
   - 6C-7 時雇用清單沒有頭像（6C-7 報告待決 4）。不加頭像，「框色照出身區」在遊戲裡就看不到，所以照最保守的做法只加在清單上。

## 2. 檔案清單

| 類別 | 檔案 |
|---|---|
| 內容 | `content/world/mercenaries.yaml` |
| Python | `src/trpg/content/world_mercenaries.py`（`origin`、`portrait`）、`src/trpg/content/world_events.py`（`tusks`）、`src/trpg/content/library.py`（出身的跨檔檢查）、`src/trpg/api/world_party_schemas.py`、`src/trpg/api/world_party_view.py`、`src/trpg/world/step.py`（只改註解） |
| 前端 | `client/src/render/portrait.ts`、`client/src/world/npcLook.ts`、`client/src/world/PartyPanel.tsx`、`client/src/world/WorldCharacterPicker.tsx`（只改文案）、`client/openapi.json`、`client/src/api/schema.d.ts` |
| 測試 | `tests/content/test_world_mercenaries.py`（新增 3 項）、`tests/api/test_world_party_api.py`、`tests/api/test_world_shadow_api.py`、`tests/api/test_world_events_api.py`（註解）、`tests/world/test_party.py`、`tests/world/test_battle_setup.py`（註解）、`tests/world/test_companions.py`（註解）、`tests/world/test_oath.py`（註解）、`client/src/render/portrait.test.ts`（新檔，12 項）、`client/src/world/party.test.ts`、`client/src/world/fieldPeople.test.ts` |
| 腳本 | `scripts/ashen_waste_sim.py`、`scripts/season_boss_sim.py`（docstring、說明、報表標籤） |
| 截圖 | `docs/art/rt4_hire_list.jpg`、`docs/art/rt4_portraits_zoom.jpg` |

commit：`01ee7786`（改名、schema、API），`d6f434d3`（頭像、雇用清單），另有報告一筆。

## 3. 測試

- `tests/content` 加 `tests/world`：3566 項通過。
- 另外跑了直接相關的 api 測試：`test_world_party_api`、`test_world_shadow_api`、`test_openapi_snapshot`，全部通過。
- `trpg content check` 通過。
- ruff check、ruff format --check、mypy src（513 檔）、lint-imports（13 條）全部乾淨。
- client vitest 全部：219 個檔、2377 項通過。新的 `portrait.test.ts` 測這幾件事：
  - 五區框色正確，不認得的區域退回傭兵金；
  - 4 種新配件各自畫出樣張的顏色或形狀，畫法確定（同一位畫兩次一樣）；
  - yaml 裡 9 名都有出身和頭像，配件都畫得出來，五區都有人；
  - 名字對應表；
  - 鏽牙的獠牙有帶進紙娃娃。
- Python 的名字對應表照現有方式寫：`ROSTER` 改成新名，另加 `ORIGINS` 和 `EXTRAS` 兩張表。
- `corepack pnpm -C client build` 結束碼 0。

## 4. 新舊名對照

| ID | 舊名 | 新名 | 職稱 | 出身 |
|---|---|---|---|---|
| merc_tiebi | 鐵壁 | 賽倫 | 盾衛 | 晶冠 crystal_crown |
| merc_qingyin | 清音 | 莉瑟 | 祝禱師 | 晶冠（精靈） |
| merc_qingfeng | 青鋒 | 青鋒 | 近戰劍客 | 雲嶺 cloud_ridge |
| merc_huichun | 回春 | 回春 | 醫者 | 雲嶺 |
| merc_panshi | 磐石 | 鉚釘 | 守護者 | 樞市 arcane_hub（矮人） |
| merc_jinglei | 驚雷 | 七號線圈 | 雷水術士 | 樞市（晶能義體人） |
| merc_chiyan | 赤焰 | 灰燼瑪菈 | 火術士 | 荒原 ashen_waste（角魔） |
| merc_fuying | 伏影 | 鏽牙 | 陷阱師 | 荒原（獸人） |
| merc_chuanyun | 穿雲 | 珊瑚 | 弓手 | 霜潮 frost_tide（海民） |

## 5. 改過的文案（給玩法 PM 確認）

全 repo 搜尋舊名，docs/ 不算。對話、quests、narration、LLM 快照裡都沒有傭兵的舊名。玩家看得到的文案只有第 1 條：

1. `client/src/world/WorldCharacterPicker.tsx` 建角說明：「隊友：一開始帶系統傭兵**鐵壁**、回春……」改成「……**賽倫**、回春……」。
2. `content/world/mercenaries.yaml` 的 `default_party` 註解：「鐵壁＋回春」改成「賽倫＋回春」。
3. `src/trpg/content/world_mercenaries.py`、`src/trpg/world/step.py`：同上，只改註解。
4. `scripts/ashen_waste_sim.py`：
   - docstring 與 `--fire` 說明裡的「赤焰」改成「灰燼瑪菈」，「鐵壁」「穿雲」照表改；
   - 報表欄位標籤「赤焰主角」改成「灰燼瑪菈主角」。
5. `scripts/season_boss_sim.py`：docstring 照表改。

**沒有改**（不是傭兵）：

- 技能、狀態「鐵壁姿態」；
- 矮人種族技「穩若磐石」；
- 開發用起手「鐵壁」（`dev_starters.yaml`、roguelite 關鍵字標籤）；
- 合成品「驚雷霧袍」；
- 樞市地形「鐵壁」（`arcaneTerrain.ts`）；
- 紙娃娃開發頁的「鐵壁騎士」。

## 6. 截圖

在真的遊戲裡拍：

1. 自己的伺服器開在 8333 埠，存檔放 scratchpad，不碰 `saves/`；
2. 用自己的無頭 Chrome（9333 埠）建角色；
3. 走進霧渡鎮酒館，點雇用處。

截圖：

- `docs/art/rt4_hire_list.jpg`：雇用清單，9 人頭像依定位分組，賽倫、回春是預設勾選。
- `docs/art/rt4_portraits_zoom.jpg`：同一份頭像放大排成一列。看得出框色照出身區：晶冠藍紫、雲嶺綠、樞市青、荒原橘、霜潮海藍。新配件冠飾、額環紫晶、義眼青光、珊瑚珠也都看得到。

拍完後，伺服器與 Chrome 都用自己的工作 ID 結束了。

## 7. noqa

沒有新增。

## 8. 待 PM 決定

1. **地圖紙娃娃與戰場外觀沒有跟著換**：
   - 移植需求寫「地圖紙娃娃照 6C-7 的規則自動跟著」，但傭兵目前不會出現在實地地圖上，所以沒有紙娃娃可換。
   - 戰鬥中的傭兵外觀照舊，用底稿 build 的英雄範本與系統裝備。
   - 檢查清單「9 人頭像和地圖紙娃娃一致」因此無從比對。
   - 要讓戰場上的傭兵也用 `portrait` 換算的外觀，需要改開戰時的單位外觀，屬另一段。
2. **HUD 左側的隊友小卡仍是通用臉**：HUD 隊友小卡（賽倫、回春）是 6F-1 正在改的世界 HUD，這段沒碰。建議 6F-1 之後用 `party.mercenaries[].portrait` 和 `origin` 換上頭像，`PartyMemberView` 已經有 `mercenary` ID 可以對。
3. **鉚釘的護目鏡**：
   - 移植需求的外觀方向寫「護目鏡推到額頭」，也就是 `goggles_up`；
   - 樣張 NEW 表寫的是 `goggles`（戴在眼上）。
   - 照指示以 NEW 表為準。要推到額頭的話，只要改 yaml 一個字。
4. **雇用清單加頭像**：屬於版面變動。只加一個 48px 圖，沒改 CSS 檔，用行內樣式。
5. **NPC頭像.md 與 6C-7 報告**：裡面的傭兵舊名照指示不改（docs 舊紀錄）。
