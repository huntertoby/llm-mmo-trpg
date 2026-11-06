# Phase 3J-2 報告｜定向蓄力原語＋龍的蓄力吐息

> 規格：`docs/phases/Phase3J計畫.md` 4.6。3J-3（身分）、3J-4（正式技能）、3J-5（外觀）沒有碰；沒有動 `client/src/render` 的紙娃娃與形態外觀。

## 做了什麼

### 1. 定向蓄力原語（引擎）

沿用延遲段（`trpg.engine.delayed`）的 `charging` 狀態與取消觸發，加上「方向」：

- `StatusInstance.direction`（新）：有值＝蓄力吐息（`skill_id` 是 `form_<形態 id>`），`None`＝複合技能的延遲段。
- `start_directed_charge(ctx, unit, direction)`：蓄力開始，發出 `followup_charged`（新欄位 `direction`；預計範圍＝以目前位置推算的錐形）。已經在蓄力時取代舊的（`replaced`）。
- 釋放：施放者**下一個自己的回合開始**（形態維持費之後、被動 `on_turn_start` 之前）以施放者**當下**的位置朝記著的方向結算；沿用 `run_delayed`（命中、傷害、元素、事件 `skill_followup`、被動觸發照常；不付代價）。範圍為空（牆／地圖邊緣）時 `followup_no_target`。
- 取消：倒下（`downed`）、暈眩／冰凍（`controlled`，既有觸發）、離開形態（新原因 `form_left`；`engine/forms.py` 的 `leave_form`，含切換、維持費不夠、取消姿態、戰鬥結束）。倒下時由 `leave_form` 以 `downed` 為原因取消。
- 預告：`charge_infos`／`ChargeInfo`／`TelegraphCharge`／`ChargeOut` 多了 `direction`；環境預告格、`StatusView.charge_tiles` 與延遲段共用，前端不需改預告繪製。
- 動作：`Attack` 多了 `direction`（恰好給目標單位、目標物件、方向其中之一）。蓄力武器的普攻＝開始蓄力（AP 照普攻）；給目標單位或物件時朝目標的方向（較大的軸向，相等取南北）；非蓄力武器帶方向會被拒絕。`legal_actions` 對蓄力武器多列四個方向（北東南西）；已經在蓄力時不再列普攻（避免白白取代）。
- 預覽：`preview(Attack)` 對蓄力武器回傳沒有傷害／命中的預覽，`affected_tiles` ＝釋放時的錐形。

### 2. 龍的蓄力吐息（資料）

- `content/forms.yaml`：龍的 `natural_weapon` 加上 `charge: {size: 3}`（1d8、智力、元素進入時選火／冰／雷，沿用 `form_element`）；schema `NaturalCharge`（`size` 2～4，只能用在遠程、無特性、無傷害加成的天生武器）。
- 結算技能由資料組出，**不登錄、不佔技能庫**：`trpg.content.form_breath.breath_skill(form, core, element)`＝錐形（大小 3）、一個傷害效果（骰、元素）、法術類別。屬性倍率要和普攻同為 0.3（法術預設 0.5），所以 `EffectSpec` 新增 `attr_permille`（damage 專用的屬性倍率覆蓋；原語定義沒有列它，玩家與 LLM 技能不能使用），`damage_parameters` 讀它。
- 卡片句（`form_text`，由資料產生）：「吐息 1d8 蓄力（錐形，大小 3）（智力 × 0.3，目前 +N），元素（進入時選火、冰、雷）傷害，普攻＝選方向開始蓄力，下回合開始時朝該方向釋放（蓄力中倒下、暈眩、冰凍或離開形態就取消）」。

### 3. 戰鬥紀錄、AI、前端文字

- 戰鬥紀錄：「◷ X 朝東開始蓄力「吐息」：下回合開始時釋放（錐形，目前預計影響 N 格）」；取消原因多了「形態解除了」；環境預告文字多了方向。
- AI：開始蓄力的預覽沿用延遲段評分 `_delayed_points`（預計範圍內〔敵人數×2 − 範圍內單位數〕× `delayed_enemy_points`），所以會選命中最多敵人的方向（`test_ai_dragon_charges_toward_the_most_enemies`）。
- 前端只動文字：`actionLabel` 對帶方向的普攻顯示「攻擊：向東蓄力」（其他動作清單）；朝敵人的快捷攻擊（點敵人）沿用，由引擎推方向。型別重產（OpenAPI → `schema.d.ts`：`Attack.direction`、`ChargeOut.direction`）。
- `LOG_FORMAT` `/79` → `/80`（`runner.py` 文件字串與 11 個測試字面值）。

### 4. 預算

形態技能的預算是固定的（`enter_form` 的 `base_points`＋`form_coefficient_permille`），天生武器本身不計價，所以吐息沒有新的計價式；沒有新增 `content/` 係數（見「待 PM 決定」1）。

## 驗收對照

