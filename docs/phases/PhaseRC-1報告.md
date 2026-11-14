# Phase RC-1 報告：組合器補配方

> 2026-11-15，main `2de4893bf` 起的分支。規格：派工 prompt（專案 PM 轉使用者「先補這個」）＋ `docs/玩法PM交接.md` 4.1.19 ＋ RC-0 報告第 4 節；中途加派第 7 項（Q4，使用者回覆「A」）。
> 資料：`docs/phases/RC-1資料/`（`census.json`、`census.md`＝改後盤點；`對照.md`＝改前改後；`樣本.md`＝技能樣本）。

## 0. 給使用者的白話結論

- **補起來了**：RC-0 找到「規則允許、組合器做不出」的洞，這段補掉大半。盤點 408 個存在的格子：**空格 142 → 72、薄格 14 → 4**；遊戲會出題的格子裡**空 102 → 32、薄 14 → 4**。
  - 連擊、怒氣、專注、氣、高處、潮濕的被動與反應全部從空變正常（每格 200 個種子全部合法，不同設計 32～129 種）。
  - **Q12（epic 被動＋高處）補到了**：1～4 階都 200／200 合法、100 多種設計；LB 第 12 題的退回路徑也改由組合器做（原本退回手寫的鷹眼）。
  - 召喚物主動：2～4 階從「只有獻祭」的薄格變正常（200 合法、13 種設計）；1 階從空變成 200 合法，但只有兩種基本召喚物、盤點的設計鍵分不出來，仍算薄格（待決 6）。
- **剩下的 32 個會出題的空格**：形態 20 格（內容刻意交給手寫池，不算洞），以及**召喚物的被動與反應 12 格**——伴生、護主程式寫好了，但「召喚到身邊」在關鍵字推導表沒有規則、推不出召喚物；「召喚物倒下時」要改引擎並放寬驗證。照「要改規則就先不做」停下，列待決 1、2。
- **規則與預算都沒改，引擎沒改**；戰鬥 46 場逐字相同。新配方都用獨立亂數，沒抽到新東西的種子技能不變。
- **第 6 項**（指定關鍵字只認專屬規則）會改「種子 → 技能」：三選一、許願的 3 個固定種子測試換了種子（掃描後三選一三張齊全 29 → 31／40）。
- **Q4**：照規則不補（common 沒有召喚寫法、遊戲也不出這題）。加做第 7 項：評估題的可行檢查改用遊戲出題的同一個檢查，LB 第 4 題從「1 階 common 召喚物」換成「1 階 rare 冰凍」，**之後 LB 第 4 題和舊數據不可比**，其他 19 題不變。

## 1. 每項改了什麼

