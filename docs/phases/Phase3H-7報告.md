# Phase 3H-7 縮放範圍補齊 完成報告

> 規格：`docs/phases/Phase3H計畫.md` 8.1（第 1～6 點）；背景：`docs/phases/工坊盤點-2026-10-24.md`（盤點 #1、#3、#4、#5，玩法 PM 5 題回覆）、7.1（3H-6 待決 #2、#3）。設計：`docs/design/06-技能.md` 6.10。
> 3H-8（工坊選項與說明整修）由另一個 agent 平行處理，本段 **沒有** 動第二屬性／專精選單、耐力與代價說明、組合規則標章、狀態選單、玩家／開發者模式。`options.py` 只改了縮放屬性欄位（新增 `_spell_scaling_field`，`_scaling_field` 的法術分支改呼叫它）。

## 做了什麼

1. **主題由效果推導**（`content/skill_scaling.py`、`content/skill_scaling.yaml`）
   - `ScalingTheme` 新增效果訊號：`effect_types_any`（原語）、`elements_any`（元素）、`surfaces_any`（表面）、`statuses_any`（狀態）。標籤 `tags_any`／`tags_none` 只當輔助。
   - 新增 `ScalingFacts`（技能或工坊草稿 dict 都能轉成它）、`ScalingBasis`（範圍＋由來）、`SkillScalingRules.basis()`／`scaling_range()`（**有順序**）；`allowed_attrs()`、`spell_theme()` 保留（改走新邏輯）。`ContentLibrary.scaling_basis()`／`scaling_range()`／`summon_elements()`。
   - 例外（`overrides`）也適用於由它進化而來的技能（`parents` 或 `<id>_evo_` 開頭）。
2. **驗證器 `scaling.range`**（`skillgen/validate.py`）：法術技的主屬性與第二屬性都要在範圍內；武器技不能有第二屬性（產生的武器技已由 3H-6 `scaling.weapon` 報過時不重複）。訊息例：「縮放屬性 力量 不在這招的允許範圍：主要效果「傷害（火焰）」屬於「元素傷害與互動」，只能看 智力」。說明文字由 `skillgen/scaling.py` `scaling_basis_zh` 產生，工坊共用。
3. **產生器都收進範圍**（`skillgen/scaling.py` 新增 `fit_scaling`、`fit_draft_scaling`；`retarget_scaling` 改寫）
   - 隨機組合器：抽到的屬性在範圍內就不動，否則取範圍裡第一個（`_fit_attr`，亂數串流不變）；雙屬性的第二屬性 **改從允許範圍（主屬性以外）抽**，範圍裡沒有別的屬性就不給、改看專精。`skill_composer.yaml` 的 `scaling.dual_attrs` 與 `ScalingRules.dual_attrs` 移除。
   - 3H-3 `retarget_scaling`：主屬性取範圍內主角最高；第二屬性和主屬性相同或超出範圍時，改取範圍內（主屬性以外）主角最高的，沒有就拿掉。
   - LLM 提議：有主角屬性照 retarget，沒有時 `fit_scaling`（LLM 填的在範圍內就保留）；保底的工坊推導（`proposal_fallback._finish`）效果填好後 `fit_draft_scaling`。
   - 傳說／修正組合（`composer_special._pick`）、進化（`evolution._tuned`）、召喚進化：驗證前 `fit_scaling`（進化的武器技只拿掉第二屬性，提示屬性不動）。
   - 「一輪中的技能」都來自上述產生器，全部經過 `validate_skill`（含 `scaling.range`）。
