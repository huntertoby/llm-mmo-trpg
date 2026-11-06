# Phase 3-33f2 報告｜召喚技能分歧進化＋召喚專用詞條

> 規格：`docs/phases/Phase3計畫.md` 36.8「3-33f2」；設計：`docs/design/06-技能.md` 6.28、6.29.4、6.29.6，`docs/design/08-裝備.md` 8.21.5.3、8.24。
> 分支：`worktree-agent-a94c5f13bbe63a59a`（從 main 的 `ea58de6` 分出），未 push。數值都是初值（放 `content/`），未經模擬。
> 本段沒有動召喚物範本的 HP 成長與定位、召喚專精被動（3-33f1 的範圍）。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `641d689` | 召喚效果變體（數量型、HP、小特性、第二灌注）與 6 條召喚詞條的引擎／內容：`summon_traits`、新觸發 `on_summon_downed`、`gear_summon.py`／`summon_variants.py`、測試物品、`LOG_FORMAT /55`、CLI 快照 |
| `e58e416` | 三支分歧進化：`summon_evolution.py`、`evolution.py` 分流、召喚技預算新增三項、API／CLI／OpenAPI 的 `count` 分支 |
| `8c35397` | 測試：燧發槍＋獻祭重播測試跟著 `/55` |
| `b937820` | 前端：`on_summon_downed` 的觸發圖示與名稱、技能圖示 fixture 重產 |
| （本報告） | `docs/phases/Phase3-33f2報告.md` |

## 2. 三支分歧進化

召喚技能（有 `summon` 效果）原本沒有任何可調旋鈕（3-26b 報告「零支」的多半是這類），所以不走一般進化模板，而是由 `trpg.skillgen.summon_evolution` 直接改 `summon` 效果；`evolution_options` 對召喚技能自動改走這條路（`EvolutionRequest`／`Evolution` 介面不變，`Evolution.branch` 多了 `count`）。參數在 `content/skill_evolution.yaml` 的 `summon` 區塊；小特性表在 `content/rules/core.yaml` 的 `summon_traits`。

| 支 | 規則 | 技能卡文字 | 名稱前綴／ID |
|---|---|---|---|
| 加深 `deepen` | `summon.max_hp_permille: 300`（召喚物最大 HP +30%）＋ `summon.trait`（小特性，依召喚物定位挑：不動／不攻擊→堅韌「護甲 +1」、近戰→迅捷「移動 +1」、遠程→銳利「暴擊範圍擴大 1」） | 加深：單隻更強（最大 HP +30%），並多一個小特性「…」 | 「強化・」／`<id>_evo_summon_deepen` |
| 橋接 `bridge` | `summon.infusion: <關鍵字>`：召喚物多帶第二個灌注（`UnitState.bonus_infusion`，與範本固有的、施放時選的並存，相同只算一次）。關鍵字依「前後搭配 → 目標身上 → 其他技能持有 → 召喚物定位偏好（`roles`）→ 推導表順序」排序，最多試 3 個；進化後（專屬規則）必須真的帶那個關鍵字（`skill_keywords.yaml` 新增 9 條 `{effect: summon, infusion: <k>}` 規則）。不攻擊的召喚物（圖騰、土牆）沒有這一支 | 橋接〈關鍵字〉：召喚物多帶一個〈關鍵字〉灌注 | 關鍵字前綴（灼燃、潮濕…）／`<id>_evo_summon_bridge_<k>` |
| 數量型 `count` | `summon.count: 2` ＋ `summon.power_permille: 600`：一次召喚 2 隻，每隻最大 HP 與傷害都是 60%（傷害乘在 `modifiers.damage_permille` 最後，`UnitState.summon_power_permille`）。第二隻放在第一隻旁邊第一個合法空格（東、西、南、北）；四周都擋住時第二隻落空（`effect_fizzled: summon_blocked`）。圖騰（光環）沒有這一支 | 數量型：一次召喚 2 隻較弱的（各 60% 的最大 HP 與傷害） | 「雙生・」／`<id>_evo_summon_count` |

