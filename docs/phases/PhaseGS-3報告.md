# Phase GS-3 報告：化身進入效果、護盾看最大 HP、天生武器屬性、實心環形（#173）

依據：`docs/phases/PhaseGS-3計畫.md`；`docs/玩法決定紀錄.md` #173；`docs/design/06-技能.md` 6.30「形態池名單」最後一點與第 29 行形狀清單；08 8.11；`docs/phases/PhaseGS-2報告.md` 與開發 PM 裁定。
基準：main `4cb00d459`。分支 `worktree-agent-adca61bea5b32f3bc`，沒 push。
沒動 `docs/design/`、`config/`、`llm.toml`、`content/forms.yaml`、`content/sim/builds.yaml`；沒跑模擬、沒量平衡。

## 1. 結果

6 項都做完。8 招（改 4、補 4）的預算都在 70～100%（見 4）。補的 4 招裡有 2 招照設計的數字會掉到 70% 以下，用最保守的方式拉進區間，交 PM 決定（見 10 第 1、2 點）。

## 2. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 4 實心環形 | `0058d7c61` | `ShapeSpec.solid`、`skill_shapes.yaml` 的 `solid_option` 與 `cell_count.solid_by_value`、`shape_budget.ring.solid_by_value`（1：1800、2：2600）、引擎幾何、驗證、敘述文字、工坊 2 欄；`tests/engine/test_solid_ring_gs3.py` |
| 1 進入時效果 | `e06d4f547` | 原語 `companions`／`companion_shapes`（`enter_form`：`[apply_status, push]`、`[ring]`）、`SkillDef` 的進入時效果規則、`skill_limits.min_form_entry_tier: 3`／`min_form_entry_cooldown: 2`、結算順序、工坊 1 欄；`tests/engine/test_form_entry_effect_gs3.py` |
| 2 護盾看最大 HP | `bd36fac67` | `shield.max_hp_permille`、`skill_budget.yaml` 的 `shield_max_hp_points: 21`、引擎、敘述與技能卡、×10 登記、工坊 2 欄；`tests/engine/test_shield_max_hp_gs3.py` |
| 3 天生武器屬性 | `dc94401e5` | `SkillDef.scaling_source: natural_weapon`、引擎縮放與對抗、算法句「天生武器的屬性」；`tests/engine/test_natural_weapon_scaling_gs3.py` |
| 5 改 4 招、補 4 招 | `d93f9c142` | 4 個新技能檔、4 招改動、登記處與招數、`tests/engine/test_form_high_gs3.py` |
| 5（快照） | `6b9795b37` | 圖示夾具、CLI 快照、parity 夾具、前端圖示測試的招數 |
| 6 工坊 | `5ce1edacf`、`e50d0a163` | `tests/api/tuning/test_workshop_open_gs3.py`（白名單本身各項已隨 1、2、4 加進去，否則預算表「每個整數都要開或列結構」的測試會紅）；第二個 commit 只拿掉一個多餘的 `type: ignore` |
| 報告 | 本 commit | |

項目 4 先做（項目 1 的形狀要用到實心環形）。

## 3. 受影響的既有功能（開工盤點）與處理

