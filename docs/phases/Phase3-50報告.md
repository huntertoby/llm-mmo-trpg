# Phase 3-50 報告：代價換強度第一批（玩法決定 #54）

規格：`docs/phases/Phase3計畫.md` 第 60 節；設計：`docs/design/06-技能.md` 6.5（`4a974b8`）。本報告對照規格 7 點與 6.5 的共通規則 7 條，最後列出「待 PM 決定」。

## 做了什麼

- **自身狀態**（`cost.self_status`）允許清單加入 **暈眩**（固定 2 回合、專屬上限 40%）、**沉默**（限法術技）、**流血**。數值全在 `content/skill_budget.yaml` 的 `allowance.self_status`（`status_caps`、`fixed_duration`、`spell_only`）。暈眩折抵 8 × 1 × 40‰ ＝ 320‰（卡片「換 32% 預算」）。
- **透支**（新代價 `cost.overdraft: 1`）：施放後自己下一個回合少 1 AP，固定折抵 `allowance.overdraft_permille: 200`。實作為新狀態 `overdrawn`（`content/statuses.yaml`，`ap_penalty: 1`，沒有 `budget_points`，只能由代價施加）；`start_turn` 在回合開始時 `AP −= ap_penalty`（最低 0）。
- **自付的代價** 走 `ApplyStatusEffect.self_paid`：不觸發控制遞減、不受 Boss 硬控轉換（施放路徑與灌注路徑共用 `trpg.engine.self_costs`）。
- 預算器、驗證器（`_self_cost_violations`）、工坊選項（`trpg.skillgen.options`）、隨機組合器（`composer_parts`）、LLM 提議（`trpg.skillgen.self_penalty`，可省略欄位 `cost_penalty`）、卡片文字（`narrative.skills.cost_parts`）、AI（`engine/ai/self_costs.py`、`ai_profiles.yaml` 的 `self_cost:` 與 `status_values.overdrawn`）都支援新代價。
- 4 招示範技能（預算比例見下表）。
- 戰鬥紀錄格式 `LOG_FORMAT` 遞增為 `trpg-battle-log/68`（自付狀態不再登記控制遞減；新狀態與暈眩的 AP 歸零；`/67` 紀錄無法重播）。
- 附帶修正：`candidates.py` 的 `usable()` 排除傳說技能（組合器的隨機結果原本可能漏出傳說候選；這次組合器抽籤變動後既有測試暴露）。
- 前端：`statusIcon.ts` 加透支圖樣；`glossary.json`、`skill_icons.json`、CLI 快照、技能總數 221 → 225 已更新。

## 共通規則 7 條對照

| # | 規則 | 實作位置 | 測試 |
|---|---|---|---|
| 1 | 各自套上限後加總，整體上限 50% | `skill_budget.yaml` `total_cap: 500`；暈眩專屬 `status_caps.stun: 400` | `tests/skillgen/test_self_costs.py`：`test_the_total_allowance_is_capped_at_fifty_percent`、`test_the_stun_allowance_is_320_...`、沉默／流血折抵參數化 |
| 2 | 一招最多 1 個自身狀態 | `SkillCost.self_status` 單一欄位（schema）；自身狀態與透支擇一（驗證器 `cap.self_penalty_single`） | `test_a_skill_can_have_only_one_self_status`、`test_self_status_and_overdraft_cannot_be_combined`、`test_only_active_skills_can_pay_self_costs` |
| 3 | 自付狀態不觸發控制遞減、不受 Boss 轉換 | `ApplyStatusEffect.self_paid`（`effects/handlers.py`） | `tests/engine/test_self_costs.py`：`..._does_not_trigger_control_diminishing`、`..._is_not_converted_on_a_boss`（含兩個對照組：別人施加仍遞減／仍轉換） |
| 4 | 會白拿折扣的代價限骨架，驗證器檢查 | `cap.self_status_category`（沉默限 `category: spell`）、`cap.self_status_duration`（暈眩固定 2）、`cap.self_status`（允許清單） | `test_self_silence_is_only_allowed_on_spells`、`test_stun_duration_is_fixed_at_two`、`test_unlisted_self_statuses_are_still_rejected`；工坊與驗證器同源：`test_workshop_options_and_the_validator_agree_on_silence` |
| 5 | 卡片代價行、工坊即時顯示折扣 | `cost_parts`：「代價：施放後自己暈眩 1 回合（換 32% 預算）」、「…下一個回合少 1 AP（換 20% 預算）」；工坊選項附折抵說明、暈眩持續回合鎖 2、沉默對武器技事前停用並附原因 | `test_the_card_shows_the_cost_line_with_the_discount`、`test_the_workshop_*` |
| 6 | AI 使用條件 | `trpg.engine.ai.self_costs.self_cost_gate`：自暈＝HP < 50% 且 6 格內有敵人；透支＝這一擊能擊殺或波及敵人 ≥ 2（數值在 `ai_profiles.yaml` `self_cost:`）；不成立時分數壓成負數 | `tests/engine/test_self_costs.py`：`test_the_ai_self_stuns_only_when_...`、`test_the_ai_uses_overdraft_only_for_...`、`test_skills_without_a_self_penalty_are_never_gated` |
| 7 | LLM 只能從允許的代價挑一個 | 提議模型多可省略欄位 `cost_penalty`（enum＝稀有度夠的允許狀態＋`overdraft`）；持續時間由引擎決定；其餘由驗證器 | `test_the_proposal_schema_lists_exactly_the_allowed_penalties`、`test_a_common_proposal_cannot_pick_rare_only_penalties`、未知／多選／稀有度不足被拒、沉默放武器技被驗證器擋下 |

