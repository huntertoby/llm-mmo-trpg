# Phase HC-4b3 報告：閃現模板的預設值搬進 content

依據：`docs/phases/PhaseHC-4b3計畫.md`；HC-4b 裁定 1、3，HC-4b2 的做法與裁定。
基準：main `0ad59e75c`（worktree 開工時在 `d79fcd889`，先 fast-forward）。分支 `worktree-agent-adb3357d927b37f5d`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 先分清楚 | `1d5bce236` | `classes.yaml`：54 筆逐筆歸類（都是 config）；規則的 `where` 拿掉沒有 config 筆數的類別；筆數不變 |
| 2 搬家 | `702836db0` | 預設值改必填；轉型的兩格改成用到時必填；`_MAX_FORM_MAGNITUDE` 改成載入時對照 `enter_form` 原語；計價與規則數值開進工坊（新表 `flash`）；規則改 done |
| 3 收尾 | `05716ff07` | 刪掉 0 筆的 `py-content-flash-templates-config-number` |
| 修正 | `f2923a272` | 工坊說明拿掉設計編號 `#70`、`#71`（`test_no_design_numbers_txt1`） |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試；第 2 項另跑第 4 節的比對。

## 2. 第 1 項：分清楚

### 2.1 54 筆的分類結果

全部是 **config**（遊戲數值或規則的程式預設值）。沒有 text、guard、const。

| 類別 | 欄位 | 筆數 | 值 | 判斷 |
|---|---|---:|---|---|
| `CompleteSkillRules` | `flashes`、`budget_permille`、`cap_permille` | 3 | 3、120、150 | 完整技能的規則數值（6.34.6） |
| `CompleteSkillRules` | `summon_power_steps`、`stance_magnitude_steps`、`status_magnitude_steps` | 21 | 各 1040～1300 共 7 個（1000 是 const 的 ‰ 中性值，不算） | 完整技能重調的倍率階梯 |
| `FlashRules` | `max_flashes`、`major_flash`、`budget_step_permille`、`dissolve_refund_permille`、`usage_min_uses` | 5 | 5、3、40、500、3 | 閃現次數、大變化、預算加成、溶掉退回、用法門檻 |
| `FlashRules` | `stance_magnitudes` | 14 | 1040～2000 | 單一狀態姿態的幅度階梯 |
| `FlashRules` | `modifier_fine_step`、`modifier_drawback_step`、`single_hit_cap_permille`、`converge_targets_permille`、`converge_usage_score` | 5 | 5、100、3000、1500、3 | 修正模板與收束的規則數值 |
| `FlashPricing` | `open`（`options`、`min_categories`）、`focused`（`cost`、`options`） | 4 | 4、2、2、3（`open.cost` 1 是 const 規則先比對到） | 出題價格（#70） |
| `TransformTemplate` | `scale_permille`、`summon_duration` | 2 | 500、2 | 轉型的縮小起點與召喚輪數 |

### 2.2 規則的 `where`
- 規則原本列了 `<module>._MAX_FORM_MAGNITUDE`、`CostCut`、`ExtraMajorTemplate`、`FlashTemplate`、`PriceRule`。這些類別的數字都已被前面的規則比對到（`py-content-guard-bounds`、`py-content-guard-constants`、`py-permille-1000` 等），所以本規則沒有涵蓋。我把它們從 `where` 拿掉，筆數不變。
- 計畫點名的 `FieldDecor._shape`、`FieldMapDef._kind_problems`、`_map_stone_checks`、`_npc_problems` 實際在 `src/trpg/content/fields.py`。它們由 `py-content-fields-text-text` 歸類，那條規則的 `files` 本來就是 `fields.py`，不用改。清單文件 `--md` 產生時兩節剛好相鄰（`fields.py` 的 text 節後面接 `flash_templates.py` 的 text 節），看起來像掛在本檔。
- 2 筆 text（`_ladder`、`FlashTemplate._check`）照計畫留給 HC-6，沒動。

## 3. 第 2 項：搬家

