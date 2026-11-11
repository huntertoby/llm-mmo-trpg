# Phase OB-3 報告：#150 OB-2 後續、#148 換示範招、免費重選、閃現 4 級限制、配點教學

> 實作者：worktree 基準 main `729c47a0`。沒有 push、沒有 merge。依據：`docs/phases/PhaseOB-3計畫.md`、`docs/design/21` 21.5（#150 九點含「OB-2 補充」、#134 示範招段）、`docs/design/09` 9.6.9、`PhaseOB-1報告.md`、`PhaseOB-2報告.md`、共用筆記 `盤點-150與147.md`（1.0、1.1、4.3）與 `核對-148示範招B案.md`。
> 沒有動 `src/trpg/engine/`、`src/trpg/roguelite/`、任何技能數值；沒有動 OB-4 的檔案（`world/field_enemies.py`、節點遭遇、事件戰鬥、雇傭兵、聯賽、賽季 Boss、誓約、換技能）；**`world/opening.py`（含 `opening_gate`）一行都沒改**。

## 1. 交付項目（每項一個 commit）

| # | commit | 項目 | 做法 |
|---|---|---|---|
| A1 | `a2321015` | #148 換示範招 | `newcomer.yaml` 的 `range.demos`：近戰 瞬步背刺＋狂野之刃、遠程 淬毒箭＋燧石飛刃、法器不變；新欄位 `range.demo_notes`（技能 ID → 示範卡片多寫的一句，鍵要是示範招）放「靶場的油桶打破會流出油」，由 `RangeDemoView.notes_zh` 帶出，技能本體說明不改。`DEMOS_148`、`test_range_api.py` 的招名同步。資料測試 `test_demos_are_not_bound_to_a_weapon`：6 招都沒有 `weapon_only`、技能資料任何一層都沒有 `wielding_weapon` 條件（另一個測試確認這個檢查抓得到被換掉的塔盾猛擊） |
| A2 | `92dbebd1` | 兩組三選一不重複 | 採「選完第 1 組才出第 2 組」：`quests.py::issue_deferred_offers(after=)` 一次只出下一組；`take_offer`（多收 `world`）選完或跳過延後的那組就接著出下一組。第 2 組出題時已經擁有第 1 組選走的招，候選自然排除 |
| A3 | `f155aefa` | 拒絕原因 | 訊息 OB-2 已有（「不能選雙手劍：它占用副手，副手要收進背包，但背包放不下（需要 31 格，只有 30 格）」），本段只補測試鎖住文字（世界層逐字、API 422 的 `detail`） |
| A4 | `b9d9938e` | 帶武器的推薦查詢 | `GET /api/world/characters/{id}/range/recommend?weapon=` → `{weapon, keywords}`（0～2 個）。只在可以正式選定或可以重選時回應，其他 422（中文原因）。快取沿用 `recommended_keywords` 的（內容庫, 開局種子, 武器, 候選）。`RangeView.recommended_keywords` 保留 |
| A5 | — | 推薦關鍵字表 | 見第 3 節 |
| B6 | `3e5b083c` | 免費重選 | 新動作 `opening_reselect {weapon, keywords}`、事件 `OpeningReselectedEvent`、新模組 `world/opening_reselect.py`；`RangeView.reselect`（能不能重選、原因、會收回的招、起始武器會不會收回、會損失的強化）。順序見第 4 節 |
| B7 | `1e38f440` | 閃現 4 級限制 | `growth.py::flash_blocked_zh`（`opening is not None and level < 4`），`_flash` 的 `FlashAction` 先查它；`world_pregen.flash_wait_request` 同條件回 `None`（預測與等待都不生成）；`GrowthView.can_flash`、`flash_blocked_zh`；第一次閃現的引導同條件不出（第 3 步打完升 4 級、`opening` 清掉後才出） |
| B8 | `af939bbb` | 配點教學 | 見第 5 節 |
| B9 | `4122f7b6` | 4 級 | `opening_reselect.py::close_opening`，在 `world_step` 結尾（所有經驗來源之後）：正式選定過、等級 ≥ 4、沒有待選的延後三選一 → `opening = None`。4 級前溶掉、傳承 OB-1 的閘門已擋（入門期與正式選定後兩個階段都有 `_before_level_4_rule`），本段補測試鎖住 |

