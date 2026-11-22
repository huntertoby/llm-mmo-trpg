# Phase E5 報告｜行為改寫補種類（彈射、普攻變形）與預算閘門

> 規格 `docs/phases/PhaseE5計畫.md`；規則以 `docs/design/08-裝備.md` 8.29 E5（#175）與玩法交接 4.1.36 待決答覆 2 為準。基準 main `2904f2d1d`（含 E1）。預算閘門的放法照開發 PM 裁定 A。

## 1. Commit

| 項目 | commit |
|---|---|
| 3 普攻變 2 格直線（`attack_shape`、展開模組、預覽、卡片、預算、工坊選項、「這把武器不能套用」標灰） | `c70034971` |
| 2 預算閘門（skillgen 算表、規則包 `reshape_gates`、引擎查表、所有開戰路徑接上、「這招不能套用」標灰） | `0d921e445` |
| 1 彈射（卡片字；機制直接用現有的單體→連鎖） | `a2e93e62c` |
| 4 收尾（上手筆記、截圖；`classify.py --check`、`content check` 通過） | `a6f046d5e` |
| 合併 main（含 E2；`view.py` 的詞條行合併成 E2 的 `_affix_line` ＋ E5 的 `off_zh`，`affixStatus.test.ts` 兩邊測試都留，OpenAPI 重產） | `c48eca727` |
| 報告 | 最後一個 commit |

## 2. 各項做法

### 2.1 普攻變 2 格直線（第 3 項）

- `ModifierChange.attack_shape: "line" | None`（沒填不輸出，既有修正技序列化不變）；`modifier_changes.yaml` 加一筆（`applies_to: [attack]`、`self_only`、`reshapes`、`budget.unit: structured`）。
- 新模組 `src/trpg/engine/attack_shapes.py`：
  - `suits_line`：近戰而且射程 1。矛、鞭（射程 2）、遠程、法器都不能套用。
  - `attack_line_tiles`：從出招起點（`strike_tiles`）往目標方向，目標那格起共 2 格；出界或視線被擋就停。
  - `attack_line_extras`：線上目標以外、活著的敵人（由近到遠，巨型單位只算一次）。隊友不算、不擋。
  - `attack_shape_state`：有沒有生效、沒生效的原因（`weapon`／`gate`）、閘門的降傷‰。
- `reactions.perform_unit_attack` 只在 `primary and not reaction`（自己回合的主動普攻）時展開。藉機攻擊、監視射擊、反擊都是 `reaction=True`，照舊打單體。`battle.py` 沒動：目標仍是相鄰的敵人，合法動作不變。
- 線上每個目標各自擲命中、各自算暴擊（`_attack_once`）。附加元素、命中附帶的狀態（`hit_reactions`、修正規則命中後效果）每個人都生效。
- 連擊、分裂只看第一個目標：其他人的 `_attack_once(..., follow_ups=False)`，不呼叫 `after_attack_hit`，所以 `attack_hits_landed` 一次普攻只 +1。
- 「每第 N 次命中」（`every_n_hits`，被動與裝備）：直線普攻期間設 `Ctx.hit_count_once`，同一個攻擊者只 +1。
- 閘門降傷（第 2 項）乘在這次普攻每一下上：主目標、雙匕首第二下、連擊多的那一下、線上其他人。
- 預覽：同一個 `perform_unit_attack` 的模擬，所以 AI 估值與畫面一致。另外把直線兩格（含沒人的格子）加進 `affected_tiles`，說明多一行「普攻直線：往目標方向打 2 格，只打敵人（傷害 X%）」。不能套用時寫「普攻變形沒有效果：這把武器不能套用」。沒有變形規則時，預覽的格子和說明跟改前一樣。
- 卡片句子（`DESCRIBED_CHANGES`）、技能工坊選項（`2 格直線`）、預算（`STRUCTURED_CHANGES["attack_shape"]`：基準武器傷害 ×（直線 2 格倍率 − 單體倍率），再乘 `shape_benefit_permille`，同 `shape_to` 的算法）都補上。
- 標灰：`GearSkillView.off_zh`、`AffixLineView.off_zh`（新欄位，`str | None = None`）。前端技能列小圖示加灰（沿用 `cond-off` 的灰），說明卡上方「沒有效果：這把武器不能套用」；裝備卡詞條行經 `inactiveNote` 標灰寫同一句。
- `ATTACK_LINE_LENGTH = 2` 歸 `const`（`classes.yaml` 新規則 `py-engine-attack-shapes-line-length`，理由：8.29 定的形狀，不是數值）。

### 2.2 預算閘門（第 2 項，玩法答覆 2；開發 PM 裁定 A）

