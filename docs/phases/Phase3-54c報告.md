# Phase 3-54c 報告｜種子技能：風、毒、神聖（玩法決定 #56、#59、#63、#64，06 6.33）

> 規格：`docs/phases/Phase3計畫.md` 第 66 節。大地 4 招、大地判定、工坊技能元素、3-55 預覽武器屬於 3-54d，本段沒有碰。

## 做了什麼

### 1. 新原語 `clear_surface`（清除表面）

| 項目 | 實作 |
|---|---|
| 行為 | 影響格上屬於指定種類的表面直接變成沒有表面（`engine/effects/blow.py` 的 `_clear_surface`，效果模型 `ClearSurfaceEffect`）。**不帶元素、不查互動表、不觸及物件、不觸發風的擴散**（`wind.py` 的擴散只掛在風元素傷害效果上，本原語不經過）。 |
| 參數 | `surface`（選填）：清哪一種；省略 ＝ `rules/core.yaml` 的 `clear_surfaces`（`[smoke, poison]`）。對象沿用通用的 `affects`：`allies` ＝ 只清有友方（含施放者）站著的格子，`tiles` ＝ 整個範圍（地形類原語預設）。 |
| 事件 | 沿用 `surface_changed`（原因 `clear`），沒有新事件，**`LOG_FORMAT` 不遞增（仍 `/77`）**。戰鬥紀錄文字：「(x,y) 的毒被清除了」。 |
| 預算（初值，平衡 B25） | `skill_primitives.yaml`：`budget_basis: fixed`、`base_points: 3`，形狀與對象倍率照一般效果。 |
| 驗證／工坊／LLM | `min_rarity: rare`、`active_only`、`acts_on: tile`；骨架：控場核心、範圍附帶；工坊玩家說明 `原語.clear_surface`（`workshop_text.yaml`，155 條；實作者初稿，待玩法 PM 改寫）；LLM 提議模型由 `skill_primitives.yaml` 自動產生。 |
| 組合器 | **不抽**：列入 `_HAND_WRITTEN_PRIMITIVES`（只給手寫技能，既有種子不變）。 |
| 卡片 | 「清除範圍內的表面（煙霧、毒），不帶元素、不引發其他反應」（`narrative/skills.py::_clear_surface`）。 |
| 其他 | AI 估值與預覽登錄（`coverage.py`、`preview.py`）；技能圖示部件 `clear_surface`（表面＋劃掉的斜線，`skillParts.ts`）；`glossary.json`、`skill_icons.json` 重產。 |
| 縮放屬性規則 | `skill_scaling.yaml`：`blow_surface` 列入元素主題（智力）的效果訊號、`clear_surface` 列入輔助主題（感知）的效果訊號。否則純吹送／純清除的法術沒有主題訊號、會被判成身體類。 |

### 2. 14 招種子技能（`content/skills/`，數值為初值、未經模擬）

比例＝total ÷ 可用預算，全部在 70～100%（`trpg skills budget --all`，違規 0）。

