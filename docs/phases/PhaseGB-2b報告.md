# Phase GB-2b 報告｜GB-2 收尾：吸氣 4 格內、圖示夾具、熔岩濺落說明字、蜥蜴出生格、工坊標籤

> 實作者（Opus 5.5），2026-11-14，起點本機 main `d195ab427` ＋ 合併 GB-2 分支 `worktree-agent-a8f4c3aaee13351db`（`f46968b85`）。依據：`docs/phases/PhaseGB-2報告.md` 第 7、10 節（待決 1～6）、`docs/phases/PhaseGB計畫.md` 0.2 R2、R7、第 6 節、末節開發 PM 裁定（使用者「都照建議」）、`docs/design/19-灰燼荒原與賽季主線.md` 19.2.3「巨型頭目段 GB 補定的細節」第 5 點。
> 引擎結算程式、AI 評分（GB-3）、`client/` 程式（只重產夾具）、設計文件都沒動。`LOG_FORMAT` 不升（理由見第 6 節）。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 吸氣「4 格內」（R7） | `skill_heart_inhale` 的 `shape` 由「環形 2」改成「範圍光環 4」（R2 量法＝離最近佔格曼哈頓距離 ≤ 4，佔格本身不算；GB-1b 的 `shapes.around_tiles` 本來就支援），往最近佔格拉 1 格（引擎 T7），後段方陣 1d10 照舊。schema 最小擴充見第 2 節 | 見第 9 節 |
| 圖示夾具 | 重產 `client/src/render/fixtures/skill_icons.json`（`uv run python -m tests.narrative.icon_fixture`），差異見第 4 節 | |
| 熔岩濺落說明字 | `narrative/skills.py`：延遲段錨點句改查表 `_ANCHOR_PLACES`，`farthest_enemy` 寫「蓄力，下回合開始時**在離自己最遠的敵人那一帶**釋放：方陣（射程 0）：…」（`cast_tile` 照舊「在施放時選的格子」） | |
| 第 2 階段蜥蜴出生格 | `content/units/ashen_heart.yaml` 第 2 階段 `spawns` 的 `at`：(3, 3) → **(2, 3)**、(7, 3) → **(8, 3)**（殼縫攻擊位各往外一格；兩格都是石地、沒有物件與表面，`content check` 通過）；熔心坑檔頭註解同步 | |
| 工坊標籤 | 限時封招的標籤在工坊畫面換成技能中文名：「部位「核心」破掉後第 2 個效果：封住「熔心吸氣」的回合數」（`objects.py` 的 `_skill_names_in_label`，`object_detail` 有內容庫時替換；`concrete_fields` 沒有內容庫仍是 ID）。部位名本來就是中文。建議範圍 `rounds` 1～5、`max_rows` 1～6 在 GB-2 已寫進 `tuning_fields.yaml` 的 `hint_min／hint_max`，不必改 | |
| 測試 | 新 `tests/content/test_builtin_gather_gb2b.py`（LLM 面範圍不變、內建吸氣載入與驗證、非內建非敵人專用不能用範圍光環聚集、衍生的敵人專用招可以、半徑 4 只限內建、熔岩濺落說明字）、`tests/engine/test_giant_inhale_gb2b.py`（3×3 巨人：曼哈頓 4 的南、斜角、西三人各被拉 1 格；5 格外不動；內容形狀）；`tests/api/tuning/test_giant_tuning_gb2.py` 加一行標籤斷言；被打到的既有測試 2 檔（第 4 節） | |
| 文件 | 本報告；`docs/dev/上手-內容資料與模擬.md` 第四節第 53 點（聚集段與 `content_max`、Windows 寫檔 CRLF） | |

## 2. 吸氣的 schema 擴充（只放寬內建技能）

GB-2 卡在兩處：聚集段第一段形狀只收 `cross`／`square3`／`ring`（`GATHER_SHAPES`）、範圍光環半徑上限 3。做法：

