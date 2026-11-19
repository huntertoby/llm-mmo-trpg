# 階段 AP-2 報告：#168 內容＋預支技能

> 2026-11-19，實作者。依據：`docs/phases/PhaseAP-2計畫.md`、06 6.3「新原語『預支』」、05 5.2「⚠ AP 改版」、06 6.34.1 ⚠、`docs/art/AP-1-AP列畫法.md` 第 2～6 節。
> 分支 `worktree-agent-abb585836203f496f`（開工 `git merge main`，快轉到 `e2344ccc7`，含 AP-1、SK-5）。不 push。
> 數值都是初值、都進工坊；沒有試數值、沒有跑平衡量測（戰鬥不變比對、白板 AP 預測除外）。沒有改 `docs/design/`、`config/`。

## 1. 做了什麼

| 項目 | commit | 內容 |
|---|---|---|
| 1 預支原語 | `2ab8e1173` | `borrow_ap`（`rewrites.borrow_ap`）：本回合 +N（不超過 `ap_cap`，實際拿到的才算）、狀態 `borrowed_ap`（`ap_penalty_per_amount`：下回合扣狀態的數值，同回合預支兩次相加）、`UnitState.ap_borrowed` 讓這回合不保留 AP、`ap_lost_borrowed`；和透支疊加、AP 最少 0；一點都拿不到時落空（`effect_fizzled ap_cap`）不扣。事件 `ap_borrowed`、紀錄文字。0 AP 只放行 `SkillDef.borrows_ap`，帶預支的必須 0 AP、唯一效果、形狀 self、只能主動。預算 `skill_budget.yaml` `borrow_ap_points`（0，工坊）、0 AP 照 1 AP 係數、不套過弱下限。AI：`self_costs.borrow_allowed`（預支後才放得出另一招）、分數同給自己 AP。`borrowed_ap` 是 `mechanic_only`（新旗標，同 `enemy_only` 不進技能池）。`LOG_FORMAT` `/134 → /135` |
| 2 基本款預支技能 | `bc5a05390` | `skill_borrowed_beat`「搶拍」：稀有、1 階、不限武器、光環、0 AP、冷卻 2、法力 1、預支 1、只給自己；沒有關鍵字（通用池）。閃現大變化 `borrow_deep`（預支 2、每場 1 次；預支技能只出這一類補充大變化）。許願：效果「增益」＋形狀「自身周圍」時手寫的預支技能放進候選（`wish_pick._borrow_draws`），`skill_pick.yaml` 增益標籤加 `borrow_ap`。`units/` 的範本只有標籤 `elite`／`boss` 可以帶預支技能（載入時檢查；目前沒有範本帶）。光環骨架核心加 `borrow_ap`（LLM 題目先排除，第 4 項才開）。預支技能不套改寫規則的冷卻下限 |
| 3 AP 相關內容 | `87c913d19` | 被動與詞條新觸發 `on_ap_spent_all`「這回合用完所有 AP 時」（`battle.run_action` 包住每個動作：動作前有 AP、動作後 0、還站著、回合沒換人；每輪最多 1 次；係數 400‰，工坊既有欄位）。詞條 `affix_trig_every3_ap`「每第 3 次命中：回 1 AP（每回合 1 次）」，和「擊殺回 AP」同一族（族名沿用原詞條 ID）。「擊倒返還 1 AP」的閃現小變化（收割）本來就沒有稀有度門檻，補測試確認普通、稀有技能做得出來。前端：新狀態、原語、觸發的圖示（暫用圖，見待決 6）與相關 vitest 計數 |
| 4 組合器、LLM | `b46d77c3b` | 組合器獨立串流 `composer.borrow_core`（光環、稀有以上，50‰）做基本款預支；`composer.ap_spent`（史詩被動，50‰）把觸發改成「用完所有 AP 時」；沒抽中的種子不變。LLM：光環題目可以出預支核心（指定關鍵字的題目不出）、補值器把預支補成 0 AP 與冷卻下限；驗證器：預支要每場 1 次或冷卻 ≥ `borrow_min_cooldown`（2）。`PROMPT_VERSION` `skill-proposal/23 → /24`（prompt 文字雜湊不變，改在 available／schema 層）。兩個機率進工坊 |
| 5 前端 AP 列 | `38a15578d` | `UnitView` 多 `ap_borrowed`、`ap_lost_borrowed`、`ap_next_loss_borrowed`（OpenAPI、`schema.d.ts` 重產）。AP 列：`[一般][這回合少掉][保留][預支菱形] ｜ [下回合紅斜線]`；菱形 9 px 級（7 px 正方形轉 45°）實心橘 `#ff9a3a`／框 `#b8641a`，用掉變空心橘框；菱形與下回合紅斜線淡入 200 ms；預支的回合不閃「會保留」；菱形、紅斜線各最多畫 2 個；超過 9 顆改寫數字（13 px）。用字照畫法第 5 節。不做預支按鈕。截圖 4 組 |
| 6 白板主動技預設 1 AP | `e47a43893` | `whiteboard.ap_cost` 2 → 1、新 `fallback_ap_cost` 2：1 AP 調不進預算窗就照預算調退回 2 AP 再調一次（配方自己寫 AP 的不變）；白板驗證收 1 或 2；兩個值進工坊 |
| 報告 | （本 commit） | 本報告、`上手-引擎戰鬥結算.md` 第 58 點、許願覆蓋表重跑 |