4. **工坊**（`skillgen/options.py` `_spell_scaling_field`）：法術（與還沒選類別）的縮放選單只列允許範圍、預設範圍裡第一個，說明寫出由來與「只能看 …」；**還沒選效果時主題未定**，列六個屬性並說明選好效果後只列允許的（之後不合的值會出現在「已填的內容和選項不符」與檢查的 `scaling.range`）。武器技維持 3H-6 的「看手上武器」鎖定。工坊「隨機」走組合器，沒有主角時只在範圍內抽。
5. **3H-6 留下的兩項**
   - 候選產生器：新增 `follows_attr(skill, attr, weapon_attrs)`、`CandidateRequest.weapon_attrs`（主角手上武器的縮放屬性與第二縮放屬性，`roguelite/offers.py` 填入）；加深／橋接／新方向的屬性比對，武器技看手上武器。`SkillOffer.off_route`（偏離路線標示）用同一個判斷（只是標示）。
   - 7 招近戰武器技（`skill_ambush_stab`、`skill_first_strike`、`skill_ground_finish`、`skill_pick_off`、`skill_pincer_strike`、`skill_shadow_ambush`、`skill_shadow_backstab`）提示屬性 敏捷 → 力量（近戰大類主屬性）；`weapon_class_mismatches` 變成空，改成測試鎖定。`build_gambler` 的 `skill_first_strike` 因此和單手劍一致；`build_assassin` 的匕首是敏捷／力量雙屬性，全部招的提示屬性（力量）都在匕首的屬性內（見待決 3）。
6. **內建技能載入檢查**：`scaling_problems` 帶召喚物元素，並檢查武器技不帶第二屬性。

## 主題推導規則（`content/skill_scaling.yaml`）

依序看技能的效果（技能本身的效果在前，複合技能接著看第二段）；**第一個帶主題訊號的效果是主要效果**，附帶效果不算。

| 主題 | 屬性 | 原語 | 元素 | 表面 | 狀態 |
|---|---|---|---|---|---|
| mind（召喚、獻祭、詛咒、心智控制、暗影） | 意志 | summon、sacrifice_summon | shadow | darkness | feared、silenced、taunted |
| support（治療、護盾、輔助、偵測與標記） | 感知 | heal、shield、cleanse、revive、reveal、restore_resource、redirect_damage、cheat_death、extra_reaction、grant_skill、grant_ap、reset_cooldown | holy | holy | marked、revealed、guarded、regenerating、defending、shielded、undying、soul_link、rallied |
| elemental（元素傷害與互動） | 智力 | teleport、teleport_target、swap_any、hurl_object、topple、detonate_runes、copy_skill | fire、ice、lightning、earth、poison、wind | fire、ice、oil、poison | burning、frozen、poison |

- 召喚效果的元素＝召喚物武器的元素（`ruleset.summons`，例：火靈的火焰法杖 → 火）。`consume_status` 的被消耗狀態與 `then` 一起看。
- 沒有訊號的效果（物理傷害、推拉、障礙、減速、緩速、加速、增傷、流血、陷阱、規則改變……）跳過，看下一個。
- 主要效果符合的主題中，表格順序第一個決定主屬性；同一個效果也符合組合主題的另一個主題時（元素＋意志、元素＋感知），範圍＝兩者（主題的屬性在前）。
- **標籤只當輔助**：每個效果都沒有訊號時（修正技能、規則改變型傳說、純物理法術）才看標籤（舊規則：依序第一個符合、`tags_none` 排除、組合主題）。標籤不能改掉效果推導出的主題（測試：治療效果加火焰標籤仍是感知）。
- 都不符合的是身體類（力量、敏捷、體質）。
- 範圍的順序：主題的屬性 → 組合主題的另一個；身體類依 `body_attrs`；例外依列出的順序。沒有主角屬性時取第一個。

## 內建 217 招對照（表格測試 `tests/content/test_skill_scaling.py`）

