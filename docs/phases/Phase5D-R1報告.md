# Phase 5D-R1 報告：5D 審查整理（世界端）＋ 5C-3f

範圍：`docs/phases/Phase5計畫.md` 第 1 節表格的 5D-R1 列與 5C-3f 列。重構項目行為不變（第 1、7、9 項除外），swamp 種子 7 重播一致。

## 交付項目

| # | 內容 | 位置 |
|---|---|---|
| 1 | 換裝檢查背包格數：換下的比換上的多（已穿副手換雙手武器）且背包放不下 → 拒絕「不能換裝備：背包放不下（需要 N 格，只有 M 格）」。roguelite 新增 `equip_swap`（同 `equip`，另回傳換下的物品，依放進背包的順序：被占用的副手、原本那格），`equip` 改成包它；world 的 `removed` 直接用回傳值，不再從背包切片推算。測試 `test_two_handed_needs_room_for_the_offhand` | `roguelite/gear.py`、`world/gear.py`、`tests/world/test_gear.py` |
| 2 | 新 `trpg/world/inventory.py`：`slots_used`、`slots_over`、`room_problem`、`check_room`、`bag_capacity`、`add_items`、`remove_items`、`remove_gear`（連同 `gear_mods`）。economy、crafting、loot、`api/world_economy_view.py` 改用；`economy.bag_slots_used`、`_with`、`_check_bag`，crafting 的 `_spend`／`_gain`／`_check_room`，loot 的 `_slots`／`_used` 刪除 | `world/inventory.py` 等 |
| 3 | `item_gen.generate_item_retrying(...) -> ItemDef | None`（`rng.fork(f"try/{n}")`，最多 `offer_attempts` 次，沒有產生器規則時 1 次；可選 `problems` 收集失敗原因，打造的錯誤訊息照舊）。打造、掉落、傭兵裝備改用，亂數與結果不變 | `content/item_gen.py` |
| 4 | `step._dispatch` 改分派表 `step.HANDLERS`（動作種類 → 處理，模組最後建表），noqa 拿掉；經濟 `ECONOMY_HANDLERS`、鐵匠 `CRAFTING_HANDLERS` 取代內部的 isinstance 串（`apply_economy`／`apply_crafting` 照舊可呼叫）。`tests/world/test_dispatch.py` 檢查每種世界動作恰好一個處理 | `world/step.py`、`economy.py`、`crafting.py` |
| 5 | `week_of` 移到新的 `world/season.py`；週長 `week_days` 從 `affinity.yaml` 移到 `world/rules.yaml`（`WorldRules.week_days`，預設 7，`DEFAULT_WEEK_DAYS`）；`AffinityRules.week_days` 刪除，摘要改「酒館每週 N 條傳聞」。`loot_rules` 移回 `world/loot.py` | `world/season.py`、`content/world_rules.py` |
| 6 | 傭兵裝備快取改掛在內容庫 `ContentLibrary.mercenary_gear_cache`（同 `retier_cache`：不是建構參數、不參與相等比較、隨內容庫回收），鍵「傭兵＋物品等級」，滿 1024 筆清空 | `content/library.py`、`world/gear.py` |
| 7 | 商店材料檢查改用 `grade == "coarse"`，`COARSE_MATERIAL` 刪除；情境「補給」名稱改 `situation_rules.yaml` 的 `exchange_name_zh`（事實文字也用它）；`ShadowSnapshot.gear` 刪除，舊存檔帶這個欄位讀入時忽略（`mode="before"` 驗證器，測試 `test_old_snapshot_with_gear_field_loads`） | `content/world_economy.py`、`world/situations.py`、`world/state.py` |
| 8 | 6.5.1 的浮動卡 grep 檢查**其實已在 vitest**（`client/src/ui/floatCardRule.test.ts`，3-32b 起：`title=`、portal、內聯 fixed／absolute、CSS fixed、CSS absolute＋z-index ≥ 20、`role=tooltip`／`dialog` 白名單）；`docs/開發PM交接.md` 6.5.1 寫「待排入」是舊的。這段只補一條漏網：直接改 DOM 的 `el.style.position = "fixed"`／`"absolute"` | `client/src/ui/floatCardRule.test.ts` |
| 9a | 一筆事實一項：有 npc 欄位、且該 NPC 在這個事件骨架裡的線頭只算「往來」，不再同時算「線索」 | `world/situations.py` |
| 9b | 隱藏地點顯示規則：新 `world.narration.location_name_for(library, viewer, region, location)`；朋友戰報（`report_line` 多一個 `viewer` 參數）與朋友影子存的地點（借用清單）套用；自己影子的存檔位置照常 | `world/narration.py`、`api/world_party_view.py`、`tests/api/test_hidden_location_names.py` |
| 9c | 影子裝備降級：`_drop_fixed` 先拿非 build 的固定點數詞條，只剩 build 詞條（`KeywordAffix`，關鍵字技能強化）仍超預算才拿它。測試 `test_downscale_keeps_build_affix_until_only_it_is_left` | `content/item_gen.py` |
| 9d | 帶電利用詞條卡片：現有文字已是「利用帶電的技能傷害 +N%」；加測試鎖住（含「傷害 +」、不含「雷電」） | `tests/content/test_equipment_content.py` |