| # | 項目 | 做了什麼 | 檔案 |
|---|---|---|---|
| 1 | 召喚物主動技 | 組合器會做整招召喚：1 階只抽兩種基本召喚物；2 階起抽 6.29.5 清單 16 種＋元素之靈（不抽殘影分身）；指定關鍵字時只抽固有關鍵字相符的（沒有相符的才全抽）。AP 1、單格（射程照白板 3 或 4），持續照 `summon` 原語的旋鈕（1～4 輪，由強度調整決定），代價變化照白板的 7 種冷卻／法力；沒有附帶效果、外觀用召喚物既有的 | `skill_composer.yaml` `recipes.summon_units`／`summon_costs`（沿用白板的 `*summon_cooldowns`）、`skeletons/summon.yaml`（`hand_written_only` → `explicit_only_active`）、`composer_recipes.summon_drafts`、`random_composer._compose_summon` |
| 2 | 被動累積層數 | 核心照舊被動抽（不抽附帶）＋對自己 `add_stack` +1（沒有旋鈕，固定 1）、`max_per_round: 1`；時機：連擊、氣 `on_hit`；怒氣 `on_damaged`；專注 `on_turn_end`＋`self_on_high_ground` 或 `on_hit`＋目標被標記。利用：條件 `self_stack_at_least`（N 照白板：連擊 3、其餘 2），層數不扣。不做消耗 | `recipes.stack_events`／`stack_counts`、`composer_recipes._passive_plan` |
| 3 | 被動的條件 | 高處：有另一方的時機一半抽 `height_advantage`（效果作用在另一方），其餘與沒有另一方的時機抽 `self_on_high_ground`。利用型條件：倒地（目標倒地）、標記（目標被標記）、潮濕（目標站在水裡），只配有另一方的時機（不含擊倒時），效果作用在另一方。另補潮濕被動「受傷時在自己腳下造水」（06 6.34.1 3W-4b） | `recipes.exploit_conditions`、`_passive_plan` |
| 4 | 被動的召喚物 | **程式做好但沒有生效**：伴生（`on_battle_start`＋`summon_beside`，照 TF-1 的縮小幅度與代價）寫好了，但 `summon_beside` 在關鍵字推導表裡沒有規則（推不出「召喚物」），要補推導規則才帶得到關鍵字 → 待 PM 決定 1。召喚物倒下時（`on_summon_downed`）**沒做**：引擎只對裝備詞條發這個時機，被動技能不會觸發，效果（獻祭原語）也只准主動技能用，要放寬驗證＋改引擎 → 待 PM 決定 2。「命中時給號令」照 4.1.19 不做 | `composer_recipes._companion_drafts`、`beside_keywords` |
| 5 | 反應技 | 層數：原本的反應效果（不抽附帶）＋ `add_stack` +1，或條件 `self_stack_at_least`；事件照組合器原本的四種抽（反應本來每回合 1 次）。高處：一半 `self_on_high_ground`，一半 `height_advantage`（固定走「對觸發者」的單體分支，比的是攻擊者）。潮濕：被攻擊（`hit_by_attack`／`hit_by_melee`）後對攻擊者出手並在他腳下造水。護主同第 4 項（寫好、等推導規則） | `composer_recipes.reaction_drafts`、`composer_parts.build_reaction_effects` 加 `second`／`branch` 參數（預設值＝原行為） |
| 6 | 指定關鍵字只認專屬規則 | `_compose_with_keyword` 改用 `has_keyword(..., exclusive_only=True)`（和退回路徑、三選一一致）；`has_keyword` 加 `exclusive_only` 參數 | `random_composer.py`、`keywords.py` |
| 7 | Q4 評估題 | `cli/llm.py::_feasible` 先要求 `keywords_reachable`（和遊戲出題同一個檢查），評估不再出遊戲不會出的題 | `src/trpg/cli/llm.py` |

**亂數**：要不要用新配方一律用獨立串流——被動 `composer.passive.recipe`、反應 `composer.reaction.recipe`（`pick_recipe`，機率 250‰；指定關鍵字時只在有配方帶得到它時才擲），整招召喚是 `_wants_special` 的最後一項 `composer.summon`（60‰，前面的特殊骨架都沒抽中才擲）。組法本身也用獨立串流（`composer.<種類>.recipe.build`、`composer.summon.build`），組不出合格技能就退回原本的組法、用沒動過的原亂數串流，所以**沒抽中新配方的種子逐字不變**（`test_seeds_without_a_recipe_are_unchanged`、`test_plain_active_seeds_without_summon_are_unchanged` 鎖）。三個機率是原型值，寫在 `skill_composer.yaml` 的 `recipes`。

**第 6 項改「種子 → 技能」**：指定關鍵字的組合，原本第一個「含通用規則帶到」的變體就交出去（交出去會被退回路徑／三選一拒絕），現在要第一個「專屬規則帶到」的變體。原本第一個變體就專屬帶到的種子不變；其餘改成更後面的變體。影響所有指定關鍵字的組合器呼叫（三選一候選、開局組合技、退回路徑①、許願）。

## 2. 引擎改動

**沒有改引擎**。逐項確認：

- `self_stack_at_least`、`self_on_high_ground`：已有（KW-1、KW-2），被動的技能條件照一般流程判斷。
- 被動觸發的 `max_per_round`：已有（`TriggerSpec.max_per_round`，`skill_triggers._usable`）。
- `height_advantage` 對觸發另一方：引擎判被動的技能條件時，對象是 `trigger.target` 指的單位（`target: other` 時是另一方；`self` 時是持有者自己，`height_advantage` 永遠不成立）。所以組合器只把目標型條件配給 `target: other`（效果作用在另一方）——不改引擎就符合 4.1.19「比的是持有者和另一方」。`target: self`＋目標型條件（例：「被比你低的人打到時，給自己護盾」）要改引擎的判斷對象 → 待 PM 決定 3。反應技形狀 `single` 時對象本來就是觸發者，不用改。
- `on_battle_start`、`summon_beside`：已有（TF-1）。
- `on_summon_downed` 給被動技能：**沒有**（見第 1 節第 4 項），沒做。

