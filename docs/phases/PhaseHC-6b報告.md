# Phase HC-6b 報告：API 與前端說明文字裡的寫死數字改從資料帶入

依據：`docs/phases/PhaseHC-6b計畫.md`。基準：main `add305d93`（worktree 開工時就在這裡）。分支 `worktree-agent-aeef94095a52169d6`，沒 push。
沒改數值、沒改玩家看到的字（目前的值組出來全部逐字相同，見第 5 節）；第 4 項只在 `wish_cards` 改了以後字才不同。沒動 `docs/design/`、`config/`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 API 的 text | `1097f7ef3` | 9 處改組字、19 筆改判 const（附理由），剩 4 筆 |
| 2 前端的 text | `a361c73d4` | `/api/glossary` 的 `rules` 加 23 個欄位、工坊狀態加 1 個；31 處改組字、44 筆改判 const，剩 23 筆 |
| 3 介面文字項目 | `4b5fdb69e` | 工坊選項 15 筆：快捷鈕、刻度、預估倍數改判 layout／const；其他 7 項不在清單裡，沒做（第 4 節） |
| 4 `wish_cards` 連動字 | `605827263` | 許願畫面、許願三選一的字、工坊相鄰兩格的說明改讀 `wish_cards` |
| 5 收尾 | `c1b80f83a` | 刪 9 條基準時就是 0 筆的 config／scale 規則；`--md` 重產清單 |
| 報告 | 本 commit | 含截圖 `docs/art/shots/hc-6b/` |

## 2. text 筆數

| | 開工 | 交件 |
|---|---:|---:|
| 後端 `api/` | 34 | **4** |
| 後端合計（含 HC-6a 留給 HC-7 的 26 筆） | 60 | **30** |
| 前端 | 98 | **23** |

`classify.py --check` 結束碼 0，沒歸類 0。`--unused` 沒有輸出。

**後端留下的 4 筆**
- `api/tuning/objects.py` 的「沒寫＝5」（移動力）、「沒寫＝4」（表面生長排數）：schema 沒有預設值可以帶，見待決 1。
- `world_growth_view.py` 兩處「1 天內」：HC-6a 裁定 3 排進 HC-7。

**前端留下的 23 筆**：程式裡沒有資料可以帶，都列在 `ts-ui-text` 的 note。
- 引擎寫死的：
  - 源泉 +1（legend、statusCard）；
  - 戰前佈置每場 1 個；
  - 召喚物守護 2 格；
  - 指揮、灌注每輪 1 次（summonControl 3 筆、SummonPanel 2 筆）；
  - 開火 1 發。
- 內容檢查寫死的：
  - 道具技能 1 AP（BagScreen、EconomyPanel）；
  - 鍛造指定 1 條、特色材料每種 1 個。
- 其他：
  - 單場戰鬥「標準隊友補到 3 人」；
  - 大世界「0～2 名隊友」；
  - 重選「2 個關鍵字」；
  - 配點範例；
  - 「每級 +2」：資料是 `attribute_points_per_level: 20`（×10 量尺），顯示要怎麼換算得先定；
  - 線索每筆 +1（2 筆）；
  - 誓約「1 天內」（WorldGrowth 2 筆，HC-7）。

## 3. 改了哪些

### 3.1 API（第 1 項）

| 位置 | 原本寫死的 | 改成讀 |
|---|---|---|
| `tuning/objects.py` `_DEFAULTS_ZH` | 沒寫＝0／1（armor_bonus、level、cost.stamina、cost.mana、stance_upkeep） | pydantic 欄位的預設值 |
| `tuning/objects.py` 升階提示 | 夾在 70～100% | `skill_budget.yaml` 的 `min/max_ratio_permille`（新 `retier_note_zh(budget)`；`library` 是 None 時讀草稿資料夾的檔） |
| `tuning/objects.py` 表單頂端提示 | AI 表「11 個值」、被動觸發「n＝2、3」 | 白名單 `parts.*` 的欄位數、`budget_by_n_permille.<n>` 的欄位（新 `ai_notes`、`table_notes`） |
| `tuning/skills.py` | 快捷分組的標籤（1 階、1 AP、2 AP）、預支「AP 固定是 0」 | 預設的篩選值、`_BORROW_AP_LIMITS` |
| `world_growth_view.py` | 誓約佔 1 格、被動最多 2 招；破誓 2 回合 | `OATH_PASSIVE_SLOTS`、`skill_slots.passive`（新 `slot_zh(library)`）；`oaths.yaml` 的 `penalty_rounds` |
| `world_economy_view.py` | 腰包「花 1 AP」 | 道具技能本身的 `ap_cost` |

