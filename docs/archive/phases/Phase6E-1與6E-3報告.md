# Phase 6E-1 與 6E-3 報告：霧牆（#122）與開打距離（#124）

規格：`docs/phases/Phase6計畫.md` 第 1 節 6E-1、6E-3 列；設計 21.4、21.10 第 18、26 條。
開工時 `git merge main` 已是最新（含 6D-R1）。沒有改引擎、沒有新增相依；避開 6E-2／6D-R2 的檔案
（`world/common.py`、`world/encounters.py`、`world/atlas.py`、`absence_view`、`atlasModel`、`FieldSpot`
的欄位、戰鬥畫面檔）。

## 1. 6E-1 霧牆

- **內容**：出口新增選填的 `gate`（`trpg.content.fields.ExitGate`：`quest`、`step`、`open_flag`、`spot`、
  `blocked_zh`、`hint_zh`、`open_zh`）。源晶裂痕的 `to_cloud_summit` 寫上
  `main_mist_rift`／`rift_battle`／`mist_rift_done`／`rift_mist_wall`，提示文字「霧太濃，還過不去」＋
  「主線：先查清源晶裂痕」、打開後的說明卡文字都在 `crystal_rift.yaml`。單檔驗證：`gate.spot` 必須是這張圖的
  情境物件。為了不和 6D-R2 改 `FieldSpot` 撞在一起，設定放在出口上、不放在情境物件上。
- **規則**（`trpg.world.field.exit_open`／`closed_exit`）：角色有 `open_flag`（`story_flags`）、或角色
  **自己的** `quest_state(quest)` 已完成、或 `steps_done` 超過 `step` 的索引 → 開著；其他（沒接、停在第
  1～3 步）關著。只看 `char`，影子、傭兵、別的角色、世界旗標都不算。
- **走路**（`_walk_path`）：下一格是關著的出口就停在前一格（那一格不算走過、不換圖、不 `travel`、
  不擲骰、不耗亂數），`walk` 多回一個 `ExitBlockedEvent`（`kind: exit_blocked`，`text_zh`＝提示）。
  同一段路先碰到敵人時照開打，不回這個事件。
- **說明卡**：`object_status` 的 `note_zh` 依狀態換：關著＝原文＋提示；開著＝`open_zh`。
- **API／前端**：`FieldExitView.blocked_zh`（關著時的提示；OpenAPI 與 `schema.d.ts` 已重產）。事件句子
  （`field_line`）就是提示文字，照舊進日誌與浮動提示；`WorldScreen` 把等於 `blocked_zh` 的句子改用
  警告框，滑鼠移到出口時顯示「往 雲頂觀（霧太濃…）」（`fieldModel.hoverText`）。
- 只擋走路：有實地地圖的地點本來就不能 `travel`，雲頂觀沒有傳送石，所以沒有別的入口。

## 2. 6E-3 開打距離

- **規則數值**（`content/world/rules.yaml` 的 `field:`）：`gap_ally_first: 2`、`gap_other: 3`、
  `gap_fallback: 1`；`FieldRules.gaps(ally_first)` 給試的順序（我方先手 2→3→1，其他 3→2→1）。
- **接觸點的前一格**：`FieldContact.came_from`（選填，舊存檔沒有）；`walk_watch` 開打時記下走到接觸點的前一格
  （只走一格＝走路前的位置）。
- **擺法**（`trpg.world.battlefield.cut_battlefield`，新增 `came_from` 參數）：每個距離 N：
  1. 敵方帶頭的不動；主角從接觸點沿 `came_from` 的方向往回退，直到離敵方帶頭的曼哈頓距離＝N＋1
     （遇到走不到、爬不上去的格子就停）。
  2. 退不了（沒有 `came_from`、撞牆、本來就比 N＋1 遠）→ 在接觸點走得到、距離剛好 N＋1 的格子裡挑最靠近
     接觸點的（同距離照 y、x）。
  3. 以雙方帶頭的中點切 12×12；起始區照 6C-2 的排序，另外**雙方起始區任兩格都至少 N＋1**（部署階段怎麼挑
     都不會更近）。
  4. 放不下就換下一個距離；三個都不行回 `zones`（文字改成「站位放不下（隔 3、2、1 格都試過）」），
     最後一次是 `check_map` 沒過時回 `check_map`。
