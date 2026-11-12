# Phase NW-2 計畫：數值工坊開放技能——技能數值、預算比例、分組改、單位招式組、地圖戰小模擬與單招施放率

> **草稿**（開發 PM 的規格助手起草，2026-11-12；依據本機 main `760fe90a`，含 NW-1a `61cdfe4d` 與 NW-1b 的交件、BAL-21e 報告）。第 0 節「待決」的建議是暫採的做法，開發 PM（技術類）與使用者（規則類）確認後移進 0.0。
> 上層規格：`docs/phases/PhaseNW計畫.md`（以下稱「NW 計畫」）。本檔只寫 NW-2 新增或不同的地方；沒寫到的（三道門、草稿檔、備份、git 前置檢查、模擬工作一次一個、改前快取、確定性）**一律照 NW 計畫與 NW-1a／1b 的現行做法**。
> 實作者先讀：`docs/dev/上手-內容資料與模擬.md`（全文，尤其第七節數值工坊、第四節第 16、18 點）、NW 計畫第 0.0、3～5 節、`docs/phases/PhaseNW-1a報告.md` 第 1 節（端點表）、`docs/phases/PhaseBAL-21e報告.md` 第 2、4、6 節；前端段另讀 `docs/phases/PhaseNW-1b報告.md` 第 1 節與 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第一節。

## 0.0 已定（附出處）

使用者原話（2026-11-12，專案 PM 轉達）：「要改數值的都給我改就好 其他都按照建議」。專案 PM 交接同日紀錄的解讀：「技能比值目標只當報表參考線、數值工坊 NW-2（技能欄位）排最前、雙匕首另開玩法題、補量法器法術」（`docs/專案PM交接.md`，`760fe90a`）。

| # | 決定 | 出處 |
|---|---|---|
| D1 | **技能數值全部由使用者在數值工坊調**；PM 與 agent 不試數值、只出報表與建議；agent 不改本段白名單內的技能欄位（規格明寫時例外） | NW 計畫 0.0；使用者「要改數值的都給我改就好」 |
| D2 | **調法：逐招或分組，不提供全域倍率**（不開 `skill_scaling.yaml`、`skill_budget.yaml` 的係數、`rules/core.yaml` 的 `budget_reference_weapon_damage` 這類一改就動全部技能的欄位） | 使用者「其他都按照建議」；BAL-21e 第 6 節「不建議用全域倍率」 |
| D3 | **預算超出合格區間（70%～100%）**：即時顯示比例；超出時紅字警告、預設不能寫回；使用者勾「我確定」後可寫回，並自動登記進 `skill_budget.yaml` 的 `known_budget_exceptions`（註解「數值工坊 日期」） | NW 計畫第 0 節第 4 列（使用者答覆提案 7 項「都照建議」第 (4) 項，NW 計畫 0.0） |
| D4 | **BAL-21e 的比值目標只當參考線**，工坊顯示、不擋寫回：無條件單體 ≥ 0.9、條件成立 ≥ 1.1、條件不成立約 ≥ 0.6、1 AP 箭類約 ≥ 0.6（後兩條標「建議，未定案」） | 專案 PM 交接（`760fe90a`）「技能比值目標只當報表參考線」；BAL-21e 第 6 節 |
| D5 | **雙匕首不在本段**（另開玩法題；工坊不做「對某把武器的倍率」） | 同上「雙匕首另開玩法題」 |
| D6 | **招式組的敵人專用招規則**：敵人範本可以裝 `enemy_only` 招；玩家這一邊（`content/sim/builds.yaml` 的 `companions`、build 英雄、傭兵用的單位）不能裝——由既有載入檢查 `player_template_enemy_only_problems`（`src/trpg/content/library/unit_checks.py:122`）擋，工坊只把它的錯誤對到欄位 | Phase 5F-3b（玩法 PM 2026-11-03 代決，`SkillDef.enemy_only` docstring） |
| D7 | **寫回後的收編**：使用者的值為準；寫回後變紅的固定答案測試與快照，由開發 PM 派「收編」小段**只更新測試、不動使用者的數值**，逐項證明變動來自那筆 `tune:`（拿掉後回到舊值） | NW 計畫第 0 節第 6 列、5.3 末段；`docs/開發PM交接.md` 3.0000 第 6 點 |
| D8 | 寫回、git、備份、三道門、草稿、模擬工作一次一個、程序池 `min(4, 核心數 − 2)`、單次上限 160 場、改前快取、不做熱載入、還原＝反向改動單 | NW 計畫 0.0、第 0 節第 1～3、5、7、8 列（使用者「都照建議」） |
| D9 | 會被 `bundled_content_dir()`／`default_content_dir()` 在 schema 匯入時讀的檔不開（草稿複本看不到） | NW 計畫第 3 節「一律不開」、附錄風險 2；`content/tuning_fields.yaml` 的 `forbidden_files` |

## 0. 待決

### 0.1 規則類（問使用者；專案 PM 轉達）

| # | 問題 | 出處／理由 | 建議 |
|---|---|---|---|
| R1 | **招式組改完，敵人的招數低於 #149 的下限**（一般 2 招、精英 3 招、頭目每階段 3 招）時怎麼辦 | #149 是寫進設計的規則，由 `tests/content/test_enemy_skill_count_149.py`（`MOB, ELITE, BOSS = 2, 3, 3`）鎖住；**不是載入檢查**，所以工坊的驗證不會擋，寫回後只在 PM 的全量才紅。收編段照 D7 只能「更新測試」，但這等於放寬一條設計規則，照開發 PM 交接第 7 點不能自己放寬 | **和預算例外同一套**：低於下限時紅字警告「低於 #149 的招數下限」、預設不能寫回；勾「我確定」後可寫回，`tune:` commit 內文加一行「#149 例外：<單位>」，收編段把該單位加進測試的 `EXEMPT` 並在報告引用那筆 commit。理由：使用者決定數值，但規則的例外要看得見、可追溯 |
| R2 | **超出預算的 1 階招，到了 2 階以上會被夾回 100%** | 升階重算 `retier`（`src/trpg/skillgen/skill_tier.py:560`，#72／3W-9b）「維持原本的比例，夾在 70～100% 窗內」；玩家角色升階、**大世界敵人等級高於該招階級時**（`src/trpg/world/battle.py:237-258`）都會重配。所以使用者把一招調到 120% 只在 1 階生效，2 階以上變回 100%；調法若是「把傷害從條件段搬到基礎段、總比例不變」，升階後也會被預算器重新分配（BAL-21c：頭目實戰用 `_t3`，改 1 階骰子對頭目沒影響，上手-內容 第四節第 18 點） | **照現行規則（夾回 100%），不改引擎**；工坊在技能表單頂端顯示唯讀提示：「這招在 2 階以上會依預算比例重算（夾在 70～100%），超出的部分只在 1 階有效」，並列出「哪些單位實戰會用升階版（等級→階級）」。要讓超出的比例保留到高階，另開玩法題 |

> 其餘看起來像規則的問題都已能依既有決定定案（0.0 的 D2～D7），不再問使用者。

### 0.2 技術類（開發 PM 可定）

