# Phase 4-L8 報告｜開放更多結構給 LLM 提議

> 規格：`docs/phases/Phase4計畫.md` 第 3H 節；PM 追加兩項（提議 schema 移除 `name_zh`、prompt 版本號寫進 run 紀錄）。實作者：opus。
> 全部測試用 `MockLLMClient`，沒有呼叫真模型（8001 埠沒碰）。開工時 HEAD 含 `fb81e020`；中途依 PM 指示 `git merge main`（4-L7），**沒有衝突**。

## 1. 往返盤點（先量）

新模組 `src/trpg/skillgen/proposal_coverage.py`：`round_trip_inventory(library)` 對全部手寫技能做「`proposal_from_skill` → 以原數值補回（`fixed_filler`）→ `evaluate_proposal`」，結果與原技能除 ID、來源、名稱（4-L8 起不是結構）外相同才算成功；武器技與縮放例外清單不比縮放屬性（沿用舊測試的規則）。手寫技能本身已知的規則問題（`cap.min_cost`、3-49 射程預算例外）算成功。失敗依序歸類：修正規則 → 形態／種族 → followup → reaction → 其他（常駐傳說的 `activation`）→ 代價欄位 → 只能巢狀 → 其他。

| 分類 | 開放前（301 招） | 開放後 | 技能 |
|---|---|---|---|
| **往返成功** | **241** | **264** | |
| 修正規則（modifiers，不開放） | 18 | 18 | attack_mastery、beam_of_mercy、burning_shove、ember_cycle、form_mastery、heavy_stomp、lingering_roar、rune_breaker、rune_etcher、rune_resonance、rune_sight、searing_scar、self_mending、summon_elite、summon_swarm、thunder_hand、timber_piercer、war_avatar |
| 形態／種族專屬（不開放） | 0 | 0 | （形態原語的手寫技能都是修正型或已能表達） |
| 複合技能 followup | 8 | **0** | armor_break_combo、charged_cleave、death_spiral、gravity_burst、leap_slam、parry_riposte、retreating_slash、shadow_whirl |
| 反應 reaction | 8 | **0** | ambush_stab、counterspell、covering_fire、grief_rage、parting_slash、reflex_ward、riposte、stand_firm |
| 代價欄位 | 7 | **0** | all_in（on_miss）、mirror_cast／rallying_cry／time_surge／undying_oath（source）、resurrection（uses_per_battle）、thunder_finisher（stacks） |
| 只能巢狀的效果 | 2 | 2 | ash_harvest（`on_kill` 的 refund_ap／refund_cooldown）、blood_sacrifice（賭注的 damage_multiplier／self_damage_of_hit） |
| 其他 | 17 | 17 | weapon_only 5、activation 4、trap 3、mastery 2、secondary_scaling_attr 1、pierce 1、crit_range＋damage_permille 1 |

（4-L3 時 163／217；技能增加到 301 招後開工實測 241／301。）

覆蓋率測試 `tests/skillgen/test_proposal_coverage.py`：`MIN_ROUND_TRIP = 264`（不得下降）、每個失敗都有分類、修正型一律在不開放分類。每個新開放結構至少 1 招手寫技能往返成功：`tests/skillgen/test_proposal_l8.py` 對上表 23 招逐一參數化，另確認六種 `followup.when` 都有手寫技能往返成功。

## 2. 開放的結構

### 2.1 代價類欄位（`proposal_costs.py`）
- 新的提議欄位（都可省略，只選「要不要」，數值由引擎決定）：`cost_once_per_battle: true` → `cost.uses_per_battle: 1`；`cost_hp: true` → `cost.hp_percent` ＝ `allowance.hp_cap ÷ hp_per_permille`（目前 200‰，剛好用滿 HP 代價的折抵上限）；`cost_on_miss`：失手反噬 1～2 個效果（`damage`／`apply_status` 的 `BacklashEffect` 模型，沒有 `affects`、`condition`），稀有度低於 `ON_MISS_MIN_RARITY` 時不出現在 schema。
- `cost.source`、`uses_per_battle`、`stacks`、`hp_percent` 改列為數值欄位（`proposal_numbers.COST_NUMBER_FIELDS`）：不在提議裡；`minimal_filler` 對傳說技能補 `source: 1`。
- `split_numbers`／補值器的走訪多了 `cost.on_miss` 與 `followup` 的效果、`followup.condition`；第二段的必填判斷只看第二段自己的效果。
- `cost_penalty`／`cost_overdraft`（3-50）不變，說明文字移到 `COST_DOCS` 共用。

### 2.2 反應（`reaction`）
- `PROPOSAL_KINDS` 加 `reaction`，`CLOSED_SKELETONS` 拿掉 `reaction`（剩 `modifier`、`trap`）。所選骨架有反應技時，頂層多 `reaction: {event}`（`SKILL_REACTION_EVENTS` 八種）；說明取 `reactions.yaml` 的 `events[].description_zh`（`reaction_events()`）。
- 子集：`ProposalRequest(kind="reaction")` 或骨架 `reaction` 可出題；`available.reactions` 列事件與說明。

