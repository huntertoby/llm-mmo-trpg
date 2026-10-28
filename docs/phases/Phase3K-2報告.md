# Phase 3K-2 報告：戰後裝備三選一接進一輪（玩法決定 #49）

規格：`docs/phases/Phase3K計畫.md` 第 0、1.1、2（3K-2 列）、3、4、5.1 節；設計 07 7.1、08 8.5、8.22.1。沒有碰到規格對不上而需要停下來的地方；規格 3K-2 列開頭舊寫的稀有度權重「50／35／13／2」已照第 1.1 節第 8 點用 **40／25／20／13／2**（`content/item_gen.yaml` 的 `rarity_weights`，3K-1 已是這組）。

## 做了什麼

### 一輪流程（`trpg.roguelite`）
- **新節點 `GearOfferNode`**（`state.py`）：每打贏一場 **一般** 戰鬥，`finish_battle` 先進這個節點，選完（或跳過）才進 `next_node`（升級、營火、下一場）；Boss 戰贏了不給。順序「裝備三選一 → 升級」。測試模式也一樣給。
- **候選 `make_gear_offer`**（新模組 `roguelite/gear.py`）：3 件（`item_gen.yaml` 新欄位 `offer_size: 3`、`offer_attempts: 8`），**部位不重複**（8 種物品種類：主手、副手、頭、身體、手、腳、項鍊、戒指；亂數洗牌取前 3），主手只出和主角目前武器 **同大類** 的武器；主手是雙手或成對武器時 **不出副手**。稀有度走 3K-1 的 `roll_rarity`（40／25／20／13／2），物品走 `generate_item`（物品等級＝抽到當下的主角等級，戰後升級之前）。亂數標籤 `gear/<場次>`（再分 `parts`、`item/<序>/<重抽次>`），同種子同候選。穿不上的候選（例如傳說物品超過全身上限）重抽，最多 8 次，仍不行就少一件。
- **`RunState` 新欄位**：`equipment: dict[欄位, ItemDef]`（目前穿戴，物品連同完整定義，因為產生的物品不在內容庫）與 `backpack: tuple[ItemDef, ...]`，都有預設值。`equipment` **非空時就是全身裝備**（第一次換裝把範本或測試模式的裝備一併搬進來）；空 ＝ 照舊用範本／測試模式的裝備。`run_loadout`（開戰的 `Loadout`、角色面板、有效屬性共用）搬到 `gear.py`，`progress.run_loadout` 仍可匯入。
- **穿戴 `equip`**：直接換上，換下的進背包；一律過 `loadout_problems`（全身上限、代價型、同一枚戒指、雙手／成對武器不能拿副手……）。主手換成別把武器時主角的 `hero.weapon` 跟著換（只能同大類，否則 `ChoiceError`）；主手原本沒有物品時，主角原本的武器變成一件沒有詞條的物品（id `base_<武器>`）進背包，營火可以換回；換成雙手／成對武器時副手自動收進背包。戒指：先放空的欄位，兩枚都有時換掉預算分數較低的。
- **營火換裝**：新選擇 `EquipChoice(item_id, slot?)`（只在營火、免費、不限次數、不推進節點），和技能換裝、屬性重配同一個畫面。
- **選擇型別**：`GearPickChoice(pick | null)`（null＝跳過）、`EquipChoice`；`Choice` 聯集已加入，API `POST /api/runs/{id}/choice` 直接可用；戰鬥中換裝不會發生（只有節點在營火／三選一時才合法）。
- **`run auto`（AI 代打）**：`auto_gear_pick`——對每個候選算「預算分數（詞條點數＋基礎加成，3K-1 的 `item_points`）減去該部位目前裝備的預算分數」（部位空著算 0，所以空部位一定優先），挑增益最大的，**沒有增益就跳過**；同分取索引小的。**保守：不換武器**（主手候選的武器與主角現在的不同時略過，因為技能是照現有武器挑的）；營火不換裝（背包由玩家自己換）。CLI 每個三選一印一行，例如 `裝備三選一（第 1 場後）：優良弓、普通布鞋、普通戒指 → 換上「優良弓」`；`run show` 摘要多「裝備：…；背包 N 件」。

