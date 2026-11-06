# Phase 3-39 報告：一輪的「測試模式」

規格：`docs/phases/Phase3計畫.md` 第 43 節第 1～5 點（B、C 未做）。

## 做了什麼

1. **資料**：`RunState`（`src/trpg/roguelite/state.py`）加 `test_mode: bool = False` 與 `test_equipment: dict[str, str]`（欄位 → 物品 ID，預設空）。
   - 規格寫「裝備 ID 清單」，實作改成「欄位 → 物品 ID」：戒指有 `ring_1`／`ring_2` 兩格，沒有欄位就無法穿戴，也與 `Loadout`／`resolve_loadout` 的輸入格式一致。
2. **規則（只在 `test_mode`）**，`src/trpg/roguelite/progress.py`：
   - `finish_battle` 打贏後，HP、法力回滿到「戰鬥中的實際上限」（取一輪自己算的上限與戰鬥單位上限的較大者，所以裝備的最大 HP／法力加成也會補滿）；升級再依最大 HP 的差補上。營火、源力、升級等其他規則不變。歷程（`BattleRecord`）仍記錄打完當下的真實剩餘。
   - `run_loadout(library, run)`：有 `test_equipment` 時解析這份清單取代範本裝備，否則走原本的 `library.loadout_of(run.hero)`。`hero_spawn` 改用它。
   - 開局驗證（`start.py` 的 `check_test_equipment`）：未知欄位或物品、種類不符、占用、同一枚戒指、代價型條數、主手武器必須是起始武器，皆回中文 `ChoiceError`（「；」連接）。`new_keyword_run` 加 `test_mode`、`test_equipment`；沒開測試模式卻給裝備會被拒絕。
3. **介面**：開新一輪畫面（`RunNewScreen`）加「測試模式」勾選（`client/src/run/TestModePanel.tsx`）；勾了才載入裝備目錄並出現挑裝備區，重用 `SlotGrid`、`ItemList`、`HeroGearPanel` 與 `/api/gear/check`（伺服器裁決）。主手只列起始武器的武器物品；換武器自動拿掉不能挑的；可以不挑（只要回滿）；不合法時顯示原因並停用開始按鈕。純函式在 `client/src/run/testMode.ts`。
4. **API**：`POST /api/runs` 加 `test_mode`、`test_equipment`（只能搭配 weapon＋keywords 開局）；`RunResponse` 加兩欄、`SaveSummary` 加 `test_mode`。OpenAPI 與 `schema.d.ts` 已重產。
5. **CLI**：`trpg run new --test-mode --test-equipment slot=id,slot=id`；存檔摘要在測試模式多印一行標記（正式模式輸出不變，快照不需更新）。

## 存檔相容性

- 格式仍是 `trpg-run/5`，**不升號**：新欄位都有預設值，3-39 之前的 `trpg-run/5` 存檔照常讀取、視為正式模式（有測試）。
- 重播與讀檔一致：`test_equipment` 存在 `RunState`，讀檔後 `battle_setup` 用同一份裝備重建；`ruleset_hash` 不受影響。

## 標記與統計排除的位置

- 標記：進度畫面標題、一輪結束摘要（另有「不計入任何統計」一行）、首頁存檔列表（`TestModeBadge`，`client/src/ui/TestModeBadge.tsx`）；CLI `trpg run new`／`run show` 的標頭行；API `RunResponse.test_mode`、`SaveSummary.test_mode`。
- 統計排除：`trpg run auto` 與模擬（`trpg.sim`）都不經過測試模式參數，不會產生測試模式的一輪；專案內目前沒有讀存檔做勝率或歷程統計的程式（存檔只被 API 的存檔列表與 `trpg run show`／`--from` 讀取），所以無需另加排除。日後若有統計讀存檔，必須用 `run.test_mode` 排除。

## 檢查結果

- 新增測試：`tests/roguelite/test_test_mode.py`（戰後回滿、回到含裝備的上限、正式模式不回、亂數不變、裝備進戰鬥、取代範本裝備、整輪重播一致、5 種不合法裝備、無測試模式卻給裝備、存檔往返、舊存檔讀取）、`tests/api/test_run_test_mode_api.py`、`tests/cli/test_run_test_mode_cli.py`、`client/src/run/testMode.test.ts`。
- `ruff check`、`ruff format --check`、`mypy` 全過；`tests/roguelite`、`tests/api`、`tests/cli/test_run*`、`tests/test_architecture.py` 共 419 通過；vitest 833 通過、`typecheck`、`build` 通過（未跑 `scripts/check.py` 全量）。
- `trpg run auto --seed 7` 與改動前（`1b6400a`）輸出逐字相同。
- 實機（8011 埠、1600×900）：開新一輪勾選測試模式 → 挑主手長劍、鎖甲、生命戒 → 英雄面板顯示 HP 82（含裝備）→ 建立一輪；用頁面腳本經 API 打完第 1 場（種子 3，全滅）→ 歷程記錄 HP 60／法力 8，一輪狀態回到 85/85、20/20（升級 +3）；戰鬥畫面的主角裝備與選的相同、最大 HP 82；首頁存檔列表與進度畫面有「測試模式」徽章；未勾選時沒有挑裝備區，正式模式的一輪沒有任何測試欄位。視窗已還原、伺服器已關閉。

## noqa

無新增。

## 待 PM 決定

1. **輸了不回滿**：規格寫「勝負皆同」，但輸了一輪就結束（`EndedNode`），回滿沒有意義（會顯示陣亡的主角滿血），所以只在打贏時回滿。若測試模式要輸了也能繼續，那是新規則，需另決定。
2. **`test_equipment` 資料形狀**：改成欄位 → 物品 ID（理由見上）。
3. **一輪的最大 HP 顯示**：測試模式挑了加最大 HP 的裝備時，回滿到含裝備的上限，一輪畫面的最大 HP 顯示為 `max(一輪上限, 目前 HP)` 以免出現 85/63。正式模式的營火回滿仍只回到一輪自己算的上限（裝備本來就不在正式一輪裡，Phase 5 才有）；Phase 5 引入裝備時需統一「上限是否含裝備」。
4. **開局畫面多了一個勾選區**：正式模式開局畫面在「種子」上方多一個未勾選的「測試模式」區（沒勾就不載入裝備目錄、不影響送出的請求）。若要完全隱藏（例如只在 `?dev=1` 出現）請告知。
5. **範圍**：測試模式只支援「武器＋關鍵字」開局（不含開發者起始包與 `--build`），CLI 與 API 都會拒絕搭配；自訂（手動組裝）物品不支援，只能挑內容庫現有物品。
6. 啟動伺服器的人要重開伺服器才會有新功能。
