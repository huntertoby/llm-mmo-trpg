# Phase 3-48h 報告：違規的選項事前停用＋一批工坊修正

規格：`docs/phases/Phase3計畫.md` 第 59 節（第 2、5a 點已移到 3-51，第 5 點不做）。

## 1. 做了什麼

### 1.1 違規的對象與狀態選項事前停用（第 1、1a 點）

- 新模組 `trpg.skillgen.option_effect_rules`。**與驗證器同源**：`validate.py` 新增 `effect_param_violations(skill, library)`，它呼叫的就是 `validate_skill` 用的同一批規則函式（`_exclusion_violations`、`_passive_violations`、`_stance_violations`、`_beneficial_core_violations`、`_on_kill_status_violations`，以及從 `_skeleton_violations` 抽出來的 `forbidden_affects_violations`），只留 `EFFECT_PARAM_RULES` 列的規則。選項停用不另寫規則：把候選效果放進草稿，直接問 `effect_param_violations`。
- 歸屬方式：單一效果規則（骨架禁止的對象、自身形狀不打敵人、暈眩的形狀與冷卻、核心效果須有益、被動對象、姿態狀態……）＝候選效果單獨放進技能就違規；成對規則（同類控制不重複、傷害與友方治療不並存、姿態必須有姿態狀態）＝加入後違規次數比原本多。
- `affects`（對象）與 `status`（狀態）子選項違規時附 `info.unavailable_zh`（白話原因；能改別的欄位解決的說明怎麼改，例：「『暈眩』是硬控，形狀只能是單體、冷卻至少 4 回合：回到『形狀』步驟改成單體」）。原語所有合理的對象都被擋（例：自身形狀或光環骨架的傷害）時，整個原語標示不可用。
- 對象預設值：`FieldSpec.default` 改成「合理且合法」的第一個（有害打敵方；有益給自己或友方，自身形狀優先自己）；引擎省略對象時的預設若不合法，欄位改為必填。
- 已加入的效果（1a）：`DraftOptions.effect_fixes`（`EffectFix(index, value, reason_zh)`）列出「對象不合法」的效果與建議的合法對象（施加有益狀態、對象沒填 → 友方／自己；有害 → 敵方；骨架或形狀改變後已選的對象不合法 → 改成合法值；沒有合理的合法對象時 `value` 為 `None`，只附原因，不亂改）。前端 `conformAffects` 照 `conformScaling` 的做法每次選項更新都套用；玩家已選的合法對象不會被蓋掉。
- 代價步驟：選了硬控（暈眩、冰凍）後冷卻欄位的下限改為規則要求的 4，說明寫出原因（`cooldown_requirement`）。代價還沒填冷卻時，效果選項假設之後會給足夠的冷卻（冷卻在後面的步驟選）。
- 前端：`FieldEditor` 的單選（卡片、按鈕、下拉）依 `info.unavailable_zh` 停用並顯示「不能選：原因」；目前已選的那一項不停用。
- 行為一致測試 `tests/skillgen/test_workshop_48h_rules.py`：隨機草稿（14 個種子）× 每個原語的每個對象／狀態選項，「選項顯示可用」⇔「完整 `validate_skill` 對這類規則沒有新違規」；另有使用者案例（自身＋光環＋暈眩／免死／戰意）、暈眩冷卻、對象預設與修正建議。

### 1.2 其他項目

