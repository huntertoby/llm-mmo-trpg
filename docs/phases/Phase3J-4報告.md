# Phase 3J-4 報告｜形態內容與形態池

> 規格：`docs/phases/Phase3J計畫.md` 4.11；設計 `docs/design/06-技能.md` 6.30「形態池名單」。`LOG_FORMAT` 沒有變（仍 `/81`：沒有新事件或欄位）。技能 297 → 300。

## 做了什麼

1. **10 招「化身為〇」正式化**：名稱本來就是「化身為〇」，改的是階級與註解——1 階熊、貓、巨鵰、狼人；2 階惡魔、巨人、元素化身、暗影形態、樹人、龍（原本全是 1 階）。法術類別、`weapon_req: any`、費用只有姿態 1 AP 與維持費（沉默看形態類別，3J-1b 已做）。拿掉「測試用」註解。
2. **3 招主動利用者**（`in_form`，都是 1 階、稀有、法術類別、`weapon_req: any`）：
   - `skill_form_pounce` 化形撲擊：`dash` ＋ 3d4 物理傷害（單體射程 4，2 AP，6 法力、冷卻 3）；在形態中另加一筆 1d3。
   - `skill_wild_roar` 野性怒吼：周圍 1 格（ring 1）2d4 物理傷害＋虛弱 1 回合（2 AP，6 法力、冷卻 3）；在形態中另加一筆 1d2。
   - `skill_form_renewal` 化形回春：治療自己 2d4（1 AP，5 法力、冷卻 2）；在形態中另加一筆 1d2。
   - 「+30%」的實作方式見待決第 1 點。
3. **解形爆發（2 階）沒有做**：現有原語沒有「解除形態」效果（只有 `end_stance` 動作與換形態／姿態時的內部 `leave_form`），規格允許先不做。要做需要新增原語 `leave_form`（含冷卻、代價折抵、卡片句、工坊說明）。
4. **預算係數**：`content/skill_budget.yaml` 的 `form_coefficient_permille` 1000 → 800。十種形態的點數都是 11（`enter_form` 的 `base_points`），2 階可用預算 18 時只有 61.1%（過弱）；改 800 後 1 階 14×0.8＝11.2（98.2%）、2 階 18×0.8＝14.4（76.4%），十招都落在 70～100%。沒有動形態資料與 `base_points`。
5. **形態池補齊後拿掉暫時標記**：刪 `form` 的 `start_hidden`（欄位本身保留）；`test_keywords.py` 的 `EXTRA_KEYWORDS`／`EXTRA_NAMES` 併進 `KEYWORDS`／`NAMES`（另加 `COMPOSABLE`，因為 `form` 的 `composable: false` 讓組合器對它回 `ComposeError`）；`test_pools_24c.py` 改回 `short == {}`；`test_keyword_start.py` 兩處 `form` 例外刪除；`test_coverage.py` 的 `in_form` 允許清單刪除。
6. **AI 蓄力中不換形態**（`src/trpg/engine/ai/utility.py`）：新增 `_breath_locks_form`；單位有帶方向的 `charging` 狀態（定向蓄力）時，`skill_estimate` 對「進入形態」的技能回 `None`。AI 本來就不主動取消形態（`EndStance` 不評分），表格測試也斷言這點。
7. **開發起始包／靶場**：新增 `dev_beast`（獸變：單手劍＋形態、倒地關鍵字）與參考 build `build_form_user`（熊、狼人、撲擊、怒吼、回春；`reference: true`）。靶場原本就能裝備所有技能。`tests/content/test_coverage.py` 要求每個手寫技能都被 build 裝備，所以需要這個 build。
8. 重產：`skill_icons.json`（`tests.narrative.icon_fixture`）、`export_client_fixtures.py`（無變更）、CLI 快照（`cli_output_hashes.json` 只有 `skills_list`／`skills_show_all` 變；7 場戰鬥雜湊沒變）、`llm_propose_mock.txt`。技能數字面值 297 → 300（`test_skill_scaling.py`、`test_budget_cli.py`）。

## 驗收對照（4.1 第 9 點）

| 條件 | 證明 |
|---|---|
| 10 招階級、名稱、法術類別、不限武器、只有 1 AP | `tests/engine/test_forms_3j4.py::test_each_form_skill_is_the_named_spell_with_the_pool_tier`（10 個參數） |
| 10 招卡片＝實戰（卡片句＝資料、進入、維持費資源與數字） | `test_entering_and_upkeep_match_the_card`（10 個參數） |
| 3 招利用者：不在／在形態中，卡片骰數＝實戰 | `test_the_pounce_dashes_and_hits_once_outside_a_form_twice_inside`、`test_the_roar_hits_adjacent_enemies_only_and_the_form_adds_a_second_hit`、`test_the_form_renewal_heals_once_outside_a_form_twice_inside` |
| 池名單：形態池 1 階主動起始技能 ＝ 3 招；10 招進入技能是製造者 | `test_the_exploiters_belong_to_the_form_pool`；`test_each_pool_has_at_least_three_tier_one_starter_skills[form]`；`test_every_keyword_pool_has_at_least_three_active_exploiters` |
| 暫時標記已移除 | 上節第 5 點；`start_ids()` 含 `form`（`test_table_has_the_twelve_keywords_in_order`）；`test_every_keyword_pool_gives_a_starter_for_some_weapon` 全部關鍵字可達 |
| AI 蓄力中不換形態 | `test_the_ai_does_not_switch_forms_while_the_dragon_is_charging`（暫時停用修正會失敗，已驗證） |
| 預算 70～100% | `tests/skillgen/test_validate.py`、`test_calibrate.py`、`test_stamina_cost.py`、`test_proposal.py` 等全數通過 |
| 重播 | `trpg battle --map open_plain --ally-build build_form_user --seed 3` → `replay`：「重播驗證通過：119 個動作、320 個事件，最終狀態一致」；戰鬥中三招各出現 9／10／13 次紀錄 |

