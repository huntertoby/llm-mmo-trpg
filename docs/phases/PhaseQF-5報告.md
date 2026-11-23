# Phase QF-5 報告｜前端小修合併段（佇列 (aa)、(o)、(h)、(q)）

實作者，2026-11-23，worktree `agent-a3352e2de7142e3c4`，基準 `7e0c34917`。

> **狀態：全部完成。** 開發 PM 說「可以跑」後先 `git merge --no-edit main`（只多 `docs/開發PM交接.md`），`check.py --all` 第 1 次擋下 1 題（見 3.3），修正後第 2 次 0；build 0；三項比對都 different=0。

## 1. Commit

| commit | 內容 |
|---|---|
| `c1cd8c82c` | (aa) `WrapUnits` 在全形「（」前、「，」後切段；提示行也走 `WrapUnits` |
| `d267da704` | (o) 一招只套一種變形：前後端測試（兩個變形、只有一個變形） |
| `cba192998` | (h) 刪 `skeletonName` 沒人用的 `override` 參數 |
| `9a9462c3b` | (q) API 地圖摘要加 `role`；試打面板改讀 `role`；程式需要的地圖用途存在檢查 |
| `879328333` | 截圖 `docs/art/shots/qf-5/`（3 張） |
| `5982daee1` | 報告（全量待跑） |
| merge main | `git merge --no-edit main`，只多 `docs/開發PM交接.md` |
| `554312b76` | (q) 修正：`CODE_REQUIRED_ROLES` 的說明字拿掉「[0]」（寫死數字掃描 `test_hardcoded_scan` 擋下） |

## 2. 做法

### 2.1 (aa) 切段規則

- `client/src/ui/WrapUnits.tsx`：分隔規則改成 `/(?<=[・、　，])|(?=（)/u`。「，」和「・」一樣留在前一段尾巴；「（」歸下一段的開頭，括號整段一起移。開頭就是「（」不會多出空段，接起來仍是原字。
- `CritDamageDetail.tsx`：提示行「另有看目標的加成，攻擊預覽時才算」原本是純文字，沒有切段，改成也包 `WrapUnits`，才會從逗號處換行。
- 三處都測：「傷害 55–288」／「（期望 69.3）」、「詞條 +10%」／「（全身上限 300%）」、「另有看目標的加成，」／「攻擊預覽時才算」（`wrapUnits.test.ts` 兩題：純函式＋預覽面板、單位卡接線）。`critDamageHint.test.ts` 原本比對提示行的原始 HTML，改成先去標籤再比字。

### 2.2 (o) 技能卡「已有其他變形」

- **已經做好了**：KD-1 第 8 項（`5ccfff69d`）後端 `UnitView.skill_notes_zh` 已經傳出「已有其他變形，〇〇的△△不會套用」，判定照 `modifiers.gear_reshapes_left_out`（技能鍵排序第一個通過閘門的生效）；前端 `skillButtons` → `reshapeNotes` → `SkillCardView` 的灰字也已接上。所以這段**沒有改程式**，後端沒有補任何欄位。
- 補的測試：
  - 後端 `tests/engine/test_reshape_notes_kd1.py`：只有一個變形時沒有灰字；兩個變形時灰字寫出物品名與沒生效的那個，且其他陣營看不到（守則 14）。原有的「兩個變形，另一個加註」那題保留。
  - 前端 `client/src/ui/qf5ShapeTaken.test.ts`：兩個變形（後端給灰字）時技能卡畫出來；只有一個變形（後端不給）時沒有；別招的灰字不會畫到這招（前端不自己判斷）。

### 2.3 (h) 刪參數

- `client/src/battle/glossary.ts` 的 `skeletonName(id)` 拿掉第二個參數 `override` 與它的分支；兩個呼叫端（`skillIcon.ts`、`wl1cGallery.tsx`）本來就沒傳。
- `wl1bSkeletonName.test.ts`：「override 參數仍可覆寫」那題改成鎖「只收一個參數」；原型鏈名字那題拿掉多傳的 `{}`。

### 2.4 (q) 試打面板讀 role

