# Phase TR-1 報告：#134 開局在主城工坊靶場試用後選武器

> 實作者：worktree `dev/r134`（從 main `9979a7e4` 開）。沒有 push、沒有 rebase。依據：決定 #134（`docs/archive/玩法決定紀錄_1-138.md`，使用者原話「b主城靶場試用再決定」）；`docs/design/21` 21.5「工坊靶場」、`09` 9.6.9、`07` 7.6／7.7、`06` 6.27.3、`18` 18.7.1；`docs/art/畫風回舊版暫停清單.md` 第 1 節。沒碰 HID-1（戰鬥檢視過濾、`client/src/battle`、`client/src/ui` 的單位卡與 HUD）與 R1d（`skillgen/proposal*`、`engine/preview.py`）的檔案；沙盒試打直接用既有戰鬥畫面（`BattleScreen`，只傳既有的 props）。

## 0. 逐項規格與驗收（動手前寫定）

| # | 規格 | 驗收 |
|---|---|---|
| 1 | 大世界建角只選名字、種族、外觀、出身（07 7.7）；`POST /api/world/characters` 的 `weapon`／`keywords` 改選填，正式流程兩個都不給 | 建角不給武器 → 201，角色有 `opening`、拿佔位武器（拳套）、沒有技能；只給一個 → 422（`tests/api/test_range_api.py`） |
| 2 | 角色多「未完成開局（在靶場）」狀態 `CharacterState.opening`（起始技能種子）；角色格式 `trpg-char/12`；`/11` 以前照讀＝已完成開局 | 舊存檔遷移測試（`tests/world/test_opening.py::test_old_save_counts_as_done`） |
| 3 | 未完成開局時只能做 `opening_confirm`、`news_seen`、只記畫面紀錄的動作；其他 422「先在主城工坊靶場選好武器與兩個關鍵字…」 | `test_pending_only_confirm_and_notes`、`test_pending_blocks_other_actions` |
| 4 | 世界動作 `opening_confirm {weapon, keywords}`（寫進世界日誌、可重播）：照 6.27.3 每個關鍵字池各給 1 招（和 roguelite 開局同一套 `new_keyword_run`，#129 觸發優先、#133 推薦配法）；名字、種族、外觀照建角；HP 法力回滿；事件 `opening_confirmed` | 確定性（同種子同結果）；和舊流程（建角就選）結果逐欄相同；選擇不合法 422 且狀態不變 |
| 5 | 出發之後不能重選（21.5） | 再送 `opening_confirm` → 422「不能重選」；試打 → 422 |
| 6 | 沙盒試打 `POST …/range/trial {weapon, keywords}`：記憶體裡開一場戰鬥（戰鬥工作階段表、不登記成角色的戰鬥）；木樁 3 個（會動、站水上、普通）；`keywords` 空＝普攻＋該大類 2 招示範招，給了＝依序給的起始技能（看示範，最多 2 個）；種子由開局種子＋選擇衍生 | 不寫日誌、角色存檔逐欄不變（HP、法力、經驗、背包）、世界畫面沒有進行中的戰鬥；同選擇同種子同戰場；會動的木樁有人靠近時退開、木樁不攻擊（`test_dummies_never_attack_and_moving_one_backs_off`） |
| 7 | 新內容放 `content/`、pydantic 驗證：`world/newcomer.yaml` 的 `range`（武器架順序、佔位武器、地圖、位置、木樁、示範招、守印人台詞）、`units/training_dummy_moving.yaml`、AI 行為 `drift` | 載入時交叉檢查（地圖、單位、示範招存在；1 階主動技；該大類每把武器都能用；位置在圖內、不重疊） |
| 8 | 畫面：未完成開局時（醒來卡「站起來」之後）世界畫面改成工坊靶場：武器架（近戰／遠程／法器）、武器介紹與示範招、「拿起試打」、每個關鍵字「看示範」、兩招與觸發關係、推薦配法、「確定出發」；試打用既有戰鬥畫面，左上離開鈕「回到靶場」；確定出發後守印人指示去霧渡鎮（共用彈窗）；中途離開回來停在靶場、選到一半的接著選（本機草稿） | vitest `client/src/world/range.test.ts`；瀏覽器實測三尺寸＋截圖 |
| 9 | 建角頁拿掉武器與關鍵字步驟，改一行說明 | `entryScreen.test.ts`；截圖 |
| 10 | 人物一律 Q 版 | 預覽用 `LookPreview`（Q 版，拿選的武器）；戰鬥畫面照既有 |
| 11 | 版號：`CHAR_FORMAT` → `trpg-char/12`、`WORLD_RULES_VERSION` → 22；openapi／`schema.d.ts` 重產；CLI 快照、`RULE_HASHES` 照慣例檢查 | 見第 3 節 |

## 1. 完成表

