# Phase LB-1 報告｜本機 LLM 模型比較

> 2026-11-14。只量測、寫報告；沒改設定檔、沒改遊戲程式（只改量測腳本 `scripts/llm_model_compare.py`）。
> 題目：4-L5 那 20 題（`trpg llm propose -n 20`，seed 0）。每題＝技能提議（重試迴圈，最多 3 次）＋通過時的命名（`name_skill`），與遊戲相同。
> 原始資料：`docs/phases/LB-1資料/`（每個模型一份 JSON ＋執行紀錄 `run_*.log`）。

## 一、比較表

四欄是派工指定的；「Gemma（重測）」是 LB-1b 依使用者「Gemma 再重測一次」補跑的一欄（2026-11-14，同一組 20 題、同樣條件），和沿用的舊 Gemma 欄並排；最後一欄（swift 不思考）是**加量的參考欄**，原因見第四節第 1 點。

| 項目 | Gemma 4 26B-A4B（沿用） | Gemma 4 26B-A4B（重測，LB-1b） | qwen3.6-35b-a3b 不思考 | qwen3.6-35b-a3b 思考（現行設定） | swift（現行設定） | （參考）swift 不思考 |
|---|---|---|---|---|---|---|
| 模型 id | `google/gemma-4-26b-a4b-qat` | 同左 | `qwen3.6-35b-a3b` | `qwen3.6-35b-a3b` | `swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp` | 同左 |
| 架構／量化 | gemma4 MoE／Q4_0 | 同左 | qwen35moe（MoE）／Q4_K_XL | 同左 | qwen35（dense 27B）／Q4_K_XL | 同左 |
| 思考設定 | `reasoning_effort=none` | `reasoning_effort=none` | `reasoning_effort=none` | 照 `config/llm.toml`（只送 `enable_thinking=false`） | 照 `config/llm.toml` | `reasoning_effort=none` |
| 每題秒數 中位數 | 3.81 | 4.28 | 3.77 | 18.41 | 38.76 | 4.91 |
| 每題秒數 最慢 | 7.30 | 7.43 | 8.19 | 21.23 | 42.15 | 10.36 |
| 每題秒數 平均 | 4.19 | 4.53 | 4.20 | 18.38 | 38.73 | 5.49 |
| 一次通過 | 8/20（40%） | 5/20（25%） | 11/20（55%） | 0/20（0%） | 0/20（0%） | 10/20（50%） |
| LLM 最終通過（含重試） | 13/20 | 10/20 | 13/20 | 0/20 | 0/20 | 17/20 |
| 退回組合器等（退回率） | 7/20（35%）：組合器 5、技能池 1、工坊 1 | 10/20（50%）：組合器 8、技能池 1、工坊 1 | 7/20（35%）：組合器 5、技能池 1、工坊 1 | 20/20（100%）：組合器 18、技能池 1、工坊 1 | 20/20（100%）：同左 | 3/20（15%）：組合器 1、技能池 1、工坊 1 |
| 平均嘗試次數 | 2.0 | 2.35 | 1.8 | 3.0 | 3.0 | 1.8 |
| 命名成功（LLM 取名／需要命名） | 13/13 | 10/10 | 10/13 | 0/0 | 0/0 | 17/17 |
| 失敗：LLM 呼叫層 | 0 | 0 | 0 | `llm.bad_response` 59 | `llm.bad_response` 60 | 0 |
| 失敗：格式（pydantic） | `value_error` 11 | `value_error` 13 | `value_error` 5 | 0 | 0 | `value_error` 2 |
| 失敗：引擎合法性（合計） | 37 | 36 | 25 | 1 | 0 | 22 |
| 生成 t/s（串流、不含 prompt 處理） | 未量 | 222.2 | 176.5 | 169.0 | 62.2 | 63.6 |
| 端到端 t/s（全部呼叫的輸出 token ÷ 呼叫時間，含 prompt 處理） | 127.1 | 128.9 | 99.4 | 167.8 | 79.8 | 60.8 |
| reasoning tokens 中位數（每次呼叫） | 0 | 0 | 0 | 990.5 | 1014 | 0 |
| 輸出被 `max_tokens` 截斷（`finish_reason=length`） | 0 | 0 | 0 | 59/60 | 60/60 | 0 |
| VRAM（`nvidia-smi`，RTX 5090 32 GB） | 未量 | 21.0 GB | 27.3 GB | 27.2 GB | 24.4 GB | 24.7 GB |
| 暖機 1 題 | 3.6 秒 | 14.7 秒 | 5.0 秒 | 8.5 秒 | 23.4 秒 | 5.8 秒 |
| LM Studio 載入的 context | 13824 | 8192 | 13824 | 13824 | 8192 | 8192 |

