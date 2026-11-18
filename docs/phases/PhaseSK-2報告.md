# Phase SK-2 報告：#166 第 2 組（新原語或規則）

> 規格：`docs/phases/PhaseSK-2計畫.md`（main `784508695`）。分支 `worktree-agent-aaaeadb953a4fbfe3`（起點 main `be42035a5`）。
> 數字一律是初值，接數值工坊；沒有試數值、沒有跑平衡量測與模擬（戰鬥不變比對除外）。

## 0. 結論

四項都做完，各一個 commit，另一個 commit 是開發頁與截圖：

| 項目 | commit | 一句話 |
|---|---|---|
| 4 推不動算撞擊（6.38-9） | `acd68ac40` | 推、拉打到推不動的目標照撞牆算一次撞擊，目標不動 |
| 1 吸收表面（6.38-4） | `3d1e2f311` | 新原語 `absorb_surface`：吸走腳下或目標格的一種表面，換成層數／治療／護盾／這一招的元素 |
| 2 疾病擴散（6.38-5、6.31） | `06cdf7bff` | 新原語 `contagion`＋倒下時的擴散規則 |
| 3 鉤（6.38-8） | `35d110509` | 新原語 `hook`：直線上第一個單位拉到身邊，推拉 2 格上限的例外 |
| 截圖 | `de4989e50` | 開發頁 `sk2-gallery.html`（真引擎事件）＋5 張截圖 |

- 三個新原語**沒有放進任何骨架**的 core／secondary：組合器（`_HAND_WRITTEN_PRIMITIVES` 在 SK-1 的檔）與 LLM 題目都抽不到，種子 → 技能逐字不變；目前只有引擎與測試、開發頁用得到。接進出題（骨架、組合器排除表、LLM 題目）是待 PM 決定 1。
- `LOG_FORMAT` `/128 → /129`；`WORLD_RULES_VERSION`、`CHAR_FORMAT`、`SAVE_FORMAT`、提示詞版號都沒動；OpenAPI 沒變（`export_openapi.py` 後 `client/openapi.json` 無差異，沒跑 `gen:api`）。

## 1. 各項做法

### 1.1 推不動算撞擊（項目 4）

- `engine/effects/world._push_unit`：`push_distance` 把要求的格數（≥ 1）減到 0、而且不是種族技的無害推拉（`harmless`）時，先照舊發 `push_resisted`，再發 `collided`（新值 `obstacle: immovable`、`shortfall: 1`、`pos`＝目標所在格），撞擊傷害照一般撞擊結算（`triggers._collision_damage`，撞擊骰、力量常駐、風壓倍率照舊），目標不移動、記 `collided_round`。
- 「因任何原因推不動」照字面：位移免疫標籤 `immovable`、巨型單位、穩若磐石、`steadfast` 把 1 格減成 0、獸人「沉穩重心」把推的距離減到 0 都算（待 PM 決定 3）。部分減少（例：穩固 2 → 1）照常移動、不撞。
- 修正規則超過上限的 `extra_collisions`（`excess`）照舊另外算（推不動那一次＋excess 各自結算）。
- 紀錄文字「X 推不動，硬吃下撞擊（1 次撞擊）」；前端浮字 `collided` 的 `immovable` 改成「推不動！撞擊」（`battle/feedback.ts`）。

### 1.2 吸收表面（項目 1）

- 參數：`gain`（`stack`／`heal`／`shield`／`element`，必填）、`surface`（省略＝任何表面）、`stack`＋`amount`（層數）、`dice`（治療、護盾）。哪一格看 `affects`：`self`＝施放者腳下、`tiles`＝形狀選中的那一格（形狀只能 `self`、`single`、`ground_tile`）。必須是第一個效果、只限主動技能、一招最多一個。
- 結算（`skills/primitives/terrain.absorb_surface`）：沒有可吸的表面 → `effect_fizzled`（`no_surface`），其他效果照常；有 → `surface_absorbed` 事件、`ClearSurfaceEffect(cause="absorb")` 移除表面，收益只給施放者（層數直接加；治療、護盾走一般效果）；`element` 把 `Cast.absorbed_element` 設成表面的元素，之後的傷害效果（和元素觸及格子）改用它。
- `gain: element` 只吸帶元素的表面（火、冰、毒、聖光、黑暗）；水、油、煙霧不吸（設計例「吸水 → 潮濕」沒做，待 PM 決定 2）。
- 驗證：`content/skills/effects._check_absorb_surface`（各收益必填／不能填的參數；只有吸收表面能填 `gain`）、`problems._stack_effect_problems`（層數必須 `owner: self`）。
- 預算（`skillgen/budget._absorb_surface_points`，初值）：`base_points` 1 ＋ 收益（層數＝`add_stack` 點數 × 層數；治療、護盾＝骰子平均；元素＝1）。

