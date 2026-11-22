# Phase GS-2 報告：形態補手寫技能（#172）

依據：`docs/phases/PhaseGS-2計畫.md`；`docs/玩法決定紀錄.md` #172；`docs/design/06-技能.md` 6.30「形態池名單」最後一點；`docs/形態補招提案.md`。
基準：main `0be842398`。分支 `worktree-agent-a3278752ad50c79e6`，沒 push。
沒動 `docs/design/`、`config/`、`llm.toml`、`CLAUDE.md`、`.claude/`、`content/forms.yaml`、`content/sim/builds.yaml`，沒改現有招式或數值，沒加原語，沒跑模擬。

## 1. 結果

**8 招只做出 4 招**：4 招「高階利用者」做出來了。4 招「高階化身」用現有原語做不出來，照規格第 2 項跳過（見 3）。

## 2. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 新增技能檔 | `cd451661e` | `content/skills/skill_form_{wild_flurry,quake,primal_return,guardian}.yaml`；登記處：招數 434 → 438（`test_skill_scaling.py`、`test_skill_icon_art_qi2a.py`）、技能檔 431 → 435（`test_tuning_fields_nw2a.py`）、`test_coverage.py` 的 `in_form` 從「沒人用」清單拿掉 |
| 1（補） | `318c0e52b` | 第一版為了「每招都要被裝備」加了參考 build `build_form_high`；改照 KW-2、SK-3b 前例，放進 `test_coverage.py` 的 `_POOL_ONLY`，`builds.yaml` 還原成基準 |
| 2 測試 | `c6a7e477e` | `tests/engine/test_form_high_gs2.py`（15 個） |
| 3 快照 | `261686ca7` | 圖示夾具、CLI 快照、parity 夾具、前端圖示測試的招數（見 5） |
| 3（補） | `f8da207a5` | `test_coverage.py` 註解換行（ruff E501） |
| 2（補） | `7c589af05` | `test_calibrate.py`：階級預算校準原本寫死「只有 1、2 階有手寫技能」，現在 1～4 階都有；每階的合格區間仍包含 `tier_budget` |
| 報告 | 本 commit | |

## 3. 跳過的 4 招（高階化身）

| 招 | 階級／稀有度 | 為什麼做不出來 |
|---|---|---|
| 熊王怒吼 | 3 階史詩 | 提案是「進入熊形態，再讓身邊 1 格的敵人虛弱」。 |
| 影貓潛襲 | 3 階稀有 | 提案是「進入貓形態，再讓自己隱蔽 1 回合」。 |
| 巨人踐地 | 4 階稀有 | 提案是「進入巨人形態，再把身邊 1 格的敵人推開 1 格」。 |
| 龍威降臨 | 4 階史詩 | 提案是「進入龍形態，再讓身邊 2 格的敵人恐懼」。 |

共同原因：`enter_form` 在 `skill_primitives.yaml` 標成 `sole_effect: true`、`allowed_shapes: [self]`，`SkillDef` 也檢查「enter_form 只能是姿態唯一的效果」。所以一招化身不能再帶第二個效果，形狀也只能是自己。看過的替代做法都不合：

- 複合技第二段（`followup`）：`after_action` 的第二段只能是自身位移；`on_hit`、`on_kill` 第一段要有傷害；`delayed` 會變成下回合才生效，不是「進入時」。
- `enter_form` 的 `magnitude_permille` 只會放大形態本身的加成與進入獎勵，等於改形態數值，提案明說形態本身的數值不變。
- 改 `forms.yaml` 的進入獎勵：規格不准。

要做的話得動引擎或原語規則（例如讓 `enter_form` 可以帶一個「進入時」的附帶效果，並定它的形狀與預算），屬於規則類，交 PM 排。

## 4. 做出來的 4 招

| 招（ID） | 階級 | 稀有度 | 骨架 | 內容 | 費用 | 預算比例 |
|---|---|---|---|---|---|---|
| 野性連擊（`skill_form_wild_flurry`） | 3 | 稀有 | 連段 | 只能在形態中施放；相鄰單體 4d8 物理傷害 × 2 下，各擲命中；力量 | 2 AP、法力 60、冷卻 2 | 70.6% |
| 化形震地（`skill_form_quake`） | 3 | 史詩 | 範圍 | 環形半徑 2 的敵人 1d10 物理傷害，在形態中 +30%；在形態中命中的敵人倒地（擊倒對抗）；體質 | 2 AP、法力 80、冷卻 3 | 73.3% |
| 原形歸一（`skill_form_primal_return`） | 4 | 史詩 | 範圍 | 只能在形態中施放；先解除形態（照常冷卻 2 回合），再對環形半徑 2 的敵人 3d8 物理傷害；體質 | 2 AP、法力 100、冷卻 3 | 73.2% |
| 化形守護（`skill_form_guardian`） | 4 | 史詩 | 光環 | 只能在形態中施放；自己與曼哈頓 1 格內的友方得到護盾 7d8＋感知 × 0.5（2 回合）；感知 | 2 AP、法力 80、冷卻 3 | 76.7% |