### 3.1 預設值改必填（`content/flash_templates.yaml` 每格都有寫、值相同，沒改內容檔）
- `CompleteSkillRules`：`flashes`、`budget_permille`、`cap_permille`、三條階梯。
- `FlashRules`：`max_flashes`、`major_flash`、`budget_step_permille`、`dissolve_refund_permille`、`usage_min_uses`、`stance_magnitudes`、`modifier_fine_step`、`modifier_drawback_step`、`single_hit_cap_permille`、`converge_targets_permille`、`converge_usage_score`；`complete` 本身也改必填。
- `FlashPricing`：`open`、`focused` 改必填。`FlashTable`：`rules`、`pricing` 改必填。
- `flash_templates.yaml` 改成必備檔（原本缺檔時用全預設的 `FlashTable()`）。`ContentLibrary.flash` 改成必填欄位。做法同 HC-4b2 的 `skill_evolution.yaml`（裁定 2）。

### 3.2 「有某欄才用到」的兩格（轉型）
- `scale_permille`：只有敵對原招（`source: hostile`）轉被動、反應時用到。現在可省略，用到時必填。`to_passive_on_hit`（500）、`to_reaction_melee`（600）都有寫。
- `summon_duration`：只有轉召喚時用到。現在可省略，用到時必填。`to_summon`（2）有寫。`skillgen/flash_major.py` 的 `_to_summon` 加了一行 assert，給 mypy 收窄型別。
- 其他 8 個轉型模板沒寫這兩格，以前吃的是程式預設值 500、2。這兩個值從來沒被讀過：程式裡沒有地方讀 `scale_permille`，`summon_duration` 只在轉召喚時讀。所以結果不變，只有 `model_dump` 從 500、2 變成 `None`（見 4.2）。

### 3.3 規則型上限：`_MAX_FORM_MAGNITUDE`
- 它和 `skill_primitives.yaml` 裡 `enter_form.params.magnitude_permille.max`（2000）是同一個上限。照 HC-4b 裁定 3 的做法，刪掉這個常數，改成載入內容庫時檢查（`library/tables.py` 的 `_check_flash_forms`）：`rules.form_magnitudes` 最後一格不能超過原語參數的上限，錯誤訊息寫「兩格要一起改」，指向 `flash_templates.yaml`。
- 閃現表不在 `Ruleset` 裡（不嵌入規則包），所以這個檢查跟大變化、轉型的跨檔檢查一樣，放在載入內容庫那一層。
- `classes.yaml` 的 `py-content-guard-constants` 拿掉 `_MAX_FORM_MAGNITUDE`（guard 少 1 筆），note 也一併更新。

### 3.4 開進工坊（新表「閃現規則與計價」，18 格）

預算表（`skill_budget.yaml`）的「閃現」組在另一個檔。工坊一個對象只對一個檔，所以照 HC-4b2 `skill_evolution` 的前例，新開對象種類 `flash`（`flash_templates.yaml`）。後端改 `tuning_fields.py`（`TARGET_MODELS`、`TABLE_KINDS`、`TuningTarget.kind`）、`api/tuning/objects.py`（名稱、頂端提示），前端 `client.ts`、`TuningScreen.tsx` 各加一行，`scripts/x10/fields.yaml` 的 hint 規則加上 `flash`。

