# Phase 3-11 報告｜暫時障礙與煙霧表面（玩法 #19）

## 1. 完成項目與 commit

- `create_obstacle` 新增可選參數 `duration`（1～10 個環境回合；省略＝永久）。物件狀態新增 `expires_in`，環境回合（緊接著火物件之後、表面倒數之前）每次 −1，歸零時移除並發出新事件 `object_expired`；**不算摧毀**（不發 `object_destroyed`、不漏油／爆炸、不掉落、不算擊殺）。到期前仍可被打破（打破後不會再到期一次）。
- 預算：新增 `budget_basis: obstacle`，點數 ＝ 基礎 3 × `obstacle_duration_permille[n−1]`（係數表放 `content/skill_budget.yaml`）；永久＝基礎（現狀）。
- 環境預告新增 `object_expired` 變化（「冰牆 (x, y) 將在本輪結束時消失」）；物件視圖帶 `expires_in`；前端物件淡化＋右上角剩餘回合徽章，最後一輪更淡，預告標「消」；戰鬥紀錄「冰牆 (x, y) 消失了」；技能說明「生成「冰牆」，3 回合後消失」。工坊的欄位由原語 `params` 推導，補上 `duration` 後自動出現。
- `smoke`（煙霧）表面：擋視線、隱蔽、無元素、持續 3 回合、預算 2 點（比照 `darkness`）；互動表新增 `wind_disperses_smoke`，聖光沒有對應規則（不驅散）。
- 新物件 `ice_wall`（擋移動、擋視線、可打破、`meltable`）、`thorn_wall`（擋移動、不擋視線、可打破、可燃）；新增物件標籤 `meltable` 與互動 `fire_melts_object`（火焰觸及即融化，走一般 `destroy_object`）。
- 示範技能（形狀依 PM 補充區分）：
  - 冰牆術：**直線 3 格**，冰牆 3 回合 ＋ 冰表面 3 回合，掛 `hero_stormcaller`。
  - 荊棘牆術：**環形半徑 1**（環形與 `create_obstacle` 相容），荊棘叢 2 回合 ＋ 毒表面 2 回合，掛 `hero_stormcaller`。
  - 煙霧彈：方陣 3×3、射程 5，`smoke` 表面 5 回合，掛 `hero_archer`。既有煙幕箭（`darkness`）未改。
- Commits（分支 `worktree-agent-a51ce5b526b56fd0d`）：
  1. `feat: temporary obstacles (create_obstacle duration), smoke surface and demo skills`
  2. `feat: show expiring objects in telegraph and map (client, openapi)`
  3. `docs: Phase 3-11 screenshots; update skill counts in cli tests`
  4. 本報告

## 2. 驗收條件逐條

| # | 結果 | 證據 |
|---|---|---|
| 1 | 通過 | `tests/engine/test_temporary_obstacles.py`：`test_temporary_obstacle_expires_after_its_duration_without_being_destroyed`、`test_expiry_does_not_trigger_break_effects`（油桶到期不漏油，對照直接摧毀會）、`test_temporary_obstacle_can_still_be_broken_before_expiry`、`test_expiry_is_deterministic_for_replay` |
| 2 | 通過（有一點說明，見待決 1） | `test_permanent_obstacle_never_expires`；既有 `test_create_obstacle_fills_only_empty_tiles` 等未改。兩張地圖（oil_depot seed 7、narrow_halls seed 3，`--allies hero_fighter,hero_mage`）改前後 `--log-json` 的 `actions`、`events`、`seed`、`orders` 逐字一致；只有內嵌的 `setup`／`final_state` 多了新內容與 `expires_in: null` |
| 3 | 通過 | `test_obstacle_budget_scales_with_duration_and_permanent_is_unchanged`、`test_demo_skills_pass_budget_validation`；三個示範技能都被裝備（`tests/content/test_coverage.py` 通過）。預算表見第 7 節 |
| 4 | 通過 | `test_smoke_blocks_sight_conceals_and_has_no_element`、`test_wind_disperses_smoke_but_holy_does_not`（並對照聖光會驅散 darkness）、`test_smoke_bomb_skill_creates_smoke_that_expires` |
| 5 | 通過 | vitest：`telegraph.test.ts`（object_expired 標記與文字）、`drawModel.test.ts`（expiresIn）；`test_telegraph_announces_the_wall_will_vanish`；截圖 `docs/phases/img/3-11-wall-created.png`（牆帶「3」徽章）、`3-11-telegraph-vanish.png`（預告「冰牆 將在本輪結束時消失」、牆標「消」）、`3-11-wall-gone.png`（牆消失、紀錄「冰牆 (1, 3) 消失了」、冰變水） |
| 6 | 通過 | `uv run python scripts/check.py` 全過（含 pytest、vitest、tsc）；`corepack pnpm -C client build` 成功 |

到期時機：與表面持續時間相同，即每輪結束的環境回合；`duration: n` 在施放當輪的環境回合算第 1 次，所以第 n 個環境回合結束時消失（與表面一致）。

