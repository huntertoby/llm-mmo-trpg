# Phase 3-54a 報告｜風元素補強（玩法決定 #56，06 6.33）

## 做了什麼

風的三個專屬機制：**吹送**（新原語 `blow_surface`）、**元素擴散**、**風壓撞擊**。數值都放在 `content/rules/core.yaml` 的 `wind:`（模型 `trpg.content.rules.WindRules`）；引擎在 `trpg/engine/wind.py`（風向、擴散）與 `trpg/engine/effects/blow.py`（吹送效果處理器）。**沒有新增種子技能**（3-54c）；驗證用的技能都寫在測試裡。

### 規則對照表

| 06 6.33 | 實作 | 備註 |
|---|---|---|
| 吹送：一招把一片表面（火、毒、冰、水、油、煙霧）往風向整片平移 2～3 格 | 原語 `blow_surface`（`distance` 2～3，必填）；可吹送的表面 `wind.blow_surfaces`；先把影響格的表面全部拿起，再依風向由前往後放下 | 聖光、黑暗不在清單，不會被吹動 |
| 風向（6.33 沒寫） | 方向型形狀＝形狀方向；中心格型（十字、方陣…）＝「施放者 → 中心格」主要軸向（整片同方向）；以施放者為中心或單體＝「施放者 → 該格」主要軸向（往外吹）；施放者腳下沒有風向 | 待決 1 |
| 邊界、障礙（6.33 沒寫） | 一格一格前進，遇到地圖外、牆壁與致命地形（表面不能存在的格子）、`blocks_move` 物件、**比目前高**的格子就停在前一格；單位不擋 | 待決 2 |
| 和既有表面重疊（6.33 沒寫） | 落點照「產生表面」的互動表（例：水落在火上熄滅、油落在火上保持火）；多片落在同一格時原本在最前面的先放；保留剩餘回合、陣營、建立者（地圖原有的永久表面仍是永久）；帶元素的表面落在物件上照常觸及 | 待決 3 |
| 元素擴散：風吹到火、冰、毒、雷的表面或區域時，範圍往風向擴大 1～2 格 | 技能的 `element: wind` 傷害效果（`affects` 為 enemies／all／tiles）結算完後，影響格中 `wind.spread_surfaces`（火、冰、毒）的表面，與涵蓋影響格、帶 `wind.spread_zone_elements`（火、冰、毒、雷）元素的固定／移動型區域，從每個被吹到的格子往風向多長 `wind.spread_distance` 格；遇到擋風的格子停下；以當下狀態一次算完，不在同一次施放中連鎖 | 擴大格數取 **1**（待決 4）；沒有「雷表面」（待決 5） |
| 風壓撞擊：被風元素推去撞牆、撞人、撞物件時撞擊傷害 +50% | 風元素技能（`is_wind_skill`：頂層有 `element: wind` 的傷害效果）的 `push` 撞擊傷害 × `wind.collision_permille`（1500）；撞到的單位與 `breakable` 物件也一樣；`Collided.damage_permille` 記錄倍率 | 拉扯不算（待決 6）；武器詞條／修正規則加的風不算（待決 7） |

### 與既有內容的衝突（已照 6.33 處理，請 PM 確認）

- **互動表「風吹散毒」（`wind_disperses_poison`）已移除**：6.33 寫「風吹到毒…擴大」，與舊規則「風吹散毒」相反。保留舊規則的話，風元素傷害會先把毒吹散，擴散永遠不會發生。「風吹散煙霧」保留（煙霧只在吹送清單、不在擴散清單）。
- 互動表的 `wind_spreads_fire`、`wind_pushes_*`（需要帶方向的元素觸及）在現有引擎裡沒有任何來源會觸發（只在 `run_effects` 的效果層測試裡用到）。**沒有動**；新的擴散不經互動表。

### 各入口

- **預算**：`blow_surface` 用 `per_distance`、`base_points: 1`（2～3 點 × 形狀倍率；初值，未經模擬）。風元素技能的推擊加「風壓撞擊」點數＝撞擊骰顆數（省略為 1d6）× `collision_die_points` × 0.5（`trpg.skillgen.budget._wind_collision_points`）。元素擴散不計點（同其他元素互動，例如火點燃油）。
- **驗證器／工坊**：`min_rarity: rare`、`active_only`、`forbid_affects: [self, enemies, allies, all]`（只作用在格子），由通用規則與 `option_effect_rules` 的事前停用自動處理；骨架：控場核心、範圍附帶加入 `blow_surface`。玩家文字加在 `content/workshop_text.yaml` 的 `原語.blow_surface`（**實作者初稿，待玩法 PM 改寫**；條目數 151 → 152）。
- **隨機組合器**：`blow_surface` 不進一般抽選（列入 `_HAND_WRITTEN_PRIMITIVES`），改由 `_blow_secondary` 以 `composer.blow` 獨立串流加入範圍骨架的附帶效果（稀有以上、還有空位時 `structure.blow_surface_permille` 80‰；距離旋鈕 `structure.blow_distances` [2, 3]）。沒抽中的種子結果不變——CLI 快照與 run auto 種子都沒有變。
- **LLM 提議**：模型由 `skill_primitives.yaml` 產生，自動包含 `blow_surface`（測試確認 schema 與 `proposal_from_skill`）。
- **卡片**：吹送「把範圍內的表面（…）整片往風向吹走 N 格（遇到牆、擋路的物件或較高的地形就停下）」；風元素傷害加一句擴散；風元素推擊加「風壓：撞擊傷害 +50%」。
- **事件與敘事**：新事件 `surface_blown`（每片一個，含起點、落點、方向）、`zone_expanded`；落點與原格另有 `surface_changed`（原因 `blow`／`wind_spread`）。
- **AI、預覽**：走通用的事件估值與 `affected_tiles`（`PRIMITIVE_VALUATION`、`PRIMITIVE_PREVIEW` 已登錄）。
- **前端**：技能圖示部件 `blow_surface`（表面＋風箭頭）；`vfx.ts` 在沒有傷害元素時，施放者的 `surface_blown` 讓施放特效用風的配色（最簡單版本，沒有做表面移動動畫——畫面本來就依每步的狀態重畫表面）。