0. **誰能用**：`SkillDef.content_only_ok`＝內建技能（`provenance.origin: builtin`）**或敵人專用招**（`enemy_only`）。只看 `builtin` 時，閃現、升階這類衍生版本（`flash_derive.py` 把來源換成 `level_up`＋`parents`）會被擋，`tests/skillgen/test_flash_bal10b.py` 對每個內建複合技做閃現就紅了；加上 `enemy_only` 是照 LW-1（`self_lacks_status`）、`lock_on` 的前例「只給敵人專用招」。LLM 提議的來源由呼叫端給（不會是 `builtin`），`enemy_only` 不在提議欄位（`proposal/convert.py`），玩家工坊選單也不列——兩條路都走不到。
1. **聚集段形狀**：新常數 `BUILTIN_GATHER_SHAPES = ("allies_in_radius",)`（`content/skills/constants.py`）。`followup.py::_check_after_gather` 收 `GATHER_SHAPES + BUILTIN_GATHER_SHAPES`；`SkillDef._check_followup` 先擋「不是 `content_only_ok` 卻用範圍光環聚集」（錯誤訊息只列 `GATHER_SHAPES`，LLM 重試看到的字不變）。`skillgen/validate.py::_move_segment_violations` 的「聚集段可不在 `displace` 骨架形狀內」也只對 `content_only_ok` 加上範圍光環。聚集點：範圍光環不在 `FOLLOWUP_CENTERED`，`gather_point` 本來就回傳施放者（同環形），後段方陣射程 0——**引擎不用改**。
2. **半徑 4**：`ParamDef` 加選填 `content_max`（> `max`）與 `top(builtin=)`；`skill_shapes.yaml` 範圍光環 `radius: {min: 1, max: 3, content_max: 4}`、`cell_count` 補 `4: 41`（`test_shape_cell_counts.py` 已對引擎幾何比過）、預算是公式（1000 ＋ 400 × 半徑）不用補表。跨檔檢查 `_int_param_problems(builtin=)` 只對 `content_only_ok` 用 `content_max`；`ShapeDef` 的格數、預算表檢查涵蓋到 `content_max`；工坊形狀欄位擋的上限用 `content_max`（工坊改的是內建內容）。
3. **沒動的**：`GATHER_SHAPES`、`ParamDef.max`、技能生成器選項（`skillgen/options.py`、`option_followup.py`、`option_params.py`）、LLM 提議 schema（`proposal/builder.py` 只讀 `spec.min／max`）、組合器——LLM 與玩家看到的範圍逐字不變（`test_llm_facing_ranges_are_unchanged`；`tests/skillgen`、`tests/llm` 全過，第 3 節）。

不用 `content_params`（十字 `arm` 的前例）的原因：它是「整個參數只給內建」，半徑本來就是公開參數，要的是「上限只對內建放寬」。另外 `content_params` 的範圍沒有看來源（任何來源寫 `arm: 2` 在跨檔檢查都過，只靠 LLM schema 不提供）；`content_max` 這次在跨檔檢查就看來源與 `enemy_only`，比前例嚴。

## 3. 逐條驗收

| 驗收 | 結果 | 證據 |
|---|---|---|
| 熔心坑以外 34 場逐字不變 | 過：`different=0` | 第 5 節 |
| 熔心坑改前（GB-2）改後勝方與輪數、30 輪內、重播一致（6 種子） | 過：12 場都在 7 輪內結束；種子 1、2、3、7、9、12 重播通過 | 第 5 節 |
| CLI 快照逐鍵預測 | 過：預測 `skills_list`、`skills_show_all/05` 兩鍵＝實際 | 第 4 節 |
| `trpg content check` | 結束碼 0（「共 690 個檔案；…；429 個技能通過預算與結構驗證」） | |
| 圖示夾具 | 重產；只變熔岩濺落、熔心吸氣兩筆；`test_client_fixture_is_current` 過 | 第 4 節 |

靜態檢查（commit 前）：`ruff check` All checks passed、`ruff format --check` 2721 files already formatted、`mypy` Success（1610 files）、`lint-imports` 14 kept 0 broken，結束碼都 0。

