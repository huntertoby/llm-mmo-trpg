# Phase OB-1 報告：#150 開局先玩再定（存檔、選大類、動作閘門）

> 實作者：worktree 基準 main `4b7d44f8`。沒有 push、沒有 merge。依據：`docs/phases/PhaseOB-1計畫.md`、`docs/design/21` 21.5（#150 第 1～9 點）、`docs/玩法決定紀錄.md` #150、共用筆記 `盤點-150與147.md` 第 1.0、1.1、2、4.3 節。沒有動 `src/trpg/engine/`、`src/trpg/roguelite/`（PR-1）、`content/units`、`content/ai_profiles.yaml`、遭遇資料（CB-2d）。

## 1. 交付項目

| # | 項目 | 做法 |
|---|---|---|
| 1 | `OpeningState` 欄位 | `stage`、`weapon_class`、`deferred_offers`（`DeferredOffer{quest, step}`）、`weapon`、`keywords`、`reselect_used`、`granted_skills`，全在 `OpeningState` 內，`CharacterState` 頂層沒加欄位。驗證：`stage == "pick_class"` 與 `weapon_class is None` 必須同時成立 |
| 2 | 內容 | `newcomer.yaml` `range.starters`；`RangeContent.starters`（要涵蓋 `racks` 每一類）；`_range_problems` 檢查武器存在、屬於該大類、非召喚物專用 |
| 3 | `opening_class {weapon_class}` | `world/actions.py` 動作與事件 `OpeningClassChosenEvent`；`world/opening.py::apply_opening_class`（入門武器讀 `range.starters`、入門招讀 `range.demos`、4 點走既有的 `recommended_allocation`，HP 法力回滿）；`world/step.py` 分派；`api/world_presenter.py` 事件句；`RangeView.stage`、`RangeView.weapon_class`、`RangeDemoView.starter_weapon`／`starter_weapon_zh` |
| 4 | `opening_gate` 分階段 | 見第 3 節 |
| 5 | 升級自動配點 | `growth.py::_starter_allocate`，`gain_xp` 結尾；`stage == "starter"` 時走 `recommended_level_up`＋`allocate_attributes`＋`with_hp_change`，多一筆 `AttributesAllocatedEvent` |
| 6 | 入門武器不能賣、寄、分解 | 照盤點是自然做不到（不是物品），`test_starter_weapon_is_not_an_item` 鎖住 |

舊流程建角：`CreateWorldCharacterRequest.dev_fields()` ＋既有的 `reject_dev_fields`，開發模式關時 `weapon`／`keywords` 回 403（同 6S-1 其他開發用欄位）。測試用統一開關：環境變數 `TRPG_LEGACY_CREATE=1`（`trpg.api.routes.world.LEGACY_CREATE_ENV`），在 `tests/conftest.py` 開頭設定，**沒有逐一改測試檔**；拒絕路徑的測試用 `monkeypatch.delenv`。`WorldStore.create` 本身不變（模擬與開發工具直接呼叫）。正式伺服器不要設這個變數。

## 2. 版號與遷移

| 項目 | 變動 |
|---|---|
| `CHAR_FORMAT` | `trpg-char/12` → `/13`；13 個測試檔的字面值改成 `/13` |
| `WORLD_RULES_VERSION` | 22 → 23（`save.py` 有寫內容） |
| `trpg-wlog` | 不升；`OpeningConfirmAction` 保留 |
| `LOG_FORMAT`、`RULE_HASHES` | 不變 |
| openapi | `client/openapi.json`、`client/src/api/schema.d.ts` 重產；`client/src/world/range.test.ts` 的 fixture 補新必填欄位 |

遷移（`/12` 照讀，新欄位靠預設值）：

| `/12` 存檔 | 升級後 |
|---|---|
| `opening: null` | 不變，已完成開局，沒有重選 |
| 沒有 `opening` 欄位 | 同上 |
| `opening: {seed}`（靶場中） | `stage="pick_class"`，走新流程 |

## 3. `opening_gate` 結構（給 OB-2、OB-4）

`opening_gate(library, world, char, action)`（簽名多了 `library`、`world`）：

- `char.opening is None`：只擋 `opening_class`、`opening_confirm`（不能重選），其他一律放行，舊角色不受影響。
- 否則依 `_STAGE_RULES[char.opening.stage]` 依序跑規則；每條規則是 `(library, world, char, action) -> str | None`，回傳擋下的中文原因。

| 階段 | 規則 |
|---|---|
| `pick_class` | `_pick_class_rule`：白名單 `_PICK_CLASS_ALLOWED`（`opening_class`、`opening_confirm`、`change_look`、`news_seen`、只記畫面紀錄的動作） |
| `starter` | `_starter_blocked_rule`（表 `_STARTER_BLOCKED`：再選大類、正式選定、換種族、閃現類、換技能、雇用與影子 AI、聯賽、賽季 Boss、誓約）；`_main_hand_rule`；`_armor_only_rule`（打造、強化、重骰、指定詞條）；`_before_level_4_rule`（溶掉、傳承） |
| `chosen` | `_chosen_rule`（本段到不了，開局動作一律不收）；`_before_level_4_rule` |

接法：

