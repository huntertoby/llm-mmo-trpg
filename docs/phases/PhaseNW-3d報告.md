# Phase NW-3d 報告｜造牆物件候選統一＋1600 黑煙

依據：`docs/玩法PM交接.md` 4.1.16（49cbf4a8c）；`docs/phases/PhaseNW-3c報告.md`（含開發 PM 裁定）；美術 GB-4d 待決 1 更正（`docs/art/GB-4b驗收.md` 末節，0a93ed38）；`docs/phases/PhaseGB-4d報告.md`。起點：本機 main `ec4aed440`（`24ccb36e3` 之後只多開發 PM 派工一個 commit，fast-forward）。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| 1600 黑煙也壓煙頂 | `partBreakFx.giantSmokeCeil` 拿掉 `isCompactRow` 那一層：800、1600 都把噴口破的黑煙壓在 HUD 下緣往下 2 畫面 px；沒有 HP 條（`noBar`）才不壓（同以前）。開發頁 `gb4bGiantGallery` 本來就呼叫同一個函式，只改註解。`gb4dGiantFixes.test.ts` 的 1600 測試從「照舊 undefined」改成「800、1600 都有上限；修之前煙頂高過上限、壓了以後每團煙含外框都在上限以下」 | `7278d310d` |
| LLM 提議的造牆物件 | `proposal/params.py` 的 `_Refs.objects` 改成 `composer_parts.obstacle_candidates(library)`。`object` 型參數全內容只有 `create_obstacle.object` 一處，投擲（`hurl_object`）沒有這個參數、丟的是場上已有的物件，不受影響 | `837e4dfc7` |
| 技能工坊的物件選單 | 後端 `option_params._obstacle_choices`＝同一份候選（照 `objects.yaml` 順序）。送出時 `option_conform` 照選單擋，冷卻井、油桶會報「物件不在可選範圍內」。**前端沒改**：`FieldEditor` 照 API 給的 `choices` 畫，沒有自己的物件清單 | `837e4dfc7` |
| 報告、上手筆記 | 本報告；`上手-內容資料與模擬.md` 第七節「組合器的造牆排除清單」一點、`上手-前端戰鬥畫面與動畫.md` 第 194 點 | 本報告 commit |

造牆候選現在三處一致：木箱、枯樹、土牆、倒木、冰牆、矮牆、倒塌物、石柱、荊棘叢（9 個）；冷卻井、油桶、草叢、木橋、薄冰這類都選不到。

## 2. 逐條驗收

| 驗收 | 結果 |
|---|---|
| 新規則有測試 | **過**。`tests/skillgen/test_obstacle_choices_nw3d.py`（11 項）：`object` 型參數只有 `create_obstacle.object`、投擲原語沒有；候選不含冷卻井、油桶（兩者仍在內容裡）；LLM schema 裡每個 `create_obstacle` 的 `object` 列舉＝候選；提議把石牆術的物件換成冷卻井／油桶 → `proposal` 階段 `effects[0].object` 報錯、可用值不含它；土牆照樣通過；工坊選單＝候選且照 `objects.yaml` 順序；工坊送冷卻井／油桶報錯、土牆沒問題；**場上的油桶照舊是投擲的合法目標**（`legal_actions` 有對它的投擲）。`tests/api/test_workshop_obstacles_nw3d.py`（1 項）：`/api/workshop/options` 給前端的選單與檢查同上。前端 `render/gb4dGiantFixes.test.ts`：1600 的煙頂不碰 HUD（含「修之前會碰」） |
| 戰鬥不變比對 46 場 | **過**：`battles=46 events=20458 different=0`，`hash_ruleset`／`ruleset_hash`／`content_digest` 相同（第 3 節） |
| CLI 快照 | 預測 **0 鍵**，實際 **0 鍵**（第 4 節） |
| OpenAPI | 沒改 API 型別（選單是資料，不是 schema），不用重產；`tests/api/test_openapi_snapshot.py` 過 |
| 全量 vitest、build | vitest 結束碼 0（370 檔、4676 項）、build 0（第 5 節） |
| 相關 pytest | `tests/skillgen tests/llm tests/api tests/roguelite tests/world tests/sim tests/narrative`（`-n 8`）**8271 passed、15 skipped、0 failed** |
| commit 前檢查 | `ruff check`、`ruff format --check`、`mypy`（1620 檔）、`lint-imports`（14 kept）全過；`tsc` 0 |

## 3. 不變比對

