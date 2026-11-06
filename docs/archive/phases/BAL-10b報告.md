# BAL-10b 報告：補閃現小變化模板（第 1 段：複合技、修正型被動、姿態與變身）

範圍照玩法 PM 決定：在 6.34.4 既有類別內補模板、不改出題規則；補不到的照既有規則少出選項。資料驅動（`content/flash_templates.yaml`），程式不寫死技能 ID。

## 做了什麼

### 1. 複合技：接續段強化（第一段形狀不動，也不再加接續段）
| 模板 | 類別 | 內容 |
|---|---|---|
| `followup_potency` | 連段 | 接續段傷害只往上調（不重設到最弱）；結構不變 → 強度嚴格變強。先取「最小的合格增幅」（固定強度檢查），留空間給之後的閃現 |
| `followup_area` | 範圍 | 接續段形狀的 size／radius +1 |
| `followup_range` | 範圍 | 接續段固定射程 +1 |
| `followup_element` | 元素與關鍵字 | 接續段加第二元素傷害（2 階起，同 `element_second`） |

- 實作細節：內建複合技的接續段傷害常已超過第一段骨架的核心占比，重調器（從最弱往上調、不允許占比違規變多）收不了；所以接續段的旋鈕從目前的值起往上，並附「原樣／原傷害往下讓 1～4 格」的草稿，重調失敗時改用固定強度直接檢查預算窗與強度下限。
- 既有 `followup`（追擊）、升階重配、完整技能走的旋鈕邏輯 **完全不動**（快照證明，見下）。

### 2. 修正型被動
- **放寬 `mod_potency`**：沒有正的傷害／治療幅度時，改用 `rules.modifier_knobs` 列的其他幅度（召喚物 HP／傷害‰、形態進入獎勵‰、推擊距離）與命中後效果的骰子當旋鈕；有條件、沒條件都可以。有傷害／治療幅度的技能照舊（結果不變）。
- **新增 4 個**（類別「修正」）：`mod_duration`（命中後狀態／符文或召喚持續 +1）、`mod_stack`（依空欄位計算的格數上限 +1）、`mod_cooldown`（命中後冷卻 −1 → −2）、`mod_cost`（代價減輕：負的傷害／治療‰ 往 0 減 100、命中 −n → −(n−1)、AP +1／召喚上限 −1／射程 −1 整條拿掉，至少留一條規則）。新模板的傷害／治療用較細的階梯（`modifier_fine_step: 5`‰），結構一變點數跳太多時可以往下補。
- 形態維持費（`form_upkeep_permille`，#67 化形專精減半）**不能當旋鈕**：schema 擋掉，資料也沒列。
- 沒有條件的修正型被動仍不出「條件放寬」「第二個關鍵字」（有測試）。

### 3. 姿態與變身
- `stance_cost_light／heavy` 放寬到 **變身姿態**：維持費照 #67 不動，改用「進入代價」（模板 `cost_fields: [cooldown]`）±1 當費用旋鈕——蓄力＝進入冷卻 +1、形態幅度提高；輕巧＝進入冷卻 −1、幅度降低（目前內建形態都沒有進入冷卻，所以輕巧不出）。
- 放寬到 **多效果姿態**：恰好一個「姿態本體」效果（姿態狀態或進入形態）時，姿態類模板只動那個效果（`stance_potency` 一併適用）。
- 新增 `stance_enter_light`（類別「費用」）：施放費用 −1，姿態本體與維持費都不動。`cost_fields: [ap_cost, cooldown]`（照指示「AP 或冷卻」；姿態的 ap_cost 規定是 null、進入固定 1 AP，所以實際只有冷卻）。
- 清空模板的 `cost_fields` 就回到 BAL-2c 的「變身姿態不出費用類」（有測試）。

