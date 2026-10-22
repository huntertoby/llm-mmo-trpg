# Phase 3-26b 完成報告：3 級分歧進化（無 LLM）

> 實作者：implementer（opus）。規格：`docs/phases/Phase3計畫.md` 28 開頭、28.2、28.3；`docs/design/06-技能.md` 6.28、6.27（關鍵字只用專屬規則，26.3）、6.12、6.6。
> 分支：`worktree-agent-a8ae0976984539a9c`（從 main 的 `f8a1fa3` 分出），未 push、未合併。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `2d9a0d8` | 用法統計 `trpg.skillgen.usage`、進化模板 `content/skill_evolution.yaml`＋schema、兩支推導 `trpg.skillgen.evolution`、`RunState.skill_usage／evolutions`、3 級門檻與二選一（`growth.py`）、AI 代打、存檔 `trpg-run/5`、測試 |
| `7bf7fbb` | API（`HeroOut.evolutions`、`SkillLevelInfo.uses／blocked_text／evolved_from_zh`、`SkillGrowthOut.evolve_uses`、選擇的 `evolve`）、CLI 進度印出進化、OpenAPI 與 `schema.d.ts` 重產、API／CLI 測試 |
| `851d4ca` | 前端：升到 3 級時兩支進化的技能卡比較（`EvolutionCompare`）、門檻擋住時顯示原因、送出 `evolve`、vitest |
| `2882b61` | 截圖 `docs/phases/img/3-26b-*.png` |
| （本報告） | `docs/phases/Phase3-26b報告.md` |

## 2. 驗收逐條

| # | 驗收項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 用法統計（確定性，從戰鬥事件累積在一輪存檔） | 通過 | `tests/roguelite/test_evolution.py::test_usage_is_deterministic_and_counts_every_cast`（同輸入兩次相同；次數 ＝ 重播出的 `skill_used` 事件數；地形總數 ＝ 次數）、`test_finish_battle_accumulates_usage_into_the_run`；存檔欄位 `run.skill_usage` |
| 2 | 門檻（3 級要用過 N 次；未達不能升並顯示原因） | 通過 | `test_level_three_needs_enough_uses_and_shows_why`（「要在這一輪用過 3 次…目前 2 次」，2 級不受影響）；API：`tests/api/test_skill_growth_api.py::test_spend_points_over_the_api_updates_cards_and_stays_on_the_node`（422 原因 ＝ 卡片 `growth.blocked_text`）；vitest `evolution.test.ts`「用過的次數不夠時不能升到 3 級，並說明原因」 |
| 3 | 兩支的推導（加深／橋接） | 通過 | `tests/skillgen/test_evolution.py`：`test_deepen_reinforces_the_skills_own_keyword_and_bridge_follows_the_partner`、`test_bridge_prefers_partners_then_targets_then_held_keywords`、`test_without_any_bridge_keyword_the_second_option_falls_back_to_deepen`、`test_single_target_usage_prefers_reshaping` |
| 4 | 進化後照同階預算驗證；不合格的模板不出現 | 通過 | `test_every_option_passes_the_validator_within_the_same_tier_budget`（全部 1 階主動技 × 3 種用法：`validate_skill` 零違規、比例 0.70–1.00、階級／種類／AP 不變、不會變傳說，>100 支）、`test_templates_that_do_not_fit_never_appear` |
| 5 | 名稱用組合式；全程確定性 | 通過 | `test_same_request_gives_the_same_options_and_names_are_composed`（「崩倒・火焰箭」）；`test_the_save_round_trips_and_a_full_run_is_deterministic`（整輪 AI 代打兩次相同） |
| 6 | 玩家二選一、進化結果跟著技能走（存檔）；重選不做 | 通過 | `test_evolving_requires_a_pick_and_swaps_in_the_evolved_skill`（沒選、索引錯、多選皆拒絕；裝備位置不變、等級與統計換到新 ID、紀錄寫入、原技能不再進候選）、`test_respec_keeps_the_evolution_and_it_never_evolves_twice`；API `tests/api/test_evolution_api.py`（2 個） |
| 7 | 存檔 | 通過 | `trpg-run/5`；`/1`～`/4` 拒絕並提示開新一輪（`tests/roguelite/test_save.py`、`test_runs_api.py`） |
| 8 | 整場重播 | 通過 | `test_a_mid_battle_save_after_an_evolution_replays_bit_for_bit`（進化後的戰鬥中存檔，重播狀態逐位元相同、續打結果相同）；`tests/roguelite/test_save.py` 全部通過 |
| 9 | `trpg run auto` 跑到至少一次進化 | 通過 | `tests/cli/test_run_cli.py::test_run_auto_reaches_a_branching_evolution[1,4]`；手動：`trpg run auto --seed 1`「分歧進化：潑水瓶 → 潮濕・潑水瓶（skill_splash_flask_evo_intensify_wet） Lv.3（加深）」、`--seed 4`「颶風踢 → 擴散・颶風踢」 |
| 10 | 網頁：升到 3 級時顯示兩支的技能卡比較（組裝式圖示） | 通過 | 截圖 `3-26b-compare.png`（魔劍斬：加深「擴散・魔劍斬」錐形 vs 橋接「衝撞・魔劍斬」撞擊加碼）、`3-26b-levelup.png`（升級畫面整體）、`3-26b-evolved-card.png`（進化後技能卡：Lv.4、「進化自 魔劍斬」）、`3-26b-evolved-full.png`（英雄面板） |
| 11 | vitest | 通過 | `client/src/run/evolution.test.ts`（4 個）；全部 62 檔 657 個 |
| 12 | `check.py` 全過、`pnpm build` 成功 | 見第 9 節 | |

