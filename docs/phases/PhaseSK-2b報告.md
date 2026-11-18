# 階段 SK-2b 報告：#166 新原語接進出題＋SK-1／SK-2 待決答覆

> 2026-11-19，實作者（SK-2b）。規格 `docs/phases/PhaseSK-2b計畫.md`；答覆來源玩法交接 4.1.28、4.1.29。
> 分支 `worktree-agent-a151f511860f8fdef`（從 main `39b76cc2d` 起，中途 fast-forward 到 `630f26f4a` 拿開發 PM 補的 `test_trigger_order`）。
> 數字一律是初值，接工坊；沒有試數值、沒有跑平衡量測與模擬（戰鬥不變比對與紙面小樣本除外）。沒有碰 SK-3 的觸發、反應、擲骰、開場檔（見第 5 節「改到的引擎檔」）。

## 結果（一兩句）

規格 A、B 兩組都做完並有測試鎖住；戰鬥不變比對 60 場 **different=0**。三個新原語能被組合器做出來（紙面 5600 招：鉤 183、吸收表面 161、疾病擴散 9），機率設 0 時 5600 招和改前逐字相同。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| A1 吸水 → 帶潮濕；油、煙霧不能換元素 | 完成 | `e745ca399` |
| A2 推不動算撞擊 | 不用改（照字面，現狀） | — |
| A3 疾病擴散一次只傳一種 | 完成 | `8ae3ba18e` |
| A4 AI 不為擴散加分 | 不用改（現狀） | — |
| A5 新原語接進出題（骨架、組合器排除表、LLM 選單、提示詞版號） | 完成 | `f42d504b4`、`920c3430d`（只加在明列的骨架）、`9f65ea43c`（測試與夾具） |
| A6 工坊白名單 | 部分（見待決 1） | `f7290b18c` |
| B1 驗證器擋一定成立的距離條件 | 完成 | `8cc4de78b` |
| B2 以血支付的字 | 完成 | `14a894a02`（和 B5 同一個 commit，同一個檔） |
| B3 附淨化只移除 1 個減益 | 完成 | `318ab8327` |
| B4 側變分類與換觸發配對 | 不用改（照 SK-1） | — |
| B5 前綴改 3 個 | 完成 | `14a894a02` |
| B6 刪 `isLlmTag` | 完成 | `faa146122` |

### A1 吸水 → 帶潮濕

- `absorb_surface` 的 `gain: element` 吸到**水**時照吸（`_absorbable` 放行水），元素不變；`Cast.absorbed_wet` 設成真，之後每個傷害效果結算完，在**命中的單位所在格**造水（`Cast.soak_hit_tiles`，接在元素觸及、風擴散之後；同召喚灌注 `wet`）。沒命中不造水。
- 油、煙霧：引擎照舊落空；驗證器另外擋「`gain: element` 又指定 `surface: oil／smoke`」（`content/skills/effects.ABSORB_NO_ELEMENT`）。油、煙霧換層數、治療、護盾照常。
- 卡片字：吸水招寫「這一招之後的傷害帶潮濕（命中時在目標格造水）」；沒指定表面時也寫明「吸到水時帶潮濕」。紀錄文字「換成潮濕（命中時在目標格造水）」。原語說明、`llm_hint`、工坊玩家文字同步。

### A3 疾病擴散只傳一種

- `engine/contagion.py`：新函式 `spread_pick`（剩餘回合最多、永久算最多，一樣多時照 `core.contagion_statuses` 的順序）；`contagion_statuses` 改成 `[burning, bleed, poison]`（順序＝優先順序，寫進 `core.yaml` 與 `CoreRules` 預設值）。`DiseaseSpread.status_ids` 只有一個。傳過去照樣 `contagious`，可以連鎖（有測試）。
- **觸發函式名稱、位置都沒變**（仍是 `engine/contagion.py::_spread_on_downed`，`unit_downed`）。

### A5 接進出題

- 骨架（`content/skeletons/`）：
  - 位移 `displace` 核心 ＋ `hook`；
  - 打擊 `strike` 附帶 ＋ `absorb_surface`、`contagion`，`harmless_ok: [absorb_surface]`（打擊附帶是 `harmful_only`，吸收表面收益給自己，是例外）；
  - 蓄力／終結 `builder_finisher` 附帶 ＋ `absorb_surface`；
  - 光環 `aura` 核心 ＋ `absorb_surface`；
  - 範圍 `area`、控場 `control`、陷阱 `trap` 附帶 ＋ `contagion`。