| 分組 | 欄位 | 名稱 | 建議範圍 |
|---|---|---|---|
| 出題價格 | `pricing.open.cost` | 不指定類別：花幾點靈感 | 0～3 |
| 出題價格 | `pricing.open.options` | 不指定類別：出幾個選項 | 2～6 |
| 出題價格 | `pricing.open.min_categories` | 不指定類別：至少涵蓋幾類 | 1～3 |
| 出題價格 | `pricing.focused.cost` | 指定類別：花幾點靈感 | 1～4 |
| 出題價格 | `pricing.focused.options` | 指定類別：出幾個選項 | 1～6 |
| 次數與預算 | `rules.max_flashes` | 每招最多閃幾次 | 3～9 |
| 次數與預算 | `rules.major_flash` | 第幾次是大變化 | 1～5 |
| 次數與預算 | `rules.budget_step_permille` | 每閃一次預算上限多幾‰ | 0～100 |
| 次數與預算 | `rules.dissolve_refund_permille` | 溶掉技能退回幾‰靈感點 | 0～1000 |
| 次數與預算 | `rules.usage_min_uses` | 用法統計至少放出幾次 | 0～10 |
| 完整技能 | `rules.complete.flashes` | 完整技能視為已閃幾次 | 0～5 |
| 完整技能 | `rules.complete.budget_permille` | 完整技能預算上限多幾‰ | 0～300 |
| 完整技能 | `rules.complete.cap_permille` | 完整技能實際加成的上限（‰） | 0～400 |
| 修正與收束 | `rules.modifier_fine_step` | 修正模板重調幅度的間距（‰） | 1～50 |
| 修正與收束 | `rules.modifier_drawback_step` | 代價減輕每次減幾‰ | 25～300 |
| 修正與收束 | `rules.single_hit_cap_permille` | 收束後單發上限（‰） | 1000～5000 |
| 修正與收束 | `rules.converge_targets_permille` | 收束：平均命中目標數低於多少（‰） | 1000～3000 |
| 修正與收束 | `rules.converge_usage_score` | 收束的用法分數 | 0～5 |

- 每格都有中文名稱，說明都寫了調高、調低的效果。會互相限制的寫了要一起改：`max_flashes` 和 `major_flash`（後者超過前者時驗證擋下）；`open.min_categories` 不能大於 `open.options`；`cap_permille` 應不小於 `budget_permille`。
- 沒開的：幅度階梯（`stance_magnitudes`、`form_magnitudes`、完整技能三條，屬旋鈕結構，同 HC-4b2 的 `blow_distances`）、轉型的 `scale_permille`（沒有程式讀它）與 `summon_duration`（見待決 3）。

### 3.5 測試
- 新增 `tests/content/test_rule_defaults_hc4b3.py`：少寫一格就驗證失敗（22 格）；轉型的兩格用到時必填、沒用到可省略；閃現檔必備；形態幅度超過 `enter_form` 上限時載入失敗。
- 新增 `tests/api/tuning/test_workshop_open_hc4b3.py`：新表在清單上、18 格的值和說明、草稿驗證通過、`major_flash` 大於 `max_flashes` 被擋。
- 改：`test_flash_state.py` 改讀內容檔的規則與計價（原本用 `FlashRules()`、`FlashPricing()`）。`test_flash.py::test_schema_rejects_bad_tables`、`test_flash_bal10b.py::test_form_upkeep_can_never_be_a_flash_knob` 改成從內容檔的 `rules`、`pricing` 起算，只換要測的那一塊。原本 `major_flash` 那一例是「缺欄位錯誤裡的輸入值剛好含 major_flash」才過，所以訊息改比對「major_flash 不可大於」。`test_rules_budget_bs1.py` 的 `TABLE_KINDS` 加上 `flash`。

## 4. 不變比對（基準 `git archive 0ad59e75c src content config`）

