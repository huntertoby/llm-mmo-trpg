# Phase 5D-2b 完成報告：5B-4f／5D-2 收尾

> 實作者：implementer agent（2026-11-03）。範圍：`docs/phases/Phase5計畫.md` 第 1 節 5D-2b 列（玩法 PM 2026-11-03 代決 7 項）；背景 `Phase5D-2報告.md`、`Phase5B-4f報告.md`、`Phase5D-3報告.md`、20.2、20.5、19.2.4、08 8.21.4.1。分支 `worktree-agent-aa22b0b183fe670c3`。
> 沒動引擎與 `LOG_FORMAT`；`trpg-char/1`／`trpg-world/1`／`trpg-wlog/1` 不升版號（新欄位都有預設值，照 5A-6 起的慣例）。

## 1. 各項做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 骨架 6 部分成功小蓮 +10 | 事件好感度表加 `monks_dispute partial +10`（只動 content） | `content/world/social/cloud_ridge.yaml` |
| 2 | 保底時三選一標題與「作罷」句也用「焦痕未冷的古松」 | `PendingOffer.guaranteed`、`EventLeftEvent.guaranteed`（都預設 `False`）；機遇解法存三選一時帶 `trigger.guaranteed`，離開地點作罷時帶 `pending_event.guaranteed`；`pending_offer_view` 與動作紀錄改用 `who_for(guaranteed=)` | `world/state.py`、`actions.py`、`events.py`、`quests.py`、`solutions.py`、`api/world_story_view.py` |
| 3 | 補技能強化詞條（8.21.4.1） | 新增 8 條（製造 1、利用 1）：潮濕 `affix_kw_wet_area`／`affix_kw_wet_damage`、隱蔽 `affix_kw_conceal_duration`／`affix_kw_conceal_damage`、點燃（缺利用）`affix_kw_ignite_damage`、倒地（缺製造）`affix_kw_prone_area`、中毒 `affix_kw_poison_duration`／`affix_kw_poison_damage`。**雲嶺偏向原本寫成 `hidden`（不是關鍵字 ID），改成 `concealed`**；`loot_problems` 加「區域偏向關鍵字要在 `skill_keywords.yaml`」的檢查，之後打錯會在載入時報錯 | `content/affixes.yaml`、`content/world/loot.yaml`、`content/world_loot.py`、`library.py` |
| 4 | 影子裝備壓到招募者等級後照穿（#87） | 新函式 `item_gen.downscale_item(library, item, level)`：照 8.22.1 的物品等級規則，物品等級改成招募者等級（基礎數值跟著物品等級走），詞條部分用新等級的預算，依序「取能放進剩餘預算的最大 N」但不超過原本的數值，並替後面的詞條保留最低點數；詞條種類、條數不變。`shadow_equipment` 改成全部照穿（取代代決 5D2-10） | `content/item_gen.py`、`world/gear.py`、`world/shadows.py` |
| 5 | 精英掉裝備改每名精英 1 件（20.2） | 陣容每名精英抽 1 件（史詩 50%）；沒有精英照一般 15% 抽 1 次。第 1 名精英用原本的 `fork("gear")`，第 2 名起 `fork("gear/<序號>")`，只有 1 名精英的場次結果不變 | `world/loot.py`、`content/world/loot.yaml` |
| 6 | 背包滿時戰後選要丟哪件 | 放不下的不再直接不撿，存進 `CharacterState.pending_loot`（`PendingLoot`：材料、裝備）；新世界動作 `loot_choose`（`drop_items`、`drop_gear`）：新拿到的和背包裡原本的都可以丟（材料先丟新拿到的）、穿戴中的不能丟，丟完剩下的戰利品必須全部放得下，否則拒絕並說「還差 N 格」；丟掉背包裡的裝備時一併刪 5D-3 的改動紀錄。API：`WorldActionRequest` 加 `LootChooseAction`、`WorldView.pending_loot`（`PendingLootView`：新拿到的列、還差幾格、說明）；事件句子（等著決定、丟掉／收下、留在原地）。前端：「最近一次戰鬥」下的最小選擇面板（`LootChoicePanel`，沿用商店列樣式與共用 `<Hint>`），裝備勾選、其他選個數，按「決定」 | `world/loot.py`、`state.py`、`economy_actions.py`、`step.py`、`api/world_economy_view.py`、`world_economy_schemas.py`、`world_schemas.py`、`world_presenter.py`、`client/src/world/LootChoicePanel.tsx`、`lootChoice.ts`、`WorldPanel.tsx`、`client/src/api/types.ts` |
| 7 | 盜賊各區都掉焦鐵（19.2.4） | `items.yaml` 加 `item_scorched_iron`（焦鐵，材料，名目價 10）；`crafting.yaml` 傾向＝護甲、格擋（`affix_cond_still_defense`、`affix_react_ranged_block`、`affix_max_hp`，沒有共鳴關鍵字）；`loot.yaml` 新增頂層 `families`（各區共用，區域的 `families` 優先），列盜賊系列 9 個單位範本 | `content/world/items.yaml`、`crafting.yaml`、`loot.yaml`、`content/world_loot.py`（`LootRules.families`、`family_material`） |

