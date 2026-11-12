# Phase BAL-21a 完成報告｜引擎能力：延遲段落在選定格＋進入新階段回復法力（預設關閉）

> 規格：`docs/phases/PhaseBAL-21計畫.md` 第 0.0 節（優先）、第 4 節、第 9 節、第 10 節 T1～T7（全照建議）。基準 commit `37c7d225`（含 `08604f69` BAL-21 定稿）。
> 本段不改 `content/` 任何檔案、不換招、不幫任何頭目填 `mana_restore`。

## 1. 做了什麼

**(i) 延遲段落在選定格（`followup.anchor: cast_tile`）**

- 內容 schema：`FollowupSpec.anchor: Literal["cast_tile"] | None`（`exclude_if=None` → 沒填不輸出）。檢查：只有 `when: delayed` 能填（`skill.py::_check_followup`）；第一段的形狀要在新常數 `ANCHOR_FIRST_SHAPES`（`cross`、`square3`、`ground_tile`＝`skill_shapes.yaml` 裡 `targeting: tile` 的三個，測試對照）（`followup.py::_check_delayed`）。第二段仍限 `DELAYED_SHAPES`、`range: 0`。
- 狀態：`StatusInstance.anchor: Pos | None = None`（只有 `charging` 用）。`StatusInstance` 是 frozen dataclass，`UnitState.clone()` 複製清單、實例共用，不必改 `clone()`；JSON 走 pydantic adapter，有預設值，舊 JSON 讀得回來。
- 施放：`delayed.charge(ctx, caster, skill, action)` 多收 `action`（呼叫點 `interpreter._resolve_cast`），`anchor_of(skill, action)` 取 `action.target_pos` 存進狀態。
- 選取：`delayed_selection(..., anchor=)` 有 anchor 時改走新函式 `skills/targeting.py::anchored_area`：以落點為中心展開十字／方陣／環形，**不重驗射程與視線**（T2），只取地圖內格子、檢查技能層級條件；施放者不在中心，不套 `include_caster`；`origin`＝落點。`charge`、`_release`（改收狀態本身）、`charge_infos` 都傳 anchor。
- 結算：`run_delayed` 的 `SkillFollowup.origin` 在 anchored 時用 `area.origin`（落點），其他照舊用施放者位置；命中、抵抗、傷害仍以施放者本人計。
- 事件：`FollowupCharged.anchored: bool = False`；anchored 時 `pos` 是落點、`tiles` 以它為中心（T3）。`ChargeInfo`、`TelegraphCharge` 也加 `anchored`。
- AI：`composite_estimate(state, unit, skill, area, action)` 多收 `action`，anchored 招以 `action.target_pos` 推預計範圍；候選列舉沿用第一段 `tile` 型形狀的 `selections`（T1，不另列舉）。`_delayed_points` 讀預覽裡的 `followup_charged.tiles`，自動正確，沒改。
- 文字：後端 `narrative/events.py`、`narrative/telegraph.py`、`narrative/skills.py`（技能卡第二段開頭）在 anchored 時寫「落在指定位置」／「在施放時選的格子」；沒填的招文字不變。
- API／前端：`StatusView.charge_anchored`、`ChargeOut.anchored` 用 `bool | None = None`（理由見第 5 節第 1 點）；`client/src/battle/followup.ts::chargeStatusText` 依 `charge_anchored` 寫「落在指定位置」（規格 4.2 第 7 點）；`client/openapi.json`、`src/api/schema.d.ts` 重產（各多 2 個選填欄位）。動畫片段不動（T7，留 21b）。
- `LOG_FORMAT` `trpg-battle-log/113` → `/114`（T3）；`docs/phases/戰鬥紀錄格式變更.md` 加一條；測試寫死的版號 11 處更新（8 處 `trpg-battle-log/113` 字面值＋3 處 `endswith("/113")`）。

**(ii) 進入新階段回復法力（`BossPhase.mana_restore`）**

- `BossPhase.mana_restore: int | None`（`ge=1`，`exclude_if=None` → 沒填不輸出）；算進 `changes_anything()`，所以開場階段填了會被 `check_phases` 擋。
- `boss_phases._enter`：換行為模式之後、施加狀態之前呼叫 `_restore_mana`：回復 `min(mana_restore, max_mana − mana)`；有實際回復才發 `resource_restored`（`source_id`＝頭目自己，`resource: mana`），已滿時什麼都不發（不發 `effect_fizzled`）。不取用亂數；預覽本來就不檢查階段。
- 沒有任何頭目填值（`test_unset_fields_are_not_serialized` 掃全部單位）。