### 3.2 前端（第 2 項）

- **一輪 roguelite**：`run/runRulesText.ts`（新），用在 RunNewScreen、RunScreen、StartScreen、RunCampfire。
  - 5 場、2 名隊友：`rules.roguelite_battles`、`rules.roguelite_companions`。
  - 營火源力 +1：`rules.campfire_source`。
- **閃現**：`run/flash.ts`，用在 FlashChooser、CampfireSkillCare、SkillFlashInfo。
  - 第 3 格、第 3 次：`rules.major_flash`。
  - 完整技能「閃現 3 次」：`rules.complete_flashes`。
  - 傳承最多 2 個、第 1、2 次：`flash_rules.max_carry`。
  - 至少涵蓋 2 類：`rules.flash_open_min_categories`。
- **數值工坊**：
  - 草稿名稱 40 字：`TuningStatus.draft_name_max`，後端同時改用 `DRAFT_NAME_MAX` 組樣式。
  - 預算區間 70～100%：`rules.budget_*`。
  - #149 招數下限：`rules.min_moves_*`。
  - 分母小於 30：既有的 `small_sample`。
  - 40,000 組：既有的 `ratio_max_work`。
- **技能工坊 TryoutPanel**：
  - 主動技最多 6 個：`skill_slots.active`。
  - 預算 70–100%：同上的預算區間。
- **戰鬥介面**：
  - 操作說明再顯示 3 次：`OP_HINT_LIMIT`。
  - 擴散 1 格內：`rules.contagion_radius`。
  - 「下回合少 1 AP」：實際要少的格數。
- **大世界**：
  - 線頭每人約 5 條、約 3 天：`rules.thread_limit`、`thread_expire_seconds`。
  - 4 級起：`rules.opening_end_level`。
  - 等待 10 秒（pregen、許願 3 處）：`rules.pregen_wait_seconds`。
  - 閃現教學「1 點、4 個變化」：`rules.flash_open_cost`、`flash_open_options`。
  - 循環賽第 13 天：`rules.league_signup_close_day`。
- **共用寫法**：`ui/rulesText.ts`（新）。
  - `budgetWindowText`：寫成「70～100%」，百分號只寫一次。
  - `aboutDurationText`：整天寫「約 N 天」，不整天寫「約 N 小時」（同 HC-6a 裁定 3 的誓約規則）。
  - `countZh`：中文數字。
- 模組常數改成函式：
  - `TRANSFORM_HINT` → `transformHint()`；`INHERIT_RULE_TEXT` → `inheritRuleText(limit)`；`SPREAD_NOTE` → `spreadNote()`；
  - `NO_THREAD_ZH`／`THREAD_RULE_ZH` → `noThreadText()`／`threadRuleText()`；
  - `FLASH_LOCK_ZH.tail`／`LEVEL4_TAG_ZH` → `openingLevelTag()`；`PREGEN_WAIT_NOTE` → `pregenDefaultNote()`；
  - `WISH_ZH` 的 timeout／waitNote／tagTimeout 也改成函式；
  - 既有測試裡的引用一起改了。

### 3.3 改判 const 的清單

每條規則的 note 都寫了理由。

- **後端** `py-api-const-text`（19 筆）：
  - 至少 1 條詞條（非空檢查）；
  - 循環賽「1 對 1」（對戰形式的名字）；
  - 一筆事件得到 1 把鑰匙、一筆增援抽 1 名（結構）；
  - 刷新時刻的「:00」（時刻格式）；
  - 「例：120」「例：2d6」「750＝−25%」（舉例）；
  - 升階提示的「2 階以上」「1 階」（基準階級）；
  - 同時 1 個誓約（單一欄位）；
  - 第 1 輪、第 2 輪（序號）；
  - 不到 1 小時（時間單位的分界）。
