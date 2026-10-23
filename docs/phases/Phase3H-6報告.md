# Phase 3H-6 報告｜武器技看手上武器的屬性

規格：`docs/phases/Phase3H計畫.md` 第 7 節（玩法決定 #45 字面執行）。分支 `worktree-agent-ad0bd2eb70deddd03`。

## 做了什麼

1. **引擎（共同入口）**：`SkillDef.scaling_value(get, weapon)` 對 `category: weapon` 且給了武器時改用 `WeaponDef.scaling_value`（雙屬性照 `attr_mode` 取較高／取平均）；`engine/skills/scaling.py` 的 `skill_scaling_value` 傳入 `unit.weapon`，傷害、命中（護盾與治療的屬性加成、擊倒、位移、狀態抵抗）、預覽、炸彈、召喚成長全部一起變。新增 `skill_scaling_attr`（對抗用的單一屬性；武器技為武器主屬性）與 `skill_scale_attr`（傷害紀錄顯示用）；`mastery_active` 對武器技改比「武器縮放值（基礎屬性）是否不低於自己最高屬性」。`attack_value`（武器技命中本來就用武器）不變。**`LOG_FORMAT` `/61` → `/62`**（`runner.py` 文件字串與測試的 `trpg-battle-log/N` 一起改）；`trpg battle --map swamp --seed 60` 紀錄重播一致（87 動作、272 事件）。
2. **工坊**：`FieldSpec.locked`（新欄位，後端選項帶出）。武器技的「縮放屬性」鎖成單一選項「看手上武器（力量／敏捷）」（依武器需求：近戰 → 力量、遠程 → 敏捷；還沒選武器需求時沒有選項），畫面唯讀顯示，`autoSingles` 會把草稿的值對齊成它；選項檢查（`field_problems`）不把鎖定欄位的舊值當玩家填錯。法術技與其他不變。
3. **產生器與驗證器**：`content/skill_scaling.yaml` 新增 `weapon_class_attrs: {melee: str, ranged: dex}`（載入時檢查是該大類某把武器的屬性）；`skillgen/scaling.py` 的 `fix_weapon_scaling`／`retarget_scaling`（武器技一律設為武器大類主屬性、拿掉第二屬性，不看主角屬性）；隨機組合器（亂數串流不變，近戰一律力量，武器技不抽第二屬性）、LLM 提議（`to_skill_def` 武器技即使沒有 `hero_attributes` 也一律修正）、保底（工坊選項推導）都接上；驗證器新增 `scaling.weapon`（只檢查產生的武器技：非內建、沒有 `parents`）。`skill_scaling.yaml` 與 `skillgen/scaling.py` 的「武器技看武器」說明同步。
4. **卡片與說明文字（程式依規則產生）**：武器技傷害算法「武器骰 1d8＋力量 × 0.3（目前 +3）」，雙屬性武器寫「敏捷／力量（取較高）」，一輪面板與戰鬥中依目前武器、「目前」值和引擎同一個函式；工坊、三選一（沒有武器）寫「武器骰＋武器的屬性 × 0.3」；卡片「縮放屬性」、專精說明、`scaling_attrs`（前端上色）、效果句裡的縮放簡稱（「武器屬性加成」「武器屬性對抗」）、屬性面板「影響哪些招」、建議屬性、自動配點（武器技算在武器的屬性上）、CLI `skills show --unit` 都跟著；武器規則句改回「雙屬性：普攻與武器技吃體質、力量，取平均」。
5. 前端：`FieldEditor` 鎖定欄位唯讀顯示（`.ws-locked`）、`autoSingles` 對齊；`openapi.json`、`schema.d.ts`、前端快照（glossary、unitDolls、skill_icons，無內容變動）、CLI 快照 hash 重產。

## 和武器不一致的內建武器技（引擎不再讀 `scaling_attr`，欄位只當顯示提示；逐招未改）

- 和武器大類主屬性（近戰 力量、遠程 敏捷）不一致的 **7 招**，全是近戰、提示屬性為敏捷：`skill_ambush_stab`（刺殺 build）、`skill_first_strike`（賭徒 build）、`skill_ground_finish`、`skill_pick_off`、`skill_pincer_strike`、`skill_shadow_ambush`、`skill_shadow_backstab`（以上四招多在刺殺 build）。清單由 `weapon_class_mismatches` 產生（測試只檢查格式，不擋載入）。
- 內建 build 英雄「武器」和其武器技提示屬性不一致：`build_assassin`（匕首 敏捷／力量取較高）：`skill_retreating_slash`、`skill_fury_stance`；`build_gambler`（單手劍 力量）：`skill_first_strike`。其他內建 build 都一致。