- **OB-2**：改 `_STARTER_BLOCKED` 的 `OpeningConfirmAction` 列與 `_chosen_rule`，讓 `opening_confirm` 依階段分流；`deferred_offers`、`granted_skills`、`weapon`、`keywords` 欄位已備好。
- **OB-3**：閃現限制加進 `chosen` 的規則。
- **OB-4**：在 `_STAGE_RULES["starter"]` 加一條戰鬥規則；動作層之外的敵人過濾（`field_enemies` 等）各自判斷 `char.opening.stage`。

## 4. 驗收

| 條件 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | All checks passed；2265 files already formatted |
| `uv run mypy` | Success: no issues found in 1424 source files |
| `lint-imports` | 14 kept, 0 broken |
| `tests/world tests/api tests/content tests/narrative tests/skillgen tests/roguelite tests/server tests/test_architecture.py`（`-n 8`） | 9496 passed、15 skipped、**1 failed**，見下 |
| `trpg battle --map swamp --seed 7 --log-json` ＋ `battle replay` | 重播驗證通過：63 個動作、235 個事件，最終狀態一致 |
| `corepack pnpm -C client typecheck` | 結束碼 0 |

唯一的失敗：`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge`（「AI 代打到結束都沒有出現 charge」）。**基準 commit 就會機率性失敗，不是本段造成的**，測試沒有修改。該測試的註解寫明世界種子與角色 ID 每次隨機、最多重試 6 次。單獨重跑整個檔案 14 passed。實測失敗率（單獨跑該測試）：

| 程式 | 失敗次數 |
|---|---|
| 基準 `4b7d44f8`（`git archive` 解到暫存資料夾，確認 `trpg.__file__` 載入的是那份） | 6／40 |
| 本段 | 2／56（三批：1／8、0／24、1／24） |

所以規格的全目錄驗收在這一次全量裡**不是全綠**，除這一個測試外全過。建議另排把這個測試的隨機改成固定種子（本段不動）。

行為一致測試（`tests/world/test_opening_stages.py`，52 個；全部跑世界動作，升級另有直接呼叫 `gain_xp` 的逐屬性比對）：

| 規格 | 測試 |
|---|---|
| `pick_class` → `starter`、三大類武器／招／4 點 | `test_pick_class_gives_starter_kit`（3 組）、`test_pick_class_is_deterministic`、`test_class_cannot_be_rechosen` |
| 入門招從資料讀 | `test_starter_kit_reads_demos_from_data` |
| `/12` 三種舊存檔 | `test_format_12_upgrades`（已完成、無 opening、靶場中）、`test_old_in_range_character_uses_new_flow` |
| 舊角色不受影響 | `test_done_character_is_untouched_by_gate`、`test_done_character_cannot_use_opening_actions` |
| `pick_class` 白名單 | `test_pick_class_whitelist` |
| `starter` 被擋 | `test_starter_blocks`（14 組）、`test_starter_blocks_main_hand_with_or_without_slot`、`test_starter_smithing_is_armor_only`（weapon、ring、offhand）、`test_starter_craft_slot_type` |
| `starter` 不被擋 | `test_starter_can_change_armor`（4 部位）、`test_starter_smithing_is_armor_only`（body、head）、`test_starter_allows_rest_and_teleport` |
| 升級自動配點 | `test_level_up_auto_allocates`（3 組，與 `recommended_level_up` 逐屬性相同）、`test_level_up_through_world_action`（真的走情境判定）、`test_non_starter_points_still_accumulate` |
| 不能賣、寄、分解 | `test_starter_weapon_is_not_an_item`（3 組）、`test_starter_skills_cannot_be_dissolved` |
| 世界日誌重播 | `test_new_flow_log_replays_identically` |

另有：`tests/api/test_opening_class_api.py`（7 個：動作、`RangeView`、舊流程建角開發模式開關）、`tests/content/test_newcomer_content.py` 新增 `starters` 檢查。

沒有新增複雜度類 noqa。

## 5. 待 PM 決定

1. **`pick_class` 仍收 `opening_confirm`**：本段不改前端，現有靶場畫面送的就是它；拿掉的話新角色在 OB-5 之前會卡死。結果是目前線上走舊的一次選定，不會經過入門期。OB-2 分流、OB-5 換畫面時收掉。
2. **`starter` 階段送 `opening_confirm` 一律 422**（OB-2 才有正式選定）。
3. **`change_look` 依盤點 1.1 放進 `pick_class` 白名單**，PR-2 不用再加。
4. **「打造與強化只限防具」的防具取 頭、身、手、腳**（8.12）；副手、項鍊、戒指也擋。
5. **附魔台的重骰、指定詞條**21.5 沒寫，保守比照打造與強化，只限防具。
6. **手動 `allocate`、`respec` 入門期沒擋**（21.5 沒列）：respec 會退回升級自動配的點，正式選定時全部重配，影響不到結果。分解、寄送背包裡的其他裝備也沒擋。
7. **一次升多級時點數一次配掉**（`gain_xp` 結尾），兩招屬性不同時全給較低的；新手鏈每步升 1 級不會遇到。
8. **入門期在城鎮整備會存影子**（`save_after_prep` 沒改）：別的玩家可能借到拿入門配備的影子。要不要在 OB-2 擋。
9. **戰鬥閘（OB-4）還沒做**：入門期目前任何戰鬥都能打；三選一延後（OB-2）也還沒做。目前前端不送 `opening_class`，玩家碰不到入門期。
10. **閘門的中文訊息是實作者暫定**（換主手一句照共用筆記），台詞由 OB-5／6 定稿。
