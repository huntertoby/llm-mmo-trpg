# Phase LB-2b 報告｜Q12 被動引導、變奏開放射程加值、改後重測

> 2026-11-14。基底 main `d96b5a974`（LB-2 已合併）。原始資料：`docs/phases/LB-2b資料/`。
> 題目同 LB-1／LB-2：4-L5 那 20 題（seed 0），每題最多 3 次＋命名，溫度 0.7、`reasoning_effort=none`。
> 依據：玩法 PM 交接 4.1.17（待決 5、6，不用問使用者）。沒改 `config/`、`docs/design/`；沒放寬任何驗證或引擎規則；沒做平衡量測或模擬。

## 一、給使用者的白話結論

**改完後 Gemma 不再明顯比 swift／qwen 差，但起伏很大。** 兩輪 Gemma 最終由 LLM 通過 17/20、12/20（LB-2 改前 11/20，LB-1 13/20），退回 3/20、8/20（改前 9/20）。swift 改後 1 輪 15/20、退回 5/20；LB-1 的 qwen 不思考是 13/20。最終通過率三個模型已經同一級；**差別在「第一次就答對」**：Gemma 6～7/20，swift 12/20（LB-1 qwen 11/20）。Gemma 要靠重試補回來，所以每題中位數約 4.8～5.8 秒，和 swift 的 5.6 秒差不多。

**剩下的錯誤主要是什麼：**
- **Gemma：變奏（戰場變奏）占了 96 條裡的 61 條。** 這次把「射程加值」開放給變奏之後，Gemma 很愛加變奏（改前 45 次嘗試有 17 次帶變奏，改後 83 次有 58 次）。加了變奏就容易超出骨架的附帶效果上限、占比上限或變奏型態預算過弱，也會把射程加值放在沒有射程的形狀（直線、錐形）上。第二多的是「沒帶到題目關鍵字」與「超預算」。
- **swift：只有 18 條錯誤，全是規則層**：沒帶到關鍵字 5、附帶效果不在骨架允許的清單 5、地形技能頂層元素沒填大地 4。沒有任何變奏錯誤。

**Q12（史詩被動＋高處）：還沒有通過**（Gemma 兩輪、swift 一輪都退回技能池）。但卡的地方變了：
- 改前：每次都拿「隆起地形」當被動效果（一定超預算）。改後**沒有一次用升降地形**。
- Gemma 改後：效果改成「自己獲得統御＋護盾」，`affects: self` 也寫對了，但統御這個狀態太貴，在「移動後」這個觸發下超預算 131%，三次都同一份答案；而且這個答案其實沒帶到「高處」。
- swift 改後：第一次就照引導寫了「居高臨下（height_advantage）＋自己護盾」，但漏了 `trigger`；之後兩次改了觸發卻把條件拿掉、或武器需求填錯。方向對了，差一點。

**另外兩件事：**
1. 第一版改完先跑 Gemma 一輪（「初版」欄），退回反而變多（14/20）：50 次嘗試有 26 次把射程加值放在直線、錐形、環形上。我補了兩處說明與回饋（列出這題哪些形狀有射程；被動要明寫 `affects: self`），之後才是正式的兩輪。
2. **swift 第 2 輪、qwen 沒跑**：swift 第 2 輪量速 58.6 t/s，低於 60 門檻，依規矩停下（VRAM 26.0 GB 和第 1 輪一樣，看起來整個在 GPU 上，只是 swift 本來就剛好在 60 上下：第 1 輪 63.7、LB-1 63.6）。qwen 因此沒跑。Gemma 已經載回來，LM Studio 只剩 Gemma 一個。

## 二、並排表

條件全部：20 題、seed 0、溫度 0.7、`reasoning_effort=none`、`response_format` 約束（LB-1 swift 那輪例外，見註）。「退回」含第 4 題（common 召喚，一直是工坊保底）與第 12 題（技能池），這兩題所有模型、所有輪都退回。