| # | 問題 | 建議（暫採） | 理由 |
|---|---|---|---|
| T1 | 白名單怎麼表達「只對某些原語開某欄位」 | `TuningField` 加選填 `effect_types: [damage, heal…]`；路徑含 `effects[*]`（或 `followup.effects[*]`、`variants[*].add_effect`…）時，`concrete_fields` 只展開 `type` 在清單內的效果。和 NW-1b 的 `_phase_skipped` 同一類（程式裡的展開規則），但寫在 YAML 上 | 守則 4：加欄位只改 YAML；一份白名單就能逐原語列 |
| T2 | 新欄位型別 | `kind` 加三種：`dice`（`NdM` 字串，畫面可打字也可按「±1 級」）、`range`（整數；現值是 `weapon`＝武器射程時唯讀）、`skill_ids`（技能 ID 清單）。`int`／`permille` 照舊 | 骰子與清單是 NW 計畫 5.2 預告的兩種新寫法；`weapon` 射程改成數字會改變技能的武器綁定語意，屬結構 |
| T3 | `yaml_patch` 擴充 | 骰子：純量字面替換（現有 154 個技能檔的骰子都沒加引號；有引號照舊擋）。清單：**整個序列節點換掉**——流式 `[a, b]` 換成新的流式字面；區塊式照原縮排重寫各行；序列範圍內有註解就擋（同 NW-1a「刪除帶註解的行一律擋」）；行尾註解保留（`skills: [...]  # BAL-21b…`） | NW 計畫 5.2；單位的 `skills` 全是流式加行尾註解（`content/units/ashen_heart.yaml:20`） |
| T4 | 預算即時顯示的算法 | 每次改值（前端停止輸入 0.3 秒）送 `POST /api/tuning/skills/{id}/budget`：後端用**服務啟動時載入的內容庫**＋草稿套用後的這一招 `SkillDef`（單檔 pydantic 驗證）呼叫 `skill_budget(skill, library)`、`validate_skill`，回比例與違規；整包驗證照舊在停止輸入 0.5 秒後跑 | 實測全部 401 招算一次預算 0.017 秒（`load_library` 0.47 秒，本機 2026-11-12）；預算只依賴表（`skill_budget.yaml`、`skill_primitives.yaml`、`statuses.yaml`…），不依賴別招，所以不必等 1.2 秒的整包驗證 |
| T5 | 例外登記的寫法 | 寫回時由後端產生「附帶改動」（不在白名單、使用者不能直接改）：把 ID 依字母序插進 `known_budget_exceptions` 的流式清單；**在該行上方插一行註解** `# 數值工坊 2026-11-12：skill_xxx 比例 112.4%（使用者確認）`；某招回到合格區間時自動從清單移除並刪掉它那一行註解（只刪工坊寫的、格式完全相符的那行）。差異頁、確認視窗都列出這筆附帶改動 | `tests/skillgen/test_range_budget.py:78` 要求清單**恰好等於**超出區間的內建技能，所以「回到區間要移除」不能漏；原行尾已有一段註解，逐項註解只能另起一行 |
| T6 | 分組改的上限與「全選」 | 一次分組最多 **100 招**；必須至少選一個篩選條件或手動勾選；不提供「全部技能」按鈕 | D2 不給全域倍率；100 招涵蓋最大的一組（1 階近戰武器技 77 招） |
| T7 | 分組的倍率怎麼取整 | `‰ 倍率`：新值 ＝ 舊值 × N ÷ 1000，**四捨五入到整數（.5 進位，整數運算）**，再夾在原語的 min／max；`±N`：直接加減再夾；`±1 級`：武器倍率照 `skill_composer.yaml` 的 `multipliers` 階梯、骰子照 `dice` 階梯（依平均值由弱到強；同平均取顆數少的）找鄰級；夾到邊界或找不到時該招列「跳過（原因）」 | 確定性；階梯沿用組合器的唯一來源，不另寫一份 |
| T8 | 不開的技能 | `skill_gear_*`（3 招，裝備附帶，預算本來就不檢查）；劇情技能（不在 `content/skills/`）；`kind: modifier` 的 `modifiers[*].change.*`（鍵的合法範圍在 `modifier_changes.yaml`，固定資料夾讀）先不開，NW-3 再議 | 最保守；修正技只有 11 招，數值少 |
| T9 | 地圖戰情境的陣容 | 地圖的預設 `encounter`（`map_spec`），另可「我方換成 build」（`--ally-build` 同款，`trpg.sim.lineup.build_allies`）；**受測招不在任何人身上時**，提供「裝到某個 build 英雄身上」（記憶體裡替換 build 的技能欄，只影響模擬，不寫回） | 玩家招多半只在 build 上；不必為量一招改內容 |
| T10 | 單招施放率的分母 | 「裝了這招的單位的行動回合數」（`TurnStarted`）；分子＝這招的 `SkillUsed`（去掉 `_t<階>` 尾碼）；另列「每場平均次數」；分母 < 30 標「樣本小」 | 和頭目施放率同一個定義（NW 計畫 5.4、上手-內容 第七節坑 7） |
| T11 | 比值重算的規模 | 預設每組 **50 種子**（BAL-21e 是 250）；單次上限「武器×招×情境的組數 × 種子 ≤ 40,000」（估約 90 秒，程序池 4）；畫面先顯示「N 組 × M 種子、預估 X 秒」 | BAL-21e：1079 組 × 250 種子＝27 萬場程序池 4 約 10 分鐘，約每秒 450 場 |
| T12 | BAL-21e 全表在工坊怎麼看 | 比值結果 JSON 以「`content/` 樹雜湊 ＋ 參數」為鍵存 `<save_dir>/tuning/ratios/`；提供「匯入一份 `t1_skill_ratio.py run` 的 JSON 當基準」（雜湊對不上時標「內容已變，僅供參考」）；技能表單顯示目前比值與參考線 | 全量 10 分鐘不適合在工坊跑；PM 已有的報表直接用 |
| T13 | commit 訊息 | 單招：`tune(<技能 ID>): <欄位> <舊>→<新>…`（同 NW-1a）；多招：`tune(skills×<N>): <分組說明或第一筆>…`，內文逐筆列；含例外時內文加「預算例外：…」「#149 例外：…」 | 同 NW 計畫第 0 節第 3 列的格式延伸 |

## 1. 現況查證（只讀，main `760fe90a`）