相關測試（`-n 8`）：`tests/content`、`tests/api/tuning`、`tests/narrative`、`tests/skillgen`、`tests/llm`、`tests/test_architecture.py`，`tests/engine/` 的 `test_shape_cell_counts.py`、`test_giant_inhale_gb2b.py`、`test_enemy_skills_149.py`、`test_lava_splash_bal21b.py`、`test_source.py`、`test_delayed_anchor_bal21.py`、`test_giant_gb1a/1b.py`、`test_giant_parts_gb1c.py`、`test_boss_phases.py`，`tests/server/test_season_reset.py`，`tests/world/` 的 `test_ashen_waste.py`、`test_enemy_ai_moves_149.py`、`test_thread_endings.py`：8775 passed。同一批一起跑時 `tests/api/test_delayed_api.py`（3 個 setup 錯誤「fixture 'client' not found」）與 `tests/api/test_encounter_look_uie3b.py`（1 個 422「這裡有實地地圖」）紅——把 `tests/api/` 的個別檔和 `tests/api/tuning` 混在同一行時 `tests/api/conftest.py` 的 fixture 沒載入，與本段無關；這三檔單獨跑全過。`tests/cli -m slow` 44 passed。

## 4. 快照、夾具與既有測試

**CLI 快照**：預測 `skills_list`（列表第二行是形狀摘要＋第二段說明：吸氣「環形（半徑 2，…）」→「範圍光環（半徑 4）」、濺落「在施放時選的格子」→「在離自己最遠的敵人那一帶」）與 `skills_show_all/05`（兩招的技能卡）；7 個戰鬥鍵都不是頭目圖、不變。第一次跑 `tests/cli -m slow`：正好這兩鍵紅、42 過。用 `trpg skills list` 改前（GB-2 舊樹）改後對比，只差這兩行。只用 `UPDATE_CLI_SNAPSHOTS=1 … -k "skills_list or skills_show_all/05"` 重產；之後 `tests/cli -m slow` 44 passed。

**圖示夾具**（`client/src/render/fixtures/skill_icons.json`，只重產）：和 GB-2 的檔逐欄比對，只有 5 個值變（`random`、`workshop` 兩組不變）：

| 技能 | 欄位 | 改前 → 改後 |
|---|---|---|
| 熔心吸氣 | `art.motion` | `spin` → `area` |
| 熔心吸氣 | `segments[0].shape_id` | `ring` → `allies_in_radius` |
| 熔岩濺落 | `art.motion` | `area` → `aura` |
| 熔岩濺落 | `segments[0].range` | 4 → null |
| 熔岩濺落 | `segments[0].shape_id` | `square3` → `self` |

**被打到的既有測試**（斷言沒放寬、數值沒調）：

| 測試 | 原因 | 改法 |
|---|---|---|
| `tests/skillgen/test_flash_bal10b.py::test_followup_potency_only_raises_the_followup[skill_heart_inhale]` | 範圍光環 4 的形狀倍率（2600‰）比環形 2（2200‰）高，T2 預算比例 95.4%，接續段傷害加一級（1d10→1d12）就超出窗；T3（78.9%）照常過 | 加進 `NO_ROOM_AT_BASE_TIER`（熔岩濺落的同一份例外，只驗 3 階），註解寫明待 PM 決定（待決 1） |
| `tests/skillgen/test_workshop_options.py::test_every_shipped_skill_fits_the_options` | 玩家工坊的選單不列範圍光環聚集（刻意，只給內建） | 照 BAL-14c 召喚上限的前例跳過「範圍光環＋第二段」的技能 |

另外改 gate 之前，`test_compound_skills_have_two_options_at_their_lowest_tier[skill_heart_inhale]` 也紅（閃現衍生版本被「只限 builtin」擋）——改成 `content_only_ok` 後通過，見第 2 節第 0 點。

## 5. 不變比對（46 場，改前＝GB-2 `f46968b85`）

