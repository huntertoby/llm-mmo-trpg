# Phase 3-41c 完成報告：說明整修補遺

規格：`docs/phases/Phase3計畫.md` 第 45 節開頭原則與 45.5 第 1～6 點。第 5 點用 3H 的最終規則（`Phase3H計畫.md` 第 5 節、`Phase3H-1／2／3報告.md`、設計 08 8.11、07 7.2）。

**原則**：規則說明一律由程式依實際規則產生，和規則同一個來源；前端不寫死規則數字。**不改規則與數值**；`LOG_FORMAT` 不變（沒有動任何事件）。規則包文字有變（`statuses.yaml` 說明、`ai_profiles.yaml` 加欄位）→ `ruleset_hash` 變，舊存檔會出現既有的「規則已更新」提示（和 3-41a 同）。

## 逐點對照

| # | 做了什麼 |
|---|---|
| 1 層數說明框 | 技能卡新增 `SkillCard.stacks`（`SkillStackRef`：層數、中文名、累積 `makes`／消耗利用 `uses`，由技能效果的 `add_stack`／`consume_stack`／`scale: stacks` 產生，`narrative/skills.py skill_stacks`）。前端共用元件 `ui/StackTip.tsx`（包 `<Hint>`，遵守 6.5.1）：技能卡的「層數：靜電（累積）」、戰鬥 HUD 的「層數」行、單位資訊卡的「層數」行都可滑出說明框，內容＝名稱、一句話、規則句（`/api/glossary` 的 `stacks`）；**主角**再列「你的技能・累積：…／消耗／利用：…」（`battle/stackInfo.ts`，用目前持有的技能卡過濾），敵人與工坊（沒有持有者）只寫一般說明。 |
| 2 召喚物實際值 | 引擎 `engine/summons.py` 新增 `summon_stats(state, owner, template, skill_id, spec)`（`SummonStats`：HP、含多的骰與成長固定傷害的武器、移動、護甲、傷害加成、等級、屬性修正）：用 `summon_unit` 同一批函式（`growth_of`、`_hp_permille`、`_empowered_weapon`、`summon_scaled_hp`、`summon_spec_hp`、新抽出的 `summon_variants.trait_adjusted`，預設灌注也照引擎取第一個可選的）。新端點 `GET /api/battles/{id}/hero-cards` 回傳主角技能卡的「實際值版本」（`api/hero_cards.py`；只含有算式或召喚物的卡），前端 `ui/useHeroCards.ts` 在輪到主角時查一次並蓋在基本卡片上，技能列浮動卡因此用施放者當下的等級、屬性（含狀態加值）、修正規則。召喚效果句的「HP N」同步用實際值。`SummonInfoCard` 加 `basis`／`basis_zh`：小卡標題寫「HP 14・基準值（1 級）」（工坊、升級三選一、開局預覽）或「HP 14・你目前的實際值（N 級）」（戰鬥中），HP 說明寫「你目前 N 級、意志修正 M：…」。數量型進化的傷害加寫「每隻只有一般的 X%」。 |
| 3 行為玩家說明 | `ai_profiles.yaml` 每個模式加必填 `player_description_zh`（`AiProfile` schema 必填，全 7 個覆蓋）；`summon_behavior_lines` 改寫「行動方式「弓手」：和敵人保持距離，找高處與視線好的位置遠遠射擊。」，不再顯示 `description_zh`（開發者說明）。 |
| 4 狀態數字由欄位產生 | `narrative/status_info.py status_rules` 新增數值句：`damage_dealt_permille`／`damage_taken_permille`／`healing_received_permille`／`move_permille` → 「×75%」之類（表格 `_PERMILLE_FIELDS`）、`attr_bonus`（六屬性同值寫「六個屬性各 +2」，否則逐一列）、`attack_bonus`、`attack_range_cap`；守護的防禦 +25%、倒地站起的移動消耗、隱蔽的 2 格改取 `core.yaml`。`statuses.yaml` 的 `description_zh` 全部去掉這些數字（虛弱、易傷、護衛、激昂、戰意、加速、緩速、致盲、中毒、狂怒、堅壁、守護、倒地、隱蔽、定時炸彈）。 |
| 5 吃什麼屬性與傷害算法 | `WeaponDef.scaling_value(get)`（雙屬性取較高／平均的唯一算式，引擎 `weapon_attribute` 改呼叫它）、`WeaponDef.attack_formula_zh(core, get?)` → 「普攻：1d8＋力量 × 0.3（目前 +4.2）」，雙屬性寫「敏捷／力量（取較高）」「體質／力量（取平均）」；放在 `rule_lines_zh` 第一行，所以角色面板、戰鬥單位資訊、開局武器提示、build 列表都有。`SkillDef.scaling_value(get)`（引擎 `skill_scaling_value` 改呼叫它）、`SkillDef.formula_lines_zh(core, weapon?, get?)` → 「傷害算法：武器骰 1d8＋力量 × 0.3（目前 +4.2）」（法術技「骰值＋智力 × 0.5」、治療與護盾同用法術倍率）；`SkillCard.formula_lines`，前端技能卡顯示。「目前」：一輪主角面板／候選卡＝基礎＋裝備屬性（`hero_effective_attributes`），戰鬥中＝有效屬性（含狀態）。倍率取 `rules/core.yaml`。 |
| 6 開局資源預覽 | `roguelite/start.py` 新增 `hero_resources(core, hero)`（HP：`run_max_hp`；法力、耐力：`core.resources.max_for`）——`new_keyword_run`、`new_run` 建立主角改用它，`start_resources(library, weapon, allocation)` 給預覽用，兩者是同一個函式。端點 `POST /api/runs/start-resources`；開局畫面（`RunNewScreen`）的「主角：HP …・法力 …・耐力 …」改取自它（配點即時更新、顯示耐力），拿掉前端自己加體質 HP 的算式。 |