| 項目 | LB-1 Gemma | LB-1b Gemma | LB-2 基準 Gemma 0.7 | 改後初版 Gemma（只 A、B） | **改後 Gemma 第 1 輪** | **改後 Gemma 第 2 輪** | LB-1 swift 不思考（註） | **改後 swift 第 1 輪** | 改後 swift 第 2 輪 | LB-1 qwen3.6 不思考 | 改後 qwen3.6 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 一次通過 | 8/20 | 5/20 | 5/20 | 5/20 | **7/20** | **6/20** | 10/20 | **12/20** | 未跑（58.6 t/s，停） | 11/20 | 未跑（停在 swift） |
| LLM 最終通過 | 13/20 | 10/20 | 11/20 | 6/20 | **17/20** | **12/20** | 17/20 | **15/20** | — | 13/20 | — |
| 退回 | 7/20 | 10/20 | 9/20 | 14/20 | **3/20** | **8/20** | 3/20 | **5/20** | — | 7/20 | — |
| 平均嘗試 | 2.0 | 2.35 | 2.25 | 2.5 | 2.0 | 2.15 | 1.8 | 1.65 | — | 1.8 | — |
| 每題秒數中位數 | 3.81 | 4.28 | 4.12 | 5.94 | 4.84 | 5.77 | 4.91 | 5.61 | — | 3.77 | — |
| 命名成功 | 13/13 | 10/10 | 11/11 | 6/6 | 16/17 | 12/12 | 17/17 | 15/15 | — | 10/13 | — |
| 生成 t/s／VRAM | 未量 | 222／21.0 GB | 225／21.6 GB | 209／21.3 GB | 215／22.4 GB | 215／22.4 GB | 63.6／24.7 GB | 63.7／26.0 GB | 58.6／26.0 GB | 176.5／27.3 GB | — |
| Q12 | 技能池 | 技能池 | 技能池 | 技能池 | 技能池 | 技能池 | 技能池 | 技能池 | — | 技能池 | — |

註：LB-1 swift 那輪是 LB-2 查出的 client 缺陷造成的**沒有 schema 約束**（`guided_json` 被 LM Studio 忽略），和改後不是同一條件，只當參考。

兩輪 Gemma 通過的題目：第 1 輪 1、2、3、5、6、7、8、10、11、13、14、15、16、17、18、19、20；第 2 輪 1、3、5、7、8、11、13、14、15、16、18、19。和 LB-2 一樣，同條件兩輪的差距（17 對 12）比改動前後的差距還大，20 題的樣本只能看大方向。

## 三、錯誤分類（Gemma 改後兩輪 vs LB-2 基準 0.7）

改後兩輪 83 次嘗試、96 條錯誤（`stats_gemma_after_both.md`）；LB-2 基準 45 次、44 條（`LB-2資料/stats_gemma_base_t07.md`）。分輪：`stats_gemma_after_t07_r1.md`、`_r2.md`；初版：`stats_gemma_firstcut_t07_r1.md`；swift：`stats_swift_after_t07_r1.md`。

改後前 10 名：

| 名次 | 類別 | 改後（83 次） | 基準（45 次） | 原文例子 |
|---|---|---|---|---|
| 1 | `variant.v1.skeleton.secondary_count` | 11 | 0 | Q2：怒火迸發：骨架 builder_finisher：附帶效果最多 2 個，收到 3 個（變奏的 add_effect 讓變奏型態超過上限） |
| 2 | `value_error`｜變奏的 range_delta 只能用在射程是數字的形狀 | 9 | 0 | Q2：變奏「怒火迸發」：range_delta 只能用在射程是數字的形狀，收到 cone 的射程 None |
| 3 | `variant.v1.skeleton.secondary_share` | 6 | 0 | Q3：殘響：骨架 displace：damage 占 50.7%，超過上限 50.0% |
| 4 | `keyword.required` | 6 | 0 | Q4：技能必須製造或利用題目的關鍵字 summon，但提議沒有帶到 |
| 5 | `budget.over` | 6 | 3 | Q12：超出預算：total 5.50 ÷ 可用預算 4.20 ＝ 131.0% |
| 6 | `skeleton.secondary_count` | 5 | 7 | Q2：骨架 builder_finisher：附帶效果最多 2 個，收到 3 個 |
| 7 | `variant.v1.budget.weak` | 5 | 0 | Q3：殘響：過弱：44.3%（下限 70.0%） |
| 8 | `reference`｜single 的 range 必須在 1–10 | 4 | 0 | Q15：single 的 range 必須在 1–10，收到 0 |
| 9 | `reference`｜層數 combo_point 只有符合條件的技能可以消耗 | 4 | 1 | Q9：effects[2].stack… |
| 10 | `variant.v1.skeleton.core` | 4 | 0 | Q17：靈光迸發：骨架 aura：沒有核心效果 |

