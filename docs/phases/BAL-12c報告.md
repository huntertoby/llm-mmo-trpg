# BAL-12c 報告：套用 BAL-12b

依 `docs/phases/PhaseBAL計畫.md` 第 7 節「BAL-12c」；設計 06 6.34.4／6.34.6「BAL-12b 定」。數值都在 content。

## 做了什麼
1. **完整技能**（`complete.stop_over_permille: 200`、`complete.modifier_step: 5`，`trpg.skillgen.complete`）：都不行、要超過上限時，若會超過 +200‰，改回「只走上限內的步子」停下的版本（+120‰ 以下最接近的一階）；修正型被動的修正幅度在完整技能用每 5‰ 一格（升階重配、閃現不動）。
2. **輕巧在 AP 1**（`cost_light.cost_fields: [cooldown, mana, stamina]`，`flash_ops._op_light`）：AP 已是 1 時，依序各出一份「冷卻／法力／耐力 −1」的草稿，每項最少留 1，威力照樣由預算器降低。AP > 1 的行為不變。
3. **延長與範圍放寬**（`rules.extend_effects`、`extend_trap`、`area_trap_shapes`、`area_tile_shapes`）：
   - 延長：原本的狀態、表面、區域延長不了時，改延長召喚物存活、障礙、刻印回合（+1）；陷阱只限觸發型（enter）加 `rounds` +1。
   - 範圍 +1：陷阱改觸發範圍（single → cross → square3）；沒有大小參數的地面格換成十字（射程夾在新形狀範圍內）。
4. **觸發效果 +1 固定值**：新參數 `flat_bonus`（`damage` 只限法術技、`heal`、`shield`；schema 1～10）。引擎把它加進骰值（暴擊不加倍），預算算成骰子平均 + n，卡片文字「1d6＋1＋…」，工坊說明 3 筆初稿。閃現的被動、反應「效果 +」（`trigger_potency`）一般重調失敗後，才加 `flat_bonus` 旋鈕（無／+1，`rules.trigger_flat_bonus: 1`）再試一次。
5. 沒做：`trigger_cooldown_trade`、`rule_param_plus`、B-3W-4。

## 行為快照（`refactor_3wr2.json` 重產）
`EffectSpec` 多了 `flat_bonus` 欄位，所有技能 JSON 多一個 `"flat_bonus":null`，所以摘要字串全部重算（檔案 689 行變動）。扣掉這個欄位後的真正變動：
- **完整技能 28／301**（同 BAL-12b 預期）：attack_mastery、blink、bloodlust、counterspell、creeping_blight、dread_gaze、ember_brand、ember_ward、fleet_foot、form_renewal、fracture_mark、holy_water、ice_wall、mark_detonation、poison_mist、reflex_ward、rending_strike、riposte、rune_resonance、rune_sight、searing_scar、seething_rage、thorn_wall、twin_strike、vanish、vault_leap、war_avatar、wind_blade。
- **升階重配 0／301**。
- **閃現出題 38／129**：第 2 項（輕巧 AP 1）後 36 筆，第 3、4 項再加 2 筆。涉及 afterimage_vow、arc_follow_up、blade_dance、blood_sacrifice、clearing_breeze、form_renewal、gear_shield_wall、hex_bolt、hunters_strike、mark_prey、pick_off、rallying_cry、resurrection、rune_ward、summon_earth_wall、summon_plateau_totem、summon_vine、time_bomb_rune。

## 重掃
- **覆蓋**（`flash_minor_coverage.py --jobs 4`，同 BAL-10c 參數；`docs/phases/BAL-12/minor_coverage_bal12c.*`）：不足名單 **230 → 183**（脫離 47 列，全部是主動技；沒有新進）。
- **`bal12b_measure.py`**（`12c_overcap.md`、`12c_minor.md`、`12c_duration.md`）：
  - 完整技能超過 +150‰ 的 50 → 23 招、最大 +200‰，跟 BAL-12b 的 `mod5_stop200` 一樣。
  - 第 2 次 < 2 的分組（BAL-12b → 12c）：召喚 26 → 11、工具技 65 → 35、地面格 5 → 3、常駐 12 → 10、陷阱 1 → 1、**被動與反應 45 → 45**。
  - 升階持續：點數固定白板 3 階做成完整技能，加不到 +120‰ 的 48 → 52／52（停下規則讓追蹤印痕從 +250‰ 停到 0～9‰）。

**被動與反應沒有救到**：+1 固定值在小骰子上和骰子一階差不多（1d4＋1 ＝ 1d6 平均），跳不出原本的「階梯跳過窗」。內建被動、反應 × 角色階級 × 種子 1～3 的探測裡，只多 3 次合法（穩息 3 階），也沒有讓任何原本合法的變成不合法（有測試）。

## 待 PM 決定
1. 【原型數值】`trigger_fine` 只多 3 次合法、不足列 0 救回。要再細（例如固定值改成千分比 +5%，或只用在 2d 以上的骰子），或接受。
2. 【解讀】延長放寬只在原本的狀態／表面／區域延長不了時才用（保守，舊結果不變）；陷阱持續只限觸發型，延遲型的 rounds 是引爆前的等待，不加。
3. 【解讀】`flat_bonus` 同時開給治療、護盾（內建被動的觸發效果多是治療，只開傷害的話幾乎沒有對象）。傷害只限法術技，武器技照舊用倍率。
4. 【解讀】範圍 +1 用在地面格時直接換成十字，效果不允許十字時（例如衝撞）由驗證器擋掉、不出。
5. 【技術】工坊說明 `原語.{damage,heal,shield}.flat_bonus` 三筆是實作者初稿，待玩法 PM 改寫。

## 測試
- 新測試 `tests/skillgen/test_flash_bal12c.py`（22 個）：完整技能停下／小幅超過照收／規則省略回舊行為／修正細階梯；輕巧 AP 1 減一項、最少留 1、沒得減不出、拿得到合法選項；延長召喚、障礙、刻印、陷阱（只限 enter）、原本路徑不變；陷阱與地面格的範圍；細旋鈕的對象、預算與卡片文字、武器技不可填、穩息 3 階救回、原本合法的不變。
- 調整既有測試：`test_complete_3w5b.py`（嗜血、還擊、反咒改成停下，換成 `skill_second_wind`、`skill_grief_rage`、`skill_covering_fire`；「超過 150 只能是到不了 120」的淬火烙印改成 `skill_cluster_bolt`）、`test_flash.py::test_area_plus_grows_size_or_radius`（地面格換十字另測，跳過）、`test_workshop_text_48f.py`（166 → 169 筆）。
- 重產 `client/src/render/fixtures/skill_icons.json`（技能 JSON 多了 `flat_bonus`）。

## 驗證
- ruff check、ruff format --check、mypy（912 檔）、lint-imports（7 kept）通過。
- pytest：tests/skillgen＋content＋narrative＋llm＋roguelite＋architecture（修正前 3 個失敗，見上；修正後重跑相關檔通過）；tests/engine＋閃現／完整技能檔 4,711 passed；tests/api 的 client fixture、openapi 快照通過。
- 重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 驗證通過（76 個動作、250 個事件）。
- 沒動 `src/trpg/sim/`、`scripts/balance_baseline.py`。