### 3K-1 留下的四項
1. **副手屬性詞條偏好比照武器**：`item_gen._attribute_weight` 改成看 `base.weapon or base.offhand` 的縮放屬性（單屬性 50%、雙屬性各 25%、其餘平分）。測試：法書（智力）智力 ≈50%、其餘 ≈10%；圓盾（力量／體質）各 ≈25%、其餘合計 ≈50%。
2. **條件成立率**：核對 `item_gen.yaml` 的 `condition_rates_permille` 已是 `common: 600／occasional: 350／rare: 200`（＝08 8.21.2.2 的 0.6／0.35／0.2），**不用改**；加了測試固定這個值，且每條條件詞條的分類都在這三級內。（逐條分類是 3K-1 實作者的初值，仍待 PM 確認。）
3. **稀有度權重**：已是 40／25／20／13／2；`RunState` 的候選抽樣測試（約 4500 件）在 ±3% 內符合。
4. **API／前端物品卡的基礎加成**：`GearItemInfo` 新欄位 `rarity`、`rarity_zh`、`item_level`、`base_bonus_zh`（「基礎加成：傷害 +4%」「基礎加成：防禦值 +2%」）、`points`（預算分數）；測試物品清單的詞條摘要（`itemSummary`）也先寫基礎加成。

### API 與前端
- `NodeOut.kind` 多 `gear_offer`（`gear: GearOfferOut`：場次與 3 件 `GearCandidateOut`）；`HeroOut` 多 `equipment`（9 個欄位，空著 `item` 為 null）與 `backpack`（每件附比較）；`SaveSummary.node` 多 `gear_offer`。`GearCandidateOut`＝物品卡＋放進的欄位＋該欄位目前的裝備＋連帶效果（武器換了、副手收進背包）。已重新匯出 `client/openapi.json` 並 `gen:api`。
- **戰後三選一畫面**（`screens/RunGearOffer.tsx`，卡片 `ui/gear/GearCardView.tsx`）：排版照升級的技能候選（`.run-offer-card`、「選這個（再按一次取消）」），底部按鈕在沒選時寫「跳過（不換裝備）」、選了寫「換上『名稱』」；顯示順序用種子洗牌（同 `displayOrder`）。每張卡：圖示、名稱＋稀有度（顏色）、部位・稀有度・物品等級・武器資訊、基礎加成與詞條、連帶效果、**和目前裝備的比較**（目前裝備圖示用共用浮動卡 `PartTip` 滑過看詞條；下方一行「預算分數 8 → 12（+4）」，增強綠、減弱橘）。
- **營火背包**（`run/BackpackSection.tsx`）：每件附比較與「換上這件（部位）」。
- **角色面板**多「裝備」一列（每件裝備圖示，共用浮動卡顯示詞條；基礎武器不算）。
- 存檔列表標籤多「裝備三選一」。

### 順手修掉的既有錯誤
`narrative/events.py` 的規則改變類事件描述用 `ruleset.skill_def(e.skill_id)` 找技能名稱，但 **裝備詞條的規則改變**（傳說物品，`skill_gear_*`）沒有技能定義 → 穿著傳說規則物品打到觸發時 `KeyError`（測試模式早就有這個潛在問題；3K-2 起戰後 2% 會拿到傳說物品，第一次在 API 自動存檔測試撞到）。新增 `_skill_name`：找不到技能時用詞條名稱（再找不到回傳 id）。

## 存檔與相容性
- `SAVE_FORMAT` **`trpg-run/5` → `trpg-run/6`**。新增的 `equipment`、`backpack` 有預設值，節點多一種 `gear_offer`，所以 **`/5` 的存檔照常讀入**（`COMPATIBLE_FORMATS`，讀入後視為 `/6`，下次存檔寫出 `/6`）；`/1`～`/4` 仍拒絕並提示開新一輪。**`/6` 的存檔舊版程式讀不了**（只有降版會有問題）。
- 戰鬥中的存檔：裝備快照內嵌在戰鬥設定、一輪的存檔帶 `equipment`／`backpack`，所以重播一致（測試涵蓋「戰鬥中存檔 → 讀檔 → 重播到存檔當下，主角狀態逐字相同」）。
- **`LOG_FORMAT` 不變（`/71`）**：這段沒有改戰鬥紀錄格式（物品定義沒有新欄位、引擎沒動）。`/70` 以前的戰鬥中存檔的限制是 3K-1 已有的。
- 舊的「以內容庫測試物品開局挑裝備」（測試模式 `test_equipment`）照舊；`equipment` 非空後以它為準（`test_equipment` 仍記著開局挑的，只用來顯示與沒換過裝時的 base）。**沒有把 `test_equipment` 遷移進 `equipment`**（保守：舊存檔與 API 欄位完全不變）。

## 規則對照表