| 驗收條件 | 證明 |
|---|---|
| 蓄力 → 下回合釋放，傷害＝卡片數字 | `test_released_at_next_turn_start_and_damage_matches_the_card`（骰面 5＋智力×0.3，兩個目標都等於）、`test_the_element_chosen_on_entry_is_the_breath_element`（冰、雷）、`test_card_sentence_describes_the_charged_breath` |
| 倒下／暈眩／冰凍取消 | `test_downed_stunned_or_frozen_dragons_lose_the_charge`（stun／frozen／lethal 三組）、`test_other_statuses_keep_the_charge`、`test_leaving_the_form_cancels_the_charge` |
| 方向與錐形格子 | `test_basic_attack_in_dragon_form_starts_a_charge_in_that_direction`（9 格、全在正東）、`test_attack_with_a_target_charges_toward_that_target`（5 組）、`test_release_uses_the_casters_current_position`、`test_a_wall_or_edge_can_shrink_the_cone`、`test_legal_actions_list_four_directions_and_none_while_charging` |
| 預告同環境預告 | `test_telegraph_and_view_show_the_cone`、`test_preview_of_a_directed_attack_shows_the_cone` |
| 存檔往返、重播一致 | `test_state_roundtrips_while_charging`、`test_a_charged_battle_replays_identically`；CLI：`trpg battle --map open_plain --ally-build build_form_tester_2 --seed 3` → `trpg battle replay`：「重播驗證通過：132 個動作、367 個事件，最終狀態一致」（局中龍朝東蓄力一次） |
| 戰鬥紀錄（開始、釋放、取消〔原因〕） | `test_narrative_lines_for_start_and_cancel`、`test_release_clears_the_charge_and_logs_it`、`test_charging_again_replaces_the_old_charge` |
| AI 選命中最多的方向 | `test_ai_dragon_charges_toward_the_most_enemies` |

## 驗收指令

| 指令 | 結果 |
|---|---|
| `UV_NO_SYNC=1 uv run pytest -q -n 8 tests/engine tests/content tests/skillgen tests/narrative` | 7328 passed、1 skipped（唯一失敗是技能圖示夾具，重產後通過） |
| `uv run python -m tests.narrative.icon_fixture`、`scripts/export_client_fixtures.py` | 重產（`EffectSpec` 多一個欄位，`skill_icons.json` 每個效果多 `attr_permille: null`，純資料） |
| `uv run pytest -q -n 8 tests/api tests/roguelite tests/narrative/test_skill_icon.py` | 484 passed |
| `uv run pytest -q -n 8 -m "slow or not slow" tests/cli --timeout=3000` | 147 passed、1 failed（`test_output_snapshots`：龍的卡片句變了，`UPDATE_CLI_SNAPSHOTS=1` 重產後通過；只有 `skills_list`／`skills_show_all` 的雜湊變） |
| `corepack pnpm -C client test` | 1038 passed |
| `uv run ruff check .`／`ruff format --check .`／`mypy`／`lint-imports`／`trpg content check` | 全過（1028 個檔案已格式化；mypy 738 檔；296 個技能通過預算與結構驗證） |

沒有跑完整的 `scripts/check.py`、`pnpm build`（依指示由 PM 跑）。

## 待 PM 決定

1. **預算係數**：規格要求「預算照延遲效果計價（係數放 `content/`）」。形態技能是固定 `base_points` 計價、天生武器不計價，吐息不是可組合的技能，所以沒有地方掛延遲折扣，我沒有新增沒人讀的係數。參考值：複合技能延遲段折扣 `composite_delayed_discount_permille: 800`。若要把吐息列入形態的預算（例如龍的 `base_points` 另加），請 PM／玩法 PM 決定。
2. **原語沒有開放給玩家技能**：目前只有「形態天生武器 `charge`」能用定向蓄力；複合技能的 `followup` 沒有 `directed`，工坊選項、LLM 提議 schema、組合器都沒有碰（組合器不抽，同規格）。要不要讓一般技能也能「選方向蓄力」留給之後。
3. **吐息仍擲命中**：結算沿用法術技，對錐形內每個目標各擲一次命中（法術命中修正），不是自動命中；傷害＝1d8＋智力×0.3，沒有武器加成。若要自動命中請告知。
4. **反應攻擊不蓄力**：藉機攻擊等反應性的普攻（不經過 `Attack` 動作）仍直接用龍的天生武器資料（1d8、遠程 3、智力），不是蓄力。
5. **維持費先於釋放**：回合開始先付形態維持費，付不起會自動解除形態並取消蓄力（`form_left`），那一輪不會噴。
6. **AI 輪替會取消蓄力**：AI 的形態輪替（3J-1b）在蓄力中仍可能換形態，造成蓄力被取消（靶場種子 3 看得到一次）。尚未加「蓄力中不輪替」的限制，請 PM 決定是否要。
7. **方向推算**：給目標時朝較大的軸向，距離相等取南北；火焰錐是否要改成「朝目標、可斜向」需要新的形狀規則，沒做。
8. **已在蓄力時的普攻**：`legal_actions` 不列（避免取代），但直接送 `Attack` 仍合法，會取代舊的（`replaced`）。
9. **`EffectSpec.attr_permille`**：新欄位只為了讓吐息的屬性倍率等於普攻的 0.3；若玩法 PM 想改成法術的 0.5，把 `form_breath.py` 的 `attr_permille` 拿掉即可（卡片句要同步）。

## 複雜度類 noqa

沒有新增（`C901`、`PLR0911`、`PLR0912`、`PLR0915` 都沒有新增；`preview._build` 為了不超標，把蓄力預告格抽成 `_breath_tiles`）。
