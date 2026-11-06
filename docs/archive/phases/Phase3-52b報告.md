# Phase 3-52b 報告｜層數擴充小修（玩法 PM 回覆 3-52；06 6.32）

實作者：agent（sonnet 5.5）。範圍：`docs/phases/Phase3計畫.md` 第 62b 節第 1～4 點。

## 1. 做了什麼

### 1.1 專注自動消耗（#2）

- 資料：`content/stacks.yaml` 的專注多了 `auto_consume: {per_stack_permille: 150}`（新 schema `AutoConsumeSpec`，只允許 `owner: self` 且加成傷害的層數）。
- 引擎：`Cast.consume_stacks` 結算完技能自己的 `consume_stack` 之後呼叫新的 `Cast.auto_consume_stacks`。規則（`trpg.content.stacks.auto_consumed`，引擎、卡片共用）：
  - 只有 **主動技能** 且 **有傷害效果** 才吃；治療、護盾等不造成傷害的技能不吃（專注留給下一個傷害技能）。
  - 技能自己有 `consume_stack` 專注（示範的「專注一擊」）時照技能的設定，不重複加成、只消耗一次。
  - 消耗全部專注，每層傷害 +15%，加成併進 `caster_bonus`（和既有的消耗加成同一條路，命中與否都消耗，與明寫的消耗一致）。普攻不是技能，不吃。
- 自動累積的資格不變（身上有消耗專注的技能才會因站定累積；示範的累積技能 `add_stack` 照舊），所以沒有示範技能的既有戰鬥不受影響。
- 卡片：每張「會自動消耗專注」的技能卡，層數列多一個「專注（消耗／利用）」（`skill_stacks` 用同一個 `auto_consumed`），可點開名詞說明；名詞對照表（`stack_rules`）的消耗行加了「你下一個造成傷害的主動技能會自動消耗全部層數，每層傷害 +15%」，層數描述文字同步。預覽走真正的引擎，傷害數字與「消耗專注」事件自然顯示。

### 1.2 氣的治療加成只算治療自己（#4）

- 資料：`ConsumerSpec.heal_self_only`（氣設為 true；只能用在 `boosts` 含 `heal` 的層數）。
- 單一判斷：`ConsumerSpec.boosts_effect(effect)`（型別在 `boosts`；治療加成只算自己時，治療的 `affects` 必須明寫 `self`）。驗證器（`_consumer_problems` → `ConsumerSpec.gaps`）、預算（`_consume_stack_points` 只算被加成的效果）都用它；引擎 `Cast.heal_multiplier(self_heal=…)` 只在效果對象為 `self` 時加治療加成（聖光雙效、獻祭治療不吃氣的加成）。聖能不受影響（任何治療與護盾都加成）。
- 卡片與說明文字：「每層使本技能傷害、治療自己 +15%」「消耗：技能每層提高傷害、治療自己」。

### 1.3 工坊事前停用不能消耗的層數（#6）

- `trpg.skillgen.option_effect_rules.stack_unavailable_reason(skill, stack_id, library)`：把候選的 `consume_stack` 放進草稿，呼叫與驗證器共用的 `ConsumerSpec.gaps`；`with_param_blocks` 對「消耗層數」原語的層數子選項逐一標上 `info.unavailable_zh`（白話原因＋怎麼改，例如「『聖能』只加成治療、護盾：先加入治療、護盾效果（任一種），再選這個層數」「『寒霜』只有冰霜傷害的技能才能消耗：加入符合的效果，或改選別的層數」）。前端的選單已會把有 `unavailable_zh` 的選項停用並附原因（已選的那項不停用），**前端沒有改動**。
- 工坊沒有讓玩家選標籤，草稿沒有標籤時「帶某標籤」的條件（連擊點的終結、靈魂碎片的召喚／詛咒）先視為符合，免得整個層數永遠選不到；有標籤時照實判斷。

### 1.4 其他

- `LOG_FORMAT` `/73` → `/74`（規則包內嵌的層數表多了 `auto_consume`、`heal_self_only`；既有戰鬥的專注技能行為改變）。
- 重產：`client/src/battle/fixtures/glossary.json`；CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`）。OpenAPI 與 `schema.d.ts` 沒有型別變動（`export_openapi.py` 無差異）；`skill_icons.json` 無差異。

## 2. 測試

- `tests/engine/test_stack_auto_consume_52b.py`（8）：下一個傷害技能吃掉全部專注（1～3 層 +15%／層、吃完歸零）、非傷害技能不吃、示範消耗技不重複加成且只消耗一次、`auto_consumed` 的判斷（被動、治療、自帶消耗）、氣只加成治療自己（`boosts_effect`）、氣的自我治療實戰加成。
- `tests/skillgen/test_stack_workshop_52b.py`（8）：只有傷害時停用治療／護盾層數、只有護盾時停用傷害層數與氣、自我治療才開放氣、友方治療不開放氣、冰霜要冰霜傷害、**選項與驗證器一致**（三招示範技 × 全部層數，選項說可以＝驗證器不報錯）、氣的預算只算自我治療。
- 全跑：pytest `tests/engine tests/content tests/skillgen tests/narrative tests/api`（6877 通過、1 skip、1 個過期 fixture 已重產）；`-m "slow or not slow" tests/cli`、vitest、build、ruff、format、mypy、lint-imports 見最後回報。

## 3. 待 PM 決定

1. **卡片噪音**：因為「專注」會被所有主動傷害技能自動消耗，每張主動傷害技能卡的「層數」列都會多一個「專注（消耗／利用）」。若覺得太吵，可改成只在名詞對照表說明（拿掉 `skill_stacks` 的自動項目）。
2. **專注的自動消耗不看命中**：與既有 `consume_stack` 一致，施放就消耗（沒打中也吃掉）。若要「命中才吃」需另開規則。
3. **氣的治療加成要求治療明寫 `affects: self`**（預設對象是友方）：預算、驗證器、引擎一致；影響範圍僅示範的「運氣調息」。
4. **標籤條件在工坊先視為符合**（見 1.3）：真正的標籤檢查仍由驗證器在提交時做；日後工坊若能選標籤，這個假設自動變成照實判斷。
5. **`LOG_FORMAT`**：另一個 agent（3K-2）也可能遞增，合併時請 PM 統一版本號（本段是 `/74`）。
