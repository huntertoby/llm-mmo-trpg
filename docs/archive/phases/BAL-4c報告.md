# BAL-4c 完成報告｜BAL-4b 與 BAL-5 合併、4 個技術修正、合併後複測

分支：`worktree-agent-a68fd72beb21b46cb`（`main`〔含 BAL-5〕快轉後 `--no-ff` 合併 BAL-4b 分支
`worktree-agent-ab7d775f430ba79df`）。

## 1. 交付

| 項目 | 做法 | 位置 |
|---|---|---|
| 0. 合併與衝突 | 4 個衝突檔（`test_skill_fuzz`、`test_reaction_events_3d3`、`test_status_determinism`、CLI 快照）先取 main 側，再在合併後版本（含下面 1～4 的修改）實測：只有 `test_reaction_events_3d3` 的 build_ranged 需要重挑（dark_forest 種子 1 → 4）。另外 `test_run_cli` 大變化測試種子 7 → 13（種子 4～15 只有 13 同時出現第 3 次閃現、完整技能三選一與重閃）。斷言都沒改，註解標 BAL-4c。`test_skill_fuzz`（種子 0）、`test_status_determinism`（9, 10）在合併後仍成立，沿用 main 側。CLI 快照用 `UPDATE_CLI_SNAPSHOTS=1` 重產：7 個戰鬥輸出雜湊改變（敵方數值 ＋ AI 一起改變了戰鬥過程），`skills list／show` 不變。 | `tests/…` |
| 1. 同歸於盡算合法完成 | `BattleMetrics.mutual_wipe`（`draw` 且結束原因 `eliminate`；不進序列化）；批次報表的 `draw` 異常對這種場次加說明「同歸於盡」；`run_completion` 把它從異常移到 `CompletionReport.mutual_wipes`，報表另列一行「同歸於盡（…合法結束、不算異常）N 場」。輪數上限的 draw 仍算異常。 | `sim/metrics.py`、`sim/batch.py`、`sim/completion.py`；測試 `tests/sim/test_completion_mutual_wipe.py`（4） |
| 2. 傷害預覽乘敵方倍率 | 查證後**不需改程式**：`preview` 是在狀態複本上實際結算（最少／最多兩組骰值），`DamageDealt.multiplier_permille` 已含 `_difficulty_permille`，期望值也用事件上的倍率。BAL-4b 報告「預覽不乘」的推論不成立。加行為一致測試釘住：普攻與敵方施放技能，三種敵人（一般／Boss／護衛，倍率各設不同值）預覽最少／最多／期望 ＝ 實際結算、只受自己那一種倍率影響。 | `tests/engine/test_preview_difficulty_bal4c.py`（9） |
| 3. 法力折扣依施放者陣營 | 拿掉 `apply_ally_mana_cost`／`scale_mana_cost`（規則包與 `with_skills` 不再縮放，技能資料一律原始費用）。新增 `CoreRules.ally_mana(mana)` 與引擎的 `skill_mana_cost(core, unit, skill)`：我方單位（含我方召喚物）打折、其他陣營原價。用在扣費（`pay_skill_cost` 改收 `core`，`PaidCost.mana`；施放、灌注、被動觸發的事件 `mana` 都是實付）、施放檢查（`resource_problem`）、反應詢問（`Pending.mana_cost`）、反應規則顯示（`view._rule_view`）、AI 估價（`skill_cost`、`_has_usable_spell`）。模擬旋鈕 `mana_cost` 改為只乘 `ally_mana_cost_permille`（一次四捨五入）。 | `content/rules.py`、`content/library.py`、`engine/skills/targeting.py` 等；測試 `tests/engine/test_ally_mana_cost_bal4c.py`（6） |
| 4. 玩家看到的費用 | `skill_card(..., ally=True)`（預設；卡片給玩家看）代價列顯示打折後法力；`cost_parts(..., ally=False)` 預設原價，所以 CLI `skills list／show`（內容瀏覽）與預算、閃現、組合器、`content check` 仍是原始費用。戰鬥中的卡片（`hero_cards`）依單位陣營。工坊 `WorkshopCheck` 新增 `battle_mana`（我方實付），前端 `skillMana` 優先用它（法力上限提醒）；送去試玩的 `skill.cost.mana` 仍是原始值。已重產 `openapi.json`、`schema.d.ts`；前端夾具重產無變化。 | `narrative/skills.py`、`api/hero_cards.py`、`api/routes/workshop.py`、`api/workshop_schemas.py`、`client/src/workshop/tryout.ts`；測試 `tests/api/test_ally_mana_display_bal4c.py`（5）、vitest 1 例 |
| 一輪掃描的資料入口 | 新增 `RunRules.heal_after_battle_permille`（預設 0 ＝ 行為不變，`roguelite.yaml` 沒寫）：打贏一般戰後回復最大生命的千分比。只供掃描，是否採用由 PM 決定。 | `content/roguelite.py`、`roguelite/progress.py`；測試 `tests/roguelite/test_heal_after_battle_bal4c.py`（2） |
| 5. 複測 | `docs/phases/BAL-4/retest2.md`（含玩法 PM 追加的一輪掃描與 open_plain 分析）。 | — |