## 2. 檢查（結束碼）

每個 commit 前都跑 ruff、format、mypy、lint-imports、`trpg content check`，以及 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`（第 1～6 項各一次：980～982 passed，第 6 項第一次 2 failed 見第 4 節，改種子後該檔 0）。

| 指令 | 結束碼 |
|---|---|
| `ruff check .`／`ruff format --check .` | 0／0 |
| `mypy`（1727 檔） | 0 |
| `lint-imports`（14 kept） | 0 |
| `trpg content check` | 0 |
| 前端 `tsc --noEmit`、`pnpm -C client build` | 0、0 |
| 全部 vitest（最後：385 檔 4766）。第 3 項前跑過一次有 16 個失敗，全是新狀態／原語／觸發的圖示計數與基準，第 3 項補上 | 0 |
| pytest 分目錄一次一組（最多 `-n 8`，見下） | 0 |
| 重播：`trpg battle --map open_plain --seed 10 --log-json` ＋ `battle replay` | 0（71 個動作、311 個事件，同 AP-1） |
| `scripts/wish_coverage.py run --seeds 40 --workers 8`、`report` | 0、0（見第 6 節） |

pytest（最後一次）：content 3142、engine＋narrative 5591（第 4 項）／engine＋narrative＋cli 5742（第 6 項）、api 1331（1 skip）、skillgen 4616～4624（14 skip）、llm 496、world 1328、roguelite 279、sim 180。全量 `scripts/check.py` 沒跑（PM 跑）。

## 3. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive e2344ccc7` 的 `src content config`、`PYTHONPATH` 指向舊 `src`（印出 `trpg` 路徑確認）；地圖預設陣容、效用 AI、`max_rounds=30`；10 張一般圖 × 種子 1、2 ＋ 4 張頭目圖 × 種子 3～12（同 AP-1）；比整份事件、步驟、最終狀態（去掉 `ruleset`、`ruleset_hash`、`format` 與新欄位 `ap_borrowed`、`ap_lost_borrowed`）。

| 時間點 | 結果 |
|---|---|
| 第 1 項 | `battles=60 events=21155 different=0` |
| 第 2 項 | different=0 |
| 第 3 項 | different=0（沒有單位帶新觸發與新詞條；`run_action` 沒有持有者時什麼都不做） |
| 第 4 項 | different=0 |
| 第 6 項（白板 1 AP） | different=0；工坊把 `whiteboard.ap_cost` 調回 2 也是 different=0（地圖預設陣容不用白板） |

（events 21155 和 AP-1 報告的 23897 不同：AP-1 那個數字是工坊值關回舊行為時的；這裡是 AP-1 的初值。）