## 3. 快照與固定種子（先預測，再對照）

改動不碰引擎、內建技能與規則包（`Ruleset` 不含骨架與 `skill_composer.yaml`），所以戰鬥、技能列表、parity 夾具預測都不變；會變的只有「經過組合器」的固定種子：指定關鍵字的組合（三選一、許願、退回路徑）與 LLM 評估題的輪替。除了圖示夾具的 1 筆（下表），**沒有重產任何快照或夾具**。

| 鍵／測試 | 預測 | 實際 | 處理 |
|---|---|---|---|
| CLI 輸出雜湊 `cli_output_hashes.json`（`skills_list`、`skills_show_all/00～15`、7 場戰鬥） | 不變（技能內容與戰鬥沒動） | 不變（`tests/cli -m slow` 44 passed，含 `test_run_cli` 固定種子一輪） | 無 |
| `llm_propose_mock.txt`（`--mock -n 3 --seed 0`） | 不變（前 3 題沒換；Mock 答案取自手寫池） | 不變 | 無 |
| parity 夾具 `refactor_3wr2.json`（完整強度、升階、閃現） | 不變（不經過組合器） | 不變（928 passed） | 無 |
| 戰鬥不變比對 46 場（8 張圖 × 種子 1、2＋`rift_gate`、`cloud_summit`、`molten_heart_pit` × 種子 3～12；地圖預設陣容、效用 AI、`max_rounds=30`；改前＝`2de4893bf` 用 `git archive` 解開、`PYTHONPATH` 指過去） | 全同、規則包雜湊也不變 | `battles=46 events=19129 different=0 ruleset_hash_changed=0`（比事件、動作、去掉規則包的最終狀態；規則包沒變所以不用剝） | 無 |
| `test_pinned_keyword.py::test_all_three_carry_the_pinned_keyword[7]` | 會變（三選一候選亂數） | 種子 7 只剩加深＋新方向 | 換種子 7 → 13；斷言不動。掃種子 1～40：三張齊全 改前 29 → 改後 31 |
| `test_wish_two_keywords_txt2.py` 兩組 | 會變（同上） | 種子 7（點燃＋標記橋接）、2（帶電＋潮濕新方向）沒帶到兩個 | 7 → 10、2 → 39；斷言不動。掃 1～40：點燃＋標記 改前 7 個種子 → 改後 6；帶電＋潮濕 2 → 1（樣本小，見待決 5） |
| `test_upgrade_topup.py` 反應技＋潮濕／高處 | 會變（組合器現在做得出來） | 退路由「工坊」變「組合器」 | 測試改成：RC-1 前的組合器（三個機率 0）照舊由工坊做；現在的組合器潮濕、高處由組合器做，召喚物照舊工坊 |
| `test_composer_new_options.py` 兩項 | 會變（召喚骨架改成可組） | `summon` 不再是 `hand_written_only` | 改斷言：召喚只出現在召喚骨架；特性表 `summon` 移到 `explicit_only_active` |
| `test_llm_propose_cli.py::test_naming_flag_adds_generated_names`（`-n 6`） | 會變（第 4 題換了） | 第 6 題 Mock 命名撞名退回組合式名稱（Mock 命名的已知限制） | 改跑 5 題（前 5 題全部命名成功的性質不變） |
| 圖示夾具 `client/src/render/fixtures/skill_icons.json` 的 `random`（組合器種子 0～49 不指定參數） | **漏預測**（一開始只想到戰鬥、技能、parity；這份夾具也收組合器的隨機技能）；事後逐種子比對：只有抽中整招召喚的種子會變 | 只有 `random[47]`：種子 47 從連段（combo）變成整招召喚；`skills`、`workshop` 不變 | 只重產這份（`uv run python -m tests.narrative.icon_fixture`），`git diff` 確認只改這一筆。前端讀這份夾具的 vitest（`skillIcon.test.ts`、`qIconSkills.test.ts`、`qi2cWiring.test.ts`、`qIconQi2d.test.ts`）是性質檢查，**這個 worktree 沒有 `client/node_modules`，沒跑**，請 PM 合併後跑一次 |
| LB 20 題（`trpg llm propose -n 20 --seed 0`，`scripts/llm_model_compare.py` 用） | 只有第 4 題會換 | 第 4 題：1 階 common 不限骨架「召喚物」（種子 4278761754）→ **1 階 rare 不限骨架「冰凍」（種子 2051557974）**；其餘 19 題逐字相同 | 無快照；**之後的 LB 量測第 4 題和舊數據不可比**（其餘 19 題可比） |

