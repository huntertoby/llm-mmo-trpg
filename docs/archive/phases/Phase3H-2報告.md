# Phase 3H-2 報告｜雙資源（武器技花耐力）

分支 `worktree-agent-af3944cbb22768e49`。規格：`docs/phases/Phase3H計畫.md` 第 0、2 節；設計 07 7.2（法力與耐力上限）、7.3（資源）、06 6.10（武器技花耐力、法術技花法力）。

## 做了什麼

1. **資源上限**（`content/rules/core.yaml` 的 `resources`，模型 `ResourceRules`）：上限 ＝ 基礎 ＋（該組屬性最高者 − 10）× 2，法力看智力／感知／意志，耐力看力量／敏捷／體質（係數、屬性組、基準都是資料）。**只套用在主角**：`UnitTemplate.scaled_resources`（一輪的主角、build 英雄為 `True`；敵人、隊友、召喚物照範本固定值，避免改到敵方平衡）。基礎：法力 ＝ `start.heroes` 的 `max_mana`（依武器大類）；耐力 ＝ 新欄位 `start.heroes.*.stamina`（三大類都填 30，省略時 `default_stamina`）。引擎在 `make_unit` 用含裝備屬性的範本算（`CoreRules.template_max_resource`），一輪的面板用 `RunState.max_mana_in`／`max_stamina_in`（不含裝備，同最大 HP 的做法）。
2. **費用**：`SkillCost.stamina`（新欄位）。武器技花耐力、法術技花法力，規則是資料（`skill_budget.yaml` 的 `cost_resource: {weapon: stamina, spell: mana}`）；內容庫載入（`_check_skills`）與驗證器（`cap.resource`）都檢查「花錯資源」。引擎：`pay_skill_cost` 扣耐力、`resource_problem` 回「耐力不足：需要 N，剩餘 M」（施放、`legal_actions`、預覽、灰掉原因共用）；`skill_used`／`skill_triggered`／`skill_infused` 多 `stamina`／`stamina_after`；反應技的暫停資料帶 `stamina_cost`。
3. **預算**：`allowance.stamina_per_mana: 2`（耐力 2 點 ＝ 法力 1 點，預算點數等價）：耐力折抵 ＝ 耐力 × `mana_per_point` ÷ 2，上限同 `mana_cap`。
4. **內建技能**：73 招武器技中 62 招「耐力 ＝ 原法力 × 2」（6／8／10／12），11 招原本就 0（8 個檔案的 `mana: 0` 拿掉）。法術技不動。
5. **產生器**：隨機組合器內部仍以法力計數值（調強度時不用改），`_finish` 依類別換成等價耐力（`BudgetRules.resource_cost`）；LLM 提議本來就不帶法力數字，`COST_NUMBER_FIELDS` 加 `stamina`（拆數值、補數值時一起處理）；工作坊的代價欄位依類別顯示「耐力」或「法力」並說明換算；傳說（`composer_special`）都是法術技，不受影響。
6. **AI**：`AiWeights.stamina_permille`（每點耐力的機會成本 ‰）；`ai_profiles.yaml` 原本有 `mana: 1` 的 6 個模式都加 `stamina_permille: 500`，和原本的法力代價等價。召喚物灌注的假想狀態補耐力。格擋的「耐力低於 20 不格擋」規則照舊，和武器技共用同一個池。
7. **一輪與存檔**：`RunState.stamina`（`None` ＝ 滿，舊存檔讀進來就是滿）；戰鬥之間不回復、營火回滿；`BattleRecord.stamina`；升級加屬性使上限變動時，目前法力／耐力同步增減（同 HP 的做法）。**`trpg-run/5` 不升**：新欄位都有預設值，舊存檔可讀（有測試）。
8. **「每場法力回滿」設定點（不開）**：`roguelite.yaml` 的 `refill_after_battle: []`，列 `mana`／`stamina` 就在每場打贏後回滿（引擎與說明文字都已接上，有測試）。
9. **介面**：一輪面板加耐力條；戰鬥 HUD 本來就有耐力條；技能卡費用顯示「耐力 N」（由 `cost_parts` 產生）；耐力不足灰掉，點了顯示「破城衝撞不能用：耐力不足：需要 8，剩餘 5」；工作坊試玩在耐力上限不夠時提醒；「戰鬥之間不回復」說明改成 HP、法力、耐力（依 `refill_after_battle` 產生）；耐力名詞卡更新。
10. **模擬**：`trpg.sim.resource_report` ＋ `scripts/sim_resources.py`（見下）。

