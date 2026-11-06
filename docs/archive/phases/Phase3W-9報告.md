# Phase 3W-9 報告｜技能預算改用角色階級

規格：`docs/phases/Phase3W計畫.md` 第 5 節（3W-9、玩法 PM 回覆 6.34.9、#73）；設計 `docs/design/06-技能.md` 6.34.3、6.34.9、6.12，07 7.6。實作者：opus。

## 1. 做了什麼

1. **角色階級一個函式**：`trpg.skillgen.skill_tier.character_tier(library, level)`（照 `roguelite.yaml` 的 `offer_tier_by_level`）。候選（`offers.candidate_request`）、白板、組合器、LLM 提議、閃現出題的 `tier` 都來自它；`SkillDef.tier` 的意思改成「這招目前用哪一階的預算」，玩家的技能一律等於角色階級（敵人等手寫內容照舊用自己寫的階級）。
2. **最低角色階級表放在 content**：`skill_budget.yaml` 的 `min_character_tier`（`CharacterTierRules`）照 6.34.9 表：3 階＝修正型被動、雙屬性縮放、整排直線（長 6）、連鎖、7 格以上地形；2 階＝召喚（含獻祭召喚物）、陷阱、姿態、自身位移或互換（teleport、dash、charge_through、shadowstep、leap、swap、swap_any）、3×3、接續段、第二元素、4～6 格地形；其餘 1 階（推拉、傳送別人、表面、吹送、震波、條件、觸發型被動、反應）。
   - 同源函式 `validate.tier_requirements`／`minimum_tier`／`tier_violations`；驗證器多了 `tier.*`。
   - 組合器（`_composable`、`build_shape`、直線長度上限）、LLM 選單（`proposal_subset`：原語、骨架、形狀、接續段範圍）、白板（形狀改讀同一張表，`shape_min_tier`／`dual_min_tier` 刪除）、`trpg llm propose` 的骨架輪替都照這張表篩；閃現模板與轉型仍用自己的 `min_tier`（6.34.9 表 3、#73）。
   - 「只能主動」「只限大地」等非稀有度限制不動。
3. **稀有度只當標記**：`validate.structural_rarity`（原本的稀有度需求、效果數、變奏數、雙屬性、#58 地形格數照算）。驗證器不再出 `rarity.primitive／shape／…`，只留 `rarity.legendary`（傳說核心只在稀有度標為傳說的技能＝完整技能）。白板、組合器重調（`evolution._rarity`）、閃現都改用它填標記。工坊仍顯示「最低稀有度」，另加「最低角色階級：N 階（原因）」的提示。
4. **升階重算**：`skill_tier.retier(library, skill, tier)`：結構、ID、名稱、來源、閃現加成保留；預算分數不低於升階前；依序試
   1. 預算器原本的旋鈕（傷害／治療／護盾骰子或倍率、推拉距離、修正幅度、接續段）；不夠再加效果參數的旋鈕（狀態、表面持續回合等，組合器同源 `effect_knobs`）；
   2. 固定強度結構：元素姿態階梯、召喚物最大 HP 加成 × 費用減輕（冷卻、資源）；
   3. 升降地形：「地形＋落石」（大地傷害，數值照預算；同 3W-2b 地形模板）；
   4. 都不行時把旋鈕推到最大（費用不動），`retier_report` 標成不在窗內。
   - 一輪裡：`trpg.roguelite.retier.sync_skill_tier`，在升級節點（角色升階的當下、戰鬥之間）對裝備＋備用技能重配；手寫技能重配後成為生成技能 `<原 ID>_t<階級>`，等級、用法統計、備用跟著換 ID，候選不再出原本那招。
   - 閃現：`derive_chain／derive_skill／skill_before` 改用 `at_role_tier`（先照角色階級重配，再套變化；強度下限以重配後為準）。`at_tier`（只換階級、不重配）保留給測試比較用。
