# 階段 SK-3b 報告：SK-3 新觸發、重擲接進出題＋玩法答覆（含追加 12～14）

> 2026-11-19，實作者（SK-3b）。規格 `docs/phases/PhaseSK-3b計畫.md`（main `638b60b95`）＋開發 PM 追加第 12～14 項；答覆來源玩法交接 4.1.28、4.1.29 第 6 點、4.1.30。
> 分支 `worktree-agent-ab6b103a2e7cd3cc5`（起點 main `951650431`；中途合併 main `5527a2ecc` 拿 AR-SK3）。不 push。
> 數字一律是初值，接工坊；沒有試數值、沒有跑平衡量測與模擬（戰鬥不變比對與紙面小樣本除外）。沒有改 `docs/design/`、`config/`；沒有存檔遷移或刪除。

## 結果（一兩句）

規格 1～11 與追加 12～14 都做完；戰鬥不變比對 60 場 **different=0**（第 10 項後、第 1～2 項後、全部做完後各跑一次）。新觸發與重擲能由組合器做出來（紙面 1200 招：被利用時被動 18、重擲反應 104），兩個串流機率設 0 時 1200 招和改前逐字相同；4 招示範都過驗證並有實跑測試。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 「利用」多算條件型、符文 | 完成 | `c6e4e98ca`（和第 2 項同一個 commit，見下） |
| 2 每回合最多 1 次（任何單位的回合；被動與詞條同一套） | 完成 | `c6e4e98ca` |
| 3 接進出題（組合器、LLM、挑選模式；重擲進反應骨架） | 完成（裝備詞條見待決 3） | `839436919` |
| 4 示範技能 4 招 | 完成 | `a71fc8bcc` |
| 5 工坊白名單補 SK-3 新數值 | 部分（見待決 4） | `dfe4e1d37` |
| 6 重擲、戰前佈置照 SK-3 現狀 | 不用改 | — |
| 7 後端輸出 `contagious` | 完成 | `cf732723c` |
| 8 「會傳染」→「會擴散」、傳給一名同伴 | 完成 | `90c4027bb` |
| 9 `contagious` 實機截圖 3 張 | 完成（另加 2 張最近鄰放大） | `a10cd99c6` |
| 10 鉤、疾病擴散、吸收表面的點數搬到 `skill_budget.yaml`＋白名單 | 完成 | `de34e495e` |
| 11 吸收表面說明補「吸水會讓這招帶潮濕」 | 完成 | `39f9137c4` |
| 12 閃現舊模板 `reshape_shape` 前綴「擴散」→「易形」 | 完成 | `d89f8485c` |
| 13 戰前佈置實機截圖（選招前、選招後金色記號） | 完成（另加 1 張滑過） | `a10cd99c6` |
| 14 「放在這裡」超出地圖時翻到左邊＋單元測試；800 寬最近鄰 | 完成 | `bf3cd3be1` |

第 1、2 項共用同一批引擎檔（`skill_triggers.py`、`state.py`、測試檔 `test_exploit_sk3b.py` 兩項都測），拆開會讓中間 commit 的測試不完整，所以同一個 commit。

## 1. 各項做法

### 1.1 「利用」多算兩種（第 1 項）

- **條件型**（新模組 `engine/skills/exploits.py`）：`Cast.resolve_effect` 在效果**結算之前**找出效果條件因為下列原因成立的對象，結算後 `ctx.events` 裡有作用在那個單位（`target_id`／`unit_id`）或那一格（`pos`）的事件才算「真的生效」，交給 `collect_exploit(製造者, 施放者)`：
  - `target_has_status`：目標身上那個狀態的 `StatusInstance.source_id`（沒有來源不算）；
  - `target_on_surface`：目標格的 `Tile.surface_creator`（地圖原有、天氣、蔓延不算）；
  - `on_own_rune`（符文被讀取）：製造者＝施放者自己。
  - `any_of` 的每個成立分支各算一筆；落空、抵抗、推不動、擋住（`effect_fizzled`、`status_resisted`、`push_resisted`、`move_blocked`、`conduct_blocked`）不算生效。
  - 技能層級的條件：`Cast.run` 在效果結算前同樣判斷（`subjects_of` 裡條件成立的對象），全部效果與連擊打完後看有沒有作用在對象的事件。
