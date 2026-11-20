# X10-3a 報告：×10 收尾（後端）

依據：`docs/phases/PhaseX10-3a計畫.md`、`PhaseX10-2b報告.md`（含開發 PM 裁定）、`docs/design/05-戰鬥.md` 5.4.1，以及途中開發 PM 轉來的玩法 PM 補充兩條（回魔藥 100；資源下限：法力、耐力、反噬、免死 10，冷卻與 AP 1）。
基準：開工時 `git merge main`（`0f89af3cc`）；第 1 項之後再 merge 一次 main（`03d38b886`，只有文件，拿設計文件的新單位用字對照）。分支 `worktree-agent-a0847cb8d9df88c6c`，沒 push。
沒改 `docs/design/`、`config/`；沒碰 `saves/`、`saves_backup/`（測試都用暫存資料夾）；沒跑全量、沒用 `-m ""`、沒試數值。`client/` 只依開發 PM 裁定重產了 `glossary.json`。

## 1. 交付與 commit

| # | 項目 | commit |
|---|---|---|
| 1 | 舊單位存檔直接拒絕 | `bd0b8065c` |
| — | merge main（文件） | `d0c156f30` |
| 2 | 說明文字的量類數字（含重產 `glossary.json`） | `5d885e618` |
| 3 | `tests/skillgen/helpers.py` 耐力 8→80 | `014c43d08` |
| 4 | 報告 | （本檔） |

## 2. 舊單位存檔拒絕（交付項目 1）

判斷：存檔寫入時記下目前內容的 `core.quantity_scale`；讀檔時**沒有記或和目前內容不同**，就當成數值改版前的存檔拒絕。

### roguelite 存檔（`trpg-run/13`，格式版號不升）
- `RunSave` 多一個選填欄位 `quantity_scale`（舊存檔沒有＝`None`）。
- `check_quantity_scale(library, save)`：不相符時拋 `SaveFormatError`，訊息 **「這是數值改版前的存檔，已經不能使用，請開新一輪。」**（`OLD_UNIT_SAVE_NOTICE`）。
- `write_save` 不收沒記倍率的存檔（拋 `ValueError`），所以新存檔一定會寫。寫入的地方：API `RunSession.to_save`、CLI `run new`、`run auto --save`（新的 `_new_save`）。
- 讀取的地方：
  - API `POST /api/runs/load`：回 422，`{"detail": "<訊息>"}`（`SaveFormatError` 原本就對應 422）。
  - API `GET /api/runs/saves`：跳過舊存檔（和原本「讀不了的略過」一致）。
  - CLI `run show`、`run auto --from`：stderr 印「錯誤：<訊息>」，結束碼 1。
- `loads_save` 本身不檢查倍率（它沒有內容庫；格式層的往返測試照舊）。檢查放在每個有內容庫的讀檔入口。

### 大世界角色存檔（`trpg-char/15`，格式版號不升）
- 倍率記在**存檔檔案**的頂層鍵 `quantity_scale`，**不是** `CharacterState` 的欄位。原因：`dumps_char` 也拿來比對重播結果和算凍結雜湊，加欄位會動到 `season_policy` 的欄位分類和凍結夾具。
- `dumps_char_save(char, quantity_scale=…)` 寫檔，`loads_char_save(text, quantity_scale=…)` 讀檔並檢查。不相符時拋 `WorldSaveFormatError`，訊息 **「這是數值改版前的角色存檔，已經不能使用，請建立新角色。」**（`OLD_UNIT_CHAR_NOTICE`）。API 回 422。
- `WorldStore` 的 `character()`、足跡索引、`_save_char` 改用這兩個函式。足跡索引原本就會略過讀不了的檔。
- `loads_char` 會丟掉這個鍵、不做檢查，給季末重置用：它要讀舊角色寫進編年史再刪掉，如果拒絕舊角色，重置就做不下去。
- 大世界沒有讀角色存檔的 CLI 命令，所以只有 API 會顯示提示。

### 測試
新檔 `tests/test_x10_saves.py`（9 個）：
- 訊息文字。
- roguelite：沒有欄位、`None`、倍率 1 都會被拒；新存檔可以讀；`write_save` 不收沒記倍率的存檔。
- CLI：`run new` 寫入 10，`show` 讀得到；刪掉欄位後 `show` 和 `auto --from` 都印提示、結束碼 1。
- API：讀檔 200；改成 1 之後 422 並帶訊息；存檔列表跳過舊存檔。
- 大世界：建角色後檔案記 10；重開 store 讀得到；倍率 1 或沒有鍵都會被拒（函式與 API 422）；`loads_char` 照讀。