| 功能 | 處理 |
|---|---|
| 引擎：形態進入 | `Cast.run`：技能有進入時效果時，先結算 `enter_form`（變身＋形態進入獎勵），再擲命中、結算進入時效果。沒有進入時效果的技能順序不變（`_form_entry_lead` 回 `None`）。 |
| 引擎：護盾 | `numeric.shield`：填 `max_hp_permille` 時護盾＝施放者目前 `max_hp` × ‰，不擲骰、`scaled_permille` 為 0；倍率（層數加成、連鎖衰減）照舊。 |
| 引擎：縮放屬性 | `engine/skills/scaling.py`：`skill_scaling_value`、`skill_scaling_attr`、`skill_scale_attr` 多傳形態中的天生武器（`unit.weapon`）。命中（`skill_profile` 走 `skill_scaling_value`）與傷害、對抗都跟著換。 |
| 引擎：目標形狀 | `ring_tiles`／`around_tiles` 多 `solid`；`_self_area`、`around_area`、`anchored_area` 傳 `spec.solid`。持續區域不支援實心（驗證擋）。巨型單位的實心環形＝到佔格的切比雪夫距離 1～N。 |
| content schema 與驗證 | `ShapeSpec.solid`（只能 `true`、只有內建內容、只有 `solid_option` 的形狀、不能配 `zone`）；`PrimitiveDef.companions`／`companion_shapes`（載入檢查：只能寫在 `sole_effect` 原語上、原語要存在）；`SkillDef._check_form_entry`（姿態、形狀自己或實心環形、形狀自己時要 `affects: self`、不能填幅度）；`skill_limit_problems` 加階級與冷卻下限；`_check_max_hp_shield`；`_check_scaling_source`（技能條件要 `in_form`、不是武器技、不能配第二屬性或專精）；`validate._stance_violations` 讓化身技的進入時效果可以施加非姿態狀態、不能施加姿態狀態；骨架 `stance` 的形狀限制對帶進入時效果的化身技放行（形狀已由 `SkillDef` 擋）。 |
| 技能預算計價 | 形態係數照舊；進入時效果的點數照形狀倍率加上去（`affects: self` 的照舊 ×1）；實心環形查 `solid_by_value`；格數查 `cell_count.solid_by_value`（區域預算與閃現用）；看最大 HP 的護盾用 `shield_max_hp_points`。 |
| 技能卡與說明文字 | 形狀句「周圍 N 格內都打，含相鄰，不含自己」；護盾「吸收量＝你目前最大 HP 的 15%」；算法句「天生武器的屬性」；卡片 `EffectStat` 的護盾標籤「最大 HP 15%」。 |
| 工坊白名單 | 見 6。 |
| 組合器 | 不用新參數：`enter_form` 照舊 `sole_effect: true`（產生器與工坊選項讀這個就不加效果）；新的原語參數 `knob: none`；`solid`／`scaling_source` 不在產生器的選項裡。census 小樣本 0 差異（見 5）。 |
| LLM 提議的 schema | 護盾的 `max_hp_permille` 是數值參數（不列給 LLM，`knob: none` 預算器不填），`dice` 改成 `required_when: {unless_filled: max_hp_permille}`，提議模型裡 `dice` 變選填、缺了由 rules 階段報錯。`proposal_from_skill` 遇到帶進入時效果的技能丟 `ValueError`（few-shot 與往返測試不收）。`scaling_source` 不在 `_SUPPORTED_SKILL_KEYS`，本來就丟 `ValueError`。OpenAPI 沒變。 |
| 前端技能卡與範圍預覽 | 範圍預覽畫伺服器的 `affected_tiles`（`screens/battle/useHighlights.ts`），所以前端不用改：`test_form_high_gs3.py::test_the_range_preview_highlights_the_solid_ring` 直接驗 `preview()` 的影響格＝距離 1～N 的每一格（化身技另外含施放者自己那格，因為變身作用在自己身上）。沒有另外截圖（前端程式沒改）。 |
| 存檔與戰鬥紀錄 | 見 7（`LOG_FORMAT` 不升）。 |
| 快照 | 見 5。 |
| 閃現、升階 | 沒改程式。新 4 招的閃現與升階行為見 10 第 4、5 點。 |

## 4. 8 招的預算比例

| 招（ID） | 階級／稀有度 | 內容 | 費用 | 比例 |
|---|---|---|---|---|
| 熊王怒吼（`skill_form_bear_king`） | 3 史詩 | 進入熊；實心環形 1 的敵人虛弱 2 回合 | 冷卻 3 | 96.0% |
| 影貓潛襲（`skill_form_shadow_cat`） | 3 稀有 | 進入貓；自己隱蔽 **2** 回合（設計 1，見 10-1） | 冷卻 3 | 73.9% |
| 巨人踐地（`skill_form_giant_stomp`） | 4 稀有 | 進入巨人；實心環形 1 的敵人推開 1 格，撞擊骰明寫 1d6（見 10-2） | 冷卻 3 | 75.5% |
| 龍威降臨（`skill_form_dragon_dread`） | 4 史詩 | 進入龍；實心環形 2 的敵人恐懼 1 回合；縮放屬性意志（`skill_scaling.yaml` 的主題要求） | 冷卻 3 | 87.9% |
| 野性連擊（`skill_form_wild_flurry`） | 3 稀有 | 改用天生武器屬性（預算不變） | 法力 60、冷卻 2 | 70.6% |
| 化形震地（`skill_form_quake`） | 3 史詩 | 改成實心環形 2（倍率 2200 → 2600） | 法力 80、冷卻 3 | 86.6%（GS-2 73.3%） |
| 原形歸一（`skill_form_primal_return`） | 4 史詩 | 改成實心環形 2 | 法力 100、冷卻 3 | 86.5%（GS-2 73.2%） |
| 化形守護（`skill_form_guardian`） | 4 史詩 | 護盾＝最大 HP × 150‰，持續 2 回合（預設），不加屬性 | 法力 80、冷卻 3 | 76.7%（同 GS-2） |

