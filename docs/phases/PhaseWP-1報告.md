# Phase WP-1 報告｜許願池後端核心

> 實作 agent，2026-11-13。規格 `docs/phases/PhaseWP計畫.md`（本段第 3 節）。依據 main `b1a76452`（LF-3 已合併）。
> 使用者核可：「都按照建議」（專案 PM 轉達）。設計依據 `docs/design/07-角色成長.md` 7.6、#88；`docs/design/` 沒動。
> commit：`e2ab5722`（規格）、`7781803b`（規則、LLM、API 生成函式）、`2bfd442f`＋`3718a5b4`（測試）、`29bfccc5`（上手筆記）、本報告一筆。

## 1. 做了什麼

| 規格 3.1 | 做法 | 檔案 |
|---|---|---|
| 1. 內容規則 | `wish:` `per_week 2`、`cost_quest_coins 4`、`refund_permille 500`、`text_max_chars 60`、`max_keywords 2`、`llm_cards 1` | `content/world/rules.yaml`、`content/world_rules.py::WishRules` |
| 2. 世界動作與事件 | `WishAction{text?, keywords}`（剛好一種）、`WishMadeEvent`；三選一的 `source` 多 `wish`；`SkillOfferTakenEvent.refund`（0 不輸出） | `world/actions.py` |
| 3. 規則 | `wish_problem`（主城、入門期、遭遇、本週次數、任務幣；之後畫面共用）、`wish_menu`（扣掉 `start_hidden`）、`wishes_left`、`wish_keywords_problem`、`wish_request`、`apply_wish`；都不拿退 `PendingOffer.refund` | `world/wish.py`（新）、`world/step.py`、`world/quests.py` |
| 4. 生成請求與紀錄 | `WishGenRequest`、`WishGen{source: llm/partial/none, keywords, offer, attempts, codes, prompt_version}`；`Generated` union 加一種；型別別名 `Record` | `world/generated.py` |
| 5. LLM 端 | `match_wish`（schema `enum`、1～2 個、驗證不過帶 `<errors>` 重試）、`WISH_PROMPT_VERSION` `wish-match/1`、`WishSource`、`mock_wish_client`；`make_proposer(player_text=)` 把願望交給 `propose_skill`（`<player_input>`） | `llm/wish.py`、`llm/prompts/wish.py`（新）、`llm/candidate_source.py` |
| 6. API 層生成函式 | `LlmProvider.wish_source`（本機與 Mock）；`world_pregen.wish_generator`、`Generators.wish`、`_run` 分支；`prefetch` 不丟 `wish` 的暫存；**不預測** | `api/llm_source.py`、`api/world_pregen.py` |
| 7. 日誌與重播 | `supply` 收進 `generated`；`recorded` 依（`wish`, 鍵）重播，不呼叫 LLM（測試用 `replay` 讀回比對） | 沿用 `world/replay.py` |
| 8. 版號 | `CHAR_FORMAT` `trpg-char/14`（`/13` 照讀）、`WORLD_RULES_VERSION` 28；`WLOG_FORMAT`、`LOG_FORMAT` 不升；季末表登記 `wish_week` | `world/state.py`、`world/save.py`、`server/season_policy.py` |
| 9. 最小顯示 | 待選三選一標題「許願池」、步驟「許願：都不拿可退 N 任務幣（次數照扣）」；故事行「許願池給了技能三選一」「跳過了許願池給的技能，退還 N 任務幣」 | `api/world_story_view.py` |

**沒改**：`client/`、`api/world_schemas.py` 的請求 union（WP-2）、`skillgen/`（含轉型與模板邏輯）、`content/flash_templates.yaml`、`config/llm.toml`、`docs/design/`。

**流程一句話**：`wish{text}` → `apply_wish` 組請求 → `supply`（API 層排進單一佇列、等 ≤ 10 秒）→ `wish_generator`：`match_wish`（願望只在 `<player_input>`）→ 用帶願望的提議器 `make_offer`（釘第 1 個關鍵字、最多 1 張 LLM）→ 引擎驗證（關鍵字、`checked_offer`＋每張帶第 1 個關鍵字）→ 扣 4 任務幣、本週次數 +1 → `pending_offers`（`source="wish"`、`refund=2`）→ 日誌記下引擎收下的 `WishGen`。

## 2. 守則對照