## 4. 快照、夾具（先預測再逐鍵核對）

| 東西 | 預測 | 結果 |
|---|---|---|
| `glossary.json` | 第 1 項：多 `borrow_ap`（效果）、`borrowed_ap`（狀態）；第 3 項：多 `on_ap_spent_all`（觸發） | 對：比對腳本列出只多這 3 筆，各自重產 |
| `skill_icons.json` | 第 1 項不該變；第 2 項只多 `skill_borrowed_beat` | 第 1 項一開始 random 第 2、41 號變了：組合器「目標有某狀態」條件從全部減益狀態抽，新狀態擠進清單。改成 `mechanic_only` 不進技能池後回到原值。第 2 項只多那一招 |
| CLI 快照（24 鍵） | 第 2 項：`skills_list` 與 `skills_show_all/01～15` 變（新招 ID 排第 37、每片 28 招，之後整排位移），00 片與 7 場戰鬥不變 | 對：16 鍵，`-k "skills_list or (skills_show_all and not 00)"` 不加 `-n` 重產 |
| parity `refactor_3wr2.json` | 第 2 項：`complete`、`retier` 各多新招一鍵，其他不變 | 對：只用腳本加這 2 鍵，沒有整份重產 |
| OpenAPI、`schema.d.ts` | 第 5 項：`UnitView` 多 3 個欄位 | 對（openapi 15 行、TS 6 行） |
| `statusFit.json`（前端，不手改） | 第 3 項：多 `borrowed_ap` 兩鍵，其他不變 | 開發頁 `?set=fitgen` 在無頭 Chrome 量出來：只多這兩鍵（值同透支，圖形同） |
| `qi3bStatusBaseline.json` | 只多 `head|borrowed_ap`、`card|borrowed_ap`，既有 236 鍵不重錄 | 用同一段 `record()` 只算這兩鍵（同時算透支確認和基準相同）；QI-2c 舊基準不加，測試改成 QI-3b 之後的新狀態另列 |
| 第 6 項白板 | 預測腳本（種子 0～59 × 1～3 階主動白板）：180 張裡 141 張變（124 張 2→1 AP、13 張退回 2 AP、30 張本來 1 AP、12 張姿態），所以鎖住「某個種子的白板」的測試都會變 | 對：失敗的都是種子樣本測試，見第 5 節 |

## 5. 為新規則改的測試

- 鎖回舊樣本（新小工具 `tests/engine/helpers.with_whiteboard_ap(lib, 2)`）：點燃斬種子 75 的閃現費用測試（`test_flash_cost_fl1a`、`fl1e`、`test_flash_text_fl1b`）、淬毒追不上 3 階（`test_skill_tier`）、`test_retier_keeps_the_ratio`（點燃斬 1 AP 時升 2 階比例差 12.6%，見待決 9）、重閃重現案例 rr1、rr2。
- LLM 題目樣本：`test_upgrade_topup_distribution` 加 `without_ap2_offers`（同 SK-2b、SK-3b 的做法）。
- 換種子：`run auto` 11、13 → 17、18（重掃 11～20：17、18、20）。
- 計數與清單：工坊說明 186 → 188、詞條 80 → 81、技能 433 → 434、內建技能檔 430 → 431、閃現大標 103 → 104、改寫規則原語集合、觸發「沒有另一方」集合、組合規則 sole_effect 集合、工坊欄位清單、狀態點數表、`RARELY`… 都是加一筆；前端圖示的狀態 118 → 119、部件暫代 +1、`ADDED_AFTER_BASELINE` 加搶拍。
- `test_rewrite_primitives` 的「每個改寫規則原語都有裝在 build 上的手寫技能」排除預支（不裝在示範 build，避免改既有戰鬥）；`test_coverage` 的 `_POOL_ONLY` 加搶拍、`borrowed_ap` 與 `on_ap_spent_all` 進允許清單。
- 新測試：`tests/engine/test_borrow_ap_ap2.py`（+N／−N、+2、上限、到頂落空、預支回合不保留、兩次相加、和透支疊加最少 0、確定性、0 AP 只放行預支、預支必須 0 AP 與唯一效果、AI 使用條件 6 例、效用 AI 分數）、`test_ap_content_ap2.py`、`test_ap_view_ap2.py`、`tests/skillgen/test_borrow_skill_ap2.py`、`test_borrow_offers_ap2.py`、`test_whiteboard_ap1_ap2.py`、前端 `apRow.test.ts` 7 條。

