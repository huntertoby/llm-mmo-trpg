# Phase FL-1h 報告｜閃現與重閃的字與小修

> 出處：`docs/開發PM交接.md` 3.0000 第 4 點待排 (e3h)、(e3i)、(e3j)、(e3f)、(e3)。分支 `worktree-agent-add7504d8325e9178`（開工時快轉到 main 6f14e0767）。
> 範圍：skillgen 閃現／重閃篩選的註解與測試、client 閃現選變體面板（大世界與一輪共用）、重閃的「比原本弱」小標、PNL-4 小鈕的複核；開發頁夾具。沒碰引擎、content、戰場、紙娃娃、單挑與盾。

## 1. commit

| commit | 內容 |
|---|---|
| `2f2023ec5` | skillgen：`flash_offer` 整招篩選的註解寫明 06 6.34.5 (b)；新測試 `tests/roguelite/test_flash_transform_floor_fl1h.py` 鎖「重閃大變化格的轉型不套整招篩選」 |
| `d2811c3da` | 開發頁夾具加兩組伺服器真的出題的重閃（`reflash`、`reflash_major`）；`scripts/export_flash_choice_fixture.py` 跟著改 |
| `29ad5c03d` | client：轉型字、「和現在一樣」、「比原本弱」三角、條件括號不可拆詞；`run/fl1hFlashWords.test.ts` |
| `77373f8d1` | 截圖 `docs/art/shots/FL-1h/`（10 張） |
| （本報告與上手筆記） | `docs/phases/PhaseFL-1h報告.md`、`docs/dev/上手-前端戰鬥畫面與動畫.md` 第 162 點與測試表 |

## 2. 逐條驗收

| # | 項目 | 做法 | 證據 |
|---|---|---|---|
| 1a | (e3h) 轉型不套整招篩選 | 後端本來就是這樣（RR-2c 的 `_Builder.option` 有 `variation.source != "transform"`），玩法 PM 選 (b) 等於確認現狀，**規則沒改**。只把註解改成引用 06 6.34.5，並加測試鎖住：RR-2 重現案例（開發起始包 0、種子 2、營火）「灼燃・燃燒爆」重閃第 3 格，轉型保底的整招低於現在仍然出現，也沒有「比原本弱」小標；其他選項都不低於現在 | `test_flash_transform_floor_fl1h.py` 通過；截圖 04 |
| 1b | 有轉型選項的面板，上固定區那句 | `FLASH_MUST_PICK_TRANSFORM_ZH`＝「一定要選一個。選哪個這招整體都會強一點（轉型除外），標 ▼ 的是拿來換的」。`mustPickText` 判斷：較弱的重閃照舊用伺服器的 `weaker_foot_zh`；否則有轉型選項（`hasTransform`）就用這句；都沒有照原句。窄版收在 (i) 說明裡（同原句） | vitest「有轉型選項的面板…」「較弱的重閃照舊…」；截圖 04（寬版那句）、05（窄版在 (i)） |
| 1c | 轉型卡下固定區句末 | `sayText(o)`：轉型卡在 `say_zh`（沒有退回 `summary_zh`）後面接「轉型後照新種類重算強度，不跟原本比。」，前句沒有句號時補一個。原本一句話最多兩行，接上去會被截掉，所以轉型卡放寬到三行，有轉型選項的面板下固定區多留一行（點哪張都不跳）；一輪窄欄（容器 ≤ 420）要四行，另放寬 | vitest；量測見第 3 節；截圖 04、05、06 |
| 2 | (e3i) 「比原本弱」的 ▼ | `reflash-weaker.css` 不再把 `.fc-weaker .fc-down` 縮成 5／5／8，改用和前 → 後列同一個 CSS 三角（6.5／6.5／11）。實量：小標 ▼ 與列裡 ▼ 都是 12×11（1600、800）。重閃入口按鈕裡的 ▼ 照舊縮小（不在這次範圍）。小標字重照舊（美術說可維持粗體） | vitest（掃 CSS）；截圖 03（同一張卡上下兩種 ▼ 對照，×3） |
| 3 | (e3j) 「和現在一樣，選了這招不會變」 | `sameAsNow(pending, o, 現在的卡)`：重閃、前 → 後一列都沒有、沒有本機模型描述、名稱不變、**卡的內容和現在的卡相同**（不看 `id`、鍵排序後比）才放；放在原本 `DiffRows` 的位置（`.fc-same`：L3 `#a39d8c`、11.5px、左緣對齊前 → 後第一列的圖示，實量 1600 488＝488、800 166.08＝166.08）。找不到現在的卡就不寫。重現案例第 1 格（例外格）4 張裡 1 張；第 3 格（大變化格）4 張裡 1 張 | vitest「和現在一樣」3 條；截圖 01、02、04 |
| 4 | (e3f) 「雙手槍」不可拆 | `FLASH_NO_BREAK_WORDS = ["雙手槍"]`＋`noBreakRuns`；`TermText` 加 `nobr`，只在「後」的條件括號（`.fc-when`）開，詞包成 `.fc-nobr`（nowrap）。一輪窄欄 361 寬：「4 成武器傷害／（手持／雙手槍時才／有）」，不再斷成「雙手／槍」；800、1600 一行，沒變 | vitest；截圖 07 |
| 5 | (e3) PNL-4 可修 2 | **LW-2b 已經做了**（commit `887788b8a`：`world/solutionGrid.waiveRuns`、`.world-sol-glue`，測試 `world/lw2bWaiveGlue.test.ts`），這次沒改程式，只複核：開發頁 `story-gallery.html?mode=event`，格寬 145 與 137 都逐字量到「用〔商人欠你」／「人情〕抵」 | 截圖 08；`lw2bWaiveGlue.test.ts` 通過 |
| — | LW-2 待決 6 | 照派工不做（等美術） | — |