### 費用欄位做法與理由

選 **加 `cost.stamina`**，不選「依類別解讀 `mana`」：
- 資料自己說清楚花什麼（卡片、紀錄、LLM、工作坊都不用再查類別才知道意思）；
- 換算比例可以不是 1:1（耐力池比法力池大，又和格擋共用；用 1:1 會讓武器技相對變便宜）；
- 舊存檔裡的生成武器技（`cost.mana`）照樣能讀、照樣花法力（引擎只照欄位扣），不需要遷移；新產生的一律檢查。

### 預算換算

`stamina_per_mana: 2`。理由：近戰主角原本 20 法力、武器技 3～6 法力 → 約 4 次；現在耐力 30＋（主屬性 14 時 +8）＝ 38、武器技 6～12 → 約 4 次，次數大致不變；格擋 10 耐力和武器技同一量級。

### 217 招重算結果

表格測試 `tests/skillgen/test_stamina_cost.py`：217 招每招都花對資源、通過驗證（含預算區間）；62 招花耐力的武器技，「耐力換回等價法力」重算後折抵與比例**完全相同**。比例範圍不變（一般技能 70%～99.7%；裝備給的技能本來就不檢查區間）。

## LOG_FORMAT 與重播

`trpg-battle-log/59` → `/60`（`runner.py` 文件字串、8 個測試檔）。`swamp` 種子 60 重播一致；新的 build 英雄戰鬥重播測試也通過。

## 模擬報表（只量、不調）

`uv run python scripts/sim_resources.py --seeds 20 --jobs 8`（每格 20 場；英雄每回合開始時檢查裝備的主動技能，至少一招因法力／耐力不足不能用就算一回合；每場開戰資源全滿）：

| 情境 | build | 勝率 | 英雄回合 | 法力不足 | 耐力不足 | 任一不足 | 剩餘法力 | 剩餘耐力 |
|---|---|---|---|---|---|---|---|---|
| 長戰單體 | 技能流弓手 | 90% | 115 | 0% | 7% | 7% | 72% | 29% |
| 長戰單體 | 普攻流弓手 | 80% | 87 | 0% | 5% | 5% | 100% | 26% |
| 長戰單體 | 召喚師 | 100% | 84 | 2% | 0% | 2% | 27% | 99% |
| 長戰單體 | 位移流（近戰技能流） | 75% | 143 | 17% | 34% | 35% | 6% | 8% |
| 範圍戰 | 技能流弓手 | 100% | 61 | 0% | 3% | 3% | 80% | 28% |
| 範圍戰 | 普攻流弓手 | 95% | 56 | 0% | 2% | 2% | 100% | 36% |
| 範圍戰 | 召喚師 | 95% | 58 | 0% | 0% | 0% | 58% | 66% |
| 範圍戰 | 位移流（近戰技能流） | 100% | 71 | 3% | 11% | 13% | 50% | 25% |
| Boss 戰 | 技能流弓手 | 40% | 128 | 12% | 27% | 28% | 48% | 27% |
| Boss 戰 | 普攻流弓手 | 45% | 96 | 0% | 11% | 11% | 100% | 42% |
| Boss 戰 | 召喚師 | 55% | 140 | 34% | 0% | 34% | 7% | 75% |
| Boss 戰 | 位移流（近戰技能流） | 15% | 147 | 24% | 54% | 56% | 56% | 27% |