- 4 招新的都是 `kind: stance`、`category: spell`、`weapon_req: any`、`cost: {cooldown: 3}`，沒有 `icon_prop`；都有繁中 `concept`、`cast_flavor`；都不是起始技能（`is_starter_skill` 只收 1 階）。
- 冷卻 3 在姿態的冷卻折抵只算 30‰（`stance_cooldown_per_turn`），幾乎不影響比例。
- `shield_max_hp_points: 21` 是反推值：GS-2 的 7d8 平均 31.5 點 ＝ 150‰ × 21 ÷ 100，所以化形守護的比例和 GS-2 逐位相同。
- 實心環形 2 的倍率 2600：一般環形 8 格 1800、16 格 2200，每 8 格 +400 外推到 24 格；實心 1 和一般環形 1 同一圈 8 格，取 1800。照格數取較貴的保守值，沒試數值。

## 5. 不受影響的比對

腳本放在 scratch（沒進 repo）：`budget434.py`、`compare78.py`、`census_cmp.py`（沿用 HC-6a），另寫 `parity_gs3.py`、`cli_text.py`／`cli_cmp.py`、`icon_cmp.py`。基準用 `git archive 4cb00d459 src content scripts`，執行時確認載入的 `trpg` 來自基準那份。

| 比對 | 結果 |
|---|---|
| 逐招預算（原有招減掉改的 4 招） | 基準 438 招、本分支 442 招；**未改的 434 招 `same=434 different=0`**（`skill_budget` 全部明細＋`validate_skill` 違規）；有差異的只有化形守護、化形震地、原形歸一（野性連擊的預算不變） |
| 78 場戰鬥（15 張正式地圖 × 種子 1、7；`open_plain` 種子 3 × 8 build；4 張頭目圖 × 種子 3～12） | **`battles=78 events=26206 different=0`**（`--log-json` 去掉 `ruleset_hash` 與內嵌規則包＋文字輸出；事件數同 HC-6a）。內嵌規則包的差異只有新欄位（原語 `companions`／`companion_shapes`、形狀 `solid_option`／`cell_count.solid_by_value`、`shape_budget.ring.solid_by_value`、`skill_limits` 兩個下限、`shield_max_hp_points`、護盾的參數）與技能清單多 4 招、改 4 招 |
| 組合器 recipe census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | **`cells=204 same=204 different=0`**，其餘欄位也相同 |
| 技能圖示夾具（`skill_icons.json`） | 重產前預測「只多 4 招」；逐鍵比對：`skills` 只多 4 招、0 改動，`random`、`workshop` 相同 |
| 前端技能卡夾具（`export_client_fixtures.py`） | 重產後 0 差異 |
| CLI 快照 | 預測「只有含技能清單的鍵會變」：實測只有 `skills_list` 與 `skills_show_all/03`～`/15`（同 GS-2，新招照 ID 插入、後面分段移位）。用 `UPDATE_CLI_SNAPSHOTS=1 ... -k "skills_list or skills_show_all" -n 0` 只重產這些鍵。另外把 `trpg skills list` 與每招 `trpg skills show` 的文字整份和基準比對：只多 4 招、只改那 4 招 |
| parity 夾具（`refactor_3wr2.json`） | 整份重產和夾具比：`complete`、`retier` 各只多 4 招、只改 4 招，其餘 0 差異；閃現 123 筆照原取樣逐筆重算，0 差異（取樣裡沒有這 8 招）。照 GS-2 的做法只更新這 8 招的 `complete`、`retier` |

## 6. 工坊（新參數都開進去）