- **前端**（44 筆）：
  - `ts-hc6b-ordinal-text`：第 1／2 段、一個關鍵字一招、許願「1～上限個關鍵字」、第 1 個、第 2 個。
  - `ts-hc6b-single-text`：最後 1 輪、至少 1 條、選 1 個或選 1 件、種族 1 招與 1 項、同時 1 個、每帳號 1 個角色、先挑 1 個。
  - `ts-hc6b-zero-text`：模式切換、集火「0 AP」，模擬的 0。
  - `ts-hc6b-format-text`：3×3、`?dev=1`、`TRPG_TUNING=1`、「1 以上」、‰ 換算、11-20 的放大 10 倍公告、配方碼 10 碼、比值情境組法。
  - `ts-hc6b-tier1-text`：「1 階比值」「1 階預算」（BAL-21e 的量法名字）。
- **數字（非 text）**：
  - `ts-rules-text-units`（const）：`rulesText.ts` 的秒、小時、天換算。
  - 第 3 項的改判見第 4 節。

## 4. 第 3 項：一併處理的介面文字

照規格開工前先查 `--dump text` 和 `寫死數值-清單.md`：

| 項目 | 有沒有 | 處理 |
|---|---|---|
| 工坊前端 15 筆（清單 `ts-tuning-presets` config 15） | 有 | 照 HC-3 裁定 3 改判：<br>・「中」10 種子、80 場、比值快捷 10 種子 → layout（`ts-tuning-quick-buttons`）；<br>・預算比例條刻度 150% → layout（`ts-tuning-budget-scale`）；<br>・預估「× 2」→ const（`ts-tuning-estimate-factor`）。<br>前端 config 22 → 15。<br>篩選列的階級、AP 選項與隨機的階級（8 筆）照裁定留 todo，還沒改由 API 帶 |
| `base_points` 的說明用字（HC-B 裁定 6） | 沒有 | 沒做 |
| 沒有技能的形狀（HC-W2 裁定 1，加一句「目前沒有招用到」） | 沒有 | 沒做（也會加玩家看得到的字） |
| 祝禱的骰子字（X10-3d 裁定 6，`1d6 HP` 改成範圍） | 沒有（`1d6` 算識別字引用） | 沒做（會改玩家看得到的字） |
| 地面提示、組裝列的說明（AR-X10 待決 4，骰子行換排法） | 沒有 | 沒做（是排版，不是數字） |
| 詞彙表的骰子欄（AR-X10 待決 5，`/api/glossary` 加結構化骰子欄） | 沒有 | 沒做 |
| 路徑預覽的重擲狀態 | 沒有 | 沒做 |

這 7 項都記在 `開發PM交接.md` 的 HC-6 待辦裡，但不在掃描清單上。見待決 2。

## 5. 驗收比對

腳本放在 scratch，沒進 repo：`apidump.py`、`jcmp.py`，加上沿用 GS-3 的 `budget434.py`、`budget_cmp.py`、`compare78.py`。基準是 `git archive add305d93`，執行時確認過載入的 `trpg` 來自基準那份。

| 比對 | 結果 |
|---|---|
| API 固定請求：<br>・工坊 519 個對象的 `object_detail`（全部欄位、`default_zh`、`note_zh`、`notes_zh`）；<br>・快捷分組；<br>・預支提示；<br>・誓約欄位；<br>・每個誓約模板的破誓與解除句；<br>・35 個物品的腰包句 | `leaves same=98355 different=0`（只有 `trpg` 路徑不同，這筆是用來確認基準的）。第 1 項後、第 4 項後各跑一次 |
| `/api/glossary` | 只多 `rules` 底下的新欄位：<br>`roguelite_battles` 5、`roguelite_companions` 2、`campfire_source` 1、<br>`budget_min_ratio_permille` 700、`budget_max_ratio_permille` 1000、`contagion_radius` 1、<br>`major_flash` 3、`complete_flashes` 3、`flash_max_carry` 2、<br>`flash_open_cost` 1、`flash_open_options` 4、`flash_open_min_categories` 2、<br>`pregen_wait_seconds` 10、`wish_cards` 3、<br>`thread_limit` 5、`thread_expire_seconds` 259200、<br>`opening_end_level` 4、`league_signup_close_day` 13、<br>`min_moves_mob` 2、`min_moves_elite` 3、`min_moves_boss_phase` 3。<br>其他鍵 0 改動 |
| 工坊 `/status` | 只多 `draft_name_max` 40 |
| 前端夾具 `battle/fixtures/glossary.json` | 重產後只有上一列的新鍵（逐鍵和 `rules` 一致）；其他夾具沒變 |
| 前端字串：每個改到的元件都有 vitest，用目前的值組出來和改前逐字相同 | `ui/hc6bRuleText.test.ts`、`world/hc6bWishCards.test.ts`，另外驗值換了字會跟著變、元件真的改用這些函式 |
| 逐招預算 | 基準與本分支都是 442 招（GS-3 之後是 442，不是規格寫的 434→438）：`same=442 different=0` |
| 78 場戰鬥 | `battles=78 events=26206 different=0`，內嵌規則包 0 差異 |
| 提示詞 | `wish_pick` 的 `_count_zh` 改名成公開的 `count_zh`，字不變；`tests/llm/test_prompts.py` 的雜湊快照通過 |
| CLI 快照、parity | 交件前由 check.py＋slow 測試確認（第 7 節） |

