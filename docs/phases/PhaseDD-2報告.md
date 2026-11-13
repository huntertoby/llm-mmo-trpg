# Phase DD-2 完成報告：雙匕首單體武器技的前端（#153）

> 依據：決定 #153（使用者：「改 A」）、`docs/design/08-裝備.md` 8.11「雙匕首的武器技也打兩下」與細節；`PhaseDD-1報告.md` 待決第 8、9 項；`PhaseDD-1b報告.md`。
> 起點：`git merge --ff-only main`（含 DD-1b `ae79627c`，`git merge-base --is-ancestor ae79627c HEAD` 成立）。不改任何數值。

## 1. 交付與 commit

| commit | 內容 |
|---|---|
| `9a729319` | 預覽：後端 `Preview.strikes`／`PreviewOut.strikes`、OpenAPI 與 `schema.d.ts` 重產、前端 `previewText.strikeLines` |
| `2dfb5100` | 出招播兩次打擊：`battle/repeatStrike.ts`，`vfx.ts`、`skillSequence.ts` 切段；`battle/dd2DualStrike.test.ts` |
| `f02cc417` | 武器卡文字（`src/trpg/content/battle.py`） |
| （本 commit） | 報告、截圖、上手筆記第四節第 69 點與第五節測試列、測試檔格式 |

## 2. 做了什麼

### 2.1 預覽（項目 1）

- **普攻雙匕首沒有既有的「下數」寫法**：普攻預覽的傷害（`_attack_numbers`）只取第一下的事件、期望值也只算一下，畫面上只有「命中　暴擊　傷害 a–b（期望 c）」，沒有標下數。所以沒有可以「照著統一」的寫法（見待決 1）。
- 另外查到：**單體技能原本在預覽框裡就沒有命中／傷害行**（`previewLines` 只在多目標或有友軍時列每個目標），只有連鎖、備註、AP 射程。
- 做法（最小）：後端加一個欄位 `strikes`（`skill_strikes(actor, _preview_skill(...))`，只有 `UseSkill` 會 ≥ 2；其他動作 1），前端在 `strikes` ≥ 2 時多一行：
  `c 盜賊2：打 2 下，每下命中 85%，傷害合計 9–18（期望 19.4）`
  數字原樣用伺服器的 `targets[].damage`（DD-1 已是合計：最少＝只中第一下、最多＝每下都暴擊、期望＝每下期望 × 下數），命中率是每一下的。`strikes` 1 時這行不出現，其他技能與普攻的輸出逐字不變（`dd2DualStrike.test.ts` 鎖住）。
- 前端不自己判斷下數（守則「前端不裁決規則」），所以補了後端欄位：`src/trpg/engine/preview.py`（`Preview.strikes`）、`src/trpg/api/schemas.py`（`PreviewOut.strikes`，預設 1）；`client/openapi.json`、`client/src/api/schema.d.ts` 各多 5 行。

### 2.2 出招播兩次（項目 2）

- 引擎（DD-1 `Cast.extra_strikes`）在技能全部效果結算完後，對同一目標再發一次 `attack_rolled`，沒有第二個 `skill_used`；原本前端把它併進同一段，只播一次出招。
- 現在：技能段裡施放者對「這一段已擲過命中的單位」又擲一次命中，就開新的一段，`basic: true`——和普攻雙匕首一樣「每個 `attack_rolled` 一段」：普攻變體照那個 `attack_rolled` 的 `seq` 挑、不蓄力、受擊與閃避算在第二段。守護者攔下時（`attack_intercepted`）守護者也記進去，第二下打守護者一樣切段。
- 判定放在 `client/src/battle/repeatStrike.ts`，`vfx.ts` 的 `opensSegment` 與 `skillSequence.ts` 的 `splitSegments` 共用，兩邊段數一一對應。
- 第一下打倒：引擎不打第二下、沒有第二個 `attack_rolled`，照事件只播一下。
- 其他技能不受影響的理由：一次施放對同一個單位本來只擲一次命中（`Cast.roll_hits` 每個目標一次；衝撞每個穿過的敵人一次），只有連擊武器多打的那幾下會重複。測試含範圍技兩個目標各擲一次＝照舊一段、別人的命中判定（反擊）不算。