## 3. 設計摘要

### 3.1 用法統計（`trpg.skillgen.usage`）

- `finish_battle` 以 `battle_setup ＋ 種子 ＋ 步驟` 重播這場（純函式，`progress.battle_usage`），收集主角的 `skill_used` 事件，只統計主角裝備中的技能，累加到 `RunState.skill_usage`（技能 ID → `SkillUsage`，依 ID 排序）。
- `SkillUsage`：`uses`、`targets`（施放當下站在影響格上的其他存活單位）、`distance`（施放者到最遠影響格的曼哈頓距離）、`kills`（施放後倒下的目標）、`target_keywords`（目標身上的狀態與腳下表面，以推導表「利用」規則的 `target_has_status`／`target_on_surface` 對到關鍵字，只看專屬規則；一個目標每個關鍵字算 1）、`terrain`（施放者所在格地形）、`partner_makes／partner_uses`（同一場、同一單位的上一招與下一招的專屬關鍵字）。全部整數；平均用 ‰（`avg_targets_permille`）。
- 放在 `trpg.skillgen`，大世界可直接呼叫。

### 3.2 進化模板（`content/skill_evolution.yaml`）

| 模板 | 分支 | 改法 | 名稱前綴 |
|---|---|---|---|
| `intensify` | 加深 | 加深這招的關鍵字：已有同一個製造效果 → 持續 +1；否則補上該關鍵字的製造效果 | 關鍵字前綴（灼燃、潮濕…） |
| `reshape` | 加深 | 換形狀（依平均距離先試遠／近：直線 3、方陣、錐形 2、十字）；改試骨架 `area` | 擴散 |
| `extend` | 加深 | 狀態、表面、區域都 +1 回合（硬控不延長） | 恆久 |
| `delayed_burst` | 加深 | 第一個傷害改成延遲爆炸（1 輪、半徑 1；只有法術技合格）；改試骨架 `control` | 延爆 |
| `kill_chain` | 加深 | 第一個傷害加 `on_kill: refund_ap 1` | 收割 |
| `bridge_exploit` | 橋接 | 加「目標帶有某關鍵字時加碼」的傷害（`grafts.<k>.uses`）；改試骨架 `combo` | 關鍵字前綴 |
| `bridge_imbue` | 橋接 | 加製造某關鍵字的效果（`grafts.<k>.makes`） | 關鍵字前綴 |

- `grafts`：9 個關鍵字的製造／利用嫁接效果（召喚物兩邊都沒有、高處沒有製造，見待決 #4）。戰場變奏（6.24）未列。
- 名稱「{前綴}・{原名}」；ID `<原 ID>_evo_<模板>[_<關鍵字>]`；`provenance.origin: level_up`、`parents: [原 ID]`。

### 3.3 挑選規則（`trpg.skillgen.evolution.evolution_options`）