| 欄位 | 對象 | 中文名 | 說明重點 |
|---|---|---|---|
| `shape_budget.ring.solid_by_value.1`、`.2` | 技能預算表（組「形狀」） | 形狀倍率：實心環形半徑 1／2（‰） | 格數、越大越貴、目前用到的招 |
| `shield_max_hp_points` | 技能預算表（組「特殊效果的算法」） | 看最大 HP 的護盾：每 10% 最大 HP 的點數 | 越大越貴、初值為什麼是 21 |
| `skill_limits.min_form_entry_cooldown` | 核心戰鬥規則 | 帶進入時效果的化身技最短冷卻（回合） | 調高、調低的效果；調高到比現有招的冷卻長會被驗證擋（測試：設 4 → 擋，設 3 → 過） |
| 技能效果 `max_hp_permille`（`effect_types: [summon, shield]`） | 技能 | 最大 HP 比例（‰） | 召喚與護盾各自的意思、調高調低；同一路徑只能列一行，所以和召喚的那行併在一起（原本標籤「召喚物 HP 加成（‰）」改成「最大 HP 比例（‰）」） |

- 不開的：`skill_limits.min_form_entry_tier`（3 階以上才能帶，是結構）、`shape.solid` 與 `scaling_source`（不是整數，工坊只開數值）。
- ×10：`shield_max_hp_points` 登記 `keep`（預算點數）；`max_hp_permille` 是 ‰，`skill_limits.*` 原本就有 `keep` 樣式涵蓋；`classify.py --check` 0。
- 寫死數字：加了兩條 `const` 規則（`py-gs3-max-hp-shield-unit`：「每 100‰」的 100；`py-gs3-form-entry-structure`：「進入時效果剛好 1 個」的結構常數與訊息裡的 `effects[1]`）。

## 7. `LOG_FORMAT` 判斷：不升

照 `docs/phases/戰鬥紀錄格式變更.md` 1.1、1.2：

- 事件、動作、決定、戰鬥狀態、`BattleLog` 的欄位都沒有增減。
- 新的欄位都有預設值或不輸出（`ShapeSpec.solid`、`SkillDef.scaling_source` 是 `None` 時不輸出；護盾的 `max_hp_permille` 是 `None`；原語 `companions` 預設空），舊內容的結算不變：78 場 `different=0`。
- 結算順序只對「帶進入時效果的化身技」改變（舊內容沒有這種技能）。
- 規則包的資料結構有增（`SkillLimits` 兩個必填欄位、`BudgetRules.shield_max_hp_points`、原語與形狀的新欄位），照 1.2 屬「不升版號、舊紀錄的 `ruleset_hash` 對不上會被拒絕」的情況（HC-B、HC-4 系列同樣處理）。

## 8. 檢查

（交件前的完整檢查補在第 9 節。）

| 檢查 | 結束碼 |
|---|---|
| `trpg content check` | 0（704 個檔案、442 個技能通過預算與結構驗證） |
| `ruff check src tests`、`ruff format --check src tests` | 0 |
| `mypy src tests` | 0（1679 檔） |
| `lint-imports` | 0（14 kept） |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| 看門狗：每項的新測試檔 | 0 |
| 看門狗：`tests/content tests/narrative tests/engine tests/skillgen tests/api tests/roguelite tests/cli tests/llm tests/test_x10_fields.py tests/test_hardcoded_scan.py -n 8`（第 5 項之後） | 0（16237 passed、8 skipped） |
| 看門狗：`-m slow tests/cli/test_output_snapshots.py`（重產前） | 1：只有 14 個技能清單的鍵（預期中），重產後通過 |
| `pnpm -C client typecheck` | 0 |
| vitest `src/render/qIcon` | 0（193 passed） |
| vitest 全部（`pnpm -C client test`） | 0（393 檔、4822 passed） |
| `pnpm -C client build` | 0 |
| `scripts/check.py`、slow 的 parity 與 cli | 見第 9 節 |

為了跑前端，在 worktree 用 `corepack pnpm -C client install --frozen-lockfile` 裝了相依（照 lockfile）。

## 9. 交件前的完整檢查

照派工：全部 commit 後問開發 PM，依回覆決定（結果補在下方）。

## 10. 待 PM 決定