腳本放在 scratch，沒進 repo。改前、改後各用自己的 `src/` 與 `content/`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`，並確認載入的 `trpg` 路徑）。

| 比對 | 用法 | 結果 |
|---|---|---|
| 逐招預算 434 招 | `budget434.py <root> <out>`：完整 `BudgetReport` repr＋`validate_skill` 違規 | `skills=434 same=434 different=0` |
| 78 場戰鬥 | `compare78.py <base> <out>`：同 X10-2a 的 78 場，`--log-json` 整份去掉 `ruleset_hash`、內嵌規則包，加上文字輸出 | `battles=78 events=26446 different=0`；內嵌規則包也 0 差異（閃現表不嵌入） |
| 閃現出題 | `flash_dump.py <root> <out>`（下列） | 全部 different=0（見 4.1） |

### 4.1 閃現出題（`flash_dump.py`，完整 JSON 逐位元組比對）
- `FlashRulesOut`（API 給前端的規則）、兩組 `PriceRule`、閃 0～7 次的預算加成、`is_major`、溶掉退回（花 0～8 點）、`rules.complete`：都相同。
- 完整技能：406 招玩家技能逐招 `complete_strength` 全文，`same=406 different=0`。
- 閃現出題：玩家技能每 7 招取 1 招（58 招）× 3 組（種子 2／階級 1、種子 9／階級 2、種子 4／階級 3）。每組連閃 5 次（含第 3 次大變化），第 1 次另出一題「指定第一個合法類別」，最後再重閃第 1 次。共 174 組、1322 筆（題目全文、錯誤訊息、最後狀態）：`same=174 different=0`。

### 4.2 預測會變的地方（逐鍵核對）
- `FlashTable.model_dump` 有 17 處不同，全部都是 3.2 預測的那些：沒寫的轉型模板，`summon_duration` 從 2 變成 `None`（9 個非召喚轉型），`scale_permille` 從 500 變成 `None`（8 個非敵對被動／反應轉型）。沒有其他差異。這份 dump 不進任何雜湊、存檔或 API。
- parity 夾具、CLI 快照：沒有重產，slow 測試照原樣通過（第 5 節）。
- OpenAPI：重產後沒有差異（`client/openapi.json` 不變，工坊的種類參數是字串）。

## 5. 檢查（最後一個程式 commit `702836db0`；之後的 commit 只改 `classes.yaml`、清單文件和工坊說明）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1764 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 逐招預算比對 434 招 | different=0 |
| 78 場戰鬥比對 | different=0 |
| 閃現出題比對 | different=0 |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979 passed） |
| `pnpm -C client typecheck` | 0 |
| `pnpm -C client test` | 0（4820 項） |
| `pnpm -C client build` | 0 |

分目錄（`run_pytest.py -q tests/<目錄> -n 8`，一次一組）：

| 目錄 | 結束碼 | 結果 |
|---|---|---|
| api | 0 | 1387 passed、1 skipped |
| bot | 0 | 67 |
| cli | 0 | 148 |
| content | 1 → 0 | 第一輪 1 failed：`test_no_design_numbers_txt1` 擋下工坊說明裡的 `#70`、`#71`。拿掉後（`f2923a272`）整個目錄重跑 3239 passed，`tests/api/tuning` 重跑 247 passed |
| engine | 0 | 5120 |
| infra | 0 | 9 |
| llm | 0 | 495 |
| narrative | 0 | 479 |
| roguelite | 0 | 279 |
| server | 0 | 77 |
| shared | 0 | 76 |
| sim | 0 | 180 |
| skillgen | 0 | 4637 passed、7 skipped |
| world | 0 | 1328 |
| 頂層 `tests/test_*.py` | 0 | 257 |

- 看門狗沒有回報 worker 掛掉或卡住（log 裡沒有 `node down`，也沒有 `stuck.txt`）。保留下來的留證資料夾是 content 那一輪失敗時自動留下的。
- `f2923a272` 只改 `content/tuning_fields.yaml` 的說明文字，比對結果不受影響。

## 6. config todo 與歸類（`classify.py --stats`）

| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `0ad59e75c` | 753 | 38 | 8889 | 194 | 398 |
| 後端 交件 | **699** | 38 | 8887 | 194 | 397 |
| 前端（只加兩行） | 26 | 0 | 5440 | 98 | 0 |

- config 少 54，都是 `flash_templates.py` 的。
- guard 少 1（`_MAX_FORM_MAGNITUDE`）。const 少 2：拿掉的預設階梯裡 4 個 1000（‰ 中性值），加上新增的 2 段欄位說明。
- 0 筆而刪掉的規則：`py-content-flash-templates-config-number`（照 HC-4b 裁定 1，不留 done）。HC-4b2 改成 done 的規則都已在 HC-4b2 刪掉，現在沒有 0 筆的。`寫死數值-清單.md` 用 `--md` 重產。

## 7. 待 PM 決定（都照最保守的做了）