腳本在 scratchpad（未 commit）：改前用 `git archive f46968b85 src content` 解開，`PYTHONPATH` 指舊 `src`、`TRPG_CONTENT_DIR` 指舊 `content`；兩邊都跑 `trpg battle --map … --seed … --log-json`（地圖預設陣容、效用 AI、`max_rounds=30`），比 `actions`、`events`、`orders`、`final_state`（拿掉 `final_state.ruleset`）、`setup`（拿掉 `setup.ruleset`）、`seed`、`format`。拿掉的只有規則包與 `ruleset_hash`（`skill_shapes.yaml` 與兩個技能檔在規則包內，46 場都會變，預期）。改前的熔心坑數字與 GB-2 報告第 3 節逐場相同（種子 1：敵／4／466、種子 2：我／5／468…），證明基準正確。

- 熔心坑以外 34 場：**`different=0`**。
- 熔心坑 12 場（只列不評；「施放」＝動作列表裡的吸氣／濺落次數）：

| 種子 | GB-2 勝方／輪／事件 | GB-2b 勝方／輪／事件 | 吸氣施放 GB-2 → 2b |
|---|---|---|---|
| 1 | 敵／4／466 | 敵／4／454 | 1 → 1 |
| 2 | 我／5／468 | **敵**／5／489 | 0 → 0 |
| 3 | 敵／4／380 | 敵／4／451 | 1 → 1 |
| 4 | 敵／5／488 | **我**／6／521 | 1 → 1 |
| 5 | 敵／5／402 | 敵／5／402 | 0 → 0 |
| 6 | 敵／5／540 | 敵／5／537 | 1 → 0 |
| 7 | 敵／6／506 | 敵／7／573 | 1 → 1 |
| 8 | 敵／5／372 | 敵／5／372 | 0 → 0 |
| 9 | 敵／6／362 | 敵／6／363 | 0 → 0 |
| 10 | 敵／4／426 | 敵／4／422 | 1 → 1 |
| 11 | 敵／5／523 | 敵／6／568 | 1 → 1 |
| 12 | 敵／5／458 | 敵／6／500 | 0 → 1 |

  12 場都和 GB-2 不同（種子 5、8 的勝方、輪數、事件數相同，但事件內容不同：第 2 階段蜥蜴出生格改了）。都在 30 輪內分出勝負（最長 7 輪）。重播：種子 1（74 動作 454 事件）、2（89／489）、3（85／451）、7（115／573）、9（69／363）、12（96／500）都「重播驗證通過」。

## 6. 影響

- **`LOG_FORMAT` 不升（`/128`）**：引擎程式沒改，結算規則沒變——範圍光環的聚集點、巨人的範圍光環量法（R2）、往最近佔格拉（T7）都是 GB-1b／1c 已有的規則；變的是內容（吸氣的形狀、召喚格）與 schema 允許的範圍。舊紀錄內嵌當時的規則包，仍可重播。
- `ruleset_hash`、`content_digest` 會變（`skill_shapes.yaml`、兩個技能檔、灰燼之心、熔心坑都在內容裡）→ 進行中的一輪從頭開始、舊世界日誌標成不能重播（使用者 11-12「存檔都可以刪除」，不寫遷移）。
- 前端：圖示夾具重產；`client/` 程式沒動。熔心吸氣的圖示動作由 `spin` 變 `area`、熔岩濺落由 `area` 變 `aura`。

## 7. 平衡疑慮（不量，只記）

1. **吸氣「4 格內」蓋到坑的北半部到中段**（GB 計畫第 10 節第 2 條）：頭目佔 x 4–6、y 2–4，曼哈頓 4 往南到 y 8（x 4–6 那三欄），坑底 y 2–5 整排（x 2–9）都在範圍；南側高台 (2, 9)、(9, 9) 離最近佔格曼哈頓 7、矮牆後與入口通路不在範圍。GB-2 的環形 2 只拉外面第 2 圈 24 格，現在是一大片，近戰、遠程站中段都會被拉。
2. 12 場吸氣施放次數幾乎不變（AI 選招權重沒動，GB-3 才調），但被拉的人變多，後段方陣 1d10 只打拉完後貼身的人。
3. 第 2 階段蜥蜴改到 (2, 3)、(8, 3)：緊貼岩漿邊（x 1 是岩漿），被推擊類技能推進岩漿的機會變大；也離開場蜥蜴 (2, 4)、(8, 4) 更近，兩隻疊在東西兩角。