1. **加深**：關鍵字＝這招自己的專屬關鍵字中，目標身上最常出現的一個（並列取推導表順序；沒有專屬時看全部）。模板依「偏好成立的排前面、其餘照資料檔順序」：`intensify`（目標身上常有該關鍵字）、`reshape`（平均目標 < 1.5）、`delay`（平均距離 ≥ 3）、`on_kill`（擊倒過）。第一個合格的就是加深。
2. **橋接**：這招沒有的關鍵字，依「前後搭配次數 → 目標身上次數 → 主角其他技能持有招數 → 推導表順序」排序，最多試 3 個；搭配的技能製造它（或目標身上常有）→ 先試 `bridge_exploit`，否則先試 `bridge_imbue`。進化後（專屬規則）必須真的帶該關鍵字。
3. 橋接做不出來 → 第二個合格的加深模板（`fallback=True`，卡片標「橋接做不出來，改給第二種加深」）；都做不出來 → 0～1 支。
4. **合格**：模板套用後，傷害／延遲爆炸／治療／護盾的骰子或武器倍率、推拉距離成為旋鈕，以組合器的調整器 `composer_tuning.tune` 調到組合器區間（0.75–0.95），再過 `validate_skill`（全部檢查）。依序試「原骨架 → 模板骨架」×「原代價 → 冷卻 +1 → +2（上限 5）」。稀有度取原本與新內容需要（原語、條件、骨架、效果個數）的較高者，需要傳說時不合格。
5. 種子：`Rng(一輪種子).fork("evolve/<技能 ID>")`；同一個 `RunState` 必得同樣的兩支（API 顯示與送出時重算一致）。

### 3.4 一輪（`trpg.roguelite`）

- `growth.raise_problem`：升過 `evolve_level` 且未進化 → 需 `uses ≥ evolve_uses`（`skill_growth.yaml`：`evolve_uses: 3`，`evolve_uses_world: 10` 先存不用）。
- `spend_points(…, evolve)`：經過進化且有選項時必須選；沒有任何合格進化時照常升級。`SpendChoice.evolve`、`LevelUpChoice.evolve`（技能 ID → 索引）。
- 進化後：裝備位置換成新 ID，定義進 `generated_skills`，等級與用法統計換到新 ID，`RunState.evolutions[新 ID] = EvolutionRecord(base_id, base_name_zh, branch, template, keyword, fallback)`；候選排除原技能。重配只退點數、不動進化；已進化的技能再升過 3 級不再進化。引擎不需改（進化後就是一般的生成技能）。
- AI 代打：門檻沒到停在 2 級、點數給下一招；進化一律選第一支（加深）。

### 3.5 API／前端（只新增欄位）

- `HeroOut.evolutions`（已達門檻、未進化的裝備中主動技能 → 兩支：`index`、`branch`、`label_zh`、`template`、`keyword`、`summary_zh`、`fallback`、`card`）；`SkillLevelInfo.uses／evolve_uses／evolved_from_zh／blocked_text`，3 級的 `next_text` 改為「分歧進化：加深／橋接二選一（用過 x/3 次）」；`SkillGrowthOut.evolve_uses`。
- 前端：`SkillGrowthPanel` 的列在草稿升到 3 級時展開 `EvolutionCompare`（兩張 `SkillCardView` 並排、單選），沒選時「確認分配」／升級「確定」不可按；門檻沒到時＋按鈕停用並顯示原因。`styles.css` 只在檔尾新增 `.evo-*`、`.growth-blocked`。

## 4. 存檔與 `LOG_FORMAT`

- 存檔 `trpg-run/4` → **`trpg-run/5`**（`run.skill_usage`、`run.evolutions`）；`/1`～`/4` 拒絕並提示開新一輪。
- **`LOG_FORMAT` 不變（`/45`）**：引擎沒有改動；`SkillGrowthRules` 多了兩個有預設值的欄位（嵌在規則包裡），舊戰鬥紀錄照樣讀得回、結算不變，所以沒有遞增。若 PM 認為規則包欄位變動也要遞增，請在合併時處理。
- `ruleset_hash` 因 `skill_growth.yaml` 變動而改變（戰鬥中的舊存檔本來就因 `/5` 被拒）。

## 5. Phase 4 接 LLM 提議時的接點

- `trpg.skillgen.evolution.EvolutionRequest`（技能、`SkillUsage`、持有關鍵字、種子）就是給 LLM 的提示材料；LLM 可在「模板範圍內」提議兩支的內容、名稱與描述。
- 驗證沿用 `_tuned`／`_finish` 的同一條路：pydantic `SkillDef` → 調整器（同階預算）→ `validate_skill`；另需檢查橋接帶到指定關鍵字（`carries`）。建議新增 `propose_evolutions(llm_client, request) -> tuple[Evolution, ...]`，不合格時退回 `evolution_options`（無 LLM 版）。
- 名稱與描述替換點：`_label`（組合式名稱）與 `narrative.concept`；`Evolution.summary_zh` 是卡片的一句話。
- roguelite 端只認 `Evolution`，`growth.evolution_choices` 換成 LLM 版即可，不需改存檔格式（`EvolutionRecord.template` 可記 `llm`）。

