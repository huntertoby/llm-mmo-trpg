# Phase NW-1a 報告：數值工坊後端

> 實作者：implementer agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhaseNW計畫.md`（定稿 `ffe6fb87`）第 0.0、0、1～6、7（NW-1a）、8、9、11、12 節。
> 分支 `worktree-agent-ad3c2ce69326255f6`，從 main `ffe6fb87` 起（未 push、未合併 main 之後的 commit）。

## 1. 做了什麼（交付逐條）

| 交付 | 內容 | commit |
|---|---|---|
| A8（搬家） | `library_violations` 從 `trpg.cli.budget` 搬到 `trpg.skillgen.library_check`（連同 `BUDGET_RANGE_RULES`），`cli.budget` re-export；`tests/test_architecture.py` 的 `LIBRARY_SKILLS_ITERATION_ALLOWED` 加一筆（理由：內容檢查要走訪全部內建技能，含敵人專用） | `599bbc9a` |
| A7（搬家） | 頭目量測核心 `scripts/cb2e_sim.py` → `src/trpg/sim/boss_probe.py`（`ProbeJob`、`character`、`BossWatch`、`probe_battle`、`boss_tally`、`boss_jobs`、`phase_skills`、`library_for`、`probe_task`、`run_boss_probe`）；腳本 `bosses`／`report` 改成呼叫它，`conceal`／`compare` 用搬過去的 `ProbeJob`／`character`。`BossWatch` 另記我方開場人數與倒下過的（不進腳本的 JSON） | `a46908bf` |
| A1 | `content/tuning_fields.yaml`（單位 26 個欄位：`max_hp`、`level`、六屬性、`speed`、`armor_bonus`、`max_mana`、`stamina`、4 組 `resist`、9 個 `element_mods`、`phases[*].trigger.permille`；中文標籤、型別、建議範圍、說明）＋`src/trpg/content/tuning_fields.py`（schema、路徑工具、載入檢查：每個路徑對得到 `UnitTemplate`／`BossPhase` 的整數欄位、禁止表、不開 ID／`*_zh`／外觀／引用欄位、路徑不重複）。對象＝`units/*.yaml`，排除 `units/summons/`、`sim_*`、`hero_*`、`gear_tester*`、`training_dummy*` | `6e97b150` |
| A3 | `api/tuning/yaml_patch.py`：字面替換、插入（區塊式／流式／空 `{}`／整個上層沒寫）、刪除（反向改動單把「沒寫」改回去）；每筆改完重新 parse 驗證；錨點、加引號的值、刪除帶註解的行、唯一一項一律擋並說明 | `d0d35b8e` |
| A2、A4、A5 | `drafts.py`（改動單、草稿存讀列刪、`normalize`／`merge`／`reverse`）、`workspace.py`（樹雜湊基底複本＋硬連結草稿複本，留 8 份草稿、4 份基底）、`check.py`（轉型 → 白名單＋`old` 比對＋字面替換 → `UnitTemplate` 單檔 → 草稿複本整包檢查；pydantic 錯誤轉中文並依 `loc` 對到欄位）、`objects.py`（對象清單與表單資料，含「遭遇護甲調整」唯讀提示）、`diff.py`（差異表＋`git diff` 風格文字）、`schemas.py` | `9995fd6c` |
| A6 | `git_guard.py`（參數陣列呼叫 git、commit 訊息走 stdin）、`writeback.py`（前置檢查、備份、寫檔、對真的 `content/` 再驗、只 commit 那幾個檔、失敗還原；`reverse_of_commit` 產生反向改動單） | `97780cc2` |
| A7（工作） | `sim_jobs.py`：背景執行緒＋保留的 spawn 程序池（`min(4, 核心數−2)`）、一次一個（409）、取消、改前快取、上限 160 場、同種子配對翻轉、估時（上次實測每場秒數） | `543d9d9d` |
| A8 | `service.py`、`routes.py`（`/api/tuning/*`、三道門）、`app.py`（`create_app(tuning=None)`；`dev_mode` 且開關開才建服務、掛路由，掛在最後）；OpenAPI 匯出與快照測試改用 `create_app(tuning=True)`；`client/openapi.json`、`client/src/api/schema.d.ts` 重產 | `330ea385` |
| A9 | 測試（第 2 節）、真的程序池測試（slow）、上手筆記（`上手-內容資料與模擬.md` 加第七節與表格列、`上手-roguelite開局與入門期.md` 加一列） | `062989ab`、本報告 |

**給 NW-1b 的介面**（前綴 `/api/tuning`；型別在 `client/src/api/schema.d.ts` 的 `Tuning*`）：

| 端點 | 回應 | 說明 |
|---|---|---|
| `GET /status` | `TuningStatus` | `can_write`／`reason_zh`、`restart_needed`／`restart_note_zh`、`drafts`、`sim_running` |
| `GET /objects?kind=unit` | `TuningObjectSummary[]` | `category`：`boss`／`enemy` |
| `GET /objects/{kind}/{object_id}` | `TuningObjectDetail` | `fields[]`：`path`（具體路徑，改動單用）、`pattern`、`label_zh`、`kind`（`int`／`permille`）、`value`（`null`＝沒寫）、`default_zh`、`hint_min`／`hint_max`、`note_zh`；`notes_zh` 唯讀提示 |
| `GET｜PUT｜DELETE /drafts/{name}` | `TuningDraftView` | PUT body `TuningDraftIn{changes: [{file, path, old, new}]}`；`new` 可傳文字（轉不了整數 422）；預設草稿名 `current` |
| `POST /drafts/{name}/check` | `TuningCheckResult` | body 可省略（驗已存的草稿）或給 `TuningDraftIn`（不必先存）；`field_errors[{file, path, message_zh}]`、`page_errors[]`、`superseded`、`seconds` |
| `GET /drafts/{name}/diff` | `TuningDiff` | `rows[]`（對象中文名、欄位中文名、舊、新）、`text`（只含改到的行）、`errors` |
| `POST /drafts/{name}/apply` | `TuningApplyResult` | 409＋`detail` 中文原因時檔案不變；成功後草稿清掉 |
| `POST /drafts/{name}/revert/{commit}` | `TuningDraftView` | 反向改動單併進草稿（不直接寫回） |
| `GET /history?limit=20` | `TuningHistoryEntry[]` | `git log --grep '^tune'` |
| `GET /sims/options` | `TuningSimOptions` | 頭目（mist／ashen／rift）、8 個 build、`default_seeds`=3、`max_battles`=160、`workers`、`seconds_per_battle`（預估秒數＝場數 × 它 ÷ workers；改前沒快取時場數 ×2） |
| `POST /sims` | `TuningSimJob` | body `TuningSimRequest{draft, boss, builds?, seeds}`；409 已有模擬在跑、422 參數或草稿有錯 |
| `GET｜DELETE /sims/{job_id}` | `TuningSimJob` | `state`、`done`／`total`、`estimate_s`、`elapsed_s`、`result`（`before`／`after` 的 `TuningSimSide`：`n`、`wins`、`rounds`（總和）、`allies`／`downed`（總和）、`small`、`phases[].skills[{skill, casts, turns, small}]`、`builds[]`；`flips{won_to_lost, lost_to_won}`；`before_cached`） |

錯誤一律 `{"detail": "<中文>"}`；帶 `CF-Connecting-IP`／`X-Forwarded-For`／`Forwarded` 任一個 → 403「數值工坊只能在本機瀏覽器直接開」。vite 的 `/api` 代理（`client/vite.config.ts`）沒開 `xfwd`，不會加轉發標頭。

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 1 | 第 8 節 T-A1～T-A10 全過 | 見下表（測試檔對照） |
| 2 | 每次 commit 前 `ruff check`、`ruff format --check`、`mypy`、`lint-imports`、相關測試 | 每個 commit 前都跑過，全 0（`lint-imports`：14 kept, 0 broken） |
| 3 | 實機走一遍 | 屬 NW-1b（有畫面才走）；本段以 TestClient 走完整條（`test_routes.py::test_apply_and_revert_through_the_api`：改 max_hp 160→150 → 寫回（暫存 repo）→ 還原 → 再寫回 → 檔案逐位元組相同）與量測腳本（第 4 節） |
| 4 | `trpg content check` 通過、一場紀錄＋重播通過 | 通過：`trpg content check` 結束碼 0，輸出和 `ffe6fb87` 逐字相同；`trpg battle --map open_plain --seed 7` 0、`battle replay` 0（91 個動作、383 個事件，最終狀態一致） |
| 5 | 報告寫明實測數字與沒驗證的 | 第 4、5 節 |

| 測試 | 檔案 |
|---|---|
| T-A1 白名單 | `tests/content/test_tuning_fields.py`（含拿掉 `tuning_fields.yaml` 後三個 digest 不變） |
| T-A2 字面替換 | `tests/api/tuning/test_yaml_patch.py`（hypothesis 300 例：開放的 59 個單位檔 × 每個白名單欄位，`difflib` 只動一行、註解一行不少；流式／區塊式／空 `{}`／沒寫插入／CRLF／BOM／刪除還原／擋下的寫法） |
| T-A3 digest | `tests/api/tuning/test_check.py::test_untouched_copy_has_the_same_digests`（複本不套改動三個 digest 相同；改 `max_hp` 後 `content_digest`、`ruleset_hash` 變、`hash_ruleset` 不變——單位範本不在規則包裡） |
| T-A4 非法值 | `test_check.py::test_illegal_values_are_refused_with_field_reasons`（`max_hp: 0`→「不能小於 1」、`speed: -1`、`attributes.str: "abc"`→「要填整數」、`phases[1].trigger.permille: 1500`→「不能大於 999」、`level: 0`、`old` 對不上、不開放的欄位、範圍外的檔）；階段門檻順序錯放頁首；整包檢查的 `ContentError` 對到欄位 |
| T-A5 寫回 | `tests/api/tuning/test_writeback.py`（假 repo：成功只含那個檔、別的暫存不帶進去、訊息格式；`MERGE_HEAD`／`index.lock`／`CHERRY_PICK_HEAD`／`rebase-merge`、不在 main、檔案有未 commit 改動、`old` 對不上、非法值 → 不寫、檔案不變；commit 失敗 → 檔案與暫存還原；對真的 content 再驗失敗 → 還原） |
| T-A6 還原 | `test_writeback.py::test_apply_then_revert_is_byte_identical`（含「原本沒寫」的欄位：插入後再刪除，逐位元組回到原樣） |
| T-A7 三道門 | `tests/api/tuning/test_routes.py`（`dev_mode=False` 404 且 OpenAPI 沒有；沒設／設 0 的 `TRPG_TUNING` 404、設 1 才 200；3 種轉發標頭（含空值）× 5 個端點 → 403） |
| T-A8 boss_probe | `tests/sim/test_boss_probe.py`（同參數兩次相同、鍵同腳本、本行程彙總＝逐場相加）；腳本逐字相同見第 3 節 |
| T-A9 模擬工作 | `tests/api/tuning/test_sim_jobs.py`（假的每場函式：一次一個 409、取消、改前快取命中只跑改後、換內容重跑、上限 160、壞參數、失敗狀態、彙總確定性）＋`test_sim_real.py`（slow，真的 spawn 程序池：兩次結果相同） |
| T-A10 搬家 | `trpg content check` 輸出搬家前後逐字相同（第 3 節）；`lint-imports`、`tests/test_architecture.py` 過 |

**交件前的測試（結束碼分開記）**

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `pytest -q tests/api -n 8` | 0 | 1049 passed, 1 skipped（203 秒） |
| `pytest -q tests/sim -n 8` | 0 | 155 passed |
| `pytest -q tests/content -n 8` | 0 | 2967 passed |
| `pytest -q tests/skillgen -m "not llm" -n 8`（含 slow） | 0 | 4908 passed, 14 skipped |
| `pytest -q tests/cli/test_output_snapshots.py -m slow` | 0 | 24 passed |
| `pytest -q tests/api/tuning/test_sim_real.py tests/test_architecture.py -m "slow or not slow"` | 0 | 14 passed |
| `corepack pnpm -C client typecheck` | 0 | |
| `ruff check .`／`ruff format --check .`／`mypy`／`lint-imports` | 0／0／0／0 | 1482 個原始檔；14 kept, 0 broken |

沒跑：完整 `scripts/check.py`、大型模擬（依派工規定）。

## 3. 改寫的既有測試、搬家與「輸出逐字相同」的證據

改到的既有測試：

- `tests/test_architecture.py`：`LIBRARY_SKILLS_ITERATION_ALLOWED` 加 `("trpg.skillgen.library_check", "library_violations")`（舊：在 `trpg.cli`，不在玩家技能池套件內所以不用登記 → 新：搬進 `skillgen` 後要登記，理由同上）。斷言不變。
- `tests/api/test_openapi_snapshot.py`：`saved == create_app().openapi()` → `saved == create_app(tuning=True).openapi()`（快照要含數值工坊端點給前端型別用；`scripts/export_openapi.py` 同步改）。

搬家的證據：

- **`trpg content check`**：搬家前（`ffe6fb87`）與每個 commit 後的完整輸出 `cmp` 相同（含 `tuning_fields.yaml` 加入後：「共 660 個檔案」不變）。
- **`scripts/cb2e_sim.py bosses --only mist --seeds 1 --out <檔>`**（8 場，`JOBS=8`）搬家前後 SHA-256：
  - JSON `34a0b12ba733de0b8bc5713fb4ef26a53d5ee2e416a92b807e15b68d506f1603`（前後相同）
  - stdout（報表）`2a8bdddbfa217532e083211907577384323184747e482df5e26d83a592ed3d49`（前後相同）
  - stderr「頭目戰 8 場」`dfa750b7ab71bb414d51382567827f44ff4c595569674305e49d9ae7c629d1a1`（前後相同）
  - `report <JSON>` 的輸出也和 `bosses` 的 stdout 相同（同一個雜湊）
  - 交件前再跑一次：三個雜湊與上面完全相同
- **OpenAPI**：`create_app(tuning=False)` 輸出與原 `client/openapi.json` 逐字相同；`tuning=True` 時路徑順序不變、只多 `/api/tuning/*` 與 25 個 `Tuning*` schema（JSON 比對：沒有刪除或改動的鍵）；`git diff --diff-algorithm=histogram --stat`：`openapi.json` 1633 行、`schema.d.ts` 1039 行，全是新增（預設演算法因為 JSON 縮排重複會顯示成大量刪除＋新增，實際沒有刪）。
- **內容 digest**：`content/tuning_fields.yaml` 不在 `KNOWN_CONTENT_FILES`、不在 `library.files`；把它從內容複本刪掉後 `ruleset_hash`、`content_digest`、`hash_ruleset` 三個都和原資料夾相同（`test_tuning_fields.py::test_whitelist_is_not_content_and_does_not_change_digests`）。`tests/content/test_yaml_parser.py`（掃全部 YAML）、`tests/llm/test_simplified.py` 照樣過，不需要登記例外。
- **快照**：沒有重產任何 CLI 快照或前端夾具；`tests/cli/test_output_snapshots.py -m slow` 照舊過（第 2 節）。

## 4. 實測數字（Windows 11、16 邏輯核心，scratchpad 量測腳本）

| 項目 | 秒數 |
|---|---|
| `load_library` | 0.64（暖機後） |
| 內容基底複本（664 個檔，第一次） | 0.52 |
| 驗證一次（含草稿複本＋整包 `load_checked_library`＋`library_violations`） | 第一次 2.15、之後 1.22 |
| 小模擬：灰燼之心 8 build × 3 種子＝24 場，改前＋改後 48 場，程序池 4（第一次，含 spawn 啟動） | 26.1 |
| 同上，改前命中快取（只跑改後 24 場，程序池已保留） | 9.4 |
| 同上，清掉改前快取再跑（程序池已保留） | 21.3 |
| 每場秒數（`seconds_per_battle`，用來估時） | 1.775 |
| 寫回測試（假 repo，含兩次整包檢查） | 每個約 3～6 秒 |

同參數同內容：第 1 次與第 3 次的結果（不含 `before_cached`）JSON 逐字相同。改 `max_hp` 160→150 的 24 場：改前 19 勝、改後 20 勝、翻轉 0／1（輸變贏 1 場）、倒下 28/72 → 26/72（這只是冒煙，不是平衡結論）。

## 5. 安全措施對照（第 5.3 節、第 0 節第 2 點）

| 措施 | 怎麼測 |
|---|---|
| ① `dev_mode` 才掛 | TestClient（`AccountSettings(dev_mode=False)`）：404、OpenAPI 沒有、`app.state` 沒有服務 |
| ② `TRPG_TUNING=1` | TestClient＋`monkeypatch` 環境變數：沒設／`0` → 404，`1` → 200 |
| ③ 轉發標頭 403 | TestClient：3 種標頭（含空值）× 5 個端點 |
| 分支是 `main` | 假 repo `checkout -b feature` |
| `MERGE_HEAD`／`REBASE_HEAD`／`rebase-merge`／`rebase-apply`／`CHERRY_PICK_HEAD`／`REVERT_HEAD`／`index.lock` | 假 repo 放標記檔（測了 4 種；`index.lock` 也查共用 git 目錄，worktree 適用） |
| 要改的檔有未 commit 改動 | 假 repo 改檔不 commit |
| `TRPG_CONTENT_DIR` 不在 repo 裡 → 只能模擬 | `Git.find(tmp)` 為 `None` 時的原因字串（單元測試） |
| `old` 對不上 | 假 repo；另在寫檔前再比對一次全文（驗證後被別人改過也擋） |
| 備份（留 50 份） | 假 repo：備份檔＝改前位元組 |
| 寫後對真的 `content/` 再驗、不過就還原 | 假 repo＋注入失敗的檢查函式 |
| 只 commit 那幾個檔 | 假 repo：先暫存別的檔，commit 後它仍在暫存區、commit 只含那個檔 |
| commit 失敗還原（含暫存） | 假 repo＋`monkeypatch` 讓 `git commit` 失敗 |
| 行尾、權限（Windows） | 假 repo 在 Windows 上：LF 檔寫回後仍是 LF、沒有 CRLF；CRLF／BOM 檔由字面替換單元測試保證；`write_bytes` 覆寫原檔，不改權限 |

**沒驗證的**：

- 主資料夾的真實寫回（規定不能做）；開發 PM 合併進行中被擋只在假 repo 放標記檔測過。
- 使用者的 git 有 hook、簽章時的行為（假 repo 關掉 hook 與簽章）；hook 失敗會走「commit 失敗 → 還原」。
- `trpg serve` 實機（NW-1b 有畫面時一起走）；伺服器關閉時程序池用 `shutdown(wait=False, cancel_futures=True)`，跑到一半的那幾場會跑完才結束。
- 碎晶之主（rift）的小模擬只在選項裡列出，沒有實跑（量測只跑灰燼之心）。

## 6. 請使用者試用的步驟

NW-1a 沒有畫面；NW-1b 合併後：設 `TRPG_TUNING=1` 開伺服器 → `?dev=1` → 數值工坊。PM 可先用 API 文件試：`TRPG_TUNING=1 TRPG_SAVE_DIR=<暫存> uv run trpg serve --port 8157` → `http://127.0.0.1:8157/docs` 的 `tuning` 區（**在 worktree 或假 repo 試寫回，不要在主資料夾**）。

## 7. 待 PM 決定

1. **`phases[i].mana_restore` 還沒進白名單**：派工時的 main（`ffe6fb87`）還沒有這個欄位；BAL-21a 之後已合併進 main（`BossPhase.mana_restore: int | None`，`ge=1`）。合併本段時在 `content/tuning_fields.yaml` 加一行 `{path: "phases[*].mana_restore", label_zh: 階段回復法力, kind: int, hint_min: 1, hint_max: 60, note_zh: …}` 即可（不改程式；T-A1 會檢查它對得到 schema）。注意：`concrete_fields` 目前只展開有 `hp_below` 門檻的階段給 `phases[*].trigger.*`，`mana_restore` 會對每個階段展開（含開場階段，但開場階段 schema 規定不能有改動 → 驗證會擋並放頁首）；要不要只開非開場階段請定。（規格第 3 節 NW-1 列）
2. **合併時 `client/openapi.json` 會衝突**（main 之後另加了 22 行）：照既有流程重跑 `uv run python scripts/export_openapi.py` 與 `corepack pnpm -C client gen:api` 即可（本段的部分全是新增）。
3. **改前快取的鍵用「`content/` 樹雜湊」而不是 `content_digest`**（規格 5.4 寫 `content_digest`）：樹雜湊不必先載入內容庫、連註解改了也算不同（較保守，只會多重跑不會誤用）。要改回 `content_digest` 請說。
4. **不開的單位**：`units/summons/`、`sim_*`、`hero_*`、`gear_tester*`、`training_dummy*`（規格「召喚物、模擬用 build 的單位不開」的解讀）；`std_enemy_t1～t5`、`variant_*` 有開。名單在 `content/tuning_fields.yaml` 的 `exclude`，要調只改那裡。
5. **建議範圍**（`hint_min`／`hint_max`，只提示不擋）是我依現有資料抓的原型數值（例 `max_hp` 1～999、屬性 1～30、抗性 −500～750‰）；請玩法 PM 或使用者看要不要調。
6. **頭目情境只有 mist／ashen／rift 三個**（`trpg.sim.boss_probe.BOSSES`，沿用腳本的地點與等級）；規格說「自動列出有 `phases` 的單位所在遭遇」，但源晶柱也有 `phases`、頭目的地點／等級要另外推，先保守用固定表。之後加頭目要在 `BOSSES` 加一列。
7. **寫回成功後自動刪掉該草稿**（避免同一張單再寫一次因 `old` 不符失敗）；若希望保留請說。
8. **`/api/tuning` 不要求登入**：照規格只靠三道門（`dev_mode` 開時本來就不用登入）；`dev_mode=false` 時根本不掛。
9. 上手筆記：選擇「併入 `上手-內容資料與模擬.md` 加第七節」（規格 A9 說由 PM 定）；要獨立成 `上手-數值工坊.md` 時直接搬那一節。
10. 開發 PM 交接的合併規則（規格 5.3 末段 ①～④，`git log <分支起點>..main --grep '^tune'`、使用者的值優先）**沒有寫進 `docs/開發PM交接.md`**（本段不改 PM 文件），請開發 PM 決定是否採用並自己寫入。

**新增的複雜度 noqa**：無（`C901`／`PLR0911`／`PLR0912`／`PLR0915` 都沒有加）。