觀察（不調）：
- 武器技流（弓、近戰）的瓶頸換成耐力；近戰技能流在長戰與 Boss 戰有 34～54% 的回合缺耐力（格擋也在吃同一個池），弓手 Boss 戰 27%。
- 召喚流只缺法力，Boss 戰 34%；耐力幾乎沒用到（法系主角的耐力基本閒置）。
- 普攻流有少量武器技，Boss 戰 11% 缺耐力；剩餘耐力 26～42% 多半是被格擋吃掉。
- 這是「單場開戰全滿」的量法；一輪中耐力和法力一樣跨場不回復，實際缺得更兇，尤其近戰（格擋＋武器技）。沒有跑改動前的基線。

## 測試

新增：`tests/engine/test_dual_resources.py`（武器技扣耐力不扣法力、耐力不足時合法動作／施放／預覽／灰掉原因一致、法力不足同理且耐力無助、格擋與武器技共用池、上限公式、非主角固定值、重播一致）、`tests/skillgen/test_stamina_cost.py`（217 招表格、折抵等價、`cap.resource`、組合器）、`tests/roguelite/test_stamina_run.py`（開局滿、跨場帶入、營火回滿、`refill_after_battle`、加屬性同步、存檔往返與舊存檔）、`tests/sim/test_resource_report.py`、前端 `workshop.test.ts` 耐力提醒。

既有測試調整：測試技能基準（`helpers.py`）改花耐力 8；武器技測試草稿 `mana` → `stamina`（工作坊、預算 CLI）；`run.max_mana` → `max_mana_in(core)`；AI 軌跡改變重選種子：`test_basic_actions_cli`（222 → 98）、`test_striker_trapper_battle`（69 → 49）；`test_delayed_followup` 的蓄力斬條件改看耐力。

## 檢查結果

ruff check／format、mypy（src）、import-linter 通過；`pytest tests/engine roguelite cli api content narrative skillgen sim llm test_architecture`：5693 通過；前端 typecheck、vitest 863、`pnpm build` 通過；`trpg content check` 通過；`swamp` 種子 60 重播一致；OpenAPI、`schema.d.ts`、`glossary.json` 已重產（`skill_icons.json`、`unitDolls.json` 無變動；CLI 快照重產無變動）。實機（8012，內建瀏覽器）：一輪面板耐力 38/38（力量 14）、存檔改成 5 後讀回 5/38；戰鬥 HUD 耐力條、技能卡「AP 2・耐力 8・冷卻 3」、點灰掉的破城衝撞顯示「耐力不足：需要 8，剩餘 5」。伺服器已關、視窗已還原。

## noqa

無新增。

## 待 PM 決定

1. **耐力在一輪中跨場不回復**（照規格「營火回滿」）：近戰的格擋＋武器技共用池，模擬單場已有 34～54% 回合缺耐力，跨場會更缺。要不要另給「每場耐力回滿」或戰後回一部分？（`refill_after_battle` 已可設定。）
2. **「技巧動作」（推擊、絆倒）目前本來就不花耐力**，所以「照舊扣耐力」只有格擋；要不要讓技巧動作花耐力？
3. 換算 `stamina_per_mana: 2`、主角耐力基礎 30（三大類相同）是初值；法系主角耐力幾乎閒置，要不要依武器大類給不同基礎？
4. 資源上限公式只套主角（`scaled_resources`）；敵人、隊友維持固定值。要不要敵我同一公式（同最大 HP）？會動到敵方平衡。
5. 舊存檔裡已生成的武器技仍是 `cost.mana`（照花法力，不遷移）；可接受嗎？
6. 開局畫面的「法力」預覽仍是基礎值、沒顯示耐力與配點加成（3H-3 的建議屬性／面板一起做較合適）。
