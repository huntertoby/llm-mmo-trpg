# Phase RC-0 報告：組合器配方盤點

> 2026-11-14，main `7f32127b3` 起的分支；只讀，沒有改 `src/`、`content/`、`config/`、`docs/design/`。
> 規格：派工 prompt（專案 PM 轉使用者「先補這個」）＋ `docs/phases/技能生成-挑選模式提案.md` 7.1、7.7 第 0 段。
> 腳本 `scripts/recipe_census.py`；資料 `docs/phases/RC-0資料/census.json`（逐格）、`census.md`（摘要表）。

## 0. 給使用者的白話結論

把 16 個關鍵字加「不指定」共 17 列 × 主動／被動／反應 × 1～4 階 × common／rare／epic，切成 612 格，每格讓組合器各做 200 次（種子 0～199），用「退回路徑會收下」的標準算合格。

- **204 格本來就不存在**：被動技最低 epic、反應技最低 rare，這些格子遊戲不會出。
- 剩下 408 格裡：**正常 252、薄 14、空 142**。
- **空的 142 格裡有 40 格是規則上就做不出來，遊戲也不會出這題**：common 稀有度沒有任何原語能帶到潮濕、倒地、撞擊、高處、召喚物和 4 個層數關鍵字（它們的專屬寫法全部是 rare 以上），形態另有 4 格。這 40 格不用補。
- **真正的洞是 102 個空格＋14 個薄格，集中在兩處**：
  1. **被動與反應**：連擊、怒氣、專注、氣、高處、召喚物這 6 個關鍵字，被動、反應全部做不出來（潮濕的反應也做不出來，被動只做得出 1～6 個）。原因是組合器的被動、反應配方根本不會用到這些關鍵字的寫法，規則本身是允許的。
  2. **召喚物的主動技**：1 階 rare／epic 完全做不出，2～4 階只做得出 7～8 種設計（全是「獻祭召喚物」），因為組合器不會做「召喚」本身。
  - 形態（20 格）是內容刻意標記「組合器不做」，由手寫技能池供應，不算洞。
- 常見的組合（主動、沒關鍵字或帶點燃、冰凍、標記、隱蔽、中毒、帶電）都很健康：正常格的不同設計數中位 83，最少 12。

**Q4（common 召喚）要改規則才補得起來，建議不補；Q12（epic 被動＋高處）不用改規則，補組合器配方就好。**詳見第 3 節。

## 1. 做法

- **格子**：關鍵字照 `content/skill_keywords.yaml`（16 個，順序同檔案）＋不指定；種類 active／passive／reaction；階級 1～4（`player_tiers`：原型 `offer_tier_by_level` 與大世界 `hero_growth.skill_tier_by_level` 都是 1～3，機遇 `tier_up_permille` 150 可以再高 1 階，所以加 4 階；`tier_budget` 有 5 階，但玩家拿不到）；稀有度 common／rare／epic。**傳說跳過**：組合器做得出傳說（走 `_compose_legendary_result`），但三選一候選產生器一律不收傳說（`candidates._Search.usable`、PERF-3 `skip_legendary`），LLM 題目的稀有度也只有這三種（`TOPIC_RARITIES`）。
- **合法**：和 `proposal_fallback._from_composer` 收下的條件相同——`compose_with_stats` 不丟 `ComposeError`、`validate_skill` 沒有違規、`_fits`（種類、骨架、題目全部關鍵字，只看專屬規則）。參數也照它：種類不是主動時骨架＝種類，關鍵字照題目，`hero_attributes` 不給。
- **設計鍵**：骨架＋種類＋形狀類型＋效果類型（含狀態 ID）＋元素標籤（同共用筆記第 1 節）。
- **空格**＝0 合法；**薄格**＝不同設計 < 12（`--thin`，挑選模式 K=12）。**設計上不存在**＝種類的骨架稀有度下限高於這格。
- **會出題**（`reachable`）：遊戲出 LLM 題目時用的同一個檢查（`select_subset` 不出錯、`keywords_reachable` 帶得到關鍵字，`proposal_topic._make_topic_of_kind`）。不過＝這個稀有度／種類沒有該關鍵字的專屬寫法，遊戲不會出這題。
- **判斷**（空格、薄格才做）：另外不帶關鍵字組 50 個種子（層數關鍵字照組合器改用蓄力骨架），數有幾個帶到關鍵字——`keyword_hit`（組合器認的 `has_keyword`，含通用規則）與 `keyword_exclusive`（退回路徑認的，只看專屬規則）。依序判成：內容標記不做 → 規則擋下（不會出題）→ 規則或預算擋下（不帶關鍵字也組不出來）→ 配方稀少（偶爾帶到專屬）→ 只帶到通用規則（組合器認、退回路徑不收）→ 缺配方（規則允許但從不帶）。
- **頻率排序**：種類比例（`whiteboard.kind_permille` 700／200／100）× 組合器稀有度權重（35／35／20）× 階級頻率（兩張階級表平均：1 階 316‰、2 階 366‰、3 階 316‰；4 階＝3 階 × 150‰ ＝ 47‰）。
- **時間**：8 個行程 1161 秒（CPU 合計約 8970 秒）。**確定性**：每格只由自己的參數決定；計時以外的欄位，8 行程版和單行程版逐格比對相同（第 6 節）。