入門招、示範招一律從 `range.demos` 讀；起始招從開局種子推。程式沒有寫死技能 ID（測試名單 `DEMOS_148` 除外）。所有新判斷以 `char.opening is not None` 為前提。

## 2. 驗收

| 條件 | 結果 |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 2286 files already formatted |
| `uv run mypy` | Success: no issues found in 1435 source files |
| `lint-imports` | 14 kept, 0 broken |
| `tests/world tests/api tests/content tests/narrative tests/skillgen tests/roguelite tests/server tests/test_architecture.py`（`-n 8`） | **分四批跑，全過：共 9570 passed、15 skipped、0 failed**（見下方說明；一次跑完的那種跑法沒有跑完） |
| `corepack pnpm -C client typecheck` | 結束碼 0 |
| `vitest run src/render/inkDollSnapshot.test.ts src/world/range.test.ts src/world/growth.test.ts` | 3 檔 22 個全過（`growth.test.ts` 的 fixture 補了 `can_flash`、`flash_blocked_zh`） |
| `trpg battle --map swamp --seed 7 --log-json` ＋ `battle replay` | 重播驗證通過：58 個動作、217 個事件，最終狀態一致 |

全目錄測試的說明（最後一個 commit `4122f7b6` 之後跑的）：

| 批次 | 結果 |
|---|---|
| `tests/world tests/api`（`-n 8`） | 2117 passed、1 skipped（3 分 40 秒；`test_dev_boss_rehearses_to_the_boss_charge` 這次有過） |
| `tests/skillgen tests/roguelite`（`-n 8`） | 4219 passed、14 skipped（6 分 32 秒） |
| `tests/content`（`-n 2`） | 2786 passed |
| `tests/narrative tests/test_architecture.py` | 371 passed |
| `tests/server`（`-n 2`） | 77 passed |

**八個目錄一次跑（`-n 8`）試了兩次都沒跑完**：跑到 99% 出現 `[gw1] node down: Not properly terminated`，之後整個 pytest 卡住不動（worker 的 CPU 時間不再增加），我把自己啟動的那個工作停掉。原因查到是 `tests/skillgen/test_player_text.py::test_player_check_texts_have_no_english_identifiers`：這台機器同時有別的 agent 在跑測試，分批跑時它單獨就花了 295 秒，離 `pyproject.toml` 的單一測試逾時 300 秒只差 5 秒；一次跑八個目錄時更擠，超過 300 秒，逾時（thread 方法）直接結束 worker，xdist 就卡在收尾。這個測試和本段的改動無關（檔案沒動、不讀示範招），沒有改它；第一次卡住時工作樹只有 A1 的改動。建議另排把它標 slow 或拆小。

`client/openapi.json`、`client/src/api/schema.d.ts` 已重產（`scripts/export_openapi.py` ＋ `gen:api`）。A1 的 commit 單獨看時 openapi 快照會差 `notes_zh` 一欄，A4 的 commit 補齊（之後每個改 API 的 commit 都有重產）。

行為一致測試：