| 元素 | 技能（id） | 階 | 稀有 | 形狀／機制 | 比例 |
|---|---|---|---|---|---|
| 風 | 風刃 `skill_wind_blade` | 1 | 普通 | 直線 4：風 2d6 | 74.4% |
| 風 | 氣爆 `skill_air_burst` | 1 | 稀有 | 環形 1：風 1d8＋推 1（風壓撞擊） | 87.6% |
| 風 | 吹送 `skill_gust_blow` | 1 | 稀有 | 錐形 4：吹送 3 格 | 80.1% |
| 風 | 暴風 `skill_tempest` | 2 | 稀有 | 3x3 射程 4：風 2d6、擴散 2 格 | 74.8% |
| 風 | 颶風推 `skill_hurricane_push` | 2 | 稀有 | 直線 3：風 1d6＋推 2、撞擊 2d6（風壓） | 75.5% |
| 風 | 清風 `skill_clearing_breeze` | 1 | 稀有 | 3x3 射程 4：`clear_surface`、對象友方（煙霧與毒） | 76.5% |
| 毒 | 毒刃 `skill_venom_blade` | 1 | 普通 | 近戰武器：毒素 65%＋中毒（製造） | 96.7% |
| 毒 | 毒霧彈 `skill_poison_mist` | 1 | 稀有 | 3x3 射程 4：毒表面 3 回合（製造） | 76.5% |
| 毒 | 蝕骨刺 `skill_marrow_thorn` | 1 | 稀有 | 近戰武器：100%，目標中毒再 ＋100% 毒素（利用） | 82.6% |
| 毒 | 劇毒引爆 `skill_venom_detonation` | 2 | 稀有 | 單體射程 5：消耗中毒、剩餘回合 × 2d10 毒素（利用） | 79.1% |
| 毒 | 腐蝕 `skill_corrosion` | 2 | 稀有 | 單體射程 5：中毒 4 回合＋易傷 3 回合＋毒素 1d8（製造） | 82.1% |
| 毒 | 毒池陷阱 `skill_venom_pit` | 2 | 稀有 | 陷阱（踩到觸發、十字）：毒素 1d6＋毒表面 4 回合（製造） | 91.2% |
| 神聖 | 破邪聖光 `skill_purging_light` | 1 | 稀有 | 十字射程 4：神聖 2d6；互動表清毒與黑暗表面 | 79.6% |
| 神聖 | 聖光印地 `skill_holy_ground` | 1 | 稀有 | 指定格射程 4：聖光表面 5 回合 | 85.0% |

- 風 6 招用 3-54a／b 的吹送、元素擴散（暴風填 `spread: 2`）、風壓撞擊（氣爆、颶風推的推擊）。
- 毒的主動利用者共 3 招（既有毒血迸發＋蝕骨刺＋劇毒引爆）；1 階起始技能：毒刃、毒霧彈、蝕骨刺（加荊棘牆）。
- 破邪聖光不寫清除效果：神聖傷害本身觸及十字內每一格（含沒有單位的格子），互動表清毒與黑暗（`holy_purifies_poison`、`holy_dispels_darkness`）。

### 3. 中毒開局

刪除 `skill_keywords.yaml` 中 `poisoned` 的 `start_hidden`；拿掉 3-53 的保守標記：`EXTRA_KEYWORDS`／`EXTRA_NAMES` 併入 `KEYWORDS`／`NAMES`，並補中毒的正面範例；`test_pools_24c.py` 改 `short == {}`；`test_keyword_start.py` 起始技能池改成和其他池一樣 ≥ 3；`test_run_start_api.py` 的開局選單包含中毒。

## 驗收對照

| 驗收條件 | 證明 |
|---|---|
| 清除表面 × 表面種類 × 對象 | `tests/engine/test_seeds_54c.py::test_clear_surface_by_kind_and_target`（8 種表面 × 友方腳下／全部 × 省略種類／指定種類），`test_clear_surface_only_clears_the_named_kind`、`..._does_nothing_outside_the_area` |
| 清風不觸發擴散、不觸發互動表 | `test_clear_surface_touches_nothing_else`（清火焰不引爆油桶、不傷單位、無傷害與物件事件）、`test_clearing_breeze_is_not_a_wind_skill_and_never_spreads`、`..._under_allies_only` |
| 破邪聖光清掉毒與黑暗 | `test_purging_light_purifies_poison_and_darkness_on_the_cross` |
| 每招卡片數字＝實戰 | `test_card_numbers_match_the_skill_data`（14 招，骰子、距離、持續回合、倍率）、`test_wind_seeds_use_the_3_54ab_mechanics_on_the_card`、`test_holy_ground_leaves_a_holy_surface`（持續回合含智力加成）、`test_tempest_spreads...`、`test_gust_blow_moves_the_poison_three_tiles_downwind` |
| 一場用到清風與吹送的重播 | `test_a_battle_with_clearing_breeze_and_gust_blow_replays_identically`（四個單位各先清風再吹送，初始狀態＋步驟列表重播的最終狀態相同） |
| 中毒池與其他 10 池一致 | `test_every_keyword_pool_has_at_least_three_active_exploiters`、`test_starter_pools_use_exclusive_rules_and_have_three_each`、`test_keywords.py` 全部 |
| 預算 70～100% | `trpg skills budget --all`：282 個技能通過、違規 0 |
| pytest | engine＋架構 3400 passed；content、skillgen、narrative、roguelite、llm、api、sim、shared 4405 passed（修正 2 項失敗後重跑相關檔通過）；`-m "slow or not slow" tests/cli --timeout=3000`：更新快照後全數通過 |
| vitest／build | vitest 104 檔 994 passed；`pnpm build` 成功 |
| ruff／format／mypy／lint-imports | 全部通過（mypy 725 檔；lint-imports 7 kept） |

