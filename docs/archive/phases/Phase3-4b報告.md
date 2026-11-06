# Phase 3-4b 報告：反應設定、反應詢問視窗、環境預告、隊友快捷指令、連鎖預覽

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 261f5c3 | 引擎：`ReactionRule.mode` 新增 `off`；動作 `set_reaction_mode`（事件 `reaction_mode_set`、`reaction_mode_problem` 驗證函式，不列入 `legal_actions`）；`UnitView.reaction_rules`、`ap_carry`；`SkillCard.cost` 不再出現「AP None」；`tests/engine/test_reaction_mode.py` |
| 80404dd | API：`BattleResponse.telegraph`、`orders_ignored`；`PreviewOut.min_events`／`max_events`；`narrative/telegraph.py`、`api/telegraph.py`；重新產生 `openapi.json`／`schema.d.ts`；`tests/api/test_reactions_telegraph.py` |
| 4ea714a | 前端：反應設定面板、正式反應詢問視窗（含「之後都自動」）、環境預告（格上標記＋側欄）、隊友指令面板、連鎖預覽、HUD 保留 AP；vitest 新增 18 個測試 |
| （本報告） | 報告 |

## 2. 驗收條件逐條

1. **反應設定三段切換；`off`／`prompt` 行為與重播一致**：通過。`tests/engine/test_reaction_mode.py`（`test_off_mode_does_not_trigger`、`test_prompt_mode_pauses_and_resumes[True/False]`、`test_rejected_when_not_own_turn_or_unknown_rule_or_paused`、`test_set_reaction_mode_costs_nothing_and_keeps_the_turn`）；`tests/api/test_reactions_telegraph.py::test_prompt_and_off_modes_replay_identically`（3 張地圖 × prompt／off，打完整場，匯出紀錄含 `set_reaction_mode` 步驟，`replay` 與 `trpg battle replay`（`cmd_replay`）皆「重播驗證通過」）、`test_prompt_mode_produces_decisions_somewhere`（確實出現詢問）。
2. **設為詢問後在瀏覽器遇到詢問視窗，接受與拒絕都正確**：實作者在內建瀏覽器確認（oil_depot、種子由預設、火焰流）：把「格擋」「藉機攻擊」設為「詢問」→ 結束回合 → 敵人暴擊攻擊主角時跳出視窗「反應詢問：格擋」，顯示觸發事件文字、說明、代價「耐力 10」，戰場上觸發者被洋紅雙框標示；勾「之後都自動」按接受後，紀錄出現「火焰流英雄 反應：格擋（耐力 −10）」，HUD 反應變「已用」，輪到主角時自動補送 `set_reaction_mode`（紀錄「將反應 格擋 設為自動」）。拒絕路徑由 API 測試（`accept` 交替）涵蓋，瀏覽器未實際按「拒絕」。待 PM 確認觀感。
3. **環境預告顯示於格子上，與下一次環境回合一致（API 層測試）**：`test_response_telegraph_matches_the_next_environment_round`（以 `_fire_field` 場地注入工作階段，回應的 `telegraph.changes` 的 (種類, 位置) 集合 ＝ 實際跑完該輪環境回合的事件）；`test_telegraph_ignores_the_enemys_hidden_traps`。瀏覽器：用「火焰箭」點燃油面後，側欄列出「油桶 (5, 3) 將爆炸」「表面變化 (6, 4)：油 → 火焰」「盜賊弓手將受到 13 點傷害」「第 3 輪結束時援軍出現：盜賊」，標記為 爆／面／傷。格上圖示的外觀（半透明外框＋右上角小徽章）只確認程式無誤，**待 PM 在瀏覽器目視**。
4. **快捷指令可下達、取消；紀錄的 `orders`**：`test_orders_ignored_reports_orders_that_cannot_run`（下達集火、目標倒下後 `orders_ignored` 帶原因「已倒下」、取消）；既有 `tests/api/test_routes.py` 的 orders 測試仍過。瀏覽器：按「集火」後點敵人，側欄顯示「集火：d 盜賊頭目」，按「取消指令」清空。隊友行為待 PM 試玩。
5. **預覽列出連鎖事件；`SkillCard` 不再出現「AP None」**：`test_preview_lists_filtered_chain_events_with_text`、`test_skill_cards_never_say_ap_none`、vitest `chain preview`；瀏覽器：滑過火焰箭目標顯示「可能發生的連鎖：確定 (5, 4) 的油變成了火焰」。前端 `targeting.ts` 已移除 `AP None` 暫時處理（被動／反應技改以 `ap_cost === null` 顯示「被動／反應」）。
6. **網頁打完一場的紀錄以 `trpg battle replay` 重播通過（含 `set_reaction_mode`）**：同第 1 條的 API 測試（`cmd_replay` 輸出「重播驗證通過」）。
7. **`check.py` 全過；複雜度 noqa 不增加**：`uv run python scripts/check.py` 全部通過（ruff、format、mypy、lint-imports、pytest、client install／typecheck／test）。複雜度類 noqa 前後皆 20 個（無新增、無移除）。