- `SecondaryRules.harmless_ok` 與 `admits()`：驗證器、組合器、工坊選項、LLM 選單（說明會寫「absorb_surface 例外」）、補強的「能不能放進骨架」都改用 `admits`。
- **組合器排除表**：三個原語加進 `_HAND_WRITTEN_PRIMITIVES`（一般抽選不抽），只由獨立串流加入，父串流不推進：
  - `composer.hook`：位移骨架核心改成鉤（只有直線形狀；冷卻下限 `hook_min_cooldown`）；
  - `composer.absorb_core`：光環核心改成吸收表面（吸自己腳下，換治療或護盾）；
  - `composer.absorb`：打擊、蓄力／終結（單體形狀、附帶還有空位、沒有衝鋒／瞬步）加吸收表面當第一個效果（換元素或層數；層數只用累積在自己身上的，技能已用到的優先；吸腳下或目標格）；
  - `composer.contagion`：技能已對敵人施加燃燒／流血／中毒、附帶還有空位時加在最後。
  - 只加在**明列**的骨架（連段、光環的附帶是「不限」，不加；`920c3430d`）。
  - 機率 `skill_composer.yaml` `structure`：`hook_core_permille: 200`、`absorb_core_permille: 100`、`absorb_secondary_permille: 150`、`contagion_permille: 150`（初值＝大約和骨架裡一個一般原語被抽到的機會相當，不另加權；6.12 稀有度門檻照原語的 `min_rarity: rare`）。
- 吸收表面的 `amount`、`dice` 從 `knob: none` 改成有旋鈕（`when: {gain: …}`），組合器與 LLM 提議的預算器才補得了數值。
- 驗證器 `cap.contagion_source`：疾病擴散前面要有施加燃燒／流血／中毒的 `apply_status`（4.1.28「只附在……上」）。
- **`llm_topic.core_exclude` 沒加**：LLM 要能出鉤、吸收表面當核心（4.1.28「組合器和 LLM 都可以用」）；骨架一改，LLM 的核心清單與選單就自動帶到。有測試鎖住三個都不在 `core_exclude`。
- 提示詞版號 `skill-proposal/19 → /20`（選單、schema、驗證變了；系統指令沒變，快照雜湊同 /19）。

### B1 距離條件的射程

- `skillgen/validate._distance_condition_violations`（`cap.distance_condition`）：主動技、射程能確定（`shape.range` 是整數，或直線／錐形的 `size`）時，貼身要 ≥ 2、遠距要 ≥ `core.far_distance`（讀工坊值，有測試改門檻）。技能層與效果層條件、`any_of` 都看。武器射程（`weapon`）和其他形狀不檢查（待決 3）。

### B2、B5 字

- `cost_blood`：說明「以血支付：法力或耐力只花 1 點，其餘改扣自己的生命，威力略升」、大標「大部分代價改用自己的血付，威力略升」。
- 前綴：`reshape_skeleton` 擴散 → 廣域、`element_swap` 轉元 → 易元、`kill_reset` 連斬 → 連殺。

### B3 附淨化只移除 1 個

- 淨化原語多參數 `count`（`type: count`，1 或 all；省略＝全部）；`CleanseEffect.count`（`None` 不輸出，舊紀錄逐字不變）。挑法：控制類（`control_group` 不是空）→ 剩餘回合最多（永久最多）→ `statuses.yaml` 順序。
- `support_cleanse` 的 rider 改 `{type: cleanse, count: 1}`；說明「附淨化：治療時順便移除目標身上 1 個減益（控制類優先）」、大標「治療時順便解除 1 個減益」。卡片字「淨化：移除身上 1 個負面狀態（控制類優先，再來剩餘回合最多的）」。
- 預算照舊固定 3 點（count 不影響；待決 2）。

### B6

- `client/src/run/llmFlow.ts` 刪 `isLlmTag`；兩個測試檔改用 `llmTagHint` 斷言同樣的事。

## 驗收條件