5. **3W-4 #4、#8、3W-2 #9**：#8 手寫池退回的候選在 `make_offer` 就照角色階級重配（卡片＝拿到後的數字）；候選池（完整模式 `_pool`／`_general_pool`、白板退回 `_from_pool`）也只取最低角色階級不高於角色的技能。#9 技能 `tier`＝角色階級，升階時統一重配。#4 見第 4 節。
6. **創角例外**：`provenance.origin: starter`（新增來源值）不受階級限制；白板配方新增 `creation_tier`，基本召喚物 `summon_spirit`／`summon_skeleton` 改 `min_tier: 2, creation_tier: 1`（三選一 2 階起才出，創角 1 階照給）；`compose_whiteboard(starter=True)`。
7. **隆地白板**：十字（5 格）升地形依表要 2 階，1 階不能出；`raise_ground` 改成單格（`ground_tile`、AP 1，同自身類白板）。
8. **存檔 `trpg-run/11`**：`RunState.skill_tier`（主角技能目前照哪一階配數值）；`/10` 可讀（讀入時 `skill_tier` 為空），`save.upgrade_save(library, save)` 在戰鬥之間照角色階級重配一次（API 讀檔、CLI `run auto --from` 會呼叫）；戰鬥中的舊存檔不動，那場打完的下一個節點（`next_node` 開頭的同步）再重配。
9. 其他：`trpg.sim.skill_fuzz` 的站位多試距離 2（環形半徑 2 的技能之前永遠沒有合法選取，這次亂數剛好抽到）。

## 2. 設計與取捨（保守做法）

- **門檻只擋「從零產生」的技能**：`tier_violations` 略過 `builtin`（手寫內容：敵人、手寫池，76／301 招按表會「超階」，保留原本的階級與內容）、`workshop`（工坊是開發者寫手寫技能的工具；工坊另外顯示最低角色階級）、`starter`（創角例外），以及 `provenance.parents` 非空的技能（閃現、轉型、分歧進化：結構保留，新內容由模板自己的 `min_tier` 把關）。
- **不改 `SkillDef` 欄位**：`tier` 仍是欄位（敵人技能要用），玩家技能靠「同步＝角色階級」維持；所以戰鬥紀錄結構與結算語意不變，`LOG_FORMAT` 不遞增（仍 `/88`；只多了 `Origin` 的一個字面值與 `skill_budget.yaml` 的新段落，舊紀錄由 `ruleset_hash` 區分，照 `戰鬥紀錄格式變更.md` 1.2）。
- **新開局不重配**：開局技能本來就是 1 階；開發者起始包、回歸範本的技能保持原樣，到第一次升階時一起重配（`skill_tier` 一開局就記成 1）。
- API／OpenAPI 沒有變（`export_openapi.py` 無差異）；`export_client_fixtures.py` 無差異；圖示夾具重產（組合器輸出隨階級篩選改變）。

## 3. 驗收證據

- 行為一致測試（新增）：
  - `tests/skillgen/test_skill_tier_3w9.py`（32）：每階各抽原語／骨架／形狀驗表（3 階 4 招、2 階 8 招、1 階＋推拉表面吹送震波條件被動反應、直線長 6）；驗證器只擋從零產生的技能、創角與推導技能不擋；稀有度只是標記；5 種傷害白板 × 3 種子在 1／2／3 階：預算比例在窗內、驗證通過、結構與 ID 不變、分數遞增；骰子隨升階變大（6.34.9 例子）；升降地形（陷地術、築高台、大地崩陷、隆地白板）2／3 階進窗；淬毒白板 3 階標成不在窗內但分數不降；**同一招 1／2／3 階卡片骰子＝規則包、預覽範圍包含實際傷害**；閃現出題從重配後的技能起算、選項不低於下限。
  - `tests/roguelite/test_retier_3w9.py`（7）：開局 1 階；升到 2 階時每招重配（階級、分數不低於升階前、驗證通過、候選也是 2 階）；手寫技能換 `_t2`／`_t3` 並帶走等級、候選排除原招；候選重配；`/10` 存檔轉換（戰鬥之間重配、再轉換不變、存讀一致）；戰鬥中舊存檔不動。
- 重算覆蓋（腳本量測，未調數值）：
  - 白板（每個配方 × 3 種子，從配方最低階升到 3 階）：2 階 117／132、3 階 175／198 在窗內；不在窗內的全是點數固定的狀態／表面白板：淬毒、毒沼、凝冰、烙印、點燃（3 階）、毒觸、毒反擊、隱蔽反擊。
  - 手寫技能（262 招 1 階）：2 階 217、3 階 189 在窗內（其餘分數不降、旋鈕推到最大）。
