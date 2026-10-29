# Phase 3W-5b 完成報告

> 實作者報告。範圍：玩法 PM 1752ae6c（06 6.34.6「沒有一般數值可調的結構」）與 3W-5 報告第 6 節第 2、8 點。
> 分支：`worktree-agent-ac79968531f4257be`（從 `main` 的 1752ae6c 快轉後開工）。

## 1. Commit 列表

| Commit | 內容 |
|---|---|
| `ad045433` | refactor: remove engine skill levels (LOG_FORMAT /89, save /13) |
| `d7f0a23b` | feat: complete skills really gain +120 (summon power, stance magnitude, cost cuts) |
| （本報告） | docs: 3W-5b report |

## 2. 第 1 點：完整技能 +120‰ 要實際加上去

### 2.1 做法（`src/trpg/skillgen/complete.py`）

- `complete_strength(library, skill)`：預算分數（`complete_power`）至少要是原本的 ×1.12。
  - `complete_power`＝總點數 ÷（AP／觸發係數 ×（1000＋代價折抵）÷1000）。
  - 和 `budget_power` 一樣，只是把代價折抵也換算掉（姿態本來就這樣算），所以「代價變便宜」也算變強。
  - 只改效果數值時，兩者的比例相同。
- 從原本的數值 **只往上加、一次一格**（數字不會變小），每一步都要通過 `validate_skill`。
  - 「過弱」不擋中間步驟：上限加了 120‰，原數值換算成新比例一定偏低；加到目標時比例就回到原本的水準。
  - 依序試三組，前一組加不動才換下一組：
    1. **數值旋鈕**：預算器原有的旋鈕（傷害、治療、護盾的骰子或倍率、推拉、修正幅度、接續段）。
       - 召喚：`power_permille`，乘上 `summon_power_steps`，加的是召喚物 HP 與傷害。
       - 姿態：`apply_status.magnitude_permille`，乘上 `stance_magnitude_steps`。
    2. **效果參數旋鈕**：狀態、表面的持續回合等，和升階重配用的 `param_knobs` 相同。
    3. **減代價**：依 `cost_cuts` 的順序（維持費 → 冷卻 → 法力 → 耐力 → AP）一次減一格，每項最少留 1。
  - 同一組裡有一步就達標的選項時，取超出最少的；沒有時取分數加最多的。
  - 三組都加不動時，停在目前最強的版本（「達到上限」），由 `_next_step(...) is None` 判定。
- 資料驅動：階梯與減代價的順序放在 `content/flash_templates.yaml` 的 `complete`（`CompleteSkillRules.summon_power_steps／stance_magnitude_steps／cost_cuts`）。程式裡沒有寫死技能 ID，也不用亂數。
- `roguelite/offers.as_complete(library, skill)` 改成呼叫它。因為已經不用亂數，拿掉了 `seed` 參數。

### 2.2 引擎與內容

- **姿態幅度**：
  - 欄位：`EffectSpec.magnitude_permille`（只有姿態技能的 `apply_status` 能填，值 ≥1000），對應的 `ApplyStatusEffect.magnitude_permille` 與 `StatusInstance.magnitude_permille`。
  - 結算：在 `rules/statuses._combined` 經過 `scaled_permille` 放大。**只放大對持有者有利的一邊**，例如受到的傷害 700 → 640；堅守姿態的移動減半是代價，不放大。
  - 預算：狀態點數 × 幅度 ÷1000。
- **召喚強度**：只召喚一隻時，現在可以帶 ≥1000 的 `power_permille`（以前只有數量型能填 <1000）。
  - 引擎原本就會把它乘在 HP 與傷害上。
  - 預算：點數照比例相乘。
  - `skill_primitives.yaml` 的上限從 999 改成 2000。

### 2.3 卡片數字＝實戰

- 姿態卡：寫「幅度強化 ×120%：自己造成的火焰傷害 ×118%」。數值句用和結算同一個函式算（`scaled_status_def`）。
- 召喚卡：寫「召喚物的 HP 與傷害 ×112.4%」，普攻句寫「傷害 ×112.4%」。
  - HP：1 級基準值與實際值兩條路徑都已經乘上強度。

### 2.4 驗收證據

