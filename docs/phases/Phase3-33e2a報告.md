# Phase 3-33e2a 報告｜召喚物（二）a：爆裂傀儡、石像、土牆、戰狼＋召喚物特性計入預算

> 規格：`docs/phases/Phase3計畫.md` 36.7「3-33e2a」5 項；設計：`docs/design/06-技能.md` 6.29.5。外觀照 `content/summon_looks.yaml`。數值都是初值（放 `content/`），名稱與數值請玩法 PM 審（第 2、3、4 節）。另一段 3-33e2b（藤蔓、守護靈、圖騰、鷹隼飛行、灌注失效紀錄）與 3-32d 沒有碰。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| 爆裂傀儡自爆 | 範本 `detonate`（半徑、傷害骰、元素、留下的表面）。走到敵人相鄰的那一步就自爆（路徑中途也算，停在該格）、回合開始時已相鄰、被打倒時自爆；周圍曼哈頓距離內的**敵人**受傷，爆心與周圍各格留下火表面，自己消失（`summon_expired`，原因 `detonated`）。事件 `summon_detonated`（`arrived`／`adjacent`／`downed`） | `content/battle.py`（`SummonDetonate`）、`engine/summons.py`（`detonate_if_adjacent`、`detonate_on_downed`）、`engine/battle.py`（`_do_move`）、`engine/turns.py`、`engine/lifecycle.py`（`down_unit`） |
| 石像不會被推動 | 單位標籤 `immovable`：推擊、拉扯（同一個 `PushEffect`）距離歸零，`push_resisted` 多了 `reason: immovable`；強制位移與被傳送（`move_unit` 的 `forced`／`teleported`）被擋下，`move_blocked` 原因 `immovable`；`Shove` 動作的不合法原因說「紋風不動」。自己走路不受影響。敵人被推撞到石像時，照既有撞擊規則（`collided`，`other_id`＝石像）雙方都受撞擊傷害 | `engine/ids.py`、`engine/effects/world.py`、`engine/effects/handlers.py`、`engine/battle.py` |
| 土牆 | 範本 `inert: true`（回合內沒有 AP、不能操控，同圖騰）、標籤 `blocks_sight`（`has_line_of_sight` 把這種單位所在格當成擋視線的物件）、標籤 `topplable`：被推擊／拉扯時不移動，朝推的方向倒下，用物件推倒同一組規則（`topple_length`、`topple_damage_dice` 2d6、倒地）壓到格上的單位與可破壞物件，土牆消失（`wall_toppled`＋`summon_expired`，原因 `toppled`）。土牆有 HP，可被打掉 | `engine/effects/world.py`（`_topple_unit`，與物件共用 `_topple_scan`）、`engine/triggers.py`、`engine/rules/geometry.py`、`engine/summons.py`（`summon_inert`） |
| 戰狼 | 速度 6，固有「倒地」（沿用 3-33e1 的絆倒：敏捷對抗，每輪 1 次）。沒有新引擎行為 | `content/units/summons/summon_war_wolf.yaml` |
| 特性計入預算 | 召喚技的點數 ＝（武器骰平均 ＋ 每輪特性）× 輪數 × `summon_round_value_permille` ＋ 一次性特性 × 同係數。各項係數放 `content/skill_budget.yaml`（`summon_trait_*`、`summon_detonate_*`、`summon_topple_*`，欄位在 `content/skill_rules.py`）。計入：額外傷害（雷電）、命中附帶狀態（點燃、冰凍、標記、揭露；有條件的另乘 40%）、造表面、水面連鎖、脈動治療、背刺骰、絆倒、震退、高處加傷、不會被推動、召喚時隱蔽（一次性）、自爆（一次性）、被推倒壓人（一次性）。不行動的召喚物（土牆）武器傷害記 0；自爆的召喚物一般攻擊與特性只算 1 輪 | `skillgen/budget.py`（`summon_trait_points`）、`content/summons.py`（`summon_dpr` 對 `inert` 回 0） |
| AI 估值 | `ai_profiles.yaml` 的 `summon:` 多 `detonate_targets_permille`（自爆：爆炸骰平均 × 預期被炸到的敵人數）與 `inert_round_points`（土牆每輪擋路價值）；`is_risky_move` 對會自爆的召喚物，路徑上有一步走到敵人相鄰就跑完整預覽（否則只用虛擬分數，看不到爆炸） | `engine/ai/summon.py`、`engine/ai/utility.py`、`content/environment.py` |
| 內容 | 4 種召喚物、4 招召喚技、3 把召喚專用武器（炸藥殼、石拳、利齒）、關鍵字推導 4 條、開發者起始包 20 → 24（傀儡包、石像包、土牆包、戰狼包） | `content/` |
| 格式 | `LOG_FORMAT` `/52 → /53`（PM 合併時定號）；CLI 快照、技能圖示 fixture 已重產；OpenAPI 沒有變 | `engine/runner.py` |

