# Phase DD-1b 完成報告：雙匕首賭注自傷算兩下總和

> 依據：`docs/design/08-裝備.md` 8.11「雙匕首的武器技也打兩下」細節 6（玩法 PM 定，`dc2d44e9`）：賭注類「依造成的傷害算自傷」算 **兩下的總和**。對應 `PhaseDD-1報告.md` 待決第 7 項。其他 DD-1 行為不動。
> 起點：本機 main ff 合入後的 `05a0e8fa`（含 DD-1 `7596b74a`、`dc2d44e9`）。

## 1. 交付與 commit

| commit | 內容 |
|---|---|
| `5fa85715` | 引擎改動與測試 |
| `1d93994b` | 報告、上手筆記、DD-1 報告待決第 7 項加註 |
| （版號 commit） | `LOG_FORMAT` `/116` → `/117`、測試版號、戰鬥紀錄格式變更 `/117` 條目、本報告第 4、6 節 |

改動的程式（`src/trpg/engine/skills/cast.py`）：

- 新 `Cast.repeated_damage()`：從 `extra_strikes()` 抽出「要多打的傷害效果」判斷（`strikes > 1`、單一敵人、有對敵人的傷害效果），行為不變。
- `Cast.deferred_hit_backlash: list[EffectSpec] | None`：`run()` 在效果迴圈前，若 `repeated_damage()` 非空就設成 `[]`；此時 `resolve_branch()` 遇到 `self_damage_of_hit` 只記下、不結算。
- 新 `Cast.settle_deferred_hit_backlash()`：`extra_strikes()` 之後呼叫，以賭注擲骰後（`cast_start` 起）全部幾下對敵人的傷害總和結算記下的 `self_damage_of_hit`，再設回 `None`。
- 不多打的施放（非雙匕首、非單體、法術、被動、陷阱）`deferred_hit_backlash` 一直是 `None`，走原路徑，事件逐字不變。

## 2. 規則與測試（`tests/engine/test_dual_dagger_skills_dd1.py` 3b 節）

| 情形 | 自傷依據 | 測試 |
|---|---|---|
| 兩下都中 | 兩下總和（反噬在第二下之後才發） | `test_gamble_self_damage_uses_the_total_of_every_strike[兩下都中]` |
| 第一下中、第二下沒中 | 第一下 | 同上 `[第一下中、第二下沒中]` |
| 第一下沒中、第二下中 | 第二下（賭注在第二下才擲） | 同上 `[第一下沒中、第二下中]` |
| 第一下打倒、不打第二下 | 第一下 | 同上 `[第一下打倒…]` |
| 非雙匕首（單手劍） | 那一下 | `test_gamble_self_damage_without_dual_daggers_follows_the_single_hit` |

測試用 `lose_gambles` 把 `Rng.randint(1, 1000)` 固定成 1000（賭注失敗），`d20s` 只換 `Rng.roll`。確認過：把延後關掉時「兩下都中」那列會失敗，其他四列在舊行為下也成立（舊行為在那些情形本來就只算到一下）。

## 3. 不變比對

腳本在 scratchpad（未 commit：`cmp_dd1b.py`、`cmp_dd1b_detail.py`）：地圖預設陣容、效用 AI、`max_rounds=30`；改前 `05a0e8fa`（`git archive` 解出的 `src`，`PYTHONPATH` 指過去）、改後本段，每場比對整份戰鬥紀錄 JSON（事件、步驟、最終狀態含 `rng_state`）的 sha256。

- **不帶雙匕首**：8 張地圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12：`battles=46 events=20491 different=0`。
- **帶雙匕首**（`open_plain`、`bandit_lair` × 種子 1～10，我方第一人拿雙匕首、帶血祭重擊／雙牙／刃舞／`skill_ambush_stab`）：20 場中 10 場擲過賭注、其中 5 場賭輸；**3 場不同、17 場相同**。逐項：
  - `open_plain` 種子 5：兩下都中（3＋14）→ 反噬 1 → **8**（17 × 500‰）。之後我方英雄 HP 不同，戰局分岔（事件 304 → 290，勝方相同：我方）。
  - `open_plain` 種子 7、8：第一下中、第二下沒中 → 反噬金額不變（1），只是反噬事件從第二下的 `attack_rolled` 之前移到之後（事件順序變，金額與亂數取用不變；勝方相同）。
  - `bandit_lair` 種子 6：第一下沒中、第二下中 → 賭注在第二下才擲，反噬原本就在最後，逐字相同。
  - 其他賭贏（`win` 分支沒有自傷）或沒放血祭重擊的場次逐字相同。