- **符文被引爆**：`effects/world._detonate_rune` 移除符文後 `collect_exploit(刻的人, 刻的人)`（只有刻的人引爆得了）。
- 符文的利用沒有狀態也沒有表面，所以只觸發沒指定 `status`／`surface` 的被動與詞條。
- 層數不算；誰利用都算（自己、隊友、敵人都有測試）。
- 沒有任何單位帶這個觸發時 `collect_exploit` 直接返回（不取亂數、不改狀態），所以既有戰鬥不變。

### 1.2 每回合最多 1 次（第 2 項）

- `UnitState.exploit_turn_counts`（被動技能 ID 或詞條 ID → 次數；空的不輸出，`clone` 已補）。
- `turns.start_turn` 對**全體**單位呼叫 `skill_triggers.reset_exploit_counts`：「回合」是任何一個單位的回合，所以同一輪裡換一個人行動就能再觸發。
- 被動：`_usable` 對這個時機改看每回合計數、不看 `max_per_round`；`_pay` 記每回合計數、不記 `trigger_counts`。
- 詞條：`gear/triggers._resolve_trigger` 對這個時機一律用每回合計數（不看 `limit`）。
- `TriggerSpec` 的 `max_per_round` 仍只能是 1（schema、LLM、工坊不變），說明改成引擎不看它。
- `LOG_FORMAT` `/130 → /131`（`docs/phases/戰鬥紀錄格式變更.md` 加一條；測試裡寫死的版號 10 檔＋4 個 `endswith`）。

### 1.3 接進出題（第 3 項）

- **組合器**（都用獨立串流，主串流不動）：
  - `composer.exploit`（`skill_composer.yaml` `structure.exploit_passive_permille: 70`）：被動（史詩以上、題目沒指定關鍵字）改用「你造的關鍵字被利用時」，組法用 `composer.exploit.build`；一半機率縮小到某種狀態或表面（從關鍵字推導表 `uses` 裡的「目標有狀態」「消耗狀態」「目標站在表面上」挑）。
  - `composer.reroll`（`reroll_reaction_permille: 100`）：反應技（稀有以上、法術或不限類別、題目沒指定關鍵字）改成重擲，時機在兩個裡抽、形狀自身、代價照反應技的抽法、縮放屬性敏捷或體質。
  - 沒抽中、或抽中但 30 次都組不出合格技能 → 回傳 `None`，照原本流程（主串流沒推進）。
  - `reroll` 加進 `_HAND_WRITTEN_PRIMITIVES`（一般抽選不抽）。`on_keyword_exploited` 的 `random_composer` 仍是 false（一般抽選不抽）。
- **挑選模式**：候選由組合器產生，所以自動帶得到；沒另外加打分（4.1.30）。
- **反應骨架**：核心多 `reroll`。
- **LLM**：反應事件清單 `proposal/builder.LLM_REACTION_EVENTS`＝`SKILL_REACTION_EVENTS`＋兩個重擲時機（schema 的 `event` 列舉與題目區的反應列表都用它）；觸發清單本來就照 `skill_triggers.yaml` 全部列，新觸發的 `llm_hint`、`description_zh`、工坊玩家文字改寫成四種利用與每回合一次。`skill-proposal/20 → /21`（和第 8 項的改字共用一次升版；system 快照雜湊同 /20）。
- **重擲的預算**（必要的改動，見待決 1）：固定 5 點時，連階級 1 的反應技都只到預算 60%（低於下限 70%），組合器、LLM、示範招都做不出合格的重擲。改成 `budget_basis: reroll`：點數＝階級預算 × 反應技係數 × `skill_budget.yaml` `reroll_budget_permille`（初值 850‰；沒有代價時剛好 85%）。
- 卡片的反應時機字補上「隊友擲失手時」「敵人擲中你時」（名詞表；`narrative/skills.REACTION_TIMING_TEXT`、`engine/view.REACTION_TRIGGER_TEXT`）。

