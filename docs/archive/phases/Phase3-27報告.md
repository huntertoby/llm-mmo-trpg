# Phase 3-27 完成報告：關鍵字池補齊第二批＋挑釁怒吼

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3計畫.md` 第 29 節、`docs/design/06-技能.md` 6.27.2。
> 分支：`worktree-agent-a2b53136f27900557`（從 main 的 `f8a1fa3` 分出），未 push、未合併。只動技能內容、測試與快照；沒有改引擎、一輪流程、技能等級、`styles.css`、API 型別，`LOG_FORMAT` 沒有遞增（沒有改引擎行為）。

## 1. 驗收逐條

| # | 規格 | 結果 | 證據 |
|---|---|---|---|
| 1 | 挑釁怒吼 AP 1、冷卻 2，標記縮成 1 回合；仍不過再縮嘲諷 1 回合 | 通過 | 標記縮成 1 回合後仍超預算（140.3%），再把嘲諷 2 → 1 回合後通過。AP 1、冷卻 2、`taunted` 1 回合、`marked` 1 回合。`tests/skillgen/test_pools_27.py::test_taunting_roar_is_ap_1_cooldown_2_and_still_marks`；`test_skill_shaping.py` 的紀錄文字改為「AP 1，冷卻 2 回合」 |
| 2 | 倒地補 3 招（條件「目標倒地中」） | 通過 | 踩踏 `trample`、倒地補刀 `ground_finish`、重壓 `gravity_crush` |
| 3 | 潮濕、標記、高處各補到 3 招 | 通過 | 潮濕：潮斬、漣射；標記：獵殺一擊、點射；高處：俯衝斬、下壓氣流 |
| 4 | 每招過預算、AI 會用、`icon_of` 有部件；附 10 池數量表 | 通過 | `test_every_new_skill_passes_validation_and_budget`（12 招逐一）、`test_the_bonus_only_applies_when_the_condition_holds`（條件成立才加碼）、`test_the_ai_scores_the_new_skill_best_when_the_condition_holds`（AI 預覽評分該招最高）；`tests/narrative/test_skill_icon.py`（每招有部件）與 vitest 全過；數量表見第 3 節 |
| — | 10 池各 ≥ 3（專屬、起始等級） | 通過 | `test_every_pool_has_three_exclusive_active_exploiters`（10 池，起始與全部主動各 ≥ 3） |
| — | `--log-json` ＋ `replay` 一致 | 通過 | `trpg battle --map lava_crossing --seed 14 --ally-build build_tank --log-json …` ＋ `battle replay`：139 個動作、373 個事件，最終狀態一致 |
| — | `check.py` 全過、`pnpm build` 成功 | 見第 7 節 | |

## 2. 新技能清單（12 招，全部 1 階、稀有、主動、過預算；數值為初值、未經模擬）

| 技能 | 武器 | 內容 | 池（專屬利用） |
|---|---|---|---|
| `skill_trample` 踩踏 | 近戰 | 1.0 倍；目標倒地再 +1.4 倍 | 倒地 |
| `skill_ground_finish` 倒地補刀 | 近戰（敏捷） | 1.0 倍；目標倒地再 +1.4 倍 | 倒地 |
| `skill_gravity_crush` 重壓 | 任何（法術） | 2d6 物理；倒地再 +2d8 | 倒地 |
| `skill_tide_cleave` 潮斬 | 近戰 | 1.0 倍；目標在水上再 +1.3 倍 | 潮濕 |
| `skill_ripple_shot` 漣射 | 遠程 | 1.0 倍；目標在水上再 +1.3 倍 | 潮濕 |
| `skill_hunters_strike` 獵殺一擊 | 近戰 | 1.0 倍；目標被標記再 +1.3 倍 | 標記 |
| `skill_pinpoint_shot` 點射 | 遠程 | 1.0 倍；目標被標記再 +1.3 倍 | 標記 |
| `skill_plunging_strike` 俯衝斬 | 近戰 | 1.0 倍；居高臨下再 +1.3 倍 | 高處 |
| `skill_downdraft` 下壓氣流 | 任何（法術） | 2d6 物理；居高臨下再 +2d8 | 高處 |
| `skill_pinning_shot` 趁亂釘射 | 遠程 | 1.0 倍；目標本回合受過撞擊再 +1.3 倍 | 撞擊（規格外補足） |
| `skill_veiled_shot` 隱匿射擊 | 遠程 | 1.0 倍；施放者隱蔽中再 +1.3 倍 | 隱蔽（規格外補足） |
| `skill_glacier_offering` 寒祭 | 任何（法術） | 獻祭召喚物，半徑 1 爆炸 2d8 冰（AP 1、法力 6、冷卻 3） | 召喚物（規格外補足）；同時製造冰凍 |

技能總數 181 → 193（`trpg skills budget --all` 的數字，測試與 CLI 快照同步）。每招都只靠既有條件的「條件成立時加碼」模板，沒有新原語。新技能沒有放進 `builds.yaml`，改用 `tests/content/test_coverage.py::_POOL_ONLY`（與 3-24c 相同）。

## 3. 10 個池「專屬規則下的主動利用者」數量表

「起始」＝1 階普通或稀有的主動技；「全部」＝所有階級的主動技。

| 關鍵字 | 起始 | 全部 | 名單（加粗＝本階段新增） |
|---|---|---|---|
| 點燃 | 4 | 7 | `flare_shot`、`kindle_pop`、`kindling_strike`、`scorching_slash`、`cinder_burst`、`detonate_burning`、`kindred_flame` |
| 潮濕 | 3（原 1） | 3 | `conductive_strike`、**`ripple_shot`**、**`tide_cleave`** |
| 帶電 | 3 | 5 | `arc_follow_up`、`rune_thunderbolt`、`spark_chain`、`chain_lightning`、`thunder_finisher` |
| 冰凍 | 4 | 4 | `frost_snap`、`icebreaker`、`shatter_ice`、`thaw_blast` |
| 倒地 | 3（原 0） | 3 | **`gravity_crush`**、**`ground_finish`**、**`trample`** |
| 撞擊 | 3（原 2） | 3 | `bone_pursuit`、**`pinning_shot`**、`shock_follow` |
| 標記 | 3（原 1） | 4 | **`hunters_strike`**、**`pinpoint_shot`**、`rune_thunderbolt`、`rune_burst` |
| 高處 | 3（原 1） | 3 | **`downdraft`**、`high_ground_shot`、**`plunging_strike`** |
| 隱蔽 | 3（原 2） | 3 | `shadow_ambush`、`shadow_backstab`、**`veiled_shot`** |
| 召喚物 | 3（原 2） | 3 | **`glacier_offering`**、`soul_burst`、`spirit_offering` |

## 4. 挑釁怒吼最後的數值

| | 3-24c 後 | 3-27 |
|---|---|---|
| AP | 2 | **1** |
| 冷卻 | 3 | **2** |
| 嘲諷 `taunted` | 2 回合 | **1 回合**（第二步退讓：只縮標記仍超預算 140.3%） |
| 標記 `marked` | 2 回合 | **1 回合** |
| 形狀 | 環形半徑 1 | 不變 |

## 5. 設計備註與設計取捨

- **沒有「倒地」的遠程利用者**：`statuses.yaml` 的倒地讓遠程攻擊有劣勢，遠程補射倒地者與機制相反（AI 也不會用），所以第一版的「伏地補射」改為近戰的「倒地補刀」。倒地池是 2 近戰＋1 法術。
- **規格只列倒地、潮濕、標記、高處，但目標是「10 個池各 ≥ 3」**：撞擊、隱蔽、召喚物在 3-24c 後仍只有 2 招，所以各補 1 招（趁亂釘射、隱匿射擊、寒祭）。
- **AI 測試的做法**：用 `UtilityAI.rank` 驗證「條件成立時，該招是不含瞄準的最高分動作」。完整 `UtilityAI.__call__` 在持法器或弓時會先選「瞄準」（瞄準分數隨最佳攻擊分數放大，屬於既有行為），所以不直接比較最終選擇；近戰持劍打倒地者時基本攻擊享有優勢，法術技則因此改用法器（雷電法杖）驗證。

## 6. 釘種子測試與快照的調整（逐項）

- `tests/cli/snapshots/cli_output_hashes.json`：重產（`UPDATE_CLI_SNAPSHOTS=1`；`skills_list`、`battle_bridge_guardian_11` 等因新技能與挑釁怒吼改變）。
- `tests/cli/test_budget_cli.py`：技能總數 181 → 193（兩處）。
- `tests/engine/test_skill_shaping.py`：挑釁怒吼的紀錄文字改為「AP 1，冷卻 2 回合」。
- `client/src/render/fixtures/skill_icons.json`：`uv run python -m tests.narrative.icon_fixture` 重產。
- `tests/content/test_coverage.py::_POOL_ONLY`：加入 12 招。
- 沒有需要換種子的測試。

## 7. 新增的複雜度 noqa

無（沒有改 `src/`）。

## 8. 最終檢查

- `ruff check`、`ruff format --check`、`mypy`（500 個檔案）：全過。
- 相關 pytest：`tests/content tests/skillgen tests/narrative tests/roguelite`（1409 passed 後修好圖示 fixture）、`tests/engine/test_taunt.py test_skill_shaping.py test_negative_statuses.py tests/cli tests/sim tests/api` 等（修完技能總數與快照後全過）。
- client：`pnpm -C client test` 61 檔 653 passed；`pnpm -C client build` 成功（只有既有的 chunk 大小警告）。
- 完整 `scripts/check.py`：見文末「check.py 結果」。

## 9. 待 PM 決定

1. **挑釁怒吼嘲諷縮成 1 回合**：只縮標記不夠（140%），照規格第二步把嘲諷縮到 1 回合。這削弱了坦克的控場時間（原 2 回合），影響 `build_tank`；`sim matrix` 沒有重跑，請平衡階段觀察。
2. **多補了撞擊、隱蔽、召喚物各 1 招**（規格只列倒地、潮濕、標記、高處），為了「10 個池各 ≥ 3」；若玩法 PM 不要，可刪除三個檔案，但池的驗收會失敗。
3. **倒地池沒有遠程利用者**（遠程打倒地者有劣勢）；若想要，需要玩法 PM 決定是否調整倒地規則或新增專屬的遠程機制。
4. **新技能數值**（1.3～1.4 倍、2d8）為過預算的初值，沒有模擬；新技能沒進 `builds.yaml`。
5. 「AI 會用」目前以預覽評分驗證，沒有跑整場 `sim matrix`／`sim keywords`。

## check.py 結果

完整 `scripts/check.py` 的前段全過（`ruff check`、`ruff format --check`、`mypy` 500 個檔案、`lint-imports` 6 個契約 KEPT）；平行 pytest 在 98% 附近卡住約 2 小時沒有進展（機器上另有 agent 同時跑全量，與 3-24c 報告記載的現象相同），沒有出現失敗；我手動中止，唯一的 `F` 是中止造成的 `node down`。因此改以分批結果為準：`tests/content tests/skillgen tests/narrative tests/roguelite` 全過、`tests/engine/test_taunt.py test_skill_shaping.py test_negative_statuses.py tests/cli tests/sim tests/api tests/test_sim_scripts.py tests/test_play_script.py` 修完技能總數與快照後全過，client vitest 653 passed、`pnpm build` 成功。**建議 PM 合併後在機器空閒時再跑一次完整 `check.py`。**

## Commit 列表

| commit | 內容 |
|---|---|
| `b914eb2` | 內容：12 招新技能、挑釁怒吼 AP 1／冷卻 2、圖示 fixture、測試 |
| （下一個） | 技能總數與 CLI 快照 |
| （本報告） | `docs/phases/Phase3-27報告.md` |