| 條件 | 結果 | 證據 |
|---|---|---|
| 各相關目錄測試 0 | 通過 | 第 3 節 |
| ruff、format、mypy、lint-imports 0 | 通過 | 第 3 節 |
| 前端 tsc、相關 vitest 0 | tsc 通過；vitest 有 2 個 SK-1 留下的失敗（待決 11） | 第 3 節 |
| 戰鬥不變比對 | **`battles=60 events=23897 different=0`** | 第 2 節 |
| 快照、夾具逐鍵核對 | 見下表 | |
| 紙面樣本：新原語能被組合器做出來 | 見第 4 節 | |
| 版號列出 | 見下表 | |

**快照與夾具**

| 鍵 | 預測 | 結果 |
|---|---|---|
| parity `complete`／`retier`（401 招） | 不變（手寫技能沒用到新原語；驗證新規則沒有手寫技能踩到） | 不變 |
| parity `flash`（126 鍵） | 有 B2、B3、B5 改字的模板出現在提議裡的鍵會變 | **31 鍵變**：先把改前／改後整份提議倒出來比（不是只比雜湊），31 鍵全部都含以血支付，把舊說明、大標換成新字後 31 鍵逐字相同；其餘 95 鍵不變。只改這 31 個值（腳本照失敗清單＝預測清單逐鍵寫回） |
| 技能圖示 `client/src/render/fixtures/skill_icons.json` | `skills`、`workshop` 不變；`random`（組合器 50 個種子）只有抽到新串流的種子會變 | `random` 第 28、44、48 個變（44 光環吸收表面、48 位移鉤、28 位移：有一次嘗試抽到鉤但沒過、重抽後主串流位置不同）；三個在「機率設 0」的內容庫下都和舊夾具相同。照 `tests.narrative.icon_fixture` 重產，只有這 3 筆變 |
| CLI 輸出（`tests/cli -m slow`）、`llm_propose_mock.txt` | 不變 | 44 passed，沒重產 |
| `glossary.json`、`unitDolls.json`、`raceLooks.json`、`skillCards.json` | 不變（不收原語的 description／參數說明） | `export_client_fixtures.py` 重產後無差異 |
| `client/openapi.json` | 不變（API 模型沒改） | `export_openapi.py` 重產後無差異；沒跑 `gen:api` |

**版號**

| 版號 | 變動 |
|---|---|
| `PROMPT_VERSION`（技能提議） | `skill-proposal/19` → **`/20`**（快照雜湊同 /19） |
| `LOG_FORMAT`、`WLOG_FORMAT`、`CHAR_FORMAT`、`SAVE_FORMAT` | 不升（沒有新事件欄位；`CleanseEffect.count` 是效果不是事件、`None` 不輸出） |
| `WORLD_RULES_VERSION` | 不升（`trpg.world` 沒改；組合器輸出變的地方同時改了內容，`content_digest` 會變，舊日誌照樣標規則已變） |
| `flash-pick/2`、`flash-variation/6` | 不升（prompt 文字沒改，只有模板字與參數） |
| `ruleset_hash`、`content_digest` | 變（骨架、原語、核心規則、組合器表、閃現模板） |

**改到的既有測試**（斷言沒有放寬）：`test_absorb_surface_sk2`（水不再落空 → 改測油、煙霧）、`test_contagion_sk2`（多狀態只傳燃燒）、`test_workshop_feedback`（條數 183 → 184）、`test_skill_rules_content`（骨架清單多新原語、`harmless_ok`）、`test_rules_budget_bs1`（工坊欄位多兩個）、`test_prompts`（版號）、`test_upgrade_topup::test_upgrade_topup_distribution`、`tests/api/test_wish_pregen.py`、`tests/api/test_wish_api_wp2.py`（這三個靠「LLM 題目抽到哪個核心」的固定樣本：新核心讓抽選換了一批，例如許願「燃燒」的題目核心變成復活，Mock 找不到手寫技能扮演答對 → 改用新的 `tests.engine.helpers.without_sk2b_offers()` 拿掉骨架裡的新原語，原斷言照舊）、前端 `llmFlow.test.ts`、`pk4bOfferTags.test.ts`（B6）。

## 2. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive 630f26f4a src content config` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；整份事件、步驟、最終狀態（去掉 `ruleset`、`ruleset_hash`、`format`）比 SHA-256。10 張一般圖（bridge_chasm、cliff_outpost、dark_forest、frozen_lake、lava_crossing、narrow_halls、oil_depot、open_plain、ruined_fort、swamp）× 種子 1、2 ＋ 4 張頭目圖（bandit_lair、rift_gate、cloud_summit、molten_heart_pit）× 種子 3～12，同 SK-2。