- 全部 217 招（法術 144、武器 73）推導出的範圍都包含現值與第二屬性。範圍來源：效果推導 102、標籤 21、例外 11、身體類 10、武器 73。
- **新增例外 4 招**（效果推導會落到別的主題，維持現值並附理由）：`skill_bloodlust`（嗜血：擊殺回血的身體被動 → 力量／敏捷／體質）、`skill_grief_rage`（悲憤：怒氣反應 → 身體類）、`skill_ember_ward`（餘燼護盾：火焰系被動 → 智力）、`skill_thorn_wall`（荊棘牆：自然屏障 → 感知）。
- **移除例外 3 招**（效果推導已得到同一個範圍）：`skill_flight`（傳送 → 智力）、`skill_hex_bolt`（主要效果暗影傷害 → 意志）、`skill_mark_detonation`（暗影傷害 → 意志）。
- 範圍改變的 8 招（現值都還在範圍內）：

| 技能 | 現值 | 改前 | 改後 | 原因 |
|---|---|---|---|---|
| skill_holy_water | 感知 | 智力、感知 | 感知 | 主要效果是聖光傷害，水表面是附帶 |
| skill_time_surge | 感知 | 智力、感知 | 感知 | grant_ap 是輔助；奧術標籤不再放寬 |
| skill_summon_bomb_puppet | 意志 | 智力、意志 | 意志 | 召喚物武器是物理（爆炸另算） |
| skill_summon_earth_wall／golem／plateau_totem | 意志 | 智力、意志 | 意志 | 召喚物武器是物理 |
| skill_summon_water_sprite | 意志 | 智力、意志、感知 | 意志 | 召喚物武器是物理 |
| skill_summon_vine | 意志 | 意志 | 意志、智力 | 藤鞭是大地元素 |

## 測試

- 新增 `tests/skillgen/test_scaling_range.py`：火焰法術選力量被擋並有中文原因；第二屬性越界被擋、組合主題內合法；進化武器技帶第二屬性被擋；魔劍斬例外；工坊選單只列允許屬性（5 招草稿表格）、檢查訊息；**組合器 150 個種子（沒有主角）與 40 個種子（有主角）全部在範圍內且合法**；`fit_scaling`／`fit_draft_scaling`／retarget 第二屬性；候選武器技看手上武器。
- 改寫 `tests/content/test_skill_scaling.py`：217 招表格、效果推導、標籤只當輔助、組合主題、例外適用進化技能、武器技第二屬性、`weapon_class_mismatches` 為空。
- 修改：`test_random_composer.py`（雙屬性改從獻祭骨架找，並檢查在範圍內）、`test_proposal.py`（例外清單的內建技能提議出來後縮放屬性依推導，不比對）、`test_scaling_follow.py`（範圍改用 `LIB.scaling_range`）、`tests/api/test_workshop_api.py`（裝上試玩的法術草稿縮放改智力，否則先被 `scaling.range` 擋）。
- 跑過：`tests/content`＋`tests/skillgen` 2618、`tests/roguelite`＋`api`＋`narrative`＋`sim`＋`llm` 806、`tests/cli`（含 slow 快照）148 全過；ruff、format、mypy（src＋tests）、lint-imports 全過；前端 typecheck、vitest 883、build 全過。
- 重產：OpenAPI、`schema.d.ts`、前端 fixtures、CLI 快照——**都沒有變動**（API 模型沒改，CLI 快照不含受影響的欄位）。`LOG_FORMAT` 不動（引擎與戰鬥結算沒改），重播不受影響。

## 種子變動

- 組合器（600 個種子，沒有主角）：其他內容相同 598；縮放屬性改變 247（法術 396 招中 255 招舊屬性超出新範圍，與盤點「6 抽 5 違規」一致）。法術屬性分布 智力 250／意志 69／感知 77 → 智力 151／意志 46／感知 194／力量 5（身體類）；**雙屬性 13 → 0**、專精 104 → 106。另外 2 個種子（438、583）整招不同：第一次嘗試在雙屬性那步少抽一次亂數（範圍裡沒有別的屬性），之後該次嘗試被關鍵字檢查退回，第二次嘗試的亂數串流因此不同。
- 有主角（體質 16、感知 14）：縮放屬性改變 117，雙屬性 12 → 0。
- 史詩 1500 個種子：雙屬性只剩 5 招（獻祭骨架的「元素獻祭」＝意志＋智力，與一招身體類 力量＋體質）。
- 測試沒有鎖具體候選，種子相關測試不需改預期值（上列修改都是規則改變）。
- `run auto`（種子 1～6，舊＝`18e4b97`）：種子 2、3、5 完全相同；種子 1、4、6 升級候選不同（武器技改看手上武器 → 匕首主角的「倒地補刀」不再算同屬性；組合器縮放屬性）。結果見下節。

