# Phase HC-3 報告：前端寫死的規則改由後端提供

基準：開工時 `git merge main`（`6c887ed7b`）。分支 `worktree-agent-a608a77a896f60d14`，沒 push。
沒動 HC-4a 的檔（`content/` 的 rules／battle／forms／parts／equipment／item_budget.py、`core.yaml`、`tuning_fields.yaml`、`classes.yaml` 的 py 區）；後端只改 `api` 的 schema 與 view 層。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| a 閃現與技能欄 | `26ef00182` | `/api/glossary` 加 `rules`；`flash_rules` 改必有；拿掉 FALLBACK、SLOT_LIMITS、SOURCE_MAX、COMPLETE_BONUS_PERMILLE、`?? 2`、詞條重複的 `>= 2` |
| b 大世界與工坊 | `3e4c4cbc8` | 背包 6×5 備用值、WALK_MAX 拿掉；工坊預設種子數與上限改讀 API |
| c 營火夾具換新單位 | `4f1c314dc` | 新腳本 `scripts/export_campfire_fixture.py` 從真的 run 產生；`flashChoice.json` 用既有腳本重產 |
| 報告 | 本 commit | |

每個 commit 前都跑過 ruff、format、mypy、lint-imports、`classify.py --check`、tsc、vitest 全部、build。

## 2. 每項改了什麼

### 2.1 閃現與技能欄（a）

- **後端（api 層）**：
  - `schemas.py` 新增 `GameRulesOut`（`source_max`、`skill_slots`、`start_keywords`、`complete_budget_permille`）與 `SkillSlotsOut`，掛在 `Glossary.rules`（必有）。
  - `glossary.py` 的 `_game_rules`：值全取自 content（`core.source_max`、`core.skill_slots`、`roguelite.start.keywords`、`flash.rules.complete.budget_permille`）。
  - `run_schemas.py`：主角的 `flash_rules` 從 `| None = None` 改必有（presenter 本來就一定給）。
- **前端**：
  - `battle/glossary.ts`：`setGlossary` 一併存 `rules`；`gameRules()` 取用，還沒載入就丟錯（App 先載入對照表才畫畫面）。
  - `run/flash.ts`：刪 FALLBACK 與 `rulesOf`，各函式直接吃伺服器的 `flash_rules`；`flashCountText` 沒拿到規則時只寫「已閃 N 次」。`COMPLETE_INTRO` 改成 `completeIntro()`，加成讀 `rules.complete_budget_permille`。
  - `run/flow.ts`：`SLOT_LIMITS` 改 `slotLimits()`（讀 `rules.skill_slots`）＋`SLOT_KINDS` 順序表；`loadout.ts`、`LoadoutEditor`、`RunHeroPanel` 跟著改。
  - `ui/SkillCardView.tsx`：源力圓點格數讀 `rules.source_max`。
  - `run/StartPicker.tsx`：`keyword_count` 選項還沒載入時改讀 `rules.start_keywords`；觸發關係的「至少 2 招」改寫 `> 1`（兩招之間的關係，不是規則數字）。
  - `gear/affixStatus.ts`：「重複」改寫成「同 id 不只一條」（`> 1`）；非數值類只有第一條生效是引擎 `diminish` 的結構，不是門檻。
  - 不載入對照表的開發頁（`panelGallery`、`flashChoiceGallery`、`itemGallery`）用 `glossary.json` 快照 `setGameRules`；其他開發頁本來就 `setGlossary`。另抽查 9 個開發頁，console 沒有錯誤。
- **備用值**：前端已沒有閃現、技能欄、源力的備用值。開發頁用的 `glossary.json` 由 `export_client_fixtures.py` 產生，`test_client_fixtures.py` 檢查沒過期。
- **測試**：新增 `tests/api/test_hc3_game_rules.py`（3 個：rules 值等於 content、端點有欄位、`flash_rules` 必有）；`test_hardcoded_scan.py` 的前端抽查換成還在的兩條，另加「這 5 個檔不再有 config 數字」；vitest 兩處改成用夾具或對照表的值。

### 2.2 大世界與工坊（b）

