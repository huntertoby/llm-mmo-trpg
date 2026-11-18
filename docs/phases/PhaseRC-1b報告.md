# Phase RC-1b 報告：伴生護主推導、種類傳給組合器

> 2026-11-15，main `5805393db` 起的分支。規格：派工 prompt＋`docs/玩法PM交接.md` 4.1.20（玩法 PM 已定）。
> 資料：`docs/phases/RC-1b資料/`（`census.json`、`census.md`＝6 格的改後盤點，50 種子／格；`對照.md`＝改前改後）。

## 0. 白話結論

- **伴生、護主生效了**：「召喚到身邊」現在會推導出「召喚物」與召喚物本身的關鍵字（鷹＝標記＋高處、火靈＝點燃…），RC-1 寫好但沒生效的伴生（被動）、護主（反應）開始出現。盤點量到的召喚物被動、反應 2 階 epic 從空格變成 50／50 合法，探針看到護主 1、2 階也做得出來（其他階沒量完）；**召喚物反應 3～4 階仍是空格**：縮小版召喚物開到全強度也進不了 3 階起的預算窗（TF-1 已知的預算問題，不在這段範圍，列待決 1）。
- **「召喚物倒下時」被動**：grep 確認沒有殘留的配方或設定（只剩裝備詞條原本就有的觸發定義），不用拿。
- **目標型條件**：RC-1 的做法加測試鎖住——效果作用在自己的被動不會抽到居高臨下、目標倒地、目標被標記、目標站在水裡；高處只用「你站在高處」。
- **種類傳給組合器**：組合器多一個 `kinds` 參數。退回路徑、開局組合技、完整技能三選一（含許願、機遇）都會傳。RC-1 待決 8 的同類格子「標記／主動／epic 2 階」合法率 **68.5%（137／200）→ 100%（50／50）**，主動題不再交出被動、反應；1 階那格（185 → 116）因收尾沒重跑，交 PM 全量盤點確認。
- **規則、預算、引擎沒改**。關鍵字表在規則包裡，所以規則包雜湊會變；去掉規則包後 46 場戰鬥逐字相同（different=0）。
- **快照**：CLI 輸出雜湊、Mock 提議、圖示夾具、parity 夾具、卡片快照都沒變，**沒有重產任何快照**。只換了兩個許願測試的固定種子（斷言不動）。

## 1. 四項各改了什麼

| # | 項目 | 做了什麼 | 檔案 |
|---|---|---|---|
| 1 | 伴生、護主的關鍵字推導 | 「召喚物」`makes` 加 `{effect: summon_beside}`；15 條 `{effect: summon, unit: X}` 各鏡像一條 `{effect: summon_beside, unit: X}`（灌注那 9 條不鏡像：`summon_beside` 沒有灌注）。組合器的 `beside_keywords` 因此不再是空的，伴生、護主自動列入被動、反應的配方清單。另外 LLM 補強（`proposal_topup.keyword_effect_rules`）排除 `summon_beside`：LLM 題目本來就不出這個原語，不排除的話它會占掉「召喚物」補強的名額（`12_knock_prone_summon` 這題補不到號令） | `content/skill_keywords.yaml`、`src/trpg/skillgen/proposal_topup.py`、`composer_recipes.py`（說明） |
| 2 | 召喚物倒下時被動不做 | grep `on_summon_downed`／「倒下時」：`src/trpg/skillgen`、`skill_composer.yaml`、骨架、盤點腳本都沒有；`skill_triggers.yaml` 的定義本來就寫「只有裝備詞條使用、`random_composer: false`」。沒有要拿的 | — |
| 3 | 目標型條件只配作用在另一方的被動 | 沒改程式（RC-1 已是這樣），加測試 `test_self_passives_never_get_target_conditions`（高處、倒地、標記、潮濕 × 1、3 階 × 24 種子：`trigger.target: self` 的被動條件一定是施放者條件；`height_advantage` 一定配 `target: other`；高處被動作用在自己的確實有出現） | `tests/skillgen/test_composer_rc1b.py` |
| 4 | 知道種類的呼叫端傳種類 | `compose_with_stats`／`compose_random_skill` 加 `kinds`（`SkillKind` 的值）。只有一種而且不是主動（被動、反應、姿態、修正）＝ 用同名骨架（和明確傳骨架逐字相同）；含主動時，被動與特殊組法裡種類不符的不擲（反應、姿態、修正的獨立串流不擲，其他骨架的串流不變）；結果種類不符（例：傳說）時，指定關鍵字的變體跳過、不指定關鍵字的丟 `ComposeError`。`None` ＝ 原行為 | `src/trpg/skillgen/random_composer.py` |