### 2.3 武器卡文字（項目 3）

- 來源只有一處：`src/trpg/content/battle.py` 的 `_weapon_batch_two_lines`（`WeaponDef.trait_lines_zh()` 呼叫）；前端只顯示伺服器的 `weapon_traits_zh`，`content/` 與前端沒有這句。
- 舊：「連擊：普攻一次打 2 下，每一下各自擲命中與傷害；背刺時每一下都吃背刺加成（武器技只打一次）」
- 新：「連擊：普攻與單體武器技都打 2 下，每一下各自擲命中與傷害；背刺時每一下都吃背刺加成（武器技的附加效果只結算一次）」——括號原本寫「武器技只打一次」已經不對，改成 08 8.11 的「附加效果只結算一次」（見待決 4）。
- 天生武器（形態）的連擊只給普攻，但形態中畫面顯示的是手上的武器（`view.py` 用 `held_weapon`），天生武器的特性行不會出現在這裡。

## 3. 改到的既有測試（舊 → 新、為什麼）

| 測試 | 舊 → 新 | 為什麼 |
|---|---|---|
| `tests/engine/test_weapons_dual_dagger_firearm.py::test_trait_and_rule_lines_follow_the_data` | `startswith("連擊：普攻一次打 2 下")`／`3 下` → `startswith("連擊：普攻與單體武器技都打 2 下")`／`3 下`（另外 `ruff format` 把過長的那行折行） | 項目 3 改字 |
| `tests/api/test_routes.py::test_preview_returns_the_numbers_and_does_not_change_the_session` | 預覽回應的欄位集合多 `"strikes"` | 項目 1 新欄位 |

新增：`tests/engine/test_dual_dagger_skills_dd1.py::test_the_preview_reports_how_many_strikes_the_damage_adds_up`（雙匕首 2；單手劍、法術、普攻 1）；`client/src/battle/dd2DualStrike.test.ts`（10 項：兩下兩段、第二下沒中、第一下打倒一段、單擊與範圍技照舊、普攻照舊、守護者、別人的命中判定；預覽行三項）。

快照與雜湊：沒有重產任何快照或雜湊。`client/openapi.json`／`schema.d.ts` 依 API 改動的正規流程重產，差異只有 `strikes` 一個欄位（各 +5 行）。CLI 快照（`-m slow`）24 passed、沒有變。沒動 `content/`、戰鬥紀錄格式（`LOG_FORMAT` 不變：預覽不進紀錄）。

## 4. 截圖（`docs/art/shots/dd2/`，3 張，jpg 80）

實機：`build_assassin` 主角換成雙匕首（自己的 `trpg serve --port 8765`、`TRPG_DEV_ROUTES=1`、存檔在 scratchpad；無頭 Chrome `--mute-audio`、`?dev=1&anim=0.1&mute=1`；開發選單「單場戰鬥 → 開始戰鬥」，CDP `Fetch` 把那次 `POST /api/battles` 的內容換成 `{map_id: open_plain, seed: 1, hero_build: build_assassin, equipment: {main_hand: {item_id: item_dual_dagger}}}`，之後的動作都是頁面自己送）。第 1 輪主角回合，對相鄰的盜賊2（HP 18）放「獵殺落單」。

| 檔案 | 看到的 |
|---|---|
| `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/dd2/dd2-1-preview.jpg`（1600×900，137 KB） | 左側預覽第一行「c 盜賊2：打 2 下，每下命中 85%，傷害合計 9–18（期望 19.4）」，其餘行照舊 |
| `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/dd2/dd2-2-two-strikes.jpg`（合圖 6 格，88 KB） | ① 技能出招 → ② 第一下命中白閃 → ③ 兩下之間 → ④ 第二下出招 → ⑤ 第二下命中白閃 → ⑥ 播完浮出 −7、−5。時間＝牆鐘 ÷ 10（`anim=0.1`），約 ±15 ms |
| `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/dd2/dd2-3-weapon-card.jpg`（1600×900，137 KB） | 釘住主角的格子資訊卡、滑過「雙匕首」：說明卡第一行是新字 |

