# Phase NW-2a 報告：數值工坊開放技能——後端

> 實作者：implementer agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhaseNW-2計畫.md`（`e9c68da4`）第 0～8、11、12 節；技術類 T1～T13 照規格「建議」（開發 PM 第八任 2026-11-12 定）。
> 規則類 **R1、R2 依使用者原話「照建議」**（2026-11-12，經專案 PM 轉達；開發 PM 已寫進本機 main 的規格 `d1778a8c`），做成最後一筆獨立 commit。
> 分支 `worktree-agent-a1b56163b788955c6`，從本機 main `a7ae957d` 起；未 push。只做 2a（後端），2b／2c 未動（前端只做讓型別檢查過的最小調整，見第 3 節）。

## 1. 做了什麼（交付逐條）

| 交付 | 內容 | commit |
|---|---|---|
| A7（核心） | `src/trpg/sim/skill_probe.py`：`SkillProbeJob`（地圖、種子、我方 build、「裝到 build」、受測招）、`MapBattle`、`SkillWatch`（`cast|<陣營>|<招>`＝`SkillUsed`、`turns|<陣營>|<招>`＝裝了這招的單位的 `TurnStarted`）、`inject_skills`（只換內容庫副本的 build 技能欄：已裝不變、有空位加在最後、滿了換同類最後一招）、`probe_battle`／`probe_task`（沿用 `boss_probe.library_for`）、`skill_tally`、`map_jobs`、`probe_maps`（有 `encounter`、去掉 `test_*` 與 `training_range`：14 張） | `fb444231` |
| A1、A2 | 白名單 schema：`TuningTarget.kind` 加 `skill`、`TARGET_MODELS["skill"]=SkillDef`；`TuningField.kind` 加 `dice`／`range`／`skill_ids`，選填 `effect_types`／`existing_only`／`kinds`；`effect_sites` × `effect_fields` 交叉成完整路徑（巢狀位置寫在 YAML）；葉節點型別依 `kind` 檢查；`FORBIDDEN_SEGMENTS` 加 3.2 的技能結構欄位。`content/tuning_fields.yaml` 加技能對象（28 個技能層級欄位、9 個效果位置 × 25 個效果欄位）與單位的 `skills`、`phases[*].skills`。`yaml_patch`：骰子純量替換、整個清單換掉（流式換字面、區塊式照縮排重寫、區塊式改空清單寫 `[]`、範圍內有註解擋）、`patch_exception_list`（只動 `known_budget_exceptions` 那一行與上方工坊註解行） | `101f4fb8` |
| A3～A6、A8 | `check.py`：依欄位種類轉型（整數／`NdM`／ID 清單，ID 清單可打逗號分隔文字）、`weapon` 射程唯讀、引用的招要存在、`SkillDef` 單檔驗證（`loc` 對到欄位，model 層級錯誤依訊息裡的欄位名對）、整包錯誤以單位 ID 對到欄位（玩家這一邊裝敵人專用招）。新 `skills.py`：預算結果（同 `trpg skills budget`）、例外清單附帶改動與自動移除、分組預覽、常用預設組 4 組。`objects.py`：技能清單（篩選欄位＋1 階預算比例）、表單（效果欄位標「效果 N（原語中文名）：」、原語／形狀表的範圍、唯讀原因）、使用這招的單位與 build。`service.py`／`routes.py`：`POST /skills/{id}/budget`、`POST /skills/group-preview`、`GET /skills/presets`、`GET /objects?kind=skill`、`POST /drafts/{name}/apply` 加 `confirm_budget`；`sim_jobs.py` 加地圖戰（`start_map`、`summarize_map`、地圖戰每場秒數另記）；`POST /sims` 加 `scenario: boss|map`；`writeback.py` 的 commit 訊息（T13：多招 `tune(skills×N)`、內文「預算例外：…」）；差異表列附帶改動 | `d5ccced5` |
| A9（OpenAPI） | `client/openapi.json`、`client/src/api/schema.d.ts` 重產；前端只做型別調整（見第 3 節） | `290ba2ea` |
| A9（文件） | 本報告；上手筆記第七節（技能對象、例外閘門、R1／R2、收編清單 5.8） | 報告 commit |
| R1、R2 | #149 判定搬到 `trpg.content.enemy_moves`（測試改呼叫，斷言不變）；工坊招式組低於下限 → `needs_confirm_min_moves` 警告、不勾 409、勾了寫回並在 commit 內文加「#149 例外：<單位>（<哪幾段>）」；技能表單 `notes_zh` 第 1 行固定提示升階重算、第 2 行列出實戰用升階版的單位（等級→階級）；`TuningSkillUser.tier` | 最後一筆 commit |

**給 NW-2b 的介面**（前綴 `/api/tuning`；型別在 `client/src/api/schema.d.ts`）：

| 端點 | 說明 |
|---|---|
| `GET /objects?kind=skill` | `TuningObjectSummary.skill`＝`TuningSkillFacets`（`tier`、`category`、`weapon_req`、`ap_cost`、`kind`、`enemy_only`、`has_condition`、`shape`、`ranged`、`tags`、`budget_ratio_permille`）；單位的 `skill` 是 `null` |
| `GET /objects/skill/{id}` | `fields[]` 多 `limit_min`／`limit_max`（原語或形狀表的範圍）、`readonly_zh`（例：武器射程）；`value` 可能是整數、骰子字串、ID 清單或 `"weapon"`；`notes_zh`（R2 提示）、`used_by[]`（`kind`、`id`、`name_zh`、`where_zh`、`tier`）、`skill` |
| `POST /skills/{id}/budget` | body `TuningBudgetIn{changes}`（只取這招的檔；可省略）→ `TuningBudgetResult`（`ratio_permille`、`ratio_text`、`min/max_ratio_permille`、`verdict` ok/over/weak/error、`verdict_zh`、`variants[]`、`segments[]`、`violations[]`、`known_exception`、`field_errors`） |
| `POST /skills/group-preview` | body `TuningGroupIn{skills?, filter?, target, op{kind: set/add/scale_permille/ladder, value}}`；`target`：`ap_cost`、`cost.stamina`、`cost.mana`、`cost.cooldown`、`shape.range`、`damage_all`、`damage_base`、`damage_conditional`；回 `rows[]`（`changes` 可直接放進草稿、前後 `*_ratio_permille`、`verdict`、`skipped_reason_zh`）；沒篩選也沒勾、超過 100 招、勾了不存在的招 → 422 |
| `GET /skills/presets` | 常用預設組（1 階遠程武器技、1 階近戰武器技、1 AP 箭類、2 AP 條件型） |
| `POST /drafts/{name}/check` | 回應多 `needs_confirm_budget[]`（要勾「我確定」的招）、`side_changes[]`（例外清單加入／移除）、`needs_confirm_min_moves[]`（R1） |
| `GET /drafts/{name}/diff` | 多 `side_changes`；`text` 含 `skill_budget.yaml` 的那一行 |
| `POST /drafts/{name}/apply` | body 可給 `TuningApplyIn{confirm_budget, confirm_min_moves}`；要恰好等於驗證回的那幾個，否則 409（訊息中文） |
| `GET /sims/options` | 多 `maps[]`、`map_default_seeds`（24）、`map_seconds_per_battle` |
| `POST /sims` | `scenario: "map"` 時：`maps`（1～3 張）、`seeds`（每張圖）、`allies`（build，同 `--ally-build`）、`probe`（空＝草稿改到的招）、`inject[{build, skill}]`（沒給 `allies` 時就用這些 build）；結果在 `TuningSimJob.map_result`（`before`／`after` 的 `n`、`wins`、`rounds`、`allies`、`downed`、`skills[{skill, team, casts, turns, battles, small}]`、`maps[]`；`flips`；`before_cached`） |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 1 | 第 8 節 T-A1～T-A10 全過 | 見下表 |
| 2 | 每次 commit 前 ruff、format、mypy、lint-imports、相關測試 | 全 0 |
| 3 | 實機走一遍 | 屬 2b；本段以服務層＋假 repo 走完整條（第 5 節），並用服務層跑了一次真的地圖戰（第 4 節） |
| 4 | `trpg content check`、一場紀錄＋重播 | 結束碼 0；`content check` 輸出和 `a7ae957d` 的 `content/`（`git archive` 解到暫存區）逐字相同，只差第 1 行的資料夾路徑；`trpg battle --map open_plain --seed 7` 0、`battle replay` 0（91 個動作、383 個事件，最終狀態一致） |
| 5 | 實測數字與沒驗證的 | 第 4、5 節 |

| 測試 | 檔案 |
|---|---|
| T-A1 白名單 | `tests/content/test_tuning_fields_nw2a.py`（401 個技能檔都合 schema、每個展開路徑對回白名單；`effect_types` 都是原語；`ap_cost` 不給被動、`stance_upkeep` 只給姿態、`magnitude_permille` 只給已寫的；開場階段不展開 `skills`；結構欄位與型別不對的路徑會報錯；未知原語會報錯） |
| T-A2 字面替換 | `tests/api/tuning/test_yaml_patch_nw2a.py`（hypothesis 400 例：全部 401 個技能檔 × 每個展開欄位，整數與骰子，`difflib` 只動一行、註解一行不少；流式／區塊式效果、`cost` 插入冷卻再清空逐位元組回原樣；骰子 `2x6`、加引號擋；單位 `skills` 流式＋行尾註解只動那一行；`phases[i].skills` 區塊式重寫、改空 `[]`、刪除、再插入；清單內有註解擋；例外清單加入兩招再移除逐位元組回原樣、手寫的行尾註解不動） |
| T-A3 預算 | `tests/api/tuning/test_skills_nw2a.py::test_budget_numbers_match_the_cli`（20 招：變奏 4、複合 4、被動 3、姿態 2、陷阱 2，其餘主動；比例文字、判定、每個變奏的比例與判定、違規有無都和 `print_skill_budget` 的輸出相同）、`test_budget_follows_the_change_direction`（火焰箭矢 800→900 比例變大、→700 變小、→1300 超出且有 `budget.over`、打錯字回欄位錯誤） |
| T-A4 寫回閘門 | `tests/api/tuning/test_writeback_nw2a.py`（假 repo：超出不勾 → 409、勾錯 → 409、兩個檔都不變；勾了 → `skill_budget.yaml` 多一筆與註解行、commit 只含兩個檔、內文有「預算例外」；之後 `test_range_budget` 的同一個判定成立；調回區間 → 自動移除、兩個檔逐位元組回到原樣、內文有「預算例外移除」；在清單裡而回到區間的招移除、其他例外不動；多招 `tune(skills×2)`；招式組寫回再還原逐位元組相同） |
| T-A5 分組 | `test_skills_nw2a.py`（850×1100÷1000＝935、502.5→503、501.5→502、負數；階梯走一級、不在階梯上取最近一級、到頂跳過；基礎／條件段／全部只動對的效果；骰子不能乘倍率而跳過、骰子 ±1 級 1d8→2d4；AP 夾到 3、沒冷卻只能「設定」、武器射程跳過；沒篩選 422、超過 100 招、同輸入兩次相同、依 ID 排序） |
| T-A6 非法值 | `test_skills_nw2a.py::test_illegal_values_carry_reasons_and_paths`（`ap_cost: 0`、`cost.cooldown: 7`、`effects[0].dice: 2x6`、`multiplier_permille: 0`、`shape.range: 99`、武器射程改數字、`skills` 有不存在的招、重複、武器不相容——都帶中文原因、對到那個欄位）；玩家這一邊裝敵人專用招：內建開放的單位都不是玩家這一邊（build 隊友是 `sim_*`，不開），所以用假白名單打開 `sim_companion_fighter` 測，錯誤（`sim/builds.yaml` 的 `ContentError`）對到 `skills` 欄位 |
| T-A7 #149（R1） | `tests/api/tuning/test_rules_r1_r2_nw2a.py`（內建沒有低於下限的；灰燼之心第 2 階段改成 2 招 → 警告 `ashen_heart/breath=2`、不勾 409、勾錯 409、檔案不變、勾了 → commit 內文「#149 例外：ashen_heart（ashen_heart/breath=2）」）；`tests/content/test_enemy_skill_count_149.py` 改呼叫搬家後的函式，14 項照過 |
| T-A8 skill_probe | `tests/sim/test_skill_probe.py`（7 項：同參數兩次相同；tally 和自己逐場數 `SkillUsed`／`TurnStarted` 相符、`skill_tally`＝逐場相加；「裝到 build」不改原內容庫與 `builds.yaml`；地圖清單）；`tests/api/tuning/test_sim_map_nw2a.py`（假的每場函式：彙總、翻轉、施放率分子分母、改前快取命中；參數驗證） |
| T-A9 digest | `test_skills_nw2a.py::test_changing_a_skill_changes_all_three_digests`（改一招三個 digest 都變；不套改動的複本三個都不變） |
| T-A10 | `lint-imports` 14 kept；`tests/test_architecture.py` 過（沒有新的直接走訪 `library.skills`，不需新登記 `LIBRARY_SKILLS_ITERATION_ALLOWED`）；`trpg content check` 逐字相同（上表） |
| R2 | `test_rules_r1_r2_nw2a.py::test_skill_form_shows_the_retier_note`（界隙閃擊：提示第 1 行、碎晶之主 3 階；火焰箭矢：新手弓手 1 階不列） |

**交件前的測試（結束碼分開記）**

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `ruff check .`／`ruff format --check .`／`mypy`／`lint-imports` | 0／0／0／0 | 1499 個原始檔；14 kept, 0 broken |
| `pytest -q tests/api/tuning tests/content/test_tuning_fields*.py tests/content/test_enemy_skill_count_149.py tests/skillgen/test_range_budget.py tests/sim/test_skill_probe.py tests/sim/test_boss_probe.py tests/test_architecture.py tests/content/test_loader.py tests/api/test_openapi_snapshot.py tests/api/test_client_fixtures.py -n 8` | 0 | 222 passed |
| `pytest -q tests/content -n 6` | 0 | 2989 passed |
| `trpg content check` | 0 | 662 個檔、404 個技能 |
| `trpg battle --map open_plain --seed 7`／`battle replay` | 0／0 | |
| `corepack pnpm -C client typecheck`／`test`／`build` | 0／0／0 | vitest 308 檔 3976 項 |

沒跑：完整 `scripts/check.py`、`tests/cli/test_output_snapshots.py -m slow`（本段沒動 CLI 與內容）、大型模擬。

## 3. 改寫的既有測試與其他既有檔

- `tests/api/tuning/test_yaml_patch.py::_concrete_cases`：舊「單位每個白名單欄位都餵整數」→ 新「只取 `int`／`permille` 欄位」（招式組 `skill_ids` 另在 `test_yaml_patch_nw2a.py` 測）。斷言不變。
- `tests/api/tuning/test_routes.py::test_objects_and_fields`：舊 `heart == {kind, id, name_zh, category, file}` → 新多一鍵 `"skill": None`（單位沒有技能篩選欄位）。
- `tests/content/test_enemy_skill_count_149.py`：`MOB/ELITE/BOSS`、`REGIONS`、`EXEMPT`、`_first_season`、`_phase_counts`、`_shortfalls` 改從 `trpg.content.enemy_moves` 匯入（內容逐字搬過去，`EXEMPT` 變 `frozenset`）；14 項斷言不變、照過。
- OpenAPI：`client/openapi.json`、`schema.d.ts` 重產。受影響的既有部分：`TuningFieldView.kind` 多三種、`value` 變成整數／字串／字串清單、`TuningChangeIn`／`TuningChangeView`／`TuningDiffRow` 的 `old`／`new` 同上、`TuningObjectSummary`／`Detail.category` 多 `skill`、`TuningSimRequest.boss` 變選填並多 `scenario` 等、`TuningSimOptions`／`TuningSimJob`／`TuningCheckResult`／`TuningDiff` 多欄位；`post_apply` 多選填 body。其餘全是新增（`/skills/*` 與約 20 個 `Tuning*` schema）。
- 前端（只為型別檢查過，畫面行為不變）：`client/src/tuning/model.ts`（`Edit.old` 與 `valueText` 收新的值型別：清單用「、」接、`weapon` 顯示「武器射程」）、`client/src/screens/TuningScreen.tsx`（開頭目戰時帶 `scenario: "boss"`）、`client/src/tuning/tuning.test.ts`（選項夾具補兩個新欄位）。
- 沒有重產任何 CLI 快照、前端夾具或 parity 夾具；`content/` 除了 `tuning_fields.yaml`（不進 digest）沒動任何內容。

## 4. 實測數字（Windows 11、16 邏輯核心；暫存區腳本，服務層直呼）

| 項目 | 數字 |
|---|---|
| 預算端點（`TuningService.budget`，火焰箭矢，20 次平均） | 19.1 毫秒（加一筆改動含單檔驗證約 130 毫秒） |
| 整包驗證（改技能，含例外附帶改動） | 第一次 3.83 秒（含複製基底）、之後 1.26 秒 |
| 地圖戰 24 場（`bandit_lair` × 24 種子，`build_ranged` 裝火焰箭矢，800→900），改前＋改後 48 場，程序池 4，第一次含 spawn | 25.4 秒（約每場 2.1 核心秒） |
| 單場地圖戰（子 agent 量，已載入內容庫） | 0.44～1.21 秒（14 張圖） |
| 技能清單（401 招含 1 階預算比例） | 0.16 秒 |

地圖戰冒煙結果（**不是平衡結論**）：勝 7/24 → 8/24、翻轉 2／3、我方火焰箭矢施放 62/100 → 76/95（每回合）、敵方 19/73 → 20/69。

## 5. 安全措施對照

| 措施 | 怎麼測 |
|---|---|
| 超出區間不勾不能寫回、檔案不變 | 假 repo（`test_writeback_nw2a.py`） |
| 勾的和實際超出的不符 → 409 | 假 repo |
| 例外清單只動那一行與工坊註解行 | 單元（`test_yaml_patch_nw2a.py`）＋假 repo 逐位元組 |
| 回到區間自動移除（含手寫的例外） | 假 repo＋單元 |
| 寫回只在 main、前置檢查、備份、對真的 content 再驗、只 commit 那幾個檔 | 沿用 NW-1a（`skill_budget.yaml` 也在要改的檔裡一起檢查「沒有未 commit 改動」） |
| #149 下限不勾不能寫回 | 假 repo（R1） |
| 地圖戰「裝到 build」不寫檔 | `tests/sim/test_skill_probe.py`（`builds.yaml` 的 mtime 與內容不變） |

**沒驗證的**：主資料夾與實機 `trpg serve` 的寫回（規定不能做；實機走一遍屬 2b，做法照上手-內容 第七節坑 5）；使用者 git hook／簽章；碎晶之主與其他地圖的地圖戰只跑了 `bandit_lair` 一張（子 agent 另把 14 張各跑一場量秒數）；分組改的「放進草稿」由前端做（2b），後端只驗了預覽的 `changes` 能直接放進草稿驗證。

## 6. 請使用者試用的步驟

2a 沒有畫面；2b 合併後照 NW-1b 的入口。PM 可先用 API 文件試：`TRPG_TUNING=1 TRPG_SAVE_DIR=<暫存> uv run trpg serve --port 8157` → `http://127.0.0.1:8157/docs` 的 `tuning` 區（**寫回只在 worktree 的 clone 試，不要在主資料夾**）。

## 7. 待 PM 決定

1. **效果層級的欄位一律「只有已寫的才展開」**（規格 3.1 只對幾個欄位寫了「只有已寫的」；其他像 `flat_bonus`、`duration` 沒寫時插入等於多一個機制，照最保守做）；`crit_range`、`damage_permille`、形狀參數、`condition.permille`、`trigger.*`、`trap.rounds`、`followup.shape.*` 也一樣。要放寬只改 `content/tuning_fields.yaml` 的 `existing_only`。（規格 3.1）
2. **變奏的預算超出區間不能用「我確定」寫回**：`known_budget_exceptions` 只豁免主型態的 `budget.over`／`budget.weak`（`library_violations`），變奏的違規規則是 `variant.<id>.budget.*`，照舊算錯；`test_range_budget` 的「恰好等於」也只看主型態。要讓變奏也能例外得改 `library_check`（規則問題）。（規格 5.3「含變奏」）
3. **已在例外清單、改完仍超出的招不必再勾**（已經是例外）；只有新超出的要勾。（規格 5.3）
4. **R2 的「實戰階級」只算遭遇表地點的 `level_min`、懸賞與賽季頭目等級**，沒算世界事件的 +1 與移動遇敵以外的來源；變體（`world/enemies.yaml`）照變體 ID 列。（R2）
5. **分組改的骰子階梯照 `composer_parts.dice_ladder`**（同平均時面數小的在前，例 7d4 在 5d6 前），規格寫「同平均取顆數少的」；為了「階梯沿用組合器的唯一來源」沒有另寫一份。武器倍率不在階梯上時以「比它大／小的最近一級」為第一級。（T7）
6. **地圖戰的受測招預設＝草稿改到的技能**；`inject` 沒給 `allies` 時我方自動用那幾個 build（標準隊友補滿），否則「裝到 build」不會上場。（T9）
7. **R1 只擋「新」低於下限的**（改前就低於的不算；目前內建沒有）；判定照 `test_enemy_skill_count_149` 的第一季範圍，變體也算（改基礎單位會連帶變體）。（R1）
8. 分組改的 `ap_cost` 夾 1～3、`cost.cooldown` 1～6、耐力／法力 ≥ 0（schema）；射程夾形狀表範圍。
9. `POST /sims` 的 `seeds` 上限由 40 放到 160（地圖戰 1 張圖 × 最多 160 種子；總場數照舊上限 160）。

**新增的複雜度 noqa**（`C901`／`PLR0911`／`PLR0912`／`PLR0915`）：無。另有三處 `# noqa: PLR2004`（魔術數字，不是複雜度類）：`objects.py` 與 `skills.py` 各一處「固定射程 ≥ 2 算遠程」、`objects.py` 一處「路徑至少兩段才看是不是 `shape.*`」。