| 項目 | 做法 | commit |
|---|---|---|
| 內容 | `newcomer.yaml` 加 `range`（`RangeContent`／`RangeDummy` schema 在 `trpg.content.world_newcomer`，交叉檢查在 `content/library/world.py::_range_problems`）；新單位「會動的木樁」（數值同木樁、速度 3）；AI 行為 `drift`（只有 `keep_distance`、`hazard` 權重：有人走到 2 格內就退開、不攻擊、不踩有害表面）。地圖沿用技能工坊的 `training_range` | `ccc9e3a2` |
| 規則 | `trpg.world.opening`（新模組，純函式）：`opening_gate`、`apply_opening`／`apply_opening_confirm`、`pending_hero`、`range_trial`、`trial_seed`；`OpeningState`、`OpeningConfirmAction`、`OpeningConfirmedEvent`；`world_step` 開頭套 `opening_gate`。`roguelite.start` 只加公開包裝（`start_hero`、`pick_starters`、`check_race`、`check_origin`），既有行為不變 | `30e1a3f6` |
| API | `WorldStore.create` 的武器、關鍵字選填（都不給＝未完成開局；都給＝舊流程不變）；`WorldView.opening`（`RangeView`：種子、武器架與示範招卡、木樁、台詞）；`POST …/range/trial`（`trpg.api.world_range`）；事件句「帶著弓出發：起始技能 …」 | `bdd4aab3` |
| 前端 | `client/src/world/RangeScreen.tsx`（靶場畫面、確定出發後的守印人彈窗）、`range.ts`（武器架分組、看示範送的關鍵字、本機草稿）、`styles/range.css`；`WorldScreen` 接線（未完成開局畫靶場、試打「回到靶場」不回寫、確定出發）；建角頁拿掉武器與關鍵字 | `0f677314`、`5535afc2` |
| 修正 | 實測發現兩件事一起修：① 回到靶場時草稿要一進畫面就還原（原本等選項載入，玩家先點的關鍵字會被蓋掉）；② 從靶場確定出發進主城時 HUD 舞台沒重新量（`useHudStage` 的 dep 加上 `opening`），原本 HUD 縮在 1190×600 | `5535afc2` |

### 流程（玩家看到的）

1. 建角：名字 → 種族 → 外觀 → 出身 →「建立並在主城醒來」（下方一行說明武器與關鍵字在工坊靶場選）。
2. 主城醒來（RT-5 ① 插圖卡）→「站起來」→ 工坊靶場（守印人兩句、沙盒說明、木樁三個）。
3. 武器架點武器：預覽的 Q 版主角換拿那把武器；武器卡寫特性與「試打用：普攻＋示範招 A、B（選完收回、不進技能庫）」；「拿起試打」開戰鬥畫面（標題「靶場試打：弓：雷鳴箭、穿透射擊　沙盒：不算勝負、不給經驗與掉落、不耗 HP 與法力」，右上地名「主城・工坊靶場」），左上離開鈕「回到靶場」。
4. 關鍵字：每列右邊「看示範」（用選的武器、那招起始技能的沙盒）；選滿 2 個顯示觸發關係（例「燃燒爆擊製造點燃 → 趁燃雷擊利用點燃」）、兩張起始技能卡、推薦配法。
5. 「確定出發」→ 回到主城廣場，守印人彈窗「好，就這套。站上傳送陣，去雲嶺的霧渡鎮找渡婆婆——第一趟不收錢。」→「出發」；之後照 RT-5 ②～④（守印人泡泡、任務欄、免費傳送）。
6. 中途離開（「先離開（下次回到靶場）」、關掉、重新整理）：再進角色還是靶場，武器與關鍵字照上次選到的。

## 2. 版號與重產

| 項目 | 變動 |
|---|---|
| `CHAR_FORMAT` | `trpg-char/11` → `trpg-char/12`（`opening`；`/1`～`/11` 照讀＝已完成開局）。測試裡寫死 `/11` 的 17 處改成 `/12` |
| `WORLD_RULES_VERSION` | 21 → 22（新動作 `opening_confirm`；未完成開局的動作限制）。日誌格式 `trpg-wlog/9` 不變 |
| openapi | `client/openapi.json`、`client/src/api/schema.d.ts` 重產（`OpeningConfirmAction`、`RangeView`、`RangeTrialRequest/Response`、建角欄位選填） |
| `RULE_HASHES` | 不變（沒改任何實地地圖） |
| CLI 快照 | 不變（slow 快照照舊通過，不用重產） |
| 其他測試常數 | `tests/content/test_con_hp.py` 的 `OLD_HP` 加會動的木樁（300）；`tests/world/test_field_ctx_replay.py` 的 `DROPPED` 加 `opening`（凍結之後才加的欄位） |

## 3. 驗收結果