### 1.4 示範技能 4 招（第 4 項）

| ID | 名稱 | 內容 | 預算 |
|---|---|---|---|
| `skill_ember_resonance` | 餘燼共鳴 | 被動，史詩 1 階：你造的燃燒被利用時，護盾 1d3＋專注 +1 | 95.2% |
| `skill_tidal_draw` | 潮引 | 被動，史詩 1 階：你造的水被利用時，護盾 1d4＋回 1 法力 | 76.2% |
| `skill_fate_deflect` | 命運偏折 | 反應，稀有 1 階：敵人擲中你時逼他重擲取較差，法力 2 | 84.2% |
| `skill_lucky_whisper` | 幸運低語 | 反應，稀有 1 階：身旁隊友擲失手時讓他重擲取較好，法力 2 | 84.2% |

- 被動骨架的核心不收 `add_stack`／`restore_resource`，照鷹眼、怒火中燒的前例借一個小護盾當核心；護盾骰子取「放得進預算」的那一格（1d4 會超出 107%，所以餘燼共鳴用 1d3）。見待決 2。
- 沒有放進任何 build 或單位（`builds.yaml` 是模擬回歸範本），列進 `tests/content/test_coverage.py` 的 `_POOL_ONLY`。

### 1.5 工坊白名單（第 5 項）

- 核心戰鬥規則：`reroll_ally_range`（重擲：幫隊友的範圍）。
- 技能預算表：`reroll_budget_permille`（重擲的預算 ‰）；第 10 項另加 `hook_points`、`contagion_points`、`absorb_surface_points`。

### 1.6 `contagious`（第 7、9 項）

- `engine/view.StatusView.contagious: bool | None`，只在 True 時有值，`exclude_if` None 不輸出——所以既有狀態 JSON、CLI 與 API 快照逐字不變。OpenAPI 只多一個選填欄位，已重產 `client/openapi.json`、`schema.d.ts`；前端 `api/types.ts` 拿掉手寫的交集型別，直接用產生的型別。

### 1.7 用字（第 8、11、12 項）

- 疾病擴散：`llm_hint`、`player_description`、工坊玩家文字改成「會擴散……傳給身邊 1 格內的一名同伴；身上有好幾種時只傳一種，傳過去的仍會擴散」（照 4.1.28 第 6 點的定案句）；工坊欄位 `contagion_radius` 的標籤「傳染距離」→「疾病擴散的距離」。開發者說明 `description_zh` 本來就寫「會擴散」，沒動。
- 吸收表面 `player_description` 補「吸水會讓這招帶潮濕」（名詞表 `glossary.json` 跟著變）。
- `flash_templates.yaml` 的 `reshape_shape` 前綴「擴散」→「易形」。**只改了這一個**；`skill_evolution.yaml` 的 `reshape`（閃現大變化 `major_reshape` 用它，名稱「擴散・破甲連擊」這類）也是「擴散」，沒動（待決 6）。

### 1.8 點數搬家（第 10 項）

- `skill_budget.yaml`：`hook_points: 6`、`contagion_points: 2`、`absorb_surface_points: 1`（值不變）；`skill_primitives.yaml` 拿掉三個 `base_points`，`budget_basis` 改成 `hook`、`contagion`（新）與 `absorb_surface`（讀新欄位）；說明文字與工坊原文（`workshop_text.yaml` 的 `source`）同步改。
- 驗證：閃現對照 216 鍵整份提議逐字相同、戰鬥不變比對 different=0、`trpg content check` 429 招通過。

### 1.9 前端小修（第 14 項）

