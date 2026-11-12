# Phase DOC-A 報告：文件瘦身第一批（docs/phases 歸檔＋截圖搬家）

> 依 `docs/phases/整理提案-程式.md` 第 1 節執行 D1、D2、A1、A2、A3、M7、K1、S1 與路徑 sed（使用者原話「瘦身都照建議」）。2026-11-06。一律 `git mv`、檔名不改；只動 `docs/phases/**`、`docs/archive/phases/**`、`docs/art/` 圖片、`src`／`tests`／`scripts`／`client/src` 的註解路徑字串。

## 1. 做了什麼

| 項 | 內容 | 數字 | commit |
|---|---|---|---|
| D1、D2 | 先確認 `scripts/flash_minor_coverage.py --help` 可跑；`git rm docs/phases/BAL-*/*.md` | 刪 114 檔（含 minor_coverage ×7）；csv／json／json.gz／log／txt 108 檔全留 | `ccbb03ea` |
| — | 新增 `docs/archive/phases/README.md`：說明＋「BAL 目錄 → 重產腳本」表（17 列） | | `ccbb03ea` |
| A1～A3 | 已結案報告 `git mv` 到 `docs/archive/phases/` | 搬 484 檔（Phase0～5 系列 288、`BAL-*報告` 48、Phase6 已結案系列 128、PhaseC 5、閃現／複合技轉型 2、Phase3 審查 4、`Phase3-41說明整修清單`、`工坊盤點-2026-10-24`…） | 搬動被併入 `fdf59891`（見第 4 節）；路徑修正在 `21d25fe6` |
| M7 | `docs/phases/戰鬥紀錄格式變更.md` 只留策略＋最近 10 版（`/112`～`/103`，70 行）；`/102`～`/1` 共 114 段搬到 `docs/archive/phases/戰鬥紀錄格式變更-舊版.md`，檔頭加一句指向舊版 | 52 KB → 5 KB | 同上 |
| 路徑 sed | ① 被搬報告裡的相對 `img/…` → `docs/phases/img/…`：39 處／11 檔（實際是反引號引用，不是 `](img/` 連結，一併改）② `docs/phases/<報告>` → `docs/archive/phases/<報告>` 與 `docs/art/<md>` → `docs/archive/art/<md>`：446 處／297 檔（其中程式 132 處／122 檔）；第二趟補 CSS 13 處／7 檔 ③ `Phase3計畫.md` 的 `docs/design/12-技術與結構.md` → `04-架構技術與LLM.md`（1 處；`10-LLM與安全`、`草稿-裝備範例` 在 `docs/phases/**` 內 0 處） | | `21d25fe6`、`48ee545c` |
| K1 | 29 份已結案 `*計畫.md` 第 2 行插入結案標記（`Phase4`／`Phase6`／`PhaseBAL計畫` 不加） | 29 檔 | `3065f90d` |
| S1 | `docs/art/` 根目錄截圖 → `docs/art/shots/<前綴>/`，分 4 批 commit（300／300／300／174） | 搬 1074 張（盤點時 1544，執行時根目錄只剩 1074；`closeup/`、`sample/` 不動）；88 個前綴 → 張數 ≥ 3 的 37 個各自成目錄，張數 ≤ 2 的 51 個前綴共 57 張併進 `shots/misc/` | `272a71a2`、`76208f30`、`15ab04ac`、`d741525b` |
| S1 路徑 | 程式／`docs/phases`／`docs/archive/phases` 裡指向根目錄截圖的路徑改成 `docs/art/shots/…` | 49 處／32 檔（client 17、docs/phases 20、archive 12）＋ CSS 7 處 | `48ee545c` |

`shots/` 目錄（張數）：rt3 74、6f14 64、rt5b 57、6t1c 50、6f19 48、ue1 46、6t1b 46、rt3b 45、ue1b 41、6f18 39、6f8 37、6f12 36、6f17 33、6f13 33、rt5c 32、6f11 32、rt5 30、uie3 28、6f15 26、6f7 24、rt1 23、6f6 23、6f10b 22、6f9 18、6f16 18、uie4 16、6f10 16、rt5d 14、6r1 10、6v2b 7、6v4b 6、gear 5、region 4、au2 4、anim 4、skill 3、idle 3、misc 57。

## 2. 驗收

- `uv run ruff check src tests scripts`：All checks passed（sed 後 9 行 docstring 超 100 字，已改寫換行：`src/trpg/content/battle.py` ×2、`fields.py` ×2、`tests/content/test_ashen_waste_content.py`、`test_field_look_6v2b.py`、`tests/known_budget_exceptions.py`、`tests/skillgen/test_flash_bal12c.py`、`tests/world/test_capital_figures_6v1.py`）。
- `uv run ruff format --check src tests scripts`：1380 files already formatted。
- `uv run pytest -q tests/test_architecture.py -x`：13 passed。
- `uv run pytest -q tests/api/test_openapi_snapshot.py`：2 passed（見第 4 節第 2 點）。
- `pnpm -C client typecheck`：通過（改了 client/src 的註解與 CSS）。
- 最後 grep `docs/phases/Phase[0-5]|PhaseBAL-|Phase6[ABCDEHLMPQSV]-|PhaseRT-5` 在 `src tests scripts client/src docs/phases docs/archive/phases`：只剩 `*計畫.md`、`Phase4-LLM技能提議設計.md`、`Phase5C-3e代決.md`（三者都沒搬，正確）。

