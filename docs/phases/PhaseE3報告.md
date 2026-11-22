# Phase E3 報告｜新地形規則種類（霜行、攀岩、表面傷害免疫）

> 規格 `docs/phases/PhaseE3計畫.md`；規則以 `docs/design/08-裝備.md` 8.29「E3」與「E2」補充（#175）為準，加上開發 PM 2026-11-22 的三點回覆（見第 5 節第 1～3 項）。基準 main `64ebd29d0`（含 E1、E2、E5、KD-1）。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 共用規則表加 3 種（`trail_surface`、`flat_climb`、`surface_damage_immunity`；參數 `duration`） | `34e953d9e` |
| 2 霜行（留冰、誰的冰、到期消失、自己不滑；`LOG_FORMAT` `/138`） | `afff23f9d` |
| 3 攀岩（`unit_step_cost`） | `015f12a1a` |
| 4 表面傷害免疫（回合開始傷害；AI `_harmful`） | `5d8ef69ca` |
| 5 地形規則只能留表面、不能施加狀態（content 檢查） | `eb3bf1719` |
| 6 數值型同參數取較強（`classify_sources`；角色面板「被蓋過」） | `a1cc13c14` |
| 6 補：主角 HUD 的種族那行也加註 | `60af06d82` |
| 7 收尾（新種類 0 點、沒有內容在用；上手筆記） | `df6aa1b74` |
| 截圖 | `99d0e4b8f` |
| 合併 main（WL-2、TS-1 等） | `4390eab72` |
| 全量後修正：版號斷言改從 `LOG_FORMAT` 推 | `bc2f6c289` |
| 報告 | 最後一個 commit |

## 2. 各項做法

1. **共用規則表**（`content/unit_rules.py`）
   - `UNIT_RULE_SPECS` 加 `trail_surface`（`surfaces`＋`duration`）、`flat_climb`（`amount`）、`surface_damage_immunity`（`surfaces`）。
   - 新參數欄位 `duration`（`RacePassive`、`TerrainAffix` 都加，預設 `None`、1～3）；`trail_surface` 的 `surfaces` 只能一種、不能是 `none`。
   - 鍵：`surface_damage_immunity` 照表面；`trail_surface`、`flat_climb` 只有一個鍵（同一個人只有一條生效）。
2. **霜行**（新模組 `engine/trail.py`）
   - 掛點：步行 `battle._do_move`、衝刺 `Cast._dash_walk`、直線衝撞 `displacement._charge_walk`（PM 回覆：`mode="dash"` 都算）。每一步 `MoveUnitEffect` 之後、反應之前，在離開的那一格放 `create_surface`（`react=False`、`cause="trail"`），再設 `Tile.surface_trail = 單位 ID`。
   - 不留的情況：那格已有表面、不能有表面、有其他單位站著（走過隊友）、單位已倒下、會飛的單位。跳躍、攀跳、瞬步、傳送、被推拉、滑行都不經過這三個掛點。
   - `Tile.surface_trail`（`None` 不輸出）。`effects/world.set_surface` 的 `replace` 多一行 `surface_trail=None`（PM 回覆同意，world.py 只動這一行），表面被任何效果換掉時標記就清掉。
   - 到期：`environment._tick_surfaces` 看到 `surface_trail` 時直接變 `none`，不變水。
   - 不滑倒：`ice_slide.slide_check_due` 看 `own_trail`；新函式 `run_start`：從自己的冰（沒擲過）走到別人的冰，算新的一段，要擲。被推進、表面出現在腳下：`effects/surface_entry._own_trail`。
   - 預覽：`path_preview._slip_runs` 對自己的冰標 `immune`（畫面「冰 N 格・不會滑倒」）。AI 的滑倒估計 `path_slide_risks` 走 `slide_check_due`，所以別人會避開、持有者不避。
   - 戰鬥紀錄：`/137` → `/138`，照格式變更文件 1.1、1.3 做（文件加一條、`runner.py` 版號與那一行）。測試裡寫死版號的地方（8 個 `"trpg-battle-log/137"`、4 個 `endswith("/137")`）改成從 `LOG_FORMAT` 推：CLI 測試比 `data["format"] == LOG_FORMAT`、紀錄文字比 `LOG_FORMAT in text`、四個重播測試改成 `startswith("trpg-battle-log/")`。`test_runs_api`、`test_save` 裡的 `"trpg-battle-log/1"` 是故意放的舊版本，沒動。