- **算法**（`src/trpg/skillgen/reshape_gate.py`）：只看「會由第 9 類詞條授予、而且有變形規則」的修正技。
  - 技能：逐招把那個修正技的變形規則套上（純函式 `modifiers.reshaped_skill`，和引擎同一份），形狀有變的才算。原招與變形後的招都用 `skill_budget` 算總點數。沒超過 → 1000‰。超過 → 傷害效果在總點數裡的那部分乘 `p`，取剛好不超過原總點數的最大整數 `p`。`p` 低於 `modifier.reshape_gate_min_permille`、或沒有傷害可降、或算不出預算 → 0（不能套用）。
  - 普攻：普攻的換算基準是基準武器傷害 × 形狀倍率，全部是傷害，所以 `p ＝ 單體倍率 ÷ 直線 2 格倍率`（目前 833‰）。
  - 「武器射程」的招轉連鎖時，射程照 `range_baseline` 算（射程係數 1，和原招的「武器射程」同價）。
- **新數字**：`skill_budget.yaml` 的 `modifier.reshape_gate_min_permille: 500`（`ModifierBudget` 必填欄位；初值照提案「傷害減半」）。開進工坊（預算表「修正技能」組，中文名「修正：裝備改寫招式的最低傷害（‰）」，寫了調高、調低的影響）；x10 由 `modifier.*` 的 keep 涵蓋。
- **表放在規則包**：`Ruleset.reshape_gates: dict[str, int]`，鍵 `<修正技 ID>|<技能 ID 或 attack>`，值＝傷害‰。空的不輸出，所以沒有裝備授予的變形修正技時，規則包 JSON 與雜湊都不變（現有內容就是這樣）。
- **引擎只查表**（`src/trpg/engine/reshape_gate.py`）：
  - 只管鍵在 `UnitState.gear_skills` 的規則。自己學的、LLM 產生的修正技不過閘門。
  - 查不到的組合當「不能套用」。
  - 同一招有好幾個裝備授予的變形修正技時，只留依技能鍵排序第一個通過的（見待決 3）。
  - `modifiers.shaped_skill` 拿掉被擋的規則（合法動作、預覽、AI、結算都經過它）；`damage_permille` 乘降傷；`attack_shapes` 對普攻做同樣的事。
- **標灰**：
  - 會被它變形的主動技能全部被擋 → `GearSkillView.off_zh ＝「這招不能套用」`，小圖示灰，卡片寫「沒有效果：這招不能套用」。
  - 只擋一部分 → 不灰，`note_zh ＝「這招不能套用：〇〇、〇〇」`寫在卡片上。
  - 普攻直線被擋 → 同樣標灰。
- `modifiers.py` 的 `shaped_skill` 拆出純函式 `reshaped_skill`（`_convert`、`_helps_allies` 改收 `Ruleset`）。邏輯與順序不變，442 招與 78 場都逐位相同。

**呼叫點（開戰的規則包都經過這裡）**

| 路徑 | 怎麼接 |
|---|---|
| CLI（`trpg battle`、`trpg run`…）、數值工坊寫回與驗證 | `api/primitive_coverage.load_checked_library` 最後 `return gate_library(library)` |
| 網頁伺服器（API 開戰、靶場、一輪、大世界遭遇、循環賽都用 `SessionStore`／`RunStore`／`WorldStore` 的內容庫） | `api/app.create_app`：`gate_library(...)` |
| API 一輪的生成技能 | `api/sessions.py`：`gated_with_skills(self.library, run.generated_skills)` |
| 技能工坊「裝上試玩」 | `api/workshop.equip_custom_skills(..., library)`：`gated_with_skills(library, custom, setup.ruleset)` |
| roguelite 開戰 | `roguelite/progress.battle_setup`：`gated_with_skills` |
| 大世界遭遇 | `world/battle.py`：`gated_with_skills` |
| 循環賽 | `world/league.py`：`gated_with_skills` |
| 工坊靶場（`practice_setup`） | `world/opening.py`：`gated_with_skills` |
| 工坊的比值模擬、頭目模擬 | `api/tuning/service.py` 的 `run_data(gate_library(load_library(...)))`、`sim/boss_probe.library_for` |
| sim（關鍵字抽樣、召喚報告、技能 fuzz） | `gated_with_skills` |

**判斷不開戰、所以沒接的**（`tests/skillgen/test_reshape_gate_paths_e5.py` 的 `LOAD_LIBRARY_ALLOWED`）：