其他跑過、全過的：`tests/skillgen`、`tests/content`、`tests/roguelite`、`tests/llm`、`tests/world`、`tests/api` 中與三選一／一輪／許願／工坊相關的 214 項、`tests/sim/test_skill_fuzz.py`、`tests/engine` 被動／反應／層數相關 296 項。

## 4. 改前改後對照（`scripts/recipe_census.py` 全量重跑，200 種子／格）

總表（`RC-1資料/對照.md` 有逐格表；改後的完整盤點在 `RC-1資料/census.md`）：

| 範圍 | 狀態 | 改前 | 改後 |
|---|---|---|---|
| 全部 408 格 | 空 | 142 | 72 |
| 全部 408 格 | 薄 | 14 | 4 |
| 全部 408 格 | 正常 | 252 | 332 |
| 會出題的格子 | 空 | 102 | 32 |
| 會出題的格子 | 薄 | 14 | 4 |
| 會出題的格子 | 正常 | 252 | 332 |

補的格子（合法數／設計數，改前 → 改後；200 種子）：

| 格子 | 1 階 | 2 階 | 3 階 | 4 階 |
|---|---|---|---|---|
| 召喚物／主動／rare | 0/0 → 200/1（薄） | 29/8 → 200/13 | 26/7 → 200/13 | 25/7 → 200/13 |
| 召喚物／主動／epic | 0/0 → 200/1（薄） | 37/8 → 200/13 | 27/8 → 200/13 | 31/8 → 200/13 |
| 連擊／被動／epic | 0/0 → 200/115 | 0/0 → 200/129 | 0/0 → 200/124 | 0/0 → 200/126 |
| 怒氣、氣／被動／epic | 同連擊 | 同連擊 | 同連擊 | 同連擊 |
| 專注／被動／epic | 0/0 → 200/124 | 0/0 → 200/119 | 0/0 → 200/113 | 0/0 → 200/101 |
| **高處／被動／epic（Q12）** | 0/0 → 200/108 | 0/0 → 200/113 | 0/0 → 200/107 | 0/0 → 200/106 |
| 潮濕／被動／epic | 6/6 → 200/96 | 4/4 → 200/96 | 3/3 → 200/92 | 1/1 → 200/89 |
| 倒地／被動／epic | 正常 → 200/93 | 182/8 → 200/94 | 正常 → 200/89 | 197/8 → 200/92 |
| 層數四種／反應／rare、epic | 0/0 → 200/117 | 0/0 → 200/112 | 0/0 → 200/90 | 0/0 → 200/72 |
| 高處／反應／rare、epic | 0/0 → 200/111 | 0/0 → 200/110 | 0/0 → 200/89 | 0/0 → 200/72 |
| 潮濕／反應／rare、epic | 0/0 → 200/70 | 0/0 → 200/66 | 0/0 → 200/51 | 0/0 → 200/32 |
| 召喚物／被動、反應 | 空 → 空（待決 1、2） | 同 | 同 | 同 |

還是薄的 4 格：召喚物／主動／1 階 rare、epic（設計鍵分不出兩種基本召喚物，待決 6）；帶電／反應／1 階 rare、epic（189/10，沒動，RC-0 判「配方稀少」，不在 4.1.19 範圍）。

**副作用（不是洞，但要知道）**：原本正常的格子有 55 格合法數或設計數下降，最多的是「標記／主動／epic」（1 階 185/164 → 116/111）：指定關鍵字又不指定骨架時，組合器本來就可能交出被動或反應（RC-0 第 2 節），現在被動多了「目標被標記」的配方，交出被動的比例變高（不合法原因 `not_fit.kind(passive)` 9 → 79）。點燃、冰凍、帶電主動的設計數也降了一些（例：帶電／主動／2 階 rare 90 → 66 種）——只認專屬規則後，含通用規則的變體不再算數，整招召喚也分走一部分。所有正常格的設計數仍 ≥ 12（最少 12）。見待決 8。

## 5. 樣本（全文含 JSON 在 `RC-1資料/樣本.md`）

`樣本.md` 每個技能都附卡片文字與 JSON，全部通過 `validate_skill`、依專屬規則帶到指定關鍵字。摘要：