3. **攀岩**：`movement.unit_step_cost` 的平地層數取 `max(形態 form_flat_height, race.flat_climb_height)`。一步最多上 1 層不變，所以攀跳照舊。`step_cost`（不看單位）沒改。走路預覽、AI 找路都經過 `unit_step_cost`。
4. **表面傷害免疫**：`turns._surface_turn_start` 的 `cause="surface"` 傷害看 `race.surface_damage_immune`；`only_tag` 的判斷順序照舊；燃燒、狀態照舊。AI `position._harmful` 的回合開始傷害那段也看這條免疫（開關 `harmful_sees_immunity` 關掉時照舊）。
5. **不能施加狀態**：`unit_rule_status_problem`（`RacePassive`、`TerrainAffix` 的 before 驗證）：填了 `status`／`statuses`／`apply_status`／`status_id`，或規則名帶 `status`，報「地形規則只能留下表面，不能施加狀態（「經過時對相鄰敵人施加狀態」是改寫規則，全身同時只能有一個）」。
6. **取較強**（`engine/rules/unit_rules.py`）
   - `winners`：每個（種類, 鍵）依來源順序走，較強而且其他參數相同時取代；一樣強時前面的生效（種族先）。`classify_sources(sources, strength)`、`first_source` 用同一套。
   - 強弱：`raw_strength`（`amount`／`permille`／`radius`／`duration`）；戰鬥與顯示用 `effective_strength`：裝備的移動加成先截到 `gear_move_room` 再比（PM 回覆第 3 點）。
   - 「其他參數相同」：`trail_surface` 的表面不同時不比強弱，排在前面的生效。
   - `reveal_radius` 改用 `first_source`（數值型，取較強）。
   - 顯示：`RaceView.passive_overridden_zh`（`race_override_zh`）：完全蓋過「被腳的「…」蓋過」、部分「水的部分被身體的「…」蓋過」。前端 `battle/race.ts` 的 `overrideNote`、`raceDetailText`；角色面板「▸ 詳細」的種族列、主角 HUD 的種族那行、被動說明都加註。OpenAPI、`schema.d.ts` 重產。
7. **收尾**：`classify.py --check` 0；新種類 `affix_points` 是 0（`terrain` 沒有 `category_points`），`affixes.yaml`、`races.yaml` 都沒人用（測試鎖住）。上手筆記 `docs/dev/上手-引擎戰鬥結算.md` 第 60 條、測試表一列。

## 3. 測試

| 檔 | 內容 |
|---|---|
| `tests/content/test_terrain_rules_e3.py`（18） | 三種的參數檢查（種族、裝備）、`duration` 只給 trail、表面只能一種、施加狀態的中文錯誤（4 種欄位、2 種規則名、經 `AffixTable`）、0 點、沒內容在用 |
| `tests/engine/test_trail_e3.py`（22） | 起點與途經留冰、停點不留；沒規則不留；事件順序（每步 `unit_moved` 後緊接離開那格的 `surface_changed`，`cause=trail`、`remaining=1`）；`surface_trail` 空值不輸出、JSON 往返；已有表面不動、不互動；隊友格不留；到期消失（對照一般冰變水）；持有者不滑、敵人會滑、別人的冰持有者照滑、自己的冰接別人的冰要擲；被推進自己的冰不擲；表面被換掉時標記清掉；衝刺、直線衝撞會留；被推、攀跳不留；預覽（持有者 `immune`、別人有滑倒風險）；AI 滑倒估計；三種規則一起穿的整場戰鬥同種子兩次與重播相同 |
| `tests/engine/test_climb_e3.py`（4） | 上 1 層 1 點、下坡照舊；2 層仍要攀跳；3 點走 3 個台階；預覽與 `path_map` |
| `tests/engine/test_surface_immunity_e3.py`（5） | 查詢；擋回合開始的毒表面傷害；中毒狀態的傷害照常；AI `_harmful` 看免疫、看不見的單位照樣避開、開關關時照舊；`position_value` 不扣 hazard |
| `tests/engine/test_stronger_rule_e3.py`（8） | 裝備較強蓋過共用的鍵（部分、全部）與面板文字；一樣強時種族生效；截上限後比（+2 額度 0 → 種族；額度 1 → 平手種族）；兩件裝備強者勝、平手前面的；trail 同表面 duration 長者勝、不同表面前面的；`radius` 取較強；沒裝備時沒有加註 |
| `client/src/battle/race.test.ts` | 加註的三種文字 |

## 4. 驗收

預算與 census 的基準是 `64ebd29d0`，78 場的基準是合併時的 main `6f9069252`（都用 `git archive` 的 `src`、`content`、`config`）。腳本在暫存區。

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`） | `cmp` 0（逐位相同） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0` |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（後端 config 28、text 0；沒歸類 0） |
| ruff、format、mypy、lint-imports | 0 |
| tsc、vitest（`src/battle/race.test.ts`、`src/ui`）、build | 0 |
| `uv run python scripts/check.py --all`（第 1 次，合併 main 後） | 結束碼 1：4 個重播測試寫死 `endswith("/137")`。修正 `bc2f6c289` |
| `uv run python scripts/check.py --all`（第 2 次） | 結束碼 0：pytest 18528 passed、8 skipped；vitest 4907；ruff、format、mypy、lint-imports、client typecheck、situation coverage 通過；已寫通過戳記 |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 結束碼 0（995 passed）；CLI 快照、parity 都沒變，不用重產 |
| 前端 build（`corepack pnpm -C client build`，合併後） | 結束碼 0 |
| 78 場（`compare78.py`，a 段那組；只多去掉 `format`；基準改用合併時的 main `6f9069252`） | `battles=78 events=26741 different=0`；內嵌規則包只多 10 個種族被動的 `duration`（missing → None） |