- **第 4 點 免死改名**：見第 3 節盤點。
- **第 5b 點 放置陷阱**：① 陷阱設定區說明「踩到後會結算：下方其他效果（目前：…）」，沒有其他效果時「請新增一個效果（例如傷害），它就是踩到後的效果」（`trap_effects_text`）；驗證器新規則 `trap.effects`（檢查面板同樣說明）；② 技能卡寫成「放置隱藏陷阱（3 輪後消失）：敵人踩到時，以該格為中心，…」（`trpg.narrative.skills._place_trap`）；③ 缺字（「rounds 輪後觸發」的變數名被拿掉）與英文（delay、trap）：原語說明由 `workshop_text.yaml` 玩家語氣覆蓋，選項說明沒有英文（`test_player_text`／新的掃描涵蓋）；④ 對象選項：放置陷阱的「對象」只剩一個選項「格子」（見待決 #1）。
- **第 5c 點 schema 錯誤白話**：`plainify` 補 pydantic 訊息（Extra inputs、字典／列表／數字、字串長度、聯集標記、tag 不符……）與 100 多個欄位名的中文（`_FIELD_ZH`）；`validation_messages` 不再把聯集分支標記（`int`、`literal[...]`）當位置；`_with_step_links` 改用 `_owner_step`：訊息開頭的路徑第一段（`trap.*`、`followup.*`、`variants[n].*`、`effects[n].*`）找所屬步驟，找不到就找訊息裡第一個欄位名，並涵蓋選項專屬的參數（`weapon_req`、`ap_cost`），所屬步驟 `complete=False`（不打勾）。掃描測試 `tests/skillgen/test_workshop_48h_schema.py`：把錯誤型別的值塞進 5 招內建技能（陷阱、變奏、複合、區域、獻祭）的每一個欄位（167 個案例）。順手修 3 個垃圾值會讓 `draft_options` 崩潰的地方（`followup.when`、探測時的未知原語）。
- **第 5d 點**：
  - 守護符陣 `skill_rune_ward`（主動、aura、`allies_in_radius` 半徑 2、護盾 2d6＋效果條件 `on_own_rune`、法力 6、冷卻 3、AP 1），預算 **91.5%**（70～100%），不在 `known_budget_exceptions`。行為測試 `tests/engine/test_rune_ward_48h.py`（站在自己符文上的友方有護盾；沒符文、別人的符文、半徑外都沒有）。放進 `build_runeweaver`（見待決 #3）。技能總數 218 → 219（CLI 快照、`skill_icons.json`、`test_skill_scaling`、`test_budget_cli`、`llm_propose_mock.txt` 已更新）。
  - 淨化改規則（#60）：引擎 `_cleanse` 與 AI `_supports` 改看 `polarity == "debuff"`；表格測試 `tests/engine/test_cleanse_polarity.py`（每種狀態一列，33 種）＋全部中性狀態保留；說明句「移除所有負面狀態」維持（原語說明來源文字、`llm_hint`、卡片句同步）。
  - 說明句（`content/workshop_text.yaml`）：intercept「替身」→「替隊友擋下」（靈魂連結的對比句同步）；賭注「傷害乘上倍率（例：×2）」「反噬不能是硬控（暈眩、冰凍）、跳過回合或持續傷害」；擊殺時補「施加的狀態只能是有益狀態」；「最多 5」「堅韌、迅捷、銳利」改為 `{rune_max_rounds}`／`{summon_traits}`，由 `option_player.fill_placeholders` 依核心規則填入；原語「給予行動點」→「給予 AP」（`name_zh`、`player_description`、`llm_hint`、詞彙表 fixture）。
  - 變奏代號：`FieldSpec.auto_generated`（新旗標）；玩家模式隱藏型態代碼欄位、新增變奏時前端自動產生 `form_1`、`form_2`…（`withAutoValues`）；開發者模式（`?dev=1`）照舊顯示可改；`test_player_text.py` 拿掉 `tide_pierce` 放行。

## 2. 規則對照表（第 3 點：驗證器所有規則 × 工坊哪一步事前提示）

「事前」＝選項在選的當下就停用或限制；「事後」＝只在檢查面板（即時檢查／稀有度步驟的違規列表）報；括號是 3-48h 新增的。