- `render/prepMarks.tipPlacement`（純函式）：格子右邊放得下就在右邊，會超出地圖右緣時翻到左邊；`placeTip` 多 `side` 參數，小三角跟著換邊；`highlightLayer` 用它。測試 `render/prepTipSide.test.ts`（3 個）。

## 2. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive main`（`951650431`）的 `src content config tests scripts` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；整份事件、步驟、最終狀態（去掉 `ruleset`、`ruleset_hash`、`format`）比 SHA-256。10 張一般圖（bridge_chasm、cliff_outpost、dark_forest、frozen_lake、lava_crossing、narrow_halls、oil_depot、open_plain、ruined_fort、swamp）× 種子 1、2 ＋ 4 張頭目圖（bandit_lair、rift_gate、cloud_summit、molten_heart_pit）× 種子 3～12，同 SK-2、SK-2b。

| 時間點 | 結果 |
|---|---|
| 第 10 項做完（點數搬家） | `battles=60 events=23897 different=0` |
| 第 1、2 項做完（條件型利用、符文、每回合計數、`/131`） | `battles=60 events=23897 different=0` |
| 全部做完（含示範 4 招、組合器串流、重擲預算、卡片字；最後一個程式 commit `a71fc8bcc`） | `battles=60 events=23897 different=0` |

- 「利用」多算兩種之後，既有詞條或被動**沒有**多觸發：地圖預設陣容的單位、build 與內容詞條沒有一個帶 `on_keyword_exploited`（示範 2 招只在內容庫；`collect_exploit` 沒有持有者就直接返回），所以不需要逐場說明。
- 另外 `trpg battle --map open_plain --seed 7` 紀錄＋重播：「重播驗證通過：91 個動作、383 個事件」。

## 3. 紙面小樣本（不呼叫 LLM）

腳本在 scratchpad：`compose_random_skill`，被動（史詩）× 階 1、2 ＋ 反應（稀有、史詩）× 階 1、2 × 種子 0～199＝1200 招，和改前副本逐招比。

| 骨架 | 新東西 | 次數 | 例 |
|---|---|---|---|
| 被動（400 招） | 你造的關鍵字被利用時 | 18（任何 13、燃燒 2、水 2、標記 1） | `passive/epic/1/30`（任何）、`passive/epic/1/166`（燃燒）、`passive/epic/1/126`（水） |
| 反應（800 招） | 重擲 | 104（隊友擲失手時 48、敵人擲中你時 56） | `reaction/rare/1/12`、`reaction/rare/1/25` |

- 1200 招都通過 `validate_skill`（invalid 0）。
- 和改前比：1078 招逐字相同、122 招不同而且**都**帶新觸發或重擲；沒有「不同但沒帶新東西」的招（沒抽中或組不出來時主串流完全沒動）。
- **兩個機率設 0：1200 招和改前逐字相同。**
- 測試 `tests/skillgen/test_sk3_offers_sk3b.py` 另外鎖：機率 1000 時被動、反應（稀有、史詩 × 階 1～3）都做得出合格的；沒抽中的種子和機率 0 逐字相同；武器類反應不出重擲；LLM 反應清單；重擲預算隨階級。

## 4. 快照、夾具、版號（先預測再逐鍵核對）