## 傷害算法句與引擎一致的測試（`tests/narrative/test_rule_texts_41c.py`）

- `test_basic_attack_formula_matches_engine_bonus`：14 把可選武器 × 4 組屬性（含雙屬性取較高／平均的各種大小關係），用引擎實際執行普攻，`damage_dealt` 事件的 `scaled_permille`（骰外加成，‰）＝ 卡片「目前 +N」× 1000，`flat` ＝ 武器固定傷害；同時比對 `weapon_attribute` ＝ `scaling_value`。
- `test_skill_formula_matches_engine_scaled_value`：全部約 90+ 個有傷害效果的技能 × 3 組屬性，卡片「傷害算法…（目前 +N）」＝ 引擎 `damage_parameters` 的 `scaled_permille`。
- `test_summon_actual_values_match_the_engine`：每個召喚效果 × 3 組（等級，屬性），`summon_stats` 與 API 卡片的 HP 同引擎實際生成的召喚物（HP、傷害骰、固定傷害、移動、護甲、傷害加成）逐項相同。
- `test_start_preview_equals_the_new_run_hero`：3 把武器 × 3 組配點，預覽的 HP／法力／耐力 ＝ `new_keyword_run` 建立的一輪（含 `max_*_in`）。
- 其他：狀態說明不含與欄位重複的寫死數字（掃描）、改欄位文字跟著變、AI 模式玩家說明全覆蓋且無開發字眼／英文／數字、召喚物行為不含開發者說明、層數 ref 與規則包名稱一致；前端 `ui/stackInfo.test.ts`（層數說明框過濾、實際值卡片覆蓋、資源預覽文字）。

## 改前／改後對照（節錄）

