# Phase 4-L8b 報告｜4-L8 待決收尾

> 規格：`docs/phases/Phase4計畫.md` 第 3I 節。實作者：sonnet。
> 全部測試用 `MockLLMClient`，沒有呼叫真模型（8001 埠沒碰）。開工時 HEAD 含 `ada247f5`，無需合併。

## 1. 只能巢狀的效果（規格 1）

- **資料**：`content/skill_primitives.yaml` 在 `primitives:` 之前新增頂層 `nested_only_effects:`（schema：`trpg.content.skills.primitives.NestedOnlyDef`、`PrimitiveTable.nested_only_effects`）。每筆有 `id`、`name_zh`、`description_zh`、`llm_hint`、旗標 `nested_only: true`、允許的父結構 `parents`（`on_kill`／`win`／`lose`）與 `params`（數值參數由補值器補，同原語的 `int`／`dice`，一律 `knob: none`）。載入時檢查：ID 不重複、不與原語同名。
  - `refund_ap`（`on_kill`；`amount` 1–2）、`refund_cooldown`（`on_kill`；無參數）、`damage_multiplier`（`win`／`lose`；`damage_multiplier_permille` 1500–3000）、`self_damage_of_hit`（`win`／`lose`；`self_damage_permille_of_hit` 100–1000）。
  - 它們**不是原語**：沒有預算基礎點數、不進原語表／組合器／工坊／`primitive_coverage`；預算與組合規則仍由原本的專用程式處理。
- **提議 schema**：`proposal._Builder._nested_type` 在原語之外，依 YAML 的 `parents` 把這四種加進對應巢狀參數（`on_kill`、`win`、`lose`）的 union；放錯父結構（例如 `damage_multiplier` 放 `on_kill`）會在提議階段被擋。`NESTED_EFFECT_TYPES`（引擎常數）仍保留，`tests/skillgen/test_proposal_l8b_nested.py` 檢查 YAML 的 `parents` 與常數一致。
- **補值器**：`proposal_numbers` 的 `split_numbers`／`minimal_filler` 的效果走訪改查「原語＋只能巢狀的效果」；帶 `refund_cooldown` 的技能自動補 `cost.cooldown: 1`（驗證器要求有冷卻可歸零）。
- **往返覆蓋率**：264 → **266／301**（`ash_harvest`、`blood_sacrifice` 往返成功）；`MIN_ROUND_TRIP` 提高為 266。剩下 18 個修正型（不開放）＋17 個「其他」，「只能巢狀」分類現在是空的（分類碼保留）。Mock 走子集：兩招各 10／10。
- 說明文字（`llm_hint`）納入 `tests/content/test_llm_hint.py` 的檢查。

## 2. AP、冷卻、耐力成為預算旋鈕（規格 2）

- **設計**：`content/skill_composer.yaml` 新增 `llm_cost`（schema：`LlmCostRules`／`CostStep`）：`max_cooldown: 5`、`steps`（15 階，由輕到重，每階各自獨立，欄位取「原本的值」與「這一階」較大者）：冷卻 1～5 → 冷卻 5＋法力 3／6／10 → AP 3 → AP 3＋冷卻 1～5 → AP 3＋冷卻 5＋法力 6。法力對武器技依 `stamina_per_mana` 換成耐力。
- **流程**：`proposal_budget.raise_costs`（在 `budget_filler` 先補必填最小值之後、`tune` 之前）：旋鈕全在最弱時的預算比例（新函式 `composer_tuning.base_ratio`）若已高於上限（`tuning.high`），依序試每一階，取第一個讓比例回到上限以內的；沒有超出、非主動技能、沒有任何一階能解決（維持原狀交給驗證器報錯）、結構不合法時原樣不動。之後照一般旋鈕調進區間。
- **範圍**：只用在**主動技能**；不影響手寫技能與隨機組合器（組合器的 `tune` 呼叫沒變）。冷卻上限取 **5**（06 6.5 的「冷卻最多 5」；引擎硬上限是 6，見待決 2）。
- **成效**（`evaluate_with_repair`，完整模型，種子 0～9）：`leap_slam` 0／10 → **10／10**（補到冷卻 2）；`gravity_burst` 10／10（冷卻 1）。Mock 走子集（題目＝原技能階級、稀有度、骨架）：`leap_slam` **0／10 → 10／10**（AP 2、冷卻 2）；`armor_break_combo` 9／10、`death_spiral` 8／10（剩下的是核心占比，不是預算）；`gravity_burst` 仍 0／10（子集 `displace` 沒有 `ring`，4-L8 待決 #5，不在本段範圍）。
- **手寫技能預算前後對照**（比照 3T-1）：另寫腳本對內容庫全部 **301** 招 `skill_budget(...)` 的 `repr` 逐行輸出，改動前（`ada247f5`）與第 1 段、第 2 段 commit 之後各比一次，**逐字相同**（`cmp` 無差異）。AP／冷卻旋鈕只存在於補值器；`budget.py`、`skill_budget.yaml` 沒有改。另有測試 `test_ladder_is_monotone`：同一技能套上每一階後預算比例不上升。

## 3. 候選產生器也出反應題（規格 3）