| 東西 | 預測 | 結果 |
|---|---|---|
| parity `flash`（126 鍵） | 第 12 項不變（`reshape_shape` 在樣本裡沒有出現）；第 3、4 項不變（閃現不走新串流） | 先把改前／改後整份提議倒出來比：**126 鍵逐字相同**（第 12 項後、第 10 項後、第 4 項後各比一次） |
| parity `complete`／`retier` | 既有 429 招不變；多 4 招示範 | 既有鍵不變（`-m slow` 全過）；只用腳本加 4 招示範的 8 個值，沒有整份重產 |
| CLI `skills_list`、`skills_show_all/00～15`（17 鍵） | 多 4 招：清單多 4 招兩行＋總數 429→433；分片大小 ⌈429/16⌉＝27 → ⌈433/16⌉＝28，16 片全部位移 | 先把改前／改後 `skills list` 與每招 `skills show` 的文字倒出來比：清單只有「共 433 個」與 4 招 8 行不同；**既有 429 招的 `show` 逐字相同**。只用 `UPDATE_CLI_SNAPSHOTS=1 -k "skills_list or skills_show_all"` 重產這 17 鍵 |
| CLI 其他鍵（戰鬥） | 不變 | `-m slow tests/cli` 44 passed，沒重產 |
| 技能圖示 `skill_icons.json` | `skills` 多 4 招；`random`（組合器 50 個種子）只有抽中新串流的種子變；`workshop` 不變 | `skills` 只多 4 招；`random` 只有第 30 個變（反應技，改前是「擋攻擊＋護盾」，改後抽中 `composer.reroll` 成了重擲／敵人擲中你時）；照 `tests.narrative.icon_fixture` 重產 |
| `glossary.json` | 第 8、11 項：疾病擴散、吸收表面的說明；第 3 項：新觸發的說明 | 只有這 3 筆 |
| `unitDolls.json`、`raceLooks.json`、`skillCards.json` | 不變 | `export_client_fixtures.py` 重產後無差異 |
| OpenAPI | 第 7 項多 `StatusView.contagious`（選填）；其他不變 | `client/openapi.json` 多 11 行、`schema.d.ts` 多 2 行 |

**版號**

| 版號 | 變動 |
|---|---|
| `LOG_FORMAT` | `trpg-battle-log/130` → **`/131`**（第 1、2 項：結算規則與 `UnitState` 欄位） |
| `PROMPT_VERSION`（技能提議） | `skill-proposal/20` → **`/21`**（第 8 項的 `llm_hint`、第 3 項的反應清單與骨架；system 快照雜湊同 /20） |
| `WLOG_FORMAT`、`CHAR_FORMAT`、`SAVE_FORMAT`、`WORLD_RULES_VERSION`、`flash-*` | 不升 |
| `ruleset_hash`、`content_digest` | 變（原語表、預算表、骨架、觸發表、組合器表、閃現模板、新技能） |

**改到的既有測試**（斷言沒有放寬）：
- 版號字面值：`trpg-battle-log/131` 10 檔、`LOG_FORMAT.endswith("/131")` 4 檔；`tests/llm/test_prompts.py` 加 `/21` 快照。
- 新欄位、新招要跟著更新的清單：`test_state_clone.py`（`exploit_turn_counts`）、`test_coverage.py`（拿掉 `on_keyword_exploited`、`reroll` 的未使用例外；4 招示範列進 `_POOL_ONLY`）、`test_skills_content.py`（未使用原語拿掉 `reroll`）、招數 429→433（`test_skill_scaling.py`、`test_skill_icon_art_qi2a.py`、前端 `qIconSkills.test.ts`）、技能檔數 426→430（`test_tuning_fields_nw2a.py`、`test_yaml_patch_nw2a.py`）、前端 `qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE` 加 4 招、`test_rules_budget_bs1.py` 的工坊欄位清單、`test_polish_3c6a.py`（卡片反應時機表多重擲兩個時機）。
- 行為改了、照新規則改期望：`test_keyword_exploited_sk3.py`（被動改記每回合計數，不記每輪次數）、`test_random_composer.py`（反應技的事件多重擲兩個）。
- 鎖舊樣本：`test_upgrade_topup.py` 的「補強順序分布表」靠 LLM 題目抽到哪個核心，反應骨架多了重擲後樣本換一批 → 加 `without_sk3b_offers()`（反應骨架拿掉重擲），斷言照舊（同 SK-2b 的 `without_sk2b_offers`）。
- 示範招已在內容庫：`test_exploit_sk3b.py`、`test_reroll_sk3.py` 的場景組裝跳過內容庫已有的技能（否則 `SkillTable` 重複 ID）。