- 後端 API：`MapSummary` 加 `role: MapRole | None`（讀 `map_archetypes.yaml`），`/api/maps` 與 `/api/workshop/arena` 改用共用的 `schemas.map_summary(library, map_def)`。重產 `client/openapi.json`、`client/src/api/schema.d.ts`（多一個 `MapRole` enum，`MapSummary.role?`）。
- 前端：`tryout.ts` 的 `isTrainingMap` 看 `role === "training"`；`TryoutPanel.tsx` 的選單附註抽成 `mapRoleNote(map)`（`training`「（試玩專用，預設）」、`boss`「（頭目地圖）」，其他與舊伺服器沒有欄位時空字串），顯示字不變。
- 防回歸：`tests/test_no_archetype_literals.py` 的前端已知清單（3 處）清空，改成前端一處都不能比對類型 ID。
- **存在檢查**（開發 PM 選 B）：只改 `src/trpg/content/maps.py`，不碰 `load.py`。新增 `CODE_REQUIRED_ROLES`（`test`、`training`、`boss` → 用到它的地方），`MapArchetypeTable` 的 validator 在載入時檢查每種用途至少有一個類型，缺了報「缺少程式需要的地圖用途（role）：training（技能工坊的靶場……）」。`trpg content check` 0。
- 測試：`tests/content/test_code_required_map_roles.py`（資料都在、程式裡 `has_role`／`role_ids`／`role_label` 用到的用途都在清單、缺任一用途時中文報錯、從資料檔刪掉 `role: training` 時載入失敗）；`test_routes.py`（`/api/maps` 多 `role` 鍵、一般地圖都是 null）；`test_workshop_api.py`（arena 每張圖的 `role` 和類型清單一致、前端夾具和真的一致）；`workshop.test.ts`（類型 ID 叫 training 但沒有 role 的不算靶場，換了名字但 role 是 training 的算；附註四種情況）。
- `test_map_archetypes_from_data.py` 原本用只有一列 `x` 的表測 `role_label` 的退路；這種表現在載入時就擋下，改用 `model_construct` 建表測同一件事。

**重產的夾具逐鍵列出**（`client/src/workshop/fixtures/arena.json`，只多 `maps[].role`，其他鍵不變）：

| 地圖 | archetype | 新增 `role` |
|---|---|---|
| training_range | training | `"training"` |
| bridge_chasm | bridge_chasm | `null` |
| cliff_outpost | ruined_heights | `null` |
| dark_forest | forest | `null` |
| frozen_lake | frozen_lake | `null` |
| lava_crossing | bridge_chasm | `null` |
| narrow_halls | corridor | `null` |
| oil_depot | oil_depot | `null` |
| open_plain | open_plain | `null` |
| ruined_fort | ruined_heights | `null` |
| swamp | swamp | `null` |

## 3. 驗收

### 3.1 結果不變（different=0）

基準 `7e0c34917` 的 `git archive`（`src`、`content`、`config`、`scripts`）；新版是全部程式 commit（含 `554312b76`）之後的工作區。腳本沿用 CR-1c 的 `compare78.py`、`budget.py`、`census_cmp.py`（暫存區 `qf5/run_cmp.sh`）。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`） | 442 招，兩邊結束碼 0，`cmp` 0（逐位相同） |
| 78 場（`compare78.py`；`format` 也比） | `battles=78 events=26741 different=0`；內嵌規則包差異 0；結束碼 0 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0 whole_equal=True`（兩邊結束碼 0） |

### 3.2 檢查指令（開發中）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy src tests` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 0 |
| `corepack pnpm -C client exec tsc --noEmit` | 0 |
| vitest：`src/ui/`、`src/run/`（(aa)） | 0 |
| vitest：`qf5ShapeTaken`、`kd1SkillNotes`（(o)） | 0 |
| vitest：`wl1bSkeletonName`、`skillIcon`（(h)） | 0 |
| vitest：`src/workshop`、`src/ui/workshop`、`hc6bRuleText`（(q)） | 0 |
| pytest：`test_reshape_notes_kd1.py`（(o)） | 0 |
| pytest：`test_code_required_map_roles`、`test_map_archetypes_from_data`、`test_map_archetype_new_type`、`test_no_archetype_literals`、`api/test_routes`、`api/test_workshop_api`、`api/test_openapi_snapshot`（(q)） | 0（87 passed） |
| `corepack pnpm -C client build`（截圖前） | 0 |

### 3.3 全量檢查

| 指令 | 結束碼 |
|---|---|
| `uv run python scripts/check.py --all`（merge main 之後，第 1 次） | 1：pytest 1 題失敗（`tests/test_hardcoded_scan.py::test_every_hardcoded_number_is_classified`）。`CODE_REQUIRED_ROLES` 的說明字「取 role_ids('test')[0]」含數字，沒有歸類；改字成「取第一個 role: test 的類型」（`554312b76`），不動 `scripts/hardcoded/classes.yaml` |
| `uv run python scripts/check.py --all`（第 2 次） | **0**：pytest 18720 passed、8 skipped；vitest 422 檔 4984 passed；ruff、format、mypy、lint-imports、client typecheck、situation coverage 通過；已寫通過戳記 |
| `corepack pnpm -C client build`（check 之後） | **0** |

