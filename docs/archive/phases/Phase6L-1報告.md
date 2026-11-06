# Phase 6L-1 報告：提示詞語氣分區與技能命名

- 依據：使用者同意（原話「好」）的 6L-1 C1～C9、#126、#127（06 6.34.7、07 7.6、09 9.6.5）；追加項「同名技能」（玩法 PM 決定，併入 C8）。
- 分支：worktree 分支，已 merge main（含 6F-1 的 `cf125360`）。沒有 push、沒有合併。
- 規則、預算、數值都沒有改；只改提示詞、文字資料、顯示名與檢查。

## 1. 逐項做了什麼

### C1 全域語氣（`content/llm/world_shattered.yaml`）

加上：「依所在界域的風格；沒有指定時用中性奇幻；不用武俠、仙俠、文言詞（施主、在下、老夫、某某訣），除非界域風格要求。」放在 `text_style_zh`，命名與閃現的系統指令「語氣：」接在 `tone_zh` 後面（`WorldStyle.text_tone()`）。技能提議只出結構，不接：一開始照規格接在 `tone_zh`，實測 12B 退回率上升，A/B 確認是這句造成的（3.3、待決 8）。

### C2～C4 說書語氣（`content/world/narration.yaml` 的 `tones`）

| 區域 | 語氣 |
|---|---|
| `capital`（新增） | 中性奇幻城邦：清楚、略帶莊重；各區來的人照自己的口音 |
| `cloud_ridge`（改） | 東方山城：短句白話；只有青霧觀修士用文言、稱人『施主』，盜賊、獵人、商人、村民說白話 |
| `ashen_waste` | 不變 |
| `crystal_crown`（預先） | 奇幻城邦：典雅清楚，帶一點騎士與法師的禮節；不用文言 |
| `arcane_hub`（預先） | 機械感：短句、精確，常用齒輪、黃銅、晶能與符文的比喻；工匠說話講效率 |
| `frost_tide`（預先） | 航海口語：爽快直接，常用潮汐、風向、船與冰的比喻；水手說話帶吆喝 |

- 原本 `tones` 的區域必須有地點圖；主城（樞紐圖）與還沒有地點圖的三區會載入失敗。改成「地點圖、主城或 `regions.yaml` 的區」都可以（`load_world_event_content(tone_regions=…)`）。區域 ID 照 `regions.yaml`。
- 說書人的 `STORY_PROMPT_VERSION` 不用升：語氣是資料區 `<world>` 的內容，系統指令沒變。

### C5 技能命名

- 命名系統指令加上：「句式多樣：兩字、三字、四字、『X之Y』混用，不要都用『X・Y』」「不可以用『施主』，也不要取『某某訣』這種名字」。
- 新的確定性檢查 `check_archaic`（`naming.py`；清單在 `world_shattered.yaml` 的 `naming.archaic`）：
  - 名稱一律不可含 `always`（施主）。
  - 區域風格不允許古風詞時（中性、主城、荒原、晶冠、樞市、海境），名稱與兩段敘事不可含 `terms`（施主、在下、老夫、真氣、丹田、心法、乾坤、九轉…共 27 個），名稱不可用 `suffixes` 結尾（訣）。
  - 違反時錯誤碼 `name_zh.archaic`／`concept.archaic`／`cast_flavor.archaic`，照舊帶錯誤重試、用盡退回組合式名稱。
  - 雲嶺（`archaic: true`）可以用古風詞與「某某訣」，只有「施主」不行。

### #126 名稱與描述照取得地點的區域

- 資料：`world_shattered.yaml` 新增 `neutral_style_zh` 與 `skill_styles`（主城＋五區，主城＝中性奇幻；雲嶺 `archaic: true`）。`WorldStyle.style_payload(region)` 給 prompt 用，沒有區域或沒列出的區域＝「無（中性）」。
- 提示詞：
  - 技能提議：有區域時 `<request>` 多 `style`（區域名＋風格），系統指令說明「只影響主題構想，不要因為它多填任何欄位」。中性時不帶（提議只出結構）。
  - 命名：`<skill>` 多 `style`，系統指令說明名稱與兩段文字照 `style_zh`。
  - 閃現：`<request>` 多 `style`，`note_zh` 照它寫。
