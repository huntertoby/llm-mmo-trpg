# Phase 5D-2 完成報告：材料與掉落

> 規格：`docs/phases/Phase5計畫.md` 第 27 節（本段新增；原本的「之後各段規格」佔位節順延成第 28 節）。分支 `worktree-agent-abdd6f77bb7843351`。
> 內容依 `docs/design/20-第一季商店與裝備內容.md` 20.1、20.2、20.5（優先）、18.2.4、08 8.26.2；數值都在 `content/world/loot.yaml` 與 `items.yaml`，被改時只動資料。

## 1. 交付

| 項目 | 內容 | 主要檔案 |
|---|---|---|
| 規格 | 第 27 節「5D-2 詳細規格」（範圍、規則、代決 5D2-1～11、驗收） | `docs/phases/Phase5計畫.md` |
| 材料 | 雲嶺 8 種（霧晶、符紙灰、丹砂、青竹節〔5D-1 已有〕、狼牙、雷羽、活血骨〔稀有〕、雲頂霧晶〔稀有〕）＋通用粗料（已有）、精料、上料；`WorldItemDef` 加 `rare`、`grade`（coarse／fine／superior，只有材料能有） | `content/world/items.yaml`、`src/trpg/content/world_economy.py` |
| 掉落規則 | `loot.yaml`（`LootRules`）：材料 40%、通用料依等級、裝備 15%／精英必掉＋史詩 50%、物品等級上限 10、回收係數 3／5／8／12、傭兵系統裝備（稀有、7 欄）、雲嶺關鍵字與家族對照；跨檔案檢查（區域、敵人、詞綴、材料） | `content/world/loot.yaml`、`src/trpg/content/world_loot.py`（新）、`library.py`（`world_loot`） |
| 產生器 | `generate_item(..., keywords=)`：稀有起的 build 詞條有符合關鍵字的技能強化詞條就只從裡面挑；不給時逐位元相同（有測試） | `src/trpg/content/item_gen.py` |
| 掉落 | 打贏才掉；敵方倒下就掉、第三方要「倒下前最後一次受傷的來源是我方」；精英必掉 1 份（詞綴稀有材料 > 家族 > 通用）；一場最多 1 件裝備；亂數 `{battle_seed}:loot`；材料先、裝備後逐份進背包，放不下的不撿並記錄 | `src/trpg/world/loot.py`（新）、`battle.py` |
| 裝備 | `CharacterState.gear`（背包裡的裝備，每件 1 格）、`equipment`（穿戴中）；`equip` 世界動作（城鎮或營火，照 roguelite `equip`）；開戰用穿戴的；`sell` 收裝備（物品等級 × 係數）；傭兵的系統裝備；影子存裝備、借用時超過招募者等級的不穿 | `src/trpg/world/gear.py`（新）、`economy.py`、`economy_actions.py`、`state.py`、`party.py`、`shadows.py`、`step.py`、`actions.py` |
| API | `WorldActionRequest` 加 `equip`；`InventoryView.bag` 列裝備（`gear`、`can_equip`、`equip_problem_zh`、回收價）、`equipped_zh`；`WorldView.last_loot_zh`；事件句子（掉落、換上、賣裝備用名稱）；OpenAPI 與前端型別重產 | `src/trpg/api/world_economy_view.py`、`world_economy_schemas.py`、`world_schemas.py`、`world_presenter.py`、`client/openapi.json`、`client/src/api/schema.d.ts` |
| 前端（最小） | 地點圖「最近一次戰鬥」下多一行掉落；背包列的裝備顯示「裝備」與「裝上」（不能換時停用，原因用共用 `<Hint>`）；「穿戴中」清單；商店賣出列自動帶裝備 | `client/src/world/WorldPanel.tsx`、`EconomyPanel.tsx`、`client/src/api/types.ts` |
| 測試 | `tests/content/test_world_loot.py`、`tests/world/test_loot.py`、`tests/world/test_gear.py`、`tests/api/test_world_loot_api.py`、vitest（`economy.test.ts` 加 1 則）；`tests/api/test_world_economy_api.py` 改成忽略打贏撿到的材料 | — |