| 規則 | 實作 | 測試 |
|---|---|---|
| 每場一般戰鬥打贏給 3 件（Boss 不給） | `finish_battle`＋`gear_offer_node` | `test_gear_comes_before_level_up_and_skip_keeps_the_gear`、`test_boss_battle_win_ends_the_run_without_a_gear_offer`、`test_finished_battle_writes_back_and_levels_up`（API） |
| 先裝備、再升級 | 節點順序 | 同上；`test_won_battle_writes_back_...` |
| 3 件部位不重複、主手同大類 | `make_gear_offer` | `test_three_distinct_parts_and_main_hand_matches_the_hero_class`（3 種武器大類 × 60 種子） |
| 稀有度 40／25／20／13／2 | `roll_rarity`（3K-1） | `test_rarity_follows_the_weights_40_25_20_13_2` |
| 稀有度不加強度（同等級預算） | 3K-1 預算 | `test_offered_items_are_at_the_hero_level_budget` |
| 可以跳過；挑到的直接換上；換下的進背包 | `take_gear`／`equip` | `test_picking_equips_directly_and_the_replaced_item_goes_to_the_backpack` |
| 營火可以換裝（不限次數、免費） | `EquipChoice` | `test_campfire_can_swap_gear_from_the_backpack_for_free` |
| 穿戴驗證（全身上限、雙手武器不能拿副手、同枚戒指） | `loadout_problems` | `test_every_offered_item_can_be_worn_...`、`test_two_handed_main_hand_moves_the_off_hand_into_the_backpack`、`test_rings_fill_the_empty_ring_slot_first_then_replace_the_weaker` |
| 換武器只能同大類 | `equip` | `test_main_hand_swap_changes_the_hero_weapon_within_the_class` |
| 亂數 `gear/<場次>` 同種子同結果 | `Rng.fork` | `test_offer_is_deterministic_per_seed_and_battle`、`test_auto_play_is_deterministic_and_takes_gear` |
| 存檔往返、戰鬥中存檔重播一致 | `RunSave` | `test_save_round_trip_...`、`test_battle_in_progress_replays_identically_with_run_equipment`、`test_a_trpg_run_5_save_without_the_new_fields_still_loads` |
| 換上後開戰的實際數值等於卡片 | 同一個 `build_gear` | `test_battle_values_match_the_item_cards`（屬性逐項、最大 HP）、`test_the_hero_spawns_with_the_run_equipment` |
| AI 挑預算分數增益最大 | `auto_gear_pick` | `test_auto_pick_prefers_the_largest_gain_over_what_is_worn` |
| 副手屬性偏好、條件成立率 | `item_gen`、`item_gen.yaml` | `tests/content/test_item_gen.py` 三個新測試 |
| 傳說規則裝備的事件描述 | `_skill_name` | `test_legendary_rule_gear_from_the_offer_can_be_narrated` |
| 前端：畫面、比較、請求 | `RunGearOffer`、`GearCardView`、`gearOffer.ts` | `client/src/run/gearOffer.test.ts`（13 個） |

## 驗證

- ruff check、ruff format --check、mypy（src＋tests，682 檔）、lint-imports（7 kept）通過。
- pytest：`-n 8 tests/engine tests/content tests/roguelite tests/api tests/narrative tests/skillgen tests/sim tests/test_architecture.py` 和 `-m "slow or not slow" tests/cli`（148 passed，含 CLI 快照與重播，**不需更新快照**）——結果：engine／content／roguelite／api／narrative／skillgen／sim／architecture 共 6863 passed、1 skipped。
- vitest 986 passed（含新增）、`pnpm build`、`typecheck` 通過。
- **內建瀏覽器實測**（埠 8027，自己啟動、已關閉）：
  - 開一輪（單手劍＋點燃＋倒地，種子 3），在戰鬥畫面按「結束回合」讓隊友打完第 1 場，回到一輪後 **出現「戰利品：裝備三選一（第 1 場後）」**：3 張卡分別是 優良戒指（戒指 1・最大 HP +5）、普通皮帽（頭・力量 +1）、優良圓盾（副手・圓盾特性、意志 +1），每張顯示「目前的戒指 1：空／預算分數 3.8（目前沒有裝備）」。選優良戒指 → 按鈕變「換上「優良戒指」」→ 確定後 **進入升級畫面（Lv 2）**，角色面板多「裝備」列，滑過戒指圖示出現共用浮動卡（戒指 1／優良戒指／最大 HP +5），點一下釘住、Esc 關閉（1024×768 視窗）。
  - 第 2 場後再出現三選一（腳／頭／手），選手部位 → 升級；第 3 場主角輸掉（隊友沒打完撤離，結束摘要正常）。
  - 營火背包用腳本做的存檔（`campdemo`，同一個伺服器讀檔）驗證：背包 2 件（優良皮甲、單手劍），每件附「目前：…」與預算分數比較、「主角的武器換成「單手劍」」連帶提示；按「換上這件（主手）」→ 武器欄變單手劍、背包換成稀有魔導劍。
  - 排版煙霧檢查（先 `localStorage.clear()`）：1600×900、800×600、1600×900＋`shortBottom` 三個情況 **全 PASS**（戰鬥畫面；三選一與背包不在這個工具的量測範圍，用上面的截圖與 `getBoundingClientRect` 看過）。
  - 注意：戰鬥是在 UI 按「結束回合」由隊友 AI 打贏的（沒有手動操作主角的技能）；一輪的三選一、升級、營火畫面都是真的在 UI 操作。