**同階預算**（`skill_budget`）：召喚技的點數公式多了三項（`_summon_variant_points`）——第二灌注＝同固有灌注的特性點數；加深＝每輪價值 ×（1＋HP 加成×`summon_hp_weight_permille` 300‰）＋小特性一次性點數；數量型＝整體 ×（隻數×強度）。進化後的點數必須落在同階 0.70–1.00 區間；超出時依序試「縮短持續輪數（最短 1）」×「冷卻 +1、+2（沿用一般進化的 `cost_attempts`，上限 5）」，第一個合格的就是結果，都不合格這一支省略。稀有度不變（6.12）。

**實例（召喚火靈：2 輪、冷卻 4、預算比 0.75）**

| 支 | 產物 | 預算比 |
|---|---|---|
| 加深 | 強化・召喚火靈：火靈最大 HP 14 → 18（+30%），小特性「銳利」（自然 19 起暴擊） | 0.91 |
| 橋接 | 潮濕・召喚火靈：火靈固有「點燃」＋第二灌注「潮濕」（命中時在目標格造水） | 0.77 |
| 數量型 | 雙生・召喚火靈：同時召喚 2 隻火靈，各 8 HP、傷害 ×0.6 | 0.90 |

**覆蓋率（17 種召喚技、無用法統計）**：三支齊全 9 種（火靈、石像、守護靈、鷹隼、影魅、元素之靈、藤蔓、戰狼、水精）；兩支 5 種（土牆、冰靈、高台圖騰、吸引圖騰：加深＋數量型／冰靈：加深＋橋接）；只有一支 3 種（喚起骷髏、爆裂傀儡、雷靈：只有橋接——它們的預算比本來就 0.94–0.99，加深與數量型加不進去；立起圖騰：只有加深）。

## 3. 召喚專用詞條（6 條）

沿用既有的 11 類詞條，不新增類別：技能強化類（`keyword: summon`）3 條、觸發類 2 條（新觸發）、普攻附加類 1 條。「召喚物數值（HP +%、攻擊 +1 骰）」**已有**（3-24b1 的修正規則 `summon_hp_permille`／`summon_attack_dice`，#35，各有測試），不是裝備詞條，本段確認、不重做。

| 詞條 | id | 類 | 部位 | 數值 | 規則 |
|---|---|---|---|---|---|
| 召喚技能冷卻 −1 | `affix_summon_cooldown` | 技能強化 | 副手、項鍊 | −1（固定） | 製造召喚物的技能施放時冷卻 −1，最低 1（`gear_summon_cooldown`，接在 `pay_skill_cost`）；兩條遞減 −1／−1.5，捨去後仍 −1 |
| 召喚物持續 +1 輪 | `affix_summon_duration` | 技能強化 | 副手（限法器珠 `orb`）、項鍊 | +1（固定） | 召喚物多存在 1 輪（`gear_summon_duration`，加在 `summon_max_duration` 上限之後）；遞減後同樣最多 +1 |
| 獻祭傷害與治療 +20% | `affix_summon_sacrifice` | 技能強化 | 戒指、項鍊 | +200‰ | `sacrifice_summon` 的爆炸傷害與治療 ×（1＋加成）；傷害加成計入全身 +50% 上限（`cap_damage_bonus`）；遞減 200／100／50／0 |
| 召喚物倒下時：原地爆炸 | `affix_trig_summon_blast` | 觸發 | 戒指、項鍊 | 1d8 火焰、半徑 1 | 新觸發 `on_summon_downed`；以倒下的召喚物為中心，對 1 格內敵人造成 1d8＋法術縮放的火焰傷害；每回合 1 次；同 id 只生效 1 條 |
| 召喚物倒下時：湧出治療 | `affix_trig_summon_mend` | 觸發 | 戒指、項鍊 | 1d8、半徑 1 | 同上，治療 1 格內的友方（含召喚者）；每回合 1 次 |
| 召喚物繼承你 1 條普攻附加詞條 | `affix_summon_inherit_attack` | 普攻附加 | 主手、副手 | — | 召喚物的裝備狀態放施放者 1 條可繼承的普攻附加（普攻元素、命中附帶狀態、連擊、分裂；符文不繼承），依詞條 ID 取第一條；多條繼承詞條只算 1 條 |