**Q12（1 階 epic 被動＋高處，種子 0～3）**：
1. 回合開始時，你站在高處：治療自己 2d6＋感知（法力 2）。
2. 回合開始時，你站在高處：治療自己 1d12＋感知，並得到「反傷護盾」1 回合。
3. 回合結束時，你站在高處：自己得到「戰意」1 回合、治療 2d4＋感知（法力 2、冷卻 2）。
4. 擲出自然 20 時，居高臨下（你比目標高）：目標「被標記」1 回合（法力 1）。
- LB 第 12 題本身（1 階 epic 被動＋高處，種子 3203845091）走退回路徑：**來源從手寫池（RC-1 前退回鷹眼）變成組合器**——造成撞擊後，你站在高處：目標「虛弱」2 回合。

**召喚物主動**：2 階 rare 指定召喚物：召喚火靈持續 3 輪（AP 1、法力 10、冷卻 4）；3 階 epic 指定點燃：召喚火靈持續 3 輪（AP 1、法力 5、冷卻 2）。

**被動層數**：受傷時對攻擊者 1d8＋智力火焰傷害並累積 1 層怒氣；命中被標記的目標時 2d4＋智力火焰傷害並累積 1 層專注；回合開始時若怒氣（或專注）達 2 層，治療自己 2d8＋感知。

**反應**：被攻擊命中時，你站在高處：武器傷害 ×1.1＋擊倒；相鄰敵人離開時，你站在高處：4d4＋智力毒素傷害；被近戰命中時：攻擊者「沉默」2 回合並在他腳下造水 3 回合；被攻擊命中時：5d4＋智力毒素傷害並在攻擊者腳下造水 1 回合。

**Q4**：照規則不補（common 沒有召喚的寫法，遊戲出題也不出這題）；第 7 項只改評估題的出題檢查，LB 第 4 題換成 1 階 rare「冰凍」。

## 6. 檢查

- `ruff check`、`ruff format --check`（全 repo）、`uv run mypy`（1635 檔無錯）、`lint-imports`（14 kept）、`tests/test_architecture.py` 全過。
- 測試：`tests/skillgen`（含新檔 `test_composer_recipes_rc1.py` 21 項）、`tests/content`＋`tests/roguelite`＋`tests/llm`（3813 passed）、`tests/world`（1313 passed）、`tests/cli -m slow`（44 passed）、`test_refactor_parity.py -m slow`（928 passed）、上表其餘。
- 沒跑 `scripts/check.py` 全量、沒跑平衡量測或戰鬥模擬；沒有改數值。
- 盤點：`uv run python scripts/recipe_census.py --workers 8 --out-dir docs/phases/RC-1資料`；對照：`uv run python scripts/recipe_census_diff.py docs/phases/RC-0資料/census.json docs/phases/RC-1資料/census.json --out docs/phases/RC-1資料/對照.md`（新腳本）。

## 7. 待 PM 決定