## 2. 每種召喚物的特性與召喚技能（玩法 PM 審）

> HP＝經體質公式（`max_hp + (體質 − 10) × 3`）後的最終值。外觀照 `summon_looks.yaml`（範本 `look` 與表一致，`tests/content/test_summon_looks.py` 檢查）。

| 召喚物 | 定位 | HP／速度／武器 | 固有關鍵字 | 特性（怎麼實作） | 預設模式 | 召喚技能 |
|---|---|---|---|---|---|---|
| 爆裂傀儡 `summon_bomb_puppet` | 自爆 | 8／5／炸藥殼 1d4 | 點燃 | 走到敵人相鄰（途中任何一步）、回合開始時已相鄰或被打倒時自爆：半徑 1（曼哈頓）2d6 火焰傷害給敵人，爆心與周圍 5 格留下火表面，自己消失 | 跟隨（「衝鋒」，見待決定 #1） | 喚出爆裂傀儡 |
| 石像 `summon_golem` | 擋路、地形工具 | 24／3／石拳 1d6（護甲 +3） | 撞擊 | 標籤 `immovable`（推、拉、強制位移、傳送都無效並說明原因）；普攻震退 1 格；敵人被推撞到牠時受撞擊傷害 | 守護我 | 召喚石像 |
| 土牆 `summon_earth_wall` | 地形工具 | 20／0／（不攻擊） | 撞擊 | 不行動、擋路、擋視線；被推時朝推的方向倒下，壓到的單位受 2d6 傷害並倒地，土牆消失 | 待命 | 築起土牆 |
| 戰狼 `summon_war_wolf` | 快速突擊 | 14／6／利齒 1d6 | 倒地 | 撲倒：普攻命中時絆倒目標（敏捷對抗，每輪 1 次） | 跟隨（衝鋒） | 召喚戰狼 |

召喚技（共通：階 1、稀有度 rare、形狀 `ground_tile` 射程 4、1 AP、冷卻 4、`category: spell`、`skeleton: summon`；關鍵字由推導得出；`icon_of` 自動產生圖示，fixture 已重產；AI 會施放，`tests/engine/test_summons_e2a.py::test_summon_skills_cost_no_more_than_the_budget_and_the_ai_casts_them`）：

| 技能 | 召喚 | 持續 | 法力 | 縮放屬性 | 標籤 | 製造的關鍵字 |
|---|---|---|---|---|---|---|
| 喚出爆裂傀儡 | 爆裂傀儡 | 2 輪 | 8 | 智力 | fire | 點燃、召喚物 |
| 召喚石像 | 石像 | 2 輪 | 10 | 力量 | earth | 撞擊、召喚物 |
| 築起土牆 | 土牆 | 3 輪 | 8 | 意志 | earth、obstacle | 撞擊、召喚物 |
| 召喚戰狼 | 戰狼 | 2 輪 | 8 | 敏捷 | physical | 倒地、召喚物 |

## 3. 特性計入預算：係數與 3-33e1 六招的調整

係數（`content/skill_budget.yaml`，皆初值）：額外傷害 80%、命中狀態點數 20%（有條件的再 × 40%）、造表面 10%、水面連鎖 30%、脈動治療 60%、背刺骰 25%、絆倒 20%、震退 25%、高處加傷 30%、不會被推動每輪 0.5 點、召喚時隱蔽 1 點（一次性）、自爆爆炸骰 × 0.8 個敵人（一次性，傀儡一般攻擊只算 1 輪）、被推倒壓人（2d6 ＋ 擊倒 3 點）× 0.9（一次性）。

可用預算約 8.7（階 1、1 AP、法力 8～10、冷卻 4），合格區間 70%～100%（6.1～8.7）。下表是每招召喚技在新規則下的點數與調整：