- 比例放 `content/roguelite.yaml` 的 `candidates.llm_reaction_permille`，**初值 100‰**（schema `CandidateSettings.llm_reaction_permille`，預設也是 100）。
- `TopicRequest.reaction_permille`／`CandidateRules.llm_reaction_permille`；`make_topic` 以獨立亂數串流（`fork("llm_topic.kind")`）擲骰，中了先出 `kind="reaction"` 的題目（骨架、事件由子集決定），出不了題（關鍵字、稀有度沒有可用的反應骨架）改出主動技能題。比例為 0 時與 4-L8 的題目逐字相同（有測試）。
- 測試：`tests/skillgen/test_proposal_l8b_topic.py`（比例為 0 不變、1000 全反應、300 約三成、確定性、Mock 提議器能答反應題）。

## 4. 命名關閉時的敘事、`--naming`（規格 4）

- `trpg.llm.naming.template_text(library, skill, taken)`：名稱與敘事都換成組合式名稱與模板敘事（`fallback_naming`），撞名加「（二）」；`make_proposer(naming=None)` 的 llm 技能改走它（`template_attempt`），不再採用提議裡 LLM 寫的 `concept`／`cast_flavor`；`name_source` 維持 `None`（不算命名）。
- `trpg llm propose --naming`：通過驗證的 llm 來源技能再命名（`--mock` 用 `mock_naming_client`，真模型用同一個 client）；每題行尾加「（命名 llm／fallback，N 次）」，摘要多一行「命名：N 個，生成 X，組合式名稱 Y，呼叫 Z 次」。沒加時用模板文字。`trpg run` 的 `--llm`／`--llm-mock` 本來就開命名，沒改。
- 測試：`tests/llm/test_naming.py`（模板敘事、不採用提議文字、同提議器不重名）、`tests/cli/test_llm_propose_cli.py`（`--naming`）。

## 5. 驗收

| 項目 | 結果 |
|---|---|
| pytest `-m "slow or not slow"` `tests/skillgen tests/llm tests/content tests/roguelite tests/cli tests/api tests/narrative tests/test_architecture.py tests/test_primitive_coverage.py --timeout=3000`（略過需要真模型的 `test_real_model_ping`） | 4765 passed、1 skipped |
| `ruff check`、`ruff format --check`、`mypy`（792 檔）、`lint-imports`（7 kept） | 全過 |
| `trpg llm propose --mock -n 10 --seed 0` | 正常：8 題 llm 通過、退回 2（pool 1、workshop 1），與 4-L8 相同；`--naming` 8 個命名全生成 |
| `trpg run auto --seed 5 --llm-mock` | 跑完（Mock 只能挑手寫技能，7 題全部退回，與 4-L6／L8 相同的 Mock 限制） |
| CLI 快照 | **沒有更動**（`llm_propose_mock.txt` 不變） |
| 存檔／prompt 版本 | **不遞增**（`trpg-run/10`、`skill-proposal/4`）：存檔欄位沒變；提議 prompt 的指令模板沒變（schema 與 `available` 是資料） |

## 6. 複雜度 noqa

沒有新增複雜度類 noqa（C901／PLR0911／0912／0915）。

## 7. 待 PM 決定

1. **「只能巢狀的效果」放在 `skill_primitives.yaml` 的獨立區段**（選項 a 的變形：不是 `primitives` 項目加旗標，而是頂層 `nested_only_effects`，避免被組合器、工坊、覆蓋率檢查當成原語）。`ruleset_hash` 因 YAML 改動而變（舊存檔的 hash 檢查照舊機制處理）。
2. **冷卻上限取 5**（規格寫「冷卻最多 5 等」，引擎硬上限是 6、`cooldown_cap` 折抵在 6 回合封頂）。若要放寬到 6 改 `llm_cost.max_cooldown` 與階梯即可。
3. **費用階梯是初值、未經模擬**（15 階；AP 3 的階在冷卻都用完後才出現）。同階梯用在 AP 3 會讓 LLM 技能花 3 AP；是否合適請 4-L9 看真模型再調。階梯只用在主動技能；被動、姿態、反應的超出預算仍不補費用。
4. **`damage_multiplier` 補值器取 1500（引擎允許 100–10000，≠1000）、`self_damage_of_hit` 取 100**（旋鈕 `none`，不隨預算調）。賭注結構的強度主要靠 `chance_permille`（有旋鈕）。
5. **反應題比例 100‰（初值）**。反應技成為候選時的取捨（玩家技能欄位與反應次數）沒有另外評估。
6. **命名關閉時，提議 schema 仍要求 LLM 寫 `concept`／`cast_flavor`**（會被丟掉）；要省 token 可在命名關閉時從 schema 移除，但 schema 組裝目前不知道命名開關，沒有動。
7. **`gravity_burst` 在子集內仍做不出**（聚集段 `ring`，4-L8 待決 #5）；完整模型沒問題。
8. 命名關閉時撞名會加「（二）」（`template_text` 與內容庫技能名一併避開），與舊行為（不去重）略有不同。
9. `llm` 標記的測試（`test_real_model_ping`）會被 `-m "slow or not slow"` 一起選到而連 8001 埠（連線被拒、失敗）；本段驗收時 `--deselect` 略過。建議之後把驗收指令改成 `-m "(slow or not slow) and not llm"`。

## 8. Commit

- `5f0dd5ca` feat(skillgen): open nested-only effects (refund_ap, gamble multipliers) to LLM proposals
- `c0bd3ed0` feat(skillgen): AP, cooldown and resource as budget knobs for LLM proposals
- `d75b2a05` feat(skillgen): candidate generator also asks reaction topics
- `0d5e6b44` feat(llm): template narrative when naming is off, add --naming to llm propose
- （本報告）docs: Phase 4-L8b report
