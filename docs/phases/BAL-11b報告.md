# BAL-11b 報告：預算旋鈕套用

依 `docs/phases/PhaseBAL計畫.md` 最末段「BAL-11b」；設計 `docs/design/06-技能.md` 6.34.4「BAL-11a 定」。量測依據 `docs/phases/BAL-11a報告.md`。

## 做了什麼
1. **第二關鍵字草稿修正**（`trpg.skillgen.flash_ops._keyword_op`，只影響小變化的 `keyword_imbue`／`keyword_exploit`／`support_keyword`；大變化的橋接不動）：
   - 技能裡有「必須是唯一的效果」或「其他效果只能作用在施放者」的原語（`skill_primitives.yaml` 的組合規則 `sole_effect`／`others_affect`：召喚、復活、規則改變、持續區域、複製、交換……）時不出這類模板（`_graft_blocked`）。
   - 法術技嫁接的傷害補上元素（這招的傷害元素 → 技能元素 → 物理）與骰子（最小一格，由預算器重調）（`_spell_graft_damage`）。
2. **姿態冷卻折抵**：`content/skill_budget.yaml` 的 `allowance.stance_cooldown_per_turn: 10`、`stance_cooldown_cap: 50`（`CostAllowance.cooldown_allowance(…, stance=)`；省略時同主動技）。只影響 `kind: stance`。
3. **細階梯只用在閃現**（`content/flash_templates.yaml` 的 rules）：
   - `modifier_potency_step: 10`：閃現「強效」（`mod_potency`）的修正傷害／治療階梯 10～1000 每 10（原 50～1000 每 25）；升階重配、完整技能照舊（op 不是 `mod_potency`）。
   - `followup_multiplier_step: 25`：接續段強化類（`followup_potency`／`_area`／`_range`／`_element`）的接續段武器倍率 3000‰ 以下每 25（與原階梯合併）；追擊 `followup`、升階重配、完整技能照舊。
   - 形態幅度不改。兩個欄位省略時回到舊階梯。
4. 沒做（BAL-11a 定）：小變化冷卻折抵、觸發細骰子、強度下限放寬。
5. 新測試 `tests/skillgen/test_flash_bal11b.py`（6 個）：自身／唯一原語不出第二關鍵字、法術嫁接傷害有骰子與元素且 schema 合法、姿態冷卻折抵 10／回合上限 50（主動技不變）、強效細階梯只在閃現、接續段細階梯（省略欄位回原階梯）。
6. `LOG_FORMAT`、存檔版本不用升（沒有改存檔欄位；已存歷程照新內容重推，同歷來的內容改版）。

## 行為快照（`tests/skillgen/fixtures/refactor_3wr2.json` 重產）
**完整技能 0／301、升階重配 0／301 不變**；閃現出題 9／129 變：
- `skill_attack_mastery@3@1／@11@1／@5@2`（強效細階梯）
- `skill_shadow_whirl@3@1／@11@1／@5@2`（接續段細階梯）
- `skill_clearing_breeze@5@2`、`skill_ember_brand@5@2`、`skill_telekinetic_hurl@5@2`（第二關鍵字草稿修正後多出／換了選項）

## 重掃
**覆蓋**（`flash_minor_coverage.py --jobs 8`，同 BAL-10c 參數；`docs/phases/BAL-11/minor_coverage_bal11b.*`）：不足名單 **247 → 230**（脫離 18、新進 1）。
- 脫離：法術技第二關鍵字修正後的 3 階主動技（`skill_detonate_burning`、`skill_quicken_tide`、`skill_rallying_cry`、`skill_soul_bond`、`skill_toxin_burst`、`skill_undying_oath` 等原本 0／0），被動 `skill_rune_snare`、`skill_seething_rage`、白板 `skill_rand_5`（1、2 階），細階梯的 `skill_leap_slam@2`、`skill_rune_resonance@2`、`skill_searing_scar@2`。
- 新進：`skill_lucky_break`（被動 3 階）第 2 次 2 → 1——第 1 次多了第二關鍵字選項，選它的分支第 2 次只剩 1 個（新分支造成的最小值下降，原分支沒變差）。

**重調失敗**（`budget_knob_audit.py retune`；`docs/phases/BAL-11/retune_bal11b.md`）：以「一次請求 × 一個模板」計 **6,760 → 5,511**；草稿 schema 不合法 2,804 → 312。修正後原本被 schema 擋下的草稿進了調整器，一部分轉成「超過上限」（1,737 → 2,377）與「骨架占比」（673 → 1,191）；合法 18,026 → 18,918、結構不符 6,746 → 7,794（自身／唯一原語改成不出）。剩下的 312 是 `gamble`（必須最後）、複合技效果上限、位移段、拉扯段等，照規格不處理。

**姿態**（`docs/phases/BAL-11/stance_bal11b.md`）：BAL-11a 那條（白板 `skill_rand_3` 橋接帶冷卻 2）不再出現；冷卻 +1 換到的幅度 50‰ → 0（一格都換不到）。

## 待 PM 決定
1. 【解讀】法術技嫁接傷害沒有任何元素可沿用時用物理。目前內建都有元素可沿用，物理只是保底。
2. 【解讀】「必須是最後一個效果」（`gamble`）沒算在「唯一／只作用自身」裡，第二關鍵字仍會試、仍會失敗（56 次）；要一起不出的話在 `_graft_blocked` 加 `position` 即可。
3. 【觀察】草稿修好後多出的「超過上限」「骨架占比」（共約 1,150 次）是 BAL-11a 定 1 決定不救的那類（不拿冷卻折抵），照現狀不出。

## 測試調整
- `tests/skillgen/test_flash_bal10b.py` 的「有進入冷卻的熊形態」夾具：幅度 1400 → 1300。姿態冷卻折抵變小後（冷卻 2 回合 100‰ → 20‰），1400 放不進預算；斷言不改。

## 驗證
- ruff check、ruff format --check、mypy（910 檔）、lint-imports（7 kept）通過。
- pytest（`-m "not llm" -n 6`）：tests/skillgen＋tests/llm＋tests/content＋test_architecture 5,853 passed（夾具修正前 2 failed，修正後該兩檔 54 passed）；tests/roguelite 224 passed。
- 重播：`trpg battle --map swamp --seed 7` → replay 驗證通過（76 個動作、250 個事件）。