## 自暈的配套（規格第 4 點）

- 仍可被推、拉、傳送：`test_a_self_stunned_unit_can_still_be_pushed_pulled_or_teleported`（`forced`／`teleported`）。
- 護盾照常存在、可吸收傷害：`test_the_shield_from_the_skill_exists_while_stunned_and_absorbs_damage`、`test_the_shield_is_not_removed_when_the_stun_is_applied_or_ends`（暈眩的施加與結束都不移除護盾；**但見待決 1**）。

## 4 招示範技能

| 技能 | 代價 | 預算比例（70～100%） |
|---|---|---|
| 冰甲封身 `skill_frost_armor_seal`（T2 光環／自身，護盾 3d8） | 自暈（折抵 320 ＋ 冷卻 200 ＋ 法力 30 → 上限 500） | 100.0% |
| 孤注詠唱 `skill_all_in_chant`（T2 範圍，3×3 閃電 2d12） | 自我沉默 2 回合（200） | 99.6% |
| 血怒斬 `skill_blood_rage_slash`（T2 近戰 ×3.0） | 自己流血 2 回合（120） | 94.1% |
| 竭力一擊 `skill_overdraft_strike`（T2 近戰 ×2.8） | 透支（200） | 86.1% |

四招都用 `tests/content/test_coverage.py` 的 `_POOL_ONLY` 當裝備來源（builds.yaml 是模擬回歸範本，不為示範而改）。

## 驗收

pytest：engine（全）、content、skillgen、llm、roguelite、narrative、api、shared、sim 全過；`-m "slow or not slow" tests/cli` 全過（更新 `cli_output_hashes.json`）；vitest 948 通過；`tsc --noEmit` 與 `vite build` 通過；ruff、format、mypy（694 檔）、lint-imports 通過；含四招示範技能的整場戰鬥重播一致（`test_a_battle_with_the_four_demo_skills_replays_identically`，AI 真的用到示範技能）。新增測試：`tests/engine/test_self_costs.py`（18）、`tests/skillgen/test_self_costs.py`（31）。

## 待 PM 決定

1. **「技能給的護盾在暈眩結束後照常存在」與現有護盾對不上**：護盾固定持續 2 回合，暈眩固定 2 回合，兩者倒數同步，**在被跳過的回合結束時同時消失**。目前行為＝護盾在整個暈眩期間存在、可吸收傷害，暈眩結束的同一刻到期（這其實是「換護盾」玩法的完整收益窗口：敵人打一輪）。若設計本意是暈眩結束後護盾還在，需要決定：護盾持續改 3？還是這類自暈技能的護盾另設持續時間（`shield` 原語目前沒有 `duration` 參數）？我沒有自行改。
2. **自暈的當回合**：照 6.5「暈眩期間沒有 AP、移動、反應」，我讓自付的 `skip_turn` 狀態在施放後把本回合剩下的 AP 與移動點數歸零（`pay_self_costs`）。若希望暈眩只跳過「下一個」回合、本回合剩餘 AP 還能用，把 `pay_self_costs` 的歸零拿掉即可（預算不變）。
3. **「一招最多 1 個自身狀態」的解讀**：我把透支也算進去——自身狀態與透支不能同時出現（驗證器 `cap.self_penalty_single`）。若玩法 PM 認為透支不算自身狀態、可疊加，需放寬（整體上限 50% 仍會截斷）。
4. **卡片回合數**：依 6.5 範例「暈眩 1 回合」，卡片顯示 **有效回合（duration − 1）**。這也改了既有自身狀態技能的卡片文字（例：捨身突刺「自身易傷 2 回合」→「自己易傷 1 回合（換 16% 預算）」）。
5. **自付狀態可被淨化**：`cleanse` 會移除 debuff，包含自付的暈眩、沉默、透支。目前沒有特別保護（隊友或自己的淨化能提早解除代價）。是否要讓 `self_paid` 的狀態不可淨化？
6. **數值為初值未經模擬**：AI 使用條件（HP 50%、6 格、波及 ≥ 2）、`status_values.overdrawn: 8`（約少半個回合行動）、組合器透支機率 `overdraft_permille: 40`、示範技能數值。冰甲封身剛好在預算上限 100.0%（組得出來，但沒有餘裕）。
7. **隨機組合器的亂數串流改變**：允許清單變長、新增透支抽籤，所有隨機組合的結果（種子 → 技能）都不同；CLI 快照、`skill_icons.json` 已更新。
8. **LLM 提議的持續時間**：LLM 只挑代價種類；持續時間由引擎決定（暈眩 2，其餘取最短的 2）。流血示範技能因此用 2 回合（才能與提議往返測試一致）。
9. **環境備註（非程式碼）**：主檢出 `client/node_modules` 缺 `@jridgewell/sourcemap-codec`，`vitest` 在主檢出無法啟動（開始前就如此）；我在 worktree 另裝（pnpm 10，不動主檢出）才跑得起來。另外嘗試安裝 pnpm 時在 `%LOCALAPPDATA%\pnpm\.tools\pnpm\` 留下 `12.14.0` 與一個 `_tmp` 目錄（不影響專案，可刪）。
10. 與 3-51 的衝突點（PM 合併時）：`trpg.skillgen.validate`（`_cap_violations` 改呼叫新的 `_self_cost_violations`）、`options.py`（`_cost_step`、`_self_status_field`）、`candidates.py`（`usable()` 一行）、`composer_parts.py`（`build_cost`、`_self_status_cost`）、`proposal.py`（`common` 欄位多 `cost_penalty`）；`LOG_FORMAT` 若兩邊都遞增，合併時取較大的並合併說明。
