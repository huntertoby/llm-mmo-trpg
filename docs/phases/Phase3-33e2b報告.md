# Phase 3-33e2b 報告｜17 種召喚物（二）b：藤蔓、守護靈、吸引圖騰、高台圖騰、鷹隼飛行、灌注失效紀錄

> 規格：`docs/phases/Phase3計畫.md` 36.7（3-33e2b 6 項）；設計：`docs/design/06-技能.md` 6.29.5；外觀：`content/summon_looks.yaml`（3-33h1 已備好 4 種的外觀）。數值都是初值（放 `content/`），**沒有調任何既有數值**。名稱與數值請玩法 PM 審（第 2、3 節）。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| 藤蔓 | 範本 `snare`：敵人踏入（走進、被推進、被拉進）相鄰格時，緩速 2 回合＋倒地；每隻每輪 1 次（`UnitState.snare_round`）；倒地會讓正在走的敵人當場停下（沿用 `_move_interrupted`） | `content/battle.py`（`SummonSnare`）、`engine/summons.py`（`unit_moved` 觸發） |
| 守護靈 | `pulse` 多 `shield_dice`／`shield_flat`：回合開始給 **最虛弱** 的友方（含召喚者與其他召喚物，不含自己）一層護盾 | `engine/summons.py`（`pulse_summon`、`weakest_ally`） |
| 吸引圖騰 | `pulse` 多 `pull_radius`：回合開始把半徑內最近（再依座標 `(y, x)`）、拉得動的敵人往圖騰拉近 1 格（用 `PushEffect`，拉進火、陷阱、深淵照常結算） | 同上（`_pull_nearest_enemy`） |
| 高台圖騰 | 範本 `platform`：召喚時在旁邊升起 1 格高台（地形高度 +1），圖騰消失（到期、被打倒、召喚者離場、超過上限）時恢復；重用 3-19 高度規則 | `engine/summons.py`（`_raise_platform`）、`engine/lifecycle.py`（`_lose_summon_extras`）、新 `engine/heights.py`（`change_height` 搬出 `world.py`，避免循環匯入） |
| 純功能圖騰 | 範本 `inert`：AP 恆為 0（不移動、不攻擊），只有回合開始的脈動／特性；`is_inert` 同時涵蓋有光環的圖騰 | `engine/summons.py`、`engine/turns.py` |
| 鷹隼飛行 | 標籤 `flying`（鷹隼原本就有）：移動成本每步 1，無視高度差、深淵、牆與障礙物（仍不能穿過敵方單位），**只能停在可站立的格子**；不受地面表面影響（進入效果、回合開始效果、互動表的單位 × 表面規則） | `engine/rules/movement.py`（`is_flying`、`unit_step_cost`、`PathMap.no_stop`）、`engine/battle.py`（`plan_move`）、`engine/effects/handlers.py`、`engine/turns.py`、`engine/interactions.py` |
| 灌注失效紀錄 | 召喚物在施放灌注技能前倒下或消失時，發出 `infusion_fizzled`（新原因 `downed`／`gone`），戰鬥紀錄多一行「〇〇的灌注技能失效：〇〇被打倒了／消失了，「技能」沒有施放（法力與冷卻不退）」 | `engine/lifecycle.py`、`engine/events.py`、`narrative/events.py` |
| 新事件 | `snare_triggered`（藤蔓纏住）、`summon_pulled`（吸引圖騰拉人）；各有戰鬥紀錄文字 | `engine/events.py`、`narrative/events.py` |
| 召喚技 4 招＋武器 3 把 | 見第 3 節；起始包 +4（藤蔓包、守護靈包、吸引圖騰包、高台圖騰包） | `content/skills/`、`content/weapons.yaml`、`content/dev_starters.yaml` |
| 關鍵字推導 | 倒地 ← 藤蔓、撞擊 ← 吸引圖騰、高處 ← 高台圖騰（守護靈由通用的「召喚物」關鍵字涵蓋） | `content/skill_keywords.yaml` |
| 格式 | `LOG_FORMAT` `/52 → /53`（PM 合併時定號）；單位狀態多 `snare_round`、`platform_pos`；CLI 快照與技能圖示 fixture 已重產；OpenAPI 無變動 | `engine/runner.py` |