### 2.3 複合技能（`followup`；`proposal_followup.py`）
- 有主動技能的版型、稀有度 ≥ `COMPOSITE_MIN_RARITY` 時多 `followup: {when?, skeleton, shape, effects, condition?, release?}`。
- 第二段效果：子集內不在 `FOLLOWUP_FORBIDDEN` 的原語，加上 `COMPOSITE_MOVES`（即使不在子集；「動作 → 位移」「擊殺 → 接下一段」用）；一般原語與一般版型相同時共用 `GeneralEffect`，否則另建 `FollowupEffect`。形狀：動作段、擊殺後第二段、延遲段的形狀與位移原語的形狀。
- 子集新增 `followup_skeletons`（此稀有度可用的全部主動骨架，不受題目骨架限制）、`followup_shapes`、`followup_moves`；`build_proposal_models` 新參數 `followup`、`followup_skeletons`、`followup_shapes`、`followup_moves`；第二段骨架另建 `FollowupSkeleton`（不同時）。
- `when`／`release` 說明：`FOLLOWUP_WHEN_HINTS`、`RELEASE_HINTS`（時機本身是引擎的 `Literal`，說明跟著放在程式，見待決 3）。`available.followup` 列時機、釋放、骨架、形狀、子集外的位移。
- **預算器調第二段**：`composer_tuning.tune(..., extra=...)`（關鍵字參數，組合器不傳、行為不變）讓旋鈕索引延伸到第二段的效果；`proposal_budget._knobs` 依第二段自己的骨架判斷核心。驗證器對第二段的代碼帶 `followup.` 前綴，`segment_code()` 去掉前綴後同樣可修（預算、占比、補冷卻的互斥規則）。

### 2.4 子集與 prompt
- `available` 依種類多列：主動技能 `costs`（含 `cost_penalty` 的可選狀態）與（稀有以上）`followup`；反應技能 `reactions`。
- `PROMPT_VERSION` `skill-proposal/3` → **`/4`**（系統指令多兩行：`costs`／`followup`／`reactions` 的用途、名稱不用填），`tests/llm/test_prompts.py` 新增快照。4-L7 的命名 prompt `skill-naming/1` 沒有動。
- 大小（全部 49 個可行題目：稀有度 × 骨架含不指定）：schema 最大 **91,020** 字元（傳說、不指定骨架；上限 `SCHEMA_CHAR_LIMIT` 125,000，沒改），訊息 token 最大 **8,069**（上限 30k）。完整 schema（不篩）99,071 字元。主動、稀有以上的 `available` 固定多約 1,100～1,200 token。

## 3. PM 追加

1. **提議 schema 移除 `name_zh`**：頂層不再有名稱欄位（填了得到 `extra_forbidden`）；`proposal_from_skill` 不輸出名稱。轉成技能時先用組合式名稱 `combined_skill_name()`（「元素・骨架」，從 `trpg.llm.naming.fallback_naming` 抽到 `skillgen.proposal`，兩邊共用同一個實作），技能 ID 由含此名稱的內容雜湊；命名步驟（4-L7）開啟時再 `apply_naming` 換掉（ID 不變，同 4-L7）。變奏的 `name_zh`、`concept`／`cast_flavor` 保留。
2. **prompt 版本號寫進 run 紀錄**：`LlmAttempt`／`LlmTrace`／`LlmRecord` 新增 `prompt_version`（有請 LLM 時為 `PROMPT_VERSION`）與 `naming_prompt_version`（有命名步驟時為 `NAMING_PROMPT_VERSION`），由 `trpg.llm.candidate_source` 填入（`skillgen`／`roguelite` 不匯入 `llm`）。存檔 **`trpg-run/9` → `/10`**（`/5～/9` 可讀；只新增有預設值的欄位）。測試裡 `trpg-run/9` 字串改 `/10`。

## 4. 驗收

| 項目 | 結果 |
|---|---|
| pytest `tests/skillgen tests/llm tests/content tests/roguelite tests/api tests/narrative tests/test_architecture.py tests/test_primitive_coverage.py` | 4574 passed、1 skipped |
| `-m "slow or not slow" tests/cli --timeout=3000` | 154 passed（含重產的 llm propose 快照） |
| `ruff check`、`ruff format --check`、`mypy`（787 檔）、`lint-imports`（7 kept） | 全過 |
| `trpg llm propose --mock -n 10 --seed 0` | 正常：8 題 llm 通過、退回 2（pool 1、workshop 1）；第 9 題出現新開放的反應技（`epic／reaction`） |
| `trpg run auto --seed 5 --llm-mock` | 跑完；7 題全部退回（與 4-L6 驗收相同的 Mock 限制） |

