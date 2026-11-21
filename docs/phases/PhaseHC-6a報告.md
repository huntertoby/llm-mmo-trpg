# Phase HC-6a 報告：後端說明文字裡的寫死數字改從資料帶入

依據：`docs/phases/PhaseHC-6a計畫.md`。基準：main `49fbb4773`（worktree 開工時就在這裡）。分支 `worktree-agent-ae28addd2dc0b0326`，沒 push。
沒改任何數值、沒改玩家看到的字（全部逐字比對 different=0，見第 4 節）。沒動 `docs/design/`、`config/`、`llm.toml`、`CLAUDE.md`、`.claude/`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 後端說明文字 | `c084fcbea` | 33 筆改成照規則、常數組字；101 筆改判 const（附理由）；`wish_cards` 組進許願提示詞與 schema 並開進工坊 |
| 2 順手項 | `db2e0e924` | `scripts/recipe_census.py` 的設計鍵帶召喚物種類 |
| 3 收尾 | `9ed577582` | 刪 17 條變成 0 筆的規則，`--md` 重產 `寫死數值-清單.md` |
| 報告 | 本 commit | |

## 2. text 筆數

- 範圍內（`narrative/`、`skillgen/`、`content/`、`engine/`、`world/`、`llm/`、`bot/`）：**159 → 26**（33 筆組字，101 筆改判 const）。
- 後端全部：193 → 60（另外 34 筆是 `api/`，留給 HC-6b）。前端 98 筆不動。
- `config` 少 2 筆：`llm/prompts/wish_pick.py` schema 的 `minItems`／`maxItems` 3 改讀 `wish_cards`。
- `classify.py --check` 結束碼 0，沒歸類 0。

## 3. 第 1 項：改了哪些

### 3.1 改成組字（字和以前逐字相同）

| 位置 | 原本寫死 | 改讀 |
|---|---|---|
| `narrative/skills.py` `mastery_text`、`skillgen/option_scaling.py` | 專精「+1」 | `engine.skills.scaling.MASTERY_BONUS` |
| `narrative/skills.py` `_hook` | 推拉 2 格上限 | `core.max_displace_distance` |
| `narrative/skills.py` 召喚物上限修正 | 最多 3 隻 | `core.summon_hard_cap` |
| `skillgen/budget.py` | 透支少 1 AP；n 必須是 2 或 3；每回合 1 次 | 透支狀態 `ap_penalty`；`budget_by_n_permille` 的鍵；`per_turn_limit` |
| `skillgen/option_followup.py`、`proposal_followup.py`（新 `followup_doc(library)`） | 兩段合計最多 4 個效果 | `skill_limits.max_effects` |
| `skillgen/option_params.py` | 冷卻縮短最多 2 | `skill_limits.max_cooldown_restore` |
| `skillgen/option_variant.py` | 稀有 1 個、史詩以上 2 個；替換 1～2 項；+1 格約 5% | `variant_max_by_rarity`；`max_variant_replacements`；`range_step_permille` |
| `skillgen/proposal_costs.py`（`COST_DOCS` 改成 `cost_docs(library)`） | 透支少 1 AP；失手反噬 1～2 個效果 | 透支狀態 `ap_penalty`；`llm_topic.max_nested_effects`（同 schema 的 `max_length`） |
| `skillgen/proposal/builder.py` 變奏模型說明 | 1～2 項替換 | `max_variant_replacements` |
| `content/battle.py` | 持續加成 1 或 2；footprint 1 或 3 | `_MAX_DURATION_BONUS`；`GIANT_FOOTPRINTS` |
| `content/composer_rules.py`、`equipment.py` | sides ≥ 2；combo N 至少 2 | `_MIN_SIDES`；`MIN_COMBO_N` |
| `content/library/giant_checks.py`、`world_situations.py` | 佔 9 格；危險度 1～3 | `size * size`；`_DANGER_LEVELS` |
| `engine/parts.py` | 4 格外 | `FAR_BEYOND + 1` |
| `world/opening.py`、`season_boss.py` | 4 級前；每天 6 點刷新 | `OPENING_END_LEVEL`；`calendar.refresh_hour` |
| `world/battlefield.py`（新 `fallback_zh(library, reason)`，`api/world_presenter.py` 改呼叫它） | 12×12；隔 3、2、1 格 | `field.cut_size`；三種開打距離由遠到近 |
| `bot/commands.py`、`service.py` | 3～20 字 | `USERNAME_MIN`／`USERNAME_MAX` |
| `llm/prompts/proposal.py`（新 `budget_note(library)`） | 預算 70%～100%；替換 1～2 項（不能 3 項以上） | `min_ratio_permille`／`max_ratio_permille`；`max_variant_replacements` |
| `llm/prompts/storyteller.py` | 1～3 句、150 字、24 字、60 字 | `world_narration` 的 `STORY_SENTENCES_MAX`、`TEXT_MAX_CHARS`、`ACTOR_MAX_CHARS`、`MOTIVE_MAX_CHARS` |
| `llm/prompts/wish_pick.py`、`llm/wish_pick.py` | 3 張（含 JSON 範例的「三張」）、schema 3 張 | `skill_pick.pool.wish_cards`（`build_wish_pick_messages(card_count=)`、`wish_pick_schema(cards=)`） |