| 規格 | 測試 |
|---|---|
| 三大類 × 正式選定 → 重選到另一大類（真的送世界動作；近戰那組第 1、2 步真的打） | `tests/world/test_opening_reselect.py::test_reselect_to_another_class`（3 組）：武器、起始 2 招（同開局種子）、整個主角範本、8 點全在 `attribute_spent`、HP 法力回滿、等級經驗靈感金幣不變；舊的 4 招（起始 2＋三選一 2）從裝備、備用、`generated_skills`、`flash`、`flash_bases`、`skill_usage`、`skill_regions` 全部不在；重新出題一次一組；只能一次 |
| 重選的條件 | `test_reselect_conditions`（舊角色、入門期、4 級、不在鎮上、有遭遇、選大類中；失敗時角色不變）、`test_reselect_rejects_bad_weapon_or_keywords`（不合法不會用掉那一次） |
| 邊界：已賣、已強化、背包滿、雙手與副手 | `test_reselect_when_the_starting_weapon_was_sold`、`…_takes_back_the_starting_weapon_item`、`…_when_worn_again`、`test_reselect_lists_and_drops_enhancement`、`test_reselect_refused_when_bag_is_full`、`test_reselect_two_handed_stows_off_hand` |
| 兩組三選一不重複（含有交集的情況） | `tests/world/test_opening_choice.py::test_second_group_never_repeats_the_skill_taken_from_the_first`、`test_deferred_offers_match_undeferred_rule`（改成逐組比對）、`test_formal_choice_after_two_steps`（逐組驗） |
| 閃現：4 級前擋、4 級後可；預先生成 4 級前不觸發 | `tests/api/test_opening_flash.py`（4 個）：`_CountingProvider` 把閃現提議用的 `MockLLMClient` 全留下來數呼叫次數，4 級前 0 次、4 級後與舊角色 > 0 |
| 舊角色的閃現、教學順序與改前相同 | `test_old_characters_flash_as_before`、`tests/api/test_opening_lessons.py::test_old_characters_keep_the_old_lesson_order`；既有的 `test_first_flash.py`、`test_newcomer.py`、`test_flash_world.py`、`test_world_pregen*.py`、`test_flash_api.py`、`test_newcomer_api.py` 一個斷言都沒改、全過 |
| 配點教學 | `tests/api/test_opening_lessons.py`（5 個）：入門期不出、選定後才出、略過與完成分開記、略過後回城鎮／營火再提示一次 |
| 4 級 | `tests/world/test_opening_end.py`（5 個）：真的打贏第 3 步 → `opening is None`、重選被擋、溶掉成功、閃現引導出現；其他經驗到 4 級也算；入門期先到 4 級不清 |
| 世界日誌重播（選定、重選、升 4 級） | `test_choice_reselect_level_4_log_replays_identically`：正式選定 → 選 2 組 → 重選 → 選 1 組、跳過 1 組 → 休息 → 出鎮遇敵 → 打贏升 4 級（`opening` 清掉）；重播與存檔往返一致 |
| API | `tests/api/test_opening_choice_api.py` 加 7 個（推薦端點 3、重選 3、背包滿 1）、`test_range_api.py` 加 1 個 |

改到的既有測試斷言（都是規格指定的改動造成，沒有放寬任何規則或驗證）：

| 檔案 | 改了什麼 | 原因 |
|---|---|---|
| `tests/world/test_opening.py` `DEMOS_148`、`tests/api/test_range_api.py` 招名 | 4 個技能 ID／中文名 | A1 換示範招 |
| `tests/world/test_opening_choice.py` `_check_offers`→`_check_offer`、`test_deferred_offers_match_undeferred_rule`；`tests/api/test_opening_choice_api.py` `len(pending_offers) == 2`→`1` | 選定當下只出第 1 組 | A2（PM 決定） |
| `tests/world/test_opening_stages.py::test_versions` | 24 → 25 | 版號 |

換示範招對 `tests/skillgen`、`tests/roguelite`、`tests/content/test_coverage.py`：**沒有任何固定種子或名單要改**，這三個目錄的測試檔一個都沒動、全過。示範招名單（`range.demos`）只有靶場與入門期在讀，這三個目錄的測試都不讀它；`test_coverage.py` 的「有被裝備」名單不看示範招，被換掉的三招本來就列在 `_POOL_ONLY`。`tests/skillgen/fixtures/refactor_3wr2.json` 裡還有舊的三招，測試照過（它在比什麼沒有細看）。

複雜度：沒有新增 `C901` 類 noqa（`world_newcomer_view.py` 原有的一個 `PLR2004` noqa 跟著那一行搬位置）。

## 3. 換招後三大類的推薦關鍵字（A5）

量法：`recommended_keywords`（開局種子 7、正式內容）。「用最多的入門招」分兩種情況各算一次；每大類取入門武器＋同大類另外 3 把＋別大類各 1 把。