## 6. 截圖（`docs/art/shots/ap-2/`）與許願覆蓋表

無頭 Chrome（`--headless=new --mute-audio --disable-gpu`，DPR 1）＋網址 `?dev=1&mute=1`；自己的 `trpg serve`（埠 8766）＋暫存 vite 設定（埠 5294，`/api` 轉 8766，用完刪掉）＋ CDP 埠 9739。戰鬥先用 API 推到要拍的那一刻（`open_plain` 種子 3、鐵壁起始包＋工坊試玩的自訂技能：搶拍、豪借・搶拍〔預支 2、每場 1 次〕、竭力護體〔自身護盾＋透支 1〕），頁面按「一鍵開局」時把建立戰鬥的回應換成 `GET /api/battles/<id>`。都是真的遊戲畫面，沒有改回應數字。結束時瀏覽器用 CDP 關掉、server 與 vite 停掉（vite 的 node 子程序另外結束），三個埠都關了。每張附 `*_ap_x4.png`（AP 那一格 4 倍重新算繪）。

| 第 6 節 | 檔名 | 畫面 |
|---|---|---|
| 2 | `2_borrow.jpg` | 回合開始 4 AP，施放搶拍後：4 顆金＋1 顆橘菱形｜1 顆紅斜線（「預支：下回合少 1 AP」） |
| 5 | `5_borrow_800.png`（真 1 倍）、`5_borrow_800_ap_nn6.png`（最近鄰 ×6） | 800×600，同狀態 2 |
| 6 | `6_next_turn_minus2.jpg` | 竭力護體（透支）＋搶拍：分隔線右邊兩顆紅斜線「下回合少 2 AP」——取代 AP-1 改數字的那張 |
| 7 | `7_borrow_two.jpg` | 跑步（1 AP）後豪借（預支 2）：4 顆金＋2 顆菱形（第 2 顆空心，見待決 5）｜2 顆紅斜線 |

許願覆蓋表：`wish_coverage.py run --seeds 40 --workers 8`（768 桶，1444 秒）＋ `report`（結束碼 0、0），更新 `docs/phases/許願覆蓋表-WC2.md`。做不到 85 → 87 項（a 56 → 57、需人工 10 → 11）、極低 36 → 34 項；變動來自組合器的兩條新串流（光環稀有以上改出預支、史詩被動改成「用完所有 AP 時」）讓少數格的成功率上下 1～3 點。覆蓋表只看組合器，許願池另外放進的手寫預支技能（增益＋自身）不在表裡。

## 7. 待 PM 決定