- **守則 7（玩家文字）**：願望只出現在動作（日誌）與兩個 prompt 的 `<player_input>`（`wrap_player_input`：截斷、跳脫）；系統指令與 `<request>` 不含願望；`WishGen` 不存願望。測試：`test_wish_only_in_player_input`（`</player_input><request>` 被跳脫、只有一組標籤）、`test_match_first_try`、`test_proposer_passes_wish_as_player_text`、`test_text_wish_with_keywords_only_uses_composer`（紀錄 JSON 不含願望）。
- **守則 3（LLM 只提議）**：關鍵字由引擎對選單驗；技能數值由預算器補（提議器內）；三選一再過 `checked_offer`＋關鍵字檢查，不合格只丟三選一。
- **守則 1（確定性）**：世界引擎不呼叫 LLM、不讀時間（週次由 `now` 算）；同樣的選單許願兩次結果逐字相同（`test_menu_wish_is_deterministic`）；文字許願用日誌重播逐字相同（`test_text_wish_is_logged_and_replayed_without_llm`）。
- **守則 6**：所有測試用 Mock，不連網路。

## 3. 本機 LLM 延遲實測（唯讀、17 次呼叫）

- 模型：LM Studio `100.87.188.89:1234`、`swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp`、`reasoning_effort = "none"`（`localhost:8001` 沒回應）。設定在 worktree 的 `config/llm.local.toml`（gitignored，沒 commit）。
- 路徑：和遊戲同一條——閃現用 `provider_generators(provider).flash`（LF-2 之後的程式，就是 pregen 背景執行緒跑的那個函式），許願用 `wish_generator`；只把 client 包一層計數（上限 29 次）。測試角色 `build_support`、雲嶺，閃現先無 LLM 閃兩次（小變化）、量第 3 次（大變化）。許願角色在主城。
- 只量時間，沒有做任何平衡量測。

| 項目 | 內容 | 耗時 | LLM 呼叫 | 結果 |
|---|---|---|---|---|
| 大變化閃現 pregen | 順風（`skill_tailwind`） | **5.6 秒** | 3（提議 2.8＋命名 1.5＋1.1） | `llm`；名稱「旋風環護／蔽影閃／迅捷靈光」 |
| 大變化閃現 pregen | 寒霜枷鎖（`skill_frost_shackle`） | **6.5 秒** | 3（3.6＋1.3＋1.2） | `llm`；名稱「寒鎖寂影／凝露結晶／遲來冰爆／凍徹餘韻／凝霜縛形」 |
| 大變化閃現 pregen | 戰歌（`skill_war_hymn`） | — | 0 | 那一招沒有合法的大變化（引擎不扣點、不出題），沒量到 |
| 許願一次 | 「想把敵人凍住再一錘敲碎」→ 冰凍 | **9.6 秒** | 4（對關鍵字 0.65＋提議 4.0＋命名 1.6＋1.3） | `llm`；LLM 卡「寒寂凝核」 |
| 許願一次 | 「讓火焰在地上蔓延，燒得越久越痛」→ 點燃 | **9.5 秒** | 4（0.5＋3.2＋1.4＋0.9） | `llm`；「燼核迴響」 |
| 許願一次 | 「躲在暗處，一擊就讓敵人倒地」→ 隱蔽＋倒地 | **7.0 秒** | 3（0.56＋2.9＋1.4） | `llm`；「幽影之種」 |

說明：

- **大變化閃現**：LF-1 時一題約 9～12 秒（LF-1 報告、LF-3 報告實機逾時），LF-2 之後實際 pregen 一題 5.6～6.5 秒，在 10 秒門檻內；命名併進提議後只剩轉型保底與名稱沒過的那幾個另外命名（這兩題各 2 次命名呼叫）。
- **許願一次 7.0～9.6 秒，貼著 10 秒門檻**。LLM 呼叫合計 4.9～7.5 秒，另外約 2～3.4 秒是同一份三選一的組合器與技能池（另兩張卡）在 CPU 上算。對關鍵字很快（0.5～0.65 秒）；慢的是完整技能提議（2.9～4.0 秒）加上命名（1～2 次）。
- 許願沒有預先生成，**而且和閃現等共用單一佇列**：若前面排著閃現或機遇的 pregen，許願要排在它們後面，實際等待會超過 10 秒 → 被拒（不扣錢）。寫進待決 3。

## 4. 檢查（交件前）

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1570 個檔） |
| `uv run lint-imports` | 0（14 kept） |
| 直接相關測試（見下） | 0 |
| `trpg battle --map open_plain --seed 7` ＋ `battle replay` | 0／0（91 動作、383 事件一致） |
| `trpg content check` | 0 |

測試（`-n 8`，分批）：`tests/world/test_wish.py`（20）、`tests/llm/test_wish_match.py`（8）、`tests/api/test_wish_pregen.py`（6）；既有的 `tests/world/` 存檔、重播、生成內容、開局版號與寫死 `trpg-char/14` 的 14 個檔（290 passed）；`tests/api/test_world_pregen.py`、`test_world_pregen_schedule.py`、`test_offer_prefetch.py`、`test_world_api.py`、`test_world_field_api.py`、`test_pr2a_range_practice.py`、`tests/llm/test_prompts.py`、`test_prompt_prefix.py`、`tests/test_architecture.py`（137 passed）；`tests/api/test_world_story.py`、`test_opportunity_offer_view.py`、`test_season_reset_api.py`、`test_world_store_cache.py`、`tests/content/test_rules.py`、`tests/server`（136 passed）。沒跑全量 `check.py`。