1. **`flash_templates.yaml` 改成必備檔**：原本缺檔時用程式預設值。改必填後缺檔就載入失敗（同 HC-4b2 `skill_evolution.yaml` 的裁定 2）。
2. **新增工坊表 `flash`**：預算表的「閃現」組是 `skill_budget.yaml`，閃現規則在 `flash_templates.yaml`。工坊一個對象對一個檔，所以照 HC-4b2 裁定 4 的前例另開一張表，沒有硬塞進預算表。
3. **轉型 `to_summon` 的 `summon_duration`（2 輪）沒開進工坊**：它是清單項目（`transforms[*]`）。要開就得在 `_ENTRY_WORDS` 加「轉型」的標籤，而且轉型沒有 `name_zh`，畫面上只會顯示 ID。`scale_permille` 沒有任何程式讀它（docstring 寫它只是起點提示），建議之後刪掉這個欄位，要刪請告訴我。
4. **同檔還有沒被掃到的預設值**（不在 54 筆內，沒動）：
   - `tighten_permille: 100` 被 `py-percent-conversion` 當成 const；
   - `form_magnitudes = tuple(range(1000, 2001, 50))` 掃描器沒有列出；
   - `insight_per_win` 程式預設 1、內容檔寫 2；
   - `cost_cuts` 的程式預設步距都是 1，內容檔的法力、耐力是 10；
   - `PriceRule.min_categories` 預設 1，`focused` 靠這個預設。

   這幾格的內容檔都有寫（`focused.min_categories` 除外），結果不受影響。要一起改成必填的話，可以併進下一段。
5. **其他階段留下的 0 筆 done 規則沒刪**：`ts-flash-fallback`、`ts-slot-limits`、`ts-source-max`、`ts-attr-base`、`ts-start-keywords`、`ts-affix-duplicate`、`ts-walk-max`、`ts-tuning-server-limits`（HC-3），`py-scale-one-defaults-content`、`py-scale-one-defaults-misc`（HC-2），`py-content-rule-bounds-boss-parts`（HC-4a）。計畫只要求刪本段和 HC-4b2 的，所以這幾條沒刪。另外有 7 條 todo 規則是 0 筆（`py-content-loader-config-number` 等），也沒動。
6. **範圍外的小改動**：`skillgen/flash_major.py` 加了一行 assert（型別收窄，輸出不變）；`scripts/x10/fields.yaml` 的 hint 規則加上 `flash`。

## 8. 平衡疑慮（無）

沒有。只換數字放的地方。434 招預算、78 場戰鬥、閃現出題、完整技能、計價都逐項相同。

## 開發 PM 裁定（2026-11-21）

已用 `--no-ff` 合併進 main。合併後在 main 重跑 ruff、format、mypy、lint-imports、`classify.py --check`、`trpg content check`，結束碼都是 0。全量檢查交給 push hook 跑。

待 PM 決定的 6 件：
1. **`flash_templates.yaml` 改成必備檔**：照做，和 HC-4b2 的 `skill_evolution.yaml` 一致。
2. **工坊另開 `flash` 表**：保留。工坊一個對象對一個檔，這樣分是對的。
3. **`summon_duration` 不開、`scale_permille` 沒人讀**：
   - `summon_duration` 不開，照做。
   - `scale_permille` 沒有程式讀，併進 HC-4c 刪掉。刪掉前要先 grep 前端與 `content/` 確認沒有用處。
4. **同檔還沒動的幾格**：併進 HC-4c 一起改成必填，值以內容檔為準，結果不變。
   - `tighten_permille`：改歸 config。
   - `form_magnitudes`：range 的預設值。
   - `insight_per_win`：程式寫 1、內容檔寫 2，以內容檔為準。
   - `cost_cuts`：步距。
   - `PriceRule.min_categories`
5. **其他段留下的 0 筆規則**：11 條 0 筆的 done 規則，併進 HC-4c 刪掉。7 條 0 筆的 todo 規則留著，等對應的段做到時再處理。
6. **範圍外的小改動**：接受，輸出不變。
