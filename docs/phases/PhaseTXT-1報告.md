# Phase TXT-1 報告：玩家看得到的字不出現設計編號

> 依據：玩法 PM 11-12 的決定（`docs/art/資訊面板版面提案.md` 第 10 節 6.4 第 1 件，經美術 PM 轉達）。
> 不改數值與規則。

## 1. 做法

- 事件骨架的解法（`SolutionDef`）原本只有 `note_zh`（選項格主字），沒有說明欄位。為了照範例把括號說明移到說明卡，加一個選填欄位 `hint_zh: str = ""`（`src/trpg/content/world_events.py`），API 的 `EventSolutionView.hint_zh`（`src/trpg/api/world_story_schemas.py`、`world_story_view.py::_solutions`）原樣轉給前端。
- 前端 `client/src/world/story.ts::solutionHint`：可以用時，`hint_zh` 放在說明卡第一行，下面接原本的種類說明；不能用時照舊只顯示原因。說明卡標題（`solutionLabel`）照舊是「種類：主字（屬性）」。
- `client/openapi.json`、`client/src/api/schema.d.ts` 重產（只多 `hint_zh` 一個選填欄位）。
- 選項圖示（`narration.ts::solutionIcon` 看主字關鍵字）：四處改字後圖示都不變（「說服」仍命中「說服」；其餘三處新舊主字都沒有方法關鍵字，照屬性退回，同改前）。

## 2. 逐條改動

| # | 位置 | 舊字 | 新主字（`note_zh`） | 說明卡（`hint_zh`） |
|---|---|---|---|---|
| 1 | `content/world/events/cloud_ridge.yaml` `tavern_storyteller` 解法 0 | 文字回答＋用心清單（#85） | 用自己的話回答 | 回答得用心可以加分（最多 +2） |
| 2 | `content/world/events/cloud_ridge.yaml` `fox_traveler` 解法 1 | 說服（獸耳族主角有專屬對話選項，不加數值，#138） | 說服 | 獸耳族主角有專屬的對話 |
| 3 | `content/world/events/ashen_waste.yaml` 骨架 14 解法 0 | 文字回答＋用心清單（#85） | 用自己的話回答 | 回答得用心可以加分（最多 +2） |
| 4 | `content/world/events/ashen_waste.yaml` 骨架 3 解法 1 | 異象（與火溝通；角魔主角 +1，#89） | 異象 | 與火溝通；角魔主角 +1 |

第 1～3 條照玩法 PM 的範例原話；第 4 條比照處理（括號說明原樣移到說明卡，只拿掉編號）。

後端字串（`src/trpg` 非 docstring 的字串常數）與 `client/src` 寫死的玩家可見字：沒有找到玩家看得到的「#數字」（見第 3 節）。

## 3. 掃過但判定玩家看不到、沒改的

| 位置 | 內容 | 理由 |
|---|---|---|
| `content/skill_primitives.yaml` `apply_status`、`create_surface` 的 `params.magnitude_permille.description_zh` | 「（BAL-12e，#76，…）」 | 原語的程式化說明，只在工坊開發者模式（`?dev=1`）顯示；玩家模式顯示 `workshop_text.yaml` 的 `player`（兩筆都有對照） |
| `content/skill_primitives.yaml` `lower_terrain.description_zh` | 「…把單位推進去才會墜落，#66）」 | 同上；玩家看的是同一筆的 `player_description` |
| `content/workshop_text.yaml` 兩筆 `source` | 同上 #76 原文 | 查表用的鍵，必須和 `skill_primitives.yaml` 逐字相同；改了玩家說明會對不到 |
| `content/world/npcs/cloud_ridge.yaml` 4 筆 `hooks_zh` | #95、#97、#138、#133／#132 | 人設卡送說書人前一律換成好感度能給的內容（`api/world_story.py::_card_for`），原文不送出 |
| `src/trpg/api/tuning/service.py`、`writeback.py` | 「低於 #149 招數下限」「#149 例外：」 | 數值工坊（開發用，`TRPG_TUNING=1` 才掛路由）；`writeback.py` 那句是 commit 內文，測試與還原依它比對 |
| `client/src/tuning/DraftPanel.tsx`、`TuningScreen.tsx`、`skillModel.ts` | 「#149 例外」 | 同上，數值工坊畫面 |
| `client/src/workshop/fixtures/random_seed42.json`、`client/src/battle/fixtures/vfx_random_skills.json` | 「火焰・姿態 #42」這類 | 舊的隨機技能測試夾具（種子編號，不是設計編號）；組合器 2026-10-23 起名稱已不帶 `#`（`random_composer.py::_finish`） |
| `tests/world/frozen_replay/events.json` | 「文字回答＋用心清單（#85）」 | 測試用的凍結複本，不是玩家內容 |