## 2. 逐條驗收（規格 4.4）

| 條件 | 證據 |
|---|---|
| 施放時選格 → `FollowupCharged.tiles` 是該格的 3×3、`pos` 是該格 | `test_delayed_anchor_bal21.py::test_casting_charges_on_the_chosen_tile`（另驗狀態 `anchor`、敘事文字）、`test_the_preview_shows_the_chosen_tile` |
| 施放者移動後 `charge_infos` 與釋放範圍仍在原格 | `test_the_planned_area_stays_put_when_the_caster_moves`（環境預告＋視圖 `charge_anchored`）、`test_the_release_lands_on_the_chosen_tile_after_the_caster_moved` |
| 下一個自己的回合開始在原格結算傷害與表面、`charging` 移除 | `test_the_release_lands_on_the_chosen_tile_after_the_caster_moved`（3×3 全是火地、施放者站的格子沒有）；T2 不重驗射程：`test_the_release_is_not_rechecked_for_reach`；`release: attacked`：`test_an_attacked_release_lands_on_the_chosen_tile` |
| 暈眩、倒下、被取代照舊取消 | `test_control_or_downing_cancels_an_anchored_charge[controlled/downed]`、`test_a_new_charge_replaces_the_anchored_one` |
| 選格超出第一段射程 → `IllegalActionError` | `test_a_tile_out_of_reach_is_illegal` |
| 沒填 `anchor` 的現有延遲段（`lava_spout`）範圍仍跟著施放者 | `test_lava_spout_still_follows_its_caster`；同數值不帶 anchor 的對照招：`test_a_loose_twin_with_the_same_first_stage_releases_around_the_caster` |
| AI：貼身沒人、4 格內 2 名敵人，anchor 招候選分數 > 0；對照招不列入 | `test_the_ai_lists_the_anchored_skill_when_nobody_is_adjacent`（`composite_estimate` 與 `UtilityAI.rank` 兩層） |
| `clone()` 與 JSON 往返保留 `anchor` | `test_the_anchor_survives_clone_and_json`；`tests/engine/test_state_clone.py` 過 |
| 重播 | `test_a_battle_with_an_anchored_charge_replays_exactly`（效用 AI 自己放出 anchored 招、`BattleLog` JSON 往返後重播，最終狀態與 `rng_state` 一致） |
| 內容檢查：非延遲段帶 anchor、第一段不是 tile 型 → 載入失敗 | `tests/content/test_delayed_anchor_content.py::test_only_delayed_segments_can_anchor`、`test_bad_anchors_fail_to_load[...]`、`test_anchor_first_shapes_are_exactly_the_tile_picking_shapes` |
| 進階段回復法力：預設不回復；回復、上限、已滿不發事件；重播 | `tests/engine/test_boss_mana_restore_bal21.py`（5 項，合成頭目）；schema：`test_mana_restore_is_optional_positive_and_not_for_the_opening_phase` |
| 沒填不輸出 | `test_unset_fields_are_not_serialized`（全部內建技能的 `followup` 與全部單位的 `phases`） |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 見第 4 節 |
| 一場 `trpg battle --log-json` ＋ `replay` | `molten_heart_pit` 種子 2：紀錄格式 `trpg-battle-log/114`，「重播驗證通過：87 個動作、477 個事件，最終狀態一致」，兩個結束碼 0 |
| 4.3 的 `different=0` | 見第 3 節 |

## 3. 雜湊與實戰不變的證明

- 腳本（scratchpad，未 commit）：改動前在 `37c7d225` 產生 `before.json`，改完產生 `after.json`，整份比對。每場比對：完整事件 JSON、步驟列表、輪數、勝方、最終 `rng_state`；比對時只拿掉 `followup_charged` 新增的預設欄位 `anchored`（`LOG_FORMAT` 字串不在事件內）。地圖預設陣容、效用 AI、`max_rounds=30`。
- **8 張地圖 × 2 種子**（`molten_heart_pit`、`rift_gate`、`cloud_summit` 三張頭目圖＋`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`；種子 1、2）：`maps/seeds=16 events=5434 different=0`。
- 這 16 場只有 3 次蓄力，所以另加 **3 張頭目圖 × 種子 3～12**（30 場，20 次 `followup_charged`、18 次延遲段釋放）：`maps/seeds=30 events=14613 different=0`。
- 三個雜湊（改前＝改後，逐字相同）：
  - `hash_ruleset(lib.ruleset)`：`163ec72f2f15a7e78761db744eeae1aab55385dcb0a4610677a46f6fc628893e`
  - `ruleset_hash(lib)`（一輪存檔）：`75ea2de332a01e16b812998c7fce2bf8abc1bb121f5449c97848ea1b23e12e8e`
  - `content_digest(lib)`（世界日誌）：`356b34e13d36021d95ace54217caddde0c84abbf28ce8720dec3430b6e9ef108`