保留 AP（0.9 #1）：引擎有 `ap_carry`（結束回合時保留、下回合開始併入）。已加進 `UnitView.ap_carry`；HUD 在別人回合顯示「AP 0（下回合保留 +1）」，自己的回合 `ap_carry` 為 0（已併入 AP）。

## 3. 複雜度 noqa

新增：無；移除：無；總數 20 → 20。

`LOG_FORMAT`：**未升**（維持 `trpg-battle-log/11`）。新增的動作、事件與 `off` 模式只是擴充；舊紀錄仍可由新引擎重播，沒有舊行為改變。

## 4. 修改既有測試期望值

- `tests/narrative/test_skills_text.py::test_every_skill_has_a_card_with_one_line_per_effect`：原本斷言 `card.cost[0] == "AP {ap_cost}"`，被動／反應技（`ap_cost` 為 `None`）改為斷言卡片代價中沒有以 `AP` 開頭的片段（修 0.9 #4）。
- `tests/api/test_routes.py::test_preview_returns_the_numbers_and_does_not_change_the_session`：預覽回應的鍵集合加入 `min_events`、`max_events`。
- 前端：`testFixtures.ts` 的 `unit()` 補 `reaction_rules`、`ap_carry`；`previewText.test.ts` 的 `base` 補 `min_events`／`max_events`；`fixtures/oil_depot_seed3.json` 重新存檔（回應多了新欄位）。

## 5. 待 PM 決定

1. **「AP None」只在 `skill_card` 修**：`cost_parts` 本身未改，因為 CLI 快照（`skills_show_all`）含 `代價 AP None` 的被動技能，改了會讓 CLI 輸出變動。CLI 仍顯示「AP None」，需要時另行修並重錄快照。
2. **`set_reaction_mode` 走 `POST /actions`**（不另設端點）；回應 `steps` 只有該步。紀錄中多一種步驟與事件 `reaction_mode_set`（有中文文字）。
3. **同一反應的多條規則一起改**（例如格擋有兩條觸發事件）；介面每個反應只列一列。
4. **「之後都自動」只在接受時有效**，做法：記在前端佇列，輪到主角（可送動作）時補送 `set_reaction_mode auto`；重新整理頁面會遺失佇列。
5. **詢問視窗不遮住戰場**（固定在左下，不用全螢幕遮罩），否則看不到被標示的觸發者。
6. **環境預告以「我方看得見的狀態」模擬**（先 `strip_hidden_traps`），所以若敵方隱藏陷阱會影響環境回合結果，預告會與實際略有出入（可接受的保守做法）。援軍與下一輪地圖事件視為公開資訊。
7. **預告標記每格一個圖示**（依優先序：爆、倒、傷、燃、毀、援、地、面），說明列在側欄與滑過；圖示與顏色在 `battle/telegraph.ts`，之後可換。
8. **連鎖預覽只列特定事件類型**（爆炸、點燃、摧毀、表面／地形變化、墜落、致命地形、陷阱觸發）的中文文字，並隱藏與之重複的 `確定／可能` 結果行；清單在 `previewText.ts` 的 `CHAIN_EVENT_TYPES`。
9. **隊友指令**：只做全隊指令（`team_orders`）；守位半徑固定 1；「保護」按鈕後點隊友或按「保護主角」；指令面板在敵人回合播放期間停用；被忽略的指令是依目前狀態即時計算（`orders_ignored`），因為下達時已驗證，`OrderRecord.ignored` 實際上恆為空。
10. 瀏覽器工具的滑鼠座標有偏移（同 3-4a），本次以派送指標事件驗證格子點選；真實滑鼠請 PM 一併確認。

## 6. 代表性輸出

- 反應詢問（oil_depot）：`反應詢問：格擋`／`盜賊1 攻擊 火焰流英雄：…自然 20，暴擊！`／`代價：耐力 10`；接受後紀錄 `⟳ 火焰流英雄 反應：格擋（耐力 −10）`。
- 設定紀錄：`火焰流英雄 將反應 格擋 設為每次詢問`、輪到自己時 `…設為自動`。
- 預告（第 2 輪）：`油桶 (5, 3) 將爆炸`、`表面變化 (6, 4)：油 → 火焰`、`第 3 輪結束時援軍出現：盜賊`。
- 連鎖預覽：`確定　(3, 2) 出現了火焰`／`確定　木箱 (3, 2) 著火了…`／`可能　＊ 木箱 (3, 2) 被摧毀！`。
- API 新欄位：`BattleResponse.telegraph {round, changes[{kind,pos,…,text}], burning[], upcoming[]}`、`orders_ignored[]`、`UnitView.reaction_rules[{reaction,name_zh,description_zh,event,trigger_zh,mode,unless_stamina_below,stamina_cost,mana_cost,hp_cost_permille}]`、`UnitView.ap_carry`、`PreviewOut.min_events／max_events`。