1. **影貓潛襲的隱蔽寫 2 回合（設計 1 回合）**（數值類）：設計寫「自己隱蔽 1 回合」，照公式只有 66.0%（形態固定 11 點＋隱蔽 1.5 點），低於 70%。進入時效果只能是施加狀態或推擊、冷卻折抵只有 30‰，沒有別的槓桿，所以照「70～100%、最保守」改成 2 回合（73.9%）。要照設計寫 1 回合，就得放寬它的預算下限（例如列進 `known_budget_exceptions`），或調整形態係數、隱蔽點數。
2. **巨人踐地的撞擊骰明寫 1d6**（數值類）：推開 1 格、撞擊骰不寫時 67.2%。把撞擊骰明寫成和核心規則預設相同的 1d6，實戰傷害完全不變，但預算每顆撞擊骰另計 1 點（`collision_die_points`）→ 75.5%。這等於「多付 1 點但沒有多拿東西」，真實強度還是約 67%。另一個選擇是推開 2 格（76.2%，和設計的 1 格不同）。我選了不改實戰行為的那個。
3. **進入時效果的命中擲骰在變身之後**（解讀類）：設計的順序是「變身 → 形態進入獎勵 → 進入時效果」，所以引擎在變身之後才對進入時效果擲命中。效果：形態的「下一次攻擊」獎勵（巨鵰命中 +2、貓暴擊 +2）會被進入時效果的命中擲骰用掉——如果那個進入時效果要擲命中。目前 4 招只有熊王怒吼（虛弱）、龍威降臨（恐懼）、巨人踐地（推擊）會擲，熊、龍、巨人都沒有「下一次攻擊」獎勵，所以實際沒有影響；影貓潛襲給自己隱蔽不擲命中，貓的暴擊 +2 照樣留給下一次攻擊。之後若有巨鵰或貓的高階化身對敵人施加狀態，要決定獎勵要不要留到真正的攻擊。
4. **新 4 招的閃現**（解讀類，沒改程式）：閃現的「變身姿態只出修正類（形態幅度）」規則是照 10 種基本形態寫的。新 4 招有時出不到幅度選項（例：龍威降臨 87.9% 加幅度會超過 100%），有時出的結果效果數是 2。測試只把 BAL-2c、BAL-10b 的形態對照限定在 10 招基本形態；新 4 招的閃現沒有專門的規則。要不要給高階化身專屬的閃現（例如進入時效果的回合 +1），另排。
5. **升階**（解讀類）：4 招新招與野性連擊、化形震地、原形歸一升到 5 階都還在區間內；**化形守護升到 5 階會掉到 61.8%**：`max_hp_permille` 沒有旋鈕（`knob: none`，避免組合器與 LLM 用它），升階不會把 150‰ 放大。GS-2 的 7d8 版本升階會放大骰子。要的話給它一個只供升階用的旋鈕，或升階時豁免下限。
6. **工坊選項與 LLM 往返不收這 8 招**：開發用的技能工坊選項（`draft_options`）沒有實心環形、天生武器、看最大 HP 的護盾、進入時效果，所以 `test_every_shipped_skill_fits_the_options` 跳過這 8 招；LLM 的 `proposal_from_skill` 遇到帶進入時效果的技能丟 `ValueError`。規格說組合器與 LLM 不主動用新參數，這兩處照「不開放」處理。要開放另排。
7. **護盾的 `dice` 在 LLM 提議模型變選填**：因為 `dice` 改成「填了 `max_hp_permille` 就不必填」（`required_when`），提議模型裡護盾的 `dice` 不再是必填，缺了由 rules 階段報「缺少必要參數」。LLM 的提示詞與 schema 快照、Mock 測試都沒變紅。
8. **野性連擊的 `scaling_source` 只限非武器技**：規格只寫「條件是在形態中」，我另外擋了武器技（武器技看手上武器）、第二縮放屬性與專精（天生武器已有自己的雙屬性取法），是保守做法。
9. **化形震地、原形歸一變強**：改成實心環形 2 後預算從 73% 升到 87%（數值沒動，範圍變大、倍率變高）；化形震地的擊倒也會打到貼身的敵人。數值由使用者在工坊調。
10. **新 4 招沒有裝在任何 build 或敵人上**：同 GS-2，列進 `test_coverage.py` 的 `_POOL_ONLY`；AI 會不會用、多常用沒驗證（沒跑模擬）。