- **背包**：`slots_max` 由 `bag_slots`（`ge=1`）來，一定 > 0，`BAG_COLS * BAG_ROWS` 的備用分支拿掉。剩下的 `BAG_COLS = 6` 是每列畫幾格（hud.png C 案），改判 layout（見待決 2）。
- **walk**：`FieldView.walk_max_steps` 在 TS 已是必有；刪 `WALK_MAX`，`chunkPath` 的上限改必填，不合法時（不該發生）一格一段。
- **工坊**（對齊 `api/tuning/schemas.py`）：
  - `TuningSimOptions` 加 `ratio_max_seeds`（`MAX_RATIO_SEEDS`）、`max_maps`（`MAX_SIM_MAPS`）、`small_sample`（`SMALL_SAMPLE`），`ratio_default_seeds` 拿掉 `= 50` 預設改必有；`TuningStatus` 加 `max_group`（`MAX_GROUP`）。全在 `service.py` 用既有常數填，沒有新數字。
  - 前端：`SMALL_SAMPLE`、`MAX_MAPS`、`MAX_GROUP`、比值的 250 與 `?? 50` 改讀上面欄位；「小」規模的 3 種子、24 場改讀 `default_seeds`、`map_default_seeds`。`simCell`／`row`／`simRows`／`mapSimRows`／`ratioSeedsProblem`／`ratioEstimate`／`groupProblem` 多一個參數。
  - 新增 `tests/api/tuning/test_hc3_limits.py`（2 個）；vitest 的手寫選項補上新欄位。
- **hud 鐘點沒改**：見待決 1。

### 2.3 營火夾具（c）

- **腳本** `scripts/export_campfire_fixture.py`：第一個開發起始包（`dev_blaze`）、種子 25，AI 代打（閃現策略 `mixed`）到第 3 場後的營火，用 `run_response`（和 API 同一個函式）輸出整份 `RunResponse`。重跑兩次輸出相同。
  - 種子是掃 1～59 挑的：要同時有「閃到第 3 次的一招」「完整技能」「上場用過、現在可以閃的一招」「帶詞條的裝備」「背包裡有東西」。腳本會檢查這幾項，內容改過不符合就結束碼 1。`all` 策略會把能閃的都閃掉，所以用 `mixed`。
  - 唯一改的是靈感點設 8（代打花光了；比照 `export_flash_choice_fixture.py` 重閃組的寫法），營火的閃現、重閃鈕才是能按的樣子。
- **結果**：技能卡、裝備詞條（例「智力 +40」「火焰抗性 +6%」）、主角數值全是現在的單位；舊的「最大 HP +12」不見了。
- **和舊夾具不同的地方**：技能換成這一輪的（灼燃・引火彈、烙印、火球、火焰爆、毒素・位移）；背包只有 1 件（換下的火焰法杖，沒有詞條），帶詞條的裝備在身上。
- **`flashChoice.json`**：照原本的 `export_flash_choice_fixture.py` 重產（主角沿用新的營火夾具）。
- vitest 沒改任何斷言就全過。

## 3. 截圖（`docs/art/shots/hc-3/`，無頭 Chrome `--mute-audio`、網址帶 `mute=1`）

| 項目 | 前 | 後 | 結果 |
|---|---|---|---|
| a 營火（`panel-gallery.html#campfire`：技能欄「主動 4/6」、閃現籌碼、技能卡） | `a_campfire_before.png` | `a_campfire_after.png` | 兩張檔案逐位元相同 |
| b 背包（`item-gallery.html?set=scene`：6×5 格、23／30） | `b_bag_before.png` | `b_bag_after.png` | 兩張檔案逐位元相同 |
| c 營火夾具重產 | `a_campfire_before.png`（舊夾具） | `c_campfire_after.png` | 換成新的 run（預期會變） |
| c 選變體開發頁 | （沒拍） | `c_flash_choice_after.png` | 主角換了；畫面上的點燃斬選項不受影響 |

## 4. 檢查（最後一個程式 commit `4f1c314dc`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1747 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `classify.py --check` | 0（沒歸類 0） |
| OpenAPI 重產（`export_openapi.py` ＋ `gen:api`） | 0 |
| `pnpm typecheck`（tsc） | 0 |
| vitest 全部 | 0（392 檔、4818 個） |
| `pnpm build` | 0 |
| `pytest -n 8 tests/api` | 0（1345 passed、1 skipped；含 OpenAPI 快照、client 夾具、tuning） |
| `pytest tests/test_hardcoded_scan.py tests/test_architecture.py` | 0（39） |