### 影響盤點

- `LOG_FORMAT` `/74` → **`/75`**（新原語、新事件、`collided.damage_permille`、核心規則 `wind`、互動表少一條）。3-53 沒有遞增，合併時請 PM 留意兩邊是否還有別的遞增。
- `skill_icons.json`：重新產生，沒有差異（沒有新內容技能）。
- glossary：`client/src/battle/fixtures/glossary.json` 重新匯出（多了吹送原語）。
- OpenAPI：重新匯出與 `gen:api`，沒有差異（事件不在 schema 的型別裡）；vitest 夾具不用改。
- CLI 快照、run auto 種子：`-m "slow or not slow" tests/cli` 148 passed，**沒有更新任何快照**。

## 測試

- 新增 `tests/engine/test_wind_54a.py`（85 項）：吹送 6 種表面 × 4 風向、不可吹送的表面、保留剩餘回合／永久、地圖邊（距離 2、3）、障礙表（牆、`blocks_move` 物件、較高地形、單位不擋）、整片擠到邊、落點互動表、中心格型整片同方向、以自身為中心往外吹；擴散 3 種表面 × 4 風向、其他表面不擴散、煙霧照樣吹散、不連鎖、牆／地圖邊／物件擋住、非風元素不擴散；區域 4 種元素 × 4 風向、物理區域不擴大、移動型區域擴大與被牆擋；風壓撞擊 ×1.5（同骰值逐筆比較）、拉扯不加成；**一場含風技能（測試用：錐形風刃＋吹送、單體風推）的整場戰鬥重播一致**（這場有 16 次吹送、5 次擴散；AI 剛好沒有用風推撞到東西，風壓撞擊由前面的表格測試覆蓋）。
- 新增 `tests/skillgen/test_wind_54a.py`（6 項）：工坊選項（只能選格子、距離 2～3、玩家文字）、驗證器、預算、組合器獨立串流、LLM 提議、**卡片＝實戰**（吹送距離、擴散、風壓 1500‰）。
- 新增 `tests/narrative/test_wind_events_54a.py`；`client/src/battle/vfx354a.test.ts`。
- 修改既有測試：`test_environment.py`（毒不再被吹散）、`test_environment_content.py`（互動表少一列）、`test_coverage.py`（`blow_surface` 列入「尚無手寫技能」允許清單，3-54c 補種子後刪除）、`test_skills_content.py`（同上）、`test_skill_rules_content.py`（骨架清單）、`test_workshop_text_48f.py`（152 條）、兩個重播測試的 `LOG_FORMAT` 斷言改 `/75`。
- 結果：pytest engine、content、skillgen、llm、narrative、api、roguelite、sim、shared、架構與原語對應 **7453 passed、1 skipped**；`-m "slow or not slow" tests/cli` **148 passed**；vitest **103 檔 992 passed**；build 成功；ruff check、ruff format --check、mypy（719 檔）、lint-imports（7 kept）通過。

## 待 PM 決定

1. **風向**：6.33 沒寫。現在是「方向型形狀＝形狀方向；中心格型＝施放者 → 中心；自身／單體＝往外」。若要「整片一律同一方向」，自身為中心的形狀需要另外決定方向（例如面向）。
2. **擋風的格子**：牆、致命地形、地圖外、`blocks_move` 物件、**比目前高的格子**（照推擊的規則）。高低差是否擋風、致命地形（深淵、岩漿）是讓表面停下還是「吹進去就消失」，請決定。
3. **重疊**：落點照產生表面的互動表；永久表面吹動後仍永久。擴散長出的格子沿用原表面的剩餘回合（原表面永久時用表面的預設持續）。
4. **擴散格數**：6.33 寫「1～2 格」，現在固定取保守的 1（`wind.spread_distance`，上限 2）。要改成 2、或依技能（例如傷害骰／形狀）決定，請決定。
5. **「雷的表面」**：內容裡沒有雷表面，只做了「帶雷元素的區域」擴大。跟隨施放者的區域不擴大（格子由施放者位置決定）。
6. **風壓撞擊只算推擊**：拉扯、技巧動作「推擊」（Shove）、互動推物件不算。
7. **「風元素的技能」的判定**：技能資料頂層有 `element: wind` 的傷害效果才算（卡片、預算、實戰同源）。武器詞條（`affix_weapon_wind`）或修正規則加上的風、普攻都不觸發擴散與風壓撞擊。
8. **移除「風吹散毒」**（見上方衝突說明），請確認。
9. **預算初值**：吹送 1 點／格（× 形狀倍率）、風壓撞擊每顆撞擊骰 +0.5 點；擴散不計點。組合器吹送機率 80‰。都未經模擬。
10. 工坊玩家文字 `原語.blow_surface` 是實作者初稿，請玩法 PM 改寫。