- `BattlefieldCut.gap`：實際用了隔幾格（`BattleStartedEvent.field_cut` 帶著）。
- 打贏照舊回到接觸點（`contact.x/y`），撤退照舊回入口。
- `WORLD_RULES_VERSION` 1 → 2（霧牆與開打距離都會讓同一份日誌重播出不同結果；`docs/開發PM交接.md` 6.6）。

## 3. 測試

- `tests/world/test_mist_wall.py`（新，13 個）：還沒接／第 0 步／第 3 步擋住、第 4 步完成與整個任務完成放行、
  只有 `mist_rift_done` 的舊角色放行；擋住時不移動、不 `travel`、補給與亂數計數不變；長路徑停在出口前一格；
  別人有進度、世界旗標有 `mist_rift_done` 都不算；說明卡兩種文字；其他出口不受影響；兩段被擋的走路重播一致；
  API 的 `blocked_zh` 與事件句子。
- `tests/world/test_battlefield.py`：
  - `test_opening_distance`（11 種）：我方先手隔 2、敵方先手與沒有先手隔 3、東西南北、視野內 4 格不用退、
    距離過遠時找最近的符合格、同一格接觸、沒有 `came_from`、靠邊；並檢查切的中心、起始區最近兩格＝N＋1。
  - `test_blocked_retreat_takes_nearest_fitting_cell`：往回退撞牆。
  - `test_fallback_distance_order`（7 種）：走廊地圖驗證 3→2→1→退回模板、我方先手 2→3→1→退回模板。
  - `test_gap_order_comes_from_rules`、原本的確定性測試、`test_prepare_battle_uses_the_cut`（渡口石階從背後
    碰到：主角從 (5, 6) 退到 (3, 6)、隔 2 格、`came_from` (4, 6)）。
  - **正式內容重新驗證**（`test_every_content_spawn_cuts`，改用不換凍結地圖的正式內容）：每一隊每個轉折點
    四方向相鄰、筆直走過來的接觸點共 267 個，我方先手與沒有先手各切一次（534 次）：全部照規定距離
    （我方先手 267 次隔 2、沒有先手 267 次隔 3），**退回模板 0 個**。
- `tests/world/test_field_ctx_replay.py`：凍結雜湊比較前拿掉 6E-3 新增的 `came_from`（和 6C-R2 遮掉
  `lineup_seed` 同一個做法），雜湊不變。

驗證（交件前）：`ruff check`、`ruff format --check`、`mypy src`、`lint-imports`（13 kept）、
`uv run trpg content check` 通過；`pytest tests/world tests/api tests/content -n 8`：4178 passed、1 skipped；
swamp 種子 7 重播通過（88 個動作、313 個事件）。前端：worktree 沒有 `node_modules`，**沒有跑 tsc／vitest**
（改動只有 `fieldModel.ts` 的 `PortalHit` 多一個欄位、`hoverText` 一行、`WorldScreen.tsx` 浮動提示分兩組）。

## 4. 模擬：新舊站位勝率（守則 8）

腳本：scratchpad `sim_gap.py`（不進 repo）。舊＝主角站在接觸點（規則 gap 全設 0，等同 6C-2）；新＝本段規則。
隊伍：支援主角（`build_support`）＋鐵壁、回春兩名傭兵；接觸點＝每隊駐守點（巡邏起點）的相鄰格、筆直走過來；
每個接觸點 × 先手（我方先手／沒有先手）× 12 個種子（`battle_seed`＝`lineup_seed`＝0～11），新舊各打一場，
效用 AI 代打雙方。等級：渡口石階 1、竹林小徑 2、北坡獵場 3（照建議等級的下限附近）。