| 項目 | 改前 | 改後 |
|---|---|---|
| 虛弱說明 | 自己造成的攻擊傷害 ×75%。 | 說明：自己造成的攻擊傷害降低。／規則：自己造成的攻擊傷害 ×75% |
| 加速 | 回合開始時的移動點數 ×150%（無條件捨去）。 | 說明：回合開始時的移動點數增加。／規則：回合開始時的移動點數（無條件捨去） ×150% |
| 致盲 | …只能選擇 2 格以內的單位；攻擊有劣勢。 | 說明：只能選擇近距離的單位；攻擊有劣勢。／規則：…只能選擇 2 格以內的單位 |
| 堅壁姿態 | 受到的骰值傷害 ×75%，但…移動點數減半 | 規則兩行：傷害 ×75%、移動點數 ×50% |
| 守護 | 防禦值 +25%，持續到… | 說明：防禦值提高…／規則：防禦值 +25%（取 `defend_defense_bonus_permille`） |
| 召喚物行為 | AI：弓手，重視距離、高處與視線。 | 行動方式「弓手」：和敵人保持距離，找高處與視線好的位置遠遠射擊。 |
| 召喚物小卡（戰鬥中） | HP 14（1 級基準） | HP 14・你目前的實際值（1 級）；升級後 HP、傷害骰、加成隨等級與屬性成長 |
| 單手劍武器卡 | （沒有算法） | 普攻：1d8＋力量 × 0.3（目前 +4.2） |
| 匕首 | （沒有算法） | 普攻：1d4＋敏捷／力量（取較高） × 0.3（目前 +5.4） |
| 錘 | （沒有算法） | 普攻：1d12＋體質／力量（取平均） × 0.3（目前 +3.6） |
| 劈砍（技能卡） | 武器傷害 ×… | 另加一行「傷害算法：武器骰 1d8＋力量 × 0.3（目前 +4.2）」 |
| 開局預覽 | 主角：HP 60・法力 20・武器…（前端自己加體質 HP、沒有耐力） | 主角：HP 66・法力 22・耐力 34・武器…（體質 12、力量 11、意志 11；配點即時更新） |

實機 8011（1600×900）：開局畫面配點即時更新資源預覽（體質 +2、力量 +1 → HP 66、耐力 34；意志 +1 → 法力 22）；角色面板「普攻：1d8＋力量 × 0.3（目前 +3.3）」；戰鬥中召喚冰靈浮動卡標題「HP 14・你目前的實際值（1 級）」，展開後行為欄「行動方式「弓手」：…」；開局預覽的召喚物小卡寫「基準值（1 級）」。（內建瀏覽器截圖逾時，改以 DOM 文字確認；層數說明框以測試為準，這個開局沒有層數技能。）視窗已還原、伺服器已關。

## noqa

無新增。

## 待 PM 決定

1. **「目前加成」顯示小數**：骰外加成是 屬性 × 0.3 或 × 0.5，例 14 力量 → +4.2；引擎先加總到‰ 再乘倍率才無條件捨去，所以卡片照實寫 +4.2（不先捨去，否則和實際傷害對不上）。要不要改成「約 +4」？
2. **戰鬥中召喚物小卡預設灌注**：實際值計入「玩家省略灌注時引擎取的第一個可選關鍵字」（和 `summon_unit` 一致，只有 `summon` 關鍵字有 HP +20%）；玩家施放時改選別的，HP 可能略有不同。小卡灌注欄仍寫「施放時選一個」。要不要在實際值版本直接列出「選 X 灌注 → HP N」？
3. **一輪面板（戰鬥之間）的召喚物小卡**仍是基準值（沒有戰鬥狀態）；傷害算法的「目前」則已用基礎＋裝備屬性。接受的話不處理。
4. **層數說明框的「你的技能」** 只列技能的累積／消耗（`add_stack`／`consume_stack`／`scale: stacks`），不列裝備詞條的充能（那個有自己的 `ChargeChips` 說明）。
5. **守護的「每輪 1 次」** 這類不是倍率欄位的次數仍寫在 `description_zh`（沒有對應欄位）；測試只掃與欄位重複的倍率、加值、格數。要整併再開項。
6. **武器技吃武器屬性**：`WeaponDef` 規則句寫「普攻與武器技吃…」，但引擎實際讓武器技用技能自己的 `scaling_attr`（`skill_scaling.yaml` 對應武器）。卡片的技能算法照引擎（技能自己的屬性）寫，武器規則句沒改；若兩者有出入屬 3H 內容問題（本段不處理）。
7. 開局的資源預覽只做開局畫面；升級配點與營火重配畫面仍只有「最大 HP ＋N」（前端公式，3H-3 就有）。要不要一併改成後端算的 HP／法力／耐力？