## 2. 空格與薄格清單（只列會出題的，依玩家遇到的頻率）

不會出題的 40 格（common 的潮濕、倒地、撞擊、高處、召喚物、連擊、怒氣、專注、氣各 4 階，加形態 common 4 階）不列；逐格在 `census.md`。

| 優先 | 格子（階） | 狀態 | 合法／設計 | 主要不合法原因 | 判斷 |
|---|---|---|---|---|---|
| 1 | 召喚物／主動／rare（1 階） | 空 | 0／0 | not_fit.keyword 127、not_fit.kind(reaction) 73 | **缺配方**：組合器只帶到通用規則（相鄰友方、對友方的效果）或抽成反應技；1 階能用的專屬寫法只有「號令」狀態（召喚、獻祭原語 2 階起，基本召喚物例外），組合器不會用 |
| 1 | 召喚物／主動／rare（2、3、4 階） | 薄 | 29／8、26／7、25／7 | not_fit.keyword ～100 | 缺配方：合法的全是獻祭骨架（`sacrifice_summon`），組合器不做召喚本身（`summon` 骨架 `hand_written_only`、`summon` 在 `_HAND_WRITTEN_PRIMITIVES`） |
| 2 | 召喚物／主動／epic（1 階空；2、3、4 階薄 37／8、27／8、31／8） | 空／薄 | 同上 | 同上 | 同上 |
| 3 | 連擊、怒氣、專注、氣／被動／epic（1～4 階，16 格） | 空 | 0／0 | keyword_exhausted 200 | **缺配方**：被動配方（`build_passive_effects`）不抽 `add_stack`／`consume_stack`、也沒有條件；規則允許（出題檢查通過） |
| 3 | 高處／被動／epic（1～4 階，Q12） | 空 | 0／0 | keyword_exhausted 200 | **缺配方**（見 3.2） |
| 3 | 召喚物／被動／epic（1～4 階） | 空 | 0／0 | keyword_exhausted 200 | 缺配方：被動配方不用召喚類寫法（對友方的效果是通用、號令狀態不在被動候選） |
| 3 | 潮濕／被動／epic（1～4 階） | 薄 | 6／6、4／4、3／3、1／1 | not_fit.keyword ～195 | 只帶到通用規則（治療）；專屬的「造水」表面、`on_enter_surface: water` 觸發極少出現 |
| 3 | 倒地／被動／epic（2、4 階） | 薄 | 182／8、197／8 | keyword_exhausted 18、3 | 配方稀少：幾乎都是「上倒地＋傷害」一種結構，只差元素（1、3 階剛好 ≥ 12） |
| 4 | 連擊、怒氣、專注、氣／反應／rare、epic（1～4 階，32 格） | 空 | 0／0 | keyword_exhausted 200 | 缺配方：反應配方不抽層數原語 |
| 4 | 高處／反應／rare、epic（1～4 階，8 格） | 空 | 0／0 | not_fit.keyword 200 | 只帶到通用規則（遠程武器傷害）；反應配方沒有高處條件、升降地形 |
| 4 | 召喚物／反應／rare、epic（8 格） | 空 | 0／0 | not_fit.keyword 200 | 只帶到通用規則（擋攻擊 `intercept`、對友方的效果） |
| 4 | 潮濕／反應／rare、epic（8 格） | 空 | 0／0 | not_fit.keyword 200 | 只帶到通用規則（治療） |
| 4 | 帶電／反應／rare、epic（1 階） | 薄 | 189／10 | keyword_exhausted 11 | 配方稀少：幾乎都是「雷傷害（＋推拉）」；2 階以上 ≥ 12 |
| — | 形態／主動 rare、epic，被動，反應（20 格） | 空 | 0／0 | keyword_not_composable 200 | 內容刻意 `composable: false`，手寫技能池供應（不算洞） |

注意兩個和挑選模式有關的現象：