### 1.3 疾病擴散（項目 2）

- 原語 `contagion`（有害、要命中）：把命中目標身上**現有的**燃燒、流血、中毒（`core.contagion_statuses`）標成會擴散（`StatusInstance.contagious`，false 不輸出），發 `contagion_marked`；沒有這些狀態就沒有效果、不發事件。要放在施加狀態的效果之後（或打已經帶狀態的目標）。
- 擴散（`engine/contagion.py`，掛 `unit_downed` 觸發）：倒下的單位身上有會擴散的狀態 → 候選＝`core.contagion_radius`（1）格內（單位距離，量到最近佔格）的同陣營存活單位，依單位 ID 排序；只有 1 個時不取亂數，多個時 `ctx.rng.choice`。發 `disease_spread`，對那 1 人逐個施加（剩餘回合、原來源、強度照舊，`contagious` 保留 → 可以連鎖）。每次倒下最多傳 1 次。
- 重複施加同一狀態不會洗掉「會擴散」標記（`handlers._reapplied`）。
- 一次倒下帶多種會擴散的狀態時**全部傳給同一個人**（「傳 1 次」解讀成 1 個對象；待 PM 決定 4）。

### 1.4 鉤（項目 3）

- 形狀只能直線（`size` 就是射程，示範 5）；`targeting.compute_area` 的 `_hook_reach` 把影響範圍縮到直線上第一個單位為止（離施放者最近、同距離依 ID）；第一個是施放者的隊友時沒有對象（整招落空）。同一招的其他效果也只打這個人。
- 命中後 `PushEffect(pull=True, stop_before_deadly=True)`，距離＝到施放者的距離 − 1，不經修正規則的推拉上限（6.6 的例外）；下一格是致命地形時停在它前面（不算撞擊）；途中被擋照拉扯撞擊；推不動（巨型頭目等）照第 4 項撞一次。已相鄰時不動。
- 冷卻門檻：`skill_budget.yaml` `hook_min_cooldown: 3`（`BudgetRules.hook_min_cooldown`），`skillgen/validate._hook_violations`（`cap.hook_cooldown`）。只限主動技能、一招最多一個。預算固定 6 點（初值，形狀倍率另算）。

### 1.5 共通

- 每個新原語都補了：解譯器、AI 估值宣告（`ai/coverage.py`，都是預覽事件評分；`contagion` 標記本身沒有預覽收益，AI 不會特別選它，待 PM 決定 6）、預覽宣告、卡片文字（`narrative/skills.py`）、紀錄文字（`narrative/events.py`）、工坊選項（`absorb_gain` 四個選項）、工坊玩家文字（`content/workshop_text.yaml` 10 筆，實作者初稿，待玩法 PM 改寫）、`client/src/battle/fixtures/glossary.json`。
- 前端：`skillClips` 暫借動作（吸收表面＝清除表面的按地、疾病擴散＝施加減益的指向、鉤＝拉扯的猛拉）、Q 版部件 `EFFECT_ALIAS` 暫代（clear_surface／apply_status／pull，專屬圖樣待美術）、`skillSequence` 事件 → 原語、浮字（吸收、會傳染、擴散、推不動！撞擊）。

## 2. 快照與相容性（先預測再核對）

| 東西 | 預測 | 實際 |
|---|---|---|
| `glossary.json` | 每個原語加一筆 | 三次各 +10 行，只有新原語那一筆 |
| `unitDolls.json`、`raceLooks.json`、`skillCards.json` | 不變 | 不變 |
| OpenAPI | 不變（事件是任意 JSON，API 輸出模型沒動） | 不變 |
| 規則包 `ruleset_hash` | 全變（原語表、核心規則、預算表多欄位） | 60 場全變（不變比對已把 `ruleset` 拿掉比） |
| 狀態 JSON | 不帶新欄位時逐字不變（`contagious` false 不輸出） | 不變比對 56 場逐字相同 |
| CLI 快照（slow） | 見第 4 節 | 見第 4 節 |