- 區域從呼叫端傳入，LLM 不猜：
  - `ProposalRequest.region`、`TopicRequest.region`、`CandidateRequest.region`（都只進 prompt，不影響子集、候選與數值）。
  - `make_offer`／`offer_key`／`OfferJob` 多 `region`；大世界任務三選一傳 `char.region`，機遇傳 `pending_event.region`（取自世界狀態）；背景預先計算照同樣參數（快取鍵一致）。
  - `FlashRequest.region`（只進 prompt）；目前沒有呼叫端傳值，見待決 3。
  - 創角、許願池、測試原型（roguelite）不傳＝中性。
- 現況：大世界的三選一與閃現目前都不開 LLM（`as_run` 的 `llm=False`），所以區域風格要等大世界開 LLM 才會實際用到；接線與測試已就緒。

### 12B 對照：命名帶武器

- 命名 `<skill>` 多 `weapon`：手上的武器名稱＋出招方式（例「匕首（武器技，用這把武器出招）」「任何武器（法術，不靠武器出招）」），系統指令說明「匕首就寫刺、劃，不要寫成拳頭或掌」。
- 來源：技能提議器用 `ProposalContext.held`（主手、副手的中文名）；閃現用 `FlashRequest.weapon_zh`（roguelite 填主角武器）；沒有時用技能的武器需求。

### C7 共鳴改名（`content/world/resonance.yaml`，id 不變）

「丹毒共鳴」→「蝕毒共鳴」、「霧隱共鳴」→「潛影共鳴」；`world_economy_schemas.py` 的說明、`tests/world/test_resonance.py`、`client/src/world/bagScreen.test.ts` 一起改。`docs/` 沒有出現這兩個名字。

### C8 偏東方的通用技能改中性名（id 不變）

見第 4 節清單。描述裡的「真氣、丹田、經脈、沉肩墜肘、丹氣」也一起改成中性說法（4 招）。測試、`sim/builds.yaml` 與程式註解的名字一起改；`docs/` 的歷史報告與設計文件沒改。霧鎖千山、霧遁沒動。

### C8 追加：同名技能

- 17 個白板配方補 `weapon_name_zh`（第 4 節清單），照武器打法加一個動作字。
- 新增內容檢查（`trpg content check` 會報錯）：
  - `whiteboard_name_problems`（`composer_rules.py`）：不同配方的技能不可同名（含武器版名稱）；`weapon_name_zh` 不可和 `name_zh` 相同；**主動的基本配方同時開放法術與武器時要有 `weapon_name_zh`**，除非名稱本來就以動作字結尾（擊、斬、刺、射、撞、刀）。
  - `skill_name_problems`（`library.py`）：手寫技能（`skills/`）同名但內容不同（排除 id 後比較）報錯；白板的武器版名稱不可和手寫技能同名。放在其他內容檢查之後，原有的錯誤訊息測試不受影響。

### C9 分區評估集

- `content/llm/style_eval.yaml`（schema `StyleEvalRules`，已登記）：分區 `[cloud_ridge, ashen_waste, capital]`、不可帶古風詞的區 `[ashen_waste, capital]`、可稱「施主」的 NPC（雲嶺：青崖道長、小蓮、霧鎖真人）、「X・Y」上限 500‰。古風詞清單共用 `naming.archaic`。
- `src/trpg/llm/style_eval.py`：純函式 `style_report`，三項驗收（只算 LLM 取的名稱；退回的組合式名稱固定是「X・Y」，不算）。
- `scripts/eval_style.py --names <csv> [--dialogues <json>]`：三項都過結束碼 0，否則 1。
- `skill_eval.region_items` 與 `eval_llm_skills.py --suites region --region N`：升級候選的同一題在三區各出一次（同題目、同種子，只差區域），合格後照區域命名；CSV 多 `region` 欄（放最後，舊的讀法不受影響）。預設的 `--suites` 不含 region。

## 2. PROMPT_VERSION

| 提示詞 | 前 | 後 |
|---|---|---|
| 技能提議 `PROMPT_VERSION` | `skill-proposal/7` | `skill-proposal/10`（`/8`、`/9` 是評估中的過渡版，見 3.3） |
| 命名 `NAMING_PROMPT_VERSION` | `skill-naming/3` | `skill-naming/4` |
| 閃現 `FLASH_PROMPT_VERSION` | `flash-variation/2` | `flash-variation/3` |
| 說書人 `STORY_PROMPT_VERSION` | `storyteller/2` | 不變（系統指令沒變，語氣在資料區） |

