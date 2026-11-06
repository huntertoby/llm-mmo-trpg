# Phase 3-25b 完成報告｜戰場變奏的介面、工坊、組合器、進化模板

分支：`worktree-agent-a1403ad4127bb709b`（從 main 6f78c14 分出）。`LOG_FORMAT` 不變（本段不動引擎）。
規格：`docs/phases/Phase3計畫.md` 第 33 節 33.2（6 項）＋ PM 追加第 7 項（射程 ± 計入預算）。只動 API 視圖、前端、工坊、組合器、進化模板、預算的變奏部分；沒有碰 `trpg/engine/modifiers.py` 與 `content/affixes.yaml`。

## 做了什麼

### 第 7 項（PM 追加）射程 ± 計入預算
- `content/skill_budget.yaml`：`variant_range_step_permille: 50`（`BudgetRules`）。變奏型態的射程每 +1 格，該型態的點數加 **基礎型態點數（不含變奏加價）** 的 5%；−1 不折抵。`BudgetReport.variant_range_permille` 記錄加價。
- 驗證器 `_variant_violations` 的型態預算改取 `report.variants`（含射程加價），不再各自重算。
- 潮汐之矛居高型態拿掉擊倒，回到純射程 +2：基礎 82.1%、水中貫穿 95.8%、居高投矛 75.3%，**全部落在預算窗內**（沒有調其他數值）。`trpg skills budget` 因此逐型態顯示含射程加價的結果。

### 第 6 項 schema 限制
- `SkillDef._check_variants`：帶變奏的技能不可含 `zone`、`delayed_damage`、`copy_skill`（含巢狀效果；`VARIANT_FORBIDDEN_PRIMITIVES`），中文錯誤訊息「帶變奏的技能不能含「xxx」效果（區域、延遲傷害、複製技能等後續查表拿到的是基礎型態，變奏不會生效）」。
- 技能卡關鍵字標「（特定地形）」：`KeywordRef.variant`（由 `SkillKeywords.variant` 帶入），`KeywordLine` 在該關鍵字後面顯示。

### 第 1 項 API 視圖
- `SkillCard.variants: tuple[SkillVariantCard]`：每個型態帶 `id`、`name_zh`、`condition`（條件中文）、`condition_kind`、`target_dependent`、`change`（替換內容中文）、`icon`（該型態自己的組裝式圖示）。
- `BattleResponse.variant_states`（新增 `src/trpg/api/variants.py`）：主角每一招帶變奏的技能 → `active`（只看施放者位置的條件，現在成立的型態）與 `available`（目前的合法動作中，目標點會選出的型態，含居高與目標表面）。型態一律由引擎的 `varied_skill`／`chosen_variant` 判定，前端不自己判條件。
- `PreviewOut.variant`（型態 id ＋ 型態名）：`/preview` 依該動作的目標點判定；傷害、範圍、射程原本就是引擎以該型態算的。
- OpenAPI 與 `client/src/api/schema.d.ts` 重產。

### 第 2 項 前端
- 技能卡（`SkillCardView` ＋ 新元件 `VariantList`）列出所有型態（圖示、型態名、條件、替換內容；目標依賴的條件註明「看目標點，預覽時顯示」）；技能列的浮動卡標出「目前生效」。技能列、升級／營火候選卡、工坊預覽都用同一個 `SkillCardView`。
- 技能列按鈕：有型態生效或選得到時發亮（綠色邊框＋緩慢脈動，`prefers-reduced-motion` 時不動）；施放者位置的條件成立時圖示換成該型態的圖示並寫型態名；只有目標點條件（居高、目標表面）選得到時不換圖示、寫「可用：型態名」。
- 預覽第一行寫「型態：水中貫穿」（沒有變奏成立時不寫）；影響格取自引擎，所以跟著型態變。
- 彈出卡一律用共用元件：型態列表在卡片內（不是另開彈出層），卡片本身是 `useFloatCard` 的浮動卡；關鍵字「（特定地形）」在既有的 `PartTip` 內。沒有新增原生 `title` 或自製彈出層。