- 改到的既有測試（沒有放寬斷言）：`LOG_FORMAT` 字面值 12 處；`tests/content/test_coverage.py`、`test_skills_content.py` 把三個新原語列為「還沒有技能用」；`tests/skillgen/test_workshop_feedback.py` 條數 173 → 183；前端 `skillClips.test.ts` 共用片段表加 3 組、`qIconSkills.test.ts` 效果碼 54 → 57。

## 3. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive be42035a5 src content` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；每場比整份事件、步驟、最終狀態（拿掉 `setup.ruleset`、`final_state.ruleset`，其他鍵沒剝）。10 張一般圖（bridge_chasm、cliff_outpost、dark_forest、frozen_lake、lava_crossing、narrow_halls、oil_depot、open_plain、ruined_fort、swamp）× 種子 1、2 ＋ 4 張頭目圖（bandit_lair、rift_gate、cloud_summit、molten_heart_pit）× 種子 3～12。

- 只做完第 4 項：`battles=60 events=23897 different=4`。
- 四項都做完：`battles=60 events=23897 different=4`，四場與上面完全相同（只第 4 項 vs 全部做完：`different=0`）→ 吸收表面、疾病擴散、鉤對既有戰鬥沒有任何影響。
- 4 場差異（都由「推不動算撞擊」造成：效用 AI 吃預覽，推拉推不動的目標現在有撞擊傷害收益，所以會選）：

| 戰鬥 | 第一個不同 | 原因 | 勝方／輪數（前 → 後） |
|---|---|---|---|
| cloud_summit 5 | 第 2 輪，主角改放颶風踢 | 推陣眼石（`immovable`）→ 撞擊 1 次 | 敵／5 → 敵／7 |
| molten_heart_pit 5 | 第 4 輪，賽倫改放鉤索箭 | 拉灰燼之心（巨型）→ 撞擊 1 次 | 敵／6 → 敵／6 |
| molten_heart_pit 6 | 第 3 輪，主角改放颶風踢 | 目標是灰燼之心，這次沒命中（沒有撞擊），之後亂數錯開 | 敵／5 → 敵／5 |
| rift_gate 4 | 第 3 輪，賽倫改放鉤索箭 | 目標是源晶柱（`immovable`），傷害直接打倒（沒走到推拉），之後錯開 | 敵／6 → 敵／6 |

## 4. 測試與檢查

分目錄、一次一組、`-n 8`，不帶 `-m`（CLI 快照另跑 slow）。全部結束碼 0。

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0 |
| `mypy`（1675 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（691 檔、429 技能） |
| 新增引擎測試 `tests/engine/test_immovable_collision_sk2.py`（12）、`test_absorb_surface_sk2.py`（21）、`test_contagion_sk2.py`（11，含 hypothesis 種子性質）、`test_hook_sk2.py`（10） | 54 passed；每個都有「同輸入同結果」與預覽不改狀態 |
| 相關引擎檔（碰撞、巨型 gb1a／gb1b、種族、召喚、位移 AI、技能原語／形狀／預覽、確定性、clone、暫停點序列化…）＋`tests/content`＋`tests/narrative`＋`test_primitive_coverage`＋`test_architecture` | 0（最後一輪 4360 passed） |
| `tests/skillgen` | 0（4440 passed、14 skipped） |
| `tests/llm` | 0（495 passed；第 1 項後跑，之後沒改 LLM 相關） |
| `tests/api` | 0（1320 passed、1 skipped） |
| `tests/world` | 0（1328 passed） |
| `tests/roguelite` | 0（278 passed） |
| `tests/cli -m slow`（CLI 輸出快照） | 0（44 passed）；預測 0 鍵會變，實際沒有重產 |
| 前端 `tsc`、`vitest run`（全部） | 0、0（371 檔 4682 passed） |
| 紀錄＋重播 `open_plain` 7、`molten_heart_pit` 5 | 都「重播驗證通過」 |

沒跑 `scripts/check.py` 全量、`tests/sim`、平衡量測與模擬（不變比對以外）。

## 5. 實機（截圖）