- **提示詞逐字相同，`PROMPT_VERSION` 沒升**（proposal、storyteller、wish-pick 三個版本號都不變；`test_prompts.py` 的雜湊快照也通過）。
- `wish_cards` 開進工坊：`content/tuning_fields.yaml` 的「技能挑選模式」表，放在「許願池：候選量」下一格；新測試 `tests/api/tuning/test_workshop_open_hc6a.py`（值與說明、合法值通過、大於候選量被擋、提示詞照張數寫）。`tests/llm/test_wish_pk4.py` 只補 `cards=` 參數。

### 3.2 改判 const 的清單（101 筆）

照 `classes.yaml` 的分類規則，每條規則的 `note` 都寫了理由。分類：

| 理由 | 例子 |
|---|---|
| ‰ 換算（1000＝×1、±100%） | 抗性 -1000～1000‰、`kind_permille` 總和 1000、階梯從 1000 開始、`power_permille` 小於 1000、預算區間上界 100% |
| 非空、非零、正數、非負檢查 | 至少 1 個標籤／效果／出口／敵人、size 至少 1×1、非 0 的 delta、下限 ≥ 0、距離至少 1 格 |
| 唯一性、結構 | 恰好 1 個核心、主城恰好 1 個傳送石、每區 1 個小鎮、郵差 1 個站位、白板只能 1 個核心、同時 1 個誓約（單一欄位）、自身狀態代價一招 1 個 |
| 下限（引擎 `max(0／1, …)`） | 冷卻最少 0、AP 最少 1、召喚物上限最少 1 隻、移動點數最低 0、HP 不低於 1 |
| 序號、編號、引用 | 第 1 項、第 1 擊、第 1 個回合、原則 1、8.22.1 第 7 點、草稿待確認 2、天數 1 起、pick 0～N−1、從 0 起算 |
| 舉例、名字 | 例 2d6、×2＝加倍、例：上限 1 個時；3×3 形狀名；縮放依據「每少 10%／每距 1 格／每有 1 名」 |
| d20 | 暴擊範圍上界 20 |
| 基準點 | 召喚物小卡「基準值（1 級）」「施放者 1 級、修正 0 時」「每升 1 級」 |
| 逐格說法 | 每少走 1 格、每空 1 格、只引爆那 1 格、射程每 +1 格 |

新規則（都是 `status: done`）：`py-content-battle-const-text`、`py-content-composer-rules-const-text`、`py-content-equipment-const-text`、`py-content-item-budget-const-text`、`py-content-library-world-const-text`、`py-content-skills-skill-const-text`、`py-content-world-economy-const-text`、`py-llm-prompts-proposal-const-text`、`py-narrative-action-info-const-text`、`py-narrative-summon-info-const-text`、`py-world-growth-const-text`；另外 33 條原本的 text 規則改成 const（例 `py-narrative-skills-text-text`、`py-content-fields-text-text`、`py-content-hc4d-text`）。同一個函式裡有留 text、有改 const 的，用 `text:` 正規表示式分開（窄的寫前面）。