- `tests/skillgen/test_complete_3w5b.py`（15 項）：

  | 結構 | 例子 | 結果 |
  |---|---|---|
  | 傷害 | `skill_fire_bolt` | ≥ +120‰ |
  | 陷阱 | `skill_bear_trap`、`skill_cinder_mine` | ≥ +120‰ |
  | 被動 | `skill_bloodlust` | ≥ +120‰ |
  | 反應 | `skill_riposte`、`skill_counterspell` | ≥ +120‰ |
  | 召喚 | `skill_summon_fire_spirit` | `power_permille` 1124，≥ +120‰ |
  | 姿態 | `skill_bulwark_stance`、`skill_fury_stance` | `magnitude_permille` 1124，≥ +120‰ |
  | 沒有數值旋鈕 | `skill_rune_burst` | 冷卻 3→1、法力 8→2，+122‰ |
  | 達到上限並記錄 | `skill_rune_breaker`（修正型，沒有幅度也沒有代價） | 0‰，再也加不動 |
  | 達到上限並記錄 | `skill_thorn_skin`（骰子再大一格就超出預算） | +100‰，再也加不動 |
  | 達到上限並記錄 | `skill_quake_topple`（代價都減到 1） | +112‰，再也加不動 |

- `tests/engine/test_complete_strength_3w5b.py`（4 項）：
  - `scaled_permille` 的各種情況。
  - 姿態施放後，狀態實例帶著幅度；`damage_dealt_permille` 的值是 1180，卡片上也是 ×118%。
  - 防守姿態的代價不放大。
  - 完整召喚實際召喚出來的 HP＝實際值卡片的 HP，也等於原本的 HP × 強度。
- 內建技能全部試算一次（臨時腳本，不進版控；形態技能除外），達到 +120‰ 的數量：

  | 種類 | 達到 +120‰ ／ 總數 |
  |---|---|
  | 召喚 | 17／17 |
  | 姿態 | 2／2 |
  | 陷阱 | 3／3 |
  | 反應 | 7／8 |
  | 被動 | 10／16 |
  | 主動 | 161／227 |
  | 修正 | 5／18 |

  - 沒達到的大多是三類：
    - 沒有數值旋鈕的工具技能：代價都減到 1 還差一點，多在 +100～119‰。
    - 只有源力代價的技能：`cost_cuts` 沒有源力。
    - 沒有幅度、也沒有代價的修正型被動。

## 3. 第 2 點：移除引擎裡的技能等級

- 刪除的檔案：
  - `engine/skill_levels.py`；其中 `grow_shape` 搬到新的 `engine/shape_growth.py`，修正規則與閃現仍在用。
  - `content/skill_growth.py`、`content/skill_growth.yaml`。
  - `tests/engine/test_skill_levels.py`、`tests/content/test_skill_growth_content.py`。
- 移除的欄位與用途：
  - 單位範本 `UnitTemplate.skill_levels`，與它的兩個驗證器。
  - 單位狀態 `UnitState.skill_levels`，與它的複製。
  - 灌注快照 `InfusedSkill.skill_level`，以及灌注借用、AI 灌注時的等級。
  - 規則包 `Ruleset.skill_growth`。
  - 施放時的 `Cast.level_permille`、`level_multiplier`，以及 5 級小特性（`leveled_skill`）。
  - API 的 `UnitView.skill_levels`。
  - 前端：`SkillBar` 的 `levels`、`Lv.N` 徽章與 `.skill-lv` 樣式，以及 `BattleBottomBar` 與測試夾具裡的欄位。
- 測試：
  - 刪掉測等級的測試（`test_variants` 的等級例子）。
  - 名稱裡有 `skill_level` 但其實是「技能整體條件」的測試改名。
- **戰鬥紀錄 `LOG_FORMAT` /88 → /89**：
  - `docs/phases/戰鬥紀錄格式變更.md` 加了一條，同時記錄姿態幅度與單隻召喚強度。
  - 用 `git grep` 更新了 `battle-log/88` 與 `endswith("/88")` 的全部字面值。
  - 舊紀錄的讀取相容：`trpg battle replay` 改成在解析之前先看 `format`（`runner.log_format_problem`）。
    - 所以 `/88` 紀錄裡多出的 `skill_levels` 不會變成「不是有效的戰鬥紀錄」，而是照文件 1.5 說明「舊格式的紀錄無法重播」。
    - 有新測試：`tests/cli/test_battle_cli.py`。