## 2. 小蓮到信賴的天數（第 1 項）

同 5B-4f 的方法（進度表照 `tests/world/test_affinity_pace.py`：骨架 2 第 2 天 DC 11、骨架 6 第 3 天 DC 13，部分成功＝差 5 內；小蓮第 2 天起每天聊；d20＋修正精確列舉；腳本在 scratchpad，不進 repo）。先用舊表重算，和 5B-4f 報告的 9.2／8.2／7.3／6.5 一致，再算本段：

| 修正 | 骨架 2／6 成功率 | 平均到信賴（本段） | 5B-4f | 第 5 天到 | 第 8 天（含）前到 |
|---|---|---|---|---|---|
| +0 | 50%／40% | **8.4 天** | 9.2 天 | 32% | 66% |
| +2 | 60%／50% | **7.4 天** | 8.2 天 | 45% | 79% |
| +4 | 70%／60% | **6.5 天** | 7.3 天 | 60% | 92% |
| +6 | 80%／70% | **5.75 天** | 6.5 天 | 76% | 99% |

- 天數分布（+0）：第 5 天 32%、第 8 天 34%、第 11 天 25%、第 15 天 9%（5B-4f：20／40／25／15%）。
- 骨架 6 部分成功現在等於成功（都 +10），所以「骨架 2 成功＋骨架 6 部分成功」也是第 5 天。
- 平均比 5B-4f 早約 0.8 天；修正 +4 以上平均落在第 6～6.5 天，+0～+2 仍是第 7.4～8.4 天（見待決 1）。
- 原有驗收（第 4～5 天第一位、第 5 天前 1～2 名、第 3 天前沒有）照舊通過。

## 3. 新欄位與相容（全部有預設值，不升版號）

| 欄位 | 預設 | 說明 |
|---|---|---|
| `PendingOffer.guaranteed` | `False` | 機遇是保底觸發的那次 |
| `EventLeftEvent.guaranteed` | `False` | 作罷的是保底觸發的那次 |
| `CharacterState.pending_loot` | `None` | 背包滿了、等戰後結算決定的戰利品 |
| `LootGainedEvent.pending_materials`／`pending_gear_names` | 空 | 放不下、等決定的 |
| 新事件 `LootChosenEvent`、`LootAbandonedEvent`；新動作 `LootChooseAction` | — | 只會出現在新日誌 |
| `LootRules.families` | 空 | 各區共用的家族材料 |

- 舊存檔、舊日誌照讀（測試鎖住 `pending_loot`、`guaranteed` 拿掉欄位照讀）。
- 同 5D-1～5D-3：舊日誌在新程式重播時格式不變、仍逐位元可重播，但內容會不同的地方有：背包滿的那場（原本不撿 → 現在進 `pending_loot`）、2 名以上精英的場次（多掉裝備）、盜賊掉焦鐵（原本掉通用料）、穿著超過招募者等級裝備的影子（原本不穿 → 現在降級照穿）、傭兵系統裝備與掉落的技能強化詞條（候選多了 8 條）。
- 掉落、降級都不耗角色亂數、不讀時間、不呼叫 LLM；`loot_choose` 不用亂數。

## 4. 代決（最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5D2b-1 | 8.21.4.1 文字裡現有 `change` 表達不了的部分 | 只用現成的 `area_delta`／`status_duration`／`damage_permille`，不改引擎：潮濕利用「雷電、冰凍傷害 +15%」→ 利用潮濕的技能傷害 +N（不限元素）；倒地製造「推倒長度 +1」→ 製造倒地的技能範圍 +1；隱蔽利用「潛行偷襲 +25%」→ 利用隱蔽的技能傷害 +N |
| 5D2b-2 | 新詞條數值與部位 | 利用方向一律照 `affix_kw_prone_damage`（60～150‰，主手／副手／項鍊／戒指）；範圍 +1 照 `affix_kw_shock_area`（不上戒指）；狀態持續 +1 照 `affix_kw_burn_duration`（中毒也算普攻，隱蔽不算） |
| 5D2b-3 | 中毒的兩條 | 8.21.4.1 的表沒有中毒，照點燃的寫法（你施加的中毒 +1 回合；利用中毒的技能傷害 +N） |
| 5D2b-4 | 降級時放不進新預算 | 先把有範圍的數值往下限縮；固定點數的詞條（例：技能強化 8 點）不能縮，所以高等級裝備壓到很低等級時詞條點數仍可能超過新預算——照「照穿、不拿掉詞條」的指示保留（測試鎖住「縮到下限仍超過」的情況） |
| 5D2b-5 | 每名精英 | 陣容 `members` 裡的精英（同之前判斷「陣容有精英」的範圍；第三方不算） |
| 5D2b-6 | 背包滿時新拿到的放哪 | 存在角色的 `pending_loot`，只留最近一場：下一場打贏、結算掉落前沒決定的「留在原地」（事件記錄）。不是可以累積的暫存區；輸掉的那場不動它 |
| 5D2b-7 | 丟完還放不下 | 拒絕動作（「背包還是放不下：還差 N 格」），不默默丟掉；想全部不要就勾新拿到的 |
| 5D2b-8 | 「焦鐵」由誰掉 | 盜賊系列全部 9 個單位範本（雲嶺陣容實際用到的是 bandit、bandit_archer、bandit_shieldbearer、bandit_captain）；區域的家族材料優先 |
| 5D2b-9 | 焦鐵的傾向 | 護甲、格擋 → `affix_cond_still_defense`（防禦）、`affix_react_ranged_block`（格擋）、`affix_max_hp`；19.2.4 沒有共鳴關鍵字，不給 |