基準前 10 名裡**改後歸零或幾乎歸零的**：`exclusion.terrain_needs_earth` 6 → 0、`passive.affects` 6 → 1、變奏替換內容 1～2 項 5 → 0、法術技 weapon_req 3 → 0、主傷害被換掉 3 → 0、武器技 weapon_req 2 → 0。也就是 LB-2 針對的「模型看不到的規則」大致都解掉了。

**新冒出來的主要是變奏**：變奏相關錯誤 改後 61/96 條（基準 11/44）。帶變奏的嘗試比例從 38%（17/45）升到 70%（58/83；初版 76%）。看起來是開放射程加值後，變奏變成「很容易寫的選項」，Gemma 就常常加；但加了以後變奏型態要另外過骨架與預算檢查。`single 的 range 收到 0` 是新出現的（4 次），可能和我補的回饋「改成有數字射程的形狀（例：single 並填數字 range）」有關（第九節第 6 點）。

swift 改後一輪 33 次、18 條：`keyword.required` 5、`skeleton.secondary` 5、`exclusion.terrain_needs_earth` 4、`passive.category` 1、其他 3；**變奏相關 0 條**。

## 四、A：Q12 的提議引導（待決 5）

做法（`skillgen/proposal_passive.py`、`proposal_subset.py`、`proposal_topup.py`）：

1. **被動題目的 `ways` 先列 `uses`**（條件、觸發），再列 `makes`；主動、反應等其他種類順序不變。
2. **放不進被動預算的 `makes` 效果不列**，照預算實算、不寫死清單（`unfit_effect_rules`）：對關鍵字每一條專屬「效果」規則，組一個最省的被動技能，用 `skill_budget` 算比例：
   - 觸發取子集裡係數最高的（`max_per_round` 1；`every_n_hits` 取係數最高的 n，目前是 n＝3 的 600‰）；
   - 效果是被動骨架的核心原語就單獨一個，否則配一個最省的核心效果（heal、shield…各試一次）；
   - 數值用 `minimal_filler` 的最小值、`affects: self`、**不加條件**（條件倍率能壓低點數，但那是另一種寫法，這裡不假設）；
   - 全部組合都超過 `max_ratio` 才算放不進；組不出合法技能就照列（保守：不確定就不藏）。
3. `ProposalSubset` 多一個 `tier`，只在 `select_subset` 最後放進去；挑子集大小時用不篩的估算（只會偏大），所以子集、模型、schema 都不變。
4. 結果（1 階史詩被動）：高處拿掉 `raise_terrain`、`lower_terrain`（最省組合 113%）；點燃、冰凍拿掉兩個姿態狀態；召喚物拿掉 `cheat_death`、`extra_reaction`、`redirect_damage`；其他關鍵字不變。3 階史詩只剩點燃、冰凍的姿態。Q12 的 `ways` 從「raise_terrain、lower_terrain、條件 height_advantage」變成「條件 height_advantage」。
5. 初版重測後補（第 3 個 commit）：被動說明改成「trigger.target 是 self 時（沒有 target 欄位的觸發一律是 self），每個效果都要明寫 `"affects": "self"`」，`passive.affects` 的回饋附同一句修法（初版 Q12 的 Gemma 用 `on_turn_start`、效果不寫 affects，三次一樣）。

**`self_on_high_ground` 沒列出來**：它在 `skill_conditions.yaml` 是 `handwritten_only: true`（KW-2 鷹眼專用），提議子集本來就不收。4.1.17 提到它當主要寫法之一，但開放給 LLM 屬規則／內容決定，我沒動（第九節第 3 點）。

## 五、B：變奏開放 `range_delta`（待決 6）

1. 提議模型 `Variant` 多 `range_delta: Literal[1, 2] | None`（照 `composer_special` 的階梯 1、2，只開加值）。
2. `VARIANT_SWAP_FIELDS` 多 `range_delta`（5 項）→ 變奏分支 10 → 15 支（`schema_shape.py`）。
3. `VARIANTS_NOTE_ZH` 說明射程加值；初版重測後補：列出**這題有射程的形狀**（形狀定義有 `range` 參數的：single、cross、square3、ground_tile、chain…）與沒有射程的形狀，回饋附 `RANGE_DELTA_ADVICE`（拿掉 range_delta 或換成有射程的形狀）。
4. 預算與驗證器不動：`range_delta` 只能配數字射程的形狀、變奏型態照算預算（6.24、#53）都照舊；+3、0、−1 由提議模型直接擋下（`literal_error`）。
5. `proposal_from_skill`（Mock 提議器與 few-shot 用）仍把 `range_delta` 當數值拿掉（`VARIANT_NUMBER_FIELDS` 沒改），所以 Mock 的行為、快照、parity 夾具都不變。LLM 給的值不會被補值器覆蓋（測試確認 +1 原樣進技能、變奏型態射程 3 → 4）。
6. **SCHEMA_CHAR_LIMIT 影響**：每份 schema 多 1,751 字元。340 題（1～5 階 × 4 稀有度 × 無關鍵字＋16 個關鍵字）**新退回不分支的 0 題**（原本就不分支的 140 題不變）；4-L5 那 20 題最大 99,105。但有 64 題分支後落在 120,000～125,000 之間（最大 122,110），之後 schema 再長就會開始退回。