### 第 3 項 技能工坊
- 新步驟 `variants`（稀有度之後；稀有以上、主動、非複合／陷阱的技能才出現；可省略）：`variants` 列表欄位（新 `FieldType: variants`），每項填型態代碼、型態名、條件（四種擇一：站在表面、居高、身旁有牆、目標點在表面）、替換內容（換形狀、射程 ±、換元素、加一個附帶效果）。上限取自 `core.yaml` 的 `variant_max_by_rarity`。
- 即時檢查：`BudgetSummary.variants`／`variant_surcharge_permille`；檢查面板列出「基礎型態因 N 個變奏多算 X%」與每個型態的比例、合格與否、含射程加價。技能卡預覽也顯示型態。
- 全部填完時工坊預設停在「稀有度」，不自動跳去可省略的變奏步驟（`defaultStep`）。
- 前端改動很少：`variants` 型別重用 `ModifiersField`（參數化標題），「加一個附帶效果」加入物件選項欄位。

### 第 4 項 隨機組合器
- `content/skill_composer.yaml` 新增 `variant`：`permille: 250`（稀有以上、主動技能抽中的機率；獨立亂數串流）、`conditions`（6 種：水中、冰上、居高、靠牆、油面、水窪）、`changes`（6 種：遠投、貫穿、火焰、雷電、寒霜、擊倒）。
- 抽中時，在強度調整 **之前** 就選好變奏（`_pick_variant`：亂數順序中第一個通過 schema 的候選），所以調整器看到的是含加價的基礎預算；最後仍由 `validate_skill` 驗證每個型態。前半的重抽（`MAX_ATTEMPTS // 2`）帶變奏，都做不出來就退回不帶變奏，確保每個種子都有結果。沒抽中的種子結果與以往完全相同（亂數串流獨立）。
- 種子 0–49 全部通過驗證，產生變奏的是種子 0（稀有，油面・雷電）與 19（史詩，水中・貫穿），共 2 個。

### 第 5 項 進化模板
- `content/skill_evolution.yaml` 加 `battle_variant`（`op: variant`，加深分支，放在加深模板的最後，所以既有進化軌跡不變，只在前面的模板都做不出來或被選為 fallback 時才出現）。候選共用組合器的 `variant` 資料，取前 8 個 schema 合法的草稿，各自照同階預算重新調整、再驗證；進化後的稀有度取原本與「變奏數量需要的稀有度」的較高者（普通 → 稀有）。

## 驗收

| 條件 | 結果 |
|---|---|
| vitest：型態列表、發亮條件、預覽型態切換 | `client/src/battle/variants.test.ts`（10 例）；全部 vitest 695 通過 |
| pytest：視圖欄位 | `tests/api/test_variant_views.py`（技能卡型態、特定地形關鍵字、`variant_states` 的 active／available、預覽型態）；`tests/api/test_routes.py` 的預覽欄位集合 |
| pytest：組合器種子 0–49 全過且有產生變奏 | `tests/skillgen/test_variant_gen.py::test_the_composer_makes_valid_variants_for_seeds_0_to_49`（2 個）＋確定性、普通不帶 |
| pytest：進化模板產生合法變奏 | `test_the_evolution_variant_op_builds_a_legal_skill`（`_build` 直接測；實際進化流程只有在前面的模板都不合格時才會挑到） |
| pytest：工坊驗證 | `test_the_workshop_offers_a_variants_step…`、`…shows_a_budget_per_form`、`…reports_bad_variants_as_problems` |
| pytest：第 6 項 schema 限制、第 7 項射程預算 | `tests/content/test_variant_schema.py`（zone／delayed_damage／copy_skill 三例；+2 射程加 10%、−1 不折抵） |
| 截圖 | `docs/phases/img/3-25b-*.jpg`（**只能存 jpg**，瀏覽器工具輸出 jpg）：`workshop`（變奏步驟、各型態預算）、`card`（工坊的技能卡預覽含型態與「特定地形」）、`glow`（站在水上，潮汐之矛發亮、圖示換成貫穿、寫「水中貫穿」）、`preview`（預覽第一行「型態：水中貫穿」與直線範圍）、`floatcard`（1600×900 技能列浮動卡，標「目前生效」）、`floatcard-800x600` |
| `check.py` 全過、`pnpm build` 成功 | 見最後一節 |

