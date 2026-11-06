# Phase 3H-5 報告｜耐力回復與 3-41c 小修

分支 `worktree-agent-a4dd5392c76769e63`。規格：`docs/phases/Phase3H計畫.md` 第 6 節；設計 07 7.2。

## 逐點做了什麼

1. **耐力回復**
   - `content/rules/core.yaml` 的 `resources.stamina_regen: 5`（模型 `ResourceRules.stamina_regen`，初值，平衡待辦 B15）：**主角**（`scaled_resources` 的範本）每回合開始回復 5 點、不超過上限；敵人、隊友、召喚物不回復（敵我同一套仍是 B14）。引擎：`UnitState.stamina_regen`（`make_unit` 由 `CoreRules.template_stamina_regen` 設定）、`start_turn` 在發出 `turn_started` 之前回復；`TurnStarted` 多了 `stamina`／`max_stamina`／`stamina_gained`；戰鬥紀錄文字「耐力 +5（13/48）」。
   - 戰後回滿：`content/roguelite.yaml` 的 `refill_after_battle: [stamina]`（只開耐力；法力維持只在營火回滿）。輸掉時照舊不回滿。
   - 說明文字全由資料產生：耐力名詞卡（`narrative/action_info.py`，`action_texts(core, refill_after_battle)`，`/api/glossary` 傳入）、一輪的資源規則句（`resource_rule_text`）；營火畫面「HP、法力與耐力已回滿」。
   - **`LOG_FORMAT` `/60` → `/61`**（`runner.py` 文件字串、`tests/cli` 六檔、`test_gear_g2/g3a`、`test_24c` 的 `/60` 一併改）。`swamp` 種子 60 重播一致；存檔 `trpg-run/5` 不變（沒有新存檔欄位）。
2. **「目前加成」整數**：新模組 `trpg/shared/bonus_text.py`（`bonus_text(value, permille)`、`plain_text`）：主文「目前 +4」（向下捨去）；帶小數時那一段寫成 `⟦目前 +4｜實際 4.2，和其他加成合計後才捨去⟧`（整數時不加標記）。武器普攻算法（`WeaponDef.attack_formula_zh`）與技能傷害／治療／護盾算法（`SkillDef.formula_lines_zh`）改用它。前端 `ui/ruleText.tsx`（`RuleText`、`plainRule`）把標記排成共用 `<Hint>`（外層是 `span.has-hint`，沒有用 `>` 直接子選擇器），套在技能卡的算法行、單位資訊的武器特性行、一輪面板的武器特性行。
3. **武器規則句**：雙屬性行改為「雙屬性：普攻吃敏捷、力量，取較高者；武器技看技能卡（在這把武器的屬性範圍內）」。屬性配點旁的「影響：…」清單原本寫「〇〇的普攻與武器技」，同樣不準，改成「〇〇的普攻」（武器技若縮放該屬性本來就會以技能名列在後面）。規則不變。
4. **召喚物小卡灌注 HP**：`SummonInfoCard.hp_infusion_zh`（`narrative/summon_info.py hp_infusion_text`），由 `summon_infusions` 中 `hp_permille` 不為 0 的灌注逐個產生「選「召喚物」灌注時 HP +20%」，之後有別的灌注動 HP 會自動多列（有測試加一個假灌注）；顯示的 HP 仍是預設值。前端在 HP 列下多顯示一行。
5. **升級配點與營火重配預覽改後端算**：新端點 `POST /api/runs/{run_id}/allocation-preview`（`{attributes}` → `{hp, mana, stamina, summary_zh}`，例「最大 HP ＋3、耐力 ＋2」），用 `RunState.max_*_in`（和一輪面板同一組函式）。前端 `run/allocationPreview.ts`（hook）＋ `AttributeAllocator` 新 `preview` 屬性；拿掉前端公式 `conHpGain` 與 `hpPerCon`（RunNewScreen 本來就有後端算的開局預覽）。升級畫面、營火重配、進度畫面的重配區都接上。OpenAPI、`schema.d.ts` 已重產。

## LOG_FORMAT 與重播

`trpg-battle-log/61`；`trpg battle --map swamp --seed 60 --log-json` ＋ `replay`：87 個動作、272 個事件，最終狀態一致。CLI 快照以 `UPDATE_CLI_SNAPSHOTS=1` 重跑，無變動；前端快照（glossary、unitDolls、skill_icons）重產，除耐力名詞卡外無變動。

## 資源不足回合比例：新舊對照（只量、不調）

同 3H-2：`scripts/sim_resources.py --seeds 20 --jobs 8`（同一組情境、每格 20 場、開戰資源全滿；英雄每回合開始（`turn_started` 之後，已含回復）檢查）。舊 ＝ 本段開工前同一份程式重跑（與 3H-2 報告完全相同），新 ＝ 每回合 +5。單位：資源不足回合比例（任一不足）／耐力不足／剩餘耐力。

