# Phase 6E-3d 報告：北坡懸賞陣容＋第三方位置

規格：`docs/phases/Phase6計畫.md` 第 1 節 6E-3d 列；設計 21.10 第 26 條「細節」（玩法 PM e7ed420a）。
開工時 `git merge main`：無衝突，含 6E-3c（`docs/phases/Phase6E-3c報告.md`）、e7ed420a 與 1289bdbb。
**沒有改引擎**、沒有新增相依、距離（2、3、1）不變、沒有跑模擬（規格寫「不重量」）。

## 1. 北坡懸賞陣容（只改內容）

- `content/world/encounters/cloud_ridge.yaml` 新增 `north_wolf_king_pack`（北坡狼王與狼群）：`[mist_wolf, mist_wolf, mist_wolf]`。
  懸賞的精英（狂暴的霧狼）照舊由懸賞排在最前，所以懸賞陣容＝**狼王＋3 隻霧狼（4 隻）**，即 6E-3c 之前北坡的陣容。
- `content/world/season.yaml` 的 `north_wolf_king` 由 `group: north_slope_pack` 改成 `group: north_wolf_king_pack`。
- 日常駐守 `north_slope_pack` 維持 6E-3c 的兩隻霧狼＋地點固定精英狼王（3 隻）；實地地圖 `north_slope.yaml` 的狼窩 spawn 照舊指 `north_slope_pack`。
- **不需要加欄位**：「懸賞期間每天第一場用指定陣容」早已由懸賞的 `group` 欄位表達（`encounters._bounty_lineup` 用
  `bounty.group`，就地開打的看得見敵人也走 `roll_lineup` → 懸賞優先），內容驗證（`world_season._bounty_problems`：
  陣容存在、沒有第三方、加精英不超過 4 名）照舊適用，`trpg content check` 通過。
  懸賞陣容不放進地點的 `groups`（不會被一般遭遇抽到），和 `summit_patrol` 一樣是「定義了、由別處引用」的陣容。

## 2. 第三方在敵方那一側

`battlefield._third_zone`：候選格多一條件——**離敵方帶頭的曼哈頓距離要比離主角近（嚴格小於；相等不行）**。
「主角」「敵方帶頭的」用切出來的起點（`_zones` 的 `anchors`），即我方、敵方起始區的第一格。其他條件不變：走得到、不在雙方
起始區、離我方起始區每一格至少隔 2 格（6E-3c）、照（離敵方起始區最近, y, x）取。排不出來＝這個距離放不下，照現行順序試
另一個距離 → 隔 1 格 → 退回模板（`zones`）。

- 保守解讀：「比離主角近」用嚴格小於（等距的格子視為不在敵方那側，不排）。
- `WORLD_RULES_VERSION` 5 → 6（`save.py` 註解補「6＝6E-3d」）。

## 3. 測試

- `tests/world/test_season_board.py`
  - 新增 `test_north_slope_bounty_and_daily_lineups`：懸賞期間第一場＝`north_wolf_king_pack`、成員（狂暴霧狼, 霧狼×3）；
    打過（輸了也算）之後同一天的第二場＝日常 `north_slope_pack`、成員（狂暴霧狼, 霧狼×2）、`bounty is None`。
  - 測試用的 `_bounty_lineup` 夾具改成新陣容（4 隻）。
  - 既有 `test_first_bounty_encounter_per_day` 照舊驗證「每天第一場是懸賞、6 點換日重算」。
- `tests/world/test_encounters.py::test_north_slope_has_the_wolf_king`（日常 3 隻）不用改，照舊通過。
- `tests/world/test_battlefield.py`
  - `test_third_party_fallback_order` 改表（8 種，走廊多一個「往北岔路」參數），每種都檢查第三方離我方 ≥ 3、且每格離敵方帶頭 < 離主角：
    - 西 6 東 3：隔 3，第三方 (19, 15)（敵我中間、靠敵方）；
    - 西 6 東 3 北 3、2 人：隔 3，(20, 12)、(19, 15)；
    - 西 5 東 4、1 人：隔 3、2 排不出 → 隔 1，(24, 15)（敵方東邊）；
    - 西 5 東 3 北 3、2 人：隔 3 排不出 → 隔 2，(20, 12)、(22, 15)；
    - **西 8 東 5、2 人：6E-3c 在隔 1 格排出 (24, 15)、(13, 15)，(13, 15) 在我方背後 → 6E-3d 排不出 → 退回模板**；
    - 西 6 東 5／西 7 東 3／西 6 東 3（2 人）：照舊退回模板。
  - `test_third_party_keeps_two_cells_from_allies`（空曠地圖兩種先手）加檢查第三方在敵方那側。
  - **正式內容重新驗證**（`test_every_content_spawn_cuts`，加檢查第三方在敵方那側）：267 個接觸點 × 我方先手／沒有先手＝534 次，
    **退回模板 0 個**；我方先手 267 次隔 2、沒有先手 266 次隔 3、1 次隔 2（`elixir_cave` 第 2 隊，同 6E-3c）。
    **三方混戰 56 次，第三方起始區全部在敵方那側**、全部離我方至少隔 2 格。
  - 與 6E-3c 比較（scratchpad 腳本 `p3d/content_diff.py`，不進 repo）：56 次裡有 **5 次** 6E-3c 的第三方有格子不在敵方那側
    （離主角 ≤ 離敵方帶頭），6E-3d 改排到敵方那側、仍切得出、距離不變，都是「沒有先手」：
    `crane_cliff` 第 1 隊 (6, 2)／第 2 隊 (5, 10)、`crystal_rift` 第 1 隊 (12, 4)／第 2 隊 (12, 13)、`rain_terraces` 第 1 隊 (16, 2)。

## 4. 驗證

- `ruff check`、`ruff format --check`、`mypy src`（512 檔無問題）、`lint-imports`（13 kept）、`uv run trpg content check` 通過。
- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content -n 8 -x`：4211 passed、1 skipped（兩項都改完後）；只改內容時先跑過 season_board／encounters／content 2563 passed。
- swamp 種子 7 重播通過（88 個動作、313 個事件）。

## 5. 待 PM 決定

1. 「第三方離敵方帶頭比離主角近」採**嚴格小於**（等距不排）。若要允許等距，只改 `_third_zone` 的 `>=` 一處。
2. 懸賞陣容 4 隻（狼王＋3）照規格不重量；6E-3c 量過的 6E-3c 規則下「狼王＋3 狼」我方先手 66.5%、敵方／無先手 75.5%
   （低於 75% 的門檻是日常駐守的，懸賞是否另有門檻留給玩法 PM）。
3. 6E-3c 待決 2（第三方排到我方後面）由本段解決；6E-3c 待決 3（`enemy_facing` 寫了不用）仍在。

## 6. Commit

- `050791e3` content: north wolf king bounty uses its own four-wolf pack
- `692de96d` feat: keep the third party on the enemy side in field cuts
- 本報告（下一個 commit）