| 項目 | 現況 | 出處 |
|---|---|---|
| 技能檔 | `content/skills/*.yaml` 404 個（一檔一招；`enemy_only: true` 24 個；`skill_gear_*` 3 個）。常見寫法：`shape: {type: single, range: weapon}` 流式、`effects:` 區塊式清單裡放流式 mapping（`- {type: damage, multiplier_permille: 800}`）、偶有區塊式效果與註解（`skill_pinpoint_shot.yaml`）、`cost: {stamina: 10, cooldown: 2}` 流式 | 掃描 `content/skills/` |
| schema | `SkillDef`（`src/trpg/content/skills/skill.py:122`）：`ap_cost`（主動 1～3，其他 `null`）、`shape: ShapeSpec`（`effects.py:37`：`size`、`range`（整數或 `weapon`）、`radius`、`jumps`、`jump_range`、`arm`）、`effects: EffectSpec`（`effects.py:70`）、`cost: SkillCost`（`specs.py:40`：`mana`、`stamina`、`cooldown` 1～6、`uses_per_battle`、`hp_percent`、`stacks`、`self_status`、`overdraft`、`source`）、`crit_range` 15～19、`damage_permille` 100～999、`followup: FollowupSpec`（`specs.py:65`）、`variants: VariantSpec`（`variants.py:87`：`range_delta`、`add_effect`、`replace_effect`）、`stance_upkeep` 0～2 | 同左 |
| 原語參數範圍 | `content/skill_primitives.yaml` 53 個原語，`params.<名>.min/max` 是 int 參數**唯一的範圍來源**（Phase 3E-2f），由 `effects.py:254` 在 schema 匯入時從 `default_content_dir()` 讀；骰子 `Dice` 顆數 ≤ 100、面數 ≤ 1000（`battle.py:92-93`） | 同左 |
| 內容裡實際出現的數值欄位（次數） | `ap_cost` 338、`cost.cooldown` 322、`cost.mana` 233、`shape.range`（整數）199、`effects[*].dice` 156、`effects[*].duration` 155、`effects[*].multiplier_permille` 151、`cost.stamina` 133、`effects[*].distance` 24、`followup.shape.range` 17、`effects[*].amount` 15、`followup.effects[*].dice` 13、`shape.size`／`radius` 各 15，其餘 ≤ 10 | 掃描腳本（暫存區） |
| 預算 | `skill_budget(skill, library)`（`trpg.skillgen.budget`）回 `BudgetReport`（`ratio`、`min_ratio`、`max_ratio`、`variants[].report`、`segments`）；`trpg skills budget <id>` 的印法在 `src/trpg/cli/budget.py:117`（`print_skill_budget`）；全庫檢查 `library_violations`（`src/trpg/skillgen/library_check.py`，NW-1a 搬來）對 `known_budget_exceptions` 內的招不計 `budget.over`／`budget.weak` | 同左 |
| 例外清單 | `content/skill_budget.yaml:18` 單行流式 `known_budget_exceptions: [skill_summon_elite]  # …`；`tests/known_budget_exceptions.py` 由它產生；`tests/skillgen/test_range_budget.py:78` 斷言清單**恰好等於**超出區間的內建技能（不含 `skill_gear_*`） | 同左 |
| 1 階武器技預算分布 | 主動、非敵人專用的 1 階武器技 122 招：比例四捨五入到 0.1 為 0.7：15、0.8：40、0.9：47、1.0：20（≥ 95% 的 20 招）。例：火焰箭矢 78.8%、點射 93.6%、遠距狙擊 77.5%、斷腱射擊 74.3%。**提高傷害多半會超出 100%**，例外流程會常用到 | 本機 2026-11-12 量 |
| 升階重算 | `retier`（`skill_tier.py:560`）維持比例、夾在 70～100%；大世界敵人等級對應階級高於招的階級時照 `at_run_tier` 重配（`world/battle.py:237-258`）；roguelite 玩家技能一律等於角色階級 | 同左；0.1 R2 |
| 單位招式組 | `UnitTemplate.skills`（`battle.py:1655`，`skill_xxx` 格式、不可重複、≤ 32、數量上限依 `core.yaml` 的 `skill_slots`、`weapon_req` 要和武器相容——載入時檢查）；`BossPhase.skills`（`battle.py:1557`，`None`＝沿用）；開場階段（沒有 `trigger`）沒有 `skills`。全部單位檔的 `skills` 是流式清單、多數帶行尾註解 | 同左 |
| 白名單 | `content/tuning_fields.yaml`（只有 `kind: unit`）、`src/trpg/content/tuning_fields.py`（`TARGET_MODELS = {"unit": UnitTemplate}`、`kind: Literal["int", "permille"]`、`_leaf_is_int` 檢查整數欄位） | 同左 |
| 字面替換 | `src/trpg/api/tuning/yaml_patch.py`：只有整數純量（替換、插入、刪除）；錨點、加引號的值、刪除帶註解的行擋下 | 同左 |
| 驗證 | `api/tuning/check.py`：轉型（`_to_int`）→ 白名單＋`old` 比對＋字面替換 → `UnitTemplate` 單檔 → 草稿複本 `load_checked_library`＋`library_violations` | 同左 |
| 地圖戰模擬 | `trpg.sim.batch.map_spec`（`batch.py:116`，地圖 `encounter`、可換我方）、`run_outcomes`、`build_report`（`_skill_rows`：每場使用次數、命中率、平均傷害，**沒有「每回合」分母**）；地圖 80 場 `--jobs 4` 27.8 秒（`BAL-6/maps_retest.txt`）；`content/maps/` 17 張，有 `encounter` 的 15 張（`test_*` 兩張沒有；扣掉靶場 `training_range` 可用 14 張） | 同左 |
| 比值腳本 | `scripts/t1_skill_ratio.py`（826 行；`run`／`report`；匯入 `trpg.roguelite.start`、`trpg.world.opening`、`trpg.engine`）；**`scripts/` 不是套件，`trpg.api` 匯入不到**；122 招、1079 組、每組 250 種子、程序池 4 約 10 分鐘；目前只量 `category: weapon`（法器法術 84 招待補量，專案 PM 交接「補量法器法術」） | BAL-21e 報告第 1、6 節 |
| 依賴方向 | `trpg.sim` 可匯入 `roguelite`、`world`；`api` 只禁 `cli` | `pyproject.toml` import-linter |

## 2. 和 CLAUDE.md 守則的關係

- **守則 1、2**：引擎不改。分組改的取整、階梯查找、例外清單排序都是整數運算與排序。
- **守則 3**：沒有 LLM。
- **守則 4**：可改欄位只寫在 `content/tuning_fields.yaml`（T1 的 `effect_types` 讓「逐原語」也是資料）。
- **守則 5**：新程式在 `trpg.api.tuning`（技能對象、預算、分組、招式組）與 `trpg.sim`（`skill_probe.py` 單招施放率、`skill_ratio.py` 比值核心）；`skill_ratio.py` 要匯入 `trpg.roguelite`、`trpg.world`，`sim` 允許。`lint-imports` 與 `tests/test_architecture.py` 照跑；`trpg.api.tuning` 若走訪全部技能（分組篩選、例外清單），照 NW-1a 的寫法登記 `LIBRARY_SKILLS_ITERATION_ALLOWED`（理由：數值工坊要列敵人專用招）。
- **守則 8**：本段不改任何數值，不需平衡模擬；比值重算的冒煙只跑 1～2 招、每組 5 種子。
- **守則 11**：工坊內的模擬照 NW 計畫 5.4 的上限；agent 只跑冒煙規模。

## 3. 範圍

**目標**：使用者在數值工坊選一招（或用篩選選一組）→ 看到中文標籤的技能數值、即時預算比例、BAL-21e 比值與參考線 → 改值（單招或分組套同一個改動）→ 超預算時勾「我確定」→ 選一張地圖跑小模擬看勝率與這招的施放率 → 寫回並自動 commit（必要時連同例外清單）。另外能改敵人與頭目各階段會放哪些招。

### 3.1 技能欄位白名單（`content/tuning_fields.yaml` 新增 `kind: skill` 對象，`glob: skills/*.yaml`，`exclude: [skill_gear_*]`）

**技能層級**