引擎合法性失敗的明細（次數，全部嘗試合計）：

- **Gemma**：`passive.affects` 6、`reference` 6、`skeleton.secondary_count` 6、`budget.over` 3、`exclusion.terrain_needs_earth` 3、`budget.weak` 2、`skeleton.core_share` 2、`variant.mark_and_shatter.*` 4、`variant.finisher.*` 2、`shield.status` 1、`skeleton.core` 1。
- **Gemma（重測）**：`reference` 10、`exclusion.terrain_needs_earth` 5、`skeleton.secondary_count` 5、`variant.overload.*` 8、`budget.over` 2、`passive.affects` 2、`skeleton.secondary_share` 2、`budget.weak` 1、`passive.category` 1。
- **qwen 不思考**：`reference` 8、`keyword.required` 4、`exclusion.terrain_needs_earth` 3、`skeleton.secondary` 2、`budget.over`／`budget.weak`／`on_kill.beneficial`／`passive.affects`／`skeleton.core_share`／`skeleton.required_primitive`／`skeleton.secondary_share`／`tier.terrain_area` 各 1。
- **qwen 思考**：`skeleton.core` 1（其餘 59 次都是思考用光 1024 tokens、沒有內容的 `llm.bad_response`）。
- **swift（現行）**：無（60 次全是 `llm.bad_response`）。
- **swift 不思考**：`budget.weak` 4、`exclusion.terrain_needs_earth` 3、`keyword.required` 3、`reference` 3、`skeleton.secondary` 3、`skeleton.core` 2、`skeleton.core_share` 2、`passive.affects` 1、`skeleton.required_primitive` 1。

命名的退回原因（命名成功但有被擋過的次數，見 JSON 的 `naming_codes`）：

- **Gemma**：`name_zh.duplicate` 1、`concept.effect_mismatch`＋`cast_flavor.effect_mismatch` 1、`cast_flavor.world_terms` 1。
- **Gemma（重測）**：`concept.effect_mismatch`＋`cast_flavor.effect_mismatch` 1、`name_zh.duplicate` 1。
- **qwen 不思考**：13 題裡 9 題的命名至少被擋過一次 `concept.world_terms`；3 題（第 3、7、20 題）3 次都不合格、名稱退回成組合式的「位移」「範圍」「刻印」。
- **swift 不思考**：`concept.effect_mismatch` 1。

## 二、技能樣本（固定抽第 1、8、15 題）

退回的題目沒有 LLM 文字，名稱與描述是組合器的暫定文字，照實貼出。

### 第 1 題：1 階／epic／不限骨架／combo_point

| 模型 | 來源 | 名稱 | 概念 | 施放描述 |
|---|---|---|---|---|
| Gemma | 組合器（3 次都不合格） | 暗影・蓄力與終結 | 隨機組合器產生的蓄力與終結技能（種子 1682515056，暫定） | （暫定）力量依你的意志成形。 |
| Gemma（重測） | 組合器（3 次都不合格） | 暗影・蓄力與終結 | 隨機組合器產生的蓄力與終結技能（種子 1682515056，暫定） | （暫定）力量依你的意志成形。 |
| qwen 不思考 | LLM（第 2 次通過） | 沉刃重壓・終擊 | 透過反覆的蓄力攻擊疊加勢能，最終釋放一次摧毀性的物理重擊。 | 武裝者將全身重量灌注於刃尖，伴隨一聲低沉悶響，利刃如隕石般狠狠砸落。 |
| qwen 思考 | 組合器 | 暗影・蓄力與終結 | （同 Gemma 的暫定文字） | （暫定）力量依你的意志成形。 |
| swift（現行） | 組合器 | 暗影・蓄力與終結 | （同上） | （暫定）力量依你的意志成形。 |
| （參考）swift 不思考 | LLM（第 3 次通過） | 裂土重擊 | 將大地的沉悶力量凝於兵刃，一記砸下讓地面崩開，對單一目標造成傷害。 | 兵刃重重落下，震得腳下的岩石碎裂，塵土中只剩一聲悶響。 |