## 六、快照與測試逐條說明

- **快照預測**：`tests/llm/test_prompts.py` 的 `SNAPSHOTS` 只雜湊 `build_skill_proposal_messages` 的固定輸入；這次全部改動都在 `build_proposal_prompt`（題目區說明、`available.keywords.ways`）、schema 與 `evaluate.advise`，所以預測「只新增 `skill-proposal/16` 一鍵、雜湊同 /15」。**結果與預測一致**，沒有任何其他快照或 parity 夾具改變、沒有整批重產。`PROMPT_VERSION` 升 `skill-proposal/15 → /16`（初版與補強都在 /16 裡，還沒合併過）。
- **改的既有測試**：
  1. `tests/skillgen/test_proposal.py::test_proposal_has_no_numeric_fields`：原本斷言變奏沒有 `range_delta`；待決 6 決定開放，改成斷言它只能是 `null` 或 `enum [1, 2]`（仍鎖住不能填其他值）。
  2. `tests/llm/test_schema_shape_lb2.py::test_split_variants_one_or_two_swaps_exactly`：夾具 `VARIANT` 照真模型多 `range_delta`，分支數 4＋6 → 5＋10。
  3. 同檔 `test_handwritten_variants_fit_the_variant_branches`：只改註解（跳過 `range_delta` 的理由從「提議模型沒有這欄位」改成「`proposal_from_skill` 仍把它當數值拿掉」），斷言不變。
  4. `tests/llm/test_prompts.py`：新增 /16 一鍵。
- **新測試**（全部離線）：`tests/llm/test_passive_ways_lb2b.py`（Q12 的 ways、照預算實算、主動題目順序不變、`tier` 為 None 不篩、被動說明與回饋）、`tests/llm/test_variant_range_lb2b.py`（15 支分支、說明、+1 原樣進技能、−1／0／+3 擋下、有射程的形狀清單、回饋修法）。

## 七、驗收

- `ruff check`、`ruff format --check`、`mypy`（不帶參數，1629 檔，含 tests）、`lint-imports`（14 kept）通過。
- `tests/llm` 全部＋`tests/skillgen` 提議相關 17 檔＋`tests/test_architecture.py`＋Mock 相依的 api／world 7 檔：926 passed（`-n 8`）。
- 戰鬥不變比對（照 LB-2 第八節：改前＝main `d96b5a974` 用 `git archive` 解開 src 與 content、`PYTHONPATH` 指過去；8 張地圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，地圖預設陣容、效用 AI、30 輪；比整份 `--log-json`，含事件、動作、最終狀態、規則包雜湊）：A＋B 後與補強後各一次，都是 `battles=46 events=19186 different=0`。這段沒動引擎。

## 八、量測紀錄（換模型規則照做）

- 開始時 `GET /api/v0/models` 只有 Gemma 是 loaded，直接量（沒重載）。之後每次換模型都先 `lms unload --all` 再 `lms load <id> -y`，每輪量測前查 loaded 只有目標一個（`run_chain.log`；腳本 `run_chain.sh.txt`、`check_loaded.py.txt`）。
- 初版 Gemma（改 A、B 後）：209 t/s；正式 Gemma 兩輪：215 t/s、22.4 GB；swift 第 1 輪 63.7 t/s、26.0 GB；swift 第 2 輪 58.6 t/s → 依門檻停（腳本結束碼 2），qwen 沒跑。
- 最後 `lms unload --all`＋`lms load google/gemma-4-26b-a4b-qat -y`，確認 loaded 只有 Gemma。
- 沒啟動、關閉 LM Studio，也沒改它的設定；換模型只用 `TRPG_LLM_MODEL`（量測腳本參數）。