| 路徑 | 中文標籤 | kind | 範圍來源（擋）／建議範圍（提示） | 備註 |
|---|---|---|---|---|
| `ap_cost` | AP 消耗 | int | schema：主動 1～3；非主動技能不展開 | 改 AP 會換預算係數（`ap_coefficient_permille`），比例會大跳 |
| `cost.stamina` | 耐力消耗 | int | ≥ 0；建議 0～30 | 沒寫＝0（插入） |
| `cost.mana` | 法力消耗 | int | ≥ 0；建議 0～40 | 同上 |
| `cost.cooldown` | 冷卻（回合） | int | 1～6；可清空＝沒有冷卻（刪除鍵） | 代價折抵會變 |
| `cost.uses_per_battle` | 每場次數上限 | int | ≥ 1；可清空 | 只有已寫的招展開（1 招） |
| `cost.hp_percent` | 消耗生命（‰） | permille | 1～999 | 只有已寫的招展開 |
| `cost.stacks` | 消耗層數 | int | ≥ 1 | 只有已寫的招展開 |
| `cost.source` | 源力消耗 | int | 1～2 | 只有已寫的招展開 |
| `cost.self_status.duration` | 自身代價狀態持續 | int | 照 schema | 只有已寫的招展開 |
| `stance_upkeep` | 姿態維持費 | int | 0～2 | 只有 `kind: stance` 展開 |
| `crit_range` | 暴擊下限 | int | 15～19；可清空 | 要有傷害效果（schema 擋） |
| `damage_permille` | 基礎傷害折扣（‰） | permille | 100～999；可清空 | 同上 |
| `shape.range` | 射程 | range | 照 `skill_shapes.yaml` 該形狀 `params.range` 的 min／max；現值 `weapon` 時唯讀顯示「武器射程」 | 射程係數會改預算（`range_baseline: 4`，每格 ±5%） |
| `shape.size`、`shape.radius`、`shape.jumps`、`shape.jump_range`、`shape.arm` | 範圍大小／半徑／跳躍次數／跳躍距離／臂長 | int | 照該形狀 `params` 的 min／max | 只展開該形狀有的參數 |
| `condition.permille` | 條件門檻（‰） | permille | 照 `skill_conditions.yaml` | 例 `target_hp_below` 400；只有已寫的招展開 |
| `trigger.max_per_round`、`trigger.n`、`trigger.max_distance` | 每輪觸發上限／第 N 次／觸發距離 | int | 照 schema | 被動技能 |
| `trap.rounds` | 陷阱持續 | int | 照 schema | 陷阱技能 |
| `followup.shape.*` | 第二段的射程與範圍 | 同上 | 同上 | 複合技能 |
| `variants[*].range_delta` | 變奏射程增減 | int | 照 schema（結果至少 1） | |

**效果層級**（路徑 `effects[*].<欄位>`；同一套也展開到 `followup.effects[*]`、`variants[*].add_effect`、`variants[*].replace_effect.effect`，以及巢狀的 `effects[*].then[*]`（`consume_status`）、`effects[*].effects[*]`（`zone`）、`effects[*].on_kill[*]`、`effects[*].win[*]`／`lose[*]`（`gamble`）；`effect_types` 照原語篩，範圍一律來自 `skill_primitives.yaml` 的 `params.<名>.min/max`，畫面只顯示）

| 原語（`type`） | 可改欄位（kind；範圍） |
|---|---|
| `damage` | `dice`（dice）、`multiplier_permille`（permille；1～10000）、`flat_bonus`（int；1～10）、`lifesteal_permille`（1～500）、`form_bonus_permille`（1～1000）、`spread`（1～2）、`scaling.per_step_permille`、`scaling.cap_permille`（permille） |
| `heal` | `dice`、`flat_bonus`（1～10）、`form_bonus_permille`（1～1000） |
| `shield` | `dice`、`flat_bonus`（1～10）、`duration`（2～3） |
| `push`、`pull` | `distance`（1～2）、`collision_dice` |
| `blow_surface` | `distance`（2～3） |
| `charge_through` | `dice` |
| `hurl_object` | `range`（1～6）、`dice` |
| `apply_status` | `duration`（1～10）、`magnitude_permille`（1000～2000，只有已寫的招展開：姿態） |
| `create_surface` | `duration`（1～10）、`magnitude_permille`（1000～2000，只有已寫的） |
| `create_obstacle` | `duration`（1～10） |
| `add_stack` | `amount`（1～3）（＝狀態／疊層的層數） |
| `consume_stack` | `per_stack_permille`（50～500） |
| `consume_status` | （本身沒有可調數值；`then[*]` 照上表） |
| `grant_ap` | `amount`（1～2） |
| `cheat_death` | `duration`（1～2） |
| `redirect_damage` | `permille`（100～500）、`duration`（1～3） |
| `restore_resource` | `amount`（1～10） |
| `reveal` | `duration`（1～3） |
| `revive` | `hp_permille`（100～1000） |
| `delayed_damage` | `dice`、`rounds`（1～3）、`radius`（0～2） |
| `summon` | `duration`（1～4）、`power_permille`（100～2000，只有已寫的）、`max_hp_permille`（1～1000，只有已寫的）；`count` 不開（2 隻時 `power_permille` 必填，屬結構） |
| `zone` | `duration`（1～4）、`speed`（1～2）；`effects[*]` 照上表 |
| `gamble` | `chance_permille`（50～950）；`win[*].damage_multiplier_permille`（1500～3000）、`lose[*].self_damage_permille_of_hit` |
| `grant_skill` | `duration`（1～4） |
| `inscribe` | `duration`（1～5） |
| `detonate_runes` | `dice` |
| `sacrifice_summon` | `dice`、`radius`（0～2） |
| `enter_form` | `magnitude_permille`（1000～2000，只有已寫的） |
| `on_kill` 的 `refund_ap` | `amount`（1～2） |
| **沒有可調數值、不展開**：`cleanse`、`knock_prone`、`shockwave`、`teleport`、`dash`、`leave_form`、`shadowstep`、`leap`、`swap`、`teleport_target`、`swap_any`、`destroy_object`、`intercept`、`place_trap`、`reset_cooldown`、`copy_skill`、`topple`、`steal_buff`、`clear_surface`、`rule_change`；範圍只有一個值的 `raise_terrain.amount`、`lower_terrain.amount`、`extra_reaction.amount`、`dispel.count`、`consume_status.splash` | |

「只有已寫的招展開」＝欄位沒寫時不給插入（插入會讓沒有該機制的招多一個機制，屬結構）。其餘欄位沒寫時可插入（例 `cost.cooldown`）。

### 3.2 一律不開（白名單的禁止表與不展開的欄位）

- **檔案**（D9、NW 計畫第 3 節）：`skill_primitives.yaml`、`skill_shapes.yaml`、`modifier_changes.yaml`、`llm/*.yaml`（schema 匯入時從固定資料夾讀）、`rules/hit_table.yaml`、`skill_icon_*.yaml`、`tuning_fields.yaml`。
- **全域表**（D2）：`skill_budget.yaml`（使用者不能直接改；只有 T5 的例外清單由後端附帶改動）、`skill_scaling.yaml`、`skill_synergies.yaml`、`skill_conditions.yaml`、`skill_triggers.yaml`、`skill_composer.yaml`、`skill_keywords.yaml`、`skill_exclusions.yaml`、`rules/core.yaml`（含 `budget_reference_weapon_damage`、`tier_budget`）、`statuses.yaml` 的 `budget_points`。
- **技能的非數值欄位**：`id`、`name_zh` 與所有 `*_zh`、`narrative`、`provenance`、`tier`、`rank`、`rarity`、`kind`、`skeleton`、`category`、`weapon_req`、`weapon_only`、`scaling_attr`、`secondary_scaling_attr`、`mastery`、`shape.type`、效果的 `type`／`affects`／`status`／`surface`／`object`／`element`／`condition`（條件種類）、`tags`、`element`、`followup.when`／`anchor`／`release`、`variants[*].when`、`enemy_only`、`pool_regions`、`icon_prop`、`budget_bonus_permille`、`activation`、`exclusive_group`、`pierce`、`include_caster`、`modifiers[*]`（T8）、`shape.range` 為 `weapon` 時。
- **結構改動**：新增／刪除效果、變奏、第二段、條件；換原語或形狀。這些仍走技能工坊或 agent。