## 6. 第 4 項：`wish_cards` 與中文數字的規則

- **前端**（`ui/rulesText.ts` 的 `countZh`，和後端 `llm/prompts/wish_pick.py` 的 `count_zh` 同規則）：
  - 0～10 寫中文數字，超過 10 寫阿拉伯數字。
  - 後面接量詞（招、張）時，2 寫「兩」：「給你兩招挑一招」「兩招都不拿」。
  - 「N 選一」是固定說法，2 照寫「二」：「技能二選一」。
- **改到的字**：
  - 許願面板的 `textLead`、`menuLead`、`tagTextLead`、`tagMenuLead`、`refundNote`、`gain`（「技能三選一」）。
  - 關鍵字「1～2」同時改讀 `WishView.max_keywords`。
- **工坊**：
  - `content/tuning_fields.yaml` 兩格的 `note_zh` 改成占位：
    - 「許願池：候選量」的「挑 {wish_cards} 張」；
    - 「都不拿時退回」的「許願的{wish_cards_zh}選一」。
  - `api/tuning/objects.py` 的 `note_text` 讀草稿資料夾的 `skill_pick.yaml` 代入。
- **測試**：
  - 3 張逐字相同；
  - 2 張、5 張另外測（vitest 與 `tests/api/tuning/test_workshop_open_hc6a.py`）。
- **截圖**：`2-wish-cards2.png` 是 2 張時的畫面，`3-wish-cards5.png` 是 5 張時的畫面。

## 7. 檢查

| 檢查 | 結束碼 |
|---|---|
| `ruff check src tests/api scripts/hardcoded` | 0 |
| `ruff format --check src tests/api` | 0 |
| `mypy src`（679 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（704 檔、442 技能） |
| `classify.py --check` | 0 |
| `tsc --noEmit` | 0 |
| `vitest run`（全部，第 2 項後） | 0（4836 passed） |
| `vitest run src/world`（第 4 項後） | 0（833 passed） |
| 相關 pytest（經看門狗）：<br>・`tests/api/tuning`、`test_text_from_data_hc6b.py`、`test_oath_warning.py`、`test_world_growth_api.py`、`test_hardcoded_scan.py`；<br>・`test_openapi_snapshot.py`、`test_views_glossary.py`、`test_glossary_names.py`；<br>・`test_workshop_open_hc6a.py`、`tests/llm/test_prompts.py`、`tests/content/test_tuning_fields.py` | 全部 0（328、335、53 passed） |
| build、`scripts/check.py`、slow（parity、`tests/cli`） | 見下面「交件前全量」 |

**交件前全量**（開發 PM 回「可以跑」後，先 `git merge --no-edit main`，main 是 `fd37e78e8`，只多 `.md`）：

- 第一次 `check.py`：mypy、pytest 各 1 個失敗，都是既有的測試，`ac1791cd2` 已修。
  - `test_hc3_game_rules.py` 寫死 `rules` 只有 HC-3 的四個鍵，改成只檢查這四個鍵還在。
  - `test_rules_r1_r2_nw2a.py` 直接用了可能是 None 的 `library`，先加一行斷言。
- 第二次 `check.py` 結束碼 0，已寫下通過戳記。
  - pytest：18202 passed、8 skipped。
  - vitest：4841 passed。
- `pnpm -C client build`：0。
- slow（`tests/skillgen/test_refactor_parity.py`、`tests/cli`）：0，995 passed。