**CLI 快照重產**：`tests/cli/snapshots/llm_propose_mock.txt` 只有三行的技能名稱改變（「聚雷」→「雷電・打擊」等）——提議不再帶名稱，`trpg llm propose` 沒有命名步驟，所以顯示組合式名稱。題目、來源、嘗試次數、統計不變。戰鬥快照沒有改變。

**Mock 走子集的實測**（`evaluate_with_repair`，題目 ＝ 原技能的階級／稀有度／骨架，種子 0～9）：代價 3 招、反應 8 招、複合 shadow_whirl／retreating_slash／charged_cleave／parry_riposte 全部 10／10；armor_break_combo 9／10、death_spiral 8／10（占比修補後仍不足）；gravity_burst 0／10（見待決 5）、leap_slam 0／10（見待決 6）。

## 5. 複雜度 noqa

沒有新增複雜度類 noqa（C901／PLR0911／0912／0915）。`minimal_filler` 超過 C901 時拆成 `_fill_conditions`、`_fill_cost`；盤點分類改成條件表。新的 `Union[...]  # noqa: UP007` 一行沿用檔案既有寫法（非複雜度）。

## 6. 待 PM 決定

1. **只能巢狀的效果沒有開放（建議拆 4-L8b）**：只影響 2 招（ash_harvest、blood_sacrifice）。`refund_ap`、`refund_cooldown`、`damage_multiplier`、`self_damage_of_hit` 不是 `skill_primitives.yaml` 的原語，參數全部是數值；開放要決定定義放哪裡（a. `skill_primitives.yaml` 加「只能巢狀」區段——會進規則包與 `ruleset_hash`，coverage／組合器／工坊都要排除；b. 另開小 YAML；c. 程式表＋`llm_hint`），以及補值器怎麼補（倍率 ≠1000、自傷必填）。
2. **HP 代價取多少**：`cost_hp: true` 固定取用滿折抵上限的量（200‰ ＝ 最大 HP 的 20%，折抵 20%），內建技能沒有 HP 代價可參考，未跑模擬。
3. **說明文字放哪裡**：反應事件說明沿用 `reactions.yaml` 的 `description_zh`（給玩家的短句，沒加 `llm_hint` 欄位以免改規則包）；`followup.when`／`release` 說明寫在 `proposal_followup.py`（時機是引擎 `Literal`）。要改成 YAML 請指示。
4. **第二段的骨架範圍**：子集對第二段開放「此稀有度可用的全部主動骨架」與全部第二段形狀、`COMPOSITE_MOVES`（不受題目骨架限制），讓模型能做「位移 → 範圍」等組合；schema 因此較大（仍在上限內）。若要省 schema 可只開 area／strike／displace。
5. **gravity_burst 在子集內做不出來**：聚集段用 `ring`，但 `displace` 骨架的 `shapes` 沒有 `ring`（驗證器允許、子集依骨架形狀篩），是 4-L4 子集的既有限制；完整模型往返沒問題。
6. **AP／冷卻／耐力不是旋鈕（4-L3 待決 #2，仍未開放）**：補值器只補最低花費，複合技能（如 leap_slam：躍擊＋十字震地）以最低花費計算時一開始就超出預算、旋鈕往下調不動，`budget.over` 修不好。需要決定花費／冷卻是否成為旋鈕（或「超出時往上補花費」）。
7. **傳說技能的源力**：補值器固定補 1 點；改寫規則型傳說還需要「每場一次或冷卻 ≥ 2」，`cap.rule_rewrite_cost` 目前不在可修清單（`TOPIC_RARITIES` 仍不出傳說題，不影響候選）。
8. **命名關閉時的敘事**：名稱改用組合式名稱，但 `concept`／`cast_flavor` 仍是提議裡的（4-L7 的退回會連敘事一起換成模板）；要不要命名關閉時也用模板敘事？
9. **`trpg llm propose` 沒有命名步驟**：輸出的技能名都是組合式名稱。要不要在 CLI 加 `--naming`（Mock 用 `mock_naming_client`）？
10. **反應技進了 `trpg llm propose` 的輪替骨架**：`_open_skeletons` 依 `CLOSED_SKELETONS` 與 `PROPOSAL_KINDS`，所以 `-n 10` 的題目會出反應技；候選產生器的題目（`make_topic`）預設是主動技能，不會出反應題。是否要讓候選產生器出反應題，請 PM 決定。

## 7. Commit

- `d62594d6` feat(skillgen): proposal round-trip inventory and coverage floor
- `ad0cbb36` feat(skillgen): open cost fields to LLM proposals
- `45818842` feat(skillgen): open reaction and followup structures to LLM proposals
- `76b3c106` Merge main (4-L7) into 4-L8（無衝突）
- `ddeec392` feat(llm): drop name_zh from proposals, record prompt versions in runs
- （本報告）docs: Phase 4-L8 report