**亂數**：`kinds=None` 時所有串流與 RC-1 相同（測試 `test_no_kind_is_unchanged`；圖示夾具 random 0～49 逐筆比對不變）。三選一擲種類用新的獨立串流 `composer.kind/<加深|橋接|新方向>`。

## 2. 改了哪些呼叫端

| 呼叫端 | 傳什麼 | 說明 |
|---|---|---|
| `skillgen/proposal_fallback._from_composer`（LLM 題目的退回路徑①） | `kinds=(wanted_kind,)` | 主動題不再交出被動、反應（原本被 `_fits` 擋掉、白白用掉嘗試）；被動、反應、姿態題原本就傳同名骨架 |
| `roguelite/start._composed_starter`（開局組合技，手寫池都沒有時的最後退路） | `kinds=("active",)` | `is_starter_skill` 只收主動（姿態只收化身，組合器不做） |
| `skillgen/candidates._Search.from_composer`（完整技能三選一；許願、機遇、故事都走這裡） | `composer_kinds(...)` 擲出的種類 | 每張候選（加深、橋接、新方向）照 `whiteboard.kind_permille`（主動 70／被動 20／反應 10，06 6.34.1、07 7.6）先擲：主動＝`("active","stance")`、被動＝`("passive",)`、反應＝`("reaction",)`。組合器做不出擲到的種類（`KeywordExhaustedError`）時這張改出主動（同白板「沒有這個種類的配方時改出主動」） |
| `scripts/recipe_census.py` | `kinds=(題目種類,)` | 盤點照退回路徑算 |

**沒改的呼叫端**（真的不指定種類）：工坊的隨機（`api/routes/workshop.py`，使用者自己選骨架）、`trpg skills random`、模擬（`sim/skill_fuzz.py`、`sim/skill_report.py`）、LLM 評估的組合器基準（`llm/skill_eval.composer_baseline`）、白板（`whiteboard_candidates` 本來就自己分種類，不經過 `compose_with_stats`）。

## 3. 快照（先預測，再對照）

| 鍵／測試 | 預測 | 實際 | 處理 |
|---|---|---|---|
| 規則包雜湊（`hash_ruleset`）、`ruleset_hash`、`content_digest` | 會變（關鍵字表在規則包內） | 變 | 無快照；舊戰鬥紀錄內嵌當時規則包仍可重播。使用者重開伺服器後進行中的一輪會從頭開始、世界日誌標成不能重播（同 QI-2a 等內容改動） |
| 戰鬥不變比對 46 場 | 整份 log 會不同（內嵌規則包），拿掉規則包後全同 | 整份 46 場不同；拿掉 `ruleset`／`ruleset_hash` 後 `battles=46 events=20458 different=0` | 照 LB-2c 拿掉規則包比 |
| CLI 輸出雜湊 `cli_output_hashes.json`（技能列表、技能卡、7 場戰鬥） | 不變（內建技能沒有 `summon_beside`；CLI 戰鬥輸出不印規則包） | 不變（`tests/cli -m slow` 44 passed，含 `test_run_cli` 固定種子） | 無 |
| `llm_propose_mock.txt` | 不變（Mock 答案取自手寫池；題目輪替不經過組合器的種類） | 不變 | 無 |
| `run auto` 固定種子 | 不變（升級三選一是白板，不經過 `generate_candidates`） | 不變（同上 44 passed） | 無 |
| parity 夾具 `refactor_3wr2.json`（完整強度、升階、閃現） | 不變（閃現轉型出的伴生、護主的 JSON 不含關鍵字；卡片文字不在夾具裡） | 不變（`test_refactor_parity.py -m slow` 928 passed） | 無 |
| 圖示夾具 `client/src/render/fixtures/skill_icons.json`（RC-1 漏過的那份） | 不變：`random` 是組合器種子 0～49 不指定種類、不指定關鍵字；第 1 項只改「被動／反應抽中新配方」時的配方清單，逐種子比對這 50 個沒有一個抽中；`skills` 是內建技能（沒有 `summon_beside`）；圖示不畫關鍵字 | 不變（`tests/narrative/test_skill_icon.py` 過；改前改後 50 筆逐筆相同） | 無；前端 vitest 讀這份的不受影響 |
| 其他前端夾具（`glossary.json`、`skillCards.json`、`unitDolls.json`、`raceLooks.json`、`dev/fixtures/flashChoice.json`） | 不變（術語表不含推導規則；技能卡是代表技能；選變體夾具是點燃斬） | 不變（`tests/api/test_client_fixtures.py` 過） | 無 |
| 卡片「製造：召喚物」 | **TF-1 閃現轉型出的伴生、護主卡片會開始顯示「製造：召喚物」**（＋召喚物本身的關鍵字），預期；沒有快照收這種卡 | — | 無 |
| `test_wish_two_keywords_txt2.py::test_one_card_carries_both_when_the_composer_can` 兩組 | 會變（三選一的組合器先擲種類） | 點燃＋標記種子 10、點燃＋倒地種子 37 不再帶兩個 | 10 → 2、37 → 6，斷言不動。掃 1～40（改前用 `git archive` 的 main 跑）：點燃＋標記 6 → 6、點燃＋倒地 3 → 3、帶電＋潮濕 1 → 2；三選一「指定帶電」三張齊全 31 → 34 |
| `test_pinned_keyword.py`（種子 1、13、23） | 可能變 | 三個種子仍齊全 | 無 |
| `test_upgrade_topup.py::test_reaction_keywords_the_composer_cannot_carry[summon]` | 會變（護主生效） | 3 階 epic 仍由工坊做（護主 3 階起進不了預算窗） | 斷言照實改：召喚物 3 階照舊工坊；另加 `test_guardian_reaction_comes_from_the_composer`（2 階 rare 由組合器做出護主） |
| `test_upgrade_topup.py::test_missing_keyword_is_topped_up[12_knock_prone_summon]` | **沒預測到** | 補強先試 `summon_beside`（主動技不能用、LLM 題目也不出），擠掉號令 | 改程式不改測試：補強排除 `summon_beside`（見第 1 節第 1 項），恢復原行為 |
| `test_random_composer.py::test_no_harmful_status_or_surface_is_aimed_at_allies` | **沒預測到** | 配方清單變長，某個不指定種類的被動種子改抽到 RC-1 的潮濕被動「受傷時在自己腳下造水」，被當成「對己方的有害表面」 | 這是 06 6.34.1 3W-4b 明寫的潮濕被動寫法；測試只對這一種（被動、`on_damaged`、對自己造水）放行，其餘照舊。列待決 3 |
| `test_composer_recipes_rc1.py` 兩項 | 會變 | `test_companion_and_guardian_wait_for_a_keyword_rule` 改成直接用內容庫驗（不再需要補規則的假內容庫）；Q12 高處被動測試允許伴生（召出鷹、高台圖騰帶高處，不靠條件） | 已改 |