| 入門大類 | 用最多的入門招 | 單手劍 | 雙手劍 | 匕首 | 矛 | 弓 | 火焰法杖 |
|---|---|---|---|---|---|---|---|
| 近戰 | 瞬步背刺 | 隱蔽 | 隱蔽 | 隱蔽 | 隱蔽 | 隱蔽 | 隱蔽 |
| 近戰 | 狂野之刃 | 隱蔽 | 隱蔽 | 隱蔽 | 隱蔽 | 隱蔽 | 隱蔽 |

| 入門大類 | 用最多的入門招 | 弓 | 弩 | 手槍 | 霰彈槍 | 單手劍 | 火焰法杖 |
|---|---|---|---|---|---|---|---|
| 遠程 | 淬毒箭 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 |
| 遠程 | 燧石飛刃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 | 中毒、點燃 |

| 入門大類 | 用最多的入門招 | 火焰法杖 | 冰霜法杖 | 單手劍 | 弓 |
|---|---|---|---|---|---|
| 法器 | 火焰箭 | 點燃、帶電 | 點燃、帶電 | 點燃、帶電 | 點燃、帶電 |
| 法器 | 火花連鎖 | 帶電、標記 | 帶電、標記 | 帶電 | 帶電 |

解讀：

- **近戰仍只推薦得出 1 個（隱蔽）**：狂野之刃沒有可選的專屬關鍵字，用最多的是它時照規則看另一招；隱蔽找不到能互相觸發的第 2 個，照 PM 決定只標 1 個。
- **遠程從 1 個（撞擊）變成 2 個（中毒、點燃）**：燧石飛刃沒有可選的專屬關鍵字（它利用的是油），所以兩種用法都落在淬毒箭的中毒。
- 法器「火花連鎖用最多」時第 2 個會隨武器變（法杖＝標記，單手劍與弓找不到）——這就是要照當下選的武器算的情況。
- **可以重選時端點回空清單**（見待決 1）。

## 4. 重選的順序與理由

`apply_reselect`（`world/opening_reselect.py`）：

| 步 | 做什麼 | 為什麼排在這裡 |
|---|---|---|
| 1 | 檢查：已正式選定、等級 < 4、沒用過、人在葛蘭所在的城鎮或主城、沒有待處理的遭遇（也沒有待選閃現）、武器在靶場、關鍵字合法 | 全部檢查完才動狀態；不合法時角色不變，也不會用掉那一次 |
| 2 | 依開局種子取新的起始 2 招 | 和靶場預覽、正式選定同一套、同一個種子；重選成原本那一套會拿到同樣 2 招 |
| 3 | 收回 `opening.granted_skills`（舊的起始 2 招＋第 1、2 步三選一拿到的）：裝備中與備用，連同 `generated_skills`、`flash`、`flash_bases`、`skill_usage`、`skill_regions`；還沒選的那組延後三選一也拿掉 | 先收回再給：新招和舊招同一招時，留下的是新給的、紀錄是空的。其他來源學到的招（機遇等）留著 |
| 4 | 收回起始武器本體：還拿在手上（不是物品）就直接換掉；玩家換過主手時，它是背包或主手欄裡那件基礎武器（`starter_item_id`），拿掉它與 `gear_mods` 紀錄；已經不在（賣、寄、分解）就不收回也不扣錢。玩家自己換上的主手收進背包 | 要在重建主角之前，主手欄先清空（「主手物品的武器必須是單位的武器」）；起始武器在背包時先拿掉會空出一格 |
| 5 | 新武器是雙手或成對：穿著的副手收進背包。第 4、5 步讓背包多出來的裝備放不下就拒絕（「不能重選：換下來的主手要收進背包，但背包放不下（需要 31 格，只有 30 格）」／「不能重選：不能選雙手劍：它占用副手…」） | 比照換主手與正式選定；要在動任何成長欄位之前擋 |
| 6 | 依新武器的大類重建基礎值；全部點數（`attribute_points`＋`attribute_spent`，正式選定後開局 4 點已經在 `attribute_spent` 裡）照推薦配法重配 | 同正式選定的 `chosen_hero`、`full_allocation`；玩家自己配過或重配過都不影響結果 |
| 7 | 新的起始 2 招排最前面；最大 HP、法力的變化走 `with_hp_change`，再把 HP、法力回滿 | 同正式選定 |
| 8 | `opening`：新武器、關鍵字、大類，`granted_skills`＝新的起始 2 招，`reselect_used = True`；`deferred_offers` 不動 | 重新出題與之後的 `granted_skills` 記錄都靠它 |
| 9 | 重新出延後三選一的第 1 組（選完才出第 2 組） | 最後才出：候選依新的武器、招、屬性產生；`offers_made` 繼續往下數（見待決 2） |

