# Phase 3-48c 報告：工坊試玩回饋第二批

規格：`docs/phases/Phase3計畫.md` 第 53 節（另含專案 PM 追加的持續區域與刻印持續回合調查）。

## 1. 稀有度步驟卡住

- **重現**：武器技（近戰）改成法術技，武器需求仍是「近戰」（法術只能法器／任何武器）；或第二縮放屬性與主屬性相同。`build_skill` 的 schema 失敗，稀有度步驟的 `_probe` 全部回 `None`，只寫「技能定義還有錯誤」，沒列原因。
- **根因**：前端 `conformScaling`（3-48）只對齊縮放屬性，不管武器需求；後端沒有把錯誤列出來；已填的值不在選項內時步驟照樣打勾。
- **修法**：
  - 稀有度步驟直接列白話原因，附「（回到第 N 步修改）」（編號同步驟列；`options._definition_errors`／`_with_step_links`）；「problems」字樣拿掉。
  - 前面步驟有「已填的內容和選項不符」時，步驟列不打勾（流程不擋，避免誤擋合法技能；實測整面擋會讓複合技能的檢查失敗）。
  - 在源頭擋住：前端 `conformScaling` 也對齊武器需求（不在選項內就清掉，玩家重選）。

## 2. 最低花費（06 6.10）

- 規則：`BudgetRules.min_cost_problem`（主動法術技 ≥1 法力、主動武器技 ≥1 耐力；被動、反應、姿態、修正不查）。
- 驗證器：`cap.min_cost`。**內建技能（id 在內容庫且 origin=builtin）不查**，工坊草稿、組合器、LLM 提議都查。
- 工坊：代價步驟的資源欄位說明寫明「主動技能至少要花 1 點」；空白或 0 在即時檢查被擋（欄位範圍沒收緊，因為內建技能有 0）。
- 隨機組合器：武器技「不花資源」那一檔改成最低 1（RNG 抽取次數不變）；傳說組合 `mana 0` 改 1。LLM 提議：`minimal_filler` 補最低花費。
- 重產 `client/src/render/fixtures/skill_icons.json`（組合器輸出變了）。測試中的假技能 `mana: 0`（3 個 engine 測試檔）改 `stamina: 1`。
- **內建技能違反最低花費（13 個，沒有改數值，交 PM）**：`skill_afterimage_vow`、`skill_bloodwake_stride`、`skill_gear_grapple`、`skill_gear_shield_wall`、`skill_gear_smoke_bomb`、`skill_kindred_flame`、`skill_mirror_cast`、`skill_mountain_mover`、`skill_overwatch`（武器技，其餘為法術技）、`skill_rallying_cry`、`skill_taunting_roar`、`skill_time_surge`、`skill_undying_oath`。多數是 0 法力、靠冷卻或源力或裝備電荷；請 PM／玩法 PM 決定是否調整。

## 3. 玩家模式隱藏開發者語氣說明＋匯出清單