- 每招都有繁中 `concept`、`cast_flavor`，名字照 06 6.30；都是 `category: spell`、`weapon_req: any`，沒有 `icon_prop`（圖示照推導表）。
- 骰子的選法：用腳本把骰子階梯（1～8 顆、4／6／8／10／12 面）全部試一遍，取比例 ≥ 70% 裡最低的一組。原形歸一的 2d12（70.4%）和 3d8（73.2%）差不多，取 3d8，和解形爆發同一種骰型，也離下限遠一點。
- 原形歸一一開始沒有冷卻，被互斥規則「無冷卻的大範圍」（環形半徑 2）擋下，所以加了冷卻 3。化形守護的範圍光環也在同一條互斥規則裡，所以也有冷卻。
- 「只能在形態中施放」用技能層級的條件 `in_form`（預算 ×0.6，嚴苛）。所以野性連擊、化形守護的骰子比同階招大很多（4d8 × 2、7d8），這是預算公式算出來的。
- 關鍵字（只看專屬規則）：4 招都帶「形態」；化形震地另外帶「倒地」。

## 5. 受影響的既有功能（開工盤點）與快照

- **形態池**：`keyword_pools(...)["form"]` 由內容推導（技能條件 `in_form`、效果的 `form_bonus_permille`、`leave_form`）。新招自動進池，不用改程式。
- **三選一指定形態**：`candidates._pool` 收階級相符、非傳說、帶關鍵字的手寫技能，不看稀有度。組合器照舊不做形態（`composable: false`）。所以 3、4 階指定形態的題，現在從手寫池出這 4 招。`recipe_census.py` 只跑組合器，看不到手寫池，所以這段改用測試證明（`test_offers_pinned_to_form_have_skills_at_tiers_three_and_four`，3、4 階各 20 個種子）。
- **起始技能**：`is_starter_skill` 只收 1 階，新招自動排除；開局選「形態」照舊只給 1 階化身。
- **技能清單與 CLI 快照**：預測只有含技能清單的鍵會變。實測只有 `skills_list` 和 `skills_show_all/03`～`/15` 變（新招照 ID 排序插進去，後面的分段一起移位）。用 `UPDATE_CLI_SNAPSHOTS=1 ... -k "skills_list or skills_show_all" -n 0` 只重產這些鍵。
- **前端技能卡夾具**：`scripts/export_client_fixtures.py` 重產後 0 差異（`skillCards.json` 不含全部內建技能）。
- **技能圖示夾具** `client/src/render/fixtures/skill_icons.json`：`uv run python -m tests.narrative.icon_fixture` 重產，逐鍵比對只多了這 4 招。前端 `qIconSkills.test.ts` 招數 434 → 438；`qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE` 加 4 招。
- **parity 夾具** `tests/skillgen/fixtures/refactor_3wr2.json`：非 slow 的 `test_fixture_covers_every_builtin_skill` 要求每招都有 `complete`、`retier`。我先在記憶體裡整份重產，和現有夾具比對：`complete`、`retier` 都只多這 4 招，原有的 0 筆改變；`flash` 是「ID 排序後等距取約 40 招」，多 4 招後取樣點移位，整份重產會把 123 筆換成 126 筆（只有 30 筆共同，30 筆都相同）。所以只把 4 招的 `complete`、`retier` 加進去，閃現對照留原樣（`docs/dev/上手-內容資料與模擬.md` 第 26 點、52 點的做法）。規格寫的是整份重產；開發 PM 回覆（2026-11-22）照這個做法，規格那句以此為準。
- **434 招逐招預算**：基準 `0be842398` 的 `content/` 和本分支，逐招 dump `skill_budget`（比例與整份明細）：原有 434 招 different=0，只多這 4 招。

## 6. 檢查

| 檢查 | 結束碼 |
|---|---|
| `trpg content check` | 0（700 個檔案、438 個技能通過預算與結構驗證） |
| `ruff check`、`ruff format --check`（改到的 Python 檔） | 0 |
| `mypy`（新測試檔、`test_coverage.py`） | 0 |
| `lint-imports` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| 看門狗 `tests/engine/test_form_high_gs2.py` | 0（15 passed） |
| 看門狗 `tests/cli tests/narrative/test_skill_icon.py tests/api/test_client_fixtures.py`（重產前） | 1：只有 `test_client_fixture_is_current`（圖示夾具，預期中），重產後通過 |
| 看門狗 `-m slow tests/cli/test_output_snapshots.py`（重產前） | 1：只有 `skills_list`、`skills_show_all` 14 個鍵（預期中），重產後通過 |
| 看門狗 `-m slow tests/skillgen/test_refactor_parity.py` | 0（935 passed，加 4 筆前後都過） |
| 看門狗 `tests/skillgen tests/roguelite tests/llm tests/content tests/narrative` ＋形態引擎測試＋前端夾具 | 1：只有 `test_calibrate.py::test_every_shipped_skill_is_inside_its_tier_window`（寫死「只有 1、2 階有手寫技能」）；改成 1～4 階後 0（9461 passed、7 skipped） |
| vitest `src/render/qIcon` | 0（193 passed） |
| `scripts/check.py`、slow 測試 | 見 7 |

