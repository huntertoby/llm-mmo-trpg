# Phase 3-48d 報告：工坊開放一層巢狀效果

規格：`docs/phases/Phase3計畫.md` 第 54 節。

## 做了什麼

- **新模組 `trpg.skillgen.option_nested`**：替四種原語的 `effects` 型參數補上子效果選項（`NESTED_PARAMS`，類型清單直接取自 `skills.py` 的 `CONSUME_THEN_TYPES`／`ZONE_EFFECT_TYPES`／`GAMBLE_BRANCH_TYPES`／`ON_KILL_TYPES`，與驗證器同源）。
  - 消耗狀態 `then`：傷害、治療、護盾、施加狀態（1–2 個，不自帶對象）。
  - 持續區域 `effects`：同上（1–2 個，對象由區域的 `affects` 決定）。
  - 賭注 `win`／`lose`：傷害、治療、護盾、施加狀態、傷害倍率、反噬自傷（各 0–2 個，可自選對象，「自己」用於失敗的反噬）。
  - 傷害的擊殺時效果 `on_kill`：返還行動點、重置本技能冷卻、治療、護盾、施加狀態（1–2 個，對象一律是施放者；狀態只列有益的）。
  - **只開一層**：子效果的欄位拿掉所有 `effects` 型欄位與只屬於技能自己傷害效果的欄位（爆骰、縮放、吸血、聖光雙效、擊殺時效果）。
- 撤掉 3-48c 的隱藏：移除 `option_player.HIDE_NESTED_EFFECTS` 與 `_hide_nested`，`later` 不再被巢狀原語設定（欄位保留給之後的功能）；骨架說明的核心清單恢復列出消耗狀態等。「消耗狀態」骨架在玩家模式重新組得出來。
- 前端不需要改：`EffectsField` 本來就遞迴處理 `choices` 不為空的情況，只剩「沒有選項才顯示不展開」的保險文字。新增 vitest 檢查巢狀列表的加入、上限、移除、取代。
- **預算**：完全沿用預算器現有算法（消耗狀態的 then × 倍率 × 濺射 × 需先有狀態、賭注的期望值、區域的輪數與時機、擊殺時 × 預估擊殺率），沒有新公式。
- **玩家文字**：子效果的說明沿用 `option_player`（原語的說明本來就有玩家版）；檢查文字的巢狀欄位名（then、win、lose、dice、type、傷害倍率、反噬自傷、返還行動點、重置本技能冷卻）補進 `plainify` 的中文表；`test_player_text.py` 新增 `test_nested_level_texts_have_no_english_identifiers`（四種原語各一份正常與故意寫錯的巢狀草稿）。

## 順手修的缺口（需 PM 知悉）

- **縮放屬性的主題只看最上層效果與 `then`**（`ScalingTheme.matches_effect`）：工坊沒有標籤欄位，用工坊組「持續區域（裡面是火焰傷害）」或賭注分支的傷害，會被判成「沒有法術主題」，只能選力量／敏捷／體質。內建技能靠 `tags` 才躲過。已改成也看賭注 `win`／`lose` 與區域 `effects`（`skill_scaling.py` 的 `_NESTED_GROUPS`）。`tests/content`、`tests/skillgen` 全過，內建技能的允許屬性未變。擊殺時效果（`on_kill`）不納入（它是額外獎勵，不是主效果）。
- 玩家文字：原本錯誤訊息裡的「不可指定 dice」現在顯示「不可指定 骰子」（`test_workshop_check.py` 的斷言同步更新）。

## 行為一致測試（`tests/skillgen/test_workshop_48d.py`，16 項）

- 選項：四種原語的巢狀欄位都有選項、`max_count` 2、子效果不再巢狀、類型清單符合規則（含賭注專用的倍率與自傷）、「消耗狀態」骨架組得出來。
- 每個子效果選項（`fill_fields` 最小填法）塞進對應範本草稿，驗證器不會因為選項本身出現 schema 錯誤。
- 每種巢狀原語各組一招（草稿 → `check_draft` 合法且預算算得出來 → `skill_to_yaml` → `skill_from_yaml` → `validate_skill`），再載入戰鬥：消耗狀態的 then 真的造成傷害並移除狀態；持續區域觸發並傷害敵人；賭注成功／失敗兩個分支都結算（失敗有反噬、成功傷害 ×2.4）；擊殺時返還 AP 並治療施放者。

## 內建瀏覽器實測（埠 8017，已關閉）

在工坊用「消耗狀態」骨架：法術技、智力、2 階、單體射程 4 → 效果選「消耗狀態」，狀態選燃燒，「消耗後的效果」區出現傷害／治療／護盾／施加狀態四個選項（沒有對象欄位）→ 加傷害，3d6 火焰 → 代價法力 6、冷卻 2 → 稀有。即時檢查「合法：可以匯出，也可以裝上試玩」，72.3%・合格，技能點數 7.35／可用預算 10.17，卡片預覽「消耗目標身上的『燃燒』，然後 3d6＋智力加成的火焰傷害」。排版煙霧檢查（先 `localStorage.clear()`）1600×900、800×600、1600×900 shortBottom 全 PASS。

## 驗收

見下方「檢查結果」。

## 待決

- 賭注分支的「傷害倍率」「反噬自傷」是賭注專用效果（不是原語），名稱與說明是我寫的（`option_nested._SPECIAL`），請玩法 PM 確認措辭。
- 子效果的狀態選單：區域／消耗後的效果沿用主效果的規則（非有益限制只在核心是光環類時才套）；擊殺時效果（對象一律是施放者）只列有益狀態——這是保守做法，驗證器本身沒有這個限制。
- 巢狀欄位文字說明來自原語的 `description_zh`／`player_description`（3-48c 的玩家版規則），「濺射距離 範圍 1–1」這類單一值欄位維持原樣。

## 檢查結果

- pytest：`tests/skillgen tests/content tests/api tests/engine tests/test_architecture.py` 5700 通過；`-m "slow or not slow" tests/cli` 148 通過。
- vitest 933 通過（新增 `nested48d.test.ts` 4 項）、build 通過、ruff、format、mypy（673 檔）、lint-imports 通過。
- 排版煙霧檢查三個情況全 PASS。