## 影響盤點

- **`LOG_FORMAT` 沒有遞增（`/77`）**：沒有新事件。3-54d 若遞增請 PM 留意合併。
- CLI 快照更新：`cli_output_hashes.json`（技能清單 268 → 282）、`llm_propose_mock.txt`（技能數與隨機組合器種子變化）；`test_budget_cli.py` 的 268 → 282。
- OpenAPI：重新匯出，沒有差異。
- `skill_icons.json`、`glossary.json` 重產。
- 技能數 268 → 282：`test_skill_scaling.py` 的計數改 282（**3-54d 也會改這個數字，合併時請加總**）。

## 複雜度類 noqa

本段沒有新增 C901、PLR0911、PLR0912、PLR0915 的 noqa。

## 待 PM 決定

1. **清除表面只做單一種類或預設組合，沒有做「任意清單」參數**：規格寫「要清的表面清單」，但清單型參數會牽動工坊欄位（沒有多選控制項）、LLM 提議模型與驗證器。現在是 `surface` 選填（單一種類），省略時清 `core.clear_surfaces`（煙霧、毒）；清風就是用省略。要任意清單需另開工坊／提議的清單欄位。
2. **名稱衝突**：既有 `skill_venom_cloud` 的名稱就是「毒霧」（2 階，中毒＋易傷）。為了不改既有技能，新的 1 階毒表面技能命名為「毒霧彈」（`skill_poison_mist`）。要不要改名（例如把舊的改成「毒雲」）請決定。
3. **預算初值**：清除表面 3 點（× 形狀、對象倍率）；14 招的骰子、冷卻、法力都是初值，沒有模擬，平衡 B25 再調。清風 76.5% 是靠「清除表面 3 點」撐到及格線以上的。
4. **稀有度**：因原語／形狀／條件門檻，氣爆（推）、吹送、清風、毒霧彈、蝕骨刺（條件）、破邪聖光（十字）、聖光印地（指定格）等都是稀有；普通階只有風刃、毒刃。
5. **種子技能沒有放進任何 build、單位或獎勵池**：風與神聖的種子技能目前只由 `tests/content/test_coverage.py::_SEEDS_54C` 列為「已裝備」，玩家實際取得的途徑（獎勵、技能書）規格沒寫；毒的 6 招透過中毒關鍵字池給出。
6. **颶風推推擊距離 2**：規格範例「吹送 2～3 格」是表面，推擊上限是 2 格（`_MAX_DISPLACE`），所以颶風推推 2 格＋撞擊骰 2d6（吃風壓 +50%）。
7. **提議子集 token 緊預算**：控場骨架多了 `clear_surface` 後，核心結構約 1530 token，`test_proposal_subset.py` 的「緊預算」測試由 1_500 放寬到 1_600；正式預設預算沒動。3-54d 若再增加控場核心原語可能要再留意。
8. **中毒關鍵字嫁接**（`skill_evolution.yaml` 的 `grafts`）、毒元素普攻對應中毒外觀：3-53 留下的兩點，本段仍沒有做。
9. **工坊玩家說明** `原語.clear_surface` 是實作者初稿，請玩法 PM 改寫。
10. 中毒現在會出現在開局選單：1 階起始技能池為毒刃、毒霧彈、蝕骨刺、荊棘牆（荊棘牆需要法器類武器）。