1. **伴生、護主要不要補關鍵字推導**（第 4、5 項）：`summon_beside`（TF-1 召喚到身邊）在 `skill_keywords.yaml` 沒有任何推導規則，伴生、護主推不出「召喚物」關鍵字，所以補不到召喚物被動／反應的洞。補法是在「召喚物」的 `makes` 加 `{effect: summon_beside}`（要不要再加各召喚物固有關鍵字的 `{effect: summon_beside, unit: ...}` 另定）——這是改推導規則（規則包會變，TF-1 閃現轉型出來的伴生、護主也會開始帶「召喚物」），照「改規則就停下」沒做。程式已經寫好：推導表一有這條，伴生、護主自動列入（測試 `test_companion_and_guardian_wait_for_a_keyword_rule` 用補上規則的內容庫驗過組得出來）。
2. **召喚物倒下時（`on_summon_downed`）給被動技能**（第 4 項）：引擎目前只對裝備詞條發這個時機（`skill_triggers._on_summon_downed` 只找詞條），被動技能不會觸發；而且 6.29.6 的效果是 `sacrifice_summon`，驗證只准主動技能用。補起來要改引擎＋放寬驗證，沒做。
3. **被動「效果作用在自己＋目標型條件」**：引擎判被動技能條件時對象是 `trigger.target`，作用在自己時對象是自己，所以「被比你低的人打到時給自己護盾」這類寫法 `height_advantage` 永遠不成立。組合器目前只把目標型條件配給「效果作用在另一方」。要支援就要改引擎的判斷對象（4.1.19 的「比持有者和另一方」屬於這種語意），會動到既有手寫被動的條件判斷，列題。
4. **三個機率是原型值**：被動、反應改用新配方 250‰，整招召喚 60‰（`skill_composer.yaml` 的 `recipes`）。高處二選一各 500‰（程式常數）。沒量平衡。
5. **許願「帶電＋潮濕」新方向帶兩個的種子變少**（掃 1～40：2 → 1）、「點燃＋標記」橋接 7 → 6：樣本小；三選一「指定帶電」三張齊全 29 → 31。沒有再細查，留給 PM 判斷要不要量。
6. **設計鍵看不出召喚物種類**：盤點的設計鍵是「骨架＋種類＋形狀＋效果類型＋元素標籤」，召喚哪一隻不算，所以 1 階召喚物主動（只有兩種基本召喚物、主題都是物理）永遠只有 1 個設計、算薄格；2 階起看的是主題元素。要不要把召喚物種類算進設計鍵，PM 定。
7. **LB 第 4 題換了**：之後 LB 系列量測（`scripts/llm_model_compare.py`）第 4 題和舊數據不可比。
8. **指定關鍵字又不指定骨架時會交出別的種類**（RC-0 第 2 節已記）：新的被動、反應配方讓這件事在「標記」等關鍵字變多（標記／主動／epic 合法 185 → 116）。要不要讓「主動題」指定關鍵字時不抽被動、反應（例：退回路徑明確傳 `skeleton` 或種類），屬於技術，開發 PM 定。

## 8. commit

分支 `worktree-agent-a7afeb0e2162bd7e7`，未 push（`git log 2de4893bf..HEAD`）：

- `20295ba2a` feat(rc-1): composer recipes for summons, passive and reaction holes
- `9dfc743ff` fix(rc-1): eval topics require keywords_reachable (Q4)
- `0059dfe50` test(rc-1): move wish two-keyword seeds after candidate RNG change
- `49677b6fc` chore(rc-1): census diff script, onboarding note, test lint
- `a86a62f66` test(rc-1): type-narrow summon effect in recipe test
- `ce5651e02` docs(rc-1): report, census after recipes, before/after diff and samples
- 之後一筆：報告 commit 清單

## 開發 PM 裁定（2026-11-15）

- **驗收通過，合併。** 規則、預算、引擎都沒改。新配方用獨立亂數串流，沒抽到新配方的種子逐字不變，有測試鎖住。既有測試的改動都是跟著新行為改：換固定種子（斷言不動）、工坊退路改用「RC-1 前的組合器」照舊測到，沒有放寬。快照只重產 `skill_icons.json` 的 random[47]，事後逐種子比對確認只變這一筆，接受。戰鬥 46 場 different=0。前端 vitest 由開發 PM 合併後跑全量時一起驗。
- **成果**：會出題的格子空格 102 → 32、薄格 14 → 4。Q12 1～4 階都是 200/200。Q4 照使用者「A」不改規則，評估題換成 1 階 rare「冰凍」；之後 LB 的第 4 題和舊數據不能比。
- 待決 1（`summon_beside` 沒有關鍵字推導規則，伴生、護主帶不到召喚物關鍵字）、待決 2（被動用「召喚物倒下時」要改引擎，還要放寬 sacrifice_summon 只准主動的驗證）、待決 3（效果作用在自己、又帶目標型條件的被動要改引擎判斷條件的對象）：都牽涉規則或規則語意，轉給玩法 PM（3.0001）。三項一次答齊後併成一段做。
- 待決 4（新配方的機率 250‰／250‰／60‰）：照原型值，數值由使用者在工坊調。
- 待決 5、6：記錄即可。
- 待決 7：已知，之後的 LB 報告要註明。
- 待決 8（指定關鍵字、不指定骨架時，交出被動或反應的比例變高）：這是分布的變化，不是洞，轉給玩法 PM 看要不要限制。
- 補記：全量檢查時 `tests/sim/test_skill_fuzz.py` 的 slow 測試失敗，它把 summon 當成手寫專用骨架，但 RC-1 起組合器也做 summon。開發 PM 把 summon 從排除清單拿掉，這樣 summon 也必須抽得到，比原本更嚴，不是放寬。單獨重跑通過。