快照：`tests/llm/test_prompts.py`、`tests/llm/test_naming.py` 各新增一筆；`test_flash_propose.py` 的版本斷言更新。

## 3. 評估（gemma-4-12b-it，`reasoning_effort=none`，一次一個請求）

- 端點 `http://127.0.0.1:1234/v1`，設定放在自己的暫存 toml（`TRPG_LLM_CONFIG`），沒改 repo 的設定檔，也沒碰模型伺服器。
- 改前：`fad5b7f5` 的 `git archive`（暫存資料夾）。改後：本分支。題目、種子、重試次數相同。
- 原始輸出在開發用的暫存資料夾 `scratchpad/l1/`，沒進版控。
- **未完成**：閃現評估（`eval_flash_llm.py`）與情境判定沒有重跑。閃現提示詞的改動只有語氣與 `style`，原因是專案 PM 要求收尾（LM Studio context 8192，新基準之後另外重跑）。
- **HTTP 400**：兩邊都有幾段連續的 400（伺服器拒絕，例如 LM Studio 的 context 只有 8192，重試帶上一份提議與錯誤時超長）。改前的自由測試有 63 題碰到，改後是 5～9 題。所以下表另外列「排除碰到 400 的題目」。

### 3.1 C9 分區驗收（`scripts/eval_style.py`，同 12 題 × 雲嶺、荒原、主城；說書人：雲嶺、荒原每位 NPC 各聊 2 次）

| 驗收 | 改前 `fad5b7f5` | 改後 `/8` | 改後 `/10`（最終） |
|---|---|---|---|
| 荒原、主城的技能名不帶古風詞 | 通過（0／14） | 通過（0／15） | 通過（0／18） |
| 雲嶺一般人的對白不出現「施主」 | **不通過**（2／30：霜音、柳掌櫃） | 通過（0／30） | 通過（0／30） |
| 「X・Y」句式不超過一半 | **不通過**（15／20，75%） | 通過（0／23，0%） | 通過（0／27，0%） |

- 改前雲嶺、荒原、主城的名字看不出差別（例：雲嶺「幽影剝離・寂滅」、荒原「破空・電弧驅逐」）。改後有分區的味道：雲嶺「鶴影護雲」「翠竹毒霧」，荒原「熔鐵重壓」「焦土焚燒」，主城「慈光環繞」「堅毅守護」。
- 改後幾乎都是四字名，「兩字、三字、X之Y 混用」只做到一部分（升級候選有「護佑之光」「震盪波」）。
- 分母是 LLM 合格且由 LLM 命名的技能（退回的不算），所以三欄的分母不同。

### 3.2 技能評估（升級 50＋強制 132＋自由 300）

| 題組 | 指標 | 改前 | 改後 `/8` | 改後 `/10`（最終） |
|---|---|---:|---:|---:|
| 升級候選 50 | 退回 | 28.0% | 40.0% | 32.0% |
| | 排除碰到 400 | 28.0%（0 題碰到） | 33.3%（5 題） | 32.0%（0 題） |
| | 一次通過／平均嘗試 | 38.0%／2.02 | 24.0%／2.28 | 30.0%／2.14 |
| 強制測試 132 | 退回 | 32.6% | 39.4% | 36.4% |
| | 排除碰到 400 | 32.6%（0 題） | 35.0%（9 題） | 36.4%（0 題） |
| 自由測試 300 | 退回 | 24.0% | 17.0% | 7.7% |
| | 排除碰到 400 | 6.8%（63 題） | 15.9%（5 題） | 7.7%（0 題） |
| 多樣性（LLM 合格） | 技能數 | 353 | 359 | 395 |
| | 不同效果組合 | 80 | 68 | 73 |
| | 最常見組合占比 | 施加狀態＋傷害 42.5% | 施加狀態＋傷害 36.2% | 施加狀態＋傷害 42.8% |
| 升級候選命名 | 「X・Y」 | 34／34（100%） | 0／30（0%） | 0／33（0%） |

### 3.3 退回率上升的原因（A/B，自由測試前 120 題，沒有碰到 400）