## 4. 盤點改前改後（`scripts/recipe_census.py --keywords summon,marked`，200 種子／格）

改前＝`docs/phases/RC-1資料/census.json`（RC-1 合併時的全量盤點）；改後＝`docs/phases/RC-1b資料/census.json`（只跑 2 階 epic 的 6 格、50 種子／格）。對照表在 `RC-1b資料/對照.md`。

| 格子 | 改前（200 種子） | 改後（50 種子） |
|---|---|---|
| 標記／主動／2 階 epic | 正常 137 合法 | 正常 50 合法（100%） |
| 標記／被動、反應／2 階 epic | 200、199 | 50、49 |
| 召喚物／主動／2 階 epic | 200 | 50 |
| 召喚物／被動／2 階 epic | **空 0** | **50 合法**（伴生，設計 8） |
| 召喚物／反應／2 階 epic | **空 0** | **50 合法**（護主，設計 1） |

另以小探針確認召喚物反應（護主）每階 6 種子：1、2 階 rare 6／6；3 階 rare、epic 與 4 階 epic 0／6（見待決 1）。

**沒跑完的**：召喚物、標記兩列完整 72 格 × 200 種子跑了約 2.5 小時（4 個行程，主要耗在 common 與 3、4 階召喚物這類「300 個變體全試完都做不出來」的格子，每格單核 15 分鐘以上），收尾時停掉、沒有結果。1 階「標記／主動／epic」、召喚物被動 1、3、4 階等格子交 PM 的全量盤點補。

## 5. 檢查

- `ruff check`、`ruff format --check`（全 repo）、`uv run mypy`（1636 檔無錯）、`lint-imports`（14 kept）、`tests/test_architecture.py`。
- 測試：`tests/skillgen`＋`tests/content`（第一輪 7485 passed、5 failed，即上表會變的 5 項；改完後逐檔重跑通過）、`tests/roguelite`（244 passed）、`tests/llm`（445 passed）、`tests/world`／`tests/api` 中許願、機遇、三選一、開局相關 8 檔（103 passed）、`tests/narrative/test_skill_icon.py`＋`tests/api/test_client_fixtures.py`、`tests/cli -m slow`（44 passed）、`tests/sim -m slow`（19 passed）、`test_refactor_parity.py -m slow`（928 passed）。
- **耗時**：最久的是盤點（召喚物、標記兩列 200 種子跑了約 2.5 小時沒跑完，見第 4 節），其次是同時跑多組測試互搶 CPU（`tests/skillgen`＋`tests/content` 一輪 8 分鐘；個別含 300 種子組合的測試在高負載下要 5 分鐘）。
- 沒跑 `scripts/check.py` 全量、沒跑平衡量測或戰鬥模擬、沒改數值。前端 vitest 沒跑（worktree 沒有 `client/node_modules`）；前端夾具預測都不變，見第 3 節。