| 檢查 | 結果 |
|---|---|
| ruff check、ruff format --check、mypy（src＋tests）、lint-imports | 全過（14 contracts kept） |
| `pytest tests/world tests/api tests/content tests/server tests/engine -n 4` | 8948 passed、1 failed（`test_con_hp` 的舊 HP 表要加新單位）、1 skipped；補上之後相關檔重跑全過。新測試 `test_range_api.py` 9 個、`test_opening.py` 7 個 |
| CLI 測試 | `tests/cli` 143 passed；slow 輸出快照 `test_output_snapshots.py -m slow` 24 passed（快照不用重產） |
| 重播 `trpg battle --map swamp --seed 7` → `battle replay` | 通過：88 個動作、313 個事件，最終狀態一致 |
| 前端 typecheck、build | 過 |
| vitest 全量 | 273 檔、3295 個測試全過（含新的 `range.test.ts` 7 個；浮動卡規則掃描 `floatCardRule.test.ts` 過） |
| 排版煙霧 `runTown`（確定出發後的主城） | 1600×900、1040×624、800×600 全 PASS（修正 ② 之前 1600 有 2 項 FAIL） |
| 6.5.1 浮動卡實測（靶場的武器說明卡，`Hint`） | 1600×900、800×600：滑過顯示 → 滑進卡片不關 → 捲到底（卡片內容不超高，不用捲）→ 點一下釘住、滑鼠移開仍在 → Esc 關閉，兩尺寸都過 |
| 流程實測（無頭 Chrome、靜音） | 1600、800 兩尺寸都跑完：建角（不選武器）→ 醒來 → 靶場 → 拿起試打 → 回到靶場（武器還在）→ 選點燃 → 看示範帶電 → 回到靶場 → 選帶電（觸發關係出現）→ 重新整理再進角色（停在靶場、弓＋點燃＋帶電都在）→ 確定出發 → 守印人彈窗 → 主城 |

截圖（`docs/art/shots/tr1/`，jpg 80，10 張、單張 ≤ 210 KB）：

- 建角新流程：`docs/art/shots/tr1/tr1_1600_create.jpg`、`docs/art/shots/tr1/tr1_800_create.jpg`
- 靶場武器架：`docs/art/shots/tr1/tr1_1600_rack.jpg`
- 試打木樁：`docs/art/shots/tr1/tr1_1600_trial.jpg`
- 選關鍵字示範：`docs/art/shots/tr1/tr1_1600_demo.jpg`；選滿兩個（觸發關係）：`docs/art/shots/tr1/tr1_1600_picked.jpg`、`docs/art/shots/tr1/tr1_800_picked.jpg`
- 中途離開回來：`docs/art/shots/tr1/tr1_1600_resume.jpg`
- 確定出發：`docs/art/shots/tr1/tr1_1600_done.jpg`、`docs/art/shots/tr1/tr1_800_done.jpg`

## 4. 待 PM 決定

1. **舊流程保留**：`POST /api/world/characters` 兩個都給時照舊建角就選好（大量測試、模擬、開發工具用，結果和靶場確定出發逐欄相同，有測試鎖）。正式畫面不再送。要不要之後只留在開發模式？
2. **選到一半的草稿只存在本機**（localStorage）：換裝置回來會從頭選（伺服器只記「未完成開局」與種子）。21.5 只寫「停在靶場」，保守做法沒有把草稿寫進世界日誌。
3. **示範招 6 招是實作者暫定**（`newcomer.yaml` 的 `range.demos`）：近戰 橫掃劈砍＋放血斬；遠程 雷鳴箭（打水上的木樁會導電）＋穿透射擊；法器 火焰箭＋風刃。請玩法 PM 定。
4. **守印人在靶場的兩段台詞**（`range.intro`、`range.done`）是實作者暫定文案，待玩法 PM 定稿。
5. **木樁外觀**：沿用技能工坊木樁的範本，沒有 `doll`，戰鬥畫面照既有退回預設人形（紅頭巾），看起來像盜賊。要不要給美術 PM 排「木樁」外觀（戰鬥畫面的單位繪製是 HID-1 範圍的檔，這段沒動）。
6. **靶場畫面是入口畫面風格的全頁面板**（浮島背景、深藍金框），不是主城地圖上的一棟建築；試打用既有靶場戰鬥地圖 `training_range`。21.5 沒寫要不要做成主城室內圖，保守做法沒做新地圖。
7. **佔位武器用拳套**（未完成開局時主角範本要有武器）：醒來插圖、角色列表頭像會畫拳套；靶場預覽在選武器前也是拳套樣子。
8. **出發之後回靶場試自己的技能裝備**（21.5 最後一條）還沒開放：完成開局後 `…/range/trial` 一律 422。
9. **未完成開局能做的動作**：只開 `opening_confirm`、`news_seen` 與只記畫面紀錄的動作（提示、開場看過了）；改外觀、換種族也擋（主城本來能做）。要開放再說。
10. 「回到靶場」鈕是戰鬥畫面左上的既有離開圖示（滑過顯示「回到靶場」），沒有另外做文字鈕。
