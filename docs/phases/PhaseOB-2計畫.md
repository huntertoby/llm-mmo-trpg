# Phase OB-2｜#150：三選一延後、正式選定、關鍵字推薦

> 來源：`docs/design/21-探索地圖與城鎮.md` 21.5（共 9 點，**以它為準**）、`docs/玩法決定紀錄.md` #150。前置：OB-1（報告 `docs/phases/PhaseOB-1報告.md`，`opening_gate` 的接法在裡面）。
> 盤點：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\盤點-150與147.md` 第 1.1、1.2、4.3 節。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 推薦關鍵字 | 用專屬關鍵字；製造優先、再照表順序；沒有就不標 |
| 選定時 | HP、法力回滿 |
| 入門期手動配點、`respec` | 不擋，正式選定時全部重配 |
| 重骰、指定詞條 | 只限頭、身、手、腳 |
| 影子 | **入門期不存影子，正式選定後才存** |
| 入門招 | 尚未定案（等使用者答 #148），一律從資料讀 |

## 範圍外

- OB-3 重選、閃現限制、配點教學；OB-4 戰鬥閘；OB-5／6 前端、台詞。
- 不動 `src/trpg/engine/`、`roguelite/`。

## 交付項目（對應盤點 1.1）

1. 第 1、2 步三選一延後：`world/quests.py:431`，入門期且任務是 `kind: starter` 時記進 `deferred_offers`，不動 `offers_made`；經驗、靈感照領，`level_to` 不動。
2. 正式選定：`opening_confirm` 依階段分流（沿用 `OpeningConfirmAction`）。換武器與招、收回入門招與其 `flash`／`skill_usage`、依新大類重建基礎值、等級 HP 走 `with_hp_change`、全部點數重配並寫進 `attribute_spent`、依序產生 `deferred_offers` 的三選一。地點限葛蘭鎮或主城。`stage` 轉 `chosen`，`_chosen_rule` 接上。
3. 關鍵字推薦：`world/opening.py` 新純函式，放進 `RangeView.recommended_keywords`。
4. 入門期不存影子：城鎮整備的影子寫入在 `stage != chosen` 時跳過。
5. `client/openapi.json`、`schema.d.ts` 重產；typecheck 過（新必填欄位補 fixture）。

## 受影響的既有功能

見盤點 4.3（`tests/world/test_quests.py`、`test_quest_replay.py`、`tests/content/test_world_quests.py`、`tests/api/test_offer_prefetch.py`、`tests/world/test_dispatch.py`、`tests/narrative/test_events_text.py` 等）。所有新判斷以 `char.opening is not None` 為前提，舊角色與 roguelite 不變。

## 行為一致測試

- 表格測試，**實際跑世界動作**：三大類 × 入門期打完第 1、2 步 → 正式選定：武器、招、HP、法力、點數全部正確，入門招與使用紀錄已收回，延後的三選一依序出現且內容與任務資料一致。
- 三選一的亂數與「不延後」時的出題規則一致（同種子可重現）。
- 影子：入門期不寫入、選定後寫入。
- 世界日誌重播一條完整流程。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/world`、`tests/api`、`tests/content`、`tests/narrative`、`tests/skillgen`、`tests/roguelite`、`tests/server`、`tests/test_architecture.py` 通過。`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` 是基準就會機率性失敗的測試，單獨重跑確認即可。
- 一場戰鬥 `--log-json` ＋ `replay` 通過。

## 報告

`docs/phases/PhaseOB-2報告.md`：逐條驗收、正式選定的順序與理由、待 PM 決定。