## 3. 下固定區量測（開發頁，五組夾具 × 四種寬，每張卡都點一次）

| 組 | 1600 大世界（720） | 800 大世界（514） | 800 一輪（753） | 408 一輪（361） |
|---|---|---|---|---|
| transform（有卸下選單） | 121，四張都一樣、轉型卡沒截 | 105，同 | 121，同 | 124；轉型卡 143（見下） |
| stance、llm、reflash_major | 95，四張一樣 | 76，四張一樣 | 95 | 95（轉型卡沒截） |
| base（沒有轉型，對照） | 74（原值） | 57（原值） | 74 | 57 |

- 轉型卡的一句話在每一種寬都完整顯示（沒有被行數截掉）。
- 408 一輪 transform 組選轉型卡時高 143、其他卡 124：多出來的是**卸下選單的三顆鈕在窄欄折成兩行**，改之前就會跳（改前窄版 `reserve` 只留 86；卸下選單兩行約 46＋一句話兩行 37.5＋間距與內距 22 ≈ 105，選轉型卡一樣會撐高），不是這次加的字。沒有轉型卸下選單的組不會跳。
- 一般卡在窄欄被兩行截掉（`CLIP`）是原本的設計（最多兩行、完整看卡上的前 → 後），沒改。

## 4. 版號、快照、不變比對

- **引擎結算沒改**：`LOG_FORMAT`、`WORLD_RULES_VERSION`、`CHAR_FORMAT` 都不升。後端只改註解；出題結果沒變（轉型本來就不篩）。
- **CLI 快照**：預測 0 鍵會變（沒改技能說明、敘事字、CLI 輸出；前端字不進 CLI）。照預測沒有重產，也沒跑 slow 的 `tests/cli`。
- **OpenAPI**：沒加欄位，沒重產。
- **重播**：`trpg battle --map bandit_lair --seed 7 --log-json …` → `trpg battle replay`：通過（73 個動作、254 個事件）。
- **開發頁夾具**：舊的五組只多了 `weaker_tag_zh: null`（RR-2c 加的欄位，夾具之前沒重產），其他逐欄位相同；新加 `reflash`、`reflash_major` 兩組與對應的 `bases`。

