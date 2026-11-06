# Phase 3-50b 報告：代價換強度修正（玩法 PM 回覆 3-50）

規格：`docs/phases/Phase3計畫.md` 第 60b 節；設計：`docs/design/06-技能.md` 6.5（#54）。背景：`Phase3-50報告.md` 的「待 PM 決定」#1～#4。

## 做了什麼（對照規格 1～5 點）

1. **護盾持續時間**
   - `shield` 原語加參數 `duration`（2～3 回合，省略＝2＝現狀）：`content/skill_primitives.yaml`、`EffectSpec.duration`（既有欄位）→ `ShieldEffect.duration` → 處理器用它取代 `shielded` 狀態預設回合；已有護盾時吸收量取較大、剩餘回合取較長（預設值時行為與以前相同）。技能的護盾、`consume_status`／`on_kill` 等 `then` 內的護盾都吃這個欄位；召喚物脈動的護盾（`summons.py`）沒有動。
   - 預算：`shield` 點數＝骰子平均 × `shield_duration_permille[n]`，係數放 `content/skill_budget.yaml`：`shield_duration_permille: [1000, 1300]`（2 回合 1000‰、3 回合 1300‰；**初值，未經模擬**）。
   - **冰甲封身**：護盾 3 回合後 `3d8` 會到 130%，**縮護盾骰為 `4d4`（平均 10，預算 13.0／13.5＝96.3%）**；其餘（自暈、冷卻 4、法力 6）不變。「自暈 2 → 暈眩結束後下一回合護盾仍在」有行為一致測試（護盾 3 → 暈眩結束時剩 1）。
2. **自暈不歸零本回合**
   - `pay_self_costs` 拿掉 AP／移動點數歸零。
   - 新增 `StatusInstance.dormant`：自己付的 `skip_turn` 狀態在**自己的回合中**施放時以 `dormant` 施加，`skip_turn_status` 視為沒有（所以本回合還能移動、再施放，也不會中斷移動），`end_turn` 結束時清除並同時倒數 → 結果＝**本回合照常、下一回合被跳過、再下一回合恢復**（持續時間仍是固定 2）。非自己回合時施放（理論上）不會 dormant，立即生效。
   - 表格測試 `test_the_self_stun_timeline_this_turn_normal_next_skipped_then_recovered`（施放後移動＋再施放、之後每個 U1 回合依序 skipped → acted，暈眩移除）與 `test_the_dormant_stun_...`（dormant → 回合結束後生效、剩 1）。
3. **透支不算自身狀態**：驗證器拿掉 `cap.self_penalty_single`（`SkillCost.self_status` 單一欄位本身就保證「一招最多 1 個自身狀態」，測試保留）；工坊（`options.py`）兩個欄位同時顯示、描述改「可和自身狀態並用」；組合器的透支改為獨立抽（原本只在沒抽到自身狀態時才抽）；LLM 提議：`cost_penalty` 只剩自身狀態，新增可省略欄位 `cost_overdraft: true`（`self_penalty.py`、`proposal.py`，往返與 few-shot 轉換同步）。整體 50% 上限照舊（測試：暈眩＋透支＋冷卻＋法力→raw>500、截斷 500）。
4. **卡片文字**：自身狀態代價行改為「代價：施放後自己暈眩，到你下個回合結束（換 32% 預算）」；持續 3 時寫「到你下 2 個回合結束」（`narrative.skills.self_status_until`）。護盾效果句寫「持續 n 回合」。這同時改了所有既有自身狀態技能的卡片（例：捨身突刺）。
5. **自付代價能否被淨化：沒有動**（等使用者決定）。

## 紀錄格式與影響盤點

- `LOG_FORMAT`：`/68` → **`/69`**（護盾 `duration`、自暈 `dormant`；`/68` 紀錄無法重播）。若 3I-3 也遞增，合併時取較大者並合併 `runner.py` 的說明。測試裡寫死 `/68` 的 9 處改為 `/69`。
- 重產：`client/src/battle/fixtures/glossary.json`（護盾說明）、`client/src/render/fixtures/skill_icons.json`（`tests.narrative.icon_fixture`）、`tests/cli/snapshots/cli_output_hashes.json`（`UPDATE_CLI_SNAPSHOTS=1`，`skills_list`／`skills_show_all`）。`client/openapi.json` 重產後沒有變（`gen:api` 不需要）。run auto 種子：CLI 快照測試通過。
- `content/workshop_text.yaml`：兩條 `shield` 說明（原語、工坊）改成含持續時間（`test_workshop_text_48f` 要求原文與改寫對得上）。
- 組合器亂數串流改變（透支改為獨立抽）：同種子的隨機組合技能可能不同（已反映在 CLI 快照）。
- 與 3I-3 的衝突點：`trpg.skillgen` 的 `proposal.py`（`common` 欄位與 `_SUPPORTED_SKILL_KEYS`）、`options.py`（`_cost_step`）、`composer_parts.py`（`build_cost` 的透支）、`validate.py`（`_self_cost_violations`）、`budget.py`（`_plain_base_points` 的 dice_average 分支）、`skill_rules.py`（`shield_duration_permille`）；改動都很小且集中。

## 驗收

pytest：engine、content、skillgen、llm、narrative、roguelite、api、shared、sim 全過；`-m "slow or not slow" tests/cli` 全過（快照已更新後）；vitest 958 通過；`vite build` 通過；ruff、format、mypy（696 檔）、lint-imports 通過。含四招示範技能的整場戰鬥重播一致（`test_a_battle_with_the_four_demo_skills_replays_identically`）。新增／改寫測試：`tests/engine/test_self_costs.py`（時間線表格、護盾比暈眩久、護盾預設 2 回合、較長護盾不被較短的縮短）、`tests/skillgen/test_self_costs.py`（透支可並用、護盾預算係數與範圍 2～3、冰甲封身在 70～100%、卡片「到你下個回合結束」、LLM 自身狀態＋`cost_overdraft` 並用）。

## 待 PM 決定／注意

1. **只有暈眩做 dormant**：沉默、流血、易傷等其他自身狀態仍立即生效（沉默會讓本回合不能再放法術）。規格只要求暈眩「本回合照常」，我沒有擴大；若玩法 PM 也要沉默本回合照常，同樣機制可套用（`dormant` 判定只看 `skip_turn`，改成看 `silenced` 即可）。
2. **dormant 暈眩在本回合期間仍會在 UI 上顯示暈眩圖示**（狀態已存在、只是不生效）；本回合內不能執行反應的限制也還沒有（本來就是自己的回合，沒有反應時機）。
3. **護盾 3 回合係數 1300‰ 是初值**（每多 1 回合 ＋30%），沒有模擬；冰甲封身因此縮到 `4d4`（96.3%）。請玩法 PM 確認係數與骰型（`3d6` 是 101.1% 超標；`2d8` 是 86.7%）。
4. **設計文件 6.5 的範例文字**仍寫「暈眩 1 回合」、「技能給的護盾在暈眩結束後照常存在」；卡片已改成「到你下個回合結束」，文件文字交玩法 PM 決定是否同步。
5. **透支和自身狀態並用**：兩者同時最多折抵 200＋400（暈眩專屬上限 400）＝600，仍被整體 500 截斷；組合器現在兩者可同時抽到，機率仍是 `self_status_permille × overdraft_permille`（很低）。
6. 環境備註：worktree 的 `client/node_modules` 用 `pnpm install --offline --frozen-lockfile` 安裝（pnpm v12.14.0 取自 corepack 快取）；沒有建立指向主資料夾的連結。