沒有新增狀態（緩速、倒地、護盾都沿用），所以 `client/src/render/skillParts.ts` 不需補圖示部件；鷹隼的飛行外觀與高台的地形高度前端本來就會畫（3-33h1 `trait: flying`、地形高度渲染），沒有新增前端浮動元素，不涉及 6.5.1。

## 2. 每種召喚物的特性（4 種新增＋鷹隼補完）

> HP＝範本 `max_hp` 經體質公式後的最終值；預設模式＝`default_mode`。外觀照 `summon_looks.yaml`（範本 `look` 與表一致，`tests/content/test_summon_looks.py` 檢查）。

| 召喚物 | 定位 | HP／速度／武器 | 預設模式 | 特性（怎麼實作） | 對應召喚技能 |
|---|---|---|---|---|---|
| 藤蔓 `summon_vine` | 陷阱、控場 | 16／0／藤鞭 1d4（土，射程 1）；怕火（火 +300‰） | 待命 | `snare: {status: slow, duration: 2, prone: true}`；不能動，只打相鄰的敵人 | 召喚藤蔓 |
| 守護靈 `summon_guardian_spirit` | 護盾輔助 | 14／4／守護之杖 1d4（聖，射程 3） | 守護我 | `pulse: {shield_dice: 1d4, shield_flat: 2}`（平均 4.5 點護盾） | 召喚守護靈 |
| 吸引圖騰 `summon_pull_totem` | 拉扯控場 | 18／0／圖騰石 1d4（僅佔位，AP 0 不會用） | 待命 | `inert: true`、`pulse: {pull_radius: 2}` | 立起吸引圖騰 |
| 高台圖騰 `summon_plateau_totem` | 地形工具 | 18／0／圖騰石 1d4（僅佔位） | 待命 | `inert: true`、`platform: {height: 1}` | 立起高台圖騰 |
| 鷹隼（補完 3-33e1 #3）`summon_hawk` | 斥候 | 8／7／利爪 1d4（未改） | 跟隨 | 標籤 `flying` 現在有真正的飛行規則；命中標記＋揭露（3-33e1 已有） | 喚出鷹隼（未改） |

## 3. 新召喚技能（4 招，玩法 PM 審）

共通：階 1、稀有度 rare、形狀 `ground_tile`、1 AP、法力 8、冷卻 4、`category: spell`、`skeleton: summon`、持續 4 輪、縮放屬性智慧（wis）；由技能池給出（`tests/content/test_coverage.py` 的 `_POOL_ONLY`），開發者起始包可帶。圖示由 `icon_of` 自動產生，fixture 已重產。

| 技能 | 召喚 | 射程 | 標籤 | 製造的關鍵字 | 預算 |
|---|---|---|---|---|---|
| 召喚藤蔓 | 藤蔓 | 4 | nature、spell、summon、control | 倒地、召喚物 | 1d4 武器 × 4 輪 × 800‰ = 8.0，過預算 |
| 召喚守護靈 | 守護靈 | 4 | holy、spell、summon、support | 召喚物 | 8.0，過 |
| 立起吸引圖騰 | 吸引圖騰 | 3 | spirit、spell、summon、control | 撞擊、召喚物 | 8.0，過 |
| 立起高台圖騰 | 高台圖騰 | 3 | earth、spell、summon、terrain | 高處、召喚物 | 8.0，過 |

新武器 3 把（`summon_only: true`，不進開局武器）：`vine_lash` 藤鞭（近戰、土、1d4）、`guardian_rod` 守護之杖（法器、聖、射程 3、1d4）、`totem_stone` 圖騰石（近戰、物理、1d4，純功能圖騰的佔位武器）。

起始包 +4（開發者起始包 20 → 24）：`dev_summon_vine`「藤蔓包」、`dev_summon_guardian`「守護靈包」、`dev_summon_pull`「吸引圖騰包」、`dev_summon_plateau`「高台圖騰包」（每包一招新召喚技能＋火焰箭；名稱都不與技能同名）。

## 4. 驗收證據