## 5. 測試與檢查

分目錄、`-n 8`（`tests/llm` 與 `tests/skillgen` 沒有同時跑）；最後一輪全部是改完之後跑的。

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check src tests scripts` | 0 |
| `uv run ruff format --check src tests` | 0 |
| `uv run mypy`（1701 檔） | 0 |
| `uv run lint-imports`（14 kept） | 0 |
| `uv run trpg content check`（695 檔、433 招） | 0 |
| `pytest tests/engine`（5039；跑完後修 1 個 `test_polish_3c6a`，單檔重跑 0） | 0 |
| `pytest tests/content tests/narrative`＋`test_polish_3c6a`（3619） | 0 |
| `pytest tests/skillgen`（4555 passed、14 skipped） | 0 |
| `pytest tests/llm`（495） | 0 |
| `pytest tests/api`（1323 passed、1 skipped；跑完後修 1 個 `test_yaml_patch_nw2a`，單檔重跑 0） | 0 |
| `pytest tests/world tests/roguelite`（1609，單獨重跑） | 0 |
| `pytest -m slow tests/cli`（44） | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py`（含 complete／retier／flash） | 0 |
| `pytest tests/test_architecture.py` | 0 |
| 前端 `tsc --noEmit` | 0 |
| 前端 `vitest run`（全部，381 檔、4735） | 0 |
| 前端 `build` | 0 |
| 紀錄＋重播 `open_plain` 7 | 「重播驗證通過」 |
| 戰鬥不變比對 60 場 | different=0 |

新測試：`tests/engine/test_exploit_sk3b.py`（18：條件型的狀態、表面、技能層級、失手不算、別人造的不算、條件不成立、篩選、自己與敵人利用、符文引爆與讀取、每回合一次與換人行動後再觸發、詞條同一套計數、確定性與 JSON 往返、預覽不改狀態、沒有持有者時不變）、`test_sk3b_demo_skills.py`（9）、`test_contagious_view_sk3b.py`（2）、`tests/skillgen/test_sk3_offers_sk3b.py`（15）、前端 `render/prepTipSide.test.ts`（3）。

沒跑：全量 `scripts/check.py`、`tests/sim`、平衡量測與模擬（不變比對以外）。

## 6. 實機截圖

`trpg serve` 埠 8765（前端用 `pnpm build` 的 `client/dist`，`TRPG_SAVE_DIR` 指到暫存區）、無頭 Chrome `--headless=new --mute-audio --remote-debugging-address=127.0.0.1 --force-device-scale-factor=1` 除錯埠 9735、CDP `deviceScaleFactor 1`、網址帶 `mute=1`。開之前兩個埠都沒人聽；結束時只停了自己起的 `trpg serve` 與 Chrome，兩個埠都已關閉。腳本在暫存區（未 commit）：頁面 `window.fetch` 包一層，把開發模式「一鍵開局」的建立戰鬥請求改掉。

**`contagious`（第 9 項，`docs/art/shots/ar-sk2/`）**：火焰流英雄（`open_plain` 種子 3）換上一招工坊技能「疫火」（施加燃燒 3 回合＋疾病擴散），包裝在開戰後先跳過戰前佈置、對敵人施放到有狀態被標成會擴散為止（2 次），把那一步的回應交給頁面。

| 檔案 | 內容 |
|---|---|
| `11-live-field-1600.jpg` | 1600×900 實戰：盜賊2（4, 3）頭頂狀態列的燃燒有「會擴散」孢子記號 |
| `11b-live-1600-nearest-x6.png` | 上圖盜賊2 那一塊 80×80 真 1 倍 × 6 最近鄰 |
| `12-live-field-800-true1x.png` | 800×600 真 1 倍（地圖自動 62%） |
| `12b-live-800-nearest-x8.png` | 上圖盜賊2 那一塊 55×50 × 8 最近鄰 |
| `13-live-status-card.jpg` | 釘選盜賊2 的單位卡、點開燃燒的狀態卡：名稱旁「會擴散」標籤＋說明一行 |