## 3. 複雜度 noqa

沒有新增或移除。`cli/render.py` 的 `render_telegraph` 一度超過 PLR0912，改為把 `object_expired` 併入既有「沿用網頁預告文字」的種類清單，未加 noqa。

## 4. 修改既有測試期望值

| 檔案 | 修改 | 原因 |
|---|---|---|
| `tests/shared/test_types.py` | `Surface` 列舉清單多 `smoke` | 新增表面 |
| `tests/skillgen/test_budget.py` | 表面預算點數多 `smoke: 2` | 新增表面 |
| `tests/cli/test_budget_cli.py` | 技能數 149 → 152（三處字串） | 新增 3 個手寫技能 |
| `tests/cli/snapshots/cli_output_hashes.json` | `skills_list`、`skills_show_all` 兩個雜湊 | 技能清單多 3 個；戰鬥類輸出雜湊未變 |

## 5. 待 PM 決定

1. **舊紀錄無法重播**：`--log-json` 內嵌規則集，新增 `Surface.smoke` 後，3-11 之前產生的紀錄重播會報「缺少表面：smoke」（pydantic 錯誤）。新紀錄的動作與事件與舊的一致。是否要升 `LOG_FORMAT` 讓錯誤訊息清楚，或接受（舊紀錄多半是一次性的）？我沒有升。
2. **示範技能為了過預算下限（70%）加了第二個效果**：單純的暫時牆分數太低（直線 3 格、3 回合只有約 2.5 點，下限約 5.5）。冰牆附帶冰表面、荊棘牆附帶毒表面；代價是表面也會鋪在有單位的格子（可能讓隊友滑倒／中毒）。若想要「純牆」，需調整係數表或形狀倍率。
3. **煙霧彈持續 5 回合**（預設表面持續 3 回合）：3 回合的 smoke 方陣只有約 49% 預算比，過不了下限；5 回合與煙幕箭同分（81%）。煙霧彈因此與煙幕箭幾乎同質（差在無元素、可被風吹散、聖光不驅散）。
4. **煙霧彈掛在 `hero_archer`（遠程武器技）**，因為所有 sim build 的主動欄位都滿了，新增 build 會動到多個測試與矩陣；冰牆術與荊棘牆術掛 `hero_stormcaller`（4 → 6 個技能）。這兩個英雄範本的戰鬥結果在兩張測試地圖未受影響（見驗收 2），但 AI 是否會善用障礙技能未驗證。
5. **係數表是初值**：`obstacle_duration_permille` = 400、500、600、700、750、800、850、900、950、1000（1～10 回合），未經模擬。
6. **荊棘叢到期不會被火「提前」處理**：可燃，會被火點燃並燒毀（走既有 burning）；若在燃燒中到期，先燒毀再不重複到期。冰牆被火觸及直接融化（新標籤 `meltable`），冰牆不可燃。
7. **預覽（`preview`）未列 `object_expired`**：預覽只涵蓋玩家動作本身的結果，環境回合的消失由環境預告負責。
8. **隨機組合器（random_composer）不會產生帶 `duration` 的障礙，也不會挑 `smoke`**（避免改變既有同種子技能的產生結果）；若要讓隨機技能也能長出暫時牆與煙霧，需另案。

## 6. 代表性輸出節錄

戰鬥紀錄（冰牆術施放後，第 1 輪至第 3 輪結束）：

```
(1, 3) 出現了冰牆 … (3, 3) 出現了冰牆；(1, 3) 出現了冰 …
環境預告（第 3 輪結束時）：冰牆 (1, 3) 將在本輪結束時消失；表面變化 (1, 3)：冰 → 水
環境回合：冰牆 (1, 3) 消失了；(1, 3) 的冰變成了水
```

## 7. 預算表

`create_obstacle` 基礎 3 點，形狀倍率另計（十字 1.8、直線 3 格 1.4）。

| 持續（回合） | 係數 | 基礎點數（未乘形狀） |
|---|---|---|
| 永久 | 1000‰ | 3.00 |
| 1 | 400‰ | 1.20 |
| 2 | 500‰ | 1.50 |
| 3 | 600‰ | 1.80 |
| 4 | 700‰ | 2.10 |
| 5 | 750‰ | 2.25 |
| 6 | 800‰ | 2.40 |
| 7 | 850‰ | 2.55 |
| 8 | 900‰ | 2.70 |
| 9 | 950‰ | 2.85 |
| 10 | 1000‰ | 3.00 |

示範技能（合格區間 70%–100%）：

| 技能 | total | 可用預算 | 比例 |
|---|---|---|---|
| 石牆術（永久，未改） | 5.40 | 7.17 | 75.3% |
| 冰牆術 | 6.72 | 7.84 | 85.7% |
| 荊棘牆術 | 6.30 | 7.80 | 80.7% |
| 煙霧彈 | 6.67 | 8.19 | 81.4% |
| 煙幕箭（對照，未改） | 6.67 | 8.19 | 81.4% |