| 版本 | 退回 |
|---|---:|
| 改前 | 6.7% |
| 改後 `/8`（提議帶 style、語氣有 C1 句） | 14.2% |
| 改後 `/9`（中性不帶 style，語氣仍有 C1 句） | 12.5%（升級候選 40.0%） |
| A：改前＋只加 C1 句 | 9.2% |
| B：改後＋拿掉 C1 句 | 5.8% |

- 結論：退回變多主要來自 **C1 那句接在技能提議的系統指令**（12B 會因此多填變奏、多出 `value_error` 和 `reference`），和區域 style 關係不大。
- 最終版（`/10`）和改前比：升級候選退回 +4 個百分點（2 題）、強制測試 +3.8（5 題）、自由測試（排除 400）+0.9；不同效果組合 80 → 73、最常見組合占比 42.5% → 42.8%。這些在 12B 單次執行的誤差範圍內（同一版本重跑常差幾題），沒有再調。最終版這一輪沒有碰到 HTTP 400。
- 處理（`skill-proposal/10`）：C1 句改放在 `world_shattered.yaml` 的 `text_style_zh`，**只接在寫文字的提示詞**（命名、閃現）；技能提議只出結構、不寫名稱與描述，所以不接。命名與閃現的系統指令文字和 `/8` 時相同。詳見待決 8。

## 4. 新名清單（給玩法 PM 確認）

### 4.1 C8 通用技能

| id | 原名 | 新名 |
|---|---|---|
| `skill_qi_breath` | 運氣調息 | 沉息癒傷 |
| `skill_palm_strike` | 震掌 | 震擊 |
| `skill_thunder_clap` | 震雷掌 | 雷鳴震波 |
| `skill_nine_turns_revival` | 九轉回天 | 復甦之環 |
| `skill_decoy_swap` | 調虎離山 | 換位重擊 |
| `skill_retreating_slash` | 回馬斬 | 撤步斬 |
| `skill_tiger_charge` | 猛虎衝撞 | 衝鋒撞擊 |

### 4.2 白板武器版名稱（`weapon_name_zh`）

| 配方 | 法術版 | 武器版 |
|---|---|---|
| `fire_bolt` | 火球 | 火球擊 |
| `fire_burst` | 火焰爆 | 火焰爆擊 |
| `kindle` | 點燃 | 點燃斬 |
| `lightning_bolt` | 雷擊 | 雷擊斬 |
| `spark_burst` | 電爆 | 電爆擊 |
| `frost_shard` | 冰錐 | 冰錐刺（6F-1 已有） |
| `frost_patch` | 凝冰 | 凝冰斬 |
| `venom` | 淬毒 | 淬毒刺 |
| `toxic_pool` | 毒沼 | 毒沼擊 |
| `mark_target` | 烙印 | 烙印擊 |
| `shadow_bolt` | 暗影彈 | 暗影彈射 |
| `water_bolt` | 水彈 | 水彈射 |
| `flame_lance` | 炎流 | 炎流斬 |
| `thunder_lance` | 雷槍 | 雷槍刺 |
| `frost_breath` | 寒息 | 寒息斬 |
| `venom_mist` | 毒霧 | 毒霧斬 |
| `shadow_ring` | 暗影環 | 暗影環斬 |
| `chain_lightning` | 連鎖閃電 | 連鎖閃電擊 |

沒有補的主動基本配方（名稱本來就是武器打法）：順水重擊、趁勢補刀、絆擊、乘勢重擊、頂撞。

## 5. 檔案