### 4. 測試
- 新增 `tests/skillgen/test_flash_bal10b.py`（43 個）：每個新模板／放寬檢查 合法（含 6.6）、預算比例在窗內、強度下限（強化類嚴格變強）、只動該動的欄位；卡片＝實戰：接續段骰子＝引擎擲骰、`mod_stack` 的「最多 N 格」＝引擎普攻倍率、形態進入冷卻＝引擎冷卻且維持費 −8 耐力不變。複合技（資料挑出的全部 8 招）最低階級第 1 次 ≥ 2、第 2 次每個分支都還有選項。
- 修改：`test_flash_templates.py`（代表性池加 2 個夾具：有進入冷卻的熊形態、冷卻 −1＋傷害的修正；`followup_element` 列入 2 階；「指定類別沒有選項」改用 `skill_thunder_hand`）、`test_flash_form_bal2c.py`／`test_flash_stance_all_bal2b.py`（變身姿態的費用類改成 BAL-10b 行為）。
- `scripts/flash_category_audit.py`：補新 op 的不合法原因文字。
- 行為快照 `tests/skillgen/fixtures/refactor_3wr2.json` 重產：**只有 13 筆閃現出題變了**（attack_mastery、form_demon、rune_breaker、shadow_whirl 各 3 個種子，deep_freeze 1 個——它第 1 次選了「追擊」變成複合技，第 2 次出現接續段模板）；完整技能強度、升階重配全部不變。LLM 閃現目錄由資料展開，新模板自動列入，llm 測試全過、不需改。

## 重掃結果（`scripts/flash_minor_coverage.py --jobs 8`，同 BAL-10a 參數）
產物：`docs/phases/BAL-10/minor_coverage_bal10b.md`／`.csv`（BAL-10a 的 `minor_coverage.*` 保留為「之前」）。

全部不足列：292 → **258**。三類前後（列＝(技能, 角色階級)；「最低階」＝技能自己的階級）：

| 類別 | 列數 | 第 1 次 <2 | 第 2 次 <2 | 最低階 第 1 次 <2 | 最低階 第 2 次 <2 |
|---|---|---|---|---|---|
| 複合技（內建 8 招） | 22 | 7 → **0** | 12 → **2** | 4 → **0** | 6 → **2** |
| 姿態（內建 12 招） | 30 | 24 → **0** | 24 → **4** | 10 → **0** | 10 → **4** |
| 姿態（白板） | 3 | 2 → 2 | 3 → 3 | 1 → 1 | 2 → 2 |
| 修正型被動（內建 18 招） | 53 | 40 → **34** | 51 → **48** | 13 → **12** | 18 → **17** |
| 修正型被動（白板） | 3 | 0 → 0 | 3 → 3 | 0 → 0 | 3 → 3 |

目標四招（最低階級 第 1／第 2 次，之前 → 之後）：影旋斬 `skill_shadow_whirl` 1/0 → **3/2**、重力爆 `skill_gravity_burst` 1/0 → **4/4**、破甲連擊 `skill_armor_break_combo` 0/0 → **2/2**、躍擊 `skill_leap_slam` 1/0 → **4/1**。其餘：`skill_death_spiral` 3/1 → 4/3、`skill_retreating_slash` 4/1 → 4/4、`skill_parry_riposte` 4/3 → 4/4、`skill_charged_cleave` 4/2 → 4/1。

## 殘留名單（仍 < 2；第 2 次取所有分支最小值）
**複合技（2 列）**——都是「第 1 次某個分支把比例推到窗頂，第 2 次只剩蓄力」，原因是旋鈕級距：
- `skill_leap_slam`（2 階）4/1：選了接續段第二元素後，比例 0.97，接續段武器倍率下一格（+100‰）超過窗。
- `skill_charged_cleave`（1 階）4/2 → 4/1：新增的「接續段強化」最小一格（倍率 1000 → 1100）就到 0.996，第 2 次只剩蓄力。這是新分支造成的最小值下降，不是原有分支變差。

**姿態（內建 4 列＋白板 3 列）**
- `skill_form_bear／cat／roc／werewolf`（1 階）2/1：第 1 次選「強效」（幅度 1000 → 1050）後比例 0.992，第 2 次只剩蓄力；形態幅度一格 50‰ 大於一次閃現的 +40‰。（選蓄力的分支第 2 次有 4 個。）
- 白板 ironwall（3 階）1/0、flame（2 階）2/0、flame（3 階）0/0：已在階梯頂或沒有進入冷卻；它們的進入代價是法力（2～3）。**若 `stance_enter_light` 的 `cost_fields` 加上 `mana`／`stamina`，這 3 列各多 1 個選項**（已試算）。