確認畫面用的資料在 `RangeView.reselect`：`returned_zh`（會收回的招）、`weapon_returned`（起始武器本體還在不在）、`lost_zh`（「雙手劍的強化 +3（材料不退）」這類，另含重骰、指定詞條）。事件 `OpeningReselectedEvent` 也帶 `returned`、`lost_zh`。

## 5. 配點教學（B8）

| 情況 | 行為 |
|---|---|
| 已完成開局的舊角色（`opening is None`、沒送過 `lesson:allocate_skip`） | 完全照舊：2 級、有沒分的點、在葛蘭的城鎮 → 教配點（`respec=False`）；之後接閃現 |
| 入門期（`stage == "starter"`） | 不出（就算手動重配出了沒分的點） |
| 正式選定後、三選一還沒選完 | 不出（這時只能送 `offer_pick`） |
| 正式選定後、在葛蘭的城鎮、沒上過、沒略過 | `LessonView{kind: allocate, respec: true}`：`points`＝全部點數（3 級是 8）、`start_points = 0`、`recommended`＝現在這套推薦配法 |
| 略過（前端送 `hint_seen` 的 `lesson:allocate_skip`） | 當下不再問；之後 **換過地點**（`world_step` 記 `lesson:allocate_left`）、第一次人在城鎮或營火時再出一次（`reminder: true`，台詞用 `allocate_again_lesson`）；出過記 `lesson:allocate_again` 就不再出 |
| 上完（`lesson:allocate`） | 不再出 |

`lesson:allocate_skip`、`lesson:allocate_again` 由前端送（OB-5／6 接），`lesson:allocate_left` 由伺服器記。都放在既有的 `hints_seen`，沒有新存檔欄位。

## 6. 版號

| 項目 | 變動 | 理由 |
|---|---|---|
| `WORLD_RULES_VERSION` | 24 → 25（只加一次） | 同一份日誌重播結果會變：延後三選一改成一次一組、新動作 `opening_reselect`、4 級前不能閃現、4 級清 `opening`、略過配點教學後換地點會記 `hints_seen`。`save.py` 有寫說明 |
| `CHAR_FORMAT`（`trpg-char/13`） | 不變 | 沒有新增存檔欄位：重選用 OB-1 已備好的 `reselect_used`、`granted_skills`；教學紀錄用既有的 `hints_seen` |
| `trpg-wlog`、`LOG_FORMAT`、`RULE_HASHES` | 不變 | 新動作只是 union 增項；沒動引擎與實地地圖 |
| 內容 digest | 會變 | `newcomer.yaml`（示範招、`demo_notes`、`allocate_again_lesson`） |

## 7. 待 PM 決定