- parity slow：`tests/skillgen/test_refactor_parity.py`（隨 `tests/skillgen` 含 slow 一起跑）過，夾具沒動。
- CLI 快照：`tests/cli/test_output_snapshots.py -m slow` 結果見第 4 節；沒有重產任何鍵。

## 4. 測試與檢查（結束碼）

（交件前跑，結果見下表）

| 指令 | 結果 |
|---|---|
| `uv run ruff check .` | 0（All checks passed） |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1459 個檔無問題） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| `uv run pytest -q -n 8 -m "not llm" tests/engine`（含 slow） | 0：4399 passed、4 xfailed（既有 `test_demo_balance` 平衡延後） |
| `uv run pytest -q -n 8 -m "not llm" tests/content tests/skillgen tests/narrative`（含 slow） | 0：8345 passed、14 skipped（既有） |
| `uv run pytest -q -n 8 -m "not llm" tests/skillgen/test_refactor_parity.py`（parity slow，單獨再跑一次確認） | 0：887 passed（夾具沒動） |
| `uv run pytest -q -n 8 tests/cli/test_output_snapshots.py -m slow` | 0：24 passed，**沒有重產任何鍵** |
| 版號字面值所在的 CLI 測試＋API：`tests/cli/test_{basic_actions,battle,run_battle,skills,variant,weapons_ranged}_cli.py`、`tests/api/test_delayed_api.py`、`test_openapi_snapshot.py`、`test_routes.py` | 0：94 passed |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0：299 檔、3811 項 |
| `corepack pnpm -C client build` | 0（只有既有的 chunk 大小警告） |

## 5. 規格沒寫到、採保守做法的地方

1. **API 欄位用 `bool | None = None` 而不是 `bool = False`**：`openapi-typescript` 7 把「有預設值、不可為 null」的欄位當必填，`StatusView` 加 `bool = False` 會讓 9 個前端測試夾具與開發頁（`bombs.test.ts`、`drawModel.test.ts`、`costStatus.test.ts`、`formGallery.ts`、`fxGallery.ts`、`scaleGallery.ts`、`statusGallery.ts`…）型別錯誤。規格說前端只改 `followup.ts` 的說明文字，所以改成選填：`StatusView.charge_anchored` 只有 anchored 時是 `true`、其他 `null`；`ChargeOut.anchored` 照引擎給 `true`／`false`。引擎內部（`FollowupCharged`、`ChargeInfo`、`TelegraphCharge`）照 T3 用 `bool = False`。
2. **`mana_restore` 是點數**（不是千分比），上限是最大法力；回復時機放在「換行為模式之後、施加狀態之前」；已滿時不發事件。
3. **anchored 不套 `include_caster`**：施放者不在中心。施放者若剛好站在落點的範圍內，照第二段的 `affects` 規則照常算（和一般範圍招一樣）。
4. **第一段可帶自身位移**（`COMPOSITE_MOVES`）的規則沒有另外收緊：落點一律取 `action.target_pos`。
5. 後端技能卡、事件、環境預告的敘事文字在 anchored 時也換成「落在指定位置」（規格只點名前端 `followup.ts`；不改的話 21b 的招卡會寫錯）。沒填的招文字逐字不變（CLI 快照不變為證）。

## 6. 影響

- 舊戰鬥紀錄（`/113`）不能重播、戰鬥中的存檔讀不回（狀態結構變了）。使用者 2026-11-12：「存檔都可以刪除」；本段沒有刪任何存檔檔案、沒寫遷移。
- 規則包雜湊、一輪存檔的 `ruleset_hash`、世界日誌的 `content_digest` 都不變，但世界日誌的規則鍵含 `LOG_FORMAT`，所以舊世界日誌會標成「規則已變、不能重播」。

## 7. 新增的複雜度 `# noqa`

無。

## 8. 待 PM 決定

1. `mana_restore` 用「點數」還是「最大法力的千分比」（目前是點數，上限最大法力）；使用者在數值工坊調時哪個好用。
2. 前端是否要把 anchored 的預告格畫得和「跟著施放者」的不同（目前畫法完全沿用，只有文字不同）；屬美術／介面，21b 派工前可問美術 PM。
3. `ChargeOut.anchored`／`StatusView.charge_anchored` 用選填型別（第 5 節第 1 點）是否接受；若要改成必填，需要另外動 9 個前端夾具。