## 6. 新增的複雜度 noqa

無（`src` 沒有新增任何 `noqa`）。`library.load_library` 因多一段載入超過 `PLR0912`，改用條件運算式＋`_check_evolution` 拆出；`_drafts` 用對照表分派避免 `PLR0911`。

## 7. 覆蓋率（目前內容，`SkillUsage` 範例用法下）

- 主動技能 146 招：兩支 77、一支 22、零支 47；1 階 125 招：兩支 62、一支 19、零支 44。
- 各模板出現次數：`bridge_exploit` 64、`reshape` 47、`intensify` 31、`bridge_imbue` 17、`kill_chain` 7、`extend` 6、`delayed_burst` 4；橋接退回加深 5 次。
- 零支的多為輔助、位移、召喚、牆、增益類（例：戰歌、召喚靈體、石牆、飛行）：它們沒有可調的強度旋鈕，模板的改動一加上去就超出預算或違反骨架。

## 8. 其他變更

- `tests/roguelite/helpers.py` 的 `VICTORY` 改成 `("build_fire", 1)`（進化改變了 AI 代打的走向，原本的種子 0 不再打完）。3-27 改了技能內容後可能又要換，合併時請注意。
- 3-26a 的 `tests/roguelite/test_skill_growth.py` 改用「關掉進化」的內容庫（沒有模板、門檻 0），保持 3-26a 的原意；`tests/api/test_skill_growth_api.py` 的花點測試改升到 2 級並檢查 3 級的門檻原因。

## 9. 全量檢查

- `uv run python scripts/check.py`（一次全量）：ruff、format、mypy、lint-imports、pytest（4113 個，7 分鐘）、client install／typecheck／vitest（62 檔 657 個）**全部通過**。
- `corepack pnpm -C client build`：成功（只有 chunk 大於 500 kB 的既有警告）。
- 截圖伺服器用 `trpg serve --port 8139`（`TRPG_SAVE_DIR` 指到暫存資料夾，沒有動 8000），截圖用 headless Chrome＋CDP（node 腳本，未進 repo），存檔以 `auto_play` ＋ `write_save` 準備（`build_push` 種子 0，第 4 級升級時的魔劍斬）。

## 10. 待 PM 決定

1. **沒有任何合格進化時照常升到 3 級**（不進化、不需選）：目前約 1/3 主動技能（多為輔助、召喚、牆、增益）會這樣。要不要另補「輔助類」進化模板（例：範圍＋1、目標＋1 友方、冷卻折抵），或讓這類技能 3 級改給別的獎勵？
2. **進化用冷卻折抵預算**：模板加的內容超出預算時，允許冷卻 +1、+2（上限 5）以換預算（6.5 的代價折抵），強度不增加。可接受嗎？
3. **稀有度隨內容提高**（例：普通 → 稀有，因加了條件或效果數超過普通上限），不會變傳說；6.12「稀有度不加強度」仍成立（同階預算）。
4. **嫁接表的缺口**：召喚物（製造與利用）、高處（製造）沒有簡單的嫁接效果，橋接不會往這兩個方向。請玩法 PM 決定要不要補。
5. **統計的定義**：目標＝施放當下站在影響格上的其他存活單位（含友方）；距離＝到最遠影響格；前後搭配＝同一場同一單位的上一招與下一招（不分回合）。目標的關鍵字狀態只看專屬規則的 `target_has_status`／`target_on_surface`（撞擊、高處、隱蔽的「狀態」沒有統計）。
6. **重配保留進化**：營火重配只退點數，進化結果不變，已進化的技能再升過 3 級不會再進化（規格：重選不做）。
7. **用法統計跟著技能**：進化後統計換到新 ID；進化前的原技能不再出現在候選。
8. **AI 代打一律選加深**、門檻沒到時點數給下一招；只是讓 `run auto` 走過進化，不代表平衡。
9. **`LOG_FORMAT` 未遞增**（見第 4 節）；存檔 `/5`。
10. **平衡未模擬**：進化後的調整器以隨機目標比例（0.75–0.95）重新配強度，可能比原技能略弱或略強；沒有跑 `sim matrix`。