## 模擬（只量、不調）

- `trpg sim keywords --samples 30`：改前改後完全相同（起始技能是內建技能池，與組合器無關）：勝率 63%，未完成 0。
- `run auto` 種子 1～6（改前 → 改後）：1 失敗 5/6 → 失敗 5/6；2 失敗 2/6 → 同；3 失敗 4/6 → 同；4 **勝利 6/6 → 失敗 5/6（Boss）**；5 失敗 5/6 → 同；6 失敗 5/6 → 同（升級候選換了一招，結果相同）。合計勝場 26/36 → 25/36。樣本太小，只能說明候選有變，不能下平衡結論。

## noqa

無新增。

## 實機（內建瀏覽器，1600×900，`trpg serve --port 8012`，已關閉伺服器並還原視窗）

- 工坊 → 進階 YAML 貼上火焰法術（傷害（火焰）＋燃燒、縮放 力量）：基本設定的縮放選單只剩「智力」，說明「技能的數值隨這個屬性成長。主要效果「傷害（火焰）」屬於「元素傷害與互動」，只能看 智力」；欄位下方「縮放屬性「str」不是合法的選項」；即時檢查列出 `scaling.range 縮放屬性 力量 不在這招的允許範圍：主要效果「傷害（火焰）」屬於「元素傷害與互動」，只能看 智力`。

## 待 PM 決定

1. **雙屬性幾乎消失**：法術第二屬性限在組合主題後，組合器的雙屬性從約 2%（600 種子 13 招）降到幾乎 0（只剩元素獻祭與少數身體類）。要等魔劍士方案 A（武器技＋心智屬性）恢復，還是先調 `dual_permille` 或組合主題？（本段只量。）
2. **身體類法術的第二屬性**：身體類範圍是力量／敏捷／體質三個，組合器仍可能給「力量＋體質」這類第二屬性（不是設計 #46 的「武器屬性＋心智屬性」）。要不要規定身體類不給第二屬性？
3. **刺殺 build 的提示屬性**：7 招改成近戰主屬性力量後，`build_assassin`（匕首 敏捷／力量取較高）的武器技提示屬性都是力量（在匕首的屬性內，但不是匕首的第一屬性敏捷）。引擎不使用；若希望卡片在沒有武器時寫敏捷，需要另訂「提示屬性＝建議武器的第一屬性」的規則。
4. **還沒選效果的工坊法術**：基本設定在效果之前，主題未定時縮放選單仍列六個並提示；效果選好後才限縮（不合的值列為問題）。若要更直覺，3H-8 可考慮把縮放屬性移到效果之後或在效果步驟提醒。
5. **工坊的修正技能與規則改變型傳說**：沒有效果訊號、草稿又沒有標籤 → 落到身體類（力量／敏捷／體質）。內建的修正技能靠標籤判斷不受影響；要不要讓修正規則的 `add_element`／命中後效果也算訊號？
6. **8 招範圍變化**（上表）：召喚土牆／石像／高原圖騰／爆彈傀儡不再能看智力（召喚物武器是物理），召喚藤蔓多了智力；聖水、時間奔流不再能看智力。是否接受，或對召喚物改看召喚物標籤／技能元素？
7. `SkillOffer.off_route`（偏離路線標示）也改成武器技看手上武器（同一個判斷），超出規格字面；只影響標示。