- **`battles=60 events=23897 different=0`**。既有技能沒有用到淨化個數、疾病擴散、吸收表面，所以附淨化、擴散的規則改動不造成差異。

## 3. 測試與檢查

分目錄、一次一組、`-n 8`；`tests/llm` 和 `tests/skillgen` 沒同時跑。

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check src tests` | 0 |
| `uv run ruff format --check src tests` | 0 |
| `uv run mypy`（1689 檔） | 0 |
| `uv run lint-imports`（14 kept） | 0 |
| `uv run trpg content check` | 0（691 檔、429 技能） |
| 新測試：`tests/engine/test_absorb_wet_sk2b.py`、`test_cleanse_count_sk2b.py`、`tests/skillgen/test_distance_condition_reach_sk2b.py`、`test_new_primitives_offers_sk2b.py`，加上 `test_contagion_sk2.py` 多的 6 個 | 0 |
| **第二輪**（全部修正後）`pytest -m slow tests/cli`（44） | 0 |
| `pytest -n 8 tests/content`（3124） | 0 |
| `pytest -n 8 tests/narrative`（475） | 0 |
| `pytest -n 8 tests/skillgen`（4530 passed、14 skipped） | 0 |
| `pytest -n 8 tests/roguelite`（281） | 0 |
| `pytest -n 8 tests/api`（1320 passed、1 skipped） | 0 |
| `pytest -n 8 tests/engine`（4942；第一次 1 個失敗：`test_self_moves` 的「位移骨架抽得到衝鋒」固定種子 454、476 被鉤的串流換掉 → 改用 `sk2b_streams_off()` 鎖樣本，`4da4dcb70`，該檔重跑 47 passed） | 0 |
| `pytest -m slow tests/sim`（19） | 0 |
| `pytest -n 8 tests/llm`（495） | 0 |
| `pytest -n 8 tests/world`（1328） | 0 |
| `pytest tests/test_architecture.py`（13） | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py`（928） | 0 |
| 前端 `tsc --noEmit` | 0 |
| 前端 `vitest run src/run src/render src/battle`（2894） | **1**：2 個失敗都是 SK-1 的距離條件 `point_blank`、`long_range` 沒有專屬圖示（`skillIcon.test.ts`、`qIconSkills.test.ts`）；這段沒改圖示、條件、`glossary.json`，是 SK-1 留下的（SK-1 報告待決 8 沒跑 vitest）；`llmFlow`、`pk4bOfferTags` 通過 |
| 戰鬥不變比對（第二輪，60 場） | 0（different=0） |

沒跑：全量 `scripts/check.py`、平衡量測、戰鬥模擬（不變比對以外）、`recipe_census.py`（紙面樣本改用組合器直接抽，見第 4 節）。

## 4. 紙面樣本（不呼叫 LLM）

腳本在 scratchpad：`compose_random_skill`，7 個骨架 × 稀有／史詩 × 角色 1、2 階 × 種子 0～199＝5600 招，和改前副本逐招比。

| 骨架 | 新原語 | 出現次數（800 招中） | 例 |
|---|---|---|---|
| 位移 | 鉤（核心、直線） | 183 | `displace/epic/1/1` |
| 光環 | 吸收表面（核心；治療 60、護盾 60，都吸腳下） | 120 | `aura/epic/1/110` |
| 打擊 | 吸收表面（附帶；換元素 19、換層數 16；吸腳下 18、目標格 17） | 35 | `strike/rare/1/103` |
| 蓄力／終結 | 吸收表面（附帶；元素 4、層數 2） | 6 | `builder_finisher/rare/1/197` |
| 範圍 | 疾病擴散 | 4 | `area/epic/1/150` |
| 控場 | 疾病擴散 | 3 | `control/rare/1/117` |
| 陷阱 | 疾病擴散 | 2 | `trap/epic/2/148` |
| 打擊 | 疾病擴散 | **0**（待決 4） | — |

- 和改前比：5051 招逐字相同；353 招不同而且帶新原語；196 招不同但沒有新原語——那個種子有一次嘗試抽到新串流、那次沒做成（預算或驗證不過）而重抽，主串流的位置跟著不同。
- **把四個機率設成 0，5600 招和改前逐字相同**（父串流不推進的證明）。
- 新原語做出來的招都通過 `validate_skill`（有測試：強制機率 1000 時鉤、光環吸收、打擊吸收、範圍／控場／陷阱的擴散）。