## 「沒有經濟規則」時的統一行為（第 2 項）

**內容庫沒有 `world/economy.yaml` 時背包沒有格數上限**（`bag_capacity` 為 `None`，`room_problem` 一律 `None`）。打造、分解、掉落、換裝原本就是這樣；經濟動作（買、賣、腰包、道具）本身沒有規則時一開始就拒絕，所以原本 economy 那邊的「拋錯」路徑走不到，行為不變。這是改動最少的統一方式（保守）。

## 改了既有斷言的地方（附理由）

- `tests/world/test_situations.py::test_facts`：拿掉 `("clue", "thread:temple_quarrel")`——5C-3f 要求的行為改變（該線頭有 npc，只算往來）。
- `tests/world/test_shadows.py::test_town_prep_saves_shadow`：拿掉 `assert snap.gear == ()`——欄位依第 7 項刪除。
- `tests/content/test_world_economy.py`：`COARSE_MATERIAL` 常數刪除，改寫字面值 `"item_coarse_material"`（斷言內容相同）。
- 匯入路徑：`tests/world/test_economy.py` 改用 `inventory.slots_used`、`tests/world/test_loot.py` 從 `world.loot` 匯入 `loot_rules`（斷言不變）。

## 代決（原型解讀，照最保守做法）

| 編號 | 項目 | 做法 |
|---|---|---|
| R1-1 | 換裝的格數檢查時機 | 只在「換下的件數多於換上的」（背包件數變多）時檢查；一換一不檢查（背包已滿也能一換一） |
| R1-2 | 沒有經濟規則的背包 | 沒有上限（見上節） |
| R1-3 | 有 npc 的線頭，但 NPC 不在這個事件骨架裡 | 仍算「線索」（往來的事實是「事件裡的 NPC」，否則這筆事實會消失）。只有 NPC 在骨架裡時才只算往來 |
| R1-4 | 「build 詞條」的判定 | 詞條是 `KeywordAffix`（關鍵字技能強化）就算，不看是否在第 1 條 |
| R1-5 | 週長沒有世界規則時 | 用 `DEFAULT_WEEK_DAYS`（7） |
| R1-6 | 情境交換名稱 | `exchange_name_zh` schema 預設「補給」（舊內容資料夾照讀），內容檔也明寫 |

## 待 PM 決定

1. R1-3：有 npc 但 NPC 不在事件裡的線頭要算線索（目前）還是完全不算。
2. `docs/開發PM交接.md` 6.5.1 最後一點「自動檢查（待排入）」可以改成「已在 `floatCardRule.test.ts`」（文件屬開發 PM，這段沒改）。
3. 9c 在現有內容下幾乎不觸發：build 詞條（8 點）多半比其他固定點數詞條便宜，40 個種子的史詩物品裡沒有一件會因新順序而改變結果；規則照代決寫好並有建構測試。

## 檢查結果

- ruff check、ruff format --check、mypy（1160 檔）、lint-imports（11 kept）：通過。
- pytest `tests/world tests/api tests/content tests/llm tests/test_architecture.py tests/roguelite`（-n 8）：3654 通過。
- vitest：135 檔、1265 測試通過；`pnpm build`：成功（只有既有的 chunk 大小警告）。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致（與 5D-4 報告相同）。
- OpenAPI 重產：沒有差異（API 型別沒變）。