## 5. 截圖（`docs/art/shots/e3/`，交美術 PM）

實機（`trpg serve`＋暫存的內容複本：三條測試詞條；治療英雄改鱗族；地圖懸崖前哨）。jpg 品質 80，都在 300 KB 以下。

| 檔 | 內容 |
|---|---|
| `e3_frost_trail_1600x900.jpg`、`e3_frost_trail_800x600.jpg` | 坦克（沒有種族）穿「霜行攀岩靴」走了 3 步，起點與途經 3 格結冰、停點沒有；滑過回頭的路，預覽牌「冰 2 格・不會滑倒」；右上環境預告「表面變化 (x,y)：冰 → 無」（到期直接消失） |
| `e3_climb_preview_1600x900.jpg`、`e3_climb_preview_800x600.jpg` | 移動 5，滑過台階頂的 ▲2 格：路徑上 ▲1、▲2 兩階當平地，可到達（沒有攀岩要 7 點，走不到） |
| `e3_race_overridden_1600x900.jpg`、`e3_race_overridden_800x600.jpg` | 鱗族（水與冰 +1）穿「站在水上，移動 +2」：HUD 種族那行與角色面板「▸ 詳細」的種族列加註「水的部分被身體的「站在水上，移動 +2」蓋過」（800 寬只拍到 HUD 那行） |

## 6. 待 PM 決定

1. **取較強比的是截上限後的值**（PM 回覆第 3 點，已照做）：裝備截完比種族弱或一樣強 → 種族生效、裝備標灰；比較強 → 裝備生效、種族註明被蓋過。兩件裝備同一套比法，一樣強時前面那件生效。上限是看裝備數值詞條已給的移動（`gear_move_room`），比的時候每條各自用整個剩餘額度；兩條裝備移動規則（天氣、表面）同時生效時，實際加值照舊合起來受上限。待玩法 PM 補進 8.29。
2. **`trail_surface` 的重複判法**（PM 回覆，已照做）：一個人只有一條生效；同一種表面時 `duration` 長的較強，表面不同時排在前面的生效。待玩法 PM 補進 8.29。
3. **衝刺＝所有 `mode="dash"`**（PM 回覆）：衝刺技能與直線衝撞；攀跳不算。
4. **保守做法**：會飛的單位不留冰；單位在那一步倒下就不留；有任何其他單位（不只隊友）站著的格子不留；可以留的表面不限冰（例如火），但一件只能一種。
5. **走路預覽不預告「這次會留下的冰」**：只顯示地圖上已有的冰，以及持有者踩自己的冰「不會滑倒」。要不要在路徑上畫出將留冰的格子，請 PM 定。
6. **表面的名詞說明**（`narrative/tile_info.surface_rules`）是依表面種類的靜態文字，冰寫「由技能產生時持續 3 回合，之後變成水」，不分是不是霜行留下的；環境預告會正確寫「冰 → 無」。要不要為霜行的冰另寫說明，請 PM 定。
7. **吹送、擴散把霜行的冰搬走時**：新格是一般的冰（標記不跟著走，到期變水）。
8. **AI 不會主動用霜行鋪冰**（草案做法，記待查）。
9. **`LOG_FORMAT` `/138`**：`Tile` 多了 `surface_trail`（空值不輸出），依格式變更文件 1.1「戰鬥狀態欄位增減」升版；`/137` 的紀錄無法重播。
10. **`flat_climb` 的 `amount`**：沿用共用欄位 1～2；2 層因為一步最多上 1 層，目前和 1 一樣。
11. **新種類的預算點數**：0，產生器不產，等 E6-a。

## 7. 數值疑慮

沒有改數值，不跑模擬。三種規則現有內容沒人用。

## 8. 開發 PM 裁定（2026-11-22）

**驗收通過**，合併為 `db25a8f1b`。`check.py --all` 第 2 次 0（18528 passed、vitest 4907）、slow parity／cli 0、build 0；442 招逐位相同、census 204 格 different=0、78 場 26741 事件 different=0（去掉 format）。

- 第 1、2、3 點：照我的回覆做，接受。轉玩法 PM 補進 8.29（取較強比截上限後的值；`trail_surface` 一人一條、同表面比 `duration`、不同表面排前面的生效；衝刺＝`mode="dash"`）。
- 第 4、7、9、10、11 點：接受。
- 第 5 點（預覽要不要畫出將留冰的格子）、第 6 點（霜行冰的名詞說明寫「之後變成水」不對）：記佇列 (t)，用字請玩法 PM 定，併進下一個碰到路徑預覽／表面說明的段。
- 第 8 點（AI 不主動鋪冰）：轉玩法 PM 記平衡待查。
- 守則 14：`view.py` 新增 `RaceView.passive_overridden_zh`，會寫出該單位裝備的地形規則名稱，敵方單位也一樣。單人階段不擋；多人階段排「每個視圖帶觀看者」時，要一併確認敵方裝備是否該被看見。