| 地圖／隊伍 | 先手 | 場數 | 舊勝率 | 新勝率 | 舊平均輪數 | 新平均輪數 |
|---|---|---|---|---|---|---|
| 渡口石階／bandit_raiders（新手固定戰） | 我方先手 | 48 | 92% | 83% | 8.0 | 8.1 |
| 渡口石階／bandit_raiders（新手固定戰） | 敵方／無先手 | 48 | 94% | 81% | 8.7 | 8.0 |
| 渡口石階／bandit_shield_line（巡邏） | 我方先手 | 48 | 100% | 100% | 6.6 | 7.0 |
| 渡口石階／bandit_shield_line（巡邏） | 敵方／無先手 | 48 | 100% | 100% | 7.2 | 6.9 |
| 竹林小徑／bandit_wolf_handler | 我方先手 | 24 | 100% | 100% | 4.4 | 4.4 |
| 竹林小徑／bandit_wolf_handler | 敵方／無先手 | 24 | 100% | 100% | 4.1 | 4.4 |
| 竹林小徑／mist_wolf_pack | 我方先手 | 24 | 100% | 100% | 4.0 | 3.5 |
| 竹林小徑／mist_wolf_pack | 敵方／無先手 | 24 | 100% | 100% | 3.9 | 4.1 |
| 北坡獵場／north_slope_pack | 我方先手 | 48 | 69% | 69% | 4.9 | 5.2 |
| 北坡獵場／north_slope_pack | 敵方／無先手 | 48 | 81% | 69% | 6.3 | 6.4 |

模擬中新舊兩種都沒有退回模板。

**結論**：拉開距離後，平均輪數幾乎不變（±0.5 輪）。巡邏戰和竹林小徑的勝率不變。下降集中在兩處：
渡口石階 1 級的新手固定戰（盜賊有弓手：我方先手 92%→83%、其他 94%→81%），以及北坡狼群的
「敵方／無先手」（81%→69%）。解讀：貼身開打時我方第 1 輪就能集火，隔 3 格時敵方遠程先多打一輪；
隔 2 格（我方先手）的損失比隔 3 格小。新手戰還在八成以上，本段**不調數值**。若 PM 想讓新手戰回到九成，
可以考慮：新手戰的 `bandit_raiders` 少一名弓手、或 `gap_other` 改 2（兩者都是內容／規則數值，不用改程式）。
樣本小（每格 24～48 場），差距 10 個百分點左右有雜訊，要定案時建議 PM 加大種子數。

## 5. 待 PM 決定

1. **第三方不保證距離**：三方混戰的第三方由引擎排在敵方起始區附近（6C-2 照舊），可能比 N 格近。要不要也套距離
   （要動引擎的排法或在世界層另畫第三方起始區）？
2. **退不了時挑格子可能跑到敵人另一側**：21.10 第 26 條第 2 點「在符合距離的格子裡挑最靠近接觸點的」照字面做，
   只要走得到就算，極端地形下主角可能被擺到敵人側邊或背後。正式內容 534 次都沒有用到退回模板；要不要限制
   「不能比接觸點更靠近敵方那一側」？
3. **已經比 N＋1 遠的接觸**（例如視野 4 格被看到卻是我方先手，實際不會發生）：照「不會擺得比 3 格更遠」往前
   找最近的符合格，所以會往敵人靠近；目前只在表格測試出現。
4. 霧牆提示的標點：`notice_zh()` 組成「霧太濃，還過不去。主線：先查清源晶裂痕」，說明卡在原文後面再接；
   文案若要改，改 `crystal_rift.yaml` 即可。
5. `WORLD_RULES_VERSION` 加到 2；6E-2 若也加一，合併時取較大值再加一即可（內容 digest 本段也已經變了）。