## 6. 待 PM 決定

1. **護主 3～4 階進不了預算窗**：縮小版召喚物強度上限 1000‰（`_power_tries`，同 TF-1），召喚到身邊沒有骰子可調，3 階起所有組合都低於預算下限，所以召喚物反應 3、4 階仍是空格（退回路徑由工坊做）。伴生（被動）2 階 epic 50／50 合法，3、4 階沒量（盤點沒跑完）。要補得改預算（例：護主允許更長的存在輪數或縮放），屬數值，交使用者在工坊調或玩法 PM 定。
2. **三選一的種類比例借用白板的 `whiteboard.kind_permille`**（70／20／10）。完整技能三選一的組合器候選現在照這個比例；手寫池與 LLM 來源沒動（LLM 題目照舊 `llm_reaction_permille` 10% 反應、不出被動）。如果完整技能要另一組比例，再加設定。擲到被動、反應但組合器做不出這個關鍵字時改出主動。
3. **潮濕被動「在自己腳下造水」和舊測試的規則衝突**：06 6.34.1 3W-4b 明寫這個寫法，但 `test_no_harmful_status_or_surface_is_aimed_at_allies`（「不對自己造有害表面」）原本沒碰到。測試只對這一種放行；請確認這是想要的（站在水裡會被雷導電、冰凍）。
4. **組合器的關鍵字檢查和三選一／退回路徑不一致（RC-1 前就有，本段發現）**：組合器的 `has_keyword(exclusive_only=True)` 會把戰場變奏（`variants`）帶的元素算進去，三選一與退回路徑用的 `skill_has_keywords`（`derive_keywords`）不算。例：1 階 epic 指定點燃、種子 13，組合器交出「物理打擊＋水窪・火焰變奏」，退回路徑判沒帶點燃而丟掉。影響是浪費嘗試，不會交出錯的技能。要不要統一，開發 PM 定。
5. **伴生、護主的卡片**：TF-1 閃現轉型出的伴生、護主開始顯示「製造：召喚物」（＋召喚物本身的關鍵字），照 4.1.20 是預期的；沒有快照收這種卡，前端如有實機截圖要更新請美術／開發 PM 留意。

## 7. commit

分支 `worktree-agent-ac12f59f263645035`，未 push（`git log 5805393db..HEAD`）：

- `f51b9db01` feat(rc-1b): derive summon keywords from summon_beside (companion, guardian)
- `2534d0bc3` feat(rc-1b): callers that know the skill kind pass it to the composer
- 之後：報告與盤點資料

## 開發 PM 裁定（2026-11-15）

- **驗收通過，合併。** 規則、預算、引擎都沒改。快照全部照預測不變，沒有重產。戰鬥 46 場拿掉規則包後 different=0；規則包雜湊會變，是因為關鍵字表在規則包裡，接受。
- **測試放寬（push 前已回報）**：`test_no_harmful_status_or_surface_is_aimed_at_allies` 只對一種寫法放行：被動、受到傷害時（on_damaged）、在自己腳下造水。依據是 06 6.34.1 3W-4b 的原文「潮濕被動：被攻擊後，在自己腳下造水」。專案 PM 轉使用者 2026-11-15 原話「A」，保留。測試註解也寫明了。
- 待決 1（護主 3～4 階進不了預算窗）：這是數值問題，轉給玩法 PM 記進平衡待查，由使用者在工坊調。這段不改預算。
- 待決 2（三選一照白板的 70／20／10 擲種類）：接受，和 06 6.34.1 一致。
- 待決 4（組合器判斷關鍵字時把戰場變奏算進去，三選一和退回路徑不算）：記入開發佇列，之後做小修。影響只是浪費嘗試，不會交出錯的技能。
- 待決 5：預期內。
- 盤點只跑了部分格子（agent 跑太久，使用者要求收尾）。完整盤點等下一次碰組合器時再用腳本重跑。
- RC-1 補記：RC-1b 合併後那次全量的結果寫在 RC-1 報告裁定段。