## 5. 檢查（結束碼）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check`（改到的 3 個 py 檔） | 0 |
| `uv run ruff format --check`（同上） | 0 |
| `uv run mypy`（同上） | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run pytest -q tests/roguelite/test_flash_transform_floor_fl1h.py tests/roguelite/test_reflash_weaker_rr2.py -n 4` | 0（6 passed） |
| `tsc --noEmit` | 0 |
| `vitest run src/run/ src/screens/ src/dev/ src/ui/ src/world/pnl4Followups.test.ts src/world/lw2bWaiveGlue.test.ts src/world/pnl4EventTiles.test.ts` | 0（76 檔、914 passed） |
| `trpg battle replay`（種子 7） | 0 |

沒跑完整 `scripts/check.py`、CLI 快照與 build（照派工）。

## 6. 瀏覽器實測

- vite 自己開在 5391（`--strictPort --host 127.0.0.1`），無頭 Chrome 除錯埠 9391（`--remote-debugging-address=127.0.0.1`、`--mute-audio`、`--disable-gpu`、DPR 1），網址都帶 `?mute=1`；開之前 netstat 確認兩個埠沒人用。
- **浮動卡流程**（開發頁 `reflash_major`，選中轉型卡後滑到術語「AP」）：1600×900 與 800×600 都是：滑過 80ms 還沒開、約 500ms 開一張、在視窗內、portal 到 `body` → 經橋接區滑進卡仍在 → 卡內捲到底（這張卡 79／79，不用捲）→ 點一下釘住（`pinned`），滑走仍在 → Esc 關掉（0 張）。截圖 09、10。

## 7. 截圖（`docs/art/shots/FL-1h/`，10 張、jpg 80、最大 79 KB、DPR 1；全部是開發頁 `client/dev/flash-choice.html`／`story-gallery.html`）

| 檔案 | 內容 |
|---|---|
| `fl1h-01-reflash-same-1600.jpg` | `set=reflash` 大世界 1600：上固定區伺服器的較弱句；3 張「▼ 比原本弱」；選中那張整招等於現在、卡裡「和現在一樣，選了這招不會變」 |
| `fl1h-02-reflash-same-800.jpg` | 同上 800（窄版） |
| `fl1h-03-weaker-tag-triangle-800-x3.jpg` | 800 第一張卡 ×3：卡頭「▼ 比原本弱」與列裡「▼ 1d6」同一個三角 |
| `fl1h-04-reflash-major-transform-1600.jpg` | `set=reflash_major` 1600：上固定區「（轉型除外）」；選中轉型卡，下固定區句末「轉型後照新種類重算強度，不跟原本比。」（兩行） |
| `fl1h-05-transform-800.jpg` | `set=transform` 800：轉型卡＋卸下選單，一句話三行完整 |
| `fl1h-06-transform-run-408.jpg` | `set=transform&mode=run` 408（一輪窄欄 361）：一句話四行完整 |
| `fl1h-07-nobr-run-408-x2.jpg` | `set=rows&mode=run` 408 ×2：「（手持／雙手槍時才／有）」，「雙手槍」不斷 |
| `fl1h-08-waive-145-x3.jpg` | `story-gallery.html?mode=event`，格寬 145：「用〔商人欠你／人情〕抵」（137 量字同，沒另拍） |
| `fl1h-09-float-pinned-1600.jpg` | 浮動卡流程釘住的樣子 1600 |
| `fl1h-10-float-pinned-800.jpg` | 同上 800 |

**實機未看**：全部項目。重閃的例外格與大變化格要一輪打到營火並有足夠靈感點，開發頁的 `reflash`／`reflash_major` 是伺服器同一套函式真的出題（`open_flash` → `pending_flash_out`），畫面元件與實機相同；大世界的「轉型除外」與轉型卡句末用 `transform`／`stance`／`llm` 三組（新的閃現第 3 次）。

## 8. 待 PM 決定

1. **「和現在一樣」的判定比卡、不只看前 → 後列**：`flash_changes` 不會列出所有欄位，前 → 後一列都沒有不保證卡一樣。所以前端另外比「卡的內容和現在的卡相同」才放這行；找不到現在的卡就不放。兩個實例（重現案例第 1、3 格）卡都逐欄位相同。若要改成伺服器給一個欄位（例如 `same_zh`），要動 API 與 OpenAPI，這次沒做。
2. **只在重閃放**：照玩法 PM 4.1.2 第 4 條的字面（「重閃選項」）。新的閃現若出現前 → 後一列都沒有的卡，照舊是空的（美術說新的閃現不會遇到，這次也沒看到）。
3. **有本機模型描述的卡不放**：卡裡已經有一行字（`fc-note`），不再加。
4. **轉型卡一句話放寬到三行（一輪窄欄四行），有轉型選項的面板下固定區多留一行**：不放寬的話，句末接的那句在 800 與一輪會被兩行截掉。代價是有轉型的面板下固定區高 19～21px（窄欄 38px），沒有轉型的面板不變。
5. **不可拆詞目前只有「雙手槍」**：照 (e3f)。其他可能被拆的詞（「雙匕首」「雙手劍」等）沒有實例，沒加；要加就往 `FLASH_NO_BREAK_WORDS` 加。一輪窄欄這句從三行變四行（「…雙手槍時才／有）」），換來不拆詞。
6. **重閃入口按鈕裡的 ▼ 照舊縮小**：美術 RR-2 可修 1 只點名卡上的小標；入口是另一個元件，沒動。
7. **營火說明行「新選項整招不會比現在弱；標 ▼ 的是換掉後變小的地方。」沒加「轉型除外」**：06 6.34.5 只指定選變體面板的兩句，營火說明行是前端字、不在指定範圍，照保守不改；大變化格的轉型保底在重閃時仍可能整招比現在弱（重現案例第 3 格）。要不要一起改請玩法 PM 定。
8. **PNL-4 可修 2 已在 LW-2b 做完**：這次只複核、補一張截圖，交接 (e3) 那條可刪。

## 9. 平衡疑慮

- 重現案例重閃第 3 格（大變化格）有一個選項「專精點燃：造成的點燃更持久」，出來的卡和現在一模一樣（前 → 後一列都沒有、卡逐欄位相同）：加深的效果可能被預算重調吃掉了，選了等於沒變。第 1 格那張「多等幾回合再用」一樣，是因為被換掉的那一筆本來就是蓄力（換成自己）。這類「選了不會變」的選項佔一個名額，請記進平衡待查，看要不要在出題時排除。