- 跑 pytest 時 `tests/api/tuning` 和 `tests/api/test_*.py` 一起列在同一次指令，`test_hc3_game_rules.py` 會找不到 `client` fixture；分開跑或跑整個 `tests/api` 都正常（收集順序的問題，和這段無關）。

## 5. 筆數（`classify.py --stats`）

- 前端 config：56 → **26，全是 todo**。
  - done：`ts-flash-fallback`、`ts-slot-limits`、`ts-source-max`、`ts-start-keywords`、`ts-affix-duplicate`、`ts-walk-max`、新增的 `ts-tuning-server-limits`（記錄用，0 筆）；`ts-bag-size` 改判 layout done。
  - 剩下的：`ts-tuning-presets` 15、`ts-vfx-damage-tiers` 4、`ts-day-phase-hours` 4、`ts-arena-defaults` 2、`ts-crystal-tier` 1。後三條不在這段範圍。
- 前端 text：99 → 98（比值種子數的「1～250」改用上限組字）。
- 後端 config：1409 → 1408（`ratio_default_seeds` 的 `= 50` 拿掉）。
- `docs/phases/寫死數值-清單.md` 每個 commit 都重產。

## 6. 待 PM 決定（4 件；解讀類都照最保守做了）

1. **hud 鐘點（`ts-day-phase-hours`，4 筆）沒搬，留 todo**：
   - 後端只有白天／夜晚（`day_phase`，06–18 白天）；早／午／晚／夜的 11、21 點分界只存在前端，是畫面上的細分。
   - 要搬到後端，得在 api 層加新的數字常數，但這段只能改 `classes.yaml` 的 ts 區，加了後端數字會沒有規則涵蓋。
   - 選項：(a) 改判 layout（只是把伺服器的白天／夜晚再分成兩個字）；(b) 之後在 content 加時段表，伺服器回 `day_part`。
2. **`ts-bag-size` 的 `BAG_COLS = 6` 改判 layout done**：上限已經照伺服器，剩下的是「每列畫幾格」的排版。PM 不同意就改回 config。
3. **工坊畫面自己的選項（`ts-tuning-presets` 15 筆）留 todo**：
   - 包括：「中」規模 10 種子、80 場；比值快捷鈕 10 種子；篩選與隨機的階級、AP 選項 `[1, 2, 3]`、`[1..5]`；預算比例條刻度 1500‰ 與 `× 100` 換算；預估秒數「改前改後各一次」的 `× 2`。
   - 後端沒有對應的規則，所以沒有東西可讀。
   - 建議：快捷鈕、刻度、換算、`× 2` 改判 layout／const；階級、AP 選項之後由 API 帶（技能資料的階級上限、AP 上限）。
4. **`StartPicker` 與 `affixStatus` 的 `2` 改寫成 `> 1`**：「觸發關係至少兩招」「同詞條不只一條算重複」是結構，不是可調的門檻，所以沒有搬到 API。這兩處是 0 筆，不是被藏起來。PM 若認為「同 id 只生效一條」也該資料化，要從引擎的 `diminish` 一起改（HC-4／HC-7）。

## 7. 平衡疑慮

- 沒有。只改讀取來源與夾具；a、b 兩項的畫面截圖逐位元相同。

## 開發 PM 裁定（2026-11-20）

通過，已用 --no-ff 合併。classify --check 在 main 上是 0，沒有歸類不到的項目。

待決四件：
1. **hud 鐘點**：先留 todo。HC-4d（世界）會在 content 加時段表，再由 api 帶給前端，不改判 layout。
2. **BAG_COLS = 6 改判 layout**：同意。上限已經照伺服器，剩下的只是排版。
3. **工坊選項 15 筆**：照建議。快捷鈕、刻度、秒數換算改判 layout／const，階級和 AP 選項留 todo，之後由 API 帶。這段沒改分類，併到 HC-6 一起改。
4. **`>= 2` 改寫成 `> 1`**：這次接受，因為這兩處是結構，不是門檻。之後的段不要用改寫語法的方式躲掃描：結構性的數字應該在 classes.yaml 寫成 const 規則並附理由，這樣在清單上看得到。