改前＝`git archive ec4aed440 src content` 解到 scratchpad，`PYTHONPATH=<暫存區>/src` 跑（腳本印出 `trpg.__file__` 確認）；改後＝本段工作樹。同 NW-3c 的 46 場（8 張地圖 × 種子 1、2 ＋ `cloud_summit`、`rift_gate`、`molten_heart_pit` × 種子 3～12；地圖預設陣容、效用 AI、`max_rounds=30`），每場比事件、步驟、回合、勝方、亂數狀態、最終狀態（拿掉 `ruleset`）逐位元組。

- **`battles=46 events=20458 different=0`**；三個雜湊相同。事件數比 NW-3c 的 19276 多，是之後幾段（GB 系列等）改了戰鬥內容，兩邊同一份 baseline，與本段無關。
- 理由也成立：沒改引擎、規則包、內容；戰鬥用內建技能，不經過提議與工坊。

## 4. 快照：預測與實際

| 對象 | 預測 | 實際 |
|---|---|---|
| LLM prompt 快照（`tests/llm/test_prompts.py` 等的 SHA-256） | **不變**：快照的訊息用 `available={"primitives": ["damage"]}`，不含提議 schema；prompt 文字沒改，不升版本號 | 不變，`tests/llm` 全過 |
| LLM 提議 schema | 只有兩處 `create_obstacle.object` 列舉從全部物件縮成 9 個；沒有任何快照或夾具存 schema | 同預測；新測試鎖住列舉＝候選 |
| Mock 夾具（`tests/cli/snapshots/llm_propose_mock.txt`、各 `mock_*`） | **不變**：Mock 提議不用 `create_obstacle`；手寫造牆技能（土牆、冰牆、荊棘叢）都在候選內，`proposal_from_skill` 往返與出題可行解不受影響 | 不變 |
| CLI 快照（`cli_output_hashes.json` 24 鍵） | **0 鍵**：都是內建技能與戰鬥，不經過提議 schema 與工坊選單 | 0 鍵：`uv run pytest -q tests/cli -m slow` 44 passed；`test_output_snapshots.py`、`test_llm_propose_cli.py` 非 slow 9 passed；沒重產 |
| `tests/skillgen/fixtures/refactor_3wr2.json` | 不變（不經過提議列舉） | 不變 |

沒有重產任何快照或夾具。

## 5. 前端全量

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `corepack pnpm -C client exec tsc --noEmit -p .` | 0 | |
| `corepack pnpm -C client test` | 0 | 370 檔、4676 項全過 |
| `corepack pnpm -C client build` | 0 | 只有既有的 chunk 大小警告 |

## 6. 截圖（`docs/art/shots/NW-3d/`，DPR 1、jpg 80）

| 檔 | 看什麼 |
|---|---|
| `01-vent-smoke-1600-dev.jpg` | 開發頁 `gb4b-giant.html?set=break&group=0&only=2,3&w=1600&zoom=2`（地圖縮放 1.308，真 1 倍＋×2）。噴口破第 3 格（斷開）、第 4 格（落地）。**第 4 格中間那團煙在 HP 條、部位條（含紅「×」）與白色朝南三角形下面，沒有碰到**（GB-4d 截圖 04 對照：原本蓋到 HP 條）；兩側煙疊在噴口口上 |
| `02-vent-smoke-800-dev.jpg` | 同兩格 800（0.531，×4），對照用：和 GB-4d 一樣 |
| `03-workshop-obstacle-menu.jpg` | 實機技能工坊（`trpg serve` ＋ build，`?dev=1&mute=1`）效果步驟的「產生障礙」：物件選單 9 項（石柱、木箱、土牆、矮牆、倒木、枯樹、倒塌物、冰牆、荊棘叢），沒有冷卻井、油桶。原生下拉選單打開時截不到，拍照前用除錯腳本把 `<select>` 暫設 `size` 攤開成清單（只為截圖，程式沒改） |

## 7. 實機未看

- 1600 黑煙只在開發頁看（遊戲與開發頁同一個 `giantSmokeCeil`＋`giantBreakCanvas`）。實機要 1600＋打破噴口，沒拍。
- LLM 提議沒連真模型（測試一律 Mock）；列舉縮小只會讓模型少一些選項。

## 8. 待 PM 決定

1. **`object` 型參數＝造牆物件**：目前只有 `create_obstacle.object` 用 `object` 型，所以直接把這個型別的列舉換成造牆候選。日後若有別的原語也要 `object` 型參數（而且不是「造」），要另開型別；新測試 `test_only_create_obstacle_takes_an_object_param` 會先紅提醒。
2. **工坊選單照 `objects.yaml` 順序**（石柱、木箱、土牆…），不照候選的字母順序；和改之前的選單排法一致。