## 九、待 PM 決定

1. **swift 的速度剛好卡在 60 t/s 門檻**：第 2 輪 58.6、第 1 輪 63.7、LB-1 63.6，VRAM 都在 25～26 GB（看起來整個在 GPU 上）。要不要對 swift 放寬門檻（例如 50）補跑 swift 第 2 輪與 qwen？指令同第五節（label 用 after）。
2. **變奏變成 Gemma 的主要錯誤來源**（61/96）：開放 `range_delta` 後帶變奏的嘗試從 38% 升到 70%。可選：(a) 維持；(b) prompt 再強調「沒必要不要加變奏」；(c) 題目沒要求時 schema 不給變奏欄位（schema 變窄，不是放寬，但會讓 LLM 很少產生變奏）。這是玩法取捨，請玩法 PM 定。
3. **`self_on_high_ground` 是 `handwritten_only`**，LLM 用不到；4.1.17 提到它當被動的主要寫法。要不要開放給 LLM 屬內容／規則決定，這段沒動。
4. **Q12 仍沒過**：Gemma 卡在「統御狀態＋移動後觸發」超預算（同一份答案交三次，而且沒帶到高處）；swift 照引導寫了 height_advantage 但漏 trigger。可考慮下一段：被動題目的 schema 把 `category`／`weapon_req` 定成 `spell`／`any`（schema 變窄）、`budget.over` 回饋附「換係數高的觸發或便宜的狀態」。屬引導，不是規則。
5. **「放不進預算」的判定不算條件倍率**：加上嚴苛條件（×0.6）時，升降地形理論上塞得進史詩被動（每命中 3 次、護盾核心：9.5 × 0.6 ＝ 5.7 ≤ 8.4）。我照「最省的寫法、不加條件」判定為放不進（和 4.1.17 的結論一致）。若玩法 PM 認為該算條件，改 `unfit_effect_rules` 一處即可。
6. **`single 的 range 收到 0`**（新出現 4 次）：可能是 `RANGE_DELTA_ADVICE` 寫了「single 並填數字 range」讓模型去填 range。要不要把例子拿掉，下一段順手改。
7. **初版資料保留**：初版（只 A、B）也是 `skill-proposal/16`、資料在 `gemma_firstcut_t07_r1.*`；正式「改後」是補強之後的版本。
8. **`SCHEMA_CHAR_LIMIT`**：這次 0 題新退回，但 64 題已在上限 3,000 字元內；待決 4（LB-2）可以一起看。

## 十、commit

1. `ca9449d1b` feat(lb-2b): passive keyword ways lead with uses and drop effects over the passive budget
2. `e90f4027b` feat(lb-2b): open variant range_delta (+1..+2) to the proposal model
3. `4d468e09a` fix(lb-2b): name the shapes that take range_delta and ask passives for explicit affects self
4. `d8cb6e353` docs(lb-2b): LM Studio model-swap rules and LB-2b proposal notes in the LLM onboarding guide（上手-LLM 第四節第 8 點）
5. docs(lb-2b): report and retest data（本報告、`LB-2b資料/`）

## 開發 PM 裁定（2026-11-14）

- **驗收通過，合併。** 改了 3 條既有測試，都是照玩法 PM 4.1.17 已定的內容改的（range_delta 開放、變奏分支 10 → 15），驗證沒有放寬。快照只新增 `skill-proposal/16` 一鍵，跟預測一致。戰鬥不變比對 different=0。換模型都照規則做，跑完已經把 Gemma 載回來。
- 待決 1：**60 t/s 門檻不放寬**。swift 第 2 輪和 qwen 的改後重測不補，這段的結論靠 Gemma 兩輪加 swift 一輪就夠了。使用者要選 qwen 或 swift 時，再派一輪單獨量。
- 待決 2（變奏成了 Gemma 的主要錯誤）、待決 3（`self_on_high_ground` 要不要開放給 LLM）：屬於玩法或規則的取捨，轉給玩法 PM。
- 待決 4、6（被動 schema 固定成 spell／any、budget.over 的回饋附修法、RANGE_DELTA_ADVICE 的例子會引出 range 0）：都只是引導，跟玩法 PM 對 2、3 的答覆一起排成 **LB-2c** 一段做，不再分好幾次小段。
- 待決 5：同意照「不加條件」判定。
- 待決 7：同意。
- 待決 8：跟 LB-2 的待決 4 一起，先維持 125k。