**戰前佈置（第 13 項，`docs/art/shots/ar-sk3/`）**：陷阱流英雄（`open_plain` 種子 3），開局停在戰前佈置。

| 檔案 | 內容 |
|---|---|
| `13-prep-live-before.jpg` | 選招前：佈置視窗（捕獸夾、灰燼地雷、不佈置直接開戰）；地圖上還沒有記號 |
| `14-prep-live-picked.jpg` | 選了捕獸夾：起始區唯一可放的那一格換成金色四角括號＋中央金菱形 |
| `15-prep-live-hover.jpg` | 滑過那一格：金框＋捕獸夾的半透明預覽；「放在這裡」被格子資訊卡蓋住（待決 10） |

**最近鄰**（第 14 項）：專案沒有 Pillow，放大圖用暫存區的 `zoom.html`（canvas `imageSmoothingEnabled = false`、CSS `image-rendering: pixelated`）在同一個無頭 Chrome 畫、截圖，是真的最近鄰。

實機未看：「放在這裡」翻到左邊的那一側（這張圖的可放格在地圖左緣，提示框在右邊；翻邊只有單元測試）；戰場狀態列在地圖縮放 > 1.55 時的排法（AR-SK3 的範圍）。

## 7. 新增 `# noqa`

- `skillgen/random_composer._attempt_passive`：`# noqa: PLR0917`（多一個選填的 `timing_id` 參數變成 6 個位置參數；既有呼叫照舊用位置參數，改成關鍵字參數要動到別處的呼叫）。


## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| # | 事項 | 我的做法 | 其他選項 |
|---|---|---|---|
| 1 | **重擲的預算**（數值／算法） | 固定 5 點做不出合格的招（階級 1 只到 60%、階級 3 只到 36%），改成「階級預算 × 反應技係數 × `reroll_budget_permille`（初值 850‰）」，隨階級長，已開工坊 | 改回固定點數但換個數字；或給重擲反應技登記預算例外 |
| 2 | 示範被動的核心效果 | 被動骨架核心不收 `add_stack`、`restore_resource`，照鷹眼、怒火中燒的前例借小護盾（1d3、1d4）當核心；技能的主效果仍是 +1 專注、回 1 法力 | 把這兩個原語加進被動骨架的核心（會改到組合器的被動抽選，要另外處理種子） |
| 3 | **裝備詞條**的「接進出題」 | `TriggerAffix` 本來就能用這個觸發（SK-3），引擎也照每回合一次；但**沒有新增任何內容詞條**：加一條觸發類詞條會改到物品產生器稀有／史詩的抽選，掉落、三選一的種子全部換一批（大世界規則版號要升） | 新增一條詞條（例：「你造的燃燒被利用時回 1 法力」），並排一段處理掉落樣本 |
| 4 | 工坊白名單只加了兩個 SK-3 數值 | 加了 `reroll_ally_range`、`reroll_budget_permille`；新觸發的係數 300（`skill_triggers.yaml`）與兩個組合器機率（`skill_composer.yaml`）不在任何可開的對象種類裡，要開得新增對象種類（改程式），沒做（SK-2b 的四個組合器機率也一樣沒開） | 新增 `skill_triggers`／`skill_composer` 對象種類 |
| 5 | 「利用」的條件型範圍 | 只看施放（`Cast`）的技能層級與效果層級條件；**修正規則**（例：火焰循環、灼疤這類「目標燃燒中時傷害提高」的被動修正）的條件成立不算利用；變奏的 `when` 也不算 | 修正規則的條件成立、而且那次攻擊命中時也算 |
| 6 | `skill_evolution.yaml` 的 `reshape` 前綴也是「擴散」 | 只照指示改 `flash_templates.yaml` 的 `reshape_shape`；閃現大變化「換個形狀」的名稱仍是「擴散・○○」（閃現對照樣本裡有 87 個這種名稱） | 一起改成「易形」（會改到閃現對照夾具 87 處的名稱，要逐鍵核對） |
| 7 | 組合器新串流的條件 | 題目指定關鍵字時不走（被動、反應技都是）；反應技指定武器類別時不出重擲；機率 70‰／100‰ 是「和一般時機、事件被抽到的機會相當」的初值 | 關鍵字題目也能出（要先定義哪些關鍵字配得上「被利用時」） |
| 8 | 被利用時與關鍵字推導 | `skill_keywords.yaml` 沒把 `on_keyword_exploited` 算成任何關鍵字的「利用」，示範招不在任何關鍵字池 | 例：`{trigger: on_keyword_exploited, status: burning}` 算點燃的利用 |
| 9 | 戰前佈置畫面的舊字 | 實機截圖看到左上技能說明卡仍寫「點選格子上的目標（紅框 1 格）」，和 AR-SK3 換成金色記號不一致（不是本段的檔，沒改） | AR 段改字 |
| 10 | 「放在這裡」被格子資訊卡蓋住 | 實機滑過可放的格子時，格子資訊卡（「草地・高度 0・可通行」）疊在提示框上（`15-prep-live-hover.jpg`）；本段只做了翻邊 | 佈置模式時不顯示格子資訊卡，或提示框畫在更上層 |