### 3.3 單位招式組（`kind: unit` 對象加欄位）

| 路徑 | 中文標籤 | kind | 規則 |
|---|---|---|---|
| `skills` | 技能（開場） | skill_ids | 只能從 `content/skills/` 既有 ID 選；不可重複；數量 ≤ `core.yaml` 的 `skill_slots`；`weapon_req` 要和單位武器相容（載入時檢查，錯誤對到欄位）；敵人專用招照 D6 |
| `phases[*].skills` | 第 N 階段技能 | skill_ids | 開場階段不展開（同 NW-1b `_phase_skipped`）；空清單＝`[]`；「沿用上一階段」＝刪除鍵 |

- 選單：可搜尋中文名或 ID；每招顯示「敵人專用」標記、武器需求、1 階預算比例；和單位武器不相容的招灰掉並寫原因。
- 招數低於 #149 下限時照 R1（暫採：警告＋「我確定」）。
- `reactions`（反應技）不在本段（列進 NW-3 或另議，報告列出）。

### 3.4 範圍外

熱載入；新增或刪除技能、改結構（3.2）；全域倍率（D2）；雙匕首的武器倍率（D5）；修正技的 `modifiers`（T8）；反應技清單；1 階法器法術的比值量測本身（專案 PM 已排「補量法器法術」另段；NW-2c 的核心若屆時腳本已支援 `--category spell`，一併支援）。

## 4. 切段

| 段 | 內容 | 完成後使用者能做什麼 | 前置 |
|---|---|---|---|
| **NW-2a** 後端 | 白名單 `kind: skill` 與 T1／T2 的 schema 擴充；`yaml_patch` 骰子與清單（T3）；技能單檔驗證；即時預算端點（T4）；例外清單附帶改動與自動移除（T5）；分組改預覽（T6、T7）；單位 `skills`／`phases[*].skills`；R1 的下限檢查（回警告）；`trpg.sim.skill_probe`（地圖戰＋單招施放率）與模擬工作接上新情境；OpenAPI 重產 | （沒有畫面；PM 可用 `/docs` 試） | NW-1b 合併 |
| **NW-2b** 前端 | 對象清單加「技能」分類（篩選：階級、武器技／法術、近戰／遠程、AP、主動／被動、敵人專用、有條件）；技能表單（效果分組顯示、骰子 ±1 級、預算比例條與合格區間、超出紅字＋「我確定」、R2 提示）；分組改面板；招式組編輯器；模擬面板加「地圖戰」情境與單招施放率；差異頁與確認視窗列附帶改動與例外 | **改技能的傷害、消耗、冷卻、範圍；一次改一組；改敵人會放哪些招；看預算比例；在示範地圖上看某招被放幾次、勝率怎麼變** | NW-2a 合併 |
| **NW-2c** 比值 | `scripts/t1_skill_ratio.py` 核心搬進 `src/trpg/sim/skill_ratio.py`（腳本改薄包裝，輸出逐字相同）；比值工作（T11，改前改後並排）；基準匯入與快取（T12）；技能表單與分組面板顯示比值與參考線（D4） | 加上：**在工坊裡看每招目前的比值與參考線，改完重算這幾招的比值** | NW-2b 合併；可和 NW-3 規格平行 |

理由：2a／2b 合起來是「能調技能」的最小可用；比值重算要搬 826 行的腳本、還要前端，分出 2c 讓前兩段早點交給使用者。2c 之前，工坊用 T12 的「匯入 JSON」顯示 BAL-21e 的現成比值也可以（若 PM 要在 2b 就看到，把 T12 的匯入與顯示提前到 2a／2b，比值工作仍留 2c）。

## 5. 技術做法（實作者照做；有更好做法先問 PM）

### 5.1 白名單 schema 擴充

- `TuningTarget.kind: Literal["unit", "skill"]`；`TARGET_MODELS["skill"] = SkillDef`。
- `TuningField` 加：`kind` 新增 `dice`、`range`、`skill_ids`（T2）；選填 `effect_types: tuple[str, ...]`（T1，值必須是 `skill_primitives.yaml` 的原語 ID，載入檢查）；選填 `existing_only: bool`（「只有已寫的招展開」）；選填 `kinds: tuple[SkillKind, ...]`（例 `ap_cost` 只給 `active`、`stance_upkeep` 只給 `stance`）。
- `_leaf_is_int` 改成依 `kind` 檢查葉節點型別：`int`／`permille`／`range` 對整數（`range` 另接受 `Literal["weapon"]`）、`dice` 對 `Dice`、`skill_ids` 對 `tuple[str, ...]`。
- 路徑展開（`concrete_fields`）：依 `effect_types` 比對該位置效果的 `type`；巢狀效果路徑一律寫在 YAML（不在程式裡遞迴猜）。
- T-A1 照 NW-1a：每個路徑在**所有** `content/skills/*.yaml` 上都對得到 schema。

### 5.2 `yaml_patch` 擴充（T3）

- 骰子：純量替換，新值必須符合 `^\d+d\d+$`；插入同整數。
- 清單：見 T3；替換後重新 parse 必須等於「原資料只改那一個清單」；`difflib` 只動那一行（流式）或那幾行（區塊式）。
- 例外清單（T5）：專用函式 `patch_exception_list(text, add=[…], remove=[…], date)`，只動 `known_budget_exceptions` 那一行與它上方的工坊註解行；其他位元組不動。

### 5.3 預算即時顯示與例外（D3、T4、T5）

- 端點 `POST /api/tuning/skills/{skill_id}/budget`：body＝這招的改動（可省略＝現值）。回 `ratio`（‰ 整數與顯示字串，照 `ratio_pct`）、`min_ratio`、`max_ratio`、`verdict`（合格／超出預算／過弱）、`variants[]`（每個變奏的比例與判定）、`segments[]`（複合技能兩段點數）、`violations[]`（`validate_skill` 的中文訊息與規則 ID，不含預算範圍以外的錯誤時照常列）、`known_exception`（目前是否在例外清單）。數字必須和 `trpg skills budget <id>` 一致（測試對 20 招逐招比）。
- **寫回的閘門**：草稿裡任何一招（含變奏）超出區間，且沒有勾「我確定」→ `apply` 回 409「技能 X 預算 112.4% 超出合格區間，要寫回請勾『我確定』」。勾了 → `apply` 的 body 帶 `confirm_budget: [skill_ids]`，後端核對清單恰好是超出的那幾招，再產生 T5 的附帶改動。
- 自動移除：草稿讓某個**在例外清單裡**的招回到區間 → 附帶改動把它移除（不需要勾）。手寫的例外（例 `skill_summon_elite`）也照這條移除，確認視窗明列。
- 整包驗證時，`library_violations` 對「草稿＋附帶改動」跑，所以勾了「我確定」的招在整包檢查裡不再算錯。

### 5.4 分組改（D2、T6、T7）