- **組合器「認」關鍵字比退回路徑寬**：組合器指定關鍵字時用 `has_keyword`（含通用規則）判斷，退回路徑和三選一的候選用 `skill_has_keywords`（只看專屬）。所以召喚物、潮濕、高處的很多種子，組合器以為做到了、交出去卻被拒（表中 not_fit.keyword）。挑選模式如果用退回路徑的標準，這些都是白跑。
- **指定關鍵字又不指定骨架時會抽到別的種類**：例如召喚物／主動有 30%～40% 種子交出反應技（not_fit.kind）。

## 3. Q4、Q12 單獨分析

### 3.1 Q4：common 召喚物（LB 第 4 題）

- **為什麼做不出來**：召喚物關鍵字的所有專屬寫法最低都是 rare——`summon` 原語（結構型，`skill_primitives.yaml` `min_rarity: rare`）、`sacrifice_summon` 原語（rare）、號令狀態 `commanding`（`statuses.yaml` `min_rarity: rare`），規則改變與修正規則的召喚類更高。common 規則上就沒有寫法，所以**不是缺配方，是規則擋下**。出題檢查也不過（`reachable` 否）：遊戲裡 LLM 題目在這個稀有度會直接換下一個稀有度（`proposal_topic._make_topic_of_kind` 的 `keywords_reachable`），**玩家實際上不會遇到這題**。
- **這題怎麼來的**：只有 `trpg llm propose` 的評估題目會出（`cli/llm.py::_feasible` 只要三層退回有一層做得出技能就算可行，而第 ③ 層工坊推導不要求帶關鍵字）。
- **補起來要動哪裡**：
  - 不改規則的做法（建議）：評估題目的可行檢查也要求 `keywords_reachable`（`src/trpg/cli/llm.py::_feasible`），之後評估就不會再出 common 召喚。不影響遊戲。
  - 真要讓 common 也有召喚技：**要放寬規則**——把 `summon`（或號令狀態）的最低稀有度降到 common，還要定 common 召喚物的強度與預算。**這要使用者決定**，而且會動到「結構型原語 rare 起」這條通則。

### 3.2 Q12：epic 被動＋高處（LB 第 12 題）

- **為什麼做不出來**：高處的專屬寫法是召喚高處相關單位、升降地形、躍步、給飛行（都是手寫或主動才有），以及**條件** `height_advantage`、`self_on_high_ground`。組合器的被動配方（`random_composer._attempt_passive`）寫死 `"condition": None`，效果候選也沒有升降地形，所以 300 個變體都帶不到。**這是缺配方，不是規則擋下**（出題檢查通過）。
- **規則允不允許**：我用暫存腳本把組合器做出的 epic 被動（1 階、3 階各 60 個）直接加上技能層級條件 `self_on_high_ground` 或 `height_advantage`，**不重調數值**就有 46／60（1 階）、43／60（3 階）過驗證而且帶到高處；其餘只是 `budget.weak`（條件讓預算打折，強度 67%～68% 低於 70%），組合器本來的強度調整步驟就會補上。**不需要放寬規則、也不用改預算。**
- **補起來要動哪裡**：組合器程式 `src/trpg/skillgen/random_composer.py::_attempt_passive`（用獨立的 `Rng(seed).fork(...)` 串流抽條件，沒抽到的種子逐字不變），條件清單放 `content/skill_composer.yaml`（例如 `passive.conditions`＋`passive.condition_permille`）；組合器指定高處關鍵字時要抽得到這兩個條件。
- **要先問玩法 PM 的設計細節**：被動帶「目標比你低」（`height_advantage`）在觸發對象是自己時怎麼解讀；被動條件要不要也開放其他利用型條件（倒地、標記、潮濕的 `target_on_surface` 等），一起補會順便填掉潮濕被動的薄格。

## 4. 給 RC-1 的補洞建議清單

依玩家遇到的頻率；都只補配方，不動規則與預算（除了第 6 項）。每項補完用同一支腳本重跑對照（`--keywords`、`--kinds` 可以只跑那幾格）。

