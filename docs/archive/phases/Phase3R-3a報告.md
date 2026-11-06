# Phase 3R-3a 報告｜開局選種族與出身

> 規格：`docs/phases/Phase3R計畫.md` 4.5「3R-3a」；設計：`docs/design/07-角色成長.md` 7.7。
> 範圍：開局順序「種族與出身 → 武器 → 2 關鍵字」的 API、前端、存檔、CLI。不含外觀（3R-3b／3c）。

## 1. 交付

| 項目 | 位置 |
|---|---|
| 出身欄位 `RunState.origin`（選填；種族沿用 3R-2 的 `hero.race`） | `src/trpg/roguelite/state.py` |
| `with_origin`（未知出身 → `ChoiceError`「未知的出身」） | `src/trpg/roguelite/start.py` |
| 存檔格式 `trpg-run/6` → `/7`；`/5`、`/6` 仍可讀（沒有 `origin`＝無出身、沒有 `hero.race`＝無種族） | `src/trpg/roguelite/save.py` |
| `POST /api/runs` 加 `origin`（未知 → 422）；`GET /api/runs/start-options` 加 `races`（種族技、被動、次數、代表界域）與 `origins`（界域、簡介） | `src/trpg/api/run_schemas.py`、`routes/runs.py`、`runs.py` |
| 一輪的英雄面板 `HeroOut` 加 `race_id`／`race_name_zh`／`origin_id`／`origin_name_zh` | `src/trpg/api/run_presenter.py` |
| CLI：`trpg run new|auto --origin`（`--race` 為 3R-2 已有） | `src/trpg/cli/run.py` |
| 前端：開新一輪畫面最上方「種族與出身」（種族卡 10 張、出身卡 5 張；浮動卡顯示種族技與被動、界域與簡介；選中的種族下方另列全文）；兩者都選才能開始；一輪面板多一行「種族・出身」 | `client/src/run/RaceOriginPicker.tsx`、`raceOrigin.ts`、`screens/RunNewScreen.tsx`、`run/RunHeroPanel.tsx`、`styles.css` |
| OpenAPI、`schema.d.ts` 已重產 | `client/openapi.json`、`client/src/api/schema.d.ts` |

主角戰鬥時帶種族：不需新程式，`hero.race` 本來就由 `battle_setup` 帶進戰鬥；以測試鎖住（見 2）。`LOG_FORMAT` 沒有動（戰鬥紀錄格式未變，仍 `/85`）。

## 2. 測試

- `tests/roguelite/test_origin_start.py`（3 項）：`with_origin`、不影響戰鬥設定（`battle_setup` 相同）、未知出身、`/5`、`/6` 舊存檔讀入。
- `tests/api/test_run_origin_api.py`（4 項）：開局選項列出 10 族與 5 個出身（文字齊全）、`race`＋`origin` 記入一輪與面板、戰鬥視圖的主角帶種族、未知出身 422。
- `tests/cli/test_origin_cli.py`（1 項）：`run new --origin` 存檔與未知出身。
- 既有測試的存檔格式字面值 `trpg-run/6` → `/7`。
- 前端 `client/src/run/raceOrigin.test.ts`（5 項）。

## 3. 驗收