## 模擬（只量、不調；同 3H-2 情境，每格 20 場）

`scripts/sim_resources.py --seeds 20 --jobs 8`（新增「平均傷害」欄＝英雄一場造成的總傷害）。
- **改前改後 3H-2 原本四個流派（技能流弓手、普攻流弓手、召喚師、近戰推擊流）12 格：勝率、資源不足比例、平均傷害完全相同**——它們的武器技提示屬性本來就和武器一致，如預期不變。
- 提示屬性與武器不一致的 build 另跑對照（`build_assassin`、`build_gambler`；改前＝暫時讓武器技忽略武器，同種子）：勝率與平均傷害 刺殺 長戰 15%／50→15%／50、範圍戰 75%／26→75%／26、Boss 10%／14→10%／14；賭徒 長戰 45%／63→45%／63、範圍戰 95%／34→95%／30、Boss 5%／34→5%／33。差異在雜訊內，無異常。
- 說明：這個環境改前資料只能用「改前行為開關」重現，未保留舊 commit 的全量報表。

## 檢查

ruff check／format、mypy（654 檔）、lint-imports 過；`tests/engine`＋`content`＋`skillgen`＋`roguelite`＋`api`＋`narrative`＋`cli`＋`llm`＋`sim`＋`test_architecture` 5954 過（`test_openapi` 與一句護盾文字改完後重跑過）；slow 的 `tests/cli/test_output_snapshots.py` 以 `UPDATE_CLI_SNAPSHOTS=1` 重產；vitest 883、typecheck、`pnpm build` 過。新增測試：`tests/engine/test_weapon_skill_scaling.py`（武器 × 屬性表、技能自己的屬性與第二屬性不生效、命中／狀態抵抗／擊倒／預覽、專精、卡片「目前」等於引擎值）、`tests/skillgen/test_weapon_skill_scaling.py`（工坊鎖定、驗證器、組合器 60 種子）、`test_scaling_follow.py`（LLM 提議的武器技）、`client/src/workshop/locked.test.ts`。

為了 AI 軌跡改變而改的既有測試：`test_gamble.py` 兩個 AI 種子 12、28 → 6、77（同樣驗證反噬與賭注失敗）；`test_proposal.py` 的往返比對不比武器技的縮放屬性；`test_weapons_24a1.py` 與 `test_rule_texts_41a.py` 改成新句子。

## 實機（內建瀏覽器，8012，1600×900，已結束並還原視窗）

工坊 → 打擊 → 主動 → 武器技 → 近戰：縮放屬性顯示「看手上武器（力量）」且草稿自動對齊；改遠程武器顯示「看手上武器（敏捷）」；改法術技恢復六屬性可選。卡片文字（刺殺／劈砍）以 `skill_card` 與 CLI 驗證（「傷害算法：武器骰 1d4＋敏捷／力量（取較高） × 0.3（目前 +4）」）；**戰鬥中的傷害數字只用自動化測試驗證，沒有在瀏覽器實際打一場**。

## noqa

`src` 無新增。測試一處 `# noqa: PLC0415`（函式內 import）。

## 待 PM 決定

1. 隨機組合器的 `melee_dex_permille`（近戰武器技抽敏捷的機率）現在不影響結果（為保持亂數串流仍抽一次）。要不要移除這個設定欄位？（移除會改變既有種子的組合結果。）
2. 三選一／候選產生器的「加深／橋接／新方向」仍用技能的 `scaling_attr` 比主角最高屬性；武器技現在固定是武器大類主屬性（力量或敏捷），與實際手上武器可能不同（例：法器主角不會拿到武器技，影響小）。要不要改成看手上武器？
3. 內建 7 招提示屬性為敏捷的近戰武器技、`build_assassin`／`build_gambler` 的不一致招：要不要順手改提示屬性（引擎不使用，只影響卡片 `scaling_attrs` 的上色與面板「影響哪些招」的舊 fallback）？
4. 「武器技在力量武器上，智力再高也不加傷害」之後，混搭 build（智力主點＋劍技）不再有收益；若要保留「魔劍士」類路線，需靠雙屬性武器或專用技能（玩法 PM 決定）。
5. 武器技的護盾／治療（如蓄力劈砍的護盾）也跟武器屬性走，效果句寫「武器屬性加成」；若玩法 PM 希望這類效果仍看技能自己的屬性，需另開例外。
