# Phase NW-1b 報告：數值工坊畫面（前端）

> 實作者：implementer agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhaseNW計畫.md` 第 0.0、3～6、7（NW-1b）、8、9、12 節，`docs/phases/PhaseNW-1a報告.md`，開發 PM 派工追加事項。
> 分支 `worktree-agent-aa07b574bdd8f6846`，從 main `61cdfe4d`（NW-1a 合併）ff 起；未 push。

## 1. 做了什麼（交付逐條）

| 交付 | 內容 | commit |
|---|---|---|
| PM 追加：`mana_restore` 進白名單 | `content/tuning_fields.yaml` 加 `phases[*].mana_restore`（階段回復法力，int，建議 1～60）。**開場階段排除**：白名單 yaml 沒辦法表達「跳過開場階段」，所以 `api/tuning/objects.py` 的 `concrete_fields` 加了一個小函式 `_phase_skipped`（`phases[*]` 一律不展開沒有 `trigger` 的開場階段；`trigger.*` 照舊只展開 `hp_below`）。測試：白名單含此欄（`test_tuning_fields.py`）、灰燼之心有 `phases[1].mana_restore`、沒有 `phases[0].mana_restore`（`test_routes.py`）、開場階段送改動 →「不開放」、填 0 →「不能小於 1」、填 6（插入新行）整包驗證通過（`test_check.py`）；hypothesis 的字面替換測試自動涵蓋新欄位。digest 不變：`test_whitelist_is_not_content_and_does_not_change_digests`（拿掉 `tuning_fields.yaml` 三個 digest 相同）照過，`trpg content check` 0 | `9821ed14` |
| B1 入口 | 開發選單（`?dev=1`，`StartScreen`）加「數值工坊」區塊 `tuning/TuningEntry.tsx`：先問 `/api/tuning/status`；200 →「進入數值工坊」；404 → 按鈕「數值工坊（未開啟）」停用，下面寫怎麼開（`TRPG_TUNING=1`，PowerShell 與 Git Bash 兩種寫法、`dev_mode` 也要開）；403 → 後端的 Tunnel 原因；連不到 → 原因。`App.tsx` 加 `tuning` 畫面，只在 `isDevMode` 時 render | `5301cab6` |
| B2 對象＋表單 | 左欄對象清單（搜尋中文名或 ID、分「頭目／一般敵人」、有改動的標「改 N」）；中欄表單**由 `/objects/{kind}/{id}` 的 `fields` 產生**：欄位中文名（滑過看 `note_zh`，共用 `<Hint>` 浮動卡）、‰ 欄位註明「1000＝100%」並附百分比、現值（沒寫時顯示 `default_zh`）、輸入框、建議範圍、「改過」標記與「還原這欄」；本機先擋非整數（中文原因），建議範圍外只黃字提醒；停止輸入 0.5 秒後送 `check`（`superseded` 丟掉），後端欄位錯誤紅字在該欄下、對不到欄位的（`page_errors`、別的對象的欄位錯誤）放頁首；`notes_zh`（遭遇護甲、等級成長）唯讀提示在表單頂 | `5301cab6` |
| B3 草稿＋差異 | 草稿列：目前草稿（下拉，含 `drafts` 清單）、存草稿（有未存時才可按）、丟掉草稿（頁內再問一次）、另開新草稿（名稱規則同後端）；換草稿前自動先存目前這份；改動清單（點對象名跳過去）。「看差異」先存再 `GET diff`：表（對象、欄位、現在、改成）＋可展開的檔案文字差異 | `5301cab6` |
| B4 模擬 | 頭目（選到頭目時自動切成它）、規模「小（每 build 3 種子＝24 場）」「中（10 種子＝80 場）」或自填種子數、build 勾選與全選；「N 場（改前、改後各 N 場），預估約 X～Y 秒」（改前有快取 X、沒有 Y）、超過 160 場或沒勾 build 中文擋下；開始前自動存草稿；每秒輪詢進度條（場數、已過、預估）、取消；結果表改前／改後／差值（勝率、平均輪數、倒下率、各階段到達場數與每招每回合施放率、各 build 勝率），每格附分子／分母、分母 < 30 標「樣本小」，勝負翻轉場數一句話；招式名稱用 `/api/skills/{id}` 補中文 | `5301cab6` |
| B5 寫回 | 「寫回遊戲…」：停用時寫原因（`status.reason_zh`／沒有改動／等驗證／草稿有錯／模擬跑中）；按下先存草稿＋拿差異 → 共用詢問視窗 `DialogFrame` 列改動與注意事項（自動 commit 一筆 `tune:`、要重開伺服器、進行中的一輪從頭開始、舊世界紀錄不能重播、有備份）→ 確定寫回；409 的中文原因顯示在視窗裡（檔案沒動）；成功顯示 commit、改到的檔、備份位置、重開伺服器提示，頁首常駐黃條 `restart_note_zh`；只能模擬時頁首寫原因 | `5301cab6`、`781f30b3` |
| B6 還原 | 「寫回紀錄與還原」列最近 20 筆 `tune` commit，「還原這次」→ `POST revert` → 反向改動放進目前草稿（提示「確認差異後按寫回才會真的改回去」） | `5301cab6` |
| B7 測試、排版、截圖、筆記 | `client/src/tuning/tuning.test.ts`（T-B1～T-B5，假 API，18 項）；`dev/layoutSmoke.ts` 加 `runTuning(標題)`；截圖 9 張；上手筆記兩份更新 | `781f30b3`、`77990b6a`、本報告 |

新檔：`client/src/screens/TuningScreen.tsx`、`client/src/tuning/{model.ts, flow.ts, FieldForm.tsx, SimPanel.tsx, DraftPanel.tsx, TuningEntry.tsx, tuning.test.ts}`、`client/src/styles/tuning.css`。改檔：`App.tsx`、`screens/StartScreen.tsx`（入口、副標題加「數值工坊」）、`api/client.ts`（`tuning*` 15 個呼叫）、`api/types.ts`（`Tuning*` 別名）、`styles/index.css`、`dev/layoutSmoke.ts`。沒動 OpenAPI／`schema.d.ts`（後端回應型別沒變）、沒動平行段的檔（`gearIcon.ts`、`qIcon/`、說明框、`appearance.py`、`content/units/`、`content/skills/`、`qBoss.ts`）。

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 1 | T-B1～T-B5 全過；改到的既有測試列舊→新 | 全過（見下表）；**沒有改既有測試**（`entryScreen.test.ts` 第 10 項鎖 `if (!isDevMode(window.location.search))` 字面，原本被我改寫的 App 寫法擋下，已改回保留原字面、測試未動） |
| 2 | 每次 commit：typecheck、相關 vitest；改 Python／yaml 加 ruff、mypy、相關 pytest | 每個 commit 前都跑，全 0 |
| 3 | 實機走一遍 | 通過（第 2.1 節） |
| 4 | `trpg content check`、一場紀錄＋重播 | `content check` 0；`battle --map open_plain --seed 7` 0、`replay` 0（91 個動作、383 個事件，最終狀態一致） |
| 5 | 實測秒數、Windows 寫回、沒驗證的 | 第 4、5 節 |

| 測試 | 檔案／項目 |
|---|---|
| T-B1 表單由欄位清單產生；改過＝差異 | `tuning.test.ts`「T-B1」6 項：放一個不在白名單的假欄位也照畫；改值→該列「改過」、改回原值／清空不算；改過的欄位＝改動單＝草稿列清單＝假 API 差異頁的列；草稿 ↔ 改動（含 `new: null`）來回不變；全形數字、非整數中文原因、範圍外只提醒；搜尋 |
| T-B2 驗證錯誤位置 | 「T-B2」2 項：欄位錯誤在該列（`aria-invalid`），其他列沒有；`page_errors`＋別的檔的欄位錯誤進頁首（標對象與欄位名） |
| T-B3 模擬結果表 | 「T-B3」4 項：格子文字與分子分母、差值（百分點）、階段只出現在一邊時 0/N 與 0/0「—」、三欄表頭、樣本小、翻轉句；估時與 160 場上限；輪詢（假計時：每秒一次、離開畫面停止、讀不到轉 `failed`） |
| T-B4 寫回 | 「T-B4」3 項：五種停用原因、按鈕 `disabled` 且顯示 `reason_zh`；確認視窗是共用 `DialogFrame`（`role=dialog`、`decision-card`）並列出改動與注意事項、409 原因；成功顯示 commit、訊息首行、檔案、重開伺服器 |
| T-B5 入口 | 「T-B5」3 項：原始碼掃描（`TuningScreen` 只在 `isDevMode` 分支、`onTuning` 只傳給 `StartScreen`、`HomeScreen` 沒有數值工坊）；探測 200／404／403／連不到；入口按鈕開著可按、未開啟停用並寫 `TRPG_TUNING=1` |

**交件前（結束碼分開記）**

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `corepack pnpm -C client typecheck` | 0 | |
| `corepack pnpm -C client test` | 0 | 302 個檔、3858 項 |
| `corepack pnpm -C client build` | 0 | |
| `uv run pytest -q tests/api/tuning tests/content/test_tuning_fields.py -n 8` | 0 | 107 passed |
| `uv run pytest -q tests/api/test_client_fixtures.py tests/api/test_openapi_snapshot.py` | 0 | 6 passed（快照沒動） |
| `ruff check .`／`ruff format --check .`／`mypy`／`lint-imports` | 0／0／0／0 | 14 kept, 0 broken |
| `trpg content check`、`battle`＋`replay` | 0、0、0 | |

沒跑：完整 `scripts/check.py`、`tests/cli/test_output_snapshots.py -m slow`（只動了白名單 yaml 與 `objects.py`，`content check` 輸出最後一行照舊）、大型模擬。

### 2.1 實機走過的流程（自己的 `trpg serve`，埠 8157；無頭 Chrome `--mute-audio`、網址 `?mute=1`）

寫回需要 `main` 分支，而 worktree 是 agent 分支，所以：在 worktree 內 `git clone --local --no-hardlinks <worktree> <worktree>/.scratch_nw1b/repo`、clone 裡 `checkout -b main`，伺服器設 `TRPG_CONTENT_DIR=<clone>/content`、`TRPG_SAVE_DIR=<worktree>/.scratch_nw1b/saves`、`TRPG_TUNING=1`。**寫回 commit 只落在這個 clone**（主資料夾與 worktree 分支都沒有 `tune:` commit；clone 在交件前刪掉）。

1. `/?dev=1&mute=1` → 開發選單「數值工坊」區塊「進入數值工坊」（`docs/art/shots/nw1/nw1_01_entry_1600.jpg`）。
2. 選灰燼之心，`max_hp` 填 0 → 欄位下紅字「不能小於 1」、頁首「有 1 個問題」、模擬與寫回停用（`docs/art/shots/nw1/nw1_02_invalid_1600.jpg`）。
3. 改 150 →「驗證通過（約 1～2 秒）」。
4. 模擬灰燼之心、8 build × 3 種子＝24 場（畫面「24 場（改前、改後各 24 場），預估約 10～19 秒」）→ 進度條與取消鈕（`nw1_03_sim_running_1600.jpg`）→ 結果表：勝率 19/24 → 20/24（+4.2 個百分點）、倒下率 28/72 → 26/72、翻轉 0／1，與 NW-1a 報告的冒煙數字一致（`nw1_04_sim_result_1600.jpg`）。
5. 看差異（灰燼之心 最大 HP 160 → 150）→ 寫回遊戲… → 確認視窗（`nw1_05_confirm_1600.jpg`）→ 確定寫回 → `ed7f3d83 tune(ashen_heart): max_hp 160→150`，頁首黃條「已寫回並 commit；重開伺服器後遊戲才用新數值（進行中的一輪會從頭開始）。」，表單現值變 150（`nw1_06_applied_1600.jpg`）。
6. 寫回紀錄「還原這次」→ 草稿出現 150 → 160、驗證通過 → 寫回 → `0beea85d tune(ashen_heart): max_hp 150→160`。**`units/ashen_heart.yaml` 的 md5 寫回前後相同**（`27371b22…`），clone `git diff 5301cab6 HEAD` 為空、`git status` 乾淨。
7. 800×600：改 140、驗證、模擬（改前命中快取）、結果表（`nw1_07_form_800.jpg`、`nw1_08_sim_result_800.jpg`），最後丟掉草稿。
8. 另開一個沒設 `TRPG_TUNING` 的伺服器（埠 8158）：入口顯示「數值工坊（未開啟）」與怎麼開（`nw1_09_entry_off_1600.jpg`）。

**`__layoutSmoke.runTuning` 三尺寸**：1600×900、1040×624、800×600 全 PASS（29 個欄位、文字不溢出、飾件不壓字、沒有左右捲軸、欄位說明卡有底色）。

**浮動卡實測（6.5.1；欄位名的 `<Hint>`）**：1600×900 與 800×600 都是「滑過出現（上方，240×52）→ 沿直線滑進卡片仍在 → 捲到底仍在（內容短、不需捲）→ 點卡片釘住 → 滑鼠移走仍在 → Esc 關閉」。寫回確認是點擊開的 `DialogFrame`（不是說明卡）。

## 3. 改寫的既有測試、搬家

- 既有測試：只在 `tests/api/tuning/test_check.py`、`test_routes.py`、`tests/content/test_tuning_fields.py` **加**斷言（mana_restore），沒有改或刪既有斷言。前端既有測試沒改。
- 沒有搬家；沒有重產快照或 OpenAPI。

## 4. 實測數字（Windows 11、16 邏輯核心、程序池 4）

| 項目 | 秒數 |
|---|---|
| 驗證一次（畫面顯示的後端秒數） | 0.85～1.93 |
| 灰燼之心 24 場（改前＋改後 48 場），程序池剛啟動 | 畫面估 19 秒；第 4 秒時 1/48（spawn 啟動），實際約二十多秒（這一輪的總秒數沒記到，見第 5 節） |
| 灰燼之心 24 場、改前命中快取（只跑改後 24 場，從按鈕到結果表出現，含輪詢） | 8.4 |
| 霧鎖真人 24 場、改前沒快取（48 場，程序池已保留；`elapsed_s`） | 23.2（畫面估 15.6，偏低約 1.5 倍：`seconds_per_battle` 是灰燼之心量的） |

## 5. 安全措施與 Windows 寫回

| 措施 | 怎麼驗 |
|---|---|
| 入口只在 `?dev=1` | vitest 原始碼掃描（T-B5）；`entryScreen.test.ts` 第 10 項照過 |
| 開關沒開 → 端點 404 → 入口「未開啟」 | 實機（埠 8158，沒設 `TRPG_TUNING`）＋vitest 假 API |
| Tunnel 標頭 403 → 入口顯示原因 | vitest 假 API（後端 403 由 NW-1a 測試鎖） |
| 寫回只在 `main`、前置檢查 | 實機在 clone 的 `main` 寫回成功；worktree 分支本身會被擋（NW-1a 測試） |
| 寫回後檔案逐位元組還原 | 實機：寫回 → 還原 → 寫回，md5 相同 |
| 行尾、權限（Windows） | 實機 clone 是 `core.autocrlf=true` 的 Windows checkout：寫回兩次後 `git status` 乾淨、md5 不變 |

**沒驗證的**：開發 PM 合併中（`MERGE_HEAD` 等）時寫回被擋的**畫面**（後端只在假 repo 測過；前端顯示 409 原因的路徑由 vitest 鎖）；碎晶之主的模擬（選單有、沒跑）；「中」規模 80 場；第一次（冷啟動）模擬的精確總秒數。

## 6. 請使用者試用的步驟

見第 8 節「給使用者的使用說明」。

## 7. 待 PM 決定

1. **`mana_restore` 的開場階段排除動到程式**：派工寫「只改 yaml 與對應測試」，但白名單 yaml 沒有「跳過開場階段」的寫法，所以在 `api/tuning/objects.py` 加了 `_phase_skipped`（所有 `phases[*]` 欄位都不展開開場階段）。若希望改成白名單欄位上的選項（例 `skip_opening: true`），要動 `TuningField` schema，請定。（派工追加第 1 點）
2. **寫回紀錄會列出早期手寫的 `tune(ai): …` commit**（例 `dcd94d4a`，BAL-5）：後端是 `git log --grep '^tune'`。按「還原這次」會照後端產反向改動單（只收白名單內欄位）。要不要只列工坊產生的（例 `tune(<對象>):` 開頭）請定。（NW-1a 第 1 節 `/history`）
3. **模擬跑中時停用「寫回」**（保守做法，避免寫回後改前結果跟著換）；規格沒寫，要放開請說。（規格 B5）
4. **規模「中」＝每 build 10 種子＝80 場**（提案寫「約 80 場」）；也可自填種子數，上限 160 場。（0.0 第 5 點）
5. **估時偏低**：`seconds_per_battle` 用灰燼之心量的（1.775），霧鎖真人實際約慢 1.5 倍；畫面寫「約 X～Y 秒」。要不要依頭目分開記，屬後端（NW-1a `sim_jobs.py`）。
6. **換草稿時自動先存目前這份**（不另問）；「丟掉草稿」才問一次。（規格 B3）
7. **「每回合施放率」可超過 100%**（例「火焰箭」158%，一回合放多次）：照後端分子分母原樣顯示，沒有改名；要改說法（例「每回合平均次數」）請定。（規格 5.4）
8. **截圖存 `docs/art/shots/nw1/`**（照派工與 6.5.2）；規格第 9 節第 3 點寫 `docs/phases/shots/nw1/`，以派工為準。
9. **錯誤字串**：後端欄位錯誤是「不能小於 1」這類（沒帶欄位名），畫面放在該欄下面所以看得懂；頁首的（別的對象）前面加「對象 ID「欄位名」：」。
10. **`.tn-label` 後面的「？」**在很長的欄位名（例「第 2 階段「呼吸」階段 HP 門檻」）會自己換到下一行，不影響使用；美術 PM 若要統一說明記號樣式再排。

**新增的複雜度 noqa**：無。

## 8. 給使用者的使用說明

**1. 開開關**（每次開伺服器都要設；沒設時開發選單會顯示「數值工坊（未開啟）」和怎麼開）

- PowerShell：`$env:TRPG_TUNING=1; uv run trpg serve`
- Git Bash：`TRPG_TUNING=1 uv run trpg serve`
- 只有你在自己電腦上直接開的瀏覽器能用；朋友從 Tunnel 連進來一律打不開。伺服器設定的開發模式（`dev_mode`）也要是開的（預設就是開的）。

**2. 從哪進**：瀏覽器開 `http://127.0.0.1:8000/?dev=1`（開發選單）→ 最下面「數值工坊」→「進入數值工坊」。