## 4. 版號

- `LOG_FORMAT` `trpg-battle-log/116` → **`/117`**。`/116`（`98d2ffc9`）已在 origin/main：一開始的判斷沒先 `git fetch`，`git branch -r --contains` 看不到才誤判為未 push，開發 PM 指正後 fetch 確認。同版號下帶雙匕首、賭輸的紀錄重播結果會變（例：`open_plain` 種子 5 反噬 1 → 8），所以升版。
  - 同步：`runner.py` 的 `LOG_FORMAT` 與說明行；測試裡寫死的版號 11 檔 12 處（CLI 6 檔、`test_gear_g2.py`、`test_gear_g3a.py`、`test_wind.py`、`test_collided_sacrifice_firearm.py`、`test_self_costs.py`）；`docs/phases/戰鬥紀錄格式變更.md` 新增 `/117` 條目（原本補在 `/116` 的那句移過去）。
- `WORLD_RULES_VERSION` **不動**（26）：世界日誌的規則鍵 `log_rules_key()`（`world/save.py`）是 `LOG_FORMAT|w版號|規則包雜湊|內容 digest`，`LOG_FORMAT` 一升，舊世界日誌就已標成「規則已變、不能重播」；世界的程式、規則包雜湊、內容 digest 都沒變，不需要再加一。
- 規則包雜湊、內容 digest 不變（沒動 `content/`）。

## 5. 改到的測試

只新增（3b 節 5 個測試案例），沒有改舊測試、沒有換種子、沒有放寬斷言。CLI 快照 `tests/cli/test_output_snapshots.py -m slow` 24 passed，**沒有重產任何鍵**（快照裡的戰鬥沒有雙匕首）。

## 6. 檢查（結束碼）

| 指令 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0 |
| `lint-imports` | 0（14 kept） |
| 相關 pytest：`test_dual_dagger_skills_dd1.py`、`test_gamble.py`、`test_gamble_preview_ai.py`、`test_weapons_dual_dagger_firearm.py`、`test_determinism.py`、`test_skill_determinism.py`、`test_state_clone.py`、`test_pending_serialization.py`、`test_skill_preview.py`、`test_preview.py`、`test_reaction_skills.py`、`test_composite_followups.py`、`test_runner_advance.py`、`tests/test_architecture.py`；升版後再加版號所在的 11 檔、`test_ruleset_hash.py`、`tests/api/test_pr2a_range_practice.py`、`tests/world/test_opening_stages.py` | 0（升版前 242 passed；升版後 28 檔 687 passed） |
| `tests/cli/test_output_snapshots.py -m slow`（升版前、後各一次） | 0（24 passed，沒有重產） |
| 帶雙匕首一場紀錄＋`trpg battle replay`：`open_plain` 種子 5（含兩下都中的賭輸；升版後重產，`format` 為 `/117`） | 0、0（72 個動作、290 個事件，最終狀態一致）；舊的 `/116` 紀錄重播被拒並提示改版 |
| `trpg battle`＋`replay`：`oil_depot` 種子 13（升版後） | 0、0 |

沒有新增 `# noqa`（`Cast.__init__` 的 `PLR0915` 上限 50：新欄位的說明改寫成註解，不加敘述數）。沒跑完整 `scripts/check.py`、沒跑模擬、沒 push。

## 7. 待 PM 決定

1. **反噬的時間點**：多打時反噬在最後一下之後才結算（不在 `gamble` 效果的位置）。因此賭注分支裡若同時有 `self_damage_of_hit` 和其他效果，其他效果先、反噬後；目前唯一的賭注招血祭重擊的 `lose` 只有反噬一項，沒有實際差別。
2. **預覽與 AI**：預覽的賭注分支直接跑引擎，所以 AI 對雙匕首放血祭重擊的「賭輸」分支估值自動算兩下的反噬（預覽最多後果＝兩下都暴擊時反噬也最大）；沒有另改 `ai/gamble.py`。