其他：
- 第 3 項的 commit（`839436919`）改了新觸發的 `llm_hint`，長度 70 字超過 `tests/content/test_llm_hint.py` 的 60 字上限；當時只跑了直接相關的測試沒抓到，在第 4 項的 commit（`a71fc8bcc`）縮短。中間那個 commit 單看 `tests/content` 會有這 1 個失敗。
- 第 3 項的 commit 改了 `tests/engine/helpers.py` 但那一行超過 100 字，也在 `a71fc8bcc` 由 `ruff format` 修好。
- 開發 PM 的確認「疾病擴散只能寫在施加燃燒、流血、中毒之後」：維持 SK-2b 的 `cap.contagion_source`，沒改。
- `docs/dev/上手-引擎戰鬥結算.md` 第 56 點、`docs/dev/上手-LLM.md` 第十二節補了 SK-3b 的一段。
- `tests/world tests/roguelite` 第一次和 `tests/skillgen` 同時跑時有 2 個 xdist 工作行程異常結束（`node down: Not properly terminated`，沒有測試失敗訊息），改成單獨重跑（見第 5 節）。

## 開發 PM 裁定（2026-11-19）

合併：main `422ed9e3e`（--no-ff）。不變比對 60 場 different=0；`LOG_FORMAT` /131、`skill-proposal/21` 接受。

待決：
1. 重擲預算改成「階級預算 × 反應係數 × 850‰」：接受（初值，工坊可調）。
2. 示範被動借小護盾當核心：接受，照鷹眼、怒火中燒前例。
3. 裝備詞條不新增內容詞條：接受。新增一條會換掉掉落、三選一的種子，排進佇列，和下一次動到物品產生器的段一起做。
4. 新觸發係數、組合器機率開進工坊（新增對象種類）：排進佇列。
5. 修正規則的條件成立不算利用：規則類，轉玩法 PM。
6. `skill_evolution` 的 reshape 前綴「擴散」是否一起改「易形」：用字，轉玩法 PM；改的話要逐鍵核對閃現夾具 87 處。
7. 關鍵字題目不走新串流：接受（保守）。
8. `on_keyword_exploited` 是否算某關鍵字的「利用」：規則類，轉玩法 PM（和 5 一起）。
9. 佈置說明卡仍寫「紅框」、10. 「放在這裡」被格子資訊卡蓋住：前端小修，轉美術 PM，下一個 AR 段做。

中間兩個 commit（`839436919`）單看不乾淨，最終 commit 乾淨：接受，下次每個 commit 都要跑到相關檢查。
