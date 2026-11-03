# Phase 5C-3d／5E-3b 完成報告：用心清單引擎端驗證、5E-3 收尾

> 規格：`docs/phases/Phase5計畫.md` 第 1 節表格 5C-3d、5E-3b 兩列（玩法 PM 2026-11-03 代決）。分支 `worktree-agent-a98875a066929f09e`。

## 5C-3d：用心清單改由引擎驗證

### 交付

| 項目 | 檔案 |
|---|---|
| 關鍵詞比對：每筆勾選的事實，玩家原文（`SituationAction.player_text`）要**完全字串包含**它的一個關鍵詞，否則這筆「不算」（`reason_zh`＝「原文沒有提到這筆事實」），其餘照算、不退回重試 | `src/trpg/world/situations.py`（`_fact_entries`、`situation_fact_keywords`、`mentions`、`_verify_care`） |
| 關鍵詞來源：① 線頭 `text_zh`＋`aliases_zh`；② NPC `name_zh`＋`aliases_zh`；③「補給」＋`situation_rules.yaml` 的 `exchange_aliases_zh`；④ 弱點 `text_zh`＋`aliases_zh`。第一個關鍵詞＝事實本身的名稱 | 同上 |
| 「針對弱點」＝原文提到弱點關鍵詞或別名 **且** 方法在弱點 `methods` 內（兩個檢查依序：關鍵詞先、方法後）；模型關閉時照舊不能引用弱點（`CITABLE_ITEMS` 沒動） | 同上 |
| 結算事件記下被拿掉的項目：`SituationCheckEvent.dropped`（事實編號，預設空、舊日誌照讀）；`care` 明細照舊逐筆標「不算」與原因 | `src/trpg/world/actions.py` |
| 別名欄位（新增，選填，每個 2～20 字）：`WeaknessDef.aliases_zh`、`ThreadDef.aliases_zh`、`NpcCardDef.aliases_zh`、`SituationRules.exchange_aliases_zh` | `src/trpg/content/world_situations.py`、`world_events.py` |
| 雲嶺內容的別名（30 個弱點、19 條線頭、8 位 NPC、交換 2 個） | `content/world/situations/cloud_ridge.yaml`、`events/cloud_ridge.yaml`、`npcs/cloud_ridge.yaml`、`situation_rules.yaml` |
| 前端點選引用：API 的 `CiteFactView.insert_zh`＝第一個沒被遮住的關鍵詞（一定過得了比對）；點選時插進回答（已含、沒有可插、插了超過 500 字都不動；取消引用不刪字） | `src/trpg/api/world_story_view.py`、`world_story_schemas.py`、`client/src/world/story.ts`（`insertCite`）、`EventCard.tsx` |
| 測試 | `tests/world/test_situations.py`（新增 4、改 4）、`tests/llm/test_situation_propose.py`（注入回答的弱點現在被拿掉）、`tests/api/test_world_events_api.py`（新增 2）、`client/src/world/story.test.ts`（新增 1） |

### 插入的文字一定能通過比對（規格第 5 點）

- 線索：插 `text_zh`（＝關鍵詞第一個）；被遮住（含還沒發現的隱藏地點名）時改插第一個沒被遮住的別名（例：「斷崖幫寨的暗門（隱藏入口）」→「暗門」）。
- 往來：插 NPC 名字（`text_zh` 是「名字（往來）」，名字本身就是關鍵詞）。
- 交換：插「補給」。
- `tests/world/test_situations.py::test_fact_keywords_cover_fact_names`、`tests/api/test_world_events_api.py::test_cite_insert_text_passes_keyword_check` 驗證。

## 5E-3b：5E-3 收尾

| 項目 | 檔案 |
|---|---|
| 精英首殺公告只說「誰打倒了什麼」：模板變數只剩 `$name`、`$target`（寫 `$location`／`$region` 會載入錯誤）；文字改成「【首殺】$name 全服第一個打倒了精英「$target」！」 | `src/trpg/api/announce.py`、`content/world/announcements.yaml`、`tests/api/test_announce.py`（新增 1、改 1） |
| 作者刪自己的留言：`DELETE /api/world/characters/{id}/notes/{note_id}`（回更新後的留言板）；不是這個角色留的、或別人的角色一律 404 | `src/trpg/api/notes.py`（`delete(..., author=)`）、`routes/world.py` |
| 管理者登入時每則留言旁一個刪除鍵：留言板回 `admin`、每則 `can_delete`（自己的或管理者）；管理者刪別人的走原本的 `DELETE /api/world/notes/{note_id}` 再重讀 | `src/trpg/api/notes_schemas.py`、`client/src/world/NotesPanel.tsx`、`notes.ts`、`api/client.ts`、`api/types.ts`、`styles/world.css` |
| 本機模型不可用時「說書人休息中（使用固定文字）」小標示：開關開著且 `model_available === false` 時，在大世界標題列右上角顯示；純文字、不擋操作；每 60 秒重讀 `/api/world/llm` | `client/src/screens/WorldScreen.tsx`、`world/story.ts`（`narratorResting`） |
| 測試 | `tests/api/test_notes.py`（新增 2）、`client/src/world/notes.test.ts`（新增 1）、`story.test.ts`（新增 1） |