### 3.3 留在 text 的 26 筆（規則數字，但程式裡沒有可帶的資料）

要先把數字搬進 content（config 類的工作）才能組字，這段不改數值、不加欄位，所以留著：

- 「最多 1 個／1 條／1 名」類的上限（檢查本身寫死 `> 1`）：武器元素詞條每件 1 條、build 詞條與觸發詞條每件 1 條、規則改變型傳說每人 1 個、每個單位同時 1 個生效中的規則改變、一場最多 1 名精英、兩種觸發每輪最多 1 次。
- 引擎寫死：跑步每回合 1 次（`ran_this_turn`）、推動／撥開物件 1 格（4 筆）、圖騰拉近 1 格（2 筆）、召喚物絆倒與纏住每輪 1 次（2 筆）、塔盾「高 2 層以上無視」（塔盾視為 1 層高）。
- 寫死在檢查裡：靶場示範技要 1 階、道具技能 1 AP（8.17）。
- 在 Ruleset 層、`SkillDef` 驗證拿不到：傳說源力 1 或 2 點（`max_source_cost`）、數量型分歧 count 2（`max_summon_count`，2 筆）。
- 提議提示詞的 range_delta「只能填 1 或 2」：提議模型的 `Literal[1, 2]`（`proposal/builder.py`，config）寫死。
- 誓約冷卻「1 天內」：資料是 `cooldown_seconds`（秒），換成天的寫法要定（見待決 3）。

## 4. 驗收比對

腳本放在 scratch，沒進 repo：`textdump.py`、`valcases.py`、`jcmp.py`，沿用 HC-5b 的 `budget434.py`、`compare78.py`、`census_cmp.py`。改前用基準 `49fbb4773` 的 `git archive`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`，並確認載入的 `trpg` 路徑）。

| 比對 | 結果 |
|---|---|
| 敘事與卡片文字：438 招 `skill_card`（兩種參數）、438 招工坊選項 `draft_options`、31 個召喚小卡、119 個狀態、10 個層數、21 個召喚物的天生／行為說明、基本動作說明 | `items=1542 same=1542 different=0`（第 1 項後、收尾後各跑一次） |
| 提示詞（mock 收到的）：說書人 4 個場景、許願挑選的 messages 與 schema、提議 18 題（3 階 × 3 稀有度 × 主動／被動，含要求變奏的變奏說明）的 messages、送給約束解碼的 schema 與提議模型 schema | 同上一列，different=0；6 題被動 common／rare 本來就丟 `SubsetError`，前後相同 |
| 驗證訊息：持續加成超限、footprint 2、骰面 1、combo N 1、危險度少一筆、被動 n=5 的預算錯誤，加 Bot 指令說明、溶解限制、戰場退回原因、部位原因、代價說明、刷新時刻 | `items=13 same=13 different=0` |
| 逐招預算 438 招（`BudgetReport` repr＋違規） | 檔案逐位元組相同 |
| 78 場戰鬥（去掉 `ruleset_hash` 與內嵌規則包） | `battles=78 events=26206 different=0`；內嵌規則包 0 差異 |
| CLI 快照、parity、前端夾具 | 這段不重產；交件前由 check.py＋slow 測試確認（第 6 節） |

## 5. 第 2 項：`recipe_census` 設計鍵

`design_key` 的效果鍵在 `summon`、`summon_beside` 後面接 `@召喚物種類`；其他效果的鍵字串不變。新測試 `test_design_key_tells_summon_units_apart`。

- `--keywords summon --seeds 50`：薄格 **12 → 6**（正常 12 → 18，空 0、設計上不存在 12 不變）。設計數變多的格子：主動 1～4 階 rare／epic（例 2 階 epic 30 → 37）、被動 epic 1～4 階 8 → 15／43／42／41、反應 rare／epic 1 → 2／12／9／4。還是薄的 6 格是反應 1、3、4 階 rare／epic（2、9、4 個設計）。
- 其他關鍵字 `--seeds 4`（15 個非召喚關鍵字＋不指定，576 格）：
  - 不帶召喚設計的 `poisoned`、`form`、`fury`、`ki`、不指定：different=0。
  - 其他關鍵字的格子裡本來就有召喚的設計（例 ignite 的火靈召喚），所以 `top_designs` 的鍵字串多了 `@召喚物`；去掉設計鍵與設計數以外的欄位，576 格 different=0。設計數變多的只有 8 格（ignite 主動 2 階 rare、反應 2 階 rare／epic 3 → 4；prone 主動 2 階 rare 3 → 4、反應 2～3 階 rare／epic 2 → 3），都是同一格裡有兩種不同召喚物。規格寫「different=0」是假設非召喚格沒有召喚設計，實際上有，見待決 4。

## 6. 檢查

| 檢查 | 結束碼 |
|---|---|
| `ruff check src tests scripts/recipe_census.py` | 0 |
| `ruff format --check src tests` | 0 |
| `mypy src`（679 檔）、`mypy scripts/recipe_census.py` | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（700 檔、438 技能） |
| `classify.py --check` | 0 |
| 相關測試（經看門狗）：`tests/llm tests/narrative tests/bot test_hardcoded_scan test_architecture tests/world/test_battlefield.py tests/world/test_opening.py`；`tests/skillgen tests/content tests/world/test_season_boss.py tests/world/test_oath.py`；`tests/api/tuning tests/content/test_tuning_fields.py tests/test_x10_fields.py`；`tests/api/test_world_battlefield_view.py tests/api/test_world_api.py`；`test_recipe_census_rc0.py` | 全部 0（1156、8184 passed＋7 skipped、397、17、4） |
| `scripts/check.py`、slow（parity、`tests/cli`） | 等開發 PM 回覆後跑（見第 8 節補記） |

## 7. 複雜度與 noqa

沒有新加 `# noqa`。`_request_payload` 原本要多一個參數，改成 keyword-only（`budget_text=`），避開 `PLR0917`。