### 瀏覽器實測：浮動卡（PM 常駐規則）
從觸發元素滑進卡片 → 在卡片內捲動 → 釘住 → 關閉，在 **1600×900** 與 **800×600** 各做一次（沼澤地圖、潮汐之矛，施放者站在水上）：

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過按鈕顯示卡片（含型態列表、「目前生效」標記） | 通過 | 通過 |
| 從按鈕滑進卡片，卡片不關閉 | 通過 | 通過 |
| 在卡片內向下捲動 | 卡片高度 347px，內容完整，沒有溢出（沒有捲軸可捲到底）；捲動時卡片不關閉 | 同左（卡片貼在按鈕上方，頂端 115px，仍在視窗內） |
| 點卡片釘住，滑鼠移開仍開著（class 帶 `pinned`） | 通過 | 通過 |
| Esc 關閉 | 通過 | 通過 |

說明：這張卡（潮汐之矛，2 個型態）在兩種尺寸下都放得下，所以「捲到底」只驗證了「沒有溢出且不誤關閉」；內容更長的技能（2 個型態加很多效果）沒有實測有捲軸的情況。

## 複雜度
沒有新增 `noqa`。

## 待 PM 決定
1. **組合器機率與產出量**：`variant.permille: 250`（稀有以上），種子 0–49 只有 2 個產出變奏（受限於基礎預算加價後常超窗、型態各自要過窗）。要更多變奏可調高機率或讓調整器的目標區間在變奏技能上更低（目前沒動 `tuning`）。
2. **進化模板的出現時機**：`battle_variant` 放在加深模板最後，不影響既有軌跡，但實際進化時很少被挑到（只有前面模板都不合格或當 fallback）。要提高曝光需要調整 `evolution_options` 的偏好規則（例如「從沒用過地形技能」之類的統計）。
3. **工坊不支援 `replace_effect`**（替換既有附帶效果）：介面只提供換形狀、射程 ±、換元素、加附帶效果；`replace_effect` 要用進階 YAML。
4. **工坊「加一個附帶效果」只列 5 種原語**（擊倒、拉扯、推擊、施加狀態、產生表面）：其他原語用進階 YAML；清單在 `option_variant._ADD_EFFECTS`。
5. **限制原語清單**：只擋 `zone`、`delayed_damage`、`copy_skill`。`time_bomb`（`delayed_damage` 的炸彈用法）、`rule_change`、`grant_skill` 等是否也有「後續查表拿到基礎型態」的問題，我只比對了 3-25a 報告 #8 列的三種，未逐一審查。
6. **`variant_states.available` 的語意**：包含「目前合法動作中選得到的型態」，所以居高型態在「有比自己低的合法目標」時就發亮，圖示不換（只標「可用：型態名」）。要不要在居高時也換圖示，請決定。
7. **組合器的變奏候選是資料表的笛卡兒積**，型態名是「條件名・替換名」（例「居高・遠投」），沒有針對技能內容挑更貼切的名稱；之後 LLM 可改名。
8. **內容檔的 `skills_show_all` CLI 快照雜湊與 `skill_icons.json` 前端固定資料已依規定重產**（潮汐之矛改動、組合器種子結果因變奏而變）；與 3-31 合併時這兩個檔案可能衝突，請以合併後重產為準（`UPDATE_CLI_SNAPSHOTS=1 uv run pytest tests/cli/test_output_snapshots.py`、`uv run python -m tests.narrative.icon_fixture`）。