| 條件 | 結果 |
|---|---|
| pytest（`-m "slow or not slow"` 的 tests/cli、tests/roguelite、tests/api，`--timeout=3000`） | 650 passed |
| vitest／build／tsc | 全部通過（113 檔 1085 項，含新增 5 項）；`corepack pnpm -C client build` 通過 |
| ruff、format、mypy | 通過 |
| 浮動卡 | 共用 `useFloatCard`／`FloatCard`（沒有自己實作；`floatCardRule` 測試通過）。瀏覽器實測：1600×900 滑過精靈卡 → 卡片顯示於按鈕上方 → 滑進卡片保持開啟 → Esc 關閉；800×600 滑過最右邊的海民卡，卡片完整在視窗內、頁面無橫向捲動。卡片內容短（約 120px），沒有捲動需求，所以「捲到底」＝卡片不出現捲軸；「釘住」見待 PM 決定 #2 |
| 內建瀏覽器走完整開局 | 選精靈＋雲嶺出身 → 弓 → 2 關鍵字 → 開局 → 一輪面板顯示「種族・出身 精靈・雲嶺出身」→ 開始第 1 場戰鬥 → 技能列出現種族技「林隱　1 AP・剩 2／2 次」（主角帶種族）。未選種族或出身時「開始這一輪」與「自動配點並開始」都灰掉 |
| 排版煙霧檢查（`__layoutSmoke`，先 `localStorage.clear()`） | 1600×900、800×600、1600×900＋`shortBottom` 三個情況全 PASS（用修好的 `startBattle`，見待 PM 決定 #6） |

## 4. 待 PM 決定

1. **種族與出身在 UI 是必選、在 API 與 CLI 是選填**：保守做法。前端開新一輪兩者都要選才能開始（沒選的後端選項不存在時除外）；API／CLI 省略＝無種族、無出身（舊測試與模擬照舊）。首頁「單場戰鬥」、技能工坊試玩、裝備測試**沒有**種族與出身這一步（它們不是一輪，種族不存檔）；需要時再加。
2. **種族／出身卡的浮動卡不做「點一下釘住」**：卡片本身是選取按鈕，與技能列的種族技按鈕相同用 `pinOn: "touch"`（觸控點一下開關，滑鼠點擊＝選取）。若要滑鼠也能釘住，要另外加一個「詳情」小按鈕。
3. **種族與出身互相獨立**：任何種族可配任何出身（7.7：代表界域只是預設，出身另選）；UI 不顯示「代表界域」以外的搭配建議。
4. **出身目前只記錄**：`run.origin` 還沒有被敘事層（開場劇情鍵）、NPC 態度或外觀使用；那些由後續段落與 3R-3b／3c 使用。
5. **存檔版本遞增為 `/7`**：只為了新欄位 `origin`；`/5`、`/6` 仍可讀。種族欄位在 3R-2 已隨 `hero.race` 存檔（當時沒遞增版本，欄位有預設值所以相容）。
6. **`layoutSmoke.startBattle` 已修（PM 補充要求）**：舊版固定點「第 1、2 個關鍵字」，目前內容下弓湊不到「點燃」的起始技能，該關鍵字被取消，只剩 1 個、開始鈕灰著，所以 `runCase` 全 FAIL。新版：①關鍵字改成「換武器後等預覽回來，一律挑目前可選、還沒選的第一個，直到選滿 2 個」；②已在戰鬥畫面就直接量測；③新選項 `runCase(title, {viaRun: true})` 走「開新一輪」：固定種族人類、出身第一個（晶冠城邦）、武器弓、自動配點並開始、按開始第 1 場（兩次點擊之間要等重繪，否則出身會用舊選擇蓋掉種族）。預設（不帶 `viaRun`）仍走首頁單場戰鬥。實測：首頁路徑 1600×900 一次通過；`viaRun` 路徑 1600×900、800×600、`shortBottom` 三個情況全 PASS（皆先 `localStorage.clear()`）。「載入後第一次全 FAIL」的舊現象在新版沒有再出現。
7. **內建瀏覽器與其他 agent 共用**：3R-3b 的 agent 同時用同一個瀏覽器窗格（8014 埠），我的分頁一度被它導走；我另開自己的分頁完成實測並關閉。

## 最終檢查

- 最後一個程式 commit 後：`ruff check`、`ruff format --check`、`mypy` 通過；vitest、`tsc --noEmit`、`pnpm build` 通過。
- 預覽伺服器 8013 埠已用自己的 PID 關閉；視窗已 `resize_window` 回 `desktop`。
- 未跑完整 `scripts/check.py`（依守則 11 由 PM 跑）。