## 7. 交件前的完整檢查

照派工：全部 commit 後問開發 PM，依回覆決定（結果補在下方）。

## 8. 待 PM 決定

1. **4 招高階化身沒做**（規則類）：要做得讓 `enter_form` 能帶「進入時」的附帶效果，或另加一種原語。這要改原語規則和預算，需要使用者或玩法 PM 定，再另排一段。沒做之前，3、4 階的形態池只有利用者，沒有新的化身招。
2. **「周圍 2 格」維持環形半徑 2**（開發 PM 回覆 2026-11-22：要涵蓋距離 1～2、不含自己，有這種形狀就換，沒有就維持 ring 2 寫進報告）：化形震地、原形歸一用 `ring radius: 2`，只打切比雪夫距離「剛好 2」的那圈 16 格，**貼身相鄰的敵人打不到**。查過 `skill_shapes.yaml` 全部 13 種形狀，沒有能涵蓋 1～2 格的：範圍骨架只收 line、cone、cross、square3、ring、chain；`square3` 固定 3×3（只到 1 格）；`allies_in_radius`（含自己、曼哈頓半徑）只給光環骨架；`cross` 臂長 2（內建專用）只有上下左右各 2 格，斜角相鄰的敵人打不到。所以維持 ring 2，數值不動。要真的涵蓋 1～2 格，得加形狀（例如給範圍骨架一個不含自己的半徑形狀）或放寬骨架的形狀清單，屬規則類；或者退一步改用十字臂長 2，再重調骰子。
3. **parity 夾具只加 4 筆，沒有整份重產**（已定：開發 PM 回覆 2026-11-22 照做，規格那句以此為準）：整份重產會把閃現對照的取樣整批換掉（123 筆 → 126 筆，只有 30 筆共同），等於放寬「重構前後等價」的檢查。所以只加新招的 `complete`、`retier`；這兩類整份重產的結果和現在相同。
4. **化形守護的護盾看骰值，不看最大 HP**（解讀類）：提案寫「護盾量看最大 HP，所以熊、龍比較厚」。現有護盾原語只有「骰值＋縮放屬性 × 0.5」，沒有看最大 HP 的參數，所以先用 7d8＋感知。縮放屬性由護盾主題定成感知（`skill_scaling.yaml`），不是體質。要看最大 HP 得加原語參數，屬規則類。
5. **野性連擊「用天生武器的屬性」**（解讀類）：法術技的縮放屬性是寫死的，沒辦法跟著形態的天生武器走。先用力量（同化形撲擊）。貓（敏捷）用起來會吃虧。
6. **數值都取「比例 ≥ 70% 裡最低」**：野性連擊 70.6% 貼著下限，使用者在工坊動代價（例如拿掉冷卻）就可能掉到過弱。「在形態中」條件是 ×0.6，所以兩招只能在形態中施放的骰子偏大（野性連擊 4d8 × 2、化形守護 7d8）。這是預算公式的結果，沒有另外調。
7. **新招沒有裝在任何 build 或敵人上**：照 KW-2、SK-3b 的前例列進 `_POOL_ONLY`，`builds.yaml` 是模擬回歸範本，不為示範改動。所以 AI 實際會不會用、多常用，還沒驗證（沒跑模擬）。

## 開發 PM 裁定（2026-11-22）

合併進 main（`--no-ff`，a5f839192）。合併後的 tree 和實作者的 `check.py` 戳記相同，push hook 略過了完整檢查。`check.py` 與 slow 的 parity、cli 都是 0。

待 PM 決定的 5 件：
1. **4 招高階化身**：使用者選 A，原話「改規則再補（建議）」：讓 `enter_form` 能帶進入時的效果。玩法 PM 寫好細節後另排一小段，改引擎與 schema 並補 4 招。
2. **涵蓋 1～2 格的範圍形狀**：這是規則類，併進第 1 項那段一起問玩法 PM。在那之前，化形震地、原形歸一照現在的環形半徑 2，打不到貼身的敵人。
3、4. **化形守護看最大 HP、野性連擊跟天生武器屬性**：使用者原話「一起改成原設計（建議）」，併進第 1 項那段。
5. **數值貼著下限、AI 會不會用還沒驗證**：照做。數值由使用者在工坊調。AI 會不會用新招，等有 build 裝上再看，不另開段。