## 5. 改到的引擎檔（和 SK-3 的邊界）

只改了：`engine/skills/primitives/terrain.py`（吸收表面）、`engine/skills/cast.py`（加 `absorbed_wet` 屬性、`soak_hit_tiles` 方法、`resolve_effect` 多呼叫一行；沒動擲骰 `roll_hits`／`roll_one`）、`engine/skills/primitives/numeric.py`（淨化傳 `count`）、`engine/effects/models.py`（`CleanseEffect.count`）、`engine/effects/handlers.py`（`_cleanse` 與新 `_cleanse_order`）、`engine/contagion.py`。觸發登錄、反應、開場流程沒碰。`cast.py` 是 SK-3 可能也會改的檔，合併時請看這三處。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| 事項 | 我的做法 | 其他選項 |
|---|---|---|
| 1. A6「預算點數」進工坊白名單 | 鉤 6、疾病擴散 2、吸收表面 1 的點數在 `skill_primitives.yaml`，這個檔是工坊的禁止檔（schema 匯入時從固定資料夾讀，草稿看不到），所以**沒加**；只加了 `hook_min_cooldown`、`contagion_radius` | 把這三個點數搬到 `skill_budget.yaml`（像 `dispel_one_points`）再開白名單 |
| 2. 淨化 1 個和全部同價（固定 3 點）、組合器四個機率（200／100／150／150‰）、吸收換層數的數量 | 初值；淨化 count 不影響預算 | 使用者在工坊調；或淨化 1 個另給點數 |
| 3. 距離條件的「最大射程」 | 只看固定射程（整數 `range`）與直線／錐形長度；武器射程與自身、光環等形狀不檢查；範圍形狀（3×3、十字）不加半徑 | 依武器射程或形狀範圍算更細的最大距離 |
| 4. 打擊骨架做不出疾病擴散 | 打擊附帶上限 1，已經用在施加燃燒／流血／中毒上，就沒有空位放擴散；照現有上限不放寬（同 SK-1 待決 6 的蓄勢） | 疾病擴散不佔附帶名額，或打擊上限放寬 |
| 5. 疾病擴散要放在施加狀態「之後」（新驗證 `cap.contagion_source`） | 4.1.28「只附在……的效果上」照字面做成驗證；所以「打已經帶狀態的目標」那種用法（SK-2 原語說明裡的另一種寫法）現在不能單獨出 | 只在組合器限制、驗證器不擋 |
| 6. 吸收表面當打擊附帶時「吸哪裡」 | 組合器在腳下與目標格之間各半 | 只吸腳下或只吸目標格 |
| 7. `reshape_shape`（舊模板「換形狀」）的前綴也叫「擴散」 | 規格只說換骨架那個改「廣域」，舊模板沒動 | 一起改，避免和「會擴散」撞字 |
| 8. 4.1.28 第 6 點的用字（狀態卡「會擴散」、浮字「擴散」取代「會傳染」） | SK-2b 規格沒列，前端浮字 `battle/feedback.ts` 沒改 | 併下一段（前端字） |
| 9. 吸收表面的 `player_description` | 沒改（仍寫「帶上那種表面的元素」）；卡片字、原語說明、工坊玩家文字已寫吸水帶潮濕 | 玩法 PM 改一句 |
| 11. 前端 vitest 2 個失敗（SK-1 的貼身、遠距條件沒有圖示部件） | 不在這段範圍，沒動 | 轉美術 PM 或併下一段 |
| 10. Mock LLM 對新核心沒有手寫示範 | 題目抽到鉤、吸收表面當核心時，Mock 找不到手寫技能扮演答對（只影響 Mock 與測試；真模型不受影響）；三個舊許願測試改用 `without_sk2b_offers` 鎖樣本 | 補手寫示範技能（鉤、光環吸收） |

其他：
- `_HAND_WRITTEN_PRIMITIVES` 沒改名（`scripts/wish_coverage.py` 照用；它對這三個原語印的「組合器不抽、只在少數骨架的特殊路徑出現」仍正確）。
- 第一輪各目錄測試是在 A5 的「只加在明列骨架」修正之前跑的；修正後全部重跑一次（第 3 節「第二輪」）。
- 新測試輔助：`tests.engine.helpers.without_sk2b_offers()`（骨架拿掉三個新原語）、`sk2b_streams_off()`（組合器四個串流機率設 0）。