- `api/tuning/service._rules_library`：只算預算，不開戰。
- `skillgen/random_composer.default_library`：組合器產生技能，不開戰。
- `load_checked_library` 本身：先 `load_library` 再包 `gate_library`。
- `content/` 底下：定義處（`Ruleset.with_skills`、`load_library`）。
- 測試、`scripts/` 用的內容庫：不是出貨路徑。比對腳本（compare78、census）沒有裝備授予的變形修正，表是空的。

**鎖住路徑的測試**（`tests/skillgen/test_reshape_gate_paths_e5.py`）：

- 結構：`src/trpg` 裡 `.with_skills(` 只准出現在 `skillgen/reshape_gate.py`。`load_library(` 要包在 `gate_library(...)` 裡，或列在上面的理由清單。
- 實際跑：帶測試用變形修正技的內容庫經過 `load_checked_library`、`create_app`（看 `store`、`runs`、`world` 三個的內容庫）、`gated_with_skills`（新加的 LLM 技能也查得到）之後，表都查得到那些組合。

### 2.3 彈射（第 1 項）

- 機制直接用現有的單體→連鎖：第二個目標是 2 格內、看得到、最近的同一邊單位；第一下沒中照樣跳；第二下 75%。引擎沒有新種類，連鎖的全域參數沒改。
- 裝備授予的修正技本來就能用 `shape_to: chain`（E1 的 `gear_checks` 只擋姿態與無聲）。只套技能，不套普攻（`shape_to` 的 `applies_to` 本來就不含 `attack`）。
- 卡片字：`shape_to: chain` 的句子加「彈射——打完第一個目標（沒打中也會跳），再跳到它 2 格內、看得到、最近的敵人，最多 1 次；每跳一次傷害、治療、護盾的威力 −25%（最低 25%）」。數字讀轉換表與 `core.yaml`。現有內容沒有人用 `shape_to: chain`，所以卡片與 CLI 快照不變。
- 預覽照現有連鎖顯示（測試 `test_bounce_preview_shows_the_chain`）。
- 「第一下沒中照樣跳，第二下 75% 再過閘門」：`test_bounce_jumps_even_when_the_first_hit_misses`。第二下的倍率＝自己學的同一招（只有連鎖 75%）× 閘門的 p。

## 3. 測試

- `tests/engine/test_attack_shape_e5.py`（25 項）：直線打到後面的敵人、只到 2 格、方向、隊友不受傷也不擋、預覽有兩格（含空格）、沒規則時預覽不變、8 種武器能不能套用、弓標灰（預覽、技能列、裝備卡）、反應攻擊不變形、元素每人都有、`every_n_hits` 只 +1、連擊只 +1、分裂只從第一個目標 1 次、預算有算、同種子同結果。
- `tests/engine/test_reshape_gate_e5.py`（12 項）：
  - 現有內容表是空的、規則包不變；
  - 降傷的 `p` 剛好不超過（用 `skill_budget` 反算）；
  - 降到最低還超過就擋（含調高最低值）；
  - 普攻用普攻基準；
  - 裝備彈射降傷、普攻不受影響；
  - 被擋的招不變形並標灰（全部擋與部分擋）；
  - 查不到＝擋；自己學的不過閘門；
  - 裝備普攻直線過普攻閘門；
  - 彈射第一下沒中照樣跳；預覽；同種子同結果。
- `tests/skillgen/test_reshape_gate_paths_e5.py`（5 項）：見 2.2。
- `tests/narrative/test_bounce_text_e5.py`（2 項）。
- 既有測試補：`tests/content/test_modifier_schema.py` 加 `attack_shape` 的範例。
- 前端：`gearSkills.test.ts`（標灰、部分擋的說明）、`affixStatus.test.ts`（詞條標灰）。

## 4. 驗收