**修正型被動（內建 48 列、白板 3 列）**，依原因：
- 只有旗標型改變、沒有任何幅度（`skill_burning_shove`、`skill_thunder_hand`、`skill_timber_piercer`、`skill_self_mending`、`skill_beam_of_mercy`、`skill_lingering_roar`）：0～1 個；模板沒有可動的數值（6 招 × 3 階）。
- 一級的離散改變一變就翻倍、超出預算窗（`skill_ember_cycle` 冷卻 −1→−2、`skill_heavy_stomp` 推擊 1→2／拿掉 AP +1、`skill_summon_swarm` 持續 1→2、`skill_rune_etcher` 符文 2→3 回合）：只在預算剛好有空間的階級出現。
- 有條件的傷害型（`skill_rune_resonance`、`skill_rune_sight`、`skill_searing_scar`、白板 3 招）第 1 次 3～4 個，但第 2 次常剩 1（重調窗太窄，BAL-10a 第 7 點的預算窗問題）。
- `skill_attack_mastery` 1/2、1/1、1/2：強效的傷害階梯 50→75 一格 +50%（舊階梯，未動），只剩新的「計數上限 +1」。
- `skill_form_mastery` 只到 2/0（1、2 階）：強效＋代價減輕兩個，第 2 次重調不進窗。

## 待 PM 決定
1. **【規則，須回使用者】變身姿態出費用類**：06 6.34.4 BAL-2c 寫「變身姿態只出修正類閃現（費用類唯一的旋鈕是維持費，不能動）」。本段依指示放寬（改用進入冷卻當費用旋鈕，維持費照 #67 不動），但設計文件那句仍在。需要玩法 PM 附使用者原話改 6.34.4；若不同意，把 `stance_cost_light／heavy` 的 `cost_fields` 清空即回到 BAL-2c（一行資料，有測試）。
2. **【數值】姿態的「進入冷卻」幾乎沒有代價**：姿態／形態一進入就持續到取消，進入冷卻多 1 回合實戰影響很小，但預算照冷卻折抵算，等於「蓄力」近乎白送幅度。建議模擬後決定是否另訂姿態的冷卻折抵係數（預算器，下一段旋鈕查修）。
3. **【數值】`stance_enter_light` 是否納入法力／耐力**：指示寫「AP 或冷卻」，照字面只動冷卻（內建姿態都沒有，實際只在蓄力加過冷卻後出現）。白板姿態的進入代價是法力，加入 `mana`／`stamina` 可補 3 列殘留。
4. **【數值，旋鈕查修段】級距太粗**：接續段武器倍率（600～1000 段每格 100‰）、形態幅度每格 50‰、修正傷害階梯每格 25‰（普攻精通 50→75）都大於一次閃現的 +40‰；是殘留的主因。新模板已用細階梯（5‰），舊的 `mod_potency` 傷害階梯沒動（會改既有結果）。
5. **多效果姿態**：放寬也讓 `stance_potency` 適用多效果姿態（同一個判斷）；目前內容裡沒有多效果姿態，只有測試夾具。
6. `mod_cost` 把「AP +1、召喚上限 −1、射程 −1」這類一級代價整條拿掉（`skill_heavy_stomp`、`skill_summon_elite`）；若希望代價只能減輕不能消失，改成不出即可。

## 複雜度與例外
- `scripts/flash_category_audit.py` 的 `_why_stance` 加 `# noqa: PLR0911`（依序判斷的原因表，多一個回傳）。其他新函式都在上限內。

## 驗證
- ruff check、ruff format --check、mypy（900 檔）、lint-imports（7 kept）通過。
- pytest（`-m "(slow or not slow) and not llm"`）：tests/skillgen＋tests/narrative＋tests/llm 4491 passed（修正 usage_base 後相關檔 888 passed）；tests/roguelite 224 passed。
- commit 時間點：程式與測試一個 commit、快照一個 commit、報告與掃描產物一個 commit（三點改到同一批檔案，未拆成每點一個）。