## 2. 版本與確定性

- 新欄位都有預設值（`CharacterState.gear`／`equipment`、`LastBattle.loot`、`ShadowSnapshot.equipment`、`ItemSoldEvent.name_zh`），`trpg-char/1`／`trpg-world/1`／`trpg-wlog/1` 不升版號（同 5D-1 的做法）；引擎與 `LOG_FORMAT` 沒改。
- 注意：舊日誌在新程式重播時，打贏的 `fight` 會多出掉落事件與背包內容（同 5D-1 加金幣時的情況）；格式沒變、仍逐位元可重播。
- 掉落亂數只來自 `battle_seed`；傭兵裝備來自 `merc_gear:{傭兵}:{欄位}:{等級}`（每個人一樣）；不耗角色亂數、不讀時間、不呼叫 LLM。

## 3. 代決（規格 27.9；開發 PM 定，最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5D2-1 | 材料 ID、名目價 | 開發 PM 取 ID；名目價 10（稀有 40）；材料不能賣也不在店裡賣，不影響金幣 |
| 5D2-2 | 沒有家族材料的敵人 | 掉通用料：地點建議等級 1～3 粗料、4～7 精料、8～10 上料 |
| 5D2-3 | 第三方「被我方擊倒」 | 倒下前最後一次受到傷害的來源是我方單位（含召喚物）；來源不明（地形、狀態）不算 |
| 5D2-4 | 精英必掉 1 件 | 一場最多 1 件 |
| 5D2-5 | 詞條偏向該區關鍵字 | 只影響稀有起的技能強化詞條；雲嶺只有「帶電」有現成詞條（`affix_kw_shock_area`，主手／副手／項鍊） |
| 5D2-6 | 背包滿了 | 放不下的那份不撿，事件與 `last_loot_zh` 寫「背包滿了，沒撿到：…」；不新增暫存區或信箱 |
| 5D2-7 | 換下的裝備放不下 | 照樣放回背包（可超過 30 格；之後撿不到，直到賣掉） |
| 5D2-8 | 傳說、初始裝備回收 | 不收（20.1 只有 4 種係數；初始武器沒有物品等級） |
| 5D2-9 | 傭兵主手、副手 | 照底稿武器不換；其餘 7 欄範本沒穿的穿系統裝備（稀有、物品等級＝主角等級） |
| 5D2-10 | 影子裝備「壓到招募者等級」 | 物品等級超過的那件不穿（不重算數值） |
| 5D2-11 | 誰撿 | 只有主角的背包 |

## 4. 待 PM 決定

1. **潮濕、隱蔽沒有技能強化詞條**：20.2 的雲嶺偏向只有「帶電」生效；要照字面就要在 `affixes.yaml` 加潮濕、隱蔽的技能強化詞條（內容工作，玩法 PM）。
2. **影子裝備的「降級」**：目前超過招募者等級的整件不穿；若要照比例降到招募者等級，需要「依新等級重算詞條數值」的規則。
3. **精英必掉 1 件**是一場 1 件還是每名精英 1 件（目前一場 1 件）。
4. **背包滿了**：目前直接不撿；是否要信箱／暫存區或戰後先選要丟什麼（5D-4 背包畫面時一起決定）。
5. **平衡**：傭兵每欄多了稀有裝備、主角有裝備掉落，隊伍會變強；本段沒跑模擬（守則：不跑大型模擬），建議 5D 收尾時跑一次 5A-SIM 類的勝率摘要。
6. **雲頂觀掉霧晶**（18.2.4 來源之一）是地點而不是敵人：等 5F 雲頂觀的陣容到位後在 `families` 加對應敵人即可；霧鎖真人掉雲頂霧晶、Boss 必掉史詩在 5F。
7. **脫下裝備**、分解（20.1「只能分解或用掉」）不在本段（分解在 5D-3）。
8. 盜賊、山豹、石背熊、多數修士 18.2.4 沒列材料 → 掉通用料；要不要給盜賊專屬材料。

## 5. 檢查

（見第 6 節，交件前填入。）
