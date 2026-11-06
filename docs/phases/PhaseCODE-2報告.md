# CODE-2 完成報告：測試固件收斂（整理提案 I2）

## 做了什麼

- 根 `tests/conftest.py` 新增 session 級固件：`content_library`（正式內容，直接回傳 `default_library()`，行程內只載入一次）、`library`、`field_library`、`calm`、`ambush`。
  - `calm`、`ambush`、`field_library` 都依賴 `content_library`，**不依賴 `library`**：`tests/api`、`tests/world` 會把 `library` 覆寫成沒有實地地圖的版本，session 級固件如果依賴 `library`，第一次在哪個目錄算出來就會被全部測試共用，結果會跟著執行順序變。
  - `tests/api/conftest.py`、`tests/world/conftest.py` 的 `library` 改成 `without_fields(content_library)`，不再自己載入。
  - `tests/engine/helpers.py` 的 `library()` 改成回傳 `default_library()`，跟固件共用同一份物件（之前每個 worker 會多載入一次，每次約 2.4 秒）。
- `tests/api/conftest.py` 新增 function 級工廠 `make_client(library, *, clock=None, **create_app 參數)`：存檔預設放在 `tmp_path / "saves"`，有傳 `clock` 就換掉大世界的時鐘，測試結束時關閉 client。`client`、`prompt_client` 都改用這個工廠。
- 盤點過有沒有測試修改 library 物件：用 grep 查了「`library.` 後面接賦值」、`object.__setattr__`，以及在 library 欄位上呼叫 `.append`／`.update`／`.pop` 等寫法。唯一命中的 `object.__setattr__` 在 `test_state_clone.py`，改的是戰鬥狀態，跟 library 無關。`ContentLibrary` 是 frozen dataclass，所以 module 級固件改成 session 級。

## 數字

| 項目 | 數量 |
|---|---|
| 刪除的 `library` 固件 | 62 份檔內固件（其中 46 份是 `load_library()`、16 份是 `default_library()`）＋ `tests/bot/conftest.py` 整檔 ＋ 2 份改名的同類固件（`test_battlefield` 的 `content_library`、`test_world_field_buildings` 的 `real_library`） |
| 改寫但保留的 `library` 固件 | 6 份：api、world 的 conftest（拿掉實地地圖）；`test_run_origin_api`、`test_world_story`（改成回傳 `content_library`）；`test_season_reset`（改聯賽設定，改成依賴上層的 `library`）；`test_flash_note_archaic` 的 `lib`（改成依賴 `library`） |
| 刪除的 `field_library` | 2 份（api、world 的 conftest） |
| 刪除的 `calm`／`ambush` | 8 份／7 份（各含 world conftest 1 份） |
| `client` 固件 | 刪 6 份（直接用 conftest 的 `client`），9 份改用 `make_client`，conftest 的 `client`、`prompt_client` 改成工廠 |
| 直接呼叫 `load_library()` | 47 處中改了 46 處：37 處改成固件參數，9 處在模組層級或 helper 裡，改呼叫 `default_library()`（共用快取，結構不變）；保留 1 處，見下表 |
| tests 行數 | 150,437 → 149,947（−490）；`git diff --stat` 共 123 檔，+298／−788 |

### 執行秒數（`pytest -q tests/<目錄> -x -n 4`）

本機同時在跑 LLM 和另一個 agent，秒數只能看趨勢。

| 目錄 | 改前 | 改後 |
|---|---|---|
| `tests/content` | 186.5 秒 | 72.3 秒 |
| `tests/api` | 205.2 秒 | 166.3 秒 |
| `tests/skillgen` | 477.7 秒 | 187.6 秒 |

其餘改到的目錄（world、cli、engine、llm、narrative、roguelite、server、sim、bot、`test_primitive_coverage.py`）合併跑一次：6,701 個全部通過。`ruff check`、`ruff format --check`、`mypy tests`、`lint-imports` 都通過。

## 保留沒收斂的地方與原因

| 檔案 | 原因 |
|---|---|
| `src/trpg/skillgen/random_composer.py` 的 `default_library` | **沒有搬**。正式碼 `src/trpg/skillgen/whiteboard.py:579` 在用，`scripts/` 也有 4 支在用（另有 5 支已歸檔）。測試這邊改成透過根固件 `content_library` 使用它。 |
| `tests/content/test_world_events.py::test_loading_twice_is_identical` | 這個測試本身就是驗證重新載入，`load_library()` 要留著。 |
| 8 份依賴檔內 `_client` 的 `client`：`test_world_economy_api`、`test_world_party_api`、`test_world_shadow_api`、`test_title_display`、`test_world_mail_api`、`test_world_crafting_api`、`test_world_events_api`、`test_world_loot_api` | 各檔的 `_client` 行為不一樣，例如預先寫入 `world.json` 的賽季種子、用 `FixedClock`、傳 `AccountSettings`／`ServerSettings`，有些測試還會用同一個存檔資料夾重開。這些 `_client` 也被測試直接呼叫，所以保留原寫法。 |
| `test_world_api` 的 `calm_client`／`ambush_client`、`test_world_growth_api` 的 `calm_client`、`test_world_dev_boss_6f3` 的 `dev` | 同上，依賴檔內的 `_client`。 |
| world 的 `calm(field_library)` 系列（`test_capital`、`test_newcomer_6f2`、`test_field_things`、`test_world_store_r3`）、`test_world_economy_api` 的 `ambush` | 內容不同：有實地地圖、會清掉生怪，或改了戰鬥金幣，不是重複的固件。 |
| `tests/bot/test_discord_adapter.py` 的 `client` | 是 Discord 的 `StubClient`，不是 `TestClient`。 |
| 參數化或 `content` 帶入暫存資料夾的 `load_library(root)` 約 60 處 | 載入的是改過的複本，本來就要各自載入。 |
| `tests/roguelite/helpers.py` 的 `full_library()`、各檔的 `@cache` helper | 給模組層級的參數化用。底層已經共用 `default_library()`，不另外改結構。 |

## 待 PM 決定

1. **`make_client` 放在 `tests/api/conftest.py`，沒放根目錄**：用到 `TestClient` 固件的只有 `tests/api`。放在根目錄的話，每個 worker 都要匯入 FastAPI 和 `trpg.api`。要搬到根目錄也只是移動一段程式。
2. **行為變更**：`tests/api/conftest.py` 原本的 `client`、`prompt_client` 和 `test_battle_start_api` 的 `client` 都沒有傳 `save_dir`，`create_app` 會用 `default_save_dir()`，等於測試在寫正式的存檔資料夾。現在統一改成 `tmp_path`，測試照樣通過。
3. **行為變更**：`tests/engine/helpers.library()` 從固定讀專案的 `content/` 改成 `default_library()`。它會讀 `TRPG_CONTENT_DIR`，但只在第一次呼叫時讀，之後就快取。目前沒有測試在整個行程設定這個環境變數，只有 monkeypatch，而且都在單一測試裡。
4. **流程事故**：我先用 `git rm` 把 `tests/bot/conftest.py` 的刪除加進暫存區，結果被另一個 agent 的 commit `ae55ee59`（CODE-3 I3）一起帶走了，內容正確（刪掉的 session `library` 由根固件取代）。我沒改寫歷史。之後的 commit 都在 commit 前一刻才 `git add`。