## 3. 留著沒搬、拿不準

| 檔 | 原因 |
|---|---|
| `docs/phases/UI-T1報告.md` | 指示寫「`UI報告.md`（不帶段號）」但實際只有帶段號的 `UI-T1報告.md`，不確定是否同一份 → 留 |
| `docs/phases/Phase6F-ART1報告.md`、`Phase6F-ART1b報告.md` | 不在 `6F-1～18` 數字範圍、也不屬 6F-19 → 留 |
| `docs/phases/4-L9/`、`docs/phases/first10_logs/`、`docs/phases/img/` | 照規則不動 |
| `docs/phases/整理提案-程式.md` | 指示的「`docs/整理提案-*.md` 不改」實際位置在 `docs/phases/`，sed 一律跳過它（裡面的舊路徑是提案當時的描述） |

另：`PhaseBAL-*報告.md` 實際檔名是 `BAL-*報告.md`（48 檔），照「BAL 報告已結案」的意思全搬；`BAL-1重跑_三種AI.md` 留。

## 4. 保守做法與必須說明的事

1. **搬動被併入別人的 commit**：`git mv` 484 檔＋M7 兩檔已暫存後、做 sed 與 ruff 修正的期間，專案 PM 在同一個工作樹 commit 了 `fdf59891 docs(pm): record model/effort instruction`，把我暫存的 484 個改名一起帶進去（該 commit 486 檔）。不 rebase、不改歷史，路徑修正另成 `21d25fe6`，commit 訊息有註明。之後所有批次都改成「`git add` 自己的路徑＋commit 在同一個指令內」，沒再發生。
2. **`client/openapi.json`、`client/src/api/schema.d.ts` 重產**：`src/trpg/content/fields.py` 的 `FieldFigure` docstring 進了 OpenAPI 描述，路徑改掉＋換行後 `tests/api/test_openapi_snapshot.py` 必失敗，所以跑 `scripts/export_openapi.py` 與 `pnpm -C client gen:api` 重產（只差 2 處描述文字）。`client/openapi.json` 嚴格說不在授權清單內，但不重產會留一個紅測試。
3. 腳本 docstring 裡的用法範例 `--out docs/phases/BAL-N/xxx.md`（含 `bal9c_pierce.py` 的 `BAL-9c/pierce.md`）**不改**：那是重產指令，不是引用。
4. 指向根目錄截圖但檔案早已不存在的路徑（`docs/art/story.png`、`6n3_*.jpg`、`rt4_*.jpg`、`au3_*.jpg` 等）：119 個檔名／135 處（docs/archive/phases 31 檔、docs/phases 11 檔、client/src/dev 1 檔），這批是搬家前就懸空的（git 裡任何位置都沒有該檔），**沒改**。`docs/art/review-*.png` 在我的範圍內 0 處（只出現在 `docs/archive/art/3-16a檢查.md`，不是我的檔）。
5. `docs/art/*.md`、`docs/archive/art/*.md` 裡的截圖引用**沒改**：裸檔名 281 處／79 檔；帶 `docs/art/` 全路徑 14 處／7 檔。搬家後要靠檔名 grep（`git ls-files 'docs/art/shots/**/<name>'`）。

## 5. 其他 PM 檔案裡仍指向舊路徑的統計（沒改，給各 PM）

計入：已搬報告的 `docs/phases/<name>`、已歸檔檢查檔的 `docs/art/<name>.md`、已搬截圖的 `docs/art/<name>.(png|jpg|gif)`。

| 檔 | 行數 | 處數 |
|---|---|---|
| `docs/開發PM交接.md` | 3 | 3 |
| `docs/design/05-戰鬥.md` | 3 | 3 |
| `docs/design/06-技能.md` | 2 | 3 |
| `docs/design/08-裝備.md` | 2 | 2 |
| `docs/design/09-世界與敘事.md` | 1 | 1 |
| `docs/玩法決定紀錄.md` | 2 | 2 |
| `docs/玩法PM交接.md` | 1 | 1 |
| `docs/專案計畫.md` | 1 | 1 |
| `docs/art/組裝式裝備.md`、`docs/art/美術風格比較.md` | 各 4 | 各 4 |
| `docs/art/6V-2b檢查.md`、`6V-3與6V-4檢查.md`、`6V-4b檢查.md`、`Q版修正清單-第17版.md`、`地圖標記.md`、`移植需求.md` | 各 1 | 各 1 |
| `docs/archive/art/*.md`（33 檔：`3-18倒地與高度` 2 行 3 處、`裝備外觀移植需求` 2 行、其餘 31 檔各 1 行） | 35 | 36 |
| `docs/archive/玩法PM交接_2026-11-05.md`、`docs/archive/玩法決定紀錄_1-138.md` | 4、2 | 4、2 |
| `README.md`、`CLAUDE.md`、`docs/美術PM交接.md`、`docs/專案PM交接.md` | 0 | 0 |

合計 50 檔、69 行、71 處。