### 測試調整（沒有為了過測試改規則）
- 機制測試裡我方施放者付的法力改用 `tests.engine.helpers.ally_mana(raw)` 計算（content 倍率 800‰）：`test_dual_resources`、`test_passive_triggers`、`test_reaction_skills`、`test_skill_primitives`、`test_skill_scenarios`、`test_skill_infusion`、`test_skill_ai_scenarios`。
- BAL-4b 為「規則包內費用已縮放」改的測試還原成 main 版本（`test_flash`、`test_flash_major`、`test_flash_templates`、`test_skill_tier_3w9`、`test_skills_content`）；`test_difficulty` 改測新語意。

## 2. 複測摘要（詳見 retest2.md）

| 目標 | BAL-4b | 合併後 |
|---|---|---|
| 一般戰勝率 35–65% | 57.0% | 56.0% ✓ |
| 一般戰輪數 4–6 | 4.5 | 4.5 ✓ |
| 各圖在 35–65% | 6／10 | 5／10（oil_depot 35 → 30） |
| Boss 召喚包勝率 35–65% | 33.3% | 31.7% ⚠ |
| Boss 召喚包輪數 6–10 | 9.2 | 9.2 ✓ |
| 短缺：召喚師 ≤ 20% | 15.0% | 19.3% ✓ |
| 短缺：火焰流（記錄） | 28.9% | 27.9% |
| Boss 無召喚（記錄） | 18.3%／7.9 | 18.3%／8.0 |
| 一輪勝率 30–50% | 8.3% | 6.7% ✗ |
| 一輪平均贏幾場 | 2.98 | 2.92 |
| 一輪打到 Boss 的輪數 | 10 | 9 |

一輪掃描（60 輪，只在模擬覆寫）：戰後回 10／20／30% 生命 → 8.3／8.3／10.0%；第 1、2 場少一隻 → 10.0%
（平均贏 3.43 場、打到 Boss 15 輪）。都遠低於 30%。診斷：輸場集中在第 3 場（24／56，敵人變 4 名）與
守點戰（19／56）。open_plain 偏難主因是頭目 ＋ 掩體最少（換掉頭目 85%、補 4 個木箱 60%）。

## 3. 驗收

- ruff check、ruff format --check（src、tests、scripts）、mypy（364 檔）、lint-imports（7 契約）：通過。
- pytest（`-m "(slow or not slow) and not llm"`）：`tests/engine`＋`content` 5413（先有 9 個因法力折扣與 1 個種子失敗，修正後重跑通過）、`sim`＋`roguelite`＋`skillgen`＋`api` 4503 passed、`roguelite`＋`content`＋架構 1753 passed（加了戰後回復欄位後重跑）、`tests/cli` 155 passed（快照重產 1 ＋ 種子 1 修正後重跑通過）。
- **`tests/sim/test_completion.py` 全部通過**（含全圖 270 場：合併後沒有 draw，oil_depot／protect_weakest／種子 0 不再同歸於盡）。
- vitest：120 檔 1176 通過。
- swamp 種子 7 重播：通過（61 個動作、219 個事件）。
- 沒有跑 `scripts/check.py`。

## 4. 戰鬥紀錄格式

紀錄結構沒變（事件欄位相同；`SkillUsed.mana` 等語意從「規則包內的費用」改成「實付費用」，數值相同）。
規則包內容變了（技能回到原始費用），BAL-4b 版本的紀錄重播時 `ruleset_hash` 不符會被拒絕並說明，依
`戰鬥紀錄格式變更.md` 1.2 不遞增 `LOG_FORMAT`（仍 /90）。

## 5. 待 PM 決定

1. **一輪勝率 6.7%，掃描的兩個選項都不夠**（最多 10%）。建議下一步查守點戰（`alt_objectives.defend` 的輪數／格子；占輸場 34%）與第 3 場 4 名敵人的陣容，而不是再調戰間回復。`heal_after_battle_permille` 欄位已加（預設 0），要不要用由 PM 決定。
2. **open_plain**：是地圖本身的問題（頭目 ＋ 4 個物件）。可選：換掉預設陣容的頭目、或補掩體（模擬各 85%／60%）。只影響示範地圖指標，一輪不用預設陣容。oil_depot 也掉到 30%（同樣帶頭目）。
3. **Boss 召喚包 31.7%**（差 3.3 點，n=60）：BAL-4b 待決 #4 延續。
4. **`/api/skills/{id}` 一律顯示我方折扣**：這個端點沒有陣營資訊，戰鬥中檢視敵方單位的技能卡（若走此端點）會看到打折後費用。目前敵方陣容的技能都不花法力，實際上沒有差異；要精確可加 `team` 查詢參數。
5. 姿態維持費（法力）與化形維持費不打折（不是技能代價，沿用原樣）。是否也要套用請決定。
