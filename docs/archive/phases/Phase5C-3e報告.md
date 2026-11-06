# Phase 5C-3e 完成報告：5C-3d／5E-3b 收尾

> 規格：`docs/phases/Phase5計畫.md` 第 1 節表格 5C-3e 列；玩法 PM 代決逐字見 `docs/phases/Phase5C-3e代決.md`。分支 `worktree-agent-aa6a5bca824f841be`。

## 交付

| 項目 | 檔案 |
|---|---|
| 別名照代決清單改（其餘不動）：線頭 peddler_owes_you、alchemist_owes_you、ferryman_daughter、shards_under_den、shards_to_ashen（碎片往荒原）、tavern_rumor（拿掉別名）、frost_chime_we；NPC 阿岳、石師傅；情境弱點 monk_story_gap、hunter_name、pursuers_lost_in_fog、envoy_duty | `content/world/events/cloud_ridge.yaml`、`npcs/cloud_ridge.yaml`、`situations/cloud_ridge.yaml` |
| 「NPC 往來」的關鍵詞＝NPC `name_zh`＋`aliases_zh`＋**相關線頭**（`npc` 欄位等於該 NPC、且角色持有）的 `text_zh`＋`aliases_zh`；第一個關鍵詞仍是 NPC 名字（前端插入不變） | `src/trpg/world/situations.py`（`_fact_entries`） |
| 情境判定 prompt 寫明「勾選的事實，玩家原文（<player_input>）要提到；原文沒有提到的不要勾，遊戲會把原文沒提到的那筆拿掉」；`SITUATION_PROMPT_VERSION` 升為 `situation-check/2` | `src/trpg/llm/situation.py` |
| 首殺足跡保留；地點留言板的地點名與足跡文字先套 `story_masks`（與 5B-5 說書人／地點說明同一套）：這個角色還沒發現的隱藏地點用 `hint_zh`（沒填用預設提示語）；留言是玩家文字，照原樣 | `src/trpg/api/notes_schemas.py`（`location_board`） |
| 測試 | `tests/world/test_situation_aliases.py`（新增：每條改過的別名能命中 13 條、拿掉的寬泛詞單獨出現不命中 13 條、往來認相關線頭 1 條）、`tests/llm/test_situation_propose.py`（新增 1：prompt 文字與版本號）、`tests/api/test_notes.py`（新增 1：未發現顯示提示語、發現後顯示原名） |

## 檢查結果

- `ruff check`、`ruff format --check`、`mypy`（1156 檔）、`lint-imports`（11 kept）全過。
- pytest `tests/world tests/api tests/llm tests/content tests/bot -n 8`：3464 passed（含 OpenAPI 快照，API 型別沒變）。
- 沒改前端，未跑 vitest／build。
- swamp 種子 7 重播通過（88 動作、313 事件）。
- 已 `git merge main`（Already up to date）。

## 代決（最保守）

| # | 代決 |
|---|---|
| 5C3e-1 | 阿岳的別名照代決逐字寫成 `[阿岳, 獵戶阿岳]`；「阿岳」與 `name_zh` 重複，關鍵詞會自動去重，沒另外處理 |
| 5C3e-2 | frost_chime_we 的新別名照代決順序放在「碎晶之主」前：`[裂痕裡有我們, 「我們」, 碎晶之主]`；「「我們」」含全形引號，玩家原文要有引號才算 |
| 5C3e-3 | 往來認的相關線頭只算**角色目前持有**（有效、未過期）的線頭，和「往來」這筆事實存在的條件一致；沒有 `npc` 欄位的線頭不算進任何 NPC |
| 5C3e-4 | prompt 版本升級不做舊日誌分流（同 5C3d-6）；`situation-check/1` 的舊動作照讀 |
| 5C3e-5 | 留言板的遮罩除了地點名，也套在足跡文字上（例：精英名含隱藏地點名時一起換成提示語）；角色名、留言文字不套 |

## 待 PM 決定

1. 角色站在還沒發現的隱藏地點這種情況，現有流程大概碰不到（要先揭露才去得了）；遮罩是保險。要不要也在其他顯示地點名的地方（戰鬥結果一句話、隊伍存檔位置等 `_location_name`）統一套提示語，這次沒動。
2. 往來的關鍵詞現在含線頭全文（例：「道童提到觀裡在吵架」），提到線頭的別名也會同時命中「線索」與「往來」兩筆；兩筆都算是否符合玩法 PM 的意思，請確認。
3. 設計文件 9.6.4、#105 由玩法 PM 更新（代決第 5 點）。

## 複雜度例外

無（沒有新增 `# noqa`）。
