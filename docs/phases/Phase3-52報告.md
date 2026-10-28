# Phase 3-52 報告｜層數擴充（玩法決定 #57，06 6.32）

實作者：agent（sonnet 5.5）。範圍：`docs/phases/Phase3計畫.md` 第 62 節。

## 1. 規則對照表（06 6.32 → 實作）

| 層數（ID） | 在誰身上 | 上限 | 累積（資料：`content/stacks.yaml` 的 `gain`） | 消耗（`consumer`） |
|---|---|---|---|---|
| 連擊點（`combo_point`） | 自己 | 5 | `weapon_skill_hit`：武器技（`category: weapon`）命中，每個被命中的單位 +1 | 加成傷害；限帶 `finisher`（終結）標籤的技能；示範每層 +20% |
| 專注（`focus`） | 自己 | 3 | `turn_end_still`：自己的回合結束且這回合 `moved_this_turn` 為假 +1 | 加成傷害；不限技能；示範每層 +15% |
| 聖能（`holy_power`） | 自己 | 3 | `heal_or_holy_cast`：施放帶 `heal` 效果、`holy` 標籤或神聖傷害的技能 +1 | 加成**治療與護盾**；示範每層 +20% |
| 靈魂碎片（`soul_shard`） | 自己 | 5 | `kill`：擊倒敵人 +1；`summon_downed`：自己的召喚物被打倒 +1 | 加成傷害；限召喚、詛咒（新標籤 `curse`）標籤或暗影傷害；示範每層 +20% |
| 寒霜（`hoarfrost`） | **敵人**（`expires_after_rounds: 3`） | 3 | `element_hit`（冰霜）：自己的冰霜攻擊傷害命中，疊在被命中者身上 +1 | 加成傷害；限冰霜傷害；示範每層 +25% |
| 氣（`ki`） | 自己 | 3 | `basic_attack_hit`：普攻命中 +1 | 加成**傷害與治療**；示範每層治療 +15% |
| 怒氣（`fury`，既有） | 自己 | 4 | `damaged`：受到傷害 +1（裝備已有同一種充能詞條的單位不重複算） | 技能可消耗（加成傷害）；示範每層 +20% |

引擎實作：
- 資料：`StackDef` 多了 `gain`（`GainSpec`：`when`、`amount`、`element`）、`consumer`（`ConsumerSpec`：`boosts`、`requires_any`）、`composer`。**YAML 欄位叫 `when` 不叫 `on`**（YAML 1.1 會把 `on` 解成布林）。
- 自動累積：新模組 `trpg.engine.stack_gain`。與被動、裝備觸發相同：事件發生時收集（`Fired`，`event` 為 `stack_gain:<時機>`），**等整招／整次攻擊結算完才累積**，所以終結技消耗層數時不會把自己這一擊的那一層算進去（消耗在先、累積在後；測試 `test_the_finisher_spends_the_points_before_its_own_hit_adds_one`）。
- **只有身上帶著消耗這種層數的技能的單位才會自動累積**（`stack_gain.consumes`）；沒有人用得到的層數不出現，舊戰鬥不受影響。
- 消耗擴充：`Cast.consume_stacks` 依 `consumer.boosts` 把加成分到傷害（`caster_bonus`）、治療（`heal_bonus` → `heal_multiplier`）、護盾（`shield_bonus` → 新 `shield_multiplier`）。疊在敵人身上的層數只能加成傷害（schema 檢查）。
- 驗證器：`consume_stack` 的技能必須有被加成的效果種類，且滿足 `requires_any` 其中一項（`_consumer_problems`，訊息繁體中文）。
- 預算：`consume_stack` 加成點數改為「被加成的效果（傷害／治療／護盾）的點數 × 期望層數 × 每層加成」。
- 隨機組合器不抽新層數（`composer: false`；怒氣照舊可抽，行為不變），所以組合器的亂數串流與既有種子不變。
- 工坊：層數選單 `stack_choices`（`info.owner`／`info.group_zh`，自己的在前）；前端 `groupChoices`＋`<optgroup>` 依「累積在你身上」「疊在敵人身上」分組；`effect_fixes` 的 `_stack_fix` 讓累積／消耗層數的對象由層數決定（前端既有的 `conformAffects` 自動套用，不能選錯）。LLM 提議：`_stack_target` 在轉成技能時以層數的 owner 覆蓋 `affects`，LLM 只挑層數。
- 說明：`stack_rules`（名詞對照表）新增「怎麼累積」「怎麼消耗」兩行；技能卡的消耗句改為「每層使本技能{傷害／治療、護盾…} +X%」；`workshop_text.yaml` 的 `consume_stack`／`add_stack` 玩家說明補了治療護盾與對象自動決定（原文 `skill_primitives.yaml` 同步）。
- `LOG_FORMAT`：`/72` → `/73`（規則包內嵌的層數表與技能表改變）。

## 2. 示範技能與預算（皆 T1，比例 70～100%）