## 8. 待 PM 決定

1. **熔心吸氣進「閃現強化沒空間」例外**（第 4 節）：`NO_ROOM_AT_BASE_TIER` 是使用者 11-12 選 C「只列熔岩濺落」、原話留了「之後若更多敵人招卡住再考慮 B（整體排除敵人專用招）」。本段照最保守做法把吸氣加進同一份例外（只是測試範圍，遊戲行為不變；敵人專用招本來不進玩家閃現），請 PM 問使用者：維持 C 擴充名單，還是改 B。
2. **「只給內建」的判準含敵人專用招**（第 2 節第 0 點）：`content_only_ok`＝`builtin` 或 `enemy_only`，否則閃現、升階的衍生版本會被擋。若 PM 要嚴格只看 `builtin`，要另外讓衍生流程跳過敵人專用招。
3. **吸氣的範圍**（第 7 節第 1 點）：照 R7「4 格內」＋R2 曼哈頓量法，蓋到坑的北半部到中段；數值交使用者。
4. 熔心吸氣的圖示動作 `spin` → `area`、熔岩濺落 `area` → `aura`（夾具自動推導），要不要美術看一眼。
5. 第 2 階段蜥蜴新出生格 (2, 3)、(8, 3) 貼著岩漿邊（第 7 節第 3 點），規格允許開發 PM 改。
6. `LOG_FORMAT` 不升（第 6 節）：結算程式沒改；若 PM 認為「schema 允許的範圍變了」也算規則變更，再升 /129。

## 9. commit

| commit | 內容 |
|---|---|
| `8f1684bdf` | feat(narrative)：延遲段錨點 `farthest_enemy` 的技能卡說明 |
| `8a6173794` | feat(content)：吸氣範圍光環 4；`BUILTIN_GATHER_SHAPES`、`ParamDef.content_max`、`content_only_ok`；新測試兩檔；被打到的 skillgen 測試兩檔 |
| `91f827d3f` | content(gb2b)：第 2 階段蜥蜴出生格 (2, 3)、(8, 3) |
| `d8ba6f097` | feat(tuning)：限時封招標籤用技能中文名；形狀欄位上限用 `content_max` |
| `639fee8bd` | test：重產圖示夾具、CLI 兩鍵 |
| 本報告的 commit | docs：本報告、上手筆記第 53 點 |

## 開發 PM 裁定（2026-11-14）

- 接受。熔心坑以外 34／0；熔心坑 12 場都在 7 輪內結束、重播一致；CLI 快照照預測兩鍵。
- **待決 1（測試放寬，push 前已報專案 PM）**：熔心吸氣加進 `NO_ROOM_AT_BASE_TIER`（`tests/skillgen/test_flash_bal10b.py:156`），等於擴充使用者 11-12 選 C 時只列熔岩濺落的例外名單。經專案 PM 問使用者：維持 C 擴充名單，或改 B。
- 待決 2：同意（內建或 `enemy_only` 才能用擴充範圍，LLM 與玩家工坊看到的範圍不變）。
- 待決 3 平衡觀察、待決 4 圖示動作變更（熔心吸氣 spin → area、熔岩濺落 area → aura）分別轉玩法 PM、美術 PM。
- 待決 5：蜥蜴出生格 (2, 3)、(8, 3) 接受（蜥蜴是火屬性敵人）。
- 待決 6：`LOG_FORMAT` 不升（結算程式沒改，規則包雜湊本來就會擋舊紀錄重播）。
- 2026-11-14 使用者回待決 1：「B」（專案 PM 轉）。做法：敵人專用招（enemy_only）整批不做閃現強化空間檢查，NO_ROOM_AT_BASE_TIER 改按 enemy_only 判斷；確認玩家招全部仍受檢查。派 GB-2c（同一 agent）做。