| 技能 | 武器每輪 | 每輪特性 | 一次性 | 舊持續 → 新持續 | 新點數 | 比例 |
|---|---|---|---|---|---|---|
| 召喚元素之靈（舊） | 3.50 | 0 | 0 | 3 → 3 | 8.40 | 96% |
| 喚起骷髏（舊） | 4.50 | 0.60（絆倒） | 0 | 2 → 2 | 8.16 | 99% |
| 召喚火靈（e1） | 3.50 | 0.60 | 0 | 3 → **2** | 6.56 | 75% |
| 召喚冰靈（e1） | 3.50 | 1.24 | 0 | 3 → **2** | 7.58 | 87% |
| 召喚雷靈（e1） | 2.50 | 2.75 | 0 | 4 → **2** | 8.40 | 96% |
| 召喚水精（e1） | 2.50 | 1.70 | 0 | 4 → **2** | 6.72 | 77% |
| 喚出影魅（e1） | 2.50 | 1.25 | 1 | 4 → **2** | 6.80 | 78% |
| 喚出鷹隼（e1） | 2.50 | 0.80 | 0 | 4 → **3** | 7.92 | 91% |
| 喚出爆裂傀儡 | 2.50（只算 1 輪） | 0.60 | 7.10（自爆） | 2 | 8.16 | 94% |
| 召喚石像 | 3.50 | 1.00（震退、不會被推動） | 0 | 2 | 7.20 | 82% |
| 築起土牆 | 0 | 0 | 9.00（推倒壓人） | 3 | 7.20 | 83% |
| 召喚戰狼 | 3.50 | 0.60 | 0 | 2 | 6.56 | 76% |

只改了 3-33e1 六招的 `duration`（以及技能檔裡的說明句）；骷髏與元素之靈的持續輪數沒動（骷髏的絆倒特性點數被計入後 99%，剛好還在區間內）。

## 4. 驗收證據

| 驗收項 | 證據 |
|---|---|
| 爆裂傀儡自爆：走到相鄰、中途停在第一個相鄰格、不傷己方、被打倒、回合開始時已相鄰、AI 會衝進去、同種子確定與紀錄文字 | `tests/engine/test_summons_e2a.py`（`test_the_bomb_*`） |
| 石像：推擊給原因、拉扯／傳送無效但自己能走、`Shove` 不合法原因、被推撞到牠的敵人受撞擊傷害 | 同檔 `test_the_golem_*`、`test_the_shove_action_*`、`test_an_enemy_pushed_into_the_golem_*` |
| 土牆：不行動／擋路／擋視線、被推倒壓人（傷害＋倒地＋消失＋紀錄）、倒下方向、有 HP 可被打掉（視線恢復） | 同檔 `test_the_wall_*`、`test_pushing_the_wall_*`、`test_a_toppled_wall_*` |
| 戰狼：速度 6、絆倒每輪 1 次 | 同檔 `test_the_wolf_*` |
| 預算：4 招過預算與關鍵字、特性有計入、3-33e1 六招與骷髏仍合格且持續 2～3 輪 | 同檔 `test_new_skills_*`、`test_summon_traits_*`、`test_the_e1_skills_*`、`test_traits_cost_budget_*`；`tests/content/test_summon_content.py` |
| 範本載入、外觀欄位、預設模式、最終 HP | `tests/content/test_summon_content.py`、`test_summon_looks.py`、`test_con_hp.py`、同檔 `test_new_summons_keep_their_look_fields_and_defaults` |
| 技能池涵蓋／圖示 fixture／技能預算總表 | `tests/content/test_coverage.py`（4 招進 `_POOL_ONLY`）、`tests/narrative/test_skill_icon.py`、`tests/cli/test_budget_cli.py`（207 → 211 招） |
| 4 個新起始包會召喚、`run_battle` ＋ `replay` 終局逐位元一致 | `tests/sim/test_summon_report.py::test_the_new_summon_packs_summon_and_replay_identically`（現在每包試 3 個種子，見待決定 #5） |
| 全量 | 見第 7 節 |

被迫改的既有測試（原因都是新增內容，非行為回歸）：`test_con_hp.py`（新範本最終 HP）、`test_summon_content.py`（範本清單、骷髏預算式多了絆倒特性）、`test_coverage.py`、`test_budget_cli.py`（技能總數）、`test_run_start_api.py`（起始包 20 → 24）、`test_summons_e1.py`（召喚專用武器改成包含關係，e2b 也會加）、`test_run_cli.py`（分歧進化種子 `[4, 6]` → `[5, 6]`：技能池多了 4 招後種子 4 的一輪不再進化）、8 個 `LOG_FORMAT` 斷言、CLI 快照雜湊。

## 5. `sim_summons.py` 小量表

`uv run python scripts/sim_summons.py --packs dev_summoner,dev_summon_bomb,dev_summon_golem,dev_summon_wall,dev_summon_wolf --seeds 2 --jobs 4`（5 張正式地圖 × 2 種子，每包 10 場；主角 Lv1；樣本很小，只看有沒有跑通與大致量級）：