- **新觸發「召喚物倒下時」**（`on_summon_downed`，`skill_triggers.yaml`，戰鬥紀錄文字「召喚物倒下時」）：召喚物被打倒（`unit_downed`）才觸發；時效到期、被獻祭、召喚者倒下而消失都不算。`random_composer: false`，只給裝備詞條用。效果用既有的 `sacrifice_summon` 效果宣告（有 `element` 是爆炸、沒有是治療），`_GearCast.build` 改成以倒下的那一格為中心結算、不獻祭任何召喚物。
- **硬上限與遞減**（8.21.5.3）：數值型（冷卻、持續、獻祭）同 id 依 100／50／25／0% 遞減再套上限；非數值型（觸發、繼承）同 id 只生效最強的 1 條；獻祭的傷害加成計入全身 +50%；冷卻最低 1。
- 測試物品（模擬／測試用，不是掉落表）：`item_sim_summon_orb`（喚靈法珠：冷卻＋持續）、`item_sim_summon_pendant`（獻靈項鍊：獻祭＋爆炸）、`item_sim_summon_ring`（安魂戒：治療＋獻祭）、`item_sim_summon_blade`（傳承長劍：標記＋繼承）。

## 4. 改動摘要

- **schema／內容**：`EffectSpec` 的 `summon` 多了 `power_permille`／`max_hp_permille`／`trait`／`infusion`，`count` 可為 2（必須同時填 `power_permille`）；`skill_primitives.yaml`、`option_params`（LLM 選單文字與選項）、`skill_keywords`（`infusion` 參數）、`skill_triggers`（`on_summon_downed`）；`KeywordAffix.change` 多了 `cooldown_delta`／`duration_delta`／`sacrifice_permille`，`AttackAffix.summon_inherit`，`TriggerAffix` 檢查 `on_summon_downed`；`CoreRules.summon_traits`；`EvolutionTable.summon`；`BudgetRules.summon_hp_weight_permille`。
- **引擎**：`engine/summon_variants.py`（HP、強度、小特性、第二隻位置）、`engine/gear_summon.py`（冷卻、持續、獻祭、繼承）、`summons.summon_unit`（新參數 `spec`）、`modifiers.damage_permille`（乘 `summon_power_permille`）、`infusion.active_keywords`（含 `bonus_infusion`）、`skill_triggers.observe`（`unit_downed` → `on_summon_downed`）、`gear_triggers`、`interpreter`（數量型、獻祭加成、`_GearCast`）。
- **進化**：`skillgen/summon_evolution.py`、`evolution.py`（召喚技能分流、`Branch` 多 `count`、`cost_attempts` 改公開）、`budget._summon_variant_points`；`roguelite.EvolutionRecord.branch`、API `branch`／標籤「數量」、CLI 文字、OpenAPI 與 `schema.d.ts` 重產；技能卡文字（`narrative/skills.py`）會寫出數量、HP、小特性與第二灌注。
- **格式**：`LOG_FORMAT` `/54 → /55`（單位狀態多 `bonus_infusion`／`summon_power_permille`，PM 合併時定號）；CLI 快照、技能圖示 fixture 已重產。

## 5. 驗收

| 驗收項 | 結果 | 證據 |
|---|---|---|
| 三支進化產物合法 | 通過 | `tests/skillgen/test_summon_evolution.py`：17 種召喚技 × 2 種用法，每支都 `validate_skill` 零違規、預算比 0.70–1.00、稀有度不變、同一種召喚物、持續輪數只會縮短；各支內容（加深 HP＋定位小特性、橋接真的帶新關鍵字、數量型 2 隻 60%）、圖騰與土牆省略不合理的支 |
| 召喚當下的結算 | 通過 | `tests/engine/test_summon_f2.py`：HP +30% 與三種小特性、第二灌注命中時生效（造水＋燃燒並存）、2 隻各 60% HP 與傷害、第二隻無空位落空、`count`／`power_permille` 必須一起填 |
| 新觸發「召喚物倒下時」 | 通過 | 爆炸傷害 1 格內敵人、治療貼著的友方、每回合 1 次、到期／被獻祭不觸發、別人的單位不觸發、戰鬥紀錄中文文字 |
| 6 條詞條各自生效與上限 | 通過 | 冷卻 −1 與最低 1、遞減；持續 +1、遞減、加在上限之後；獻祭傷害與治療 ×1.2、遞減 300‰、硬上限 +50%；繼承 1 條（符文與繼承詞條本身不傳）；內容測試 `tests/content/test_summon_affixes.py`（schema 規則、部位、物品合法） |
| 確定性與重播 | 通過 | `test_a_battle_with_evolved_summon_skills_and_summon_gear_replays_identically`：三支進化＋全部召喚詞條的整場戰鬥，初始狀態＋動作列表重播逐位元一致；狀態 JSON 來回含新欄位 |
| `check.py`／`pnpm build` | 見第 7 節 | |