- 新 `trpg.skillgen.option_player`：`draft_options` 對每個欄位與選項的說明做一次處理——**程式產生**（核心規則數值、參數名、ID 換中文、檔名與階段編號整段拿掉，沿用 `plainify`），仍含英文就改用原語的 `player_description`，都沒有就留空。原文放新欄位 `dev_description_zh`，`?dev=1` 才顯示（前端 `descOf`）。API 新增欄位：`dev_description_zh`、`later`、`show_when`（已重產 OpenAPI 與 `schema.d.ts`）。
- 既有 API 層過濾（`trpg.api.player_text.clean_text`，3-5c-2）把識別字直接刪掉，才會出現「超過 （初值 6）」；現在先在 domain 層由程式補值，`clean_text` 保留當最後保險。
- 內容資料：持續區域、消耗狀態、刻印、重置冷卻的參數說明直接改成玩家語氣中文（`skill_primitives.yaml`）。
- 匯出：`scripts/export_workshop_descriptions.py`（可重跑），已寫出 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_46ffc72c-28dd-48aa-9eb7-f1724ef32432\workshop_descriptions.csv`（UTF-8 BOM，`id,原文`，149 筆：原語 62、工坊程式組出的 76、條件 4、形狀 4、觸發 3）。id 格式 `原語.zone`、`形狀.line`、`工坊.effects.effects=shadowstep/landing`。

## 4. 巢狀效果原語隱藏

- 新旗標 `later`；`PrimitiveDef.nested_core`（YAML：消耗狀態、賭注、持續區域）與原語的 `effects` 型參數（擊殺時效果 `on_kill`）。玩家模式不列出，效果選單下方寫「這類效果之後開放：…」；`?dev=1` 全部列出。
- 骨架說明的核心清單也不再列被隱藏的原語。
- **3-48d 撤掉的方法**：把 `option_player.HIDE_NESTED_EFFECTS` 改成 `False` 即可（後端不再標 `later`；前端沒有寫死）。
- 注意：「消耗狀態」骨架的核心只有消耗狀態，玩家模式下該骨架暫時組不出技能（核心清單顯示「（無）」），3-48d 開放後恢復。

## 5. 法術技選效果前

- 縮放屬性：法術技（category=spell）選效果前只列智力／感知／意志，沒有預設；舊值不合法（例如從武器技換來的力量）時前端清掉讓玩家重選；選了效果後行為照舊（取範圍內第一個）。
- 形狀射程的「用武器射程」勾選只給武器技（`shape_param_fields(weapon_ok=…)`），標籤改成「用武器射程」（原本寫「用武器骰」）。

## 6. 刻印

- 標籤：下拉選單，只列有符文單字的標籤，顯示「獵紋」；不可自訂（驗證器 `rune.tag`）。其他「標籤」型參數（重置冷卻）也改成中文下拉。
- 說明補字、去英文（元素、標籤、持續回合數）。
- 對象：`inscribe` 加 `forbid_affects: [self, enemies, allies, all]`（資料驅動，工坊與驗證器共用）→ 只剩「格子」。內建 5 個刻印技能都沒寫 `affects`（預設格子），沒有違反。實戰引擎與既存技能的處理是 3-48e。

## 7. 追加：持續區域與條件顯示

- ① 持續區域說明整段隱藏（nested_core）並列入匯出清單；缺字（zone_limit_per_owner）由程式補值。② 錨點、觸發時機等欄位說明已中文化。③ 玩家模式隱藏該原語。
- ④ 新欄位 `show_when`（`PrimitiveParam.show_when`，資料驅動，前端 `fieldShown`）：持續區域的「速度」只在錨點＝移動時顯示。**掃描其他原語的條件式欄位**（說明含「為…時」「才」「填了」）：消耗狀態的「層數種類」（scale＝stacks）、重置冷卻的「標籤」（which＝tag）、召喚的「每隻強度」（count＝2）——都已加 `show_when`。沒有條件式但「兩者擇一」的：刻印的元素／標籤（schema 檢查，說明已寫明）；爆炸的元素（有＝爆炸、無＝治療，是選填不是條件）。其他 `required_when`（傷害元素看類別）本來就由後端決定欄位。

## 8. 追加：刻印卡片「持續 1 輪」與匯出 YAML 的 duration 不同

- 重現步驟：開 `?dev=1`，把草稿設成刻印技能（duration 4），用真實輸入框「4→1」、再「1→9（超出範圍）」、API 層「1→4」「4→1」各一次，每次同時看卡片文字、進階 YAML 文字、localStorage 草稿、下載匯出。
- 結果：**YAML、草稿、輸入框當下立刻一致；卡片預覽落後約 250 ms（即時檢查的去抖動）才更新，之後一致**。匯出是用目前草稿向伺服器要的，與卡片無關；伺服器無狀態，API 測試涵蓋兩種順序都一致（`test_rune_duration_card_and_export_follow_the_draft_in_both_edit_orders`）。匯出檔名含草稿內容雜湊，不同 duration 檔名不同，不會是瀏覽器覆蓋同檔名。持續回合、骰子、射程共用同一個編輯路徑（`setPath`＋`replaceItem`），行為相同。
- 推測：使用者看到的是「更新中」的舊卡片（`pending` 時仍顯示上一張），或玩家模式下匯出前的舊檢查結果。沒有找到永久不同步的路徑。
- 預防（小改）：即時檢查更新中時，卡片預覽變淡、匯出按鈕暫停，避免看到的和匯出的不同。

## 全面掃描清單（流程改善 E）

| 位置 | 掃描／改動 | 結果 |
|---|---|---|
| 步驟 1 骨架 | 說明含英文？ | 玩家版無英文（掃描測試）|
| 步驟 2 基本設定 | 類別換法術技時武器需求、縮放屬性殘留 | 前端對齊；步驟列不打勾；法術技縮放不列體能屬性 |
| 步驟 3 形狀 | 形狀說明（line、ring、cone、square3、chain、allies_in_radius）含參數名；「用武器射程」 | 程式把參數名換中文；法術技不列武器射程 |
| 步驟 4 效果 | 59 種原語說明、參數說明、骨架核心清單、巢狀 | 改玩家版或 player_description；巢狀 3 種原語＋擊殺時效果隱藏；`show_when` 4 處 |
| 步驟 5 條件 | `self_hp_below`、`on_own_rune`… 說明含英文 | 程式處理；匯出 4 筆 |
| 步驟 6 代價 | 最低花費 | 說明＋檢查 |
| 步驟 7 稀有度 | 卡住與「problems」 | 列原因、回到第 N 步 |
| 步驟 8 變奏、修正規則 | 「可套用：all_attacks…」含 ID、變奏 id 範例英文 | 程式處理（掃描測試涵蓋）|
| 匯出／預覽 | 更新中的卡片 | 變淡、暫停匯出 |
| 確認沒問題 | 武器技縮放鎖定、第二屬性、技能名稱、階級 | 無改動 |

自動掃描：`tests/skillgen/test_player_text.py` 現在也掃欄位／選項／步驟的 `description_zh`（無英文詞）；`tests/skillgen/test_workshop_48c.py` 新增 10 項（稀有度原因、殘留武器需求、法術技選項、最低花費、組合器 300 種子、刻印下拉與只列格子、驗證器 `rune.tag`、`later`／`show_when`、說明匯出）；vitest `client/src/workshop/player48c.test.ts`（說明、later、show_when、conformScaling 新行為、數值連續修改）。

## 驗收結果

- pytest：`tests/skillgen tests/content tests/api tests/narrative tests/llm tests/test_architecture.py` 3230 通過（重產技能圖示 fixture 後）；`-m "slow or not slow" tests/cli` 148 通過；另跑 `tests/roguelite sim engine shared` 與根目錄腳本測試全過。
- vitest 919 通過、1 失敗（`floatCardRule` 抓到 `dev/layoutSmoke.ts`，3-48 報告已記錄、非本段造成）；build 通過；ruff、format、mypy（665 檔）、lint-imports 通過。
- 排版煙霧檢查（先 `localStorage.clear()`）：1600×900、800×600、1600×900 shortBottom 全 PASS。預覽伺服器用 8014，已用自己的 PID 結束。

## noqa

無。

## 待 PM 決定

1. 內建技能 13 個違反最低花費（見 §2），要調數值還是列為例外？
2. 最低花費目前只在檢查回報，代價步驟不會因為它變成「未完成」（避免擋住既有流程）；要不要改成必填？
3. 玩家模式下「消耗狀態」骨架暫時組不出技能，直到 3-48d。
4. `floatCardRule` vitest 失敗（`dev/layoutSmoke.ts` 含 `role=tooltip`）仍未處理。
5. 匯出清單裡「工坊.*」那些程式組出的說明（如「形狀 單位與落點：…」）是程式拼出的，玩法 PM 改寫時要同時改程式或內容。