## 檢查結果

- `ruff check`、`ruff format --check`、`mypy`（1150 檔）、`lint-imports`（11 kept）全過。
- pytest `tests/world tests/api tests/llm tests/bot tests/content tests/test_architecture.py -n 8`：見下方（交件前跑）。
- vitest 134 檔 1254 passed；`build` 通過。
- swamp 種子 7 重播通過（88 動作、313 事件）。
- OpenAPI 已重產（`CiteFactView.insert_zh`、`NoteView.can_delete`、`LocationBoard.admin`、新端點）；合併 main 後再產一次沒有差異。
- 已 `git merge main`（含 5D-2b、5D-3b，無衝突）。
- 沒開瀏覽器實測（前端變更由 vitest、型別檢查、build 與 API 測試覆蓋）。

## 代決（最保守）

| # | 代決 |
|---|---|
| 5C3d-1 | 比對是 `keyword in player_text`，不轉大小寫、不去空白、不做簡繁轉換 |
| 5C3d-2 | 別名至少 2 字（單字太容易順口帶到）、最多 20 字；選填 |
| 5C3d-3 | 往來（②）的關鍵詞只有 NPC 名字與別名，不含往來線頭的文字（只提「欠我人情」不算提到這位 NPC） |
| 5C3d-4 | 交換（③）的事實名稱定為「補給」，別名「乾糧」「糧食」 |
| 5C3d-5 | 檢查順序：同一項重複 → 核對不到 → 原文沒提到 → 弱點方法不符；「同一項只算一次」只看算過的那筆，所以第一筆線索被拿掉時第二筆線索還有機會 |
| 5C3d-6 | 舊日誌：`dropped` 預設空、照讀；但舊的 `situation` 動作重播時會用新規則重算用心清單（原文沒關鍵詞的那筆會變不算）。現在沒有正式上線的大世界存檔，所以沒做版本分流 |
| 5C3d-7 | 前端取消引用時不刪已插入的字（可能已被玩家改寫）；字數會超過 500 時不插 |
| 5C3d-8 | 關鍵詞都被遮住時 `insert_zh` 為 `null`，點選不插字（玩家要自己寫）；雲嶺現有內容都有沒被遮住的關鍵詞 |
| 5C3d-9 | LLM prompt 沒改（仍是 `situation-check/1`）；引擎拿掉的筆數不回饋給模型 |
| 5E3b-1 | 「作者」＝留這則的**角色**（不是帳號）；同帳號的其他角色也不能刪，別人的一律 404（不洩漏是誰的） |
| 5E3b-2 | 開發模式沒帶 token 時 API 仍可刪任何留言（照 5E3-4），但畫面**不**給每則刪除鍵（規格寫「管理者登入時」） |
| 5E3b-3 | 小標示只在「開關開著、但健康檢查說不可用」時出現；開關關著是刻意不用，不顯示。因專案規則（`floatCardRule.test.ts`）禁止新的 `position: fixed`，標示放在大世界標題列右上角，不是浮在畫面上 |
| 5E3b-4 | 前端每 60 秒重讀一次 LLM 狀態（跟伺服器健康檢查預設間隔一樣） |

## 待 PM 決定

1. **別名內容**是實作者寫的初稿（雲嶺 30 弱點、19 線頭、8 NPC），有些可能太寬（例：`hunter_name` 的「名字」、`frost_chime_we` 的「我們」、`monk_story_gap` 的「矛盾」）或太窄，請玩法 PM 審。
2. **舊日誌重播**（5C3d-6）：要不要依 `prompt_version` 或日誌版本分流，讓舊的 `situation` 動作照舊規則算。
3. 往來（②）要不要也接受往來線頭的文字或別名（5C3d-3）。
4. 要不要把「原文要提到」寫進 LLM prompt（要改 prompt 版本號），減少模型白勾。
5. 首殺足跡（地點留言板的「X 在這裡首殺了精英」）仍會在**那個地點**顯示，這是到過的人才看得到的足跡，不是公告；要不要也拿掉。
6. 設計文件（9.6.4、9.6.10、#105）的對應文字由玩法 PM 更新。

## 複雜度例外

無（沒有新增 `# noqa`）。