| 規則代碼 | 內容 | 工坊 |
|---|---|---|
| `reference` | 引用的 ID、參數範圍 | 事前：選項只列存在的值與範圍 |
| `cap.resource`／`cap.min_cost` | 法力／耐力依類別；主動技能最低花費 | 事前：代價步驟欄位依類別；最低花費寫在說明（空白或 0 事後報） |
| `cap.effects` | 效果 1～4 個 | 事前：效果欄位 `max_count`＋備註 |
| `cap.weapon_req` | 武器需求大類 | 事前：基本設定只列合法大類 |
| `cap.self_status` | 自身狀態代價白名單 | 事前：代價步驟只列白名單 |
| `cap.rule_rewrite`／`cap.rule_rewrite_cost`／`cap.revive_cost` | 改寫規則型上限、需限一次或長冷卻 | **事後**（尚無事前提示，建議後續補代價步驟備註） |
| (`trap.effects`) | 陷阱要有踩到後的效果 | 事前：陷阱設定區說明＋事後：檢查面板 |
| `rune.tag` | 刻印標籤只能用已定義的 | 事前：下拉選單（3-48c） |
| `on_kill.beneficial` | 擊殺時施加的狀態只能有益 | 事前：巢狀欄位只列有益狀態（3-48f）；事後：檢查 |
| `scaling.weapon`／`scaling.range` | 縮放屬性允許範圍 | 事前：基本設定選項＋`conformScaling`（3H-6、3-48） |
| `keyword.required` | 至少一個關鍵字 | **事後**（3-51 處理） |
| `passive.category`／`passive.affects` | 被動骨架的類別；觸發對象為自己時效果只能作用在自己 | 事前：基本設定限制類別；（3-48h）對象選項；被動對象本來就只列「自己」 |
| `stance.misuse`／`stance.status`／`stance.duration` | 姿態狀態只能由姿態技能施加、姿態技能須施加姿態狀態、不設持續回合 | （事前：3-48h 狀態選項停用）；持續回合事後 |
| `exclusion.no_cooldown_big_area` | 無冷卻不得用大範圍形狀 | 事前提示：形狀步驟備註；形狀不停用（冷卻在後面才選）；事後：檢查 |
| `exclusion.stun_single_long_cooldown` | 硬控只能單體、冷卻至少 4 | （事前：3-48h 狀態選項停用並說怎麼改；代價步驟冷卻下限） |
| `exclusion.no_push_with_pull` | 推拉不並存 | 事後（效果備註列出規則）；建議後續補成原語停用 |
| `exclusion.self_shape_no_enemy_effect` | 自身形狀不打敵人 | （事前：3-48h 對象選項停用；已選的對象自動修正建議） |
| `exclusion.no_damage_with_ally_heal` | 傷害與友方治療不並存 | （事前：3-48h 對象選項停用） |
| `exclusion.no_repeated_control_group` | 同類控制不重複 | （事前：3-48h 狀態選項停用） |
| `skeleton.disabled`／`skeleton.kind`／`skeleton.shape` | 骨架啟用、種類、形狀 | 事前：只列啟用的骨架與其種類、形狀 |
| `skeleton.core`／`skeleton.secondary`／`skeleton.secondary_count` | 核心與附帶效果的原語與數量 | 事前：原語選項標示核心／附帶、備註列上限 |
| `skeleton.forbidden_affects` | 骨架禁止的對象 | 事前：選項只列骨架允許的對象；（3-48h：預設對象改成合法值、原因附說明）|
| `skeleton.core_beneficial` | 核心效果的狀態與表面須有益 | 事前：光環的狀態／表面只列有益；（3-48h：核心狀態停用附原因） |
| `skeleton.condition`／`skeleton.required_primitive` | 骨架需要條件／指定原語 | 事前：備註；事後：檢查 |
| `skeleton.core_share`／`skeleton.secondary_share` | 點數占比 | 事後（預算依賴整體組合）；備註列門檻 |
| `rarity.*` | 稀有度限制 | 事前：稀有度步驟只列允許的稀有度，原因附「回到第 N 步」 |
| `budget.*` | 預算窗 | 事後：預算面板 |
| `variant.<id>.*`、`followup.*`、`composite.skeleton` | 變奏型態、複合技能各段 | 事前：變奏與第二段各自的選項；事後：檢查 |
| 巢狀／模型 `schema` 錯誤 | 型別、必填、範圍 | 事前：欄位型別與範圍；（3-48h：事後的 schema 訊息白話＋回到第 N 步） |

## 3. 免死改名盤點（第 4 點）

grep `不死`（排除 `不死系`／`undead`）後改為「免死」的地方：

- `content/statuses.yaml`：狀態 `undying` 的 `name_zh`，以及兩段註解。
- `content/skill_primitives.yaml`：`cheat_death` 的說明（狀態「免死」）與 `duration` 參數說明。
- `content/workshop_text.yaml`：原語 `cheat_death` 與工坊選項的 `source`（與 `skill_primitives.yaml` 一致才查得到）。
- `content/ai_profiles.yaml`（註解 `undying_points`）、`src/trpg/content/battle.py`、`environment.py`、`engine/ai/utility.py`、`engine/effects/handlers.py`、`engine/events.py`、`engine/skills/primitives/rule_rewrites.py`（說明與註解）。
- 測試 `tests/narrative/test_events_text.py`（戰鬥紀錄文字「的『免死』擋下了致命傷害」，文字由狀態 `name_zh` 產生）。
- 前端 fixture：`client/src/battle/fixtures/glossary.json`（重產）、`client/src/workshop/fixtures/options_charge_*.json`。
- 技能卡、詞條、戰鬥紀錄的文字都由狀態 `name_zh` 產生，沒有另外寫死「不死」。
- **沒有改**：`undead` 標籤的「不死系」（`narrative/tile_info.py`）、聖屬性說明「傷害不死者」（`elements.yaml`、`docs/design/05-戰鬥.md`）。
- 順帶：`content/sim/builds.yaml` 註解的「不死誓約」（技能實際名稱是「不滅誓約」）改為「不滅誓約」。