基準：合併前用 `2904f2d1d`，合併 main 後用 `5e7b2cb9d`（含 E2）各比一次（`git archive` 的 `src`、`content`、`scripts`，執行時確認載入的 `trpg` 來自基準那份）。腳本放在暫存區，沒進 repo。

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill` 違規） | 合併前、合併後都逐位相同，`same=442 different=0` |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | 合併前、合併後都 `cells=204 different=0` |
| 78 場戰鬥（`compare78.py`，同 a 段那組；去掉 `ruleset_hash`、內嵌規則包，**`format` 也比**：`LOG_FORMAT` 沒變；合併 main 後） | `battles=78 events=26206 different=0`；內嵌規則包 0 差異 |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| ruff、format、mypy、lint-imports | 0 |
| tsc、vitest、build | 0（合併後 vitest 4895；build 合併後再跑一次也是 0） |
| `uv run python scripts/check.py`（合併 main `5e7b2cb9d` 之後，`c48eca727`） | 0（pytest 18360 passed、vitest 4895；已寫通過戳記） |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（995 passed）；CLI 快照沒變 |

`LOG_FORMAT` 不升版：沒有新事件、動作、狀態欄位。`Ctx.hit_count_once` 不在狀態裡；規則包新欄位空的時候不輸出。現有規則包與步驟算出的結果不變（78 場比對）。

**截圖**（實機，暫存的內容複本多兩個只給截圖用的修正技與詞條：普攻直線、只套「推擊」標籤的彈射；靶場把主角與兩個木樁排成一列）：

- 普攻直線的預覽：`docs/art/shots/e5/e5_attack_line_preview_1600x900.png`、`..._800x600.png`（兩個木樁格都標橘，預覽寫「普攻直線：往目標方向打 2 格，只打敵人（傷害 83.3%）」）
- 標灰的「這招不能套用」：`docs/art/shots/e5/e5_gate_blocked_1600x900.png`、`..._800x600.png`（彈射小圖示灰，卡片「沒有效果：這招不能套用」）
- 標灰的「這把武器不能套用」：`docs/art/shots/e5/e5_weapon_blocked_1600x900.png`、`..._800x600.png`（拿弓，普攻直線小圖示灰）

交美術 PM 驗收。

## 5. 待 PM 決定

1. **鞭也不能套用普攻直線**：規格寫「近戰武器；矛除外，矛本來就打 2 格」。鞭也是射程 2 的近戰，我照「射程 1 的近戰才行」一起排除，標灰同一句「這把武器不能套用」。
2. **同一招有兩個以上的裝備授予變形**：每個閘門是單獨算的，疊起來的總點數沒算過。保守做法：只有依技能鍵排序第一個通過閘門的那個生效，其他的對這招不套用。目前沒有內容會遇到；E6 的「同時 3 個」接上時再看。
3. **自己學的變形和裝備給的變形同時作用在一招上**：閘門只看裝備那個單獨套上去的點數，沒有算兩個疊起來。
4. **「武器射程」的招轉連鎖**：閘門用 `range_baseline`（射程係數 1）算，和原招的「武器射程」同價。實戰的連鎖射程是手上武器的射程，所以遠程武器（射程大於基準）的實際點數會比表高一點、近戰會低一點。
5. **部分擋下時不標灰**：彈射只對一部分招被擋時，小圖示不灰，卡片寫「這招不能套用：〇〇」。被擋的那招自己的按鈕沒有加註記。全部被擋才標灰。
6. **雙匕首的直線**：線上其他目標只打 1 下。主目標照連擊武器打 2 下，兩下都乘閘門降傷。
7. **直線普攻的被近戰轉身**：線上其他人被打（不論命中）也轉向攻擊者，例外照無聲、隱蔽。
8. **AI 的便宜估計**（`ai/utility/skill_estimate.py`，E2 在改，我沒碰）不知道閘門降傷，只影響候選排序。真正選招用預覽，預覽已經含降傷與直線。
9. **閘門最低傷害初值 500‰**：照提案「傷害減半」，未經模擬，使用者可在工坊調。目前測試內容的普攻直線 833‰、彈射大多 683～858‰；帶推擊等非傷害效果多的招（例如颶風踢、破城衝撞）會被擋。疑慮可記平衡待查（這段沒寫進 `docs/design/`）。
10. **`docs/phases/寫死數值-清單.md` 沒重產**：它由程式產生，基準上已經和現況有差（不是這段造成的）；為了不和 E2 衝突，沒改，合併後再重產一次即可。

## 開發 PM 裁定（2026-11-22）

合併為 a86658d3a 推上 main。寫死數值清單在 0cae2eecd 重產。截圖交給美術 PM 驗收。

1. 鞭比照矛排除：接受。鞭本來就能打 2 格，跟矛同理。已通知玩法 PM 補進 8.29。
2. 同一招有多個裝備授予的變形時，只有第一個生效：接受，這是保守做法。已轉給玩法 PM，看要不要寫成規則。
3. 「武器射程」照 `range_baseline` 算：接受。差距記進平衡待查，請玩法 PM 記。
4. 部分被擋時不標灰、只在卡片寫明：接受。交美術 PM 看。
5. `reshape_gate_min_permille` 初值 500：接受，數值由使用者在工坊調。帶推擊的招會整招被擋，例如颶風踢、破城衝撞，這件請玩法 PM 記進平衡待查。
6. AI 便宜估計不知道閘門會降傷：排進佇列，下次碰到 `skill_estimate.py` 時一起改。
7. 已重產（0cae2eecd）。
