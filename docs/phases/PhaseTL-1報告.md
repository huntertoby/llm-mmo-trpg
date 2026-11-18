# TL-1 報告：截圖比對腳本 `scripts/screenshot_diff.py`

分支 `worktree-agent-a5c0ee8fe576f7619`（base main `ca9d0fa08`）。只新增腳本、測試、本報告，並在 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第四節補第 195 點（用法一行）。沒動 `src/`、`content/`、`config/`、`docs/design/`、`client/`，沒碰 TL-2 的檔。

## 1. 做了什麼

- **`scripts/screenshot_diff.py`**：輸入舊、新兩個資料夾，依相對路徑（含子資料夾）配對 PNG，輸出：
  - 有變化（差異像素比例 > `--threshold`，由大到小）；
  - 細微變化（有差異但沒超過門檻，列出來但不影響結束碼）；
  - 尺寸不同、只在舊的、只在新的、無法讀取；
  - 略過的非 PNG 檔數（`.jpg`／`.jpeg`／`.gif`／`.webp`）。
- **相依**：`pyproject.toml` 沒有 Pillow、環境裡也沒有 numpy，所以**沒有新增相依**，PNG 用標準庫（`zlib`＋`struct`）自己解：支援全部非交錯 PNG（灰階 1/2/4/8/16、RGB 8/16、調色盤 1/2/4/8＋`tRNS`、灰階＋α、RGBA 8/16；五種濾波）；16 位元取高位元組；交錯 PNG 列「無法讀取」。差異圖用同一套自寫的編碼器輸出（RGB、濾波 0、zlib 6）。
- **像素差的定義**：兩張圖都轉成 8 位元 RGBA，單像素色差＝四通道差值的最大值（0～255），> `--pixel-tol` 才算這個像素有變。差異比例＝有變的像素 ÷ 總像素。整列位元組相同就跳過（快路徑）；兩個檔位元組完全相同時只讀檔頭、不解碼。
- **參數與預設**（保守＝最嚴，任何差異都抓）：

| 參數 | 預設 | 說明 |
|---|---|---|
| `--threshold` | `0`（0～1，不含 1） | 差異比例 **大於**這個值才算「有變化」；0＝有一個像素變就算 |
| `--pixel-tol` | `0`（0～255） | 單像素色差 **大於**這個值才算這個像素有變 |
| `--diff-out` | 不輸出 | 把「有變化」的圖畫成差異圖（新圖轉灰、調淡，變化處純紅），依相對路徑存 |
| `--format` | `text` | `text` 或 `markdown` |
| `--out` | 標準輸出 | 摘要寫到檔案 |

- **結束碼**：`0` 沒有超過門檻的變化（可以有細微變化）；`1` 有變化（超過門檻、只在一邊、尺寸不同任一）；`2` 輸入錯誤（資料夾不存在、兩邊都沒有 PNG、有 PNG 讀不了、參數不合法）。
- **速度**：1600×1708 的 RGBA 截圖解一張約 0.8 秒（純 Python）；189 張的 qicons 資料夾（大多相同、位元組比對直接跳過）全跑約 3 秒。

## 2. 用法範例（拿現有截圖實跑）

`docs/art/shots/qicons/` 在 `9aef7a248`（獨狼圖示樣張）與 `3cb3eb3e3`（獨狼修正）之間有 5 個檔變了（`git diff --stat`：2 張 jpg、3 張 png）。兩個版本用 `git archive` 匯出到暫存區再比：

```bash
git archive -o <暫存區>/old.tar 9aef7a248 docs/art/shots/qicons
git archive -o <暫存區>/new.tar 3cb3eb3e3 docs/art/shots/qicons
tar --force-local -xf <暫存區>/old.tar -C <暫存區>/old      # Windows 的 tar 要 --force-local，不然 C: 會被當成主機名
tar --force-local -xf <暫存區>/new.tar -C <暫存區>/new
uv run python scripts/screenshot_diff.py <暫存區>/old/docs/art/shots/qicons <暫存區>/new/docs/art/shots/qicons \
    --diff-out <暫存區>/diff --format markdown
```

結束碼 1，摘要（路徑縮寫）：

```
# 截圖比對
- 門檻：差異比例 > 0.000%；單像素色差 > 0
- 結果：有變化（配對比對 189 張）
- 略過非 PNG 檔：36 個

## 有變化（2）
- true1x/parts-chip18-12.png：0.098%（576／587520 像素）
- parts-b-condition-cost.png：0.015%（155／1018880 像素）

## 尺寸不同（1）
- true1x/parts-lw-t1.png：1280x500 → 1280x516
```

和 `git diff --stat` 的 3 張 PNG 完全對上（另外 186 張位元組相同，沒誤報）；兩張 jpg 被計入「略過」。差異圖 `true1x/parts-chip18-12.png` 看得到獨狼圖示的兩個紅色小塊（右上角的修正處），其他地方是淡灰底圖。

## 3. 怎麼接進現有流程