浮動卡：本段沒動浮動卡元件與版面，沒有做「滑進卡片 → 捲到底 → 釘住 → 關閉」的 1600／800 實測；800×600 沒拍。

## 5. 檢查（結束碼）

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（315 檔、4059 項） |
| `corepack pnpm -C client build` | 0 |
| `ruff check .`、`ruff format --check .` | 0、0 |
| `mypy` | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0 |
| 相關 pytest：`test_dual_dagger_skills_dd1.py`、`test_weapons_dual_dagger_firearm.py`、`test_preview.py`、`test_skill_preview.py`、`test_gamble_preview_ai.py`、`test_scene_preview.py`、`test_variance_preview.py`、`test_preview_difficulty_bal4c.py`、`tests/api/test_routes.py`、`test_openapi_snapshot.py`、`test_client_fixtures.py`、`tests/test_architecture.py`、`test_determinism.py` | 0（234 passed）；另外開發中跑過整個 `tests/api`（1094 passed，唯一失敗即上表 `test_routes` 那項，已改） |
| `tests/cli/test_output_snapshots.py -m slow` | 0（24 passed） |
| `trpg battle --map oil_depot --seed 13 --log-json`＋`trpg battle replay` | 0、0 |

沒跑完整 `scripts/check.py`、沒跑模擬、沒 push。自己啟動的 `trpg serve`（8765）與無頭 Chrome（CDP 9333，每次腳本結束用 `Browser.close` 關）交件前已關：`trpg serve` 用自己的 PID `taskkill /T`，8765 已沒有監聽；自己啟動的 Chrome（記下的 10 個 PID）都已不在。交件時 9333 上有另一個 Chrome 在聽，頁面是 `127.0.0.1:8743`（不是本段的伺服器），判斷是別的 agent 的，沒有動它。

## 6. 待 PM 決定

1. **普攻雙匕首的預覽沒有「下數」**：普攻的傷害與期望只算第一下、也沒標「2 下」，所以「照普攻寫法統一」沒有對象；本段只改技能。要不要普攻也標（例「傷害 3–6（期望 4.6）× 2 下」，期望要不要也合計）。
2. **其他單體技能的預覽本來就沒有命中／傷害行**（只有多目標或友軍時才列），所以現在雙匕首單體武器技比其他單體技能多一行數字。要不要所有單體技能都列這一行（`strikes` 1 時不寫「打 N 下」）。
3. **期望值可能大於最多**：截圖那一下目標 HP 18，最多被 HP 擋在 18，期望 19.4（每下期望 × 2，沒扣「第一下打倒」與 HP 上限；DD-1 待決 8 的延續）。要不要後端把期望值夾在最多以內，或前端另寫。
4. 武器卡括號寫「（武器技的附加效果只結算一次）」，比 PM 例句多一段；要不要拿掉括號。
5. 第二下照普攻播（普攻變體、不蓄力、沒有技能的蓄力／元素起手），不是把技能的出招片段再播一次；要第二下也像技能，另議。
6. 實機看到傷害數字在整招播完後才一起浮出（−7、−5 疊著出現），不是每下命中時各出一個；本段沒動浮動字的排程，也沒逐一核對普攻雙匕首是否同樣如此。

## 開發 PM 裁定（2026-11-12，第八任）

1、2 照現狀（普攻雙匕首與其他單體技能的預覽寫法不在本段範圍）。3 期望值大於最多是錯的，排小修夾住（期望 ≤ 最多）。4 括號保留。5 第二下照普攻變體播：接受。6、7 照現狀。