- 指令（最後一輪）：`ruff check .`、`ruff format --check .`、`mypy`（831 檔）、`lint-imports`（7 kept）全過；pytest `tests/skillgen tests/content tests/llm tests/narrative tests/roguelite tests/api tests/engine/test_composite_skills.py tests/engine/test_earth_54b.py tests/test_architecture.py tests/test_primitive_coverage.py` 5404 通過（1 個 evolution 測試修正後單檔重跑通過）；`tests/cli --timeout=3000` 154 通過、1 xfail；`tests/sim` 通過；`pnpm typecheck`、vitest 1158 通過；swamp 種子 7 重播通過。沒跑 `scripts/check.py`、大型模擬。
- **CLI 快照**：`tests/cli/snapshots/llm_propose_mock.txt` 用 `UPDATE_CLI_SNAPSHOTS=1` 更新——骨架輪替照角色階級篩選後題目改變；第 2 題（rare、關鍵字「召喚物」、1 階）因為召喚要 2 階，LLM 的召喚提議被選單擋下、退回手寫池（退回率 33%）。`test_run_auto_reaches_a_branching_evolution` 種子 3 不再進化，改用種子 2（種子 5 照舊 xfail 等 3W-5）。

## 4. 待 PM 決定

1. **點數固定的狀態／表面白板追不上高階預算**（3W-4 #4）：淬毒、毒沼、凝冰、烙印、點燃、毒觸、毒反擊、隱蔽反擊在 2／3 階重算後低於 70%（目前標為不在窗內、數值推到最大、分數不降）。選項：(a) 狀態／表面的點數隨階級放大（效果本身變強，例如持續或層數上限），(b) 升階時補一個隨預算的弱傷害（像地形的「落石」），(c) 接受偏弱。
2. **升降地形用「地形＋落石」過預算下限**（3W-2b #5、本段第 5 項）：費用減輕不夠時會多一個大地傷害效果（結構多一個效果）。是否接受、或改別的做法？
3. **手寫內容不受最低角色階級限制**：76 招手寫技能按表會「超階」（例：1 階的召喚技、姿態、化身）。敵人照舊；玩家只會經由候選（已依表篩）、開發者起始包、回歸範本拿到。開發者起始包／回歸範本開局時保持原樣，第一次升階才重配——要不要開局就照表檢查或重配？
4. **工坊不擋最低角色階級**（只顯示提示）：工坊目前是開發者寫手寫技能的工具；若之後開放給玩家（大世界許願池等），應改成照角色階級擋。
5. **由既有技能推出來的不擋**（閃現、轉型、分歧進化）：例如 1 階創角召喚白板閃現後仍是召喚；新內容由模板 `min_tier` 把關。是否同意？
6. **創角例外的範圍**：只有白板路徑標 `starter`；創角退回手寫池時是內容庫技能（`builtin`，本來就不擋）。化身（姿態）、召喚的起始技能在 1 階閃現時，模板照角色階級出（大多數模板 1 階可用）。
7. **重算目標**：重配時預算器在 75～95% 抽目標（同組合器），所以同一招升階後的比例不一定和升階前相同；被動模板少的技能（例：燃燒印記）升到 2 階後起點較高，之後的閃現較快被強度下限擋住（`test_power_never_drops_along_five_flashes` 對它只要求閃 1 次）。要不要改成「維持升階前的比例」？
8. **`trpg llm propose --mock` 預設 1 階**：關鍵字輪替會抽到 1 階還不能用的召喚物，會退回手寫池；要不要讓 CLI 依關鍵字自動選可行的階級？
9. **舊存檔轉換的時機**：`/10` 的戰鬥中存檔不重配（重播要用當時的技能），打完那場才重配；戰鬥之間的存檔讀檔就重配。
10. **複雜度 noqa**：沒有新增 C901／PLR0911／0912／0915 的 noqa。

## 5. Commit 列表

- `af7e43b0` feat: skill budget follows character tier (tier gate, retier, save /11)
- `609a613c` fix: gate only fresh skills by tier, creation recipes, update skillgen tests
- `629b8b3d` test: 3W-9 tier table, retier, run sync and save /11 tests
- `5af085b8` fix: workshop skills are not tier-gated (authoring tool)
- `40d4f61c` test: update composer, proposal and schema tests for character-tier gate; refresh icon fixture
- `5100452b` test: engine/cli/sim updates for character-tier gate; refresh llm propose snapshot
- `4b63df20` fix: retier cache keeps the library; rarity marker assertions in evolution test
- （本報告）docs: 3W-9 report