### 第 8 題：1 階／rare／不限骨架／high_ground

| 模型 | 來源 | 名稱 | 概念 | 施放描述 |
|---|---|---|---|---|
| Gemma | LLM（第 1 次通過） | 大地號令 | 藉由震盪頻率引發地表共鳴，強行將目標拉向震央並施加統御意志。 | 碎裂的地面隆起，將迷途者強行拽入這場秩序的洗禮。 |
| Gemma（重測） | 組合器（3 次都不合格） | 雷電・連段 | 隨機組合器產生的連段技能（種子 3466511313，暫定） | （暫定）力量依你的意志成形。 |
| qwen 不思考 | 組合器 | 雷電・連段 | 隨機組合器產生的連段技能（種子 3466511313，暫定） | （暫定）力量依你的意志成形。 |
| qwen 思考 | 組合器 | 雷電・連段 | （同上） | （暫定）力量依你的意志成形。 |
| swift（現行） | 組合器 | 雷電・連段 | （同上） | （暫定）力量依你的意志成形。 |
| （參考）swift 不思考 | 組合器 | 雷電・連段 | （同上） | （暫定）力量依你的意志成形。 |

### 第 15 題：1 階／epic／不限骨架／marked

| 模型 | 來源 | 名稱 | 概念 | 施放描述 |
|---|---|---|---|---|
| Gemma | LLM（第 1 次通過） | 跳動的電光印記 | 在目標身上烙下閃爍的電光標記，隨後引發劇烈的電擊。 | 當殘餘的電光在空氣中震盪，雷鳴便會追隨印記而至。 |
| Gemma（重測） | 組合器（3 次都不合格） | 雷電・刻印 | 隨機組合器產生的刻印技能（種子 3211773546，暫定） | （暫定）力量依你的意志成形。 |
| qwen 不思考 | 組合器 | 雷電・刻印 | 隨機組合器產生的刻印技能（種子 3211773546，暫定） | （暫定）力量依你的意志成形。 |
| qwen 思考 | 組合器 | 雷電・刻印 | （同上） | （暫定）力量依你的意志成形。 |
| swift（現行） | 組合器 | 雷電・刻印 | （同上） | （暫定）力量依你的意志成形。 |
| （參考）swift 不思考 | LLM（第 2 次通過） | 斷界標 | 在目標身上烙下殘破的頻率紋路，使其成為破碎世界中的顯眼焦點。 | 指尖劃過空氣，一道晶亮的殘痕懸浮於對手胸前，隨呼吸微微震動。 |

### 補充：各模型 LLM 取的全部名稱（固定抽樣外，只列名稱）

- **Gemma**：意志的重壓、灼熱刻印、重力崩裂、遲滯波紋、大地號令、灼痕刻印、沉重重擊、霜凍殘響、跳動的電光印記、凝滯的衝擊、雷鳴號令、終焉之號令、灼熱烙印。
- **Gemma（重測）**：怒火號令、重力印記、燼痕灼印、寒流衝撞、裂隙重擊、灼熱刻印、重壓碎裂、遲滯刻印、雷鳴積蓄、灼燒刻痕（第 1、8、15 題這次都退回組合器，所以固定抽樣沒有 LLM 文字）。
- **qwen 不思考**：沉刃重壓・終擊、沉岩環印、熾焰尖錐、疊燼燃魂、赤燼十字、裂風侵襲、雷鳴削骨、重壓・崩解印、凝滯縛印、熾痕烙心（另 3 題命名失敗，退回「位移」「範圍」「刻印」）。
- **swift 不思考**：裂土重擊、灼骨餘燼、驚雷印、赤痕標記、凝霜封界、流火錐、纏電蓄力、沉岩刻誌、焚心點、瞬閃雷鳴、陷足石牢、斷界標、沉土拖曳、引雷盡散、鎖鏈伏雷、疾風層疊、烙心火印。