- 沒有跑 `scripts/check.py` 全量。

## 模擬（只量，不調數值）

`run auto`（`default_start` 開局，種子 0～39，腳本在 scratchpad 不進 repo；「改前」＝把三選一節點關掉）：改前 6/40 勝、平均打完 3.73 場；改後 5/40 勝、平均 3.62 場。樣本小，差異在雜訊內（AI 的預設開局本來勝率就低）；沒有調任何數值。

## 影響盤點（規格第 3 節）

| 項目 | 影響 |
|---|---|
| 一輪節點流程 | 戰後多 `gear_offer`；`apply_choice` 多兩種選擇；`_NODE_TEXT`、CLI、API、前端、存檔列表都補了 |
| `RunState`、存檔 | 見上；`trpg-run/6`、`/5` 可讀 |
| 開戰 `Loadout` | `run_loadout` 優先用 `RunState.equipment`；`hero.weapon` 隨主手武器更新（`hero_spawn`、`_card`、面板都吃 `run.hero.weapon`） |
| 穿戴驗證與全身上限 | 沿用 `loadout_problems`（沒改） |
| 詞條遞減、硬上限、常駐數值（3H-1）、資源上限（3H-2） | 沒改；裝備的屬性詞條照舊併進有效屬性（測試證明卡片＝實戰） |
| 營火畫面 | 多背包區 |
| `run auto`、模擬報表 | AI 會挑裝備（勝率變化見上）；`trpg sim` 沒改 |
| 測試模式（3-39）、裝備卡片與比較（3-32b） | `test_equipment` 照舊；測試模式戰後回滿的測試改成「≥ 一輪算的上限」（拿到裝備後可能更高）；物品卡多稀有度、基礎加成、預算分數 |
| 3I 新武器與副手 | 都可以出現在三選一（主手限同大類） |

## 待 PM 決定

1. **主手換武器**：同大類的武器直接把主角的武器換掉（技能只看大類，所以合法），但主角的屬性配點與技能是照原武器挑的，換成縮放屬性不同的武器可能降低輸出；AI 代打因此 **不換武器**。玩家端目前沒有「這會換掉你的武器」的二次確認，只在卡片寫「主角的武器換成「…」」。要不要加確認、或讓主手候選只出同一把武器，請決定。
2. **主角原本的基礎武器**換下後以 `base_<武器>` 物品進背包（沒有詞條），營火可換回；它的「預算分數」是 0，所以比較行常顯示「→ 0（−N）」，數字沒有意義（武器本身的基礎傷害不計入預算分數）。
3. **預算分數**＝詞條點數（含基礎加成）：武器基礎傷害、防具基礎防禦沒進分數（防具沒有基礎數值資料，3K-1 待決第 1 點）；傳說物品的分數用現有的點數表算（改變規則 40 點），可能遠高於同等級預算。AI 因此偏愛傳說物品。
4. **測試模式的 `test_equipment` 沒有遷移進 `equipment`**（見上，保守）；如果要統一成一個欄位，需要同時改 API 與舊存檔相容，請決定。
5. **背包沒有丟棄／出售**，一輪內不限數量（07 7.1）；卸下不換上（空著）也沒有。
6. **不選的候選直接丟棄**（不進背包），規格沒寫，採保守做法。
7. **候選部位不依「目前最弱」加權**（純均勻抽 3 種部位）；規格 7.1 的「預算分數最高、且部位目前最弱」只用在 AI。
8. 規格 3K-2 列裡舊寫的「50／35／13／2」請玩法 PM／開發 PM 在 `Phase3K計畫.md` 改成 40／25／20／13／2（第 1.1 節已是）。
9. 3K-1 待決仍然成立：小部位稀有／史詩大量下修（B22）、等級 9、10 優良主手產生不出來（一輪只到 Lv6，不影響）、逐條條件成立率分類、防具類型偏好。