| 起始包 | 場數 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 有召喚場數 | 平均存活輪數 | 首召輪 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 喚靈（保證召喚，元素之靈） | 10 | 80% | 4.1 | 6.9 | 119 | 18 | 14.7% | 0.70 | 7 | 2.1 | 1.3 |
| 傀儡包 | 10 | 60% | 4.7 | 10.1 | 112 | 2 | 1.5% | 0.60 | 6 | 0.5 | 1.2 |
| 石像包 | 10 | 90% | 5.1 | 10.2 | 128 | 2 | 1.2% | 0.50 | 5 | 1.6 | 1.4 |
| 土牆包 | 10 | 80% | 4.5 | 8.8 | 119 | 0 | 0.0% | 0.50 | 4 | 1.2 | 1.8 |
| 戰狼包 | 10 | 50% | 4.6 | 5.2 | 102 | 6 | 5.4% | 0.60 | 5 | 1.0 | 2.0 |

召喚物結束原因：傀儡 6 隻中自爆 4、被打倒 1、到期 1（自爆一次約 7 點，所以「召喚物傷害」小）；石像 5 隻：被打倒 2、到期 2、撐到戰鬥結束 1；土牆 5 隻：被打倒 3、撐到戰鬥結束 2（沒有被推倒：模擬裡沒有人去推牠，推倒只在玩家／技能推擊時發生）；戰狼 6 隻：被打倒 4、撐到結束 2。

觀察：全部跑通、無例外與動作上限；傀儡 HP 8 幾乎一定自爆或被打倒（平均存活 0.5 輪）；土牆不攻擊，傷害占比 0%，價值在擋路與推倒壓人（模擬看不出來）；戰狼被打倒 4／6，HP 14 的近戰快速單位偏脆。**不調數值**，建議 3-33g 的對照模擬一併看。

## 6. 待 PM 決定

1. **「衝鋒」模式**：規格寫爆裂傀儡、戰狼「模式衝鋒」，但 `SummonMode` 只有守護我／跟隨／待命／集火（3-33c 把 6.29.5 的「衝鋒」當成預設跟隨）。本段沿用：兩者 `default_mode` 是跟隨；傀儡因自爆價值大，AI 會自己衝進敵人旁。若要真的新增「衝鋒」模式（不受跟隨半徑拉住），請另開項目。
2. **自爆時機**：「走到相鄰」做在移動結算（每走一步檢查，第一個相鄰格就停下自爆）、回合開始時已相鄰、被打倒時，三者共用同一個爆炸；不做「一般普攻改成自爆」（因為移動後必然已經自爆，普攻到不了）。只傷敵人、不傷友方與自己，爆炸不經過命中判定與格擋。傀儡被打倒時的爆炸也會連鎖引爆旁邊的傀儡（有限，因為單位數有限）。
3. **自爆的預算與 AI 估值**：預算把「一般攻擊與特性」只算 1 輪，爆炸算 0.8 個敵人（一次性）；因此持續輪數（2）不影響點數，只影響傀儡能在場上等多久。AI 估值對應：`detonate_targets_permille` 1000。請玩法 PM 看傀儡 HP 8（一擊就倒）是否太脆；被打倒也會自爆，所以不算白白浪費。
4. **土牆的細節**：①被「任何人」推（含友方、含自己的推擊技）都會倒，不分敵我；②友方可以穿過土牆格（單位走路本來就可以暫時穿過友方），敵人不行——「擋路」主要是擋敵人與擋視線；③不能灌注、不能操控（`inert`，同圖騰），灌注選單會顯示不能操控的原因；④倒下不留倒塌物（規格寫「土牆消失」）。
5. **持續輪數縮短的後果**：3-33e1 六招改成 2～3 輪後，AI 在個別種子的第一回合更常先用火焰箭而不是召喚（冰靈包 Boss 地圖種子 1 沒有召喚，種子 2、3 有），所以 `test_the_new_summon_packs_summon_and_replay_identically` 改成試 3 個種子取任一次有召喚。若玩法 PM 要維持「首選召喚」，需調 AI 的召喚收益權重或提高持續輪數（會超預算，只能降特性係數）。
6. **石像 HP 24 比骷髏（20）高**：在 `std` 定位上它是最耐打的召喚物但持續只有 2 輪（預算被「不會被推動」與震退吃掉一部分）；是否要降特性係數換更長的持續，請看 3-33f/g 的存活量測。
7. **共同欄位與合併**：`UnitTemplate` 新增 `detonate`、`inert`（只新增，沒改既有欄位），`PushResisted.reason`、`MoveBlocked.reason` 多一個值、`SummonExpiryReason` 多 `detonated`／`toppled`；3-33e2b 若也新增「不行動」類欄位（藤蔓）請與 `inert` 合併成一個；`turns.py`／`summon_control.py`／`view.py` 現在用 `summon_inert()`（圖騰或 `inert`）判斷「沒有行動」，e2b 的藤蔓可直接沿用。
8. **視線**：`has_line_of_sight` 每次呼叫多掃一遍單位找帶 `blocks_sight` 標籤的（目前只有土牆）；單位數很少、沒有可量測的效能差異（CLI 快照重產的耗時與之前相同），若之後 `blocks_sight` 單位變多再改成狀態內的快取。