## 6. 新增的複雜度 noqa

無新增 `C901`／`PLR*` 的 `noqa`（`PLR0917` 以把兩個參數收進 tuple 解決）。`evolution.py` 內一處 `PLC0415`（召喚技能分流的函式內匯入，避免 `evolution` ↔ `summon_evolution` 循環匯入）。

## 7. 全量檢查

- `uv run python scripts/check.py`：ruff、format、mypy（548 檔）、lint-imports、pytest、client install／typecheck／vitest（72 檔 753 個）全過；`corepack pnpm -C client build` 成功（只有 chunk 大於 500 kB 的既有警告）。
- 抓到並修掉的：`tests/api/test_gear_api.py` 的詞條總數（40 → 46）、`tests/engine/test_24c.py` 的 `/54`、技能圖示 fixture 與 vitest 的觸發圖示清單（新觸發 `on_summon_downed` 要有圖示）。
- 與 3-33f1 同時開發：沒有動召喚物範本的 HP 成長與定位、召喚專精被動；合併時預期會衝突的是 `summons.summon_unit`（`spec` 參數、`duration` 那一行）、`core.yaml`、`runner.py` 的 `LOG_FORMAT` 文件字串。

## 8. 待 PM 決定

1. **「召喚物數值」詞條不是裝備詞條**：規格寫「已有，確認」，已有的是修正規則 `summon_hp_permille`／`summon_attack_dice`（技能的修正，3-24b1），裝備白名單裡沒有對應詞條。本段只確認它們存在、沒有新增裝備版；要不要補「召喚物最大 HP +N%」「召喚物攻擊 +1 骰」的裝備詞條請決定。
2. **沒有三支齊全的召喚技能**：17 種中 9 種三支齊全；喚起骷髏、爆裂傀儡、雷靈的預算比本來就 0.94–0.99，加深與數量型加不進去（縮短到 1 輪又太弱），只有橋接；立起圖騰只有加深。是否放寬（例如允許冷卻 +3、或下調 `summon_hp_weight_permille`／小特性點數）請決定。
3. **持續 +1 輪詞條加在 `summon_max_duration`（4）之後**：4 輪的召喚技搭配詞條可以到 5 輪。3-33f1 的專精（群召 +1、精英 +2 輪）怎麼和這個詞條合計、有沒有總上限，請與 f1 對齊（兩邊合併時看 `summons.summon_unit` 的 `duration` 那一行）。
4. **獻祭加成只和自己遞減／上限比**：獻祭的傷害本來就不吃其他傷害修正，所以「計入 +50%」的做法是詞條自己的遞減加總後套 `cap_damage_bonus`（+50%），沒有和施放者身上的其他傷害加成合計。
5. **繼承普攻附加的取捨**：施放者有多條普攻附加時，召喚物只取詞條 ID 排序第一條可繼承的（符文類不繼承）；沒有讓玩家選。繼承詞條與被繼承的詞條要裝在同一個人身上（主手的普攻附加＋副手的繼承詞條）。
6. **數量型與同時上限**：2 隻各自占一個召喚名額（上限 2 時兩隻會把舊的都擠掉）；搭配 3-33f1 的精英召喚（上限 1）時，第二隻會讓第一隻消失，實質只剩 1 隻。效用 AI 的召喚估值（`ai/summon.py`）沒有依 `power_permille` 折算，會高估數量型。
7. **召喚物倒下的爆炸／治療數值**：1d8（火焰／治療）、半徑 1、每回合 1 次是初值，未計入詞條預算、未模擬；「每回合 1 次」沿用 `limit: per_turn`（在持有者自己的回合開始時清除）。
8. **`LOG_FORMAT` `/55`、橋接候選**：與 3-33f1 若同時遞增請 PM 合併時定號；橋接沒有把「召喚物」（HP +20%）灌注放進候選（沒有一般意義的新關鍵字），沒有用法統計時依召喚物定位的 `roles` 偏好挑。