- `POST /api/tuning/skills/group-preview`：body＝`{skills: [id…] | filter: {...}, target: <欄位選擇器>, op: {kind: set|add|scale_permille|ladder, value}}`。
- **欄位選擇器**：`ap_cost`、`cost.stamina`、`cost.mana`、`cost.cooldown`、`shape.range`，以及傷害三種：「所有傷害效果」「基礎傷害（沒有條件的傷害效果）」「條件段傷害（帶 `condition` 的傷害效果）」——對應 BAL-21e 建議的「基礎段提高、條件段降低」；傷害的 `ladder` 依該效果是 `multiplier_permille`（武器階梯）或 `dice`（骰子階梯）自動選；`scale_permille` 對武器倍率直接乘、對骰子不適用（該招列跳過，請改用 ±級）。
- 回應逐招列：`{skill_id, name_zh, changes: [Change…], before_ratio, after_ratio, verdict, skipped_reason}`；前端按「放進草稿」才把 `changes` 併進草稿（草稿與差異頁仍逐招逐欄）。
- 篩選條件（同前端清單）：`tier`、`category`、`weapon_req`、`ap_cost`、`kind`、`enemy_only`、`has_condition`、`shape.type`、`tags` 包含；加 BAL-21e 分類（無條件／條件類／非單體／召喚／非傷害，有比值資料時）。常用預設組：「1 階遠程武器技」「1 階近戰武器技」「1 AP 箭類（1 階、遠程、AP 1、單體傷害）」「2 AP 條件型（基礎 1000‰＋條件段）」。

### 5.5 招式組（3.3）

- 驗證順序：轉型（逐項 `skill_xxx` 格式、不重複）→ ID 存在 → `UnitTemplate` 單檔 → 整包（武器相容、`skill_slots`、玩家這一邊不能裝敵人專用招）。錯誤對到 `skills` 或 `phases[i].skills`。
- #149 下限（R1）：工坊自己算「該單位在第一季遭遇裡算一般／精英／頭目」——**和 `tests/content/test_enemy_skill_count_149.py` 用同一個函式**：把測試裡的 `_shortfalls` 判定搬到 `trpg.content`（或 `trpg.api.tuning`）的函式，測試改呼叫它（行為不變）。

### 5.6 地圖戰小模擬與單招施放率（T9、T10）

- 新 `src/trpg/sim/skill_probe.py`：`SkillProbeJob{map_id, seed, allies: Sequence[str] | None, inject: {build_id: skill_id} | None}`、`probe_task(root, job)`（照 `boss_probe` 的 `library_for` 快取）、`skill_tally`（每招：施放次數、裝備者行動回合數、每場次數；陣營分開）。
- 情境選單：地圖（有 `encounter` 的 14 張；`test_*`、`training_range` 不列）、我方（預設陣容／build 勾選）、受測招（從草稿改到的招預設帶入；可加）、種子數。**受測招不在任何人身上**時，畫面提示並提供 T9 的「裝到 build」。
- 指標：勝率、平均輪數、我方倒下率、受測招的施放率（分子／分母）與每場次數、改前改後差值、勝負翻轉場數；分母 < 30 標「樣本小」（同 NW-1b）。
- 規模：預設 24 場（1 張圖 × 24 種子，或 3 張圖 × 8 種子），可選 80；上限 160（D8）。估時用「地圖戰每場秒數」（另記，不和頭目共用；NW-1b 待決 5 的偏差問題）。
- 頭目招的施放率照舊用頭目戰情境（NW-1）。

### 5.7 比值重算（NW-2c；T11、T12）

- `scripts/t1_skill_ratio.py` 的量測核心（情境建構、條件成立的做法、`condition_met`／`variant_holds` 檢查、彙總）搬進 `src/trpg/sim/skill_ratio.py`；腳本保留 CLI 與印表。證據：`run --skills skill_fire_arrow,skill_pinpoint_shot,skill_rng_venom_arrow --seeds 20 --jobs 4` 搬家前後 JSON 與 stdout 的 SHA-256 相同（報告附指令與雜湊）。
- 工作：`POST /api/tuning/sims` 的情境加 `ratio`（`skills`、`seeds`）；改前結果以樹雜湊快取；結果逐招列「直接、含持續、成立直接、成立含持續、綁定武器」的範圍（同 BAL-21e 摘要表欄位）與參考線判定（D4，「建議，未定案」的兩條另標）。
- 估時（T11）：組數 ＝ Σ（招 × 可用武器 × 情境數）；預估秒數 ＝ 組數 × 種子 ÷ 每秒場數（上一次實測，預設 450）。

### 5.8 寫回後的收編（D7）

寫回本身照 NW 計畫 5.3。技能改動會讓下列「固定答案」變紅，**都走收編段、只更新測試**（本段先在 `docs/dev/上手-內容資料與模擬.md` 第七節列清單，收編段照表做）：

| 會變的 | 收編怎麼做 |
|---|---|
| `tests/skillgen/test_refactor_parity.py` 夾具（雜湊鎖整個技能 JSON） | 只重產被 `tune:` 動到的那幾招的項目；證明：用 `tune:` 前的 `content/` 重產等於舊夾具 |
| CLI 快照 `skills_list`、`skills_show_all`、`skills budget`（`tests/cli/test_output_snapshots.py -m slow`） | `UPDATE_CLI_SNAPSHOTS=1` 加 `-k` 只重產受影響的鍵（上手-內容 第四節第 2 點） |
| 前端快照 `skillCards.json`（`scripts/export_client_fixtures.py`）、`skill_icons.json`（數值不影響圖示時應不變） | 重產後 `git diff --stat` 只有那幾招 |
| AI 固定種子（`tests/cli/test_run_cli.py -m slow`、`tests/world/test_enemy_ai_moves_149.py`…） | 換種子不改斷言（上手-內容 第四節第 3 點） |
| 寫死數字的行為測試（例 `tests/engine/test_enemy_skills_149.py`） | 改成從內容讀，或更新數字並引用 `tune:` commit |
| `test_range_budget.py:78`（例外清單恰好等於超出的招） | 不應變紅（T5 自動維護）；紅了是工坊的 bug，回報開發 PM |
| `test_enemy_skill_count_149.py`、`tests/content/test_coverage.py::test_every_handwritten_skill_is_equipped_by_a_build_or_unit` | **規則型測試，不自行放寬**：R1 答覆前先回報；R1 照建議定案後，`#149 例外` 照 commit 內文加豁免。「每招都有人裝」被招式組改破時同樣先回報（建議同 R1 的做法，屬技術延伸，PM 可定） |

## 6. 受影響的既有功能