1. **預支的範圍比規格嚴一點（解讀）**：帶預支的技能必須 0 AP、預支是唯一效果、形狀 self、只能主動；0 AP 只放行它。預支一點都拿不到（已到上限）時落空、不扣下回合；扣回的是實際拿到的量。
2. **預算**：預支每 1 AP 算 `borrow_ap_points`（0）；0 AP 的可用預算照 1 AP 係數算、不套過弱下限，只擋超出預算。預支不算進裝備的 AP 回復上限（`ap_gain_turn`）。不套改寫規則型「每場一次或冷卻 ≥ 4」，改成「每場一次或冷卻 ≥ `borrow_min_cooldown`（2）」（沒冷卻＝每回合都能預支，是選項題 3 C）。
3. **基本款搶拍花 1 點法力**：沿用「主動法術技至少 1 法力」的既有規則；設計寫「代價是冷卻與稀有度」，要 0 法力就得給預支開例外。
4. **敵人**：只加了「`units/` 的範本只有 elite／boss 標籤能帶預支」的載入檢查與 AI 使用條件，**沒有給任何精英、頭目裝上預支**（裝上去會改既有戰鬥）。效用 AI 給預支的分數同「給自己 1 AP」，實戰中常輸給直接普攻，所以就算條件成立也不一定預支。大世界加精英詞條的敵人沒有另外檢查。
5. **AP 列的空心順序**：沿用 AP-1「從右邊開始變空心」，所以先花 1 AP 再預支 2 時，空心的是第 2 顆菱形（截圖 7）。菱形用 7 px 正方形轉 45°（外接約 10 px），請美術確認大小。
6. **前端圖示是暫用的**：狀態「預支」用透支的閃電＋橘色減號（Q 版）與透支的舊圖；原語「預支」暫借給予 AP、觸發「用完所有 AP 時」暫借「回合結束時」（部件暫代清單各 +1）；動畫暫借給予 AP 的拍肩。請美術 PM 補畫。
7. **「擊倒返還 1 AP 放進普通、稀有的閃現與詞條」**：閃現（收割）本來就不限稀有度，只補測試；詞條「擊殺時回 1 AP」只在稀有以上的物品（觸發類），**普通物品照 08 8.7 只有數值類詞條，沒有加**——要讓普通物品也出，需要改稀有度表，請玩法 PM 決定。
8. **新觸發係數 400‰、新詞條每第 3 次命中、組合器兩條串流各 50‰** 都是初值；觸發每輪最多 1 次寫死在驗證。
9. **白板 1 AP 的影響**：點燃斬（燃燒的白板）1 AP 升 2 階時比例差 12.6%，超過升階測試的 10% 容許（測試鎖回 2 AP 樣本）；退回 2 AP 的條件用「1 AP 調不進預算窗（含超出上限）」，不只「低於下限」。白板 1 AP 後大部分三選一、任務、創角白板都變了（預測 180 張變 141 張）。
10. **工坊做不出預支**：工坊的 AP 選單照舊 1～3，預支技能在「內容庫每招都對得上選項」的測試裡排除。
11. **LLM**：指定關鍵字的題目不出預支核心（預支沒有關鍵字）；`PROMPT_VERSION` 升 `/24`。第 1 項加的 `borrow_ap` 已經讓提議 schema 的版型清單多一個「唯一效果」版型，版號到第 4 項才升。
12. **第 1 項 commit 的前端計數**：第 1 項改了 `glossary.json`，但前端狀態計數（118 → 119）與圖示到第 3 項才補，第 1、2 項的 commit 單獨看 vitest `src/render`、`qi3bStatusCorner` 會失敗。

## 開發 PM 裁定（2026-11-19）

合併：`Merge AP-2`（--no-ff）。合併後 ruff、format、mypy、lint-imports、`trpg content check` 都是 0；全量檢查合併後跑一次。

待決 12 件：
1. 接受。範圍比規格嚴，是最保守的做法；要放寬再另外排。
2. 接受。預算、冷卻下限都是初值，放在工坊。
3. **照設計改**：設計寫明搶拍的代價只有冷卻和稀有度，所以要給預支開例外，改成 0 法力。排進下一個小段。
4. 接受。先不給既有精英、頭目裝上預支，以免改到既有戰鬥。要裝哪幾隻，排進下一個內容段。
5. 接受，轉美術 PM 確認菱形大小和空心順序。
6. 轉美術 PM 補畫圖示和動畫，交件後排移植。
7. 接受。普通物品照 08 8.7，不加「擊殺時回 1 AP」；計畫的說法和設計衝突，轉玩法 PM 決定要不要改稀有度表。
8. 接受。都是初值。
9. 接受。白板改 1 AP 後，三選一、任務、創角白板預測 180 張、實際 141 張變動，都在預期內。
10. 接受。工坊的 AP 選單維持 1～3。
11. 接受。版號 /24 只升一次就好。
12. 記一次：計畫要求每個 commit 都乾淨，第 1、2 項的 commit 單獨跑前端測試會失敗。已合併，不改歷史；下次狀態計數要和改 `glossary.json` 放在同一個 commit。