| 驗收項 | 證據（`tests/engine/test_summons_e2b.py`，共 40 個） |
|---|---|
| 藤蔓：不能動、纏住（緩速＋倒地）、一輪一次、下一輪恢復、不纏友方、被推進相鄰格也纏、倒地讓走路停下 | `test_vine_*` |
| 守護靈：護盾給最虛弱者（含召喚物、含召喚者）、不給自己、同比例時依 HP 再依 ID、回合開始觸發 | `test_guardian_*` |
| 吸引圖騰：不行動、拉最近者、同距離依座標、範圍 2、相鄰與被擋的略過、拉進火裡照常結算（燃燒）、不拉友方 | `test_pull_totem_*` |
| 高台圖騰：升起離召喚者最近的相鄰格、到期／被打倒／召喚者倒下都恢復、沒有空格不報錯、可攀上去（成本 2） | `test_plateau_*` |
| 鷹隼飛行：越過牆、深淵、高度差；不能停在牆裡（非法移動拋錯）；步行者做不到；不受火表面影響（同格的步行者仍著火）；敵人仍擋路；合法動作列表含越過的終點 | `test_hawk_*`、`test_a_walker_cannot_do_the_same` |
| 灌注失效紀錄：被打倒、消失、召喚者倒下時各一行；沒有待施放的灌注就沒有 | `test_downing_an_infused_summon_*`、`test_a_vanishing_*`、`test_no_fizzle_*`、`test_owner_downed_*` |
| 新技能過預算與關鍵字、範本模式與外觀 | `test_new_summon_skills_have_their_keyword_and_pass_the_budget`、`test_new_templates_have_modes_looks_and_traits` |
| 同種子確定、`--log-json` 與重播 | `test_same_seed_and_inputs_give_the_same_battle`；`tests/sim/test_summon_report.py::test_the_new_summon_packs_summon_and_replay_identically`（4 個新包在 Boss 地圖 `run_battle` ＋ `replay` 終局逐位元一致） |

被迫改的既有測試（原因都是新增內容，非行為回歸）：`test_run_cli.py`（進化種子 4 → 5）、`test_budget_cli.py`（技能數 207 → 211）、`test_run_start_api.py`／`test_keyword_start.py`（起始包 20 → 24）、`test_con_hp.py`（新範本最終 HP）、`test_summon_content.py`（範本清單）、`test_coverage.py`（新技能進 `_POOL_ONLY`）、`test_summons_e1.py`（召喚專用武器清單多 3 把）、`test_summon_report.py`（參數多 4 個包）、8 個 `LOG_FORMAT` 斷言（`/52 → /53`）、CLI 快照雜湊。

## 5. `sim_summons.py` 小量表

`uv run python scripts/sim_summons.py --packs dev_summon_vine,dev_summon_guardian,dev_summon_pull,dev_summon_plateau,dev_summon_hawk --seeds 2 --jobs 3`（5 張正式地圖 × 2 種子，每包 10 場；主角 Lv1；樣本很小，只看有沒有跑通與大致量級，**不下平衡結論**）：

| 起始包 | 場數 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 平均存活輪數 | 結束原因（隻） |
|---|---|---|---|---|---|---|---|---|---|---|
| 藤蔓包 | 10 | 80% | 4.1 | 9.8 | 120 | 5 | 4.5% | 0.90 | 1.9 | 倒 3、到期 1、撐到戰鬥結束 5 |
| 守護靈包 | 10 | 80% | 4.3 | 6.1 | 119 | 8 | 7.0% | 0.90 | 1.7 | 倒 6、撐到 3 |
| 吸引圖騰包 | 10 | 80% | 4.8 | 10.2 | 128 | 0 | 0.0% | 1.30 | 0.8 | 倒 9、召喚者倒下 3、撐到 1 |
| 高台圖騰包 | 10 | 60% | 5.4 | 8.6 | 118 | 1 | 0.6% | 1.20 | 1.6 | 倒 8、到期 2、撐到 2 |
| 鷹隼包（飛行後；對照 3-33e1 的 90%） | 10 | 80% | 4.0 | 8.9 | 128 | 14 | 10.6% | 1.00 | 1.6 | 倒 6、撐到 4 |

觀察：吸引圖騰與高台圖騰不攻擊，直接傷害當然接近 0（價值在拉扯與高台，統計看不到）；吸引圖騰 13 隻中倒 9 隻、平均只活 0.8 輪（AI 把它放在靠近敵人處，HP 18 容易被集火）。AI 不認得「拉扯」「高台」的價值，只用武器 DPR 估值（見「待 PM 決定」#2、#3）。

## 6. 待 PM 決定