- **存檔 `trpg-run/12` → `/13`**：
  - `/12` 的 `run.hero` 還帶 `skill_levels`；新加的 `convert_raw_hero` 讀入時會拿掉它（`/5`～`/12` 都會經過）。
  - 有新測試：`tests/roguelite/test_save.py::test_run_12_saves_drop_the_hero_skill_levels`。
  - 存檔版號的字面值全部更新。
- 重新產生的檔案：
  - `export_openapi.py` → `gen:api`。
  - `export_client_fixtures.py`：內容沒有變。
  - `icon_fixture`：第 1 點新增欄位後，兩個修正型技能的序列化多了 `magnitude_permille: null`。
- `git grep -i "skill_level\|skill_growth"`（不含 docs）只剩讀取相容與它們的測試：
  - `roguelite/save.py`：轉換 `/11` 以前的 `run.skill_levels`，以及 `/12` 的 `run.hero.skill_levels`；模組說明裡也有歷史描述。
  - `runner.log_format_problem` 的說明。
  - `tests/roguelite/test_flash_llm_run.py`（`/11` 轉換）、`tests/roguelite/test_save.py`（`/12` 轉換）、`tests/cli/test_battle_cli.py`（`/88` 紀錄）。

## 4. 收尾檢查

- `ruff check`、`ruff format --check`、`mypy`（808 檔）、`lint-imports`（7 條契約）：全部通過。
- pytest，加上 `-m "(slow or not slow) and not llm" -n 8`：

  | 範圍 | 結果 |
  |---|---|
  | engine、content、narrative、skillgen | 8529 通過（3 xfail、1 xpass 是原本就有的平衡標記） |
  | roguelite、api、llm、sim | 809 通過 |
  | cli（`--timeout=3000`）＋ architecture | 163 通過；CLI 快照沒有變，沒用 `UPDATE_CLI_SNAPSHOTS` |

- 前端：`tsc --noEmit` 通過、vitest 119 個檔案 1148 項通過、`build` 通過。
- swamp 種子 7 重播：「重播驗證通過：60 個動作、223 個事件，最終狀態一致」。

## 5. 待 PM 決定

1. **姿態幅度只放大有利的一邊**：
   - 「姿態的幅度（傷害 +X% 的 X）」沒有說代價（例如堅守姿態的移動減半）要不要跟著放大。
   - 採保守做法：代價不放大。預算仍是「點數 × 幅度」，所以實際的強化略多於帳面。
2. **減代價只減不拿掉**：設計寫「減費用、維持費或冷卻」。
   - 採保守做法：每項最少留 1，例如冷卻不會變成沒有冷卻。
   - 步長 1、順序是維持費 → 冷卻 → 法力 → 耐力 → AP，都可以在 `flash_templates.yaml` 改。
   - 源力不在清單裡。
3. **加不到 +120‰ 的技能停在上限**。
   - 主要是三類：沒有數值的工具技能、沒有代價的被動、修正型被動。
   - 「記錄」目前只是測試與本報告的數字（第 2.4 節），沒有寫進存檔或卡片。要不要在卡片上標「已達上限」，請 PM 決定。
4. **一律從原數值往上加**：取代 3W-5 的「預算器整招重調」（以前會先把數值歸到最弱、再隨機抽目標）。
   - 好處：數字只增不減，玩家看得出變強。
   - 代價：骰子階梯粗的技能可能超出目標不少。例如 `skill_fire_bolt` 是 +166‰，因為下一格骰子就跳這麼多。
5. **單隻召喚可以填 `power_permille` ≥1000**：這是為完整技能開的口。
   - LLM 提示與工坊仍然只在 `count: 2` 時顯示這個欄位（`show_when` 沒改）。
   - 新參數 `apply_status.magnitude_permille` 的工坊玩家說明是實作者寫的初稿（`workshop_text.yaml`），待玩法 PM 改寫。
6. **`/88` 戰鬥中的存檔**：引擎版號變了，照既有規則拒絕重播。戰鬥之間的存檔照常讀，`/12` 會自動轉成 `/13`。