## 三、做法

1. **腳本**：`scripts/llm_model_compare.py`（前一位 agent 寫，commit f4cce2ab5；這次加了串流量速、`nvidia-smi`、reasoning 中位數、截斷次數、`--enable-thinking`，並在生成速度低於 60 t/s 時停止）。模型與思考設定只用環境變數 `TRPG_LLM_MODEL`、`TRPG_LLM_REASONING_EFFORT` 覆寫這一次執行。
2. **每個模型（每輪）**：先跑 1 題暖機（種子 999 的另一題、只試 1 次，不計入）→ 串流短請求量生成速度（「用繁體中文寫一段約 600 字的奇幻冒險故事」，`max_tokens` 500，從第一個 token 算到最後，不含 prompt 處理）→ `nvidia-smi` 看 VRAM → 依序跑 20 題。全程一次一個請求，沒有其他程式同時用 LM Studio。
3. **怎麼關掉 qwen 的思考**：先用短請求試了五種寫法（`max_tokens` 400）：

   | 寫法 | reasoning tokens／輸出 | content |
   |---|---|---|
   | 什麼都不帶 | 385／400 | 空 |
   | `chat_template_kwargs.enable_thinking=false`（遊戲現行送的） | 381／400 | 空 |
   | `reasoning_effort=none` | 0／161 | 有 |
   | `reasoning_effort=none` ＋ `enable_thinking=false` | 0／193 | 有 |
   | `reasoning_effort=low` | 381／400 | 空 |

   結論：LM Studio 上只有 `reasoning_effort=none` 關得掉（也就是專案已有的 `TRPG_LLM_REASONING_EFFORT=none`，`config/llm.toml` 裡註解掉的那行）；`chat_template_kwargs` 被忽略。不思考那一輪 61 次呼叫的 `reasoning_tokens` 全部是 0。swift 也一樣（`reasoning_effort=none` 時 0）。
4. **Gemma 沿用**前一位的資料（`google_gemma-4-26b-a4b-qat.json`、`run.log`），沒重跑；那份沒有串流 t/s 與 VRAM，表上寫「未量」。**LB-1b** 另外重測一次（`gemma_retest.json`、`run_gemma_retest.log`，舊資料沒覆蓋），條件相同：`TRPG_LLM_REASONING_EFFORT=none`、暖機 1 題、串流量速、`nvidia-smi`、依序 20 題；程式為 main bf0618b03（`src`、`content` 與舊 Gemma 那次相同）。端到端 t/s 與 reasoning tokens 那份有記錄（reasoning 全為 0）。前一位跑的程式碼與這次相同（`src`、`content` 在兩個基底之間沒有差異）。

## 四、注意事項

1. **「現行設定」等於思考開著**：`config/llm.toml` 現在只送 `chat_template_kwargs.enable_thinking=false`，`reasoning_effort` 是註解掉的；LM Studio 不認前者，所以 qwen 與 swift 照現行設定都會思考，思考把 `max_tokens` 1024 用光（120 次呼叫中 119 次 `finish_reason=length`），回應沒有內容 → 每題 3 次都 `llm.bad_response` → 全部退回組合器。這是「思考開啟」欄 0% 通過的原因，不代表模型本身寫不出合格技能。這也表示：**如果遊戲現在就是用 `config/llm.toml` 原樣連 LM Studio 的 swift，生成的技能會全部是組合器退回**。因為這個結果，額外跑了一輪「swift 不思考」當參考欄，讓兩個 Qwen 系模型能在同樣條件下比較（約 2 分鐘）。沒改任何設定檔。
2. **qwen 第一次很慢**：前一位 agent 跑 qwen 時暖機 60.8 秒、第 1 題 161.6 秒（`run.log` 末兩行），原因是 LM Studio 把 MoE 的專家權重放在 CPU。使用者已修好；這次 qwen 佔 VRAM 約 27 GB、生成約 170～177 t/s，都在 GPU 上。
3. **速度門檻**：swift 的生成速度 62～64 t/s，剛好在 60 t/s 門檻之上，VRAM 24.4 GB；它是 dense 27B（每個 token 要算全部參數），qwen 與 Gemma 是 MoE（每個 token 只算一小部分），速度差距主要來自架構，不是沒載進 GPU，所以沒停下來。swift 現行設定那輪的串流請求首 token 等了 10.8 秒（換模型後的第一個串流請求），不思考那輪是 2.3 秒。
4. **端到端 t/s 不等於生成 t/s**：表上的「端到端」把 prompt 處理（每題 prompt 約 5,000 tokens）也算進時間，輸出短的時候會偏低（例如 qwen 不思考每次只輸出中位數 131 tokens）。比較純生成速度看串流那一列。
5. **樣本小**：每個模型只有 20 題、溫度 0.7，一次通過率差一兩題就差 5～10 個百分點；第 4 題（召喚）與第 12 題（高地被動）所有模型都退回，屬題目本身的限制（見 4-L5 報告待決第 3 點）。
6. **qwen 不思考的命名**：`concept.world_terms`（世界觀詞用量）是它最常被擋的原因，13 題中 3 題命名失敗、名稱退回成「位移」「範圍」「刻印」這類組合式名稱；Gemma 與 swift 不思考沒有這個情況。
7. LM Studio 給 swift 載入的 context 是 8192，Gemma 與 qwen 是 13824；這次 prompt 都在 8192 以內，沒有影響結果。Gemma 重測時 LM Studio 載入的 context 是 8192（舊的是 13824），暖機 14.7 秒含換模型的載入時間。