- 內容：`content/llm/world_shattered.yaml`、`content/llm/style_eval.yaml`（新）、`content/world/narration.yaml`、`content/world/resonance.yaml`、`content/skill_composer.yaml`、`content/skills/skill_{qi_breath,palm_strike,thunder_clap,nine_turns_revival,decoy_swap,retreating_slash,tiger_charge}.yaml`、`content/sim/builds.yaml`、`content/units/sect_steward.yaml`（註解）。
- 程式：`src/trpg/content/{world,world_events,world_narration,library,composer_rules,registry}.py`、`src/trpg/llm/{naming,candidate_source,flash_propose,flash_eval,skill_eval,style_eval(新)}.py`、`src/trpg/llm/prompts/{builder,proposal,naming,flash}.py`、`src/trpg/skillgen/{proposal_subset,proposal_topic,candidates,flash_offer}.py`、`src/trpg/roguelite/{offers,flashes}.py`、`src/trpg/world/{quests,solutions}.py`、`src/trpg/api/{offer_prefetch,world_economy_schemas}.py`；`engine/ai/{priority,composite}.py`、`content/environment.py` 只改註解的技能名。
- 腳本：`scripts/eval_style.py`（新）、`scripts/eval_llm_skills.py`。
- 測試：`tests/llm/test_region_style.py`（新，14 個）、`tests/content/test_skill_same_name.py`（新，8 個）、`tests/content/test_world_narration.py`（+1）、`tests/llm/{test_prompts,test_naming,test_flash_propose}.py`（快照）、改名跟著改的 `tests/engine/*`、`tests/api/test_followup_api.py`、`tests/content/test_skill_scaling.py`、`tests/world/test_resonance.py`；`client/src/battle/followup.test.ts`、`client/src/world/bagScreen.test.ts`（只換字串）。

## 6. 測試

- `tests/llm`、`tests/skillgen`：4160 通過、14 略過；最終版（`skill-proposal/10`）再跑 `tests/llm`：342 通過。
- `tests/world`、`tests/roguelite`、`tests/content`：3801 通過（同名檢查移到其他檢查之後再跑一次）。
- `tests/api/test_offer_prefetch.py`、`test_opportunity_offer_view.py`、`test_followup_api.py`、改名相關的 `tests/engine/*`：通過。
- `trpg content check`：通過。
- 每次 commit 前 ruff check、ruff format --check、mypy src、lint-imports 都通過。
- 沒跑：全量、CLI 快照、client vitest（worktree 沒有 `node_modules`；兩個 client 測試只換字串，前後一致）。

## 7. noqa

沒有新增。

## 8. 待 PM 決定

1. **C8 新名**（4.1）要玩法 PM 看。另外 **「九轉回天」是雲嶺精英「青霧執事」的蓄力強招**（18 18.2.1 點名），照本段規格改成中性名「復甦之環」，但 18 的設計文件還寫「九轉回天」。它是雲嶺敵人專用，照 #126 也可以保留東方名；請決定要不要改回，或請玩法 PM 改 18。
2. **白板武器版名稱**（4.2）：一個配方只有一個 `weapon_name_zh`，近戰、遠程拿到的是同一個名字（例：弓手的武器版也叫「火球擊」）。要分近戰／遠程的話要加欄位。被動、反應配方的武器版目前仍和法術版同名（檢查只管主動基本配方）。
3. **白板配方和手寫技能同名 13 個**：召喚元素之靈、召喚冰靈、召喚戰狼、召喚水精、召喚火靈、召喚石像、召喚雷靈、喚起骷髏、回春、回氣、捕獸夾、毒霧、連鎖閃電。內容不同，但這次的檢查沒有把它們算錯（不然要一起改名）；要不要也報錯、改名請決定。
4. **閃現名照原技能的界域**：玩家持有的技能沒有記「取得地點的區域」，所以 `FlashRequest.region` 目前沒有人傳值（閃現一律中性）。要做到 #126 的這一點需要在角色的技能上記區域（存檔欄位），留給大世界開 LLM 時。
5. **古風詞清單**（`naming.archaic.terms`，27 個，含單字「仙」「罡」）與「訣」只在雲嶺可用、「施主」任何區的技能名都不可用：是開發照最保守做的解讀，請玩法 PM 定稿。中性區的檢查也套在 concept、cast_flavor。
6. **C4 三區語氣與 `skill_styles` 的風格文字**是開發擬的初稿，請玩法 PM 看。
7. 改名技能的**描述也改成中性**（4 招）；層數「氣」沒改。
8. **C1 的位置**：規格寫「`tone_zh` 加上」。實測接在技能提議會讓 12B 退回率上升（3.3），所以改成獨立的 `text_style_zh`，只接在命名與閃現；文字一字不改。說書人、情境判定本來就不讀 `tone_zh`（說書人用 `narration.yaml` 的區域語氣）。請 PM 確認這個做法。
9. 評估在 LM Studio context 8192 下跑，HTTP 400 不少。新的基準（context 調大後）由 PM 另排重跑。