| # | 補什麼 | 要改的檔案 | 先問玩法 PM？ |
|---|---|---|---|
| 1 | **組合器召喚配方**（召喚物主動 rare／epic 1～4 階） | `src/trpg/skillgen/composer_parts.py`（`_HAND_WRITTEN_PRIMITIVES` 拿掉 `summon` 或另寫召喚分支）、`random_composer.py`（召喚骨架的組法）、`content/skeletons/summon.yaml`（`hand_written_only`）、`content/skill_composer.yaml`（可抽的召喚物、持續輪數範圍、機率；用獨立串流） | **要**：組合器可以抽哪些召喚物（1 階只能 `basic_summon_units` 兩種；帶固有關鍵字的召喚物算不算）、持續輪數、要不要附帶效果、召喚物長什麼樣（外觀 `summon_looks.yaml`） |
| 2 | **被動的層數配方**（連擊、怒氣、專注、氣 × 被動 epic） | `composer_parts.py::_passive_candidates`／`build_passive_effects`（附帶可抽 `add_stack`，KW-2 筆記：被動的附帶不限原語）、`skill_composer.yaml` | 要：被動累積層數的觸發時機（命中時？回合開始？）與數量；被動消耗層數要不要做 |
| 3 | **被動的條件**（高處＝Q12、順便潮濕、倒地） | `random_composer.py::_attempt_passive`、`skill_composer.yaml` | 要：見 3.2 |
| 4 | **被動的召喚物寫法**（召喚物 × 被動 epic） | `composer_parts.py::_passive_candidates`（號令狀態、對友方的效果——後者是通用，不算） | 要：被動召喚物技長什麼樣（例：命中時給號令？召喚物倒下時？`on_summon_downed` 目前 `random_composer: false`） |
| 5 | **反應的層數、高處、召喚物、潮濕配方** | `composer_parts.py` 反應段（`NON_INTERCEPT_EVENTS` 一帶）、`skill_composer.yaml` `reaction` | 要：反應技累積層數、反應技的高處寫法（站高處時才反擊？）、護主型召喚反應 |
| 6 | （可選）組合器指定關鍵字時改用專屬規則判斷 | `random_composer.py::_compose_with_keyword` | 不用問玩法，但**會改既有種子的結果**（三選一、run auto 快照），開發 PM 決定要不要做；做了可以少很多白跑 |
| 7 | 評估題目不出不會出現的題（Q4） | `src/trpg/cli/llm.py::_feasible` | 不用 |

形態（composable: false）照現行，不補。

## 5. 待 PM 決定

1. **Q4 要不要改規則**：建議不改（遊戲不會出 common 召喚題），只做第 4 節第 7 項；要做 common 召喚技就是放寬「召喚 rare 起」，要使用者決定。
2. **第 4 節第 6 項**（組合器改用專屬規則認關鍵字）會改「種子 → 技能」，要不要排進 RC-1。
3. 第 1～5 項的設計細節要先由玩法 PM 定（召喚物怎麼抽、被動與反應怎麼帶層數、被動條件的解讀）。
4. 盤點沒算「主動但指定骨架」的格子（例如 rune、trap 骨架 × 關鍵字），也沒算 5 階與傳說；需要時加 `--tiers 5`、`--rarities legendary` 重跑即可。

## 6. 腳本與驗證

- `uv run python scripts/recipe_census.py --workers 8`（預設全部格子、200 個種子、薄格門檻 12、診斷 50 個種子；`--keywords`、`--kinds`、`--tiers`、`--rarities`、`--seeds`、`--thin`、`--diag-seeds`、`--out-dir`、`--name` 可調）。平行用 `ProcessPoolExecutor`（最多 8），每格只由自己的參數決定。
- 確定性：以 `--workers 1 --keywords=-,wet,charged,prone --tiers 1` 重跑 36 格，計時以外的欄位和 8 行程版逐格相同（差異 0）。
- 測試 `tests/skillgen/test_recipe_census_rc0.py`（格子數、順序無關、門檻參數、骨架稀有度下限）。ruff、ruff format、`uv run mypy` 通過。
- 沒有平衡量測、沒有戰鬥模擬、沒有任何數值調整。

## 開發 PM 裁定（2026-11-14）

- **驗收通過，合併。** 只有新增的盤點腳本、測試和資料，src/、content/ 都沒動。有 36 格用單行程重跑，結果逐格相同。
- 待決 1（Q4 common 召喚）：這格是規則擋下，不是缺配方。遊戲出題時會跳過這個稀有度，玩家不會遇到。開發 PM 建議**不改規則**，RC-1 只修評估題的可行檢查（第 4 節第 7 項）。要不要做 common 召喚技屬於放寬規則，經專案 PM 問使用者。
- 待決 2（第 4 節第 6 項：組合器指定關鍵字時只用專屬規則判斷）：**排進 RC-1**。這是正確性修正，目前組合器以為做到的技能在退回路徑會被拒。會改「種子 → 技能」，三選一和 run auto 的快照要先預測哪些鍵會變，再只重產那些。
- 待決 3（第 1～5 項的設計細節）：一次整理給玩法 PM（3.0001）。玩法 PM 答覆後派 RC-1，一段做完第 1～7 項，不拆小段。
- 待決 4：先不算 5 階和傳說，之後需要再用腳本參數重跑。