快照：沒有 CLI 輸出快照、OpenAPI 會變（WP-1 不動 API 請求與輸出模型；預測的 key 是「無」，實際也沒有快照失敗）。

## 5. 版號

- `CHAR_FORMAT` `trpg-char/13` → `/14`（`wish_week`、`PendingOffer.refund`、`source` 多 `wish`；`/13` 進 `LEGACY_CHAR_FORMATS` 照讀）。新欄位 `exclude_if` 空值：沒許過願的角色 JSON 只差標頭版號（`test_save_round_trip_and_old_format`）。測試裡寫死 `trpg-char/13` 的 14 個檔一起改成 `/14`。
- `WORLD_RULES_VERSION` 27 → 28（新動作、都不拿退款）；`test_opening_stages.py`、`test_pr2a_range_practice.py` 的字面值跟著改。
- `WLOG_FORMAT` 不升（待決 7）；`LOG_FORMAT` `trpg-battle-log/119` 不升（戰鬥紀錄沒變，三個 `endswith` 測試不用動）；`SAVE_FORMAT` 不升（一輪存檔沒變）。存檔沒有刪。

## 6. 待 PM 決定（照最保守的做法做了）

1. **要不要站在池邊**：只看「在主城區域」（同改外觀）；WP-2 的面板從池子與守池人打開。
2. **每次多少任務幣**：初值 4（退一半 2）；只改 `rules.yaml`。
3. **許願排在單一佇列後面**（第 3 節）：許願一次實測 7～9.6 秒，前面若有閃現或機遇的 pregen 在跑，很容易超過 10 秒而被拒（不扣錢、請改用選單）。WP-2 可以讓許願插到佇列最前面（不打斷正在跑的那一筆），或許願時暫停預測；要哪一種請定。
4. **願望文字上限**：初值 60 字。
5. **選單範圍**：扣掉開局隱藏的關鍵字（`start_hidden`）。
6. **兩個關鍵字怎麼出題**：釘第 1 個（三張都帶）、第 2 個當偏向；實測「隱蔽＋倒地」的 LLM 卡只帶隱蔽。要三張都帶兩個需改候選產生器（`skillgen/candidates.py`），另排。
7. **`WLOG_FORMAT` 不升**：`generated` 多一種紀錄，照「動作 union 多一種不用加」的前例。
8. **對不上關鍵字＝動作被拒**：不由引擎替玩家猜，請玩家改用選單；沒扣錢、沒算次數，但 LLM 已經呼叫過（不記日誌）。
9. **命名步驟不看願望**：只有提議那一步有 `<player_input>`；名稱用中性奇幻（`region=None`）。要讓名稱呼應願望，得把願望也傳進命名 prompt（升 `NAMING_PROMPT_VERSION`）。
10. **許願學到的技能記主城**（`skill_regions`）。
11. **`PregenWaitRequest` 的 `kind` 已在型別別名 `Kind` 多 `wish`**，但等待端點本身（帶願望文字）留給 WP-2。

## 7. 平衡疑慮（只記，不量）

1. 每份最多 1 張 LLM 卡（`llm_cards`），其餘兩張是組合器與技能池：設計「LLM 提議 1～3 招」的下限。強度不受影響（同階預算），只影響「許願感」。
2. 價格 4 任務幣 vs 任務幣來源（新手任務 2、主線一步 3、懸賞 3、今日目標 1）：兩週 4 次就是 16 任務幣，佔比由使用者調。

## 8. 需要使用者決定

1. 任務幣價格（初值 4）。
2. 一次許願只請 LLM 出 1 招是否接受（3 招都由 LLM 出，以目前實測約要 15～20 秒，超過 10 秒門檻）。

## 開發 PM 裁定

- 接受，已合併。規格 `PhaseWP計畫.md` 三段照用。
- 待 PM 決定：
  - 1、4～10：照 agent 的做法維持。規則解讀的部分（只要在主城區域、願望上限 60 字、對不上關鍵字就拒絕不扣錢、只釘第 1 個關鍵字）轉交玩法 PM 確認，要改再做。
  - 2：價格 4 幣、退 2 是數值，交數值工坊由使用者調。
  - 3：採用。WP-2 讓許願在 pregen 佇列插隊排最前面，因為實測 7～9.6 秒，貼著 10 秒門檻。
- 「一次只請 LLM 出 1 招」：設計是 LLM 提議 1～3 招，1 招在範圍內，不另問使用者。
- 延遲實測：LF-2 之後大變化閃現 5.6～6.5 秒，已在 10 秒門檻內。