1. **可以重選時推薦是空的**。第 1 個推薦要看「入門招用過幾次」，但入門招與它們的使用紀錄在正式選定時就收回了。端點照規格在可重選時有回應，只是 `keywords: []`。要有推薦的話，得在正式選定時把入門招的使用次數記進 `OpeningState`（加欄位、升 `CHAR_FORMAT`）。
2. **重選後的三選一不會和第一次一樣**：`offers_made` 繼續往下數（第一次用第 0、1 組的種子，重選用第 2、3 組）。重選成同一套武器與關鍵字時起始 2 招相同，但三選一候選不同。要「同一套就出同樣的題」的話要把計數退回去。
3. **起始武器本體靠基礎武器的物品 ID 認**（`base_<武器 ID>`，roguelite 既有的命名）。別人寄來同一種基礎武器的話分不出來，重選時會收回背包裡的第一件。目前想不到正常玩法會遇到。
4. **起始武器現在其實強化不了**：基礎武器沒有物品等級，鐵匠回「初始裝備不能強化」。所以「會損失的強化」清單目前恆為空；程式與測試照規格做了（測試直接擺一筆改動紀錄驗證）。
5. **開局結束的細節**：只清正式選定過的角色；還在入門期就先到 4 級的不清（清了就永遠拿著入門配備），等選定、兩組三選一選完才清，這種角色沒有重選可用。清掉時沒有事件，前端看 `opening` 變成 `null`、`reselect.blocked_zh` 得知。
6. **配點教學的「再提示」解讀**：「略過後第一次進城鎮或營火」做成「略過之後換過地點，再來第一次人在城鎮或營火」（留在原地休息不算）。再提示的台詞是實作者暫定（`allocate_again_lesson`：「上次沒動的屬性點還照推薦配著。想自己分的話，現在可以重來一次。」）。略過過的角色之後即使 `opening` 清掉，也走再提示這條路，不回到舊教學。
7. **沒改的台詞**（留給 OB-5／6）：升級畫面在入門期 2 級仍接「回霧渡鎮找導師堂的葛蘭，學怎麼配點」；`allocate_lesson` 第一句「身上多了兩點力氣」、`allocate_done_zh`「接下來看看你剛才用過的那一招」和新順序對不上；閃現被擋的原因「4 級前不能閃現（靈感會先存著）」、重選各種拒絕訊息、`OpeningReselectedEvent` 的句子都是暫定。
8. **閃現限制放在 `growth.py`**（沒動 `opening_gate`，避開 OB-4）。`flash_pick` 沒擋（4 級前開不出閃現，碰不到）。
9. **兩組候選有交集的種子沒有自然找到**：三大類 × 80 個角色共 240 組，照舊規則一起出的兩組沒有一次交集（候選大多是生成技能，ID 不重複，只有內容庫的技能可能撞）。測試改用「把舊規則第 2 組裡的內容庫技能放進第 1 組讓玩家選走」造出交集，再驗第 2 組不含它。
10. **正式選定與重選後，第 2 組三選一在玩家選完第 1 組時同步計算**（約 1～3 秒），背景預先計算幫不上；OB-5／6 的畫面要有等待提示。
11. **示範招「不綁武器」只有測試在檢查**，內容載入（`_range_problems`）沒加這條；要不要升成內容檢查。
12. **推薦端點用 GET＋query**；不能選定也不能重選時回 422（不是空清單）。
13. **重選後的影子**：世界裡那份舊影子留到下次城鎮整備才更新（別的玩家這段時間借到的是重選前的配備）。
14. `LessonView.respec` 的教學要前端先送 `respec` 再送 `allocate`（兩個都要在城鎮或營火，條件成立）；略過＝什麼都不送，維持推薦配法。

## 8. 沒驗證

- 八個目錄用一個 pytest 一次跑完的結果（兩次都卡住，改成分批；見第 2 節）。`scripts/check.py` 全量照守則沒跑。
- 重選後舊影子的行為（待決 13）只讀程式判斷（`save_after_prep` 只在整備動作後存），沒有寫測試。
- 起始武器本體能不能重骰、指定詞條沒有查，只確認強化被「初始裝備不能強化」擋住（待決 4）。
- 用新的入門招（狂野之刃、淬毒箭、燧石飛刃）打新手第 1、2 步的難度沒有量；近戰那組的表格測試有真的打贏兩場（AI 代打、換種子到贏為止），不代表勝率。
- 前端只跑了 typecheck 與 `src/world`、`src/api`、`src/ui`、`src/render`、`src/battle`、`src/dev`、`src/screens` 的 vitest（都過），沒有跑整包 `pnpm test`，也沒有開瀏覽器（本段沒有畫面改動）。
- 重選、配點教學的新 `hint_seen` ID 目前沒有前端會送，實際流程要等 OB-5／6 接上才走得到。