## 7. noqa 與最終檢查

新增 1 個 `PLC0415`（`engine/lifecycle.py` 的 `down_unit` 內延後匯入 `detonate_on_downed`，避免 `summons` ↔ `lifecycle` 循環匯入；沿用同函式 `spawn_on_downed` 的作法）；測試沒有新增 `noqa`。沒有新增複雜度類（`C901`／`PLR*`）的 `noqa`。

FINAL_PLACEHOLDER

## 合併 3-33e2b

main（已含 3-33e2b）合併進本分支，18 個檔案衝突，原則是兩段的新增全部保留。

- **LOG_FORMAT**：兩段都定 `/53`，合併後改 **`/54`**；`runner.py` 文件字串依序寫 `/54`（3-33e2a）、`/53`（3-33e2b）；測試裡的 `trpg-battle-log/53`、`endswith("/53")` 一併改 `/54`。
- **範本欄位**（`content/battle.py`）：`detonate`、`snare`、`platform`、`inert` 並存；兩段都新增了 `inert`，合併成同一個欄位（不行動、不能操控）。驗證訊息列出全部欄位。
- **`inert` 判斷函式**：3-33e2a 叫 `summon_inert`、3-33e2b 叫 `is_inert`，語意相同，保留 `summon_inert`（`summon_control`、`view` 等已在用），拿掉 `is_inert`。
- **引擎**：`ids.py` 同時有 `FLYING`、`IMMOVABLE`；`effects/world.py` 同時匯入 `change_height` 與 `dismiss_summon`；`summons.py` 合併事件匯入（自爆、纏繞、拉扯），自爆與高台函式並存。
- **內容**：武器（炸藥殼、石拳、利齒、藤鞭、守護之杖、圖騰石）、起始包（8 個召喚對照組，共 28 包）、關鍵字規則（`prone` 與 `collision` 各含兩段的召喚）全部保留。召喚物特性計入預算（3-33e2a）之後，總技能數 215。
- **測試**：技能數 211 → 215、起始包 24 → 28、召喚專用武器改成列出全部 7 把的相等斷言。`tests/roguelite/test_keyword_start.py` 的固定種子 2 在新技能池下提案第一個變成 `summon`，改種子 **1**（`test_run_cli.py` 的參數 `[5, 6]` 合併後仍有效）。
- 重產：`tests.narrative.icon_fixture`、CLI 快照；OpenAPI 與 `client gen:api` 沒有變動需要重產（`check.py` 的 client 步驟全過）。

### 第 5 點：召喚物特性計入預算後重審 3-33e2b 的 4 招

- 藤蔓、守護靈：武器骰與脈動讓總點數 8，在區間內，不用動。
- 吸引圖騰、高台圖騰：3-33e2a 之後，不行動的召喚物（`inert`）不計武器骰，`totem_stone` 不再貢獻任何點數（每輪 0），兩招總點數 0，**預算不過**。原有特性（沒有拉扯、高台）沒有計價項目，所以「特性已足夠」不成立，不能單靠拿掉佔位武器解決（範本的 `weapon` 欄位也是必填，`totem_stone` 因此保留）。
- 處理（最小補價，初值未經模擬，請 PM 決定）：在 `skill_budget.yaml` 新增 `summon_trait_pull_permille: 1000`（拉扯 ＝ 拉扯原語 2 點 × 每輪）與 `summon_trait_platform_permille: 1000`（高台 ＝ 升起地形原語 2 點 × 高度 × 每輪），`skillgen/budget.py` 的 `summon_trait_points` 在 `inert` 濾掉每輪特性之後再加入。兩招各 2 × 4 輪 × 800‰ ＝ 6.4 點，落在 6.1～8.7 的合格區間內。藤蔓的纏繞、守護靈的護盾仍未計價（本來就過，沒動）。