## 五、給使用者的觀察（只描述數據，不做決定）

- **在都關掉思考的條件下**，qwen3.6-35b-a3b 與 Gemma 的每題時間幾乎一樣（中位數 3.77 vs 3.81 秒），swift 慢約 1 秒（4.91 秒）。純生成速度 qwen 約 176 t/s、swift 約 64 t/s；Gemma 舊的那次沒量，重測約 222 t/s（重測的每題中位數 4.28 秒）。
- **一次通過率**：qwen 不思考 55%、swift 不思考 50%、Gemma 40%（重測 25%）。**最終由 LLM 產出（含重試）**：swift 不思考 17/20，qwen 不思考與 Gemma 都是 13/20。
- **格式錯誤**（pydantic 的 `value_error`）：Gemma 11 次、qwen 5 次、swift 2 次。
- **命名**：Gemma 13/13、swift 不思考 17/17 都由 LLM 取名；qwen 不思考 10/13，另外 3 題因世界觀詞與敘事不一致退回組合式名稱。
- **思考開著（現行設定）**：qwen 與 swift 都 100% 退回組合器，每題 18～39 秒，時間全花在被截斷的思考上。
- 第 8 題（high_ground）四個 Qwen 系的欄位都退回，只有 Gemma 通過；第 1 題 Gemma 退回、兩個 Qwen 系不思考都通過。
- VRAM：Gemma 約 21 GB（重測時量）、qwen 約 27 GB、swift 約 24.5 GB（32 GB 卡）。
- **兩次 Gemma**：同一組題目、同樣設定，重測的一次通過 5/20（舊的 8/20）、LLM 最終產出 10/20（舊的 13/20）、退回 10/20（舊的 7/20），每題中位數 4.28 秒（舊的 3.81 秒）。兩次都由 LLM 產出的有 9 題（第 2、5、6、7、10、11、16、17、20 題）；第 8、14、15、19 題舊的通過、重測退回，第 3 題相反。重測量到的純生成速度 222 t/s，是這次量過的模型裡最快的。

## 開發 PM 裁定（2026-11-14）

- 接受。前一位 agent 被停掉（qwen 當時被 LM Studio 放在 CPU，約 20 t/s；使用者修好後重新載入，開發 PM 實測 27 GB、148 t/s），本位接續、沿用 Gemma 資料。
- **重要發現轉使用者**：`config/llm.toml` 現行只送 `chat_template_kwargs.enable_thinking=false`，LM Studio 不認，qwen 與 swift 都關不掉思考，思考用光 max_tokens 1024，20 題全部退回組合器。要關掉思考得設 `reasoning_effort=none`（`TRPG_LLM_REASONING_EFFORT=none`）。改設定檔與改用哪個模型都由使用者決定，這段沒改。
