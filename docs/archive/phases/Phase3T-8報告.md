# Phase 3T-8 完成報告｜組合器骨架 ID 分支移 YAML、私有匯入改公開

純整理、行為不變。規格：`docs/phases/Phase3T計畫.md` 4.2；背景：`docs/phases/Phase3後段審查-Python.md` 第 9 點。

## 1. 資料化的骨架 ID 分支

新增 `SkeletonDef.composer`（`ComposerTraits`，`src/trpg/content/skill_rules.py`），各骨架 YAML 末尾的 `composer:` 區塊填值；預設值＝沒有特殊行為，所以新增骨架不需改程式。

| 原本（依 ID 寫死） | 位置 | 現在（YAML 欄位） | 骨架 |
|---|---|---|---|
| `id in (control, aura, displace)` 核心數量（含 displace 子分支，共 3 處） | `composer_parts._core_count` | `core_count: up_to_two / second_by_chance` | control、aura＝`up_to_two`；displace＝`second_by_chance` |
| `id == combo` 連段雙傷害核心 | `choose_core` | `double_damage_core` | combo |
| `shape == single and id == aura` 有益效果作用在友方 | `_beneficial_affects` | `single_allies` | aura |
| `id != passive` 自身形狀可有害 | `_status_effect` | `self_shape_harmful_ok` | passive |
| `id == control` 核心狀態可能改自我增益 | `_wants_buff` | `buff_core_chance` | control |
| `id in (builder_finisher, trap)` 結構效果扣附帶上限 | `_secondary_count` | `setup`（非空即扣 1） | trap、builder_finisher |
| `id == trap` 陷阱設定／`id == builder_finisher` 層數效果 | `build_effects` | `setup: trap / stack` | trap、builder_finisher |
| `id == aura` 不加附帶效果 | `build_effects` | `no_secondary` | aura |
| `id in ("area",)` 吹送／震波附帶（2 處，`_BLOW_SKELETONS`、`_SHOCKWAVE_SKELETONS`） | `_blow_secondary`、`_shockwave_secondary` | `blow_secondary`、`shockwave_secondary` | area |
| `id == aura` 條件種類 | `_condition_kinds` | `condition_mode: allies` | aura |
| `id in (builder_finisher, trap)` 不帶技能條件 | `build_condition` | `condition_mode: never` | trap、builder_finisher |
| `id == combo` 兩段以上傷害時條件寫在第二段 | `build_condition` | `effect_level_condition` | combo |
| `_HAND_WRITTEN_ONLY`（隨機組合器不產生） | `random_composer` | `hand_written_only` | consume_status、summon |
| `_EXPLICIT_ONLY_ACTIVE`（3 處使用） | `random_composer` | `explicit_only_active` | builder_finisher、trap、rune、sacrifice |
| `_LEGENDARY_SKELETONS`（2 處使用，含錯誤訊息） | `random_composer` | `legendary` | aura、modifier |

`composer_parts.py` 與 `composer_special.py` 已無 `skeleton.id ==/in` 比對。

## 2. 留下的分支與理由（純邏輯或與技能種類的建構函式綁定）

- `random_composer._wants_passive`／`_wants_special`／`_compose_special`／`_attempt_passive`：以 `passive`、`reaction`、`stance`、`modifier`、`builder_finisher`、`trap`、`rune`、`sacrifice` 的名稱挑「該用哪個建構函式」（`_attempt_reaction`、`_attempt_stance`……）與讀 `skill_composer.yaml` 的各自機率；骨架種類對應程式建構函式，新增這類骨架本來就要新寫建構函式，無法只靠資料。
- `random_composer` 傳說技能：`skeleton or "aura"` 預設值、`_compose_legendary_result` 的 `modifier → ("modifier",)`、否則 `("rule_change","rule_rewrite")`：決定傳說核心種類的邏輯，屬 `composer_special` 的流程，非單純旗標。
- `composer_special` 裡寫入技能草稿的 `"skeleton": "modifier"`／`"aura"`：輸出內容，不是分支。
- `option_followup.FOLLOWUP_SKELETON = "displace"`、`proposal.CLOSED_SKELETONS`（LLM 提議面，非組合器；規格不含）。
- `composer_parts._HAND_WRITTEN_PRIMITIVES`：原語 ID，不是骨架 ID，本次不動。

## 3. 私有匯入改公開

| 原名 | 新名 | 呼叫端 |
|---|---|---|
| `engine.battle._actor` | `acting_unit`（加入 `__all__`） | `engine/preview.py`、`battle.py` |
| `engine.summons.core._order_index` | `owner_order_index`（加入 `__all__`） | `engine/race/skills.py` |
| `engine.summons.core._insert_in_order` | `insert_in_order`（加入 `__all__`） | `engine/race/skills.py` |

（`skills/revive.py` 自己的 `_order_index` 是模組內部函式，沒動。）

## 4. 前後比對證據

- 隨機組合器：種子 0–599 × 稀有度（不指定／common／rare／epic／legendary）× 骨架（不指定／輪替各骨架）共 6000 次呼叫（成功 4805、預期失敗 1195），把每個技能的 JSON 與失敗類型串成 SHA-256：改前（用 `git archive HEAD` 取出的原始碼）與改後皆為 `de34e6235b01a77bf4b467dcf2992cfd520d99c6ad429e2d3c0d0c9eff5eb8ff`，**逐字相同**。
- 唯一文字差異：非傳說骨架要求傳說技能時，錯誤訊息的「可用：」清單由寫死的「modifier、aura」改成由 YAML 產生（依 ID 排序為「aura、modifier」）；測試只比對「傳說」，通過。雜湊比對時失敗只記類型。
- 測試：`tests/skillgen tests/content`（3688 passed, 1 skipped，含新增 `tests/skillgen/test_composer_traits_3t8.py`）；`tests/engine`＋`tests/test_architecture.py`（3784 passed, 3 xfailed, 1 xpassed，xfail／xpass 為既有的平衡延後標記）；`tests/llm tests/roguelite tests/api tests/narrative`（921 passed）；`tests/cli`（155 passed）。
- `ruff check`、`ruff format --check`、`mypy`、`lint-imports` 全過。手寫技能預算、CLI 快照、LLM 提議子集沒有程式變動（相關測試全過）。

## 5. 待 PM 決定

1. `content/skills/` 套件內部各子模組互相匯入底線名稱（`constants` 的 `_PERMILLE`、`_unique`、`_MAX_*`，`followup._FOLLOWUP_CHECKS`，`skill._int_param_problems`、`effects._check_composition` 等約 40 個，`__init__.py` 並再匯出供測試）。這是同一套件拆檔後的內部共用，不是跨模組；機械式改名範圍大，本次未動。是否另排一段？
2. 測試端仍有約 30 處匯入 `src` 的私有函式（例如 `ai.utility._weapon_terms`、`composer_parts._composable`）；測試白箱使用，未動。
3. `_wants_special` 的「骨架 → 機率設定」對照表（見第 2 節）是否也要資料化（需先決定 `skill_composer.yaml` 的結構），目前判斷收益低。