1. **純功能圖騰靠「佔位武器」過預算**：目前預算公式只算 武器骰 × 持續輪數，吸引圖騰、高台圖騰不攻擊卻要有武器才過預算（`totem_stone` 1d4 × 4 輪）。3-33e2a 會把特性計入預算（`skill_budget.yaml`，我沒動）；那邊合併後請檢查這 4 招（尤其是持續輪數，1d4 × 4 輪只是剛好過下限），必要時把佔位武器拿掉改以特性點數計。
2. **AI 對新特性的估值為 0**：召喚技能的 AI 估值只看武器 DPR（沿用 3-33e1 的作法），守護靈的護盾、吸引圖騰的拉扯、高台圖騰的高台、藤蔓的纏住都沒有收益，因此 AI 召喚它們主要靠「武器 DPR × 輪數」的虛值；新召喚物放的位置也只依「離敵人近」（圖騰類應該放在友方旁邊／戰線上）。是否要在 3-33g（AI／平衡）補專屬估值請決定。
3. **吸引圖騰存活偏低**（模擬 13 隻倒 9 隻）：HP 18、AI 放在靠近敵人處。建議 3-33f（HP 成長）一併看，或讓圖騰類放置位置偏向友方。
4. **守護靈護盾範圍沒有上限**：規格寫「最虛弱的友方」，我沒加距離限制（全場）；護盾量 1d4＋2（平均 4.5）為初值。「最虛弱」＝HP 比例最低，再依目前 HP、單位 ID；全員滿血時也會上盾（給 HP 最少者）。
5. **吸引圖騰拉不動時略過**：目標相鄰（拉不動）、前面被單位／牆／較高地形擋住、堅守（steadfast）單位距離打折為 0 時，改選下一個符合的敵人；完全沒有就這回合不動（無事件）。拉進深淵／岩漿會依「致命地形」死亡（規格「照常結算」）；單向拉扯沒有撞擊傷害。
6. **藤蔓「每回合 1 次」解讀為每隻藤蔓每輪 1 次**（不是每個敵人）；敵人傳送復位（`teleport`）不算踏入；飛行單位也會被纏（沒有特別規定）。倒地者站起要付移動點數，緩速 2 回合。
7. **高台細節**：只升 1 格、只支援高度 +1（恢復時不結算墜落，欄位上限 1）；位置選圖騰旁離召喚者最近的空格（可站立、無單位／物件、非致命），再依座標；四周都沒位置時就沒有高台（技能照常召喚圖騰）。站在高台上的單位在圖騰消失時跟著降 1 層（落差 1，不墜落）。
8. **飛行的範圍**：只做「移動」與「不受地面表面影響」；飛行單位仍會被推擊、仍會因 `deadly` 地形死亡（被推進岩漿時）、仍受陷阱影響（陷阱沒有被排除）；AI 的接近距離啟發式（`_steps_to`）仍以步行路徑估計，所以鷹隼不會刻意「繞過牆飛」，只是在 `path_map` 找到更短路徑時自然使用。`flying` 標籤現在是引擎規則，之後別的單位（蝙蝠等）帶這個標籤也會飛。
9. **共用檔案**：`change_height` 從 `engine/effects/world.py` 搬到新檔 `engine/heights.py`（`world.py` 仍匯出同名函式）；`UnitTemplate` 新增 `snare`／`platform`／`inert`、`SummonPulse` 新增 `shield_*`／`pull_radius`、`UnitState` 新增 `snare_round`／`platform_pos`，皆為新增欄位，與 3-33e2a 合併時兩邊保留。

## 7. noqa 與最終檢查

沒有新增複雜度類（`C901`／`PLR*`）的 `noqa`；測試內有一處 `PLC0415`（函式內 import，沿用既有測試作法）。

最終檢查：與其他 agent 同時跑，完整 `scripts/check.py` 不可行，改分段跑：ruff、format、mypy、lint-imports 全過；`tests/engine`＋`narrative`＋`sim`＋`shared`＋`content`（3310 個）全過（僅圖示 fixture 重產前的一個失敗已修）；`tests/cli`＋`api`＋`roguelite`＋`skillgen` 第一次 5 個失敗（上述計數與種子）已修，修正後相關檔案重跑全過；未重跑整批、`pnpm build` 未跑（沒動前端程式，只動圖示 fixture JSON）。