開發頁 `client/dev/sk2-gallery.html?case=…`（自己起 vite `127.0.0.1:5291`；無頭 Chrome `--headless=new --mute-audio --remote-debugging-address=127.0.0.1`，除錯埠 9733、`--force-device-scale-factor=1`＋CDP `deviceScaleFactor 1`，量到 `devicePixelRatio = 1`；網址帶 `mute=1`；1100×500）。開之前兩個埠都沒人聽；結束時只停了自己起的 vite 與 Chrome，兩個埠都沒在聽。事件是真引擎跑出來的（產生腳本：`tests/engine/helpers` 組場 → `resolve` → `model_dump`＋`describe_event`，寫進 `client/src/dev/fixtures/sk2Events.json`；腳本在 scratchpad，未 commit），畫面資料照產生事件的戰場手抄，走正式 `playbackPlan → frameOps → BattleRenderer`。每張三格：施放前、演出中（停格）、結算後，上方是紀錄文字。

- `docs/art/shots/sk-2/absorb.jpg`：吸走腳下的冰，火球變冰霜彈（演出中彈體是冰色），結算後冰不見。
- `docs/art/shots/sk-2/contagion.jpg`：帶會擴散燃燒的盜賊1被打倒，燃燒傳給相鄰的盜賊2。
- `docs/art/shots/sk-2/hook.jpg`：鉤住第一個敵人拉 3 格到身邊，後面的不動。
- `docs/art/shots/sk-2/hook_lava.jpg`：中間有岩漿，停在岩漿前一格。
- `docs/art/shots/sk-2/hook_giant.jpg`：鉤打巨型頭目（灰燼之心外觀），不動、受一次撞擊。

實機未看：浮字（「吸收」「會傳染」「擴散」「推不動！撞擊」）是戰鬥畫面的 DOM 層，開發頁沒有畫（有 `feedback.test.ts` 之外的 vitest 覆蓋事件 → 原語；字樣沒有專屬測試）；真人戰鬥裡用不到這三個原語（沒有內建技能、沒有骨架）。鉤的演出是暫借的一般彈體＋拉扯，沒有繩索。

## 6. 新增 `# noqa`

沒有。`targeting.compute_area` 超過 `PLR0912` 時把「依原語縮小範圍」拆成 `_narrowed`。

## 7. 待 PM 決定

1. **接進出題**（規格要求寫進報告由下一段接）：三個原語要放進哪些骨架的 core／secondary，並同時加進組合器的 `_HAND_WRITTEN_PRIMITIVES`（或決定讓組合器抽）、`skill_composer.yaml` `llm_topic.core_exclude`、LLM schema；不然放進骨架會改掉組合器與 LLM 題目的種子 → 技能。也還沒有任何內建示範技能。
2. **吸水 → 潮濕**（6.38-4 原文例子）：水、油、煙霧沒有元素，`gain: element` 目前不吸它們。要做的話需要定「潮濕」是什麼（例：命中時在目標格造水，同 `wet` 灌注）。屬規則，照守則先不做。
3. **「因任何原因推不動」的範圍**：照字面把穩固 1 → 0 格、獸人沉穩重心減到 0、穩若磐石都算撞擊；種族技的無害推拉不算。若只想限位移免疫與巨型頭目要改。
4. **疾病擴散一次倒下帶多種狀態**：目前全部傳給同一個人；另一種讀法是只傳一種。傳過去的狀態仍會擴散（連鎖）。
5. **吸收表面的收益數值、鉤的 6 點與冷卻 3、疾病擴散 2 點、半徑 1**：初值，放工坊（`skill_budget.yaml` `hook_min_cooldown`、`core.yaml` `contagion_*`；預算點數在 `skill_primitives.yaml`）。工坊欄位白名單 `tuning_fields.yaml` 沒加（沒有對應的技能可調）。
6. **AI**：`contagion` 的標記沒有預覽收益，效用 AI 不會為它加分；鉤、吸收表面靠預覽事件。要不要給估值待決。
7. **美術**：三個原語的 Q 版部件、鉤的繩索演出、吸收表面的吸入特效都是暫借；狀態「會擴散」沒有畫面標示（狀態框看不出來）。
8. **和 SK-1 的合併點**：`client/src/render/qIcon/qIconSkills.test.ts` 的數量那一行（SK-1 加條件也會改同一行）、`tests/skillgen/test_workshop_feedback.py` 的條數、`content/workshop_text.yaml` 尾端；`LOG_FORMAT` 如果 SK-1 也升要改成 `/130`。