## 4. 測試

- 新增 `tests/content/test_no_design_numbers_txt1.py`：
  - `content/` 底下**所有** YAML／JSON 的字串值（不限 `*_zh`）不得含「#數字」或「＃數字」；排除第 3 節的 `skill_primitives.yaml::description_zh`、`workshop_text.yaml::source`、`world/npcs/cloud_ridge.yaml`／`ashen_waste.yaml::hooks_zh`；顏色碼（`#4a6a5a`、`#103030`）不算。
  - `src/trpg/**/*.py` 非 docstring 的字串常數不得含「#數字」；排除 `api/tuning/service.py`、`api/tuning/writeback.py`。
  - 排除清單的檔案要存在（改名時跟著改）；正規式自身的正反例。
  - 事件卡 API：獸耳族旅人那一格是 `("說服", "獸耳族主角有專屬的對話")`；兩個說書人骨架是 `("用自己的話回答", "回答得用心可以加分（最多 +2）")`。
- 前端 `client/src/world/story.test.ts` 加一項「補充說明只在說明卡」。
- 改到的既有測試：無（沒有既有測試寫死這四段字）。

## 5. 雜湊與快照

- 改了兩個事件檔：`ruleset_hash`、`content_digest` 會變（`library.files`）；事件不在規則包，`hash_ruleset` 不變，舊戰鬥紀錄照樣重播。使用者重開伺服器後進行中的一輪從頭開始、世界日誌標成不能重播。
- CLI 快照（`tests/cli/test_output_snapshots.py -m slow`）全數通過，沒有重產任何鍵。
- 沒有測試寫死 content digest 而變紅（見第 6 節結束碼）。
- 請使用者重開伺服器檢查的重點：雲嶺說書人、狐耳旅人、灰燼荒原說書人與「異象」那格的選項主字沒有「#數字」，滑過選項時說明卡第一行是補充說明。

## 6. 檢查（結束碼）

分支 `txt1-finish`＝前一個 agent 的 `worktree-agent-afafa8fcce8335864`（4019e289）再 `git merge main`（main 當時 876f1d3b，含 QI-7、PNL-1a／1b／2／3、NW-2c）。合併無衝突；`client/openapi.json`、`client/src/api/schema.d.ts` 自動合併後 `tests/api/test_openapi_snapshot.py` 直接通過，沒有重產。main 新增的程式與內容裡的「#數字」只在註解與 docstring（`client/src/api/client.ts` 的 JSDoc、`schema.d.ts` 的 `@description`），玩家看不到，新測試也沒抓到任何一筆，排除清單不變。

以下都在合併後的 `txt1-finish` 上跑：

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run mypy` | 0 | 1525 個檔沒有問題 |
| `uv run lint-imports` | 0 | 14 kept、0 broken |
| `uv run trpg content check` | 0 | 662 個檔、404 個技能 |
| `uv run pytest -q -n 8 tests/content tests/api tests/world` | 0 | 5429 passed、1 skipped |
| `uv run pytest -q -m slow tests/cli/test_output_snapshots.py` | 0 | 24 passed；沒有重產任何鍵 |
| `corepack pnpm -C client typecheck` | 0 | |
| `corepack pnpm -C client test --run` | 0 | 326 個檔、4239 項通過 |
| `corepack pnpm -C client build` | 0 | 只有既有的「chunk 大於 500 kB」警告 |

沒有跑完整的 `scripts/check.py`（依規定由 PM 跑）。

## 7. 待 PM 決定

1. 第 4 條（灰燼荒原「異象」）的說明卡沿用原括號「與火溝通；角魔主角 +1」，是否要改成更口語的說法由玩法 PM 定。
2. `skill_primitives.yaml` 的 `description_zh`（#76、#66）與 `workshop_text.yaml` 的 `source` 在開發者模式看得到；要一起清，需兩檔同步改並確認是否進規則包雜湊，建議另排。