| 層數 | 累積 | 比例 | 消耗 | 比例 |
|---|---|---|---|---|
| 連擊點 | 連環快刺 `skill_flurry_jab` | 97.1% | 連擊終結 `skill_combo_finisher` | 86.7% |
| 專注 | 穩穩瞄準 `skill_steady_aim` | 97.1% | 專注一擊 `skill_focused_shot` | 81.7% |
| 聖能 | 聖光撫慰 `skill_radiant_mend` | 90.6% | 聖能壁壘 `skill_sanctified_ward` | 81.9% |
| 靈魂碎片 | 收割靈魂 `skill_soul_reap` | 88.3% | 魂潮奔流 `skill_soul_torrent` | 85.1% |
| 寒霜 | 霜寒之觸 `skill_rime_touch` | 86.9% | 碎霜爆裂 `skill_shatter_frost` | 77.9% |
| 氣 | 震掌 `skill_palm_strike` | 97.1% | 運氣調息 `skill_qi_breath` | 77.9% |
| 怒氣 | 怒火中燒 `skill_seething_rage`（被動，受傷時護盾＋怒氣） | 80.4% | 怒氣爆發 `skill_rage_unleashed` | 80.9% |

共 14 招，技能總數 254 → 268。全部組得出來，沒有超預算或過弱。聖能與氣的消耗技用 `aura` 骨架（核心是治療／護盾，附帶 `consume_stack`）；其餘用 `builder_finisher`。
`skill_soul_burst` 原本就存在（3-24c 的池內技能），示範技能改名 `skill_soul_torrent`（魂潮奔流）避免覆蓋。新增技能標籤 `curse`（詛咒）。

## 3. 測試

- `tests/engine/test_stack_expansion.py`（22）：資料表檢查、每種層數的自動累積（命中／未命中／沒有消耗技能不累積／上限）、終結技先消耗後累積、專注（站定／移動）、聖能與氣的治療與護盾加成、擊殺碎片、寒霜疊在敵人身上並消耗、怒氣受傷累積與技能消耗、同一串動作重播事件與結果完全相同。
- `tests/skillgen/test_stack_expansion_52.py`（14）：卡片消耗句、名詞對照表說明（無英文）、示範技能成對、驗證器的消耗規則（終結標籤、治療／護盾、冰霜傷害、對象必須對應層數 owner）、工坊分組與對象自動決定（`effect_fixes`）。
- `client/src/workshop/stackGroups52.test.ts`：`groupChoices` 與對象自動修正。
- 更新：`test_coverage.py`（示範技能進 `_POOL_ONLY`、怒氣離開未覆蓋清單）、技能總數 268（`test_budget_cli.py`、`test_skill_scaling.py`）、`LOG_FORMAT` 斷言 `/73`、`skill_icons.json`（`uv run python -m tests.narrative.icon_fixture`）、CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`）。
- OpenAPI：`FieldSpec`／`Choice` 型別沒有變（`info` 是任意字典），`export_openapi.py` ＋ `gen:api` 後無差異。

驗收結果見提交訊息與最後回報（ruff、format、mypy、lint-imports、pytest 各目錄、vitest、build）。

## 4. 待 PM 決定

1. **「怎麼累積」的解讀**：06 6.32 表的「怎麼累積」我做成**自動累積規則**（資料驅動），而且**只有身上帶著消耗該層數技能的單位才會累積**（避免所有人的畫面都出現沒人用的層數，也不動既有戰鬥）。示範的「累積技能」是在自動累積之外**再加**一層（`add_stack`），所以例如連環快刺命中一次會得 2 點連擊點。若玩法 PM 的本意是「只有累積技能才能累積、沒有自動累積」，需要拿掉 `gain`（資料改動，引擎保留）。
2. **專注的「下一招」**：做成一般的消耗技（消耗全部專注，加成**那一招**），不是「施放任何下一招都自動吃掉」。若要後者需要新機制（任何技能施放時自動消耗）。
3. **靈魂碎片的「詛咒」**：原本沒有詛咒標籤，新增 `curse`（詛咒）標籤；消耗限制為「帶召喚／詛咒標籤，或有暗影傷害」。哪些技能算詛咒由玩法 PM 日後標示。
4. **氣的「普攻命中」**：普攻命中即累積（不分徒手或持武器）；「治療自己」目前只限制「技能要有治療效果」，沒有限定對象為自己（對象由技能決定）。
5. **層數沒有關鍵字**：只有 `static_charge`／`overload_surge` 掛在「帶電」關鍵字下。新層數的示範技能依各自的元素／標籤推導（例如冰霜技能進冰凍池），其餘（連擊點、專注、氣、怒氣）目前是「基礎技能」。是否要為新層數建立關鍵字，交玩法 PM。
6. **工坊事前停用**：對象已由層數自動決定（`effect_fixes`＋前端自動套用）；但「這個層數不能給這種技能消耗」（例如連擊點要終結標籤、聖能要有治療／護盾）目前仍是驗證器事後報錯，沒有在層數選單上事前停用。
7. **聖能的累積觸發比 add_stack 多一倍**：治療技能本身自動 +1 之外示範技能再 +1。數值為初值，交平衡階段。
8. 示範技能沒有裝進任何 build（照 3-50 的做法放進 `_POOL_ONLY`，由池給出）。