| 情境 | build | 勝率 舊→新 | 耐力不足 舊→新 | 任一不足 舊→新 | 剩餘耐力 舊→新 |
|---|---|---|---|---|---|
| 長戰單體 | 技能流弓手 | 90→90% | 7→0% | 7→0% | 29→63% |
| 長戰單體 | 普攻流弓手 | 80→80% | 5→0% | 5→0% | 26→51% |
| 長戰單體 | 召喚師 | 100→100% | 0→0% | 2→2% | 99→99% |
| 長戰單體 | 近戰推擊流（位移流） | 75→75% | 34→10% | 35→25% | 8→23% |
| 範圍戰 | 技能流弓手 | 100→100% | 3→0% | 3→0% | 28→50% |
| 範圍戰 | 普攻流弓手 | 95→95% | 2→0% | 2→0% | 36→55% |
| 範圍戰 | 召喚師 | 95→95% | 0→0% | 0→0% | 66→82% |
| 範圍戰 | 近戰推擊流 | 100→100% | 11→0% | 13→1% | 25→40% |
| Boss 戰 | 技能流弓手 | 40→35% | 27→0% | 28→17% | 27→67% |
| Boss 戰 | 普攻流弓手 | 45→40% | 11→0% | 11→0% | 42→73% |
| Boss 戰 | 召喚師 | 55→60% | 0→0% | 34→38% | 75→94% |
| Boss 戰 | 近戰推擊流 | 15→10% | 54→4% | 56→26% | 27→50% |

觀察（不調）：
- 耐力不足幾乎消失（最高剩 10%、Boss 戰近戰 4%）。每回合 +5 對武器技（6～12）加格擋（10）的支出已很寬鬆；瓶頸移到法力（近戰推擊流長戰 24%、Boss 24%，弓手 Boss 17%，召喚師 Boss 38% 都是法力不足，法力只有營火回滿）。
- 這個量法每場開戰全滿、單場內評估；一輪中的跨場影響現在由「戰後回滿」處理，所以單場數字就是一輪每場的狀況。
- 勝率差異（±5%、每格 20 場）在雜訊內；沒有為了勝率調任何數值。

## 實機（內建瀏覽器，8012，1600×900）

開發包（單手劍）＋存檔改耐力 3：一輪面板耐力 3／48；打第 1 場：耐力每回合開始 +5（8→13，戰鬥紀錄「耐力 +5（13/48）」，HUD 耐力條同步）；打贏後耐力 48／48、HP 25／63 不回（法力不變）。一輪的規則句「每場打贏後耐力回滿；戰鬥中主角的耐力每回合開始回復 5 點；HP、法力不會在戰鬥之間回復，只有營火會回滿（第 3 場、第 5 場之後）」。角色面板武器行「普攻：1d8＋力量 × 0.3（目前 +4）」，滑過「目前 +4」出現說明卡「實際 4.2，和其他加成合計後才捨去」；雙屬性武器句與「影響：單手劍的普攻」。升級三選一的召喚石像小卡 HP 列下有「選「召喚物」灌注時 HP +20%」。升級配點：體質 +1、力量 +1 → 「配點後：最大 HP ＋3、耐力 ＋2」（後端算）。未實機：營火畫面的重配預覽（和升級畫面同一個 hook 與端點，有 API 測試與前端渲染測試）、技能卡算法行的說明卡（與武器行同一個元件，有渲染測試）。伺服器（PID 5924）已關、視窗已還原、測試存檔已刪。

## 檢查結果

ruff check／format、mypy（src、tests）、lint-imports 通過；pytest `tests/engine`、`roguelite`、`content`、`narrative`、`api`、`cli`、`sim`、`skillgen`、`llm`、`shared`、`test_architecture` 全過（一次 `-n 8` 合併跑時 `tests/engine` 4 個召喚物 HP 測試又失敗，單獨重跑 94 個全過——就是開發 PM 交接檔記的「待查」那個既有的偶發問題，與本段無關）；前端 typecheck、vitest 880、`pnpm build` 通過。新測試：`tests/engine/test_dual_resources.py`（回復上限、只有主角）、`tests/roguelite/test_stamina_run.py`（戰後回滿耐力不回滿法力、設定點可關；改成找到打贏的種子才有意義）、`tests/narrative/test_stamina_text.py`、`test_bonus_text.py`、`test_summon_hp_infusion.py`、`tests/api/test_allocation_preview.py`、前端 `ui/ruleText.test.ts`、`hpPreview.test.ts`（改測後端預覽字串）。

## 執行上的備註

- 這個環境的 `python` 是 Windows Store 假指令，改檔腳本要用 `uv run python`（我一開始的幾次改檔沒生效，已重做並由測試確認）。
- 檔案行尾有 CRLF 警告（既有狀況）。

## noqa

新增兩處測試內的局部匯入／fixture 重用：`tests/api/test_allocation_preview.py` 的 `# noqa: F401`、`F811`（重用 `test_runs_api` 的 fixture）。src 沒有新增 noqa。

## 待 PM 決定

1. **標記語法 `⟦顯示字｜說明⟧` 放在規則句字串裡**：好處是武器、技能卡、單位資訊三處的字串結構不用動；代價是純文字呈現處（目前 CLI 沒有用到這些句子）要用 `plain_text`。若偏好結構化欄位（每行多一個 `hint`），可再改。
2. **「影響：〇〇的普攻與武器技」我也改成「的普攻」**（屬性配點區），規格只提武器規則句；若要保留原樣請告知。
3. 耐力回復後，耐力幾乎不再是瓶頸（見上表），法力成為新的短板（只有營火回滿）；是否要給法力回復，與使用者待決的「每場法力回滿」一起考慮（平衡待辦 B15）。
4. 戰鬥紀錄文字只在有回復時才顯示「耐力 +5（x/y）」（已滿不顯示），避免每回合洗版；要不要總是顯示可再調。
5. 營火文字改成「HP、法力與耐力已回滿」（原本只寫 HP 與法力，3H-2 漏改）。