以下既有測試原本直接寫存檔、或寫角色檔給 store 讀，這次改成記倍率：
- `tests/roguelite/test_race_start.py`
- `tests/roguelite/test_save.py`
- `tests/cli/test_run_cli.py`（`RunSave` 加 `quantity_scale`）
- `tests/api/test_offer_prefetch.py`
- `tests/api/test_world_field_things.py`
- `tests/api/test_world_pregen.py`（`dumps_char_save`；`test_world_pregen_schedule` 共用它的 `_store`）

## 3. 說明文字（交付項目 2）

掃法：腳本走過 `content/` 的所有 YAML／JSON 字串（`name_zh` 除外），挑出同時有中文、數字和量類用語的，共 376 筆。逐筆對照資料或程式的實際值判斷。`content/` 裡的非 YAML 檔只有 `README.md`，沒有命中。YAML 註解不算說明文字，沒改。

### 改了的（14 處）

| 檔 | 欄位 | 舊字 | 新字 | 依據 |
|---|---|---|---|---|
| `world/items.yaml` | `item_mana_potion.description_zh` | 戰鬥中回 10 法力 | 戰鬥中回 100 法力 | 效果 `restore_resource amount: 100`（玩法 PM 補充 1） |
| `reactions.yaml` | `block.description_zh` | 消耗 10 耐力 | 消耗 100 耐力 | `stamina_cost: 100` |
| `statuses.yaml` | `undying.description_zh` | HP 留在 1 | HP 留在 10 | 免死下限 1 × scale（handlers） |
| `skill_primitives.yaml` | `nested_only_effects[self_damage_of_hit].description_zh` | 不會讓 HP 低於 1 | 不會讓 HP 低於 10 | `_cap_backlash` 下限 1 × scale |
| `skill_primitives.yaml` | `gamble.description_zh` | 反噬傷害不會讓他的 HP 低於 1 | …低於 10 | 同上 |
| `workshop_text.yaml` | 原語.gamble 的 `source`（2 筆，與原文同步） | 同上 | 同上 | 同上 |
| `workshop_text.yaml` | 原語.gamble 的 `player`（2 筆） | 反噬不會讓你的 HP 低於 1 | …低於 10 | 同上 |
| `flash_templates.yaml` | `cost_light.summary_zh` | AP 已是 1 時改成冷卻或資源 −1（每項最少留 1） | AP 已是 1 時改成冷卻 −1 或法力、耐力 −10（冷卻最少留 1，法力、耐力最少留 10） | `_light_cost_drafts` 的 `cost_floor`：法力、耐力一格 10、下限 10；冷卻 1（玩法 PM 補充 2）。「AP −1（最少 1）」不變 |
| `flash_templates.yaml` | `cost_blood.summary_zh` | 法力或耐力只花 1 點 | 法力或耐力只花 10 點 | `blood_price` 留 1 × scale |
| `workshop.yaml` | `opponents[dummy].description_zh` | 木樁（HP 300） | 木樁（HP 3000） | `training_dummy.max_hp: 3000` |
| `world/newcomer.yaml` | `attribute_notes.str` | 14 起撞擊傷害多 1、受到的少 1 | 140 起撞擊傷害多 10、受到的少 10 | `attribute_perks` base 100 + step 40；`collision_*` per_tier 10 |
| `world/newcomer.yaml` | `attribute_notes.int` | 14 起你產生的表面多 1 回合 | 140 起…多 1 回合 | 門檻 140；回合數不變 |
| `world/newcomer.yaml` | `attribute_notes.wis` | 14 起看得見更遠… | 140 起… | 門檻 140 |
| `world/newcomer.yaml` | `attribute_notes.wil` | 14 起控制抵抗 +1 | 140 起控制抵抗 +10 | `control_resist` per_tier 10 |
| `world/events/cloud_ridge.yaml` | 骨架 14 線頭 `shards_to_ashen.on_expire_zh` | 灰燼之心第 1 階段護甲 +1 | …護甲 +10 | `encounters/ashen_waste.yaml` `ashen_heart_hardened amount: 10` |

上表是 14 處說明文字。`workshop_text.yaml` 那兩列各有 2 筆，所以 git 實際改了 17 行。

前端夾具：`client/src/battle/fixtures/glossary.json` 用 `scripts/export_client_fixtures.py` 重產（開發 PM 裁定 A），和文字放在同一個 commit。
- 變了 2 行：免死、格擋。
- 同一支腳本也會寫 `unitDolls.json`、`raceLooks.json`、`skillCards.json`，這三個內容沒變。