## 8. 待 PM 決定

1. **`wish_cards` 開進工坊後，畫面還有寫死的「三選一」**：許願的三選一畫面、`tuning_fields.yaml` 裡「許願池：候選量」與「都不拿時退回」的 `note_zh`（「挑 3 張」「三選一」）、前端許願畫面，都在 HC-6b 或內容文字範圍，這段沒動。工坊改成 4 張時，後端的提示詞、檢查、schema 會照改，但這些字不會。
2. **新格的建議範圍**：`pool.wish_cards` 的 `hint_min` 2、`hint_max` 5（保守，現值 3 在中間）；上限由載入檢查「不能大於候選量」擋。
3. **誓約冷卻「1 天內」**留 text：資料是 `cooldown_seconds`（86400），要組字得決定「秒換成天」的寫法（不整除時怎麼寫）。
4. **recipe_census 的非召喚關鍵字比對**：規格要求 different=0，但 ignite、prone 等格子裡本來就有召喚設計，鍵字串與 8 格設計數因此不同（第 5 節）。不帶召喚設計的關鍵字是 0；請 PM 確認這樣算通過。
5. **26 筆留在 text**（3.3 節）：多數要先把數字搬進 content（「最多 1 個」類上限、引擎寫死的 1 格／每輪 1 次），建議排進 HC-7 的 config 搬家；或 PM 裁定「最多 1 個」也算結構、改判 const。
6. **原本就沒用到的 9 條規則沒刪**（`py-scale-names`、`py-scale-dict-keys`、`py-scale-resource-base`、`py-content-loader-config-number` 等 config／scale）：基準時就是 0 筆，不是這段造成的，規格只說刪「搬完變成 0 筆的」，所以留著。
7. **`py-content-rules-text-text`、`py-content-skill-rules-text-text`** 基準時已是 0 筆（text 類），這段一起刪了。
8. **API 呼叫點小改**：`api/world_presenter.py` 只把 `FALLBACK_ZH[...]` 改成 `fallback_zh(library, ...)`（字在 `world/battlefield.py`），沒動 API 的文字。