## 8. 截圖（`docs/art/shots/hc-6b/`）

- 開發頁用 vite（埠 5196），Chrome headless 加 `--mute-audio`，網址帶 `?mute=1`。
  - 臨時開發頁畫的是正式元件：`WishPanel`、`ExceptionChecks`、`Hud`，加上工坊說明句的函式。
  - 臨時開發頁沒 commit。
  - 拍完 vite 和 Chrome 都用 PID 關掉了。

| 檔案 | 內容 |
|---|---|
| `1-wish-workshop-cards3.png` | 左：許願面板（3 張，字和改前相同：「給你三招挑一招」「三招都不拿」「技能三選一」）。右：數值工坊的草稿名稱、預算例外、#149 例外、樣本小、比值組數說明；技能工坊的「不換」選項與預算區間 |
| `2-wish-cards2.png` | 許願面板，`wish_cards`＝2：「兩招挑一招」「兩招都不拿」「技能二選一」 |
| `3-wish-cards5.png` | 許願面板，`wish_cards`＝5 |
| `4-battle-status-spread-tip.png` | 戰鬥主角卡滑過「會擴散」的燃燒：說明卡最後一行「傳給身邊 1 格內的一名同伴」（照 `contagion_radius`） |

沒有實機截圖：許願池要主城角色，工坊要開伺服器。如果需要實機圖再補拍。

## 9. 複雜度與 noqa

沒有新加 `# noqa`。

## 10. 待 PM 決定

1. **工坊「沒寫＝5」「沒寫＝4」已經過時**：
   - 移動力（`speed`）和表面生長排數（`max_rows`）HC-4a 起 schema 已經沒有預設值，YAML 一定要寫，所以畫面上的「沒寫＝5／4」不會發生。
   - 這段不改字，留 text。建議 HC-7 直接拿掉這兩條。
2. **第 3 項的 7 個介面項目不在掃描清單，沒做**（第 4 節）：
   - 其中祝禱範圍與「沒有技能的形狀」會改玩家看得到的字，地面提示與組裝列是排版，詞彙表骰子欄要加 API 欄位。
   - 建議另開一段，或併進 HC-7。
3. **新欄位的預設值歸 config（保守）**：
   - `GameRulesOut` 21 個欄位、`TuningStatus.draft_name_max`，再加 `DRAFT_NAME_MAX`，規則 `py-api-text-rules-defaults`。
   - 後端 config 162 → 181。
   - 這些預設只給舊回應相容用，伺服器一律由內容庫填，值和內容檔相同。PM 可以改判 const。
4. **#149 招數下限放在 `/api/glossary` 的 `rules`，沒放工坊 `/status`**：
   - 例外說明的元件（`ExceptionChecks`）拿不到工坊狀態，改從全域規則讀。
   - 數值相同，`world/enemies.yaml` 沒有時用預設值。
5. **「線頭約 3 天」用秒數組字**：整天寫「約 N 天」，不整天寫「約 N 小時」（四捨五入），套用 HC-6a 裁定 3 的誓約規則。
6. **工坊選項的階級與 AP（8 筆）留 config todo**：HC-3 裁定 3 要改由 API 帶；階級該讀哪個上限還沒定，這段沒接。
7. **規格的 434→438 招**：現在 main 有 442 招（GS-3 之後），比對的是全部 442 招。

## 開發 PM 裁定（2026-11-22）

驗收通過，已合併進 main 並 push。合併 main 後 check.py 0（pytest 18202、vitest 4841），build 0，slow parity＋cli 995 passed；442 招預算、78 場 different=0。截圖已看（許願 3／2／5 張、戰鬥擴散提示）。

1. 工坊「沒寫＝5／4」：HC-7 a 直接拿掉這兩句（schema 已必填，不會發生）。
2. 7 個不在掃描清單的介面項目：另排 HC-6c（HC-7 之後），因為會改玩家看到的字與排版，要逐項截圖。
3. 新欄位預設值歸 config：接受；HC-7 b 一併處理（能改判 const 的改判）。
4. #149 招數下限放 `/api/glossary`：接受。
5. 「線頭約 N 天／小時」：接受，和 HC-7 的誓約冷卻規則一致。
6. 工坊選項的階級與 AP 8 筆：併進 HC-7 b。
7. 442 招：接受。