### 3.4 截圖（`docs/art/shots/qf-5/`，交美術 PM）

`trpg serve --port 8795`（`TRPG_SAVE_DIR` 指暫存區、`TRPG_DEV_ROUTES=1`）、`?dev=1&mute=1&anim=0`、無頭 Chrome `--mute-audio`、DPR 1；jpg 品質 80。開發選單「弓＋點燃＋標記」開戰，包 fetch 把地圖換成開闊平原。

**注入資料**（真實內容碰不到，照 RG-3 的做法在回應裡注入，只在截圖的瀏覽器裡）：主角陣營單位的 `crit_damage_hint_zh` 設成「另有看目標的加成，攻擊預覽時才算」（現有內容沒有看目標的暴擊修正技）；主角第一招（引火彈）的 `skill_notes_zh` 設成「已有其他變形，彈射護腕的連鎖彈射不會套用」（現有內容沒有裝備變形）。

- `docs/art/shots/qf-5/qf5_attack_preview_800x600.jpg`：普攻預覽「命中 60%　暴擊率 5%」／「傷害 40–190（期望 47.3）」。這一次的數字放得下，「傷害」和「（期望）」兩段排在同一行；放不下時「（期望 …）」整段移到下一行由 vitest 鎖住（實機沒拍到斷開的樣子）。
- `docs/art/shots/qf-5/qf5_unit_card_800x600.jpg`：釘住主角的單位卡、展開「▸ 詳細」：「武器「弓」200%」／「（全身上限 300%）」，提示行「另有看目標的加成，」／「攻擊預覽時才算」（提示行是注入的）。
- `docs/art/shots/qf-5/qf5_skill_card_shape_taken_1600x900.jpg`：滑過技能列「引火彈」，技能卡內文最後灰字「已有其他變形，彈射護腕的連鎖彈射不會套用」（注入的）。

截圖後伺服器與 Chrome 用自己的 PID（`taskkill /PID … /T /F`）關掉。

## 4. 複雜度

沒有新加 `# noqa`。

## 5. 待 PM 決定

1. **(o) 已在 KD-1 做完**：後端欄位與前端灰字 KD-1 第 8 項就有了，這段只補測試。佇列 (o) 可以直接結案。灰字用字「已有其他變形，〇〇的△△不會套用」是 KD-1 時「待玩法 PM 定」的暫定字（`SHAPE_TAKEN_ZH`），玩法 PM 是否已定沒有查到，沿用。
2. **(q) 存在檢查放在 `MapArchetypeTable` 的 validator**（開發 PM 選 B）：缺用途時是 pydantic 驗證錯誤（經載入器包成 `ContentError`，帶 `map_archetypes.yaml` 路徑）。這也代表**少於三種用途的表一律建不起來**，測試裡要造小表得用 `model_construct`；目前只有一題受影響，已改。
3. **`CODE_REQUIRED_ROLES` 三種都列**：`test` 只有開發用量測工具 `sim/leap_check.py` 用到，照 WL-2 報告第 4 點「會 IndexError」也列進去。要放寬（只列 `training`、`boss`）就刪一行。
4. **截圖的提示行與變形灰字是注入的**：現有內容碰不到。實機未看：真的有兩件裝備變形時的技能卡、真的有看目標修正技時的單位卡。
5. **`StartScreen.tsx` 的地圖選單還顯示類型 ID**（「（10×10・open_plain）」）：只是顯示、不是分支，不在 (q) 的三處裡，沒改。

## 開發 PM 驗收（2026-11-23）

**通過**，已合併進 main。`check.py --all` 第 2 次 0（第 1 次擋在硬編碼掃描，改說明字修好，沒動歸類表）；build 0；442 招、78 場、census 都 different=0。

- 待決裁定：1 (o) 佇列結案，灰字用字轉玩法確認；2 validator 內檢查、測試用 `model_construct`：接受；3 `test` 用途留著：接受（量測工具要用）；4 注入情況的實機確認：等內容出現兩件變形或看目標修正技時補看，記佇列；5 `StartScreen` 顯示類型 ID：記佇列 (g) 一起問用字。