現有截圖的位置與命名（`docs/開發PM交接.md` 6.5.2、`docs/dev/上手-前端戰鬥畫面與動畫.md` 第 6 點）：

- 每段的截圖在 `docs/art/shots/<段名>/`（例 `FL-1b/`、`RG-5/`、`qicons/true1x/`），早期的在 `docs/phases/img/`；同一段的審查另開 `<段名>-review/`，**檔名和原段不同**（`fl1b_01_none_1600.jpg` vs `review-01-none-1600.jpg`），所以「原段 vs review」不能直接配對。
- 截圖約一半是 jpg（6.5.2 規定 jpg 品質 80）；腳本只比 PNG。

建議接法（都不用改現有腳本）：

1. **同一個資料夾、前後兩個 commit**（最常用）：`git archive <舊 rev> docs/art/shots/<段>` 匯出到暫存區，和目前工作目錄的同一資料夾比（第 2 節的做法）。適合「這次改動有沒有動到別段的截圖／圖示樣張」。
2. **用同一支截圖腳本重拍**：美術的 `docs/art/sample/tools/qicons_shots.py` 等會覆寫 `docs/art/shots/qicons/`；先把現有資料夾複製到暫存區（或用方法 1 匯出 HEAD），重拍後比，`--diff-out` 的紅點就是要在報告裡說明的變動。同一份畫法要用 `--disable-gpu`（上手筆記第 37、137 點），否則 GPU 雜訊會讓整張都「有變化」；真的要在 GPU 繪製下比，放寬 `--pixel-tol`（例 8）與 `--threshold`（例 0.001）。
3. **驗收／審查**：派截圖 agent 時要求「比對用的那幾張存 PNG、檔名固定」，PM 就能拿 `--format markdown --out` 的摘要直接貼進驗收報告；結束碼 0／1 也可以接在腳本裡當閘門。

## 4. 測試與檢查

測試 `tests/test_screenshot_diff.py`（放 tests 根目錄，和 `tests/test_sim_scripts.py` 等腳本測試同一層；用 `importlib` 載入腳本，和 `tests/api/test_deploy_script.py` 同做法）。所有 PNG 在測試裡用標準庫產生（最大 10×12 像素），不放圖檔。21 個測試：

- 解碼：RGBA 五種濾波各一＋混用；RGB、灰階、灰階＋α；調色盤 8/4/2/1 位元含透明；16 位元取高位元組；編碼器來回；非 PNG 與交錯 PNG 報錯。
- 比對：各類別（變化排序、只在一邊、尺寸不同、略過 jpg、同像素不同濾波不算變化）、`--pixel-tol` 與 `--threshold`、只有細微變化時結束碼 0、差異圖紅點位置、markdown 摘要、輸入錯誤（資料夾不存在、沒有 PNG、壞檔、門檻超範圍）結束碼 2、相同資料夾結束碼 0。

| 檢查 | 結束碼 |
|---|---|
| `uv run pytest -q tests/test_screenshot_diff.py` | 0（21 passed） |
| `uv run ruff check scripts/screenshot_diff.py tests/test_screenshot_diff.py` | 0 |
| `uv run ruff format --check`（同兩檔） | 0 |
| `uv run mypy`（全專案 src＋tests＋scripts，1672 檔） | 0 |
| `uv run lint-imports` | 0（14 kept） |

沒跑全量 `scripts/check.py`、沒跑模擬（依規格）。

`# noqa`：腳本檔頭有一行 `# ruff: noqa: PLR2004`——PNG 規格的色彩型態（0/2/3/4/6）、濾波型態（0～4）、位元深度（8/16）是規格固定數字，逐一取名反而難讀（`scripts/archive/` 有同樣用法）。沒有 C901／PLR0911／0912／0915 的例外。

## 5. 待 PM 決定

1. **JPEG 不比**：截圖約一半是 jpg（`docs/art/` 與 `docs/phases/` 共 1795 張 jpg、1650 張 png），沒有 Pillow 解不了 JPEG，目前只計數略過。選項：(a) 維持只比 PNG，規定要比對的截圖存 PNG；(b) 加 Pillow 到 dev 相依（我沒加，規格說非加不可才停）。另外 jpg 有壓縮雜訊，就算能解也要放寬 `--pixel-tol`。
2. **預設門檻**：照「保守」取最嚴 `--threshold 0 --pixel-tol 0`（有一個像素差就結束碼 1）。GPU 繪製的截圖會整張雜訊，屆時要不要換預設，請 PM 定。
3. **結束碼的歸類**：「只在一邊」與「尺寸不同」算有變化（1）；「有 PNG 讀不了」（含交錯 PNG）與「兩邊都沒有 PNG」算輸入錯誤（2）。細微變化（沒超過門檻）不影響結束碼、但會列出。
4. **測試位置**：專案沒有 `tests/scripts/`，照既有慣例放 `tests/test_screenshot_diff.py`（根目錄）。要另開 `tests/scripts/` 請告知。
5. **α 通道算進色差**：透明度變了也算像素有變；差異圖的底圖以白底合成透明處。沒做「只比 RGB」的選項。