## 5. 待 PM 決定

1. **小蓮平均到信賴**：修正 +4 以上約第 6～6.5 天，+0～+2 仍第 7.4～8.4 天。要再提前可再動 content（例：骨架 2 成功 +20 → +25）。
2. **8.21.4.1 的精確效果**（元素篩選、推倒長度、潛行偷襲、隱蔽中第一次攻擊暴擊）要引擎新的 `change` 種類；目前是最接近的現成效果。
3. **帶電只有製造 1 條**（`affix_kw_shock_area`）：8.21.4.1 的利用方向（對帶電目標暴擊範圍 +1 等）還沒有詞條；任務只要求潮濕、隱蔽與荒原三個，沒補。其他關鍵字（冰凍、撞擊、標記、高處）也還沒有技能強化詞條。
4. **新詞條沒跑模擬**（守則：不跑大型模擬）；數值照現有同類詞條。
5. **降級裝備可能超過新等級預算**（代決 5D2b-4）：要不要在降級時改成「放不下的固定點數詞條換成基礎加成」或其他規則。
6. **pending_loot 的保留期限**（代決 5D2b-6）：目前留到下一場打贏；要不要改成「離開地點就留在原地」或「不限期」。
7. 前端選擇面板是最小版（5D-4 背包畫面時一起整理）；沒做瀏覽器實測，vitest 有純函式與靜態輸出測試，API 測試走完「背包滿 → 拒絕（還差幾格）→ 丟掉 → 清空」。
8. 開發中有一次 `tests/api/test_world_economy_api.py::test_fight_buy_and_pouch` 在 `-n 8` 全組時失敗（打 4 場都沒贏、或拿到的金幣不是 30），單獨重跑 4 次、`tests/api -n 8` 重跑都通過；看起來是既有的「效用 AI 代打不保證贏」不穩定，沒有改測試。

## 6. 測試

| 檔案 | 內容 |
|---|---|
| `tests/world/test_affinity_pace.py`（加） | 骨架 6 partial +10、沒有 failure 列 |
| `tests/world/test_opportunity.py`（加） | 保底機遇的待選三選一與作罷事件記下保底；一般觸發不記；舊資料照讀 |
| `tests/api/test_opportunity_offer_view.py`、`test_world_story.py`（加） | 保底三選一標題、「作罷」句子用「焦痕未冷的古松」，一般照舊 |
| `tests/content/test_equipment_content.py`、`tests/api/test_gear_api.py`（改） | 詞條 69 → 77 |
| `tests/content/test_world_loot.py`（加） | 偏向關鍵字檢查（`hidden` 報錯）；盜賊各區掉焦鐵、區域優先、焦鐵傾向 |
| `tests/world/test_loot.py`（加、改） | 雲嶺三個關鍵字都會出現；點燃／倒地／中毒／潮濕／隱蔽各有製造與利用；每名精英 1 件；背包滿 → `pending_loot`；`loot_choose` 丟舊的、丟新的、放不下拒絕、穿戴中不能丟、下一場打贏留在原地、舊存檔照讀 |
| `tests/world/test_gear.py`（改、加） | 影子超過等級的照穿；`downscale_item` 不超過原數值、放進新預算（或已在下限） |
| `tests/api/test_world_loot_api.py`（加） | 背包 1 格的內容庫：打贏 → `pending_loot` → 空的 `loot_choose` 被拒 → 丟掉新拿到的 → 清空 |
| `client/src/world/lootChoice.test.ts`（新） | 動作組裝（個數上限、兩邊都可丟）、面板靜態輸出 |

## 7. 檢查（最後一次合併 main〔含 5E-3〕之後）

- `ruff check .`、`ruff format --check .`、`mypy`（1149 檔）、`lint-imports`（11 kept）通過。
- `tests/world tests/api tests/content -n 8`：3023 通過、1 失敗（待決 8 的不穩定測試；單獨重跑通過）；`tests/api -n 8` 重跑 483 通過。
- `tests/engine tests/skillgen -k "gear or affix or keyword or item or equip or loot or resonance"`：527 通過；`tests/roguelite tests/test_architecture.py`：236 通過。
- vitest 134 檔 1251 通過；`npm run build`（`tsc --noEmit` ＋ vite）通過。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- OpenAPI 重產（`scripts/export_openapi.py` → `pnpm gen:api`）；合併 main 後再產一次沒有差異。
- 沒有新增 `# noqa`；沒跑全量與大型模擬。