### 看過、不改的（判斷為不變類或和程式一致）
- 冷卻、AP 的「最少 1」「留 1」（輕巧的「AP −1（最少 1）」、`tuning_fields` 的射程「結果至少 1」）：玩法 PM 補充 2，不動。
- 復活「以 hp_permille‰ 的最大 HP（至少 1）」（`skill_primitives` 原語 revive 與參數、`workshop_text` 兩筆 source）：程式 `skills/revive.py` 111 仍是 `max(1, …)`，是「活著」的下限，X10-2b 第 3.4 節已裁定不改。所以文字和程式一致。
- 姿態「維持費 ±1」（`stance_cost_light`／`heavy`、`tuning_fields` 的 0～2）：技能的 `stance_upkeep` 是點數，不放大，乘上 `forms.yaml` 的 `stance_upkeep_*`（那邊已 ×10，見 `scripts/x10/fields.yaml` 261）。
- 骰子寫法「回 2d6 HP」「4d6」：骰面在擲骰時才 ×10，骰子寫法本身不是量。這裡**沒改**，列為待決 2。
- 百分比、‰、格數、回合、層數、d20 修正（「判定 +1」）、物品數量（「封印鑰匙 +5」「每週限購 5 個」）、等級、AP、預算點數、縮放係數「×0.5」：都是不變類。
- `tests/world/frozen_replay/events.json` 裡有一份「護甲 +1」的文字：那是凍結的輸入夾具，不改。

### 測試
新檔 `tests/test_x10_texts.py`（8 個）：每一條都從資料讀出實際的值，再比對說明文字裡的數字。比對的值有：
- 回魔藥的 `amount`、格擋的 `stamina_cost`
- 木樁 `max_hp`
- 屬性常駐的門檻和每階值
- 灰燼之心旗標的 `amount`
- 免死、反噬、輕巧、以血支付的倍率

## 4. 測試小工具（交付項目 3）
- `tests/skillgen/helpers.py` 基準技能 `cost` 耐力 8 → 80，docstring 改成「耐力 80」（比例 80.4% 本來就是照 80 算的）。
- `test_budget.py` 的手算案例 1 和「預算是精確分數」：原本要明寫 `cost={"stamina": 80, …}` 蓋掉舊預設，現在直接用預設的 `skill()`。手算案例的斷言沒動（折抵 120‰、比例 45/56），預設不是 80 就會失敗，這就是這一項的回歸測試。
- `test_validate.py` 的 `COST` 註解改成「預設已是新單位 80」，值不變。
- 用到 helpers 的 29 個測試檔全部重跑：1504 passed，沒有其他測試因此改數字。
- 沒改：`test_self_costs.py`（4 處）、`test_stamina_cost.py`（1 處）自己明寫的 `stamina: 8`。這些測的是規則（武器技不能自沉默、法術不能花耐力），和量無關，也不是 helpers 的預設，不在這項的範圍。列為待決 4。

## 5. 不變比對

- **做法**：同一份程式（`014c43d08`），內容分兩次跑：
  - 基準：`git archive 0f89af3cc content`，用 `TRPG_CONTENT_DIR` 指過去；
  - 目前：這段改過的內容。
- **範圍**：同 X10-2a、2b 的 78 場：
  - 15 張正式地圖 × 種子 1、7；
  - `open_plain` 種子 3 × 8 個 build；
  - 4 張頭目圖 × 種子 3～12。
- **比對內容**：`--log-json` 整份加文字輸出。
- **排除**：
  - `ruleset_hash`；
  - 內嵌規則包裡的說明字串欄位（`description_zh` 等）。這次只改了說明字串，所以這些欄位本來就會不同。
  - 文字輸出的「寫入路徑」那一行。
- 結果：**`battles=78 events=26446 different=0`**。事件總數和 X10-2b 換算後相同。
- 沒排除前，78 份 JSON 全部不同，差在雜湊和內嵌的免死、格擋說明（抽查 `open_plain_s1` 確認過）。

第 1、3 項沒有改到戰鬥：第 1 項只動存檔讀寫，第 3 項只動測試。

## 6. 檢查

最後一個程式 commit 是 `014c43d08`，之後只加了這份報告。

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（全專案，1735 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| 不變比對 78 場 | different=0 |
| 分目錄 `pytest -n 8`（預設標記） | 全部 0：api 1336（1 skipped）、bot 67、cli 148、content 3166、engine 5120、llm 495、narrative 475、roguelite 279、server 77、shared 72、sim 180、skillgen 4634（7 skipped）、world 1328、頂層 198 |
| `pytest -n 8 -m slow tests/cli` | 0（44 passed） |
| 前端 `vitest run`（全部；共用設定 `src/test/setup.ts` 會載入 glossary） | 0（387 檔、4788 passed） |

worktree 裡沒有 `client/node_modules`，跑 vitest 前先 `corepack pnpm -C client install --frozen-lockfile`（node_modules 在 .gitignore 內，沒有進 commit）。