| 區塊 | 改／不改 | 說明 |
|---|---|---|
| 引擎 `trpg.engine` | 不改 | |
| `content/` 的資料 | 不改（工具本身）；`content/tuning_fields.yaml` 加 `kind: skill` 對象與單位的 `skills` 欄位 | 白名單不進 digest（NW-1a 已測） |
| `trpg.content.tuning_fields` | `kind` 擴充、`effect_types`／`existing_only`／`kinds`、葉節點型別檢查 | |
| `trpg.api.tuning` | `yaml_patch`（骰子、清單、例外清單）、`check`（`SkillDef` 單檔、例外閘門）、`objects`（技能對象、分類、唯讀提示）、新 `skills.py`（預算、分組）、`writeback`（附帶改動、commit 訊息 T13）、`sim_jobs`（地圖戰、比值情境）、`routes`／`schemas` | |
| `trpg.sim` | 新 `skill_probe.py`（2a）、`skill_ratio.py`（2c） | |
| `scripts/t1_skill_ratio.py` | 2c 改薄包裝 | 輸出逐字相同 |
| `tests/content/test_enemy_skill_count_149.py` | 判定函式搬家、測試改呼叫（行為不變） | 5.5 |
| OpenAPI 與前端型別 | 重產 | 照既有流程 |
| 前端 | `client/src/tuning/` 加技能表單、分組面板、招式組編輯器、地圖戰與比值結果表 | 只在 `?dev=1` |
| 測試的快照與固定種子 | 本段不動 | 使用者之後的 `tune:` 才會動（5.8） |

## 7. 交付項目

### NW-2a 後端
- **A1** 白名單：`kind: skill` 對象與 3.1 全部欄位；單位加 `skills`、`phases[*].skills`；schema 擴充（5.1）。
- **A2** `yaml_patch`：骰子、清單、例外清單（5.2）。
- **A3** 驗證：`SkillDef` 單檔（pydantic 錯誤轉中文、`loc` 對到欄位，含 `effects[i].dice` 這類路徑）；招式組（5.5）；R1 下限警告。
- **A4** 預算端點與寫回閘門、例外附帶改動與自動移除（5.3）。
- **A5** 分組預覽（5.4）。
- **A6** 對象：技能清單（分類、篩選欄位、使用這招的單位與其實戰階級——R2 提示用）、表單資料（欄位、現值、範圍、唯讀提示）。
- **A7** `trpg.sim.skill_probe`＋模擬工作的地圖戰情境（5.6）；地圖戰每場秒數另記。
- **A8** 寫回：附帶改動、commit 訊息（T13）；差異表列附帶改動。
- **A9** OpenAPI 重產；測試（第 8 節）；報告；上手筆記第七節更新（含 5.8 收編清單）。

端點（暫定，前綴 `/api/tuning`）：`GET /objects?kind=skill`、`GET /objects/skill/{id}`、`POST /skills/{id}/budget`、`POST /skills/group-preview`、`GET /skills/presets`（常用預設組）、`POST /drafts/{name}/apply` 加 `confirm_budget`、`confirm_min_moves`；`GET /sims/options` 加地圖戰（與 2c 的比值）情境；`POST /sims` 的 body 加 `scenario: boss|map|ratio`。

### NW-2b 前端
- **B1** 對象清單：「敵人與頭目」「技能」兩個分頁；技能篩選與常用預設組。
- **B2** 技能表單：依區塊分組（消耗與冷卻／形狀與射程／效果 1、2…／第二段／變奏），效果標題寫原語中文名；骰子欄位可打字也有「−1 級／＋1 級」；「只有已寫的」欄位沒值時不顯示。
- **B3** 預算比例條：比例數字、合格區間 70～100% 的底色、超出紅字與「我確定」勾選；變奏、複合兩段分列；`violations` 紅字在頁首；R2 提示；使用這招的單位列表。
- **B4** 分組面板：選招（篩選＋手動勾、最多 100）→ 選欄位與改法 → 預覽表（逐招前後值、前後預算比例、跳過原因）→「放進草稿」。
- **B5** 招式組編輯器：目前招式（可排序、移除）、加招選單（搜尋、敵人專用標記、不相容灰掉）；#149 下限警告與「我確定」。
- **B6** 模擬面板：情境「頭目戰／地圖戰」；地圖戰的地圖、陣容、受測招、「裝到 build」；結果表加單招施放率。
- **B7** 寫回確認視窗：列附帶改動（例外清單加入／移除）與例外勾選；差異頁同。
- **B8** vitest、截圖、報告（截圖存 `docs/art/shots/nw2/`，依 NW-1b 待決 8 的慣例）。

### NW-2c 比值
- **C1** `trpg.sim.skill_ratio`＋腳本薄包裝（5.7）。
- **C2** 比值工作與快取、基準匯入（T11、T12）。
- **C3** 前端：技能表單的比值區（目前值、參考線、與上次量測的差）；分組預覽加比值欄；模擬面板加「比值」情境。
- **C4** 測試、報告。

## 8. 行為一致測試

### NW-2a（pytest）
| # | 測什麼 |
|---|---|
| T-A1 | 白名單每個技能路徑在所有 `content/skills/*.yaml` 上對得到 schema；`effect_types` 的原語都存在；`existing_only`／`kinds` 的展開正確（`ap_cost` 不展開給被動；`magnitude_permille` 只給已寫的）；禁止表的檔與 3.2 的欄位不能出現 |
| T-A2 | `yaml_patch`：hypothesis 對全部技能檔的每個展開欄位改一次（整數、骰子）→ 重新 parse 只差那一個值、`difflib` 只動一行、註解一行不少；流式效果、區塊式效果、`cost` 沒寫的鍵插入、清空冷卻刪鍵；單位 `skills` 流式＋行尾註解、`phases[i].skills` 區塊式；例外清單加入／移除各兩招後逐位元組回到原樣 |
| T-A3 | 預算端點：20 招（含變奏、複合、被動、姿態、陷阱各至少一招）的比例與 `trpg skills budget <id>` 輸出的數字相同；改一個值後比例變化方向正確 |
| T-A4 | 寫回閘門（假 repo）：超出不勾 → 409、檔案不變；勾了 → 例外清單加入、註解行格式、commit 只含那幾個檔；把例外招調回區間 → 自動移除；`confirm_budget` 和實際超出的招不符 → 409；之後跑 `test_range_budget` 的同一個判定為真 |
| T-A5 | 分組預覽：`scale_permille` 取整（例 850 × 1100 ÷ 1000 ＝ 935、.5 進位）、夾到原語範圍；`ladder` 武器與骰子各走一級與到頂跳過；「基礎／條件段」選擇器只動對的效果；超過 100 招 422；沒有篩選也沒勾選 422；結果確定性（同輸入兩次相同、依 ID 排序） |
| T-A6 | 非法值帶中文原因與欄位路徑：`ap_cost: 0`、`cost.cooldown: 7`、`effects[0].dice: "2x6"`、`effects[0].multiplier_permille: 0`、`shape.range` 超出形狀範圍、`skills` 有不存在的 ID、重複、武器不相容、玩家這一邊的單位裝敵人專用招（若有開放的單位會被 build 使用；否則以假內容測） |
| T-A7 | #149 下限：判定函式搬家後 `test_enemy_skill_count_149.py` 照過；工坊把頭目某階段改成 2 招 → 警告；不勾 → 409；勾了 → commit 內文有「#149 例外」 |
| T-A8 | `skill_probe`：同參數兩次相同；施放率分子分母和逐場事件相加相符；「裝到 build」只影響模擬內容庫、不寫檔 |
| T-A9 | 改技能後三個 digest：`hash_ruleset` 變（技能在規則包裡）、`content_digest`／`ruleset_hash` 變；不套改動的複本三個都不變（沿用 NW-1a 測試加技能案例） |
| T-A10 | `lint-imports`、`tests/test_architecture.py`（含 `LIBRARY_SKILLS_ITERATION_ALLOWED` 新登記）；`trpg content check` 輸出逐字不變 |

