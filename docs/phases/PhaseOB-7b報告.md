# Phase OB-7b 報告：新手渡口改 1 隻（2 打 1）

> 實作者：OB-7b 實作 agent（Opus 5.5）。
> 依據：#155 2026-11-12 修訂（玩法 PM commit 81e7cb12；使用者原話「剛開始 2打1 後面才加人」）、18 18.7.1。

## 1. 改動與 commit

| commit | 內容 |
|---|---|
| 6a004e43 | `src/trpg/content/world_encounters.py`：`MIN_GROUP_SIZE` 2 → 1（說明寫明只給渡口）；`content/world/encounters/cloud_ridge.yaml` 的 `bandit_raiders`＝`[bandit_rookie]`；新增內容測試鎖住 |
| f5059ae5 | 上手筆記：`docs/dev/上手-內容資料與模擬.md` 第 20 條補例外、`docs/dev/上手-roguelite開局與入門期.md` 第 20 條補「第 1 步 2 打 1」 |
| 5024f0a7 | 調參台測試換對象（見第 2 節） |
| （本報告） | 報告 |

- 新測試 `tests/content/test_world_encounters.py::test_only_ferry_lineup_is_single`：所有區域的陣容裡，少於 2 名的只有 `("cloud_ridge", "bandit_raiders")`，且它是 `("bandit_rookie",)`、沒有第三方。之後要加 1 隻的陣容要先改這項（筆記有寫）。
- 沒有改任何單位數值、地圖、規則版號。陣容只是 `content/`，世界日誌的規則鍵因內容 digest 改變自動標成不能重播（同 OB-7）。
- `bandit_archer_rookie`（新手弓手）不再出現在任何遭遇，但單位檔、掉落表（`content/world/loot.yaml`）、AI 設定照留（見待決 2）。

## 2. 改到的測試（舊 → 新）

| 測試 | 為什麼變 | 改法 |
|---|---|---|
| `tests/content/test_world_encounters.py::test_schema_groups_and_locations` 第一段 | 原本用 1 名 `["bandit"]` 驗證「人數不足會擋」，現在 1 名合法 | 改用空陣容 `[]`，仍斷言 `ValidationError`（match `units`）；超過 4 名那段不變 |
| `tests/api/tuning/test_rules_r1_r2_nw2a.py::test_skill_form_shows_the_retier_note` 後半 | 原本拿 `skill_fire_arrow` 的使用者 `bandit_archer_rookie` 驗證「1 階照原樣、不列進升階名單」；它離開渡口後沒有階（`tier` 變 `None`） | 換成同樣「1 階＋高階並存」的唯一一招 `skill_frost_shackle`：`sect_talisman_caster` 是 1 階且不在升階說明裡，另補 `thunder_talisman_caster` 階 > 1；斷言種類與強度不變 |

- 沒有固定種子／雜湊的測試受影響（`tests/content`、`tests/world` 4267 項一次全過；沒有換種子）。
- CLI 快照：`tests/cli/test_output_snapshots.py -m slow` 24 項全過，**沒有重產任何鍵**。

## 3. 新手模擬（`scripts/ob6_newbie_sim.py run --candidates current --per-cell 80 --jobs 4`）

三輪都用本段 HEAD 的程式，只換 `TRPG_CONTENT_DIR`：OB-7 前＝b148dd81 的 `content/`（渡口 3 隻、主角＋賽倫＋阿岳 3 打 3）；OB-7＝6a004e43~1 的 `content/`（渡口 2 隻、主角＋賽倫 2 打 2）；本段＝6a004e43（渡口 1 隻、2 打 1）。前兩欄跟 OB-7 報告的數字完全一樣（DD-1b 之後的程式沒影響這幾場）。只出表、沒調任何敵人數值。

**第 1、2 步（入門配備）**

| 大類 | 步 | 勝率 OB-7 前／OB-7／本段 | 主角倒下率 OB-7 前／OB-7／本段 | 平均輪數 |
|---|---|---|---|---|
| 近戰 | 1 渡口 | 98%／97%／**100%**（160/160） | 10%／13%／**0%**（0/160） | 3.3／3.7／2.3 |
| 近戰 | 2 竹林 | 100%／99%／**100%** | 21%／26%／**2%**（4/160） | 2.5／2.6／2.4 |
| 遠程 | 1 渡口 | 100%／100%／**100%** | 2%／2%／**0%**（0/80） | 2.7／3.4／1.7 |
| 遠程 | 2 竹林 | 99%／98%／**100%** | 11%／16%／**4%**（3/80） | 2.5／2.6／2.4 |
| 法器 | 1 渡口 | 100%／98%／**100%** | 12%／16%／**1%**（1/80） | 2.3／2.5／1.4 |
| 法器 | 2 竹林 | 100%／96%／**100%** | 24%／30%／**5%**（4/80） | 2.1／2.3／2.0 |

**第 3 步路上（正式配備；分母＝走到第 3 步的 80 人）**

| 格 | 主角倒下 OB-7 前／OB-7／本段 | 固定戰勝率（三欄） |
|---|---|---|
| 火焰法杖 點燃＋帶電 | 2%／0%／0% | 80/80 |
| 匕首 冰凍＋隱蔽 | 1%／0%／0% | 80/80 |
| 巨劍 倒地＋撞擊 | 8%／8%／8% | 80/80 |
| 弓 標記＋高處 | 0%／0%／0% | 80/80 |

讀法：渡口 2 打 1 幾乎不會倒（0～1%），而且第 2 步竹林的倒下率也大降（近戰 26→2%、法器 30→5%）——模擬裡第 1、2 步之間不休息，第 1 步省下的 HP 直接帶進第 2 步；另外本段第 1 步沒人輸，所以走不到第 3 步的人數歸零。第 3 步前回城補滿，三欄差不多。模擬是效用 AI 代打，不代表真人手感；數值由使用者在數值工坊判斷。

## 4. 檢查結束碼

| 項目 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0、0 |
| `mypy` | 0（1513 檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0 |
| `pytest tests/content tests/world -n 8` | 0（4267 passed） |
| `pytest tests/roguelite tests/sim tests/api -n 8` | 1 failed（調參台測試，見第 2 節）→ 修正後該檔 0（3 passed）；其餘 1489 passed |
| `pytest tests/cli/test_output_snapshots.py -m slow` | 0（24 passed） |
| `trpg battle --map open_plain --seed 7`＋`replay` | 0、0（91 動作、383 事件一致） |

## 5. 待 PM 決定

1. 渡口 2 打 1 後第 1 步主角倒下率 0～1%、第 2 步也降到 2～5%：教學難度是否太低由使用者在工坊判斷（沒調數值）。
2. `bandit_archer_rookie` 已不在任何遭遇（單位檔、掉落、AI 設定還在）；保留給之後的內容，或另排清理。
3. `MIN_GROUP_SIZE` 放到 1 是全域 schema 規則，「只有渡口 1 隻」靠內容測試鎖，不是 schema 擋；之後要開放路邊 1 隻時改那項測試即可。