### 快照預測與實際
| 檔案 | 預測 | 實際 |
|---|---|---|
| `client/.../glossary.json` | 會變（狀態、反應的說明） | 變 2 行（免死、格擋），已重產 |
| `client` 其他手做夾具（見待決 1） | 會留著舊字（沒有 Python 測試檢查） | 同預測，沒動 |
| CLI 輸出雜湊、`llm` prompt 快照、OpenAPI、parity | 可能變（如果輸出帶到這些說明） | 都沒變，相關測試全過，沒有重產 |

## 7. 版號
- `SAVE_FORMAT`（`trpg-run/13`）、`CHAR_FORMAT`（`trpg-char/15`）都**不升**：
  - 新欄位是選填的；
  - 舊存檔本來就要整份拒絕，不需要靠版號轉換。
  - 季末重置、凍結夾具也都照原格式讀。
- `LOG_FORMAT`、`PROMPT_VERSION`、OpenAPI 都不變。

## 8. 待 PM 決定
1. **前端夾具裡的舊字**（交給 X10-3b，這段沒動）：
   - `client/src/dev/fixtures/flashChoice.json`：「改成冷卻或資源 −1（每項最少留 1）」×3（輕巧的舊說明）
   - `client/src/workshop/fixtures/arena.json`：「木樁（HP 300）」×1
   - `client/src/workshop/fixtures/options_charge_effects.json`：「HP 留在 1，」×1（免死）
   - `client/src/workshop/fixtures/options_charge_full.json`：「HP 留在 1，」×2（免死）
2. **說明文字裡的骰子寫法**（`world/items.yaml` 治療藥水「回 2d6 HP」「4d6」，技能卡也一樣）：骰面在擲骰時 ×10，骰子寫法不是量。照最保守的做法沒改。玩家看到「2d6」可能以為只回 2～12，這要和 X10-3b 的骰子顯示一起決定。
3. **姿態「進入代價 ±1」的程式步距沒跟著 ×10**（規則類，發現的，沒改）：
   - 程式：`skillgen/flash_ops.py` 1124 `_entry_cost` 的法力、耐力一次只加減 **1**，下限也是 1，沒有用 `cost_floor`。X10-2b A2 改的是 `cost_cuts` 和完整技能，這條路漏了。
   - 結果：閃現「進入代價 −1」「沉勢」一次只改 1 點法力或耐力，等於舊單位的 0.1。
   - 文字：`flash_templates.yaml` `stance_enter_light`／`heavy` 的「法力或耐力 −1（最少留 1）」「+1」，**和目前程式一致，所以沒改**。
   - 如果要改：程式步距、下限改成 1 × scale，文字跟著改成 10。這會改到閃現輸出，parity 夾具要重產。
4. `test_self_costs.py`、`test_stamina_cost.py` 測試輸入明寫的 `stamina: 8`（舊單位，測的是規則、和量無關、測試都過）：要不要一起改成 80？這段照範圍沒動。
5. 世界裡如果還有舊角色檔，要列出全部角色的端點（留言板名字、郵件、`/api/world/characters` 清單等，會逐一呼叫 `character()`）遇到舊檔會 422。這和原本「角色檔格式壞掉」的行為相同；開發 PM 轉述舊存檔已季末重置，所以照現狀。如果需要「列表時略過舊角色」，要另外改。
6. 程式的 docstring、註解裡還有舊單位的說法：
   - `engine/events/rules.py` 122「HP 留在 1」；
   - `skillgen/complete.py` 14、`flash_ops.py` 719「每項最少留 1」；
   - `rules/core.yaml` 註解「14＝1 階」、`units/training_dummy_moving.yaml` 註解「HP 300」、`newcomer.yaml` 註解「HP 300」。

   規格只要求改 `content/` 的說明文字，這些沒動。

## 9. 平衡疑慮
- 沒有。這段沒有改到戰鬥數值（不變比對 different=0）。

## 開發 PM 裁定（2026-11-20）

合併：`Merge X10-3a`（--no-ff）。

待決 6 件：
1. 交給 X10-3b，連同前端夾具裡的舊字一起改。
2. 交給 X10-3b，道具說明的骰子照卡片同一套規則改成範圍，例如「回 20–120 HP」。
3. **要修**：這是 X10-2b 漏換的地方。姿態「進入代價 ±1」「沉勢」的法力、耐力步距和下限都改成 × scale，程式和 `flash_templates.yaml` 的文字一起改，parity 夾具照程序重產。另開小段 X10-3c。
4. 不改。那兩個測試的輸入是規則測試自己寫的，和量無關。
5. 接受。舊角色檔已經季末重置清掉。
6. 交給 X10-3c，掃程式的 docstring 和 YAML 註解裡的舊單位說法，只改文字。