**3. 改一個頭目**：左邊選「灰燼之心」→ 中間每一欄是一個數值：欄位名（滑鼠移上去看說明）、現值、「改成」輸入框、建議範圍。在「最大 HP」的「改成」填 150。
- 填錯會在那一欄下面用紅字說原因（例如填 0 →「不能小於 1」）；超出建議範圍只是黃字提醒，不會擋。
- 改過的欄位會標「改過」，旁邊「還原這欄」可以單欄取消。
- 等上方出現「驗證通過」。

**4. 跑模擬看結果**：右邊「小模擬」：頭目會自動選成你正在改的頭目；規模先用「小」（24 場，約 10～20 秒）→「開始模擬」→ 等進度條跑完（可隨時「取消模擬」）。
- 結果表三欄：改前、改後、差值。看勝率、平均輪數、我方倒下率，以及頭目每個階段每招多常放。括號是「分子／分母」；標「樣本小」的數字容易跳，想確定再用「中」（80 場）跑一次。
- 最上面一句是「勝負翻轉」：同樣的種子，改前贏改後輸、改前輸改後贏各幾場。
- 模擬不會改遊戲，也不用重開伺服器。

**5. 存草稿、看差異**：右邊「草稿」可以「存草稿」、換一份草稿或「丟掉草稿」；「看差異」列出「哪個對象、哪一欄、從多少改成多少」。

**6. 寫回**：「寫回遊戲…」→ 跳出確認視窗，再看一次清單 →「確定寫回」。完成後會顯示一筆紀錄編號（commit）和黃色提示。
- **要重開伺服器**（關掉 `trpg serve` 再開，記得照第 1 步設開關）遊戲才會用新數值。
- 重開後，**進行中的 roguelite 一輪會從頭開始**，舊的世界紀錄不能重播（和平常改內容一樣）。
- 寫回時若顯示「開發 PM 正在合併，稍後再寫回」之類的原因，檔案不會動，等一下再按即可。
- 寫回後有些自動測試的「固定答案」會變紅，開發 PM 會派人只更新測試、不動你的數值，所以不會馬上 push。

**7. 還原**：右邊最下面「寫回紀錄與還原」→ 找到那一筆 →「還原這次」→ 反向的改動會放進草稿（例「最大 HP 150 → 160」）→ 看一下差異 →「寫回遊戲…」→「確定寫回」。一樣要重開伺服器才生效。