## 驗收指令

| 指令 | 結果 |
|---|---|
| `pytest -n 8 tests/engine` | 3645 passed |
| `pytest -n 8 tests/skillgen tests/roguelite tests/api tests/narrative tests/content` | 4236 passed、1 skipped（改 dev 起始包前）；改後 `tests/roguelite tests/api tests/sim tests/content` 2038 passed |
| `pytest -n 8 tests/sim tests/llm` | 193 passed |
| `-m "slow or not slow" tests/cli --timeout=3000 -n 8` | 預算總表字面值與兩個快照更新後，快照測試（`UPDATE_CLI_SNAPSHOTS=1`）7 passed；其餘 144 passed；dev 起始包相關再跑 9 passed |
| `corepack pnpm -C client test` / `build` | 111 files、1067 tests passed／建置通過 |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 通過（7 kept） |

沒有跑 `scripts/check.py` 與全量 slow 測試。

## 模擬摘要（不調數值）

`trpg.sim.keyword_sample` 的小樣本：從種子 0～399 挑開局關鍵字含「形態」的前 12 個樣本，各打 2 場（隨機地圖）。**24 場全部完成，0 場例外或動作上限**；我方勝率 66%（形態關鍵字 24 場；弱法杖組 focus 16% 屬於既有的法杖弱勢，近戰 91%、遠程 66%）。樣本數很小，只用來確認形態池的 build 跑得完，不作平衡依據。

## 待 PM 決定

1. **「在形態中 +30%」沒有精確做到（需玩法 PM 回覆）**：法術類別的傷害與治療不能用 `multiplier_permille`，條件加成只能多加一筆「條件成立才結算」的效果（同餘燼爆發的做法），而每一筆效果都會再加一次屬性加成（力量／體質／感知 × 0.5）。所以在形態中的實際加成是「另一筆骰子＋再一次屬性加成」，屬性 14 時約為 +45～60%，不是 +30%；我把追加骰縮到最小（1d3、1d2、1d2，骰子本身約 +25～30%）。要精確 +30% 有三條路：(a) 新增依據 `in_form` 的 `scaling.by`（改 content、引擎、卡片、工坊、預算規則）；(b) 條件效果支援 `multiplier_permille`（法術也可）；(c) 改成武器類別（但會吃化形專精的武器技 −20%，與設計相反）。建議 (b)。
2. **解形爆發（2 階）未做**：需要新原語 `leave_form`（先解除形態、照常冷卻、算代價折抵）。形態池目前主動利用者 3 招（剛好達標）、1 階起始技能 3 招；少了這招 2 階沒有利用者。
3. **預算係數 800**：是為了讓六個 2 階形態通過 70% 下限的最小改動（也可改成 `enter_form` 的 `base_points` 13，兩階都合格）。形態資料不動；平衡階段再看是否要讓 2 階形態更強。
4. 三招利用者是法術類別、花法力；化形撲擊與野性怒吼雖然是物理傷害，仍會被沉默擋住、也不吃武器技修正（刻意：避免被化形專精的 −20% 打到）。若要「物理形態中沉默擋不住」需另案。野性怒吼的縮放屬性用體質（物理元素的法術只能用力量／敏捷／體質）。
5. 化形撲擊用 `strike` 骨架（`displace` 骨架要求核心位移效果，衝鋒＋傷害會超過次要效果占比）。
6. `dev_beast`（獸變）起始技能是從形態池與倒地池各抽 1 招，形態池抽到的永遠是三招利用者之一（進入形態的姿態技能不是起始技能），所以開局拿不到變身技能本身——和規格「1 階熊、貓、巨鵰、狼人可當開局起始技能」不一致：現行起始技能的定義（`is_starter_skill` 要求 `kind == "active"`）排除姿態。要讓熊等直接當起始技能需改該定義（連帶影響其他姿態技能池）。
7. 形態池開局可選後，指定「形態」關鍵字且沒有武器限制的開局，起始技能只會是三招利用者，沒有變身技能就無法觸發「在形態中」加成；要靠之後的掉落／三選一取得形態技能。
8. 隨機組合器仍不產生形態技能（`composable: false`），3J-3 待決第 2 點維持現狀。
9. 沒有新增 `skill_evolution.yaml` 嫁接或工坊文字；技能標籤沒有新增 `form`（新技能沿用既有標籤 `mobility`／`area`／`debuff`／`heal`）。

## 複雜度類 noqa

沒有新增。`skill_estimate` 原本已在 `PLR0911`／`PLR0912` 邊緣，AI 規則併進既有的姿態判斷條件，沒有加分支。