## 4. 淨化規則的影響（第 5d 點）

- 內建技能：只有 `skill_purify` 用 `cleanse`；AI 只有 `_supports`（有負面狀態才值得淨化）與 `_gains` 的 `StatusRemoved(cleansed)` 價值。
- **目前所有內建狀態的行為完全不變**：33 種狀態裡，非有益的全部是 `polarity: debuff`，中性（隱蔽、蓄力、免死、靈魂連結、兩個姿態）全部 `beneficial: true`，所以舊規則（非有益且非姿態）與新規則（減益）結果相同。沒有 AI 依賴「淨化移除自己的姿態／隱蔽」。
- 差別只在之後新增「中性但非有益」的狀態時才會顯現（新規則保留它）。`LOG_FORMAT` 沒有遞增（事件格式沒變、現有內容的重播結果沒變，仍是 `/66`）。

## 5. 測試與檢查

- pytest：除 `llm` 與 `cli` 外全部 6591 通過（含 `test_player_text.py`、新增的 4 個測試檔）；`-m "slow or not slow" tests/cli` 148 通過（CLI 快照 `cli_output_hashes.json`、`llm_propose_mock.txt` 因新技能重產；run auto 種子沒有變動）。
- vitest 946 通過（新增 `effectRules48h.test.ts`）、`tsc`＋`vite build` 通過；ruff、format、mypy、lint-imports 通過。
- 一場含守護符陣的重播：`trpg battle --map training_range --seed 7 --ally-build build_runeweaver` 的紀錄重播驗證通過（257 個動作、663 個事件，最終狀態一致）。
- 排版煙霧檢查（內建瀏覽器，埠 8019，1600×900、800×600、底部列最矮）三種情況全 PASS；伺服器已關閉。
- 新增測試：`tests/skillgen/test_workshop_48h_rules.py`、`test_workshop_48h_schema.py`、`tests/engine/test_cleanse_polarity.py`、`test_rune_ward_48h.py`、`client/src/workshop/effectRules48h.test.ts`。

## 6. 待 PM 決定

1. **放置陷阱的對象**：規格 5b-④ 寫「照刻印的做法只留格子」。刻印是 `acts_on: tile` ＋ `forbid_affects`；若把 `place_trap` 也改成 `acts_on: tile`，預算器會對它套形狀倍率，**內建陷阱預算會變**（灰燼地雷 90.5% → 99.8%，仍合格）。我採保守做法：`acts_on` 不動，工坊的「對象」欄位只留一個選項「格子」（值仍是 `self`），內建技能全部通過、預算不變。要不要真的改成 `tile` 請 PM 決定（會動到預算與內建陷阱的數值）。
2. **選項停用的語意**：選項標示的是「再加一個這樣的效果會不會違規」（歸屬於這個新效果的違規）；已經加進草稿、後來才變不合法的效果，改由 `effect_fixes` 自動修正（沒有合理的合法對象時只在檢查面板說明，不亂改）。玩家明確選了合法但不「合理」的對象（例：非光環骨架裡對敵方施加戰意）不會被改。
3. **守護符陣放進 `build_runeweaver`**：主動欄位已滿 6 格，**換下了 `skill_chain_lightning`**（其他 build 仍有）。sim 數值會變，未跑模擬；要不要保留這個替換，或改放別的 build，請 PM／玩法 PM 決定。
4. **冷卻未填的假設**：代價步驟還沒填冷卻時，暈眩這類硬控不會被停用（冷卻在後面選，代價步驟會標出下限 4）；已填冷卻不足時才停用並說明。
5. **仍是事後才報的規則**（見對照表）：`cap.rule_rewrite*`、`cap.revive_cost`、`exclusion.no_push_with_pull`、`exclusion.no_cooldown_big_area`（形狀步驟只有備註）、`keyword.required`（3-51）、占比與預算。建議之後補：改寫規則型與復活的代價步驟備註、推拉不並存的原語停用。
6. **變奏代號**：玩家模式自動產生 `form_N`；已存的舊技能（含手寫代號）不受影響。
7. 守護符陣的預算是 91.5%（骰 2d6）；數值未經模擬，照其他 `known_budget_exceptions` 以外的新技能慣例標為初值。
8. worktree 的 `client/node_modules` 是我用目錄連結（junction）指到主 checkout 的（git 已忽略），不影響提交。