### NW-2b（vitest）
| # | 測什麼 |
|---|---|
| T-B1 | 技能表單由 `/objects/skill/{id}` 的欄位產生（不寫死）；效果分組標題；骰子 ±1 級按鈕只在 `dice` 欄位 |
| T-B2 | 預算比例條：合格／超出／過弱三態的文字與顏色 class；超出時寫回停用、勾「我確定」後啟用；變奏分列 |
| T-B3 | 分組面板：上限 100、沒條件不能預覽、跳過原因、「放進草稿」後差異頁逐招逐欄 |
| T-B4 | 招式組：不相容灰掉、敵人專用標記、下限警告與勾選 |
| T-B5 | 模擬結果的單招施放率（分子分母、樣本小）；寫回確認視窗列附帶改動 |

### NW-2c
| # | 測什麼 |
|---|---|
| T-C1 | 搬家前後腳本 JSON 與 stdout SHA-256 相同（5.7 的指令） |
| T-C2 | 比值工作：同參數兩次相同；改前快取命中；上限 40,000 組×種子；參考線判定（無條件 0.89 → 低於 0.9、條件成立 1.12 → 達標） |

## 9. 驗收條件

1. 第 8 節測試全過；改到的既有測試逐條寫「舊斷言 → 新斷言」。
2. 每次 commit：`ruff check`、`ruff format --check`、`mypy`、`lint-imports`、相關測試；2b／2c 前端另 `corepack pnpm -C client typecheck`、`test`、`build` 三個結束碼分開記，全 0 才交。
3. **實機走一遍**（2b，在自己的 `trpg serve` 與 worktree 內的 clone；做法照上手-內容 第七節坑 5）：
   - 火焰箭矢 `effects[0].multiplier_permille` 800→900 → 預算比例即時變化、仍合格 → 地圖戰小模擬（`bandit_lair` 或 `open_plain`，冒煙規模）看到這招的施放率改前改後 → 寫回（clone 的 `main` 上一筆 `tune:`）→ 還原 → 檔案逐位元組回到原樣。
   - 同一招改到 1300 → 紅字「超出預算」、寫回停用 → 勾「我確定」→ 寫回 → `skill_budget.yaml` 多一筆與註解行 → 還原 → 例外清單與註解行自動移除、逐位元組回到原樣。
   - 分組：「1 階遠程武器技」的「基礎傷害」＋1 級 → 預覽表逐招列 → 放進草稿 → 差異頁逐招。
   - 招式組：灰燼之心第 2 階段拿掉一招 → #149 警告；加一招武器不相容的 → 欄位紅字。
   - 截圖 ≤ 10 張，jpg 80。
4. `trpg content check` 通過；一場紀錄＋重播通過（內容不變，雜湊不變）。
5. 報告寫明：預算端點每次幾毫秒、整包驗證幾秒、地圖戰 24 場實測秒數、（2c）比值重算 1 招／一組的實測秒數；沒驗證的。

## 10. 工作環境

照 NW 計畫第 10 節（Windows、Git Bash、新 worktree 先 `uv sync --frozen` 與 `corepack pnpm -C client install --frozen-lockfile --offline`、之後 `UV_NO_SYNC=1`；預覽埠 vite 5310～5314、`trpg serve` 8157～8159；`TRPG_SAVE_DIR=<暫存>`、`TRPG_TUNING=1`；**絕不對主資料夾寫回或 commit**；`?mute=1`、`--mute-audio`；用自己記下的 PID 關程序；等待用完成通知、不寫 `until`／`while` 輪詢；不跑 `scripts/check.py`、不跑大型模擬；不 push；每個交付項目一個 commit，第一行英文、結尾帶 Co-Authored-By）。另外：
- 這台 Bash 的 `python` 是 Windows Store 空殼，一律 `uv run python`。
- shell 指令的字串裡不放反引號；含反引號的文字用檔案工具或 `<<'EOF'` heredoc 寫。
- agent 與子 agent 一律 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣。

## 11. 開發中跑的測試

- NW-2a：`UV_NO_SYNC=1 uv run pytest -q tests/api/tuning tests/content/test_tuning_fields.py tests/content/test_enemy_skill_count_149.py tests/skillgen/test_range_budget.py tests/sim/test_skill_probe.py tests/test_architecture.py tests/content/test_loader.py -n 8`；改到 `library_violations` 或預算輸出時加 `tests/cli/test_skills_cli.py`、`tests/cli/test_budget_cli.py`。
- NW-2b：`corepack pnpm -C client exec vitest run src/tuning/ src/screens/ src/test/importCycles.test.ts`；交件前 typecheck／test／build。
- NW-2c：`tests/sim/test_skill_ratio.py`、`tests/api/tuning`；腳本逐字相同的實跑一次（5.7）。
- 交件前一次：`tests/api/test_client_fixtures.py`、`tests/api/test_openapi_snapshot.py`、`tests/cli/test_output_snapshots.py -m slow`（本段不改內容，應全過、快照不動）。

## 12. 報告格式

各段寫 `docs/phases/PhaseNW-2a報告.md` 等，照 NW 計畫第 12 節：做了什麼（附 commit）、驗收逐條（結束碼分開記）、改寫的既有測試與搬家證據、實測數字、安全措施對照（含例外閘門與附帶改動哪條是假 repo 測、哪條是實機測）、請使用者試用的步驟（2b 起寫「給使用者的使用說明」一節，專案 PM 會原樣轉給使用者）、**待 PM 決定**（最多 10 點，附出處；原型數值與解讀類照最保守做完再列）。

## 附：起草時查到的風險與疑點

1. **調高傷害多半會超出預算**（第 1 節：122 招 1 階武器技有 20 招已 ≥ 95%）：例外流程會常用，`known_budget_exceptions` 可能從 1 筆變成幾十筆。這是 D3 的既有決定，只在確認視窗與報告提醒；若使用者覺得煩，另議「放寬合格區間」（屬規則，不在本段）。
2. **BAL-21e 的比值和預算比例是兩把尺**：比值是實戰木樁傷害 ÷ 普攻，預算是點數模型；同一招可能比值 0.6、預算 95%。畫面兩個並列並各自標來源，避免使用者以為改一個另一個會跟著到線。
3. **升階重算吃掉超出的部分**（R2）：大世界的敵人與 2 階以上的玩家用的是重配後的版本；只改 1 階數字對頭目實戰常常沒有影響（BAL-21c 的界隙閃擊）。表單要列「哪些單位實戰用升階版」，否則使用者會以為改了沒用。
4. **字面替換的覆蓋面**：技能檔比單位檔寫法多（區塊式效果、效果上方的註解、巢狀流式 mapping）；hypothesis 測試一定要跑全部 404 個技能檔。遇到擋下的寫法（錨點、加引號）要在報告列出是哪幾個檔、哪些欄位因此不能改。
5. **`test_coverage.py` 與 #149 測試**：招式組改動會打破這兩個規則型測試；收編不能自己放寬（5.8）。R1 沒答覆前，工坊照建議做「警告＋我確定」，但收編時要先回報。
6. **地圖戰的受測招可能根本不在場上**：玩家招多半只在 build 上；`map_spec` 的預設陣容是 `hero_*`。沒有 T9 的「裝到 build」，使用者會量到 0 次而誤判。
7. **比值腳本搬家**（2c）：826 行、自帶程序池與暫存檔路徑；搬家要照 NW-1a 搬 `boss_probe` 的做法（逐字相同的雜湊證據），程序池改由 `sim_jobs` 管。
